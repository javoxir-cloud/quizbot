import asyncio
import hashlib
import hmac
import html
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import parse_qsl

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from aiohttp import web
from dotenv import dotenv_values, load_dotenv

# ---------------------------------------------------------------- sozlamalar
load_dotenv()
logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent
WEBAPP_DIR = BASE_DIR / "webapp"
# Savol banklari endi ochiq papkada emas - faqat /api/bank orqali,
# ruxsat tekshirilgandan keyin beriladi.
DATA_DIR = BASE_DIR / "data"
ENV_PATH = BASE_DIR / ".env"
WEBAPP_PORT = int(os.getenv("PORT") or os.getenv("WEBAPP_PORT", "8080"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
# Adminlar: Telegram ID lari vergul bilan, masalan: ADMIN_IDS=123456789,987654321
ADMIN_IDS = {int(x) for x in re.findall(r"\d+", os.getenv("ADMIN_IDS", ""))}
# Mini App ochilgandan keyin initData qancha vaqt amal qiladi (soniya)
INIT_DATA_MAX_AGE = 7 * 24 * 3600

bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher()


def get_webapp_url() -> str:
    values = dotenv_values(ENV_PATH)
    return (values.get("WEBAPP_URL") or os.getenv("WEBAPP_URL") or "").strip()


_total_savol = 0
for _p in sorted(DATA_DIR.glob("*.json")):
    with open(_p, encoding="utf-8") as f:
        _total_savol += len(json.load(f))
logging.info("Jami bank fayllari: %d ta, savollar: %d", len(list(DATA_DIR.glob('*.json'))), _total_savol)


# ================================================================ saqlash
# Har bir foydalanuvchi: status = pending | allowed | denied,
# expires_at = ruxsat qachongacha (None = muddatsiz). Keyinchalik pullik
# obuna ham shu ustun orqali ishlaydi.
class Storage:
    async def init(self): ...
    async def get(self, uid: int) -> Optional[dict]: ...
    async def upsert(self, uid: int, **fields): ...
    async def list(self, status: Optional[str] = None) -> list: ...


class MemoryStorage(Storage):
    """Baza ulanmagan bo'lsa (mahalliy sinov uchun). Server qayta ishga
    tushganda ro'yxat o'chib ketadi!"""

    def __init__(self):
        self.rows: Dict[int, dict] = {}

    async def init(self):
        logging.warning("DATABASE_URL yo'q - ruxsatlar xotirada saqlanadi va qayta ishga tushganda o'chadi!")

    async def get(self, uid):
        return self.rows.get(uid)

    async def upsert(self, uid, **fields):
        row = self.rows.setdefault(uid, {"user_id": uid, "name": "", "username": "", "status": "pending",
                                         "expires_at": None, "updated_at": None})
        row.update(fields)
        row["updated_at"] = datetime.now(timezone.utc)

    async def list(self, status=None):
        rows = [r for r in self.rows.values() if status is None or r["status"] == status]
        return sorted(rows, key=lambda r: r["updated_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)


class PgStorage(Storage):
    def __init__(self, url: str):
        self.url = url
        self.pool = None

    async def init(self):
        import asyncpg
        self.pool = await asyncpg.create_pool(self.url, min_size=1, max_size=3)
        async with self.pool.acquire() as c:
            await c.execute(
                """
                CREATE TABLE IF NOT EXISTS access (
                    user_id    BIGINT PRIMARY KEY,
                    name       TEXT NOT NULL DEFAULT '',
                    username   TEXT NOT NULL DEFAULT '',
                    status     TEXT NOT NULL DEFAULT 'pending',
                    expires_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        logging.info("PostgreSQL bazaga ulandi")

    async def get(self, uid):
        async with self.pool.acquire() as c:
            r = await c.fetchrow("SELECT * FROM access WHERE user_id=$1", uid)
        return dict(r) if r else None

    async def upsert(self, uid, **fields):
        cols = ["user_id"] + list(fields)
        vals = [uid] + list(fields.values())
        ph = ", ".join(f"${i + 1}" for i in range(len(cols)))
        upd = ", ".join(f"{k}=EXCLUDED.{k}" for k in fields) + (", " if fields else "") + "updated_at=now()"
        async with self.pool.acquire() as c:
            await c.execute(
                f"INSERT INTO access ({', '.join(cols)}) VALUES ({ph}) ON CONFLICT (user_id) DO UPDATE SET {upd}",
                *vals,
            )

    async def list(self, status=None):
        async with self.pool.acquire() as c:
            if status:
                rows = await c.fetch("SELECT * FROM access WHERE status=$1 ORDER BY updated_at DESC", status)
            else:
                rows = await c.fetch("SELECT * FROM access ORDER BY updated_at DESC")
        return [dict(r) for r in rows]


store: Storage = PgStorage(DATABASE_URL) if DATABASE_URL else MemoryStorage()


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


def row_active(row: Optional[dict]) -> bool:
    if not row or row["status"] != "allowed":
        return False
    exp = row.get("expires_at")
    return exp is None or exp > datetime.now(timezone.utc)


async def has_access(uid: int) -> bool:
    return is_admin(uid) or row_active(await store.get(uid))


def user_label(row_or_user) -> str:
    if isinstance(row_or_user, dict):
        name, username, uid = row_or_user["name"], row_or_user["username"], row_or_user["user_id"]
    else:
        name, username, uid = row_or_user.full_name, row_or_user.username or "", row_or_user.id
    s = html.escape(name or "—")
    if username:
        s += f" (@{html.escape(username)})"
    return f"{s} · <code>{uid}</code>"


def fmt_exp(exp) -> str:
    return "muddatsiz" if exp is None else exp.astimezone(timezone(timedelta(hours=5))).strftime("%d.%m.%Y gacha")


# ================================================================ bot
def main_menu() -> ReplyKeyboardMarkup:
    url = get_webapp_url()
    buttons = []
    if url:
        buttons = [[KeyboardButton(text="🎮 Testni boshlash", web_app=WebAppInfo(url=f"{url}?v={int(time.time())}"))]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def decision_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Muddatsiz", callback_data=f"acc:ok:{uid}:0"),
         InlineKeyboardButton(text="✅ 30 kun", callback_data=f"acc:ok:{uid}:30")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"acc:no:{uid}:0")],
    ])


async def notify_admins(text: str, kb=None):
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logging.warning("Adminga yuborib bo'lmadi %s: %s", aid, e)


@dp.message(CommandStart())
async def start(message: Message):
    u = message.from_user
    if await has_access(u.id):
        if get_webapp_url():
            await message.answer("Salom! Testni boshlash uchun pastdagi tugmani bosing.", reply_markup=main_menu())
        else:
            await message.answer("Mini-ilova manzili (WEBAPP_URL) sozlanmagan.")
        return

    row = await store.get(u.id)
    if row and row["status"] == "pending":
        await message.answer("⏳ So'rovingiz adminga yuborilgan, javobni kuting.", reply_markup=ReplyKeyboardRemove())
        return
    if row and row["status"] == "denied":
        await message.answer("⛔ Sizga ruxsat berilmagan. Savollar bo'lsa, admin bilan bog'laning.",
                             reply_markup=ReplyKeyboardRemove())
        return

    # Yangi foydalanuvchi yoki muddati tugagan
    expired = row is not None and row["status"] == "allowed"
    await store.upsert(u.id, name=u.full_name or "", username=u.username or "", status="pending")
    await message.answer(
        ("⌛ Ruxsat muddatingiz tugagan." if expired else "👋 Salom! Bu bot faqat ruxsat berilgan foydalanuvchilar uchun.")
        + "\n\nSo'rovingiz adminga yuborildi. Ruxsat berilishi bilan sizga xabar keladi.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await notify_admins(f"🆕 Ruxsat so'rovi:\n{user_label(u)}", decision_kb(u.id))


@dp.callback_query(F.data.startswith("acc:"))
async def on_decision(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("Faqat admin uchun", show_alert=True)
    _, action, uid_s, days_s = cb.data.split(":")
    uid, days = int(uid_s), int(days_s)
    if action == "ok":
        exp = datetime.now(timezone.utc) + timedelta(days=days) if days else None
        await store.upsert(uid, status="allowed", expires_at=exp)
        try:
            await bot.send_message(uid, f"✅ Sizga ruxsat berildi ({fmt_exp(exp)}). Testni boshlash uchun pastdagi tugmani bosing.",
                                   reply_markup=main_menu())
        except Exception:
            pass
        note = f"✅ Ruxsat berildi ({fmt_exp(exp)})"
    else:
        await store.upsert(uid, status="denied", expires_at=None)
        note = "❌ Rad etildi"
    row = await store.get(uid)
    try:
        await cb.message.edit_text(f"{user_label(row)}\n{note} — {cb.from_user.full_name}", parse_mode="HTML")
    except Exception:
        pass
    await cb.answer(note)


ADMIN_HELP = (
    "<b>Admin buyruqlari</b>\n"
    "/users — ruxsat berilganlar\n"
    "/pending — kutayotgan so'rovlar\n"
    "/add ID [kun] — ruxsat berish (kun yozilmasa muddatsiz)\n"
    "/remove ID — ruxsatni olib qo'yish\n"
    "/myid — o'z ID ingiz"
)


@dp.message(Command("myid"))
async def myid(message: Message):
    await message.answer(f"Sizning Telegram ID: <code>{message.from_user.id}</code>", parse_mode="HTML")


@dp.message(Command("admin"))
async def admin_help(message: Message):
    if is_admin(message.from_user.id):
        await message.answer(ADMIN_HELP, parse_mode="HTML")


@dp.message(Command("users"))
async def cmd_users(message: Message):
    if not is_admin(message.from_user.id):
        return
    rows = [r for r in await store.list("allowed")]
    if not rows:
        return await message.answer("Hali hech kimga ruxsat berilmagan.")
    lines = [f"{'🟢' if row_active(r) else '⚪️'} {user_label(r)} — {fmt_exp(r['expires_at'])}" for r in rows]
    await send_long(message, f"<b>Ruxsat berilganlar ({len(rows)}):</b>\n" + "\n".join(lines))


@dp.message(Command("pending"))
async def cmd_pending(message: Message):
    if not is_admin(message.from_user.id):
        return
    rows = await store.list("pending")
    if not rows:
        return await message.answer("Kutayotgan so'rov yo'q.")
    for r in rows[:20]:
        await message.answer(f"⏳ {user_label(r)}", reply_markup=decision_kb(r["user_id"]), parse_mode="HTML")


@dp.message(Command("add"))
async def cmd_add(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    if not parts or not parts[0].isdigit():
        return await message.answer("Foydalanish: /add 123456789 [kun]\nMasalan: /add 123456789 30")
    uid = int(parts[0])
    days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    exp = datetime.now(timezone.utc) + timedelta(days=days) if days else None
    await store.upsert(uid, status="allowed", expires_at=exp)
    await message.answer(f"✅ <code>{uid}</code> ga ruxsat berildi ({fmt_exp(exp)})", parse_mode="HTML")
    try:
        await bot.send_message(uid, "✅ Sizga ruxsat berildi. Testni boshlash uchun pastdagi tugmani bosing.",
                               reply_markup=main_menu())
    except Exception:
        await message.answer("ℹ️ Foydalanuvchi hali botga /start bosmagan, unga xabar yuborilmadi. "
                             "/start bosganda darhol ishlaydi.")


@dp.message(Command("remove"))
async def cmd_remove(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    arg = (command.args or "").strip()
    if not arg.isdigit():
        return await message.answer("Foydalanish: /remove 123456789")
    await store.upsert(int(arg), status="denied", expires_at=None)
    await message.answer(f"⛔ <code>{arg}</code> ning ruxsati olib qo'yildi", parse_mode="HTML")


async def send_long(message: Message, text: str):
    while text:
        chunk = text[:3900]
        if len(text) > 3900:
            cut = chunk.rfind("\n")
            chunk = text[:cut] if cut > 0 else chunk
        await message.answer(chunk, parse_mode="HTML")
        text = text[len(chunk):].lstrip("\n")


@dp.message()
async def fallback(message: Message):
    if await has_access(message.from_user.id):
        await message.answer("Testni boshlash uchun pastdagi tugmani bosing.", reply_markup=main_menu())
    else:
        await start(message)


# ================================================================ web server
def check_init_data(init_data: str) -> Optional[int]:
    """Telegram Mini App initData imzosini tekshiradi va foydalanuvchi ID sini
    qaytaradi. Soxta yoki eskirgan bo'lsa - None."""
    if not init_data or not BOT_TOKEN:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None
    recv_hash = pairs.pop("hash", "")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, recv_hash):
        return None
    try:
        if time.time() - int(pairs.get("auth_date", "0")) > INIT_DATA_MAX_AGE:
            return None
        return int(json.loads(pairs["user"])["id"])
    except Exception:
        return None


async def api_user(request) -> Optional[int]:
    uid = check_init_data(request.headers.get("X-Init-Data", ""))
    if uid is None:
        return None
    return uid


async def api_me(request):
    uid = await api_user(request)
    if uid is None:
        return web.json_response({"ok": False, "reason": "auth"}, status=401)
    if not await has_access(uid):
        return web.json_response({"ok": False, "reason": "denied"}, status=403)
    row = await store.get(uid)
    exp = row.get("expires_at") if row else None
    return web.json_response({"ok": True, "admin": is_admin(uid), "expires_at": exp.isoformat() if exp else None})


BANK_KEY_RE = re.compile(r"^[A-Za-z0-9_]+$")


async def api_bank(request):
    uid = await api_user(request)
    if uid is None:
        return web.json_response({"ok": False, "reason": "auth"}, status=401)
    if not await has_access(uid):
        return web.json_response({"ok": False, "reason": "denied"}, status=403)
    key = request.match_info["key"]
    path = DATA_DIR / f"{key}.json"
    if not BANK_KEY_RE.match(key) or not path.is_file():
        return web.json_response({"ok": False, "reason": "notfound"}, status=404)
    return web.FileResponse(path)


async def start_webapp_server():
    @web.middleware
    async def no_cache_middleware(request, handler):
        response = await handler(request)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

    app = web.Application(middlewares=[no_cache_middleware])

    async def index(request):
        return web.FileResponse(WEBAPP_DIR / "index.html")

    app.router.add_get("/", index)
    app.router.add_get("/index.html", index)
    app.router.add_get("/api/me", api_me)
    app.router.add_get("/api/bank/{key}", api_bank)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBAPP_PORT)
    await site.start()
    logging.info("Mini-ilova serveri ishga tushdi: http://localhost:%d", WEBAPP_PORT)


async def main():
    if not BOT_TOKEN:
        logging.warning("DIQQAT: BOT_TOKEN yo'q!")
    if not ADMIN_IDS:
        logging.warning("DIQQAT: ADMIN_IDS yo'q - hech kim ruxsat bera olmaydi!")
    await store.init()
    await start_webapp_server()
    if bot:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    else:
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

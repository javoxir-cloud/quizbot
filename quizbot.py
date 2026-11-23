"""Test boti (Telegram Mini App).

Bitta server bir nechta botni boshqaradi. Har bir botning o'z savol banklari
(papkasi) va o'z ruxsatlar ro'yxati bor; Mini App (webapp/index.html) hammasi
uchun bitta.

Render -> Environment:
  BOT_TOKEN      1-bot tokeni           (savollar: data/)
  BOT2_TOKEN     2-bot tokeni, ixtiyoriy (savollar: data_ped/ yoki BOT2_DATA)
  WEBAPP_URL     https://....onrender.com
  ADMIN_IDS      admin Telegram ID lari, vergul bilan (bo'sh = ochiq rejim)
  DATABASE_URL   PostgreSQL (ruxsatlar saqlanadi)
"""
import asyncio
import hashlib
import hmac
import html
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qsl

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
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
ENV_PATH = BASE_DIR / ".env"
WEBAPP_PORT = int(os.getenv("PORT") or os.getenv("WEBAPP_PORT", "8080"))
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
# Adminlar: Telegram ID lari vergul bilan, masalan: ADMIN_IDS=123456789,987654321
ADMIN_IDS = {int(x) for x in re.findall(r"\d+", os.getenv("ADMIN_IDS", ""))}
# ADMIN_IDS berilmagan bo'lsa - ochiq rejim: hamma foydalana oladi.
OPEN_MODE = not ADMIN_IDS
# Mini App ochilgandan keyin initData qancha vaqt amal qiladi (soniya)
INIT_DATA_MAX_AGE = 7 * 24 * 3600


@dataclass
class BotCfg:
    key: str          # ichki nom: "main", "ped"
    token: str
    data_dir: Path    # savol banklari papkasi (banks.json + <key>.json fayllar)
    bot: Optional[Bot] = None
    secret: bytes = b""


def _bot_cfgs():
    cfgs = []
    specs = [
        ("main", os.getenv("BOT_TOKEN", ""), os.getenv("BOT_DATA", "data")),
        ("ped", os.getenv("BOT2_TOKEN", ""), os.getenv("BOT2_DATA", "data_ped")),
    ]
    for key, token, data in specs:
        token = token.strip()
        if not token:
            continue
        c = BotCfg(key=key, token=token, data_dir=BASE_DIR / data)
        c.secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        cfgs.append(c)
    return cfgs


BOTS = _bot_cfgs()
BY_KEY: Dict[str, BotCfg] = {c.key: c for c in BOTS}
BY_ID: Dict[int, BotCfg] = {}       # bot.id -> cfg (ishga tushganda to'ldiriladi)
for _c in BOTS:
    try:
        _c.bot = Bot(token=_c.token)
        BY_ID[_c.bot.id] = _c
    except Exception as e:
        logging.error("%s boti tokeni noto'g'ri: %s", _c.key, e)
dp = Dispatcher()


def get_webapp_url() -> str:
    values = dotenv_values(ENV_PATH)
    return (values.get("WEBAPP_URL") or os.getenv("WEBAPP_URL") or "").strip()


def load_manifest(cfg: BotCfg) -> dict:
    p = cfg.data_dir / "banks.json"
    if not p.is_file():
        return {"title": "Test banklari", "banks": []}
    with open(p, encoding="utf-8") as f:
        m = json.load(f)
    # faqat fayli mavjud banklar
    m["banks"] = [b for b in m.get("banks", []) if (cfg.data_dir / f"{b['key']}.json").is_file()]
    return m


for _c in BOTS:
    _m = load_manifest(_c)
    logging.info("[%s] %d ta bank (%s)", _c.key, len(_m["banks"]), _c.data_dir.name)


def cfg_of(bot: Bot) -> BotCfg:
    return BY_ID[bot.id]


# ================================================================ saqlash
# Har bir (bot, foydalanuvchi): status = pending | allowed | denied,
# expires_at = ruxsat qachongacha (None = muddatsiz). Pullik obuna ham shu orqali.
class Storage:
    async def init(self): ...
    async def get(self, bk: str, uid: int) -> Optional[dict]: ...
    async def upsert(self, bk: str, uid: int, **fields): ...
    async def list(self, bk: str, status: Optional[str] = None) -> list: ...


class MemoryStorage(Storage):
    """Baza ulanmagan bo'lsa. Server qayta ishga tushganda ro'yxat o'chadi!"""

    def __init__(self):
        self.rows: Dict[Tuple[str, int], dict] = {}

    async def init(self):
        logging.warning("DATABASE_URL yo'q - ruxsatlar xotirada saqlanadi va qayta ishga tushganda o'chadi!")

    async def get(self, bk, uid):
        return self.rows.get((bk, uid))

    async def upsert(self, bk, uid, **fields):
        row = self.rows.setdefault((bk, uid), {"bot": bk, "user_id": uid, "name": "", "username": "",
                                               "status": "pending", "expires_at": None, "updated_at": None})
        row.update(fields)
        row["updated_at"] = datetime.now(timezone.utc)

    async def list(self, bk, status=None):
        rows = [r for r in self.rows.values() if r["bot"] == bk and (status is None or r["status"] == status)]
        return sorted(rows, key=lambda r: r["updated_at"], reverse=True)


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
                CREATE TABLE IF NOT EXISTS bot_access (
                    bot        TEXT   NOT NULL,
                    user_id    BIGINT NOT NULL,
                    name       TEXT NOT NULL DEFAULT '',
                    username   TEXT NOT NULL DEFAULT '',
                    status     TEXT NOT NULL DEFAULT 'pending',
                    expires_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (bot, user_id)
                )
                """
            )
        logging.info("PostgreSQL bazaga ulandi")

    async def get(self, bk, uid):
        async with self.pool.acquire() as c:
            r = await c.fetchrow("SELECT * FROM bot_access WHERE bot=$1 AND user_id=$2", bk, uid)
        return dict(r) if r else None

    async def upsert(self, bk, uid, **fields):
        cols = ["bot", "user_id"] + list(fields)
        vals = [bk, uid] + list(fields.values())
        ph = ", ".join(f"${i + 1}" for i in range(len(cols)))
        upd = "".join(f"{k}=EXCLUDED.{k}, " for k in fields) + "updated_at=now()"
        async with self.pool.acquire() as c:
            await c.execute(
                f"INSERT INTO bot_access ({', '.join(cols)}) VALUES ({ph}) "
                f"ON CONFLICT (bot, user_id) DO UPDATE SET {upd}",
                *vals,
            )

    async def list(self, bk, status=None):
        async with self.pool.acquire() as c:
            if status:
                rows = await c.fetch("SELECT * FROM bot_access WHERE bot=$1 AND status=$2 ORDER BY updated_at DESC",
                                     bk, status)
            else:
                rows = await c.fetch("SELECT * FROM bot_access WHERE bot=$1 ORDER BY updated_at DESC", bk)
        return [dict(r) for r in rows]


store: Storage = PgStorage(DATABASE_URL) if DATABASE_URL else MemoryStorage()


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


def row_active(row: Optional[dict]) -> bool:
    if not row or row["status"] != "allowed":
        return False
    exp = row.get("expires_at")
    return exp is None or exp > datetime.now(timezone.utc)


async def has_access(bk: str, uid: int) -> bool:
    if OPEN_MODE or is_admin(uid):
        return True
    return row_active(await store.get(bk, uid))


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
def main_menu() -> InlineKeyboardMarkup:
    """Xabar ostidagi (inline) tugma. MUHIM: pastki reply-klaviatura tugmasi
    orqali ochilgan Mini App'ga Telegram initData bermaydi."""
    url = get_webapp_url()
    if not url:
        return InlineKeyboardMarkup(inline_keyboard=[])
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎮 Testni boshlash", web_app=WebAppInfo(url=f"{url}?v={int(time.time())}"))
    ]])


async def send_menu(bot: Bot, chat_id: int, greeting: str):
    await bot.send_message(chat_id, greeting, reply_markup=ReplyKeyboardRemove())
    await bot.send_message(chat_id, "Testni boshlash uchun tugmani bosing 👇", reply_markup=main_menu())


def decision_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Muddatsiz", callback_data=f"acc:ok:{uid}:0"),
         InlineKeyboardButton(text="✅ 30 kun", callback_data=f"acc:ok:{uid}:30")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"acc:no:{uid}:0")],
    ])


async def notify_admins(bot: Bot, text: str, kb=None):
    # Xabar o'sha botning o'zidan boradi - admin har bir botga /start bosgan bo'lishi kerak
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logging.warning("Adminga yuborib bo'lmadi %s: %s", aid, e)


@dp.message(CommandStart())
async def start(message: Message, bot: Bot):
    bk = cfg_of(bot).key
    u = message.from_user
    if await has_access(bk, u.id):
        if get_webapp_url():
            await send_menu(bot, message.chat.id, "Salom! 👋")
        else:
            await message.answer("Mini-ilova manzili (WEBAPP_URL) sozlanmagan.")
        return

    row = await store.get(bk, u.id)
    if row and row["status"] == "pending":
        await message.answer("⏳ So'rovingiz adminga yuborilgan, javobni kuting.", reply_markup=ReplyKeyboardRemove())
        return
    if row and row["status"] == "denied":
        await message.answer("⛔ Sizga ruxsat berilmagan. Savollar bo'lsa, admin bilan bog'laning.",
                             reply_markup=ReplyKeyboardRemove())
        return

    expired = row is not None and row["status"] == "allowed"
    await store.upsert(bk, u.id, name=u.full_name or "", username=u.username or "", status="pending")
    await message.answer(
        ("⌛ Ruxsat muddatingiz tugagan." if expired else "👋 Salom! Bu bot faqat ruxsat berilgan foydalanuvchilar uchun.")
        + "\n\nSo'rovingiz adminga yuborildi. Ruxsat berilishi bilan sizga xabar keladi.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await notify_admins(bot, f"🆕 Ruxsat so'rovi:\n{user_label(u)}", decision_kb(u.id))


@dp.callback_query(F.data.startswith("acc:"))
async def on_decision(cb: CallbackQuery, bot: Bot):
    if not is_admin(cb.from_user.id):
        return await cb.answer("Faqat admin uchun", show_alert=True)
    bk = cfg_of(bot).key
    _, action, uid_s, days_s = cb.data.split(":")
    uid, days = int(uid_s), int(days_s)
    if action == "ok":
        exp = datetime.now(timezone.utc) + timedelta(days=days) if days else None
        await store.upsert(bk, uid, status="allowed", expires_at=exp)
        try:
            await bot.send_message(uid, f"✅ Sizga ruxsat berildi ({fmt_exp(exp)}). Testni boshlash uchun tugmani bosing 👇",
                                   reply_markup=main_menu())
        except Exception:
            pass
        note = f"✅ Ruxsat berildi ({fmt_exp(exp)})"
    else:
        await store.upsert(bk, uid, status="denied", expires_at=None)
        note = "❌ Rad etildi"
    row = await store.get(bk, uid)
    try:
        await cb.message.edit_text(f"{user_label(row)}\n{note} — {html.escape(cb.from_user.full_name)}", parse_mode="HTML")
    except Exception:
        pass
    await cb.answer(note)


ADMIN_HELP = (
    "<b>Admin buyruqlari</b> (shu bot uchun)\n"
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
async def cmd_users(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    rows = await store.list(cfg_of(bot).key, "allowed")
    if not rows:
        return await message.answer("Hali hech kimga ruxsat berilmagan.")
    lines = [f"{'🟢' if row_active(r) else '⚪️'} {user_label(r)} — {fmt_exp(r['expires_at'])}" for r in rows]
    await send_long(message, f"<b>Ruxsat berilganlar ({len(rows)}):</b>\n" + "\n".join(lines))


@dp.message(Command("pending"))
async def cmd_pending(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    rows = await store.list(cfg_of(bot).key, "pending")
    if not rows:
        return await message.answer("Kutayotgan so'rov yo'q.")
    for r in rows[:20]:
        await message.answer(f"⏳ {user_label(r)}", reply_markup=decision_kb(r["user_id"]), parse_mode="HTML")


@dp.message(Command("add"))
async def cmd_add(message: Message, command: CommandObject, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    if not parts or not parts[0].isdigit():
        return await message.answer("Foydalanish: /add 123456789 [kun]\nMasalan: /add 123456789 30")
    uid = int(parts[0])
    days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    exp = datetime.now(timezone.utc) + timedelta(days=days) if days else None
    await store.upsert(cfg_of(bot).key, uid, status="allowed", expires_at=exp)
    await message.answer(f"✅ <code>{uid}</code> ga ruxsat berildi ({fmt_exp(exp)})", parse_mode="HTML")
    try:
        await bot.send_message(uid, "✅ Sizga ruxsat berildi. Testni boshlash uchun tugmani bosing 👇",
                               reply_markup=main_menu())
    except Exception:
        await message.answer("ℹ️ Foydalanuvchi hali botga /start bosmagan, unga xabar yuborilmadi. "
                             "/start bosganda darhol ishlaydi.")


@dp.message(Command("remove"))
async def cmd_remove(message: Message, command: CommandObject, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    arg = (command.args or "").strip()
    if not arg.isdigit():
        return await message.answer("Foydalanish: /remove 123456789")
    await store.upsert(cfg_of(bot).key, int(arg), status="denied", expires_at=None)
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
async def fallback(message: Message, bot: Bot):
    if await has_access(cfg_of(bot).key, message.from_user.id):
        await send_menu(bot, message.chat.id, "Testlar shu yerda 📚")
    else:
        await start(message, bot)


# ================================================================ web server
def check_init_data(init_data: str) -> Optional[Tuple[BotCfg, int]]:
    """Telegram Mini App initData imzosini tekshiradi. Qaysi bot tokeni bilan
    imzolangan bo'lsa - o'sha bot va foydalanuvchi ID sini qaytaradi."""
    if not init_data:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None
    recv_hash = pairs.pop("hash", "")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items())).encode()
    for cfg in BOTS:
        calc = hmac.new(cfg.secret, check_string, hashlib.sha256).hexdigest()
        if hmac.compare_digest(calc, recv_hash):
            try:
                if time.time() - int(pairs.get("auth_date", "0")) > INIT_DATA_MAX_AGE:
                    return None
                return cfg, int(json.loads(pairs["user"])["id"])
            except Exception:
                return None
    return None


async def api_auth(request):
    """(cfg, uid) yoki xato javobi."""
    res = check_init_data(request.headers.get("X-Init-Data", ""))
    if res is None:
        return None, web.json_response({"ok": False, "reason": "auth"}, status=401)
    cfg, uid = res
    if not await has_access(cfg.key, uid):
        return None, web.json_response({"ok": False, "reason": "denied"}, status=403)
    return res, None


async def api_me(request):
    res, err = await api_auth(request)
    if err:
        return err
    cfg, uid = res
    row = await store.get(cfg.key, uid)
    exp = row.get("expires_at") if row else None
    m = load_manifest(cfg)
    return web.json_response({
        "ok": True, "bot": cfg.key, "admin": is_admin(uid),
        "expires_at": exp.isoformat() if exp else None,
        "title": m.get("title", "Test banklari"), "banks": m["banks"],
    })


BANK_KEY_RE = re.compile(r"^[A-Za-z0-9_]+$")


async def api_bank(request):
    res, err = await api_auth(request)
    if err:
        return err
    cfg, _ = res
    key = request.match_info["key"]
    path = cfg.data_dir / f"{key}.json"
    if not BANK_KEY_RE.match(key) or key == "banks" or not path.is_file():
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
    if not BOTS:
        logging.warning("DIQQAT: BOT_TOKEN yo'q!")
    if OPEN_MODE:
        logging.warning("ADMIN_IDS yo'q - OCHIQ REJIM: botlar hamma uchun ishlaydi, ruxsat tizimi o'chiq")
    await store.init()
    await start_webapp_server()
    bots = [c.bot for c in BOTS if c.bot]
    if not bots:
        await asyncio.Event().wait()
        return
    url = get_webapp_url()
    for b in bots:
        if url:
            try:
                # Chap pastdagi menyu tugmasi - u ham initData beradi
                await b.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Test", web_app=WebAppInfo(url=url)))
            except Exception as e:
                logging.warning("Menyu tugmasini o'rnatib bo'lmadi: %s", e)
        await b.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(*bots)


if __name__ == "__main__":
    asyncio.run(main())

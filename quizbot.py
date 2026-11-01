import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from aiohttp import web
from dotenv import dotenv_values, load_dotenv

# ---------------------------------------------------------------- sozlamalar
load_dotenv()
logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent
WEBAPP_DIR = BASE_DIR / "webapp"
USER_BANKS_DIR = WEBAPP_DIR / "user_banks"
USER_BANKS_DIR.mkdir(parents=True, exist_ok=True)
ENV_PATH = BASE_DIR / ".env"
# Hosting xizmatlari (Render va boshqalar) PORT nomli muhit o'zgaruvchisini
# o'zi beradi - shuni ustun qo'yamiz, bo'lmasa WEBAPP_PORT yoki 8080.
WEBAPP_PORT = int(os.getenv("PORT") or os.getenv("WEBAPP_PORT", "8080"))

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_QUESTIONS = 2000

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


def get_webapp_url() -> str:
    """.env faylidan WEBAPP_URL ni har safar qayta o'qiydi (ngrok manzili
    qayta ishga tushirilganda botni qayta yoqmasdan yangilanishi uchun)."""
    values = dotenv_values(ENV_PATH)
    return (values.get("WEBAPP_URL") or os.getenv("WEBAPP_URL") or "").strip()


# Mini-ilovaning o'zi savol banklarini (bio.json, chem.json) to'g'ridan-to'g'ri
# webapp/ papkasidan o'qiydi - bot tomonida alohida yuklash shart emas,
# faqat bor-yo'qligini log uchun tekshiramiz.
for fname in ("bio.json", "chem.json"):
    path = WEBAPP_DIR / fname
    if path.exists():
        with open(path, encoding="utf-8") as f:
            count = len(json.load(f))
        logging.info("Topildi: %s (%d savol)", fname, count)
    else:
        logging.warning("Topilmadi: %s", path)


# ------------------------------------------------------ foydalanuvchi banki
def parse_json_bank(text: str) -> List[Dict[str, Any]]:
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("JSON ro'yxat (array) bo'lishi kerak, masalan: [ {...}, {...} ]")
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        q = str(item.get("q", "")).strip()
        options = item.get("options")
        correct = str(item.get("correct", "")).strip()
        topic = str(item.get("topic", "")).strip() or None
        if not q or not isinstance(options, list) or not correct:
            continue
        options = [str(o).strip() for o in options if str(o).strip()]
        if len(options) < 2 or correct not in options:
            continue
        entry = {"q": q, "options": options, "correct": correct}
        if topic:
            entry["topic"] = topic
        out.append(entry)
    return out


_OPT_PREFIX_RE = re.compile(r"^[A-DА-Г1-4][\)\.\-]\s*|^[\-\*•]\s*")
_MAVZU_RE = re.compile(r"(?i)^mavzu\s*[:\-]\s*(.+)$")
_SAVOL_PREFIX_RE = re.compile(r"(?i)^savol\s*[:\-]\s*")
_NUM_PREFIX_RE = re.compile(r"^\d+[\.\)]\s*")
_TOGRI_SUFFIX_RE = re.compile(r"(?i)\s*\(to'?g'?ri\)\s*$")


def parse_text_bank(text: str) -> List[Dict[str, Any]]:
    """Oddiy .txt formatini o'qiydi:
    Mavzu: ... (ixtiyoriy, keyingi savollarga tatbiq etiladi)

    Savol: Matn?
    A) variant1
    B) variant2 *
    C) variant3
    D) variant4

    (bo'sh qator savollarni ajratadi; to'g'ri javobdan keyin * qo'yiladi)
    """
    lines = text.replace("\r\n", "\n").split("\n")
    blocks: List[List[str]] = []
    current: List[str] = []
    for line in lines:
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)

    out: List[Dict[str, Any]] = []
    topic = None
    for block in blocks:
        first = block[0].strip()
        m = _MAVZU_RE.match(first)
        if m:
            topic = m.group(1).strip()
            continue

        qline = _SAVOL_PREFIX_RE.sub("", first)
        qline = _NUM_PREFIX_RE.sub("", qline).strip()

        options: List[str] = []
        correct = None
        for opt_line in block[1:]:
            s = opt_line.strip()
            if not s:
                continue
            is_correct = False
            if s.endswith("*"):
                is_correct = True
                s = s[:-1].strip()
            if s.startswith("✅"):
                is_correct = True
                s = s[1:].strip()
            if _TOGRI_SUFFIX_RE.search(s):
                is_correct = True
                s = _TOGRI_SUFFIX_RE.sub("", s).strip()
            s = _OPT_PREFIX_RE.sub("", s).strip()
            if not s:
                continue
            options.append(s)
            if is_correct:
                correct = s

        if qline and len(options) >= 2 and correct:
            entry = {"q": qline, "options": options, "correct": correct}
            if topic:
                entry["topic"] = topic
            out.append(entry)

    return out


USER_UPLOAD_HELP = (
    "📥 O'zingizning savollaringizni yuklash uchun botga <b>.json</b> yoki "
    "<b>.txt</b> fayl yuboring (hujjat/fayl sifatida, rasm emas).\n\n"
    "📄 <b>.txt formati</b> (eng oson usul):\n"
    "<code>Mavzu: Kimyo asoslari\n\n"
    "Savol: Suvning kimyoviy formulasi?\n"
    "A) H2O *\n"
    "B) CO2\n"
    "C) O2\n"
    "D) NaCl\n\n"
    "Savol: Oltin elementi belgisi?\n"
    "A) Fe\n"
    "B) Au *\n"
    "C) Ag\n"
    "D) Cu</code>\n\n"
    "Qoidalar: har bir savol va variantlar orasida bo'sh qator qoldiring, "
    "to'g'ri javobdan keyin <b>*</b> belgisini qo'ying. \"Mavzu:\" qatori "
    "ixtiyoriy - uni qo'ysangiz, test mavzularga bo'lib ko'rsatiladi.\n\n"
    "📄 <b>.json formati</b> (dasturchilar uchun):\n"
    '<code>[{"topic":"Kimyo","q":"Suvning formulasi?",'
    '"options":["H2O","CO2","O2","NaCl"],"correct":"H2O"}]</code>\n\n'
    "Faylni yuborgach, Mini-ilovada \"📥 Mening savollarim\" banki paydo "
    "bo'ladi. Qayta fayl yuborsangiz, eski savollar yangisi bilan "
    "almashtiriladi."
)


def main_menu() -> ReplyKeyboardMarkup:
    webapp_url = get_webapp_url()
    if webapp_url:
        # Har safar yangi "versiya" parametri - Telegram sahifani keshdan
        # emas, serverdan qayta yuklab olishi uchun
        versioned_url = f"{webapp_url}?v={int(time.time())}"
        buttons = [
            [KeyboardButton(text="🎮 Testni boshlash", web_app=WebAppInfo(url=versioned_url))]
        ]
    else:
        buttons = []
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


@dp.message(CommandStart())
async def start(message: Message):
    webapp_url = get_webapp_url()
    if webapp_url:
        await message.answer(
            "Salom! Testni boshlash uchun pastdagi tugmani bosing.\n\n"
            "O'zingizning savollaringizni yuklamoqchi bo'lsangiz, "
            "/savol_yukla buyrug'ini yuboring.",
            reply_markup=main_menu(),
        )
    else:
        await message.answer(
            "Salom! Mini-ilova hali sozlanmagan. .env faylida WEBAPP_URL ni "
            "ngrok manzili bilan to'ldiring, so'ng /start ni qayta yuboring."
        )


@dp.message(Command("savol_yukla"))
async def savol_yukla_help(message: Message):
    await message.answer(USER_UPLOAD_HELP, parse_mode="HTML")


@dp.message(F.document)
async def handle_document(message: Message):
    doc = message.document
    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await message.answer("Fayl juda katta (2 MB dan oshmasligi kerak).")
        return

    fname = (doc.file_name or "").lower()
    if not (fname.endswith(".json") or fname.endswith(".txt")):
        await message.answer(
            "Faqat .json yoki .txt fayl qabul qilinadi. Format haqida "
            "/savol_yukla buyrug'ini yuboring."
        )
        return

    tg_file = await bot.get_file(doc.file_id)
    buf = await bot.download_file(tg_file.file_path)
    raw = buf.read().decode("utf-8", errors="ignore")

    try:
        if fname.endswith(".json"):
            items = parse_json_bank(raw)
        else:
            items = parse_text_bank(raw)
    except Exception as e:
        await message.answer(
            f"❌ Faylni o'qib bo'lmadi: {e}\n\nFormat uchun /savol_yukla "
            f"buyrug'ini yuboring."
        )
        return

    if not items:
        await message.answer(
            "❌ Hech qanday to'g'ri formatdagi savol topilmadi. Format "
            "uchun /savol_yukla buyrug'ini yuboring."
        )
        return

    truncated = len(items) > MAX_QUESTIONS
    items = items[:MAX_QUESTIONS]

    uid = message.from_user.id
    out_path = USER_BANKS_DIR / f"{uid}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)

    msg = f"✅ {len(items)} ta savol muvaffaqiyatli yuklandi!"
    if truncated:
        msg += f" (bitta bankda {MAX_QUESTIONS} tagacha savol bo'lishi mumkin, qolganlari olinmadi)"
    msg += (
        "\n\nEndi Mini-ilovani oching va \"📥 Mening savollarim\" bankidan "
        "test ishlang."
    )
    await message.answer(msg)


# ------------------------------------------------------------------ fallback
@dp.message()
async def fallback(message: Message):
    await message.answer(
        "Testni boshlash uchun pastdagi tugmani bosing, yoki /start yuboring.\n"
        "O'z savollaringizni yuklash uchun /savol_yukla buyrug'ini yuboring.",
        reply_markup=main_menu(),
    )


async def start_webapp_server():
    """Mini-ilova fayllarini (index.html, bio.json, chem.json va h.k.)
    mahalliy serverda xizmat qiladi. Buni ngrok orqali internetga
    chiqarasiz (yoki Render kabi hostingga joylaysiz)."""
    @web.middleware
    async def no_cache_middleware(request, handler):
        response = await handler(request)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

    app = web.Application(middlewares=[no_cache_middleware])

    async def index(request):
        return web.FileResponse(WEBAPP_DIR / "index.html")

    async def user_bank_handler(request):
        uid = request.query.get("uid", "")
        if not uid.isdigit():
            return web.json_response([])
        path = USER_BANKS_DIR / f"{uid}.json"
        if not path.exists():
            return web.json_response([])
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return web.json_response([])
        return web.json_response(data)

    app.router.add_get("/", index)
    app.router.add_get("/api/user_bank", user_bank_handler)
    app.router.add_static("/", str(WEBAPP_DIR), show_index=False)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBAPP_PORT)
    await site.start()
    logging.info("Mini-ilova serveri ishga tushdi: http://localhost:%d", WEBAPP_PORT)


async def main():
    if not os.getenv("BOT_TOKEN"):
        logging.warning("DIQQAT: .env faylida BOT_TOKEN yo'q!")
    await start_webapp_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

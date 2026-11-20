import asyncio
import gzip
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
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
ENV_PATH = BASE_DIR / ".env"
# Hosting xizmatlari (Render va boshqalar) PORT nomli muhit o'zgaruvchisini
# o'zi beradi - shuni ustun qo'yamiz, bo'lmasa WEBAPP_PORT yoki 8080.
WEBAPP_PORT = int(os.getenv("PORT") or os.getenv("WEBAPP_PORT", "8080"))

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


def get_webapp_url() -> str:
    """.env faylidan WEBAPP_URL ni har safar qayta o'qiydi (ngrok manzili
    qayta ishga tushirilganda botni qayta yoqmasdan yangilanishi uchun)."""
    values = dotenv_values(ENV_PATH)
    return (values.get("WEBAPP_URL") or os.getenv("WEBAPP_URL") or "").strip()


# Mini-ilovaning o'zi savol banklarini (webapp/*.json) to'g'ridan-to'g'ri
# o'zi o'qiydi - bot tomonida alohida yuklash shart emas, faqat bor-yo'qligini
# va umumiy savollar sonini log uchun tekshiramiz.
_total_savol = 0
for path in sorted(WEBAPP_DIR.glob("*.json")):
    with open(path, encoding="utf-8") as f:
        count = len(json.load(f))
    _total_savol += count
    logging.info("Topildi: %s (%d savol)", path.name, count)
logging.info("Jami bank fayllari savollari: %d", _total_savol)


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
            "Salom! Testni boshlash uchun pastdagi tugmani bosing.",
            reply_markup=main_menu(),
        )
    else:
        await message.answer(
            "Salom! Mini-ilova hali sozlanmagan. .env faylida WEBAPP_URL ni "
            "ngrok manzili bilan to'ldiring, so'ng /start ni qayta yuboring."
        )


# ------------------------------------------------------------------ fallback
@dp.message()
async def fallback(message: Message):
    await message.answer(
        "Testni boshlash uchun pastdagi tugmani bosing, yoki /start yuboring.",
        reply_markup=main_menu(),
    )


_MIME = {".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8"}
_file_cache: Dict[str, tuple] = {}


def _load_file(name: str):
    """Faylni xotiraga oldindan gzip qilib saqlaydi. Fayl o'zgarsa
    (mtime/hajm), qayta o'qiladi - botni qayta yoqish shart emas."""
    path = (WEBAPP_DIR / name).resolve()
    if path.parent != WEBAPP_DIR.resolve() or path.suffix not in _MIME or not path.is_file():
        return None
    st = path.stat()
    key = (st.st_mtime_ns, st.st_size)
    cached = _file_cache.get(name)
    if cached and cached[0] == key:
        return cached
    raw = path.read_bytes()
    entry = (key, raw, gzip.compress(raw, 9), '"%s"' % hashlib.md5(raw).hexdigest(), _MIME[path.suffix])
    _file_cache[name] = entry
    return entry


async def start_webapp_server():
    """Mini-ilova fayllarini (index.html va savol banklari *.json) xizmat
    qiladi. Fayllar gzip bilan siqilib (~4-5 barobar kichik) yuboriladi,
    JSON banklar brauzer keshida saqlanadi (ETag bilan - o'zgarmagan bo'lsa
    qayta yuklanmaydi)."""

    async def serve(request):
        name = request.match_info.get("name") or "index.html"
        entry = _load_file(name)
        if entry is None:
            raise web.HTTPNotFound()
        _, raw, gz, etag, mime = entry
        headers = {"ETag": etag, "Vary": "Accept-Encoding"}
        if name.endswith(".json"):
            headers["Cache-Control"] = "no-cache"
        else:
            headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            headers["Pragma"] = "no-cache"
        if request.headers.get("If-None-Match") == etag:
            return web.Response(status=304, headers=headers)
        body = raw
        if "gzip" in request.headers.get("Accept-Encoding", ""):
            body = gz
            headers["Content-Encoding"] = "gzip"
        headers["Content-Type"] = mime
        return web.Response(body=body, headers=headers)

    app = web.Application()
    app.router.add_get("/", serve)
    app.router.add_get("/{name}", serve)

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

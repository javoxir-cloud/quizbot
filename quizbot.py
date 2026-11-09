import asyncio
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


async def start_webapp_server():
    """Mini-ilova fayllarini (index.html, bio.json, chem.json) mahalliy
    serverda xizmat qiladi. Buni ngrok orqali internetga chiqarasiz."""
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

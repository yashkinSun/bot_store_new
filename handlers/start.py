from aiogram import Router, F
from aiogram.types import Message
from database import get_user_by_telegram_id, add_new_user
from utils.helpers import get_user_language
import json
from pathlib import Path
from keyboards.menu_kb import main_menu_kb

start_router = Router()

@start_router.message(commands=["start"])
async def cmd_start(message: Message):
    user_data = get_user_by_telegram_id(message.from_user.id)
    if not user_data:
        # Новый пользователь
        language = get_user_language(message.from_user)
        add_new_user(message.from_user.id, message.from_user.username or "", language)

    # Определяем язык и берём нужный словарь переводов
    lang_code = get_user_language(message.from_user)
    translations_path = Path(__file__).parent.parent / "translations" / f"{lang_code}.json"
    with open(translations_path, "r", encoding="utf-8") as f:
        t = json.load(f)

    await message.answer(
        text=t["start_greeting"],
        reply_markup=main_menu_kb(t)
    )

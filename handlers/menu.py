import json
from pathlib import Path
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import update_user_language, get_user_by_telegram_id

menu_router = Router()

def load_translations(lang_code: str) -> dict:
    translations_path = Path(__file__).parent.parent / "translations" / f"{lang_code}.json"
    if not translations_path.exists():
        # Если нет файла, по умолчанию en
        lang_code = "en"
        translations_path = Path(__file__).parent.parent / "translations" / "en.json"
    with open(translations_path, "r", encoding="utf-8") as f:
        return json.load(f)

@menu_router.callback_query(F.data == "choose_language")
async def choose_language_callback(call: CallbackQuery):
    """
    Показываем под-меню с выбором языка (ru / en).
    """
    kb = InlineKeyboardBuilder()
    kb.button(text="Русский", callback_data="setlang_ru")
    kb.button(text="English", callback_data="setlang_en")
    kb.button(text="Назад", callback_data="main_menu")  # Кнопка назад
    kb.adjust(1)
    await call.message.edit_text(
        text="Выберите язык / Choose language:",
        reply_markup=kb.as_markup()
    )

@menu_router.callback_query(F.data.startswith("setlang_"))
async def set_language_callback(call: CallbackQuery):
    """
    Устанавливаем язык пользователя (ru или en).
    """
    new_lang = call.data.split("_")[1]  # 'ru' или 'en'
    update_user_language(call.from_user.id, new_lang)

    # Подгружаем новые переводы
    t = load_translations(new_lang)

    # Сообщаем пользователю на выбранном языке
    if new_lang == "ru":
        await call.message.edit_text("Язык изменён!")
    else:
        await call.message.edit_text("Language changed!")

    # Обновляем главное меню, уже на новом языке
    from keyboards.menu_kb import main_menu_kb
    await call.message.answer(
        text=t["main_menu"],
        reply_markup=main_menu_kb(t)
    )

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
# meny keboard
def main_menu_kb(t: dict):
    kb = InlineKeyboardBuilder()
    kb.button(text=t["btn_categories"], callback_data="show_categories")
    kb.button(text=t["btn_about"], callback_data="about_bot")
    kb.button(text=t["btn_profile"], callback_data="show_profile")
    # Новая кнопка для выбора языка:
    kb.button(text=t["btn_language"], callback_data="choose_language")
    kb.adjust(1)
    return kb.as_markup()

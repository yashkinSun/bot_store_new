import json
from pathlib import Path
import sqlite3
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import update_user_language, get_user_by_telegram_id, get_unique_categories
from keyboards.menu_kb import main_menu_kb
from config import DB_PATH
from utils.helpers import get_user_language
from utils.catalog_map import CATEGORY_MAP, REVERSE_CATEGORY_MAP  # Импортируем словари
from handlers.start import show_main_menu  # Функция, отправляющая главное меню с фото

menu_router = Router()

def load_translations(lang_code: str) -> dict:
    translations_path = Path(__file__).parent.parent / "translations" / f"{lang_code}.json"
    if not translations_path.exists():
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
    kb.button(text="Назад", callback_data="main_menu")
    kb.adjust(1)
    text_to_show = "Выберите язык / Choose language:"
    if call.message.text:
        await call.message.edit_text(text=text_to_show, reply_markup=kb.as_markup())
    elif call.message.caption:
        await call.message.edit_caption(caption=text_to_show, reply_markup=kb.as_markup())
    else:
        await call.message.answer(text=text_to_show, reply_markup=kb.as_markup())
    await call.answer()
#Обработчик выбора языка
@menu_router.callback_query(F.data.startswith("setlang_"))
async def set_language_callback(call: CallbackQuery):
    """
    Устанавливаем язык пользователя (ru или en), 
    а затем вызываем show_main_menu, передавая туда call (а не call.message).
    """
    new_lang = call.data.split("_")[1]  # 'ru' или 'en'
    update_user_language(call.from_user.id, new_lang)

    if new_lang == "ru":
        await call.message.answer("Язык изменён!")
    else:
        await call.message.answer("Language changed!")

    # Теперь вызываем show_main_menu(call), а не show_main_menu(call.message)
    await show_main_menu(call)

    await call.answer()


# --- Обработчик для кнопки «Категории» ---
@menu_router.callback_query(F.data == "show_categories")
async def show_categories_callback(call: CallbackQuery):
    """
    Вывод списка категорий из базы данных в виде inline‑клавиатуры.
    """
    categories = get_unique_categories()  # Список display‑имен, например: ["🔑 Ключи", "🛒 Подписки", "🛍️ Разное"]
    if categories:
        kb = InlineKeyboardBuilder()
        for cat in categories:
            # Получаем safe_id через обратный словарь
            safe_id = REVERSE_CATEGORY_MAP.get(cat, cat)
            kb.button(text=cat, callback_data=f"select_category_{safe_id}")
        kb.button(text="Назад", callback_data="main_menu")
        kb.adjust(1)
        if call.message.text:
            await call.message.edit_text("Выберите категорию:", reply_markup=kb.as_markup())
        elif call.message.caption:
            await call.message.edit_caption("Выберите категорию:", reply_markup=kb.as_markup())
        else:
            await call.message.answer("Выберите категорию:", reply_markup=kb.as_markup())
    else:
        if call.message.text:
            await call.message.edit_text("В базе данных нет доступных категорий.")
        elif call.message.caption:
            await call.message.edit_caption("В базе данных нет доступных категорий.")
        else:
            await call.message.answer("В базе данных нет доступных категорий.")
    await call.answer()

# --- Обработчик для кнопки «О боте» ---
@menu_router.callback_query(F.data == "about_bot")
async def about_bot_callback(call: CallbackQuery):
    """
    Вывод информации о боте с фото.
    Если возникает ошибка, логируем её и делаем fallback на текст.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Products")
            product_count = cursor.fetchone()[0]
            cursor.execute("""
                SELECT COUNT(DISTINCT c.display_name)
                FROM Products p
                JOIN Categories c ON p.category_id = c.id
            """)
            category_count = cursor.fetchone()[0]
        text = (
            "Информация о боте: E-Service.ge - Магазин и сервис цифровых товаров и услуг!\n"
            "Мы предлагаем отличное качество по доступной цене\n"
            "✅ Гарантия на все предложения\n"
            "💸 Всегда выгодные цены!\n"
            f"Всего товаров: {product_count}\nУникальных категорий: {category_count}"
        )
    except Exception as e:
        logging.error(f"Ошибка при получении информации о боте: {e}")
        text = "Произошла ошибка при выводе информации о боте."

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В главное меню", callback_data="back_to_menu")
    kb.adjust(1)
    from aiogram.types import FSInputFile
    about_photo_path = Path(__file__).parent.parent / "data" / "about_photo.jpg"
    try:
        photo_file = FSInputFile(str(about_photo_path))
        await call.message.answer_photo(
            photo=photo_file,
            caption=text,
            parse_mode="HTML",
            reply_markup=kb.as_markup()
        )
    except Exception as e:
        logging.error(f"Ошибка отправки фото о боте: {e}")
        await call.message.answer(text, reply_markup=kb.as_markup())
    await call.answer()

# --- Обработчик для кнопки «Профиль» ---
@menu_router.callback_query(F.data == "show_profile")
async def show_profile_callback(call: CallbackQuery):
    """
    Вывод информации о профиле пользователя с фото-иконкой.
    """
    user = get_user_by_telegram_id(call.from_user.id)
    if user:
        balance = user[3]
        username = user[2]
        text = f"Профиль @{username}\nТекущий баланс: {balance} GEL"
    else:
        text = "Пользователь не найден в БД."
    
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В главное меню", callback_data="back_to_menu")
    kb.adjust(1)
    
    from aiogram.types import FSInputFile
    profile_photo_path = Path(__file__).parent.parent / "data" / "profile_icon.jpg"
    try:
        photo_file = FSInputFile(str(profile_photo_path))
        await call.message.answer_photo(
            photo=photo_file,
            caption=text,
            parse_mode="HTML",
            reply_markup=kb.as_markup()
        )
    except Exception as e:
        logging.error(f"Ошибка отправки фото профиля: {e}")
        await call.message.answer(text, reply_markup=kb.as_markup())
    await call.answer()
# Кнопка "назад" во втором слое меню возвращающая в главное меню
@menu_router.callback_query(F.data == "main_menu")
async def back_to_main_menu_callback(call: CallbackQuery):
    """
    Возвращает пользователя в главное меню.
    Передаём в show_main_menu весь call, а не call.message
    """
    await show_main_menu(call)
    await call.answer()

#кнопка "в главное меню" 
@menu_router.callback_query(F.data == "back_to_menu")
async def back_to_menu(call: CallbackQuery):
    """
    Обработчик кнопки "Возврат в меню" – выводит главное меню.
    Аналогично: передаём целиком call.
    """
    await show_main_menu(call)
    await call.answer()



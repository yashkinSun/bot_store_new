import logging
import sqlite3
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import (
    get_unique_categories,      # должна возвращать список display_name (например, ["🔑 Ключи", "🛒 Подписки", "🛍️ Разное"])
    get_unique_subcategories,   # теперь принимает safe_id (например, "keys", "subs", "misc")
    get_products                # теперь принимает safe_id и subcat и делает JOIN с Categories
)
from config import DB_PATH
from utils.catalog_map import CATEGORY_MAP, REVERSE_CATEGORY_MAP  # CATEGORY_MAP: {safe_id: display_name}, REVERSE_CATEGORY_MAP: {display_name: safe_id}

catalog_router = Router()

@catalog_router.callback_query(F.data == "show_categories")
async def show_categories_callback(call: CallbackQuery):
    """
    Шаг 1: Выводим список категорий.
    Каждая кнопка показывает красивое название (display_name), а в callback_data передаётся безопасный идентификатор (safe_id).
    """
    categories = get_unique_categories()  # Ожидается, что эта функция теперь возвращает список display_name
    if categories:
        kb = InlineKeyboardBuilder()
        for cat in categories:
            # По display_name получаем safe_id (если нет – оставляем само display_name)
            safe_id = REVERSE_CATEGORY_MAP.get(cat, cat)
            kb.button(text=cat, callback_data=f"select_category_{safe_id}")
        kb.button(text="Назад", callback_data="main_menu")
        kb.adjust(1)

        text_to_show = "Выберите категорию:"
        if call.message.text:
            await call.message.edit_text(text=text_to_show, reply_markup=kb.as_markup())
        elif call.message.caption:
            await call.message.edit_caption(caption=text_to_show, reply_markup=kb.as_markup())
        else:
            await call.message.answer(text=text_to_show, reply_markup=kb.as_markup())
    else:
        no_cat_text = "В базе нет доступных категорий."
        if call.message.text:
            await call.message.edit_text(no_cat_text)
        elif call.message.caption:
            await call.message.edit_caption(no_cat_text)
        else:
            await call.message.answer(no_cat_text)
    await call.answer()


@catalog_router.callback_query(F.data.startswith("select_category_"))
async def select_category_callback(call: CallbackQuery):
    """
    Шаг 2: Пользователь выбрал категорию.
    Callback_data имеет формат "select_category_{safe_id}".
    Получаем display‑имя для показа и далее по safe_id запрашиваем подкатегории.
    """
    logging.info(f"select_category_callback raw call.data={call.data}")
    safe_id = call.data.split("_", 2)[2]  # Например, "keys"
    # По словарю получаем красивое имя категории
    category_display = CATEGORY_MAP.get(safe_id, safe_id)
    # Получаем подкатегории по safe_id (функция должна учитывать новый внешний ключ)
    subcats = get_unique_subcategories(safe_id)

    kb = InlineKeyboardBuilder()
    for sc in subcats:
        kb.button(text=sc, callback_data=f"selectSubcat_{safe_id}_{sc}")
    kb.button(text="Назад", callback_data="show_categories")
    kb.adjust(1)

    text_to_show = f"Вы выбрали категорию: {category_display}\nВыберите подкатегорию:"
    if call.message.text:
        await call.message.edit_text(text=text_to_show, reply_markup=kb.as_markup())
    elif call.message.caption:
        await call.message.edit_caption(caption=text_to_show, reply_markup=kb.as_markup())
    else:
        await call.message.answer(text=text_to_show, reply_markup=kb.as_markup())
    await call.answer()

#  далее выбор подкатегории
@catalog_router.callback_query(F.data.startswith("selectSubcat_"))
async def select_subcategory_callback(call: CallbackQuery):
    """
    Шаг 3: Пользователь выбрал подкатегорию.
    Callback_data имеет формат "selectSubcat_{safe_id}_{subcat}".
    Используем safe_id для запроса товаров через JOIN.
    """
    logging.info(f"select_subcategory_callback raw call.data={call.data}")
    _, safe_id, subcat = call.data.split("_", 2)
    # Получаем display‑имя категории из словаря
    category_display = CATEGORY_MAP.get(safe_id, safe_id)
    logging.info(f"Parsed safe_id={safe_id} -> category_display={category_display}, subcat={subcat}")

    products = get_products(safe_id, subcat)
    logging.info(f"get_products(safe_id={safe_id}, subcat={subcat}) => {products}")

    if not products:
        empty_text = f"В подкатегории '{subcat}' пока нет товаров."
        if call.message.text:
            await call.message.edit_text(empty_text)
        elif call.message.caption:
            await call.message.edit_caption(empty_text)
        else:
            await call.message.answer(empty_text)
        await call.answer()
        return

    try:
        kb = InlineKeyboardBuilder()
        for (prod_id, name, price, qty) in products:
            button_text = f"{name} — {price} (GEL)"
            logging.info(f"Добавляем кнопку: {button_text} -> select_product_{prod_id}")
            kb.button(text=button_text, callback_data=f"select_product_{prod_id}")
        # Кнопка «Назад» возвращает к выбору категории (используем safe_id)
        kb.button(text="⬅ Назад", callback_data=f"select_category_{safe_id}")
        kb.adjust(1)

        text_response = f"📦 Товары в категории {category_display}, подкатегории {subcat}:"
        logging.info(f"Отправляем сообщение: {text_response}")

        if call.message.text:
            await call.message.edit_text(text=text_response, reply_markup=kb.as_markup())
        elif call.message.caption:
            await call.message.edit_caption(caption=text_response, reply_markup=kb.as_markup())
        else:
            await call.message.answer(text_response, reply_markup=kb.as_markup())
    except Exception as e:
        logging.error(f"Ошибка при обработке товаров в подкатегории {subcat}: {e}")
        if call.message.text:
            await call.message.edit_text("Произошла ошибка при загрузке товаров.")
        elif call.message.caption:
            await call.message.edit_caption("Произошла ошибка при загрузке товаров.")
        else:
            await call.message.answer("Произошла ошибка при загрузке товаров.")
    await call.answer()


@catalog_router.callback_query(F.data.startswith("select_product_"))
async def select_product_callback(call: CallbackQuery):
    import logging
    from aiogram.types import FSInputFile
    prod_id = int(call.data.split("_")[2])
    logging.info(f"select_product_callback: prod_id={prod_id}")

    # Расширяем запрос: теперь выбираем также safe_id и logic_type
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.name, p.description, p.price, p.photo_path, 
                   c.display_name, c.safe_id, p.type, c.logic_type
            FROM Products p
            JOIN Categories c ON p.category_id = c.id
            WHERE p.id = ?
        """, (prod_id,))
        row = cursor.fetchone()

    if not row:
        await call.message.answer("Товар не найден в базе.")
        await call.answer()
        return

    # Распаковываем значения
    name, description, price, photo_path, category_display, safe_id, subcat, logic_type = row

    # Формируем базовый текст описания
    text = f"<b>{name}</b>\n{description}\n\nЦена: {price} GEL\n"
    kb = InlineKeyboardBuilder()

    if logic_type == 'appointment':
        text += "Формат услуги: Запись на услугу"
        kb.button(text="Оставить заявку", callback_data=f"request_service_{prod_id}")
    elif logic_type == 'physical':
        text += "Формат заказа: Доставка или Самовывоз. Оплата: Наличные, Card2Card"
        kb.button(text="Оформить заказ", callback_data=f"order_product_{prod_id}")
    else:
        text += "Формат покупки: Цифровой Товар. После оплаты оператор свяжется с Вами в рабочее время для оказания услуги."
        kb.button(text="Купить", callback_data=f"buy_product_{prod_id}")

    # Кнопка «Назад» возвращает к выбору подкатегории; для этого используем safe_id из таблицы Categories
    kb.button(text="Назад", callback_data=f"selectSubcat_{safe_id}_{subcat}")
    kb.adjust(1)

    # Отправляем фото товара с подписью. Если фото не отправляется, отправляем только текст.
    try:
        photo_file = FSInputFile(photo_path)
        await call.message.answer_photo(
            photo=photo_file,
            caption=text,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка отправки фото товара: {e}")
        await call.message.answer(text, parse_mode="HTML")

    logging.info(f"select_product_callback: name={name}, category_display={category_display}, subcat={subcat}, price={price}, logic_type={logic_type}")

    # Отправляем второе сообщение с кнопками для дальнейших действий
    await call.message.answer(
        text="Что делаем дальше?",
        reply_markup=kb.as_markup()
    )
    await call.answer()

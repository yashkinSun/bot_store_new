import logging
import sqlite3
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from handlers.start import show_main_menu
from config import DB_PATH, ADMIN_ID_ENCRYPTED, DEFAULT_DECRYPT_PASSWORD
from encryption import decrypt_admin_data
from database import get_user_by_telegram_id

order_router = Router()

class OrderFSM(StatesGroup):
    waiting_delivery_choice = State()
    waiting_address = State()

@order_router.callback_query(F.data.startswith("order_product_"))
async def order_product_callback(call: CallbackQuery, state: FSMContext):
    """
    Пользователь выбрал товар для оформления заказа (физический товар).
    Вместо покупки бот выводит варианты: «Оформить доставку», «Забрать самовывозом», «Назад».
    """
    try:
        product_id = int(call.data.split("_")[2])
    except ValueError:
        await call.message.answer("Неверный формат запроса.")
        return

    # Получаем данные о товаре (имя, цену и т.д.) из БД
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.name, p.price, c.display_name
            FROM Products p
            JOIN Categories c ON p.category_id = c.id
            WHERE p.id = ?
        """, (product_id,))
        row = cursor.fetchone()

    if not row:
        await call.message.answer("Товар не найден в базе.")
        await call.answer()
        return

    name, price, category_display = row
    # Сохраняем данные в состоянии
    await state.update_data(product_id=product_id, product_name=name, price=price)

    # Формируем клавиатуру выбора способа оформления заказа
    kb = InlineKeyboardBuilder()
    kb.button(text="Оформить доставку", callback_data="order_delivery")
    kb.button(text="Забрать самовывозом", callback_data="order_selfpickup")
    kb.button(text="Назад", callback_data=f"select_product_{product_id}")
    kb.adjust(1)

    text = (
        f"Вы выбрали товар «{name}»\nЦена: {price} GEL\n\n"
        "Выберите способ оформления заказа:"
    )
    await call.message.answer(text, reply_markup=kb.as_markup())
    await call.answer()

@order_router.callback_query(F.data == "order_delivery")
async def order_delivery_callback(call: CallbackQuery, state: FSMContext):
    """
    Пользователь выбирает доставку.
    Запрашиваем адрес доставки и дату/время.
    """
    await state.set_state(OrderFSM.waiting_address)
    kb = InlineKeyboardBuilder()
    kb.button(text="Назад", callback_data="order_back_to_choice")
    kb.adjust(1)
    await call.message.answer("Введите адрес доставки и удобное время (одним сообщением).", reply_markup=kb.as_markup())
    await call.answer()

@order_router.message(OrderFSM.waiting_address)
async def handle_address(message: Message, state: FSMContext):
    address_info = message.text.strip()
    data = await state.get_data()
    product_name = data.get("product_name", "Товар")
    price = data.get("price", 0)
    
    # Сохраняем заказ в таблицу Purchase
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Purchase (user_id, username, product_id, date)
            VALUES (?, ?, ?, datetime('now'))
        """, (message.from_user.id, message.from_user.username or "", data.get("product_id")))
        conn.commit()
        order_id = cursor.lastrowid

    # Отправка уведомления админу о новом заказе доставки
    try:
        admin_id_decrypted = decrypt_admin_data(ADMIN_ID_ENCRYPTED, DEFAULT_DECRYPT_PASSWORD)
        admin_id = int(admin_id_decrypted.decode("utf-8"))
    except Exception as e:
        logging.error(f"Ошибка дешифрования ADMIN_ID: {e}")
        admin_id = None

    if admin_id:
        order_type = "Доставка"
        user_display = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        admin_text = (
            f"Новый заказ!\n\n"
            f"Тип заказа: {order_type}\n"
            f"Товар: {product_name}\n"
            f"User: {user_display} (id={message.from_user.id})\n"
            f"Адрес доставки: {address_info}"
        )
        await message.bot.send_message(chat_id=admin_id, text=admin_text)
    else:
        logging.error("Администратор не задан (admin_id is None).")

    kb = InlineKeyboardBuilder()
    kb.button(text="В главное меню", callback_data="back_to_menu")
    kb.adjust(1)
    text = (
        f"Ваш заказ оформлен!\n"
        f"Товар: {product_name}\n"
        f"Цена: {price} GEL\n"
        f"Адрес доставки: {address_info}\n"
        f"Номер заказа: {order_id}\n\n"
        "Спасибо за заказ, с вами свяжется оператор."
    )
    await message.answer(text, reply_markup=kb.as_markup())
    await state.clear()

@order_router.callback_query(F.data == "order_selfpickup")
async def order_selfpickup_callback(call: CallbackQuery, state: FSMContext):
    """
    Пользователь выбирает самовывоз.
    Предлагаем подтвердить резерв.
    """
    data = await state.get_data()
    product_name = data.get("product_name", "Товар")
    price = data.get("price", 0)
    kb = InlineKeyboardBuilder()
    kb.button(text="Подтвердить резерв", callback_data="order_confirm_selfpickup")
    kb.button(text="Назад", callback_data=f"select_product_{data.get('product_id')}")
    kb.adjust(1)
    text = (
        f"Вы выбрали товар «{product_name}» с самовывозом.\n"
        "Самовывоз возможен с 12 до 21 ч ежедневно, после подтверждения заказа оператором.\n"
        "Адрес Самовывоза: Батуми, Инасаридзе 13. Ориентир - Додо-Пицца\n"
        "Подтвердите резерв?"
    )
    await call.message.answer(text, reply_markup=kb.as_markup())
    await call.answer()

@order_router.callback_query(F.data == "order_confirm_selfpickup")
async def confirm_selfpickup_callback(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product_name = data.get("product_name", "Товар")
    price = data.get("price", 0)
    # Сохраняем заказ в таблицу Purchase
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Purchase (user_id, username, product_id, date)
            VALUES (?, ?, ?, datetime('now'))
        """, (call.from_user.id, call.from_user.username or "", data.get("product_id")))
        conn.commit()
        order_id = cursor.lastrowid

    # Отправка уведомления админу о новом заказе самовывоза
    try:
        admin_id_decrypted = decrypt_admin_data(ADMIN_ID_ENCRYPTED, DEFAULT_DECRYPT_PASSWORD)
        admin_id = int(admin_id_decrypted.decode("utf-8"))
    except Exception as e:
        logging.error(f"Ошибка дешифрования ADMIN_ID: {e}")
        admin_id = None

    if admin_id:
        order_type = "Самовывоз"
        user_display = f"@{call.from_user.username}" if call.from_user.username else call.from_user.full_name
        admin_text = (
            f"Новый заказ!\n\n"
            f"Тип заказа: {order_type}\n"
            f"Товар: {product_name}\n"
            f"User: {user_display} (id={call.from_user.id})\n"
        )
        await call.message.bot.send_message(chat_id=admin_id, text=admin_text)
    else:
        logging.error("Администратор не задан (admin_id is None).")

    kb = InlineKeyboardBuilder()
    kb.button(text="В главное меню", callback_data="back_to_menu")
    kb.adjust(1)
    text = (
        f"Заказ оформлен!\n"
        f"Товар: {product_name}\n"
        f"Цена: {price} GEL\n"
        f"Номер заказа: {order_id}\n\n"
        "Мы свяжемся с вами в рабочее время."
    )
    await call.message.answer(text, reply_markup=kb.as_markup())
    await state.clear()
    await call.answer()
#возврат к выбору
@order_router.callback_query(F.data == "order_back_to_choice")
async def order_back_to_choice(call: CallbackQuery, state: FSMContext):
    """
    Кнопка "Назад" в состоянии выбора способа оформления заказа.
    Возвращает пользователя к выбору способа (доставка/самовывоз).
    """
    await state.set_state(OrderFSM.waiting_delivery_choice)
    kb = InlineKeyboardBuilder()
    kb.button(text="Оформить доставку", callback_data="order_delivery")
    kb.button(text="Забрать самовывозом", callback_data="order_selfpickup")
    # Возвращаемся к выбору товара
    data = await state.get_data()
    kb.button(text="Назад", callback_data=f"select_product_{data.get('product_id')}")  
    kb.adjust(1)
    await call.message.answer("Выберите способ оформления заказа:", reply_markup=kb.as_markup())
    await call.answer()

@order_router.callback_query(F.data == "appointment_main_menu")
async def go_to_main_menu_from_order(call: CallbackQuery, state: FSMContext):
    """
    Кнопка "В меню": пользователь выходит в главное меню, заказ не сохраняется.
    """
    await state.clear()
    await show_main_menu(call.message)
    await call.answer()

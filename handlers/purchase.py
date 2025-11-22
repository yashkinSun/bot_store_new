from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import get_user_by_telegram_id, update_user_balance
from config import DB_PATH
import sqlite3

purchase_router = Router()

@purchase_router.callback_query(F.data.startswith("buy_product_"))
async def buy_product_callback(call: CallbackQuery):
    """
    1. Пользователь нажал «Купить» (callback_data="buy_product_{prod_id}")
    Проверяем баланс, если хватает -> кнопка «Оплатить с баланса»
    Если не хватает -> «Пополнить баланс».
    """
    product_id = int(call.data.split("_")[2])
    user = get_user_by_telegram_id(call.from_user.id)

    if not user:
        await call.message.answer("Ошибка: пользователь не найден в базе.")
        await call.answer()
        return

    # Извлекаем цену товара
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT price, photo_path, name FROM Products WHERE id=?", (product_id,))
        row = cursor.fetchone()

    if not row:
        await call.message.answer("Ошибка: товар не найден в базе.")
        await call.answer()
        return

    price, photo_path, product_name = row
    user_balance = user[3]  # Индекс 3 = balance (по вашей структуре)

    text = (
        f"Вы выбрали товар: {product_name}\n"
        f"Цена: {price} GEL\n"
        f"Баланс: {user_balance} GEL"
    )

    # Формируем клавиатуру
    kb = InlineKeyboardBuilder()

    if user_balance >= price:
        # Достаточно денег: «Оплатить с баланса» и «Пополнить баланс»
        kb.button(text="Оплатить с баланса", callback_data=f"pay_balance_{product_id}")
    else:
        text += "\nНедостаточно средств."
    # В любом случае кнопка «Пополнить баланс»
    kb.button(text="Пополнить баланс", callback_data="topup_balance")
    # Кнопка «Назад» возвращает на выбор товара
    kb.button(text="Назад", callback_data=f"select_product_{product_id}")
    kb.adjust(1)

    await call.message.answer(text, reply_markup=kb.as_markup())
    await call.answer()


@purchase_router.callback_query(F.data.startswith("pay_balance_"))
async def pay_balance_callback(call: CallbackQuery):
    """
    2. Нажата кнопка «Оплатить с баланса».
    Проверяем ещё раз баланс, предлагаем «Подтвердить покупку» или «Назад».
    """
    product_id = int(call.data.split("_")[2])
    user = get_user_by_telegram_id(call.from_user.id)

    if not user:
        await call.message.answer("Ошибка: пользователь не найден.")
        await call.answer()
        return

    # Повторно берём цену товара
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT price, photo_path, name FROM Products WHERE id=?", (product_id,))
        row = cursor.fetchone()

    if not row:
        await call.message.answer("Товар не найден.")
        await call.answer()
        return

    price, photo_path, product_name = row
    user_balance = user[3]

    if user_balance < price:
        await call.message.answer(
            f"На балансе {user_balance} GEL, товар стоит {price}GEL.\n"
            "Недостаточно средств!"
        )
        await call.answer()
        return

    # Предлагаем «Подтвердить» или «Назад»
    text = (
        f"Товар (Item): {product_name}\n"
        f"Цена (Price): {price}GEL\n"
        f"Баланс (Balance): {user_balance} GEL\n\n"
        "Нажмите «Подтвердить покупку» для списания средств. Press Confirm to pay."
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="Подтвердить покупку (Confirm)", callback_data=f"confirm_purchase_{product_id}")
    kb.button(text="Назад (Back)", callback_data=f"buy_product_{product_id}")
    kb.adjust(1)

    await call.message.answer(text, reply_markup=kb.as_markup())
    await call.answer()


@purchase_router.callback_query(F.data.startswith("confirm_purchase_"))
async def confirm_purchase_callback(call: CallbackQuery):
    product_id = int(call.data.split("_")[2])
    user = get_user_by_telegram_id(call.from_user.id)

    if not user:
        await call.message.answer("Ошибка: пользователь не найден.")
        await call.answer()
        return

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT price, photo_path, name, quantity FROM Products WHERE id=?", (product_id,))
        row = cursor.fetchone()

    if not row:
        await call.message.answer("Товар не найден в базе.")
        await call.answer()
        return

    price, photo_path, product_name, quantity = row
    user_balance = user[3]

    if quantity <= 0:
        await call.message.answer("❌ Ошибка: товар закончился. Попробуйте выбрать другой.")
        await call.answer()
        return

    if user_balance < price:
        await call.message.answer("Недостаточно средств для покупки! Пожалуйста, пополните баланс.")
        await call.answer()
        return

    new_balance = user_balance - price
    new_quantity = quantity - 1

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET balance=? WHERE telegram_id=?", (new_balance, call.from_user.id))
        cursor.execute("UPDATE Products SET quantity=? WHERE id=?", (new_quantity, product_id))
        cursor.execute("""
            INSERT INTO Purchase (user_id, username, product_id, date)
            VALUES (?, ?, ?, datetime('now'))
        """, (call.from_user.id, call.from_user.username, product_id))
        conn.commit()

    # Создаём кнопку "Возврат в меню"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Возврат в меню", callback_data="back_to_menu")]]
    )

    text = (
        f"✅ Покупка подтверждена!\n"
        f"💰 Списано: {price}Y\n"
        ####### f"📦 Остаток товара: {new_quantity} шт.\n"
        f"💳 Новый баланс: {new_balance}GEL\n\n"
        f"🎁 Ваш товар: {product_name}\n\n"
        f"🎧 Оператор свяжется с Вами в рабочее время для оказания услуги\n\n"
        f"Операция завершена. Нажмите для возврата в меню."
    )

    try:
        await call.message.answer_photo(
            photo=open(photo_path, "rb"),
            caption=text,
            reply_markup=keyboard
        )
    except:
        await call.message.answer(f"{text}\n(Не удалось отправить фото)", reply_markup=keyboard)

    await call.answer()

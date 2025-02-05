import logging
import sqlite3

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import DB_PATH
from database import get_balance, update_user_balance

orders_router = Router()

@orders_router.callback_query(F.data.startswith("buy_"))
async def buy_item_callback(call: CallbackQuery):
    prod_id = int(call.data.split("_")[1])
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, price, photo_path, quantity FROM Products WHERE id=?", (prod_id,))
        row = cursor.fetchone()

    if not row:
        await call.answer("Товар не найден.")
        return

    name, price, photo_path, quantity = row
    if quantity <= 0:
        await call.answer("Товар закончился.")
        return

    balance = get_balance(call.from_user.id)
    if balance < price:
        # Показываем кнопку "Назад" (например, назад к списку товаров) + "Пополнить баланс"
        kb = InlineKeyboardBuilder()
        kb.button(text="Пополнить баланс", callback_data="topup_balance")
        kb.button(text="Назад", callback_data="back_to_subcat")
        kb.adjust(1)
        await call.message.edit_text(
            text="Недостаточно средств. Пополните баланс или вернитесь назад.",
            reply_markup=kb.as_markup()
        )
        return

    new_balance = balance - price
    update_user_balance(call.from_user.id, new_balance)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Products SET quantity = quantity - 1 WHERE id=?", (prod_id,))
        cursor.execute("INSERT INTO Purchase (username, product_id, date) VALUES (?, ?, datetime('now'))",
                       (call.from_user.username, prod_id))
        conn.commit()

    try:
        await call.message.answer_photo(
            photo=open(photo_path, "rb"),
            caption=f"Товар: {name}\nСпасибо за покупку! Возвращаемся в главное меню."
        )
        logging.info(f"Пользователь {call.from_user.id} купил товар {name} (prod_id={prod_id}).")
    except Exception as e:
        logging.exception("Ошибка при отправке фото товара пользователю.")
        admin_id = None
        try:
            admin_id = int(call.router.__dict__.get("SUPER_ADMIN_ID", 0))
        except:
            pass
        if admin_id:
            await call.bot.send_message(admin_id, f"Ошибка при отправке файла пользователю {call.from_user.id}. {e}")

        await call.answer("Ошибка при отправке файла. Свяжитесь с администратором.")

    # В конце — возвращаемся в главное меню (без кнопки «Назад», как по условию).
    await call.message.answer("Главное меню", reply_markup=None)
    await call.answer("Покупка оформлена!")

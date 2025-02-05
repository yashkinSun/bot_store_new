import logging
import sqlite3

from aiogram import Router, F
from aiogram.types import Message
from config import DB_PATH

admin_router = Router()
SUPER_ADMIN_ID = None  # Значение будет установлено в bot.py

@admin_router.message(commands=["confirm"])
async def confirm_payment_cmd(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Usage: /confirm <user_id> <amount>")
        return

    user_id = int(parts[1])
    amount = float(parts[2])

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Ищем последнюю запись Payments со статусом 'pending' для данного user_id и amount
            cursor.execute("""
                SELECT id, status 
                FROM Payments 
                WHERE user_id=? AND amount=? AND status='pending'
                ORDER BY id DESC
                LIMIT 1
            """, (user_id, amount))
            row = cursor.fetchone()
            if not row:
                await message.answer("Не найдено платежа со статусом 'pending' для этого пользователя и суммы.")
                return

            payment_id, old_status = row
            cursor.execute("UPDATE Payments SET status='confirmed' WHERE id=?", (payment_id,))

            # Увеличим баланс пользователя на amount
            cursor.execute("SELECT balance FROM Users WHERE telegram_id=?", (user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                await message.answer("Пользователь не найден в БД.")
                return

            old_balance = user_row[0]
            new_balance = old_balance + amount
            cursor.execute("UPDATE Users SET balance=? WHERE telegram_id=?", (new_balance, user_id))
            conn.commit()

        # Уведомим админа и пользователя
        await message.answer(f"Платёж (id={payment_id}) пользователя {user_id} подтверждён. Баланс: {new_balance}Y")
        await message.bot.send_message(user_id, f"Ваш платёж на сумму {amount}Y подтверждён!\nТекущий баланс: {new_balance}Y")
        logging.info(f"Payment #{payment_id} confirmed for user_id={user_id}, new_balance={new_balance}")

    except Exception as e:
        logging.exception("Ошибка при подтверждении платежа.")
        await message.answer(f"Ошибка при подтверждении платежа: {str(e)}")

@admin_router.message(commands=["rejectpay"])
async def reject_payment_cmd(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Usage: /rejectpay <user_id> <amount>")
        return

    user_id = int(parts[1])
    amount = float(parts[2])

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, status
                FROM Payments
                WHERE user_id=? AND amount=? AND status='pending'
                ORDER BY id DESC
                LIMIT 1
            """, (user_id, amount))
            row = cursor.fetchone()
            if not row:
                await message.answer("Нет платежа 'pending' для этого пользователя и суммы.")
                return

            payment_id, old_status = row
            cursor.execute("UPDATE Payments SET status='rejected' WHERE id=?", (payment_id,))
            conn.commit()

        await message.answer(f"Платёж (id={payment_id}) пользователя {user_id} отклонён.")
        await message.bot.send_message(user_id, f"Ваш платёж на сумму {amount}Y отклонён администратором.")
        logging.info(f"Payment #{payment_id} rejected for user_id={user_id}")

    except Exception as e:
        logging.exception("Ошибка при отклонении платежа.")
        await message.answ

import logging
import sqlite3
from aiogram.filters import Command
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import DB_PATH

admin_router = Router()

#
# === Команды /confirm /rejectpay (как было ранее) ===
#
@admin_router.message(Command("confirm"))
async def confirm_payment_cmd(message: Message):
    admin_id = admin_router.__dict__.get("SUPER_ADMIN_ID")
    logging.info(f"Admin command from {message.from_user.id}, SUPER_ADMIN_ID={admin_id}")

    if message.from_user.id != admin_id:
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
            cursor.execute("""
                SELECT id, status 
                FROM Payments 
                WHERE user_id=? AND amount=? AND status='pending'
                ORDER BY id DESC
                LIMIT 1
            """, (user_id, amount))
            row = cursor.fetchone()
            if not row:
                await message.answer("Не найден платеж со статусом 'pending' для этого пользователя и суммы.")
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

        # Создаём кнопку "К покупкам"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="К покупкам", callback_data="back_to_menu")]]
        )

        # Уведомляем пользователя о подтверждении платежа
        await message.bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ Ваш платеж на сумму {amount} GEL подтвержден!\n"
                f"💳 Текущий баланс: {new_balance} GEL"
            ),
            reply_markup=keyboard
        )

        await message.answer(
            f"Платеж (id={payment_id}) пользователя {user_id} подтвержден. "
            f"Баланс: {new_balance}$"
        )
        logging.info(f"Payment #{payment_id} confirmed for user_id={user_id}, new_balance={new_balance}")

    except Exception as e:
        logging.exception("Ошибка при подтверждении платежа.")
        await message.answer(f"Ошибка при подтверждении платежа: {str(e)}")

@admin_router.message(Command("rejectpay"))
async def reject_payment_cmd(message: Message):
    admin_id = admin_router.__dict__.get("SUPER_ADMIN_ID")
    if message.from_user.id != admin_id:
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

        await message.answer(f"Платеж (id={payment_id}) пользователя {user_id} отклонен.")
        await message.bot.send_message(
            chat_id=user_id,
            text=f"Ваш платеж на сумму {amount}Y отклонен администратором."
        )
        logging.info(f"Payment #{payment_id} rejected for user_id={user_id}")

    except Exception as e:
        logging.exception("Ошибка при отклонении платежа.")
        await message.answer(f"Ошибка при отклонении платежа: {str(e)}")

#
# === Обработка инлайн-кнопок "Подтвердить платеж" и "Отклонить платеж" ===
# (callback_data="admin_confirm_<user_id>_<amount>" / "admin_reject_<user_id>_<amount>")
#

@admin_router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm_callback(call: CallbackQuery):
    admin_id = admin_router.__dict__.get("SUPER_ADMIN_ID")
    if call.from_user.id != admin_id:
        # Не админ — игнорируем
        await call.answer()
        return

    try:
        # Формат: "admin_confirm_<user_id>_<amount>"
        parts = call.data.split("_")
        user_id = int(parts[2])
        amount = float(parts[3])

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
                await call.message.answer("Не найден платеж со статусом 'pending' для этого пользователя и суммы.")
                await call.answer()
                return

            payment_id, old_status = row
            cursor.execute("UPDATE Payments SET status='confirmed' WHERE id=?", (payment_id,))

            # Увеличиваем баланс
            cursor.execute("SELECT balance FROM Users WHERE telegram_id=?", (user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                await call.message.answer("Пользователь не найден в БД.")
                await call.answer()
                return

            old_balance = user_row[0]
            new_balance = old_balance + amount
            cursor.execute("UPDATE Users SET balance=? WHERE telegram_id=?", (new_balance, user_id))
            conn.commit()

        # Уведомляем пользователя
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="К покупкам", callback_data="back_to_menu")]]
        )
        await call.bot.send_message(
            chat_id=user_id,
            text=(f"✅ Ваш платеж на сумму {amount} GEL подтвержден!\n"
                  f"💳 Текущий баланс: {new_balance} GEL"),
            reply_markup=keyboard
        )

        await call.message.answer(
            f"Платеж (id={payment_id}) пользователя {user_id} подтвержден. Баланс: {new_balance}$"
        )
        logging.info(f"[Inline] Payment #{payment_id} confirmed for user_id={user_id}, new_balance={new_balance}")

    except Exception as e:
        logging.exception("Ошибка при инлайн-подтверждении платежа (confirm).")
        await call.message.answer(f"Ошибка при подтверждении платежа: {str(e)}")

    await call.answer()

@admin_router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_callback(call: CallbackQuery):
    admin_id = admin_router.__dict__.get("SUPER_ADMIN_ID")
    if call.from_user.id != admin_id:
        await call.answer()
        return

    try:
        parts = call.data.split("_")
        user_id = int(parts[2])
        amount = float(parts[3])

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
                await call.message.answer("Нет платежа 'pending' для этого пользователя и суммы.")
                await call.answer()
                return

            payment_id, old_status = row
            cursor.execute("UPDATE Payments SET status='rejected' WHERE id=?", (payment_id,))
            conn.commit()

        await call.message.answer(f"Платеж (id={payment_id}) пользователя {user_id} отклонён.")
        await call.bot.send_message(
            chat_id=user_id,
            text=f"Ваш платеж на сумму {amount}Y отклонен администратором."
        )
        logging.info(f"[Inline] Payment #{payment_id} rejected for user_id={user_id}")

    except Exception as e:
        logging.exception("Ошибка при инлайн-отклонении платежа (reject).")
        await call.message.answer(f"Ошибка при отклонении платежа: {str(e)}")

    await call.answer()


import os
import logging
import sqlite3

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import DB_PATH, ENCRYPTED_PAYMENT_DETAILS, DEFAULT_DECRYPT_PASSWORD
from encryption import decrypt_payment_details
from database import get_rate
from utils.helpers import format_float

balance_router = Router()

class BalanceFSM(StatesGroup):
    choosing_amount = State()
    choosing_currency = State()
    confirm_payment = State()
    wait_screenshot = State()

def kb_amounts():
    kb = InlineKeyboardBuilder()
    kb.button(text="100Y", callback_data="amount_100")
    kb.button(text="200Y", callback_data="amount_200")
    kb.button(text="300Y", callback_data="amount_300")
    kb.button(text="Назад", callback_data="back_main")
    kb.adjust(1)
    return kb.as_markup()

def kb_currencies():
    kb = InlineKeyboardBuilder()
    kb.button(text="Доллар", callback_data="currency_dollar")
    kb.button(text="Евро", callback_data="currency_euro")
    kb.button(text="Назад", callback_data="back_to_amount")
    kb.adjust(1)
    return kb.as_markup()

def kb_confirm_or_back():
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплачено", callback_data="confirm_done")
    kb.button(text="Назад", callback_data="back_to_currency")
    kb.adjust(1)
    return kb.as_markup()

def kb_wait_screenshot():
    kb = InlineKeyboardBuilder()
    kb.button(text="Назад", callback_data="back_to_confirm")
    kb.adjust(1)
    return kb.as_markup()

@balance_router.callback_query(F.data == "topup_balance")
async def on_start_topup(call: CallbackQuery, state: FSMContext):
    await state.set_state(BalanceFSM.choosing_amount)
    await call.message.edit_text(
        text="Выберите сумму пополнения (Y):",
        reply_markup=kb_amounts()
    )

@balance_router.callback_query(BalanceFSM.choosing_amount, F.data.startswith("amount_"))
async def on_amount_chosen(call: CallbackQuery, state: FSMContext):
    amount_y = int(call.data.split("_")[1])
    await state.update_data(amount=amount_y)
    await state.set_state(BalanceFSM.choosing_currency)
    await call.message.edit_text(
        text=f"Сумма {amount_y}Y выбрана.\nТеперь выберите валюту оплаты:",
        reply_markup=kb_currencies()
    )

@balance_router.callback_query(BalanceFSM.choosing_currency, F.data.startswith("currency_"))
async def on_currency_chosen(call: CallbackQuery, state: FSMContext):
    currency_code = call.data.split("_")[1]  # "dollar" или "euro"
    data = await state.get_data()
    amount_y = data.get("amount", 0)

    if currency_code == "dollar":
        rate = get_rate("USD")
        currency_str = "USD"
    else:
        rate = get_rate("EUR")
        currency_str = "EUR"

    total = amount_y * rate
    await state.update_data(currency=currency_str, total=total)

    try:
        # Расшифровываем реквизиты
        payment_details = decrypt_payment_details(ENCRYPTED_PAYMENT_DETAILS, DEFAULT_DECRYPT_PASSWORD)
    except Exception as e:
        logging.error(f"Ошибка при дешифровании реквизитов: {e}")
        payment_details = "Реквизиты недоступны, свяжитесь с администратором."

    await state.set_state(BalanceFSM.confirm_payment)
    text_ = (
        f"Ты выбрал сумму: {amount_y}Y\n"
        f"К оплате: {format_float(total, 4)} {currency_str}\n"
        f"Отправьте средства на реквизиты: {payment_details}\n"
        f"Затем нажми 'Оплачено'."
    )
    await call.message.edit_text(
        text=text_,
        reply_markup=kb_confirm_or_back()
    )

@balance_router.callback_query(BalanceFSM.confirm_payment, F.data == "confirm_done")
async def on_confirm_done(call: CallbackQuery, state: FSMContext):
    await state.set_state(BalanceFSM.wait_screenshot)
    await call.message.edit_text(
        text="Отправьте скриншот платежа.\nПосле проверки админом баланс будет зачислен.",
        reply_markup=kb_wait_screenshot()
    )

@balance_router.message(BalanceFSM.wait_screenshot, F.photo)
async def handle_screenshot(message: Message, state: FSMContext):
    try:
        photo = message.photo[-1]
        file_id = photo.file_id
        file_bytes = await message.bot.download_file_by_id(file_id)

        screenshot_path = f"data/payments/{message.from_user.id}_{photo.file_unique_id}.jpg"
        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)

        with open(screenshot_path, "wb") as f:
            f.write(file_bytes.getvalue())

        data = await state.get_data()
        amount_y = data.get("amount", 0.0)
        currency = data.get("currency", "USD")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Payments (user_id, amount, currency, status, screenshot_path, date)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (message.from_user.id, amount_y, currency, 'pending', screenshot_path))
            conn.commit()

        await message.answer("Скриншот получен и отправлен администратору на проверку.")
        logging.info(f"Платёж в ожидании: user_id={message.from_user.id}, amount={amount_y}, currency={currency}")

    except Exception as e:
        logging.exception("Ошибка при обработке скриншота или записи в БД.")
        await message.answer("Произошла ошибка при загрузке скриншота. Повторите попытку или свяжитесь с администратором.")

    await state.clear()

# ---- Кнопки "Назад" ----

@balance_router.callback_query(BalanceFSM.choosing_amount, F.data == "back_main")
async def back_to_main_from_amount(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Вы вернулись в главное меню.")

@balance_router.callback_query(BalanceFSM.choosing_currency, F.data == "back_to_amount")
async def back_to_amount(call: CallbackQuery, state: FSMContext):
    await state.set_state(BalanceFSM.choosing_amount)
    await call.message.edit_text(
        text="Выберите сумму пополнения (Y):",
        reply_markup=kb_amounts()
    )

@balance_router.callback_query(BalanceFSM.confirm_payment, F.data == "back_to_currency")
async def back_to_currency(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount_y = data.get("amount", 0)
    await state.set_state(BalanceFSM.choosing_currency)
    await call.message.edit_text(
        text=f"Сумма {amount_y}Y выбрана.\nТеперь выберите валюту оплаты:",
        reply_markup=kb_currencies()
    )

@balance_router.callback_query(BalanceFSM.wait_screenshot, F.data == "back_to_confirm")
async def back_to_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount_y = data.get("amount", 0)
    currency_str = data.get("currency", "USD")
    total = data.get("total", 0.0)
    await state.set_state(BalanceFSM.confirm_payment)
    text_ = (
        f"Ты выбрал сумму: {amount_y}Y\n"
        f"К оплате: {format_float(total, 4)} {currency_str}\n"
        f"Отправьте средства на реквизиты: XXXXX\n"
        f"Затем нажми 'Оплачено'."
    )
    await call.message.edit_text(
        text=text_,
        reply_markup=kb_confirm_or_back()
    )

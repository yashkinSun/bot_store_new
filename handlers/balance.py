import os
import logging
import sqlite3

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, FSInputFile

from config import DB_PATH, DEFAULT_DECRYPT_PASSWORD
from config import LTC_PAYMENT_DETAILS_ENCRYPTED, TRX_PAYMENT_DETAILS_ENCRYPTED
from encryption import decrypt_payment_details, decrypt_admin_data
from database import get_rate
from utils.helpers import format_float

balance_router = Router()

class BalanceFSM(StatesGroup):
    choosing_amount = State()
    entering_custom_amount = State()  # <-- состояние ручного ввода суммы
    choosing_currency = State()
    confirm_payment = State()
    wait_screenshot = State()

def kb_amounts():
    kb = InlineKeyboardBuilder()
    kb.button(text="50 Gel", callback_data="amount_30")
    kb.button(text="100 Gel", callback_data="amount_90")
    kb.button(text="150 Gel", callback_data="amount_180")
    kb.button(text="Указать свою сумму", callback_data="enter_custom_amount")
    kb.button(text="Назад", callback_data="back_main")
    kb.adjust(1)
    return kb.as_markup()

def kb_currencies():
    kb = InlineKeyboardBuilder()
    kb.button(text="Credo Bank (C2C)", callback_data="currency_dollar")
    kb.button(text="Tron (TRX)", callback_data="currency_euro")
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
        text="Выберите сумму пополнения (Gel):",
        reply_markup=kb_amounts()
    )


@balance_router.callback_query(BalanceFSM.choosing_amount, F.data.startswith("amount_"))
async def on_amount_chosen(call: CallbackQuery, state: FSMContext):
    amount_y = int(call.data.split("_")[1])
    await state.update_data(amount=amount_y)
    await state.set_state(BalanceFSM.choosing_currency)
    await call.message.edit_text(
        text=f"Сумма {amount_y} Gel выбрана.\nТеперь выберите валюту оплаты:",
        reply_markup=kb_currencies()
    )


#
# Новый обработчик: Пользователь выбрал "Указать свою сумму"
#
@balance_router.callback_query(BalanceFSM.choosing_amount, F.data == "enter_custom_amount")
async def on_enter_custom_amount(call: CallbackQuery, state: FSMContext):
    """
    Переводим бота в состояние ручного ввода суммы.
    """
    await state.set_state(BalanceFSM.entering_custom_amount)
    kb = InlineKeyboardBuilder()
    kb.button(text="Назад", callback_data="back_to_amount_list")
    kb.adjust(1)

    await call.message.edit_text(
        text="Введите сумму в GEL (только число). Минимальная сумма пополнения 10 GEL",
        reply_markup=kb.as_markup()
    )
    await call.answer()


#
# Обработчик "Назад" из состояния ручного ввода
#
@balance_router.callback_query(BalanceFSM.entering_custom_amount, F.data == "back_to_amount_list")
async def back_to_amount_list(call: CallbackQuery, state: FSMContext):
    await state.set_state(BalanceFSM.choosing_amount)
    await call.message.edit_text(
        text="Выберите сумму пополнения (GEL):",
        reply_markup=kb_amounts()
    )
    await call.answer()


#
# Обработчик текстового сообщения с введённой суммой
#
@balance_router.message(BalanceFSM.entering_custom_amount)
async def handle_custom_amount(message: Message, state: FSMContext):
    text_input = message.text.strip()
    try:
        amount = float(text_input)
    except ValueError:
        await message.answer("❌ Ошибка: введите целое или десятичное число. Попробуйте ещё раз.")
        return

    if amount < 10:
        await message.answer("❌ Минимальная сумма пополнения 10 GEL. Введите сумму заново.")
        return

    # Если всё ок, записываем в FSM и переходим к выбору валюты
    await state.update_data(amount=amount)
    await state.set_state(BalanceFSM.choosing_currency)
    await message.answer(
        text=f"Сумма {amount} GEL выбрана.\nТеперь выберите валюту оплаты:",
        reply_markup=kb_currencies()
    )


@balance_router.callback_query(BalanceFSM.choosing_currency, F.data.startswith("currency_"))
async def on_currency_chosen(call: CallbackQuery, state: FSMContext):
    currency_code = call.data.split("_")[1]  # "dollar" или "euro"
    data = await state.get_data()
    amount_y = data.get("amount", 0)

    if currency_code == "dollar":
        rate = get_rate("USD")
        currency_str = "Credo Bank (C2C)"
        encrypted_details = LTC_PAYMENT_DETAILS_ENCRYPTED
    else:
        rate = get_rate("EUR")
        currency_str = "Tron (TRX)"
        encrypted_details = TRX_PAYMENT_DETAILS_ENCRYPTED

    total = amount_y * rate
    await state.update_data(currency=currency_str, total=total)

    try:
        payment_details = decrypt_payment_details(encrypted_details, DEFAULT_DECRYPT_PASSWORD)
    except Exception as e:
        logging.error(f"Ошибка при дешифровании реквизитов: {e}")
        payment_details = "Реквизиты недоступны, свяжитесь с администратором."

    await state.set_state(BalanceFSM.confirm_payment)
    text_ = (
        f"🏦Ты выбрал сумму: {amount_y} Gel \n"
        f"💵К оплате: {format_float(total, 2)} {currency_str}\n"
        f"🚀Отправьте средства на реквизиты: {payment_details}\n"
        f"✅Затем нажми 'Оплачено'."
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
        file_info = await message.bot.get_file(file_id)
        file_bytes = await message.bot.download_file(file_info.file_path)

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

        # Получаем admin_id через дешифрование
        from config import ADMIN_ID_ENCRYPTED
        from encryption import decrypt_admin_data

        try:
            admin_id_decrypted = decrypt_admin_data(ADMIN_ID_ENCRYPTED, DEFAULT_DECRYPT_PASSWORD)
            admin_id = int(admin_id_decrypted.decode("utf-8"))
        except Exception as e:
            logging.error(f"Ошибка дешифрования ADMIN_ID: {e}")
            admin_id = None

        if admin_id:
            try:
                fs_file = FSInputFile(screenshot_path)
                admin_kb = InlineKeyboardBuilder()
                admin_kb.button(
                    text="Подтвердить платеж",
                    callback_data=f"admin_confirm_{message.from_user.id}_{amount_y}"
                )
                admin_kb.button(
                    text="Отклонить платеж",
                    callback_data=f"admin_reject_{message.from_user.id}_{amount_y}"
                )
                admin_kb.adjust(1)

                await message.bot.send_photo(
                    chat_id=admin_id,
                    photo=fs_file,
                    caption=(
                        f"🆕 <b>Новый платёж!</b>\n"
                        f"👤 Пользователь: <b>{message.from_user.full_name}</b>\n"
                        f"🔢 User ID: <code>{message.from_user.id}</code>\n"
                        f"💰 Сумма: <b>{amount_y} GEL</b>\n"
                        f"💱 Валюта: <b>{currency}</b>"
                    ),
                    parse_mode="HTML",
                    reply_markup=admin_kb.as_markup()
                )
            except Exception as e:
                logging.exception(f"Ошибка при отправке уведомления администратору: {e}")
        else:
            logging.error("Администратор не задан (admin_id is None).")

    except Exception as e:
        logging.exception("Ошибка при обработке скриншота или записи в БД.")
        await message.answer("Произошла ошибка при загрузке скриншота. Повторите попытку или свяжитесь с администратором.")

    await state.clear()

#
# ---- Кнопки "Назад" ----
#
@balance_router.callback_query(BalanceFSM.choosing_amount, F.data == "back_main")
async def back_to_previous_step(call: CallbackQuery, state: FSMContext):
    """
    Возвращает пользователя на предыдущий шаг (к выбору оплаты или пополнения баланса).
    """
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить с баланса", callback_data="pay_balance")
    kb.button(text="Пополнить баланс", callback_data="topup_balance")
    kb.button(text="⬅️ В главное меню", callback_data="back_to_main_menu")
    kb.adjust(1)

    await call.message.edit_text(
        "Вы вернулись на предыдущий шаг.\nВыберите способ оплаты:",
        reply_markup=kb.as_markup()
    )


@balance_router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu(call: CallbackQuery, state: FSMContext):
    """
    Полностью выходит из взаимодействия и отправляет главное меню.
    """
    await state.clear()
    from keyboards.menu_kb import main_menu_kb
    from utils.helpers import get_user_language
    from pathlib import Path
    import json

    lang_code = get_user_language(call.from_user)
    translations_path = Path(__file__).parent.parent / "translations" / f"{lang_code}.json"
    with open(translations_path, "r", encoding="utf-8") as f:
        t = json.load(f)

    await call.message.edit_text(
        text=t["start_greeting"],
        reply_markup=main_menu_kb(t)
    )


@balance_router.callback_query(BalanceFSM.choosing_currency, F.data == "back_to_amount")
async def back_to_amount(call: CallbackQuery, state: FSMContext):
    await state.set_state(BalanceFSM.choosing_amount)
    await call.message.edit_text(
        text="Выберите сумму пополнения (Gel):",
        reply_markup=kb_amounts()
    )


@balance_router.callback_query(BalanceFSM.confirm_payment, F.data == "back_to_currency")
async def back_to_currency(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount_y = data.get("amount", 0)
    await state.set_state(BalanceFSM.choosing_currency)
    await call.message.edit_text(
        text=f"Сумма {amount_y} Gel выбрана.\nТеперь выберите валюту оплаты:",
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
        f"Ты выбрал сумму: {amount_y}Gel\n"
        f"К оплате: {format_float(total, 2)} {currency_str}\n"
        f"Отправьте средства на реквизиты: XXXXX\n"
        f"Затем нажми 'Оплачено'."
    )
    await call.message.edit_text(
        text=text_,
        reply_markup=kb_confirm_or_back()
    )


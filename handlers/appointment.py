import logging
import sqlite3
import os

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pathlib import Path

from config import DB_PATH, ADMIN_ID_ENCRYPTED, DEFAULT_DECRYPT_PASSWORD
from encryption import decrypt_admin_data
from database import get_user_by_telegram_id
from handlers.start import show_main_menu  # Функция для отображения главного меню

appointment_router = Router()

class AppointmentFSM(StatesGroup):
    waiting_description = State()
    waiting_confirmation = State()

@appointment_router.callback_query(F.data.startswith("request_service_"))
async def start_service_appointment(call: CallbackQuery, state: FSMContext):
    """
    Пользователь нажал кнопку «Оставить заявку» для услуги.
    Callback_data: "request_service_{product_id}"
    Получаем product_id и через запрос в БД – название услуги.
    Затем отправляем запрос с текстом, в который встроено название услуги,
    и добавляем кнопку «Отмена» для выхода из процесса заявки.
    """
    data_parts = call.data.split("_", 2)
    product_id = data_parts[2]
    logging.info(f"[start_service_appointment] product_id={product_id}")

    # Запрашиваем имя услуги из таблицы Products
    service_name = None
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM Products WHERE id = ?", (product_id,))
            row = cursor.fetchone()
            if row:
                service_name = row[0]
    except Exception as e:
        logging.exception("Ошибка при получении имени услуги")
        service_name = "Услуга"

    # Сохраняем product_id и service_name в FSM
    await state.update_data(product_id=product_id, service_name=service_name)

    # Формируем клавиатуру с кнопкой "Отмена"
    kb = InlineKeyboardBuilder()
    kb.button(text="Отмена", callback_data="appointment_cancel")
    kb.adjust(1)

    text_prompt = (
        f"Вы выбрали услугу «{service_name}».\n"
        "Опишите, пожалуйста, вашу проблему или вопрос.\n"
        "Сообщение можно отправить одним сообщением."
    )

    await state.set_state(AppointmentFSM.waiting_description)
    try:
        await call.message.edit_text(text=text_prompt, reply_markup=kb.as_markup())
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        await call.message.answer(text=text_prompt, reply_markup=kb.as_markup())
    await call.answer()

@appointment_router.message(AppointmentFSM.waiting_description)
async def handle_user_description(message: Message, state: FSMContext):
    """
    Обработка текстового сообщения с описанием услуги.
    После ввода текста предлагаем варианты: "Подтвердить", "Редактировать" и "Отмена".
    """
    user_description = message.text.strip()
    data = await state.get_data()
    service_name = data.get("service_name", "Услуга")
    await state.update_data(description=user_description)

    kb = InlineKeyboardBuilder()
    kb.button(text="Подтвердить", callback_data="confirm_appointment")
    kb.button(text="Редактировать", callback_data="appointment_edit")
    kb.button(text="Отмена", callback_data="appointment_cancel")
    kb.adjust(1)

    text_confirm = (
        f"Вы выбрали услугу «{service_name}».\n"
        "Ниже ваш текст заявки:\n\n"
        f"«{user_description}»\n\n"
        "Подтвердить заявку?"
    )

    await state.set_state(AppointmentFSM.waiting_confirmation)
    await message.answer(text_confirm, reply_markup=kb.as_markup())

@appointment_router.callback_query(AppointmentFSM.waiting_confirmation, F.data == "appointment_edit")
async def edit_appointment_description(call: CallbackQuery, state: FSMContext):
    """
    Кнопка «Редактировать»: позволяет изменить введённый текст заявки.
    """
    prompt_text = "Отправьте новое описание вашей ситуации (предыдущее будет перезаписано):"
    await state.set_state(AppointmentFSM.waiting_description)
    try:
        await call.message.edit_text(prompt_text)
        logging.info("Описание заявки успешно отредактировано.")
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        await call.message.answer(prompt_text)
    await call.answer()
#Отмена и возврат к стартовому меню 
@appointment_router.callback_query(F.data == "appointment_cancel")
async def cancel_appointment(call: CallbackQuery, state: FSMContext):
    """
    Кнопка «Отмена»: отменяет заявку и возвращает пользователя в главное меню.
    Вместо вызова cmd_start() вызываем аналогичную логику, как в разделе "Профиль",
    чтобы отправить новое сообщение с приветственным фото и кнопкой возврата в меню.
    """
    await state.clear()
    
    # Формируем клавиатуру с кнопкой "⬅️ В главное меню"
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В главное меню", callback_data="back_to_menu")
    kb.adjust(1)
    
    # Определяем путь к приветственному фото
    welcome_photo_path = Path(__file__).parent.parent / "data" / "welcome.jpg"
    try:
        photo_file = FSInputFile(str(welcome_photo_path))
        # Отправляем фото с подписью (например, можно задать текст "Возврат в главное меню")
        await call.message.answer_photo(
            photo=photo_file,
            caption="Возврат в главное меню",
            parse_mode="HTML",
            reply_markup=kb.as_markup()
        )
    except Exception as e:
        logging.error(f"Ошибка отправки фото в appointment_cancel: {e}")
        await call.message.answer(
            "Возврат в главное меню",
            reply_markup=kb.as_markup()
        )
    await call.answer()
@appointment_router.callback_query(AppointmentFSM.waiting_confirmation, F.data == "confirm_appointment")
async def confirm_appointment_callback(call: CallbackQuery, state: FSMContext):
    """
    Пользователь подтверждает заявку.
    Сохраняем заявку в таблицу appointments_requests и уведомляем админа.
    В уведомлении вместо product_id выводим название услуги.
    """
    data = await state.get_data()
    product_id = data.get("product_id")
    service_name = data.get("service_name", "Услуга")
    user_description = data.get("description", "")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO appointments_requests (user_id, product_id, description, status, date)
                VALUES (?, ?, ?, 'pending', datetime('now'))
                """,
                (call.from_user.id, product_id, user_description)
            )
            conn.commit()
            appointment_id = cursor.lastrowid
    except Exception as e:
        logging.exception("Ошибка при сохранении заявки в БД.")
        await call.message.answer("Ошибка при сохранении заявки. Попробуйте позже.")
        await state.clear()
        return

    try:
        admin_id_decrypted = decrypt_admin_data(ADMIN_ID_ENCRYPTED, DEFAULT_DECRYPT_PASSWORD)
        admin_id = int(admin_id_decrypted.decode("utf-8"))
    except Exception as e:
        logging.error(f"[confirm_appointment_callback] Ошибка дешифрования ADMIN_ID: {e}")
        admin_id = None

    if admin_id:
        try:
            user_info = call.from_user.username or call.from_user.full_name
            text_for_admin = (
                f"Новая заявка на услугу!\n\n"
                f"User: @{user_info} (id={call.from_user.id})\n"
                f"Услуга: {service_name}\n"
                f"Appointment ID: {appointment_id}\n\n"
                f"Сообщение:\n{user_description}"
            )
            await call.message.bot.send_message(chat_id=admin_id, text=text_for_admin)
        except Exception as e:
            logging.exception(f"Ошибка при отправке заявки админу: {e}")
    else:
        logging.error("Администратор не задан (admin_id is None).")

    kb_user = InlineKeyboardBuilder()
    kb_user.button(text="В главное меню", callback_data="back_to_menu")
    kb_user.adjust(1)
    await call.message.answer(
        f"Ваша заявка на услугу «{service_name}» принята! Мы свяжемся с вами в рабочее время.",
        reply_markup=kb_user.as_markup()
    )
    await state.clear()
    await call.answer()

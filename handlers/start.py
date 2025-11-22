from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputFile
from aiogram.types import FSInputFile
from aiogram.filters import Command  # Импорт Command для aiogram 3.x
from database import get_user_by_telegram_id, add_new_user
from utils.helpers import get_user_language
import json
from pathlib import Path
from keyboards.menu_kb import main_menu_kb
import logging

start_router = Router()

@start_router.message(Command("start"))
async def cmd_start(message: Message):
    # 1) Логируем вход в handler и базовые данные из объекта message
    logging.info(
        f"[cmd_start] Начало обработки /start\n"
        f" message_id={message.message_id}, "
        f" from_user_id={message.from_user.id}, "
        f" username={message.from_user.username}, "
        f" language_code={message.from_user.language_code}"
    )

    # 2) Пытаемся получить пользователя из базы
    user_data = get_user_by_telegram_id(message.from_user.id)
    logging.info(f"[cmd_start] get_user_by_telegram_id => {user_data}")

    # 3) Если пользователь не найден, записываем нового
    if not user_data:
        language = get_user_language(message.from_user)
        logging.info(f"[cmd_start] Новый пользователь, get_user_language вернул: {language}")
        add_new_user(message.from_user.id, message.from_user.username or "", language)
        logging.info(f"[cmd_start] add_new_user(telegram_id={message.from_user.id}, language={language}) выполнен")

    # 4) Ещё раз определяем язык из базы (или через fallback)
    lang_code = get_user_language(message.from_user)
    logging.info(f"[cmd_start] Итоговый язык для пользователя {message.from_user.id}: {lang_code}")

    # 5) Загружаем JSON-файл перевода
    translations_path = Path(__file__).parent.parent / "translations" / f"{lang_code}.json"
    logging.info(f"[cmd_start] Загружаем переводы из файла {translations_path}")
    with open(translations_path, "r", encoding="utf-8") as f:
        t = json.load(f)

    # 6) Путь к приветственному фото
    welcome_photo_path = Path(__file__).parent.parent / "data" / "welcome.jpg"
    logging.info(f"[cmd_start] Пытаемся отправить фото из: {welcome_photo_path.resolve()}")

    try:
        photo_file = FSInputFile(str(welcome_photo_path))
        await message.answer_photo(
            photo=photo_file,
            caption=t["start_greeting"],
            parse_mode="HTML",
            reply_markup=main_menu_kb(t)
        )
        logging.info("[cmd_start] Фото отправлено успешно")
    except Exception as e:
        logging.error(f"Ошибка отправки приветственного фото: {e}")
        # Если фото не отправляется, просто отправляем текст
        await message.answer(
            text=t["start_greeting"],
            reply_markup=main_menu_kb(t)
        )
        logging.info("[cmd_start] Фото не отправлено, отправлен текст")

    # 7) Логируем завершение
    logging.info("[cmd_start] Завершение обработки /start")

async def show_main_menu(call: CallbackQuery):
    """
    Универсальная функция для отображения главного меню,
    принимаем сам CallbackQuery (у него есть call.from_user, call.message.chat, и т.п.).
    """

    # Реальный ID пользователя (тот, кто нажал кнопку)
    user_id = call.from_user.id

    # Получаем язык из БД или fallback
    lang_code = get_user_language(call.from_user)  # <-- Теперь вызов без проблемы ID бота
    translations_path = Path(__file__).parent.parent / "translations" / f"{lang_code}.json"
    with open(translations_path, "r", encoding="utf-8") as f:
        t = json.load(f)

    # Приветственное фото
    welcome_photo_path = Path(__file__).parent.parent / "data" / "welcome.jpg"
    logging.info(f"[show_main_menu] Отправка фото {welcome_photo_path} для user_id={user_id}")

    try:
        photo_file = FSInputFile(str(welcome_photo_path))
        # Вызываем answer_photo от имени того же чата,
        # но через call.message (у него есть chat_id = call.message.chat.id)
        await call.message.answer_photo(
            photo=photo_file,
            caption=t["start_greeting"],
            parse_mode="HTML",
            reply_markup=main_menu_kb(t)
        )
    except Exception as e:
        logging.error(f"[show_main_menu] Ошибка отправки фото: {e}")
        await call.message.answer(
            text=t["start_greeting"],
            reply_markup=main_menu_kb(t)
        )
# обновленная кнопка бэк ту меню
@start_router.callback_query(F.data == "back_to_menu")
async def back_to_menu(call: CallbackQuery):
    await show_main_menu(call)
    await call.answer()
from aiogram.types import User
from database import get_user_by_telegram_id
import logging

def get_user_language(user: User) -> str:
    db_user = get_user_by_telegram_id(user.id)
    if db_user:
        db_lang = db_user[4]  # индекс 4 = поле language
        if db_lang:
            # Логируем и нормализуем
            logging.info(f"[get_user_language] Для пользователя {user.id} БД вернула язык='{db_lang}'")
            db_lang = db_lang.strip().lower()
            logging.info(f"[get_user_language] Нормализованное значение='{db_lang}'")
            if db_lang in ["ru", "en"]:
                return db_lang  # <-- если нормализованный язык подходит
    # fallback
    logging.info(f"[get_user_language] fallback, user.language_code={user.language_code}")
    # user.language_code может быть None или, например, "uk"
    if user.language_code in ["ru", "uk"]:
        return "ru"
    return "en"
    
def format_float(value, decimals):
    try:
        if isinstance(value, str):
            value = float(value.replace(",", "."))
        else:
            value = float(value)
    except Exception:
        value = 0.0
    return f"{value:.{decimals}f}"

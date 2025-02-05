from aiogram.types import User

def get_user_language(user: User) -> str:
    """
    Если user.language_code == 'ru' или 'uk', то используем 'ru', иначе 'en'.
    """
    lang_code = user.language_code
    if lang_code in ['ru', 'uk']:
        return 'ru'
    return 'en'

def format_float(value: float, decimals: int = 4) -> str:
    """
    Форматирование с нужным количеством знаков после запятой.
    Например, format_float(12.3456789) -> '12.3457'
    """
    return f"{value:.{decimals}f}"

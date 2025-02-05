from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def payment_amount_kb():
    """
    Пример: суммы в Y: 100, 200, 300
    """
    kb = InlineKeyboardBuilder()
    kb.button(text="100Y", callback_data="amount_100")
    kb.button(text="200Y", callback_data="amount_200")
    kb.button(text="300Y", callback_data="amount_300")
    kb.adjust(1)
    return kb.as_markup()

def payment_currency_kb(translations: dict):
    """
    Выбор способа оплаты: Доллар/Евро
    """
    kb = InlineKeyboardBuilder()
    kb.button(text=translations["btn_dollar"], callback_data="pay_dollar")
    kb.button(text=translations["btn_euro"], callback_data="pay_euro")
    kb.adjust(2)
    return kb.as_markup()

def payment_confirm_kb(translations: dict):
    """
    Кнопки 'Оплачено' и 'Отменить'
    """
    kb = InlineKeyboardBuilder()
    kb.button(text=translations["pay_done"], callback_data="pay_done")
    kb.button(text=translations["cancel"], callback_data="cancel_pay")
    kb.adjust(2)
    return kb.as_markup()

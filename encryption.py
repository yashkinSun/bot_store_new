from cryptography.fernet import Fernet
from config import get_fernet, DEFAULT_DECRYPT_PASSWORD

def decrypt_admin_data(encrypted_data: bytes, password: str) -> bytes:
    if password != DEFAULT_DECRYPT_PASSWORD:
        raise ValueError("Неверный пароль для дешифрования административных данных.")
    f = get_fernet()
    return f.decrypt(encrypted_data)

def decrypt_payment_details(encrypted_details: bytes, password: str) -> str:
    """
    Расшифровываем реквизиты для оплаты (строка).
    """
    if password != DEFAULT_DECRYPT_PASSWORD:
        raise ValueError("Неверный пароль для дешифрования реквизитов.")
    f = get_fernet()
    decrypted = f.decrypt(encrypted_details)
    return decrypted.decode("utf-8")

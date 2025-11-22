import os
from pathlib import Path
from cryptography.fernet import Fernet

# Зашифрованный admin_id
ADMIN_ID_ENCRYPTED = b"gAAAAABnoxWJ9QLyCHT8phiv4OYZ9kgSMuv25O1uA1WsnTN20gc49cHs99tfxfy_0J-vEZSA82G6PQApNj4kFVdvDlHbuVp04w=="  

# Пароль для расшифровки
DEFAULT_DECRYPT_PASSWORD = "kerasys854"

# Токен бота
API_TOKEN = "7534771450:AAFNi_QQy2d1WhdbImr98fsCfbaVJ5a742Y"

# Путь к ключу
SECRET_KEY_PATH = str(Path(__file__).parent / "secret.key")

# Путь к БД  (SQLite)
DB_PATH = str(Path(__file__).parent / "bot_store.sqlite3")

# -- Зашифрованные реквизиты для оплаты (пример) --
# Чтобы получить это значение, офлайн:
#   from cryptography.fernet import Fernet
#   f = Fernet(<ключ>)
#   encrypted = f.encrypt(b"PAYMENT_DETAILS")
# Здесь подставляем результат в виде b"..."
# Зашифрованные реквизиты для LTC
LTC_PAYMENT_DETAILS_ENCRYPTED = b"gAAAAABnrEK4zkWHX2DeloeADTRGok9RHIkBzav_7yzOoBYeEaqqEovgdm44xtPeVIGhEFxIhIPHxgSdvoQKyZ0yopIyg-buw0vLN4A9mLl3fiah7M1u6-WXoQlZgPwU6-NpwN6gsHHQ"

# Зашифрованные реквизиты для TRX
TRX_PAYMENT_DETAILS_ENCRYPTED = b"gAAAAABnrEK4rzEY2BE31Qolepx2-W2fqzaRUYIFdmAL-W-tcEjx4gygFn6pMdDZkxw528Jp9AFxhhH-cDH7-vRNZXSjNMDUrIAgH2u3NT0yzr2eYSx68APnwiLQj5Q-yP236u0E07kdUo2syFipv8233Lp_lPM86uKru98alLPMFvSsGTqg_5Y="
def get_fernet() -> Fernet:
    with open(SECRET_KEY_PATH, 'rb') as key_file:
        key = key_file.read()
    return Fernet(key)

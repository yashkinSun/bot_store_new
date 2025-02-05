import os
from pathlib import Path
from cryptography.fernet import Fernet

# Зашифрованный admin_id
ADMIN_ID_ENCRYPTED = b"gAAAAABnoxWJ9QLyCHT8phiv4OYZ9kgSMuv25O1uA1WsnTN20gc49cHs99tfxfy_0J-vEZSA82G6PQApNj4kFVdvDlHbuVp04w=="  

# Пароль для расшифровки
DEFAULT_DECRYPT_PASSWORD = "kerasys854"

# Токен бота
API_TOKEN = "7829146035:AAEFaDtf8bSTK39PooaQ2okcDvcUcSbhnnc"

# Путь к ключу
SECRET_KEY_PATH = str(Path("/etc/bot_store/secret.key"))

# Путь к БД (SQLite)
DB_PATH = str(Path(__file__).parent / "bot_store.sqlite3")

# -- Зашифрованные реквизиты для оплаты (пример) --
# Чтобы получить это значение, офлайн:
#   from cryptography.fernet import Fernet
#   f = Fernet(<ключ>)
#   encrypted = f.encrypt(b"PAYMENT_DETAILS")
# Здесь подставляем результат в виде b"..."
ENCRYPTED_PAYMENT_DETAILS = b"gAAAAABnoxSUzJQyi48mxpHnhNClpTbk4lXqynU-XhbijSWUOXTYNyXkGOmE4OiArNkiAUgv_FAQStDrJHRHAmYw-RwtLAG_2qUSgD3ZkiRMMNUGOk5XzYFNtraE-y6CNCN6E7A3SSTB0PZr_qcK4cl2HGJfBWnwHg=="

def get_fernet() -> Fernet:
    with open(SECRET_KEY_PATH, 'rb') as key_file:
        key = key_file.read()
    return Fernet(key)

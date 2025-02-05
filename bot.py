import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage  # <-- добавляем
from config import API_TOKEN, ADMIN_ID_ENCRYPTED, DEFAULT_DECRYPT_PASSWORD
from encryption import decrypt_admin_data
from handlers.start import start_router
from handlers.menu import menu_router
from handlers.orders import orders_router
from handlers.balance import balance_router
from handlers.admin import admin_router, SUPER_ADMIN_ID
from database import init_db, initialize_demo_products

logging.basicConfig(level=logging.INFO)

async def main():
    try:
        admin_id_decrypted = decrypt_admin_data(ADMIN_ID_ENCRYPTED, DEFAULT_DECRYPT_PASSWORD)
        actual_admin_id = int(admin_id_decrypted.decode("utf-8"))
    except ValueError:
        logging.error("Неверный пароль для дешифрования ADMIN_ID!")
        return
    except Exception as e:
        logging.error(f"Ошибка дешифрования ADMIN_ID: {e}")
        return

    # Передаём расшифрованный ID в модуль admin.py
    SUPER_ADMIN_ID = actual_admin_id
    admin_router.__dict__["SUPER_ADMIN_ID"] = SUPER_ADMIN_ID

    # Включаем in-memory-хранилище FSM
    bot = Bot(token=API_TOKEN, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())

    init_db()
    initialize_demo_products()

    # Роутеры
    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(orders_router)
    dp.include_router(balance_router)
    dp.include_router(admin_router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import API_TOKEN
from handlers.start import start_router
from handlers.menu import menu_router
from handlers.orders import orders_router
from handlers.balance import balance_router
from handlers.admin import admin_router
from database import init_db

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=API_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    # Инициализация БД
    init_db()

    # Регистрация роутеров
    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(orders_router)
    dp.include_router(balance_router)
    dp.include_router(admin_router)

    # Запуск поллинга
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

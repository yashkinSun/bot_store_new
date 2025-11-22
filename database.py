import sqlite3
from contextlib import closing
from config import DB_PATH
import logging

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            telegram_username TEXT,
            balance REAL DEFAULT 0,
            language TEXT
        )
        """)

        # Новая таблица категорий
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            safe_id TEXT UNIQUE,
            display_name TEXT
        )
        """)

        # Таблица товаров/услуг с внешним ключом на Categories
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            type TEXT,
            name TEXT,
            description TEXT,
            price REAL,
            photo_path TEXT,
            quantity INTEGER,
            FOREIGN KEY(category_id) REFERENCES Categories(id)
        )
        """)

        # Таблица платежей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            currency TEXT,
            status TEXT,
            screenshot_path TEXT,
            date TEXT
        )
        """)

        # Таблица покупок
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Purchase (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            product_id INTEGER,
            date TEXT
        )
        """)

        # Таблица курсов валют
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS RatesY (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency TEXT,
            rate_to_y REAL
        )
        """)

        conn.commit()

def get_user_by_telegram_id(telegram_id: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        logging.info(f"[get_user_by_telegram_id] row={row} for telegram_id={telegram_id}")
        return row

def add_new_user(telegram_id: int, username: str, language: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Users (telegram_id, telegram_username, language) VALUES (?, ?, ?)",
                       (telegram_id, username, language))
        conn.commit()

def get_balance(telegram_id: int) -> float:
    user = get_user_by_telegram_id(telegram_id)
    if user:
        return user[3]
    return 0.0

def update_user_balance(telegram_id: int, new_balance: float):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET balance = ? WHERE telegram_id = ?", (new_balance, telegram_id))
        conn.commit()

def get_rate(currency: str) -> float:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT rate_to_y FROM RatesY WHERE currency = ?", (currency,))
        row = cursor.fetchone()
        if row:
            rate_str = str(row[0]).replace(",", ".")
            try:
                rate_val = float(rate_str)
            except ValueError:
                logging.error(f"Некорректный формат курса: {row[0]}")
                return 1.0
            return rate_val
        else:
            return 1.0

def get_unique_categories() -> list[str]:
    """
    Возвращает список display_name категорий, для которых есть товары с quantity > 0.
    """
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT c.display_name
            FROM Products p
            JOIN Categories c ON p.category_id = c.id
            WHERE p.quantity > 0
        """)
        rows = cursor.fetchall()
        return [r[0] for r in rows]

def get_unique_subcategories(category_safe_id: str) -> list[str]:
    """
    Возвращает список уникальных подкатегорий (p.type) для товаров,
    где категория соответствует заданному safe_id.
    """
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT p.type
            FROM Products p
            JOIN Categories c ON p.category_id = c.id
            WHERE c.safe_id = ? AND p.quantity > 0
        """, (category_safe_id,))
        rows = cursor.fetchall()
        return [r[0] for r in rows]

def get_products(category_safe_id: str, subcat: str) -> list[tuple]:
    import logging
    logging.info(f"get_products(category_safe_id={category_safe_id}, subcat={subcat}) called")
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, p.price, p.quantity
            FROM Products p
            JOIN Categories c ON p.category_id = c.id
            WHERE c.safe_id = ? AND p.type = ? AND p.quantity > 0
        """, (category_safe_id, subcat))
        rows = cursor.fetchall()
    logging.info(f"get_products => {rows}")
    return rows

def initialize_demo_products():
    """
    Заполняет таблицу Products демонстрационными данными, если в ней нет записей.
    Для каждой категории (по safe_id) вставляются товары с подкатегориями.
    Предполагается, что в таблице Categories уже есть записи с safe_id: 'keys', 'subs', 'misc', 'services'
    """
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Products")
        count = cursor.fetchone()[0]
        if count > 0:
            return

        # Пример safe_id для существующих категорий
        safe_ids = ["keys", "subs", "misc"]
        subcategories = ["Bronze", "Silver", "Platinum"]
        product_names = ["One", "Two", "Three"]
        price = 100.0
        quantity = 10
        photo_path = "data/orders/sample.jpg"

        for safe in safe_ids:
            for subcat in subcategories:
                for pname in product_names:
                    cursor.execute(
                        """
                        INSERT INTO Products (category_id, type, name, description, price, photo_path, quantity)
                        VALUES (
                            (SELECT id FROM Categories WHERE safe_id = ?),
                            ?, ?, ?, ?, ?, ?
                        )
                        """,
                        (safe, subcat, pname, f"Описание для {pname}", price, photo_path, quantity)
                    )
        conn.commit()

def update_user_language(telegram_id: int, language: str):
    from contextlib import closing
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET language = ? WHERE telegram_id = ?", (language, telegram_id))
        conn.commit()
        logging.info(f"Обновлен язык для {telegram_id}: {language}")

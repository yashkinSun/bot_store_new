import sqlite3
from contextlib import closing
from config import DB_PATH

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            telegram_username TEXT,
            balance REAL DEFAULT 0,
            language TEXT
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            type TEXT,
            name TEXT,
            description TEXT,
            price REAL,
            photo_path TEXT,
            quantity INTEGER
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            currency TEXT,
            status TEXT,
            screenshot_path TEXT,
            date TEXT
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Purchase (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            product_id INTEGER,
            date TEXT
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS RatesY (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency TEXT,
            rate_to_y REAL
        )""")

        conn.commit()

def get_user_by_telegram_id(telegram_id: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE telegram_id = ?", (telegram_id,))
        return cursor.fetchone()

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
            return row[0]
        else:
            return 1.0

def get_unique_categories() -> list[str]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM Products WHERE quantity > 0")
        rows = cursor.fetchall()
        return [r[0] for r in rows]

def get_unique_subcategories(category: str) -> list[str]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT type FROM Products 
            WHERE category = ? AND quantity > 0
        """, (category,))
        rows = cursor.fetchall()
        return [r[0] for r in rows]

def get_products(category: str, subcat: str) -> list[tuple]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, price, quantity 
            FROM Products
            WHERE category = ? AND type = ? AND quantity > 0
        """, (category, subcat))
        return cursor.fetchall()

def initialize_demo_products():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Products")
        count = cursor.fetchone()[0]
        if count > 0:
            return

        categories = ["Key", "Box", "Gift"]
        subcategories = ["Bronze", "Silver", "Platinum"]
        product_names = ["One", "Two", "Three"]
        price = 100.0
        quantity = 10
        photo_path = "data/orders/sample.jpg"

        for cat in categories:
            for subcat in subcategories:
                for pname in product_names:
                    cursor.execute(
                        "INSERT INTO Products (category, type, name, description, price, photo_path, quantity) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (cat, subcat, pname, f"Описание для {pname}", price, photo_path, quantity)
                    )
        conn.commit()
# ... остальное содержимое database.py без изменений ...

def update_user_language(telegram_id: int, language: str):
    """
    Обновляет колонку language у пользователя с данным telegram_id.
    """
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET language = ? WHERE telegram_id = ?", (language, telegram_id))
        conn.commit()

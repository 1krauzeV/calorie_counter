
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "database.db"

PRODUCTS = [
    ("Яблоко", 52),
    ("Банан", 89),
    ("Рис", 130),
    ("Куриная грудка", 165),
    ("Яйцо", 155),
    ("Хлеб", 265),
    ("Молоко", 42),
    ("Картофель", 77),
    ("Сыр", 350),
    ("Йогурт", 60)
]


def init_database():
    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                calories_per_100g REAL NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                weight REAL NOT NULL,
                meal_date TEXT NOT NULL,
                calories REAL NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        for name, calories in PRODUCTS:
            existing = conn.execute(
                """
                SELECT id FROM products
                WHERE name = ? COLLATE NOCASE
                LIMIT 1
                """,
                (name,)
            ).fetchone()

            if existing is None:
                conn.execute(
                    """
                    INSERT INTO products (name, calories_per_100g)
                    VALUES (?, ?)
                    """,
                    (name, calories)
                )

        conn.commit()

    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
    print("База данных готова к работе.")

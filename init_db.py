import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    calories_per_100g REAL NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS meals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    weight REAL NOT NULL,
    meal_date TEXT NOT NULL,
    calories REAL NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id)
)
''')

products = [
    ('Яблоко', 52),
    ('Банан', 89),
    ('Рис', 130),
    ('Куриная грудка', 165),
    ('Яйцо', 155),
    ('Хлеб', 265),
    ('Молоко', 42),
    ('Картофель', 77),
    ('Сыр', 350),
    ('Йогурт', 60)
]

cursor.executemany('''
INSERT INTO products (name, calories_per_100g)
VALUES (?, ?)
''', products)

conn.commit()
conn.close()

print("База данных создана, продукты добавлены.")
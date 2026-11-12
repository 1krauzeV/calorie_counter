from flask import Flask, render_template, request, redirect, flash, session
import sqlite3
from datetime import date, datetime, timedelta
from init_db import init_database, DB_PATH
from math import isfinite

app = Flask(__name__)
app.secret_key = 'calorie_counter_secret_key'


def get_db_connection():
    """Создаёт подключение к базе данных SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def normalize_date(date_string):
    if not date_string:
        return date.today().isoformat()

    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date().isoformat()
    except ValueError:
        return date.today().isoformat()


def ensure_db_setup():
    """Создаёт таблицу настроек и устанавливает начальную цель."""
    conn = get_db_connection()

    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    goal_row = conn.execute(
        "SELECT value FROM settings WHERE key = 'daily_goal'"
    ).fetchone()

    if goal_row is None:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ('daily_goal', '2000')
        )

    conn.commit()
    conn.close()


def get_home_data(selected_date):
    """Получает из базы данные для отображения главной страницы."""
    conn = get_db_connection()

    products = conn.execute(
        'SELECT * FROM products ORDER BY name'
    ).fetchall()

    meals = conn.execute('''
        SELECT meals.id, meals.product_id, products.name, meals.weight, meals.calories, meals.meal_date
        FROM meals
        JOIN products ON meals.product_id = products.id
        WHERE meals.meal_date = ?
        ORDER BY meals.id DESC
    ''', (selected_date,)).fetchall()

    total_row = conn.execute('''
        SELECT SUM(calories) AS total
        FROM meals
        WHERE meal_date = ?
    ''', (selected_date,)).fetchone()

    goal_row = conn.execute(
        "SELECT value FROM settings WHERE key = 'daily_goal'"
    ).fetchone()

    history = conn.execute('''
        SELECT meal_date, ROUND(SUM(calories), 2) AS total
        FROM meals
        GROUP BY meal_date
        ORDER BY meal_date DESC
        LIMIT 7
    ''').fetchall()

    conn.close()

    total_calories = float(total_row['total']) if total_row['total'] is not None else 0
    daily_goal = float(goal_row['value']) if goal_row is not None else 2000
    remaining = daily_goal - total_calories

    return products, meals, total_calories, daily_goal, remaining, history


ensure_db_setup()
init_database()
ensure_db_setup()

@app.route('/')
def index():
    """Формирует главную страницу для выбранной даты."""

    selected_date = normalize_date(request.args.get('selected_date'))
    products, meals, total_calories, daily_goal, remaining, history = get_home_data(selected_date)

    duplicate_data = session.pop('duplicate_data', None)

    remaining_calories = remaining if remaining >= 0 else 0
    exceeded_calories = abs(remaining) if remaining < 0 else 0

    today_value = date.today().isoformat()
    yesterday_value = (date.today() - timedelta(days=1)).isoformat()

    if daily_goal > 0:
        progress_percent = min((total_calories / daily_goal) * 100, 100)
    else:
        progress_percent = 0

    return render_template(
        'index.html',
        products=products,
        meals=meals,
        total_calories=total_calories,
        daily_goal=daily_goal,
        remaining_calories=remaining_calories,
        exceeded_calories=exceeded_calories,
        history=history,
        selected_date=selected_date,
        today=today_value,
        yesterday=yesterday_value,
        progress_percent=progress_percent,
        duplicate_data=duplicate_data
    )

@app.route('/set_goal', methods=['POST'])
def set_goal():
    """Проверяет и сохраняет дневную норму калорий."""

    selected_date = normalize_date(request.form.get('selected_date'))

    try:
        daily_goal = float(request.form.get('daily_goal', ''))

        # Цель должна быть положительным конечным числом
        if not isfinite(daily_goal) or daily_goal <= 0:
            raise ValueError

    except (ValueError, TypeError):
        flash('Введите корректную цель по калориям.', 'error')
        return redirect(f'/?selected_date={selected_date}')

    conn = get_db_connection()
    conn.execute(
        "UPDATE settings SET value = ? WHERE key = 'daily_goal'",
        (str(daily_goal),)
    )
    conn.commit()
    conn.close()

    flash(f'Новая дневная цель: {daily_goal:.0f} ккал.', 'success')
    return redirect(f'/?selected_date={selected_date}')


@app.route('/add', methods=['POST'])
def add_meal():
    """Рассчитывает калорийность и добавляет запись о приёме пищи."""

    selected_date = normalize_date(request.form.get('selected_date'))


    try:
        product_id = int(request.form.get('product_id', ''))
        weight = float(request.form.get('weight', ''))

        # Проверяем, что продукт выбран, а вес положительный
        if product_id <= 0 or not isfinite(weight) or weight <= 0:
            raise ValueError

    except (ValueError, TypeError):
        flash('Введите корректный вес продукта.', 'error')
        return redirect(f'/?selected_date={selected_date}')


    conn = get_db_connection()

    product = conn.execute(
        'SELECT * FROM products WHERE id = ?',
        (product_id,)
    ).fetchone()

    if product is None:
        conn.close()
        flash('Продукт не найден.', 'error')
        return redirect(f'/?selected_date={selected_date}')

    calories = (product['calories_per_100g'] / 100) * weight

    conn.execute('''
        INSERT INTO meals (product_id, weight, meal_date, calories)
        VALUES (?, ?, ?, ?)
    ''', (product_id, weight, selected_date, calories))

    conn.commit()
    conn.close()

    flash(f'Продукт добавлен на дату {selected_date}.', 'success')
    return redirect(f'/?selected_date={selected_date}')


@app.route('/add_product', methods=['POST'])
def add_product():
    """Добавляет продукт или предлагает обновить существующий."""

    selected_date = normalize_date(request.form.get('selected_date'))
    name = request.form.get('name', '').strip()

    try:
        new_calories = float(request.form.get('new_calories', ''))

        # Запрещаем отрицательные и неконечные значения
        if not isfinite(new_calories) or new_calories < 0:
            raise ValueError

    except (ValueError, TypeError):
        flash('Новая калорийность указана неверно.', 'error')
        return redirect(f'/?selected_date={selected_date}')

    if not name:
        flash('Название продукта не может быть пустым.', 'error')
        return redirect(f'/?selected_date={selected_date}')

    conn = get_db_connection()

    existing_product = conn.execute(
        'SELECT * FROM products WHERE LOWER(name) = LOWER(?)',
        (name,)
    ).fetchone()

    if existing_product is None:
        conn.execute('''
            INSERT INTO products (name, calories_per_100g)
            VALUES (?, ?)
        ''', (name, calories_per_100g))
        conn.commit()
        conn.close()

        flash(f'Продукт "{name}" успешно добавлен.', 'success')
        return redirect(f'/?selected_date={selected_date}')

    current_calories = float(existing_product['calories_per_100g'])

    if abs(current_calories - calories_per_100g) < 0.0001:
        conn.close()
        flash(
            f'Продукт "{existing_product["name"]}" уже существует с такой же калорийностью.',
            'warning'
        )
        return redirect(f'/?selected_date={selected_date}')

    conn.close()

    session['duplicate_data'] = {
        'id': existing_product['id'],
        'name': existing_product['name'],
        'current_calories': current_calories,
        'new_calories': calories_per_100g,
        'selected_date': selected_date
    }

    return redirect(f'/?selected_date={selected_date}')


@app.route('/update_product/<int:product_id>', methods=['POST'])
def update_product(product_id):
    """Обновляет калорийность продукта и пересчитывает записи."""

    selected_date = normalize_date(request.form.get('selected_date'))

    try:
        new_calories = float(request.form['new_calories'])
        if new_calories < 0:
            raise ValueError
    except ValueError:
        flash('Новая калорийность указана неверно.', 'error')
        return redirect(f'/?selected_date={selected_date}')

    conn = get_db_connection()

    conn.execute('''
        UPDATE products
        SET calories_per_100g = ?
        WHERE id = ?
    ''', (new_calories, product_id))

    conn.execute('''
        UPDATE meals
        SET calories = (weight / 100.0) * ?
        WHERE product_id = ?
    ''', (new_calories, product_id))

    conn.commit()
    conn.close()

    flash('Пищевая ценность обновлена, сохранённые записи пересчитаны.', 'success')
    return redirect(f'/?selected_date={selected_date}')



@app.route('/delete/<int:meal_id>', methods=['POST'])
def delete_meal(meal_id):
    """Удаляет запись о приёме пищи за выбранную дату."""

    # Получаем дату, за которую пользователь удаляет запись
    selected_date = normalize_date(
        request.form.get('selected_date')
    )

    conn = get_db_connection()

    # Удаляем запись только за выбранную дату
    result = conn.execute(
        'DELETE FROM meals WHERE id = ? AND meal_date = ?',
        (meal_id, selected_date)
    )

    conn.commit()
    conn.close()

    # Показываем результат операции
    if result.rowcount > 0:
        flash('Запись успешно удалена.', 'success')
    else:
        flash('Запись не найдена.', 'warning')

    return redirect(f'/?selected_date={selected_date}')



if __name__ == '__main__':
    app.run(debug=True)
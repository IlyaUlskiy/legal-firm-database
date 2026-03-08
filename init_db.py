from models import init_db, get_db
from werkzeug.security import generate_password_hash


def create_test_users():
    """Создание тестовых пользователей"""
    connection = get_db()
    cursor = connection.cursor()

    # Администратор
    cursor.execute("""
        INSERT INTO users (username, password_hash, role_id, full_name, email, is_active)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, ('admin', generate_password_hash('admin123'), 1, 'Администратор Системы', 'admin@firm.ru', True))

    # Менеджер
    cursor.execute("""
        INSERT INTO users (username, password_hash, role_id, full_name, email, is_active)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, ('manager', generate_password_hash('manager123'), 2, 'Менеджер Иван', 'manager@firm.ru', True))

    # Юрист
    cursor.execute("""
        INSERT INTO users (username, password_hash, role_id, full_name, email, is_active)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, ('lawyer', generate_password_hash('lawyer123'), 3, 'Юрист Петр', 'lawyer@firm.ru', True))

    connection.commit()
    connection.close()


if __name__ == '__main__':
    print("Инициализация базы данных...")
    init_db()
    print("Создание тестовых пользователей...")
    create_test_users()
    print("Готово! Запускайте: python app.py")
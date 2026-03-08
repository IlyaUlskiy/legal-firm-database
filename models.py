import pymysql
from config import DB_CONFIG


def get_db():
    """Создание подключения к базе данных"""
    return pymysql.connect(**DB_CONFIG)


def init_db():
    """Инициализация базы данных (создание таблиц)"""
    connection = get_db()
    cursor = connection.cursor()

    # Создание таблиц
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_roles (
            role_id TINYINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            role_name VARCHAR(50) NOT NULL UNIQUE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role_id TINYINT UNSIGNED NOT NULL,
            full_name VARCHAR(255) NOT NULL,
            email VARCHAR(100) UNIQUE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL,
            FOREIGN KEY (role_id) REFERENCES user_roles(role_id) ON DELETE RESTRICT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            client_id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL,
            phone VARCHAR(20) UNIQUE NOT NULL,
            email VARCHAR(100),
            passport_data VARCHAR(255) NOT NULL,
            registration_date DATE NOT NULL DEFAULT (CURRENT_DATE),
            manager_id INT UNSIGNED NOT NULL,
            FOREIGN KEY (manager_id) REFERENCES users(user_id) ON DELETE RESTRICT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS case_statuses (
            status_id TINYINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            status_name VARCHAR(50) NOT NULL UNIQUE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS case_types (
            type_id TINYINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            type_name VARCHAR(100) NOT NULL UNIQUE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cases (
            case_id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            case_number VARCHAR(50) UNIQUE NOT NULL,
            client_id INT UNSIGNED NOT NULL,
            lawyer_id INT UNSIGNED NOT NULL,
            manager_id INT UNSIGNED NOT NULL,
            status_id TINYINT UNSIGNED NOT NULL,
            type_id TINYINT UNSIGNED NOT NULL,
            description TEXT,
            open_date DATE NOT NULL DEFAULT (CURRENT_DATE),
            close_date DATE NULL,
            FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE RESTRICT,
            FOREIGN KEY (lawyer_id) REFERENCES users(user_id) ON DELETE RESTRICT,
            FOREIGN KEY (manager_id) REFERENCES users(user_id) ON DELETE RESTRICT,
            FOREIGN KEY (status_id) REFERENCES case_statuses(status_id) ON DELETE RESTRICT,
            FOREIGN KEY (type_id) REFERENCES case_types(type_id) ON DELETE RESTRICT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''')

    # Заполнение справочников
    cursor.execute(
        "INSERT IGNORE INTO user_roles (role_id, role_name) VALUES (1, 'Администратор'), (2, 'Менеджер'), (3, 'Юрист')")
    cursor.execute(
        "INSERT IGNORE INTO case_statuses (status_id, status_name) VALUES (1, 'Новое'), (2, 'В работе'), (3, 'На рассмотрении суда'), (4, 'Завершено'), (5, 'Отказано')")
    cursor.execute(
        "INSERT IGNORE INTO case_types (type_id, type_name) VALUES (1, 'Гражданское'), (2, 'Уголовное'), (3, 'Арбитражное'), (4, 'Административное')")

    connection.commit()
    connection.close()
import pymysql.cursors

# Настройки базы данных
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Digrel4ik',  # ← Укажите ваш пароль от MySQL
    'database': 'ppractica',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Секретный ключ для сессий
SECRET_KEY = 'legal_firm_secret_key_2026'
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
from config import DB_CONFIG, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY


def get_db():
    """Создание подключения к базе данных"""
    return pymysql.connect(**DB_CONFIG)


# ===== АВТОРИЗАЦИЯ =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница авторизации"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Введите логин и пароль', 'danger')
            return render_template('login.html')

        connection = get_db()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT user_id, username, password_hash, role_id, full_name
            FROM users
            WHERE username = %s AND is_active = TRUE
        """, (username,))

        user = cursor.fetchone()
        connection.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role_id'] = user['role_id']
            session['full_name'] = user['full_name']

            flash(f'Добро пожаловать, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный логин или пароль', 'danger')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    return redirect(url_for('login'))


# ===== ГЛАВНАЯ =====

@app.route('/')
def dashboard():
    """Главная страница"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM clients")
    clients_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM cases")
    cases_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM hearings")
    hearings_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM documents")
    documents_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_active = TRUE")
    users_count = cursor.fetchone()['count']

    connection.close()

    return render_template('dashboard.html',
                           clients_count=clients_count,
                           cases_count=cases_count,
                           hearings_count=hearings_count,
                           documents_count=documents_count,
                           users_count=users_count,
                           role_id=session['role_id'])


# ===== КЛИЕНТЫ =====

@app.route('/clients')
def clients():
    """Список клиентов с поиском"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '').strip()

    connection = get_db()
    cursor = connection.cursor()

    if search:
        cursor.execute("""
            SELECT c.*, u.full_name as manager_name
            FROM clients c
            JOIN users u ON c.manager_id = u.user_id
            WHERE c.full_name LIKE %s
            ORDER BY c.registration_date DESC
        """, (f'%{search}%',))
    else:
        cursor.execute("""
            SELECT c.*, u.full_name as manager_name
            FROM clients c
            JOIN users u ON c.manager_id = u.user_id
            ORDER BY c.registration_date DESC
        """)

    clients_list = cursor.fetchall()
    connection.close()

    return render_template('clients.html',
                           clients=clients_list,
                           search_query=search,
                           role_id=session['role_id'])


@app.route('/clients/add', methods=['GET', 'POST'])
def add_client():
    """Добавление клиента"""
    if 'user_id' not in session or session['role_id'] not in [1, 2]:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('clients'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        passport_data = request.form.get('passport_data', '').strip()

        if not full_name or not phone or not passport_data:
            flash('Заполните все обязательные поля', 'danger')
            return render_template('client_form.html', mode='add')

        connection = get_db()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                INSERT INTO clients (full_name, phone, email, passport_data, manager_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (full_name, phone, email if email else None, passport_data, session['user_id']))

            connection.commit()
            flash('Клиент успешно добавлен', 'success')
            return redirect(url_for('clients'))
        except pymysql.Error as e:
            flash(f'Ошибка при добавлении клиента: {str(e)}', 'danger')
            return render_template('client_form.html', mode='add')
        finally:
            connection.close()

    return render_template('client_form.html', mode='add')


@app.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    """Редактирование клиента"""
    if 'user_id' not in session or session['role_id'] not in [1, 2]:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('clients'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM clients WHERE client_id = %s", (client_id,))
    client = cursor.fetchone()

    if not client:
        flash('Клиент не найден', 'danger')
        return redirect(url_for('clients'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        passport_data = request.form.get('passport_data', '').strip()

        if not full_name or not phone or not passport_data:
            flash('Заполните все обязательные поля', 'danger')
            return render_template('client_form.html', mode='edit', client=client)

        try:
            cursor.execute("""
                UPDATE clients
                SET full_name = %s, phone = %s, email = %s, passport_data = %s
                WHERE client_id = %s
            """, (full_name, phone, email if email else None, passport_data, client_id))

            connection.commit()
            flash('Клиент успешно обновлён', 'success')
            return redirect(url_for('clients'))
        except pymysql.Error as e:
            flash(f'Ошибка при обновлении клиента: {str(e)}', 'danger')
            return render_template('client_form.html', mode='edit', client=client)
        finally:
            connection.close()

    connection.close()
    return render_template('client_form.html', mode='edit', client=client)


@app.route('/clients/delete/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    """Удаление клиента"""
    if 'user_id' not in session or session['role_id'] not in [1, 2]:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('clients'))

    connection = get_db()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT COUNT(*) as count FROM cases WHERE client_id = %s", (client_id,))
        result = cursor.fetchone()

        if result['count'] > 0:
            flash(f'Нельзя удалить клиента, у которого есть {result["count"]} дел', 'danger')
            return redirect(url_for('clients'))

        cursor.execute("DELETE FROM clients WHERE client_id = %s", (client_id,))
        connection.commit()

        flash('Клиент успешно удалён', 'success')
        return redirect(url_for('clients'))
    except pymysql.Error as e:
        flash(f'Ошибка при удалении клиента: {str(e)}', 'danger')
        return redirect(url_for('clients'))
    finally:
        connection.close()


# ===== ДЕЛА =====

@app.route('/cases')
def cases():
    """Список дел с фильтрацией"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    status_id = request.args.get('status_id', '').strip()
    type_id = request.args.get('type_id', '').strip()
    search = request.args.get('search', '').strip()

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM case_statuses ORDER BY status_id")
    statuses = cursor.fetchall()

    cursor.execute("SELECT * FROM case_types ORDER BY type_id")
    types = cursor.fetchall()

    sql = """
        SELECT c.*, 
               cl.full_name as client_name,
               u.full_name as lawyer_name,
               m.full_name as manager_name,
               cs.status_name,
               ct.type_name,
               cc.category_name
        FROM cases c
        JOIN clients cl ON c.client_id = cl.client_id
        JOIN users u ON c.lawyer_id = u.user_id
        JOIN users m ON c.manager_id = m.user_id
        JOIN case_statuses cs ON c.status_id = cs.status_id
        JOIN case_types ct ON c.type_id = ct.type_id
        JOIN case_categories cc ON c.category_id = cc.category_id
        WHERE 1=1
    """
    params = []

    if status_id:
        sql += " AND c.status_id = %s"
        params.append(status_id)

    if type_id:
        sql += " AND c.type_id = %s"
        params.append(type_id)

    if search:
        sql += " AND (c.case_number LIKE %s OR cl.full_name LIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])

    if session['role_id'] == 3:
        sql += " AND c.lawyer_id = %s"
        params.append(session['user_id'])

    sql += " ORDER BY c.open_date DESC"

    cursor.execute(sql, params)
    cases_list = cursor.fetchall()

    connection.close()

    return render_template('cases.html',
                           cases=cases_list,
                           statuses=statuses,
                           types=types,
                           selected_status=status_id,
                           selected_type=type_id,
                           search_query=search,
                           role_id=session['role_id'])


@app.route('/cases/add', methods=['GET', 'POST'])
def add_case():
    """Добавление дела"""
    if 'user_id' not in session or session['role_id'] not in [1, 2]:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('cases'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM clients ORDER BY full_name")
    clients = cursor.fetchall()

    cursor.execute("SELECT * FROM users WHERE role_id = 3 AND is_active = TRUE ORDER BY full_name")
    lawyers = cursor.fetchall()

    cursor.execute("SELECT * FROM case_statuses ORDER BY status_id")
    statuses = cursor.fetchall()

    cursor.execute("SELECT * FROM case_types ORDER BY type_id")
    types = cursor.fetchall()

    cursor.execute("SELECT * FROM case_categories ORDER BY category_id")
    categories = cursor.fetchall()

    if request.method == 'POST':
        client_id = request.form.get('client_id', type=int)
        lawyer_id = request.form.get('lawyer_id', type=int)
        status_id = request.form.get('status_id', type=int)
        type_id = request.form.get('type_id', type=int)
        category_id = request.form.get('category_id', type=int)
        description = request.form.get('description', '').strip()

        if not all([client_id, lawyer_id, status_id, type_id, category_id, description]):
            flash('Заполните все обязательные поля', 'danger')
            return render_template('case_form.html', mode='add',
                                   clients=clients, lawyers=lawyers,
                                   statuses=statuses, types=types, categories=categories)

        try:
            cursor.execute("SELECT MAX(case_id) as max_id FROM cases")
            result = cursor.fetchone()
            new_case_id = (result['max_id'] or 0) + 1

            cursor.execute("SELECT type_name FROM case_types WHERE type_id = %s", (type_id,))
            type_name = cursor.fetchone()['type_name']

            prefix = {
                'Гражданское': 'ГР',
                'Уголовное': 'УГ',
                'Арбитражное': 'АР',
                'Административное': 'АД'
            }.get(type_name, 'ДЕЛ')

            case_number = f"{prefix}-{2026}-{str(new_case_id).zfill(3)}"

            cursor.execute("""
                INSERT INTO cases (case_number, client_id, lawyer_id, manager_id, status_id, type_id, category_id, description, open_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURDATE())
            """, (case_number, client_id, lawyer_id, session['user_id'], status_id, type_id, category_id, description))

            connection.commit()
            flash(f'Дело успешно создано. Номер: {case_number}', 'success')
            return redirect(url_for('cases'))
        except pymysql.Error as e:
            flash(f'Ошибка при добавлении дела: {str(e)}', 'danger')
            return render_template('case_form.html', mode='add',
                                   clients=clients, lawyers=lawyers,
                                   statuses=statuses, types=types, categories=categories)
        finally:
            connection.close()

    connection.close()
    return render_template('case_form.html', mode='add',
                           clients=clients, lawyers=lawyers,
                           statuses=statuses, types=types, categories=categories)


@app.route('/cases/edit/<int:case_id>', methods=['GET', 'POST'])
def edit_case(case_id):
    """Редактирование дела"""
    if 'user_id' not in session or session['role_id'] not in [1, 2]:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('cases'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM clients ORDER BY full_name")
    clients = cursor.fetchall()

    cursor.execute("SELECT * FROM users WHERE role_id = 3 AND is_active = TRUE ORDER BY full_name")
    lawyers = cursor.fetchall()

    cursor.execute("SELECT * FROM case_statuses ORDER BY status_id")
    statuses = cursor.fetchall()

    cursor.execute("SELECT * FROM case_types ORDER BY type_id")
    types = cursor.fetchall()

    cursor.execute("SELECT * FROM case_categories ORDER BY category_id")
    categories = cursor.fetchall()

    cursor.execute("SELECT * FROM cases WHERE case_id = %s", (case_id,))
    case = cursor.fetchone()

    if not case:
        flash('Дело не найдено', 'danger')
        return redirect(url_for('cases'))

    if request.method == 'POST':
        client_id = request.form.get('client_id', type=int)
        lawyer_id = request.form.get('lawyer_id', type=int)
        status_id = request.form.get('status_id', type=int)
        type_id = request.form.get('type_id', type=int)
        category_id = request.form.get('category_id', type=int)
        description = request.form.get('description', '').strip()

        if not all([client_id, lawyer_id, status_id, type_id, category_id, description]):
            flash('Заполните все обязательные поля', 'danger')
            return render_template('case_form.html', mode='edit', case=case,
                                   clients=clients, lawyers=lawyers,
                                   statuses=statuses, types=types, categories=categories)

        try:
            cursor.execute("""
                UPDATE cases
                SET client_id = %s, lawyer_id = %s, status_id = %s, type_id = %s, category_id = %s, description = %s
                WHERE case_id = %s
            """, (client_id, lawyer_id, status_id, type_id, category_id, description, case_id))

            connection.commit()
            flash('Дело успешно обновлено', 'success')
            return redirect(url_for('cases'))
        except pymysql.Error as e:
            flash(f'Ошибка при обновлении дела: {str(e)}', 'danger')
            return render_template('case_form.html', mode='edit', case=case,
                                   clients=clients, lawyers=lawyers,
                                   statuses=statuses, types=types, categories=categories)
        finally:
            connection.close()

    connection.close()
    return render_template('case_form.html', mode='edit', case=case,
                           clients=clients, lawyers=lawyers,
                           statuses=statuses, types=types, categories=categories)


@app.route('/cases/delete/<int:case_id>', methods=['POST'])
def delete_case(case_id):
    """Удаление дела"""
    if 'user_id' not in session or session['role_id'] not in [1, 2]:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('cases'))

    connection = get_db()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM cases WHERE case_id = %s", (case_id,))
        connection.commit()

        flash('Дело успешно удалено', 'success')
        return redirect(url_for('cases'))
    except pymysql.Error as e:
        flash(f'Ошибка при удалении дела: {str(e)}', 'danger')
        return redirect(url_for('cases'))
    finally:
        connection.close()


# ===== ПОДРОБНОСТИ ДЕЛА =====

@app.route('/cases/<int:case_id>')
def case_details(case_id):
    """Подробности дела"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT c.*, cl.full_name as client_name, cl.phone as client_phone,
               u.full_name as lawyer_name, m.full_name as manager_name,
               cs.status_name, ct.type_name, cc.category_name
        FROM cases c
        JOIN clients cl ON c.client_id = cl.client_id
        JOIN users u ON c.lawyer_id = u.user_id
        JOIN users m ON c.manager_id = m.user_id
        JOIN case_statuses cs ON c.status_id = cs.status_id
        JOIN case_types ct ON c.type_id = ct.type_id
        JOIN case_categories cc ON c.category_id = cc.category_id
        WHERE c.case_id = %s
    """, (case_id,))

    case = cursor.fetchone()

    if not case:
        flash('Дело не найдено', 'danger')
        return redirect(url_for('cases'))

    cursor.execute("""
        SELECT * FROM hearings
        WHERE case_id = %s
        ORDER BY hearing_date DESC
    """, (case_id,))
    hearings = cursor.fetchall()

    cursor.execute("""
        SELECT d.*, dt.type_name
        FROM documents d
        JOIN document_types dt ON d.type_id = dt.type_id
        WHERE d.case_id = %s
        ORDER BY d.upload_date DESC
    """, (case_id,))
    documents = cursor.fetchall()

    cursor.execute("""
        SELECT c.*, u.full_name as author_name
        FROM comments c
        JOIN users u ON c.user_id = u.user_id
        WHERE c.case_id = %s
        ORDER BY c.created_at DESC
    """, (case_id,))
    comments = cursor.fetchall()

    connection.close()

    return render_template('case_details.html',
                           case=case,
                           hearings=hearings,
                           documents=documents,
                           comments=comments,
                           role_id=session['role_id'])


# ===== СУДЕБНЫЕ ЗАСЕДАНИЯ =====

@app.route('/hearings')
def hearings():
    """Список заседаний"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT h.*, c.case_number, cl.full_name as client_name
        FROM hearings h
        JOIN cases c ON h.case_id = c.case_id
        JOIN clients cl ON c.client_id = cl.client_id
        ORDER BY h.hearing_date DESC
    """)

    hearings_list = cursor.fetchall()
    connection.close()

    return render_template('hearings.html',
                           hearings=hearings_list,
                           role_id=session['role_id'])


@app.route('/hearings/add/<int:case_id>', methods=['GET', 'POST'])
def add_hearing(case_id):
    """Добавление заседания"""
    if 'user_id' not in session or session['role_id'] not in [1, 2]:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('cases'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM cases WHERE case_id = %s", (case_id,))
    case = cursor.fetchone()

    if not case:
        flash('Дело не найдено', 'danger')
        return redirect(url_for('cases'))

    if request.method == 'POST':
        hearing_date = request.form.get('hearing_date')
        court_name = request.form.get('court_name', '').strip()
        courtroom = request.form.get('courtroom', '').strip()
        result = request.form.get('result', '').strip()

        if not all([hearing_date, court_name]):
            flash('Заполните все обязательные поля', 'danger')
            return render_template('hearing_form.html', mode='add', case=case)

        try:
            cursor.execute("""
                INSERT INTO hearings (case_id, hearing_date, court_name, courtroom, result, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (case_id, hearing_date, court_name, courtroom if courtroom else None, result if result else None,
                  session['user_id']))

            connection.commit()
            flash('Заседание успешно добавлено', 'success')
            return redirect(url_for('case_details', case_id=case_id))
        except pymysql.Error as e:
            flash(f'Ошибка при добавлении заседания: {str(e)}', 'danger')
            return render_template('hearing_form.html', mode='add', case=case)
        finally:
            connection.close()

    connection.close()
    return render_template('hearing_form.html', mode='add', case=case)


@app.route('/hearings/edit/<int:hearing_id>', methods=['GET', 'POST'])
def edit_hearing(hearing_id):
    """Редактирование заседания"""
    if 'user_id' not in session or session['role_id'] not in [1, 2]:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('hearings'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM hearings WHERE hearing_id = %s", (hearing_id,))
    hearing = cursor.fetchone()

    if not hearing:
        flash('Заседание не найдено', 'danger')
        return redirect(url_for('hearings'))

    cursor.execute("SELECT * FROM cases WHERE case_id = %s", (hearing['case_id'],))
    case = cursor.fetchone()

    if request.method == 'POST':
        hearing_date = request.form.get('hearing_date')
        court_name = request.form.get('court_name', '').strip()
        courtroom = request.form.get('courtroom', '').strip()
        result = request.form.get('result', '').strip()

        if not all([hearing_date, court_name]):
            flash('Заполните все обязательные поля', 'danger')
            return render_template('hearing_form.html', mode='edit', hearing=hearing, case=case)

        try:
            cursor.execute("""
                UPDATE hearings
                SET hearing_date = %s, court_name = %s, courtroom = %s, result = %s
                WHERE hearing_id = %s
            """, (hearing_date, court_name, courtroom if courtroom else None, result if result else None, hearing_id))

            connection.commit()
            flash('Заседание успешно обновлено', 'success')
            return redirect(url_for('case_details', case_id=hearing['case_id']))
        except pymysql.Error as e:
            flash(f'Ошибка при обновлении заседания: {str(e)}', 'danger')
            return render_template('hearing_form.html', mode='edit', hearing=hearing, case=case)
        finally:
            connection.close()

    connection.close()
    return render_template('hearing_form.html', mode='edit', hearing=hearing, case=case)


@app.route('/hearings/delete/<int:hearing_id>', methods=['POST'])
def delete_hearing(hearing_id):
    """Удаление заседания"""
    if 'user_id' not in session or session['role_id'] not in [1, 2]:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('hearings'))

    connection = get_db()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT case_id FROM hearings WHERE hearing_id = %s", (hearing_id,))
        case_id = cursor.fetchone()['case_id']

        cursor.execute("DELETE FROM hearings WHERE hearing_id = %s", (hearing_id,))
        connection.commit()

        flash('Заседание успешно удалено', 'success')
        return redirect(url_for('case_details', case_id=case_id))
    except pymysql.Error as e:
        flash(f'Ошибка при удалении заседания: {str(e)}', 'danger')
        return redirect(url_for('hearings'))
    finally:
        connection.close()


# ===== ДОКУМЕНТЫ =====

@app.route('/documents')
def documents():
    """Список документов"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT d.*, c.case_number, dt.type_name, u.full_name as uploader_name
        FROM documents d
        JOIN cases c ON d.case_id = c.case_id
        JOIN document_types dt ON d.type_id = dt.type_id
        JOIN users u ON d.uploaded_by = u.user_id
        ORDER BY d.upload_date DESC
    """)

    documents_list = cursor.fetchall()
    connection.close()

    return render_template('documents.html',
                           documents=documents_list,
                           role_id=session['role_id'])


@app.route('/documents/add/<int:case_id>', methods=['GET', 'POST'])
def add_document(case_id):
    """Добавление документа"""
    if 'user_id' not in session:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('cases'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM cases WHERE case_id = %s", (case_id,))
    case = cursor.fetchone()

    if not case:
        flash('Дело не найдено', 'danger')
        return redirect(url_for('cases'))

    cursor.execute("SELECT * FROM document_types ORDER BY type_id")
    doc_types = cursor.fetchall()

    if request.method == 'POST':
        type_id = request.form.get('type_id', type=int)
        document_name = request.form.get('document_name', '').strip()
        file_path = request.form.get('file_path', '').strip()

        if not all([type_id, document_name, file_path]):
            flash('Заполните все обязательные поля', 'danger')
            return render_template('document_form.html', mode='add', case=case, doc_types=doc_types)

        try:
            cursor.execute("""
                INSERT INTO documents (case_id, type_id, document_name, file_path, uploaded_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (case_id, type_id, document_name, file_path, session['user_id']))

            connection.commit()
            flash('Документ успешно добавлен', 'success')
            return redirect(url_for('case_details', case_id=case_id))
        except pymysql.Error as e:
            flash(f'Ошибка при добавлении документа: {str(e)}', 'danger')
            return render_template('document_form.html', mode='add', case=case, doc_types=doc_types)
        finally:
            connection.close()

    connection.close()
    return render_template('document_form.html', mode='add', case=case, doc_types=doc_types)


@app.route('/documents/edit/<int:document_id>', methods=['GET', 'POST'])
def edit_document(document_id):
    """Редактирование документа"""
    if 'user_id' not in session or session['role_id'] not in [1, 2]:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('documents'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM documents WHERE document_id = %s", (document_id,))
    document = cursor.fetchone()

    if not document:
        flash('Документ не найден', 'danger')
        return redirect(url_for('documents'))

    cursor.execute("SELECT * FROM cases WHERE case_id = %s", (document['case_id'],))
    case = cursor.fetchone()

    cursor.execute("SELECT * FROM document_types ORDER BY type_id")
    doc_types = cursor.fetchall()

    if request.method == 'POST':
        type_id = request.form.get('type_id', type=int)
        document_name = request.form.get('document_name', '').strip()
        file_path = request.form.get('file_path', '').strip()

        if not all([type_id, document_name, file_path]):
            flash('Заполните все обязательные поля', 'danger')
            return render_template('document_form.html', mode='edit', document=document, case=case, doc_types=doc_types)

        try:
            cursor.execute("""
                UPDATE documents
                SET type_id = %s, document_name = %s, file_path = %s
                WHERE document_id = %s
            """, (type_id, document_name, file_path, document_id))

            connection.commit()
            flash('Документ успешно обновлён', 'success')
            return redirect(url_for('case_details', case_id=document['case_id']))
        except pymysql.Error as e:
            flash(f'Ошибка при обновлении документа: {str(e)}', 'danger')
            return render_template('document_form.html', mode='edit', document=document, case=case, doc_types=doc_types)
        finally:
            connection.close()

    connection.close()
    return render_template('document_form.html', mode='edit', document=document, case=case, doc_types=doc_types)


@app.route('/documents/delete/<int:document_id>', methods=['POST'])
def delete_document(document_id):
    """Удаление документа"""
    if 'user_id' not in session or session['role_id'] not in [1, 2]:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('documents'))

    connection = get_db()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT case_id FROM documents WHERE document_id = %s", (document_id,))
        case_id = cursor.fetchone()['case_id']

        cursor.execute("DELETE FROM documents WHERE document_id = %s", (document_id,))
        connection.commit()

        flash('Документ успешно удалён', 'success')
        return redirect(url_for('case_details', case_id=case_id))
    except pymysql.Error as e:
        flash(f'Ошибка при удалении документа: {str(e)}', 'danger')
        return redirect(url_for('documents'))
    finally:
        connection.close()


# ===== КОММЕНТАРИИ =====

@app.route('/comments/add/<int:case_id>', methods=['POST'])
def add_comment(case_id):
    """Добавление комментария"""
    if 'user_id' not in session:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('cases'))

    comment_text = request.form.get('comment_text', '').strip()

    if not comment_text:
        flash('Комментарий не может быть пустым', 'danger')
        return redirect(url_for('case_details', case_id=case_id))

    connection = get_db()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO comments (case_id, user_id, comment_text)
            VALUES (%s, %s, %s)
        """, (case_id, session['user_id'], comment_text))

        connection.commit()
        flash('Комментарий добавлен', 'success')
    except pymysql.Error as e:
        flash(f'Ошибка при добавлении комментария: {str(e)}', 'danger')
    finally:
        connection.close()

    return redirect(url_for('case_details', case_id=case_id))


@app.route('/comments/delete/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    """Удаление комментария"""
    if 'user_id' not in session or session['role_id'] not in [1, 2]:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('cases'))

    connection = get_db()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT case_id FROM comments WHERE comment_id = %s", (comment_id,))
        case_id = cursor.fetchone()['case_id']

        cursor.execute("DELETE FROM comments WHERE comment_id = %s", (comment_id,))
        connection.commit()

        flash('Комментарий удалён', 'success')
    except pymysql.Error as e:
        flash(f'Ошибка при удалении комментария: {str(e)}', 'danger')
    finally:
        connection.close()

    return redirect(url_for('case_details', case_id=case_id))


# ===== ПОЛЬЗОВАТЕЛИ (только для администратора) =====

@app.route('/users')
def users():
    if 'user_id' not in session or session['role_id'] != 1:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('dashboard'))

    connection = get_db()
    cursor = connection.cursor()

    # Исключаем администраторов из списка
    cursor.execute("""
        SELECT u.*, r.role_name
        FROM users u
        JOIN user_roles r ON u.role_id = r.role_id
        WHERE u.role_id != 1  -- Скрываем администраторов
        ORDER BY u.created_at DESC
    """)

    users_list = cursor.fetchall()
    connection.close()

    return render_template('users.html', users=users_list, role_id=session['role_id'])


@app.route('/users/add', methods=['GET', 'POST'])
def add_user():
    """Добавление пользователя"""
    if 'user_id' not in session or session['role_id'] != 1:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('users'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM user_roles WHERE role_id != 1 ORDER BY role_id")
    roles = cursor.fetchall()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role_id = request.form.get('role_id', type=int)
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()

        if not all([username, password, role_id, full_name, email]):
            flash('Заполните все обязательные поля', 'danger')
            return render_template('user_form.html', mode='add', roles=roles)

        try:
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE username = %s", (username,))
            if cursor.fetchone()['count'] > 0:
                flash('Пользователь с таким логином уже существует', 'danger')
                return render_template('user_form.html', mode='add', roles=roles)

            cursor.execute("SELECT COUNT(*) as count FROM users WHERE email = %s", (email,))
            if cursor.fetchone()['count'] > 0:
                flash('Пользователь с таким email уже существует', 'danger')
                return render_template('user_form.html', mode='add', roles=roles)

            password_hash = generate_password_hash(password)

            cursor.execute("""
                INSERT INTO users (username, password_hash, role_id, full_name, email, is_active)
                VALUES (%s, %s, %s, %s, %s, TRUE)
            """, (username, password_hash, role_id, full_name, email))

            connection.commit()
            flash('Пользователь успешно добавлен', 'success')
            return redirect(url_for('users'))
        except pymysql.Error as e:
            flash(f'Ошибка при добавлении пользователя: {str(e)}', 'danger')
            return render_template('user_form.html', mode='add', roles=roles)
        finally:
            connection.close()

    connection.close()
    return render_template('user_form.html', mode='add', roles=roles)


@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    """Редактирование пользователя"""
    if 'user_id' not in session or session['role_id'] != 1:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('users'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM user_roles WHERE role_id != 1 ORDER BY role_id")
    roles = cursor.fetchall()

    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('users'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role_id = request.form.get('role_id', type=int)
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        is_active = request.form.get('is_active') == 'on'

        if not all([username, role_id, full_name, email]):
            flash('Заполните все обязательные поля', 'danger')
            return render_template('user_form.html', mode='edit', user=user, roles=roles)

        try:
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE username = %s AND user_id != %s",
                           (username, user_id))
            if cursor.fetchone()['count'] > 0:
                flash('Пользователь с таким логином уже существует', 'danger')
                return render_template('user_form.html', mode='edit', user=user, roles=roles)

            cursor.execute("SELECT COUNT(*) as count FROM users WHERE email = %s AND user_id != %s", (email, user_id))
            if cursor.fetchone()['count'] > 0:
                flash('Пользователь с таким email уже существует', 'danger')
                return render_template('user_form.html', mode='edit', user=user, roles=roles)

            if password:
                password_hash = generate_password_hash(password)
                cursor.execute("""
                    UPDATE users
                    SET username = %s, password_hash = %s, role_id = %s, full_name = %s, email = %s, is_active = %s
                    WHERE user_id = %s
                """, (username, password_hash, role_id, full_name, email, is_active, user_id))
            else:
                cursor.execute("""
                    UPDATE users
                    SET username = %s, role_id = %s, full_name = %s, email = %s, is_active = %s
                    WHERE user_id = %s
                """, (username, role_id, full_name, email, is_active, user_id))

            connection.commit()
            flash('Пользователь успешно обновлён', 'success')
            return redirect(url_for('users'))
        except pymysql.Error as e:
            flash(f'Ошибка при обновлении пользователя: {str(e)}', 'danger')
            return render_template('user_form.html', mode='edit', user=user, roles=roles)
        finally:
            connection.close()

    connection.close()
    return render_template('user_form.html', mode='edit', user=user, roles=roles)


@app.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Удаление пользователя"""
    if 'user_id' not in session or session['role_id'] != 1:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('users'))

    connection = get_db()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        connection.commit()

        flash('Пользователь успешно удалён', 'success')
        return redirect(url_for('users'))
    except pymysql.Error as e:
        flash(f'Ошибка при удалении пользователя: {str(e)}', 'danger')
        return redirect(url_for('users'))
    finally:
        connection.close()


# ===== СПРАВОЧНИКИ (только для администратора) =====

@app.route('/reference')
def reference():
    """Справочники"""
    if 'user_id' not in session or session['role_id'] != 1:
        flash('Нет прав доступа', 'danger')
        return redirect(url_for('dashboard'))

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM user_roles ORDER BY role_id")
    user_roles = cursor.fetchall()

    cursor.execute("SELECT * FROM case_statuses ORDER BY status_id")
    case_statuses = cursor.fetchall()

    cursor.execute("SELECT * FROM case_types ORDER BY type_id")
    case_types = cursor.fetchall()

    cursor.execute("SELECT * FROM case_categories ORDER BY category_id")
    case_categories = cursor.fetchall()

    cursor.execute("SELECT * FROM document_types ORDER BY type_id")
    document_types = cursor.fetchall()

    connection.close()

    return render_template('reference.html',
                           user_roles=user_roles,
                           case_statuses=case_statuses,
                           case_types=case_types,
                           case_categories=case_categories,
                           document_types=document_types,
                           role_id=session['role_id'])


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
# auth.py

import streamlit as st
import hashlib
from sqlalchemy import text
import pandas as pd
from datetime import datetime, timedelta

def init_auth():
    """Инициализация переменных сессии для аутентификации"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "role" not in st.session_state:
        st.session_state.role = None
    if "login_error" not in st.session_state:
        st.session_state.login_error = None
    if "last_activity" not in st.session_state:
        st.session_state.last_activity = datetime.now()

def authenticate(username, password, engine):
    """Проверка учетных данных пользователя"""
    # Простое хеширование пароля
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Запрос к базе данных
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT user_id, username, role, is_active 
            FROM users 
            WHERE username = :username AND password_hash = :password_hash
        """), {"username": username, "password_hash": password_hash}).fetchone()
    
    if result and result.is_active:
        # Успешная аутентификация
        st.session_state.authenticated = True
        st.session_state.username = result.username
        st.session_state.user_id = result.user_id
        st.session_state.role = result.role
        st.session_state.last_activity = datetime.now()
        st.session_state.login_error = None
        return True
    else:
        # Ошибка аутентификации
        st.session_state.login_error = "Неверный логин или пароль"
        return False

def check_authentication():
    """Проверка активной сессии и времени последней активности"""
    # Если пользователь не аутентифицирован, показываем форму логина
    if not st.session_state.get("authenticated", False):
        return False
    
    # Проверяем время последней активности (30 минут)
    if datetime.now() - st.session_state.last_activity > timedelta(minutes=30):
        # Сессия истекла
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.user_id = None
        st.session_state.role = None
        return False
    
    # Обновляем время последней активности
    st.session_state.last_activity = datetime.now()
    return True

def logout():
    """Выход из системы"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_id = None
    st.session_state.role = None

def login_page(engine):
    """Отображение страницы входа"""
    st.title("🔐 Вход в систему")
    
    with st.form("login_form"):
        username = st.text_input("Имя пользователя")
        password = st.text_input("Пароль", type="password")
        submitted = st.form_submit_button("Войти")
        
        if submitted:
            # Пытаемся аутентифицировать и при успехе перезапускаем приложение
            if authenticate(username, password, engine):
                st.rerun()
    
    if st.session_state.login_error:
        st.error(st.session_state.login_error)
    
    # Информация о тестовых пользователях
    with st.expander("Информация для тестирования"):
        st.markdown("""
        ### Тестовые пользователи:
        
        **Администратор**:
        - Логин: admin
        - Пароль: admin123
        
        **Методист**:
        - Логин: methodist
        - Пароль: methodist123
        """)

def show_user_menu():
    """Отображение меню пользователя в боковой панели"""
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Пользователь:** {st.session_state.username}")
    st.sidebar.markdown(f"**Роль:** {st.session_state.role}")
    
    if st.sidebar.button("Выйти"):
        logout()
        st.rerun()

def get_assigned_cards(engine, user_id=None):
    """Получение списка карточек, назначенных пользователю"""
    query = """
    SELECT ca.*, 
           cs.program, cs.module, cs.lesson, cs.gz, cs.card_type,
           u.username, u.full_name
    FROM card_assignments ca
    JOIN cards_structure cs ON ca.card_id = cs.card_id
    JOIN users u ON ca.user_id = u.user_id
    """
    
    params = {}
    
    # Если указан user_id, фильтруем только его карточки
    if user_id:
        query += " WHERE ca.user_id = :user_id"
        params["user_id"] = user_id
    
    query += " ORDER BY ca.updated_at DESC"
    
    with engine.connect() as conn:
        result = pd.read_sql(text(query), conn, params=params)
    
    return result

def assign_card_to_user(engine, card_id, user_id, status="in_progress", notes=None):
    """Назначение карточки пользователю"""
    with engine.begin() as conn:
        # Проверяем, назначена ли уже карточка этому пользователю
        existing = conn.execute(text("""
            SELECT assignment_id FROM card_assignments
            WHERE card_id = :card_id AND user_id = :user_id
        """), {"card_id": card_id, "user_id": user_id}).fetchone()
        
        if existing:
            # Обновляем существующее назначение
            conn.execute(text("""
                UPDATE card_assignments
                SET status = :status, updated_at = CURRENT_TIMESTAMP, notes = :notes
                WHERE assignment_id = :assignment_id
            """), {"status": status, "notes": notes, "assignment_id": existing[0]})
            
            # Записываем историю изменений
            conn.execute(text("""
                INSERT INTO assignment_history (assignment_id, old_status, new_status, changed_by)
                VALUES (:assignment_id, (SELECT status FROM card_assignments WHERE assignment_id = :assignment_id), :new_status, :user_id)
            """), {"assignment_id": existing[0], "new_status": status, "user_id": user_id})
            
            return existing[0]
        else:
            # Создаем новое назначение
            result = conn.execute(text("""
                INSERT INTO card_assignments (card_id, user_id, status, notes)
                VALUES (:card_id, :user_id, :status, :notes)
                RETURNING assignment_id
            """), {"card_id": card_id, "user_id": user_id, "status": status, "notes": notes})
            
            assignment_id = result.fetchone()[0]
            
            # Записываем историю изменений
            conn.execute(text("""
                INSERT INTO assignment_history (assignment_id, old_status, new_status, changed_by)
                VALUES (:assignment_id, NULL, :new_status, :user_id)
            """), {"assignment_id": assignment_id, "new_status": status, "user_id": user_id})
            
            return assignment_id

def update_card_status(engine, assignment_id, new_status, user_id, comment=None):
    """Обновление статуса карточки"""
    with engine.begin() as conn:
        # Получаем текущий статус
        old_status = conn.execute(text("""
            SELECT status FROM card_assignments WHERE assignment_id = :assignment_id
        """), {"assignment_id": assignment_id}).fetchone()[0]
        
        # Обновляем статус
        conn.execute(text("""
            UPDATE card_assignments
            SET status = :status, updated_at = CURRENT_TIMESTAMP
            WHERE assignment_id = :assignment_id
        """), {"status": new_status, "assignment_id": assignment_id})
        
        # Записываем историю изменений
        conn.execute(text("""
            INSERT INTO assignment_history (assignment_id, old_status, new_status, changed_by, comment)
            VALUES (:assignment_id, :old_status, :new_status, :user_id, :comment)
        """), {
            "assignment_id": assignment_id, 
            "old_status": old_status, 
            "new_status": new_status, 
            "user_id": user_id,
            "comment": comment
        })
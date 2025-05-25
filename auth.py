# auth.py

import streamlit as st
import hashlib
from sqlalchemy import text
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

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
    if "user_data" not in st.session_state:
        st.session_state.user_data = None

def get_user_data(engine, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает данные пользователя из базы данных
    
    Args:
        engine: SQLAlchemy engine
        user_id: ID пользователя
        
    Returns:
        Dict с данными пользователя или None, если пользователь не найден
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT user_id, username, email, full_name, role, is_active
                FROM users 
                WHERE user_id = :user_id
            """), {"user_id": user_id}).fetchone()
            
            if result:
                return {
                    "user_id": result.user_id,
                    "username": result.username,
                    "email": result.email,
                    "full_name": result.full_name,
                    "role": result.role,
                    "is_active": result.is_active
                }
            return None
    except Exception as e:
        st.error(f"Ошибка при получении данных пользователя: {str(e)}")
        return None

def authenticate(username: str, password: str, engine) -> bool:
    """
    Проверка учетных данных пользователя
    
    Args:
        username: Имя пользователя
        password: Пароль
        engine: SQLAlchemy engine
        
    Returns:
        bool: True если аутентификация успешна, False в противном случае
    """
    try:
        # Простое хеширование пароля
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Запрос к базе данных
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT user_id, username, email, full_name, role, is_active 
                FROM users 
                WHERE username = :username AND password_hash = :password_hash
            """), {"username": username, "password_hash": password_hash}).fetchone()
        
        if result and result.is_active:
            # Успешная аутентификация
            user_data = {
                "user_id": result.user_id,
                "username": result.username,
                "email": result.email,
                "full_name": result.full_name,
                "role": result.role,
                "is_active": result.is_active
            }
            
            st.session_state.authenticated = True
            st.session_state.username = result.username
            st.session_state.user_id = result.user_id
            st.session_state.role = result.role
            st.session_state.user_data = user_data
            st.session_state.last_activity = datetime.now()
            st.session_state.login_error = None
            return True
        else:
            # Ошибка аутентификации
            st.session_state.login_error = "Неверный логин или пароль"
            return False
    except Exception as e:
        st.error(f"Ошибка при аутентификации: {str(e)}")
        st.session_state.login_error = "Ошибка при аутентификации"
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
    """Выход из системы и полный сброс состояния сессии и URL."""
    # Сохраняем ключи, которые не нужно удалять (если есть, например, связанные с темами Streamlit)
    # В данном случае, кажется, можно удалять все, так как init_auth() их пересоздаст.
    # Но для безопасности, можно выборочно или копировать st.session_state и чистить.
    
    # Простой способ: очистить все ключи
    keys_to_delete = list(st.session_state.keys())
    for key in keys_to_delete:
        del st.session_state[key]
    
    # Переинициализируем базовые ключи аутентификации (на всякий случай, если init_auth() не вызовется до следующей проверки)
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_id = None
    st.session_state.role = None
    st.session_state.user_data = None
    st.session_state.last_activity = None
    st.session_state.login_error = None
    # Важно также сбросить current_page и фильтры, но удаление всех ключей это уже делает
    # st.session_state.current_page = "Обзор" # или None
    # st.session_state.filter_program = None
    # ... и другие фильтры ...

    # Сбрасываем URL на базовый (например, страница обзора или корень)
    # Это предотвратит загрузку последней страницы предыдущего пользователя для нового.
    st.query_params.clear() # Очищаем все текущие query_params
    st.query_params = {"page": "overview"} # Устанавливаем на страницу обзора
    print("[LOGOUT] Session state cleared and query_params reset to overview.")
    # st.rerun() вызывается в show_user_menu после вызова logout()

def login_page(engine):
    """Отображение страницы входа и регистрации"""
    
    # Используем st.query_params для определения, какую вкладку показать по умолчанию
    query_params = st.query_params
    active_tab_key = query_params.get("form", "login") # "login" или "register"

    # Создаем вкладки
    # Чтобы управлять активной вкладкой через URL, нам нужен более сложный подход или использование компонента.
    # Streamlit st.tabs не позволяет напрямую управлять активной вкладкой через код после создания.
    # Простой вариант: две разные формы, показываемые по условию.
    # Более продвинутый: кнопки, меняющие параметр в URL, который затем используется для выбора формы.

    # Для простоты, пока сделаем две секции и дадим пользователю возможность выбрать.
    # Или можно использовать радиокнопки для выбора действия.

    action_choice = st.radio("Выберите действие:", ("Вход", "Регистрация"), horizontal=True, key="action_choice")

    if action_choice == "Вход":
        st.subheader("🔐 Вход в систему")
        with st.form("login_form"):
            username_login = st.text_input("Имя пользователя", key="login_username")
            password_login = st.text_input("Пароль", type="password", key="login_password")
            submitted_login = st.form_submit_button("Войти")
            
            if submitted_login:
                if authenticate(username_login, password_login, engine):
                    # Сбрасываем query_params, чтобы при обновлении не оставался ?form=register
                    st.query_params.clear()
                    st.query_params = {"page": st.session_state.get("current_page", "overview").lower().replace(" ","_")}
                    st.rerun()
        
        if st.session_state.get("login_error"):
            st.error(st.session_state.login_error)

    elif action_choice == "Регистрация":
        st.subheader("📝 Регистрация нового пользователя")
        with st.form("register_form"):
            reg_username = st.text_input("Имя пользователя (логин)", key="reg_username")
            reg_email = st.text_input("Email", key="reg_email")
            reg_full_name = st.text_input("Полное имя", key="reg_fullname")
            reg_password = st.text_input("Пароль (мин. 6 символов)", type="password", key="reg_password")
            reg_password_confirm = st.text_input("Подтвердите пароль", type="password", key="reg_password_confirm")
            
            # Выбор роли (можно сделать более гибким, если ролей много)
            available_roles = ["methodist", "admin"] # Пример
            reg_role = st.selectbox("Роль", available_roles, key="reg_role")
            
            submitted_register = st.form_submit_button("Зарегистрироваться")

            if submitted_register:
                if reg_password != reg_password_confirm:
                    st.error("Пароли не совпадают!")
                else:
                    success, message = register_user(engine, reg_username, reg_password, reg_email, reg_full_name, reg_role)
                    if success:
                        st.success("Пользователь успешно зарегистрирован! Теперь вы можете войти.")
                        # Можно автоматически переключить на вкладку входа или предложить это
                        # Для простоты, пользователь сам переключится.
                    else:
                        st.error(message)
    
    # Информация о тестовых пользователях (можно оставить или убрать для регистрации)
    with st.expander("Информация для тестирования (существующие пользователи)"):
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
    user_col1, user_col2 = st.sidebar.columns([3, 1])
    
    with user_col1:
        if st.session_state.user_data and st.session_state.user_data.get("full_name"):
            st.markdown(f"👤 **{st.session_state.user_data['full_name']}**")
        else:
            st.markdown(f"👤 **{st.session_state.username}**")
        st.markdown(f"*{st.session_state.role}*")
    
    with user_col2:
        if st.button("Выход", key="logout_button"):
            logout()
            st.rerun()

def get_assigned_cards(engine, user_id: Optional[int] = None) -> pd.DataFrame:
    """
    Получение списка карточек, назначенных пользователю
    
    Args:
        engine: SQLAlchemy engine
        user_id: ID пользователя (опционально)
        
    Returns:
        DataFrame с данными о назначенных карточках
    """
    try:
        query = """
        SELECT 
            ca.assignment_id,
            ca.card_id,
            ca.user_id,
            ca.status,
            ca.assigned_at,
            ca.updated_at,
            ca.notes,
            cs.program_name,
            cs.module_name,
            cs.lesson_name,
            cs.gz_name,
            cs.card_type,
            cs.card_url,
            u.username,
            u.full_name,
            u.email
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
    except Exception as e:
        st.error(f"Ошибка при получении назначенных карточек: {str(e)}")
        return pd.DataFrame()

def assign_card_to_user(
    engine,
    card_id: int,
    user_id: int,
    status: str = "in_progress",
    notes: Optional[str] = None
) -> Optional[int]:
    """
    Назначение карточки пользователю
    
    Args:
        engine: SQLAlchemy engine
        card_id: ID карточки
        user_id: ID пользователя
        status: Статус назначения
        notes: Заметки к назначению
        
    Returns:
        ID назначения или None в случае ошибки
    """
    try:
        with engine.begin() as conn:
            # Проверяем, назначена ли уже карточка этому пользователю
            existing = conn.execute(text("""
                SELECT assignment_id, status FROM card_assignments
                WHERE card_id = :card_id AND user_id = :user_id
            """), {"card_id": card_id, "user_id": user_id}).fetchone()
            
            if existing:
                # Обновляем существующее назначение
                conn.execute(text("""
                    UPDATE card_assignments
                    SET status = :status,
                        updated_at = CURRENT_TIMESTAMP,
                        notes = :notes
                    WHERE assignment_id = :assignment_id
                """), {
                    "status": status,
                    "notes": notes,
                    "assignment_id": existing.assignment_id
                })
                
                # Записываем историю изменений
                conn.execute(text("""
                    INSERT INTO assignment_history 
                    (assignment_id, old_status, new_status, changed_by, change_time)
                    VALUES (:assignment_id, :old_status, :new_status, :user_id, CURRENT_TIMESTAMP)
                """), {
                    "assignment_id": existing.assignment_id,
                    "old_status": existing.status,
                    "new_status": status,
                    "user_id": user_id
                })
                
                return existing.assignment_id
            else:
                # Создаем новое назначение
                result = conn.execute(text("""
                    INSERT INTO card_assignments 
                    (card_id, user_id, status, notes, assigned_at, updated_at)
                    VALUES (:card_id, :user_id, :status, :notes, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING assignment_id
                """), {
                    "card_id": card_id,
                    "user_id": user_id,
                    "status": status,
                    "notes": notes
                })
                
                assignment_id = result.fetchone()[0]
                
                # Записываем историю изменений
                conn.execute(text("""
                    INSERT INTO assignment_history 
                    (assignment_id, old_status, new_status, changed_by, change_time)
                    VALUES (:assignment_id, NULL, :new_status, :user_id, CURRENT_TIMESTAMP)
                """), {
                    "assignment_id": assignment_id,
                    "new_status": status,
                    "user_id": user_id
                })
                
                return assignment_id
    except Exception as e:
        st.error(f"Ошибка при назначении карточки: {str(e)}")
        return None

def update_card_status(
    engine,
    assignment_id: int,
    new_status: str,
    user_id: int,
    comment: Optional[str] = None
) -> bool:
    """
    Обновление статуса карточки
    
    Args:
        engine: SQLAlchemy engine
        assignment_id: ID назначения
        new_status: Новый статус
        user_id: ID пользователя, вносящего изменения
        comment: Комментарий к изменению
        
    Returns:
        bool: True если обновление успешно, False в случае ошибки
    """
    try:
        with engine.begin() as conn:
            # Получаем текущий статус
            current = conn.execute(text("""
                SELECT status FROM card_assignments 
                WHERE assignment_id = :assignment_id
            """), {"assignment_id": assignment_id}).fetchone()
            
            if not current:
                st.error("Назначение не найдено")
                return False
            
            old_status = current.status
            
            # Обновляем статус
            conn.execute(text("""
                UPDATE card_assignments
                SET status = :status,
                    updated_at = CURRENT_TIMESTAMP
                WHERE assignment_id = :assignment_id
            """), {
                "status": new_status,
                "assignment_id": assignment_id
            })
            
            # Записываем историю изменений
            conn.execute(text("""
                INSERT INTO assignment_history 
                (assignment_id, old_status, new_status, changed_by, change_time, comment)
                VALUES (:assignment_id, :old_status, :new_status, :user_id, CURRENT_TIMESTAMP, :comment)
            """), {
                "assignment_id": assignment_id,
                "old_status": old_status,
                "new_status": new_status,
                "user_id": user_id,
                "comment": comment
            })
            
            return True
    except Exception as e:
        st.error(f"Ошибка при обновлении статуса: {str(e)}")
        return False

def get_assignment_history(engine, assignment_id: int) -> pd.DataFrame:
    """
    Получение истории изменений назначения
    
    Args:
        engine: SQLAlchemy engine
        assignment_id: ID назначения
        
    Returns:
        DataFrame с историей изменений
    """
    try:
        query = """
        SELECT 
            ah.history_id,
            ah.assignment_id,
            ah.old_status,
            ah.new_status,
            ah.changed_by,
            ah.change_time,
            ah.comment,
            u.username,
            u.full_name
        FROM assignment_history ah
        JOIN users u ON ah.changed_by = u.user_id
        WHERE ah.assignment_id = :assignment_id
        ORDER BY ah.change_time DESC
        """
        
        with engine.connect() as conn:
            result = pd.read_sql(
                text(query),
                conn,
                params={"assignment_id": assignment_id}
            )
        
        return result
    except Exception as e:
        st.error(f"Ошибка при получении истории изменений: {str(e)}")
        return pd.DataFrame()

def register_user(engine, username, password, email, full_name, role="methodist") -> tuple[bool, Optional[str]]:
    """
    Регистрирует нового пользователя в системе.

    Args:
        engine: SQLAlchemy engine.
        username (str): Имя пользователя (логин).
        password (str): Пароль.
        email (str): Email пользователя.
        full_name (str): Полное имя пользователя.
        role (str): Роль пользователя (по умолчанию 'methodist').

    Returns:
        tuple[bool, Optional[str]]: (True, None) при успехе, (False, "сообщение об ошибке") при неудаче.
    """
    if not username or not password or not email:
        return False, "Имя пользователя, пароль и email не могут быть пустыми."
    
    # Проверка длины пароля (пример)
    if len(password) < 6:
        return False, "Пароль должен быть не менее 6 символов."

    try:
        # Используем engine.begin() для явного управления транзакцией на уровне engine
        with engine.begin() as conn: # conn здесь будет частью внешней транзакции
            # Проверка, существует ли уже пользователь с таким username
            res_username = conn.execute(text("SELECT user_id FROM users WHERE username = :username"), {"username": username}).fetchone()
            if res_username:
                # Мы не хотим откатывать транзакцию здесь, просто возвращаем ошибку
                return False, f"Пользователь с именем '{username}' уже существует."
            
            # Проверка, существует ли уже пользователь с таким email
            res_email = conn.execute(text("SELECT user_id FROM users WHERE email = :email"), {"email": email}).fetchone()
            if res_email:
                return False, f"Пользователь с email '{email}' уже существует."
            
            # Хеширование пароля
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Вставка нового пользователя
            conn.execute(text("""
                INSERT INTO users (username, password_hash, email, full_name, role, is_active)
                VALUES (:username, :password_hash, :email, :full_name, :role, :is_active)
            """), {
                "username": username,
                "password_hash": password_hash,
                "email": email,
                "full_name": full_name,
                "role": role,
                "is_active": True 
            })
            # Если мы дошли сюда без ошибок, engine.begin() автоматически закоммитит транзакцию при выходе из блока with
            return True, None
            # Явный trans.commit() или trans.rollback() не нужны при использовании with engine.begin()

    except Exception as e:
        # Если возникла любая ошибка (включая ошибки уникальности constraint violation при INSERT, 
        # которые могли быть не пойманы проверками выше, если они не атомарны с INSERT),
        # with engine.begin() автоматически откатит транзакцию.
        print(f"Error in register_user (transaction rolled back): {e}")
        # Можно вернуть более специфичное сообщение, если e - это ошибка БД
        if "UNIQUE constraint failed" in str(e) or "duplicate key value violates unique constraint" in str(e):
             return False, "Имя пользователя или email уже заняты (ошибка БД)."
        return False, f"Общая ошибка при регистрации: {e}"
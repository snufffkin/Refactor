# create_auth_tables.py

import pandas as pd
import hashlib
from sqlalchemy import create_engine, text
import os

# Получаем строку подключения из переменной окружения или используем дефолтную
DB_PATH = os.getenv("DB_DSN", "postgresql:///course_quality")
engine = create_engine(DB_PATH, future=True)

# SQL для создания таблицы пользователей
with engine.begin() as conn:
    conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(128) NOT NULL,
            email VARCHAR(100) UNIQUE,
            full_name VARCHAR(100),
            role VARCHAR(20) NOT NULL DEFAULT 'methodist',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # SQL для создания таблицы назначенных карточек
    conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS card_assignments (
            assignment_id SERIAL PRIMARY KEY,
            card_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(user_id),
            status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            UNIQUE(card_id, user_id) -- Карточка может быть назначена пользователю только один раз
        );
    """)
    
    # SQL для создания таблицы истории изменений
    conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS assignment_history (
            history_id SERIAL PRIMARY KEY,
            assignment_id INTEGER NOT NULL REFERENCES card_assignments(assignment_id),
            old_status VARCHAR(20),
            new_status VARCHAR(20) NOT NULL,
            changed_by INTEGER NOT NULL REFERENCES users(user_id),
            change_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            comment TEXT
        );
    """)
    
    # Добавляем админа (пароль: admin123)
    admin_password = "admin123"
    # Простое хеширование пароля
    password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
    
    # Проверяем, существует ли пользователь admin
    admin_exists = conn.execute(text(
        "SELECT 1 FROM users WHERE username = 'admin'"
    )).fetchone()
    
    if not admin_exists:
        conn.execute(text("""
            INSERT INTO users (username, password_hash, role, full_name, email)
            VALUES (:username, :password_hash, 'admin', 'Администратор', 'admin@example.com')
        """), {"username": "admin", "password_hash": password_hash})
        print("Admin user created.")
    
    # Добавляем тестового методиста (пароль: methodist123)
    methodist_password = "methodist123"
    password_hash = hashlib.sha256(methodist_password.encode()).hexdigest()
    
    methodist_exists = conn.execute(text(
        "SELECT 1 FROM users WHERE username = 'methodist'"
    )).fetchone()
    
    if not methodist_exists:
        conn.execute(text("""
            INSERT INTO users (username, password_hash, role, full_name, email)
            VALUES (:username, :password_hash, 'methodist', 'Тестовый методист', 'methodist@example.com')
        """), {"username": "methodist", "password_hash": password_hash})
        print("Test methodist user created.")

print("✓ Auth tables created successfully.")
#!/bin/bash

# setup_db.sh - Скрипт для настройки базы данных PostgreSQL для приложения Course Quality Dashboard
# Используется для настройки базы данных на виртуальной машине Ubuntu

set -e  # Остановка скрипта при ошибке

echo "-----------------------------------------------------"
echo "  Настройка базы данных PostgreSQL для приложения"
echo "-----------------------------------------------------"

# 1. Проверка и установка PostgreSQL, если он не установлен
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL не установлен. Установка..."
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
    echo "PostgreSQL установлен."
else
    echo "PostgreSQL уже установлен."
fi

# 2. Создание базы данных и пользователя
echo "Создание базы данных course_quality..."
sudo -u postgres psql -c "CREATE DATABASE course_quality;" || echo "База данных уже существует."
sudo -u postgres psql -c "CREATE USER $USER WITH PASSWORD '$USER';" || echo "Пользователь уже существует."
sudo -u postgres psql -c "ALTER ROLE $USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $USER SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE course_quality TO $USER;"
echo "База данных и пользователь настроены."

# 3. Создание и настройка таблиц в базе данных
echo "Создание таблиц в базе данных..."

# Создание структуры таблиц
psql -d course_quality << EOF
-- Таблица cards_structure
CREATE TABLE IF NOT EXISTS cards_structure(
    program TEXT,
    module TEXT,
    module_order INTEGER,
    lesson TEXT,
    lesson_order INTEGER,
    gz TEXT,
    gz_id INTEGER,
    card_id INTEGER PRIMARY KEY,
    card_type TEXT,
    card_url TEXT
);

-- Таблица card_status
CREATE TABLE IF NOT EXISTS card_status(
    card_id     INTEGER PRIMARY KEY,
    status      TEXT DEFAULT 'new',
    updated_by  TEXT,
    updated_at  TEXT
);

-- Таблица cards_metrics (пустая таблица для метрик)
CREATE TABLE IF NOT EXISTS cards_metrics(
    card_id INTEGER PRIMARY KEY,
    total_attempts INTEGER,
    attempted_share FLOAT,
    success_rate FLOAT,
    first_try_success_rate FLOAT,
    complaint_rate FLOAT,
    complaints_total INTEGER,
    discrimination_avg FLOAT,
    success_attempts_rate FLOAT
);

-- Представление cards_mv
DROP VIEW IF EXISTS cards_mv;
CREATE OR REPLACE VIEW cards_mv AS
SELECT
    s.program, s.module, s.module_order, s.lesson, s.lesson_order,
    s.gz, s.gz_id, s.card_id, s.card_type, s.card_url,
    m.total_attempts, m.attempted_share, m.success_rate,
    m.first_try_success_rate, m.complaint_rate, m.complaints_total,
    m.discrimination_avg, m.success_attempts_rate,
    COALESCE(st.status,'new') AS status, st.updated_at
FROM cards_structure s
LEFT JOIN cards_metrics m USING(card_id)
LEFT JOIN card_status st USING(card_id);

-- Таблица учителей для аутентификации
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

-- Таблица назначенных карточек
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

-- Таблица истории изменений
CREATE TABLE IF NOT EXISTS assignment_history (
    history_id SERIAL PRIMARY KEY,
    assignment_id INTEGER NOT NULL REFERENCES card_assignments(assignment_id),
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_by INTEGER NOT NULL REFERENCES users(user_id),
    change_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    comment TEXT
);

-- Добавление пользователей для аутентификации
-- Пароль admin123
INSERT INTO users (username, password_hash, role, full_name, email)
VALUES ('admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin', 'Администратор', 'admin@example.com')
ON CONFLICT (username) DO NOTHING;

-- Пароль methodist123
INSERT INTO users (username, password_hash, role, full_name, email)
VALUES ('methodist', 'e25f35740fadb5af91b79af51fc5bacfe429800c1d0304465c2f194ae07701e8', 'methodist', 'Тестовый методист', 'methodist@example.com')
ON CONFLICT (username) DO NOTHING;
EOF

echo "Таблицы успешно созданы в базе данных."

# 4. Настройка переменной окружения для подключения к базе данных
echo "Настройка переменной окружения..."

# Добавление переменной окружения в .bashrc или .zshrc
if [ -f "$HOME/.bashrc" ]; then
    if ! grep -q "DB_DSN=" "$HOME/.bashrc"; then
        echo 'export DB_DSN="postgresql:///course_quality"' >> "$HOME/.bashrc"
    fi
fi

if [ -f "$HOME/.zshrc" ]; then
    if ! grep -q "DB_DSN=" "$HOME/.zshrc"; then
        echo 'export DB_DSN="postgresql:///course_quality"' >> "$HOME/.zshrc"
    fi
fi

# Экспорт переменной в текущую сессию
export DB_DSN="postgresql:///course_quality"

echo "Переменная окружения DB_DSN настроена."
echo "-----------------------------------------------------"
echo "  Настройка базы данных успешно завершена!"
echo "-----------------------------------------------------"
echo "Дополнительно рекомендуется запустить скрипт optimize_db.py для создания"
echo "индексов и материализованных представлений для ускорения работы приложения." 
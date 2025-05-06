#!/bin/bash

# fix_db_import_v2.sh - Исправление проблем с импортом данных
# Для использования на виртуальной машине Ubuntu

set -e  # Остановка скрипта при ошибке

echo "-----------------------------------------------------"
echo "  Полное пересоздание таблиц и импорт данных"
echo "-----------------------------------------------------"

# Активация переменной окружения для текущей сессии
export DB_DSN="postgresql:///course_quality"
echo "Переменная окружения DB_DSN установлена: $DB_DSN"

# Проверяем доступ к базе данных
echo "Проверка подключения к PostgreSQL..."
if ! psql -d course_quality -c "SELECT 1;" > /dev/null 2>&1; then
    echo "ОШИБКА: Не удалось подключиться к базе данных course_quality."
    exit 1
fi

# Полное удаление и пересоздание таблиц
echo "Полное пересоздание таблиц..."
psql -d course_quality << EOF
-- Удаляем представление
DROP VIEW IF EXISTS cards_mv;

-- Удаляем зависимые таблицы
DROP TABLE IF EXISTS card_assignments CASCADE;
DROP TABLE IF EXISTS assignment_history CASCADE;

-- Основные таблицы
DROP TABLE IF EXISTS cards_structure CASCADE;
DROP TABLE IF EXISTS cards_metrics CASCADE;
DROP TABLE IF EXISTS card_status CASCADE;

-- Заново создаем таблицы
CREATE TABLE cards_structure(
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

CREATE TABLE cards_metrics(
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

CREATE TABLE card_status(
    card_id INTEGER PRIMARY KEY,
    status TEXT DEFAULT 'new',
    updated_by TEXT,
    updated_at TEXT
);

-- Воссоздаем представление
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

-- Пересоздаем таблицы для назначений
CREATE TABLE IF NOT EXISTS card_assignments (
    assignment_id SERIAL PRIMARY KEY,
    card_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    UNIQUE(card_id, user_id)
);

CREATE TABLE IF NOT EXISTS assignment_history (
    history_id SERIAL PRIMARY KEY,
    assignment_id INTEGER NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_by INTEGER NOT NULL,
    change_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    comment TEXT
);
EOF

echo "Таблицы успешно пересозданы."

# Удаление дубликатов из файлов CSV
echo "Обработка CSV-файлов для удаления дубликатов..."

# Обработка cards_structure.csv - удаление дубликатов
echo "Обработка cards_structure.csv..."
awk -F, 'NR==1 {header=$0; print; next} !seen[$8]++ {print}' db_export/cards_structure.csv > db_export/cards_structure_unique.csv
mv db_export/cards_structure_unique.csv db_export/cards_structure.csv

# Обработка cards_metrics.csv - удаление дубликатов
echo "Обработка cards_metrics.csv..."
awk -F, 'NR==1 {header=$0; print; next} !seen[$1]++ {print}' db_export/cards_metrics.csv > db_export/cards_metrics_unique.csv
mv db_export/cards_metrics_unique.csv db_export/cards_metrics.csv

# Обработка card_status.csv - удаление дубликатов
echo "Обработка card_status.csv..."
awk -F, 'NR==1 {header=$0; print; next} !seen[$1]++ {print}' db_export/card_status.csv > db_export/card_status_unique.csv
mv db_export/card_status_unique.csv db_export/card_status.csv

# Конвертация UTF-8 с BOM в обычный UTF-8 (если есть)
for file in db_export/*.csv; do
    # Проверяем наличие BOM
    if [ $(hexdump -n 3 -v -e '1/1 "%02X"' "$file") = "EFBBBF" ]; then
        echo "Удаление BOM из файла $(basename "$file")..."
        (sed '1s/^\xEF\xBB\xBF//' < "$file" > "${file}.tmp" && mv "${file}.tmp" "$file")
    fi
done

# Импорт данных с использованием psql -c
echo "Импорт данных cards_structure..."
psql -d course_quality -c "\COPY cards_structure FROM 'db_export/cards_structure.csv' WITH CSV HEADER" || {
    echo "ОШИБКА: Не удалось импортировать cards_structure."
    exit 1
}

echo "Импорт данных cards_metrics..."
psql -d course_quality -c "\COPY cards_metrics FROM 'db_export/cards_metrics.csv' WITH CSV HEADER" || {
    echo "ОШИБКА: Не удалось импортировать cards_metrics."
    exit 1
}

echo "Импорт данных card_status..."
psql -d course_quality -c "\COPY card_status FROM 'db_export/card_status.csv' WITH CSV HEADER" || {
    echo "ОШИБКА: Не удалось импортировать card_status."
    exit 1
}

# Проверка результатов импорта
echo "Проверка результатов импорта..."
cards_structure_count=$(psql -d course_quality -t -c "SELECT COUNT(*) FROM cards_structure;")
cards_metrics_count=$(psql -d course_quality -t -c "SELECT COUNT(*) FROM cards_metrics;")
card_status_count=$(psql -d course_quality -t -c "SELECT COUNT(*) FROM card_status;")

echo "Количество записей в cards_structure: $cards_structure_count"
echo "Количество записей в cards_metrics: $cards_metrics_count"
echo "Количество записей в card_status: $card_status_count"

# Создание необходимых индексов
echo "Создание индексов..."
psql -d course_quality -c "CREATE INDEX IF NOT EXISTS idx_cards_structure_program ON cards_structure(program);"
psql -d course_quality -c "CREATE INDEX IF NOT EXISTS idx_cards_structure_module ON cards_structure(module);"
psql -d course_quality -c "CREATE INDEX IF NOT EXISTS idx_cards_structure_lesson ON cards_structure(lesson);"
psql -d course_quality -c "CREATE INDEX IF NOT EXISTS idx_cards_structure_gz ON cards_structure(gz);"

# Обеспечение переменной окружения
echo "Обеспечение переменной окружения DB_DSN..."

# В файле запуска приложения
if [ -f "start.sh" ]; then
    grep -q "export DB_DSN=" "start.sh" || sed -i '1s/^/export DB_DSN="postgresql:\/\/\/course_quality"\n/' "start.sh"
    chmod +x start.sh
    echo "Переменная окружения добавлена в start.sh"
fi

# Создание файла .env
echo 'DB_DSN="postgresql:///course_quality"' > .env
echo "Создан файл .env с переменной окружения"

echo "-----------------------------------------------------"
echo "  Импорт данных завершен успешно!"
echo "-----------------------------------------------------"
echo "Теперь перезапустите приложение со следующими командами:"
echo "export DB_DSN=\"postgresql:///course_quality\""
echo "cd ~/app && ./start.sh"
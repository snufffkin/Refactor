#!/bin/bash

# fix_db_import.sh - Скрипт для исправления проблем с импортом данных
# Для использования на виртуальной машине Ubuntu

set -e  # Остановка скрипта при ошибке

echo "-----------------------------------------------------"
echo "  Исправление проблем с импортом данных в PostgreSQL"
echo "-----------------------------------------------------"

# Проверка наличия необходимых файлов
if [ ! -d "db_export" ]; then
    echo "ОШИБКА: Папка db_export не найдена. Проверьте, был ли распакован архив db_export.tar.gz."
    exit 1
fi

# Активация переменной окружения для текущей сессии
export DB_DSN="postgresql:///course_quality"
echo "Переменная окружения DB_DSN установлена: $DB_DSN"

# Проверяем доступ к базе данных
echo "Проверка подключения к PostgreSQL..."
if ! psql -d course_quality -c "SELECT 1;" > /dev/null 2>&1; then
    echo "ОШИБКА: Не удалось подключиться к базе данных course_quality."
    echo "Проверьте, запущен ли PostgreSQL и создана ли база данных."
    exit 1
fi

# Очистка таблиц перед импортом
echo "Очистка таблиц перед импортом..."
psql -d course_quality -c "TRUNCATE cards_structure, cards_metrics, card_status CASCADE;"

# Исправление файлов CSV (удаление mac-специфичных файлов и строк)
echo "Подготовка файлов для импорта..."
for file in db_export/*.csv; do
    # Пропускаем файлы с префиксом ._
    if [[ $(basename "$file") == ._* ]]; then
        continue
    fi
    
    # Удаляем символы CR (macOS) и пустые строки
    cat "$file" | tr -d '\r' | grep -v '^$' > "${file}.tmp"
    mv "${file}.tmp" "$file"
    echo "Файл $(basename "$file") подготовлен."
done

# Импорт данных с подробным выводом ошибок
echo "Импорт данных cards_structure..."
if ! psql -d course_quality -c "\COPY cards_structure FROM 'db_export/cards_structure.csv' WITH CSV HEADER"; then
    echo "ПРЕДУПРЕЖДЕНИЕ: Ошибка при импорте cards_structure. Попытка альтернативного метода..."
    psql -d course_quality -c "COPY cards_structure FROM STDIN WITH CSV HEADER" < db_export/cards_structure.csv
fi

echo "Импорт данных cards_metrics..."
if ! psql -d course_quality -c "\COPY cards_metrics FROM 'db_export/cards_metrics.csv' WITH CSV HEADER"; then
    echo "ПРЕДУПРЕЖДЕНИЕ: Ошибка при импорте cards_metrics. Попытка альтернативного метода..."
    psql -d course_quality -c "COPY cards_metrics FROM STDIN WITH CSV HEADER" < db_export/cards_metrics.csv
fi

echo "Импорт данных card_status..."
if ! psql -d course_quality -c "\COPY card_status FROM 'db_export/card_status.csv' WITH CSV HEADER"; then
    echo "ПРЕДУПРЕЖДЕНИЕ: Ошибка при импорте card_status. Попытка альтернативного метода..."
    psql -d course_quality -c "COPY card_status FROM STDIN WITH CSV HEADER" < db_export/card_status.csv
fi

# Проверка результатов импорта
echo "Проверка результатов импорта..."
cards_structure_count=$(psql -d course_quality -t -c "SELECT COUNT(*) FROM cards_structure;")
cards_metrics_count=$(psql -d course_quality -t -c "SELECT COUNT(*) FROM cards_metrics;")
card_status_count=$(psql -d course_quality -t -c "SELECT COUNT(*) FROM card_status;")

echo "Количество записей в cards_structure: $cards_structure_count"
echo "Количество записей в cards_metrics: $cards_metrics_count"
echo "Количество записей в card_status: $card_status_count"

# Создание необходимых индексов и материализованных представлений
echo "Создание индексов и материализованных представлений..."
if [ -f "optimize_db.py" ]; then
    python optimize_db.py
else
    # Создаем базовые индексы, если скрипт оптимизации не найден
    psql -d course_quality -c "CREATE INDEX IF NOT EXISTS idx_structure_card_id ON cards_structure(card_id);"
    psql -d course_quality -c "CREATE INDEX IF NOT EXISTS idx_metrics_card_id ON cards_metrics(card_id);"
    psql -d course_quality -c "CREATE INDEX IF NOT EXISTS idx_status_card_id ON card_status(card_id);"
fi

# Обновляем переменную окружения в .bash_profile и .profile
if [ -f "$HOME/.bash_profile" ]; then
    if ! grep -q "DB_DSN=" "$HOME/.bash_profile"; then
        echo 'export DB_DSN="postgresql:///course_quality"' >> "$HOME/.bash_profile"
        echo "Переменная окружения добавлена в .bash_profile"
    fi
fi

if [ -f "$HOME/.profile" ]; then
    if ! grep -q "DB_DSN=" "$HOME/.profile"; then
        echo 'export DB_DSN="postgresql:///course_quality"' >> "$HOME/.profile"
        echo "Переменная окружения добавлена в .profile"
    fi
fi

# Обновляем переменную окружения в файле запуска приложения
if [ -f "start.sh" ]; then
    if ! grep -q "DB_DSN=" "start.sh"; then
        sed -i '1s/^/export DB_DSN="postgresql:\/\/\/course_quality"\n/' start.sh
        echo "Переменная окружения добавлена в start.sh"
    fi
fi

echo "-----------------------------------------------------"
echo "  Процесс импорта данных завершен!"
echo "-----------------------------------------------------"
echo "Если приложение всё ещё показывает 'nan', перезапустите его:"
echo "export DB_DSN=\"postgresql:///course_quality\""
echo "cd ~/app && ./start.sh"
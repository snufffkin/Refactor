#!/bin/bash

# fix_db_import_v3.sh - Скрипт для исправления проблем с импортом данных
# Использует более надежные методы для удаления дубликатов

set -e  # Остановка скрипта при ошибке

echo "-----------------------------------------------------"
echo "  Исправление проблем импорта с удалением дубликатов"
echo "-----------------------------------------------------"

# Активируем переменную окружения
export DB_DSN="postgresql:///course_quality"
echo "Переменная окружения DB_DSN установлена: $DB_DSN"

# Проверяем, установлен ли Python
if ! command -v python3 &> /dev/null; then
    echo "Python не установлен. Установка Python..."
    sudo apt update
    sudo apt install -y python3 python3-pip
fi

# Создаем Python-скрипт для обработки CSV файлов
cat > process_csv.py << 'EOL'
#!/usr/bin/env python3
import csv
import sys

def process_csv(input_file, output_file, key_column):
    """
    Обрабатывает CSV файл, удаляя дубликаты по указанному ключевому столбцу.
    Сохраняет только первое вхождение каждого ключа.
    """
    print(f"Обработка файла {input_file}, ключевой столбец: {key_column}")
    
    # Чтение CSV файла
    with open(input_file, 'r', encoding='utf-8-sig') as infile:
        # Используем 'utf-8-sig' для правильной обработки BOM
        reader = csv.reader(infile)
        header = next(reader)  # Сохраняем заголовок
        
        # Находим индекс указанного столбца
        try:
            key_index = header.index(key_column)
        except ValueError:
            print(f"ОШИБКА: Столбец '{key_column}' не найден в заголовке файла. Доступные столбцы: {header}")
            sys.exit(1)
        
        # Читаем строки и удаляем дубликаты
        rows = []
        seen_keys = set()
        duplicates = []
        
        for row in reader:
            if len(row) <= key_index:
                print(f"Предупреждение: строка с недостаточным количеством столбцов пропущена: {row}")
                continue
                
            key = row[key_index]
            if key in seen_keys:
                duplicates.append(key)
                continue
            seen_keys.add(key)
            rows.append(row)
        
        # Выводим информацию о дубликатах
        duplicate_count = len(duplicates)
        if duplicate_count > 0:
            print(f"Удалено {duplicate_count} дубликатов по ключу '{key_column}'")
            if duplicate_count < 10:
                print(f"Дублирующиеся ключи: {', '.join(duplicates)}")
            else:
                print(f"Первые 10 дублирующихся ключей: {', '.join(duplicates[:10])}...")
    
    # Запись обработанного файла
    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(header)
        writer.writerows(rows)
    
    print(f"Сохранено {len(rows)} уникальных строк в {output_file}")
    return len(rows)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Использование: python process_csv.py <входной_файл> <выходной_файл> <ключевой_столбец>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    key_column = sys.argv[3]
    
    process_csv(input_file, output_file, key_column)
EOL

# Делаем скрипт исполняемым
chmod +x process_csv.py

# Обрабатываем файлы CSV с использованием Python-скрипта
echo "Обработка CSV-файлов для удаления дубликатов..."

echo "1. Анализ файла cards_structure.csv..."
# Сначала определим заголовок файла
header=$(head -1 db_export/cards_structure.csv)
echo "Заголовок: $header"

# Обрабатываем файлы
echo "2. Обработка cards_structure.csv..."
python3 process_csv.py db_export/cards_structure.csv db_export/cards_structure_clean.csv "card_id"

echo "3. Обработка cards_metrics.csv..."
python3 process_csv.py db_export/cards_metrics.csv db_export/cards_metrics_clean.csv "card_id"

echo "4. Обработка card_status.csv..."
python3 process_csv.py db_export/card_status.csv db_export/card_status_clean.csv "card_id"

# Пересоздаем таблицы
echo "5. Полное пересоздание таблиц..."
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

# Импорт данных с обработкой ошибок
echo "6. Импорт обработанных данных в базу данных..."

echo "Импорт cards_structure..."
if ! psql -d course_quality -c "\COPY cards_structure FROM 'db_export/cards_structure_clean.csv' WITH CSV HEADER"; then
    echo "ОШИБКА при импорте cards_structure!"
    exit 1
fi

echo "Импорт cards_metrics..."
if ! psql -d course_quality -c "\COPY cards_metrics FROM 'db_export/cards_metrics_clean.csv' WITH CSV HEADER"; then
    echo "ОШИБКА при импорте cards_metrics!"
    exit 1
fi

echo "Импорт card_status..."
if ! psql -d course_quality -c "\COPY card_status FROM 'db_export/card_status_clean.csv' WITH CSV HEADER"; then
    echo "ОШИБКА при импорте card_status!"
    exit 1
fi

# Проверка результатов импорта
echo "7. Проверка результатов импорта..."
cards_structure_count=$(psql -d course_quality -t -c "SELECT COUNT(*) FROM cards_structure;")
cards_metrics_count=$(psql -d course_quality -t -c "SELECT COUNT(*) FROM cards_metrics;")
card_status_count=$(psql -d course_quality -t -c "SELECT COUNT(*) FROM card_status;")

echo "Количество записей в cards_structure: $cards_structure_count"
echo "Количество записей в cards_metrics: $cards_metrics_count"
echo "Количество записей в card_status: $card_status_count"

# Добавляем переменную окружения в файлы запуска
echo "8. Настройка переменной окружения..."

# В start.sh
if [ -f "start.sh" ]; then
    if ! grep -q "export DB_DSN=" "start.sh"; then
        sed -i '1s/^/export DB_DSN="postgresql:\/\/\/course_quality"\n/' "start.sh"
    fi
    chmod +x start.sh
    echo "Переменная окружения добавлена в start.sh"
fi

# Создание файла .env
echo 'DB_DSN="postgresql:///course_quality"' > .env
echo "Создан файл .env с переменной окружения"

# Добавление переменной в streamlit/.config
mkdir -p ~/.streamlit
echo '[general]' > ~/.streamlit/config.toml
echo 'DB_DSN = "postgresql:///course_quality"' >> ~/.streamlit/config.toml
echo "Настроен файл конфигурации Streamlit"

echo "-----------------------------------------------------"
echo "  Импорт данных завершен успешно!"
echo "-----------------------------------------------------"
echo "Для запуска приложения выполните:"
echo "export DB_DSN=\"postgresql:///course_quality\""
echo "cd ~/app && ./start.sh"
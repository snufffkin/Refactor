import pandas as pd
from sqlalchemy import create_engine, text

DB_PATH = "postgresql:///course_quality"
XLSX    = "informatics_structure.xlsx"   # имя новой выгрузки с теоретическими карточками

engine = create_engine(DB_PATH, future=True)

# --- 1. STRUCTURE -----------------------------------------------------------
# Читаем первый (и единственный) лист с новой структурой
structure = pd.read_excel(XLSX, sheet_name=0)
# Оставляем только нужные колонки (игнорируем лишний card_order)
structure = structure[[
    'program','module','module_order','lesson','lesson_order',
    'gz','gz_id','card_id','card_type','card_url'
]]
# Создаю таблицу структуры, если не существует, и очищаю её без удаления зависимостей
with engine.begin() as conn:
    conn.exec_driver_sql("""
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
    """
    )
    conn.exec_driver_sql("TRUNCATE TABLE cards_structure;")
# Вставляю новые данные
structure.to_sql("cards_structure", engine, if_exists="append", index=False)

# --- 2. METRICS (не изменяем) --------------------------------------------------
# Метрики остаются в таблице cards_metrics без перезаписи, новые карточки получат NULL

# --- 3. STATUS (пустая таблица) --------------------------------------------
with engine.begin() as conn:
    conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS card_status(
            card_id     INTEGER PRIMARY KEY,
            status      TEXT DEFAULT 'new',
            updated_by  TEXT,
            updated_at  TEXT
        );
    """)

# --- 4. VIEW ---------------------------------------------------------------
with engine.begin() as conn:
    conn.exec_driver_sql("DROP VIEW IF EXISTS cards_mv;" )
    conn.exec_driver_sql("""
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
    """)

print("✓ PostgreSQL database course_quality настроена и содержит view cards_mv")

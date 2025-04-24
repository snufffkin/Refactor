import pandas as pd
from sqlalchemy import create_engine, text

DB_PATH = "postgresql:///course_quality"
XLSX    = "course_metrics.xlsx"          # <‑‑  имя вашего файла

engine = create_engine(DB_PATH, future=True)

# --- 1. STRUCTURE -----------------------------------------------------------
structure = (
    pd.read_excel(XLSX, sheet_name="cards_mv")  # лист 1
      .rename(columns={
          "Программа":"program", "Модуль":"module",
          "Порядок модуля в программе":"module_order",
          "Урок":"lesson", "Порядок урока в модуле":"lesson_order",
          "ГЗ":"gz", "ID ГЗ":"gz_id", "ID карточки":"card_id",
          "Тип карточки":"card_type", "Ссылка на карточку":"card_url"
      })
)
structure.to_sql("cards_structure", engine, if_exists="replace", index=False)

# --- 2. METRICS -------------------------------------------------------------
metrics = (
    pd.read_excel(XLSX, sheet_name="card_status")   # лист 2
      .rename(columns={
          "ID карточки":"card_id",
          "Всего попытавшихся":"total_attempts",
          "Доля попытавшихся":"attempted_share",
          "Доля успешно решивших от попытавшихся":"success_rate",
          "Доля успешных с первой попытки":"first_try_success_rate",
          "Доля жалоб":"complaint_rate",
          "Общее количество жалоб":"complaints_total",
          "Средняя дискриминативность":"discrimination_avg",
          "Доля успешных попыток":"success_attempts_rate",
      })
)
metrics.to_sql("cards_metrics", engine, if_exists="replace", index=False)

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
        JOIN cards_metrics m USING(card_id)
        LEFT JOIN card_status st USING(card_id);
    """)

print("✓ PostgreSQL database course_quality настроена и содержит view cards_mv")

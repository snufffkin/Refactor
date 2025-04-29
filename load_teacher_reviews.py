import pandas as pd
from sqlalchemy import create_engine

DB_PATH = "postgresql:///course_quality"
XLSX = "GZ_stat.xlsx"

engine = create_engine(DB_PATH, future=True)

# --- Загрузка отзывов учителей ------------------------------------------------
df = pd.read_excel(XLSX, sheet_name=0)

# Создание таблицы teacher_reviews, если не существует, и очистка
with engine.begin() as conn:
    conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS teacher_reviews(
            program TEXT,
            module TEXT,
            lesson TEXT,
            presentation_rate FLOAT,
            presentation_like TEXT,
            presentation_dislike TEXT,
            workbook_rate FLOAT,
            workbook_like TEXT,
            workbook_dislike TEXT,
            addmaterial_stat FLOAT,
            addmaterial_rate FLOAT,
            addmaterial_like TEXT,
            addmaterial_dislike TEXT,
            overall_stat FLOAT,
            interest_stat FLOAT,
            interest_dislike TEXT,
            interest_like TEXT,
            complexity_stat FLOAT,
            complexity_to_simplify TEXT,
            complexity_to_complicate TEXT
        );
    """)
    conn.exec_driver_sql("TRUNCATE TABLE teacher_reviews;")

# Вставка данных
df.to_sql("teacher_reviews", engine, if_exists="append", index=False)

print("✓ Данные отзывов учителей из GZ_stat.xlsx загружены в PostgreSQL (таблица teacher_reviews)") 
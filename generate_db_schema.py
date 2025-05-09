import core
from sqlalchemy import text, inspect
from typing import List, Dict, Any
import json

def get_table_info(conn, table_name: str) -> Dict[str, Any]:
    """Получает информацию о структуре таблицы."""
    # Получаем информацию о колонках
    columns = conn.execute(text(f"""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = :table_name
        ORDER BY ordinal_position
    """), {"table_name": table_name}).fetchall()
    
    # Получаем информацию об индексах
    indexes = conn.execute(text(f"""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = :table_name
    """), {"table_name": table_name}).fetchall()
    
    # Получаем информацию о внешних ключах
    foreign_keys = conn.execute(text(f"""
        SELECT
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.table_name = :table_name
        AND tc.constraint_type = 'FOREIGN KEY'
    """), {"table_name": table_name}).fetchall()

    return {
        "columns": columns,
        "indexes": indexes,
        "foreign_keys": foreign_keys
    }

def get_view_definition(conn, view_name: str) -> str:
    """Получает SQL-определение представления."""
    result = conn.execute(text("""
        SELECT pg_get_viewdef(:view_name, true)
    """), {"view_name": view_name}).scalar()
    return result

def format_table_columns(info: Dict[str, Any]) -> str:
    """Форматирует информацию о колонках таблицы."""
    if not info["columns"]:
        return "No columns found"
        
    # Вычисляем максимальные длины для каждой колонки
    max_lengths = {
        "name": max(len(col[0]) for col in info["columns"]),
        "type": max(len(col[1]) for col in info["columns"]),
        "nullable": 9,  # длина слова "Nullable"
        "default": max(len(str(col[3] or '')) for col in info["columns"])
    }
    
    # Создаем заголовок таблицы
    header = f"{'Column'.ljust(max_lengths['name'])} | {'Type'.ljust(max_lengths['type'])} | {'Nullable'.ljust(max_lengths['nullable'])} | {'Default'.ljust(max_lengths['default'])}"
    separator = f"{'-' * max_lengths['name']}-+-{'-' * max_lengths['type']}-+-{'-' * max_lengths['nullable']}-+-{'-' * max_lengths['default']}"
    
    result = header + "\n" + separator + "\n"
    
    # Добавляем строки с данными
    for col in info["columns"]:
        name = col[0].ljust(max_lengths['name'])
        type_ = col[1].ljust(max_lengths['type'])
        nullable = ('YES' if col[2] == 'YES' else 'NO').ljust(max_lengths['nullable'])
        default = (str(col[3] or '')).ljust(max_lengths['default'])
        result += f"{name} | {type_} | {nullable} | {default}\n"
    
    return result

def generate_markdown() -> str:
    """Генерирует markdown документацию схемы базы данных."""
    engine = core.get_engine()
    
    markdown = "# Структура базы данных course_quality\n\n"

    with engine.connect() as conn:
        # Получаем список всех таблиц
        tables = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)).fetchall()
        
        # Получаем список всех представлений
        views = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'VIEW'
            ORDER BY table_name
        """)).fetchall()
        
        # Получаем список материализованных представлений
        mat_views = conn.execute(text("""
            SELECT matviewname 
            FROM pg_matviews 
            WHERE schemaname = 'public'
            ORDER BY matviewname
        """)).fetchall()

        # Генерируем документацию для таблиц
        if tables:
            markdown += "## Таблицы\n\n"
            for table in tables:
                table_name = table[0]
                markdown += f"### Таблица: {table_name}\n\n```sql\n"
                
                info = get_table_info(conn, table_name)
                
                # Форматируем информацию о колонках
                markdown += format_table_columns(info)
                
                # Добавляем информацию об индексах
                if info["indexes"]:
                    markdown += "\nIndexes:\n"
                    for idx in info["indexes"]:
                        markdown += f"    \"{idx[0]}\" {idx[1].split(' ', 1)[1]}\n"
                
                # Добавляем информацию о внешних ключах
                if info["foreign_keys"]:
                    markdown += "\nForeign-key constraints:\n"
                    for fk in info["foreign_keys"]:
                        markdown += f"    \"{fk[0]}\" FOREIGN KEY ({fk[1]}) REFERENCES {fk[2]}({fk[3]})\n"
                
                markdown += "```\n\n"

        # Генерируем документацию для представлений
        if views:
            markdown += "## Представления (Views)\n\n"
            for view in views:
                view_name = view[0]
                markdown += f"### Представление: {view_name}\n\n"
                view_def = get_view_definition(conn, view_name)
                if view_def:
                    markdown += f"```sql\n{view_def}\n```\n\n"

        # Генерируем документацию для материализованных представлений
        if mat_views:
            markdown += "## Материализованные представления\n\n"
            for mview in mat_views:
                mview_name = mview[0]
                markdown += f"### Материализованное представление: {mview_name}\n\n"
                
                # Получаем структуру материализованного представления
                info = get_table_info(conn, mview_name)
                
                # Форматируем информацию о колонках
                markdown += "```sql\n" + format_table_columns(info)
                
                # Добавляем информацию об индексах
                if info["indexes"]:
                    markdown += "\nIndexes:\n"
                    for idx in info["indexes"]:
                        markdown += f"    \"{idx[0]}\" {idx[1].split(' ', 1)[1]}\n"
                
                markdown += "```\n\n"
                
                # Добавляем SQL определение
                view_def = get_view_definition(conn, mview_name)
                if view_def:
                    markdown += "#### SQL определение:\n\n```sql\n"
                    markdown += view_def + "\n```\n\n"

    return markdown

def main():
    """Основная функция для генерации и сохранения схемы базы данных."""
    try:
        markdown = generate_markdown()
        with open('db_schema.md', 'w', encoding='utf-8') as f:
            f.write(markdown)
        print("Схема базы данных успешно сгенерирована и сохранена в db_schema.md")
    except Exception as e:
        print(f"Ошибка при генерации схемы базы данных: {e}")

if __name__ == "__main__":
    main() 
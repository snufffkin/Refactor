import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

# Параметры подключения к базе данных
DB_PATH = "postgresql:///course_quality"
XLSX_PATH = "problem_stat_all_with_feedback.xlsx"

def load_time_and_complaints():
    print(f"Загружаем данные из файла {XLSX_PATH}...")
    
    # Создаем подключение к БД
    engine = create_engine(DB_PATH, future=True)
    
    # Загружаем данные из Excel
    try:
        # Пробуем явно указать engine для Excel
        df = pd.read_excel(XLSX_PATH, engine='openpyxl')
        print(f"Загружено {len(df)} строк из Excel файла")
        
        # Выводим информацию о всех столбцах
        print("Столбцы в файле:", df.columns.tolist())
        
        # Проверяем наличие необходимых столбцов
        required_cols = ['card_id', 'time_median', 'complaints_text']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"Ошибка: В файле отсутствуют следующие колонки: {', '.join(missing_cols)}")
            return
        
        # Выводим первые несколько строк для отладки
        print("\nПервые 5 строк из файла:")
        print(df.head(5)[['card_id', 'time_median', 'complaints_text']])
        
        # Проверяем, есть ли непустые значения в нужных столбцах
        non_null_time = df['time_median'].notna().sum()
        non_null_complaints = df['complaints_text'].notna().sum()
        print(f"\nНепустые значения: time_median: {non_null_time}, complaints_text: {non_null_complaints}")
        
        # Подготавливаем данные
        update_data = df[['card_id', 'time_median', 'complaints_text']].copy()
        
        # Убираем строки с пустыми card_id
        update_data = update_data.dropna(subset=['card_id'])
        
        # Преобразуем card_id в целое число
        update_data['card_id'] = update_data['card_id'].astype(int)
        
        # Проверяем, существуют ли указанные card_id в таблице cards_metrics
        card_ids = tuple(update_data['card_id'].tolist())
        if not card_ids:
            print("Ошибка: Нет допустимых card_id для обновления")
            return
        
        with engine.begin() as conn:
            # Проверяем, какие card_id существуют в таблице cards_metrics
            query = text(f"""
                SELECT card_id FROM cards_metrics 
                WHERE card_id IN :card_ids
            """)
            
            result = conn.execute(query, {'card_ids': card_ids})
            existing_ids = [row[0] for row in result]
            
            print(f"Найдено {len(existing_ids)} из {len(card_ids)} card_id в таблице cards_metrics")
            
            # Фильтруем только существующие card_id
            update_data = update_data[update_data['card_id'].isin(existing_ids)]
            
            # Если нет данных для обновления, завершаем скрипт
            if update_data.empty:
                print("Нет данных для обновления")
                return
        
        # Выполняем обновление для каждой строки
        updated_count = 0
        
        with engine.begin() as conn:
            for idx, row in update_data.iterrows():
                update_sql = text("""
                    UPDATE cards_metrics 
                    SET time_median = :time_median, 
                        complaints_text = :complaints_text
                    WHERE card_id = :card_id
                """)
                
                # Выполняем запрос
                result = conn.execute(
                    update_sql, 
                    {
                        'card_id': int(row['card_id']), 
                        'time_median': row['time_median'] if pd.notna(row['time_median']) else None,
                        'complaints_text': str(row['complaints_text']) if pd.notna(row['complaints_text']) else None
                    }
                )
                
                # Увеличиваем счетчик обновленных строк
                if result.rowcount > 0:
                    updated_count += 1
        
        print(f"Успешно обновлено {updated_count} записей в таблице cards_metrics")
        
        # Обновляем материализованные представления
        print("Обновляем материализованные представления...")
        with engine.begin() as conn:
            conn.execute(text("REFRESH MATERIALIZED VIEW mv_cards_mv;"))
            conn.execute(text("REFRESH MATERIALIZED VIEW mv_program_stats;"))
            conn.execute(text("REFRESH MATERIALIZED VIEW mv_module_stats;"))
            conn.execute(text("REFRESH MATERIALIZED VIEW mv_lesson_stats;"))
            conn.execute(text("REFRESH MATERIALIZED VIEW mv_gz_stats;"))
            
        print("Данные успешно загружены и представления обновлены!")
        
    except Exception as e:
        print(f"Ошибка при загрузке данных: {str(e)}")

if __name__ == "__main__":
    load_time_and_complaints() 
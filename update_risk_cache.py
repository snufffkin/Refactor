# update_risk_cache.py
import pandas as pd
from sqlalchemy import text, exc
import time

# Предполагается, что core.py и зависимости находятся в той же директории
# или доступны через PYTHONPATH
from core import get_engine, load_card_data, calculate_risk_score
# get_config будет вызван внутри calculate_risk_score

def update_card_risk_cache():
    engine = get_engine()

    print("1. Загрузка всех данных по карточкам...")
    # load_card_data загружает данные, объединяя cards_structure, cards_metrics, 
    # card_status и card_risk_cache. Старое значение риска из crc.risk нам не помешает,
    # так как мы рассчитаем новое.
    try:
        all_cards_df = load_card_data(_engine=engine)
    except Exception as e:
        print(f"Ошибка при загрузке данных карточек: {e}")
        print("Убедитесь, что база данных доступна и структура таблиц корректна.")
        return

    if all_cards_df.empty:
        print("Не найдены данные по карточкам для обработки.")
        return

    print(f"Загружено {len(all_cards_df)} строк с данными карточек.")

    # Колонки, необходимые для calculate_risk_score, как они используются в calculate_X_risk функциях
    # и в самом calculate_risk_score.
    # total_attempts используется для confidence_factor.
    # discrimination_avg, success_rate, complaints_total, attempted_share - для соответствующих risk_X компонентов.
    # first_try_success_rate используется в calculate_trickiness_level -> calculate_trickiness_risk
    
    required_metrics_cols = [
        'total_attempts', 'attempted_share', 'success_rate', 
        'first_try_success_rate', 'complaint_rate', 'complaints_total', 
        'discrimination_avg'
    ]
    
    # Проверим наличие card_id
    if 'card_id' not in all_cards_df.columns:
        print("Ошибка: колонка 'card_id' отсутствует в загруженных данных.")
        return
    
    # Заполнение NaN значений для метрик
    # Значения для заполнения выбраны так, чтобы при отсутствии данных риск был скорее высоким/нейтральным
    fill_values = {
        'total_attempts': 0,          # Приведет к confidence_factor = 0, риск = NEUTRAL_RISK_VALUE
        'attempted_share': 0.0,       # Низкая доля попыток -> высокий attempted_share_risk
        'success_rate': 0.0,          # Низкая успешность -> высокий success_rate_risk
        'first_try_success_rate': 0.0,# Низкая успешность с первой попытки (для tricky_cards)
        'complaint_rate': 0.0,        # Используется для расчета complaints_total, если он NaN
        'complaints_total': 0,        # Отсутствие жалоб -> низкий complaint_risk
        'discrimination_avg': 0.0     # Низкая дискриминативность -> высокий discrimination_risk
    }

    print("Предварительная обработка данных (заполнение NaN)...")
    for col in required_metrics_cols:
        if col not in all_cards_df.columns:
            print(f"Предупреждение: Ожидаемая колонка метрик '{col}' отсутствует. Будет создана и заполнена значением по умолчанию.")
            all_cards_df[col] = fill_values.get(col) 
        else:
            all_cards_df[col] = all_cards_df[col].fillna(fill_values.get(col))

    # Особый случай для complaints_total, если он рассчитывается из complaint_rate и total_attempts
    # В core.py, calculate_complaint_risk напрямую использует 'complaints_total'.
    # Если 'complaints_total' отсутствует или NaN, он будет заполнен 0 выше.

    print("2. Перерасчет значений риска...")
    # risk_config.json будет неявно прочитан внутри calculate_risk_score через get_config()
    try:
        # Передаем копию DataFrame, чтобы избежать потенциальных проблем с SettingWithCopyWarning
        # и чтобы функция calculate_risk_score не изменяла исходный all_cards_df неожиданным образом.
        all_cards_df['new_risk'] = calculate_risk_score(all_cards_df.copy()) 
    except KeyError as e:
        print(f"Ошибка KeyError при расчете риска: {e}.")
        print("Это может означать, что в risk_config.json отсутствует необходимый ключ или секция (например, 'tricky_cards' или его подсекции).")
        print("Пожалуйста, проверьте ваш risk_config.json на полноту и соответствие ожиданиям функции get_config() и calculate_risk_score().")
        return
    except Exception as e:
        print(f"Непредвиденная ошибка при расчете риска: {e}")
        return

    # Обработка NaN или бесконечных значений в new_risk, если они появились
    all_cards_df['new_risk'] = all_cards_df['new_risk'].replace([float('inf'), -float('inf')], float('nan'))
    # Записи с NaN риском будут удалены перед вставкой в БД
    
    print("3. Подготовка данных для обновления кэша риска...")
    risk_cache_df = all_cards_df[['card_id', 'new_risk']].copy()
    risk_cache_df.rename(columns={'new_risk': 'risk'}, inplace=True)
    
    # Удаляем строки, где card_id is None или risk is None
    risk_cache_df.dropna(subset=['card_id', 'risk'], inplace=True)
    
    if risk_cache_df.empty:
        print("Нет данных для обновления в кэше риска после расчета и фильтрации.")
        return
        
    risk_cache_df['card_id'] = risk_cache_df['card_id'].astype(int)
    # Убираем дубликаты по card_id, если они вдруг есть, оставляя первое значение
    risk_cache_df.drop_duplicates(subset=['card_id'], keep='first', inplace=True)


    print(f"Будет обновлено/вставлено {len(risk_cache_df)} записей в card_risk_cache.")

    print("4. Обновление таблицы card_risk_cache...")
    
    retries = 3
    for i in range(retries):
        try:
            with engine.begin() as connection:
                # Для PostgreSQL:
                # Используем более случайное имя для временной таблицы, чтобы избежать коллизий при параллельном запуске (хотя это маловероятно для скрипта)
                timestamp_micros = int(time.time() * 1_000_000)
                temp_table_name = f"temp_risk_update_{timestamp_micros}" 
                
                # Записываем DataFrame во временную таблицу
                risk_cache_df.to_sql(temp_table_name, connection, if_exists='replace', index=False, chunksize=1000)
                print(f"Данные ({len(risk_cache_df)} строк) записаны во временную таблицу {temp_table_name}.")

                # SQL для UPSERT из временной таблицы в card_risk_cache
                # Предполагаем, что в card_risk_cache есть поле updated_at
                upsert_sql = text(f"""
                    INSERT INTO card_risk_cache (card_id, risk, updated_at)
                    SELECT card_id, risk, NOW() FROM {temp_table_name}
                    ON CONFLICT (card_id) DO UPDATE SET
                        risk = EXCLUDED.risk,
                        updated_at = NOW();
                """)
                connection.execute(upsert_sql)
                print("Операция UPSERT для card_risk_cache выполнена.")
                
                # Удаляем временную таблицу
                connection.execute(text(f"DROP TABLE {temp_table_name}"))
                print(f"Временная таблица {temp_table_name} удалена.")
            
            print("Таблица card_risk_cache успешно обновлена.")
            break # Успех, выходим из цикла попыток
        except exc.OperationalError as e:
            print(f"Ошибка OperationalError при обновлении БД (попытка {i+1}/{retries}): {e}")
            if "lock" in str(e).lower() or "deadlock" in str(e).lower() or "timeout" in str(e).lower():
                print(f"Обнаружена блокировка/таймаут, ожидание 5 секунд перед повторной попыткой...")
                time.sleep(5) 
                if i == retries - 1:
                    print("Не удалось обновить БД после нескольких попыток из-за проблем с блокировками/таймаутами.")
                    return
            else:
                print("Произошла OperationalError, не связанная с блокировкой/таймаутом.")
                raise 
        except Exception as e:
            print(f"Ошибка при обновлении таблицы card_risk_cache (попытка {i+1}/{retries}): {e}")
            # Для других ошибок не повторяем сразу, если это не OperationalError, связанная с блокировкой
            return 

    print("Перерасчет и обновление кэша риска завершено.")

if __name__ == "__main__":
    # Этот скрипт предназначен для запуска из командной строки.
    # Убедитесь, что все зависимости (pandas, sqlalchemy, psycopg2-binary или другой драйвер БД) установлены.
    # Также убедитесь, что файлы core.py, core_config.py, db_config.py, risk_config.json 
    # находятся в правильном месте для импорта и использования.
    update_card_risk_cache() 
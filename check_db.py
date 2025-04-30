import core
import pandas as pd
from sqlalchemy import text

# Получаем engine
engine = core.get_engine()

# Проверяем таблицы в базе данных
print("Структура таблиц в базе данных:")
with engine.connect() as conn:
    tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
    for table in tables:
        print(f"- {table[0]}")

# Проверяем содержимое таблицы card_status
print("\nСодержимое таблицы card_status:")
with engine.connect() as conn:
    try:
        result = conn.execute(text("SELECT * FROM card_status LIMIT 10"))
        if result.rowcount == 0:
            print("Таблица card_status пуста")
        else:
            for row in result:
                print(row)
    except Exception as e:
        print(f"Ошибка при запросе к таблице card_status: {e}")

# Проверяем содержимое таблицы card_assignments
print("\nСодержимое таблицы card_assignments:")
with engine.connect() as conn:
    try:
        result = conn.execute(text("SELECT * FROM card_assignments LIMIT 10"))
        if result.rowcount == 0:
            print("Таблица card_assignments пуста")
        else:
            for row in result:
                print(row)
    except Exception as e:
        print(f"Ошибка при запросе к таблице card_assignments: {e}")

# Проверяем view cards_mv
print("\nПроверка представления cards_mv (статусы карточек):")
with engine.connect() as conn:
    try:
        result = conn.execute(text("SELECT card_id, status, updated_at FROM cards_mv WHERE status != 'new' LIMIT 10"))
        if result.rowcount == 0:
            print("Нет карточек с измененным статусом")
        else:
            for row in result:
                print(row)
    except Exception as e:
        print(f"Ошибка при запросе к представлению cards_mv: {e}")

# Проверяем связь между статусом карточки и карточкой в системе назначений
print("\nПроверка связи статусов и назначений:")
with engine.connect() as conn:
    try:
        # Получаем карточки с не 'new' статусом из card_status
        status_cards = conn.execute(text("SELECT card_id, status FROM card_status WHERE status != 'new'")).fetchall()
        print(f"Карточек с изменённым статусом в card_status: {len(status_cards)}")
        
        # Проверяем, есть ли эти карточки в card_assignments
        if status_cards:
            for card in status_cards:
                card_id = card[0]
                status = card[1]
                assignment = conn.execute(text("SELECT * FROM card_assignments WHERE card_id = :card_id"), 
                                          {"card_id": card_id}).fetchone()
                if assignment:
                    print(f"Карточка {card_id} с статусом '{status}' имеет назначение: {assignment}")
                else:
                    print(f"Карточка {card_id} с статусом '{status}' НЕ имеет назначения в системе")
                    
            # Предложение решения
            print("\nРешение проблемы:")
            print("1. Добавим запись в card_assignments для карточки со статусом")
            user_id = conn.execute(text("SELECT user_id FROM users LIMIT 1")).fetchone()
            if user_id:
                user_id = user_id[0]
                for card in status_cards:
                    card_id = card[0]
                    assignment = conn.execute(text("SELECT * FROM card_assignments WHERE card_id = :card_id"), 
                                          {"card_id": card_id}).fetchone()
                    if not assignment:
                        print(f"Для создания назначения для карточки {card_id} пользователю {user_id}, выполните:")
                        print(f"INSERT INTO card_assignments (card_id, user_id, status) VALUES ({card_id}, {user_id}, '{card[1]}');")
            
    except Exception as e:
        print(f"Ошибка при проверке связи статусов и назначений: {e}") 
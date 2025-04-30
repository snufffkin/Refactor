import core
from sqlalchemy import text

# Получаем engine
engine = core.get_engine()

# Синхронизация card_status с card_assignments
print("Синхронизация статусов карточек с назначениями...")

with engine.begin() as conn:
    # Получаем все карточки с измененным статусом
    cards_with_status = conn.execute(text(
        "SELECT card_id, status FROM card_status WHERE status != 'new'"
    )).fetchall()
    
    print(f"Найдено {len(cards_with_status)} карточек с измененным статусом")
    
    # Для каждой карточки с статусом
    for card in cards_with_status:
        card_id = card[0]
        status = card[1]
        
        # Проверяем, есть ли уже назначение для этой карточки
        assignment = conn.execute(text(
            "SELECT assignment_id FROM card_assignments WHERE card_id = :card_id"
        ), {"card_id": card_id}).fetchone()
        
        # Если назначения нет, то создаем его
        if not assignment:
            # Получаем первого пользователя (обычно админ/демо)
            user = conn.execute(text(
                "SELECT user_id FROM users ORDER BY user_id LIMIT 1"
            )).fetchone()
            
            if user:
                user_id = user[0]
                
                # Создаем назначение
                conn.execute(text("""
                    INSERT INTO card_assignments (card_id, user_id, status) 
                    VALUES (:card_id, :user_id, :status)
                """), {
                    "card_id": card_id,
                    "user_id": user_id,
                    "status": status
                })
                
                # Создаем запись в истории
                conn.execute(text("""
                    INSERT INTO assignment_history (assignment_id, old_status, new_status, changed_by)
                    VALUES ((SELECT assignment_id FROM card_assignments WHERE card_id = :card_id), NULL, :status, :user_id)
                """), {
                    "card_id": card_id,
                    "status": status,
                    "user_id": user_id
                })
                
                print(f"Создано назначение для карточки {card_id} со статусом '{status}' пользователю {user_id}")
            else:
                print(f"Ошибка: не найдено ни одного пользователя в системе")
        else:
            print(f"Карточка {card_id} уже имеет назначение")

print("Синхронизация завершена!")

# Проверяем результат
with engine.connect() as conn:
    assignments = conn.execute(text("SELECT * FROM card_assignments")).fetchall()
    print(f"\nПосле синхронизации: {len(assignments)} назначений в системе") 
import openai
import pandas as pd
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import json
from db_config import get_cloud_dsn

# Загрузка переменных окружения (например, API ключа)
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Предполагается, что db_config.py и функция get_cloud_dsn() существуют
# from db_config import get_cloud_dsn 


PROMPT_TEMPLATE = """
Ты ведущий аналитик по адаптивным образовательным траекториям, эксперт по выявлению когнитивных ловушек в учебных заданиях, обладатель награды «Цифровой Учитель года».
Перед тобой данные по онлайн-уроку на одну из тем по школьной информатике в формате списка JSON объектов. Каждая карточка в списке описана следующими полями:
- card_order: порядковый номер карточки в уроке
- card_id: уникальный идентификатор карточки  
- screenshot_url: ссылка на скриншот карточки
- card_type: тип карточки
- success_rate: успешность прохождения карточки (от 0 до 1)
- time_median: медианное время выполнения в секундах
- text_blocks: содержание скрытых блоков/спойлеров
- interactives: описание интерактивной механики задания
- complaints_total: общее количество жалоб на карточку
- complaints_text: тексты жалоб пользователей
ОБНАРУЖЕНИЕ ПРОСЕДАЮЩИХ КАРТОЧЕК
Из данных JSON возьми следующие поля:
- success_rate (успешность)
- time_median (время в секундах)
Проанализируй динамику успешности и времени (только по карточкам типа practice!). Для успешности смотри за тем, как себя показывает карточка относительно бенчмарка (0,85) и относительно остальных карточек. Для времени сопоставляй только с остальными карточками.
Пометь карточки, которые особенно сильно выделяются по этим параметрам (имеют успешность ниже бенчмарка и/или время выше медианного по уроку), как "проседающие карточки".
АНАЛИЗ СОДЕРЖАНИЯ
По данным JSON ты можешь с помощью ID сопоставить порядковый номер карточки и ее скриншот (поле screenshot_url).
Содержание скрытых блоков/спойлеров можно найти в поле text_blocks.
Дополнительную информацию по заданию может дать поле interactives, вот описание механик в нем. Список механик:
- inline: В задании один или несколько блоков для ответа. Блок может заполняться одним из двух способов: ввод текста с клавиатуры (в этом случае называй механику "ввод ответа") или выбор из предложенных вариантов (в этом случае называй механику "выпадающий список").
- choice: В задании нужно выбрать один или несколько вариантов ответа из списка (в случае одного верного варианта называй механику "радиобаттон", а в случае нескольких - "чекбоксы"). Варианты ответа могут быть представлены текстом или картинками.
- dragimage: В задании нужно перетаскиванием верно разместить блоки с текстом или картинками на соответствующих пустых полях. Называй механику "перетаск"
- chooseimage: В задании нужно выбрать область на картинке, соответствующую заданным требованиям. Называй механику "выбор области"
- macaroni: В задании нужно соединить линиями элементы одного списка с элементами другого списка в соответствии с задачей. Элементы могут быть текстом или картинками. Называй механику "соединение списков"
- polylines: Механика, похожая на makaroni, но в ней можно соединять линиями любые элементы на изображении. Называй механику "соединение точек"
- diskurl: Поле, в которое необходимо вставить ссылку на созданный в ходе выполнения проектной работы документ, лежащий на Яндекс Диске. Называй механику "ссылка на диск"
- coloring: Механика раскраски, в которой нужно определенные поля заполнить определенными цветами. Называй механику "раскраска"
Собери всю доступную информацию о содержании карточек, обрати внимание на то, какая именно информация ученикам дается, в каком объеме и в какой последовательности.
АНАЛИЗ ПРИЧИН ПРОСЕДАНИЯ
На основе анализа содержания и жалоб (поля complaints_total и complaints_text) сделай выводы о том, почему проседающие карточки показывают такие результаты в статистике.
ФОРМАТ ВЫВОДА
Оформи результат так, чтобы можно было его скопировать вместе с разметкой в markdown. До и после блока markdown не добавляй никакого текста, в ответе должен быть только этот блок.
Если "проседающих карточек" нет, выдай результат "Все карточки имеют значения, соответствующие норме". Если "проседающих карточек" одна или более, выпиши по порядку (от меньшего значения порядкового номера (card_order) к большему) только их (карточки с нормальными значениями и теоретические карточки пропускай). Для каждой выведенной карточки укажи следующее:
- порядковый номер
- ID карточки
- ссылка на скриншот (screenshot_url)
- характеристика данных успешности и времени, на основе которых карточка была отнесена к проседающим. 
- объяснение причин, по которым карточка проседает. При описании задания используй названия механик, которые предложены в списке механик.
- рекомендации об изменениях, которые можно внести, чтобы карточка показывала лучший результат (это могут быть изменения в саму карточку, добавление дополнительных карточек или перемещение карточек по уроку для лучшего восприятия информации)
Всю информацию по карточкам сообщи максимально кратко и емко, в соответствии с примером:
### Карточка №9 (ID: 256046, [скриншот])
#### Статистика:
- Успешность: **0.51 (очень низко)**
- Медиана времени: **100 сек (одно из самых высоких значений)**
#### Задание:
**Перетаск:** нужно перетащить правильные значения разрешений и соотношения сторон к разным мониторам. Теории нет, только небольшая справка по характеристикам под спойлером.
#### Причины проседания:
1. По жалобам: для некоторых задание выглядит нерешаемым, а варианты ответа - неподходящими. 
2. Также есть жалобы на технические проблемы (маленький экран, неудобно перетаскивать, нельзя убрать неправильный вариант)
3. Нет пояснений или пояснения недостаточно точны
4. Интерфейс слишком сложен для восприятия
#### Рекомендации:
1. Убедиться, что в задании нет технически ошибок и оно решается
2. Упростить интерфейс: возможно, убрать часть заполняемых полей, или сделать их больше
3. Добавить теорию по соотношению сторон или убрать эту характеристику из задания, оставив только длину и ширину экрана
4. Разбить карточку на две: в одной разобрать разрешение и сделать задание на него, во второй разобрать соотношение сторон и сделать задание на него
5. Добавить инструкции по интерфейсу механики
Данные по карточкам:
{cards_data_json}
"""

# Версия промпта для записи в БД
PROMPT_VERSION = "1.2_gz_focused_user_template"

def get_db_engine():
    """Создает и возвращает SQLAlchemy engine."""
    try:
        db_url = get_cloud_dsn()
        if not db_url:
            raise ValueError("DSN для подключения к БД не найден.")
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        print(f"Ошибка при создании подключения к БД: {e}")
        return None

def get_programs_for_refactor(engine):
    """Получает список program_id для программ с program_refactor_status = TRUE."""
    query = text("SELECT program_id FROM program_ids WHERE program_refactor_status = TRUE;")
    try:
        with engine.connect() as connection:
            result = connection.execute(query)
            program_ids = [row[0] for row in result]
            return program_ids
    except Exception as e:
        print(f"Ошибка при получении списка программ для рефакторинга: {e}")
        return []

def get_gz_ids_for_programs(engine, program_ids_list):
    """Получает все gz_id для указанных program_id."""
    if not program_ids_list:
        return []
    
    # Мы должны пройти по иерархии: program -> module -> lesson -> gz
    # Используем cards_structure, так как она связывает все эти сущности
    query = text(f"""
        SELECT DISTINCT cs.gz_id
        FROM cards_structure cs
        WHERE cs.program_id IN ({','.join(map(str, program_ids_list))}) AND cs.gz_id IS NOT NULL;
    """)
    # Альтернативный вариант, если связи через lesson_ids и gz_ids более прямые для ГЗ
    # query = text(f"""
    #     SELECT DISTINCT g.gz_id
    #     FROM program_ids p
    #     JOIN module_ids m ON p.program_id = m.program_id
    #     JOIN lesson_ids l ON m.module_id = l.module_id AND p.program_id = l.program_id
    #     JOIN gz_ids g ON l.lesson_id = ANY(g.lesson_ids) -- Эта связь может быть сложной, если lesson_ids это массив
    #     WHERE p.program_id IN ({','.join(map(str, program_ids_list))});
    # """)
    # Более надежный вариант через cards_structure, если она полная
    
    try:
        with engine.connect() as connection:
            result = connection.execute(query)
            gz_ids = [row[0] for row in result]
            return list(set(gz_ids)) # Убираем дубликаты, если есть
    except Exception as e:
        print(f"Ошибка при получении gz_id для программ: {e}")
        return []

def get_cards_data_for_gz(engine, gz_id):
    """Получает данные всех карточек для указанного gz_id."""
    query = text(f"""
        SELECT 
            cs.card_id,
            cs.card_order,
            cs.card_type,
            cm.success_rate,
            cm.time_median,
            cc.text_blocks,
            cc.interactives,
            cm.complaints_total,
            cm.complaints_text -- Это поле из cards_metrics, нужно убедиться, что оно содержит то, что нужно
                               -- Или cc.card_complaints если такое поле есть в cards_content
        FROM cards_structure cs
        LEFT JOIN cards_metrics cm ON cs.card_id = cm.card_id
        LEFT JOIN cards_content cc ON cs.card_id = cc.card_id
        WHERE cs.gz_id = :gz_id
        ORDER BY cs.card_order;
    """)
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"gz_id": gz_id})
            df_cards = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            # Собираем cards_content_data отдельно, т.к. в prepare_cards_data_for_ai он ожидается
            # В данном запросе мы уже джойним нужные поля из cards_content, так что cards_content_data не нужен
            # в том виде, как он был в исходной функции. Мы передадим df_cards.
            
            # Для поля complaints_text используем cm.complaints_text.
            # Если нужно что-то другое, нужно будет скорректировать запрос или логику ниже.
            
            return df_cards
    except Exception as e:
        print(f"Ошибка при получении данных карточек для GZ ID {gz_id}: {e}")
        return pd.DataFrame()


def prepare_cards_data_for_ai(df_cards):
    """Готовит данные карточек в формате списка словарей для передачи в AI."""
    cards_list = []
    if df_cards is None or df_cards.empty:
        return cards_list

    for _, card_row in df_cards.iterrows():
        card_id = int(card_row.get("card_id", 0))
        # text_blocks и interactives уже должны быть в card_row из запроса get_cards_data_for_gz
        # complaints_text также должен быть из запроса

        card_order_val = card_row.get("card_order")
        card_order_int = 0
        if pd.notna(card_order_val):
            try:
                card_order_int = int(card_order_val)
            except ValueError:
                print(f"Warning: Could not convert card_order '{card_order_val}' to int for card_id {card_id}. Using 0.")
        else:
            # Если card_order_val это NaN или None, также используем 0 или другое значение по умолчанию
            print(f"Warning: card_order is NaN or None for card_id {card_id}. Using 0.")

        card_info = {
            "card_order": card_order_int,
            "card_id": card_id,
            "screenshot_url": f"https://snufffkin-pics.website.yandexcloud.net/Refactor/image/{card_id}.png",
            "card_type": card_row.get("card_type", ""),
            "success_rate": card_row.get("success_rate") if pd.notna(card_row.get("success_rate")) else None,
            "time_median": float(card_row.get("time_median")) if pd.notna(card_row.get("time_median")) else None,
            "text_blocks": card_row.get("text_blocks", ""), # Из cc.text_blocks
            "interactives": card_row.get("interactives", ""), # Из cc.interactives
            "complaints_total": int(card_row.get("complaints_total", 0)) if pd.notna(card_row.get("complaints_total")) else 0,
            "complaints_text": card_row.get("complaints_text", "") # Из cm.complaints_text
        }
        cards_list.append(card_info)
    return cards_list

def get_ai_recommendations(cards_data_list, api_key, model="gpt-4o-mini"):
    """Отправляет запрос к OpenAI и получает рекомендации."""
    if not api_key:
        # raise ValueError("API ключ OpenAI не предоставлен.")
        print("API ключ OpenAI не предоставлен. Анализ будет пропущен.")
        return "Ошибка: API ключ OpenAI не предоставлен."
    if not cards_data_list:
        return "Нет данных по карточкам для анализа."

    client = openai.OpenAI(api_key=api_key)

    # Преобразуем список словарей в строку JSON для вставки в промпт
    cards_data_json_str = json.dumps(cards_data_list, indent=2, ensure_ascii=False)

    full_prompt = PROMPT_TEMPLATE.format(cards_data_json=cards_data_json_str)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Ты полезный ассистент, специализирующийся на анализе образовательного контента."},
                {"role": "user", "content": full_prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Ошибка при обращении к API OpenAI: {str(e)}"

def save_gz_recommendation_to_db(gz_id, recommendation_markdown, engine, model_version, prompt_version_str):
    """Сохраняет рекомендацию для ГЗ в таблицу gz_ai_recommendations."""
    if not recommendation_markdown or not engine:
        print(f"Нет рекомендации или подключения к БД для GZ ID {gz_id}. Сохранение пропущено.")
        return

    insert_query = text("""
        INSERT INTO gz_ai_recommendations (gz_id, gz_ai_recommendation, ai_model_version, prompt_version, created_at)
        VALUES (:gz_id, :recommendation, :model, :prompt_v, NOW())
        ON CONFLICT (gz_id) DO UPDATE SET -- Предполагаем, что gz_id должен быть уникальным или мы хотим обновлять
            gz_ai_recommendation = EXCLUDED.gz_ai_recommendation,
            ai_model_version = EXCLUDED.ai_model_version,
            prompt_version = EXCLUDED.prompt_version,
            created_at = NOW();
    """)
    # Если уникального ограничения на gz_id нет или не нужно обновлять, а добавлять новую запись всегда:
    # insert_query = text("""
    #     INSERT INTO gz_ai_recommendations (gz_id, gz_ai_recommendation, ai_model_version, prompt_version, created_at)
    #     VALUES (:gz_id, :recommendation, :model, :prompt_v, NOW());
    # """)
    # Уточните, какой вариант поведения ON CONFLICT предпочтителен.
    # Судя по схеме, analysis_id это PK, а на gz_id есть просто INDEX.
    # Если мы хотим хранить историю анализов для одного ГЗ, то ON CONFLICT не нужен, а если только последнюю - то нужен.
    # В db_schema.md указан FOREIGN KEY (gz_id) REFERENCES gz_ids (gz_id) и INDEX на gz_id. Нет UNIQUE.
    # Значит, для одного gz_id может быть много записей. Убираю ON CONFLICT.
    
    final_insert_query = text("""
        INSERT INTO gz_ai_recommendations (gz_id, gz_ai_recommendation, ai_model_version, prompt_version, created_at)
        VALUES (:gz_id, :recommendation, :model, :prompt_v, NOW());
    """)

    try:
        with engine.connect() as connection:
            connection.execute(final_insert_query, {
                "gz_id": gz_id,
                "recommendation": recommendation_markdown,
                "model": model_version,
                "prompt_v": prompt_version_str
            })
            connection.commit()
            print(f"Рекомендация для GZ ID {gz_id} успешно сохранена.")
    except Exception as e:
        print(f"Ошибка при сохранении рекомендации для GZ ID {gz_id}: {e}")

def analyze_single_gz(gz_id: int, engine, api_key: str, model: str = "gpt-4o-mini") -> str:
    """
    Выполняет AI-анализ для одного указанного gz_id, сохраняет результат в БД 
    и возвращает текст рекомендации или сообщение об ошибке.
    """
    if not gz_id:
        return "Ошибка: GZ ID не указан."
    if not engine:
        return "Ошибка: Подключение к БД не установлено."
    if not api_key:
        return "Ошибка: API ключ OpenAI не предоставлен."

    print(f"--- Запуск анализа для GZ ID: {gz_id} ---")
    df_cards_for_gz = get_cards_data_for_gz(engine, gz_id)

    if df_cards_for_gz.empty:
        msg = f"Нет данных по карточкам для GZ ID {gz_id}. Анализ невозможен."
        print(msg)
        # Не сохраняем это в БД как "анализ", т.к. это состояние данных, а не результат работы ИИ
        return msg
    
    print(f"Для GZ ID {gz_id} найдено {len(df_cards_for_gz)} карточек.")
    
    cards_data_list_for_ai = prepare_cards_data_for_ai(df_cards_for_gz)
    
    if not cards_data_list_for_ai:
        msg = f"Не удалось подготовить данные карточек для AI для GZ ID {gz_id}."
        print(msg)
        return msg

    print(f"Отправка запроса в OpenAI для GZ ID {gz_id} (модель: {model})...")
    ai_response = get_ai_recommendations(cards_data_list_for_ai, api_key, model=model)

    if "Ошибка:" in ai_response:
        print(f"Ошибка от OpenAI для GZ ID {gz_id}: {ai_response}")
        # Можно сохранить информацию об ошибке в БД, если есть такая логика
        # save_gz_recommendation_to_db(gz_id, ai_response, engine, model, PROMPT_VERSION) 
        # Пока не сохраняем ошибки OpenAI как "анализ", чтобы не замусоривать таблицу.
        # Пользователь увидит ошибку и сможет попробовать еще раз.
        return ai_response 
    else:
        print(f"Получен ответ от OpenAI для GZ ID {gz_id}.")
        save_gz_recommendation_to_db(gz_id, ai_response, engine, model, PROMPT_VERSION)
        print(f"--- Завершение анализа GZ ID: {gz_id} ---")
        # Возвращаем "сырой" ответ от OpenAI, чтобы его можно было сразу показать,
        # очистка от ```markdown``` и т.п. произойдет при следующем чтении из БД
        return ai_response

def main_analyze_refactor_programs():
    """Основная функция для анализа ГЗ из программ на рефакторинге."""
    engine = get_db_engine()
    if not engine:
        print("Не удалось подключиться к БД. Выход.")
        return

    if not OPENAI_API_KEY:
        print("API ключ OpenAI не найден в .env. Проверьте файл .env и переменную OPENAI_API_KEY. Выход.")
        return
        
    print(f"Используется ключ OpenAI: {'*' * (len(OPENAI_API_KEY) - 4) + OPENAI_API_KEY[-4:]}")


    programs_to_refactor = get_programs_for_refactor(engine)
    if not programs_to_refactor:
        print("Нет программ, отмеченных для рефакторинга (program_refactor_status = TRUE).")
        return
    print(f"Найдены программы для рефакторинга: {programs_to_refactor}")

    gz_ids_to_analyze = get_gz_ids_for_programs(engine, programs_to_refactor)
    if not gz_ids_to_analyze:
        print(f"Не найдено ГЗ для программ: {programs_to_refactor}.")
        return
    print(f"Найдено {len(gz_ids_to_analyze)} ГЗ для анализа: {gz_ids_to_analyze}")

    # Ограничение для тестирования
    # gz_ids_to_analyze = gz_ids_to_analyze[:2] 
    # print(f"Ограничение для теста: обрабатываем только {gz_ids_to_analyze}")


    current_model = "gpt-4o-mini" # или другая модель

    for gz_id in gz_ids_to_analyze:
        print(f"--- Обработка GZ ID: {gz_id} ---")
        df_cards_for_gz = get_cards_data_for_gz(engine, gz_id)

        if df_cards_for_gz.empty:
            print(f"Нет данных по карточкам для GZ ID {gz_id}. Пропуск.")
            # Можно записать в БД, что данных нет, если это нужно
            # save_gz_recommendation_to_db(gz_id, "Нет данных по карточкам для анализа.", engine, current_model, PROMPT_VERSION)
            continue
        
        print(f"Для GZ ID {gz_id} найдено {len(df_cards_for_gz)} карточек.")
        
        cards_data_list_for_ai = prepare_cards_data_for_ai(df_cards_for_gz)
        
        if not cards_data_list_for_ai:
            print(f"Не удалось подготовить данные карточек для AI для GZ ID {gz_id}. Пропуск.")
            # save_gz_recommendation_to_db(gz_id, "Не удалось подготовить данные карточек для AI.", engine, current_model, PROMPT_VERSION)
            continue

        print(f"Отправка запроса в OpenAI для GZ ID {gz_id}...")
        ai_response = get_ai_recommendations(cards_data_list_for_ai, OPENAI_API_KEY, model=current_model)

        if "Ошибка:" in ai_response:
            print(f"Ошибка от OpenAI для GZ ID {gz_id}: {ai_response}")
            # Можно сохранить информацию об ошибке в БД
            save_gz_recommendation_to_db(gz_id, ai_response, engine, current_model, PROMPT_VERSION)
        else:
            print(f"Получен ответ от OpenAI для GZ ID {gz_id}.")
            # print("---- Ответ OpenAI ----")
            # print(ai_response)
            # print("---- Конец ответа ----")
            save_gz_recommendation_to_db(gz_id, ai_response, engine, current_model, PROMPT_VERSION)
        
        print(f"--- Завершение обработки GZ ID: {gz_id} ---")

if __name__ == "__main__":
    # Создание тестового файла .env для примера, если его нет
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("OPENAI_API_KEY=ваш_ключ_сюда\n") # Напоминание пользователю
            f.write("# DB_DSN=postgresql://user:pass@host:port/db\n")
        print("Создан пример файла .env. Пожалуйста, укажите в нем ваш OPENAI_API_KEY.")

    # Предполагается, что db_config.py и функция get_cloud_dsn() существуют
    # Для локального теста можно создать заглушку db_config.py:
    if not os.path.exists("db_config.py"):
        with open("db_config.py", "w", encoding="utf-8") as f:
            f.write("# -*- coding: utf-8 -*-\n")
            f.write("def get_cloud_dsn():\n")
            f.write("    # Замените на ваш реальный DSN или используйте переменные окружения\n")
            f.write("    # import os\n")
            f.write("    # return os.getenv(\"DB_DSN\")\n")
            f.write("    print(\"Используется заглушка get_cloud_dsn() из analyze_bad_cards.py. Укажите реальный DSN в db_config.py\")\n")
            f.write("    return \"postgresql://testuser:testpass@localhost:5432/testdb\" # Пример\n")
        print("Создан пример файла db_config.py с функцией-заглушкой get_cloud_dsn().")
        print("Пожалуйста, настройте его для подключения к вашей базе данных.")
        
    main_analyze_refactor_programs()

# Функции для сохранения и загрузки в/из БД можно будет добавить сюда позже
# def save_gz_recommendation_to_db(gz_id, recommendation_markdown, engine):
#     pass

# def load_gz_recommendation_from_db(gz_id, engine):
#     pass
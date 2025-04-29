# navigation_data.py
"""
Модуль для создания и обновления JSON-файла с данными навигации
"""

import os
import json
import pandas as pd
import urllib.parse as ul

def create_link(page, **params):
    """
    Создает URL-ссылку с параметрами
    
    Args:
        page: Название страницы
        **params: Дополнительные параметры для URL
    
    Returns:
        str: URL-ссылка с параметрами
    """
    base_url = "?"
    all_params = {"page": page}
    all_params.update(params)
    
    param_strings = []
    for key, value in all_params.items():
        if value is not None:
            param_strings.append(f"{key}={ul.quote_plus(str(value))}")
    
    return base_url + "&".join(param_strings)

def prepare_navigation_json(df, output_path="components/navigation_data.json"):
    """
    Создает и сохраняет полный JSON со структурой навигации
    
    Args:
        df: DataFrame с данными о курсах
        output_path: Путь для сохранения JSON-файла
    
    Returns:
        dict: Структура навигации в виде словаря
    """
    # Создаем основную структуру
    navigation = {
        "main_sections": [
            {"id": "overview", "name": "Обзор", "icon": "📊", "url": create_link("overview")},
            {"id": "admin", "name": "Настройки", "icon": "⚙️", "url": create_link("admin")}
        ],
        "programs": []
    }
    
    # Получаем все уникальные программы
    programs = sorted(df["program"].unique())
    
    # Для каждой программы
    for program_name in programs:
        program_df = df[df["program"] == program_name]
        
        # Создаем структуру программы
        program = {
            "id": program_name,
            "name": program_name,
            "url": create_link("programs", program=program_name),
            "modules": []
        }
        
        # Получаем все модули для программы
        modules = sorted(program_df["module"].unique())
        
        # Для каждого модуля
        for module_name in modules:
            module_df = program_df[program_df["module"] == module_name]
            
            # Создаем структуру модуля
            module = {
                "id": module_name,
                "name": module_name,
                "url": create_link("modules", program=program_name, module=module_name),
                "lessons": []
            }
            
            # Получаем все уроки для модуля
            lessons = sorted(module_df["lesson"].unique())
            
            # Для каждого урока
            for lesson_name in lessons:
                lesson_df = module_df[module_df["lesson"] == lesson_name]
                
                # Создаем структуру урока
                lesson = {
                    "id": lesson_name,
                    "name": lesson_name,
                    "url": create_link("lessons", program=program_name, module=module_name, lesson=lesson_name),
                    "groups": []
                }
                
                # Получаем все группы заданий для урока
                groups = sorted(lesson_df["gz"].unique())
                
                # Для каждой группы заданий
                for group_name in groups:
                    group_df = lesson_df[lesson_df["gz"] == group_name]
                    
                    # Создаем структуру группы заданий
                    group = {
                        "id": group_name,
                        "name": group_name,
                        "url": create_link("gz", program=program_name, module=module_name, lesson=lesson_name, gz=group_name),
                        "cards": []
                    }
                    
                    # Получаем карточки для группы заданий
                    # Сортируем по риску, берем топ-10
                    cards_df = group_df.sort_values("risk", ascending=False).head(10)
                    
                    # Проверяем, есть ли еще карточки
                    has_more_cards = len(group_df) > 10
                    more_cards_count = len(group_df) - 10 if has_more_cards else 0
                    
                    # Для каждой карточки
                    for _, card in cards_df.iterrows():
                        card_id = int(card["card_id"])
                        raw_risk = card["risk"]
                        if pd.isna(raw_risk):
                            risk_json = None
                            risk_str = "N/A"
                        else:
                            risk_json = float(raw_risk)
                            risk_str = f"{risk_json:.2f}"
                        # Создаем структуру карточки
                        card_data = {
                            "id": str(card_id),
                            "name": f"ID: {card_id} - Риск: {risk_str}",
                            "risk": risk_json,
                            "url": create_link("cards", program=program_name, module=module_name, 
                                              lesson=lesson_name, gz=group_name, card_id=card_id)
                        }
                        
                        group["cards"].append(card_data)
                    
                    # Добавляем информацию о дополнительных карточках
                    group["has_more_cards"] = has_more_cards
                    group["more_cards_count"] = more_cards_count
                    
                    # Добавляем группу в урок
                    lesson["groups"].append(group)
                
                # Добавляем урок в модуль
                module["lessons"].append(lesson)
            
            # Добавляем модуль в программу
            program["modules"].append(module)
        
        # Добавляем программу в навигацию
        navigation["programs"].append(program)
    
    # Убеждаемся, что директория существует
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Сохраняем структуру в JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(navigation, f, ensure_ascii=False, indent=2)
    
    return navigation

def get_navigation_data(df=None, force_update=False):
    """
    Получает данные навигации - либо загружает существующий JSON, 
    либо создает новый, если файл не существует или требуется обновление
    
    Args:
        df: DataFrame с данными (опционально, если нужно обновить)
        force_update: Принудительно обновить данные
        
    Returns:
        dict: Структура навигации
    """
    json_path = "components/navigation_data.json"
    
    # Если требуется обновление и есть данные
    if force_update and df is not None:
        return prepare_navigation_json(df, json_path)
    
    # Пробуем загрузить существующий файл
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            # Если не удалось загрузить и есть данные, создаем новый
            if df is not None:
                return prepare_navigation_json(df, json_path)
    else:
        # Если файла нет и есть данные, создаем новый
        if df is not None:
            return prepare_navigation_json(df, json_path)
    
    # Если ничего не сработало, возвращаем пустую структуру
    return {"main_sections": [], "programs": []}
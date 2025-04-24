# update_navigation.py
"""
Скрипт для принудительного обновления файла навигации
Запускается отдельно от Streamlit для обновления данных
"""

import os
import sys
import json

# Добавляем путь к родительской директории для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import get_engine, load_data, risk_score
from navigation_data import prepare_navigation_json

def update_navigation():
    """Обновляет файл навигации с использованием текущих данных"""
    print("Обновление данных навигации...")
    
    # Путь к JSON файлу
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                           "..", "components", "navigation_data.json")
    
    # Создаем директорию, если она не существует
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    
    # Получаем соединение с БД
    engine = get_engine()
    
    # Загружаем данные
    data = load_data(engine)
    # Вычисляем риск для каждой карточки
    data["risk"] = data.apply(risk_score, axis=1)
    
    # Создаем JSON-файл с навигацией
    navigation = prepare_navigation_json(data, json_path)
    
    print(f"Обновление завершено. Файл сохранен: {json_path}")
    print(f"JSON содержит {len(navigation['programs'])} программ")

if __name__ == "__main__":
    update_navigation()
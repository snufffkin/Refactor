# serve_static.py
"""
Модуль для обслуживания статических файлов JSON, CSS, HTML через Streamlit
Позволяет HTML-компонентам получать доступ к файлам навигации
"""

import os
import json
import base64
import streamlit as st
import streamlit.components.v1 as components

def serve_json(path, key=None):
    """
    Сервирует JSON-файл для доступа из HTML-компонента
    
    Args:
        path: Путь к JSON-файлу
        key: Уникальный ключ для компонента (опционально) - не используется в текущей версии
        
    Returns:
        str: URL для доступа к JSON-файлу
    """
    if not os.path.exists(path):
        return None
    
    # Загружаем JSON-файл
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Создаем HTML-компонент, который будет обслуживать JSON
    # Через data URI
    json_str = json.dumps(data)
    json_b64 = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    
    html = f"""
    <div id="json-server" style="display:none;">
        <script>
            // Создаем URL для JSON
            const jsonUrl = "data:application/json;base64,{json_b64}";
            
            // Функция для получения JSON по запросу
            async function getNavigationData() {{
                return fetch(jsonUrl).then(response => response.json());
            }}
            
            // Экспортируем функцию в глобальную область
            window.getNavigationData = getNavigationData;
            
            // Отправляем сообщение родительскому окну
            window.parent.postMessage({{
                type: 'json-server:ready',
                url: jsonUrl
            }}, '*');
        </script>
    </div>
    """
    
    # Рендерим компонент БЕЗ ключа
    components.html(html, height=0)
    
    # Возвращаем URL для доступа к JSON
    return f"data:application/json;base64,{json_b64}"

def create_navigation_html(json_url, height=800):
    """
    Создает HTML-компонент для навигации с указанным URL для JSON
    
    Args:
        json_url: URL для доступа к JSON-файлу
        height: Высота компонента
        
    Returns:
        str: HTML-код компонента навигации
    """
    # Читаем шаблон HTML
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                           "components", "navigation.html")
    
    if not os.path.exists(html_path):
        return f"""
        <div style="padding: 20px; background-color: rgba(255, 77, 77, 0.2); border-radius: 4px;">
            <p style="color: #ff4d4d;">Файл навигации не найден по пути {html_path}</p>
        </div>
        """
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Добавляем URL для JSON
    html_content = html_content.replace(
        '// Загружаем данные навигации из JSON-файла',
        f'''// Загружаем данные навигации из JSON-файла
        // URL для JSON: {json_url}'''
    )
    
    html_content = html_content.replace(
        'const response = await fetch(\'../navigation_data.json\');',
        f'const response = await fetch(\'{json_url}\');'
    )
    
    # Добавляем дополнительные стили для максимального использования пространства
    additional_styles = """
    <style>
        /* Стили для максимального использования пространства */
        body, html {
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
        }
        
        .sidebar-menu {
            width: 100%;
            height: 100%;
            overflow-y: auto;
            padding-bottom: 60px; /* Место для скрытой кнопки обновления */
        }
        
        /* Убираем лишние заголовки, если есть */
        .section-title:first-child {
            margin-top: 0;
            padding-top: 10px;
        }
    </style>
    """
    
    # Вставляем дополнительные стили после открывающего тега <head>
    html_content = html_content.replace('<head>', '<head>' + additional_styles)
    
    return html_content
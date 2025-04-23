# pages/sidebar.py с очищенной структурой
"""
Компоненты боковой панели с иерархической навигацией через HTML/JS
"""

import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from navigation_data import prepare_navigation_json
from serve_static import serve_json, create_navigation_html

def sidebar_filters(df_full: pd.DataFrame, create_link_fn=None):
    """
    Отображает только HTML/JS компонент для навигации в боковой панели
    без каких-либо дополнительных фильтров
    
    Args:
        df_full: DataFrame с данными
        create_link_fn: Функция для создания ссылок с параметрами URL
    """
    # Импортируем components правильно
    import streamlit.components.v1 as components
    
    # Путь к JSON файлу
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                           "components", "navigation_data.json")
    
    # Проверяем, нужно ли обновить данные навигации
    force_update = st.session_state.get("update_navigation", False)
    
    # Если принудительное обновление или файл не существует, создаем его
    if force_update or not os.path.exists(json_path):
        prepare_navigation_json(df_full, json_path)
        st.session_state["update_navigation"] = False
    
    # Сервируем JSON-файл
    json_url = serve_json(json_path)
    
    # Определяем высоту HTML-компонента для отображения
    sidebar_height = 800
    
    # Создаем HTML для навигации с URL к JSON
    html_content = create_navigation_html(json_url, sidebar_height)
    
    # Используем правильный способ для отображения HTML в сайдбаре
    with st.sidebar:
        # Включаем внутренний скролл iframe
        components.html(html_content, height=sidebar_height, scrolling=True)
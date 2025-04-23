# pages/sidebar.py с очищенной структурой
"""
Компоненты боковой панели с иерархической навигацией через HTML/JS
"""

import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64

from navigation_data import prepare_navigation_json
from serve_static import serve_json, create_navigation_html

import streamlit as st
from navigation_component import navigation_menu
from navigation_data import get_navigation_data

def sidebar_filters(df_full, create_link_fn=None):
    """
    Отображает навигационное меню в боковой панели
    
    Args:
        df_full: DataFrame с данными
        create_link_fn: Функция для создания ссылок с параметрами URL
    """
    # Получаем данные для навигации
    navigation_data = get_navigation_data(df_full, create_link_fn)
    
    # Получаем текущую страницу и параметры
    query_params = st.query_params
    current_page = query_params.get("page", "overview")
    
    # Преобразуем параметры в словарь
    current_params = {}
    for key, value in query_params.items():
        current_params[key] = value
    
    # Отображаем компонент в сайдбаре
    with st.sidebar:
        result = navigation_menu(
            navigation_data=navigation_data,
            current_page=current_page,
            current_params=current_params,
            key="navigation_sidebar"
        )
        
        # Обработка результата компонента, если нужно
        if result and "action" in result and result["action"] == "navigate":
            url = result.get("url", "")
            if url:
                # Переход по URL
                from urllib.parse import parse_qs, urlparse
                parsed_url = urlparse(url)
                params = parse_qs(parsed_url.query)
                
                # Преобразуем параметры в формат для st.query_params
                new_params = {}
                for key, value in params.items():
                    new_params[key] = value[0] if value else ""
                
                # Обновляем параметры URL
                st.query_params.update(**new_params)
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
    
    # Очищаем заголовок сайдбара (используем пустой заголовок)
    st.sidebar.markdown("<style>div[data-testid='stSidebarUserContent'] > div:first-child {display: none !important;}</style>", unsafe_allow_html=True)
    
    # Опции CSS для компонента
    sidebar_height = 800  # Увеличиваем высоту, чтобы использовать все доступное пространство
    css_options = f"""
    <style>
        /* Скрываем заголовки и прочие элементы в сайдбаре */
        div[data-testid="stSidebar"] .block-container {{
            padding-top: 0 !important;
        }}
        
        /* Настройки для HTML компонента */
        div[data-testid="stSidebar"] iframe {{
            border: none !important;
            width: 100% !important;
            height: {sidebar_height}px !important;
            overflow: auto !important;
        }}
        
        /* Скрываем стандартный скролл и добавляем свой */
        div[data-testid="stSidebar"] {{
            overflow-y: hidden !important;
            scrollbar-width: thin !important;
        }}
        
        /* Убираем внутренние отступы в сайдбаре */
        section[data-testid="stSidebar"] > div {{
            padding-top: 0 !important;
            padding-right: 0 !important;
            padding-left: 0 !important;
            padding-bottom: 0 !important;
        }}
        
        /* Скрываем все стандартные заголовки h3 в сайдбаре */
        div[data-testid="stSidebar"] h3 {{
            display: none !important;
        }}
        
        /* Скрываем все прочие элементы в сайдбаре, кроме iframe */
        div[data-testid="stSidebar"] > div > div > div:not(:first-child) {{
            display: none !important;
        }}
    </style>
    """
    
    # Добавляем CSS опции
    st.sidebar.markdown(css_options, unsafe_allow_html=True)
    
    # Создаем HTML для навигации с URL к JSON
    html_content = create_navigation_html(json_url, sidebar_height)
    
    # Отображаем компонент
    components.html(html_content, height=sidebar_height, scrolling=True)
    
    # Неявно добавляем крошечную кнопку для обновления навигации (скрытую в нижней части сайдбара)
    with st.sidebar:
        # Добавляем кнопку обновления, но делаем её очень маленькой и незаметной
        if st.button("↻", help="Обновить навигацию", key="tiny_update_button"):
            st.session_state["update_navigation"] = True
            st.rerun()
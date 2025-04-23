# pages/sidebar.py с использованием сервера статических файлов
"""
Компоненты боковой панели с иерархической навигацией через HTML/JS
"""

import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

import core
from navigation_data import get_navigation_data, prepare_navigation_json
from serve_static import serve_json, create_navigation_html

def sidebar_filters(df_full: pd.DataFrame, create_link_fn=None):
    """
    Отображает HTML/JS компонент для навигации в боковой панели
    
    Args:
        df_full: DataFrame с данными
        create_link_fn: Функция для создания ссылок с параметрами URL (не используется в этой версии)
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
    json_url = serve_json(json_path, key="navigation_json")
    
    # Опции CSS для компонента
    sidebar_height = 600
    css_options = f"""
    <style>
        /* Настройки для HTML компонента */
        iframe {{
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
    </style>
    """
    
    # Добавляем CSS опции
    st.sidebar.markdown(css_options, unsafe_allow_html=True)
    
    # Отображаем компонент
    st.sidebar.markdown("### Навигация")
    
    # Создаем HTML для навигации с URL к JSON
    html_content = create_navigation_html(json_url, sidebar_height)
    
    # Отображаем компонент
    components.html(html_content, height=sidebar_height, scrolling=True)
    
    # Добавляем кнопку для обновления навигации
    with st.sidebar:
        if st.button("🔄 Обновить навигацию"):
            st.session_state["update_navigation"] = True
            st.rerun()
    
    # Добавляем расширенные фильтры внизу
    st.sidebar.markdown("### Расширенные фильтры")
    
    # Фильтр по статусу
    if "status" in df_full.columns:
        status_options = ["Все"] + sorted(df_full["status"].dropna().unique())
        st.sidebar.multiselect(
            "Статус",
            options=status_options[1:],  # Убираем "Все" из опций
            default=st.session_state.get("filter_status", None),
            key="filter_status"
        )
    
    # Фильтр по типу карточек
    if "card_type" in df_full.columns:
        card_type_options = ["Все"] + sorted(df_full["card_type"].dropna().unique())
        st.sidebar.multiselect(
            "Тип карточки",
            options=card_type_options[1:],  # Убираем "Все" из опций
            default=st.session_state.get("filter_card_type", None),
            key="filter_card_type"
        )
    
    # Фильтр по риску
    st.sidebar.slider(
        "Уровень риска",
        min_value=0.0,
        max_value=1.0,
        value=st.session_state.get("filter_risk", (0.0, 1.0)),
        step=0.1,
        key="filter_risk"
    )
    
    # Добавляем информацию о проекте
    st.sidebar.markdown("---")
    st.sidebar.info(
        """
        **Course Quality Dashboard**
        
        Этот инструмент помогает анализировать качество учебных материалов 
        и выявлять проблемные места на основе метрик успешности учащихся.
        
        Версия 3.0
        """
    )
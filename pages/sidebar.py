# pages/sidebar.py с очищенной структурой
"""
Компоненты боковой панели с иерархической навигацией через HTML/JS
"""

import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64  # используется для кодирования при необходимости

from navigation_data import get_navigation_data
from navbar_component import navigation_menu

def render_sidebar():
    """Рендерит основное содержимое сайдбара, включая ссылки на страницы"""
    
    # Это основные страницы, доступные для всех авторизованных пользователей
    st.sidebar.title("Навигация")
    
    menu_items = {
        "Обзор": "overview",
        "Программы": "programs",
        "Модули": "modules",
        "Уроки": "lessons",
        "ГЗ": "gz"
    }
    
    for label, page in menu_items.items():
        if st.sidebar.button(label, key=f"sidebar_{page}"):
            # Используем параметры URL для навигации без перезагрузки страницы
            st.query_params.update({"page": page})
            st.rerun()
    
    # Добавляем разделитель
    st.sidebar.markdown("---")
    
    # Страницы админа, доступные только для ролей admin и methodist_admin
    if st.session_state.role in ["admin", "methodist_admin"]:
        st.sidebar.subheader("Администрирование")
        
        admin_menu = {
            "⚙️ Настройки": "admin",
            "👥 Управление методистами": "methodist_admin",
        }
        
        # Только для admin добавляем страницу планирования рефакторинга
        if st.session_state.role == "admin":
            admin_menu["📅 Планирование рефакторинга"] = "refactor_planning"
        
        for label, page in admin_menu.items():
            if st.sidebar.button(label, key=f"sidebar_{page}"):
                # Прямое обновление URL-параметров без вызова дополнительных функций
                if page == "refactor_planning":
                    print(f"Переход на страницу планирования рефакторинга через боковое меню")
                    st.session_state.current_page = "Планирование рефакторинга"
                    st.query_params = {"page": page}
                    st.rerun()
                else:
                    st.query_params.update({"page": page})
                    st.rerun()
    
    # Страницы методиста, доступные для всех ролей методиста
    if "methodist" in st.session_state.role:
        st.sidebar.subheader("Методистам")
        
        if st.sidebar.button("📝 Мои задачи", key="sidebar_my_tasks"):
            st.query_params.update({"page": "my_tasks"})
            st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**👤 {st.session_state.username}**")
    st.sidebar.markdown(f"**🔑 {st.session_state.role}**")
    
    if st.sidebar.button("Выйти", key="sidebar_logout"):
        # Сбрасываем сессию при выходе
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

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
                
                # Обновляем параметры URL (сохраняется session_state)
                st.query_params.update(**new_params)
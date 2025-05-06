# pages/sidebar.py с очищенной структурой
"""
Компоненты боковой панели с иерархической навигацией через HTML/JS
"""

import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64  # используется для кодирования при необходимости

def render_sidebar():
    """Рендерит основное содержимое сайдбара, включая ссылки на страницы"""
    
    # Убираем секцию "Навигация" с кнопками
    
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
    Отображает базовые фильтры в боковой панели без использования компонента streamlit-navbar
    
    Args:
        df_full: DataFrame с данными
        create_link_fn: Функция для создания ссылок с параметрами URL
    """
    # Получаем текущую страницу и параметры
    query_params = st.query_params
    current_page = query_params.get("page", "overview")
    
    # Вместо использования streamlit-navbar и отображения информации о странице,
    # просто не делаем ничего, чтобы оставить место в сайдбаре чистым
    pass
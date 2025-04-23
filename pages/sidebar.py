# pages/sidebar.py с поддержкой URL-навигации
"""
Компоненты боковой панели
"""

import streamlit as st
import pandas as pd

import core

def sidebar_filters(df_full: pd.DataFrame, create_link_fn=None):
    """
    Каскадные фильтры в сайдбаре — опции зависят от уже выбранных уровней.
    
    Args:
        df_full: DataFrame с данными
        create_link_fn: Функция для создания ссылок с параметрами URL
    """
    st.sidebar.header("Фильтры")
    ctx = df_full.copy()
    
    # Текущая страница (если есть)
    current_page = st.session_state.get("page", "Обзор").lower()
    if current_page == "⚙️ настройки":
        current_page = "admin"

    # Создаем функцию для сброса фильтров с обновлением URL
    def reset_filter(level):
        """Сбрасывает фильтр и дочерние фильтры"""
        # Сначала сбрасываем значение в session_state
        st.session_state[f"filter_{level}"] = None
        core.reset_child(level)  # Сбросить дочерние фильтры при сбросе родительского
        
        # Если доступна функция создания ссылок, перенаправляем на новый URL
        if create_link_fn:
            # Собираем текущие активные фильтры
            params = {}
            for col in core.FILTERS:
                filter_value = st.session_state.get(f"filter_{col}")
                if filter_value:
                    params[col] = filter_value
            
            # Создаем новый URL с текущими фильтрами (без сброшенного)
            new_url = create_link_fn(current_page, **params)
            st.experimental_set_query_params(**params, page=current_page)

    # Создаем функцию для установки фильтра с обновлением URL
    def set_filter(level, value):
        """Устанавливает фильтр и обновляет URL"""
        # Сначала устанавливаем значение в session_state
        st.session_state[f"filter_{level}"] = value
        
        # Если доступна функция создания ссылок, перенаправляем на новый URL
        if create_link_fn:
            # Собираем текущие активные фильтры
            params = {}
            for col in core.FILTERS:
                filter_value = st.session_state.get(f"filter_{col}")
                if filter_value:
                    params[col] = filter_value
            
            # Определяем, какую страницу показывать на основе выбранных фильтров
            target_page = current_page
            
            # Если меняется уровень, меняем и страницу
            if level == "program" and value is not None:
                target_page = "programs"
            elif level == "module" and value is not None:
                target_page = "modules"
            elif level == "lesson" and value is not None:
                target_page = "lessons"
            elif level == "gz" and value is not None:
                target_page = "gz"
            
            # Устанавливаем новые параметры URL
            st.experimental_set_query_params(**params, page=target_page)

    for col in core.FILTERS:
        # Сжимаем контекст ОПЕРЕЖАЮЩЕ, если родитель уже выбран
        for prev_col in core.FILTERS[:core.FILTERS.index(col)]:
            prev_val = st.session_state.get(f"filter_{prev_col}")
            if prev_val:
                ctx = ctx[ctx[prev_col] == prev_val]

        options = ["Все"] + sorted(ctx[col].dropna().unique())
        current = st.session_state.get(f"filter_{col}") or "Все"
        if current not in options:
            current = "Все"

        # Используем ключ без "sb_" префикса, чтобы избежать путаницы
        sel = st.sidebar.selectbox(
            col.capitalize(),
            options,
            index=options.index(current),
            key=f"sidebar_{col}"
        )

        # Обрабатываем изменение фильтра с учетом URL-навигации
        if sel == "Все":
            if st.session_state.get(f"filter_{col}"):
                reset_filter(col)
        else:
            if st.session_state.get(f"filter_{col}") != sel:
                set_filter(col, sel)
    
    # Добавляем разделитель
    st.sidebar.markdown("---")
    
    # Добавляем дополнительные фильтры, если нужно
    if st.sidebar.checkbox("Расширенные фильтры", False):
        # Фильтр по статусу
        if "status" in df_full.columns:
            status_options = ["Все"] + sorted(df_full["status"].dropna().unique())
            st.sidebar.multiselect(
                "Статус",
                options=status_options[1:],  # Убираем "Все" из опций
                default=None,
                key="filter_status"
            )
        
        # Фильтр по типу карточек
        if "card_type" in df_full.columns:
            card_type_options = ["Все"] + sorted(df_full["card_type"].dropna().unique())
            st.sidebar.multiselect(
                "Тип карточки",
                options=card_type_options[1:],  # Убираем "Все" из опций
                default=None,
                key="filter_card_type"
            )
        
        # Фильтр по риску
        st.sidebar.slider(
            "Уровень риска",
            min_value=0.0,
            max_value=1.0,
            value=(0.0, 1.0),
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
        """
    )
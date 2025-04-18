# pages/sidebar.py
"""
Компоненты боковой панели
"""

import streamlit as st
import pandas as pd

import core

def sidebar_filters(df_full: pd.DataFrame):
    """Каскадные фильтры в сайдбаре — опции зависят от уже выбранных уровней."""
    st.sidebar.header("Фильтры")
    ctx = df_full.copy()

    for col in core.FILTERS:
        # сжимаем контекст ОПЕРЕЖАЮЩЕ, если родитель уже выбран
        for prev_col in core.FILTERS[:core.FILTERS.index(col)]:
            prev_val = st.session_state.get(f"filter_{prev_col}")
            if prev_val:
                ctx = ctx[ctx[prev_col] == prev_val]

        options = ["Все"] + sorted(ctx[col].dropna().unique())
        current = st.session_state.get(f"filter_{col}") or "Все"
        if current not in options:
            current = "Все"

        sel = st.sidebar.selectbox(
            col.capitalize(),
            options,
            index=options.index(current),
            key=f"sb_{col}",
        )

        if sel == "Все":
            st.session_state[f"filter_{col}"] = None
            core.reset_child(col)  # Сбросить дочерние фильтры при сбросе родительского
        else:
            st.session_state[f"filter_{col}"] = sel
            
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
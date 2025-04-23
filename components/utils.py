# components/utils.py с поддержкой URL-навигации
"""
Вспомогательные функции для компонентов интерфейса
"""

import streamlit as st
import pandas as pd
import numpy as np

def create_hierarchical_header(levels, values, emoji_map=None):
    """
    Создает иерархический заголовок страницы в виде "лесенки" с кликабельными элементами
    
    Args:
        levels: Список названий уровней иерархии
        values: Список значений для каждого уровня
        emoji_map: Словарь с эмодзи для каждого уровня
    """
    import core
    import urllib.parse as ul
    
    if emoji_map is None:
        emoji_map = {
            "program": "📚",
            "module": "📘",
            "lesson": "📝",
            "gz": "🧩",
            "card": "🗂️"
        }
    
    # Текущая страница
    current_page = st.session_state.get("page", "Обзор").lower()
    if current_page == "⚙️ настройки":
        current_page = "admin"
    
    # Заголовок страницы
    current_level = levels[-1]
    current_value = values[-1] or '—'
    emoji = emoji_map.get(current_level, "📊")
    
    st.header(f"{emoji} {current_level.capitalize()}: {current_value}")
    
    # Создаем "лесенку" навигации с улучшенным UI и кликабельными элементами
    nav_col1, nav_col2 = st.columns([1, 3])
    
    with nav_col1:
        for level in levels:
            st.markdown(f"**{level.capitalize()}:**")
    
    with nav_col2:
        for i, value in enumerate(values):
            if value and i < len(levels):  # Проверяем, что значение существует и уровень соответствует
                # Определяем, на какую страницу вести при клике
                level = levels[i]
                target_page = level + "s"  # Например, program -> programs
                if level == "gz":
                    target_page = "gz"  # Особый случай для ГЗ
                
                # Собираем параметры для URL
                params = {}
                for j, l in enumerate(levels[:i+1]):
                    if values[j]:
                        params[l] = values[j]
                
                # Создаем ссылку
                url = "?" + "&".join([f"{k}={ul.quote_plus(str(v))}" for k, v in params.items()]) + f"&page={target_page}"
                
                st.markdown(
                    f'<a href="{url}" target="_self" '
                    'style="text-decoration:none;color:#4da6ff;font-weight:600;">'
                    f'{value}</a>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"**{value or '—'}**")
    
    # Добавляем разделитель
    st.markdown("---")

def display_clickable_items(df, column, level, metrics=None):
    """
    Отображает список кликабельных элементов в две колонки
    
    Args:
        df: DataFrame с данными
        column: Колонка с названиями элементов
        level: Уровень для перехода при клике
        metrics: Список метрик для отображения рядом с элементом
    """
    import urllib.parse as ul
    
    # Получаем уникальные значения и метрики для них
    if metrics:
        agg_df = df.groupby(column).agg(
            success=("success_rate", "mean"),
            complaints=("complaint_rate", "mean"),
            risk=("risk", "mean"),
            cards=("card_id", "nunique")
        ).reset_index()
    else:
        agg_df = df.groupby(column).agg(
            cards=("card_id", "nunique")
        ).reset_index()
    
    # Сортируем по колонке
    sorted_df = agg_df.sort_values(column)
    
    # Разбиваем на две колонки
    col1, col2 = st.columns(2)
    
    half = len(sorted_df) // 2 + len(sorted_df) % 2
    
    # Собираем текущие фильтры
    current_filters = {}
    for filter_col in ["program", "module", "lesson", "gz"]:
        if st.session_state.get(f"filter_{filter_col}"):
            current_filters[filter_col] = st.session_state[f"filter_{filter_col}"]
    
    # Определяем целевую страницу
    target_page = level + "s"  # Например, program -> programs
    if level == "gz":
        target_page = "gz"  # Особый случай для ГЗ
    elif level == "card":
        target_page = "cards"
    
    for i, (_, row) in enumerate(sorted_df.iterrows()):
        # Определяем, в какую колонку добавить элемент
        current_col = col1 if i < half else col2
        
        with current_col:
            c1, c2 = st.columns([4, 3])
            with c1:
                # Создаем параметры URL
                url_params = current_filters.copy()
                url_params[level] = row[column]
                
                # Создаем URL
                url = "?" + "&".join([f"{k}={ul.quote_plus(str(v))}" for k, v in url_params.items()]) + f"&page={target_page}"
                
                # Создаем ссылку
                st.markdown(
                    f'<a href="{url}" target="_self" '
                    'style="text-decoration:none;color:#4da6ff;font-weight:600;">'
                    f'{row[column]}</a>',
                    unsafe_allow_html=True,
                )
            with c2:
                if metrics:
                    # Создаем строку с метриками
                    metrics_str = []
                    if "cards" in metrics:
                        metrics_str.append(f"Cards: {row.cards}")
                    if "risk" in metrics:
                        metrics_str.append(f"Risk: {row.risk:.2f}")
                    if "success" in metrics:
                        metrics_str.append(f"Success: {row.success:.1%}")
                    if "complaints" in metrics:
                        metrics_str.append(f"Compl: {row.complaints:.1%}")
                    
                    st.markdown(f"{' | '.join(metrics_str)}")
                else:
                    st.markdown(f"Cards: {row.cards}")

def add_gz_links(df, gz_filter):
    """
    Добавляет ссылки на ГЗ в начало страницы, если выбран фильтр ГЗ
    
    Args:
        df: DataFrame с данными
        gz_filter: Текущий фильтр ГЗ
    """
    # Если выбрана группа заданий, добавляем кнопки со ссылками
    if gz_filter and 'gz_id' in df.columns:
        # Получаем ID группы заданий
        gz_id = df.loc[df.gz == gz_filter, 'gz_id'].iloc[0] if not df.empty else None
        
        if gz_id:
            st.markdown("### Ссылки для группы заданий")
            link_col1, link_col2 = st.columns(2)
            
            with link_col1:
                st.markdown(f"[🔗 Ссылка для редактирования](https://education.yandex-team.ru/exercise/edit/{gz_id})")
            
            with link_col2:
                st.markdown(f"[🌐 Публичная ссылка](https://education.yandex.ru/classroom/public-lesson/{gz_id}/run/)")
            
            st.markdown("---")
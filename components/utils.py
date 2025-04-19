# components/utils.py
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
    
    if emoji_map is None:
        emoji_map = {
            "program": "📚",
            "module": "📘",
            "lesson": "📝",
            "gz": "🧩",
            "card": "🗂️"
        }
    
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
                # Создаем кликабельную ссылку, используя функцию clickable
                level = levels[i]
                core.clickable(value, level)
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
    import core
    
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
    
    for i, (_, row) in enumerate(sorted_df.iterrows()):
        # Определяем, в какую колонку добавить элемент
        current_col = col1 if i < half else col2
        
        with current_col:
            c1, c2 = st.columns([4, 3])
            with c1:
                core.clickable(row[column], level)
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
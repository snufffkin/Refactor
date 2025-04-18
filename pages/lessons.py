# pages/lessons.py
"""
Страница урока (Обзор + навигация по группам заданий)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

import core
from components.utils import create_hierarchical_header, display_clickable_items
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart, display_completion_radar

def page_lessons(df: pd.DataFrame):
    """Страница урока с детализацией по группам заданий"""
    # Фильтруем данные по выбранной программе, модулю и уроку
    df_lesson = core.apply_filters(df, ["program", "module", "lesson"])
    program_filter = st.session_state.get('filter_program')
    module_filter = st.session_state.get('filter_module')
    lesson_filter = st.session_state.get('filter_lesson')
    
    # Создаем иерархический заголовок
    create_hierarchical_header(
        levels=["program", "module", "lesson"],
        values=[program_filter, module_filter, lesson_filter]
    )
    
    # Проверка наличия данных после фильтрации
    if df_lesson.empty:
        st.warning(f"Нет данных для урока '{lesson_filter}' в модуле '{module_filter}'")
        return
    
    # 1. Отображаем общие метрики урока
    st.subheader("📈 Метрики урока")
    display_metrics_row(df_lesson, compare_with=df)
    
    # 2. Отображаем распределение риска и статусы
    col1, col2 = st.columns(2)
    
    with col1:
        display_risk_distribution(df_lesson, "gz")
    
    with col2:
        display_status_chart(df_lesson, "gz")
    
    # 3. Визуализируем группы заданий в виде столбчатой диаграммы
    st.subheader("📊 Группы заданий")
    
    # Агрегируем данные по группам заданий
    agg = df_lesson.groupby("gz").agg(
        risk=("risk", "mean"),
        success=("success_rate", "mean"),
        complaints=("complaint_rate", "mean"),
        discrimination=("discrimination_avg", "mean"),
        cards=("card_id", "nunique")
    ).reset_index()
    
    # Создаем столбчатую диаграмму риска по группам заданий
    fig = px.bar(
        agg,
        x="gz",
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={"gz": "Группа заданий", "risk": "Риск"},
        title="Уровень риска по группам заданий",
        hover_data=["success", "complaints", "discrimination", "cards"]
    )
    
    # Добавляем горизонтальные линии для границ категорий риска
    fig.add_hline(y=0.3, line_dash="dash", line_color="green", 
                  annotation_text="Низкий риск", annotation_position="left")
    fig.add_hline(y=0.5, line_dash="dash", line_color="gold", 
                  annotation_text="Средний риск", annotation_position="left")
    fig.add_hline(y=0.7, line_dash="dash", line_color="red", 
                  annotation_text="Высокий риск", annotation_position="left")
    
    # Форматируем подсказки
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>" +
                      "Риск: %{y:.2f}<br>" +
                      "Успешность: %{customdata[0]:.1%}<br>" +
                      "Жалобы: %{customdata[1]:.1%}<br>" +
                      "Дискриминативность: %{customdata[2]:.2f}<br>" +
                      "Карточек: %{customdata[3]}"
    )
    
    fig.update_layout(
        xaxis_title="Группа заданий",
        yaxis_title="Риск",
        xaxis_tickangle=-45 if len(agg) > 8 else 0
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 4. Детальное сравнение групп заданий
    st.subheader("📊 Детальное сравнение групп заданий")
    
    # Создаем вкладки для разных представлений
    tabs = st.tabs(["Ключевые метрики", "Успешность и жалобы", "Радарная диаграмма"])
    
    with tabs[0]:
        # График сравнения нескольких метрик
        display_metrics_comparison(
            df_lesson,
            "gz",
            ["success_rate", "complaint_rate", "discrimination_avg", "risk"],
            limit=15,
            title="Сравнение ключевых метрик по группам заданий"
        )
    
    with tabs[1]:
        # График зависимости успешности и жалоб
        display_success_complaints_chart(df_lesson, "gz", limit=20)
    
    with tabs[2]:
        # Радарная диаграмма для топ-5 групп заданий с высоким риском
        display_completion_radar(df_lesson, "gz", limit=5)
    
    # 5. Таблица с группами заданий
    st.subheader("📋 Детальная информация по группам заданий")
    
    # Улучшенная таблица с группами заданий
    detailed_df = agg[["gz", "risk", "success", "complaints", "discrimination", "cards"]]
    
    st.dataframe(
        detailed_df.style.format({
            "risk": "{:.2f}",
            "success": "{:.1%}",
            "complaints": "{:.1%}",
            "discrimination": "{:.2f}"
        }).background_gradient(
            subset=["risk"],
            cmap="RdYlGn_r"
        ),
        use_container_width=True
    )
    
    # 6. Список групп заданий с кликабельными ссылками
    st.subheader("🧩 Список групп заданий")
    display_clickable_items(df_lesson, "gz", "gz", metrics=["cards", "risk", "success"])
    
    # Встроенная версия страницы уроков для использования в других страницах
    
def _page_lessons_inline(df: pd.DataFrame):
    """Встроенная версия страницы уроков для отображения на странице модуля"""
    # Фильтруем данные по выбранной программе и модулю
    df_mod = core.apply_filters(df, ["program", "module"])
    
    # Проверка наличия данных после фильтрации
    if df_mod.empty:
        mod_name = st.session_state.get('filter_module') or '—'
        st.warning(f"Нет данных для модуля '{mod_name}'")
        return
    
    # Заголовок
    st.subheader("🏫 Уроки выбранного модуля")
    
    # Агрегируем данные по урокам
    agg = df_mod.groupby("lesson").agg(
        risk=("risk", "mean"),
        success=("success_rate", "mean"),
        complaints=("complaint_rate", "mean"),
        cards=("card_id", "nunique")
    ).reset_index()
    
    # Сортируем уроки по порядку, если есть такая колонка
    if "lesson_order" in df_mod.columns:
        lesson_order = df_mod.groupby("lesson")["lesson_order"].first().reset_index()
        agg = agg.merge(lesson_order, on="lesson", how="left")
        agg = agg.sort_values("lesson_order")
    
    # Создаем график
    fig = px.bar(
        agg,
        x="lesson",
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={"lesson": "Урок", "risk": "Риск"},
        title="Уровень риска по урокам",
        hover_data=["success", "complaints", "cards"]
    )
    
    # Форматируем подсказки
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>" +
                      "Риск: %{y:.2f}<br>" +
                      "Успешность: %{customdata[0]:.1%}<br>" +
                      "Жалобы: %{customdata[1]:.1%}<br>" +
                      "Карточек: %{customdata[2]}"
    )
    
    fig.update_layout(
        xaxis_tickangle=-45 if len(agg) > 8 else 0
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Таблица с уроками
    st.dataframe(
        agg.style.format({
            "risk": "{:.2f}",
            "success": "{:.1%}",
            "complaints": "{:.1%}"
        }),
        use_container_width=True
    )
    
    # Список кликабельных уроков
    display_clickable_items(df_mod, "lesson", "lesson", metrics=["cards", "risk"])
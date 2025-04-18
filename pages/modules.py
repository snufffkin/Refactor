# pages/modules.py
"""
Страница модуля (Обзор + навигация по урокам)
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

def page_modules(df: pd.DataFrame):
    """Страница модуля с детализацией по урокам"""
    # Фильтруем данные по выбранной программе и модулю
    df_mod = core.apply_filters(df, ["program", "module"])
    program_filter = st.session_state.get('filter_program')
    module_filter = st.session_state.get('filter_module')
    
    # Создаем иерархический заголовок
    create_hierarchical_header(
        levels=["program", "module"],
        values=[program_filter, module_filter]
    )
    
    # Проверка наличия данных после фильтрации
    if df_mod.empty:
        st.warning(f"Нет данных для модуля '{module_filter}' в программе '{program_filter}'")
        return
    
    # 1. Отображаем общие метрики модуля
    st.subheader("📈 Метрики модуля")
    display_metrics_row(df_mod, compare_with=df)
    
    # 2. Отображаем распределение риска и статусы
    col1, col2 = st.columns(2)
    
    with col1:
        display_risk_distribution(df_mod, "lesson")
    
    with col2:
        display_status_chart(df_mod, "lesson")
    
    # 3. Визуализируем уроки в виде столбчатой диаграммы
    st.subheader("📊 Уроки модуля")
    
    # Агрегируем данные по урокам
    agg = df_mod.groupby("lesson").agg(
        risk=("risk", "mean"),
        success=("success_rate", "mean"),
        complaints=("complaint_rate", "mean"),
        discrimination=("discrimination_avg", "mean"),
        cards=("card_id", "nunique")
    ).reset_index()
    
    # Сортируем уроки по порядку, если есть такая колонка
    if "lesson_order" in df_mod.columns:
        lesson_order = df_mod.groupby("lesson")["lesson_order"].first().reset_index()
        agg = agg.merge(lesson_order, on="lesson", how="left")
        agg = agg.sort_values("lesson_order")
    
    # Создаем столбчатую диаграмму риска по урокам
    fig = px.bar(
        agg,
        x="lesson",
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={"lesson": "Урок", "risk": "Риск"},
        title="Уровень риска по урокам",
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
        xaxis_title="Урок",
        yaxis_title="Риск",
        xaxis_tickangle=-45 if len(agg) > 8 else 0
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 4. Детальное сравнение уроков
    st.subheader("📊 Детальное сравнение уроков")
    
    # Создаем вкладки для разных представлений
    tabs = st.tabs(["Метрики уроков", "Успешность и жалобы", "Радарная диаграмма"])
    
    with tabs[0]:
        # График сравнения нескольких метрик
        display_metrics_comparison(
            df_mod,
            "lesson",
            ["success_rate", "complaint_rate", "discrimination_avg", "risk"],
            limit=15,
            title="Сравнение ключевых метрик по урокам"
        )
    
    with tabs[1]:
        # График зависимости успешности и жалоб
        display_success_complaints_chart(df_mod, "lesson", limit=20)
    
    with tabs[2]:
        # Радарная диаграмма для топ-5 уроков с высоким риском
        display_completion_radar(df_mod, "lesson", limit=5)
    
    # 5. Таблица с уроками
    st.subheader("📋 Детальная информация по урокам")
    
    # Улучшенная таблица с уроками
    detailed_df = agg[["lesson", "risk", "success", "complaints", "discrimination", "cards"]]
    
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
    
    # 6. Список уроков с кликабельными ссылками
    st.subheader("📖 Список уроков")
    display_clickable_items(df_mod, "lesson", "lesson", metrics=["cards", "risk", "success"])
    
    # 7. Если урок выбран, показываем встроенную страницу ГЗ
    if st.session_state.get("filter_lesson"):
        from .gz import _page_gz_inline
        
        # Добавляем разделитель
        st.markdown("---")
        _page_gz_inline(df)
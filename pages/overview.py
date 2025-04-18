# pages/overview.py
"""
Страница обзора программ
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

import core
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart

def page_overview(df: pd.DataFrame):
    """Страница с обзором всех программ"""
    st.header("📊 Обзор программ")
    
    # Добавляем краткое описание
    with st.expander("ℹ️ О дашборде", expanded=False):
        st.markdown("""
        ### Дашборд качества курсов
        
        Этот дашборд помогает анализировать качество учебных материалов на всех уровнях:
        - **Программы**: Общий обзор всех программ
        - **Модули**: Детализация по модулям выбранной программы
        - **Уроки**: Анализ уроков в выбранном модуле
        - **Группы заданий (ГЗ)**: Детализация по группам заданий в уроке
        - **Карточки**: Подробный анализ отдельных заданий
        
        Используйте фильтры в боковой панели для навигации по уровням.
        
        **Ключевые метрики**:
        - **Успешность**: Процент успешных попыток решения заданий
        - **Жалобы**: Процент заданий, на которые поступили жалобы
        - **Дискриминативность**: Показатель способности задания различать знающих/незнающих студентов
        - **Риск**: Комплексный показатель проблемности задания (выше = хуже)
        """)
    
    # 1. Отображаем общие метрики
    st.subheader("📈 Ключевые метрики")
    display_metrics_row(df)
    
    # 2. Отображаем распределение риска
    col1, col2 = st.columns(2)
    
    with col1:
        # Распределение риска по категориям
        display_risk_distribution(df, "program")
    
    with col2:
        # Статусы карточек
        display_status_chart(df, "card_id")
    
    # 3. Визуализируем программы в виде тримапа и рейтинга
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Treemap для программ
        agg = core.agg_by(df, "program")
        fig = px.treemap(
            agg, 
            path=["program"], 
            values="cards", 
            color="risk", 
            color_continuous_scale="RdYlGn_r",
            hover_data=["success", "complaints"]
        )
        
        # Улучшаем формат подсказок
        fig.update_traces(
            hovertemplate="<b>%{label}</b><br>" +
                          "Карточек: %{value}<br>" +
                          "Риск: %{color:.2f}<br>" +
                          "Успешность: %{customdata[0]:.1%}<br>" +
                          "Жалобы: %{customdata[1]:.1%}"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Топ программ с высоким риском
        high_risk_programs = display_risk_bar_chart(
            df, 
            "program", 
            title="Топ программ по уровню риска"
        )
    
    # 4. Сравнение метрик для программ
    st.subheader("📊 Сравнение метрик по программам")
    
    tab1, tab2 = st.tabs(["Успешность и жалобы", "Метрики программ"])
    
    with tab1:
        # График сравнения успешности и жалоб
        display_success_complaints_chart(df, "program", limit=20)
    
    with tab2:
        # График сравнения нескольких метрик
        display_metrics_comparison(
            df,
            "program",
            ["success_rate", "complaint_rate", "discrimination_avg", "risk"],
            limit=10
        )
    
    # 5. Список программ с кликабельными ссылками
    st.subheader("📚 Список программ")
    
    # Группируем данные по программам
    agg = core.agg_by(df, "program")
    
    # Создаем таблицу с метриками
    st.dataframe(
        agg.style.format({
            "success": "{:.1%}", 
            "complaints": "{:.1%}", 
            "risk": "{:.2f}"
        }),
        use_container_width=True
    )
    
    # Отображаем кликабельный список программ
    from components.utils import display_clickable_items
    display_clickable_items(df, "program", "program", metrics=["cards", "risk", "success"])
    
    # 6. Дополнительная аналитика
    if st.checkbox("Показать дополнительную аналитику", value=False):
        st.subheader("📋 Дополнительная аналитика")
        
        # Добавляем график общего соотношения статусов карточек
        status_counts = df["status"].value_counts().reset_index()
        status_counts.columns = ["Статус", "Количество"]
        
        fig = px.pie(
            status_counts, 
            values="Количество", 
            names="Статус",
            title="Общее распределение по статусам",
            color="Статус",
            color_discrete_map={
                "new": "#d3d3d3",
                "in_work": "#add8e6",
                "ready_for_qc": "#fffacd",
                "done": "#90ee90",
                "wont_fix": "#f08080"
            }
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Распределение типов карточек
        if "card_type" in df.columns:
            card_type_counts = df["card_type"].value_counts().reset_index()
            card_type_counts.columns = ["Тип карточки", "Количество"]
            
            fig = px.bar(
                card_type_counts,
                x="Тип карточки",
                y="Количество",
                title="Распределение типов карточек"
            )
            
            st.plotly_chart(fig, use_container_width=True)
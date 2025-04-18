# pages/programs.py
"""
Страница программы (Обзор + навигация по модулям)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

import core
from components.utils import create_hierarchical_header, display_clickable_items
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart

def page_programs(df: pd.DataFrame):
    """Страница программы с детализацией по модулям"""
    # Фильтруем данные по выбранной программе
    df_prog = core.apply_filters(df, ["program"])
    prog_name = st.session_state.get('filter_program')
    
    # Создаем иерархический заголовок
    create_hierarchical_header(
        levels=["program"],
        values=[prog_name]
    )
    
    # Проверка наличия данных после фильтрации
    if df_prog.empty:
        st.warning(f"Нет данных для программы '{prog_name}'")
        return
    
    # 1. Отображаем общие метрики программы
    st.subheader("📈 Метрики программы")
    display_metrics_row(df_prog, compare_with=df)
    
    # 2. Отображаем распределение риска и статусы
    col1, col2 = st.columns(2)
    
    with col1:
        display_risk_distribution(df_prog, "module")
    
    with col2:
        display_status_chart(df_prog, "module")
    
    # 3. Визуализируем модули в виде столбчатой диаграммы
    st.subheader("📊 Модули программы")
    
    # Агрегируем данные по модулям
    agg = df_prog.groupby("module").agg(
        risk=("risk", "mean"),
        success=("success_rate", "mean"),
        complaints=("complaint_rate", "mean"),
        discrimination=("discrimination_avg", "mean"),
        cards=("card_id", "nunique")
    ).reset_index()
    
    # Сортируем модули по порядку, если есть такая колонка
    if "module_order" in df_prog.columns:
        module_order = df_prog.groupby("module")["module_order"].first().reset_index()
        agg = agg.merge(module_order, on="module", how="left")
        agg = agg.sort_values("module_order")
    
    # Создаем столбчатую диаграмму риска по модулям
    fig = px.bar(
        agg,
        x="module",
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={"module": "Модуль", "risk": "Риск"},
        title="Уровень риска по модулям"
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
                      "Карточек: %{customdata[4]}"
    )
    
    fig.update_layout(
        xaxis_title="Модуль",
        yaxis_title="Риск",
        xaxis_tickangle=-45 if len(agg) > 8 else 0
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 4. Сравнение метрик для модулей
    st.subheader("📊 Сравнение метрик по модулям")
    
    tab1, tab2 = st.tabs(["Успешность и жалобы", "Метрики модулей"])
    
    with tab1:
        # График зависимости успешности и жалоб
        display_success_complaints_chart(df_prog, "module")
    
    with tab2:
        # График сравнения нескольких метрик
        display_metrics_comparison(
            df_prog,
            "module",
            ["success_rate", "complaint_rate", "discrimination_avg", "risk"],
            limit=10
        )
    
    # 5. Таблица с модулями
    st.subheader("📋 Детальная информация по модулям")
    
    # Улучшенная таблица с модулями
    detailed_df = agg[["module", "risk", "success", "complaints", "discrimination", "cards"]]
    
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
    
    # 6. Список модулей с кликабельными ссылками
    st.subheader("📚 Список модулей")
    display_clickable_items(df_prog, "module", "module", metrics=["cards", "risk", "success"])
    
    # 7. Если модуль выбран, показываем встроенную страницу уроков
    if st.session_state.get("filter_module"):
        from .lessons import _page_lessons_inline
        
        # Добавляем разделитель
        st.markdown("---")
        _page_lessons_inline(df)
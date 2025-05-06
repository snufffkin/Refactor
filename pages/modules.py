# pages/modules.py с обновленной нумерацией для графиков
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
import navigation_utils

def page_modules(df: pd.DataFrame):
    """Страница модуля с детализацией по урокам"""
    # Фильтруем данные по выбранной программе и модулю
    df_module = core.apply_filters(df, ["program", "module"])
    prog_name = st.session_state.get('filter_program')
    module_name = st.session_state.get('filter_module')
    
    # Создаем иерархический заголовок
    create_hierarchical_header(
        levels=["program", "module"],
        values=[prog_name, module_name]
    )
    
    # Проверка наличия данных после фильтрации
    if df_module.empty:
        st.warning(f"Нет данных для модуля '{module_name}' в программе '{prog_name}'")
        return
    
    # 1. Отображаем общие метрики модуля
    st.subheader("📈 Метрики модуля")
    display_metrics_row(df_module, compare_with=df[df["program"] == prog_name])
    
    # Добавляем метрику среднего суммарного времени на урок
    lessons_data = df_module.groupby("lesson").agg(
        total_time_median=("time_median", "sum")
    ).reset_index()
    
    avg_time_per_lesson = lessons_data["total_time_median"].mean() if not lessons_data.empty else 0
    avg_time_per_lesson = avg_time_per_lesson / 60
    
    # Отображаем метрику времени
    st.subheader("⏱️ Среднее время на урок")
    st.metric(
        label="Среднее суммарное время на урок (мин)",
        value=f"{avg_time_per_lesson:.1f}"
    )
    
    # 2. Отображаем распределение риска и статусы
    col1, col2 = st.columns(2)
    
    with col1:
        display_risk_distribution(df_module, "lesson")
    
    with col2:
        display_status_chart(df_module, "lesson")
    
    # 3. Визуализируем уроки в виде столбчатой диаграммы
    st.subheader("📊 Уроки модуля")
    
    # Агрегируем данные по урокам
    agg = df_module.groupby("lesson").agg(
        risk=("risk", "mean"),
        success=("success_rate", "mean"),
        complaints=("complaint_rate", "mean"),
        discrimination=("discrimination_avg", "mean"),
        cards=("card_id", "nunique")
    ).reset_index()
    
    # Сортируем уроки по порядку, если есть такая колонка
    if "lesson_order" in df_module.columns:
        lesson_order = df_module.groupby("lesson")["lesson_order"].first().reset_index()
        agg = agg.merge(lesson_order, on="lesson", how="left")
        agg = agg.sort_values("lesson_order")
    else:
        # Если нет колонки с порядком, сортируем по риску
        agg = agg.sort_values("risk", ascending=False)
    
    # Добавляем последовательную нумерацию
    agg = agg.reset_index(drop=True)
    agg["lesson_num"] = agg.index + 1
    
    # Создаем столбчатую диаграмму риска по урокам с использованием порядковых номеров
    fig = px.bar(
        agg,
        x="lesson_num",  # Используем последовательную нумерацию вместо ID
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={"lesson_num": "Номер урока", "risk": "Риск"},
        title="Уровень риска по урокам",
        hover_data=["lesson", "success", "complaints", "discrimination", "cards"]  # Добавляем реальное название в подсказку
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
        hovertemplate="<b>Урок: %{customdata[0]}</b><br>" +
                      "Номер: %{x}<br>" +
                      "Риск: %{y:.2f}<br>" +
                      "Успешность: %{customdata[1]:.1%}<br>" +
                      "Жалобы: %{customdata[2]:.1%}<br>" +
                      "Дискриминативность: %{customdata[3]:.2f}<br>" +
                      "Карточек: %{customdata[4]}"
    )
    
    fig.update_layout(
        xaxis_title="Номер урока",
        yaxis_title="Риск",
        xaxis_tickangle=0  # Убираем наклон, т.к. числа компактны
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 4. Детальное сравнение уроков
    st.subheader("📊 Детальное сравнение уроков")
    
    # Создаем вкладки для разных представлений
    tabs = st.tabs(["Метрики уроков", "Успешность и жалобы", "Радарная диаграмма"])
    
    with tabs[0]:
        # График сравнения нескольких метрик - используем нумерацию вместо ID
        agg_metrics = df_module.groupby("lesson").agg(
            success_rate=("success_rate", "mean"),
            complaint_rate=("complaint_rate", "mean"),
            discrimination_avg=("discrimination_avg", "mean"),
            risk=("risk", "mean")
        ).reset_index()
        
        # Добавляем последовательную нумерацию для групп заданий
        if "lesson_order" in df_module.columns:
            lesson_order = df_module.groupby("lesson")["lesson_order"].first().reset_index()
            agg_metrics = agg_metrics.merge(lesson_order, on="lesson", how="left")
            agg_metrics = agg_metrics.sort_values("lesson_order")
        else:
            agg_metrics = agg_metrics.sort_values("risk", ascending=False)
        
        agg_metrics = agg_metrics.reset_index(drop=True)
        agg_metrics["lesson_num"] = agg_metrics.index + 1
        
        # Ограничиваем количество уроков для отображения
        agg_metrics = agg_metrics.head(15)
        
        # Переводим в формат "длинных данных" для графика
        melted_df = pd.melt(
            agg_metrics,
            id_vars=["lesson", "lesson_num"],
            value_vars=["success_rate", "complaint_rate", "discrimination_avg", "risk"],
            var_name="metric",
            value_name="value"
        )
        
        # Переименование метрик для отображения
        metric_names = {
            "success_rate": "Успешность",
            "complaint_rate": "Жалобы",
            "discrimination_avg": "Дискриминативность",
            "risk": "Риск"
        }
        melted_df["metric_name"] = melted_df["metric"].map(metric_names)
        
        # Создаем график сравнения метрик
        fig_metrics = px.bar(
            melted_df,
            x="lesson_num",  # Используем порядковые номера вместо ID
            y="value",
            color="metric_name",
            barmode="group",
            hover_data=["lesson"],  # Показываем реальное название в подсказке
            labels={
                "lesson_num": "Номер урока",
                "value": "Значение",
                "metric_name": "Метрика"
            },
            title="Сравнение ключевых метрик по урокам"
        )
        
        # Настраиваем формат оси Y в зависимости от метрики
        fig_metrics.update_layout(
            yaxis_tickformat=".1%",
            xaxis_tickangle=0  # Убираем наклон, т.к. числа компактны
        )
        
        st.plotly_chart(fig_metrics, use_container_width=True)
    
    with tabs[1]:
        # График зависимости успешности и жалоб
        display_success_complaints_chart(df_module, "lesson", limit=20)
    
    with tabs[2]:
        # Радарная диаграмма для топ-5 уроков с высоким риском
        display_completion_radar(df_module, "lesson", limit=5)
    
    # 5. Таблица с уроками
    st.subheader("📋 Детальная информация по урокам")
    
    # Улучшенная таблица с уроками, добавляем номер для соответствия с графиком
    detailed_df = agg[["lesson_num", "lesson", "risk", "success", "complaints", "discrimination", "cards"]]
    detailed_df.columns = ["Номер", "Урок", "Риск", "Успешность", "Жалобы", "Дискриминативность", "Карточек"]
    
    st.dataframe(
        detailed_df.style.format({
            "Риск": "{:.2f}",
            "Успешность": "{:.1%}",
            "Жалобы": "{:.1%}",
            "Дискриминативность": "{:.2f}"
        }).background_gradient(
            subset=["Риск"],
            cmap="RdYlGn_r"
        ),
        use_container_width=True
    )
    
    # 6. Список уроков с кликабельными ссылками
    st.subheader("📖 Список уроков")
    display_clickable_items(df_module, "lesson", "lesson", metrics=["cards", "risk", "success"])
    
    # 7. Если урок выбран, показываем встроенную страницу ГЗ
    if st.session_state.get("filter_lesson"):
        from .gz import _page_gz_inline
        
        # Добавляем разделитель
        st.markdown("---")
        _page_gz_inline(df)
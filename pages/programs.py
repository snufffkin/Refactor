# pages/programs.py с обновленной нумерацией для графиков
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
    else:
        # Если нет колонки с порядком, сортируем по риску
        agg = agg.sort_values("risk", ascending=False)
    
    # Добавляем последовательную нумерацию
    agg = agg.reset_index(drop=True)
    agg["module_num"] = agg.index + 1
    
    # Создаем столбчатую диаграмму риска по модулям с использованием порядковых номеров
    fig = px.bar(
        agg,
        x="module_num",  # Используем последовательную нумерацию вместо ID
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={"module_num": "Номер модуля", "risk": "Риск"},
        title="Уровень риска по модулям",
        hover_data=["module", "success", "complaints", "discrimination", "cards"]  # Добавляем реальное название в подсказку
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
        hovertemplate="<b>Модуль: %{customdata[0]}</b><br>" +
                      "Номер: %{x}<br>" +
                      "Риск: %{y:.2f}<br>" +
                      "Успешность: %{customdata[1]:.1%}<br>" +
                      "Жалобы: %{customdata[2]:.1%}<br>" +
                      "Дискриминативность: %{customdata[3]:.2f}<br>" +
                      "Карточек: %{customdata[4]}"
    )
    
    fig.update_layout(
        xaxis_title="Номер модуля",
        yaxis_title="Риск",
        xaxis_tickangle=0  # Убираем наклон, т.к. числа компактны
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 4. Сравнение метрик для модулей
    st.subheader("📊 Сравнение метрик по модулям")
    
    tab1, tab2 = st.tabs(["Успешность и жалобы", "Метрики модулей"])
    
    with tab1:
        # График зависимости успешности и жалоб
        display_success_complaints_chart(df_prog, "module")
    
    with tab2:
        # График сравнения нескольких метрик - используем нумерацию вместо ID
        agg_metrics = df_prog.groupby("module").agg(
            success_rate=("success_rate", "mean"),
            complaint_rate=("complaint_rate", "mean"),
            discrimination_avg=("discrimination_avg", "mean"),
            risk=("risk", "mean")
        ).reset_index()
        
        # Добавляем последовательную нумерацию 
        if "module_order" in df_prog.columns:
            module_order = df_prog.groupby("module")["module_order"].first().reset_index()
            agg_metrics = agg_metrics.merge(module_order, on="module", how="left")
            agg_metrics = agg_metrics.sort_values("module_order")
        else:
            agg_metrics = agg_metrics.sort_values("risk", ascending=False)
        
        agg_metrics = agg_metrics.reset_index(drop=True)
        agg_metrics["module_num"] = agg_metrics.index + 1
        
        # Ограничиваем количество модулей для отображения
        agg_metrics = agg_metrics.head(10)
        
        # Переводим в формат "длинных данных" для графика
        melted_df = pd.melt(
            agg_metrics,
            id_vars=["module", "module_num"],
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
            x="module_num",  # Используем порядковые номера вместо ID
            y="value",
            color="metric_name",
            barmode="group",
            hover_data=["module"],  # Показываем реальное название в подсказке
            labels={
                "module_num": "Номер модуля",
                "value": "Значение",
                "metric_name": "Метрика"
            },
            title="Сравнение ключевых метрик по модулям"
        )
        
        # Настраиваем формат оси Y в зависимости от метрики
        fig_metrics.update_layout(
            yaxis_tickformat=".1%",
            xaxis_tickangle=0  # Убираем наклон, т.к. числа компактны
        )
        
        st.plotly_chart(fig_metrics, use_container_width=True)
    
    # 5. Таблица с модулями
    st.subheader("📋 Детальная информация по модулям")
    
    # Улучшенная таблица с модулями, добавляем номер для соответствия с графиком
    detailed_df = agg[["module_num", "module", "risk", "success", "complaints", "discrimination", "cards"]]
    detailed_df.columns = ["Номер", "Модуль", "Риск", "Успешность", "Жалобы", "Дискриминативность", "Карточек"]
    
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
    
    # 6. Список модулей с кликабельными ссылками
    st.subheader("📚 Список модулей")
    display_clickable_items(df_prog, "module", "module", metrics=["cards", "risk", "success"])
    
    # 7. Если модуль выбран, показываем встроенную страницу уроков
    if st.session_state.get("filter_module"):
        from .lessons import _page_lessons_inline
        
        # Добавляем разделитель
        st.markdown("---")
        _page_lessons_inline(df)
# pages/gz.py с обновленной нумерацией для графиков
"""
Страница группы заданий (Обзор + навигация по карточкам)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

import core
from components.utils import create_hierarchical_header, display_clickable_items, add_gz_links
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart, display_completion_radar

def page_gz(df: pd.DataFrame):
    """Страница группы заданий с детализацией по карточкам"""
    # Фильтруем данные по выбранной программе, модулю, уроку и группе заданий
    df_gz = core.apply_filters(df, ["program", "module", "lesson", "gz"])
    program_filter = st.session_state.get('filter_program')
    module_filter = st.session_state.get('filter_module')
    lesson_filter = st.session_state.get('filter_lesson')
    gz_filter = st.session_state.get('filter_gz')
    
    # Создаем иерархический заголовок
    create_hierarchical_header(
        levels=["program", "module", "lesson", "gz"],
        values=[program_filter, module_filter, lesson_filter, gz_filter]
    )
    
    # Проверка наличия данных после фильтрации
    if df_gz.empty:
        st.warning(f"Нет данных для группы заданий '{gz_filter}' в уроке '{lesson_filter}'")
        return
    
    # Добавляем ссылки на ГЗ
    add_gz_links(df_gz, gz_filter)
    
    # 1. Отображаем общие метрики группы заданий
    st.subheader("📈 Метрики группы заданий")
    display_metrics_row(df_gz, compare_with=df)
    
    # 2. Отображаем распределение риска и статусы
    col1, col2 = st.columns(2)
    
    with col1:
        display_risk_distribution(df_gz)
    
    with col2:
        display_status_chart(df_gz)
    
    # 3. Визуализируем карточки в виде столбчатой диаграммы
    st.subheader("📊 Карточки в группе заданий")
    
    # Добавляем последовательную нумерацию для карточек
    df_cards = df_gz.copy().reset_index(drop=True)
    df_cards["card_num"] = df_cards.index + 1  # Нумерация с 1
    
    # Сортируем по риску для лучшей визуализации
    df_cards = df_cards.sort_values("risk", ascending=False).reset_index(drop=True)
    df_cards["card_num"] = df_cards.index + 1  # Перенумеруем после сортировки
    
    # Создаем столбчатую диаграмму риска по карточкам
    fig = px.bar(
        df_cards,
        x="card_num",  # Используем последовательную нумерацию вместо ID
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={"card_num": "Номер карточки", "risk": "Риск"},
        title="Уровень риска по карточкам",
        hover_data=["card_id", "success_rate", "complaint_rate", "discrimination_avg", "card_type"]  # Показываем реальный ID в подсказке
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
        hovertemplate="<b>ID: %{customdata[0]}</b><br>" +
                      "Номер: %{x}<br>" +
                      "Риск: %{y:.2f}<br>" +
                      "Успешность: %{customdata[1]:.1%}<br>" +
                      "Жалобы: %{customdata[2]:.1%}<br>" +
                      "Дискриминативность: %{customdata[3]:.2f}<br>" +
                      "Тип: %{customdata[4]}"
    )
    
    fig.update_layout(
        xaxis_title="Номер карточки",
        yaxis_title="Риск",
        xaxis_tickangle=0  # Убираем наклон, т.к. числа компактны
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 4. Детальное сравнение карточек
    st.subheader("📊 Детальное сравнение карточек")
    
    # Создаем вкладки для разных представлений
    tabs = st.tabs(["Ключевые метрики", "Успешность и жалобы", "Типы карточек"])
    
    with tabs[0]:
        # График сравнения нескольких метрик для карточек
        fig = px.bar(
            df_cards,
            x="card_num",  # Используем последовательную нумерацию вместо ID
            y=["success_rate", "first_try_success_rate", "complaint_rate"],
            barmode="group",
            hover_data=["card_id", "card_type"],  # Показываем реальный ID в подсказке
            color_discrete_sequence=["#4da6ff", "#ff9040", "#ff6666"],
            labels={
                "card_num": "Номер карточки", 
                "value": "Значение", 
                "variable": "Метрика"
            },
            title="Сравнение ключевых метрик по карточкам"
        )
        
        # Настройки осей
        fig.update_layout(
            xaxis_tickangle=0,  # Убираем наклон, т.к. числа компактны
            yaxis_tickformat=".0%",
            legend_title="Метрика"
        )
        
        # Переименование легенды
        fig.for_each_trace(lambda t: t.update(name = {
            "success_rate": "Успешность",
            "first_try_success_rate": "Успех с 1-й попытки",
            "complaint_rate": "Жалобы"
        }.get(t.name, t.name)))
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tabs[1]:
        # График зависимости успешности и жалоб
        fig = px.scatter(
            df_gz,
            x="success_rate",
            y="complaint_rate",
            color="risk",
            size="total_attempts",
            hover_name="card_id",
            color_continuous_scale="RdYlGn_r",
            labels={
                "success_rate": "Успешность", 
                "complaint_rate": "Процент жалоб",
                "risk": "Риск"
            },
            title="Зависимость успешности и жалоб",
            hover_data={
                "card_id": True,
                "success_rate": ":.1%",
                "complaint_rate": ":.1%",
                "risk": ":.2f",
                "discrimination_avg": ":.2f",
                "card_type": True,
                "total_attempts": True
            }
        )
        
        # Настройки осей
        fig.update_layout(
            xaxis_tickformat=".0%",
            yaxis_tickformat=".1%"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tabs[2]:
        # Если есть разные типы карточек, показываем их распределение
        if "card_type" in df_gz.columns and len(df_gz["card_type"].unique()) > 1:
            # Группируем по типу карточки
            card_type_stats = df_gz.groupby("card_type").agg(
                count=("card_id", "count"),
                risk=("risk", "mean"),
                success=("success_rate", "mean"),
                complaints=("complaint_rate", "mean")
            ).reset_index()
            
            # Создаем столбчатую диаграмму для типов карточек
            fig = px.bar(
                card_type_stats,
                x="card_type",
                y="count",
                color="risk",
                color_continuous_scale="RdYlGn_r",
                labels={
                    "card_type": "Тип карточки", 
                    "count": "Количество", 
                    "risk": "Риск"
                },
                title="Распределение карточек по типам",
                hover_data=["success", "complaints"]
            )
            
            # Форматируем подсказки
            fig.update_traces(
                hovertemplate="<b>%{x}</b><br>" +
                              "Количество: %{y}<br>" +
                              "Средний риск: %{marker.color:.2f}<br>" +
                              "Успешность: %{customdata[0]:.1%}<br>" +
                              "Жалобы: %{customdata[1]:.1%}"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("В этой группе заданий все карточки одного типа.")
    
    # 5. Таблица с карточками
    st.subheader("📋 Детальная информация по карточкам")
    
    # Отображаем таблицу
    cards_df = df_gz[["card_id", "card_type", "status", "success_rate", 
                      "first_try_success_rate", "complaint_rate", 
                      "discrimination_avg", "total_attempts", "risk"]]
    
    # Добавляем номер в таблицу для соответствия с графиками
    cards_df = cards_df.sort_values("risk", ascending=False).reset_index(drop=True)
    cards_df["Номер"] = cards_df.index + 1
    
    # Переорганизуем колонки, чтобы номер был в начале
    cards_df = cards_df[["Номер", "card_id", "card_type", "status", "success_rate", 
                         "first_try_success_rate", "complaint_rate", 
                         "discrimination_avg", "total_attempts", "risk"]]
    
    # Создаем кликабельные ссылки на карточки, если доступны URL
    if "card_url" in df_gz.columns:
        cards_df_display = cards_df.copy()
        cards_df_display["Карточка"] = df_gz.apply(
            lambda row: f"[ID:{int(row['card_id'])}]({row['card_url']})" if pd.notna(row['card_url']) else f"ID:{int(row['card_id'])}", 
            axis=1
        )
        
        # Создаем DataFrame для отображения с более понятными названиями колонок
        formatted_df = pd.DataFrame({
            "Номер": cards_df_display["Номер"],
            "Карточка": cards_df_display["Карточка"],
            "Тип": cards_df_display["card_type"],
            "Статус": cards_df_display["status"],
            "Успешность": cards_df_display["success_rate"].apply(lambda x: f"{x:.1%}"),
            "Успех 1-й": cards_df_display["first_try_success_rate"].apply(lambda x: f"{x:.1%}"),
            "Жалобы": cards_df_display["complaint_rate"].apply(lambda x: f"{x:.1%}"),
            "Дискр.": cards_df_display["discrimination_avg"].apply(lambda x: f"{x:.2f}"),
            "Попытки": cards_df_display["total_attempts"].apply(lambda x: f"{int(x)}"),
            "Риск": cards_df_display["risk"].apply(lambda x: f"{x:.2f}")
        })
        
        # Отображаем с кликабельными ссылками
        st.dataframe(formatted_df, hide_index=True, use_container_width=True)
    else:
        # Форматируем таблицу
        formatted_cards = cards_df.style.format({
            "success_rate": "{:.1%}",
            "first_try_success_rate": "{:.1%}",
            "complaint_rate": "{:.1%}",
            "discrimination_avg": "{:.2f}",
            "risk": "{:.2f}"
        }).background_gradient(
            subset=["risk"],
            cmap="RdYlGn_r"
        )
        
        st.dataframe(formatted_cards, use_container_width=True)
    
    # 6. Список карточек с кликабельными ссылками
    st.subheader("🗂️ Карточки группы заданий")
    
    # Отображаем карточки с прямыми ссылками, если доступны URL
    if "card_url" in df_gz.columns:
        st.subheader("Ссылки на карточки")
        
        # Создаем ссылки на карточки
        card_links = []
        for _, card in df_gz.iterrows():
            if pd.notna(card['card_url']):
                card_links.append({
                    "id": int(card['card_id']),
                    "type": card['card_type'],
                    "risk": card['risk'],
                    "url": card['card_url']
                })
        
        # Отображаем в несколько колонок
        if card_links:
            columns = st.columns(3)
            links_per_col = (len(card_links) + 2) // 3  # Распределяем равномерно
            
            for i, column in enumerate(columns):
                with column:
                    start_idx = i * links_per_col
                    end_idx = min((i + 1) * links_per_col, len(card_links))
                    
                    for link in card_links[start_idx:end_idx]:
                        risk_color = "red" if link["risk"] > 0.7 else ("orange" if link["risk"] > 0.5 else ("yellow" if link["risk"] > 0.3 else "green"))
                        st.markdown(f"[ID: {link['id']} ({link['type']})]({link['url']}) <span style='color:{risk_color};'>■</span>", unsafe_allow_html=True)
    
    # Если нет URL, показываем просто список карточек
    else:
        display_clickable_items(df_gz, "card_id", "card_id", metrics=["risk"])

def _page_gz_inline(df: pd.DataFrame):
    """Встроенная версия страницы групп заданий для отображения на странице урока"""
    # Фильтруем данные по выбранной программе, модулю и уроку
    df_lesson = core.apply_filters(df, ["program", "module", "lesson"])
    
    # Проверка наличия данных после фильтрации
    if df_lesson.empty:
        lesson_name = st.session_state.get('filter_lesson') or '—'
        st.warning(f"Нет данных для урока '{lesson_name}'")
        return
    
    # Заголовок
    st.subheader("🧩 Группы заданий выбранного урока")
    
    # Агрегируем данные по группам заданий
    agg = df_lesson.groupby("gz").agg(
        risk=("risk", "mean"),
        success=("success_rate", "mean"),
        complaints=("complaint_rate", "mean"),
        cards=("card_id", "nunique")
    ).reset_index()
    
    # Добавляем нумерацию для групп заданий
    agg = agg.sort_values("risk", ascending=False).reset_index(drop=True)
    agg["gz_num"] = agg.index + 1
    
    # Создаем график
    fig = px.bar(
        agg,
        x="gz_num",  # Используем последовательную нумерацию
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={"gz_num": "Номер группы заданий", "risk": "Риск"},
        title="Уровень риска по группам заданий",
        hover_data=["gz", "success", "complaints", "cards"]  # Показываем реальный ID в подсказке
    )
    
    # Форматируем подсказки
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                      "Номер: %{x}<br>" +
                      "Риск: %{y:.2f}<br>" +
                      "Успешность: %{customdata[1]:.1%}<br>" +
                      "Жалобы: %{customdata[2]:.1%}<br>" +
                      "Карточек: %{customdata[3]}"
    )
    
    fig.update_layout(
        xaxis_tickangle=0  # Убираем наклон, т.к. числа компактны
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Таблица с группами заданий, добавляем номер для соответствия с графиком
    table_df = agg[["gz_num", "gz", "risk", "success", "complaints", "cards"]]
    table_df.columns = ["Номер", "Группа заданий", "Риск", "Успешность", "Жалобы", "Карточек"]
    
    st.dataframe(
        table_df.style.format({
            "Риск": "{:.2f}",
            "Успешность": "{:.1%}",
            "Жалобы": "{:.1%}"
        }),
        use_container_width=True
    )
    
    # Список кликабельных групп заданий
    display_clickable_items(df_lesson, "gz", "gz", metrics=["cards", "risk"])
# pages/gz.py
"""
Страница группы заданий (Обзор + навигация по карточкам)
Включает функциональность анализа карточек из прежней страницы cards.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import urllib.parse as ul
import io
import zipfile
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import math

import core
from components.utils import create_hierarchical_header, display_clickable_items, add_gz_links
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_cards_chart, display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart, display_completion_radar, display_trickiness_chart, display_trickiness_success_chart
import navigation_utils

def page_gz(df_cards_input: pd.DataFrame, eng, create_link_fn=None):
    """Страница группы заданий с детализацией по карточкам"""
    prog_name = st.session_state.get('filter_program')
    module_name = st.session_state.get('filter_module')
    lesson_name = st.session_state.get('filter_lesson')
    gz_name = st.session_state.get('filter_gz')

    # ОПРЕДЕЛЯЕМ КАРТЫ ЦВЕТОВ И ИКОНОК ОДИН РАЗ В НАЧАЛЕ ФУНКЦИИ
    status_color_map_gz = {
        "new": "blue", "in_work": "orange", "review": "purple",
        "ready_for_qc": "violet", "done": "green", "wont_fix": "red", "archive": "grey"
    }
    status_icon_map_gz = {
        "new": ":material/fiber_new:", "in_work": ":material/construction:", "review": ":material/rate_review:",
        "ready_for_qc": ":material/checklist:", "done": ":material/check_circle:",
        "wont_fix": ":material/cancel:", "archive": ":material/archive:"
    }

    # Фильтрация df_cards_input до любых операций с ним, чтобы df_gz был актуальным
    # (Предполагается, что df_cards_input уже загружен и может содержать карточки из разных ГЗ)
    if df_cards_input is not None and not df_cards_input.empty and gz_name:
        df_gz_current = df_cards_input[
            (df_cards_input.get("program_name") == prog_name) &
            (df_cards_input.get("module_name") == module_name) &
            (df_cards_input.get("lesson_name") == lesson_name) &
            (df_cards_input.get("gz_name") == gz_name)
        ].copy() # Используем .get для безопасности, если колонки могут отсутствовать
    else:
        df_gz_current = pd.DataFrame() # Пустой DataFrame, если входные данные некорректны

    # Отображение УНИКАЛЬНЫХ статусов карточек в текущей ГЗ (В САМОМ ВЕРХУ)
    if not df_gz_current.empty and "status" in df_gz_current.columns:
        unique_statuses = df_gz_current["status"].dropna().unique()
        unique_statuses.sort() # Для консистентного порядка
        
        if len(unique_statuses) > 0:
            # Карты для отображения статусов - теперь используются глобальные для функции
            badge_html_list_top = []
            for status_val in unique_statuses:
                color = status_color_map_gz.get(status_val, "grey") # Используем общую карту
                # Только текст статуса, без иконок и доп. слов
                badge_html_list_top.append(f"<span style='display:inline-block; background-color:{color}; color:white; padding:0.2em 0.6em; border-radius:0.7em; font-weight:bold; font-size:0.9em; margin-right:5px; margin-bottom:5px;'>{status_val.capitalize()}</span>")
            st.markdown(" ".join(badge_html_list_top), unsafe_allow_html=True)
            st.markdown("<hr style='margin-top: 5px; margin-bottom: 10px;'>", unsafe_allow_html=True) # Горизонтальная линия для отделения

    if not prog_name or not module_name or not lesson_name or not gz_name:
        st.warning("Фильтры программы, модуля, урока или ГЗ не установлены.")
        return

    if df_cards_input is None or df_cards_input.empty:
        st.warning("Нет данных о карточках для отображения.")
        return

    # df_cards_input - это результат core.load_card_data, который уже должен быть отфильтрован
    # по program, module, lesson, gz (если gz передавался как gz_name)
    # Убедимся, что в df_cards_input есть нужные колонки для проверки фильтров
    # и что данные действительно соответствуют текущим фильтрам.
    # Колонки типа program_name, module_name и т.д. должны приходить из cards_structure через JOIN в load_card_data
    
    # Проверяем, есть ли необходимые колонки для фильтрации в df_cards_input
    required_filter_cols = ["program_name", "module_name", "lesson_name", "gz_name"]
    if not all(col in df_cards_input.columns for col in required_filter_cols):
        missing_cols = [col for col in required_filter_cols if col not in df_cards_input.columns]
        st.error(f"Входные данные для страницы ГЗ не содержат необходимых колонок для проверки фильтров: {missing_cols}. Доступные: {df_cards_input.columns.tolist()}")
        return

    df_gz = df_gz_current # Используем уже отфильтрованный DataFrame
    
    if df_gz.empty:
        st.warning(f"Нет данных для ГЗ '{gz_name}' в уроке '{lesson_name}', модуль '{module_name}', программа '{prog_name}'. Проверьте, что данные были корректно загружены для этого уровня.")
        return
    
    # Создаем иерархический заголовок с кликабельными ссылками
    create_hierarchical_header(
        levels=["program", "module", "lesson", "gz"],
        values=[prog_name, module_name, lesson_name, gz_name]
    )

    # 1. Метрики группы заданий
    st.subheader("📈 Метрики группы заданий")
    display_metrics_row(df_gz)
    
    # Добавляем метрику суммарного времени на ГЗ
    if "time_median" in df_gz.columns and not df_gz.empty:
        total_time = df_gz["time_median"].sum() / 60
        st.subheader("⏱️ Суммарное время на ГЗ")
        st.metric(
            label="Суммарное время на группу заданий (мин)",
            value=f"{total_time:.1f}"
        )
    else:
        st.info("Данные о времени выполнения карточек (time_median) отсутствуют.")
    
    # 2. Отображаем распределение риска и статусы
    col1, col2 = st.columns(2)
    
    with col1:
        display_risk_distribution(df_gz)
    
    with col2:
        if "status" in df_gz.columns:
            display_status_chart(df_gz)
        else:
            st.info("Данные о статусах карточек отсутствуют.")
    
    # 3. Подготовка данных для визуализации
    st.subheader("📊 Карточки в группе заданий")
    
    # Проверяем наличие колонки trickiness_level, если нет, вычисляем (если core.get_trickiness_level доступна)
    if "trickiness_level" not in df_gz.columns and hasattr(core, 'get_trickiness_level'):
        # Эта операция может быть долгой, если core.get_trickiness_level не векторизована и применяется к большому df_gz
        # Возможно, это поле должно приходить уже рассчитанным из core.load_card_data
        st.warning("Вычисляем trickiness_level... Это может занять некоторое время.")
        df_gz["trickiness_level"] = df_gz.apply(core.get_trickiness_level, axis=1)
    elif "trickiness_level" not in df_gz.columns:
        df_gz["trickiness_level"] = 0 # Значение по умолчанию, если рассчитать нельзя
        
    # Добавляем разницу между общей успешностью и успехом с первой попытки, если есть обе колонки
    if "success_rate" in df_gz.columns and "first_try_success_rate" in df_gz.columns:
        df_gz["success_diff"] = df_gz["success_rate"] - df_gz["first_try_success_rate"]
    else:
        df_gz["success_diff"] = 0.0
    
    df_cards = df_gz.copy()
    
    # Обработка card_order
    if "card_order" in df_cards.columns:
        # Убедимся, что card_order это число
        df_cards["card_order"] = pd.to_numeric(df_cards["card_order"], errors='coerce')
        # Заполним пропущенные значения
        if df_cards["card_order"].isna().any():
            # Если card_order отсутствует или NULL, используем порядковый номер строки + 1
            df_cards.loc[df_cards["card_order"].isna(), "card_order"] = df_cards.index[df_cards["card_order"].isna()] + 1
    else:
        # Если колонки нет в данных, создаем её на основе порядкового номера в группе заданий
        df_cards["card_order"] = range(1, len(df_cards) + 1)
    
    # Преобразуем card_order в целые числа для корректного отображения
    df_cards["card_order"] = df_cards["card_order"].astype(int)
    
    # Сортируем данные по номеру карточки
    df_cards = df_cards.sort_values("card_order").reset_index(drop=True)
    
    # Получаем СВЕЖИЕ СТАТУСЫ для всех карточек в текущей ГЗ
    if not df_cards.empty and "card_id" in df_cards.columns:
        list_of_card_ids = df_cards["card_id"].dropna().unique().tolist()
        print(f"[DEBUG page_gz] list_of_card_ids to fetch statuses for: {list_of_card_ids}")
        if list_of_card_ids:
            try:
                print(f"[page_gz] Attempting to fetch fresh statuses for {len(list_of_card_ids)} cards using provided engine.")
                df_fresh_statuses_gz = core.get_fresh_card_statuses(eng, list_of_card_ids) # Используем переданный eng

                if not df_fresh_statuses_gz.empty:
                    status_map = pd.Series(df_fresh_statuses_gz.status.values, index=df_fresh_statuses_gz.card_id).to_dict()
                    # Обновляем столбец 'status' в df_cards, сохраняя существующие значения, если свежий статус не найден
                    # И обрабатываем NaN/None изначальные статусы
                    def update_status(row):
                        fresh_status = status_map.get(row['card_id'])
                        if fresh_status is not None and not pd.isna(fresh_status):
                            return fresh_status
                        elif pd.isna(row['status']): # Если старый статус был NaN/None и свежего нет
                            return 'unknown'
                        return row['status'] # Возвращаем старый, если он не NaN/None и свежего нет
                    
                    df_cards['status'] = df_cards.apply(update_status, axis=1)
                    print(f"[page_gz] Fresh statuses applied to df_cards.")
                else:
                    print(f"[page_gz] No fresh statuses returned for card_ids: {list_of_card_ids}. Ensuring NaN statuses are 'unknown'.")
                    df_cards['status'] = df_cards['status'].apply(lambda x: 'unknown' if pd.isna(x) else str(x))
            except Exception as e_gz_status:
                st.error(f"Ошибка при получении свежих статусов для ГЗ: {e_gz_status}")
                print(f"[page_gz] Exception when fetching/applying fresh statuses: {e_gz_status}")
                df_cards['status'] = df_cards['status'].apply(lambda x: 'unknown' if pd.isna(x) else str(x))
        else: # Если нет list_of_card_ids (например, все card_id были NaN)
            print("[page_gz] No valid card_ids to fetch fresh statuses. Ensuring NaN statuses are 'unknown'.")
            if "status" in df_cards.columns:
                df_cards['status'] = df_cards['status'].apply(lambda x: 'unknown' if pd.isna(x) else str(x))
            else:
                df_cards['status'] = 'unknown'
    elif "status" in df_cards.columns: # Если нет card_id в df_cards, но есть столбец status
        df_cards['status'] = df_cards['status'].apply(lambda x: 'unknown' if pd.isna(x) else str(x))
    else: # Если нет ни card_id, ни status
        df_cards['status'] = 'unknown'

    # Создаем столбчатую диаграмму риска по карточкам напрямую через Plotly
    st.subheader("📊 Уровень риска по карточкам")
    
    # Создаем график с помощью Plotly Express
    fig = px.bar(
        df_cards,
        x="card_order",
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={
            "card_order": "Номер карточки", 
            "risk": "Риск"
        },
        title="Уровень риска по карточкам",
        hover_data=["card_id", "card_type", "card_order"]
    )
    
    # Форматируем подсказки
    fig.update_traces(
        hovertemplate="<b>ID: %{customdata[0]}</b><br>" +
                      "Номер: %{customdata[2]}<br>" +
                      "Тип: %{customdata[1]}<br>" +
                      "Риск: %{y:.2f}"
    )
    
    # Настраиваем оси X - фиксируем порядок и значения
    fig.update_layout(
        xaxis=dict(
            title="Номер карточки",
            tickmode='array',
            tickvals=df_cards["card_order"],
            ticktext=df_cards["card_order"],
            tickangle=0,
            categoryorder='array',
            categoryarray=df_cards["card_order"].tolist()
        ),
        yaxis_title="Уровень риска",
        hoverlabel=dict(
            bgcolor="white",
            font_size=12
        )
    )
    
    # Отображаем график
    st.plotly_chart(fig, use_container_width=True)
    
    # 4. Детальное сравнение карточек (используя компоненты из прежней страницы cards)
    st.subheader("📊 Детальное сравнение карточек")
    
    # Создаем вкладки для разных представлений
    tabs = st.tabs([
        "Ключевые метрики", 
        "Успешность и жалобы", 
        "Типы карточек", 
        "Трики-карточки",
        "Дискриминативность"
    ])
    
    with tabs[0]:
        # График сравнения нескольких метрик для карточек
        # Создаем график с несколькими метриками напрямую через Plotly
        fig = go.Figure()
        
        # Определяем цвета для метрик
        color_map = {
            "success_rate": "#4da6ff",
            "first_try_success_rate": "#ff9040",
            "complaint_rate": "#ff6666"
        }
        
        # Названия метрик
        metric_labels = {
            "success_rate": "Успешность",
            "first_try_success_rate": "Успех с 1-й попытки",
            "complaint_rate": "Жалобы"
        }
        
        # Метрики для отображения
        metrics = ["success_rate", "first_try_success_rate", "complaint_rate"]
        
        # Добавляем столбцы для каждой метрики
        for i, col in enumerate(metrics):
            # Определяем формат значений
            hover_format = ":.1%" if col in ["success_rate", "first_try_success_rate", "complaint_rate"] else ":.2f"
            
            # Создаем текст подсказки
            hovertemplate = (
                f"<b>ID: {{customdata[0]}}</b><br>" +
                f"Номер: {{customdata[2]}}<br>" +
                f"Тип: {{customdata[1]}}<br>" +
                f"{metric_labels[col]}: {{{{'y{hover_format}'}}}}"
            )
            
            fig.add_trace(go.Bar(
                x=df_cards["card_order"],
                y=df_cards[col],
                name=metric_labels[col],
                marker_color=color_map[col],
                customdata=df_cards[["card_id", "card_type", "card_order"]],
                hovertemplate=hovertemplate
            ))
        
        # Настройка группировки столбцов
        fig.update_layout(
            barmode="group",
            title="Сравнение ключевых метрик по карточкам",
            xaxis=dict(
                title="Номер карточки",
                tickmode='array',
                tickvals=df_cards["card_order"],
                ticktext=df_cards["card_order"],
                tickangle=0,
                categoryorder='array',
                categoryarray=df_cards["card_order"].tolist()
            ),
            yaxis=dict(
                title="Значение",
                tickformat=".0%"
            ),
            hoverlabel=dict(
                bgcolor="white",
                font_size=12
            ),
            legend_title="Метрики"
        )
        
        # Отображаем график
        st.plotly_chart(fig, use_container_width=True)
    
    with tabs[1]:
        # График зависимости успешности и жалоб
        # Заменяем NaN в total_attempts на 0 для параметра size
        scatter_df = df_cards.copy()
        scatter_df['total_attempts'] = scatter_df['total_attempts'].fillna(0)
        
        fig = px.scatter(
            scatter_df,
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
                "total_attempts": True,
                "card_order": True
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
            
            # Сравнение метрик по типам карточек
            fig2 = px.bar(
                card_type_stats,
                x="card_type",
                y=["success", "complaints", "risk"],
                barmode="group",
                labels={
                    "card_type": "Тип карточки",
                    "value": "Значение",
                    "variable": "Метрика"
                },
                title="Сравнение метрик по типам карточек",
                color_discrete_sequence=["#4da6ff", "#ff6666", "#ff7f7f"]
            )
            
            # Переименование легенды
            fig2.for_each_trace(lambda t: t.update(name = {
                "success": "Успешность",
                "complaints": "Жалобы",
                "risk": "Риск"
            }.get(t.name, t.name)))
            
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("В этой группе заданий все карточки одного типа.")
    
    with tabs[3]:
        # Анализ трики-карточек
        st.markdown("### Анализ \"трики\"-карточек")
        
        # Подсчитываем количество трики-карточек
        tricky_count = (df_gz["trickiness_level"] > 0).sum()
        
        if tricky_count > 0:
            # Отображаем распределение трики-карточек по уровням
            tricky_levels = df_gz["trickiness_level"].value_counts().sort_index()
            
            # Создаем DataFrame для отображения статистики
            tricky_df = pd.DataFrame({
                "Уровень": ["Нет подлости", "Низкий", "Средний", "Высокий"],
                "Количество": [
                    tricky_levels.get(0, 0),
                    tricky_levels.get(1, 0),
                    tricky_levels.get(2, 0),
                    tricky_levels.get(3, 0)
                ]
            })
            
            # Показываем статистику
            col1, col2 = st.columns(2)
            
            with col1:
                # Показываем общую статистику
                st.metric("Трики-карточек", tricky_count, f"{tricky_count/len(df_gz):.1%} от всех карточек")
                
                # Показываем распределение по уровням
                st.markdown("#### Распределение по уровням подлости")
                for i, row in tricky_df.iterrows():
                    if i == 0:  # Пропускаем "Нет подлости"
                        continue
                    
                    level = row["Уровень"]
                    count = row["Количество"]
                    percent = count / len(df_gz) * 100
                    
                    # Выбираем цвет в зависимости от уровня
                    color = "yellow"
                    if level == "Средний":
                        color = "orange"
                    elif level == "Высокий":
                        color = "red"
                    
                    st.markdown(f"**{level}**: <span style='color:{color};'>{count}</span> ({percent:.1f}%)", unsafe_allow_html=True)
            
            with col2:
                # Создаем круговую диаграмму для распределения трики-карточек
                fig = px.pie(
                    tricky_df[tricky_df["Количество"] > 0],
                    values="Количество",
                    names="Уровень",
                    title="Распределение по уровням подлости",
                    color="Уровень",
                    color_discrete_map={
                        "Нет подлости": "#c0c0c0",
                        "Низкий": "#ffff7f",
                        "Средний": "#ffaa7f",
                        "Высокий": "#ff7f7f"
                    }
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Отображаем график подлости карточек с использованием card_order
            display_trickiness_chart(df_gz, x_col="card_order", limit=50, title="Уровень подлости карточек")
            
            # Отображаем диаграмму рассеяния для трики-карточек
            display_trickiness_success_chart(df_gz, limit=50)
            
            # Отображаем таблицу с трики-карточками
            tricky_cards = df_cards[df_cards["trickiness_level"] > 0].sort_values("card_order")
            
            if not tricky_cards.empty:
                st.markdown("#### Список трики-карточек")
                
                # Создаем таблицу с данными трики-карточек
                tricky_table = tricky_cards[["card_id", "card_type", "success_rate", "first_try_success_rate", "success_diff", "risk", "trickiness_level", "card_order"]]
                
                # Добавляем колонку с уровнем подлости
                tricky_table["Уровень подлости"] = tricky_table["trickiness_level"].map({
                    1: "Низкий",
                    2: "Средний",
                    3: "Высокий"
                })
                
                # Переименовываем и форматируем столбцы для отображения
                display_df = pd.DataFrame()
                display_df["ID карточки"] = tricky_table["card_id"]
                display_df["Тип"] = tricky_table["card_type"]
                display_df["Номер"] = tricky_table["card_order"]
                display_df["Успешность"] = tricky_table["success_rate"].apply(lambda x: f"{x:.1%}")
                display_df["Успех с 1-й"] = tricky_table["first_try_success_rate"].apply(lambda x: f"{x:.1%}")
                display_df["Разница"] = tricky_table["success_diff"].apply(lambda x: f"{x:.1%}")
                display_df["Уровень подлости"] = tricky_table["Уровень подлости"]
                display_df["Риск"] = tricky_table["risk"].apply(lambda x: f"{x:.2f}")
                
                # Отображаем таблицу
                st.dataframe(display_df, hide_index=True, use_container_width=True)
                # Кнопки для перехода к детальному анализу трики-карточек
                # Удаляем дубликаты по card_id перед генерацией кнопок
                unique_tricky_cards_for_buttons = tricky_cards.drop_duplicates(subset=['card_id'], keep='first')
                for _, row in unique_tricky_cards_for_buttons.iterrows():
                    card_id = int(row["card_id"])
                    if st.button(f"Перейти к карточке {card_id}", key=f"gz_tricky_nav_{card_id}"):
                        # Навигация без сброса сессии
                        if hasattr(st, 'navigate_to_app'):
                            st.navigate_to_app("Карточки", card_id=str(card_id))
                        else:
                            st.query_params.clear()
                            st.query_params["page"] = "cards"
                            st.query_params["card_id"] = str(card_id)
                        st.rerun()
        else:
            st.info("В этой группе заданий нет трики-карточек.")
    
    with tabs[4]:
        # Анализ дискриминативности карточек
        st.markdown("### Анализ дискриминативности карточек")
        
        # Создаем график дискриминативности используя card_order
        fig = px.bar(
            df_cards,
            x="card_order",
            y="discrimination_avg",
            color="success_rate",
            color_continuous_scale="RdYlGn",
            title="Индекс дискриминативности по карточкам",
            labels={"card_order": "Номер карточки", "discrimination_avg": "Дискриминативность"},
            hover_data=["card_id", "card_type", "card_order"]
        )
        
        # Добавляем горизонтальные линии для границ категорий
        fig.add_hline(y=0.35, line_dash="dash", line_color="green", 
                      annotation_text="Хорошая", annotation_position="left")
        fig.add_hline(y=0.15, line_dash="dash", line_color="red", 
                      annotation_text="Низкая", annotation_position="left")
        
        # Форматируем подсказки
        fig.update_traces(
            hovertemplate="<b>ID: %{customdata[0]}</b><br>" +
                          "Номер: %{customdata[2]}<br>" +
                          "Тип: %{customdata[1]}<br>" +
                          "Дискриминативность: %{y:.3f}<br>" +
                          "Успешность: %{marker.color:.1%}"
        )
        
        # Настраиваем оси X - показываем номера карточек
        fig.update_layout(
            xaxis=dict(
                title="Номер карточки",
                tickmode='array',
                tickvals=df_cards["card_order"],
                ticktext=df_cards["card_order"],
                tickangle=0,
                categoryorder='array',
                categoryarray=df_cards["card_order"].tolist()
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Распределение по категориям дискриминативности
        good_discr = (df_gz["discrimination_avg"] >= 0.35).sum()
        medium_discr = ((df_gz["discrimination_avg"] < 0.35) & (df_gz["discrimination_avg"] >= 0.15)).sum()
        low_discr = (df_gz["discrimination_avg"] < 0.15).sum()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Хорошая дискр. (>0.35)", good_discr, f"{good_discr/len(df_gz):.1%}")
        
        with col2:
            st.metric("Средняя дискр. (0.15-0.35)", medium_discr, f"{medium_discr/len(df_gz):.1%}")
        
        with col3:
            st.metric("Низкая дискр. (<0.15)", low_discr, f"{low_discr/len(df_gz):.1%}")
        
        # Показываем карточки с низкой дискриминативностью
        if low_discr > 0:
            st.markdown("#### Карточки с низкой дискриминативностью")
            low_discr_cards = df_cards[df_cards["discrimination_avg"] < 0.15].sort_values("card_order")
            
            # Создаем таблицу
            display_df = pd.DataFrame()
            display_df["ID карточки"] = low_discr_cards["card_id"]
            display_df["Тип"] = low_discr_cards["card_type"]
            display_df["Номер"] = low_discr_cards["card_order"]
            display_df["Дискриминативность"] = low_discr_cards["discrimination_avg"].apply(lambda x: f"{x:.3f}")
            display_df["Успешность"] = low_discr_cards["success_rate"].apply(lambda x: f"{x:.1%}")
            display_df["Риск"] = low_discr_cards["risk"].apply(lambda x: f"{x:.2f}")
            
            # Отображаем таблицу
            st.dataframe(display_df, hide_index=True, use_container_width=True)
            # Кнопки для перехода к детальному анализу карточек
            # Удаляем дубликаты по card_id перед генерацией кнопок
            unique_low_discr_cards_for_buttons_list = low_discr_cards.drop_duplicates(subset=['card_id'], keep='first')
            
            # DEBUG: Вывод содержимого unique_low_discr_cards_for_buttons_list
            st.write("DEBUG unique_low_discr_cards_for_buttons_list (вкладка Дискриминативность):", unique_low_discr_cards_for_buttons_list[['card_id', 'card_order', 'discrimination_avg', 'card_type']])
            st.write(f"Дубликаты card_id: {unique_low_discr_cards_for_buttons_list.duplicated(subset=['card_id']).sum()}")
            st.write(f"Записи для card_id 259085: {unique_low_discr_cards_for_buttons_list[unique_low_discr_cards_for_buttons_list['card_id'] == 259085]}")

            if not unique_low_discr_cards_for_buttons_list.empty:
                for _, card in unique_low_discr_cards_for_buttons_list.iterrows():
                    card_id = int(card["card_id"])
                    discr = card["discrimination_avg"]
                    card_order = int(card["card_order"])
                    color = "purple"
                    key = f"gz_lowdiscr_nav_list_{card_id}"
                    if st.button(f"№{card_order}: ID {card_id} - Дискр.: {discr:.2f} - {card['card_type']}", key=key):
                        if hasattr(st, 'navigate_to_app'):
                            st.navigate_to_app("Карточки", card_id=str(card_id))
                        else:
                            st.query_params.clear()
                            st.query_params["page"] = "cards"
                            st.query_params["card_id"] = str(card_id)
                        st.rerun()
                if len(unique_low_discr_cards_for_buttons_list) > 12:
                    st.info(f"И еще {len(unique_low_discr_cards_for_buttons_list) - 12} карточек...")
    
    # 5. Таблица с карточками и ссылками на карточки
    st.subheader("📋 Детальная информация по карточкам")
    
    # Колонки для извлечения из df_cards
    cols_to_extract = ["card_id", "card_type", "status", "success_rate", 
                       "first_try_success_rate", "complaint_rate", 
                       "discrimination_avg", "total_attempts", "risk", 
                       "trickiness_level", "card_order"]
    if "complaints_total" in df_cards.columns:
        cols_to_extract.append("complaints_total")
        
    cards_df = df_cards[cols_to_extract]
    
    # Сортируем по порядку карточек
    cards_df = cards_df.sort_values("card_order").reset_index(drop=True)
    
    # Переорганизуем колонки, чтобы номер был в начале
    # Сначала обязательные колонки
    ordered_cols = ["card_order", "card_id", "card_type", "status", "success_rate", 
                    "first_try_success_rate", "complaint_rate"]
    # Добавляем complaints_total если есть
    if "complaints_total" in cards_df.columns:
        ordered_cols.append("complaints_total")
    # Добавляем остальные
    ordered_cols.extend(["discrimination_avg", "total_attempts", "risk", "trickiness_level"])
    
    # Фильтруем ordered_cols, чтобы оставить только те, что реально есть в cards_df
    # Это важно, так как 'complaints_total' может отсутствовать в df_cards и, соответственно, в cards_df
    final_cols = [col for col in ordered_cols if col in cards_df.columns]
    cards_df = cards_df[final_cols]
    
    # Создаем таблицу с данными для отображения
    display_df = pd.DataFrame()
    display_df["Номер"] = cards_df["card_order"]
    display_df["ID карточки"] = cards_df["card_id"]
    display_df["Тип"] = cards_df["card_type"]
    # display_df["Статус"] = cards_df["status"] # Заменим на HTML badge

    def create_status_badge(status):
        if pd.isna(status):
            status = "unknown"
        color = status_color_map_gz.get(status, "grey")
        icon = status_icon_map_gz.get(status, ":material/help:")
        # Важно: st.dataframe не рендерит markdown или HTML напрямую.
        # Поэтому просто вернем текстовый статус, а бейджи отобразим отдельно.
        # Либо, если нужно именно в таблице, придется использовать st.markdown для всей таблицы построчно.
        # Для простоты пока вернем текстовый статус, а ниже рассмотрим вывод бейджей.
        # Возвращаем сам статус для таблицы, а бейджи сделаем ниже или в другом месте.
        # return f"<span style='display:inline-flex; align-items:center; gap:0.3em; background-color:{color}; color:white; padding:0.1em 0.5em; border-radius:0.5em; font-weight:bold; font-size:0.85em;'>{icon} {status.capitalize()}</span>"
        return status # Пока оставляем текстовый статус для st.dataframe

    display_df["Статус"] = cards_df["status"].apply(create_status_badge)
    display_df["Успешность"] = cards_df["success_rate"].apply(lambda x: f"{x:.1%}" if pd.notnull(x) else "N/A")
    display_df["Успех с 1-й"] = cards_df["first_try_success_rate"].apply(lambda x: f"{x:.1%}" if pd.notnull(x) else "N/A")
    display_df["Жалобы (%)"] = cards_df["complaint_rate"].apply(lambda x: f"{x:.1%}" if pd.notnull(x) else "N/A")
    
    if "complaints_total" in cards_df.columns:
        display_df["Общее кол-во жалоб"] = cards_df["complaints_total"].fillna(0).astype(int).astype(str)
    else:
        # Если колонки complaints_total нет, можно либо не добавлять столбец, либо добавить с N/A
        display_df["Общее кол-во жалоб"] = "N/A" 
        
    display_df["Дискр."] = cards_df["discrimination_avg"].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A")
    # Заменяем NaN на 0 и форматируем как целое число в строку
    display_df["Попытки"] = cards_df["total_attempts"].fillna(0).astype(int).astype(str)
    display_df["Риск"] = cards_df["risk"].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A")
    
    # Добавляем категорию подлости
    trickiness_categories = {
        0: "Нет",
        1: "Низкий",
        2: "Средний",
        3: "Высокий"
    }
    display_df["Подлость"] = cards_df["trickiness_level"].map(trickiness_categories)
    
    # Отображаем таблицу
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    # 6. Кнопки для быстрого перехода ко всем карточкам, сортированные по card_order
    st.subheader("🔍 Все карточки в группе заданий")

    for _, card in df_cards.sort_values("card_order").iterrows():
        card_id = int(card["card_id"])
        risk = card["risk"]
        card_type = card["card_type"]
        card_order = int(card["card_order"])
        current_card_status = card.get("status", "unknown")
        if pd.isna(current_card_status):
            current_card_status = "unknown"
        else:
            current_card_status = str(current_card_status)
        
        status_color = status_color_map_gz.get(current_card_status, "#808080") # Цвет по умолчанию (серый)
        status_text = current_card_status.capitalize()
        
        # HTML для компактного бейджа
        # Стили подбираем для компактности и выравнивания
        badge_html = f"""<span style="
            background-color: {status_color};
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            margin-right: 4px;
            display: inline-block;
            vertical-align: middle;
            line-height: 1.2;
        ">{status_text}</span>"""
        
        button_label_text = f"№{card_order}: ID {card_id} - Риск: {risk:.2f} - {card_type}"
        # Всплывающая подсказка для кнопки может теперь содержать и статус, если нужно, или только доп. инфо
        button_help = f"Карточка №{card_order}, ID {card_id}, Статус: {status_text}"
        key = f"gz_card_nav_{card_id}_{current_card_status}" # Добавим статус в ключ для уникальности при обновлении

        # Используем колонки: одна для бейджа, другая для кнопки
        # Соотношение ширин подбираем экспериментально для компактности
        col_badge, col_button_text = st.columns([1, 10]) # Уменьшаем первую колонку относительно второй

        with col_badge:
            st.markdown(badge_html, unsafe_allow_html=True)
        
        with col_button_text:
            if st.button(button_label_text, key=key, help=button_help):
                if hasattr(st, 'navigate_to_app'):
                    st.navigate_to_app("Карточки", card_id=str(card_id))
                else:
                    st.query_params.clear()
                    st.query_params["page"] = "cards"
                    st.query_params["card_id"] = str(card_id)
                st.rerun()

        # Специальные флаги (этот блок можно оставить или модифицировать)
        special_flags = []
        if card.get("trickiness_level", 0) > 0:
            level_text = trickiness_categories.get(int(card["trickiness_level"]), "")
            if level_text:
                special_flags.append(f"📊 Подлость: {level_text}")
        if card.get("discrimination_avg", 0) < 0.15:
            special_flags.append("📉 Низкая дискриминативность")

        # Флаги для успешности
        success_rate = card.get("success_rate")
        if pd.notna(success_rate):
            if success_rate < 0.65: # suboptimal_low from risk_config.json
                special_flags.append(f"📉 Низкая успешность: {success_rate:.0%}")
            elif success_rate >= 0.95: # too_easy from risk_config.json
                special_flags.append(f"🥱 Слишком легко: {success_rate:.0%}")

        # Получаем complaints_total, если есть, иначе рассчитываем
        complaints_total = card.get("complaints_total")
        if pd.isna(complaints_total):
            complaint_rate = card.get("complaint_rate", 0)
            total_attempts = card.get("total_attempts", 0)
            if pd.notna(complaint_rate) and pd.notna(total_attempts) and total_attempts > 0:
                complaints_total = complaint_rate * total_attempts
            else:
                complaints_total = 0 # Если не можем рассчитать, считаем 0

        if complaints_total >= 50: # Используем порог из risk_config.json
            special_flags.append(f"⚠️ Жалобы: {int(complaints_total)}")
        elif complaints_total >= 10: # Порог "high"
             special_flags.append(f"🟡 Жалобы: {int(complaints_total)}")

        if special_flags:
            st.caption(" | ".join(special_flags))
    
    # Создаем список трики-карточек
    tricky_cards = df_cards[df_cards["trickiness_level"] > 0].sort_values("card_order")
    unique_tricky_cards_for_buttons_list = tricky_cards.drop_duplicates(subset=['card_id'], keep='first')
    
    if not unique_tricky_cards_for_buttons_list.empty:
        st.markdown("### Трики-карточки")
        for _, card in unique_tricky_cards_for_buttons_list.iterrows():
            card_id = int(card["card_id"])
            trickiness = card.get("trickiness_level", 0)
            card_order = int(card["card_order"])
            color = "red" if trickiness == 3 else ("orange" if trickiness == 2 else "gold")
            key = f"gz_tricky_nav_list_{card_id}"
            if st.button(f"№{card_order}: ID {card_id} - Подлость: {trickiness} - {card['card_type']}", key=key):
                if hasattr(st, 'navigate_to_app'):
                    st.navigate_to_app("Карточки", card_id=str(card_id))
                else:
                    st.query_params.clear()
                    st.query_params["page"] = "cards"
                    st.query_params["card_id"] = str(card_id)
                st.rerun()
        # Отображаем оставшиеся карточки при большом числе
        if len(unique_tricky_cards_for_buttons_list) > 12:
            st.info(f"И еще {len(unique_tricky_cards_for_buttons_list) - 12} карточек...")
    
    # Добавляем разделитель
    st.markdown("---")
    
    # Добавляем интерфейс экспорта данных ГЗ в конце страницы
    st.markdown("## 📥 Экспорт данных группы заданий")
    
    # Отображаем селектор полей
    field_selection_gz = display_export_field_selector_gz()
    
    # Создаем колонки для кнопки и информации
    col1, col2 = st.columns([1, 2])
    with col1:
        display_csv_download_button_gz(df_cards, eng, field_selection_gz, gz_name)
    with col2:
        # Показываем информацию о выбранных полях
        selected_fields = [k for k, v in field_selection_gz.items() if v and k != 'download_screenshots']
        download_screenshots = field_selection_gz.get('download_screenshots', False)
        if selected_fields or download_screenshots:
            field_count = len(selected_fields)
            cards_count = len(df_cards)
            
            # Группируем поля по категориям для отображения
            field_groups_display = {
                'basic': ['card_id', 'card_type', 'program_name', 'module_name', 'lesson_name', 'gz_name', 'card_order', 'card_url', 'status'],
                'metrics': ['success_rate', 'first_try_success_rate', 'success_diff', 'discrimination_avg', 'complaint_rate', 'complaints_total', 'attempted_share', 'total_attempts', 'time_median', 'trickiness_level'],
                'risk': ['risk_discrimination', 'risk_success_rate', 'risk_trickiness', 'risk_complaints', 'risk_attempted_share', 'weighted_avg_risk', 'max_risk', 'confidence_factor', 'final_risk'],
                'additional': ['card_public_url', 'screenshot_url', 'embedding', 'text_blocks', 'media', 'interactives'],
                'timestamps': ['updated_at', 'updated_by', 'export_timestamp'],
                'complaints_text': ['complaints_text'],
                'screenshots': ['download_screenshots']
            }
            
            group_names_display = {
                'basic': '📋 Основная информация',
                'metrics': '📊 Ключевые метрики', 
                'risk': '⚠️ Компоненты риска',
                'additional': '🔗 Дополнительные данные',
                'timestamps': '🕒 Временные метки',
                'complaints_text': '💬 Тексты жалоб',
                'screenshots': '📸 Файлы скриншотов'
            }
            
            selected_by_group = {}
            for group, fields in field_groups_display.items():
                selected_in_group = [f for f in fields if f in selected_fields]
                if selected_in_group:
                    selected_by_group[group] = selected_in_group
            
            if selected_by_group:
                info_text = f"**Выбрано {field_count} полей для экспорта {cards_count} карточек:**\n\n"
                for group, fields in selected_by_group.items():
                    info_text += f"**{group_names_display[group]}:** {len(fields)} полей\n"
                    info_text += "• " + ", ".join(fields) + "\n\n"
                
                # Добавляем информацию о скриншотах
                if download_screenshots:
                    info_text += "**📸 Файлы скриншотов:** Включены в архив\n"
                    info_text += "• Будет создан ZIP архив с CSV файлом и изображениями скриншотов\n\n"
                
                st.info(info_text, icon="ℹ️")
            else:
                base_text = f"**Выбрано {field_count} кастомных полей для экспорта {cards_count} карточек**"
                if download_screenshots:
                    base_text += "\n\n**📸 Файлы скриншотов:** Включены в архив"
                st.info(base_text, icon="ℹ️")
        else:
            st.warning("Не выбрано ни одного поля для экспорта", icon="⚠️")

def display_export_field_selector_gz():
    """
    Отображает интерфейс для выбора полей экспорта для ГЗ
    
    Returns:
        dict: Словарь с выбранными индивидуальными полями
    """
    # Определяем все доступные поля по группам
    field_groups = {
        'basic': {
            'title': '📋 Основная информация',
            'fields': {
                'card_id': 'ID карточки',
                'card_type': 'Тип карточки',
                'program_name': 'Название программы',
                'module_name': 'Название модуля', 
                'lesson_name': 'Название урока',
                'gz_name': 'Название группы заданий',
                'card_order': 'Порядковый номер карточки',
                'card_url': 'URL карточки в редакторе',
                'status': 'Статус карточки'
            }
        },
        'metrics': {
            'title': '📊 Ключевые метрики',
            'fields': {
                'success_rate': 'Общая успешность',
                'first_try_success_rate': 'Успешность с первой попытки',
                'success_diff': 'Разница в успешности',
                'discrimination_avg': 'Индекс дискриминативности',
                'complaint_rate': 'Доля жалоб',
                'complaints_total': 'Количество жалоб',
                'attempted_share': 'Доля пытавшихся',
                'total_attempts': 'Общее количество попыток',
                'time_median': 'Медианное время (мин)',
                'trickiness_level': 'Уровень подлости'
            }
        },
        'risk': {
            'title': '⚠️ Компоненты риска',
            'fields': {
                'risk_discrimination': 'Риск по дискриминативности',
                'risk_success_rate': 'Риск по успешности',
                'risk_trickiness': 'Риск по подлости',
                'risk_complaints': 'Риск по жалобам',
                'risk_attempted_share': 'Риск по доле пытавшихся',
                'weighted_avg_risk': 'Взвешенный средний риск',
                'max_risk': 'Максимальный риск',
                'confidence_factor': 'Коэффициент доверия',
                'final_risk': 'Итоговый риск'
            }
        },
        'additional': {
            'title': '🔗 Дополнительные данные',
            'fields': {
                'card_public_url': 'Публичная ссылка на карточку',
                'screenshot_url': 'Ссылка на скриншот',
                'embedding': 'Векторное представление (embedding)',
                'text_blocks': 'Текстовые блоки карточки',
                'media': 'Медиа-контент карточки',
                'interactives': 'Интерактивные элементы карточки'
            }
        },
        'timestamps': {
            'title': '🕒 Временные метки',
            'fields': {
                'updated_at': 'Дата последнего обновления',
                'updated_by': 'Кем обновлено',
                'export_timestamp': 'Время экспорта'
            }
        },
        'complaints_text': {
            'title': '💬 Тексты жалоб',
            'fields': {
                'complaints_text': 'Полные тексты жалоб'
            }
        },
        'screenshots': {
            'title': '📸 Файлы скриншотов',
            'fields': {
                'download_screenshots': 'Скачать файлы скриншотов карточек'
            }
        }
    }
    
    # Инициализируем состояние по умолчанию для всех полей
    force_update_key = st.session_state.get('export_gz_force_update', 0)
    
    # Создаем список всех полей
    all_field_keys = []
    for group_key, group_data in field_groups.items():
        for field_key in group_data['fields'].keys():
            all_field_keys.append(f"gz_field_{field_key}")
    
    # Устанавливаем значения по умолчанию, если их нет в session_state
    for field_key in all_field_keys:
        if field_key not in st.session_state:
            st.session_state[field_key] = True
    
    st.subheader("🔧 Настройки экспорта ГЗ")
    
    # Глобальные кнопки управления
    col_global1, col_global2, col_global3 = st.columns([1, 1, 2])
    with col_global1:
        if st.button("✅ Выбрать все поля", key="select_all_fields_global_gz"):
            st.session_state.export_gz_force_update = force_update_key + 1
            for field_key in all_field_keys:
                st.session_state[field_key] = True
            st.rerun()
    
    with col_global2:
        if st.button("❌ Снять все поля", key="deselect_all_fields_global_gz"):
            st.session_state.export_gz_force_update = force_update_key + 1
            for field_key in all_field_keys:
                st.session_state[field_key] = False
            st.rerun()
    
    with col_global3:
        # Показываем счетчик выбранных полей
        selected_count = sum(1 for field_key in all_field_keys if st.session_state.get(field_key, True))
        st.info(f"Выбрано полей: {selected_count}/{len(all_field_keys)}")
    
    st.markdown("---")
    
    # Создаем группы полей
    selected_fields = {}
    
    for group_key, group_data in field_groups.items():
        with st.expander(group_data['title'], expanded=False):
            # Кнопки для группы
            col_group1, col_group2, col_group3 = st.columns([1, 1, 2])
            
            group_field_keys = [f"gz_field_{field_key}" for field_key in group_data['fields'].keys()]
            
            with col_group1:
                if st.button(f"✅ Все", key=f"select_group_gz_{group_key}"):
                    st.session_state.export_gz_force_update = force_update_key + 1
                    for field_key in group_field_keys:
                        st.session_state[field_key] = True
                    st.rerun()
            
            with col_group2:
                if st.button(f"❌ Ничего", key=f"deselect_group_gz_{group_key}"):
                    st.session_state.export_gz_force_update = force_update_key + 1
                    for field_key in group_field_keys:
                        st.session_state[field_key] = False
                    st.rerun()
            
            with col_group3:
                # Показываем счетчик для группы
                group_selected_count = sum(1 for field_key in group_field_keys if st.session_state.get(field_key, True))
                st.caption(f"Выбрано: {group_selected_count}/{len(group_field_keys)}")
            
            # Чекбоксы для полей в группе
            for field_key, field_description in group_data['fields'].items():
                session_key = f"gz_field_{field_key}"
                checkbox_key = f"{session_key}_{force_update_key}"
                
                selected = st.checkbox(
                    field_description,
                    value=st.session_state.get(session_key, True),
                    key=checkbox_key,
                    help=f"Включить поле '{field_key}' в экспорт"
                )
                
                selected_fields[field_key] = selected
                st.session_state[session_key] = selected
    
    return selected_fields

def get_screenshot_url_gz(card_id):
    """
    Формирует URL для скриншота карточки из Yandex Object Storage
    
    Args:
        card_id: ID карточки
    
    Returns:
        str: URL скриншота
    """
    return f"https://snufffkin-pics.website.yandexcloud.net/Refactor/image/{card_id}.png"

def prepare_gz_data_for_csv(df_cards, engine, field_selection=None):
    """
    Подготавливает данные карточек ГЗ для экспорта в CSV
    
    Args:
        df_cards: DataFrame с данными карточек ГЗ
        engine: SQLAlchemy engine для подключения к БД
        field_selection: dict с выбранными индивидуальными полями для экспорта
        
    Returns:
        pd.DataFrame: DataFrame с данными для экспорта
    """
    # Если не указан выбор полей, включаем все поля по умолчанию
    if field_selection is None:
        field_selection = {
            'card_id': True, 'card_type': True, 'program_name': True, 'module_name': True,
            'lesson_name': True, 'gz_name': True, 'card_order': True, 'card_url': True,
            'status': True, 'success_rate': True, 'first_try_success_rate': True,
            'success_diff': True, 'discrimination_avg': True, 'complaint_rate': True,
            'complaints_total': True, 'attempted_share': True, 'total_attempts': True,
            'time_median': True, 'trickiness_level': True, 'risk_discrimination': True,
            'risk_success_rate': True, 'risk_trickiness': True, 'risk_complaints': True,
            'risk_attempted_share': True, 'weighted_avg_risk': True, 'max_risk': True,
            'confidence_factor': True, 'final_risk': True, 'card_public_url': True,
            'screenshot_url': True, 'embedding': True, 'text_blocks': True, 'media': True,
            'interactives': True, 'updated_at': True, 'updated_by': True, 
            'export_timestamp': True, 'complaints_text': True, 'download_screenshots': False
        }
    
    if df_cards.empty:
        return pd.DataFrame()
    
    # Получаем конфигурацию для расчета компонентов риска
    config = core.get_config()
    
    # Список для хранения данных экспорта
    export_data_list = []
    
    # Получаем данные из cards_content только если нужны
    content_data_dict = {}
    content_fields_needed = any(field_selection.get(field, False) for field in ['embedding', 'text_blocks', 'media', 'interactives'])
    
    if content_fields_needed:
        try:
            card_ids_for_content = df_cards['card_id'].dropna().unique().tolist()
            if card_ids_for_content:
                with engine.connect() as conn:
                    from sqlalchemy import text
                    
                    # Формируем список полей для запроса
                    fields_to_select = ['card_id']
                    if field_selection.get('embedding', False):
                        fields_to_select.append('embedding')
                    if field_selection.get('text_blocks', False):
                        fields_to_select.append('text_blocks')
                    if field_selection.get('media', False):
                        fields_to_select.append('media')
                    if field_selection.get('interactives', False):
                        fields_to_select.append('interactives')
                    
                    content_query = text(f"""
                        SELECT {', '.join(fields_to_select)}
                        FROM cards_content 
                        WHERE card_id = ANY(:card_ids)
                    """)
                    result = conn.execute(content_query, {"card_ids": card_ids_for_content})
                    
                    for row in result:
                        card_id = row[0]
                        content_data_dict[card_id] = {}
                        
                        for i, field_name in enumerate(fields_to_select[1:], 1):  # Пропускаем card_id
                            try:
                                field_value = row[i]
                                if field_name == 'embedding' and field_value:
                                    # Специальная обработка для embedding
                                    vector_str = str(field_value)
                                    if vector_str.startswith('[') and vector_str.endswith(']'):
                                        content_data_dict[card_id][field_name] = vector_str[1:-1]  # Убираем [ и ]
                                    else:
                                        content_data_dict[card_id][field_name] = vector_str
                                else:
                                    # Для остальных полей просто конвертируем в строку
                                    content_data_dict[card_id][field_name] = str(field_value) if field_value is not None else ""
                            except Exception as field_e:
                                print(f"Ошибка при обработке поля {field_name} для карточки {card_id}: {str(field_e)}")
                                content_data_dict[card_id][field_name] = ""
        except Exception as e:
            print(f"Ошибка при получении данных из cards_content для ГЗ: {str(e)}")
    
    # Обрабатываем каждую карточку
    for _, card_row in df_cards.iterrows():
        card_dict = card_row.to_dict()
        export_data = {}
        
        # Рассчитываем компоненты риска только если нужны
        risk_discr = risk_success = risk_trickiness = risk_complaints = risk_attempted = np.nan
        weighted_avg_risk = max_risk = confidence_factor_val = final_risk_val = np.nan
        
        if any(field_selection.get(f'risk_{comp}', False) for comp in ['discrimination', 'success_rate', 'trickiness', 'complaints', 'attempted_share']) or \
           any(field_selection.get(f'{comp}', False) for comp in ['weighted_avg_risk', 'max_risk', 'confidence_factor', 'final_risk']):
            # Рассчитываем компоненты риска
            d_avg = card_row.get("discrimination_avg")
            s_rate = card_row.get("success_rate")
            
            risk_discr = core.discrimination_risk_score(d_avg) if pd.notna(d_avg) else np.nan
            risk_success = core.success_rate_risk_score(s_rate) if pd.notna(s_rate) else np.nan
            risk_trickiness = core.trickiness_risk_score(card_dict)
            risk_complaints = core.complaint_risk_score(card_dict)
            risk_attempted = core.attempted_share_risk_score(card_row.get("attempted_share")) if pd.notna(card_row.get("attempted_share")) else np.nan
            
            # Рассчитываем взвешенные риски
            WEIGHT_DISCRIMINATION = config["weights"]["discrimination"]
            WEIGHT_SUCCESS_RATE = config["weights"]["success_rate"]
            WEIGHT_TRICKINESS = config["weights"].get("trickiness", 0.15)
            WEIGHT_COMPLAINT_RATE = config["weights"]["complaint_rate"]
            WEIGHT_ATTEMPTED = config["weights"]["attempted"]
            
            # Вычисляем взвешенное среднее
            weighted_sum = 0
            total_weight = 0
            if pd.notna(risk_discr): weighted_sum += WEIGHT_DISCRIMINATION * risk_discr; total_weight += WEIGHT_DISCRIMINATION
            if pd.notna(risk_success): weighted_sum += WEIGHT_SUCCESS_RATE * risk_success; total_weight += WEIGHT_SUCCESS_RATE
            if pd.notna(risk_trickiness): weighted_sum += WEIGHT_TRICKINESS * risk_trickiness; total_weight += WEIGHT_TRICKINESS
            if pd.notna(risk_complaints): weighted_sum += WEIGHT_COMPLAINT_RATE * risk_complaints; total_weight += WEIGHT_COMPLAINT_RATE
            if pd.notna(risk_attempted): weighted_sum += WEIGHT_ATTEMPTED * risk_attempted; total_weight += WEIGHT_ATTEMPTED
            
            weighted_avg_risk = (weighted_sum / total_weight) if total_weight > 0 else np.nan
            
            # Определяем максимальный риск
            all_risks_list = [r for r in [risk_discr, risk_success, risk_trickiness, risk_complaints, risk_attempted] if pd.notna(r)]
            max_risk = np.max(all_risks_list) if all_risks_list else np.nan
            
            # Рассчитываем итоговый риск
            ta_for_confidence = card_row.get("total_attempts")
            if pd.notna(ta_for_confidence):
                significance_threshold = config["stats"]["significance_threshold"]
                if significance_threshold > 0:
                    confidence_factor_val = min(ta_for_confidence / significance_threshold, 1.0)
                else:
                    confidence_factor_val = 1.0
            
            final_risk_val = card_row.get('risk', np.nan)
        
        # Безопасное получение complaints_total
        ct_raw = card_row.get('complaints_total')
        if pd.notna(ct_raw):
            complaints_total = ct_raw
        else:
            cr_for_calc = card_row.get('complaint_rate')
            ta_for_calc = card_row.get('total_attempts')
            if pd.notna(cr_for_calc) and pd.notna(ta_for_calc):
                complaints_total = cr_for_calc * ta_for_calc
            else:
                complaints_total = np.nan
        
        # Получаем дополнительные данные если нужны
        screenshot_url = ""
        card_id_int = int(card_row.get("card_id", 0))
        card_content_data = content_data_dict.get(card_id_int, {})
        
        if field_selection.get('screenshot_url', False):
            screenshot_url = get_screenshot_url_gz(card_id_int)
        
        # Подготавливаем данные для экспорта на основе выбранных полей
        export_data = {}
        
        # Основная информация
        if field_selection.get('card_id', False):
            export_data['card_id'] = int(card_row.get("card_id", 0))
        if field_selection.get('card_type', False):
            export_data['card_type'] = card_row.get("card_type", "")
        if field_selection.get('program_name', False):
            export_data['program_name'] = card_row.get("program_name", "")
        if field_selection.get('module_name', False):
            export_data['module_name'] = card_row.get("module_name", "")
        if field_selection.get('lesson_name', False):
            export_data['lesson_name'] = card_row.get("lesson_name", "")
        if field_selection.get('gz_name', False):
            export_data['gz_name'] = card_row.get("gz_name", "")
        if field_selection.get('card_order', False):
            export_data['card_order'] = card_row.get("card_order", "")
        if field_selection.get('card_url', False):
            export_data['card_url'] = card_row.get("card_url", "")
        if field_selection.get('status', False):
            export_data['status'] = card_row.get("status", "")
        
        # Основные метрики
        if field_selection.get('success_rate', False):
            export_data['success_rate'] = card_row.get("success_rate")
        if field_selection.get('first_try_success_rate', False):
            export_data['first_try_success_rate'] = card_row.get("first_try_success_rate")
        if field_selection.get('success_diff', False):
            export_data['success_diff'] = card_row.get("success_diff")
        if field_selection.get('discrimination_avg', False):
            export_data['discrimination_avg'] = card_row.get("discrimination_avg")
        if field_selection.get('complaint_rate', False):
            export_data['complaint_rate'] = card_row.get("complaint_rate")
        if field_selection.get('complaints_total', False):
            export_data['complaints_total'] = complaints_total
        if field_selection.get('attempted_share', False):
            export_data['attempted_share'] = card_row.get("attempted_share")
        if field_selection.get('total_attempts', False):
            export_data['total_attempts'] = card_row.get("total_attempts")
        if field_selection.get('time_median', False):
            export_data['time_median'] = card_row.get("time_median")
        if field_selection.get('trickiness_level', False):
            export_data['trickiness_level'] = card_row.get("trickiness_level", 0)
        
        # Компоненты риска
        if field_selection.get('risk_discrimination', False):
            export_data['risk_discrimination'] = risk_discr
        if field_selection.get('risk_success_rate', False):
            export_data['risk_success_rate'] = risk_success
        if field_selection.get('risk_trickiness', False):
            export_data['risk_trickiness'] = risk_trickiness
        if field_selection.get('risk_complaints', False):
            export_data['risk_complaints'] = risk_complaints
        if field_selection.get('risk_attempted_share', False):
            export_data['risk_attempted_share'] = risk_attempted
        if field_selection.get('weighted_avg_risk', False):
            export_data['weighted_avg_risk'] = weighted_avg_risk
        if field_selection.get('max_risk', False):
            export_data['max_risk'] = max_risk
        if field_selection.get('confidence_factor', False):
            export_data['confidence_factor'] = confidence_factor_val
        if field_selection.get('final_risk', False):
            export_data['final_risk'] = final_risk_val
        
        # Дополнительные данные
        if field_selection.get('card_public_url', False):
            export_data['card_public_url'] = card_row.get("card_public_url", "")
        if field_selection.get('screenshot_url', False):
            export_data['screenshot_url'] = screenshot_url
        if field_selection.get('embedding', False):
            export_data['embedding'] = card_content_data.get('embedding', "")
        if field_selection.get('text_blocks', False):
            export_data['text_blocks'] = card_content_data.get('text_blocks', "")
        if field_selection.get('media', False):
            export_data['media'] = card_content_data.get('media', "")
        if field_selection.get('interactives', False):
            export_data['interactives'] = card_content_data.get('interactives', "")
        
        # Временные метки
        if field_selection.get('updated_at', False):
            export_data['updated_at'] = card_row.get("updated_at", "")
        if field_selection.get('updated_by', False):
            export_data['updated_by'] = card_row.get("updated_by", "")
        if field_selection.get('export_timestamp', False):
            export_data['export_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Тексты жалоб
        if field_selection.get('complaints_text', False):
            complaints_text = card_row.get("complaints_text", "")
            export_data['complaints_text'] = complaints_text.strip() if pd.notna(complaints_text) else ""
        
        export_data_list.append(export_data)
    
    # Создаем DataFrame
    df_export = pd.DataFrame(export_data_list)
    
    return df_export

def download_image_from_url(url, timeout=10):
    """
    Скачивает изображение по URL
    
    Args:
        url: URL изображения для скачивания
        timeout: Таймаут запроса в секундах
        
    Returns:
        bytes: Содержимое изображения или None при ошибке
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Ошибка при скачивании изображения {url}: {str(e)}")
        return None

def create_screenshot_matrix(screenshots_data, gz_name):
    """
    Создает матрицу скриншотов - одно большое изображение со всеми скриншотами карточек
    
    Args:
        screenshots_data: список кортежей (card_id, image_data) с данными изображений
        gz_name: название группы заданий
        
    Returns:
        bytes: содержимое PNG изображения матрицы
    """
    if not screenshots_data:
        return None
    
    # Параметры матрицы
    THUMBNAIL_WIDTH = 600
    THUMBNAIL_HEIGHT = 500
    LABEL_HEIGHT = 30
    PADDING = 5
    BACKGROUND_COLOR = (255, 255, 255)  # Белый
    TEXT_COLOR = (0, 0, 0)  # Черный
    
    # Вычисляем количество колонок и строк (примерно квадратная сетка)
    total_images = len(screenshots_data)
    cols = math.ceil(math.sqrt(total_images))
    rows = math.ceil(total_images / cols)
    
    # Размеры итогового изображения
    cell_width = THUMBNAIL_WIDTH + PADDING
    cell_height = THUMBNAIL_HEIGHT + LABEL_HEIGHT + PADDING
    
    matrix_width = cols * cell_width + PADDING
    matrix_height = rows * cell_height + PADDING + 50  # +50 для заголовка
    
    # Создаем основное изображение
    matrix_image = Image.new('RGB', (matrix_width, matrix_height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(matrix_image)
    
    # Пытаемся загрузить шрифт
    try:
        # Попробуем несколько вариантов шрифтов
        font_paths = [
            "arial.ttf", "Arial.ttf", "calibri.ttf", "Calibri.ttf",
            "/System/Library/Fonts/Arial.ttf",  # macOS
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Linux
        ]
        font = None
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, 16)
                break
            except:
                continue
        
        title_font = ImageFont.truetype(font_path, 20) if font else None
    except:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()
    
    # Добавляем заголовок
    title_text = f"Матрица скриншотов: {gz_name} ({total_images} карточек)"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (matrix_width - title_width) // 2
    draw.text((title_x, 15), title_text, fill=TEXT_COLOR, font=title_font)
    
    # Размещаем скриншоты
    for idx, (card_id, image_data) in enumerate(screenshots_data):
        row = idx // cols
        col = idx % cols
        
        # Вычисляем позицию
        x = col * cell_width + PADDING
        y = row * cell_height + PADDING + 50  # +50 для заголовка
        
        try:
            if image_data:
                # Загружаем и обрабатываем изображение
                screenshot = Image.open(io.BytesIO(image_data))
                
                # Изменяем размер с сохранением пропорций
                screenshot.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS)
                
                # Создаем изображение с белым фоном для центрирования
                thumbnail = Image.new('RGB', (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), BACKGROUND_COLOR)
                
                # Центрируем скриншот
                paste_x = (THUMBNAIL_WIDTH - screenshot.width) // 2
                paste_y = (THUMBNAIL_HEIGHT - screenshot.height) // 2
                thumbnail.paste(screenshot, (paste_x, paste_y))
                
                # Вставляем в матрицу
                matrix_image.paste(thumbnail, (x, y))
            else:
                # Создаем заглушку для отсутствующего изображения
                placeholder = Image.new('RGB', (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), (240, 240, 240))
                placeholder_draw = ImageDraw.Draw(placeholder)
                
                # Добавляем текст "Нет изображения"
                placeholder_text = "Нет\nизображения"
                text_bbox = placeholder_draw.textbbox((0, 0), placeholder_text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x = (THUMBNAIL_WIDTH - text_width) // 2
                text_y = (THUMBNAIL_HEIGHT - text_height) // 2
                placeholder_draw.text((text_x, text_y), placeholder_text, fill=(128, 128, 128), font=font, align='center')
                
                matrix_image.paste(placeholder, (x, y))
            
        except Exception as e:
            print(f"Ошибка при обработке изображения для карточки {card_id}: {str(e)}")
            # Создаем заглушку с ошибкой
            error_placeholder = Image.new('RGB', (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), (255, 200, 200))
            error_draw = ImageDraw.Draw(error_placeholder)
            error_text = "Ошибка\nзагрузки"
            text_bbox = error_draw.textbbox((0, 0), error_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = (THUMBNAIL_WIDTH - text_width) // 2
            text_y = (THUMBNAIL_HEIGHT - text_height) // 2
            error_draw.text((text_x, text_y), error_text, fill=(128, 0, 0), font=font, align='center')
            matrix_image.paste(error_placeholder, (x, y))
        
        # Добавляем подпись с ID карточки
        label_text = f"ID: {card_id}"
        label_y = y + THUMBNAIL_HEIGHT + 5
        
        # Центрируем текст подписи
        text_bbox = draw.textbbox((0, 0), label_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        label_x = x + (THUMBNAIL_WIDTH - text_width) // 2
        
        # Рисуем фон для текста (белый прямоугольник)
        bg_padding = 2
        draw.rectangle([
            label_x - bg_padding, 
            label_y - bg_padding,
            label_x + text_width + bg_padding,
            label_y + text_bbox[3] - text_bbox[1] + bg_padding
        ], fill=BACKGROUND_COLOR, outline=(200, 200, 200))
        
        # Рисуем текст
        draw.text((label_x, label_y), label_text, fill=TEXT_COLOR, font=font)
    
    # Сохраняем в буфер
    output_buffer = io.BytesIO()
    matrix_image.save(output_buffer, format='PNG', quality=95)
    output_buffer.seek(0)
    
    return output_buffer.getvalue()

def create_zip_archive_with_screenshots(df_export, df_cards, gz_name):
    """
    Создает ZIP архив с CSV файлом и скриншотами карточек
    
    Args:
        df_export: DataFrame с данными для экспорта в CSV
        df_cards: DataFrame с данными карточек (для получения screenshot_url)
        gz_name: Название группы заданий
        
    Returns:
        bytes: Содержимое ZIP архива
    """
    # Создаем буфер для ZIP архива
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Добавляем CSV файл
        csv_buffer = io.StringIO()
        df_export.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_data = csv_buffer.getvalue()
        
        safe_gz_name = "".join(c for c in gz_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        csv_filename = f"gz_{safe_gz_name}_data.csv"
        zip_file.writestr(csv_filename, csv_data.encode('utf-8-sig'))
        
        # Создаем папку для скриншотов в архиве
        screenshots_folder = "screenshots/"
        
        # Скачиваем и добавляем скриншоты
        success_count = 0
        error_count = 0
        screenshots_data = []  # Для создания матрицы
        
        for _, card_row in df_cards.iterrows():
            card_id = int(card_row.get("card_id", 0))
            
            # Получаем URL скриншота
            screenshot_url = get_screenshot_url_gz(card_id)
            
            # Скачиваем изображение
            image_data = download_image_from_url(screenshot_url)
            
            if image_data:
                # Добавляем изображение в архив
                image_filename = f"{screenshots_folder}{card_id}.png"
                zip_file.writestr(image_filename, image_data)
                success_count += 1
                
                # Сохраняем для матрицы
                screenshots_data.append((card_id, image_data))
            else:
                error_count += 1
                # Добавляем в матрицу даже если изображение не загрузилось
                screenshots_data.append((card_id, None))
        
        # Создаем и добавляем матрицу скриншотов
        if screenshots_data:
            try:
                matrix_data = create_screenshot_matrix(screenshots_data, gz_name)
                if matrix_data:
                    matrix_filename = f"screenshot_matrix_{safe_gz_name}.png"
                    zip_file.writestr(matrix_filename, matrix_data)
                    print(f"Матрица скриншотов создана: {matrix_filename}")
            except Exception as e:
                print(f"Ошибка при создании матрицы скриншотов: {str(e)}")
        
        # Добавляем информационный файл о результатах скачивания
        matrix_info = "Да" if screenshots_data else "Нет"
        info_content = f"""Информация о скачивании скриншотов
Группа заданий: {gz_name}
Всего карточек: {len(df_cards)}
Скриншотов успешно скачано: {success_count}
Ошибок при скачивании: {error_count}
Матрица скриншотов создана: {matrix_info}
Дата создания архива: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Содержимое архива:
- {csv_filename} - CSV файл с данными карточек
- screenshots/ - папка с индивидуальными скриншотами карточек
- screenshot_matrix_{safe_gz_name}.png - матрица всех скриншотов с подписями ID
- download_info.txt - этот информационный файл

Как использовать матрицу скриншотов:
Матрица содержит все скриншоты карточек в виде сетки с подписями ID.
Каждый скриншот масштабирован до размера 300x200 пикселей с сохранением пропорций.
Под каждым изображением указан ID соответствующей карточки.
Это удобно для быстрого визуального анализа всех карточек группы заданий.
"""
        zip_file.writestr("download_info.txt", info_content.encode('utf-8'))
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def display_csv_download_button_gz(df_cards, engine, field_selection, gz_name):
    """
    Отображает кнопку для скачивания данных карточек ГЗ в CSV формате или ZIP архиве со скриншотами
    
    Args:
        df_cards: DataFrame с данными карточек ГЗ
        engine: SQLAlchemy engine для подключения к БД
        field_selection: dict с выбранными индивидуальными полями для экспорта
        gz_name: Название группы заданий
    """
    try:
        # Подготавливаем данные для экспорта
        df_export = prepare_gz_data_for_csv(df_cards, engine, field_selection)
        
        # Проверяем, есть ли данные для экспорта
        if df_export.empty or df_export.shape[1] == 0:
            st.warning("Выберите хотя бы одно поле для экспорта")
            return
        
        # Проверяем, нужно ли включать скриншоты
        download_screenshots = field_selection.get('download_screenshots', False)
        
        # Формируем базовые параметры
        selected_fields = [k for k, v in field_selection.items() if v and k != 'download_screenshots']
        field_count = len(selected_fields)
        cards_count = len(df_cards)
        safe_gz_name = "".join(c for c in gz_name if c.isalnum() or c in (' ', '-', '_')).rstrip()[:20]
        
        if download_screenshots:
            # Создаем ZIP архив с CSV и скриншотами
            with st.spinner("Создание архива со скриншотами... Это может занять некоторое время."):
                zip_data = create_zip_archive_with_screenshots(df_export, df_cards, gz_name)
            
            # Формируем имя архива
            filename = f"gz_{safe_gz_name}_{cards_count}_cards_with_screenshots.zip"
            
            # Отображаем кнопку скачивания архива
            st.download_button(
                label=f"📦 Скачать архив ГЗ ({cards_count} карточек, {field_count} полей + скриншоты)",
                data=zip_data,
                file_name=filename,
                mime="application/zip",
                help=f"Экспортировать {field_count} выбранных полей для {cards_count} карточек + файлы скриншотов в ZIP архиве"
            )
        else:
            # Обычный CSV экспорт
            csv_buffer = io.StringIO()
            df_export.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            csv_data = csv_buffer.getvalue()
            
            # Формируем имя файла
            if field_count <= 5:
                fields_suffix = "_".join(selected_fields[:5])
            else:
                fields_suffix = f"{field_count}_fields"
            
            filename = f"gz_{safe_gz_name}_{cards_count}_cards_{fields_suffix}.csv"
            
            # Отображаем кнопку скачивания
            st.download_button(
                label=f"📥 Скачать данные ГЗ ({cards_count} карточек, {field_count} полей)",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
                help=f"Экспортировать {field_count} выбранных полей для {cards_count} карточек"
            )
        
    except Exception as e:
        st.error(f"Ошибка при подготовке данных для экспорта: {str(e)}")
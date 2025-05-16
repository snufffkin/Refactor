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

import core
from components.utils import create_hierarchical_header, display_clickable_items, add_gz_links
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_cards_chart, display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart, display_completion_radar, display_trickiness_chart, display_trickiness_success_chart
import navigation_utils

def page_gz(df_cards_input: pd.DataFrame, create_link_fn=None):
    """Страница группы заданий с детализацией по карточкам"""
    prog_name = st.session_state.get('filter_program')
    module_name = st.session_state.get('filter_module')
    lesson_name = st.session_state.get('filter_lesson')
    gz_name = st.session_state.get('filter_gz')

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

    df_gz = df_cards_input[
        (df_cards_input["program_name"] == prog_name) &
        (df_cards_input["module_name"] == module_name) &
        (df_cards_input["lesson_name"] == lesson_name) &
        (df_cards_input["gz_name"] == gz_name)
    ].copy()
    
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
                        navigation_utils.navigate_to("cards", card_id=str(card_id))
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
            unique_low_discr_cards_for_buttons = low_discr_cards.drop_duplicates(subset=['card_id'], keep='first')
            for _, row in unique_low_discr_cards_for_buttons.iterrows():
                card_id = int(row['card_id'])
                if st.button(f"Перейти к карточке {card_id}", key=f"gz_lowdiscr_nav_list_{card_id}"):
                    # Навигация без сброса сессии
                    navigation_utils.navigate_to("cards", card_id=str(card_id))
                    st.rerun()
    
    # 5. Таблица с карточками и ссылками на карточки
    st.subheader("📋 Детальная информация по карточкам")
    
    # Отображаем таблицу, сортируя по card_order
    cards_df = df_cards[["card_id", "card_type", "status", "success_rate", 
                      "first_try_success_rate", "complaint_rate", 
                      "discrimination_avg", "total_attempts", "risk", "trickiness_level", "card_order"]]
    
    # Сортируем по порядку карточек
    cards_df = cards_df.sort_values("card_order").reset_index(drop=True)
    
    # Переорганизуем колонки, чтобы номер был в начале
    cards_df = cards_df[["card_order", "card_id", "card_type", "status", "success_rate", 
                         "first_try_success_rate", "complaint_rate", 
                         "discrimination_avg", "total_attempts", "risk", "trickiness_level"]]
    
    # Создаем таблицу с данными для отображения
    display_df = pd.DataFrame()
    display_df["Номер"] = cards_df["card_order"]
    display_df["ID карточки"] = cards_df["card_id"]
    display_df["Тип"] = cards_df["card_type"]
    display_df["Статус"] = cards_df["status"]
    display_df["Успешность"] = cards_df["success_rate"].apply(lambda x: f"{x:.1%}")
    display_df["Успех с 1-й"] = cards_df["first_try_success_rate"].apply(lambda x: f"{x:.1%}")
    display_df["Жалобы"] = cards_df["complaint_rate"].apply(lambda x: f"{x:.1%}")
    display_df["Дискр."] = cards_df["discrimination_avg"].apply(lambda x: f"{x:.2f}")
    # Заменяем NaN на 0 и форматируем как целое число в строку
    display_df["Попытки"] = cards_df["total_attempts"].fillna(0).astype(int).astype(str)
    display_df["Риск"] = cards_df["risk"].apply(lambda x: f"{x:.2f}")
    
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
    # Кнопки для перехода к детальному анализу карточек
    # Удаляем дубликаты по card_id перед генерацией кнопок
    unique_cards_df_for_buttons = cards_df.drop_duplicates(subset=['card_id'], keep='first')
    for _, row in unique_cards_df_for_buttons.iterrows():
        card_id = int(row['card_id'])
        card_order = int(row['card_order'])
        if st.button(f"Перейти к карточке {card_id} (№{card_order})", key=f"gz_detail_nav_{card_id}"):
            # Навигация без сброса сессии
            navigation_utils.navigate_to("cards", card_id=str(card_id))
            st.rerun()
    
    # 6. Кнопки для быстрого перехода ко всем карточкам, сортированные по card_order
    st.subheader("🔍 Все карточки в группе заданий")
    for _, card in df_cards.sort_values("card_order").iterrows():
        card_id = int(card["card_id"])
        risk = card["risk"]
        card_type = card["card_type"]
        card_order = int(card["card_order"])
        color = "red" if risk > 0.75 else ("orange" if risk > 0.5 else ("gold" if risk > 0.25 else "green"))
        key = f"gz_card_nav_{card_id}"
        if st.button(f"№{card_order}: ID {card_id} - Риск: {risk:.2f} - {card_type}", key=key):
            navigation_utils.navigate_to("cards", card_id=str(card_id))
            st.rerun()
        # Специальные флаги
        special_flags = []
        if card.get("trickiness_level", 0) > 0:
            level_text = trickiness_categories.get(int(card["trickiness_level"]), "")
            if level_text:
                special_flags.append(f"📊 Подлость: {level_text}")
        if card.get("discrimination_avg", 0) < 0.15:
            special_flags.append("📉 Низкая дискриминативность")
        if card.get("complaint_rate", 0) > 0.05:
            special_flags.append("⚠️ Жалобы")
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
                navigation_utils.navigate_to("cards", card_id=str(card_id))
                st.rerun()
        # Отображаем оставшиеся карточки при большом числе
        if len(unique_tricky_cards_for_buttons_list) > 12:
            st.info(f"И еще {len(unique_tricky_cards_for_buttons_list) - 12} карточек...")
    
    # Создаем список карточек с низкой дискриминативностью
    low_discr_cards = df_cards[df_cards["discrimination_avg"] < 0.15].sort_values("card_order")
    unique_low_discr_cards_for_buttons_list = low_discr_cards.drop_duplicates(subset=['card_id'], keep='first')
    
    if not unique_low_discr_cards_for_buttons_list.empty:
        st.markdown("### Карточки с низкой дискриминативностью")
        for _, card in unique_low_discr_cards_for_buttons_list.iterrows():
            card_id = int(card["card_id"])
            discr = card["discrimination_avg"]
            card_order = int(card["card_order"])
            color = "purple"
            key = f"gz_lowdiscr_nav_list_{card_id}"
            if st.button(f"№{card_order}: ID {card_id} - Дискр.: {discr:.2f} - {card['card_type']}", key=key):
                navigation_utils.navigate_to("cards", card_id=str(card_id))
                st.rerun()
        if len(unique_low_discr_cards_for_buttons_list) > 12:
            st.info(f"И еще {len(unique_low_discr_cards_for_buttons_list) - 12} карточек...")

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
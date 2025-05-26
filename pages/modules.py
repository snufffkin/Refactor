# pages/modules.py с обновленной нумерацией для графиков
"""
Страница модуля (Обзор + навигация по урокам)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from sqlalchemy import text

import core
from components.utils import create_hierarchical_header, display_clickable_items
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart, display_completion_radar
import navigation_utils

def page_modules(df: pd.DataFrame):
    """Страница модуля с детализацией по урокам"""
    
    prog_name = st.session_state.get('filter_program')
    module_name = st.session_state.get('filter_module')

    if not prog_name or not module_name:
        st.warning("Программа или модуль не выбраны.")
        # TODO: Возможно, предложить выбрать программу/модуль или вернуться на предыдущую страницу
        return

    if df is None or df.empty:
        st.warning("Нет данных об уроках для отображения.")
        return

    # Переименование столбцов из mv_lesson_stats в ожидаемый формат
    column_mapping = {
        "avg_success_rate": "success_rate",
        "avg_first_try_success_rate": "first_try_success_rate",
        "avg_complaint_rate": "complaint_rate",
        "avg_discrimination": "discrimination_avg",
        "avg_risk": "risk",
        "avg_time_median": "time_median",
        # total_gz будет использован для cards_count
    }
    df = df.rename(columns=column_mapping)

    # Создание cards_count на основе total_gz или длины gz_ids
    # В mv_lesson_stats есть total_gz
    if 'total_gz' in df.columns:
        df['cards_count'] = df['total_gz']
    elif 'gz_ids' in df.columns: # Резервный вариант
        df['cards_count'] = df['gz_ids'].apply(lambda x: len(x) if isinstance(x, (list, np.ndarray)) else 0)
    else:
        df['cards_count'] = 0

    # Фильтруем данные по выбранной программе и модулю
    # df уже должен содержать только уроки, отфильтруем их
    df_module = df[(df["program_name"] == prog_name) & (df["module_name"] == module_name)].copy()

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
    # display_metrics_row(df_module, compare_with=df[df["program_name"] == prog_name])
    # df для compare_with должен быть df модулей, а не уроков. Пока упростим.
    display_metrics_row(df_module)
    
    # Добавляем метрику среднего суммарного времени на урок
    if 'time_median' in df_module.columns and not df_module.empty:
        avg_time_per_lesson = df_module["time_median"].mean() / 60 if not df_module.empty else 0
        st.subheader("⏱️ Среднее время на урок в этом модуле")
        st.metric(
            label="Среднее время на урок (мин)",
            value=f"{avg_time_per_lesson:.1f}"
        )
    
    # 2. Отображаем распределение риска и статусы
    col1, col2 = st.columns(2)
    
    with col1:
        display_risk_distribution(df_module, "lesson_name")
    
    with col2:
        # display_status_chart(df_module, "lesson_name") # Status не доступен в mv_lesson_stats
        # st.info("Данные о статусах уроков/карточек недоступны на этом уровне.")
        # --- НАЧАЛО ИЗМЕНЕНИЙ ДЛЯ ГРАФИКА СТАТУСОВ МОДУЛЯ ---
        if not df_module.empty and "lesson_name" in df_module.columns:
            # Получаем уникальные lesson_name из df_module (это уже отфильтрованные уроки текущего модуля)
            module_lesson_names = df_module["lesson_name"].dropna().unique().tolist()
            
            if module_lesson_names:
                try:
                    engine = core.get_engine()
                    current_program_name = st.session_state.get('filter_program')
                    current_module_name = st.session_state.get('filter_module')
                    
                    # 1. Получить lesson_id для уроков этого модуля
                    lesson_name_placeholders = ", ".join([f":lesson_name_{i}" for i in range(len(module_lesson_names))])
                    params_lesson_ids = {
                        "program_name": current_program_name,
                        "module_name": current_module_name
                    }
                    for i, name in enumerate(module_lesson_names):
                        params_lesson_ids[f"lesson_name_{i}"] = name
                    
                    lesson_ids_query = text(f"""
                        SELECT lesson_id 
                        FROM lesson_ids 
                        WHERE program_name = :program_name 
                          AND module_name = :module_name 
                          AND lesson_name IN ({lesson_name_placeholders})
                    """)
                    
                    df_lesson_ids_for_module = pd.read_sql(lesson_ids_query, engine, params=params_lesson_ids)
                    
                    if not df_lesson_ids_for_module.empty and "lesson_id" in df_lesson_ids_for_module.columns:
                        lesson_ids_list = df_lesson_ids_for_module["lesson_id"].dropna().unique().tolist()
                        if lesson_ids_list:
                            # 2. Получить все card_id для этих lesson_id
                            lesson_id_placeholders_for_cards = ", ".join([f":lesson_id_{i}" for i in range(len(lesson_ids_list))])
                            params_card_ids = {f"lesson_id_{i}": lid for i, lid in enumerate(lesson_ids_list)}
                            
                            cards_for_module_query = text(f"""
                                SELECT DISTINCT card_id 
                                FROM cards_structure 
                                WHERE lesson_id IN ({lesson_id_placeholders_for_cards})
                            """)
                            df_card_ids_for_module = pd.read_sql(cards_for_module_query, engine, params=params_card_ids)
                            
                            if not df_card_ids_for_module.empty and "card_id" in df_card_ids_for_module.columns:
                                card_ids_list = df_card_ids_for_module["card_id"].dropna().unique().tolist()
                                if card_ids_list:
                                    # 3. Получить свежие статусы
                                    df_fresh_statuses_module = core.get_fresh_card_statuses(engine, card_ids_list)
                                    if not df_fresh_statuses_module.empty and "status" in df_fresh_statuses_module.columns:
                                        display_status_chart(df_fresh_statuses_module)
                                    else:
                                        st.info("Не удалось получить статусы карточек для модуля.")
                                else:
                                    st.info("В уроках этого модуля нет карточек.")
                            else:
                                st.info("Не найдено карточек для уроков этого модуля.")
                        else:
                            st.info("Не найдено ID уроков для выбранного модуля.")
                    else:
                        st.info("Не удалось получить ID уроков для выбранного модуля.")
                except Exception as e:
                    st.error(f"Ошибка при загрузке статусов карточек для модуля: {e}")
            else:
                st.info("В этом модуле нет уроков для анализа статусов.")
        else:
            st.info("Данные о статусах карточек недоступны для этого модуля.")
        # --- КОНЕЦ ИЗМЕНЕНИЙ ДЛЯ ГРАФИКА СТАТУСОВ МОДУЛЯ ---
    
    # 3. Визуализируем уроки в виде столбчатой диаграммы
    st.subheader("📊 Уроки модуля")
    
    # Агрегируем данные по урокам
    # Если df_module уже содержит уникальные уроки, то agg - это просто df_module с нужными колонками
    # Предполагаем, что df_module - это уже список уроков для текущего модуля
    agg_lessons_display = df_module[["lesson_name", "risk", "success_rate", "complaint_rate", "discrimination_avg", "cards_count", "lesson_order"]].copy()
    agg_lessons_display.rename(columns={'success_rate': 'success', 'complaint_rate': 'complaints', 'discrimination_avg': 'discrimination', 'cards_count': 'cards'}, inplace=True)
        
    # Сортируем уроки по порядку
    if "lesson_order" in agg_lessons_display.columns:
        agg_lessons_display = agg_lessons_display.sort_values("lesson_order")
    else:
        agg_lessons_display = agg_lessons_display.sort_values("risk", ascending=False)
    
    # Добавляем последовательную нумерацию
    agg_lessons_display = agg_lessons_display.reset_index(drop=True)
    agg_lessons_display["lesson_num"] = agg_lessons_display.index + 1
    
    # Создаем столбчатую диаграмму риска по урокам
    fig = px.bar(
        agg_lessons_display,
        x="lesson_num",
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={"lesson_num": "Номер урока", "risk": "Риск"},
        title="Уровень риска по урокам",
        hover_data=["lesson_name", "success", "complaints", "discrimination", "cards"]
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
        xaxis_tickangle=0
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 4. Детальное сравнение уроков
    st.subheader("📊 Детальное сравнение уроков")
    
    # Создаем вкладки для разных представлений
    tabs = st.tabs(["Метрики уроков", "Успешность и жалобы", "Радарная диаграмма"])
    
    with tabs[0]:
        # График сравнения нескольких метрик
        agg_metrics = df_module.groupby("lesson_name").agg(
            success_rate=("success_rate", "mean"),
            complaint_rate=("complaint_rate", "mean"),
            discrimination_avg=("discrimination_avg", "mean"),
            risk=("risk", "mean")
        ).reset_index()
        
        # Добавляем последовательную нумерацию для групп заданий
        if "lesson_order" in df_module.columns:
            lesson_order = df_module.groupby("lesson_name")["lesson_order"].first().reset_index()
            agg_metrics = agg_metrics.merge(lesson_order, on="lesson_name", how="left")
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
            id_vars=["lesson_name", "lesson_num"],
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
            x="lesson_num",
            y="value",
            color="metric_name",
            barmode="group",
            hover_data=["lesson_name"],
            labels={
                "lesson_num": "Номер урока",
                "value": "Значение",
                "metric_name": "Метрика"
            },
            title="Сравнение ключевых метрик по урокам"
        )
        
        fig_metrics.update_layout(
            yaxis_tickformat=".1%",
            xaxis_tickangle=0
        )
        
        st.plotly_chart(fig_metrics, use_container_width=True)
    
    with tabs[1]:
        # График зависимости успешности и жалоб
        display_success_complaints_chart(df_module, "lesson_name", limit=20)
    
    with tabs[2]:
        # Радарная диаграмма для топ-5 уроков с высоким риском
        display_completion_radar(df_module, "lesson_name", limit=5)
    
    # 5. Таблица с уроками
    st.subheader("📋 Детальная информация по урокам")
    
    # Улучшенная таблица с уроками
    # detailed_df = agg[["lesson_num", "lesson_name", "risk", "success", "complaints", "discrimination", "cards"]]
    detailed_df = agg_lessons_display[["lesson_num", "lesson_name", "risk", "success", "complaints", "discrimination", "cards"]]
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
        use_container_width=True,
        hide_index=True
    )
    
    # 6. Список уроков с кликабельными ссылками
    st.subheader("📖 Список уроков")
    # display_clickable_items(df_module, "lesson_name", "lesson", metrics=["cards", "risk", "success"])
    display_clickable_items(df_module, "lesson_name", "lesson", metrics=["cards_count", "risk", "success_rate"])
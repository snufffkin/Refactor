# pages/programs.py с обновленной нумерацией для графиков
"""
Страница программы (Обзор + навигация по модулям)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import psycopg2 # Добавлено для работы с БД
from db_config import get_cloud_dsn # Добавлено для подключения к БД

import core
from components.utils import create_hierarchical_header, display_clickable_items
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart
import navigation_utils

def page_programs(df: pd.DataFrame):
    """Страница программы с детализацией по модулям"""
    print(f"[page_programs] В начале: filter_program = {st.session_state.get('filter_program')}")
    print(f"[page_programs] Входной DataFrame df is None: {df is None}, df is empty: {df.empty if df is not None else 'N/A'}")

    if df is None or df.empty:
        st.warning("Нет данных о модулях для отображения.")
        return

    # Функция для получения статуса программы из БД
    @st.cache_data(ttl=300) # Кэшируем результат на 5 минут
    def get_program_status(program_name_to_find: str):
        conn = None
        try:
            dsn = get_cloud_dsn()
            conn = psycopg2.connect(dsn)
            cur = conn.cursor()
            cur.execute(
                "SELECT program_id, program_active_status FROM program_ids WHERE program_name = %s",
                (program_name_to_find,)
            )
            result = cur.fetchone()
            cur.close()
            if result:
                return result[0], result[1] # program_id, program_active_status
            return None, None
        except psycopg2.Error as e:
            st.error(f"Ошибка подключения к БД или выполнения запроса: {e}")
            return None, None
        finally:
            if conn:
                conn.close()

    # Переименование столбцов из mv_module_stats в ожидаемый формат
    column_mapping = {
        "avg_success_rate": "success_rate",
        "avg_first_try_success_rate": "first_try_success_rate",
        "avg_complaint_rate": "complaint_rate",
        "avg_discrimination": "discrimination_avg", # Имя совпадает
        "avg_risk": "risk",
        "avg_time_median": "time_median",
        # total_gz будет использован для cards_count
    }
    df = df.rename(columns=column_mapping)

    # Создание cards_count на основе total_gz или длины gz_ids
    if 'total_gz' in df.columns:
        df['cards_count'] = df['total_gz']
    elif 'gz_ids' in df.columns:
        df['cards_count'] = df['gz_ids'].apply(lambda x: len(x) if isinstance(x, (list, np.ndarray)) else 0)
    else:
        df['cards_count'] = 0 # По умолчанию, если нет данных для подсчета

    # Фильтруем данные по выбранной программе
    prog_name = st.session_state.get('filter_program')
    if not prog_name:
        st.warning("Программа не выбрана. Пожалуйста, выберите программу на странице обзора.")
        # Можно показать список всех программ для выбора или перенаправить
        # Отображение всех модулей всех программ, если программа не выбрана (менее предпочтительно)
        # df_prog = df
        return 
    
    # Получаем статус программы
    program_id, program_active_status = get_program_status(prog_name)

    # Отображаем значок статуса программы
    if program_active_status is not None:
        if program_active_status:
            st.badge("Программа активна", icon=":material/check_circle:", color="green")
        else:
            st.badge("Программа не активна", icon=":material/cancel:", color="red")
    else:
        # Если статус не удалось получить, можно вывести сообщение или ничего не делать
        # st.caption("Статус программы не определен")
        pass # Не выводим ничего, если статус не получен

    # Применяем фильтр программы к уже переименованному df
    df_prog = df[df["program_name"] == prog_name].copy() # Используем program_name из mv_module_stats
    
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
    # Для compare_with также нужно передать df с переименованными колонками и cards_count
    # display_metrics_row(df_prog, compare_with=df) 
    # Пока уберем compare_with, чтобы упростить, или нужно убедиться, что df правильно подготовлен
    display_metrics_row(df_prog) 
    
    # Добавляем метрику среднего суммарного времени на урок
    # Эта логика специфична для уроков, а у нас данные модулей.
    # Пересмотрим или уберем.
    # Если есть time_median (среднее для модуля) и total_lessons (в модуле)
    if 'time_median' in df_prog.columns and 'total_lessons' in df_prog.columns and not df_prog.empty:
        # Расчет среднего времени на урок для выбранной программы
        # Суммируем общее время по всем модулям программы и делим на общее кол-во уроков
        total_time_all_modules = (df_prog['time_median'] * df_prog['total_lessons']).sum()
        total_lessons_in_program = df_prog['total_lessons'].sum()
        avg_time_per_lesson_in_program = (total_time_all_modules / total_lessons_in_program) / 60 if total_lessons_in_program > 0 else 0
        
        st.subheader("⏱️ Среднее время на урок в программе")
        st.metric(
            label="Среднее время на урок (мин)",
            value=f"{avg_time_per_lesson_in_program:.1f}"
        )
    
    # 2. Отображаем распределение риска и статусы
    col1, col2 = st.columns(2)
    
    with col1:
        display_risk_distribution(df_prog, "module_name")
    
    with col2:
        # display_status_chart(df_prog, "module_name") # Закомментировано, т.к. status отсутствует
        st.info("Данные о статусах модулей/карточек недоступны на этом уровне.")
    
    # 3. Визуализируем модули в виде столбчатой диаграммы
    st.subheader("📊 Модули программы")
    
    # Агрегируем данные по модулям
    agg = df_prog.groupby("module_name").agg(
        risk=("risk", "mean"),
        success=("success_rate", "mean"),
        complaints=("complaint_rate", "mean"),
        discrimination=("discrimination_avg", "mean"),
        cards=("cards_count", "sum") # Используем cards_count
    ).reset_index()
    
    # Сортируем модули по порядку
    if "module_order" in df_prog.columns:
        module_order = df_prog.groupby("module_name")["module_order"].first().reset_index()
        agg = agg.merge(module_order, on="module_name", how="left")
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
        hover_data=["module_name", "success", "complaints", "discrimination", "cards"]  # Добавляем реальное название в подсказку
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
        display_success_complaints_chart(df_prog, "module_name")
    
    with tab2:
        # График сравнения нескольких метрик
        agg_metrics = df_prog.groupby("module_name").agg(
            success_rate=("success_rate", "mean"),
            complaint_rate=("complaint_rate", "mean"),
            discrimination_avg=("discrimination_avg", "mean"),
            risk=("risk", "mean")
        ).reset_index()
        
        # Добавляем последовательную нумерацию 
        if "module_order" in df_prog.columns:
            module_order = df_prog.groupby("module_name")["module_order"].first().reset_index()
            agg_metrics = agg_metrics.merge(module_order, on="module_name", how="left")
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
            id_vars=["module_name", "module_num"],
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
            hover_data=["module_name"],  # Показываем реальное название в подсказке
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
    detailed_df = agg[["module_num", "module_name", "risk", "success", "complaints", "discrimination", "cards"]]
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
    # display_clickable_items(df_prog, "module_name", "module", metrics=["cards", "risk", "success"])
    # display_clickable_items теперь ожидает cards_count или card_id внутри себя.
    # Передаем df_prog, который уже содержит cards_count и переименованные метрики.
    # Метрики, которые мы хотим видеть: 'cards_count', 'risk', 'success_rate'
    display_clickable_items(df_prog, "module_name", "module", metrics=["cards_count", "risk", "success_rate"]) 
    
    # 7. Если модуль выбран, показываем встроенную страницу уроков
    if st.session_state.get("filter_module"):
        from .lessons import _page_lessons_inline
        
        # Добавляем разделитель
        st.markdown("---")
        _page_lessons_inline(df)
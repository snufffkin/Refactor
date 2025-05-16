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
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution, display_overall_card_risk_stats
from components.charts import display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart
import navigation_utils
from components.utils import display_programs_by_class

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
        - **Успешность с первой попытки**: Процент заданий, решенных с первой попытки
        - **Жалобы**: Процент заданий, на которые поступили жалобы
        - **Дискриминативность**: Показатель способности задания различать знающих/незнающих студентов
        - **Риск**: Комплексный показатель проблемности задания (выше = хуже)
        - **Время**: Среднее время, затрачиваемое на выполнение задания
        """)
    
    if df is None or df.empty:
        st.warning("Нет данных для отображения.")
        return

    # Преобразуем имена столбцов, если необходимо (например, из mv_program_stats)
    # Это сделает остальной код более универсальным
    column_mapping = {
        "avg_success_rate": "success_rate",
        "avg_first_try_success_rate": "first_try_success_rate",
        "avg_complaint_rate": "complaint_rate",
        "avg_discrimination": "discrimination_avg", # уже совпадает, но для полноты
        "avg_risk": "risk",
        "avg_time_median": "time_median",
        # "total_cards": "cards_count" # если бы было такое поле
    }
    df = df.rename(columns=column_mapping)

    # Подсчет количества карточек, если столбец card_ids существует и является списком/массивом
    if 'card_ids' in df.columns:
        df['cards_count'] = df['card_ids'].apply(lambda x: len(x) if isinstance(x, (list, np.ndarray)) else 0)
    elif 'total_cards' in df.columns: # Обработка если поле total_cards уже есть
        df['cards_count'] = df['total_cards']
    else:
        # Если нет ни card_ids, ни total_cards, но есть total_gz, total_lessons, total_modules
        # Это агрегированные данные, и нам нужно поле для количества на текущем уровне
        # Для mv_program_stats, "program_name" является уникальным ключом строки.
        # Мы можем использовать количество модулей или уроков как прокси, или просто 1, если это обзор программ
        if 'total_modules' in df.columns: # Предполагаем, что это mv_program_stats
             df['cards_count'] = df['total_modules'] # Не совсем карточки, а скорее количество элементов следующего уровня
        else:
             df['cards_count'] = 1 # Если нет информации для подсчета

    # --- НОВЫЙ БЛОК ДЛЯ ОТОБРАЖЕНИЯ КОЛИЧЕСТВА ПРОГРАММ, УРОКОВ, КАРТОЧЕК ---
    st.subheader("📋 Общая статистика")
    
    num_programs = len(df)
    
    # Надежное вычисление total_num_lessons
    total_num_lessons = "N/A (уроки)" # Значение по умолчанию
    if 'total_lessons' in df.columns:
        lessons_series = pd.to_numeric(df['total_lessons'], errors='coerce')
        if lessons_series.notna().any():
            calculated_sum = lessons_series.sum()
            if pd.notna(calculated_sum) and isinstance(calculated_sum, (int, float, np.number)):
                total_num_lessons = calculated_sum
            else:
                total_num_lessons = "Ошибка данных (уроки)"
        else:
            total_num_lessons = 0 # Если все значения NaN или столбец пуст после конвертации
    
    # Надежное вычисление total_num_cards
    total_num_cards = "N/A (карточки)" # Значение по умолчанию
    if 'cards_count' in df.columns:
        cards_series = pd.to_numeric(df['cards_count'], errors='coerce')
        if cards_series.notna().any():
            calculated_sum_cards = cards_series.sum()
            if pd.notna(calculated_sum_cards) and isinstance(calculated_sum_cards, (int, float, np.number)):
                total_num_cards = calculated_sum_cards
            else:
                total_num_cards = "Ошибка данных (карточки)"
        else:
            total_num_cards = 0 # Если все значения NaN или столбец пуст после конвертации

    # Расчет уникальных карточек
    num_unique_cards = "N/A (уник.)"
    if 'card_ids' in df.columns:
        all_card_ids = []
        for id_list in df['card_ids'].dropna(): 
            if isinstance(id_list, (list, np.ndarray)):
                all_card_ids.extend(id_list)
            elif pd.notna(id_list) and isinstance(id_list, (int, float, np.number)):
                 all_card_ids.append(id_list)
        
        if all_card_ids:
            num_unique_cards = len(set(all_card_ids))
        elif isinstance(total_num_cards, (int, float, np.number)) and total_num_cards == 0:
             num_unique_cards = 0 # Если общее число карт 0, то и уникальных 0
        else:
            num_unique_cards = "Данных нет для уник." # Если card_ids был, но пуст или некорректен
    elif isinstance(total_num_cards, (int, float, np.number)) and pd.notna(total_num_cards):
        num_unique_cards = total_num_cards # Если нет card_ids, но есть числовое total_num_cards

    col1_stat, col2_stat, col3_stat = st.columns(3)
    with col1_stat:
        st.metric("Всего программ", f"{num_programs}")
    with col2_stat:
        metric_val_lessons = str(total_num_lessons)
        if isinstance(total_num_lessons, (int, float, np.number)) and pd.notna(total_num_lessons):
            metric_val_lessons = f"{total_num_lessons:,.0f}"
        st.metric("Всего уроков", metric_val_lessons)
    with col3_stat:
        display_total_val = str(total_num_cards)
        if isinstance(total_num_cards, (int, float, np.number)) and pd.notna(total_num_cards):
            display_total_val = f"{total_num_cards:,.0f}"
        
        unique_cards_suffix = ""
        if isinstance(num_unique_cards, (int, float, np.number)) and pd.notna(num_unique_cards):
            if isinstance(total_num_cards, (int, float, np.number)) and pd.notna(total_num_cards):
                if num_unique_cards != total_num_cards:
                    unique_cards_suffix = f" / {num_unique_cards:,.0f} (уник.)"
                elif total_num_cards > 0: # num_unique_cards == total_num_cards и не ноль
                    unique_cards_suffix = f" (все уник.)"
        elif isinstance(num_unique_cards, str) and num_unique_cards not in ["N/A (уник.)", "Данных нет для уник."]:
             unique_cards_suffix = f" / {num_unique_cards}"
            
        st.metric("Всего карточек", display_total_val + unique_cards_suffix)
    # --- КОНЕЦ НОВОГО БЛОКА ---

    # --- ИСПРАВЛЕННЫЙ ВЫЗОВ ДЛЯ СТАТИСТИКИ РИСКОВ КАРТОЧЕК ---
    # display_overall_card_risk_stats больше не требует project_id,
    # так как использует get_cloud_dsn() внутри.
    # Импорт display_overall_card_risk_stats должен быть в начале файла.
    display_overall_card_risk_stats() 
    # --- КОНЕЦ ИСПРАВЛЕННОГО ВЫЗОВА ---

    # Добавляем метрику среднего суммарного времени на урок
    if 'time_median' in df.columns and 'total_lessons' in df.columns and isinstance(total_num_lessons, (int, float)) and total_num_lessons > 0:
        # Для mv_program_stats, time_median это avg_time_median на программу.
        # Суммировать средние не совсем корректно, но для общей оценки допустимо.
        # Более точный расчет потребовал бы данных на уровне уроков.
        # Предполагаем, что time_median уже нормализовано (например, в минутах)
        
        # Убедимся, что time_median тоже числовой для корректного суммирования
        time_median_sum = 0
        if pd.api.types.is_numeric_dtype(df["time_median"]):
            time_median_sum = df["time_median"].sum()
        else:
            try:
                time_median_sum = pd.to_numeric(df["time_median"], errors='coerce').sum()
            except Exception:
                 pass # Оставим time_median_sum = 0, или можно вывести предупреждение

        if total_num_lessons > 0: # Повторная проверка после возможной ошибки конвертации total_lessons
             avg_time_per_lesson = time_median_sum / total_num_lessons
        else:
             avg_time_per_lesson = 0


        st.subheader("⏱️ Среднее время на урок")
        st.metric(
            label="Среднее суммарное время на урок (мин)",
            value=f"{avg_time_per_lesson:.1f}"
        )
    
    # 1. Отображаем общие метрики
    st.subheader("📈 Ключевые метрики")
    # display_metrics_row ожидает определенные имена, которые мы создали через rename
    display_metrics_row(df)
    
    # 2. Отображаем распределение риска
    col1, col2 = st.columns(2)
    
    with col1:
        # Распределение риска по категориям
        display_risk_distribution(df, "program_name")
    
    with col2:
        # Статусы карточек из таблицы card_status
        # Временно комментируем, так как 'status' отсутствует в mv_program_stats
        # if 'status' in df.columns:
        #     display_status_chart(df, "cards_count") # Используем cards_count вместо card_id для агрегированных данных
        # else:
        #     st.info("Данные о статусах карточек недоступны для этого уровня обзора.")
        pass # Оставляем колонку пустой или добавим другую диаграмму позже
    
    # Топ программ по уровню риска
    df_for_chart = df.copy()
    df_for_chart["program_full"] = df_for_chart["program_name"]
    df_for_chart["program"] = df_for_chart["program_name"]  # Временно используем полное название
    high_risk_programs = display_risk_bar_chart(
        df_for_chart, 
        "program", 
        value_column='risk', # Указываем столбец для значения риска
        title="Топ программ по уровню риска",
        height=800
    )
    
    # 4. Сравнение метрик для программ
    st.subheader("📊 Сравнение метрик по программам")
    
    tab1, tab2 = st.tabs(["Успешность и жалобы", "Метрики программ"])
    
    with tab1:
        # График сравнения успешности и жалоб
        # Убедимся, что display_success_complaints_chart использует переименованные колонки
        display_success_complaints_chart(df, "program_name", limit=20)
    
    with tab2:
        # График сравнения нескольких метрик
        # Убедимся, что display_metrics_comparison использует переименованные колонки
        display_metrics_comparison(
            df,
            "program_name",
            ["success_rate", "first_try_success_rate", "complaint_rate", "discrimination_avg", "risk"],
            limit=10
        )
    
    # 5. Список программ с кликабельными ссылками
    st.subheader("📚 Список программ")
    
    # Используем текущий df, который уже должен быть mv_program_stats с переименованными колонками
    # agg = df.groupby("program_name").agg({
    #     "success_rate": "mean",
    #     "first_try_success_rate": "mean",
    #     "complaint_rate": "mean",
    #     "discrimination_avg": "mean",
    #     "risk": "mean",
    #     "cards_count": "sum" # или max, если cards_count уже посчитан на программу
    # }).reset_index()
    # Поскольку df уже содержит агрегированные данные по программам (каждая строка - программа),
    # дополнительная группировка не нужна, если только мы не получали более детализированные данные.
    # Для mv_program_stats, df уже готов.
    
    agg_display_df = df[["program_name", "success_rate", "first_try_success_rate", "complaint_rate", "discrimination_avg", "risk", "cards_count"]].copy()
    
    # Создаем таблицу с метриками
    st.dataframe(
        agg_display_df.style.format({
            "success_rate": "{:.1%}",
            "first_try_success_rate": "{:.1%}",
            "complaint_rate": "{:.1%}",
            "discrimination_avg": "{:.2f}",
            "risk": "{:.2f}",
            "cards_count": "{:.0f}"
        }),
        use_container_width=True
    )
    
    # Отображаем программы, сгруппированные по классам
    # display_programs_by_class ожидает cards, risk, success_rate, first_try_success_rate
    display_programs_by_class(df, "program_name", metrics=["cards_count", "risk", "success_rate", "first_try_success_rate"])
    
    # 6. Дополнительная аналитика
    if st.checkbox("Показать дополнительную аналитику", value=False):
        st.subheader("📋 Дополнительная аналитика")
        
        # Добавляем график общего соотношения статусов карточек
        # Временно комментируем, так как 'status' отсутствует в mv_program_stats
        # if 'status' in df.columns:
        #     status_counts = df["status"].value_counts().reset_index()
        #     status_counts.columns = ["Статус", "Количество"]
        #     
        #     fig = px.pie(
        #         status_counts, 
        #         values="Количество", 
        #         names="Статус",
        #         title="Общее распределение по статусам",
        #         color="Статус",
        #         color_discrete_map={
        #             "new": "#d3d3d3",
        #             "in_work": "#add8e6",
        #             "ready_for_qc": "#fffacd",
        #             "done": "#90ee90",
        #             "wont_fix": "#f08080"
        #         }
        #     )
        #     st.plotly_chart(fig, use_container_width=True)
        # else:
        #     st.info("Данные о статусах карточек недоступны для этого уровня обзора.")
        
        # Распределение типов карточек
        # 'card_type' также отсутствует в mv_program_stats
        # if "card_type" in df.columns:
        #     card_type_counts = df["card_type"].value_counts().reset_index()
        #     card_type_counts.columns = ["Тип карточки", "Количество"]
        #     
        #     fig = px.bar(
        #         card_type_counts,
        #         x="Тип карточки",
        #         y="Количество",
        #         title="Распределение типов карточек"
        #     )
        #     
        #     st.plotly_chart(fig, use_container_width=True)
        # else:
        #    st.info("Данные о типах карточек недоступны для этого уровня обзора.")
        pass
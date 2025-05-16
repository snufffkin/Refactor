# pages/overview.py
"""
Страница обзора программ
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import psycopg2 # Добавлено для работы с БД
from db_config import get_cloud_dsn # Добавлено для подключения к БД
from sqlalchemy import create_engine, text # Добавлено для прямого выполнения SQL в этой странице

import core
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart
import navigation_utils
from components.utils import display_programs_by_class

# --- КОД, ПЕРЕНЕСЕННЫЙ ИЗ components/metrics.py ---
def display_overall_card_risk_stats_local(active_card_ids: list = None):
    """
    Отображает общую статистику по уровням риска карточек.
    Если active_card_ids предоставлен, фильтрует по этим ID.
    Эта версия функции локальна для pages/overview.py
    """
    
    where_clause = ""
    params = {}
    if active_card_ids is not None:
        if not active_card_ids: # Если список пуст (например, нет активных программ с карточками)
            st.info("Нет карточек для отображения статистики рисков по выбранным программам.")
            cols_risk_cards_empty = st.columns(5)
            for col in cols_risk_cards_empty:
                col.metric(label="...", value="0")
            return
        where_clause = "WHERE card_id = ANY(:active_card_ids_param)"
        params = {"active_card_ids_param": active_card_ids}

    query_sql_str = f"""
    SELECT
        COUNT(*) as total_cards,
        COALESCE(SUM(CASE WHEN risk IS NULL OR risk = 0 THEN 1 ELSE 0 END), 0) as no_risk_count,
        COALESCE(SUM(CASE WHEN risk > 0 AND risk <= 0.25 THEN 1 ELSE 0 END), 0) as low_risk_count,
        COALESCE(SUM(CASE WHEN risk > 0.25 AND risk <= 0.5 THEN 1 ELSE 0 END), 0) as moderate_risk_count,
        COALESCE(SUM(CASE WHEN risk > 0.5 AND risk <= 0.75 THEN 1 ELSE 0 END), 0) as high_risk_count,
        COALESCE(SUM(CASE WHEN risk > 0.75 THEN 1 ELSE 0 END), 0) as critical_risk_count
    FROM card_risk_cache
    {where_clause};
    """
    query_sql = text(query_sql_str)

    try:
        dsn = get_cloud_dsn()
        if not dsn:
            st.error("DSN для подключения к базе данных не получен.")
            return
            
        engine = create_engine(dsn)
        with engine.connect() as connection:
            df_risks = pd.read_sql_query(query_sql, connection, params=params)

        if not df_risks.empty and df_risks.iloc[0] is not None:
            results = df_risks.iloc[0]
            total_cards = int(results.get('total_cards', 0))
            no_risk_count = int(results.get('no_risk_count', 0))
            low_risk_count = int(results.get('low_risk_count', 0))
            moderate_risk_count = int(results.get('moderate_risk_count', 0))
            high_risk_count = int(results.get('high_risk_count', 0))
            critical_risk_count = int(results.get('critical_risk_count', 0))

            if total_cards > 0:
                no_risk_perc = (no_risk_count / total_cards) * 100
                low_risk_perc = (low_risk_count / total_cards) * 100
                moderate_risk_perc = (moderate_risk_count / total_cards) * 100
                high_risk_perc = (high_risk_count / total_cards) * 100
                critical_risk_perc = (critical_risk_count / total_cards) * 100
            else:
                no_risk_perc = low_risk_perc = moderate_risk_perc = high_risk_perc = critical_risk_perc = 0

            cols_risk_cards = st.columns(5)
            with cols_risk_cards[0]:
                st.metric(label="Без риска", value=f"{no_risk_count:,}")
            with cols_risk_cards[1]:
                st.metric(label="Низкий риск", value=f"{low_risk_count:,}")
            with cols_risk_cards[2]:
                st.metric(label="Умеренный риск", value=f"{moderate_risk_count:,}")
            with cols_risk_cards[3]:
                st.metric(label="Высокий риск", value=f"{high_risk_count:,}", delta_color="inverse")
            with cols_risk_cards[4]:
                st.metric(label="Критический риск", value=f"{critical_risk_count:,}", delta_color="inverse")
        else:
            st.warning("Данные о распределении рисков карточек не получены или пусты.")
            
    except ImportError as ie: # Хотя sqlalchemy импортируется выше, оставим на всякий случай
        st.error(f"Ошибка импорта для работы с БД: {ie}. Установите необходимые библиотеки (например, psycopg2-binary, sqlalchemy).")    
    except Exception as e:
        st.error(f"Ошибка при подключении к БД или выполнении запроса для статистики рисков: {e}")

def display_card_risk_categories_chart_local(active_card_ids: list = None):
    """
    Отображает столбчатую диаграмму распределения карточек по категориям риска.
    Если active_card_ids предоставлен, фильтрует по этим ID.
    Эта версия функции локальна для pages/overview.py
    """
    where_clause = ""
    params = {}
    if active_card_ids is not None:
        if not active_card_ids: # Если список пуст
            st.info("Нет карточек для отображения распределения рисков по выбранным программам.")
            fig = go.Figure()
            fig.update_layout(title="Распределение карточек по уровням риска", xaxis_title="Категория риска", yaxis_title="Количество карточек")
            st.plotly_chart(fig, use_container_width=True)
            return
        where_clause = "WHERE card_id = ANY(:active_card_ids_param)"
        params = {"active_card_ids_param": active_card_ids}
        
    query_sql_str = f"""
    SELECT
        COALESCE(SUM(CASE WHEN risk IS NULL OR risk = 0 THEN 1 ELSE 0 END), 0) as no_risk_count,
        COALESCE(SUM(CASE WHEN risk > 0 AND risk <= 0.25 THEN 1 ELSE 0 END), 0) as low_risk_count,
        COALESCE(SUM(CASE WHEN risk > 0.25 AND risk <= 0.5 THEN 1 ELSE 0 END), 0) as moderate_risk_count,
        COALESCE(SUM(CASE WHEN risk > 0.5 AND risk <= 0.75 THEN 1 ELSE 0 END), 0) as high_risk_count,
        COALESCE(SUM(CASE WHEN risk > 0.75 THEN 1 ELSE 0 END), 0) as critical_risk_count
    FROM card_risk_cache
    {where_clause};
    """
    query_sql = text(query_sql_str)
    
    st.subheader("📊 Распределение карточек по уровням риска")

    try:
        dsn = get_cloud_dsn()
        if not dsn:
            st.error("DSN для подключения к базе данных не получен.")
            return
            
        engine = create_engine(dsn)
        with engine.connect() as connection:
            df_risks_agg = pd.read_sql_query(query_sql, connection, params=params)

        if not df_risks_agg.empty and df_risks_agg.iloc[0] is not None:
            results = df_risks_agg.iloc[0]
            
            risk_data = {
                "Без риска": int(results.get('no_risk_count', 0)),
                "Низкий риск": int(results.get('low_risk_count', 0)),
                "Умеренный риск": int(results.get('moderate_risk_count', 0)),
                "Высокий риск": int(results.get('high_risk_count', 0)),
                "Критический риск": int(results.get('critical_risk_count', 0))
            }
            
            risk_distribution_df = pd.DataFrame(list(risk_data.items()), columns=["Категория риска", "Количество"])
            
            risk_order = ["Без риска", "Низкий риск", "Умеренный риск", "Высокий риск", "Критический риск"]
            risk_distribution_df["Категория риска"] = pd.Categorical(
                risk_distribution_df["Категория риска"], 
                categories=risk_order, 
                ordered=True
            )
            risk_distribution_df = risk_distribution_df.sort_values("Категория риска")
            
            color_map = {
                "Без риска": "#D3D3D3", 
                "Низкий риск": "#7FFF7F", 
                "Умеренный риск": "#FFFF7F", 
                "Высокий риск": "#FFAA7F", 
                "Критический риск": "#FF7F7F"
            }
            
            fig = px.bar(
                risk_distribution_df, 
                x="Категория риска", 
                y="Количество", 
                color="Категория риска", 
                color_discrete_map=color_map, 
                title="Распределение карточек по уровням риска" # Этот title может дублироваться с st.subheader выше
            )
            fig.update_layout(xaxis_title="Категория риска", yaxis_title="Количество карточек")
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.warning("Данные о распределении рисков карточек не получены или пусты для построения графика.")
            
    except ImportError as ie:
        st.error(f"Ошибка импорта для работы с БД: {ie}. Установите необходимые библиотеки (например, psycopg2-binary, sqlalchemy).")    
    except Exception as e:
        st.error(f"Ошибка при построении графика распределения рисков карточек: {e}")

# --- КОНЕЦ ПЕРЕНЕСЕННОГО КОДА ---

# Функция для получения списка активных программ
def get_active_programs():
    """Подключается к БД и возвращает список имен активных программ."""
    active_programs = []
    try:
        dsn = get_cloud_dsn()
        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT program_name FROM program_ids WHERE program_active_status = TRUE")
                results = cur.fetchall()
                active_programs = [row[0] for row in results]
    except Exception as e:
        st.error(f"Ошибка при подключении к базе данных или выполнении запроса: {e}")
    return active_programs

def page_overview(df: pd.DataFrame):
    """Страница с обзором всех программ"""
    st.header("📊 Обзор программ")
    
    # Переключатель для отображения только активных программ
    show_active_only = st.toggle("Показывать только активные программы", value=False) # value=False по умолчанию

    df_filtered = df.copy() # Работаем с копией, чтобы не изменять оригинальный df для других частей, если понадобится
    active_card_ids_list = None # Список ID карточек для фильтрации, None по умолчанию

    # Фильтрация DataFrame если переключатель включен
    if show_active_only:
        active_program_names = get_active_programs()
        if active_program_names:
            if "program_name" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["program_name"].isin(active_program_names)].copy()
                # Собираем ID карточек из отфильтрованного df_filtered
                if "card_ids" in df_filtered.columns and not df_filtered.empty:
                    all_card_ids_from_active = []
                    for ids_array in df_filtered["card_ids"].dropna():
                        if isinstance(ids_array, (list, np.ndarray)):
                            all_card_ids_from_active.extend(ids_array)
                        elif pd.notna(ids_array): # На случай если это одиночный ID, а не массив
                            all_card_ids_from_active.append(ids_array)
                    
                    if all_card_ids_from_active:
                        # Убираем дубликаты и конвертируем в int, если они еще не int
                        active_card_ids_list = [int(cid) for cid in set(all_card_ids_from_active) if pd.notna(cid)]
                    else:
                        # Если card_ids есть, но после обработки список пуст (например, все были NaN)
                        active_card_ids_list = [] # Пустой список, чтобы функции в metrics.py это обработали
            else:
                st.warning("Столбец 'program_name' не найден в данных для фильтрации по активным программам.")
        elif df is not None and not df.empty:
             st.info("Нет активных программ для отображения или не удалось получить список активных программ.")
             # df_filtered = pd.DataFrame() # Если нужно полностью очистить данные

    # Используем df_filtered далее для всех отображений
    # Вместо оригинального df
    
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
    
    if df_filtered is None or df_filtered.empty:
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
    df_filtered = df_filtered.rename(columns=column_mapping)

    # Подсчет количества карточек, если столбец card_ids существует и является списком/массивом
    if 'card_ids' in df_filtered.columns:
        df_filtered['cards_count'] = df_filtered['card_ids'].apply(lambda x: len(x) if isinstance(x, (list, np.ndarray)) else 0)
    elif 'total_cards' in df_filtered.columns: # Обработка если поле total_cards уже есть
        df_filtered['cards_count'] = df_filtered['total_cards']
    else:
        # Если нет ни card_ids, ни total_cards, но есть total_gz, total_lessons, total_modules
        # Это агрегированные данные, и нам нужно поле для количества на текущем уровне
        # Для mv_program_stats, "program_name" является уникальным ключом строки.
        # Мы можем использовать количество модулей или уроков как прокси, или просто 1, если это обзор программ
        if 'total_modules' in df_filtered.columns: # Предполагаем, что это mv_program_stats
             df_filtered['cards_count'] = df_filtered['total_modules'] # Не совсем карточки, а скорее количество элементов следующего уровня
        else:
             df_filtered['cards_count'] = 1 # Если нет информации для подсчета

    # --- НОВЫЙ БЛОК ДЛЯ ОТОБРАЖЕНИЯ КОЛИЧЕСТВА ПРОГРАММ, УРОКОВ, КАРТОЧЕК ---
    st.subheader("📋 Общая статистика")
    
    num_programs = len(df_filtered)
    
    # Надежное вычисление total_num_lessons
    total_num_lessons = "N/A (уроки)" # Значение по умолчанию
    if 'total_lessons' in df_filtered.columns:
        lessons_series = pd.to_numeric(df_filtered['total_lessons'], errors='coerce')
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
    if 'cards_count' in df_filtered.columns:
        cards_series = pd.to_numeric(df_filtered['cards_count'], errors='coerce')
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
    if 'card_ids' in df_filtered.columns:
        all_card_ids = []
        for id_list in df_filtered['card_ids'].dropna(): 
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

    col1_stat, col2_stat, col3_stat, col4_stat = st.columns(4)
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
            
        st.metric("Всего карточек", display_total_val)
    with col4_stat:
        display_total_val = str(total_num_cards)
        if isinstance(total_num_cards, (int, float, np.number)) and pd.notna(total_num_cards):
            display_total_val = f"{total_num_cards:,.0f}"
        
        unique_cards_suffix = ""
        if isinstance(num_unique_cards, (int, float, np.number)) and pd.notna(num_unique_cards):
            if isinstance(total_num_cards, (int, float, np.number)) and pd.notna(total_num_cards):
                if num_unique_cards != total_num_cards:
                    unique_cards_suffix = f"{num_unique_cards:,.0f}"
                elif total_num_cards > 0: # num_unique_cards == total_num_cards и не ноль
                    unique_cards_suffix = f""
        elif isinstance(num_unique_cards, str) and num_unique_cards not in ["N/A (уник.)", "Данных нет для уник."]:
             unique_cards_suffix = f"{num_unique_cards}"
            
        st.metric("Уникальных карточек", unique_cards_suffix)
    # --- КОНЕЦ НОВОГО БЛОКА ---

    # --- ИСПРАВЛЕННЫЙ ВЫЗОВ ДЛЯ СТАТИСТИКИ РИСКОВ КАРТОЧЕК ---
    # display_overall_card_risk_stats больше не требует project_id,
    # так как использует get_cloud_dsn() внутри.
    # Импорт display_overall_card_risk_stats должен быть в начале файла.
    display_overall_card_risk_stats_local(active_card_ids=active_card_ids_list) 
    # --- КОНЕЦ ИСПРАВЛЕННОГО ВЫЗОВА ---

    # Добавляем метрику среднего суммарного времени на урок
    if 'time_median' in df_filtered.columns and 'total_lessons' in df_filtered.columns and isinstance(total_num_lessons, (int, float)) and total_num_lessons > 0:
        # Для mv_program_stats, time_median это avg_time_median на программу.
        # Суммировать средние не совсем корректно, но для общей оценки допустимо.
        # Более точный расчет потребовал бы данных на уровне уроков.
        # Предполагаем, что time_median уже нормализовано (например, в минутах)
        
        # Убедимся, что time_median тоже числовой для корректного суммирования
        time_median_sum = 0
        if pd.api.types.is_numeric_dtype(df_filtered["time_median"]):
            time_median_sum = df_filtered["time_median"].sum()
        else:
            try:
                time_median_sum = pd.to_numeric(df_filtered["time_median"], errors='coerce').sum()
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
    display_metrics_row(df_filtered)
    
    # 2. Отображаем распределение риска
    col1, col2 = st.columns(2)
    
    with col1:
        # Распределение риска по категориям - теперь для карточек
        display_card_risk_categories_chart_local(active_card_ids=active_card_ids_list)
    
    with col2:
        # Статусы карточек из таблицы card_status
        # Временно комментируем, так как 'status' отсутствует в mv_program_stats
        # if 'status' in df_filtered.columns:
        #     display_status_chart(df_filtered, "cards_count") # Используем cards_count вместо card_id для агрегированных данных
        # else:
        #     st.info("Данные о статусах карточек недоступны для этого уровня обзора.")
        pass # Оставляем колонку пустой или добавим другую диаграмму позже
    
    # Топ программ по уровню риска
    df_for_chart = df_filtered.copy()
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
        display_success_complaints_chart(df_filtered, "program_name", limit=20)
    
    with tab2:
        # График сравнения нескольких метрик
        # Убедимся, что display_metrics_comparison использует переименованные колонки
        display_metrics_comparison(
            df_filtered,
            "program_name",
            ["success_rate", "first_try_success_rate", "complaint_rate", "discrimination_avg", "risk"],
            limit=10
        )
    
    # 5. Список программ с кликабельными ссылками
    st.subheader("📚 Список программ")
    
    # Используем текущий df_filtered, который уже должен быть mv_program_stats с переименованными колонками
    # agg = df_filtered.groupby("program_name").agg({
    #     "success_rate": "mean",
    #     "first_try_success_rate": "mean",
    #     "complaint_rate": "mean",
    #     "discrimination_avg": "mean",
    #     "risk": "mean",
    #     "cards_count": "sum" # или max, если cards_count уже посчитан на программу
    # }).reset_index()
    # Поскольку df_filtered уже содержит агрегированные данные по программам (каждая строка - программа),
    # дополнительная группировка не нужна, если только мы не получали более детализированные данные.
    # Для mv_program_stats, df_filtered уже готов.
    
    agg_display_df = df_filtered[["program_name", "success_rate", "first_try_success_rate", "complaint_rate", "discrimination_avg", "risk", "cards_count"]].copy()
    
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
    display_programs_by_class(df_filtered, "program_name", metrics=["cards_count", "risk", "success_rate", "first_try_success_rate"])
    
    # 6. Дополнительная аналитика
    if st.checkbox("Показать дополнительную аналитику", value=False):
        st.subheader("📋 Дополнительная аналитика")
        
        # Добавляем график общего соотношения статусов карточек
        # Временно комментируем, так как 'status' отсутствует в mv_program_stats
        # if 'status' in df_filtered.columns:
        #     status_counts = df_filtered["status"].value_counts().reset_index()
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
        # if "card_type" in df_filtered.columns:
        #     card_type_counts = df_filtered["card_type"].value_counts().reset_index()
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
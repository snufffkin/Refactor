# pages/lessons.py с обновленной нумерацией для графиков
"""
Страница урока (Обзор + навигация по группам заданий)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from sqlalchemy.sql import text
from sqlalchemy.orm import sessionmaker

import core
from components.utils import create_hierarchical_header, display_clickable_items
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart, display_completion_radar
import navigation_utils

def page_lessons(df: pd.DataFrame):
    """Страница урока с детализацией по группам заданий"""
    prog_name = st.session_state.get('filter_program')
    module_name = st.session_state.get('filter_module')
    lesson_name = st.session_state.get('filter_lesson')

    if not prog_name or not module_name or not lesson_name:
        st.warning("Программа, модуль или урок не выбраны.")
        return

    if df is None or df.empty:
        st.warning("Нет данных о группах заданий для отображения.")
        return

    # Переименование столбцов из mv_gz_stats в ожидаемый формат
    # Поля program_name, module_name, lesson_name и т.д. должны быть добавлены в core.load_gz_data через JOIN
    column_mapping = {
        "avg_success_rate": "success_rate",
        "avg_first_try_success_rate": "first_try_success_rate",
        "avg_complaint_rate": "complaint_rate",
        "avg_discrimination": "discrimination_avg",
        "avg_risk": "risk",
        "avg_time_median": "time_median",
        "total_cards": "cards_count" # Используем total_cards из mv_gz_stats для cards_count
    }
    df = df.rename(columns=column_mapping)
    
    # Фильтруем данные по выбранной программе, модулю и уроку
    # df уже должен содержать отфильтрованные ГЗ по этим параметрам из core.load_gz_data
    # Однако, если core.load_gz_data возвращает больше, чем нужно, дополнительная фильтрация тут:
    df_lesson = df[
        (df["program_name"] == prog_name) &
        (df["module_name"] == module_name) &
        (df["lesson_name"] == lesson_name)
    ].copy()
    
    if df_lesson.empty:
        st.warning(f"Нет данных для урока '{lesson_name}' в модуле '{module_name}', программа '{prog_name}'")
        return
    
    create_hierarchical_header(
        levels=["program", "module", "lesson"],
        values=[prog_name, module_name, lesson_name]
    )
    
    st.subheader("📈 Метрики урока")
    # df_module_for_compare = df[
    #     (df["program_name"] == prog_name) &
    #     (df["module_name"] == module_name)
    # ] # Это будут все ГЗ модуля для сравнения
    # display_metrics_row(df_lesson, compare_with=df_module_for_compare) # Пока упростим
    display_metrics_row(df_lesson)
    
    if 'time_median' in df_lesson.columns and not df_lesson.empty:
        total_time_gz = df_lesson["time_median"].sum() / 60 # Суммарное среднее время всех ГЗ урока в минутах
        st.subheader("⏱️ Суммарное медианное время выполнения ГЗ урока")
        st.metric(
            label="Время на ГЗ урока (мин)",
            value=f"{total_time_gz:.1f}"
        )
    
    col1, col2 = st.columns(2)
    with col1:
        if "gz_name" in df_lesson.columns:
             display_risk_distribution(df_lesson, "gz_name")
        else:
            st.info("Нет данных о названиях ГЗ для распределения риска.")
    
    with col2:
        # display_status_chart(df_lesson, "gz_name") # Status не доступен
        # st.info("Данные о статусах ГЗ недоступны на этом уровне.")
        # --- НАЧАЛО ИЗМЕНЕНИЙ ДЛЯ ГРАФИКА СТАТУСОВ УРОКА ---
        if not df_lesson.empty and "gz_id" in df_lesson.columns:
            lesson_gz_ids = df_lesson["gz_id"].dropna().unique().tolist()
            if lesson_gz_ids:
                try:
                    engine = core.get_engine()
                    # 1. Получить все card_id для ГЗ этого урока
                    # Мы не можем использовать card_ids_query напрямую, так как он требует lesson_id, 
                    # а у нас есть gz_ids. Нужно получить card_id из cards_structure по gz_id
                    
                    # Формируем строку с плейсхолдерами для gz_ids
                    gz_id_placeholders = ", ".join([f":gz_id_{i}" for i in range(len(lesson_gz_ids))])
                    params_card_ids = {f"gz_id_{i}": gz_id for i, gz_id in enumerate(lesson_gz_ids)}

                    cards_for_lesson_query = text(f"""
                        SELECT DISTINCT card_id 
                        FROM cards_structure 
                        WHERE gz_id IN ({gz_id_placeholders})
                    """)
                    
                    df_card_ids_for_lesson = pd.read_sql(cards_for_lesson_query, engine, params=params_card_ids)
                    
                    if not df_card_ids_for_lesson.empty and "card_id" in df_card_ids_for_lesson.columns:
                        card_ids_list = df_card_ids_for_lesson["card_id"].dropna().unique().tolist()
                        if card_ids_list:
                            # 2. Получить свежие статусы для этих карточек
                            df_fresh_statuses_lesson = core.get_fresh_card_statuses(engine, card_ids_list)
                            if not df_fresh_statuses_lesson.empty and "status" in df_fresh_statuses_lesson.columns:
                                # 3. Отобразить график статусов
                                display_status_chart(df_fresh_statuses_lesson) # Передаем DataFrame только со статусами
                            else:
                                st.info("Не удалось получить статусы карточек для урока.")
                        else:
                            st.info("В ГЗ этого урока нет карточек.")
                    else:
                        st.info("Не найдено карточек для ГЗ этого урока.")
                except Exception as e:
                    st.error(f"Ошибка при загрузке статусов карточек для урока: {e}")
            else:
                st.info("В этом уроке нет ГЗ для анализа статусов.")
        elif "status" in df_lesson.columns: # Если вдруг статусы есть напрямую (маловероятно для агрегированных данных урока)
             display_status_chart(df_lesson)
        else:
            st.info("Данные о статусах карточек недоступны для этого урока.")
        # --- КОНЕЦ ИЗМЕНЕНИЙ ДЛЯ ГРАФИКА СТАТУСОВ УРОКА ---
    
    st.subheader("📊 Группы заданий")
    
    if "gz_name" not in df_lesson.columns or df_lesson.empty:
        st.info("Нет групп заданий для отображения в этом уроке.")
    else:
        # Предполагаем, что df_lesson уже содержит уникальные ГЗ для текущего урока
        # Колонки из mv_gz_stats + program_name, module_name, lesson_name из join
        # Нужны: gz_name, risk, success_rate, complaint_rate, discrimination_avg, cards_count (был total_cards)
        # lesson_order, module_order не нужны для сортировки ГЗ внутри урока, gz_name должно быть достаточно или gz_id
        
        # Используем gz_id для hover_data если есть, иначе gz_name
        # hover_name_col = "gz_id" if "gz_id" in df_lesson.columns else "gz_name"

        # Для hover_data всегда будем передавать gz_name, если он есть.
        # gz_id можно добавить дополнительно, если он существует и отличается.
        columns_for_agg_display = ["gz_name", "risk", "success_rate", "complaint_rate", "discrimination_avg", "cards_count"]
        if "gz_id" in df_lesson.columns:
            columns_for_agg_display.append("gz_id")
        if "lesson_order" in df_lesson.columns: # lesson_order не используется для ГЗ, но если бы был gz_order
            columns_for_agg_display.append("lesson_order") # или gz_order
        
        # Убираем дубликаты столбцов, если gz_id == gz_name
        columns_for_agg_display = sorted(list(set(columns_for_agg_display)))
        
        # Убедимся, что все столбцы существуют в df_lesson
        columns_for_agg_display = [col for col in columns_for_agg_display if col in df_lesson.columns]

        agg_gz_display = df_lesson[columns_for_agg_display].copy()
        
        # Функция для сокращения названий ГЗ
        def shorten_gz_name(name):
            """Сокращает длинные названия ГЗ"""
            if pd.isna(name):
                return name
            name = str(name).strip()
            # Словарь замен
            replacements = {
                "Презентация": "Пр.",
                "презентация": "Пр.",
                "Рабочая тетрадь": "РТ",
                "рабочая тетрадь": "РТ",
                "Дополнительное задание": "Доп.",
                "дополнительное задание": "Доп.",
                "Дополнительные материалы": "Доп.",
                "дополнительные материалы": "Доп.",
                "Дополнительные задания": "Доп.",
                "дополнительные задания": "Доп."
            }
            # Применяем замены
            for full, short in replacements.items():
                if full in name:
                    name = name.replace(full, short)
            return name
        
        # Сохраняем полные названия для hover_data
        agg_gz_display['gz_name_full'] = agg_gz_display['gz_name'].copy()
        # Применяем сокращения для отображения
        agg_gz_display['gz_name'] = agg_gz_display['gz_name'].apply(shorten_gz_name)
        
        agg_gz_display.rename(columns={
            'success_rate': 'success',
            'complaint_rate': 'complaints',
            'discrimination_avg': 'discrimination',
            'cards_count': 'cards'
        }, inplace=True)
        
        # Сортировка ГЗ (например, по имени или риску)
        agg_gz_display = agg_gz_display.sort_values("risk", ascending=False).reset_index(drop=True)
        agg_gz_display["gz_num"] = agg_gz_display.index + 1
        
        hover_data_cols = ["gz_name_full", "success", "complaints", "discrimination", "cards"]
        if "gz_id" in agg_gz_display.columns and "gz_id" not in hover_data_cols:
            hover_data_cols.insert(1, "gz_id") # Вставим gz_id после gz_name_full для подсказки

        fig = px.bar(
            agg_gz_display,
            x="gz_name",
            y="risk",
            color="risk",
            color_continuous_scale="RdYlGn_r",
            labels={"gz_name": "Группа заданий", "risk": "Риск"},
            title="Уровень риска по группам заданий",
            hover_data=hover_data_cols 
        )
        fig.add_hline(y=0.3, line_dash="dash", line_color="green", annotation_text="Низкий риск", annotation_position="left")
        fig.add_hline(y=0.5, line_dash="dash", line_color="gold", annotation_text="Средний риск", annotation_position="left")
        fig.add_hline(y=0.7, line_dash="dash", line_color="red", annotation_text="Высокий риск", annotation_position="left")
        
        # Собираем hovertemplate динамически
        hovertemplate = "<b>ГЗ: %{customdata[0]}</b><br>"
        if "gz_id" in hover_data_cols and hover_data_cols[1] == "gz_id":
            hovertemplate += "ID: %{customdata[1]}<br>"
            current_customdata_idx = 2
        else:
            current_customdata_idx = 1

        hovertemplate += (
            "Название: %{x}<br>" +
            "Риск: %{y:.2f}<br>" +
            f"Успешность: %{{customdata[{current_customdata_idx}]:.1%}}<br>" +
            f"Жалобы: %{{customdata[{current_customdata_idx+1}]:.1%}}<br>" +
            f"Дискриминативность: %{{customdata[{current_customdata_idx+2}]:.2f}}<br>" +
            f"Карточек: %{{customdata[{current_customdata_idx+3}]}}"
        )
        fig.update_traces(hovertemplate=hovertemplate)
        fig.update_layout(xaxis_title="Группа заданий", yaxis_title="Риск", xaxis_tickangle=0)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📊 Детальное сравнение групп заданий")
        tabs = st.tabs(["Ключевые метрики", "Успешность и жалобы", "Радарная диаграмма"])
        
        # Данные для вкладок - это df_lesson (уже отфильтрованные ГЗ урока)
        # Убедимся, что нужные колонки (после rename) используются в функциях компонентов
        with tabs[0]:
            # display_metrics_comparison(df_lesson, "gz_name", ["success_rate", "complaint_rate", "discrimination_avg", "risk"], limit=15)
            # Создаем agg_metrics локально для графика, чтобы он использовал gz_num
            tab_agg_metrics = df_lesson.groupby("gz_name").agg(
                success_rate=("success_rate", "mean"),
                complaint_rate=("complaint_rate", "mean"),
                discrimination_avg=("discrimination_avg", "mean"),
                risk=("risk", "mean")
            ).reset_index()
            tab_agg_metrics = tab_agg_metrics.sort_values("risk", ascending=False).reset_index(drop=True)
            tab_agg_metrics["gz_num"] = tab_agg_metrics.index + 1
            tab_agg_metrics = tab_agg_metrics.head(15)
            # Применяем сокращения названий
            tab_agg_metrics['gz_name_full'] = tab_agg_metrics['gz_name'].copy()
            tab_agg_metrics['gz_name'] = tab_agg_metrics['gz_name'].apply(shorten_gz_name)
            melted_df_tab = pd.melt(
                tab_agg_metrics, 
                id_vars=["gz_name", "gz_num", "gz_name_full"],
                value_vars=["success_rate", "complaint_rate", "discrimination_avg", "risk"],
                var_name="metric", value_name="value"
            )
            metric_names_tab = {"success_rate": "Успешность", "complaint_rate": "Жалобы", "discrimination_avg": "Дискриминативность", "risk": "Риск"}
            melted_df_tab["metric_name"] = melted_df_tab["metric"].map(metric_names_tab)
            fig_metrics_tab = px.bar(melted_df_tab, x="gz_name", y="value", color="metric_name", barmode="group",
                                 labels={"gz_name": "Группа заданий", "value": "Значение", "metric_name": "Метрика"}, 
                                 title="Сравнение метрик по ГЗ",
                                 hover_data=["gz_name_full"])
            # Обновляем hover template
            fig_metrics_tab.update_traces(
                hovertemplate="<b>%{customdata[0]}</b><br>" +
                             "Метрика: %{data.name}<br>" +
                             "Значение: %{y:.1%}<br>" +
                             "<extra></extra>"
            )
            fig_metrics_tab.update_layout(yaxis_tickformat=".1%", xaxis_tickangle=0)
            st.plotly_chart(fig_metrics_tab, use_container_width=True)

        with tabs[1]:
            # Подготавливаем данные с сокращенными названиями для графика
            df_lesson_short = df_lesson.copy()
            df_lesson_short['gz_name_full'] = df_lesson_short['gz_name']
            df_lesson_short['gz_name'] = df_lesson_short['gz_name'].apply(shorten_gz_name)
            display_success_complaints_chart(df_lesson_short, "gz_name", limit=20)
        
        with tabs[2]:
            # Подготавливаем данные с сокращенными названиями для радара
            df_lesson_radar = df_lesson.copy()
            df_lesson_radar['gz_name_full'] = df_lesson_radar['gz_name']
            df_lesson_radar['gz_name'] = df_lesson_radar['gz_name'].apply(shorten_gz_name)
            display_completion_radar(df_lesson_radar, "gz_name", limit=5)
        
        st.subheader("📋 Детальная информация по группам заданий")
        # detailed_df_gz = agg_gz_display[["gz_num", "gz_name", "risk", "success", "complaints", "discrimination", "cards"]]
        # Переименовываем обратно для отображения, если нужно, или используем изначальные имена из agg_gz_display
        
        # Добавляем total_complaints в agg_gz_display, если он есть в df_lesson
        # Предполагаем, что df_lesson может содержать total_complaints из mv_gz_stats
        if 'total_complaints' in df_lesson.columns:
            # Нужен merge, так как agg_gz_display это результат группировки df_lesson по gz_name
            # и total_complaints может быть разным для ГЗ с одинаковым gz_name, если gz_id различается (хотя это маловероятно)
            # Более безопасный способ - если total_complaints это свойство ГЗ, то он должен быть в df_lesson на уровне каждой ГЗ.
            # Если total_complaints уже агрегирован (например, сумма по всем карточкам ГЗ), то можно просто взять .first()
            # Для простоты, если total_complaints есть в df_lesson (после переименования из mv_gz_stats), 
            # то он должен быть и в agg_gz_display после группировки (если он числовой, то sum/mean/first)
            # Уточним: mv_gz_stats уже содержит агрегированные данные по ГЗ.
            # Значит, total_complaints в df_lesson (если пришел оттуда) уже является агрегированным.
            # Мы делали rename: df = df.rename(columns=column_mapping)
            # Если total_complaints не был переименован, он останется total_complaints.
            # agg_gz_display = df_lesson[columns_for_agg_display].copy()
            # columns_for_agg_display должен включать total_complaints
            # Давайте модифицируем columns_for_agg_display ранее
            
            # Однако, agg_gz_display уже создан ранее. 
            # Мы можем добавить total_complaints в detailed_df_gz из исходного df_lesson, смерджив по gz_name
            if 'gz_name' in df_lesson.columns and 'total_complaints' in df_lesson.columns:
                # Берем первое значение total_complaints для каждой группы, т.к. mv_gz_stats уже агрегирован
                gz_total_complaints = df_lesson.groupby('gz_name')['total_complaints'].first().reset_index()
                # Мерджим с agg_gz_display, который уже содержит gz_name и gz_num
                agg_gz_display = pd.merge(agg_gz_display, gz_total_complaints, on='gz_name', how='left')

        # Используем полные названия для таблицы
        detailed_df_gz = agg_gz_display.rename(columns={'gz_num': 'Номер', 'gz_name_full': 'Группа заданий', 'risk': 'Риск', 'success': 'Успешность', 'complaints': 'Жалобы (%)', 'discrimination': 'Дискриминативность', 'cards': 'Карточек'})
        
        # Колонки для отображения
        # Порядок важен и будет сохранен
        cols_for_display = ["Номер", "Группа заданий", "Риск", "Успешность", "Жалобы (%)"]
        if 'total_complaints' in detailed_df_gz.columns:
            detailed_df_gz["Общее кол-во жалоб"] = detailed_df_gz['total_complaints'].fillna(0).astype(int)
            cols_for_display.append("Общее кол-во жалоб")
        else:
             # Если total_complaints не удалось добавить, создаем столбец с N/A
            detailed_df_gz["Общее кол-во жалоб"] = "N/A"
            cols_for_display.append("Общее кол-во жалоб")
            
        cols_for_display.extend(["Дискриминативность", "Карточек"])
        
        # Убедимся, что все колонки из cols_for_display существуют в detailed_df_gz
        # и сохраняем порядок
        final_display_cols = [col for col in cols_for_display if col in detailed_df_gz.columns]
        detailed_df_gz_display = detailed_df_gz[final_display_cols]
        
        # detailed_df_gz_display.columns = ["Номер", "Группа заданий", "Риск", "Успешность", "Жалобы (%)", "Дискриминативность", "Карточек"]
        # Переименование уже сделано через rename и cols_for_display

        style_format = {
            "Риск": "{:.2f}", 
            "Успешность": "{:.1%}", 
            "Жалобы (%)": "{:.1%}", 
            "Дискриминативность": "{:.2f}"
        }
        if "Общее кол-во жалоб" in detailed_df_gz_display.columns and detailed_df_gz_display["Общее кол-во жалоб"].dtype != 'object':
            style_format["Общее кол-во жалоб"] = "{:d}" # Формат для целых чисел

        st.dataframe(
            detailed_df_gz_display.style.format(style_format).background_gradient(subset=["Риск"], cmap="RdYlGn_r"),
            use_container_width=True,
            hide_index=True
        )
        
        st.subheader("🧩 Список групп заданий")
        display_clickable_items(df_lesson, "gz_name", "gz", metrics=["cards_count", "risk", "success_rate"]) 

    # Отзывы учителей (остается как есть, если prog_name, module_name, lesson_name корректны)
    st.subheader(" Отзывы учителей")

    # Загружаем отзывы из БД
    engine = core.get_engine()
    
    # Используем параметризованный запрос для безопасности
    sql_query_reviews = text("""
        SELECT *
        FROM teacher_reviews
        WHERE program_name = :prog_name
          AND module_name = :module_name
          AND lesson_name = :lesson_name
    """)
    params_reviews = {
        "prog_name": prog_name,
        "module_name": module_name,
        "lesson_name": lesson_name
    }
    
    try:
        df_reviews = pd.read_sql(sql_query_reviews, engine, params=params_reviews)
    except Exception as e:
        st.error(f"Ошибка при загрузке отзывов учителей: {e}")
        df_reviews = pd.DataFrame() # Возвращаем пустой DataFrame в случае ошибки

    if df_reviews.empty:
        st.info("Нет отзывов учителей для этого урока")
    else:
        row = df_reviews.iloc[0]
        
        # Создаем блок с основными метриками в виде нативных компонентов Streamlit
        st.markdown("### Основные метрики")
        
        # Отображаем основные метрики в три колонки
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Просто отображаем значение без дельты
            st.metric("Общая оценка", f"{row['overall_stat']:.1f}")
        
        with col2:
            st.metric("Интересность", f"{row['interest_stat']:.1f}")
        
        with col3:
            # Для сложности: показываем отклонение от оптимальной сложности (3.0)
            delta = 3.0 - row["complexity_stat"]
            # Отклонение от идеальной сложности должно быть отрицательной дельтой, если слишком сложно,
            # и положительной, если слишком просто
            delta_text = f"{delta:.1f}"
            # Если сложность близка к оптимальной (2.5-3.5), не показываем дельту
            if 2.5 <= row["complexity_stat"] <= 3.5:
                st.metric("Сложность", f"{row['complexity_stat']:.1f}")
            else:
                st.metric("Сложность", f"{row['complexity_stat']:.1f}", delta_text, delta_color="inverse")
        
        # Вторая строка метрик
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Презентация", f"{row['presentation_rate']:.1f}")
        
        with col2:
            st.metric("Рабочая тетрадь", f"{row['workbook_rate']:.1f}")
        
        with col3:
            st.metric("Доп. материалы", f"{row['addmaterial_rate']:.1f}")
        
        # Функция для создания карточки отзыва
        def create_review_card(text, is_positive=True):
            bg_color = "rgba(47, 120, 80, 0.1)" if is_positive else "rgba(180, 60, 60, 0.1)"
            border_color = "rgba(47, 120, 80, 0.5)" if is_positive else "rgba(180, 60, 60, 0.5)"
            
            return f"""
            <div style="
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 8px;
                margin-bottom: 8px;
                font-size: 0.9em;
            ">
                {text}
            </div>
            """
        
        # Функция для отображения отзывов в 2 колонки внутри основной колонки
        def display_reviews_in_subcols(reviews, is_positive=True):
            if pd.isna(reviews) or reviews == '':
                st.info("Нет отзывов")
                return
            
            # Разделяем отзывы по переносу строки и убираем пустые строки
            items = [item.strip() for item in reviews.split('\n') if item.strip()]
            if not items:
                st.info("Нет отзывов")
                return
            
            # Разделяем отзывы на две подколонки
            subcol1, subcol2 = st.columns(2)
            
            # Распределяем отзывы поровну между подколонками
            half = len(items) // 2 + (1 if len(items) % 2 != 0 else 0)
            
            # Первая подколонка
            with subcol1:
                for i in range(half):
                    st.markdown(create_review_card(items[i], is_positive), unsafe_allow_html=True)
            
            # Вторая подколонка
            with subcol2:
                for i in range(half, len(items)):
                    st.markdown(create_review_card(items[i], is_positive), unsafe_allow_html=True)
        
        # Отображаем текстовые отзывы в виде вкладок
        st.markdown("### Детальные отзывы учителей")
        
        # Инициализация вкладок
        tabs = st.tabs(["Презентация", "Рабочая тетрадь", "Доп. материалы", "Интересность", "Сложность", "AI-суммаризация"])
        
        # Отзывы о презентации
        with tabs[0]:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Что понравилось")
                display_reviews_in_subcols(row["presentation_like"], is_positive=True)
            with col2:
                st.subheader("Что не понравилось")
                display_reviews_in_subcols(row["presentation_dislike"], is_positive=False)

        # Отзывы о рабочей тетради
        with tabs[1]:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Что понравилось")
                display_reviews_in_subcols(row["workbook_like"], is_positive=True)
            with col2:
                st.subheader("Что не понравилось")
                display_reviews_in_subcols(row["workbook_dislike"], is_positive=False)

        # Отзывы о дополнительных материалах
        with tabs[2]:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Что понравилось")
                display_reviews_in_subcols(row["addmaterial_like"], is_positive=True)
            with col2:
                st.subheader("Что не понравилось")
                display_reviews_in_subcols(row["addmaterial_dislike"], is_positive=False)

        # Отзывы об интересности
        with tabs[3]:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Что понравилось")
                display_reviews_in_subcols(row["interest_like"], is_positive=True)
            with col2:
                st.subheader("Что не понравилось")
                display_reviews_in_subcols(row["interest_dislike"], is_positive=False)

        # Отзывы о сложности
        with tabs[4]:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Как упростить")
                display_reviews_in_subcols(row["complexity_to_simplify"], is_positive=False)
            with col2:
                st.subheader("Как усложнить")
                display_reviews_in_subcols(row["complexity_to_complicate"], is_positive=True)

        # AI-суммаризация отзывов
        with tabs[5]:
            if "ai_summarization" in row and pd.notna(row["ai_summarization"]):
                try:
                    ai_data = row["ai_summarization"]
                    if isinstance(ai_data, str):
                        import json
                        ai_data = json.loads(ai_data)
                    
                    # Функция для отображения элементов с приоритетом
                    def display_priority_items(items, title):
                        """Отображает список элементов с цветовой кодировкой приоритета"""
                        if not items:
                            return
                        
                        st.markdown(f"**{title}**")
                        for item in items:
                            if isinstance(item, str):
                                # Определяем цвет фона по эмодзи приоритета
                                if item.startswith("🔴"):
                                    bg_color = "rgba(255, 82, 82, 0.1)"
                                    border_color = "rgba(255, 82, 82, 0.3)"
                                elif item.startswith("🟠"):
                                    bg_color = "rgba(255, 159, 64, 0.1)"
                                    border_color = "rgba(255, 159, 64, 0.3)"
                                elif item.startswith("🟡"):
                                    bg_color = "rgba(255, 205, 86, 0.1)"
                                    border_color = "rgba(255, 205, 86, 0.3)"
                                elif item.startswith("🟢"):
                                    bg_color = "rgba(75, 192, 192, 0.1)"
                                    border_color = "rgba(75, 192, 192, 0.3)"
                                else:
                                    bg_color = "rgba(200, 200, 200, 0.1)"
                                    border_color = "rgba(200, 200, 200, 0.3)"
                                
                                st.markdown(f"""
                                <div style="
                                    background-color: {bg_color};
                                    border: 1px solid {border_color};
                                    border-radius: 4px;
                                    padding: 8px;
                                    margin-bottom: 4px;
                                    font-size: 0.9em;
                                ">
                                    {item}
                                </div>
                                """, unsafe_allow_html=True)
                    
                    # Общая сводка
                    if "summary" in ai_data:
                        summary = ai_data["summary"]
                        st.markdown("### 📊 Общая сводка")
                        
                        # Основной вывод
                        if "main_conclusion" in summary:
                            st.info(summary["main_conclusion"])
                        
                        # Создаем вкладки для приоритетных улучшений и рекомендаций
                        summary_tabs = st.tabs(["Приоритетные улучшения", "Рекомендации"])
                        
                        with summary_tabs[0]:
                            # Приоритетные улучшения
                            if "priority_improvements" in summary:
                                display_priority_items(summary["priority_improvements"], "Приоритетные улучшения:")
                        
                        with summary_tabs[1]:
                            # Объединенные рекомендации
                            st.markdown("#### Рекомендации по улучшению урока")
                            
                            # Собираем все рекомендации в один список с категориями
                            if "methodist_action_items" in ai_data:
                                actions = ai_data["methodist_action_items"]
                                
                                if "immediate_fixes" in actions and actions["immediate_fixes"]:
                                    display_priority_items(actions["immediate_fixes"], "Срочные исправления:")
                                
                                if "content_additions" in actions and actions["content_additions"]:
                                    display_priority_items(actions["content_additions"], "Добавить контент:")
                                
                                if "structural_changes" in actions and actions["structural_changes"]:
                                    display_priority_items(actions["structural_changes"], "Структурные изменения:")
                                
                                if "content_removals" in actions and actions["content_removals"]:
                                    display_priority_items(actions["content_removals"], "Удалить контент:")
                                
                                if "assessment_recommendations" in actions and actions["assessment_recommendations"]:
                                    display_priority_items(actions["assessment_recommendations"], "Рекомендации по оценке:")
                            
                            if "teacher_recommendations" in ai_data:
                                teacher_recs = ai_data["teacher_recommendations"]
                                
                                if "engagement_ideas" in teacher_recs and teacher_recs["engagement_ideas"]:
                                    display_priority_items(teacher_recs["engagement_ideas"], "Идеи для вовлечения:")
                                
                                if "content_improvements" in teacher_recs and teacher_recs["content_improvements"]:
                                    display_priority_items(teacher_recs["content_improvements"], "Улучшение контента:")
                                
                                if "complexity_adjustments" in teacher_recs and teacher_recs["complexity_adjustments"]:
                                    display_priority_items(teacher_recs["complexity_adjustments"], "Корректировка сложности:")
                                
                                if "methodology_suggestions" in teacher_recs and teacher_recs["methodology_suggestions"]:
                                    display_priority_items(teacher_recs["methodology_suggestions"], "Методические предложения:")
                    
                    # Сильные стороны и проблемы
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### 💪 Сильные стороны")
                        if "key_strengths" in ai_data:
                            strengths = ai_data["key_strengths"]
                            
                            # Презентация
                            if "presentation" in strengths and strengths["presentation"]:
                                display_priority_items(strengths["presentation"], "Презентация:")
                            
                            # Рабочая тетрадь
                            if "workbook" in strengths and strengths["workbook"]:
                                display_priority_items(strengths["workbook"], "Рабочая тетрадь:")
                            
                            # Педагогическая ценность
                            if "pedagogical_value" in strengths and strengths["pedagogical_value"]:
                                display_priority_items(strengths["pedagogical_value"], "Педагогическая ценность:")
                            
                            # Дополнительные материалы
                            if "additional_materials" in strengths and strengths["additional_materials"]:
                                display_priority_items(strengths["additional_materials"], "Дополнительные материалы:")
                    
                    with col2:
                        st.markdown("### ⚠️ Выявленные проблемы")
                        if "identified_issues" in ai_data:
                            issues = ai_data["identified_issues"]
                            
                            # Презентация
                            if "presentation" in issues and issues["presentation"]:
                                display_priority_items(issues["presentation"], "Презентация:")
                            
                            # Рабочая тетрадь
                            if "workbook" in issues and issues["workbook"]:
                                display_priority_items(issues["workbook"], "Рабочая тетрадь:")
                            
                            # Баланс сложности
                            if "complexity_balance" in issues and issues["complexity_balance"]:
                                display_priority_items(issues["complexity_balance"], "Баланс сложности:")
                            
                            # Дополнительные материалы
                            if "additional_materials" in issues and issues["additional_materials"]:
                                display_priority_items(issues["additional_materials"], "Дополнительные материалы:")
                    
                    # Паттерны и инсайты
                    if "patterns_and_insights" in ai_data:
                        st.markdown("### 🔍 Паттерны и инсайты")
                        patterns = ai_data["patterns_and_insights"]
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if "teacher_consensus" in patterns:
                                display_priority_items(patterns["teacher_consensus"], "Консенсус учителей:")
                            
                            if "successful_elements" in patterns:
                                display_priority_items(patterns["successful_elements"], "Успешные элементы:")
                        
                        with col2:
                            if "common_difficulties" in patterns:
                                display_priority_items(patterns["common_difficulties"], "Общие сложности:")
                            
                            if "controversial_points" in patterns:
                                display_priority_items(patterns["controversial_points"], "Спорные моменты:")
                    
                except Exception as e:
                    st.error(f"Ошибка при обработке AI-суммаризации: {e}")
                    st.text("Данные AI-суммаризации:")
                    st.json(row["ai_summarization"])
            else:
                st.info("AI-суммаризация для этого урока пока недоступна")

    st.subheader("🛠️ Управление статусами карточек урока")

    # Возможные статусы для карточек
    # TODO: Получать эти статусы из базы данных или конфигурационного файла, если они могут меняться
    POSSIBLE_CARD_STATUSES = ["new", "in_work", "review", "done", "archive"]
    
    selected_status = st.selectbox(
        "Выберите новый статус для ВСЕХ карточек этого урока:",
        options=POSSIBLE_CARD_STATUSES,
        index=0  # По умолчанию выбран первый статус
    )

    if st.button("Применить статус ко всем карточкам урока"):
        if prog_name and module_name and lesson_name:
            try:
                engine = core.get_engine()
                Session = sessionmaker(bind=engine)
                session = Session()

                # 1. Получить lesson_id
                lesson_id_query = text("""
                    SELECT lesson_id FROM lesson_ids
                    WHERE program_name = :prog_name AND module_name = :module_name AND lesson_name = :lesson_name
                """)
                lesson_id_result = session.execute(lesson_id_query, {"prog_name": prog_name, "module_name": module_name, "lesson_name": lesson_name}).fetchone()

                if lesson_id_result:
                    current_lesson_id = lesson_id_result[0]

                    # 2. Получить все card_id для этого lesson_id из cards_structure
                    cards_query = text("""
                        SELECT card_id FROM cards_structure
                        WHERE lesson_id = :lesson_id
                    """)
                    cards_result = session.execute(cards_query, {"lesson_id": current_lesson_id}).fetchall()
                    
                    card_ids_to_update = [row[0] for row in cards_result if row[0] is not None]

                    if card_ids_to_update:
                        # 3. Обновить статус для каждой карточки в card_status
                        # Мы будем обновлять существующие записи или вставлять новые, если карточки нет в card_status
                        
                        # Сначала получим существующие card_id в card_status для этого урока
                        existing_card_ids_in_status_table_query = text("""
                            SELECT cs.card_id 
                            FROM card_status cs
                            JOIN cards_structure cstruct ON cs.card_id = cstruct.card_id
                            WHERE cstruct.lesson_id = :lesson_id
                        """)
                        existing_cards_in_status_table_result = session.execute(existing_card_ids_in_status_table_query, {"lesson_id": current_lesson_id}).fetchall()
                        existing_card_ids_set = {row[0] for row in existing_cards_in_status_table_result}

                        cards_to_update_in_status = []
                        cards_to_insert_in_status = []

                        for card_id in card_ids_to_update:
                            if card_id in existing_card_ids_set:
                                cards_to_update_in_status.append(card_id)
                            else:
                                cards_to_insert_in_status.append(card_id)
                        
                        current_user_for_db = st.session_state.get("username", "system_bulk_update") 
                        current_user_id = st.session_state.get("user_id", 1)  # ID пользователя для card_assignments
                        
                        if cards_to_update_in_status:
                            update_stmt = text("""
                                UPDATE card_status
                                SET status = :new_status, updated_by = :user, updated_at = NOW()
                                WHERE card_id = ANY(:card_ids)
                            """)
                            session.execute(update_stmt, {"new_status": selected_status, "user": current_user_for_db, "card_ids": cards_to_update_in_status})
                        
                        if cards_to_insert_in_status:
                            # Для вставки нужно подготовить список словарей
                            insert_data = [
                                {
                                    "card_id": c_id, 
                                    "status": selected_status, 
                                    "updated_by": current_user_for_db, 
                                    "updated_at": pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M:%S%z') 
                                } for c_id in cards_to_insert_in_status
                            ]
                            # Предполагается, что таблица card_status существует и имеет столбцы card_id, status, updated_by, updated_at
                            # Используем более явную вставку. `text()` не очень хорошо работает с `execute_many` или аналогами в SQLAlchemy Core без ORM моделей.
                            # Будем вставлять по одной записи, если их немного, или подготовим батч инсерт если их много.
                            # Для простоты примера пока что вставляем по одной, хотя это не оптимально для большого количества.
                            for data_item in insert_data:
                                insert_stmt = text("""
                                    INSERT INTO card_status (card_id, status, updated_by, updated_at)
                                    VALUES (:card_id, :status, :updated_by, :updated_at)
                                    ON CONFLICT (card_id) DO UPDATE 
                                    SET status = EXCLUDED.status, 
                                        updated_by = EXCLUDED.updated_by, 
                                        updated_at = EXCLUDED.updated_at;
                                """)
                                session.execute(insert_stmt, data_item)
                        
                        # Синхронизация с card_assignments (как в cards.py)
                        for card_id in card_ids_to_update:
                            # Проверяем, есть ли уже назначение для этой карточки
                            assignment = session.execute(text(
                                "SELECT assignment_id FROM card_assignments WHERE card_id = :card_id"
                            ), {"card_id": card_id}).fetchone()
                            
                            if assignment:
                                # Если есть назначение, обновляем статус
                                assignment_id = assignment[0]
                                session.execute(text("""
                                    UPDATE card_assignments
                                    SET status = :status, updated_at = CURRENT_TIMESTAMP
                                    WHERE assignment_id = :assignment_id
                                """), {
                                    "status": selected_status,
                                    "assignment_id": assignment_id
                                })
                            else:
                                # Если нет назначения, создаем его
                                session.execute(text("""
                                    INSERT INTO card_assignments (card_id, user_id, status) 
                                    VALUES (:card_id, :user_id, :status)
                                """), {
                                    "card_id": card_id,
                                    "user_id": current_user_id,
                                    "status": selected_status
                                })
                                
                        session.commit()
                        st.success(f"Статус '{selected_status}' успешно применен к {len(card_ids_to_update)} карточкам урока.")

                        # Очистка кэша перед rerun
                        if hasattr(core, 'load_raw_data'):
                            core.load_raw_data.clear()
                        if hasattr(core, 'process_data'):
                            core.process_data.clear()
                        if hasattr(core, 'load_card_data'):
                            core.load_card_data.clear()
                        if hasattr(core, 'load_gz_data'): # Данные для ГЗ также могут зависеть от статусов карточек
                            core.load_gz_data.clear()
                        if hasattr(core, 'load_all_data_for_level'):
                            core.load_all_data_for_level.clear()

                        st.rerun() # Добавляем rerun для обновления интерфейса
                    else:
                        st.info("В этом уроке нет карточек для обновления.")
                else:
                    st.error(f"Не удалось найти ID для урока: {lesson_name}")
                
                session.close()
            except Exception as e:
                st.error(f"Ошибка при обновлении статусов карточек: {e}")
                if 'session' in locals() and session.is_active:
                    session.rollback()
                    session.close()
        else:
            st.warning("Необходимо выбрать программу, модуль и урок для применения статуса.")

# Встроенная версия страницы уроков для использования в других страницах
def _page_lessons_inline(df: pd.DataFrame):
    """Встроенная версия страницы уроков для отображения на странице модуля"""
    # Фильтруем данные по выбранной программе и модулю
    df_mod = core.apply_filters(df, ["program", "module"])
    
    # Проверка наличия данных после фильтрации
    if df_mod.empty:
        mod_name = st.session_state.get('filter_module') or '—'
        st.warning(f"Нет данных для модуля '{mod_name}'")
        return
    
    # Заголовок
    st.subheader("🏫 Уроки выбранного модуля")
    
    # Агрегируем данные по урокам
    agg = df_mod.groupby("lesson").agg(
        risk=("risk", "mean"),
        success=("success_rate", "mean"),
        complaints=("complaint_rate", "mean"),
        cards=("card_id", "nunique")
    ).reset_index()
    
    # Сортируем уроки по порядку, если есть такая колонка
    if "lesson_order" in df_mod.columns:
        lesson_order = df_mod.groupby("lesson")["lesson_order"].first().reset_index()
        agg = agg.merge(lesson_order, on="lesson", how="left")
        agg = agg.sort_values("lesson_order")
    else:
        # Если нет колонки с порядком, сортируем по риску
        agg = agg.sort_values("risk", ascending=False)
    
    # Добавляем последовательную нумерацию
    agg = agg.reset_index(drop=True)
    agg["lesson_num"] = agg.index + 1
    
    # Создаем график
    fig = px.bar(
        agg,
        x="lesson_num",  # Используем последовательную нумерацию вместо ID
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={"lesson_num": "Номер урока", "risk": "Риск"},
        title="Уровень риска по урокам",
        hover_data=["lesson", "success", "complaints", "cards"]  # Добавляем реальный ID в подсказку
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
    
    # Таблица с уроками
    table_df = agg[["lesson_num", "lesson", "risk", "success", "complaints", "cards"]]
    table_df.columns = ["Номер", "Урок", "Риск", "Успешность", "Жалобы", "Карточек"]
    
    st.dataframe(
        table_df.style.format({
            "Риск": "{:.2f}",
            "Успешность": "{:.1%}",
            "Жалобы": "{:.1%}"
        }),
        use_container_width=True,
        hide_index=True
    )
    
    # Список кликабельных уроков
    display_clickable_items(df_mod, "lesson", "lesson", metrics=["cards", "risk"])
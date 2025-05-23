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
        st.info("Данные о статусах ГЗ недоступны на этом уровне.")
    
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
        
        # Добавляем радарную диаграмму для общего обзора метрик
        st.markdown("### Сравнение метрик")
        
        # Создаем радарную диаграмму для метрик
        radar_data = pd.DataFrame({
            'Метрика': ['Общая оценка', 'Интересность', 'Рабочая тетрадь', 'Презентация', 'Доп. материалы'],
            'Значение': [row["overall_stat"], row["interest_stat"], row["workbook_rate"], 
                        row["presentation_rate"], row["addmaterial_rate"]]
        })
        
        # Отображаем радарную диаграмму
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=radar_data['Значение'],
            theta=radar_data['Метрика'],
            fill='toself',
            name='Оценки',
            line_color='rgb(77, 166, 255)'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 5]
                )
            ),
            title="Радар оценок материалов",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
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
        tabs = st.tabs(["Презентация", "Рабочая тетрадь", "Доп. материалы", "Интересность", "Сложность"])
        
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
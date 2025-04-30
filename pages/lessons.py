# pages/lessons.py с обновленной нумерацией для графиков
"""
Страница урока (Обзор + навигация по группам заданий)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

import core
from components.utils import create_hierarchical_header, display_clickable_items
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart, display_completion_radar
import navigation_utils

def page_lessons(df: pd.DataFrame):
    """Страница урока с детализацией по группам заданий"""
    # Фильтруем данные по выбранной программе, модулю и уроку
    df_lesson = core.apply_filters(df, ["program", "module", "lesson"])
    program_filter = st.session_state.get('filter_program')
    module_filter = st.session_state.get('filter_module')
    lesson_filter = st.session_state.get('filter_lesson')
    
    # Создаем иерархический заголовок
    create_hierarchical_header(
        levels=["program", "module", "lesson"],
        values=[program_filter, module_filter, lesson_filter]
    )
    
    # Проверка наличия данных после фильтрации
    if df_lesson.empty:
        st.warning(f"Нет данных для урока '{lesson_filter}' в модуле '{module_filter}'")
        return
    
    # 1. Отображаем общие метрики урока
    st.subheader("📈 Метрики урока")
    display_metrics_row(df_lesson, compare_with=df)
    
    # 2. Отображаем распределение риска и статусы
    col1, col2 = st.columns(2)
    
    with col1:
        display_risk_distribution(df_lesson, "gz")
    
    with col2:
        display_status_chart(df_lesson, "gz")
    
    # 3. Визуализируем группы заданий в виде столбчатой диаграммы
    st.subheader("📊 Группы заданий")
    
    # Агрегируем данные по группам заданий
    agg = df_lesson.groupby("gz").agg(
        risk=("risk", "mean"),
        success=("success_rate", "mean"),
        complaints=("complaint_rate", "mean"),
        discrimination=("discrimination_avg", "mean"),
        cards=("card_id", "nunique")
    ).reset_index()
    
    # Добавляем последовательную нумерацию для групп заданий
    agg = agg.sort_values("risk", ascending=False).reset_index(drop=True)
    agg["gz_num"] = agg.index + 1  # Нумерация с 1
    
    # Создаем столбчатую диаграмму риска по группам заданий с использованием порядковых номеров
    fig = px.bar(
        agg,
        x="gz_num",  # Используем последовательную нумерацию вместо ID
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={"gz_num": "Номер группы заданий", "risk": "Риск"},
        title="Уровень риска по группам заданий",
        hover_data=["gz", "success", "complaints", "discrimination", "cards"]  # Добавляем реальный ID в подсказку
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
        hovertemplate="<b>ГЗ: %{customdata[0]}</b><br>" +
                      "Номер: %{x}<br>" +
                      "Риск: %{y:.2f}<br>" +
                      "Успешность: %{customdata[1]:.1%}<br>" +
                      "Жалобы: %{customdata[2]:.1%}<br>" +
                      "Дискриминативность: %{customdata[3]:.2f}<br>" +
                      "Карточек: %{customdata[4]}"
    )
    
    fig.update_layout(
        xaxis_title="Номер группы заданий",
        yaxis_title="Риск",
        xaxis_tickangle=0  # Убираем наклон, т.к. числа компактны
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 4. Детальное сравнение групп заданий
    st.subheader("📊 Детальное сравнение групп заданий")
    
    # Создаем вкладки для разных представлений
    tabs = st.tabs(["Ключевые метрики", "Успешность и жалобы", "Радарная диаграмма"])
    
    with tabs[0]:
        # График сравнения нескольких метрик - используем нумерацию вместо ID
        agg_metrics = df_lesson.groupby("gz").agg(
            success_rate=("success_rate", "mean"),
            complaint_rate=("complaint_rate", "mean"),
            discrimination_avg=("discrimination_avg", "mean"),
            risk=("risk", "mean")
        ).reset_index()
        
        # Добавляем последовательную нумерацию для групп заданий
        agg_metrics = agg_metrics.sort_values("risk", ascending=False).reset_index(drop=True)
        agg_metrics["gz_num"] = agg_metrics.index + 1
        
        # Ограничиваем количество групп для отображения
        agg_metrics = agg_metrics.head(15)
        
        # Переводим в формат "длинных данных" для графика
        melted_df = pd.melt(
            agg_metrics, 
            id_vars=["gz", "gz_num"],
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
            x="gz_num",  # Используем порядковые номера вместо ID
            y="value",
            color="metric_name",
            barmode="group",
            hover_data=["gz"],  # Показываем реальный ID в подсказке
            labels={
                "gz_num": "Номер группы заданий",
                "value": "Значение",
                "metric_name": "Метрика"
            },
            title="Сравнение ключевых метрик по группам заданий"
        )
        
        # Настраиваем формат оси Y в зависимости от метрики
        fig_metrics.update_layout(
            yaxis_tickformat=".1%",
            xaxis_tickangle=0  # Убираем наклон, т.к. числа компактны
        )
        
        st.plotly_chart(fig_metrics, use_container_width=True)
    
    with tabs[1]:
        # График зависимости успешности и жалоб
        display_success_complaints_chart(df_lesson, "gz", limit=20)
    
    with tabs[2]:
        # Радарная диаграмма для топ-5 групп заданий с высоким риском
        display_completion_radar(df_lesson, "gz", limit=5)
    
    # 5. Таблица с группами заданий
    st.subheader("📋 Детальная информация по группам заданий")
    
    # Улучшенная таблица с группами заданий, добавляем номер для соответствия с графиком
    detailed_df = agg[["gz_num", "gz", "risk", "success", "complaints", "discrimination", "cards"]]
    detailed_df.columns = ["Номер", "Группа заданий", "Риск", "Успешность", "Жалобы", "Дискриминативность", "Карточек"]
    
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
    
    # 6. Список групп заданий с кликабельными ссылками
    st.subheader("🧩 Список групп заданий")
    display_clickable_items(df_lesson, "gz", "gz", metrics=["cards", "risk", "success"])
    
    # 7. Если урок выбран, показываем встроенную страницу ГЗ
    if st.session_state.get("filter_lesson"):
        from .gz import _page_gz_inline
        
        # Добавляем разделитель
        st.markdown("---")
        _page_gz_inline(df)
    # Улучшенный блок для отображения отзывов учителей в 4 колонки
    st.subheader("📝 Отзывы учителей")

    # Загружаем отзывы из БД
    engine = core.get_engine()
    query = f"SELECT * FROM teacher_reviews WHERE program = '{program_filter}' AND module = '{module_filter}' AND lesson = '{lesson_filter}'"
    df_reviews = pd.read_sql(query, engine)

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
        use_container_width=True
    )
    
    # Список кликабельных уроков
    display_clickable_items(df_mod, "lesson", "lesson", metrics=["cards", "risk"])
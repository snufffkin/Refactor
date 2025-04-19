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

# Модификация функции page_gz в pages/gz.py
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
    
    # Создаем столбчатую диаграмму риска по карточкам
    fig = px.bar(
        df_gz,
        x="card_id",
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={"card_id": "ID карточки", "risk": "Риск"},
        title="Уровень риска по карточкам",
        hover_data=["success_rate", "complaint_rate", "discrimination_avg", "card_type"]
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
        hovertemplate="<b>ID: %{x}</b><br>" +
                      "Риск: %{y:.2f}<br>" +
                      "Успешность: %{customdata[0]:.1%}<br>" +
                      "Жалобы: %{customdata[1]:.1%}<br>" +
                      "Дискриминативность: %{customdata[2]:.2f}<br>" +
                      "Тип: %{customdata[3]}"
    )
    
    fig.update_layout(
        xaxis_title="ID карточки",
        yaxis_title="Риск",
        xaxis_tickangle=-45 if len(df_gz) > 8 else 0
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 4. Детальное сравнение карточек
    st.subheader("📊 Детальное сравнение карточек")
    
    # Создаем вкладки для разных представлений
    tabs = st.tabs(["Ключевые метрики", "Успешность и жалобы", "Типы карточек"])
    
    with tabs[0]:
        # График сравнения нескольких метрик для карточек
        fig = px.bar(
            df_gz,
            x="card_id",
            y=["success_rate", "first_try_success_rate", "complaint_rate"],
            barmode="group",
            color_discrete_sequence=["#4da6ff", "#ff9040", "#ff6666"],
            labels={
                "card_id": "ID карточки", 
                "value": "Значение", 
                "variable": "Метрика"
            },
            title="Сравнение ключевых метрик по карточкам"
        )
        
        # Настройки осей
        fig.update_layout(
            xaxis_tickangle=-45 if len(df_gz) > 8 else 0,
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
    
    # Создаем кликабельные ссылки на карточки, если доступны URL
    if "card_url" in df_gz.columns:
        cards_df_display = cards_df.copy()
        cards_df_display["Карточка"] = df_gz.apply(
            lambda row: f"[ID:{int(row['card_id'])}]({row['card_url']})" if pd.notna(row['card_url']) else f"ID:{int(row['card_id'])}", 
            axis=1
        )
        
        # Создаем DataFrame для отображения с более понятными названиями колонок
        formatted_df = pd.DataFrame({
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

    # ---------------------------------------------------------------------------
    # Добавляем дополнительный дашборд с детальным анализом карточек
    # ---------------------------------------------------------------------------
    st.subheader("🔍 Углубленный анализ карточек группы заданий")
    
    # Подготавливаем данные для анализа
    display_df = df_gz.copy()
    # Добавляем короткие идентификаторы для отображения на графиках
    display_df["card_short_id"] = display_df["card_id"].astype(str).str[-4:]
    
    # Создаем вкладки для разных аспектов анализа
    detailed_tabs = st.tabs(["Процент успеха", "Успех и попытки", "Жалобы", "Дискриминативность", "Компоненты риска"])
    
    with detailed_tabs[0]:
        st.markdown("### Детальный анализ успешности")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # График успешности по каждой карточке
            avg_success = display_df["success_rate"].mean()
            fig_success_cards = px.bar(
                display_df,
                x="card_short_id",
                y="success_rate",
                color="risk",
                hover_data=["card_id", "card_type", "total_attempts"],
                color_continuous_scale="RdYlGn_r",
                labels={"success_rate": "Успешность", "card_short_id": "ID карточки (последние 4 цифры)"},
                title="Успешность по каждой карточке"
            )
            fig_success_cards.update_layout(xaxis_title="ID карточки (последние 4 цифры)", yaxis_title="Успешность", yaxis_tickformat=".0%")
            # Добавляем горизонтальную линию среднего значения
            fig_success_cards.add_hline(y=avg_success, line_dash="dash", line_color="green", 
                            annotation_text=f"Среднее: {avg_success:.1%}", 
                            annotation_position="top right")
            st.plotly_chart(fig_success_cards, use_container_width=True)
        
        with col2:
            # График соотношения успешности и успешности с первой попытки
            fig_success_comparison = px.bar(
                display_df,
                x="card_short_id",
                y=["success_rate", "first_try_success_rate"],
                barmode="group",
                color_discrete_sequence=["#4da6ff", "#ff9040"],
                labels={"value": "Успешность", "card_short_id": "ID карточки", "variable": "Метрика"},
                title="Сравнение общей успешности и успеха с первой попытки"
            )
            fig_success_comparison.update_layout(xaxis_title="ID карточки (последние 4 цифры)", yaxis_tickformat=".0%", legend_title="Тип успешности")
            st.plotly_chart(fig_success_comparison, use_container_width=True)
            
    with detailed_tabs[1]:
        st.markdown("### Попытки и успешность")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Абсолютное количество попыток по каждой карточке
            fig_attempts_cards = px.bar(
                display_df,
                x="card_short_id",
                y="total_attempts",
                color="card_type",
                labels={"total_attempts": "Количество попыток", "card_short_id": "ID карточки"},
                title="Количество попыток по каждой карточке"
            )
            
            # Добавляем горизонтальную линию среднего значения
            fig_attempts_cards.add_hline(y=display_df["total_attempts"].mean(), line_dash="dash", line_color="blue", 
                              annotation_text=f"Среднее: {display_df['total_attempts'].mean():.0f}", 
                              annotation_position="top right")
            
            st.plotly_chart(fig_attempts_cards, use_container_width=True)
        
        with col2:
            # Доля студентов, пытавшихся решить задание
            fig_attempted_share = px.bar(
                display_df,
                x="card_short_id",
                y="attempted_share",
                color="risk",
                color_continuous_scale="RdYlGn_r",
                labels={"attempted_share": "Доля пытавшихся", "card_short_id": "ID карточки"},
                title="Доля студентов, пытавшихся решить задание"
            )
            fig_attempted_share.update_layout(yaxis_tickformat=".0%")
            
            # Добавляем горизонтальную линию среднего значения
            fig_attempted_share.add_hline(y=display_df["attempted_share"].mean(), line_dash="dash", line_color="green", 
                              annotation_text=f"Среднее: {display_df['attempted_share'].mean():.1%}", 
                              annotation_position="top right")
            
            st.plotly_chart(fig_attempted_share, use_container_width=True)
    
    with detailed_tabs[2]:
        st.markdown("### Детальный анализ жалоб")
        
        # Рассчитываем абсолютное количество жалоб для каждой карточки, если его нет
        if "complaints_total" not in display_df.columns:
            display_df["complaints_total"] = display_df["complaint_rate"] * display_df["total_attempts"]
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Абсолютное количество жалоб по каждой карточке
            fig_complaints_abs = px.bar(
                display_df,
                x="card_short_id",
                y="complaints_total",
                color="risk",
                color_continuous_scale="RdYlGn_r",
                labels={"complaints_total": "Количество жалоб", "card_short_id": "ID карточки"},
                title="Абсолютное количество жалоб"
            )
            
            # Добавляем горизонтальную линию среднего значения
            fig_complaints_abs.add_hline(y=display_df["complaints_total"].mean(), line_dash="dash", line_color="red", 
                              annotation_text=f"Среднее: {display_df['complaints_total'].mean():.0f}", 
                              annotation_position="top right")
            
            st.plotly_chart(fig_complaints_abs, use_container_width=True)
        
        with col2:
            # Процент жалоб по каждой карточке
            fig_complaints_pct = px.bar(
                display_df,
                x="card_short_id",
                y="complaint_rate",
                color="success_rate",
                color_continuous_scale="RdYlGn",
                labels={"complaint_rate": "Процент жалоб", "card_short_id": "ID карточки"},
                title="Процент жалоб"
            )
            fig_complaints_pct.update_layout(yaxis_tickformat=".0%")
            
            # Добавляем горизонтальную линию среднего значения
            fig_complaints_pct.add_hline(y=display_df["complaint_rate"].mean(), line_dash="dash", line_color="red", 
                              annotation_text=f"Среднее: {display_df['complaint_rate'].mean():.1%}", 
                              annotation_position="top right")
            
            st.plotly_chart(fig_complaints_pct, use_container_width=True)
    
    with detailed_tabs[3]:
        st.markdown("### Анализ дискриминативности")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Индекс дискриминативности по каждой карточке
            fig_discrimination_cards = px.bar(
                display_df,
                x="card_short_id",
                y="discrimination_avg",
                color="success_rate",
                color_continuous_scale="RdYlGn",
                labels={"discrimination_avg": "Индекс дискриминативности", "card_short_id": "ID карточки"},
                title="Индекс дискриминативности"
            )
            
            # Добавляем горизонтальную линию среднего значения
            fig_discrimination_cards.add_hline(y=display_df["discrimination_avg"].mean(), line_dash="dash", line_color="purple", 
                              annotation_text=f"Среднее: {display_df['discrimination_avg'].mean():.2f}", 
                              annotation_position="top right")
            
            # Добавляем горизонтальную линию оптимального значения (0.5)
            fig_discrimination_cards.add_hline(y=0.5, line_dash="dot", line_color="black", 
                              annotation_text="Оптимальное: 0.5", 
                              annotation_position="bottom right")
            
            st.plotly_chart(fig_discrimination_cards, use_container_width=True)
        
        with col2:
            # Дискриминативность vs Успешность - диаграмма рассеяния
            fig_discr_vs_success = px.scatter(
                display_df,
                x="success_rate",
                y="discrimination_avg",
                color="risk",
                size="total_attempts",
                hover_data=["card_id", "card_type"],
                color_continuous_scale="RdYlGn_r",
                labels={"success_rate": "Успешность", "discrimination_avg": "Индекс дискриминативности"},
                title="Зависимость дискриминативности от успешности"
            )
            fig_discr_vs_success.update_layout(xaxis_tickformat=".0%")
            
            # Отображаем оптимальную зону
            fig_discr_vs_success.add_shape(
                type="rect",
                x0=0.4, y0=0.4,
                x1=0.6, y1=0.6,
                line=dict(color="green", width=2, dash="dash"),
                fillcolor="rgba(0,255,0,0.1)"
            )
            
            fig_discr_vs_success.add_annotation(
                x=0.5, y=0.6,
                text="Оптимальная зона",
                showarrow=False,
                font=dict(color="green")
            )
            
            st.plotly_chart(fig_discr_vs_success, use_container_width=True)
    
    with detailed_tabs[4]:
        st.markdown("### Компоненты риска")
        
        # Получаем подробные данные о компонентах риска
        df_risk_components = core.get_risk_components(df_gz)
        
        # Выводим информацию о компонентах риска
        st.markdown("""
        #### Формула риска учитывает несколько компонентов:
        - **Общая успешность (25%)**: Низкий процент успешных решений увеличивает риск
        - **Успешность с первой попытки (15%)**: Низкий процент успеха с первой попытки указывает на сложность задания
        - **Жалобы (30%)**: Высокий процент жалоб - критический показатель проблем с заданием
        - **Дискриминативность (20%)**: Низкая дискриминативность означает, что задание плохо различает знающих от незнающих
        - **Доля пытавшихся (10%)**: Низкий процент студентов, пытавшихся решить задание, может указывать на проблемы
        """)
        
        # Создаем визуализацию компонентов риска
        contrib_cols = [
            "contrib_success", "contrib_first_try", "contrib_complaints", 
            "contrib_discrimination", "contrib_attempted"
        ]
        
        contrib_labels = {
            "contrib_success": "Успешность",
            "contrib_first_try": "Успех с 1-й попытки",
            "contrib_complaints": "Жалобы",
            "contrib_discrimination": "Дискриминативность",
            "contrib_attempted": "Доля пытавшихся"
        }
        
        # Для наглядности, отбираем топ-10 карточек с высоким риском
        top_risk = df_risk_components.sort_values("risk", ascending=False).head(10)
        top_risk["card_short_id"] = top_risk["card_id"].astype(str).str[-4:]
        
        fig = px.bar(
            top_risk,
            x="card_short_id",
            y=contrib_cols,
            barmode="stack",
            color_discrete_sequence=["#ff9040", "#ffbf80", "#ff6666", "#9370db", "#66c2a5"],
            labels={
                "card_short_id": "ID карточки",
                "value": "Вклад в риск",
                "variable": "Компонент"
            },
            title="Вклад различных компонентов в итоговый риск (топ-10 карточек)"
        )
        
        # Переименовываем легенду
        fig.for_each_trace(lambda t: t.update(name = contrib_labels.get(t.name, t.name)))
        
        # Добавляем общий риск как линию
        fig.add_trace(go.Scatter(
            x=top_risk["card_short_id"],
            y=top_risk["raw_risk"],
            mode="lines+markers",
            name="Общий риск",
            marker=dict(color="black"),
            line=dict(color="black", width=2)
        ))
        
        # Настраиваем макет
        fig.update_layout(
            xaxis_title="ID карточки (последние 4 цифры)",
            yaxis_title="Вклад в риск",
            legend_title="Компонент"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Отображаем таблицу с компонентами риска
        risk_table = top_risk[["card_id", "risk_success", "risk_first_try", "risk_complaints", 
                             "risk_discrimination", "risk_attempted", "raw_risk", "confidence_factor", "adjusted_risk"]]
        
        st.markdown("### Таблица компонентов риска")
        st.markdown("*Значения риска от 0 до 1, где 1 - максимальный риск*")
        
        formatted_risk_table = risk_table.style.format({
            "risk_success": "{:.2f}",
            "risk_first_try": "{:.2f}",
            "risk_complaints": "{:.2f}",
            "risk_discrimination": "{:.2f}",
            "risk_attempted": "{:.2f}",
            "raw_risk": "{:.2f}",
            "confidence_factor": "{:.2f}",
            "adjusted_risk": "{:.2f}"
        }).background_gradient(
            subset=["risk_success", "risk_first_try", "risk_complaints", 
                   "risk_discrimination", "risk_attempted", "raw_risk", "adjusted_risk"],
            cmap="RdYlGn_r"
        )
        
        st.dataframe(formatted_risk_table, use_container_width=True)
    
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
        display_clickable_items(df_gz, "card_id", "card", metrics=["risk"])

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
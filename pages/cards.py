# pages/cards.py
"""
Страница с детальной информацией по карточкам
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

import core
from components.utils import create_hierarchical_header, add_gz_links
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart, display_completion_radar,display_cards_chart


def page_cards(df: pd.DataFrame, eng):
    """Страница с детальным анализом карточек"""
    df_filtered = core.apply_filters(df)
    
    # Получаем выбранные фильтры
    program_filter = st.session_state.get("filter_program")
    module_filter = st.session_state.get("filter_module")
    lesson_filter = st.session_state.get("filter_lesson")
    gz_filter = st.session_state.get("filter_gz")
    
    # Создаем иерархический заголовок
    create_hierarchical_header(
        levels=["program", "module", "lesson", "gz", "card"],
        values=[program_filter, module_filter, lesson_filter, gz_filter, "Анализ"]
    )
    
    # Если выбрана группа заданий, добавляем кнопки со ссылками
    add_gz_links(df_filtered, gz_filter)
    
    # Проверка наличия данных после фильтрации
    if df_filtered.empty:
        hdr = " / ".join(filter(None, [st.session_state.get(f"filter_{c}") for c in core.FILTERS]))
        st.warning(f"Нет данных для выбранных фильтров: {hdr}")
        return
    
    # Получаем подробные данные о компонентах риска
    df_risk_components = core.get_risk_components(df_filtered)
    
    # ---------------------------------------------------------------------------
    # Объяснение улучшенной формулы риска
    # ---------------------------------------------------------------------------
    with st.expander("ℹ️ Информация о формуле риска", expanded=False):
        st.markdown("""
        ### Улучшенная формула расчета риска

        Мы используем комплексную формулу для оценки риска, учитывающую несколько ключевых компонентов:

        **Компоненты риска и их веса:**
        - **Общая успешность (25%)**: Низкий процент успешных решений увеличивает риск
        - **Успешность с первой попытки (15%)**: Низкий процент успеха с первой попытки указывает на сложность или неясность задания
        - **Жалобы (30%)**: Высокий процент жалоб - критический показатель проблем с заданием
        - **Дискриминативность (20%)**: Низкая дискриминативность означает, что задание плохо различает знающих от незнающих студентов
        - **Доля пытавшихся (10%)**: Низкий процент студентов, пытавшихся решить задание, может указывать на проблемы

        **Корректировка на статистическую значимость:**
        - Для карточек с малым количеством попыток (<100) риск смещается к 0.5 (неопределённость)
        - Это позволяет избежать ложных выводов на основе недостаточных данных
        
        **Формула:**
        ```
        raw_risk = 0.25*(1-success_rate) + 0.15*(1-first_try_success_rate) + 0.30*min(complaint_rate*3, 1) + 0.20*(1-discrimination_avg) + 0.10*(1-attempted_share)
        
        confidence_factor = min(total_attempts/100, 1.0)
        
        adjusted_risk = raw_risk * confidence_factor + 0.5 * (1-confidence_factor)
        ```
        
        **Интерпретация риска:**
        - **< 0.3**: Низкий риск - хорошо работающие задания
        - **0.3 - 0.5**: Средний риск - возможны небольшие улучшения
        - **0.5 - 0.7**: Высокий риск - требуется внимание
        - **> 0.7**: Очень высокий риск - требуется срочная доработка
        """)
    
    # ---------------------------------------------------------------------------
    # Dashboard с ключевыми метриками - с добавлением абсолютных значений
    # ---------------------------------------------------------------------------
    st.subheader("📊 Дашборд ключевых метрик")
    
    # Отображаем общие метрики
    metrics = display_metrics_row(df_filtered, compare_with=df)
    
    # Распределение риска и статусы
    col1, col2 = st.columns(2)
    
    with col1:
        display_risk_distribution(df_filtered)
    
    with col2:
        display_status_chart(df_filtered)
    
    # ---------------------------------------------------------------------------
    # Распределение ключевых метрик по конкретным карточкам
    # ---------------------------------------------------------------------------
    st.subheader("📈 Распределение ключевых метрик")
    
    # Для более наглядной визуализации ограничиваем количество отображаемых карточек
    # если их слишком много
    max_cards_to_display = 50
    
    # Если карточек больше max_cards_to_display, работаем с подвыборкой
    # Приоритет отдаем карточкам с высоким риском и сортируем по риску
    if len(df_filtered) > max_cards_to_display:
        # Отбираем карточки с высоким риском
        high_risk_sample = df_filtered[df_filtered["risk"] > 0.6].sort_values(by="risk", ascending=False)
        
        # Если высокорисковых карточек меньше max_cards_to_display, добавляем случайные карточки до max_cards_to_display
        if len(high_risk_sample) < max_cards_to_display:
            remaining_count = max_cards_to_display - len(high_risk_sample)
            other_cards_sample = df_filtered[df_filtered["risk"] <= 0.6].sample(min(remaining_count, len(df_filtered[df_filtered["risk"] <= 0.6])))
            display_df = pd.concat([high_risk_sample, other_cards_sample])
        else:
            # Если высокорисковых больше max_cards_to_display, берем только топ-N
            display_df = high_risk_sample.head(max_cards_to_display)
    else:
        # Если карточек меньше max_cards_to_display, используем все
        display_df = df_filtered.copy()
    
    # Сортируем карточки по риску для более наглядного отображения
    display_df = display_df.sort_values(by="risk", ascending=False)
    
    # Добавляем короткие идентификаторы для отображения на графиках
    display_df["card_short_id"] = display_df["card_id"].astype(str).str[-4:]
    
    # Добавляем кликабельные URL, если они доступны
    if 'card_url' in display_df.columns:
        display_df["card_link"] = display_df.apply(
            lambda row: f"[{row['card_short_id']}]({row['card_url']})" if pd.notna(row['card_url']) else row['card_short_id'], 
            axis=1
        )
    else:
        display_df["card_link"] = display_df["card_short_id"]
    
    tabs = st.tabs(["Процент успеха", "Успех и попытки", "Жалобы", "Дискриминативность", "Сравнение метрик"])
    
    with tabs[0]:
        st.markdown("### Детальный анализ успешности по карточкам")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # График успешности по каждой карточке
            avg_success = display_df["success_rate"].mean()
            fig_success_cards = px.bar(
                display_df,
                x="card_short_id",
                y="success_rate",
                color="risk",
                hover_data=["card_id", "card_type", "total_attempts", "card_url"],
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
            
        # Рейтинг карточек по успешности
        st.markdown("### Рейтинг карточек по успешности")
        col1, col2 = st.columns(2)
        
        # Для топ-10 карточек с самой высокой успешностью
        with col1:
            # Топ-10 карточек с самой высокой успешностью
            top_success = display_df.sort_values(by="success_rate", ascending=False).head(10)
            
            # Создаем таблицу с использованием st.dataframe вместо html
            st.markdown("#### Самые успешные карточки")
            
            # Подготавливаем таблицу данных с кликабельными ссылками
            if 'card_url' in top_success.columns:
                success_table = top_success[['card_id', 'card_type', 'success_rate']].copy()
                
                # Создаем колонку с кликабельными ссылками используя markdown
                success_table_display = pd.DataFrame()
                success_table_display['Карточка'] = top_success.apply(
                    lambda row: f"[ID:{int(row['card_id'])}]({row['card_url']})" if pd.notna(row['card_url']) else f"ID:{int(row['card_id'])}", 
                    axis=1
                )
                success_table_display['Тип'] = top_success['card_type']
                success_table_display['Успешность'] = top_success['success_rate'].apply(lambda x: f"{x:.1%}")
                
                # Используем st.dataframe вместо st.write с html
                st.dataframe(success_table_display, hide_index=True, use_container_width=True)
            else:
                # Если URL недоступны, используем обычный график
                fig_top_success = px.bar(
                    top_success,
                    x="card_short_id",
                    y="success_rate",
                    color="card_type",
                    text_auto=".1%",
                    labels={"success_rate": "Успешность", "card_short_id": "ID карточки"},
                    title="Топ-10 карточек с самой высокой успешностью"
                )
                fig_top_success.update_layout(yaxis_tickformat=".0%")
                st.plotly_chart(fig_top_success, use_container_width=True)

        # Для топ-10 карточек с самой низкой успешностью
        with col2:
            # Топ-10 карточек с самой низкой успешностью
            bottom_success = display_df.sort_values(by="success_rate").head(10)
            
            # Используем тот же подход с st.dataframe
            st.markdown("#### Наименее успешные карточки")
            
            if 'card_url' in bottom_success.columns:
                bottom_table_display = pd.DataFrame()
                bottom_table_display['Карточка'] = bottom_success.apply(
                    lambda row: f"[ID:{int(row['card_id'])}]({row['card_url']})" if pd.notna(row['card_url']) else f"ID:{int(row['card_id'])}", 
                    axis=1
                )
                bottom_table_display['Тип'] = bottom_success['card_type']
                bottom_table_display['Успешность'] = bottom_success['success_rate'].apply(lambda x: f"{x:.1%}")
                
                st.dataframe(bottom_table_display, hide_index=True, use_container_width=True)
            else:
                # Если URL недоступны, используем обычный график
                fig_bottom_success = px.bar(
                    bottom_success,
                    x="card_short_id",
                    y="success_rate",
                    color="card_type",
                    text_auto=".1%",
                    labels={"success_rate": "Успешность", "card_short_id": "ID карточки"},
                    title="Топ-10 карточек с самой низкой успешностью"
                )
                fig_bottom_success.update_layout(yaxis_tickformat=".0%")
                st.plotly_chart(fig_bottom_success, use_container_width=True)
    
    with tabs[1]:
        st.markdown("### Попытки и успешность по карточкам")
        
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
        
        # Сравнение количества попыток и успешности
        fig_attempts_success = px.scatter(
            display_df,
            x="total_attempts",
            y="success_rate",
            color="risk",
            size="attempted_share",
            hover_data=["card_id", "card_type", "first_try_success_rate", "card_url"],
            color_continuous_scale="RdYlGn_r",
            labels={"success_rate": "Успешность", "total_attempts": "Количество попыток"},
            title="Зависимость успешности от количества попыток"
        )
        fig_attempts_success.update_layout(yaxis_tickformat=".0%")
        
        # Добавляем аннотации для карточек с экстремальными значениями
        for _, row in display_df.nlargest(3, "total_attempts").iterrows():
            fig_attempts_success.add_annotation(
                x=row["total_attempts"],
                y=row["success_rate"],
                text=f"ID: {row['card_short_id']}",
                showarrow=True,
                arrowhead=1
            )
        
        for _, row in display_df.nsmallest(3, "success_rate").iterrows():
            if row["total_attempts"] > display_df["total_attempts"].quantile(0.25):  # Исключаем карточки с малым числом попыток
                fig_attempts_success.add_annotation(
                    x=row["total_attempts"],
                    y=row["success_rate"],
                    text=f"ID: {row['card_short_id']}",
                    showarrow=True,
                    arrowhead=1
                )
        
        st.plotly_chart(fig_attempts_success, use_container_width=True)
    
    with tabs[2]:
        st.markdown("### Детальный анализ жалоб по карточкам")
        
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
                title="Абсолютное количество жалоб по карточкам"
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
                title="Процент жалоб по карточкам"
            )
            fig_complaints_pct.update_layout(yaxis_tickformat=".0%")
            
            # Добавляем горизонтальную линию среднего значения
            fig_complaints_pct.add_hline(y=display_df["complaint_rate"].mean(), line_dash="dash", line_color="red", 
                              annotation_text=f"Среднее: {display_df['complaint_rate'].mean():.1%}", 
                              annotation_position="top right")
            
            st.plotly_chart(fig_complaints_pct, use_container_width=True)
        
        # Топ карточек с жалобами
        st.markdown("### Карточки с наибольшим количеством жалоб")

        # Отбираем карточки с наибольшим абсолютным количеством жалоб
        top_complaints = display_df.sort_values(by="complaints_total", ascending=False).head(10)

        # Отображаем таблицу с кликабельными ссылками, если доступны
        if 'card_url' in top_complaints.columns:
            complaints_table_display = pd.DataFrame()
            complaints_table_display['Карточка'] = top_complaints.apply(
                lambda row: f"[ID:{int(row['card_id'])}]({row['card_url']})" if pd.notna(row['card_url']) else f"ID:{int(row['card_id'])}", 
                axis=1
            )
            complaints_table_display['Тип'] = top_complaints['card_type']
            complaints_table_display['Всего жалоб'] = top_complaints['complaints_total'].apply(lambda x: f"{int(x)}")
            complaints_table_display['Процент жалоб'] = top_complaints['complaint_rate'].apply(lambda x: f"{x:.1%}")
            
            st.dataframe(complaints_table_display, hide_index=True, use_container_width=True)
        else:
            # Если URL недоступны, используем обычный график
            fig_top_complaints = px.bar(
                top_complaints,
                x="card_short_id",
                y=["complaints_total", "total_attempts"],
                barmode="group",
                color_discrete_sequence=["#ff6666", "#4da6ff"],
                labels={"value": "Количество", "card_short_id": "ID карточки", "variable": "Метрика"},
                title="Топ-10 карточек по абсолютному количеству жалоб"
            )
            
            # Добавляем текстовые метки с процентом жалоб
            for i, row in enumerate(top_complaints.iterrows()):
                _, r = row
                fig_top_complaints.add_annotation(
                    x=i,
                    y=r["complaints_total"] + max(top_complaints["complaints_total"]) * 0.05,
                    text=f"{r['complaint_rate']:.1%}",
                    showarrow=False,
                    font=dict(color="red", size=10)
                )
            
            st.plotly_chart(fig_top_complaints, use_container_width=True)
        
        # Жалобы vs Успешность - диаграмма рассеяния
        fig_complaints_vs_success = px.scatter(
            display_df,
            x="success_rate",
            y="complaint_rate",
            color="risk",
            size="total_attempts",
            hover_data=["card_id", "card_type", "complaints_total", "card_url"],
            color_continuous_scale="RdYlGn_r",
            labels={"success_rate": "Успешность", "complaint_rate": "Процент жалоб"},
            title="Зависимость жалоб от успешности"
        )
        fig_complaints_vs_success.update_layout(xaxis_tickformat=".0%", yaxis_tickformat=".0%")
        
        # Добавляем аннотации для карточек с высоким процентом жалоб
        for _, row in display_df.nlargest(5, "complaint_rate").iterrows():
            fig_complaints_vs_success.add_annotation(
                x=row["success_rate"],
                y=row["complaint_rate"],
                text=f"ID: {row['card_short_id']}",
                showarrow=True,
                arrowhead=1
            )
        
        st.plotly_chart(fig_complaints_vs_success, use_container_width=True)
    
    with tabs[3]:
        st.markdown("### Детальный анализ дискриминативности по карточкам")
        
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
                title="Индекс дискриминативности по карточкам"
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
            # Распределение индекса дискриминативности
            fig_discr_hist = px.histogram(
                display_df,
                x="discrimination_avg",
                nbins=20,
                color_discrete_sequence=["#9370db"],
                labels={"discrimination_avg": "Индекс дискриминативности", "count": "Количество карточек"},
                title="Распределение индекса дискриминативности"
            )
            
            # Добавляем вертикальную линию среднего значения
            fig_discr_hist.add_vline(x=display_df["discrimination_avg"].mean(), line_dash="dash", line_color="purple", 
                              annotation_text=f"Среднее: {display_df['discrimination_avg'].mean():.2f}", 
                              annotation_position="top right")
            
            # Добавляем вертикальную линию оптимального значения (0.5)
            fig_discr_hist.add_vline(x=0.5, line_dash="dot", line_color="black", 
                              annotation_text="Оптимальное: 0.5", 
                              annotation_position="bottom right")
            
            st.plotly_chart(fig_discr_hist, use_container_width=True)

        # Топ карточек с экстремальными значениями дискриминативности
        st.markdown("### Карточки с экстремальными значениями дискриминативности")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Карточки с самой низкой дискриминативностью (проблемные)
            low_discr = display_df.sort_values(by="discrimination_avg").head(10)
            fig_low_discr = px.bar(
                low_discr,
                x="card_short_id",
                y="discrimination_avg",
                color="success_rate",
                color_continuous_scale="RdYlGn",
                text_auto=".2f",
                labels={"discrimination_avg": "Индекс дискриминативности", "card_short_id": "ID карточки"},
                title="Карточки с самой низкой дискриминативностью"
            )
            st.plotly_chart(fig_low_discr, use_container_width=True)
        
        with col2:
            # Карточки с самой высокой дискриминативностью (хорошие)
            high_discr = display_df.sort_values(by="discrimination_avg", ascending=False).head(10)
            fig_high_discr = px.bar(
                high_discr,
                x="card_short_id",
                y="discrimination_avg",
                color="success_rate",
                color_continuous_scale="RdYlGn",
                text_auto=".2f",
                labels={"discrimination_avg": "Индекс дискриминативности", "card_short_id": "ID карточки"},
                title="Карточки с самой высокой дискриминативностью"
            )
            st.plotly_chart(fig_high_discr, use_container_width=True)
        
        # Дискриминативность vs Успешность - диаграмма рассеяния
        fig_discr_vs_success = px.scatter(
            display_df,
            x="success_rate",
            y="discrimination_avg",
            color="risk",
            size="total_attempts",
            hover_data=["card_id", "card_type", "card_url"],
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
        
        # Отображаем таблицу с кликабельными ссылками, если доступны
        if 'card_url' in display_df.columns:
            # Отбираем карточки с экстремальными значениями дискриминативности
            extreme_discr = pd.concat([
                display_df.nsmallest(5, "discrimination_avg"), 
                display_df.nlargest(5, "discrimination_avg")
            ])
            
            st.markdown("#### Карточки с экстремальной дискриминативностью")
            
            # Создаем отображаемую таблицу с правильным форматированием
            discr_table_display = pd.DataFrame()
            discr_table_display['Карточка'] = extreme_discr.apply(
                lambda row: f"[ID:{int(row['card_id'])}]({row['card_url']})" if pd.notna(row['card_url']) else f"ID:{int(row['card_id'])}", 
                axis=1
            )
            discr_table_display['Тип'] = extreme_discr['card_type']
            discr_table_display['Дискриминативность'] = extreme_discr['discrimination_avg'].apply(lambda x: f"{x:.2f}")
            discr_table_display['Успешность'] = extreme_discr['success_rate'].apply(lambda x: f"{x:.1%}")
            
            # Используем st.dataframe вместо st.write с html
            st.dataframe(discr_table_display, hide_index=True, use_container_width=True)
        
        st.plotly_chart(fig_discr_vs_success, use_container_width=True)
    
    with tabs[4]:
        st.markdown("### Сравнительный анализ всех ключевых метрик")
        
        # Выбор метрик для отображения
        metrics_options = [
            "success_rate", "first_try_success_rate", "complaint_rate", 
            "discrimination_avg", "attempted_share", "risk"
        ]
        
        metrics_labels = {
            "success_rate": "Успешность",
            "first_try_success_rate": "Успех с первой попытки",
            "complaint_rate": "Процент жалоб",
            "discrimination_avg": "Индекс дискриминативности",
            "attempted_share": "Доля пытавшихся",
            "risk": "Риск"
        }
        
        # Определение количества карточек для визуализации
        num_cards_to_show = st.slider("Количество карточек для отображения", 5, min(30, len(display_df)), 10)
        
        # Выбираем топ карточек по риску для визуализации
        top_risk_cards = display_df.sort_values(by="risk", ascending=False).head(num_cards_to_show)
        
        # Подготавливаем данные для параллельных координат
        fig_parallel = px.parallel_coordinates(
            top_risk_cards,
            dimensions=["success_rate", "first_try_success_rate", "complaint_rate", "discrimination_avg", "attempted_share", "risk"],
            color="risk",
            labels=metrics_labels,
            color_continuous_scale="RdYlGn_r",
            title=f"Параллельные координаты для топ-{num_cards_to_show} карточек по риску"
        )
        
        # Настраиваем форматирование осей
        for i, dim in enumerate(fig_parallel.data[0].dimensions):
            if dim.label in ["success_rate", "first_try_success_rate", "complaint_rate", "attempted_share"]:
                dim.tickformat = ".0%"
            elif dim.label in ["discrimination_avg", "risk"]:
                dim.tickformat = ".2f"
        
        st.plotly_chart(fig_parallel, use_container_width=True)
        
        # Радарная диаграмма для топ-5 карточек с высоким риском
        st.markdown("### Радарные диаграммы для карточек с высоким риском")
        
        # Выбираем топ-5 карточек для радарной диаграммы
        radar_cards = top_risk_cards.head(5)
        
        # Создаем радарную диаграмму
        fig_radar = go.Figure()
        
        # Определяем метрики для радара
        radar_metrics = ["success_rate", "first_try_success_rate", "complaint_rate", "discrimination_avg", "attempted_share"]
        
        # Определяем нормализацию для каждой метрики (1 = хорошо, 0 = плохо)
        radar_normalize = {
            "success_rate": lambda x: x,  # Больше - лучше
            "first_try_success_rate": lambda x: x,  # Больше - лучше
            "complaint_rate": lambda x: 1 - x,  # Меньше - лучше
            "discrimination_avg": lambda x: x,  # Больше - лучше
            "attempted_share": lambda x: x  # Больше - лучше
        }
        
        # Добавляем каждую карточку на радар
        for _, card in radar_cards.iterrows():
            fig_radar.add_trace(go.Scatterpolar(
                r=[radar_normalize[m](card[m]) for m in radar_metrics],
                theta=[metrics_labels[m] for m in radar_metrics],
                fill='toself',
                name=f"ID: {card['card_short_id']} (риск: {card['risk']:.2f})"
            ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )
            ),
            title="Радарная диаграмма для топ-5 рисковых карточек"
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)
        
        # Сводная таблица с детальными метриками по карточкам
        st.markdown("### Детальная таблица метрик")
        
        # Форматируем таблицу для отображения
        table_df = top_risk_cards[["card_id", "card_type", "success_rate", "first_try_success_rate", 
                                  "complaint_rate", "discrimination_avg", "total_attempts", "risk"]]
        
        # Форматируем числовые значения
        # Продолжение обновленной части функции page_cards в pages.py
        
        # Форматируем числовые значения
        formatted_table = table_df.style.format({
            "success_rate": "{:.1%}",
            "first_try_success_rate": "{:.1%}",
            "complaint_rate": "{:.1%}",
            "discrimination_avg": "{:.2f}",
            "total_attempts": "{:.0f}",
            "risk": "{:.2f}"
        })
        
        # Добавляем цветовое форматирование
        formatted_table = formatted_table.background_gradient(
            subset=["success_rate", "first_try_success_rate"],
            cmap="RdYlGn"
        )
        
        formatted_table = formatted_table.background_gradient(
            subset=["complaint_rate", "risk"],
            cmap="RdYlGn_r"
        )
        
        formatted_table = formatted_table.background_gradient(
            subset=["discrimination_avg"],
            cmap="PuRd"
        )
        
        formatted_table = formatted_table.background_gradient(
            subset=["total_attempts"],
            cmap="Blues"
        )
        
        st.dataframe(formatted_table, use_container_width=True)
        
        # График изменения метрик относительно среднего значения
        st.markdown("### Отклонение метрик от среднего значения")
        
        # Выбираем метрики для анализа
        deviation_metrics = ["success_rate", "first_try_success_rate", "complaint_rate", "discrimination_avg", "risk"]
        
        # Вычисляем средние значения
        metric_means = {m: display_df[m].mean() for m in deviation_metrics}
        
        # Создаем DataFrame с отклонениями от среднего
        deviations = pd.DataFrame()
        
        for card_id in top_risk_cards["card_short_id"]:
            card_data = top_risk_cards[top_risk_cards["card_short_id"] == card_id].iloc[0]
            
            card_deviations = {}
            for metric in deviation_metrics:
                # Для complaint_rate и risk отрицательное отклонение - хорошо
                if metric in ["complaint_rate", "risk"]:
                    card_deviations[metric] = -(card_data[metric] - metric_means[metric]) / metric_means[metric]
                else:
                    card_deviations[metric] = (card_data[metric] - metric_means[metric]) / metric_means[metric]
            
            card_df = pd.DataFrame.from_dict(card_deviations, orient='index').reset_index()
            card_df.columns = ["metric", "deviation"]
            card_df["card_id"] = card_id
            
            deviations = pd.concat([deviations, card_df])
        
        # Преобразуем названия метрик для отображения
        deviations["metric"] = deviations["metric"].map(metrics_labels)
        
        # Создаем график отклонений
        fig_deviations = px.bar(
            deviations,
            x="metric",
            y="deviation",
            color="card_id",
            barmode="group",
            labels={"deviation": "Отклонение от среднего (%)", "metric": "Метрика"},
            title="Отклонение метрик от среднего значения по карточкам"
        )
        
        fig_deviations.update_layout(yaxis_tickformat=".0%")
        
        st.plotly_chart(fig_deviations, use_container_width=True)
        
        # Поясняющий текст
        st.markdown("""
        **Примечание по интерпретации отклонений:**
        - Положительные значения (выше среднего) означают **лучше** среднего для всех метрик
        - Для жалоб и риска значения инвертированы, чтобы положительные значения всегда означали лучше среднего
        """)
    
    # ---------------------------------------------------------------------------
    # Таблица со статусами карточек
    # ---------------------------------------------------------------------------
    st.subheader("📋 Статусы карточек")
    
    # Добавляем разделитель
    st.markdown("---")
    
    # Определяем настройки отображения статусов
    status_colors = {
        "new": "lightgray",
        "in_work": "lightblue",
        "ready_for_qc": "lightyellow",
        "done": "lightgreen",
        "wont_fix": "lightcoral"
    }
    
    editor_cfg = {
        "status": st.column_config.SelectboxColumn(
            "Status", 
            options=["new", "in_work", "ready_for_qc", "done", "wont_fix"], 
            required=True
        ),
        "card_id": st.column_config.NumberColumn(
            "ID карточки",
            format="%d"
        ),
        "success_rate": st.column_config.ProgressColumn(
            "Успешность",
            format="%.1f%%",
            min_value=0,
            max_value=1
        ),
        "complaint_rate": st.column_config.ProgressColumn(
            "Жалобы",
            format="%.1f%%",
            min_value=0,
            max_value=0.5,
            help="Процент жалоб от общего числа попыток"
        ),
        "discrimination_avg": st.column_config.NumberColumn(
            "Дискриминативность",
            format="%.2f"
        ),
        "risk": st.column_config.ProgressColumn(
            "Риск",
            format="%.2f",
            min_value=0,
            max_value=1
        ),
        "total_attempts": st.column_config.NumberColumn(
            "Количество попыток",
            format="%d"
        )
    }
    
    # Добавляем статистику по статусам
    status_counts = df_filtered["status"].value_counts().reset_index()
    status_counts.columns = ["Статус", "Количество"]
    
    status_fig = px.pie(
        status_counts,
        values="Количество",
        names="Статус",
        title="Распределение карточек по статусам",
        color="Статус",
        color_discrete_map={
            "new": "#d3d3d3",
            "in_work": "#add8e6",
            "ready_for_qc": "#fffacd",
            "done": "#90ee90",
            "wont_fix": "#f08080"
        },
        hole=0.4
    )
    
    st.plotly_chart(status_fig, use_container_width=True)
    
    # Добавляем фильтр по статусу и другие полезные фильтры
    col1, col2 = st.columns(2)
    
    with col1:
        selected_status = st.multiselect(
            "Фильтр по статусу:",
            options=df_filtered["status"].unique(),
            default=df_filtered["status"].unique()
        )
    
    with col2:
        # Добавляем фильтр по типу карточки, если есть разные типы
        if "card_type" in df_filtered.columns and len(df_filtered["card_type"].unique()) > 1:
            selected_types = st.multiselect(
                "Фильтр по типу карточки:",
                options=df_filtered["card_type"].unique(),
                default=df_filtered["card_type"].unique()
            )
        else:
            selected_types = df_filtered["card_type"].unique() if "card_type" in df_filtered.columns else None
    
    # Фильтруем данные по выбранным статусам и типам
    df_filtered_status = df_filtered
    
    if selected_status:
        df_filtered_status = df_filtered_status[df_filtered_status["status"].isin(selected_status)]
    
    if "card_type" in df_filtered.columns and selected_types is not None and len(selected_types) > 0:
        df_filtered_status = df_filtered_status[df_filtered_status["card_type"].isin(selected_types)]
    
    # Сортируем карточки по риску (от высокого к низкому)
    df_filtered_sorted = df_filtered_status.sort_values(by="risk", ascending=False)
    
    # Отображаем дата-редактор с улучшенной визуализацией
    edited = st.data_editor(
        df_filtered_sorted, 
        column_config=editor_cfg, 
        hide_index=True,
        use_container_width=True
    )
    
    # Кнопка сохранения изменений
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("💾 Сохранить изменения в статусах", type="primary"):
            core.save_status_changes(df_filtered_sorted, edited, eng)
            st.success("Изменения статусов успешно сохранены!")
    
    with col2:
        # Если у нас есть URL карточек, отображаем их кликабельными
        if 'card_url' in df_filtered_sorted.columns and not df_filtered_sorted.empty:
            st.markdown("### Прямые ссылки на карточки")
            
            # Создаем DataFrame с карточками для отображения в виде таблицы
            card_links_df = pd.DataFrame()
            card_links_df['ID карточки'] = df_filtered_sorted['card_id'].apply(lambda x: int(x))
            card_links_df['Ссылка'] = df_filtered_sorted.apply(
                lambda row: f"[Открыть]({row['card_url']})" if pd.notna(row['card_url']) else "Нет ссылки", 
                axis=1
            )
            card_links_df['Тип'] = df_filtered_sorted['card_type']
            card_links_df['Риск'] = df_filtered_sorted['risk'].apply(lambda x: f"{x:.2f}")
            
            # Отображаем в виде таблицы с кликабельными ссылками
            st.dataframe(card_links_df, hide_index=True, use_container_width=True)
        
        st.markdown("""
        **Подсказка:** Используйте сортировку по колонкам для удобного анализа карточек.
        Нажмите на заголовок колонки для сортировки по возрастанию или убыванию.
        """)
# pages/cards.py
"""
Обновленная страница с детальной информацией по одной выбранной карточке
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

import core
from components.utils import create_hierarchical_header, add_gz_links
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution

def page_cards(df: pd.DataFrame, eng):
    """Страница детального анализа одной карточки"""
    # Фильтруем данные по выбранным фильтрам
    df_filtered = core.apply_filters(df)
    
    # Получаем выбранные фильтры
    program_filter = st.session_state.get("filter_program")
    module_filter = st.session_state.get("filter_module")
    lesson_filter = st.session_state.get("filter_lesson")
    gz_filter = st.session_state.get("filter_gz")
    
    # Проверяем, выбрана ли конкретная карточка
    card_filter = st.session_state.get("filter_card_id")
    
    # Если карточка не выбрана, предлагаем выбрать из списка доступных
    if not card_filter:
        # Создаем иерархический заголовок
        create_hierarchical_header(
            levels=["program", "module", "lesson", "gz", "card"],
            values=[program_filter, module_filter, lesson_filter, gz_filter, "Выбор карточки"]
        )
        
        # Проверка наличия данных после фильтрации
        if df_filtered.empty:
            hdr = " / ".join(filter(None, [st.session_state.get(f"filter_{c}") for c in core.FILTERS]))
            st.warning(f"Нет данных для выбранных фильтров: {hdr}")
            return
        
        # Добавляем информацию о выборе карточки
        st.info("📌 Пожалуйста, выберите карточку для детального анализа")
        
        # Добавляем селектор карточек
        card_options = df_filtered.sort_values("risk", ascending=False)
        
        # Создаем красивые опции с информацией о риске
        card_display_options = {}
        for _, card in card_options.iterrows():
            card_id = int(card['card_id'])
            risk_icon = "🔴" if card['risk'] > 0.7 else ("🟠" if card['risk'] > 0.5 else ("🟡" if card['risk'] > 0.3 else "🟢"))
            card_type = card['card_type'] if 'card_type' in card.index else "Карточка"
            card_display_options[card_id] = f"{risk_icon} ID: {card_id} - {card_type} (Риск: {card['risk']:.2f})"
        
        # Отображаем выбор карточки
        selected_card_id = st.selectbox(
            "Выберите карточку для анализа:",
            options=list(card_display_options.keys()),
            format_func=lambda x: card_display_options[x],
            index=0 if card_options.shape[0] > 0 else None
        )
        
        # Добавляем кнопку для перехода к анализу
        if st.button("📊 Анализировать выбранную карточку", type="primary"):
            st.session_state["filter_card_id"] = selected_card_id
            st.rerun()
            
        # Отображаем предварительную таблицу со всеми карточками
        st.subheader("📋 Доступные карточки")
        
        # Отображаем таблицу
        cards_df = df_filtered[["card_id", "card_type", "status", "success_rate", 
                              "first_try_success_rate", "complaint_rate", 
                              "discrimination_avg", "total_attempts", "risk"]]
        
        # Сортируем по риску для удобства
        cards_df = cards_df.sort_values("risk", ascending=False)
        
        # Создаем кликабельные ссылки на карточки, если доступны URL
        if "card_url" in df_filtered.columns:
            cards_df_display = cards_df.copy()
            cards_df_display["Карточка"] = df_filtered.apply(
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
        
        return
    
    # Если карточка выбрана, отображаем её детальный анализ
    # Фильтруем данные для выбранной карточки
    card_data = df_filtered[df_filtered["card_id"] == card_filter]
    
    # Если данные карточки не найдены, выводим сообщение об ошибке
    if card_data.empty:
        st.error(f"Карточка с ID {card_filter} не найдена в выбранных фильтрах.")
        
        # Добавляем кнопку для сброса выбора карточки
        if st.button("🔙 Вернуться к выбору карточки"):
            st.session_state["filter_card_id"] = None
            st.rerun()
        
        return
    
    # Получаем данные о карточке
    card = card_data.iloc[0]
    
    # Создаем иерархический заголовок
    create_hierarchical_header(
        levels=["program", "module", "lesson", "gz", "card"],
        values=[program_filter, module_filter, lesson_filter, gz_filter, f"ID: {int(card_filter)}"]
    )
    
    # Добавляем ссылки на ГЗ
    add_gz_links(card_data, gz_filter)
    
    # Создаем шапку с основной информацией о карточке
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        st.subheader(f"📝 Карточка ID: {int(card_filter)}")
        st.markdown(f"**Тип карточки:** {card['card_type']}")
        st.markdown(f"**Статус:** {card['status']}")
        
        # Если есть URL карточки, добавляем ссылку
        if "card_url" in card and pd.notna(card["card_url"]):
            st.markdown(f"**[🔗 Открыть карточку в редакторе]({card['card_url']})**")
    
    with col2:
        # Отображаем визуальный индикатор риска
        risk_value = card['risk']
        risk_color = "red" if risk_value > 0.7 else ("orange" if risk_value > 0.5 else ("gold" if risk_value > 0.3 else "green"))
        risk_text = "Очень высокий" if risk_value > 0.7 else ("Высокий" if risk_value > 0.5 else ("Средний" if risk_value > 0.3 else "Низкий"))
        
        st.markdown(f"### Уровень риска: {risk_text}")
        
        # Создаем визуальный индикатор риска
        st.progress(risk_value, text=f"{risk_value:.2f}")
        
        # Добавляем текстовое описание риска
        if risk_value > 0.7:
            st.error("⚠️ Критический уровень риска! Требуется немедленная доработка.")
        elif risk_value > 0.5:
            st.warning("⚠️ Высокий уровень риска! Рекомендуется доработка.")
        elif risk_value > 0.3:
            st.info("ℹ️ Средний уровень риска. Возможны улучшения.")
        else:
            st.success("✅ Низкий уровень риска. Карточка работает хорошо.")
    
    with col3:
        # Добавляем кнопки действий
        if st.button("🔙 К списку карточек"):
            st.session_state["filter_card_id"] = None
            st.rerun()
        
        # Добавляем кнопку для изменения статуса
        current_status = card["status"]
        status_options = ["new", "in_work", "ready_for_qc", "done", "wont_fix"]
        
        new_status = st.selectbox(
            "Изменить статус:",
            options=status_options,
            index=status_options.index(current_status) if current_status in status_options else 0,
            key="change_status"
        )
        
        if new_status != current_status:
            if st.button("💾 Сохранить статус", type="primary"):
                # Создаем DataFrame для сохранения изменений
                original_df = pd.DataFrame([card])
                edited_df = original_df.copy()
                edited_df.loc[0, "status"] = new_status
                
                # Сохраняем изменения
                core.save_status_changes(original_df, edited_df, eng)
                st.success(f"Статус изменен на: {new_status}")
                # Обновляем страницу для отображения нового статуса
                st.rerun()
    
    # Добавляем разделитель
    st.markdown("---")
    
    # Основные метрики карточки в виде больших визуальных индикаторов
    st.subheader("📊 Ключевые метрики карточки")
    
    # Создаем 4 колонки для основных метрик
    metrics_cols = st.columns(4)
    
    with metrics_cols[0]:
        success_rate = card["success_rate"]
        success_color = "normal" if success_rate >= 0.5 else "off"
        
        st.metric(
            "Успешность решения",
            f"{success_rate:.1%}",
            help="Процент студентов, успешно решивших карточку от числа пытавшихся"
        )
        
        # Визуальный индикатор
        st.progress(success_rate, text=f"{success_rate:.1%}")
    
    with metrics_cols[1]:
        first_try_rate = card["first_try_success_rate"]
        
        st.metric(
            "Успех с 1-й попытки",
            f"{first_try_rate:.1%}",
            help="Процент студентов, решивших карточку с первой попытки"
        )
        
        # Визуальный индикатор
        st.progress(first_try_rate, text=f"{first_try_rate:.1%}")
    
    with metrics_cols[2]:
        complaint_rate = card["complaint_rate"]
        # Для жалоб используем инвертированную шкалу (меньше - лучше)
        complaint_delta = None
        complaint_color = "inverse"
        
        st.metric(
            "Процент жалоб",
            f"{complaint_rate:.1%}",
            delta=complaint_delta,
            delta_color=complaint_color,
            help="Процент попыток, на которые поступили жалобы"
        )
        
        # Визуальный индикатор (инвертированный)
        st.progress(1 - complaint_rate, text=f"{complaint_rate:.1%}")
    
    with metrics_cols[3]:
        discrimination = card["discrimination_avg"]
        # Оптимальное значение дискриминативности - 0.5
        discrimination_delta = f"{discrimination - 0.5:+.2f} от оптимального" if abs(discrimination - 0.5) > 0.1 else None
        discrimination_color = "normal" if 0.4 <= discrimination <= 0.6 else "off"
        
        st.metric(
            "Дискриминативность",
            f"{discrimination:.2f}",
            delta=discrimination_delta,
            delta_color=discrimination_color,
            help="Способность задания различать знающих от незнающих студентов (оптимально: 0.5)"
        )
        
        # Визуальный индикатор (нормализованный к 0.5)
        discrimination_norm = 1 - abs(discrimination - 0.5) * 2 # 0.5 -> 1.0, 0.0 или 1.0 -> 0.0
        discrimination_norm = max(0, min(1, discrimination_norm)) # Ограничиваем значения от 0 до 1
        st.progress(discrimination_norm, text=f"{discrimination:.2f}")
    
    # Добавляем вторую строку метрик
    metrics_cols2 = st.columns(4)
    
    with metrics_cols2[0]:
        attempts = int(card["total_attempts"])
        
        st.metric(
            "Всего попыток",
            f"{attempts:,}",
            help="Общее количество попыток решения этой карточки"
        )
    
    with metrics_cols2[1]:
        attempted_share = card["attempted_share"]
        
        st.metric(
            "Доля пытавшихся",
            f"{attempted_share:.1%}",
            help="Процент студентов, которые попытались решить эту карточку"
        )
        
        # Визуальный индикатор
        st.progress(attempted_share, text=f"{attempted_share:.1%}")
    
    with metrics_cols2[2]:
        if "complaints_total" in card:
            complaints_total = int(card["complaints_total"])
        else:
            complaints_total = int(card["complaint_rate"] * card["total_attempts"])
        
        st.metric(
            "Всего жалоб",
            f"{complaints_total:,}",
            help="Общее количество жалоб на эту карточку"
        )
    
    with metrics_cols2[3]:
        success_attempts_rate = card.get("success_attempts_rate", card["success_rate"])
        
        st.metric(
            "Успешных попыток",
            f"{success_attempts_rate:.1%}",
            help="Процент успешных попыток от общего числа попыток"
        )
        
        # Визуальный индикатор
        st.progress(success_attempts_rate, text=f"{success_attempts_rate:.1%}")
    
    # Добавляем разделитель
    st.markdown("---")
    
    # Углубленный анализ компонентов риска
    st.subheader("🔍 Углубленный анализ компонентов риска")
    
    # Получаем подробные данные о компонентах риска
    df_risk_components = core.get_risk_components(card_data)
    risk_component = df_risk_components.iloc[0]
    
    # Выводим информацию о формуле риска
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
    
    # Создаем визуализацию компонентов риска
    # 1. Круговая диаграмма вклада каждого компонента в риск
    col1, col2 = st.columns([2, 3])
    
    with col1:
        # Создаем DataFrame для круговой диаграммы
        risk_components_df = pd.DataFrame({
            "Компонент": [
                "Успешность", 
                "Успех с 1-й попытки", 
                "Жалобы", 
                "Дискриминативность", 
                "Доля пытавшихся"
            ],
            "Вклад": [
                risk_component["contrib_success"],
                risk_component["contrib_first_try"],
                risk_component["contrib_complaints"],
                risk_component["contrib_discrimination"],
                risk_component["contrib_attempted"]
            ],
            "Вес": [0.25, 0.15, 0.30, 0.20, 0.10],
            "Значение": [
                risk_component["risk_success"],
                risk_component["risk_first_try"],
                risk_component["risk_complaints"],
                risk_component["risk_discrimination"],
                risk_component["risk_attempted"]
            ]
        })
        
        # Создаем круговую диаграмму
        fig = px.pie(
            risk_components_df,
            values="Вклад",
            names="Компонент",
            title="Вклад компонентов в риск",
            color="Компонент",
            color_discrete_sequence=["#ff9040", "#ffbf80", "#ff6666", "#9370db", "#66c2a5"],
            hover_data=["Вес", "Значение"]
        )
        
        # Добавляем подписи процентов
        fig.update_traces(
            textposition='inside',
            textinfo='percent',
            hovertemplate="<b>%{label}</b><br>Вклад: %{value:.3f}<br>Вес: %{customdata[0]:.2f}<br>Значение компонента: %{customdata[1]:.2f}"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Создаем столбчатую диаграмму для сравнения компонентов риска
        fig = px.bar(
            risk_components_df,
            x="Компонент",
            y="Значение",
            color="Компонент",
            color_discrete_sequence=["#ff9040", "#ffbf80", "#ff6666", "#9370db", "#66c2a5"],
            title="Значения компонентов риска",
            hover_data=["Вес", "Вклад"]
        )
        
        # Улучшаем подсказки
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>Значение: %{y:.2f}<br>Вес: %{customdata[0]:.2f}<br>Вклад в риск: %{customdata[1]:.3f}"
        )
        
        # Добавляем горизонтальную линию для значения 0.5 (нейтральное)
        fig.add_hline(y=0.5, line_dash="dash", line_color="gray", 
                    annotation_text="Нейтральный уровень", annotation_position="left")
        
        # Добавляем верхнюю границу (1.0)
        fig.add_hline(y=1.0, line_dash="dot", line_color="red")
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Объясняем вклад каждого компонента в риск
    st.subheader("Анализ вклада компонентов в риск")
    
    # Создаем таблицу с подробным анализом
    risk_analysis = []
    
    # Анализ успешности
    success_risk = risk_component["risk_success"]
    success_contrib = risk_component["contrib_success"]
    success_weight = risk_component["weight_success"]
    
    success_text = ""
    if success_risk > 0.7:
        success_text = "Очень низкая успешность решения - критическая проблема!"
    elif success_risk > 0.5:
        success_text = "Низкая успешность решения - серьезная проблема"
    elif success_risk > 0.3:
        success_text = "Умеренная успешность решения - возможны улучшения"
    else:
        success_text = "Хорошая успешность решения - компонент в норме"
    
    success_raw_percent = (1 - card["success_rate"]) * 100
    risk_analysis.append({
        "Компонент": "Успешность",
        "Формула": f"1 - {card['success_rate']:.2%} = {success_risk:.2f}",
        "Вес": f"{success_weight:.2f}",
        "Вклад": f"{success_contrib:.3f}",
        "Доля в риске": f"{100 * success_contrib / risk_component['raw_risk']:.1f}%",
        "Анализ": f"{success_text} (неуспешно решают {success_raw_percent:.1f}% студентов)"
    })
    
    # Анализ успеха с первой попытки
    first_try_risk = risk_component["risk_first_try"]
    first_try_contrib = risk_component["contrib_first_try"]
    first_try_weight = risk_component["weight_first_try"]
    
    first_try_text = ""
    if first_try_risk > 0.7:
        first_try_text = "Очень низкий успех с первой попытки - задание неинтуитивно"
    elif first_try_risk > 0.5:
        first_try_text = "Низкий успех с первой попытки - возможно, задание недостаточно понятно"
    elif first_try_risk > 0.3:
        first_try_text = "Умеренный успех с первой попытки - можно сделать задание более понятным"
    else:
        first_try_text = "Хороший успех с первой попытки - компонент в норме"
    
    first_try_raw_percent = (1 - card["first_try_success_rate"]) * 100
    risk_analysis.append({
        "Компонент": "Успех с 1-й попытки",
        "Формула": f"1 - {card['first_try_success_rate']:.2%} = {first_try_risk:.2f}",
        "Вес": f"{first_try_weight:.2f}",
        "Вклад": f"{first_try_contrib:.3f}",
        "Доля в риске": f"{100 * first_try_contrib / risk_component['raw_risk']:.1f}%",
        "Анализ": f"{first_try_text} (не решают с первой попытки {first_try_raw_percent:.1f}% студентов)"
    })
    
    # Анализ жалоб
    complaints_risk = risk_component["risk_complaints"]
    complaints_contrib = risk_component["contrib_complaints"]
    complaints_weight = risk_component["weight_complaints"]
    
    complaints_text = ""
    if complaints_risk > 0.7:
        complaints_text = "Критически высокий уровень жалоб - требуется немедленное вмешательство!"
    elif complaints_risk > 0.5:
        complaints_text = "Высокий уровень жалоб - серьезная проблема"
    elif complaints_risk > 0.3:
        complaints_text = "Повышенный уровень жалоб - требуется внимание"
    else:
        complaints_text = "Низкий уровень жалоб - компонент в норме"
    
    complaints_raw_percent = card["complaint_rate"] * 100
    risk_analysis.append({
        "Компонент": "Жалобы",
        "Формула": f"min({card['complaint_rate']:.2%} * 3, 1) = {complaints_risk:.2f}",
        "Вес": f"{complaints_weight:.2f}",
        "Вклад": f"{complaints_contrib:.3f}",
        "Доля в риске": f"{100 * complaints_contrib / risk_component['raw_risk']:.1f}%",
        "Анализ": f"{complaints_text} (жалобы на {complaints_raw_percent:.1f}% попыток)"
    })
    
    # Анализ дискриминативности
    discrimination_risk = risk_component["risk_discrimination"]
    discrimination_contrib = risk_component["contrib_discrimination"]
    discrimination_weight = risk_component["weight_discrimination"]
    
    discrimination_text = ""
    if abs(card["discrimination_avg"] - 0.5) > 0.3:
        discrimination_text = "Критическая проблема с дискриминативностью - задание не различает знающих от незнающих"
    elif abs(card["discrimination_avg"] - 0.5) > 0.2:
        discrimination_text = "Серьезные проблемы с дискриминативностью - задание плохо различает знающих от незнающих"
    elif abs(card["discrimination_avg"] - 0.5) > 0.1:
        discrimination_text = "Умеренные проблемы с дискриминативностью - задание недостаточно хорошо различает знающих от незнающих"
    else:
        discrimination_text = "Хорошая дискриминативность - задание хорошо различает знающих от незнающих"
    
    risk_analysis.append({
        "Компонент": "Дискриминативность",
        "Формула": f"1 - {card['discrimination_avg']:.2f} = {discrimination_risk:.2f}",
        "Вес": f"{discrimination_weight:.2f}",
        "Вклад": f"{discrimination_contrib:.3f}",
        "Доля в риске": f"{100 * discrimination_contrib / risk_component['raw_risk']:.1f}%",
        "Анализ": f"{discrimination_text} (значение: {card['discrimination_avg']:.2f}, оптимально: 0.5)"
    })
    
    # Анализ доли пытавшихся
    attempted_risk = risk_component["risk_attempted"]
    attempted_contrib = risk_component["contrib_attempted"]
    attempted_weight = risk_component["weight_attempted"]
    
    attempted_text = ""
    if attempted_risk > 0.7:
        attempted_text = "Очень низкая доля пытавшихся - многие пропускают задание"
    elif attempted_risk > 0.5:
        attempted_text = "Низкая доля пытавшихся - задание часто пропускают"
    elif attempted_risk > 0.3:
        attempted_text = "Умеренная доля пытавшихся - некоторые студенты пропускают задание"
    else:
        attempted_text = "Хорошая доля пытавшихся - компонент в норме"
    
    attempted_raw_percent = card["attempted_share"] * 100
    risk_analysis.append({
        "Компонент": "Доля пытавшихся",
        "Формула": f"1 - {card['attempted_share']:.2%} = {attempted_risk:.2f}",
        "Вес": f"{attempted_weight:.2f}",
        "Вклад": f"{attempted_contrib:.3f}",
        "Доля в риске": f"{100 * attempted_contrib / risk_component['raw_risk']:.1f}%",
        "Анализ": f"{attempted_text} (пытаются решить {attempted_raw_percent:.1f}% студентов)"
    })
    
    # Отображаем итоговый риск с учетом фактора доверия
    confidence_factor = risk_component["confidence_factor"]
    raw_risk = risk_component["raw_risk"]
    adjusted_risk = risk_component["adjusted_risk"]
    
    confidence_text = ""
    if confidence_factor < 0.3:
        confidence_text = "Очень низкое доверие к метрикам из-за малого количества попыток"
    elif confidence_factor < 0.6:
        confidence_text = "Низкое доверие к метрикам из-за недостаточного количества попыток"
    elif confidence_factor < 0.9:
        confidence_text = "Умеренное доверие к метрикам"
    else:
        confidence_text = "Высокое доверие к метрикам"
    
    risk_analysis.append({
        "Компонент": "Итоговый риск",
        "Формула": f"{raw_risk:.2f} * {confidence_factor:.2f} + 0.5 * (1 - {confidence_factor:.2f}) = {adjusted_risk:.2f}",
        "Вес": "1.00",
        "Вклад": f"{adjusted_risk:.3f}",
        "Доля в риске": "100.0%",
        "Анализ": f"{confidence_text} (попыток: {int(card['total_attempts'])}, фактор доверия: {confidence_factor:.2f})"
    })
    
    # Создаем DataFrame для таблицы анализа
    risk_analysis_df = pd.DataFrame(risk_analysis)
    
    # Отображаем таблицу
    st.dataframe(risk_analysis_df, use_container_width=True, hide_index=True)
    
    # Добавляем визуализацию корректировки риска на фактор доверия
    col1, col2 = st.columns(2)
    
    with col1:
        # Создаем график показывающий итоговое вычисление риска
        fig = go.Figure()
        
        # Добавляем сырой риск
        fig.add_trace(go.Bar(
            x=["Сырой риск"],
            y=[raw_risk],
            name="Сырой риск",
            marker_color="#ff7f7f"
        ))
        
        # Добавляем корректировку (смещение к 0.5)
        correction = adjusted_risk - raw_risk
        fig.add_trace(go.Bar(
            x=["Корректировка"],
            y=[abs(correction)],
            name="Корректировка",
            marker_color="#ffe090" if correction > 0 else "#90d2ff"
        ))
        
        # Добавляем итоговый риск как линию
        fig.add_trace(go.Scatter(
            x=["Сырой риск", "Итоговый риск"],
            y=[raw_risk, adjusted_risk],
            mode="lines+markers",
            name="Итоговый риск",
            line=dict(color="black", width=2)
        ))
        
        # Настройки макета
        fig.update_layout(
            title="Корректировка риска с учетом фактора доверия",
            yaxis_title="Значение риска",
            barmode='stack' if correction > 0 else 'group'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Создаем диаграмму доверия к метрикам
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=confidence_factor,
            title={'text': "Фактор доверия к метрикам"},
            gauge={
                'axis': {'range': [0, 1]},
                'steps': [
                    {'range': [0, 0.3], 'color': "#ff7f7f"},
                    {'range': [0.3, 0.6], 'color': "#ffbf7f"},
                    {'range': [0.6, 0.9], 'color': "#ffff7f"},
                    {'range': [0.9, 1], 'color': "#7fff7f"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 2},
                    'thickness': 0.8,
                    'value': confidence_factor
                }
            }
        ))
        
        # Настройки макета
        fig.update_layout(
            title="Доверие к метрикам (зависит от числа попыток)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Добавляем разделитель
    st.markdown("---")
    
    # Генерируем рекомендации на основе анализа
    st.subheader("🔧 Рекомендации по улучшению")
    
    # Определяем наибольшую проблему
    max_contrib_component = max(risk_analysis[:-1], key=lambda x: float(x["Вклад"].replace(',', '.')))
    
    # Формируем рекомендации
    recommendations = []
    
    # Общие рекомендации на основе уровня риска
    if adjusted_risk > 0.7:
        st.error("⚠️ Критический уровень риска! Карточка требует существенной доработки.")
    elif adjusted_risk > 0.5:
        st.warning("⚠️ Высокий уровень риска! Рекомендуется доработка карточки.")
    elif adjusted_risk > 0.3:
        st.info("ℹ️ Средний уровень риска. Возможны улучшения карточки.")
    else:
        st.success("✅ Низкий уровень риска. Карточка работает хорошо.")
    
    # Рекомендации по компонентам
    # Проблемы с успешностью
    if success_risk > 0.5:
        recommendations.append({
            "Проблема": "Низкая успешность решения",
            "Рекомендация": "Упростить задание или добавить более подробное объяснение. Проверить формулировку на ясность.",
            "Приоритет": "Высокий" if success_contrib > 0.1 else "Средний"
        })
    
    # Проблемы с успехом с первой попытки
    if first_try_risk > 0.5:
        recommendations.append({
            "Проблема": "Низкий успех с первой попытки",
            "Рекомендация": "Улучшить формулировку задания. Возможно, добавить подсказку или пример решения.",
            "Приоритет": "Высокий" if first_try_contrib > 0.1 else "Средний"
        })
    
    # Проблемы с жалобами
    if complaints_risk > 0.3:
        recommendations.append({
            "Проблема": "Повышенный уровень жалоб",
            "Рекомендация": "Проанализировать причины жалоб. Проверить корректность ответов, улучшить проверку ввода.",
            "Приоритет": "Критический" if complaints_risk > 0.7 else ("Высокий" if complaints_risk > 0.5 else "Средний")
        })
    
    # Проблемы с дискриминативностью
    if abs(card["discrimination_avg"] - 0.5) > 0.2:
        if card["discrimination_avg"] < 0.3:
            recommendations.append({
                "Проблема": "Низкая дискриминативность",
                "Рекомендация": "Задание слишком сложное или запутанное. Упростить или более четко сформулировать.",
                "Приоритет": "Высокий" if discrimination_contrib > 0.1 else "Средний"
            })
        elif card["discrimination_avg"] > 0.7:
            recommendations.append({
                "Проблема": "Слишком высокая дискриминативность",
                "Рекомендация": "Задание может быть слишком простым или очевидным. Рассмотреть возможность усложнения.",
                "Приоритет": "Средний"
            })
    
    # Проблемы с долей пытавшихся
    if attempted_risk > 0.5:
        recommendations.append({
            "Проблема": "Низкая доля пытавшихся решить",
            "Рекомендация": "Проверить расположение задания в уроке. Возможно, студенты пропускают его или оно не привлекает внимание.",
            "Приоритет": "Высокий" if attempted_contrib > 0.05 else "Средний"
        })
    
    # Проблемы с доверием к метрикам
    if confidence_factor < 0.5:
        recommendations.append({
            "Проблема": "Низкое доверие к метрикам",
            "Рекомендация": "Недостаточно данных для точного анализа. Рекомендуется повторный анализ после набора большего количества попыток.",
            "Приоритет": "Информационный"
        })
    
    # Если нет рекомендаций, добавляем положительный отзыв
    if not recommendations:
        st.success("👍 Карточка работает хорошо, особых рекомендаций нет!")
    else:
        # Отображаем рекомендации
        recommendations_df = pd.DataFrame(recommendations)
        
        # Сортируем по приоритету
        priority_order = {
            "Критический": 0,
            "Высокий": 1,
            "Средний": 2,
            "Низкий": 3,
            "Информационный": 4
        }
        
        recommendations_df["Сортировка"] = recommendations_df["Приоритет"].map(priority_order)
        recommendations_df = recommendations_df.sort_values("Сортировка").drop("Сортировка", axis=1)
        
        # Отображаем таблицу рекомендаций
        st.dataframe(recommendations_df, use_container_width=True, hide_index=True)
    
    # Добавляем разделитель
    st.markdown("---")
    
    # Добавляем кнопки действий в конце страницы
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔙 Вернуться к списку карточек", key="bottom_back"):
            st.session_state["filter_card_id"] = None
            st.rerun()
    
    with col2:
        if "card_url" in card and pd.notna(card["card_url"]):
            st.markdown(f"[🔗 Открыть карточку в редакторе]({card['card_url']})")
    
    with col3:
        # Кнопка для перехода к другой карточке группы заданий
        next_card = df_filtered[df_filtered['card_id'] != card_filter].sample(1)['card_id'].iloc[0] if len(df_filtered) > 1 else None
        
        if next_card:
            if st.button(f"🔄 Перейти к другой карточке (ID: {int(next_card)})", key="next_card"):
                st.session_state["filter_card_id"] = next_card
                st.rerun()
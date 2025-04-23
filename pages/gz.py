# pages/gz.py
"""
Страница группы заданий (Обзор + навигация по карточкам)
Включает функциональность анализа карточек из прежней страницы cards.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import urllib.parse as ul

import core
from components.utils import create_hierarchical_header, display_clickable_items, add_gz_links
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_cards_chart, display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart, display_completion_radar, display_trickiness_chart, display_trickiness_success_chart

def page_gz(df: pd.DataFrame, create_link_fn=None):
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
    
    # Проверяем наличие колонки trickiness_level
    if "trickiness_level" not in df_gz.columns:
        df_gz["trickiness_level"] = df_gz.apply(core.get_trickiness_level, axis=1)
        
    # Добавляем разницу между общей успешностью и успехом с первой попытки
    df_gz["success_diff"] = df_gz["success_rate"] - df_gz["first_try_success_rate"]
    
    # Сортируем по риску для лучшей визуализации
    df_cards = df_gz.copy().sort_values("risk", ascending=False).reset_index(drop=True)
    df_cards["card_num"] = df_cards.index + 1  # Перенумеруем после сортировки
    
    # Создаем столбчатую диаграмму риска по карточкам
    display_cards_chart(
        df_cards,
        x_col="card_num",
        y_cols="risk",
        title="Уровень риска по карточкам",
        sort_by="risk",
        ascending=False
    )
    
    # 4. Детальное сравнение карточек (используя компоненты из прежней страницы cards)
    st.subheader("📊 Детальное сравнение карточек")
    
    # Создаем вкладки для разных представлений
    tabs = st.tabs([
        "Ключевые метрики", 
        "Успешность и жалобы", 
        "Типы карточек", 
        "Трики-карточки",
        "Дискриминативность"
    ])
    
    with tabs[0]:
        # График сравнения нескольких метрик для карточек
        display_cards_chart(
            df_cards,
            x_col="card_num",
            y_cols=["success_rate", "first_try_success_rate", "complaint_rate"],
            title="Сравнение ключевых метрик по карточкам",
            barmode="group",
            color_discrete_sequence=["#4da6ff", "#ff9040", "#ff6666"]
        )
    
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
            
            # Сравнение метрик по типам карточек
            fig2 = px.bar(
                card_type_stats,
                x="card_type",
                y=["success", "complaints", "risk"],
                barmode="group",
                labels={
                    "card_type": "Тип карточки",
                    "value": "Значение",
                    "variable": "Метрика"
                },
                title="Сравнение метрик по типам карточек",
                color_discrete_sequence=["#4da6ff", "#ff6666", "#ff7f7f"]
            )
            
            # Переименование легенды
            fig2.for_each_trace(lambda t: t.update(name = {
                "success": "Успешность",
                "complaints": "Жалобы",
                "risk": "Риск"
            }.get(t.name, t.name)))
            
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("В этой группе заданий все карточки одного типа.")
    
    with tabs[3]:
        # Анализ трики-карточек
        st.markdown("### Анализ \"трики\"-карточек")
        
        # Подсчитываем количество трики-карточек
        tricky_count = (df_gz["trickiness_level"] > 0).sum()
        
        if tricky_count > 0:
            # Отображаем распределение трики-карточек по уровням
            tricky_levels = df_gz["trickiness_level"].value_counts().sort_index()
            
            # Создаем DataFrame для отображения статистики
            tricky_df = pd.DataFrame({
                "Уровень": ["Нет подлости", "Низкий", "Средний", "Высокий"],
                "Количество": [
                    tricky_levels.get(0, 0),
                    tricky_levels.get(1, 0),
                    tricky_levels.get(2, 0),
                    tricky_levels.get(3, 0)
                ]
            })
            
            # Показываем статистику
            col1, col2 = st.columns(2)
            
            with col1:
                # Показываем общую статистику
                st.metric("Трики-карточек", tricky_count, f"{tricky_count/len(df_gz):.1%} от всех карточек")
                
                # Показываем распределение по уровням
                st.markdown("#### Распределение по уровням подлости")
                for i, row in tricky_df.iterrows():
                    if i == 0:  # Пропускаем "Нет подлости"
                        continue
                    
                    level = row["Уровень"]
                    count = row["Количество"]
                    percent = count / len(df_gz) * 100
                    
                    # Выбираем цвет в зависимости от уровня
                    color = "yellow"
                    if level == "Средний":
                        color = "orange"
                    elif level == "Высокий":
                        color = "red"
                    
                    st.markdown(f"**{level}**: <span style='color:{color};'>{count}</span> ({percent:.1f}%)", unsafe_allow_html=True)
            
            with col2:
                # Создаем круговую диаграмму для распределения трики-карточек
                fig = px.pie(
                    tricky_df[tricky_df["Количество"] > 0],
                    values="Количество",
                    names="Уровень",
                    title="Распределение по уровням подлости",
                    color="Уровень",
                    color_discrete_map={
                        "Нет подлости": "#c0c0c0",
                        "Низкий": "#ffff7f",
                        "Средний": "#ffaa7f",
                        "Высокий": "#ff7f7f"
                    }
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Отображаем график подлости карточек
            display_trickiness_chart(df_gz, x_col="card_id", limit=50, title="Уровень подлости карточек")
            
            # Отображаем диаграмму рассеяния для трики-карточек
            display_trickiness_success_chart(df_gz, limit=50)
            
            # Отображаем таблицу с трики-карточками
            tricky_cards = df_gz[df_gz["trickiness_level"] > 0].sort_values("trickiness_level", ascending=False)
            
            if not tricky_cards.empty:
                st.markdown("#### Список трики-карточек")
                
                # Создаем таблицу с данными трики-карточек
                tricky_table = tricky_cards[["card_id", "card_type", "success_rate", "first_try_success_rate", "success_diff", "risk", "trickiness_level"]]
                
                # Добавляем колонку с уровнем подлости
                tricky_table["Уровень подлости"] = tricky_table["trickiness_level"].map({
                    1: "Низкий",
                    2: "Средний",
                    3: "Высокий"
                })
                
                # Переименовываем и форматируем столбцы для отображения
                display_df = pd.DataFrame()
                display_df["ID карточки"] = tricky_table["card_id"]
                display_df["Тип"] = tricky_table["card_type"]
                display_df["Успешность"] = tricky_table["success_rate"].apply(lambda x: f"{x:.1%}")
                display_df["Успех с 1-й"] = tricky_table["first_try_success_rate"].apply(lambda x: f"{x:.1%}")
                display_df["Разница"] = tricky_table["success_diff"].apply(lambda x: f"{x:.1%}")
                display_df["Уровень подлости"] = tricky_table["Уровень подлости"]
                display_df["Риск"] = tricky_table["risk"].apply(lambda x: f"{x:.2f}")
                
                # Добавляем ссылки на карточки
                # Используем create_link_fn для создания URL, если функция доступна
                if create_link_fn:
                    display_df["Действия"] = tricky_cards.apply(
                        lambda row: f"[Детальный анализ]({create_link_fn('cards', card_id=int(row['card_id']))})" 
                        if pd.notna(row['card_id']) else "-", 
                        axis=1
                    )
                else:
                    # Относительный URL как запасной вариант
                    display_df["Действия"] = tricky_cards.apply(
                        lambda row: f"[Детальный анализ](?page=cards&card_id={int(row['card_id'])})" 
                        if pd.notna(row['card_id']) else "-", 
                        axis=1
                    )
                
                # Отображаем таблицу
                st.dataframe(display_df, use_container_width=True)
        else:
            st.info("В этой группе заданий нет трики-карточек.")
    
    with tabs[4]:
        # Анализ дискриминативности карточек
        st.markdown("### Анализ дискриминативности карточек")
        
        # Создаем график дискриминативности
        fig = px.bar(
            df_cards,
            x="card_num",
            y="discrimination_avg",
            color="success_rate",
            color_continuous_scale="RdYlGn",
            title="Индекс дискриминативности по карточкам",
            labels={"card_num": "Номер карточки", "discrimination_avg": "Дискриминативность"},
            hover_data=["card_id", "card_type"]
        )
        
        # Добавляем горизонтальные линии для границ категорий
        fig.add_hline(y=0.35, line_dash="dash", line_color="green", 
                      annotation_text="Хорошая", annotation_position="left")
        fig.add_hline(y=0.15, line_dash="dash", line_color="red", 
                      annotation_text="Низкая", annotation_position="left")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Распределение по категориям дискриминативности
        good_discr = (df_gz["discrimination_avg"] >= 0.35).sum()
        medium_discr = ((df_gz["discrimination_avg"] < 0.35) & (df_gz["discrimination_avg"] >= 0.15)).sum()
        low_discr = (df_gz["discrimination_avg"] < 0.15).sum()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Хорошая дискр. (>0.35)", good_discr, f"{good_discr/len(df_gz):.1%}")
        
        with col2:
            st.metric("Средняя дискр. (0.15-0.35)", medium_discr, f"{medium_discr/len(df_gz):.1%}")
        
        with col3:
            st.metric("Низкая дискр. (<0.15)", low_discr, f"{low_discr/len(df_gz):.1%}")
        
        # Показываем карточки с низкой дискриминативностью
        if low_discr > 0:
            st.markdown("#### Карточки с низкой дискриминативностью")
            low_discr_cards = df_gz[df_gz["discrimination_avg"] < 0.15].sort_values("discrimination_avg")
            
            # Создаем таблицу
            display_df = pd.DataFrame()
            display_df["ID карточки"] = low_discr_cards["card_id"]
            display_df["Тип"] = low_discr_cards["card_type"]
            display_df["Дискриминативность"] = low_discr_cards["discrimination_avg"].apply(lambda x: f"{x:.3f}")
            display_df["Успешность"] = low_discr_cards["success_rate"].apply(lambda x: f"{x:.1%}")
            display_df["Риск"] = low_discr_cards["risk"].apply(lambda x: f"{x:.2f}")
            
            # Добавляем ссылки на карточки
            # Используем create_link_fn для создания URL, если функция доступна
            if create_link_fn:
                display_df["Действия"] = low_discr_cards.apply(
                    lambda row: f"[Детальный анализ]({create_link_fn('cards', card_id=int(row['card_id']))})" 
                    if pd.notna(row['card_id']) else "-", 
                    axis=1
                )
            else:
                # Относительный URL как запасной вариант
                display_df["Действия"] = low_discr_cards.apply(
                    lambda row: f"[Детальный анализ](?page=cards&card_id={int(row['card_id'])})" 
                    if pd.notna(row['card_id']) else "-", 
                    axis=1
                )
            
            # Отображаем таблицу
            st.dataframe(display_df, use_container_width=True)
    
    # 5. Таблица с карточками и ссылками на карточки
    st.subheader("📋 Детальная информация по карточкам")
    
    # Отображаем таблицу
    cards_df = df_gz[["card_id", "card_type", "status", "success_rate", 
                      "first_try_success_rate", "complaint_rate", 
                      "discrimination_avg", "total_attempts", "risk", "trickiness_level"]]
    
    # Добавляем номер в таблицу для соответствия с графиками
    cards_df = cards_df.sort_values("risk", ascending=False).reset_index(drop=True)
    cards_df["Номер"] = cards_df.index + 1
    
    # Переорганизуем колонки, чтобы номер был в начале
    cards_df = cards_df[["Номер", "card_id", "card_type", "status", "success_rate", 
                         "first_try_success_rate", "complaint_rate", 
                         "discrimination_avg", "total_attempts", "risk", "trickiness_level"]]
    
    # Создаем таблицу с данными для отображения
    display_df = pd.DataFrame()
    display_df["Номер"] = cards_df["Номер"]
    display_df["ID карточки"] = cards_df["card_id"]
    display_df["Тип"] = cards_df["card_type"]
    display_df["Статус"] = cards_df["status"]
    display_df["Успешность"] = cards_df["success_rate"].apply(lambda x: f"{x:.1%}")
    display_df["Успех с 1-й"] = cards_df["first_try_success_rate"].apply(lambda x: f"{x:.1%}")
    display_df["Жалобы"] = cards_df["complaint_rate"].apply(lambda x: f"{x:.1%}")
    display_df["Дискр."] = cards_df["discrimination_avg"].apply(lambda x: f"{x:.2f}")
    display_df["Попытки"] = cards_df["total_attempts"].apply(lambda x: f"{int(x)}")
    display_df["Риск"] = cards_df["risk"].apply(lambda x: f"{x:.2f}")
    
    # Добавляем категорию подлости
    trickiness_categories = {
        0: "Нет",
        1: "Низкий",
        2: "Средний",
        3: "Высокий"
    }
    display_df["Подлость"] = cards_df["trickiness_level"].map(trickiness_categories)
    
    # Добавляем ссылки на страницу детального анализа карточки
    if create_link_fn:
        display_df["Действия"] = cards_df.apply(
            lambda row: f"[Детальный анализ]({create_link_fn('cards', card_id=int(row['card_id']))})" 
            if pd.notna(row['card_id']) else "-", 
            axis=1
        )
    else:
        display_df["Действия"] = cards_df.apply(
            lambda row: f"[Детальный анализ](?page=cards&card_id={int(row['card_id'])})" 
            if pd.notna(row['card_id']) else "-", 
            axis=1
        )
    
    # Добавляем ссылки на карточки в редакторе, если доступны URL
    if "card_url" in df_gz.columns:
        display_df["Редактор"] = df_gz.apply(
            lambda row: f"[Открыть]({row['card_url']})" if pd.notna(row['card_url']) else "-", 
            axis=1
        )
    
    # Отображаем таблицу
    st.dataframe(display_df, hide_index=True, use_container_width=True)
    
    # 6. Кнопки для быстрого перехода к анализу отдельных карточек
    st.subheader("🔍 Анализ отдельных карточек")
    
    # Создаем список карточек с высоким риском
    high_risk_cards = df_gz[df_gz["risk"] > 0.5].sort_values("risk", ascending=False)
    
    if not high_risk_cards.empty:
        st.markdown("### Карточки с высоким риском")
        
        # Создаем кнопки для быстрого перехода
        cols = st.columns(4)
        for i, (_, card) in enumerate(high_risk_cards.iterrows()):
            col_idx = i % 4
            with cols[col_idx]:
                card_id = int(card["card_id"])
                risk = card["risk"]
                card_type = card["card_type"]
                
                # Создаем цвет на основе риска
                color = "red" if risk > 0.75 else "orange"
                
                # Используем create_link_fn для создания URL, если функция доступна
                if create_link_fn:
                    card_url = create_link_fn("cards", card_id=card_id)
                else:
                    # Относительный URL как запасной вариант
                    card_url = f"?page=cards&card_id={card_id}"
                
                # Создаем кнопку с соответствующим цветом
                st.markdown(
                    f"<a href='{card_url}' target='_self' "
                    f"style='text-decoration:none;color:{color};'>"
                    f"ID: {card_id} - Риск: {risk:.2f} - {card_type}</a>",
                    unsafe_allow_html=True
                )
                
                # Ограничиваем количество отображаемых карточек
                if i >= 11:  # Показываем максимум 12 карточек
                    st.markdown(f"И еще {len(high_risk_cards) - 12} карточек...")
                    break
    
    # Создаем список трики-карточек
    tricky_cards = df_gz[df_gz["trickiness_level"] > 0].sort_values("trickiness_level", ascending=False)
    
    if not tricky_cards.empty:
        st.markdown("### Трики-карточки")
        
        # Создаем кнопки для быстрого перехода
        cols = st.columns(4)
        for i, (_, card) in enumerate(tricky_cards.iterrows()):
            col_idx = i % 4
            with cols[col_idx]:
                card_id = int(card["card_id"])
                trickiness = card["trickiness_level"]
                card_type = card["card_type"]
                
                # Создаем цвет на основе уровня подлости
                color = "red" if trickiness == 3 else ("orange" if trickiness == 2 else "gold")
                
                # Используем create_link_fn для создания URL, если функция доступна
                if create_link_fn:
                    card_url = create_link_fn("cards", card_id=card_id)
                else:
                    # Относительный URL как запасной вариант
                    card_url = f"?page=cards&card_id={card_id}"
                
                # Создаем кнопку с соответствующим цветом
                trickiness_text = trickiness_categories.get(trickiness, "")
                st.markdown(
                    f"<a href='{card_url}' target='_self' "
                    f"style='text-decoration:none;color:{color};'>"
                    f"ID: {card_id} - Подлость: {trickiness_text} - {card_type}</a>",
                    unsafe_allow_html=True
                )
                
                # Ограничиваем количество отображаемых карточек
                if i >= 11:  # Показываем максимум 12 карточек
                    st.markdown(f"И еще {len(tricky_cards) - 12} карточек...")
                    break
    
    # Создаем список карточек с низкой дискриминативностью
    low_discr_cards = df_gz[df_gz["discrimination_avg"] < 0.15].sort_values("discrimination_avg")
    
    if not low_discr_cards.empty:
        st.markdown("### Карточки с низкой дискриминативностью")
        
        # Создаем кнопки для быстрого перехода
        cols = st.columns(4)
        for i, (_, card) in enumerate(low_discr_cards.iterrows()):
            col_idx = i % 4
            with cols[col_idx]:
                card_id = int(card["card_id"])
                discr = card["discrimination_avg"]
                card_type = card["card_type"]
                
                # Используем create_link_fn для создания URL, если функция доступна
                if create_link_fn:
                    card_url = create_link_fn("cards", card_id=card_id)
                else:
                    # Относительный URL как запасной вариант
                    card_url = f"?page=cards&card_id={card_id}"
                
                # Создаем кнопку
                st.markdown(
                    f"<a href='{card_url}' target='_self' "
                    f"style='text-decoration:none;color:purple;'>"
                    f"ID: {card_id} - Дискр.: {discr:.2f} - {card_type}</a>",
                    unsafe_allow_html=True
                )
                
                # Ограничиваем количество отображаемых карточек
                if i >= 11:  # Показываем максимум 12 карточек
                    st.markdown(f"И еще {len(low_discr_cards) - 12} карточек...")
                    break

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
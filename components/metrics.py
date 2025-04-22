# components/metrics.py
"""
Переиспользуемые компоненты для отображения метрик и статистики
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Исправление в components/metrics.py или в соответствующей функции

def display_trickiness_distribution(df, group_by_col=None):
    """
    Отображает распределение уровней подлости карточек.
    
    Args:
        df: DataFrame с данными
        group_by_col: Колонка для группировки (если None, используются все данные)
    """
    # Проверяем наличие колонки trickiness_level
    if "trickiness_level" not in df.columns:
        df["trickiness_level"] = df.apply(core.get_trickiness_level, axis=1)
    
    # Определяем категории подлости
    trickiness_categories = {
        0: "Нет подлости",
        1: "Низкий уровень подлости",
        2: "Средний уровень подлости",
        3: "Высокий уровень подлости"
    }
    
    # Добавляем колонку с текстовыми категориями
    df["trickiness_category"] = df["trickiness_level"].map(trickiness_categories)
    
    if group_by_col is not None:
        # Группируем данные по указанной колонке
        trickiness_distribution = []
        
        for _, group in df.groupby(group_by_col):
            trickiness_counts = group["trickiness_level"].value_counts().sort_index()
            name = group[group_by_col].iloc[0]
            
            for level, count in trickiness_counts.items():
                trickiness_distribution.append({
                    "name": name,
                    "level": level,
                    "category": trickiness_categories.get(level, "Неизвестно"),
                    "count": count
                })
        
        trickiness_df = pd.DataFrame(trickiness_distribution)
        
        # Группируем по категории и считаем общее количество
        overall_distribution = trickiness_df.groupby("category")["count"].sum().reset_index()
        overall_distribution.columns = ["Категория подлости", "Количество"]
        
        # Устанавливаем правильный порядок категорий
        category_order = list(trickiness_categories.values())
        overall_distribution["Категория подлости"] = pd.Categorical(
            overall_distribution["Категория подлости"], 
            categories=category_order, 
            ordered=True
        )
        overall_distribution = overall_distribution.sort_values("Категория подлости")
    else:
        # Используем все данные напрямую
        trickiness_counts = df["trickiness_level"].value_counts().sort_index()
        
        overall_distribution = pd.DataFrame({
            "Категория подлости": [trickiness_categories.get(level, "Неизвестно") for level in trickiness_counts.index],
            "Количество": trickiness_counts.values
        })
        
        # Устанавливаем правильный порядок категорий
        category_order = list(trickiness_categories.values())
        overall_distribution["Категория подлости"] = pd.Categorical(
            overall_distribution["Категория подлости"], 
            categories=category_order, 
            ordered=True
        )
        overall_distribution = overall_distribution.sort_values("Категория подлости")
    
    # Цветовая схема для уровней подлости
    color_map = {
        "Нет подлости": "#c0c0c0",  # серый
        "Низкий уровень подлости": "#ffff7f",  # желтый
        "Средний уровень подлости": "#ffaa7f",  # оранжевый
        "Высокий уровень подлости": "#ff7f7f"   # красный
    }
    
    # Создаем диаграмму
    fig = px.bar(
        overall_distribution,
        x="Категория подлости",
        y="Количество",
        color="Категория подлости",
        color_discrete_map=color_map,
        title="Распределение по уровням подлости"
    )
    
    # Форматируем подсказки
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>" +
                      "Количество: %{y}"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    return overall_distribution

def update_display_metrics_row(df, group_by_col=None, compare_with=None):
    """
    Дополняет функцию display_metrics_row для отображения метрики подлости
    
    Args:
        df: DataFrame с данными
        group_by_col: Колонка для группировки (если None, используются все данные)
        compare_with: DataFrame для сравнения (если указан, показывает дельту)
    """
    # Проверяем наличие колонки trickiness_level
    if "trickiness_level" not in df.columns:
        df["trickiness_level"] = df.apply(core.get_trickiness_level, axis=1)
    
    # Вычисляем средний уровень подлости
    if group_by_col is not None:
        # Агрегируем данные по указанной колонке
        df_agg = df.groupby(group_by_col).agg(
            trickiness_avg=("trickiness_level", "mean")
        ).reset_index()
        
        # Вычисляем средний уровень подлости
        avg_trickiness = df_agg["trickiness_avg"].mean()
    else:
        # Используем все данные
        avg_trickiness = df["trickiness_level"].mean()
    
    # Если есть данные для сравнения, вычисляем дельту
    if compare_with is not None and "trickiness_level" in compare_with.columns:
        trickiness_delta = avg_trickiness - compare_with["trickiness_level"].mean()
    else:
        trickiness_delta = None
    
    # Возвращаем результаты для дополнения отображения метрик
    return {
        "avg_trickiness": avg_trickiness,
        "trickiness_delta": trickiness_delta
    }

# Добавляем функцию для отображения метрики подлости
def display_trickiness_metric(avg_trickiness, trickiness_delta=None):
    """
    Отображает метрику среднего уровня подлости
    
    Args:
        avg_trickiness: Средний уровень подлости
        trickiness_delta: Дельта относительно другого набора данных (опционально)
    """
    # Определяем цвет метрики в зависимости от уровня подлости
    trickiness_color = "#4da6ff"  # Стандартный цвет метрики
    
    # Отображаем метрику подлости
    st.metric(
        "Средний уровень подлости", 
        f"{avg_trickiness:.2f}", 
        f"{trickiness_delta:.2f}" if trickiness_delta is not None else None, 
        delta_color="inverse"  # Инвертируем цвет дельты (т.к. увеличение подлости - негативно)
    )
    
    # Дополнительная информация об интерпретации уровня подлости
    trickiness_info = ""
    if avg_trickiness < 0.5:
        trickiness_info = "Низкий уровень подлости"
    elif avg_trickiness < 1.5:
        trickiness_info = "В основном низкий уровень"
    elif avg_trickiness < 2.0:
        trickiness_info = "Средний уровень подлости"
    elif avg_trickiness < 2.5:
        trickiness_info = "Преимущественно средний уровень"
    else:
        trickiness_info = "Высокий уровень подлости"
    
    # Возвращаем информацию для дополнительного отображения
    return trickiness_info

# Функция для расчета распределения карточек по уровням подлости
def get_trickiness_distribution(df):
    """
    Рассчитывает распределение карточек по уровням подлости
    
    Args:
        df: DataFrame с данными
        
    Returns:
        dict: Словарь с количеством карточек по уровням подлости
    """
    # Проверяем наличие колонки trickiness_level
    if "trickiness_level" not in df.columns:
        df["trickiness_level"] = df.apply(core.get_trickiness_level, axis=1)
    
    # Считаем количество карточек по уровням подлости
    trickiness_distribution = df["trickiness_level"].value_counts().to_dict()
    
    # Обеспечиваем наличие всех ключей
    for level in range(4):  # 0, 1, 2, 3
        if level not in trickiness_distribution:
            trickiness_distribution[level] = 0
    
    # Возвращаем распределение
    return trickiness_distribution

def display_metrics_row(df, group_by_col=None, compare_with=None):
    """
    Отображает ряд ключевых метрик для DataFrame
    
    Args:
        df: DataFrame с данными
        group_by_col: Колонка для группировки (если None, используются все данные)
        compare_with: DataFrame для сравнения (если указан, показывает дельту)
    """
    if group_by_col is not None:
        # Агрегируем данные по указанной колонке
        df_agg = df.groupby(group_by_col).agg(
            success_rate=("success_rate", "mean"),
            complaint_rate=("complaint_rate", "mean"),
            discrimination_avg=("discrimination_avg", "mean"),
            risk=("risk", "mean"),
            total_items=("card_id", "nunique")
        ).reset_index()
        
        # Вычисляем средние метрики
        avg_success = df_agg["success_rate"].mean()
        avg_complaints = df_agg["complaint_rate"].mean()
        avg_discrimination = df_agg["discrimination_avg"].mean()
        avg_risk = df_agg["risk"].mean()
        total_items = df_agg["total_items"].sum()
    else:
        # Используем все данные
        avg_success = df["success_rate"].mean()
        avg_complaints = df["complaint_rate"].mean()
        avg_discrimination = df["discrimination_avg"].mean()
        avg_risk = df["risk"].mean()
        total_items = len(df["card_id"].unique())
    
    # Если есть данные для сравнения, вычисляем дельту
    if compare_with is not None:
        success_delta = avg_success - compare_with["success_rate"].mean()
        complaints_delta = avg_complaints - compare_with["complaint_rate"].mean()
        discrimination_delta = avg_discrimination - compare_with["discrimination_avg"].mean()
        risk_delta = avg_risk - compare_with["risk"].mean()
    else:
        success_delta = None
        complaints_delta = None
        discrimination_delta = None
        risk_delta = None
    
    # Отображаем метрики в ряд
    cols = st.columns(4)
    
    with cols[0]:
        # Обратите внимание - первое значение (label) - это заголовок, второе (value) - это показатель метрики
        st.metric(
            "Средний успех", 
            f"{avg_success:.1%}", 
            f"{success_delta:.1%}" if success_delta is not None else None
        )
        
    with cols[1]:
        st.metric(
            "Средний % жалоб", 
            f"{avg_complaints:.1%}", 
            f"{complaints_delta:.1%}" if complaints_delta is not None else None, 
            delta_color="inverse"
        )
        
    with cols[2]:
        st.metric(
            "Средняя дискриминативность", 
            f"{avg_discrimination:.2f}", 
            f"{discrimination_delta:.2f}" if discrimination_delta is not None else None
        )
        
    with cols[3]:
        st.metric(
            "Средний риск", 
            f"{avg_risk:.2f}", 
            f"{risk_delta:.2f}" if risk_delta is not None else None, 
            delta_color="inverse"
        )
    
    # Отображаем дополнительные метрики во втором ряду
    cols2 = st.columns(4)
    
    with cols2[0]:
        st.metric("Всего элементов", f"{total_items:,}")
    
    # Вычисляем количество заданий с высоким риском
    high_risk_count = len(df[df["risk"] > 0.7])
    
    with cols2[1]:
        st.metric(
            "Элементов высокого риска", 
            f"{high_risk_count}", 
            f"{high_risk_count/total_items:.1%} от общего числа", 
            delta_color="inverse"
        )
    
    # Добавляем метрики использования попыток, если доступны
    if "total_attempts" in df.columns and "attempted_share" in df.columns:
        total_attempts = df["total_attempts"].sum()
        avg_attempted = df["attempted_share"].mean()
        
        with cols2[2]:
            st.metric("Всего попыток", f"{int(total_attempts):,}")
            
        with cols2[3]:
            st.metric("Среднее участие", f"{avg_attempted:.1%}")
    
    return {
        "avg_success": avg_success,
        "avg_complaints": avg_complaints, 
        "avg_discrimination": avg_discrimination,
        "avg_risk": avg_risk,
        "total_items": total_items,
        "high_risk_count": high_risk_count
    }

def display_status_chart(df, item_col=None):
    """
    Отображает круговую диаграмму распределения статусов
    
    Args:
        df: DataFrame с данными 
        item_col: Колонка для группировки (если None, используются все строки)
    """
    # Если указана колонка для группировки, агрегируем по ней
    if item_col is not None:
        # Сначала определим преобладающий статус для каждого элемента
        status_by_item = df.groupby(item_col)["status"].agg(
            lambda x: x.mode().iloc[0] if not x.mode().empty else "unknown"
        ).reset_index()
        
        status_counts = status_by_item["status"].value_counts().reset_index()
    else:
        # Используем все строки
        status_counts = df["status"].value_counts().reset_index()
    
    status_counts.columns = ["Статус", "Количество"]
    
    # Создаем круговую диаграмму
    status_fig = px.pie(
        status_counts,
        values="Количество",
        names="Статус",
        title="Распределение по статусам",
        color="Статус",
        color_discrete_map={
            "new": "#d3d3d3",
            "in_work": "#add8e6",
            "ready_for_qc": "#fffacd",
            "done": "#90ee90",
            "wont_fix": "#f08080",
            "unknown": "#cccccc"
        },
        hole=0.4
    )
    
    st.plotly_chart(status_fig, use_container_width=True)

def display_risk_distribution(df, group_by_col=None):
    """
    Отображает распределение риска по категориям
    
    Args:
        df: DataFrame с данными
        group_by_col: Колонка для группировки (если None, используются все данные)
    """
    if group_by_col is not None:
        # Группируем данные по указанной колонке
        risk_categories = []
        
        for _, group in df.groupby(group_by_col):
            avg_risk = group["risk"].mean()
            name = group[group_by_col].iloc[0]
            
            if avg_risk < 0.25:                # Было 0.3
                category = "Низкий риск"
            elif avg_risk < 0.5:               # Остается 0.5
                category = "Умеренный риск"    # Было "Средний риск"
            elif avg_risk < 0.75:              # Было 0.7
                category = "Высокий риск"
            else:
                category = "Критический риск"  # Было "Очень высокий риск"
                
            risk_categories.append({"name": name, "risk": avg_risk, "category": category})
        
        risk_df = pd.DataFrame(risk_categories)
        
        # Вычисляем распределение риска по категориям
        risk_distribution = risk_df["category"].value_counts().reset_index()
        risk_distribution.columns = ["Категория риска", "Количество"]
        
        # Устанавливаем правильный порядок категорий
        risk_order = ["Низкий риск", "Умеренный риск", "Высокий риск", "Критический риск"]  # Обновите порядок категорий
        risk_distribution["Категория риска"] = pd.Categorical(
            risk_distribution["Категория риска"], 
            categories=risk_order, 
            ordered=True
        )
        risk_distribution = risk_distribution.sort_values("Категория риска")
        
        color_map = {
            "Низкий риск": "#7FFF7F",
            "Умеренный риск": "#FFFF7F",   # Было "Средний риск"
            "Высокий риск": "#FFAA7F",
            "Критический риск": "#FF7F7F"  # Было "Очень высокий риск"
        }
        
        # Создаем диаграмму
        fig = px.bar(
            risk_distribution,
            x="Категория риска",
            y="Количество",
            color="Категория риска",
            color_discrete_map=color_map,
            title="Распределение по уровням риска"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Если нет группировки, показываем гистограмму риска
        fig = px.histogram(
            df,
            x="risk",
            nbins=20,
            color_discrete_sequence=["#FF9F7F"],
            labels={"risk": "Риск", "count": "Количество"},
            title="Распределение риска"
        )
        
        # Добавляем вертикальные линии для границ категорий
        fig.add_vline(x=0.25, line_dash="dash", line_color="green",         # Было 0.3
                      annotation_text="Низкий", annotation_position="top")
        fig.add_vline(x=0.5, line_dash="dash", line_color="yellow",         # Остается 0.5
                      annotation_text="Умеренный", annotation_position="top") # Было "Средний"
        fig.add_vline(x=0.75, line_dash="dash", line_color="red",           # Было 0.7
                      annotation_text="Высокий", annotation_position="top")
        
        # Добавьте дополнительную линию для критического риска
        fig.add_vline(x=0.75, line_dash="dash", line_color="darkred",
                      annotation_text="Критический", annotation_position="top")
        
        st.plotly_chart(fig, use_container_width=True)
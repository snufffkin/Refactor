# components/charts.py
"""
Переиспользуемые компоненты для отображения графиков и визуализаций
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


# Добавьте эту новую вспомогательную функцию в начало файла charts.py

def display_cards_chart(df, x_col="card_id", y_cols=None, title=None, barmode="group", 
                       sort_by="risk", ascending=False, limit=50, 
                       color_discrete_sequence=None):
    """
    Отображает график данных карточек, заменяя ID на последовательные номера
    
    Args:
        df: DataFrame с данными карточек
        x_col: Колонка с ID карточек
        y_cols: Список колонок для отображения (может быть одна колонка или список)
        title: Заголовок графика
        barmode: Режим отображения столбцов ('group', 'stack', и т.д.)
        sort_by: Колонка для сортировки
        ascending: Порядок сортировки
        limit: Максимальное количество элементов
        color_discrete_sequence: Список цветов для столбцов
    """
    import streamlit as st
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    
    # Проверяем, что y_cols - это список
    if y_cols is None:
        y_cols = ["success_rate"]
    elif isinstance(y_cols, str):
        y_cols = [y_cols]
    
    # Задаем понятные названия метрик
    metric_labels = {
        "success_rate": "Успешность",
        "first_try_success_rate": "Успех с 1-й попытки",
        "complaint_rate": "Жалобы",
        "discrimination_avg": "Дискриминативность",
        "attempted_share": "Доля участия",
        "risk": "Риск"
    }
    
    # Копируем DataFrame и сортируем
    sorted_df = df.copy()
    
    if sort_by is not None:
        sorted_df = sorted_df.sort_values(by=sort_by, ascending=ascending)
    
    # Ограничиваем количество элементов, если нужно
    if limit is not None and len(sorted_df) > limit:
        sorted_df = sorted_df.head(limit)
    
    # Создаем новый столбец с порядковыми номерами
    sorted_df = sorted_df.reset_index(drop=True)
    sorted_df["card_num"] = sorted_df.index + 1  # Начинаем с 1 для лучшего восприятия пользователем
    
    # Создаем график
    if len(y_cols) == 1:
        # Для одной метрики используем px.bar с цветовой схемой
        y_col = y_cols[0]
        
        # Определяем цветовую схему в зависимости от метрики
        if y_col == "risk":
            color_scale = "RdYlGn_r"
        elif y_col in ["success_rate", "first_try_success_rate", "discrimination_avg"]:
            color_scale = "RdYlGn"
        else:
            color_scale = "Blues"
        
        fig = px.bar(
            sorted_df,
            x="card_num",
            y=y_col,
            color=y_col,
            color_continuous_scale=color_scale,
            labels={
                "card_num": "Номер карточки", 
                y_col: metric_labels.get(y_col, y_col)
            },
            title=title or f"{metric_labels.get(y_col, y_col)} по карточкам",
            hover_data=[x_col, "card_type"] + ([col for col in y_cols if col != y_col])
        )
        
        # Форматируем подсказки
        hover_format = ":.1%" if y_col in ["success_rate", "first_try_success_rate", "complaint_rate", "attempted_share"] else ":.2f"
        fig.update_traces(
            hovertemplate=f"<b>ID: %{{customdata[0]}}</b><br>" +
                          f"Номер: %{{x}}<br>" +
                          f"Тип: %{{customdata[1]}}<br>" +
                          f"{metric_labels.get(y_col, y_col)}: %{{y{hover_format}}}"
        )
    else:
        # Для нескольких метрик используем go.Figure для группировки
        fig = go.Figure()
        
        # Определяем цвета для разных метрик
        if color_discrete_sequence is None:
            color_map = {
                "success_rate": "#4da6ff",
                "first_try_success_rate": "#ff9040",
                "complaint_rate": "#ff6666",
                "discrimination_avg": "#9370db",
                "attempted_share": "#66c2a5",
                "risk": "#ff7f7f"
            }
            color_discrete_sequence = [color_map.get(col, "#999999") for col in y_cols]
        
        # Добавляем столбцы для каждой метрики
        for i, col in enumerate(y_cols):
            # Определяем формат значений и названия
            is_percent = col in ["success_rate", "first_try_success_rate", "complaint_rate", "attempted_share"]
            hover_format = ":.1%" if is_percent else ":.2f"
            name = metric_labels.get(col, col)
            
            # Создаем текст подсказки
            hovertemplate = (
                f"<b>ID: {{{{customdata[0]}}}}</b><br>" +
                f"Номер: {{{{x}}}}<br>" +
                f"Тип: {{{{customdata[1]}}}}<br>" +
                f"{name}: {{{{'y{hover_format}'}}}}"
            )
            
            fig.add_trace(go.Bar(
                x=sorted_df["card_num"],
                y=sorted_df[col],
                name=name,
                marker_color=color_discrete_sequence[i % len(color_discrete_sequence)],
                customdata=sorted_df[[x_col, "card_type"]],
                hovertemplate=hovertemplate
            ))
        
        # Настройка группировки столбцов
        fig.update_layout(barmode=barmode)
        
        # Добавляем заголовок
        if title is None:
            metrics_names = [metric_labels.get(col, col) for col in y_cols]
            title = f"Сравнение метрик ({', '.join(metrics_names)})"
        
        fig.update_layout(title=title)
    
    # Настраиваем оси X - показываем порядковый номер и добавляем метку с ID карточки
    fig.update_layout(
        xaxis=dict(
            title="Номер карточки",
            tickmode='array',
            tickvals=sorted_df["card_num"],
            ticktext=sorted_df["card_num"],
            tickangle=0
        ),
        yaxis_title="Значение",
        yaxis_tickformat=".0%" if all(col in ["success_rate", "first_try_success_rate", "complaint_rate", "attempted_share"] for col in y_cols) else None,
        hoverlabel=dict(
            bgcolor="white",
            font_size=12
        )
    )
    
    # Отображаем график
    st.plotly_chart(fig, use_container_width=True)
    
    # Возвращаем отсортированный датафрейм с добавленными номерами для возможного использования
    return sorted_df


def prepare_sequential_ids(df, id_column, sort_by=None, ascending=False, limit=None):
    """
    Подготавливает DataFrame для отображения на графике с последовательными ID без пропусков
    
    Args:
        df: DataFrame с данными
        id_column: Название колонки с ID
        sort_by: Колонка для сортировки (если None, сортировка по id_column)
        ascending: Порядок сортировки
        limit: Максимальное количество элементов
    
    Returns:
        DataFrame с добавленной колонкой для последовательного отображения
    """
    # Копируем датафрейм
    result_df = df.copy()
    
    # Сортируем, если указана колонка
    if sort_by is not None:
        result_df = result_df.sort_values(by=sort_by, ascending=ascending)
    
    # Ограничиваем количество, если указано
    if limit is not None:
        result_df = result_df.head(limit)
    
    # Создаем последовательный индекс без пропусков
    result_df = result_df.reset_index(drop=True)
    result_df["sequential_index"] = range(len(result_df))
    
    # Сохраняем оригинальные ID для отображения в hover
    result_df["original_id"] = result_df[id_column]
    
    # Создаем короткую версию ID для отображения
    if result_df[id_column].dtype == "object" or result_df[id_column].dtype == "string":
        result_df["display_id"] = result_df[id_column]
    else:
        # Если числовой тип, используем последние 4 цифры или весь ID
        result_df["display_id"] = result_df[id_column].astype(str).str[-4:]
    
    return result_df
    
def display_risk_bar_chart(df, category_col, limit=20, title=None, height=None):
    """
    Отображает столбчатую диаграмму риска по категориям
    
    Args:
        df: DataFrame с данными
        category_col: Колонка с категориями для группировки
        limit: Максимальное количество элементов для отображения
        title: Заголовок графика (если None, будет сгенерирован)
        height: Высота графика (если None, используется автоматическое значение)
    """
    # Группируем данные по указанной колонке и вычисляем средний риск
    agg_df = df.groupby(category_col).agg(
        risk=("risk", "mean"),
        success=("success_rate", "mean"),
        complaints=("complaint_rate", "mean"),
        items=("card_id", "nunique")
    ).reset_index()
    
    # Сортируем по риску (от высокого к низкому)
    sorted_df = agg_df.sort_values("risk", ascending=False).head(limit)
    
    # Создаем заголовок, если не указан
    if title is None:
        title = f"Уровень риска по {category_col}"
    
    # Создаем график
    fig = px.bar(
        sorted_df,
        x=category_col,
        y="risk",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        labels={category_col: category_col.capitalize(), "risk": "Риск"},
        title=title,
        height=height,
        hover_data=["success", "complaints", "items"]
    )
    
    # Форматируем подсказки
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>" +
                      "Риск: %{y:.2f}<br>" +
                      "Успешность: %{customdata[0]:.1%}<br>" +
                      "Жалобы: %{customdata[1]:.1%}<br>" +
                      "Элементов: %{customdata[2]}"
    )
    
    # Добавляем горизонтальные линии для границ категорий риска
    fig.add_hline(y=0.3, line_dash="dash", line_color="green", 
                  annotation_text="Низкий риск", annotation_position="left")
    fig.add_hline(y=0.5, line_dash="dash", line_color="gold", 
                  annotation_text="Средний риск", annotation_position="left")
    fig.add_hline(y=0.7, line_dash="dash", line_color="red", 
                  annotation_text="Высокий риск", annotation_position="left")
    
    # Настройка макета
    fig.update_layout(
        xaxis_title=category_col.capitalize(),
        yaxis_title="Уровень риска",
        xaxis_tickangle=-45 if len(sorted_df) > 8 else 0
    )
    
    # Отображаем график
    st.plotly_chart(fig, use_container_width=True)
    
    return sorted_df

def display_metrics_comparison(df, category_col, value_cols, limit=10, title=None):
    """
    Отображает сравнение нескольких метрик по категориям
    
    Args:
        df: DataFrame с данными
        category_col: Колонка с категориями для группировки
        value_cols: Список колонок с метриками для сравнения
        limit: Максимальное количество элементов для отображения
        title: Заголовок графика (если None, будет сгенерирован)
    """
    # Задаем понятные названия метрик
    metric_labels = {
        "success_rate": "Успешность",
        "first_try_success_rate": "Успех с 1-й попытки",
        "complaint_rate": "Процент жалоб",
        "discrimination_avg": "Дискриминативность",
        "attempted_share": "Доля участия",
        "risk": "Риск"
    }
    
    # Группируем данные по указанной колонке
    agg_df = df.groupby(category_col)[value_cols].mean().reset_index()
    
    # Сортируем по первой метрике
    sorted_df = agg_df.sort_values(value_cols[0], ascending=False).head(limit)
    
    # Создаем заголовок, если не указан
    if title is None:
        metrics_names = [metric_labels.get(col, col) for col in value_cols]
        title = f"Сравнение метрик ({', '.join(metrics_names)})"
    
    # Создаем график
    fig = go.Figure()
    
    # Определяем цвета для метрик
    color_map = {
        "success_rate": "#4da6ff",
        "first_try_success_rate": "#ff9040",
        "complaint_rate": "#ff6666",
        "discrimination_avg": "#9370db",
        "attempted_share": "#66c2a5",
        "risk": "#ff7f7f"
    }
    
    # Добавляем линии для каждой метрики
    for col in value_cols:
        # Определяем формат значений
        if col in ["complaint_rate", "success_rate", "first_try_success_rate", "attempted_share"]:
            hovertemplate = "%{y:.1%}"
        else:
            hovertemplate = "%{y:.2f}"
        
        fig.add_trace(go.Bar(
            x=sorted_df[category_col],
            y=sorted_df[col],
            name=metric_labels.get(col, col),
            marker_color=color_map.get(col, "#999999"),
            hovertemplate=hovertemplate
        ))
    
    # Настройка макета
    fig.update_layout(
        title=title,
        xaxis_title=category_col.capitalize(),
        yaxis_tickformat=".1%" if any(col in ["complaint_rate", "success_rate", "first_try_success_rate", "attempted_share"] 
                                    for col in value_cols) else None,
        xaxis_tickangle=-45 if len(sorted_df) > 8 else 0,
        barmode='group',
        legend_title="Метрики"
    )
    
    # Отображаем график
    st.plotly_chart(fig, use_container_width=True)
    
    return sorted_df

def display_success_complaints_chart(df, category_col, limit=15, title=None):
    """
    Отображает зависимость между успешностью и жалобами
    
    Args:
        df: DataFrame с данными
        category_col: Колонка с категориями для группировки
        limit: Максимальное количество элементов для отображения
        title: Заголовок графика (если None, будет сгенерирован)
    """
    # Группируем данные по указанной колонке
    agg_df = df.groupby(category_col).agg(
        success=("success_rate", "mean"),
        complaints=("complaint_rate", "mean"),
        risk=("risk", "mean"),
        discrimination=("discrimination_avg", "mean"),
        items=("card_id", "nunique")
    ).reset_index()
    
    # Сортируем по риску для выбора самых интересных точек
    sorted_df = agg_df.sort_values("risk", ascending=False).head(limit)
    
    # Вычисляем имеющийся максимум попыток
    if "total_attempts" in df.columns:
        attempts_sum = df.groupby(category_col)["total_attempts"].sum().reset_index()
        sorted_df = sorted_df.merge(attempts_sum, on=category_col, how="left")
        size_col = "total_attempts"
    else:
        sorted_df["size_proxy"] = sorted_df["items"] * 10  # Прокси для размера маркера
        size_col = "size_proxy"
    
    # Создаем заголовок, если не указан
    if title is None:
        title = f"Зависимость успешности и жалоб"
    
    # Создаем график
    fig = px.scatter(
        sorted_df,
        x="success",
        y="complaints",
        color="risk",
        size=size_col,
        hover_name=category_col,
        color_continuous_scale="RdYlGn_r",
        labels={
            "success": "Успешность", 
            "complaints": "Процент жалоб",
            "risk": "Риск"
        },
        title=title,
        hover_data={
            category_col: True,
            "success": ":.1%",
            "complaints": ":.1%",
            "risk": ":.2f",
            "discrimination": ":.2f",
            "items": True,
            size_col: False  # Скрываем переменную размера из подсказки
        }
    )
    
    # Добавляем текстовые метки к точкам
    fig.update_traces(
        textposition='top center',
        textfont=dict(size=10)
    )
    
    # Настройка макета
    fig.update_layout(
        xaxis_title="Успешность",
        yaxis_title="Процент жалоб",
        xaxis_tickformat=".0%",
        yaxis_tickformat=".1%"
    )
    
    # Отображаем график
    st.plotly_chart(fig, use_container_width=True)
    
    return sorted_df

def display_completion_radar(df, category_col, limit=5, title=None):
    """
    Отображает радарную диаграмму для ключевых метрик
    
    Args:
        df: DataFrame с данными
        category_col: Колонка с категориями для группировки
        limit: Максимальное количество элементов для отображения
        title: Заголовок графика (если None, будет сгенерирован)
    """
    # Проверяем наличие необходимых колонок
    required_cols = [
        "success_rate", "first_try_success_rate", 
        "complaint_rate", "discrimination_avg", "risk"
    ]
    
    # Группируем данные по указанной колонке
    agg_df = df.groupby(category_col).agg(
        success_rate=("success_rate", "mean"),
        first_try_success_rate=("first_try_success_rate", "mean") if "first_try_success_rate" in df.columns else ("success_rate", "mean"),
        complaint_rate=("complaint_rate", "mean"),
        discrimination_avg=("discrimination_avg", "mean"),
        risk=("risk", "mean"),
        items=("card_id", "nunique")
    ).reset_index()
    
    # Сортируем по риску и выбираем верхние N элементов
    top_items = agg_df.sort_values("risk", ascending=False).head(limit)
    
    # Создаем заголовок, если не указан
    if title is None:
        title = f"Сравнение метрик для {limit} элементов с высоким риском"
    
    # Создаем радарную диаграмму
    fig = go.Figure()
    
    # Определяем метрики для радара
    radar_metrics = [
        "success_rate", "first_try_success_rate", 
        "discrimination_avg", "complaint_rate_inv", "risk_inv"
    ]
    
    # Определяем метки для метрик
    metric_labels = {
        "success_rate": "Успешность",
        "first_try_success_rate": "Успех с 1-й попытки",
        "discrimination_avg": "Дискриминативность",
        "complaint_rate_inv": "Отсутствие жалоб",
        "risk_inv": "Низкий риск"
    }
    
    # Нормализуем значения (чтобы 1 всегда было хорошо)
    for _, item in top_items.iterrows():
        # Инвертируем метрики, где меньше - лучше
        item_data = {
            "success_rate": item["success_rate"],
            "first_try_success_rate": item["first_try_success_rate"],
            "discrimination_avg": item["discrimination_avg"],
            "complaint_rate_inv": 1 - item["complaint_rate"],
            "risk_inv": 1 - item["risk"]
        }
        
        # Добавляем на радар
        fig.add_trace(go.Scatterpolar(
            r=[item_data[m] for m in radar_metrics],
            theta=[metric_labels[m] for m in radar_metrics],
            fill='toself',
            name=f"{item[category_col]} (риск: {item['risk']:.2f})"
        ))
    
    # Настройка макета
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        title=title
    )
    
    # Отображаем график
    st.plotly_chart(fig, use_container_width=True)
    
    return top_items

# Дополнения в components/charts.py

def display_trickiness_chart(df, x_col="card_id", limit=50, title="Уровень подлости карточек"):
    """
    Отображает график уровня подлости для карточек
    
    Args:
        df: DataFrame с данными
        x_col: Колонка с идентификаторами (обычно card_id)
        limit: Максимальное количество элементов для отображения
        title: Заголовок графика
    """
    # Проверяем наличие колонки trickiness_level
    if "trickiness_level" not in df.columns:
        df["trickiness_level"] = df.apply(core.get_trickiness_level, axis=1)
    
    # Сортируем по уровню подлости (от высокого к низкому)
    sorted_df = df.sort_values(by="trickiness_level", ascending=False).head(limit)
    
    # Добавляем последовательную нумерацию
    sorted_df = sorted_df.reset_index(drop=True)
    sorted_df["card_num"] = sorted_df.index + 1
    
    # Определяем категории для подлости
    trickiness_categories = {
        0: "Нет подлости",
        1: "Низкий уровень",
        2: "Средний уровень",
        3: "Высокий уровень"
    }
    sorted_df["trickiness_category"] = sorted_df["trickiness_level"].map(trickiness_categories)
    
    # Создаем цветовую схему
    color_map = {
        "Нет подлости": "#c0c0c0",  # серый
        "Низкий уровень": "#ffff7f",  # желтый
        "Средний уровень": "#ffaa7f",  # оранжевый
        "Высокий уровень": "#ff7f7f"   # красный
    }
    
    # Создаем график
    fig = px.bar(
        sorted_df,
        x="card_num",
        y="trickiness_level",
        color="trickiness_category",
        color_discrete_map=color_map,
        labels={"card_num": "Номер карточки", "trickiness_level": "Уровень подлости"},
        title=title,
        hover_data=[x_col, "success_rate", "first_try_success_rate", "card_type"]
    )
    
    # Добавляем горизонтальные линии для границ категорий
    fig.add_hline(y=0.5, line_dash="dash", line_color="gray", 
                 annotation_text="Граница подлости", annotation_position="left")
    fig.add_hline(y=1.5, line_dash="dash", line_color="gold", 
                 annotation_text="Граница среднего уровня", annotation_position="left")
    fig.add_hline(y=2.5, line_dash="dash", line_color="red", 
                 annotation_text="Граница высокого уровня", annotation_position="left")
    
    # Форматируем подсказки
    fig.update_traces(
        hovertemplate="<b>ID: %{customdata[0]}</b><br>" +
                      "Номер: %{x}<br>" +
                      "Уровень подлости: %{y}<br>" +
                      "Категория: %{marker.color}<br>" +
                      "Общая успешность: %{customdata[1]:.1%}<br>" +
                      "Успех с 1-й попытки: %{customdata[2]:.1%}<br>" +
                      "Тип: %{customdata[3]}"
    )
    
    # Настраиваем ось Y для отображения целых чисел
    fig.update_layout(
        yaxis=dict(
            tickmode='array',
            tickvals=[0, 1, 2, 3],
            ticktext=["0 (Нет)", "1 (Низкий)", "2 (Средний)", "3 (Высокий)"]
        )
    )
    
    # Отображаем график
    st.plotly_chart(fig, use_container_width=True)
    
    return sorted_df

def display_trickiness_success_chart(df, limit=50, title="Зависимость подлости от успешности и первой попытки"):
    """
    Отображает точечную диаграмму зависимости подлости от успешности и первой попытки
    
    Args:
        df: DataFrame с данными
        limit: Максимальное количество элементов для отображения
        title: Заголовок графика
    """
    # Проверяем наличие колонки trickiness_level
    if "trickiness_level" not in df.columns:
        df["trickiness_level"] = df.apply(core.get_trickiness_level, axis=1)
    
    # Отбираем только карточки с некоторым уровнем подлости
    tricky_df = df[df["trickiness_level"] > 0].copy()
    
    # Если таких карточек нет, показываем сообщение
    if tricky_df.empty:
        st.info("В выбранных данных нет карточек с подлостью")
        return None
    
    # Ограничиваем количество карточек для отображения
    if len(tricky_df) > limit:
        tricky_df = tricky_df.sort_values(by="trickiness_level", ascending=False).head(limit)
    
    # Определяем категории для подлости
    trickiness_categories = {
        1: "Низкий уровень",
        2: "Средний уровень",
        3: "Высокий уровень"
    }
    tricky_df["trickiness_category"] = tricky_df["trickiness_level"].map(trickiness_categories)
    
    # Добавляем разницу между успешностью и успехом с первой попытки
    tricky_df["success_diff"] = tricky_df["success_rate"] - tricky_df["first_try_success_rate"]
    
    # Создаем цветовую схему
    color_map = {
        "Низкий уровень": "#ffff7f",  # желтый
        "Средний уровень": "#ffaa7f",  # оранжевый
        "Высокий уровень": "#ff7f7f"   # красный
    }
    
    # Создаем график
    fig = px.scatter(
        tricky_df,
        x="success_rate",
        y="first_try_success_rate",
        color="trickiness_category",
        color_discrete_map=color_map,
        size="success_diff",  # Размер точки зависит от разницы
        size_max=25,
        labels={
            "success_rate": "Общая успешность", 
            "first_try_success_rate": "Успешность с первой попытки",
            "trickiness_category": "Уровень подлости"
        },
        title=title,
        hover_data=["card_id", "success_diff", "card_type", "complaint_rate"]
    )
    
    # Добавляем диагональную линию равенства
    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            line=dict(color="gray", dash="dash", width=1),
            name="Успешность = Успешность с 1-й попытки",
            hoverinfo="skip"
        )
    )
    
    # Получаем параметры трики-карточек из конфигурации
    config = core.get_config()
    tricky_config = config.get("tricky_cards", {})
    
    # Получаем базовые параметры
    basic_config = tricky_config.get("basic", {})
    min_success_rate = basic_config.get("min_success_rate", 0.70)
    max_first_try_rate = basic_config.get("max_first_try_rate", 0.60)
    min_difference = basic_config.get("min_difference", 0.20)
    
    # Получаем параметры зон
    zones_config = tricky_config.get("zones", {})
    high_success_threshold = zones_config.get("high_success_threshold", 0.90)
    medium_success_threshold = zones_config.get("medium_success_threshold", 0.80)
    low_first_try_threshold = zones_config.get("low_first_try_threshold", 0.40)
    medium_first_try_threshold = zones_config.get("medium_first_try_threshold", 0.50)
    
    # Добавляем диагональную линию минимальной разницы
    x_values = np.linspace(min_success_rate, 1, 100)
    y_values = [min(x - min_difference, max_first_try_rate) for x in x_values]
    
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=y_values,
            mode="lines",
            line=dict(color="purple", dash="dot", width=1),
            name=f"Минимальная разница: {min_difference:.2f}",
            hoverinfo="skip"
        )
    )
    
    # Добавляем зоны "подлости"
    fig.add_shape(
        type="rect",
        x0=min_success_rate,
        y0=0,
        x1=1,
        y1=max_first_try_rate,
        fillcolor="rgba(255,255,0,0.2)",
        line=dict(color="yellow", width=1, dash="dash"),
        layer="below",
        name="Зона низкой подлости"
    )
    
    fig.add_shape(
        type="rect",
        x0=medium_success_threshold,
        y0=0,
        x1=1,
        y1=medium_first_try_threshold,
        fillcolor="rgba(255,165,0,0.3)",
        line=dict(color="orange", width=1, dash="dash"),
        layer="below",
        name="Зона средней подлости"
    )
    
    fig.add_shape(
        type="rect",
        x0=high_success_threshold,
        y0=0,
        x1=1,
        y1=low_first_try_threshold,
        fillcolor="rgba(255,0,0,0.4)",
        line=dict(color="red", width=1, dash="dash"),
        layer="below",
        name="Зона высокой подлости"
    )
    
    # Настройка макета
    fig.update_layout(
        xaxis=dict(
            title="Общая успешность",
            range=[0, 1],
            tickformat=".0%"
        ),
        yaxis=dict(
            title="Успешность с первой попытки",
            range=[0, 1],
            tickformat=".0%"
        )
    )
    
    # Форматируем подсказки
    fig.update_traces(
        hovertemplate="<b>ID: %{customdata[0]}</b><br>" +
                      "Общая успешность: %{x:.1%}<br>" +
                      "Успех с 1-й попытки: %{y:.1%}<br>" +
                      "Разница: %{customdata[1]:.1%}<br>" +
                      "Тип: %{customdata[2]}<br>" +
                      "Жалобы: %{customdata[3]:.1%}"
    )
    
    # Отображаем график
    st.plotly_chart(fig, use_container_width=True)
    
    return tricky_df

# Обновляем функцию display_metrics_comparison для использования подлости вместо first_try
def update_metrics_comparison(df, category_col, value_cols, limit=10, title=None):
    """
    Обновленная версия display_metrics_comparison для использования подлости вместо first_try
    
    Args:
        df: DataFrame с данными
        category_col: Колонка с категориями для группировки
        value_cols: Список колонок с метриками для сравнения (включая trickiness_level)
        limit: Максимальное количество элементов для отображения
        title: Заголовок графика (если None, будет сгенерирован)
    """
    # Проверяем наличие колонки trickiness_level
    if "trickiness_level" not in df.columns and "trickiness_level" in value_cols:
        df["trickiness_level"] = df.apply(core.get_trickiness_level, axis=1)
    
    # Заменяем first_try_success_rate на trickiness_level, если такая замена требуется
    value_cols_updated = []
    for col in value_cols:
        if col == "first_try_success_rate" and "trickiness_level" not in value_cols:
            value_cols_updated.append("trickiness_level")
        else:
            value_cols_updated.append(col)
    
    # Задаем понятные названия метрик
    metric_labels = {
        "success_rate": "Успешность",
        "first_try_success_rate": "Успех с 1-й попытки",
        "trickiness_level": "Уровень подлости",
        "complaint_rate": "Процент жалоб",
        "discrimination_avg": "Дискриминативность",
        "attempted_share": "Доля участия",
        "risk": "Риск"
    }
    
    # Группируем данные по указанной колонке
    agg_df = df.groupby(category_col)[value_cols_updated].mean().reset_index()
    
    # Сортируем по первой метрике
    sorted_df = agg_df.sort_values(value_cols_updated[0], ascending=False).head(limit)
    
    # Создаем заголовок, если не указан
    if title is None:
        metrics_names = [metric_labels.get(col, col) for col in value_cols_updated]
        title = f"Сравнение метрик ({', '.join(metrics_names)})"
    
    # Создаем график
    fig = go.Figure()
    
    # Определяем цвета для метрик
    color_map = {
        "success_rate": "#4da6ff",
        "trickiness_level": "#ff9040",  # новый цвет для подлости
        "first_try_success_rate": "#ff9040",
        "complaint_rate": "#ff6666",
        "discrimination_avg": "#9370db",
        "attempted_share": "#66c2a5",
        "risk": "#ff7f7f"
    }
    
    # Добавляем линии для каждой метрики
    for col in value_cols_updated:
        # Определяем формат значений
        if col in ["complaint_rate", "success_rate", "attempted_share"]:
            hovertemplate = "%{y:.1%}"
        elif col == "trickiness_level":
            hovertemplate = "%{y:.1f}"
        else:
            hovertemplate = "%{y:.2f}"
        
        fig.add_trace(go.Bar(
            x=sorted_df[category_col],
            y=sorted_df[col],
            name=metric_labels.get(col, col),
            marker_color=color_map.get(col, "#999999"),
            hovertemplate=hovertemplate
        ))
    
    # Настройка макета
    fig.update_layout(
        title=title,
        xaxis_title=category_col.capitalize(),
        yaxis_tickformat=".1%" if any(col in ["complaint_rate", "success_rate", "attempted_share"] 
                                    for col in value_cols_updated) else None,
        xaxis_tickangle=-45 if len(sorted_df) > 8 else 0,
        barmode='group',
        legend_title="Метрики"
    )
    
    # Отображаем график
    st.plotly_chart(fig, use_container_width=True)
    
    return sorted_df
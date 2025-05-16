# components/charts.py
"""
Переиспользуемые компоненты для отображения графиков и визуализаций
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import core
from db_config import get_cloud_dsn
from sqlalchemy import create_engine, text


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
    
    # Убедимся, что указанная колонка x_col существует
    if x_col not in sorted_df.columns:
        # Если колонки нет, используем индекс + 1
        sorted_df["card_num"] = sorted_df.index + 1
        x_display = "card_num"
    else:
        # Используем переданную колонку
        x_display = x_col
    
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
            x=x_display,
            y=y_col,
            color=y_col,
            color_continuous_scale=color_scale,
            labels={
                x_display: "Номер карточки", 
                y_col: metric_labels.get(y_col, y_col)
            },
            title=title or f"{metric_labels.get(y_col, y_col)} по карточкам",
            hover_data=["card_id", "card_type"] + ([col for col in y_cols if col != y_col])
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
                x=sorted_df[x_display],
                y=sorted_df[col],
                name=name,
                marker_color=color_discrete_sequence[i % len(color_discrete_sequence)],
                customdata=sorted_df[["card_id", "card_type"]],
                hovertemplate=hovertemplate
            ))
        
        # Настройка группировки столбцов
        fig.update_layout(barmode=barmode)
        
        # Добавляем заголовок
        if title is None:
            metrics_names = [metric_labels.get(col, col) for col in y_cols]
            title = f"Сравнение метрик ({', '.join(metrics_names)})"
        
        fig.update_layout(title=title)
    
    # Настраиваем оси X - показываем значения из выбранной колонки
    fig.update_layout(
        xaxis=dict(
            title="Номер карточки",
            tickmode='array',
            tickvals=sorted_df[x_display],
            ticktext=sorted_df[x_display],
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
    
def display_risk_bar_chart(df, category_col, value_column='risk', limit=20, title=None, height=None):
    """
    Отображает столбчатую диаграмму риска по категориям
    
    Args:
        df: DataFrame с данными
        category_col: Колонка с категориями для группировки (ожидается, что это program_name)
        value_column: Колонка со значениями для оси Y (по умолчанию 'risk')
        limit: Максимальное количество элементов для отображения
        title: Заголовок графика (если None, будет сгенерирован)
        height: Высота графика (если None, используется автоматическое значение)
    """
    if df is None or df.empty:
        st.warning("Нет данных для отображения графика.")
        return pd.DataFrame()

    # Проверяем наличие необходимых колонок
    required_cols = [category_col, value_column, "success_rate", "complaint_rate"]
    if not all(col in df.columns for col in required_cols):
        missing_cols = [col for col in required_cols if col not in df.columns]
        if not ("cards_count" in df.columns or "card_id" in df.columns) and "items" not in missing_cols:
             missing_cols.append("cards_count/card_id for items")
        st.error(f"Для графика display_risk_bar_chart отсутствуют колонки: {missing_cols}. Доступные: {df.columns.tolist()}")
        return pd.DataFrame()

    # --- Начало изменений: Загрузка коротких имен программ ---
    program_short_names_df = pd.DataFrame()
    try:
        dsn = get_cloud_dsn()
        if dsn:
            engine = create_engine(dsn)
            with engine.connect() as connection:
                # Предполагаем, что category_col содержит program_name
                # или program_id, если бы он был стандартизирован.
                # Сейчас используем program_name для связи.
                # Важно: если category_col не program_name, эту логику нужно адаптировать.
                # В overview.py category_col = "program", который является копией "program_name"
                # df_for_chart["program_full"] = df_for_chart["program_name"] - это уже есть в overview.py
                query_sql = text("SELECT program_name, program_short_name FROM program_ids")
                program_short_names_df = pd.read_sql_query(query_sql, connection)
        else:
            st.warning("DSN не настроен, короткие имена программ не будут загружены.")
    except Exception as e:
        st.warning(f"Ошибка при загрузке коротких имен программ: {e}")
    
    # Объединяем с df, если есть короткие имена
    # category_col должен содержать значения, по которым можно соединить с program_name из program_ids
    # В overview.py это df_for_chart["program"], который равен df_for_chart["program_name"]
    # df_for_chart["program_full"] = df_for_chart["program_name"] - это уже есть в overview.py
    
    # Перед агрегацией, присоединим короткие имена
    # Убедимся, что в df есть колонка, совпадающая с category_col, которая является program_name
    if not program_short_names_df.empty:
        # Если category_col в df это не 'program_name', а, например, 'program_id',
        # то и в program_ids нужно выбирать 'program_id' и 'program_short_name'
        # и мержить по 'program_id'.
        # Сейчас мы ожидаем, что category_col == 'program_name'
        if category_col in df.columns and 'program_name' in program_short_names_df.columns:
            df = pd.merge(df, program_short_names_df, left_on=category_col, right_on='program_name', how='left')
            # Заполняем отсутствующие короткие имена полными именами (или значением category_col)
            if 'program_short_name' in df.columns:
                 df['program_short_name'] = df['program_short_name'].fillna(df[category_col])
            else: # Если мерж не добавил колонку (например, program_short_names_df пуст)
                 df['program_short_name'] = df[category_col]
            # Удаляем дубликат program_name, если он появился после merge и не совпадает с category_col
            if 'program_name_y' in df.columns: # sufix _y по умолчанию для правой таблицы
                df = df.drop(columns=['program_name_y'])
            if 'program_name_x' in df.columns and category_col != 'program_name_x':
                 df = df.rename(columns={'program_name_x': 'program_name_original_from_df'})


        else:
            st.warning(f"Не удалось сопоставить category_col ('{category_col}') с 'program_name' из program_ids для добавления коротких имен.")
            df['program_short_name'] = df[category_col] # Используем исходные значения, если не удалось смержить
    else:
        df['program_short_name'] = df[category_col] # Используем исходные значения, если не удалось загрузить program_ids
    
    # Если program_full не было, но есть category_col (которое является полным именем)
    if 'program_full' not in df.columns and category_col in df.columns:
        df['program_full'] = df[category_col]

    # --- Конец изменений ---

    agg_spec = {
        value_column: (value_column, "mean"),
        "success": ("success_rate", "mean"),
        "complaints": ("complaint_rate", "mean")
    }
    if "cards_count" in df.columns:
        agg_spec["items"] = ("cards_count", "sum")
    elif "card_id" in df.columns:
        agg_spec["items"] = ("card_id", "nunique")
    else:
        df["_group_count_helper"] = 1 
        agg_spec["items"] = ("_group_count_helper", "count")

    # Группируем данные по КОРОТКОМУ имени программы для отображения на оси X
    # Важно: category_col все еще используется для hover (если program_full нет)
    # или как ключ для других данных. Здесь для агрегации и оси X используем program_short_name.
    # Также нужно агрегировать program_full для hover.
    # Если program_short_name не уникальны, группировка по ним может быть некорректной.
    # Предполагаем, что program_short_name должны быть уникальны для отображения.
    # Если нет, то нужно пересмотреть.
    # Более безопасный подход - группировать по исходному category_col (полное имя или ID),
    # а program_short_name использовать только для меток оси X.
    
    # Сохраняем исходный category_col для группировки, если он содержит уникальные идентификаторы
    # program_short_name будет использоваться для отображения на оси.
    # agg_df = df.groupby(category_col).agg(**agg_spec).reset_index()
    # Чтобы сохранить и короткое, и полное имя, добавим их в агрегацию, если они есть
    if 'program_short_name' in df.columns:
        agg_spec['program_short_name_agg'] = ('program_short_name', 'first') # Берем первое короткое имя в группе
    if 'program_full' in df.columns:
        agg_spec['program_full_agg'] = ('program_full', 'first') # Берем первое полное имя в группе
    
    agg_df = df.groupby(category_col).agg(**agg_spec).reset_index()
    
    # Если program_short_name_agg не было добавлено (например, df не содержал program_short_name)
    # или если мы хотим использовать program_short_name как основную категорию для оси X,
    # нужно решить, как это повлияет на уникальность
    # Сейчас agg_df.columns будет содержать category_col, value_column, success, complaints, items,
    # и опционально program_short_name_agg, program_full_agg

    # Переименовываем агрегированные колонки обратно, если они были добавлены
    if 'program_short_name_agg' in agg_df.columns:
        agg_df.rename(columns={'program_short_name_agg': 'program_short_name'}, inplace=True)
    elif 'program_short_name' in agg_df.columns: # Если было в df, но не агрегировалось отдельно
        pass # уже есть program_short_name
    else: # Если совсем нет, используем category_col
        agg_df['program_short_name'] = agg_df[category_col]

    if 'program_full_agg' in agg_df.columns:
        agg_df.rename(columns={'program_full_agg': 'program_full'}, inplace=True)
    elif 'program_full' not in agg_df.columns: # Если не было и не агрегировалось
         agg_df['program_full'] = agg_df[category_col] # Используем category_col как полное имя

    if "_group_count_helper" in df.columns: 
        # df.drop(columns=["_group_count_helper"], inplace=True) # df может быть уже не тем
        pass # Временный столбец использовался для df, а не agg_df

    sorted_df = agg_df.sort_values(value_column, ascending=False).head(limit)
    
    if title is None:
        # Используем program_short_name или category_col для заголовка
        display_category_col_name = "program_short_name" if 'program_short_name' in sorted_df.columns else category_col
        title = f"Уровень риска по {display_category_col_name.replace('_', ' ').capitalize()}"
    
    # Обновляем customdata и hovertemplate
    # Теперь program_short_name будет на оси X
    # program_full (полное имя программы) будет в customdata для подсказки
    
    custom_data_cols = [
        sorted_df["success"],
        sorted_df["complaints"],
        sorted_df["items"]
    ]
    hover_template_parts = [
        "Риск: %{y:.2f}",
        "Успешность: %{customdata[0]:.1%}",
        "Жалобы: %{customdata[1]:.1%}",
        "Элементов: %{customdata[2]}"
    ]

    # Основной текст для hover - короткое имя (которое на оси X)
    # Дополнительно - полное имя программы
    # x_display_col = 'program_short_name' if 'program_short_name' in sorted_df.columns else category_col
    x_display_col = 'program_short_name'


    if 'program_full' in sorted_df.columns:
        custom_data_cols.append(sorted_df['program_full'])
        # hovertemplate = f"<b>%{{x}}</b> ({sorted_df['program_full']})<br>" # Не сработает, т.к. sorted_df['program_full'] это серия
        hovertemplate_title = "<b>%{x}</b> (%{customdata[3]})<br>"

    else: # Если program_full нет, используем category_col (который может быть program_name)
        # custom_data_cols.append(sorted_df[category_col]) # category_col уже будет как %{x} или его надо передать?
                                                        # %{x} это значение из колонки x_display_col
        # Если program_full нет, то x (короткое имя) и есть то, что мы хотим показать жирным.
        # Если category_col (исходное полное имя) отличается от program_short_name, его можно добавить
        if category_col in sorted_df.columns and category_col != x_display_col :
            custom_data_cols.append(sorted_df[category_col])
            hovertemplate_title = "<b>%{x}</b> (Полное: %{customdata[3]})<br>"
        else:
            hovertemplate_title = "<b>%{x}</b><br>"


    final_hovertemplate = hovertemplate_title + "<br>".join(hover_template_parts)
    
    # Если x_display_col (program_short_name) отсутствует, используем category_col
    if x_display_col not in sorted_df.columns:
        if category_col in sorted_df.columns:
            x_display_col = category_col
            # st.warning(f"Колонка '{x_display_col}' для оси X не найдена, используется '{category_col}'.")
        else: # Этого не должно произойти, если category_col был в required_cols
            st.error(f"Не найдена колонка для оси X ('{x_display_col}' или '{category_col}')")
            return pd.DataFrame()


    fig = px.bar(
        sorted_df,
        x=x_display_col, # Используем program_short_name для оси X
        y=value_column,
        color=value_column,
        color_continuous_scale="RdYlGn_r",
        labels={x_display_col: "Программа (кратко)", value_column: value_column.capitalize()},
        title=title,
        height=height
    )
    fig.update_traces(customdata=np.stack(custom_data_cols, axis=-1), hovertemplate=final_hovertemplate)
    
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
    if df is None or df.empty:
        st.warning("Нет данных для отображения графика.")
        return pd.DataFrame()

    required_cols_agg = ["success_rate", "complaint_rate", "risk", "discrimination_avg"]
    if not all(col in df.columns for col in required_cols_agg):
        missing_cols = [col for col in required_cols_agg if col not in df.columns]
        st.error(f"Для графика display_success_complaints_chart отсутствуют колонки для агрегации: {missing_cols}. Доступные: {df.columns.tolist()}")
        return pd.DataFrame()

    agg_spec_sc = {
        "success": ("success_rate", "mean"),
        "complaints": ("complaint_rate", "mean"),
        "risk": ("risk", "mean"),
        "discrimination": ("discrimination_avg", "mean")
    }
    if "cards_count" in df.columns:
        agg_spec_sc["items"] = ("cards_count", "sum")
    elif "card_id" in df.columns:
        agg_spec_sc["items"] = ("card_id", "nunique")
    else:
        df["_group_count_helper_sc"] = 1 # Временный столбец
        agg_spec_sc["items"] = ("_group_count_helper_sc", "count")

    # Группируем данные по указанной колонке
    agg_df = df.groupby(category_col).agg(**agg_spec_sc).reset_index()

    if "_group_count_helper_sc" in df.columns: # Удаляем временный столбец
        df.drop(columns=["_group_count_helper_sc"], inplace=True)

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
    agg_spec_radar = {
        "success_rate": ("success_rate", "mean"),
        "first_try_success_rate": ("first_try_success_rate", "mean") if "first_try_success_rate" in df.columns else ("success_rate", "mean"),
        "complaint_rate": ("complaint_rate", "mean"),
        "discrimination_avg": ("discrimination_avg", "mean"),
        "risk": ("risk", "mean")
    }
    temp_col_name = None # Инициализируем temp_col_name
    if "cards_count" in df.columns:
        agg_spec_radar["items"] = ("cards_count", "sum")
    elif "card_id" in df.columns:
        agg_spec_radar["items"] = ("card_id", "nunique")
    else:
        # Если нет ни cards_count, ни card_id, создаем items как количество строк в группе
        temp_col_name = "_radar_group_count_helper"
        while temp_col_name in df.columns:
            temp_col_name += "_"
        df[temp_col_name] = 1 
        agg_spec_radar["items"] = (temp_col_name, "count")

    agg_df = df.groupby(category_col).agg(**agg_spec_radar).reset_index()
    
    # Удаляем временный столбец, если он был создан
    if temp_col_name is not None and temp_col_name in df.columns: # Проверяем, что temp_col_name был установлен и существует в df
        # Убедимся, что мы удаляем столбец, который действительно использовали для агрегации, на всякий случай
        if agg_spec_radar.get("items") and agg_spec_radar["items"][0] == temp_col_name:
            # errors='ignore' полезен, если df мог быть изменен между созданием и удалением
            df.drop(columns=[temp_col_name], inplace=True, errors='ignore') 

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
    
    # Используем в качестве x либо переданное значение x_col, либо card_num
    x_display = x_col if x_col in sorted_df.columns else "card_num"
    
    # Создаем график
    fig = px.bar(
        sorted_df,
        x=x_display,
        y="trickiness_level",
        color="trickiness_category",
        color_discrete_map=color_map,
        labels={x_display: "Номер карточки", "trickiness_level": "Уровень подлости"},
        title=title,
        hover_data=["card_id", "success_rate", "first_try_success_rate", "card_type"]
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
                      f"Номер: %{{{x_display}}}<br>" +
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
    import core
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
# components/utils.py с поддержкой URL-навигации
"""
Вспомогательные функции для компонентов интерфейса
"""

import streamlit as st
import pandas as pd
import numpy as np
import navigation_utils
import re
import core

def create_hierarchical_header(levels, values, emoji_map=None):
    """
    Создает иерархический заголовок страницы в виде "лесенки" с кликабельными элементами
    
    Args:
        levels: Список названий уровней иерархии
        values: Список значений для каждого уровня
        emoji_map: Словарь с эмодзи для каждого уровня
    """
    import urllib.parse as ul
    
    if emoji_map is None:
        emoji_map = {
            "program": "📚",
            "module": "📘",
            "lesson": "📝",
            "gz": "🧩",
            "card": "🗂️"
        }
    
    # Текущая страница
    current_page = st.session_state.get("page", "Обзор").lower()
    if current_page == "⚙️ настройки":
        current_page = "admin"
    
    # Заголовок страницы
    current_level = levels[-1]
    current_value = values[-1] or '—'
    emoji = emoji_map.get(current_level, "📊")
    
    st.header(f"{emoji} {current_level.capitalize()}: {current_value}")
    
    # Создаем "лесенку" навигации с улучшенным UI и кликабельными элементами
    nav_col1, nav_col2 = st.columns([1, 3])
    
    with nav_col1:
        for level in levels:
            st.markdown(f"**{level.capitalize()}:**")
    
    with nav_col2:
        for i, value in enumerate(values):
            if value and i < len(levels):
                level = levels[i]
                # Вычисляем целевую страницу (человекочитаемое имя)
                if level == "program": target_page_name = "Программы"
                elif level == "module": target_page_name = "Модули"
                elif level == "lesson": target_page_name = "Уроки"
                elif level == "gz": target_page_name = "ГЗ"
                elif level == "card": target_page_name = "Карточки"
                else: target_page_name = level.capitalize() # Fallback

                # Собираем параметры для навигации
                params = {}
                for j, l in enumerate(levels[:i+1]):
                    if values[j]:
                        params[l] = values[j]
                # Кнопка навигации
                key = f"nav_header_{level}_{i}"
                if st.button(f"{value}", key=key):
                    # Используем зарегистрированную функцию navigate_to_app из app.py
                    if hasattr(st, 'navigate_to_app') and callable(st.navigate_to_app):
                        print(f"[create_hierarchical_header] Navigating to: {target_page_name}, params: {params}") # DEBUG
                        st.navigate_to_app(target_page_name, **params)
                    else:
                        st.error("Функция навигации (header) не настроена!")
            else:
                st.markdown(f"**{value or '—'}**")
    
    # Добавляем разделитель
    st.markdown("---")

    # Определяем целевую страницу (человекочитаемое имя)
    if level == "program": target_page_display = "Программы"
    elif level == "module": target_page_display = "Модули"
    elif level == "lesson": target_page_display = "Уроки"
    elif level == "gz": target_page_display = "ГЗ"
    elif level == "card": target_page_display = "Карточки"
    else: target_page_display = level.capitalize() # Fallback

def group_programs_by_class(df, column="program"):
    """
    Группирует программы по классам обучения (5-11) и возвращает словарь с программами по группам.
    
    Args:
        df: DataFrame с данными
        column: Название колонки с названиями программ
        
    Returns:
        dict: Словарь с группами программ по классам {класс: [список программ]}
    """
    # Получаем уникальные названия программ
    programs = df[column].unique()
    
    # Словарь для результатов
    result = {
        '5 класс': [],
        '6 класс': [],
        '7 класс': [],
        '8 класс': [],
        '9 класс': [],
        '10 класс': [],
        '11 класс': [],
        'Другие программы': []
    }
    
    # Паттерны для определения класса программы
    class_patterns = {
        '5 класс': r'для 5 класса',
        '6 класс': r'для 6 класса',
        '7 класс': r'для 7 класса',
        '8 класс': r'для 8 класса',
        '9 класс': r'для 9 класса',
        '10 класс': r'для 10 класса',
        '11 класс': r'для 11 класса'
    }
    
    # Функция извлечения года из названия программы
    def extract_year(program_name):
        # Ищем год в формате 2023-2024 или 2022-2023
        match = re.search(r'(\d{4})-(\d{4})', program_name)
        if match:
            return int(match.group(1))  # Первый год из диапазона
        return 0  # Если год не найден
    
    # Распределяем программы по классам
    for program in programs:
        classified = False
        for class_name, pattern in class_patterns.items():
            if re.search(pattern, program, re.IGNORECASE):
                result[class_name].append(program)
                classified = True
                break
        
        if not classified:
            result['Другие программы'].append(program)
    
    # Сортируем программы внутри каждого класса по году (по убыванию)
    for class_name in result:
        result[class_name] = sorted(result[class_name], key=extract_year, reverse=True)
    
    return result

def display_clickable_items(df, column, level, metrics=None):
    """
    Отображает список кликабельных элементов в две колонки
    
    Args:
        df: DataFrame с данными
        column: Колонка с названиями элементов
        level: Уровень для перехода при клике
        metrics: Список метрик для отображения рядом с элементом
    """
    import urllib.parse as ul
    
    # Получаем уникальные значения и метрики для них
    if metrics:
        agg_spec = {
            "success_rate": "mean",
            "complaint_rate": "mean",
            "risk": "mean",
        }
        if "cards_count" in df.columns and ("cards" in metrics or "cards_count" in metrics):
            agg_spec["cards"] = ("cards_count", "sum")
        elif "card_id" in df.columns and "cards" in metrics:
            agg_spec["cards"] = ("card_id", "nunique")
        
        # Фильтруем agg_spec, оставляя только те метрики, которые есть в df и запрошены
        final_agg_spec = {k: v for k, v in agg_spec.items() if v[0] in df.columns and (k in metrics or v[0] in metrics)}
        # Если cards специально не запросили, но есть cards_count/card_id, добавляем его для подсчета
        if "cards" not in final_agg_spec and "cards_count" in df.columns:
             final_agg_spec["cards"] = ("cards_count", "sum")
        elif "cards" not in final_agg_spec and "card_id" in df.columns:
             final_agg_spec["cards"] = ("card_id", "nunique")

        if not final_agg_spec: # Если нечего агрегировать из запрошенного
            # Просто берем уникальные значения из column
            agg_df = pd.DataFrame({column: df[column].unique()})
            # Добавляем пустые колонки для метрик, чтобы не было ошибок ниже
            for m_name in ["cards", "risk", "success_rate", "complaint_rate"]:
                if m_name in metrics: agg_df[m_name] = 0 if m_name == "cards" else np.nan 
        else:
            agg_df = df.groupby(column).agg(**final_agg_spec).reset_index()
    else: # Если метрики не запрошены, все равно посчитаем количество элементов
        if "cards_count" in df.columns:
            agg_df = df.groupby(column).agg(cards=("cards_count", "sum")).reset_index()
        elif "card_id" in df.columns:
            agg_df = df.groupby(column).agg(cards=("card_id", "nunique")).reset_index()
        else:
            agg_df = pd.DataFrame({column: df[column].unique()})
            agg_df["cards"] = 1 # По умолчанию 1 элемент, если нечего считать
    
    # Проверяем, есть ли в исходном DataFrame информация о порядке
    # Для модулей это module_order, для уроков - lesson_order, для ГЗ - gz_order
    order_column_map = {
        "module_name": "module_order",
        "lesson_name": "lesson_order", 
        "gz_name": "gz_order",
        "gz": "gz_order"
    }
    
    order_column = order_column_map.get(column)
    
    if order_column and order_column in df.columns:
        # Получаем порядок из исходного DataFrame
        order_df = df.groupby(column)[order_column].first().reset_index()
        # Объединяем с агрегированными данными
        sorted_df = agg_df.merge(order_df, on=column, how='left')
        # Сортируем по порядку
        sorted_df = sorted_df.sort_values(order_column)
        # Удаляем колонку с порядком, так как она больше не нужна
        sorted_df = sorted_df.drop(columns=[order_column])
    else:
        # Если порядок не задан, сортируем по алфавиту
        sorted_df = agg_df.sort_values(column)
    
    # Разбиваем на две колонки
    col1, col2 = st.columns(2)
    
    half = len(sorted_df) // 2 + len(sorted_df) % 2
    
    # Собираем текущие фильтры
    current_filters = {}
    for filter_col in ["program", "module", "lesson", "gz"]:
        if st.session_state.get(f"filter_{filter_col}"):
            current_filters[filter_col] = st.session_state[f"filter_{filter_col}"]
    
    # Определяем целевую страницу (человекочитаемое имя) - ИСПРАВЛЕННАЯ ЛОГИКА
    if level == "program": 
        target_page_display = "Программы"
    elif level == "module": 
        target_page_display = "Модули"
    elif level == "lesson": 
        target_page_display = "Уроки"
    elif level == "gz": 
        target_page_display = "ГЗ"
    elif level == "card": 
        target_page_display = "Карточки"
    else: 
        target_page_display = level.capitalize() # Fallback, маловероятен для основных уровней

    for i, (_, row) in enumerate(sorted_df.iterrows()):
        current_col = col1 if i < half else col2
        with current_col:
            # НОВЫЙ ПОДХОД: формируем url_params_for_nav только с нужными уровнями
            url_params_for_nav = {}
            # target_page_display уже определен выше как человекочитаемое имя ("Программы", "Модули" и т.д.)
            # level - это ключ уровня элемента, по которому кликаем ("program", "module", "lesson", "gz")
            # row[column] - это имя элемента (например, имя программы, имя модуля)

            # Копируем фильтры ВЫШЕ текущего `level` из st.session_state
            # core.FILTERS = ["program", "module", "lesson", "gz"]
            current_level_index_for_params = -1
            if level in core.FILTERS: # core должен быть импортирован или FILTERS доступны
                current_level_index_for_params = core.FILTERS.index(level)
            
            for idx, f_key in enumerate(core.FILTERS):
                if idx < current_level_index_for_params: # Фильтры строго выше текущего уровня
                    session_filter_value = st.session_state.get(f"filter_{f_key}")
                    if session_filter_value:
                        url_params_for_nav[f_key] = session_filter_value
                elif idx == current_level_index_for_params: # Текущий уровень
                    url_params_for_nav[f_key] = row[column] # row[column] это имя элемента текущего уровня
                    break # Останавливаемся, фильтры ниже текущего уровня не нужны
            
            # Если level не является стандартным фильтром (например, 'card_id'), 
            # но его нужно передать, он должен быть в row[column] или params из вызова display_clickable_items.
            # Эта логика здесь не покрывает произвольные параметры, только иерархические фильтры.
            # Если display_clickable_items вызывается для карточек, `level` будет 'card', `row[column]` будет card_id.
            if level not in core.FILTERS and level == "card": # Особый случай для карточек
                 url_params_for_nav["card_id"] = row[column]
                 # Также нужно добавить родительские фильтры (program, module, lesson, gz) из session_state
                 # Это уже должно быть сделано циклом выше, если card_id обрабатывается после них.
                 # Лучше, если display_clickable_items для карточек получает все родительские фильтры извне.

            # Суффикс для ключа по metrics, чтобы ключи были уникальны при разных вызовах
            metrics_suffix = "-".join(metrics) if metrics else ""
            key = f"nav_item_{level}_{metrics_suffix}_{i}"

            if st.button(f"{row[column]}", key=key):
                if hasattr(st, 'navigate_to_app') and callable(st.navigate_to_app):
                    print(f"[display_clickable_items] Navigating to: {target_page_display}, params: {url_params_for_nav}") # DEBUG
                    st.navigate_to_app(target_page_display, **url_params_for_nav) 
                else:
                    st.error("Функция навигации (clickable_items) не настроена!")
            # Показ метрик рядом с кнопкой
            if metrics:
                metrics_str = []
                if ("cards" in metrics or "cards_count" in metrics) and hasattr(row, 'cards'):
                    metrics_str.append(f"Cards: {int(row.cards) if pd.notna(row.cards) else 0}")
                if "risk" in metrics and hasattr(row, 'risk'):
                    metrics_str.append(f"Risk: {row.risk:.2f}")
                if ("success" in metrics or "success_rate" in metrics) and hasattr(row, 'success_rate'): # Проверяем оба варианта имени
                    metrics_str.append(f"Success: {row.success_rate:.1%}")
                elif ("success" in metrics or "success_rate" in metrics) and hasattr(row, 'success'): # Старый вариант для обратной совместимости
                     metrics_str.append(f"Success: {row.success:.1%}")
                if ("complaints" in metrics or "complaint_rate" in metrics) and hasattr(row, 'complaint_rate'):
                    metrics_str.append(f"Compl: {row.complaint_rate:.1%}")
                elif ("complaints" in metrics or "complaint_rate" in metrics) and hasattr(row, 'complaints'):
                     metrics_str.append(f"Compl: {row.complaints:.1%}")
                st.markdown(" | ".join(metrics_str))

def display_programs_by_class(df, column="program", metrics=None):
    """
    Отображает программы, сгруппированные по классам обучения
    
    Args:
        df: DataFrame с данными
        column: Колонка с названиями элементов
        metrics: Список метрик для отображения рядом с элементом
    """
    import urllib.parse as ul
    
    # Группируем программы по классам
    programs_by_class = group_programs_by_class(df, column)
    
    metrics_dict = {}
    if metrics:
        # Создаем словарь для агрегации
        agg_dict = {}
        possible_metrics_map = {
            "cards_count": "sum", # Если передаем cards_count, то суммируем
            "risk": "mean",
            "success_rate": "mean",
            "complaint_rate": "mean",
            "first_try_success_rate": "mean",
            "discrimination_avg": "mean"
        }

        # Проверяем, какие из запрошенных метрик доступны в df и добавляем в agg_dict
        for metric_name in metrics:
            if metric_name in df.columns:
                # Для cards_count используем имя "cards" в результате агрегации, если оно запрошено как "cards_count"
                # или если метрика "cards" была запрошена и cards_count доступен.
                if metric_name == "cards_count":
                    agg_dict["cards"] = (metric_name, possible_metrics_map.get(metric_name, "sum")) # sum or first
                elif metric_name in possible_metrics_map:
                    agg_dict[metric_name] = (metric_name, possible_metrics_map[metric_name])
            elif metric_name == "cards" and "cards_count" in df.columns: # если запросили 'cards', а есть 'cards_count'
                 agg_dict["cards"] = ("cards_count", possible_metrics_map.get("cards_count", "sum"))
            elif metric_name == "cards" and "card_id" in df.columns: # резервный вариант для cards
                 agg_dict["cards"] = ("card_id", "nunique")

        if agg_dict: # Только если есть что агрегировать
            agg_df = df.groupby(column).agg(**agg_dict).reset_index()
            # Преобразуем в словарь для быстрого доступа
            for _, row in agg_df.iterrows():
                metrics_dict[row[column]] = row
        else: # Если нечего агрегировать из запрошенных метрик
            # Создаем metrics_dict с пустыми значениями или значениями по умолчанию
            for program_name in df[column].unique():
                # Создаем объект Series с NaN или 0 для каждой запрошенной метрики
                # Это предотвратит ошибки AttributeError при попытке доступа к row.metric_name
                metric_values = {m: np.nan for m in metrics}
                if "cards" in metrics: metric_values["cards"] = 0 # default for cards
                metrics_dict[program_name] = pd.Series(metric_values)
    
    # Собираем текущие фильтры
    current_filters = {}
    for filter_col in ["program", "module", "lesson", "gz"]:
        if st.session_state.get(f"filter_{filter_col}"):
            current_filters[filter_col] = st.session_state[f"filter_{filter_col}"]
    
    # Перебираем классы с 5 по 11, затем "Другие программы"
    for class_name in list(programs_by_class.keys()):
        programs = programs_by_class[class_name]
        
        # Пропускаем пустые классы
        if not programs:
            continue
        
        st.subheader(class_name)
        
        # Разбиваем на две колонки
        col1, col2 = st.columns(2)
        half = len(programs) // 2 + len(programs) % 2
        
        for i, program in enumerate(programs):
            current_col = col1 if i < half else col2
            with current_col:
                url_params_for_nav = {}
                # Для display_programs_by_class, `level` всегда "program"
                # `program` это имя программы из цикла
                url_params_for_nav["program"] = program 
                
                metrics_suffix = "-".join(metrics) if metrics else ""
                key = f"nav_item_program_{metrics_suffix}_{class_name}_{i}"
                
                if st.button(f"{program}", key=key):
                    if hasattr(st, 'navigate_to_app') and callable(st.navigate_to_app):
                        print(f"[display_programs_by_class] Navigating to: Программы, params: {url_params_for_nav}") # DEBUG
                        st.navigate_to_app("Программы", **url_params_for_nav)
                    else:
                        st.error("Функция навигации (programs_by_class) не настроена!")
                
                # Показ метрик рядом с кнопкой
                if metrics and program in metrics_dict:
                    row = metrics_dict[program]
                    metrics_str = []
                    # Обрабатываем отображение метрик на основе того, что есть в row
                    if "cards_count" in metrics and hasattr(row, 'cards'): # "cards" - это результат агрегации cards_count
                        metrics_str.append(f"Cards: {int(row.cards) if pd.notna(row.cards) else 0}")
                    elif "cards" in metrics and hasattr(row, 'cards'): # если cards_count не передали, но cards есть
                        metrics_str.append(f"Cards: {int(row.cards) if pd.notna(row.cards) else 0}")
                    
                    if "risk" in metrics and hasattr(row, 'risk'):
                        metrics_str.append(f"Risk: {row.risk:.2f}")
                    if "success_rate" in metrics and hasattr(row, 'success_rate'):
                        metrics_str.append(f"Success: {row.success_rate:.1%}")
                    if "complaint_rate" in metrics and hasattr(row, 'complaint_rate'): # Добавлено для полноты, если будет использоваться
                        metrics_str.append(f"Compl: {row.complaint_rate:.1%}")
                    if "first_try_success_rate" in metrics and hasattr(row, 'first_try_success_rate'):
                        metrics_str.append(f"1st Try: {row.first_try_success_rate:.1%}")
                        
                    st.markdown(" | ".join(metrics_str))
        
        # Добавляем разделитель между классами
        st.markdown("---")

def add_gz_links(df, gz_filter):
    """
    Добавляет ссылки на ГЗ в начало страницы, если выбран фильтр ГЗ
    
    Args:
        df: DataFrame с данными
        gz_filter: Текущий фильтр ГЗ
    """
    # Если выбрана группа заданий, добавляем кнопки со ссылками
    if gz_filter and 'gz_id' in df.columns:
        # Получаем ID группы заданий
        gz_id = df.loc[df.gz == gz_filter, 'gz_id'].iloc[0] if not df.empty else None
        
        if gz_id:
            st.markdown("### Ссылки для группы заданий")
            link_col1, link_col2 = st.columns(2)
            
            with link_col1:
                st.markdown(f"[🔗 Ссылка для редактирования](https://education.yandex-team.ru/exercise/edit/{gz_id})")
            
            with link_col2:
                st.markdown(f"[🌐 Публичная ссылка на ГЗ](https://education.yandex.ru/classroom/public-lesson/{gz_id}/run/)")
            
            st.markdown("---")

def add_card_links(card_data):
    """
    Добавляет ссылки на карточку в начало страницы
    
    Args:
        card_data: Series с данными карточки
    """
    # Проверяем наличие необходимых данных
    if 'gz_id' in card_data and pd.notna(card_data['gz_id']):
        gz_id = card_data['gz_id']
        
        # Определяем card_order (используем card_id, если card_order отсутствует)
        card_order = card_data.get('card_order', card_data['card_id'])
        
        st.markdown("### Ссылки для карточки")
        link_col1, link_col2, link_col3 = st.columns(3)
        
        with link_col1:
            st.markdown(f"[🔗 Ссылка для редактирования](https://education.yandex-team.ru/exercise/edit/{gz_id})")
        
        with link_col2:
            st.markdown(f"[🔗 Публичная ссылка](https://education.yandex.ru/classroom/public-lesson/{gz_id}/run/{card_order}/)")
        
        with link_col3:
            st.markdown(f"[🌐 Публичная ссылка на ГЗ](https://education.yandex.ru/classroom/public-lesson/{gz_id}/run/)")
        
        st.markdown("---")
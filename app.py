# app.py — точка входа Streamlit с JSON-навигацией
"""
Обновленная версия с улучшенным интерфейсом и структурой проекта.
Поддерживает продвинутую аналитику на всех уровнях иерархии курса:
Программа -> Модуль -> Урок -> ГЗ (группы заданий) -> Карточка
"""

# ---------------- IMPORTS ------------------------------------------------------- #

import urllib.parse as ul
import streamlit as st
import os
import shutil
import pandas as pd
import auth
import multiprocessing
from typing import Dict, List, Optional, Union

auth.init_auth()

import core
import pages
import pages.my_tasks
import pages.methodist_admin
import pages.refactor_planning
import navigation_utils

# Определяем оптимальное количество потоков для системы
# Используем максимальное доступное количество CPU или 8, что меньше
MAX_WORKERS = min(multiprocessing.cpu_count(), 8)
print(f"Using {MAX_WORKERS} worker threads for parallel operations")

# Настройка страницы
st.set_page_config(
    "Course Quality Dashboard", 
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

# Применяем CSS для улучшения внешнего вида и скрытия элементов
st.markdown("""
<style>
    /* Скрыть боковую навигацию страниц */
    [data-testid="collapsedControl"] {
        display: none;
    }
    
    /* Скрыть список файлов в боковой панели */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    
    /* Скрыть разделитель после списка файлов */
    [data-testid="stSidebarNavSeparator"] {
        display: none !important;
    }
    
    /* Прижать сайдбар к краю */
    section[data-testid="stSidebar"] {
        width: auto !important;
        max-width: 320px !important;
        margin-left: 0 !important;
        padding-left: 0 !important;
    }
    
    /* Убрать отступ слева для сайдбара */
    .css-1d391kg, .css-1v3fvcr {
        padding-left: 0 !important;
    }
    
    /* Принудительный цвет текста для метрик */
    div[data-testid="stMetric"] {
        background-color: rgba(28, 131, 225, 0.1);
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    div[data-testid="stMetric"] label {
        color: #4da6ff !important; 
    }
    
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;  /* белый текст для значения */
    }
    
    div[data-testid="stMetric"] div[data-testid="stMetricDelta"] {
        color: inherit !important;  /* наследуем цвет для дельты */
    }
    
    /* Стили для навигационных ссылок */
    .nav-link {
        text-decoration: none;
        color: #4da6ff;
        font-weight: 600;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        margin-right: 0.5rem;
    }
    
    .nav-link:hover {
        background-color: rgba(77, 166, 255, 0.1);
    }
    
    .nav-link.active {
        background-color: rgba(77, 166, 255, 0.2);
    }
    
    /* Улучшения для iframe */
    iframe {
        border: none !important;
        padding: 0 !important;
    }
    
    /* Стили для скролла */
    div[data-testid="stSidebar"]::-webkit-scrollbar {
        width: 5px;
    }
    
    div[data-testid="stSidebar"]::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.1);
    }
    
    div[data-testid="stSidebar"]::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 5px;
    }
    
    div[data-testid="stSidebar"]::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.3);
    }
    
    /* Кастомизация элементов Streamlit в сайдбаре */
    div[data-testid="stSidebar"] div[data-testid="stMarkdown"] h3 {
        color: rgba(255, 255, 255, 0.7);
        font-size: 16px;
        font-weight: 600;
        margin-top: 20px;
        margin-bottom: 10px;
    }
    
    /* Стили для кнопок навигации */
    div[data-testid="stButton"] button {
        border-radius: 4px;
        font-weight: bold;
        padding: 0.5rem 0.5rem;
        min-width: 40px;
        background-color: rgba(28, 131, 225, 0.1);
        border: 1px solid rgba(77, 166, 255, 0.3);
        transition: all 0.2s ease;
        font-size: 16px;
    }
    
    div[data-testid="stButton"] button:hover {
        background-color: rgba(28, 131, 225, 0.3);
        border: 1px solid rgba(77, 166, 255, 0.6);
    }
    
    div[data-testid="stButton"] button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        background-color: rgba(28, 131, 225, 0.05);
        border: 1px solid rgba(77, 166, 255, 0.1);
    }
    
    /* Стили для контейнера панели навигации */
    .nav-container {
        margin-bottom: 10px;
        padding: 5px 0;
        border-bottom: 1px solid rgba(77, 166, 255, 0.1);
    }
    
    /* Стили для навигации в сайдбаре */
    .sidebar-nav-container {
        margin-bottom: 15px;
    }
    
    /* Стили для SVG иконок в кнопках */
    div[data-testid="stButton"] button img {
        display: inline-block;
        vertical-align: middle;
    }
    
    /* Выравнивание для кнопок в сайдбаре */
    .stButton > button {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 36px;
    }
    
    /* Стили для текста текущей страницы */
    .sidebar-nav-container div[data-testid="stMarkdown"] {
        margin-top: 8px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- FUNCTIONS ------------------------------------------------------- #

# Функция для навигации между страницами без перезагрузки
def navigate_to(page, update_url=True, **params):
    """
    Изменяет текущую страницу без полной перезагрузки приложения.
    
    Args:
        page: Название страницы для перехода
        update_url: Обновлять ли URL в адресной строке
        **params: Дополнительные параметры (фильтры, card_id и т.д.)
    """
    # Сохраняем предыдущую страницу в истории
    if "nav_history" not in st.session_state:
        st.session_state.nav_history = []
    
    # Добавляем текущую страницу в историю только если она отличается от предыдущей
    current = st.session_state.get("current_page")
    if current and current != page and (not st.session_state.nav_history or st.session_state.nav_history[-1] != current):
        st.session_state.nav_history.append(current)
    
    # Ограничиваем историю 10 последними страницами
    if len(st.session_state.nav_history) > 10:
        st.session_state.nav_history = st.session_state.nav_history[-10:]
    
    # Сохраняем новую страницу и параметры в session_state
    st.session_state.current_page = page
    
    # Обрабатываем дополнительные параметры
    for key, value in params.items():
        if key == "filter_program" or key == "program":
            st.session_state.filter_program = value
        elif key == "filter_module" or key == "module":
            st.session_state.filter_module = value
        elif key == "filter_lesson" or key == "lesson":
            st.session_state.filter_lesson = value
        elif key == "filter_gz" or key == "gz":
            st.session_state.filter_gz = value
        elif key == "card_id":
            st.session_state.selected_card_id = value
        elif key == "assignment_id":  # Добавляем поддержку assignment_id
            st.session_state.selected_assignment_id = value
        else:
            st.session_state[key] = value
    
    # Обновляем URL, если требуется
    if update_url:
        url_params = {"page": page.lower()}
        # Добавляем фильтры в URL параметры
        if "filter_program" in st.session_state and st.session_state.filter_program:
            url_params["program"] = st.session_state.filter_program
        if "filter_module" in st.session_state and st.session_state.filter_module:
            url_params["module"] = st.session_state.filter_module
        if "filter_lesson" in st.session_state and st.session_state.filter_lesson:
            url_params["lesson"] = st.session_state.filter_lesson
        if "filter_gz" in st.session_state and st.session_state.filter_gz:
            url_params["gz"] = st.session_state.filter_gz
        if "selected_card_id" in st.session_state and st.session_state.selected_card_id:
            url_params["card_id"] = st.session_state.selected_card_id
        if "selected_assignment_id" in st.session_state and st.session_state.selected_assignment_id:
            url_params["assignment_id"] = st.session_state.selected_assignment_id
        
        # Обновляем URL без перезагрузки страницы
        st.query_params = url_params
        # Добавляем текущие параметры в историю навигации системы navigation_utils
        navigation_utils.add_to_history(url_params)

# Функция для возврата на предыдущую страницу
def go_back():
    """Возвращает на предыдущую страницу из истории навигации"""
    if "nav_history" in st.session_state and st.session_state.nav_history:
        prev_page = st.session_state.nav_history.pop()
        
        # Проверяем, является ли prev_page словарем или строкой
        if isinstance(prev_page, dict):
            # Если это словарь параметров URL
            page = prev_page.get("page", "overview")
            
            # Преобразуем page в название страницы для session_state
            if page == "overview":
                st.session_state.current_page = "Обзор"
            elif page == "programs":
                st.session_state.current_page = "Программы"
            elif page == "modules":
                st.session_state.current_page = "Модули"
            elif page == "lessons":
                st.session_state.current_page = "Уроки"
            elif page == "gz":
                st.session_state.current_page = "ГЗ"
            elif page == "cards":
                st.session_state.current_page = "Карточки"
            elif page == "admin":
                st.session_state.current_page = "⚙️ Настройки"
            else:
                st.session_state.current_page = "Обзор"
            
            # Синхронизируем фильтры из параметров URL
            for filter_name in core.FILTERS:
                if filter_name in prev_page:
                    st.session_state[f"filter_{filter_name}"] = prev_page[filter_name]
                else:
                    # Очищаем неиспользуемые фильтры
                    if f"filter_{filter_name}" in st.session_state:
                        del st.session_state[f"filter_{filter_name}"]
            
            # Обрабатываем особые параметры (card_id)
            if "card_id" in prev_page:
                st.session_state["selected_card_id"] = prev_page["card_id"]
            elif "selected_card_id" in st.session_state:
                del st.session_state["selected_card_id"]
                
            # Используем параметры напрямую
            st.query_params = prev_page
            # Добавляем параметры в историю навигации navigation_utils
            navigation_utils.add_to_history(prev_page)
        else:
            # Если это строка с названием страницы (старый формат)
            # Сначала меняем страницу
            st.session_state.current_page = prev_page
            # Затем обновляем URL
            page_lower = prev_page.lower()
            if page_lower == "обзор":
                page_lower = "overview"
            elif page_lower == "программы":
                page_lower = "programs"
            elif page_lower == "модули":
                page_lower = "modules"
            elif page_lower == "уроки":
                page_lower = "lessons"
            elif page_lower == "гз":
                page_lower = "gz"
            elif page_lower == "карточки":
                page_lower = "cards"
            elif page_lower == "⚙️ настройки":
                page_lower = "admin"
            
            # Обновляем URL с новой страницей
            current_params = dict(st.query_params)
            current_params["page"] = page_lower
            st.query_params = current_params
            # Добавляем параметры в историю навигации navigation_utils
            navigation_utils.add_to_history(current_params)
        
        return True
    return False

# Функция для установки фильтров из URL-параметров
def set_filters_from_params(params_arg):
    """Устанавливает фильтры на основе параметров URL"""
    print(f"[set_filters_from_params] Полученные параметры: {params_arg}")
    # Проходим по всем возможным фильтрам
    # ВАЖНО: core.FILTERS определяет ключи, которые мы ищем в params_arg
    # Убедимся, что core.FILTERS = ["program", "module", "lesson", "gz"]
    # или что мы правильно обрабатываем ключи params_arg
    filter_keys_from_url = {
        "program": "filter_program",
        "module": "filter_module",
        "lesson": "filter_lesson",
        "gz": "filter_gz"
    }

    for url_key, session_key in filter_keys_from_url.items():
        if url_key in params_arg:
            param_value = params_arg[url_key]
            # Если значение - это список, берем первый элемент (streamlit может так делать)
            if isinstance(param_value, list):
                param_value = param_value[0] if param_value else None 
            
            if param_value is not None:
                st.session_state[session_key] = param_value
                print(f"[set_filters_from_params] Установлен {session_key} = {param_value}")
            elif session_key in st.session_state: # Если параметр пришел пустым, но был в session_state, удаляем
                del st.session_state[session_key]
                print(f"[set_filters_from_params] Удален {session_key} из session_state, так как параметр в URL пуст")

    # Обрабатываем дополнительные параметры из URL
    if "card_id" in params_arg:
        card_id_val = params_arg["card_id"]
        if isinstance(card_id_val, list):
            card_id_val = card_id_val[0] if card_id_val else None
        if card_id_val is not None:
            st.session_state.selected_card_id = card_id_val
            print(f"[set_filters_from_params] Установлен selected_card_id = {card_id_val}")
        elif "selected_card_id" in st.session_state:
            del st.session_state.selected_card_id

    if "assignment_id" in params_arg:
        assignment_id_val = params_arg["assignment_id"]
        if isinstance(assignment_id_val, list):
            assignment_id_val = assignment_id_val[0] if assignment_id_val else None
        if assignment_id_val is not None:
            st.session_state.selected_assignment_id = assignment_id_val
            print(f"[set_filters_from_params] Установлен selected_assignment_id = {assignment_id_val}")
        elif "selected_assignment_id" in st.session_state:
            del st.session_state.selected_assignment_id
    
    print(f"[set_filters_from_params] После установки: filter_program = {st.session_state.get('filter_program')}")

# Новая функция для параллельной загрузки данных
@st.cache_data(ttl=3600)
def load_app_data(_engine, current_page, program, module, lesson, gz):
    """
    Загружает данные в зависимости от текущей страницы с использованием материализованных представлений
    
    Args:
        _engine: SQLAlchemy engine для подключения к БД
        current_page: Текущая страница приложения
        program: Текущий фильтр по программе
        module: Текущий фильтр по модулю
        lesson: Текущий фильтр по уроку
        gz: Текущий фильтр по ГЗ
        
    Returns:
        dict: Словарь с разными наборами данных для текущей страницы
    """
    result = {} # Инициализируем result здесь
    # Преобразуем название страницы в уровень навигации
    level_mapping = {
        "Обзор": "overview",
        "Программы": "program",
        "Модули": "module",
        "Уроки": "lesson",
        "ГЗ": "gz",
        "Карточки": "card"
    }
    level = level_mapping.get(current_page, "overview")
    
    # Параметры фильтрации теперь приходят как аргументы функции.
    # card_id все еще получаем из session_state, так как он специфичен для страницы карточки
    # и не должен влиять на кэш load_app_data на уровне фильтров программы/модуля и т.д.
    card_id = st.session_state.get("selected_card_id")
    
    # Создаем словарь с параметрами для передачи в load_all_data_for_level
    # Заметим, что program, module, lesson, gz здесь - это аргументы функции load_app_data
    params_for_load_all = {
        "level": level,
        "program": program, # из аргумента
        "module": module,   # из аргумента
        "lesson": lesson,   # из аргумента
        "gz": gz,           # из аргумента
        "_engine": _engine,
        "max_workers": MAX_WORKERS
    }
    
    # Загружаем данные из соответствующего материализованного представления
    if level == "overview":
        # Загружаем данные для программ и модулей для обзорной страницы
        result = {"programs": core.load_program_data(_engine=_engine)}
        # Дополнительно можно загрузить модули, если это нужно для обзора
        # result["modules"] = core.load_module_data(_engine=_engine) 
    elif level == "program":
        # Используем 'program' из аргументов функции
        result = core.load_module_data(program=program, _engine=_engine)
        program_data_df = core.load_program_data(_engine=_engine)
        if program and not program_data_df[program_data_df["program_name"] == program].empty:
            result = {"program_data": program_data_df[program_data_df["program_name"] == program], 
                      "modules": result}
        else:
            result = {"modules": result}
    elif level == "module":
        # Используем 'program', 'module' из аргументов функции
        result = core.load_lesson_data(program=program, module=module, _engine=_engine)
        module_data_df = core.load_module_data(program=program, _engine=_engine)
        if module and not module_data_df[module_data_df["module_name"] == module].empty:
            result = {"module_data": module_data_df[module_data_df["module_name"] == module], 
                      "lessons": result}
        else:
            result = {"lessons": result}
    elif level == "lesson":
        # Используем 'program', 'module', 'lesson' из аргументов функции
        result = core.load_gz_data(program=program, module=module, lesson=lesson, _engine=_engine)
        lesson_data_df = core.load_lesson_data(program=program, module=module, _engine=_engine)
        if lesson and not lesson_data_df[lesson_data_df["lesson_name"] == lesson].empty:
            result = {"lesson_data": lesson_data_df[lesson_data_df["lesson_name"] == lesson], 
                      "gz_list": result}
        else:
            result = {"gz_list": result}
    elif level == "gz":
        # Используем 'program', 'module', 'lesson', 'gz' из аргументов функции
        result = {"cards": core.load_card_data(program=program, module=module, lesson=lesson, gz=gz, _engine=_engine)}
        gz_data_df = core.load_gz_data(program=program, module=module, lesson=lesson, _engine=_engine)
        if gz and not gz_data_df.empty:
            current_gz_data = gz_data_df[gz_data_df["gz_name"] == gz]
            if not current_gz_data.empty:
                 result["gz_data"] = current_gz_data
    elif level == "card":
        # Используем 'program', 'module', 'lesson', 'gz' из аргументов функции
        result["card_page_data"] = core.load_card_data(program=program, module=module, lesson=lesson, gz=gz, _engine=_engine)
    else:
        # Используем params_for_load_all, которые содержат program, module, lesson, gz из аргументов
        result = core.load_all_data_for_level(**params_for_load_all)
    
    # Загружаем данные для навигации из cards_structure (для боковой панели и, возможно, для display_course_links)
    navigation_data = core.load_navigation_data(_engine)
    result["navigation_data"] = navigation_data
    
    # Для страниц администрирования загружаем полный набор данных
    if current_page in ["⚙️ Настройки", "Мои задачи", "Панель администратора методистов", "Планирование рефакторинга"]:
        result["full_data"] = navigation_data
        
        # Добавляем данные о назначениях для страницы задач
        if current_page == "Мои задачи":
            result["assignments"] = core.load_user_assignments(_engine, st.session_state.user_id)
        
        # Добавляем данные для панели администратора методистов
        if current_page == "Панель администратора методистов":
            result["users"] = core.load_users(_engine)
            result["assignments"] = core.load_all_assignments(_engine)
    
    return result

# Измененная функция создания ссылок для внутренней навигации
def create_internal_link(target_page, label, **params):
    """
    Создает HTML-кнопку для навигации внутри приложения без перезагрузки страницы.
    
    Args:
        target_page: Целевая страница
        label: Текст ссылки
        **params: Дополнительные параметры для передачи в navigate_to
    """
    # Создаем уникальный ключ для кнопки на основе параметров
    key_str = f"{target_page}_{label}"
    for k, v in params.items():
        key_str += f"_{k}_{v}"
    
    key = str(hash(key_str))
    
    if st.button(label, key=key):
        # Сначала добавляем текущую страницу в историю
        current = st.session_state.get("current_page")
        if current and current != target_page:
            if "nav_history" not in st.session_state:
                st.session_state.nav_history = []
            st.session_state.nav_history.append(current)
            # Для отладки - печатаем историю в консоль
            print(f"История навигации (из кнопки): {st.session_state.nav_history}")
            
        # Затем устанавливаем новую страницу
        st.session_state.current_page = target_page
        
        # Обновляем URL и параметры (без добавления в историю)
        url_params = {"page": target_page.lower().replace(" ", "_")}
        # Добавляем фильтры в URL параметры и обновляем session_state
        for param_key, param_value in params.items():
            print(f"[create_internal_link] Processing param: {param_key} = {param_value}")
            # Установка session_state для фильтров
            if param_key == "program" or param_key == "filter_program":
                st.session_state.filter_program = param_value
                url_params["program"] = param_value # Ключ в URL всегда "program"
            elif param_key == "module" or param_key == "filter_module":
                st.session_state.filter_module = param_value
                url_params["module"] = param_value
            elif param_key == "lesson" or param_key == "filter_lesson":
                st.session_state.filter_lesson = param_value
                url_params["lesson"] = param_value
            elif param_key == "gz" or param_key == "filter_gz":
                st.session_state.filter_gz = param_value
                url_params["gz"] = param_value
            elif param_key == "card_id":
                st.session_state.selected_card_id = param_value
                url_params["card_id"] = param_value
            elif param_key == "assignment_id":
                st.session_state.selected_assignment_id = param_value
                url_params["assignment_id"] = param_value
            else:
                st.session_state[param_key] = param_value
                # Если это не стандартный фильтр, но ключ совпадает с URL-версией фильтра, добавляем в URL
                if param_key in ["program", "module", "lesson", "gz", "card_id", "assignment_id"] and param_key not in url_params:
                    url_params[param_key] = param_value
        
        # Убедимся, что в URL попадают значения из session_state, если они там есть и не были переопределены
        if st.session_state.get("filter_program") and "program" not in url_params:
            url_params["program"] = st.session_state.filter_program
        if st.session_state.get("filter_module") and "module" not in url_params:
            url_params["module"] = st.session_state.filter_module
        if st.session_state.get("filter_lesson") and "lesson" not in url_params:
            url_params["lesson"] = st.session_state.filter_lesson
        if st.session_state.get("filter_gz") and "gz" not in url_params:
            url_params["gz"] = st.session_state.filter_gz
        if st.session_state.get("selected_card_id") and "card_id" not in url_params:
            url_params["card_id"] = st.session_state.selected_card_id
        if st.session_state.get("selected_assignment_id") and "assignment_id" not in url_params:
            url_params["assignment_id"] = st.session_state.selected_assignment_id

        # Заменяем пробелы на подчеркивания в target_page для URL
        # Это было сделано выше при инициализации url_params, здесь просто для консистентности, если target_page изменится
        url_params["page"] = target_page.lower().replace(" ", "_")

        print(f"[create_internal_link] Перед rerun: filter_program = {st.session_state.get('filter_program')}")
        print(f"[create_internal_link] Перед rerun: url_params для query_params = {url_params}")
        st.rerun()

# Инициализация navigation_utils для работы с новой системой навигации
def init_internal_navigation():
    """Инициализирует внутреннюю систему навигации"""
    # Перезаписываем функцию создания ссылок для использования внутренней навигации
    navigation_utils.create_page_link = create_internal_link
    
    # Инициализация истории навигации, если ее нет
    if "nav_history" not in st.session_state:
        st.session_state.nav_history = []
    
    # Инициализация истории в navigation_utils
    navigation_utils.init_navigation_history()
    
    # Добавляем текущие параметры URL в историю navigation_utils
    if st.query_params:
        navigation_utils.add_to_history(st.query_params)
    else:
        # Если параметров URL нет, добавляем overview как первую страницу
        navigation_utils.add_to_history({"page": "overview"})

# Создаем engine вне кэширования
engine = core.get_engine()

# Проверяем активность сессии и авторизацию пользователя
if not auth.check_authentication():
    auth.login_page(engine)
    st.stop()

# ---------------------- Обработка URL-параметров ---------------------- #
params = st.query_params
print(f"[app.py] В начале после rerun: st.query_params = {params}")

# Инициализация системы навигации
init_internal_navigation()

# Устанавливаем текущую страницу из URL или из session_state
page_from_url = params.get("page", None)
if page_from_url:
    # Приводим к формату, соответствующему нашим ключам страниц
    if page_from_url == "overview":
        current_page = "Обзор"
        # Добавляем overview в историю навигации, если история пуста
        if navigation_utils.get_history_size() == 0:
            navigation_utils.add_to_history({"page": "overview"})
    elif page_from_url == "programs":
        current_page = "Программы"
    elif page_from_url == "modules":
        current_page = "Модули"
    elif page_from_url == "lessons":
        current_page = "Уроки"
    elif page_from_url == "gz":
        current_page = "ГЗ"
    elif page_from_url == "cards":
        current_page = "Карточки"
    elif page_from_url == "admin":
        current_page = "⚙️ Настройки"
    elif page_from_url == "my_tasks":
        current_page = "Мои задачи"
    elif page_from_url == "methodist_admin":
        current_page = "Панель администратора методистов"
    elif page_from_url == "refactor_planning":
        current_page = "Планирование рефакторинга"
    else:
        current_page = "Обзор"
        # Добавляем overview в историю навигации, если история пуста
        if navigation_utils.get_history_size() == 0:
            navigation_utils.add_to_history({"page": "overview"})
    
    # Сохраняем в session_state для будущего использования
    st.session_state.current_page = current_page
else:
    # Используем страницу из session_state или по умолчанию "Обзор"
    current_page = st.session_state.get("current_page", "Обзор")
    
    # Если это первый запуск и нет выбранной страницы, добавляем overview в историю
    if navigation_utils.get_history_size() == 0:
        navigation_utils.add_to_history({"page": "overview"})

# Инициализация пользовательских данных после успешной аутентификации
if "user_data" not in st.session_state and "user_id" in st.session_state:
    user_data = auth.get_user_data(engine, st.session_state.user_id)
    if user_data:
        st.session_state.user_data = user_data
        st.session_state.role = user_data.get("role", "methodist")
        st.session_state.username = user_data.get("username")
        st.session_state.full_name = user_data.get("full_name")

# Проверяем права доступа для административных страниц
if current_page in ["Панель администратора методистов", "Планирование рефакторинга"] and st.session_state.role != "admin":
    st.error("У вас нет прав доступа к этой странице")
    navigate_to("Обзор")
    st.stop()

# Устанавливаем фильтры из URL-параметров
set_filters_from_params(params)

# Получаем актуальные значения фильтров из session_state
program_filter = st.session_state.get("filter_program")
module_filter = st.session_state.get("filter_module")
lesson_filter = st.session_state.get("filter_lesson")
gz_filter = st.session_state.get("filter_gz")

# Обработка параметра card_id для страницы карточки
if "card_id" in params and current_page == "Карточки":
    card_id = params["card_id"]
    st.session_state["selected_card_id"] = card_id
    
# Проверяем, есть ли у нас кэшированные данные для этой страницы и текущих фильтров
# Формируем data_key с учетом фильтров
data_key = f"data_cache_{current_page}_{program_filter}_{module_filter}_{lesson_filter}_{gz_filter}"
data_dict = st.session_state.get(data_key)

# Если данных нет или они устарели, загружаем заново
if data_dict is None:
    data_dict = load_app_data(engine, current_page, program_filter, module_filter, lesson_filter, gz_filter)
    # Кэшируем данные в session_state
    st.session_state[data_key] = data_dict

# Если это страница карточки, настраиваем фильтры на основе данных карточки
if "card_id" in params and current_page == "Карточки":
    card_id = params["card_id"]
    if "card_data" in data_dict and not data_dict["card_data"].empty:
        card_data = data_dict["card_data"]
        # Устанавливаем фильтры только если они еще не установлены
        if "filter_program" not in st.session_state or not st.session_state["filter_program"]:
            st.session_state["filter_program"] = card_data["program"].iloc[0]
        if "filter_module" not in st.session_state or not st.session_state["filter_module"]:
            st.session_state["filter_module"] = card_data["module"].iloc[0]
        if "filter_lesson" not in st.session_state or not st.session_state["filter_lesson"]:
            st.session_state["filter_lesson"] = card_data["lesson"].iloc[0]
        if "filter_gz" not in st.session_state or not st.session_state["filter_gz"]:
            st.session_state["filter_gz"] = card_data["gz"].iloc[0]

# Добавляем функцию для использования истории из navigation_utils
def use_navigation_utils_history():
    """Использует историю из модуля navigation_utils для навигации"""
    # Выводим текущую историю для отладки
    history_size = navigation_utils.get_history_size()
    print(f"Размер истории navigation_utils: {history_size}")
    if history_size > 0:
        # Вывод содержимого истории, если она не пуста
        history = st.session_state.get("nav_history", [])
        position = st.session_state.get("nav_history_position", -1)
        print(f"Содержимое истории: {history}")
        print(f"Текущая позиция: {position}")
    
    if navigation_utils.navigate_back():
        # История навигации успешно использована
        return True
    return False

# Функция для навигации вперед с использованием navigation_utils
def use_navigation_utils_forward():
    """Использует историю из модуля navigation_utils для навигации вперед"""
    if navigation_utils.navigate_forward():
        # История навигации успешно использована
        return True
    return False

# ---------------------- sidebar & navigation ------------------------------ #
# Добавляем навигационную панель с кнопками назад/вперед/домой
col1, col2, col3 = st.sidebar.columns([1, 1, 1])

with col1:
    if st.button("⬅️", help="Назад", key="btn_back"):
        # Сначала пробуем использовать историю из navigation_utils
        if use_navigation_utils_history():
            st.rerun()
        # Если не получилось, пробуем использовать нашу внутреннюю историю
        elif go_back():
            st.rerun()
        else:
            st.warning("История навигации пуста", icon="⚠️")

with col2:
    if st.button("➡️", help="Вперед", key="btn_forward"):
        # Пробуем использовать навигацию вперед
        if use_navigation_utils_forward():
            st.rerun()
        else:
            st.warning("Нет доступных переходов вперед", icon="⚠️")

with col3:
    if st.button("🏠", help="Домой", key="btn_home"):
        # Сначала добавляем текущую страницу в историю
        current = st.session_state.get("current_page")
        if current and current != "Обзор":
            if "nav_history" not in st.session_state:
                st.session_state.nav_history = []
            st.session_state.nav_history.append(current)
        
        # Устанавливаем новую страницу
        st.session_state.current_page = "Обзор"
        st.query_params = {"page": "overview"}
        navigation_utils.add_to_history({"page": "overview"})
        st.rerun()

# Получаем данные для фильтров
filter_data = data_dict.get("navigation_data")

# Передаем функцию создания ссылок в функцию сайдбара
pages.sidebar_filters(filter_data, create_internal_link)

# Навигация по задачам и админке методистов через кнопки
st.sidebar.markdown("---")

# Кнопка "Мои задачи" с индикатором количества активных задач
if "user_id" in st.session_state:
    active_tasks = core.get_active_tasks_count(engine, st.session_state.user_id)
    tasks_label = f"📝 Мои задачи ({active_tasks})" if active_tasks > 0 else "📝 Мои задачи"
    if st.sidebar.button(tasks_label, key="sidebar_my_tasks"):
        navigate_to("Мои задачи")
        st.rerun()

# Кнопки для администраторов
if st.session_state.role == "admin":
    if st.sidebar.button("👨‍🏫 Панель администратора методистов", key="sidebar_methodist_admin"):
        navigate_to("Панель администратора методистов")
        st.rerun()
    if st.sidebar.button("📅 Планирование рефакторинга", key="sidebar_refactor_planning"):
        navigate_to("Планирование рефакторинга")
        st.rerun()

# Обновленный словарь функций для страниц с передачей словаря данных
PAGES = {
    "Обзор": lambda data_dict: pages.page_overview(data_dict.get("programs")),
    "Программы": lambda data_dict: pages.page_programs(data_dict.get("modules")),
    "Модули": lambda data_dict: pages.page_modules(data_dict.get("lessons")),
    "Уроки": lambda data_dict: pages.page_lessons(data_dict.get("gz_list")),
    "ГЗ": lambda data_dict: pages.page_gz(data_dict.get("cards"), create_internal_link),
    "Карточки": lambda data_dict: pages.page_cards(
        df_card_details=data_dict.get("card_page_data"), 
        df_structure=data_dict.get("navigation_data"), 
        eng=engine
    ),
    "⚙️ Настройки": lambda data_dict: pages.page_admin(
        data_dict.get("full_data", pd.DataFrame()),
        engine
    ),
    "Мои задачи": lambda data_dict: pages.my_tasks.page_my_tasks(
        data_dict.get("full_data", pd.DataFrame()),
        engine,
        data_dict.get("assignments", []),
        st.session_state.get("selected_assignment_id"),
        update_task_status,
        create_task_link
    ),
    "Панель администратора методистов": lambda data_dict: pages.methodist_admin.page_methodist_admin(
        data_dict.get("full_data", pd.DataFrame()),
        engine,
        data_dict.get("users", []),
        data_dict.get("assignments", [])
    ),
    "Планирование рефакторинга": lambda data_dict: pages.refactor_planning.page_refactor_planning(
        data_dict.get("full_data", pd.DataFrame()),
        engine
    ),
}

# Запускаем выбранную страницу с данными
print(f"Текущая страница перед запуском: {current_page}")
print(f"Доступные страницы: {list(PAGES.keys())}")
print(f"Текущая страница в URL: {params.get('page')}")

if current_page in PAGES:
    print(f"Запускаем страницу: {current_page}")
    PAGES[current_page](data_dict)
else:
    print(f"Ошибка: страница {current_page} не найдена в PAGES")
    st.error(f"Страница {current_page} не найдена")

# Показываем информацию пользователя и кнопку выхода
auth.show_user_menu()
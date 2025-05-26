# app.py — точка входа Streamlit с JSON-навигацией
"""
Обновленная версия с улучшенным интерфейсом и структурой проекта.
Поддерживает продвинутую аналитику на всех уровнях иерархии курса:
Программа -> Модуль -> Урок -> ГЗ (группы заданий) -> Карточка
"""

# ---------------- IMPORTS ------------------------------------------------------- #
import streamlit as st 
import uuid 
import urllib.parse as ul
import os
import shutil
import pandas as pd
import auth
import multiprocessing
from typing import Dict, List, Optional, Union
from sqlalchemy import text
import json

# Инициализация SESSION_ID после импортов
if '_session_id' not in st.session_state:
    st.session_state._session_id = str(uuid.uuid4())
SESSION_ID = st.session_state._session_id

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
print(f"[{SESSION_ID}] Using {MAX_WORKERS} worker threads for parallel operations")

# Инициализация счетчика обновлений для инвалидации кэша (если где-то используется)
if 'data_update_counter' not in st.session_state:
    st.session_state.data_update_counter = 0

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

    /* Более специфичные стили для кнопок истории в сайдбаре */
    /* Стили для текста ВНУТРИ кнопки истории */
    div[data-testid="stSidebar"] div.history-button-container .stButton button div[data-testid="stMarkdownContainer"] p {
        font-size: 0.75rem !important;      /* Уменьшенный шрифт */
        line-height: 1.25 !important;       /* Межстрочный интервал */
        color: #f0f0f0 !important;          /* Цвет текста (светлее) */
        margin: 0 !important;               /* Убираем отступы параграфа */
        padding: 0 !important;              /* Убираем padding параграфа */
        font-weight: normal !important;     /* Нормальный вес шрифта */
        /* white-space: normal !important;  - это свойство лучше для родительской кнопки */
        /* overflow-wrap: break-word !important; - и это тоже */
    }

    /* Стили для САМОЙ кнопки истории (контейнера текста) */
    div[data-testid="stSidebar"] div.history-button-container .stButton button {
        padding: 0.2rem 0.3rem !important;   /* Отступы самой кнопки */
        height: auto !important; 
        width: 100% !important;
        display: block !important;
        text-align: left !important;
        white-space: normal !important;      /* Разрешить перенос текста для кнопки */
        overflow-wrap: break-word !important;/* Перенос длинных слов для кнопки */
        border: 1px solid rgba(77, 166, 255, 0.15) !important; /* Чуть менее заметная рамка */
        margin-bottom: 3px !important;       /* Отступ между кнопками */
        background-color: transparent !important; /* Прозрачный фон кнопки */
        border-radius: 4px !important;       /* Скругление углов */
    }
    
    div[data-testid="stSidebar"] div.history-button-container .stButton button:hover {
        background-color: rgba(77, 166, 255, 0.1) !important; /* Фон при наведении */
    }

</style>
""", unsafe_allow_html=True)

# ---------------- FUNCTIONS ------------------------------------------------------- #

print(f"[{SESSION_ID}] APP START query_params: {st.query_params}, session_state.current_page: {st.session_state.get('current_page')}")

# Функция для навигации между страницами без перезагрузки
def navigate_to(page, update_url=True, **params_to_set):
    """
    Изменяет текущую страницу без полной перезагрузки приложения.
    
    Args:
        page: Название страницы для перехода
        update_url: Обновлять ли URL в адресной строке
        **params_to_set: Дополнительные параметры (фильтры, card_id и т.д.)
    """
    print(f"[{SESSION_ID}] [NAVIGATE_TO] Called with page: '{page}', params: {params_to_set}")

    # 1. Определяем slug целевой страницы (всегда латиница, строчные)
    # page - это человекочитаемое имя ("Обзор", "Программы", "Модули" и т.д.)
    target_page_slug = "overview" # default
    if page == "Обзор": target_page_slug = "overview"
    elif page == "Программы": target_page_slug = "programs"
    elif page == "Модули": target_page_slug = "modules"
    elif page == "Уроки": target_page_slug = "lessons"
    elif page == "ГЗ": target_page_slug = "gz"
    elif page == "Карточки": target_page_slug = "cards"
    elif page == "⚙️ Настройки": target_page_slug = "admin"
    elif page == "Мои задачи": target_page_slug = "my_tasks"
    elif page == "Панель администратора методистов": target_page_slug = "methodist_admin"
    elif page == "Планирование рефакторинга": target_page_slug = "refactor_planning"
    else:
        print(f"[{SESSION_ID}] [NAVIGATE_TO] Warning: Unknown page name '{page}' for slug generation. Defaulting to 'overview'.")
    
    # 2. Сброс дочерних фильтров в session_state на основе целевого slug
    level_to_reset_below = None # Это ключ из core.FILTERS (program, module, lesson, gz)
    if target_page_slug == "overview":
        core.reset_child("overview") # Сбросит все фильтры из core.FILTERS и card/assignment ID
    elif target_page_slug == "programs":
        level_to_reset_below = "program"
    elif target_page_slug == "modules":
        level_to_reset_below = "module"
    elif target_page_slug == "lessons":
        level_to_reset_below = "lesson"
    # Для "gz", "cards" и админских страниц - не сбрасываем ничего ниже по иерархии фильтров
    
    if level_to_reset_below:
        core.reset_child(level_to_reset_below)

    # 3. Обновляем st.session_state.current_page (человекочитаемое имя) и фильтры на основе аргумента `page` и `params_to_set`
    st.session_state.current_page = page 
    
    if params_to_set:
        for key, value in params_to_set.items():
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
            elif key == "assignment_id": 
                st.session_state.selected_assignment_id = value
            else:
                st.session_state[key] = value
    
    # --- Логирование действия навигации (после обновления session_state) --- 
    try:
        current_user_id = st.session_state.get("user_id") # Получаем user_id
        print(f"[{SESSION_ID}] [NAVIGATE_TO LOGGING] Attempting to log. User ID: {current_user_id}") # <-- ПЕРВЫЙ DEBUG PRINT

        if current_user_id:
            current_page_key_for_log = st.session_state.get("current_page", "Начало").lower().replace(" ", "_")
            prev_url_params_for_log = dict(st.query_params) # Читаем напрямую
            
            prog_name = st.session_state.get("filter_program")
            mod_name = st.session_state.get("filter_module")
            les_name = st.session_state.get("filter_lesson")
            gz_name_filter = st.session_state.get("filter_gz") # gz_name уже используется как переменная
            sel_card_id = st.session_state.get("selected_card_id")
            sel_assignment_id = st.session_state.get("selected_assignment_id") # Для будущего использования

            # Формируем display_name для лога на основе текущего состояния
            # Это отображаемое имя страницы, *с которой* пользователь уходит
            log_display_name_parts = [st.session_state.get("current_page", "Начало")]
            if prog_name: log_display_name_parts.append(f"П: {prog_name[:20]}") # Ограничим длину для краткости
            if mod_name: log_display_name_parts.append(f"М: {mod_name[:20]}")
            if les_name: log_display_name_parts.append(f"У: {les_name[:20]}")
            if gz_name_filter: log_display_name_parts.append(f"ГЗ: {gz_name_filter[:20]}")
            if sel_card_id: log_display_name_parts.append(f"Карта: {sel_card_id}")
            log_display_name = " / ".join(log_display_name_parts)

            # Получаем ID для текущего контекста (страницы, с которой уходим)
            # Используем engine, который должен быть доступен в этом скоупе app.py
            context_ids_for_log = core.get_context_ids_by_names(
                _engine=engine, 
                program_name=prog_name, 
                module_name=mod_name, 
                lesson_name=les_name, 
                gz_name=gz_name_filter,
                card_id_param=sel_card_id
            )
            if sel_assignment_id:
                context_ids_for_log["assignment_id"] = sel_assignment_id

            # Логируем переход НА НОВУЮ страницу `page` с параметрами `params_to_set`
            # Для этого нам нужно определить display_name и context_ids для *целевой* страницы.
            # Пока что для простоты в поле display_name запишем имя целевой страницы `page`,
            # а в url_params - передаваемые `params_to_set`.
            # В будущем можно будет формировать более детальный display_name для целевой страницы.
            
            # ID текущего пользователя
            current_user_id = st.session_state.get("user_id")

            if current_user_id:
                # Определяем page_key для целевой страницы
                target_page_key = page.lower().replace(" ", "_")
                
                # Собираем параметры для целевой страницы, чтобы передать их в get_context_ids_by_names
                target_prog_name = params_to_set.get("program", params_to_set.get("filter_program"))
                target_mod_name = params_to_set.get("module", params_to_set.get("filter_module"))
                target_les_name = params_to_set.get("lesson", params_to_set.get("filter_lesson"))
                target_gz_name = params_to_set.get("gz", params_to_set.get("filter_gz"))
                target_card_id = params_to_set.get("card_id")
                target_assignment_id = params_to_set.get("assignment_id")

                target_context_ids = core.get_context_ids_by_names(
                    _engine=engine,
                    program_name=target_prog_name,
                    module_name=target_mod_name,
                    lesson_name=target_les_name,
                    gz_name=target_gz_name,
                    card_id_param=target_card_id
                )
                if target_assignment_id:
                     target_context_ids["assignment_id"] = target_assignment_id
                
                # Формируем display_name для целевой страницы в формате short_program/module/lesson/gz/card_id
                name_parts = []
                # short_program_name теперь должен быть в target_context_ids
                s_prog_name = target_context_ids.get("program_short_name") 
                if s_prog_name:
                    name_parts.append(s_prog_name)
                elif target_prog_name: # Если short_name нет, используем полное имя программы
                    name_parts.append(target_prog_name.split('.')[0][:25]) # Берем часть до точки или первые 25 символов
                
                if target_mod_name:
                    name_parts.append(target_mod_name[:25]) # Ограничиваем длину для краткости
                if target_les_name:
                    name_parts.append(target_les_name[:25])
                if target_gz_name:
                    name_parts.append(target_gz_name[:25])
                if target_card_id:
                    name_parts.append(f"Карта:{target_card_id}")
                
                if name_parts:
                    target_display_name = " / ".join(name_parts)
                else:
                    target_display_name = page # Имя страницы по умолчанию, если нет других частей

                # Параметры URL для логирования - это те, которые будут установлены для новой страницы
                # Их нужно сформировать до вызова st.query_params.clear()
                future_url_params = {"page": target_page_key}
                if target_prog_name: future_url_params["program"] = target_prog_name
                if target_mod_name: future_url_params["module"] = target_mod_name
                if target_les_name: future_url_params["lesson"] = target_les_name
                if target_gz_name: future_url_params["gz"] = target_gz_name
                if target_card_id: future_url_params["card_id"] = target_card_id
                if target_assignment_id: future_url_params["assignment_id"] = target_assignment_id
                # Добавить другие кастомные параметры из params_to_set, если они есть и должны быть в URL
                for k, v in params_to_set.items():
                    if k not in ["program", "module", "lesson", "gz", "card_id", "assignment_id"] and k not in future_url_params:
                        future_url_params[k] = v

                print(f"[{SESSION_ID}] --- Logging Action Data (Inside if current_user_id) ---") # <-- ВТОРОЙ DEBUG PRINT
                print(f"[{SESSION_ID}] User ID (verified): {current_user_id}")
                print(f"[{SESSION_ID}] Action Type: navigate_page")
                print(f"[{SESSION_ID}] Target Page Key: {target_page_key}")
                print(f"[{SESSION_ID}] Target Context IDs: {target_context_ids}")
                print(f"[{SESSION_ID}] Target Display Name: {target_display_name}")
                print(f"[{SESSION_ID}] Future URL Params (to be logged): {future_url_params}")
                print(f"[{SESSION_ID}] --- End Logging Action Data ---")
                # --- КОНЕЦ ОТЛАДОЧНЫХ PRINT --- 

                core.log_user_action(
                    _engine=engine,
                    user_id=current_user_id,
                    action_type='navigate_page',
                    page_key=target_page_key, # Ключ целевой страницы
                    context_ids=target_context_ids, # ID для целевой страницы/контекста
                    display_name=target_display_name, # Отображаемое имя для целевой страницы
                    url_params=future_url_params # Параметры, которые БУДУТ установлены
                )
            else:
                print(f"[{SESSION_ID}] [NAVIGATE_TO LOGGING] User ID is None or invalid. Skipping action logging.") # <-- ТРЕТИЙ DEBUG PRINT

    except Exception as e:
        print(f"[{SESSION_ID}] [NAVIGATE_TO LOGGING] Error during action logging preparation: {e}") # <-- ЧЕТВЕРТЫЙ DEBUG PRINT
    # --- Конец логирования --- 

    # Очищаем кэш данных для целевой страницы, чтобы она загрузила свежие данные
    # Формируем ключ на основе того, какими БУДУТ фильтры и current_page,
    # а также user_id и selected_card_id текущей сессии.
    target_page_slug_for_cache = page.lower().replace(" ", "_") 
    prog_for_key = st.session_state.get("filter_program")
    mod_for_key = st.session_state.get("filter_module")
    les_for_key = st.session_state.get("filter_lesson")
    gz_for_key = st.session_state.get("filter_gz")
    
    # Важно: используем user_id и selected_card_id из текущей сессии для ключа очистки
    current_user_id_for_clear_key = st.session_state.get("user_id", "guest")
    selected_card_id_for_clear_key = st.session_state.get("selected_card_id", "none")
    
    data_key_to_clear = f"data_cache_{current_user_id_for_clear_key}_{selected_card_id_for_clear_key}_{page}_{prog_for_key}_{mod_for_key}_{les_for_key}_{gz_for_key}"
    if data_key_to_clear in st.session_state:
        del st.session_state[data_key_to_clear]
        print(f"[{SESSION_ID}] [NAVIGATE_TO] Cleared data cache key: {data_key_to_clear}")

    # Обновляем URL, если требуется
    if update_url:
        # Формируем url_params для установки. target_page_slug уже определен.
        # params_to_set - это **params, переданные в navigate_to
        final_url_params = {"page": target_page_slug}
        final_url_params.update(params_to_set) # Добавляем все переданные параметры

        print(f"[{SESSION_ID}] [NAVIGATE_TO] For user_id: {st.session_state.get('user_id')}. Clearing and setting query_params to: {final_url_params}")
        st.query_params.clear() # Очищаем старые
        # st.query_params.from_dict(final_url_params) # Используем from_dict или присваивание
        # Альтернатива: st.query_params = final_url_params (если from_dict не работает как ожидается или для большей ясности, что это полная замена)
        # Согласно документации, присваивание st.query_params.key = value добавляет или обновляет. 
        # Чтобы полностью заменить, лучше clear() + update() или from_dict()
        # Попробуем clear() + цикл для большей надежности и явности
        for key, value in final_url_params.items():
            st.query_params[key] = value # Это должно правильно обработать строки и списки (для повторяющихся ключей)

        st.rerun() 

# Функция для возврата на предыдущую страницу
def go_back():
    """Возвращает на предыдущую страницу из истории действий в БД"""
    current_user_id = st.session_state.get("user_id")
    print(f"[{SESSION_ID}] [GO_BACK] User ID: {current_user_id}")
    if not current_user_id:
        st.warning("Не удалось определить пользователя для возврата назад.")
        return False

    prev_page_action = None
    try:
        with engine.connect() as connection:
            query_text = text("""
                SELECT id, page_key, display_name, url_params, timestamp
                FROM action_history
                WHERE user_id = :user_id AND action_type = 'navigate_page'
                ORDER BY timestamp DESC
                LIMIT 1 OFFSET 1 
            """) 
            result = connection.execute(query_text, {"user_id": current_user_id}).fetchone()
            if result:
                prev_page_action = result._asdict() 
                print(f"[{SESSION_ID}] [GO_BACK] Found previous action from DB: {prev_page_action}") # DEBUG
            else:
                print(f"[{SESSION_ID}] [GO_BACK] No previous action found in history (LIMIT 1 OFFSET 1 returned None).") # DEBUG
                st.warning("Нет предыдущей страницы в истории.")
                return False
    except Exception as e:
        st.error(f"[{SESSION_ID}] [GO_BACK] Ошибка при загрузке истории для возврата: {e}") # DEBUG
        return False

    if prev_page_action:
        entry_url_params_stored = prev_page_action.get("url_params")
        # page_key из БД может быть использован как fallback, если в url_params нет 'page'
        db_page_key = prev_page_action.get("page_key", "overview") 
        print(f"[{SESSION_ID}] [GO_BACK] DB page_key: {db_page_key}, Stored url_params: {entry_url_params_stored}") # DEBUG
        
        entry_url_params = {}
        if isinstance(entry_url_params_stored, str):
            try:
                entry_url_params = json.loads(entry_url_params_stored) 
            except Exception as e:
                print(f"[{SESSION_ID}] [GO_BACK] Error parsing url_params JSON: {e}. Using db_page_key as fallback.")
                entry_url_params = {"page": db_page_key} 
        elif isinstance(entry_url_params_stored, dict):
            entry_url_params = entry_url_params_stored
        else: 
            print(f"[{SESSION_ID}] [GO_BACK] url_params is not str or dict (type: {type(entry_url_params_stored)}). Using db_page_key as fallback.") # DEBUG
            entry_url_params = {"page": db_page_key}

        page_key_from_url_params = entry_url_params.get("page", db_page_key) # Приоритет 'page' из url_params
        print(f"[{SESSION_ID}] [GO_BACK] Page key to use for navigation (from url_params or db_page_key): {page_key_from_url_params}") # DEBUG
        
        target_page_for_nav = "Обзор" 
        if page_key_from_url_params == "overview": target_page_for_nav = "Обзор"
        elif page_key_from_url_params == "programs": target_page_for_nav = "Программы"
        elif page_key_from_url_params == "modules": target_page_for_nav = "Модули"
        elif page_key_from_url_params == "lessons": target_page_for_nav = "Уроки"
        elif page_key_from_url_params == "gz": target_page_for_nav = "ГЗ"
        elif page_key_from_url_params == "cards": target_page_for_nav = "Карточки"
        elif page_key_from_url_params == "admin": target_page_for_nav = "⚙️ Настройки"
        elif page_key_from_url_params == "my_tasks": target_page_for_nav = "Мои задачи"
        elif page_key_from_url_params == "methodist_admin": target_page_for_nav = "Панель администратора методистов"
        elif page_key_from_url_params == "refactor_planning": target_page_for_nav = "Планирование рефакторинга"
        else: target_page_for_nav = page_key_from_url_params.capitalize()

        nav_params = {k: v for k, v in entry_url_params.items() if k != 'page'}
        
        print(f"[{SESSION_ID}] [GO_BACK] Navigating to page: '{target_page_for_nav}' with params: {nav_params}") # DEBUG
        navigate_to(target_page_for_nav, **nav_params)
        return True
    return False

# Функция для установки фильтров из URL-параметров
def set_filters_from_params(params_arg):
    """Устанавливает фильтры на основе параметров URL"""
    current_user_for_log = st.session_state.get('user_id', 'UNKNOWN_USER') 
    print(f"[{SESSION_ID}] [set_filters_from_params] For user_id: {current_user_for_log}. Полученные параметры: {params_arg}")
    
    filter_keys_from_url = {
        "program": "filter_program",
        "module": "filter_module",
        "lesson": "filter_lesson",
        "gz": "filter_gz"
    }

    for url_key, session_key in filter_keys_from_url.items():
        if url_key in params_arg: 
            param_value = params_arg.get(url_key) 
            print(f"[{SESSION_ID}] DEBUG_QUERY_PARAMS: url_key='{url_key}', raw_param_value='{param_value}', type={type(param_value)}") # Отладочный print
            
            # Попытка явно обработать как строку, если это поможет (хотя не должно быть нужно)
            if isinstance(param_value, str):
                actual_value_to_set = param_value
            elif isinstance(param_value, list) and param_value: # На случай, если st.query_params иногда возвращает список
                actual_value_to_set = str(param_value[0])
            elif param_value is not None:
                actual_value_to_set = str(param_value)
            else:
                actual_value_to_set = None
            
            print(f"[{SESSION_ID}] DEBUG_QUERY_PARAMS: url_key='{url_key}', actual_value_to_set='{actual_value_to_set}'")

            if actual_value_to_set is not None:
                st.session_state[session_key] = actual_value_to_set
                print(f"[{SESSION_ID}] [set_filters_from_params] Установлен {session_key} = {actual_value_to_set} для user_id: {current_user_for_log}")
            elif session_key in st.session_state: 
                del st.session_state[session_key]
                print(f"[{SESSION_ID}] [set_filters_from_params] Удален {session_key} из session_state для user_id: {current_user_for_log}, так как параметр в URL пуст")

    if "card_id" in params_arg:
        card_id_val_list = params_arg["card_id"]
        card_id_val = card_id_val_list[0] if card_id_val_list else None
        if card_id_val is not None:
            st.session_state.selected_card_id = card_id_val
            print(f"[{SESSION_ID}] [set_filters_from_params] Установлен selected_card_id = {card_id_val} для user_id: {current_user_for_log}")
        elif "selected_card_id" in st.session_state:
            del st.session_state.selected_card_id

    if "assignment_id" in params_arg:
        assignment_id_val_list = params_arg["assignment_id"]
        assignment_id_val = assignment_id_val_list[0] if assignment_id_val_list else None
        if assignment_id_val is not None:
            st.session_state.selected_assignment_id = assignment_id_val
            print(f"[{SESSION_ID}] [set_filters_from_params] Установлен selected_assignment_id = {assignment_id_val} для user_id: {current_user_for_log}")
        elif "selected_assignment_id" in st.session_state:
            del st.session_state.selected_assignment_id
    
    print(f"[{SESSION_ID}] [set_filters_from_params] После установки для user_id: {current_user_for_log}: filter_program = {st.session_state.get('filter_program')}")

# Новая функция для параллельной загрузки данных
@st.cache_data(ttl=3600)
def load_app_data(_engine, current_page, program, module, lesson, gz, user_id, selected_card_id=None, update_trigger=0):
    """
    Загружает данные в зависимости от текущей страницы с использованием материализованных представлений
    
    Args:
        _engine: SQLAlchemy engine для подключения к БД
        current_page: Текущая страница приложения
        program: Текущий фильтр по программе
        module: Текущий фильтр по модулю
        lesson: Текущий фильтр по уроку
        gz: Текущий фильтр по ГЗ
        user_id: ID текущего пользователя
        selected_card_id: ID выбранной карточки (опционально)
        
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
    # card_id (selected_card_id) теперь также является аргументом функции.
    # Это обеспечивает его включение в ключ кэша.
    # card_id = st.session_state.get("selected_card_id") # СТАРАЯ СТРОКА, УДАЛЯЕМ
    
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
        # selected_card_id также должен быть передан в core.load_card_data, если он там используется
        # или данные для карточки загружаются по-другому, используя selected_card_id
        result["card_page_data"] = core.load_card_data(program=program, module=module, lesson=lesson, gz=gz, card_id=selected_card_id, _engine=_engine, update_trigger=update_trigger)
    else:
        # Используем params_for_load_all, которые содержат program, module, lesson, gz из аргументов
        params_for_load_all["update_trigger"] = update_trigger
        # Добавляем selected_card_id и user_id в params_for_load_all для передачи в load_all_data_for_level
        # selected_card_id передается как selected_card_id_arg
        # user_id пока не используется в load_all_data_for_level, но если понадобится, механизм будет тот же.
        params_for_load_all["selected_card_id_arg"] = selected_card_id
        result = core.load_all_data_for_level(**params_for_load_all)
    
    # Загружаем данные для навигации из cards_structure (для боковой панели и, возможно, для display_course_links)
    navigation_data = core.load_navigation_data(_engine)
    result["navigation_data"] = navigation_data
    
    # Для страниц администрирования загружаем полный набор данных
    if current_page in ["⚙️ Настройки", "Мои задачи", "Панель администратора методистов", "Планирование рефакторинга"]:
        result["full_data"] = navigation_data
        
        # Добавляем данные о назначениях для страницы задач
        if current_page == "Мои задачи":
            result["assignments"] = core.load_user_specific_assignments(_engine, user_id, update_trigger=update_trigger)
        
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
        # Формируем параметры для navigate_to
        # target_page уже является человекочитаемым именем страницы
        # params - это словарь с фильтрами и другими параметрами (например, program="XYZ", module="ABC")
        nav_call_params = params.copy() # Копируем, чтобы не изменять оригинальный params, если он где-то еще нужен

        print(f"[{SESSION_ID}] [create_internal_link] Calling app.navigate_to with page: '{target_page}', params: {nav_call_params}")
        navigate_to(target_page, **nav_call_params) # Вызываем navigate_to из app.py
        # st.rerun() здесь больше не нужен, так как navigate_to (через изменение st.query_params) вызовет rerun

# Инициализация navigation_utils для работы с новой системой навигации
def init_internal_navigation():
    """Инициализирует внутреннюю систему навигации"""
    # Перезаписываем функцию создания ссылок для использования внутренней навигации
    # navigation_utils.create_page_link = create_internal_link # Это пока оставим, но create_internal_link нужно будет исправить
    
    # # ПЕРЕНАПРАВЛЯЕМ navigation_utils.navigate_to НА ФУНКЦИЮ navigate_to ИЗ app.py - БОЛЬШЕ НЕ НУЖНО
    # navigation_utils.navigate_to = navigate_to 

    # Регистрируем функции навигации из app.py как атрибуты st для доступа из других модулей
    st.navigate_to_app = navigate_to
    st.app_go_back = go_back

    # # Инициализация истории навигации, если ее нет (для старой системы go_back, которая теперь не нужна) - УДАЛЕНО
    # # if "nav_history" not in st.session_state:
    # #     st.session_state.nav_history = [] 
    
    # # Инициализация истории в navigation_utils (старая, больше не нужна) - УДАЛЕНО
    # # navigation_utils.init_navigation_history()
    
    # # Добавляем текущие параметры URL в историю navigation_utils (старая, больше не нужна) - УДАЛЕНО
    # # if st.experimental_get_query_params():
    # #     navigation_utils.add_to_history(st.experimental_get_query_params())
    # # else:
    # #     navigation_utils.add_to_history({"page": "overview"})

# Создаем engine вне кэширования
engine = core.get_engine()

# Проверяем активность сессии и авторизацию пользователя
if not auth.check_authentication():
    auth.login_page(engine)
    st.stop()

# ---------------------- Обработка URL-параметров ---------------------- #
params = st.query_params # Читаем напрямую
print(f"[{SESSION_ID}] В начале после rerun: query_params = {params}")

# Инициализация системы навигации
init_internal_navigation()

# Устанавливаем текущую страницу из URL или из session_state
page_from_url = params.get("page") # .get() вернет None если ключа нет, или значение (строку)
current_page_determined = "Обзор" 

if page_from_url:
    print(f"[{SESSION_ID}] [APP URL PARSE] page_from_url: '{page_from_url}'") 
    if page_from_url == "overview":
        current_page_determined = "Обзор"
    elif page_from_url == "programs":
        current_page_determined = "Программы"
    elif page_from_url == "modules": 
        current_page_determined = "Модули"
    elif page_from_url == "lessons":
        current_page_determined = "Уроки"
    elif page_from_url == "gz":
        current_page_determined = "ГЗ"
    elif page_from_url == "cards":
        current_page_determined = "Карточки"
    elif page_from_url == "admin": 
        current_page_determined = "⚙️ Настройки"
    elif page_from_url == "my_tasks":
        current_page_determined = "Мои задачи"
    elif page_from_url == "methodist_admin": 
        current_page_determined = "Панель администратора методистов"
    elif page_from_url == "refactor_planning":
        current_page_determined = "Планирование рефакторинга"
    else:
        print(f"[{SESSION_ID}] [APP URL PARSE] Unknown page_from_url: '{page_from_url}', defaulting to Обзор.") 
        current_page_determined = "Обзор" 
    
    st.session_state.current_page = current_page_determined
    print(f"[{SESSION_ID}] [APP URL PARSE] current_page set to: '{st.session_state.current_page}' from URL.") 
else:
    st.session_state.current_page = st.session_state.get("current_page", "Обзор")
    print(f"[{SESSION_ID}] [APP URL PARSE] current_page set to: '{st.session_state.current_page}' from session_state (no page in URL).") 

# Инициализация пользовательских данных после успешной аутентификации
if "user_data" not in st.session_state and "user_id" in st.session_state:
    user_data = auth.get_user_data(engine, st.session_state.user_id)
    if user_data:
        st.session_state.user_data = user_data
        st.session_state.role = user_data.get("role", "methodist")
        st.session_state.username = user_data.get("username")
        st.session_state.full_name = user_data.get("full_name")

# Проверяем права доступа для административных страниц
if current_page_determined in ["Панель администратора методистов", "Планирование рефакторинга"] and st.session_state.role != "admin":
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

# Обработка параметра card_id из URL для selected_card_id в session_state
# Это важно сделать до формирования data_key, если selected_card_id влияет на data_key
url_card_id_from_params = params.get("card_id") # params - это st.query_params, .get() вернет значение или None

if url_card_id_from_params:
    st.session_state["selected_card_id"] = str(url_card_id_from_params) # Сохраняем как строку
    print(f"[{SESSION_ID}] Updated st.session_state.selected_card_id from URL params to: {st.session_state.selected_card_id}")
    # Если card_id пришел в URL, а current_page не "Карточки", 
    # возможно, стоит принудительно установить current_page_determined = "Карточки",
    # но пока оставим как есть, navigate_to должна это обработать.
else:
    # Если card_id нет в URL, но он мог быть установлен в session_state ранее (например, при выборе из списка на стр. Карточки)
    # и мы НЕ на странице карточки, то его, возможно, стоит сбросить, чтобы он не влиял на data_key других страниц.
    # Однако, если мы на странице карточки, но card_id пропал из URL, мы все равно должны пытаться использовать тот, что в session_state.
    # Эта логика может потребовать уточнения в зависимости от желаемого поведения.
    # Пока что, если card_id нет в URL, selected_card_id в session_state останется как есть или будет None/"none".
    pass 

# Формируем data_key с учетом фильтров, user_id и selected_card_id
current_user_id_for_key = st.session_state.get("user_id", "guest")
selected_card_id_for_key = st.session_state.get("selected_card_id", "none") 
print(f"[{SESSION_ID}] For data_key generation: current_page_determined='{current_page_determined}', selected_card_id_for_key='{selected_card_id_for_key}'")

program_filter_for_key = st.session_state.get("filter_program") # Берем актуальные фильтры из session_state
module_filter_for_key = st.session_state.get("filter_module")
lesson_filter_for_key = st.session_state.get("filter_lesson")
gz_filter_for_key = st.session_state.get("filter_gz")

data_key = f"data_cache_{current_user_id_for_key}_{selected_card_id_for_key}_{current_page_determined}_{program_filter_for_key}_{module_filter_for_key}_{lesson_filter_for_key}_{gz_filter_for_key}"
data_dict = st.session_state.get(data_key)

if data_dict is None:
    print(f"[{SESSION_ID}] Cache miss for data_key: {data_key}. Loading data...")
    data_dict = load_app_data(
        engine,
        current_page_determined, 
        program_filter_for_key, # Передаем актуальные фильтры
        module_filter_for_key,
        lesson_filter_for_key,
        gz_filter_for_key,
        current_user_id_for_key, 
        selected_card_id_for_key 
    )
    st.session_state[data_key] = data_dict
else:
    print(f"[{SESSION_ID}] Cache hit for data_key: {data_key}.")

# Если это страница карточки, настраиваем фильтры в session_state на основе фактических данных карточки
# Это нужно делать ПОСЛЕ того, как data_dict загружен (либо из кэша, либо свежий)
if current_page_determined == "Карточки" and selected_card_id_for_key != "none":
    if "card_page_data" in data_dict and data_dict["card_page_data"] is not None and not data_dict["card_page_data"].empty:
        card_data_df_for_filters = data_dict["card_page_data"]
        try:
            # core.load_card_data уже должна была отфильтровать по card_id, если он был передан,
            # и вернуть одну строку или пустой DataFrame.
            # Если selected_card_id_for_key не "none", значит, он был передан в load_card_data.
            if not card_data_df_for_filters.empty:
                # Предполагаем, что если card_page_data не пуст, то это данные нужной карточки
                actual_card_data_row = card_data_df_for_filters.iloc[0]
                
                keys_to_update = {
                    "filter_program": "program_name",
                    "filter_module": "module_name",
                    "filter_lesson": "lesson_name",
                    "filter_gz": "gz_name"
                }
                updated_any_filter = False
                for session_key, data_key_name in keys_to_update.items():
                    if data_key_name in actual_card_data_row and pd.notna(actual_card_data_row[data_key_name]):
                        # Обновляем фильтр в session_state только если он отличается или не установлен
                        if st.session_state.get(session_key) != actual_card_data_row[data_key_name]:
                            st.session_state[session_key] = actual_card_data_row[data_key_name]
                            updated_any_filter = True
                    elif session_key in st.session_state: # Если в данных карточки нет поля, а фильтр есть, удаляем
                        del st.session_state[session_key]
                        updated_any_filter = True # Считаем изменением для возможного rerun
                
                if updated_any_filter:
                    print(f"[{SESSION_ID}] Filters in session_state (program, module, etc.) updated from actual card data for card_id: {selected_card_id_for_key}. Rerunning.")
                    # Этот rerun важен, если сайдбар или хлебные крошки должны немедленно отразить новые фильтры
                    st.rerun() 
            else:
                print(f"[{SESSION_ID}] Card data for card_id {selected_card_id_for_key} not found in card_page_data after load_card_data (it was empty). Error display handled by page_cards.")
        except Exception as e_filter_update:
            print(f"[{SESSION_ID}] Error updating filters from card data: {e_filter_update}")
    else:
        print(f"[{SESSION_ID}] 'card_page_data' is empty or not in data_dict for card_id: {selected_card_id_for_key}. Cannot update filters from card data.")
        # Если card_page_data нет, страница карточки все равно покажет ошибку, что данные не загружены.

# Добавляем функцию для использования истории из navigation_utils
def use_navigation_utils_history():
    """Использует историю из модуля navigation_utils для навигации"""
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
        # Используем только нашу обновленную go_back()
        if go_back(): # go_back() теперь сама вызывает navigate_to, которая делает rerun
            pass # st.rerun() больше не нужен здесь явно
        else:
            st.warning("История навигации пуста", icon="⚠️")

with col2:
    # Кнопка "Вперед" пока остается под вопросом.
    # navigation_utils.navigate_forward() работает со своей устаревшей историей.
    # Для полноценной работы "Вперед" с action_history нужна доп. логика.
    # Пока можно ее сделать неактивной или оставить как есть, если она не мешает.
    # Для простоты, пока оставим ее вызов, но он, скорее всего, не будет работать ожидаемо.
    if st.button("➡️", help="Вперед", key="btn_forward"):
        if navigation_utils.navigate_forward(): # Использует старую историю из navigation_utils
            st.rerun()
        else:
            st.warning("Нет доступных переходов вперед", icon="⚠️")

with col3:
    if st.button("🏠", help="Домой", key="btn_home"):
        print(f"[{SESSION_ID}] [HOME_BUTTON] Navigating to Обзор") # DEBUG
        navigate_to("Обзор") # Вызываем нашу центральную функцию

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

# --- Отображение истории из БД --- 
history_entries_df = pd.DataFrame()
if "user_id" in st.session_state:
    current_user_id_for_display = st.session_state.user_id
    try:
        with engine.connect() as connection:
            query_text = text("""
                SELECT id, page_key, display_name, url_params 
                FROM action_history
                WHERE user_id = :user_id AND action_type = 'navigate_page'
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            history_entries_df = pd.read_sql(query_text, connection, params={"user_id": current_user_id_for_display})
    except Exception as e:
        st.sidebar.error(f"[{SESSION_ID}] Ошибка загрузки истории: {e}")

if not history_entries_df.empty:
    st.sidebar.subheader("История") 
    for index, entry in history_entries_df.iterrows():
        entry_display_name = entry.get("display_name", "Запись истории")
        st.sidebar.markdown(f"<div style='font-size: 0.78rem; color: #e0e0e0; padding: 0.1rem 0.2rem; margin-bottom: 4px; white-space: normal; overflow-wrap: break-word;'>{entry_display_name}</div>", unsafe_allow_html=True)

else:
    st.sidebar.markdown("_Пока нет истории посещений_")
# --- Конец отображения истории из БД ---

# Обновленный словарь функций для страниц с передачей словаря данных
PAGES = {
    "Обзор": lambda data_dict: pages.page_overview(data_dict.get("programs")),
    "Программы": lambda data_dict: pages.page_programs(data_dict.get("modules")),
    "Модули": lambda data_dict: pages.page_modules(data_dict.get("lessons")),
    "Уроки": lambda data_dict: pages.page_lessons(data_dict.get("gz_list")),
    "ГЗ": lambda data_dict: pages.page_gz(
        df_cards_input=data_dict.get("cards"), 
        eng=engine,  # Передаем engine
        create_link_fn=create_internal_link
    ),
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
current_page_to_render = st.session_state.get("current_page", "Обзор") # Всегда берем из session_state, с Обзором как fallback

print(f"[{SESSION_ID}] [APP RENDER] current_page from session_state for PAGES: {current_page_to_render}") # DEBUG
print(f"[{SESSION_ID}] Текущая страница перед запуском: {current_page_to_render}") # Этот print уже был, но оставим для сравнения
print(f"[{SESSION_ID}] Доступные страницы: {list(PAGES.keys())}")
print(f"[{SESSION_ID}] Текущая страница в URL: {params.get('page', [None])[0]}") # Пример исправления для .get() на params

if current_page_to_render in PAGES:
    print(f"[{SESSION_ID}] Запускаем страницу: {current_page_to_render}")
    PAGES[current_page_to_render](data_dict)
else:
    print(f"[{SESSION_ID}] Ошибка: страница {current_page_to_render} не найдена в PAGES")
    st.error(f"[{SESSION_ID}] Страница {current_page_to_render} не найдена")

# Показываем информацию пользователя и кнопку выхода
auth.show_user_menu()
# app.py — точка входа Streamlit (v2.0)
"""
Обновленная версия с улучшенным интерфейсом и структурой проекта.
Поддерживает продвинутую аналитику на всех уровнях иерархии курса:
Программа -> Модуль -> Урок -> ГЗ (группы заданий) -> Карточка
"""

import urllib.parse as ul
import streamlit as st

import core
import pages

# Настройка страницы
st.set_page_config(
    "Course Quality Dashboard", 
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

# Добавьте сразу после st.set_page_config()

# Применяем CSS для улучшения внешнего вида и скрытия элементов
st.markdown("""
<style>
    /* Скрыть боковую навигацию страниц */
    [data-testid="collapsedControl"] {
        display: none;
    }
    
    /* Скрыть элементы навигации файлов */
    section[data-testid="stSidebar"] > div.element-container:first-child {
        visibility: hidden;
        height: 0;
        position: absolute;
    }
    
    /* Прижать сайдбар к краю */
    section[data-testid="stSidebar"] {
        width: 100% !important;
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
</style>
""", unsafe_allow_html=True)

# Кэшируем только данные, но не engine
@st.cache_data(ttl=3600)  # Кэширование данных на 1 час
def load_cached_data(_engine):
    """Загружает и кэширует данные из базы данных"""
    data = core.load_data(_engine)
    # Применение улучшенной формулы риска
    data["risk"] = data.apply(core.risk_score, axis=1)
    return data

# Создаем engine вне кэширования
engine = core.get_engine()
data = load_cached_data(engine)

# ---------------------- query params (clickable links) -------------------- #
qry = st.query_params
if "level" in qry and "value" in qry:
    lvl, val = qry["level"], ul.unquote_plus(qry["value"])
    if lvl in core.FILTERS:
        st.session_state[f"filter_{lvl}"] = val
        core.reset_child(lvl)  # сбросить дочерние фильтры

        # если родителей ещё нет, ставим их автоматически из датафрейма
        if lvl == "module":
            if not st.session_state.get("filter_program"):
                prog = data.loc[data.module == val, "program"].mode().iat[0]
                st.session_state["filter_program"] = prog
        elif lvl == "lesson":
            if not st.session_state.get("filter_module"):
                mod = data.loc[data.lesson == val, "module"].mode().iat[0]
                st.session_state["filter_module"] = mod
            if not st.session_state.get("filter_program"):
                prog = data.loc[data.lesson == val, "program"].mode().iat[0]
                st.session_state["filter_program"] = prog
        elif lvl == "gz":
            # Добавить автоматическое заполнение фильтров для ГЗ
            if not st.session_state.get("filter_lesson"):
                les = data.loc[data.gz == val, "lesson"].mode().iat[0]
                st.session_state["filter_lesson"] = les
            if not st.session_state.get("filter_module"):
                mod = data.loc[data.gz == val, "module"].mode().iat[0]
                st.session_state["filter_module"] = mod
            if not st.session_state.get("filter_program"):
                prog = data.loc[data.gz == val, "program"].mode().iat[0]
                st.session_state["filter_program"] = prog

        # Правильный выбор страницы в зависимости от уровня
        page_mapping = {
            "program": "Программы", 
            "module": "Модули", 
            "lesson": "Уроки",
            "gz": "ГЗ",
            "card": "Карточки"
        }
        st.session_state["page"] = page_mapping.get(lvl, "Обзор")

    st.query_params.clear()
    st.rerun()

# ---------------------- sidebar & navigation ------------------------------ #
pages.sidebar_filters(data)

# Меню навигации
PAGES = {
    "Обзор": pages.page_overview,
    "Программы": pages.page_programs,
    "Модули": pages.page_modules,
    "Уроки": pages.page_lessons,
    "ГЗ": pages.page_gz,
    "Карточки": lambda df: pages.page_cards(df, engine),
}

choice = st.sidebar.radio(
    "Навигация",
    list(PAGES.keys()),
    index=list(PAGES.keys()).index(st.session_state.get("page", "Обзор")),
)

st.session_state["page"] = choice

# Добавляем информацию о приложении
with st.sidebar:
    st.markdown("---")
    st.markdown("""
    ### О приложении
    
    Course Quality Dashboard помогает анализировать учебные материалы и выявлять проблемные места.
    
    **Версия 2.0**
    
    📧 [Сообщить об ошибке](mailto:support@example.com)
    """)

# Запускаем выбранную страницу
PAGES[choice](data)
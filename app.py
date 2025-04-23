# app.py — точка входа Streamlit с URL-ориентированной навигацией
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
</style>
""", unsafe_allow_html=True)

# Кэшируем только данные, но не engine
@st.cache_data(ttl=3600)  # Уменьшаем время кэширования до 1 часа
def load_cached_data(_engine):
    """Загружает и кэширует данные из базы данных"""
    data = core.load_data(_engine)
    
    # Добавляем расчет уровня "подлости" для каждой карточки
    data["trickiness_level"] = data.apply(core.get_trickiness_level, axis=1)
    
    # Применение улучшенной формулы риска с учетом подлости вместо first_try
    data["risk"] = data.apply(core.risk_score, axis=1)
    
    return data

# Создаем engine вне кэширования
engine = core.get_engine()
data = load_cached_data(engine)

# Функция для создания ссылок с параметрами
def create_page_link(page, **params):
    """Создает URL с параметрами для навигации между страницами"""
    base_url = "?"
    all_params = {"page": page}
    all_params.update(params)
    
    param_strings = []
    for key, value in all_params.items():
        if value is not None:
            param_strings.append(f"{key}={ul.quote_plus(str(value))}")
    
    return base_url + "&".join(param_strings)

# Функция для установки фильтров из URL-параметров
def set_filters_from_params(params):
    """Устанавливает фильтры на основе параметров URL"""
    # Проходим по всем возможным фильтрам
    for filter_name in core.FILTERS:
        # Если фильтр есть в параметрах, устанавливаем его значение
        if filter_name in params:
            st.session_state[f"filter_{filter_name}"] = params[filter_name]

# ---------------------- Обработка URL-параметров ---------------------- #
params = st.query_params

# Устанавливаем текущую страницу
current_page = params.get("page", "overview")
# Приводим к формату, соответствующему нашим ключам страниц
if current_page == "overview":
    current_page = "Обзор"
elif current_page == "programs":
    current_page = "Программы"
elif current_page == "modules":
    current_page = "Модули"
elif current_page == "lessons":
    current_page = "Уроки"
elif current_page == "gz":
    current_page = "ГЗ"
elif current_page == "cards":
    current_page = "Карточки"
elif current_page == "admin":
    current_page = "⚙️ Настройки"

# Устанавливаем фильтры из URL-параметров
set_filters_from_params(params)

# Обработка параметра card_id для страницы карточки
if "card_id" in params and current_page == "Карточки":
    card_id = params["card_id"]
    st.session_state["selected_card_id"] = card_id
    
    # Автоматически устанавливаем фильтры на основе данных карточки
    card_data = data[data.card_id == float(card_id)]
    if not card_data.empty:
        # Устанавливаем фильтры только если они еще не установлены
        if "filter_program" not in st.session_state or not st.session_state["filter_program"]:
            st.session_state["filter_program"] = card_data["program"].iloc[0]
        if "filter_module" not in st.session_state or not st.session_state["filter_module"]:
            st.session_state["filter_module"] = card_data["module"].iloc[0]
        if "filter_lesson" not in st.session_state or not st.session_state["filter_lesson"]:
            st.session_state["filter_lesson"] = card_data["lesson"].iloc[0]
        if "filter_gz" not in st.session_state or not st.session_state["filter_gz"]:
            st.session_state["filter_gz"] = card_data["gz"].iloc[0]

# ---------------------- sidebar & navigation ------------------------------ #
# Передаем функцию создания ссылок в функцию сайдбара
pages.sidebar_filters(data, create_page_link)

# Словарь функций для страниц
PAGES = {
    "Обзор": pages.page_overview,
    "Программы": pages.page_programs,
    "Модули": pages.page_modules,
    "Уроки": pages.page_lessons,
    "ГЗ": lambda df: pages.page_gz(df, create_page_link),  # Передаем функцию создания ссылок
    "Карточки": lambda df: pages.page_cards(df, engine),
    "⚙️ Настройки": pages.page_admin,
}

# Создаем ссылки для навигации между страницами (вместо radio)
st.sidebar.markdown("### Навигация")

# Получаем список страниц
page_keys = list(PAGES.keys())
columns = st.sidebar.columns(len(page_keys))

# Создаем горизонтальные кнопки-ссылки
for i, (col, page) in enumerate(zip(columns, page_keys)):
    with col:
        # Преобразуем название страницы для использования в URL
        url_page = page.lower()
        if url_page == "⚙️ настройки":
            url_page = "admin"
        
        # Определяем, активна ли текущая страница
        is_active = page == current_page
        
        # Создаем HTML для кнопки-ссылки
        active_class = " active" if is_active else ""
        link_html = f'<a href="{create_page_link(url_page)}" class="nav-link{active_class}" target="_self">{page}</a>'
        
        st.markdown(link_html, unsafe_allow_html=True)

# Запоминаем текущую страницу в состоянии
st.session_state["page"] = current_page

# Добавляем информацию о приложении
with st.sidebar:
    st.markdown("---")
    st.markdown("""
    ### О приложении
    
    Course Quality Dashboard помогает анализировать учебные материалы и выявлять проблемные места.
    
    **Версия 3.0**
    
    📧 [Сообщить об ошибке](mailto:support@example.com)
    """)

# Запускаем выбранную страницу
PAGES[current_page](data)
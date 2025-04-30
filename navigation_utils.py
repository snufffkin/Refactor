"""
Утилиты для обработки навигации в приложении.
Предоставляет функции для работы с историей браузера и навигацией между страницами.
"""

import streamlit as st
import json
import urllib.parse as ul
import os
import base64

# Функция для кодирования изображения в base64
def get_image_base64(image_path):
    """
    Преобразует изображение в строку base64 для использования в HTML
    
    Args:
        image_path (str): Путь к изображению
        
    Returns:
        str: Строка base64
    """
    if not os.path.exists(image_path):
        return ""
        
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    
    return encoded_string

# Функция для получения HTML-кода SVG изображения
def get_svg_html(svg_path, width=24, height=24, transform=None):
    """
    Получает HTML-код для встраивания SVG изображения
    
    Args:
        svg_path (str): Путь к SVG файлу
        width (int): Ширина изображения
        height (int): Высота изображения
        transform (str): CSS-трансформация (например, для поворота)
        
    Returns:
        str: HTML-код изображения
    """
    svg_base64 = get_image_base64(svg_path)
    if not svg_base64:
        return ""
        
    transform_style = f"transform: {transform};" if transform else ""
    return f"""
    <img src="data:image/svg+xml;base64,{svg_base64}" 
         width="{width}" height="{height}" 
         style="vertical-align: middle; {transform_style}">
    """

# Инициализация истории навигации
def init_navigation_history():
    """Инициализирует историю навигации в session_state"""
    if "nav_history" not in st.session_state:
        st.session_state.nav_history = []
    if "nav_history_position" not in st.session_state:
        st.session_state.nav_history_position = -1
    if "current_nav_params" not in st.session_state:
        st.session_state.current_nav_params = {}

def add_to_history(params):
    """
    Добавляет текущие параметры в историю навигации
    
    Args:
        params: Словарь параметров URL
    """
    # Инициализация, если необходимо
    init_navigation_history()
    
    # Преобразуем params в сериализуемый формат
    params_dict = dict(params)
    
    # Если текущие параметры отличаются от последних в истории
    if not st.session_state.nav_history or params_dict != st.session_state.nav_history[-1]:
        # Если мы не в конце истории, удаляем все после текущей позиции
        if st.session_state.nav_history_position < len(st.session_state.nav_history) - 1:
            st.session_state.nav_history = st.session_state.nav_history[:st.session_state.nav_history_position + 1]
        
        # Добавляем текущие параметры в историю
        st.session_state.nav_history.append(params_dict)
        st.session_state.nav_history_position = len(st.session_state.nav_history) - 1
        st.session_state.current_nav_params = params_dict

def navigate_back():
    """
    Переходит на предыдущую страницу в истории навигации
    
    Returns:
        bool: True, если переход выполнен, иначе False
    """
    init_navigation_history()
    
    print(f"navigation_utils.navigate_back: history_position={st.session_state.nav_history_position}, history_size={len(st.session_state.nav_history)}")
    print(f"navigation_utils.navigate_back: history={st.session_state.nav_history}")
    
    if st.session_state.nav_history_position > 0:
        st.session_state.nav_history_position -= 1
        params = st.session_state.nav_history[st.session_state.nav_history_position]
        print(f"navigation_utils.navigate_back: переходим к params={params}")
        st.query_params.clear()
        for key, value in params.items():
            st.query_params[key] = value
        return True
    
    print("navigation_utils.navigate_back: история пуста или мы в начале")
    return False

def navigate_forward():
    """
    Переходит на следующую страницу в истории навигации
    
    Returns:
        bool: True, если переход выполнен, иначе False
    """
    init_navigation_history()
    
    if st.session_state.nav_history_position < len(st.session_state.nav_history) - 1:
        st.session_state.nav_history_position += 1
        params = st.session_state.nav_history[st.session_state.nav_history_position]
        st.query_params.clear()
        for key, value in params.items():
            st.query_params[key] = value
        return True
    return False

def create_page_link(page, **params):
    """
    Создает URL с параметрами для навигации между страницами
    
    Args:
        page (str): Имя страницы для перехода
        **params: Дополнительные параметры URL
        
    Returns:
        str: URL с параметрами
    """
    base_url = "?"
    all_params = {"page": page}
    all_params.update(params)
    
    param_strings = []
    for key, value in all_params.items():
        if value is not None:
            param_strings.append(f"{key}={ul.quote_plus(str(value))}")
    
    return base_url + "&".join(param_strings)

def navigate_to(page, **params):
    """
    Переходит на указанную страницу с параметрами и сохраняет в историю
    
    Args:
        page (str): Имя страницы для перехода
        **params: Дополнительные параметры URL
    """
    # Сначала очищаем текущие параметры
    st.query_params.clear()
    
    # Устанавливаем новые параметры
    st.query_params["page"] = page
    for key, value in params.items():
        if value is not None:
            st.query_params[key] = value
    
    # Перезагружаем страницу для применения изменений
    st.rerun()

def navigation_bar():
    """
    Отображает панель навигации с кнопками: назад, вперед, домой
    Использует собственную систему истории навигации в session_state
    """
    # Инициализация истории навигации
    init_navigation_history()
    
    # Добавляем текущие параметры в историю
    add_to_history(st.query_params)
    
    # Контейнер с классом для стилизации
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 10])
    
    # Используем Unicode-символы для кнопок
    back_icon = "⬅️"    # Стрелка влево
    forward_icon = "➡️"  # Стрелка вправо
    home_icon = "🏠"     # Дом
    
    with col1:
        back_disabled = st.session_state.nav_history_position <= 0
        if st.button(back_icon, disabled=back_disabled, key="nav_back_btn", use_container_width=True):
            navigate_back()
            st.rerun()
            
    with col2:
        forward_disabled = st.session_state.nav_history_position >= len(st.session_state.nav_history) - 1
        if st.button(forward_icon, disabled=forward_disabled, key="nav_forward_btn", use_container_width=True):
            navigate_forward()
            st.rerun()
            
    with col3:
        if st.button(home_icon, key="nav_home_btn", use_container_width=True):
            # Navigating to home page using our navigation system
            navigate_to("overview")
            
    # Добавляем информацию о текущей странице
    with col4:
        current_page_display = st.session_state.get("page", "Обзор").replace("⚙️ ", "")
        st.markdown(f"<div style='margin-top:8px;'>📍 <b>{current_page_display}</b></div>", unsafe_allow_html=True)
    
    # Закрываем контейнер
    st.markdown('</div>', unsafe_allow_html=True)

def sidebar_navigation():
    """
    Отображает навигацию в верхней части сайдбара
    """
    # Инициализация истории навигации
    init_navigation_history()
    
    # Добавляем текущие параметры в историю
    add_to_history(st.query_params)
    
    # Создаем контейнер в сайдбаре
    with st.sidebar:
        st.markdown('<div class="sidebar-nav-container">', unsafe_allow_html=True)
        
        # Используем Unicode-символы вместо SVG для большей надежности
        back_icon = "⬅️"    # Стрелка влево
        forward_icon = "➡️"  # Стрелка вправо
        home_icon = "🏠"     # Дом
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            back_disabled = st.session_state.nav_history_position <= 0
            if st.button(back_icon, disabled=back_disabled, key="sidebar_nav_back_btn", use_container_width=True):
                navigate_back()
                st.rerun()
                
        with col2:
            forward_disabled = st.session_state.nav_history_position >= len(st.session_state.nav_history) - 1
            if st.button(forward_icon, disabled=forward_disabled, key="sidebar_nav_forward_btn", use_container_width=True):
                navigate_forward()
                st.rerun()
                
        with col3:
            if st.button(home_icon, key="sidebar_nav_home_btn", use_container_width=True):
                # Navigating to home page using our navigation system
                navigate_to("overview")
        
        # Отображаем текущую страницу
        current_page_display = st.session_state.get("page", "Обзор").replace("⚙️ ", "")
        st.markdown(f"""
        <div style='text-align: center; margin: 8px 0; padding: 5px;
                   background-color: rgba(28, 131, 225, 0.1); 
                   border-radius: 4px;
                   font-size: 14px;'>
            📍 <b>{current_page_display}</b>
        </div>
        """, unsafe_allow_html=True)
        
        # Добавляем разделитель
        st.markdown("<hr style='margin: 15px 0 20px; opacity: 0.2;'>", unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def back_button(page=None, **params):
    """
    Добавляет кнопку "назад" с переходом на указанную страницу или с использованием истории
    
    Args:
        page: Страница для перехода (None - использовать историю)
        **params: Параметры для перехода
    """
    # Используем Unicode-символ для кнопки назад
    back_icon = "⬅️"    # Стрелка влево
    
    if st.button(f"{back_icon} Вернуться назад"):
        if page:
            # Переход на указанную страницу с параметрами
            navigate_to(page, **params)
        else:
            # Используем историю навигации
            navigate_back()
            st.rerun()

def navigation_link(text, page, **params):
    """
    Создает ссылку для навигации с сохранением в историю
    
    Args:
        text: Текст ссылки
        page: Страница для перехода
        **params: Параметры для перехода
    """
    url = create_page_link(page, **params)
    if st.markdown(f"[{text}]({url})", unsafe_allow_html=True):
        # Если ссылка нажата (в Streamlit это не работает напрямую),
        # но мы оставляем для совместимости с HTML-версией
        navigate_to(page, **params)

def handle_navigation_event(event_type, **params):
    """
    Обрабатывает навигационные события из разных частей приложения
    
    Args:
        event_type (str): Тип события ('back', 'forward', 'home', 'navigate')
        **params: Параметры для навигации (если event_type='navigate')
    """
    if event_type == 'back':
        if navigate_back():
            st.rerun()
    elif event_type == 'forward':
        if navigate_forward():
            st.rerun()
    elif event_type == 'home':
        navigate_to("overview")
    elif event_type == 'navigate':
        if 'page' in params:
            page = params.pop('page')
            navigate_to(page, **params)
        else:
            st.error("Ошибка навигации: не указана страница назначения")
    else:
        st.error(f"Неизвестный тип навигационного события: {event_type}")
        
def show_navigation_debug():
    """Отображает дебаг-информацию о текущей истории навигации"""
    init_navigation_history()
    
    with st.expander("🔍 Дебаг навигации", expanded=False):
        st.write("История навигации:")
        
        # Если история пуста, показываем соответствующее сообщение
        if not st.session_state.nav_history:
            st.info("История навигации пуста")
            return
            
        # Таблица истории навигации
        history_data = []
        for i, params in enumerate(st.session_state.nav_history):
            is_current = i == st.session_state.nav_history_position
            page = params.get("page", "N/A")
            other_params = {k: v for k, v in params.items() if k != "page"}
            
            # Выделяем текущую позицию
            position_mark = "▶️ " if is_current else ""
            
            history_data.append({
                "Позиция": f"{position_mark}{i+1}",
                "Страница": page,
                "Параметры": str(other_params)
            })
        
        # Выводим таблицу с историей
        st.table(history_data)

def get_history_size():
    """
    Возвращает размер истории навигации
    
    Returns:
        int: Количество элементов в истории навигации
    """
    init_navigation_history()
    return len(st.session_state.nav_history) 
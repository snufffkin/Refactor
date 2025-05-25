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
    
    return base_url + "&" + "&".join(param_strings)

def navigation_bar():
    """
    Отображает панель навигации с кнопками: назад, вперед, домой.
    Теперь кнопки "назад" и "вперед" должны вызывать функции из app.py или быть упрощены.
    """
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1, 1, 1, 10])
    back_icon = "⬅️"
    forward_icon = "➡️"
    home_icon = "🏠"
    
    with col1:
        # Эта кнопка "Назад" теперь должна как-то вызывать app.go_back()
        # Простой способ - оставить ее как есть, но она будет работать с ошибкой или не работать,
        # так как navigate_back() из этого файла удалена.
        # Либо ее нужно убрать из этого общего компонента.
        # Для рефакторинга, лучше пока убрать ее функционал или сделать заглушку.
        if st.button(back_icon, key="nav_back_btn_stub", use_container_width=True, help="Назад (требует доработки)"):
            st.toast("Функция 'Назад' в этой панели требует обновления.")
            # Здесь должен быть механизм вызова app.go_back(), если эта панель используется.
            # Например, через st.session_state callback или передачу функции.
            pass 
            
    with col2:
        if st.button(forward_icon, key="nav_forward_btn_stub", use_container_width=True, help="Вперед (требует доработки)"):
            st.toast("Функция 'Вперед' в этой панели требует обновления.")
            pass
            
    with col3:
        if st.button(home_icon, key="nav_home_btn", use_container_width=True):
            if hasattr(st, 'navigate_to_app'): # Проверяем, зарегистрировали ли мы app.navigate_to
                st.navigate_to_app("Обзор") # Предполагаем, что navigate_to_app это app.navigate_to
            else:
                # Фолбек или ошибка, если app.navigate_to не доступна
                st.query_params.clear()
                st.query_params["page"] = "overview"
                st.rerun()
            
    with col4:
        current_page_display = st.session_state.get("current_page", "Обзор").replace("⚙️ ", "") # Используем current_page из app.py
        st.markdown(f"<div style='margin-top:8px;'>📍 <b>{current_page_display}</b></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def sidebar_navigation():
    """
    Отображает навигацию в верхней части сайдбара.
    Кнопки "назад" и "вперед" здесь также должны быть обновлены.
    """
    with st.sidebar:
        st.markdown('<div class="sidebar-nav-container">', unsafe_allow_html=True)
        back_icon = "⬅️"
        forward_icon = "➡️"
        home_icon = "🏠"
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button(back_icon, key="sidebar_nav_back_btn_stub", use_container_width=True, help="Назад (сайдбар)"):
                 # Эта кнопка "Назад" теперь должна вызывать app.go_back()
                 # Поскольку мы в navigation_utils.py, прямого доступа к app.go_back() нет.
                 # Это указывает на то, что sidebar_navigation() должна быть частью app.py или
                 # app.go_back должна быть передана/зарегистрирована.
                 # Пока оставим вызов app.go_back через st.session_state, если мы его туда повесим.
                 if hasattr(st, 'app_go_back') and callable(st.app_go_back):
                     if st.app_go_back():
                         st.rerun() # rerun если go_back вернул True
                 else:
                     st.toast("Функция 'Назад' (сайдбар) не настроена.")
                
        with col2:
            if st.button(forward_icon, key="sidebar_nav_forward_btn_stub", use_container_width=True, help="Вперед (сайдбар, требует доработки)"):
                st.toast("Функция 'Вперед' (сайдбар) требует обновления.")
                pass
                
        with col3:
            if st.button(home_icon, key="sidebar_nav_home_btn", use_container_width=True):
                if hasattr(st, 'navigate_to_app'):
                    st.navigate_to_app("Обзор")
                else:
                    st.query_params.clear()
                    st.query_params["page"] = "overview"
                    st.rerun()
        
        current_page_display = st.session_state.get("current_page", "Обзор").replace("⚙️ ", "")
        st.markdown(f"""
        <div style='text-align: center; margin: 8px 0; padding: 5px;
                   background-color: rgba(28, 131, 225, 0.1); 
                   border-radius: 4px;
                   font-size: 14px;'>
            📍 <b>{current_page_display}</b>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<hr style='margin: 15px 0 20px; opacity: 0.2;'>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def back_button(page=None, **params):
    """
    Добавляет кнопку "назад" с переходом на указанную страницу или с использованием истории.
    Эта функция должна быть пересмотрена.
    """
    back_icon = "⬅️"
    if st.button(f"{back_icon} Вернуться назад"):
        if page: 
            if hasattr(st, 'navigate_to_app'):
                st.navigate_to_app(page, **params)
            else: # Fallback
                temp_q_params = {"page": page.lower().replace(" ","_")}
                temp_q_params.update(params)
                st.query_params = temp_q_params
                st.rerun()
        else:
            # Вызов app.go_back()
            if hasattr(st, 'app_go_back') and callable(st.app_go_back):
                if st.app_go_back():
                    st.rerun()
            else:
                st.toast("Функция 'Назад' не настроена.")

def navigation_link(text, page, **params):
    """
    Создает КНОПКУ для навигации (вместо markdown ссылки).
    """
    # Генерируем уникальный ключ для кнопки
    key_suffix = page + "_".join(f"{k}{v}" for k, v in params.items())    
    button_key = f"nav_link_btn_{hash(key_suffix)}"

    if st.button(text, key=button_key):
        if hasattr(st, 'navigate_to_app'):
            st.navigate_to_app(page, **params)
        else: # Fallback
            temp_q_params = {"page": page.lower().replace(" ","_")}
            temp_q_params.update(params)
            st.query_params = temp_q_params
            st.rerun()

def handle_navigation_event(event_type, **params):
    """
    Обрабатывает навигационные события.
    Эта функция также должна использовать app.navigate_to и app.go_back.
    """
    if event_type == 'back':
        if hasattr(st, 'app_go_back') and callable(st.app_go_back):
            if st.app_go_back(): st.rerun()
        else: st.toast("Функция 'Назад' не настроена.")
    elif event_type == 'forward':
        st.toast("Функция 'Вперед' требует обновления.")
    elif event_type == 'home':
        if hasattr(st, 'navigate_to_app'): st.navigate_to_app("Обзор")
        else: 
            st.query_params = {"page": "overview"}
            st.rerun()
    elif event_type == 'navigate':
        if 'page' in params:
            page_to_nav = params.pop('page')
            if hasattr(st, 'navigate_to_app'): st.navigate_to_app(page_to_nav, **params)
            else:
                temp_q_params = {"page": page_to_nav.lower().replace(" ","_")}
                temp_q_params.update(params)
                st.query_params = temp_q_params
                st.rerun()
        else:
            st.error("Ошибка навигации: не указана страница назначения")
    else:
        st.error(f"Неизвестный тип навигационного события: {event_type}") 
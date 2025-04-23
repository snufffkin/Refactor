import os
import streamlit.components.v1 as components
import streamlit as st

# Получаем абсолютный путь к папке компонента
COMPONENT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend/build")

# Создаем экземпляр компонента
_navigation_component = components.declare_component(
    "navigation_component",
    path=COMPONENT_PATH,
)

def navigation_menu(navigation_data, current_page="overview", current_params=None, key=None):
    """
    Отображает навигационное меню
    
    Args:
        navigation_data: Данные для навигации
        current_page: Текущая страница
        current_params: Текущие параметры URL
        key: Уникальный ключ компонента
        
    Returns:
        dict: Результат взаимодействия с компонентом
    """
    if current_params is None:
        current_params = {}
    
    # Вызываем компонент
    component_value = _navigation_component(
        navigationData=navigation_data,
        currentPage=current_page,
        currentParams=current_params,
        key=key,
        default=None
    )
    
    # Обрабатываем результат
    if component_value and component_value.get("action") == "navigate":
        # Получаем URL для навигации
        url = component_value.get("url")
        if url:
            # Устанавливаем URL-параметры
            st.query_params.update_from_url(url)
    
    return component_value
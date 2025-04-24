import os
import streamlit.components.v1 as components
import streamlit as st

# Определяем текущий каталог
current_dir = os.path.dirname(os.path.abspath(__file__))

# Путь к директории сборки фронтенда (TypeScript-компонент)
build_path = os.path.abspath(os.path.join(
    current_dir, "..", "..", "component-template", "streamlit-navbar", "streamlit_navbar", "frontend", "build"
))

# Определяем режим работы
_RELEASE = os.path.exists(build_path)  # Проверяем существует ли директория сборки

# Объявляем компонент
if _RELEASE:
    # В продакшн режиме используем сборку
    _component_func = components.declare_component(
        "navigation_component", 
        path=build_path
    )
else:
    # В режиме разработки используем dev-сервер
    _component_func = components.declare_component(
        "navigation_component",
        url="http://localhost:3001",
    )

def navigation_menu(navigation_data, current_page="overview", current_params=None, key=None):
    """
    Отображает навигационное меню
    
    Args:
        navigation_data: Структура данных для навигации 
        current_page: Текущая активная страница
        current_params: Словарь с текущими параметрами URL
        key: Уникальный ключ компонента
        
    Returns:
        Результат взаимодействия с компонентом
    """
    if current_params is None:
        current_params = {}
    
    # Вызываем компонент
    component_value = _component_func(
        navigationData=navigation_data,
        currentPage=current_page,
        currentParams=current_params,
        key=key,
        default=None
    )
    
    # Обрабатываем результат
    if component_value and component_value.get("action") == "navigate":
        url = component_value.get("url", "")
        if url and hasattr(st, "query_params"):
            # Получаем параметры из URL
            params = parse_query_params(url)
            # Устанавливаем параметры
            st.query_params.update(params)
    
    return component_value

def parse_query_params(url):
    """Извлекает параметры из URL строки"""
    import urllib.parse as ul
    
    # Получаем часть URL с параметрами
    parts = url.split("?", 1)
    if len(parts) < 2:
        return {}
    
    query = parts[1]
    if not query:
        return {}
    
    # Парсим параметры
    params = {}
    for param in query.split("&"):
        if "=" in param:
            key, value = param.split("=", 1)
            params[key] = ul.unquote_plus(value)
    
    return params
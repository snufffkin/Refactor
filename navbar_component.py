import os
import streamlit.components.v1 as components
import streamlit as st

# Определяем путь к сборке TS компонента
_build_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "components",
    "streamlit-navbar",
    "streamlit_navbar",
    "frontend",
    "build",
)

# Объявляем компонент
_navbar_component = components.declare_component(
    "streamlit_navbar",
    path=_build_path,
)

def navigation_menu(navigation_data, current_page="overview", current_params=None, key=None):
    """Отображает боковую навигацию через TS компонент"""
    if current_params is None:
        current_params = {}
    # Вызываем TS компонент
    component_value = _navbar_component(
        navigationData=navigation_data,
        currentPage=current_page,
        currentParams=current_params,
        key=key,
        default=None,
    )
    return component_value 
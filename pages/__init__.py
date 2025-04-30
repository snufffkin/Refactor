# pages/__init__.py
"""
Экспорты функций страниц для удобного импорта
"""

# Импорт функций боковой панели
from .sidebar import sidebar_filters

# Импорт функций страниц
from .overview import page_overview
from .programs import page_programs 
from .modules import page_modules
from .lessons import page_lessons
from .gz import page_gz
from .cards import page_cards 
from .admin import page_admin
from .my_tasks import page_my_tasks
from .methodist_admin import page_methodist_admin
from .sidebar import render_sidebar
from .refactor_planning import page_refactor_planning
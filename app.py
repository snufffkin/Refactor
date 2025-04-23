# app.py — точка входа Streamlit с JSON-навигацией
"""
Обновленная версия с улучшенным интерфейсом и структурой проекта.
Поддерживает продвинутую аналитику на всех уровнях иерархии курса:
Программа -> Модуль -> Урок -> ГЗ (группы заданий) -> Карточка
"""

import urllib.parse as ul
import streamlit as st
import os
import shutil

import core
import pages
from navigation_data import prepare_navigation_json

# Проверяем и создаем директорию компонентов, если она не существует
components_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "components")
if not os.path.exists(components_dir):
    os.makedirs(components_dir)

# Путь к HTML файлу навигации
html_path = os.path.join(components_dir, "navigation.html")

# Копируем HTML из артефакта если файл не существует
if not os.path.exists(html_path):
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <style>
        /* Общие стили */
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: "Source Sans Pro", sans-serif;
            font-size: 14px;
            color: rgba(255, 255, 255, 0.95);
            background-color: transparent;
        }
        .sidebar-menu {
            width: 100%;
            max-width: 300px;
        }

        /* Стили для списков */
        ul.nav-list {
            list-style-type: none;
            margin: 0;
            padding: 0;
        }
        ul.nav-list ul {
            padding-left: 20px;
            overflow: hidden;
            max-height: 0;
            transition: max-height 0.3s ease-out;
        }
        ul.nav-list ul.expanded {
            max-height: 1000px; /* Временное значение, подстраивается JS */
            transition: max-height 0.5s ease-in;
        }

        /* Стили для элементов */
        .nav-item {
            margin: 2px 0;
        }
        .nav-link-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 6px 10px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .nav-link-container:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        .nav-link-container.active {
            background-color: rgba(77, 166, 255, 0.2);
        }
        .nav-link {
            display: flex;
            align-items: center;
            flex-grow: 1;
            text-decoration: none;
            color: rgba(255, 255, 255, 0.9);
        }
        .nav-circle {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .nav-circle.blue {
            background-color: #4da6ff;
        }
        .nav-circle.green {
            background-color: #09ab3b;
        }
        .nav-circle.orange {
            background-color: #ff8f00;
        }
        .nav-circle.red {
            background-color: #ff4b4b;
        }
        .nav-page-name {
            flex-grow: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .nav-page-name.active {
            font-weight: 600;
        }
        .nav-accordion {
            cursor: pointer;
            margin-left: 8px;
            width: 22px;
            height: 22px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
        }
        .nav-accordion:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        .nav-accordion-icon {
            font-size: 16px;
            color: rgba(255, 255, 255, 0.6);
            transition: transform 0.3s;
        }
        .nav-accordion-icon.open {
            transform: rotate(0deg);
        }
        .nav-accordion-icon.close {
            transform: rotate(45deg);
        }

        /* Иконки для элементов */
        .icon {
            margin-right: 8px;
            font-size: 16px;
        }
        
        /* Дополнительные стили для разделов */
        .section-title {
            padding: 10px 10px 5px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.7);
            font-size: 16px;
        }
        .nav-separator {
            height: 1px;
            background-color: rgba(255, 255, 255, 0.1);
            margin: 10px 0;
        }
        
        /* Стили для загрузки */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            color: rgba(255, 255, 255, 0.7);
        }
        .loading-spinner {
            width: 20px;
            height: 20px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top: 2px solid #4da6ff;
            border-radius: 50%;
            margin-right: 10px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Стили для ошибки */
        .error-message {
            padding: 10px;
            background-color: rgba(255, 77, 77, 0.2);
            border-radius: 4px;
            margin: 10px;
            color: #ff4d4d;
        }
    </style>
</head>
<body>
    <div class="sidebar-menu" id="sidebar-menu">
        <div class="section-title">Основные разделы</div>
        <ul class="nav-list" id="main-nav">
            <!-- Здесь будут основные разделы -->
            <div class="loading">
                <div class="loading-spinner"></div>
                <span>Загрузка навигации...</span>
            </div>
        </ul>
        
        <div class="nav-separator"></div>
        
        <div class="section-title">Структура курсов</div>
        <ul class="nav-list" id="courses-nav">
            <!-- Здесь будет структура курсов -->
        </ul>
        
        <div class="nav-separator"></div>
        
        <div class="section-title">Фильтры</div>
        <ul class="nav-list" id="filters-nav">
            <li class="nav-item">
                <div class="nav-link-container" id="nav-filters">
                    <span class="nav-link">
                        <span class="icon">🔍</span>
                        <span class="nav-page-name">Расширенные фильтры</span>
                    </span>
                    <div class="nav-accordion" onclick="toggleSubmenu('filters-submenu')">
                        <span class="nav-accordion-icon open">+</span>
                    </div>
                </div>
                <ul class="nav-list" id="filters-submenu">
                    <li class="nav-item filter-item">
                        <div class="filter-placeholder">
                            Фильтры доступны в боковой панели Streamlit
                        </div>
                    </li>
                </ul>
            </li>
        </ul>
    </div>

    <script>
        // Функция для получения текущих URL-параметров
        function getUrlParams() {
            const params = {};
            const searchParams = new URLSearchParams(window.parent.location.search);
            for (const [key, value] of searchParams.entries()) {
                params[key] = value;
            }
            return params;
        }
        
        // Функция для генерации HTML-структуры на основе данных
        function generateNavigation(data) {
            const currentParams = getUrlParams();
            const currentPage = currentParams.page || 'overview';
            
            // Очищаем загрузчик
            document.getElementById('main-nav').innerHTML = '';
            document.getElementById('courses-nav').innerHTML = '';
            
            // Генерируем основные разделы
            if (data.main_sections && data.main_sections.length > 0) {
                const mainNav = document.getElementById('main-nav');
                
                data.main_sections.forEach(section => {
                    const isActive = currentPage === section.id;
                    
                    const sectionLi = document.createElement('li');
                    sectionLi.className = 'nav-item';
                    
                    const sectionContainer = document.createElement('div');
                    sectionContainer.className = `nav-link-container${isActive ? ' active' : ''}`;
                    sectionContainer.id = `nav-${section.id}`;
                    
                    const sectionLink = document.createElement('a');
                    sectionLink.href = section.url;
                    sectionLink.className = 'nav-link';
                    sectionLink.innerHTML = `
                        <span class="icon">${section.icon}</span>
                        <span class="nav-page-name${isActive ? ' active' : ''}">${section.name}</span>
                    `;
                    
                    sectionContainer.appendChild(sectionLink);
                    sectionLi.appendChild(sectionContainer);
                    mainNav.appendChild(sectionLi);
                });
            }
            
            // Генерируем структуру курсов
            if (data.programs && data.programs.length > 0) {
                const coursesNav = document.getElementById('courses-nav');
                
                data.programs.forEach(program => {
                    const programLi = document.createElement('li');
                    programLi.className = 'nav-item';
                    
                    // Определяем, активна ли программа
                    const isActiveProgram = program.id === currentParams.program;
                    
                    // Создаем элемент контейнера для программы
                    const programContainer = document.createElement('div');
                    programContainer.className = `nav-link-container${isActiveProgram ? ' active' : ''}`;
                    programContainer.id = `nav-program-${program.id.replace(/\s+/g, '-').toLowerCase()}`;
                    
                    // Создаем ссылку на программу
                    const programLink = document.createElement('a');
                    programLink.href = program.url;
                    programLink.className = 'nav-link';
                    programLink.innerHTML = `
                        <span class="icon">📚</span>
                        <span class="nav-page-name${isActiveProgram ? ' active' : ''}">${program.name}</span>
                    `;
                    
                    // Создаем кнопку аккордеона для программы
                    const programAccordion = document.createElement('div');
                    programAccordion.className = 'nav-accordion';
                    programAccordion.onclick = function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        toggleSubmenu(`program-${program.id.replace(/\s+/g, '-').toLowerCase()}-submenu`);
                    };
                    
                    const programAccordionIcon = document.createElement('span');
                    programAccordionIcon.className = `nav-accordion-icon ${program.modules.length > 0 ? 'open' : ''}`;
                    programAccordionIcon.textContent = '+';
                    
                    programAccordion.appendChild(programAccordionIcon);
                    programContainer.appendChild(programLink);
                    programContainer.appendChild(programAccordion);
                    programLi.appendChild(programContainer);
                    
                    // Создаем подменю для модулей программы
                    const modulesUl = document.createElement('ul');
                    modulesUl.className = 'nav-list';
                    modulesUl.id = `program-${program.id.replace(/\s+/g, '-').toLowerCase()}-submenu`;
                    
                    // Если программа активна, раскрываем подменю
                    if (isActiveProgram) {
                        modulesUl.classList.add('expanded');
                        programAccordionIcon.classList.remove('open');
                        programAccordionIcon.classList.add('close');
                        programAccordionIcon.textContent = '✕';
                    }
                    
                    // Создаем элементы для модулей программы
                    if (program.modules && program.modules.length > 0) {
                        program.modules.forEach(module => {
                            const moduleLi = document.createElement('li');
                            moduleLi.className = 'nav-item';
                            
                            // Определяем, активен ли модуль
                            const isActiveModule = isActiveProgram && module.id === currentParams.module;
                            
                            // Создаем элемент контейнера для модуля
                            const moduleContainer = document.createElement('div');
                            moduleContainer.className = `nav-link-container${isActiveModule ? ' active' : ''}`;
                            
                            // Создаем ссылку на модуль
                            const moduleLink = document.createElement('a');
                            moduleLink.href = module.url;
                            moduleLink.className = 'nav-link';
                            moduleLink.innerHTML = `
                                <span class="nav-circle blue"></span>
                                <span class="nav-page-name${isActiveModule ? ' active' : ''}">${module.name}</span>
                            `;
                            
                            // Создаем кнопку аккордеона для модуля
                            const moduleAccordion = document.createElement('div');
                            moduleAccordion.className = 'nav-accordion';
                            moduleAccordion.onclick = function(e) {
                                e.preventDefault();
                                e.stopPropagation();
                                toggleSubmenu(`module-${program.id.replace(/\s+/g, '-').toLowerCase()}-${module.id.replace(/\s+/g, '-').toLowerCase()}-submenu`);
                            };
                            
                            const moduleAccordionIcon = document.createElement('span');
                            moduleAccordionIcon.className = `nav-accordion-icon ${module.lessons && module.lessons.length > 0 ? 'open' : ''}`;
                            moduleAccordionIcon.textContent = '+';
                            
                            moduleAccordion.appendChild(moduleAccordionIcon);
                            moduleContainer.appendChild(moduleLink);
                            moduleContainer.appendChild(moduleAccordion);
                            moduleLi.appendChild(moduleContainer);
                            
                            // Создаем подменю для уроков модуля
                            const lessonsUl = document.createElement('ul');
                            lessonsUl.className = 'nav-list';
                            lessonsUl.id = `module-${program.id.replace(/\s+/g, '-').toLowerCase()}-${module.id.replace(/\s+/g, '-').toLowerCase()}-submenu`;
                            
                            // Если модуль активен, раскрываем подменю
                            if (isActiveModule) {lessonsUl.classList.add('expanded');
                                moduleAccordionIcon.classList.remove('open');
                                moduleAccordionIcon.classList.add('close');
                                moduleAccordionIcon.textContent = '✕';
                            }
                            
                            // Создаем элементы для уроков модуля
                            if (module.lessons && module.lessons.length > 0) {
                                module.lessons.forEach(lesson => {
                                    const lessonLi = document.createElement('li');
                                    lessonLi.className = 'nav-item';
                                    
                                    // Определяем, активен ли урок
                                    const isActiveLesson = isActiveModule && lesson.id === currentParams.lesson;
                                    
                                    // Создаем элемент контейнера для урока
                                    const lessonContainer = document.createElement('div');
                                    lessonContainer.className = `nav-link-container${isActiveLesson ? ' active' : ''}`;
                                    
                                    // Создаем ссылку на урок
                                    const lessonLink = document.createElement('a');
                                    lessonLink.href = lesson.url;
                                    lessonLink.className = 'nav-link';
                                    lessonLink.innerHTML = `
                                        <span class="nav-circle blue"></span>
                                        <span class="nav-page-name${isActiveLesson ? ' active' : ''}">${lesson.name}</span>
                                    `;
                                    
                                    // Создаем кнопку аккордеона для урока
                                    const lessonAccordion = document.createElement('div');
                                    lessonAccordion.className = 'nav-accordion';
                                    lessonAccordion.onclick = function(e) {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        toggleSubmenu(`lesson-${program.id.replace(/\s+/g, '-').toLowerCase()}-${module.id.replace(/\s+/g, '-').toLowerCase()}-${lesson.id.replace(/\s+/g, '-').toLowerCase()}-submenu`);
                                    };
                                    
                                    const lessonAccordionIcon = document.createElement('span');
                                    lessonAccordionIcon.className = `nav-accordion-icon ${lesson.groups && lesson.groups.length > 0 ? 'open' : ''}`;
                                    lessonAccordionIcon.textContent = '+';
                                    
                                    lessonAccordion.appendChild(lessonAccordionIcon);
                                    lessonContainer.appendChild(lessonLink);
                                    lessonContainer.appendChild(lessonAccordion);
                                    lessonLi.appendChild(lessonContainer);
                                    
                                    // Создаем подменю для групп заданий урока
                                    const groupsUl = document.createElement('ul');
                                    groupsUl.className = 'nav-list';
                                    groupsUl.id = `lesson-${program.id.replace(/\s+/g, '-').toLowerCase()}-${module.id.replace(/\s+/g, '-').toLowerCase()}-${lesson.id.replace(/\s+/g, '-').toLowerCase()}-submenu`;
                                    
                                    // Если урок активен, раскрываем подменю
                                    if (isActiveLesson) {
                                        groupsUl.classList.add('expanded');
                                        lessonAccordionIcon.classList.remove('open');
                                        lessonAccordionIcon.classList.add('close');
                                        lessonAccordionIcon.textContent = '✕';
                                    }
                                    
                                    // Создаем элементы для групп заданий урока
                                    if (lesson.groups && lesson.groups.length > 0) {
                                        lesson.groups.forEach(group => {
                                            const groupLi = document.createElement('li');
                                            groupLi.className = 'nav-item';
                                            
                                            // Определяем, активна ли группа заданий
                                            const isActiveGroup = isActiveLesson && group.id === currentParams.gz;
                                            
                                            // Создаем элемент контейнера для группы заданий
                                            const groupContainer = document.createElement('div');
                                            groupContainer.className = `nav-link-container${isActiveGroup ? ' active' : ''}`;
                                            
                                            // Создаем ссылку на группу заданий
                                            const groupLink = document.createElement('a');
                                            groupLink.href = group.url;
                                            groupLink.className = 'nav-link';
                                            groupLink.innerHTML = `
                                                <span class="nav-circle blue"></span>
                                                <span class="nav-page-name${isActiveGroup ? ' active' : ''}">${group.name}</span>
                                            `;
                                            
                                            // Создаем кнопку аккордеона для группы заданий
                                            const groupAccordion = document.createElement('div');
                                            groupAccordion.className = 'nav-accordion';
                                            groupAccordion.onclick = function(e) {
                                                e.preventDefault();
                                                e.stopPropagation();
                                                toggleSubmenu(`group-${program.id.replace(/\s+/g, '-').toLowerCase()}-${module.id.replace(/\s+/g, '-').toLowerCase()}-${lesson.id.replace(/\s+/g, '-').toLowerCase()}-${group.id.replace(/\s+/g, '-').toLowerCase()}-submenu`);
                                            };
                                            
                                            const groupAccordionIcon = document.createElement('span');
                                            groupAccordionIcon.className = `nav-accordion-icon ${group.cards && group.cards.length > 0 ? 'open' : ''}`;
                                            groupAccordionIcon.textContent = '+';
                                            
                                            groupAccordion.appendChild(groupAccordionIcon);
                                            groupContainer.appendChild(groupLink);
                                            groupContainer.appendChild(groupAccordion);
                                            groupLi.appendChild(groupContainer);
                                            
                                            // Создаем подменю для карточек группы заданий
                                            const cardsUl = document.createElement('ul');
                                            cardsUl.className = 'nav-list';
                                            cardsUl.id = `group-${program.id.replace(/\s+/g, '-').toLowerCase()}-${module.id.replace(/\s+/g, '-').toLowerCase()}-${lesson.id.replace(/\s+/g, '-').toLowerCase()}-${group.id.replace(/\s+/g, '-').toLowerCase()}-submenu`;
                                            
                                            // Если группа заданий активна, раскрываем подменю
                                            if (isActiveGroup) {
                                                cardsUl.classList.add('expanded');
                                                groupAccordionIcon.classList.remove('open');
                                                groupAccordionIcon.classList.add('close');
                                                groupAccordionIcon.textContent = '✕';
                                            }
                                            
                                            // Создаем элементы для карточек группы заданий
                                            if (group.cards && group.cards.length > 0) {
                                                group.cards.forEach(card => {
                                                    const cardLi = document.createElement('li');
                                                    cardLi.className = 'nav-item';
                                                    
                                                    // Определяем, активна ли карточка
                                                    const isActiveCard = isActiveGroup && card.id === currentParams.card_id;
                                                    
                                                    // Определяем цвет для карточки на основе уровня риска
                                                    let circleClass = 'blue';
                                                    if (card.risk > 0.75) {
                                                        circleClass = 'red';
                                                    } else if (card.risk > 0.5) {
                                                        circleClass = 'orange';
                                                    } else if (card.risk > 0.25) {
                                                        circleClass = 'green';
                                                    }
                                                    
                                                    // Создаем элемент контейнера для карточки
                                                    const cardContainer = document.createElement('div');
                                                    cardContainer.className = `nav-link-container${isActiveCard ? ' active' : ''}`;
                                                    
                                                    // Создаем ссылку на карточку
                                                    const cardLink = document.createElement('a');
                                                    cardLink.href = card.url;
                                                    cardLink.className = 'nav-link';
                                                    cardLink.innerHTML = `
                                                        <span class="nav-circle ${circleClass}"></span>
                                                        <span class="nav-page-name${isActiveCard ? ' active' : ''}">${card.name}</span>
                                                    `;
                                                    
                                                    cardContainer.appendChild(cardLink);
                                                    cardLi.appendChild(cardContainer);
                                                    cardsUl.appendChild(cardLi);
                                                });
                                                
                                                // Если есть еще карточки, которые не отображаются
                                                if (group.has_more_cards) {
                                                    const moreLi = document.createElement('li');
                                                    moreLi.className = 'nav-item';
                                                    
                                                    const moreContainer = document.createElement('div');
                                                    moreContainer.className = 'nav-link-container';
                                                    moreContainer.innerHTML = `
                                                        <span class="nav-link">
                                                            <span class="nav-circle blue"></span>
                                                            <span class="nav-page-name" style="color: rgba(255, 255, 255, 0.5);">...ещё ${group.more_cards_count} карточек</span>
                                                        </span>
                                                    `;
                                                    
                                                    moreLi.appendChild(moreContainer);
                                                    cardsUl.appendChild(moreLi);
                                                }
                                            }
                                            
                                            groupLi.appendChild(cardsUl);
                                            groupsUl.appendChild(groupLi);
                                        });
                                    }
                                    
                                    lessonLi.appendChild(groupsUl);
                                    lessonsUl.appendChild(lessonLi);
                                });
                            }
                            
                            moduleLi.appendChild(lessonsUl);
                            modulesUl.appendChild(moduleLi);
                        });
                    }
                    
                    programLi.appendChild(modulesUl);
                    coursesNav.appendChild(programLi);
                });
            } else {
                // Если нет данных о программах
                const noDataEl = document.createElement('div');
                noDataEl.className = 'loading';
                noDataEl.innerHTML = 'Нет данных о курсах';
                document.getElementById('courses-nav').appendChild(noDataEl);
            }
        }
        
        // Функция для раскрытия/скрытия подменю
        function toggleSubmenu(submenuId) {
            const submenu = document.getElementById(submenuId);
            if (!submenu) return;
            
            const isExpanded = submenu.classList.contains('expanded');
            const accordionIcon = submenu.previousElementSibling.querySelector('.nav-accordion-icon');
            
            if (isExpanded) {
                submenu.classList.remove('expanded');
                if (accordionIcon) {
                    accordionIcon.classList.remove('close');
                    accordionIcon.classList.add('open');
                    accordionIcon.textContent = '+';
                }
            } else {
                submenu.classList.add('expanded');
                if (accordionIcon) {
                    accordionIcon.classList.remove('open');
                    accordionIcon.classList.add('close');
                    accordionIcon.textContent = '✕';
                }
            }
        }
        
        // Загружаем данные навигации из JSON-файла
        async function loadNavigationData() {
            try {
                const response = await fetch('../navigation_data.json');
                if (!response.ok) {
                    throw new Error(`Ошибка загрузки данных: ${response.status}`);
                }
                const data = await response.json();
                generateNavigation(data);
            } catch (error) {
                console.error('Ошибка загрузки навигации:', error);
                
                // Показываем сообщение об ошибке
                const errorMessage = document.createElement('div');
                errorMessage.className = 'error-message';
                errorMessage.textContent = `Не удалось загрузить навигацию: ${error.message}`;
                
                document.getElementById('main-nav').innerHTML = '';
                document.getElementById('main-nav').appendChild(errorMessage);
            }
        }
        
        // Запускаем загрузку данных при загрузке страницы
        document.addEventListener('DOMContentLoaded', loadNavigationData);
    </script>
</body>
</html>""")

# Путь к JSON файлу навигации
json_path = os.path.join(components_dir, "navigation_data.json")

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
    
    /* Улучшения для iframe */
    iframe {
        border: none !important;
        padding: 0 !important;
    }
    
    /* Кастомизация элементов Streamlit в сайдбаре */
    div[data-testid="stSidebar"] div[data-testid="stMarkdown"] h3 {
        color: rgba(255, 255, 255, 0.7);
        font-size: 16px;
        font-weight: 600;
        margin-top: 20px;
        margin-bottom: 10px;
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

# Создаем engine вне кэширования
engine = core.get_engine()
data = load_cached_data(engine)

# Проверяем, существует ли файл JSON с навигацией, если нет - создаем его
if not os.path.exists(json_path) or st.session_state.get("update_navigation", False):
    prepare_navigation_json(data, json_path)
    st.session_state["update_navigation"] = False

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

# Запоминаем текущую страницу в состоянии
st.session_state["page"] = current_page

# Запускаем выбранную страницу
PAGES[current_page](data)
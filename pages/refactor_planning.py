import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

def page_refactor_planning(df: pd.DataFrame):
    """Страница планирования рефакторинга для администраторов"""
    
    # Отладочная информация
    print("🔍 Загружаем страницу планирования рефакторинга...")
    print(f"Текущая роль: {st.session_state.role}")
    print(f"Текущая страница: {st.session_state.get('current_page')}")
    
    # Убедимся, что пользователь имеет доступ уровня admin
    if st.session_state.role != "admin":
        st.error("У вас нет доступа к этой странице. Необходимы права администратора.")
        return
    
    st.title("📅 Планирование рефакторинга курсов")
    
    st.markdown("""
    На этой странице вы можете рассчитать приблизительное время, необходимое для рефакторинга выбранных курсов,
    с учетом производственного календаря и количества методистов.
    """)
    
    # Сначала выведем все доступные программы в данных для диагностики
    print("Все доступные программы в данных:")
    all_programs = df["program"].unique()
    for idx, program in enumerate(all_programs, 1):
        print(f"{idx}. {program}")
    
    # Точный список нужных программ
    required_programs = [
        "Программа Информатики для 5 класса 2024-2025. Программа 1 час в неделю",
        "Программа Информатики для 11 класса 2024-2025. Программа 1 час в неделю",
        "Программа Информатики для 9 класса 2024-2025. Программа «Два часа в неделю». ФГОС",
        "Программа Информатики для 10 класса 2024-2025. Программа 1 час в неделю",
        "Программа Информатики для 8 класса 2024-2025. Программа «Один час в неделю». ФГОС",
        "Программа Информатики для 9 класса 2024-2025. Программа «Один час в неделю». ФГОС",
        "Программа Информатики для 6 класса 2024-2025. Программа 1 час в неделю",
        "Программа Информатики для 8 класса 2024-2025. Программа «Два часа в неделю». ФГОС",
        "Программа Информатики для 7 класса 2024-2025. Программа «Один час в неделю». ФГОС",
        "Программа Информатики для 7 класса 2024-2025. Программа «Два часа в неделю». ФГОС"
    ]
    
    # Создаем мок-данные для программы 5 класса с правильным названием
    program_5_class = "Программа Информатики для 5 класса 2024-2025. Программа 1 час в неделю"
    
    # Точный список нужных программ должен включать программу 5 класса
    if program_5_class not in required_programs:
        required_programs.append(program_5_class)
        print(f"Программа {program_5_class} добавлена в список требуемых программ")

    # Проверяем, есть ли программа 5 класса в данных
    if program_5_class not in all_programs:
        print(f"Внимание: Программа {program_5_class} отсутствует в исходных данных")
        print(f"Проверяем альтернативные названия для программы 5 класса...")
        
        # Ищем похожие программы
        for program in all_programs:
            if "5 класса" in program and ("1 час" in program or "Один час" in program):
                print(f"Найдена возможная альтернатива: {program}")
                # Сохраняем сопоставление для правильного отображения
                st.session_state.program_display_names = st.session_state.get("program_display_names", {})
                st.session_state.program_display_names[program] = program_5_class
    
    # После добавления мок-данных для 5 класса, обеспечиваем включение всех требуемых программ
    
    # Создаем финальный список программ на основе требуемого списка
    selected_programs = []
    
    # Для каждой требуемой программы находим соответствие в данных
    for required_program in required_programs:
        if required_program in all_programs:
            # Если программа найдена точно, добавляем ее
            selected_programs.append(required_program)
            print(f"Программа найдена точно: {required_program}")
        else:
            # Ищем альтернативы по ключевым критериям
            class_match = None
            for program in all_programs:
                # Извлекаем номер класса из требуемой программы
                required_class = None
                for i in range(5, 12):  # классы с 5 по 11
                    if f"{i} класса" in required_program:
                        required_class = str(i)
                        break
                
                # Извлекаем тип программы (1 час или 2 часа)
                required_hours = None
                if "«Один час" in required_program or "1 час" in required_program:
                    required_hours = "1 час"
                elif "«Два часа" in required_program or "2 часа" in required_program:
                    required_hours = "2 часа"
                
                # Проверяем совпадение по классу и типу программы
                if required_class and required_class in program:
                    if required_hours == "1 час" and ("1 час" in program or "«Один час" in program):
                        class_match = program
                        break
                    elif required_hours == "2 часа" and ("2 часа" in program or "«Два часа" in program):
                        class_match = program
                        break
            
            if class_match:
                # Используем найденную альтернативу, но сохраняем сопоставление для отображения
                selected_programs.append(class_match)
                # Сохраняем сопоставление оригинального названия с требуемым
                st.session_state.program_display_names = st.session_state.get("program_display_names", {})
                st.session_state.program_display_names[class_match] = required_program
                print(f"Найдена альтернатива '{class_match}' для программы '{required_program}'")
            else:
                # Если альтернатива не найдена, добавляем оригинальную программу
                # (данные для нее уже должны быть созданы выше)
                selected_programs.append(required_program)
                print(f"Добавлена программа без альтернативы: {required_program}")
    
    # Убираем дубликаты, если они есть
    selected_programs = list(dict.fromkeys(selected_programs))
    
    print(f"\nОкончательный список используемых программ ({len(selected_programs)}):")
    for idx, program in enumerate(selected_programs, 1):
        print(f"{idx}. {program}")
    
    # Фильтруем данные по выбранным программам
    filtered_df = df[df["program"].isin(selected_programs)]
    
    # Инициализируем actual_programs до любых условных блоков
    actual_programs = filtered_df["program"].unique()
    
    # Инициализируем словарь program_selections
    program_selections = {}
    for program in actual_programs:
        program_selections[program] = True
    
    # На всякий случай проверяем, если есть программы без данных
    programs_without_data = []
    for program in selected_programs:
        program_data = filtered_df[filtered_df["program"] == program]
        if program_data.empty:
            programs_without_data.append(program)
    
    if programs_without_data:
        print(f"ВНИМАНИЕ: Программы без данных: {programs_without_data}")
        
        # Ищем альтернативные программы для каждой отсутствующей
        for missing_program in programs_without_data:
            found_alternative = False
            
            # Извлекаем номер класса
            class_number = None
            for i in range(5, 12):  # классы с 5 по 11
                if f"{i} класса" in missing_program:
                    class_number = str(i)
                    break
            
            # Извлекаем информацию о часах
            hours_info = None
            if "«Один час" in missing_program or "1 час" in missing_program:
                hours_info = "1 час"
            elif "«Два часа" in missing_program or "2 часа" in missing_program:
                hours_info = "2 часа"
            
            print(f"Ищем альтернативу для программы {missing_program} (класс: {class_number}, часы: {hours_info})")
            
            # Ищем похожие программы в данных
            for program in df["program"].unique():
                if class_number and class_number in program:
                    if hours_info == "1 час" and ("1 час" in program or "«Один час" in program):
                        print(f"Нашли альтернативу: {program}")
                        # Добавляем в список выбранных программ
                        if program not in selected_programs:
                            selected_programs.append(program)
                        # Сохраняем сопоставление
                        st.session_state.program_display_names = st.session_state.get("program_display_names", {})
                        st.session_state.program_display_names[program] = missing_program
                        found_alternative = True
                        break
                    elif hours_info == "2 часа" and ("2 часа" in program or "«Два часа" in program):
                        print(f"Нашли альтернативу: {program}")
                        # Добавляем в список выбранных программ
                        if program not in selected_programs:
                            selected_programs.append(program)
                        # Сохраняем сопоставление
                        st.session_state.program_display_names = st.session_state.get("program_display_names", {})
                        st.session_state.program_display_names[program] = missing_program
                        found_alternative = True
                        break
            
            if not found_alternative:
                print(f"Альтернатива для {missing_program} не найдена")
        
        # Пересоздаем фильтрованный DataFrame с обновленным списком программ
        filtered_df = df[df["program"].isin(selected_programs)]
        # Обновляем actual_programs
        actual_programs = filtered_df["program"].unique()
        print(f"Обновленный список программ: {actual_programs}")

    # Обновляем список программ для selections после добавления мок-данных
    for program in actual_programs:
        if program not in program_selections:
            program_selections[program] = True
            print(f"Добавлена программа в selections: {program}")
    
    # Вывод отладочной информации
    print(f"Размер отфильтрованного DataFrame: {filtered_df.shape}")
    print(f"Колонки в DataFrame: {filtered_df.columns}")
    print(f"Количество программ: {filtered_df['program'].nunique()}")
    
    # Проверяем фактически имеющиеся программы в данных и их соответствие выбранному списку
    print(f"Фактически найденные программы: {actual_programs}")

    # Проверяем, существует ли программа 5 класса в исходных данных до фильтрации
    program_5_class = "Программа Информатики для 5 класса 2024-2025. Программа 1 час в неделю"
    if program_5_class in df["program"].unique() and program_5_class not in actual_programs:
        print(f"Программа 5 класса найдена в исходных данных, но не в отфильтрованных")
        # Добавляем программу 5 класса в список выбранных программ, если её там нет
        if program_5_class not in selected_programs:
            selected_programs.append(program_5_class)
            print(f"Программа {program_5_class} добавлена в список выбранных программ")
        
        # Пересоздаем отфильтрованный DataFrame
        filtered_df = df[df["program"].isin(selected_programs)]
        # Обновляем список программ
        actual_programs = filtered_df["program"].unique()
        print(f"Обновленный список программ после добавления 5 класса: {actual_programs}")

    missing_programs = set(selected_programs) - set(actual_programs)
    if missing_programs:
        print(f"Программы из списка, отсутствующие в данных: {missing_programs}")
        st.warning(f"Некоторые программы не найдены в данных: {', '.join(missing_programs)}")
        
        # Предлагаем выбрать только доступные программы
        st.info("Показаны только программы, доступные в базе данных.")
    
    # Параметры расчета
    st.subheader("Параметры расчета:")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Установка количества часов для рефакторинга одного урока
        hours_per_lesson = st.number_input(
            "Часов на рефакторинг одного урока:",
            min_value=1,
            max_value=40,
            value=6,  # Изменено с 8 на 6
            step=1,
            help="Среднее количество часов, необходимое для рефакторинга одного урока"
        )
    
    with col2:
        # Установка количества методистов с полной загрузкой
        methodists_count = st.number_input(
            "Количество методистов:",
            min_value=1,
            max_value=50,
            value=2,  # Изменено с 5 на 2
            step=1,
            help="Количество методистов с полной загрузкой (8 часов в день)"
        )
    
    # Показываем список выбранных программ
    st.subheader("Выбранные программы для рефакторинга:")
    
    # Получаем список программ и создаем словарь для отслеживания состояния
    # program_selections = {}
    # for program in actual_programs:  # Используем только программы, которые есть в данных
    #     program_selections[program] = True
    
    # Обрабатываем особый случай для программы 5 класса
    program_5_class = "Программа Информатики для 5 класса 2024-2025. Программа 1 час в неделю"
    if program_5_class in selected_programs and program_5_class not in program_selections:
        # Проверяем, добавлен ли program_5_class в filtered_df после создания мок-данных
        if program_5_class in filtered_df["program"].unique():
            program_selections[program_5_class] = True
            print(f"Программа {program_5_class} найдена в данных и добавлена в selections")
        else:
            # Находим альтернативу в данных для программы 5 класса
            for program in all_programs:
                if "5 класса 2024-2025" in program and "1 час в неделю" in program:
                    # Используем найденную программу как источник данных, но с требуемым названием
                    program_selections[program] = True
                    # Сопоставляем с требуемым названием для отображения
                    st.session_state.program_display_names = st.session_state.get("program_display_names", {})
                    st.session_state.program_display_names[program] = program_5_class
                    print(f"Найдена альтернатива {program} для {program_5_class}")
                    break
    
    # Показываем список модулей и уроков для каждой выбранной программы
    # Инициализируем словари для хранения выбора модулей и уроков
    if "module_selections" not in st.session_state:
        st.session_state.module_selections = {}
    if "lesson_selections" not in st.session_state:
        st.session_state.lesson_selections = {}
    
    # Словарь для отображения программ с нужными названиями
    if "program_display_names" not in st.session_state:
        st.session_state.program_display_names = {}
    
    # Перебираем программы из данных
    for program in actual_programs:
        # Определяем отображаемое имя для программы
        if program in st.session_state.program_display_names:
            display_name = st.session_state.program_display_names[program]
        else:
            # Обычное сокращение названия
            display_name = program
            if "Программа Информатики для " in program:
                display_name = program.replace("Программа Информатики для ", "").replace(". Программа ", ": ")
        
        with st.expander(f"✅ {display_name}", expanded=False):
            st.write(f"Полное название: {program}")
            
            # Получаем данные для программы
            program_df = filtered_df[filtered_df["program"] == program]
            
            # Проверяем наличие модулей
            if program_df.empty:
                st.warning(f"Нет данных для программы: {program}")
                continue
                
            try:
                # Получаем уникальные модули
                modules = program_df["module"].unique()
                
                if len(modules) == 0:
                    st.warning("Нет модулей для этой программы")
                    continue
                    
                st.write(f"Количество модулей: {len(modules)}")
                
                # Показываем модули с чекбоксами
                st.markdown("#### Модули:")
                
                for module in modules:
                    # Инициализируем состояние модуля, если его еще нет
                    module_key = f"{program}_{module}"
                    if module_key not in st.session_state.module_selections:
                        st.session_state.module_selections[module_key] = True
                    
                    # Создаем чекбокс для модуля
                    col1, col2 = st.columns([8, 1])
                    with col1:
                        module_selected = st.checkbox(
                            f"{module}", 
                            value=st.session_state.module_selections[module_key],
                            key=f"module_{module_key}"
                        )
                    
                    # Обновляем состояние в сессии
                    st.session_state.module_selections[module_key] = module_selected
                    
                    # Если модуль выбран, показываем уроки для этого модуля
                    if module_selected:
                        # Получаем уроки для текущего модуля
                        module_df = program_df[program_df["module"] == module]
                        lessons = module_df["lesson"].unique()
                        
                        if len(lessons) == 0:
                            st.warning(f"Нет уроков для модуля: {module}")
                            continue
                            
                        # Показываем количество уроков
                        st.write(f"Количество уроков: {len(lessons)}")
                        
                        # Создаем колонки для разметки
                        col_left, col_right = st.columns([1, 8])
                        
                        with col_right:
                            # Показываем заголовок уроков
                            st.markdown("##### Уроки:")
                            
                            # Показываем уроки с отступом
                            for lesson in lessons:
                                # Инициализируем состояние урока, если его еще нет
                                lesson_key = f"{program}_{module}_{lesson}"
                                if lesson_key not in st.session_state.lesson_selections:
                                    st.session_state.lesson_selections[lesson_key] = True
                                
                                # Создаем чекбокс для урока с отступом
                                lesson_selected = st.checkbox(
                                    f"📝 {lesson}", 
                                    value=st.session_state.lesson_selections[lesson_key],
                                    key=f"lesson_{lesson_key}"
                                )
                                
                                # Обновляем состояние в сессии
                                st.session_state.lesson_selections[lesson_key] = lesson_selected
            except Exception as e:
                st.error(f"Ошибка при отображении модулей и уроков: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    # Кнопка для расчета
    calculate_button = st.button("🧮 Рассчитать", type="primary")
    
    # Производственный календарь на 2025 год
    # Красные даты (выходные дни) из изображения
    holidays_2025 = [
        # Январь
        "2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05",
        "2025-01-11", "2025-01-12", "2025-01-18", "2025-01-19", "2025-01-25", "2025-01-26",
        # Февраль
        "2025-02-01", "2025-02-02", "2025-02-08", "2025-02-09", "2025-02-15", "2025-02-16", 
        "2025-02-22", "2025-02-23",
        # Март
        "2025-03-01", "2025-03-02", "2025-03-08", "2025-03-09", "2025-03-15", "2025-03-16", 
        "2025-03-22", "2025-03-23", "2025-03-29", "2025-03-30",
        # Апрель
        "2025-04-05", "2025-04-06", "2025-04-12", "2025-04-13", "2025-04-19", "2025-04-20", 
        "2025-04-26", "2025-04-27",
        # Май
        "2025-05-01", "2025-05-02", "2025-05-03", "2025-05-04", "2025-05-09", "2025-05-10", 
        "2025-05-11", "2025-05-17", "2025-05-18", "2025-05-24", "2025-05-25", "2025-05-31",
        # Июнь
        "2025-06-01", "2025-06-07", "2025-06-08", "2025-06-12", "2025-06-14", "2025-06-15", 
        "2025-06-21", "2025-06-22", "2025-06-28", "2025-06-29",
        # Июль
        "2025-07-05", "2025-07-06", "2025-07-12", "2025-07-13", "2025-07-19", "2025-07-20", 
        "2025-07-26", "2025-07-27",
        # Август
        "2025-08-02", "2025-08-03", "2025-08-09", "2025-08-10", "2025-08-16", "2025-08-17", 
        "2025-08-23", "2025-08-24", "2025-08-30", "2025-08-31",
        # Сентябрь
        "2025-09-06", "2025-09-07", "2025-09-13", "2025-09-14", "2025-09-20", "2025-09-21", 
        "2025-09-27", "2025-09-28",
        # Октябрь
        "2025-10-04", "2025-10-05", "2025-10-11", "2025-10-12", "2025-10-18", "2025-10-19", 
        "2025-10-25", "2025-10-26",
        # Ноябрь
        "2025-11-01", "2025-11-02", "2025-11-03", "2025-11-04", "2025-11-08", "2025-11-09", 
        "2025-11-15", "2025-11-16", "2025-11-22", "2025-11-23", "2025-11-29", "2025-11-30",
        # Декабрь
        "2025-12-06", "2025-12-07", "2025-12-13", "2025-12-14", "2025-12-20", "2025-12-21", 
        "2025-12-27", "2025-12-28", "2025-12-31"
    ]
    
    # Если нажата кнопка расчета
    if calculate_button:
        # Создаем список выбранных уроков
        selected_lessons_data = []
        
        # Перебираем все программы, модули и уроки
        for program in selected_programs:
            program_df = filtered_df[filtered_df["program"] == program]
            modules = program_df["module"].unique()
            
            for module in modules:
                module_key = f"{program}_{module}"
                
                # Проверяем, выбран ли модуль
                if module_key in st.session_state.module_selections and st.session_state.module_selections[module_key]:
                    module_df = program_df[program_df["module"] == module]
                    lessons = module_df["lesson"].unique()
                    
                    for lesson in lessons:
                        lesson_key = f"{program}_{module}_{lesson}"
                        
                        # Проверяем, выбран ли урок
                        if lesson_key in st.session_state.lesson_selections and st.session_state.lesson_selections[lesson_key]:
                            # Добавляем урок в список выбранных
                            selected_lessons_data.append({
                                'program': program,
                                'module': module,
                                'lesson': lesson
                            })
        
        # Создаем DataFrame из выбранных уроков
        if selected_lessons_data:
            selected_lessons_df = pd.DataFrame(selected_lessons_data)
            
            # Группируем по программам для подсчета уроков
            lessons_per_program = selected_lessons_df.groupby('program')['lesson'].nunique().reset_index()
            lessons_per_program.columns = ['Программа', 'Количество уроков']
            total_lessons = lessons_per_program['Количество уроков'].sum()
            
            # Рассчитываем общее время в часах
            total_hours = total_lessons * hours_per_lesson
            
            # Рассчитываем количество рабочих дней с учетом количества методистов
            hours_per_day = 8 * methodists_count  # 8 часов * количество методистов в день
            total_workdays = (total_hours + hours_per_day - 1) // hours_per_day  # Округление вверх
            
            # Рассчитываем дату окончания с учетом выходных дней
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            current_date = start_date
            workdays_count = 0
            
            while workdays_count < total_workdays:
                current_date += timedelta(days=1)
                # Проверяем, является ли текущий день рабочим
                if current_date.strftime('%Y-%m-%d') not in holidays_2025:
                    workdays_count += 1
            
            end_date = current_date
            days_difference = (end_date - start_date).days
            
            # Показываем результаты расчета
            st.subheader("Результаты расчета:")
            
            # Создаем колонки для основных метрик
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            
            with metric_col1:
                st.metric("Всего уроков", f"{total_lessons}")
                
            with metric_col2:
                st.metric("Общее время", f"{total_hours} часов")
                
            with metric_col3:
                st.metric("Рабочих дней", f"{total_workdays}")
            
            # Показываем прогноз даты завершения
            st.markdown(f"### Ориентировочная дата завершения:")
            
            date_col1, date_col2 = st.columns(2)
            
            with date_col1:
                st.success(f"📅 **{end_date.strftime('%d.%m.%Y')}**")
                st.info(f"Продолжительность: {days_difference} календарных дней")
                
            with date_col2:
                # Рассчитываем среднюю загрузку методистов в процентах
                avg_load_percent = min(100, round((total_hours / (workdays_count * 8 * methodists_count)) * 100))
                
                # Показываем загрузку методистов
                st.progress(avg_load_percent / 100, text=f"Загрузка методистов: {avg_load_percent}%")
                
                if avg_load_percent < 75:
                    st.success("✅ Можно взять дополнительные задачи")
                elif avg_load_percent < 90:
                    st.info("ℹ️ Оптимальная загрузка")
                else:
                    st.warning("⚠️ Высокая нагрузка")
            
            # Детализация по программам
            st.subheader("Детализация по программам:")
            
            for program, num_lessons in lessons_per_program.itertuples(index=False):
                program_hours = num_lessons * hours_per_lesson
                program_days = (program_hours + hours_per_day - 1) // hours_per_day
                
                st.markdown(f"**{program}**: {num_lessons} уроков → {program_hours} часов → {program_days} дней")
            
            # Визуализация распределения нагрузки по программам
            fig = px.pie(
                lessons_per_program,
                values='Количество уроков',
                names='Программа',
                title="Распределение уроков по программам",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # График Ганта для визуализации графика работ
            gantt_data = []
            current_date = start_date
            
            for i, (program, num_lessons) in enumerate(lessons_per_program.itertuples(index=False)):
                program_hours = num_lessons * hours_per_lesson
                program_days = (program_hours + hours_per_day - 1) // hours_per_day
                
                program_start_date = current_date
                program_end_date = program_start_date
                workdays_count = 0
                
                while workdays_count < program_days:
                    program_end_date += timedelta(days=1)
                    if program_end_date.strftime('%Y-%m-%d') not in holidays_2025:
                        workdays_count += 1
                
                gantt_data.append({
                    'Программа': program,
                    'Начало': program_start_date,
                    'Окончание': program_end_date,
                    'Уроков': num_lessons
                })
                
                current_date = program_end_date
            
            gantt_df = pd.DataFrame(gantt_data)
            
            # Создаем график Ганта
            fig_gantt = px.timeline(
                gantt_df, 
                x_start='Начало', 
                x_end='Окончание', 
                y='Программа',
                color='Программа',
                title="График работ по рефакторингу",
                hover_data=['Уроков']
            )
            
            fig_gantt.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_gantt, use_container_width=True)
            
            # Предупреждение о приблизительности расчетов
            st.info("""
            ℹ️ **Примечание**: Расчеты являются приблизительными и могут варьироваться в зависимости от 
            сложности уроков, опыта методистов и других факторов.
            """)
        else:
            st.error("Не выбрано ни одного урока для рефакторинга. Пожалуйста, выберите хотя бы один урок.") 
# pages/admin.py
"""
Страница администрирования конфигурационных параметров для вычисления риска
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import plotly.express as px
import plotly.graph_objects as go

import core
from core_config import get_config, save_config

def page_admin(df: pd.DataFrame):
    """Страница администрирования конфигурации расчета риска"""
    st.title("⚙️ Настройка параметров оценки риска")

    # Получаем текущую конфигурацию
    config = get_config()
    
    # Добавляем чекбокс для включения/отключения минимального порога риска
    use_min_threshold = st.checkbox(
        "Использовать минимальный порог риска для критических метрик",
        value=config["risk_thresholds"].get("use_min_threshold", True),
        key="use_min_threshold",
        help="Если включено, карточки с критичными значениями отдельных метрик всегда будут иметь минимальный уровень риска"
    )
    
    # Сохраняем изменение параметра в конфигурации
    if use_min_threshold != config["risk_thresholds"].get("use_min_threshold", True):
        config["risk_thresholds"]["use_min_threshold"] = use_min_threshold
        save_config(config)
        st.success("Параметр минимального порога риска обновлен!")
        
        # Добавляем кнопку для пересчета данных с новыми параметрами
        if st.button("🔄 Пересчитать данные с новыми параметрами", type="primary"):
            # Очищаем кэш данных для принудительного пересчета
            st.cache_data.clear()
            st.success("Данные будут пересчитаны с новыми параметрами!")
            st.rerun()

    st.markdown("## 📊 Распределение карточек по группам риска")


    # Создаем фильтр программ с множественным выбором
    with st.expander("Фильтр программ", expanded=True):
        # Получаем список программ из датафрейма
        programs = df["program"].unique()
        # Создаем множественный селектор программ
        selected_programs = st.multiselect(
            "Выберите программы для анализа:",
            options=programs,
            default=programs,  # По умолчанию выбраны все программы
            key="risk_programs_filter"
        )
        
        # Если выбраны программы, создаем кнопку для пересчета
        if selected_programs:
            recalculate = st.button("📊 Пересчитать распределение", type="primary")
        else:
            st.warning("Выберите хотя бы одну программу для анализа")
            recalculate = False

    # Если нажата кнопка пересчета или страница загружена впервые
    if recalculate or 'risk_distribution' not in st.session_state:
        # Фильтруем данные по выбранным программам
        if selected_programs:
            filtered_df = df[df["program"].isin(selected_programs)]
        else:
            filtered_df = df
        
        # Создаем метрики и диаграммы только если есть данные
        if not filtered_df.empty:
            # Классифицируем карточки по уровням риска
            risk_categories = {
                "Низкий риск (0-0.25)": (filtered_df["risk"] <= 0.25).sum(),
                "Умеренный риск (0.26-0.50)": ((filtered_df["risk"] > 0.25) & (filtered_df["risk"] <= 0.50)).sum(),
                "Высокий риск (0.51-0.75)": ((filtered_df["risk"] > 0.50) & (filtered_df["risk"] <= 0.75)).sum(),
                "Критический риск (0.76-1.0)": (filtered_df["risk"] > 0.75).sum()
            }
            
            # Создаем DataFrame для диаграммы
            risk_df = pd.DataFrame({
                "Категория": risk_categories.keys(),
                "Количество": risk_categories.values()
            })
            
            # Сохраняем в session_state для инкрементального обновления
            st.session_state['risk_distribution'] = risk_df
            st.session_state['filtered_card_count'] = len(filtered_df)
            st.session_state['selected_programs_count'] = len(selected_programs)
        else:
            st.warning("Нет данных для выбранных программ")
            st.session_state['risk_distribution'] = pd.DataFrame({
                "Категория": ["Низкий риск (0-0.25)", "Умеренный риск (0.26-0.50)", "Высокий риск (0.51-0.75)", "Критический риск (0.76-1.0)"],
                "Количество": [0, 0, 0, 0]
            })
            st.session_state['filtered_card_count'] = 0
            st.session_state['selected_programs_count'] = 0

    # Показываем информацию и диаграммы
    if 'risk_distribution' in st.session_state:
        # Распределение карточек по группам риска
        col1, col2 = st.columns([2, 3])
        
        with col1:
            st.markdown(f"### Распределение риска")
            
            # Метрики для каждой категории
            risk_df = st.session_state['risk_distribution']
            card_count = st.session_state['filtered_card_count']
            programs_count = st.session_state['selected_programs_count']
            
            # Информация о выборке
            st.info(f"Выбрано {programs_count} программ, всего {card_count} карточек")
            
            # Показываем количество и процент для каждой категории
            for i, row in risk_df.iterrows():
                # Определяем цвет для категории
                if "Низкий" in row["Категория"]:
                    color = "green"
                elif "Умеренный" in row["Категория"]:
                    color = "orange"
                elif "Высокий" in row["Категория"]:
                    color = "red"
                else:  # Критический
                    color = "darkred"
                
                # Рассчитываем процент
                percent = (row["Количество"] / card_count * 100) if card_count > 0 else 0
                
                # Показываем метрику с цветом
                st.markdown(f"**{row['Категория']}:** <span style='color:{color};'>{row['Количество']}</span> ({percent:.1f}%)", unsafe_allow_html=True)

            st.sidebar.markdown("---")
            if st.sidebar.button(
                "🔄 Обновить данные с новыми параметрами", 
                type="primary",
                key="refresh_risk_data_sidebar"  # Более уникальный ключ
            ):
                # Очищаем кэш данных, чтобы при следующем обращении данные загрузились заново
                st.cache_data.clear()
                st.success("Кэш очищен. Данные будут пересчитаны с новыми параметрами!")
                st.rerun()

        with col2:
            # Создаем диаграмму с цветами, соответствующими уровням риска
            colors = ["#7FFF7F", "#FFFF7F", "#FFAA7F", "#FF7F7F"]  # зеленый, желтый, оранжевый, красный
            
            # Круговая диаграмма
            fig1 = px.pie(
                risk_df,
                values="Количество",
                names="Категория",
                title="Распределение карточек по группам риска",
                color="Категория",
                color_discrete_map={
                    "Низкий риск (0-0.25)": colors[0],
                    "Умеренный риск (0.26-0.50)": colors[1],
                    "Высокий риск (0.51-0.75)": colors[2],
                    "Критический риск (0.76-1.0)": colors[3]
                },
                hole=0.4
            )
            
            # Настройка подписей
            fig1.update_traces(
                textposition='inside',
                textinfo='percent+label',
                insidetextfont=dict(color='white')
            )
            
            # Отображаем диаграмму
            st.plotly_chart(fig1, use_container_width=True)
        
        # Дополнительная гистограмма распределения риска
        st.markdown("### Гистограмма распределения риска")
        
        # Если есть данные, показываем гистограмму
        if st.session_state['filtered_card_count'] > 0:
            # Фильтруем данные заново для гистограммы
            if selected_programs:
                hist_df = df[df["program"].isin(selected_programs)]
            else:
                hist_df = df
            
            # Создаем гистограмму распределения риска
            fig2 = px.histogram(
                hist_df,
                x="risk",
                nbins=40,
                title="Распределение карточек по значению риска",
                color_discrete_sequence=["#FF9F7F"],
                labels={"risk": "Риск", "count": "Количество карточек"}
            )
            
            # Добавляем вертикальные линии для границ риска
            fig2.add_vline(x=0.25, line_dash="dash", line_color="green", 
                        annotation_text="Низкий", annotation_position="top")
            fig2.add_vline(x=0.50, line_dash="dash", line_color="orange", 
                        annotation_text="Умеренный", annotation_position="top")
            fig2.add_vline(x=0.75, line_dash="dash", line_color="red", 
                        annotation_text="Высокий", annotation_position="top")
            
            # Настройка макета
            fig2.update_layout(
                xaxis_title="Значение риска",
                yaxis_title="Количество карточек",
                bargap=0.2
            )
            
            # Отображаем гистограмму
            st.plotly_chart(fig2, use_container_width=True)
        
        # Добавляем разделитель
        st.markdown("---")
    
    # Путь к файлу конфигурации
    config_path = "risk_config.json"
    
    # Загрузка конфигурации из текущих значений через get_config()
    config = get_config()
    
    st.markdown("""
    Эта страница позволяет настраивать параметры для вычисления риска карточек.
    Изменения будут сохранены в файл и применены при следующем запуске приложения.
    
    Вы можете протестировать влияние изменений параметров на примере конкретных карточек в разделе "Тестирование конфигурации".
    """)
    
    tabs = st.tabs([
        "📊 Метрики дискриминативности", 
        "✅ Метрики успешности", 
        "⚠️ Метрики жалоб",
        "🔄 Настройки весов", 
        "🎯 Трики-карточки",  # Новая вкладка
        "📈 Тестирование"
    ])
    
    # Вкладка дискриминативности
    with tabs[0]:
        st.subheader("Настройка параметров дискриминативности")
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("### Пороги дискриминативности")
            
            # Интерфейс для редактирования порогов дискриминативности
            discrimination_good = st.slider(
                "Хорошая дискриминативность (выше этого значения)",
                min_value=0.0,
                max_value=1.0,
                value=float(config["discrimination"]["good"]),
                step=0.01,
                format="%.2f",
                key="discrimination_good"
            )
            
            discrimination_medium = st.slider(
                "Средняя дискриминативность (выше этого значения)",
                min_value=0.0,
                max_value=discrimination_good,
                value=min(float(config["discrimination"]["medium"]), discrimination_good),
                step=0.01,
                format="%.2f",
                key="discrimination_medium"
            )
            
            # Обновляем конфигурацию
            config["discrimination"]["good"] = discrimination_good
            config["discrimination"]["medium"] = discrimination_medium
            
            st.markdown("""
            ### Интерпретация параметров:
            - **Хорошая**: > {:.2f} → Риск 0-0.25
            - **Средняя**: {:.2f}-{:.2f} → Риск 0.26-0.50
            - **Низкая**: < {:.2f} → Риск 0.51-1.0
            """.format(
                discrimination_good, 
                discrimination_medium,
                discrimination_good,
                discrimination_medium
            ))
        
        with col2:
            # Визуализация границ дискриминативности
            x = np.linspace(0, 1, 100)
            y = []
            
            for val in x:
                if val >= discrimination_good:
                    # Хорошая дискриминативность (0-0.25)
                    normalized = min(1.0, (val - discrimination_good) / 0.4)
                    y.append(max(0, 0.25 * (1 - normalized)))
                elif val >= discrimination_medium:
                    # Средняя дискриминативность (0.26-0.50)
                    normalized = (val - discrimination_medium) / (discrimination_good - discrimination_medium)
                    y.append(0.50 - normalized * 0.24)
                else:
                    # Низкая дискриминативность (0.51-1.0)
                    normalized = max(0, val / discrimination_medium)
                    y.append(1.0 - normalized * 0.49)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x, 
                y=y, 
                mode='lines', 
                name='Риск',
                line=dict(width=2, color='red')
            ))
            
            # Добавляем вертикальные линии для границ
            fig.add_vline(x=discrimination_medium, line_dash="dash", line_color="orange", 
                         annotation_text="Средняя", annotation_position="top")
            fig.add_vline(x=discrimination_good, line_dash="dash", line_color="green", 
                         annotation_text="Хорошая", annotation_position="top")
            
            # Добавляем горизонтальные линии для уровней риска
            fig.add_hline(y=0.25, line_dash="dash", line_color="green", 
                         annotation_text="Низкий риск", annotation_position="left")
            fig.add_hline(y=0.50, line_dash="dash", line_color="orange", 
                         annotation_text="Умеренный риск", annotation_position="left")
            fig.add_hline(y=0.75, line_dash="dash", line_color="red", 
                         annotation_text="Высокий риск", annotation_position="left")
            
            fig.update_layout(
                title="График риска в зависимости от дискриминативности",
                xaxis_title="Дискриминативность",
                yaxis_title="Риск",
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Вкладка успешности
    with tabs[1]:
        st.subheader("Настройка параметров успешности")
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("### Пороги успешности")
            
            # Интерфейс для редактирования порогов успешности
            success_boring = st.slider(
                "Скучная успешность (выше этого значения)",
                min_value=0.8,
                max_value=1.0,
                value=float(config["success_rate"]["boring"]),
                step=0.01,
                format="%.2f",
                key="success_boring"
            )
            
            success_optimal_high = min(success_boring, float(config["success_rate"]["optimal_high"]))
            
            success_optimal_low = st.slider(
                "Нижняя граница оптимальной успешности",
                min_value=0.5,
                max_value=success_boring,
                value=min(float(config["success_rate"]["optimal_low"]), success_boring),
                step=0.01,
                format="%.2f",
                key="success_optimal_low"
            )
            
            success_suboptimal_low = st.slider(
                "Нижняя граница субоптимальной успешности",
                min_value=0.2,
                max_value=success_optimal_low,
                value=min(float(config["success_rate"]["suboptimal_low"]), success_optimal_low),
                step=0.01,
                format="%.2f",
                key="success_suboptimal_low"
            )
            
            # Обновляем конфигурацию
            config["success_rate"]["boring"] = success_boring
            config["success_rate"]["optimal_high"] = success_boring  # Верхняя граница = boring
            config["success_rate"]["optimal_low"] = success_optimal_low
            config["success_rate"]["suboptimal_low"] = success_suboptimal_low
            
            st.markdown("""
            ### Первая попытка
            """)
            
            # Интерфейс для редактирования порогов успешности с первой попытки
            first_try_too_easy = st.slider(
                "Слишком простая задача (выше этого значения)",
                min_value=0.8,
                max_value=1.0,
                value=float(config["first_try"]["too_easy"]),
                step=0.01,
                format="%.2f",
                key="first_try_too_easy"
            )
            
            first_try_optimal_low = st.slider(
                "Нижняя граница оптимальной успешности с первой попытки",
                min_value=0.4,
                max_value=first_try_too_easy,
                value=min(float(config["first_try"]["optimal_low"]), first_try_too_easy),
                step=0.01,
                format="%.2f",
                key="first_try_optimal_low"
            )
            
            first_try_multiple_low = st.slider(
                "Нижняя граница требующей нескольких попыток",
                min_value=0.1,
                max_value=first_try_optimal_low,
                value=min(float(config["first_try"]["multiple_low"]), first_try_optimal_low),
                step=0.01,
                format="%.2f",
                key="first_try_multiple_low"
            )
            
            # Обновляем конфигурацию
            config["first_try"]["too_easy"] = first_try_too_easy
            config["first_try"]["optimal_low"] = first_try_optimal_low
            config["first_try"]["multiple_low"] = first_try_multiple_low
            
            st.markdown("""
            ### Интерпретация параметров успешности:
            - **Скучная**: > {:.2f} → Риск 0.30-0.40
            - **Оптимальная**: {:.2f}-{:.2f} → Риск 0-0.25
            - **Субоптимальная**: {:.2f}-{:.2f} → Риск 0.26-0.50
            - **Фрустрирующая**: < {:.2f} → Риск 0.51-1.0
            
            ### Интерпретация параметров успешности с первой попытки:
            - **Слишком простая**: > {:.2f} → Риск 0.26-0.35
            - **Оптимальная**: {:.2f}-{:.2f} → Риск 0-0.25
            - **Требует нескольких попыток**: {:.2f}-{:.2f} → Риск 0.26-0.50
            - **Сложная**: < {:.2f} → Риск 0.51-1.0
            """.format(
                success_boring,
                success_optimal_low, success_boring,
                success_suboptimal_low, success_optimal_low,
                success_suboptimal_low,
                first_try_too_easy,
                first_try_optimal_low, first_try_too_easy,
                first_try_multiple_low, first_try_optimal_low,
                first_try_multiple_low
            ))
        
        with col2:
            # Визуализация границ успешности
            st.markdown("### График риска для успешности")
            
            x = np.linspace(0, 1, 100)
            success_y = []
            
            for val in x:
                if val > success_boring:
                    # Скучная (слишком простая) задача (0.30-0.40)
                    normalized = min(1.0, (val - success_boring) / 0.05)
                    success_y.append(0.30 + normalized * 0.10)
                elif val >= success_optimal_low:
                    # Оптимальная успешность (0-0.25)
                    normalized = (val - success_optimal_low) / (success_boring - success_optimal_low)
                    success_y.append(0.25 * (1 - normalized))
                elif val >= success_suboptimal_low:
                    # Субоптимальная успешность (0.26-0.50)
                    normalized = (val - success_suboptimal_low) / (success_optimal_low - success_suboptimal_low)
                    success_y.append(0.50 - normalized * 0.24)
                else:
                    # Фрустрирующая успешность (0.51-1.0)
                    normalized = max(0, val / success_suboptimal_low)
                    success_y.append(1.0 - normalized * 0.49)
            
            fig_success = go.Figure()
            fig_success.add_trace(go.Scatter(
                x=x, 
                y=success_y, 
                mode='lines', 
                name='Риск',
                line=dict(width=2, color='blue')
            ))
            
            # Добавляем вертикальные линии для границ
            fig_success.add_vline(x=success_suboptimal_low, line_dash="dash", line_color="red", 
                                 annotation_text="Фрустр.", annotation_position="top")
            fig_success.add_vline(x=success_optimal_low, line_dash="dash", line_color="orange", 
                                 annotation_text="Субопт.", annotation_position="top")
            fig_success.add_vline(x=success_boring, line_dash="dash", line_color="green", 
                                 annotation_text="Оптим.", annotation_position="top")
            
            # Добавляем горизонтальные линии для уровней риска
            fig_success.add_hline(y=0.25, line_dash="dash", line_color="green", 
                                 annotation_text="Низкий риск", annotation_position="left")
            fig_success.add_hline(y=0.50, line_dash="dash", line_color="orange", 
                                 annotation_text="Умеренный риск", annotation_position="left")
            fig_success.add_hline(y=0.75, line_dash="dash", line_color="red", 
                                 annotation_text="Высокий риск", annotation_position="left")
            
            fig_success.update_layout(
                title="График риска в зависимости от успешности",
                xaxis_title="Успешность",
                yaxis_title="Риск",
                height=300
            )
            
            st.plotly_chart(fig_success, use_container_width=True)
            
            # Визуализация границ успешности с первой попытки
            st.markdown("### График риска для успешности с первой попытки")
            
            first_try_y = []
            
            for val in x:
                if val > first_try_too_easy:
                    # Слишком простая задача (0.26-0.35)
                    normalized = min(1.0, (val - first_try_too_easy) / 0.1)
                    first_try_y.append(0.26 + normalized * 0.09)
                elif val >= first_try_optimal_low:
                    # Оптимальная успешность с первой попытки (0-0.25)
                    normalized = (val - first_try_optimal_low) / (first_try_too_easy - first_try_optimal_low)
                    first_try_y.append(0.25 * (1 - normalized))
                elif val >= first_try_multiple_low:
                    # Требует нескольких попыток (0.26-0.50)
                    normalized = (val - first_try_multiple_low) / (first_try_optimal_low - first_try_multiple_low)
                    first_try_y.append(0.50 - normalized * 0.24)
                else:
                    # Сложная задача (0.51-1.0)
                    normalized = max(0, val / first_try_multiple_low)
                    first_try_y.append(1.0 - normalized * 0.49)
            
            fig_first_try = go.Figure()
            fig_first_try.add_trace(go.Scatter(
                x=x, 
                y=first_try_y, 
                mode='lines', 
                name='Риск',
                line=dict(width=2, color='green')
            ))
            
            # Добавляем вертикальные линии для границ
            fig_first_try.add_vline(x=first_try_multiple_low, line_dash="dash", line_color="red", 
                                   annotation_text="Сложная", annotation_position="top")
            fig_first_try.add_vline(x=first_try_optimal_low, line_dash="dash", line_color="orange", 
                                   annotation_text="Неск. попыток", annotation_position="top")
            fig_first_try.add_vline(x=first_try_too_easy, line_dash="dash", line_color="green", 
                                   annotation_text="Оптим.", annotation_position="top")
            
            # Добавляем горизонтальные линии для уровней риска
            fig_first_try.add_hline(y=0.25, line_dash="dash", line_color="green", 
                                   annotation_text="Низкий риск", annotation_position="left")
            fig_first_try.add_hline(y=0.50, line_dash="dash", line_color="orange", 
                                   annotation_text="Умеренный риск", annotation_position="left")
            fig_first_try.add_hline(y=0.75, line_dash="dash", line_color="red", 
                                   annotation_text="Высокий риск", annotation_position="left")
            
            fig_first_try.update_layout(
                title="График риска в зависимости от успешности с первой попытки",
                xaxis_title="Успешность с первой попытки",
                yaxis_title="Риск",
                height=300
            )
            
            st.plotly_chart(fig_first_try, use_container_width=True)
    
    # Вкладка жалоб и попыток
    with tabs[2]:
        st.subheader("Настройка параметров жалоб и попыток")
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("### Пороги жалоб (абсолютные значения)")
            
            # Интерфейс для редактирования порогов жалоб
            complaints_critical = st.number_input(
                "Критический уровень жалоб (выше этого значения)",
                min_value=1,
                max_value=1000,
                value=int(config["complaints"]["critical"]),
                step=1,
                key="complaints_critical"
            )
            
            complaints_high = st.number_input(
                "Высокий уровень жалоб (выше этого значения)",
                min_value=1,
                max_value=complaints_critical-1,
                value=min(int(config["complaints"]["high"]), complaints_critical-1),
                step=1,
                key="complaints_high"
            )
            
            complaints_medium = st.number_input(
                "Средний уровень жалоб (выше этого значения)",
                min_value=0,
                max_value=complaints_high-1,
                value=min(int(config["complaints"]["medium"]), complaints_high-1),
                step=1,
                key="complaints_medium"
            )
            
            # Обновляем конфигурацию
            config["complaints"]["critical"] = complaints_critical
            config["complaints"]["high"] = complaints_high
            config["complaints"]["medium"] = complaints_medium
            
            st.markdown("### Пороги доли пытавшихся решить")
            
            # Интерфейс для редактирования порогов доли пытавшихся решить
            attempts_high = st.slider(
                "Высокая доля пытавшихся (выше этого значения)",
                min_value=0.8,
                max_value=1.0,
                value=float(config["attempts"]["high"]),
                step=0.01,
                format="%.2f",
                key="attempts_high"
            )
            
            attempts_normal_low = st.slider(
                "Нижняя граница нормальной доли пытавшихся",
                min_value=0.6,
                max_value=attempts_high,
                value=min(float(config["attempts"]["normal_low"]), attempts_high),
                step=0.01,
                format="%.2f",
                key="attempts_normal_low"
            )
            
            attempts_insufficient_low = st.slider(
                "Нижняя граница недостаточной доли пытавшихся",
                min_value=0.2,
                max_value=attempts_normal_low,
                value=min(float(config["attempts"]["insufficient_low"]), attempts_normal_low),
                step=0.01,
                format="%.2f",
                key="attempts_insufficient_low"
            )
            
            # Обновляем конфигурацию
            config["attempts"]["high"] = attempts_high
            config["attempts"]["normal_low"] = attempts_normal_low
            config["attempts"]["insufficient_low"] = attempts_insufficient_low
            
            st.markdown("""
            ### Интерпретация параметров жалоб:
            - **Критическое**: > {} → Риск 0.76-1.0
            - **Высокое**: {}-{} → Риск 0.51-0.75
            - **Среднее**: {}-{} → Риск 0.26-0.50
            - **Низкое**: < {} → Риск 0-0.25
            
            ### Интерпретация параметров доли пытавшихся:
            - **Высокая**: > {:.2f} → Риск 0-0.10
            - **Нормальная**: {:.2f}-{:.2f} → Риск 0-0.25
            - **Недостаточная**: {:.2f}-{:.2f} → Риск 0.26-0.50
            - **Игнорируемая**: < {:.2f} → Риск 0.51-1.0
            """.format(
                complaints_critical,
                complaints_high, complaints_critical,
                complaints_medium, complaints_high,
                complaints_medium,
                attempts_high,
                attempts_normal_low, attempts_high,
                attempts_insufficient_low, attempts_normal_low,
                attempts_insufficient_low
            ))
        
        with col2:
            # Визуализация границ жалоб
            st.markdown("### График риска для количества жалоб")
            
            # Создаем массив значений для жалоб
            complaints_x = np.linspace(0, int(complaints_critical * 1.5), 100)
            complaints_y = []
            
            for val in complaints_x:
                if val > complaints_critical:
                    # Критический уровень жалоб (0.76-1.0)
                    excess = min(100, val - complaints_critical)
                    normalized = excess / 100
                    complaints_y.append(0.76 + normalized * 0.24)
                elif val >= complaints_high:
                    # Высокий уровень жалоб (0.51-0.75)
                    normalized = (val - complaints_high) / (complaints_critical - complaints_high)
                    complaints_y.append(0.51 + normalized * 0.24)
                elif val >= complaints_medium:
                    # Средний уровень жалоб (0.26-0.50)
                    normalized = (val - complaints_medium) / (complaints_high - complaints_medium)
                    complaints_y.append(0.26 + normalized * 0.24)
                else:
                    # Низкий уровень жалоб (0-0.25)
                    normalized = val / max(1, complaints_medium)
                    complaints_y.append(normalized * 0.25)
            
            fig_complaints = go.Figure()
            fig_complaints.add_trace(go.Scatter(
                x=complaints_x, 
                y=complaints_y, 
                mode='lines', 
                name='Риск',
                line=dict(width=2, color='red')
            ))
            
            # Добавляем вертикальные линии для границ
            fig_complaints.add_vline(x=complaints_medium, line_dash="dash", line_color="green", 
                                    annotation_text="Средний", annotation_position="top")
            fig_complaints.add_vline(x=complaints_high, line_dash="dash", line_color="orange", 
                                    annotation_text="Высокий", annotation_position="top")
            fig_complaints.add_vline(x=complaints_critical, line_dash="dash", line_color="red", 
                                    annotation_text="Критический", annotation_position="top")
            
            # Добавляем горизонтальные линии для уровней риска
            fig_complaints.add_hline(y=0.25, line_dash="dash", line_color="green", 
                                    annotation_text="Низкий риск", annotation_position="left")
            fig_complaints.add_hline(y=0.50, line_dash="dash", line_color="orange", 
                                    annotation_text="Умеренный риск", annotation_position="left")
            fig_complaints.add_hline(y=0.75, line_dash="dash", line_color="red", 
                                    annotation_text="Высокий риск", annotation_position="left")
            
            fig_complaints.update_layout(
                title="График риска в зависимости от количества жалоб",
                xaxis_title="Количество жалоб",
                yaxis_title="Риск",
                height=300
            )
            
            st.plotly_chart(fig_complaints, use_container_width=True)
            
            # Визуализация границ доли пытавшихся
            st.markdown("### График риска для доли пытавшихся")
            
            x = np.linspace(0, 1, 100)
            attempts_y = []
            
            for val in x:
                if val > attempts_high:
                    # Высокая доля пытавшихся (0-0.10)
                    normalized = min(1.0, (val - attempts_high) / 0.05)
                    attempts_y.append(0.10 * (1 - normalized))
                elif val >= attempts_normal_low:
                    # Нормальная доля пытавшихся (0-0.25)
                    normalized = (val - attempts_normal_low) / (attempts_high - attempts_normal_low)
                    attempts_y.append(0.25 - normalized * 0.15)
                elif val >= attempts_insufficient_low:
                    # Недостаточная доля пытавшихся (0.26-0.50)
                    normalized = (val - attempts_insufficient_low) / (attempts_normal_low - attempts_insufficient_low)
                    attempts_y.append(0.50 - normalized * 0.24)
                else:
                    # Игнорируемая доля пытавшихся (0.51-1.0)
                    normalized = max(0, val / attempts_insufficient_low)
                    attempts_y.append(1.0 - normalized * 0.49)
            
            fig_attempts = go.Figure()
            fig_attempts.add_trace(go.Scatter(
                x=x, 
                y=attempts_y, 
                mode='lines', 
                name='Риск',
                line=dict(width=2, color='purple')
            ))
            
            # Добавляем вертикальные линии для границ
            fig_attempts.add_vline(x=attempts_insufficient_low, line_dash="dash", line_color="red", 
                                  annotation_text="Игнорир.", annotation_position="top")
            fig_attempts.add_vline(x=attempts_normal_low, line_dash="dash", line_color="orange", 
                                  annotation_text="Недост.", annotation_position="top")
            fig_attempts.add_vline(x=attempts_high, line_dash="dash", line_color="green", 
                                  annotation_text="Норм.", annotation_position="top")
            
            # Добавляем горизонтальные линии для уровней риска
            fig_attempts.add_hline(y=0.25, line_dash="dash", line_color="green", 
                                  annotation_text="Низкий риск", annotation_position="left")
            fig_attempts.add_hline(y=0.50, line_dash="dash", line_color="orange", 
                                  annotation_text="Умеренный риск", annotation_position="left")
            fig_attempts.add_hline(y=0.75, line_dash="dash", line_color="red", 
                                  annotation_text="Высокий риск", annotation_position="left")
            
            fig_attempts.update_layout(
                title="График риска в зависимости от доли пытавшихся",
                xaxis_title="Доля пытавшихся",
                yaxis_title="Риск",
                height=300
            )
            
            st.plotly_chart(fig_attempts, use_container_width=True)
    
    # Вкладка весов и настроек комбинирования
    with tabs[3]:
        st.subheader("Настройка весов метрик и параметров комбинирования риска")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Веса для метрик")
            
            # Слайдеры весов с синхронизацией суммы 1.0
            current_sum = sum([
                config["weights"]["complaint_rate"],
                config["weights"]["success_rate"],
                config["weights"]["discrimination"],
                config["weights"]["first_try"],
                config["weights"]["attempted"]
            ])
            
            complaint_weight = st.slider(
                "Вес жалоб",
                min_value=0.05,
                max_value=0.5,
                value=float(config["weights"]["complaint_rate"]),
                step=0.05,
                format="%.2f",
                key="complaint_weight"
            )
            
            success_weight = st.slider(
                "Вес успешности",
                min_value=0.05,
                max_value=0.5,
                value=float(config["weights"]["success_rate"]),
                step=0.05,
                format="%.2f",
                key="success_weight"
            )
            
            discrimination_weight = st.slider(
                "Вес дискриминативности",
                min_value=0.05,
                max_value=0.5,
                value=float(config["weights"]["discrimination"]),
                step=0.05,
                format="%.2f",
                key="discrimination_weight"
            )
            
            first_try_weight = st.slider(
                "Вес успешности с первой попытки",
                min_value=0.05,
                max_value=0.5,
                value=float(config["weights"]["first_try"]),
                step=0.05,
                format="%.2f",
                key="first_try_weight"
            )
            
            attempted_weight = st.slider(
                "Вес доли пытавшихся",
                min_value=0.05,
                max_value=0.5,
                value=float(config["weights"]["attempted"]),
                step=0.05,
                format="%.2f",
                key="attempted_weight"
            )
            
            # Проверяем сумму весов и нормализуем при необходимости
            new_sum = complaint_weight + success_weight + discrimination_weight + first_try_weight + attempted_weight
            
            if abs(new_sum - 1.0) > 0.01:
                st.warning(f"Сумма весов должна быть равна 1.0. Текущая сумма: {new_sum:.2f}")
                
                # Предлагаем нормализовать веса
                if st.button("Нормализовать веса"):
                    scale = 1.0 / new_sum
                    complaint_weight *= scale
                    success_weight *= scale
                    discrimination_weight *= scale
                    first_try_weight *= scale
                    attempted_weight *= scale
                    st.success("Веса нормализованы!")
            
            # Обновляем конфигурацию весов
            config["weights"]["complaint_rate"] = complaint_weight
            config["weights"]["success_rate"] = success_weight
            config["weights"]["discrimination"] = discrimination_weight
            config["weights"]["first_try"] = first_try_weight
            config["weights"]["attempted"] = attempted_weight
            
            # Визуализация весов в виде круговой диаграммы
            weights_df = pd.DataFrame({
                "Метрика": ["Жалобы", "Успешность", "Дискриминативность", "Первая попытка", "Доля пытавшихся"],
                "Вес": [complaint_weight, success_weight, discrimination_weight, first_try_weight, attempted_weight]
            })
            
            fig_weights = px.pie(
                weights_df, 
                values='Вес', 
                names='Метрика', 
                title='Распределение весов метрик',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            
            st.plotly_chart(fig_weights, use_container_width=True)
        
        with col2:
            st.markdown("### Параметры комбинирования риска")
            
            # Интерфейс для редактирования параметров комбинирования
            alpha_weight_avg = st.slider(
                "Вес взвешенного среднего в комбинированной формуле",
                min_value=0.0,
                max_value=1.0,
                value=float(config["risk_thresholds"]["alpha_weight_avg"]),
                step=0.05,
                format="%.2f",
                key="alpha_weight_avg",
                help="При значении 1.0 используется только взвешенное среднее, при 0.0 - только максимальный риск"
            )
            
            risk_critical_threshold = st.slider(
                "Порог критического риска",
                min_value=0.5,
                max_value=0.95,
                value=float(config["risk_thresholds"]["critical"]),
                step=0.05,
                format="%.2f",
                key="risk_critical_threshold",
                help="Значение риска выше этого порога считается критическим"
            )
            
            risk_high_threshold = st.slider(
                "Порог высокого риска",
                min_value=0.25,
                max_value=risk_critical_threshold - 0.05,
                value=min(float(config["risk_thresholds"]["high"]), risk_critical_threshold - 0.05),
                step=0.05,
                format="%.2f",
                key="risk_high_threshold",
                help="Значение риска выше этого порога считается высоким"
            )
            
            min_risk_for_critical = st.slider(
                "Минимальный порог риска при наличии критической метрики",
                min_value=0.5,
                max_value=risk_critical_threshold,
                value=min(float(config["risk_thresholds"]["min_for_critical"]), risk_critical_threshold),
                step=0.05,
                format="%.2f",
                key="min_risk_for_critical"
            )
            
            min_risk_for_high = st.slider(
                "Минимальный порог риска при наличии высокой риск-метрики",
                min_value=0.25,
                max_value=min_risk_for_critical - 0.05,
                value=min(float(config["risk_thresholds"]["min_for_high"]), min_risk_for_critical - 0.05),
                step=0.05,
                format="%.2f",
                key="min_risk_for_high"
            )
            
            # Обновляем конфигурацию пороговых значений
            config["risk_thresholds"]["alpha_weight_avg"] = alpha_weight_avg
            config["risk_thresholds"]["critical"] = risk_critical_threshold
            config["risk_thresholds"]["high"] = risk_high_threshold
            config["risk_thresholds"]["min_for_critical"] = min_risk_for_critical
            config["risk_thresholds"]["min_for_high"] = min_risk_for_high
            
            st.markdown("### Параметры статистической значимости")
            
            significance_threshold = st.number_input(
                "Количество попыток для полной статистической значимости",
                min_value=10,
                max_value=1000,
                value=int(config["stats"]["significance_threshold"]),
                step=10,
                key="significance_threshold"
            )
            
            neutral_risk_value = st.slider(
                "Значение риска к которому смещаемся при малом числе попыток",
                min_value=0.25,
                max_value=0.75,
                value=float(config["stats"]["neutral_risk_value"]),
                step=0.05,
                format="%.2f",
                key="neutral_risk_value"
            )
            
            # Обновляем конфигурацию статистической значимости
            config["stats"]["significance_threshold"] = significance_threshold
            config["stats"]["neutral_risk_value"] = neutral_risk_value
            
            # Визуализация статистической значимости
            st.markdown("### Влияние количества попыток на корректировку риска")
            
            attempts_x = np.linspace(0, significance_threshold * 1.5, 100)
            confidence_y = []
            
            for val in attempts_x:
                confidence_factor = min(val / significance_threshold, 1.0)
                confidence_y.append(confidence_factor)
            
            fig_confidence = go.Figure()
            fig_confidence.add_trace(go.Scatter(
                x=attempts_x, 
                y=confidence_y, 
                mode='lines', 
                name='Коэффициент доверия',
                line=dict(width=2, color='blue')
            ))
            
            # Добавляем вертикальную линию для порога
            fig_confidence.add_vline(x=significance_threshold, line_dash="dash", line_color="red", 
                                    annotation_text="Полная значимость", annotation_position="top")
            
            fig_confidence.update_layout(
                title="Коэффициент доверия в зависимости от количества попыток",
                xaxis_title="Количество попыток",
                yaxis_title="Коэффициент доверия",
                height=250
            )
            
            st.plotly_chart(fig_confidence, use_container_width=True)
    
    # Вкладка анализа "трики"-карточек
    with tabs[4]:  # Индекс 4 соответствует добавленной вкладке
        st.subheader("Анализ \"трики\"-карточек")
        
        st.markdown("""
        ## Что такое "трики"-карточки?
        
        **"Трики"-карточки** - это задания, которые обладают следующими характеристиками:
        - **Высокий процент общей успешности** - большинство студентов в итоге решают задание
        - **Низкий процент успеха с первой попытки** - студентам требуется несколько попыток для решения
        - Большая **разница** между общей успешностью и успешностью с первой попытки
        - Часто сопровождаются повышенным количеством **жалоб** из-за неочевидности или "подвоха" в задании
        
        Эти карточки могут быть полезны для обучения, но требуют внимательного рассмотрения.
        """)

        # Настройка параметров для определения "трики"-карточек
        st.sidebar.markdown("### Параметры \"трики\"-карточек")
        
        min_success_rate = st.sidebar.slider(
            "Минимальная общая успешность",
            min_value=0.50,
            max_value=1.0,
            value=0.75,
            step=0.05,
            format="%.2f",
            help="Минимальный процент общей успешности для отнесения к трики-карточкам"
        )
        
        max_first_try_rate = st.sidebar.slider(
            "Максимальная успешность с 1-й попытки",
            min_value=0.0,
            max_value=0.75,
            value=0.50,
            step=0.05,
            format="%.2f",
            help="Максимальный процент успеха с первой попытки для отнесения к трики-карточкам"
        )
        
        min_difference = st.sidebar.slider(
            "Минимальная разница успешности",
            min_value=0.05,
            max_value=0.50,
            value=0.25,
            step=0.05,
            format="%.2f",
            help="Минимальная разница между общей успешностью и успехом с первой попытки"
        )
        
        # Подготовка данных для анализа
        # Используем только параметры успешности и первой попытки, без учета жалоб для упрощения
        
        # Копируем данные для обработки
        working_df = df.copy()
        
        # Добавляем разницу между общей успешностью и успехом с первой попытки
        working_df["success_diff"] = working_df["success_rate"] - working_df["first_try_success_rate"]
        
        # Определяем "трики"-карточки на основе параметров
        working_df["is_tricky"] = (
            (working_df["success_rate"] >= min_success_rate) & 
            (working_df["first_try_success_rate"] <= max_first_try_rate) &
            (working_df["success_diff"] >= min_difference)
        )
        
        # Категория для легенды
        working_df["category"] = working_df["is_tricky"].map({True: "Трики-карточки", False: "Обычные карточки"})
        
        # Подсчет статистики
        total_cards = len(working_df)
        tricky_cards = working_df["is_tricky"].sum()
        tricky_percent = tricky_cards / total_cards if total_cards > 0 else 0
        
        # Отображение статистики
        st.markdown(f"### Статистика \"трики\"-карточек")
        st.markdown(f"Найдено **{tricky_cards}** \"трики\"-карточек из **{total_cards}** карточек (**{tricky_percent:.1%}**)")
        
        # Создаем точечную диаграмму
        st.markdown(f"### Карта успешности карточек")
        
        fig = px.scatter(
            working_df,
            x="success_rate",
            y="first_try_success_rate",
            color="category",
            hover_data=["card_id", "card_type", "success_rate", "first_try_success_rate", "complaint_rate", "program", "module", "lesson"],
            labels={
                "success_rate": "Общая успешность", 
                "first_try_success_rate": "Успешность с первой попытки",
                "category": "Категория карточек"
            },
            color_discrete_map={"Трики-карточки": "red", "Обычные карточки": "blue"},
            opacity=0.7,
            title="Распределение карточек по успешности и успешности с первой попытки"
        )
        
        # Добавляем диагональную линию равенства
        fig.add_trace(
            go.Scatter(
                x=[0, 1],
                y=[0, 1],
                mode="lines",
                line=dict(color="gray", dash="dash", width=1),
                name="Успешность = Успешность с 1-й попытки",
                hoverinfo="skip"
            )
        )
        
        # Добавляем диагональную линию минимальной разницы
        x_values = np.linspace(min_success_rate, 1, 100)
        y_values = [min(x - min_difference, max_first_try_rate) for x in x_values]
        
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode="lines",
                line=dict(color="purple", dash="dot", width=1),
                name=f"Минимальная разница: {min_difference:.2f}",
                hoverinfo="skip"
            )
        )
        
        # Создаем зону "трики"-карточек
        # Используем полупрозрачную заливку для обозначения зоны
        fig.add_shape(
            type="rect",
            x0=min_success_rate,
            y0=0,
            x1=1,
            y1=max_first_try_rate,
            fillcolor="rgba(255,0,0,0.1)",
            line=dict(color="red", width=1, dash="dash"),
            layer="below",
            name="Зона трики-карточек"
        )
        
        # Добавляем вертикальную линию минимальной успешности
        fig.add_vline(
            x=min_success_rate, 
            line_dash="dash", 
            line_color="green", 
            line_width=1,
            annotation_text=f"Мин. успешность: {min_success_rate:.2f}",
            annotation_position="top"
        )
        
        # Добавляем горизонтальную линию максимальной успешности с первой попытки
        fig.add_hline(
            y=max_first_try_rate, 
            line_dash="dash", 
            line_color="red", 
            line_width=1,
            annotation_text=f"Макс. успешность с 1-й попытки: {max_first_try_rate:.2f}",
            annotation_position="left"
        )
        
        # Добавляем аннотацию для зоны "трики"-карточек
        fig.add_annotation(
            x=(min_success_rate + 1) / 2,
            y=max_first_try_rate / 2,
            text="Зона 'трики'-карточек",
            showarrow=False,
            font=dict(color="red", size=14),
            bgcolor="rgba(255,255,255,0.7)",
            bordercolor="red",
            borderwidth=1,
            borderpad=4
        )
        
        # Настройка макета
        fig.update_layout(
            xaxis=dict(
                title="Общая успешность",
                range=[0, 1],
                tickformat=".0%"
            ),
            yaxis=dict(
                title="Успешность с первой попытки",
                range=[0, 1],
                tickformat=".0%"
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=600  # Увеличиваем высоту графика
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Отображение таблицы с трики-карточками
        if tricky_cards > 0:
            st.markdown("### Список \"трики\"-карточек")
            
            # Фильтруем только трики-карточки
            tricky_df = working_df[working_df["is_tricky"]].sort_values("success_diff", ascending=False)
            
            # Показываем только основные колонки
            display_columns = [
                "card_id", "card_type", "program", "module", "lesson", 
                "success_rate", "first_try_success_rate", "success_diff", "complaint_rate"
            ]
            
            # Проверяем наличие URL-колонки
            if "card_url" in tricky_df.columns:
                # Создаем DataFrame для отображения с кликабельными ссылками
                display_df = pd.DataFrame()
                display_df["ID карточки"] = tricky_df.apply(
                    lambda row: f"[{int(row['card_id'])}]({row['card_url']})" if pd.notna(row['card_url']) else str(int(row['card_id'])),
                    axis=1
                )
                display_df["Тип"] = tricky_df["card_type"]
                display_df["Общая успешность"] = tricky_df["success_rate"].apply(lambda x: f"{x:.1%}")
                display_df["Успех с 1-й попытки"] = tricky_df["first_try_success_rate"].apply(lambda x: f"{x:.1%}")
                display_df["Разница"] = tricky_df["success_diff"].apply(lambda x: f"{x:.1%}")
                display_df["Жалобы"] = tricky_df["complaint_rate"].apply(lambda x: f"{x:.1%}")
                display_df["Программа"] = tricky_df["program"]
                
                # Отображаем с кликабельными ссылками
                st.dataframe(display_df, hide_index=True, use_container_width=True)
            else:
                # Отображаем обычную таблицу
                st.dataframe(
                    tricky_df[display_columns].style.format({
                        "success_rate": "{:.1%}",
                        "first_try_success_rate": "{:.1%}",
                        "success_diff": "{:.1%}",
                        "complaint_rate": "{:.1%}"
                    }),
                    use_container_width=True
                )
    # Вкладка тестирования
    with tabs[5]:
        st.subheader("Тестирование конфигурации на примере карточек")
        
        # Выбор карточек для тестирования
        if not df.empty:
            # Отбираем карточки с высоким риском для тестирования
            high_risk_cards = df[df["risk"] > 0.5].sort_values(by="risk", ascending=False).head(50)
            
            # Добавляем карточки со средним и низким риском
            medium_risk_cards = df[(df["risk"] <= 0.5) & (df["risk"] > 0.25)].sample(min(20, len(df[(df["risk"] <= 0.5) & (df["risk"] > 0.25)])))
            low_risk_cards = df[df["risk"] <= 0.25].sample(min(10, len(df[df["risk"] <= 0.25])))
            
            # Объединяем карточки
            test_cards = pd.concat([high_risk_cards, medium_risk_cards, low_risk_cards])
            
            # Создаем селектор для выбора карточки
            selected_card_id = st.selectbox(
                "Выберите карточку для тестирования",
                options=test_cards["card_id"].values,
                format_func=lambda x: f"ID: {x} - Риск: {df[df['card_id'] == x]['risk'].values[0]:.2f}",
                key="selected_card_id"
            )
            
            # Получаем данные выбранной карточки
            selected_card = df[df["card_id"] == selected_card_id].iloc[0]
            
            # Отображаем данные карточки в две колонки
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Данные карточки")
                
                card_data = {
                    "ID карточки": selected_card["card_id"],
                    "Тип карточки": selected_card["card_type"] if "card_type" in selected_card else "Не указан",
                    "Дискриминативность": f"{selected_card['discrimination_avg']:.3f}",
                    "Успешность": f"{selected_card['success_rate']:.1%}",
                    "Успешность с первой попытки": f"{selected_card['first_try_success_rate']:.1%}",
                    "Количество жалоб": f"{selected_card['complaints_total'] if 'complaints_total' in selected_card else 0}",
                    "Доля жалоб": f"{selected_card['complaint_rate']:.1%}",
                    "Доля пытавшихся": f"{selected_card['attempted_share']:.1%}",
                    "Количество попыток": f"{selected_card['total_attempts']:.0f}",
                    "Текущий риск": f"{selected_card['risk']:.3f}"
                }
                
                for key, value in card_data.items():
                    st.markdown(f"**{key}:** {value}")
                
                # Показываем ссылку на карточку, если есть
                if "card_url" in selected_card and pd.notna(selected_card["card_url"]):
                    st.markdown(f"[Открыть карточку в редакторе]({selected_card['card_url']})")
            
            with col2:
                st.markdown("### Расчет риска")
                
                # Рассчитываем риски отдельных метрик с новыми настройками
                try:
                    # Преобразуем серию в словарь для более простой работы
                    card_dict = selected_card.to_dict()
                    card_series = pd.Series(card_dict)
                    
                    # Рассчитываем компоненты риска с новыми параметрами
                    old_risk = selected_card["risk"]
                    
                    # Создаем функции расчета риска с новыми параметрами
                    def discrimination_risk_score_new(discrimination_avg):
                        if discrimination_avg >= config["discrimination"]["good"]:
                            normalized = min(1.0, (discrimination_avg - config["discrimination"]["good"]) / 0.4)
                            return max(0, 0.25 * (1 - normalized))
                        elif discrimination_avg >= config["discrimination"]["medium"]:
                            normalized = (discrimination_avg - config["discrimination"]["medium"]) / (config["discrimination"]["good"] - config["discrimination"]["medium"])
                            return 0.50 - normalized * 0.24
                        else:
                            normalized = max(0, discrimination_avg / config["discrimination"]["medium"])
                            return 1.0 - normalized * 0.49
                    
                    def success_rate_risk_score_new(success_rate):
                        if success_rate > config["success_rate"]["boring"]:
                            normalized = min(1.0, (success_rate - config["success_rate"]["boring"]) / 0.05)
                            return 0.30 + normalized * 0.10
                        elif success_rate >= config["success_rate"]["optimal_low"]:
                            normalized = (success_rate - config["success_rate"]["optimal_low"]) / (config["success_rate"]["boring"] - config["success_rate"]["optimal_low"])
                            return 0.25 * (1 - normalized)
                        elif success_rate >= config["success_rate"]["suboptimal_low"]:
                            normalized = (success_rate - config["success_rate"]["suboptimal_low"]) / (config["success_rate"]["optimal_low"] - config["success_rate"]["suboptimal_low"])
                            return 0.50 - normalized * 0.24
                        else:
                            normalized = max(0, success_rate / config["success_rate"]["suboptimal_low"])
                            return 1.0 - normalized * 0.49
                    
                    def first_try_risk_score_new(first_try_success_rate):
                        if first_try_success_rate > config["first_try"]["too_easy"]:
                            normalized = min(1.0, (first_try_success_rate - config["first_try"]["too_easy"]) / 0.1)
                            return 0.26 + normalized * 0.09
                        elif first_try_success_rate >= config["first_try"]["optimal_low"]:
                            normalized = (first_try_success_rate - config["first_try"]["optimal_low"]) / (config["first_try"]["too_easy"] - config["first_try"]["optimal_low"])
                            return 0.25 * (1 - normalized)
                        elif first_try_success_rate >= config["first_try"]["multiple_low"]:
                            normalized = (first_try_success_rate - config["first_try"]["multiple_low"]) / (config["first_try"]["optimal_low"] - config["first_try"]["multiple_low"])
                            return 0.50 - normalized * 0.24
                        else:
                            normalized = max(0, first_try_success_rate / config["first_try"]["multiple_low"])
                            return 1.0 - normalized * 0.49
                    
                    def complaint_risk_score_new(row):
                        # Получаем абсолютное количество жалоб
                        complaints_total = row.get("complaints_total", 0)
                        
                        if complaints_total > config["complaints"]["critical"]:
                            excess = min(100, complaints_total - config["complaints"]["critical"])
                            normalized = excess / 100
                            return 0.76 + normalized * 0.24
                        elif complaints_total >= config["complaints"]["high"]:
                            normalized = (complaints_total - config["complaints"]["high"]) / (config["complaints"]["critical"] - config["complaints"]["high"])
                            return 0.51 + normalized * 0.24
                        elif complaints_total >= config["complaints"]["medium"]:
                            normalized = (complaints_total - config["complaints"]["medium"]) / (config["complaints"]["high"] - config["complaints"]["medium"])
                            return 0.26 + normalized * 0.24
                        else:
                            normalized = complaints_total / max(1, config["complaints"]["medium"])
                            return normalized * 0.25
                    
                    def attempted_share_risk_score_new(attempted_share):
                        if attempted_share > config["attempts"]["high"]:
                            normalized = min(1.0, (attempted_share - config["attempts"]["high"]) / 0.05)
                            return 0.10 * (1 - normalized)
                        elif attempted_share >= config["attempts"]["normal_low"]:
                            normalized = (attempted_share - config["attempts"]["normal_low"]) / (config["attempts"]["high"] - config["attempts"]["normal_low"])
                            return 0.25 - normalized * 0.15
                        elif attempted_share >= config["attempts"]["insufficient_low"]:
                            normalized = (attempted_share - config["attempts"]["insufficient_low"]) / (config["attempts"]["normal_low"] - config["attempts"]["insufficient_low"])
                            return 0.50 - normalized * 0.24
                        else:
                            normalized = max(0, attempted_share / config["attempts"]["insufficient_low"])
                            return 1.0 - normalized * 0.49
                    
                    # Рассчитываем компоненты риска
                    risk_discr = discrimination_risk_score_new(selected_card["discrimination_avg"])
                    risk_success = success_rate_risk_score_new(selected_card["success_rate"])
                    risk_first_try = first_try_risk_score_new(selected_card["first_try_success_rate"])
                    risk_complaints = complaint_risk_score_new(card_dict)
                    risk_attempted = attempted_share_risk_score_new(selected_card["attempted_share"])
                    
                    # Определяем максимальный риск
                    max_risk = max(risk_discr, risk_success, risk_first_try, risk_complaints, risk_attempted)
                    
                    # Рассчитываем взвешенное среднее
                    weighted_avg_risk = (
                        config["weights"]["discrimination"] * risk_discr +
                        config["weights"]["success_rate"] * risk_success +
                        config["weights"]["first_try"] * risk_first_try +
                        config["weights"]["complaint_rate"] * risk_complaints +
                        config["weights"]["attempted"] * risk_attempted
                    )
                    
                    # Определяем минимальный порог риска на основе максимального риска
                    if max_risk > config["risk_thresholds"]["critical"]:
                        min_threshold = config["risk_thresholds"]["min_for_critical"]
                    elif max_risk > config["risk_thresholds"]["high"]:
                        min_threshold = config["risk_thresholds"]["min_for_high"]
                    else:
                        min_threshold = 0
                    
                    # Применяем комбинированную формулу
                    combined_risk = config["risk_thresholds"]["alpha_weight_avg"] * weighted_avg_risk + (1 - config["risk_thresholds"]["alpha_weight_avg"]) * max_risk
                    raw_risk = max(weighted_avg_risk, combined_risk, min_threshold)
                    
                    # Корректировка на статистическую значимость
                    confidence_factor = min(selected_card["total_attempts"] / config["stats"]["significance_threshold"], 1.0)
                    new_risk = raw_risk * confidence_factor + config["stats"]["neutral_risk_value"] * (1 - confidence_factor)
                    
                    # Отображаем результаты расчета
                    st.markdown(f"#### Риск по метрикам:")
                    
                    # Определение категорий риска и цветов
                    def risk_category(risk):
                        if risk > 0.75:
                            return "Критический", "red"
                        elif risk > 0.5:
                            return "Высокий", "orange"
                        elif risk > 0.25:
                            return "Умеренный", "gold"
                        else:
                            return "Низкий", "green"
                    
                    risks = {
                        "Дискриминативность": risk_discr,
                        "Успешность": risk_success,
                        "Успешность с первой попытки": risk_first_try,
                        "Количество жалоб": risk_complaints,
                        "Доля пытавшихся": risk_attempted
                    }
                    
                    for metric, risk in risks.items():
                        category, color = risk_category(risk)
                        st.markdown(f"**{metric}**: {risk:.3f} - <span style='color:{color};'>{category}</span>", unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    st.markdown(f"**Максимальный риск**: {max_risk:.3f}")
                    st.markdown(f"**Взвешенное среднее**: {weighted_avg_risk:.3f}")
                    st.markdown(f"**Комбинированный риск**: {combined_risk:.3f}")
                    st.markdown(f"**Минимальный порог**: {min_threshold:.3f}")
                    st.markdown(f"**Сырой риск (без корректировки)**: {raw_risk:.3f}")
                    
                    st.markdown("---")
                    
                    st.markdown(f"**Коэффициент доверия**: {confidence_factor:.2f}")
                    st.markdown(f"**Итоговый новый риск**: {new_risk:.3f}")
                    st.markdown(f"**Текущий риск**: {old_risk:.3f}")
                    
                    # Показываем изменение риска
                    delta = new_risk - old_risk
                    delta_color = "red" if delta > 0 else "green"
                    delta_sign = "+" if delta > 0 else ""
                    
                    st.markdown(f"**Изменение риска**: <span style='color:{delta_color};'>{delta_sign}{delta:.3f}</span>", unsafe_allow_html=True)
                    
                    # Визуализация компонентов риска
                    components = pd.DataFrame({
                        "Метрика": list(risks.keys()),
                        "Риск": list(risks.values()),
                        "Вес": [
                            config["weights"]["discrimination"],
                            config["weights"]["success_rate"],
                            config["weights"]["first_try"],
                            config["weights"]["complaint_rate"],
                            config["weights"]["attempted"]
                        ]
                    })
                    
                    # Добавляем столбец с взвешенным риском
                    components["Взвешенный риск"] = components["Риск"] * components["Вес"]
                    
                    # Сортируем по взвешенному риску
                    components = components.sort_values(by="Взвешенный риск", ascending=False)
                    
                    # Создаем столбчатую диаграмму
                    fig = px.bar(
                        components,
                        x="Метрика",
                        y=["Взвешенный риск"],
                        title="Вклад метрик в общий риск",
                        color_discrete_sequence=["red"],
                        labels={"value": "Взвешенный риск", "Метрика": ""}
                    )
                    
                    # Добавляем горизонтальную линию для среднего
                    fig.add_hline(y=weighted_avg_risk, line_dash="dash", line_color="blue", 
                                 annotation_text=f"Взвешенное среднее: {weighted_avg_risk:.3f}", 
                                 annotation_position="top right")
                    
                    # Добавляем аннотации со значениями риска
                    for i, row in components.iterrows():
                        fig.add_annotation(
                            x=row["Метрика"],
                            y=row["Взвешенный риск"] + 0.02,
                            text=f"{row['Риск']:.2f}",
                            showarrow=False,
                            font=dict(size=10)
                        )
                    
                    fig.update_layout(height=350)
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"Ошибка при расчете риска: {str(e)}")
        else:
            st.warning("Нет доступных данных для тестирования.")
    
    # Кнопка сохранения конфигурации
    st.markdown("---")

    with st.expander("📖 Подробное описание формулы риска", expanded=False):
        st.subheader("Как работает формула расчета риска")
        
        st.markdown("""
        ## Концепция интервального подхода к риску
        
        Формула риска основана на интервальном подходе, который оценивает каждую метрику карточки 
        и преобразует её в значение риска от 0 до 1. Это позволяет:
        
        1. Интуитивно понимать, какие значения метрик считаются хорошими, а какие проблемными
        2. Учитывать критические значения отдельных метрик, не позволяя им "затираться" другими
        3. Настраивать веса метрик в зависимости от их важности
        4. Корректировать риск с учетом статистической значимости данных
        
        ### Основные шаги расчета риска:
        
        1. **Преобразование метрик в риск** - каждая метрика преобразуется в значение риска от 0 до 1
        2. **Взвешенное среднее** - вычисляется средневзвешенное значение рисков по всем метрикам
        3. **Учет максимального риска** - комбинируется взвешенное среднее и максимальный риск, без этого шага критические проблемы в одной метрике могут "затираться" хорошими значениями других метрик.
        4. **Минимальный порог** - устанавливается минимальный порог риска для критических метрик, что гарантирует, что карточки с критическими значениями отдельных метрик всегда получат достаточно высокий риск. Работает только при наличии действительно высоких рисков, не влияя на оценку карточек без явных проблем. Карточки с критическими метриками всегда будут попадать в категории, требующие внимания.
        5. **Корректировка на статистическую значимость** - учитывается количество попыток. При малом количестве попыток (низкой статистической значимости) риск смещается к нейтральному значению (0.5).
        6. **Выбор максимального значения из промежуточных показателей** - итоговый риск определяется как максимум между взвешенным средним, комбинированным риском и минимальным порогом
        """)
        
        # Добавляем интерактивную демонстрацию преобразования метрик
        st.markdown("## Интерактивная демонстрация")
        
        # Создаем две колонки: для ввода значений и для графика
        demo_col1, demo_col2 = st.columns([1, 2])
        
        with demo_col1:
            st.markdown("### Введите значения метрик")
            
            # Создаем слайдеры для всех метрик
            demo_discr = st.slider(
                "Дискриминативность",
                min_value=0.0,
                max_value=1.0,
                value=0.4,
                step=0.05,
                key="demo_discr"
            )
            
            demo_success = st.slider(
                "Успешность",
                min_value=0.0,
                max_value=1.0,
                value=0.85,
                step=0.05,
                key="demo_success"
            )
            
            demo_first_try = st.slider(
                "Успешность с 1-й попытки",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.05,
                key="demo_first_try"
            )
            
            demo_complaints = st.number_input(
                "Количество жалоб",
                min_value=0,
                max_value=100,
                value=5,
                step=1,
                key="demo_complaints"
            )
            
            demo_attempts = st.slider(
                "Доля пытавшихся",
                min_value=0.0,
                max_value=1.0,
                value=0.9,
                step=0.05,
                key="demo_attempts"
            )
            
            demo_total_attempts = st.number_input(
                "Количество попыток",
                min_value=1,
                max_value=1000,
                value=200,
                step=10,
                key="demo_total_attempts"
            )
        
        # Расчет риска на основе введенных данных
        # Создаем временные функции для расчета риска с текущими настройками
        def demo_get_discr_risk(val):
            if val >= config["discrimination"]["good"]:
                normalized = min(1.0, (val - config["discrimination"]["good"]) / 0.4)
                return max(0, 0.25 * (1 - normalized))
            elif val >= config["discrimination"]["medium"]:
                normalized = (val - config["discrimination"]["medium"]) / (config["discrimination"]["good"] - config["discrimination"]["medium"])
                return 0.50 - normalized * 0.24
            else:
                normalized = max(0, val / config["discrimination"]["medium"])
                return 1.0 - normalized * 0.49
        
        def demo_get_success_risk(val):
            if val > config["success_rate"]["boring"]:
                normalized = min(1.0, (val - config["success_rate"]["boring"]) / 0.05)
                return 0.30 + normalized * 0.10
            elif val >= config["success_rate"]["optimal_low"]:
                normalized = (val - config["success_rate"]["optimal_low"]) / (config["success_rate"]["boring"] - config["success_rate"]["optimal_low"])
                return 0.25 * (1 - normalized)
            elif val >= config["success_rate"]["suboptimal_low"]:
                normalized = (val - config["success_rate"]["suboptimal_low"]) / (config["success_rate"]["optimal_low"] - config["success_rate"]["suboptimal_low"])
                return 0.50 - normalized * 0.24
            else:
                normalized = max(0, val / config["success_rate"]["suboptimal_low"])
                return 1.0 - normalized * 0.49
        
        def demo_get_first_try_risk(val):
            if val > config["first_try"]["too_easy"]:
                normalized = min(1.0, (val - config["first_try"]["too_easy"]) / 0.1)
                return 0.26 + normalized * 0.09
            elif val >= config["first_try"]["optimal_low"]:
                normalized = (val - config["first_try"]["optimal_low"]) / (config["first_try"]["too_easy"] - config["first_try"]["optimal_low"])
                return 0.25 * (1 - normalized)
            elif val >= config["first_try"]["multiple_low"]:
                normalized = (val - config["first_try"]["multiple_low"]) / (config["first_try"]["optimal_low"] - config["first_try"]["multiple_low"])
                return 0.50 - normalized * 0.24
            else:
                normalized = max(0, val / config["first_try"]["multiple_low"])
                return 1.0 - normalized * 0.49
        
        def demo_get_complaints_risk(val):
            if val > config["complaints"]["critical"]:
                excess = min(100, val - config["complaints"]["critical"])
                normalized = excess / 100
                return 0.76 + normalized * 0.24
            elif val >= config["complaints"]["high"]:
                normalized = (val - config["complaints"]["high"]) / (config["complaints"]["critical"] - config["complaints"]["high"])
                return 0.51 + normalized * 0.24
            elif val >= config["complaints"]["medium"]:
                normalized = (val - config["complaints"]["medium"]) / (config["complaints"]["high"] - config["complaints"]["medium"])
                return 0.26 + normalized * 0.24
            else:
                normalized = val / max(1, config["complaints"]["medium"])
                return normalized * 0.25
        
        def demo_get_attempts_risk(val):
            if val > config["attempts"]["high"]:
                normalized = min(1.0, (val - config["attempts"]["high"]) / 0.05)
                return 0.10 * (1 - normalized)
            elif val >= config["attempts"]["normal_low"]:
                normalized = (val - config["attempts"]["normal_low"]) / (config["attempts"]["high"] - config["attempts"]["normal_low"])
                return 0.25 - normalized * 0.15
            elif val >= config["attempts"]["insufficient_low"]:
                normalized = (val - config["attempts"]["insufficient_low"]) / (config["attempts"]["normal_low"] - config["attempts"]["insufficient_low"])
                return 0.50 - normalized * 0.24
            else:
                normalized = max(0, val / config["attempts"]["insufficient_low"])
                return 1.0 - normalized * 0.49
        
        # Рассчитываем риски для каждой метрики
        risk_discr = demo_get_discr_risk(demo_discr)
        risk_success = demo_get_success_risk(demo_success)
        risk_first_try = demo_get_first_try_risk(demo_first_try)
        risk_complaints = demo_get_complaints_risk(demo_complaints)
        risk_attempts = demo_get_attempts_risk(demo_attempts)
        
        # Рассчитываем максимальный риск
        max_risk = max(risk_discr, risk_success, risk_first_try, risk_complaints, risk_attempts)
        
        # Рассчитываем взвешенное среднее
        weighted_avg = (
            config["weights"]["discrimination"] * risk_discr +
            config["weights"]["success_rate"] * risk_success +
            config["weights"]["first_try"] * risk_first_try +
            config["weights"]["complaint_rate"] * risk_complaints +
            config["weights"]["attempted"] * risk_attempts
        )
        
        # Определяем минимальный порог
        if max_risk > config["risk_thresholds"]["critical"]:
            min_threshold = config["risk_thresholds"]["min_for_critical"]
        elif max_risk > config["risk_thresholds"]["high"]:
            min_threshold = config["risk_thresholds"]["min_for_high"]
        else:
            min_threshold = 0
        
        # Применяем комбинированную формулу
        combined_risk = config["risk_thresholds"]["alpha_weight_avg"] * weighted_avg + (1 - config["risk_thresholds"]["alpha_weight_avg"]) * max_risk
        raw_risk = max(weighted_avg, combined_risk, min_threshold)
        
        # Корректировка на статистическую значимость
        confidence = min(demo_total_attempts / config["stats"]["significance_threshold"], 1.0)
        final_risk = raw_risk * confidence + config["stats"]["neutral_risk_value"] * (1 - confidence)
        
        # Вычисляем вклад каждой метрики во взвешенное среднее
        contribution_discr = config["weights"]["discrimination"] * risk_discr / weighted_avg if weighted_avg > 0 else 0
        contribution_success = config["weights"]["success_rate"] * risk_success / weighted_avg if weighted_avg > 0 else 0
        contribution_first_try = config["weights"]["first_try"] * risk_first_try / weighted_avg if weighted_avg > 0 else 0
        contribution_complaints = config["weights"]["complaint_rate"] * risk_complaints / weighted_avg if weighted_avg > 0 else 0
        contribution_attempts = config["weights"]["attempted"] * risk_attempts / weighted_avg if weighted_avg > 0 else 0
        
        with demo_col2:
            st.markdown("### Результат расчета риска")
            
            # Создаем датафрейм для отображения рисков по метрикам
            risks_df = pd.DataFrame({
                "Метрика": ["Дискриминативность", "Успешность", "Успех с 1-й попытки", "Количество жалоб", "Доля пытавшихся"],
                "Значение": [demo_discr, demo_success, demo_first_try, demo_complaints, demo_attempts],
                "Риск": [risk_discr, risk_success, risk_first_try, risk_complaints, risk_attempts],
                "Вес": [
                    config["weights"]["discrimination"],
                    config["weights"]["success_rate"],
                    config["weights"]["first_try"],
                    config["weights"]["complaint_rate"],
                    config["weights"]["attempted"]
                ],
                "Взвешенный риск": [
                    config["weights"]["discrimination"] * risk_discr,
                    config["weights"]["success_rate"] * risk_success,
                    config["weights"]["first_try"] * risk_first_try,
                    config["weights"]["complaint_rate"] * risk_complaints,
                    config["weights"]["attempted"] * risk_attempts
                ]
            })
            
            # Сортируем по взвешенному риску
            risks_df = risks_df.sort_values("Взвешенный риск", ascending=False)
            
            # Создаем график с вкладом каждой метрики
            fig = px.bar(
                risks_df,
                x="Метрика",
                y="Взвешенный риск",
                title="Вклад метрик в общий риск",
                color="Риск",
                color_continuous_scale="RdYlGn_r",
                text=risks_df["Риск"].apply(lambda x: f"{x:.2f}")
            )
            
            # Добавляем горизонтальную линию для взвешенного среднего
            fig.add_hline(
                y=weighted_avg,
                line_dash="dash",
                line_color="blue",
                annotation_text=f"Взвешенное среднее: {weighted_avg:.2f}",
                annotation_position="top right"
            )
            
            # Добавляем горизонтальную линию для максимального риска
            fig.add_hline(
                y=max_risk,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Максимальный риск: {max_risk:.2f}",
                annotation_position="top right"
            )
            
            # Обновляем макет
            fig.update_layout(height=400)
            
            # Отображаем график
            st.plotly_chart(fig, use_container_width=True)
            
            # Показываем итоговый расчет риска
            st.markdown("### Формула расчета риска")
            
            # Описание расчета
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Промежуточные значения:")
                st.markdown(f"**Взвешенное среднее:** {weighted_avg:.3f}")
                st.markdown(f"<span style='color:gray; font-size:0.9em'>= ({config['weights']['discrimination']:.3f} × {risk_discr:.3f}) + ({config['weights']['success_rate']:.3f} × {risk_success:.3f}) + ({config['weights']['first_try']:.3f} × {risk_first_try:.3f}) + ({config['weights']['complaint_rate']:.3f} × {risk_complaints:.3f}) + ({config['weights']['attempted']:.3f} × {risk_attempts:.3f})</span>", unsafe_allow_html=True)
                
                st.markdown(f"**Максимальный риск:** {max_risk:.3f}")
                st.markdown(f"<span style='color:gray; font-size:0.9em'>= max({risk_discr:.3f}, {risk_success:.3f}, {risk_first_try:.3f}, {risk_complaints:.3f}, {risk_attempts:.3f})</span>", unsafe_allow_html=True)
                
                st.markdown(f"**Минимальный порог:** {min_threshold:.3f}")
                min_threshold_explanation = ""
                if max_risk > config["risk_thresholds"]["critical"]:
                    min_threshold_explanation = f"= {config['risk_thresholds']['min_for_critical']:.3f} (т.к. max_risk {max_risk:.3f} > critical_threshold {config['risk_thresholds']['critical']:.3f})"
                elif max_risk > config["risk_thresholds"]["high"]:
                    min_threshold_explanation = f"= {config['risk_thresholds']['min_for_high']:.3f} (т.к. max_risk {max_risk:.3f} > high_threshold {config['risk_thresholds']['high']:.3f})"
                else:
                    min_threshold_explanation = "= 0 (т.к. нет высокого риска)"
                st.markdown(f"<span style='color:gray; font-size:0.9em'>{min_threshold_explanation}</span>", unsafe_allow_html=True)
                
                st.markdown(f"**Комбинированный риск:** {combined_risk:.3f}")
                st.markdown(f"<span style='color:gray; font-size:0.9em'>= ({config['risk_thresholds']['alpha_weight_avg']:.3f} × {weighted_avg:.3f}) + ((1 - {config['risk_thresholds']['alpha_weight_avg']:.3f}) × {max_risk:.3f})</span>", unsafe_allow_html=True)
                
                st.markdown(f"**Сырой риск:** {raw_risk:.3f}")
                st.markdown(f"<span style='color:gray; font-size:0.9em'>= max({weighted_avg:.3f}, {combined_risk:.3f}, {min_threshold:.3f})</span>", unsafe_allow_html=True)
                
                st.markdown(f"**Коэффициент доверия:** {confidence:.2f}")
                st.markdown(f"<span style='color:gray; font-size:0.9em'>= min({demo_total_attempts} / {config['stats']['significance_threshold']}, 1.0) = min({demo_total_attempts/config['stats']['significance_threshold']:.3f}, 1.0)</span>", unsafe_allow_html=True)
            
            with col2:
                # Показываем категорию риска и итоговое значение
                final_category = "Неизвестный"
                category_color = "gray"
                
                if final_risk <= 0.25:
                    final_category = "Низкий"
                    category_color = "green"
                elif final_risk <= 0.50:
                    final_category = "Умеренный"
                    category_color = "orange"
                elif final_risk <= 0.75:
                    final_category = "Высокий" 
                    category_color = "red"
                else:
                    final_category = "Критический"
                    category_color = "darkred"
                
                st.markdown(f"#### Итоговый риск:")
                st.markdown(f"**Значение риска:** {final_risk:.3f}")
                st.markdown(f"**Категория риска:** <span style='color:{category_color};font-weight:bold;'>{final_category}</span>", unsafe_allow_html=True)
                
                # Показываем, что повлияло на решение
                decision_factor = ""
                if raw_risk == weighted_avg:
                    decision_factor = "взвешенное среднее"
                elif raw_risk == combined_risk:
                    decision_factor = "комбинированный риск"
                elif raw_risk == min_threshold:
                    decision_factor = "минимальный порог из-за высокого риска метрики"
                
                st.markdown(f"**Решающий фактор:** {decision_factor}")
        
        # Показываем пошаговое объяснение формулы
        st.markdown("## Пошаговое объяснение расчета")
        
        st.markdown("""
        ### Шаг 1: Преобразование метрик в риск
        
        Каждая метрика преобразуется в значение риска от 0 до 1 на основе заданных интервалов:
        """)
        
        # Создаем таблицу с примерами преобразования метрик в риск
        metrics_examples = pd.DataFrame({
            "Метрика": ["Дискриминативность", "Успешность", "Успех с 1-й попытки", "Количество жалоб", "Доля пытавшихся"],
            "Значение": [demo_discr, demo_success, demo_first_try, demo_complaints, demo_attempts],
            "Риск": [risk_discr, risk_success, risk_first_try, risk_complaints, risk_attempts],
            "Формула преобразования": [
                "Хорошая: >0.35, Средняя: 0.15-0.35, Низкая: <0.15", 
                "Скучная: >0.95, Оптимальная: 0.75-0.95, Субоптимальная: 0.50-0.75, Фрустрирующая: <0.50",
                "Слишком простая: >0.90, Оптимальная: 0.65-0.90, Требует попыток: 0.40-0.65, Сложная: <0.40",
                f"Критическое: >{config['complaints']['critical']}, Высокое: {config['complaints']['high']}-{config['complaints']['critical']}, Среднее: {config['complaints']['medium']}-{config['complaints']['high']}, Низкое: <{config['complaints']['medium']}",
                "Высокая: >0.95, Нормальная: 0.80-0.95, Недостаточная: 0.60-0.80, Игнорируемая: <0.60"
            ]
        })
        
        # Отображаем таблицу
        st.dataframe(metrics_examples, use_container_width=True)
        
        st.markdown("""
        ### Шаг 2: Взвешенное среднее
        
        Вычисляется взвешенное среднее значение рисков всех метрик с учетом их весов:
        
        Взвешенное среднее = Σ(Риск_метрики * Вес_метрики)
        """)
        
        # Создаем таблицу с вкладом каждой метрики
        weighted_examples = pd.DataFrame({
            "Метрика": risks_df["Метрика"],
            "Риск": risks_df["Риск"],
            "Вес": risks_df["Вес"],
            "Вклад в риск": risks_df["Взвешенный риск"],
            "Доля в общем риске": [
                f"{contribution_discr*100:.1f}%",
                f"{contribution_success*100:.1f}%",
                f"{contribution_first_try*100:.1f}%",
                f"{contribution_complaints*100:.1f}%",
                f"{contribution_attempts*100:.1f}%"
            ]
        })
        
        # Отображаем таблицу
        st.dataframe(weighted_examples, use_container_width=True)
        
        # Строка расчета взвешенного среднего
        weighted_formula = " + ".join([f"{row['Вес']:.2f} × {row['Риск']:.2f}" for _, row in risks_df.iterrows()])
        st.markdown(f"**Взвешенное среднее** = {weighted_formula} = **{weighted_avg:.3f}**")
        
        st.markdown("""
        ### Шаг 3: Учет максимального риска
        
        Комбинируем взвешенное среднее и максимальный риск по формуле:
        
        Комбинированный риск = α × Взвешенное_среднее + (1-α) × Максимальный_риск
        
        где α - коэффициент баланса между взвешенным средним и максимальным риском (0.7)
        """)
        
        # Строка расчета комбинированного риска
        st.markdown(f"""
        **Максимальный риск** = max({', '.join([f"{r:.2f}" for r in [risk_discr, risk_success, risk_first_try, risk_complaints, risk_attempts]])}) = **{max_risk:.3f}**
        
        **Комбинированный риск** = {config["risk_thresholds"]["alpha_weight_avg"]:.2f} × {weighted_avg:.3f} + (1 - {config["risk_thresholds"]["alpha_weight_avg"]:.2f}) × {max_risk:.3f} = **{combined_risk:.3f}**
        """)
        
        st.markdown("""
        ### Шаг 4: Минимальный порог
        
        Устанавливаем минимальный порог риска в зависимости от максимального риска среди метрик:
        
        * Если есть метрика с критическим риском (>0.75), итоговый риск не может быть ниже 0.60
        * Если есть метрика с высоким риском (>0.50), итоговый риск не может быть ниже 0.40
        """)
        
        # Описание минимального порога
        threshold_reason = ""
        if max_risk > config["risk_thresholds"]["critical"]:
            threshold_reason = f"Есть метрика с критическим риском (>{config['risk_thresholds']['critical']:.2f})"
        elif max_risk > config["risk_thresholds"]["high"]:
            threshold_reason = f"Есть метрика с высоким риском (>{config['risk_thresholds']['high']:.2f})"
        else:
            threshold_reason = "Нет метрик с высоким риском"
        
        st.markdown(f"""
        **Минимальный порог** = **{min_threshold:.2f}** ({threshold_reason})
        
        **Сырой риск** = max({weighted_avg:.3f}, {combined_risk:.3f}, {min_threshold:.2f}) = **{raw_risk:.3f}**
        """)
        
        st.markdown("""
        ### Шаг 5: Корректировка на статистическую значимость
        
        Корректируем риск с учетом количества попыток:
        
        * Если попыток мало, значение риска смещается к нейтральному значению (0.5)
        * Если попыток достаточно (>100), используется рассчитанное значение риска
        
        Итоговый риск = Сырой_риск × Коэффициент_доверия + 0.5 × (1 - Коэффициент_доверия)
        """)
        
        # Строка расчета итогового риска
        st.markdown(f"""
        **Коэффициент доверия** = min({demo_total_attempts} / {config["stats"]["significance_threshold"]}, 1.0) = **{confidence:.2f}**
        
        **Итоговый риск** = {raw_risk:.3f} × {confidence:.2f} + {config["stats"]["neutral_risk_value"]:.2f} × (1 - {confidence:.2f}) = **{final_risk:.3f}**
        """)
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("💾 Сохранить конфигурацию", type="primary"):
            # Сохраняем конфигурацию с использованием функции из core_config
            if save_config(config):
                st.success("Конфигурация успешно сохранена и будет применяться к расчетам риска!")
            else:
                st.error("Ошибка при сохранении конфигурации.")

    with col2:
        # Отображаем структуру конфигурации
        if st.checkbox("Показать JSON конфигурации"):
            st.code(json.dumps(config, indent=4, ensure_ascii=False), language="json")
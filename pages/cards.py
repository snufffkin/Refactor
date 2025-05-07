# pages/cards.py
"""
Страница с детальным анализом одной карточки
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from sqlalchemy import text

import core
from components.utils import create_hierarchical_header, add_gz_links, add_card_links
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart

# Функция для отображения подробной информации о карточке
def display_card_details(card_data):
    """
    Отображает подробную информацию о карточке
    
    Args:
        card_data: Series с данными карточки
    """
    # Создаем колонки для отображения информации
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Основная информация о карточке
        st.markdown("### Основная информация")
        
        # Определяем уровень подлости
        trickiness_level = card_data.get("trickiness_level", 0)
        trickiness_text = "Нет"
        trickiness_color = "gray"
        
        if trickiness_level == 1:
            trickiness_text = "Низкий"
            trickiness_color = "yellow"
        elif trickiness_level == 2:
            trickiness_text = "Средний"
            trickiness_color = "orange"
        elif trickiness_level == 3:
            trickiness_text = "Высокий"
            trickiness_color = "red"
        
        # Собираем данные о карточке
        card_info = {
            "ID карточки": int(card_data["card_id"]),
            "Тип карточки": card_data["card_type"] if "card_type" in card_data else "Не указан",
            "Программа": card_data["program"],
            "Модуль": card_data["module"],
            "Урок": card_data["lesson"],
            "Группа заданий": card_data["gz"],
            "Статус": card_data["status"],
            "Текущий риск": f"{card_data['risk']:.3f}"
        }
        
        # Отображаем основную информацию
        for key, value in card_info.items():
            st.markdown(f"**{key}:** {value}")
        
        # Показываем ссылку на карточку, если есть
        if "card_url" in card_data and pd.notna(card_data["card_url"]):
            st.markdown(f"[🔗 Открыть карточку в редакторе]({card_data['card_url']})")
    
    with col2:
        # Метрики карточки
        st.markdown("### Ключевые метрики")
        
        # Отображаем метрики с подходящим форматированием
        metrics = {
            "Успешность": f"{card_data['success_rate']:.1%}",
            "Успешность с первой попытки": f"{card_data['first_try_success_rate']:.1%}",
            "Разница": f"{card_data['success_rate'] - card_data['first_try_success_rate']:.1%}",
            "Уровень подлости": f"<span style='color:{trickiness_color};font-weight:bold;'>{trickiness_text}</span>",
            "Дискриминативность": f"{card_data['discrimination_avg']:.3f}",
            "Количество жалоб": f"{card_data.get('complaints_total', card_data['complaint_rate'] * card_data['total_attempts']):.0f}",
            "Доля жалоб": f"{card_data['complaint_rate']:.1%}",
            "Доля пытавшихся": f"{card_data['attempted_share']:.1%}",
            "Количество попыток": f"{card_data['total_attempts']:.0f}"
        }
        
        for key, value in metrics.items():
            if key == "Уровень подлости":
                st.markdown(f"**{key}:** {value}", unsafe_allow_html=True)
            else:
                st.markdown(f"**{key}:** {value}")

def display_course_links(card_id, engine, card_df):
    """
    Отображает привязку карточки к курсам, урокам и группам заданий
    
    Args:
        card_id: ID карточки
        engine: SQLAlchemy engine для подключения к БД
        card_df: DataFrame с данными карточек
    """
    st.markdown("## Привязка к курсам")
    
    # Вспомогательная функция для URL-кодирования
    def create_query_params(params_dict):
        """Создает строку URL-параметров из словаря"""
        import urllib.parse
        return urllib.parse.urlencode(params_dict)
    
    try:
        # Запрос для изучения структуры таблицы card_assignments
        schema_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'card_assignments'
        """)
        
        # Получаем структуру таблицы
        with engine.connect() as conn:
            schema_result = conn.execute(schema_query)
            columns = [row[0] for row in schema_result]
            
            st.write("Доступные колонки в таблице card_assignments:", columns)
            
            # Запрос для получения данных о привязке карточки
            # Используем DISTINCT для получения уникальных привязок
            query = text("""
                SELECT DISTINCT card_id, status, user_id, assigned_at, updated_at
                FROM card_assignments 
                WHERE card_id = :card_id
            """)
            
            result = conn.execute(query, {"card_id": card_id})
            assignments = [row._asdict() for row in result]
            
            if assignments:
                st.markdown("### Информация о назначениях")
                for assignment in assignments:
                    st.markdown(f"- **Статус**: {assignment['status']}")
                    st.markdown(f"  **Дата назначения**: {assignment['assigned_at']}")
                    st.markdown(f"  **Последнее обновление**: {assignment['updated_at']}")
    except Exception as e:
        st.error(f"Ошибка при запросе к таблице card_assignments: {str(e)}")
    
    # Используем данные из DataFrame для отображения привязок
    try:
        # Находим все записи с данным card_id
        matching_cards = card_df[card_df["card_id"] == int(card_id)]
        
        if matching_cards.empty:
            st.info("В DataFrame нет данных о привязке карточки к курсам.")
            return
        
        # Группируем по программе, модулю, уроку
        key_columns = ['program', 'module', 'lesson']
        if all(col in matching_cards.columns for col in key_columns):
            grouped = matching_cards.groupby(key_columns)
            
            # Отображаем данные
            st.markdown("### Привязка к урокам")
            for (program, module, lesson), group in grouped:
                with st.expander(f"📚 {program} / {module} / {lesson}", expanded=False):
                    # Создаем таблицу
                    for _, row in group.iterrows():
                        gz = row.get('gz', 'Неизвестно')
                        card_type = row.get('card_type', 'Неизвестно')
                        
                        # Формируем URL для перехода к ГЗ
                        gz_url_params = {
                            "program": program,
                            "module": module,
                            "lesson": lesson,
                            "gz": gz
                        }
                        gz_url = f"/?{create_query_params(gz_url_params)}"
                        
                        # Отображаем строку с ссылкой
                        st.markdown(f"- **ГЗ**: [{gz}]({gz_url}) - **Тип карточки**: {card_type}")
        else:
            # Если нет данных о привязке, показываем доступные в записи поля
            st.info("Не найдены поля program/module/lesson в DataFrame.")
            for _, row in matching_cards.iterrows():
                st.markdown("### Доступная информация о карточке")
                for col in matching_cards.columns:
                    if col != 'card_id' and not pd.isna(row[col]):
                        st.markdown(f"**{col}**: {row[col]}")
    
    except Exception as e:
        st.error(f"Ошибка при обработке данных из DataFrame: {str(e)}")
        # Выводим детали для отладки
        st.markdown("### Отладочная информация")
        st.markdown(f"Тип card_df: {type(card_df)}")
        st.markdown(f"Форма card_df: {card_df.shape if hasattr(card_df, 'shape') else 'Нет формы'}")
        st.markdown(f"Колонки card_df: {list(card_df.columns) if hasattr(card_df, 'columns') else 'Нет колонок'}")

def display_risk_components(card_data):
    """
    Отображает компоненты риска для карточки
    
    Args:
        card_data: Series с данными карточки
    """
    st.markdown("## Анализ компонентов риска")
    
    # Получаем параметры из конфигурации
    config = core.get_config()
    
    # Рассчитываем риски отдельных метрик
    card_dict = card_data.to_dict()
    risk_discr = core.discrimination_risk_score(card_data["discrimination_avg"])
    risk_success = core.success_rate_risk_score(card_data["success_rate"])
    risk_trickiness = core.trickiness_risk_score(card_dict)
    risk_complaints = core.complaint_risk_score(card_dict)
    risk_attempted = core.attempted_share_risk_score(card_data["attempted_share"])
    
    # Определяем максимальный риск
    max_risk = max(risk_discr, risk_success, risk_trickiness, risk_complaints, risk_attempted)
    
    # Получаем веса из конфигурации
    WEIGHT_DISCRIMINATION = config["weights"]["discrimination"]
    WEIGHT_SUCCESS_RATE = config["weights"]["success_rate"]
    WEIGHT_TRICKINESS = config["weights"].get("trickiness", 0.15)
    WEIGHT_COMPLAINT_RATE = config["weights"]["complaint_rate"]
    WEIGHT_ATTEMPTED = config["weights"]["attempted"]
    
    # Рассчитываем взвешенное среднее
    weighted_avg_risk = (
        WEIGHT_DISCRIMINATION * risk_discr +
        WEIGHT_SUCCESS_RATE * risk_success +
        WEIGHT_TRICKINESS * risk_trickiness +
        WEIGHT_COMPLAINT_RATE * risk_complaints +
        WEIGHT_ATTEMPTED * risk_attempted
    )
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        # Отображаем результаты расчета
        st.markdown("### Риск по метрикам")
        
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
        
        # Словарь с рисками для отображения
        risks = {
            "Дискриминативность": risk_discr,
            "Успешность": risk_success,
            "Подлость": risk_trickiness,
            "Количество жалоб": risk_complaints,
            "Доля пытавшихся": risk_attempted
        }
        
        # Отображаем риски по метрикам с категориями
        for metric, risk in risks.items():
            category, color = risk_category(risk)
            st.markdown(f"**{metric}**: {risk:.3f} - <span style='color:{color};'>{category}</span>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Отображаем промежуточные значения расчета
        st.markdown("### Формула расчета")
        st.markdown(f"**Взвешенное среднее**: {weighted_avg_risk:.3f}")
        st.markdown(f"**Максимальный риск**: {max_risk:.3f}")
        
        # Определяем минимальный порог риска
        min_threshold = 0
        if max_risk > config["risk_thresholds"]["critical"]:
            min_threshold = config["risk_thresholds"]["min_for_critical"]
        elif max_risk > config["risk_thresholds"]["high"]:
            min_threshold = config["risk_thresholds"]["min_for_high"]
        
        st.markdown(f"**Минимальный порог**: {min_threshold:.3f}")
        
        # Комбинированный риск
        alpha = config["risk_thresholds"]["alpha_weight_avg"]
        combined_risk = alpha * weighted_avg_risk + (1 - alpha) * max_risk
        st.markdown(f"**Комбинированный риск**: {combined_risk:.3f}")
        
        # Сырой риск (без корректировки)
        raw_risk = max(weighted_avg_risk, combined_risk, min_threshold)
        st.markdown(f"**Сырой риск**: {raw_risk:.3f}")
        
        # Корректировка на статистическую значимость
        significance_threshold = config["stats"]["significance_threshold"]
        neutral_risk_value = config["stats"]["neutral_risk_value"]
        confidence_factor = min(card_data["total_attempts"] / significance_threshold, 1.0)
        
        st.markdown(f"**Коэффициент доверия**: {confidence_factor:.2f}")
        
        # Итоговый риск
        final_risk = raw_risk * confidence_factor + neutral_risk_value * (1 - confidence_factor)
        st.markdown(f"**Итоговый риск**: {final_risk:.3f}")
    
    with col2:
        # Создаем DataFrame для визуализации
        risks_df = pd.DataFrame({
            "Метрика": list(risks.keys()),
            "Риск": list(risks.values()),
            "Вес": [WEIGHT_DISCRIMINATION, WEIGHT_SUCCESS_RATE, WEIGHT_TRICKINESS, WEIGHT_COMPLAINT_RATE, WEIGHT_ATTEMPTED],
            "Взвешенный риск": [
                WEIGHT_DISCRIMINATION * risk_discr,
                WEIGHT_SUCCESS_RATE * risk_success,
                WEIGHT_TRICKINESS * risk_trickiness,
                WEIGHT_COMPLAINT_RATE * risk_complaints,
                WEIGHT_ATTEMPTED * risk_attempted
            ]
        })
        
        # Сортируем по взвешенному риску
        risks_df = risks_df.sort_values(by="Взвешенный риск", ascending=False)
        
        # Создаем график
        fig = px.bar(
            risks_df,
            x="Метрика",
            y="Взвешенный риск",
            color="Риск",
            color_continuous_scale="RdYlGn_r",
            title="Вклад метрик в общий риск",
            labels={"Взвешенный риск": "Вклад в риск"},
            text=risks_df["Риск"].apply(lambda x: f"{x:.2f}")
        )
        
        # Добавляем горизонтальную линию для среднего
        fig.add_hline(y=weighted_avg_risk, line_dash="dash", line_color="blue", 
                     annotation_text=f"Взвешенное среднее: {weighted_avg_risk:.2f}", 
                     annotation_position="top right")
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

def display_success_analysis(card_data):
    """
    Отображает анализ успешности для карточки
    
    Args:
        card_data: Series с данными карточки
    """
    st.markdown("## Анализ успешности")
    
    # Создаем колонки для разных графиков
    col1, col2 = st.columns(2)
    
    with col1:
        # Визуализация успешности и первой попытки
        fig = go.Figure()
        
        # Добавляем столбцы для общей успешности и успеха с первой попытки
        fig.add_trace(go.Bar(
            x=["Общая успешность", "Успех с первой попытки"],
            y=[card_data["success_rate"], card_data["first_try_success_rate"]],
            marker_color=["#4da6ff", "#ff9040"],
            text=[f"{card_data['success_rate']:.1%}", f"{card_data['first_try_success_rate']:.1%}"],
            textposition="auto"
        ))
        
        # Настройка макета
        fig.update_layout(
            title="Сравнение общей успешности и успеха с первой попытки",
            yaxis=dict(
                title="Доля успешных попыток",
                tickformat=".0%",
                range=[0, 1]
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Визуализация уровня подлости
        fig = go.Figure()
        
        # Получаем уровень подлости
        trickiness_level = card_data.get("trickiness_level", 0)
        
        # Определяем категории и цвета
        categories = ["Нет подлости", "Низкий уровень", "Средний уровень", "Высокий уровень"]
        colors = ["#c0c0c0", "#ffff7f", "#ffaa7f", "#ff7f7f"]
        
        # Создаем данные для графика
        levels = [0, 0, 0, 0]  # Изначально все 0
        levels[trickiness_level] = 1  # Устанавливаем 1 для текущего уровня
        
        # Добавляем столбцы для уровней подлости
        fig.add_trace(go.Bar(
            x=categories,
            y=levels,
            marker_color=colors,
            text=[trickiness_level == i for i in range(4)],
            textposition="auto"
        ))
        
        # Настройка макета
        fig.update_layout(
            title="Уровень подлости карточки",
            yaxis=dict(
                title="Значение",
                range=[0, 1],
                showticklabels=False
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Рассчитываем разницу между общей успешностью и успехом с первой попытки
    success_diff = card_data["success_rate"] - card_data["first_try_success_rate"]
    
    # Отображаем пояснения на основе данных успешности
    st.markdown("### Интерпретация данных успешности")
    
    success_interpretation = ""
    if card_data["success_rate"] > 0.95:
        success_interpretation = "Карточка имеет **очень высокую общую успешность** (>95%), что может указывать на то, что она слишком простая."
    elif card_data["success_rate"] > 0.8:
        success_interpretation = "Карточка имеет **высокую общую успешность** (>80%), что является хорошим показателем."
    elif card_data["success_rate"] > 0.6:
        success_interpretation = "Карточка имеет **среднюю общую успешность** (>60%), что является приемлемым значением."
    else:
        success_interpretation = "Карточка имеет **низкую общую успешность** (<60%), что может указывать на её чрезмерную сложность или недостаточно ясную формулировку."
    
    first_try_interpretation = ""
    if card_data["first_try_success_rate"] > 0.9:
        first_try_interpretation = "**Очень высокая успешность с первой попытки** (>90%) указывает на то, что задание слишком простое."
    elif card_data["first_try_success_rate"] > 0.7:
        first_try_interpretation = "**Высокая успешность с первой попытки** (>70%) говорит о том, что задание интуитивно понятно."
    elif card_data["first_try_success_rate"] > 0.5:
        first_try_interpretation = "**Средняя успешность с первой попытки** (>50%) показывает хороший баланс сложности."
    else:
        first_try_interpretation = "**Низкая успешность с первой попытки** (<50%) указывает на то, что студентам требуется несколько попыток для понимания задания."
    
    diff_interpretation = ""
    if success_diff > 0.3:
        diff_interpretation = "**Большая разница** между общей успешностью и успехом с первой попытки (>30%) указывает на то, что карточка может содержать скрытые сложности или неоднозначности, которые студенты преодолевают после нескольких попыток."
    elif success_diff > 0.2:
        diff_interpretation = "**Средняя разница** между общей успешностью и успехом с первой попытки (>20%) говорит о том, что карточка требует дополнительных попыток для полного понимания."
    else:
        diff_interpretation = "**Небольшая разница** между общей успешностью и успехом с первой попытки (<20%) указывает на то, что большинство студентов либо сразу понимают задание, либо не могут его решить даже после нескольких попыток."
    
    # Отображаем интерпретацию
    st.markdown(success_interpretation)
    st.markdown(first_try_interpretation)
    st.markdown(diff_interpretation)
    
    # Если карточка является "трики", добавляем специальный блок
    if trickiness_level > 0:
        st.markdown("### Анализ \"трики\"-характеристик")
        
        trickiness_explanation = {
            1: "Карточка имеет **низкий уровень подлости**. Студенты в целом успешно решают задание, но часто требуется несколько попыток.",
            2: "Карточка имеет **средний уровень подлости**. Заметна существенная разница между общей успешностью и успехом с первой попытки, что может указывать на неочевидные моменты в задании.",
            3: "Карточка имеет **высокий уровень подлости**. Большинство студентов не справляются с заданием с первой попытки, но в итоге решают его. Это может быть признаком наличия скрытых условий или неоднозначностей в формулировке."
        }
        
        st.markdown(trickiness_explanation.get(trickiness_level, ""))
        
        st.markdown("""
        **Рекомендации для трики-карточек:**
        - Проверить формулировку задания на наличие неоднозначностей
        - Уточнить условия задания, особенно если они неявно подразумеваются
        - Добавить подсказки или пояснения для улучшения понимания с первой попытки
        - Рассмотреть возможность переработки задания, если разница между попытками слишком велика
        """)

def display_complaints_analysis(card_data):
    """
    Отображает анализ жалоб для карточки
    
    Args:
        card_data: Series с данными карточки
    """
    st.markdown("## Анализ жалоб")
    
    # Рассчитываем абсолютное количество жалоб
    complaints_total = 0
    if "complaints_total" in card_data:
        complaints_total = card_data["complaints_total"]
    elif "complaint_rate" in card_data and "total_attempts" in card_data:
        complaints_total = card_data["complaint_rate"] * card_data["total_attempts"]
    
    # Создаем колонки для разных показателей
    col1, col2 = st.columns(2)
    
    with col1:
        # Визуализация абсолютного количества жалоб
        fig = go.Figure()
        
        # Добавляем столбец для количества жалоб
        fig.add_trace(go.Bar(
            x=["Количество жалоб"],
            y=[complaints_total],
            marker_color="#ff6666",
            text=[f"{complaints_total:.0f}"],
            textposition="auto"
        ))
        
        # Настройка макета
        fig.update_layout(
            title="Абсолютное количество жалоб",
            yaxis=dict(
                title="Количество"
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Визуализация доли жалоб
        fig = go.Figure()
        
        # Добавляем столбец для доли жалоб
        fig.add_trace(go.Bar(
            x=["Доля жалоб"],
            y=[card_data["complaint_rate"]],
            marker_color="#ff6666",
            text=[f"{card_data['complaint_rate']:.1%}"],
            textposition="auto"
        ))
        
        # Настройка макета
        fig.update_layout(
            title="Доля жалоб",
            yaxis=dict(
                title="Доля",
                tickformat=".0%",
                range=[0, max(0.25, card_data["complaint_rate"] * 1.5)]
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Отображаем пояснения на основе данных о жалобах
    st.markdown("### Интерпретация данных о жалобах")
    
    complaints_interpretation = ""
    if complaints_total > 50:
        complaints_interpretation = f"Карточка имеет **критически высокое количество жалоб** ({complaints_total:.0f}). Это указывает на серьезные проблемы с заданием, которые требуют немедленного внимания."
    elif complaints_total > 10:
        complaints_interpretation = f"Карточка имеет **высокое количество жалоб** ({complaints_total:.0f}). Необходимо проанализировать причины и внести исправления."
    elif complaints_total > 5:
        complaints_interpretation = f"Карточка имеет **среднее количество жалоб** ({complaints_total:.0f}). Рекомендуется обратить внимание на возможные проблемы."
    else:
        complaints_interpretation = f"Карточка имеет **низкое количество жалоб** ({complaints_total:.0f}), что является хорошим показателем."
    
    complaint_rate_interpretation = ""
    if card_data["complaint_rate"] > 0.1:
        complaint_rate_interpretation = f"**Высокая доля жалоб** ({card_data['complaint_rate']:.1%}) указывает на то, что значительная часть студентов испытывает проблемы с заданием."
    elif card_data["complaint_rate"] > 0.05:
        complaint_rate_interpretation = f"**Средняя доля жалоб** ({card_data['complaint_rate']:.1%}) говорит о наличии некоторых проблем с заданием, но не критичных."
    else:
        complaint_rate_interpretation = f"**Низкая доля жалоб** ({card_data['complaint_rate']:.1%}) свидетельствует о том, что большинство студентов не испытывает проблем с заданием."
    
    # Отображаем интерпретацию
    st.markdown(complaints_interpretation)
    st.markdown(complaint_rate_interpretation)
    
    # Добавляем рекомендации на основе уровня жалоб
    if complaints_total > 10 or card_data["complaint_rate"] > 0.05:
        st.markdown("""
        **Рекомендации при высоком уровне жалоб:**
        - Проверить формулировку задания на наличие ошибок или неточностей
        - Пересмотреть систему проверки ответов
        - Проанализировать конкретные жалобы студентов для выявления повторяющихся проблем
        - Рассмотреть возможность добавления подсказок или пояснений
        - В случае критического уровня жалоб - временно отключить карточку до исправления проблем
        """)

    # Отображаем текст жалоб, если он доступен
    if pd.notna(card_data.get("complaints_text")) and card_data["complaints_text"]:
        st.subheader("📝 Тексты жалоб")
        
        # Разделяем текст жалоб по строкам
        complaints_list = card_data["complaints_text"].strip().split('\n')
        
        # Отображаем каждую жалобу в отдельной карточке
        for i, complaint in enumerate(complaints_list):
            complaint = complaint.strip()
            if complaint:  # Проверяем, что строка не пустая
                st.markdown(f"""
                <div style="border:1px solid #d33682; border-radius:8px; padding:15px; margin-bottom:15px; background-color:#fdf6e3; color:#333333; font-size:16px;">
                    {complaint}
                </div>
                """, unsafe_allow_html=True)

def display_discrimination_analysis(card_data):
    """
    Отображает анализ дискриминативности для карточки
    
    Args:
        card_data: Series с данными карточки
    """
    st.markdown("## Анализ дискриминативности")
    
    # Визуализация дискриминативности
    fig = go.Figure()
    
    # Определяем цвет на основе значения
    color = "#9370db"
    if card_data["discrimination_avg"] > 0.5:
        color = "#32CD32"  # зеленый для высокой дискриминативности
    elif card_data["discrimination_avg"] < 0.2:
        color = "#ff6666"  # красный для низкой дискриминативности
    
    # Добавляем столбец для дискриминативности
    fig.add_trace(go.Bar(
        x=["Индекс дискриминативности"],
        y=[card_data["discrimination_avg"]],
        marker_color=color,
        text=[f"{card_data['discrimination_avg']:.3f}"],
        textposition="auto"
    ))
    
    # Добавляем горизонтальные линии для границ категорий
    fig.add_shape(
        type="line",
        x0=-0.5, y0=0.35, x1=0.5, y1=0.35,
        line=dict(color="green", width=2, dash="dash")
    )
    
    fig.add_shape(
        type="line",
        x0=-0.5, y0=0.15, x1=0.5, y1=0.15,
        line=dict(color="red", width=2, dash="dash")
    )
    
    # Добавляем аннотации для границ
    fig.add_annotation(
        x=0.5, y=0.35,
        text="Хорошая дискриминативность",
        showarrow=False,
        xanchor="left"
    )
    
    fig.add_annotation(
        x=0.5, y=0.15,
        text="Низкая дискриминативность",
        showarrow=False,
        xanchor="left"
    )
    
    # Настройка макета
    fig.update_layout(
        title="Индекс дискриминативности",
        yaxis=dict(
            title="Значение",
            range=[0, max(0.6, card_data["discrimination_avg"] * 1.2)]
        ),
        xaxis=dict(
            range=[-0.5, 1]
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Отображаем пояснения на основе дискриминативности
    st.markdown("### Интерпретация дискриминативности")
    
    discrimination_interpretation = ""
    if card_data["discrimination_avg"] > 0.35:
        discrimination_interpretation = f"Карточка имеет **высокую дискриминативность** ({card_data['discrimination_avg']:.3f}). Это указывает на то, что задание хорошо различает знающих и незнающих студентов."
    elif card_data["discrimination_avg"] > 0.15:
        discrimination_interpretation = f"Карточка имеет **среднюю дискриминативность** ({card_data['discrimination_avg']:.3f}). Это приемлемый показатель, но есть возможности для улучшения."
    else:
        discrimination_interpretation = f"Карточка имеет **низкую дискриминативность** ({card_data['discrimination_avg']:.3f}). Это указывает на то, что задание плохо различает знающих и незнающих студентов."
    
    # Отображаем интерпретацию
    st.markdown(discrimination_interpretation)
    
    # Добавляем рекомендации на основе уровня дискриминативности
    if card_data["discrimination_avg"] < 0.25:
        st.markdown("""
        **Рекомендации при низкой дискриминативности:**
        - Проверить, не слишком ли простое или слишком сложное задание
        - Пересмотреть варианты ответов, если это задание с выбором
        - Уточнить формулировку для исключения случайных угадываний
        - Рассмотреть возможность добавления дистракторов, если это тестовое задание
        - Оценить, насколько задание соответствует целям обучения
        """)
    
    # Визуализация идеальной дискриминативности
    st.markdown("### Идеальная дискриминативность")
    st.markdown("""
    Индекс дискриминативности показывает, насколько хорошо задание различает знающих и незнающих студентов.
    
    - **Высокая дискриминативность (>0.35)**: задание хорошо различает знающих и незнающих студентов
    - **Средняя дискриминативность (0.15-0.35)**: задание удовлетворительно различает знающих и незнающих студентов
    - **Низкая дискриминативность (<0.15)**: задание плохо различает знающих и незнающих студентов
    
    Идеальное значение дискриминативности находится в диапазоне 0.4-0.6. Слишком высокая или слишком низкая дискриминативность может указывать на проблемы с заданием.
    """)

def display_attempts_analysis(card_data):
    """
    Отображает анализ попыток для карточки
    
    Args:
        card_data: Series с данными карточки
    """
    st.markdown("## Анализ попыток")
    
    # Создаем колонки для разных показателей
    col1, col2 = st.columns(2)
    
    with col1:
        # Визуализация количества попыток
        fig = go.Figure()
        
        # Добавляем столбец для количества попыток
        fig.add_trace(go.Bar(
            x=["Количество попыток"],
            y=[card_data["total_attempts"]],
            marker_color="#4da6ff",
            text=[f"{card_data['total_attempts']:.0f}"],
            textposition="auto"
        ))
        
        # Настройка макета
        fig.update_layout(
            title="Общее количество попыток",
            yaxis=dict(
                title="Количество"
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Визуализация доли пытавшихся
        fig = go.Figure()
        
        # Добавляем столбец для доли пытавшихся
        fig.add_trace(go.Bar(
            x=["Доля пытавшихся"],
            y=[card_data["attempted_share"]],
            marker_color="#66c2a5",
            text=[f"{card_data['attempted_share']:.1%}"],
            textposition="auto"
        ))
        
        # Настройка макета
        fig.update_layout(
            title="Доля пытавшихся решить задание",
            yaxis=dict(
                title="Доля",
                tickformat=".0%",
                range=[0, 1]
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Отображаем пояснения на основе данных о попытках
    st.markdown("### Интерпретация данных о попытках")
    
    attempts_interpretation = ""
    if card_data["total_attempts"] > 500:
        attempts_interpretation = f"Карточка имеет **очень большое количество попыток** ({card_data['total_attempts']:.0f}), что говорит о высокой статистической значимости метрик."
    elif card_data["total_attempts"] > 100:
        attempts_interpretation = f"Карточка имеет **достаточное количество попыток** ({card_data['total_attempts']:.0f}) для статистической значимости метрик."
    elif card_data["total_attempts"] > 50:
        attempts_interpretation = f"Карточка имеет **среднее количество попыток** ({card_data['total_attempts']:.0f}). Метрики могут быть умеренно надежными."
    else:
        attempts_interpretation = f"Карточка имеет **малое количество попыток** ({card_data['total_attempts']:.0f}), что снижает статистическую значимость метрик."
    
    attempted_share_interpretation = ""
    if card_data["attempted_share"] > 0.95:
        attempted_share_interpretation = f"**Очень высокая доля пытавшихся** ({card_data['attempted_share']:.1%}) указывает на то, что практически все студенты пытаются решить это задание."
    elif card_data["attempted_share"] > 0.8:
        attempted_share_interpretation = f"**Высокая доля пытавшихся** ({card_data['attempted_share']:.1%}) говорит о том, что большинство студентов пытаются решить это задание."
    elif card_data["attempted_share"] > 0.6:
        attempted_share_interpretation = f"**Средняя доля пытавшихся** ({card_data['attempted_share']:.1%}) показывает, что задание пропускают некоторые студенты."
    else:
        attempted_share_interpretation = f"**Низкая доля пытавшихся** ({card_data['attempted_share']:.1%}) указывает на то, что многие студенты пропускают это задание."
    
    # Отображаем интерпретацию
    st.markdown(attempts_interpretation)
    st.markdown(attempted_share_interpretation)
    
    # Добавляем рекомендации на основе доли пытавшихся
    if card_data["attempted_share"] < 0.7:
        st.markdown("""
        **Рекомендации при низкой доле пытавшихся:**
        - Проверить позицию задания в уроке - возможно, оно находится в конце и студенты не доходят до него
        - Оценить, насколько задание интегрировано в общий контекст урока
        - Рассмотреть возможность перемещения задания в другую часть урока
        - Проанализировать, не выглядит ли задание слишком сложным или не связанным с предыдущим материалом
        """)

def display_card_status_form(card_data, engine):
    """
    Отображает форму для обновления статуса карточки
    
    Args:
        card_data: Series с данными карточки
        engine: SQLAlchemy engine для подключения к БД
    """
    st.markdown("## Управление статусом карточки")
    
    # Определяем статусы и их описания
    statuses = {
        "new": "Новая карточка, требуется анализ",
        "in_work": "Карточка в работе, проблемы анализируются",
        "ready_for_qc": "Карточка готова к проверке качества",
        "done": "Карточка проверена и одобрена",
        "wont_fix": "Проблемы с карточкой не будут исправлены"
    }
    
    # Получаем текущий статус
    current_status = card_data["status"]
    
    # Создаем форму для обновления статуса
    with st.form(key="update_status_form"):
        # Выбор нового статуса
        new_status = st.selectbox(
            "Статус карточки",
            options=list(statuses.keys()),
            format_func=lambda x: f"{x} - {statuses[x]}",
            index=list(statuses.keys()).index(current_status)
        )
        
        # Кнопка для сохранения статуса
        submit_button = st.form_submit_button(label="Обновить статус", type="primary")
        
        # Если кнопка нажата и статус изменился
        if submit_button and new_status != current_status:
            # Создаем оригинальный и отредактированный датафреймы для функции сохранения
            original_df = pd.DataFrame([card_data.to_dict()]).reset_index(drop=True)
            edited_df = original_df.copy()
            edited_df.loc[0, "status"] = new_status
            
            # Сохраняем изменения
            try:
                # Обновляем статус в таблице card_status
                core.save_status_changes(original_df, edited_df, engine)
                
                # Синхронизируем с card_assignments - обновляем или создаем назначение
                with engine.begin() as conn:
                    # Проверяем, есть ли уже назначение для этой карточки
                    card_id = int(card_data["card_id"])
                    assignment = conn.execute(text(
                        "SELECT assignment_id FROM card_assignments WHERE card_id = :card_id"
                    ), {"card_id": card_id}).fetchone()
                    
                    # Получаем текущего пользователя
                    user_id = st.session_state.get("user_id", 1)  # Если нет, используем 1 (админ)
                    
                    if assignment:
                        # Если есть назначение, обновляем статус
                        assignment_id = assignment[0]
                        conn.execute(text("""
                            UPDATE card_assignments
                            SET status = :status, updated_at = CURRENT_TIMESTAMP
                            WHERE assignment_id = :assignment_id
                        """), {
                            "status": new_status,
                            "assignment_id": assignment_id
                        })
                    else:
                        # Если нет назначения, создаем его
                        conn.execute(text("""
                            INSERT INTO card_assignments (card_id, user_id, status) 
                            VALUES (:card_id, :user_id, :status)
                        """), {
                            "card_id": card_id,
                            "user_id": user_id,
                            "status": new_status
                        })
                
                st.success(f"Статус карточки обновлен с '{current_status}' на '{new_status}'")
            except Exception as e:
                st.error(f"Ошибка при обновлении статуса: {str(e)}")

def get_card_order(card_id, engine):
    """
    Получает порядковый номер карточки (card_order) из базы данных
    
    Args:
        card_id: ID карточки
        engine: SQLAlchemy engine для подключения к БД
        
    Returns:
        card_order: Порядковый номер карточки или None, если не найден
    """
    try:
        # Запрос для получения card_order из таблицы cards_structure
        query = text("""
            SELECT card_order 
            FROM cards_structure 
            WHERE card_id = :card_id
        """)
        
        # Выполняем запрос
        with engine.connect() as conn:
            result = conn.execute(query, {"card_id": card_id})
            row = result.fetchone()
            
            if row and row[0]:
                return row[0]
            
            # Если не нашли, возвращаем None
            return None
    
    except Exception as e:
        st.error(f"Ошибка при получении card_order: {str(e)}")
        return None

def page_cards(df: pd.DataFrame, eng):
    """Страница с детальным анализом одной карточки"""
    
    # Получаем выбранные фильтры
    program_filter = st.session_state.get("filter_program")
    module_filter = st.session_state.get("filter_module")
    lesson_filter = st.session_state.get("filter_lesson")
    gz_filter = st.session_state.get("filter_gz")
    
    # Фильтруем данные по выбранным фильтрам
    df_filtered = core.apply_filters(df, ["program", "module", "lesson", "gz"])
    
    # Получаем card_id из параметра запроса или из состояния
    query_params = st.query_params
    card_id = None
    
    if "card_id" in query_params:
        card_id = query_params["card_id"]
        # Сохраняем card_id в состоянии для использования при обновлении страницы
        st.session_state["selected_card_id"] = card_id
    elif "selected_card_id" in st.session_state:
        card_id = st.session_state["selected_card_id"]
    
    # Если card_id не определен, предоставляем выбор из фильтрованных данных
    if card_id is None:
        # Создаем иерархический заголовок
        create_hierarchical_header(
            levels=["program", "module", "lesson", "gz"],
            values=[program_filter, module_filter, lesson_filter, gz_filter]
        )
        
        # Если данных нет, показываем предупреждение
        if df_filtered.empty:
            st.warning("Нет данных для выбранных фильтров. Выберите другие фильтры в боковой панели.")
            return
        
        # Сортируем карточки по риску для лучшего выбора
        df_sorted = df_filtered.sort_values("risk", ascending=False)
        
        st.header("🔍 Выберите карточку для анализа")
        
        # Создаем селектор карточек
        selected_card_id = st.selectbox(
            "Выберите карточку",
            options=df_sorted["card_id"].values,
            format_func=lambda x: f"ID: {x} - Риск: {df[df['card_id'] == x]['risk'].values[0]:.2f} - Тип: {df[df['card_id'] == x]['card_type'].values[0]}",
            key="card_selector"
        )
        
        # Сохраняем выбор в состоянии
        st.session_state["selected_card_id"] = selected_card_id
        
        # Обновляем параметр URL для сохранения выбора при обновлении страницы
        st.query_params["card_id"] = selected_card_id
        
        # Перезагружаем страницу для применения выбора
        st.rerun()
    
    # Получаем данные выбранной карточки
    card_data = df[df["card_id"] == int(card_id)]
    
    # Проверяем, есть ли данные для карточки
    if card_data.empty:
        st.error(f"Карточка с ID {card_id} не найдена в данных.")
        return
    
    # Получаем Series с данными карточки
    card_data = card_data.iloc[0]
    
    # Добавляем метрику разницы между success_rate и first_try_success_rate
    card_data["success_diff"] = card_data["success_rate"] - card_data["first_try_success_rate"]
    
    # Проверяем, есть ли поле trickiness_level, если нет - вычисляем
    if "trickiness_level" not in card_data:
        card_data["trickiness_level"] = core.get_trickiness_level(card_data)
    
    # Получаем card_order из базы данных
    card_order = get_card_order(int(card_data["card_id"]), eng)
    if card_order is not None:
        card_data["card_order"] = card_order
    
    # Создаем иерархический заголовок с указанием карточки
    create_hierarchical_header(
        levels=["program", "module", "lesson", "gz", "card"],
        values=[card_data["program"], card_data["module"], card_data["lesson"], card_data["gz"], f"Карточка {int(card_data['card_id'])}"]
    )
    
    # Отображаем ссылки на карточку и ГЗ
    add_card_links(card_data)
    
    # Отображаем основную информацию о карточке
    display_card_details(card_data)
    
    # Отображаем привязку к курсам, передаем DataFrame целиком
    display_course_links(int(card_data["card_id"]), eng, df)
    
    # Добавляем разделитель
    st.markdown("---")
    
    # Создаем вкладки для разных аспектов анализа
    tabs = st.tabs([
        "📊 Компоненты риска", 
        "✅ Анализ успешности", 
        "⚠️ Анализ жалоб", 
        "🔍 Анализ дискриминативности",
        "🔄 Анализ попыток"
    ])
    
    # Наполняем вкладки соответствующим содержимым
    with tabs[0]:
        display_risk_components(card_data)
    
    with tabs[1]:
        display_success_analysis(card_data)
    
    with tabs[2]:
        display_complaints_analysis(card_data)
    
    with tabs[3]:
        display_discrimination_analysis(card_data)
    
    with tabs[4]:
        display_attempts_analysis(card_data)
    
    # Добавляем разделитель
    st.markdown("---")
    
    # Отображаем форму для обновления статуса карточки
    display_card_status_form(card_data, eng)
    
    # Добавляем общие рекомендации на основе риска
    st.markdown("## Общие рекомендации")
    
    risk_level = card_data["risk"]
    
    if risk_level > 0.75:
        st.error("""
        ### Карточка с критически высоким риском
        
        **Рекомендуемые действия:**
        - Временно отключить карточку до исправления проблем
        - Провести полный анализ причин высокого риска
        - Пересмотреть формулировку, систему проверки ответов и контекст карточки
        - Провести тестирование с фокус-группой перед повторным включением
        """)
    elif risk_level > 0.5:
        st.warning("""
        ### Карточка с высоким риском
        
        **Рекомендуемые действия:**
        - Проанализировать причины высокого риска по отдельным метрикам
        - Внести необходимые исправления в содержание карточки
        - Уточнить формулировку и добавить подсказки при необходимости
        - Отслеживать динамику метрик после внесения изменений
        """)
    elif risk_level > 0.25:
        st.info("""
        ### Карточка с умеренным риском
        
        **Рекомендуемые действия:**
        - Обратить внимание на метрики с наибольшим вкладом в риск
        - Рассмотреть возможности для улучшения выявленных проблемных аспектов
        - Включить карточку в план доработок при наличии ресурсов
        """)
    else:
        st.success("""
        ### Карточка с низким риском
        
        **Статус:**
        - Карточка работает хорошо и не требует срочных изменений
        - Можно рассмотреть возможности для дальнейшей оптимизации отдельных аспектов
        - Продолжать мониторинг метрик в рамках обычного процесса
        """)

    # Отображаем метрику времени на карточку, если оно доступно
    if pd.notna(card_data.get("time_median")):
        st.subheader("⏱️ Время выполнения")
        st.metric(
            label="Медианное время на карточку (мин)",
            value=f"{card_data['time_median']:.1f}"
        )
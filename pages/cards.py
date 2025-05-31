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
import os
import requests
from urllib.parse import quote
import io
from datetime import datetime

import core
from components.utils import create_hierarchical_header, add_gz_links, add_card_links
from components.metrics import display_metrics_row, display_status_chart, display_risk_distribution
from components.charts import display_risk_bar_chart, display_metrics_comparison, display_success_complaints_chart



# Функция для отображения подробной информации о карточке
def get_screenshot_url(card_id):
    """
    Формирует URL для скриншота карточки из Yandex Object Storage
    
    Args:
        card_id: ID карточки
    
    Returns:
        str: URL скриншота
    """
    return f"https://snufffkin-pics.website.yandexcloud.net/Refactor/image/{card_id}.png"

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
        risk_value = card_data.get('risk')
        risk_display = f"{risk_value:.3f}" if pd.notna(risk_value) else "N/A"

        card_info = {
            "ID карточки": int(card_data["card_id"]),
            "Тип карточки": card_data.get("card_type", "Не указан"), # Используем .get для безопасности
            "Программа": card_data.get("program_name", "N/A"),
            "Модуль": card_data.get("module_name", "N/A"),
            "Урок": card_data.get("lesson_name", "N/A"),
            "Группа заданий": card_data.get("gz_name", "N/A"),
            "Текущий риск": risk_display
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
        
        # Безопасное получение и форматирование метрик
        sr = card_data.get('success_rate')
        ft_sr = card_data.get('first_try_success_rate')
        s_diff = card_data.get('success_diff') 
        da = card_data.get('discrimination_avg')
        
        # Безопасное получение complaints_total
        ct_raw = card_data.get('complaints_total')
        if pd.notna(ct_raw):
            ct = ct_raw
        else:
            cr_for_calc = card_data.get('complaint_rate')
            ta_for_calc = card_data.get('total_attempts')
            if pd.notna(cr_for_calc) and pd.notna(ta_for_calc):
                ct = cr_for_calc * ta_for_calc
            else:
                ct = np.nan # Если не можем вычислить, ставим NaN
                
        cr = card_data.get('complaint_rate')
        as_ = card_data.get('attempted_share')
        ta = card_data.get('total_attempts')

        metrics = {
            "Успешность": f"{sr:.1%}" if pd.notna(sr) else "N/A",
            "Успешность с первой попытки": f"{ft_sr:.1%}" if pd.notna(ft_sr) else "N/A",
            "Разница": f"{s_diff:.1%}" if pd.notna(s_diff) else "N/A",
            "Уровень подлости": f"<span style='color:{trickiness_color};font-weight:bold;'>{trickiness_text}</span>", # trickiness_text уже обработан
            "Дискриминативность": f"{da:.3f}" if pd.notna(da) else "N/A",
            "Количество жалоб": f"{ct:.0f}" if pd.notna(ct) else "N/A",
            "Доля жалоб": f"{cr:.1%}" if pd.notna(cr) else "N/A",
            "Доля пытавшихся": f"{as_:.1%}" if pd.notna(as_) else "N/A",
            "Количество попыток": f"{ta:.0f}" if pd.notna(ta) else "N/A"
        }
        
        for key, value in metrics.items():
            if key == "Уровень подлости":
                st.markdown(f"**{key}:** {value}", unsafe_allow_html=True)
            else:
                st.markdown(f"**{key}:** {value}")
    
    # Отображаем скриншот карточки под основной информацией
    st.markdown("### 📷 Скриншот карточки")
    screenshot_url = get_screenshot_url(int(card_data["card_id"]))
    
    # Создаем контейнер для скриншота с адаптивным размером
    st.markdown(f"""
        <div style="border: 1px solid #ccc; border-radius: 5px; padding: 10px; margin: 10px 0; background-color: white;">
            <img src="{screenshot_url}" style="display: block; max-width: 100%; margin: 0 auto;" alt="Скриншот карточки {int(card_data['card_id'])}">
        </div>
    """, unsafe_allow_html=True)
    
    # Добавляем прямую ссылку на скриншот
    st.markdown(f"[🔗 Открыть скриншот в новом окне]({screenshot_url})")

def display_export_field_selector():
    """
    Отображает интерфейс для выбора полей экспорта
    
    Returns:
        dict: Словарь с выбранными индивидуальными полями
    """
    # Определяем все доступные поля по группам
    field_groups = {
        'basic': {
            'title': '📋 Основная информация',
            'fields': {
                'card_id': 'ID карточки',
                'card_type': 'Тип карточки',
                'program_name': 'Название программы',
                'module_name': 'Название модуля',
                'lesson_name': 'Название урока',
                'gz_name': 'Название группы заданий',
                'card_order': 'Порядковый номер карточки',
                'card_url': 'URL карточки в редакторе',
                'status': 'Статус карточки'
            }
        },
        'metrics': {
            'title': '📊 Ключевые метрики',
            'fields': {
                'success_rate': 'Общая успешность',
                'first_try_success_rate': 'Успешность с первой попытки',
                'success_diff': 'Разница в успешности',
                'discrimination_avg': 'Индекс дискриминативности',
                'complaint_rate': 'Доля жалоб',
                'complaints_total': 'Количество жалоб',
                'attempted_share': 'Доля пытавшихся',
                'total_attempts': 'Общее количество попыток',
                'time_median': 'Медианное время (мин)',
                'trickiness_level': 'Уровень подлости'
            }
        },
        'risk': {
            'title': '⚠️ Компоненты риска',
            'fields': {
                'risk_discrimination': 'Риск по дискриминативности',
                'risk_success_rate': 'Риск по успешности',
                'risk_trickiness': 'Риск по подлости',
                'risk_complaints': 'Риск по жалобам',
                'risk_attempted_share': 'Риск по доле пытавшихся',
                'weighted_avg_risk': 'Взвешенный средний риск',
                'max_risk': 'Максимальный риск',
                'confidence_factor': 'Коэффициент доверия',
                'final_risk': 'Итоговый риск'
            }
        },
        'additional': {
            'title': '🔗 Дополнительные данные',
            'fields': {
                'card_public_url': 'Публичная ссылка на карточку',
                'screenshot_url': 'Ссылка на скриншот',
                'embedding': 'Векторное представление (embedding)'
            }
        },
        'timestamps': {
            'title': '🕒 Временные метки',
            'fields': {
                'updated_at': 'Дата последнего обновления',
                'updated_by': 'Кем обновлено',
                'export_timestamp': 'Время экспорта'
            }
        },
        'complaints_text': {
            'title': '💬 Тексты жалоб',
            'fields': {
                'complaints_text': 'Полные тексты жалоб'
            }
        }
    }
    
    # Инициализируем состояние по умолчанию для всех полей
    force_update_key = st.session_state.get('export_force_update', 0)
    
    # Создаем список всех полей
    all_field_keys = []
    for group_key, group_data in field_groups.items():
        for field_key in group_data['fields'].keys():
            all_field_keys.append(f"field_{field_key}")
    
    # Устанавливаем значения по умолчанию, если их нет в session_state
    for field_key in all_field_keys:
        if field_key not in st.session_state:
            st.session_state[field_key] = True
    
    st.subheader("🔧 Настройки экспорта")
    
    # Глобальные кнопки управления
    col_global1, col_global2, col_global3 = st.columns([1, 1, 2])
    with col_global1:
        if st.button("✅ Выбрать все поля", key="select_all_fields_global"):
            st.session_state.export_force_update = force_update_key + 1
            for field_key in all_field_keys:
                st.session_state[field_key] = True
            st.rerun()
    
    with col_global2:
        if st.button("❌ Снять все поля", key="deselect_all_fields_global"):
            st.session_state.export_force_update = force_update_key + 1
            for field_key in all_field_keys:
                st.session_state[field_key] = False
            st.rerun()
    
    with col_global3:
        # Показываем счетчик выбранных полей
        selected_count = sum(1 for field_key in all_field_keys if st.session_state.get(field_key, True))
        st.info(f"Выбрано полей: {selected_count}/{len(all_field_keys)}")
    
    st.markdown("---")
    
    # Создаем группы полей
    selected_fields = {}
    
    for group_key, group_data in field_groups.items():
        with st.expander(group_data['title'], expanded=False):
            # Кнопки для группы
            col_group1, col_group2, col_group3 = st.columns([1, 1, 2])
            
            group_field_keys = [f"field_{field_key}" for field_key in group_data['fields'].keys()]
            
            with col_group1:
                if st.button(f"✅ Все", key=f"select_group_{group_key}"):
                    st.session_state.export_force_update = force_update_key + 1
                    for field_key in group_field_keys:
                        st.session_state[field_key] = True
                    st.rerun()
            
            with col_group2:
                if st.button(f"❌ Ничего", key=f"deselect_group_{group_key}"):
                    st.session_state.export_force_update = force_update_key + 1
                    for field_key in group_field_keys:
                        st.session_state[field_key] = False
                    st.rerun()
            
            with col_group3:
                # Показываем счетчик для группы
                group_selected_count = sum(1 for field_key in group_field_keys if st.session_state.get(field_key, True))
                st.caption(f"Выбрано: {group_selected_count}/{len(group_field_keys)}")
            
            # Чекбоксы для полей в группе
            for field_key, field_description in group_data['fields'].items():
                session_key = f"field_{field_key}"
                checkbox_key = f"{session_key}_{force_update_key}"
                
                selected = st.checkbox(
                    field_description,
                    value=st.session_state.get(session_key, True),
                    key=checkbox_key,
                    help=f"Включить поле '{field_key}' в экспорт"
                )
                
                selected_fields[field_key] = selected
                st.session_state[session_key] = selected
    
    return selected_fields

def prepare_card_data_for_csv(card_data, engine, field_selection=None):
    """
    Подготавливает данные карточки для экспорта в CSV
    
    Args:
        card_data: Series с данными карточки
        engine: SQLAlchemy engine для подключения к БД
        field_selection: dict с выбранными индивидуальными полями для экспорта
        
    Returns:
        pd.DataFrame: DataFrame с данными для экспорта
    """
    # Если не указан выбор полей, включаем все поля по умолчанию
    if field_selection is None:
        # Все доступные поля по умолчанию
        field_selection = {
            'card_id': True, 'card_type': True, 'program_name': True, 'module_name': True,
            'lesson_name': True, 'gz_name': True, 'card_order': True, 'card_url': True,
            'status': True, 'success_rate': True, 'first_try_success_rate': True,
            'success_diff': True, 'discrimination_avg': True, 'complaint_rate': True,
            'complaints_total': True, 'attempted_share': True, 'total_attempts': True,
            'time_median': True, 'trickiness_level': True, 'risk_discrimination': True,
            'risk_success_rate': True, 'risk_trickiness': True, 'risk_complaints': True,
            'risk_attempted_share': True, 'weighted_avg_risk': True, 'max_risk': True,
            'confidence_factor': True, 'final_risk': True, 'card_public_url': True,
            'screenshot_url': True, 'embedding': True, 'updated_at': True,
            'updated_by': True, 'export_timestamp': True, 'complaints_text': True
        }
    
    # Получаем конфигурацию для расчета компонентов риска
    config = core.get_config()
    card_dict = card_data.to_dict()
    
    # Рассчитываем компоненты риска только если нужны
    risk_discr = risk_success = risk_trickiness = risk_complaints = risk_attempted = np.nan
    weighted_avg_risk = max_risk = confidence_factor_val = final_risk_val = np.nan
    
    if field_selection.get('risk', False):
        # Рассчитываем компоненты риска
        d_avg = card_data.get("discrimination_avg")
        s_rate = card_data.get("success_rate")
        
        risk_discr = core.discrimination_risk_score(d_avg) if pd.notna(d_avg) else np.nan
        risk_success = core.success_rate_risk_score(s_rate) if pd.notna(s_rate) else np.nan
        risk_trickiness = core.trickiness_risk_score(card_dict)
        risk_complaints = core.complaint_risk_score(card_dict)
        risk_attempted = core.attempted_share_risk_score(card_data.get("attempted_share")) if pd.notna(card_data.get("attempted_share")) else np.nan
        
        # Рассчитываем взвешенные риски
        WEIGHT_DISCRIMINATION = config["weights"]["discrimination"]
        WEIGHT_SUCCESS_RATE = config["weights"]["success_rate"]
        WEIGHT_TRICKINESS = config["weights"].get("trickiness", 0.15)
        WEIGHT_COMPLAINT_RATE = config["weights"]["complaint_rate"]
        WEIGHT_ATTEMPTED = config["weights"]["attempted"]
        
        # Вычисляем взвешенное среднее
        weighted_sum = 0
        total_weight = 0
        if pd.notna(risk_discr): weighted_sum += WEIGHT_DISCRIMINATION * risk_discr; total_weight += WEIGHT_DISCRIMINATION
        if pd.notna(risk_success): weighted_sum += WEIGHT_SUCCESS_RATE * risk_success; total_weight += WEIGHT_SUCCESS_RATE
        if pd.notna(risk_trickiness): weighted_sum += WEIGHT_TRICKINESS * risk_trickiness; total_weight += WEIGHT_TRICKINESS
        if pd.notna(risk_complaints): weighted_sum += WEIGHT_COMPLAINT_RATE * risk_complaints; total_weight += WEIGHT_COMPLAINT_RATE
        if pd.notna(risk_attempted): weighted_sum += WEIGHT_ATTEMPTED * risk_attempted; total_weight += WEIGHT_ATTEMPTED
        
        weighted_avg_risk = (weighted_sum / total_weight) if total_weight > 0 else np.nan
        
        # Определяем максимальный риск
        all_risks_list = [r for r in [risk_discr, risk_success, risk_trickiness, risk_complaints, risk_attempted] if pd.notna(r)]
        max_risk = np.max(all_risks_list) if all_risks_list else np.nan
        
        # Рассчитываем итоговый риск
        ta_for_confidence = card_data.get("total_attempts")
        if pd.notna(ta_for_confidence):
            significance_threshold = config["stats"]["significance_threshold"]
            if significance_threshold > 0:
                confidence_factor_val = min(ta_for_confidence / significance_threshold, 1.0)
            else:
                confidence_factor_val = 1.0
        
        final_risk_val = card_data.get('risk', np.nan)
    
    # Безопасное получение complaints_total
    ct_raw = card_data.get('complaints_total')
    if pd.notna(ct_raw):
        complaints_total = ct_raw
    else:
        cr_for_calc = card_data.get('complaint_rate')
        ta_for_calc = card_data.get('total_attempts')
        if pd.notna(cr_for_calc) and pd.notna(ta_for_calc):
            complaints_total = cr_for_calc * ta_for_calc
        else:
            complaints_total = np.nan
    
    # Получаем дополнительные данные если нужны
    screenshot_url = ""
    embedding_data = None
    
    if field_selection.get('screenshot_url', False) or field_selection.get('embedding', False):
        card_id_for_additional = int(card_data.get("card_id", 0))
        
        if field_selection.get('screenshot_url', False):
            screenshot_url = get_screenshot_url(card_id_for_additional)
        
        if field_selection.get('embedding', False):
            # Получаем embedding из базы данных
            try:
                with engine.connect() as conn:
                    embedding_query = text("""
                        SELECT embedding 
                        FROM cards_content 
                        WHERE card_id = :card_id
                    """)
                    result = conn.execute(embedding_query, {"card_id": card_id_for_additional})
                    row = result.fetchone()
                    if row and row[0] is not None:
                        # Конвертируем vector в строку для CSV
                        try:
                            vector_str = str(row[0])
                            if vector_str.startswith('[') and vector_str.endswith(']'):
                                embedding_data = vector_str[1:-1]  # Убираем [ и ]
                            else:
                                embedding_data = vector_str
                        except Exception as vector_error:
                            print(f"Ошибка при обработке вектора: {vector_error}")
                            embedding_data = str(row[0])
            except Exception as e:
                print(f"Ошибка при получении embedding для карточки {card_id_for_additional}: {str(e)}")
                embedding_data = None
    
    # Подготавливаем данные для экспорта на основе выбранных полей
    export_data = {}
    
    # Основная информация
    if field_selection.get('card_id', False):
        export_data['card_id'] = int(card_data.get("card_id", 0))
    if field_selection.get('card_type', False):
        export_data['card_type'] = card_data.get("card_type", "")
    if field_selection.get('program_name', False):
        export_data['program_name'] = card_data.get("program_name", "")
    if field_selection.get('module_name', False):
        export_data['module_name'] = card_data.get("module_name", "")
    if field_selection.get('lesson_name', False):
        export_data['lesson_name'] = card_data.get("lesson_name", "")
    if field_selection.get('gz_name', False):
        export_data['gz_name'] = card_data.get("gz_name", "")
    if field_selection.get('card_order', False):
        export_data['card_order'] = card_data.get("card_order", "")
    if field_selection.get('card_url', False):
        export_data['card_url'] = card_data.get("card_url", "")
    if field_selection.get('status', False):
        export_data['status'] = card_data.get("status", "")
    
    # Основные метрики
    if field_selection.get('success_rate', False):
        export_data['success_rate'] = card_data.get("success_rate")
    if field_selection.get('first_try_success_rate', False):
        export_data['first_try_success_rate'] = card_data.get("first_try_success_rate")
    if field_selection.get('success_diff', False):
        export_data['success_diff'] = card_data.get("success_diff")
    if field_selection.get('discrimination_avg', False):
        export_data['discrimination_avg'] = card_data.get("discrimination_avg")
    if field_selection.get('complaint_rate', False):
        export_data['complaint_rate'] = card_data.get("complaint_rate")
    if field_selection.get('complaints_total', False):
        export_data['complaints_total'] = complaints_total
    if field_selection.get('attempted_share', False):
        export_data['attempted_share'] = card_data.get("attempted_share")
    if field_selection.get('total_attempts', False):
        export_data['total_attempts'] = card_data.get("total_attempts")
    if field_selection.get('time_median', False):
        export_data['time_median'] = card_data.get("time_median")
    if field_selection.get('trickiness_level', False):
        export_data['trickiness_level'] = card_data.get("trickiness_level", 0)
    
    # Компоненты риска
    if field_selection.get('risk_discrimination', False):
        export_data['risk_discrimination'] = risk_discr
    if field_selection.get('risk_success_rate', False):
        export_data['risk_success_rate'] = risk_success
    if field_selection.get('risk_trickiness', False):
        export_data['risk_trickiness'] = risk_trickiness
    if field_selection.get('risk_complaints', False):
        export_data['risk_complaints'] = risk_complaints
    if field_selection.get('risk_attempted_share', False):
        export_data['risk_attempted_share'] = risk_attempted
    if field_selection.get('weighted_avg_risk', False):
        export_data['weighted_avg_risk'] = weighted_avg_risk
    if field_selection.get('max_risk', False):
        export_data['max_risk'] = max_risk
    if field_selection.get('confidence_factor', False):
        export_data['confidence_factor'] = confidence_factor_val
    if field_selection.get('final_risk', False):
        export_data['final_risk'] = final_risk_val
    
    # Дополнительные данные
    if field_selection.get('card_public_url', False):
        export_data['card_public_url'] = card_data.get("card_public_url", "")
    if field_selection.get('screenshot_url', False):
        export_data['screenshot_url'] = screenshot_url
    if field_selection.get('embedding', False):
        export_data['embedding'] = embedding_data
    
    # Временные метки
    if field_selection.get('updated_at', False):
        export_data['updated_at'] = card_data.get("updated_at", "")
    if field_selection.get('updated_by', False):
        export_data['updated_by'] = card_data.get("updated_by", "")
    if field_selection.get('export_timestamp', False):
        export_data['export_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Тексты жалоб
    if field_selection.get('complaints_text', False):
        complaints_text = card_data.get("complaints_text", "")
        export_data['complaints_text'] = complaints_text.strip() if pd.notna(complaints_text) else ""
    
    # Создаем DataFrame
    df_export = pd.DataFrame([export_data])
    
    return df_export

def display_csv_download_button(card_data, engine, field_selection):
    """
    Отображает кнопку для скачивания данных карточки в CSV формате
    
    Args:
        card_data: Series с данными карточки
        engine: SQLAlchemy engine для подключения к БД
        field_selection: dict с выбранными индивидуальными полями для экспорта
    """
    try:
        # Подготавливаем данные для экспорта
        df_export = prepare_card_data_for_csv(card_data, engine, field_selection)
        
        # Проверяем, есть ли данные для экспорта
        if df_export.empty or df_export.shape[1] == 0:
            st.warning("Выберите хотя бы одно поле для экспорта")
            return
        
        # Конвертируем в CSV
        csv_buffer = io.StringIO()
        df_export.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_data = csv_buffer.getvalue()
        
        # Формируем имя файла
        card_id = int(card_data.get("card_id", 0))
        selected_fields = [k for k, v in field_selection.items() if v]
        field_count = len(selected_fields)
        
        # Сокращаем имя файла, чтобы оно не было слишком длинным
        if field_count <= 5:
            fields_suffix = "_".join(selected_fields[:5])
        else:
            fields_suffix = f"{field_count}_fields"
        
        filename = f"card_{card_id}_{fields_suffix}.csv"
        
        # Отображаем кнопку скачивания
        st.download_button(
            label=f"📥 Скачать выбранные данные ({field_count} полей)",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            help=f"Экспортировать {field_count} выбранных полей"
        )
        
    except Exception as e:
        st.error(f"Ошибка при подготовке данных для экспорта: {str(e)}")



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
        key_columns = ['program_name', 'module_name', 'lesson_name']
        if all(col in matching_cards.columns for col in key_columns):
            grouped = matching_cards.groupby(key_columns)
            
            # Отображаем данные
            st.markdown("### Привязка к урокам")
            for (program, module, lesson), group in grouped:
                with st.expander(f"📚 {program} / {module} / {lesson}", expanded=False):
                    # Создаем таблицу
                    for _, row in group.iterrows():
                        gz = row.get('gz_name', 'Неизвестно')
                        card_type = row.get('card_type', 'Неизвестно')
                        
                        # Формируем URL для перехода к ГЗ
                        gz_url_params = {
                            "page": "gz", # Добавляем целевую страницу
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
    
    config = core.get_config()
    card_dict = card_data.to_dict()

    # Безопасно получаем значения метрик из card_data
    d_avg = card_data.get("discrimination_avg")
    s_rate = card_data.get("success_rate")
    # trickiness_level и success_diff уже должны быть в card_data с обработкой None/NaN из page_cards
    # complaints_total и attempted_share также используются в core.complaint_risk_score и core.attempted_share_risk_score
    # которые, будем надеяться, устойчивы к None в card_dict (они ожидают DataFrame)
    
    # Функции core.*_risk_score должны возвращать число или NaN, если входные данные некорректны
    risk_discr = core.discrimination_risk_score(d_avg) if pd.notna(d_avg) else np.nan
    risk_success = core.success_rate_risk_score(s_rate) if pd.notna(s_rate) else np.nan
    risk_trickiness = core.trickiness_risk_score(card_dict) # Предполагаем, что эта функция устойчива или вернет NaN
    risk_complaints = core.complaint_risk_score(card_dict) # Аналогично
    risk_attempted = core.attempted_share_risk_score(card_data.get("attempted_share")) if pd.notna(card_data.get("attempted_share")) else np.nan

    # Определяем максимальный риск, игнорируя NaN
    all_risks_list = [r for r in [risk_discr, risk_success, risk_trickiness, risk_complaints, risk_attempted] if pd.notna(r)]
    max_risk = np.max(all_risks_list) if all_risks_list else np.nan
    
    WEIGHT_DISCRIMINATION = config["weights"]["discrimination"]
    WEIGHT_SUCCESS_RATE = config["weights"]["success_rate"]
    WEIGHT_TRICKINESS = config["weights"].get("trickiness", 0.15)
    WEIGHT_COMPLAINT_RATE = config["weights"]["complaint_rate"]
    WEIGHT_ATTEMPTED = config["weights"]["attempted"]
    
    # Рассчитываем взвешенное среднее, обрабатывая NaN
    weighted_sum = 0
    total_weight = 0
    if pd.notna(risk_discr): weighted_sum += WEIGHT_DISCRIMINATION * risk_discr; total_weight += WEIGHT_DISCRIMINATION
    if pd.notna(risk_success): weighted_sum += WEIGHT_SUCCESS_RATE * risk_success; total_weight += WEIGHT_SUCCESS_RATE
    if pd.notna(risk_trickiness): weighted_sum += WEIGHT_TRICKINESS * risk_trickiness; total_weight += WEIGHT_TRICKINESS
    if pd.notna(risk_complaints): weighted_sum += WEIGHT_COMPLAINT_RATE * risk_complaints; total_weight += WEIGHT_COMPLAINT_RATE
    if pd.notna(risk_attempted): weighted_sum += WEIGHT_ATTEMPTED * risk_attempted; total_weight += WEIGHT_ATTEMPTED
    
    weighted_avg_risk = (weighted_sum / total_weight) if total_weight > 0 else np.nan

    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.markdown("---")
        st.markdown("### Риск по метрикам")
        
        def risk_category_safe(risk_value):
            if not pd.notna(risk_value):
                return "N/A", "grey"
            if risk_value > 0.75: return "Критический", "red"
            elif risk_value > 0.5: return "Высокий", "orange"
            elif risk_value > 0.25: return "Умеренный", "gold"
            else: return "Низкий", "green"
        
        risks_map = {
            "Дискриминативность": risk_discr,
            "Успешность": risk_success,
            "Подлость": risk_trickiness,
            "Количество жалоб": risk_complaints,
            "Доля пытавшихся": risk_attempted
        }
        
        for metric, risk_val in risks_map.items():
            category, color = risk_category_safe(risk_val)
            risk_display_text = f"{risk_val:.3f}" if pd.notna(risk_val) else "N/A"
            st.markdown(f"**{metric}**: {risk_display_text} - <span style='color:{color};'>{category}</span>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### Формула расчета")
        
        # 1. Вычисляем все необходимые значения
        min_threshold = 0
        if pd.notna(max_risk): # max_risk вычислен ранее
            if max_risk > config["risk_thresholds"]["critical"]: 
                min_threshold = config["risk_thresholds"]["min_for_critical"]
            elif max_risk > config["risk_thresholds"]["high"]: 
                min_threshold = config["risk_thresholds"]["min_for_high"]
        
        alpha = config["risk_thresholds"]["alpha_weight_avg"]
        combined_risk_val = np.nan # Используем суффикс _val для вычисленных значений
        if pd.notna(weighted_avg_risk) and pd.notna(max_risk):
            combined_risk_val = alpha * weighted_avg_risk + (1 - alpha) * max_risk
        
        raw_risk_val = np.nan
        # Убедимся, что min_threshold это число для np.max, если weighted_avg_risk или combined_risk_val - NaN
        # np.nanmax игнорирует NaN, но если все NaN, вернет ошибку. Лучше собрать список не-NaN значений.
        raw_risk_components = [r for r in [weighted_avg_risk, combined_risk_val, float(min_threshold)] if pd.notna(r)]
        if raw_risk_components:
            raw_risk_val = np.max(raw_risk_components)
            
        ta_for_confidence = card_data.get("total_attempts")
        confidence_factor_val = np.nan
        if pd.notna(ta_for_confidence):
            significance_threshold = config["stats"]["significance_threshold"]
            if significance_threshold > 0: # Избегаем деления на ноль
                confidence_factor_val = min(ta_for_confidence / significance_threshold, 1.0)
            else:
                confidence_factor_val = 1.0 # Если порог 0, считаем доверие максимальным
        
        final_risk_val = np.nan
        if pd.notna(raw_risk_val) and pd.notna(confidence_factor_val):
            neutral_risk_value = config["stats"]["neutral_risk_value"]
            final_risk_val = raw_risk_val * confidence_factor_val + neutral_risk_value * (1 - confidence_factor_val)

        # 2. Теперь форматируем и выводим
        display_wavr = f"{weighted_avg_risk:.3f}" if pd.notna(weighted_avg_risk) else "N/A"
        st.markdown(f"**Взвешенное среднее**: {display_wavr}")
        
        display_maxr = f"{max_risk:.3f}" if pd.notna(max_risk) else "N/A"
        st.markdown(f"**Максимальный риск**: {display_maxr}")
        
        st.markdown(f"**Минимальный порог**: {min_threshold:.3f}") 
        
        display_combr = f"{combined_risk_val:.3f}" if pd.notna(combined_risk_val) else "N/A"
        st.markdown(f"**Комбинированный риск**: {display_combr}")
        
        display_rawr = f"{raw_risk_val:.3f}" if pd.notna(raw_risk_val) else "N/A"
        st.markdown(f"**Сырой риск**: {display_rawr}")
        
        display_conff = f"{confidence_factor_val:.2f}" if pd.notna(confidence_factor_val) else "N/A"
        st.markdown(f"**Коэффициент доверия**: {display_conff}")
        
        display_finalr = f"{final_risk_val:.3f}" if pd.notna(final_risk_val) else "N/A"
        st.markdown(f"**Итоговый риск**: {display_finalr}")
    
    with col2:
        risks_df_data = {
            "Метрика": [], "Риск": [], "Вес": [], "Взвешенный риск": []
        }
        if pd.notna(risk_discr): 
            risks_df_data["Метрика"].append("Дискриминативность"); risks_df_data["Риск"].append(risk_discr); risks_df_data["Вес"].append(WEIGHT_DISCRIMINATION); risks_df_data["Взвешенный риск"].append(WEIGHT_DISCRIMINATION * risk_discr)
        if pd.notna(risk_success): 
            risks_df_data["Метрика"].append("Успешность"); risks_df_data["Риск"].append(risk_success); risks_df_data["Вес"].append(WEIGHT_SUCCESS_RATE); risks_df_data["Взвешенный риск"].append(WEIGHT_SUCCESS_RATE * risk_success)
        if pd.notna(risk_trickiness): 
            risks_df_data["Метрика"].append("Подлость"); risks_df_data["Риск"].append(risk_trickiness); risks_df_data["Вес"].append(WEIGHT_TRICKINESS); risks_df_data["Взвешенный риск"].append(WEIGHT_TRICKINESS * risk_trickiness)
        if pd.notna(risk_complaints): 
            risks_df_data["Метрика"].append("Жалобы"); risks_df_data["Риск"].append(risk_complaints); risks_df_data["Вес"].append(WEIGHT_COMPLAINT_RATE); risks_df_data["Взвешенный риск"].append(WEIGHT_COMPLAINT_RATE * risk_complaints)
        if pd.notna(risk_attempted): 
            risks_df_data["Метрика"].append("Попытки (доля)"); risks_df_data["Риск"].append(risk_attempted); risks_df_data["Вес"].append(WEIGHT_ATTEMPTED); risks_df_data["Взвешенный риск"].append(WEIGHT_ATTEMPTED * risk_attempted)
        
        if risks_df_data["Метрика"]:
            risks_df = pd.DataFrame(risks_df_data)
            risks_df = risks_df.sort_values(by="Взвешенный риск", ascending=False)
            fig = px.bar(
                risks_df,
                x="Метрика",
                y="Взвешенный риск",
                color="Риск",
                color_continuous_scale="RdYlGn_r",
                title="Вклад метрик в общий риск",
                labels={"Взвешенный риск": "Вклад в риск"},
                text=risks_df["Риск"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
            )
            if pd.notna(weighted_avg_risk):
                fig.add_hline(y=weighted_avg_risk, line_dash="dash", line_color="blue", 
                              annotation_text=f"Взвешенное среднее: {weighted_avg_risk:.2f}", 
                              annotation_position="top right")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных для построения графика вклада метрик в риск.")

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
    # card_data["success_diff"] = card_data["success_rate"] - card_data["first_try_success_rate"] # Старая версия
    if pd.notna(card_data.get("success_rate")) and pd.notna(card_data.get("first_try_success_rate")):
        card_data["success_diff"] = card_data["success_rate"] - card_data["first_try_success_rate"]
    else:
        card_data["success_diff"] = None # или 0, или np.nan, в зависимости от желаемой дальнейшей обработки
    
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
    # Используем card_data.get("success_diff") с проверкой на pd.notna, так как теперь это может быть np.nan
    current_success_diff = card_data.get("success_diff")
    if pd.notna(current_success_diff):
        if current_success_diff > 0.3:
            diff_interpretation = "**Большая разница** между общей успешностью и успехом с первой попытки (>30%) указывает на то, что карточка может содержать скрытые сложности или неоднозначности, которые студенты преодолевают после нескольких попыток."
        elif current_success_diff > 0.2:
            diff_interpretation = "**Средняя разница** между общей успешностью и успехом с первой попытки (>20%) говорит о том, что карточка требует дополнительных попыток для полного понимания."
        else: # Включая current_success_diff <= 0.2
            diff_interpretation = "**Небольшая разница** между общей успешностью и успехом с первой попытки (<=20%) указывает на то, что большинство студентов либо сразу понимают задание, либо не могут его решить даже после нескольких попыток."
    else:
        diff_interpretation = "Данные для расчета разницы в успешности отсутствуют."
    
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
        "wont_fix": "Проблемы с карточкой не будут исправлены",
        "archive": "Карточка архивирована"
    }
    
    # Получаем текущий статус
    current_status_value = card_data.get("status") 
    
    if current_status_value is None or pd.isna(current_status_value):
        display_status = "unknown"
    else:
        display_status = str(current_status_value)

    # Определяем индекс для selectbox
    status_keys = list(statuses.keys())
    current_status_index = 0 # Индекс по умолчанию (для 'new')

    if display_status in status_keys:
        current_status_index = status_keys.index(display_status)
    else:
        st.warning(f"Текущий статус карточки ('{display_status}') недействителен или отсутствует. Используется статус по умолчанию 'new'.")
        # Если статус недействителен, устанавливаем display_status в 'new', чтобы форма работала корректно
        display_status = "new" 
        if "new" in status_keys: # Убедимся, что 'new' есть в ключах
            current_status_index = status_keys.index("new")
        # Если 'new' по какой-то причине отсутствует, current_status_index останется 0, что безопасно

    # Создаем форму для обновления статуса
    with st.form(key="update_status_form"):
        # Инициализация счетчика обновлений, если его нет
        if 'data_update_counter' not in st.session_state:
            st.session_state.data_update_counter = 0

        # Выбор нового статуса
        new_status = st.selectbox(
            "Статус карточки",
            options=status_keys, # Используем status_keys
            format_func=lambda x: f"{x} - {statuses.get(x, 'Неизвестный статус')}", # .get() для безопасности
            index=current_status_index
        )
        
        # Кнопка для сохранения статуса
        submit_button = st.form_submit_button(label="Обновить статус", type="primary")
        
        # Если кнопка нажата и статус изменился
        if submit_button and new_status != display_status:
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
                
                st.success(f"Статус карточки обновлен с '{display_status}' на '{new_status}'")

                # Инкрементируем счетчик для инвалидации кэша
                st.session_state.data_update_counter = st.session_state.get('data_update_counter', 0) + 1
                print(f"Data update counter incremented to: {st.session_state.data_update_counter}") # Отладка
                
                st.rerun() 
            except Exception as e:
                st.error(f"Ошибка при обновлении статуса: {str(e)}")

    # Получаем текущие параметры URL для обновления
    query_params = st.query_params # Читаем напрямую

    # Обновляем URL, чтобы отразить выбранную карточку (если она изменилась)
    selected_card_id_session = st.session_state.get("selected_card_id")
    current_card_id_from_url = query_params.get("card_id") 

    if selected_card_id_session and str(current_card_id_from_url) != str(selected_card_id_session):
        # temp_params = dict(st.query_params)
        # temp_params["card_id"] = str(selected_card_id_session)
        # temp_params["page"] = "cards" 
        # st.query_params = temp_params # Это один из способов
        
        # Более явный способ с clear()
        st.query_params.clear()
        st.query_params["page"] = "cards"
        st.query_params["card_id"] = str(selected_card_id_session)
        # Если нужно сохранить другие существующие query_params, их нужно прочитать до clear()
        # и добавить обратно после установки page и card_id. Но для этой логики, похоже, 
        # достаточно установить только page и card_id.
        st.rerun()

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

def page_cards(df_card_details: pd.DataFrame, df_structure: pd.DataFrame, eng):
    """Страница с детальным анализом одной карточки"""
    
    # Получаем выбранные фильтры
    program_filter = st.session_state.get("filter_program")
    module_filter = st.session_state.get("filter_module")
    lesson_filter = st.session_state.get("filter_lesson")
    gz_filter = st.session_state.get("filter_gz")
    
    # Фильтруем данные структуры для селектора карточек, если card_id не выбран
    # df_structure - это cards_structure
    df_filtered_structure = core.apply_filters(df_structure)
    
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
        if df_filtered_structure.empty:
            st.warning("Нет данных для выбранных фильтров. Выберите другие фильтры в боковой панели.")
            return
        
        # Данные для селектора берем из df_card_details, отфильтрованные по структуре
        # Присоединяем метрики (risk, card_type) к отфильтрованной структуре для селектора
        if df_card_details is not None and not df_card_details.empty:
            # Убедимся, что df_card_details содержит card_id как int для мержа
            df_card_details["card_id"] = pd.to_numeric(df_card_details["card_id"], errors='coerce')
            df_filtered_structure["card_id"] = pd.to_numeric(df_filtered_structure["card_id"], errors='coerce')

            # Выбираем только нужные колонки из df_card_details перед мержем, чтобы избежать дубликатов колонок структуры
            # Предполагаем, что df_card_details содержит card_id, risk, card_type
            cols_from_details = ["card_id"]
            if "risk" in df_card_details.columns: cols_from_details.append("risk")
            if "card_type" in df_card_details.columns: cols_from_details.append("card_type")
            
            df_selector_data = pd.merge(
                df_filtered_structure[["card_id"]].drop_duplicates(), # Только ID из структуры, чтобы не было дублей структурных полей
                df_card_details[cols_from_details],
                on="card_id",
                how="left"
            )
            df_selector_data.fillna({"risk": 0, "card_type": "N/A"}, inplace=True)
        else:
            # Если df_card_details пуст, используем только структуру и добавляем заглушки для метрик
            df_selector_data = df_filtered_structure.copy()
            if "risk" not in df_selector_data.columns: df_selector_data["risk"] = 0
            if "card_type" not in df_selector_data.columns: df_selector_data["card_type"] = "N/A"

        # Сортируем карточки по риску для лучшего выбора
        df_sorted_for_selector = df_selector_data.sort_values("risk", ascending=False)
        
        st.header("🔍 Выберите карточку для анализа")
        
        selected_card_id = st.selectbox(
            "Выберите карточку",
            options=df_sorted_for_selector["card_id"].unique(), # Уникальные ID
            format_func=lambda x: f"ID: {x} - Риск: {df_sorted_for_selector[df_sorted_for_selector['card_id'] == x]['risk'].values[0]:.2f} - Тип: {df_sorted_for_selector[df_sorted_for_selector['card_id'] == x]['card_type'].values[0]}",
            key="card_selector"
        )
        
        # Сохраняем выбор в состоянии
        st.session_state["selected_card_id"] = selected_card_id
        
        # Обновляем параметр URL для сохранения выбора при обновлении страницы
        st.query_params.clear()
        st.query_params["page"] = "cards"
        st.query_params["card_id"] = str(selected_card_id)
        
        # Перезагружаем страницу для применения выбора
        st.rerun()
    
    # Получаем данные выбранной карточки из df_card_details
    # df_card_details должен содержать все метрики и структурные поля (из джойна в load_card_data)
    if df_card_details is None or df_card_details.empty:
        st.error(f"Данные о карточках (df_card_details) не загружены. Невозможно отобразить карточку ID {card_id}.")
        return

    card_data_rows = df_card_details[df_card_details["card_id"] == int(card_id)]
    
    # Проверяем, есть ли данные для карточки
    if card_data_rows.empty:
        st.error(f"Карточка с ID {card_id} не найдена в данных.")
        return
    
    # Получаем Series с данными карточки
    card_data = card_data_rows.iloc[0].copy() # Используем .copy() чтобы избежать SettingWithCopyWarning
    
    # Получаем СВЕЖИЙ СТАТУС для текущей карточки
    current_card_id = int(card_data["card_id"])
    df_fresh_status = core.get_fresh_card_statuses(eng, [current_card_id])
    if not df_fresh_status.empty:
        fresh_status_info = df_fresh_status.iloc[0]
        card_data["status"] = fresh_status_info["status"]
        card_data["updated_at"] = fresh_status_info["updated_at"] # Обновляем и дату обновления статуса
        card_data["updated_by"] = fresh_status_info["updated_by"] # и кем обновлен
        print(f"[page_cards] Fresh status for card {current_card_id}: {card_data['status']}")
    else:
        print(f"[page_cards] Could not fetch fresh status for card {current_card_id}. Using status from df_card_details.")

    # --- ОТОБРАЖЕНИЕ СТАТУСА КАРТОЧКИ В САМОМ ВЕРХУ СТРАНИЦЫ (ДО ЗАГОЛОВКА) ---
    current_status_value_for_badge = card_data.get("status") 
    display_status_for_badge = "unknown"
    if current_status_value_for_badge is not None and not pd.isna(current_status_value_for_badge):
        display_status_for_badge = str(current_status_value_for_badge)
    
    # Карта цветов для бейджа (можно вынести, если используется еще где-то в таком же виде)
    badge_status_color_map = {
        "new": "blue", "in_work": "orange", "review": "purple", 
        "ready_for_qc": "violet", "done": "green", "wont_fix": "red", "archive": "grey", "unknown": "grey"
    }
    badge_color = badge_status_color_map.get(display_status_for_badge, "grey")
    
    st.markdown(
        f"<span style='display:inline-block; background-color:{badge_color}; color:white; padding:0.2em 0.7em; border-radius:0.7em; font-weight:bold; font-size:1em; margin-bottom:10px;'>"
        f"{display_status_for_badge.capitalize()}</span>",
        unsafe_allow_html=True
    )
    # st.markdown("<hr style='margin-top: 5px; margin-bottom: 10px;'>", unsafe_allow_html=True) # Горизонтальную линию можно убрать или оставить по желанию
    # --- КОНЕЦ БЛОКА ОТОБРАЖЕНИЯ СТАТУСА ---

    # Добавляем метрику разницы между success_rate и first_try_success_rate
    if pd.notna(card_data.get("success_rate")) and pd.notna(card_data.get("first_try_success_rate")):
        card_data["success_diff"] = card_data["success_rate"] - card_data["first_try_success_rate"]
    else:
        card_data["success_diff"] = np.nan # Используем np.nan для числовых колонок, если данные отсутствуют

    # Проверяем, есть ли поле trickiness_level, если нет - вычисляем
    if "trickiness_level" not in card_data or pd.isna(card_data.get("trickiness_level")):
        if hasattr(core, 'get_trickiness_level'):
            # Убедимся, что core.get_trickiness_level может обработать Series или требует dict
            # Если core.get_trickiness_level ожидает dict, то card_data.to_dict()
            # Если он векторизован и ожидает DataFrame, то pd.DataFrame([card_data])
            # Судя по предыдущему использованию, он может принимать строку (Series)
            try:
                card_data["trickiness_level"] = core.get_trickiness_level(card_data)
            except Exception as e_trickiness:
                print(f"Error calculating trickiness_level in page_cards: {e_trickiness}")
                card_data["trickiness_level"] = 0 # Fallback
        else:
            card_data["trickiness_level"] = 0 
    
    # Получаем card_order из базы данных
    card_order = get_card_order(int(card_data["card_id"]), eng)
    if card_order is not None:
        card_data["card_order"] = card_order
    
    # Создаем иерархический заголовок с указанием карточки
    create_hierarchical_header(
        levels=["program", "module", "lesson", "gz", "card"],
        values=[card_data["program_name"], card_data["module_name"], card_data["lesson_name"], card_data["gz_name"], f"Карточка {int(card_data['card_id'])}"]
    )

    # Отображаем ссылки на карточку и ГЗ
    add_card_links(card_data)
    
    # Отображаем основную информацию о карточке
    display_card_details(card_data)
    
    # Отображаем привязку к курсам, передаем DataFrame целиком
    display_course_links(int(card_data["card_id"]), eng, df_structure)
    
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
    
    # Добавляем разделитель
    st.markdown("---")
    
    # Добавляем интерфейс экспорта данных в конце страницы
    st.markdown("## 📥 Экспорт данных карточки")
    
    # Отображаем селектор полей
    field_selection = display_export_field_selector()
    
    # Создаем колонки для кнопки и информации
    col1, col2 = st.columns([1, 2])
    with col1:
        display_csv_download_button(card_data, eng, field_selection)
    with col2:
        # Показываем информацию о выбранных полях
        selected_fields = [k for k, v in field_selection.items() if v]
        if selected_fields:
            field_count = len(selected_fields)
            
            # Группируем поля по категориям для отображения
            field_groups = {
                'basic': ['card_id', 'card_type', 'program_name', 'module_name', 'lesson_name', 'gz_name', 'card_order', 'card_url', 'status'],
                'metrics': ['success_rate', 'first_try_success_rate', 'success_diff', 'discrimination_avg', 'complaint_rate', 'complaints_total', 'attempted_share', 'total_attempts', 'time_median', 'trickiness_level'],
                'risk': ['risk_discrimination', 'risk_success_rate', 'risk_trickiness', 'risk_complaints', 'risk_attempted_share', 'weighted_avg_risk', 'max_risk', 'confidence_factor', 'final_risk'],
                'additional': ['card_public_url', 'screenshot_url', 'embedding'],
                'timestamps': ['updated_at', 'updated_by', 'export_timestamp'],
                'complaints_text': ['complaints_text']
            }
            
            group_names = {
                'basic': '📋 Основная информация',
                'metrics': '📊 Ключевые метрики', 
                'risk': '⚠️ Компоненты риска',
                'additional': '🔗 Дополнительные данные',
                'timestamps': '🕒 Временные метки',
                'complaints_text': '💬 Тексты жалоб'
            }
            
            selected_by_group = {}
            for group, fields in field_groups.items():
                selected_in_group = [f for f in fields if f in selected_fields]
                if selected_in_group:
                    selected_by_group[group] = selected_in_group
            
            if selected_by_group:
                info_text = f"**Выбрано {field_count} полей для экспорта:**\n\n"
                for group, fields in selected_by_group.items():
                    info_text += f"**{group_names[group]}:** {len(fields)} полей\n"
                    info_text += "• " + ", ".join(fields) + "\n\n"
                
                st.info(info_text, icon="ℹ️")
            else:
                st.info(f"**Выбрано {field_count} кастомных полей для экспорта**", icon="ℹ️")
        else:
            st.warning("Не выбрано ни одного поля для экспорта", icon="⚠️")
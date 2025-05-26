# pages/my_tasks.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from sqlalchemy import text
from datetime import datetime

import core
import auth

def format_array_field(arr):
    """Форматирование массива для отображения"""
    if arr is None or (isinstance(arr, float) and pd.isna(arr)):
        return ""
    if isinstance(arr, list):
        return ", ".join(str(x) for x in arr if x)
    return str(arr)

def get_risk_color(risk):
    """Получение цвета для значения риска"""
    if pd.isna(risk):
        return "#808080"  # Серый для отсутствующих данных
    elif risk >= 0.7:
        return "#FF4444"  # Красный
    elif risk >= 0.4:
        return "#FFA500"  # Оранжевый
    else:
        return "#44FF44"  # Зеленый

def get_status_color(status):
    """Получение цвета для статуса"""
    colors = {
        "not_started": "#808080",  # Серый
        "in_progress": "#3498db",  # Синий
        "review": "#f39c12",       # Оранжевый
        "completed": "#27ae60",    # Зеленый
        "wont_fix": "#e74c3c",     # Красный
        "ready_for_qc": "#9b59b6"  # Фиолетовый
    }
    return colors.get(status, "#808080")

def page_my_tasks(df: pd.DataFrame, engine):
    """Страница задач методиста"""
    st.title("📝 Мои задачи")
    
    # Получаем уникальные карточки с агрегированной информацией
    user_id = st.session_state.user_id
    assignments = auth.get_assigned_cards_unique(engine, user_id)
    
    if assignments.empty:
        st.info("У вас нет назначенных карточек")
        return
    
    # Статусы для отображения
    status_labels = {
        "not_started": "Не начато",
        "in_progress": "В работе", 
        "review": "На проверке",
        "completed": "Завершено",
        "wont_fix": "Не будет исправлено",
        "ready_for_qc": "Готово к проверке качества"
    }
    
    # Создаем вкладки для разных представлений
    tab1, tab2, tab3 = st.tabs(["📊 Обзор", "📋 Список задач", "📈 Аналитика"])
    
    with tab1:
        # Общая статистика
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Всего карточек", len(assignments))
        
        with col2:
            in_progress = len(assignments[assignments["status"] == "in_progress"])
            st.metric("В работе", in_progress)
        
        with col3:
            completed = len(assignments[assignments["status"] == "completed"])
            completion_rate = (completed / len(assignments) * 100) if len(assignments) > 0 else 0
            st.metric("Завершено", completed, f"{completion_rate:.1f}%")
        
        with col4:
            high_risk = len(assignments[assignments["risk"] >= 0.7])
            st.metric("Высокий риск", high_risk)
        
        # График распределения по статусам
        st.subheader("Распределение по статусам")
        
        status_counts = assignments["status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        status_counts["label"] = status_counts["status"].map(status_labels)
        status_counts["color"] = status_counts["status"].map(get_status_color)
        
        fig = go.Figure(data=[
            go.Bar(
                x=status_counts["label"],
                y=status_counts["count"],
                marker_color=status_counts["color"],
                text=status_counts["count"],
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            title="Количество карточек по статусам",
            xaxis_title="Статус",
            yaxis_title="Количество",
            showlegend=False,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Распределение по программам
        st.subheader("Распределение по программам")
        
        # Разворачиваем массивы программ
        program_data = []
        for _, row in assignments.iterrows():
            if row["program_names"] and isinstance(row["program_names"], list):
                for program in row["program_names"]:
                    program_data.append({
                        "program": program,
                        "status": row["status"],
                        "risk": row["risk"]
                    })
        
        if program_data:
            program_df = pd.DataFrame(program_data)
            program_counts = program_df.groupby(["program", "status"]).size().reset_index(name="count")
            
            fig = px.bar(
                program_counts,
                x="program",
                y="count",
                color="status",
                color_discrete_map={k: get_status_color(k) for k in status_labels.keys()},
                labels={"count": "Количество", "program": "Программа", "status": "Статус"},
                title="Карточки по программам и статусам"
            )
            
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Фильтры
        st.subheader("Фильтры")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Фильтр по статусу
            selected_statuses = st.multiselect(
                "Статус",
                options=list(status_labels.keys()),
                default=None,
                format_func=lambda x: status_labels.get(x, x)
            )
        
        with col2:
            # Фильтр по риску
            risk_filter = st.select_slider(
                "Минимальный риск",
                options=[0.0, 0.3, 0.5, 0.7, 0.9],
                value=0.0,
                format_func=lambda x: f"{x:.1f}"
            )
        
        with col3:
            # Сортировка
            sort_by = st.selectbox(
                "Сортировать по",
                options=["updated_at", "risk", "total_attempts", "success_rate"],
                format_func=lambda x: {
                    "updated_at": "Дате обновления",
                    "risk": "Риску",
                    "total_attempts": "Количеству попыток",
                    "success_rate": "Успешности"
                }.get(x, x)
            )
        
        # Применяем фильтры
        filtered_assignments = assignments.copy()
        
        if selected_statuses:
            filtered_assignments = filtered_assignments[
                filtered_assignments["status"].isin(selected_statuses)
            ]
        
        if risk_filter > 0:
            filtered_assignments = filtered_assignments[
                filtered_assignments["risk"] >= risk_filter
            ]
        
        # Сортировка
        ascending = sort_by == "success_rate"  # Для успешности - по возрастанию
        filtered_assignments = filtered_assignments.sort_values(
            by=sort_by, 
            ascending=ascending,
            na_position='last'
        )
        
        # Отображение карточек
        st.subheader(f"Найдено карточек: {len(filtered_assignments)}")
        
        for idx, row in filtered_assignments.iterrows():
            with st.expander(
                f"Карточка {row['card_id']} - {status_labels.get(row['status'], row['status'])}",
                expanded=False
            ):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Основная информация
                    st.markdown(f"**ID карточки:** {row['card_id']}")
                    st.markdown(f"**Тип:** {row['card_type'] if pd.notna(row['card_type']) else 'Не указан'}")
                    
                    # Местоположения карточки
                    st.markdown("**Используется в:**")
                    
                    # Программы
                    if row["program_names"] and isinstance(row["program_names"], list):
                        st.markdown(f"- **Программы:** {', '.join(row['program_names'])}")
                    
                    # Модули
                    if row["module_names"] and isinstance(row["module_names"], list):
                        st.markdown(f"- **Модули:** {', '.join(row['module_names'])}")
                    
                    # Уроки
                    if row["lesson_names"] and isinstance(row["lesson_names"], list):
                        st.markdown(f"- **Уроки:** {', '.join(row['lesson_names'][:5])}")
                        if len(row['lesson_names']) > 5:
                            st.markdown(f"  *...и еще {len(row['lesson_names']) - 5} уроков*")
                    
                    # Группы заданий
                    if row["gz_names"] and isinstance(row["gz_names"], list):
                        st.markdown(f"- **Группы заданий:** {', '.join(row['gz_names'][:3])}")
                        if len(row['gz_names']) > 3:
                            st.markdown(f"  *...и еще {len(row['gz_names']) - 3} ГЗ*")
                    
                    # Заметки
                    if pd.notna(row["notes"]) and row["notes"]:
                        st.markdown(f"**Заметки:** {row['notes']}")
                
                with col2:
                    # Метрики
                    st.markdown("**Метрики:**")
                    
                    # Риск
                    risk_value = row["risk"] if pd.notna(row["risk"]) else None
                    if risk_value is not None:
                        risk_color = get_risk_color(risk_value)
                        st.markdown(
                            f"<div style='color: {risk_color}; font-weight: bold;'>Риск: {risk_value:.2f}</div>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown("Риск: Нет данных")
                    
                    # Другие метрики
                    if pd.notna(row["total_attempts"]):
                        st.markdown(f"Попыток: {int(row['total_attempts'])}")
                    
                    if pd.notna(row["success_rate"]):
                        st.markdown(f"Успешность: {row['success_rate']:.1f}%")
                    
                    if pd.notna(row["complaint_rate"]):
                        st.markdown(f"Жалобы: {row['complaint_rate']:.1f}%")
                    
                    if pd.notna(row["time_median"]):
                        st.markdown(f"Время (медиана): {row['time_median']:.1f} сек")
                
                # Действия
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"Открыть карточку", key=f"open_{row['card_id']}"):
                        st.query_params.clear()
                        st.query_params["page"] = "cards"
                        st.query_params["card_id"] = str(row['card_id'])
                        st.rerun()
                
                with col2:
                    # Изменение статуса
                    current_status = row["status"]
                    # Проверяем, есть ли текущий статус в словаре
                    if current_status in status_labels:
                        current_index = list(status_labels.keys()).index(current_status)
                    else:
                        # Если статус неизвестен, добавляем его временно
                        status_labels[current_status] = current_status
                        current_index = list(status_labels.keys()).index(current_status)
                    
                    new_status = st.selectbox(
                        "Изменить статус",
                        options=list(status_labels.keys()),
                        index=current_index,
                        format_func=lambda x: status_labels.get(x, x),
                        key=f"status_{row['assignment_id']}"
                    )
                    
                    if new_status != row["status"]:
                        if st.button("Сохранить", key=f"save_{row['assignment_id']}"):
                            if auth.update_card_status(
                                engine,
                                row["assignment_id"],
                                new_status,
                                user_id
                            ):
                                st.success("Статус обновлен")
                                st.rerun()
                
                with col3:
                    # Дата обновления
                    if pd.notna(row["updated_at"]):
                        updated = pd.to_datetime(row["updated_at"])
                        st.markdown(f"*Обновлено: {updated.strftime('%d.%m.%Y %H:%M')}*")
    
    with tab3:
        # Аналитика
        st.subheader("Аналитика по назначенным карточкам")
        
        # Временная динамика
        if "assigned_at" in assignments.columns:
            assignments["assigned_date"] = pd.to_datetime(assignments["assigned_at"]).dt.date
            daily_assignments = assignments.groupby("assigned_date").size().reset_index(name="count")
            
            fig = px.line(
                daily_assignments,
                x="assigned_date",
                y="count",
                title="Динамика назначений",
                labels={"assigned_date": "Дата", "count": "Количество назначений"}
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Корреляция метрик
        metrics_cols = ["risk", "success_rate", "complaint_rate", "total_attempts"]
        available_metrics = [col for col in metrics_cols if col in assignments.columns]
        
        if len(available_metrics) >= 2:
            st.subheader("Корреляция метрик")
            
            # Фильтруем только числовые данные
            metrics_data = assignments[available_metrics].select_dtypes(include=[np.number])
            
            if not metrics_data.empty:
                corr_matrix = metrics_data.corr()
                
                fig = px.imshow(
                    corr_matrix,
                    labels=dict(color="Корреляция"),
                    x=available_metrics,
                    y=available_metrics,
                    color_continuous_scale="RdBu",
                    zmin=-1,
                    zmax=1
                )
                
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        # Топ проблемных карточек
        st.subheader("Топ-10 проблемных карточек")
        
        # Считаем проблемность как комбинацию риска и низкой успешности
        problem_cards = assignments.copy()
        problem_cards["problem_score"] = 0
        
        if "risk" in problem_cards.columns:
            problem_cards["problem_score"] += problem_cards["risk"].fillna(0) * 0.5
        
        if "success_rate" in problem_cards.columns:
            problem_cards["problem_score"] += (100 - problem_cards["success_rate"].fillna(100)) / 100 * 0.3
        
        if "complaint_rate" in problem_cards.columns:
            problem_cards["problem_score"] += problem_cards["complaint_rate"].fillna(0) / 100 * 0.2
        
        top_problems = problem_cards.nlargest(10, "problem_score")
        
        if not top_problems.empty:
            fig = go.Figure(data=[
                go.Bar(
                    x=top_problems["card_id"].astype(str),
                    y=top_problems["problem_score"],
                    text=top_problems["problem_score"].round(2),
                    textposition='auto',
                    marker_color=top_problems["problem_score"].apply(
                        lambda x: "#FF4444" if x > 0.7 else "#FFA500" if x > 0.4 else "#FFFF44"
                    )
                )
            ])
            
            fig.update_layout(
                title="Топ-10 проблемных карточек",
                xaxis_title="ID карточки",
                yaxis_title="Индекс проблемности",
                showlegend=False,
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
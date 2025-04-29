# pages/my_tasks.py

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from sqlalchemy import text

import core
import auth

def page_my_tasks(df: pd.DataFrame, engine):
    """Страница задач методиста"""
    st.title("📝 Мои задачи")
    
    # Получаем задачи, назначенные текущему пользователю
    user_id = st.session_state.user_id
    assignments = auth.get_assigned_cards(engine, user_id)
    
    if assignments.empty:
        st.info("У вас нет назначенных карточек")
    else:
        # Статистика
        st.subheader("Статистика по статусам")
        
        # Группируем по статусам
        status_counts = assignments["status"].value_counts().reset_index()
        status_counts.columns = ["Статус", "Количество"]
        
        # Переименование статусов для отображения
        status_labels = {
            "not_started": "Не начато",
            "in_progress": "В работе",
            "review": "На проверке",
            "completed": "Завершено",
            "wont_fix": "Не будет исправлено"
        }
        
        status_counts["Название"] = status_counts["Статус"].map(status_labels)
        
        # Отображаем метрики в строку
        cols = st.columns(len(status_counts))
        
        for i, (_, row) in enumerate(status_counts.iterrows()):
            with cols[i]:
                st.metric(
                    row["Название"],
                    row["Количество"],
                    delta=None
                )
        
        # График распределения по статусам
        fig = px.pie(
            status_counts,
            values="Количество",
            names="Название",
            title="Распределение задач по статусам",
            color="Название",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Фильтры
        st.subheader("Список задач")
        
        # Фильтр по статусу
        selected_status = st.multiselect(
            "Фильтр по статусу",
            options=list(status_labels.keys()),
            default=None,
            format_func=lambda x: status_labels.get(x, x)
        )
        
        # Применяем фильтр
        filtered_assignments = assignments
        
        if selected_status:
            filtered_assignments = filtered_assignments[filtered_assignments["status"].isin(selected_status)]
        
        # Создаем DataFrame для отображения
        display_df = pd.DataFrame()
        display_df["ID карточки"] = filtered_assignments["card_id"]
        display_df["Программа"] = filtered_assignments["program"]
        display_df["Модуль"] = filtered_assignments["module"]
        display_df["Урок"] = filtered_assignments["lesson"]
        display_df["Группа заданий"] = filtered_assignments["gz"]
        display_df["Тип карточки"] = filtered_assignments["card_type"]
        display_df["Статус"] = filtered_assignments["status"].map(status_labels)
        display_df["Обновлено"] = filtered_assignments["updated_at"]
        
        # Добавляем ссылку на страницу карточки
        display_df["Действия"] = filtered_assignments.apply(
            lambda row: f"[Перейти к карточке](?page=cards&card_id={int(row['card_id'])})", 
            axis=1
        )
        
        # Отображаем таблицу без колонки 'Действия'
        st.dataframe(display_df.drop(columns=["Действия"]), use_container_width=True)
        
        # Кнопки для перехода к карточкам
        for _, row in assignments.iterrows():
            card_id = int(row['card_id'])
            if st.button(f"Перейти к карточке {card_id}", key=f"my_tasks_nav_{card_id}"):
                # Устанавливаем параметры URL и перезапускаем приложение
                st.query_params = {"page": "cards", "card_id": str(card_id)}
                st.rerun()
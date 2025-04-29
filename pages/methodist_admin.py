# pages/methodist_admin.py

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os
import hashlib
from sqlalchemy import text

import core
import auth
from components.utils import create_hierarchical_header

def page_methodist_admin(df: pd.DataFrame, engine):
    """Страница администратора методистов"""
    st.title("👨‍🏫 Панель администратора методистов")
    
    # Создаем вкладки для разных разделов
    tabs = st.tabs([
        "📋 Назначенные карточки", 
        "👥 Управление пользователями", 
        "📊 Статистика"
    ])
    
    # Вкладка назначенных карточек
    with tabs[0]:
        st.header("Назначенные карточки")
        
        # Получаем все назначенные карточки
        assignments = auth.get_assigned_cards(engine)
        
        if assignments.empty:
            st.info("Нет назначенных карточек")
        else:
            # Фильтры
            col1, col2 = st.columns(2)
            
            with col1:
                # Фильтр по методисту
                methodists = assignments["username"].unique()
                selected_methodist = st.multiselect(
                    "Фильтр по методисту",
                    options=methodists,
                    default=None
                )
            
            with col2:
                # Фильтр по статусу
                statuses = assignments["status"].unique()
                status_labels = {
                    "not_started": "Не начато",
                    "in_progress": "В работе",
                    "review": "На проверке",
                    "completed": "Завершено",
                    "wont_fix": "Не будет исправлено"
                }
                
                selected_status = st.multiselect(
                    "Фильтр по статусу",
                    options=statuses,
                    default=None,
                    format_func=lambda x: status_labels.get(x, x)
                )
            
            # Применяем фильтры
            filtered_assignments = assignments
            
            if selected_methodist:
                filtered_assignments = filtered_assignments[filtered_assignments["username"].isin(selected_methodist)]
            
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
            display_df["Методист"] = filtered_assignments["username"]
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
            for _, row in filtered_assignments.iterrows():
                card_id = int(row['card_id'])
                if st.button(f"Перейти к карточке {card_id}", key=f"methodist_admin_nav_{card_id}"):
                    # Устанавливаем параметры URL и перезапускаем приложение
                    st.query_params = {"page": "cards", "card_id": str(card_id)}
                    st.rerun()
            
            # График распределения по статусам
            st.subheader("Распределение по статусам")
            
            status_counts = filtered_assignments["status"].value_counts().reset_index()
            status_counts.columns = ["Статус", "Количество"]
            status_counts["Статус"] = status_counts["Статус"].map(status_labels)
            
            fig = px.pie(
                status_counts, 
                values="Количество", 
                names="Статус",
                title="Распределение карточек по статусам",
                color="Статус",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Вкладка управления пользователями
    with tabs[1]:
        st.header("Управление пользователями")
        
        # Получаем список пользователей
        with engine.connect() as conn:
            users = pd.read_sql(text("""
                SELECT user_id, username, email, full_name, role, is_active, created_at
                FROM users
                ORDER BY username
            """), conn)
        
        # Отображаем список пользователей
        st.subheader("Список пользователей")
        
        # Создаем DataFrame для отображения
        display_users = pd.DataFrame()
        display_users["ID"] = users["user_id"]
        display_users["Имя пользователя"] = users["username"]
        display_users["Полное имя"] = users["full_name"]
        display_users["Email"] = users["email"]
        display_users["Роль"] = users["role"]
        display_users["Активен"] = users["is_active"]
        display_users["Создан"] = users["created_at"]
        
        st.dataframe(display_users, use_container_width=True)
        
        # Форма для создания нового пользователя
        st.subheader("Создать нового пользователя")
        
        with st.form(key="create_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                username = st.text_input("Имя пользователя")
                password = st.text_input("Пароль", type="password")
                role = st.selectbox("Роль", options=["methodist", "admin", "viewer"])
            
            with col2:
                full_name = st.text_input("Полное имя")
                email = st.text_input("Email")
                is_active = st.checkbox("Активен", value=True)
            
            submit_button = st.form_submit_button(label="Создать пользователя", type="primary")
            
            if submit_button:
                if not username or not password:
                    st.error("Имя пользователя и пароль обязательны")
                else:
                    # Хешируем пароль
                    password_hash = hashlib.sha256(password.encode()).hexdigest()
                    
                    # Проверяем, существует ли уже пользователь с таким именем
                    with engine.connect() as conn:
                        user_exists = conn.execute(text("""
                            SELECT 1 FROM users WHERE username = :username
                        """), {"username": username}).fetchone()
                        
                        if user_exists:
                            st.error(f"Пользователь с именем '{username}' уже существует")
                        else:
                            # Создаем пользователя
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO users (username, password_hash, email, full_name, role, is_active)
                                    VALUES (:username, :password_hash, :email, :full_name, :role, :is_active)
                                """), {
                                    "username": username,
                                    "password_hash": password_hash,
                                    "email": email,
                                    "full_name": full_name,
                                    "role": role,
                                    "is_active": is_active
                                })
                            
                            st.success(f"Пользователь '{username}' успешно создан")
                            st.rerun()
        
        # Форма для редактирования пользователя
        st.subheader("Редактировать пользователя")
        
        with st.form(key="edit_user_form"):
            # Выбор пользователя для редактирования
            user_options = {row["user_id"]: f"{row['username']} ({row['full_name']})" for _, row in users.iterrows()}
            selected_user_id = st.selectbox(
                "Выберите пользователя",
                options=list(user_options.keys()),
                format_func=lambda x: user_options[x]
            )
            
            # Получаем данные выбранного пользователя
            selected_user = users[users["user_id"] == selected_user_id].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                new_password = st.text_input("Новый пароль (оставьте пустым, чтобы не менять)", type="password")
                new_role = st.selectbox("Роль", options=["methodist", "admin", "viewer"], index=["methodist", "admin", "viewer"].index(selected_user["role"]))
            
            with col2:
                new_full_name = st.text_input("Полное имя", value=selected_user["full_name"])
                new_email = st.text_input("Email", value=selected_user["email"])
                new_is_active = st.checkbox("Активен", value=selected_user["is_active"])
            
            submit_button = st.form_submit_button(label="Обновить пользователя", type="primary")
            
            if submit_button:
                # Составляем запрос для обновления
                query = "UPDATE users SET full_name = :full_name, email = :email, role = :role, is_active = :is_active"
                params = {
                    "user_id": selected_user_id,
                    "full_name": new_full_name,
                    "email": new_email,
                    "role": new_role,
                    "is_active": new_is_active
                }
                
                # Если указан новый пароль, обновляем его
                if new_password:
                    password_hash = hashlib.sha256(new_password.encode()).hexdigest()
                    query += ", password_hash = :password_hash"
                    params["password_hash"] = password_hash
                
                query += " WHERE user_id = :user_id"
                
                # Выполняем обновление
                with engine.begin() as conn:
                    conn.execute(text(query), params)
                
                st.success(f"Пользователь успешно обновлен")
                st.rerun()
    
    # Вкладка статистики
    with tabs[2]:
        st.header("Статистика")
        
        # Получаем данные о назначенных карточках
        assignments = auth.get_assigned_cards(engine)
        
        if assignments.empty:
            st.info("Нет данных для отображения статистики")
        else:
            # Статистика по методистам
            st.subheader("Статистика по методистам")
            
            # Группируем данные по методистам и статусам
            methodist_stats = assignments.groupby(["username", "status"]).size().reset_index(name="count")
            
            # Создаем график
            fig = px.bar(
                methodist_stats,
                x="username",
                y="count",
                color="status",
                title="Количество карточек по методистам и статусам",
                barmode="group",
                color_discrete_map={
                    "not_started": "gray",
                    "in_progress": "blue",
                    "review": "orange",
                    "completed": "green",
                    "wont_fix": "red"
                }
            )
            
            # Переименование статусов для легенды
            status_labels = {
                "not_started": "Не начато",
                "in_progress": "В работе",
                "review": "На проверке",
                "completed": "Завершено",
                "wont_fix": "Не будет исправлено"
            }
            
            fig.for_each_trace(lambda t: t.update(name = status_labels.get(t.name, t.name)))
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Статистика по программам
            st.subheader("Статистика по программам")
            
            # Группируем данные по программам и статусам
            program_stats = assignments.groupby(["program", "status"]).size().reset_index(name="count")
            
            # Создаем график
            fig = px.bar(
                program_stats,
                x="program",
                y="count",
                color="status",
                title="Количество карточек по программам и статусам",
                barmode="group",
                color_discrete_map={
                    "not_started": "gray",
                    "in_progress": "blue",
                    "review": "orange",
                    "completed": "green",
                    "wont_fix": "red"
                }
            )
            
            fig.for_each_trace(lambda t: t.update(name = status_labels.get(t.name, t.name)))
            
            st.plotly_chart(fig, use_container_width=True)
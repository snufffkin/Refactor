# components/metrics.py
"""
Переиспользуемые компоненты для отображения метрик и статистики
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

import core
from db_config import get_cloud_dsn
from sqlalchemy import create_engine, text

def display_trickiness_distribution(df, group_by_col=None):
    """
    Отображает распределение уровней подлости карточек.
    
    Args:
        df: DataFrame с данными
        group_by_col: Колонка для группировки (если None, используются все данные)
    """
    if "trickiness_level" not in df.columns:
        df["trickiness_level"] = df.apply(core.get_trickiness_level, axis=1)
    
    trickiness_categories = {
        0: "Нет подлости",
        1: "Низкий уровень подлости",
        2: "Средний уровень подлости",
        3: "Высокий уровень подлости"
    }
    df["trickiness_category"] = df["trickiness_level"].map(trickiness_categories)
    
    if group_by_col is not None:
        trickiness_distribution = []
        for _, group in df.groupby(group_by_col):
            trickiness_counts = group["trickiness_level"].value_counts().sort_index()
            name = group[group_by_col].iloc[0]
            for level, count in trickiness_counts.items():
                trickiness_distribution.append({
                    "name": name,
                    "level": level,
                    "category": trickiness_categories.get(level, "Неизвестно"),
                    "count": count
                })
        trickiness_df = pd.DataFrame(trickiness_distribution)
        overall_distribution = trickiness_df.groupby("category")["count"].sum().reset_index()
        overall_distribution.columns = ["Категория подлости", "Количество"]
    else:
        trickiness_counts = df["trickiness_level"].value_counts().sort_index()
        overall_distribution = pd.DataFrame({
            "Категория подлости": [trickiness_categories.get(level, "Неизвестно") for level in trickiness_counts.index],
            "Количество": trickiness_counts.values
        })
        
    category_order = list(trickiness_categories.values())
    overall_distribution["Категория подлости"] = pd.Categorical(
        overall_distribution["Категория подлости"], 
        categories=category_order, 
        ordered=True
    )
    overall_distribution = overall_distribution.sort_values("Категория подлости")
    
    color_map = {
        "Нет подлости": "#c0c0c0",
        "Низкий уровень подлости": "#ffff7f",
        "Средний уровень подлости": "#ffaa7f",
        "Высокий уровень подлости": "#ff7f7f"
    }
    
    fig = px.bar(
        overall_distribution,
        x="Категория подлости",
        y="Количество",
        color="Категория подлости",
        color_discrete_map=color_map,
        title="Распределение по уровням подлости"
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>Количество: %{y}")
    st.plotly_chart(fig, use_container_width=True)
    return overall_distribution

def update_display_metrics_row(df, group_by_col=None, compare_with=None):
    if "trickiness_level" not in df.columns:
        df["trickiness_level"] = df.apply(core.get_trickiness_level, axis=1)
    if group_by_col is not None:
        df_agg = df.groupby(group_by_col).agg(trickiness_avg=("trickiness_level", "mean")).reset_index()
        avg_trickiness = df_agg["trickiness_avg"].mean()
    else:
        avg_trickiness = df["trickiness_level"].mean()
    trickiness_delta = None
    if compare_with is not None and "trickiness_level" in compare_with.columns:
        trickiness_delta = avg_trickiness - compare_with["trickiness_level"].mean()
    return {"avg_trickiness": avg_trickiness, "trickiness_delta": trickiness_delta}

def display_trickiness_metric(avg_trickiness, trickiness_delta=None):
    st.metric(
        "Средний уровень подлости", 
        f"{avg_trickiness:.2f}", 
        f"{trickiness_delta:.2f}" if trickiness_delta is not None else None, 
        delta_color="inverse"
    )
    if avg_trickiness < 0.5: return "Низкий уровень подлости"
    if avg_trickiness < 1.5: return "В основном низкий уровень"
    if avg_trickiness < 2.0: return "Средний уровень подлости"
    if avg_trickiness < 2.5: return "Преимущественно средний уровень"
    return "Высокий уровень подлости"

def get_trickiness_distribution(df):
    if "trickiness_level" not in df.columns:
        df["trickiness_level"] = df.apply(core.get_trickiness_level, axis=1)
    trickiness_distribution = df["trickiness_level"].value_counts().to_dict()
    for level in range(4):
        if level not in trickiness_distribution: trickiness_distribution[level] = 0
    return trickiness_distribution

def display_metrics_row(df, group_by_col=None, compare_with=None):
    if df is None or df.empty:
        st.warning("Нет данных для отображения метрик.")
        return {}
    required_metrics_cols = ["success_rate", "complaint_rate", "discrimination_avg", "risk"]
    if not all(col in df.columns for col in required_metrics_cols):
        st.error(f"Отсутствуют необходимые колонки для отображения метрик: {required_metrics_cols}")
        return {}

    if group_by_col is not None:
        agg_functions = {
            "success_rate": "mean", "complaint_rate": "mean",
            "discrimination_avg": "mean", "risk": "mean"
        }
        if "cards_count" in df.columns: agg_functions["total_items"] = ("cards_count", "sum")
        elif "card_id" in df.columns: agg_functions["total_items"] = ("card_id", "nunique")
        else: agg_functions["total_items"] = (df.columns[0], "count")
        df_agg = df.groupby(group_by_col).agg(**agg_functions).reset_index()
        avg_success = df_agg["success_rate"].mean()
        avg_complaints = df_agg["complaint_rate"].mean()
        avg_discrimination = df_agg["discrimination_avg"].mean()
        avg_risk = df_agg["risk"].mean()
        total_items = df_agg["total_items"].sum()
    else:
        avg_success, avg_complaints, avg_discrimination, avg_risk = np.nan, np.nan, np.nan, np.nan
        if "success_rate" in df.columns and df["success_rate"].notna().any(): avg_success = df["success_rate"].mean()
        if "complaint_rate" in df.columns and df["complaint_rate"].notna().any(): avg_complaints = df["complaint_rate"].mean()
        if "discrimination_avg" in df.columns and df["discrimination_avg"].notna().any(): avg_discrimination = df["discrimination_avg"].mean()
        if "risk" in df.columns and df["risk"].notna().any(): avg_risk = df["risk"].mean()
        if "cards_count" in df.columns: total_items = df["cards_count"].sum()
        elif "card_id" in df.columns: total_items = len(df["card_id"].unique())
        else: total_items = len(df)

    success_delta, complaints_delta, discrimination_delta, risk_delta = None, None, None, None
    if compare_with is not None and not compare_with.empty:
        if all(col in compare_with.columns for col in required_metrics_cols):
            success_delta = avg_success - compare_with["success_rate"].mean()
            complaints_delta = avg_complaints - compare_with["complaint_rate"].mean()
            discrimination_delta = avg_discrimination - compare_with["discrimination_avg"].mean()
            risk_delta = avg_risk - compare_with["risk"].mean()

    cols = st.columns(4)
    cols[0].metric("Средний успех", f"{avg_success:.1%}" if pd.notna(avg_success) else "N/A", f"{success_delta:.1%}" if success_delta is not None and pd.notna(success_delta) else None)
    cols[1].metric("Средний % жалоб", f"{avg_complaints:.1%}" if pd.notna(avg_complaints) else "N/A", f"{complaints_delta:.1%}" if complaints_delta is not None and pd.notna(complaints_delta) else None, delta_color="inverse")
    cols[2].metric("Средняя дискриминативность", f"{avg_discrimination:.2f}" if pd.notna(avg_discrimination) else "N/A", f"{discrimination_delta:.2f}" if discrimination_delta is not None and pd.notna(discrimination_delta) else None)
    cols[3].metric("Средний риск", f"{avg_risk:.2f}" if pd.notna(avg_risk) else "N/A", f"{risk_delta:.2f}" if risk_delta is not None and pd.notna(risk_delta) else None, delta_color="inverse")

    if "total_attempts" in df.columns and "attempted_share" in df.columns:
        total_attempts_val, avg_attempted_val = np.nan, np.nan
        if pd.api.types.is_numeric_dtype(df["total_attempts"]): total_attempts_val = df["total_attempts"].sum()
        else: 
            try: total_attempts_val = pd.to_numeric(df["total_attempts"], errors='coerce').sum()
            except Exception: pass
        if pd.api.types.is_numeric_dtype(df["attempted_share"]): avg_attempted_val = df["attempted_share"].mean()
        else: 
            try: avg_attempted_val = pd.to_numeric(df["attempted_share"], errors='coerce').mean()
            except Exception: pass
        cols_attempts = st.columns(2)
        cols_attempts[0].metric("Всего попыток", f"{int(total_attempts_val):,}" if pd.notna(total_attempts_val) else "N/A")
        cols_attempts[1].metric("Среднее участие", f"{avg_attempted_val:.1%}" if pd.notna(avg_attempted_val) else "N/A")
    
    return {
        "avg_success": avg_success, "avg_complaints": avg_complaints,
        "avg_discrimination": avg_discrimination, "avg_risk": avg_risk,
        "total_items": total_items, "high_risk_count": None 
    }

def display_status_chart(df, item_col=None):
    if item_col is not None:
        status_by_item = df.groupby(item_col)["status"].agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "unknown").reset_index()
        status_counts = status_by_item["status"].value_counts().reset_index()
    else:
        status_counts = df["status"].value_counts().reset_index()
    status_counts.columns = ["Статус", "Количество"]
    status_fig = px.pie(
        status_counts, values="Количество", names="Статус", title="Распределение по статусам",
        color="Статус", color_discrete_map={
            "new": "#d3d3d3", "in_work": "#add8e6", "ready_for_qc": "#fffacd",
            "done": "#90ee90", "wont_fix": "#f08080", "unknown": "#cccccc"
        }, hole=0.4
    )
    st.plotly_chart(status_fig, use_container_width=True)

def display_risk_distribution(df, group_by_col=None):
    if group_by_col is not None:
        risk_categories = []
        risk_data = df[["risk", group_by_col]].copy()
        if not pd.api.types.is_numeric_dtype(risk_data["risk"]):
            risk_data["risk"] = pd.to_numeric(risk_data["risk"], errors='coerce')
        risk_data.dropna(subset=['risk'], inplace=True)
        for name, group in risk_data.groupby(group_by_col):
            avg_risk = group["risk"].mean()
            if pd.isna(avg_risk): continue
            if avg_risk < 0.25: category = "Низкий риск"
            elif avg_risk < 0.5: category = "Умеренный риск"
            elif avg_risk < 0.75: category = "Высокий риск"
            else: category = "Критический риск"
            risk_categories.append({"name": name, "risk": avg_risk, "category": category})
        if not risk_categories: 
            st.info("Нет данных для отображения распределения риска по категориям.")
            return
        risk_df = pd.DataFrame(risk_categories)
        risk_distribution = risk_df["category"].value_counts().reset_index()
        risk_distribution.columns = ["Категория риска", "Количество"]
        risk_order = ["Низкий риск", "Умеренный риск", "Высокий риск", "Критический риск"]
        risk_distribution["Категория риска"] = pd.Categorical(risk_distribution["Категория риска"], categories=risk_order, ordered=True)
        risk_distribution = risk_distribution.sort_values("Категория риска").dropna(subset=["Категория риска"])
        color_map = {"Низкий риск": "#7FFF7F", "Умеренный риск": "#FFFF7F", "Высокий риск": "#FFAA7F", "Критический риск": "#FF7F7F"}
        fig = px.bar(risk_distribution, x="Категория риска", y="Количество", color="Категория риска", color_discrete_map=color_map, title="Распределение по уровням риска")
        st.plotly_chart(fig, use_container_width=True)
    else:
        risk_data_hist = df["risk"].copy()
        if not pd.api.types.is_numeric_dtype(risk_data_hist):
            risk_data_hist = pd.to_numeric(risk_data_hist, errors='coerce')
        risk_data_hist.dropna(inplace=True)
        if risk_data_hist.empty:
            st.info("Нет данных для отображения гистограммы риска.")
            return
        fig = px.histogram(risk_data_hist, nbins=20, color_discrete_sequence=["#FF9F7F"], labels={"value": "Риск", "count": "Количество"}, title="Распределение риска")
        fig.add_vline(x=0.25, line_dash="dash", line_color="green", annotation_text="Низкий", annotation_position="top left")
        fig.add_vline(x=0.5, line_dash="dash", line_color="#CCCC00", annotation_text="Умеренный", annotation_position="top left")
        fig.add_vline(x=0.75, line_dash="dash", line_color="red", annotation_text="Высокий", annotation_position="top right")
        st.plotly_chart(fig, use_container_width=True)

def display_overall_card_risk_stats():
    """
    Отображает общую статистику по уровням риска всех карточек в card_risk_cache.
    Выполняет SQL-запрос с использованием get_cloud_dsn() из db_config.
    """
    query_sql = text("""
    SELECT
        COUNT(*) as total_cards,
        COALESCE(SUM(CASE WHEN risk IS NULL OR risk = 0 THEN 1 ELSE 0 END), 0) as no_risk_count,
        COALESCE(SUM(CASE WHEN risk > 0 AND risk <= 0.25 THEN 1 ELSE 0 END), 0) as low_risk_count,
        COALESCE(SUM(CASE WHEN risk > 0.25 AND risk <= 0.5 THEN 1 ELSE 0 END), 0) as moderate_risk_count,
        COALESCE(SUM(CASE WHEN risk > 0.5 AND risk <= 0.75 THEN 1 ELSE 0 END), 0) as high_risk_count,
        COALESCE(SUM(CASE WHEN risk > 0.75 THEN 1 ELSE 0 END), 0) as critical_risk_count
    FROM card_risk_cache;
    """)
    
    st.subheader("📊 Распределение рисков по всем карточкам")

    try:
        dsn = get_cloud_dsn()
        if not dsn:
            st.error("DSN для подключения к базе данных не получен.")
            return
            
        engine = create_engine(dsn)
        with engine.connect() as connection:
            df_risks = pd.read_sql_query(query_sql, connection)

        if not df_risks.empty and df_risks.iloc[0] is not None:
            results = df_risks.iloc[0]
            total_cards = int(results.get('total_cards', 0))
            no_risk_count = int(results.get('no_risk_count', 0))
            low_risk_count = int(results.get('low_risk_count', 0))
            moderate_risk_count = int(results.get('moderate_risk_count', 0))
            high_risk_count = int(results.get('high_risk_count', 0))
            critical_risk_count = int(results.get('critical_risk_count', 0))

            if total_cards > 0:
                no_risk_perc = (no_risk_count / total_cards) * 100
                low_risk_perc = (low_risk_count / total_cards) * 100
                moderate_risk_perc = (moderate_risk_count / total_cards) * 100
                high_risk_perc = (high_risk_count / total_cards) * 100
                critical_risk_perc = (critical_risk_count / total_cards) * 100
            else:
                no_risk_perc = low_risk_perc = moderate_risk_perc = high_risk_perc = critical_risk_perc = 0

            cols_risk_cards = st.columns(5)
            with cols_risk_cards[0]:
                delta_val_no_risk = f"{no_risk_perc:.1f}%" if total_cards > 0 else None
                st.metric(label="Без риска", value=f"{no_risk_count:,}", delta=delta_val_no_risk)
            with cols_risk_cards[1]:
                delta_val_low = f"{low_risk_perc:.1f}%" if total_cards > 0 else None
                st.metric(label="Низкий риск", value=f"{low_risk_count:,}", delta=delta_val_low)
            with cols_risk_cards[2]:
                delta_val_mod = f"{moderate_risk_perc:.1f}%" if total_cards > 0 else None
                st.metric(label="Умеренный риск", value=f"{moderate_risk_count:,}", delta=delta_val_mod)
            with cols_risk_cards[3]:
                delta_val_high = f"{high_risk_perc:.1f}%" if total_cards > 0 else None
                st.metric(label="Высокий риск", value=f"{high_risk_count:,}", delta=delta_val_high, delta_color="inverse")
            with cols_risk_cards[4]:
                delta_val_crit = f"{critical_risk_perc:.1f}%" if total_cards > 0 else None
                st.metric(label="Критический риск", value=f"{critical_risk_count:,}", delta=delta_val_crit, delta_color="inverse")
        else:
            st.warning("Данные о распределении рисков карточек не получены или пусты.")
            
    except ImportError as ie:
        st.error(f"Ошибка импорта для работы с БД: {ie}. Установите необходимые библиотеки (например, psycopg2-binary, sqlalchemy).")    
    except Exception as e:
        st.error(f"Ошибка при подключении к БД или выполнении запроса для статистики рисков: {e}")

__all__ = [
    'display_trickiness_distribution',
    'update_display_metrics_row',
    'display_trickiness_metric',
    'get_trickiness_distribution',
    'display_metrics_row',
    'display_status_chart',
    'display_risk_distribution',
    'display_overall_card_risk_stats'
]
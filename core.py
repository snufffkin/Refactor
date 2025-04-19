# core.py — утилиты / БД (исправлена рекурсия)
"""Содержит только функции.
Никаких глобальных `engine = core.get_engine()`!
"""

import os
from datetime import datetime
from typing import List, Optional
import urllib.parse as ul
import numpy as np

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# ---------------- DB ------------------------------------------------------- #

def get_engine():
    dsn = os.getenv("DB_DSN", "sqlite:///course_quality.db")
    return create_engine(dsn, future=True)


def load_data(engine):
    sql = text(
        """
        SELECT program,module,module_order,lesson,lesson_order,
               gz,gz_id,card_id,card_type,card_url,
               total_attempts,attempted_share,success_rate,first_try_success_rate,
               complaint_rate,complaints_total,discrimination_avg,success_attempts_rate,
               status,updated_at
        FROM cards_mv
        """
    )
    return pd.read_sql(sql, engine)

# ---------------- Filters / Risk ------------------------------------------ #

# Обновленный FILTERS
FILTERS: List[str] = ["program", "module", "lesson", "gz", "card_id"]  # Добавлен "card_id" в список фильтров


def risk_score(row: pd.Series) -> float:
    """
    Расчет показателя риска для карточки на основе комплексной оценки всех метрик.
    
    Формула учитывает:
    - Успешность прохождения (success_rate)
    - Успешность с первой попытки (first_try_success_rate)
    - Количество жалоб (complaint_rate)
    - Индекс дискриминативности (discrimination_avg)
    - Долю студентов, которые попытались решить (attempted_share)
    - Общее количество попыток (total_attempts) - как весовой фактор
    
    Возвращает значение от 0 до 1, где 1 - максимальный риск
    """
    # Веса компонентов (сумма = 1)
    w_success = 0.25        # Вес общей успешности
    w_first_try = 0.15      # Вес успеха с первой попытки
    w_complaints = 0.30     # Вес жалоб (критично)
    w_discrimination = 0.20 # Вес дискриминативности
    w_attempted = 0.10      # Вес доли пытавшихся
    
    # Компоненты риска
    risk_success = 1 - row.success_rate  # Неуспешность (1 - успешность)
    risk_first_try = 1 - row.first_try_success_rate  # Неуспешность с первой попытки
    risk_complaints = min(row.complaint_rate * 3, 1)  # Умножаем на 3, чтобы выделить жалобы (макс = 1)
    
    # Корректируем дискриминативность: 0.5 = нейтрально, <0.5 = плохо, >0.5 = хорошо
    # Дискриминативность должна быть близка к 1 (хорошо различает знающих от незнающих)
    risk_discrimination = 1 - row.discrimination_avg
    
    # Доля студентов, не пытавшихся решить задачу
    risk_attempted = 1 - row.attempted_share
    
    # Базовая оценка риска
    base_risk = (
        w_success * risk_success +
        w_first_try * risk_first_try +
        w_complaints * risk_complaints +
        w_discrimination * risk_discrimination +
        w_attempted * risk_attempted
    )
    
    # Корректировка на основе количества попыток
    # Если попыток мало, доверие к метрикам ниже
    confidence_factor = min(row.total_attempts / 100, 1.0)  # 100+ попыток = полное доверие
    
    # Если попыток мало, смещаем риск к 0.5 (неопределённость)
    adjusted_risk = base_risk * confidence_factor + 0.5 * (1 - confidence_factor)
    
    return adjusted_risk


def apply_filters(df: pd.DataFrame, upto: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Применяет фильтры из session_state к DataFrame.
    
    Args:
        df: DataFrame с данными
        upto: Список фильтров для применения (если None, применяются все фильтры)
    
    Returns:
        Отфильтрованный DataFrame
    """
    cols = FILTERS if upto is None else upto
    for col in cols:
        v = st.session_state.get(f"filter_{col}")
        if v:
            if col == "card_id":  # Специальная обработка для card_id, который должен быть точным совпадением
                df = df[df[col] == v]
            else:
                df = df[df[col] == v]
    return df

# Обновленная функция reset_child в core.py
def reset_child(level: str):
    """
    Сбрасывает дочерние фильтры относительно указанного уровня и 
    обновляет текущую страницу навигации соответственно.
    """
    if level not in FILTERS:
        return
    
    idx = FILTERS.index(level)
    for col in FILTERS[idx+1:]:
        st.session_state[f"filter_{col}"] = None
    
    # Обновляем текущую страницу в соответствии с уровнем фильтрации
    page_mapping = {
        "program": "Программы", 
        "module": "Модули", 
        "lesson": "Уроки",
        "gz": "ГЗ",
        "card_id": "Карточки"
    }
    
    # Если уровень имеет соответствующую страницу, устанавливаем её
    if level in page_mapping and "page" in st.session_state:
        st.session_state["page"] = page_mapping[level]

# ---------------- Aggregation --------------------------------------------- #

def agg_by(df: pd.DataFrame, level: str) -> pd.DataFrame:
    return (df.groupby(level)
              .agg(success=("success_rate","mean"),
                   complaints=("complaint_rate","mean"),
                   risk=("risk","mean"),
                   cards=("card_id","nunique")).reset_index())

# ---------------- Status update ------------------------------------------- #

def save_status_changes(original: pd.DataFrame, edited: pd.DataFrame, engine):
    diff = edited.loc[edited.status != original.status, ["card_id", "status"]]
    if diff.empty:
        return
    with engine.begin() as conn:
        for _, row in diff.iterrows():
            conn.execute(
                text("""
                INSERT INTO card_status(card_id,status,updated_by,updated_at)
                VALUES (:cid,:st,:by,:ts)
                ON CONFLICT(card_id) DO UPDATE SET
                  status=EXCLUDED.status,
                  updated_by=EXCLUDED.updated_by,
                  updated_at=EXCLUDED.updated_at;
                """),
                {"cid": int(row.card_id), "st": row.status, "by": st.session_state.get("user","demo"), "ts": datetime.utcnow()},
            )

# ---------------- UI helper ------------------------------------------------ #

def clickable(label: str, level: str) -> None:
    """Создает кликабельную ссылку с переходом на соответствующий уровень иерархии."""
    if label is None:
        return
    
    safe = ul.quote_plus(str(label))
    st.markdown(
        f'<a href="?level={level}&value={safe}" target="_self" '
        'style="text-decoration:none;color:#4da6ff;font-weight:600;">'
        f'{label}</a>',
        unsafe_allow_html=True,
    )

# ---------------- Risk Analysis -------------------------------------------- #

def get_risk_components(df: pd.DataFrame) -> pd.DataFrame:
    """
    Рассчитывает компоненты риска для каждой карточки и возвращает их в виде DataFrame.
    Полезно для подробного анализа источников риска.
    """
    # Копируем данные для расчетов
    df_risk = df.copy()
    
    # Рассчитываем компоненты риска
    df_risk['risk_success'] = 1 - df_risk.success_rate
    df_risk['risk_first_try'] = 1 - df_risk.first_try_success_rate
    df_risk['risk_complaints'] = np.minimum(df_risk.complaint_rate * 3, 1)
    df_risk['risk_discrimination'] = 1 - df_risk.discrimination_avg
    df_risk['risk_attempted'] = 1 - df_risk.attempted_share
    
    # Добавляем информацию о весах компонентов
    df_risk['weight_success'] = 0.25
    df_risk['weight_first_try'] = 0.15
    df_risk['weight_complaints'] = 0.30
    df_risk['weight_discrimination'] = 0.20
    df_risk['weight_attempted'] = 0.10
    
    # Рассчитываем вклады в итоговый риск
    df_risk['contrib_success'] = df_risk.risk_success * df_risk.weight_success
    df_risk['contrib_first_try'] = df_risk.risk_first_try * df_risk.weight_first_try
    df_risk['contrib_complaints'] = df_risk.risk_complaints * df_risk.weight_complaints
    df_risk['contrib_discrimination'] = df_risk.risk_discrimination * df_risk.weight_discrimination
    df_risk['contrib_attempted'] = df_risk.risk_attempted * df_risk.weight_attempted
    
    # Рассчитываем сырой риск без учета количества попыток
    df_risk['raw_risk'] = (
        df_risk.contrib_success +
        df_risk.contrib_first_try +
        df_risk.contrib_complaints +
        df_risk.contrib_discrimination +
        df_risk.contrib_attempted
    )
    
    # Фактор доверия на основе количества попыток
    df_risk['confidence_factor'] = np.minimum(df_risk.total_attempts / 100, 1.0)
    
    # Итоговый скорректированный риск
    df_risk['adjusted_risk'] = df_risk.raw_risk * df_risk.confidence_factor + 0.5 * (1 - df_risk.confidence_factor)
    
    return df_risk
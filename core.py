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

FILTERS: List[str] = ["program", "module", "lesson", "gz"]  # Добавил "gz" в список фильтров

# Обновленная функция расчета риска на основе интервалов
# Добавьте эти функции в файл core.py

# ------------------ Конфигурационные параметры -----------------------------
# Параметры для дискриминативности
DISCRIMINATION_GOOD = 0.35  # Выше этого значения - хорошая дискриминативность
DISCRIMINATION_MEDIUM = 0.15  # Между этим и GOOD - средняя, ниже - низкая

# Параметры для успешности
SUCCESS_BORING = 0.95  # Выше этого значения - скучная задача
SUCCESS_OPTIMAL_HIGH = 0.95  # Верхняя граница оптимальной успешности
SUCCESS_OPTIMAL_LOW = 0.75  # Нижняя граница оптимальной успешности
SUCCESS_SUBOPTIMAL_LOW = 0.50  # Нижняя граница субоптимальной успешности
# Ниже SUCCESS_SUBOPTIMAL_LOW - фрустрирующая успешность

# Параметры для успешности с первой попытки
FIRST_TRY_TOO_EASY = 0.90  # Выше этого значения - слишком простая задача
FIRST_TRY_OPTIMAL_LOW = 0.65  # Нижняя граница оптимальной успешности с первой попытки
FIRST_TRY_MULTIPLE_LOW = 0.40  # Нижняя граница требующей нескольких попыток
# Ниже FIRST_TRY_MULTIPLE_LOW - сложная задача

COMPLAINTS_CRITICAL = 50  # Выше этого значения - критический уровень жалоб
COMPLAINTS_HIGH = 10  # Между этим и CRITICAL - высокий уровень
COMPLAINTS_MEDIUM = 5  # Между этим и HIGH - средний уровень
# Ниже COMPLAINTS_MEDIUM - низкий уровень жалоб

# Параметры для доли пытавшихся решить
ATTEMPTS_HIGH = 0.95  # Выше этого значения - высокая доля пытавшихся
ATTEMPTS_NORMAL_LOW = 0.80  # Нижняя граница нормальной доли
ATTEMPTS_INSUFFICIENT_LOW = 0.60  # Нижняя граница недостаточной доли
# Ниже ATTEMPTS_INSUFFICIENT_LOW - игнорируемая доля

# Веса для метрик
WEIGHT_COMPLAINT_RATE = 0.35
WEIGHT_SUCCESS_RATE = 0.25
WEIGHT_DISCRIMINATION = 0.20
WEIGHT_FIRST_TRY = 0.15
WEIGHT_ATTEMPTED = 0.05

# Параметры для комбинирования риска
ALPHA_WEIGHT_AVG = 0.7  # Вес для взвешенного среднего в комбинированной формуле
RISK_CRITICAL_THRESHOLD = 0.75  # Риск выше этого значения считается критическим
RISK_HIGH_THRESHOLD = 0.50  # Риск выше этого значения считается высоким
MIN_RISK_FOR_CRITICAL = 0.60  # Минимальный порог риска при наличии критической метрики
MIN_RISK_FOR_HIGH = 0.40  # Минимальный порог риска при наличии высокой риск-метрики

# Параметры для статистической значимости
STATS_SIGNIFICANCE_THRESHOLD = 100  # Количество попыток для полной статистической значимости
NEUTRAL_RISK_VALUE = 0.50  # Значение риска к которому смещаемся при малом числе попыток

# ------------------ Вспомогательные функции расчета риска ------------------
def discrimination_risk_score(discrimination_avg):
    """
    Рассчитывает риск (0-1) для дискриминативности.
    Хорошая: > 0.35 → 0-0.25
    Средняя: 0.15-0.35 → 0.26-0.50
    Низкая: < 0.15 → 0.51-1.0
    """
    if discrimination_avg >= DISCRIMINATION_GOOD:
        # Хорошая дискриминативность (0-0.25)
        # Чем выше значение, тем ниже риск
        normalized = min(1.0, (discrimination_avg - DISCRIMINATION_GOOD) / 0.4)
        return max(0, 0.25 * (1 - normalized))
    elif discrimination_avg >= DISCRIMINATION_MEDIUM:
        # Средняя дискриминативность (0.26-0.50)
        normalized = (discrimination_avg - DISCRIMINATION_MEDIUM) / (DISCRIMINATION_GOOD - DISCRIMINATION_MEDIUM)
        return 0.50 - normalized * 0.24  # 0.26-0.50
    else:
        # Низкая дискриминативность (0.51-1.0)
        # Чем ниже значение, тем выше риск
        normalized = max(0, discrimination_avg / DISCRIMINATION_MEDIUM)
        return 1.0 - normalized * 0.49  # 0.51-1.0

def success_rate_risk_score(success_rate):
    """
    Рассчитывает риск (0-1) для доли верных ответов.
    Скучная: > 0.95 → 0.30-0.40
    Оптимальная: 0.75-0.95 → 0-0.25
    Субоптимальная: 0.50-0.75 → 0.26-0.50
    Фрустрирующая: < 0.50 → 0.51-1.0
    """
    if success_rate > SUCCESS_BORING:
        # Скучная (слишком простая) задача (0.30-0.40)
        normalized = min(1.0, (success_rate - SUCCESS_BORING) / 0.05)
        return 0.30 + normalized * 0.10  # 0.30-0.40
    elif success_rate >= SUCCESS_OPTIMAL_LOW:
        # Оптимальная успешность (0-0.25)
        normalized = (success_rate - SUCCESS_OPTIMAL_LOW) / (SUCCESS_OPTIMAL_HIGH - SUCCESS_OPTIMAL_LOW)
        return 0.25 * (1 - normalized)  # 0-0.25
    elif success_rate >= SUCCESS_SUBOPTIMAL_LOW:
        # Субоптимальная успешность (0.26-0.50)
        normalized = (success_rate - SUCCESS_SUBOPTIMAL_LOW) / (SUCCESS_OPTIMAL_LOW - SUCCESS_SUBOPTIMAL_LOW)
        return 0.50 - normalized * 0.24  # 0.26-0.50
    else:
        # Фрустрирующая успешность (0.51-1.0)
        normalized = max(0, success_rate / SUCCESS_SUBOPTIMAL_LOW)
        return 1.0 - normalized * 0.49  # 0.51-1.0

def first_try_risk_score(first_try_success_rate):
    """
    Рассчитывает риск (0-1) для успешности с первой попытки.
    Слишком простая: > 0.90 → 0.26-0.35
    Оптимальная: 0.65-0.90 → 0-0.25
    Требует нескольких попыток: 0.40-0.65 → 0.26-0.50
    Сложная: < 0.40 → 0.51-1.0
    """
    if first_try_success_rate > FIRST_TRY_TOO_EASY:
        # Слишком простая задача (0.26-0.35)
        normalized = min(1.0, (first_try_success_rate - FIRST_TRY_TOO_EASY) / 0.1)
        return 0.26 + normalized * 0.09  # 0.26-0.35
    elif first_try_success_rate >= FIRST_TRY_OPTIMAL_LOW:
        # Оптимальная успешность с первой попытки (0-0.25)
        normalized = (first_try_success_rate - FIRST_TRY_OPTIMAL_LOW) / (FIRST_TRY_TOO_EASY - FIRST_TRY_OPTIMAL_LOW)
        return 0.25 * (1 - normalized)  # 0-0.25
    elif first_try_success_rate >= FIRST_TRY_MULTIPLE_LOW:
        # Требует нескольких попыток (0.26-0.50)
        normalized = (first_try_success_rate - FIRST_TRY_MULTIPLE_LOW) / (FIRST_TRY_OPTIMAL_LOW - FIRST_TRY_MULTIPLE_LOW)
        return 0.50 - normalized * 0.24  # 0.26-0.50
    else:
        # Сложная задача (0.51-1.0)
        normalized = max(0, first_try_success_rate / FIRST_TRY_MULTIPLE_LOW)
        return 1.0 - normalized * 0.49  # 0.51-1.0

def complaint_risk_score(row):
    """
    Рассчитывает риск (0-1) для количества жалоб.
    Критическая: > 50 → 0.76-1.0
    Высокая: 10-50 → 0.51-0.75
    Средняя: 5-10 → 0.26-0.50
    Низкая: < 5 → 0-0.25
    
    Parameters:
    -----------
    row : pd.Series
        Строка DataFrame с данными карточки. Должна содержать поле 'complaints_total'
        
    Returns:
    --------
    float
        Значение риска от 0 до 1
    """
    # Получаем абсолютное количество жалоб
    complaints_total = row.complaints_total if 'complaints_total' in row else 0
    
    if complaints_total > COMPLAINTS_CRITICAL:
        # Критический уровень жалоб (0.76-1.0)
        # Чем выше значение, тем выше риск
        excess = min(100, complaints_total - COMPLAINTS_CRITICAL)  # Ограничиваем избыток до 100
        normalized = excess / 100
        return 0.76 + normalized * 0.24  # 0.76-1.0
    elif complaints_total >= COMPLAINTS_HIGH:
        # Высокий уровень жалоб (0.51-0.75)
        normalized = (complaints_total - COMPLAINTS_HIGH) / (COMPLAINTS_CRITICAL - COMPLAINTS_HIGH)
        return 0.51 + normalized * 0.24  # 0.51-0.75
    elif complaints_total >= COMPLAINTS_MEDIUM:
        # Средний уровень жалоб (0.26-0.50)
        normalized = (complaints_total - COMPLAINTS_MEDIUM) / (COMPLAINTS_HIGH - COMPLAINTS_MEDIUM)
        return 0.26 + normalized * 0.24  # 0.26-0.50
    else:
        # Низкий уровень жалоб (0-0.25)
        normalized = complaints_total / COMPLAINTS_MEDIUM
        return normalized * 0.25  # 0-0.25

def attempted_share_risk_score(attempted_share):
    """
    Рассчитывает риск (0-1) для доли пытавшихся решить.
    Высокая: > 0.95 → 0-0.10
    Нормальная: 0.80-0.95 → 0-0.25
    Недостаточная: 0.60-0.80 → 0.26-0.50
    Игнорируемая: < 0.60 → 0.51-1.0
    """
    if attempted_share > ATTEMPTS_HIGH:
        # Высокая доля пытавшихся (0-0.10)
        normalized = min(1.0, (attempted_share - ATTEMPTS_HIGH) / 0.05)
        return 0.10 * (1 - normalized)  # 0-0.10
    elif attempted_share >= ATTEMPTS_NORMAL_LOW:
        # Нормальная доля пытавшихся (0-0.25)
        normalized = (attempted_share - ATTEMPTS_NORMAL_LOW) / (ATTEMPTS_HIGH - ATTEMPTS_NORMAL_LOW)
        return 0.25 - normalized * 0.15  # 0.10-0.25
    elif attempted_share >= ATTEMPTS_INSUFFICIENT_LOW:
        # Недостаточная доля пытавшихся (0.26-0.50)
        normalized = (attempted_share - ATTEMPTS_INSUFFICIENT_LOW) / (ATTEMPTS_NORMAL_LOW - ATTEMPTS_INSUFFICIENT_LOW)
        return 0.50 - normalized * 0.24  # 0.26-0.50
    else:
        # Игнорируемая доля пытавшихся (0.51-1.0)
        normalized = max(0, attempted_share / ATTEMPTS_INSUFFICIENT_LOW)
        return 1.0 - normalized * 0.49  # 0.51-1.0


def risk_score(row: pd.Series) -> float:
    """
    Расчет показателя риска для карточки на основе интервального подхода.
    
    Формула учитывает:
    - Успешность прохождения (success_rate)
    - Успешность с первой попытки (first_try_success_rate)
    - Количество жалоб (complaints_total) - абсолютное значение
    - Индекс дискриминативности (discrimination_avg)
    - Долю студентов, которые попытались решить (attempted_share)
    - Общее количество попыток (total_attempts) - как весовой фактор
    
    Возвращает значение от 0 до 1, где 1 - максимальный риск
    """
    # Рассчитываем риск для каждой метрики (0-1)
    risk_discr = discrimination_risk_score(row.discrimination_avg)
    risk_success = success_rate_risk_score(row.success_rate)
    risk_first_try = first_try_risk_score(row.first_try_success_rate)
    risk_complaints = complaint_risk_score(row)  # Передаем всю строку для доступа к complaints_total
    risk_attempted = attempted_share_risk_score(row.attempted_share)
    
    # Остальная часть функции остается без изменений
    # Определяем максимальный риск
    max_risk = max(risk_discr, risk_success, risk_first_try, risk_complaints, risk_attempted)
    
    # Рассчитываем взвешенное среднее
    weighted_avg_risk = (
        WEIGHT_DISCRIMINATION * risk_discr +
        WEIGHT_SUCCESS_RATE * risk_success +
        WEIGHT_FIRST_TRY * risk_first_try +
        WEIGHT_COMPLAINT_RATE * risk_complaints +
        WEIGHT_ATTEMPTED * risk_attempted
    )
    
    # Определяем минимальный порог риска на основе максимального риска
    if max_risk > RISK_CRITICAL_THRESHOLD:
        min_threshold = MIN_RISK_FOR_CRITICAL
    elif max_risk > RISK_HIGH_THRESHOLD:
        min_threshold = MIN_RISK_FOR_HIGH
    else:
        min_threshold = 0
    
    # Применяем комбинированную формулу
    combined_risk = ALPHA_WEIGHT_AVG * weighted_avg_risk + (1 - ALPHA_WEIGHT_AVG) * max_risk
    raw_risk = max(weighted_avg_risk, combined_risk, min_threshold)
    
    # Корректировка на статистическую значимость
    confidence_factor = min(row.total_attempts / STATS_SIGNIFICANCE_THRESHOLD, 1.0)
    adjusted_risk = raw_risk * confidence_factor + NEUTRAL_RISK_VALUE * (1 - confidence_factor)
    
    return adjusted_risk


def apply_filters(df: pd.DataFrame, upto: Optional[List[str]] = None) -> pd.DataFrame:
    cols = FILTERS if upto is None else upto
    for col in cols:
        v = st.session_state.get(f"filter_{col}")
        if v:
            df = df[df[col] == v]
    return df


def reset_child(level: str):
    """Сбрасывает дочерние фильтры относительно указанного уровня."""
    if level not in FILTERS:
        return
    
    idx = FILTERS.index(level)
    for col in FILTERS[idx+1:]:
        st.session_state[f"filter_{col}"] = None

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
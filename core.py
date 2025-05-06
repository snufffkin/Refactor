# core.py — утилиты / БД (исправлена рекурсия)
"""Содержит только функции.
Никаких глобальных `engine = core.get_engine()`!
"""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
import urllib.parse as ul
import numpy as np
import concurrent.futures
from functools import partial

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

from core_config import get_config
# ---------------- DB ------------------------------------------------------- #

def get_engine():
    # Строка подключения к удаленной базе данных в Яндекс.Облаке
    cloud_dsn = "postgresql://romannikitin:changeme123@rc1b-fkbqfy1dg88d0134.mdb.yandexcloud.net:6432/course_quality?sslmode=verify-full&sslrootcert=/Users/romannikitin/.postgresql/root.crt"
    # Используем переменную окружения, если она задана, иначе используем строку подключения к облаку
    dsn = os.getenv("DB_DSN", cloud_dsn)
    return create_engine(dsn, future=True)

@st.cache_data(ttl=3600)  # Кэширование на 1 час (3600 секунд)
def load_raw_data(_engine):
    """
    Загружает сырые данные из базы данных.
    Функция кэшируется с большим TTL для оптимизации обращений к БД.
    
    Args:
        _engine: SQLAlchemy engine для подключения к БД (не хешируемый параметр)
        
    Returns:
        DataFrame с данными из таблицы cards_mv
    """
    sql = text(
        """
        SELECT program,module,module_order,lesson,lesson_order,
               gz,gz_id,card_id,card_type,card_url,
               total_attempts,attempted_share,success_rate,first_try_success_rate,
               complaint_rate,complaints_total,discrimination_avg,success_attempts_rate,
               time_median,complaints_text,
               status,updated_at
        FROM cards_mv
        """
    )
    return pd.read_sql(sql, _engine)

@st.cache_data(ttl=300)  # Кэширование на 5 минут (300 секунд)
def process_data(raw_data):
    """
    Обрабатывает сырые данные, добавляя вычисляемые метрики.
    Функция кэшируется с коротким TTL для обновления обработанных данных.
    
    Args:
        raw_data: DataFrame с сырыми данными из load_raw_data
        
    Returns:
        DataFrame с обработанными данными и дополнительными метриками
    """
    # Копируем данные, чтобы не модифицировать оригинал
    df = raw_data.copy()
    
    # Вычисляем риск для всего DataFrame векторизованно
    df['risk'] = calculate_risk_score(df)
    
    return df

# Для обратной совместимости
def load_data(_engine):
    """
    Загружает и обрабатывает данные (устаревшая функция для обратной совместимости).
    Рекомендуется использовать комбинацию load_raw_data и process_data.
    
    Args:
        _engine: SQLAlchemy engine для подключения к БД (не хешируемый параметр)
    """
    raw_data = load_raw_data(_engine)
    return process_data(raw_data)

# ---------------- Filters / Risk ------------------------------------------ #

FILTERS: List[str] = ["program", "module", "lesson", "gz"]  # Добавил "gz" в список фильтров

# Обновленная функция расчета риска на основе интервалов
# Добавьте эти функции в файл core.py


# ------------------ Вспомогательные функции расчета риска ------------------
def discrimination_risk_score(discrimination_avg):
    """
    Рассчитывает риск (0-1) для дискриминативности.
    Хорошая: > 0.35 → 0-0.25
    Средняя: 0.15-0.35 → 0.26-0.50
    Низкая: < 0.15 → 0.51-1.0
    
    Использует параметры из конфигурации.
    """
    # Создаем временный DataFrame с одним значением
    temp_df = pd.DataFrame({'discrimination_avg': [discrimination_avg]})
    return calculate_discrimination_risk(temp_df)[0]

def success_rate_risk_score(success_rate):
    """
    Рассчитывает риск (0-1) для доли верных ответов.
    Скучная: > 0.95 → 0.30-0.40
    Оптимальная: 0.75-0.95 → 0-0.25
    Субоптимальная: 0.50-0.75 → 0.26-0.50
    Фрустрирующая: < 0.50 → 0.51-1.0
    
    Использует параметры из конфигурации.
    """
    # Создаем временный DataFrame с одним значением
    temp_df = pd.DataFrame({'success_rate': [success_rate]})
    return calculate_success_rate_risk(temp_df)[0]

def first_try_risk_score(first_try_success_rate):
    """
    Рассчитывает риск (0-1) для успешности с первой попытки.
    Слишком простая: > 0.90 → 0.26-0.35
    Оптимальная: 0.65-0.90 → 0-0.25
    Требует нескольких попыток: 0.40-0.65 → 0.26-0.50
    Сложная: < 0.40 → 0.51-1.0
    
    Использует параметры из конфигурации.
    """
    # Создаем временный DataFrame с одним значением
    temp_df = pd.DataFrame({'first_try_success_rate': [first_try_success_rate]})
    return calculate_first_try_risk(temp_df)[0]

def complaint_risk_score(row):
    """
    Рассчитывает риск (0-1) для количества жалоб.
    Критическая: > 50 → 0.76-1.0
    Высокая: 10-50 → 0.51-0.75
    Средняя: 5-10 → 0.26-0.50
    Низкая: < 5 → 0-0.25
    
    Parameters:
    -----------
    row : pd.Series или dict
        Строка DataFrame с данными карточки или словарь с данными.
        Должен содержать поле 'complaints_total' или 'complaint_rate' и 'total_attempts'
        
    Returns:
    --------
    float
        Значение риска от 0 до 1
        
    Использует параметры из конфигурации.
    """
    # Создаем временный DataFrame из одной строки
    if isinstance(row, dict) or hasattr(row, 'get'):
        temp_df = pd.DataFrame([row])
    else:
        # Если это не словарь, пытаемся создать словарь
        try:
            temp_dict = {'complaints_total': getattr(row, 'complaints_total', 0)}
            if temp_dict['complaints_total'] == 0 and hasattr(row, 'complaint_rate') and hasattr(row, 'total_attempts'):
                temp_dict['complaints_total'] = row.complaint_rate * row.total_attempts
            temp_df = pd.DataFrame([temp_dict])
        except Exception:
            # В случае ошибки используем нулевое значение
            temp_df = pd.DataFrame({'complaints_total': [0]})
    
    return calculate_complaint_risk(temp_df)[0]

def attempted_share_risk_score(attempted_share):
    """
    Рассчитывает риск (0-1) для доли пытавшихся решить.
    Высокая: > 0.95 → 0-0.10
    Нормальная: 0.80-0.95 → 0-0.25
    Недостаточная: 0.60-0.80 → 0.26-0.50
    Игнорируемая: < 0.60 → 0.51-1.0
    
    Использует параметры из конфигурации.
    """
    # Создаем временный DataFrame с одним значением
    temp_df = pd.DataFrame({'attempted_share': [attempted_share]})
    return calculate_attempted_share_risk(temp_df)[0]

# Заменяем старую функцию get_trickiness_level на векторизованную версию
def calculate_trickiness_level(df):
    """
    Векторизованная функция для определения уровня "подлости" карточек.
    
    Args:
        df: DataFrame с данными карточек
        
    Returns:
        Series: Уровни "подлости" для каждой карточки (0 - нет, 1 - низкий, 2 - средний, 3 - высокий)
    """
    # Получаем параметры из конфигурации
    config = get_config()
    tricky_config = config.get("tricky_cards", {})
    
    # Базовые параметры
    basic_config = tricky_config.get("basic", {})
    min_success_rate = basic_config.get("min_success_rate", 0.70)
    max_first_try_rate = basic_config.get("max_first_try_rate", 0.60)
    min_difference = basic_config.get("min_difference", 0.20)
    
    # Параметры зон
    zones_config = tricky_config.get("zones", {})
    high_success_threshold = zones_config.get("high_success_threshold", 0.90)
    medium_success_threshold = zones_config.get("medium_success_threshold", 0.80)
    low_first_try_threshold = zones_config.get("low_first_try_threshold", 0.40)
    medium_first_try_threshold = zones_config.get("medium_first_try_threshold", 0.50)
    
    # Вычисляем разницу между success_rate и first_try_success_rate для всех строк
    success_diff = df["success_rate"] - df["first_try_success_rate"]
    
    # Создаем маску для трики-карточек
    is_tricky = (
        (df["success_rate"] >= min_success_rate) & 
        (df["first_try_success_rate"] <= max_first_try_rate) &
        (success_diff >= min_difference)
    )
    
    # Используем np.select для векторизованного определения уровня
    conditions = [
        ~is_tricky,  # Не трики-карточки
        is_tricky & (df["success_rate"] >= high_success_threshold) & 
            (df["first_try_success_rate"] <= low_first_try_threshold),  # Высокий уровень (3)
        is_tricky & (df["success_rate"] >= medium_success_threshold) &
            (df["first_try_success_rate"] <= medium_first_try_threshold)  # Средний уровень (2)
    ]
    
    choices = [0, 3, 2]
    
    # Все остальные трики-карточки получат значение 1 (низкий уровень)
    default = np.where(is_tricky, 1, 0)
    
    return np.select(conditions, choices, default=default)

# Для обратной совместимости оставляем функцию get_trickiness_level, но реализуем ее через векторизованную версию
def get_trickiness_level(row):
    """
    Определяет уровень "подлости" карточки на основе успешности и успешности с первой попытки.
    
    Args:
        row: Строка DataFrame с данными карточки
        
    Returns:
        int: Уровень "подлости" (0 - нет, 1 - низкий, 2 - средний, 3 - высокий)
    """
    # Создаем временный DataFrame из одной строки
    temp_df = pd.DataFrame([row])
    # Используем векторизованную функцию
    return calculate_trickiness_level(temp_df)[0]

# Векторизованная версия функции trickiness_risk_score
def calculate_trickiness_risk(df):
    """
    Векторизованная функция для расчета риска на основе уровня "подлости" карточек.
    
    Args:
        df: DataFrame с данными карточек
        
    Returns:
        Series: Значения риска от 0 до 1 для каждой карточки
    """
    # Сначала рассчитываем уровень подлости
    trickiness_level = calculate_trickiness_level(df)
    
    # Используем np.select для векторизованного выбора значений риска
    conditions = [
        trickiness_level == 0,
        trickiness_level == 1,
        trickiness_level == 2,
        trickiness_level == 3
    ]
    
    choices = [0.0, 0.3, 0.6, 0.9]
    
    return np.select(conditions, choices, default=0.0)

# Обновляем функцию trickiness_risk_score для обратной совместимости
def trickiness_risk_score(row):
    """
    Рассчитывает риск (0-1) на основе уровня "подлости" карточки.
    
    Args:
        row: Строка DataFrame с данными карточки
        
    Returns:
        float: Значение риска от 0 до 1
    """
    # Создаем временный DataFrame из одной строки
    temp_df = pd.DataFrame([row])
    # Используем векторизованную функцию
    return calculate_trickiness_risk(temp_df)[0]

# ------------------ Векторизованные функции расчета риска ------------------
def calculate_discrimination_risk(df):
    """
    Векторизованная функция для расчета риска (0-1) для дискриминативности.
    
    Args:
        df: DataFrame с данными карточек
        
    Returns:
        Series: Значения риска от 0 до 1 для каждой карточки
    """
    # Получаем параметры из конфигурации
    config = get_config()
    DISCRIMINATION_GOOD = config["discrimination"]["good"]
    DISCRIMINATION_MEDIUM = config["discrimination"]["medium"]
    
    # Создаем условия и соответствующие выражения
    conditions = [
        df.discrimination_avg >= DISCRIMINATION_GOOD,  # Хорошая дискриминативность
        df.discrimination_avg >= DISCRIMINATION_MEDIUM  # Средняя дискриминативность
    ]
    
    # Вычисляем normalized для каждого условия
    norm_high = np.minimum(1.0, (df.discrimination_avg - DISCRIMINATION_GOOD) / 0.4)
    norm_medium = (df.discrimination_avg - DISCRIMINATION_MEDIUM) / (DISCRIMINATION_GOOD - DISCRIMINATION_MEDIUM)
    norm_low = np.maximum(0, df.discrimination_avg / DISCRIMINATION_MEDIUM)
    
    # Выбираем соответствующие значения риска
    high_risk = np.maximum(0, 0.25 * (1 - norm_high))  # 0-0.25
    medium_risk = 0.50 - norm_medium * 0.24  # 0.26-0.50
    low_risk = 1.0 - norm_low * 0.49  # 0.51-1.0
    
    # Используем np.select для выбора значений
    choices = [high_risk, medium_risk]
    default = low_risk
    
    return np.select(conditions, choices, default=default)

def calculate_success_rate_risk(df):
    """
    Векторизованная функция для расчета риска (0-1) для доли верных ответов.
    
    Args:
        df: DataFrame с данными карточек
        
    Returns:
        Series: Значения риска от 0 до 1 для каждой карточки
    """
    # Получаем параметры из конфигурации
    config = get_config()
    SUCCESS_BORING = config["success_rate"]["boring"]
    SUCCESS_OPTIMAL_HIGH = config["success_rate"]["optimal_high"]
    SUCCESS_OPTIMAL_LOW = config["success_rate"]["optimal_low"]
    SUCCESS_SUBOPTIMAL_LOW = config["success_rate"]["suboptimal_low"]
    
    # Создаем условия
    conditions = [
        df.success_rate > SUCCESS_BORING,  # Скучная задача
        df.success_rate >= SUCCESS_OPTIMAL_LOW,  # Оптимальная успешность
        df.success_rate >= SUCCESS_SUBOPTIMAL_LOW  # Субоптимальная успешность
    ]
    
    # Вычисляем normalized для каждого условия
    norm_boring = np.minimum(1.0, (df.success_rate - SUCCESS_BORING) / 0.05)
    norm_optimal = (df.success_rate - SUCCESS_OPTIMAL_LOW) / (SUCCESS_OPTIMAL_HIGH - SUCCESS_OPTIMAL_LOW)
    norm_suboptimal = (df.success_rate - SUCCESS_SUBOPTIMAL_LOW) / (SUCCESS_OPTIMAL_LOW - SUCCESS_SUBOPTIMAL_LOW)
    norm_frustrating = np.maximum(0, df.success_rate / SUCCESS_SUBOPTIMAL_LOW)
    
    # Выбираем соответствующие значения риска
    boring_risk = 0.30 + norm_boring * 0.10  # 0.30-0.40
    optimal_risk = 0.25 * (1 - norm_optimal)  # 0-0.25
    suboptimal_risk = 0.50 - norm_suboptimal * 0.24  # 0.26-0.50
    frustrating_risk = 1.0 - norm_frustrating * 0.49  # 0.51-1.0
    
    # Используем np.select для выбора значений
    choices = [boring_risk, optimal_risk, suboptimal_risk]
    default = frustrating_risk
    
    return np.select(conditions, choices, default=default)

def calculate_first_try_risk(df):
    """
    Векторизованная функция для расчета риска (0-1) для успешности с первой попытки.
    
    Args:
        df: DataFrame с данными карточек
        
    Returns:
        Series: Значения риска от 0 до 1 для каждой карточки
    """
    # Получаем параметры из конфигурации
    config = get_config()
    FIRST_TRY_TOO_EASY = config["first_try"]["too_easy"]
    FIRST_TRY_OPTIMAL_LOW = config["first_try"]["optimal_low"]
    FIRST_TRY_MULTIPLE_LOW = config["first_try"]["multiple_low"]
    
    # Создаем условия
    conditions = [
        df.first_try_success_rate > FIRST_TRY_TOO_EASY,  # Слишком простая задача
        df.first_try_success_rate >= FIRST_TRY_OPTIMAL_LOW,  # Оптимальная успешность
        df.first_try_success_rate >= FIRST_TRY_MULTIPLE_LOW  # Требует нескольких попыток
    ]
    
    # Вычисляем normalized для каждого условия
    norm_easy = np.minimum(1.0, (df.first_try_success_rate - FIRST_TRY_TOO_EASY) / 0.1)
    norm_optimal = (df.first_try_success_rate - FIRST_TRY_OPTIMAL_LOW) / (FIRST_TRY_TOO_EASY - FIRST_TRY_OPTIMAL_LOW)
    norm_multiple = (df.first_try_success_rate - FIRST_TRY_MULTIPLE_LOW) / (FIRST_TRY_OPTIMAL_LOW - FIRST_TRY_MULTIPLE_LOW)
    norm_hard = np.maximum(0, df.first_try_success_rate / FIRST_TRY_MULTIPLE_LOW)
    
    # Выбираем соответствующие значения риска
    easy_risk = 0.26 + norm_easy * 0.09  # 0.26-0.35
    optimal_risk = 0.25 * (1 - norm_optimal)  # 0-0.25
    multiple_risk = 0.50 - norm_multiple * 0.24  # 0.26-0.50
    hard_risk = 1.0 - norm_hard * 0.49  # 0.51-1.0
    
    # Используем np.select для выбора значений
    choices = [easy_risk, optimal_risk, multiple_risk]
    default = hard_risk
    
    return np.select(conditions, choices, default=default)

def calculate_complaint_risk(df):
    """
    Векторизованная функция для расчета риска (0-1) для количества жалоб.
    
    Args:
        df: DataFrame с данными карточек
        
    Returns:
        Series: Значения риска от 0 до 1 для каждой карточки
    """
    # Получаем параметры из конфигурации
    config = get_config()
    COMPLAINTS_CRITICAL = config["complaints"]["critical"]
    COMPLAINTS_HIGH = config["complaints"]["high"]
    COMPLAINTS_MEDIUM = config["complaints"]["medium"]
    
    # Определяем общее количество жалоб
    complaints_total = df['complaints_total']
    
    # Проверяем, что complaints_total имеет числовой тип
    complaints_total = pd.to_numeric(complaints_total, errors='coerce').fillna(0)
    
    # Создаем условия
    conditions = [
        complaints_total > COMPLAINTS_CRITICAL,  # Критический уровень
        complaints_total >= COMPLAINTS_HIGH,  # Высокий уровень
        complaints_total >= COMPLAINTS_MEDIUM  # Средний уровень
    ]
    
    # Вычисляем normalized для каждого условия
    excess = np.minimum(100, complaints_total - COMPLAINTS_CRITICAL)
    norm_critical = excess / 100
    norm_high = (complaints_total - COMPLAINTS_HIGH) / (COMPLAINTS_CRITICAL - COMPLAINTS_HIGH)
    norm_medium = (complaints_total - COMPLAINTS_MEDIUM) / (COMPLAINTS_HIGH - COMPLAINTS_MEDIUM)
    norm_low = complaints_total / np.maximum(1, COMPLAINTS_MEDIUM)
    
    # Выбираем соответствующие значения риска
    critical_risk = 0.76 + norm_critical * 0.24  # 0.76-1.0
    high_risk = 0.51 + norm_high * 0.24  # 0.51-0.75
    medium_risk = 0.26 + norm_medium * 0.24  # 0.26-0.50
    low_risk = norm_low * 0.25  # 0-0.25
    
    # Используем np.select для выбора значений
    choices = [critical_risk, high_risk, medium_risk]
    default = low_risk
    
    return np.select(conditions, choices, default=default)

def calculate_attempted_share_risk(df):
    """
    Векторизованная функция для расчета риска (0-1) для доли пытавшихся решить.
    
    Args:
        df: DataFrame с данными карточек
        
    Returns:
        Series: Значения риска от 0 до 1 для каждой карточки
    """
    # Получаем параметры из конфигурации
    config = get_config()
    ATTEMPTS_HIGH = config["attempts"]["high"]
    ATTEMPTS_NORMAL_LOW = config["attempts"]["normal_low"]
    ATTEMPTS_INSUFFICIENT_LOW = config["attempts"]["insufficient_low"]
    
    # Создаем условия
    conditions = [
        df.attempted_share > ATTEMPTS_HIGH,  # Высокая доля
        df.attempted_share >= ATTEMPTS_NORMAL_LOW,  # Нормальная доля
        df.attempted_share >= ATTEMPTS_INSUFFICIENT_LOW  # Недостаточная доля
    ]
    
    # Вычисляем normalized для каждого условия
    norm_high = np.minimum(1.0, (df.attempted_share - ATTEMPTS_HIGH) / 0.05)
    norm_normal = (df.attempted_share - ATTEMPTS_NORMAL_LOW) / (ATTEMPTS_HIGH - ATTEMPTS_NORMAL_LOW)
    norm_insufficient = (df.attempted_share - ATTEMPTS_INSUFFICIENT_LOW) / (ATTEMPTS_NORMAL_LOW - ATTEMPTS_INSUFFICIENT_LOW)
    norm_ignored = np.maximum(0, df.attempted_share / ATTEMPTS_INSUFFICIENT_LOW)
    
    # Выбираем соответствующие значения риска
    high_risk = 0.10 * (1 - norm_high)  # 0-0.10
    normal_risk = 0.25 - norm_normal * 0.15  # 0.10-0.25
    insufficient_risk = 0.50 - norm_insufficient * 0.24  # 0.26-0.50
    ignored_risk = 1.0 - norm_ignored * 0.49  # 0.51-1.0
    
    # Используем np.select для выбора значений
    choices = [high_risk, normal_risk, insufficient_risk]
    default = ignored_risk
    
    return np.select(conditions, choices, default=default)

def calculate_risk_score(df):
    """
    Векторизованная функция для расчета показателя риска для всех карточек.
    
    Args:
        df: DataFrame с данными карточек
        
    Returns:
        Series: Значения риска от 0 до 1 для каждой карточки
    """
    # Получаем параметры из конфигурации
    config = get_config()
    WEIGHT_DISCRIMINATION = config["weights"]["discrimination"]
    WEIGHT_SUCCESS_RATE = config["weights"]["success_rate"]
    WEIGHT_TRICKINESS = config["weights"].get("trickiness", 0.15)
    WEIGHT_COMPLAINT_RATE = config["weights"]["complaint_rate"]
    WEIGHT_ATTEMPTED = config["weights"]["attempted"]
    
    RISK_CRITICAL_THRESHOLD = config["risk_thresholds"]["critical"]
    RISK_HIGH_THRESHOLD = config["risk_thresholds"]["high"]
    MIN_RISK_FOR_CRITICAL = config["risk_thresholds"]["min_for_critical"]
    MIN_RISK_FOR_HIGH = config["risk_thresholds"]["min_for_high"]
    ALPHA_WEIGHT_AVG = config["risk_thresholds"]["alpha_weight_avg"]
    
    # Получаем параметр, отвечающий за использование минимального порога
    USE_MIN_THRESHOLD = config["risk_thresholds"].get("use_min_threshold", True)
    
    STATS_SIGNIFICANCE_THRESHOLD = config["stats"]["significance_threshold"]
    NEUTRAL_RISK_VALUE = config["stats"]["neutral_risk_value"]
    
    # Рассчитываем риск для каждой метрики (0-1)
    risk_discr = calculate_discrimination_risk(df)
    risk_success = calculate_success_rate_risk(df)
    risk_trickiness = calculate_trickiness_risk(df)
    risk_complaints = calculate_complaint_risk(df)
    risk_attempted = calculate_attempted_share_risk(df)
    
    # Определяем максимальный риск для каждой строки
    max_risk = np.maximum.reduce([risk_discr, risk_success, risk_trickiness, risk_complaints, risk_attempted])
    
    # Рассчитываем взвешенное среднее
    weighted_avg_risk = (
        WEIGHT_DISCRIMINATION * risk_discr +
        WEIGHT_SUCCESS_RATE * risk_success +
        WEIGHT_TRICKINESS * risk_trickiness +
        WEIGHT_COMPLAINT_RATE * risk_complaints +
        WEIGHT_ATTEMPTED * risk_attempted
    )
    
    # Определяем минимальный порог риска на основе максимального риска
    if USE_MIN_THRESHOLD:
        min_threshold = np.where(
            max_risk > RISK_CRITICAL_THRESHOLD, 
            MIN_RISK_FOR_CRITICAL,
            np.where(max_risk > RISK_HIGH_THRESHOLD, MIN_RISK_FOR_HIGH, 0)
        )
    else:
        # Если не используем минимальный порог, создаем массив нулей той же длины
        min_threshold = np.zeros_like(weighted_avg_risk)
    
    # Применяем комбинированную формулу
    combined_risk = ALPHA_WEIGHT_AVG * weighted_avg_risk + (1 - ALPHA_WEIGHT_AVG) * max_risk
    
    # Используем попарный максимум вместо reduce для большей устойчивости
    raw_risk = np.maximum(weighted_avg_risk, combined_risk)
    raw_risk = np.maximum(raw_risk, min_threshold)
    
    # Корректировка на статистическую значимость
    confidence_factor = np.minimum(df.total_attempts / STATS_SIGNIFICANCE_THRESHOLD, 1.0)
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
    
    # Определяем уровень подлости для каждой карточки векторизованно
    df_risk['trickiness_level'] = calculate_trickiness_level(df_risk)
    
    # Рассчитываем компоненты риска векторизованно
    df_risk['risk_success'] = 1 - df_risk.success_rate
    df_risk['risk_trickiness'] = calculate_trickiness_risk(df_risk)
    df_risk['risk_complaints'] = np.minimum(df_risk.complaint_rate * 3, 1)
    df_risk['risk_discrimination'] = 1 - df_risk.discrimination_avg
    df_risk['risk_attempted'] = 1 - df_risk.attempted_share
    
    # Получаем параметры из конфигурации
    config = get_config()
    WEIGHT_DISCRIMINATION = config["weights"]["discrimination"]
    WEIGHT_SUCCESS_RATE = config["weights"]["success_rate"]
    WEIGHT_TRICKINESS = config["weights"].get("trickiness", 0.15)
    WEIGHT_COMPLAINT_RATE = config["weights"]["complaint_rate"]
    WEIGHT_ATTEMPTED = config["weights"]["attempted"]
    
    # Добавляем информацию о весах компонентов
    df_risk['weight_success'] = WEIGHT_SUCCESS_RATE
    df_risk['weight_trickiness'] = WEIGHT_TRICKINESS
    df_risk['weight_complaints'] = WEIGHT_COMPLAINT_RATE
    df_risk['weight_discrimination'] = WEIGHT_DISCRIMINATION
    df_risk['weight_attempted'] = WEIGHT_ATTEMPTED
    
    # Рассчитываем вклады в итоговый риск
    df_risk['contrib_success'] = df_risk.risk_success * df_risk.weight_success
    df_risk['contrib_trickiness'] = df_risk.risk_trickiness * df_risk.weight_trickiness
    df_risk['contrib_complaints'] = df_risk.risk_complaints * df_risk.weight_complaints
    df_risk['contrib_discrimination'] = df_risk.risk_discrimination * df_risk.weight_discrimination
    df_risk['contrib_attempted'] = df_risk.risk_attempted * df_risk.weight_attempted
    
    # Рассчитываем сырой риск без учета количества попыток
    df_risk['raw_risk'] = (
        df_risk.contrib_success +
        df_risk.contrib_trickiness +
        df_risk.contrib_complaints +
        df_risk.contrib_discrimination +
        df_risk.contrib_attempted
    )
    
    # Фактор доверия на основе количества попыток
    df_risk['confidence_factor'] = np.minimum(df_risk.total_attempts / 100, 1.0)
    
    # Итоговый скорректированный риск
    df_risk['adjusted_risk'] = df_risk.raw_risk * df_risk.confidence_factor + 0.5 * (1 - df_risk.confidence_factor)
    
    return df_risk

# Обновляем функцию risk_score для использования векторизованной функции
def risk_score(row):
    """
    Расчет показателя риска для одной карточки на основе интервального подхода.
    Обертка для векторизованной функции calculate_risk_score.
    
    Формула учитывает:
    - Успешность прохождения (success_rate)
    - Уровень "подлости" карточки (trickiness) - вместо first_try_success_rate
    - Количество жалоб (complaints_total) - абсолютное значение
    - Индекс дискриминативности (discrimination_avg)
    - Долю студентов, которые попытались решить (attempted_share)
    - Общее количество попыток (total_attempts) - как весовой фактор
    
    Возвращает значение от 0 до 1, где 1 - максимальный риск
    
    Args:
        row: Строка DataFrame с данными карточки
        
    Returns:
        float: Значение риска от 0 до 1
    """
    # Создаем временный DataFrame из одной строки
    temp_df = pd.DataFrame([row])
    
    # Используем векторизованную функцию для расчета риска
    # Используем .iloc[0] вместо [0], чтобы избежать проблем с индексацией
    result = calculate_risk_score(temp_df)
    return result.iloc[0] if isinstance(result, pd.Series) else result[0]

# Добавляем функции для загрузки данных для конкретного уровня навигации

@st.cache_data(ttl=1800)  # Кэширование на 30 минут
def load_program_data(_engine=None):
    """
    Загружает агрегированные данные на уровне программ.
    Использует материализованное представление mv_program_risk.
    
    Args:
        _engine: SQLAlchemy engine для подключения к БД (не хешируемый параметр)
        
    Returns:
        DataFrame с данными программ, включая статистику и риски
    """
    if _engine is None:
        _engine = get_engine()
        
    sql = text(
        """
        SELECT 
            p.*,
            r.avg_risk
        FROM mv_program_stats p
        LEFT JOIN mv_program_risk r USING(program)
        ORDER BY program
        """
    )
    return pd.read_sql(sql, _engine)

@st.cache_data(ttl=1800)  # Кэширование на 30 минут
def load_module_data(program=None, _engine=None):
    """
    Загружает агрегированные данные на уровне модулей для указанной программы.
    Использует материализованное представление mv_module_risk.
    
    Args:
        program: Название программы для фильтрации (None для всех программ)
        _engine: SQLAlchemy engine для подключения к БД (не хешируемый параметр)
        
    Returns:
        DataFrame с данными модулей, включая статистику и риски
    """
    if _engine is None:
        _engine = get_engine()
    
    query = """
        SELECT 
            m.*,
            r.avg_risk
        FROM mv_module_stats m
        LEFT JOIN mv_module_risk r USING(program, module, module_order)
    """
    
    params = {}
    if program:
        query += " WHERE m.program = :program"
        params["program"] = program
        
    query += " ORDER BY m.program, m.module_order"
    
    return pd.read_sql(text(query), _engine, params=params)

@st.cache_data(ttl=1800)  # Кэширование на 30 минут
def load_lesson_data(program=None, module=None, _engine=None):
    """
    Загружает агрегированные данные на уровне уроков для указанной программы и модуля.
    Использует материализованное представление mv_lesson_risk.
    
    Args:
        program: Название программы для фильтрации (None для всех программ)
        module: Название модуля для фильтрации (None для всех модулей)
        _engine: SQLAlchemy engine для подключения к БД (не хешируемый параметр)
        
    Returns:
        DataFrame с данными уроков, включая статистику и риски
    """
    if _engine is None:
        _engine = get_engine()
    
    query = """
        SELECT 
            l.*,
            r.avg_risk
        FROM mv_lesson_stats l
        LEFT JOIN mv_lesson_risk r USING(program, module, module_order, lesson, lesson_order)
    """
    
    params = {}
    where_clauses = []
    
    if program:
        where_clauses.append("l.program = :program")
        params["program"] = program
        
    if module:
        where_clauses.append("l.module = :module")
        params["module"] = module
    
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
        
    query += " ORDER BY l.program, l.module_order, l.lesson_order"
    
    return pd.read_sql(text(query), _engine, params=params)

@st.cache_data(ttl=1800)  # Кэширование на 30 минут
def load_gz_data(program=None, module=None, lesson=None, _engine=None):
    """
    Загружает агрегированные данные на уровне групп заданий (ГЗ) для указанных параметров.
    Использует материализованное представление mv_gz_risk.
    
    Args:
        program: Название программы для фильтрации (None для всех программ)
        module: Название модуля для фильтрации (None для всех модулей)
        lesson: Название урока для фильтрации (None для всех уроков)
        _engine: SQLAlchemy engine для подключения к БД (не хешируемый параметр)
        
    Returns:
        DataFrame с данными групп заданий, включая статистику и риски
    """
    if _engine is None:
        _engine = get_engine()
    
    query = """
        SELECT 
            g.*,
            r.avg_risk
        FROM mv_gz_stats g
        LEFT JOIN mv_gz_risk r USING(program, module, module_order, lesson, lesson_order, gz, gz_id)
    """
    
    params = {}
    where_clauses = []
    
    if program:
        where_clauses.append("g.program = :program")
        params["program"] = program
        
    if module:
        where_clauses.append("g.module = :module")
        params["module"] = module
        
    if lesson:
        where_clauses.append("g.lesson = :lesson")
        params["lesson"] = lesson
    
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
        
    query += " ORDER BY g.program, g.module_order, g.lesson_order, g.gz"
    
    return pd.read_sql(text(query), _engine, params=params)

@st.cache_data(ttl=1800)  # Кэширование на 30 минут
def load_card_data(program=None, module=None, lesson=None, gz=None, _engine=None):
    """
    Загружает данные карточек для указанных параметров фильтрации.
    Использует материализованное представление mv_cards_mv и данные о риске.
    
    Args:
        program: Название программы для фильтрации (None для всех программ)
        module: Название модуля для фильтрации (None для всех модулей)
        lesson: Название урока для фильтрации (None для всех уроков)
        gz: Название группы заданий для фильтрации (None для всех групп)
        _engine: SQLAlchemy engine для подключения к БД (не хешируемый параметр)
        
    Returns:
        DataFrame с данными карточек, включая все метрики и риск
    """
    if _engine is None:
        _engine = get_engine()
    
    query = """
        SELECT 
            c.*,
            r.risk
        FROM mv_cards_mv c
        LEFT JOIN card_risk_cache r ON c.card_id = r.card_id
    """
    
    params = {}
    where_clauses = []
    
    if program:
        where_clauses.append("c.program = :program")
        params["program"] = program
        
    if module:
        where_clauses.append("c.module = :module")
        params["module"] = module
        
    if lesson:
        where_clauses.append("c.lesson = :lesson")
        params["lesson"] = lesson
        
    if gz:
        where_clauses.append("c.gz = :gz")
        params["gz"] = gz
    
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
        
    query += " ORDER BY c.program, c.module_order, c.lesson_order, c.gz"
    
    return pd.read_sql(text(query), _engine, params=params)

@st.cache_data(ttl=1800)  # Кэширование на 30 минут
def load_top_cards_by_risk(gz=None, limit=10, _engine=None):
    """
    Загружает карточки с наивысшим риском для указанной группы заданий или для всех групп.
    
    Args:
        gz: Название группы заданий для фильтрации (None для всех групп)
        limit: Максимальное количество карточек для каждой группы заданий
        _engine: SQLAlchemy engine для подключения к БД (не хешируемый параметр)
        
    Returns:
        DataFrame с данными топ-карточек по риску
    """
    if _engine is None:
        _engine = get_engine()
    
    query = """
        SELECT 
            t.gz, t.card_id, t.risk, t.rn,
            c.program, c.module, c.lesson, c.card_type, c.card_url
        FROM top10_by_group t
        JOIN mv_cards_mv c ON t.card_id = c.card_id
    """
    
    params = {}
    if gz:
        query += " WHERE t.gz = :gz"
        params["gz"] = gz
    
    if limit:
        query += " AND t.rn <= :limit"
        params["limit"] = limit
        
    query += " ORDER BY t.gz, t.rn"
    
    return pd.read_sql(text(query), _engine, params=params)

# ------------------ Параллельная загрузка данных --------------------- #

def execute_in_parallel(functions_with_args, max_workers=4):
    """
    Выполняет несколько функций параллельно и возвращает их результаты.
    
    Args:
        functions_with_args: Список кортежей (функция, аргументы), где аргументы - словарь
        max_workers: Максимальное количество параллельных рабочих потоков
        
    Returns:
        dict: Результаты выполнения функций в формате {имя_функции: результат}
    """
    results = {}
    
    def execute_function(func_info):
        func, args = func_info
        try:
            return func.__name__, func(**args)
        except Exception as e:
            return func.__name__, f"Error: {str(e)}"
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_func = {executor.submit(execute_function, func_info): func_info for func_info in functions_with_args}
        for future in concurrent.futures.as_completed(future_to_func):
            func_name, result = future.result()
            results[func_name] = result
    
    return results

@st.cache_data(ttl=1800)
def load_data_parallel(program=None, module=None, lesson=None, gz=None, _engine=None):
    """
    Загружает несколько наборов данных параллельно в зависимости от уровня навигации.
    
    Args:
        program: Название программы для фильтрации
        module: Название модуля для фильтрации
        lesson: Название урока для фильтрации
        gz: Название группы заданий для фильтрации
        _engine: SQLAlchemy engine для подключения к БД
        
    Returns:
        dict: Словарь с различными наборами данных
    """
    if _engine is None:
        _engine = get_engine()
        
    functions_with_args = []
    
    # Определяем, какие данные нам нужны в зависимости от уровня навигации
    if gz:
        # Уровень группы заданий - нужны карточки и топ карточки по риску
        functions_with_args = [
            (load_card_data, {'program': program, 'module': module, 'lesson': lesson, 'gz': gz, '_engine': _engine}),
            (load_top_cards_by_risk, {'gz': gz, '_engine': _engine})
        ]
    elif lesson:
        # Уровень урока - нужны группы заданий и карточки
        functions_with_args = [
            (load_gz_data, {'program': program, 'module': module, 'lesson': lesson, '_engine': _engine}),
            (load_card_data, {'program': program, 'module': module, 'lesson': lesson, '_engine': _engine})
        ]
    elif module:
        # Уровень модуля - нужны уроки
        functions_with_args = [
            (load_lesson_data, {'program': program, 'module': module, '_engine': _engine}),
            (load_gz_data, {'program': program, 'module': module, '_engine': _engine})
        ]
    elif program:
        # Уровень программы - нужны модули
        functions_with_args = [
            (load_module_data, {'program': program, '_engine': _engine}),
            (load_lesson_data, {'program': program, '_engine': _engine})
        ]
    else:
        # Обзорный уровень - нужны программы и модули
        functions_with_args = [
            (load_program_data, {'_engine': _engine}),
            (load_module_data, {'_engine': _engine})
        ]
    
    # Выполняем функции параллельно
    return execute_in_parallel(functions_with_args)

# ------------------ Объединенная функция загрузки данных --------------------- #

@st.cache_data(ttl=3600)
def load_all_data_for_level(level="overview", program=None, module=None, lesson=None, gz=None, _engine=None):
    """
    Загружает все необходимые данные для указанного уровня навигации, используя параллельную загрузку.
    
    Args:
        level: Уровень навигации ("overview", "program", "module", "lesson", "gz", "card")
        program: Название программы для фильтрации
        module: Название модуля для фильтрации
        lesson: Название урока для фильтрации
        gz: Название группы заданий для фильтрации
        _engine: SQLAlchemy engine для подключения к БД
        
    Returns:
        dict: Словарь с различными наборами данных для указанного уровня
    """
    if _engine is None:
        _engine = get_engine()
    
    result = {}
    
    # Загружаем базовые данные для уровня
    if level == "overview":
        parallel_data = load_data_parallel(_engine=_engine)
        result["programs"] = parallel_data.get("load_program_data", pd.DataFrame())
        result["modules"] = parallel_data.get("load_module_data", pd.DataFrame())
    
    elif level == "program" and program:
        parallel_data = load_data_parallel(program=program, _engine=_engine)
        result["modules"] = parallel_data.get("load_module_data", pd.DataFrame())
        result["lessons"] = parallel_data.get("load_lesson_data", pd.DataFrame())
        result["program_data"] = load_program_data(_engine=_engine)
        result["program_data"] = result["program_data"][result["program_data"]["program"] == program]
    
    elif level == "module" and module:
        parallel_data = load_data_parallel(program=program, module=module, _engine=_engine)
        result["lessons"] = parallel_data.get("load_lesson_data", pd.DataFrame())
        result["gz_list"] = parallel_data.get("load_gz_data", pd.DataFrame())
        result["module_data"] = load_module_data(program=program, _engine=_engine)
        result["module_data"] = result["module_data"][result["module_data"]["module"] == module]
    
    elif level == "lesson" and lesson:
        parallel_data = load_data_parallel(program=program, module=module, lesson=lesson, _engine=_engine)
        result["gz_list"] = parallel_data.get("load_gz_data", pd.DataFrame())
        result["cards"] = parallel_data.get("load_card_data", pd.DataFrame())
        result["lesson_data"] = load_lesson_data(program=program, module=module, _engine=_engine)
        result["lesson_data"] = result["lesson_data"][result["lesson_data"]["lesson"] == lesson]
    
    elif level == "gz" and gz:
        parallel_data = load_data_parallel(program=program, module=module, lesson=lesson, gz=gz, _engine=_engine)
        result["cards"] = parallel_data.get("load_card_data", pd.DataFrame())
        result["top_cards"] = parallel_data.get("load_top_cards_by_risk", pd.DataFrame())
        result["gz_data"] = load_gz_data(program=program, module=module, lesson=lesson, _engine=_engine)
        result["gz_data"] = result["gz_data"][result["gz_data"]["gz"] == gz]
    
    elif level == "card" and "card_id" in result:
        card_id = result["card_id"]
        result["card_data"] = load_card_data(program=program, module=module, lesson=lesson, gz=gz, _engine=_engine)
        result["card_data"] = result["card_data"][result["card_data"]["card_id"] == card_id]
    
    return result
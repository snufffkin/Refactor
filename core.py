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
import json # <--- ДОБАВЛЯЕМ ИМПОРТ JSON

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from db_config import get_cloud_dsn

from core_config import get_config
# ---------------- DB ------------------------------------------------------- #

def get_engine():
    # Строка подключения к удаленной базе данных в Яндекс.Облаке
    cloud_dsn = get_cloud_dsn()
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
        SELECT 
            cs.program_name, cs.module_name, cs.module_order, 
            cs.lesson_name, cs.lesson_order,
            cs.gz_name, cs.gz_id, cs.card_id, cs.card_type, cs.card_url,
            cm.total_attempts, cm.attempted_share, cm.success_rate, 
            cm.first_try_success_rate, cm.complaint_rate, cm.complaints_total,
            cm.discrimination_avg, cm.success_attempts_rate, cm.time_median,
            cm.complaints_text,
            cst.status, cst.updated_at
        FROM cards_structure cs
        LEFT JOIN cards_metrics cm ON cs.card_id = cm.card_id
        LEFT JOIN card_status cst ON cs.card_id = cst.card_id
        """
    )
    return pd.read_sql(sql, _engine)

@st.cache_data(ttl=300)  # Кэширование на 5 минут
def process_data(raw_data, use_parallel=False, max_workers=4):
    """
    Обрабатывает сырые данные, добавляя вычисляемые метрики.
    Функция кэшируется с коротким TTL для обновления обработанных данных.
    
    Args:
        raw_data: DataFrame с сырыми данными из load_raw_data
        use_parallel: Использовать ли параллельную обработку для больших объемов данных
        max_workers: Количество параллельных потоков для обработки
        
    Returns:
        DataFrame с обработанными данными и дополнительными метриками
    """
    # Копируем данные, чтобы не модифицировать оригинал
    df = raw_data.copy()
    
    if use_parallel and len(df) > 100:  # Используем параллельную обработку только для больших датасетов
        # Вычисляем риск с использованием параллельной обработки
        df['risk'] = parallel_process_data(df, calculate_risk_score, max_workers)
    else:
        # Вычисляем риск для всего DataFrame векторизованно
        df['risk'] = calculate_risk_score(df)
    
    return df

def parallel_process_data(df, process_func, max_workers=4, chunk_size=None):
    """
    Обрабатывает большие объемы данных параллельно по чанкам.
    
    Args:
        df: DataFrame для обработки
        process_func: Функция, которая будет применена к каждому чанку
        max_workers: Количество параллельных потоков для обработки
        chunk_size: Размер чанка для обработки (если None, определяется автоматически)
        
    Returns:
        Series с результатами обработки
    """
    # Определяем оптимальный размер чанка, если не указан
    if chunk_size is None:
        # Используем от 100 до 1000 строк в чанке в зависимости от размера DataFrame
        chunk_size = max(100, min(1000, len(df) // max_workers))
    
    # Определяем функцию для обработки одного чанка
    def process_chunk(chunk):
        return process_func(chunk)
    
    # Создаем чанки DataFrame для параллельной обработки
    chunks = [df[i:i + chunk_size] for i in range(0, len(df), chunk_size)]
    result_series = pd.Series(index=df.index)
    
    # Обрабатываем чанки параллельно
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Запускаем процессинг параллельно для каждого чанка
        chunk_results = list(executor.map(process_chunk, chunks))
        
        # Объединяем результаты
        result_index = 0
        for i, chunk_result in enumerate(chunk_results):
            chunk_len = len(chunks[i])
            chunk_indices = df.index[result_index:result_index + chunk_len]
            result_series.loc[chunk_indices] = chunk_result.values
            result_index += chunk_len
    
    return result_series

# Для обратной совместимости
def load_data(_engine, max_workers=4):
    """
    Загружает и обрабатывает данные (устаревшая функция для обратной совместимости).
    Рекомендуется использовать комбинацию load_raw_data и process_data.
    
    Args:
        _engine: SQLAlchemy engine для подключения к БД (не хешируемый параметр)
        max_workers: Количество параллельных потоков для обработки (если больше 1, используется параллельная обработка)
    """
    raw_data = load_raw_data(_engine)
    # Используем параллельную обработку, если указано больше 1 потока
    use_parallel = max_workers > 1
    return process_data(raw_data, use_parallel=use_parallel, max_workers=max_workers)

# ---------------- Filters / Risk ------------------------------------------ #

FILTERS: List[str] = ["program", "module", "lesson", "gz"]  # Ключи, используемые в session_state (filter_program, filter_module, ...)

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
    """
    Применяет фильтры к DataFrame.
    
    Args:
        df: DataFrame для фильтрации
        upto: Список фильтров для применения (если None, используются все фильтры)
        
    Returns:
        Отфильтрованный DataFrame
    """
    cols = FILTERS if upto is None else upto
    for col in cols:
        v = st.session_state.get(f"filter_{col}")
        if v:
            actual_col_name = col 
            if col not in df.columns and f"{col}_name" in df.columns:
                actual_col_name = f"{col}_name"
            
            if actual_col_name in df.columns:
                df = df[df[actual_col_name] == v]
            else:
                # Можно добавить логирование или предупреждение, если столбец не найден
                # print(f"Предупреждение: Столбец '{col}' или '{f"{col}_name"}' не найден для фильтрации. Фильтр пропущен.")
                pass # Пропустить фильтрацию, если столбец не существует
    return df

def reset_child(level: str):
    """
    Сбрасывает дочерние фильтры в st.session_state относительно указанного уровня.
    Уровень должен быть одним из ключей в FILTERS (program, module, lesson, gz).
    Например, reset_child("program") сбросит filter_module, filter_lesson, filter_gz.
    """
    if level not in FILTERS:
        # Если уровень "overview" или что-то выше "program", сбрасываем все
        if level == "overview" or level is None: # Добавим обработку None для сброса всего
            for f_key in FILTERS:
                st.session_state[f"filter_{f_key}"] = None
                print(f"[CORE.RESET_CHILD] Reset filter_overview: filter_{f_key}")
            st.session_state.selected_card_id = None # Также сбрасываем card_id
            st.session_state.selected_assignment_id = None # и assignment_id
        else:
            # print(f"[CORE.RESET_CHILD] Unknown level: {level}. No filters reset.")
            pass # Неизвестный уровень, ничего не делаем или можно вывести предупреждение
        return
    
    start_resetting = False
    for f_key in FILTERS:
        if start_resetting:
            st.session_state[f"filter_{f_key}"] = None
            print(f"[CORE.RESET_CHILD] Reset: filter_{f_key}")
        if f_key == level:
            start_resetting = True
    
    # При сбросе уровня, также сбрасываем специфичные ID
    if level == "program":
        st.session_state.selected_card_id = None
        st.session_state.selected_assignment_id = None
    elif level == "module":
        st.session_state.selected_card_id = None
        st.session_state.selected_assignment_id = None # Если задачи привязаны к урокам/ГЗ
    elif level == "lesson":
        st.session_state.selected_card_id = None 
        # selected_assignment_id может быть привязан к карточке, которая ниже ГЗ

# ---------------- Aggregation --------------------------------------------- #

def agg_by(df: pd.DataFrame, level: str) -> pd.DataFrame:
    """
    Агрегирует данные по указанному уровню.
    
    Args:
        df: DataFrame для агрегации
        level: Уровень агрегации (одно из полей FILTERS)
        
    Returns:
        Агрегированный DataFrame
    """
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
                INSERT INTO card_status(card_id, status, updated_by, updated_at)
                VALUES (:cid, :st, :by, :ts)
                ON CONFLICT(card_id) DO UPDATE SET
                  status = EXCLUDED.status,
                  updated_by = EXCLUDED.updated_by,
                  updated_at = EXCLUDED.updated_at;
                """),
                {
                    "cid": int(row.card_id), 
                    "st": row.status, 
                    "by": st.session_state.get("user", "demo"), 
                    "ts": datetime.utcnow().isoformat()
                },
            )

# ---------------- UI helper ------------------------------------------------ #

def clickable(label: str, level: str) -> None:
    """
    Создает кликабельную ссылку с переходом на соответствующий уровень иерархии.
    
    Args:
        label: Текст ссылки
        level: Уровень иерархии для перехода
    """
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
    Использует материализованное представление mv_program_stats.
    """
    if _engine is None:
        _engine = get_engine()
        
    sql = text(
        """
        SELECT 
            p.*
        FROM mv_program_stats p
        ORDER BY program_name
        """
    )
    return pd.read_sql(sql, _engine)

@st.cache_data(ttl=1800)  # Кэширование на 30 минут
def load_module_data(program=None, _engine=None):
    """
    Загружает агрегированные данные на уровне модулей для указанной программы.
    Использует материализованное представление mv_module_stats.
    """
    if _engine is None:
        _engine = get_engine()
    
    query = """
        SELECT 
            m.*
        FROM mv_module_stats m
    """
    
    params = {}
    if program:
        query += " WHERE m.program_name = :program"
        params["program"] = program
        
    query += " ORDER BY m.program_name, m.module_order"
    
    return pd.read_sql(text(query), _engine, params=params)

@st.cache_data(ttl=1800)  # Кэширование на 30 минут
def load_lesson_data(program=None, module=None, _engine=None):
    """
    Загружает агрегированные данные на уровне уроков для указанной программы и модуля.
    Использует материализованное представление mv_lesson_stats.
    """
    if _engine is None:
        _engine = get_engine()
    
    query = """
        SELECT 
            l.*
        FROM mv_lesson_stats l
    """
    
    params = {}
    where_clauses = []
    
    if program:
        where_clauses.append("l.program_name = :program")
        params["program"] = program
        
    if module:
        where_clauses.append("l.module_name = :module")
        params["module"] = module
    
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
        
    query += " ORDER BY l.program_name, l.module_order, l.lesson_order"
    
    return pd.read_sql(text(query), _engine, params=params)

@st.cache_data(ttl=1800)  # Кэширование на 30 минут
def load_gz_data(program=None, module=None, lesson=None, _engine=None):
    """
    Загружает агрегированные данные на уровне групп заданий (ГЗ) для указанных параметров.
    Использует материализованное представление mv_gz_stats, соединенное с cards_structure для фильтрации.
    """
    if _engine is None:
        _engine = get_engine()
    
    # Выбираем все поля из mv_gz_stats и необходимые для сортировки/фильтрации из cards_structure
    # Используем DISTINCT для g.* чтобы избежать дублирования строк из mv_gz_stats, если одна ГЗ
    # теоретически может быть привязана к разным путям в cards_structure, соответствующим фильтрам.
    # Однако, для правильной работы фильтров и сортировки, нам нужны поля из cs в выборке.
    # Чтобы избежать дубликатов ГЗ, если одна ГЗ относится к нескольким урокам (что не должно быть, но возможно),
    # лучше группировать по полям ГЗ и агрегировать или выбирать первое значение для полей структуры.
    # Но для начала, попробуем JOIN и фильтрацию. Если будут дубли, будем уточнять.

    query = """
        SELECT DISTINCT
            g.*,
            cs.program_name, 
            cs.module_name, 
            cs.module_order, 
            cs.lesson_name, 
            cs.lesson_order
        FROM mv_gz_stats g
        JOIN cards_structure cs ON g.gz_id = cs.gz_id
    """
    
    params = {}
    where_clauses = []
    
    if program:
        where_clauses.append("cs.program_name = :program")
        params["program"] = program
        
    if module:
        where_clauses.append("cs.module_name = :module")
        params["module"] = module
        
    if lesson:
        where_clauses.append("cs.lesson_name = :lesson")
        params["lesson"] = lesson
    
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
        
    query += " ORDER BY cs.program_name, cs.module_order, cs.lesson_order, g.gz_name"
    
    return pd.read_sql(text(query), _engine, params=params)

@st.cache_data(ttl=1800)  # Кэширование на 30 минут
def load_card_data(program=None, module=None, lesson=None, gz=None, _engine=None):
    """
    Загружает данные карточек для указанных параметров фильтрации.
    """
    if _engine is None:
        _engine = get_engine()
    
    query = """
        SELECT 
            cs.*,
            cm.total_attempts, cm.attempted_share, cm.success_rate, 
            cm.first_try_success_rate, cm.complaint_rate, cm.complaints_total,
            cm.discrimination_avg, cm.success_attempts_rate, cm.time_median,
            cm.complaints_text,
            cst.status, cst.updated_at,
            crc.risk
        FROM cards_structure cs
        LEFT JOIN cards_metrics cm ON cs.card_id = cm.card_id
        LEFT JOIN card_status cst ON cs.card_id = cst.card_id
        LEFT JOIN card_risk_cache crc ON cs.card_id = crc.card_id
    """
    
    params = {}
    where_clauses = []
    
    if program:
        where_clauses.append("cs.program_name = :program")
        params["program"] = program
        
    if module:
        where_clauses.append("cs.module_name = :module")
        params["module"] = module
        
    if lesson:
        where_clauses.append("cs.lesson_name = :lesson")
        params["lesson"] = lesson
        
    if gz:
        where_clauses.append("cs.gz_name = :gz")
        params["gz"] = gz
    
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
        
    query += " ORDER BY cs.program_name, cs.module_order, cs.lesson_order, cs.gz_name"
    
    return pd.read_sql(text(query), _engine, params=params)

@st.cache_data(ttl=1800)  # Кэширование на 30 минут
def load_top_cards_by_risk(gz=None, limit=10, _engine=None):
    """
    Загружает карточки с наивысшим риском для указанной группы заданий или для всех групп.
    """
    if _engine is None:
        _engine = get_engine()
    
    query = """
        SELECT 
            t.gz_name, t.card_id, t.risk, t.rn,
            cs.program_name, cs.module_name, cs.lesson_name, cs.card_type, cs.card_url
        FROM top10_by_group t
        JOIN cards_structure cs ON t.card_id = cs.card_id
    """
    
    params = {}
    if gz:
        query += " WHERE t.gz_name = :gz"
        params["gz"] = gz
    
    if limit:
        query += " AND t.rn <= :limit"
        params["limit"] = limit
        
    query += " ORDER BY t.gz_name, t.rn"
    
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
def load_data_parallel(program=None, module=None, lesson=None, gz=None, _engine=None, max_workers=4):
    """
    Загружает несколько наборов данных параллельно в зависимости от уровня навигации.
    
    Args:
        program: Название программы для фильтрации
        module: Название модуля для фильтрации
        lesson: Название урока для фильтрации
        gz: Название группы заданий для фильтрации
        _engine: SQLAlchemy engine для подключения к БД
        max_workers: Максимальное количество параллельных рабочих потоков
        
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
    return execute_in_parallel(functions_with_args, max_workers=max_workers)

# ------------------ Объединенная функция загрузки данных --------------------- #

@st.cache_data(ttl=3600)
def load_all_data_for_level(level="overview", program=None, module=None, lesson=None, gz=None, _engine=None, max_workers=4):
    """
    Загружает все необходимые данные для указанного уровня навигации, используя параллельную загрузку.
    
    Args:
        level: Уровень навигации ("overview", "program", "module", "lesson", "gz", "card")
        program: Название программы для фильтрации
        module: Название модуля для фильтрации
        lesson: Название урока для фильтрации
        gz: Название группы заданий для фильтрации
        _engine: SQLAlchemy engine для подключения к БД
        max_workers: Максимальное количество параллельных рабочих потоков
        
    Returns:
        dict: Словарь с различными наборами данных для указанного уровня
    """
    if _engine is None:
        _engine = get_engine()
    
    result = {}
    
    # Загружаем базовые данные для уровня
    if level == "overview":
        parallel_data = load_data_parallel(_engine=_engine, max_workers=max_workers)
        result["programs"] = parallel_data.get("load_program_data", pd.DataFrame())
        result["modules"] = parallel_data.get("load_module_data", pd.DataFrame())
    
    elif level == "program" and program:
        parallel_data = load_data_parallel(program=program, _engine=_engine, max_workers=max_workers)
        result["modules"] = parallel_data.get("load_module_data", pd.DataFrame())
        result["lessons"] = parallel_data.get("load_lesson_data", pd.DataFrame())
        result["program_data"] = load_program_data(_engine=_engine)
        result["program_data"] = result["program_data"][result["program_data"]["program_name"] == program]
    
    elif level == "module" and module:
        parallel_data = load_data_parallel(program=program, module=module, _engine=_engine, max_workers=max_workers)
        result["lessons"] = parallel_data.get("load_lesson_data", pd.DataFrame())
        result["gz_list"] = parallel_data.get("load_gz_data", pd.DataFrame())
        result["module_data"] = load_module_data(program=program, _engine=_engine)
        result["module_data"] = result["module_data"][result["module_data"]["module_name"] == module]
    
    elif level == "lesson" and lesson:
        parallel_data = load_data_parallel(program=program, module=module, lesson=lesson, _engine=_engine, max_workers=max_workers)
        result["gz_list"] = parallel_data.get("load_gz_data", pd.DataFrame())
        result["cards"] = parallel_data.get("load_card_data", pd.DataFrame())
        result["lesson_data"] = load_lesson_data(program=program, module=module, _engine=_engine)
        result["lesson_data"] = result["lesson_data"][result["lesson_data"]["lesson_name"] == lesson]
    
    elif level == "gz" and gz:
        parallel_data = load_data_parallel(program=program, module=module, lesson=lesson, gz=gz, _engine=_engine, max_workers=max_workers)
        result["cards"] = parallel_data.get("load_card_data", pd.DataFrame())
        result["top_cards"] = parallel_data.get("load_top_cards_by_risk", pd.DataFrame())
        result["gz_data"] = load_gz_data(program=program, module=module, lesson=lesson, _engine=_engine)
        result["gz_data"] = result["gz_data"][result["gz_data"]["gz_name"] == gz]
    
    elif level == "card" and "card_id" in result:
        card_id = result["card_id"]
        result["card_data"] = load_card_data(program=program, module=module, lesson=lesson, gz=gz, _engine=_engine)
        result["card_data"] = result["card_data"][result["card_data"]["card_id"] == card_id]
    
    return result

@st.cache_data(ttl=3600)  # Кэширование на 1 час
def load_navigation_data(_engine=None):
    """
    Загружает все данные из таблицы cards_structure, объединенные с program_short_name из program_ids,
    для навигации и фильтрации.
    """
    if _engine is None:
        _engine = get_engine()
    
    # Обновленный SQL-запрос для включения program_short_name
    sql = text("""
        SELECT 
            cs.*,
            p.program_short_name
        FROM cards_structure cs
        LEFT JOIN program_ids p ON cs.program_id = p.program_id
    """)
    return pd.read_sql(sql, _engine)

@st.cache_data(ttl=300)  # Кэширование на 5 минут
def get_active_tasks_count(_engine, user_id: int) -> int:
    """
    Подсчитывает количество активных задач для указанного пользователя.
    Активными считаются задачи, статус которых не входит в список завершенных.
    """
    if user_id is None:
        return 0

    # Статусы, которые считаются неактивными (завершенными)
    inactive_statuses = ('completed', 'done', 'closed', 'resolved', 'cancelled', 'rejected')
    
    # Формируем строку с плейсхолдерами для статусов
    status_placeholders = ", ".join([f":status_{i}" for i in range(len(inactive_statuses))])
    
    # Создаем словарь параметров для SQL-запроса
    params = {"user_id": user_id}
    for i, status_val in enumerate(inactive_statuses):
        params[f"status_{i}"] = status_val

    sql_query = text(f"""
        SELECT COUNT(*) 
        FROM card_assignments
        WHERE user_id = :user_id AND status NOT IN ({status_placeholders});
    """)
    
    try:
        with _engine.connect() as connection:
            result = connection.execute(sql_query, params).scalar_one_or_none()
        return result if result is not None else 0
    except Exception as e:
        print(f"Error counting active tasks: {e}")
        return 0

# ------------------ User Action History --------------------- #

@st.cache_data(ttl=60) # Кэшируем на короткое время, чтобы не дергать БД слишком часто при одинаковых фильтрах
def get_context_ids_by_names(_engine, program_name: Optional[str] = None, module_name: Optional[str] = None, lesson_name: Optional[str] = None, gz_name: Optional[str] = None, card_id_param: Optional[Any] = None) -> Dict[str, Any]: # Изменен тип возвращаемого значения
    """
    Получает числовые ID для программы, модуля, урока, ГЗ и карточки, а также program_short_name.
    Использует данные из cards_structure (которая теперь включает program_short_name).

    Args:
        _engine: SQLAlchemy engine.
        program_name (Optional[str]): Название программы.
        module_name (Optional[str]): Название модуля.
        lesson_name (Optional[str]): Название урока.
        gz_name (Optional[str]): Название ГЗ.
        card_id_param (Optional[Any]): ID карточки.

    Returns:
        Dict[str, Any]: Словарь с ключами 'program_id', 'module_id', 'lesson_id', 'gz_id', 'card_id', 'program_short_name'.
                                   Значения ID будут None, если не найдены. program_short_name будет None, если не найден.
    """
    ids = {
        "program_id": None,
        "module_id": None,
        "lesson_id": None,
        "gz_id": None,
        "card_id": None,
        "program_short_name": None # Добавлено новое поле
    }
    
    # Попытка преобразовать card_id_param в int, если он не None
    if card_id_param is not None:
        try:
            ids["card_id"] = int(card_id_param)
        except (ValueError, TypeError):
            print(f"Warning: card_id_param '{card_id_param}' could not be converted to int. Will proceed without it for ID fetching.")
            # card_id_param остается не-None, но ids["card_id"] будет None, если конвертация не удалась
            # Это важно, чтобы не пытаться фильтровать по некорректному card_id дальше

    if not any([program_name, module_name, lesson_name, gz_name, ids["card_id"] is not None]):
        return ids

    try:
        df_structure = load_navigation_data(_engine=_engine)
        if df_structure.empty:
            print("Warning: cards_structure is empty. Cannot fetch context IDs.")
            return ids

        filtered_df = df_structure.copy()

        # Если card_id известен и валиден, он однозначно определяет строку
        if ids["card_id"] is not None:
            filtered_df = filtered_df[filtered_df['card_id'] == ids["card_id"]]
            if not filtered_df.empty:
                first_match = filtered_df.iloc[0]
                ids["program_id"] = int(first_match["program_id"]) if pd.notna(first_match["program_id"]) else None
                ids["module_id"] = int(first_match["module_id"]) if pd.notna(first_match["module_id"]) else None
                ids["lesson_id"] = int(first_match["lesson_id"]) if pd.notna(first_match["lesson_id"]) else None
                ids["gz_id"] = int(first_match["gz_id"]) if pd.notna(first_match["gz_id"]) else None
                ids["program_short_name"] = first_match["program_short_name"] if pd.notna(first_match["program_short_name"]) else None # Получаем short_name
                # ids["card_id"] уже установлен
                return ids 
            else:
                # card_id был предоставлен, но не найден в структуре. Это странно.
                print(f"Warning: Provided card_id {ids['card_id']} not found in cards_structure.")
                ids["card_id"] = None # Сбрасываем, чтобы не мешать дальнейшему поиску по именам, если он нужен
                # Если card_id был единственным параметром, то вернем пустые ids
                if not any([program_name, module_name, lesson_name, gz_name]):
                    return ids
                # Пересоздаем filtered_df из оригинала для поиска по именам
                filtered_df = df_structure.copy() 

        # Если card_id не был предоставлен или не найден, фильтруем по именам
        if program_name:
            filtered_df = filtered_df[filtered_df['program_name'] == program_name]
        if module_name and not filtered_df.empty:
            filtered_df = filtered_df[filtered_df['module_name'] == module_name]
        if lesson_name and not filtered_df.empty:
            filtered_df = filtered_df[filtered_df['lesson_name'] == lesson_name]
        if gz_name and not filtered_df.empty:
            filtered_df = filtered_df[filtered_df['gz_name'] == gz_name]

        if not filtered_df.empty:
            first_match = filtered_df.iloc[0]
            ids["program_id"] = int(first_match["program_id"]) if pd.notna(first_match["program_id"]) else None
            ids["module_id"] = int(first_match["module_id"]) if pd.notna(first_match["module_id"]) else None
            ids["lesson_id"] = int(first_match["lesson_id"]) if pd.notna(first_match["lesson_id"]) else None
            ids["gz_id"] = int(first_match["gz_id"]) if pd.notna(first_match["gz_id"]) else None
            ids["program_short_name"] = first_match["program_short_name"] if pd.notna(first_match["program_short_name"]) else None # Получаем short_name
            # card_id может быть уже установлен, если он пришел как параметр и был валиден
            # Если он не был установлен, и мы нашли его по именам, устанавливаем сейчас
            if ids["card_id"] is None and pd.notna(first_match["card_id"]):
                 ids["card_id"] = int(first_match["card_id"])
        else:
            print(f"Warning: No match found in cards_structure for filters: P={program_name}, M={module_name}, L={lesson_name}, GZ={gz_name}")

    except Exception as e:
        print(f"Error in get_context_ids_by_names: {e}")
    
    return ids

def log_user_action(_engine, user_id: Optional[int], action_type: str, page_key: str, 
                    context_ids: Optional[Dict[str, Optional[int]]] = None, 
                    display_name: Optional[str] = None, 
                    url_params: Optional[Dict[str, Any]] = None):
    """
    Записывает действие пользователя в таблицу action_history.

    Args:
        _engine: SQLAlchemy engine.
        user_id (Optional[int]): ID пользователя.
        action_type (str): Тип действия (например, 'navigate_page').
        page_key (str): Ключ страницы (например, 'overview', 'programs').
        context_ids (Optional[Dict[str, Optional[int]]]): Словарь с ID ('program_id', 'module_id', etc.).
        display_name (Optional[str]): Человекочитаемое имя страницы/контекста.
        url_params (Optional[Dict[str, Any]]): Словарь с параметрами URL (будет сохранен как JSON).
    """
    if user_id is None:
        print("Critical: user_id is None. Skipping action logging.")
        return
    try:
        user_id = int(user_id) # Убедимся, что user_id это int
    except (ValueError, TypeError):
        print(f"Critical: user_id '{user_id}' is not a valid integer. Skipping action logging.")
        return

    insert_query = text("""
        INSERT INTO action_history (
            user_id, action_type, page_key,
            target_program_id, target_module_id, target_lesson_id, target_gz_id, target_card_id, target_assignment_id,
            display_name, url_params
        ) VALUES (
            :user_id, :action_type, :page_key,
            :program_id, :module_id, :lesson_id, :gz_id, :card_id, :assignment_id,
            :display_name, :url_params_json
        )
    """)

    params_to_insert = {
        "user_id": user_id,
        "action_type": action_type,
        "page_key": page_key,
        "program_id": context_ids.get("program_id") if context_ids else None,
        "module_id": context_ids.get("module_id") if context_ids else None,
        "lesson_id": context_ids.get("lesson_id") if context_ids else None,
        "gz_id": context_ids.get("gz_id") if context_ids else None,
        "card_id": context_ids.get("card_id") if context_ids else None,
        "assignment_id": context_ids.get("assignment_id") if context_ids else None, # Добавим позже, если нужно
        "display_name": display_name,
        "url_params_json": json.dumps(url_params) if url_params else None # ИСПОЛЬЗУЕМ json.dumps
    }
    
    # Проверка типов для ID, чтобы избежать ошибок при вставке
    for id_key in ["program_id", "module_id", "lesson_id", "gz_id", "card_id", "assignment_id"]:
        if params_to_insert[id_key] is not None:
            try:
                params_to_insert[id_key] = int(params_to_insert[id_key])
            except (ValueError, TypeError):
                print(f"Warning: Could not convert {id_key} ('{params_to_insert[id_key]}') to int. Setting to None.")
                params_to_insert[id_key] = None


    try:
        with _engine.connect() as connection:
            connection.execute(insert_query, params_to_insert)
            connection.commit()
            print(f"Action logged: {action_type} by user {user_id} for page {page_key}")
    except Exception as e:
        print(f"Error logging user action: {e}")
        # В случае ошибки можно попробовать откатить транзакцию, если она была начата явно,
        # но здесь connect() управляет транзакцией.
        # Важно не прерывать основное выполнение приложения из-за ошибки логирования.
# core_config.py
"""
Модуль для работы с конфигурацией расчета риска.
"""

import os
import json
import logging

# Путь к файлу конфигурации
CONFIG_PATH = "risk_config.json"

# Настройки по умолчанию
DEFAULT_CONFIG = {
    "discrimination": {
        "good": 0.35,
        "medium": 0.15
    },
    "success_rate": {
        "boring": 0.95,
        "optimal_high": 0.95,
        "optimal_low": 0.75,
        "suboptimal_low": 0.50
    },
    "first_try": {
        "too_easy": 0.90,
        "optimal_low": 0.65,
        "multiple_low": 0.40
    },
    "complaints": {
        "critical": 50,
        "high": 10,
        "medium": 5
    },
    "attempts": {
        "high": 0.95,
        "normal_low": 0.80,
        "insufficient_low": 0.60
    },
    "weights": {
        "complaint_rate": 0.35,
        "success_rate": 0.25,
        "discrimination": 0.20,
        "first_try": 0.15,
        "attempted": 0.05
    },
    "risk_thresholds": {
        "critical": 0.75,
        "high": 0.50,
        "min_for_critical": 0.60,
        "min_for_high": 0.40,
        "alpha_weight_avg": 0.7
    },
    "stats": {
        "significance_threshold": 100,
        "neutral_risk_value": 0.50
    }
}

# Кэшированная конфигурация
_cached_config = None
_config_last_modified = 0

def get_config():
    """
    Загружает конфигурацию из файла или возвращает кэшированную версию,
    если файл не изменился с момента последней загрузки.
    
    Returns:
        dict: Конфигурация риска
    """
    global _cached_config, _config_last_modified
    
    try:
        # Проверяем существование файла и время последней модификации
        if os.path.exists(CONFIG_PATH):
            current_mtime = os.path.getmtime(CONFIG_PATH)
            
            # Если файл не изменялся и у нас есть кэшированная версия, возвращаем её
            if _cached_config is not None and current_mtime <= _config_last_modified:
                return _cached_config
            
            # Иначе загружаем конфигурацию из файла
            with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
                config = json.load(file)
                _cached_config = config
                _config_last_modified = current_mtime
                return config
        else:
            # Если файл не существует, возвращаем настройки по умолчанию
            return DEFAULT_CONFIG
    except Exception as e:
        # В случае ошибки логируем её и возвращаем настройки по умолчанию
        logging.error(f"Ошибка при загрузке конфигурации: {str(e)}")
        return DEFAULT_CONFIG

def save_config(config):
    """
    Сохраняет конфигурацию в файл.
    
    Args:
        config (dict): Конфигурация для сохранения
    
    Returns:
        bool: True если сохранение успешно, иначе False
    """
    global _cached_config, _config_last_modified
    
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=4, ensure_ascii=False)
        
        # Обновляем кэш
        _cached_config = config
        _config_last_modified = os.path.getmtime(CONFIG_PATH)
        return True
    except Exception as e:
        logging.error(f"Ошибка при сохранении конфигурации: {str(e)}")
        return False
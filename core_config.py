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
    # Убираем секцию first_try, так как теперь используем trickiness
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
        "trickiness": 0.15,  # Заменяем first_try на trickiness с тем же весом
        "attempted": 0.05
    },
    "risk_thresholds": {
        "critical": 0.75,
        "high": 0.50,
        "min_for_critical": 0.60,
        "min_for_high": 0.40,
        "alpha_weight_avg": 0.7,
        "use_min_threshold": False  # Параметр для включения/отключения минимального порога
    },
    "stats": {
        "significance_threshold": 100,
        "neutral_risk_value": 0.50
    },
    # Секция с параметрами трики-карточек
    "tricky_cards": {
        "basic": {
            "min_success_rate": 0.70,
            "max_first_try_rate": 0.60,
            "min_difference": 0.20,
        },
        "zones": {
            "high_success_threshold": 0.90,
            "medium_success_threshold": 0.80,
            "low_first_try_threshold": 0.40,
            "medium_first_try_threshold": 0.50
        }
    }
}

# Кэшированная конфигурация
_cached_config = None
_config_last_modified = 0

def get_tricky_config():
    """
    Получает параметры трики-карточек из общего конфигурационного файла
    
    Returns:
        dict: Параметры трики-карточек или значения по умолчанию
    """
    config = get_config()  # Используем существующую функцию для получения конфигурации
    
    # Проверяем наличие секции трики-карточек
    if "tricky_cards" in config:
        return config["tricky_cards"]
    else:
        # Возвращаем значения по умолчанию, если секция отсутствует
        default_tricky_config = {
            "basic": {
                "min_success_rate": 0.70,
                "max_first_try_rate": 0.60,
                "min_difference": 0.20,
            },
            "zones": {
                "high_success_threshold": 0.90,
                "medium_success_threshold": 0.80,
                "low_first_try_threshold": 0.40,
                "medium_first_try_threshold": 0.50
            }
        }
        return default_tricky_config

def save_tricky_config(tricky_config):
    """
    Сохраняет параметры трики-карточек в общий конфигурационный файл
    
    Args:
        tricky_config (dict): Параметры трики-карточек для сохранения
        
    Returns:
        bool: True, если сохранение успешно, иначе False
    """
    try:
        # Получаем текущую конфигурацию
        config = get_config()
        
        # Обновляем или добавляем секцию трики-карточек
        config["tricky_cards"] = tricky_config
        
        # Сохраняем обновленную конфигурацию
        result = save_config(config)
        
        return result
    except Exception as e:
        logging.error(f"Ошибка при сохранении конфигурации трики-карточек: {str(e)}")
        return False
    
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
                
                # Проверяем наличие новых параметров и добавляем их при необходимости
                if "risk_thresholds" in config and "use_min_threshold" not in config["risk_thresholds"]:
                    config["risk_thresholds"]["use_min_threshold"] = True
                
                # Обновляем веса - заменяем first_try на trickiness
                if "weights" in config:
                    if "first_try" in config["weights"] and "trickiness" not in config["weights"]:
                        config["weights"]["trickiness"] = config["weights"].pop("first_try")
                
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
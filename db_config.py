import os
import platform
import requests
from typing import Dict, Optional
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

def get_cert_path():
    system = platform.system().lower()
    home = os.path.expanduser("~")
    
    if system == "windows":
        return os.path.join(home, ".postgresql", "root.crt")
    elif system == "darwin":  # macOS
        return os.path.join(home, ".postgresql", "root.crt")
    elif system == "linux":
        return os.path.join(home, ".postgresql", "root.crt")
    else:
        raise OSError(f"Unsupported operating system: {system}")

def get_github_secrets() -> Optional[Dict[str, str]]:
    """
    Пытается получить секреты из GitHub Actions.
    Возвращает None, если не удалось получить секреты.
    """
    try:
        # Проверяем, находимся ли мы в GitHub Actions
        if os.environ.get("GITHUB_ACTIONS") == "true":
            return {
                "DB_USER": os.environ.get("DB_USER"),
                "DB_PASSWORD": os.environ.get("DB_PASSWORD"),
                "DB_HOST": os.environ.get("DB_HOST"),
                "DB_PORT": os.environ.get("DB_PORT"),
                "DB_NAME": os.environ.get("DB_NAME")
            }
    except Exception:
        pass
    return None

def get_db_config():
    """
    Получает конфигурацию базы данных.
    Сначала пытается получить секреты из GitHub Actions,
    затем проверяет локальные переменные окружения.
    """
    # Пробуем получить секреты из GitHub
    config = get_github_secrets()
    
    # Если не в GitHub Actions, используем локальные переменные
    if config is None:
        config = {
            "DB_USER": os.environ.get("DB_USER"),
            "DB_PASSWORD": os.environ.get("DB_PASSWORD"),
            "DB_HOST": os.environ.get("DB_HOST"),
            "DB_PORT": os.environ.get("DB_PORT"),
            "DB_NAME": os.environ.get("DB_NAME")
        }
    
    # Проверяем, что все необходимые переменные установлены
    missing_vars = [key for key, value in config.items() if value is None]
    if missing_vars:
        raise ValueError(f"Отсутствуют необходимые переменные окружения: {', '.join(missing_vars)}")
    
    return config

def get_cloud_dsn():
    cert_path = get_cert_path()
    config = get_db_config()
    return f"postgresql://{config['DB_USER']}:{config['DB_PASSWORD']}@{config['DB_HOST']}:{config['DB_PORT']}/{config['DB_NAME']}?sslmode=verify-full&sslrootcert={cert_path}" 
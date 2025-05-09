import os
import platform
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
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

# Базовые параметры подключения из переменных окружения
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

def get_cloud_dsn():
    cert_path = get_cert_path()
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=verify-full&sslrootcert={cert_path}" 
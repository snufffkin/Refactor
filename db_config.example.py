import os
import platform

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

# Базовые параметры подключения
DB_USER = "your_username"
DB_PASSWORD = "your_password"
DB_HOST = "your_host"
DB_PORT = "your_port"
DB_NAME = "your_database"

def get_cloud_dsn():
    cert_path = get_cert_path()
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=verify-full&sslrootcert={cert_path}" 
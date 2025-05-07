import os
import sys
import time
import logging
import argparse
import yadisk
from tqdm import tqdm

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Константы
LOCAL_DIR = "image"
REMOTE_DIR = "Refactor/image"
TOKEN = "y0__xDy8e2YARjblgMgl_6WhRO_IK0EtVc_09fxm3Bi3u9x1_m6vQ"

def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Скрипт для загрузки файлов на Яндекс Диск')
    parser.add_argument('--local-dir', '-l', type=str, default=LOCAL_DIR,
                       help=f'Локальная директория с файлами (по умолчанию: {LOCAL_DIR})')
    parser.add_argument('--remote-dir', '-r', type=str, default=REMOTE_DIR,
                       help=f'Удаленная директория на Яндекс Диске (по умолчанию: {REMOTE_DIR})')
    parser.add_argument('--token', '-t', type=str, default=TOKEN,
                       help='Токен для доступа к API Яндекс Диска')
    parser.add_argument('--batch-size', '-b', type=int, default=50,
                       help='Размер пакета для загрузки (по умолчанию: 50)')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Принудительно перезаписывать существующие файлы без проверки')
    return parser.parse_args()

def validate_token(y):
    """Проверка валидности токена"""
    try:
        if not y.check_token():
            logger.error("Токен недействителен. Получите новый токен в https://yandex.ru/dev/disk/poligon/")
            return False
        
        # Дополнительная проверка доступа
        y.get_disk_info()
        return True
    except yadisk.exceptions.UnauthorizedError:
        logger.error("Ошибка авторизации. Токен недействителен или срок его действия истек.")
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке токена: {e}")
        return False

def ensure_remote_dir_exists(y, remote_dir):
    """Проверяет существование удаленной директории и создает её при необходимости"""
    try:
        # Разбиваем путь на компоненты
        parts = remote_dir.strip('/').split('/')
        current_path = ""
        
        # Создаем каждый уровень директории, если он не существует
        for part in parts:
            if not part:  # Пропускаем пустые части
                continue
                
            current_path += f"/{part}"
            
            # Проверяем существование текущего уровня
            try:
                y.get_meta(current_path)
            except yadisk.exceptions.PathNotFoundError:
                logger.info(f"Создание директории {current_path} на Яндекс Диске")
                y.mkdir(current_path)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании директории {remote_dir}: {e}")
        return False

def get_remote_files(y, remote_dir):
    """Получает список файлов в удаленной директории"""
    try:
        remote_files = {}
        for item in y.listdir(remote_dir):
            if not item.is_dir:
                remote_files[item.name] = {
                    'path': item.path,
                    'modified': item.modified,
                    'size': item.size
                }
        
        logger.info(f"Найдено {len(remote_files)} файлов в удаленной директории")
        return remote_files
    except yadisk.exceptions.PathNotFoundError:
        # Директория не существует, значит и файлов нет
        return {}
    except Exception as e:
        logger.error(f"Ошибка при получении списка файлов из {remote_dir}: {e}")
        return {}

def upload_files(y, local_dir, remote_dir, remote_files, batch_size=50, force_overwrite=False):
    """Загружает файлы из локальной директории на Яндекс Диск"""
    # Проверяем существование локальной директории
    if not os.path.exists(local_dir):
        logger.error(f"Локальная директория {local_dir} не существует")
        return False
    
    # Получаем список локальных файлов
    local_files = []
    for filename in os.listdir(local_dir):
        file_path = os.path.join(local_dir, filename)
        if os.path.isfile(file_path):
            local_files.append(filename)
    
    if not local_files:
        logger.warning(f"В локальной директории {local_dir} не найдено файлов")
        return False
    
    logger.info(f"Найдено {len(local_files)} файлов в локальной директории")
    
    # Загружаем файлы порциями для оптимального использования API
    total_uploaded = 0
    total_skipped = 0
    total_errors = 0
    
    # Используем tqdm для отображения прогресса
    pbar = tqdm(total=len(local_files), desc="Загрузка файлов", unit="файл")
    
    # Разбиваем на пакеты для загрузки
    for i in range(0, len(local_files), batch_size):
        batch = local_files[i:i+batch_size]
        
        for filename in batch:
            try:
                local_path = os.path.join(local_dir, filename)
                remote_path = f"{remote_dir}/{filename}"
                
                # Проверяем, существует ли файл уже на Яндекс Диске
                file_exists = filename in remote_files
                
                # Определяем, нужно ли загружать файл
                should_upload = True
                
                if file_exists and not force_overwrite:
                    # Сравниваем размеры и даты модификации
                    local_size = os.path.getsize(local_path)
                    local_mtime = os.path.getmtime(local_path)
                    
                    remote_size = remote_files[filename]['size']
                    
                    # Если размеры совпадают, можно пропустить
                    if local_size == remote_size:
                        logger.debug(f"Файл {filename} уже существует и имеет тот же размер, пропускаем")
                        should_upload = False
                
                if should_upload:
                    # Загружаем файл, перезаписывая существующий при необходимости
                    y.upload(local_path, remote_path, overwrite=True)
                    action = "обновлен" if file_exists else "загружен"
                    logger.debug(f"Файл {filename} успешно {action}")
                    total_uploaded += 1
                else:
                    total_skipped += 1
            
            except Exception as e:
                logger.error(f"Ошибка при загрузке файла {filename}: {e}")
                total_errors += 1
            
            # Обновляем прогресс-бар
            pbar.update(1)
            
            # Небольшая задержка, чтобы не превысить лимиты API
            time.sleep(0.1)
    
    # Закрываем прогресс-бар
    pbar.close()
    
    logger.info(f"Загрузка завершена: {total_uploaded} файлов загружено, "
                f"{total_skipped} пропущено, {total_errors} с ошибками")
    
    return total_uploaded > 0

def main():
    """Основная функция скрипта"""
    args = parse_args()
    
    try:
        # Инициализация клиента Яндекс Диска
        y = yadisk.YaDisk(token=args.token)
        
        # Проверка токена
        if not validate_token(y):
            sys.exit(1)
        
        logger.info("Токен действителен, подключение к Яндекс Диску установлено")
        
        # Проверка и создание удаленной директории
        if not ensure_remote_dir_exists(y, args.remote_dir):
            sys.exit(1)
        
        # Получение списка удаленных файлов
        remote_files = get_remote_files(y, args.remote_dir)
        
        # Загрузка файлов
        if upload_files(y, args.local_dir, args.remote_dir, remote_files, 
                        args.batch_size, args.force):
            logger.info("Загрузка успешно завершена")
        else:
            logger.warning("Загрузка завершена, но есть проблемы")
    
    except Exception as e:
        logger.error(f"Необработанная ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
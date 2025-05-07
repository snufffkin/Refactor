#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import argparse
import logging
import yadisk
from tqdm import tqdm

# Импортируем константы из существующих файлов
from upload_to_yadisk import (
    TOKEN, 
    REMOTE_DIR, 
    validate_token, 
    ensure_remote_dir_exists
)
from get_screenshot import OUTPUT_DIR

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Синхронизация скриншотов с Яндекс Диском')
    parser.add_argument('--token', '-t', type=str, default=TOKEN,
                       help='Токен для доступа к API Яндекс Диска')
    parser.add_argument('--remote-dir', '-r', type=str, default=REMOTE_DIR,
                       help='Удаленная директория на Яндекс Диске')
    parser.add_argument('--local-dir', '-l', type=str, default=OUTPUT_DIR,
                       help='Локальная директория с файлами')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Принудительно перезаписывать существующие файлы без проверки')
    parser.add_argument('--only-missing', '-m', action='store_true',
                       help='Загружать только отсутствующие в облаке файлы')
    parser.add_argument('--batch-size', '-b', type=int, default=50,
                       help='Размер пакета для загрузки (для оптимизации API)')
    return parser.parse_args()

def get_remote_files(y, remote_dir):
    """Получает список файлов в удаленной директории"""
    try:
        remote_files = {}
        logger.info(f"Получение списка файлов из директории {remote_dir}...")
        
        # Используем прогресс-бар для отображения процесса получения файлов
        remote_items = list(y.listdir(remote_dir))
        
        if remote_items:
            logger.info(f"Обработка {len(remote_items)} элементов в удаленной директории...")
            for item in tqdm(remote_items, desc="Анализ облачных файлов", unit="файл"):
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
        logger.warning(f"Директория {remote_dir} не существует на Яндекс Диске")
        return {}
    except Exception as e:
        logger.error(f"Ошибка при получении списка файлов из {remote_dir}: {e}")
        return {}

def get_local_files(local_dir):
    """Получает список локальных файлов"""
    if not os.path.exists(local_dir):
        logger.error(f"Локальная директория {local_dir} не существует")
        return []
    
    local_files = []
    for filename in os.listdir(local_dir):
        file_path = os.path.join(local_dir, filename)
        if os.path.isfile(file_path) and filename.endswith(('.jpg', '.jpeg', '.png')):
            local_files.append(filename)
    
    logger.info(f"Найдено {len(local_files)} файлов в локальной директории")
    return local_files

def upload_files_to_yadisk(y, local_dir, local_files, remote_dir, remote_files, batch_size=50, force_overwrite=False):
    """Загружает указанные файлы на Яндекс Диск"""
    if not local_files:
        logger.warning("Нет файлов для загрузки")
        return 0
    
    # Загружаем файлы порциями
    total_uploaded = 0
    total_skipped = 0
    total_errors = 0
    
    # Разбиваем на пакеты для оптимизации работы с API
    batches = [local_files[i:i+batch_size] for i in range(0, len(local_files), batch_size)]
    logger.info(f"Подготовлено {len(batches)} пакетов по {batch_size} файлов")
    
    # Обрабатываем пакеты
    for i, batch in enumerate(batches):
        logger.info(f"Обработка пакета {i+1}/{len(batches)} ({len(batch)} файлов)")
        
        # Используем tqdm для отображения прогресса
        pbar = tqdm(total=len(batch), desc=f"Загрузка пакета {i+1}", unit="файл")
        
        for filename in batch:
            try:
                local_path = os.path.join(local_dir, filename)
                remote_path = f"{remote_dir}/{filename}"
                
                # Проверяем, существует ли файл уже на Яндекс Диске
                file_exists = filename in remote_files
                
                # Определяем, нужно ли загружать файл
                should_upload = True
                
                if file_exists and not force_overwrite:
                    # Сравниваем размеры
                    local_size = os.path.getsize(local_path)
                    remote_size = remote_files[filename]['size']
                    
                    # Если размеры совпадают, можно пропустить
                    if local_size == remote_size:
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
        
        # Закрываем прогресс-бар для текущего пакета
        pbar.close()
        
        # Выводим промежуточную статистику
        logger.info(f"Пакет {i+1}: {sum(1 for _ in batch if _ in [f for f in batch if os.path.join(local_dir, f) in [local_path for local_path in [os.path.join(local_dir, f) for f in batch] if y.exists(f'{remote_dir}/{os.path.basename(local_path)}')]])} файлов загружено, {total_skipped} пропущено")
    
    # Итоговая статистика
    logger.info(f"Загрузка на Яндекс Диск завершена: {total_uploaded} файлов загружено, "
                f"{total_skipped} пропущено, {total_errors} с ошибками")
    
    return total_uploaded

def main():
    """Основная функция скрипта"""
    args = parse_args()
    
    # Инициализация клиента Яндекс Диска
    y = yadisk.YaDisk(token=args.token)
    
    # Проверка токена
    if not validate_token(y):
        logger.error("Токен Яндекс Диска недействителен")
        return 1
    
    logger.info("Токен действителен, подключение к Яндекс Диску установлено")
    
    # Проверка и создание удаленной директории
    if not ensure_remote_dir_exists(y, args.remote_dir):
        logger.error("Не удалось создать директорию на Яндекс Диске")
        return 1
    
    # Получение списка файлов на Яндекс Диске
    remote_files = get_remote_files(y, args.remote_dir)
    
    # Получение списка локальных файлов
    local_files = get_local_files(args.local_dir)
    
    if not local_files:
        logger.warning("Локальные файлы не найдены, нечего синхронизировать")
        return 0
    
    # Если нужно загрузить только отсутствующие в облаке файлы
    if args.only_missing:
        files_to_upload = [f for f in local_files if f not in remote_files]
        logger.info(f"Подготовлено {len(files_to_upload)} отсутствующих в облаке файлов для загрузки")
    else:
        files_to_upload = local_files
        logger.info(f"Подготовлено {len(files_to_upload)} файлов для синхронизации")
    
    if not files_to_upload:
        logger.info("Все файлы уже синхронизированы с облаком")
        return 0
    
    # Загружаем файлы
    total_uploaded = upload_files_to_yadisk(
        y, args.local_dir, files_to_upload, args.remote_dir, 
        remote_files, args.batch_size, args.force
    )
    
    logger.info(f"Синхронизация завершена. Всего загружено {total_uploaded} файлов.")
    return 0

if __name__ == "__main__":
    start_time = time.time()
    exit_code = main()
    elapsed = time.time() - start_time
    
    # Выводим итоговую статистику по времени
    logger.info(f"Общее время выполнения: {elapsed:.2f} секунд ({elapsed/60:.2f} минут)")
    
    # Возвращаем код завершения
    exit(exit_code) 
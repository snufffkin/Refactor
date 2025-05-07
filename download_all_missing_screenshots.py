import os
import asyncio
import argparse
import logging
from tqdm import tqdm
import time
import yadisk

# Импортируем функцию для проверки и загрузки отсутствующих скриншотов
from check_missing_screenshots import (
    get_all_card_ids_from_db,
    get_existing_screenshot_ids,
    save_missing_card_ids,
    main as check_and_download_func,
    OUTPUT_DIR
)

# Импортируем функции для работы с Яндекс Диском
from upload_to_yadisk import (
    TOKEN,
    REMOTE_DIR, 
    validate_token, 
    ensure_remote_dir_exists,
    get_remote_files
)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_download_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Массовая загрузка отсутствующих скриншотов')
    parser.add_argument('--batch-size', '-b', type=int, default=500,
                       help='Количество скриншотов для загрузки за одну итерацию')
    parser.add_argument('--total-limit', '-t', type=int, default=0,
                       help='Общее ограничение на количество загружаемых скриншотов (0 = все)')
    parser.add_argument('--skip-errors', '-s', action='store_true',
                       help='Пропускать карточки с ошибками из предыдущих запусков')
    parser.add_argument('--delay', '-d', type=int, default=5,
                       help='Задержка между итерациями в секундах')
    parser.add_argument('--no-yadisk', '-n', action='store_true',
                       help='Не загружать скриншоты на Яндекс Диск')
    parser.add_argument('--token', type=str, default=TOKEN,
                       help='Токен для доступа к API Яндекс Диска')
    parser.add_argument('--remote-dir', type=str, default=REMOTE_DIR,
                       help='Удаленная директория на Яндекс Диске')
    parser.add_argument('--sync-only', action='store_true',
                       help='Только синхронизировать существующие скриншоты с Яндекс Диском')
    return parser.parse_args()

def upload_files_to_yadisk(y, local_files, remote_dir, remote_files, force_overwrite=False):
    """Загружает указанные файлы на Яндекс Диск"""
    if not local_files:
        logger.warning("Нет файлов для загрузки")
        return 0
    
    # Загружаем файлы
    total_uploaded = 0
    total_skipped = 0
    total_errors = 0
    
    # Используем tqdm для отображения прогресса
    pbar = tqdm(total=len(local_files), desc="Загрузка на Яндекс Диск", unit="файл")
    
    for filename in local_files:
        try:
            local_path = os.path.join(OUTPUT_DIR, filename)
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
    
    # Закрываем прогресс-бар
    pbar.close()
    
    logger.info(f"Загрузка на Яндекс Диск: {total_uploaded} файлов загружено, "
                f"{total_skipped} пропущено, {total_errors} с ошибками")
    
    return total_uploaded

def sync_screenshots_with_yadisk(token, remote_dir, new_files_only=False):
    """Синхронизирует локальные скриншоты с Яндекс Диском"""
    # Инициализация клиента Яндекс Диска
    y = yadisk.YaDisk(token=token)
    
    # Проверка токена
    if not validate_token(y):
        logger.error("Токен Яндекс Диска недействителен")
        return 0
    
    # Проверка и создание удаленной директории
    if not ensure_remote_dir_exists(y, remote_dir):
        logger.error("Не удалось создать директорию на Яндекс Диске")
        return 0
    
    # Получение списка файлов на Яндекс Диске
    remote_files = get_remote_files(y, remote_dir)
    
    # Получение списка локальных файлов
    if not os.path.exists(OUTPUT_DIR):
        logger.error(f"Локальная директория {OUTPUT_DIR} не существует")
        return 0
    
    local_files = []
    for filename in os.listdir(OUTPUT_DIR):
        if os.path.isfile(os.path.join(OUTPUT_DIR, filename)) and filename.endswith(('.jpg', '.jpeg', '.png')):
            local_files.append(filename)
    
    if not local_files:
        logger.warning(f"В локальной директории {OUTPUT_DIR} не найдено файлов")
        return 0
    
    logger.info(f"Найдено {len(local_files)} файлов в локальной директории")
    
    # Если нужно загрузить только новые файлы
    if new_files_only:
        # Фильтруем файлы, которых нет на Яндекс Диске
        files_to_upload = [f for f in local_files if f not in remote_files]
        logger.info(f"Подготовлено {len(files_to_upload)} новых файлов для загрузки")
    else:
        files_to_upload = local_files
        logger.info(f"Подготовлено {len(files_to_upload)} файлов для загрузки/проверки")
    
    # Загружаем файлы
    return upload_files_to_yadisk(y, files_to_upload, remote_dir, remote_files)

def check_missing_uploads(token, remote_dir):
    """Проверяет и загружает скриншоты, которые есть локально, но отсутствуют в облаке"""
    # Инициализация клиента Яндекс Диска
    y = yadisk.YaDisk(token=token)
    
    # Проверка токена
    if not validate_token(y):
        logger.error("Токен Яндекс Диска недействителен")
        return 0
    
    logger.info("Проверка отсутствующих в облаке скриншотов...")
    
    # Проверка и создание удаленной директории
    if not ensure_remote_dir_exists(y, remote_dir):
        logger.error("Не удалось создать директорию на Яндекс Диске")
        return 0
    
    # Получение списка файлов на Яндекс Диске
    remote_files = get_remote_files(y, remote_dir)
    
    # Получение списка локальных файлов
    if not os.path.exists(OUTPUT_DIR):
        logger.error(f"Локальная директория {OUTPUT_DIR} не существует")
        return 0
    
    local_files = []
    for filename in os.listdir(OUTPUT_DIR):
        if os.path.isfile(os.path.join(OUTPUT_DIR, filename)) and filename.endswith(('.jpg', '.jpeg', '.png')):
            local_files.append(filename)
    
    # Находим файлы, которые есть локально, но отсутствуют в облаке
    missing_in_cloud = [f for f in local_files if f not in remote_files]
    
    if not missing_in_cloud:
        logger.info("Все локальные скриншоты уже загружены в облако")
        return 0
    
    logger.info(f"Найдено {len(missing_in_cloud)} скриншотов, отсутствующих в облаке")
    
    # Загружаем отсутствующие файлы
    return upload_files_to_yadisk(y, missing_in_cloud, remote_dir, remote_files)

async def main():
    """Основная функция для массовой загрузки отсутствующих скриншотов"""
    args = parse_download_args()
    
    # Если нужно только синхронизировать, выполняем только эту операцию
    if args.sync_only:
        logger.info("Запуск в режиме синхронизации существующих скриншотов с Яндекс Диском")
        check_missing_uploads(args.token, args.remote_dir)
        return
    
    # Текущая итерация
    iteration = 1
    
    # Загружено скриншотов всего
    total_downloaded = 0
    total_uploaded = 0
    
    # Время начала
    start_time = time.time()
    
    while True:
        logger.info(f"Итерация {iteration}, всего загружено: {total_downloaded} скриншотов")
        
        # Получаем текущее количество скриншотов
        before_count = len(get_existing_screenshot_ids())
        
        # Устанавливаем ограничение на текущую итерацию
        current_max_items = args.batch_size
        
        # Если указан общий лимит, учитываем его
        if args.total_limit > 0:
            remaining = args.total_limit - total_downloaded
            if remaining <= 0:
                logger.info(f"Достигнут общий лимит в {args.total_limit} скриншотов. Завершение работы.")
                break
            
            current_max_items = min(args.batch_size, remaining)
        
        # Вызываем основную функцию
        result = await check_and_download_func(
            download=True,
            max_items=current_max_items,
            batch_size=current_max_items,  # Размер пакета = максимальному количеству
            verbose=True,
            skip_errors=args.skip_errors
        )
        
        # Получаем новое количество скриншотов
        after_count = len(get_existing_screenshot_ids())
        
        # Вычисляем количество загруженных скриншотов
        downloaded = after_count - before_count
        total_downloaded += downloaded
        
        # Выводим статистику
        elapsed = time.time() - start_time
        screenshots_per_second = total_downloaded / elapsed if elapsed > 0 else 0
        logger.info(f"Итерация {iteration} завершена, загружено {downloaded} скриншотов")
        logger.info(f"Всего загружено {total_downloaded} скриншотов за {elapsed/60:.2f} минут")
        logger.info(f"Средняя скорость: {screenshots_per_second:.2f} скриншотов/сек")
        
        # Если не отключена загрузка на Яндекс Диск и есть новые скриншоты
        if not args.no_yadisk and downloaded > 0:
            logger.info("Синхронизация новых скриншотов с Яндекс Диском...")
            uploaded = sync_screenshots_with_yadisk(args.token, args.remote_dir, new_files_only=True)
            total_uploaded += uploaded
            logger.info(f"Всего загружено в облако: {total_uploaded} скриншотов")
        
        # Если ничего не загружено, завершаем работу
        if downloaded == 0:
            logger.info("Новые скриншоты не были загружены. Завершение работы.")
            break
        
        # Задержка между итерациями
        logger.info(f"Ожидание {args.delay} секунд перед следующей итерацией...")
        await asyncio.sleep(args.delay)
        
        # Увеличиваем счетчик итераций
        iteration += 1
    
    # Итоговая статистика
    total_time = time.time() - start_time
    logger.info(f"Загрузка завершена. Всего загружено {total_downloaded} скриншотов за {total_time/60:.2f} минут")
    logger.info(f"Средняя скорость: {total_downloaded/total_time:.2f} скриншотов/сек")
    
    # Финальная синхронизация с Яндекс Диском
    if not args.no_yadisk:
        logger.info("Финальная проверка и синхронизация с Яндекс Диском...")
        final_uploaded = check_missing_uploads(args.token, args.remote_dir)
        total_uploaded += final_uploaded
        logger.info(f"Всего загружено в облако: {total_uploaded} скриншотов")

if __name__ == "__main__":
    asyncio.run(main()) 
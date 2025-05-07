import os
import psycopg2
from psycopg2.extras import RealDictCursor
import argparse
import logging
import asyncio
import sys
from tqdm import tqdm
from playwright.async_api import async_playwright

# Импортируем необходимые функции из get_screenshot.py
from get_screenshot import (
    DB_CONFIG, 
    OUTPUT_DIR,
    setup_browser,
    process_card,
    CONCURRENT_BROWSERS,
    BATCH_SIZE,
    clear_progress,
    ERROR_LOG_FILE,
    save_error
)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Проверка и докачка отсутствующих скриншотов')
    parser.add_argument('--download', '-d', action='store_true',
                       help='Загрузить отсутствующие скриншоты')
    parser.add_argument('--check-only', '-c', action='store_true',
                       help='Только проверить наличие скриншотов без загрузки')
    parser.add_argument('--batch-size', '-b', type=int, default=100,
                       help='Размер пакета для обработки карточек')
    parser.add_argument('--max-items', '-m', type=int, default=0,
                       help='Максимальное количество карточек для загрузки за один запуск (0 = все)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Подробный режим вывода информации об ошибках')
    parser.add_argument('--skip-errors', '-s', action='store_true',
                       help='Пропускать карточки с ошибками из прошлых запусков')
    return parser.parse_args()

def get_all_card_ids_from_db():
    """Получает все ID карточек из базы данных"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT card_id
            FROM cards_structure
            WHERE gz_id IS NOT NULL AND card_order IS NOT NULL
            ORDER BY card_id
        """)
        cards = cursor.fetchall()
    
    conn.close()
    return [card['card_id'] for card in cards]

def get_existing_screenshot_ids():
    """Получает ID карточек, для которых уже есть скриншоты"""
    if not os.path.exists(OUTPUT_DIR):
        return set()
    
    existing_ids = set()
    for filename in os.listdir(OUTPUT_DIR):
        if filename.endswith(('.jpg', '.jpeg', '.png')):
            try:
                card_id = int(filename.split('.')[0])
                existing_ids.add(card_id)
            except (ValueError, IndexError):
                continue
    
    return existing_ids

def load_error_cards():
    """Загружает список карточек с ошибками"""
    if not os.path.exists(ERROR_LOG_FILE):
        return set()
    
    error_ids = set()
    with open(ERROR_LOG_FILE, "r") as f:
        for line in f:
            parts = line.strip().split(",", 2)
            if len(parts) >= 1 and parts[0].isdigit():
                error_ids.add(int(parts[0]))
    
    return error_ids

def save_missing_card_ids(missing_ids, filename="missing_screenshots.txt"):
    """Сохраняет ID отсутствующих карточек в файл"""
    with open(filename, "w") as f:
        for card_id in missing_ids:
            f.write(f"{card_id}\n")
    logger.info(f"Список отсутствующих скриншотов сохранен в {filename}")

def get_card_data_from_db(card_ids):
    """Получает данные карточек по их ID"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    cards = []
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        # Используем параметризованный запрос с placeholder
        placeholder = ','.join(['%s'] * len(card_ids))
        query = f"""
            SELECT card_id, gz_id, card_order
            FROM cards_structure
            WHERE card_id IN ({placeholder})
            AND gz_id IS NOT NULL AND card_order IS NOT NULL
            ORDER BY card_id
        """
        cursor.execute(query, card_ids)
        cards = cursor.fetchall()
    
    conn.close()
    logger.info(f"Получено {len(cards)} карточек из базы данных")
    return cards

async def process_card_with_error_tracking(page, card, processed_cards, semaphore, pbar):
    """Обрабатывает карточку с отслеживанием ошибок"""
    try:
        return await process_card(page, card, processed_cards, semaphore, pbar, force_reload=True)
    except Exception as e:
        card_id = card['card_id']
        gz_id = card['gz_id']
        card_order = card['card_order']
        url = f"https://education.yandex.ru/classroom/public-lesson/{gz_id}/run/{card_order}/"
        
        error_msg = str(e)
        logger.error(f"Ошибка при обработке карточки {card_id}: {error_msg}")
        save_error(card_id, url, error_msg)
        
        # Обновляем прогресс-бар
        pbar.update(1)
        return False

async def download_screenshots_batch_with_browser(playwright, cards, processed_cards, semaphore, pbar):
    """Загружает группу скриншотов с одним браузером"""
    browser = await setup_browser(playwright)
    
    try:
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
            java_script_enabled=True,
            bypass_csp=True,
            ignore_https_errors=True,
            extra_http_headers={"Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"}
        )
        
        context.set_default_navigation_timeout(60000)
        
        page = await context.new_page()
        
        # Обрабатываем карточки с отслеживанием ошибок
        results = []
        for card in cards:
            result = await process_card_with_error_tracking(page, card, processed_cards, semaphore, pbar)
            results.append(result)
        
        return results
    
    except Exception as e:
        logger.error(f"Ошибка в обработчике браузера: {e}")
        return [False] * len(cards)
    
    finally:
        if browser:
            await browser.close()

async def download_screenshots_batch(card_ids, batch_size=100):
    """Загружает скриншоты для указанных ID карточек"""
    # Получаем данные карточек из базы
    cards = get_card_data_from_db(card_ids)
    
    if not cards:
        logger.warning("Не найдены данные для указанных ID карточек")
        return 0
    
    # Общее количество карточек
    total_cards = len(cards)
    
    # Очищаем файл прогресса
    processed_cards = set()
    
    # Создаем прогресс-бар
    pbar = tqdm(total=total_cards, desc="Скриншоты", unit="карт")
    
    # Создаем семафор для ограничения параллельных запросов
    semaphore = asyncio.Semaphore(CONCURRENT_BROWSERS * 2)
    
    # Счетчики статистики
    success_count = 0
    error_count = 0
    
    # Запускаем Playwright
    async with async_playwright() as playwright:
        # Разбиваем на группы для браузеров
        browser_groups = []
        group_size = max(1, total_cards // CONCURRENT_BROWSERS)
        for i in range(0, total_cards, group_size):
            browser_groups.append(cards[i:i + group_size])
        
        # Запускаем группы параллельно в разных браузерах
        tasks = []
        for browser_group in browser_groups:
            task = download_screenshots_batch_with_browser(
                playwright, browser_group, processed_cards, semaphore, pbar
            )
            tasks.append(task)
        
        # Ждем завершения всех задач
        results = await asyncio.gather(*tasks)
        
        # Собираем результаты
        for browser_result in results:
            success_count += sum(1 for r in browser_result if r)
            error_count += sum(1 for r in browser_result if not r)
    
    pbar.close()
    
    # Итоговая статистика
    logger.info(f"Обработано {success_count} карточек успешно, {error_count} с ошибками")
    return success_count

async def download_screenshots_in_batches(missing_ids, batch_size=100):
    """Загружает скриншоты порциями заданного размера"""
    total_missing = len(missing_ids)
    batches = [missing_ids[i:i+batch_size] for i in range(0, total_missing, batch_size)]
    
    logger.info(f"Разбивка задачи загрузки на {len(batches)} порций по {batch_size} карточек")
    
    total_processed = 0
    for i, batch in enumerate(batches):
        logger.info(f"Обработка партии {i+1}/{len(batches)} ({len(batch)} карточек)")
        
        # Загружаем партию
        processed = await download_screenshots_batch(batch)
        total_processed += processed
        
        logger.info(f"Партия {i+1}/{len(batches)} завершена, обработано {processed} карточек")
    
    return total_processed

async def main(download=False, max_items=0, batch_size=100, verbose=False, skip_errors=False):
    """
    Основная функция для проверки и загрузки отсутствующих скриншотов
    
    Параметры:
        download (bool): Загружать ли отсутствующие скриншоты
        max_items (int): Максимальное количество карточек для загрузки (0 = все)
        batch_size (int): Размер пакета для обработки карточек
        verbose (bool): Подробный режим вывода информации
        skip_errors (bool): Пропускать ли карточки с ошибками из прошлых запусков
    """
    # Если аргументы не указаны, берем из командной строки
    args = parse_args()
    
    # Приоритет отдаем параметрам функции
    download = download or args.download
    max_items = max_items or args.max_items
    batch_size = batch_size or args.batch_size
    verbose = verbose or args.verbose
    skip_errors = skip_errors or args.skip_errors
    
    logger.info("Получение всех ID карточек из базы данных...")
    all_card_ids = get_all_card_ids_from_db()
    logger.info(f"Всего карточек в базе данных: {len(all_card_ids)}")
    
    logger.info("Получение ID существующих скриншотов...")
    existing_ids = get_existing_screenshot_ids()
    logger.info(f"Найдено существующих скриншотов: {len(existing_ids)}")
    
    # Находим отсутствующие скриншоты
    missing_ids = [card_id for card_id in all_card_ids if card_id not in existing_ids]
    logger.info(f"Отсутствует скриншотов: {len(missing_ids)}")
    
    # Если нужно пропустить карточки с ошибками
    if skip_errors:
        error_ids = load_error_cards()
        logger.info(f"Найдено {len(error_ids)} карточек с ошибками")
        
        # Отфильтровываем карточки с ошибками
        filtered_missing_ids = [card_id for card_id in missing_ids if card_id not in error_ids]
        
        logger.info(f"После фильтрации карточек с ошибками: {len(filtered_missing_ids)} из {len(missing_ids)}")
        missing_ids = filtered_missing_ids
    
    # Если есть отсутствующие скриншоты
    if missing_ids:
        # Сохраняем список отсутствующих ID в файл
        save_missing_card_ids(missing_ids)
        
        if download:
            logger.info("Начинаем загрузку отсутствующих скриншотов...")
            
            # Если указано максимальное количество карточек для загрузки
            if max_items > 0 and max_items < len(missing_ids):
                logger.info(f"Ограничение загрузки до {max_items} карточек")
                missing_ids = missing_ids[:max_items]
            
            # Сначала получаем данные из базы для всех ID сразу
            batch_cards = get_card_data_from_db(missing_ids)
            
            # Создаем словарь для быстрого поиска карточек по ID
            card_dict = {card['card_id']: card for card in batch_cards}
            
            # Очищаем файл прогресса перед началом
            clear_progress()
            
            # Создаем семафор для ограничения параллельных запросов
            semaphore = asyncio.Semaphore(CONCURRENT_BROWSERS * 2)
            
            # Создаем прогресс-бар
            pbar = tqdm(total=len(missing_ids), desc="Скриншоты", unit="карт")
            
            # Список отсутствующих ID после обработки
            still_missing_ids = []
            
            # Счетчики статистики
            success_count = 0
            error_count = 0
            
            # Запускаем Playwright
            async with async_playwright() as playwright:
                # Разбиваем на группы для параллельной обработки
                browser_groups = []
                
                # Собираем карточки по ID в заданном порядке
                cards_to_process = []
                for card_id in missing_ids:
                    if card_id in card_dict:
                        cards_to_process.append(card_dict[card_id])
                    else:
                        still_missing_ids.append(card_id)
                        logger.warning(f"Карточка с ID {card_id} не найдена в базе данных")
                
                # Равномерно распределяем по браузерам
                browser_count = min(CONCURRENT_BROWSERS, max(1, len(cards_to_process) // 5))
                group_size = max(1, len(cards_to_process) // browser_count)
                
                for i in range(0, len(cards_to_process), group_size):
                    browser_groups.append(cards_to_process[i:i + group_size])
                
                # Запускаем группы параллельно в разных браузерах
                tasks = []
                for browser_group in browser_groups:
                    task = download_screenshots_batch_with_browser(
                        playwright, browser_group, set(), semaphore, pbar
                    )
                    tasks.append(task)
                
                # Ждем завершения всех задач
                results = await asyncio.gather(*tasks)
                
                # Собираем результаты
                for browser_result in results:
                    success_count += sum(1 for r in browser_result if r)
                    error_count += sum(1 for r in browser_result if not r)
            
            pbar.close()
            
            # Проверяем, есть ли новые скриншоты
            new_existing_ids = get_existing_screenshot_ids()
            new_count = len(new_existing_ids) - len(existing_ids)
            
            logger.info(f"Загрузка завершена, обработано {success_count} карточек успешно, {error_count} с ошибками")
            logger.info(f"Добавлено {new_count} новых скриншотов")
            
            # Находим карточки, для которых не удалось создать скриншоты
            for card_id in missing_ids:
                if not os.path.exists(f"{OUTPUT_DIR}/{card_id}.jpg") and not os.path.exists(f"{OUTPUT_DIR}/{card_id}.png"):
                    still_missing_ids.append(card_id)
            
            if still_missing_ids:
                logger.warning(f"Не удалось создать {len(still_missing_ids)} скриншотов")
                
                if verbose:
                    logger.info(f"ID карточек, для которых не удалось создать скриншоты: {still_missing_ids[:20]}" + 
                               ("..." if len(still_missing_ids) > 20 else ""))
        else:
            logger.info("Для загрузки отсутствующих скриншотов запустите скрипт с параметром --download")
    else:
        logger.info("Все скриншоты на месте! Отсутствующих скриншотов не обнаружено.")
    
    # Возвращаем статистику
    return {
        "existing_screenshots": len(existing_ids),
        "missing_screenshots": len(missing_ids),
        "processed_screenshots": success_count if 'success_count' in locals() else 0,
        "new_screenshots": new_count if 'new_count' in locals() else 0,
        "errors": error_count if 'error_count' in locals() else 0
    }

if __name__ == "__main__":
    asyncio.run(main()) 
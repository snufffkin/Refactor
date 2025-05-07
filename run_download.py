import os
import asyncio
import argparse
import logging
import time
import random
import cv2
import numpy as np
from tqdm import tqdm

# Импортируем только нужные функции
from check_missing_screenshots import (
    get_all_card_ids_from_db,
    get_existing_screenshot_ids,
    get_card_data_from_db,
    download_screenshots_batch_with_browser,
    process_card_with_error_tracking,
    clear_progress,
    load_error_cards,
    OUTPUT_DIR,
    CONCURRENT_BROWSERS
)
from playwright.async_api import async_playwright

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Массовая загрузка отсутствующих скриншотов')
    parser.add_argument('--batch-size', '-b', type=int, default=100,
                       help='Количество скриншотов для загрузки за одну итерацию')
    parser.add_argument('--total-limit', '-t', type=int, default=0,
                       help='Общее ограничение на количество загружаемых скриншотов (0 = все)')
    parser.add_argument('--max-items', '-m', type=int, default=0,
                       help='Максимальное количество карточек для загрузки за одну итерацию (0 = все)')
    parser.add_argument('--skip-errors', '-s', action='store_true',
                       help='Пропускать карточки с ошибками из прошлых запусков')
    parser.add_argument('--delay', '-d', type=int, default=5,
                       help='Задержка между итерациями в секундах')
    parser.add_argument('--min-request-delay', type=float, default=1.0,
                       help='Минимальная задержка между запросами (в секундах)')
    parser.add_argument('--max-request-delay', type=float, default=3.0,
                       help='Максимальная задержка между запросами (в секундах)')
    parser.add_argument('--captcha-check', action='store_true',
                       help='Проверять скриншоты на наличие капчи')
    return parser.parse_args()

def detect_captcha(image_path):
    """Определяет наличие капчи на изображении"""
    try:
        # Загружаем изображение
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Не удалось открыть файл {image_path}")
            return False
            
        # Конвертируем в HSV для лучшего обнаружения цветов логотипа Яндекс
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Диапазон красного цвета для логотипа Яндекса
        lower_red = np.array([0, 100, 100])
        upper_red = np.array([10, 255, 255])
        mask1 = cv2.inRange(hsv, lower_red, upper_red)
        
        # Второй диапазон для красного (он циклический в HSV)
        lower_red = np.array([170, 100, 100])
        upper_red = np.array([180, 255, 255])
        mask2 = cv2.inRange(hsv, lower_red, upper_red)
        
        # Объединяем маски
        red_mask = mask1 + mask2
        
        # Определяем количество красных пикселей
        red_pixels = cv2.countNonZero(red_mask)
        
        # Примерные характеристики изображения капчи Яндекса:
        # Проверяем наличие характерного текста о капче, конвертируя в оттенки серого
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Текстовые признаки: белый фон в центре
        # Получаем центральную часть изображения
        height, width = gray.shape
        center_y, center_x = height // 2, width // 2
        center_region = gray[center_y-100:center_y+100, center_x-150:center_x+150]
        
        # Яндекс капча обычно имеет белый фон в центре
        white_pixels = np.sum(center_region > 220)
        
        # Если много красных пикселей (логотип Яндекса) и белого в центре, 
        # вероятно это капча
        is_captcha = (red_pixels > 100) and (white_pixels > 10000)
        
        if is_captcha:
            logger.warning(f"Обнаружена капча в файле {image_path}")
        
        return is_captcha
    
    except Exception as e:
        logger.error(f"Ошибка при проверке капчи в {image_path}: {e}")
        return False

def check_and_handle_captcha():
    """Проверяет наличие капчи в последних загруженных скриншотах"""
    captcha_found = 0
    
    if not os.path.exists(OUTPUT_DIR):
        return 0
    
    # Получаем список файлов, отсортированных по времени модификации (сначала новые)
    files = [(f, os.path.getmtime(os.path.join(OUTPUT_DIR, f))) 
             for f in os.listdir(OUTPUT_DIR) 
             if os.path.isfile(os.path.join(OUTPUT_DIR, f)) and f.endswith(('.jpg', '.jpeg', '.png'))]
    
    files.sort(key=lambda x: x[1], reverse=True)
    
    # Проверяем последние 10 файлов (или меньше, если файлов меньше)
    for filename, _ in files[:10]:
        file_path = os.path.join(OUTPUT_DIR, filename)
        if detect_captcha(file_path):
            # Обнаружена капча - переименовываем файл или удаляем
            captcha_path = os.path.join(OUTPUT_DIR, f"captcha_{filename}")
            os.rename(file_path, captcha_path)
            logger.warning(f"Файл со скриншотом капчи переименован: {captcha_path}")
            captcha_found += 1
    
    return captcha_found

async def download_batch(missing_ids, max_items=100, min_delay=1.0, max_delay=3.0, check_captcha=False):
    """Загружает одну партию скриншотов"""
    # Ограничиваем количество скриншотов
    if max_items > 0 and max_items < len(missing_ids):
        missing_ids = missing_ids[:max_items]
    
    # Получаем данные карточек
    batch_cards = get_card_data_from_db(missing_ids)
    card_dict = {card['card_id']: card for card in batch_cards}
    
    # Очищаем прогресс
    clear_progress()
    
    # Создаем семафор
    semaphore = asyncio.Semaphore(CONCURRENT_BROWSERS * 2)
    
    # Создаем прогресс-бар
    pbar = tqdm(total=len(missing_ids), desc="Скриншоты", unit="карт")
    
    # Списки для статистики
    cards_to_process = []
    still_missing_ids = []
    
    # Формируем список карточек для обработки
    for card_id in missing_ids:
        if card_id in card_dict:
            cards_to_process.append(card_dict[card_id])
        else:
            still_missing_ids.append(card_id)
            logger.warning(f"Карточка с ID {card_id} не найдена в базе данных")
    
    # Статистика
    success_count = 0
    error_count = 0
    
    # Функция для добавления случайной задержки между запросами
    async def process_with_delay(playwright, cards, processed_set, semaphore, pbar):
        results = []
        for card in cards:
            # Добавляем случайную задержку перед каждым запросом
            delay = random.uniform(min_delay, max_delay)
            await asyncio.sleep(delay)
            
            # Выполняем запрос
            result = await download_screenshots_batch_with_browser(
                playwright, [card], processed_set, semaphore, pbar
            )
            results.extend(result)
            
            # Проверяем на капчу, если включено
            if check_captcha and result and result[0]:
                card_id = card["card_id"]
                jpg_path = os.path.join(OUTPUT_DIR, f"{card_id}.jpg")
                png_path = os.path.join(OUTPUT_DIR, f"{card_id}.png")
                
                # Проверяем файл, который существует
                if os.path.exists(jpg_path):
                    if detect_captcha(jpg_path):
                        # Обнаружена капча
                        logger.warning(f"Обнаружена капча для карточки {card_id}. Удаляем скриншот.")
                        os.remove(jpg_path)
                        results[-1] = False  # Отмечаем как ошибку
                elif os.path.exists(png_path):
                    if detect_captcha(png_path):
                        # Обнаружена капча
                        logger.warning(f"Обнаружена капча для карточки {card_id}. Удаляем скриншот.")
                        os.remove(png_path)
                        results[-1] = False  # Отмечаем как ошибку
        
        return results
    
    # Запускаем Playwright
    async with async_playwright() as playwright:
        # Распределяем карточки по браузерам, но с меньшим размером групп для лучшего распределения задержек
        browser_count = min(CONCURRENT_BROWSERS, max(1, len(cards_to_process) // 3))
        group_size = max(1, len(cards_to_process) // browser_count)
        
        browser_groups = []
        for i in range(0, len(cards_to_process), group_size):
            browser_groups.append(cards_to_process[i:i + group_size])
        
        # Запускаем группы параллельно
        tasks = []
        for browser_group in browser_groups:
            task = process_with_delay(
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
    
    logger.info(f"Обработано {success_count} карточек успешно, {error_count} с ошибками")
    
    # Проверяем наличие капчи в загруженных файлах
    if check_captcha:
        captcha_count = check_and_handle_captcha()
        if captcha_count > 0:
            logger.warning(f"Найдено {captcha_count} скриншотов с капчей")
            # Уменьшаем успешный счетчик
            success_count -= captcha_count
    
    return success_count, error_count

async def main():
    args = parse_args()
    
    # Получаем все ID карточек
    logger.info("Получение всех ID карточек из базы данных...")
    all_card_ids = get_all_card_ids_from_db()
    logger.info(f"Всего карточек в базе данных: {len(all_card_ids)}")
    
    # Итерация и статистика
    iteration = 1
    total_downloaded = 0
    start_time = time.time()
    
    # Проверка существующих скриншотов на капчу
    if args.captcha_check:
        logger.info("Проверка существующих скриншотов на наличие капчи...")
        captcha_count = check_and_handle_captcha()
        if captcha_count > 0:
            logger.warning(f"Найдено и обработано {captcha_count} скриншотов с капчей")
    
    while True:
        logger.info(f"Итерация {iteration}, всего загружено: {total_downloaded} скриншотов")
        
        # Получаем текущее количество скриншотов
        before_count = len(get_existing_screenshot_ids())
        logger.info(f"Существующих скриншотов: {before_count}")
        
        # Находим отсутствующие скриншоты
        missing_ids = [card_id for card_id in all_card_ids 
                      if not os.path.exists(f"{OUTPUT_DIR}/{card_id}.jpg") and 
                         not os.path.exists(f"{OUTPUT_DIR}/{card_id}.png") and
                         not os.path.exists(f"{OUTPUT_DIR}/captcha_{card_id}.jpg") and
                         not os.path.exists(f"{OUTPUT_DIR}/captcha_{card_id}.png")]
        
        logger.info(f"Отсутствует скриншотов: {len(missing_ids)}")
        
        if not missing_ids:
            logger.info("Все скриншоты на месте! Завершение работы.")
            break
        
        # Если нужно пропустить карточки с ошибками
        if args.skip_errors:
            error_ids = load_error_cards()
            logger.info(f"Найдено {len(error_ids)} карточек с ошибками")
            
            # Отфильтровываем карточки с ошибками
            filtered_missing_ids = [card_id for card_id in missing_ids if card_id not in error_ids]
            
            logger.info(f"После фильтрации карточек с ошибками: {len(filtered_missing_ids)} из {len(missing_ids)}")
            missing_ids = filtered_missing_ids
        
        # Определяем размер текущей партии
        current_max_items = args.batch_size
        
        # Ограничиваем размер партии, если указан max_items
        if args.max_items > 0:
            current_max_items = min(current_max_items, args.max_items)
        
        # Если указан общий лимит, учитываем его
        if args.total_limit > 0:
            remaining = args.total_limit - total_downloaded
            if remaining <= 0:
                logger.info(f"Достигнут общий лимит в {args.total_limit} скриншотов. Завершение работы.")
                break
            
            current_max_items = min(current_max_items, remaining)
        
        # Загружаем текущую партию
        success, errors = await download_batch(
            missing_ids, 
            current_max_items,
            args.min_request_delay,
            args.max_request_delay,
            args.captcha_check
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
        
        # Если ничего не загружено, завершаем работу
        if downloaded == 0:
            logger.info("Новые скриншоты не были загружены. Проверьте ошибки и попробуйте еще раз.")
            break
        
        # Задержка между итерациями
        logger.info(f"Ожидание {args.delay} секунд перед следующей итерацией...")
        await asyncio.sleep(args.delay)
        
        # Увеличиваем счетчик итераций
        iteration += 1
    
    # Итоговая статистика
    total_time = time.time() - start_time
    logger.info(f"Загрузка завершена. Всего загружено {total_downloaded} скриншотов за {total_time/60:.2f} минут")
    if total_time > 0:
        logger.info(f"Средняя скорость: {total_downloaded/total_time:.2f} скриншотов/сек")
    

if __name__ == "__main__":
    asyncio.run(main()) 
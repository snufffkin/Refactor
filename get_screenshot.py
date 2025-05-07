import os
import asyncio
import time
import argparse
import random
from playwright.async_api import async_playwright
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import tqdm as tqdm_module

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Параметры подключения к базе данных
DB_CONFIG = {
    "host": "rc1b-fkbqfy1dg88d0134.mdb.yandexcloud.net",
    "port": "6432",
    "user": "romannikitin",
    "password": "changeme123",
    "dbname": "course_quality",
    "sslmode": "verify-full",
    "sslrootcert": "/Users/romannikitin/.postgresql/root.crt"
}

# Параметры оптимизации
CONCURRENT_BROWSERS = 8  # Увеличено количество параллельных браузеров с 5 до 8
PAGES_PER_BROWSER = 4    # Увеличено количество страниц на браузер с 3 до 4
BATCH_SIZE = 200         # Увеличен размер пакета со 100 до 200
SCREENSHOT_QUALITY = 70  # Снижено качество скриншота с 80 до 70 (для JPEG)
WAIT_TIME = 1000         # Уменьшено время ожидания с 1500 до 1000 мс
RESOLUTION = {"width": 1280, "height": 720}  # Разрешение скриншота
USE_JPEG = True          # Использовать JPEG вместо PNG для меньшего размера
MAX_RETRIES = 2          # Уменьшено количество повторных попыток с 3 до 2
RETRY_DELAY = 250        # Уменьшена задержка между повторными попытками с 500 до 250 мс

# Параметры водяного знака
WATERMARK_TEXT = "PREVIEW"
WATERMARK_OPACITY = 40   # Уменьшенное значение прозрачности (было 64)
WATERMARK_POSITION = "bottom-right"  # Позиция: "bottom-right", "bottom", "bottom-left", "top-right", "top"

# Учетные данные для авторизации (если нужно)
LOGIN_REQUIRED = False   # Установите True, если требуется авторизация
LOGIN_URL = "https://passport.yandex.ru/auth"
USERNAME = ""            # Заполните, если LOGIN_REQUIRED = True
PASSWORD = ""            # Заполните, если LOGIN_REQUIRED = True

# Путь для сохранения прогресса
PROGRESS_FILE = "screenshot_progress.txt"
OUTPUT_DIR = "image"
ERROR_LOG_FILE = "screenshot_errors.txt"

def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Скрипт для создания скриншотов карточек Яндекс Образования')
    parser.add_argument('--limit', '-l', type=int, default=0, 
                       help='Максимальное количество карточек для обработки (0 = все карточки)')
    parser.add_argument('--retry-errors', '-r', action='store_true',
                       help='Повторить попытку для карточек с ошибками из предыдущих запусков')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Игнорировать предыдущий прогресс и заново обработать все карточки')
    return parser.parse_args()

def get_cards_from_db(batch_size, offset=0):
    """Получает партию карточек из базы данных с оптимизированным запросом"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        # Добавляем индексацию для ускорения запроса
        cursor.execute("""
            SELECT card_id, gz_id, card_order
            FROM cards_structure
            WHERE gz_id IS NOT NULL AND card_order IS NOT NULL
            ORDER BY card_id
            LIMIT %s OFFSET %s
        """, (batch_size, offset))
        cards = cursor.fetchall()
    
    conn.close()
    return cards

def get_total_cards(limit=0):
    """Получает общее количество карточек"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(DISTINCT card_id)
            FROM cards_structure
            WHERE gz_id IS NOT NULL AND card_order IS NOT NULL
        """)
        total = cursor.fetchone()[0]
    
    conn.close()
    
    # Если задан лимит и он больше 0, используем его как максимум
    if limit > 0 and limit < total:
        return limit
    return total

def save_progress(card_id):
    """Сохраняет прогресс"""
    with open(PROGRESS_FILE, "a") as f:
        f.write(f"{card_id}\n")

def load_progress():
    """Загружает информацию о прогрессе"""
    if not os.path.exists(PROGRESS_FILE):
        return set()
    
    with open(PROGRESS_FILE, "r") as f:
        return set(int(line.strip()) for line in f if line.strip().isdigit())

def clear_progress():
    """Очищает файл прогресса"""
    if os.path.exists(PROGRESS_FILE):
        os.unlink(PROGRESS_FILE)
        logger.info(f"Файл прогресса {PROGRESS_FILE} очищен")
    return set()

def save_error(card_id, url, error_message):
    """Сохраняет информацию об ошибке"""
    with open(ERROR_LOG_FILE, "a") as f:
        f.write(f"{card_id},{url},{error_message}\n")

def load_errors():
    """Загружает информацию об ошибках"""
    if not os.path.exists(ERROR_LOG_FILE):
        return {}
    
    errors = {}
    with open(ERROR_LOG_FILE, "r") as f:
        for line in f:
            parts = line.strip().split(",", 2)
            if len(parts) >= 2 and parts[0].isdigit():
                card_id = int(parts[0])
                url = parts[1]
                errors[card_id] = url
    
    return errors

def add_watermark(image_bytes, text=WATERMARK_TEXT):
    """Упрощенная функция добавления водяного знака для максимальной скорости"""
    try:
        # Открываем изображение из байтов
        image = Image.open(BytesIO(image_bytes))
        
        # Сразу создаем объект для рисования с RGBA
        draw = ImageDraw.Draw(image, 'RGBA')
        
        # Используем дефолтный шрифт
        font = ImageFont.load_default()
        
        # Максимально упрощенное размещение
        width, height = image.size
        position = (width - 200, height - 40)
        
        # Рисуем текст полупрозрачным серым
        draw.text(position, text, fill=(128, 128, 128, WATERMARK_OPACITY), font=font)
        
        # Сохраняем с оптимизированными настройками
        output = BytesIO()
        if USE_JPEG:
            image.save(output, format='JPEG', quality=SCREENSHOT_QUALITY, optimize=True)
        else:
            image.save(output, format='PNG', optimize=True, compress_level=1)
        
        return output.getvalue()
    except:
        # В случае любой ошибки возвращаем оригинальное изображение
        return image_bytes

async def setup_browser(playwright):
    """Настройка браузера с максимально оптимизированными параметрами"""
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            '--disable-extensions',
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-setuid-sandbox',
            '--no-sandbox',
            '--no-zygote',          # Отключаем использование zygote процесса
            '--disable-infobars',   # Отключаем инфо-полосы
            '--window-size=1280,720', # Устанавливаем размер окна
            '--disable-features=TranslateUI', # Отключаем интерфейс перевода
            '--disable-notifications', # Отключаем уведомления
            # Удалена опция отключения изображений
        ]
    )
    return browser

async def login(page):
    """Выполняет вход в аккаунт Яндекс, если требуется"""
    if not LOGIN_REQUIRED:
        return True
    
    try:
        logger.info("Выполняется вход в аккаунт...")
        await page.goto(LOGIN_URL, timeout=60000)
        await page.wait_for_selector('input[name="login"]', timeout=10000)
        await page.fill('input[name="login"]', USERNAME)
        await page.click('button[type="submit"]')
        
        await page.wait_for_selector('input[name="passwd"]', timeout=10000)
        await page.fill('input[name="passwd"]', PASSWORD)
        await page.click('button[type="submit"]')
        
        # Ждем перенаправления после входа
        await page.wait_for_load_state('networkidle', timeout=30000)
        
        logger.info("Вход выполнен успешно")
        return True
    except Exception as e:
        logger.error(f"Ошибка при входе: {e}")
        return False

async def close_modal_windows(page):
    """Ультрабыстрая функция закрытия модальных окон"""
    try:
        # Сразу используем JavaScript для закрытия всех возможных модальных окон
        await page.evaluate('''() => {
            // Удаляем все модальные окна одной командой
            document.querySelectorAll('.modal__portal, .modal, .student-modal-old__content, .overlay, .modal-backdrop, [role="dialog"]')
                .forEach(el => el.parentNode ? el.parentNode.removeChild(el) : null);
            
            // Восстанавливаем прокрутку и другие свойства
            document.body.style.overflow = 'auto';
            document.body.style.position = '';
            document.body.style.paddingRight = '0';
        }''')
    except:
        pass  # Игнорируем ошибки для максимальной скорости

async def process_card(page, card, processed_cards, semaphore, pbar, error_cards=None, force_reload=False):
    """Обрабатывает одну карточку и делает скриншот"""
    card_id = card['card_id']
    gz_id = card['gz_id']
    card_order = card['card_order']
    
    # Определяем формат и имя файла
    file_ext = "jpg" if USE_JPEG else "png"
    file_path = f"{OUTPUT_DIR}/{card_id}.{file_ext}"
    
    # Проверяем, не обработана ли уже эта карточка или существует ли уже файл
    if not force_reload and (card_id in processed_cards or os.path.exists(file_path)):
        if card_id not in processed_cards and os.path.exists(file_path):
            # Если файл существует, но карточка не отмечена как обработанная,
            # добавляем её в список обработанных
            save_progress(card_id)
            processed_cards.add(card_id)
            
        pbar.update(1)
        return True
    
    # Если это повторная попытка для карточки с ошибкой, а не карточка из списка
    if error_cards and card_id in error_cards:
        url = error_cards[card_id]
    else:
        url = f"https://education.yandex.ru/classroom/public-lesson/{gz_id}/run/{card_order}/"
    
    # Ограничиваем количество одновременных запросов с помощью семафора
    async with semaphore:
        retry_count = 0
        success = False
        last_error = None
        
        while retry_count < MAX_RETRIES and not success:
            try:
                # Переходим на страницу с оптимизированным ожиданием
                response = await page.goto(
                    url, 
                    timeout=60000,
                    wait_until="domcontentloaded"  # Меньше ожидания
                )
                
                # Проверяем код ответа
                if response.status >= 400:
                    raise Exception(f"HTTP ошибка: {response.status}")
                
                # Оптимизированное ожидание
                try:
                    # Ожидаем загрузки основного контента с меньшим таймаутом
                    await page.wait_for_selector('.lesson-material', timeout=5000)
                except:
                    # Если не нашли селектор, просто ждем стандартное время
                    await page.wait_for_timeout(WAIT_TIME)
                
                # Закрываем все модальные окна перед созданием скриншота
                await close_modal_windows(page)
                
                # Делаем скриншот в память
                screenshot_bytes = await page.screenshot(full_page=True)
                
                # Добавляем водяной знак
                watermarked_bytes = add_watermark(screenshot_bytes)
                
                # Сохраняем изображение с водяным знаком
                with open(file_path, "wb") as f:
                    f.write(watermarked_bytes)
                
                # Сохраняем прогресс
                save_progress(card_id)
                processed_cards.add(card_id)
                
                success = True
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                logger.debug(f"Попытка {retry_count} для карточки {card_id} не удалась: {e}")
                
                # Задержка перед следующей попыткой (уменьшена)
                await asyncio.sleep(RETRY_DELAY / 1000)
        
        # Обновляем прогресс-бар в любом случае
        pbar.update(1)
        
        # Если не удалось после всех попыток, записываем ошибку
        if not success:
            logger.error(f"Ошибка при создании скриншота для карточки {card_id}: {last_error}")
            save_error(card_id, url, last_error)
            return False
        
        return True

async def process_batch_with_browser(playwright, cards_batch, processed_cards, semaphore, pbar, error_cards=None, force_reload=False):
    """Обрабатывает пакет карточек с одним браузером"""
    browser = await setup_browser(playwright)
    context = None
    page = None
    
    try:
        # Создаем основной контекст браузера с оптимизированными настройками
        context = await browser.new_context(
            viewport=RESOLUTION,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
            java_script_enabled=True,  # Включаем JavaScript (нужен для взаимодействия)
            bypass_csp=True,          # Обходим Content Security Policy
            ignore_https_errors=True, # Игнорируем ошибки HTTPS для ускорения
            extra_http_headers={"Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"}
        )
        
        # Удалена блокировка ресурсов, чтобы страницы загружались со всем содержимым
        
        # Отключаем таймаут для ожидания навигации
        context.set_default_navigation_timeout(60000)
        
        # Создаем страницу и выполняем вход
        page = await context.new_page()
        
        # Если требуется вход, выполняем его
        if LOGIN_REQUIRED:
            login_success = await login(page)
            if not login_success:
                logger.error("Не удалось войти в аккаунт. Прерывание.")
                return [False] * len(cards_batch)
        
        # Обрабатываем карточки последовательно в одном браузере
        results = []
        for card in cards_batch:
            try:
                result = await process_card(page, card, processed_cards, semaphore, pbar, error_cards, force_reload)
                results.append(result)
            except Exception as e:
                logger.error(f"Необработанная ошибка при обработке карточки {card['card_id']}: {e}")
                results.append(False)
        
        return results
    
    except Exception as e:
        logger.error(f"Ошибка в обработчике браузера: {e}")
        return [False] * len(cards_batch)
    
    finally:
        # Закрываем ресурсы
        if page:
            await page.close()
        if context:
            await context.close()
        await browser.close()

async def main(force_download=False, specific_card_ids=None):
    # Получаем настройки из командной строки
    args = parse_args()
    card_limit = args.limit
    retry_errors = args.retry_errors
    force_reload = args.force or force_download
    
    # Создаем папку для скриншотов, если ее нет
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # Загружаем или очищаем информацию о прогрессе
    if force_reload:
        logger.info("Включен режим принудительной перезагрузки")
        processed_cards = clear_progress()
    else:
        processed_cards = load_progress()
        logger.info(f"Загружено {len(processed_cards)} обработанных карточек из предыдущих запусков")
    
    # Загружаем информацию об ошибках
    error_cards = load_errors() if retry_errors else None
    
    if specific_card_ids:
        # Если указаны конкретные ID карточек для обработки
        logger.info(f"Подготовка к обработке {len(specific_card_ids)} указанных карточек")
        
        # Получаем данные для указанных ID из базы
        conn = psycopg2.connect(**DB_CONFIG)
        cards_to_process = []
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Получаем данные для каждого ID
            placeholder = ','.join(['%s'] * len(specific_card_ids))
            query = f"""
                SELECT card_id, gz_id, card_order
                FROM cards_structure
                WHERE card_id IN ({placeholder})
                AND gz_id IS NOT NULL AND card_order IS NOT NULL
            """
            cursor.execute(query, specific_card_ids)
            cards_to_process = cursor.fetchall()
        
        conn.close()
        
        total_cards = len(cards_to_process)
        logger.info(f"Найдено {total_cards} карточек из {len(specific_card_ids)} указанных")
        
    elif retry_errors and error_cards:
        logger.info(f"Загружено {len(error_cards)} карточек с ошибками для повторной обработки")
        
        # Если мы повторяем обработку ошибок, создаем список карточек из ошибок
        cards_to_process = []
        for card_id, url in error_cards.items():
            parts = url.split('/')
            if len(parts) >= 6:
                try:
                    gz_id = parts[-3]
                    card_order = parts[-1]
                    cards_to_process.append({
                        'card_id': card_id,
                        'gz_id': gz_id,
                        'card_order': card_order
                    })
                except:
                    logger.warning(f"Не удалось распарсить URL для карточки {card_id}: {url}")
        
        total_cards = len(cards_to_process)
        logger.info(f"Подготовлено {total_cards} карточек с ошибками для повторной обработки")
    else:
        # Получаем общее количество карточек (уникальных card_id)
        total_cards = get_total_cards(card_limit)
        if card_limit > 0:
            logger.info(f"Ограничение установлено на {card_limit} карточек")
        logger.info(f"Всего уникальных карточек для обработки: {total_cards}")
        cards_to_process = None
    
    # Определяем начальное значение для прогресс-бара
    initial_count = 0 if force_reload or retry_errors or specific_card_ids else len(processed_cards)
    
    # Сбор статистики времени выполнения
    start_time = time.time()
    processed_count = len(processed_cards) if not force_reload else 0
    
    # Создаем семафор для ограничения параллельных запросов
    # Увеличиваем лимит семафора для большей параллельности
    semaphore = asyncio.Semaphore(CONCURRENT_BROWSERS * 2)
    
    # Инициализируем прогресс-бар
    pbar = tqdm_module.tqdm(
        total=total_cards, 
        initial=initial_count, 
        desc="Скриншоты", 
        unit="карт", 
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
    )
    
    async with async_playwright() as playwright:
        if specific_card_ids or (retry_errors and cards_to_process):
            # Обрабатываем указанные карточки или карточки с ошибками
            # Разделяем на пакеты для параллельной обработки
            batch_size = min(100, len(cards_to_process))
            batches = [cards_to_process[i:i+batch_size] for i in range(0, len(cards_to_process), batch_size)]
            
            # Запускаем все пакеты одновременно для максимальной параллельности
            tasks = [process_batch_with_browser(playwright, batch, processed_cards, semaphore, pbar, error_cards) for batch in batches]
            results = await asyncio.gather(*tasks)
            
            # Обновляем статистику
            flat_results = [item for sublist in results for item in sublist]
            successful = sum(1 for r in flat_results if r)
            processed_count += successful
        else:
            # Обрабатываем карточки пакетами, запрашивая большие блоки данных
            offset = 0
            processed_in_current_run = 0
            
            # Предзагружаем данные для ускорения (получаем сразу крупный блок)
            prefetch_size = min(5000, total_cards)
            all_cards = get_cards_from_db(prefetch_size, 0) if total_cards <= prefetch_size else None
            
            while offset < total_cards:
                # Определяем размер текущей партии
                current_batch_size = BATCH_SIZE
                if card_limit > 0:
                    remaining = card_limit - processed_in_current_run
                    current_batch_size = min(current_batch_size, max(0, remaining))
                    if remaining <= 0:
                        break
                
                # Получаем пакет карточек (либо из предзагруженных, либо из БД)
                if all_cards:
                    end_index = min(offset + current_batch_size, len(all_cards))
                    cards_batch = all_cards[offset:end_index]
                else:
                    cards_batch = get_cards_from_db(current_batch_size, offset)
                
                if not cards_batch:
                    break
                
                # Разделяем пакет на группы для параллельной обработки
                # Используем более равномерное разделение
                batch_groups = []
                group_size = max(1, len(cards_batch) // CONCURRENT_BROWSERS)
                for i in range(0, len(cards_batch), group_size):
                    batch_groups.append(cards_batch[i:i + group_size])
                
                # Запускаем все группы параллельно
                tasks = [process_batch_with_browser(playwright, group, processed_cards, semaphore, pbar, error_cards, force_reload) for group in batch_groups]
                results = await asyncio.gather(*tasks)
                
                # Обновляем статистику
                flat_results = [item for sublist in results for item in sublist]
                successful = sum(1 for r in flat_results if r)
                processed_count += successful
                processed_in_current_run += len(cards_batch)
                
                # Выводим краткую статистику с частотой обновления
                if offset % 500 == 0:
                    elapsed = time.time() - start_time
                    cards_per_second = processed_count / elapsed if elapsed > 0 else 0
                    logger.info(f"Прогресс: {processed_count}/{total_cards}, Скорость: {cards_per_second:.2f} карточек/сек")
                
                # Переходим к следующему пакету
                offset += current_batch_size
    
    # Закрываем прогресс-бар
    pbar.close()
    
    # Итоговая статистика
    total_time = time.time() - start_time
    logger.info(f"Выполнено за {total_time/60:.2f} минут")
    logger.info(f"Обработано {processed_count} карточек")
    logger.info(f"Средняя скорость: {processed_count/total_time:.2f} карточек/сек")
    
    # Статистика ошибок
    new_errors = load_errors()
    logger.info(f"Количество карточек с ошибками: {len(new_errors)}")
    if new_errors:
        logger.info(f"Для повторной обработки карточек с ошибками запустите скрипт с флагом --retry-errors")

if __name__ == "__main__":
    # Проверяем наличие необходимых пакетов
    try:
        import PIL
        # Примечание: мы уже импортировали tqdm как tqdm_module
    except ImportError:
        print("Установите необходимые зависимости:")
        print("pip install pillow tqdm playwright psycopg2-binary")
        print("playwright install chromium")
        exit(1)
        
    asyncio.run(main())
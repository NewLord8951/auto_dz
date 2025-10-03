from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from loguru import logger
import os
from dotenv import load_dotenv, find_dotenv
import sys
import time

logger.remove()
logger.add(
    "file.log",
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    rotation="3 days", 
    backtrace=True, 
    diagnose=True,
    level="INFO"
)
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}", level="INFO")

load_dotenv(find_dotenv())

LOGIN = os.getenv('LOGIN')
PASSWORD = os.getenv('PASSWORD')
HOMEWORK_LINK = os.getenv('HOMEWORK_LINK', '')

def check_env_variables():
    """Проверка наличия необходимых переменных окружения"""
    if not LOGIN or not PASSWORD:
        logger.error("LOGIN или PASSWORD не установлены в .env файле")
        return False
    return True

def safe_click(element, description="элемент"):
    """Безопасный клик с несколькими попытками"""
    for attempt in range(3):
        try:
            element.scroll_into_view_if_needed()
            element.click(timeout=5000)
            logger.info(f"Успешный клик на {description}")
            return True
        except Exception as e:
            logger.warning(f"Попытка {attempt + 1} клика не удалась: {e}")
            time.sleep(1)
    return False

def login_to_journal(page):
    """Выполнение процесса входа"""
    try:
        logger.info("Загрузка страницы авторизации...")
        page.goto(
            "https://journal.top-academy.ru/ru/auth/login/index?returnUrl=%2Fru%2Fmain%2Fdashboard%2Fpage%2Findex",
            wait_until="networkidle",
            timeout=20000
        )

        logger.info("Ожидание элементов формы...")
        page.wait_for_selector('input[name="username"]', state="visible", timeout=15000)

        page.fill('input[name="username"]', LOGIN)
        page.fill('input[name="password"]', PASSWORD)
        logger.info("Данные для входа введены")

        page.click('button[type="submit"]')
        logger.info("Кнопка входа нажата")

        try:
            page.wait_for_url("**/dashboard/**", timeout=15000)
            logger.success(f"Вход выполнен успешно! Текущий URL: {page.url}")
            return True
        except PlaywrightTimeoutError:
            error_selector = page.locator(".error, .alert-danger, [class*='error']")
            if error_selector.count() > 0:
                error_text = error_selector.first.text_content()
                logger.error(f"Ошибка входа: {error_text}")
            else:
                logger.error("Не удалось определить результат входа")
            return False

    except PlaywrightTimeoutError:
        logger.error("Таймаут при загрузке страницы или элементов формы")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при входе: {e}")
        return False

def navigate_to_homework(page):
    """Навигация к разделу с домашними заданиями"""
    try:
        logger.info("Поиск раздела с домашними заданиями...")
        
        # Даем странице полностью загрузиться
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(3)
        
        # Сначала попробуем найти прямые ссылки на задания
        homework_selectors = [
            "a:has-text('Текущие')",
            "a:has-text('Задания')", 
            "a:has-text('Домашние задания')",
            "a[href*='homework']",
            "a[href*='assignment']",
            "[class*='homework'] a",
            "[class*='assignment'] a"
        ]
        
        for selector in homework_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=3000):
                    logger.info(f"Найдена ссылка: {selector}")
                    if safe_click(element, f"ссылку {selector}"):
                        page.wait_for_load_state("networkidle", timeout=10000)
                        time.sleep(3)
                        return True
            except Exception as e:
                logger.debug(f"Не удалось найти/кликнуть по {selector}: {e}")
                continue
        
        # Если прямые ссылки не найдены, ищем в меню
        logger.info("Поиск в меню навигации...")
        menu_items = page.locator("nav a, .menu a, .navigation a, [class*='nav'] a, [class*='item'] a")
        count = menu_items.count()
        
        logger.info(f"Найдено {count} элементов меню")
        
        for i in range(min(count, 20)):  # Ограничиваем поиск первыми 20 элементами
            try:
                element = menu_items.nth(i)
                text = element.text_content().strip().lower()
                logger.debug(f"Элемент меню {i}: '{text}'")
                
                if any(word in text for word in ['текущие', 'домашн', 'homework', 'assignment', 'задани']):
                    logger.info(f"Найдена подходящая ссылка в меню: {text}")
                    if safe_click(element, f"меню '{text}'"):
                        page.wait_for_load_state("networkidle", timeout=10000)
                        time.sleep(3)
                        return True
            except Exception as e:
                logger.debug(f"Ошибка при обработке элемента меню {i}: {e}")
                continue
        
        logger.error("Не удалось найти раздел с домашними заданиями")
        return False
        
    except Exception as e:
        logger.error(f"Ошибка при навигации к заданиям: {e}")
        return False

def find_homework_buttons(page):
    """Поиск кнопок для загрузки задания"""
    logger.info("Поиск кнопок для загрузки задания...")
    
    # Сначала проверим, есть ли уже выполненные задания
    completed_selectors = [
        ":has-text('Скачать / Посмотреть выполненное задание')",
        ":has-text('Выполнено')",
        ":has-text('Проверено')"
    ]
    
    for selector in completed_selectors:
        try:
            completed_elements = page.locator(selector)
            if completed_elements.count() > 0:
                logger.info("Найдены уже выполненные задания - пропускаем")
                return None
        except:
            continue
    
    # Основные селекторы для кнопок загрузки
    upload_selectors = [
        "button:has-text('Загрузить выполненное задание')",
        "a:has-text('Загрузить выполненное задание')",
        "button:has-text('Сдать задание')",
        "a:has-text('Сдать задание')",
        ":has-text('Загрузить выполненное задание')",
        ":has-text('Сдать задание')",
    ]
    
    for selector in upload_selectors:
        try:
            buttons = page.locator(selector)
            count = buttons.count()
            if count > 0:
                logger.info(f"Найдено {count} кнопок по селектору: {selector}")
                return buttons
        except Exception as e:
            logger.debug(f"Ошибка при поиске по селектору {selector}: {e}")
            continue
    
    # Альтернативные селекторы
    alternative_selectors = [
        "a[href*='homework']",
        "a[href*='assignment']",
        "[class*='homework'] a",
        "[class*='assignment'] a",
        ".btn:has-text('Отправить')",
        ".btn:has-text('Сдать')"
    ]
    
    for selector in alternative_selectors:
        try:
            elements = page.locator(selector)
            count = elements.count()
            if count > 0:
                logger.info(f"Найдено {count} элементов по альтернативному селектору: {selector}")
                return elements
        except Exception as e:
            logger.debug(f"Ошибка при поиске по альтернативному селектору {selector}: {e}")
            continue
    
    return None

def find_and_submit_homework(page, homework_link):
    """Поиск конкретного задания и отправка ссылки"""
    try:
        logger.info("Поиск заданий на странице...")
        
        # Ждем загрузки списка заданий
        page.wait_for_load_state("networkidle", timeout=20000)
        time.sleep(3)
        
        # Сохраняем текущий URL для сравнения
        original_url = page.url
        
        # Ищем кнопки для загрузки задания
        homework_elements = find_homework_buttons(page)
        
        if not homework_elements:
            logger.error("Не найдены кнопки для загрузки задания или задание уже выполнено")
            return False
        
        # Пробуем кликнуть на каждую найденную кнопку
        count = homework_elements.count()
        logger.info(f"Пробуем кликнуть на {count} найденных элементов")
        
        for i in range(count):
            try:
                element = homework_elements.nth(i)
                if element.is_visible(timeout=5000):
                    element_text = element.text_content().strip()
                    logger.info(f"Попытка клика на элемент #{i+1}: '{element_text}'")
                    
                    # Прокручиваем к элементу
                    element.scroll_into_view_if_needed()
                    time.sleep(1)
                    
                    # Сохраняем текущий URL перед кликом
                    before_click_url = page.url
                    
                    # Пробуем кликнуть
                    try:
                        element.click()
                    except:
                        # Если обычный клик не работает, пробуем через JavaScript
                        page.evaluate("(element) => element.click()", element)
                    
                    # Ждем загрузки
                    page.wait_for_load_state("networkidle", timeout=15000)
                    time.sleep(3)
                    
                    # Проверяем, изменился ли URL
                    if page.url != before_click_url:
                        logger.info(f"Успешно перешли на страницу: {page.url}")
                        break
                    else:
                        # Проверяем, не появилось ли модальное окно или форма
                        modal_selectors = [
                            "[role='dialog']",
                            ".modal",
                            "[class*='modal']",
                            ".popup",
                            "form",
                            "textarea",
                            "input[type='text']"
                        ]
                        modal_found = False
                        for modal_selector in modal_selectors:
                            try:
                                if page.locator(modal_selector).first.is_visible(timeout=2000):
                                    logger.info("Обнаружено модальное окно или форма")
                                    modal_found = True
                                    break
                            except:
                                continue
                        
                        if modal_found:
                            break
                        
            except Exception as e:
                logger.debug(f"Ошибка при клике на элемент #{i+1}: {e}")
                continue
        
        # Если все еще на той же странице, выходим
        if page.url == original_url:
            logger.error("Не удалось перейти на страницу загрузки задания")
            page.screenshot(path="debug_no_navigation.png")
            return False
        
        # Теперь мы на странице загрузки задания или в модальном окне
        logger.info(f"Текущий URL: {page.url}")
        
        # Ищем поле для ввода ссылки
        logger.info("Поиск поля для ввода ссылки...")
        
        input_selectors = [
            "textarea",
            "input[type='text']",
            "input[type='url']",
            "[contenteditable='true']",
            ".form-control",
            "[class*='input']",
            "[class*='field']",
            "input:not([type='hidden'])",
            "input[name*='url']",
            "input[name*='link']",
            "input[placeholder*='ссылка']",
            "input[placeholder*='link']",
            "input[placeholder*='URL']",
            "input[placeholder*='url']"
        ]
        
        link_field = None
        
        # Сначала ищем в модальном окне
        for selector in input_selectors:
            try:
                modal_fields = page.locator(f"[role='dialog'] {selector}, .modal {selector}")
                if modal_fields.count() > 0 and modal_fields.first.is_visible(timeout=2000):
                    link_field = modal_fields.first
                    logger.info("Найдено поле в модальном окне")
                    break
            except:
                continue
        
        # Если не нашли в модальном окне, ищем на странице
        if not link_field:
            for selector in input_selectors:
                try:
                    fields = page.locator(selector)
                    if fields.count() > 0:
                        for i in range(fields.count()):
                            try:
                                field = fields.nth(i)
                                if field.is_visible(timeout=2000):
                                    link_field = field
                                    logger.info(f"Найдено поле на странице: {selector}")
                                    break
                            except:
                                continue
                        if link_field:
                            break
                except:
                    continue
        
        if not link_field:
            logger.error("Не найдено подходящего поля для ввода ссылки")
            page.screenshot(path="debug_no_field.png")
            return False
        
        # Заполняем поле ссылкой
        try:
            link_field.scroll_into_view_if_needed()
            link_field.click()
            link_field.clear()
            link_field.fill(homework_link)
            logger.info("Ссылка вставлена в поле")
            time.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка при заполнении поля: {e}")
            return False
        
        # Ищем кнопку отправки
        logger.info("Поиск кнопки отправки...")
        
        submit_selectors = [
            "button:has-text('Отправить')",
            "button:has-text('Submit')", 
            "button:has-text('Сохранить')",
            "button:has-text('Save')",
            "button[type='submit']",
            "input[type='submit']",
            "[class*='submit']",
            "[class*='save']",
            "button:has-text('Загрузить')",
            "button:has-text('Отправить задание')",
            "button:has-text('Send')",
            "button:has-text('Принять')",
            "button:has-text('Готово')"
        ]
        
        submit_button = None
        
        for selector in submit_selectors:
            try:
                buttons = page.locator(selector)
                if buttons.count() > 0:
                    for i in range(buttons.count()):
                        try:
                            button = buttons.nth(i)
                            if button.is_visible(timeout=2000):
                                submit_button = button
                                logger.info(f"Найдена кнопка отправки: {selector}")
                                break
                        except:
                            continue
                    if submit_button:
                        break
            except:
                continue
        
        if not submit_button:
            logger.error("Не найдена кнопка отправки")
            return False
        
        # Нажимаем кнопку отправки
        try:
            submit_button.scroll_into_view_if_needed()
            button_text = submit_button.text_content().strip()
            logger.info(f"Нажимаем кнопку: '{button_text}'")
            
            submit_button.click()
            
            # Ждем обработки
            time.sleep(5)
            
            # Проверяем успешность
            if check_submission_success(page):
                logger.success("Задание успешно отправлено!")
                return True
            else:
                logger.info("Отправка выполнена, но статус не подтвержден")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при нажатии кнопки отправки: {e}")
            return False
        
    except Exception as e:
        logger.error(f"Ошибка при отправке задания: {e}")
        page.screenshot(path="debug_error.png")
        return False

def check_submission_success(page):
    """Проверка успешности отправки задания"""
    try:
        success_indicators = [
            ".alert-success",
            "[class*='success']",
            ":has-text('успешно')",
            ":has-text('отправлено')", 
            ":has-text('принято')",
            ":has-text('загружено')",
            ":has-text('задание отправлено')",
            ":has-text('assignment submitted')"
        ]
        
        for selector in success_indicators:
            try:
                if page.locator(selector).first.is_visible(timeout=5000):
                    success_text = page.locator(selector).first.text_content()
                    logger.success(f"Успех: {success_text.strip()}")
                    return True
            except:
                continue
        
        # Проверяем, не вернулись ли мы на страницу со списком заданий
        if "dashboard" in page.url or "assignment" in page.url or "homework" in page.url:
            logger.info("Вернулись на страницу заданий - вероятно, отправка прошла успешно")
            return True
                
        return False
        
    except Exception as e:
        logger.debug(f"Ошибка при проверке успешности: {e}")
        return False

def auto_fill_homework(page):
    """Автоматическое заполнение домашнего задания"""
    if not HOMEWORK_LINK:
        logger.warning("Ссылка на домашнее задание не указана в переменной HOMEWORK_LINK")
        user_link = input("Введите ссылку на домашнее задание: ").strip()
        if not user_link:
            logger.error("Ссылка не введена")
            return False
    else:
        user_link = HOMEWORK_LINK
        logger.info(f"Используется ссылка: {user_link}")
    
    logger.info("Начинается процесс автозаполнения домашнего задания...")
    
    # Навигация к разделу с заданиями
    if not navigate_to_homework(page):
        logger.error("Не удалось найти раздел с домашними заданиями")
        return False
    
    # Поиск и отправка задания
    for attempt in range(2):  # Уменьшил количество попыток
        logger.info(f"Попытка {attempt + 1} из 2")
        if find_and_submit_homework(page, user_link):
            return True
        time.sleep(3)
    
    logger.error("Не удалось автоматически заполнить домашнее задание")
    return False

def main():
    if not check_env_variables():
        return

    logger.info("Запуск браузера...")

    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
            )
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            context.add_init_script("""
                delete navigator.__proto__.webdriver;
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)

            page = context.new_page()

            if login_to_journal(page):
                logger.info("Успешный вход в систему")

                try:
                    user_element = page.locator("[class*='user'], [class*='profile']").first
                    if user_element.is_visible(timeout=5000):
                        logger.info(f"Пользователь: {user_element.text_content().strip()}")
                except Exception as e:
                    logger.debug(f"Не удалось получить имя пользователя: {e}")

                # Автоматическое заполнение домашнего задания
                logger.info("Запуск автоматического заполнения домашнего задания...")
                if auto_fill_homework(page):
                    logger.success("Процесс завершен успешно!")
                else:
                    logger.warning("Автозаполнение не удалось, но вход выполнен")
                
                input("Нажмите Enter для закрытия...")
            else:
                logger.error("Не удалось выполнить вход")
                input("Нажмите Enter для закрытия...")

        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
        finally:
            if browser:
                browser.close()
                logger.info("Браузер закрыт")

if __name__ == "__main__":
    main()

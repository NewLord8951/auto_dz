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

def navigate_to_homework_section(page):
    """Навигация к разделу с домашними заданиями"""
    try:
        logger.info("Поиск раздела с домашними заданиями...")
        
        # Ждем полной загрузки страницы
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(3)
        
        # Сначала ищем прямые ссылки на домашние задания
        homework_selectors = [
            "a:has-text('Текущие задания')",
            "a:has-text('Домашние задания')",
            "a:has-text('Задания')",
            "a:has-text('Homework')",
            "a:has-text('Assignments')",
            "a[href*='homework']",
            "a[href*='assignment']",
            "a[href*='task']",
            "[class*='homework'] a",
            "[class*='assignment'] a",
            "[class*='task'] a",
            ".nav-link:has-text('Задания')",
            ".menu-item:has-text('Задания')"
        ]
        
        for selector in homework_selectors:
            try:
                elements = page.locator(selector)
                if elements.count() > 0:
                    for i in range(elements.count()):
                        try:
                            element = elements.nth(i)
                            if element.is_visible(timeout=3000):
                                element_text = element.text_content().strip()
                                logger.info(f"Найдена ссылка: '{element_text}'")
                                if safe_click(element, f"ссылку '{element_text}'"):
                                    page.wait_for_load_state("networkidle", timeout=10000)
                                    time.sleep(3)
                                    return True
                        except Exception as e:
                            logger.debug(f"Ошибка с элементом {i} селектора {selector}: {e}")
                            continue
            except Exception as e:
                logger.debug(f"Селектор {selector} не найден: {e}")
                continue
        
        # Если прямые ссылки не найдены, ищем в меню
        logger.info("Поиск в меню навигации...")
        menu_selectors = [
            "nav",
            ".menu",
            ".navigation", 
            "[class*='nav']",
            "[class*='menu']",
            ".sidebar",
            "[class*='sidebar']"
        ]
        
        for menu_selector in menu_selector:
            try:
                menu = page.locator(menu_selector)
                if menu.count() > 0:
                    menu_items = menu.locator("a")
                    count = menu_items.count()
                    logger.info(f"Найдено меню с {count} элементами")
                    
                    for i in range(min(count, 30)):
                        try:
                            item = menu_items.nth(i)
                            if item.is_visible(timeout=2000):
                                text = item.text_content().strip().lower()
                                logger.debug(f"Элемент меню {i}: '{text}'")
                                
                                # Более точные критерии поиска
                                homework_keywords = ['текущие', 'домашн', 'homework', 'assignment', 'задани', 'task', 'урок']
                                if any(keyword in text for keyword in homework_keywords):
                                    logger.info(f"Найдена подходящая ссылка в меню: '{text}'")
                                    if safe_click(item, f"меню '{text}'"):
                                        page.wait_for_load_state("networkidle", timeout=10000)
                                        time.sleep(3)
                                        return True
                        except Exception as e:
                            logger.debug(f"Ошибка при обработке элемента меню {i}: {e}")
                            continue
            except Exception as e:
                logger.debug(f"Ошибка при поиске в {menu_selector}: {e}")
                continue
        
        logger.error("Не удалось найти раздел с домашними заданиями")
        return False
        
    except Exception as e:
        logger.error(f"Ошибка при навигации к заданиям: {e}")
        return False

def find_homework_items(page):
    """Поиск конкретных домашних заданий на странице"""
    logger.info("Поиск домашних заданий на странице...")
    
    # Ждем загрузки контента
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(3)
    
    # Проверяем, есть ли уже выполненные задания
    completed_indicators = [
        ":has-text('Скачать / Посмотреть выполненное задание')",
        ":has-text('Выполнено')",
        ":has-text('Проверено')",
        ":has-text('Сдано')",
        "[class*='completed']",
        "[class*='done']",
        ".status-completed"
    ]
    
    for selector in completed_indicators:
        try:
            if page.locator(selector).first.is_visible(timeout=2000):
                logger.info("Найдены уже выполненные задания - пропускаем")
                return None
        except:
            continue
    
    # Ищем активные домашние задания
    homework_containers = [
        "[class*='homework']",
        "[class*='assignment']", 
        "[class*='task']",
        "[class*='lesson']",
        ".card",
        ".item",
        ".list-item",
        "[class*='widget']"
    ]
    
    active_homeworks = []
    
    for container_selector in homework_containers:
        try:
            containers = page.locator(container_selector)
            count = containers.count()
            if count > 0:
                logger.info(f"Найдено {count} контейнеров типа: {container_selector}")
                
                for i in range(count):
                    try:
                        container = containers.nth(i)
                        if container.is_visible(timeout=2000):
                            container_text = container.text_content().strip().lower()
                            
                            # Ищем контейнеры с домашними заданиями
                            if any(keyword in container_text for keyword in ['домашн', 'homework', 'assignment', 'задани', 'сдать', 'загрузить']):
                                
                                # Ищем кнопки для сдачи в этом контейнере
                                button_selectors = [
                                    "button:has-text('Загрузить выполненное задание')",
                                    "a:has-text('Загрузить выполненное задание')", 
                                    "button:has-text('Сдать задание')",
                                    "a:has-text('Сдать задание')",
                                    "button:has-text('Отправить')",
                                    "button:has-text('Загрузить')",
                                    ".btn:has-text('Сдать')",
                                    ".btn:has-text('Отправить')"
                                ]
                                
                                for btn_selector in button_selectors:
                                    try:
                                        buttons = container.locator(btn_selector)
                                        if buttons.count() > 0:
                                            for j in range(buttons.count()):
                                                try:
                                                    button = buttons.nth(j)
                                                    if button.is_visible(timeout=2000):
                                                        active_homeworks.append({
                                                            'container': container,
                                                            'button': button,
                                                            'text': container_text[:100]  # первые 100 символов для лога
                                                        })
                                                        logger.info(f"Найдено активное ДЗ: {container_text[:100]}...")
                                                        break
                                                except:
                                                    continue
                                    except:
                                        continue
                    except Exception as e:
                        logger.debug(f"Ошибка при обработке контейнера {i}: {e}")
                        continue
        except Exception as e:
            logger.debug(f"Ошибка при поиске контейнеров {container_selector}: {e}")
            continue
    
    return active_homeworks if active_homeworks else None

def submit_homework_link(page, homework_item, homework_link):
    """Отправка ссылки на домашнее задание"""
    try:
        logger.info(f"Обработка домашнего задания: {homework_item['text']}...")
        
        # Кликаем на кнопку в контейнере ДЗ
        button = homework_item['button']
        button_text = button.text_content().strip()
        logger.info(f"Кликаем на кнопку: '{button_text}'")
        
        # Сохраняем текущий URL
        original_url = page.url
        
        if safe_click(button, f"кнопку '{button_text}'"):
            # Ждем изменений
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(3)
            
            # Проверяем, открылась ли форма
            if page.url != original_url or check_if_modal_opened(page):
                logger.info("Форма для загрузки задания открыта")
                return fill_homework_form(page, homework_link)
            else:
                logger.warning("Форма не открылась после клика")
                return False
        else:
            logger.error("Не удалось кликнуть на кнопку")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при отправке задания: {e}")
        return False

def check_if_modal_opened(page):
    """Проверка, открылось ли модальное окно"""
    modal_indicators = [
        "[role='dialog']",
        ".modal",
        "[class*='modal']",
        ".popup",
        ".dialog",
        "form:visible",
        "textarea:visible",
        "input[type='text']:visible"
    ]
    
    for selector in modal_indicators:
        try:
            if page.locator(selector).first.is_visible(timeout=3000):
                logger.info(f"Обнаружено модальное окно/форма: {selector}")
                return True
        except:
            continue
    
    return False

def fill_homework_form(page, homework_link):
    """Заполнение формы домашнего задания"""
    try:
        logger.info("Заполнение формы домашнего задания...")
        
        # Ищем поле для ввода ссылки
        input_selectors = [
            "textarea",
            "input[type='text']",
            "input[type='url']",
            "[contenteditable='true']",
            ".form-control",
            "[class*='input']",
            "[class*='field']",
            "input[name*='url']",
            "input[name*='link']",
            "input[placeholder*='ссылка']",
            "input[placeholder*='link']",
            "input[placeholder*='URL']"
        ]
        
        link_field = None
        
        # Сначала ищем в модальном окне
        for selector in input_selectors:
            try:
                modal_fields = page.locator(f"[role='dialog'] {selector}, .modal {selector}")
                if modal_fields.count() > 0:
                    for i in range(modal_fields.count()):
                        if modal_fields.nth(i).is_visible(timeout=2000):
                            link_field = modal_fields.nth(i)
                            logger.info("Найдено поле в модальном окне")
                            break
                    if link_field:
                        break
            except:
                continue
        
        # Если не нашли в модальном, ищем на странице
        if not link_field:
            for selector in input_selectors:
                try:
                    fields = page.locator(selector)
                    if fields.count() > 0:
                        for i in range(fields.count()):
                            if fields.nth(i).is_visible(timeout=2000):
                                link_field = fields.nth(i)
                                logger.info(f"Найдено поле на странице: {selector}")
                                break
                        if link_field:
                            break
                except:
                    continue
        
        if not link_field:
            logger.error("Не найдено поле для ввода ссылки")
            page.screenshot(path="debug_no_input_field.png")
            return False
        
        # Заполняем поле
        link_field.click()
        link_field.clear()
        link_field.fill(homework_link)
        logger.info("Ссылка вставлена в поле")
        time.sleep(1)
        
        # Ищем кнопку отправки
        submit_selectors = [
            "button:has-text('Отправить')",
            "button:has-text('Submit')",
            "button:has-text('Сохранить')", 
            "button:has-text('Save')",
            "button[type='submit']",
            "input[type='submit']",
            "[class*='submit']",
            "button:has-text('Загрузить')",
            "button:has-text('Готово')"
        ]
        
        submit_button = None
        
        for selector in submit_selectors:
            try:
                buttons = page.locator(selector)
                if buttons.count() > 0:
                    for i in range(buttons.count()):
                        if buttons.nth(i).is_visible(timeout=2000):
                            submit_button = buttons.nth(i)
                            logger.info(f"Найдена кнопка отправки: {selector}")
                            break
                    if submit_button:
                        break
            except:
                continue
        
        if not submit_button:
            logger.error("Не найдена кнопка отправки")
            return False
        
        # Нажимаем кнопку
        submit_button.click()
        logger.info("Кнопка отправки нажата")
        
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
        logger.error(f"Ошибка при заполнении формы: {e}")
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
            ":has-text('загружено')"
        ]
        
        for selector in success_indicators:
            try:
                if page.locator(selector).first.is_visible(timeout=5000):
                    success_text = page.locator(selector).first.text_content()
                    logger.success(f"Успех: {success_text.strip()}")
                    return True
            except:
                continue
                
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
    if not navigate_to_homework_section(page):
        logger.error("Не удалось найти раздел с домашними заданиями")
        return False
    
    # Поиск конкретных домашних заданий
    homework_items = find_homework_items(page)
    
    if not homework_items:
        logger.info("Не найдено активных домашних заданий для выполнения")
        return True  # Не ошибка, просто нет заданий
    
    logger.info(f"Найдено {len(homework_items)} активных домашних заданий")
    
    # Обрабатываем первое найденное задание
    success = submit_homework_link(page, homework_items[0], user_link)
    
    if success:
        logger.success("Домашнее задание успешно обработано!")
        return True
    else:
        logger.error("Не удалось отправить домашнее задание")
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

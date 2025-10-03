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

def login_to_journal(page):
    """Выполнение процесса входа"""
    try:
        logger.info("Загрузка страницы авторизации...")
        page.goto(
            "https://journal.top-academy.ru/ru/auth/login/index?returnUrl=%2Fru%2Fmain%2Fdashboard%2Fpage%2Findex",
            wait_until="networkidle",
            timeout=15000
        )

        logger.info("Ожидание элементов формы...")
        page.wait_for_selector('input[name="username"]', state="visible", timeout=10000)

        page.fill('input[name="username"]', LOGIN)
        page.fill('input[name="password"]', PASSWORD)
        logger.info("Данные для входа введены")

        page.click('button[type="submit"]')
        logger.info("Кнопка входа нажата")

        try:
            page.wait_for_url("**/dashboard/**", timeout=10000)
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
                if page.locator(selector).first.is_visible(timeout=2000):
                    page.locator(selector).first.click()
                    logger.info(f"Нажата ссылка: {selector}")
                    page.wait_for_load_state("networkidle", timeout=10000)
                    time.sleep(3)
                    return True
            except:
                continue
        
        # Если прямые ссылки не найдены, ищем в меню
        logger.info("Поиск в меню навигации...")
        menu_items = page.locator("nav a, .menu a, .navigation a, [class*='nav'] a, [class*='item'] a")
        count = menu_items.count()
        
        for i in range(count):
            try:
                text = menu_items.nth(i).text_content().strip().lower()
                if any(word in text for word in ['текущие', 'домашн', 'homework', 'assignment', 'задани']):
                    menu_items.nth(i).click()
                    logger.info(f"Найдена ссылка в меню: {text}")
                    page.wait_for_load_state("networkidle", timeout=10000)
                    time.sleep(3)
                    return True
            except:
                continue
        
        return False
        
    except Exception as e:
        logger.error(f"Ошибка при навигации к заданиям: {e}")
        return False

def find_and_submit_homework(page, homework_link):
    """Поиск конкретного задания и отправка ссылки"""
    try:
        logger.info("Поиск заданий на странице...")
        
        # Ждем загрузки списка заданий
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(3)
        
        # Сохраняем текущий URL для сравнения
        original_url = page.url
        
        # Ищем кнопку "Помощь с домашним заданием" - приоритетный поиск
        logger.info("Поиск кнопки 'Помощь с домашним заданием'...")
        
        upload_selectors = [
            "a:has-text('Помощь с домашним заданием')",
            "button:has-text('Помощь с домашним заданием')",
            ":has-text('Помощь с домашним заданием')",
            "a:has-text('Загрузить выполненное задание')",
            "button:has-text('Загрузить выполненное задание')",
            ":has-text('Загрузить выполненное задание')",
            "a:has-text('Сдать задание')",
            "button:has-text('Сдать задание')",
        ]
        
        button_clicked = False
        
        for selector in upload_selectors:
            try:
                upload_buttons = page.locator(selector)
                count = upload_buttons.count()
                if count > 0:
                    logger.info(f"Найдено {count} кнопок по селектору: {selector}")
                    
                    # Пробуем кликнуть на все найденные кнопки по порядку
                    for i in range(count):
                        try:
                            button = upload_buttons.nth(i)
                            if button.is_visible(timeout=3000):
                                button_text = button.text_content().strip()
                                logger.info(f"Кликаем на кнопку #{i+1}: '{button_text}'")
                                button.scroll_into_view_if_needed()
                                time.sleep(1)
                                
                                # Пробуем разные варианты клика
                                try:
                                    button.click()
                                except:
                                    # Если обычный клик не работает, пробуем через JavaScript
                                    page.evaluate("(element) => element.click()", button)
                                
                                # Ждем загрузки
                                page.wait_for_load_state("networkidle", timeout=10000)
                                time.sleep(3)
                                
                                # Проверяем, изменился ли URL
                                if page.url != original_url:
                                    logger.info(f"Успешно перешли на страницу: {page.url}")
                                    button_clicked = True
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
                                    for modal_selector in modal_selectors:
                                        if page.locator(modal_selector).first.is_visible(timeout=2000):
                                            logger.info("Обнаружено модальное окно или форма")
                                            button_clicked = True
                                            break
                                    
                                    if button_clicked:
                                        break
                                        
                        except Exception as e:
                            logger.debug(f"Ошибка при клике на кнопку #{i+1}: {e}")
                            continue
                    
                    if button_clicked:
                        break
            except:
                continue
        
        # Если не нашли нужные кнопки, ищем другие варианты
        if not button_clicked:
            logger.info("Поиск других кликабельных элементов...")
            
            other_selectors = [
                "a:has-text('Помощь')",
                "button:has-text('Помощь')",
                "a[href*='homework']",
                "a[href*='assignment']",
                "[class*='homework'] a",
                "[class*='assignment'] a",
                ".btn:has-text('Отправить')",
                ".btn:has-text('Сдать')"
            ]
            
            for selector in other_selectors:
                try:
                    elements = page.locator(selector)
                    if elements.count() > 0:
                        elements.first.click()
                        logger.info(f"Кликнули на элемент: {selector}")
                        page.wait_for_load_state("networkidle", timeout=10000)
                        time.sleep(3)
                        button_clicked = True
                        break
                except:
                    continue
        
        # Если все еще не нашли, пробуем кликнуть на первую карточку задания
        if not button_clicked:
            logger.info("Попытка клика на первую карточку задания...")
            assignment_cards = page.locator(".card, [class*='assignment'], [class*='homework']")
            if assignment_cards.count() > 0:
                try:
                    assignment_cards.first.click()
                    logger.info("Кликнули на первую карточку задания")
                    page.wait_for_load_state("networkidle", timeout=10000)
                    time.sleep(3)
                    button_clicked = True
                except Exception as e:
                    logger.debug(f"Не удалось кликнуть на карточку: {e}")
        
        # Если все еще на той же странице, выходим
        if not button_clicked and page.url == original_url:
            logger.error("Не удалось найти или нажать на кнопку для загрузки задания")
            page.screenshot(path="debug_no_button.png")
            logger.info("Скриншот сохранен как debug_no_button.png")
            return False
        
        # Теперь мы на странице загрузки задания или в модальном окне
        logger.info(f"Текущий URL: {page.url}")
        
        # Ищем поле для ввода ссылки - сначала в модальном окне, потом на странице
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
        
        link_field_found = False
        
        # Сначала ищем в модальном окне
        modal_inputs = page.locator("[role='dialog'] textarea, [role='dialog'] input[type='text'], .modal textarea, .modal input[type='text']")
        if modal_inputs.count() > 0:
            try:
                modal_inputs.first.click()
                modal_inputs.first.clear()
                modal_inputs.first.fill(homework_link)
                logger.info("Ссылка вставлена в поле модального окна")
                link_field_found = True
            except Exception as e:
                logger.debug(f"Не удалось вставить в модальное окно: {e}")
        
        # Если не нашли в модальном окне, ищем на странице
        if not link_field_found:
            for selector in input_selectors:
                try:
                    fields = page.locator(selector)
                    count = fields.count()
                    
                    for i in range(count):
                        try:
                            field = fields.nth(i)
                            if field.is_visible(timeout=3000):
                                # Прокручиваем к полю
                                field.scroll_into_view_if_needed()
                                time.sleep(1)
                                
                                # Очищаем поле и вводим ссылку
                                field.click()
                                field.clear()
                                field.fill(homework_link)
                                logger.info(f"Ссылка вставлена в поле: {selector}")
                                link_field_found = True
                                break
                        except Exception as e:
                            logger.debug(f"Ошибка при работе с полем #{i+1}: {e}")
                            continue
                    
                    if link_field_found:
                        break
                        
                except:
                    continue
        
        if not link_field_found:
            logger.warning("Не найдено подходящего поля для ввода ссылки")
            page.screenshot(path="debug_no_field.png")
            logger.info("Скриншот сохранен как debug_no_field.png")
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
        
        submitted = False
        
        for selector in submit_selectors:
            try:
                submit_buttons = page.locator(selector)
                count = submit_buttons.count()
                
                for i in range(count):
                    try:
                        button = submit_buttons.nth(i)
                        if button.is_visible(timeout=3000):
                            button.scroll_into_view_if_needed()
                            button_text = button.text_content().strip()
                            logger.info(f"Нажимаем кнопку: '{button_text}'")
                            
                            # Пробуем кликнуть
                            try:
                                button.click()
                            except:
                                page.evaluate("(element) => element.click()", button)
                            
                            # Ждем обработки
                            time.sleep(5)
                            
                            # Проверяем успешность
                            if check_submission_success(page):
                                logger.success("Задание успешно отправлено!")
                                return True
                            else:
                                logger.info("Отправка выполнена, но статус не подтвержден")
                                submitted = True
                                break
                    except Exception as e:
                        logger.debug(f"Ошибка при нажатии кнопки #{i+1}: {e}")
                        continue
                
                if submitted:
                    break
                    
            except:
                continue
        
        if not submitted:
            logger.warning("Кнопка отправки не найдена или не сработала")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отправке задания: {e}")
        page.screenshot(path="debug_error.png")
        logger.info("Скриншот ошибки сохранен как debug_error.png")
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
    for attempt in range(3):
        logger.info(f"Попытка {attempt + 1} из 3")
        if find_and_submit_homework(page, user_link):
            return True
        time.sleep(2)
    
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
                args=["--disable-blink-features=AutomationControlled"]
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
                    const pluginArray = {
                        length: 3,
                        item: () => null,
                        namedItem: () => null,
                        [Symbol.iterator]: function* () {
                            yield { name: "Chrome PDF Plugin", filename: "internal-pdf-viewer" };
                            yield { name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojoecjjalo" };
                            yield { name: "Native Client", filename: "internal-nacl-plugin" };
                        }
                    };
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => pluginArray
                    });
                    const originalQuery = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(param) {
                        if (param === 37445) return 'Google Inc.';
                        if (param === 37446) return 'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)';
                        return originalQuery.call(this, param);
                    };
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
                choice = input("Хотите автоматически заполнить домашнее задание? (y/n): ").strip().lower()
                if choice in ['y', 'yes', 'д', 'да']:
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

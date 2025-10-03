from playwright.sync_api import sync_playwright
from loguru import logger
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

LOGIN = os.getenv('LOGIN')
PASSWORD = os.getenv('PASSWORD')
logger.info("Запуск браузера...")

with sync_playwright() as p:
    logger.add("file.log",
               format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
               rotation="3 days", backtrace=True, diagnose=True)

    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    page.goto("https://journal.top-academy.ru/  ")
    logger.info("Страница загружена")

    page.wait_for_selector('input[name="username"]', timeout=10000)

    page.fill('input[name="username"]', LOGIN)
    page.fill('input[name="password"]', PASSWORD)
    logger.info("Данные для входа введены")

    page.click('button[type="submit"]')
    logger.info("Кнопка входа нажата")

    page.wait_for_timeout(5000)

    logger.success(f"Вход выполнен! Текущий URL: {page.url}")

    page.goto("https://journal.top-academy.ru/main/homework/page/index  ")

    # Ждем загрузки страницы с домашними заданиями
    page.wait_for_selector('.homework-item', timeout=10000)
    logger.info("Страница с домашними заданиями загружена")

    # Ищем все элементы с домашними заданиями
    homework_items = page.query_selector_all('.homework-item')
    logger.info(f"Найдено элементов с домашними заданиями: {len(homework_items)}")

    # Проходим по каждому домашнему заданию
    for index, homework_item in enumerate(homework_items):
        try:
            # Проверяем, есть ли кнопка загрузки выполненного задания
            upload_button = homework_item.query_selector('.upload-file img[src*="upload.png"]')
            
            if upload_button:
                # Получаем информацию о предмете для логирования
                subject_element = homework_item.query_selector('.name-spec')
                subject_name = subject_element.inner_text() if subject_element else f"Задание {index + 1}"
                
                logger.info(f"Найдена кнопка загрузки для: {subject_name}")
                
                # Наводим курсор на элемент, чтобы показать кнопки
                homework_item.hover()
                page.wait_for_timeout(1000)  # Ждем появления кнопок
                
                # Кликаем на кнопку загрузки
                upload_button.click()
                logger.info(f"Клик на кнопку загрузки для: {subject_name}")
                
                # Ждем появления модального окна или формы загрузки
                page.wait_for_timeout(3000)
                
                # Загружаем файл cat.jpg через input элемент
                try:
                    # Находим input[type="file"] напрямую
                    input_file = page.wait_for_selector('input[type="file"]', timeout=5000)
                    
                    # Получаем путь к файлу cat.jpg (рядом с main.py)
                    file_path = os.path.join(os.path.dirname(__file__), 'cat.jpg')
                    logger.info(f"Путь к файлу: {file_path}")
                    
                    # Загружаем файл через input элемент
                    input_file.set_input_files(file_path)
                    logger.info(f"Файл cat.jpg успешно загружен")
                    
                    # Ждем немного для обработки файла
                    page.wait_for_timeout(2000)
                    
                    # Клик на рейтинг звездочек и заполнение времени
                    try:
                        # Кликаем на одну из звезд рейтинга (например, на 5-ю звезду)
                        star_buttons = [
                            '.bs-rating-star[title="5"] .rating-star',  # 5-я звезда
                            '.bs-rating-star[title="4"] .rating-star',  # 4-я звезда  
                            '.bs-rating-star[title="3"] .rating-star',  # 3-я звезда
                            '.bs-rating-star[title="2"] .rating-star',  # 2-я звезда
                            '.bs-rating-star[title="1"] .rating-star',  # 1-я звезда
                            '.rating-star',  # Любая звезда
                            '.bs-rating-star button'  # Альтернативный селектор
                        ]
                        
                        for star_selector in star_buttons:
                            try:
                                page.wait_for_selector(star_selector, timeout=1000)
                                page.click(star_selector)
                                logger.info(f"Клик на звезду рейтинга выполнен (селектор: {star_selector})")
                                break
                            except:
                                continue
                        else:
                            logger.warning("Не удалось найти звезду рейтинга")
                        
                        page.wait_for_timeout(1000)
                        
                        # Заполняем поле часов
                        hours_input = page.wait_for_selector('input[placeholder="чч"]', timeout=3000)
                        hours_input.click()
                        hours_input.fill('12')  # Любая цифра, например 12
                        logger.info("Поле часов заполнено: 12")
                        page.wait_for_timeout(500)
                        
                        # Заполняем поле минут
                        minutes_input = page.wait_for_selector('input[placeholder="мм"]', timeout=3000)
                        minutes_input.click()
                        minutes_input.fill('30')  # Любая цифра, например 30
                        logger.info("Поле минут заполнено: 30")
                        page.wait_for_timeout(500)
                        
                    except Exception as time_error:
                        logger.error(f"Ошибка при работе с рейтингом и полями времени: {time_error}")
                    
                    # ЗАМЕНА: Нажимаем кнопку "Отправить" вместо закрытия
                    try:
                        # Ищем кнопку "Отправить"
                        submit_buttons = [
                            'button.btn.btn-accept:has-text("Отправить")',
                            'button:has-text("Отправить")',
                            '.btn-accept',
                            'button[class*="accept"]'
                        ]
                        
                        for submit_selector in submit_buttons:
                            try:
                                submit_btn = page.wait_for_selector(submit_selector, timeout=3000)
                                if submit_btn and submit_btn.is_visible():
                                    submit_btn.click()
                                    logger.info("Кнопка 'Отправить' нажата")
                                    page.wait_for_timeout(3000)  # Ждем обработки отправки
                                    
                                    # Проверяем, закрылось ли модальное окно после отправки
                                    try:
                                        page.wait_for_selector('.modal', state='hidden', timeout=3000)
                                        logger.info("Модальное окно закрылось после отправки")
                                    except:
                                        logger.info("Модальное окно все еще открыто")
                                    break
                            except:
                                continue
                        else:
                            logger.warning("Не удалось найти кнопку 'Отправить', пробуем Escape")
                            page.keyboard.press('Escape')
                            page.wait_for_timeout(1000)
                            
                    except Exception as submit_error:
                        logger.warning(f"Не удалось нажать кнопку 'Отправить': {submit_error}")
                        # Запасной вариант - закрываем через Escape
                        try:
                            page.keyboard.press('Escape')
                            page.wait_for_timeout(1000)
                        except:
                            pass
                    
                except Exception as e:
                    logger.error(f"Ошибка при загрузке файла: {e}")
                    # Пробуем закрыть модальное окно даже при ошибке
                    try:
                        page.keyboard.press('Escape')
                        page.wait_for_timeout(1000)
                    except:
                        pass
                
                logger.success(f"Обработка завершена для: {subject_name}")
                
        except Exception as e:
            logger.error(f"Ошибка при обработке задания {index + 1}: {e}")
            # Пробуем закрыть возможное модальное окно
            try:
                page.keyboard.press('Escape')
                page.wait_for_timeout(1000)
            except:
                pass

    logger.info("Обработка домашних заданий завершена")

    input("Вход выполнен. Нажмите Enter для закрытия...")

    browser.close()

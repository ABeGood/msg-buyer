"""
SeleniumBaseScraper - скрапер с обходом Cloudflare через SeleniumBase UC mode

Использует undetected-chromedriver режим SeleniumBase для обхода:
- Cloudflare JS Challenge
- Cloudflare Turnstile CAPTCHA
- Другие anti-bot системы
"""
import time
import random
from typing import Optional, Tuple

from seleniumbase import SB
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from sources.scrapers.base_scraper import BaseScraper


class SeleniumBaseScraper(BaseScraper):
    """
    Скрапер на основе SeleniumBase с режимом undetected-chromedriver

    Наследуется от BaseScraper и переопределяет инициализацию драйвера
    для использования SeleniumBase UC mode (обход Cloudflare)
    """

    def __init__(
        self,
        headless: bool = False,
        window_size: Tuple[int, int] = (1920, 1080),
        min_delay: float = 2.0,
        max_delay: float = 5.0
    ):
        """
        Инициализация SeleniumBaseScraper

        Args:
            headless: Запускать браузер в фоновом режиме (менее надежно для Cloudflare)
            window_size: Размер окна браузера (ширина, высота)
            min_delay: Минимальная задержка между действиями
            max_delay: Максимальная задержка между действиями
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.sb = None
        self._context = None

        # Вызываем конструктор BaseScraper
        # Но _init_driver будет переопределен
        self.driver = None
        self.headless = headless
        self.window_size = window_size
        # Не вызываем super().__init__() чтобы не запускать _init_driver автоматически
        # Драйвер будет создан при первом вызове get_page или start()

    def _init_driver(self):
        """
        Переопределение инициализации драйвера для SeleniumBase UC mode
        """
        self._context = SB(uc=True, headless=self.headless)
        self.sb = self._context.__enter__()
        self.driver = self.sb.driver

        # Устанавливаем размер окна
        self.driver.set_window_size(*self.window_size)
        print("[OK] SeleniumBase UC mode инициализирован")

    def start(self):
        """
        Запуск браузера в UC режиме
        """
        if not self.sb:
            self._init_driver()

    def get_page(self, url: str, timeout: int = 10, reconnect_tries: int = 3) -> bool:
        """
        Переход на страницу с автоматическим обходом Cloudflare

        Args:
            url: URL страницы
            timeout: Таймаут загрузки (для совместимости с BaseScraper)
            reconnect_tries: Количество попыток переподключения при Cloudflare challenge

        Returns:
            bool: True если страница загружена успешно
        """
        if not self.sb:
            self.start()

        try:
            print(f"Переход на страницу: {url}")

            # Используем uc_open_with_reconnect для автоматического обхода Cloudflare
            self.sb.uc_open_with_reconnect(url, reconnect_tries)

            # Проверяем, не появился ли Cloudflare challenge
            if self._handle_cloudflare_challenge():
                print("[OK] Cloudflare challenge пройден")

            self.random_delay()
            print("Страница успешно загружена")
            return True

        except Exception as e:
            print(f"Ошибка при загрузке страницы: {e}")
            return False

    def _handle_cloudflare_challenge(self) -> bool:
        """
        Обработка Cloudflare challenge (если появился)

        Returns:
            bool: True если challenge был обнаружен и пройден
        """
        try:
            # Проверяем наличие кнопки Verify
            if self.sb.is_element_visible('input[value*="Verify"]'):
                print("[INFO] Обнаружена кнопка Verify, кликаем...")
                self.sb.uc_click('input[value*="Verify"]')
                time.sleep(3)
                return True

            # Проверяем наличие Turnstile CAPTCHA
            if self.sb.is_element_visible('iframe[title*="Cloudflare"]'):
                print("[INFO] Обнаружен Cloudflare iframe, пытаемся решить...")
                try:
                    self.sb.uc_gui_click_captcha()
                    time.sleep(3)
                    return True
                except:
                    pass

            # Альтернативный метод: поиск checkbox в iframe
            try:
                from selenium.webdriver.common.by import By

                # Пробуем найти iframe с Cloudflare challenge
                iframe_selectors = [
                    "iframe[title='Widget containing a Cloudflare security challenge']",
                    "iframe[title*='Cloudflare']",
                    "iframe[src*='challenges.cloudflare.com']"
                ]

                for selector in iframe_selectors:
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, selector))
                        )

                        # Кликаем на checkbox
                        checkbox = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "label.ctp-checkbox-label, input[type='checkbox']"))
                        )
                        checkbox.click()

                        # Возвращаемся к основному контенту
                        self.driver.switch_to.default_content()
                        time.sleep(3)
                        return True
                    except:
                        self.driver.switch_to.default_content()
                        continue

            except Exception:
                pass

            return False

        except Exception as e:
            print(f"[WARNING] Ошибка при обработке Cloudflare challenge: {e}")
            return False

    def wait_for_element(self, by, value, timeout: int = 10):
        """
        Ожидание появления элемента на странице

        Переопределяет метод BaseScraper для поддержки SeleniumBase

        Args:
            by: Способ поиска (By.ID, By.CLASS_NAME, By.XPATH и т.д.)
            value: Значение для поиска
            timeout: Максимальное время ожидания в секундах

        Returns:
            WebElement или None
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            print(f"Элемент не найден: {by}={value}")
            return None

    def wait_for_element_css(self, selector: str, timeout: int = 10):
        """
        Ожидание появления элемента по CSS селектору (SeleniumBase стиль)

        Args:
            selector: CSS селектор элемента
            timeout: Таймаут в секундах

        Returns:
            WebElement или None
        """
        try:
            self.sb.wait_for_element(selector, timeout=timeout)
            return self.sb.find_element(selector)
        except:
            return None

    def random_delay(self, min_sec: Optional[float] = None, max_sec: Optional[float] = None):
        """
        Случайная задержка между действиями
        """
        min_sec = min_sec or self.min_delay
        max_sec = max_sec or self.max_delay
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def human_delay(self):
        """
        Задержка, имитирующая время на чтение страницы
        """
        delay = random.gauss(5, 2)
        delay = max(2, min(delay, 10))
        time.sleep(delay)

    def scroll_down(self):
        """
        Прокрутка страницы вниз
        """
        if self.sb:
            self.sb.scroll_to_bottom()

    def scroll_to_element(self, selector: str):
        """
        Прокрутка к элементу
        """
        if self.sb:
            try:
                self.sb.scroll_to(selector)
            except:
                pass

    def click(self, selector: str):
        """
        Клик по элементу с UC mode (менее детектируемый)
        """
        if self.sb:
            try:
                self.sb.uc_click(selector)
            except:
                self.sb.click(selector)

    def close(self):
        """
        Закрытие браузера
        """
        if self._context:
            try:
                self._context.__exit__(None, None, None)
            except:
                pass
            self._context = None
            self.sb = None
            self.driver = None
            print("Браузер закрыт")

    def __enter__(self):
        """Поддержка контекстного менеджера"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие при выходе из контекста"""
        self.close()

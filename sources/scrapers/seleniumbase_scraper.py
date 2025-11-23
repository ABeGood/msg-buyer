"""
SeleniumBaseScraper - скрапер с обходом Cloudflare через SeleniumBase UC mode

Использует undetected-chromedriver режим SeleniumBase для обхода:
- Cloudflare JS Challenge
- Cloudflare Turnstile CAPTCHA
- Другие anti-bot системы
"""
import time
import random
from typing import Optional, Tuple, List, Generator

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
        min_delay: float = 0.5,
        max_delay: float = 1.5
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
        start_total = time.time()
        print("[CF] Проверка Cloudflare challenge...")

        try:
            # Проверяем наличие кнопки Verify
            start = time.time()
            if self.sb.is_element_visible('input[value*="Verify"]'):
                print(f"[CF] Кнопка Verify найдена ({time.time() - start:.2f}s), кликаем...")
                self.sb.uc_click('input[value*="Verify"]')
                time.sleep(1)
                print(f"[CF] Verify пройден, всего: {time.time() - start_total:.2f}s")
                return True
            print(f"[CF] Шаг 1 - Verify check: {time.time() - start:.2f}s")

            # Проверяем наличие Turnstile CAPTCHA
            start = time.time()
            if self.sb.is_element_visible('iframe[title*="Cloudflare"]'):
                print(f"[CF] Cloudflare iframe найден ({time.time() - start:.2f}s), решаем...")
                try:
                    self.sb.uc_gui_click_captcha()
                    time.sleep(1)
                    print(f"[CF] CAPTCHA пройдена, всего: {time.time() - start_total:.2f}s")
                    return True
                except Exception as e:
                    print(f"[CF] Ошибка CAPTCHA: {e}")
            print(f"[CF] Шаг 2 - iframe check: {time.time() - start:.2f}s")

            # Альтернативный метод: поиск checkbox в iframe
            start = time.time()
            try:
                from selenium.webdriver.common.by import By

                iframe_selectors = [
                    "iframe[title='Widget containing a Cloudflare security challenge']",
                    "iframe[title*='Cloudflare']",
                    "iframe[src*='challenges.cloudflare.com']"
                ]

                for selector in iframe_selectors:
                    try:
                        WebDriverWait(self.driver, 1.5).until(
                            EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, selector))
                        )
                        print(f"[CF] iframe найден: {selector}")

                        checkbox = WebDriverWait(self.driver, 1.5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "label.ctp-checkbox-label, input[type='checkbox']"))
                        )
                        checkbox.click()

                        self.driver.switch_to.default_content()
                        time.sleep(1)
                        print(f"[CF] Checkbox кликнут, всего: {time.time() - start_total:.2f}s")
                        return True
                    except:
                        self.driver.switch_to.default_content()
                        continue

            except Exception:
                pass
            print(f"[CF] Шаг 3 - iframe checkbox: {time.time() - start:.2f}s")

            print(f"[CF] Challenge не обнаружен, всего: {time.time() - start_total:.2f}s")
            return False

        except Exception as e:
            print(f"[CF] Ошибка: {e}, всего: {time.time() - start_total:.2f}s")
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
        delay = random.gauss(2, 1)
        delay = max(0.5, min(delay, 4))
        time.sleep(delay)

    def wait_for_page_load(self, timeout: int = 15) -> bool:
        """
        Ожидание полной загрузки страницы

        Args:
            timeout: Максимальное время ожидания в секундах

        Returns:
            bool: True если страница загружена
        """
        try:
            # Ждем document.readyState == complete
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Дополнительно ждем пока не появятся товары на странице
            from selenium.webdriver.common.by import By
            try:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-part-id], .add-to-wishlist, .MuiCard-root"))
                )
            except TimeoutException:
                pass  # Не критично если не найдено

            return True

        except Exception as e:
            print(f"[WARNING] Таймаут ожидания загрузки: {e}")
            return False

    def dismiss_cookie_dialog(self) -> bool:
        """
        Закрытие cookie диалога (Accept All)

        Returns:
            bool: True если диалог закрыт
        """
        accept_selectors = [
            "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
            "#CybotCookiebotDialogBodyButtonAccept",
            "button[id*='Accept']",
            ".CybotCookiebotDialogBodyButton"
        ]

        try:
            for selector in accept_selectors:
                try:
                    if self.sb.is_element_visible(selector):
                        self.sb.uc_click(selector)
                        print("[OK] Cookie диалог закрыт")
                        time.sleep(0.5)
                        return True
                except:
                    continue

            # Попробуем закрыть крестиком
            close_btn = ".CybotCookiebotBannerCloseButton"
            if self.sb.is_element_visible(close_btn):
                self.sb.uc_click(close_btn)
                print("[OK] Cookie диалог закрыт (крестик)")
                return True

            return False
        except Exception as e:
            print(f"[WARNING] Не удалось закрыть cookie диалог: {e}")
            return False

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

    def get_steering_racks_pages(
        self,
        start_page: int = 1,
        end_page: int = 10
    ) -> Generator[str, None, None]:
        """
        Генератор для получения HTML страниц со списком steering racks

        Args:
            start_page: Начальная страница (1-indexed)
            end_page: Конечная страница (включительно)

        Yields:
            str: HTML каждой страницы
        """
        for page_num in range(start_page, end_page + 1):
            if page_num == 1:
                url = "https://rrr.lt/en/search?cpc=333&prs=1"
            else:
                url = f"https://rrr.lt/en/search?cpc=333&prs=1&page={page_num}"
            print(f"\n[PAGE {page_num}/{end_page}] Загрузка страницы...")

            if self.get_page(url, timeout=3):
                # self.wait_for_page_load(timeout=2)
                html = self.get_page_html()

                # Проверяем, есть ли товары на странице
                if 'add-to-wishlist' not in html and 'data-part-id' not in html:
                    print(f"[INFO] Страница {page_num} пуста, завершаем")
                    break

                yield html
                self.random_delay(0.01, 1.5)
            else:
                print(f"[ERROR] Не удалось загрузить страницу {page_num}")
                break

    def __enter__(self):
        """Поддержка контекстного менеджера"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие при выходе из контекста"""
        self.close()

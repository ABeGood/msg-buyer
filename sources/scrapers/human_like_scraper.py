"""
HumanLikeScraper - скрапер с защитой от обнаружения ботов (Cloudflare и др.)

Реализует:
- Stealth JavaScript (скрытие navigator.webdriver)
- Случайные задержки между действиями
- Ротация User-Agent
- Сохранение cookies между сессиями
- Случайные размеры окна
- Реалистичные HTTP заголовки
"""
import os
import json
import random
import time
from pathlib import Path
from typing import Optional, List, Tuple

from sources.scrapers.base_scraper import BaseScraper


class HumanLikeScraper(BaseScraper):
    """
    Скрапер с человекоподобным поведением для обхода защиты от ботов
    """

    # Популярные User-Agent строки (Edge на Windows)
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.0.0",
        "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]

    # Реалистичные размеры окон (популярные разрешения)
    WINDOW_SIZES = [
        (1920, 1080),
        (1366, 768),
        (1536, 864),
        (1440, 900),
        (1280, 720),
        (1600, 900),
        (1280, 800),
    ]

    # Языки для заголовка Accept-Language
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9,en-US;q=0.8",
        "en-US,en;q=0.9,lt;q=0.8",
        "en,en-US;q=0.9,lt;q=0.8,ru;q=0.7",
    ]

    def __init__(
        self,
        headless: bool = False,
        cookies_file: Optional[str] = None,
        randomize_window: bool = True,
        min_delay: float = 1.0,
        max_delay: float = 3.0
    ):
        """
        Инициализация HumanLikeScraper

        Args:
            headless: Запускать браузер в фоновом режиме
            cookies_file: Путь к файлу для сохранения cookies (None = не сохранять)
            randomize_window: Использовать случайный размер окна
            min_delay: Минимальная задержка между действиями (секунды)
            max_delay: Максимальная задержка между действиями (секунды)
        """
        self.cookies_file = cookies_file
        self.randomize_window = randomize_window
        self.min_delay = min_delay
        self.max_delay = max_delay

        # Выбираем случайный User-Agent для этой сессии
        self.user_agent = random.choice(self.USER_AGENTS)

        # Выбираем случайный язык
        self.accept_language = random.choice(self.ACCEPT_LANGUAGES)

        # Выбираем размер окна
        if randomize_window:
            window_size = random.choice(self.WINDOW_SIZES)
        else:
            window_size = (1920, 1080)

        # Вызываем родительский конструктор
        super().__init__(headless=headless, window_size=window_size)

        # Применяем stealth настройки после инициализации драйвера
        self._apply_stealth()

        # Загружаем сохраненные cookies
        if self.cookies_file:
            self._load_cookies()

    def _init_driver(self):
        """
        Переопределяем инициализацию драйвера с дополнительными настройками
        """
        from selenium import webdriver
        from selenium.webdriver.edge.service import Service
        from selenium.webdriver.edge.options import Options

        try:
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            WEBDRIVER_MANAGER_AVAILABLE = True
        except ImportError:
            WEBDRIVER_MANAGER_AVAILABLE = False

        edge_options = Options()

        # Путь к Edge
        edge_path = self._find_edge_path()
        if edge_path:
            edge_options.binary_location = edge_path
            print(f"[OK] Найден Edge: {edge_path}")

        if self.headless:
            edge_options.add_argument('--headless=new')  # Новый headless режим менее детектируемый

        # Базовые настройки
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')
        edge_options.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')

        # Anti-detection настройки
        edge_options.add_argument('--disable-blink-features=AutomationControlled')
        edge_options.add_argument(f'--user-agent={self.user_agent}')
        edge_options.add_argument(f'--lang={self.accept_language.split(",")[0]}')

        # Дополнительные anti-detection флаги
        edge_options.add_argument('--disable-extensions')
        edge_options.add_argument('--disable-plugins-discovery')
        edge_options.add_argument('--disable-infobars')
        edge_options.add_argument('--ignore-certificate-errors')
        edge_options.add_argument('--disable-popup-blocking')

        # Experimental options
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        edge_options.add_experimental_option('useAutomationExtension', False)

        # Настройки для более реалистичного поведения
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "intl.accept_languages": self.accept_language,
        }
        edge_options.add_experimental_option("prefs", prefs)

        # Инициализация драйвера
        try:
            print("Попытка использовать встроенный EdgeDriver...")
            self.driver = webdriver.Edge(options=edge_options)
            print("[OK] Использован встроенный EdgeDriver")
        except Exception as e:
            print(f"[WARNING] Не удалось использовать встроенный драйвер: {e}")
            if WEBDRIVER_MANAGER_AVAILABLE:
                print("Попытка скачать EdgeDriver через webdriver-manager...")
                try:
                    service = Service(EdgeChromiumDriverManager().install())
                    self.driver = webdriver.Edge(service=service, options=edge_options)
                    print("[OK] EdgeDriver установлен через webdriver-manager")
                except Exception as e2:
                    raise Exception(f"Не удалось инициализировать EdgeDriver. Ошибка: {e2}")
            else:
                raise Exception(f"Не удалось инициализировать EdgeDriver. Ошибка: {e}")

        # Установка размера окна с небольшой случайной вариацией
        width_variation = random.randint(-20, 20)
        height_variation = random.randint(-20, 20)
        self.driver.set_window_size(
            self.window_size[0] + width_variation,
            self.window_size[1] + height_variation
        )

        print(f"[OK] HumanLikeScraper инициализирован (UA: {self.user_agent[:50]}...)")

    def _apply_stealth(self):
        """
        Применение stealth JavaScript для скрытия признаков автоматизации
        """
        stealth_scripts = [
            # Скрытие navigator.webdriver
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """,

            # Добавление chrome объекта (если отсутствует)
            """
            if (!window.chrome) {
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
            }
            """,

            # Скрытие признаков headless режима
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    },
                    {
                        0: {type: "application/pdf", suffixes: "pdf", description: ""},
                        description: "",
                        filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                        length: 1,
                        name: "Chrome PDF Viewer"
                    }
                ]
            });
            """,

            # Скрытие languages
            """
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'lt']
            });
            """,

            # Правильный permissions API
            """
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            """,

            # Скрытие automation-related свойств
            """
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """,

            # Hardware concurrency (количество ядер CPU)
            """
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            """,

            # Device memory
            """
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            """,
        ]

        try:
            # Используем CDP для выполнения скриптов на каждой новой странице
            for script in stealth_scripts:
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': script
                })
            print("[OK] Stealth scripts применены")
        except Exception as e:
            print(f"[WARNING] Не удалось применить некоторые stealth scripts: {e}")
            # Fallback: выполняем скрипты напрямую
            try:
                for script in stealth_scripts:
                    self.driver.execute_script(script)
            except:
                pass

    def random_delay(self, min_sec: Optional[float] = None, max_sec: Optional[float] = None):
        """
        Случайная задержка между действиями

        Args:
            min_sec: Минимальная задержка (по умолчанию self.min_delay)
            max_sec: Максимальная задержка (по умолчанию self.max_delay)
        """
        min_sec = min_sec or self.min_delay
        max_sec = max_sec or self.max_delay
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def human_delay(self):
        """
        Задержка, имитирующая время на чтение страницы человеком
        """
        # Люди обычно тратят 2-8 секунд на просмотр страницы
        delay = random.gauss(5, 2)  # Нормальное распределение со средним 5 и стд. откл. 2
        delay = max(2, min(delay, 10))  # Ограничиваем от 2 до 10 секунд
        time.sleep(delay)

    def get_page(self, url: str, timeout: int = 10, add_delay: bool = True):
        """
        Переход на страницу с человекоподобным поведением

        Args:
            url: URL страницы
            timeout: Таймаут загрузки
            add_delay: Добавить случайную задержку перед загрузкой

        Returns:
            bool: True если страница загружена успешно
        """
        if add_delay:
            self.random_delay(0.5, 2.0)  # Небольшая задержка перед переходом

        result = super().get_page(url, timeout)

        if result:
            # Повторно применяем stealth после загрузки страницы
            self._execute_stealth_on_page()

            if add_delay:
                self.random_delay()  # Задержка после загрузки

        return result

    def _execute_stealth_on_page(self):
        """
        Выполнение stealth скриптов на текущей странице
        """
        try:
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
        except:
            pass

    def _load_cookies(self):
        """
        Загрузка cookies из файла
        """
        if not self.cookies_file:
            return

        cookies_path = Path(self.cookies_file)
        if not cookies_path.exists():
            print(f"[INFO] Файл cookies не найден: {self.cookies_file}")
            return

        try:
            with open(cookies_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)

            # Сначала нужно открыть домен, чтобы установить cookies
            # Это будет сделано при первом get_page
            self._pending_cookies = cookies
            print(f"[OK] Загружено {len(cookies)} cookies из файла")
        except Exception as e:
            print(f"[WARNING] Не удалось загрузить cookies: {e}")

    def _apply_pending_cookies(self, domain: str):
        """
        Применение загруженных cookies для домена
        """
        if not hasattr(self, '_pending_cookies') or not self._pending_cookies:
            return

        try:
            for cookie in self._pending_cookies:
                # Проверяем, что cookie для текущего домена
                cookie_domain = cookie.get('domain', '')
                if domain in cookie_domain or cookie_domain in domain:
                    try:
                        self.driver.add_cookie(cookie)
                    except:
                        pass

            print(f"[OK] Cookies применены для {domain}")
            self._pending_cookies = None
        except Exception as e:
            print(f"[WARNING] Не удалось применить cookies: {e}")

    def save_cookies(self, filepath: Optional[str] = None):
        """
        Сохранение текущих cookies в файл

        Args:
            filepath: Путь к файлу (по умолчанию self.cookies_file)
        """
        filepath = filepath or self.cookies_file
        if not filepath:
            print("[WARNING] Не указан путь для сохранения cookies")
            return

        try:
            cookies = self.driver.get_cookies()

            # Создаем директорию, если не существует
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)

            print(f"[OK] Сохранено {len(cookies)} cookies в {filepath}")
        except Exception as e:
            print(f"[WARNING] Не удалось сохранить cookies: {e}")

    def scroll_page_naturally(self, scroll_pause: float = 0.5):
        """
        Естественная прокрутка страницы вниз
        """
        try:
            # Получаем высоту страницы
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            viewport_height = self.driver.execute_script("return window.innerHeight")

            current_position = 0

            while current_position < total_height:
                # Случайный скролл (200-500 пикселей)
                scroll_amount = random.randint(200, 500)
                current_position += scroll_amount

                self.driver.execute_script(f"window.scrollTo(0, {current_position});")

                # Случайная пауза между скроллами
                time.sleep(random.uniform(scroll_pause * 0.5, scroll_pause * 1.5))

                # Обновляем высоту (страница может подгрузиться)
                total_height = self.driver.execute_script("return document.body.scrollHeight")
        except Exception as e:
            print(f"[WARNING] Ошибка при скролле: {e}")

    def move_mouse_randomly(self):
        """
        Имитация случайного движения мыши (если поддерживается)
        """
        try:
            from selenium.webdriver.common.action_chains import ActionChains

            actions = ActionChains(self.driver)

            # Получаем размеры окна
            width = self.driver.execute_script("return window.innerWidth")
            height = self.driver.execute_script("return window.innerHeight")

            # Делаем несколько случайных движений
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, width - 100)
                y = random.randint(100, height - 100)

                actions.move_by_offset(x // 10, y // 10)
                actions.pause(random.uniform(0.1, 0.3))

            actions.perform()
        except Exception as e:
            # Движение мыши может не поддерживаться в headless режиме
            pass

    def close(self):
        """
        Закрытие браузера с сохранением cookies
        """
        if self.cookies_file and self.driver:
            self.save_cookies()

        super().close()

"""
Базовый класс для работы с Selenium WebDriver
"""
import os
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
try:
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False


class BaseScraper:
    """
    Базовый класс для скрапинга с использованием Selenium
    
    Этот класс предоставляет:
    - Инициализацию WebDriver с автоматической установкой драйвера
    - Настройки браузера (headless режим, размер окна и т.д.)
    - Методы для ожидания загрузки элементов
    - Безопасное закрытие браузера
    """
    
    def __init__(self, headless: bool = False, window_size: tuple = (1920, 1080)):
        """
        Инициализация WebDriver
        
        Args:
            headless: Запускать браузер в фоновом режиме (без GUI)
            window_size: Размер окна браузера (ширина, высота)
        """
        self.driver = None
        self.headless = headless
        self.window_size = window_size
        self._init_driver()
    
    def _find_edge_path(self):
        """
        Поиск пути к Edge в стандартных местах Windows
        """
        possible_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def _init_driver(self):
        """
        Инициализация Edge WebDriver с настройками
        Edge обычно уже установлен в Windows 10/11
        """
        # Настройки Edge
        edge_options = Options()
        
        # Указываем путь к Edge, если найден
        edge_path = self._find_edge_path()
        if edge_path:
            edge_options.binary_location = edge_path
            print(f"[OK] Найден Edge: {edge_path}")
        else:
            print("[WARNING] Edge не найден в стандартных местах, используем системный путь")
        
        if self.headless:
            edge_options.add_argument('--headless')
        
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')
        edge_options.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        edge_options.add_argument('--disable-blink-features=AutomationControlled')
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option('useAutomationExtension', False)
        
        # Попытка использовать встроенный драйвер Edge (Selenium 4.6+)
        # Если не получится, попробуем через webdriver-manager
        try:
            print("Попытка использовать встроенный EdgeDriver...")
            # В Selenium 4.6+ можно использовать Edge без указания Service
            # Selenium автоматически найдет драйвер
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
                raise Exception(f"Не удалось инициализировать EdgeDriver. Установите webdriver-manager или обновите Selenium. Ошибка: {e}")
        
        # Установка размера окна
        self.driver.set_window_size(*self.window_size)
        print("[OK] Edge WebDriver инициализирован")
    
    def get_page(self, url: str, timeout: int = 10):
        """
        Переход на указанный URL и ожидание загрузки страницы
        
        Args:
            url: URL страницы для загрузки
            timeout: Максимальное время ожидания в секундах
            
        Returns:
            bool: True если страница загружена успешно, False в противном случае
        """
        try:
            print(f"Переход на страницу: {url}")
            self.driver.get(url)
            
            # Ожидание загрузки страницы (проверка готовности DOM)
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            
            print("Страница успешно загружена")
            return True
            
        except TimeoutException:
            print(f"Таймаут при загрузке страницы: {url}")
            return False
        except Exception as e:
            print(f"Ошибка при загрузке страницы: {e}")
            return False
    
    def wait_for_element(self, by, value, timeout: int = 10):
        """
        Ожидание появления элемента на странице
        
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
    
    def get_current_url(self) -> str:
        """Получить текущий URL"""
        return self.driver.current_url
    
    def get_page_title(self) -> str:
        """Получить заголовок страницы"""
        return self.driver.title
    
    def get_page_html(self) -> str:
        """
        Получить HTML код текущей страницы
        
        Returns:
            str: HTML код страницы
        """
        if self.driver:
            return self.driver.page_source
        return ""
    
    def close(self):
        """Закрыть браузер"""
        if self.driver:
            self.driver.quit()
            print("Браузер закрыт")
    
    def __enter__(self):
        """Поддержка контекстного менеджера (with statement)"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие браузера при выходе из контекста"""
        self.close()


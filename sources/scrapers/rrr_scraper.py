"""
Специализированный скрапер для сайта rrr.lt
"""
from sources.scrapers.base_scraper import BaseScraper


class RRRScraper(BaseScraper):
    """
    Скрапер для работы с сайтом rrr.lt
    
    Наследуется от BaseScraper и добавляет специфичные методы
    для работы с разделом Steering Rack
    """
    
    STEERING_RACK_URL = "https://rrr.lt/en/parts-list/front-axle/driving-mechanism/steering-rack"
    
    def __init__(self, headless: bool = False):
        """
        Инициализация скрапера для rrr.lt
        
        Args:
            headless: Запускать браузер в фоновом режиме
        """
        super().__init__(headless=headless)
    
    def open_steering_rack_page(self) -> bool:
        """
        Открыть страницу со списком steering rack
        
        Returns:
            bool: True если страница успешно загружена
        """
        return self.get_page(self.STEERING_RACK_URL)
    
    def is_page_loaded(self) -> bool:
        """
        Проверить, что страница полностью загружена
        
        Returns:
            bool: True если страница загружена
        """
        # Можно добавить проверку специфичных элементов страницы
        # Например, наличие заголовка или списка товаров
        return self.driver.execute_script('return document.readyState') == 'complete'


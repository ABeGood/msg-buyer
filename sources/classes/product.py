"""
Модель данных для товара
"""
import re
from typing import Optional, Dict, Any, List, Tuple


class Product:
    """
    Универсальная модель данных для товара
    
    Содержит общие поля для всех товаров и специфичные данные
    для детальной информации о товаре
    """
    
    def __init__(
        self,
        part_id: Optional[str] = None,
        code: Optional[str] = None,
        price: Optional[float] = None,
        url: Optional[str] = None,
        source_site: Optional[str] = None,
        category: Optional[str] = None,
        item_description: Optional[Dict[str, Any]] = None,
        car_details: Optional[Dict[str, Any]] = None,
        seller_email: Optional[str] = None,
        seller_phone: Optional[str] = None,
        images: Optional[List[str]] = None,
        seller_comment: Optional[str] = None
    ):
        """
        Инициализация товара

        Args:
            part_id: Уникальный идентификатор товара
            code: Код товара (SKU)
            price: Цена
            url: Ссылка на товар
            source_site: Источник (rrr.lt, другой сайт)
            category: Категория товара
            item_description: Описание товара (manufacturer_code, oem_code, other_codes, condition)
            car_details: Детали автомобиля (make, series, model, year, engine_capacity, gearbox_code, mileage, vin_code, ...)
            seller_email: Email продавца (используется как ключ для связи с таблицей Sellers)
            seller_phone: Телефон продавца
            images: Список URL изображений товара
            seller_comment: Комментарий продавца о конкретном товаре (может отсутствовать)
        """
        self.part_id = part_id
        self.code = code
        self.price = price
        self.url = url
        self.source_site = source_site or 'rrr.lt'
        self.category = category or 'steering-rack'
        self.item_description = item_description or {}
        self.car_details = car_details or {}
        self.seller_email = seller_email
        self.seller_phone = seller_phone
        self.images = images or []
        self.seller_comment = seller_comment
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование в словарь для сохранения в БД

        Returns:
            Словарь с данными товара
        """
        return {
            'part_id': self.part_id,
            'code': self.code,
            'price': self.price,
            'url': self.url,
            'source_site': self.source_site,
            'category': self.category,
            'item_description': self.item_description,
            'car_details': self.car_details,
            'seller_email': self.seller_email,
            'seller_phone': self.seller_phone,
            'images': self.images,
            'seller_comment': self.seller_comment
        }
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Валидация данных товара перед сохранением в БД
        
        Returns:
            Кортеж (is_valid, error_message)
            is_valid: True если данные валидны, False в противном случае
            error_message: Сообщение об ошибке или None
        """
        if not self.part_id:
            return False, "part_id обязателен для сохранения"
        
        if not self.code:
            return False, "code обязателен для сохранения"
        
        if self.price is not None and self.price < 0:
            return False, "price не может быть отрицательным"
        
        if self.url:
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            if not url_pattern.match(self.url):
                return False, f"url имеет неверный формат: {self.url}"
        
        if self.seller_email:
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not email_pattern.match(self.seller_email):
                return False, f"seller_email имеет неверный формат: {self.seller_email}"
        
        return True, None
    
    def __repr__(self) -> str:
        return f"Product(part_id={self.part_id}, code={self.code}, price={self.price})"


"""
Модель данных для товара
"""
from typing import Optional, Dict, Any, List


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
        seller_info: Optional[Dict[str, Any]] = None,
        images: Optional[List[str]] = None
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
            seller_info: Информация о продавце (name, country, rating, stars)
            images: Список URL изображений товара
        """
        self.part_id = part_id
        self.code = code
        self.price = price
        self.url = url
        self.source_site = source_site or 'rrr.lt'
        self.category = category or 'steering-rack'
        self.item_description = item_description or {}
        self.car_details = car_details or {}
        self.seller_info = seller_info or {}
        self.images = images or []
    
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
            'seller_info': self.seller_info,
            'images': self.images
        }
    
    def __repr__(self) -> str:
        return f"Product(part_id={self.part_id}, code={self.code}, price={self.price})"


"""
SQLAlchemy модели для базы данных
"""
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, Index, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

Base = declarative_base()


class ProductModel(Base):
    """
    SQLAlchemy модель для таблицы products
    
    Соответствует структуре класса Product из sources.classes.product
    """
    __tablename__ = 'products'
    
    # Основные поля
    id = Column(Integer, primary_key=True, autoincrement=True)
    part_id = Column(String(50), unique=True, nullable=False)  # Индекс создается через __table_args__
    code = Column(String(50), nullable=False)  # Индекс создается через __table_args__
    price = Column(Numeric(10, 2), nullable=True)
    url = Column(Text, nullable=True)
    source_site = Column(String(50), default='rrr.lt', nullable=False)
    category = Column(String(100), default='steering-rack', nullable=False)
    
    # JSON поля (JSONB в PostgreSQL для лучшей производительности)
    item_description = Column(JSONB, nullable=True)  # {manufacturer_code, oem_code, other_codes, condition}
    car_details = Column(JSONB, nullable=True)       # {make, series, model, year, engine_capacity, gearbox_code, mileage, vin_code, ...}
    seller_email = Column(String(255), nullable=True)  # Email продавца (FK к таблице Sellers)
    images = Column(JSONB, nullable=True)            # [url1, url2, ...] - массив строк
    available = Column(Boolean, nullable=True)       # Заглушка для будущей логики доступности товара
    
    # Метаданные
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Индексы
    __table_args__ = (
        Index('idx_products_part_id', 'part_id'),
        Index('idx_products_code', 'code'),
        Index('idx_products_category', 'category'),
        Index('idx_products_source_site', 'source_site'),
        Index('idx_products_seller_email', 'seller_email'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование в словарь
        
        Returns:
            Словарь с данными товара
        """
        return {
            'id': self.id,
            'part_id': self.part_id,
            'code': self.code,
            'price': float(self.price) if self.price else None,
            'url': self.url,
            'source_site': self.source_site,
            'category': self.category,
            'item_description': self.item_description or {},
            'car_details': self.car_details or {},
            'seller_email': self.seller_email,
            'images': self.images or [],
            'available': self.available,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self) -> str:
        return f"ProductModel(part_id={self.part_id}, code={self.code}, price={self.price})"


class SellerModel(Base):
    """
    SQLAlchemy модель для таблицы sellers
    
    Хранит информацию о продавцах, извлеченную из скриптов на страницах товаров.
    Каждое поле из seller_data (кроме email) хранится в отдельной колонке.
    Сложные структуры (workingHours, country, currentHolidays) хранятся как JSONB.
    """
    __tablename__ = 'sellers'
    
    # PRIMARY KEY
    email = Column(String(255), primary_key=True, nullable=False, unique=True)
    
    # Простые поля из seller_data
    address = Column(Text, nullable=True)
    company_code = Column(String(50), nullable=True)  # companyCode
    title = Column(String(255), nullable=True)
    seller_id = Column(Integer, nullable=True)  # id из seller_data (переименован, чтобы не конфликтовало с id таблицы)
    is_top_seller = Column(Boolean, nullable=True)  # isTopSeller
    suspended = Column(Boolean, nullable=True)
    name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    rating = Column(Integer, nullable=True)
    short_name = Column(String(50), nullable=True)  # shortName
    vat_code = Column(String(50), nullable=True)  # vatCode
    is_vat_enabled = Column(Boolean, nullable=True)  # isVatEnabled
    
    # Сложные структуры как JSONB
    working_hours = Column(JSONB, nullable=True)  # workingHours - массив объектов
    country = Column(JSONB, nullable=True)  # объект с IsoAlpha2 и name
    current_holidays = Column(JSONB, nullable=True)  # currentHolidays - может быть null или объект
    
    # Комментарий продавца (извлекается из HTML)
    seller_comment = Column(Text, nullable=True)  # Комментарий продавца (может отсутствовать)
    
    # SKU товаров продавца (заглушка под будущую логику)
    sellers_sku = Column(JSONB, nullable=True)  # Массив SKU товаров, доступных у продавца
    
    # Метаданные (в конце таблицы)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование в словарь
        
        Returns:
            Словарь с данными продавца (в формате, аналогичном seller_data)
        """
        return {
            'email': self.email,
            'address': self.address,
            'companyCode': self.company_code,
            'title': self.title,
            'id': self.seller_id,
            'isTopSeller': self.is_top_seller,
            'suspended': self.suspended,
            'name': self.name,
            'phone': self.phone,
            'rating': self.rating,
            'shortName': self.short_name,
            'vatCode': self.vat_code,
            'isVatEnabled': self.is_vat_enabled,
            'workingHours': self.working_hours or [],
            'country': self.country or {},
            'currentHolidays': self.current_holidays,
            'sellerComment': self.seller_comment,
            'sellersSku': self.sellers_sku or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self) -> str:
        return f"SellerModel(email={self.email}, name={self.name})"


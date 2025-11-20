"""
SQLAlchemy модели для базы данных
"""
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
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
    seller_info = Column(JSONB, nullable=True)        # {name, country, rating, stars}
    images = Column(JSONB, nullable=True)            # [url1, url2, ...] - массив строк
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Индексы
    __table_args__ = (
        Index('idx_products_part_id', 'part_id'),
        Index('idx_products_code', 'code'),
        Index('idx_products_category', 'category'),
        Index('idx_products_source_site', 'source_site'),
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
            'seller_info': self.seller_info or {},
            'images': self.images or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self) -> str:
        return f"ProductModel(part_id={self.part_id}, code={self.code}, price={self.price})"


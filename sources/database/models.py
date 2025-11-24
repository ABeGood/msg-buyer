"""
SQLAlchemy модели для базы данных
"""
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, Index, Boolean, ForeignKey
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
    seller_comment = Column(Text, nullable=True)      # Комментарий продавца о конкретном товаре (может отсутствовать)
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
            'seller_comment': self.seller_comment,
            'available': self.available,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self) -> str:
        return f"ProductModel(part_id={self.part_id}, code={self.code}, price={self.price})"


class UserModel(Base):
    """
    SQLAlchemy модель для таблицы users

    Пользователи, авторизованные через Google OAuth.
    Требуют одобрения админа для получения доступа.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    picture = Column(Text, nullable=True)  # URL аватарки Google
    google_id = Column(String(255), unique=True, nullable=False)

    # Статус одобрения
    is_approved = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Метаданные
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    approved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_google_id', 'google_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'picture': self.picture,
            'is_approved': self.is_approved,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
        }

    def __repr__(self) -> str:
        return f"UserModel(email={self.email}, is_approved={self.is_approved})"


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
            'sellersSku': self.sellers_sku or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self) -> str:
        return f"SellerModel(email={self.email}, name={self.name})"


class CompareResultModel(Base):
    """
    SQLAlchemy модель для таблицы compare

    Хранит результаты сравнения продуктов с каталогами (eur/gur)
    """
    __tablename__ = 'compare'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Источник каталога
    catalog = Column(String(10), nullable=False)  # 'eur' or 'gur'

    # Данные из БД продуктов
    db_part_id = Column(String(50), nullable=False)
    db_code = Column(String(50), nullable=True)
    db_price = Column(Numeric(10, 2), nullable=True)
    db_url = Column(Text, nullable=True)
    db_source_site = Column(String(50), nullable=True)
    db_category = Column(String(100), nullable=True)
    db_oem_code = Column(String(100), nullable=True)
    db_other_codes = Column(Text, nullable=True)
    db_manufacturer_code = Column(String(100), nullable=True)

    # Данные из каталога
    catalog_oes_numbers = Column(Text, nullable=True)
    catalog_price_eur = Column(Numeric(10, 2), nullable=True)
    catalog_segments_names = Column(String(255), nullable=True)
    catalog_data = Column(JSONB, nullable=True)  # Полные данные строки каталога

    # Результат сравнения
    matched_by = Column(String(50), nullable=True)  # oem_code, manufacturer_code, other_codes
    matched_value = Column(String(100), nullable=True)
    price_classification = Column(String(20), nullable=True)  # OK, HIGH, NA

    # Метаданные
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index('idx_compare_catalog', 'catalog'),
        Index('idx_compare_db_part_id', 'db_part_id'),
        Index('idx_compare_price_classification', 'price_classification'),
        Index('idx_compare_created_at', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'catalog': self.catalog,
            'db_part_id': self.db_part_id,
            'db_code': self.db_code,
            'db_price': float(self.db_price) if self.db_price else None,
            'db_url': self.db_url,
            'db_source_site': self.db_source_site,
            'db_category': self.db_category,
            'db_oem_code': self.db_oem_code,
            'db_other_codes': self.db_other_codes,
            'db_manufacturer_code': self.db_manufacturer_code,
            'catalog_oes_numbers': self.catalog_oes_numbers,
            'catalog_price_eur': float(self.catalog_price_eur) if self.catalog_price_eur else None,
            'catalog_segments_names': self.catalog_segments_names,
            'catalog_data': self.catalog_data,
            'matched_by': self.matched_by,
            'matched_value': self.matched_value,
            'price_classification': self.price_classification,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"CompareResultModel(catalog={self.catalog}, db_part_id={self.db_part_id}, classification={self.price_classification})"


class EmailLogModel(Base):
    """
    SQLAlchemy модель для таблицы email_logs
    
    Хранит историю отправленных email сообщений продавцам
    """
    __tablename__ = 'email_logs'
    
    # PRIMARY KEY
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Основные поля
    seller_email = Column(String(255), nullable=False)  # Email продавца
    product_part_id = Column(String(50), nullable=True)  # ID товара (может быть NULL для bulk запросов)
    subject = Column(String(500), nullable=False)  # Тема письма
    body = Column(Text, nullable=False)  # Тело письма
    
    # Статус и метаданные
    status = Column(String(50), nullable=False, default='sent')  # sent, failed, bounced
    error_message = Column(Text, nullable=True)  # Сообщение об ошибке (если status=failed)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    response_received = Column(Boolean, default=False, nullable=False)  # Получен ли ответ
    response_at = Column(DateTime, nullable=True)  # Когда получен ответ
    
    # Индексы
    __table_args__ = (
        Index('idx_email_logs_seller_email', 'seller_email'),
        Index('idx_email_logs_product_part_id', 'product_part_id'),
        Index('idx_email_logs_status', 'status'),
        Index('idx_email_logs_sent_at', 'sent_at'),
        Index('idx_email_logs_response_received', 'response_received'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование в словарь
        
        Returns:
            Словарь с данными email лога
        """
        return {
            'id': self.id,
            'seller_email': self.seller_email,
            'product_part_id': self.product_part_id,
            'subject': self.subject,
            'body': self.body,
            'status': self.status,
            'error_message': self.error_message,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'response_received': self.response_received,
            'response_at': self.response_at.isoformat() if self.response_at else None
        }
    
    def __repr__(self) -> str:
        return f"EmailLogModel(id={self.id}, seller_email={self.seller_email}, status={self.status})"


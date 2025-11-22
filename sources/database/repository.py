"""
Репозиторий для работы с товарами в базе данных
"""
import json
import hashlib
from typing import Optional, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sources.database.models import ProductModel, SellerModel, Base
from sources.classes.product import Product
from sources.utils.logger import get_logger

logger = get_logger("repository")


class ProductRepository:
    """
    Репозиторий для работы с товарами в БД
    
    Предоставляет методы для сохранения и удаления товаров
    """
    
    def __init__(self, database_url: str):
        """
        Инициализация репозитория
        
        Args:
            database_url: URL подключения к БД (например: postgresql://user:pass@host:port/dbname)
        """
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
    
    def create_tables(self):
        """
        Создание таблиц в БД (если их нет)
        """
        Base.metadata.create_all(bind=self.engine)
        logger.info("Таблицы созданы/проверены")
    
    def save(self, product: Product) -> bool:
        """
        Сохранение товара в БД
        
        Если товар с таким part_id уже существует, он будет обновлен
        
        Args:
            product: Объект Product для сохранения
            
        Returns:
            True если успешно, False в противном случае
        """
        # Валидация данных
        is_valid, error_message = product.validate()
        if not is_valid:
            logger.error(f"Ошибка валидации товара: {error_message}")
            return False
        
        session: Session = self.SessionLocal()
        try:
            # Проверяем, существует ли товар
            existing_product = session.query(ProductModel).filter_by(part_id=product.part_id).first()
            
            if existing_product:
                # Обновляем существующий товар
                existing_product.code = product.code
                existing_product.price = product.price
                existing_product.url = product.url
                existing_product.source_site = product.source_site
                existing_product.category = product.category
                existing_product.item_description = product.item_description
                existing_product.car_details = product.car_details
                existing_product.seller_email = product.seller_email
                existing_product.images = product.images
                # available остается без изменений (заглушка)
                # updated_at обновится автоматически через onupdate
                
                session.commit()
                logger.info(f"Товар {product.part_id} обновлен в БД")
                return True
            else:
                # Создаем новый товар
                db_product = ProductModel(
                    part_id=product.part_id,
                    code=product.code,
                    price=product.price,
                    url=product.url,
                    source_site=product.source_site,
                    category=product.category,
                    item_description=product.item_description,
                    car_details=product.car_details,
                    seller_email=product.seller_email,
                    images=product.images,
                    available=None  # Заглушка
                )
                
                session.add(db_product)
                session.commit()
                logger.info(f"Товар {product.part_id} сохранен в БД")
                return True
                
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при сохранении товара {product.part_id}: {e}", exc_info=True)
            return False
        finally:
            session.close()
    
    def delete_by_part_id(self, part_id: str) -> bool:
        """
        Удаление товара по part_id
        
        Args:
            part_id: Уникальный идентификатор товара
            
        Returns:
            True если товар удален, False в противном случае
        """
        session: Session = self.SessionLocal()
        try:
            product = session.query(ProductModel).filter_by(part_id=part_id).first()
            
            if product:
                session.delete(product)
                session.commit()
                logger.info(f"Товар {part_id} удален из БД")
                return True
            else:
                logger.warning(f"Товар {part_id} не найден в БД")
                return False
                
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при удалении товара {part_id}: {e}", exc_info=True)
            return False
        finally:
            session.close()
    
    def delete_by_code(self, code: str) -> bool:
        """
        Удаление товара по code (SKU)
        
        Args:
            code: Код товара (SKU)
            
        Returns:
            True если товар удален, False в противном случае
        """
        session: Session = self.SessionLocal()
        try:
            product = session.query(ProductModel).filter_by(code=code).first()
            
            if product:
                part_id = product.part_id
                session.delete(product)
                session.commit()
                logger.info(f"Товар {code} (part_id={part_id}) удален из БД")
                return True
            else:
                logger.warning(f"Товар {code} не найден в БД")
                return False
                
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при удалении товара {code}: {e}", exc_info=True)
            return False
        finally:
            session.close()
    
    def find_by_part_id(self, part_id: str) -> Optional[Product]:
        """
        Поиск товара по part_id
        
        Args:
            part_id: Уникальный идентификатор товара
            
        Returns:
            Объект Product или None
        """
        session: Session = self.SessionLocal()
        try:
            db_product = session.query(ProductModel).filter_by(part_id=part_id).first()
            
            if db_product:
                return self._db_to_product(db_product)
            return None
                
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске товара {part_id}: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def find_by_code(self, code: str) -> Optional[Product]:
        """
        Поиск товара по code
        
        Args:
            code: Код товара (SKU)
            
        Returns:
            Объект Product или None
        """
        session: Session = self.SessionLocal()
        try:
            db_product = session.query(ProductModel).filter_by(code=code).first()
            
            if db_product:
                return self._db_to_product(db_product)
            return None
                
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске товара {code}: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def _db_to_product(self, db_product: ProductModel) -> Product:
        """
        Преобразование ProductModel в Product
        
        Args:
            db_product: Объект ProductModel из БД
            
        Returns:
            Объект Product
        """
        # Безопасное преобразование price
        price_value = None
        if db_product.price is not None:
            try:
                if isinstance(db_product.price, (int, float)):
                    price_value = float(db_product.price)
                else:
                    price_value = float(str(db_product.price))
            except (ValueError, TypeError):
                price_value = None
        
        return Product(
            part_id=db_product.part_id,
            code=db_product.code,
            price=price_value,
            url=db_product.url,
            source_site=db_product.source_site,
            category=db_product.category,
            item_description=db_product.item_description or {},
            car_details=db_product.car_details or {},
            seller_email=db_product.seller_email,
            images=db_product.images or []
        )
    
    def save_seller(self, email: str, seller_data: Dict[str, Any], seller_comment: Optional[str] = None) -> bool:
        """
        Сохранение продавца в БД
        
        Если продавец с таким email уже существует, проверяет, изменились ли данные.
        Если данные идентичны - пропускает обновление.
        Если данные отличаются - обновляет существующего продавца.
        Извлекает поля из seller_data и сохраняет их в отдельные колонки.
        
        Args:
            email: Email продавца (PRIMARY KEY)
            seller_data: Словарь со всеми данными о продавце (извлеченными из скрипта)
            seller_comment: Комментарий продавца (извлекается из HTML, может быть None)
            
        Returns:
            True если успешно, False в противном случае
        """
        if not email:
            logger.error("email обязателен для сохранения продавца")
            return False
        
        session: Session = self.SessionLocal()
        try:
            # Извлекаем поля из seller_data
            # Простые поля
            address = seller_data.get('address')
            company_code = seller_data.get('companyCode')
            title = seller_data.get('title')
            seller_id = seller_data.get('id')
            is_top_seller = seller_data.get('isTopSeller')
            suspended = seller_data.get('suspended')
            name = seller_data.get('name')
            phone = seller_data.get('phone')
            rating = seller_data.get('rating')
            short_name = seller_data.get('shortName')
            vat_code = seller_data.get('vatCode')
            is_vat_enabled = seller_data.get('isVatEnabled')
            
            # Сложные структуры (JSONB)
            working_hours = seller_data.get('workingHours')
            country = seller_data.get('country')
            current_holidays = seller_data.get('currentHolidays')
            
            # Проверяем, существует ли продавец
            existing_seller = session.query(SellerModel).filter_by(email=email).first()
            
            if existing_seller:
                # Оптимизированное сравнение данных через хеширование JSONB полей
                def get_jsonb_hash(value: Any) -> Optional[str]:
                    """Получение хеша JSONB значения для быстрого сравнения"""
                    if value is None:
                        return None
                    try:
                        json_str = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
                        return hashlib.md5(json_str.encode('utf-8')).hexdigest()
                    except (TypeError, ValueError):
                        return str(value)
                
                # Сравниваем простые поля
                simple_fields_changed = (
                    existing_seller.address != address or
                    existing_seller.company_code != company_code or
                    existing_seller.title != title or
                    existing_seller.seller_id != seller_id or
                    existing_seller.is_top_seller != is_top_seller or
                    existing_seller.suspended != suspended or
                    existing_seller.name != name or
                    existing_seller.phone != phone or
                    existing_seller.rating != rating or
                    existing_seller.short_name != short_name or
                    existing_seller.vat_code != vat_code or
                    existing_seller.is_vat_enabled != is_vat_enabled or
                    existing_seller.seller_comment != seller_comment
                )
                
                # Сравниваем JSONB поля через хеши
                jsonb_fields_changed = (
                    get_jsonb_hash(existing_seller.working_hours) != get_jsonb_hash(working_hours) or
                    get_jsonb_hash(existing_seller.country) != get_jsonb_hash(country) or
                    get_jsonb_hash(existing_seller.current_holidays) != get_jsonb_hash(current_holidays)
                )
                
                data_changed = simple_fields_changed or jsonb_fields_changed
                
                if not data_changed:
                    # Данные идентичны - пропускаем обновление
                    logger.debug(f"Данные продавца {email} не изменились, обновление не требуется")
                    return True
                
                # Данные изменились - обновляем существующего продавца
                existing_seller.address = address
                existing_seller.company_code = company_code
                existing_seller.title = title
                existing_seller.seller_id = seller_id
                existing_seller.is_top_seller = is_top_seller
                existing_seller.suspended = suspended
                existing_seller.name = name
                existing_seller.phone = phone
                existing_seller.rating = rating
                existing_seller.short_name = short_name
                existing_seller.vat_code = vat_code
                existing_seller.is_vat_enabled = is_vat_enabled
                existing_seller.working_hours = working_hours
                existing_seller.country = country
                existing_seller.current_holidays = current_holidays
                existing_seller.seller_comment = seller_comment
                # updated_at обновится автоматически через onupdate
                
                session.commit()
                logger.info(f"Продавец {email} обновлен в БД (данные изменились)")
                return True
            else:
                # Создаем нового продавца
                db_seller = SellerModel(
                    email=email,
                    address=address,
                    company_code=company_code,
                    title=title,
                    seller_id=seller_id,
                    is_top_seller=is_top_seller,
                    suspended=suspended,
                    name=name,
                    phone=phone,
                    rating=rating,
                    short_name=short_name,
                    vat_code=vat_code,
                    is_vat_enabled=is_vat_enabled,
                    working_hours=working_hours,
                    country=country,
                    current_holidays=current_holidays,
                    seller_comment=seller_comment
                )
                
                session.add(db_seller)
                session.commit()
                logger.info(f"Продавец {email} сохранен в БД")
                return True
                
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при сохранении продавца {email}: {e}", exc_info=True)
            return False
        finally:
            session.close()
    
    def find_seller_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Поиск продавца по email
        
        Args:
            email: Email продавца
            
        Returns:
            Словарь с данными продавца (в формате, аналогичном seller_data) или None
        """
        if not email:
            return None
        
        session: Session = self.SessionLocal()
        try:
            db_seller = session.query(SellerModel).filter_by(email=email).first()
            
            if db_seller:
                return db_seller.to_dict()
            return None
                
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске продавца {email}: {e}", exc_info=True)
            return None
        finally:
            session.close()
    
    def save_product_with_seller(
        self, 
        product: Product, 
        seller_data: Optional[Dict[str, Any]] = None, 
        seller_comment: Optional[str] = None
    ) -> bool:
        """
        Сохранение товара и продавца в одной транзакции
        
        Гарантирует атомарность операции: либо сохраняются оба, либо ни один.
        
        Args:
            product: Объект Product для сохранения
            seller_data: Данные продавца (если есть)
            seller_comment: Комментарий продавца (если есть)
            
        Returns:
            True если успешно, False в противном случае
        """
        # Валидация товара
        is_valid, error_message = product.validate()
        if not is_valid:
            logger.error(f"Ошибка валидации товара: {error_message}")
            return False
        
        session: Session = self.SessionLocal()
        try:
            # Сохраняем продавца, если есть данные
            if product.seller_email and seller_data:
                # Извлекаем поля из seller_data
                address = seller_data.get('address')
                company_code = seller_data.get('companyCode')
                title = seller_data.get('title')
                seller_id = seller_data.get('id')
                is_top_seller = seller_data.get('isTopSeller')
                suspended = seller_data.get('suspended')
                name = seller_data.get('name')
                phone = seller_data.get('phone')
                rating = seller_data.get('rating')
                short_name = seller_data.get('shortName')
                vat_code = seller_data.get('vatCode')
                is_vat_enabled = seller_data.get('isVatEnabled')
                working_hours = seller_data.get('workingHours')
                country = seller_data.get('country')
                current_holidays = seller_data.get('currentHolidays')
                
                # Проверяем, существует ли продавец
                existing_seller = session.query(SellerModel).filter_by(email=product.seller_email).first()
                
                if existing_seller:
                    # Обновляем существующего продавца
                    existing_seller.address = address
                    existing_seller.company_code = company_code
                    existing_seller.title = title
                    existing_seller.seller_id = seller_id
                    existing_seller.is_top_seller = is_top_seller
                    existing_seller.suspended = suspended
                    existing_seller.name = name
                    existing_seller.phone = phone
                    existing_seller.rating = rating
                    existing_seller.short_name = short_name
                    existing_seller.vat_code = vat_code
                    existing_seller.is_vat_enabled = is_vat_enabled
                    existing_seller.working_hours = working_hours
                    existing_seller.country = country
                    existing_seller.current_holidays = current_holidays
                    existing_seller.seller_comment = seller_comment
                else:
                    # Создаем нового продавца
                    db_seller = SellerModel(
                        email=product.seller_email,
                        address=address,
                        company_code=company_code,
                        title=title,
                        seller_id=seller_id,
                        is_top_seller=is_top_seller,
                        suspended=suspended,
                        name=name,
                        phone=phone,
                        rating=rating,
                        short_name=short_name,
                        vat_code=vat_code,
                        is_vat_enabled=is_vat_enabled,
                        working_hours=working_hours,
                        country=country,
                        current_holidays=current_holidays,
                        seller_comment=seller_comment
                    )
                    session.add(db_seller)
            
            # Сохраняем товар
            existing_product = session.query(ProductModel).filter_by(part_id=product.part_id).first()
            
            if existing_product:
                # Обновляем существующий товар
                existing_product.code = product.code
                existing_product.price = product.price
                existing_product.url = product.url
                existing_product.source_site = product.source_site
                existing_product.category = product.category
                existing_product.item_description = product.item_description
                existing_product.car_details = product.car_details
                existing_product.seller_email = product.seller_email
                existing_product.images = product.images
            else:
                # Создаем новый товар
                db_product = ProductModel(
                    part_id=product.part_id,
                    code=product.code,
                    price=product.price,
                    url=product.url,
                    source_site=product.source_site,
                    category=product.category,
                    item_description=product.item_description,
                    car_details=product.car_details,
                    seller_email=product.seller_email,
                    images=product.images,
                    available=None
                )
                session.add(db_product)
            
            # Коммитим все изменения в одной транзакции
            session.commit()
            logger.info(f"Товар {product.part_id} и продавец сохранены в БД (транзакция)")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при сохранении товара и продавца: {e}", exc_info=True)
            return False
        finally:
            session.close()


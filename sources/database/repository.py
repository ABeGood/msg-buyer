"""
Репозиторий для работы с товарами в базе данных
"""
import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sources.database.models import ProductModel, SellerModel, UserModel, CompareResultModel, ConversationModel, MessageModel, ConversationClassificationModel, CatalogMatchModel, UnmatchedProductModel, Base
from sources.classes.product import Product
from sources.utils.logger import get_logger
from sources.utils.formatter import clean_reply_to_text

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

    def drop_table(self, table_name: str) -> bool:
        """
        Удаление таблицы по имени

        Args:
            table_name: Имя таблицы для удаления

        Returns:
            True если таблица удалена, False в противном случае
        """
        from sqlalchemy import text

        session: Session = self.SessionLocal()
        try:
            session.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
            session.commit()
            logger.info(f"Таблица {table_name} удалена")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при удалении таблицы {table_name}: {e}", exc_info=True)
            return False
        finally:
            session.close()

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
                existing_product.seller_phone = product.seller_phone
                existing_product.images = product.images
                existing_product.seller_comment = product.seller_comment
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
                    seller_phone=product.seller_phone,
                    images=product.images,
                    seller_comment=product.seller_comment,
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
    
    def get_all(self, limit: Optional[int] = None) -> list[Product]:
        """
        Получение всех товаров из БД

        Args:
            limit: Максимальное количество товаров (опционально)

        Returns:
            Список объектов Product
        """
        session: Session = self.SessionLocal()
        try:
            query = session.query(ProductModel)
            if limit:
                query = query.limit(limit)
            db_products = query.all()
            return [self._db_to_product(p) for p in db_products]
        except SQLAlchemyError as e:
            print(f"[ERROR] Ошибка при получении товаров: {e}")
            return []
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
            images=db_product.images or [],
            seller_comment=db_product.seller_comment
        )
    
    def save_seller(self, email: str, seller_data: Dict[str, Any]) -> bool:
        """
        Сохранение продавца в БД
        
        Если продавец с таким email уже существует, проверяет, изменились ли данные.
        Если данные идентичны - пропускает обновление.
        Если данные отличаются - обновляет существующего продавца.
        Извлекает поля из seller_data и сохраняет их в отдельные колонки.
        
        Args:
            email: Email продавца (PRIMARY KEY)
            seller_data: Словарь со всеми данными о продавце (извлеченными из скрипта)
            
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
                    existing_seller.is_vat_enabled != is_vat_enabled
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
                    current_holidays=current_holidays
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
        seller_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Сохранение товара и продавца в одной транзакции
        
        Гарантирует атомарность операции: либо сохраняются оба, либо ни один.
        seller_comment должен быть уже присвоен объекту product перед вызовом.
        
        Args:
            product: Объект Product для сохранения (должен содержать seller_comment, если есть)
            seller_data: Данные продавца (если есть)
            
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
            # Сохраняем продавца, если есть email
            # Если seller_data пустой или None, создаем продавца только с email
            if product.seller_email:
                # Проверяем, существует ли продавец
                existing_seller = session.query(SellerModel).filter_by(email=product.seller_email).first()
                
                # Если есть seller_data (не пустой словарь), извлекаем поля
                if seller_data and len(seller_data) > 0:
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
                    
                    if existing_seller:
                        # Обновляем существующего продавца данными из seller_data
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
                        logger.debug(f"Обновлен продавец {product.seller_email} с данными из seller_data")
                    else:
                        # Создаем нового продавца с данными из seller_data
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
                            current_holidays=current_holidays
                        )
                        session.add(db_seller)
                        logger.debug(f"Создан новый продавец {product.seller_email} с данными из seller_data")
                else:
                    # seller_data пустой или None, но есть email - создаем/проверяем продавца только с email
                    if not existing_seller:
                        # Создаем нового продавца только с email
                        db_seller = SellerModel(email=product.seller_email)
                        session.add(db_seller)
                        logger.debug(f"Создан новый продавец {product.seller_email} только с email (seller_data отсутствует)")
                    else:
                        # Продавец уже существует, ничего не делаем (не обновляем, т.к. нет данных)
                        logger.debug(f"Продавец {product.seller_email} уже существует, seller_data пустой - обновление не требуется")
            
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
                existing_product.seller_comment = product.seller_comment
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
                    seller_comment=product.seller_comment,
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


class UserRepository:
    """
    Репозиторий для работы с пользователями (авторизация через Google OAuth)
    """

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def create_tables(self):
        """Создание таблиц в БД"""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Получение сессии для использования в FastAPI Depends"""
        return self.SessionLocal()

    def find_by_email(self, email: str) -> Optional[UserModel]:
        """Поиск пользователя по email"""
        session = self.SessionLocal()
        try:
            return session.query(UserModel).filter_by(email=email).first()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске пользователя {email}: {e}")
            return None
        finally:
            session.close()

    def find_by_google_id(self, google_id: str) -> Optional[UserModel]:
        """Поиск пользователя по Google ID"""
        session = self.SessionLocal()
        try:
            return session.query(UserModel).filter_by(google_id=google_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске пользователя по google_id {google_id}: {e}")
            return None
        finally:
            session.close()

    def create_user(
        self,
        email: str,
        google_id: str,
        name: Optional[str] = None,
        picture: Optional[str] = None,
        is_approved: bool = False
    ) -> Optional[UserModel]:
        """Создание нового пользователя"""
        from datetime import datetime, timezone

        session = self.SessionLocal()
        try:
            user = UserModel(
                email=email,
                google_id=google_id,
                name=name,
                picture=picture,
                is_approved=is_approved,
                approved_at=datetime.now(timezone.utc) if is_approved else None
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info(f"Создан пользователь {email}")
            return user
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при создании пользователя {email}: {e}")
            return None
        finally:
            session.close()

    def update_user(
        self,
        email: str,
        name: Optional[str] = None,
        picture: Optional[str] = None
    ) -> Optional[UserModel]:
        """Обновление данных пользователя"""
        session = self.SessionLocal()
        try:
            user = session.query(UserModel).filter_by(email=email).first()
            if user:
                if name is not None:
                    user.name = name
                if picture is not None:
                    user.picture = picture
                session.commit()
                session.refresh(user)
            return user
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при обновлении пользователя {email}: {e}")
            return None
        finally:
            session.close()

    def approve_user(self, email: str) -> Optional[UserModel]:
        """Одобрение пользователя"""
        from datetime import datetime, timezone

        session = self.SessionLocal()
        try:
            user = session.query(UserModel).filter_by(email=email).first()
            if user:
                user.is_approved = True
                user.approved_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(user)
                logger.info(f"Пользователь {email} одобрен")
            return user
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при одобрении пользователя {email}: {e}")
            return None
        finally:
            session.close()

    def reject_user(self, email: str) -> Optional[UserModel]:
        """Отклонение/деактивация пользователя"""
        session = self.SessionLocal()
        try:
            user = session.query(UserModel).filter_by(email=email).first()
            if user:
                user.is_active = False
                session.commit()
                session.refresh(user)
                logger.info(f"Пользователь {email} деактивирован")
            return user
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при деактивации пользователя {email}: {e}")
            return None
        finally:
            session.close()

    def get_all_users(self) -> list[UserModel]:
        """Получение всех пользователей"""
        session = self.SessionLocal()
        try:
            return session.query(UserModel).all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении пользователей: {e}")
            return []
        finally:
            session.close()

    def get_pending_users(self) -> list[UserModel]:
        """Получение пользователей, ожидающих одобрения"""
        session = self.SessionLocal()
        try:
            return session.query(UserModel).filter_by(is_approved=False, is_active=True).all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении pending пользователей: {e}")
            return []
        finally:
            session.close()


class CompareRepository:
    """
    Репозиторий для работы с результатами сравнения (таблица compare)
    """

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def create_tables(self):
        """Создание таблиц в БД"""
        Base.metadata.create_all(bind=self.engine)

    def clear_table(self) -> bool:
        """Очистка таблицы compare перед новым сравнением"""
        session = self.SessionLocal()
        try:
            session.query(CompareResultModel).delete()
            session.commit()
            logger.info("Таблица compare очищена")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при очистке таблицы compare: {e}")
            return False
        finally:
            session.close()

    def clear_by_catalog(self, catalog: str) -> bool:
        """Очистка результатов для конкретного каталога"""
        session = self.SessionLocal()
        try:
            session.query(CompareResultModel).filter_by(catalog=catalog).delete()
            session.commit()
            logger.info(f"Результаты для каталога {catalog} удалены")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при очистке каталога {catalog}: {e}")
            return False
        finally:
            session.close()

    def save_results(self, results: list[Dict[str, Any]], catalog: str) -> int:
        """
        Сохранение результатов сравнения в БД

        Args:
            results: Список словарей с результатами
            catalog: Название каталога ('eur' или 'gur')

        Returns:
            Количество сохраненных записей
        """
        session = self.SessionLocal()
        saved_count = 0
        try:
            for row in results:
                # Build catalog_data with all catalog fields (non-db fields)
                catalog_data = {k: v for k, v in row.items() if not k.startswith('db_') and k not in ['matched_by', 'matched_value', 'price_classification']}

                # Debug: log first row to verify article is included
                if saved_count == 0:
                    logger.info(f"Sample row keys: {list(row.keys())}")
                    logger.info(f"Catalog_data keys: {list(catalog_data.keys())}")
                    if 'article' in catalog_data:
                        logger.info(f"Article found in catalog_data: {catalog_data['article']}")
                    else:
                        logger.warning("Article NOT found in catalog_data!")

                compare_result = CompareResultModel(
                    catalog=catalog,
                    db_part_id=row.get('db_part_id'),
                    db_code=row.get('db_code'),
                    db_price=row.get('db_price'),
                    db_url=row.get('db_url'),
                    db_source_site=row.get('db_source_site'),
                    db_category=row.get('db_category'),
                    db_oem_code=row.get('db_oem_code'),
                    db_other_codes=row.get('db_other_codes'),
                    db_manufacturer_code=row.get('db_manufacturer_code'),
                    catalog_oes_numbers=row.get('oes_numbers'),
                    catalog_price_eur=row.get('price_eur'),
                    catalog_segments_names=row.get('segments_names'),
                    catalog_data=catalog_data,
                    matched_by=row.get('matched_by'),
                    matched_value=row.get('matched_value'),
                    price_classification=row.get('price_classification'),
                )
                session.add(compare_result)
                saved_count += 1

            session.commit()
            logger.info(f"Сохранено {saved_count} результатов для каталога {catalog}")
            return saved_count
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при сохранении результатов: {e}")
            return 0
        finally:
            session.close()

    def get_all(self, catalog: Optional[str] = None) -> list[CompareResultModel]:
        """Получение всех результатов сравнения"""
        session = self.SessionLocal()
        try:
            query = session.query(CompareResultModel)
            if catalog:
                query = query.filter_by(catalog=catalog)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении результатов: {e}")
            return []
        finally:
            session.close()

    def get_by_classification(self, classification: str, catalog: Optional[str] = None) -> list[CompareResultModel]:
        """Получение результатов по классификации цены"""
        session = self.SessionLocal()
        try:
            query = session.query(CompareResultModel).filter_by(price_classification=classification)
            if catalog:
                query = query.filter_by(catalog=catalog)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении результатов: {e}")
            return []
        finally:
            session.close()

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики по результатам сравнения"""
        session = self.SessionLocal()
        try:
            from sqlalchemy import func

            total = session.query(func.count(CompareResultModel.id)).scalar()

            stats = {
                'total': total,
                'by_catalog': {},
                'by_classification': {},
            }

            # По каталогам
            catalog_counts = session.query(
                CompareResultModel.catalog,
                func.count(CompareResultModel.id)
            ).group_by(CompareResultModel.catalog).all()
            stats['by_catalog'] = {cat: cnt for cat, cnt in catalog_counts}

            # По классификации
            class_counts = session.query(
                CompareResultModel.price_classification,
                func.count(CompareResultModel.id)
            ).group_by(CompareResultModel.price_classification).all()
            stats['by_classification'] = {cls or 'NA': cnt for cls, cnt in class_counts}

            return stats
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {}
        finally:
            session.close()


class CatalogMatchRepository:
    """
    Репозиторий для работы с catalog_matches и unmatched_products

    Хранит результаты сравнения в формате: каталог → список совпавших продуктов
    """

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def create_tables(self):
        """Создание таблиц в БД"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Таблицы catalog_matches и unmatched_products созданы/проверены")

    def clear_tables(self, catalog: Optional[str] = None) -> bool:
        """
        Очистка таблиц catalog_matches и unmatched_products

        Args:
            catalog: Если указан, удаляет только данные для этого каталога ('eur' или 'gur')

        Returns:
            True если успешно
        """
        session = self.SessionLocal()
        try:
            if catalog:
                session.query(CatalogMatchModel).filter_by(catalog=catalog).delete()
                session.query(UnmatchedProductModel).filter_by(catalog=catalog).delete()
                logger.info(f"Очищены данные для каталога {catalog}")
            else:
                session.query(CatalogMatchModel).delete()
                session.query(UnmatchedProductModel).delete()
                logger.info("Очищены все данные из catalog_matches и unmatched_products")

            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при очистке таблиц: {e}")
            return False
        finally:
            session.close()

    def save_catalog_matches(self, results: List[Dict[str, Any]], catalog: str) -> int:
        """
        Сохранение совпавших каталожных позиций

        Args:
            results: Список словарей с результатами (catalog_oes_numbers, matched_products, etc.)
            catalog: Название каталога ('eur' или 'gur')

        Returns:
            Количество сохраненных записей
        """
        session = self.SessionLocal()
        saved_count = 0
        try:
            for row in results:
                catalog_match = CatalogMatchModel(
                    catalog=catalog,
                    catalog_oes_numbers=row.get('catalog_oes_numbers'),
                    catalog_price_eur=row.get('catalog_price_eur'),
                    catalog_price_usd=row.get('catalog_price_usd'),
                    catalog_segments_names=row.get('catalog_segments_names'),
                    matched_products_count=row.get('matched_products_count', 0),
                    matched_products_ids=row.get('matched_products_ids', []),
                    price_match_ok_count=row.get('price_match_ok_count', 0),
                    price_match_high_count=row.get('price_match_high_count', 0),
                    avg_db_price=row.get('avg_db_price'),
                    min_db_price=row.get('min_db_price'),
                    max_db_price=row.get('max_db_price'),
                    catalog_data=row.get('catalog_data', {}),
                    matched_products=row.get('matched_products', [])
                )
                session.add(catalog_match)
                saved_count += 1

            session.commit()
            logger.info(f"Сохранено {saved_count} catalog_matches для каталога {catalog}")
            return saved_count
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при сохранении catalog_matches: {e}")
            return 0
        finally:
            session.close()

    def save_unmatched_products(self, results: List[Dict[str, Any]], catalog: str) -> int:
        """
        Сохранение несовпавших продуктов

        Args:
            results: Список словарей с продуктами (product_part_id, searched_codes, etc.)
            catalog: Название каталога ('eur' или 'gur')

        Returns:
            Количество сохраненных записей
        """
        session = self.SessionLocal()
        saved_count = 0
        try:
            for row in results:
                unmatched = UnmatchedProductModel(
                    catalog=catalog,
                    product_part_id=row.get('product_part_id'),
                    product_code=row.get('product_code'),
                    product_price=row.get('product_price'),
                    searched_codes=row.get('searched_codes', {}),
                    product_data=row.get('product_data', {})
                )
                session.add(unmatched)
                saved_count += 1

            session.commit()
            logger.info(f"Сохранено {saved_count} unmatched_products для каталога {catalog}")
            return saved_count
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при сохранении unmatched_products: {e}")
            return 0
        finally:
            session.close()

    def get_catalog_matches(self, catalog: Optional[str] = None, limit: Optional[int] = None) -> List[CatalogMatchModel]:
        """Получение всех catalog_matches"""
        session = self.SessionLocal()
        try:
            query = session.query(CatalogMatchModel)
            if catalog:
                query = query.filter_by(catalog=catalog)
            if limit:
                query = query.limit(limit)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении catalog_matches: {e}")
            return []
        finally:
            session.close()

    def get_unmatched_products(self, catalog: Optional[str] = None, limit: Optional[int] = None) -> List[UnmatchedProductModel]:
        """Получение всех unmatched_products"""
        session = self.SessionLocal()
        try:
            query = session.query(UnmatchedProductModel)
            if catalog:
                query = query.filter_by(catalog=catalog)
            if limit:
                query = query.limit(limit)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении unmatched_products: {e}")
            return []
        finally:
            session.close()

    def get_stats(self, catalog: Optional[str] = None) -> Dict[str, Any]:
        """
        Получение статистики по catalog_matches и unmatched_products

        Args:
            catalog: Фильтр по каталогу (опционально)

        Returns:
            Словарь со статистикой
        """
        session = self.SessionLocal()
        try:
            from sqlalchemy import func

            stats = {}

            # Catalog matches stats
            matches_query = session.query(func.count(CatalogMatchModel.id))
            if catalog:
                matches_query = matches_query.filter_by(catalog=catalog)
            stats['catalog_matches_count'] = matches_query.scalar()

            # Total matched products count
            matched_products_query = session.query(func.sum(CatalogMatchModel.matched_products_count))
            if catalog:
                matched_products_query = matched_products_query.filter_by(catalog=catalog)
            stats['total_matched_products'] = matched_products_query.scalar() or 0

            # Unmatched products stats
            unmatched_query = session.query(func.count(UnmatchedProductModel.id))
            if catalog:
                unmatched_query = unmatched_query.filter_by(catalog=catalog)
            stats['unmatched_products_count'] = unmatched_query.scalar()

            # Price classification breakdown
            ok_count_query = session.query(func.sum(CatalogMatchModel.price_match_ok_count))
            high_count_query = session.query(func.sum(CatalogMatchModel.price_match_high_count))
            if catalog:
                ok_count_query = ok_count_query.filter_by(catalog=catalog)
                high_count_query = high_count_query.filter_by(catalog=catalog)

            stats['price_ok_count'] = ok_count_query.scalar() or 0
            stats['price_high_count'] = high_count_query.scalar() or 0

            # By catalog breakdown (if no specific catalog requested)
            if not catalog:
                by_catalog = {}
                catalogs = session.query(CatalogMatchModel.catalog).distinct().all()
                for (cat,) in catalogs:
                    by_catalog[cat] = self.get_stats(catalog=cat)
                stats['by_catalog'] = by_catalog

            return stats
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {}
        finally:
            session.close()


class ConversationRepository:
    """
    Репозиторий для работы с переписками (conversations и messages)
    """

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def create_tables(self):
        """Создание таблиц в БД"""
        Base.metadata.create_all(bind=self.engine)

    # === Conversations ===

    def create_conversation(
        self,
        seller_email: str,
        position_ids: List[str],
        title: Optional[str] = None,
        language: str = 'en'
    ) -> Optional[ConversationModel]:
        """
        Создание новой переписки с продавцом

        Args:
            seller_email: Email продавца
            position_ids: Список part_id позиций, о которых идет переписка
            title: Название переписки (опционально)
            language: Язык переписки

        Returns:
            Созданная переписка или None
        """
        session = self.SessionLocal()
        try:
            conversation = ConversationModel(
                seller_email=seller_email,
                position_ids=position_ids,
                title=title or f"Inquiry about {len(position_ids)} positions",
                language=language,
                status='active',
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)
            logger.info(f"Создана переписка {conversation.id} с {seller_email}")
            return conversation
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при создании переписки: {e}")
            return None
        finally:
            session.close()

    def get_conversation(self, conversation_id: int) -> Optional[ConversationModel]:
        """Получение переписки по ID"""
        session = self.SessionLocal()
        try:
            return session.query(ConversationModel).filter_by(id=conversation_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении переписки {conversation_id}: {e}")
            return None
        finally:
            session.close()

    def get_conversations_by_seller(self, seller_email: str) -> List[ConversationModel]:
        """Получение всех переписок с продавцом"""
        session = self.SessionLocal()
        try:
            return session.query(ConversationModel)\
                .filter_by(seller_email=seller_email)\
                .order_by(ConversationModel.last_message_at.desc().nullsfirst(), ConversationModel.created_at.desc())\
                .all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении переписок с {seller_email}: {e}")
            return []
        finally:
            session.close()

    def get_all_conversations(self, status: Optional[str] = None) -> List[ConversationModel]:
        """Получение всех переписок"""
        session = self.SessionLocal()
        try:
            query = session.query(ConversationModel)
            if status:
                query = query.filter_by(status=status)
            return query.order_by(ConversationModel.last_message_at.desc().nullsfirst()).all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении переписок: {e}")
            return []
        finally:
            session.close()

    def update_conversation_status(self, conversation_id: int, status: str) -> bool:
        """Обновление статуса переписки"""
        session = self.SessionLocal()
        try:
            conversation = session.query(ConversationModel).filter_by(id=conversation_id).first()
            if conversation:
                conversation.status = status
                conversation.updated_at = datetime.now(timezone.utc)
                session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при обновлении статуса переписки {conversation_id}: {e}")
            return False
        finally:
            session.close()

    def delete_conversation(self, conversation_id: int) -> bool:
        """Удаление переписки (каскадно удалит все сообщения)"""
        session = self.SessionLocal()
        try:
            conversation = session.query(ConversationModel).filter_by(id=conversation_id).first()
            if conversation:
                session.delete(conversation)
                session.commit()
                logger.info(f"Удалена переписка {conversation_id}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при удалении переписки {conversation_id}: {e}")
            return False
        finally:
            session.close()

    # === Messages ===

    def add_message(
        self,
        conversation_id: int,
        direction: str,  # 'outbound' или 'inbound'
        body: str,
        subject: Optional[str] = None,
        body_html: Optional[str] = None,
        status: str = 'draft',
        message_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None
    ) -> Optional[MessageModel]:
        """
        Добавление сообщения в переписку

        Args:
            conversation_id: ID переписки
            direction: Направление ('outbound' - мы отправляем, 'inbound' - нам отправляют)
            body: Текст сообщения
            subject: Тема (опционально)
            body_html: HTML версия (опционально)
            status: Статус сообщения
            message_id: Email Message-ID
            in_reply_to: In-Reply-To header
            references: References header

        Returns:
            Созданное сообщение или None
        """
        session = self.SessionLocal()
        try:
            message = MessageModel(
                conversation_id=conversation_id,
                direction=direction,
                subject=subject,
                body=body,
                body_html=body_html,
                status=status,
                message_id=message_id,
                in_reply_to=in_reply_to,
                references=references,
                created_at=datetime.now(timezone.utc),
                received_at=datetime.now(timezone.utc) if direction == 'inbound' else None
            )
            session.add(message)

            # Обновляем last_message_at в переписке
            conversation = session.query(ConversationModel).filter_by(id=conversation_id).first()
            if conversation:
                conversation.last_message_at = datetime.now(timezone.utc)
                conversation.updated_at = datetime.now(timezone.utc)
                # Если получили ответ, меняем статус
                if direction == 'inbound' and conversation.status == 'pending_reply':
                    conversation.status = 'active'

            session.commit()
            session.refresh(message)
            logger.info(f"Добавлено сообщение {message.id} в переписку {conversation_id}")
            return message
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при добавлении сообщения: {e}")
            return None
        finally:
            session.close()

    def get_messages(self, conversation_id: int) -> List[MessageModel]:
        """Получение всех сообщений переписки"""
        session = self.SessionLocal()
        try:
            return session.query(MessageModel)\
                .filter_by(conversation_id=conversation_id)\
                .order_by(MessageModel.created_at.asc())\
                .all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении сообщений переписки {conversation_id}: {e}")
            return []
        finally:
            session.close()

    def get_message(self, message_id: int) -> Optional[MessageModel]:
        """Получение сообщения по ID"""
        session = self.SessionLocal()
        try:
            return session.query(MessageModel).filter_by(id=message_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении сообщения {message_id}: {e}")
            return None
        finally:
            session.close()

    def update_message_status(
        self,
        message_id: int,
        status: str,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        email_message_id: Optional[str] = None
    ) -> bool:
        """Обновление статуса сообщения после отправки"""
        session = self.SessionLocal()
        try:
            message = session.query(MessageModel).filter_by(id=message_id).first()
            if message:
                message.status = status
                if error_message:
                    message.error_message = error_message
                if sent_at:
                    message.sent_at = sent_at
                if email_message_id:
                    message.message_id = email_message_id
                session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при обновлении статуса сообщения {message_id}: {e}")
            return False
        finally:
            session.close()

    def find_conversation_by_message_id(self, email_message_id: str) -> Optional[ConversationModel]:
        """Поиск переписки по Message-ID (для связывания ответов)"""
        session = self.SessionLocal()
        try:
            message = session.query(MessageModel).filter_by(message_id=email_message_id).first()
            if message:
                return session.query(ConversationModel).filter_by(id=message.conversation_id).first()
            return None
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске переписки по message_id {email_message_id}: {e}")
            return None
        finally:
            session.close()

    def find_conversation_by_in_reply_to(self, in_reply_to: str) -> Optional[ConversationModel]:
        """Поиск переписки по In-Reply-To header (для связывания ответов)"""
        session = self.SessionLocal()
        try:
            # Ищем сообщение с таким message_id
            original_message = session.query(MessageModel).filter_by(message_id=in_reply_to).first()
            if original_message:
                return session.query(ConversationModel).filter_by(id=original_message.conversation_id).first()
            return None
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске переписки по in_reply_to {in_reply_to}: {e}")
            return None
        finally:
            session.close()

    def get_conversation_with_messages(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Получение переписки со всеми сообщениями (для отображения в чате)"""
        session = self.SessionLocal()
        try:
            conversation = session.query(ConversationModel).filter_by(id=conversation_id).first()
            if not conversation:
                return None

            messages = session.query(MessageModel)\
                .filter_by(conversation_id=conversation_id)\
                .order_by(MessageModel.created_at.asc())\
                .all()
            
            for message in messages:
                message.body = clean_reply_to_text(message.body)

            return {
                'conversation': conversation.to_dict(),
                'messages': [m.to_dict() for m in messages]
            }
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении переписки {conversation_id}: {e}")
            return None
        finally:
            session.close()

    def get_conversations_with_last_message(self, seller_email: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получение списка переписок с последним сообщением и статусом непрочитанных"""
        session = self.SessionLocal()
        try:
            query = session.query(ConversationModel)
            if seller_email:
                query = query.filter_by(seller_email=seller_email)
            conversations = query.order_by(
                ConversationModel.last_message_at.desc().nullsfirst(),
                ConversationModel.created_at.desc()
            ).all()

            result = []
            for conv in conversations:
                last_message = session.query(MessageModel)\
                    .filter_by(conversation_id=conv.id)\
                    .order_by(MessageModel.created_at.desc())\
                    .first()

                # Check for unread inbound messages
                unread_count = session.query(MessageModel)\
                    .filter_by(conversation_id=conv.id, direction='inbound', is_read=False)\
                    .count()

                # Get classification if exists
                classification = session.query(ConversationClassificationModel)\
                    .filter_by(conversation_id=conv.id)\
                    .first()

                conv_dict = conv.to_dict()
                conv_dict['last_message'] = last_message.to_dict() if last_message else None
                conv_dict['message_count'] = session.query(MessageModel).filter_by(conversation_id=conv.id).count()
                conv_dict['unread_count'] = unread_count
                conv_dict['has_unread'] = unread_count > 0
                conv_dict['classification'] = classification.to_dict() if classification else None
                result.append(conv_dict)

            return result
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении переписок: {e}")
            return []
        finally:
            session.close()

    def mark_messages_as_read(self, conversation_id: int) -> int:
        """Отметить все inbound сообщения переписки как прочитанные"""
        session = self.SessionLocal()
        try:
            count = session.query(MessageModel)\
                .filter_by(conversation_id=conversation_id, direction='inbound', is_read=False)\
                .update({'is_read': True})
            session.commit()
            return count
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при отметке сообщений как прочитанных: {e}")
            return 0
        finally:
            session.close()

    # === Classification ===

    def save_classification(self, conversation_id: int, classification: Dict[str, Any]) -> Optional[ConversationClassificationModel]:
        """
        Сохранение или обновление классификации переписки.
        Использует upsert - создает новую запись или обновляет существующую.

        Args:
            conversation_id: ID переписки
            classification: Словарь с результатами классификации

        Returns:
            ConversationClassificationModel или None при ошибке
        """
        session = self.SessionLocal()
        try:
            # Проверяем существующую классификацию
            existing = session.query(ConversationClassificationModel)\
                .filter_by(conversation_id=conversation_id)\
                .first()

            # Преобразуем prices_mentioned в JSON-совместимый формат
            prices_mentioned = classification.get('prices_mentioned', [])
            if prices_mentioned and hasattr(prices_mentioned[0], 'model_dump'):
                prices_mentioned = [p.model_dump() for p in prices_mentioned]

            if existing:
                # Обновляем существующую
                existing.status = classification.get('status')
                existing.decline_reason = classification.get('decline_reason')
                existing.decline_details = classification.get('decline_details')
                existing.confidence = classification.get('confidence')
                existing.seller_sentiment = classification.get('seller_sentiment')
                existing.has_price_info = classification.get('has_price_info', False)
                existing.prices_mentioned = prices_mentioned
                existing.availability_info = classification.get('availability_info')
                existing.next_steps = classification.get('next_steps')
                existing.summary = classification.get('summary')
                existing.updated_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(existing)
                logger.info(f"Обновлена классификация для переписки {conversation_id}: {existing.status}")
                return existing
            else:
                # Создаем новую
                new_classification = ConversationClassificationModel(
                    conversation_id=conversation_id,
                    status=classification.get('status'),
                    decline_reason=classification.get('decline_reason'),
                    decline_details=classification.get('decline_details'),
                    confidence=classification.get('confidence'),
                    seller_sentiment=classification.get('seller_sentiment'),
                    has_price_info=classification.get('has_price_info', False),
                    prices_mentioned=prices_mentioned,
                    availability_info=classification.get('availability_info'),
                    next_steps=classification.get('next_steps'),
                    summary=classification.get('summary'),
                )
                session.add(new_classification)
                session.commit()
                session.refresh(new_classification)
                logger.info(f"Создана классификация для переписки {conversation_id}: {new_classification.status}")
                return new_classification

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка при сохранении классификации для переписки {conversation_id}: {e}")
            return None
        finally:
            session.close()

    def get_classification(self, conversation_id: int) -> Optional[ConversationClassificationModel]:
        """Получение классификации переписки по ID"""
        session = self.SessionLocal()
        try:
            return session.query(ConversationClassificationModel)\
                .filter_by(conversation_id=conversation_id)\
                .first()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении классификации {conversation_id}: {e}")
            return None
        finally:
            session.close()

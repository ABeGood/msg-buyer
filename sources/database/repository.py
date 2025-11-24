"""
Репозиторий для работы с товарами в базе данных
"""
import json
import hashlib
from typing import Optional, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sources.database.models import ProductModel, SellerModel, UserModel, Base
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

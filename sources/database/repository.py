"""
Репозиторий для работы с товарами в базе данных
"""
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sources.database.models import ProductModel, Base
from sources.classes.product import Product


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
        print("[OK] Таблицы созданы/проверены")
    
    def save(self, product: Product) -> bool:
        """
        Сохранение товара в БД
        
        Если товар с таким part_id уже существует, он будет обновлен
        
        Args:
            product: Объект Product для сохранения
            
        Returns:
            True если успешно, False в противном случае
        """
        if not product.part_id:
            print("[ERROR] part_id обязателен для сохранения")
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
                existing_product.seller_info = product.seller_info
                existing_product.images = product.images
                # updated_at обновится автоматически через onupdate
                
                session.commit()
                print(f"[OK] Товар {product.part_id} обновлен в БД")
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
                    seller_info=product.seller_info,
                    images=product.images
                )
                
                session.add(db_product)
                session.commit()
                print(f"[OK] Товар {product.part_id} сохранен в БД")
                return True
                
        except SQLAlchemyError as e:
            session.rollback()
            print(f"[ERROR] Ошибка при сохранении товара {product.part_id}: {e}")
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
                print(f"[OK] Товар {part_id} удален из БД")
                return True
            else:
                print(f"[WARNING] Товар {part_id} не найден в БД")
                return False
                
        except SQLAlchemyError as e:
            session.rollback()
            print(f"[ERROR] Ошибка при удалении товара {part_id}: {e}")
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
                print(f"[OK] Товар {code} (part_id={part_id}) удален из БД")
                return True
            else:
                print(f"[WARNING] Товар {code} не найден в БД")
                return False
                
        except SQLAlchemyError as e:
            session.rollback()
            print(f"[ERROR] Ошибка при удалении товара {code}: {e}")
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
            print(f"[ERROR] Ошибка при поиске товара {part_id}: {e}")
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
            print(f"[ERROR] Ошибка при поиске товара {code}: {e}")
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
        return Product(
            part_id=db_product.part_id,
            code=db_product.code,
            price=float(db_product.price) if db_product.price else None,
            url=db_product.url,
            source_site=db_product.source_site,
            category=db_product.category,
            item_description=db_product.item_description or {},
            car_details=db_product.car_details or {},
            seller_info=db_product.seller_info or {},
            images=db_product.images or []
        )


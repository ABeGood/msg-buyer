"""
Конфигурация для подключения к базе данных
"""
import os
import re
from typing import Optional
from pathlib import Path
from sources.utils.logger import get_logger

logger = get_logger("config")

# Загружаем переменные окружения из .env файла
try:
    from dotenv import load_dotenv
    # Ищем .env файл в корне проекта
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Пробуем загрузить из текущей директории
        load_dotenv()
except ImportError:
    # python-dotenv не установлен, используем только системные переменные
    pass


def _validate_database_url(url: str) -> bool:
    """
    Валидация формата URL базы данных PostgreSQL
    
    Args:
        url: URL для проверки
        
    Returns:
        True если URL валиден, False в противном случае
    """
    if not url:
        return False
    
    # Паттерн для PostgreSQL URL: postgresql://user:password@host:port/database
    pattern = r'^postgresql://[^:]+:[^@]+@[^:]+:\d+/\w+'
    return bool(re.match(pattern, url))


def get_database_url() -> Optional[str]:
    """
    Получение URL подключения к БД из переменных окружения
    
    Returns:
        URL подключения или None, если URL не найден или невалиден
    """
    # Пробуем разные варианты переменных окружения
    # Railway предоставляет DATABASE_URL и DATABASE_PUBLIC_URL
    database_url = (
        os.getenv('DATABASE_URL') or
        os.getenv('DATABASE_PUBLIC_URL') or  # Railway public URL
        os.getenv('POSTGRES_URL') or
        os.getenv('POSTGRESQL_URL')
    )
    
    if not database_url:
        # Пробуем собрать из отдельных переменных
        host = os.getenv('PGHOST')
        port = os.getenv('PGPORT', '5432')
        user = os.getenv('PGUSER')
        password = os.getenv('PGPASSWORD')
        database = os.getenv('PGDATABASE')
        
        if all([host, user, password, database]):
            database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    # Валидация URL
    if database_url and not _validate_database_url(database_url):
        logger.warning(f"URL БД имеет неверный формат: {database_url[:50]}...")
        return None
    
    return database_url


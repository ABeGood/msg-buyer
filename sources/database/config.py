"""
Конфигурация для подключения к базе данных
"""
import os
from typing import Optional
from pathlib import Path

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


def get_database_url() -> Optional[str]:
    """
    Получение URL подключения к БД из переменных окружения
    
    Returns:
        URL подключения или None
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
    
    return database_url


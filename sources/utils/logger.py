"""
Настройка логирования для проекта MSG Buyer
"""
import logging
import sys
from pathlib import Path


def setup_logger(name: str = "msg_buyer", log_level: int = logging.INFO) -> logging.Logger:
    """
    Настройка логгера для проекта
    
    Создает логгер с выводом в консоль и файл.
    Файл логов перезаписывается при каждом запуске.
    
    Args:
        name: Имя логгера
        log_level: Уровень логирования (по умолчанию INFO)
        
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Удаляем существующие обработчики, если есть
    logger.handlers.clear()
    
    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Обработчик для файла
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "msg_buyer.log"
    
    # Перезаписываем файл при каждом запуске
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "msg_buyer") -> logging.Logger:
    """
    Получение логгера (создает новый, если не существует)
    
    Args:
        name: Имя логгера
        
    Returns:
        Логгер
    """
    logger = logging.getLogger(name)
    
    # Если логгер еще не настроен, настраиваем его
    if not logger.handlers:
        return setup_logger(name)
    
    return logger


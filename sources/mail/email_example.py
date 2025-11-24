"""
Пример использования Email Service
"""
from sources.services.email_service import EmailService
from sources.database.repository import ProductRepository
from sources.database.config import get_database_url
from sources.utils.logger import setup_logger

logger = setup_logger("email_example")


def example_send_single_inquiry():
    """
    Пример отправки одного запроса продавцу
    """
    print("\n" + "=" * 80)
    print("ПРИМЕР: Отправка одного запроса")
    print("=" * 80)
    
    # Получаем URL базы данных
    database_url = get_database_url()
    if not database_url:
        print("ERROR: DATABASE_URL не найден в .env")
        return
    
    # Инициализируем сервисы
    email_service = EmailService(database_url=database_url)
    repository = ProductRepository(database_url)
    
    # Находим товар (замените на реальный part_id из вашей БД)
    product = repository.find_by_part_id("YOUR_PART_ID")
    
    if not product:
        print("ERROR: Товар не найден в БД")
        print("Используйте реальный part_id из вашей базы данных")
        return
    
    print(f"\nТовар найден: {product.code}")
    print(f"Продавец: {product.seller_email}")
    
    # Отправляем запрос
    success = email_service.send_product_inquiry(
        product=product,
        message="Hello! I'm interested in this steering rack. Is it still available? What's the condition?",
        buyer_email="your-email@example.com",
        buyer_name="Your Name",
        buyer_phone="+370123456789",  # Опционально
        language='en'  # или 'lt' для литовского
    )
    
    if success:
        print("\n✓ Email успешно отправлен!")
    else:
        print("\n✗ Ошибка при отправке email")


def example_check_responses():
    """
    Пример проверки ответов от продавцов
    """
    print("\n" + "=" * 80)
    print("ПРИМЕР: Проверка ответов от продавцов")
    print("=" * 80)
    
    database_url = get_database_url()
    if not database_url:
        print("ERROR: DATABASE_URL не найден в .env")
        return
    
    email_service = EmailService(database_url=database_url)
    
    # Проверяем ответы (не помечаем как прочитанные)
    responses = email_service.check_responses(mark_as_read=False)
    
    print(f"\nНайдено ответов: {len(responses)}")
    
    for i, response in enumerate(responses, 1):
        print(f"\n--- Ответ #{i} ---")
        print(f"От: {response['seller_email']}")
        print(f"Тема: {response['subject']}")
        print(f"Положительный: {response['is_positive']}")
        
        if response['has_price']:
            print(f"Цена: €{response['extracted_price']}")
        
        if response['is_available']:
            print("Статус: Доступен")
        elif response['has_availability']:
            print("Статус: Не доступен")
        else:
            print("Статус: Неизвестно")
        
        print(f"\nТекст (первые 200 символов):")
        print(response['body'][:200] + "...")


def example_bulk_inquiries():
    """
    Пример отправки запросов нескольким продавцам
    """
    print("\n" + "=" * 80)
    print("ПРИМЕР: Массовая отправка запросов")
    print("=" * 80)
    
    database_url = get_database_url()
    if not database_url:
        print("ERROR: DATABASE_URL не найден в .env")
        return
    
    email_service = EmailService(database_url=database_url)
    repository = ProductRepository(database_url)
    
    # Находим несколько товаров (замените на реальные part_id)
    part_ids = ["PART_ID_1", "PART_ID_2", "PART_ID_3"]
    products = []
    
    for part_id in part_ids:
        product = repository.find_by_part_id(part_id)
        if product and product.seller_email:
            products.append(product)
    
    if not products:
        print("ERROR: Товары не найдены")
        return
    
    print(f"\nНайдено товаров: {len(products)}")
    
    # Отправляем запросы
    results = email_service.send_bulk_inquiries(
        products=products,
        message="Hello! I'm interested in multiple parts. Are they available?",
        buyer_email="your-email@example.com",
        buyer_name="Your Name",
        language='en'
    )
    
    print(f"\nРезультаты:")
    print(f"  Всего: {results['total']}")
    print(f"  Отправлено: {results['sent']}")
    print(f"  Ошибок: {results['failed']}")
    print(f"  Пропущено: {results['skipped']}")
    
    if results['errors']:
        print("\nОшибки:")
        for error in results['errors']:
            print(f"  - {error['product_id']}: {error['error']}")


def main():
    """
    Главное меню с примерами
    """
    print("\n" + "=" * 80)
    print("EMAIL SERVICE - ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ")
    print("=" * 80)
    print("\nВыберите пример:")
    print("1. Отправить один запрос продавцу")
    print("2. Проверить ответы от продавцов")
    print("3. Массовая отправка запросов")
    print("0. Выход")
    
    choice = input("\nВведите номер: ")
    
    if choice == '1':
        example_send_single_inquiry()
    elif choice == '2':
        example_check_responses()
    elif choice == '3':
        example_bulk_inquiries()
    elif choice == '0':
        print("До свидания!")
    else:
        print("Неверный выбор")


if __name__ == "__main__":
    main()

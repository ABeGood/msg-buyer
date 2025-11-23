"""
CLI скрипт для отправки email запросов продавцам
"""
import sys
import argparse
from sources.services.email_service import EmailService
from sources.database.repository import ProductRepository
from sources.database.config import get_database_url
from sources.utils.logger import setup_logger

logger = setup_logger("send_inquiry")


def main():
    """
    Главная функция для отправки email запросов
    """
    parser = argparse.ArgumentParser(
        description='Отправка email запросов продавцам о товарах'
    )
    
    parser.add_argument(
        '--part-id',
        type=str,
        help='Part ID товара для запроса'
    )
    
    parser.add_argument(
        '--code',
        type=str,
        help='Code (SKU) товара для запроса'
    )
    
    parser.add_argument(
        '--message',
        type=str,
        required=True,
        help='Текст сообщения продавцу'
    )
    
    parser.add_argument(
        '--buyer-name',
        type=str,
        required=True,
        help='Имя покупателя'
    )
    
    parser.add_argument(
        '--buyer-email',
        type=str,
        required=True,
        help='Email покупателя для ответа'
    )
    
    parser.add_argument(
        '--buyer-phone',
        type=str,
        help='Телефон покупателя (опционально)'
    )
    
    parser.add_argument(
        '--language',
        type=str,
        choices=['en', 'lt'],
        default='en',
        help='Язык письма (en или lt)'
    )
    
    parser.add_argument(
        '--check-responses',
        action='store_true',
        help='Проверить почтовый ящик на наличие ответов от продавцов'
    )
    
    parser.add_argument(
        '--mark-as-read',
        action='store_true',
        help='Помечать письма как прочитанные при проверке ответов'
    )
    
    args = parser.parse_args()
    
    # Получаем URL базы данных
    database_url = get_database_url()
    if not database_url:
        logger.error("DATABASE_URL не найден. Проверьте файл .env")
        sys.exit(1)
    
    # Инициализируем сервисы
    email_service = EmailService(database_url=database_url)
    
    # Режим проверки ответов
    if args.check_responses:
        print("\n" + "=" * 80)
        print("ПРОВЕРКА ОТВЕТОВ ОТ ПРОДАВЦОВ")
        print("=" * 80)
        
        logger.info("Начинаем проверку ответов от продавцов")
        responses = email_service.check_responses(mark_as_read=args.mark_as_read)
        
        print(f"\nНайдено ответов: {len(responses)}")
        
        for i, response in enumerate(responses, 1):
            print(f"\n{'=' * 80}")
            print(f"ОТВЕТ #{i}")
            print(f"{'=' * 80}")
            print(f"От: {response['seller_email']}")
            print(f"Тема: {response['subject']}")
            print(f"Дата: {response['date']}")
            print(f"Код товара: {response.get('product_code', 'не найден')}")
            print(f"Положительный ответ: {'Да' if response['is_positive'] else 'Нет'}")
            print(f"Есть цена: {'Да' if response['has_price'] else 'Нет'}")
            if response['extracted_price']:
                print(f"Цена: €{response['extracted_price']}")
            print(f"Доступность: {'Да' if response['is_available'] else 'Нет/Неизвестно'}")
            print(f"\nТекст (первые 300 символов):")
            print(response['body'][:300])
            if len(response['body']) > 300:
                print("...")
        
        logger.info(f"Проверка завершена. Найдено {len(responses)} ответов")
        return
    
    # Режим отправки запроса
    if not args.part_id and not args.code:
        logger.error("Необходимо указать --part-id или --code")
        parser.print_help()
        sys.exit(1)
    
    repository = ProductRepository(database_url)
    
    # Находим товар
    if args.part_id:
        product = repository.find_by_part_id(args.part_id)
        if not product:
            logger.error(f"Товар с part_id={args.part_id} не найден в БД")
            sys.exit(1)
    else:
        product = repository.find_by_code(args.code)
        if not product:
            logger.error(f"Товар с code={args.code} не найден в БД")
            sys.exit(1)
    
    print("\n" + "=" * 80)
    print("ОТПРАВКА EMAIL ЗАПРОСА ПРОДАВЦУ")
    print("=" * 80)
    
    print(f"\nТовар:")
    print(f"  Part ID: {product.part_id}")
    print(f"  Code: {product.code}")
    print(f"  Category: {product.category}")
    if product.price:
        print(f"  Price: €{product.price}")
    
    print(f"\nПродавец:")
    print(f"  Email: {product.seller_email}")
    
    print(f"\nПокупатель:")
    print(f"  Name: {args.buyer_name}")
    print(f"  Email: {args.buyer_email}")
    if args.buyer_phone:
        print(f"  Phone: {args.buyer_phone}")
    
    print(f"\nСообщение:")
    print(f"  {args.message}")
    
    print(f"\nЯзык: {args.language}")
    
    # Подтверждение
    print("\n" + "=" * 80)
    confirm = input("Отправить email? (y/n): ")
    
    if confirm.lower() != 'y':
        print("Отменено")
        sys.exit(0)
    
    # Отправляем email
    logger.info(f"Отправка email для товара {product.part_id}")
    success = email_service.send_product_inquiry(
        product=product,
        message=args.message,
        buyer_email=args.buyer_email,
        buyer_name=args.buyer_name,
        buyer_phone=args.buyer_phone,
        language=args.language
    )
    
    if success:
        print("\n✓ Email успешно отправлен!")
        logger.info("Email успешно отправлен")
    else:
        print("\n✗ Ошибка при отправке email")
        logger.error("Ошибка при отправке email")
        sys.exit(1)


if __name__ == "__main__":
    main()

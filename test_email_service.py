"""
Тесты для Email Service
"""
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from sources.services.email_service import EmailService
from sources.database.config import get_database_url
from sources.classes.product import Product


def test_configuration():
    """Тест конфигурации"""
    print("\n" + "=" * 80)
    print("ТЕСТ 1: Проверка конфигурации")
    print("=" * 80)
    
    # Проверяем наличие database_url
    database_url = get_database_url()
    if database_url:
        print("✓ DATABASE_URL найден")
    else:
        print("✗ DATABASE_URL не найден в .env")
        return False
    
    # Проверяем email конфигурацию
    email_service = EmailService(database_url=database_url)
    
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    if smtp_user:
        print(f"✓ SMTP_USER: {smtp_user}")
    else:
        print("✗ SMTP_USER не настроен")
        return False
    
    if smtp_password:
        print(f"✓ SMTP_PASSWORD: {'*' * len(smtp_password)}")
    else:
        print("✗ SMTP_PASSWORD не настроен")
        return False
    
    if email_service.validate_configuration():
        print("✓ Конфигурация валидна")
        return True
    else:
        print("✗ Конфигурация невалидна")
        return False


def test_email_templates():
    """Тест генерации email шаблонов"""
    print("\n" + "=" * 80)
    print("ТЕСТ 2: Генерация email шаблонов")
    print("=" * 80)
    
    # Создаем тестовый продукт
    product = Product(
        part_id="TEST123",
        code="ABC123",
        price=150.00,
        url="https://rrr.lt/en/used-part/abc123",
        source_site="rrr.lt",
        category="steering-rack",
        item_description={
            "manufacturer_code": "12345",
            "condition": "Used, good"
        },
        car_details={
            "make": "Renault",
            "model": "Megane",
            "year": "2015"
        },
        seller_email="test@example.com"
    )
    
    database_url = get_database_url()
    email_service = EmailService(database_url=database_url)
    
    # Генерируем subject и body
    subject = email_service._generate_subject(product, 'en')
    body = email_service._generate_inquiry_body(
        product=product,
        message="Test message",
        buyer_email="buyer@example.com",
        buyer_name="Test Buyer",
        buyer_phone="+37012345678",
        language='en'
    )
    
    print(f"✓ Subject: {subject}")
    print(f"✓ Body length: {len(body)} characters")
    print(f"✓ Contains product code: {'ABC123' in body}")
    print(f"✓ Contains buyer email: {'buyer@example.com' in body}")
    
    # Проверяем литовский шаблон
    subject_lt = email_service._generate_subject(product, 'lt')
    print(f"✓ Lithuanian subject: {subject_lt}")
    
    return True


def test_response_parsing():
    """Тест парсинга ответов"""
    print("\n" + "=" * 80)
    print("ТЕСТ 3: Парсинг ответов")
    print("=" * 80)
    
    database_url = get_database_url()
    email_service = EmailService(database_url=database_url)
    
    # Тест 1: Положительный ответ с ценой
    test_body_1 = """
    Hello,
    
    Yes, this part is available. The price is €150.00.
    We can ship it tomorrow.
    
    Best regards,
    Seller
    """
    
    analysis_1 = email_service._analyze_response_content(test_body_1)
    print("\nТест 1: Положительный ответ с ценой")
    print(f"  is_positive: {analysis_1['is_positive']}")
    print(f"  has_price: {analysis_1['has_price']}")
    print(f"  extracted_price: {analysis_1['price']}")
    print(f"  is_available: {analysis_1['is_available']}")
    
    assert analysis_1['is_positive'] == True
    assert analysis_1['has_price'] == True
    assert analysis_1['price'] == 150.00
    print("  ✓ Passed")
    
    # Тест 2: Отрицательный ответ
    test_body_2 = """
    Sorry, this part is not available anymore.
    It was sold yesterday.
    """
    
    analysis_2 = email_service._analyze_response_content(test_body_2)
    print("\nТест 2: Отрицательный ответ")
    print(f"  is_positive: {analysis_2['is_positive']}")
    print(f"  is_available: {analysis_2['is_available']}")
    
    assert analysis_2['is_positive'] == False
    assert analysis_2['is_available'] == False
    print("  ✓ Passed")
    
    # Тест 3: Литовский ответ
    test_body_3 = """
    Sveiki,
    
    Taip, turime šią detalę. Kaina 120€.
    Galime parduoti.
    """
    
    analysis_3 = email_service._analyze_response_content(test_body_3)
    print("\nТест 3: Литовский положительный ответ")
    print(f"  is_positive: {analysis_3['is_positive']}")
    print(f"  has_price: {analysis_3['has_price']}")
    print(f"  extracted_price: {analysis_3['price']}")
    
    assert analysis_3['is_positive'] == True
    assert analysis_3['has_price'] == True
    assert analysis_3['price'] == 120.00
    print("  ✓ Passed")
    
    print("\n✓ Все тесты парсинга пройдены!")
    return True


def test_product_code_extraction():
    """Тест извлечения кода товара"""
    print("\n" + "=" * 80)
    print("ТЕСТ 4: Извлечение кода товара")
    print("=" * 80)
    
    database_url = get_database_url()
    email_service = EmailService(database_url=database_url)
    
    test_cases = [
        ("Re: Inquiry about steering-rack - ABC123", "ABC123"),
        ("Užklausa dėl steering-rack - XYZ789", "XYZ789"),
        ("Part A1B2C3 inquiry", "A1B2C3"),
        ("No code here", None)
    ]
    
    for subject, expected in test_cases:
        result = email_service._extract_product_code(subject)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{subject}' -> {result} (expected: {expected})")
    
    return True


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 80)
    print("EMAIL SERVICE - ТЕСТИРОВАНИЕ")
    print("=" * 80)
    
    tests = [
        ("Конфигурация", test_configuration),
        ("Email шаблоны", test_email_templates),
        ("Парсинг ответов", test_response_parsing),
        ("Извлечение кода товара", test_product_code_extraction)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Ошибка в тесте '{name}': {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Итоги
    print("\n" + "=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nВсего тестов: {total}")
    print(f"Пройдено: {passed}")
    print(f"Провалено: {total - passed}")
    
    if passed == total:
        print("\n🎉 Все тесты пройдены успешно!")
        return 0
    else:
        print("\n⚠️  Некоторые тесты провалены")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
Точка входа в проект MSG Buyer
Парсинг товаров с сайта rrr.lt и сохранение в БД
"""
import time
from sources.scrapers import SeleniumBaseScraper
from sources.parsers.rrr.steering_rack_parser import RRRSteeringRackParser
from sources.database.repository import ProductRepository
from sources.database.config import get_database_url
from sources.utils.logger import setup_logger

# Настройка логирования
logger = setup_logger("main")


def main():
    # """
    # Основная функция для запуска парсинга и сохранения в БД
    # """
    # Настройки пагинации
    START_PAGE = 1
    END_PAGE = 10  # Парсим страницы 1-10

    print("=" * 80)
    print("MSG Buyer - Парсинг товаров Steering Rack и сохранение в БД")
    print(f"Страницы: {START_PAGE} - {END_PAGE}")
    print("=" * 80)

    scraper = None

    try:
        # 1. Инициализация скрапера
        print("\n[1] Инициализация скрапера...")
        scraper = SeleniumBaseScraper(headless=False)
        scraper.start()
        print("  [OK] Скрапер готов")

        # 2. Инициализация репозитория БД
        print("\n[2] Инициализация подключения к БД...")
        database_url = get_database_url()
        if not database_url:
            print("  [ERROR] DATABASE_URL не найден. Проверьте файл .env")
            return

        repository = ProductRepository(database_url)
        repository.create_tables()
        print("  [OK] Подключение к БД установлено")

        # 3. Инициализация парсера
        parser = RRRSteeringRackParser()

        # 4. Сбор всех товаров со всех страниц
        print("\n[3] Сбор товаров со страниц...")
        all_products = []

        for page_html in scraper.get_steering_racks_pages(START_PAGE, END_PAGE):
            products = parser.parse_product_list(page_html)
            all_products.extend(products)
            print(f"  Найдено на странице: {len(products)}, всего: {len(all_products)}")

        print(f"\n[OK] Всего найдено товаров: {len(all_products)}")

        if not all_products:
            print("  [WARNING] Товары не найдены")
            return

        # 5. Обработка товаров
        print(f"\n[4] Обработка {len(all_products)} товаров...")

        successful = 0
        failed = 0

        for i, product in enumerate(all_products, 1):
            print(f"\n[{i}/{len(all_products)}] {product.part_id} ({product.code})")

            if not product.url:
                print(f"  [SKIP] Нет URL")
                failed += 1
                continue

            try:
                # 5.1. Переход на страницу товара
                scraper.get_page(product.url)
                scraper.wait_for_page_load(timeout=4)

                # 5.2. Извлечение детальной информации
                if not scraper.driver:
                    raise Exception("Driver не инициализирован")
                detail_data = parser.parse_product_detail_enhanced(scraper.driver)

                # 5.3. Обновление объекта Product
                product.item_description = detail_data.get('item_description', {})
                product.car_details = detail_data.get('car_details', {})
                product.seller_email = detail_data.get('seller_email')
                product.images = detail_data.get('images', [])
                product.seller_comment = detail_data.get('seller_comment', '')
                seller_data = detail_data.get('seller_data', {})

                print(f"      [OK] Данные извлечены:")
                print(f"        - Item Description: {len(product.item_description)} полей")
                print(f"        - Car Details: {len(product.car_details)} полей")
                print(f"        - Seller Email: {product.seller_email or 'не найден'}")
                print(f"        - Seller Data: {len(seller_data)} полей")
                print(f"        - Seller Comment: {'найден' if product.seller_comment else 'не найден'}")
                print(f"        - Images: {len(product.images)} изображений")

                # 5.4. Сохранение в БД
                if repository.save_product_with_seller(product, seller_data):
                    print(f"      [OK] Товар и продавец сохранены в БД")
                    logger.info(f"Товар {product.part_id} успешно сохранен в БД")
                    successful += 1
                else:
                    error_msg = f"Не удалось сохранить товар {product.part_id} и продавца в БД"
                    print(f"      [ERROR] {error_msg}")
                    logger.error(error_msg)
                    failed += 1

            except Exception as e:
                print(f"  [ERROR] {e}")
                failed += 1
                continue

        # 6. Итоговая статистика
        print("\n" + "=" * 80)
        print("ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 80)
        print(f"Всего товаров: {len(all_products)}")
        print(f"Успешно сохранено: {successful}")
        print(f"Ошибок: {failed}")

    except Exception as e:
        print(f"\n[ERROR] Ошибка при выполнении: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if scraper:
            print("\nЗакрытие браузера...")
            scraper.close()

        print("\n" + "=" * 80)
        print("Парсинг завершен")
        print("=" * 80)

    # from sources.database.repository import ProductRepository
    # from sources.database.config import get_database_url
    # from sources.mail.mail_templates import format_first_contact_email

    # # Get products from database
    # repo = ProductRepository(get_database_url())
    # products = repo.get_all()

    # if not products:
    #     print("No products found in database")
    # else:
    #     print(f"Found {len(products)} products in database")

    #     # Generate email in different languages
    #     for lang in ["ru", "uk", "en"]:
    #         email = format_first_contact_email(products[0:2], language=lang)
    #         print(f"\n{'=' * 60}")
    #         print(f"Language: {lang.upper()}")
    #         print(f"{'=' * 60}")
    #         print(f"Subject: {email.subject}")
    #         print(f"\n{email.body}")


if __name__ == "__main__":
    main()

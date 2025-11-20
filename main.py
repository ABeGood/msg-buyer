"""
Точка входа в проект MSG Buyer
Парсинг товаров с сайта rrr.lt и сохранение в БД
"""
import time
from sources.scrapers.rrr_scraper import RRRScraper
from sources.parsers.rrr.steering_rack_parser import RRRSteeringRackParser
from sources.database.repository import ProductRepository
from sources.database.config import get_database_url


def main():
    """
    Основная функция для запуска парсинга и сохранения в БД
    """
    print("=" * 80)
    print("MSG Buyer - Парсинг товаров Steering Rack и сохранение в БД")
    print("=" * 80)
    
    scraper = None
    
    try:
        # 1. Инициализация скрапера
        print("\n[1] Инициализация скрапера...")
        scraper = RRRScraper(headless=False)
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
        
        # 3. Открытие страницы steering rack
        print("\n[3] Открытие страницы steering rack...")
        url = "https://rrr.lt/en/parts-list/front-axle/driving-mechanism/steering-rack"
        success = scraper.get_page(url)
        
        if not success:
            print("  [ERROR] Не удалось загрузить страницу")
            return
        
        print("  [OK] Страница открыта")
        
        # 4. Ожидание загрузки JavaScript
        print("\n[4] Ожидание загрузки JavaScript...")
        time.sleep(15)  # Даем время на загрузку динамического контента
        print("  [OK] JavaScript загружен")
        
        # 5. Получение HTML и парсинг списка товаров
        print("\n[5] Парсинг списка товаров...")
        html = scraper.get_page_html()
        parser = RRRSteeringRackParser()
        products = parser.parse_product_list(html)
        print(f"  [OK] Найдено товаров: {len(products)}")
        
        if not products:
            print("  [WARNING] Товары не найдены")
            return
        
        # 6. Берем первые 3 товара
        products_to_process = products[:3]
        print(f"\n[6] Обработка первых {len(products_to_process)} товаров...")
        
        successful = 0
        failed = 0
        
        # 7. Обработка каждого товара
        for i, product in enumerate(products_to_process, 1):
            print(f"\n{'=' * 80}")
            print(f"ТОВАР {i}/{len(products_to_process)}: {product.part_id} ({product.code})")
            print(f"{'=' * 80}")
            
            if not product.url:
                print(f"  [SKIP] Нет URL для товара")
                failed += 1
                continue
            
            try:
                # 7.1. Переход на страницу товара
                print(f"  [1] Переход на страницу товара...")
                print(f"      URL: {product.url}")
                scraper.get_page(product.url)
                time.sleep(15)  # Даем время на загрузку
                print(f"      [OK] Страница загружена")
                
                # 7.2. Извлечение детальной информации
                print(f"  [2] Извлечение детальной информации...")
                detail_data = parser.parse_product_detail_enhanced(scraper.driver)
                
                # 7.3. Обновление объекта Product
                product.item_description = detail_data.get('item_description', {})
                product.car_details = detail_data.get('car_details', {})
                product.seller_info = detail_data.get('seller_info', {})
                product.images = detail_data.get('images', [])
                
                print(f"      [OK] Данные извлечены:")
                print(f"        - Item Description: {len(product.item_description)} полей")
                print(f"        - Car Details: {len(product.car_details)} полей")
                print(f"        - Seller Info: {len(product.seller_info)} полей")
                print(f"        - Images: {len(product.images)} изображений")
                
                # 7.4. Сохранение в БД
                print(f"  [3] Сохранение в БД...")
                if repository.save(product):
                    print(f"      [OK] Товар сохранен в БД")
                    successful += 1
                else:
                    print(f"      [ERROR] Не удалось сохранить товар в БД")
                    failed += 1
                
            except Exception as e:
                print(f"  [ERROR] Ошибка при обработке товара: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
                continue
        
        # 8. Итоговая статистика
        print("\n" + "=" * 80)
        print("ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 80)
        print(f"\nОбработано товаров: {len(products_to_process)}")
        print(f"Успешно сохранено: {successful}")
        print(f"Ошибок: {failed}")
        
        print("\nБраузер останется открытым на 5 секунд...")
        time.sleep(5)
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка при выполнении: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 9. Закрытие браузера
        if scraper:
            print("\n[9] Закрытие браузера...")
            scraper.close()
            print("  [OK] Браузер закрыт")
        
        print("\n" + "=" * 80)
        print("Парсинг завершен")
        print("=" * 80)


if __name__ == "__main__":
    main()


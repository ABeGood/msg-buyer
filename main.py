"""
Точка входа в проект MSG Buyer
Парсинг товаров с сайта rrr.lt и сохранение в БД
"""
from sources.scrapers import SeleniumBaseScraper
from sources.parsers.rrr.steering_rack_parser import RRRSteeringRackParser
from sources.database.repository import ProductRepository
from sources.database.config import get_database_url
from sources.utils.logger import setup_logger

# Настройка логирования
logger = setup_logger("main")


def main():
    """
    Основная функция для запуска парсинга и сохранения в БД
    """
    print("=" * 80)
    print("MSG Buyer - Парсинг товаров Steering Rack и сохранение в БД")
    print("=" * 80)
    
    scraper = None
    
    logger.info("=" * 80)
    logger.info("Запуск MSG Buyer - Парсинг товаров Steering Rack")
    logger.info("=" * 80)
    
    try:
        # 1. Инициализация скрапера
        print("\n[1] Инициализация скрапера...")
        logger.info("Инициализация скрапера")
        scraper = SeleniumBaseScraper(headless=False)
        scraper.start()
        print("  [OK] Скрапер готов")
        logger.info("Скрапер успешно инициализирован")
        
        # 2. Инициализация репозитория БД
        print("\n[2] Инициализация подключения к БД...")
        logger.info("Инициализация подключения к БД")
        database_url = get_database_url()
        if not database_url:
            error_msg = "DATABASE_URL не найден. Проверьте файл .env"
            print(f"  [ERROR] {error_msg}")
            logger.error(error_msg)
            return
        
        logger.info("Подключение к БД установлено")
        repository = ProductRepository(database_url)
        repository.create_tables()
        print("  [OK] Подключение к БД установлено")
        
        # 3. Открытие страницы steering rack
        print("\n[3] Открытие страницы steering rack...")
        url = "https://rrr.lt/en/parts-list/front-axle/driving-mechanism/steering-rack"
        logger.info(f"Открытие страницы: {url}")
        success = scraper.get_page(url)
        
        if not success:
            error_msg = "Не удалось загрузить страницу"
            print(f"  [ERROR] {error_msg}")
            logger.error(error_msg)
            return
        
        print("  [OK] Страница открыта")
        logger.info("Страница успешно открыта")
        
        # 4. Ожидание загрузки динамического контента
        print("\n[4] Ожидание загрузки динамического контента...")
        logger.debug("Ожидание загрузки динамического контента (human_delay)")
        scraper.human_delay()  # Человекоподобная задержка для обхода защиты
        print("  [OK] Динамический контент загружен")
        logger.debug("Динамический контент загружен")
        
        # 5. Получение HTML и парсинг списка товаров
        print("\n[5] Парсинг списка товаров...")
        logger.info("Начало парсинга списка товаров")
        logger.debug("Получение HTML страницы")
        html = scraper.get_page_html()
        parser = RRRSteeringRackParser()
        logger.debug("Парсинг списка товаров из HTML")
        products = parser.parse_product_list(html)
        print(f"  [OK] Найдено товаров: {len(products)}")
        logger.info(f"Найдено товаров: {len(products)}")
        
        if not products:
            warning_msg = "Товары не найдены"
            print(f"  [WARNING] {warning_msg}")
            logger.warning(warning_msg)
            return
        
        # 6. Обрабатываем все найденные товары
        products_to_process = products
        print(f"\n[6] Обработка всех {len(products_to_process)} товаров...")
        logger.info(f"Начало обработки {len(products_to_process)} товаров")
        
        successful = 0
        failed = 0
        
        # 7. Обработка каждого товара
        for i, product in enumerate(products_to_process, 1):
            print(f"\n{'=' * 80}")
            print(f"ТОВАР {i}/{len(products_to_process)}: {product.part_id} ({product.code})")
            print(f"{'=' * 80}")
            logger.info(f"Обработка товара {i}/{len(products_to_process)}: part_id={product.part_id}, code={product.code}")
            
            if not product.url:
                warning_msg = f"Нет URL для товара {product.part_id}"
                print(f"  [SKIP] {warning_msg}")
                logger.warning(warning_msg)
                failed += 1
                continue
            
            try:
                # 7.1. Переход на страницу товара
                print(f"  [1] Переход на страницу товара...")
                print(f"      URL: {product.url}")
                logger.debug(f"Переход на страницу товара: {product.url}")
                scraper.get_page(product.url)
                logger.debug(f"Ожидание загрузки страницы товара {product.part_id} (human_delay)")
                scraper.human_delay()  # Человекоподобная задержка для обхода защиты
                print(f"      [OK] Страница загружена")
                logger.debug(f"Страница товара {product.part_id} загружена")
                
                # 7.2. Извлечение детальной информации
                print(f"  [2] Извлечение детальной информации...")
                logger.debug(f"Извлечение детальной информации для товара {product.part_id}")
                if not scraper.driver:
                    error_msg = "Driver не инициализирован"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                detail_data = parser.parse_product_detail_enhanced(scraper.driver)
                logger.debug(f"Детальная информация извлечена для товара {product.part_id}")
                
                # 7.3. Обновление объекта Product
                product.item_description = detail_data.get('item_description', {})
                product.car_details = detail_data.get('car_details', {})
                product.seller_email = detail_data.get('seller_email')
                product.images = detail_data.get('images', [])
                product.seller_comment = detail_data.get('seller_comment')  # Комментарий продавца о конкретном товаре
                
                seller_data = detail_data.get('seller_data', {})
                seller_comment = product.seller_comment  # Для вывода в консоль
                
                print(f"      [OK] Данные извлечены:")
                print(f"        - Item Description: {len(product.item_description)} полей")
                print(f"        - Car Details: {len(product.car_details)} полей")
                print(f"        - Seller Email: {product.seller_email or 'не найден'}")
                print(f"        - Seller Data: {len(seller_data)} полей")
                print(f"        - Seller Comment: {'найден' if seller_comment else 'не найден'}")
                print(f"        - Images: {len(product.images)} изображений")
                
                logger.debug(f"Данные извлечены для товара {product.part_id}: "
                           f"item_description={len(product.item_description)} полей, "
                           f"car_details={len(product.car_details)} полей, "
                           f"seller_email={product.seller_email or 'не найден'}, "
                           f"images={len(product.images)}")
                
                # 7.4. Сохранение товара и продавца в одной транзакции
                print(f"  [3] Сохранение товара и продавца в БД...")
                logger.info(f"Сохранение товара {product.part_id} и продавца в БД")
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
                error_msg = f"Ошибка при обработке товара {product.part_id}: {e}"
                print(f"  [ERROR] {error_msg}")
                logger.error(error_msg, exc_info=True)
                failed += 1
                continue
        
        # 8. Итоговая статистика
        print("\n" + "=" * 80)
        print("ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 80)
        print(f"\nОбработано товаров: {len(products_to_process)}")
        print(f"Успешно сохранено: {successful}")
        print(f"Ошибок: {failed}")
        
        logger.info("=" * 80)
        logger.info("ИТОГОВАЯ СТАТИСТИКА")
        logger.info(f"Обработано товаров: {len(products_to_process)}")
        logger.info(f"Успешно сохранено: {successful}")
        logger.info(f"Ошибок: {failed}")
        logger.info("=" * 80)
        
    except Exception as e:
        error_msg = f"Критическая ошибка при выполнении: {e}"
        print(f"\n[ERROR] {error_msg}")
        logger.critical(error_msg, exc_info=True)
    
    finally:
        # 10. Закрытие браузера
        if scraper:
            print("\n[10] Закрытие браузера...")
            logger.info("Закрытие браузера")
            scraper.close()
            print("  [OK] Браузер закрыт")
        
        print("\n" + "=" * 80)
        print("Парсинг завершен")
        print("=" * 80)
        logger.info("Парсинг завершен")


if __name__ == "__main__":
    main()


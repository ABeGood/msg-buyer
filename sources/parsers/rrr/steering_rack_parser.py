"""
Парсер для извлечения данных о steering rack товарах с сайта rrr.lt
"""
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sources.classes.product import Product


class RRRSteeringRackParser:
    """
    Парсер для извлечения данных о steering rack товарах
    
    Работает с HTML, полученным через Selenium,
    и парсит его через BeautifulSoup
    """
    
    def __init__(self):
        """Инициализация парсера"""
        pass
    
    def parse_product_list(self, html: str) -> List[Product]:
        """
        Парсинг списка товаров из HTML
        
        Args:
            html: HTML код страницы со списком товаров
            
        Returns:
            Список объектов Product с данными о товарах
        """
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        # Находим все карточки товаров
        # Нужно будет определить правильный селектор после анализа страницы
        product_elements = self._find_product_elements(soup)
        
        for element in product_elements:
            try:
                product = self._parse_product_card(element)
                if product:
                    products.append(product)
            except Exception as e:
                # При ошибке парсинга записываем частичные данные
                print(f"[WARNING] Ошибка парсинга товара: {e}")
                # Можно попробовать извлечь хотя бы базовые данные
                partial_product = self._parse_partial_product(element)
                if partial_product:
                    products.append(partial_product)
        
        return products
    
    def _find_product_elements(self, soup: BeautifulSoup) -> List:
        """
        Поиск элементов карточек товаров на странице
        
        Args:
            soup: BeautifulSoup объект
            
        Returns:
            Список элементов карточек товаров
        """
        # Пробуем разные селекторы для поиска товаров
        # Будем уточнять после анализа страницы
        
        # Вариант 1: По data-part-id (мы знаем, что это есть)
        elements = soup.find_all('span', class_='add-to-wishlist')
        
        # Если не нашли, пробуем другие варианты
        if not elements:
            # Вариант 2: По классу products
            elements = soup.find_all('div', class_='products__items')
        
        return elements
    
    def _parse_product_card(self, element) -> Optional[Product]:
        """
        Парсинг одной карточки товара
        
        Извлекает только необходимые поля: part_id, code, price, url
        
        Args:
            element: BeautifulSoup элемент карточки товара
            
        Returns:
            Product объект или None
        """
        # 1. Part ID (data-part-id)
        part_id = element.get('data-part-id') or self._find_in_parent(element, 'data-part-id')
        if not part_id:
            return None
        
        # 2. Code (data-code)
        code = element.get('data-code') or self._find_in_parent(element, 'data-code')
        
        # 3. Price (data-price)
        price = element.get('data-price') or self._find_in_parent(element, 'data-price')
        price_float = None
        if price:
            try:
                price_float = float(price)
            except:
                price_float = None
        
        # 4. URL товара - формируем из code
        # Формула: https://rrr.lt/en/used-part/ + code
        url = None
        if code:
            url = f"https://rrr.lt/en/used-part/{code.lower()}"
        
        # Создаем объект Product только с необходимыми полями
        product = Product(
            part_id=part_id,
            code=code,
            price=price_float,
            url=url,
            source_site='rrr.lt',
            category='steering-rack'
        )
        
        return product
    
    def _parse_partial_product(self, element) -> Optional[Product]:
        """
        Попытка извлечь хотя бы частичные данные при ошибке парсинга
        
        Args:
            element: BeautifulSoup элемент
            
        Returns:
            Product с частичными данными или None
        """
        try:
            part_id = element.get('data-part-id') or self._find_in_parent(element, 'data-part-id')
            if part_id:
                return Product(
                    part_id=part_id,
                    source_site='rrr.lt',
                    category='steering-rack'
                )
        except:
            pass
        return None
    
    def _find_in_parent(self, element, attr_name: str, max_depth: int = 5) -> Optional[str]:
        """
        Поиск атрибута в родительских элементах
        
        Args:
            element: Начальный элемент
            attr_name: Название атрибута
            max_depth: Максимальная глубина поиска
            
        Returns:
            Значение атрибута или None
        """
        current = element
        depth = 0
        
        while current and depth < max_depth:
            if current.get(attr_name):
                return current.get(attr_name)
            current = current.parent
            depth += 1
        
        return None
    
    def parse_product_detail(self, html: str) -> Dict[str, Any]:
        """
        Парсинг детальной страницы товара
        
        Извлекает ВСЕ доступные данные со страницы товара
        
        Args:
            html: HTML код страницы товара
            
        Returns:
            Словарь со всеми найденными данными о товаре
        """
        soup = BeautifulSoup(html, 'html.parser')
        product_data = {}
        
        # Извлекаем все возможные данные
        # Будем собирать все поля для последующего анализа
        
        # 1. Все data-атрибуты на странице
        all_data_attrs = self._extract_all_data_attributes(soup)
        product_data.update(all_data_attrs)
        
        # 2. Текст из различных элементов
        text_data = self._extract_text_elements(soup)
        product_data.update(text_data)
        
        # 3. Изображения
        images = self._extract_images(soup)
        if images:
            product_data['images'] = images
        
        # 4. Метаданные (meta tags)
        meta_data = self._extract_meta_tags(soup)
        product_data.update(meta_data)
        
        # 5. Структурированные данные (JSON-LD, микроразметка)
        structured_data = self._extract_structured_data(soup)
        if structured_data:
            product_data['structured_data'] = structured_data
        
        # 6. Таблицы и списки
        tables_data = self._extract_tables(soup)
        if tables_data:
            product_data['tables'] = tables_data
        
        # 7. Ссылки
        links = self._extract_links(soup)
        if links:
            product_data['links'] = links
        
        # 8. Все классы и ID элементов
        classes_and_ids = self._extract_classes_and_ids(soup)
        if classes_and_ids:
            product_data['element_structure'] = classes_and_ids
        
        return product_data
    
    def _extract_all_data_attributes(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Извлечение всех data-атрибутов"""
        data_attrs = {}
        
        # Находим все элементы с data-атрибутами
        def has_data_attr(tag):
            if not tag or not hasattr(tag, 'attrs'):
                return False
            return any(k.startswith('data-') for k in tag.attrs.keys())
        
        elements = soup.find_all(has_data_attr)
        
        for element in elements:
            if hasattr(element, 'attrs'):
                for attr_name, attr_value in element.attrs.items():
                    if attr_name.startswith('data-'):
                        if attr_name not in data_attrs:
                            data_attrs[attr_name] = []
                        if attr_value not in data_attrs[attr_name]:
                            data_attrs[attr_name].append(attr_value)
        
        # Преобразуем списки в одиночные значения, если они одинаковые
        for key, value in data_attrs.items():
            if len(value) == 1:
                data_attrs[key] = value[0]
        
        return data_attrs
    
    def _extract_text_elements(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Извлечение текста из различных элементов"""
        text_data = {}
        
        # Заголовки
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            elements = soup.find_all(tag)
            if elements:
                text_data[f'{tag}_text'] = [elem.get_text(strip=True) for elem in elements if elem.get_text(strip=True)]
        
        # Параграфы
        paragraphs = soup.find_all('p')
        if paragraphs:
            text_data['paragraphs'] = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
        
        # Списки
        lists = soup.find_all(['ul', 'ol'])
        if lists:
            text_data['lists'] = []
            for lst in lists:
                items = [li.get_text(strip=True) for li in lst.find_all('li') if li.get_text(strip=True)]
                if items:
                    text_data['lists'].append(items)
        
        # Элементы с классами, содержащими ключевые слова
        keywords = ['title', 'name', 'description', 'price', 'code', 'part', 'product', 'info', 'detail']
        for keyword in keywords:
            elements = soup.find_all(class_=lambda x: x and keyword in str(x).lower())
            if elements:
                text_data[f'class_{keyword}'] = [elem.get_text(strip=True) for elem in elements if elem.get_text(strip=True) and len(elem.get_text(strip=True)) < 500]
        
        return text_data
    
    def _extract_images(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Извлечение изображений"""
        images = []
        img_elements = soup.find_all('img')
        
        for img in img_elements:
            img_data = {}
            if img.get('src'):
                img_data['src'] = img.get('src')
            if img.get('alt'):
                img_data['alt'] = img.get('alt')
            if img.get('title'):
                img_data['title'] = img.get('title')
            if img.get('data-src'):
                img_data['data_src'] = img.get('data-src')
            if hasattr(img, 'attrs'):
                for attr in img.attrs:
                    if attr.startswith('data-'):
                        img_data[attr] = img.get(attr)
            
            if img_data:
                images.append(img_data)
        
        return images
    
    def _extract_meta_tags(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Извлечение мета-тегов"""
        meta_data = {}
        meta_tags = soup.find_all('meta')
        
        for meta in meta_tags:
            name = meta.get('name') or meta.get('property') or meta.get('itemprop')
            content = meta.get('content')
            if name and content:
                meta_data[f'meta_{name}'] = content
        
        return meta_data
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Извлечение структурированных данных (JSON-LD, микроразметка)"""
        structured_data = {}
        
        # JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        if json_ld_scripts:
            structured_data['json_ld'] = []
            for script in json_ld_scripts:
                if script.string:
                    try:
                        import json
                        data = json.loads(script.string)
                        structured_data['json_ld'].append(data)
                    except:
                        pass
        
        # Микроразметка (schema.org)
        def has_itemtype(tag):
            if not tag or not hasattr(tag, 'attrs'):
                return False
            return 'itemtype' in tag.attrs
        
        schema_elements = soup.find_all(has_itemtype)
        if schema_elements:
            structured_data['schema_org'] = []
            for elem in schema_elements:
                schema_data = {}
                if elem.get('itemtype'):
                    schema_data['itemtype'] = elem.get('itemtype')
                if elem.get('itemprop'):
                    schema_data['itemprop'] = elem.get('itemprop')
                if elem.get('itemscope'):
                    schema_data['itemscope'] = elem.get('itemscope')
                if schema_data:
                    structured_data['schema_org'].append(schema_data)
        
        return structured_data if structured_data else None
    
    def _extract_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Извлечение данных из таблиц"""
        tables_data = []
        tables = soup.find_all('table')
        
        for table in tables:
            table_data = {'headers': [], 'rows': []}
            
            # Заголовки
            headers = table.find_all('th')
            if headers:
                table_data['headers'] = [th.get_text(strip=True) for th in headers]
            
            # Строки
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    table_data['rows'].append(row_data)
            
            if table_data['rows']:
                tables_data.append(table_data)
        
        return tables_data if tables_data else None
    
    def _extract_links(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Извлечение ссылок"""
        links = []
        link_elements = soup.find_all('a', href=True)
        
        for link in link_elements:
            link_data = {}
            if link.get('href'):
                link_data['href'] = link.get('href')
            if link.get_text(strip=True):
                link_data['text'] = link.get_text(strip=True)
            if link.get('class'):
                link_data['class'] = link.get('class')
            if link_data:
                links.append(link_data)
        
        return links if links else None
    
    def _extract_classes_and_ids(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Извлечение структуры классов и ID"""
        structure = {'classes': set(), 'ids': set()}
        
        # Все классы
        elements_with_class = soup.find_all(class_=True)
        for elem in elements_with_class:
            if elem.get('class'):
                for cls in elem.get('class'):
                    structure['classes'].add(cls)
        
        # Все ID
        elements_with_id = soup.find_all(id=True)
        for elem in elements_with_id:
            if elem.get('id'):
                structure['ids'].add(elem.get('id'))
        
        # Преобразуем sets в lists
        structure['classes'] = list(structure['classes'])
        structure['ids'] = list(structure['ids'])
        
        return structure if (structure['classes'] or structure['ids']) else None
    
    def parse_product_detail_enhanced(self, driver: WebDriver) -> Dict[str, Any]:
        """
        Расширенный парсинг детальной страницы товара с использованием Selenium
        
        Извлекает структурированные данные: item_description, car_details, seller_info, images
        
        Args:
            driver: Selenium WebDriver с открытой страницей товара
            
        Returns:
            Словарь с данными: item_description, car_details, seller_info, images
        """
        result = {
            'item_description': {},
            'car_details': {},
            'seller_info': {},
            'images': []
        }
        
        try:
            # Извлекаем Item description
            result['item_description'] = self._extract_item_description(driver)
        except Exception as e:
            print(f"[WARNING] Ошибка извлечения Item description: {e}")
        
        try:
            # Извлекаем Car details
            result['car_details'] = self._extract_car_details(driver)
        except Exception as e:
            print(f"[WARNING] Ошибка извлечения Car details: {e}")
        
        try:
            # Извлекаем Seller info
            result['seller_info'] = self._extract_seller_info(driver)
        except Exception as e:
            print(f"[WARNING] Ошибка извлечения Seller info: {e}")
        
        try:
            # Извлекаем Images
            result['images'] = self._extract_images(driver)
        except Exception as e:
            print(f"[WARNING] Ошибка извлечения Images: {e}")
        
        return result
    
    def _extract_item_description(self, driver: WebDriver) -> Dict[str, Any]:
        """Извлечение Item description"""
        item_description = {}
        
        try:
            wait = WebDriverWait(driver, 2)
            heading = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//h3[contains(text(), 'Item description')] | //h4[contains(text(), 'Item description')]")
            ))
            
            container = heading.find_element(By.XPATH, "./ancestor::div[contains(@class, 'Mui')]")
            table = container.find_element(By.TAG_NAME, "table")
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) == 2:
                    key = cells[0].text.strip()
                    value = cells[1].text.strip()
                    if key and value:
                        if key == "Manufacturer code":
                            item_description['manufacturer_code'] = value
                        elif key == "OEM Code":
                            item_description['oem_code'] = value
                        elif key == "Other codes":
                            item_description['other_codes'] = value
                        elif key == "Condition":
                            item_description['condition'] = value
        
        except Exception as e:
            print(f"[WARNING] Ошибка парсинга Item description: {e}")
        
        return item_description
    
    def _extract_car_details(self, driver: WebDriver) -> Dict[str, Any]:
        """Извлечение Car details"""
        car_details = {}
        
        field_mapping = {
            'Make': 'make',
            'Series': 'series',
            'Model': 'model',
            'Year': 'year',
            'Engine capacity': 'engine_capacity',
            'Engine capacity, cm³': 'engine_capacity',
            'Engine capacity, cm3': 'engine_capacity',
            'Gearbox code': 'gearbox_code',
            'Mileage': 'mileage',
            'Mileage, km': 'mileage',
            'km': 'mileage_unit',
            'VIN code': 'vin_code'
        }
        
        # Метод 1: Через селектор
        try:
            selector = "body > div.MuiBox-root.mui-oqf2yl > div > div.MuiContainer-root.MuiContainer-disableGutters.mui-bay56u > div.MuiPaper-root.MuiPaper-elevation.MuiPaper-rounded.MuiPaper-elevation3.MuiCard-root.mui-1egwvqv > div > div.MuiBox-root.mui-oapo5e > div.MuiBox-root.mui-dztwg9 > div:nth-child(2) > div"
            wait = WebDriverWait(driver, 2)
            car_details_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            table = car_details_container.find_element(By.TAG_NAME, "table")
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) == 2:
                    key = cells[0].text.strip()
                    value = cells[1].text.strip()
                    if key and value:
                        field_name = field_mapping.get(key, key.lower().replace(' ', '_'))
                        car_details[field_name] = value
            
            if car_details:
                return car_details
        except:
            pass
        
        # Метод 2: Через заголовок "Car details"
        try:
            wait = WebDriverWait(driver, 2)
            heading = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//h3[contains(text(), 'Car details')] | //h4[contains(text(), 'Car details')]")
            ))
            
            # Ищем все таблицы на странице
            all_tables = driver.find_elements(By.TAG_NAME, "table")
            
            # Находим таблицу Car details по содержимому
            for table in all_tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                if not rows:
                    continue
                
                # Проверяем первую строку на наличие полей Car details
                first_row = rows[0]
                cells = first_row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    first_cell = cells[0].text.strip()
                    # Если первая ячейка содержит поля Car details, это наша таблица
                    if first_cell in ['Make', 'Series', 'Model', 'Year', 'Engine capacity']:
                        # Это таблица Car details
                        for row in rows:
                            row_cells = row.find_elements(By.TAG_NAME, "td")
                            if len(row_cells) == 2:
                                key = row_cells[0].text.strip()
                                value = row_cells[1].text.strip()
                                if key and value:
                                    field_name = field_mapping.get(key, key.lower().replace(' ', '_'))
                                    car_details[field_name] = value
                        
                        if car_details:
                            return car_details
            
        except Exception as e:
            pass
        
        # Метод 3: Поиск всех таблиц и выбор нужной
        try:
            all_tables = driver.find_elements(By.TAG_NAME, "table")
            
            for table in all_tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                if not rows:
                    continue
                
                # Проверяем первую строку на наличие полей Car details
                first_row = rows[0]
                cells = first_row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    first_cell = cells[0].text.strip()
                    if first_cell in ['Make', 'Series', 'Model', 'Year']:
                        # Это таблица Car details
                        temp_details = {}
                        for row in rows:
                            row_cells = row.find_elements(By.TAG_NAME, "td")
                            if len(row_cells) == 2:
                                key = row_cells[0].text.strip()
                                value = row_cells[1].text.strip()
                                if key and value:
                                    field_name = field_mapping.get(key, key.lower().replace(' ', '_'))
                                    temp_details[field_name] = value
                        
                        if temp_details:
                            car_details = temp_details
                            return car_details
        except:
            pass
        
        # Метод 4: Парсинг через BeautifulSoup (данные могут быть в HTML, но не в таблицах)
        try:
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Ищем заголовок "Car details"
            heading = soup.find(['h3', 'h4'], string=lambda x: x and 'car details' in str(x).lower())
            
            if heading:
                # Ищем все таблицы после заголовка
                all_tables = soup.find_all('table')
                
                for table in all_tables:
                    rows = table.find_all('tr')
                    if not rows:
                        continue
                    
                    # Проверяем первую строку
                    first_row = rows[0]
                    cells = first_row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        first_cell_text = cells[0].get_text(strip=True)
                        # Если это поля Car details
                        if first_cell_text in ['Make', 'Series', 'Model', 'Year', 'Engine capacity']:
                            for row in rows:
                                row_cells = row.find_all(['td', 'th'])
                                if len(row_cells) == 2:
                                    key = row_cells[0].get_text(strip=True)
                                    value = row_cells[1].get_text(strip=True)
                                    if key and value:
                                        # Очищаем ключ от запятых и лишних символов
                                        clean_key = key.replace(',', '').strip()
                                        field_name = field_mapping.get(clean_key) or field_mapping.get(key) or clean_key.lower().replace(' ', '_').replace('³', '3')
                                        
                                        # Обработка специальных случаев
                                        if 'mileage' in field_name.lower() and 'km' in value.lower():
                                            # Разделяем mileage и km
                                            parts = value.split()
                                            if len(parts) >= 2:
                                                car_details['mileage'] = parts[0]
                                                car_details['mileage_unit'] = parts[1]
                                            else:
                                                car_details[field_name] = value
                                        else:
                                            car_details[field_name] = value
                            
                            if car_details:
                                return car_details
        except Exception as e:
            pass
        
        return car_details
    
    def _extract_seller_info(self, driver: WebDriver) -> Dict[str, Any]:
        """Извлечение Seller info"""
        seller_info = {}
        
        try:
            wait = WebDriverWait(driver, 2)
            
            # Ищем контейнер продавца
            seller_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".mui-eti4d7, .mui-hwcfm4")))
            seller_text = seller_container.text
            lines = [line.strip() for line in seller_text.split('\n') if line.strip()]
            
            # Ищем название продавца (обычно это "Ovoko, UAB" или другое название компании)
            for line in lines:
                if 'Top Seller' in line or 'Seller' in line:
                    seller_info['rating'] = line
                elif line in ['France', 'Poland', 'Lithuania', 'Germany', 'Spain', 'Italy', 'Finland', 'Romania']:
                    seller_info['country'] = line
                elif line and not any(x in line for x in ['€', 'Delivery', 'BUY', 'SKU', 'Incl.', 'Service', '14-day', 'Free', 'Quick', 'Renault', 'Steering', 'rack']):
                    # Это должно быть название продавца
                    if 'name' not in seller_info and len(line) < 100:
                        seller_info['name'] = line
            
            # Если название не найдено, пробуем найти по тексту "Ovoko"
            if 'name' not in seller_info:
                ovoko_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Ovoko')]")
                for elem in ovoko_elements:
                    text = elem.text.strip()
                    if 'Ovoko' in text and len(text) < 50:
                        seller_info['name'] = text
                        break
            
            # Ищем рейтинг звезд
            rating_selector = "body > div.MuiBox-root.mui-oqf2yl > div > div.MuiContainer-root.MuiContainer-disableGutters.mui-bay56u > div.MuiPaper-root.MuiPaper-elevation.MuiPaper-rounded.MuiPaper-elevation3.MuiCard-root.mui-1egwvqv > div > div.MuiBox-root.mui-hwcfm4 > div > div.MuiBox-root.mui-eti4d7 > div > div > span.MuiRating-root.MuiRating-sizeMedium.Mui-readOnly.MuiRating-readOnly.mui-dabo6s"
            
            try:
                rating_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, rating_selector)))
                rating_value = rating_element.get_attribute('value') or rating_element.get_attribute('aria-label')
                
                if rating_value:
                    import re
                    numbers = re.findall(r'\d+\.?\d*', rating_value)
                    if numbers:
                        seller_info['stars'] = float(numbers[0])
                
                if 'stars' not in seller_info:
                    active_stars = rating_element.find_elements(By.CSS_SELECTOR, "[class*='MuiRating-iconFilled'], [class*='MuiRating-iconActive']")
                    if active_stars:
                        seller_info['stars'] = len(active_stars)
            except:
                pass
        
        except Exception as e:
            print(f"[WARNING] Ошибка парсинга Seller info: {e}")
        
        return seller_info
    
    def _extract_images(self, driver: WebDriver) -> List[str]:
        """Извлечение изображений"""
        images = []
        
        try:
            # Ищем изображения товара
            img_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='part-image']")
            
            if not img_elements:
                img_elements = driver.find_elements(By.CSS_SELECTOR, ".part-image, .image-gallery img, [class*='part-image']")
            
            for img in img_elements:
                src = img.get_attribute('src')
                if src and src not in images:
                    images.append(src)
            
            # Также пробуем data-src для lazy loading
            lazy_imgs = driver.find_elements(By.CSS_SELECTOR, "[data-src]")
            for img in lazy_imgs:
                src = img.get_attribute('data-src')
                if src and src not in images:
                    images.append(src)
            
            # Фильтруем дубликаты (убираем разные размеры одного изображения)
            # Оставляем только уникальные базовые URL
            unique_images = []
            seen_bases = set()
            
            for img_url in images:
                # Извлекаем базовый URL без размеров
                base_url = img_url.split('/tr/')[0] if '/tr/' in img_url else img_url.split('/br/')[0] if '/br/' in img_url else img_url
                base_url = base_url.split('/130x103/')[0] if '/130x103/' in base_url else base_url.split('/99x74/')[0] if '/99x74/' in base_url else base_url
                
                if base_url not in seen_bases:
                    seen_bases.add(base_url)
                    # Берем версию с максимальным размером если есть
                    if '/1024x768/' in img_url:
                        unique_images.append(img_url)
                    elif '/fill/' in img_url:
                        unique_images.append(img_url)
                    else:
                        unique_images.append(img_url)
            
            return unique_images
        
        except Exception as e:
            print(f"[WARNING] Ошибка парсинга Images: {e}")
            return []
    

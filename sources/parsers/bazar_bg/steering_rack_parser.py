import sys
import os

# Add project root to path when running as standalone script
if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    sys.path.insert(0, project_root)

from typing import List, Optional
from bs4 import BeautifulSoup
from sources.classes.product import Product


class BazarBGSteeringRackParser:
    """Parser for steering rack products from bazar.bg"""

    BASE_URL = "https://bazar.bg"
    CATALOG_URL = "https://bazar.bg/obiavi/rezervni-chasti/kormilna-sistema/reyka"
    # KEYWORDS = ["Кормилна", "рейка"]
    KEYWORDS = ["рейка"]

    def __init__(self):
        self.source_site = "bazar.bg"
        self.category = "steering_rack"

    def parse_product_list(self, html: str) -> List[str]:
        """
        Parse catalog page and return list of URLs for relevant products.
        Filters products containing 'Кормилна' or 'рейка' in title.

        Args:
            html: HTML content of catalog page

        Returns:
            List of product URLs
        """
        soup = BeautifulSoup(html, 'html.parser')
        product_urls = []

        product_elements = self._find_product_elements(soup)

        for element in product_elements:
            url = self._parse_product_card(element)
            if url:
                product_urls.append(url)

        return product_urls

    def _find_product_elements(self, soup: BeautifulSoup) -> list:
        """
        Find all product card elements in the catalog page.
        Excludes hidden skeleton cards.

        Args:
            soup: BeautifulSoup object of catalog page

        Returns:
            List of product card elements
        """
        # Find all product cards, excluding hidden ones (skeleton templates)
        all_cards = soup.select('div.listItemContainer.listItemContainerV2')

        # Filter out hidden cards
        visible_cards = [
            card for card in all_cards
            if not (card.get('style') and 'display: none' in card.get('style', ''))
        ]

        return visible_cards

    def _parse_product_card(self, element) -> Optional[str]:
        """
        Parse a single product card and extract URL if it matches keywords.

        Args:
            element: BeautifulSoup element of product card

        Returns:
            Product URL if keywords match, None otherwise
        """
        # Find the link element
        link = element.select_one('a.listItemLink')
        if not link:
            return None

        # Get title from the title attribute or span.title
        title = link.get('title', '')
        if not title:
            title_span = element.select_one('span.title')
            if title_span:
                title = title_span.get_text(strip=True)

        # Check if title contains any of the keywords
        if not self._matches_keywords(title):
            return None

        # Get relative URL and convert to absolute
        href = link.get('href', '')
        if not href:
            return None

        # Build full URL
        if href.startswith('/'):
            full_url = f"{self.BASE_URL}{href}"
        else:
            full_url = href

        return full_url

    def _matches_keywords(self, text: str) -> bool:
        """
        Check if text contains any of the required keywords.

        Args:
            text: Text to check

        Returns:
            True if any keyword is found, False otherwise
        """
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.KEYWORDS)

    def get_next_page_url(self, current_page: int) -> str:
        """
        Get URL for the next catalog page.

        Args:
            current_page: Current page number

        Returns:
            URL for next page
        """
        next_page = current_page + 1
        return f"https://bazar.bg/obiavi/rezervni-chasti/kormilna-sistema/reyka?page={next_page}"

    def has_products(self, html: str) -> bool:
        """
        Check if catalog page has any products.

        Args:
            html: HTML content of catalog page

        Returns:
            True if page has products, False otherwise
        """
        soup = BeautifulSoup(html, 'html.parser')
        product_elements = self._find_product_elements(soup)
        return len(product_elements) > 0

    def parse_product_details(self, html: str, url: str) -> Optional[Product]:
        """
        Parse detailed product information from product page.

        Args:
            html: HTML content of product page
            url: Product URL

        Returns:
            Product object with detailed information or None
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Extract part_id from title (Обява XXXXXXXX)
        part_id = None
        title_elem = soup.select_one('h1.classifiedTitle span')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            # Extract numbers from "Обява 50821577"
            import re
            match = re.search(r'\d+', title_text)
            if match:
                part_id = match.group()

        if not part_id:
            return None

        # Extract product title
        title = None
        title_elem = soup.select_one('h1.classifiedTitle')
        if title_elem:
            # Remove the "Обява XXXX" part
            title_full = title_elem.get_text(strip=True)
            title = title_full.split('→')[0].strip() if '→' in title_full else title_full

        # Extract price (in EUR)
        price = None
        price_elem = soup.select_one('.adPrice .current-price')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            # Extract EUR price (after separator, before €)
            # Example: "200 лв \n 102,26 €"
            import re
            eur_match = re.search(r'([\d,]+)\s*€', price_text)
            if eur_match:
                try:
                    # Replace comma with dot for decimal point
                    price = float(eur_match.group(1).replace(',', '.'))
                except ValueError:
                    pass

        # Extract location
        location = None
        location_elem = soup.select_one('a.location span')
        if location_elem:
            location = location_elem.get_text(strip=True)

        # Extract description
        description = None
        desc_elem = soup.select_one('div[itemprop="description"]')
        if desc_elem:
            description = desc_elem.get_text(strip=True)

        # Extract images
        images = []
        img_elements = soup.select('span.gallery-element img.picture')
        for img in img_elements:
            img_src = img.get('src', '')
            if img_src and img_src.startswith('//'):
                img_src = 'https:' + img_src
            if img_src and img_src not in images:
                images.append(img_src)

        # Extract parameters (Състояние, Доставка, etc.)
        item_description = {}
        param_rows = soup.select('.adParameters .productInfo')
        for row in param_rows:
            key_elem = row.select_one('.span4')
            value_elem = row.select_one('.span8 span')
            if key_elem and value_elem:
                key = key_elem.get_text(strip=True)
                value = value_elem.get_text(strip=True)
                item_description[key] = value

        # Extract seller phone (if visible)
        seller_phone = None
        phone_elem = soup.select_one('a.adConnectButtonPhone')
        if phone_elem:
            phone_text = phone_elem.get_text(strip=True)
            # Clean phone number
            import re
            phone_match = re.search(r'[\d\s]+', phone_text)
            if phone_match:
                seller_phone = phone_match.group().replace(' ', '')

        # Extract seller name and info
        seller_info = {}
        seller_name_elem = soup.select_one('a.usrName')
        if seller_name_elem:
            seller_info['name'] = seller_name_elem.get_text(strip=True)
            seller_info['profile_url'] = seller_name_elem.get('href', '')

        if seller_phone:
            seller_info['phone'] = seller_phone

        # Create Product object
        product = Product(
            part_id=part_id,
            code=part_id,  # Using part_id as code for BazarBG
            price=price,
            url=url,
            source_site=self.source_site,
            category=self.category,
            item_description={
                'title': title,
                'location': location,
                'parameters': item_description
            },
            car_details={},  # BazarBG doesn't have structured car details like RRR
            seller_email=None,  # No email on page, would need to extract from contact form
            images=images,
            seller_comment=description
        )

        # Store seller info separately (can be used to populate seller_info field)
        product.seller_info = seller_info

        return product


if __name__ == "__main__":
    import sys
    import os
    import time
    import json
    from datetime import datetime

    # Add project root to path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    sys.path.insert(0, project_root)

    from sources.scrapers.bazar_bg_scraper import BazarBGScraper

    parser = BazarBGSteeringRackParser()
    all_product_urls = []
    all_products = []

    # STEP 1: Scrape catalog pages to collect product URLs
    print("=" * 60)
    print("STEP 1: Scraping catalog pages")
    print("=" * 60)

    with BazarBGScraper(headless=False) as scraper:
        current_page = 0
        max_pages = 10  # Limit for testing

        while current_page < max_pages:
            # Get URL for current page
            if current_page == 0:
                url = parser.CATALOG_URL
            else:
                url = parser.get_next_page_url(current_page)

            print(f"\n--- Scraping catalog page {current_page + 1}: {url} ---")

            # Load page
            if not scraper.get_page(url, timeout=15):
                print(f"Failed to load page {current_page + 1}")
                break

            # Wait a bit for dynamic content
            time.sleep(1.5)

            # Get HTML
            html = scraper.get_page_html()

            # Check if page has products
            if not parser.has_products(html):
                print(f"No products found on page {current_page + 1}, stopping.")
                break

            # Parse product URLs
            product_urls = parser.parse_product_list(html)
            print(f"Found {len(product_urls)} relevant products on page {current_page + 1}")

            all_product_urls.extend(product_urls)

            current_page += 1

    print(f"\n\nTotal product URLs collected: {len(all_product_urls)}")

    # STEP 2: Scrape individual product pages
    print("\n" + "=" * 60)
    print("STEP 2: Scraping individual product pages")
    print("=" * 60)

    max_products_to_scrape = 600  # Limit for testing

    with BazarBGScraper(headless=False) as scraper:
        for i, product_url in enumerate(all_product_urls[:max_products_to_scrape], 1):
            print(f"\n--- Scraping product {i}/{min(len(all_product_urls), max_products_to_scrape)}: {product_url} ---")

            # Load product page with interactions
            html = scraper.scrape_product_page(product_url, click_phone=True, get_images=True)

            if not html:
                print(f"Failed to load product page: {product_url}")
                continue

            # Parse product details
            product = parser.parse_product_details(html, product_url)

            if product:
                all_products.append(product)
                print(f"✓ Product parsed successfully:")
                print(f"  ID: {product.part_id}")
                print(f"  Title: {product.item_description.get('title', 'N/A')}")
                print(f"  Price: {product.price} €")
                print(f"  Location: {product.item_description.get('location', 'N/A')}")
                print(f"  Images: {len(product.images)}")
                print(f"  Seller: {product.seller_info.get('name', 'N/A')}")
                if 'phone' in product.seller_info:
                    print(f"  Phone: {product.seller_info['phone']}")
            else:
                print(f"Failed to parse product: {product_url}")

            # Be nice to the server
            time.sleep(1.5)

    # Print final summary
    print("\n\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Total product URLs found: {len(all_product_urls)}")
    print(f"Total products scraped: {len(all_products)}")
    print(f"\nProduct details:")
    for i, product in enumerate(all_products, 1):
        print(f"\n{i}. {product.item_description.get('title', 'N/A')}")
        print(f"   ID: {product.part_id}")
        print(f"   Price: {product.price} €")
        print(f"   URL: {product.url}")

    # STEP 3: Save to JSON file
    if all_products:
        print("\n" + "=" * 60)
        print("STEP 3: Saving to JSON file")
        print("=" * 60)

        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"bazar_bg_products_{timestamp}.json")

        # Convert products to JSON-serializable format
        products_data = []
        for product in all_products:
            product_dict = {
                "part_id": product.part_id,
                "code": product.code,
                "price": product.price,
                "url": product.url,
                "source_site": product.source_site,
                "category": product.category,
                "item_description": product.item_description,
                "car_details": product.car_details,
                "seller_email": product.seller_email,
                "seller_comment": product.seller_comment,
                "images": product.images,
                "seller_info": product.seller_info if hasattr(product, 'seller_info') else {}
            }
            products_data.append(product_dict)

        # Save to JSON file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "scrape_date": datetime.now().isoformat(),
                "total_products": len(all_products),
                "products": products_data
            }, f, ensure_ascii=False, indent=2)

        print(f"✓ Saved {len(all_products)} products to: {output_file}")
        print(f"File size: {os.path.getsize(output_file)} bytes")

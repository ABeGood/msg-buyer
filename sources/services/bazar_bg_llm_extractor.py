"""
LLM-based data extraction pipeline for bazar.bg products

Extracts structured data from Bulgarian text using OpenAI GPT models:
- item_description: OEM codes, manufacturer codes, condition
- car_details: Make, model, year, and other vehicle information
"""

import os
import json
from typing import Dict, Any, Optional, List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class BazarBGLLMExtractor:
    """
    Extracts structured product and car data from bazar.bg listings using OpenAI LLM
    """

    def __init__(self, api_key: Optional[str] = None, use_advanced_vision: bool = False):
        """
        Initialize the extractor

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            use_advanced_vision: If True, use gpt-4o for better image processing (higher cost)
        """
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_TOKEN"))
        # Flag to enable advanced vision model (gpt-4o) for image processing
        self.use_advanced_vision = use_advanced_vision

    def extract_product_data(
        self,
        title: str,
        seller_comment: Optional[str] = None,
        image_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract structured product data from bazar.bg listing

        Args:
            title: Product title (Bulgarian)
            seller_comment: Seller's comment/description (Bulgarian)
            image_urls: List of product image URLs

        Returns:
            Dictionary with item_description and car_details
        """
        # Extract from text first (always use mini model)
        text_result = self._extract_from_text(title, seller_comment)

        # Extract from images if provided (use advanced model based on flag)
        has_images = image_urls and len(image_urls) > 0
        if has_images:
            image_result = self._extract_from_images(image_urls, title)
            # Merge results: image data takes precedence for part numbers
            merged_result = self._merge_extraction_results(text_result, image_result)
            return merged_result

        return text_result

    def _extract_from_text(self, title: str, seller_comment: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract data from text only using gpt-4o-mini

        Args:
            title: Product title
            seller_comment: Seller's comment

        Returns:
            Extracted data dictionary
        """
        prompt = self._build_extraction_prompt(title, seller_comment)

        messages = [
            {
                "role": "system",
                "content": """You are a data extraction specialist for automotive parts.
Extract structured information from Bulgarian text about automotive steering rack parts.
Return ONLY valid JSON, no additional text or markdown formatting.
All extracted text values must be translated to English.""",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Always use mini for text
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            print(f"Error extracting text data: {e}")
            return {"item_description": {}, "car_details": {}}

    def _extract_from_images(self, image_urls: List[str], title: str) -> Dict[str, Any]:
        """
        Extract data from images using vision model

        Args:
            image_urls: List of image URLs
            title: Product title for context

        Returns:
            Extracted data dictionary
        """
        # Choose model based on advanced vision flag
        model_to_use = "gpt-4o" if self.use_advanced_vision else "gpt-4o-mini"
        detail_level = "high" if self.use_advanced_vision else "low"

        messages = [
            {
                "role": "system",
                "content": """You are a data extraction specialist for automotive parts.
Extract part numbers, codes, and vehicle information visible in product images.
Focus on extracting: OEM codes, manufacturer codes, part numbers, VIN codes, labels, stickers.
Return ONLY valid JSON, no additional text or markdown formatting.""",
            },
            {
                "role": "user",
                "content": f"""Extract all visible part numbers, codes, and vehicle information from these images of a steering rack part.

Product title for context: {title}

Look for:
- OEM codes / part numbers on labels or stamped on the part
- Manufacturer codes
- Any alphanumeric codes visible on stickers or metal
- VIN codes if visible
- Vehicle make/model information on labels

Return JSON with this structure:
{{
  "item_description": {{
    "oem_code": "code if visible",
    "manufacturer_code": "code if visible",
    "other_codes": "any other codes visible"
  }},
  "car_details": {{
    "make": "if visible on labels",
    "model": "if visible on labels",
    "vin_code": "if visible"
  }}
}}

If no relevant information is visible in images, return empty objects.""",
            },
        ]

        # Add images (up to 3)
        for image_url in image_urls[:3]:
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url, "detail": detail_level},
                        }
                    ],
                }
            )

        try:
            response = self.client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            print(f"Error extracting image data: {e}")
            return {"item_description": {}, "car_details": {}}

    def _merge_extraction_results(
        self, text_result: Dict[str, Any], image_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge text and image extraction results
        Image data takes precedence for part numbers

        Args:
            text_result: Results from text extraction
            image_result: Results from image extraction

        Returns:
            Merged results
        """
        merged = {
            "item_description": {},
            "car_details": {}
        }

        # Merge item_description: prefer image data for codes, text for condition
        text_item = text_result.get("item_description", {})
        image_item = image_result.get("item_description", {})

        # Part codes: prefer image extraction (more accurate OCR)
        merged["item_description"]["oem_code"] = (
            image_item.get("oem_code") or text_item.get("oem_code") or "-"
        )
        merged["item_description"]["manufacturer_code"] = (
            image_item.get("manufacturer_code") or text_item.get("manufacturer_code") or "-"
        )
        merged["item_description"]["other_codes"] = (
            image_item.get("other_codes") or text_item.get("other_codes") or "-"
        )

        # Condition: only from text
        merged["item_description"]["condition"] = text_item.get("condition", "-")

        # Merge car_details: prefer text extraction (more complete)
        text_car = text_result.get("car_details", {})
        image_car = image_result.get("car_details", {})

        merged["car_details"] = {**text_car}  # Start with text data

        # Override with image data for VIN if found
        if image_car.get("vin_code"):
            merged["car_details"]["vin_code"] = image_car["vin_code"]

        return merged

    def _build_extraction_prompt(
        self, title: str, seller_comment: Optional[str] = None
    ) -> str:
        """
        Build the extraction prompt for the LLM

        Args:
            title: Product title
            seller_comment: Seller's comment

        Returns:
            Formatted prompt string
        """
        prompt = f"""Extract structured data from this Bulgarian automotive parts listing and translate to English.

**Title (Bulgarian):** {title}
"""

        if seller_comment:
            prompt += f"""
**Seller Comment (Bulgarian):** {seller_comment}
"""

        prompt += """

**Extract the following information:**

1. **item_description** - Part identification codes and condition:
   - oem_code: OEM/original part number (e.g., "1K1423055C", "07130199", "73613DE27F")
   - manufacturer_code: Manufacturer part number (e.g., "6C1423058E", "A1644600600", "974320ZF0")
   - other_codes: Alternative/compatible part numbers (e.g., "6900003928", "1K1423051CC")
   - condition: Condition of the part - translate to English ("New", "Used", "Refurbished")

2. **car_details** - Vehicle information (translate car make/model names to English):
   - make: Car manufacturer (e.g., "Volkswagen", "Peugeot", "Skoda", "Mercedes-Benz") - TRANSLATE TO ENGLISH
   - model: Car model (e.g., "Golf", "Octavia", "5008", "ML W164") - TRANSLATE TO ENGLISH
   - year: Year or year range (e.g., "2014", "2005-2009", "2010")
   - series: Car series if mentioned (e.g., "Mk3", "B6", "ML-class")
   - engine_capacity: Engine displacement in cc (e.g., "999", "1600", "2987")
   - engine_code: Engine code if mentioned (e.g., "DKRC", "BKD", "642820")
   - gearbox_type: "Manual" or "Automatic" - TRANSLATE TO ENGLISH
   - gearbox_code: Gearbox code if mentioned (e.g., "UDN", "722902")
   - fuel_type: "Gasoline", "Diesel", "Electric", etc. - TRANSLATE TO ENGLISH
   - steering_wheel_position: "Left" or "Right" - TRANSLATE TO ENGLISH (look for "ляв волан"/"десен волан")
   - vin_code: VIN number if mentioned
   - body_type: Body type if mentioned (e.g., "Hatchback", "Sedan", "SUV") - TRANSLATE TO ENGLISH
   - mileage: Mileage in km if mentioned
   - color: Color if mentioned - TRANSLATE TO ENGLISH
   - driving_wheels: "Front", "Rear", "AWD" - TRANSLATE TO ENGLISH

**Important instructions:**
- Extract ONLY information that is explicitly mentioned in the text or visible in images
- For fields not found, use "-" as the value or omit the field
- Part numbers should be exact as written (don't translate these)
- ALL text values (make, model, condition, etc.) MUST be in English
- Look for part numbers in formats like: номер XXXX, код XXXX, каталожен номер XXXX
- Bulgarian car makes: Рено→Renault, Пежо→Peugeot, Ситроен→Citroen, Фолксваген/VW→Volkswagen, Мерцедес→Mercedes-Benz, БМВ→BMW, Ауди→Audi, Опел→Opel, Форд→Ford, Фиат→Fiat, Шкода→Skoda, Сеат→Seat, Мазда→Mazda
- Return valid JSON with this structure:
{
  "item_description": {
    "oem_code": "...",
    "manufacturer_code": "...",
    "other_codes": "...",
    "condition": "..."
  },
  "car_details": {
    "make": "...",
    "model": "...",
    "year": "...",
    ...
  }
}
"""
        return prompt

    def process_batch(
        self, products: List[Dict[str, Any]], max_products: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of products and extract data

        Args:
            products: List of product dictionaries from bazar.bg scraper
            max_products: Maximum number of products to process (for testing)

        Returns:
            List of products with enhanced item_description and car_details
        """
        results = []
        products_to_process = (
            products[:max_products] if max_products else products
        )

        for i, product in enumerate(products_to_process, 1):
            print(f"Processing product {i}/{len(products_to_process)}: {product.get('part_id')}")

            title = product.get("item_description", {}).get("title", "")
            seller_comment = product.get("seller_comment", "")
            images = product.get("images", [])

            # Extract data
            extracted = self.extract_product_data(title, seller_comment, images)

            # Merge extracted data with original product
            enhanced_product = product.copy()

            # Update item_description (keep title and parameters from original)
            original_item_desc = enhanced_product.get("item_description", {})
            extracted_item_desc = extracted.get("item_description", {})
            enhanced_product["item_description"] = {
                **original_item_desc,  # Keep title, location, parameters
                **extracted_item_desc  # Add extracted codes and condition
            }

            # Update car_details
            enhanced_product["car_details"] = extracted.get("car_details", {})

            results.append(enhanced_product)

        return results


def main():
    """
    Example usage: Process first 5 products from the scraped JSON file
    """
    import sys

    # Check for --advanced-vision flag
    use_advanced = "--advanced-vision" in sys.argv or "-av" in sys.argv

    # Load scraped data
    input_file = "sources/parsers/bazar_bg/output/bazar_bg_products_20251229_033144.json"
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = data.get("products", [])

    # Initialize extractor
    print(f"Using model: {'gpt-4o (advanced vision)' if use_advanced else 'gpt-4o-mini (cost-effective)'}")
    extractor = BazarBGLLMExtractor(use_advanced_vision=use_advanced)

    # Process first 5 products
    print(f"Processing {min(5, len(products))} products...")
    # enhanced_products = extractor.process_batch(products, max_products=5)
    enhanced_products = extractor.process_batch(products)

    # Save results
    output_file = "sources/parsers/bazar_bg/output/bazar_bg_products_enhanced_sample.json"
    output_data = {
        "scrape_date": data.get("scrape_date"),
        "total_products": len(enhanced_products),
        "products": enhanced_products,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {output_file}")
    print("\nSample enhanced product:")
    print(json.dumps(enhanced_products[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

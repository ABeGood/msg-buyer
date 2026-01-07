"""
Upload enhanced bazar.bg products to the database

Reads the enhanced JSON file and uploads products to the products table
"""

import json
import sys
from sources.database.repository import ProductRepository
from sources.database.config import get_database_url
from sources.classes.product import Product


def upload_products_from_json(json_file_path: str, dry_run: bool = False):
    """
    Upload products from enhanced JSON file to database

    Args:
        json_file_path: Path to the enhanced JSON file
        dry_run: If True, only validate products without saving
    """
    # Load JSON data
    print(f"Loading products from: {json_file_path}")
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    products_data = data.get("products", [])
    print(f"Found {len(products_data)} products to upload")

    # Initialize repository
    repo = ProductRepository(get_database_url())

    # Statistics
    success_count = 0
    error_count = 0
    errors = []

    # Process each product
    for i, product_data in enumerate(products_data, 1):
        try:
            # Extract seller_phone from seller_info
            seller_info = product_data.get("seller_info", {})
            seller_phone = seller_info.get("phone")

            # Add prefix to part_id
            original_part_id = product_data.get("part_id")
            prefixed_part_id = f"bazar-bg-{original_part_id}"

            # Create Product object
            product = Product(
                part_id=prefixed_part_id,
                code=product_data.get("code"),
                price=product_data.get("price"),
                url=product_data.get("url"),
                source_site=product_data.get("source_site"),
                category=product_data.get("category"),
                item_description=product_data.get("item_description", {}),
                car_details=product_data.get("car_details", {}),
                seller_email=product_data.get("seller_email"),
                seller_phone=seller_phone,
                images=product_data.get("images", []),
                seller_comment=product_data.get("seller_comment"),
            )

            # Validate
            is_valid, error_msg = product.validate()
            if not is_valid:
                error_count += 1
                error_info = f"Product {product.part_id}: {error_msg}"
                errors.append(error_info)
                print(f"  ❌ [{i}/{len(products_data)}] {error_info}")
                continue

            # Save to database (unless dry_run)
            if dry_run:
                print(f"  ✓ [{i}/{len(products_data)}] Valid: {product.part_id}")
                success_count += 1
            else:
                saved = repo.save(product)
                if saved:
                    success_count += 1
                    print(f"  ✓ [{i}/{len(products_data)}] Saved: {product.part_id}")
                else:
                    error_count += 1
                    error_info = f"Product {product.part_id}: Failed to save"
                    errors.append(error_info)
                    print(f"  ❌ [{i}/{len(products_data)}] {error_info}")

        except Exception as e:
            error_count += 1
            error_info = f"Product {product_data.get('part_id', 'UNKNOWN')}: {str(e)}"
            errors.append(error_info)
            print(f"  ❌ [{i}/{len(products_data)}] {error_info}")

    # Print summary
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Total products: {len(products_data)}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No data was saved to database")

    if errors:
        print("\n" + "=" * 60)
        print("ERRORS:")
        print("=" * 60)
        for error in errors:
            print(f"  - {error}")


def main():
    """
    Main function - upload products from enhanced JSON file
    """
    # Default file path
    default_file = "sources/parsers/bazar_bg/output/bazar_bg_products_enhanced_sample.json"

    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv

    # Parse command line arguments (excluding flags)
    args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]

    if args:
        json_file = args[0]
    else:
        json_file = default_file

    print("=" * 60)
    print("BAZAR.BG PRODUCTS UPLOAD")
    print("=" * 60)
    print(f"Input file: {json_file}")
    print(f"Mode: {'DRY RUN (validation only)' if dry_run else 'LIVE (will save to database)'}")
    print("=" * 60)
    print()

    # Upload products
    upload_products_from_json(json_file, dry_run=dry_run)


if __name__ == "__main__":
    main()

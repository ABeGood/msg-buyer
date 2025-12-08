"""
Utilities for comparing product prices with catalogs
"""
import os
import pandas as pd
from typing import Optional, List, Dict, Any, Tuple
from sources.database.repository import ProductRepository, CompareRepository, CatalogMatchRepository
from sources.database.config import get_database_url
from sources.classes.product import Product
from sources.utils.logger import get_logger

logger = get_logger("compare_utils")

# Path to CSV files (relative to project root)
CSV_DIR = 'data/stocklists/'


def compare_products_with_catalog(
    table: str,
    price_delta_perc: float
) -> pd.DataFrame:
    """
    Compare product prices from DB with catalog (eur.csv or gur.csv)

    Args:
        table: Catalog table name ('gur' or 'eur')
        price_delta_perc: Multiplier for allowed price difference (e.g., 1.1 for +10%)

    Returns:
        DataFrame with found products and price classification
    """
    if table not in ('gur', 'eur'):
        raise ValueError(f"table must be 'gur' or 'eur', got: {table}")

    # Load CSV catalog
    csv_path = os.path.join(CSV_DIR, f"{table}.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Catalog file not found: {csv_path}")

    catalog_df = pd.read_csv(csv_path)
    logger.info(f"Loaded catalog {table}.csv: {len(catalog_df)} rows")

    # Get products from DB
    database_url = get_database_url()
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")

    repo = ProductRepository(database_url)
    products = repo.get_all()
    logger.info(f"Got {len(products)} products from DB")

    if not products:
        logger.warning("No products in DB to compare")
        return pd.DataFrame()

    # Search results
    found_items: List[Dict[str, Any]] = []

    for product in products:
        # Extract codes from item_description
        item_desc = product.item_description or {}
        oem_code = item_desc.get('oem_code', '')
        other_codes = item_desc.get('other_codes', [])
        manufacturer_code = item_desc.get('manufacturer_code', '')

        # Convert other_codes to list of strings
        if isinstance(other_codes, str):
            other_codes = [other_codes] if other_codes else []
        elif not isinstance(other_codes, list):
            other_codes = []

        # Search for matches in catalog
        match_result = _find_in_catalog(
            catalog_df,
            oem_code=oem_code,
            other_codes=other_codes,
            manufacturer_code=manufacturer_code,
            product=product
        )

        if match_result['found']:
            # Left join: for each matched catalog row, add the product data
            matched_rows = match_result['matched_rows'].copy()
            matched_rows['db_part_id'] = product.part_id
            matched_rows['db_code'] = product.code
            matched_rows['db_price'] = product.price
            matched_rows['db_url'] = product.url
            matched_rows['db_source_site'] = product.source_site
            matched_rows['db_category'] = product.category
            matched_rows['db_oem_code'] = oem_code
            matched_rows['db_other_codes'] = ' | '.join(other_codes) if other_codes else ''
            matched_rows['db_manufacturer_code'] = manufacturer_code
            matched_rows['matched_by'] = match_result['matched_by']
            matched_rows['matched_value'] = match_result['matched_value']

            found_items.append(matched_rows)

    if not found_items:
        logger.info("No matches found with catalog")
        return pd.DataFrame()

    # Concatenate all matched rows into single DataFrame
    result_df = pd.concat(found_items, ignore_index=True)

    # Price classification
    result_df['price_classification'] = result_df.apply(
        lambda row: _classify_price(
            price=row['db_price'],
            catalog_price_eur=row.get('price_eur'),
            segments_names=row.get('segments_names'),
            price_delta_perc=price_delta_perc
        ),
        axis=1
    )

    logger.info(f"Found {len(result_df)} matches with catalog")
    logger.info(f"Price classification: {result_df['price_classification'].value_counts().to_dict()}")

    return result_df


def _find_in_catalog(
    catalog_df: pd.DataFrame,
    oem_code: str,
    other_codes: List[str],
    manufacturer_code: str,
    product: Product
) -> Dict[str, Any]:
    """
    Search for product in catalog by codes

    Args:
        catalog_df: Catalog DataFrame
        oem_code: Product OEM code
        other_codes: List of other codes
        manufacturer_code: Manufacturer code
        product: Product object for logging

    Returns:
        Dictionary with search results including matched_rows DataFrame
    """
    result = {
        'found': False,
        'matched_by': None,
        'matched_value': None,
        'matched_rows': pd.DataFrame(),
        'match_count': 0
    }

    # Function to search code in oes_numbers string
    def code_in_oes(code: str, oes_numbers: str) -> bool:
        if not code or not oes_numbers:
            return False
        # Split oes_numbers by " | " and check for exact match
        oes_list = [x.strip() for x in str(oes_numbers).split(' | ')]
        return code.strip().upper() in [x.upper() for x in oes_list]

    matched_rows = pd.DataFrame()
    matched_by = None
    matched_value = None

    # Search by oem_code
    if oem_code:
        mask = catalog_df['oes_numbers'].apply(lambda x: code_in_oes(oem_code, x))
        if mask.any():
            matched_rows = catalog_df[mask]
            matched_by = 'oem_code'
            matched_value = oem_code

    # Search by manufacturer_code (if not found by oem_code)
    if matched_rows.empty and manufacturer_code:
        mask = catalog_df['oes_numbers'].apply(lambda x: code_in_oes(manufacturer_code, x))
        if mask.any():
            matched_rows = catalog_df[mask]
            matched_by = 'manufacturer_code'
            matched_value = manufacturer_code

    # Search by other_codes (if not found by previous)
    if matched_rows.empty and other_codes:
        for code in other_codes:
            if code:
                mask = catalog_df['oes_numbers'].apply(lambda x: code_in_oes(code, x))
                if mask.any():
                    matched_rows = catalog_df[mask]
                    matched_by = 'other_codes'
                    matched_value = code
                    break

    if not matched_rows.empty:
        result['found'] = True
        result['matched_by'] = matched_by
        result['matched_value'] = matched_value
        result['matched_rows'] = matched_rows.copy()
        result['match_count'] = len(matched_rows)

        logger.info(
            f"Product {product.part_id}: found {len(matched_rows)} matches "
            f"by {matched_by}='{matched_value}'"
        )
    else:
        logger.debug(
            f"Product {product.part_id}: no matches found "
            f"(oem_code='{oem_code}', manufacturer_code='{manufacturer_code}', "
            f"other_codes={other_codes})"
        )

    return result


def _classify_price(
    price: Optional[float],
    catalog_price_eur: Optional[float],
    segments_names: Optional[str],
    price_delta_perc: float
) -> str:
    """
    Classify product price

    Args:
        price: Product price from DB
        catalog_price_eur: Price from catalog in EUR
        segments_names: Segment name from catalog
        price_delta_perc: Allowed difference multiplier for TOP segment

    Returns:
        'OK' or 'HIGH'
    """
    if price is None or catalog_price_eur is None:
        return 'NA'

    # For TOP segment apply price_delta_perc
    if segments_names and 'TOP' in str(segments_names).upper():
        threshold = catalog_price_eur * price_delta_perc
    else:
        threshold = catalog_price_eur

    return 'OK' if price <= threshold else 'HIGH'


def compare_all_and_save(
    price_delta_perc: float = 1.1,
    clear_before: bool = True
) -> Dict[str, Any]:
    """
    Compare products with both EUR and GUR catalogs and save results to database.

    Args:
        price_delta_perc: Multiplier for allowed price difference (e.g., 1.1 for +10%)
        clear_before: Whether to clear the compare table before saving new results

    Returns:
        Dictionary with statistics about the comparison
    """
    database_url = get_database_url()
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")

    compare_repo = CompareRepository(database_url)
    compare_repo.create_tables()

    # Clear table if requested
    if clear_before:
        compare_repo.clear_table()

    results = {
        'eur': {'matches': 0, 'saved': 0, 'error': None},
        'gur': {'matches': 0, 'saved': 0, 'error': None},
    }

    # Compare with EUR catalog
    try:
        eur_df = compare_products_with_catalog('eur', price_delta_perc)
        if not eur_df.empty:
            results['eur']['matches'] = len(eur_df)
            # Replace NaN with None for JSON compatibility
            eur_df = eur_df.where(pd.notnull(eur_df), None)
            eur_records = eur_df.to_dict('records')
            results['eur']['saved'] = compare_repo.save_results(eur_records, 'eur')
    except FileNotFoundError as e:
        logger.warning(f"EUR catalog not found: {e}")
        results['eur']['error'] = str(e)
    except Exception as e:
        logger.error(f"Error comparing with EUR catalog: {e}")
        results['eur']['error'] = str(e)

    # Compare with GUR catalog
    try:
        gur_df = compare_products_with_catalog('gur', price_delta_perc)
        if not gur_df.empty:
            results['gur']['matches'] = len(gur_df)
            # Replace NaN with None for JSON compatibility
            gur_df = gur_df.where(pd.notnull(gur_df), None)
            gur_records = gur_df.to_dict('records')
            results['gur']['saved'] = compare_repo.save_results(gur_records, 'gur')
    except FileNotFoundError as e:
        logger.warning(f"GUR catalog not found: {e}")
        results['gur']['error'] = str(e)
    except Exception as e:
        logger.error(f"Error comparing with GUR catalog: {e}")
        results['gur']['error'] = str(e)

    # Get final stats
    stats = compare_repo.get_stats()
    results['stats'] = stats

    logger.info(f"Comparison complete: EUR={results['eur']['saved']}, GUR={results['gur']['saved']} saved")
    logger.info(f"Stats: {stats}")

    return results


def _group_catalog_results_by_article(catalog_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group catalog results by article (and brand) to avoid duplicates.
    Merges products from multiple catalog rows with the same article.

    Args:
        catalog_results: List of catalog result dictionaries

    Returns:
        List of grouped catalog results (one per unique article+brand)
    """
    # Group by article and brand
    grouped = {}

    for result in catalog_results:
        article = result['catalog_data'].get('article', '')
        brand = result['catalog_data'].get('brand', '')
        key = f"{article}|{brand}"

        if key not in grouped:
            # First occurrence - initialize
            grouped[key] = result.copy()
            grouped[key]['all_oes_numbers'] = [result['catalog_oes_numbers']]
        else:
            # Merge with existing
            existing = grouped[key]

            # Merge matched products (avoid duplicates by part_id)
            existing_part_ids = {p['part_id'] for p in existing['matched_products']}
            for product in result['matched_products']:
                if product['part_id'] not in existing_part_ids:
                    existing['matched_products'].append(product)
                    existing_part_ids.add(product['part_id'])

            # Collect all OES numbers
            if result['catalog_oes_numbers'] not in existing['all_oes_numbers']:
                existing['all_oes_numbers'].append(result['catalog_oes_numbers'])

            # Recalculate statistics
            prices = [p['price'] for p in existing['matched_products'] if p['price'] is not None]
            ok_count = sum(1 for p in existing['matched_products'] if p['price_classification'] == 'OK')
            high_count = sum(1 for p in existing['matched_products'] if p['price_classification'] == 'HIGH')

            existing['matched_products_count'] = len(existing['matched_products'])
            existing['matched_products_ids'] = [p['part_id'] for p in existing['matched_products']]
            existing['price_match_ok_count'] = ok_count
            existing['price_match_high_count'] = high_count
            existing['avg_db_price'] = sum(prices) / len(prices) if prices else None
            existing['min_db_price'] = min(prices) if prices else None
            existing['max_db_price'] = max(prices) if prices else None

            # Update catalog_oes_numbers to show all variants
            existing['catalog_oes_numbers'] = ' | '.join(existing['all_oes_numbers'])

    # Convert back to list and clean up temporary fields
    result_list = []
    for result in grouped.values():
        if 'all_oes_numbers' in result:
            del result['all_oes_numbers']
        result_list.append(result)

    logger.info(f"Grouped {len(catalog_results)} catalog rows into {len(result_list)} unique articles")
    return result_list


def compare_catalog_with_products(
    table: str,
    price_delta_perc: float
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compare catalog items with products from DB (INVERTED RELATIONSHIP)

    Each catalog row gets a list of matched products.
    Products without catalog matches are returned separately.

    Args:
        table: Catalog table name ('gur' or 'eur')
        price_delta_perc: Multiplier for allowed price difference (e.g., 1.1 for +10%)

    Returns:
        Tuple of (catalog_matches_df, unmatched_products_df)
    """
    if table not in ('gur', 'eur'):
        raise ValueError(f"table must be 'gur' or 'eur', got: {table}")

    # Load catalog
    csv_path = os.path.join(CSV_DIR, f"{table}.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Catalog file not found: {csv_path}")

    catalog_df = pd.read_csv(csv_path)
    logger.info(f"Loaded catalog {table}.csv: {len(catalog_df)} rows")

    # Get products
    database_url = get_database_url()
    if not database_url:
        raise ValueError("DATABASE_URL not found")

    repo = ProductRepository(database_url)
    products = repo.get_all()
    logger.info(f"Got {len(products)} products from DB")

    if not products:
        logger.warning("No products in DB")
        return pd.DataFrame(), pd.DataFrame()

    # Track which products matched
    matched_product_ids = set()

    # Build catalog results
    catalog_results = []

    for idx, catalog_row in catalog_df.iterrows():
        oes_numbers = catalog_row.get('oes_numbers', '')
        if not oes_numbers:
            continue

        # Find all products matching this catalog row
        matched_products = []

        for product in products:
            item_desc = product.item_description or {}
            oem_code = item_desc.get('oem_code', '')
            other_codes = item_desc.get('other_codes', [])
            manufacturer_code = item_desc.get('manufacturer_code', '')

            # Normalize other_codes
            if isinstance(other_codes, str):
                other_codes = [other_codes] if other_codes else []
            elif not isinstance(other_codes, list):
                other_codes = []

            # Check if any product code matches this catalog row
            match_info = _check_product_matches_catalog_row(
                oes_numbers=oes_numbers,
                oem_code=oem_code,
                manufacturer_code=manufacturer_code,
                other_codes=other_codes
            )

            if match_info['matched']:
                # Classify price
                price_class = _classify_price(
                    price=product.price,
                    catalog_price_eur=catalog_row.get('price_eur'),
                    segments_names=catalog_row.get('segments_names'),
                    price_delta_perc=price_delta_perc
                )

                matched_products.append({
                    'part_id': product.part_id,
                    'code': product.code,
                    'price': product.price,
                    'url': product.url,
                    'matched_by': match_info['matched_by'],
                    'matched_value': match_info['matched_value'],
                    'price_classification': price_class,
                    'product_data': product.to_dict()
                })

                matched_product_ids.add(product.part_id)

        # Build catalog result row (only if has matches)
        if matched_products:
            # Calculate aggregates
            prices = [p['price'] for p in matched_products if p['price'] is not None]
            ok_count = sum(1 for p in matched_products if p['price_classification'] == 'OK')
            high_count = sum(1 for p in matched_products if p['price_classification'] == 'HIGH')

            catalog_result = {
                'catalog': table,
                'catalog_oes_numbers': oes_numbers,
                'catalog_price_eur': catalog_row.get('price_eur'),
                'catalog_price_usd': catalog_row.get('price_usd'),
                'catalog_segments_names': catalog_row.get('segments_names'),

                # Match statistics
                'matched_products_count': len(matched_products),
                'matched_products_ids': [p['part_id'] for p in matched_products],

                # Price statistics
                'price_match_ok_count': ok_count,
                'price_match_high_count': high_count,
                'avg_db_price': sum(prices) / len(prices) if prices else None,
                'min_db_price': min(prices) if prices else None,
                'max_db_price': max(prices) if prices else None,

                # Full data
                'catalog_data': catalog_row.to_dict(),
                'matched_products': matched_products
            }

            catalog_results.append(catalog_result)

    # Group by article to avoid duplicates
    catalog_results = _group_catalog_results_by_article(catalog_results)

    # Build unmatched products
    unmatched_results = []
    for product in products:
        if product.part_id not in matched_product_ids:
            item_desc = product.item_description or {}
            oem_code = item_desc.get('oem_code', '')
            other_codes = item_desc.get('other_codes', [])
            manufacturer_code = item_desc.get('manufacturer_code', '')

            if isinstance(other_codes, str):
                other_codes = [other_codes] if other_codes else []
            elif not isinstance(other_codes, list):
                other_codes = []

            unmatched_results.append({
                'catalog': table,
                'product_part_id': product.part_id,
                'product_code': product.code,
                'product_price': product.price,
                'searched_codes': {
                    'oem_code': oem_code,
                    'manufacturer_code': manufacturer_code,
                    'other_codes': other_codes
                },
                'product_data': product.to_dict()
            })

    catalog_df_result = pd.DataFrame(catalog_results)
    unmatched_df_result = pd.DataFrame(unmatched_results)

    logger.info(f"Catalog items with matches: {len(catalog_df_result)}")
    logger.info(f"Unmatched products: {len(unmatched_df_result)}")

    return catalog_df_result, unmatched_df_result


def _check_product_matches_catalog_row(
    oes_numbers: str,
    oem_code: str,
    manufacturer_code: str,
    other_codes: List[str]
) -> Dict[str, Any]:
    """
    Check if product codes match catalog row oes_numbers

    Args:
        oes_numbers: Pipe-separated codes from catalog
        oem_code: Product OEM code
        manufacturer_code: Product manufacturer code
        other_codes: List of other product codes

    Returns:
        Dict with matched status and match info
    """
    def code_in_oes(code: str, oes_numbers: str) -> bool:
        if not code or not oes_numbers:
            return False
        oes_list = [x.strip().upper() for x in str(oes_numbers).split(' | ')]
        return code.strip().upper() in oes_list

    # Try oem_code first
    if oem_code and code_in_oes(oem_code, oes_numbers):
        return {'matched': True, 'matched_by': 'oem_code', 'matched_value': oem_code}

    # Try manufacturer_code
    if manufacturer_code and code_in_oes(manufacturer_code, oes_numbers):
        return {'matched': True, 'matched_by': 'manufacturer_code', 'matched_value': manufacturer_code}

    # Try other_codes
    for code in other_codes:
        if code and code_in_oes(code, oes_numbers):
            return {'matched': True, 'matched_by': 'other_codes', 'matched_value': code}

    return {'matched': False, 'matched_by': None, 'matched_value': None}


def compare_all_inverted_and_save(
    price_delta_perc: float = 1.1,
    clear_before: bool = True
) -> Dict[str, Any]:
    """
    Compare catalogs with products (inverted relationship) and save to database.

    Saves to catalog_matches and unmatched_products tables.

    Args:
        price_delta_perc: Multiplier for allowed price difference (e.g., 1.1 for +10%)
        clear_before: Whether to clear tables before saving

    Returns:
        Dictionary with statistics
    """
    database_url = get_database_url()
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")

    catalog_repo = CatalogMatchRepository(database_url)
    catalog_repo.create_tables()

    # Clear tables if requested
    if clear_before:
        catalog_repo.clear_tables()

    results = {
        'eur': {'catalog_matches': 0, 'unmatched_products': 0, 'error': None},
        'gur': {'catalog_matches': 0, 'unmatched_products': 0, 'error': None},
    }

    # Compare with EUR catalog
    try:
        eur_matches_df, eur_unmatched_df = compare_catalog_with_products('eur', price_delta_perc)

        if not eur_matches_df.empty:
            eur_matches_df = eur_matches_df.where(pd.notnull(eur_matches_df), None)
            eur_matches_records = eur_matches_df.to_dict('records')
            results['eur']['catalog_matches'] = catalog_repo.save_catalog_matches(eur_matches_records, 'eur')

        if not eur_unmatched_df.empty:
            eur_unmatched_df = eur_unmatched_df.where(pd.notnull(eur_unmatched_df), None)
            eur_unmatched_records = eur_unmatched_df.to_dict('records')
            results['eur']['unmatched_products'] = catalog_repo.save_unmatched_products(eur_unmatched_records, 'eur')

    except FileNotFoundError as e:
        logger.warning(f"EUR catalog not found: {e}")
        results['eur']['error'] = str(e)
    except Exception as e:
        logger.error(f"Error comparing with EUR catalog: {e}", exc_info=True)
        results['eur']['error'] = str(e)

    # Compare with GUR catalog
    try:
        gur_matches_df, gur_unmatched_df = compare_catalog_with_products('gur', price_delta_perc)

        if not gur_matches_df.empty:
            gur_matches_df = gur_matches_df.where(pd.notnull(gur_matches_df), None)
            gur_matches_records = gur_matches_df.to_dict('records')
            results['gur']['catalog_matches'] = catalog_repo.save_catalog_matches(gur_matches_records, 'gur')

        if not gur_unmatched_df.empty:
            gur_unmatched_df = gur_unmatched_df.where(pd.notnull(gur_unmatched_df), None)
            gur_unmatched_records = gur_unmatched_df.to_dict('records')
            results['gur']['unmatched_products'] = catalog_repo.save_unmatched_products(gur_unmatched_records, 'gur')

    except FileNotFoundError as e:
        logger.warning(f"GUR catalog not found: {e}")
        results['gur']['error'] = str(e)
    except Exception as e:
        logger.error(f"Error comparing with GUR catalog: {e}", exc_info=True)
        results['gur']['error'] = str(e)

    # Get final stats
    stats = catalog_repo.get_stats()
    results['stats'] = stats

    logger.info(f"Comparison complete: EUR={results['eur']}, GUR={results['gur']}")
    logger.info(f"Stats: {stats}")

    return results

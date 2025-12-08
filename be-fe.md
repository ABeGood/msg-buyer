# Backend-Frontend Data Structure

## Catalog Matches Endpoint

### Purpose
Display catalog items (from EUR/GUR catalogs) with their matched products from the database.

### Data Flow
1. **Backend**: `compare_catalog_with_products()` from `compare_utils.py` creates inverted relationship
2. **Database**: `CatalogMatchModel` stores catalog items with matched products array
3. **Frontend**: Receives catalog-centric view with product matches

### API Endpoints

#### 1. Get Catalog Matches (with filters and pagination)
**GET** `/api/catalog-matches`

**Query Parameters:**
- `catalog` (optional): Filter by catalog ('eur', 'gur', 'eur,gur', or empty for all)
- `segment` (optional): Filter by segment name (e.g., 'TOP')
- `price_classification` (optional): Filter by price classification ('OK' or 'HIGH')
- `limit` (optional): Number of records to return (pagination)
- `offset` (optional): Offset for pagination (default: 0)

**Examples:**
- Get EUR only: `/api/catalog-matches?catalog=eur`
- Get EUR + GUR: `/api/catalog-matches?catalog=eur,gur`
- Get all: `/api/catalog-matches`

**Response Format:**
```json
{
  "catalog": "eur",
  "total_matches": 150,
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "catalog": "eur",
      "catalog_oes_numbers": "1K0423051BT | 1K0423051CP",
      "catalog_price_eur": 245.50,
      "catalog_price_usd": 267.80,
      "catalog_segments_names": "TOP",
      "matched_products_count": 3,
      "matched_products_ids": ["P123", "P456", "P789"],

      // Price statistics
      "price_match_ok_count": 2,
      "price_match_high_count": 1,
      "avg_db_price": 220.00,
      "min_db_price": 200.00,
      "max_db_price": 250.00,

      // Full catalog data
      "catalog_data": {
        "oes_numbers": "1K0423051BT | 1K0423051CP",
        "price_eur": 245.50,
        "price_usd": 267.80,
        "segments_names": "TOP",
        "remains": 10,
        // ... other catalog fields
      },

      // Matched products with classification
      "matched_products": [
        {
          "part_id": "P123",
          "code": "1K0423051BT",
          "price": 200.00,
          "url": "https://rrr.lt/product/P123",
          "matched_by": "oem_code",
          "matched_value": "1K0423051BT",
          "price_classification": "OK",
          "product_data": {
            "seller_email": "seller@example.com",
            "images": ["img1.jpg", "img2.jpg"],
            "car_details": {...},
            "item_description": {...}
          }
        },
        {
          "part_id": "P456",
          "code": "1K0423051CP",
          "price": 250.00,
          "url": "https://rrr.lt/product/P456",
          "matched_by": "manufacturer_code",
          "matched_value": "1K0423051CP",
          "price_classification": "HIGH",
          "product_data": {...}
        }
      ]
    }
  ]
}
```

### Key Fields Explanation

**Catalog Level:**
- `catalog_oes_numbers`: Pipe-separated OEM codes from catalog
- `catalog_price_eur/usd`: Reference prices from catalog
- `catalog_segments_names`: Segment classification (TOP, STANDARD, etc.)
- `matched_products_count`: Total number of matching products found

**Match Statistics:**
- `price_match_ok_count`: Products with acceptable price (≤ catalog_price * threshold)
- `price_match_high_count`: Products with high price (> catalog_price * threshold)
- `avg/min/max_db_price`: Price statistics for matched products

**Product Match Level:**
- `matched_by`: Which code matched (oem_code, manufacturer_code, other_codes)
- `matched_value`: The specific code that matched
- `price_classification`: OK (good price), HIGH (expensive), NA (no price info)
- `product_data`: Full product details including seller, images, car compatibility

### Price Classification Logic
- **TOP Segment**: `price_classification = 'OK'` if `product.price <= catalog_price_eur * price_delta_perc` (e.g., 1.1 for +10%)
- **Other Segments**: `price_classification = 'OK'` if `product.price <= catalog_price_eur`

### Frontend Display Recommendations

**Table View:**
- Row per catalog item
- Show OES numbers, catalog price, match count, price stats
- Expand to show matched products list

**Product Cards:**
- Display matched products with classification badges (OK/HIGH)
- Show seller info, images, car compatibility
- Link to original product page

**Filters:**
- By catalog (EUR/GUR)
- By segment (TOP, STANDARD)
- By price classification (OK only, HIGH only, all)
- By match count (single match, multiple matches)

#### 2. Get Catalog Match Detail
**GET** `/api/catalog-matches/{match_id}`

**Response Format:**
Same structure as single item from the list above (without the array wrapper).

#### 3. Get Catalog Statistics
**GET** `/api/catalog-stats`

**Response Format:**
```json
[
  {
    "catalog": "eur",
    "total_catalog_items": 450,
    "total_matched_products": 1250,
    "total_ok_prices": 800,
    "total_high_prices": 450,
    "overall_avg_price": 235.50,
    "items_with_ok_prices": 320,
    "items_with_only_high_prices": 130
  },
  {
    "catalog": "gur",
    "total_catalog_items": 380,
    "total_matched_products": 1100,
    "total_ok_prices": 650,
    "total_high_prices": 450,
    "overall_avg_price": 198.75,
    "items_with_ok_prices": 280,
    "items_with_only_high_prices": 100
  }
]
```

### Data Source
- Generated by: `compare_all_inverted_and_save()` in `compare_utils.py`
- Stored in: `catalog_matches` table (`CatalogMatchModel`)
- Inverted relationship: Catalog items → Matched products (vs. products → catalog matches)
- **Grouping**: Results are grouped by `article + brand` to ensure each article appears only once, even if it has multiple OES number variants in the catalog

### Implementation Notes
- All endpoints require authentication (user must be approved)
- Results are ordered by `price_match_ok_count DESC, matched_products_count DESC`
- Full product data is embedded in `matched_products` array with `product_data` field
- Pagination is supported via `limit` and `offset` parameters

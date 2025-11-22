# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MSG Buyer is a web scraping application that parses auto parts data from rrr.lt and stores it in a PostgreSQL database. Currently focused on steering rack products.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the scraper
python main.py
```

## Architecture

**Data Flow:** Scraper → Parser → Product → Repository → PostgreSQL

### Key Components

- **sources/scrapers/**: Selenium-based scrapers using Edge WebDriver
  - `base_scraper.py`: WebDriver initialization, page loading, element waiting
  - `rrr_scraper.py`: Site-specific scraper for rrr.lt

- **sources/parsers/**: HTML parsing with BeautifulSoup + Selenium
  - `rrr/steering_rack_parser.py`: Extracts product list from category pages and detailed data (item_description, car_details, seller_info, images) from product pages

- **sources/classes/product.py**: Domain model with fields: part_id, code, price, url, source_site, category, item_description, car_details, seller_info, images

- **sources/database/**: SQLAlchemy with PostgreSQL (JSONB for flexible fields)
  - `models.py`: ProductModel ORM mapping
  - `repository.py`: CRUD operations with upsert logic (save updates if part_id exists)
  - `config.py`: Database URL from .env (supports DATABASE_URL, DATABASE_PUBLIC_URL, or individual PG* vars)

## Configuration

Requires `.env` file with PostgreSQL connection:
```
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

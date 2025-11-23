# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MSG Buyer is a web scraping application that parses auto parts data from rrr.lt and stores it in a PostgreSQL database. Currently focused on steering rack products. Includes email service for contacting sellers.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the scraper
python main.py

# Send email inquiry to seller
python send_inquiry.py --part-id P123456 --message "..." --buyer-name "..." --buyer-email "..."

# Check email responses
python send_inquiry.py --check-responses

# Run email examples
python email_example.py
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
  - `models.py`: ProductModel, SellerModel, EmailLogModel ORM mappings
  - `repository.py`: CRUD operations with upsert logic (save updates if part_id exists)
  - `config.py`: Database URL from .env (supports DATABASE_URL, DATABASE_PUBLIC_URL, or individual PG* vars)

- **sources/services/**: External integrations
  - `email_service.py`: Gmail SMTP/IMAP service for sending inquiries and parsing responses
  - `email_templates.py`: Email templates for various inquiry types

## Configuration

Requires `.env` file with PostgreSQL connection and email credentials:
```env
# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Email (Gmail)
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=MSG Buyer
```

See `.env.email.example` for full configuration options.
See `EMAIL_SERVICE.md` for detailed email service documentation.

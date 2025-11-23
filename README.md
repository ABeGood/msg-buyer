# MSG Buyer - Auto Parts Scraper & Email Service

Web scraping application that parses auto parts data from rrr.lt and stores it in PostgreSQL database. Includes email service for contacting sellers with intelligent response parsing.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Database & Email
```bash
cp .env.email.example .env
# Edit .env with your credentials
```

See **[QUICK_START.md](QUICK_START.md)** for detailed Gmail setup (5 minutes).

### 3. Run Scraper
```bash
python main.py
```

### 4. Send Email to Seller
```bash
python send_inquiry.py \
  --part-id P123456 \
  --message "I'm interested in this part" \
  --buyer-name "Your Name" \
  --buyer-email "your@email.com" \
  --language en
```

### 5. Check Responses
```bash
python send_inquiry.py --check-responses
```

## 📋 Features

### Web Scraping
- ✅ Scrapes product listings from rrr.lt
- ✅ Extracts detailed product information (codes, prices, descriptions)
- ✅ Collects car details (make, model, year, engine, mileage)
- ✅ Retrieves seller information and contact details
- ✅ Downloads product images
- ✅ Stores everything in PostgreSQL with JSONB support

### Email Service
- ✉️ Send inquiries to sellers via Gmail SMTP
- 📧 Parse seller responses automatically via IMAP
- 🔍 Extract prices from responses (€150, 150€, EUR 150)
- 📊 Detect availability (positive/negative keywords)
- 🌍 Multi-language support (English & Lithuanian)
- 📝 Professional HTML email templates
- 💾 Database logging of all emails and responses

## 📁 Project Structure

```
msg-buyer/
├── main.py                    # Scraper entry point
├── send_inquiry.py           # Email CLI tool
├── email_example.py          # Usage examples
├── test_email_service.py     # Email service tests
│
├── sources/
│   ├── scrapers/            # Selenium-based scrapers
│   ├── parsers/             # HTML parsing logic
│   ├── classes/             # Data models (Product)
│   ├── database/            # SQLAlchemy models & repository
│   ├── services/            # Email service & templates
│   └── utils/               # Logger utilities
│
├── QUICK_START.md           # 5-minute setup guide
├── EMAIL_SERVICE.md         # Complete email documentation
├── IMPLEMENTATION_SUMMARY.md # Technical details
└── CLAUDE.md                # AI assistant context
```

## 🗄️ Database Schema

### Products Table
- Product details (part_id, code, price, url, category)
- Item description (manufacturer codes, condition) - JSONB
- Car details (make, model, year, engine) - JSONB
- Seller email, images, comments

### Sellers Table
- Contact info (email, phone, address)
- Company details (name, VAT, rating)
- Working hours, holidays - JSONB

### Email Logs Table
- Sent emails (seller, product, subject, body)
- Status tracking (sent, failed, bounced)
- Response tracking (received, analyzed)

## 📧 Email Service Usage

### CLI Usage

**Send inquiry:**
```bash
python send_inquiry.py \
  --part-id P123456 \
  --message "Is this available?" \
  --buyer-name "John Doe" \
  --buyer-email "john@example.com" \
  --language en
```

**Check responses:**
```bash
python send_inquiry.py --check-responses
```

### Programmatic Usage

```python
from sources.services.email_service import EmailService
from sources.database.repository import ProductRepository
from sources.database.config import get_database_url

# Initialize
email_service = EmailService(database_url=get_database_url())
repository = ProductRepository(get_database_url())

# Send inquiry
product = repository.find_by_part_id("P123456")
success = email_service.send_product_inquiry(
    product=product,
    message="I'm interested in this part",
    buyer_email="buyer@example.com",
    buyer_name="John Doe",
    language='en'
)

# Check responses
responses = email_service.check_responses()
for response in responses:
    if response['is_available'] and response['has_price']:
        print(f"Available at €{response['extracted_price']}")
```

## 🔧 Configuration

Create `.env` file with:

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Gmail SMTP
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Get from myaccount.google.com/apppasswords
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=Your Name

# IMAP (for responses)
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
```

See [QUICK_START.md](QUICK_START.md) for Gmail App Password setup.

## 🧪 Testing

```bash
# Test email service
python test_email_service.py

# Test configuration, templates, response parsing
# Expected: 🎉 Все тесты пройдены успешно!
```

## 📚 Documentation

- **[QUICK_START.md](QUICK_START.md)** - Get started in 5 minutes
- **[EMAIL_SERVICE.md](EMAIL_SERVICE.md)** - Complete email service docs
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Technical details
- **[CLAUDE.md](CLAUDE.md)** - Project architecture & context

## 🎯 Use Cases

1. **Price Comparison** - Query multiple sellers for same part
2. **Availability Check** - Find which sellers have specific parts
3. **Automated Responses** - Parse seller replies for availability and price
4. **Bulk Inquiries** - Send inquiries to multiple sellers at once
5. **Market Analysis** - Collect pricing data over time

## ⚡ Key Features

### Intelligent Response Parsing
- Detects availability using keyword analysis
- Extracts prices in multiple formats (€150, 150€, EUR 150)
- Identifies positive/negative responses
- Supports English and Lithuanian

### Professional Email Templates
- HTML formatted with product details
- Car information included automatically
- Contact information clearly displayed
- Multi-language support (EN/LT)

### Database Integration
- All emails logged automatically
- Response tracking and analysis
- Seller information linked to products
- Easy querying and reporting

## 🛡️ Security

- Environment variable configuration (no hardcoded credentials)
- Gmail App Password support (not main password)
- TLS/SSL encryption for email
- SQL injection protection (SQLAlchemy ORM)
- Input validation and sanitization

## 📊 Response Analysis Example

```python
{
    'seller_email': 'seller@example.com',
    'subject': 'Re: Inquiry about steering-rack - ABC123',
    'product_code': 'ABC123',
    'is_positive': True,        # ✅ Positive response
    'has_price': True,          # 💰 Price found
    'extracted_price': 150.00,  # €150
    'is_available': True,       # ✅ Part available
    'keywords': ['available', 'have', 'can sell']
}
```

## 🚦 Getting Started Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Create Gmail App Password (see [QUICK_START.md](QUICK_START.md))
- [ ] Configure `.env` file with database and email credentials
- [ ] Run scraper: `python main.py`
- [ ] Test email: `python test_email_service.py`
- [ ] Send first inquiry: `python send_inquiry.py --part-id ...`
- [ ] Check responses: `python send_inquiry.py --check-responses`

## 💡 Tips

- **Test first:** Send email to yourself to see format
- **Check logs:** All emails saved in `email_logs` table
- **Rate limits:** Gmail allows ~500 emails/day for free accounts
- **Response time:** Sellers typically respond in 24-48 hours
- **Language:** Use seller's language for better response rate

## ⚠️ Troubleshooting

**SMTP Authentication Failed?**
- Use Gmail App Password, not regular password
- Enable 2-Step Verification first
- Check credentials in `.env`

**No responses found?**
- Wait 24-48 hours for seller replies
- Check spam folder
- Verify IMAP enabled in Gmail settings

See [EMAIL_SERVICE.md](EMAIL_SERVICE.md) for full troubleshooting guide.

## 🔮 Future Enhancements

- [ ] Task queue (Celery) for async email sending
- [ ] Retry mechanism with exponential backoff
- [ ] Email scheduling based on seller working hours
- [ ] Web dashboard for email management
- [ ] Telegram/Slack integration
- [ ] AI-powered response suggestions
- [ ] A/B testing for email templates

## 📝 Requirements

- Python 3.13+
- PostgreSQL database
- Gmail account with App Password
- Internet connection

## 📄 License

Part of MSG Buyer project - auto parts sourcing automation.

## 🤝 Contributing

This is a private project. For questions or issues, check documentation files.

---

**Current Branch:** `mail-service`  
**Status:** ✅ Email service fully implemented and tested  
**Last Updated:** November 23, 2025

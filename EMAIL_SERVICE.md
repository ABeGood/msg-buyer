# Email Service Documentation

## Overview

Email service для отправки запросов продавцам автозапчастей и парсинга ответов.

## Features

- ✉️ Отправка email запросов через Gmail SMTP
- 📧 Парсинг ответов от продавцов через IMAP
- 📊 Логирование всех отправленных писем в БД
- 🌍 Поддержка английского и литовского языков
- 🎨 HTML форматирование писем
- 🔍 Автоматический анализ ответов (цена, доступность)
- 📝 Шаблоны для различных типов запросов

## Setup

### 1. Gmail Configuration

#### Enable 2-Step Verification
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification

#### Create App Password
1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
2. Select "Mail" and "Other (Custom name)"
3. Enter name: "MSG Buyer"
4. Click "Generate"
5. Copy the 16-character password

### 2. Environment Variables

Copy `.env.email.example` to `.env` and fill in your credentials:

```bash
cp .env.email.example .env
```

Edit `.env`:
```env
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=MSG Buyer
```

### 3. Database Migration

The email service requires the `email_logs` table. Run the scraper once to create all tables:

```bash
python main.py
```

Or create tables manually:
```python
from sources.database.config import get_database_url
from sources.database.models import Base
from sqlalchemy import create_engine

database_url = get_database_url()
engine = create_engine(database_url)
Base.metadata.create_all(bind=engine)
```

## Usage

### Send Product Inquiry

#### By Part ID:
```bash
python send_inquiry.py \
  --part-id P123456 \
  --message "I'm interested in this steering rack. Is it still available?" \
  --buyer-name "John Doe" \
  --buyer-email "john@example.com" \
  --buyer-phone "+37012345678" \
  --language en
```

#### By Code (SKU):
```bash
python send_inquiry.py \
  --code A1B2C3 \
  --message "Ar ši detalė vis dar prieinama?" \
  --buyer-name "Jonas Jonaitis" \
  --buyer-email "jonas@example.com" \
  --language lt
```

### Check Responses

Check inbox for seller responses:
```bash
python send_inquiry.py --check-responses
```

Check and mark as read:
```bash
python send_inquiry.py --check-responses --mark-as-read
```

### Programmatic Usage

```python
from sources.services.email_service import EmailService
from sources.database.repository import ProductRepository
from sources.database.config import get_database_url

# Initialize services
database_url = get_database_url()
email_service = EmailService(database_url=database_url)
repository = ProductRepository(database_url)

# Find product
product = repository.find_by_part_id("P123456")

# Send inquiry
success = email_service.send_product_inquiry(
    product=product,
    message="I'm interested in this part. Is it still available?",
    buyer_email="buyer@example.com",
    buyer_name="John Doe",
    buyer_phone="+37012345678",
    language='en'
)

print(f"Email sent: {success}")

# Check responses
responses = email_service.check_responses(mark_as_read=False)
for response in responses:
    print(f"Response from: {response['seller_email']}")
    print(f"Is positive: {response['is_positive']}")
    print(f"Has price: {response['has_price']}")
    if response['extracted_price']:
        print(f"Price: €{response['extracted_price']}")
```

### Bulk Inquiries

```python
from sources.services.email_service import EmailService
from sources.database.repository import ProductRepository

# Get multiple products
repository = ProductRepository(database_url)
products = [
    repository.find_by_part_id("P123456"),
    repository.find_by_part_id("P789012"),
]

email_service = EmailService(database_url)

# Send bulk inquiries
results = email_service.send_bulk_inquiries(
    products=products,
    message="I'm interested in these parts. Are they available?",
    buyer_email="buyer@example.com",
    buyer_name="John Doe",
    language='en'
)

print(f"Total: {results['total']}")
print(f"Sent: {results['sent']}")
print(f"Failed: {results['failed']}")
print(f"Skipped: {results['skipped']}")
```

## Email Templates

### Product Inquiry Template

**English:**
- Subject: `Inquiry about {category} - {code}`
- Includes: product details, car details, buyer message, contact info

**Lithuanian:**
- Subject: `Užklausa dėl {category} - {code}`
- Same structure in Lithuanian

### Custom Templates

Add new templates in `sources/services/email_templates.py`:

```python
@staticmethod
def get_custom_template(product, **kwargs):
    subject = "Custom Subject"
    body = """
    Custom email body with {product.code}
    """
    return {'subject': subject, 'body': body}
```

## Response Parsing

The service automatically analyzes seller responses for:

### Availability Detection
- **Positive keywords**: "available", "in stock", "yes", "have", "can sell"
- **Negative keywords**: "not available", "sold out", "sorry"

### Price Extraction
- Patterns: `€123`, `123€`, `EUR 123`, `123.45`
- Automatically converts to float

### Response Data Structure
```python
{
    'seller_email': 'seller@example.com',
    'subject': 'Re: Inquiry about steering-rack - ABC123',
    'date': 'Mon, 23 Nov 2025 10:30:00 +0200',
    'body': 'Full email text...',
    'product_code': 'ABC123',
    'is_positive': True,
    'has_price': True,
    'extracted_price': 150.00,
    'has_availability': True,
    'is_available': True,
    'keywords': ['available', 'have']
}
```

## Database Schema

### email_logs Table

```sql
CREATE TABLE email_logs (
    id SERIAL PRIMARY KEY,
    seller_email VARCHAR(255) NOT NULL,
    product_part_id VARCHAR(50),
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'sent',
    error_message TEXT,
    sent_at TIMESTAMP NOT NULL,
    response_received BOOLEAN DEFAULT FALSE,
    response_at TIMESTAMP
);

CREATE INDEX idx_email_logs_seller_email ON email_logs(seller_email);
CREATE INDEX idx_email_logs_product_part_id ON email_logs(product_part_id);
CREATE INDEX idx_email_logs_status ON email_logs(status);
CREATE INDEX idx_email_logs_sent_at ON email_logs(sent_at);
CREATE INDEX idx_email_logs_response_received ON email_logs(response_received);
```

## Troubleshooting

### SMTP Authentication Failed

**Error:** `smtplib.SMTPAuthenticationError: (535, ...)`

**Solution:**
1. Verify Gmail credentials
2. Use App Password, not regular password
3. Enable "Less secure app access" (not recommended)
4. Check 2-Step Verification is enabled

### IMAP Connection Failed

**Error:** `imaplib.IMAP4.error: ...`

**Solution:**
1. Enable IMAP in Gmail settings
2. Verify IMAP credentials match SMTP
3. Check firewall/network settings

### No Responses Found

**Possible reasons:**
1. Sellers haven't replied yet
2. Responses went to spam folder
3. Email filters are active
4. Wrong inbox is being checked

**Solution:**
- Check spam folder manually
- Wait 24-48 hours for responses
- Verify IMAP credentials

### Rate Limiting

Gmail has sending limits:
- **Free accounts**: ~500 emails/day
- **Workspace accounts**: ~2000 emails/day

**Solution:**
- Use `MAX_EMAILS_PER_DAY` in `.env`
- Implement queue system for bulk operations
- Consider professional email service (SendGrid, AWS SES)

## Best Practices

### 1. Respect Seller Working Hours
```python
# Check seller working hours before sending
if seller_data.get('workingHours'):
    # Send only during working hours
    pass
```

### 2. Avoid Spam
- Don't send multiple emails to same seller about same product
- Wait for response before sending follow-up
- Include clear contact information
- Add unsubscribe option for bulk campaigns

### 3. Email Deliverability
- Use professional email signature
- Include real buyer contact info
- Personalize messages
- Avoid spam trigger words

### 4. Response Handling
- Check responses regularly (daily)
- Update product availability in database
- Track seller response times
- Follow up on positive responses

## Future Enhancements

### Planned Features
- [ ] Task queue (Celery + Redis)
- [ ] Retry mechanism for failed emails
- [ ] Email scheduling based on working hours
- [ ] Response sentiment analysis
- [ ] Automatic follow-up emails
- [ ] Email analytics dashboard
- [ ] Integration with SendGrid/Mailgun
- [ ] Multi-language support (more languages)
- [ ] Email templates editor
- [ ] A/B testing for email content

### Integration Ideas
- Telegram bot for notifications
- Slack integration for team alerts
- Web dashboard for email management
- Mobile app for quick responses

## Security Notes

- Never commit `.env` file to git
- Use App Passwords, not main password
- Rotate credentials regularly
- Monitor for suspicious activity
- Implement rate limiting
- Validate email addresses before sending
- Sanitize user input in messages

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review email_logs table in database
3. Test SMTP connection manually
4. Verify environment variables

## License

Part of MSG Buyer project.

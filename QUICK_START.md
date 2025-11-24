# Email Service - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### Step 1: Configure Gmail

1. **Enable 2-Step Verification**
   - Go to https://myaccount.google.com/security
   - Click "2-Step Verification" → Turn on

2. **Create App Password**
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Enter: "MSG Buyer"
   - Click "Generate"
   - **Copy the 16-character password** (you'll need it next)

3. **Enable IMAP**
   - Go to Gmail Settings → See all settings → Forwarding and POP/IMAP
   - Enable IMAP → Save Changes

### Step 2: Configure .env File

Create `.env` file in project root:

```bash
cp .env.email.example .env
```

Edit `.env` and add your credentials:

```env
# Your Gmail address
SMTP_USER=your-email@gmail.com

# The 16-character App Password from Step 1
SMTP_PASSWORD=abcd efgh ijkl mnop

# Same as SMTP_USER
SENDER_EMAIL=your-email@gmail.com

# Your name or company name
SENDER_NAME=Your Name
```

### Step 3: Test Configuration

Run the test script:

```bash
python test_email_service.py
```

Expected output:
```
✓ DATABASE_URL найден
✓ SMTP_USER: your-email@gmail.com
✓ SMTP_PASSWORD: ****************
✓ Конфигурация валидна
...
🎉 Все тесты пройдены успешно!
```

## 📧 First Email in 3 Commands

### 1. Find a product in your database

```bash
# Run the scraper first if you haven't
python main.py
```

This will scrape products and save them to database.

### 2. Get a product's part_id

Check your database or look at the scraper output for a `part_id` (e.g., `P123456`).

### 3. Send your first inquiry!

```bash
python send_inquiry.py \
  --part-id P123456 \
  --message "Hello! I'm interested in this steering rack. Is it still available? What's the condition?" \
  --buyer-name "Your Name" \
  --buyer-email "your-email@example.com" \
  --buyer-phone "+37012345678" \
  --language en
```

**That's it! 🎉** The email is sent to the seller.

## 📬 Check for Responses

Wait a few hours, then check for seller responses:

```bash
python send_inquiry.py --check-responses
```

Example output:
```
ОТВЕТ #1
================================================================================
От: seller@rrr.lt
Тема: Re: Inquiry about steering-rack - ABC123
Положительный ответ: Да
Есть цена: Да
Цена: €150.0
Доступность: Да

Текст (первые 300 символов):
Hello,

Yes, this part is available. The price is €150. We can ship it tomorrow...
```

## 🎯 Common Use Cases

### Use Case 1: Send inquiry in Lithuanian

```bash
python send_inquiry.py \
  --code ABC123 \
  --message "Sveiki! Ar ši detalė dar prieinama? Kokia būklė?" \
  --buyer-name "Jonas Jonaitis" \
  --buyer-email "jonas@example.com" \
  --language lt
```

### Use Case 2: Check responses and mark as read

```bash
python send_inquiry.py --check-responses --mark-as-read
```

### Use Case 3: Programmatic usage

```python
from sources.services.email_service import EmailService
from sources.database.repository import ProductRepository
from sources.database.config import get_database_url

# Setup
database_url = get_database_url()
email_service = EmailService(database_url)
repository = ProductRepository(database_url)

# Send inquiry
product = repository.find_by_part_id("P123456")
success = email_service.send_product_inquiry(
    product=product,
    message="I'm interested!",
    buyer_email="buyer@example.com",
    buyer_name="John Doe",
    language='en'
)

print(f"Sent: {success}")

# Check responses
responses = email_service.check_responses()
for r in responses:
    print(f"{r['seller_email']}: {r['is_available']}")
```

## ⚠️ Troubleshooting

### Problem: "SMTP Authentication Failed"

**Solution:**
- Make sure you're using App Password, not your regular Gmail password
- Remove spaces from App Password: `abcd efgh ijkl mnop` → `abcdefghijklmnop`
- Verify 2-Step Verification is enabled

### Problem: "DATABASE_URL not found"

**Solution:**
- Make sure `.env` file exists in project root
- Check that `DATABASE_URL` is set in `.env`
- Run `python main.py` once to initialize database

### Problem: "Product not found"

**Solution:**
- Run scraper first: `python main.py`
- Check database for available products
- Use correct `part_id` or `code` from database

### Problem: "No responses found"

**Solution:**
- Wait 24-48 hours for sellers to respond
- Check your spam folder manually
- Verify IMAP is enabled in Gmail settings

## 📚 Next Steps

1. **Read full documentation:** `EMAIL_SERVICE.md`
2. **Try examples:** `python email_example.py`
3. **Customize templates:** Edit `sources/services/email_templates.py`
4. **View email logs:** Check `email_logs` table in database

## 🎓 Learning Path

1. ✅ **You are here** → Quick Start (5 min)
2. Send first inquiry (2 min)
3. Check responses (1 min)
4. Read `EMAIL_SERVICE.md` (15 min)
5. Try bulk inquiries (5 min)
6. Customize templates (10 min)
7. Build your own automation (∞)

## 💡 Tips

- **Test with yourself first:** Send inquiry to your own email to see how it looks
- **Check logs:** All emails are logged in `email_logs` database table
- **Rate limits:** Gmail free accounts limited to ~500 emails/day
- **Response time:** Sellers typically respond within 24-48 hours
- **Language:** Use seller's language (Lithuanian for Lithuanian sellers)

## 🆘 Need Help?

1. Check `EMAIL_SERVICE.md` troubleshooting section
2. Review `test_email_service.py` output
3. Check `logs/` directory for error details
4. Verify `.env` configuration

---

**Ready to send your first email?** Run the command from "First Email in 3 Commands" above! 🚀

"""
Сервис для отправки email продавцам
"""
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import re
import os
from pathlib import Path
import requests

from sources.classes.product import Product
from sources.database.models import EmailLogModel, ConversationModel, MessageModel
from sources.database.repository import ProductRepository, ConversationRepository
from sources.utils.logger import get_logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import uuid

logger = get_logger("email_service")

# Загружаем переменные окружения
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass


class EmailService:
    """
    Сервис для отправки email запросов продавцам
    
    Использует Gmail SMTP для отправки и IMAP для получения ответов
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Инициализация email сервиса
        
        Args:
            database_url: URL подключения к БД (для логирования email)
        """
        # SMTP конфигурация
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.sender_email = os.getenv('SENDER_EMAIL', self.smtp_user)
        self.sender_name = os.getenv('SENDER_NAME', 'MSG Buyer')

        # IMAP конфигурация для получения ответов
        self.imap_host = os.getenv('IMAP_HOST', 'imap.gmail.com')
        self.imap_port = int(os.getenv('IMAP_PORT', '993'))

        # Mailgun конфигурация (для Railway и других хостингов без SMTP)
        self.mailgun_api_key = os.getenv('MAILGUN_API_KEY')
        self.mailgun_domain = os.getenv('MAILGUN_DOMAIN')
        self.mailgun_base_url = os.getenv('MAILGUN_BASE_URL', 'https://api.mailgun.net')
        self.use_mailgun = os.getenv('USE_MAILGUN', 'false').lower() == 'true'

        # Debug mode - send all emails to ADMIN_EMAIL
        self.debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
        self.admin_email = os.getenv('ADMIN_EMAIL')

        # Лимиты
        self.max_emails_per_day = int(os.getenv('MAX_EMAILS_PER_DAY', '50'))
        
        # База данных для логирования
        self.database_url = database_url
        if self.database_url:
            self.engine = create_engine(self.database_url, echo=False)
            self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        else:
            self.engine = None
            self.SessionLocal = None
        
        # Валидация конфигурации
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials не настроены. Проверьте .env файл")
    
    def validate_configuration(self) -> bool:
        """
        Проверка правильности конфигурации
        
        Returns:
            True если конфигурация валидна
        """
        if not self.smtp_user:
            logger.error("SMTP_USER не настроен")
            return False
        
        if not self.smtp_password:
            logger.error("SMTP_PASSWORD не настроен")
            return False
        
        return True
    
    def send_product_inquiry(
        self,
        product: Product,
        message: str,
        buyer_email: str,
        buyer_name: str,
        buyer_phone: Optional[str] = None,
        language: str = 'en'
    ) -> bool:
        """
        Отправка запроса продавцу о конкретном товаре
        
        Args:
            product: Объект Product с данными о товаре
            message: Текст сообщения от покупателя
            buyer_email: Email покупателя для ответа
            buyer_name: Имя покупателя
            buyer_phone: Телефон покупателя (опционально)
            language: Язык сообщения ('en' или 'lt')
            
        Returns:
            True если отправлено успешно
        """
        if not product.seller_email:
            logger.error(f"У товара {product.part_id} нет email продавца")
            return False
        
        if not self.validate_configuration():
            return False
        
        # Формируем тему письма
        subject = self._generate_subject(product, language)
        
        # Формируем тело письма
        body = self._generate_inquiry_body(
            product=product,
            message=message,
            buyer_email=buyer_email,
            buyer_name=buyer_name,
            buyer_phone=buyer_phone,
            language=language
        )
        
        # Отправляем email
        success = self._send_email(
            to_email=product.seller_email,
            subject=subject,
            body=body,
            html=True
        )
        
        # Логируем в БД
        if success and self.SessionLocal:
            self._log_email(
                seller_email=product.seller_email,
                product_part_id=product.part_id,
                subject=subject,
                body=body,
                status='sent'
            )
        
        return success
    
    def send_bulk_inquiries(
        self,
        products: List[Product],
        message: str,
        buyer_email: str,
        buyer_name: str,
        buyer_phone: Optional[str] = None,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Отправка запросов нескольким продавцам о разных товарах
        
        Args:
            products: Список товаров
            message: Текст сообщения
            buyer_email: Email покупателя
            buyer_name: Имя покупателя
            buyer_phone: Телефон покупателя
            language: Язык сообщения
            
        Returns:
            Словарь со статистикой отправки
        """
        results = {
            'total': len(products),
            'sent': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        for product in products:
            try:
                if not product.seller_email:
                    results['skipped'] += 1
                    continue
                
                success = self.send_product_inquiry(
                    product=product,
                    message=message,
                    buyer_email=buyer_email,
                    buyer_name=buyer_name,
                    buyer_phone=buyer_phone,
                    language=language
                )
                
                if success:
                    results['sent'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'product_id': product.part_id,
                    'error': str(e)
                })
                logger.error(f"Ошибка отправки email для товара {product.part_id}: {e}")
        
        return results
    
    def _send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False
    ) -> bool:
        """
        Отправка email через SMTP
        
        Args:
            to_email: Email получателя
            subject: Тема письма
            body: Тело письма
            html: Использовать HTML формат
            
        Returns:
            True если отправлено успешно
        """
        try:
            # Создаем сообщение
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Reply-To'] = self.sender_email
            
            # Добавляем тело письма
            if html:
                msg.attach(MIMEText(body, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Подключаемся к SMTP серверу
            logger.info(f"Подключение к SMTP {self.smtp_host}:{self.smtp_port}")
            if self.smtp_port == 465:
                # SSL connection (port 465)
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                # STARTTLS connection (port 587)
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)

            logger.info(f"Email отправлен на {to_email}")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP ошибка при отправке на {to_email}: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Ошибка при отправке email на {to_email}: {e}", exc_info=True)
            return False
    
    def _generate_subject(self, product: Product, language: str = 'en') -> str:
        """
        Генерация темы письма
        
        Args:
            product: Товар
            language: Язык
            
        Returns:
            Тема письма
        """
        if language == 'lt':
            return f"Užklausa dėl {product.category} - {product.code}"
        else:
            return f"Inquiry about {product.category} - {product.code}"
    
    def _generate_inquiry_body(
        self,
        product: Product,
        message: str,
        buyer_email: str,
        buyer_name: str,
        buyer_phone: Optional[str] = None,
        language: str = 'en'
    ) -> str:
        """
        Генерация тела письма с запросом о товаре
        
        Args:
            product: Товар
            message: Сообщение от покупателя
            buyer_email: Email покупателя
            buyer_name: Имя покупателя
            buyer_phone: Телефон покупателя
            language: Язык письма
            
        Returns:
            HTML тело письма
        """
        if language == 'lt':
            greeting = "Sveiki,"
            intro = "Esu suinteresuotas šia dalimi:"
            details_header = "Detalės informacija:"
            car_header = "Automobilio informacija:"
            message_header = "Mano žinutė:"
            contact_header = "Kontaktinė informacija:"
            name_label = "Vardas:"
            email_label = "El. paštas:"
            phone_label = "Telefonas:"
            footer = "Ačiū už atsakymą!"
            regards = "Pagarbiai,"
        else:
            greeting = "Hello,"
            intro = "I am interested in the following part:"
            details_header = "Part Details:"
            car_header = "Car Details:"
            message_header = "My Message:"
            contact_header = "Contact Information:"
            name_label = "Name:"
            email_label = "Email:"
            phone_label = "Phone:"
            footer = "Thank you for your response!"
            regards = "Best regards,"
        
        # Формируем HTML письмо
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .section {{ margin-bottom: 20px; }}
                .section-title {{ font-weight: bold; color: #2c3e50; margin-bottom: 10px; }}
                .details {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
                .detail-row {{ margin: 5px 0; }}
                .label {{ font-weight: bold; }}
                .message-box {{ background-color: #e8f4f8; padding: 15px; border-left: 4px solid #3498db; margin: 15px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.9em; color: #666; }}
                a {{ color: #3498db; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="container">
                <p>{greeting}</p>
                <p>{intro}</p>
                
                <div class="section">
                    <div class="section-title">{details_header}</div>
                    <div class="details">
                        <div class="detail-row"><span class="label">Code:</span> {product.code}</div>
                        <div class="detail-row"><span class="label">Part ID:</span> {product.part_id}</div>
                        <div class="detail-row"><span class="label">Category:</span> {product.category}</div>
                        {f'<div class="detail-row"><span class="label">Price:</span> €{product.price}</div>' if product.price else ''}
                        {f'<div class="detail-row"><span class="label">URL:</span> <a href="{product.url}">{product.url}</a></div>' if product.url else ''}
        """
        
        # Добавляем детали товара
        if product.item_description:
            for key, value in product.item_description.items():
                if value:
                    html += f'<div class="detail-row"><span class="label">{key.replace("_", " ").title()}:</span> {value}</div>'
        
        html += "</div></div>"
        
        # Добавляем детали автомобиля
        if product.car_details:
            html += f"""
                <div class="section">
                    <div class="section-title">{car_header}</div>
                    <div class="details">
            """
            for key, value in product.car_details.items():
                if value:
                    html += f'<div class="detail-row"><span class="label">{key.replace("_", " ").title()}:</span> {value}</div>'
            html += "</div></div>"
        
        # Добавляем сообщение покупателя
        html += f"""
                <div class="section">
                    <div class="section-title">{message_header}</div>
                    <div class="message-box">
                        {message.replace(chr(10), '<br>')}
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">{contact_header}</div>
                    <div class="details">
                        <div class="detail-row"><span class="label">{name_label}</span> {buyer_name}</div>
                        <div class="detail-row"><span class="label">{email_label}</span> <a href="mailto:{buyer_email}">{buyer_email}</a></div>
        """
        
        if buyer_phone:
            html += f'<div class="detail-row"><span class="label">{phone_label}</span> {buyer_phone}</div>'
        
        html += f"""
                    </div>
                </div>
                
                <div class="footer">
                    <p>{footer}</p>
                    <p>{regards}<br>{buyer_name}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _log_email(
        self,
        seller_email: str,
        product_part_id: str,
        subject: str,
        body: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Логирование отправленного email в БД
        
        Args:
            seller_email: Email продавца
            product_part_id: ID товара
            subject: Тема письма
            body: Тело письма
            status: Статус ('sent', 'failed')
            error_message: Сообщение об ошибке
            
        Returns:
            True если залогировано успешно
        """
        if not self.SessionLocal:
            return False
        
        session: Session = self.SessionLocal()
        try:
            email_log = EmailLogModel(
                seller_email=seller_email,
                product_part_id=product_part_id,
                subject=subject,
                body=body,
                status=status,
                error_message=error_message,
                sent_at=datetime.now(timezone.utc),
                response_received=False
            )
            
            session.add(email_log)
            session.commit()
            logger.debug(f"Email лог сохранен для {seller_email}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка сохранения email лога: {e}", exc_info=True)
            return False
        finally:
            session.close()
    
    def check_responses(self, mark_as_read: bool = False) -> List[Dict[str, Any]]:
        """
        Проверка почтового ящика на наличие ответов от продавцов
        
        Args:
            mark_as_read: Помечать ли письма как прочитанные
            
        Returns:
            Список ответов с распарсенными данными
        """
        if not self.validate_configuration():
            return []
        
        responses = []
        
        try:
            # Подключаемся к IMAP серверу
            logger.info(f"Подключение к IMAP {self.imap_host}:{self.imap_port}")
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.smtp_user, self.smtp_password)
            mail.select('INBOX')
            
            # Ищем непрочитанные письма
            status, messages = mail.search(None, 'UNSEEN' if not mark_as_read else 'ALL')
            
            if status != 'OK':
                logger.warning("Не удалось получить список писем")
                return responses
            
            email_ids = messages[0].split()
            logger.info(f"Найдено {len(email_ids)} непрочитанных писем")
            
            # Обрабатываем каждое письмо
            for email_id in email_ids[-10:]:  # Берем последние 10 писем
                try:
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    
                    if status != 'OK':
                        continue
                    
                    # Парсим email
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    response_data = self._parse_email_response(email_message)
                    if response_data:
                        responses.append(response_data)
                        
                        # Обновляем статус в БД
                        if self.SessionLocal and response_data.get('seller_email'):
                            self._update_response_status(response_data['seller_email'])
                    
                    # Помечаем как прочитанное
                    if mark_as_read:
                        mail.store(email_id, '+FLAGS', '\\Seen')
                        
                except Exception as e:
                    logger.error(f"Ошибка обработки письма {email_id}: {e}", exc_info=True)
                    continue
            
            mail.close()
            mail.logout()
            
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP ошибка: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Ошибка при проверке ответов: {e}", exc_info=True)
        
        return responses
    
    def _parse_email_response(self, email_message) -> Optional[Dict[str, Any]]:
        """
        Парсинг email ответа от продавца
        
        Args:
            email_message: Email сообщение
            
        Returns:
            Словарь с данными ответа
        """
        try:
            # Извлекаем основные поля
            subject = self._decode_header(email_message['Subject'])
            from_email = self._extract_email(email_message['From'])
            date = email_message['Date']
            
            # Извлекаем тело письма
            body = self._get_email_body(email_message)
            
            # Извлекаем информацию о товаре из темы (если есть код)
            product_code = self._extract_product_code(subject)
            
            # Анализируем содержание ответа
            analysis = self._analyze_response_content(body)
            
            response_data = {
                'seller_email': from_email,
                'subject': subject,
                'date': date,
                'body': body,
                'product_code': product_code,
                'is_positive': analysis['is_positive'],
                'has_price': analysis['has_price'],
                'extracted_price': analysis['price'],
                'has_availability': analysis['has_availability'],
                'is_available': analysis['is_available'],
                'keywords': analysis['keywords']
            }
            
            logger.info(f"Распарсен ответ от {from_email}: {subject}")
            return response_data
            
        except Exception as e:
            logger.error(f"Ошибка парсинга email: {e}", exc_info=True)
            return None
    
    def _decode_header(self, header: str) -> str:
        """Декодирование заголовка email"""
        if not header:
            return ""
        
        decoded_parts = decode_header(header)
        result = []
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(encoding or 'utf-8', errors='ignore'))
            else:
                result.append(str(part))
        
        return ''.join(result)
    
    def _extract_email(self, from_field: str) -> str:
        """Извлечение email адреса из поля From"""
        if not from_field:
            return ""
        
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_field)
        return match.group(0) if match else from_field
    
    def _get_email_body(self, email_message) -> str:
        """Извлечение тела письма"""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:
                        pass
                elif content_type == "text/html" and not body:
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            try:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body = str(email_message.get_payload())
        
        return body
    
    def _extract_product_code(self, subject: str) -> Optional[str]:
        """Извлечение кода товара из темы письма"""
        if not subject:
            return None
        
        # Ищем паттерн кода товара (например: ABC123, A1B2C3)
        match = re.search(r'\b([A-Z0-9]{6,})\b', subject)
        return match.group(1) if match else None
    
    def _analyze_response_content(self, body: str) -> Dict[str, Any]:
        """
        Анализ содержания ответа для определения наличия товара, цены и т.д.
        
        Args:
            body: Тело письма
            
        Returns:
            Словарь с результатами анализа
        """
        body_lower = body.lower()
        
        # Позитивные ключевые слова
        positive_keywords = [
            'available', 'in stock', 'yes', 'have', 'can sell', 'can offer',
            'turimas', 'taip', 'turime', 'galime parduoti'
        ]
        
        # Негативные ключевые слова
        negative_keywords = [
            'not available', 'sold out', 'no longer', 'sorry', 'unfortunately',
            'neturime', 'parduota', 'ne', 'deja'
        ]
        
        # Проверка на наличие
        is_positive = any(keyword in body_lower for keyword in positive_keywords)
        is_negative = any(keyword in body_lower for keyword in negative_keywords)
        
        # Поиск цены (€123, 123€, EUR 123, 123.45)
        price_pattern = r'€?\s*(\d+[.,]?\d*)\s*€?|EUR\s*(\d+[.,]?\d*)'
        price_matches = re.findall(price_pattern, body)
        extracted_price = None
        
        if price_matches:
            for match in price_matches:
                price_str = match[0] or match[1]
                if price_str:
                    try:
                        extracted_price = float(price_str.replace(',', '.'))
                        break
                    except:
                        pass
        
        return {
            'is_positive': is_positive and not is_negative,
            'has_price': extracted_price is not None,
            'price': extracted_price,
            'has_availability': is_positive or is_negative,
            'is_available': is_positive and not is_negative,
            'keywords': [kw for kw in positive_keywords + negative_keywords if kw in body_lower]
        }
    
    def _update_response_status(self, seller_email: str) -> bool:
        """
        Обновление статуса получения ответа в БД

        Args:
            seller_email: Email продавца

        Returns:
            True если обновлено успешно
        """
        if not self.SessionLocal:
            return False

        session: Session = self.SessionLocal()
        try:
            # Находим последний отправленный email этому продавцу
            email_log = session.query(EmailLogModel).filter_by(
                seller_email=seller_email,
                response_received=False
            ).order_by(EmailLogModel.sent_at.desc()).first()

            if email_log:
                email_log.response_received = True
                session.commit()
                logger.debug(f"Обновлен статус ответа для {seller_email}")
                return True

            return False

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Ошибка обновления статуса ответа: {e}", exc_info=True)
            return False
        finally:
            session.close()

    # === Conversation-based email methods ===

    def send_conversation_message(
        self,
        conversation_id: int,
        subject: str,
        body: str,
        body_html: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Отправка сообщения в рамках переписки

        Args:
            conversation_id: ID переписки
            subject: Тема письма
            body: Текст письма
            body_html: HTML версия (опционально)

        Returns:
            Словарь с результатом {success, message_id, error}
        """
        if not self.database_url:
            return {'success': False, 'error': 'Database not configured'}

        conv_repo = ConversationRepository(self.database_url)

        # Получаем переписку
        conversation = conv_repo.get_conversation(conversation_id)
        if not conversation:
            return {'success': False, 'error': 'Conversation not found'}

        # Получаем последнее исходящее сообщение для построения цепочки
        messages = conv_repo.get_messages(conversation_id)
        last_outbound = None
        references_list = []

        for msg in messages:
            if msg.message_id:
                references_list.append(msg.message_id)
            if msg.direction == 'outbound' and msg.message_id:
                last_outbound = msg

        # Генерируем Message-ID
        message_id = f"<{uuid.uuid4()}@msg-buyer.local>"
        in_reply_to = last_outbound.message_id if last_outbound else None
        references = ' '.join(references_list) if references_list else None

        # Сохраняем сообщение как draft
        message = conv_repo.add_message(
            conversation_id=conversation_id,
            direction='outbound',
            subject=subject,
            body=body,
            body_html=body_html,
            status='draft',
            message_id=message_id,
            in_reply_to=in_reply_to,
            references=references
        )

        if not message:
            return {'success': False, 'error': 'Failed to create message'}

        # Отправляем email
        success = self._send_email_with_headers(
            to_email=conversation.seller_email,
            subject=subject,
            body=body_html or body,
            html=body_html is not None,
            message_id=message_id,
            in_reply_to=in_reply_to,
            references=references
        )

        # Обновляем статус сообщения
        if success:
            conv_repo.update_message_status(
                message_id=message.id,
                status='sent',
                sent_at=datetime.now(timezone.utc),
                email_message_id=message_id
            )
            # Обновляем статус переписки
            conv_repo.update_conversation_status(conversation_id, 'pending_reply')
            return {'success': True, 'message_id': message.id, 'email_message_id': message_id}
        else:
            conv_repo.update_message_status(
                message_id=message.id,
                status='failed',
                error_message='Failed to send email'
            )
            return {'success': False, 'error': 'Failed to send email', 'message_id': message.id}

    def _send_email_with_headers(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False,
        message_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None
    ) -> bool:
        """
        Отправка email с дополнительными заголовками для threading

        Args:
            to_email: Email получателя
            subject: Тема письма
            body: Тело письма
            html: Использовать HTML формат
            message_id: Message-ID header
            in_reply_to: In-Reply-To header
            references: References header

        Returns:
            True если отправлено успешно
        """
        try:
            # Debug mode: redirect all emails to ADMIN_EMAIL
            actual_recipient = to_email
            if self.debug_mode and self.admin_email:
                actual_recipient = self.admin_email
                # Modify subject to show original recipient
                subject = f"[DEBUG to: {to_email}] {subject}"
                logger.info(f"DEBUG MODE: Redirecting email from {to_email} to {self.admin_email}")

            # Use Mailgun if configured
            if self.use_mailgun:
                return self._send_email_mailgun(
                    to_email=actual_recipient,
                    subject=subject,
                    body=body,
                    html=html,
                    message_id=message_id,
                    in_reply_to=in_reply_to,
                    references=references,
                    original_recipient=to_email if self.debug_mode else None
                )

            # # Создаем сообщение для SMTP
            # msg = MIMEMultipart('alternative')
            # msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            # msg['To'] = actual_recipient
            # msg['Subject'] = subject
            # msg['Reply-To'] = self.sender_email

            # # Добавляем заголовки для threading
            # if message_id:
            #     msg['Message-ID'] = message_id
            # if in_reply_to:
            #     msg['In-Reply-To'] = in_reply_to
            # if references:
            #     msg['References'] = references

            # # Добавляем тело письма
            # if html:
            #     msg.attach(MIMEText(body, 'html', 'utf-8'))
            # else:
            #     msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # # Подключаемся к SMTP серверу
            # logger.info(f"Подключение к SMTP {self.smtp_host}:{self.smtp_port}")
            # if self.smtp_port == 465:
            #     # SSL connection (port 465)
            #     with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
            #         server.login(self.smtp_user, self.smtp_password)
            #         server.send_message(msg)
            # else:
            #     # STARTTLS connection (port 587)
            #     with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            #         server.starttls()
            #         server.login(self.smtp_user, self.smtp_password)
            #         server.send_message(msg)

            logger.info(f"Email отправлен на {actual_recipient}" + (f" (original: {to_email})" if self.debug_mode else ""))
            return True

        except smtplib.SMTPException as e:
            logger.error(f"SMTP ошибка при отправке на {to_email}: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Ошибка при отправке email на {to_email}: {e}", exc_info=True)
            return False

    def _send_email_mailgun(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False,
        message_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        original_recipient: Optional[str] = None
    ) -> bool:
        """
        Отправка email через Mailgun API

        Args:
            to_email: Email получателя
            subject: Тема письма
            body: Тело письма
            html: Использовать HTML формат
            message_id: Message-ID header
            in_reply_to: In-Reply-To header
            references: References header
            original_recipient: Оригинальный получатель (для debug mode логирования)

        Returns:
            True если отправлено успешно
        """
        if not self.mailgun_api_key or not self.mailgun_domain:
            logger.error("Mailgun не настроен: отсутствует API_KEY или DOMAIN")
            return False

        try:
            url = f"{self.mailgun_base_url}/v3/{self.mailgun_domain}/messages"

            # Reply-To: env variable REPLY_TO_EMAIL or sender_email
            reply_to_email = os.getenv('REPLY_TO_EMAIL') or self.sender_email

            # Формируем данные запроса
            data = {
                "from": f"{self.sender_name} <{self.sender_email}>",
                "to": to_email,
                "subject": subject,
                "h:Reply-To": reply_to_email,
            }

            # Тело письма
            if html:
                data["html"] = body
            else:
                data["text"] = body

            # Заголовки для threading
            if message_id:
                data["h:Message-ID"] = message_id
            if in_reply_to:
                data["h:In-Reply-To"] = in_reply_to
            if references:
                data["h:References"] = references

            logger.info(f"Отправка email через Mailgun на {to_email}")

            response = requests.post(
                url,
                auth=("api", self.mailgun_api_key),
                data=data,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"Email отправлен через Mailgun на {to_email}" +
                           (f" (original: {original_recipient})" if original_recipient else ""))
                return True
            else:
                logger.error(f"Mailgun ошибка {response.status_code}: {response.text}")
                return False

        except requests.RequestException as e:
            logger.error(f"Ошибка при отправке через Mailgun на {to_email}: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка Mailgun: {e}", exc_info=True)
            return False

    def check_and_save_responses(self, mark_as_read: bool = False) -> List[Dict[str, Any]]:
        """
        Проверка почтового ящика и сохранение ответов в соответствующие переписки.
        Проверяет только письма от продавцов, с которыми есть активные переписки.

        Args:
            mark_as_read: Помечать ли письма как прочитанные

        Returns:
            Список сохраненных ответов
        """
        if not self.validate_configuration() or not self.database_url:
            return []

        conv_repo = ConversationRepository(self.database_url)
        saved_responses = []

        # Get all seller emails we have conversations with
        all_conversations = conv_repo.get_all_conversations()
        seller_emails = set(c.seller_email for c in all_conversations)

        if not seller_emails:
            logger.info("No active conversations, skipping email check")
            return []

        logger.info(f"Checking emails from {len(seller_emails)} sellers")

        try:
            # Подключаемся к IMAP серверу
            logger.info(f"Подключение к IMAP {self.imap_host}:{self.imap_port}")
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.smtp_user, self.smtp_password)
            mail.select('INBOX')

            # Build IMAP search query for unread emails from our sellers
            # IMAP OR syntax: (OR (FROM "a@b.com") (OR (FROM "c@d.com") (FROM "e@f.com")))
            if len(seller_emails) == 1:
                search_query = f'(UNSEEN FROM "{list(seller_emails)[0]}")'
            else:
                # Build nested OR query for multiple sellers
                emails_list = list(seller_emails)
                search_query = f'FROM "{emails_list[-1]}"'
                for email_addr in reversed(emails_list[:-1]):
                    search_query = f'OR (FROM "{email_addr}") ({search_query})'
                search_query = f'(UNSEEN {search_query})'

            logger.info(f"IMAP search: {search_query}")
            status, messages = mail.search(None, search_query)

            if status != 'OK':
                logger.warning("Не удалось получить список писем")
                return saved_responses

            email_ids = messages[0].split()
            logger.info(f"Найдено {len(email_ids)} непрочитанных писем")

            # Обрабатываем каждое письмо
            for email_id in email_ids:
                try:
                    status, msg_data = mail.fetch(email_id, '(RFC822)')

                    if status != 'OK':
                        continue

                    # Парсим email
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)

                    # Извлекаем заголовки для связывания
                    in_reply_to = email_message.get('In-Reply-To', '').strip()
                    references = email_message.get('References', '').strip()
                    from_email = self._extract_email(email_message['From'])
                    subject = self._decode_header(email_message['Subject'])
                    body = self._get_email_body(email_message)
                    received_message_id = email_message.get('Message-ID', '').strip()

                    # Пытаемся найти связанную переписку
                    conversation = None

                    # Сначала по In-Reply-To
                    if in_reply_to:
                        conversation = conv_repo.find_conversation_by_in_reply_to(in_reply_to)

                    # Затем по References
                    if not conversation and references:
                        for ref in references.split():
                            ref = ref.strip()
                            if ref:
                                conversation = conv_repo.find_conversation_by_message_id(ref)
                                if conversation:
                                    break

                    # Если нашли переписку, сохраняем ответ
                    if conversation:
                        message = conv_repo.add_message(
                            conversation_id=conversation.id,
                            direction='inbound',
                            subject=subject,
                            body=body,
                            status='received',
                            message_id=received_message_id,
                            in_reply_to=in_reply_to,
                            references=references
                        )

                        if message:
                            # Classify response with LLM (pass conversation_id to load full history)
                            classification = self._classify_response_with_llm(conversation.id, body)

                            # Save classification to database
                            conv_repo.save_classification(conversation.id, classification)

                            saved_responses.append({
                                'conversation_id': conversation.id,
                                'message_id': message.id,
                                'from_email': from_email,
                                'subject': subject,
                                'body': body[:200] + '...' if len(body) > 200 else body,
                                'classification': classification
                            })
                            logger.info(f"Сохранен ответ в переписку {conversation.id} от {from_email}, classification: {classification.get('status', 'unknown')}")
                    else:
                        # Переписка не найдена - логируем
                        logger.info(f"Не найдена переписка для письма от {from_email}: {subject}")

                    # Помечаем как прочитанное
                    if mark_as_read:
                        mail.store(email_id, '+FLAGS', '\\Seen')

                except Exception as e:
                    logger.error(f"Ошибка обработки письма {email_id}: {e}", exc_info=True)
                    continue

            mail.close()
            mail.logout()

        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP ошибка: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Ошибка при проверке ответов: {e}", exc_info=True)

        return saved_responses

    def create_and_send_conversation(
        self,
        seller_email: str,
        position_ids: List[str],
        subject: str,
        body: str,
        body_html: Optional[str] = None,
        language: str = 'en',
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создание новой переписки и отправка первого сообщения

        Args:
            seller_email: Email продавца
            position_ids: Список part_id позиций
            subject: Тема письма
            body: Текст письма
            body_html: HTML версия (опционально)
            language: Язык переписки
            title: Название переписки (опционально)

        Returns:
            Словарь с результатом {success, conversation_id, message_id, error}
        """
        if not self.database_url:
            return {'success': False, 'error': 'Database not configured'}

        if not self.validate_configuration():
            return {'success': False, 'error': 'SMTP not configured'}

        conv_repo = ConversationRepository(self.database_url)

        # Создаем переписку
        conversation = conv_repo.create_conversation(
            seller_email=seller_email,
            position_ids=position_ids,
            title=title or subject,
            language=language
        )

        if not conversation:
            return {'success': False, 'error': 'Failed to create conversation'}

        # Отправляем первое сообщение
        result = self.send_conversation_message(
            conversation_id=conversation.id,
            subject=subject,
            body=body,
            body_html=body_html
        )

        if result['success']:
            return {
                'success': True,
                'conversation_id': conversation.id,
                'message_id': result['message_id'],
                'email_message_id': result.get('email_message_id')
            }
        else:
            # Удаляем переписку если не удалось отправить
            conv_repo.delete_conversation(conversation.id)
            return {'success': False, 'error': result.get('error', 'Failed to send message')}

    def _classify_response_with_llm(self, conversation_id: int, body: str) -> Dict[str, Any]:
        """
        Classify seller response using LLM with full conversation history.

        Args:
            conversation_id: ID of the conversation to load messages from
            body: Latest email body text (fallback for basic classification)

        Returns:
            Classification result dict
        """
        try:
            from sources.llm_utils.mail_response_analyzer import analyze_seller_response

            # Load all messages from conversation
            conv_repo = ConversationRepository(self.database_url)
            conv_data = conv_repo.get_conversation_with_messages(conversation_id)

            if not conv_data:
                logger.warning(f"Conversation {conversation_id} not found, using basic classification")
                return self._basic_response_classification(body)

            messages = conv_data.get('messages', [])
            conversation = conv_data.get('conversation', {})

            # Format positions info from conversation
            position_ids = conversation.get('position_ids', [])
            positions_info = f"Position IDs: {', '.join(position_ids)}" if position_ids else None

            # Call LLM analyzer with full conversation
            result = analyze_seller_response(messages)

            # Convert Pydantic model to dict
            return result.model_dump()

        except ImportError:
            logger.warning("LLM analyzer not available, using basic classification")
            return self._basic_response_classification(body)
        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            return self._basic_response_classification(body)

    def _basic_response_classification(self, body: str) -> Dict[str, Any]:
        """Fallback basic classification without LLM"""
        body_lower = body.lower()

        # Basic keyword detection
        positive_keywords = ['yes', 'available', 'in stock', 'can offer', 'interested', 'price', 'tak', 'mamy', 'dostępne']
        negative_keywords = ['no', 'sorry', 'unavailable', 'out of stock', 'nie', 'niestety', 'brak']

        is_positive = any(kw in body_lower for kw in positive_keywords)
        is_negative = any(kw in body_lower for kw in negative_keywords)

        if is_positive and not is_negative:
            sentiment = 'positive'
            intent = 'interested'
        elif is_negative and not is_positive:
            sentiment = 'negative'
            intent = 'not_interested'
        else:
            sentiment = 'neutral'
            intent = 'need_more_info'

        return {
            'sentiment': sentiment,
            'intent': intent,
            'has_price': any(c.isdigit() for c in body) and ('€' in body or 'eur' in body_lower or 'pln' in body_lower),
            'has_availability': any(kw in body_lower for kw in ['stock', 'available', 'mamy', 'dostępne']),
            'summary': body[:100] + '...' if len(body) > 100 else body,
            'method': 'basic'
        }

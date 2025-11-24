"""
Шаблоны email сообщений
"""
from typing import Dict, Any, Optional
from sources.classes.product import Product


class EmailTemplates:
    """
    Коллекция шаблонов для различных типов email
    """
    
    @staticmethod
    def get_inquiry_template(
        product: Product,
        message: str,
        buyer_name: str,
        buyer_email: str,
        buyer_phone: Optional[str] = None,
        language: str = 'en'
    ) -> Dict[str, str]:
        """
        Получить шаблон запроса о товаре
        
        Args:
            product: Товар
            message: Сообщение покупателя
            buyer_name: Имя покупателя
            buyer_email: Email покупателя
            buyer_phone: Телефон покупателя
            language: Язык ('en' или 'lt')
            
        Returns:
            Словарь с 'subject' и 'body'
        """
        if language == 'lt':
            return EmailTemplates._get_lt_inquiry_template(
                product, message, buyer_name, buyer_email, buyer_phone
            )
        else:
            return EmailTemplates._get_en_inquiry_template(
                product, message, buyer_name, buyer_email, buyer_phone
            )
    
    @staticmethod
    def _get_en_inquiry_template(
        product: Product,
        message: str,
        buyer_name: str,
        buyer_email: str,
        buyer_phone: Optional[str] = None
    ) -> Dict[str, str]:
        """Английский шаблон запроса"""
        subject = f"Inquiry about {product.category} - {product.code}"
        
        body = f"""
Hello,

I am interested in the following auto part:

Part Details:
- Code: {product.code}
- Part ID: {product.part_id}
- Category: {product.category}
"""
        
        if product.price:
            body += f"- Listed Price: €{product.price}\n"
        
        if product.url:
            body += f"- URL: {product.url}\n"
        
        if product.item_description:
            body += "\nItem Description:\n"
            for key, value in product.item_description.items():
                if value:
                    body += f"- {key.replace('_', ' ').title()}: {value}\n"
        
        if product.car_details:
            body += "\nCar Details:\n"
            for key, value in product.car_details.items():
                if value:
                    body += f"- {key.replace('_', ' ').title()}: {value}\n"
        
        body += f"\n{message}\n\n"
        body += f"Contact Information:\n"
        body += f"Name: {buyer_name}\n"
        body += f"Email: {buyer_email}\n"
        
        if buyer_phone:
            body += f"Phone: {buyer_phone}\n"
        
        body += f"\nThank you for your response!\n\n"
        body += f"Best regards,\n{buyer_name}"
        
        return {'subject': subject, 'body': body}
    
    @staticmethod
    def _get_lt_inquiry_template(
        product: Product,
        message: str,
        buyer_name: str,
        buyer_email: str,
        buyer_phone: Optional[str] = None
    ) -> Dict[str, str]:
        """Литовский шаблон запроса"""
        subject = f"Užklausa dėl {product.category} - {product.code}"
        
        body = f"""
Sveiki,

Esu suinteresuotas šia automobilių dalimi:

Detalės informacija:
- Kodas: {product.code}
- Dalies ID: {product.part_id}
- Kategorija: {product.category}
"""
        
        if product.price:
            body += f"- Nurodyta kaina: €{product.price}\n"
        
        if product.url:
            body += f"- URL: {product.url}\n"
        
        if product.item_description:
            body += "\nDetalės aprašymas:\n"
            for key, value in product.item_description.items():
                if value:
                    body += f"- {key.replace('_', ' ').title()}: {value}\n"
        
        if product.car_details:
            body += "\nAutomobilio informacija:\n"
            for key, value in product.car_details.items():
                if value:
                    body += f"- {key.replace('_', ' ').title()}: {value}\n"
        
        body += f"\n{message}\n\n"
        body += f"Kontaktinė informacija:\n"
        body += f"Vardas: {buyer_name}\n"
        body += f"El. paštas: {buyer_email}\n"
        
        if buyer_phone:
            body += f"Telefonas: {buyer_phone}\n"
        
        body += f"\nAčiū už atsakymą!\n\n"
        body += f"Pagarbiai,\n{buyer_name}"
        
        return {'subject': subject, 'body': body}
    
    @staticmethod
    def get_price_negotiation_template(
        product: Product,
        offered_price: float,
        buyer_name: str,
        buyer_email: str,
        language: str = 'en'
    ) -> Dict[str, str]:
        """
        Получить шаблон для переговоров о цене
        
        Args:
            product: Товар
            offered_price: Предложенная цена
            buyer_name: Имя покупателя
            buyer_email: Email покупателя
            language: Язык
            
        Returns:
            Словарь с 'subject' и 'body'
        """
        if language == 'lt':
            subject = f"Kainos pasiūlymas - {product.code}"
            body = f"""
Sveiki,

Esu suinteresuotas jūsų skelbime nurodytu {product.category} (kodas: {product.code}).

Nurodyta kaina: €{product.price}
Mano pasiūlymas: €{offered_price}

Ar galėtumėte apsvarstyti šį pasiūlymą?

Kontaktai:
{buyer_name}
{buyer_email}

Ačiū!
"""
        else:
            subject = f"Price Offer - {product.code}"
            body = f"""
Hello,

I am interested in your {product.category} (code: {product.code}).

Listed price: €{product.price}
My offer: €{offered_price}

Would you consider this offer?

Contact:
{buyer_name}
{buyer_email}

Thank you!
"""
        
        return {'subject': subject, 'body': body}
    
    @staticmethod
    def get_multi_product_inquiry_template(
        products: list,
        message: str,
        buyer_name: str,
        buyer_email: str,
        language: str = 'en'
    ) -> Dict[str, str]:
        """
        Получить шаблон запроса о нескольких товарах
        
        Args:
            products: Список товаров
            message: Сообщение покупателя
            buyer_name: Имя покупателя
            buyer_email: Email покупателя
            language: Язык
            
        Returns:
            Словарь с 'subject' и 'body'
        """
        if language == 'lt':
            subject = f"Užklausa dėl {len(products)} dalių"
            body = f"Sveiki,\n\nEsu suinteresuotas šiomis dalimis:\n\n"
            
            for i, product in enumerate(products, 1):
                body += f"{i}. {product.code} - {product.category}"
                if product.price:
                    body += f" (€{product.price})"
                body += "\n"
            
            body += f"\n{message}\n\n"
            body += f"Kontaktai:\n{buyer_name}\n{buyer_email}\n\nAčiū!"
        else:
            subject = f"Inquiry about {len(products)} parts"
            body = f"Hello,\n\nI am interested in the following parts:\n\n"
            
            for i, product in enumerate(products, 1):
                body += f"{i}. {product.code} - {product.category}"
                if product.price:
                    body += f" (€{product.price})"
                body += "\n"
            
            body += f"\n{message}\n\n"
            body += f"Contact:\n{buyer_name}\n{buyer_email}\n\nThank you!"
        
        return {'subject': subject, 'body': body}

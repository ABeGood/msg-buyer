"""
(01;>= ?5@2>3> :>=B0:B=>3> ?8AL<0 4;O ?>AB02I8:>2 @C;52KE @55:
First contact email template for steering rack suppliers
"""
from typing import List, Optional
from dataclasses import dataclass

# Import Product class for type hints
from sources.classes.product import Product


@dataclass
class FirstContactTemplate:
    """
    (01;>= ?8AL<0 =0 @07=KE O7K:0E
    """
    subject: str
    body: str
    language: str


# =============================================================================
# RUSSIAN ( CAA:89)
# =============================================================================
TEMPLATE_RU = FirstContactTemplate(
    language="ru",
    subject="0?@>A =0 A>B@C4=8G5AB2> 70:C?:0 @C;52KE @55: (Master Service)",
    body="""

456

{parts_list}

123
"""
)


# =============================================================================
# UKRAINIAN (#:@0W=AL:0)
# =============================================================================
# TEMPLATE_UK = FirstContactTemplate(
#     language="uk",
#     subject="0?8B =0 A?V2?@0FN  70:C?V2;O @C;L>28E @59>: (Master Service)",
#     body="""VB0N!

# 5=5 720B8 0A8;L, O ?@54AB02;ON :><?0=VN Master Service (#:@0W=0). 8 A?5FV0;V7CT<>AO =0 ?@>406C B0 2V4=>2;5==V @C;L>28E @59>: V =0A>AV2 .

# 0@07V HC:0T<> =>28E ?0@B=5@V2 C >;LIV 4;O @53C;O@=8E 70:C?V25;L 1/2 @C;L>28E @59>: (>@83V=0;, 157 ?>H:>465=L :>@?CAC B0 :@V?;5=L).

# ;0=>20=V >1AO38 70:C?V25;L  2V4 500 4> 1000 HBC: 70 ?0@BVN, 7 <>6;82VABN ?>ABV9=>W A?V2?@0FV ?@8 CA?VH=><C ?5@H><C 70<>2;5==V.

# {parts_list}

# C45<> 24OG=V, O:I> 28 7<>65B5 ?>2V4><8B8:
# " 0O2=VABL 0A>@B8<5=BC =0 AB>FV
# " '0AB>B0 ?>?>2=N20=>ABV AB>:C

# "0:>6 1C45<> @04V, O:I> 7<>65B5 =04VA;0B8 D>B> B8?>28E ?0@BV9 01> :>@>B:89 >?8A 0A>@B8<5=BC.

# 8 2V4:@8BV 4> 4V0;>3C B0 3>B>2V >13>2>@8B8 45B0;V B5AB>2>W 70:C?V2;V.

#  ?>203>N,
# 0A8;L
# Master Service (#:@0W=0)
# """
# )


# =============================================================================
# ENGLISH
# =============================================================================
TEMPLATE_EN = FirstContactTemplate(
    language="en",
    subject="Partnership Inquiry Steering Rack Procurement (Master Service)",
    body="""Hello!

My name is Vasyl, and I represent Master Service (Ukraine). We specialize in the sale and remanufacturing of steering racks and power steering pumps.

We are currently looking for new partners in Poland for regular purchases of used steering racks (original parts, without damage to the housing or mounts).

Our planned purchase volumes are 500 to 1,000 units per batch, with the possibility of ongoing cooperation following a successful first order.

{parts_list}

We would appreciate it if you could provide information on:
" Current stock availability
" Stock replenishment frequency

We would also be grateful if you could send photos of typical batches or a brief description of your product range.

We are open to discussion and ready to negotiate the details of a trial purchase.

Best regards,
Vasyl
Master Service (Ukraine)
"""
)


# =============================================================================
# GERMAN (Deutsch)
# =============================================================================
# TEMPLATE_DE = FirstContactTemplate(
#     language="de",
#     subject="Kooperationsanfrage Einkauf von Lenkgetrieben (Master Service)",
#     body="""Guten Tag!

# Mein Name ist Vasyl, und ich vertrete die Firma Master Service (Ukraine). Wir sind spezialisiert auf den Verkauf und die Aufarbeitung von Lenkgetrieben und Servolenkungspumpen.

# Derzeit suchen wir neue Partner in Polen f�r regelm��ige Eink�ufe von gebrauchten Lenkgetrieben (Originalteile, ohne Besch�digungen am Geh�use oder an den Befestigungen).

# Unsere geplanten Einkaufsmengen liegen bei 500 bis 1.000 St�ck pro Charge, mit der M�glichkeit einer dauerhaften Zusammenarbeit nach einer erfolgreichen Erstbestellung.

# {parts_list}

# Wir w�ren Ihnen dankbar, wenn Sie uns folgende Informationen mitteilen k�nnten:
# " Aktuelle Lagerverf�gbarkeit
# " H�ufigkeit der Lagerauff�llung

# Wir w�rden uns auch freuen, wenn Sie uns Fotos typischer Chargen oder eine kurze Beschreibung Ihres Sortiments zusenden k�nnten.

# Wir sind offen f�r einen Dialog und bereit, die Details eines Probekaufs zu besprechen.

# Mit freundlichen Gr��en,
# Vasyl
# Master Service (Ukraine)
# """
# )


# =============================================================================
# All templates dictionary
# =============================================================================
TEMPLATES = {
    "ru": TEMPLATE_RU,
    # "uk": TEMPLATE_UK,
    "en": TEMPLATE_EN,
    # "de": TEMPLATE_DE,
}


def format_parts_list(products: List[Product], language: str = "en") -> str:
    """
    $>@<0B8@>20=85 A?8A:0 B>20@>2 4;O 2AB02:8 2 ?8AL<>

    Args:
        products: !?8A>: >1J5:B>2 Product
        language: /7K: D>@<0B8@>20=8O (ru, uk, en, de)

    Returns:
        BD>@<0B8@>20==K9 B5:AB A> A?8A:>< B>20@>2
    """
    if not products:
        return ""

    # Headers by language
    headers = {
        "ru": "123:",
        "uk": "456:",
        "en": "We are interested in the following items:",
        "de": "Wir interessieren uns f�r folgende Positionen:",
    }

    header = headers.get(language, headers["en"])
    lines = [header, ""]

    for product in products:
        # Format each product line
        parts = []

        if product.code:
            parts.append(f"SKU: {product.code}")

        if product.item_description:
            if product.item_description.get("manufacturer_code"):
                parts.append(f"Manufacturer: {product.item_description['manufacturer_code']}")
            if product.item_description.get("oem_code"):
                parts.append(f"OEM: {product.item_description['oem_code']}")

        if product.car_details:
            car_info = []
            if product.car_details.get("make"):
                car_info.append(product.car_details["make"])
            if product.car_details.get("model"):
                car_info.append(product.car_details["model"])
            if product.car_details.get("year"):
                car_info.append(f"({product.car_details['year']})")
            if car_info:
                parts.append(" ".join(car_info))

        if product.price:
            parts.append(f"�{product.price:.2f}")

        line = " | ".join(parts) if parts else f"Part ID: {product.part_id}"
        lines.append(f" {line}")

    lines.append("")
    return "\n".join(lines)


def format_first_contact_email(
    products: Optional[List[Product]] = None,
    language: str = "en",
    custom_parts_text: Optional[str] = None
) -> FirstContactTemplate:
    """
    $>@<0B8@>20=85 H01;>=0 ?8AL<0 A ?>4AB0=>2:>9 A?8A:0 B>20@>2

    Args:
        products: !?8A>: >1J5:B>2 Product 4;O 2:;NG5=8O 2 ?8AL<>
        language: /7K: ?8AL<0 (ru, uk, en, de)
        custom_parts_text: @>872>;L=K9 B5:AB 2<5AB> 02B><0B8G5A:>3> A?8A:0

    Returns:
        FirstContactTemplate A 70?>;=5==K< B5;>< ?8AL<0
    """
    template = TEMPLATES.get(language, TEMPLATE_EN)

    # Format parts list
    if custom_parts_text:
        parts_text = custom_parts_text
    elif products:
        parts_text = format_parts_list(products, language)
    else:
        parts_text = ""

    # Create new template with formatted body
    formatted_body = template.body.format(parts_list=parts_text)

    return FirstContactTemplate(
        language=template.language,
        subject=template.subject,
        body=formatted_body
    )


# =============================================================================
# Example usage
# =============================================================================
if __name__ == "__main__":
    from sources.database.repository import ProductRepository
    from sources.database.config import get_database_url

    # Get products from database
    repo = ProductRepository(get_database_url())
    products = repo.get_all()

    if not products:
        print("No products found in database")
    else:
        print(f"Found {len(products)} products in database")

        # Generate email in different languages
        for lang in ["ru", "uk", "en"]:
            email = format_first_contact_email(products, language=lang)
            print(f"\n{'=' * 60}")
            print(f"Language: {lang.upper()}")
            print(f"{'=' * 60}")
            print(f"Subject: {email.subject}")
            print(f"\n{email.body}")

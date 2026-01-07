"""
FastAPI приложение с авторизацией через Google OAuth.
Новые пользователи требуют одобрения админа.
"""
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from jose import jwt, JWTError

# Загрузка .env
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

from sources.database.repository import UserRepository, ProductRepository, ConversationRepository, CatalogMatchRepository
from sources.database.models import UserModel
from sources.services.email_service import EmailService
from pydantic import BaseModel
from typing import List


# ================== CONFIG ==================

DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Email настройки
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 дней

# Templates
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ================== REPOSITORY ==================

user_repo = UserRepository(DATABASE_URL) if DATABASE_URL else None
product_repo = ProductRepository(DATABASE_URL) if DATABASE_URL else None
conv_repo = ConversationRepository(DATABASE_URL) if DATABASE_URL else None
catalog_match_repo = CatalogMatchRepository(DATABASE_URL) if DATABASE_URL else None
email_service = EmailService(DATABASE_URL) if DATABASE_URL else None


def get_user_repo() -> UserRepository:
    if not user_repo:
        raise HTTPException(status_code=500, detail="Database not configured")
    return user_repo


def get_product_repo() -> ProductRepository:
    if not product_repo:
        raise HTTPException(status_code=500, detail="Database not configured")
    return product_repo


def get_conv_repo() -> ConversationRepository:
    if not conv_repo:
        raise HTTPException(status_code=500, detail="Database not configured")
    return conv_repo


def get_catalog_match_repo() -> CatalogMatchRepository:
    if not catalog_match_repo:
        raise HTTPException(status_code=500, detail="Database not configured")
    return catalog_match_repo


def get_email_service() -> EmailService:
    if not email_service:
        raise HTTPException(status_code=500, detail="Email service not configured")
    return email_service


# ================== PYDANTIC MODELS ==================

class CreateConversationRequest(BaseModel):
    seller_email: str
    position_ids: List[str]
    subject: str
    body: str
    language: str = 'en'
    title: Optional[str] = None


class SendMessageRequest(BaseModel):
    subject: str
    body: str


# ================== CONFIG FOR BACKGROUND TASKS ==================

EMAIL_CHECK_INTERVAL_MINUTES = int(os.getenv('EMAIL_CHECK_INTERVAL_MINUTES', '5'))
EMAIL_CHECK_ENABLED = os.getenv('EMAIL_CHECK_ENABLED', 'false').lower() == 'true'


# ================== BACKGROUND TASK ==================

async def check_responses_task():
    """Background task that checks for email responses periodically"""
    while True:
        try:
            await asyncio.sleep(EMAIL_CHECK_INTERVAL_MINUTES * 60)
            if email_service:
                print(f"[{datetime.now()}] Checking for email responses...")
                responses = email_service.check_and_save_responses(mark_as_read=True)
                if responses:
                    print(f"[{datetime.now()}] Found {len(responses)} new responses")
                else:
                    print(f"[{datetime.now()}] No new responses")
        except asyncio.CancelledError:
            print("Email check task cancelled")
            break
        except Exception as e:
            print(f"[{datetime.now()}] Error checking responses: {e}")


# ================== LIFESPAN ==================

@asynccontextmanager
async def lifespan(app: FastAPI):
    if user_repo:
        user_repo.create_tables()
    if conv_repo:
        conv_repo.create_tables()

    # Start background task if enabled
    task = None
    if EMAIL_CHECK_ENABLED and email_service:
        print(f"Starting email check background task (every {EMAIL_CHECK_INTERVAL_MINUTES} minutes)")
        task = asyncio.create_task(check_responses_task())

    yield

    # Cancel background task on shutdown
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


# ================== APP ==================

app = FastAPI(title="MSG Buyer API", version="1.0.0", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

security = HTTPBearer()

# OAuth настройка
oauth = OAuth()
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)


# ================== JWT UTILS ==================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=JWT_EXPIRATION_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


# ================== EMAIL ==================

def send_approval_request_email(user_email: str, user_name: str):
    """Отправка письма админу о запросе на одобрение"""
    if not all([SMTP_USER, SMTP_PASSWORD, ADMIN_EMAIL]):
        print(f"[INFO] Email not configured. New user registration: {user_email} ({user_name})")
        return

    approval_link = f"{BASE_URL}/admin/approve/{user_email}"

    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = ADMIN_EMAIL
    msg['Subject'] = f"[MSG Buyer] Access request: {user_email}"

    body = f"""
New user requests access to MSG Buyer:

Email: {user_email}
Name: {user_name}

To approve, click the link:
{approval_link}

Or use API endpoint:
POST /admin/approve/{user_email}
"""

    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"[INFO] Approval request email sent for: {user_email}")
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")


# ================== AUTH DEPENDENCIES ==================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    repo: UserRepository = Depends(get_user_repo)
) -> UserModel:
    """Получение текущего пользователя из JWT токена"""
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = repo.find_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


async def get_approved_user(user: UserModel = Depends(get_current_user)) -> UserModel:
    """Получение одобренного пользователя"""
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending approval"
        )
    return user


async def get_admin_user(user: UserModel = Depends(get_current_user)) -> UserModel:
    """Проверка, что пользователь - админ"""
    if user.email != ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


# ================== PAGE ROUTES ==================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to login"""
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/auth/callback", response_class=HTMLResponse)
async def auth_callback_page(request: Request):
    """Auth callback page (handles token from OAuth)"""
    return templates.TemplateResponse("callback.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard page (legacy redirect)"""
    return templates.TemplateResponse("razom_catalog.html", {"request": request})


@app.get("/razom-catalog", response_class=HTMLResponse)
async def razom_catalog_page(request: Request):
    """Catalog Matches page"""
    return templates.TemplateResponse("razom_catalog.html", {"request": request})


@app.get("/sellers", response_class=HTMLResponse)
async def dashboard_sellers_page(request: Request):
    """Dashboard sellers page"""
    return templates.TemplateResponse("sellers.html", {"request": request})


@app.get("/seller/{email}", response_class=HTMLResponse)
async def seller_detail_page(request: Request, email: str):
    """Seller detail page with matching positions"""
    return templates.TemplateResponse("seller_detail.html", {"request": request, "seller_email": email})


@app.get("/conversations", response_class=HTMLResponse)
async def conversations_page(request: Request):
    """Conversations page"""
    return templates.TemplateResponse("conversations.html", {"request": request})


# ================== AUTH ROUTES ==================

@app.get("/auth/google")
async def google_login(request: Request):
    """Начало OAuth flow с Google"""
    redirect_uri = f"{BASE_URL}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
async def google_callback(request: Request, repo: UserRepository = Depends(get_user_repo)):
    """Callback от Google OAuth"""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        return RedirectResponse(url=f"/auth/callback?error={str(e)}")

    user_info = token.get('userinfo')
    if not user_info:
        return RedirectResponse(url="/auth/callback?error=Failed to get user info")

    email = user_info.get('email')
    google_id = user_info.get('sub')
    name = user_info.get('name')
    picture = user_info.get('picture')

    # Проверяем существующего пользователя
    user = repo.find_by_email(email)

    is_new_user = False
    if not user:
        is_new_user = True
        is_admin = (email == ADMIN_EMAIL)

        user = repo.create_user(
            email=email,
            google_id=google_id,
            name=name,
            picture=picture,
            is_approved=is_admin  # Админ автоматически одобрен
        )

        if not user:
            return RedirectResponse(url="/auth/callback?error=Failed to create user")

        # Отправляем письмо админу
        if not is_admin:
            send_approval_request_email(email, name or email)
    else:
        repo.update_user(email, name=name, picture=picture)

    access_token = create_access_token({"email": email, "sub": google_id})

    redirect_url = f"/auth/callback?token={access_token}&is_new={is_new_user}&is_approved={user.is_approved}"
    return RedirectResponse(url=redirect_url)


@app.get("/auth/me")
async def get_me(user: UserModel = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    return user.to_dict()


# ================== ADMIN ROUTES ==================

@app.get("/admin/users")
async def list_users(
    admin: UserModel = Depends(get_admin_user),
    repo: UserRepository = Depends(get_user_repo)
):
    """Список всех пользователей"""
    users = repo.get_all_users()
    return [u.to_dict() for u in users]


@app.get("/admin/pending")
async def list_pending_users(
    admin: UserModel = Depends(get_admin_user),
    repo: UserRepository = Depends(get_user_repo)
):
    """Список пользователей, ожидающих одобрения"""
    users = repo.get_pending_users()
    return [u.to_dict() for u in users]


@app.post("/admin/approve/{email}")
async def approve_user(
    email: str,
    admin: UserModel = Depends(get_admin_user),
    repo: UserRepository = Depends(get_user_repo)
):
    """Одобрение пользователя"""
    user = repo.approve_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": f"User {email} approved", "user": user.to_dict()}


@app.post("/admin/reject/{email}")
async def reject_user(
    email: str,
    admin: UserModel = Depends(get_admin_user),
    repo: UserRepository = Depends(get_user_repo)
):
    """Отклонение пользователя"""
    user = repo.reject_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": f"User {email} rejected", "user": user.to_dict()}


# ================== PROTECTED ROUTES ==================

@app.get("/api/protected")
async def protected_route(user: UserModel = Depends(get_approved_user)):
    """Пример защищенного маршрута"""
    return {"message": f"Hello, {user.name}! You have access."}


@app.get("/api/products")
async def get_products(
    user: UserModel = Depends(get_approved_user),
    repo: ProductRepository = Depends(get_product_repo)
):
    """Получение всех продуктов"""
    products = repo.get_all()
    return [p.to_dict() for p in products]


@app.get("/api/seller/{email}/positions")
async def get_seller_positions(
    email: str,
    user: UserModel = Depends(get_approved_user),
):
    """Получение позиций продавца с результатами сравнения из catalog_matches"""
    from sqlalchemy import create_engine, text
    from urllib.parse import unquote
    import json

    email = unquote(email)
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Get all matched products for this seller from catalog_matches
        query = text("""
            SELECT
                cm.id,
                cm.catalog,
                cm.catalog_oes_numbers,
                cm.catalog_price_eur,
                cm.catalog_segments_names,
                cm.catalog_data,
                cm.matched_products
            FROM catalog_matches cm
            WHERE EXISTS (
                SELECT 1
                FROM jsonb_array_elements(cm.matched_products) AS mp
                JOIN products p ON p.part_id = (mp->>'part_id')
                WHERE p.seller_email = :email
            )
        """)
        result = conn.execute(query, {"email": email})
        rows = result.fetchall()

    positions = []
    for row in rows:
        catalog_data = row[5] or {}
        matched_products = row[6] or []

        # Filter matched products for this seller only
        for product in matched_products:
            product_data = product.get('product_data', {})
            if product_data.get('seller_email') == email:
                positions.append({
                    'id': f"{row[0]}_{product.get('part_id')}",  # Unique ID
                    'catalog': row[1],
                    'part_id': product.get('part_id'),
                    'code': product.get('code'),
                    'price': product.get('price'),
                    'url': product.get('url'),
                    'oem_code': product_data.get('item_description', {}).get('oem_code'),
                    'manufacturer_code': product_data.get('item_description', {}).get('manufacturer_code'),
                    'catalog_oes_numbers': row[2],
                    'catalog_price_eur': float(row[3]) if row[3] else None,
                    'catalog_segments': row[4],
                    'matched_by': product.get('matched_by'),
                    'matched_value': product.get('matched_value'),
                    'classification': product.get('price_classification'),
                    'images': product_data.get('images', []),
                    'catalog_data': catalog_data,
                })

    return positions


@app.get("/api/seller/{email}")
async def get_seller_info(
    email: str,
    user: UserModel = Depends(get_approved_user),
):
    """Получение информации о продавце"""
    from sqlalchemy import create_engine, text
    from urllib.parse import unquote

    email = unquote(email)
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        query = text("""
            SELECT email, name, phone, title, rating, address
            FROM sellers
            WHERE email = :email
        """)
        result = conn.execute(query, {"email": email})
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Seller not found")

    return {
        'email': row[0],
        'name': row[1],
        'phone': row[2],
        'title': row[3],
        'rating': row[4],
        'address': row[5],
    }


@app.get("/api/sellers-stats")
async def get_sellers_stats(
    user: UserModel = Depends(get_approved_user),
):
    """
    Получение статистики по продавцам:
    - OK matches: количество matched products от продавца с price_classification = 'OK'
    - HIGH matches: количество matched products от продавца с price_classification = 'HIGH'
    - Total matches: общее количество matched products от продавца
    """
    from sqlalchemy import create_engine, text

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Query: Count matched products for each seller by classification
        query = text("""
            SELECT
                s.email,
                s.name,
                s.phone,
                s.title,
                s.rating,
                COALESCE(stats.total_matches, 0) as total_matches,
                COALESCE(stats.ok_matches, 0) as ok_matches,
                COALESCE(stats.high_matches, 0) as high_matches,
                COALESCE(stats.total_products, 0) as total_products,
                COALESCE(stats.ok_products, 0) as ok_products,
                COALESCE(stats.high_products, 0) as high_products
            FROM sellers s
            LEFT JOIN LATERAL (
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(*) FILTER (WHERE mp->>'price_classification' = 'OK') as ok_matches,
                    COUNT(*) FILTER (WHERE mp->>'price_classification' = 'HIGH') as high_matches,
                    COUNT(DISTINCT p.part_id) as total_products,
                    COUNT(DISTINCT p.part_id) FILTER (
                        WHERE EXISTS (
                            SELECT 1
                            FROM catalog_matches cm2
                            CROSS JOIN jsonb_array_elements(cm2.matched_products) mp2
                            WHERE (mp2->>'part_id') = p.part_id
                            AND (mp2->>'price_classification') = 'OK'
                        )
                    ) as ok_products,
                    COUNT(DISTINCT p.part_id) FILTER (
                        WHERE EXISTS (
                            SELECT 1
                            FROM catalog_matches cm2
                            CROSS JOIN jsonb_array_elements(cm2.matched_products) mp2
                            WHERE (mp2->>'part_id') = p.part_id
                            AND (mp2->>'price_classification') = 'HIGH'
                        )
                    ) as high_products
                FROM catalog_matches cm
                CROSS JOIN jsonb_array_elements(cm.matched_products) mp
                JOIN products p ON p.part_id = (mp->>'part_id')
                WHERE p.seller_email = s.email
            ) stats ON true
            WHERE stats.total_matches > 0
            ORDER BY stats.ok_products DESC NULLS LAST
        """)
        result = conn.execute(query)
        rows = result.fetchall()

    sellers = []
    for row in rows:
        sellers.append({
            'email': row[0],
            'name': row[1],
            'phone': row[2],
            'title': row[3],
            'rating': row[4],
            'total_matches': row[5],
            'ok_matches': row[6],
            'high_matches': row[7],
            'total_products': row[8],
            'ok_products': row[9],
            'high_products': row[10],
        })

    return sellers


@app.get("/seller/sales")
async def get_seller_sales(
    email: str,
    user: UserModel = Depends(get_approved_user),
):
    """
    Получение продаж продавца из conversations с данными о продуктах
    """
    from sqlalchemy import create_engine, text
    from urllib.parse import unquote
    import json

    email = unquote(email)
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        query = text("""
            SELECT
                c.id,
                c.title,
                c.seller_email,
                c.position_ids,
                c.status,
                c.created_at,
                c.updated_at,
                COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN conversation_messages m ON m.conversation_id = c.id
            WHERE c.seller_email = :email
            GROUP BY c.id, c.title, c.seller_email, c.position_ids, c.status, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC
        """)
        result = conn.execute(query, {"email": email})
        rows = result.fetchall()

    sales = []
    for row in rows:
        position_ids = row[3] or []

        # Fetch product details for each position
        products = []
        if position_ids:
            with engine.connect() as conn:
                products_query = text("""
                    SELECT
                        p.part_id,
                        p.code,
                        p.price,
                        p.images,
                        c.catalog_data,
                        c.matched_by,
                        c.matched_value
                    FROM products p
                    LEFT JOIN compare c ON c.db_part_id = p.part_id
                    WHERE p.part_id = ANY(:position_ids)
                """)
                products_result = conn.execute(products_query, {"position_ids": position_ids})
                products_rows = products_result.fetchall()

                for prod_row in products_rows:
                    catalog_data = prod_row[4] or {}
                    products.append({
                        'part_id': prod_row[0],
                        'code': prod_row[1],
                        'price': float(prod_row[2]) if prod_row[2] else None,
                        'images': prod_row[3] or [],
                        'catalog_article': catalog_data.get('article') if catalog_data else None,
                        'matched_by': prod_row[5],
                        'matched_value': prod_row[6],
                    })

        sales.append({
            'id': row[0],
            'title': row[1],
            'seller_email': row[2],
            'position_ids': position_ids,
            'products': products,
            'status': row[4],
            'created_at': row[5].isoformat() if row[5] else None,
            'updated_at': row[6].isoformat() if row[6] else None,
            'message_count': row[7],
        })

    return sales


# ================== CONVERSATION ROUTES ==================

@app.post("/api/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    user: UserModel = Depends(get_approved_user),
    service: EmailService = Depends(get_email_service)
):
    """Создание новой переписки и отправка первого сообщения"""
    result = service.create_and_send_conversation(
        seller_email=request.seller_email,
        position_ids=request.position_ids,
        subject=request.subject,
        body=request.body,
        language=request.language,
        title=request.title
    )

    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error', 'Failed to create conversation'))

    return result


@app.get("/api/conversations")
async def list_conversations(
    seller_email: Optional[str] = None,
    user: UserModel = Depends(get_approved_user),
    repo: ConversationRepository = Depends(get_conv_repo)
):
    """Получение списка переписок с информацией о непрочитанных"""
    # Always use the method that includes unread status
    conversations = repo.get_conversations_with_last_message(seller_email)
    return conversations


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    user: UserModel = Depends(get_approved_user),
    repo: ConversationRepository = Depends(get_conv_repo)
):
    """Получение переписки со всеми сообщениями (автоматически помечает как прочитанные)"""
    result = repo.get_conversation_with_messages(conversation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    # Mark inbound messages as read when conversation is opened
    repo.mark_messages_as_read(conversation_id)
    return result


@app.post("/api/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    request: SendMessageRequest,
    user: UserModel = Depends(get_approved_user),
    service: EmailService = Depends(get_email_service)
):
    """Отправка сообщения в существующую переписку"""
    result = service.send_conversation_message(
        conversation_id=conversation_id,
        subject=request.subject,
        body=request.body
    )

    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error', 'Failed to send message'))

    return result


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    user: UserModel = Depends(get_approved_user),
    repo: ConversationRepository = Depends(get_conv_repo)
):
    """Удаление переписки"""
    success = repo.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted"}


@app.patch("/api/conversations/{conversation_id}/status")
async def update_conversation_status(
    conversation_id: int,
    status: str,
    user: UserModel = Depends(get_approved_user),
    repo: ConversationRepository = Depends(get_conv_repo)
):
    """Обновление статуса переписки"""
    if status not in ['active', 'closed', 'pending_reply']:
        raise HTTPException(status_code=400, detail="Invalid status")

    success = repo.update_conversation_status(conversation_id, status)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": f"Status updated to {status}"}


@app.post("/api/conversations/check-responses")
async def check_email_responses(
    mark_as_read: bool = False,
    user: UserModel = Depends(get_approved_user),
    service: EmailService = Depends(get_email_service)
):
    """Проверка почты на наличие ответов от продавцов"""
    responses = service.check_and_save_responses(mark_as_read=mark_as_read)
    return {
        "found": len(responses),
        "responses": responses
    }


# ================== CATALOG MATCHES ROUTES ==================

@app.get("/api/catalog-matches")
async def get_catalog_matches(
    catalog: Optional[str] = None,
    segment: Optional[str] = None,
    price_classification: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = 0,
    user: UserModel = Depends(get_approved_user),
):
    """
    Получение каталожных позиций с совпадениями продуктов

    Параметры:
    - catalog: Фильтр по каталогу ('eur', 'gur', 'eur,gur', или пусто для всех)
    - segment: Фильтр по сегменту (например, 'TOP')
    - price_classification: Фильтр по классификации цен ('OK' or 'HIGH')
    - limit: Количество записей (пагинация)
    - offset: Смещение (пагинация)
    """
    from sqlalchemy import create_engine, text

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Build WHERE conditions
        where_conditions = []
        params = {}

        if catalog:
            # Support multiple catalogs: 'eur,gur' or single 'eur'
            catalogs = [c.strip() for c in catalog.split(',')]
            if len(catalogs) == 1:
                where_conditions.append("catalog = :catalog")
                params['catalog'] = catalogs[0]
            else:
                placeholders = ', '.join([f':catalog{i}' for i in range(len(catalogs))])
                where_conditions.append(f"catalog IN ({placeholders})")
                for i, cat in enumerate(catalogs):
                    params[f'catalog{i}'] = cat

        if segment:
            # Map English segment names to Russian values used in database
            segment_mapping = {
                'TOP': 'ТОП',
                'SORTIMENT': 'Ассортимент',
                'NEW': 'Новый товар',
                'SORTIMENT_OUT': 'Выводим из ассортимента',
                'IN_DEVELOPMENT': 'В разработке',
                'UNDEFINED': 'Неопределен'
            }
            segment_value = segment_mapping.get(segment.upper(), segment)
            where_conditions.append("catalog_segments_names ILIKE :segment")
            params['segment'] = f"%{segment_value}%"

        if price_classification:
            if price_classification == 'OK':
                where_conditions.append("price_match_ok_count > 0")
            elif price_classification == 'HIGH':
                where_conditions.append("price_match_high_count > 0 AND price_match_ok_count = 0")

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # Count total
        count_query = text(f"""
            SELECT COUNT(*) as total
            FROM catalog_matches
            WHERE {where_clause}
        """)
        total_result = conn.execute(count_query, params)
        total_matches = total_result.fetchone()[0]

        # Build main query
        query = text(f"""
            SELECT
                id,
                catalog,
                catalog_oes_numbers,
                catalog_price_eur,
                catalog_price_usd,
                catalog_segments_names,
                matched_products_count,
                matched_products_ids,
                price_match_ok_count,
                price_match_high_count,
                avg_db_price,
                min_db_price,
                max_db_price,
                catalog_data,
                matched_products,
                created_at
            FROM catalog_matches
            WHERE {where_clause}
            ORDER BY price_match_ok_count DESC, matched_products_count DESC
            {f'LIMIT :limit' if limit else ''}
            {f'OFFSET :offset' if offset else ''}
        """)

        if limit:
            params['limit'] = limit
        if offset:
            params['offset'] = offset

        result = conn.execute(query, params)
        rows = result.fetchall()

    items = []
    for row in rows:
        items.append({
            'id': row[0],
            'catalog': row[1],
            'catalog_oes_numbers': row[2],
            'catalog_price_eur': float(row[3]) if row[3] else None,
            'catalog_price_usd': float(row[4]) if row[4] else None,
            'catalog_segments_names': row[5],
            'matched_products_count': row[6],
            'matched_products_ids': row[7] or [],
            'price_match_ok_count': row[8],
            'price_match_high_count': row[9],
            'avg_db_price': float(row[10]) if row[10] else None,
            'min_db_price': float(row[11]) if row[11] else None,
            'max_db_price': float(row[12]) if row[12] else None,
            'catalog_data': row[13] or {},
            'matched_products': row[14] or [],
            'created_at': row[15].isoformat() if row[15] else None,
        })

    return {
        'catalog': catalog,
        'total_matches': total_matches,
        'limit': limit,
        'offset': offset,
        'items': items
    }


@app.get("/api/catalog-matches/{match_id}")
async def get_catalog_match_detail(
    match_id: int,
    user: UserModel = Depends(get_approved_user),
):
    """Получение детальной информации о каталожной позиции с продуктами"""
    from sqlalchemy import create_engine, text

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        query = text("""
            SELECT
                id,
                catalog,
                catalog_oes_numbers,
                catalog_price_eur,
                catalog_price_usd,
                catalog_segments_names,
                matched_products_count,
                matched_products_ids,
                price_match_ok_count,
                price_match_high_count,
                avg_db_price,
                min_db_price,
                max_db_price,
                catalog_data,
                matched_products,
                created_at
            FROM catalog_matches
            WHERE id = :match_id
        """)
        result = conn.execute(query, {"match_id": match_id})
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Catalog match not found")

    return {
        'id': row[0],
        'catalog': row[1],
        'catalog_oes_numbers': row[2],
        'catalog_price_eur': float(row[3]) if row[3] else None,
        'catalog_price_usd': float(row[4]) if row[4] else None,
        'catalog_segments_names': row[5],
        'matched_products_count': row[6],
        'matched_products_ids': row[7] or [],
        'price_match_ok_count': row[8],
        'price_match_high_count': row[9],
        'avg_db_price': float(row[10]) if row[10] else None,
        'min_db_price': float(row[11]) if row[11] else None,
        'max_db_price': float(row[12]) if row[12] else None,
        'catalog_data': row[13] or {},
        'matched_products': row[14] or [],
        'created_at': row[15].isoformat() if row[15] else None,
    }


@app.get("/api/catalog-stats")
async def get_catalog_stats(
    user: UserModel = Depends(get_approved_user),
):
    """Получение статистики по каталогам"""
    from sqlalchemy import create_engine, text

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        query = text("""
            SELECT
                catalog,
                COUNT(*) as total_catalog_items,
                SUM(matched_products_count) as total_matched_products,
                SUM(price_match_ok_count) as total_ok_prices,
                SUM(price_match_high_count) as total_high_prices,
                AVG(avg_db_price) as overall_avg_price,
                COUNT(CASE WHEN price_match_ok_count > 0 THEN 1 END) as items_with_ok_prices,
                COUNT(CASE WHEN price_match_high_count > 0 AND price_match_ok_count = 0 THEN 1 END) as items_with_only_high_prices
            FROM catalog_matches
            GROUP BY catalog
        """)
        result = conn.execute(query)
        rows = result.fetchall()

    stats = []
    for row in rows:
        stats.append({
            'catalog': row[0],
            'total_catalog_items': row[1],
            'total_matched_products': row[2],
            'total_ok_prices': row[3],
            'total_high_prices': row[4],
            'overall_avg_price': float(row[5]) if row[5] else None,
            'items_with_ok_prices': row[6],
            'items_with_only_high_prices': row[7],
        })

    return stats

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

from sources.database.repository import UserRepository
from sources.database.models import UserModel


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


def get_user_repo() -> UserRepository:
    if not user_repo:
        raise HTTPException(status_code=500, detail="Database not configured")
    return user_repo


# ================== LIFESPAN ==================

@asynccontextmanager
async def lifespan(app: FastAPI):
    if user_repo:
        user_repo.create_tables()
    yield


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


# ================== AUTH ROUTES ==================

@app.get("/auth/google")
async def google_login(request: Request):
    """Начало OAuth flow с Google"""
    redirect_uri = request.url_for('google_callback')
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

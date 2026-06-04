"""
routes_auth.py — Authentification admin simple (mot de passe unique → JWT)

POST /api/auth/login            → { token }
GET  /api/auth/verify           → 200 si token valide, 401 sinon
POST /api/auth/change-password  → change le mot de passe (ancien requis)
POST /api/auth/forgot-password  → envoie un mail de réinitialisation
POST /api/auth/reset-password   → applique le nouveau mot de passe via token mail
"""

import hashlib
import logging
import os
import secrets
import smtplib
import time
from email.mime.text import MIMEText
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# True quand l'application tourne en production (sur le Raspberry).
# Met ENV=production (ou APP_ENV=production) dans le .env du serveur.
IS_PROD = os.getenv("ENV", os.getenv("APP_ENV", "")).lower() in (
    "prod",
    "production",
)

_ADMIN_PASSWORD_HASH = hashlib.sha256(
    os.getenv("ADMIN_PASSWORD", "campiglia").encode()
).hexdigest()

# A-5 — Secret JWT : interdit de garder le secret par défaut en production.
# En local (dev) on tolère le défaut pour ne pas bloquer le développement.
_DEFAULT_JWT_SECRET = "haccp-monitor-secret-key-change-in-prod-2026"
_JWT_SECRET = os.getenv("JWT_SECRET", _DEFAULT_JWT_SECRET)

if IS_PROD and _JWT_SECRET == _DEFAULT_JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET non configuré en production. "
        "Génère un secret aléatoire (ex: `python -c \"import secrets; "
        "print(secrets.token_urlsafe(48))\"`) et place-le dans le .env du serveur."
    )

_JWT_ALGO   = "HS256"
_JWT_EXPIRE = 8 * 3600  # 8 heures

# Nom du cookie de session (posé à la connexion, lu par le middleware).
COOKIE_NAME = "admin_token"

# SMTP
_SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
_SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
_SMTP_USER = os.getenv("SMTP_USER", "")
_SMTP_PASS = os.getenv("SMTP_PASSWORD", "")
_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "ucampiglia@gmail.com")
_APP_URL = os.getenv("APP_URL", "http://ulyssetest.ddns.net")

# Stockage en mémoire des tokens de reset (token → expiration timestamp)
# Simple et suffisant pour un seul admin — réinitialisé au redémarrage du service.
_reset_tokens: dict[str, float] = {}
_RESET_EXPIRE = 15 * 60  # 15 minutes

# A-2 — Limitation de débit du login (anti brute-force), en mémoire.
# Par IP : on garde les horodatages des tentatives sur une fenêtre glissante.
_LOGIN_MAX_TENTATIVES = 5            # tentatives autorisées…
_LOGIN_FENETRE_S = 60               # …par fenêtre de 60 s
_login_tentatives: dict[str, list[float]] = {}


def _verifier_rate_limit_login(ip: str):
    """Lève 429 si l'IP a dépassé le quota de tentatives sur la fenêtre."""
    maintenant = time.time()
    tentatives = [
        t for t in _login_tentatives.get(ip, []) if maintenant - t < _LOGIN_FENETRE_S
    ]
    if len(tentatives) >= _LOGIN_MAX_TENTATIVES:
        retry = int(_LOGIN_FENETRE_S - (maintenant - tentatives[0])) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives. Réessayez dans un instant.",
            headers={"Retry-After": str(max(1, retry))},
        )
    tentatives.append(maintenant)
    _login_tentatives[ip] = tentatives


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_token() -> str:
    payload = {
        "sub": "admin",
        "exp": int(time.time()) + _JWT_EXPIRE,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGO)


def _decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGO])
        if payload.get("sub") != "admin":
            raise ValueError
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )


_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")


def _set_password(new_password: str):
    """Met à jour le hash en mémoire ET écrit le nouveau mot de passe en clair dans .env."""
    global _ADMIN_PASSWORD_HASH
    _ADMIN_PASSWORD_HASH = hashlib.sha256(new_password.encode()).hexdigest()

    env_path = os.path.abspath(_ENV_PATH)
    try:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("ADMIN_PASSWORD="):
                    lines[i] = f"ADMIN_PASSWORD={new_password}\n"
                    updated = True
                    break
            if not updated:
                lines.append(f"ADMIN_PASSWORD={new_password}\n")
        else:
            lines = [f"ADMIN_PASSWORD={new_password}\n"]

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception:
        pass  # Si écriture impossible, le changement reste actif en mémoire uniquement


def _send_reset_email(reset_url: str):
    msg = MIMEText(
        f"Bonjour,\n\n"
        f"Une demande de réinitialisation du mot de passe HACCP Monitor a été effectuée.\n\n"
        f"Cliquez sur ce lien (valable 15 minutes) :\n{reset_url}\n\n"
        f"Si vous n'avez pas fait cette demande, ignorez ce message.\n\n"
        f"— HACCP Monitor · Au Comptoir des Lilas",
        "plain",
        "utf-8",
    )
    msg["Subject"] = "Réinitialisation mot de passe HACCP Monitor"
    msg["From"]    = _SMTP_USER
    msg["To"]      = _ADMIN_EMAIL

    with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as srv:
        srv.ehlo()
        srv.starttls()
        srv.login(_SMTP_USER, _SMTP_PASS)
        srv.sendmail(_SMTP_USER, [_ADMIN_EMAIL], msg.as_string())


# ---------------------------------------------------------------------------
# Extraction du token : en-tête Authorization OU cookie de session
# ---------------------------------------------------------------------------

def extraire_token(request: Request) -> Optional[str]:
    """Récupère le JWT brut depuis l'en-tête `Authorization: Bearer …`
    ou, à défaut, depuis le cookie de session. Retourne None si absent."""
    auth = request.headers.get("Authorization") or request.headers.get(
        "authorization"
    )
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie:
        return cookie.strip()
    return None


def token_valide(request: Request) -> bool:
    """True si la requête porte un JWT valide (header ou cookie). Ne lève rien."""
    token = extraire_token(request)
    if not token:
        return False
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGO])
        return payload.get("sub") == "admin"
    except JWTError:
        return False


# ---------------------------------------------------------------------------
# Dépendance réutilisable dans les autres routers
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)


def verify_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    """Dépendance FastAPI : accepte le token via header Bearer ou cookie."""
    token = credentials.credentials if credentials else request.cookies.get(
        COOKIE_NAME
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token manquant",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_token(token)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

class LoginBody(BaseModel):
    password: str


class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str


class ResetPasswordBody(BaseModel):
    token: str
    new_password: str


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response):
    # A-2 — anti brute-force : limite par IP appelante.
    ip = request.client.host if request.client else "inconnue"
    _verifier_rate_limit_login(ip)

    given_hash = hashlib.sha256(body.password.encode()).hexdigest()
    if given_hash != _ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mot de passe incorrect",
        )
    token = _make_token()
    # Cookie HttpOnly : envoyé automatiquement par le navigateur sur chaque
    # requête same-origin → toutes les pages existantes sont authentifiées
    # sans modifier leur code. HttpOnly = inaccessible au JavaScript (anti-XSS).
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=_JWT_EXPIRE,
        httponly=True,
        samesite="lax",
        secure=IS_PROD,  # HTTPS uniquement en prod (mettre l'appli en HTTPS idéalement)
        path="/",
    )
    return {"token": token, "expires_in": _JWT_EXPIRE}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/verify")
async def verify(payload: dict = Depends(verify_token)):
    return {"ok": True}


@router.post("/change-password")
async def change_password(body: ChangePasswordBody):
    old_hash = hashlib.sha256(body.old_password.encode()).hexdigest()
    if old_hash != _ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ancien mot de passe incorrect",
        )
    if len(body.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le nouveau mot de passe doit faire au moins 6 caractères",
        )
    _set_password(body.new_password)
    return {"ok": True, "message": "Mot de passe modifié. Pensez à mettre à jour votre fichier .env sur le serveur."}


@router.post("/forgot-password")
async def forgot_password():
    """Envoie un mail de réinitialisation à l'adresse admin."""
    if not _SMTP_USER or not _SMTP_PASS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Envoi de mail non configuré sur le serveur",
        )
    # Génère un token aléatoire sécurisé
    token = secrets.token_urlsafe(32)
    _reset_tokens[token] = time.time() + _RESET_EXPIRE

    reset_url = f"{_APP_URL}/static/reset.html?token={token}"
    try:
        _send_reset_email(reset_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erreur envoi mail : {e}",
        )
    return {"ok": True}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordBody):
    exp = _reset_tokens.get(body.token)
    if not exp or time.time() > exp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien invalide ou expiré",
        )
    if len(body.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le mot de passe doit faire au moins 6 caractères",
        )
    _set_password(body.new_password)
    del _reset_tokens[body.token]
    return {"ok": True}

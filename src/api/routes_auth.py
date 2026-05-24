"""
routes_auth.py — Authentification admin simple (mot de passe unique → JWT)

POST /api/auth/login            → { token }
GET  /api/auth/verify           → 200 si token valide, 401 sinon
POST /api/auth/change-password  → change le mot de passe (ancien requis)
POST /api/auth/forgot-password  → envoie un mail de réinitialisation
POST /api/auth/reset-password   → applique le nouveau mot de passe via token mail
"""

import hashlib
import os
import secrets
import smtplib
import time
from email.mime.text import MIMEText
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_ADMIN_PASSWORD_HASH = hashlib.sha256(
    os.getenv("ADMIN_PASSWORD", "campiglia").encode()
).hexdigest()

_JWT_SECRET = os.getenv(
    "JWT_SECRET",
    "haccp-monitor-secret-key-change-in-prod-2026",
)
_JWT_ALGO   = "HS256"
_JWT_EXPIRE = 8 * 3600  # 8 heures

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
# Dépendance réutilisable dans les autres routers
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token manquant",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_token(credentials.credentials)


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
async def login(body: LoginBody):
    given_hash = hashlib.sha256(body.password.encode()).hexdigest()
    if given_hash != _ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mot de passe incorrect",
        )
    return {"token": _make_token(), "expires_in": _JWT_EXPIRE}


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

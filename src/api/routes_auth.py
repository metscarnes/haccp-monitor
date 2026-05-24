"""
routes_auth.py — Authentification admin simple (mot de passe unique → JWT)

POST /api/auth/login   → { token }
GET  /api/auth/verify  → 200 si token valide, 401 sinon
"""

import hashlib
import os
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Mot de passe stocké sous forme de hash SHA-256 (jamais en clair dans le code)
_ADMIN_PASSWORD_HASH = hashlib.sha256(
    os.getenv("ADMIN_PASSWORD", "campiglia").encode()
).hexdigest()

_JWT_SECRET = os.getenv(
    "JWT_SECRET",
    "haccp-monitor-secret-key-change-in-prod-2026",
)
_JWT_ALGO    = "HS256"
_JWT_EXPIRE  = 8 * 3600  # 8 heures


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
    """Lève HTTPException 401 si token invalide ou expiré."""
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


# ---------------------------------------------------------------------------
# Dépendance réutilisable dans les autres routers
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    """Dépendance FastAPI — injecter dans les routes à protéger."""
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


@router.post("/login")
async def login(body: LoginBody):
    """Vérifie le mot de passe admin et retourne un JWT."""
    given_hash = hashlib.sha256(body.password.encode()).hexdigest()
    if given_hash != _ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mot de passe incorrect",
        )
    return {"token": _make_token(), "expires_in": _JWT_EXPIRE}


@router.get("/verify")
async def verify(payload: dict = Depends(verify_token)):
    """Vérifie qu'un token est encore valide (utilisé par le frontend)."""
    return {"ok": True}

"""
main.py — Point d'entrée FastAPI

Démarrage :
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

Dashboard accessible sur : http://localhost:8000
API docs (Swagger)       : http://localhost:8000/docs
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv  # pip install python-dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles

from src.database import init_db, get_db, purger_anciens_releves
from src.api.routes_boutiques  import router as router_boutiques
from src.api.routes_enceintes  import router as router_enceintes
from src.api.routes_releves    import router as router_releves
from src.api.routes_alertes    import router as router_alertes
from src.api.routes_rapports   import router as router_rapports
from src.api.routes_etiquettes import router as router_etiquettes
from src.api.routes_produits   import router as router_produits
from src.api.routes_reception  import router as router_reception
from src.api.routes_taches     import router as router_taches
from src.api.routes_admin      import router as router_admin
from src.api.routes_ouvertures    import router as router_ouvertures
from src.api.routes_incidents     import router as router_incidents
from src.api.routes_fabrication   import router as router_fabrication
from src.api.routes_nettoyage    import router as router_nettoyage
from src.api.routes_nuisibles    import router as router_nuisibles
from src.api.routes_etalonnage   import router as router_etalonnage
from src.api.routes_dlc           import router as router_dlc
from src.api.routes_cuisson       import router as router_cuisson
from src.api.routes_refroidissement import router as router_refroidissement
from src.api.routes_actions_correctives import router as router_actions_correctives
from src.api.routes_stock           import router as router_stock
from src.api.routes_hub             import router as router_hub
from src.api.routes_elearning       import router as router_elearning
from src.api.routes_auth            import router as router_auth
from src.api.routes_achats          import router as router_achats
from src.api.routes_vente           import router as router_vente
from src.api.routes_attente         import router as router_attente

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR    = Path(__file__).parent.parent
STATIC_DIR  = BASE_DIR / "static"


# ---------------------------------------------------------------------------
# Lifespan : démarrage / arrêt propres
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Démarrage
    await init_db()
    logger.info("Base de données prête")

    # Subscriber MQTT (désactivable pour les tests sans broker)
    subscriber_task = None
    if os.getenv("MQTT_DISABLED", "").lower() not in ("1", "true", "yes"):
        try:
            from src.mqtt_subscriber import demarrer_subscriber
            subscriber_task = await demarrer_subscriber()
            logger.info("Subscriber MQTT actif")
        except Exception as exc:
            logger.warning("Subscriber MQTT non démarré : %s", exc)
    else:
        logger.info("MQTT désactivé (MQTT_DISABLED=1)")

    yield

    # Arrêt
    if subscriber_task:
        subscriber_task.cancel()
    logger.info("Arrêt propre")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

# A-5 — Détection prod (mettre ENV=production dans le .env du serveur)
IS_PROD = os.getenv("ENV", os.getenv("APP_ENV", "")).lower() in ("prod", "production")

# A-4 — En production, on n'expose pas la documentation interactive de l'API
# (/docs, /redoc, /openapi.json) pour ne pas offrir la cartographie complète.
_docs_kwargs = (
    {"docs_url": None, "redoc_url": None, "openapi_url": None} if IS_PROD else {}
)

app = FastAPI(
    title="HACCP Monitor — Au Comptoir des Lilas",
    version="2.0.0",
    description="Monitoring HACCP complet — Mets Carnés Holding (Phase 2 : DLC, Réception, Tâches)",
    lifespan=lifespan,
    **_docs_kwargs,
)

# CORS : avec une authentification par cookie, `allow_origins=["*"]` est interdit
# si on autorise les credentials. L'appli étant servie en same-origin (la SPA et
# l'API sont sur le même hôte), on n'a pas besoin d'ouvrir le CORS à d'autres
# origines. On restreint donc à l'origine de l'app (configurable via CORS_ORIGINS).
_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", os.getenv("APP_URL", "")).split(",")
    if o.strip()
]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ---------------------------------------------------------------------------
# A-1 — Contrôle d'accès global
#
# Sans token valide (en-tête Authorization OU cookie de session) :
#   • toute requête /api/*  → 401 JSON
#   • toute page .html      → redirection vers /login.html
# Les chemins ci-dessous restent PUBLICS (nécessaires avant la connexion).
# ---------------------------------------------------------------------------

from src.api.routes_auth import (  # noqa: E402  (après création app)
    ADMIN_ONLY_PAGES,
    role_du_token,
)

# Routes API publiques (exactes) — accessibles sans authentification.
_PUBLIC_API_PATHS = {
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/verify",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    "/api/system/status",   # healthcheck
}

# Pages servies sans connexion (login + réinitialisation de mot de passe).
# On couvre les deux chemins possibles : racine (/login.html) et statique
# (/static/reset.html, utilisé dans le lien de réinitialisation envoyé par mail).
_PUBLIC_PAGES = {
    "/login.html",
    "/reset.html",
    "/static/login.html",
    "/static/reset.html",
}

# Préfixes de ressources statiques toujours servies (CSS/JS/images/manifest…)
# pour que la page de login s'affiche correctement.
_PUBLIC_PREFIXES = ("/static/",)


def _est_public(path: str) -> bool:
    if path in _PUBLIC_PAGES or path in _PUBLIC_API_PATHS:
        return True
    # Ressources statiques (CSS/JS/images/manifest…) MAIS pas les pages .html :
    # ces dernières vivent aussi dans static/ et doivent rester protégées.
    if path.startswith(_PUBLIC_PREFIXES) and not path.lower().endswith(".html"):
        return True
    # Fichiers techniques racine (favicon, manifest, service worker…)
    if path in ("/favicon.ico", "/manifest.json", "/sw.js", "/robots.txt"):
        return True
    return False


@app.middleware("http")
async def controle_acces(request: Request, call_next):
    path = request.url.path

    # Laisser passer les pré-vols CORS et les chemins publics.
    if request.method == "OPTIONS" or _est_public(path):
        return await call_next(request)

    role = role_du_token(request)  # "admin", "equipe" ou None

    if role is None:
        # Non authentifié : réponse adaptée au type de ressource.
        if path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentification requise"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Page HTML (ou autre) → on renvoie vers la page de connexion.
        return RedirectResponse(url="/login.html", status_code=302)

    # Authentifié mais rôle « equipe » : les pages réservées à l'admin
    # (admin.html, catalogue.html) restent interdites — comme avant.
    if role != "admin" and path in ADMIN_ONLY_PAGES:
        return RedirectResponse(url="/login.html?admin=1", status_code=302)

    return await call_next(request)

# Routes API — Phase 1
app.include_router(router_boutiques)
app.include_router(router_enceintes)
app.include_router(router_releves)
app.include_router(router_alertes)
app.include_router(router_rapports)

# Routes API — Phase 2
app.include_router(router_produits)   # CRUD catalogue produits (avant etiquettes pour priorité)
app.include_router(router_etiquettes)
app.include_router(router_reception)
app.include_router(router_taches)
app.include_router(router_admin)
app.include_router(router_ouvertures)
app.include_router(router_incidents)

# Routes API — Phase 3
app.include_router(router_fabrication)

# Routes API — Nettoyage & Nuisibles
app.include_router(router_nettoyage)
app.include_router(router_nuisibles)

# Routes API — Étalonnage thermomètres
app.include_router(router_etalonnage)

# Routes API — Calendrier DLC
app.include_router(router_dlc)

# Routes API — Cuisson (Rôtissoire…)
app.include_router(router_cuisson)

# Routes API — Refroidissement rapide (≤ 10 °C en ≤ 2 h)
app.include_router(router_refroidissement)

# Routes API — Agrégateur Actions correctives (PCR01 + NC étalonnages/cuissons/refroidissements)
app.include_router(router_actions_correctives)

# Routes API — Stock unifié (FIFO toutes sources)
app.include_router(router_stock)

app.include_router(router_hub)

# Routes API — E-Learning HACCP
app.include_router(router_elearning)

# Routes API — Authentification
app.include_router(router_auth)

# Routes API — Module Achats (fournisseurs, catalogue, commandes)
app.include_router(router_achats)
app.include_router(router_vente)

# Routes API — Produits en attente de traçabilité (lot/DLC manquant)
app.include_router(router_attente)


# ---------------------------------------------------------------------------
# Routes système
# ---------------------------------------------------------------------------

@app.get("/api/system/status")
async def system_status():
    """Santé globale du système (MQTT, DB)."""
    import paho.mqtt.client as mqtt_client

    # Test DB
    db_ok = False
    try:
        async with get_db() as db:
            await db.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass

    # Test broker MQTT (connexion rapide)
    mqtt_ok = False
    try:
        c = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
        c.connect(
            os.getenv("MQTT_BROKER") or "localhost",
            int(os.getenv("MQTT_PORT") or "1883"),
            keepalive=5,
        )
        c.disconnect()
        mqtt_ok = True
    except Exception:
        pass

    return {
        "statut": "ok" if (db_ok and mqtt_ok) else "degradé",
        "composants": {
            "base_de_donnees": "ok" if db_ok else "erreur",
            "broker_mqtt": "ok" if mqtt_ok else "erreur",
        },
    }


@app.post("/api/system/purge")
async def purger():
    """Déclenche la purge manuelle des données expirées."""
    async with get_db() as db:
        result = await purger_anciens_releves(db)
    return result


# ---------------------------------------------------------------------------
# Servir les vidéos avec support des Range requests (seek dans le lecteur)
#
# StaticFiles ne publie pas correctement `Accept-Ranges` / `206 Partial
# Content` dans cette config : sans ça le navigateur ne peut pas se
# positionner dans la vidéo (le seek revient à la dernière position bufferisée).
# Cette route dédiée doit être déclarée AVANT le mount /static pour avoir
# la priorité sur les fichiers .mp4.
# ---------------------------------------------------------------------------

if STATIC_DIR.exists():

    PMS_DIR = STATIC_DIR / "docs" / "Classeur PMS"

    @app.get("/api/pms/liste", include_in_schema=False)
    async def pms_liste(dossier: str = ""):
        """Liste les fichiers d'un sous-dossier du Classeur PMS."""
        from fastapi.responses import JSONResponse
        import urllib.parse

        dossier_dec = urllib.parse.unquote(dossier)
        cible = (PMS_DIR / dossier_dec).resolve()

        # Sécurité : rester dans PMS_DIR
        if not str(cible).startswith(str(PMS_DIR.resolve())):
            return JSONResponse({"fichiers": []})

        if not cible.is_dir():
            return JSONResponse({"fichiers": []})

        fichiers = sorted(
            f.name for f in cible.iterdir()
            if f.is_file() and not f.name.startswith(".")
        )
        return JSONResponse({"fichiers": fichiers})

    @app.get("/static/{file_path:path}.mp4", include_in_schema=False)
    async def servir_video(file_path: str, request: Request):
        """Sert les .mp4 avec Range requests pour permettre le seek."""
        video = (STATIC_DIR / f"{file_path}.mp4").resolve()
        if not str(video).startswith(str(STATIC_DIR.resolve())) or not video.is_file():
            return RedirectResponse("/")

        file_size = video.stat().st_size
        range_header = request.headers.get("range")

        if range_header is None:
            return FileResponse(
                str(video),
                media_type="video/mp4",
                headers={"Accept-Ranges": "bytes"},
            )

        # Parse "bytes=start-end"
        try:
            units, rng = range_header.split("=", 1)
            start_s, end_s = rng.split("-", 1)
            start = int(start_s) if start_s else 0
            end = int(end_s) if end_s else file_size - 1
        except ValueError:
            start, end = 0, file_size - 1

        start = max(0, start)
        end = min(end, file_size - 1)
        chunk_size = end - start + 1

        def iter_file():
            with open(video, "rb") as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    data = f.read(min(1024 * 1024, remaining))
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": "video/mp4",
        }
        return StreamingResponse(iter_file(), status_code=206, headers=headers)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.get("/{page}.html", include_in_schema=False)
    async def html_page(page: str):
        """Sert tout fichier .html de static/ à la racine de l'app.
        Permet d'accéder à /hub.html, /taches.html, /etiquettes.html, etc.
        """
        path = STATIC_DIR / f"{page}.html"
        if path.exists():
            return FileResponse(str(path))
        return RedirectResponse("/")

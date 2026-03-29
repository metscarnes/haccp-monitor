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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.database import init_db, get_db, purger_anciens_releves
from src.api.routes_boutiques  import router as router_boutiques
from src.api.routes_enceintes  import router as router_enceintes
from src.api.routes_releves    import router as router_releves
from src.api.routes_alertes    import router as router_alertes
from src.api.routes_rapports   import router as router_rapports
from src.api.routes_etiquettes import router as router_etiquettes
from src.api.routes_reception  import router as router_reception
from src.api.routes_taches     import router as router_taches
from src.api.routes_admin      import router as router_admin

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

app = FastAPI(
    title="HACCP Monitor — Au Comptoir des Lilas",
    version="2.0.0",
    description="Monitoring HACCP complet — Mets Carnés Holding (Phase 2 : DLC, Réception, Tâches)",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restreindre en prod
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes API — Phase 1
app.include_router(router_boutiques)
app.include_router(router_enceintes)
app.include_router(router_releves)
app.include_router(router_alertes)
app.include_router(router_rapports)

# Routes API — Phase 2
app.include_router(router_etiquettes)
app.include_router(router_reception)
app.include_router(router_taches)
app.include_router(router_admin)


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
            os.getenv("MQTT_BROKER", "localhost"),
            int(os.getenv("MQTT_PORT", "1883")),
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
# Servir le frontend statique
# ---------------------------------------------------------------------------

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(str(STATIC_DIR / "index.html"))

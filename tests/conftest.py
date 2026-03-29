"""
conftest.py — Fixtures partagées pour tous les tests

Utilise une base SQLite en mémoire (:memory:) pour l'isolation totale.
L'application FastAPI est instanciée avec MQTT_DISABLED=1.
"""

import os
import pytest
import pytest_asyncio
from pathlib import Path

# Désactiver MQTT avant tout import de l'app
os.environ["MQTT_DISABLED"] = "1"

# Pointer la DB vers un fichier temporaire (évite de polluer la base réelle)
import tempfile
_tmp = tempfile.mktemp(suffix=".db")
os.environ["HACCP_DB_PATH"] = _tmp


# ---------------------------------------------------------------------------
# Patch DB_PATH avant import de database
# ---------------------------------------------------------------------------

import src.database as _db_module
_db_module.DB_PATH = Path(_tmp)


# ---------------------------------------------------------------------------
# Client HTTP de test (ASGI, sans réseau)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def app_client():
    """Client httpx branché directement sur l'app ASGI — pas de réseau."""
    from httpx import AsyncClient, ASGITransport
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# ---------------------------------------------------------------------------
# Base de données isolée (fixture function-scope)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db():
    """Connexion aiosqlite isolée : schéma + seed frais à chaque test."""
    from src.database import init_db, get_db, SEED_SQL, SEED_SQL_PHASE2
    await init_db()
    async with get_db() as conn:
        # Vider toutes les tables pour isolation totale entre tests
        phase2_tables = (
            "tache_validations", "tache_types",
            "plan_nettoyage", "pieges", "personnel",
            "non_conformites_fournisseur", "reception_lignes", "receptions", "fournisseurs",
            "etiquettes_generees", "regles_dlc", "produits",
        )
        phase1_tables = ("releves", "alertes", "rapports", "destinataires", "enceintes", "boutiques")
        for table in phase2_tables + phase1_tables:
            await conn.execute(f"DELETE FROM {table}")
        await conn.executescript(SEED_SQL)
        await conn.executescript(SEED_SQL_PHASE2)
        await conn.commit()
        yield conn

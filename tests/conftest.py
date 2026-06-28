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


# Mot de passe admin connu pour les tests (l'app hashe cette valeur au démarrage).
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")


@pytest_asyncio.fixture(scope="session")
async def app_client():
    """Client httpx branché directement sur l'app ASGI — pas de réseau.

    Depuis le durcissement de sécurité (A-1), toutes les routes /api/* exigent
    une authentification. On se connecte une fois ici : le cookie de session
    posé par /api/auth/login est ensuite réémis automatiquement par le client
    httpx sur chaque requête, donc tous les tests héritent d'une session valide.
    """
    from httpx import AsyncClient, ASGITransport
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/login",
            json={"password": os.environ["ADMIN_PASSWORD"]},
        )
        assert resp.status_code == 200, f"login test échoué: {resp.status_code} {resp.text}"
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
            # Enfants en premier (respecter les FK)
            # Inventaire valorisé (FK vers inventaires, catalogue_fournisseur)
            "inventaire_lignes",                   # → inventaires, catalogue_fournisseur
            "inventaires",                         # → boutiques, personnel
            "ca_journalier",                       # → boutiques, personnel (pilotage CA)
            # Module Achat — Factures & Commandes (FK vers receptions/reception_lignes/fournisseurs)
            "historique_prix_achat",               # → catalogue_fournisseur, receptions, reception_lignes
            "facture_lignes",                      # → factures, reception_lignes, catalogue_fournisseur
            "factures",                            # → fournisseurs, receptions, commandes, personnel
            "commande_receptions_mapping",         # → commandes, receptions, personnel
            "commande_lignes",                     # → commandes, catalogue_fournisseur
            "commandes",                           # → fournisseurs, personnel
            "panier_lignes",                       # → fournisseurs, catalogue_fournisseur
            "catalogue_fournisseur",               # → fournisseurs
            # Phase 3 — Fabrication
            "fabrication_lots",                    # → fabrications, recette_ingredients, reception_lignes
            "fabrications",                        # → recettes, personnel
            "recette_ingredients",                 # → recettes, produits
            "recettes",                            # → produits
            # Modules thermiques HACCP
            "refroidissements",                    # → cuissons, produits, personnel
            "cuissons",                            # → produits, personnel, reception_lignes
            # Modules hygiène / IPM
            "registre_nettoyage",                  # → taches_nettoyage
            "taches_nettoyage",
            "nuisibles_controles",
            # Étalonnage thermomètres
            "etalonnage_comparaisons",             # → etalonnages, enceintes
            "etalonnages",                         # → thermometres_ref
            "thermometres_ref",                    # → boutiques
            # Paramètres key/value
            "parametres",                          # → boutiques
            "lot_interne_counters",
            # Calendrier DLC
            "dlc_devenir",                         # → personnel
            # Phase 2
            "fiches_incident",                     # → receptions, reception_lignes, fournisseurs, produits, personnel
            "ouvertures",                          # → produits, personnel, reception_lignes
            "tache_validations",                   # → tache_types
            "tache_types",
            "pieges",
            "non_conformites_fournisseur",         # → receptions, reception_lignes
            "reception_lignes",                    # → receptions, produits, fournisseurs
            "receptions",                          # → personnel, fournisseurs (AVANT personnel)
            "personnel",
            "fournisseurs",
            "etiquettes_generees",                 # → produits
            "regles_dlc",
            "produits",
        )
        phase1_tables = ("releves", "alertes", "rapports", "destinataires", "enceintes", "boutiques")
        # FK désactivées le temps du nettoyage : on vide en masse sans avoir à trier
        # parfaitement l'ordre parent/enfant (le tri ci-dessus reste une intention,
        # mais certaines tables du module Achat se croisent — OFF évite les faux conflits).
        await conn.execute("PRAGMA foreign_keys = OFF")
        for table in phase2_tables + phase1_tables:
            await conn.execute(f"DELETE FROM {table}")
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.executescript(SEED_SQL)
        await conn.executescript(SEED_SQL_PHASE2)
        await conn.commit()
        yield conn

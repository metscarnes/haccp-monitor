"""
test_etiquettes.py — Tests Module DLC / Étiquettes

Couvre :
- CRUD produits
- Règles DLC
- Calcul DLC (toutes catégories + cas décongélation)
- Génération numéro de lot
- Création étiquette (sans impression réelle)
- Alertes DLC proches
- Endpoints API /api/produits, /api/regles-dlc, /api/etiquettes/*
"""

import pytest
import pytest_asyncio
from datetime import date, timedelta


# ---------------------------------------------------------------------------
# Tests unitaires — base de données
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_creer_produit(db):
    from src.database import create_produit, get_produit
    pid = await create_produit(db, {
        "boutique_id": 1,
        "nom": "Bœuf haché test",
        "categorie": "viande_hachee",
        "dlc_jours": 1,
        "temperature_conservation": "0°C à +4°C",
    })
    assert pid > 0
    produit = await get_produit(db, pid)
    assert produit["nom"] == "Bœuf haché test"
    assert produit["categorie"] == "viande_hachee"
    assert produit["dlc_jours"] == 1
    assert produit["actif"] == 1


@pytest.mark.anyio
async def test_lister_produits(db):
    from src.database import create_produit, get_produits
    await create_produit(db, {
        "boutique_id": 1,
        "nom": "Entrecôte",
        "categorie": "viande_pieces",
        "dlc_jours": 3,
        "temperature_conservation": "0°C à +3°C",
    })
    produits = await get_produits(db, 1)
    assert any(p["nom"] == "Entrecôte" for p in produits)


@pytest.mark.anyio
async def test_desactiver_produit(db):
    from src.database import create_produit, update_produit, get_produits
    pid = await create_produit(db, {
        "boutique_id": 1,
        "nom": "Produit temporaire",
        "categorie": "plat_cuisine",
        "dlc_jours": 3,
        "temperature_conservation": "0°C à +4°C",
    })
    await update_produit(db, pid, {"actif": False})
    produits = await get_produits(db, 1)
    assert not any(p["id"] == pid for p in produits)


@pytest.mark.anyio
async def test_regles_dlc_seed(db):
    """Les règles DLC par défaut sont bien insérées au démarrage."""
    from src.database import get_regles_dlc
    regles = await get_regles_dlc(db, 1)
    categories = {r["categorie"] for r in regles}
    assert "viande_hachee" in categories
    assert "charcuterie_tranchee" in categories
    assert "produit_deconge" in categories


@pytest.mark.anyio
async def test_modifier_regle_dlc(db):
    from src.database import update_regle_dlc, get_regles_dlc
    await update_regle_dlc(db, 1, "viande_hachee", 2, "Règle modifiée test")
    regles = await get_regles_dlc(db, 1)
    regle = next(r for r in regles if r["categorie"] == "viande_hachee")
    assert regle["dlc_jours"] == 2


# ---------------------------------------------------------------------------
# Tests unitaires — calcul DLC (fonction pure)
# ---------------------------------------------------------------------------

def test_calcul_dlc_viande_hachee():
    from src.database import calculer_dlc
    d = date(2026, 3, 29)
    dlc = calculer_dlc("viande_hachee", d, 1)
    assert dlc == date(2026, 3, 30)


def test_calcul_dlc_decongélation_j3():
    """La DLC décongélation est toujours J+3, non modifiable."""
    from src.database import calculer_dlc
    d = date(2026, 3, 29)
    dlc = calculer_dlc("produit_deconge", d, 3)
    assert dlc == date(2026, 4, 1)


def test_calcul_dlc_charcuterie():
    from src.database import calculer_dlc
    d = date(2026, 3, 29)
    dlc = calculer_dlc("charcuterie_tranchee", d, 5)
    assert dlc == date(2026, 4, 3)


# ---------------------------------------------------------------------------
# Tests unitaires — numérotation lots
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_numero_lot_premier_du_jour(db):
    from src.database import get_next_numero_lot
    jour = date(2026, 3, 29)
    numero = await get_next_numero_lot(db, 1, jour)
    assert numero == "MC-20260329-0001"


@pytest.mark.anyio
async def test_numero_lot_increment(db):
    from src.database import get_next_numero_lot, create_etiquette
    jour = date(2026, 3, 29)
    # Insérer une étiquette pour simuler un lot existant
    await create_etiquette(db, {
        "boutique_id": 1,
        "produit_nom": "Test",
        "type_date": "fabrication",
        "date_etiquette": "2026-03-29",
        "dlc": "2026-03-30",
        "operateur": "Éric",
        "numero_lot": "MC-20260329-0001",
        "lot_type": "interne",
    })
    numero = await get_next_numero_lot(db, 1, jour)
    assert numero == "MC-20260329-0002"


# ---------------------------------------------------------------------------
# Tests unitaires — alertes DLC
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_alertes_dlc_proche(db):
    from src.database import create_etiquette, get_alertes_dlc
    aujourd_hui = date.today()
    dlc_demain = (aujourd_hui + timedelta(days=1)).isoformat()

    await create_etiquette(db, {
        "boutique_id": 1,
        "produit_nom": "Bœuf haché",
        "type_date": "fabrication",
        "date_etiquette": aujourd_hui.isoformat(),
        "dlc": dlc_demain,
        "operateur": "Éric",
        "numero_lot": "MC-TEST-0001",
        "lot_type": "interne",
    })
    alertes = await get_alertes_dlc(db, 1, jours_seuil=2)
    assert len(alertes) >= 1
    assert any(a["produit_nom"] == "Bœuf haché" for a in alertes)


@pytest.mark.anyio
async def test_alertes_dlc_loin_pas_retournee(db):
    from src.database import create_etiquette, get_alertes_dlc
    aujourd_hui = date.today()
    dlc_loin = (aujourd_hui + timedelta(days=10)).isoformat()

    await create_etiquette(db, {
        "boutique_id": 1,
        "produit_nom": "Produit longue durée",
        "type_date": "fabrication",
        "date_etiquette": aujourd_hui.isoformat(),
        "dlc": dlc_loin,
        "operateur": "Éric",
        "numero_lot": "MC-TEST-0099",
        "lot_type": "interne",
    })
    alertes = await get_alertes_dlc(db, 1, jours_seuil=2)
    assert not any(a["produit_nom"] == "Produit longue durée" for a in alertes)


# ---------------------------------------------------------------------------
# Tests API
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_lister_produits(app_client):
    r = await app_client.get("/api/produits")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_api_creer_produit(app_client):
    r = await app_client.post("/api/produits", json={
        "nom": "Jambon cuit API",
        "categorie": "charcuterie_tranchee",
        "dlc_jours": 5,
        "temperature_conservation": "0°C à +4°C",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["nom"] == "Jambon cuit API"
    assert data["dlc_jours"] == 5


@pytest.mark.anyio
async def test_api_regles_dlc(app_client):
    r = await app_client.get("/api/regles-dlc")
    assert r.status_code == 200
    regles = r.json()
    assert len(regles) >= 7


@pytest.mark.anyio
async def test_api_modifier_regle_dlc(app_client):
    r = await app_client.put("/api/regles-dlc/plat_cuisine", json={"dlc_jours": 4})
    assert r.status_code == 200
    assert r.json()["dlc_jours"] == 4


@pytest.mark.anyio
async def test_api_historique_etiquettes(app_client):
    r = await app_client.get("/api/etiquettes")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_api_alertes_dlc(app_client):
    r = await app_client.get("/api/etiquettes/alertes-dlc")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_api_generer_etiquette_sans_produit_id(app_client):
    """Génération d'une étiquette en saisie manuelle (sans produit_id)."""
    from datetime import date
    today = date.today().isoformat()
    r = await app_client.post("/api/etiquettes/generer", json={
        "produit_nom": "Saisie manuelle test",
        "type_date": "fabrication",
        "date_etiquette": today,
        "operateur": "Éric",
        "lot_type": "interne",
        "dlc_jours": 2,
        "temperature_conservation": "0°C à +4°C",
    })
    assert r.status_code == 201
    data = r.json()
    assert "numero_lot" in data
    assert data["numero_lot"].startswith("MC-")
    assert "dlc" in data


@pytest.mark.anyio
async def test_api_generer_etiquette_decongélation(app_client):
    """La DLC décongélation doit être J+3 quelle que soit la règle produit."""
    from datetime import date
    today_str = date.today().isoformat()
    dlc_attendue = (date.today() + timedelta(days=3)).isoformat()

    r = await app_client.post("/api/etiquettes/generer", json={
        "produit_nom": "Entrecôte décongelée",
        "type_date": "decongélation",
        "date_etiquette": today_str,
        "operateur": "Éric",
        "lot_type": "interne",
        "dlc_jours": 3,
        "temperature_conservation": "0°C à +3°C",
    })
    assert r.status_code == 201
    assert r.json()["dlc"] == dlc_attendue


@pytest.mark.anyio
async def test_api_statut_imprimante(app_client):
    r = await app_client.get("/api/impression/status")
    assert r.status_code == 200
    data = r.json()
    assert "disponible" in data
    assert "message" in data

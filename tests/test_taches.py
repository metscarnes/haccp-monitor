"""
test_taches.py — Tests Module Tâches HACCP

Couvre :
- Seed des 12 types de tâches par défaut
- CRUD types de tâches
- Création de validations (avec données JSON spécifiques)
- Vue "Aujourd'hui" (statuts en_retard / a_faire / fait)
- Personnel et admin
- Endpoints API
"""

import pytest
import pytest_asyncio
from datetime import date, datetime


# ---------------------------------------------------------------------------
# Tests unitaires — types de tâches
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_tache_types_seed(db):
    """Les 12 types de tâches HACCP sont insérés par défaut."""
    from src.database import get_tache_types
    types = await get_tache_types(db, 1)
    codes = {t["code"] for t in types}
    # Vérifier quelques fiches clés
    assert "releve_temp_enceintes_matin" in codes
    assert "releve_temp_enceintes_soir" in codes
    assert "nettoyage_desinfection" in codes
    assert "suivi_decongélation" in codes
    assert "tiac" in codes
    # Au moins 12 types
    assert len(types) >= 12


@pytest.mark.anyio
async def test_creer_tache_type(db):
    from src.database import create_tache_type, get_tache_type
    tid = await create_tache_type(db, {
        "boutique_id": 1,
        "code": "test_custom",
        "libelle": "Tâche personnalisée",
        "frequence": "quotidien",
        "heure_cible": "09:00",
        "photo_requise": True,
    })
    assert tid > 0
    t = await get_tache_type(db, tid)
    assert t["libelle"] == "Tâche personnalisée"
    assert t["photo_requise"] == 1


@pytest.mark.anyio
async def test_modifier_tache_type(db):
    from src.database import create_tache_type, update_tache_type, get_tache_type
    tid = await create_tache_type(db, {
        "boutique_id": 1,
        "code": "test_modif",
        "libelle": "Avant modif",
        "frequence": "quotidien",
    })
    await update_tache_type(db, tid, {"libelle": "Après modif", "heure_cible": "10:00"})
    t = await get_tache_type(db, tid)
    assert t["libelle"] == "Après modif"
    assert t["heure_cible"] == "10:00"


# ---------------------------------------------------------------------------
# Tests unitaires — validations
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_creer_validation_simple(db):
    from src.database import get_tache_types, create_validation, get_validations
    from datetime import timezone, timedelta

    types = await get_tache_types(db, 1)
    tache = next(t for t in types if t["code"] == "nettoyage_desinfection")

    vid = await create_validation(db, {
        "boutique_id": 1,
        "tache_type_id": tache["id"],
        "operateur": "Éric",
        "date_tache": date.today().isoformat(),
        "conforme": True,
        "commentaire": "RAS",
        "donnees_specifiques": {
            "local": "Laboratoire",
            "surface": "Plan de travail inox",
            "frequence": "quotidien",
        },
    })
    assert vid > 0

    depuis = datetime.now(timezone.utc) - timedelta(days=1)
    validations = await get_validations(db, 1, depuis=depuis, tache_type_id=tache["id"])
    assert len(validations) >= 1
    v = validations[0]
    assert v["operateur"] == "Éric"
    assert isinstance(v["donnees_specifiques"], dict)
    assert v["donnees_specifiques"]["local"] == "Laboratoire"


@pytest.mark.anyio
async def test_validation_fiche2_temperatures(db):
    """Fiche 2 — relevé températures avec données JSON spécifiques."""
    from src.database import get_tache_types, create_validation, get_validations
    from datetime import timezone, timedelta

    types = await get_tache_types(db, 1)
    tache = next(t for t in types if t["code"] == "releve_temp_enceintes_matin")

    await create_validation(db, {
        "boutique_id": 1,
        "tache_type_id": tache["id"],
        "operateur": "Ulysse",
        "date_tache": date.today().isoformat(),
        "conforme": True,
        "donnees_specifiques": {
            "enceinte_id": 1,
            "moment": "matin",
            "temperature": 2.8,
        },
    })
    depuis = datetime.now(timezone.utc) - timedelta(days=1)
    validations = await get_validations(db, 1, depuis=depuis, tache_type_id=tache["id"])
    v = validations[0]
    assert v["donnees_specifiques"]["temperature"] == 2.8
    assert v["donnees_specifiques"]["moment"] == "matin"


@pytest.mark.anyio
async def test_validation_fiche11_decongélation(db):
    """Fiche 11 — décongélation : DLC J+3 stockée dans les données."""
    from src.database import get_tache_types, create_validation, get_validations
    from datetime import timezone, timedelta

    types = await get_tache_types(db, 1)
    tache = next(t for t in types if t["code"] == "suivi_decongélation")

    aujourd_hui = date.today()
    dlc_j3 = (aujourd_hui + timedelta(days=3)).isoformat()

    await create_validation(db, {
        "boutique_id": 1,
        "tache_type_id": tache["id"],
        "operateur": "Éric",
        "date_tache": aujourd_hui.isoformat(),
        "conforme": True,
        "donnees_specifiques": {
            "produit": "Entrecôte",
            "date_mise_en_decongélation": datetime.now().isoformat(),
            "dlc_calculee": dlc_j3,
            "type_conservation": "CF positive 0°C à +3°C",
        },
    })
    depuis = datetime.now(timezone.utc) - timedelta(days=1)
    validations = await get_validations(db, 1, depuis=depuis, tache_type_id=tache["id"])
    v = validations[0]
    assert v["donnees_specifiques"]["dlc_calculee"] == dlc_j3


# ---------------------------------------------------------------------------
# Tests unitaires — vue Aujourd'hui
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_taches_today_structure(db):
    from src.database import get_taches_today
    result = await get_taches_today(db, 1)
    assert "date" in result
    assert "en_retard" in result
    assert "a_faire" in result
    assert "fait" in result
    assert isinstance(result["a_faire"], list)


@pytest.mark.anyio
async def test_taches_today_apres_validation(db):
    """Une tâche validée apparaît dans 'fait'."""
    from src.database import get_tache_types, create_validation, get_taches_today
    types = await get_tache_types(db, 1)
    # Prendre une tâche quotidienne
    tache = next(t for t in types if t["code"] == "nettoyage_desinfection")

    await create_validation(db, {
        "boutique_id": 1,
        "tache_type_id": tache["id"],
        "operateur": "Éric",
        "date_tache": date.today().isoformat(),
        "conforme": True,
    })
    result = await get_taches_today(db, 1)
    faits_ids = {t["id"] for t in result["fait"]}
    assert tache["id"] in faits_ids


# ---------------------------------------------------------------------------
# Tests unitaires — personnel
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_personnel_seed(db):
    """Éric et Ulysse sont dans le seed par défaut."""
    from src.database import get_personnel
    personnel = await get_personnel(db, 1)
    prenoms = {p["prenom"] for p in personnel}
    assert "Éric" in prenoms
    assert "Ulysse" in prenoms


@pytest.mark.anyio
async def test_ajouter_personnel(db):
    from src.database import create_personnel, get_personnel
    await create_personnel(db, {"boutique_id": 1, "prenom": "Marie"})
    personnel = await get_personnel(db, 1)
    assert any(p["prenom"] == "Marie" for p in personnel)


# ---------------------------------------------------------------------------
# Tests unitaires — pièges
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_pieges_seed(db):
    from src.database import get_pieges
    pieges = await get_pieges(db, 1)
    assert len(pieges) >= 3
    types = {p["type"] for p in pieges}
    assert "rongeur" in types
    assert "oiseau" in types


@pytest.mark.anyio
async def test_ajouter_piege(db):
    from src.database import create_piege, get_pieges
    await create_piege(db, {
        "boutique_id": 1,
        "type": "rongeur",
        "identifiant": "P10",
        "localisation": "Réserve",
    })
    pieges = await get_pieges(db, 1)
    assert any(p["identifiant"] == "P10" for p in pieges)


# ---------------------------------------------------------------------------
# Tests API
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_taches_today(app_client):
    r = await app_client.get("/api/taches/today")
    assert r.status_code == 200
    data = r.json()
    assert "date" in data
    assert "a_faire" in data
    assert "fait" in data
    assert "en_retard" in data


@pytest.mark.anyio
async def test_api_taches_types(app_client):
    r = await app_client.get("/api/taches/types")
    assert r.status_code == 200
    assert len(r.json()) >= 12


@pytest.mark.anyio
async def test_api_creer_tache_type(app_client):
    r = await app_client.post("/api/taches/types", json={
        "code": "test_api_type",
        "libelle": "Test API",
        "frequence": "quotidien",
        "heure_cible": "14:00",
    })
    assert r.status_code == 201
    assert r.json()["libelle"] == "Test API"


@pytest.mark.anyio
async def test_api_valider_tache(app_client):
    # Récupérer un type existant
    r = await app_client.get("/api/taches/types")
    tache = r.json()[0]

    r2 = await app_client.post("/api/taches/valider", json={
        "tache_type_id": tache["id"],
        "operateur": "Éric",
        "date_tache": date.today().isoformat(),
        "conforme": True,
        "commentaire": "OK test",
        "donnees_specifiques": {"test": True},
    })
    assert r2.status_code == 201
    assert r2.json()["valide"] is True


@pytest.mark.anyio
async def test_api_historique_validations(app_client):
    r = await app_client.get("/api/taches/historique")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_api_taches_en_retard(app_client):
    r = await app_client.get("/api/taches/en-retard")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_api_admin_personnel(app_client):
    r = await app_client.get("/api/admin/personnel")
    assert r.status_code == 200
    prenoms = {p["prenom"] for p in r.json()}
    assert "Éric" in prenoms


@pytest.mark.anyio
async def test_api_admin_ajouter_personnel(app_client):
    r = await app_client.post("/api/admin/personnel", json={"prenom": "Thomas"})
    assert r.status_code == 201
    assert r.json()["prenom"] == "Thomas"


@pytest.mark.anyio
async def test_api_admin_pieges(app_client):
    r = await app_client.get("/api/admin/pieges")
    assert r.status_code == 200
    assert len(r.json()) >= 3


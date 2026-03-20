"""
test_api.py — Tests des endpoints FastAPI (via client ASGI, sans réseau)
"""

import pytest
from datetime import datetime, timedelta, timezone

from src.database import insert_releve, ouvrir_alerte

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Boutiques
# ---------------------------------------------------------------------------

async def test_liste_boutiques(app_client):
    r = await app_client.get("/api/boutiques")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert data[0]["nom"] == "Au Comptoir des Lilas"


async def test_boutique_inexistante(app_client):
    r = await app_client.get("/api/boutiques/9999")
    assert r.status_code == 404


async def test_dashboard_retourne_enceintes(app_client):
    r = await app_client.get("/api/boutiques/1/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert "boutique" in data
    assert "enceintes" in data
    assert len(data["enceintes"]) == 4


async def test_dashboard_statut_global_present(app_client):
    r = await app_client.get("/api/boutiques/1/dashboard")
    data = r.json()
    assert data["boutique"]["statut"] in ("ok", "attention", "alerte", "inconnu")


# ---------------------------------------------------------------------------
# Enceintes
# ---------------------------------------------------------------------------

async def test_detail_enceinte(app_client):
    r = await app_client.get("/api/enceintes/1")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == 1
    assert data["seuil_temp_max"] == 4.0


async def test_enceinte_inexistante(app_client):
    r = await app_client.get("/api/enceintes/9999")
    assert r.status_code == 404


async def test_creer_enceinte(app_client):
    payload = {
        "boutique_id": 1,
        "nom": "Congélateur test",
        "type": "congelateur",
        "sonde_zigbee_id": "congelateur_test",
        "seuil_temp_min": -25.0,
        "seuil_temp_max": -18.0,
    }
    r = await app_client.post("/api/enceintes", json=payload)
    assert r.status_code == 201
    assert "id" in r.json()


async def test_modifier_enceinte(app_client):
    r = await app_client.put("/api/enceintes/1", json={"seuil_temp_max": 5.0})
    assert r.status_code == 200
    # Vérifier que la modif est persistée
    r2 = await app_client.get("/api/enceintes/1")
    assert r2.json()["seuil_temp_max"] == 5.0
    # Remettre la valeur d'origine
    await app_client.put("/api/enceintes/1", json={"seuil_temp_max": 4.0})


async def test_statut_enceinte(app_client):
    r = await app_client.get("/api/enceintes/1/status")
    assert r.status_code == 200
    data = r.json()
    assert "statut" in data
    assert "alertes_actives" in data


# ---------------------------------------------------------------------------
# Relevés
# ---------------------------------------------------------------------------

async def test_releves_periode_raccourcie(app_client):
    r = await app_client.get("/api/enceintes/1/releves?periode=24h")
    assert r.status_code == 200
    data = r.json()
    assert "releves" in data
    assert "nb_releves" in data


async def test_releves_periode_invalide(app_client):
    r = await app_client.get("/api/enceintes/1/releves?periode=99j")
    assert r.status_code == 400


async def test_stats_releves(app_client):
    r = await app_client.get("/api/enceintes/1/releves/stats?periode=24h")
    assert r.status_code == 200
    data = r.json()
    assert "enceinte_id" in data
    assert "periode" in data


async def test_export_csv(app_client):
    r = await app_client.get("/api/enceintes/1/releves/export.csv?periode=24h")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    # Vérifier l'en-tête CSV
    assert "horodatage" in r.text


# ---------------------------------------------------------------------------
# Alertes
# ---------------------------------------------------------------------------

async def test_alertes_en_cours_vide(app_client):
    r = await app_client.get("/api/alertes/en-cours")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_alertes_enceinte(app_client):
    r = await app_client.get("/api/enceintes/1/alertes")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Destinataires
# ---------------------------------------------------------------------------

async def test_ajouter_destinataire(app_client):
    payload = {"nom": "Ulysse", "email": "ulysse@metscarnes.fr", "telephone": "+33612345678"}
    r = await app_client.post("/api/destinataires", json=payload)
    assert r.status_code == 201
    assert "id" in r.json()


async def test_destinataire_sans_contact_rejete(app_client):
    payload = {"nom": "Sans contact"}
    r = await app_client.post("/api/destinataires", json=payload)
    assert r.status_code == 400


async def test_liste_destinataires(app_client):
    r = await app_client.get("/api/destinataires")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Rapports
# ---------------------------------------------------------------------------

async def test_liste_rapports(app_client):
    r = await app_client.get("/api/rapports?boutique_id=1")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_rapport_boutique_inexistante(app_client):
    payload = {"boutique_id": 9999, "type": "journalier"}
    r = await app_client.post("/api/rapports/generer", json=payload)
    assert r.status_code == 404


async def test_rapport_type_invalide(app_client):
    payload = {"boutique_id": 1, "type": "hebdomadaire"}
    r = await app_client.post("/api/rapports/generer", json=payload)
    assert r.status_code == 400


async def test_rapport_pdf_inexistant(app_client):
    r = await app_client.get("/api/rapports/9999/pdf")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Système
# ---------------------------------------------------------------------------

async def test_system_status(app_client):
    r = await app_client.get("/api/system/status")
    assert r.status_code == 200
    data = r.json()
    assert "statut" in data
    assert "composants" in data
    assert "base_de_donnees" in data["composants"]

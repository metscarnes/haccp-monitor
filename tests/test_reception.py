"""
test_reception.py — Tests Module Contrôles Réception (fiches 8 et 9)

Couvre :
- CRUD fournisseurs
- Création réception + lignes + finalisation
- Non-conformités (création + liste)
- Endpoints API
"""

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Tests unitaires — base de données
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_creer_fournisseur(db):
    from src.database import create_fournisseur, get_fournisseurs
    fid = await create_fournisseur(db, {"boutique_id": 1, "nom": "Bigard"})
    assert fid > 0
    fournisseurs = await get_fournisseurs(db, 1)
    assert any(f["nom"] == "Bigard" for f in fournisseurs)


@pytest.mark.anyio
async def test_fournisseur_desactiver(db):
    from src.database import create_fournisseur, update_fournisseur, get_fournisseurs
    fid = await create_fournisseur(db, {"boutique_id": 1, "nom": "Fournisseur à supprimer"})
    await update_fournisseur(db, fid, {"actif": False})
    fournisseurs = await get_fournisseurs(db, 1)
    assert not any(f["id"] == fid for f in fournisseurs)


@pytest.mark.anyio
async def test_creer_reception_complete(db):
    from src.database import (
        create_fournisseur, create_reception, add_reception_ligne,
        finaliser_reception, get_reception,
    )
    fid = await create_fournisseur(db, {"boutique_id": 1, "nom": "O'Guste"})
    rid = await create_reception(db, {
        "boutique_id": 1,
        "fournisseur_id": fid,
        "fournisseur_nom": "O'Guste",
        "numero_bon_livraison": "BL-2026-001",
        "operateur": "Éric",
        "heure_livraison": "08:30",
        "temperature_camion": 3.2,
        "proprete_camion": "S",
    })
    assert rid > 0

    # Ajouter 2 lignes
    lid1 = await add_reception_ligne(db, rid, {
        "produit_nom": "Bœuf haché",
        "temperature_produit": 2.8,
        "integrite_emballage": "S",
        "dlc": "2026-03-31",
        "numero_lot": "BIG-2026-0042",
        "quantite": 5.0,
        "heure_stockage": "08:45",
        "conforme": True,
    })
    lid2 = await add_reception_ligne(db, rid, {
        "produit_nom": "Entrecôte",
        "temperature_produit": 6.1,
        "integrite_emballage": "S",
        "dlc": "2026-04-01",
        "numero_lot": "BIG-2026-0043",
        "quantite": 8.0,
        "heure_stockage": "08:47",
        "conforme": False,    # hors seuil température
    })
    assert lid1 > 0
    assert lid2 > 0

    # Finaliser
    await finaliser_reception(db, rid, conforme=False)

    # Vérifier
    rec = await get_reception(db, rid)
    assert rec is not None
    assert rec["conforme"] == 0
    assert len(rec["lignes"]) == 2
    assert rec["lignes"][0]["produit_nom"] == "Bœuf haché"
    assert rec["lignes"][1]["conforme"] == 0


@pytest.mark.anyio
async def test_historique_receptions(db):
    from src.database import create_reception, get_receptions
    await create_reception(db, {
        "boutique_id": 1,
        "fournisseur_nom": "Elivia",
        "operateur": "Ulysse",
    })
    receptions = await get_receptions(db, 1)
    assert len(receptions) >= 1


@pytest.mark.anyio
async def test_creer_non_conformite(db):
    from src.database import create_non_conformite, get_non_conformites
    nc_id = await create_non_conformite(db, {
        "boutique_id": 1,
        "operateur": "Éric",
        "date_livraison": "2026-03-29",
        "fournisseur_nom": "O'Guste",
        "produits": "Entrecôte",
        "nature_nc": ["temperature", "qualite"],
        "commentaires": "Température camion à 7°C",
        "refuse_livraison": False,
        "nc_apres_livraison": True,
        "info_ddpp": False,
    })
    assert nc_id > 0
    ncs = await get_non_conformites(db, 1)
    assert len(ncs) >= 1
    nc = ncs[0]
    assert isinstance(nc["nature_nc"], list)
    assert "temperature" in nc["nature_nc"]


@pytest.mark.anyio
async def test_non_conformite_liee_reception(db):
    from src.database import create_reception, create_non_conformite, get_non_conformites
    rid = await create_reception(db, {
        "boutique_id": 1,
        "fournisseur_nom": "Bigard",
        "operateur": "Éric",
    })
    nc_id = await create_non_conformite(db, {
        "boutique_id": 1,
        "reception_id": rid,
        "operateur": "Éric",
        "fournisseur_nom": "Bigard",
        "nature_nc": ["dlc"],
    })
    ncs = await get_non_conformites(db, 1)
    nc = next(n for n in ncs if n["id"] == nc_id)
    assert nc["reception_id"] == rid


# ---------------------------------------------------------------------------
# Tests API
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_lister_fournisseurs(app_client):
    r = await app_client.get("/api/fournisseurs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_api_ajouter_fournisseur(app_client):
    r = await app_client.post("/api/fournisseurs", json={"nom": "Fournisseur API Test"})
    assert r.status_code == 201
    assert r.json()["nom"] == "Fournisseur API Test"


@pytest.mark.anyio
async def test_api_creer_reception(app_client):
    r = await app_client.post("/api/receptions", json={
        "fournisseur_nom": "Bigard API",
        "operateur": "Éric",
        "temperature_camion": 3.5,
        "proprete_camion": "S",
    })
    assert r.status_code == 201
    assert "id" in r.json()


@pytest.mark.anyio
async def test_api_ajouter_ligne_reception(app_client):
    # Créer une réception
    r = await app_client.post("/api/receptions", json={
        "fournisseur_nom": "Test Fournisseur",
        "operateur": "Éric",
    })
    rid = r.json()["id"]

    # Ajouter une ligne
    r2 = await app_client.post(f"/api/receptions/{rid}/lignes", json={
        "produit_nom": "Côte de bœuf",
        "temperature_produit": 2.5,
        "integrite_emballage": "S",
        "dlc": "2026-04-02",
        "numero_lot": "TEST-001",
        "quantite": 4.0,
        "conforme": True,
    })
    assert r2.status_code == 201
    assert "id" in r2.json()


@pytest.mark.anyio
async def test_api_finaliser_reception(app_client):
    r = await app_client.post("/api/receptions", json={
        "fournisseur_nom": "Finalisation Test",
        "operateur": "Ulysse",
    })
    rid = r.json()["id"]

    r2 = await app_client.post(f"/api/receptions/{rid}/finaliser", json={"conforme": True})
    assert r2.status_code == 200
    assert r2.json()["conforme"] == 1


@pytest.mark.anyio
async def test_api_reception_inexistante(app_client):
    r = await app_client.get("/api/receptions/99999")
    assert r.status_code == 404


@pytest.mark.anyio
async def test_api_historique_receptions(app_client):
    r = await app_client.get("/api/receptions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_api_declarer_nc(app_client):
    r = await app_client.post("/api/non-conformites", json={
        "operateur": "Éric",
        "fournisseur_nom": "O'Guste",
        "produits": "Jambon",
        "nature_nc": ["temperature", "etiquetage"],
        "commentaires": "DLC illisible",
        "refuse_livraison": True,
        "nc_apres_livraison": False,
        "info_ddpp": False,
    })
    assert r.status_code == 201
    assert "id" in r.json()


@pytest.mark.anyio
async def test_api_historique_nc(app_client):
    r = await app_client.get("/api/non-conformites")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

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


@pytest.mark.skip(reason="Schéma v1 obsolète : finaliser_reception supprimé, champs boutique_id/fournisseur_nom/operateur remplacés par personnel_id. Couvert par test_reception_v2.py.")
@pytest.mark.anyio
async def test_creer_reception_complete(db):
    pass


@pytest.mark.skip(reason="Schéma v1 obsolète : create_reception ne prend plus boutique_id/fournisseur_nom/operateur. Couvert par test_reception_v2.py.")
@pytest.mark.anyio
async def test_historique_receptions(db):
    pass


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


@pytest.mark.skip(reason="Schéma v1 obsolète : create_reception ne prend plus boutique_id/fournisseur_nom/operateur. Couvert par test_reception_v2.py.")
@pytest.mark.anyio
async def test_non_conformite_liee_reception(db):
    pass


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
async def test_api_creer_reception(app_client, db):
    cur = await db.execute("SELECT id FROM personnel WHERE boutique_id=1 LIMIT 1")
    personnel_id = (await cur.fetchone())[0]

    r = await app_client.post("/api/receptions", data={
        "personnel_id":      str(personnel_id),
        "heure_reception":   "10:00",
        "temperature_camion": "3.5",
        "proprete_camion":   "satisfaisant",
    })
    assert r.status_code == 201
    assert "id" in r.json()


@pytest.mark.anyio
async def test_api_ajouter_ligne_reception(app_client, db):
    cur = await db.execute("SELECT id FROM personnel WHERE boutique_id=1 LIMIT 1")
    personnel_id = (await cur.fetchone())[0]

    # Créer un produit pour la ligne
    await db.execute(
        """
        INSERT OR IGNORE INTO produits
            (nom, code_unique, categorie, etape, conditionnement, dlc_jours,
             boutique_id, temperature_conservation)
        VALUES ('Côte de bœuf', 'REC_TEST_01', 'matiere_premiere', 1, 'SOUS_VIDE', 0,
                1, '0°C à +4°C')
        """
    )
    cur2 = await db.execute("SELECT id FROM produits WHERE code_unique='REC_TEST_01'")
    produit_id = (await cur2.fetchone())[0]
    await db.commit()

    # Créer une réception (schéma v2 : form-data)
    r = await app_client.post("/api/receptions", data={
        "personnel_id":    str(personnel_id),
        "heure_reception": "10:30",
    })
    assert r.status_code == 201, r.text
    rid = r.json()["id"]

    r2 = await app_client.post(f"/api/receptions/{rid}/lignes", json={
        "produit_id":  produit_id,
        "numero_lot":  "TEST-001",
    })
    assert r2.status_code == 201
    assert "id" in r2.json()


@pytest.mark.anyio
async def test_api_finaliser_reception(app_client, db):
    cur = await db.execute("SELECT id FROM personnel WHERE boutique_id=1 LIMIT 1")
    personnel_id = (await cur.fetchone())[0]

    r = await app_client.post("/api/receptions", data={
        "personnel_id":    str(personnel_id),
        "heure_reception": "11:00",
    })
    assert r.status_code == 201, r.text
    rid = r.json()["id"]

    r2 = await app_client.put(f"/api/receptions/{rid}/cloturer", json={})
    assert r2.status_code == 200
    assert r2.json()["conformite_globale"] == "conforme"


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

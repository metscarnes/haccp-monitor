"""
test_ouvertures.py — Tests Module Ouvertures

Couvre :
- POST /api/ouvertures  → 201 + photo sauvegardée sur disque
- GET  /api/ouvertures  → liste
- GET  /api/ouvertures/suggestions  → matières premières, récentes en premier
- GET  /api/ouvertures/suggestions?q=  → filtre
"""

import pytest
import pytest_asyncio
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers fixtures
# ---------------------------------------------------------------------------

async def _seed_produit_et_personnel(db):
    """Insère un produit matière_première et un personnel, retourne (produit_id, personnel_id)."""
    cursor = await db.execute(
        """
        INSERT INTO produits (nom, code_unique, categorie, etape, conditionnement, dlc_jours,
                              boutique_id, temperature_conservation)
        VALUES (?, ?, 'matiere_premiere', 1, 'SOUS_VIDE', 0, 1, '0°C à +4°C')
        """,
        ("VB-PALERON", "VBR06"),
    )
    produit_id = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO personnel (boutique_id, prenom) VALUES (1, 'TestUser')"
    )
    personnel_id = cursor.lastrowid
    await db.commit()
    return produit_id, personnel_id


# ---------------------------------------------------------------------------
# Tests API
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_post_ouverture_retourne_201(app_client, db):
    """POST /api/ouvertures avec photo simulée → 201 + id dans la réponse."""
    produit_id, personnel_id = await _seed_produit_et_personnel(db)

    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color=(255, 0, 0)).save(buf, format="JPEG")
    fake_jpeg = buf.getvalue()

    r = await app_client.post(
        "/api/ouvertures",
        data={"produit_id": str(produit_id), "personnel_id": str(personnel_id)},
        files={"photo": ("test.jpg", fake_jpeg, "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "id" in data
    assert "timestamp" in data
    assert data["produit_id"] == produit_id
    assert data["personnel_id"] == personnel_id
    assert data["source"] == "catalogue"


@pytest.mark.anyio
async def test_post_ouverture_photo_sauvegardee_sur_disque(app_client, db):
    """Le fichier photo doit exister sur disque après la création."""
    from src.api.routes_ouvertures import PHOTOS_DIR

    produit_id, personnel_id = await _seed_produit_et_personnel(db)

    # Quelques bytes quelconques — Pillow acceptera ça en mode raw
    # On utilise un PNG 1×1 minimal pour éviter les erreurs de décodage
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color=(200, 100, 50)).save(buf, format="JPEG")
    fake_jpeg = buf.getvalue()

    r = await app_client.post(
        "/api/ouvertures",
        data={"produit_id": str(produit_id), "personnel_id": str(personnel_id)},
        files={"photo": ("snap.jpg", fake_jpeg, "image/jpeg")},
    )
    assert r.status_code == 201
    filename = r.json()["photo_filename"]
    assert filename.startswith("OUV-")
    assert filename.endswith(".jpg")
    assert (PHOTOS_DIR / filename).exists()


@pytest.mark.anyio
async def test_get_ouvertures_retourne_liste(app_client, db):
    """GET /api/ouvertures → liste (éventuellement vide)."""
    r = await app_client.get("/api/ouvertures")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_get_ouvertures_contient_champs_jointure(app_client, db):
    """La liste inclut produit_nom et personnel_prenom via JOIN."""
    import io
    from PIL import Image

    produit_id, personnel_id = await _seed_produit_et_personnel(db)

    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color=(0, 0, 0)).save(buf, format="JPEG")

    await app_client.post(
        "/api/ouvertures",
        data={"produit_id": str(produit_id), "personnel_id": str(personnel_id)},
        files={"photo": ("x.jpg", buf.getvalue(), "image/jpeg")},
    )

    r = await app_client.get("/api/ouvertures")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    item = items[0]
    assert "produit_nom" in item
    assert "personnel_prenom" in item
    assert item["produit_nom"] == "VB-PALERON"
    assert item["personnel_prenom"] == "TestUser"


@pytest.mark.anyio
async def test_get_suggestions_retourne_matieres_premieres(app_client, db):
    """GET /api/ouvertures/suggestions → liste de matières premières."""
    # Insérer quelques produits
    await db.execute(
        """
        INSERT INTO produits (nom, code_unique, categorie, etape, conditionnement, dlc_jours,
                              boutique_id, temperature_conservation)
        VALUES ('VB-PALERON', 'VBR06', 'matiere_premiere', 1, 'SOUS_VIDE', 0, 1, '0°C à +4°C')
        """
    )
    await db.execute(
        """
        INSERT INTO produits (nom, code_unique, categorie, etape, conditionnement, dlc_jours,
                              boutique_id, temperature_conservation)
        VALUES ('PAV-ENTRECOTE', 'PAV01', 'pav', 4, 'SOUS_VIDE', 3, 1, '0°C à +4°C')
        """
    )
    await db.commit()

    r = await app_client.get("/api/ouvertures/suggestions")
    assert r.status_code == 200
    items = r.json()
    noms = [i["nom"] for i in items]
    assert "VB-PALERON" in noms
    assert "PAV-ENTRECOTE" not in noms
    for item in items:
        assert "produit_id" in item
        assert "is_recent" in item


@pytest.mark.anyio
async def test_get_suggestions_recentes_en_premier(app_client, db):
    """Les produits issus d'une réception récente ont is_recent=True et apparaissent en tête."""
    # Produit en réception récente
    cursor = await db.execute(
        """
        INSERT INTO produits (nom, code_unique, categorie, etape, conditionnement, dlc_jours,
                              boutique_id, temperature_conservation)
        VALUES ('VB-PALERON', 'VBR06', 'matiere_premiere', 1, 'SOUS_VIDE', 0, 1, '0°C à +4°C')
        """
    )
    produit_recept_id = cursor.lastrowid

    # Produit catalogue seul
    await db.execute(
        """
        INSERT INTO produits (nom, code_unique, categorie, etape, conditionnement, dlc_jours,
                              boutique_id, temperature_conservation)
        VALUES ('VB-BASSE-COTE', 'VBR10', 'matiere_premiere', 1, 'SOUS_VIDE', 0, 1, '0°C à +4°C')
        """
    )

    # Créer une réception d'aujourd'hui avec ce produit
    cursor = await db.execute(
        """
        INSERT INTO receptions (boutique_id, fournisseur_nom, operateur)
        VALUES (1, 'Bigard', 'Éric')
        """
    )
    reception_id = cursor.lastrowid

    await db.execute(
        """
        INSERT INTO reception_lignes (reception_id, produit_id, produit_nom, conforme)
        VALUES (?, ?, 'VB-PALERON', 1)
        """,
        (reception_id, produit_recept_id),
    )
    await db.commit()

    r = await app_client.get("/api/ouvertures/suggestions")
    assert r.status_code == 200
    items = r.json()

    # Le premier item doit être le produit en réception récente
    assert items[0]["produit_id"] == produit_recept_id
    assert items[0]["is_recent"] is True

    # Le suivant doit avoir is_recent=False
    non_recents = [i for i in items if not i["is_recent"]]
    assert any(i["nom"] == "VB-BASSE-COTE" for i in non_recents)


@pytest.mark.anyio
async def test_get_suggestions_filtre_q(app_client, db):
    """GET /api/ouvertures/suggestions?q=PAL → filtre sur nom."""
    await db.execute(
        """
        INSERT INTO produits (nom, code_unique, categorie, etape, conditionnement, dlc_jours,
                              boutique_id, temperature_conservation)
        VALUES ('VB-PALERON', 'VBR06', 'matiere_premiere', 1, 'SOUS_VIDE', 0, 1, '0°C à +4°C')
        """
    )
    await db.execute(
        """
        INSERT INTO produits (nom, code_unique, categorie, etape, conditionnement, dlc_jours,
                              boutique_id, temperature_conservation)
        VALUES ('VB-BASSE-COTE', 'VBR10', 'matiere_premiere', 1, 'SOUS_VIDE', 0, 1, '0°C à +4°C')
        """
    )
    await db.commit()

    r = await app_client.get("/api/ouvertures/suggestions?q=PAL")
    assert r.status_code == 200
    items = r.json()
    noms = [i["nom"] for i in items]
    assert "VB-PALERON" in noms
    assert "VB-BASSE-COTE" not in noms


@pytest.mark.anyio
async def test_get_suggestions_filtre_q_code(app_client, db):
    """GET /api/ouvertures/suggestions?q=VBR → filtre sur code_unique."""
    await db.execute(
        """
        INSERT INTO produits (nom, code_unique, categorie, etape, conditionnement, dlc_jours,
                              boutique_id, temperature_conservation)
        VALUES ('VB-PALERON', 'VBR06', 'matiere_premiere', 1, 'SOUS_VIDE', 0, 1, '0°C à +4°C')
        """
    )
    await db.commit()

    r = await app_client.get("/api/ouvertures/suggestions?q=VBR06")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    assert items[0]["code_unique"] == "VBR06"

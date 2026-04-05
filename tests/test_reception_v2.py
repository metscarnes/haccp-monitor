"""
test_reception_v2.py — Tests Module Réception (schéma v2)

Couvre :
- POST /api/receptions → 201
- POST /api/receptions/{id}/lignes température conforme → conforme=1
- POST /api/receptions/{id}/lignes température hors norme → conforme=0
- POST /api/receptions/{id}/lignes pH hors plage → ph_conforme=0
- PUT  /api/receptions/{id}/cloturer toutes conformes → conformite_globale=conforme
- PUT  /api/receptions/{id}/cloturer une NC → conformite_globale=non_conforme
- GET  /api/receptions retourne la liste
- GET  /api/receptions/{id} retourne les lignes
- GET  /api/receptions/textes-aide-visuel retourne les textes
- Upload photo BL + vérification fichier sur disque
"""

import io
import pytest
import pytest_asyncio
from PIL import Image


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_personnel_produit(db):
    """Insère un personnel et un produit, retourne (personnel_id, produit_id)."""
    cur = await db.execute(
        "INSERT INTO personnel (boutique_id, prenom) VALUES (1, 'Éric')"
    )
    personnel_id = cur.lastrowid

    cur2 = await db.execute(
        """
        INSERT INTO produits
            (nom, code_unique, categorie, etape, conditionnement, dlc_jours,
             boutique_id, temperature_conservation)
        VALUES ('VB-PALERON', 'VBR06', 'matiere_premiere', 1, 'SOUS_VIDE', 0,
                1, '0°C à +4°C')
        """
    )
    produit_id = cur2.lastrowid
    await db.commit()
    return personnel_id, produit_id


def _fake_jpeg():
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color=(120, 60, 30)).save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests API
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_post_reception_retourne_201(app_client, db):
    """POST /api/receptions → 201 avec id dans la réponse."""
    personnel_id, _ = await _seed_personnel_produit(db)

    r = await app_client.post(
        "/api/receptions",
        data={
            "personnel_id":    str(personnel_id),
            "heure_reception": "08:30",
            "temperature_camion": "1.5",
            "proprete_camion": "satisfaisant",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "id" in data
    assert data["personnel_id"] == personnel_id
    assert data["camion_conforme"] == 1     # temp 1.5 < 2 ET propreté OK


@pytest.mark.anyio
async def test_camion_non_conforme_si_temp_haute(app_client, db):
    """camion_conforme=0 si température ≥ 2°C."""
    personnel_id, _ = await _seed_personnel_produit(db)

    r = await app_client.post(
        "/api/receptions",
        data={
            "personnel_id":     str(personnel_id),
            "heure_reception":  "09:00",
            "temperature_camion": "3.5",
            "proprete_camion":  "satisfaisant",
        },
    )
    assert r.status_code == 201
    assert r.json()["camion_conforme"] == 0


@pytest.mark.anyio
async def test_camion_non_conforme_si_proprete_mauvaise(app_client, db):
    """camion_conforme=0 si propreté non_satisfaisant."""
    personnel_id, _ = await _seed_personnel_produit(db)

    r = await app_client.post(
        "/api/receptions",
        data={
            "personnel_id":    str(personnel_id),
            "heure_reception": "09:00",
            "temperature_camion": "1.0",
            "proprete_camion": "non_satisfaisant",
        },
    )
    assert r.status_code == 201
    assert r.json()["camion_conforme"] == 0


@pytest.mark.anyio
async def test_post_ligne_temperature_conforme(app_client, db):
    """Ligne avec température dans la plage → conforme=1, temperature_conforme=1."""
    personnel_id, produit_id = await _seed_personnel_produit(db)

    # Créer une réception (camion OK : temp 1°C)
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00",
              "temperature_camion": "1.0"},
    )
    rid = r.json()["id"]

    # Ajouter ligne : temp 2°C (dans la plage 0-4°C)
    r2 = await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={
            "produit_id":          produit_id,
            "temperature_reception": 2.0,
            "numero_lot":          "LOT-001",
        },
    )
    assert r2.status_code == 201, r2.text
    ligne = r2.json()
    assert ligne["temperature_conforme"] == 1
    assert ligne["conforme"] == 1


@pytest.mark.anyio
async def test_post_ligne_temperature_hors_norme(app_client, db):
    """Ligne avec température hors plage → temperature_conforme=0, conforme=0."""
    personnel_id, produit_id = await _seed_personnel_produit(db)

    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00"},
    )
    rid = r.json()["id"]

    r2 = await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={
            "produit_id":            produit_id,
            "temperature_reception": 6.5,   # > 4°C
        },
    )
    assert r2.status_code == 201
    ligne = r2.json()
    assert ligne["temperature_conforme"] == 0
    assert ligne["conforme"] == 0


@pytest.mark.anyio
async def test_post_ligne_temperature_renforcee_camion_nc(app_client, db):
    """Seuil renforcé : camion >2°C ET temp produit > (max-1=3°C) → non conforme."""
    personnel_id, produit_id = await _seed_personnel_produit(db)

    # Camion à 3°C (non conforme)
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00",
              "temperature_camion": "3.0"},
    )
    rid = r.json()["id"]

    # Produit à 3.5°C : dans la plage normale (≤4°C) MAIS > (4-1=3°C) avec camion NC
    r2 = await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={"produit_id": produit_id, "temperature_reception": 3.5},
    )
    assert r2.status_code == 201
    ligne = r2.json()
    assert ligne["temperature_conforme"] == 0


@pytest.mark.anyio
async def test_post_ligne_ph_conforme(app_client, db):
    """pH entre 5.5 et 5.7 → ph_conforme=1."""
    personnel_id, produit_id = await _seed_personnel_produit(db)
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00"},
    )
    rid = r.json()["id"]

    r2 = await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={"produit_id": produit_id, "ph_valeur": 5.6},
    )
    assert r2.status_code == 201
    assert r2.json()["ph_conforme"] == 1
    assert r2.json()["conforme"] == 1


@pytest.mark.anyio
async def test_post_ligne_ph_hors_plage(app_client, db):
    """pH hors 5.5-5.7 → ph_conforme=0, conforme=0."""
    personnel_id, produit_id = await _seed_personnel_produit(db)
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00"},
    )
    rid = r.json()["id"]

    r2 = await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={"produit_id": produit_id, "ph_valeur": 6.2},
    )
    assert r2.status_code == 201
    ligne = r2.json()
    assert ligne["ph_conforme"] == 0
    assert ligne["conforme"] == 0


@pytest.mark.anyio
async def test_cloturer_toutes_conformes(app_client, db):
    """Clôture avec toutes lignes conformes → conformite_globale='conforme'."""
    personnel_id, produit_id = await _seed_personnel_produit(db)

    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00",
              "temperature_camion": "1.0"},
    )
    rid = r.json()["id"]

    # Deux lignes conformes
    for _ in range(2):
        await app_client.post(
            f"/api/receptions/{rid}/lignes",
            json={"produit_id": produit_id, "temperature_reception": 2.0},
        )

    r_clot = await app_client.put(f"/api/receptions/{rid}/cloturer", json={})
    assert r_clot.status_code == 200
    assert r_clot.json()["conformite_globale"] == "conforme"


@pytest.mark.anyio
async def test_cloturer_avec_ligne_nc(app_client, db):
    """Clôture avec une ligne NC → conformite_globale='non_conforme'."""
    personnel_id, produit_id = await _seed_personnel_produit(db)

    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00"},
    )
    rid = r.json()["id"]

    # Ligne conforme
    await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={"produit_id": produit_id, "temperature_reception": 2.0},
    )
    # Ligne non conforme (couleur)
    await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={"produit_id": produit_id, "couleur_conforme": 0,
              "couleur_observation": "Brunâtre"},
    )

    r_clot = await app_client.put(
        f"/api/receptions/{rid}/cloturer",
        json={"commentaire_nc": "Couleur anormale sur lot 2"},
    )
    assert r_clot.status_code == 200
    body = r_clot.json()
    assert body["conformite_globale"] == "non_conforme"
    assert body["commentaire_nc"] == "Couleur anormale sur lot 2"


@pytest.mark.anyio
async def test_get_receptions_retourne_liste(app_client, db):
    """GET /api/receptions → liste avec champs de jointure."""
    personnel_id, _ = await _seed_personnel_produit(db)

    await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00"},
    )

    r = await app_client.get("/api/receptions")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    item = items[0]
    assert "personnel_prenom" in item
    assert "nb_lignes" in item


@pytest.mark.anyio
async def test_get_reception_detail_avec_lignes(app_client, db):
    """GET /api/receptions/{id} retourne les lignes avec jointures produits."""
    personnel_id, produit_id = await _seed_personnel_produit(db)

    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00"},
    )
    rid = r.json()["id"]

    await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={"produit_id": produit_id, "numero_lot": "LOT-TEST"},
    )

    r2 = await app_client.get(f"/api/receptions/{rid}")
    assert r2.status_code == 200
    rec = r2.json()
    assert "lignes" in rec
    assert len(rec["lignes"]) == 1
    assert rec["lignes"][0]["produit_nom"] == "VB-PALERON"


@pytest.mark.anyio
async def test_get_textes_aide_visuel(app_client, db):
    """GET /api/receptions/textes-aide-visuel retourne les espèces connues."""
    r = await app_client.get("/api/receptions/textes-aide-visuel")
    assert r.status_code == 200
    data = r.json()
    assert "Boeuf" in data
    assert "Veau" in data
    assert "Porc" in data
    boeuf = data["Boeuf"]
    assert "couleur" in boeuf
    assert "odeur" in boeuf
    assert "ph" in boeuf
    assert "normal" in boeuf["couleur"]
    assert "anomalies" in boeuf["couleur"]


@pytest.mark.anyio
async def test_upload_photo_bl(app_client, db):
    """Upload photo BL → fichier présent sur disque."""
    from src.api.routes_reception import PHOTOS_BL_DIR

    personnel_id, _ = await _seed_personnel_produit(db)
    jpeg = _fake_jpeg()

    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00"},
        files={"photo_bl": ("bl.jpg", jpeg, "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    filename = data.get("photo_bl_filename")
    assert filename is not None
    assert filename.startswith("BL-")
    assert (PHOTOS_BL_DIR / filename).exists()


@pytest.mark.anyio
async def test_reception_inexistante(app_client, db):
    """GET /api/receptions/99999 → 404."""
    r = await app_client.get("/api/receptions/99999")
    assert r.status_code == 404

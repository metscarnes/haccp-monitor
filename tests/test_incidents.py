"""
test_incidents.py — Tests Fiches Incident PCR01

Couvre :
- POST /api/fiches-incident → 201
- GET  /api/fiches-incident retourne la liste
- GET  /api/fiches-incident/{id} retourne le détail
- PUT  /api/fiches-incident/{id} mise à jour statut → cloturee_le auto-rempli
- Filtrage par statut fonctionne
- Upload signature PNG et vérification fichier sur disque
"""

import io
import pytest
from PIL import Image


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_reception_avec_ligne(db, app_client):
    """Crée personnel + produit + fournisseur + réception + ligne. Retourne le dict complet."""
    # Personnel
    await db.execute(
        "INSERT OR IGNORE INTO personnel (boutique_id, prenom) VALUES (1, 'Éric')"
    )
    cur = await db.execute("SELECT id FROM personnel WHERE boutique_id=1 AND prenom='Éric'")
    personnel_id = (await cur.fetchone())[0]

    # Produit
    await db.execute(
        """
        INSERT OR IGNORE INTO produits
            (nom, code_unique, categorie, etape, conditionnement, dlc_jours,
             boutique_id, temperature_conservation)
        VALUES ('PALERON', 'INC01', 'matiere_premiere', 1, 'SOUS_VIDE', 0, 1, '0°C à +4°C')
        """
    )
    cur = await db.execute("SELECT id FROM produits WHERE code_unique='INC01'")
    produit_id = (await cur.fetchone())[0]

    # Fournisseur
    await db.execute(
        "INSERT OR IGNORE INTO fournisseurs (nom, boutique_id) VALUES ('Fournisseur Test INC', 1)"
    )
    cur = await db.execute("SELECT id FROM fournisseurs WHERE nom='Fournisseur Test INC' AND boutique_id=1")
    fournisseur_id = (await cur.fetchone())[0]

    await db.commit()

    # Réception via API
    r = await app_client.post(
        "/api/receptions",
        data={
            "personnel_id":      str(personnel_id),
            "heure_reception":   "09:00",
            "temperature_camion": "1.0",
            "proprete_camion":   "satisfaisant",
        },
    )
    assert r.status_code == 201, r.text
    reception_id = r.json()["id"]

    # Ligne via API
    r2 = await app_client.post(
        f"/api/receptions/{reception_id}/lignes",
        json={
            "produit_id":            produit_id,
            "fournisseur_id":        fournisseur_id,
            "temperature_reception": 5.0,   # NC : dépasse 4°C
            "couleur_ok":            True,
            "odeur_ok":              True,
            "texture_ok":            True,
            "emballage_ok":          True,
            "ph":                    None,
            "numero_lot":            "LOT-TEST-001",
        },
    )
    assert r2.status_code == 201, r2.text
    ligne_id = r2.json()["id"]

    return {
        "personnel_id":  personnel_id,
        "produit_id":    produit_id,
        "fournisseur_id": fournisseur_id,
        "reception_id":  reception_id,
        "ligne_id":      ligne_id,
    }


def _fake_png():
    buf = io.BytesIO()
    Image.new("RGB", (100, 50), color=(200, 100, 50)).save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_post_fiche_incident_retourne_201(app_client, db):
    """POST /api/fiches-incident → 201 et retourne l'id."""
    ctx = await _seed_reception_avec_ligne(db, app_client)

    r = await app_client.post(
        "/api/fiches-incident",
        data={
            "reception_id":     str(ctx["reception_id"]),
            "fournisseur_id":   str(ctx["fournisseur_id"]),
            "produit_id":       str(ctx["produit_id"]),
            "nature_probleme":  "temperature",
            "action_immediate": "refus",
            "livreur_present":  "0",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "id" in data
    assert data["nature_probleme"] == "temperature"
    assert data["action_immediate"] == "refus"
    assert data["statut"] == "ouverte"


@pytest.mark.anyio
async def test_get_fiches_retourne_liste(app_client, db):
    """GET /api/fiches-incident retourne une liste non vide après création."""
    ctx = await _seed_reception_avec_ligne(db, app_client)

    await app_client.post(
        "/api/fiches-incident",
        data={
            "reception_id":     str(ctx["reception_id"]),
            "fournisseur_id":   str(ctx["fournisseur_id"]),
            "produit_id":       str(ctx["produit_id"]),
            "nature_probleme":  "hygiene",
            "action_immediate": "isoler",
            "livreur_present":  "0",
        },
    )

    r = await app_client.get("/api/fiches-incident")
    assert r.status_code == 200, r.text
    fiches = r.json()
    assert isinstance(fiches, list)
    assert len(fiches) >= 1


@pytest.mark.anyio
async def test_get_fiche_detail(app_client, db):
    """GET /api/fiches-incident/{id} retourne le détail de la fiche."""
    ctx = await _seed_reception_avec_ligne(db, app_client)

    r_create = await app_client.post(
        "/api/fiches-incident",
        data={
            "reception_id":     str(ctx["reception_id"]),
            "fournisseur_id":   str(ctx["fournisseur_id"]),
            "produit_id":       str(ctx["produit_id"]),
            "nature_probleme":  "temperature",
            "action_immediate": "refus",
            "livreur_present":  "1",
            "description":      "Produit hors plage température",
            "numero_lot":       "LOT-001",
        },
    )
    assert r_create.status_code == 201
    fiche_id = r_create.json()["id"]

    r = await app_client.get(f"/api/fiches-incident/{fiche_id}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"] == fiche_id
    assert data["description"] == "Produit hors plage température"
    assert data["numero_lot"] == "LOT-001"


@pytest.mark.anyio
async def test_put_fiche_statut_cloture_remplit_cloturee_le(app_client, db):
    """PUT statut → 'cloturee' doit auto-remplir cloturee_le."""
    ctx = await _seed_reception_avec_ligne(db, app_client)

    r_create = await app_client.post(
        "/api/fiches-incident",
        data={
            "reception_id":     str(ctx["reception_id"]),
            "fournisseur_id":   str(ctx["fournisseur_id"]),
            "produit_id":       str(ctx["produit_id"]),
            "nature_probleme":  "temperature",
            "action_immediate": "refus",
            "livreur_present":  "0",
        },
    )
    assert r_create.status_code == 201
    fiche_id = r_create.json()["id"]

    # Avant clôture : cloturee_le doit être null
    assert r_create.json().get("cloturee_le") is None

    r_put = await app_client.put(
        f"/api/fiches-incident/{fiche_id}",
        json={
            "statut":            "cloturee",
            "cloturee_par":      ctx["personnel_id"],
            "action_corrective": "Retour fournisseur",
        },
    )
    assert r_put.status_code == 200, r_put.text
    data = r_put.json()
    assert data["statut"] == "cloturee"
    assert data["cloturee_le"] is not None    # auto-rempli
    assert data["action_corrective"] == "Retour fournisseur"


@pytest.mark.anyio
async def test_filtrage_par_statut(app_client, db):
    """GET /api/fiches-incident?statut=ouverte ne retourne que les fiches ouvertes."""
    ctx = await _seed_reception_avec_ligne(db, app_client)

    # Créer deux fiches
    r1 = await app_client.post(
        "/api/fiches-incident",
        data={
            "reception_id":     str(ctx["reception_id"]),
            "fournisseur_id":   str(ctx["fournisseur_id"]),
            "produit_id":       str(ctx["produit_id"]),
            "nature_probleme":  "temperature",
            "action_immediate": "refus",
            "livreur_present":  "0",
        },
    )
    r2 = await app_client.post(
        "/api/fiches-incident",
        data={
            "reception_id":     str(ctx["reception_id"]),
            "fournisseur_id":   str(ctx["fournisseur_id"]),
            "produit_id":       str(ctx["produit_id"]),
            "nature_probleme":  "hygiene",
            "action_immediate": "isoler",
            "livreur_present":  "0",
        },
    )
    fiche2_id = r2.json()["id"]

    # Clôturer la deuxième
    await app_client.put(
        f"/api/fiches-incident/{fiche2_id}",
        json={"statut": "cloturee", "cloturee_par": ctx["personnel_id"]},
    )

    r_open = await app_client.get("/api/fiches-incident?statut=ouverte")
    assert r_open.status_code == 200
    fiches_ouvertes = r_open.json()
    assert all(f["statut"] == "ouverte" for f in fiches_ouvertes)

    r_closed = await app_client.get("/api/fiches-incident?statut=cloturee")
    assert r_closed.status_code == 200
    fiches_closes = r_closed.json()
    assert all(f["statut"] == "cloturee" for f in fiches_closes)


@pytest.mark.anyio
async def test_upload_signature_png_fichier_sur_disque(app_client, db):
    """Upload d'une signature PNG → fichier créé sur disque + endpoint /signature OK."""
    ctx = await _seed_reception_avec_ligne(db, app_client)

    png_bytes = _fake_png()

    r = await app_client.post(
        "/api/fiches-incident",
        data={
            "reception_id":     str(ctx["reception_id"]),
            "fournisseur_id":   str(ctx["fournisseur_id"]),
            "produit_id":       str(ctx["produit_id"]),
            "nature_probleme":  "temperature",
            "action_immediate": "refus",
            "livreur_present":  "1",
        },
        files={"signature_livreur": ("signature.png", png_bytes, "image/png")},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    fiche_id = data["id"]

    # Le champ signature_livreur_filename doit être rempli
    assert data.get("signature_livreur_filename"), "signature_livreur_filename vide"

    # L'endpoint /signature doit retourner l'image
    r_sig = await app_client.get(f"/api/fiches-incident/{fiche_id}/signature")
    assert r_sig.status_code == 200, r_sig.text
    assert r_sig.headers["content-type"] == "image/png"
    # Vérifier que c'est bien une image PNG valide
    img = Image.open(io.BytesIO(r_sig.content))
    assert img.format == "PNG"

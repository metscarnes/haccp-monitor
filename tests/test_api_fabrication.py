"""
test_api_fabrication.py — Tests Module Fabrication (API + moteur FIFO)

Couvre :
  Test 1 — POST /api/recettes puis GET /api/recettes  → création et listing
  Test 2 — GET  /api/fabrications/fifo-lots           → lot le plus ancien retourné,
                                                         null si aucun stock
  Test 3 — POST /api/fabrications                     → 201 + lot MC-YYYYMMDD-XXXX généré
"""

import pytest
from datetime import date, timedelta

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Helpers de seed
# ---------------------------------------------------------------------------

async def _seed_base(db) -> dict:
    """
    Insère les données bouchons nécessaires aux tests fabrication.

    Retourne un dict avec les IDs créés :
      produit_fini_id, produit_ing1_id, produit_ing2_id,
      personnel_id,
      reception_ligne_ancienne_id, reception_ligne_recente_id
    """
    # --- Produit fini ---
    cur = await db.execute(
        "INSERT INTO produits (boutique_id, nom, categorie, dlc_jours) "
        "VALUES (1, 'Merguez maison', 'plat_cuisine', 3)"
    )
    produit_fini_id = cur.lastrowid

    # --- Ingrédient 1 : agneau haché (2 lots de dates différentes = test FIFO) ---
    cur = await db.execute(
        "INSERT INTO produits (boutique_id, nom, categorie, dlc_jours) "
        "VALUES (1, 'Agneau haché', 'matiere_premiere', 2)"
    )
    produit_ing1_id = cur.lastrowid

    # --- Ingrédient 2 : épices (aucune réception → lot null) ---
    cur = await db.execute(
        "INSERT INTO produits (boutique_id, nom, categorie, dlc_jours) "
        "VALUES (1, 'Épices merguez', 'matiere_premiere', 30)"
    )
    produit_ing2_id = cur.lastrowid

    # --- Personnel ---
    cur = await db.execute(
        "INSERT OR IGNORE INTO personnel (boutique_id, prenom) VALUES (1, 'Éric')"
    )
    cur = await db.execute("SELECT id FROM personnel WHERE boutique_id=1 AND prenom='Éric'")
    personnel_id = (await cur.fetchone())[0]

    # --- Fournisseur ---
    cur = await db.execute(
        "INSERT INTO fournisseurs (boutique_id, nom) VALUES (1, 'Fournisseur FIFO Test')"
    )
    fourn_id = cur.lastrowid

    # --- Réception ancienne (il y a 5 jours) ---
    date_ancienne = (date.today() - timedelta(days=5)).isoformat()
    cur = await db.execute(
        "INSERT INTO receptions (personnel_id, date_reception, heure_reception) VALUES (?, ?, '07:00')",
        (personnel_id, date_ancienne),
    )
    rec_ancienne_id = cur.lastrowid

    dlc_ancienne = (date.today() + timedelta(days=1)).isoformat()   # DLC très courte
    cur = await db.execute(
        "INSERT INTO reception_lignes (reception_id, produit_id, fournisseur_id, numero_lot, dlc) "
        "VALUES (?, ?, ?, 'LOT-ANCIEN-001', ?)",
        (rec_ancienne_id, produit_ing1_id, fourn_id, dlc_ancienne),
    )
    rl_ancienne_id = cur.lastrowid

    # --- Réception récente (aujourd'hui) ---
    cur = await db.execute(
        "INSERT INTO receptions (personnel_id, date_reception, heure_reception) VALUES (?, ?, '09:00')",
        (personnel_id, date.today().isoformat()),
    )
    rec_recente_id = cur.lastrowid

    dlc_recente = (date.today() + timedelta(days=5)).isoformat()    # DLC plus longue
    cur = await db.execute(
        "INSERT INTO reception_lignes (reception_id, produit_id, fournisseur_id, numero_lot, dlc) "
        "VALUES (?, ?, ?, 'LOT-RECENT-001', ?)",
        (rec_recente_id, produit_ing1_id, fourn_id, dlc_recente),
    )
    rl_recente_id = cur.lastrowid

    await db.commit()

    return {
        "produit_fini_id":           produit_fini_id,
        "produit_ing1_id":           produit_ing1_id,
        "produit_ing2_id":           produit_ing2_id,
        "personnel_id":              personnel_id,
        "reception_ligne_ancienne_id": rl_ancienne_id,
        "reception_ligne_recente_id":  rl_recente_id,
    }


async def _creer_recette_test(app_client, ids: dict) -> int:
    """Crée une recette via l'API et retourne son ID."""
    payload = {
        "nom": "Merguez Test FIFO",
        "produit_fini_id": ids["produit_fini_id"],
        "dlc_jours": 3,
        "instructions": "Mélanger, embosser.",
        "ingredients": [
            {"produit_id": ids["produit_ing1_id"], "quantite": 1.2, "unite": "kg"},
            {"produit_id": ids["produit_ing2_id"], "quantite": 50,  "unite": "g"},
        ],
    }
    r = await app_client.post("/api/recettes", json=payload)
    assert r.status_code == 201, f"Création recette échouée : {r.text}"
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Test 1 — Création et listing de recettes
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_post_puis_get_recettes(app_client, db):
    """POST /api/recettes crée la recette ; GET /api/recettes la retourne."""
    ids = await _seed_base(db)

    # Création
    payload = {
        "nom": "Saucisse maison",
        "produit_fini_id": ids["produit_fini_id"],
        "dlc_jours": 3,
        "instructions": "Hacher, assaisonner, embosser.",
        "ingredients": [
            {"produit_id": ids["produit_ing1_id"], "quantite": 0.8, "unite": "kg"},
        ],
    }
    r_post = await app_client.post("/api/recettes", json=payload)
    assert r_post.status_code == 201, r_post.text
    recette = r_post.json()

    assert recette["nom"] == "Saucisse maison"
    assert recette["dlc_jours"] == 3
    assert recette["produit_fini_id"] == ids["produit_fini_id"]
    assert len(recette["ingredients"]) == 1
    assert recette["ingredients"][0]["quantite"] == 0.8
    assert recette["ingredients"][0]["unite"] == "kg"

    recette_id = recette["id"]

    # Listing
    r_get = await app_client.get("/api/recettes")
    assert r_get.status_code == 200
    noms = [rec["nom"] for rec in r_get.json()]
    assert "Saucisse maison" in noms

    # Détail
    r_detail = await app_client.get(f"/api/recettes/{recette_id}")
    assert r_detail.status_code == 200
    assert r_detail.json()["id"] == recette_id


@pytest.mark.anyio
async def test_get_recette_inexistante_retourne_404(app_client, db):
    r = await app_client.get("/api/recettes/99999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Test 2 — Moteur FIFO (cœur de la fonctionnalité)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_fifo_retourne_lot_le_plus_ancien(app_client, db):
    """
    FIFO strict : pour l'ingrédient 1 (2 lots), doit retourner LOT-ANCIEN-001
    (DLC la plus courte). Pour l'ingrédient 2 (0 lot), lot_fifo doit être null.
    """
    ids = await _seed_base(db)
    recette_id = await _creer_recette_test(app_client, ids)

    r = await app_client.get(f"/api/fabrications/fifo-lots?recette_id={recette_id}")
    assert r.status_code == 200, r.text

    data = r.json()
    assert data["recette_id"] == recette_id
    ingredients = data["ingredients"]
    assert len(ingredients) == 2

    # --- Ingrédient 1 : agneau haché — doit avoir le LOT ANCIEN ---
    ing1 = next(i for i in ingredients if i["produit_id"] == ids["produit_ing1_id"])
    assert ing1["lot_fifo"] is not None, "Un lot devrait être trouvé pour l'agneau haché"
    assert ing1["lot_fifo"]["numero_lot"] == "LOT-ANCIEN-001", (
        f"FIFO KO : attendu LOT-ANCIEN-001, obtenu {ing1['lot_fifo']['numero_lot']}"
    )

    # --- Ingrédient 2 : épices — aucune réception, lot doit être null ---
    ing2 = next(i for i in ingredients if i["produit_id"] == ids["produit_ing2_id"])
    assert ing2["lot_fifo"] is None, (
        "Aucune réception pour les épices → lot_fifo devrait être null"
    )


@pytest.mark.anyio
async def test_fifo_recette_inexistante_retourne_404(app_client, db):
    r = await app_client.get("/api/fabrications/fifo-lots?recette_id=99999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Test 3 — Enregistrement d'une fabrication
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_post_fabrication_retourne_201_avec_lot_mc(app_client, db):
    """
    POST /api/fabrications → 201 avec lot_interne au format MC-YYYYMMDD-XXXX.
    """
    ids = await _seed_base(db)
    recette_id = await _creer_recette_test(app_client, ids)

    # Récupérer les IDs des recette_ingredients via l'API
    r_detail = await app_client.get(f"/api/recettes/{recette_id}")
    ingredients = r_detail.json()["ingredients"]
    ing1 = next(i for i in ingredients if i["produit_id"] == ids["produit_ing1_id"])

    payload = {
        "recette_id":  recette_id,
        "date":        date.today().isoformat(),
        "personnel_id": ids["personnel_id"],
        "lots": [
            {
                "recette_ingredient_id": ing1["id"],
                "reception_ligne_id":    ids["reception_ligne_ancienne_id"],
            }
        ],
        "info_complementaire": "Batch test FIFO",
    }

    r = await app_client.post("/api/fabrications", json=payload)
    assert r.status_code == 201, r.text

    fab = r.json()
    assert "lot_interne" in fab

    # Vérifier le format INITIALES-YYYYMMDD-XXXX (initiales extraites du nom de recette)
    # "Merguez Test FIFO" → MTF ; format : {initiales}-{YYYYMMDD}-{counter:04d}
    lot = fab["lot_interne"]
    import re
    pattern = r"^[A-Z]+-\d{8}-\d{4}$"
    assert re.match(pattern, lot), (
        f"Format lot_interne invalide : '{lot}' (attendu INITIALES-YYYYMMDD-XXXX)"
    )

    today_str = date.today().strftime("%Y%m%d")
    assert today_str in lot, f"La date du jour {today_str} devrait être dans le lot : {lot}"
    assert lot.startswith("MTF-"), (
        f"Initiales incorrectes : '{lot}' (attendu MTF- pour 'Merguez Test FIFO')"
    )


@pytest.mark.anyio
async def test_post_fabrication_lots_vides_retourne_422(app_client, db):
    """Un payload sans lots doit être refusé (422)."""
    ids = await _seed_base(db)
    recette_id = await _creer_recette_test(app_client, ids)

    payload = {
        "recette_id":   recette_id,
        "date":         date.today().isoformat(),
        "personnel_id": ids["personnel_id"],
        "lots":         [],
    }
    r = await app_client.post("/api/fabrications", json=payload)
    assert r.status_code == 422


@pytest.mark.anyio
async def test_post_fabrication_recette_inexistante_retourne_404(app_client, db):
    """Une fabrication avec recette inconnue doit retourner 404."""
    ids = await _seed_base(db)

    payload = {
        "recette_id":   99999,
        "date":         date.today().isoformat(),
        "personnel_id": ids["personnel_id"],
        "lots": [{"recette_ingredient_id": 1, "reception_ligne_id": 1}],
    }
    r = await app_client.post("/api/fabrications", json=payload)
    assert r.status_code == 404

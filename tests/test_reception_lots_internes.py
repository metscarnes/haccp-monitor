"""
test_reception_lots_internes.py — Lot interne sur toute la commande.

Couvre POST /api/receptions/{id}/lots-internes :
- génère un lot interne {BL}-{code}-{JJMMAA} pour les lignes sans N° de lot
- ne touche pas les lignes ayant déjà un lot
- une ligne sans DLC reste 'en_attente' (lot rempli, date manquante)
- 400 si le n° de BL n'est pas saisi
"""

import pytest


async def _seed_personnel(db):
    await db.execute("INSERT OR IGNORE INTO personnel (boutique_id, prenom) VALUES (1, 'Éric')")
    cur = await db.execute("SELECT id FROM personnel WHERE boutique_id = 1 AND prenom = 'Éric'")
    return (await cur.fetchone())[0]


async def _seed_article_catalogue(db, code, dlc_type="dlc"):
    """Crée un fournisseur + un article catalogue avec un dlc_type donné."""
    await db.execute("INSERT OR IGNORE INTO fournisseurs (boutique_id, nom) VALUES (1, 'FOURNX')")
    cur = await db.execute("SELECT id FROM fournisseurs WHERE nom = 'FOURNX'")
    fid = (await cur.fetchone())[0]
    await db.execute(
        """INSERT INTO catalogue_fournisseur (fournisseur_id, code_article, designation, dlc_type)
           VALUES (?, ?, ?, ?)""",
        (fid, code, f"ARTICLE {code}", dlc_type),
    )
    cur2 = await db.execute(
        "SELECT id FROM catalogue_fournisseur WHERE code_article = ?", (code,)
    )
    await db.commit()
    return fid, (await cur2.fetchone())[0]


@pytest.mark.anyio
async def test_lots_internes_toute_commande(app_client, db):
    personnel_id = await _seed_personnel(db)
    fid, cat_dlc = await _seed_article_catalogue(db, "ART-DLC", "dlc")
    _, cat_nodlc = await _seed_article_catalogue(db, "ART-NODLC", "no_dlc")

    # Réception avec n° BL + date connue (préfixe et suffixe JJMMAA déterministes)
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00",
              "temperature_camion": "1.0", "date_reception": "2026-06-19",
              "numero_bon_livraison": "BL42"},
    )
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert r.json()["numero_bon_livraison"] == "BL42"

    # Ligne 1 : article DLC, lot manquant + DLC manquante → restera en attente après lot
    l1 = (await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={"catalogue_fournisseur_id": cat_dlc, "fournisseur_id": fid,
              "designation_libre": "ARTICLE ART-DLC",
              "dlc_type": "dlc", "temperature_reception": 2.0, "poids_kg": 10.0},
    )).json()
    # Ligne 2 : article no_dlc, lot manquant → complet une fois le lot généré
    l2 = (await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={"catalogue_fournisseur_id": cat_nodlc, "fournisseur_id": fid,
              "designation_libre": "ARTICLE ART-NODLC",
              "dlc_type": "no_dlc", "temperature_reception": 2.0, "poids_kg": 5.0},
    )).json()
    # Ligne 3 : a déjà un lot fournisseur → non touchée
    l3 = (await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={"catalogue_fournisseur_id": cat_dlc, "fournisseur_id": fid,
              "designation_libre": "ARTICLE ART-DLC",
              "dlc_type": "dlc", "numero_lot": "FOURN-LOT-9", "dlc": "2026-12-31",
              "temperature_reception": 2.0, "poids_kg": 3.0},
    )).json()

    # Appliquer le lot interne à toute la commande
    res = await app_client.post(f"/api/receptions/{rid}/lots-internes")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["generes"] == 2          # l1 + l2
    assert body["deja_lot"] == 1         # l3
    assert body["restant_attente"] == 1  # l1 (DLC manquante)

    # Vérifier en base
    cur = await db.execute(
        "SELECT numero_lot, lot_interne, statut FROM reception_lignes WHERE id = ?", (l1["id"],)
    )
    n1, li1, s1 = await cur.fetchone()
    assert n1 == "BL42-ART-DLC-190626"
    assert li1 == 1
    assert s1 == "en_attente"            # lot OK mais DLC encore manquante

    cur = await db.execute(
        "SELECT numero_lot, lot_interne, statut FROM reception_lignes WHERE id = ?", (l2["id"],)
    )
    n2, li2, s2 = await cur.fetchone()
    assert n2 == "BL42-ART-NODLC-190626"
    assert li2 == 1
    assert s2 == "complet"               # no_dlc : lot suffit → entre en stock

    cur = await db.execute(
        "SELECT numero_lot, lot_interne FROM reception_lignes WHERE id = ?", (l3["id"],)
    )
    n3, li3 = await cur.fetchone()
    assert n3 == "FOURN-LOT-9"           # lot fournisseur préservé
    assert li3 == 0


@pytest.mark.anyio
async def test_lots_internes_sans_bl_400(app_client, db):
    personnel_id = await _seed_personnel(db)
    fid, cat = await _seed_article_catalogue(db, "ART-Z", "dlc")
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00",
              "temperature_camion": "1.0"},
    )
    rid = r.json()["id"]
    await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={"catalogue_fournisseur_id": cat, "fournisseur_id": fid,
              "designation_libre": "ARTICLE ART-Z",
              "dlc_type": "dlc", "temperature_reception": 2.0, "poids_kg": 1.0},
    )
    res = await app_client.post(f"/api/receptions/{rid}/lots-internes")
    assert res.status_code == 400
    assert "bon de livraison" in res.json()["detail"].lower()

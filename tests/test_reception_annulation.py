"""
test_reception_annulation.py — Annulation (suppression) d'une réception.

Couvre :
- DELETE /api/receptions/{id} supprime la réception + ses lignes (stock dérivé)
- Le lien commande est retiré et la commande « livree » repasse « confirmee »
- Annulation bloquée (409) si une donnée aval existe (ex. ligne de fabrication)
- 404 si la réception n'existe pas
"""

import pytest


async def _seed_personnel_produit(db):
    await db.execute("INSERT OR IGNORE INTO personnel (boutique_id, prenom) VALUES (1, 'Éric')")
    cur = await db.execute("SELECT id FROM personnel WHERE boutique_id = 1 AND prenom = 'Éric'")
    personnel_id = (await cur.fetchone())[0]
    await db.execute(
        """INSERT OR IGNORE INTO produits
               (nom, code_unique, categorie, etape, conditionnement, dlc_jours,
                boutique_id, temperature_conservation)
           VALUES ('VB-PALERON', 'VBR06', 'matiere_premiere', 1, 'SOUS_VIDE', 0,
                   1, '0°C à +4°C')"""
    )
    cur2 = await db.execute("SELECT id FROM produits WHERE code_unique = 'VBR06'")
    produit_id = (await cur2.fetchone())[0]
    await db.commit()
    return personnel_id, produit_id


async def _creer_reception_avec_ligne(app_client, personnel_id, produit_id):
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00",
              "temperature_camion": "1.0"},
    )
    rid = r.json()["id"]
    r2 = await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={"produit_id": produit_id, "temperature_reception": 2.0,
              "numero_lot": "LOT-001", "dlc": "2026-12-31", "poids_kg": 10.0},
    )
    ligne_id = r2.json()["id"]
    return rid, ligne_id


@pytest.mark.anyio
async def test_annuler_reception_supprime_tout(app_client, db):
    personnel_id, produit_id = await _seed_personnel_produit(db)
    rid, ligne_id = await _creer_reception_avec_ligne(app_client, personnel_id, produit_id)

    r = await app_client.delete(f"/api/receptions/{rid}")
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] is True

    # Réception et lignes effacées
    cur = await db.execute("SELECT COUNT(*) FROM receptions WHERE id = ?", (rid,))
    assert (await cur.fetchone())[0] == 0
    cur = await db.execute("SELECT COUNT(*) FROM reception_lignes WHERE reception_id = ?", (rid,))
    assert (await cur.fetchone())[0] == 0


@pytest.mark.anyio
async def test_annuler_reception_libere_commande(app_client, db):
    personnel_id, produit_id = await _seed_personnel_produit(db)
    rid, _ = await _creer_reception_avec_ligne(app_client, personnel_id, produit_id)

    # Fournisseur + commande « livree » liée à la réception
    await db.execute("INSERT OR IGNORE INTO fournisseurs (id, boutique_id, nom) VALUES (99, 1, 'Bigard')")
    await db.execute(
        """INSERT INTO commandes (id, boutique_id, fournisseur_id, numero_commande,
                                  date_commande, statut)
           VALUES (777, 1, 99, 'CMD-TEST-001', '2026-06-15', 'livree')"""
    )
    await db.execute(
        "INSERT INTO commande_receptions_mapping (commande_id, reception_id) VALUES (777, ?)",
        (rid,),
    )
    await db.commit()

    r = await app_client.delete(f"/api/receptions/{rid}")
    assert r.status_code == 200, r.text
    assert 777 in r.json()["commande_ids"]

    # Mapping retiré, commande repassée « confirmee »
    cur = await db.execute("SELECT COUNT(*) FROM commande_receptions_mapping WHERE reception_id = ?", (rid,))
    assert (await cur.fetchone())[0] == 0
    cur = await db.execute("SELECT statut FROM commandes WHERE id = 777")
    assert (await cur.fetchone())[0] == "confirmee"


@pytest.mark.anyio
async def test_annuler_reception_bloquee_si_fabrication(app_client, db):
    personnel_id, produit_id = await _seed_personnel_produit(db)
    rid, ligne_id = await _creer_reception_avec_ligne(app_client, personnel_id, produit_id)

    # Une ligne de fabrication consomme cette ligne de réception → blocage
    await db.execute("INSERT OR IGNORE INTO recettes (id, nom, dlc_jours) VALUES (1, 'Recette test', 3)")
    await db.execute(
        """INSERT INTO fabrications (id, recette_id, date, lot_interne, personnel_id)
           VALUES (1, 1, '2026-06-16', 'FAB-TEST-001', ?)""",
        (personnel_id,),
    )
    await db.execute(
        """INSERT INTO fabrication_lots (fabrication_id, recette_ingredient_id, reception_ligne_id)
           VALUES (1, 1, ?)""",
        (ligne_id,),
    )
    await db.commit()

    r = await app_client.delete(f"/api/receptions/{rid}")
    assert r.status_code == 409, r.text
    assert "fabrication" in r.text.lower()

    # Rien n'a été supprimé
    cur = await db.execute("SELECT COUNT(*) FROM receptions WHERE id = ?", (rid,))
    assert (await cur.fetchone())[0] == 1


@pytest.mark.anyio
async def test_annuler_reception_inexistante_404(app_client, db):
    r = await app_client.delete("/api/receptions/999999")
    assert r.status_code == 404

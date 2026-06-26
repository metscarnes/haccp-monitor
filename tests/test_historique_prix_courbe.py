"""
test_historique_prix_courbe.py — Endpoint GET /catalogue/{id}/historique-prix (courbe d'évolution).

Vérifie que les prix constatés à chaque clôture s'accumulent et ressortent triés,
avec le prix de référence catalogue actuel pour la ligne de comparaison.
"""
import pytest


async def _personnel(db):
    await db.execute(
        "INSERT OR IGNORE INTO personnel (id, boutique_id, prenom, actif) VALUES (1, 1, 'Test', 1)"
    )
    await db.commit()


async def _reception_cloturee(client, db, fid, cat_id, prix_bl, date_recep):
    cur = await db.execute(
        """INSERT INTO receptions (personnel_id, heure_reception, fournisseur_principal_id, statut, date_reception)
           VALUES (1, '08:00', ?, 'en_cours', ?)""",
        (fid, date_recep),
    )
    await db.commit()
    rid = cur.lastrowid
    await db.execute(
        """INSERT INTO reception_lignes
               (reception_id, catalogue_fournisseur_id, poids_kg, prix_unitaire_ht, statut, conforme)
           VALUES (?, ?, 10.0, ?, 'complet', 1)""",
        (rid, cat_id, prix_bl),
    )
    await db.commit()
    r = await client.put(f"/api/receptions/{rid}/cloturer", json={})
    assert r.status_code == 200, r.text
    return rid


@pytest.mark.anyio
async def test_courbe_prix_accumule_les_releves(app_client, db):
    await _personnel(db)
    r = await app_client.post("/api/achats/fournisseurs", json={"nom": "Bourdicaud"})
    fid = r.json()["id"]
    r = await app_client.post("/api/achats/catalogue", json={
        "fournisseur_id": fid, "code_article": "CB01", "designation": "Côte de boeuf",
        "prix_achat_ht": 12.0, "format_prix": "kg", "famille": "Viande",
    })
    cat_id = r.json()["id"]

    # Trois réceptions avec prix BL croissants → 3 points dans l'historique
    await _reception_cloturee(app_client, db, fid, cat_id, 12.00, "2026-01-10")
    await _reception_cloturee(app_client, db, fid, cat_id, 12.80, "2026-02-15")
    await _reception_cloturee(app_client, db, fid, cat_id, 13.55, "2026-03-20")

    r = await app_client.get(f"/api/achats/catalogue/{cat_id}/historique-prix")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["designation"] == "Côte de boeuf"
    assert data["prix_reference_kg"] == 12.0  # référence catalogue inchangée (semi-auto)

    pts = data["points"]
    assert len(pts) == 3
    # Triés du plus ancien au plus récent
    assert [p["date_constat"] for p in pts] == ["2026-01-10", "2026-02-15", "2026-03-20"]
    assert [p["prix_kg"] for p in pts] == [12.0, 12.8, 13.55]
    assert all(p["source"] == "bl" for p in pts)


@pytest.mark.anyio
async def test_courbe_article_sans_historique(app_client, db):
    r = await app_client.post("/api/achats/fournisseurs", json={"nom": "MetroPro"})
    fid = r.json()["id"]
    r = await app_client.post("/api/achats/catalogue", json={
        "fournisseur_id": fid, "code_article": "X1", "designation": "Article neuf",
        "prix_achat_ht": 5.0, "format_prix": "kg",
    })
    cat_id = r.json()["id"]
    r = await app_client.get(f"/api/achats/catalogue/{cat_id}/historique-prix")
    assert r.status_code == 200, r.text
    assert r.json()["points"] == []


@pytest.mark.anyio
async def test_courbe_article_inconnu(app_client, db):
    r = await app_client.get("/api/achats/catalogue/999999/historique-prix")
    assert r.status_code == 404

"""
test_variations_prix.py — Endpoint GET /catalogue/variations-prix (vue d'ensemble).

Vérifie que la vue liste TOUS les articles ayant au moins 2 prix constatés sur la
période, avec la variation premier→dernier prix, triés par ampleur décroissante,
et que le filtre de période exclut les relevés trop anciens.
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


async def _article(client, fid, code, designation, prix):
    r = await client.post("/api/achats/catalogue", json={
        "fournisseur_id": fid, "code_article": code, "designation": designation,
        "prix_achat_ht": prix, "format_prix": "kg", "famille": "Viande",
    })
    return r.json()["id"]


@pytest.mark.anyio
async def test_variations_triees_par_ampleur(app_client, db):
    await _personnel(db)
    r = await app_client.post("/api/achats/fournisseurs", json={"nom": "Bourdicaud"})
    fid = r.json()["id"]

    # Boeuf : forte hausse (10 → 13 = +30 %)
    boeuf = await _article(app_client, fid, "B1", "Boeuf", 10.0)
    await _reception_cloturee(app_client, db, fid, boeuf, 10.0, "2026-06-05")
    await _reception_cloturee(app_client, db, fid, boeuf, 13.0, "2026-06-25")

    # Poulet : légère baisse (8 → 7.6 = -5 %)
    poulet = await _article(app_client, fid, "P1", "Poulet", 8.0)
    await _reception_cloturee(app_client, db, fid, poulet, 8.0, "2026-06-05")
    await _reception_cloturee(app_client, db, fid, poulet, 7.6, "2026-06-25")

    r = await app_client.get("/api/achats/catalogue/variations-prix?jours=60")
    assert r.status_code == 200, r.text
    data = r.json()
    vars = data["variations"]
    assert len(vars) == 2
    # Trié par |variation| décroissante : boeuf (+30 %) avant poulet (-5 %)
    assert vars[0]["designation"] == "Boeuf"
    assert vars[0]["ecart_pct"] == 30.0
    assert vars[0]["prix_kg_debut"] == 10.0
    assert vars[0]["prix_kg_fin"] == 13.0
    assert vars[1]["designation"] == "Poulet"
    assert vars[1]["ecart_pct"] == -5.0
    # Points fournis pour la mini-sparkline
    assert len(vars[0]["points"]) == 2


@pytest.mark.anyio
async def test_variations_exclut_un_seul_releve(app_client, db):
    await _personnel(db)
    r = await app_client.post("/api/achats/fournisseurs", json={"nom": "MetroPro"})
    fid = r.json()["id"]
    art = await _article(app_client, fid, "S1", "Solo", 5.0)
    # Une seule réception = pas de variation mesurable → absent de la vue
    await _reception_cloturee(app_client, db, fid, art, 5.0, "2026-06-20")

    r = await app_client.get("/api/achats/catalogue/variations-prix?jours=60")
    assert r.status_code == 200, r.text
    assert r.json()["variations"] == []


@pytest.mark.anyio
async def test_variations_filtre_periode(app_client, db):
    await _personnel(db)
    r = await app_client.post("/api/achats/fournisseurs", json={"nom": "Vieux"})
    fid = r.json()["id"]
    art = await _article(app_client, fid, "A1", "Ancien", 10.0)
    # 2 relevés dont un très ancien : sur 7 jours, un seul reste → exclu.
    await _reception_cloturee(app_client, db, fid, art, 10.0, "2026-01-01")
    await _reception_cloturee(app_client, db, fid, art, 12.0, "2026-06-30")

    # Fenêtre large : la variation existe.
    r = await app_client.get("/api/achats/catalogue/variations-prix?jours=3650")
    assert r.status_code == 200
    designations = [v["designation"] for v in r.json()["variations"]]
    assert "Ancien" in designations

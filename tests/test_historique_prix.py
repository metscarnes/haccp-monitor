"""
test_historique_prix.py — Étape 5 : historisation des prix + MAJ catalogue semi-auto.

Vérifie :
- la clôture alimente historique_prix_achat (1 ligne par article avec prix + catalogue) ;
- GET /catalogue/ecarts-prix/{reception_id} renvoie les écarts significatifs en attente ;
- POST /catalogue/{id}/appliquer-prix met à jour le prix de référence + marque l'historique ;
- aucun écart si prix BL ≈ catalogue ; pas d'historisation sans article catalogue.
"""
import pytest


async def _personnel(db):
    await db.execute(
        "INSERT OR IGNORE INTO personnel (id, boutique_id, prenom, actif) VALUES (1, 1, 'Test', 1)"
    )
    await db.commit()


async def _setup(client, db, prix_cat=12.0, prix_bl=12.0, avec_catalogue=True):
    """Réception clôturable : catalogue (Viande, €/kg) + 1 ligne réception avec prix BL."""
    await _personnel(db)
    r = await client.post("/api/achats/fournisseurs", json={"nom": "Bourdicaud"})
    fid = r.json()["id"]
    cat_id = None
    if avec_catalogue:
        r = await client.post("/api/achats/catalogue", json={
            "fournisseur_id": fid, "code_article": "CB01", "designation": "Côte de boeuf",
            "prix_achat_ht": prix_cat, "format_prix": "kg", "famille": "Viande",
        })
        cat_id = r.json()["id"]

    cur = await db.execute(
        """INSERT INTO receptions (personnel_id, heure_reception, fournisseur_principal_id, statut)
           VALUES (1, '08:00', ?, 'en_cours')""",
        (fid,),
    )
    await db.commit()
    rid = cur.lastrowid
    await db.execute(
        """INSERT INTO reception_lignes
               (reception_id, catalogue_fournisseur_id, poids_kg, prix_unitaire_ht, statut, conforme)
           VALUES (?, ?, 9.4, ?, 'complet', 1)""",
        (rid, cat_id, prix_bl),
    )
    await db.commit()
    return {"reception_id": rid, "fournisseur_id": fid, "cat_id": cat_id}


@pytest.mark.anyio
async def test_cloture_historise_et_detecte_ecart(app_client, db):
    # Catalogue 12 €/kg, BL 15 €/kg → écart +25 %
    ids = await _setup(app_client, db, prix_cat=12.0, prix_bl=15.0)
    r = await app_client.put(f"/api/receptions/{ids['reception_id']}/cloturer", json={})
    assert r.status_code == 200, r.text

    # historique alimenté
    cur = await db.execute(
        "SELECT prix_ht, prix_kg, prix_kg_precedent, source, applique_au_catalogue "
        "FROM historique_prix_achat WHERE reception_id = ?", (ids["reception_id"],)
    )
    rows = [dict(x) for x in await cur.fetchall()]
    assert len(rows) == 1
    assert rows[0]["prix_ht"] == 15.0
    assert rows[0]["prix_kg"] == 15.0           # viande → €/kg direct
    assert rows[0]["prix_kg_precedent"] == 12.0  # référence au moment du constat
    assert rows[0]["source"] == "bl"
    assert rows[0]["applique_au_catalogue"] == 0

    # l'écart est exposé
    r = await app_client.get(f"/api/achats/catalogue/ecarts-prix/{ids['reception_id']}")
    assert r.status_code == 200, r.text
    ecarts = r.json()["ecarts"]
    assert len(ecarts) == 1
    e = ecarts[0]
    assert e["catalogue_fournisseur_id"] == ids["cat_id"]
    assert e["prix_kg_constate"] == 15.0
    assert e["prix_kg_reference"] == 12.0
    assert e["ecart_pct"] == 25.0
    assert e["deja_applique"] is False


@pytest.mark.anyio
async def test_appliquer_prix_met_a_jour_catalogue(app_client, db):
    ids = await _setup(app_client, db, prix_cat=12.0, prix_bl=15.0)
    await app_client.put(f"/api/receptions/{ids['reception_id']}/cloturer", json={})

    # Appliquer le nouveau prix
    r = await app_client.post(
        f"/api/achats/catalogue/{ids['cat_id']}/appliquer-prix",
        json={"nouveau_prix_ht": 15.0, "reception_id": ids["reception_id"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ancien_prix_ht"] == 12.0
    assert r.json()["nouveau_prix_ht"] == 15.0

    # Le catalogue est à jour
    r = await app_client.get(f"/api/achats/catalogue/{ids['cat_id']}")
    assert r.json()["prix_achat_ht"] == 15.0

    # L'historique est marqué appliqué, et l'écart ne ressort plus
    cur = await db.execute(
        "SELECT applique_au_catalogue FROM historique_prix_achat WHERE reception_id = ?",
        (ids["reception_id"],),
    )
    assert (await cur.fetchone())[0] == 1
    r = await app_client.get(f"/api/achats/catalogue/ecarts-prix/{ids['reception_id']}")
    assert r.json()["ecarts"] == []


@pytest.mark.anyio
async def test_pas_decart_si_prix_egal(app_client, db):
    ids = await _setup(app_client, db, prix_cat=12.0, prix_bl=12.0)
    await app_client.put(f"/api/receptions/{ids['reception_id']}/cloturer", json={})
    # historisé quand même (trace), mais aucun écart significatif
    cur = await db.execute(
        "SELECT COUNT(*) FROM historique_prix_achat WHERE reception_id = ?", (ids["reception_id"],)
    )
    assert (await cur.fetchone())[0] == 1
    r = await app_client.get(f"/api/achats/catalogue/ecarts-prix/{ids['reception_id']}")
    assert r.json()["ecarts"] == []


@pytest.mark.anyio
async def test_pas_historise_sans_article_catalogue(app_client, db):
    # Ligne sans catalogue_fournisseur_id → rien à rattacher → pas d'historisation
    ids = await _setup(app_client, db, avec_catalogue=False)
    await app_client.put(f"/api/receptions/{ids['reception_id']}/cloturer", json={})
    cur = await db.execute(
        "SELECT COUNT(*) FROM historique_prix_achat WHERE reception_id = ?", (ids["reception_id"],)
    )
    assert (await cur.fetchone())[0] == 0


@pytest.mark.anyio
async def test_appliquer_prix_article_inconnu(app_client, db):
    r = await app_client.post(
        "/api/achats/catalogue/999999/appliquer-prix",
        json={"nouveau_prix_ht": 10.0},
    )
    assert r.status_code == 404

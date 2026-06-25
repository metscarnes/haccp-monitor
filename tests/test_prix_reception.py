"""
test_prix_reception.py — Étape 3 : le prix d'achat circule jusqu'à reception_lignes.

Couvre :
- POST /api/receptions/{id}/lignes persiste prix_unitaire_ht / montant_ht ;
- une mise à jour partielle de ligne (complétion d'un lot) n'efface pas le prix ;
- POST /api/achats/catalogue/comparer-prix normalise en €/kg et signale l'écart,
  en neutralisant le piège kg/colis.
"""
import pytest


async def _personnel(db):
    await db.execute(
        "INSERT OR IGNORE INTO personnel (id, boutique_id, prenom, actif) VALUES (1, 1, 'Test', 1)"
    )
    await db.commit()


@pytest.mark.anyio
async def test_ligne_reception_persiste_prix(app_client, db):
    await _personnel(db)
    # Réception
    r = await app_client.post("/api/receptions", data={
        "personnel_id": 1, "heure_reception": "08:00", "date_reception": "2026-06-25",
        "temperature_camion": 2.0, "proprete_camion": "satisfaisant",
    })
    assert r.status_code == 201, r.text
    rid = r.json()["id"]

    # Ligne AVEC prix
    r = await app_client.post(f"/api/receptions/{rid}/lignes", json={
        "designation_libre": "Côte de boeuf", "numero_lot": "L100",
        "dlc": "2026-07-10", "dlc_type": "dlc", "poids_kg": 10.0,
        "prix_unitaire_ht": 18.50, "montant_ht": 185.00,
    })
    assert r.status_code == 201, r.text
    ligne = r.json()
    lid = ligne["id"]
    assert ligne["prix_unitaire_ht"] == 18.50
    assert ligne["montant_ht"] == 185.00

    # Complétion partielle (on change le lot, sans renvoyer le prix) → prix conservé
    r = await app_client.put(f"/api/receptions/{rid}/lignes/{lid}", json={
        "numero_lot": "L100-bis", "poids_kg": 10.0,
    })
    assert r.status_code == 200, r.text
    maj = r.json()
    assert maj["prix_unitaire_ht"] == 18.50, "le prix ne doit pas être effacé par une complétion partielle"
    assert maj["montant_ht"] == 185.00
    assert maj["numero_lot"] == "L100-bis"


@pytest.mark.anyio
async def test_ligne_reception_sans_prix_reste_null(app_client, db):
    await _personnel(db)
    r = await app_client.post("/api/receptions", data={
        "personnel_id": 1, "heure_reception": "08:00", "proprete_camion": "satisfaisant",
    })
    rid = r.json()["id"]
    r = await app_client.post(f"/api/receptions/{rid}/lignes", json={
        "designation_libre": "Bavette", "numero_lot": "L200",
        "dlc": "2026-07-08", "dlc_type": "dlc", "poids_kg": 5.0,
    })
    assert r.status_code == 201, r.text
    assert r.json()["prix_unitaire_ht"] is None
    assert r.json()["montant_ht"] is None


@pytest.mark.anyio
async def test_comparer_prix_viande_kg_ecart_significatif(app_client, db):
    # Catalogue viande à 17.90 €/kg, BL à 18.50 → +3.35 % significatif
    r = await app_client.post("/api/achats/fournisseurs", json={"nom": "Bourdicaud"})
    fid = r.json()["id"]
    r = await app_client.post("/api/achats/catalogue", json={
        "fournisseur_id": fid, "code_article": "CB01", "designation": "Côte de boeuf",
        "prix_achat_ht": 17.90, "format_prix": "kg", "famille": "Viande",
    })
    cat_id = r.json()["id"]

    r = await app_client.post("/api/achats/catalogue/comparer-prix", json={
        "items": [{"catalogue_fournisseur_id": cat_id, "prix_unitaire": 18.50, "unite_prix": "kg"}],
        "seuil_pct": 2.0,
    })
    assert r.status_code == 200, r.text
    res = r.json()["resultats"][0]
    assert res["trouve"] is True
    assert res["comparable"] is True
    assert res["prix_kg_catalogue"] == 17.90
    assert res["prix_kg_bl"] == 18.50
    assert res["ecart_significatif"] is True
    assert res["ecart_pct"] > 0


@pytest.mark.anyio
async def test_comparer_prix_colis_normalise_en_kg(app_client, db):
    # Article au colis : 90 €/colis, poids colis 5 kg → 18 €/kg. BL 92.50/colis → 18.50 €/kg.
    r = await app_client.post("/api/achats/fournisseurs", json={"nom": "MetroPro"})
    fid = r.json()["id"]
    r = await app_client.post("/api/achats/catalogue", json={
        "fournisseur_id": fid, "code_article": "EMB01", "designation": "Barquettes",
        "prix_achat_ht": 90.0, "format_prix": "colis", "famille": "Hygiène et emballage",
        "qte_par_colis": 5, "poids_unitaire_kg": 1.0,
    })
    cat_id = r.json()["id"]

    r = await app_client.post("/api/achats/catalogue/comparer-prix", json={
        "items": [{"catalogue_fournisseur_id": cat_id, "prix_unitaire": 92.50, "unite_prix": "colis"}],
    })
    assert r.status_code == 200, r.text
    res = r.json()["resultats"][0]
    assert res["comparable"] is True
    assert round(res["prix_kg_catalogue"], 2) == 18.00
    assert round(res["prix_kg_bl"], 2) == 18.50
    assert res["ecart_significatif"] is True  # +2.78 % > 2 %


@pytest.mark.anyio
async def test_comparer_prix_article_inconnu(app_client, db):
    r = await app_client.post("/api/achats/catalogue/comparer-prix", json={
        "items": [{"catalogue_fournisseur_id": 999999, "prix_unitaire": 10.0, "unite_prix": "kg"}],
    })
    assert r.status_code == 200, r.text
    res = r.json()["resultats"][0]
    assert res["trouve"] is False

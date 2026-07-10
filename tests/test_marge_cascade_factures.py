"""
test_marge_cascade_factures.py — Cascade de vérité du CMV : factures VALIDÉES
> saisie manuelle > calcul catalogue.

Contexte : le module marge valorisait le CMV uniquement au prix catalogue
(poids reçu × prix de référence), sans jamais lire les factures. Avec la
refonte facture (fiabilité des montants), le prix RÉELLEMENT FACTURÉ (une fois
la facture validée) doit primer — c'est la source la plus fiable.

Règles testées :
- _achats_reels_factures (routes_inventaire.py) ne compte QUE les factures
  statut='validee' (brouillon/litige/rapprochee exclus : pas encore un montant sûr).
- Filtré sur la date de RÉCEPTION rattachée (pas date_facture) — rattachement
  correct à l'exercice, cohérent avec le calcul catalogue existant.
- Un AVOIR (sans reception_id propre) compte sur la période de la réception de
  SA FACTURE LIÉE, en négatif.
- GET /api/inventaire/marge : cascade factures > saisie manuelle > catalogue.
  achats.source ∈ {'factures','reel','calcule'}, achats.ht_calcule toujours
  présent (référence), achats.ecart_reel_calcule = écart vs catalogue.
"""
import pytest


async def _fournisseur(client, nom="Fournisseur Marge"):
    r = await client.post("/api/achats/fournisseurs", json={"nom": nom})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _reception(db, fournisseur_id, date_reception):
    await db.execute(
        "INSERT OR IGNORE INTO personnel (id, boutique_id, prenom, actif) VALUES (1, 1, 'Test', 1)"
    )
    cur = await db.execute(
        """INSERT INTO receptions (personnel_id, heure_reception, fournisseur_principal_id,
                                    statut, date_reception)
           VALUES (1, '08:00', ?, 'cloturee', ?)""",
        (fournisseur_id, date_reception),
    )
    await db.commit()
    return cur.lastrowid


async def _facture_validee(client, fournisseur_id, reception_id, montant_ht,
                           type_doc="facture", facture_liee_id=None):
    payload = {
        "fournisseur_id": fournisseur_id,
        "type": type_doc,
        "lignes": [{
            "designation": "Article", "type_ligne": "marchandise",
            "tva_pct": 5.5, "montant_facture_ht": montant_ht,
        }],
    }
    if reception_id:
        payload["reception_id"] = reception_id
    if facture_liee_id:
        payload["facture_liee_id"] = facture_liee_id
    r = await client.post("/api/achats/factures", json=payload)
    assert r.status_code == 201, r.text
    fac_id = r.json()["id"]
    r2 = await client.put(f"/api/achats/factures/{fac_id}", json={
        "numero_facture": f"FA-{fac_id}", "statut": "validee",
    })
    assert r2.status_code == 200, r2.text
    return fac_id


async def _facture_brouillon(client, fournisseur_id, reception_id, montant_ht):
    r = await client.post("/api/achats/factures", json={
        "fournisseur_id": fournisseur_id, "reception_id": reception_id,
        "lignes": [{
            "designation": "Article", "type_ligne": "marchandise",
            "tva_pct": 5.5, "montant_facture_ht": montant_ht,
        }],
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_facture_validee_prime_sur_catalogue(app_client, db):
    from src.api.routes_inventaire import _achats_reels_factures
    fid = await _fournisseur(app_client)
    rec = await _reception(db, fid, "2026-06-15")
    await _facture_validee(app_client, fid, rec, 250.0)

    res = await _achats_reels_factures(db, "2026-06-01", "2026-06-30")
    assert res["nb_factures"] == 1
    assert res["ht"] == pytest.approx(250.0)


@pytest.mark.asyncio
async def test_facture_brouillon_exclue(app_client, db):
    from src.api.routes_inventaire import _achats_reels_factures
    fid = await _fournisseur(app_client)
    rec = await _reception(db, fid, "2026-06-15")
    await _facture_brouillon(app_client, fid, rec, 999.0)

    res = await _achats_reels_factures(db, "2026-06-01", "2026-06-30")
    assert res["nb_factures"] == 0
    assert res["ht"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_filtre_sur_date_reception_pas_date_facture(app_client, db):
    from src.api.routes_inventaire import _achats_reels_factures
    fid = await _fournisseur(app_client)
    # Réception le 15 juin, facture ÉMISE (date_facture) le 5 juillet — doit
    # compter sur juin (date de réception), pas sur juillet.
    rec = await _reception(db, fid, "2026-06-15")
    r = await app_client.post("/api/achats/factures", json={
        "fournisseur_id": fid, "reception_id": rec, "date_facture": "2026-07-05",
        "lignes": [{"designation": "Article", "type_ligne": "marchandise",
                    "tva_pct": 5.5, "montant_facture_ht": 180.0}],
    })
    fac_id = r.json()["id"]
    await app_client.put(f"/api/achats/factures/{fac_id}",
                         json={"numero_facture": "FA-X", "statut": "validee"})

    res_juin = await _achats_reels_factures(db, "2026-06-01", "2026-06-30")
    assert res_juin["ht"] == pytest.approx(180.0)
    res_juillet = await _achats_reels_factures(db, "2026-07-01", "2026-07-31")
    assert res_juillet["ht"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_avoir_compte_sur_periode_facture_liee(app_client, db):
    from src.api.routes_inventaire import _achats_reels_factures
    fid = await _fournisseur(app_client)
    rec = await _reception(db, fid, "2026-06-10")
    fac_id = await _facture_validee(app_client, fid, rec, 500.0)
    # Avoir : pas de reception_id propre, lié à la facture d'origine.
    await _facture_validee(app_client, fid, None, 80.0,
                           type_doc="avoir", facture_liee_id=fac_id)

    res = await _achats_reels_factures(db, "2026-06-01", "2026-06-30")
    assert res["nb_factures"] == 2
    assert res["ht"] == pytest.approx(420.0)  # 500 - 80


@pytest.mark.asyncio
async def test_tableau_marge_cascade_source_factures(app_client, db):
    fid = await _fournisseur(app_client)
    rec = await _reception(db, fid, "2026-06-15")
    await _facture_validee(app_client, fid, rec, 300.0)

    r = await app_client.get(
        "/api/inventaire/marge?date_debut=2026-06-01&date_fin=2026-06-30")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["achats"]["source"] == "factures"
    assert data["achats"]["ht"] == pytest.approx(300.0)
    assert data["achats"]["nb_factures"] == 1
    assert data["achats"]["ht_calcule"] is not None  # référence toujours présente


@pytest.mark.asyncio
async def test_tableau_marge_repli_calcule_sans_facture(app_client, db):
    r = await app_client.get(
        "/api/inventaire/marge?date_debut=2026-01-01&date_fin=2026-01-31")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["achats"]["source"] == "calcule"
    assert data["achats"]["nb_factures"] == 0


@pytest.mark.asyncio
async def test_saisie_manuelle_secours_si_pas_de_facture(app_client, db):
    body = {"date_debut": "2026-02-01", "date_fin": "2026-02-28", "montant_ht": 777.0}
    r = await app_client.put("/api/inventaire/marge/achats-reels", json=body)
    assert r.status_code == 200, r.text

    r2 = await app_client.get(
        "/api/inventaire/marge?date_debut=2026-02-01&date_fin=2026-02-28")
    data = r2.json()
    assert data["achats"]["source"] == "reel"
    assert data["achats"]["ht"] == pytest.approx(777.0)


@pytest.mark.asyncio
async def test_facture_prime_meme_avec_saisie_manuelle_presente(app_client, db):
    """La saisie manuelle existe pour la période, mais une facture validée
    arrive ensuite : les factures doivent primer (cascade convenue)."""
    fid = await _fournisseur(app_client)
    body = {"date_debut": "2026-03-01", "date_fin": "2026-03-31", "montant_ht": 111.0}
    await app_client.put("/api/inventaire/marge/achats-reels", json=body)

    rec = await _reception(db, fid, "2026-03-15")
    await _facture_validee(app_client, fid, rec, 222.0)

    r = await app_client.get(
        "/api/inventaire/marge?date_debut=2026-03-01&date_fin=2026-03-31")
    data = r.json()
    assert data["achats"]["source"] == "factures"
    assert data["achats"]["ht"] == pytest.approx(222.0)

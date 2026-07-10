"""
test_marge_cascade_factures.py — Achats HT du CMV calculés RÉCEPTION PAR
RÉCEPTION (jamais globalement sur la période).

Contexte : une première version basculait TOUTE la période sur les factures dès
qu'une seule facture validée existait, ce qui faisait DISPARAÎTRE du calcul les
réceptions dont la facture était encore en litige (ou inexistante) — sous-
comptant le CMV et gonflant artificiellement la marge affichée. Diagnostiqué en
conditions réelles : 9 réceptions sur une semaine, 7 factures validées + 2 en
litige (Dipsa, Saveur d'Antoine) → les 2 en litige disparaissaient entièrement.

Règle corrigée, PAR RÉCEPTION :
  1. Facture 'validee' OU 'litige' → montant HT facturé (un litige porte un
     montant réel, le désaccord sera réglé par un avoir plus tard, mais le
     montant facturé aujourd'hui est bien une charge réelle).
  2. Sinon, prix BL saisi à la réception (reception_lignes.montant_ht ou
     prix_unitaire_ht × poids) — lu sur le vrai document, plus fiable qu'une
     estimation catalogue.
  3. Sinon, calcul catalogue (poids × prix de référence) — dernier repli.
Une réception SANS AUCUNE facture (même brouillon) est signalée en anomalie
opérationnelle (le hook de clôture doit toujours en créer une), mais reste
COMPTÉE (niveau 2 ou 3) — jamais ignorée silencieusement.
"""
import pytest


async def _fournisseur(client, nom="Fournisseur Marge"):
    r = await client.post("/api/achats/fournisseurs", json={"nom": nom})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _catalogue(client, fournisseur_id, prix_kg=10.0, code="ART01"):
    r = await client.post("/api/achats/catalogue", json={
        "fournisseur_id": fournisseur_id, "code_article": code,
        "designation": "Article test", "prix_achat_ht": prix_kg, "format_prix": "kg",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _reception_avec_ligne(db, fournisseur_id, date_reception, *,
                                poids_kg=10.0, prix_unitaire_ht=None, montant_ht=None,
                                catalogue_fournisseur_id=None):
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
    rid = cur.lastrowid
    await db.execute(
        """INSERT INTO reception_lignes (reception_id, catalogue_fournisseur_id, poids_kg,
                                         prix_unitaire_ht, montant_ht, statut)
           VALUES (?, ?, ?, ?, ?, 'complet')""",
        (rid, catalogue_fournisseur_id, poids_kg, prix_unitaire_ht, montant_ht),
    )
    await db.commit()
    return rid


async def _facture(client, fournisseur_id, reception_id, montant_ht, statut=None):
    r = await client.post("/api/achats/factures", json={
        "fournisseur_id": fournisseur_id, "reception_id": reception_id,
        "lignes": [{
            "designation": "Article", "type_ligne": "marchandise",
            "tva_pct": 5.5, "montant_facture_ht": montant_ht,
        }],
    })
    assert r.status_code == 201, r.text
    fac_id = r.json()["id"]
    if statut:
        r2 = await client.put(f"/api/achats/factures/{fac_id}",
                              json={"numero_facture": f"FA-{fac_id}", "statut": statut})
        assert r2.status_code == 200, r2.text
    return fac_id


@pytest.mark.asyncio
async def test_facture_validee_prime(app_client, db):
    from src.api.routes_inventaire import _achats_reels_par_reception
    fid = await _fournisseur(app_client)
    rec = await _reception_avec_ligne(db, fid, "2026-06-15", poids_kg=10.0)
    await _facture(app_client, fid, rec, 250.0, statut="validee")

    res = await _achats_reels_par_reception(db, "2026-06-01", "2026-06-30")
    assert res["nb_receptions"] == 1
    assert res["nb_source_facture"] == 1
    assert res["ht"] == pytest.approx(250.0)
    assert res["anomalies_sans_facture"] == []


@pytest.mark.asyncio
async def test_facture_en_litige_compte_normalement(app_client, db):
    """LE bug corrigé : une facture en litige porte un montant réel, elle ne
    doit JAMAIS disparaître du calcul."""
    from src.api.routes_inventaire import _achats_reels_par_reception
    fid = await _fournisseur(app_client)
    rec = await _reception_avec_ligne(db, fid, "2026-06-15", poids_kg=10.0)
    await _facture(app_client, fid, rec, 400.0, statut="litige")

    res = await _achats_reels_par_reception(db, "2026-06-01", "2026-06-30")
    assert res["nb_receptions"] == 1
    assert res["nb_source_facture"] == 1
    assert res["ht"] == pytest.approx(400.0)


@pytest.mark.asyncio
async def test_neuf_receptions_sept_validees_deux_litiges(app_client, db):
    """Reproduit le scénario réel qui a révélé le bug : aucune réception ne
    doit disparaître, qu'elle soit validée OU en litige."""
    from src.api.routes_inventaire import _achats_reels_par_reception
    fid = await _fournisseur(app_client)
    total_attendu = 0.0
    for i in range(7):
        rec = await _reception_avec_ligne(db, fid, "2026-06-15", poids_kg=5.0)
        await _facture(app_client, fid, rec, 100.0 + i, statut="validee")
        total_attendu += 100.0 + i
    for i in range(2):
        rec = await _reception_avec_ligne(db, fid, "2026-06-15", poids_kg=5.0)
        await _facture(app_client, fid, rec, 200.0 + i, statut="litige")
        total_attendu += 200.0 + i

    res = await _achats_reels_par_reception(db, "2026-06-01", "2026-06-30")
    assert res["nb_receptions"] == 9
    assert res["nb_source_facture"] == 9
    assert res["ht"] == pytest.approx(total_attendu)


@pytest.mark.asyncio
async def test_facture_brouillon_repli_sur_prix_bl(app_client, db):
    """Une facture brouillon n'est PAS assez fiable (montants pas confirmés) :
    on retombe sur le prix BL saisi à la réception, pas sur zéro."""
    from src.api.routes_inventaire import _achats_reels_par_reception
    fid = await _fournisseur(app_client)
    rec = await _reception_avec_ligne(db, fid, "2026-06-15", poids_kg=10.0,
                                      prix_unitaire_ht=15.0)  # BL : 10kg × 15 = 150
    await _facture(app_client, fid, rec, 999.0, statut=None)  # reste 'brouillon'

    res = await _achats_reels_par_reception(db, "2026-06-01", "2026-06-30")
    assert res["nb_source_bl"] == 1
    assert res["nb_source_facture"] == 0
    assert res["ht"] == pytest.approx(150.0)  # PAS 999 (brouillon ignoré)


@pytest.mark.asyncio
async def test_prix_bl_prime_sur_catalogue(app_client, db):
    from src.api.routes_inventaire import _achats_reels_par_reception
    fid = await _fournisseur(app_client)
    cat_id = await _catalogue(app_client, fid, prix_kg=8.0)  # catalogue dit 8€/kg
    await _reception_avec_ligne(db, fid, "2026-06-15", poids_kg=10.0,
                                montant_ht=170.0,  # BL dit 170€ (17€/kg réel)
                                catalogue_fournisseur_id=cat_id)

    res = await _achats_reels_par_reception(db, "2026-06-01", "2026-06-30")
    assert res["nb_source_bl"] == 1
    assert res["ht"] == pytest.approx(170.0)  # le BL prime, pas 10×8=80


@pytest.mark.asyncio
async def test_repli_catalogue_si_aucun_prix_bl(app_client, db):
    from src.api.routes_inventaire import _achats_reels_par_reception
    fid = await _fournisseur(app_client)
    cat_id = await _catalogue(app_client, fid, prix_kg=12.0)
    await _reception_avec_ligne(db, fid, "2026-06-15", poids_kg=5.0,
                                catalogue_fournisseur_id=cat_id)  # aucun prix BL saisi

    res = await _achats_reels_par_reception(db, "2026-06-01", "2026-06-30")
    assert res["nb_source_catalogue"] == 1
    assert res["ht"] == pytest.approx(60.0)  # 5 × 12


@pytest.mark.asyncio
async def test_anomalie_signalee_si_aucune_facture(app_client, db):
    """Réception sans AUCUNE facture (ni même brouillon) = anomalie
    opérationnelle signalée, mais le montant reste compté (jamais un trou)."""
    from src.api.routes_inventaire import _achats_reels_par_reception
    fid = await _fournisseur(app_client, "Fournisseur Anomalie")
    rec = await _reception_avec_ligne(db, fid, "2026-06-15", poids_kg=10.0,
                                      prix_unitaire_ht=20.0)  # pas de facture du tout

    res = await _achats_reels_par_reception(db, "2026-06-01", "2026-06-30")
    assert res["ht"] == pytest.approx(200.0)  # comptée quand même (10×20)
    assert len(res["anomalies_sans_facture"]) == 1
    assert res["anomalies_sans_facture"][0]["reception_id"] == rec
    assert res["anomalies_sans_facture"][0]["fournisseur_nom"] == "Fournisseur Anomalie"


@pytest.mark.asyncio
async def test_avoir_non_lie_a_une_reception_nest_pas_compte_deux_fois(app_client, db):
    """Un avoir (facture_liee_id) n'a pas sa propre reception_id : le calcul par
    réception ne le voit pas séparément (il n'a pas de ligne reception_lignes),
    donc pas de double comptage — l'avoir devra être géré au niveau facture si
    besoin plus fin, mais n'introduit pas d'erreur ici."""
    from src.api.routes_inventaire import _achats_reels_par_reception
    fid = await _fournisseur(app_client)
    rec = await _reception_avec_ligne(db, fid, "2026-06-10", poids_kg=10.0)
    fac_id = await _facture(app_client, fid, rec, 500.0, statut="validee")
    # Avoir lié, sans reception_id propre.
    r = await app_client.post("/api/achats/factures", json={
        "fournisseur_id": fid, "type": "avoir", "facture_liee_id": fac_id,
        "lignes": [{"designation": "Retour", "type_ligne": "marchandise",
                    "tva_pct": 5.5, "montant_facture_ht": 80.0}],
    })
    avoir_id = r.json()["id"]
    await app_client.put(f"/api/achats/factures/{avoir_id}",
                         json={"numero_facture": "AV-1", "statut": "validee"})

    res = await _achats_reels_par_reception(db, "2026-06-01", "2026-06-30")
    # Une seule réception → une seule contribution (celle de la facture d'origine).
    assert res["nb_receptions"] == 1
    assert res["ht"] == pytest.approx(500.0)


@pytest.mark.asyncio
async def test_filtre_sur_date_reception(app_client, db):
    from src.api.routes_inventaire import _achats_reels_par_reception
    fid = await _fournisseur(app_client)
    rec_juin = await _reception_avec_ligne(db, fid, "2026-06-15", poids_kg=5.0)
    await _facture(app_client, fid, rec_juin, 100.0, statut="validee")
    rec_juillet = await _reception_avec_ligne(db, fid, "2026-07-05", poids_kg=5.0)
    await _facture(app_client, fid, rec_juillet, 200.0, statut="validee")

    res_juin = await _achats_reels_par_reception(db, "2026-06-01", "2026-06-30")
    assert res_juin["ht"] == pytest.approx(100.0)
    res_juillet = await _achats_reels_par_reception(db, "2026-07-01", "2026-07-31")
    assert res_juillet["ht"] == pytest.approx(200.0)


@pytest.mark.asyncio
async def test_tableau_marge_source_par_reception(app_client, db):
    fid = await _fournisseur(app_client)
    rec = await _reception_avec_ligne(db, fid, "2026-06-15", poids_kg=10.0)
    await _facture(app_client, fid, rec, 300.0, statut="validee")

    r = await app_client.get(
        "/api/inventaire/marge?date_debut=2026-06-01&date_fin=2026-06-30")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["achats"]["source"] == "par_reception"
    assert data["achats"]["ht"] == pytest.approx(300.0)
    assert data["achats"]["nb_source_facture"] == 1
    assert data["achats"]["ht_calcule"] is not None


@pytest.mark.asyncio
async def test_tableau_marge_repli_calcule_sans_reception(app_client, db):
    r = await app_client.get(
        "/api/inventaire/marge?date_debut=2026-01-01&date_fin=2026-01-31")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["achats"]["source"] == "calcule"


@pytest.mark.asyncio
async def test_saisie_manuelle_prime_volontairement(app_client, db):
    """La saisie manuelle est un OVERRIDE explicite : elle prime même si le
    calcul par réception a des données (décision assumée par un clic)."""
    fid = await _fournisseur(app_client)
    rec = await _reception_avec_ligne(db, fid, "2026-03-15", poids_kg=10.0)
    await _facture(app_client, fid, rec, 222.0, statut="validee")

    body = {"date_debut": "2026-03-01", "date_fin": "2026-03-31", "montant_ht": 999.0}
    await app_client.put("/api/inventaire/marge/achats-reels", json=body)

    r = await app_client.get(
        "/api/inventaire/marge?date_debut=2026-03-01&date_fin=2026-03-31")
    data = r.json()
    assert data["achats"]["source"] == "reel"
    assert data["achats"]["ht"] == pytest.approx(999.0)
    # Le calcul par réception reste visible en référence.
    assert data["achats"]["ht_par_reception"] == pytest.approx(222.0)

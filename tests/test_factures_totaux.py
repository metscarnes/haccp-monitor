"""
test_factures_totaux.py — Synthèse GET /factures/totaux (HT/TTC global + par
fournisseur, filtrable par période sur date_facture).

Règles testées :
- Global HT = somme montant_total_ht_facture des factures (hors annulées).
- Un avoir compte en NÉGATIF (réduit le montant dû à ce fournisseur).
- Filtre date_debut/date_fin sur date_facture (bornes incluses).
- Regroupement par fournisseur, trié par HT décroissant.
- Les factures annulées sont exclues par défaut, incluses via ?statut=annulee.
- TTC : utilise total_ttc_papier si renseigné, sinon calcule via TVA des lignes.
"""
import pytest


async def _fournisseur(client, nom):
    r = await client.post("/api/achats/fournisseurs", json={"nom": nom})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _facture(client, fournisseur_id, *, date_facture, montant_ht, tva_pct=5.5,
                    type_doc="facture", total_ttc_papier=None, statut=None):
    r = await client.post("/api/achats/factures", json={
        "fournisseur_id": fournisseur_id,
        "date_facture": date_facture,
        "type": type_doc,
        "lignes": [{
            "designation": "Article test", "type_ligne": "marchandise",
            "tva_pct": tva_pct, "montant_facture_ht": montant_ht,
        }],
    })
    assert r.status_code == 201, r.text
    fac_id = r.json()["id"]
    if total_ttc_papier is not None or statut is not None:
        body = {}
        if total_ttc_papier is not None:
            body["total_ttc_papier"] = total_ttc_papier
        if statut is not None:
            body["numero_facture"] = f"FA-{fac_id}"
            body["statut"] = statut
        r2 = await client.put(f"/api/achats/factures/{fac_id}", json=body)
        assert r2.status_code == 200, r2.text
    return fac_id


@pytest.mark.asyncio
async def test_global_et_par_fournisseur(app_client, db):
    f1 = await _fournisseur(app_client, "Fournisseur A")
    f2 = await _fournisseur(app_client, "Fournisseur B")
    await _facture(app_client, f1, date_facture="2026-06-10", montant_ht=100.0)
    await _facture(app_client, f1, date_facture="2026-06-15", montant_ht=50.0)
    await _facture(app_client, f2, date_facture="2026-06-12", montant_ht=200.0)

    r = await app_client.get("/api/achats/factures/totaux")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["nb_factures"] == 3
    assert data["global_ht"] == pytest.approx(350.0)

    par_f = {f["fournisseur_id"]: f for f in data["fournisseurs"]}
    assert par_f[f1]["total_ht"] == pytest.approx(150.0)
    assert par_f[f1]["nb_factures"] == 2
    assert par_f[f2]["total_ht"] == pytest.approx(200.0)
    # Trié HT décroissant : fournisseur B (200) avant A (150)
    assert data["fournisseurs"][0]["fournisseur_id"] == f2


@pytest.mark.asyncio
async def test_avoir_compte_en_negatif(app_client, db):
    f1 = await _fournisseur(app_client, "Fournisseur Avoir")
    await _facture(app_client, f1, date_facture="2026-06-10", montant_ht=300.0)
    await _facture(app_client, f1, date_facture="2026-06-11", montant_ht=50.0,
                   type_doc="avoir")

    r = await app_client.get("/api/achats/factures/totaux")
    data = r.json()
    par_f = {f["fournisseur_id"]: f for f in data["fournisseurs"]}
    assert par_f[f1]["total_ht"] == pytest.approx(250.0)  # 300 - 50


@pytest.mark.asyncio
async def test_filtre_periode(app_client, db):
    f1 = await _fournisseur(app_client, "Fournisseur Periode")
    await _facture(app_client, f1, date_facture="2026-05-30", montant_ht=100.0)
    await _facture(app_client, f1, date_facture="2026-06-15", montant_ht=200.0)
    await _facture(app_client, f1, date_facture="2026-07-01", montant_ht=400.0)

    r = await app_client.get(
        "/api/achats/factures/totaux?date_debut=2026-06-01&date_fin=2026-06-30")
    data = r.json()
    assert data["nb_factures"] == 1
    assert data["global_ht"] == pytest.approx(200.0)


@pytest.mark.asyncio
async def test_facture_annulee_exclue_par_defaut(app_client, db):
    f1 = await _fournisseur(app_client, "Fournisseur Annule")
    await _facture(app_client, f1, date_facture="2026-06-10", montant_ht=100.0)
    fac_doublon = await _facture(app_client, f1, date_facture="2026-06-10", montant_ht=999.0)
    await app_client.post(f"/api/achats/factures/{fac_doublon}/annuler-doublon",
                          json={"motif": "doublon test"})

    r = await app_client.get("/api/achats/factures/totaux")
    data = r.json()
    assert data["global_ht"] == pytest.approx(100.0)  # le doublon 999 est exclu

    r2 = await app_client.get("/api/achats/factures/totaux?statut=annulee")
    assert r2.json()["global_ht"] == pytest.approx(999.0)


@pytest.mark.asyncio
async def test_ttc_papier_prime_sur_calcul(app_client, db):
    f1 = await _fournisseur(app_client, "Fournisseur TTC")
    await _facture(app_client, f1, date_facture="2026-06-10", montant_ht=100.0,
                   tva_pct=20.0, total_ttc_papier=115.0)  # papier dit 115, pas 120

    r = await app_client.get("/api/achats/factures/totaux")
    data = r.json()
    assert data["global_ttc"] == pytest.approx(115.0)


@pytest.mark.asyncio
async def test_ttc_calcule_si_pas_de_papier(app_client, db):
    f1 = await _fournisseur(app_client, "Fournisseur TTC Calc")
    await _facture(app_client, f1, date_facture="2026-06-10", montant_ht=100.0, tva_pct=5.5)

    r = await app_client.get("/api/achats/factures/totaux")
    data = r.json()
    assert data["global_ttc"] == pytest.approx(105.50)

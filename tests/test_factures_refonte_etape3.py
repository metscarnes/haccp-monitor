"""
test_factures_refonte_etape3.py — Refonte facture étape 3 : workflow de validation
verrouillé, correction rapide « solder l'écart », avoir depuis litiges.

Règles testées :
- Valider EXIGE un numéro de facture (anti-doublon + rapprochement compta).
- Facture validée = VERROUILLÉE (lignes, entête, suppression) ; seuls le
  déverrouillage explicite (statut) et le commentaire restent permis.
- brouillon ⇄ rapprochee automatique selon le bouclage (litige/validee intouchés).
- « Solder l'écart » : ligne d'ajustement traçable = reste à expliquer HT,
  jamais d'écrasement ; exige le Total HT papier ; refuse si ça boucle déjà.
- Avoir depuis litiges : document séparé lié, une ligne par litige (écart > 0),
  un seul avoir par facture.
"""
import pytest

from test_factures_refonte_etape0 import _setup


async def _facture_kg(client, db):
    """Facture standard : 9,4 kg × 12 €/kg = 112,80 € marchandise, écarts nuls.
    TTC calculé = 112,80 + 5,5 % (6,20) = 119,00."""
    ids = await _setup(client, db)
    r = await client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    assert r.status_code == 201, r.text
    return ids, r.json()


# ─── Validation / verrouillage ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_valider_exige_numero(app_client, db):
    ids, fac = await _facture_kg(app_client, db)

    r = await app_client.put(f"/api/achats/factures/{fac['id']}", json={"statut": "validee"})
    assert r.status_code == 400, r.text
    assert "uméro" in r.json()["detail"]

    r = await app_client.put(f"/api/achats/factures/{fac['id']}",
                             json={"numero_facture": "FA-100", "statut": "validee"})
    assert r.status_code == 200, r.text
    assert r.json()["statut"] == "validee"


@pytest.mark.asyncio
async def test_statut_invalide_refuse(app_client, db):
    ids, fac = await _facture_kg(app_client, db)
    r = await app_client.put(f"/api/achats/factures/{fac['id']}", json={"statut": "payee"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_facture_validee_verrouillee(app_client, db):
    ids, fac = await _facture_kg(app_client, db)
    lid = fac["lignes"][0]["id"]
    await app_client.put(f"/api/achats/factures/{fac['id']}",
                         json={"numero_facture": "FA-101", "statut": "validee"})

    # Modifs bloquées (409) : ligne, ajout, suppression ligne, entête, suppression facture
    r = await app_client.put(f"/api/achats/factures/{fac['id']}/lignes/{lid}",
                             json={"prix_facture_ht": 13.0})
    assert r.status_code == 409, r.text
    r = await app_client.post(f"/api/achats/factures/{fac['id']}/lignes",
                              json={"designation": "Transport", "type_ligne": "transport",
                                    "montant_facture_ht": 5.0})
    assert r.status_code == 409
    r = await app_client.delete(f"/api/achats/factures/{fac['id']}/lignes/{lid}")
    assert r.status_code == 409
    r = await app_client.put(f"/api/achats/factures/{fac['id']}",
                             json={"date_facture": "2026-07-01"})
    assert r.status_code == 409
    r = await app_client.delete(f"/api/achats/factures/{fac['id']}")
    assert r.status_code == 409

    # Le commentaire reste permis (note interne, ne touche pas aux montants)
    r = await app_client.put(f"/api/achats/factures/{fac['id']}",
                             json={"commentaire": "Payée le 15/07"})
    assert r.status_code == 200, r.text

    # Déverrouillage EXPLICITE → modifications de nouveau possibles
    r = await app_client.put(f"/api/achats/factures/{fac['id']}", json={"statut": "brouillon"})
    assert r.status_code == 200, r.text
    r = await app_client.put(f"/api/achats/factures/{fac['id']}/lignes/{lid}",
                             json={"prix_facture_ht": 13.0})
    assert r.status_code == 200, r.text


# ─── Statut rapprochée automatique ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_statut_rapprochee_automatique(app_client, db):
    """La facture passe en 'rapprochee' quand elle boucle, redevient 'brouillon'
    quand le bouclage casse."""
    ids, fac = await _facture_kg(app_client, db)
    assert fac["statut"] == "brouillon"

    # TTC papier = TTC calculé (119,00) → boucle → rapprochee
    r = await app_client.put(f"/api/achats/factures/{fac['id']}",
                             json={"total_ttc_papier": 119.00})
    fac2 = r.json()
    assert fac2["recap"]["boucle"] is True
    assert fac2["statut"] == "rapprochee"

    # TTC papier différent → ne boucle plus → retour brouillon
    r = await app_client.put(f"/api/achats/factures/{fac['id']}",
                             json={"total_ttc_papier": 125.00})
    assert r.json()["statut"] == "brouillon"

    # Une modification de ligne qui refait boucler → de nouveau rapprochee
    lid = fac["lignes"][0]["id"]
    await app_client.put(f"/api/achats/factures/{fac['id']}",
                         json={"total_ttc_papier": 119.00})
    r = await app_client.put(f"/api/achats/factures/{fac['id']}/lignes/{lid}",
                             json={"poids_facture_kg": 9.4})
    r2 = await app_client.get(f"/api/achats/factures/{fac['id']}")
    assert r2.json()["statut"] == "rapprochee"


# ─── Solder l'écart ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_solder_ecart(app_client, db):
    """HT papier 118,00 vs calculé 112,80 → ligne d'ajustement +5,20, la facture
    boucle, tout est traçable (rien d'écrasé)."""
    ids, fac = await _facture_kg(app_client, db)

    # Sans total HT papier → refus explicite
    r = await app_client.post(f"/api/achats/factures/{fac['id']}/solder-ecart")
    assert r.status_code == 400, r.text

    await app_client.put(f"/api/achats/factures/{fac['id']}",
                         json={"total_ht_papier": 118.00})
    r = await app_client.post(f"/api/achats/factures/{fac['id']}/solder-ecart")
    assert r.status_code == 201, r.text
    res = r.json()
    assert res["montant_solde_ht"] == pytest.approx(5.20)
    assert res["ligne"]["type_ligne"] == "ajustement"
    assert res["ligne"]["montant_facture_ht"] == pytest.approx(5.20)

    fac2 = (await app_client.get(f"/api/achats/factures/{fac['id']}")).json()
    assert fac2["montant_total_ht_facture"] == pytest.approx(118.00)
    assert fac2["recap"]["reste_a_expliquer_ht"] == pytest.approx(0.0)
    assert fac2["recap"]["boucle"] is True
    assert fac2["statut"] == "rapprochee"       # bascule auto
    assert fac2["ecart_total_ht"] == pytest.approx(0.0)  # marchandise non polluée

    # Ça boucle déjà → rien à solder
    r = await app_client.post(f"/api/achats/factures/{fac['id']}/solder-ecart")
    assert r.status_code == 400

    # Verrouillée → 409
    await app_client.put(f"/api/achats/factures/{fac['id']}",
                         json={"numero_facture": "FA-102", "statut": "validee"})
    await app_client.put(f"/api/achats/factures/{fac['id']}", json={"statut": "brouillon"})
    await app_client.put(f"/api/achats/factures/{fac['id']}",
                         json={"total_ht_papier": 130.00, "numero_facture": "FA-102",
                               "statut": "validee"})
    r = await app_client.post(f"/api/achats/factures/{fac['id']}/solder-ecart")
    assert r.status_code == 409


# ─── Avoir depuis litiges ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_avoir_depuis_litiges(app_client, db):
    ids, fac = await _facture_kg(app_client, db)
    lid = fac["lignes"][0]["id"]

    # Aucun litige → refus
    r = await app_client.post(f"/api/achats/factures/{fac['id']}/avoir-depuis-litiges")
    assert r.status_code == 400

    # Litige : facturé 10 kg au lieu de 9,4 pesés → écart +7,20 €
    await app_client.put(f"/api/achats/factures/{fac['id']}/lignes/{lid}",
                         json={"poids_facture_kg": 10.0, "statut_ligne": "litige",
                               "commentaire_litige": "Poids facturé > pesé"})

    r = await app_client.post(f"/api/achats/factures/{fac['id']}/avoir-depuis-litiges")
    assert r.status_code == 201, r.text
    avoir = r.json()
    assert avoir["type"] == "avoir"
    assert avoir["facture_liee_id"] == fac["id"]
    assert avoir["statut"] == "brouillon"
    assert len(avoir["lignes"]) == 1
    assert avoir["lignes"][0]["montant_facture_ht"] == pytest.approx(7.20)
    assert "écart litige" in avoir["lignes"][0]["designation"]
    assert avoir["montant_total_ht_facture"] == pytest.approx(7.20)

    # Un seul avoir par facture
    r = await app_client.post(f"/api/achats/factures/{fac['id']}/avoir-depuis-litiges")
    assert r.status_code == 409

    # Pas d'avoir sur un avoir
    r = await app_client.post(f"/api/achats/factures/{avoir['id']}/avoir-depuis-litiges")
    assert r.status_code == 400

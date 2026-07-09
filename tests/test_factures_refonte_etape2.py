"""
test_factures_refonte_etape2.py — Refonte facture étape 2 : lignes annexes,
TVA par taux, bouclage « reste à expliquer », avoir.

Règles testées :
- Une ligne ANNEXE (transport/taxe/consigne/remise/ajustement) compte dans le
  total facturé (bouclage) mais PAS dans l'attendu ni l'écart marchandise.
- Remise = montant négatif.
- Récap TVA PAR TAUX sur la base cumulée du taux (pas ligne à ligne), TTC calculé.
- Bouclage : total papier (HT/TTC) saisi → reste à expliquer ; boucle si ≤ 0,05 €.
- Avoir = document séparé (type='avoir', facture_liee_id), jamais une facture modifiée.
- Suggestions d'annexes habituelles par fournisseur.
"""
import pytest

from test_factures_refonte_etape0 import _setup


async def _facture_kg(client, db):
    """Facture standard 9,4 kg × 12 €/kg = 112,80 € marchandise (écarts nuls)."""
    ids = await _setup(client, db)
    r = await client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    assert r.status_code == 201, r.text
    return ids, r.json()


@pytest.mark.asyncio
async def test_ligne_annexe_hors_rapprochement(app_client, db):
    """Transport 12 € : total facturé l'inclut, attendu/écart marchandise NON."""
    ids, fac = await _facture_kg(app_client, db)

    r = await app_client.post(f"/api/achats/factures/{fac['id']}/lignes", json={
        "designation": "Frais de transport",
        "type_ligne": "transport",
        "montant_facture_ht": 12.0,
        "tva_pct": 20.0,
    })
    assert r.status_code == 201, r.text
    annexe = r.json()
    assert annexe["type_ligne"] == "transport"
    assert annexe["montant_facture_ht"] == pytest.approx(12.0)
    assert annexe["ecart_montant_ht"] == 0.0  # pas de rapprochement sur une annexe

    fac2 = (await app_client.get(f"/api/achats/factures/{fac['id']}")).json()
    assert fac2["montant_total_ht_facture"] == pytest.approx(124.80)  # 112,80 + 12
    assert fac2["montant_total_ht_attendu"] == pytest.approx(112.80)  # marchandise seule
    assert fac2["ecart_total_ht"] == pytest.approx(0.0)               # rapprochement pur
    assert fac2["recap"]["marchandise_ht"] == pytest.approx(112.80)
    assert fac2["recap"]["annexes_ht"] == pytest.approx(12.0)
    assert fac2["recap"]["annexes_par_type"]["transport"] == pytest.approx(12.0)


@pytest.mark.asyncio
async def test_remise_negative(app_client, db):
    """Remise −5 € : total facturé baisse, écart marchandise inchangé."""
    ids, fac = await _facture_kg(app_client, db)
    r = await app_client.post(f"/api/achats/factures/{fac['id']}/lignes", json={
        "designation": "Remise commerciale",
        "type_ligne": "remise",
        "montant_facture_ht": -5.0,
        "tva_pct": 5.5,
    })
    assert r.status_code == 201, r.text
    fac2 = (await app_client.get(f"/api/achats/factures/{fac['id']}")).json()
    assert fac2["montant_total_ht_facture"] == pytest.approx(107.80)
    assert fac2["ecart_total_ht"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_recap_tva_par_taux_et_ttc(app_client, db):
    """TVA calculée PAR TAUX sur la base cumulée : marchandise 5,5 % + transport 20 %.
    112,80 × 5,5 % = 6,204 → 6,20 ; 12 × 20 % = 2,40 ; TTC = 124,80 + 8,60 = 133,40."""
    ids, fac = await _facture_kg(app_client, db)
    await app_client.post(f"/api/achats/factures/{fac['id']}/lignes", json={
        "designation": "Transport", "type_ligne": "transport",
        "montant_facture_ht": 12.0, "tva_pct": 20.0,
    })
    recap = (await app_client.get(f"/api/achats/factures/{fac['id']}")).json()["recap"]

    par_taux = {t["taux"]: t for t in recap["tva_par_taux"]}
    assert par_taux[5.5]["base_ht"] == pytest.approx(112.80)
    assert par_taux[5.5]["tva"] == pytest.approx(6.20)     # 6,204 arrondi commercial
    assert par_taux[20.0]["base_ht"] == pytest.approx(12.0)
    assert par_taux[20.0]["tva"] == pytest.approx(2.40)
    assert recap["total_tva"] == pytest.approx(8.60)
    assert recap["total_ttc_calcule"] == pytest.approx(133.40)
    assert recap["nb_lignes_sans_tva"] == 0  # génération = TVA 5,5 par défaut


@pytest.mark.asyncio
async def test_bouclage_reste_a_expliquer(app_client, db):
    """Saisie du TTC papier → reste à expliquer ; boucle si ≤ 0,05 €, effaçable."""
    ids, fac = await _facture_kg(app_client, db)
    await app_client.post(f"/api/achats/factures/{fac['id']}/lignes", json={
        "designation": "Transport", "type_ligne": "transport",
        "montant_facture_ht": 12.0, "tva_pct": 20.0,
    })

    # TTC papier = TTC calculé (133,40) → ça boucle
    r = await app_client.put(f"/api/achats/factures/{fac['id']}",
                             json={"total_ttc_papier": 133.40})
    recap = r.json()["recap"]
    assert recap["reste_a_expliquer_ttc"] == pytest.approx(0.0)
    assert recap["boucle"] is True

    # TTC papier = 140 → 6,60 € à expliquer, ne boucle pas
    r = await app_client.put(f"/api/achats/factures/{fac['id']}",
                             json={"total_ttc_papier": 140.0})
    recap = r.json()["recap"]
    assert recap["reste_a_expliquer_ttc"] == pytest.approx(6.60)
    assert recap["boucle"] is False

    # Écart d'un centime (arrondi fournisseur) → boucle quand même (tolérance 0,05)
    r = await app_client.put(f"/api/achats/factures/{fac['id']}",
                             json={"total_ttc_papier": 133.41})
    assert r.json()["recap"]["boucle"] is True

    # Effacement (null explicite) → plus de bouclage évalué
    r = await app_client.put(f"/api/achats/factures/{fac['id']}",
                             json={"total_ttc_papier": None})
    assert r.status_code == 200, r.text
    recap = r.json()["recap"]
    assert recap["total_ttc_papier"] is None
    assert recap["boucle"] is None


@pytest.mark.asyncio
async def test_annexe_montant_modifiable_ecarts_restent_nuls(app_client, db):
    """Modifier le montant d'une annexe le conserve tel quel (arrondi), écarts nuls,
    et ne pollue pas l'écart marchandise de l'entête."""
    ids, fac = await _facture_kg(app_client, db)
    annexe = (await app_client.post(f"/api/achats/factures/{fac['id']}/lignes", json={
        "designation": "Consigne", "type_ligne": "consigne", "montant_facture_ht": 3.0,
    })).json()
    assert annexe["tva_pct"] == 20.0  # défaut annexe

    r = await app_client.put(
        f"/api/achats/factures/{fac['id']}/lignes/{annexe['id']}",
        json={"montant_facture_ht": 4.567},
    )
    assert r.status_code == 200, r.text
    ligne = r.json()
    assert ligne["montant_facture_ht"] == pytest.approx(4.57)  # arrondi commercial
    assert ligne["ecart_montant_ht"] == 0.0

    fac2 = (await app_client.get(f"/api/achats/factures/{fac['id']}")).json()
    assert fac2["ecart_total_ht"] == pytest.approx(0.0)
    assert fac2["montant_total_ht_facture"] == pytest.approx(112.80 + 4.57)


@pytest.mark.asyncio
async def test_annexes_frequentes_par_fournisseur(app_client, db):
    """Les annexes récurrentes d'un fournisseur remontent en suggestion (dernier montant)."""
    ids, fac = await _facture_kg(app_client, db)
    await app_client.post(f"/api/achats/factures/{fac['id']}/lignes", json={
        "designation": "Taxe équarrissage", "type_ligne": "taxe",
        "montant_facture_ht": 2.50, "tva_pct": 20.0,
    })
    # Une seconde facture (manuelle) du même fournisseur avec la même taxe, autre montant
    fac2 = (await app_client.post("/api/achats/factures", json={
        "fournisseur_id": ids["fournisseur_id"],
        "lignes": [{"designation": "Taxe équarrissage", "type_ligne": "taxe",
                    "montant_facture_ht": 2.80, "tva_pct": 20.0}],
    })).json()

    r = await app_client.get(
        f"/api/achats/factures/annexes-frequentes?fournisseur_id={ids['fournisseur_id']}"
    )
    assert r.status_code == 200, r.text
    sugg = r.json()
    taxe = next(s for s in sugg if s["designation"] == "Taxe équarrissage")
    assert taxe["type_ligne"] == "taxe"
    assert taxe["occurrences"] == 2
    assert taxe["dernier_montant_ht"] == pytest.approx(2.80)


@pytest.mark.asyncio
async def test_avoir_document_separe(app_client, db):
    """Un avoir est un document distinct rattaché à sa facture d'origine."""
    ids, fac = await _facture_kg(app_client, db)

    r = await app_client.post("/api/achats/factures", json={
        "fournisseur_id": ids["fournisseur_id"],
        "type": "avoir",
        "facture_liee_id": fac["id"],
        "numero_facture": "AV-2026-001",
        "lignes": [{"designation": "Avoir écart poids", "type_ligne": "ajustement",
                    "montant_facture_ht": 7.20, "tva_pct": 5.5}],
    })
    assert r.status_code == 201, r.text
    avoir = r.json()
    assert avoir["type"] == "avoir"
    assert avoir["facture_liee_id"] == fac["id"]
    assert avoir["montant_total_ht_facture"] == pytest.approx(7.20)

    # Type invalide → 422 ; facture liée inexistante → 404
    r = await app_client.post("/api/achats/factures", json={
        "fournisseur_id": ids["fournisseur_id"], "type": "note_de_credit", "lignes": [],
    })
    assert r.status_code == 422
    r = await app_client.post("/api/achats/factures", json={
        "fournisseur_id": ids["fournisseur_id"], "type": "avoir",
        "facture_liee_id": 999999, "lignes": [],
    })
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_type_ligne_invalide_refuse(app_client, db):
    ids, fac = await _facture_kg(app_client, db)
    r = await app_client.post(f"/api/achats/factures/{fac['id']}/lignes", json={
        "designation": "N'importe quoi", "type_ligne": "cadeau", "montant_facture_ht": 1.0,
    })
    assert r.status_code == 422

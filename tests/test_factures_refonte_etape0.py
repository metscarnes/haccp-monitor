"""
test_factures_refonte_etape0.py — Refonte facture : unités, arrondis, anti-doublon.

Écrits à l'étape 0 en xfail(strict) pour CARACTÉRISER les défauts (D1 unités,
D2 arrondis, A3 doublons), ces tests sont devenus les tests d'ACCEPTATION de
l'étape 1 (marqueurs retirés une fois le comportement cible implémenté) :

  D1  montant d'un article facturé au colis/pièce = quantité × prix (pas poids × prix)
  D2  montants arrondis commercialement à 2 décimales (ROUND_HALF_UP)
  A3  doublon (fournisseur, numéro de facture) refusé (409)

Les comportements SAINS pré-existants (kg, montant saisi tel quel, réception
figée, totaux) restent figés par tests/test_factures.py (baseline golden).
"""
import pytest


async def _setup(client, db, *, format_prix="kg", prix=12.0, quantite=10.0,
                 unite="kg", poids_recu=9.4, poids_colis_kg=None, nb_colis=None):
    """Fournisseur + article catalogue + commande 1 ligne + réception + mapping."""
    r = await client.post("/api/achats/fournisseurs", json={"nom": "Bourdicaud"})
    assert r.status_code == 201, r.text
    fournisseur_id = r.json()["id"]

    payload_cat = {
        "fournisseur_id": fournisseur_id,
        "code_article": "ART01",
        "designation": "Article refonte",
        "prix_achat_ht": prix,
        "format_prix": format_prix,
    }
    if poids_colis_kg is not None:
        payload_cat["poids_colis_kg"] = poids_colis_kg
    r = await client.post("/api/achats/catalogue", json=payload_cat)
    assert r.status_code == 201, r.text
    cat_id = r.json()["id"]

    await db.execute(
        "INSERT OR IGNORE INTO personnel (id, boutique_id, prenom, actif) VALUES (1, 1, 'Test', 1)"
    )
    await db.commit()

    r = await client.post("/api/achats/commandes", json={
        "fournisseur_id": fournisseur_id,
        "lignes": [{
            "catalogue_fournisseur_id": cat_id,
            "code_article": "ART01",
            "designation": "Article refonte",
            "prix_unitaire_ht": prix,
            "quantite_commandee": quantite,
            "unite": unite,
        }],
    })
    assert r.status_code == 201, r.text
    commande_id = r.json()["id"]

    cur = await db.execute(
        """INSERT INTO receptions (personnel_id, heure_reception, fournisseur_principal_id, statut)
           VALUES (1, '08:00', ?, 'cloturee')""",
        (fournisseur_id,),
    )
    await db.commit()
    reception_id = cur.lastrowid
    await db.execute(
        """INSERT INTO reception_lignes (reception_id, catalogue_fournisseur_id, poids_kg,
                                         nb_colis, statut)
           VALUES (?, ?, ?, ?, 'complet')""",
        (reception_id, cat_id, poids_recu, nb_colis),
    )
    await db.commit()

    r = await client.post("/api/achats/commande_receptions_mapping", json={
        "commande_id": commande_id, "reception_id": reception_id,
    })
    assert r.status_code == 201, r.text
    return {"fournisseur_id": fournisseur_id, "cat_id": cat_id,
            "commande_id": commande_id, "reception_id": reception_id}


# ─── D1 : unités ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_montant_article_au_colis(app_client, db):
    """3 colis de saucisses à 45 € HT le colis (colis de 5,2 kg, pesée 15,6 kg).
    Montant facture attendu : 3 × 45 = 135,00 € — PAS 15,6 × 45 = 702 €."""
    ids = await _setup(app_client, db, format_prix="colis", prix=45.0,
                       quantite=3.0, unite="colis", poids_recu=15.6,
                       poids_colis_kg=5.2)
    r = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    assert r.status_code == 201, r.text
    fac = r.json()
    ligne = fac["lignes"][0]
    assert ligne["unite_prix"] == "colis"
    assert ligne["quantite_facturee"] == 3.0
    assert ligne["montant_facture_ht"] == pytest.approx(135.00, abs=0.005)
    r = await app_client.get(f"/api/achats/factures/{fac['id']}")
    assert r.json()["montant_total_ht_facture"] == pytest.approx(135.00, abs=0.005)


@pytest.mark.asyncio
async def test_montant_article_a_la_piece(app_client, db):
    """12 poulets à 8,50 € HT pièce (14,4 kg pesés).
    Montant attendu : 12 × 8,50 = 102,00 € — PAS 14,4 × 8,50 = 122,40 €."""
    ids = await _setup(app_client, db, format_prix="piece", prix=8.50,
                       quantite=12.0, unite="piece", poids_recu=14.4)
    r = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    assert r.status_code == 201, r.text
    ligne = r.json()["lignes"][0]
    assert ligne["unite_prix"] == "piece"
    assert ligne["montant_facture_ht"] == pytest.approx(102.00, abs=0.005)


@pytest.mark.asyncio
async def test_nb_colis_reception_prioritaire_sur_commande(app_client, db):
    """Le nb de colis POINTÉ à la réception (4) prime sur la quantité commandée (3) :
    c'est ce qui a été livré que le fournisseur facture. Montant = 4 × 45 = 180 €."""
    ids = await _setup(app_client, db, format_prix="colis", prix=45.0,
                       quantite=3.0, unite="colis", poids_recu=20.8, nb_colis=4)
    r = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    assert r.status_code == 201, r.text
    ligne = r.json()["lignes"][0]
    assert ligne["quantite_facturee"] == 4.0
    assert ligne["montant_facture_ht"] == pytest.approx(180.00, abs=0.005)
    # Écart montant = facturé (4×45=180) − attendu commande (3×45=135) = +45
    assert ligne["ecart_montant_ht"] == pytest.approx(45.00, abs=0.005)


@pytest.mark.asyncio
async def test_saisie_quantite_facturee_recalcule_montant(app_client, db):
    """Corriger la quantité facturée d'une ligne au colis recalcule le montant
    (qté × prix), sans toucher au poids HACCP."""
    ids = await _setup(app_client, db, format_prix="colis", prix=45.0,
                       quantite=3.0, unite="colis", poids_recu=15.6)
    fac = (await app_client.post(
        f"/api/achats/factures/depuis-reception/{ids['reception_id']}")).json()
    lid = fac["lignes"][0]["id"]

    r = await app_client.put(f"/api/achats/factures/{fac['id']}/lignes/{lid}",
                             json={"quantite_facturee": 5.0})
    assert r.status_code == 200, r.text
    ligne = r.json()
    assert ligne["montant_facture_ht"] == pytest.approx(225.00, abs=0.005)  # 5 × 45
    assert ligne["poids_facture_kg"] == 15.6  # poids inchangé (affichage/HACCP)


@pytest.mark.asyncio
async def test_montant_direct_sur_ligne_piece_recale_prix_unitaire(app_client, db):
    """Montant saisi tel quel sur une ligne à la pièce : conservé, et le prix
    unitaire est recalé montant / quantité (pas montant / poids)."""
    ids = await _setup(app_client, db, format_prix="piece", prix=8.50,
                       quantite=12.0, unite="piece", poids_recu=14.4)
    fac = (await app_client.post(
        f"/api/achats/factures/depuis-reception/{ids['reception_id']}")).json()
    lid = fac["lignes"][0]["id"]

    r = await app_client.put(f"/api/achats/factures/{fac['id']}/lignes/{lid}",
                             json={"montant_facture_ht": 108.0})
    assert r.status_code == 200, r.text
    ligne = r.json()
    assert ligne["montant_facture_ht"] == pytest.approx(108.00, abs=0.005)
    assert ligne["prix_facture_ht"] == pytest.approx(108.0 / 12.0, abs=1e-9)  # 9 €/pièce


# ─── D2 : arrondis ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_montant_ligne_arrondi_2_decimales(app_client, db):
    """3,333 kg × 11,87 €/kg = 39,562710 → le montant stocké doit être 39,56
    exactement (comme sur la facture papier), pas un float à 6 décimales."""
    ids = await _setup(app_client, db, prix=11.87, quantite=3.333, poids_recu=3.333)
    r = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    assert r.status_code == 201, r.text
    fac = r.json()
    ligne = fac["lignes"][0]
    montant = ligne["montant_facture_ht"]
    # Exactement 2 décimales, valeur commerciale
    assert montant == round(montant, 2), f"montant non arrondi : {montant!r}"
    assert montant == pytest.approx(39.56, abs=1e-9)
    # Total entête = somme des lignes ARRONDIES (pas des floats bruts)
    r = await app_client.get(f"/api/achats/factures/{fac['id']}")
    total = r.json()["montant_total_ht_facture"]
    assert total == round(total, 2), f"total non arrondi : {total!r}"


@pytest.mark.asyncio
async def test_arrondi_commercial_half_up():
    """L'arrondi est commercial (2,675 → 2,68), pas bancaire comme round() (→ 2,67)."""
    from src.api.routes_achats import _arrondi_commercial
    assert _arrondi_commercial(2.675) == 2.68
    assert _arrondi_commercial(2.665) == 2.67  # half-up sur le chiffre suivant
    assert _arrondi_commercial(39.56271) == 39.56
    assert _arrondi_commercial(None) is None


# ─── A3 : anti-doublon numéro de facture ────────────────────────────────────

@pytest.mark.asyncio
async def test_doublon_numero_facture_refuse(app_client, db):
    """Deux factures du même fournisseur ne peuvent pas porter le même numéro."""
    ids = await _setup(app_client, db)
    fac1 = (await app_client.post(
        f"/api/achats/factures/depuis-reception/{ids['reception_id']}")).json()
    r = await app_client.put(f"/api/achats/factures/{fac1['id']}",
                             json={"numero_facture": "FA-2026-0042"})
    assert r.status_code == 200, r.text

    # Seconde facture (manuelle) du même fournisseur, même numéro → refusée
    r2 = await app_client.post("/api/achats/factures", json={
        "fournisseur_id": ids["fournisseur_id"],
        "numero_facture": "FA-2026-0042",
        "lignes": [],
    })
    assert r2.status_code == 409, (
        f"Doublon accepté (status {r2.status_code}) : "
        "risque de double comptabilisation/paiement"
    )

    # Re-sauver la MÊME facture avec son propre numéro reste possible (exclure_id)
    r3 = await app_client.put(f"/api/achats/factures/{fac1['id']}",
                              json={"numero_facture": "FA-2026-0042"})
    assert r3.status_code == 200, r3.text

    # Le même numéro chez un AUTRE fournisseur est légitime
    r4 = await app_client.post("/api/achats/fournisseurs", json={"nom": "AutreFournisseur"})
    autre_fid = r4.json()["id"]
    r5 = await app_client.post("/api/achats/factures", json={
        "fournisseur_id": autre_fid,
        "numero_facture": "FA-2026-0042",
        "lignes": [],
    })
    assert r5.status_code == 201, r5.text

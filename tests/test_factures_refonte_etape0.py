"""
test_factures_refonte_etape0.py — Caractérisation des défauts AVANT refonte facture.

Étape 0 de la refonte : chaque test xfail(strict=True) documente un défaut
diagnostiqué et affirme le comportement CIBLE (celui de l'étape 1). Aujourd'hui
il échoue (xfail = attendu) ; quand l'étape 1 sera codée, il passera et pytest
signalera XPASS strict → on retirera alors le marqueur pour l'ancrer en golden.

Défauts couverts :
  D1  montant d'un article facturé au colis = quantité × prix (pas poids × prix)
  D2  montants arrondis commercialement à 2 décimales (ROUND_HALF_UP)
  A3  doublon (fournisseur, numéro de facture) refusé

Les comportements SAINS (kg, montant saisi tel quel, réception figée, totaux)
sont déjà figés par tests/test_factures.py : ils constituent la baseline golden.
"""
import pytest


async def _setup(client, db, *, format_prix="kg", prix=12.0, quantite=10.0,
                 unite="kg", poids_recu=9.4, poids_colis_kg=None):
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
        """INSERT INTO reception_lignes (reception_id, catalogue_fournisseur_id, poids_kg, statut)
           VALUES (?, ?, ?, 'complet')""",
        (reception_id, cat_id, poids_recu),
    )
    await db.commit()

    r = await client.post("/api/achats/commande_receptions_mapping", json={
        "commande_id": commande_id, "reception_id": reception_id,
    })
    assert r.status_code == 201, r.text
    return {"fournisseur_id": fournisseur_id, "cat_id": cat_id,
            "commande_id": commande_id, "reception_id": reception_id}


# ─── D1 : unités ────────────────────────────────────────────────────────────

@pytest.mark.xfail(
    strict=True,
    reason="D1 (étape 1) : article au COLIS → montant = quantité × prix colis. "
           "Code actuel : poids_kg × prix_colis = montant aberrant.",
)
@pytest.mark.asyncio
async def test_montant_article_au_colis(app_client, db):
    """3 colis de saucisses à 45 € HT le colis (colis de 5,2 kg, pesée 15,6 kg).
    Montant facture attendu : 3 × 45 = 135,00 € — PAS 15,6 × 45 = 702 €."""
    ids = await _setup(app_client, db, format_prix="colis", prix=45.0,
                       quantite=3.0, unite="colis", poids_recu=15.6,
                       poids_colis_kg=5.2)
    r = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    assert r.status_code == 201, r.text
    ligne = r.json()["lignes"][0]
    assert ligne["montant_facture_ht"] == pytest.approx(135.00, abs=0.005)
    r = await app_client.get(f"/api/achats/factures/{r.json()['id']}")
    assert r.json()["montant_total_ht_facture"] == pytest.approx(135.00, abs=0.005)


@pytest.mark.xfail(
    strict=True,
    reason="D1 (étape 1) : article à la PIÈCE → montant = quantité × prix pièce.",
)
@pytest.mark.asyncio
async def test_montant_article_a_la_piece(app_client, db):
    """12 poulets à 8,50 € HT pièce (14,4 kg pesés).
    Montant attendu : 12 × 8,50 = 102,00 € — PAS 14,4 × 8,50 = 122,40 €."""
    ids = await _setup(app_client, db, format_prix="piece", prix=8.50,
                       quantite=12.0, unite="piece", poids_recu=14.4)
    r = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    assert r.status_code == 201, r.text
    ligne = r.json()["lignes"][0]
    assert ligne["montant_facture_ht"] == pytest.approx(102.00, abs=0.005)


# ─── D2 : arrondis ──────────────────────────────────────────────────────────

@pytest.mark.xfail(
    strict=True,
    reason="D2 (étape 1) : montant de ligne arrondi commercialement à 2 décimales "
           "(ROUND_HALF_UP). Code actuel : float brut (39.56271).",
)
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


# ─── A3 : anti-doublon numéro de facture ────────────────────────────────────

@pytest.mark.xfail(
    strict=True,
    reason="A3 (étape 1) : même (fournisseur, numéro de facture) refusé (409) — "
           "contrôle anti-double-paiement standard. Aucun contrôle aujourd'hui.",
)
@pytest.mark.asyncio
async def test_doublon_numero_facture_refuse(app_client, db):
    """Deux factures du même fournisseur ne peuvent pas porter le même numéro."""
    ids = await _setup(app_client, db)
    fac1 = (await app_client.post(
        f"/api/achats/factures/depuis-reception/{ids['reception_id']}")).json()
    r = await app_client.put(f"/api/achats/factures/{fac1['id']}",
                             json={"numero_facture": "FA-2026-0042"})
    assert r.status_code == 200, r.text

    # Seconde facture (manuelle) du même fournisseur, même numéro → doit être refusée
    r2 = await app_client.post("/api/achats/factures", json={
        "fournisseur_id": ids["fournisseur_id"],
        "numero_facture": "FA-2026-0042",
        "lignes": [],
    })
    assert r2.status_code == 409, (
        f"Doublon accepté (status {r2.status_code}) : "
        "risque de double comptabilisation/paiement"
    )

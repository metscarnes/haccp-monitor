"""
test_factures.py — Sous-module Facture (rapprochement commande ↔ réception ↔ facture).

Vérifie : pré-remplissage depuis réception + commande mappée, calcul des écarts
(poids/prix/montant), recalcul à la saisie du facturé, statut litige, et que la
réception n'est jamais modifiée (poids_recu figé).
"""
import pytest


async def _setup_base(client, db):
    """Crée fournisseur, catalogue, commande, réception, mapping. Renvoie les ids."""
    # Fournisseur
    r = await client.post("/api/achats/fournisseurs", json={"nom": "Bourdicaud"})
    assert r.status_code == 201, r.text
    fournisseur_id = r.json()["id"]

    # Article catalogue
    r = await client.post("/api/achats/catalogue", json={
        "fournisseur_id": fournisseur_id,
        "code_article": "BOEUF01",
        "designation": "Faux-filet boeuf",
        "prix_achat_ht": 12.0,
    })
    assert r.status_code == 201, r.text
    cat_id = r.json()["id"]

    # Personnel (pour réception) — idempotent : app_client est session-scoped,
    # les inserts via l'API persistent entre tests alors que db repart à vide.
    await db.execute(
        "INSERT OR IGNORE INTO personnel (id, boutique_id, prenom, actif) VALUES (1, 1, 'Test', 1)"
    )
    await db.commit()

    # Commande avec 1 ligne : 10 kg à 12 €/kg
    r = await client.post("/api/achats/commandes", json={
        "fournisseur_id": fournisseur_id,
        "lignes": [{
            "catalogue_fournisseur_id": cat_id,
            "code_article": "BOEUF01",
            "designation": "Faux-filet boeuf",
            "prix_unitaire_ht": 12.0,
            "quantite_commandee": 10.0,
            "unite": "kg",
        }],
    })
    assert r.status_code == 201, r.text
    commande_id = r.json()["id"]

    # Réception : poids RÉELLEMENT pesé = 9.4 kg (moins que commandé)
    cur = await db.execute(
        """INSERT INTO receptions (personnel_id, heure_reception, fournisseur_principal_id, statut)
           VALUES (1, '08:00', ?, 'cloturee')""",
        (fournisseur_id,),
    )
    await db.commit()
    reception_id = cur.lastrowid
    cur2 = await db.execute(
        """INSERT INTO reception_lignes (reception_id, catalogue_fournisseur_id, poids_kg, statut)
           VALUES (?, ?, 9.4, 'complet')""",
        (reception_id, cat_id),
    )
    await db.commit()

    # Mapping commande ↔ réception
    r = await client.post("/api/achats/commande_receptions_mapping", json={
        "commande_id": commande_id, "reception_id": reception_id,
    })
    assert r.status_code == 201, r.text

    return {
        "fournisseur_id": fournisseur_id, "cat_id": cat_id,
        "commande_id": commande_id, "reception_id": reception_id,
    }


@pytest.mark.asyncio
async def test_facture_depuis_reception_prerempli(app_client, db):
    ids = await _setup_base(app_client, db)

    r = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    assert r.status_code == 201, r.text
    fac = r.json()

    assert fac["reception_id"] == ids["reception_id"]
    assert fac["commande_id"] == ids["commande_id"]
    assert fac["statut"] == "brouillon"
    assert len(fac["lignes"]) == 1

    ligne = fac["lignes"][0]
    # Poids reçu figé = 9.4 (réception), prix commande = 12 (commande mappée)
    assert ligne["poids_recu_kg"] == 9.4
    assert ligne["prix_commande_ht"] == 12.0
    assert ligne["quantite_commandee"] == 10.0
    # Pré-rempli : facturé = reçu, prix = commande → écarts nuls au départ
    assert ligne["poids_facture_kg"] == 9.4
    assert ligne["prix_facture_ht"] == 12.0
    assert ligne["ecart_poids_kg"] == 0.0
    assert ligne["ecart_montant_ht"] == 0.0


@pytest.mark.asyncio
async def test_ecart_poids_facture(app_client, db):
    ids = await _setup_base(app_client, db)
    r = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    fac = r.json()
    ligne_id = fac["lignes"][0]["id"]

    # Le fournisseur facture 10 kg alors que 9.4 ont été pesés → écart +0.6 kg
    r = await app_client.put(
        f"/api/achats/factures/{fac['id']}/lignes/{ligne_id}",
        json={"poids_facture_kg": 10.0},
    )
    assert r.status_code == 200, r.text
    ligne = r.json()
    assert abs(ligne["ecart_poids_kg"] - 0.6) < 1e-9
    # montant facturé = 10 × 12 = 120 ; attendu = 9.4 × 12 = 112.8 → écart 7.2
    assert abs(ligne["montant_facture_ht"] - 120.0) < 1e-9
    assert abs(ligne["ecart_montant_ht"] - 7.2) < 1e-9

    # Totaux d'entête recalculés
    r = await app_client.get(f"/api/achats/factures/{fac['id']}")
    head = r.json()
    assert abs(head["montant_total_ht_facture"] - 120.0) < 1e-9
    assert abs(head["montant_total_ht_attendu"] - 112.8) < 1e-9
    assert abs(head["ecart_total_ht"] - 7.2) < 1e-9


@pytest.mark.asyncio
async def test_ecart_prix_et_litige(app_client, db):
    ids = await _setup_base(app_client, db)
    r = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    fac = r.json()
    ligne_id = fac["lignes"][0]["id"]

    # Prix facturé 13 au lieu de 12 négocié → écart +1, et on marque en litige
    r = await app_client.put(
        f"/api/achats/factures/{fac['id']}/lignes/{ligne_id}",
        json={"prix_facture_ht": 13.0, "statut_ligne": "litige",
              "commentaire_litige": "Prix supérieur au tarif négocié"},
    )
    assert r.status_code == 200, r.text
    ligne = r.json()
    assert abs(ligne["ecart_prix_ht"] - 1.0) < 1e-9
    assert ligne["statut_ligne"] == "litige"

    # Liste : le compteur de litiges remonte
    r = await app_client.get("/api/achats/factures")
    factures = {f["id"]: f for f in r.json()}
    assert factures[fac["id"]]["nb_litiges"] == 1


@pytest.mark.asyncio
async def test_reception_jamais_modifiee(app_client, db):
    """La saisie d'un poids facturé ne doit PAS toucher reception_lignes.poids_kg."""
    ids = await _setup_base(app_client, db)
    r = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    fac = r.json()
    ligne_id = fac["lignes"][0]["id"]

    await app_client.put(
        f"/api/achats/factures/{fac['id']}/lignes/{ligne_id}",
        json={"poids_facture_kg": 10.0},
    )

    cur = await db.execute(
        "SELECT poids_kg FROM reception_lignes WHERE reception_id = ?", (ids["reception_id"],)
    )
    row = await cur.fetchone()
    assert row["poids_kg"] == 9.4  # inchangé


@pytest.mark.asyncio
async def test_commande_expose_reception_et_facture(app_client, db):
    """get_commande enrichit reception_id (mapping) + facture_id (bouton 'Saisir la facture')."""
    ids = await _setup_base(app_client, db)

    # Avant facture : reception mappée connue, pas de facture
    r = await app_client.get(f"/api/achats/commandes/{ids['commande_id']}")
    cmd = r.json()
    assert cmd["reception_id"] == ids["reception_id"]
    assert cmd["facture_id"] is None

    # Après création : facture_id renseigné
    rf = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    facture_id = rf.json()["id"]
    r2 = await app_client.get(f"/api/achats/commandes/{ids['commande_id']}")
    assert r2.json()["facture_id"] == facture_id


@pytest.mark.asyncio
async def test_doublon_facture_refuse(app_client, db):
    ids = await _setup_base(app_client, db)
    r1 = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    assert r1.status_code == 201
    r2 = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    assert r2.status_code == 409, r2.text

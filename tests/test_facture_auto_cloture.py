"""
test_facture_auto_cloture.py — Étape 4 : facture brouillon auto à la clôture de réception.

Vérifie :
- la clôture génère une facture brouillon pré-remplie avec le prix BL (prix_facture_ht) ;
- un écart prix > 2 % vs commande met la ligne en litige et l'entête en 'litige' ;
- un refus total de livraison ne génère PAS de facture ;
- l'idempotence (facture déjà existante) n'empêche pas la clôture ;
- une réception sans fournisseur se clôture quand même (facture non créée, non bloquant).
"""
import pytest


async def _personnel(db):
    await db.execute(
        "INSERT OR IGNORE INTO personnel (id, boutique_id, prenom, actif) VALUES (1, 1, 'Test', 1)"
    )
    await db.commit()


async def _setup(client, db, prix_cmd=12.0, prix_bl=12.0, avec_commande=True, avec_fournisseur=True):
    """Crée fournisseur + catalogue + (commande) + réception cloturable avec prix BL sur la ligne.

    Renvoie {reception_id, fournisseur_id, cat_id, commande_id?}.
    """
    await _personnel(db)
    fournisseur_id = None
    cat_id = None
    if avec_fournisseur:
        r = await client.post("/api/achats/fournisseurs", json={"nom": "Bourdicaud"})
        fournisseur_id = r.json()["id"]
        r = await client.post("/api/achats/catalogue", json={
            "fournisseur_id": fournisseur_id, "code_article": "CB01",
            "designation": "Côte de boeuf", "prix_achat_ht": prix_cmd,
            "format_prix": "kg", "famille": "Viande",
        })
        cat_id = r.json()["id"]

    commande_id = None
    if avec_commande and avec_fournisseur:
        r = await client.post("/api/achats/commandes", json={
            "fournisseur_id": fournisseur_id,
            "lignes": [{
                "catalogue_fournisseur_id": cat_id, "code_article": "CB01",
                "designation": "Côte de boeuf", "prix_unitaire_ht": prix_cmd,
                "quantite_commandee": 10.0, "unite": "kg",
            }],
        })
        commande_id = r.json()["id"]

    # Réception EN COURS (statut sera passé à cloturee par l'endpoint)
    cur = await db.execute(
        """INSERT INTO receptions (personnel_id, heure_reception, fournisseur_principal_id, statut)
           VALUES (1, '08:00', ?, 'en_cours')""",
        (fournisseur_id,),
    )
    await db.commit()
    reception_id = cur.lastrowid

    # Ligne de réception avec poids pesé + prix BL
    await db.execute(
        """INSERT INTO reception_lignes
               (reception_id, catalogue_fournisseur_id, poids_kg, prix_unitaire_ht, statut, conforme)
           VALUES (?, ?, 9.4, ?, 'complet', 1)""",
        (reception_id, cat_id, prix_bl),
    )
    await db.commit()

    if commande_id:
        r = await client.post("/api/achats/commande_receptions_mapping", json={
            "commande_id": commande_id, "reception_id": reception_id,
        })
        assert r.status_code == 201, r.text

    return {"reception_id": reception_id, "fournisseur_id": fournisseur_id,
            "cat_id": cat_id, "commande_id": commande_id}


async def _factures_de(client, reception_id):
    r = await client.get("/api/achats/factures")
    assert r.status_code == 200, r.text
    return [f for f in r.json() if f["reception_id"] == reception_id]


@pytest.mark.anyio
async def test_cloture_genere_facture_brouillon_prix_bl(app_client, db):
    # Commande à 12 €/kg, BL à 12 €/kg (pas d'écart) → facture brouillon, prix_facture = BL
    ids = await _setup(app_client, db, prix_cmd=12.0, prix_bl=12.0)
    r = await app_client.put(f"/api/receptions/{ids['reception_id']}/cloturer", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("facture_auto", {}).get("creee") is True
    fac_id = body["facture_auto"]["facture_id"]

    # La facture existe, statut brouillon, prix facturé = prix BL
    r = await app_client.get(f"/api/achats/factures/{fac_id}")
    assert r.status_code == 200, r.text
    fac = r.json()
    assert fac["statut"] == "brouillon"
    ligne = fac["lignes"][0]
    assert ligne["prix_facture_ht"] == 12.0
    assert ligne["poids_recu_kg"] == 9.4
    assert ligne["statut_ligne"] == "ok"


@pytest.mark.anyio
async def test_cloture_ecart_prix_met_en_litige(app_client, db):
    # Commande 12 €/kg, BL 15 €/kg → +25 % > 2 % → litige
    ids = await _setup(app_client, db, prix_cmd=12.0, prix_bl=15.0)
    r = await app_client.put(f"/api/receptions/{ids['reception_id']}/cloturer", json={})
    assert r.status_code == 200, r.text
    fac_id = r.json()["facture_auto"]["facture_id"]

    r = await app_client.get(f"/api/achats/factures/{fac_id}")
    fac = r.json()
    assert fac["statut"] == "litige", "l'entête doit passer en litige si une ligne l'est"
    ligne = fac["lignes"][0]
    assert ligne["statut_ligne"] == "litige"
    assert ligne["prix_facture_ht"] == 15.0
    assert ligne["commentaire_litige"] and "Écart prix" in ligne["commentaire_litige"]


@pytest.mark.anyio
async def test_refus_livraison_pas_de_facture(app_client, db):
    ids = await _setup(app_client, db)
    r = await app_client.put(
        f"/api/receptions/{ids['reception_id']}/cloturer",
        json={"livraison_refusee": True},
    )
    assert r.status_code == 200, r.text
    # facture_auto absente/None puisque refus
    assert not r.json().get("facture_auto")
    assert await _factures_de(app_client, ids["reception_id"]) == []


@pytest.mark.anyio
async def test_idempotent_si_facture_existe(app_client, db):
    # On crée d'abord la facture manuellement, puis on clôture → pas de doublon, clôture OK
    ids = await _setup(app_client, db)
    r = await app_client.post(f"/api/achats/factures/depuis-reception/{ids['reception_id']}")
    assert r.status_code == 201, r.text

    r = await app_client.put(f"/api/receptions/{ids['reception_id']}/cloturer", json={})
    assert r.status_code == 200, r.text
    fa = r.json().get("facture_auto", {})
    assert fa.get("creee") is False
    assert fa.get("raison") == "deja_facturee"
    # Une seule facture pour cette réception
    assert len(await _factures_de(app_client, ids["reception_id"])) == 1


@pytest.mark.anyio
async def test_sans_fournisseur_cloture_ok_sans_facture(app_client, db):
    # Réception sans fournisseur ni commande → clôture réussit, facture non créée
    ids = await _setup(app_client, db, avec_commande=False, avec_fournisseur=False)
    r = await app_client.put(f"/api/receptions/{ids['reception_id']}/cloturer", json={})
    assert r.status_code == 200, r.text
    fa = r.json().get("facture_auto", {})
    assert fa.get("creee") is False
    assert fa.get("raison") == "sans_fournisseur"
    assert await _factures_de(app_client, ids["reception_id"]) == []

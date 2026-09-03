"""
test_commande_numerotation.py — Numérotation des commandes (CMD-AAAAMMJJ-NNN).

Le numéro est unique en base. Il doit rester généré sans collision même après
suppression d'une commande du jour, sinon la génération depuis le panier
échoue en 500 et plus aucune commande ne peut être passée de la journée.
"""
import pytest


async def _fournisseur(client, nom):
    r = await client.post("/api/achats/fournisseurs", json={"nom": nom})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _article(client, fournisseur_id, code, designation):
    r = await client.post("/api/achats/catalogue", json={
        "fournisseur_id": fournisseur_id,
        "code_article": code,
        "designation": designation,
        "prix_achat_ht": 10.0,
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_generer_apres_suppression_commande_du_jour(app_client, db):
    """Créer 2 commandes, en supprimer une, regénérer → pas de collision de numéro."""
    fid = await _fournisseur(app_client, "Numero-Co")
    art = await _article(app_client, fid, "ART01", "Article test")

    ligne = {"catalogue_fournisseur_id": art, "fournisseur_id": fid,
             "fournisseur_nom": "Numero-Co", "code_article": "ART01",
             "designation": "Article test", "quantite": 5.0,
             "unite": "kg", "prix_ht": 10.0}

    numeros = []
    for _ in range(2):
        r = await app_client.put("/api/achats/panier", json={"lignes": [ligne]})
        assert r.status_code == 200, r.text
        r = await app_client.post("/api/achats/panier/generer", json={})
        assert r.status_code == 201, r.text
        numeros.append(r.json()["commandes"][0])

    # Suppression de la 1re commande du jour → le COUNT(*) redescend
    r = await app_client.delete(f"/api/achats/commandes/{numeros[0]['id']}")
    assert r.status_code == 204, r.text

    # 3e génération : le numéro calculé retombe sur celui de la commande restante
    r = await app_client.put("/api/achats/panier", json={"lignes": [ligne]})
    assert r.status_code == 200, r.text
    r = await app_client.post("/api/achats/panier/generer", json={})
    assert r.status_code == 201, r.text
    nouveau = r.json()["commandes"][0]["numero_commande"]
    assert nouveau != numeros[1]["numero_commande"]

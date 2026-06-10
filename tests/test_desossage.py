"""
test_desossage.py — Règle métier prestation désossage veau.

Quand le panier contient du veau (famille=Viande, sous-famille=Veau), le
fournisseur dont le catalogue contient l'article 99864-1 reçoit, à la génération
des commandes, une ligne de prestation désossage dont la quantité (kg) = poids
total de veau commandé chez CE fournisseur. Appliqué fournisseur par fournisseur.
"""
import pytest


async def _fournisseur(client, nom):
    r = await client.post("/api/achats/fournisseurs", json={"nom": nom})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _article(client, fournisseur_id, code, designation, **kw):
    body = {
        "fournisseur_id": fournisseur_id,
        "code_article": code,
        "designation": designation,
        "prix_achat_ht": kw.pop("prix_achat_ht", 10.0),
    }
    body.update(kw)
    r = await client.post("/api/achats/catalogue", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _set_panier(client, lignes):
    r = await client.put("/api/achats/panier", json={"lignes": lignes})
    assert r.status_code == 200, r.text


async def _lignes_commande(client, commande_id):
    r = await client.get(f"/api/achats/commandes/{commande_id}")
    assert r.status_code == 200, r.text
    return r.json()["lignes"]


@pytest.mark.asyncio
async def test_desossage_ajoute_avec_poids_total_veau(app_client, db):
    """Veau en kg chez un fournisseur ayant 99864-1 → ligne désossage = somme des kg."""
    fid = await _fournisseur(app_client, "Veau-Co")
    veau1 = await _article(app_client, fid, "VEAU01", "Côte de veau",
                           famille="Viande", sous_famille="Veau")
    veau2 = await _article(app_client, fid, "VEAU02", "Épaule de veau",
                           famille="Viande", sous_famille="Veau")
    prest = await _article(app_client, fid, "99864-1", "PREST DESOSSAGE VX PAD",
                           prix_achat_ht=2.5)

    def ligne(cat_id, code, design, qte):
        return {"catalogue_fournisseur_id": cat_id, "fournisseur_id": fid,
                "fournisseur_nom": "Veau-Co", "code_article": code,
                "designation": design, "quantite": qte, "unite": "kg", "prix_ht": 10.0}

    await _set_panier(app_client, [
        ligne(veau1, "VEAU01", "Côte de veau", 12.0),
        ligne(veau2, "VEAU02", "Épaule de veau", 8.5),
    ])

    r = await app_client.post("/api/achats/panier/generer", json={})
    assert r.status_code == 201, r.text
    cmd = r.json()["commandes"][0]

    lignes = await _lignes_commande(app_client, cmd["id"])
    desossage = [l for l in lignes if l["code_article"] == "99864-1"]
    assert len(desossage) == 1, "une ligne désossage attendue"
    assert desossage[0]["quantite_commandee"] == pytest.approx(20.5)  # 12 + 8.5
    assert desossage[0]["unite"] == "kg"


@pytest.mark.asyncio
async def test_pas_de_desossage_sans_veau(app_client, db):
    """Sans veau au panier → aucune ligne désossage, même si 99864-1 est au catalogue."""
    fid = await _fournisseur(app_client, "Boeuf-Co")
    boeuf = await _article(app_client, fid, "BOEUF01", "Faux-filet",
                           famille="Viande", sous_famille="Boeuf")
    await _article(app_client, fid, "99864-1", "PREST DESOSSAGE VX PAD")

    await _set_panier(app_client, [{
        "catalogue_fournisseur_id": boeuf, "fournisseur_id": fid,
        "fournisseur_nom": "Boeuf-Co", "code_article": "BOEUF01",
        "designation": "Faux-filet", "quantite": 5.0, "unite": "kg", "prix_ht": 12.0,
    }])

    r = await app_client.post("/api/achats/panier/generer", json={})
    assert r.status_code == 201, r.text
    lignes = await _lignes_commande(app_client, r.json()["commandes"][0]["id"])
    assert not [l for l in lignes if l["code_article"] == "99864-1"]


@pytest.mark.asyncio
async def test_veau_sans_prestation_au_catalogue_ignore(app_client, db):
    """Veau chez un fournisseur sans 99864-1 → pas de ligne désossage (pas d'erreur)."""
    fid = await _fournisseur(app_client, "Veau-SansPrest")
    veau = await _article(app_client, fid, "VEAU01", "Côte de veau",
                          famille="Viande", sous_famille="Veau")

    await _set_panier(app_client, [{
        "catalogue_fournisseur_id": veau, "fournisseur_id": fid,
        "fournisseur_nom": "Veau-SansPrest", "code_article": "VEAU01",
        "designation": "Côte de veau", "quantite": 10.0, "unite": "kg", "prix_ht": 10.0,
    }])

    r = await app_client.post("/api/achats/panier/generer", json={})
    assert r.status_code == 201, r.text
    lignes = await _lignes_commande(app_client, r.json()["commandes"][0]["id"])
    assert not [l for l in lignes if l["code_article"] == "99864-1"]


@pytest.mark.asyncio
async def test_desossage_par_fournisseur(app_client, db):
    """Veau chez deux fournisseurs ; seul celui qui a 99864-1 reçoit la prestation,
    avec le poids de SON veau uniquement."""
    f1 = await _fournisseur(app_client, "Fournisseur-A")
    f2 = await _fournisseur(app_client, "Fournisseur-B")
    veau1 = await _article(app_client, f1, "VEAU01", "Côte de veau",
                           famille="Viande", sous_famille="Veau")
    await _article(app_client, f1, "99864-1", "PREST DESOSSAGE VX PAD", prix_achat_ht=2.5)
    veau2 = await _article(app_client, f2, "VEAU02", "Épaule de veau",
                           famille="Viande", sous_famille="Veau")  # f2 n'a PAS 99864-1

    await _set_panier(app_client, [
        {"catalogue_fournisseur_id": veau1, "fournisseur_id": f1,
         "fournisseur_nom": "Fournisseur-A", "code_article": "VEAU01",
         "designation": "Côte de veau", "quantite": 7.0, "unite": "kg", "prix_ht": 10.0},
        {"catalogue_fournisseur_id": veau2, "fournisseur_id": f2,
         "fournisseur_nom": "Fournisseur-B", "code_article": "VEAU02",
         "designation": "Épaule de veau", "quantite": 30.0, "unite": "kg", "prix_ht": 10.0},
    ])

    r = await app_client.post("/api/achats/panier/generer", json={})
    assert r.status_code == 201, r.text
    cmds = r.json()["commandes"]

    desossage = []
    for c in cmds:
        desossage += [l for l in await _lignes_commande(app_client, c["id"])
                      if l["code_article"] == "99864-1"]
    assert len(desossage) == 1, "seul le fournisseur avec 99864-1 reçoit la prestation"
    assert desossage[0]["quantite_commandee"] == pytest.approx(7.0)  # veau de f1 seulement


@pytest.mark.asyncio
async def test_desossage_idempotent(app_client, db):
    """Une ligne 99864-1 déjà dans le panier ne doit pas être doublée ni cumulée :
    elle est régénérée à partir du poids de veau réel."""
    fid = await _fournisseur(app_client, "Veau-Idem")
    veau = await _article(app_client, fid, "VEAU01", "Côte de veau",
                          famille="Viande", sous_famille="Veau")
    prest = await _article(app_client, fid, "99864-1", "PREST DESOSSAGE VX PAD", prix_achat_ht=2.5)

    await _set_panier(app_client, [
        {"catalogue_fournisseur_id": veau, "fournisseur_id": fid,
         "fournisseur_nom": "Veau-Idem", "code_article": "VEAU01",
         "designation": "Côte de veau", "quantite": 9.0, "unite": "kg", "prix_ht": 10.0},
        # Ligne désossage parasite avec un mauvais poids (simule un panier restauré)
        {"catalogue_fournisseur_id": prest, "fournisseur_id": fid,
         "fournisseur_nom": "Veau-Idem", "code_article": "99864-1",
         "designation": "PREST DESOSSAGE VX PAD", "quantite": 999.0, "unite": "kg", "prix_ht": 2.5},
    ])

    r = await app_client.post("/api/achats/panier/generer", json={})
    assert r.status_code == 201, r.text
    lignes = await _lignes_commande(app_client, r.json()["commandes"][0]["id"])
    desossage = [l for l in lignes if l["code_article"] == "99864-1"]
    assert len(desossage) == 1
    assert desossage[0]["quantite_commandee"] == pytest.approx(9.0)  # recalculé, pas 999

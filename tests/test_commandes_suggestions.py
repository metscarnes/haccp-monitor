"""
test_commandes_suggestions.py — Moteur de suggestions de commande, pop-up
« oublis » et étoile ⭐ cachée dans Commandes (audit du 15/11/2026).

Historique simulé : Elivia commandé 2×/semaine, Saveurs 1×/semaine.
"""
from datetime import date, timedelta

import pytest

T = date.today()


async def _fournisseur(db, nom):
    cur = await db.execute("INSERT INTO fournisseurs (nom, boutique_id) VALUES (?, 1)", (nom,))
    return cur.lastrowid


async def _article(db, fid, code, famille=None):
    cur = await db.execute(
        "INSERT INTO catalogue_fournisseur (fournisseur_id, code_article, designation, "
        "prix_achat_ht, actif, famille) VALUES (?,?,?,10,1,?)",
        (fid, code, f"Article {code}", famille))
    return cur.lastrowid


async def _commande(db, fid, jours_avant, lignes, statut="livree"):
    cur = await db.execute(
        "INSERT INTO commandes (boutique_id, fournisseur_id, date_commande, statut) VALUES (1,?,?,?)",
        (fid, (T - timedelta(days=jours_avant)).isoformat(), statut))
    for cat_id, qte in lignes:
        await db.execute(
            "INSERT INTO commande_lignes (commande_id, catalogue_fournisseur_id, code_article, "
            "designation, quantite_commandee, unite) VALUES (?,?,?,?,?,'kg')",
            (cur.lastrowid, cat_id, "X", "X", qte))


async def _historique(db):
    E = await _fournisseur(db, "Elivia-test")
    S = await _fournisseur(db, "Saveurs-test")
    a = {
        "bavette": await _article(db, E, "BAV"),   # dans chaque commande Elivia
        "onglet":  await _article(db, E, "ONG"),   # arrêté depuis ~100 j
        "paleron": await _article(db, E, "PAL"),   # 1 commande Elivia sur 2
        "jambon":  await _article(db, S, "JAM"),   # dans chaque commande Saveurs
    }
    n, j = 0, 2
    while j < 175:
        lignes = [(a["bavette"], 10)]
        if j > 100:
            lignes.append((a["onglet"], 5))
        if n % 2 == 0:
            lignes.append((a["paleron"], 8))
        await _commande(db, E, j, lignes)
        j += 3 if n % 2 == 0 else 4
        n += 1
    j = 6
    while j < 175:
        await _commande(db, S, j, [(a["jambon"], 12)])
        j += 7
    await db.commit()
    return E, S, a


@pytest.mark.asyncio
async def test_frequence_mesuree_sur_les_commandes_du_fournisseur(app_client, db):
    E, S, a = await _historique(db)
    r = await app_client.get("/api/achats/panier/suggestions")
    assert r.status_code == 200, r.text
    s = {x["catalogue_fournisseur_id"]: x for x in r.json()["suggestions"]}
    # Présent dans 100 % des commandes de SON fournisseur, quel que soit le rythme.
    assert s[a["jambon"]]["composantes"]["frequence"] == pytest.approx(1.0)
    assert s[a["bavette"]]["composantes"]["frequence"] == pytest.approx(1.0)
    assert s[a["paleron"]]["composantes"]["frequence"] == pytest.approx(0.5, abs=0.02)
    # Consommation : la dernière livraison n'est pas comptée comme consommée.
    assert s[a["jambon"]]["conso_hebdo"] == pytest.approx(12.0, rel=0.02)


@pytest.mark.asyncio
async def test_article_arrete_plus_a_commander(app_client, db):
    E, S, a = await _historique(db)
    r = await app_client.get("/api/achats/panier/suggestions")
    s = {x["catalogue_fournisseur_id"]: x for x in r.json()["suggestions"]}
    assert s[a["onglet"]]["arrete"] is True
    assert s[a["onglet"]]["a_commander"] is False
    assert s[a["onglet"]]["score"] < s[a["paleron"]]["score"]
    assert s[a["bavette"]]["arrete"] is False


@pytest.mark.asyncio
async def test_oublis_par_fournisseur(app_client, db):
    E, S, a = await _historique(db)
    r = await app_client.get(f"/api/achats/panier/oublis?fournisseur_ids={E}")
    assert r.status_code == 200, r.text
    ids = {o["catalogue_fournisseur_id"] for o in r.json()}
    assert a["bavette"] in ids          # dans toutes les commandes
    assert a["paleron"] in ids          # dans 1 sur 2 (seuil 50 %)
    assert a["onglet"] not in ids       # arrêté
    assert a["jambon"] not in ids       # autre fournisseur, pas dans le panier
    bav = next(o for o in r.json() if o["catalogue_fournisseur_id"] == a["bavette"])
    assert bav["derniere_qte"] == 10 and bav["derniere_unite"] == "kg"
    assert bav["nb_commandes"] == 8


@pytest.mark.asyncio
async def test_oublis_ignore_brouillons_et_historique_trop_court(app_client, db):
    F = await _fournisseur(db, "Nouveau-test")
    art = await _article(db, F, "NEW")
    await _commande(db, F, 3, [(art, 4)])
    await _commande(db, F, 10, [(art, 4)])
    await _commande(db, F, 1, [(art, 4)], statut="brouillon")   # ignorée
    await db.commit()
    r = await app_client.get(f"/api/achats/panier/oublis?fournisseur_ids={F}")
    assert r.status_code == 200
    assert r.json() == []   # 2 commandes passées seulement : on ne devine rien


@pytest.mark.asyncio
async def test_etoile_cachee_dans_commandes_seulement(app_client, db):
    E = await _fournisseur(db, "Ref-test")
    art = await _article(db, E, "REF")
    cur = await db.execute("INSERT INTO comparatif_groupe (nom, boutique_id) VALUES ('Groupe test', 1)")
    gid = cur.lastrowid
    cur = await db.execute(
        "INSERT INTO catalogue_vente (nom, boutique_id, actif) VALUES ('Produit test', 1, 1)")
    vid = cur.lastrowid
    await db.execute(
        "INSERT INTO comparatif_groupe_vente (groupe_id, catalogue_vente_id, ligne_choisie_id) VALUES (?,?,?)",
        (gid, vid, art))
    await db.commit()

    refs = (await app_client.get("/api/achats/panier/references")).json()
    assert art in {r["catalogue_fournisseur_id"] for r in refs}

    r = await app_client.put(f"/api/achats/panier/references/{art}", json={"masquee": True})
    assert r.status_code == 200, r.text
    refs = (await app_client.get("/api/achats/panier/references")).json()
    assert art not in {r["catalogue_fournisseur_id"] for r in refs}
    # Le comparatif (base des marges) n'est pas touché.
    cur = await db.execute(
        "SELECT ligne_choisie_id FROM comparatif_groupe_vente WHERE groupe_id = ?", (gid,))
    assert (await cur.fetchone())[0] == art

    r = await app_client.put(f"/api/achats/panier/references/{art}", json={"masquee": False})
    assert r.status_code == 200
    refs = (await app_client.get("/api/achats/panier/references")).json()
    assert art in {r["catalogue_fournisseur_id"] for r in refs}

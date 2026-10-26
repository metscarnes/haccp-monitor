"""
test_file_etiquettes_prix.py — File des étiquettes prix à réimprimer.

Chaîne testée : prix d'achat → proposition validée → produit dans la file → impression
(serveur) ou sortie manuelle (navigateur / retiré) → produit hors de la file.
L'imprimante n'est jamais appelée : imprimer_lot / imprimer_etiquette_prix sont simulés.
"""

import pytest

import src.printing.brother_ql_prix as brother
from tests.test_prix_vente_moteur import _appliquer, _propositions, _reception, _scenario
from tests.test_liaison_vente_achat import _produit_vente

pytestmark = pytest.mark.asyncio


async def _file(client, ids=None):
    r = await client.get("/api/prix-etiquettes/a-reimprimer")
    assert r.status_code == 200, r.text
    elements = r.json()["elements"]
    if ids is not None:   # catalogue_vente n'est pas vidé entre les tests
        elements = [e for e in elements if e["catalogue_vente_id"] in ids]
    return {e["catalogue_vente_id"]: e for e in elements}


async def _sortir(client, ids, statut="imprimee", mode="navigateur"):
    r = await client.post("/api/prix-etiquettes/a-reimprimer/sortir",
                          json={"produit_ids": ids, "statut": statut, "mode": mode})
    assert r.status_code == 200, r.text
    return r.json()


async def _modele(client, nom="Prix", lignes=None):
    from tests.test_styles_etiquettes import creer_modele
    return await creer_modele(client, nom, {
        "largeur_cm": 10, "hauteur_cm": 6.2,
        "lignes": lignes or [{"texte": "{Nom}"}, {"texte": "{prix}"}, {"texte": "{article_unite}"}]})


async def test_nouveau_prix_entre_dans_la_file_et_garde_le_prix_en_rayon(app_client, db):
    pid = await _produit_vente(app_client, "Onglet file", prix_vente_ttc=24.90, unite_vente="kg")
    await _sortir(app_client, [pid])          # étiquette de création déjà posée
    assert await _file(app_client, {pid}) == {}

    await app_client.put(f"/api/vente/catalogue/{pid}", json={"prix_vente_ttc": 25.90})
    await app_client.put(f"/api/vente/catalogue/{pid}", json={"prix_vente_ttc": 26.90})
    e = (await _file(app_client, {pid}))[pid]
    assert e["prix_ancien_ttc"] == 24.90      # prix de l'étiquette encore en rayon
    assert e["prix_actuel_ttc"] == 26.90      # l'impression prendra le prix ACTUEL
    assert e["nom"] == "Onglet file"

    # Retour au prix de l'étiquette en rayon : plus rien à refaire.
    await app_client.put(f"/api/vente/catalogue/{pid}", json={"prix_vente_ttc": 24.90})
    assert await _file(app_client, {pid}) == {}


async def test_proposition_validee_a_la_reception_met_l_etiquette_en_file(app_client, db):
    s = await _scenario(app_client)
    await _sortir(app_client, [s["steak"], s["bourgui"], s["roti"]])   # étiquettes de création
    rid = await _reception(db, s["fid"])
    await _appliquer(app_client, s["a"], 10.40, rid)
    pid = {p["catalogue_vente_id"]: p["id"]
           for p in (await _propositions(app_client, reception_id=rid))["propositions"]}
    r = await app_client.post("/api/vente/propositions-prix/decider", json={"decisions": [
        {"proposition_id": pid[s["steak"]], "action": "appliquer"},
        {"proposition_id": pid[s["bourgui"]], "action": "garder"},
    ]})
    assert r.status_code == 200, r.text

    file = await _file(app_client, {s["steak"], s["bourgui"], s["roti"]})
    assert set(file) == {s["steak"]}          # prix gardé → étiquette inchangée
    assert file[s["steak"]]["prix_ancien_ttc"] == 18.90
    assert file[s["steak"]]["prix_actuel_ttc"] == 19.90
    assert file[s["steak"]]["motif"] == "proposition"
    r = await app_client.get("/api/prix-etiquettes/a-reimprimer/compte")
    assert r.json()["total"] >= 1


async def test_impression_de_masse_sort_les_produits_imprimes(app_client, db, monkeypatch):
    a = await _produit_vente(app_client, "Masse A", prix_vente_ttc=10.90, unite_vente="kg")
    b = await _produit_vente(app_client, "Masse B", prix_vente_ttc=3.99, unite_vente="piece")
    envoyees = []

    def faux_lot(configs):
        envoyees.extend(configs)
        return True, "ok"
    monkeypatch.setattr(brother, "imprimer_lot", faux_lot)

    modele = {"largeur_cm": 10, "hauteur_cm": 6.2,
              "lignes": [{"texte": "{Nom}"}, {"texte": "{prix}"}, {"texte": "{article_unite}"}]}
    r = await app_client.post("/api/prix-etiquettes/imprimer-masse", json={
        "config": modele,
        "produits": [{"produit_id": a, "quantite": 2}, {"produit_id": b, "quantite": 1}],
    })
    assert r.status_code == 200, r.text
    assert r.json() == {"imprimees": 3, "erreurs": []}
    textes = [[l["texte"] for l in c["lignes"]] for c in envoyees]
    assert textes[0] == ["Masse a", "10,90 €", "le kg"]
    assert textes[2] == ["Masse b", "3,99 €", "la pièce"]
    assert await _file(app_client, {a, b}) == {}

    h = (await app_client.get("/api/prix-etiquettes/a-reimprimer/historique")).json()["historique"]
    assert {x["catalogue_vente_id"] for x in h if x["mode"] == "serveur"} >= {a, b}


async def test_impression_de_masse_en_echec_garde_les_produits_en_file(app_client, db, monkeypatch):
    a = await _produit_vente(app_client, "Echec A", prix_vente_ttc=10.90)
    monkeypatch.setattr(brother, "imprimer_lot", lambda configs: (False, "Erreur imprimante : timeout"))
    r = await app_client.post("/api/prix-etiquettes/imprimer-masse", json={
        "config": {"lignes": [{"texte": "{prix}"}]},
        "produits": [{"produit_id": a, "quantite": 1}],
    })
    assert r.status_code == 503
    assert set(await _file(app_client, {a})) == {a}


async def test_impression_unitaire_remplit_les_variables_et_sort_de_la_file(app_client, db,
                                                                            monkeypatch):
    pid = await _produit_vente(app_client, "CÔTE DE BŒUF", prix_vente_ttc=32.90, unite_vente="kg")
    recu = {}

    def faux_unitaire(data):
        recu.update(data)
        return True, "Étiquette imprimée."
    monkeypatch.setattr(brother, "imprimer_etiquette_prix", faux_unitaire)

    r = await app_client.post("/api/prix-etiquettes/imprimer", json={
        "largeur_cm": 10, "hauteur_cm": 6.2, "produit_id": pid,
        "lignes": [{"texte": "{Nom}"}, {"texte": "{prix}"}, {"texte": "Fait maison"}],
    })
    assert r.status_code == 200, r.text
    assert [l["texte"] for l in recu["lignes"]] == ["Côte de bœuf", "32,90 €", "Fait maison"]
    assert "produit_id" not in recu
    assert await _file(app_client, {pid}) == {}

    # Sans produit : étiquette libre, au style de la boutique.
    await _modele(app_client, "Style")
    r = await app_client.post("/api/prix-etiquettes/imprimer",
                              json={"lignes": [{"texte": "Promo"}]})
    assert r.status_code == 200 and recu["lignes"][0]["texte"] == "Promo"


async def test_produit_desactive_absent_et_retrait_manuel(app_client, db):
    a = await _produit_vente(app_client, "Inactif file", prix_vente_ttc=9.90)
    b = await _produit_vente(app_client, "Retire file", prix_vente_ttc=8.90)
    await app_client.put(f"/api/vente/catalogue/{a}", json={"actif": False})
    assert set(await _file(app_client, {a, b})) == {b}

    res = await _sortir(app_client, [b], statut="retiree", mode="manuel")
    assert res["traites"] == 1
    assert await _file(app_client, {b}) == {}
    r = await app_client.post("/api/prix-etiquettes/a-reimprimer/sortir",
                              json={"produit_ids": [b], "statut": "nimporte"})
    assert r.status_code == 422


async def test_modele_par_defaut(app_client, db):
    r = await app_client.get("/api/prix-etiquettes/modele-defaut")
    assert r.json() == {"modele_id": None}            # aucun modèle

    unique = await _modele(app_client, "Prix boutique")
    r = await app_client.get("/api/prix-etiquettes/modele-defaut")
    assert r.json() == {"modele_id": unique}          # modèle unique → choisi d'office

    autre = await _modele(app_client, "Promo")
    r = await app_client.get("/api/prix-etiquettes/modele-defaut")
    assert r.json() == {"modele_id": None}            # plusieurs → à choisir
    from tests.test_styles_etiquettes import jeton_styles
    jeton = (await jeton_styles(app_client)).json()["jeton"]   # réservé à l'administrateur
    r = await app_client.put("/api/prix-etiquettes/modele-defaut",
                             json={"modele_id": autre, "jeton": jeton})
    assert r.json() == {"modele_id": autre}
    assert (await app_client.get("/api/prix-etiquettes/a-reimprimer")).json()[
        "modele_defaut_id"] == autre
    r = await app_client.put("/api/prix-etiquettes/modele-defaut",
                             json={"modele_id": 99999, "jeton": jeton})
    assert r.status_code == 404


async def test_historique_des_impressions(app_client, db, monkeypatch):
    a = await _produit_vente(app_client, "Histo A", prix_vente_ttc=10.90, unite_vente="kg")
    b = await _produit_vente(app_client, "Histo B", prix_vente_ttc=3.99, unite_vente="piece")
    monkeypatch.setattr(brother, "imprimer_lot", lambda c: (True, "ok"))
    monkeypatch.setattr(brother, "imprimer_etiquette_prix", lambda d: (True, "ok"))

    r = await app_client.post("/api/prix-etiquettes/imprimer-masse", json={
        "config": {"lignes": [{"texte": "{Nom}"}]},
        "produits": [{"produit_id": a, "quantite": 2}, {"produit_id": b, "quantite": 1}]})
    assert r.status_code == 200
    await _modele(app_client, "Style")                    # l'étiquette libre reprend le style
    await app_client.post("/api/prix-etiquettes/imprimer", json={"lignes": [{"texte": "Paupiette de lapin"}, {"texte": "14,90 €"}]})
    await app_client.post("/api/prix-etiquettes/impressions/navigateur",
                          json={"type": "normal", "produits": [{"produit_id": b, "quantite": 3}]})

    h = (await app_client.get("/api/prix-etiquettes/impressions")).json()["impressions"]
    nav, libre, serie = h[0], h[1], h[2]                    # du plus récent au plus ancien
    assert serie["mode"] == "serveur" and serie["total"] == 3 and len(serie["imprime_at"]) == 19
    assert [(l["libelle"], l["quantite"], l["prix_ttc"]) for l in serie["lignes"]] == [
        ("Histo A", 2, 10.90), ("Histo B", 1, 3.99)]
    # Toutes les lignes sont gardées : l'historique les affiche et peut les réimprimer.
    assert libre["lignes"] == [{"libelle": "Paupiette de lapin\n14,90 €", "quantite": 1, "type": "libre",
                                "prix_ttc": None, "catalogue_vente_id": None, "unite_vente": None,
                                "fait_maison": False}]
    assert nav["mode"] == "navigateur" and nav["lignes"][0]["quantite"] == 3

    # Échec de l'imprimante : rien n'est noté.
    monkeypatch.setattr(brother, "imprimer_lot", lambda c: (False, "Erreur imprimante : timeout"))
    await app_client.post("/api/prix-etiquettes/imprimer-masse", json={
        "config": {"lignes": [{"texte": "{Nom}"}]}, "produits": [{"produit_id": a, "quantite": 1}]})
    assert len((await app_client.get("/api/prix-etiquettes/impressions")).json()["impressions"]) == 3

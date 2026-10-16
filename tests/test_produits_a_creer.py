"""
test_produits_a_creer.py — Étiquette prix hors catalogue → produit à créer au catalogue.

Chaîne testée : l'équipe imprime une étiquette prix (nom, prix, unité) pour un article
absent du catalogue de vente → étiquette au style de la boutique + demande notée →
tâche du Hub → produit créé au catalogue → demande close, tâche disparue.
L'imprimante n'est jamais appelée : imprimer_etiquette_prix est simulé.
"""

import pytest

import src.printing.brother_ql_prix as brother
from tests.test_file_etiquettes_prix import _modele
from tests.test_liaison_vente_achat import _produit_vente

pytestmark = pytest.mark.asyncio


def _espion(monkeypatch):
    envoyees = []
    monkeypatch.setattr(brother, "imprimer_etiquette_prix",
                        lambda d: (envoyees.append(d), (True, "ok"))[1])
    return envoyees


async def _imprimer(client, nom, prix, unite="kg"):
    r = await client.post("/api/prix-etiquettes/imprimer-hors-catalogue",
                          json={"nom": nom, "prix_vente_ttc": prix, "unite_vente": unite})
    assert r.status_code == 200, r.text
    return r.json()


async def _demandes(client, nom=None):
    d = (await client.get("/api/prix-etiquettes/produits-a-creer")).json()["demandes"]
    return [x for x in d if nom is None or x["nom"] == nom]


async def _tache_hub(client):
    t = (await client.get("/api/hub/taches-resume")).json()["aujourd_hui"]
    return next((x for x in t if x["code"] == "produits_a_creer"), None)


async def test_etiquette_prix_au_style_et_demande_de_creation(app_client, db, monkeypatch):
    envoyees = _espion(monkeypatch)
    await _modele(app_client, "Style")
    rep = await _imprimer(app_client, "Paupiette  de lapin", 14.9, "piece")
    assert rep["demande_id"] and rep["existant"] is None

    # Mise en page officielle : les zones du style remplies avec nom / prix / unité.
    assert [l["texte"] for l in envoyees[0]["lignes"]] == ["Paupiette de lapin", "14,90 €", "la pièce"]
    assert envoyees[0]["largeur_cm"] == 10

    # Réimprimer la même (autre casse, accents) : pas de doublon, prix mis à jour.
    rep2 = await _imprimer(app_client, "PAUPIETTE DE LAPIN", 15.9, "piece")
    assert rep2["demande_id"] == rep["demande_id"]
    [d] = await _demandes(app_client, "PAUPIETTE DE LAPIN")
    assert d["prix_vente_ttc"] == 15.9 and d["unite_vente"] == "piece" and d["nb_etiquettes"] == 2

    tache = await _tache_hub(app_client)
    assert tache and tache["url"] == "/catalogue-vente.html?a_creer=1"

    # Historique : réimprimable (nom, prix, unité gardés).
    h = (await app_client.get("/api/prix-etiquettes/impressions")).json()["impressions"]
    ligne = h[0]["lignes"][0]
    assert (ligne["type"], ligne["libelle"], ligne["prix_ttc"], ligne["unite_vente"]) == (
        "hors_catalogue", "PAUPIETTE DE LAPIN", 15.9, "piece")

    # Le produit est créé au catalogue (fiche pré-remplie) → demande close.
    pid = await _produit_vente(app_client, "Paupiette de lapin", prix_vente_ttc=15.9, unite_vente="piece")
    r = await app_client.post(f"/api/prix-etiquettes/produits-a-creer/{rep['demande_id']}/cree",
                              json={"catalogue_vente_id": pid})
    assert r.status_code == 200
    assert await _demandes(app_client, "PAUPIETTE DE LAPIN") == []
    r = await app_client.post(f"/api/prix-etiquettes/produits-a-creer/{rep['demande_id']}/cree",
                              json={"catalogue_vente_id": pid})
    assert r.status_code == 404                                # déjà traitée


async def test_produit_deja_au_catalogue_pas_de_demande(app_client, db, monkeypatch):
    _espion(monkeypatch)
    await _modele(app_client, "Style")
    await _produit_vente(app_client, "Rôti de veau HC", prix_vente_ttc=32.9, unite_vente="kg")
    rep = await _imprimer(app_client, "roti de veau hc", 32.9)
    assert rep["demande_id"] is None and rep["existant"]["nom"] == "Rôti de veau HC"


async def test_demande_close_si_produit_cree_ailleurs_ou_ignoree(app_client, db, monkeypatch):
    _espion(monkeypatch)
    await _modele(app_client, "Style")
    await _imprimer(app_client, "Terrine maison HC", 22.5)
    rep = await _imprimer(app_client, "Boudin blanc HC", 19.9)
    # Créé directement dans le catalogue (sans passer par la demande) : close d'elle-même.
    await _produit_vente(app_client, "Terrine Maison HC", prix_vente_ttc=22.5, unite_vente="kg")
    assert await _demandes(app_client, "Terrine maison HC") == []
    # « Ignorer » : retirée de la liste.
    r = await app_client.post(f"/api/prix-etiquettes/produits-a-creer/{rep['demande_id']}/ignorer")
    assert r.status_code == 200 and await _demandes(app_client, "Boudin blanc HC") == []


async def test_saisie_invalide_et_impression_navigateur(app_client, db, monkeypatch):
    _espion(monkeypatch)
    await _modele(app_client, "Style")
    for corps in ({"nom": "  ", "prix_vente_ttc": 5}, {"nom": "X", "prix_vente_ttc": 0},
                  {"nom": "X", "prix_vente_ttc": 5, "unite_vente": "colis"}):
        r = await app_client.post("/api/prix-etiquettes/imprimer-hors-catalogue", json=corps)
        assert r.status_code == 422, corps
    # Impression par le navigateur : notée dans l'historique ET demande de création.
    r = await app_client.post("/api/prix-etiquettes/impressions/navigateur", json={
        "type": "hors_catalogue",
        "article": {"nom": "Saucisse aux herbes HC", "prix_vente_ttc": 16.9, "unite_vente": "kg"}})
    assert r.status_code == 201 and r.json()["demande_id"]
    assert len(await _demandes(app_client, "Saucisse aux herbes HC")) == 1

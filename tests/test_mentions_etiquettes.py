"""
test_mentions_etiquettes.py — Mentions des étiquettes prix (AOP, IGP, Label Rouge,
Artisanal, Sans nitrite ajouté, Local, Race à viande).

Cochées dans la fiche du produit (2 au maximum), elles s'affichent en bandeau sous le
texte ; pour une étiquette libre ou hors catalogue, ce sont les boutons de l'écran.
L'imprimante n'est jamais appelée.
"""

import pytest

import src.printing.brother_ql_prix as brother
from tests.test_file_etiquettes_prix import _modele
from tests.test_liaison_vente_achat import _produit_vente

pytestmark = pytest.mark.asyncio

CONFIG = {"largeur_cm": 10, "hauteur_cm": 6, "fond_noir": True,
          "lignes": [{"texte": "Côte de bœuf"}, {"texte": "32,90 €"}]}


def test_fichiers_des_mentions_presents():
    for cle in brother.MENTIONS_ORDRE:
        assert (brother.MENTIONS_DIR / f"{cle}.png").is_file(), cle


def test_normalisation_ordre_et_maximum():
    assert brother.normaliser_mentions(["local", "aop", "igp", "inconnue", "aop"]) == ["aop", "igp"]
    assert brother.lire_mentions('["race_viande", "label_rouge"]') == ["label_rouge", "race_viande"]
    assert brother.lire_mentions("pas du json") == [] and brother.lire_mentions(None) == []
    assert brother.mentions_json([]) is None


def test_bandeau_en_bas_et_texte_au_dessus():
    h = brother.cm_to_px(6)
    w = brother.cm_to_px(10)
    marge_v = round(h * 0.06)
    tailles = [brother._mention(c).size for c in ("label_rouge", "race_viande")]
    g = brother.geometrie_mentions(tailles, round(w * .05), w - round(w * .05), h, marge_v)
    (x1, y1, w1, h1), (x2, y2, w2, h2) = g["placements"]
    assert x1 + w1 < x2 and max(y1 + h1, y2 + h2) <= h - marge_v      # côte à côte, en bas
    assert g["bas_texte"] < min(y1, y2)                                # le texte au-dessus
    # L'image a bien de l'encre dans le bandeau, et pas sans mentions.
    bas = lambda img: sum(1 for x in range(0, img.width, 4) for y in range(min(y1, y2), h - marge_v, 4)
                          if img.convert("L").getpixel((x, y)) > 128)
    sans = brother.generer_image_prix(CONFIG)
    avec = brother.generer_image_prix({**CONFIG, "mentions": ["label_rouge", "race_viande"]})
    assert bas(avec) > 5 * bas(sans) + 50


async def test_fiche_produit_jusqu_a_l_impression(app_client, db, monkeypatch):
    envoyes = []
    monkeypatch.setattr(brother, "imprimer_lot", lambda c: (envoyes.extend(c), (True, "ok"))[1])
    monkeypatch.setattr(brother, "imprimer_etiquette_prix", lambda d: (envoyes.append(d), (True, "ok"))[1])
    await _modele(app_client, "Style")
    pid = await _produit_vente(app_client, "Côte LR test", prix_vente_ttc=32.9, unite_vente="kg")

    r = await app_client.put(f"/api/vente/catalogue/{pid}", json={"mentions": ["aop", "igp", "local"]})
    assert r.status_code == 422                                   # 3 mentions : refusé
    r = await app_client.put(f"/api/vente/catalogue/{pid}", json={"mentions": ["bio"]})
    assert r.status_code == 422                                   # mention inconnue
    r = await app_client.put(f"/api/vente/catalogue/{pid}", json={"mentions": ["race_viande", "label_rouge"]})
    assert r.status_code == 200 and r.json()["mentions"] == ["label_rouge", "race_viande"]
    liste = (await app_client.get("/api/vente/catalogue")).json()
    assert [p["mentions"] for p in liste if p["id"] == pid] == [["label_rouge", "race_viande"]]

    r = await app_client.post("/api/prix-etiquettes/imprimer-masse", json={
        "config": {"lignes": [{"texte": "{Nom}"}]}, "produits": [{"produit_id": pid, "quantite": 1}]})
    assert r.status_code == 200 and envoyes[-1]["mentions"] == ["label_rouge", "race_viande"]

    # Retirer les mentions.
    r = await app_client.put(f"/api/vente/catalogue/{pid}", json={"mentions": []})
    assert r.status_code == 200 and r.json()["mentions"] == []

    # Étiquette libre / hors catalogue : les boutons de l'écran, gardés dans l'historique.
    await app_client.post("/api/prix-etiquettes/imprimer",
                          json={"lignes": [{"texte": "Arrivage"}], "mentions": ["local"]})
    assert envoyes[-1]["mentions"] == ["local"]
    r = await app_client.post("/api/prix-etiquettes/imprimer-hors-catalogue", json={
        "nom": "Jambon sans nitrite HC", "prix_vente_ttc": 34.9, "mentions": ["sans_nitrite", "artisanal"]})
    assert r.status_code == 200 and envoyes[-1]["mentions"] == ["artisanal", "sans_nitrite"]
    h = (await app_client.get("/api/prix-etiquettes/impressions")).json()["impressions"]
    assert h[0]["lignes"][0]["mentions"] == ["artisanal", "sans_nitrite"]
    assert h[1]["lignes"][0]["mentions"] == ["local"]
    d = (await app_client.get("/api/prix-etiquettes/produits-a-creer")).json()["demandes"]
    assert [x["mentions"] for x in d if x["nom"] == "Jambon sans nitrite HC"] == [["artisanal", "sans_nitrite"]]


async def test_mentions_de_l_article_d_achat(app_client, db):
    """Le label n'est plus écrit dans la désignation : il se coche sur l'article d'achat."""
    from tests.test_commande_numerotation import _fournisseur
    fid = await _fournisseur(app_client, "Fournisseur mentions")
    corps = {"fournisseur_id": fid, "code_article": "LR-1", "designation": "Poulet fermier",
             "prix_achat_ht": 8.5}
    r = await app_client.post("/api/achats/catalogue", json={**corps, "mentions": ["aop", "igp", "local"]})
    assert r.status_code == 422                                   # 3 mentions : refusé
    r = await app_client.post("/api/achats/catalogue", json={**corps, "mentions": ["local", "label_rouge"]})
    assert r.status_code == 201 and r.json()["mentions"] == ["label_rouge", "local"]
    aid = r.json()["id"]
    liste = (await app_client.get(f"/api/achats/catalogue?fournisseur_id={fid}")).json()
    assert [a["mentions"] for a in liste if a["id"] == aid] == [["label_rouge", "local"]]
    r = await app_client.put(f"/api/achats/catalogue/{aid}", json={"mentions": []})
    assert r.status_code == 200 and r.json()["mentions"] == []
    # Un article sans mention (champ non fourni) renvoie une liste vide.
    r = await app_client.post("/api/achats/catalogue", json={**corps, "code_article": "LR-2"})
    assert r.status_code == 201 and r.json()["mentions"] == []

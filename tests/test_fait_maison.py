"""
test_fait_maison.py — Logo « Fait maison » sur les étiquettes prix.

Le logo suit la case « Fait maison » de la fiche du produit (catalogue de vente) ;
pour une étiquette libre ou hors catalogue, c'est le bouton de l'écran. Il occupe une
colonne à gauche et le texte se range à droite. L'imprimante n'est jamais appelée.
"""

import pytest

import src.printing.brother_ql_prix as brother
from tests.test_file_etiquettes_prix import _modele
from tests.test_liaison_vente_achat import _produit_vente

pytestmark = pytest.mark.asyncio

CONFIG = {"largeur_cm": 10, "hauteur_cm": 6, "fond_noir": True,
          "lignes": [{"texte": "Paupiette"}, {"texte": "14,90 €"}]}


def _encre_a_gauche(img, x_max):
    """Nombre de pixels blancs (encre sur fond noir) dans la bande x < x_max."""
    g = img.convert("L")
    return sum(1 for x in range(0, x_max, 3) for y in range(0, g.height, 3) if g.getpixel((x, y)) > 128)


def test_logo_dessine_dans_sa_colonne_et_texte_a_droite():
    court = {**CONFIG, "lignes": [{"texte": "A"}]}        # texte étroit : bande gauche vide
    sans = brother.generer_image_prix(court)
    avec = brother.generer_image_prix({**court, "fait_maison": True})
    w, h = avec.size
    fm = brother.geometrie_fait_maison(w, h, round(w * 0.05))
    assert fm["x_logo"] + fm["lw"] < fm["x0"]               # le logo ne touche pas le texte
    col = fm["x0"] - 5
    assert _encre_a_gauche(sans, col) < _encre_a_gauche(avec, col) / 10   # le logo est là
    assert brother.LOGO_FAIT_MAISON.is_file()


def test_appliquer_variables_suit_la_fiche_produit():
    d = brother.appliquer_variables(CONFIG, {"nom": "X", "prix_vente_ttc": 1, "fait_maison": 1})
    assert d["fait_maison"] is True
    d = brother.appliquer_variables({**CONFIG, "fait_maison": True}, {"nom": "X", "fait_maison": 0})
    assert d["fait_maison"] is False
    assert brother.config_libre(CONFIG, ["Arrivage"], fait_maison=True)["fait_maison"] is True


async def test_case_fiche_produit_jusqu_a_l_impression(app_client, db, monkeypatch):
    envoyes = []
    monkeypatch.setattr(brother, "imprimer_lot", lambda c: (envoyes.extend(c), (True, "ok"))[1])
    monkeypatch.setattr(brother, "imprimer_etiquette_prix", lambda d: (envoyes.append(d), (True, "ok"))[1])
    await _modele(app_client, "Style")
    pid = await _produit_vente(app_client, "Terrine FM", prix_vente_ttc=24.9, unite_vente="kg")
    r = await app_client.put(f"/api/vente/catalogue/{pid}", json={"fait_maison": True})
    assert r.status_code == 200 and r.json()["fait_maison"] == 1

    cat = (await app_client.get("/api/prix-etiquettes/catalogue?q=Terrine FM")).json()["articles"]
    assert [a["fait_maison"] for a in cat if a["id"] == pid] == [True]

    r = await app_client.post("/api/prix-etiquettes/imprimer-masse", json={
        "config": {"lignes": [{"texte": "{Nom}"}]}, "produits": [{"produit_id": pid, "quantite": 1}]})
    assert r.status_code == 200 and envoyes[-1]["fait_maison"] is True

    # Étiquette libre et hors catalogue : le bouton de l'écran, gardé dans l'historique.
    await app_client.post("/api/prix-etiquettes/imprimer",
                          json={"lignes": [{"texte": "Arrivage"}], "fait_maison": True})
    assert envoyes[-1]["fait_maison"] is True
    r = await app_client.post("/api/prix-etiquettes/imprimer-hors-catalogue", json={
        "nom": "Pâté en croûte FM", "prix_vente_ttc": 29.9, "fait_maison": True})
    assert r.status_code == 200 and envoyes[-1]["fait_maison"] is True
    h = (await app_client.get("/api/prix-etiquettes/impressions")).json()["impressions"]
    assert h[0]["lignes"][0]["fait_maison"] is True and h[1]["lignes"][0]["fait_maison"] is True
    d = (await app_client.get("/api/prix-etiquettes/produits-a-creer")).json()["demandes"]
    assert [x["fait_maison"] for x in d if x["nom"] == "Pâté en croûte FM"] == [1]

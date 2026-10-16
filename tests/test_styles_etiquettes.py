"""
test_styles_etiquettes.py — Styles d'étiquettes à zones (normal / promo).

Le style ne contient que l'apparence ; le texte vient de la zone (nom, prix, unité…).
Les anciens modèles au texte écrit en dur sont repris automatiquement.
"""

import json
import os

import pytest

from src.printing.brother_ql_prix import (
    appliquer_variables, generer_image_prix, normaliser_style,
)

pytestmark = pytest.mark.asyncio

# Le modèle réellement en production le 15/10/2026 (lu sur le VPS).
MODELE_PROD = {"largeur_cm": 10.0, "hauteur_cm": 6.0, "fond_noir": True, "lignes": [
    {"texte": "Graisse de canard", "poids": 1.0, "taille_px": 0, "gras": False,
     "police": "MoreSugar-Thin.otf", "alignement": "center"},
    {"texte": "9,90 €", "poids": 1.0, "taille_px": 0, "gras": False,
     "police": "MoreSugar-Thin.otf", "alignement": "center"},
    {"texte": "le kg", "poids": 0.6, "taille_px": 0, "gras": False,
     "police": "MoreSugar-Thin.otf", "alignement": "center"}]}


async def jeton_styles(client, password=None):
    """Déverrouille l'édition du style (mot de passe administrateur) → autorisation.
    La limite anti-essais (partagée avec la connexion) est remise à zéro : sinon les
    tests, enchaînés en quelques secondes, la déclencheraient."""
    from src.api import routes_auth
    routes_auth._login_tentatives.clear()
    r = await client.post("/api/prix-etiquettes/styles/deverrouiller",
                          json={"password": password or os.environ["ADMIN_PASSWORD"]})
    return r


async def test_modele_de_production_repris_en_zones():
    style, converti = normaliser_style(MODELE_PROD)
    assert converti is True
    assert [(l["zone"], l["texte"]) for l in style["lignes"]] == [
        ("nom", "{Nom}"), ("prix", "{prix}"), ("unite", "{article_unite}")]
    assert style["type"] == "normal"
    # L'apparence est intacte.
    assert style["fond_noir"] is True and style["hauteur_cm"] == 6.0
    assert [l["police"] for l in style["lignes"]] == ["MoreSugar-Thin.otf"] * 3
    assert [l["poids"] for l in style["lignes"]] == [1.0, 1.0, 0.6]
    # Un style déjà à zones n'est plus « converti ».
    assert normaliser_style(style)[1] is False

    produit = {"nom": "CORDON BLEU", "prix_vente_ttc": 2.99, "unite_vente": "piece"}
    textes = [l["texte"] for l in appliquer_variables(style, produit)["lignes"]]
    assert textes == ["Cordon bleu", "2,99 €", "la pièce"]


async def test_texte_fixe_et_variable_inconnue_restent_du_texte():
    style, _ = normaliser_style({"lignes": [
        {"texte": "{Nom}"}, {"texte": "Fait maison"}, {"texte": "Rayon {famille}"}]})
    assert [(l["zone"], l["texte"]) for l in style["lignes"]] == [
        ("nom", "{Nom}"), ("texte", "Fait maison"), ("texte", "Rayon {famille}")]


async def test_style_promo_et_variables_promo():
    style, _ = normaliser_style({"type": "promo", "lignes": [
        {"zone": "nom"}, {"zone": "prix_reference"}, {"zone": "prix_promo"},
        {"zone": "unite"}, {"zone": "economie"}]})
    assert style["type"] == "promo"
    assert [l["barre"] for l in style["lignes"]] == [False, True, False, False, False]
    produit = {"nom": "Steak haché", "prix_vente_ttc": 19.90, "unite_vente": "kg",
               "promo": {"prix_reference_ttc": 19.90, "prix_promo_ttc": 16.90}}
    textes = [l["texte"] for l in appliquer_variables(style, produit)["lignes"]]
    assert textes == ["Steak haché", "19,90 €", "16,90 €", "le kg", "Économisez 3,00 € / kg"]


async def test_prix_barre_dessine_un_trait():
    base = {"largeur_cm": 6, "hauteur_cm": 3, "lignes": [{"texte": "19,90 €"}]}
    sans = generer_image_prix(base).convert("L")
    avec = generer_image_prix({**base, "lignes": [{"texte": "19,90 €", "barre": True}]}).convert("L")
    noirs = lambda img: sum(1 for p in img.getdata() if p < 128)
    assert noirs(avec) > noirs(sans)          # le trait ajoute de l'encre


async def test_enregistrer_les_styles_normal_et_promo(app_client, db):
    r = await app_client.post("/api/prix-etiquettes/modeles",
                              json={"nom": "sauvegarde 3 test", "config": MODELE_PROD})
    ancien = r.json()["id"]
    styles = (await app_client.get("/api/prix-etiquettes/styles")).json()
    assert styles["normal"]["id"] == ancien and styles["normal"]["converti"] is True
    # Style promo proposé d'office, tiré du style normal (pas encore enregistré).
    promo = styles["promo"]
    assert promo["id"] is None and promo["par_defaut"] is True
    assert [l["zone"] for l in promo["config"]["lignes"]] == [
        "nom", "prix_reference", "prix_promo", "unite", "economie"]
    assert promo["config"]["fond_noir"] is True
    assert {l["police"] for l in promo["config"]["lignes"]} == {"MoreSugar-Thin.otf"}

    # « Enregistrer le style » : le texte affiché n'est jamais enregistré.
    cfg = {**styles["normal"]["config"]}
    cfg["lignes"][0] = {**cfg["lignes"][0], "texte": "Graisse de canard", "poids": 2}
    jeton = (await jeton_styles(app_client)).json()["jeton"]
    r = await app_client.put("/api/prix-etiquettes/styles/normal", json={"config": cfg, "jeton": jeton})
    assert r.status_code == 200, r.text
    normal = r.json()["normal"]
    assert normal["id"] == ancien                      # même modèle, mis à jour…
    assert normal["nom"] == "Étiquette normale"        # …et renommé selon son rôle
    modeles = (await app_client.get("/api/prix-etiquettes/modeles")).json()["modeles"]
    assert {m["id"]: m["style"] for m in modeles}[ancien] == "normal"
    assert normal["config"]["lignes"][0]["texte"] == "{Nom}"
    assert normal["config"]["lignes"][0]["poids"] == 2
    cur = await db.execute("SELECT config_json FROM modeles_etiquettes_prix WHERE id = ?", (ancien,))
    assert json.loads((await cur.fetchone())[0])["lignes"][1]["zone"] == "prix"

    promo_cfg = {**cfg, "lignes": [{"zone": "nom"}, {"zone": "prix_reference"},
                                   {"zone": "prix_promo", "poids": 3}, {"zone": "economie"}]}
    r = await app_client.put("/api/prix-etiquettes/styles/promo", json={"config": promo_cfg, "jeton": jeton})
    styles = r.json()
    assert styles["promo"]["nom"] == "Étiquette promo"
    assert styles["promo"]["config"]["type"] == "promo"
    # Le style promo ne prend pas la place du style normal pour les réimpressions.
    r = await app_client.get("/api/prix-etiquettes/modele-defaut")
    assert r.json()["modele_id"] == ancien
    r = await app_client.put("/api/prix-etiquettes/styles/inconnu", json={"config": cfg, "jeton": jeton})
    assert r.status_code == 404


async def test_style_reserve_a_l_administrateur(app_client, db):
    r = await app_client.post("/api/prix-etiquettes/modeles",
                              json={"nom": "Style prod", "config": MODELE_PROD})
    modele = r.json()["id"]
    cfg = (await app_client.get("/api/prix-etiquettes/styles")).json()["normal"]["config"]

    # Sans autorisation, ou avec une fausse : refusé, rien n'est modifié.
    for corps in ({"config": cfg}, {"config": cfg, "jeton": "faux"}):
        r = await app_client.put("/api/prix-etiquettes/styles/normal", json=corps)
        assert r.status_code == 401
    r = await app_client.put("/api/prix-etiquettes/modele-defaut", json={"modele_id": modele})
    assert r.status_code == 401
    # Mauvais mot de passe administrateur : pas d'autorisation.
    assert (await jeton_styles(app_client, "pas-le-bon")).status_code == 401

    # L'étiquette libre ne peut ni modifier ni supprimer un modèle qui sert de style.
    r = await app_client.put(f"/api/prix-etiquettes/modeles/{modele}",
                             json={"nom": "x", "config": MODELE_PROD})
    assert r.status_code == 409
    assert (await app_client.delete(f"/api/prix-etiquettes/modeles/{modele}")).status_code == 409

    # Une police utilisée par le style ne se supprime pas.
    from src.api.routes_prix_etiquettes import FONTS_DIR
    police = FONTS_DIR / "MoreSugar-Thin.otf"
    cree = not police.exists()
    if cree:
        police.write_bytes(b"test")
    try:
        r = await app_client.delete("/api/prix-etiquettes/fonts/MoreSugar-Thin.otf")
        assert r.status_code == 409 and police.exists()
    finally:
        if cree:
            police.unlink()

    # Avec le mot de passe administrateur : autorisé.
    r = await jeton_styles(app_client)
    assert r.status_code == 200 and r.json()["expire_dans"] == 15 * 60
    r = await app_client.put("/api/prix-etiquettes/styles/normal",
                             json={"config": cfg, "jeton": r.json()["jeton"]})
    assert r.status_code == 200

"""
test_hub_disposition.py — Disposition des tuiles du Hub (ordre, dossiers, tuiles retirées).

Une seule disposition pour la boutique, modifiable seulement avec le mot de passe
administrateur (autorisation de 15 min, comme le style des étiquettes).
"""

import json
import os

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client(app_client, db):
    """Client connecté, sans disposition enregistrée par un test précédent."""
    await db.execute("DELETE FROM parametres WHERE cle = 'hub_disposition'")
    await db.commit()
    return app_client


async def jeton(client, password=None):
    from src.api import routes_auth
    routes_auth._login_tentatives.clear()
    return await client.post("/api/hub/disposition/deverrouiller",
                             json={"password": password or os.environ["ADMIN_PASSWORD"]})


async def enregistrer(client, **disposition):
    j = (await jeton(client)).json()["jeton"]
    return await client.put("/api/hub/disposition", json={**disposition, "jeton": j})


async def test_hub_d_origine_par_defaut(client):
    r = await client.get("/api/hub/disposition")
    assert r.status_code == 200
    assert r.json()["personnalisee"] is False


async def test_enregistrer_avec_dossiers_imbriques(client):
    r = await enregistrer(client,
        accueil=["pilotage-ca", "dossier-achats", "reception", "reception"],
        dossiers={"dossier-achats": {"titre": "Achats", "icone": "🛒",
                                     "tuiles": ["commandes", "dossier-pilotage"]},
                  "dossier-pilotage": {"titre": "Pilotage", "icone": "📊", "tuiles": ["marge"]}},
        connues=["ouverture"])
    assert r.status_code == 200, r.text
    d = (await client.get("/api/hub/disposition")).json()
    assert d["personnalisee"] is True
    assert d["accueil"] == ["pilotage-ca", "dossier-achats", "reception"]      # doublon retiré
    assert d["dossiers"]["dossier-achats"]["tuiles"] == ["commandes", "dossier-pilotage"]
    assert d["dossiers"]["dossier-pilotage"] == {"titre": "Pilotage", "icone": "📊", "tuiles": ["marge"]}
    assert set(d["connues"]) == {"ouverture", "pilotage-ca", "reception", "commandes", "marge"}


async def test_dossier_dans_lui_meme_et_dossier_fantome_ignores(client):
    r = await enregistrer(client,
        accueil=["dossier-a", "dossier-inexistant"],
        dossiers={"dossier-a": {"titre": "A", "tuiles": ["dossier-b"]},
                  "dossier-b": {"titre": "B", "tuiles": ["dossier-a", "marge"]},   # boucle
                  "dossier-orphelin": {"titre": "O", "tuiles": ["cuisson"]}})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["accueil"] == ["dossier-a"]
    assert d["dossiers"]["dossier-b"]["tuiles"] == ["marge"]
    assert set(d["dossiers"]) == {"dossier-a", "dossier-b"}        # orphelin abandonné


async def test_sans_mot_de_passe_refuse(client):
    r = await client.put("/api/hub/disposition", json={"accueil": ["reception"]})
    assert r.status_code == 401
    assert (await jeton(client, password="mauvais")).status_code == 401
    r = await client.put("/api/hub/disposition", json={"accueil": ["reception"], "jeton": "faux"})
    assert r.status_code == 401
    assert (await client.get("/api/hub/disposition")).json()["personnalisee"] is False


async def test_identifiants_mal_formes_refuses(client):
    assert (await enregistrer(client, accueil=["<script>"])).status_code == 422
    r = await enregistrer(client, accueil=["mon-dossier"],
                          dossiers={"mon-dossier": {"titre": "X", "tuiles": []}})
    assert r.status_code == 422
    r = await enregistrer(client, accueil=["dossier-x"],
                          dossiers={"dossier-x": {"titre": "", "tuiles": []}})
    assert r.status_code == 422


async def test_ancien_format_ignore(client, db):
    """Une disposition d'avant les dossiers (jamais déployée) → Hub d'origine."""
    await db.execute("INSERT INTO parametres (boutique_id, cle, valeur) VALUES (1, 'hub_disposition', ?)",
                     (json.dumps({"ordre": ["reception"], "connues": []}),))
    await db.commit()
    assert (await client.get("/api/hub/disposition")).json()["personnalisee"] is False


async def test_revenir_a_l_origine(client):
    await enregistrer(client, accueil=["reception"])
    assert (await client.post("/api/hub/disposition/reinitialiser", json={})).status_code == 401
    j = (await jeton(client)).json()["jeton"]
    r = await client.post("/api/hub/disposition/reinitialiser", json={"jeton": j})
    assert r.status_code == 200
    assert (await client.get("/api/hub/disposition")).json()["personnalisee"] is False

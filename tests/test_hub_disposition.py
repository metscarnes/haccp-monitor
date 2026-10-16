"""
test_hub_disposition.py — Disposition des tuiles du Hub (ordre, tuiles masquées).

Une seule disposition pour la boutique, modifiable seulement avec le mot de passe
administrateur (autorisation de 15 min, comme le style des étiquettes).
"""

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


async def test_hub_d_origine_par_defaut(client):
    r = await client.get("/api/hub/disposition")
    assert r.status_code == 200
    assert r.json() == {"personnalisee": False, "ordre": [], "connues": []}


async def test_enregistrer_puis_relire(client):
    j = (await jeton(client)).json()["jeton"]
    r = await client.put("/api/hub/disposition", json={
        "ordre": ["pilotage-ca", "taches", "taches", "reception"],
        "connues": ["taches", "reception", "ouverture"], "jeton": j})
    assert r.status_code == 200
    d = (await client.get("/api/hub/disposition")).json()
    assert d["personnalisee"] is True
    assert d["ordre"] == ["pilotage-ca", "taches", "reception"]          # doublon retiré
    assert set(d["connues"]) == {"taches", "reception", "ouverture", "pilotage-ca"}


async def test_sans_mot_de_passe_refuse(client):
    r = await client.put("/api/hub/disposition", json={"ordre": ["taches"], "connues": []})
    assert r.status_code == 401
    assert (await jeton(client, password="mauvais")).status_code == 401
    r = await client.put("/api/hub/disposition",
                         json={"ordre": ["taches"], "connues": [], "jeton": "faux"})
    assert r.status_code == 401
    assert (await client.get("/api/hub/disposition")).json()["personnalisee"] is False


async def test_identifiant_mal_forme_refuse(client):
    j = (await jeton(client)).json()["jeton"]
    r = await client.put("/api/hub/disposition",
                         json={"ordre": ["<script>"], "connues": [], "jeton": j})
    assert r.status_code == 422


async def test_revenir_a_l_origine(client):
    j = (await jeton(client)).json()["jeton"]
    await client.put("/api/hub/disposition", json={"ordre": ["taches"], "connues": [], "jeton": j})
    assert (await client.post("/api/hub/disposition/reinitialiser", json={})).status_code == 401
    r = await client.post("/api/hub/disposition/reinitialiser", json={"jeton": j})
    assert r.status_code == 200
    assert (await client.get("/api/hub/disposition")).json()["personnalisee"] is False

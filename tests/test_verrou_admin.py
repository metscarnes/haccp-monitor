"""
test_verrou_admin.py — CA, marge et valeur du stock réservés au mot de passe administrateur.

Même connecté (équipe ou admin), ces API exigent l'autorisation temporaire
remise par /api/auth/deverrouiller, présentée dans l'en-tête X-Jeton-Admin.
"""

import os

import pytest

pytestmark = pytest.mark.asyncio

API_VERROUILLEES = [
    "/api/achats/pilotage/ca/stats/resume",
    "/api/achats/pilotage/ca?limit=5",
    "/api/inventaire/sessions?limit=1",
    "/api/inventaire/marge/tva",
]


async def sans_jeton(app_client, url):
    jeton = app_client.headers.pop("X-Jeton-Admin")
    try:
        return await app_client.get(url)
    finally:
        app_client.headers["X-Jeton-Admin"] = jeton


@pytest.mark.parametrize("url", API_VERROUILLEES)
async def test_refuse_sans_mot_de_passe_admin(app_client, db, url):
    r = await sans_jeton(app_client, url)
    assert r.status_code == 401
    assert r.json()["verrou"] == "pilotage"


@pytest.mark.parametrize("url", API_VERROUILLEES)
async def test_accepte_avec_l_autorisation(app_client, db, url):
    assert (await app_client.get(url)).status_code == 200


async def test_faux_jeton_et_mauvais_mot_de_passe(app_client, db):
    from src.api import routes_auth
    routes_auth._login_tentatives.clear()
    r = await app_client.post("/api/auth/deverrouiller", json={"password": "faux", "verrou": "pilotage"})
    assert r.status_code == 401
    r = await app_client.get("/api/inventaire/marge/tva", headers={"X-Jeton-Admin": "faux"})
    assert r.status_code == 401
    r = await app_client.post("/api/auth/deverrouiller",
                              json={"password": os.environ["ADMIN_PASSWORD"], "verrou": "inconnu"})
    assert r.status_code == 404


async def test_le_reste_de_l_appli_n_est_pas_verrouille(app_client, db):
    r = await sans_jeton(app_client, "/api/hub/taches-resume")
    assert r.status_code == 200

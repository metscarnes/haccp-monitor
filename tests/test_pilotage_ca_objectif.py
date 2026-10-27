"""
test_pilotage_ca_objectif.py — Objectif de CA mensuel et projection de fin de mois.

Projection = CA des journées terminées du mois + CA moyen du jour de semaine
(8 dernières semaines) pour chaque jour restant ; jour habituellement fermé = 0 €.
"""
import calendar
from datetime import date, timedelta

import pytest

from src.api.routes_achats import _aujourdhui_paris

API = "/api/achats/pilotage/ca"


async def _remplir_8_semaines(client):
    """100 € chaque jour jusqu'à hier, lundis fermés."""
    today = _aujourdhui_paris()
    for n in range(56, 0, -1):
        d = today - timedelta(days=n)
        corps = {"date_ca": d.isoformat()}
        corps.update({"ferme": True} if d.weekday() == 0 else {"montant_ttc_matin": 100})
        r = await client.post(API, json=corps)
        assert r.status_code == 201, r.text


@pytest.mark.anyio
async def test_projection_fin_de_mois_et_objectif(app_client, db):
    await _remplir_8_semaines(app_client)
    today = _aujourdhui_paris()
    nb_jours = calendar.monthrange(today.year, today.month)[1]
    ouverts = [date(today.year, today.month, j) for j in range(1, nb_jours + 1)
               if date(today.year, today.month, j).weekday() != 0]
    realises = [d for d in ouverts if d < today]
    restants = [d for d in ouverts if d >= today]

    o = (await app_client.get(f"{API}/objectif")).json()
    assert o["objectif_ttc"] is None
    assert o["realise_ttc"] == pytest.approx(100 * len(realises))
    assert o["jours_ouverts_restants"] == len(restants)            # les lundis comptent 0 €
    assert o["projection_ttc"] == pytest.approx(100 * len(ouverts))

    # Objectif au-dessus de la projection → écart négatif et besoin par jour
    objectif = 100 * len(ouverts) + 1000
    r = await app_client.put(f"{API}/objectif", json={"mois": o["mois"], "objectif_ttc": objectif})
    assert r.status_code == 200, r.text
    o = r.json()
    assert o["objectif_ttc"] == objectif
    assert o["ecart_projection"] == pytest.approx(-1000)
    assert o["reste_a_faire"] == pytest.approx(objectif - 100 * len(realises))
    if restants:
        assert o["besoin_par_jour"] == pytest.approx(round((objectif - 100 * len(realises)) / len(restants), 2))

    # Suppression
    r = await app_client.put(f"{API}/objectif", json={"mois": o["mois"], "objectif_ttc": None})
    assert r.json()["objectif_ttc"] is None


@pytest.mark.anyio
async def test_mois_passe_projection_egale_realise(app_client, db):
    await app_client.post(API, json={"date_ca": "2026-06-10", "montant_ttc_matin": 900})
    o = (await app_client.get(f"{API}/objectif", params={"mois": "2026-06"})).json()
    assert o["realise_ttc"] == pytest.approx(900)
    assert o["projection_ttc"] == pytest.approx(900)
    assert o["jours_ouverts_restants"] == 0


@pytest.mark.anyio
@pytest.mark.parametrize("corps", [{"mois": "2026-13", "objectif_ttc": 100},
                                   {"mois": "octobre", "objectif_ttc": 100},
                                   {"mois": "2026-10", "objectif_ttc": -5}])
async def test_objectif_refuse(app_client, db, corps):
    assert (await app_client.put(f"{API}/objectif", json=corps)).status_code == 400

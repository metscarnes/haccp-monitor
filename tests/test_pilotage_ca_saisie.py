"""
test_pilotage_ca_saisie.py — Saisie du CA quotidien (lot 1 de l'audit du 16/10/2026).

- Jour de fermeture enregistrable (CA 0) et exclu des moyennes / profils.
- Refus d'un jour sans montant (hors fermeture), d'une date future ou invalide.
- Jour proposé par défaut : le plus ancien oubli des 14 derniers jours, jamais futur.
"""
from datetime import timedelta

import pytest

from src.api.routes_achats import _aujourdhui_paris

API = "/api/achats/pilotage/ca"


async def _saisir(client, iso, matin=0.0, soir=0.0, tickets=10, ferme=False):
    return await client.post(API, json={
        "date_ca": iso,
        "montant_ttc_matin": matin,
        "nb_tickets_matin": tickets if matin else None,
        "montant_ttc_soir": soir,
        "nb_tickets_soir": tickets if soir else None,
        "ferme": ferme,
    })


@pytest.mark.anyio
async def test_jour_ferme_enregistre_a_zero(app_client, db):
    # Même avec des montants envoyés, un jour fermé est stocké à 0 sans tickets
    r = await _saisir(app_client, "2026-09-07", matin=500, soir=300, ferme=True)
    assert r.status_code == 201, r.text
    j = (await app_client.get(f"{API}/2026-09-07")).json()
    assert j["ferme"] == 1
    assert (j["montant_ttc"], j["montant_ttc_matin"], j["montant_ttc_soir"]) == (0, 0, 0)
    assert j["nb_tickets"] is None

    # Rouvrir le jour (correction) remet bien ferme à 0
    r = await _saisir(app_client, "2026-09-07", matin=400)
    assert r.status_code == 201, r.text
    j = (await app_client.get(f"{API}/2026-09-07")).json()
    assert j["ferme"] == 0 and j["montant_ttc"] == 400


@pytest.mark.anyio
@pytest.mark.parametrize("iso, attendu", [
    ("2026-09-08", "montant"),        # ni montant ni fermeture
    ("pas-une-date", "Date invalide"),
    ("futur", "pas encore passé"),
])
async def test_saisie_refusee(app_client, db, iso, attendu):
    if iso == "futur":
        iso = (_aujourdhui_paris() + timedelta(days=1)).isoformat()
        r = await _saisir(app_client, iso, matin=100)
    else:
        r = await _saisir(app_client, iso)
    assert r.status_code == 400
    assert attendu in r.json()["detail"]


@pytest.mark.anyio
async def test_jour_ferme_hors_moyennes(app_client, db):
    # Lun 31/08 et lun 14/09 ouverts à 1000 €, lun 07/09 fermé
    await _saisir(app_client, "2026-08-31", matin=1000)
    await _saisir(app_client, "2026-09-07", ferme=True)
    await _saisir(app_client, "2026-09-14", matin=1000)

    r = await app_client.get(f"{API}/stats/comparatif",
                             params={"date_debut": "2026-08-31", "date_fin": "2026-09-14"})
    courant = r.json()["courant"]
    assert courant["nb_jours"] == 2
    assert courant["ca_moyen_jour"] == pytest.approx(1000)

    p = (await app_client.get(f"{API}/stats/profil-semaine")).json()
    lundi = next(j for j in p["jours"] if j["dow"] == 1)
    assert lundi["nb"] == 2 and lundi["ca_moyen"] == pytest.approx(1000)

    # L'encart d'analyse d'un jour fermé le dit, et le lundi suivant ne se
    # compare pas au lundi fermé (pas de « +100 % » contre 0 €)
    ferme = (await app_client.get(f"{API}/stats/profil-semaine", params={"jour": "2026-09-07"})).json()
    assert ferme["dernier_vs_jour_type"]["ferme"] is True
    suivant = (await app_client.get(f"{API}/stats/profil-semaine", params={"jour": "2026-09-14"})).json()
    assert suivant["dernier_vs_jour_type"]["ca"]["s1"] is None

    lignes = (await app_client.get(f"{API}/stats/par-periode", params={"granularite": "jour"})).json()["lignes"]
    par_date = {l["periode"]: l for l in lignes}
    assert par_date["2026-09-07"]["ferme"] == 1
    assert par_date["2026-09-14"]["evolution"]["pct"] is None


@pytest.mark.anyio
async def test_prochain_a_saisir_plus_ancien_oubli(app_client, db):
    today = _aujourdhui_paris()
    j = lambda n: (today - timedelta(days=n)).isoformat()
    # Saisis : J-5, J-3 (fermé), J-1 → oubliés : J-4, J-2
    await _saisir(app_client, j(5), matin=100)
    await _saisir(app_client, j(3), ferme=True)
    await _saisir(app_client, j(1), matin=100)

    d = (await app_client.get(f"{API}/stats/prochain-a-saisir")).json()
    assert d == {"date": j(4), "oublis": 2}

    await _saisir(app_client, j(4), matin=100)
    await _saisir(app_client, j(2), matin=100)
    d = (await app_client.get(f"{API}/stats/prochain-a-saisir")).json()
    # Plus aucun oubli → aujourd'hui (jamais demain)
    assert d == {"date": today.isoformat(), "oublis": 0}

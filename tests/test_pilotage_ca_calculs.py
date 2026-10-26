"""
test_pilotage_ca_calculs.py — Calculs du CA quotidien (lot 2 de l'audit du 16/10/2026).

- Panier moyen : seul le CA des sections dont on connaît les tickets est divisé.
- Journée en cours exclue des moyennes (CA moyen / jour, glissantes, jour-type).
- Ajustements caisse/banque de la marge hors du suivi quotidien (table dédiée),
  y compris la migration des anciennes lignes.
"""
from datetime import timedelta

import pytest

from src.api.routes_achats import _aujourdhui_paris

API = "/api/achats/pilotage/ca"


async def _saisir(client, iso, matin=0.0, tm=None, soir=0.0, ts=None):
    r = await client.post(API, json={
        "date_ca": iso, "montant_ttc_matin": matin, "nb_tickets_matin": tm,
        "montant_ttc_soir": soir, "nb_tickets_soir": ts,
    })
    assert r.status_code == 201, r.text


@pytest.mark.anyio
async def test_panier_ignore_le_ca_sans_tickets(app_client, db):
    # Lun 07/09 : 1000 € / 50 tickets → 20 € ; lun 14/09 : 3000 € SANS tickets.
    # Lun 21/09 : matin 600 € / 20 tickets, après-midi 400 € sans tickets.
    await _saisir(app_client, "2026-09-07", matin=1000, tm=50)
    await _saisir(app_client, "2026-09-14", matin=3000)
    await _saisir(app_client, "2026-09-21", matin=600, tm=20, soir=400)

    # Panier = (1000 + 600) / (50 + 20) = 22,86 € (avant : 5000 / 70 = 71,43 €)
    cmp = (await app_client.get(f"{API}/stats/comparatif",
                                params={"date_debut": "2026-09-01", "date_fin": "2026-09-30"})).json()
    assert cmp["courant"]["panier_moyen"] == pytest.approx(22.86)
    assert cmp["courant"]["panier_moyen_matin"] == pytest.approx(22.86)
    assert cmp["courant"]["panier_moyen_soir"] is None

    jour = (await app_client.get(f"{API}/2026-09-21")).json()
    assert jour["panier_moyen"] == pytest.approx(30.0)          # 600 / 20

    lundi = next(j for j in (await app_client.get(f"{API}/stats/profil-semaine")).json()["jours"]
                 if j["dow"] == 1)
    assert lundi["panier_moyen"] == pytest.approx(22.86)

    mois = (await app_client.get(f"{API}/stats/par-periode", params={"granularite": "mois"})).json()
    assert mois["lignes"][0]["panier_moyen"] == pytest.approx(22.86)


@pytest.mark.anyio
async def test_journee_en_cours_hors_moyennes(app_client, db):
    today = _aujourdhui_paris()
    hier = (today - timedelta(days=1)).isoformat()
    await _saisir(app_client, hier, matin=600, tm=30, soir=400, ts=20)   # journée complète
    await _saisir(app_client, today.isoformat(), matin=200, tm=10)       # matin seul

    r = (await app_client.get(f"{API}/stats/resume")).json()["trente_jours"]
    assert r["total_ttc"] == pytest.approx(1200)       # le cumul compte tout
    assert r["nb_jours"] == 2
    assert r["ca_moyen_jour"] == pytest.approx(1000)   # mais la moyenne, hier seul

    p = (await app_client.get(f"{API}/stats/profil-semaine")).json()
    assert p["moyenne_glissante_7j"] == pytest.approx(1000)
    jour_type = next(j for j in p["jours"] if j["dow"] == (today.isoweekday() % 7))
    assert jour_type["nb"] == 0                        # aujourd'hui pas encore dans son jour-type


@pytest.mark.anyio
async def test_ajustement_marge_hors_suivi_quotidien(app_client, db):
    await _saisir(app_client, "2026-06-10", matin=1000)
    r = await app_client.put("/api/inventaire/marge/ca-ajuster", json={
        "date_debut": "2026-06-01", "date_fin": "2026-06-30", "montant_ttc_cible": 1300.0,
    })
    assert r.json()["ecart"] == pytest.approx(300.0)

    # Le suivi quotidien ne voit pas l'ajustement : le 30/06 reste « non saisi »
    assert (await app_client.get(f"{API}/2026-06-30")).json() is None
    cmp = (await app_client.get(f"{API}/stats/comparatif",
                                params={"date_debut": "2026-06-01", "date_fin": "2026-06-30"})).json()
    assert (cmp["courant"]["total_ttc"], cmp["courant"]["nb_jours"]) == (1000, 1)

    # Saisir ensuite le vrai CA du 30/06 n'écrase pas l'ajustement de la marge
    await _saisir(app_client, "2026-06-30", matin=200)
    marge = (await app_client.get("/api/inventaire/marge",
                                  params={"date_debut": "2026-06-01", "date_fin": "2026-06-30"})).json()
    assert marge["ca"]["ttc"] == pytest.approx(1500.0)   # 1000 + 200 + 300


@pytest.mark.anyio
async def test_migration_anciennes_lignes_ajustement(app_client, db):
    from src.database import init_db
    # Ancienne ligne d'ajustement pure + une ligne ressaisie à l'écran (gardée)
    await db.execute(
        "INSERT INTO ca_journalier (boutique_id, date_ca, montant_ttc, commentaire) "
        "VALUES (1, '2026-05-31', 250, 'Ajustement caisse/banque')")
    await db.execute(
        "INSERT INTO ca_journalier (boutique_id, date_ca, montant_ttc, montant_ttc_matin, commentaire) "
        "VALUES (1, '2026-05-30', 800, 800, 'Ajustement caisse/banque')")
    await db.commit()

    await init_db()          # rejoue les migrations

    assert (await app_client.get(f"{API}/2026-05-31")).json() is None
    assert (await app_client.get(f"{API}/2026-05-30")).json()["montant_ttc"] == 800
    cur = await db.execute("SELECT date_ca, montant_ttc FROM ca_ajustements")
    assert [tuple(r) for r in await cur.fetchall()] == [("2026-05-31", 250)]

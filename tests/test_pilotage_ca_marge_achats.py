"""
test_pilotage_ca_marge_achats.py — Marge apparente sur achats, sans inventaire,
sur 4 semaines glissantes (jusqu'à la dernière journée terminée).
"""
from datetime import timedelta

import pytest

from src.api.routes_achats import _aujourdhui_paris
from tests.test_inventaire import _article, _fournisseur, _reception_cloturee

API = "/api/achats/pilotage/ca"


@pytest.mark.anyio
async def test_marge_sur_achats_4_semaines(app_client, db):
    hier = _aujourdhui_paris() - timedelta(days=1)
    # 20 jours à 211 € TTC dans la fenêtre → 4 220 € TTC = 4 000 € HT (TVA 5,5 %)
    for n in range(20):
        r = await app_client.post(API, json={"date_ca": (hier - timedelta(days=n)).isoformat(),
                                             "montant_ttc_matin": 211})
        assert r.status_code == 201, r.text
    # 100 kg à 10 € HT/kg reçus il y a 5 jours → 1 000 € HT d'achats (prix catalogue)
    fid = await _fournisseur(app_client)
    cat = await _article(app_client, fid, prix_achat_ht=10.0, format_prix="kg")
    await _reception_cloturee(db, fid, cat, (hier - timedelta(days=4)).isoformat(), 100.0)
    # Hors fenêtre (il y a 40 jours) : ne compte pas dans les 4 dernières semaines
    await _reception_cloturee(db, fid, cat, (hier - timedelta(days=40)).isoformat(), 500.0)

    m = (await app_client.get(f"{API}/marge-achats", params={"semaines": 3})).json()
    c = m["courant"]
    assert m["tva_pct"] == 5.5
    assert c["date_fin"] == hier.isoformat()
    assert c["ca_ht"] == pytest.approx(4000.0)
    assert c["achats_ht"] == pytest.approx(1000.0)
    assert c["marge_ht"] == pytest.approx(3000.0)
    assert c["taux_marge_pct"] == pytest.approx(75.0)
    assert c["coefficient"] == pytest.approx(4.0)
    assert (c["nb_receptions"], c["nb_source_catalogue"], c["nb_sans_facture"]) == (1, 1, 1)
    assert c["exploitable"] is True

    # Fenêtre précédente : 5 000 € d'achats sans CA → pas exploitable, pas d'évolution
    assert m["precedent"]["achats_ht"] == pytest.approx(5000.0)
    assert m["precedent"]["exploitable"] is False
    assert m["evolution_taux_points"] is None
    assert len(m["historique"]) == 3 and m["historique"][-1]["date_fin"] == hier.isoformat()


@pytest.mark.anyio
async def test_marge_sur_achats_par_periode_et_depliage(app_client, db):
    fid = await _fournisseur(app_client)
    cat = await _article(app_client, fid, prix_achat_ht=10.0, format_prix="kg")
    # Août : 2 000 € HT vendus, 800 € HT achetés (60 %) ; septembre : 1 000 / 300 (70 %)
    for iso, ttc in (("2026-08-12", 2110), ("2026-09-10", 1055)):
        r = await app_client.post(API, json={"date_ca": iso, "montant_ttc_matin": ttc})
        assert r.status_code == 201, r.text
    await _reception_cloturee(db, fid, cat, "2026-08-20", 80.0)
    await _reception_cloturee(db, fid, cat, "2026-09-15", 30.0)

    url = f"{API}/marge-achats/periodes"
    mois = {l["periode"]: l for l in (await app_client.get(url, params={"granularite": "mois"})).json()["lignes"]}
    sept, aout = mois["2026-09"], mois["2026-08"]
    assert (sept["ca_ht"], sept["achats_ht"], sept["taux_marge_pct"]) == (1000.0, 300.0, 70.0)
    assert aout["taux_marge_pct"] == 60.0
    assert sept["evolution_taux_points"] == 10.0 and sept["en_cours"] is False

    # Dépliage de septembre : ses semaines (CA et achats tombent dans des semaines différentes)
    sem = (await app_client.get(url, params={"granularite": "semaine",
                                             "date_debut": "2026-09-01", "date_fin": "2026-09-30"})).json()["lignes"]
    assert [l["periode"] for l in sem] == ["2026-S38", "2026-S37"]
    assert sem[0]["ca_ht"] == 0 and sem[0]["taux_marge_pct"] is None      # achats seuls
    assert sem[1]["exploitable"] is False                                 # CA seul

    annee = (await app_client.get(url, params={"granularite": "annee"})).json()["lignes"][0]
    assert annee["periode"] == "2026"
    assert (annee["ca_ht"], annee["achats_ht"]) == (3000.0, 1100.0)
    assert (await app_client.get(url, params={"granularite": "jour"})).status_code == 400

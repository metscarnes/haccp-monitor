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

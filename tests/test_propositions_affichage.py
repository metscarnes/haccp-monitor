"""
test_propositions_affichage.py — Ce que la fenêtre « Prix à revoir » affiche pour décider :
coût d'achat avant → après, réception et bon de livraison d'origine, et « garder ».
"""

import pytest

from tests.test_prix_vente_moteur import _appliquer, _propositions, _reception, _scenario

pytestmark = pytest.mark.asyncio


async def test_proposition_porte_cout_avant_apres_et_bl_de_la_reception(app_client, db):
    s = await _scenario(app_client)              # steak 18,90 € ← cuisse 9,80 €/kg
    rid = await _reception(db, s["fid"])
    await db.execute("UPDATE receptions SET numero_bon_livraison = 'BL-778', "
                     "photo_bl_filename = 'BL-test.jpg' WHERE id = ?", (rid,))
    await db.commit()
    await _appliquer(app_client, s["a"], 10.40, rid)

    p = next(x for x in (await _propositions(app_client))["propositions"]
             if x["catalogue_vente_id"] == s["steak"])
    assert p["cout_reference"] == pytest.approx(9.80)      # avant
    assert p["cout_nouveau"] == pytest.approx(10.40)       # après
    assert p["reception_id"] == rid and p["reception_bl"] == "BL-778"
    assert p["reception_date"] and p["reception_a_photo_bl"] == 1

    # Sans photo de BL : pas de bouton « Voir le BL » (indicateur à 0).
    await db.execute("UPDATE receptions SET photo_bl_filename = NULL WHERE id = ?", (rid,))
    await db.commit()
    p = next(x for x in (await _propositions(app_client))["propositions"]
             if x["catalogue_vente_id"] == s["steak"])
    assert p["reception_a_photo_bl"] == 0


async def test_garder_le_prix_actuel(app_client, db):
    s = await _scenario(app_client)
    rid = await _reception(db, s["fid"])
    await _appliquer(app_client, s["a"], 10.40, rid)
    pid = next(x["id"] for x in (await _propositions(app_client))["propositions"]
               if x["catalogue_vente_id"] == s["steak"])
    r = await app_client.post("/api/vente/propositions-prix/decider",
                              json={"decisions": [{"proposition_id": pid, "action": "garder"}]})
    assert r.status_code == 200 and [g["catalogue_vente_id"] for g in r.json()["gardees"]] == [s["steak"]]
    restantes = [x["catalogue_vente_id"] for x in (await _propositions(app_client))["propositions"]]
    assert s["steak"] not in restantes
    assert (await app_client.get(f"/api/vente/catalogue/{s['steak']}")).json()["prix_vente_ttc"] == 18.90

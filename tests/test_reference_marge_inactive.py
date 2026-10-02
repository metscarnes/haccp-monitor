"""
test_reference_marge_inactive.py — Protection des achats de référence de marge.

Un article d'achat désactivé alors qu'il servait de référence de marge laissait la marge
calculée en silence sur un prix figé (Pintade / Haricot vert, 02/10/2026). On vérifie :
  - /catalogue/references-marge liste les produits de vente impactés (avant désactivation) ;
  - après désactivation, catalogue vente et comparateur signalent « référence inactive »
    au lieu d'afficher une marge ;
  - un article inactif ne peut plus être « meilleur » dans le comparateur.
"""
import pytest

from tests.test_liaison_vente_achat import _article, _fournisseur, _produit_vente


async def _relier(client, vente, achats, reference):
    rg = await client.post("/api/achats/comparatif/groupes/from-vente",
                           json={"catalogue_vente_id": vente})
    assert rg.status_code == 201, rg.text
    groupe = rg.json()["id"]
    for a in achats:
        rl = await client.post(f"/api/achats/comparatif/groupes/{groupe}/lignes",
                               json={"catalogue_fournisseur_id": a})
        assert rl.status_code == 201, rl.text
    rr = await client.put(f"/api/achats/comparatif/groupes/{groupe}/ventes/{vente}/reference",
                          json={"ligne_choisie_id": reference})
    assert rr.status_code == 200, rr.text
    return groupe


@pytest.mark.asyncio
async def test_reference_inactive_signalee_partout(app_client, db):
    fid = await _fournisseur(app_client, "Volailles Test")
    ancienne = await _article(app_client, fid, "3500", "Pintade fermière", prix_achat_ht=6.0)
    nouvelle = await _article(app_client, fid, "003500", "PINTADE LR", prix_achat_ht=7.9)
    vente = await _produit_vente(app_client, "Pintade", prix_vente_ttc=19.9,
                                 tva_percent=5.5, unite_vente="kg")
    groupe = await _relier(app_client, vente, [ancienne, nouvelle], reference=ancienne)

    # Avant désactivation : l'article est bien détecté comme référence de « Pintade ».
    r = await app_client.post("/api/achats/catalogue/references-marge", json={"ids": [ancienne]})
    assert r.status_code == 200, r.text
    assert [x["nom"] for x in r.json()] == ["Pintade"]
    r = await app_client.post("/api/achats/catalogue/references-marge", json={"ids": [nouvelle]})
    assert r.json() == []

    # Désactivation (soft delete).
    rd = await app_client.delete(f"/api/achats/catalogue/{ancienne}")
    assert rd.status_code == 200, rd.text

    # Catalogue vente : plus de marge, état « reference_inactive ».
    rv = await app_client.get("/api/vente/catalogue")
    p = next(x for x in rv.json() if x["id"] == vente)
    assert p["liaison_achat"] == "reference_inactive"
    assert p["marge"] is None

    # Comparateur : même signalement ; l'ancienne (6 €/kg, moins chère mais inactive)
    # n'est plus « meilleur », c'est la nouvelle active.
    rc = await app_client.get(f"/api/achats/comparatif/groupes/{groupe}")
    data = rc.json()
    pv = next(x for x in data["produits_vente"] if x["id"] == vente)
    assert pv["reference_inactive"] is True
    assert pv["marge"] is None
    meilleurs = [l["id"] for l in data["lignes"] if l["meilleur"]]
    assert meilleurs == [nouvelle]

    # Re-choisir l'achat actif rétablit la marge.
    rr = await app_client.put(f"/api/achats/comparatif/groupes/{groupe}/ventes/{vente}/reference",
                              json={"ligne_choisie_id": nouvelle})
    pv = next(x for x in rr.json()["produits_vente"] if x["id"] == vente)
    assert pv["reference_inactive"] is False
    assert pv["marge"]["marge"] == pytest.approx(19.9 / 1.055 - 7.9, abs=0.01)

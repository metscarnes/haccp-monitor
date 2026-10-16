"""
test_impression_rapide_prix.py — Popup « Imprimer les nouvelles étiquettes » après
un changement de prix de vente : impression directe au style de la boutique.

L'imprimante n'est jamais appelée : imprimer_lot est simulé.
"""
import json
from datetime import date, timedelta

import pytest

import src.printing.brother_ql_prix as brother
from tests.test_liaison_vente_achat import _produit_vente

pytestmark = pytest.mark.asyncio

STYLE_NORMAL = {"type": "normal", "lignes": [{"zone": "nom"}, {"zone": "prix"}]}


async def _style_boutique(db):
    from src.printing.brother_ql_prix import normaliser_style
    await db.execute("DELETE FROM modeles_etiquettes_prix")
    await db.execute("INSERT INTO modeles_etiquettes_prix (nom, config_json) VALUES (?, ?)",
                     ("Étiquette normale", json.dumps(normaliser_style(STYLE_NORMAL)[0])))
    await db.commit()


async def test_impression_rapide_style_normal_et_promo(app_client, db, monkeypatch):
    await _style_boutique(db)
    normal = await _produit_vente(app_client, "Rapide normal", prix_vente_ttc=12.90)
    promo = await _produit_vente(app_client, "Rapide promo", prix_vente_ttc=19.90)
    await db.execute("DELETE FROM historique_prix_vente WHERE catalogue_vente_id = ?", (promo,))
    await db.commit()
    r = await app_client.post("/api/prix-etiquettes/promos", json={
        "produit_id": promo, "prix_promo_ttc": 15.90,
        "date_fin": (date.today() + timedelta(days=7)).isoformat()})
    assert r.status_code == 201, r.text

    # Les deux étiquettes sont « à réimprimer » (prix changés)
    from src.file_etiquettes_prix import ajouter_a_la_file
    for cv in (normal, promo):
        await ajouter_a_la_file(db, cv, 1.0, 2.0, motif="test")
    await db.commit()

    async def ids_en_file():
        r = await app_client.get("/api/prix-etiquettes/a-reimprimer")
        return {e["catalogue_vente_id"] for e in r.json()["elements"]}
    assert {normal, promo} <= await ids_en_file()

    envoyees = []
    monkeypatch.setattr(brother, "imprimer_lot", lambda c: (envoyees.extend(c), (True, "ok"))[1])
    r = await app_client.post("/api/prix-etiquettes/imprimer-rapide", json={
        "produits": [{"produit_id": normal, "quantite": 2}, {"produit_id": promo, "quantite": 1}]})
    assert r.status_code == 200, r.text
    assert r.json() == {"imprimees": 3, "erreurs": []}
    assert [e["type"] for e in envoyees] == ["normal", "normal", "promo"]

    # Les produits imprimés sortent de la file « À réimprimer »
    assert not ({normal, promo} & await ids_en_file())


async def test_impression_rapide_imprimante_injoignable(app_client, db, monkeypatch):
    await _style_boutique(db)
    cv = await _produit_vente(app_client, "Rapide panne", prix_vente_ttc=9.90)
    monkeypatch.setattr(brother, "imprimer_lot", lambda c: (False, "Erreur imprimante : timeout"))
    r = await app_client.post("/api/prix-etiquettes/imprimer-rapide",
                              json={"produits": [{"produit_id": cv, "quantite": 1}]})
    assert r.status_code == 503
    assert "timeout" in r.json()["detail"]


async def test_impression_rapide_sans_style(app_client, db):
    await db.execute("DELETE FROM modeles_etiquettes_prix")
    await db.commit()
    cv = await _produit_vente(app_client, "Rapide sans style", prix_vente_ttc=9.90)
    r = await app_client.post("/api/prix-etiquettes/imprimer-rapide",
                              json={"produits": [{"produit_id": cv, "quantite": 1}]})
    assert r.status_code == 503
    assert "style" in r.json()["detail"]

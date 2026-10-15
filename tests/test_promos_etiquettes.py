"""
test_promos_etiquettes.py — Promotions sur étiquette (prix barré légal, fin automatique).

Règle testée (C. conso. L112-1-1) : le prix barré est le prix le plus bas pratiqué
pendant les 30 jours précédant la promo. La promo ne change jamais le prix du catalogue.
"""

from datetime import date, timedelta

import pytest

import src.printing.brother_ql_prix as brother
from src.promos_etiquettes import prix_reference_30j
from tests.test_liaison_vente_achat import _produit_vente

pytestmark = pytest.mark.asyncio

AUJ = date.today()


def _j(n):   # date d'il y a n jours, format historique (heure locale)
    return (AUJ - timedelta(days=n)).isoformat() + " 10:00:00"


async def _historique(db, cv, changements, prix_actuel):
    """Remplace l'historique du produit par des changements datés [(jours, ancien, nouveau)]."""
    await db.execute("DELETE FROM historique_prix_vente WHERE catalogue_vente_id = ?", (cv,))
    for jours, ancien, nouveau in changements:
        await db.execute(
            """INSERT INTO historique_prix_vente
                   (catalogue_vente_id, prix_ancien_ttc, prix_nouveau_ttc, motif, created_at)
               VALUES (?, ?, ?, 'manuel', ?)""", (cv, ancien, nouveau, _j(jours)))
    await db.execute("UPDATE catalogue_vente SET prix_vente_ttc = ? WHERE id = ?", (prix_actuel, cv))
    await db.commit()


async def _promo(client, cv, prix, fin=None):
    return await client.post("/api/prix-etiquettes/promos", json={
        "produit_id": cv, "prix_promo_ttc": prix,
        "date_fin": (fin or AUJ + timedelta(days=7)).isoformat()})


async def test_prix_de_reference_plus_bas_des_30_jours(app_client, db):
    cv = await _produit_vente(app_client, "Ref 30j", prix_vente_ttc=19.90)
    # 18,90 depuis 45 j, baisse à 17,50 il y a 20 j, hausse à 19,90 il y a 5 j.
    await _historique(db, cv, [(45, None, 18.90), (20, 18.90, 17.50), (5, 17.50, 19.90)], 19.90)
    ref = await prix_reference_30j(db, cv)
    assert ref["prix_reference_ttc"] == 17.50
    assert ref["prix_releves"] == [17.50, 18.90, 19.90]

    # Une baisse d'AVANT la fenêtre compte si elle était encore en vigueur au début.
    await _historique(db, cv, [(45, None, 18.90), (35, 18.90, 16.90), (5, 16.90, 19.90)], 19.90)
    assert (await prix_reference_30j(db, cv))["prix_reference_ttc"] == 16.90
    # Une baisse finie AVANT la fenêtre ne compte plus.
    await _historique(db, cv, [(60, None, 15.90), (40, 15.90, 19.90)], 19.90)
    assert (await prix_reference_30j(db, cv))["prix_reference_ttc"] == 19.90
    # Sans historique : le prix actuel.
    await _historique(db, cv, [], 19.90)
    assert (await prix_reference_30j(db, cv))["prix_reference_ttc"] == 19.90


async def test_promo_precedente_dans_la_fenetre_abaisse_la_reference(app_client, db):
    cv = await _produit_vente(app_client, "Ref promo", prix_vente_ttc=19.90)
    await _historique(db, cv, [], 19.90)
    await db.execute(
        """INSERT INTO promotions_etiquettes (catalogue_vente_id, prix_reference_ttc,
               prix_promo_ttc, date_debut, date_fin, statut)
           VALUES (?, 19.90, 15.90, ?, ?, 'terminee')""",
        (cv, (AUJ - timedelta(days=15)).isoformat(), (AUJ - timedelta(days=10)).isoformat()))
    await db.commit()
    assert (await prix_reference_30j(db, cv))["prix_reference_ttc"] == 15.90


async def test_creer_promo_valide_et_ne_touche_pas_au_catalogue(app_client, db):
    cv = await _produit_vente(app_client, "Steak promo", prix_vente_ttc=19.90, unite_vente="kg")
    await _historique(db, cv, [(10, 18.90, 19.90)], 19.90)

    r = await _promo(app_client, cv, 18.90)          # pas sous le plus bas des 30 j
    assert r.status_code == 422 and "18,90" in r.json()["detail"]
    r = await _promo(app_client, cv, 15.90, fin=AUJ - timedelta(days=1))
    assert r.status_code == 422

    r = await _promo(app_client, cv, 15.90)
    assert r.status_code == 201, r.text
    promo = r.json()
    assert promo["prix_reference_ttc"] == 18.90 and promo["prix_promo_ttc"] == 15.90
    assert (await app_client.get(f"/api/vente/catalogue/{cv}")).json()["prix_vente_ttc"] == 19.90

    # Modifier la promo en cours garde la référence figée et le même identifiant.
    r = await _promo(app_client, cv, 14.90, fin=AUJ + timedelta(days=3))
    assert r.json()["id"] == promo["id"] and r.json()["prix_reference_ttc"] == 18.90

    cat = (await app_client.get("/api/prix-etiquettes/catalogue?limit=2000")).json()["articles"]
    p = next(a for a in cat if a["id"] == cv)
    assert p["promo"]["prix_promo_ttc"] == 14.90 and p["promo"]["prix_reference_ttc"] == 18.90
    ref = (await app_client.get(f"/api/prix-etiquettes/promos/reference/{cv}")).json()
    assert ref["promo_en_cours"]["id"] == promo["id"]


async def test_reference_donne_la_marge_pour_juger_la_promo(app_client, db):
    from tests.test_prix_vente_moteur import _scenario
    s = await _scenario(app_client)       # steak 18,90 € ← cuisse de bœuf 9,80 €/kg HT
    ref = (await app_client.get(f"/api/prix-etiquettes/promos/reference/{s['steak']}")).json()
    m = ref["marge"]
    assert m["cout_ht"] == pytest.approx(9.80)
    assert m["taux_actuel"] == pytest.approx(1 - 9.80 / (18.90 / 1.055), abs=1e-4)
    assert m["tva_percent"] == 5.5 and m["article"] == "Cuisse de boeuf"
    assert m["fournisseur"] == "Elivia Test" and m["groupe_id"] == s["g_steak"]

    # Produit relié à aucun achat : marge inconnue (l'écran le signale).
    seul = await _produit_vente(app_client, "Sans achat", prix_vente_ttc=9.90)
    ref = (await app_client.get(f"/api/prix-etiquettes/promos/reference/{seul}")).json()
    assert ref["marge"] == {"cout_ht": None, "groupe_id": None}


async def test_impression_style_promo(app_client, db, monkeypatch):
    cv = await _produit_vente(app_client, "STEAK HACHÉ PROMO", prix_vente_ttc=19.90, unite_vente="kg")
    await _historique(db, cv, [], 19.90)
    assert (await _promo(app_client, cv, 15.90)).status_code == 201
    envoyees = []
    monkeypatch.setattr(brother, "imprimer_lot", lambda c: (envoyees.extend(c), (True, "ok"))[1])
    style = {"type": "promo", "lignes": [{"zone": "nom"}, {"zone": "prix_reference"},
                                         {"zone": "prix_promo"}, {"zone": "economie"}]}
    from src.printing.brother_ql_prix import normaliser_style
    r = await app_client.post("/api/prix-etiquettes/imprimer-masse", json={
        "config": normaliser_style(style)[0], "produits": [{"produit_id": cv, "quantite": 1}]})
    assert r.status_code == 200, r.text
    lignes = envoyees[0]["lignes"]
    assert [l["texte"] for l in lignes] == [
        "Steak haché promo", "19,90 €", "15,90 €", "Économisez 4,00 € / kg"]
    assert [l["barre"] for l in lignes] == [False, True, False, False]


async def test_fin_de_promo_remet_l_etiquette_normale_en_file(app_client, db):
    cv = await _produit_vente(app_client, "Fin promo", prix_vente_ttc=12.90)
    await _historique(db, cv, [], 12.90)
    await app_client.post("/api/prix-etiquettes/a-reimprimer/sortir", json={"produit_ids": [cv]})
    promo = (await _promo(app_client, cv, 9.90)).json()

    # Date de fin dépassée → terminée à la lecture, étiquette normale à refaire.
    await db.execute("UPDATE promotions_etiquettes SET date_fin = ? WHERE id = ?",
                     ((AUJ - timedelta(days=1)).isoformat(), promo["id"]))
    await db.commit()
    file = (await app_client.get("/api/prix-etiquettes/a-reimprimer")).json()["elements"]
    e = next(x for x in file if x["catalogue_vente_id"] == cv)
    assert e["motif"] == "fin_promo" and e["prix_ancien_ttc"] == 9.90 and e["prix_actuel_ttc"] == 12.90
    promos = (await app_client.get("/api/prix-etiquettes/promos")).json()["promos"]
    assert cv not in [p["catalogue_vente_id"] for p in promos]

    # Arrêt manuel d'une promo.
    autre = (await _promo(app_client, cv, 10.90)).json()
    r = await app_client.post(f"/api/prix-etiquettes/promos/{autre['id']}/terminer")
    assert r.status_code == 200
    r = await app_client.post(f"/api/prix-etiquettes/promos/{autre['id']}/terminer")
    assert r.status_code == 404

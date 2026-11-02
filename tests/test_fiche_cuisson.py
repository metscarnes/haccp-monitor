"""
test_fiche_cuisson.py — Fiche cuisson unique (v8.7) : cuisson + suite + refroidissement,
saisie après coup (rattrapage du soir).

Couvre les défauts relevés à l'audit du 02/11/2026 : heures incohérentes acceptées,
refroidissement daté/borné indépendamment de la cuisson, DLC du refroidi recalculée,
cuisson saignante (55 °C) déclarée « à jeter » au refroidissement.
"""

from datetime import date, timedelta

import pytest

from tests.test_production_a_cuire import (
    _article_achat, _creer_lot_recu_et_cloture, _fournisseur,
)

JOUR = (date.today() - timedelta(days=1)).isoformat()   # rattrapage de la veille


async def _lot_boeuf(app_client, db, code):
    fid = await _fournisseur(app_client, f"Fournisseur {code}")
    achat = await _article_achat(app_client, fid, code, f"Tende de tranche {code}",
                                  famille="Viande", sous_famille="Boeuf")
    rl_id, pers = await _creer_lot_recu_et_cloture(app_client, db, achat, f"LOT-{code}")
    return achat, rl_id, pers


def _fiche(achat, rl_id, pers, **kw):
    body = {
        "personnel_id": pers,
        "date_cuisson": JOUR,
        "catalogue_fournisseur_id": achat,
        "reception_ligne_id": rl_id,
        "quantite": 2.4,
    }
    body.update(kw)
    return body


@pytest.mark.anyio
async def test_fiche_ouverte_puis_completee_le_soir(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC1")

    # Dans la journée : produit + lot seulement.
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(achat, rl_id, pers))
    assert r.status_code == 201, r.text
    fiche = r.json()
    assert fiche["etat"] == "cuisson_a_saisir"
    fid = fiche["id"]

    liste = (await app_client.get("/api/cuisson/fiches")).json()
    assert any(f["id"] == fid for f in liste["a_completer"])
    # Pas encore cuite : absente du stock « à refroidir ».
    prods = (await app_client.get("/api/refroidissement/produits")).json()
    assert not any(p["catalogue_fournisseur_id"] == achat for p in prods)

    # Le soir : cuisson + refroidissement d'un coup.
    r = await app_client.put(f"/api/cuisson/fiches/{fid}", json={
        "personnel_id": pers,
        "heure_debut": "10:15", "heure_fin": "11:30", "temperature_sortie": 78,
        "suite": "refroidi",
        "refroidissement": {"heure_debut": "11:35", "heure_fin": "13:05",
                            "temperature_finale": 6},
    })
    assert r.status_code == 200, r.text
    fiche = r.json()
    assert fiche["etat"] == "terminee"
    assert fiche["refroid_duree"] == 90
    assert fiche["refroid_conforme"] == 1
    # Le refroidi garde la DLC du cuit.
    assert fiche["refroid_dlc"] == fiche["dlc_finale"]

    cur = await db.execute(
        "SELECT date_refroidissement, temperature_initiale FROM refroidissements WHERE cuisson_id = ?",
        (fid,))
    rf = await cur.fetchone()
    assert rf["date_refroidissement"] == JOUR
    assert rf["temperature_initiale"] == 78


@pytest.mark.anyio
async def test_refroidissement_avant_fin_cuisson_refuse_et_rien_enregistre(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC2")
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(
        achat, rl_id, pers,
        heure_debut="08:12", heure_fin="08:37", temperature_sortie=80,
        suite="refroidi",
        refroidissement={"heure_debut": "08:13", "heure_fin": "09:43", "temperature_finale": 5},
    ))
    assert r.status_code == 422
    assert "avant la fin de la cuisson" in r.json()["detail"]
    # Tout ou rien : la cuisson n'a pas été créée (sinon doublon au renvoi).
    cur = await db.execute("SELECT COUNT(*) FROM cuissons WHERE reception_ligne_id = ?", (rl_id,))
    assert (await cur.fetchone())[0] == 0


@pytest.mark.anyio
@pytest.mark.parametrize("debut,fin", [("11:30", "10:15"), ("10:00", "10:00")])
async def test_fin_cuisson_avant_debut_refusee(app_client, db, debut, fin):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, f"FC3{debut[:2]}{fin[:2]}")
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(
        achat, rl_id, pers, heure_debut=debut, heure_fin=fin, temperature_sortie=80))
    assert r.status_code == 422


@pytest.mark.anyio
async def test_cuisson_dans_le_futur_refusee(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC4")
    demain = (date.today() + timedelta(days=2)).isoformat()
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(
        achat, rl_id, pers, date_cuisson=demain))
    assert r.status_code == 422
    assert "futur" in r.json()["detail"]


@pytest.mark.anyio
async def test_heure_fin_sans_temperature_refusee(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC5")
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(
        achat, rl_id, pers, heure_debut="10:00", heure_fin="11:00"))
    assert r.status_code == 422


@pytest.mark.anyio
async def test_saignant_55_pas_jete_au_refroidissement(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC6")
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(
        achat, rl_id, pers,
        heure_debut="10:00", heure_fin="11:00", temperature_sortie=56,
        degre_cuisson="saignant", suite="refroidi",
        refroidissement={"heure_debut": "11:05", "heure_fin": "12:30", "temperature_finale": 8},
    ))
    assert r.status_code == 201, r.text
    fiche = r.json()
    assert fiche["conforme"] == 1
    assert fiche["refroid_conforme"] == 1
    assert fiche["refroid_jeter"] == 0


@pytest.mark.anyio
async def test_vendu_chaud_termine_la_fiche_et_sort_du_stock(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC7")
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(
        achat, rl_id, pers, heure_debut="09:00", heure_fin="10:30", temperature_sortie=82))
    assert r.status_code == 201, r.text
    fid = r.json()["id"]
    assert r.json()["etat"] == "suite_a_choisir"

    r = await app_client.put(f"/api/cuisson/fiches/{fid}",
                             json={"personnel_id": pers, "suite": "vendu_chaud"})
    assert r.status_code == 200, r.text
    assert r.json()["etat"] == "terminee"
    prods = (await app_client.get("/api/refroidissement/produits")).json()
    assert not any(p.get("catalogue_fournisseur_id") == achat for p in prods)

    # Une fois vendu chaud, plus de refroidissement possible.
    r = await app_client.put(f"/api/cuisson/fiches/{fid}", json={
        "personnel_id": pers, "suite": "refroidi",
        "refroidissement": {"heure_debut": "10:35", "heure_fin": "11:30", "temperature_finale": 5},
    })
    assert r.status_code == 422


@pytest.mark.anyio
async def test_cuisson_terminee_figee(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC8")
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(
        achat, rl_id, pers, heure_debut="09:00", heure_fin="10:00", temperature_sortie=80))
    fid = r.json()["id"]
    r = await app_client.put(f"/api/cuisson/fiches/{fid}", json={
        "personnel_id": pers, "temperature_sortie": 60, "suite": "refroidi"})
    assert r.status_code == 200, r.text
    assert r.json()["temperature_sortie"] == 80
    assert r.json()["etat"] == "refroidissement_a_saisir"


@pytest.mark.anyio
async def test_refroidissement_double_ko_impose_le_jet(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC9")
    corps = _fiche(achat, rl_id, pers,
                   heure_debut="08:00", heure_fin="09:00", temperature_sortie=80,
                   suite="refroidi",
                   refroidissement={"heure_debut": "09:00", "heure_fin": "11:30",
                                    "temperature_finale": 14})
    r = await app_client.post("/api/cuisson/fiches", json=corps)
    assert r.status_code == 422          # action corrective obligatoire
    corps["refroidissement"].update(jeter_action=True, action_corrective="Produit jeté")
    r = await app_client.post("/api/cuisson/fiches", json=corps)
    assert r.status_code == 201, r.text
    assert r.json()["refroid_jeter"] == 1


@pytest.mark.anyio
async def test_ancien_ecran_refroidissement_fin_avant_debut_refusee(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC10")
    r = await app_client.post("/api/refroidissement/enregistrements", json={
        "date_refroidissement": JOUR, "personnel_id": pers,
        "catalogue_fournisseur_id": achat,
        "heure_debut": "14:00", "heure_fin": "13:59", "temperature_finale": 5,
    })
    assert r.status_code == 422


# ── Lot 3 : stock cru, type de cuisson, rappel Hub, calendrier DLC ──────────

@pytest.mark.anyio
async def test_lot_epuise_sort_du_stock_cru_sans_sortir_la_cuisson(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC11")
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(
        achat, rl_id, pers, heure_debut="09:00", heure_fin="10:00",
        temperature_sortie=80, lot_epuise=True))
    assert r.status_code == 201, r.text
    fid = r.json()["id"]
    # Le lot cru n'est plus cuisinable…
    lots = (await app_client.get(f"/api/cuisson/lots?catalogue_fournisseur_id={achat}")).json()
    assert not any(l["reception_ligne_id"] == rl_id for l in lots)
    # …mais la cuisson, elle, reste en stock (pas de sortie en cascade).
    cur = await db.execute(
        "SELECT source_type, statut FROM dlc_devenir WHERE (source_type, source_id) IN "
        "(('reception_ligne', ?), ('cuisson', ?))", (rl_id, fid))
    assert [tuple(r) for r in await cur.fetchall()] == [("reception_ligne", "consomme")]
    prods = (await app_client.get("/api/refroidissement/produits")).json()
    assert any(p.get("catalogue_fournisseur_id") == achat for p in prods)


@pytest.mark.anyio
async def test_lot_partiel_reste_cuisinable(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC12")
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(achat, rl_id, pers, lot_epuise=False))
    assert r.status_code == 201, r.text
    lots = (await app_client.get(f"/api/cuisson/lots?catalogue_fournisseur_id={achat}")).json()
    assert any(l["reception_ligne_id"] == rl_id for l in lots)


@pytest.mark.anyio
async def test_type_cuisson(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC13")
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(achat, rl_id, pers, type_cuisson="four"))
    assert r.status_code == 201, r.text
    assert r.json()["type_cuisson"] == "four"
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(achat, rl_id, pers, type_cuisson="barbecue"))
    assert r.status_code == 422


@pytest.mark.anyio
async def test_hub_rappelle_les_fiches_a_completer(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC14")
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(achat, rl_id, pers))
    fid = r.json()["id"]
    hub = (await app_client.get("/api/hub/taches-resume")).json()["aujourd_hui"]
    assert "cuisson_a_completer" in [t["code"] for t in hub]

    # On termine toutes les fiches encore ouvertes (y compris celles des autres tests).
    liste = (await app_client.get("/api/cuisson/fiches")).json()["a_completer"]
    for f in liste:
        corps = {"personnel_id": pers, "suite": "vendu_chaud"}
        if f["etat"] == "cuisson_a_saisir":
            corps.update(heure_debut="09:00", heure_fin="10:00", temperature_sortie=80)
        if f["etat"] == "refroidissement_a_saisir":
            corps = {"personnel_id": pers, "refroidissement": {
                "heure_debut": f["heure_fin"], "heure_fin": "23:59", "temperature_finale": 5,
                "action_corrective": "Contrôlé"}}
        rr = await app_client.put(f"/api/cuisson/fiches/{f['id']}", json=corps)
        assert rr.status_code == 200, rr.text
    hub = (await app_client.get("/api/hub/taches-resume")).json()["aujourd_hui"]
    assert "cuisson_a_completer" not in [t["code"] for t in hub]
    assert fid


@pytest.mark.anyio
async def test_calendrier_dlc_montre_les_cuissons_catalogue(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC15")
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(
        achat, rl_id, pers, heure_debut="09:00", heure_fin="10:00", temperature_sortie=80))
    fiche = r.json()
    cal = (await app_client.get("/api/dlc/calendrier", params={
        "date_debut": JOUR, "date_fin": fiche["dlc_finale"], "source": "cuisson"})).json()
    items = cal if isinstance(cal, list) else cal.get("items", [])
    assert any(i["source_id"] == fiche["id"] and i["produit_nom"] for i in items), cal


# ── Suppression d'une fiche ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_supprimer_fiche_sans_mesure_libre_et_lot_rendu(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC16")
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(achat, rl_id, pers, lot_epuise=True))
    fid = r.json()["id"]
    lots = (await app_client.get(f"/api/cuisson/lots?catalogue_fournisseur_id={achat}")).json()
    assert not any(l["reception_ligne_id"] == rl_id for l in lots)

    r = await app_client.post(f"/api/cuisson/fiches/{fid}/supprimer", json={"motif": "Mauvais produit"})
    assert r.status_code == 200, r.text
    assert (await app_client.get(f"/api/cuisson/fiches/{fid}")).status_code == 404
    # Le lot cru revient en stock.
    lots = (await app_client.get(f"/api/cuisson/lots?catalogue_fournisseur_id={achat}")).json()
    assert any(l["reception_ligne_id"] == rl_id for l in lots)


@pytest.mark.anyio
async def test_supprimer_fiche_avec_mesures_exige_mot_de_passe_admin(app_client, db):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, "FC17")
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(
        achat, rl_id, pers, heure_debut="09:00", heure_fin="10:00", temperature_sortie=80,
        suite="refroidi",
        refroidissement={"heure_debut": "10:05", "heure_fin": "11:30", "temperature_finale": 6}))
    fid = r.json()["id"]

    _mdp_admin()
    for corps in ({}, {"password": "faux"}):
        r = await app_client.post(f"/api/cuisson/fiches/{fid}/supprimer", json=corps)
        assert r.status_code == 401
    assert (await app_client.get(f"/api/cuisson/fiches/{fid}")).status_code == 200

    r = await app_client.post(f"/api/cuisson/fiches/{fid}/supprimer",
                              json={"password": _mdp_admin()})
    assert r.status_code == 200, r.text
    cur = await db.execute("SELECT COUNT(*) FROM refroidissements WHERE cuisson_id = ?", (fid,))
    assert (await cur.fetchone())[0] == 0


# ── Correction d'une fiche terminée ────────────────────────────────────────

def _mdp_admin():
    import os
    from src.api import routes_auth
    routes_auth._login_tentatives.clear()   # limite anti-brute-force partagée entre tests
    return os.environ["ADMIN_PASSWORD"]


async def _fiche_refroidie(app_client, db, code, **kw):
    achat, rl_id, pers = await _lot_boeuf(app_client, db, code)
    corps = _fiche(achat, rl_id, pers, heure_debut="09:00", heure_fin="10:00",
                   temperature_sortie=80, suite="refroidi",
                   refroidissement={"heure_debut": "10:05", "heure_fin": "11:30",
                                    "temperature_finale": 6})
    corps.update(kw)
    r = await app_client.post("/api/cuisson/fiches", json=corps)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.anyio
async def test_corriger_date_heures_et_temperatures(app_client, db):
    fiche = await _fiche_refroidie(app_client, db, "FC18")
    fid = fiche["id"]
    avant_hier = (date.today() - timedelta(days=2)).isoformat()

    _mdp_admin()
    r = await app_client.post(f"/api/cuisson/fiches/{fid}/corriger", json={"date_cuisson": avant_hier})
    assert r.status_code == 401          # mot de passe administrateur obligatoire

    r = await app_client.post(f"/api/cuisson/fiches/{fid}/corriger", json={
        "password": _mdp_admin(), "motif": "Saisie sur la mauvaise date",
        "date_cuisson": avant_hier, "heure_fin": "10:20", "temperature_sortie": 79,
        "refroidissement": {"heure_debut": "10:25", "heure_fin": "11:40", "temperature_finale": 5},
    })
    assert r.status_code == 200, r.text
    f = r.json()
    assert (f["date_cuisson"], f["heure_fin"], f["temperature_sortie"]) == (avant_hier, "10:20", 79)
    assert (f["refroid_debut"], f["refroid_fin"], f["refroid_temperature"]) == ("10:25", "11:40", 5)
    assert f["refroid_duree"] == 75
    # DLC recalculée (J+3 de la nouvelle date) et reprise par le refroidi.
    assert f["dlc_finale"] == (date.today() + timedelta(days=1)).isoformat()
    assert f["refroid_dlc"] == f["dlc_finale"]
    cur = await db.execute("SELECT date_refroidissement FROM refroidissements WHERE id = ?", (f["refroid_id"],))
    assert (await cur.fetchone())[0] == avant_hier
    assert f["etiquette_a_reimprimer"] is False


@pytest.mark.anyio
async def test_corriger_signale_etiquette_a_reimprimer(app_client, db):
    fiche = await _fiche_refroidie(app_client, db, "FC19")
    await db.execute(
        """INSERT INTO etiquettes_generees (boutique_id, produit_nom, type_date, date_etiquette,
               dlc, operateur, numero_lot, lot_type, source_type, source_id)
           VALUES (1, 'Rosbeef', 'fabrication', ?, ?, 'Test', 'LOT', 'interne', 'refroidissement', ?)""",
        (JOUR, fiche["refroid_dlc"], fiche["refroid_id"]))
    await db.commit()
    avant_hier = (date.today() - timedelta(days=2)).isoformat()
    r = await app_client.post(f"/api/cuisson/fiches/{fiche['id']}/corriger",
                              json={"password": _mdp_admin(), "date_cuisson": avant_hier})
    assert r.status_code == 200, r.text
    assert r.json()["etiquette_a_reimprimer"] is True


@pytest.mark.anyio
async def test_corriger_refuse_les_incoherences(app_client, db):
    fiche = await _fiche_refroidie(app_client, db, "FC20")
    url = f"/api/cuisson/fiches/{fiche['id']}/corriger"
    # Fin de cuisson après la mise au froid.
    r = await app_client.post(url, json={"password": _mdp_admin(), "heure_fin": "10:30"})
    assert r.status_code == 422
    # Correction qui ferait jeter un produit gardé.
    r = await app_client.post(url, json={"password": _mdp_admin(), "refroidissement": {
        "heure_fin": "13:00", "temperature_finale": 15, "action_corrective": "x"}})
    assert r.status_code == 422
    assert "jeter" in r.json()["detail"]
    # Rien n'a changé.
    f = (await app_client.get(f"/api/cuisson/fiches/{fiche['id']}")).json()
    assert (f["heure_fin"], f["refroid_fin"]) == ("10:00", "11:30")


@pytest.mark.anyio
async def test_produits_disponibles_signalent_la_derniere_cuisson(app_client, db):
    achat_a, rl_a, pers = await _lot_boeuf(app_client, db, "FC21")
    achat_b, rl_b, _ = await _lot_boeuf(app_client, db, "FC22")
    # Un lot reçu sans DLC est « en attente », hors stock : on la complète.
    dlc = (date.today() + timedelta(days=5)).isoformat()
    await db.execute("UPDATE reception_lignes SET dlc = ?, statut = 'complet' WHERE id IN (?, ?)",
                     (dlc, rl_a, rl_b))
    await db.commit()
    r = await app_client.post("/api/cuisson/fiches", json=_fiche(achat_b, rl_b, pers, lot_epuise=False))
    assert r.status_code == 201, r.text
    prods = {p["catalogue_fournisseur_id"]: p
             for p in (await app_client.get("/api/cuisson/produits-disponibles")).json()}
    assert prods[achat_b]["derniere_cuisson"] == JOUR
    assert prods[achat_b]["rang_utilisation"] == r.json()["id"]
    assert prods[achat_a]["derniere_cuisson"] is None
    assert prods[achat_a]["rang_utilisation"] == 0

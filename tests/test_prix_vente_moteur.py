"""
test_prix_vente_moteur.py — Socle « prix de vente à marge maintenue » (étape 1).

Couvre :
  - les calculs purs : arrondi ,90 (le plus proche par défaut, égalité → supérieur), prix
    cible pour un taux / un coef / une marge €, proposition complète (hausse, baisse non
    pré-cochée, hausse absorbée par l'arrondi, jamais à contre-sens, achat gratuit) ;
  - l'historique : chaque chemin qui écrit le prix de vente (création, fiche, comparateur)
    trace l'ancien → nouveau prix avec la marge ;
  - les propositions : nées d'une MAJ de prix d'achat (réception, fiche article, inventaire,
    changement d'achat de référence), une seule en attente par produit avec la marge de
    référence figée, annulée si le coût revient, remplacée si le prix change ailleurs ;
  - les décisions (appliquer / garder), réservées à l'admin.

Cas chiffré de référence (plan validé le 04/10/2026) : cuisse de bœuf 9,80 → 10,40 €/kg ;
steak haché 18,90 € (marge 45,3 %) → 19,90 € ; bourguignon 15,90 € → 16,90 €.
"""
import pytest

from src.prix_vente import (
    arrondi_terminaison, candidats_terminaison, prix_cible_ttc, proposer_prix_vente,
    taux_marque, terminaison_du_prix,
)
from tests.test_liaison_vente_achat import _article, _fournisseur, _produit_vente
from tests.test_reference_marge_inactive import _relier


# ───────────────────────────────────────────────────────────────────────────
#  Calculs purs
# ───────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("prix,attendu", [
    (20.057145, 19.90),     # cas steak haché : prix exact 20,06 → 19,90
    (18.37, 17.90),         # 0,47 sous 17,90… contre 0,53 jusqu'à 18,90
    (18.45, 18.90),
    (18.95, 18.90),
    (19.40, 19.90),         # égalité parfaite → supérieur (on protège la marge)
    (18.90, 18.90),         # déjà en ,90
    (0.50, 0.90),           # jamais sous 0,90
    (18.899999999, 18.90),  # bruit de float neutralisé
])
def test_arrondi_90_le_plus_proche(prix, attendu):
    assert arrondi_terminaison(prix) == attendu


def test_arrondi_sens_et_terminaison():
    assert arrondi_terminaison(18.37, sens="superieur") == 18.90
    assert arrondi_terminaison(18.37, sens="inferieur") == 17.90
    assert arrondi_terminaison(18.95, sens="superieur") == 19.90
    assert arrondi_terminaison(18.95, sens="inferieur") == 18.90
    assert arrondi_terminaison(0.50, sens="inferieur") == 0.90   # pas de ,90 en dessous
    assert arrondi_terminaison(18.37, sens="aucun") == 18.37
    assert arrondi_terminaison(2.675, sens="aucun") == 2.68      # demi supérieur, pas bancaire
    assert arrondi_terminaison(18.37, terminaison=0.50) == 18.50
    assert arrondi_terminaison(0) is None
    assert arrondi_terminaison(None) is None


def test_candidats_terminaison():
    assert candidats_terminaison(20.06) == {"inferieur": 19.90, "superieur": 20.90}
    assert candidats_terminaison(18.90) == {"inferieur": 18.90, "superieur": 18.90}
    assert candidats_terminaison(0.40) == {"inferieur": None, "superieur": 0.90}
    assert candidats_terminaison(2.14, terminaison=0.0) == {"inferieur": 2.0, "superieur": 3.0}


@pytest.mark.parametrize("prix,attendu", [
    (18.90, 0.90), (2.99, 0.99), (32.95, 0.95), (2.00, 0.00), (12.50, 0.50),
    (13.47, 0.90),          # pas de terminaison commerciale → défaut ,90
    (None, 0.90),
])
def test_terminaison_du_prix(prix, attendu):
    assert terminaison_du_prix(prix) == pytest.approx(attendu)


def test_proposition_garde_la_terminaison_99():
    # Saucisse cocktail 8,99 € : +5 % de coût → prix exact 9,44 → reste 8,99 (absorbée).
    p = proposer_prix_vente(prix_actuel_ttc=8.99, tva=5.5, cout_reference=4.00,
                            cout_nouveau=4.20, terminaison=0.99)
    assert p["prix_propose_ttc"] == 8.99 and p["absorbee"]
    # +10 % cumulés → prix exact 9,89 → 9,99 (et non 9,90).
    p2 = proposer_prix_vente(prix_actuel_ttc=8.99, tva=5.5, cout_reference=4.00,
                             cout_nouveau=4.40, terminaison=0.99)
    assert p2["prix_propose_ttc"] == 9.99
    assert p2["terminaison"] == 0.99


def test_prix_cible_taux_coef_marge():
    taux = taux_marque(18.90, 5.5, 9.80)
    assert taux == pytest.approx(0.45296, abs=1e-4)
    # Même taux de marque sur le nouveau coût : 10,40 / (1 − 0,45296) × 1,055 ≈ 20,06 €.
    assert prix_cible_ttc(10.40, 5.5, taux=taux) == pytest.approx(20.0571, abs=1e-3)
    # Garder le taux ≡ garder le coef (HT/HT).
    coef = (18.90 / 1.055) / 9.80
    assert prix_cible_ttc(10.40, 5.5, coef=coef) == pytest.approx(20.0571, abs=1e-3)
    # Marge HT en € constante : 18,90/1,055 − 9,80 = 8,11 € gardés sur le nouveau coût.
    marge = 18.90 / 1.055 - 9.80
    assert prix_cible_ttc(10.40, 5.5, marge_ht=marge) == pytest.approx((10.40 + marge) * 1.055)
    assert prix_cible_ttc(10.0, 5.5, taux=1.0) is None


def test_proposition_hausse_steak_hache():
    p = proposer_prix_vente(prix_actuel_ttc=18.90, tva=5.5, cout_reference=9.80, cout_nouveau=10.40)
    assert p["sens_variation"] == "hausse"
    assert p["variation_cout_pct"] == pytest.approx(6.12, abs=0.01)
    assert p["prix_exact_ttc"] == pytest.approx(20.057, abs=0.001)
    assert p["prix_propose_ttc"] == 19.90
    assert p["prix_alternatif_ttc"] == 20.90
    assert p["taux_reference"] == pytest.approx(0.4530, abs=1e-4)
    assert p["taux_propose"] == pytest.approx(0.4486, abs=1e-4)
    assert p["taux_alternatif"] == pytest.approx(0.4750, abs=1e-4)
    assert p["taux_sans_changer"] == pytest.approx(0.4195, abs=1e-4)   # si on ne touche à rien
    assert p["changement"] and p["pre_coche"] and not p["absorbee"]
    assert not p["alerte_unite"]


def test_proposition_sens_superieur():
    p = proposer_prix_vente(prix_actuel_ttc=18.90, tva=5.5, cout_reference=9.80,
                            cout_nouveau=10.40, sens="superieur")
    assert p["prix_propose_ttc"] == 20.90
    assert p["prix_alternatif_ttc"] == 19.90


def test_proposition_hausse_absorbee_puis_cumulee():
    # 6,90 € ; coût 3,00 → 3,10 : prix exact 7,13 → le ,90 le plus proche reste 6,90.
    p = proposer_prix_vente(prix_actuel_ttc=6.90, tva=5.5, cout_reference=3.00, cout_nouveau=3.10)
    assert p["prix_propose_ttc"] == 6.90
    assert p["absorbee"] and not p["changement"] and not p["pre_coche"]
    # Les hausses se cumulent sur la même référence : à 3,40 le prix exact (7,82) → 7,90.
    p2 = proposer_prix_vente(prix_actuel_ttc=6.90, tva=5.5, cout_reference=3.00, cout_nouveau=3.40)
    assert p2["prix_propose_ttc"] == 7.90
    assert p2["changement"]


def test_proposition_baisse_non_precochee():
    p = proposer_prix_vente(prix_actuel_ttc=18.90, tva=5.5, cout_reference=10.40, cout_nouveau=9.80)
    assert p["sens_variation"] == "baisse"
    assert p["prix_propose_ttc"] == 17.90
    assert p["changement"] and not p["pre_coche"]       # décision : on garde le prix par défaut
    p2 = proposer_prix_vente(prix_actuel_ttc=18.90, tva=5.5, cout_reference=10.40,
                             cout_nouveau=9.80, precocher_baisse=True)
    assert p2["pre_coche"]


def test_proposition_politique_marge_euro():
    p = proposer_prix_vente(prix_actuel_ttc=18.90, tva=5.5, cout_reference=9.80,
                            cout_nouveau=10.40, politique="euro")
    assert p["politique"] == "euro"
    assert p["prix_exact_ttc"] == pytest.approx(18.90 + 0.60 * 1.055, abs=1e-3)   # 19,53
    assert p["prix_propose_ttc"] == 19.90


def test_proposition_achat_gratuit_bascule_marge_euro():
    # Achat à 0 € (gratuit) : 100 % de marque intenable dès que le coût n'est plus nul.
    p = proposer_prix_vente(prix_actuel_ttc=4.90, tva=5.5, cout_reference=0.0, cout_nouveau=0.50)
    assert p["politique"] == "euro"
    assert p["prix_propose_ttc"] == 5.90
    # 0 € était peut-être un prix jamais saisi : alerte, jamais cochée d'office.
    assert p["alerte_achat_gratuit"] and p["changement"] and not p["pre_coche"]


def test_proposition_jamais_a_contre_sens():
    # Prix actuel non aligné (18,10) + légère hausse : le ,90 le plus proche (17,90) ferait
    # BAISSER le prix alors que le coût monte → on propose le ,90 supérieur.
    p = proposer_prix_vente(prix_actuel_ttc=18.10, tva=5.5, cout_reference=10.0, cout_nouveau=10.05)
    assert p["prix_propose_ttc"] == 18.90
    assert p["prix_alternatif_ttc"] == 17.90


def test_proposition_alerte_unite_jamais_precochee():
    # +200 % : typiquement un prix au colis saisi comme un prix au kilo (cas réels de
    # l'audit : quiche poireau / rillette de canard 34,90 → 106,90).
    p = proposer_prix_vente(prix_actuel_ttc=9.90, tva=5.5, cout_reference=4.40, cout_nouveau=13.20)
    assert p["alerte_unite"] and p["changement"] and not p["pre_coche"]
    # Juste sous le seuil (+18,6 %, vraie hausse de la longe de porc) : cochée normalement.
    p2 = proposer_prix_vente(prix_actuel_ttc=18.90, tva=5.5, cout_reference=10.0, cout_nouveau=11.86)
    assert not p2["alerte_unite"] and p2["pre_coche"]


# ───────────────────────────────────────────────────────────────────────────
#  Scénario base de données
# ───────────────────────────────────────────────────────────────────────────

async def _scenario(client):
    """Cuisse de bœuf (9,80 €/kg) = achat de référence du steak haché (18,90 €) et du
    bourguignon (15,90 €) ; tende de tranche (12 €/kg) = référence du rôti (témoin)."""
    fid = await _fournisseur(client, "Elivia Test")
    a = await _article(client, fid, "A01", "Cuisse de boeuf", prix_achat_ht=9.80, format_prix="kg")
    b = await _article(client, fid, "B01", "Tende de tranche", prix_achat_ht=12.0, format_prix="kg")
    steak = await _produit_vente(client, "Steak haché", prix_vente_ttc=18.90,
                                 tva_percent=5.5, unite_vente="kg")
    bourgui = await _produit_vente(client, "Bourguignon", prix_vente_ttc=15.90,
                                   tva_percent=5.5, unite_vente="kg")
    roti = await _produit_vente(client, "Rôti", prix_vente_ttc=26.90,
                                tva_percent=5.5, unite_vente="kg")
    s = {"fid": fid, "a": a, "b": b, "steak": steak, "bourgui": bourgui, "roti": roti}
    s["g_steak"] = await _relier(client, steak, [a], reference=a)
    s["g_bourgui"] = await _relier(client, bourgui, [a], reference=a)
    s["g_roti"] = await _relier(client, roti, [b], reference=b)
    return s


async def _reception(db, fid):
    await db.execute(
        "INSERT OR IGNORE INTO personnel (id, boutique_id, prenom, actif) VALUES (1, 1, 'Test', 1)"
    )
    cur = await db.execute(
        """INSERT INTO receptions (personnel_id, heure_reception, fournisseur_principal_id, statut)
           VALUES (1, '08:00', ?, 'en_cours')""",
        (fid,),
    )
    await db.commit()
    return cur.lastrowid


async def _appliquer(client, article_id, prix, reception_id=None):
    r = await client.post(f"/api/achats/catalogue/{article_id}/appliquer-prix",
                          json={"nouveau_prix_ht": prix, "reception_id": reception_id})
    assert r.status_code == 200, r.text
    return r.json()


async def _propositions(client, **params):
    r = await client.get("/api/vente/propositions-prix", params=params)
    assert r.status_code == 200, r.text
    return r.json()


async def _prix_vente(client, cv_id):
    r = await client.get(f"/api/vente/catalogue/{cv_id}")
    return r.json()["prix_vente_ttc"]


async def _historique(client, cv_id):
    r = await client.get(f"/api/vente/catalogue/{cv_id}/historique-prix")
    assert r.status_code == 200, r.text
    return r.json()["historique"]


async def _statut(db, cv_id):
    cur = await db.execute(
        "SELECT statut, prix_decide_ttc FROM propositions_prix_vente WHERE catalogue_vente_id = ? "
        "ORDER BY id DESC LIMIT 1", (cv_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


# ───────────────────────────────────────────────────────────────────────────
#  Historique des prix de vente
# ───────────────────────────────────────────────────────────────────────────

async def test_creation_et_fiche_historisees(app_client, db):
    s = await _scenario(app_client)
    r = await app_client.put(f"/api/vente/catalogue/{s['steak']}", json={"prix_vente_ttc": 19.90})
    assert r.status_code == 200, r.text
    assert r.json()["prix_vente_ttc"] == 19.90
    # Même prix renvoyé : aucune nouvelle ligne.
    await app_client.put(f"/api/vente/catalogue/{s['steak']}", json={"prix_vente_ttc": 19.9})

    h = await _historique(app_client, s["steak"])
    assert [x["motif"] for x in h] == ["manuel", "creation"]
    assert h[0]["prix_ancien_ttc"] == 18.90 and h[0]["prix_nouveau_ttc"] == 19.90
    assert h[0]["cout_matiere"] == pytest.approx(9.80)
    assert h[0]["taux_marge_avant"] == pytest.approx(0.4530, abs=1e-4)
    assert h[0]["taux_marge_apres"] == pytest.approx(1 - 9.80 / (19.90 / 1.055), abs=1e-4)
    assert h[0]["role"] == "admin"
    assert h[1]["prix_ancien_ttc"] is None and h[1]["prix_nouveau_ttc"] == 18.90


async def test_prix_modifie_dans_le_comparateur_historise(app_client, db):
    s = await _scenario(app_client)
    r = await app_client.put(f"/api/achats/comparatif/groupes/{s['g_steak']}/ventes/{s['steak']}",
                             json={"prix_vente_ttc": 20.50})
    assert r.status_code == 200, r.text
    assert await _prix_vente(app_client, s["steak"]) == 20.50
    h = await _historique(app_client, s["steak"])
    assert h[0]["motif"] == "comparateur"
    assert h[0]["prix_ancien_ttc"] == 18.90 and h[0]["prix_nouveau_ttc"] == 20.50


# ───────────────────────────────────────────────────────────────────────────
#  Propositions
# ───────────────────────────────────────────────────────────────────────────

async def test_maj_prix_achat_reception_cree_les_propositions(app_client, db):
    s = await _scenario(app_client)
    rid = await _reception(db, s["fid"])
    res = await _appliquer(app_client, s["a"], 10.40, rid)
    assert len(res["propositions_prix_vente"]) == 2

    data = await _propositions(app_client, reception_id=rid)
    par_produit = {p["catalogue_vente_id"]: p for p in data["propositions"]}
    assert set(par_produit) == {s["steak"], s["bourgui"]}     # le rôti (autre achat) n'est pas touché
    steak = par_produit[s["steak"]]
    assert steak["origine"] == "reception"
    assert steak["cout_reference"] == pytest.approx(9.80)
    assert steak["cout_nouveau"] == pytest.approx(10.40)
    assert steak["article_designation"] == "Cuisse de boeuf"
    assert steak["proposition"]["prix_propose_ttc"] == 19.90
    assert steak["proposition"]["pre_coche"] is True
    assert par_produit[s["bourgui"]]["proposition"]["prix_propose_ttc"] == 16.90
    assert data["compteurs"]["a_decider"] == 2
    assert data["reglages"]["sens"] == "proche"
    # Rien n'est appliqué sans décision.
    assert await _prix_vente(app_client, s["steak"]) == 18.90


async def test_chaine_complete_depuis_la_cloture_de_reception(app_client, db):
    """BL à 10,40 €/kg → clôture → écart détecté → « Mettre à jour » → proposition 19,90."""
    s = await _scenario(app_client)
    rid = await _reception(db, s["fid"])
    await db.execute(
        """INSERT INTO reception_lignes
               (reception_id, catalogue_fournisseur_id, poids_kg, prix_unitaire_ht, statut, conforme)
           VALUES (?, ?, 12.5, 10.40, 'complet', 1)""",
        (rid, s["a"]),
    )
    await db.commit()
    r = await app_client.put(f"/api/receptions/{rid}/cloturer", json={})
    assert r.status_code == 200, r.text

    ecarts = (await app_client.get(f"/api/achats/catalogue/ecarts-prix/{rid}")).json()["ecarts"]
    assert [e["catalogue_fournisseur_id"] for e in ecarts] == [s["a"]]
    # La clôture seule ne propose rien : le prix de référence n'a pas encore changé.
    assert (await _propositions(app_client, reception_id=rid))["propositions"] == []

    await _appliquer(app_client, s["a"], ecarts[0]["prix_constate"], rid)
    data = await _propositions(app_client, reception_id=rid)
    steak = next(p for p in data["propositions"] if p["catalogue_vente_id"] == s["steak"])
    assert steak["proposition"]["prix_propose_ttc"] == 19.90


async def test_deux_hausses_gardent_la_marge_de_reference(app_client, db):
    s = await _scenario(app_client)
    rid1 = await _reception(db, s["fid"])
    rid2 = await _reception(db, s["fid"])
    await _appliquer(app_client, s["a"], 10.40, rid1)
    await _appliquer(app_client, s["a"], 11.00, rid2)

    cur = await db.execute("SELECT * FROM propositions_prix_vente WHERE catalogue_vente_id = ?",
                           (s["steak"],))
    lignes = [dict(x) for x in await cur.fetchall()]
    assert len(lignes) == 1                        # une seule proposition en attente
    p = lignes[0]
    assert p["statut"] == "en_attente"
    assert p["reception_id"] == rid2               # rattachée à la dernière réception
    assert p["cout_reference"] == pytest.approx(9.80)
    assert p["cout_nouveau"] == pytest.approx(11.00)
    assert p["taux_reference"] == pytest.approx(0.4530, abs=1e-4)

    data = await _propositions(app_client)
    steak = next(x for x in data["propositions"] if x["catalogue_vente_id"] == s["steak"])
    # 11,00 / (1 − 0,45296) × 1,055 = 21,21 → 20,90 (le plus proche)
    assert steak["proposition"]["prix_propose_ttc"] == 20.90


async def test_retour_au_cout_de_reference_annule_la_proposition(app_client, db):
    s = await _scenario(app_client)
    await _appliquer(app_client, s["a"], 10.40)
    await _appliquer(app_client, s["a"], 9.80)
    assert (await _statut(db, s["steak"]))["statut"] == "annulee"
    data = await _propositions(app_client)
    assert data["propositions"] == []


async def test_hausse_absorbee_reste_en_attente_et_se_cumule(app_client, db):
    fid = await _fournisseur(app_client, "Volailler Test")
    art = await _article(app_client, fid, "V01", "Haut de cuisse", prix_achat_ht=3.00, format_prix="kg")
    vente = await _produit_vente(app_client, "Haut de cuisse", prix_vente_ttc=6.90,
                                 tva_percent=5.5, unite_vente="kg")
    await _relier(app_client, vente, [art], reference=art)

    await _appliquer(app_client, art, 3.10)
    data = await _propositions(app_client)
    assert data["compteurs"]["a_decider"] == 0
    assert data["compteurs"]["absorbees"] == 1
    assert data["propositions"][0]["proposition"]["prix_propose_ttc"] == 6.90

    await _appliquer(app_client, art, 3.40)
    data = await _propositions(app_client)
    assert data["compteurs"]["a_decider"] == 1
    p = data["propositions"][0]
    assert p["cout_reference"] == pytest.approx(3.00)       # la référence n'a pas glissé
    assert p["proposition"]["prix_propose_ttc"] == 7.90


async def _decider(client, decisions):
    r = await client.post("/api/vente/propositions-prix/decider", json={"decisions": decisions})
    assert r.status_code == 200, r.text
    return r.json()


async def test_baisse_gardee_puis_remontee_ne_propose_rien(app_client, db):
    """Effet cliquet (trouvé à la lecture de l'audit du 05/10/2026) : coût 9,80 → 9,20
    (prix gardé) puis 9,20 → 9,80 ne doit RIEN proposer — le coût est revenu à celui du
    prix fixé. Avant correction, la référence glissait sur la baisse et on proposait une
    hausse sans raison."""
    s = await _scenario(app_client)
    await _appliquer(app_client, s["a"], 9.20)
    data = await _propositions(app_client)
    steak = next(p for p in data["propositions"] if p["catalogue_vente_id"] == s["steak"])
    assert steak["proposition"]["sens_variation"] == "baisse"
    assert steak["proposition"]["pre_coche"] is False          # baisse : prix gardé par défaut
    await _decider(app_client, [{"proposition_id": p["id"], "action": "garder"}
                                for p in data["propositions"]])

    res = await _appliquer(app_client, s["a"], 9.80)            # retour au coût de départ
    assert res["propositions_prix_vente"] == []
    assert (await _propositions(app_client))["propositions"] == []

    await _appliquer(app_client, s["a"], 10.40)                 # vraie hausse ensuite
    data = await _propositions(app_client)
    steak = next(p for p in data["propositions"] if p["catalogue_vente_id"] == s["steak"])
    assert steak["cout_reference"] == pytest.approx(9.80)        # pas 9,20
    assert steak["proposition"]["prix_propose_ttc"] == 19.90


async def test_baisse_affichee_pour_information_seulement(app_client, db):
    """Décision 06/10/2026 : une baisse de coût n'est PAS « à décider » (pas de badge) ;
    elle est listée pour information (catégorie baisse_info), jamais cochée."""
    s = await _scenario(app_client)
    await _appliquer(app_client, s["a"], 9.20)
    data = await _propositions(app_client)
    assert data["compteurs"]["a_decider"] == 0
    assert data["compteurs"]["baisses"] == 2
    assert {p["categorie"] for p in data["propositions"]} == {"baisse_info"}
    assert all(p["proposition"]["pre_coche"] is False for p in data["propositions"])

    await _appliquer(app_client, s["a"], 10.40)          # devient une hausse → à décider
    data = await _propositions(app_client)
    assert data["compteurs"]["a_decider"] == 2
    assert {p["categorie"] for p in data["propositions"]} == {"a_decider"}


async def test_reference_est_le_dernier_prix_fixe(app_client, db):
    s = await _scenario(app_client)
    # Prix fixé à la main à 19,90 avec un coût de 9,80 → c'est la nouvelle marge de référence.
    r = await app_client.put(f"/api/vente/catalogue/{s['steak']}", json={"prix_vente_ttc": 19.90})
    assert r.status_code == 200, r.text

    await _appliquer(app_client, s["a"], 10.40)
    data = await _propositions(app_client)
    steak = next(p for p in data["propositions"] if p["catalogue_vente_id"] == s["steak"])
    assert steak["prix_vente_reference_ttc"] == 19.90
    assert steak["cout_reference"] == pytest.approx(9.80)
    # 10,40 / (1 − 0,48045) × 1,055 = 21,12 → 20,90
    assert steak["proposition"]["prix_propose_ttc"] == 20.90

    # « Garder » ne déplace pas la référence : la hausse suivante repart de 19,90 / 9,80.
    await _decider(app_client, [{"proposition_id": steak["id"], "action": "garder"}])
    await _appliquer(app_client, s["a"], 11.00)
    data = await _propositions(app_client)
    steak = next(p for p in data["propositions"] if p["catalogue_vente_id"] == s["steak"])
    assert steak["cout_reference"] == pytest.approx(9.80)
    assert steak["proposition"]["prix_propose_ttc"] == 21.90     # 11,00 → prix exact 22,34


async def test_terminaison_du_produit_conservee(app_client, db):
    fid = await _fournisseur(app_client, "Charcutier Test")
    art = await _article(app_client, fid, "S01", "Saucisse cocktail", prix_achat_ht=4.00, format_prix="kg")
    vente = await _produit_vente(app_client, "Saucisse cocktail", prix_vente_ttc=8.99,
                                 tva_percent=5.5, unite_vente="kg")
    await _relier(app_client, vente, [art], reference=art)
    await _appliquer(app_client, art, 4.40)

    prop = (await _propositions(app_client))["propositions"][0]["proposition"]
    assert prop["terminaison"] == 0.99
    assert prop["prix_propose_ttc"] == 9.99              # garde sa fin en ,99

    # Réglage boutique « tout en ,90 » : même proposition → 9,90.
    r = await app_client.put("/api/vente/reglages-prix", json={"garder_terminaison": False})
    assert r.status_code == 200 and r.json()["garder_terminaison"] is False
    prop = (await _propositions(app_client))["propositions"][0]["proposition"]
    assert prop["prix_propose_ttc"] == 9.90


async def test_decider_appliquer_et_garder(app_client, db):
    s = await _scenario(app_client)
    rid = await _reception(db, s["fid"])
    await _appliquer(app_client, s["a"], 10.40, rid)
    data = await _propositions(app_client, reception_id=rid)
    pid = {p["catalogue_vente_id"]: p["id"] for p in data["propositions"]}

    corps = {"decisions": [
        {"proposition_id": pid[s["steak"]], "action": "appliquer"},       # prix proposé
        {"proposition_id": pid[s["bourgui"]], "action": "garder"},
    ]}
    r = await app_client.post("/api/vente/propositions-prix/decider", json=corps)
    assert r.status_code == 200, r.text
    res = r.json()
    assert [x["catalogue_vente_id"] for x in res["appliquees"]] == [s["steak"]]
    assert [x["catalogue_vente_id"] for x in res["gardees"]] == [s["bourgui"]]
    assert res["erreurs"] == []

    assert await _prix_vente(app_client, s["steak"]) == 19.90
    assert await _prix_vente(app_client, s["bourgui"]) == 15.90
    h = await _historique(app_client, s["steak"])
    assert h[0]["motif"] == "proposition"
    assert h[0]["proposition_id"] == pid[s["steak"]]
    assert h[0]["reception_id"] == rid
    assert (await _statut(db, s["steak"])) == {"statut": "appliquee", "prix_decide_ttc": 19.90}
    assert (await _statut(db, s["bourgui"])) == {"statut": "gardee", "prix_decide_ttc": 15.90}

    # Une proposition déjà traitée ne se rejoue pas.
    r = await app_client.post("/api/vente/propositions-prix/decider", json=corps)
    assert len(r.json()["erreurs"]) == 2
    assert (await _propositions(app_client))["propositions"] == []


async def test_decider_prix_choisi_et_reserve_admin(app_client, db):
    s = await _scenario(app_client)
    await _appliquer(app_client, s["a"], 10.40)
    data = await _propositions(app_client)
    pid = next(p["id"] for p in data["propositions"] if p["catalogue_vente_id"] == s["steak"])
    corps = {"decisions": [{"proposition_id": pid, "action": "appliquer", "prix_ttc": 20.90}]}

    # Un compte équipe voit les propositions mais ne change pas les prix.
    from src.api.routes_auth import _make_token
    equipe = {"Authorization": f"Bearer {_make_token('equipe')}"}
    r = await app_client.get("/api/vente/propositions-prix", headers=equipe)
    assert r.status_code == 200
    r = await app_client.post("/api/vente/propositions-prix/decider", json=corps, headers=equipe)
    assert r.status_code == 403
    assert await _prix_vente(app_client, s["steak"]) == 18.90

    # L'admin applique l'autre ,90 (20,90 au lieu de 19,90).
    r = await app_client.post("/api/vente/propositions-prix/decider", json=corps)
    assert r.status_code == 200, r.text
    assert await _prix_vente(app_client, s["steak"]) == 20.90


async def test_prix_change_ailleurs_remplace_la_proposition(app_client, db):
    s = await _scenario(app_client)
    await _appliquer(app_client, s["a"], 10.40)
    r = await app_client.put(f"/api/vente/catalogue/{s['steak']}", json={"prix_vente_ttc": 20.50})
    assert r.status_code == 200, r.text
    assert (await _statut(db, s["steak"])) == {"statut": "remplacee", "prix_decide_ttc": 20.50}
    # Le bourguignon, non retouché, attend toujours.
    assert (await _statut(db, s["bourgui"]))["statut"] == "en_attente"


async def test_fiche_article_achat_cree_les_propositions(app_client, db):
    s = await _scenario(app_client)
    r = await app_client.put(f"/api/achats/catalogue/{s['a']}", json={"prix_achat_ht": 10.40})
    assert r.status_code == 200, r.text
    data = await _propositions(app_client)
    assert {p["catalogue_vente_id"] for p in data["propositions"]} == {s["steak"], s["bourgui"]}
    assert all(p["origine"] == "catalogue_achat" and p["reception_id"] is None
               for p in data["propositions"])
    # Un champ sans effet sur le coût ne touche pas aux propositions.
    r = await app_client.put(f"/api/achats/catalogue/{s['a']}", json={"designation": "Cuisse de boeuf FR"})
    assert r.status_code == 200, r.text
    assert (await _propositions(app_client))["compteurs"]["total"] == 2


async def test_prix_kg_inventaire_cree_les_propositions(app_client, db):
    s = await _scenario(app_client)
    r = await app_client.put(f"/api/inventaire/catalogue/{s['a']}/prix-kg", json={"prix_kg": 10.40})
    assert r.status_code == 200, r.text
    data = await _propositions(app_client)
    assert {p["origine"] for p in data["propositions"]} == {"inventaire"}
    assert data["compteurs"]["a_decider"] == 2


async def test_changement_achat_de_reference_cree_la_proposition(app_client, db):
    fid = await _fournisseur(app_client, "Grossiste Test")
    a = await _article(app_client, fid, "A01", "Cuisse de boeuf A", prix_achat_ht=9.80, format_prix="kg")
    c = await _article(app_client, fid, "C01", "Cuisse de boeuf C", prix_achat_ht=11.00, format_prix="kg")
    steak = await _produit_vente(app_client, "Steak haché", prix_vente_ttc=18.90,
                                 tva_percent=5.5, unite_vente="kg")
    g = await _relier(app_client, steak, [a, c], reference=a)

    r = await app_client.put(f"/api/achats/comparatif/groupes/{g}/ventes/{steak}/reference",
                             json={"ligne_choisie_id": c})
    assert r.status_code == 200, r.text
    data = await _propositions(app_client)
    p = data["propositions"][0]
    assert p["origine"] == "reference"
    assert p["cout_reference"] == pytest.approx(9.80) and p["cout_nouveau"] == pytest.approx(11.00)

    # Retour à l'achat d'origine : le coût revient à la référence → proposition annulée.
    await app_client.put(f"/api/achats/comparatif/groupes/{g}/ventes/{steak}/reference",
                         json={"ligne_choisie_id": a})
    assert (await _statut(db, steak))["statut"] == "annulee"


async def test_reglages_arrondi(app_client, db):
    r = await app_client.put("/api/vente/reglages-prix", json={"sens": "superieur"})
    assert r.status_code == 200, r.text
    assert r.json()["sens"] == "superieur"
    s = await _scenario(app_client)
    await _appliquer(app_client, s["a"], 10.40)
    data = await _propositions(app_client)
    steak = next(p for p in data["propositions"] if p["catalogue_vente_id"] == s["steak"])
    assert steak["proposition"]["prix_propose_ttc"] == 20.90

    r = await app_client.put("/api/vente/reglages-prix", json={"sens": "au_hasard"})
    assert r.status_code == 422
    r = await app_client.put("/api/vente/reglages-prix", json={"terminaison": 1.5})
    assert r.status_code == 422

"""
test_production_a_cuire.py — Détection automatique "prêt à cuire"

Couvre le circuit Réception → Cuisson pour les produits reçus déjà préparés
(ex. Lasagne, Gratin dauphinois, Parmentier de canard) marqués
`suivi_cuisson_auto` sur le produit de VENTE (catalogue_vente), relié à
l'article d'achat reçu via le groupe comparatif :

- GET /api/cuisson/a-traiter liste les lots reçus/clôturés pas encore cuits
- Le lot disparaît de la liste dès qu'une cuisson lui est liée
- GET /api/hub/taches-resume répercute le compteur sur la tuile Hub

v7.6 (28/08/2026) : réécrit sur le catalogue achats/vente. La version
d'origine testait `produits.suivi_cuisson_auto`, référentiel abandonné
depuis la migration v6.0 (vide pour tout le stock réel) — voir
POINT_CHAINE_CUISSON_REFROIDISSEMENT.md.
"""

import pytest


async def _fournisseur(client, nom):
    r = await client.post("/api/achats/fournisseurs", json={"nom": nom})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _article_achat(client, fournisseur_id, code, designation, **kw):
    body = {
        "fournisseur_id": fournisseur_id,
        "code_article": code,
        "designation": designation,
        "prix_achat_ht": kw.pop("prix_achat_ht", 10.0),
        "format_prix": kw.pop("format_prix", "kg"),
    }
    body.update(kw)
    r = await client.post("/api/achats/catalogue", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _produit_vente(client, nom, suivi_cuisson_auto=False, **kw):
    body = {"nom": nom, "suivi_cuisson_auto": suivi_cuisson_auto}
    body.update(kw)
    r = await client.post("/api/vente/catalogue", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _relier_achat_a_vente(client, catalogue_vente_id, catalogue_fournisseur_id):
    """Reproduit le flux de la modale « Relier à un article d'achat » : crée le
    groupe comparatif depuis le produit de vente, puis y rattache l'article
    d'achat — c'est ce lien que GET /api/cuisson/a-traiter exploite."""
    rg = await client.post("/api/achats/comparatif/groupes/from-vente",
                            json={"catalogue_vente_id": catalogue_vente_id})
    assert rg.status_code == 201, rg.text
    groupe_id = rg.json()["id"]
    rl = await client.post(f"/api/achats/comparatif/groupes/{groupe_id}/lignes",
                            json={"catalogue_fournisseur_id": catalogue_fournisseur_id})
    assert rl.status_code == 201, rl.text
    return groupe_id


async def _creer_personnel(db, prenom="TestOperateur"):
    # SEED_SQL ne pré-remplit pas la table personnel (contrairement à boutiques) :
    # chaque test crée le sien plutôt que de dépendre d'une ligne préexistante.
    cur = await db.execute(
        "INSERT INTO personnel (boutique_id, prenom, actif) VALUES (1, ?, 1)",
        (prenom,),
    )
    await db.commit()
    return cur.lastrowid


async def _creer_lot_recu_et_cloture(app_client, db, catalogue_fournisseur_id, numero_lot,
                                      designation_libre="Article test"):
    personnel_id = await _creer_personnel(db, f"Op-{numero_lot}")

    r = await app_client.post("/api/receptions", data={
        "personnel_id":    str(personnel_id),
        "heure_reception": "08:00",
    })
    assert r.status_code == 201, r.text
    reception_id = r.json()["id"]

    # Comme le vrai front (reception.js) : designation_libre toujours envoyée en
    # complément de catalogue_fournisseur_id — l'API l'exige (produit_id absent).
    r2 = await app_client.post(f"/api/receptions/{reception_id}/lignes", json={
        "catalogue_fournisseur_id": catalogue_fournisseur_id,
        "designation_libre": designation_libre,
        "numero_lot": numero_lot,
    })
    assert r2.status_code == 201, r2.text
    reception_ligne_id = r2.json()["id"]

    r3 = await app_client.put(f"/api/receptions/{reception_id}/cloturer", json={})
    assert r3.status_code == 200, r3.text

    return reception_ligne_id, personnel_id


async def _creer_plat_suivi_auto(app_client, nom, code_article):
    """Crée le trio complet : fournisseur → article d'achat → produit de vente
    marqué suivi_cuisson_auto=1, reliés via le groupe comparatif. Renvoie
    (catalogue_fournisseur_id, catalogue_vente_id)."""
    fid = await _fournisseur(app_client, f"Fournisseur {nom}")
    achat = await _article_achat(app_client, fid, code_article, nom,
                                  prix_achat_ht=8.0, format_prix="kg")
    vente = await _produit_vente(app_client, nom, suivi_cuisson_auto=True)
    await _relier_achat_a_vente(app_client, vente, achat)
    return achat, vente


@pytest.mark.anyio
async def test_lot_apparait_dans_a_traiter(app_client, db):
    achat, vente = await _creer_plat_suivi_auto(app_client, "Lasagne (test A)", "LASA-A")
    await _creer_lot_recu_et_cloture(app_client, db, achat, "LOT-A-001")

    r = await app_client.get("/api/cuisson/a-traiter")
    assert r.status_code == 200
    lots = r.json()
    assert any(
        l["catalogue_fournisseur_id"] == achat
        and l["catalogue_vente_id"] == vente
        and l["numero_lot"] == "LOT-A-001"
        for l in lots
    )


@pytest.mark.anyio
async def test_lot_disparait_apres_cuisson(app_client, db):
    achat, vente = await _creer_plat_suivi_auto(app_client, "Lasagne (test B)", "LASA-B")
    reception_ligne_id, personnel_id = await _creer_lot_recu_et_cloture(
        app_client, db, achat, "LOT-B-001",
    )

    r = await app_client.get("/api/cuisson/a-traiter")
    assert any(l["reception_ligne_id"] == reception_ligne_id for l in r.json())

    r2 = await app_client.post("/api/cuisson/enregistrements", json={
        "type_cuisson":             "rotissoire",
        "date_cuisson":              "2026-06-12",
        "personnel_id":              personnel_id,
        "catalogue_fournisseur_id":  achat,
        "catalogue_vente_id":        vente,
        "reception_ligne_id":        reception_ligne_id,
        "heure_debut":               "09:00",
        "heure_fin":                 "09:25",
        "temperature_sortie":        75.5,
    })
    assert r2.status_code == 201, r2.text

    r3 = await app_client.get("/api/cuisson/a-traiter")
    assert not any(l["reception_ligne_id"] == reception_ligne_id for l in r3.json())


@pytest.mark.anyio
async def test_produit_non_marque_absent_de_a_traiter(app_client, db):
    # Produit "normal" (suivi_cuisson_auto=0 par défaut) : ne doit jamais apparaître,
    # même reçu et clôturé, tant que la case n'est pas cochée dans le catalogue vente.
    fid = await _fournisseur(app_client, "Fournisseur bœuf test")
    achat = await _article_achat(app_client, fid, "COTE-TEST", "Côte de bœuf (test auto)",
                                  prix_achat_ht=20.0, format_prix="kg")
    vente = await _produit_vente(app_client, "Côte de bœuf (test auto)", suivi_cuisson_auto=False)
    await _relier_achat_a_vente(app_client, vente, achat)

    await _creer_lot_recu_et_cloture(app_client, db, achat, "LOT-C-001")

    r = await app_client.get("/api/cuisson/a-traiter")
    assert not any(l["catalogue_fournisseur_id"] == achat for l in r.json())


@pytest.mark.anyio
async def test_hub_resume_signale_production_a_cuire(app_client, db):
    achat, vente = await _creer_plat_suivi_auto(app_client, "Lasagne (test D)", "LASA-D")
    await _creer_lot_recu_et_cloture(app_client, db, achat, "LOT-D-001")

    r = await app_client.get("/api/hub/taches-resume")
    assert r.status_code == 200
    codes = [t["code"] for t in r.json()["aujourd_hui"]]
    assert "production_a_cuire" in codes


@pytest.mark.anyio
async def test_a_traiter_expose_le_produit_receptionne(app_client, db):
    # Le détail (front) doit pouvoir distinguer l'article reçu (catalogue achats)
    # du produit fini (catalogue vente), notamment quand les noms diffèrent.
    achat, vente = await _creer_plat_suivi_auto(app_client, "Gratin dauphinois (test E)", "GRAT-E")
    await _creer_lot_recu_et_cloture(app_client, db, achat, "LOT-E-001")

    r = await app_client.get("/api/cuisson/a-traiter")
    lot = next(l for l in r.json() if l["catalogue_fournisseur_id"] == achat)
    assert lot["article_designation"] == "Gratin dauphinois (test E)"
    assert lot["article_code"] == "GRAT-E"
    assert lot["produit_nom"] == "Gratin dauphinois (test E)"
    assert lot["reception_id"] is not None


@pytest.mark.anyio
async def test_exclusion_retire_le_lot_et_reintegration_le_remet(app_client, db):
    achat, vente = await _creer_plat_suivi_auto(app_client, "Lasagne (test F)", "LASA-F")
    reception_ligne_id, _ = await _creer_lot_recu_et_cloture(app_client, db, achat, "LOT-F-001")

    r = await app_client.get("/api/cuisson/a-traiter")
    assert any(l["reception_ligne_id"] == reception_ligne_id for l in r.json())

    rex = await app_client.post(
        f"/api/cuisson/a-traiter/{reception_ligne_id}/exclure",
        json={"motif": "Mauvais rattachement catalogue"},
    )
    assert rex.status_code == 200, rex.text

    r2 = await app_client.get("/api/cuisson/a-traiter")
    assert not any(l["reception_ligne_id"] == reception_ligne_id for l in r2.json())

    rlist = await app_client.get("/api/cuisson/a-traiter/exclusions")
    assert rlist.status_code == 200
    exclus = rlist.json()
    lot_exclu = next(l for l in exclus if l["reception_ligne_id"] == reception_ligne_id)
    assert lot_exclu["motif"] == "Mauvais rattachement catalogue"

    rre = await app_client.post(f"/api/cuisson/a-traiter/{reception_ligne_id}/reintegrer")
    assert rre.status_code == 200, rre.text

    r3 = await app_client.get("/api/cuisson/a-traiter")
    assert any(l["reception_ligne_id"] == reception_ligne_id for l in r3.json())

    rlist2 = await app_client.get("/api/cuisson/a-traiter/exclusions")
    assert not any(l["reception_ligne_id"] == reception_ligne_id for l in rlist2.json())


@pytest.mark.anyio
async def test_exclure_lot_inexistant_404(app_client):
    r = await app_client.post("/api/cuisson/a-traiter/999999/exclure", json={})
    assert r.status_code == 404

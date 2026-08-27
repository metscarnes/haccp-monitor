"""
test_production_a_cuire.py — Détection automatique "prêt à cuire"

Couvre le circuit Réception → Cuisson pour les produits reçus déjà préparés
(ex. Lasagne, Gratin dauphinois, Parmentier de canard) marqués
`suivi_cuisson_auto` dans le catalogue :

- GET /api/cuisson/a-traiter liste les lots reçus/clôturés pas encore cuits
- Le lot disparaît de la liste dès qu'une cuisson lui est liée
- GET /api/hub/taches-resume répercute le compteur sur la tuile Hub
"""

import pytest


async def _creer_produit_suivi_auto(db, code_unique="LASAGNE_TEST"):
    await db.execute(
        """
        INSERT OR IGNORE INTO produits
            (nom, code_unique, categorie, conditionnement, dlc_jours,
             boutique_id, temperature_conservation, type_produit, suivi_cuisson_auto)
        VALUES ('Lasagne (test)', ?, 'traiteur', 'BARQUETTE', 0,
                1, '0°C à +4°C', 'fini', 1)
        """,
        (code_unique,),
    )
    await db.commit()
    cur = await db.execute("SELECT id FROM produits WHERE code_unique=?", (code_unique,))
    return (await cur.fetchone())[0]


async def _creer_personnel(db, prenom="TestOperateur"):
    # SEED_SQL ne pré-remplit pas la table personnel (contrairement à boutiques) :
    # chaque test crée le sien plutôt que de dépendre d'une ligne préexistante.
    cur = await db.execute(
        "INSERT INTO personnel (boutique_id, prenom, actif) VALUES (1, ?, 1)",
        (prenom,),
    )
    await db.commit()
    return cur.lastrowid


async def _creer_lot_recu_et_cloture(app_client, db, produit_id, numero_lot):
    personnel_id = await _creer_personnel(db, f"Op-{numero_lot}")

    r = await app_client.post("/api/receptions", data={
        "personnel_id":    str(personnel_id),
        "heure_reception": "08:00",
    })
    assert r.status_code == 201, r.text
    reception_id = r.json()["id"]

    r2 = await app_client.post(f"/api/receptions/{reception_id}/lignes", json={
        "produit_id": produit_id,
        "numero_lot": numero_lot,
    })
    assert r2.status_code == 201, r2.text
    reception_ligne_id = r2.json()["id"]

    r3 = await app_client.put(f"/api/receptions/{reception_id}/cloturer", json={})
    assert r3.status_code == 200, r3.text

    return reception_ligne_id, personnel_id


@pytest.mark.anyio
async def test_lot_apparait_dans_a_traiter(app_client, db):
    produit_id = await _creer_produit_suivi_auto(db, "LASAGNE_A")
    await _creer_lot_recu_et_cloture(app_client, db, produit_id, "LOT-A-001")

    r = await app_client.get("/api/cuisson/a-traiter")
    assert r.status_code == 200
    lots = r.json()
    assert any(l["produit_id"] == produit_id and l["numero_lot"] == "LOT-A-001" for l in lots)


@pytest.mark.anyio
async def test_lot_disparait_apres_cuisson(app_client, db):
    produit_id = await _creer_produit_suivi_auto(db, "LASAGNE_B")
    reception_ligne_id, personnel_id = await _creer_lot_recu_et_cloture(
        app_client, db, produit_id, "LOT-B-001",
    )

    r = await app_client.get("/api/cuisson/a-traiter")
    assert any(l["reception_ligne_id"] == reception_ligne_id for l in r.json())

    r2 = await app_client.post("/api/cuisson/enregistrements", json={
        "type_cuisson":       "rotissoire",
        "date_cuisson":       "2026-06-12",
        "personnel_id":       personnel_id,
        "produit_id":         produit_id,
        "reception_ligne_id": reception_ligne_id,
        "heure_debut":        "09:00",
        "heure_fin":          "09:25",
        "temperature_sortie": 75.5,
    })
    assert r2.status_code == 201, r2.text

    r3 = await app_client.get("/api/cuisson/a-traiter")
    assert not any(l["reception_ligne_id"] == reception_ligne_id for l in r3.json())


@pytest.mark.anyio
async def test_produit_non_marque_absent_de_a_traiter(app_client, db):
    # Produit "normal" (suivi_cuisson_auto=0 par défaut) : ne doit jamais apparaître,
    # même reçu et clôturé, tant que la case n'est pas cochée dans le catalogue.
    await db.execute(
        """
        INSERT OR IGNORE INTO produits
            (nom, code_unique, categorie, conditionnement, dlc_jours,
             boutique_id, temperature_conservation, type_produit)
        VALUES ('Côte de bœuf (test auto)', 'NON_AUTO_TEST', 'matiere_premiere', 'SOUS_VIDE', 0,
                1, '0°C à +4°C', 'brut')
        """
    )
    await db.commit()
    cur = await db.execute("SELECT id FROM produits WHERE code_unique='NON_AUTO_TEST'")
    produit_id = (await cur.fetchone())[0]

    await _creer_lot_recu_et_cloture(app_client, db, produit_id, "LOT-C-001")

    r = await app_client.get("/api/cuisson/a-traiter")
    assert not any(l["produit_id"] == produit_id for l in r.json())


@pytest.mark.anyio
async def test_hub_resume_signale_production_a_cuire(app_client, db):
    produit_id = await _creer_produit_suivi_auto(db, "LASAGNE_D")
    await _creer_lot_recu_et_cloture(app_client, db, produit_id, "LOT-D-001")

    r = await app_client.get("/api/hub/taches-resume")
    assert r.status_code == 200
    codes = [t["code"] for t in r.json()["aujourd_hui"]]
    assert "production_a_cuire" in codes

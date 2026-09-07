"""
test_nuisibles.py — Module IPM (lutte contre nuisibles)

Couvre :
- /api/nuisibles/carte/resume : les pièges réellement installés sur le plan,
  qui pilotent les colonnes du registre et la saisie (rapide et individuelle).
- La désactivation de l'espèce « Oiseaux » : elle n'est plus attendue dans le
  contrôle hebdomadaire remonté par le Hub.
"""

import pytest

from src.api.routes_hub import NUISIBLES_TYPES, NUISIBLES_TYPES_DESACTIVES
from src.api.routes_nuisibles import TYPES_DESACTIVES


@pytest.fixture
async def carte_vide(db):
    """Base propre : aucun piège positionné sur le plan."""
    await db.execute("DELETE FROM nuisibles_pieges_carte")
    await db.commit()
    return db


# ---------------------------------------------------------------------------
# Mémoire des pièges installés via le plan
# ---------------------------------------------------------------------------

async def test_resume_vide_quand_aucun_piege_place(app_client, carte_vide):
    r = await app_client.get("/api/nuisibles/carte/resume")
    assert r.status_code == 200
    assert r.json()["pieges_par_type"] == {}


async def test_resume_retourne_les_pieges_places_par_type(app_client, carte_vide):
    """Le plan fait foi : le résumé rend les numéros placés, triés, par espèce."""
    await app_client.post("/api/nuisibles/carte", json={
        "type_id": 1,
        "pieges": [
            {"piege_num": 5, "pos_x": 50.0, "pos_y": 20.0},
            {"piege_num": 1, "pos_x": 10.0, "pos_y": 12.5},
            {"piege_num": 2, "pos_x": 30.0, "pos_y": 80.0},
        ],
    })
    await app_client.post("/api/nuisibles/carte", json={
        "type_id": 2,
        "pieges": [{"piege_num": 3, "pos_x": 60.0, "pos_y": 40.0}],
    })

    r = await app_client.get("/api/nuisibles/carte/resume")
    assert r.status_code == 200
    assert r.json()["pieges_par_type"] == {"1": [1, 2, 5], "2": [3]}


async def test_resume_suit_le_retrait_d_un_piege(app_client, carte_vide):
    """Retirer un piège du plan le retire aussi de la liste à saisir."""
    await app_client.post("/api/nuisibles/carte", json={
        "type_id": 1,
        "pieges": [
            {"piege_num": 1, "pos_x": 10.0, "pos_y": 10.0},
            {"piege_num": 2, "pos_x": 20.0, "pos_y": 20.0},
        ],
    })
    await app_client.post("/api/nuisibles/carte", json={
        "type_id": 1,
        "pieges": [{"piege_num": 1, "pos_x": 10.0, "pos_y": 10.0}],
    })

    r = await app_client.get("/api/nuisibles/carte/resume")
    assert r.json()["pieges_par_type"] == {"1": [1]}


# ---------------------------------------------------------------------------
# Espèce « Oiseaux » désactivée
# ---------------------------------------------------------------------------

def test_oiseaux_desactive_partout():
    """Les deux listes de désactivation doivent rester alignées (type 4)."""
    assert TYPES_DESACTIVES == {4}
    assert NUISIBLES_TYPES_DESACTIVES == TYPES_DESACTIVES
    assert NUISIBLES_TYPES[4] == "Oiseaux"


async def test_hub_ne_reclame_pas_les_oiseaux(app_client, db):
    """Le rappel hebdomadaire du Hub ne doit plus attendre de contrôle oiseaux."""
    r = await app_client.get("/api/hub/taches-resume")
    assert r.status_code == 200

    taches = [t for t in r.json()["aujourd_hui"] if t["code"] == "nuisibles"]
    # La tâche n'apparaît que le lundi : on ne vérifie son contenu que si elle est là.
    for tache in taches:
        assert "Oiseaux" not in tache["detail"]

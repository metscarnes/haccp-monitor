"""
test_database.py — Tests de la couche SQLite (insert, lecture, stats)
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone

from src.database import (
    insert_releve, get_latest_releve, get_releves, get_stats_releves,
    get_enceinte, get_enceinte_by_zigbee_id,
    ouvrir_alerte, fermer_alerte, get_alerte_en_cours, get_alertes_en_cours,
    get_dashboard_boutique,
)

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Relevés
# ---------------------------------------------------------------------------

async def test_insert_et_lecture_releve(db):
    rid = await insert_releve(db, 1, 3.2, 75.0, 95, 110)
    assert rid > 0

    dernier = await get_latest_releve(db, 1)
    assert dernier is not None
    assert dernier["temperature"] == 3.2
    assert dernier["humidite"] == 75.0
    assert dernier["batterie"] == 95


async def test_plusieurs_releves_ordre_chronologique(db):
    now = datetime.now(timezone.utc)
    for i, temp in enumerate([2.5, 3.0, 3.8]):
        ts = now - timedelta(minutes=10 - i * 5)
        await insert_releve(db, 1, temp, 70.0, 90, 100, ts)

    # Le dernier retourné doit être le plus récent
    dernier = await get_latest_releve(db, 1)
    assert dernier["temperature"] == 3.8


async def test_get_releves_filtre_par_periode(db):
    now = datetime.now(timezone.utc)
    # Relevé ancien (hors fenêtre)
    await insert_releve(db, 2, 4.0, 80.0, 88, 100, now - timedelta(hours=25))
    # Relevé récent (dans la fenêtre)
    await insert_releve(db, 2, 3.5, 78.0, 88, 100, now - timedelta(hours=1))

    depuis = now - timedelta(hours=24)
    releves = await get_releves(db, 2, depuis)
    temps = [r["temperature"] for r in releves]
    assert 3.5 in temps
    assert 4.0 not in temps


async def test_stats_min_max_moy(db):
    now = datetime.now(timezone.utc)
    depuis = now - timedelta(hours=1)
    for temp in [2.0, 3.0, 4.0]:
        await insert_releve(db, 3, temp, 65.0, 90, 100, now - timedelta(minutes=30))

    stats = await get_stats_releves(db, 3, depuis)
    assert stats["temp_min"] == pytest.approx(2.0, abs=0.01)
    assert stats["temp_max"] == pytest.approx(4.0, abs=0.01)
    assert stats["temp_moy"] == pytest.approx(3.0, abs=0.01)
    assert stats["nb_releves"] >= 3


# ---------------------------------------------------------------------------
# Enceintes
# ---------------------------------------------------------------------------

async def test_get_enceinte_by_zigbee_id(db):
    enc = await get_enceinte_by_zigbee_id(db, "chambre_froide_1")
    assert enc is not None
    assert enc["id"] == 1
    assert enc["seuil_temp_max"] == 4.0


async def test_get_enceinte_zigbee_inconnu(db):
    enc = await get_enceinte_by_zigbee_id(db, "sonde_inconnue_xyz")
    assert enc is None


async def test_seuils_enceintes_par_defaut(db):
    """Vérifie que les seuils HACCP sont bien configurés pour chaque enceinte."""
    for eid, seuil_max in [(1, 4.0), (2, 4.0), (3, 4.0)]:
        enc = await get_enceinte(db, eid)
        assert enc["seuil_temp_min"] == 0.0
        assert enc["seuil_temp_max"] == seuil_max

    # Laboratoire : seuils différents
    labo = await get_enceinte(db, 4)
    assert labo["seuil_temp_min"] == 10.0
    assert labo["seuil_temp_max"] == 15.0


# ---------------------------------------------------------------------------
# Alertes
# ---------------------------------------------------------------------------

async def test_ouvrir_et_fermer_alerte(db):
    now = datetime.now(timezone.utc)
    aid = await ouvrir_alerte(db, 1, "temperature_haute", 6.2, 4.0, now)
    assert aid > 0

    # L'alerte est bien ouverte
    alerte = await get_alerte_en_cours(db, 1, "temperature_haute")
    assert alerte is not None
    assert alerte["valeur"] == 6.2
    assert alerte["fin"] is None

    # Fermer l'alerte
    await fermer_alerte(db, aid, now + timedelta(minutes=15))

    # Elle ne doit plus être "en cours"
    alerte_fermee = await get_alerte_en_cours(db, 1, "temperature_haute")
    assert alerte_fermee is None


async def test_une_seule_alerte_ouverte_par_type(db):
    now = datetime.now(timezone.utc)
    await ouvrir_alerte(db, 2, "temperature_basse", -0.5, 0.0, now)
    await ouvrir_alerte(db, 2, "temperature_basse", -0.8, 0.0, now + timedelta(minutes=1))

    # get_alerte_en_cours retourne la plus récente — on vérifie qu'il en existe bien une
    alerte = await get_alerte_en_cours(db, 2, "temperature_basse")
    assert alerte is not None


async def test_alertes_en_cours_multi_enceintes(db):
    now = datetime.now(timezone.utc)
    await ouvrir_alerte(db, 1, "perte_signal", 20.0, 15.0, now)
    await ouvrir_alerte(db, 3, "batterie_faible", 15.0, 20.0, now)

    alertes = await get_alertes_en_cours(db)
    eids = [a["enceinte_id"] for a in alertes]
    assert 1 in eids
    assert 3 in eids


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

async def test_dashboard_retourne_4_enceintes(db):
    data = await get_dashboard_boutique(db, 1)
    assert data["boutique"]["id"] == 1
    assert len(data["enceintes"]) == 4


async def test_dashboard_statut_ok_sans_alerte(db):
    now = datetime.now(timezone.utc)
    # Injecter une température dans les seuils
    await insert_releve(db, 1, 2.5, 75.0, 95, 110, now)
    data = await get_dashboard_boutique(db, 1)
    enceinte_1 = next(e for e in data["enceintes"] if e["id"] == 1)
    assert enceinte_1["statut"] in ("ok", "attention")


async def test_dashboard_statut_alerte_si_hors_seuil(db):
    now = datetime.now(timezone.utc)
    # Température hors seuil + alerte ouverte
    await insert_releve(db, 2, 7.5, 80.0, 90, 100, now)
    await ouvrir_alerte(db, 2, "temperature_haute", 7.5, 4.0, now)
    data = await get_dashboard_boutique(db, 1)
    enceinte_2 = next(e for e in data["enceintes"] if e["id"] == 2)
    assert enceinte_2["statut"] == "alerte"
    assert enceinte_2["alerte_en_cours"] is not None

"""
test_alerts.py — Tests de la logique d'alertes (seuils, délais, notifications)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from src.database import (
    insert_releve, ouvrir_alerte, fermer_alerte,
    get_alerte_en_cours, marquer_alerte_notifiee,
)

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enceinte(seuil_min=0.0, seuil_max=4.0, delai=5, eid=1):
    return {
        "id": eid, "nom": "Test enceinte",
        "type": "chambre_froide_positive",
        "seuil_temp_min": seuil_min,
        "seuil_temp_max": seuil_max,
        "delai_alerte_minutes": delai,
    }


# ---------------------------------------------------------------------------
# Tests logique de seuils (via mqtt_subscriber._verifier_seuils)
# ---------------------------------------------------------------------------

async def test_temperature_haute_ouvre_alerte(db):
    from src.mqtt_subscriber import _verifier_seuils
    enc = _enceinte(seuil_max=4.0)
    now = datetime.now(timezone.utc)

    await _verifier_seuils(db, enc, temperature=5.5, humidite=78, batterie=90, now=now)

    alerte = await get_alerte_en_cours(db, 1, "temperature_haute")
    assert alerte is not None
    assert alerte["valeur"] == pytest.approx(5.5)
    assert alerte["seuil"] == pytest.approx(4.0)


async def test_temperature_basse_ouvre_alerte(db):
    from src.mqtt_subscriber import _verifier_seuils
    enc = _enceinte(seuil_min=0.0)
    now = datetime.now(timezone.utc)

    await _verifier_seuils(db, enc, temperature=-1.2, humidite=78, batterie=90, now=now)

    alerte = await get_alerte_en_cours(db, 1, "temperature_basse")
    assert alerte is not None


async def test_temperature_dans_seuils_ferme_alerte(db):
    from src.mqtt_subscriber import _verifier_seuils
    enc = _enceinte()
    now = datetime.now(timezone.utc)

    # Ouvrir une alerte manuellement
    aid = await ouvrir_alerte(db, 1, "temperature_haute", 5.5, 4.0, now - timedelta(minutes=10))

    # Recevoir une température OK
    await _verifier_seuils(db, enc, temperature=3.2, humidite=78, batterie=90, now=now)

    # L'alerte doit être fermée
    alerte = await get_alerte_en_cours(db, 1, "temperature_haute")
    assert alerte is None


async def test_batterie_faible_ouvre_alerte(db):
    from src.mqtt_subscriber import _verifier_seuils
    enc = _enceinte(eid=3)
    now = datetime.now(timezone.utc)

    await _verifier_seuils(db, enc, temperature=3.0, humidite=70, batterie=15, now=now)

    alerte = await get_alerte_en_cours(db, 3, "batterie_faible")
    assert alerte is not None
    assert alerte["valeur"] == pytest.approx(15.0)


async def test_batterie_ok_ne_ouvre_pas_alerte(db):
    from src.mqtt_subscriber import _verifier_seuils
    enc = _enceinte(eid=3)
    now = datetime.now(timezone.utc)

    await _verifier_seuils(db, enc, temperature=3.0, humidite=70, batterie=85, now=now)

    alerte = await get_alerte_en_cours(db, 3, "batterie_faible")
    assert alerte is None


# ---------------------------------------------------------------------------
# Tests du délai de notification
# ---------------------------------------------------------------------------

async def test_notification_declenchee_apres_delai(db):
    from src.mqtt_subscriber import _ouvrir_ou_escalader

    enc = _enceinte(delai=5)
    now = datetime.now(timezone.utc)

    # Ouvrir l'alerte il y a 10 minutes (délai de 5 min dépassé)
    debut = now - timedelta(minutes=10)
    await ouvrir_alerte(db, 1, "temperature_haute", 6.0, 4.0, debut)

    with patch("src.mqtt_subscriber.envoyer_alerte", new_callable=AsyncMock) as mock_envoi, \
         patch("src.mqtt_subscriber.get_destinataires", new_callable=AsyncMock) as mock_dest:
        mock_dest.return_value = [{"nom": "Test", "email": "test@test.fr", "telephone": None}]

        await _ouvrir_ou_escalader(
            db, 1, "temperature_haute",
            valeur=6.0, seuil=4.0,
            delai_minutes=5, now=now,
            enceinte=enc,
        )

        mock_envoi.assert_called_once()


async def test_notification_non_declenchee_avant_delai(db):
    from src.mqtt_subscriber import _ouvrir_ou_escalader

    enc = _enceinte(delai=5)
    now = datetime.now(timezone.utc)

    # Alerte ouverte il y a 2 minutes seulement (délai de 5 min non atteint)
    debut = now - timedelta(minutes=2)
    await ouvrir_alerte(db, 1, "temperature_haute", 6.0, 4.0, debut)

    with patch("src.mqtt_subscriber.envoyer_alerte", new_callable=AsyncMock) as mock_envoi:
        await _ouvrir_ou_escalader(
            db, 1, "temperature_haute",
            valeur=6.0, seuil=4.0,
            delai_minutes=5, now=now,
            enceinte=enc,
        )
        mock_envoi.assert_not_called()


async def test_notification_non_repetee_si_deja_notifiee(db):
    from src.mqtt_subscriber import _ouvrir_ou_escalader

    enc = _enceinte(delai=5)
    now = datetime.now(timezone.utc)

    aid = await ouvrir_alerte(db, 1, "temperature_haute", 6.0, 4.0, now - timedelta(hours=1))
    await marquer_alerte_notifiee(db, aid)

    with patch("src.mqtt_subscriber.envoyer_alerte", new_callable=AsyncMock) as mock_envoi:
        await _ouvrir_ou_escalader(
            db, 1, "temperature_haute",
            valeur=6.5, seuil=4.0,
            delai_minutes=5, now=now,
            enceinte=enc,
        )
        mock_envoi.assert_not_called()


# ---------------------------------------------------------------------------
# Tests alert_manager (formatage messages)
# ---------------------------------------------------------------------------

async def test_envoi_email_sans_config_ne_plante_pas():
    """Sans SMTP configuré, envoyer_alerte doit logger un warning sans lever d'exception."""
    from src.alert_manager import envoyer_alerte
    enc = {"id": 1, "nom": "Chambre froide 1", "boutique_nom": "Test"}
    now = datetime.now(timezone.utc)

    # Ne doit pas lever d'exception même sans config SMTP
    await envoyer_alerte(
        enceinte=enc,
        type_alerte="temperature_haute",
        valeur=6.2,
        seuil=4.0,
        debut=now - timedelta(minutes=10),
        maintenant=now,
        destinataires=[{"nom": "Test", "email": "test@test.fr", "telephone": None}],
    )


async def test_corps_alerte_contient_infos_essentielles():
    from src.alert_manager import _corps_alerte
    now = datetime.now(timezone.utc)
    enc = {"id": 1, "nom": "Chambre froide 1", "boutique_nom": "Au Comptoir des Lilas"}
    corps = _corps_alerte(enc, "temperature_haute", 6.2, 4.0, now - timedelta(minutes=12), now)

    assert "Chambre froide 1" in corps
    assert "6.2" in corps
    assert "4.0" in corps
    assert "12 minutes" in corps

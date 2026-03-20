"""
mqtt_subscriber.py — Écoute MQTT + stockage + logique d'alertes

Flux :
  Zigbee2MQTT → Mosquitto → ici → SQLite + alertes email/SMS

Lancement autonome :
  python -m src.mqtt_subscriber

Ou intégré à FastAPI via lifespan (main.py).
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import paho.mqtt.client as mqtt

from src.database import (
    get_db,
    get_enceinte_by_zigbee_id,
    get_latest_releve,
    get_alerte_en_cours,
    insert_releve,
    ouvrir_alerte,
    fermer_alerte,
    marquer_alerte_notifiee,
    get_destinataires,
)
from src.alert_manager import envoyer_alerte

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (surchargeable via variables d'environnement)
# ---------------------------------------------------------------------------

MQTT_BROKER  = os.getenv("MQTT_BROKER",  "localhost")
MQTT_PORT    = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC   = os.getenv("MQTT_TOPIC",   "zigbee2mqtt/#")

# Durée sans réception avant d'ouvrir une alerte perte_signal (secondes)
DELAI_PERTE_SIGNAL_S = int(os.getenv("DELAI_PERTE_SIGNAL_S", str(15 * 60)))

# ---------------------------------------------------------------------------
# État en mémoire
# ---------------------------------------------------------------------------

_derniere_reception: dict[int, datetime] = {}   # enceinte_id → datetime UTC
_loop: Optional[asyncio.AbstractEventLoop] = None

# Cache des devices Zigbee2MQTT issus de bridge/devices
_zigbee_devices: list[dict] = []


def get_zigbee_devices() -> list[dict]:
    """Retourne la liste des sondes Zigbee2MQTT détectées (température/humidité)."""
    return _zigbee_devices


# ---------------------------------------------------------------------------
# Traitement d'un message MQTT
# ---------------------------------------------------------------------------

async def _traiter_message(topic: str, payload_bytes: bytes) -> None:
    """Appelé pour chaque message reçu sur zigbee2mqtt/#."""
    # Extraire le friendly_name depuis le topic (zigbee2mqtt/<name>)
    parts = topic.split("/")
    if len(parts) < 2:
        return
    zigbee_id = parts[1]

    # Ignorer les topics de contrôle Zigbee2MQTT (bridge/…)
    if zigbee_id in ("bridge", ""):
        return

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        logger.warning("Payload non-JSON sur %s : %s", topic, payload_bytes[:80])
        return

    temperature = payload.get("temperature")
    if temperature is None:
        return  # Message sans température (ex: availability)

    humidite       = payload.get("humidity")
    batterie       = payload.get("battery")
    qualite_signal = payload.get("linkquality")
    now            = datetime.now(timezone.utc)

    async with get_db() as db:
        enceinte = await get_enceinte_by_zigbee_id(db, zigbee_id)
        if not enceinte:
            logger.debug("Sonde inconnue ignorée : %s", zigbee_id)
            return

        eid = enceinte["id"]

        # 1. Stocker le relevé
        await insert_releve(db, eid, temperature, humidite, batterie, qualite_signal, now)
        _derniere_reception[eid] = now

        logger.debug(
            "%s | T=%.1f°C H=%s%% BAT=%s%%",
            enceinte["nom"], temperature,
            f"{humidite:.1f}" if humidite is not None else "—",
            batterie if batterie is not None else "—",
        )

        # 2. Vérifier les seuils et gérer les alertes
        await _verifier_seuils(db, enceinte, temperature, humidite, batterie, now)


async def _verifier_seuils(
    db,
    enceinte: dict,
    temperature: float,
    humidite: Optional[float],
    batterie: Optional[int],
    now: datetime,
) -> None:
    eid = enceinte["id"]

    # --- Température haute ---
    if temperature > enceinte["seuil_temp_max"]:
        await _ouvrir_ou_escalader(
            db, eid, "temperature_haute",
            valeur=temperature, seuil=enceinte["seuil_temp_max"],
            delai_minutes=enceinte["delai_alerte_minutes"], now=now,
            enceinte=enceinte,
        )
    else:
        await _fermer_si_ouverte(db, eid, "temperature_haute", now)

    # --- Température basse ---
    if temperature < enceinte["seuil_temp_min"]:
        await _ouvrir_ou_escalader(
            db, eid, "temperature_basse",
            valeur=temperature, seuil=enceinte["seuil_temp_min"],
            delai_minutes=enceinte["delai_alerte_minutes"], now=now,
            enceinte=enceinte,
        )
    else:
        await _fermer_si_ouverte(db, eid, "temperature_basse", now)

    # --- Batterie faible (seuil fixe 20 %) ---
    if batterie is not None and batterie < 20:
        await _ouvrir_ou_escalader(
            db, eid, "batterie_faible",
            valeur=batterie, seuil=20,
            delai_minutes=0, now=now,
            enceinte=enceinte,
        )
    else:
        await _fermer_si_ouverte(db, eid, "batterie_faible", now)


async def _ouvrir_ou_escalader(
    db,
    enceinte_id: int,
    type_alerte: str,
    valeur: float,
    seuil: float,
    delai_minutes: int,
    now: datetime,
    enceinte: dict,
) -> None:
    """
    Ouvre une alerte si elle n'existe pas encore.
    Notifie si le délai de déclenchement est atteint et qu'elle n'a pas été notifiée.
    """
    existante = await get_alerte_en_cours(db, enceinte_id, type_alerte)

    if not existante:
        await ouvrir_alerte(db, enceinte_id, type_alerte, valeur, seuil, now)
        logger.info(
            "Alerte ouverte — %s | %s | valeur=%.1f seuil=%.1f",
            enceinte["nom"], type_alerte, valeur, seuil,
        )
        return

    # Déjà ouverte : vérifier si le délai est dépassé pour notifier
    if existante["notifie"]:
        return

    try:
        debut = datetime.fromisoformat(existante["debut"].replace("Z", "+00:00"))
    except Exception:
        return

    duree_s = (now - debut).total_seconds()
    if duree_s >= delai_minutes * 60:
        destinataires = await get_destinataires(db)
        await envoyer_alerte(enceinte, type_alerte, valeur, seuil, debut, now, destinataires)
        await marquer_alerte_notifiee(db, existante["id"])
        logger.info(
            "Alerte notifiée — %s | %s | durée=%.0fmin",
            enceinte["nom"], type_alerte, duree_s / 60,
        )


async def _fermer_si_ouverte(
    db, enceinte_id: int, type_alerte: str, now: datetime
) -> None:
    existante = await get_alerte_en_cours(db, enceinte_id, type_alerte)
    if existante:
        await fermer_alerte(db, existante["id"], now)
        logger.info(
            "Alerte fermée — enceinte_id=%d | %s", enceinte_id, type_alerte
        )


# ---------------------------------------------------------------------------
# Watchdog perte de signal (tâche asyncio périodique)
# ---------------------------------------------------------------------------

async def _watchdog_perte_signal() -> None:
    """
    Vérifie toutes les minutes si une enceinte n'a pas émis depuis
    DELAI_PERTE_SIGNAL_S secondes et ouvre une alerte perte_signal.
    """
    while True:
        await asyncio.sleep(60)
        now = datetime.now(timezone.utc)

        async with get_db() as db:
            from src.database import get_boutiques, get_enceintes

            boutiques = await get_boutiques(db)
            for boutique in boutiques:
                enceintes = await get_enceintes(db, boutique["id"])
                for enc in enceintes:
                    eid = enc["id"]
                    derniere = _derniere_reception.get(eid)

                    if derniere is None:
                        # Pas encore de donnée depuis le démarrage :
                        # regarder le dernier relevé en base
                        releve = await get_latest_releve(db, eid)
                        if releve:
                            try:
                                derniere = datetime.fromisoformat(
                                    releve["horodatage"].replace("Z", "+00:00")
                                )
                            except Exception:
                                continue
                        else:
                            continue

                    age_s = (now - derniere).total_seconds()
                    if age_s > DELAI_PERTE_SIGNAL_S:
                        await _ouvrir_ou_escalader(
                            db, eid, "perte_signal",
                            valeur=age_s / 60, seuil=DELAI_PERTE_SIGNAL_S / 60,
                            delai_minutes=0, now=now,
                            enceinte=enc,
                        )
                    else:
                        await _fermer_si_ouverte(db, eid, "perte_signal", now)


# ---------------------------------------------------------------------------
# Client MQTT (callbacks paho → asyncio)
# ---------------------------------------------------------------------------

def _on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        logger.info("MQTT connecté — abonné à %s", MQTT_TOPIC)
    else:
        logger.error("Échec connexion MQTT, code %d", rc)


def _on_message(client, userdata, msg):
    """Callback paho (thread réseau) → schedule coroutine dans la boucle asyncio."""
    if _loop is None:
        return
    asyncio.run_coroutine_threadsafe(
        _traiter_message(msg.topic, msg.payload), _loop
    )


def _on_disconnect(client, userdata, rc, properties=None):
    if rc != 0:
        logger.warning("MQTT déconnecté (code %d) — reconnexion automatique", rc)


# ---------------------------------------------------------------------------
# Point d'entrée public
# ---------------------------------------------------------------------------

async def demarrer_subscriber() -> asyncio.Task:
    """
    Démarre le client MQTT et le watchdog dans la boucle asyncio courante.
    Retourne la tâche watchdog (utile pour l'annuler à l'arrêt).
    """
    global _loop
    _loop = asyncio.get_running_loop()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect    = _on_connect
    client.on_message    = _on_message
    client.on_disconnect = _on_disconnect

    await asyncio.get_running_loop().run_in_executor(
        None, lambda: client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    )
    client.loop_start()
    logger.info("Subscriber MQTT démarré (%s:%d)", MQTT_BROKER, MQTT_PORT)

    watchdog_task = asyncio.create_task(_watchdog_perte_signal(), name="watchdog_signal")
    return watchdog_task


async def arreter_subscriber(client: mqtt.Client, watchdog_task: asyncio.Task) -> None:
    watchdog_task.cancel()
    client.loop_stop()
    client.disconnect()
    logger.info("Subscriber MQTT arrêté")


# ---------------------------------------------------------------------------
# Lancement autonome (sans FastAPI)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    async def _main():
        from src.database import init_db
        await init_db()
        watchdog = await demarrer_subscriber()
        logger.info("En écoute… (Ctrl+C pour arrêter)")
        try:
            await asyncio.Event().wait()   # attend indéfiniment
        except asyncio.CancelledError:
            pass
        finally:
            watchdog.cancel()

    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("\nSubscriber arrêté.")
        sys.exit(0)

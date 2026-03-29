"""
mqtt_subscriber.py — Écoute MQTT + stockage + alertes + auto-découverte Zigbee2MQTT

Flux :
  Zigbee2MQTT → Mosquitto → ici → SQLite + alertes

  1. bridge/devices  → auto-création des enceintes en base (pas de config manuelle)
  2. <friendly_name> → stockage du relevé + vérification seuils
"""

import asyncio
import json
import logging
import os
import threading
from datetime import datetime, timedelta, timezone
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
    create_enceinte,
    get_enceintes,
    get_boutiques,
    exporter_jour_csv,
    purger_anciens_releves,
    RETENTION_RELEVES_JOURS,
)
from src.alert_manager import envoyer_alerte

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MQTT_BROKER          = os.getenv("MQTT_BROKER",  "localhost")
MQTT_PORT            = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC           = os.getenv("MQTT_TOPIC",   "zigbee2mqtt/#")
DELAI_PERTE_SIGNAL_S = int(os.getenv("DELAI_PERTE_SIGNAL_S", str(15 * 60)))

# Boutique par défaut pour l'auto-création
BOUTIQUE_ID_DEFAUT = int(os.getenv("BOUTIQUE_ID", "1"))

# ---------------------------------------------------------------------------
# État en mémoire
# ---------------------------------------------------------------------------

_derniere_reception: dict[int, datetime] = {}
_loop: Optional[asyncio.AbstractEventLoop] = None

# Cache live : friendly_name → dernière mesure reçue
_live_data: dict[str, dict] = {}


def get_live_data() -> dict[str, dict]:
    """Retourne les dernières mesures reçues par friendly_name."""
    return _live_data


# ---------------------------------------------------------------------------
# Auto-création d'enceinte depuis un friendly_name
# ---------------------------------------------------------------------------

def _deviner_type_et_seuils(friendly_name: str) -> tuple[str, float, float]:
    """Devine le type HACCP et les seuils par défaut depuis le nom de la sonde."""
    nom = friendly_name.lower()
    if any(k in nom for k in ("congelat", "negat", "freezer", "surgelat")):
        return "chambre_froide_negative", -25.0, -18.0
    if any(k in nom for k in ("chambre", "froide", "cold")):
        return "chambre_froide_positive", 0.0, 4.0
    if "vitrine" in nom:
        return "vitrine_refrigeree", 0.0, 4.0
    if "labo" in nom:
        return "autre", 10.0, 25.0
    return "autre", 0.0, 30.0


async def _auto_creer_enceinte_si_absente(db, friendly_name: str) -> Optional[dict]:
    """Crée l'enceinte en base si elle n'existe pas encore."""
    enceinte = await get_enceinte_by_zigbee_id(db, friendly_name)
    if enceinte:
        return enceinte

    type_enc, seuil_min, seuil_max = _deviner_type_et_seuils(friendly_name)
    eid = await create_enceinte(db, {
        "boutique_id":          BOUTIQUE_ID_DEFAUT,
        "nom":                  friendly_name,
        "type":                 type_enc,
        "sonde_zigbee_id":      friendly_name,
        "seuil_temp_min":       seuil_min,
        "seuil_temp_max":       seuil_max,
        "seuil_hum_max":        90.0,
        "delai_alerte_minutes": 5,
    })
    logger.info(
        "✅ Enceinte auto-créée : '%s'  type=%s  seuils=[%.0f ; %.0f]°C  (id=%d)",
        friendly_name, type_enc, seuil_min, seuil_max, eid,
    )
    return await get_enceinte_by_zigbee_id(db, friendly_name)


# ---------------------------------------------------------------------------
# Traitement bridge/devices — découverte initiale
# ---------------------------------------------------------------------------

async def _traiter_bridge_devices(payload: list) -> None:
    """
    Reçu sur zigbee2mqtt/bridge/devices au démarrage de Z2M.
    Auto-crée les enceintes pour chaque sonde qui expose la température.
    """
    logger.info("bridge/devices reçu — %d appareils trouvés", len(payload))
    async with get_db() as db:
        for device in payload:
            if device.get("type") == "Coordinator":
                continue
            friendly_name = device.get("friendly_name")
            if not friendly_name:
                continue

            # Vérifier que le device expose bien la température
            exposes = (device.get("definition") or {}).get("exposes", [])
            has_temp = any(e.get("name") == "temperature" for e in exposes)
            if not has_temp:
                logger.debug("Ignoré (pas de température) : %s", friendly_name)
                continue

            logger.info("Sonde détectée : %s", friendly_name)
            await _auto_creer_enceinte_si_absente(db, friendly_name)


# ---------------------------------------------------------------------------
# Traitement d'un relevé de température
# ---------------------------------------------------------------------------

async def _traiter_message(topic: str, payload_bytes: bytes) -> None:
    logger.debug("MQTT reçu : %s  payload=%s", topic, payload_bytes[:120])

    parts = topic.split("/")
    if len(parts) < 2:
        return

    sub = parts[1]

    # --- bridge/devices ---
    if sub == "bridge" and len(parts) >= 3 and parts[2] == "devices":
        try:
            payload = json.loads(payload_bytes)
            if isinstance(payload, list):
                await _traiter_bridge_devices(payload)
        except json.JSONDecodeError:
            logger.warning("bridge/devices : payload JSON invalide")
        return

    # Ignorer les autres topics bridge/...
    if sub in ("bridge", ""):
        return

    friendly_name = sub

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        logger.warning("Payload non-JSON sur %s", topic)
        return

    temperature = payload.get("temperature")
    if temperature is None:
        logger.debug("%s : pas de température dans le payload — ignoré", friendly_name)
        return

    humidite       = payload.get("humidity")
    batterie       = payload.get("battery")
    qualite_signal = payload.get("linkquality")
    now            = datetime.now(timezone.utc)

    # Mettre à jour le cache live (indépendant de la DB)
    _live_data[friendly_name] = {
        "temperature":  temperature,
        "humidity":     humidite,
        "battery":      batterie,
        "linkquality":  qualite_signal,
        "timestamp":    now.isoformat(),
    }

    logger.info(
        "📡 %s | T=%.1f°C  H=%s%%  BAT=%s%%  LQI=%s",
        friendly_name, temperature,
        f"{humidite:.1f}" if humidite is not None else "—",
        batterie       if batterie       is not None else "—",
        qualite_signal if qualite_signal is not None else "—",
    )

    async with get_db() as db:
        # Auto-créer l'enceinte si elle n'existe pas encore
        enceinte = await _auto_creer_enceinte_si_absente(db, friendly_name)
        if not enceinte:
            logger.error("Impossible de créer/récupérer l'enceinte pour %s", friendly_name)
            return

        eid = enceinte["id"]
        await insert_releve(db, eid, temperature, humidite, batterie, qualite_signal, now)
        _derniere_reception[eid] = now
        logger.info("💾 Relevé stocké → enceinte '%s' (id=%d)", enceinte["nom"], eid)

        await _verifier_seuils(db, enceinte, temperature, humidite, batterie, now)


# ---------------------------------------------------------------------------
# Vérification des seuils et gestion des alertes
# ---------------------------------------------------------------------------

async def _verifier_seuils(db, enceinte, temperature, humidite, batterie, now):
    eid = enceinte["id"]

    if temperature > enceinte["seuil_temp_max"]:
        await _ouvrir_ou_escalader(db, eid, "temperature_haute",
            valeur=temperature, seuil=enceinte["seuil_temp_max"],
            delai_minutes=enceinte["delai_alerte_minutes"], now=now, enceinte=enceinte)
    else:
        await _fermer_si_ouverte(db, eid, "temperature_haute", now)

    if temperature < enceinte["seuil_temp_min"]:
        await _ouvrir_ou_escalader(db, eid, "temperature_basse",
            valeur=temperature, seuil=enceinte["seuil_temp_min"],
            delai_minutes=enceinte["delai_alerte_minutes"], now=now, enceinte=enceinte)
    else:
        await _fermer_si_ouverte(db, eid, "temperature_basse", now)

    if batterie is not None and batterie < 20:
        await _ouvrir_ou_escalader(db, eid, "batterie_faible",
            valeur=batterie, seuil=20,
            delai_minutes=0, now=now, enceinte=enceinte)
    else:
        await _fermer_si_ouverte(db, eid, "batterie_faible", now)


async def _ouvrir_ou_escalader(db, enceinte_id, type_alerte, valeur, seuil,
                                delai_minutes, now, enceinte):
    existante = await get_alerte_en_cours(db, enceinte_id, type_alerte)
    if not existante:
        await ouvrir_alerte(db, enceinte_id, type_alerte, valeur, seuil, now)
        logger.info("🔴 Alerte ouverte — %s | %s | valeur=%.1f seuil=%.1f",
                    enceinte["nom"], type_alerte, valeur, seuil)
        return

    if existante["notifie"]:
        return

    try:
        debut  = datetime.fromisoformat(existante["debut"].replace("Z", "+00:00"))
    except Exception:
        return

    duree_s = (now - debut).total_seconds()
    if duree_s >= delai_minutes * 60:
        destinataires = await get_destinataires(db)
        await envoyer_alerte(enceinte, type_alerte, valeur, seuil, debut, now, destinataires)
        await marquer_alerte_notifiee(db, existante["id"])
        logger.info("📧 Alerte notifiée — %s | %s | durée=%.0fmin",
                    enceinte["nom"], type_alerte, duree_s / 60)


async def _fermer_si_ouverte(db, enceinte_id, type_alerte, now):
    existante = await get_alerte_en_cours(db, enceinte_id, type_alerte)
    if existante:
        await fermer_alerte(db, existante["id"], now)
        logger.info("✅ Alerte fermée — enceinte_id=%d | %s", enceinte_id, type_alerte)


# ---------------------------------------------------------------------------
# Watchdog perte de signal
# ---------------------------------------------------------------------------

async def _watchdog_perte_signal() -> None:
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
                        releve = await get_latest_releve(db, eid)
                        if releve:
                            try:
                                derniere = datetime.fromisoformat(
                                    releve["horodatage"].replace("Z", "+00:00"))
                            except Exception:
                                continue
                        else:
                            continue
                    age_s = (now - derniere).total_seconds()
                    if age_s > DELAI_PERTE_SIGNAL_S:
                        await _ouvrir_ou_escalader(db, eid, "perte_signal",
                            valeur=age_s / 60, seuil=DELAI_PERTE_SIGNAL_S / 60,
                            delai_minutes=0, now=now, enceinte=enc)
                    else:
                        await _fermer_si_ouverte(db, eid, "perte_signal", now)


# ---------------------------------------------------------------------------
# Export CSV quotidien + purge SQLite
# ---------------------------------------------------------------------------

async def _tache_export_et_purge() -> None:
    """
    Tourne en arrière-plan.
    Au démarrage : exporte les jours manquants depuis 30 jours.
    Ensuite : toutes les 24h, exporte hier + purge la base.
    """
    # Export de rattrapage au démarrage
    await _exporter_jours_manquants()

    while True:
        # Attendre minuit (simplification : on attend 24h)
        await asyncio.sleep(24 * 3600)

        hier = datetime.now(timezone.utc) - timedelta(days=1)
        await _exporter_jour(hier)

        async with get_db() as db:
            stats = await purger_anciens_releves(db)
            logger.info(
                "🗑️  Purge SQLite : %d relevés supprimés, %d alertes supprimées",
                stats["releves_supprimes"], stats["alertes_supprimees"],
            )


async def _exporter_jours_manquants() -> None:
    """Au démarrage, exporte tous les jours non encore exportés dans la fenêtre de rétention."""
    now = datetime.now(timezone.utc)
    for delta in range(1, RETENTION_RELEVES_JOURS):
        jour = now - timedelta(days=delta)
        await _exporter_jour(jour)


async def _exporter_jour(jour: datetime) -> None:
    """Exporte les relevés de toutes les enceintes pour un jour donné."""
    async with get_db() as db:
        boutiques = await get_boutiques(db)
        for boutique in boutiques:
            enceintes = await get_enceintes(db, boutique["id"])
            for enc in enceintes:
                await exporter_jour_csv(db, enc["id"], enc["nom"], jour)


# ---------------------------------------------------------------------------
# Client MQTT — thread dédié (API classique, fiable)
# ---------------------------------------------------------------------------

def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        logger.info("✅ MQTT connecté — abonné à %s", MQTT_TOPIC)
    else:
        codes = {1: "protocole refusé", 2: "identifiant refusé",
                 3: "serveur indisponible", 4: "auth incorrecte", 5: "non autorisé"}
        logger.error("❌ Échec connexion MQTT (code %d) : %s", rc, codes.get(rc, "inconnu"))


def _on_message(client, userdata, msg):
    if _loop is None:
        return
    asyncio.run_coroutine_threadsafe(
        _traiter_message(msg.topic, msg.payload), _loop
    )


def _on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("⚠️  MQTT déconnecté (code %d) — reconnexion automatique", rc)


def _on_log(client, userdata, level, buf):
    """Relaye les logs internes de paho vers notre logger."""
    logger.debug("[paho] %s", buf)


def _run_mqtt_thread():
    """Tourne dans un thread dédié, indépendant de l'event loop asyncio."""
    client = mqtt.Client()
    client.on_connect    = _on_connect
    client.on_message    = _on_message
    client.on_disconnect = _on_disconnect
    client.on_log        = _on_log

    logger.info("Connexion MQTT → %s:%d …", MQTT_BROKER, MQTT_PORT)
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except Exception as e:
        logger.error("❌ Impossible de se connecter à Mosquitto : %s", e)
        return

    logger.info("loop_forever() démarré")
    client.loop_forever()


# ---------------------------------------------------------------------------
# Point d'entrée public
# ---------------------------------------------------------------------------

async def demarrer_subscriber() -> asyncio.Task:
    global _loop
    _loop = asyncio.get_running_loop()

    thread = threading.Thread(target=_run_mqtt_thread, daemon=True, name="mqtt-subscriber")
    thread.start()
    logger.info("Thread MQTT démarré")

    watchdog_task = asyncio.create_task(_watchdog_perte_signal(), name="watchdog_signal")
    asyncio.create_task(_tache_export_et_purge(), name="export_purge")
    return watchdog_task


# ---------------------------------------------------------------------------
# Lancement autonome
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    async def _main():
        from src.database import init_db
        await init_db()
        watchdog = await demarrer_subscriber()
        logger.info("En écoute… (Ctrl+C pour arrêter)")
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        finally:
            watchdog.cancel()

    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("\nArrêté.")
        sys.exit(0)

"""
simulate_sensors.py — Simulateur de sondes Zigbee SNZB-02D
Publie des données MQTT au même format que Zigbee2MQTT

Usage :
    python scripts/simulate_sensors.py [--scenario normal|derive|alerte|batterie_faible]

Scenarios :
    normal          : données dans les seuils (défaut)
    derive          : température dérive lentement vers le haut
    alerte          : chambre_froide_2 dépasse 4°C après 2 minutes
    perte_signal    : chambre_froide_1 cesse d'émettre après 1 minute
    batterie_faible : chambre_froide_2 signale batterie < 20%
"""

import argparse
import json
import math
import random
import time
import sys

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Erreur : paho-mqtt non installé. Lance : pip install paho-mqtt")
    sys.exit(1)

BROKER = "localhost"
PORT = 1883
INTERVAL_SECONDS = 30  # Fréquence d'envoi (les vraies sondes envoient toutes les 5s, on simule 30s)

SONDES = [
    {
        "id": "chambre_froide_1",
        "topic": "zigbee2mqtt/chambre_froide_1",
        "temp_base": 2.5,
        "hum_base": 75,
        "variation_temp": 0.8,
        "variation_hum": 3.0,
        "batterie_base": 95,
        "actif": True,
    },
    {
        "id": "chambre_froide_2",
        "topic": "zigbee2mqtt/chambre_froide_2",
        "temp_base": 3.0,
        "hum_base": 78,
        "variation_temp": 0.6,
        "variation_hum": 2.5,
        "batterie_base": 88,
        "actif": True,
    },
    {
        "id": "vitrine",
        "topic": "zigbee2mqtt/vitrine",
        "temp_base": 3.5,
        "hum_base": 65,
        "variation_temp": 1.2,
        "variation_hum": 4.0,
        "batterie_base": 72,
        "actif": True,
    },
    {
        "id": "laboratoire",
        "topic": "zigbee2mqtt/laboratoire",
        "temp_base": 12.0,
        "hum_base": 55,
        "variation_temp": 2.0,
        "variation_hum": 5.0,
        "batterie_base": 99,
        "actif": True,
    },
]


def build_payload(sonde: dict, tick: int, scenario: str) -> dict | None:
    """Construit le payload JSON selon le scénario."""
    sid = sonde["id"]

    # Scénario perte_signal : chambre_froide_1 disparaît après tick 2
    if scenario == "perte_signal" and sid == "chambre_froide_1" and tick >= 2:
        return None

    temp = sonde["temp_base"]
    hum = sonde["hum_base"]
    batterie = sonde["batterie_base"]

    # Scénario dérive : température monte de 0.2°C par tick sur chambre_froide_2
    if scenario == "derive" and sid == "chambre_froide_2":
        temp += tick * 0.2

    # Scénario alerte : chambre_froide_2 passe à 6°C après tick 4
    if scenario == "alerte" and sid == "chambre_froide_2":
        if tick >= 4:
            temp = 6.0 + random.uniform(-0.3, 0.3)

    # Scénario batterie faible
    if scenario == "batterie_faible" and sid == "chambre_froide_2":
        batterie = 12

    # Bruit naturel sinusoïdal + aléatoire (simule cycle compresseur)
    bruit_temp = sonde["variation_temp"] * math.sin(tick * 0.3) + random.uniform(-0.2, 0.2)
    bruit_hum = sonde["variation_hum"] * math.sin(tick * 0.2 + 1) + random.uniform(-1, 1)

    return {
        "temperature": round(temp + bruit_temp, 1),
        "humidity": round(max(30, min(99, hum + bruit_hum)), 1),
        "battery": batterie + random.randint(-1, 1),
        "linkquality": random.randint(80, 150),
        "voltage": 3000,
    }


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connecté au broker MQTT {BROKER}:{PORT}")
    else:
        print(f"Échec de connexion, code : {rc}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Simulateur HACCP — sondes SNZB-02D")
    parser.add_argument(
        "--scenario",
        choices=["normal", "derive", "alerte", "perte_signal", "batterie_faible"],
        default="normal",
        help="Scénario de simulation (défaut : normal)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=INTERVAL_SECONDS,
        help=f"Intervalle entre envois en secondes (défaut : {INTERVAL_SECONDS})",
    )
    args = parser.parse_args()

    print(f"Scénario : {args.scenario} | Intervalle : {args.interval}s")
    print("Sondes simulées :")
    for s in SONDES:
        print(f"  - {s['id']} → {s['topic']} (temp base : {s['temp_base']}°C)")
    print()

    client = mqtt.Client()
    client.on_connect = on_connect
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()

    tick = 0
    try:
        while True:
            tick += 1
            for sonde in SONDES:
                payload = build_payload(sonde, tick, args.scenario)
                if payload is None:
                    print(f"[tick {tick:04d}] {sonde['id']:20s} — HORS LIGNE (perte de signal simulée)")
                    continue
                message = json.dumps(payload)
                result = client.publish(sonde["topic"], message)
                status = "OK" if result.rc == 0 else f"ERR({result.rc})"
                print(
                    f"[tick {tick:04d}] {sonde['id']:20s} | "
                    f"T={payload['temperature']:5.1f}°C "
                    f"H={payload['humidity']:4.1f}% "
                    f"BAT={payload['battery']:3d}% "
                    f"[{status}]"
                )
            print()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nSimulateur arrêté.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()

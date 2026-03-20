"""
seed_data.py — Injecte 48h de relevés réalistes en base (sans MQTT ni broker)
Usage : python scripts/seed_data.py
"""
import asyncio
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import init_db, get_db, insert_releve

SONDES = [
    {"enceinte_id": 1, "temp_base": 2.5, "hum_base": 75, "variation": 0.8},
    {"enceinte_id": 2, "temp_base": 3.0, "hum_base": 78, "variation": 0.6},
    {"enceinte_id": 3, "temp_base": 3.5, "hum_base": 65, "variation": 1.2},
    {"enceinte_id": 4, "temp_base": 12.0, "hum_base": 55, "variation": 2.0},
]

# Scénario : chambre froide 2 monte à 6°C pendant 20 min il y a 4 heures
ANOMALIE_EID    = 2
ANOMALIE_DEBUT  = datetime.now(timezone.utc) - timedelta(hours=4, minutes=20)
ANOMALIE_FIN    = datetime.now(timezone.utc) - timedelta(hours=4)


async def main():
    await init_db()
    now = datetime.now(timezone.utc)
    debut = now - timedelta(hours=48)
    interval = timedelta(minutes=5)

    total = 0
    async with get_db() as db:
        ts = debut
        tick = 0
        while ts <= now:
            tick += 1
            for s in SONDES:
                eid = s["enceinte_id"]
                bruit = s["variation"] * math.sin(tick * 0.25) + random.uniform(-0.15, 0.15)
                temp = s["temp_base"] + bruit

                # Injecter l'anomalie sur enceinte 2
                if eid == ANOMALIE_EID and ANOMALIE_DEBUT <= ts <= ANOMALIE_FIN:
                    temp = 6.0 + random.uniform(-0.3, 0.3)

                hum      = s["hum_base"] + math.sin(tick * 0.18) * 3 + random.uniform(-1, 1)
                batterie = max(80, 95 - tick // 50)

                await insert_releve(db, eid, round(temp, 1), round(hum, 1), batterie, random.randint(90, 150), ts)
                total += 1

            ts += interval

    print(f"OK {total} releves injectes ({tick} ticks x {len(SONDES)} sondes, sur 48h)")
    print(f"   Anomalie simulee : enceinte 2 a ~6C de {ANOMALIE_DEBUT.strftime('%H:%M')} a {ANOMALIE_FIN.strftime('%H:%M')} UTC")

asyncio.run(main())

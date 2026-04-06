#!/usr/bin/env python3
"""Mettre à jour les tolérances de température dans la BDD"""
import sqlite3
import sys
from pathlib import Path

db_path = Path(__file__).parent / "haccp.db"
if not db_path.exists():
    print(f"❌ BDD non trouvée: {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Mettre à jour les tolérances selon la plage de conservation
updates = [
    ("UPDATE produits SET temperature_tolerance = 5 WHERE (temperature_conservation LIKE '%0°C à +4°C%' OR temperature_conservation LIKE '%0°C à 4°C%') AND temperature_tolerance = 2.0", "0-4°C → +5"),
    ("UPDATE produits SET temperature_tolerance = 4 WHERE (temperature_conservation LIKE '%0°C à +3°C%' OR temperature_conservation LIKE '%0°C à 3°C%') AND temperature_tolerance = 2.0", "0-3°C → +4"),
    ("UPDATE produits SET temperature_tolerance = 8 WHERE (temperature_conservation LIKE '%0°C à +7°C%' OR temperature_conservation LIKE '%0°C à 7°C%') AND temperature_tolerance = 2.0", "0-7°C → +8"),
]

for sql, label in updates:
    cursor.execute(sql)
    print(f"✓ {label}: {cursor.rowcount} produits")

conn.commit()

# Vérifier
cursor.execute("SELECT temperature_tolerance, COUNT(*) FROM produits GROUP BY temperature_tolerance ORDER BY temperature_tolerance")
print("\nRésumé:")
for tol, count in cursor.fetchall():
    print(f"  Tolérance {tol}°C: {count} produits")

conn.close()
print("\n✓ Mise à jour terminée")

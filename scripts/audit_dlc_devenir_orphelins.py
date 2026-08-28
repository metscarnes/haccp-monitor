#!/usr/bin/env python3
"""
audit_dlc_devenir_orphelins.py — Confirme l'hypothèse : dlc_devenir contient des
entrées 'refroidissement'/'cuisson' antérieures au rebuild de table v7.4
(21/07 ou avant selon la migration), dont le source_id a été RÉUTILISÉ par de
nouvelles lignes après le rebuild (AUTOINCREMENT repart de 1 sur une table
recréée par DROP/CREATE). Isole tous les cas concernés, pas seulement les 3
détectés dans le rattrapage.

Lecture seule, ne modifie rien.
"""
import sqlite3
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DB_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "haccp.db"
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print(f"=== Base : {DB_PATH} ===\n")

print("--- 1. sqlite_sequence pour cuissons / refroidissements (confirme le dernier id distribué) ---")
cur.execute("SELECT name, seq FROM sqlite_sequence WHERE name IN ('cuissons', 'refroidissements')")
for r in cur.fetchall():
    print(f"  {r['name']} : seq={r['seq']}")
print()

for table in ("refroidissement", "cuisson"):
    real_table = table + "s"
    print(f"--- 2. dlc_devenir '{table}' dont source_id ne correspond PAS à la ligne {real_table} actuelle ---")
    cur.execute(f"""
        SELECT dd.id AS dlc_devenir_id, dd.source_id, dd.statut, dd.created_at AS dd_created,
               r.created_at AS ligne_created, r.id IS NOT NULL AS ligne_existe
        FROM dlc_devenir dd
        LEFT JOIN {real_table} r ON r.id = dd.source_id
        WHERE dd.source_type = ?
        ORDER BY dd.source_id
    """, (table,))
    rows = cur.fetchall()
    suspects = []
    for r in rows:
        if r["ligne_existe"] and r["dd_created"] and r["ligne_created"] and r["dd_created"] < r["ligne_created"]:
            suspects.append(r)
    print(f"  {len(rows)} entrée(s) dlc_devenir '{table}' au total")
    print(f"  {len(suspects)} suspecte(s) : dlc_devenir créée AVANT la ligne {real_table} qu'elle référence")
    for r in suspects:
        print(f"      dlc_devenir.id={r['dlc_devenir_id']} source_id={r['source_id']} "
              f"statut={r['statut']} dd_created={r['dd_created']} vs ligne_created={r['ligne_created']}")
    print()

print("=== Fin de l'audit ===")
conn.close()

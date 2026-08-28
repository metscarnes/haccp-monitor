#!/usr/bin/env python3
"""
audit_tende_tranche.py — Compare le calcul marge Carpaccio entre le
comparateur (correct, 7,16€/pièce) et /api/vente/catalogue (aberrant,
-238,46€/pièce), avec la ligne d'achat réelle "TENDE TRANCHE PAD BOVIN"
(code 43549-02, Elivia/Selvi) pour trouver l'écart exact.

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

print("--- 1. Ligne d'achat TENDE TRANCHE PAD BOVIN — TOUTES les colonnes ---")
cur.execute("SELECT * FROM catalogue_fournisseur WHERE code_article = '43549-02'")
rows = cur.fetchall()
for r in rows:
    d = dict(r)
    for k, v in d.items():
        print(f"    {k} = {v!r}")
    print()
print()

print("--- 2. Carpaccio catalogue_vente — TOUTES les colonnes ---")
cur.execute("SELECT * FROM catalogue_vente WHERE nom LIKE '%arpaccio%'")
for r in cur.fetchall():
    d = dict(r)
    for k, v in d.items():
        print(f"    {k} = {v!r}")
print()

print("--- 3. comparatif_groupe_vente pour Carpaccio (toutes lignes, sans filtre groupe) ---")
cv_id = None
cur.execute("SELECT id FROM catalogue_vente WHERE nom LIKE '%arpaccio%'")
r = cur.fetchone()
if r:
    cv_id = r["id"]
    cur.execute("SELECT * FROM comparatif_groupe_vente WHERE catalogue_vente_id = ?", (cv_id,))
    for row in cur.fetchall():
        print(f"    {dict(row)}")
print()

print("=== Fin de l'audit ===")
conn.close()

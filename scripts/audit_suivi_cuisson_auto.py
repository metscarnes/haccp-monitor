#!/usr/bin/env python3
"""
audit_suivi_cuisson_auto.py — Liste tous les produits catalogue_vente marqués
suivi_cuisson_auto=1, pour diagnostiquer les 138 lots "à cuire" (28/08/2026) :
si un produit relié à un groupe comparatif générique (ex. Rosbeef cuit → groupe
"Boeuf", 15 articles bruts) est coché à tort, toutes ses réceptions brutes en
attente remontent comme "à cuire".

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

print("--- Produits catalogue_vente avec suivi_cuisson_auto = 1 ---")
cur.execute("""
    SELECT cv.id, cv.nom, cv.actif,
           gv.groupe_id, cg.nom AS groupe_nom,
           (SELECT COUNT(*) FROM comparatif_groupe_ligne gl WHERE gl.groupe_id = gv.groupe_id) AS nb_articles_groupe
    FROM catalogue_vente cv
    LEFT JOIN comparatif_groupe_vente gv ON gv.catalogue_vente_id = cv.id
    LEFT JOIN comparatif_groupe cg ON cg.id = gv.groupe_id
    WHERE cv.suivi_cuisson_auto = 1
    ORDER BY cv.nom
""")
rows = cur.fetchall()
if not rows:
    print("  Aucun produit marqué.")
for r in rows:
    print(f"  id={r['id']:<5} {r['nom']:<40} actif={r['actif']} "
          f"groupe_id={r['groupe_id']} ({r['groupe_nom']!r}) — {r['nb_articles_groupe']} article(s) dans le groupe")

print("\n=== Fin de l'audit ===")
conn.close()

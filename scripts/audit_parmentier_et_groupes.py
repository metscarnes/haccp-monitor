#!/usr/bin/env python3
"""
audit_parmentier_et_groupes.py — Vérifie l'existence de "Parmentier canard
gratiné cantal AOP" dans catalogue_vente, et l'état des groupes comparatifs
pour Lasagnes (id=52) / Gratin dauphinois (id=49) : sont-ils déjà reliés à
des articles catalogue_fournisseur via comparatif_groupe_vente/ligne ?

Lecture seule, ne modifie rien.

    python3 scripts/audit_parmentier_et_groupes.py [chemin/vers/haccp.db]
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

print("--- 1. Recherche 'Parmentier' dans catalogue_vente (nom exact et approché) ---")
cur.execute("SELECT id, nom, actif FROM catalogue_vente WHERE LOWER(nom) LIKE '%parmentier%'")
rows = cur.fetchall()
for r in rows:
    print(f"  id={r['id']} nom={r['nom']!r} actif={r['actif']}")
if not rows:
    print("  Aucun résultat — le produit n'existe pas encore dans catalogue_vente.")
print()

print("--- 2. Recherche 'canard' dans catalogue_fournisseur (matière reçue) ---")
cur.execute("SELECT id, designation, famille, sous_famille FROM catalogue_fournisseur WHERE LOWER(designation) LIKE '%canard%'")
for r in cur.fetchall():
    print(f"  id={r['id']} designation={r['designation']!r} famille={r['famille']} sous_famille={r['sous_famille']}")
print()

print("--- 3. Groupe comparatif de Lasagnes (catalogue_vente_id=52) ---")
cur.execute("""
    SELECT cgv.groupe_id, cg.nom AS groupe_nom
    FROM comparatif_groupe_vente cgv
    LEFT JOIN comparatif_groupe cg ON cg.id = cgv.groupe_id
    WHERE cgv.catalogue_vente_id = 52
""")
r = cur.fetchone()
if r:
    print(f"  groupe_id={r['groupe_id']} nom={r['groupe_nom']!r}")
    cur.execute("""
        SELECT gl.catalogue_fournisseur_id, cf.designation
        FROM comparatif_groupe_ligne gl
        LEFT JOIN catalogue_fournisseur cf ON cf.id = gl.catalogue_fournisseur_id
        WHERE gl.groupe_id = ?
    """, (r["groupe_id"],))
    for l in cur.fetchall():
        print(f"      article id={l['catalogue_fournisseur_id']} {l['designation']}")
else:
    print("  Lasagnes (id=52) n'est relié à AUCUN groupe comparatif.")
print()

print("--- 4. Groupe comparatif de Gratin dauphinois (catalogue_vente_id=49) ---")
cur.execute("""
    SELECT cgv.groupe_id, cg.nom AS groupe_nom
    FROM comparatif_groupe_vente cgv
    LEFT JOIN comparatif_groupe cg ON cg.id = cgv.groupe_id
    WHERE cgv.catalogue_vente_id = 49
""")
r = cur.fetchone()
if r:
    print(f"  groupe_id={r['groupe_id']} nom={r['groupe_nom']!r}")
    cur.execute("""
        SELECT gl.catalogue_fournisseur_id, cf.designation
        FROM comparatif_groupe_ligne gl
        LEFT JOIN catalogue_fournisseur cf ON cf.id = gl.catalogue_fournisseur_id
        WHERE gl.groupe_id = ?
    """, (r["groupe_id"],))
    for l in cur.fetchall():
        print(f"      article id={l['catalogue_fournisseur_id']} {l['designation']}")
else:
    print("  Gratin dauphinois (id=49) n'est relié à AUCUN groupe comparatif.")
print()

print("=== Fin de l'audit ===")
conn.close()

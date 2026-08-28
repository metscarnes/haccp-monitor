#!/usr/bin/env python3
"""
audit_groupe_132.py — État complet du groupe comparatif #132 ("Boeuf") et de
sa liaison avec Rosbeef cuit (catalogue_vente id=114, le seul actif).

Lecture seule, ne modifie rien.

    python3 scripts/audit_groupe_132.py [chemin/vers/haccp.db]
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

print("--- 1. comparatif_groupe #132 (colonnes legacy 1↔1) ---")
cur.execute("SELECT * FROM comparatif_groupe WHERE id = 132")
r = cur.fetchone()
if r:
    print(f"  {dict(r)}")
else:
    print("  id=132 n'existe pas")
print()

print("--- 2. comparatif_groupe_vente (liaison actuelle, table v6.4) pour groupe_id=132 ---")
cur.execute("""
    SELECT cgv.groupe_id, cgv.catalogue_vente_id, cv.nom, cv.actif
    FROM comparatif_groupe_vente cgv
    LEFT JOIN catalogue_vente cv ON cv.id = cgv.catalogue_vente_id
    WHERE cgv.groupe_id = 132
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  catalogue_vente_id={row['catalogue_vente_id']} nom={row['nom']!r} actif={row['actif']}")
else:
    print("  AUCUNE ligne — le groupe 132 n'est relié à aucun produit de vente via comparatif_groupe_vente")
print()

print("--- 3. Toutes les liaisons comparatif_groupe_vente pointant vers Rosbeef cuit (id=114) ---")
cur.execute("""
    SELECT cgv.groupe_id, cg.nom AS groupe_nom, cgv.catalogue_vente_id
    FROM comparatif_groupe_vente cgv
    LEFT JOIN comparatif_groupe cg ON cg.id = cgv.groupe_id
    WHERE cgv.catalogue_vente_id = 114
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  groupe_id={row['groupe_id']} groupe_nom={row['groupe_nom']!r} -> catalogue_vente_id=114")
else:
    print("  AUCUNE — Rosbeef cuit (id=114) n'est relié à aucun groupe comparatif")
print()

print("--- 4. Lignes fournisseur du groupe #132 (comparatif_groupe_ligne) ---")
cur.execute("""
    SELECT cgl.catalogue_fournisseur_id, cf.designation, cf.fournisseur_id
    FROM comparatif_groupe_ligne cgl
    LEFT JOIN catalogue_fournisseur cf ON cf.id = cgl.catalogue_fournisseur_id
    WHERE cgl.groupe_id = 132
""")
rows = cur.fetchall()
print(f"  {len(rows)} article(s) d'achat rattaché(s) au groupe #132 :")
for row in rows:
    print(f"    id={row['catalogue_fournisseur_id']:<6} {row['designation']}")
print()

print("--- 5. Autres groupes comparatifs contenant 'Boeuf'/'Rosbeef' dans le nom ---")
cur.execute("""
    SELECT id, nom, sous_famille, catalogue_vente_id
    FROM comparatif_groupe
    WHERE nom LIKE '%oeuf%' OR nom LIKE '%osbeef%' OR nom LIKE '%osbif%'
""")
for row in cur.fetchall():
    print(f"  id={row['id']} nom={row['nom']!r} sous_famille={row['sous_famille']} catalogue_vente_id(legacy)={row['catalogue_vente_id']}")
print()

print("--- 6. ligne_choisie_id du groupe #132 (arbitrage manuel prix de référence) ---")
cur.execute("SELECT ligne_choisie_id FROM comparatif_groupe WHERE id = 132")
r = cur.fetchone()
if r and r["ligne_choisie_id"]:
    cur.execute("SELECT id, designation FROM catalogue_fournisseur WHERE id = ?", (r["ligne_choisie_id"],))
    cf = cur.fetchone()
    print(f"  ligne_choisie_id={r['ligne_choisie_id']} -> {dict(cf) if cf else 'INTROUVABLE (orphelin)'}")
else:
    print("  Aucune ligne choisie (NULL)")
print()

print("=== Fin de l'audit ===")
conn.close()

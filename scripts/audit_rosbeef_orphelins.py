#!/usr/bin/env python3
"""
audit_rosbeef_orphelins.py — Vérifie l'état du catalogue_vente "Rosbeef cuit"
après suppression du doublon (id 106 ou 114) et de "Rosbeef cru".

Lecture seule, ne modifie rien.

    python3 scripts/audit_rosbeef_orphelins.py [chemin/vers/haccp.db]
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

# 1) Etat actuel du catalogue_vente pour rosbeef
print("--- 1. catalogue_vente (recherche rosbeef) ---")
cur.execute("""
    SELECT id, nom, actif, code_vente
    FROM catalogue_vente
    WHERE nom LIKE '%osbeef%' OR nom LIKE '%osbif%' OR nom LIKE '%oast beef%'
""")
rows = cur.fetchall()
ids_vente = [r["id"] for r in rows]
for r in rows:
    print(f"  id={r['id']:<5} nom={r['nom']!r:<30} actif={r['actif']} code_vente={r['code_vente']}")
if not rows:
    print("  (aucun résultat — vérifier l'orthographe ou que la base est la bonne)")
print()

# 2) Existence des anciens id connus 106 et 114
print("--- 2. Anciens id connus (106 et 114) ---")
for old_id in (106, 114):
    cur.execute("SELECT id, nom, actif FROM catalogue_vente WHERE id = ?", (old_id,))
    r = cur.fetchone()
    if r:
        print(f"  id={old_id} EXISTE ENCORE -> nom={r['nom']!r} actif={r['actif']}")
    else:
        print(f"  id={old_id} n'existe plus (supprimé)")
print()

# 3) Références orphelines : tables qui pointent vers catalogue_vente_id
tables_a_verifier = [
    ("recettes", "catalogue_vente_id"),
    ("comparatif_groupe", "catalogue_vente_id"),
    ("comparatif_groupe_vente", "catalogue_vente_id"),
    ("cuissons", "catalogue_vente_id"),
    ("refroidissements", "catalogue_vente_id"),
]

print("--- 3. Recherche de références orphelines (catalogue_vente_id inexistant) ---")
any_orphan = False
for table, col in tables_a_verifier:
    try:
        cur.execute(f"""
            SELECT t.id, t.{col}
            FROM {table} t
            LEFT JOIN catalogue_vente cv ON cv.id = t.{col}
            WHERE t.{col} IS NOT NULL AND cv.id IS NULL
        """)
        orphans = cur.fetchall()
        if orphans:
            any_orphan = True
            print(f"  [{table}] {len(orphans)} ligne(s) orpheline(s) :")
            for o in orphans[:20]:
                print(f"      {table}.id={o['id']}  ->  {col}={o[col]} (INEXISTANT)")
        else:
            print(f"  [{table}] OK — aucune référence orpheline")
    except sqlite3.OperationalError as e:
        print(f"  [{table}] ignoré ({e})")
print()
if not any_orphan:
    print("  ✅ Aucune référence orpheline détectée.")
else:
    print("  ⚠️  Des références orphelines existent — voir détail ci-dessus.")
print()

# 4) Groupe comparatif #132 (Rosbeef cru/cuit selon le doc) — état actuel
print("--- 4. comparatif_groupe #132 (partagé rosbeef cru/cuit dans le doc) ---")
cur.execute("SELECT id, nom, sous_famille, catalogue_vente_id, ligne_choisie_id FROM comparatif_groupe WHERE id = 132")
r = cur.fetchone()
if r:
    print(f"  id=132 nom={r['nom']!r} catalogue_vente_id={r['catalogue_vente_id']} ligne_choisie_id={r['ligne_choisie_id']}")
    if r["catalogue_vente_id"] is not None and r["catalogue_vente_id"] not in ids_vente:
        print(f"  ⚠️  catalogue_vente_id={r['catalogue_vente_id']} ne correspond à aucun rosbeef trouvé en étape 1 !")
else:
    print("  id=132 n'existe pas (ou plus)")
print()

# 5) Combien de groupes comparatifs pointent vers le rosbeef restant
if ids_vente:
    print("--- 5. Groupes comparatifs liés au(x) rosbeef restant(s) ---")
    placeholders = ",".join("?" * len(ids_vente))
    cur.execute(f"""
        SELECT id, nom, sous_famille, catalogue_vente_id
        FROM comparatif_groupe
        WHERE catalogue_vente_id IN ({placeholders})
    """, ids_vente)
    for r in cur.fetchall():
        print(f"  groupe id={r['id']} nom={r['nom']!r} sous_famille={r['sous_famille']} -> catalogue_vente_id={r['catalogue_vente_id']}")
print()

print("=== Fin de l'audit ===")
conn.close()

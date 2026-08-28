#!/usr/bin/env python3
"""
audit_groupe_58_et_couverture.py —
  1. Pourquoi le groupe comparatif de "Parmentier canard gratiné cantal AOP"
     (catalogue_vente_id=58) n'est pas ressorti dans l'audit précédent.
  2. Couverture globale : tous les produits catalogue_vente ACTIFS non reliés
     à AUCUN groupe comparatif (donc à aucun catalogue_fournisseur_id).

Lecture seule, ne modifie rien.

    python3 scripts/audit_groupe_58_et_couverture.py [chemin/vers/haccp.db]
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

print("--- 1. Toute ligne comparatif_groupe_vente pour catalogue_vente_id=58 ---")
cur.execute("""
    SELECT cgv.groupe_id, cg.nom AS groupe_nom, cgv.catalogue_vente_id
    FROM comparatif_groupe_vente cgv
    LEFT JOIN comparatif_groupe cg ON cg.id = cgv.groupe_id
    WHERE cgv.catalogue_vente_id = 58
""")
rows = cur.fetchall()
if rows:
    for r in rows:
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
    print("  Toujours aucune ligne trouvée pour catalogue_vente_id=58.")
print()

print("--- 2. Tous les groupes dont le NOM contient 'armentier' (au cas où le lien serait ailleurs) ---")
cur.execute("SELECT id, nom FROM comparatif_groupe WHERE LOWER(nom) LIKE '%armentier%'")
for g in cur.fetchall():
    print(f"  groupe id={g['id']} nom={g['nom']!r}")
    cur.execute("""
        SELECT catalogue_vente_id, (SELECT nom FROM catalogue_vente WHERE id = catalogue_vente_id) AS nom
        FROM comparatif_groupe_vente WHERE groupe_id = ?
    """, (g["id"],))
    for v in cur.fetchall():
        print(f"      vente lié : id={v['catalogue_vente_id']} {v['nom']}")
    cur.execute("""
        SELECT gl.catalogue_fournisseur_id, cf.designation
        FROM comparatif_groupe_ligne gl LEFT JOIN catalogue_fournisseur cf ON cf.id = gl.catalogue_fournisseur_id
        WHERE gl.groupe_id = ?
    """, (g["id"],))
    for l in cur.fetchall():
        print(f"      achat lié : id={l['catalogue_fournisseur_id']} {l['designation']}")
print()

print("--- 3. Couverture globale : produits catalogue_vente ACTIFS sans AUCUN groupe comparatif ---")
cur.execute("""
    SELECT v.id, v.nom, v.famille, v.sous_famille
    FROM catalogue_vente v
    WHERE v.boutique_id = 1 AND v.actif = 1
      AND v.id NOT IN (SELECT catalogue_vente_id FROM comparatif_groupe_vente)
    ORDER BY v.famille, v.sous_famille, v.nom
""")
rows = cur.fetchall()
print(f"  {len(rows)} produit(s) de vente actif(s) SANS lien vers un groupe comparatif :")
for r in rows:
    print(f"      id={r['id']:<5} {r['nom']:<45} famille={r['famille']} / {r['sous_famille']}")
print()

print("--- 4. Total produits catalogue_vente actifs (pour contexte) ---")
cur.execute("SELECT COUNT(*) AS n FROM catalogue_vente WHERE boutique_id = 1 AND actif = 1")
print(f"  {cur.fetchone()['n']} produit(s) actif(s) au total")

print("\n=== Fin de l'audit ===")
conn.close()

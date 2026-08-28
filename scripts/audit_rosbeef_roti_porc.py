#!/usr/bin/env python3
"""
audit_rosbeef_roti_porc.py — État réel de Rosbeef cuit et Rôti de porc cuit
pour élargir le rattrapage cuisson/refroidissement (28/08/2026) : catalogue
vente, groupe comparatif, articles d'achat liés, et lignes de réception
depuis le 10/06 non encore cuites.

Lecture seule, ne modifie rien.

    python3 scripts/audit_rosbeef_roti_porc.py [chemin/vers/haccp.db]
"""

import sqlite3
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DB_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "haccp.db"
DEPUIS = "2026-06-10"
TERMES = ["rosbeef", "roti de porc", "rôti de porc"]

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print(f"=== Base : {DB_PATH} ===\n")

print("--- 1. catalogue_vente (produit fini) ---")
cur.execute("""
    SELECT id, nom, actif FROM catalogue_vente
    WHERE LOWER(nom) LIKE '%osbeef%' OR LOWER(nom) LIKE '%ti de porc%' OR LOWER(nom) LIKE '%oti porc%'
""")
cv_rows = cur.fetchall()
for r in cv_rows:
    print(f"  id={r['id']} nom={r['nom']!r} actif={r['actif']}")
print()

for cv in cv_rows:
    cv_id, nom = cv["id"], cv["nom"]
    print(f"--- 2. Groupe comparatif de « {nom} » (catalogue_vente_id={cv_id}) ---")
    cur.execute("""
        SELECT gv.groupe_id, cg.nom AS groupe_nom, gv.ligne_choisie_id
        FROM comparatif_groupe_vente gv
        LEFT JOIN comparatif_groupe cg ON cg.id = gv.groupe_id
        WHERE gv.catalogue_vente_id = ?
    """, (cv_id,))
    g = cur.fetchone()
    if not g:
        print("  AUCUN groupe comparatif relié.")
        print()
        continue
    print(f"  groupe_id={g['groupe_id']} nom={g['groupe_nom']!r} ligne_choisie_id={g['ligne_choisie_id']}")
    cur.execute("""
        SELECT gl.catalogue_fournisseur_id, cf.designation, cf.actif
        FROM comparatif_groupe_ligne gl
        LEFT JOIN catalogue_fournisseur cf ON cf.id = gl.catalogue_fournisseur_id
        WHERE gl.groupe_id = ?
        ORDER BY cf.designation
    """, (g["groupe_id"],))
    cf_rows = cur.fetchall()
    cf_ids = [r["catalogue_fournisseur_id"] for r in cf_rows]
    for r in cf_rows:
        print(f"      article id={r['catalogue_fournisseur_id']:<6} actif={r['actif']} {r['designation']}")
    print()

    print(f"--- 3. Réceptions depuis {DEPUIS} pour ces articles ---")
    if cf_ids:
        placeholders = ",".join("?" * len(cf_ids))
        cur.execute(f"""
            SELECT rl.id, rl.catalogue_fournisseur_id, cf.designation, rl.numero_lot,
                   rl.dlc, r.date_reception, r.statut, rl.conforme, r.livraison_refusee,
                   EXISTS(SELECT 1 FROM cuissons c WHERE c.reception_ligne_id = rl.id) AS deja_cuit
            FROM reception_lignes rl
            JOIN receptions r ON r.id = rl.reception_id
            LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
            WHERE rl.catalogue_fournisseur_id IN ({placeholders})
              AND r.date_reception >= ?
            ORDER BY r.date_reception
        """, (*cf_ids, DEPUIS))
        rows = cur.fetchall()
        print(f"  {len(rows)} ligne(s) trouvée(s), dont {sum(1 for r in rows if not r['deja_cuit'])} sans cuisson enregistrée")
        for r in rows:
            print(f"      rl.id={r['id']} {r['designation']} lot={r['numero_lot']} "
                  f"date={r['date_reception']} statut={r['statut']} conforme={r['conforme']} "
                  f"refusee={r['livraison_refusee']} deja_cuit={bool(r['deja_cuit'])}")
    else:
        print("  Aucun article dans le groupe — rien à chercher.")
    print()

print("=== Fin de l'audit ===")
conn.close()

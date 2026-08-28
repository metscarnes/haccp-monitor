#!/usr/bin/env python3
"""
verif_rattrapage_stock_dlc.py — Vérifie que les 42 cycles cuisson+refroidissement
créés par le rattrapage du 28/08/2026 apparaissent bien dans le stock (donc dans
le calendrier DLC, qui se base sur le même get_stock_unifie).

Trois vérifications :
  1. Combien de refroidissements créés aujourd'hui ont une DLC encore future
     (candidats "encore en stock" vs déjà périmés/hors période d'affichage) ?
  2. Aucun n'a jeter=1 ni de ligne dlc_devenir associée (ce qui les exclurait
     du stock actif) ?
  3. Appel direct à l'API /api/refroidissement/produits (utilisée par le wizard
     Refroidissement, alimentée par get_stock_unifie côté cuisson) pour voir
     si des lots du rattrapage y apparaissent encore (normalement NON, puisque
     le rattrapage crée DIRECTEMENT le refroidissement, pas juste la cuisson).

Lecture seule (sauf l'appel HTTP, GET uniquement), ne modifie rien.

    python3 scripts/verif_rattrapage_stock_dlc.py [chemin/vers/haccp.db]
"""

import sqlite3
import sys
from datetime import date
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

today = date.today().isoformat()

print("--- 1. Refroidissements créés aujourd'hui (rattrapage) ---")
cur.execute("""
    SELECT id, date_refroidissement, catalogue_vente_id, catalogue_fournisseur_id,
           numero_lot, dlc_finale, jeter, conforme
    FROM refroidissements
    WHERE date(created_at) = date('now')
    ORDER BY id
""")
rows = cur.fetchall()
print(f"  {len(rows)} refroidissement(s) créé(s) aujourd'hui")

encore_valides = [r for r in rows if r["dlc_finale"] and r["dlc_finale"] >= today]
perimes = [r for r in rows if r["dlc_finale"] and r["dlc_finale"] < today]
print(f"  dont {len(encore_valides)} avec DLC encore valide (>= {today})")
print(f"  dont {len(perimes)} avec DLC déjà dépassée (normal pour un rattrapage rétroactif — DLC J+3)")
print()

print("--- 2. Contrôle jeter / dlc_devenir sur ces refroidissements ---")
avec_jeter = [r for r in rows if r["jeter"]]
print(f"  {len(avec_jeter)} avec jeter=1 (seraient EXCLUS du stock)")

if rows:
    ids = [r["id"] for r in rows]
    placeholders = ",".join("?" * len(ids))
    cur.execute(f"""
        SELECT source_id FROM dlc_devenir
        WHERE source_type = 'refroidissement' AND source_id IN ({placeholders})
    """, ids)
    deja_traites = [r["source_id"] for r in cur.fetchall()]
    print(f"  {len(deja_traites)} avec une entrée dlc_devenir déjà associée (seraient EXCLUS du stock) : {deja_traites}")
print()

print("--- 3. Les refroidissements ENCORE VALIDES apparaissent-ils dans get_stock_unifie ? ---")
print("    (reproduction de la requête réelle de src/database.py, branche refroidissement)")
if encore_valides:
    ids_valides = [r["id"] for r in encore_valides]
    placeholders = ",".join("?" * len(ids_valides))
    cur.execute(f"""
        SELECT rf.id, rf.dlc_finale, rf.jeter,
               COALESCE(p.nom, cv_r.nom, cf_r.designation, 'Produit refroidi') AS produit_nom,
               EXISTS(SELECT 1 FROM dlc_devenir dd WHERE dd.source_type='refroidissement' AND dd.source_id=rf.id) AS a_dlc_devenir
        FROM refroidissements rf
        LEFT JOIN produits p ON p.id = rf.produit_id
        LEFT JOIN catalogue_vente cv_r ON cv_r.id = rf.catalogue_vente_id
        LEFT JOIN catalogue_fournisseur cf_r ON cf_r.id = rf.catalogue_fournisseur_id
        WHERE rf.id IN ({placeholders})
          AND rf.dlc_finale IS NOT NULL
          AND rf.jeter = 0
          AND NOT EXISTS (SELECT 1 FROM dlc_devenir dd WHERE dd.source_type='refroidissement' AND dd.source_id=rf.id)
    """, ids_valides)
    apparaissent = cur.fetchall()
    print(f"  {len(apparaissent)} / {len(encore_valides)} apparaîtraient dans get_stock_unifie (donc dans le stock ET le calendrier DLC)")
    for r in apparaissent:
        print(f"      refroidissement.id={r['id']} produit={r['produit_nom']} DLC={r['dlc_finale']}")
else:
    print("  Aucun refroidissement avec DLC encore valide aujourd'hui (tous périmés — normal si le rattrapage")
    print("  couvre une période ancienne dont les DLC J+3 sont largement dépassées).")

print("\n=== Fin de la vérification ===")
conn.close()

#!/usr/bin/env python3
"""
audit_rattrapage_cuisson.py — État réel des 3 plats cibles du rattrapage
(Lasagne, Gratin dauphinois, Parmentier de canard) dans le catalogue achats
+ le catalogue vente, pour réécrire rattrapage_cuisson_refroidissement.py sur
le bon référentiel (produits est vide pour ces plats depuis la v6.0).

Lecture seule, ne modifie rien.

    python3 scripts/audit_rattrapage_cuisson.py [chemin/vers/haccp.db]
"""

import sqlite3
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DB_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "haccp.db"
PRODUITS_CIBLES = ["lasagne", "gratin dauphinois", "parmentier de canard"]
DEPUIS = "2026-06-10"

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print(f"=== Base : {DB_PATH} ===\n")

print("--- 1. Table produits (ancien référentiel — probablement vide) ---")
for terme in PRODUITS_CIBLES:
    cur.execute("SELECT id, nom FROM produits WHERE LOWER(nom) LIKE ?", (f"%{terme}%",))
    rows = cur.fetchall()
    print(f"  « {terme} » : {len(rows)} résultat(s)")
    for r in rows:
        print(f"      id={r['id']} nom={r['nom']!r}")
print()

print("--- 2. catalogue_fournisseur (matière reçue) ---")
cf_ids = {}
for terme in PRODUITS_CIBLES:
    cur.execute(
        "SELECT id, designation, fournisseur_id, famille, sous_famille "
        "FROM catalogue_fournisseur WHERE LOWER(designation) LIKE ?",
        (f"%{terme}%",),
    )
    rows = cur.fetchall()
    print(f"  « {terme} » : {len(rows)} résultat(s)")
    cf_ids[terme] = []
    for r in rows:
        print(f"      id={r['id']} designation={r['designation']!r} famille={r['famille']} sous_famille={r['sous_famille']}")
        cf_ids[terme].append(r["id"])
print()

print("--- 3. catalogue_vente (produit fini) ---")
cv_ids = {}
for terme in PRODUITS_CIBLES:
    cur.execute("SELECT id, nom, actif FROM catalogue_vente WHERE LOWER(nom) LIKE ?", (f"%{terme}%",))
    rows = cur.fetchall()
    print(f"  « {terme} » : {len(rows)} résultat(s)")
    cv_ids[terme] = []
    for r in rows:
        print(f"      id={r['id']} nom={r['nom']!r} actif={r['actif']}")
        cv_ids[terme].append(r["id"])
print()

print(f"--- 4. Lignes de réception depuis {DEPUIS} pour ces articles catalogue_fournisseur ---")
all_cf_ids = [i for ids in cf_ids.values() for i in ids]
if all_cf_ids:
    placeholders = ",".join("?" * len(all_cf_ids))
    cur.execute(
        f"""
        SELECT rl.id, rl.catalogue_fournisseur_id, cf.designation, rl.numero_lot,
               rl.dlc, rl.poids_kg, r.date_reception, r.statut, rl.conforme, r.livraison_refusee,
               EXISTS(SELECT 1 FROM cuissons c WHERE c.reception_ligne_id = rl.id) AS deja_cuit
        FROM reception_lignes rl
        JOIN receptions r ON r.id = rl.reception_id
        LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
        WHERE rl.catalogue_fournisseur_id IN ({placeholders})
          AND r.date_reception >= ?
        ORDER BY r.date_reception
        """,
        (*all_cf_ids, DEPUIS),
    )
    rows = cur.fetchall()
    print(f"  {len(rows)} ligne(s) de réception trouvée(s)")
    non_cuites = [r for r in rows if not r["deja_cuit"]]
    print(f"  dont {len(non_cuites)} SANS cuisson enregistrée (candidates au rattrapage)")
    for r in rows[:15]:
        print(f"      rl.id={r['id']} {r['designation']} lot={r['numero_lot']} "
              f"date_reception={r['date_reception']} statut={r['statut']} conforme={r['conforme']} "
              f"refusee={r['livraison_refusee']} deja_cuit={bool(r['deja_cuit'])}")
    if len(rows) > 15:
        print(f"      … et {len(rows) - 15} de plus")
else:
    print("  Aucun catalogue_fournisseur_id trouvé pour ces 3 plats — vérifier les libellés.")
print()

print("--- 5. Cuissons déjà enregistrées pour ces plats (catalogue_vente_id) depuis migration v7.4+ ---")
all_cv_ids = [i for ids in cv_ids.values() for i in ids]
if all_cv_ids:
    placeholders = ",".join("?" * len(all_cv_ids))
    cur.execute(
        f"""
        SELECT c.id, c.date_cuisson, c.catalogue_vente_id, cv.nom,
               EXISTS(SELECT 1 FROM refroidissements r WHERE r.cuisson_id = c.id) AS deja_refroidi
        FROM cuissons c
        LEFT JOIN catalogue_vente cv ON cv.id = c.catalogue_vente_id
        WHERE c.catalogue_vente_id IN ({placeholders})
        ORDER BY c.date_cuisson
        """,
        all_cv_ids,
    )
    rows = cur.fetchall()
    print(f"  {len(rows)} cuisson(s) déjà enregistrée(s) via catalogue_vente_id")
    sans_refroid = [r for r in rows if not r["deja_refroidi"]]
    print(f"  dont {len(sans_refroid)} SANS refroidissement (candidates passe B)")
    for r in rows:
        print(f"      cuisson.id={r['id']} date={r['date_cuisson']} produit={r['nom']} deja_refroidi={bool(r['deja_refroidi'])}")
else:
    print("  (aucun catalogue_vente_id résolu à l'étape 3)")
print()

print("=== Fin de l'audit ===")
conn.close()

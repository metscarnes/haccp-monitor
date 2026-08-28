#!/usr/bin/env python3
"""
audit_a_traiter_vide.py — Diagnostique pourquoi GET /api/cuisson/a-traiter
(et le compteur Hub) ne remonte plus aucun lot après ajout du filtre DLC
(28/08/2026). Reconstruit la requête étape par étape pour voir où les lots
sont éliminés : plus aucun lot valide, ou le filtre DLC élimine à tort des
lots dont la DLC est bien future ?

Lecture seule, ne modifie rien.
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

today = date.today().isoformat()
print(f"=== Base : {DB_PATH} === (aujourd'hui = {today})\n")

print("--- 1. Produits suivi_cuisson_auto=1 actuels ---")
cur.execute("SELECT id, nom FROM catalogue_vente WHERE suivi_cuisson_auto = 1")
cv_ids = [r["id"] for r in cur.fetchall()]
for cid in cv_ids:
    cur.execute("SELECT nom FROM catalogue_vente WHERE id=?", (cid,))
    print(f"  id={cid} {cur.fetchone()['nom']}")
print()

if not cv_ids:
    print("Aucun produit marqué — c'est la cause (rien à détecter). Arrêt.")
    sys.exit(0)

placeholders = ",".join("?" * len(cv_ids))

print("--- 2. Réceptions liées à ces produits (via groupe), SANS filtre DLC ni cuisson ---")
cur.execute(f"""
    SELECT rl.id AS reception_ligne_id, rl.catalogue_fournisseur_id,
           COALESCE(cf.designation, rl.designation_libre) AS produit_nom,
           rl.numero_lot, COALESCE(rl.dlc, rl.dluo) AS dlc,
           r.statut, rl.conforme, r.livraison_refusee,
           EXISTS(SELECT 1 FROM cuissons c WHERE c.reception_ligne_id = rl.id) AS deja_cuit
    FROM reception_lignes rl
    JOIN receptions r ON r.id = rl.reception_id
    JOIN comparatif_groupe_ligne gl ON gl.catalogue_fournisseur_id = rl.catalogue_fournisseur_id
    JOIN comparatif_groupe_vente gv ON gv.groupe_id = gl.groupe_id
    LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
    WHERE gv.catalogue_vente_id IN ({placeholders})
    ORDER BY rl.id DESC
    LIMIT 30
""", cv_ids)
rows = cur.fetchall()
print(f"  {len(rows)} ligne(s) trouvée(s) (max 30 affichées)")
for r in rows:
    dlc = r["dlc"] or "—"
    dlc_ok = "✅" if (r["dlc"] is None or r["dlc"] >= today) else "❌ PÉRIMÉ"
    print(f"    rl.id={r['reception_ligne_id']:<5} {r['produit_nom']:<40} lot={r['numero_lot']!s:<25} "
          f"dlc={dlc:<12} {dlc_ok}  statut={r['statut']:<10} conforme={r['conforme']} "
          f"refusee={r['livraison_refusee']} deja_cuit={bool(r['deja_cuit'])}")

print("\n--- 3. Résumé ---")
total = len(rows)
non_cuits = sum(1 for r in rows if not r["deja_cuit"])
non_cuits_valides = sum(1 for r in rows if not r["deja_cuit"] and (r["dlc"] is None or r["dlc"] >= today))
print(f"  Total lignes (30 dernières) : {total}")
print(f"  Non encore cuites : {non_cuits}")
print(f"  Non cuites ET DLC valide/absente : {non_cuits_valides}  <- doit matcher a-traiter")

print("\n=== Fin de l'audit ===")
conn.close()

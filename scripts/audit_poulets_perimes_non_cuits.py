#!/usr/bin/env python3
"""
audit_poulets_perimes_non_cuits.py — Liste EXHAUSTIVE de tous les lots
"suivi cuisson auto" jamais cuits, périmés ou non, sans limite de résultats
(contrairement à audit_a_traiter_vide.py qui se limitait aux 30 dernières
lignes). Sert à décider s'il faut un rattrapage ciblé (cuisson réelle non
saisie) ou constater une vraie perte matière (jetés sans être cuits).

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

cur.execute("SELECT id, nom FROM catalogue_vente WHERE suivi_cuisson_auto = 1")
cv_ids = [r["id"] for r in cur.fetchall()]
if not cv_ids:
    print("Aucun produit marqué — arrêt.")
    sys.exit(0)

placeholders = ",".join("?" * len(cv_ids))

print("--- TOUS les lots suivi_cuisson_auto jamais cuits (sans limite) ---")
cur.execute(f"""
    SELECT rl.id AS reception_ligne_id, rl.catalogue_fournisseur_id,
           COALESCE(cf.designation, rl.designation_libre) AS produit_nom,
           rl.numero_lot, COALESCE(rl.dlc, rl.dluo) AS dlc,
           r.date_reception, r.statut, rl.conforme, r.livraison_refusee,
           f.nom AS fournisseur_nom,
           EXISTS(SELECT 1 FROM dlc_devenir dd WHERE dd.source_type='reception_ligne' AND dd.source_id=rl.id) AS a_dlc_devenir
    FROM reception_lignes rl
    JOIN receptions r ON r.id = rl.reception_id
    JOIN comparatif_groupe_ligne gl ON gl.catalogue_fournisseur_id = rl.catalogue_fournisseur_id
    JOIN comparatif_groupe_vente gv ON gv.groupe_id = gl.groupe_id
    LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
    LEFT JOIN fournisseurs f ON f.id = rl.fournisseur_id
    WHERE gv.catalogue_vente_id IN ({placeholders})
      AND r.statut = 'cloturee'
      AND rl.conforme = 1
      AND r.livraison_refusee = 0
      AND NOT EXISTS (SELECT 1 FROM cuissons c WHERE c.reception_ligne_id = rl.id)
    ORDER BY r.date_reception ASC
""", cv_ids)
rows = cur.fetchall()

print(f"  {len(rows)} lot(s) jamais cuit(s) au total\n")

perimes = [r for r in rows if r["dlc"] and r["dlc"] < today]
valides = [r for r in rows if not r["dlc"] or r["dlc"] >= today]
perimes_avec_devenir = [r for r in perimes if r["a_dlc_devenir"]]
perimes_sans_devenir = [r for r in perimes if not r["a_dlc_devenir"]]

print(f"  Périmés : {len(perimes)}  (dont {len(perimes_avec_devenir)} déjà marqués dans dlc_devenir, "
      f"{len(perimes_sans_devenir)} SANS trace de sortie de stock)")
print(f"  Encore valides : {len(valides)}\n")

print("--- Détail périmés SANS entrée dlc_devenir (ni cuits, ni tracés comme jetés/perdus) ---")
for r in perimes_sans_devenir:
    print(f"    rl.id={r['reception_ligne_id']:<5} {r['produit_nom']:<45} lot={r['numero_lot']!s:<20} "
          f"reçu={r['date_reception']} dlc={r['dlc']}  {r['fournisseur_nom'] or ''}")

if perimes_avec_devenir:
    print("\n--- Périmés déjà marqués dlc_devenir (sortie de stock déjà tracée) ---")
    for r in perimes_avec_devenir:
        print(f"    rl.id={r['reception_ligne_id']:<5} {r['produit_nom']:<45} lot={r['numero_lot']!s:<20} "
              f"reçu={r['date_reception']} dlc={r['dlc']}")

print("\n--- Répartition par produit (parmi les périmés sans dlc_devenir) ---")
compte = {}
for r in perimes_sans_devenir:
    compte[r["produit_nom"]] = compte.get(r["produit_nom"], 0) + 1
for nom, n in sorted(compte.items(), key=lambda kv: -kv[1]):
    print(f"    {n:>3}  {nom}")

print("\n=== Fin de l'audit ===")
conn.close()

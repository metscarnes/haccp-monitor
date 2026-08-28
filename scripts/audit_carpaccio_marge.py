#!/usr/bin/env python3
"""
audit_carpaccio_marge.py — Diagnostique la marge aberrante affichée pour
Carpaccio (-238,46 €/pièce, coefficient x0.04) : quelle ligne d'achat est
choisie comme référence, et quelles valeurs brutes produisent ce calcul.

Lecture seule, ne modifie rien.

    python3 scripts/audit_carpaccio_marge.py [chemin/vers/haccp.db]
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

print("--- 1. catalogue_vente : Carpaccio ---")
cur.execute("SELECT * FROM catalogue_vente WHERE nom LIKE '%arpaccio%'")
rows = cur.fetchall()
for r in rows:
    print(f"  {dict(r)}")
print()

if not rows:
    print("Aucun Carpaccio trouvé — arrêt.")
    sys.exit(0)

cv_id = rows[0]["id"]

print(f"--- 2. Groupe comparatif + ligne_choisie_id pour catalogue_vente_id={cv_id} ---")
cur.execute("""
    SELECT gv.groupe_id, gv.ligne_choisie_id, cg.nom AS groupe_nom
    FROM comparatif_groupe_vente gv
    LEFT JOIN comparatif_groupe cg ON cg.id = gv.groupe_id
    WHERE gv.catalogue_vente_id = ?
""", (cv_id,))
r = cur.fetchone()
if not r:
    print("  Pas de groupe comparatif relié.")
    sys.exit(0)
print(f"  groupe_id={r['groupe_id']} nom={r['groupe_nom']!r} ligne_choisie_id={r['ligne_choisie_id']}")
print()

if r["ligne_choisie_id"]:
    print("--- 3. Ligne d'achat choisie (catalogue_fournisseur) — TOUTES les colonnes prix ---")
    cur.execute("""
        SELECT id, designation, fournisseur_id, format_prix, prix_achat_ht,
               poids_colis_kg, poids_unitaire_kg, qte_par_colis, unite_colis, famille, sous_famille
        FROM catalogue_fournisseur WHERE id = ?
    """, (r["ligne_choisie_id"],))
    cf = cur.fetchone()
    print(f"  {dict(cf)}")
    print()

    print("--- 4. Reconstruction manuelle du calcul (comme _calc_prix_piece / _calc_prix_kg) ---")
    fp = cf["format_prix"]
    prix = cf["prix_achat_ht"]
    print(f"  format_prix={fp!r}  prix_achat_ht={prix}")
    if fp == "piece":
        print(f"  -> achat_ref_piece = prix tel quel = {prix}")
    elif fp == "colis" and cf["qte_par_colis"]:
        print(f"  -> achat_ref_piece = {prix} / {cf['qte_par_colis']} = {prix / cf['qte_par_colis'] if cf['qte_par_colis'] else None}")
    elif fp == "kg" and cf["poids_unitaire_kg"]:
        print(f"  -> achat_ref_piece = {prix} * poids_unitaire_kg({cf['poids_unitaire_kg']}) = {prix * cf['poids_unitaire_kg']}")
    else:
        print("  -> achat_ref_piece indérivable dans ce format")

    print(f"  -> achat_ref_kg (via _calc_prix_kg) :")
    if fp == "kg":
        print(f"       = prix tel quel = {prix}")
    elif fp == "colis" and cf["poids_colis_kg"]:
        print(f"       = {prix} / poids_colis_kg({cf['poids_colis_kg']}) = {prix / cf['poids_colis_kg'] if cf['poids_colis_kg'] else None}")
    elif fp == "piece" and cf["poids_unitaire_kg"]:
        print(f"       = {prix} / poids_unitaire_kg({cf['poids_unitaire_kg']}) = {prix / cf['poids_unitaire_kg'] if cf['poids_unitaire_kg'] else None}")
    else:
        print("       indérivable dans ce format")
else:
    print("  Aucune ligne_choisie_id (NULL) — marge ne devrait pas être calculable.")

print("\n=== Fin de l'audit ===")
conn.close()

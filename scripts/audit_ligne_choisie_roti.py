#!/usr/bin/env python3
"""
audit_ligne_choisie_roti.py — ligne_choisie_id de « Roti de porc cuit »
(catalogue_vente) et sa désignation, pour restreindre le rattrapage
synthétique à cette seule référence (comme Rosbeef cuit -> Tende tranche).

Lecture seule, ne modifie rien.
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

for nom in ["Rosbeef cuit", "Roti de porc cuit"]:
    cur.execute("SELECT id FROM catalogue_vente WHERE nom = ? AND actif = 1", (nom,))
    r = cur.fetchone()
    if not r:
        print(f"{nom} : introuvable/inactif")
        continue
    cv_id = r["id"]
    cur.execute("""
        SELECT gv.groupe_id, gv.ligne_choisie_id, cf.designation
        FROM comparatif_groupe_vente gv
        LEFT JOIN catalogue_fournisseur cf ON cf.id = gv.ligne_choisie_id
        WHERE gv.catalogue_vente_id = ?
    """, (cv_id,))
    g = cur.fetchone()
    if not g or not g["ligne_choisie_id"]:
        print(f"{nom} (id={cv_id}) : AUCUNE ligne_choisie_id définie — groupe_id={g['groupe_id'] if g else None}")
        continue
    print(f"{nom} (id={cv_id}) : groupe_id={g['groupe_id']} ligne_choisie_id={g['ligne_choisie_id']} désignation={g['designation']!r}")

    # Combien de lots reçus depuis le 10/06 pour cette ligne précise ?
    cur.execute("""
        SELECT COUNT(*) AS n
        FROM reception_lignes rl
        JOIN receptions r ON r.id = rl.reception_id
        WHERE rl.catalogue_fournisseur_id = ?
          AND r.date_reception >= '2026-06-10'
          AND r.statut = 'cloturee' AND rl.conforme = 1 AND r.livraison_refusee = 0
    """, (g["ligne_choisie_id"],))
    print(f"    -> {cur.fetchone()['n']} lot(s) reçu(s) depuis le 10/06 pour cette référence seule")

#!/usr/bin/env python3
"""
verif_3_lots_valides.py — Pourquoi seul 1 des 4 refroidissements du rattrapage
encore sous DLC valide apparaît dans get_stock_unifie. Détail des 4 lots.
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

cur.execute("""
    SELECT rf.id, rf.date_refroidissement, rf.dlc_finale, rf.jeter, rf.conforme,
           rf.catalogue_vente_id, rf.catalogue_fournisseur_id,
           COALESCE(cv.nom, cf.designation) AS produit_nom,
           EXISTS(SELECT 1 FROM dlc_devenir dd WHERE dd.source_type='refroidissement' AND dd.source_id=rf.id) AS a_dlc_devenir
    FROM refroidissements rf
    LEFT JOIN catalogue_vente cv ON cv.id = rf.catalogue_vente_id
    LEFT JOIN catalogue_fournisseur cf ON cf.id = rf.catalogue_fournisseur_id
    WHERE date(rf.created_at) = date('now')
      AND rf.dlc_finale >= ?
    ORDER BY rf.id
""", (today,))

for r in cur.fetchall():
    print(dict(r))

    if r["a_dlc_devenir"]:
        cur.execute("SELECT * FROM dlc_devenir WHERE source_type='refroidissement' AND source_id=?", (r["id"],))
        d = cur.fetchone()
        print(f"    -> dlc_devenir: {dict(d)}")

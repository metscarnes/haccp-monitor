#!/usr/bin/env python3
"""
audit_references_inactives.py — Pourquoi des produits de vente ont-ils pour achat de
référence un article inactif ou introuvable ? Pour chaque cas : état de l'article,
dernières traces d'usage (commandes, réceptions, factures) et articles ACTIFS du même
fournisseur au libellé/code proche (remplaçant probable).

Lecture seule, ne modifie rien.

    python3 scripts/audit_references_inactives.py [chemin/vers/haccp.db]
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


def tables():
    return {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def colonnes(t):
    return {r[1] for r in cur.execute(f"PRAGMA table_info({t})")}


TABLES = tables()

print(f"=== Base : {DB_PATH} ===\n")

cas = cur.execute(
    """SELECT v.nom, gv.groupe_id, gv.ligne_choisie_id AS ref, cf.id AS cf_id, cf.actif,
              cf.designation, cf.code_article, cf.fournisseur_id, cf.date_maj, f.nom AS fournisseur
       FROM comparatif_groupe_vente gv
       JOIN catalogue_vente v ON v.id = gv.catalogue_vente_id
       LEFT JOIN catalogue_fournisseur cf ON cf.id = gv.ligne_choisie_id
       LEFT JOIN fournisseurs f ON f.id = cf.fournisseur_id
       WHERE gv.ligne_choisie_id IS NOT NULL AND v.actif = 1
         AND (cf.id IS NULL OR cf.actif = 0)
       ORDER BY v.nom""").fetchall()

print(f"{len(cas)} produit(s) de vente avec une référence inactive ou introuvable\n")

for c in cas:
    print(f"■ {c['nom']}  (groupe {c['groupe_id']}, référence #{c['ref']})")
    if c["cf_id"] is None:
        print("  → article SUPPRIMÉ définitivement (n'existe plus en base)")
        print()
        continue
    print(f"  → article INACTIF : {c['fournisseur']} · {c['code_article']} · {c['designation']}"
          f" · dernière modif {c['date_maj']}")

    # Dernières traces d'usage de l'article.
    for table, col_date in (("commande_lignes", None), ("reception_lignes", None),
                            ("facture_lignes", None)):
        if table not in TABLES or "catalogue_fournisseur_id" not in colonnes(table):
            continue
        n = cur.execute(f"SELECT COUNT(*) FROM {table} WHERE catalogue_fournisseur_id = ?",
                        (c["ref"],)).fetchone()[0]
        print(f"     utilisé dans {table} : {n} ligne(s)")

    # Autres articles du groupe (actifs ?).
    autres = cur.execute(
        """SELECT cf.id, cf.actif, cf.code_article, cf.designation, cf.prix_achat_ht, cf.format_prix
           FROM comparatif_groupe_ligne gl JOIN catalogue_fournisseur cf ON cf.id = gl.catalogue_fournisseur_id
           WHERE gl.groupe_id = ? AND cf.id != ?""", (c["groupe_id"], c["ref"])).fetchall()
    for a in autres:
        print(f"     autre ligne du groupe : #{a['id']} {'actif' if a['actif'] else 'INACTIF'} · "
              f"{a['code_article']} · {a['designation']} · {a['prix_achat_ht']} €/{a['format_prix']}")

    # Remplaçant probable : même fournisseur, actif, même racine de code ou premier mot commun.
    racine = (c["code_article"] or "").split("-")[0].lstrip("0")
    mot = ((c["designation"] or "").split() or [""])[0]
    proches = cur.execute(
        """SELECT id, code_article, designation, prix_achat_ht, format_prix, date_maj
           FROM catalogue_fournisseur
           WHERE fournisseur_id = ? AND actif = 1 AND id != ?
             AND (LTRIM(code_article, '0') LIKE ? OR designation LIKE ?)
           LIMIT 5""",
        (c["fournisseur_id"], c["ref"], racine + "%", "%" + mot + "%")).fetchall()
    for p in proches:
        print(f"     remplaçant possible (actif) : #{p['id']} · {p['code_article']} · {p['designation']}"
              f" · {p['prix_achat_ht']} €/{p['format_prix']} · créé/modifié {p['date_maj']}")
    print()

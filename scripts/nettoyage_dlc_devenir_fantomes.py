#!/usr/bin/env python3
"""
nettoyage_dlc_devenir_fantomes.py — Supprime 6 entrées dlc_devenir orphelines
(type 'refroidissement', créées le 05-08/05/2026, statut='annule') dont la
ligne `refroidissements` d'origine a disparu lors du rebuild de table v7.4
(DROP/CREATE — cf. POINT_CHAINE_CUISSON_REFROIDISSEMENT.md §3.3).

Découvert le 28/08/2026 : le rattrapage cuisson/refroidissement (voir
rattrapage_cuisson_refroidissement.py) a créé de nouvelles lignes
`refroidissements` dont l'AUTOINCREMENT a recyclé les id 21, 22, 24, 25, 26, 27
— déjà référencés par ces 6 entrées dlc_devenir fantômes. Conséquence :
get_stock_unifie() (NOT EXISTS dlc_devenir WHERE source_id = rf.id) excluait
à tort 3 des nouveaux refroidissements du stock/calendrier DLC alors qu'ils
sont valides et non jetés.

Confirmé par audit_dlc_devenir_orphelins.py : les 6 lignes ci-dessous ont
dlc_devenir.created_at < refroidissements.created_at pour le même source_id
— preuve qu'elles ne peuvent PAS référencer la ligne actuelle.

Par défaut : DRY-RUN — affiche ce qui serait supprimé, n'écrit rien.
Ajouter --commit pour supprimer réellement.

    python3 scripts/nettoyage_dlc_devenir_fantomes.py [chemin/vers/haccp.db]
    python3 scripts/nettoyage_dlc_devenir_fantomes.py --commit
"""

import argparse
import sqlite3
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DB_PATH_DEFAUT = Path(__file__).parent.parent / "haccp.db"

# Identifiants exacts confirmés par audit_dlc_devenir_orphelins.py (28/08/2026).
# Volontairement une liste fermée, pas une requête générique : on ne supprime
# QUE ce qui a été vérifié un par un, pas "tout ce qui ressemble à un fantôme".
DLC_DEVENIR_IDS_FANTOMES = [239, 249, 250, 251, 252, 253]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("db_path", nargs="?", default=str(DB_PATH_DEFAUT))
    parser.add_argument("--commit", action="store_true",
                         help="Supprime réellement (défaut : dry-run, aucune écriture)")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"ERREUR : base introuvable : {db_path}")
        sys.exit(1)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    print(f"Base ciblée : {db_path}")
    print(f"Mode        : {'COMMIT (suppression réelle)' if args.commit else 'DRY-RUN (aucune écriture)'}")
    print()

    placeholders = ",".join("?" for _ in DLC_DEVENIR_IDS_FANTOMES)
    rows = con.execute(
        f"SELECT * FROM dlc_devenir WHERE id IN ({placeholders})",
        DLC_DEVENIR_IDS_FANTOMES,
    ).fetchall()

    print(f"--- {len(rows)} entrée(s) trouvée(s) sur {len(DLC_DEVENIR_IDS_FANTOMES)} attendue(s) ---")
    for r in rows:
        print(f"  id={r['id']} source_type={r['source_type']} source_id={r['source_id']} "
              f"statut={r['statut']} created_at={r['created_at']}")

    if len(rows) != len(DLC_DEVENIR_IDS_FANTOMES):
        trouves = {r["id"] for r in rows}
        manquants = set(DLC_DEVENIR_IDS_FANTOMES) - trouves
        print(f"\n⚠ {len(manquants)} id attendu(s) introuvable(s) : {sorted(manquants)} "
              f"(déjà supprimés, ou base différente de celle auditée — à vérifier avant de continuer).")

    print()
    if args.commit:
        con.execute(f"DELETE FROM dlc_devenir WHERE id IN ({placeholders})", DLC_DEVENIR_IDS_FANTOMES)
        con.commit()
        print(f"✅ {len(rows)} entrée(s) supprimée(s).")
    else:
        print(f"ℹ️  DRY-RUN : {len(rows)} entrée(s) seraient supprimées. Relance avec --commit pour écrire réellement.")

    con.close()


if __name__ == "__main__":
    main()

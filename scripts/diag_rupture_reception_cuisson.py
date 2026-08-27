#!/usr/bin/env python3
"""
diag_rupture_reception_cuisson.py — Audit de la rupture Réception → Cuisson

Contexte : la migration v6.0 a basculé la Production vers les catalogues
Achats/Vente (`recettes.produit_fini_id` → `recettes.catalogue_vente_id`,
`reception_lignes.produit_id` devenu nullable au profit de
`catalogue_fournisseur_id`). Les modules Cuisson et Refroidissement, eux,
sont restés sur l'ancien modèle `produits` :

  • cuissons.produit_id / refroidissements.produit_id sont NOT NULL → FK produits
  • routes_cuisson.py interroge encore `rec.produit_fini_id` (colonne disparue)

Ce script mesure l'ampleur réelle des dégâts sur la base de PROD. Il ne
modifie RIEN (lecture seule).

    python3 scripts/diag_rupture_reception_cuisson.py [chemin/vers/haccp.db]

Sans argument : haccp.db à la racine du dépôt.
"""

import sqlite3
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DB_PATH_DEFAUT = Path(__file__).parent.parent / "haccp.db"


def section(titre):
    print()
    print("=" * 72)
    print(titre)
    print("=" * 72)


def main():
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DB_PATH_DEFAUT
    if not db_path.exists():
        print(f"ERREUR : base introuvable : {db_path}")
        sys.exit(1)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    print(f"Base analysée : {db_path}")

    def colonnes(table):
        return {r[1] for r in cur.execute(f"PRAGMA table_info({table})")}

    # ── 1. État du schéma ────────────────────────────────────────────────
    section("1. SCHÉMA — quel modèle chaque table utilise-t-elle ?")
    cols_rec = colonnes("recettes")
    cols_rl  = colonnes("reception_lignes")
    migre_v6 = "catalogue_vente_id" in cols_rec
    print(f"  recettes         : {'catalogue_vente_id (v6 ✓)' if migre_v6 else 'produit_fini_id (pré-v6)'}")
    print(f"  reception_lignes : produit_id={'oui' if 'produit_id' in cols_rl else 'NON'}, "
          f"catalogue_fournisseur_id={'oui' if 'catalogue_fournisseur_id' in cols_rl else 'NON'}")
    print(f"  cuissons         : produit_id → produits (ancien modèle)")

    if migre_v6:
        print()
        print("  ⚠ INCOHÉRENCE : recettes est en v6 mais routes_cuisson.py interroge")
        print("    encore `rec.produit_fini_id` → GET /api/cuisson/produits/{id}/receptions")
        print("    renvoie HTTP 500 à CHAQUE appel (chemin critique du wizard Cuisson).")

    # ── 2. Lignes de réception orphelines ────────────────────────────────
    section("2. RÉCEPTIONS — combien de lots sont invisibles pour la Cuisson ?")
    tot = cur.execute("SELECT COUNT(*) FROM reception_lignes").fetchone()[0]
    sans = cur.execute("SELECT COUNT(*) FROM reception_lignes WHERE produit_id IS NULL").fetchone()[0]
    print(f"  lignes de réception au total : {tot}")
    print(f"  dont SANS produit_id         : {sans}"
          + (f"  ({100*sans//tot} %)" if tot else ""))

    stock_sql = """
        FROM reception_lignes rl
        JOIN receptions r ON r.id = rl.reception_id
        WHERE r.statut='cloturee' AND rl.conforme=1 AND r.livraison_refusee=0
          AND (COALESCE(rl.dlc, rl.dluo) IS NULL OR COALESCE(rl.dlc, rl.dluo) >= DATE('now'))
          AND NOT EXISTS (SELECT 1 FROM dlc_devenir d
                          WHERE d.source_type='reception_ligne' AND d.source_id=rl.id)
    """
    stock_tot  = cur.execute("SELECT COUNT(*) " + stock_sql).fetchone()[0]
    stock_sans = cur.execute("SELECT COUNT(*) " + stock_sql + " AND rl.produit_id IS NULL").fetchone()[0]
    print()
    print(f"  EN STOCK VIVANT aujourd'hui  : {stock_tot}")
    print(f"  dont NON CUISINABLES         : {stock_sans}   ← produit_id NULL, POST cuisson = HTTP 422")

    if stock_sans:
        print()
        print("  Échantillon des lots bloqués :")
        rows = cur.execute("""
            SELECT rl.numero_lot, COALESCE(cf.designation, rl.designation_libre) AS libelle,
                   COALESCE(rl.dlc, rl.dluo) AS dlc, r.date_reception
            FROM reception_lignes rl
            JOIN receptions r ON r.id = rl.reception_id
            LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
            WHERE rl.produit_id IS NULL AND r.statut='cloturee' AND rl.conforme=1
              AND r.livraison_refusee=0
              AND (COALESCE(rl.dlc, rl.dluo) IS NULL OR COALESCE(rl.dlc, rl.dluo) >= DATE('now'))
            ORDER BY r.date_reception DESC LIMIT 15
        """).fetchall()
        for r in rows:
            print(f"    lot={r['numero_lot'] or '—':<20} {(r['libelle'] or '?')[:40]:<40} "
                  f"DLC={r['dlc'] or '—'}  reçu={r['date_reception']}")

    # ── 3. Traçabilité perdue sur les cuissons existantes ────────────────
    section("3. CUISSONS — traçabilité amont perdue ?")
    n_cuissons = cur.execute("SELECT COUNT(*) FROM cuissons").fetchone()[0]
    orphelines = cur.execute(
        "SELECT COUNT(*) FROM cuissons WHERE reception_ligne_id IS NULL AND fabrication_id IS NULL"
    ).fetchone()[0]
    print(f"  cuissons enregistrées        : {n_cuissons}")
    print(f"  SANS lot amont (ni réception, ni fabrication) : {orphelines}"
          + (f"  ({100*orphelines//n_cuissons} %)" if n_cuissons else ""))
    if orphelines:
        print("    ← symptôme du bug : le wizard avance malgré l'erreur 500 et")
        print("      enregistre la cuisson sans lien vers le lot (cuisson.js:483).")
        print("      Conséquence HACCP : pas de traçabilité amont, DLC non plafonnée.")
        rows = cur.execute("""
            SELECT c.date_cuisson, p.nom AS produit, c.dlc_finale
            FROM cuissons c LEFT JOIN produits p ON p.id = c.produit_id
            WHERE c.reception_ligne_id IS NULL AND c.fabrication_id IS NULL
            ORDER BY c.date_cuisson DESC LIMIT 15
        """).fetchall()
        print()
        for r in rows:
            print(f"    {r['date_cuisson']}  {(r['produit'] or '?')[:40]:<40} DLC={r['dlc_finale'] or '—'}")

    # ── 4. Impact sur le rattrapage prévu ────────────────────────────────
    section("4. IMPACT sur le script de rattrapage (plats traiteur)")
    for terme in ("lasagne", "gratin", "parmentier"):
        p_rows = cur.execute(
            "SELECT id, nom FROM produits WHERE LOWER(nom) LIKE ?", (f"%{terme}%",)
        ).fetchall()
        try:
            cf_rows = cur.execute(
                "SELECT id, designation FROM catalogue_fournisseur WHERE LOWER(designation) LIKE ?",
                (f"%{terme}%",),
            ).fetchall()
        except sqlite3.OperationalError:
            cf_rows = []
        print(f"  « {terme} » : {len(p_rows)} dans produits, {len(cf_rows)} dans catalogue_fournisseur")
        for r in p_rows:
            print(f"      produits            id={r['id']}  {r['nom']}")
        for r in cf_rows:
            print(f"      catalogue_fournisseur id={r['id']}  {r['designation']}")

    print()
    print("  → Si ces plats n'existent QUE dans catalogue_fournisseur (pas dans produits),")
    print("    le script de rattrapage ne trouvera AUCUN candidat : il faut d'abord")
    print("    corriger la rupture avant de lancer le rattrapage.")

    con.close()
    print()
    print("Fin de l'audit (lecture seule — rien n'a été modifié).")


if __name__ == "__main__":
    main()

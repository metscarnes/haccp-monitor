#!/usr/bin/env python3
"""
audit_factures.py — Audit de fiabilité des factures existantes (étape 0 refonte).

But : mesurer, AVANT le refactoring du module Facture, l'ampleur réelle des
4 défauts diagnostiqués sur les données de prod :

  D1  Unités   — lignes dont l'article catalogue est au colis/pièce : le montant
                 stocké vaut poids × prix (présomption €/kg) et est donc suspect.
  D2  Arrondis — montants/prix à plus de 2 décimales + micro-écarts (« écarts
                 fantômes » au centime) qui polluent les litiges.
  D3  Bouclage — factures dont le total entête ne colle pas à la somme des lignes.
  A3  Doublons — même (fournisseur, numéro de facture) enregistré plusieurs fois.

⚠️ Les vraies données sont sur le Raspberry Pi. Lance ce script LÀ où se trouve
la base de prod (ou sur une copie), en passant son chemin :

    python scripts/audit_factures.py /chemin/vers/haccp.db

Sans argument, il tente data/haccp.db du projet (souvent vide en local).

Ne modifie RIEN : lecture seule.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

# Console Windows (cp1252) : force UTF-8 pour ne pas planter sur les accents/€.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Tolérance « arrondi commercial » : en-dessous, un écart est du bruit de calcul.
TOLERANCE_LIGNE = 0.02
TOLERANCE_TOTAL = 0.05


def a_plus_de_2_decimales(x, epsilon=1e-6):
    """True si x ne tombe pas juste au centime (ex. 39.56271)."""
    if x is None:
        return False
    return abs(round(x, 2) - x) > epsilon


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("db", nargs="?",
                    default=str(Path(__file__).resolve().parent.parent / "haccp.db"),
                    help="Chemin de la base SQLite (défaut : haccp.db à la racine du projet, "
                         "= la base de prod sur le Pi)")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[X] Base introuvable : {db_path}", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row

    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "factures" not in tables or "facture_lignes" not in tables:
        print("[X] Cette base n'a pas les tables factures/facture_lignes.", file=sys.stderr)
        sys.exit(2)

    print(f"Base : {db_path}")
    print("=" * 100)

    # ── Vue d'ensemble ──────────────────────────────────────────────────────
    stats = con.execute(
        """SELECT COUNT(*) AS nb, MIN(date_facture) AS d_min, MAX(date_facture) AS d_max,
                  ROUND(SUM(montant_total_ht_facture), 2) AS total_ht
           FROM factures"""
    ).fetchone()
    print(f"\n📊 VUE D'ENSEMBLE — {stats['nb']} facture(s) du {stats['d_min']} au {stats['d_max']}, "
          f"total facturé HT : {stats['total_ht']} €")
    for r in con.execute("SELECT statut, COUNT(*) AS nb FROM factures GROUP BY statut ORDER BY nb DESC"):
        print(f"   - {r['statut']:<12} : {r['nb']}")
    nb_lignes = con.execute("SELECT COUNT(*) AS n FROM facture_lignes").fetchone()["n"]
    print(f"   - lignes        : {nb_lignes}")

    # ── D1 : lignes au colis / à la pièce (montant présumé €/kg → suspect) ──
    lignes_d1 = con.execute(
        """SELECT fl.id, fl.facture_id, fl.designation, fl.unite,
                  fl.poids_facture_kg, fl.prix_facture_ht, fl.montant_facture_ht,
                  fl.quantite_commandee, cf.format_prix, cf.poids_colis_kg
           FROM facture_lignes fl
           JOIN catalogue_fournisseur cf ON cf.id = fl.catalogue_fournisseur_id
           WHERE cf.format_prix IN ('colis', 'piece')
           ORDER BY fl.facture_id, fl.id"""
    ).fetchall()
    impact_d1 = 0.0
    print(f"\n🔴 D1 UNITÉS — {len(lignes_d1)} ligne(s) sur article au colis/pièce "
          f"(montant calculé poids × prix, donc suspect) :")
    for l in lignes_d1:
        poids, prix, montant = l["poids_facture_kg"], l["prix_facture_ht"], l["montant_facture_ht"]
        qte = l["quantite_commandee"]
        montant_natif = round(qte * prix, 2) if (qte and prix) else None
        delta = (montant - montant_natif) if (montant is not None and montant_natif is not None) else None
        if delta:
            impact_d1 += delta
        print(f"   fac {l['facture_id']:>4} · {l['designation'][:38]:<38} "
              f"[{l['format_prix']}] poids={poids} prix={prix} "
              f"montant_stocké={montant} vs qté×prix={montant_natif} "
              f"{'⚠ Δ=' + format(delta, '.2f') + ' €' if delta else ''}")
    if lignes_d1:
        print(f"   → Impact cumulé si l'unité vraie est le {lignes_d1[0]['format_prix']} : "
              f"{impact_d1:+.2f} € (à vérifier facture papier en main)")
    else:
        print("   (aucune — le défaut existe dans le code mais n'a pas encore touché de données)")

    # ── D2 : arrondis ────────────────────────────────────────────────────────
    lignes = con.execute(
        """SELECT id, facture_id, designation, poids_facture_kg, prix_facture_ht,
                  montant_facture_ht, ecart_montant_ht FROM facture_lignes"""
    ).fetchall()
    non_rondes = [l for l in lignes if a_plus_de_2_decimales(l["montant_facture_ht"])]
    micro_ecarts = [l for l in lignes
                    if l["ecart_montant_ht"] and 0 < abs(l["ecart_montant_ht"]) <= TOLERANCE_LIGNE]
    print(f"\n🟠 D2 ARRONDIS — {len(non_rondes)} montant(s) de ligne à plus de 2 décimales, "
          f"{len(micro_ecarts)} micro-écart(s) ≤ {TOLERANCE_LIGNE} € (faux litiges potentiels) :")
    for l in non_rondes[:15]:
        print(f"   fac {l['facture_id']:>4} · {l['designation'][:38]:<38} "
              f"montant={l['montant_facture_ht']!r}")
    if len(non_rondes) > 15:
        print(f"   … et {len(non_rondes) - 15} autres")

    # ── D3 : bouclage entête vs somme des lignes ────────────────────────────
    factures_drift = con.execute(
        """SELECT f.id, f.numero_facture, f.montant_total_ht_facture AS total_entete,
                  ROUND(COALESCE(SUM(fl.montant_facture_ht), 0), 2) AS total_lignes
           FROM factures f
           LEFT JOIN facture_lignes fl ON fl.facture_id = f.id
           GROUP BY f.id
           HAVING ABS(COALESCE(f.montant_total_ht_facture, 0) - total_lignes) > ?""",
        (TOLERANCE_TOTAL,),
    ).fetchall()
    print(f"\n🟠 D3 BOUCLAGE — {len(factures_drift)} facture(s) dont le total entête "
          f"s'écarte de la somme des lignes (> {TOLERANCE_TOTAL} €) :")
    for f in factures_drift:
        print(f"   fac {f['id']:>4} n°{f['numero_facture'] or '(sans n°)'} : "
              f"entête={f['total_entete']} vs lignes={f['total_lignes']}")

    # ── A3 : doublons (fournisseur, numéro) ─────────────────────────────────
    doublons = con.execute(
        """SELECT fournisseur_id, numero_facture, COUNT(*) AS nb,
                  GROUP_CONCAT(id) AS ids
           FROM factures
           WHERE numero_facture IS NOT NULL AND TRIM(numero_facture) <> ''
           GROUP BY fournisseur_id, numero_facture
           HAVING COUNT(*) > 1"""
    ).fetchall()
    print(f"\n🔴 A3 DOUBLONS — {len(doublons)} numéro(s) de facture en double "
          f"(même fournisseur) :")
    for d in doublons:
        print(f"   fournisseur {d['fournisseur_id']} n°{d['numero_facture']} "
              f"× {d['nb']} (ids factures : {d['ids']})")
    sans_numero = con.execute(
        """SELECT COUNT(*) AS n FROM factures
           WHERE numero_facture IS NULL OR TRIM(numero_facture) = ''"""
    ).fetchone()["n"]
    print(f"   (+ {sans_numero} facture(s) SANS numéro — l'index unique de l'étape 1 "
          f"ne pourra pas les protéger tant que le numéro n'est pas saisi)")

    # ── Lignes sans prix ────────────────────────────────────────────────────
    sans_prix = con.execute(
        """SELECT COUNT(*) AS n FROM facture_lignes
           WHERE prix_facture_ht IS NULL OR prix_facture_ht = 0"""
    ).fetchone()["n"]
    print(f"\nℹ️  {sans_prix} ligne(s) sans prix facturé (NULL ou 0) — non valorisées.")

    print("\n" + "=" * 100)
    print("Audit terminé (lecture seule, rien n'a été modifié).")


if __name__ == "__main__":
    main()

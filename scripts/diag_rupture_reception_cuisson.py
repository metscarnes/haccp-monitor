#!/usr/bin/env python3
"""
diag_rupture_reception_cuisson.py — Audit Réception → Cuisson → Refroidissement

Contexte : la migration v6.0 a basculé la Production vers les catalogues
Achats/Vente (`recettes.produit_fini_id` → `recettes.catalogue_vente_id`,
`reception_lignes.produit_id` devenu nullable au profit de
`catalogue_fournisseur_id`), mais avait laissé Cuisson et Refroidissement sur
l'ancien modèle `produits` — rendant 100 % du stock réel non cuisinable.

Ce script CONSTATE l'état réel (schéma + données + code source) au lieu de le
supposer : il sert aussi bien à diagnostiquer la rupture qu'à vérifier, après
déploiement, que les correctifs sont bien en place. Il ne modifie RIEN.

    python3 scripts/diag_rupture_reception_cuisson.py [chemin/vers/haccp.db]

Sans argument : haccp.db à la racine du dépôt.
"""

import re
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

    # Migration v7.4 : cuissons/refroidissements rejoignent les catalogues.
    # On VÉRIFIE l'état réel plutôt que de l'annoncer — l'audit doit refléter la base,
    # pas ce qu'on croit avoir déployé.
    v74_ok = True
    for t in ("cuissons", "refroidissements"):
        infos = list(cur.execute(f"PRAGMA table_info({t})"))
        noms = {r[1] for r in infos}
        pid = next((r for r in infos if r[1] == "produit_id"), None)
        nullable = pid is not None and pid[3] == 0
        a_achat  = "catalogue_fournisseur_id" in noms
        a_vente  = "catalogue_vente_id" in noms
        ok = nullable and a_achat and a_vente
        v74_ok = v74_ok and ok
        print(f"  {t:<17}: produit_id {'nullable ✓' if nullable else 'NOT NULL ✗'} · "
              f"catalogue_fournisseur_id {'✓' if a_achat else '✗'} · "
              f"catalogue_vente_id {'✓' if a_vente else '✗'}")

    print()
    if v74_ok:
        print("  ✓ Migration v7.4 appliquée : le schéma accepte les lots du catalogue achats.")
    else:
        print("  ✗ Migration v7.4 NON appliquée — redémarrer le backend (elle tourne au")
        print("    démarrage). Vérifier les logs : journalctl -u haccp-backend | grep 'v7.4'")

    # Vérification du code source : le bug rec.produit_fini_id est-il corrigé ?
    src = Path(__file__).parent.parent / "src" / "api" / "routes_cuisson.py"
    if src.exists():
        txt = src.read_text(encoding="utf-8", errors="replace")
        if "rec.produit_fini_id" in txt:
            print()
            print("  ✗ routes_cuisson.py interroge encore `rec.produit_fini_id` (colonne")
            print("    disparue en v6) → GET /api/cuisson/produits/{id}/receptions = HTTP 500.")
        elif "rec.catalogue_vente_id" in txt:
            print("  ✓ routes_cuisson.py utilise rec.catalogue_vente_id (bug HTTP 500 corrigé).")

    js = Path(__file__).parent.parent / "static" / "js" / "cuisson.js"
    if js.exists():
        txt_js = js.read_text(encoding="utf-8", errors="replace")
        if "Lots indisponibles" in txt_js:
            print("  ✓ cuisson.js alerte l'opérateur si les lots ne se chargent pas.")
        else:
            print("  ✗ cuisson.js avale encore l'erreur de chargement des lots (silencieux).")

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
    print(f"  dont sans produit interne    : {stock_sans}")

    # Le schéma migré ne suffit pas : l'API valide encore `produit_id: int`.
    # Tant que ce contrat n'a pas bougé, ces lots restent refusés en HTTP 422.
    api_ok = False
    if src.exists():
        txt_api = src.read_text(encoding="utf-8", errors="replace")
        # Regex plutôt qu'égalité de chaîne : l'alignement des annotations varie.
        api_ok = bool(re.search(r"produit_id\s*:\s*Optional\[int\]", txt_api)) and \
                 "catalogue_fournisseur_id" in txt_api
    print()
    if stock_sans and not api_ok:
        print("  ⚠ ÉTAT INTERMÉDIAIRE : le schéma accepte ces lots (v7.4 ✓) mais l'API les")
        print("    refuse encore — CuissonCreate exige `produit_id: int` → HTTP 422.")
        print("    Ces lots ne sont donc PAS encore cuisinables. Étape suivante prévue.")
    elif stock_sans and api_ok:
        print("  ✓ Schéma ET API acceptent les lots du catalogue achats.")
    else:
        print("  ✓ Aucun lot bloqué.")

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

    # ── 5. Liaison vente ↔ achat (comparatif) ────────────────────────────
    # Le déclencheur du cycle doit partir du catalogue de VENTE (ce qu'on produit)
    # et retrouver les articles d'ACHAT qui l'alimentent, via :
    #   catalogue_vente → comparatif_groupe_vente → comparatif_groupe
    #                   → comparatif_groupe_ligne → catalogue_fournisseur
    section("5. LIAISON VENTE ↔ ACHAT — le déclencheur est-il branchable ?")
    try:
        n_vente   = cur.execute("SELECT COUNT(*) FROM catalogue_vente WHERE actif=1").fetchone()[0]
        n_groupes = cur.execute("SELECT COUNT(*) FROM comparatif_groupe").fetchone()[0]
        n_liens_v = cur.execute("SELECT COUNT(*) FROM comparatif_groupe_vente").fetchone()[0]
        n_liens_a = cur.execute("SELECT COUNT(*) FROM comparatif_groupe_ligne").fetchone()[0]
        print(f"  produits de vente actifs        : {n_vente}")
        print(f"  groupes de comparaison          : {n_groupes}")
        print(f"  liens groupe → produit de vente : {n_liens_v}")
        print(f"  liens groupe → article d'achat  : {n_liens_a}")

        print()
        print("  Produits de vente correspondant aux plats visés,")
        print("  avec le nombre d'articles d'achat réellement reliés :")
        rows = cur.execute(
            """
            SELECT v.id, v.nom, v.famille,
                   gv.groupe_id,
                   (SELECT COUNT(*) FROM comparatif_groupe_ligne gl
                     WHERE gl.groupe_id = gv.groupe_id) AS nb_achats
            FROM catalogue_vente v
            LEFT JOIN comparatif_groupe_vente gv ON gv.catalogue_vente_id = v.id
            WHERE LOWER(v.nom) LIKE '%lasagne%'
               OR LOWER(v.nom) LIKE '%gratin%'
               OR LOWER(v.nom) LIKE '%parmentier%'
               OR LOWER(v.nom) LIKE '%rosbeef%' OR LOWER(v.nom) LIKE '%rosbif%'
            ORDER BY v.nom
            """
        ).fetchall()
        if not rows:
            print("    (aucun) ← ces plats ne sont PAS dans le catalogue de vente :")
            print("      il faudra les y créer avant de pouvoir déclencher le cycle.")
        for r in rows:
            if r["groupe_id"] is None:
                etat = "NON RELIÉ à un groupe → déclencheur inopérant"
            elif not r["nb_achats"]:
                etat = f"groupe #{r['groupe_id']} mais 0 article d'achat → inopérant"
            else:
                etat = f"groupe #{r['groupe_id']} · {r['nb_achats']} article(s) d'achat ✓"
            print(f"    id={r['id']:<5} {(r['nom'] or '')[:44]:<44} {etat}")
    except sqlite3.OperationalError as e:
        print(f"  ERREUR (tables comparatif absentes ?) : {e}")

    # ── 6. Verdict ───────────────────────────────────────────────────────
    section("6. VERDICT")
    etapes = [
        ("Bug HTTP 500 (rec.produit_fini_id)",
         src.exists() and "rec.produit_fini_id" not in src.read_text(encoding="utf-8", errors="replace")),
        ("Alerte opérateur si lots non chargés",
         js.exists() and "Lots indisponibles" in js.read_text(encoding="utf-8", errors="replace")),
        ("Migration v7.4 (schéma cuissons/refroidissements)", v74_ok),
        ("API accepte les lots du catalogue achats", api_ok),
    ]
    for libelle, ok in etapes:
        print(f"  [{'✓' if ok else ' '}] {libelle}")

    restant = [l for l, ok in etapes if not ok]
    print()
    if restant:
        print("  Reste à faire :")
        for l in restant:
            print(f"    • {l}")
    else:
        print("  Tout est en place — la chaîne Réception → Cuisson → Refroidissement")
        print("  est opérationnelle sur le stock réel.")

    con.close()
    print()
    print("Fin de l'audit (lecture seule — rien n'a été modifié).")


if __name__ == "__main__":
    main()

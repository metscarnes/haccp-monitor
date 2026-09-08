#!/usr/bin/env python3
"""
audit_stock_hors_calendrier_dlc.py — Produits présents dans le STOCK mais
ABSENTS du CALENDRIER DLC.

POURQUOI L'ÉCART EXISTE
-----------------------
Les deux écrans lisent les mêmes tables mais ne filtrent pas pareil :

  • Stock unifié      (get_stock_unifie)   : garde la ligne même sans DLC, et pour
                                            les réceptions retient COALESCE(dlc, dluo).
  • Calendrier DLC    (get_dlc_calendrier) : exige une DLC NON NULLE
                                            (`WHERE rl.dlc IS NOT NULL`, idem
                                            `dlc_finale IS NOT NULL`) et une date
                                            comprise dans la période affichée.

Conséquence : tout lot daté seulement par une DLUO, ou sans aucune date, reste
visible au stock mais ne s'affiche JAMAIS au calendrier — donc jamais surveillé
par les alertes DLC ni proposé au traitement des expirés.

USAGE (sur le Raspberry Pi, où vit la vraie base) :
    python3 scripts/audit_stock_hors_calendrier_dlc.py
    python3 scripts/audit_stock_hors_calendrier_dlc.py --db /chemin/haccp.db
    python3 scripts/audit_stock_hors_calendrier_dlc.py --csv rapport.csv

Lecture seule : le script n'écrit jamais dans la base.
"""

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

BOUTIQUE_ID = 1

# Colonnes communes à toutes les sources, pour un rendu et un CSV homogènes.
CHAMPS = ["source_type", "source_id", "produit_nom", "date_trouvee",
          "type_date", "numero_lot", "quantite", "date_origine", "detail"]


def _colonnes(con, table):
    return {r[1] for r in con.execute(f"PRAGMA table_info({table})")}


def _tables(con):
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def auditer(con):
    """
    Retourne (lignes_hors_calendrier, compteurs_par_source).

    Le schéma a évolué au fil des versions (v6 catalogue achats, v7.4 catalogue
    vente sur les cuissons, colonne `statut` ajoutée sur reception_lignes…) et
    toutes les bases ne sont pas au même niveau. On inspecte donc les colonnes
    réellement présentes avant de construire chaque requête, plutôt que de les
    supposer — sinon l'audit plante sur une base en retard de migration.
    """
    manquants = []
    totaux = {}
    tables = _tables(con)

    # ── 📦 RÉCEPTIONS ────────────────────────────────────────────────────
    # En stock : DLC ou DLUO. Au calendrier : DLC uniquement.
    # → tout ce qui n'a pas de `dlc` est un angle mort.
    rl_cols = _colonnes(con, "reception_lignes")
    r_cols = _colonnes(con, "receptions")

    filtres = ["r.statut='cloturee'" if "statut" in r_cols else "1=1",
               "rl.conforme=1" if "conforme" in rl_cols else "1=1",
               "r.livraison_refusee=0" if "livraison_refusee" in r_cols else "1=1"]
    if "statut" in rl_cols:
        filtres.append("COALESCE(rl.statut,'complet') <> 'en_attente'")
    filtre_recep = " AND ".join(filtres)

    nom_recep, joins_recep = [], []
    if "produit_id" in rl_cols and "produits" in tables:
        joins_recep.append("LEFT JOIN produits p ON p.id = rl.produit_id")
        nom_recep.append("p.nom")
    if "catalogue_fournisseur_id" in rl_cols and "catalogue_fournisseur" in tables:
        joins_recep.append("LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id")
        nom_recep.append("cf.designation")
    if "designation_libre" in rl_cols:
        nom_recep.append("rl.designation_libre")
    if "fournisseur_id" in rl_cols and "fournisseurs" in tables:
        joins_recep.append("LEFT JOIN fournisseurs f ON f.id = rl.fournisseur_id")
        fourn_expr = "f.nom"
    elif "fournisseur_nom" in rl_cols:
        fourn_expr = "rl.fournisseur_nom"
    else:
        fourn_expr = "NULL"
    dluo_expr = "rl.dluo" if "dluo" in rl_cols else "NULL"
    nom_recep.append("'(sans nom)'")

    totaux["reception_ligne"] = con.execute(f"""
        SELECT COUNT(*) FROM reception_lignes rl
        JOIN receptions r ON r.id = rl.reception_id
        WHERE {filtre_recep}
          AND NOT EXISTS (SELECT 1 FROM dlc_devenir dd
                          WHERE dd.source_type='reception_ligne' AND dd.source_id=rl.id)
    """).fetchone()[0]

    for r in con.execute(f"""
        SELECT rl.id, COALESCE({', '.join(nom_recep)}) AS nom,
               {dluo_expr} AS dluo, rl.numero_lot, rl.poids_kg,
               r.date_reception, {fourn_expr} AS fournisseur
        FROM reception_lignes rl
        JOIN receptions r ON r.id = rl.reception_id
        {' '.join(joins_recep)}
        WHERE {filtre_recep}
          AND rl.dlc IS NULL
          AND NOT EXISTS (SELECT 1 FROM dlc_devenir dd
                          WHERE dd.source_type='reception_ligne' AND dd.source_id=rl.id)
        ORDER BY r.date_reception DESC
    """):
        manquants.append({
            "source_type": "reception_ligne",
            "source_id": r["id"],
            "produit_nom": r["nom"] or "(sans nom)",
            "date_trouvee": r["dluo"] or "",
            "type_date": "DLUO seule" if r["dluo"] else "AUCUNE DATE",
            "numero_lot": r["numero_lot"] or "",
            "quantite": r["poids_kg"],
            "date_origine": r["date_reception"],
            "detail": f"Fournisseur : {r['fournisseur'] or '—'}",
        })

    # ── 🔪 FABRICATIONS / 🔥 CUISSONS / ❄️ REFROIDISSEMENTS ───────────────
    # Ces trois sources n'ont qu'une seule date (`dlc_finale`). Si elle est
    # NULL, la ligne compte au stock mais n'atteint jamais le calendrier.
    transformes = [
        ("fabrication", "fabrications", "fab", "", ""),
        ("cuisson", "cuissons", "cu",
         "AND NOT EXISTS (SELECT 1 FROM refroidissements rf WHERE rf.cuisson_id = cu.id)", ""),
        ("refroidissement", "refroidissements", "rf", "AND COALESCE(rf.jeter,0)=0", ""),
    ]

    for src, table, alias, filtre_extra, _ in transformes:
        totaux[src] = con.execute(f"""
            SELECT COUNT(*) FROM {table} {alias}
            WHERE 1=1 {filtre_extra}
              AND NOT EXISTS (SELECT 1 FROM dlc_devenir dd
                              WHERE dd.source_type='{src}' AND dd.source_id={alias}.id)
        """).fetchone()[0]

        cols = _colonnes(con, table)
        # Le nom du produit se reconstruit différemment selon les colonnes
        # réellement présentes (le schéma a évolué : v6 catalogue achats, v7.4
        # catalogue vente sur cuissons ; `fabrications` n'a pas de produit_id
        # et passe par sa recette). On s'adapte au lieu de supposer.
        joins, nom_parts = [], []
        if "produit_id" in cols and "produits" in tables:
            joins.append(f"LEFT JOIN produits p ON p.id = {alias}.produit_id")
            nom_parts.append("p.nom")
        if "catalogue_vente_id" in cols and "catalogue_vente" in tables:
            joins.append(f"LEFT JOIN catalogue_vente cv ON cv.id = {alias}.catalogue_vente_id")
            nom_parts.append("cv.nom")
        if "catalogue_fournisseur_id" in cols and "catalogue_fournisseur" in tables:
            joins.append(f"LEFT JOIN catalogue_fournisseur cf ON cf.id = {alias}.catalogue_fournisseur_id")
            nom_parts.append("cf.designation")
        if table == "fabrications" and "recette_id" in cols and "recettes" in tables:
            joins.append(f"LEFT JOIN recettes rec ON rec.id = {alias}.recette_id")
            if "catalogue_vente" in tables and "catalogue_vente_id" in _colonnes(con, "recettes"):
                joins.append("LEFT JOIN catalogue_vente cv_rec ON cv_rec.id = rec.catalogue_vente_id")
                nom_parts.append("cv_rec.nom")
            nom_parts.append("rec.nom")
        nom_parts.append("'(sans nom)'")

        date_col = {"fabrications": "date", "cuissons": "date_cuisson",
                    "refroidissements": "date_refroidissement"}[table]
        lot_expr = f"{alias}.numero_lot" if "numero_lot" in cols else (
            f"{alias}.lot_interne" if "lot_interne" in cols else "NULL")
        qte_expr = f"{alias}.quantite" if "quantite" in cols else (
            f"{alias}.poids_fabrique" if "poids_fabrique" in cols else "NULL")

        sql = f"""
            SELECT {alias}.id AS id,
                   COALESCE({', '.join(nom_parts)}) AS nom,
                   {lot_expr} AS lot,
                   {qte_expr} AS qte,
                   {alias}.{date_col} AS date_origine
            FROM {table} {alias}
            {' '.join(joins)}
            WHERE {alias}.dlc_finale IS NULL {filtre_extra}
              AND NOT EXISTS (SELECT 1 FROM dlc_devenir dd
                              WHERE dd.source_type='{src}' AND dd.source_id={alias}.id)
            ORDER BY {alias}.{date_col} DESC
        """
        for r in con.execute(sql):
            manquants.append({
                "source_type": src,
                "source_id": r["id"],
                "produit_nom": r["nom"],
                "date_trouvee": "",
                "type_date": "AUCUNE DATE (dlc_finale vide)",
                "numero_lot": r["lot"] or "",
                "quantite": r["qte"],
                "date_origine": r["date_origine"],
                "detail": "",
            })

    return manquants, totaux


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="haccp.db", help="chemin de la base (defaut: haccp.db)")
    ap.add_argument("--csv", help="exporte le detail dans ce fichier CSV")
    args = ap.parse_args()

    chemin = Path(args.db)
    if not chemin.exists():
        sys.exit(f"Base introuvable : {chemin.resolve()}")

    con = sqlite3.connect(f"file:{chemin}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    manquants, totaux = auditer(con)

    print("=" * 74)
    print(" AUDIT — produits EN STOCK mais ABSENTS du CALENDRIER DLC")
    print(f" Base : {chemin.resolve()}")
    print("=" * 74)
    print()
    print(" Cause : le calendrier n'affiche que les lignes ayant une DLC renseignee.")
    print(" Le stock, lui, garde aussi celles datees par DLUO ou sans date du tout.")
    print()

    total_stock = sum(totaux.values())
    print(f" Lignes en stock (toutes sources) : {total_stock}")
    print(f" Dont INVISIBLES au calendrier    : {len(manquants)}")
    print()

    if not manquants:
        print(" Aucun ecart : tout le stock est bien suivi par le calendrier DLC.")
        return

    par_src = {}
    for m in manquants:
        par_src.setdefault(m["source_type"], []).append(m)

    emoji = {"reception_ligne": "[RECEPTION]", "fabrication": "[FABRICATION]",
             "cuisson": "[CUISSON]", "refroidissement": "[REFROIDI]"}

    for src, lst in sorted(par_src.items(), key=lambda kv: -len(kv[1])):
        print("-" * 74)
        print(f" {emoji.get(src, src)}  {len(lst)} ligne(s) sur {totaux.get(src, 0)} en stock")
        print("-" * 74)
        for m in lst:
            qte = f"{m['quantite']}" if m["quantite"] is not None else "?"
            print(f"  #{m['source_id']:<6} {str(m['produit_nom'])[:38]:<38} "
                  f"{m['type_date']:<28} lot={m['numero_lot'] or '-':<14} "
                  f"qte={qte:<8} le {m['date_origine'] or '?'}")
            if m["detail"]:
                print(f"         {m['detail']}")
        print()

    print("=" * 74)
    print(" QUE FAIRE")
    print("=" * 74)
    print(" • 'DLUO seule'  : produit d'epicerie/conserve date par une DLUO. Normal")
    print("   qu'il n'ait pas de DLC, mais il echappe aux alertes du calendrier.")
    print(" • 'AUCUNE DATE' : lot saisi sans date — a completer en reception, sinon")
    print("   il ne sera jamais alerte a l'approche de sa peremption.")
    print()

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=CHAMPS, delimiter=";")
            w.writeheader()
            w.writerows(manquants)
        print(f" CSV ecrit : {Path(args.csv).resolve()}")


if __name__ == "__main__":
    main()

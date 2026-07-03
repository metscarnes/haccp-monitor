#!/usr/bin/env python3
"""
audit_prix_reception.py — Audit des prix d'achat saisis en réception.

But : lister toutes les lignes de réception ayant un PRIX D'ACHAT saisi
(`prix_unitaire_ht`) depuis une date donnée, et indiquer pour chacune si elle
a bien été historisée dans `historique_prix_achat` (donc si elle alimente la
vue « 📈 Variations de prix d'achat »). Sert à repérer les hausses « sautées »
(ex. bateau, poulet tikka massala) : prix saisi mais absent des variations.

⚠️ Les vraies données sont sur le Raspberry Pi. Lance ce script LÀ où se trouve
la base de prod (ou sur une copie), en passant son chemin :

    python scripts/audit_prix_reception.py /chemin/vers/haccp.db --depuis 2026-05-11

Sans argument de base, il tente le haccp.db à la racine du projet (souvent vide
en local — d'où l'avertissement si 0 ligne).

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


def colonnes(con, table):
    return {r[1] for r in con.execute(f"PRAGMA table_info({table})")}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("db", nargs="?", default=str(Path(__file__).resolve().parent.parent / "haccp.db"),
                    help="Chemin de la base SQLite (défaut : haccp.db du projet)")
    ap.add_argument("--depuis", default="2026-05-11",
                    help="Date de début (YYYY-MM-DD), défaut 2026-05-11")
    ap.add_argument("--seuil", type=float, default=2.0,
                    help="Seuil %% pour marquer une variation 'significative' (défaut 2)")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[X] Base introuvable : {db_path}", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row

    # Garde-fous : la base doit avoir les tables/colonnes attendues.
    cols_rl = colonnes(con, "reception_lignes")
    if "prix_unitaire_ht" not in cols_rl:
        print("[X] Cette base n'a pas la colonne reception_lignes.prix_unitaire_ht "
              "(schéma trop ancien : les prix d'achat en réception n'y existent pas).",
              file=sys.stderr)
        sys.exit(2)
    a_historique = "historique_prix_achat" in {
        r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    print(f"Base       : {db_path}")
    print(f"Depuis     : {args.depuis}")
    print(f"Historique : {'présent' if a_historique else 'ABSENT (table historique_prix_achat manquante)'}")
    print("=" * 100)

    # Toutes les lignes de réception AVEC un prix d'achat saisi, depuis la date.
    lignes = con.execute(
        """
        SELECT rl.id                       AS ligne_id,
               rl.reception_id             AS reception_id,
               r.date_reception            AS date_reception,
               r.statut                    AS statut_reception,
               rl.catalogue_fournisseur_id AS cat_id,
               COALESCE(cf.designation, rl.fournisseur_nom, '(sans article catalogue)') AS designation,
               cf.code_article             AS code_article,
               rl.prix_unitaire_ht         AS prix,
               rl.poids_kg                 AS poids_kg
        FROM reception_lignes rl
        JOIN receptions r ON r.id = rl.reception_id
        LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
        WHERE rl.prix_unitaire_ht IS NOT NULL
          AND r.date_reception >= ?
        ORDER BY r.date_reception ASC, rl.id ASC
        """,
        (args.depuis,),
    ).fetchall()

    if not lignes:
        print("[!] Aucune ligne de réception avec prix d'achat depuis cette date "
              "(base vide en local ? lance sur le Pi).")
        con.close()
        return

    # Pour chaque ligne : est-elle historisée ? (clé = reception_ligne_id)
    hist_par_ligne = {}
    if a_historique:
        for h in con.execute(
            "SELECT reception_ligne_id, id FROM historique_prix_achat "
            "WHERE reception_ligne_id IS NOT NULL"
        ):
            hist_par_ligne[h["reception_ligne_id"]] = h["id"]

    total = len(lignes)
    historisees = 0
    sans_article = 0
    non_cloturees = 0
    manquantes = []

    print(f"{'Date':<12}{'Article':<38}{'Prix':>10}  {'Statut récep.':<14}{'Dans Variations ?'}")
    print("-" * 100)
    for l in lignes:
        dans_hist = l["ligne_id"] in hist_par_ligne
        if dans_hist:
            historisees += 1
            etat = "OUI"
        else:
            # Diagnostic de la raison la plus probable
            if l["cat_id"] is None:
                raison = "NON - pas d'article catalogue relie"
                sans_article += 1
            elif l["statut_reception"] not in ("cloturee", "cloture", "termine", "complet"):
                raison = f"NON - reception '{l['statut_reception']}' (pas clôturée ?)"
                non_cloturees += 1
            else:
                raison = "NON - historisation sautee (a verifier)"
            etat = raison
            manquantes.append(l)

        art = (l["designation"] or "")[:36]
        prix = f"{l['prix']:.2f} €" if l["prix"] is not None else "—"
        print(f"{str(l['date_reception']):<12}{art:<38}{prix:>10}  "
              f"{str(l['statut_reception'] or ''):<14}{etat}")

    print("=" * 100)
    print(f"TOTAL lignes avec prix depuis {args.depuis} : {total}")
    print(f"  OK historisees (dans Variations)         : {historisees}")
    print(f"  KO absentes des Variations               : {total - historisees}")
    if sans_article:
        print(f"       dont sans article catalogue relié   : {sans_article}")
    if non_cloturees:
        print(f"       dont réception non clôturée         : {non_cloturees}")

    if manquantes:
        print("\nLIGNES ABSENTES DES VARIATIONS (hausses potentiellement sautées) :")
        for l in manquantes:
            print(f"   - {l['date_reception']}  {l['designation']}  "
                  f"{l['prix']:.2f} €  (réception #{l['reception_id']}, ligne #{l['ligne_id']})")

    con.close()


if __name__ == "__main__":
    main()

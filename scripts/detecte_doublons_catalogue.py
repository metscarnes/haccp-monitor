#!/usr/bin/env python3
"""
detecte_doublons_catalogue.py — Détection (LECTURE SEULE) des fiches catalogue
susceptibles d'être des doublons du MÊME produit.

Contexte : la vue « Variations de prix » regroupe l'historique par
catalogue_fournisseur_id. Si un même produit physique existe sous plusieurs
fiches (ex. « POULET TIKKA MASSALA 3KG » et « Poulet Tikka Massala »), chaque
fiche a trop peu de relevés → la vraie hausse (+11 %) passe inaperçue.

Ce script repère ces doublons SANS RIEN MODIFIER. Il normalise la désignation
(minuscules, sans accents, sans ponctuation, sans les mentions de
conditionnement fréquentes : poids, BQT, PV, S/V, PCE, KG, COL…) puis regroupe.
Un groupe de 2+ fiches = doublon probable à examiner.

Usage :
    python scripts/detecte_doublons_catalogue.py haccp.db
    python scripts/detecte_doublons_catalogue.py haccp.db --meme-fournisseur

Options :
    --meme-fournisseur : ne signale que les doublons CHEZ LE MÊME fournisseur
                         (candidats à la fusion la plus sûre). Par défaut, on
                         montre aussi les doublons inter-fournisseurs (utiles à
                         relier dans un même groupe comparatif).
"""
import argparse
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Mentions de conditionnement / présentation à retirer pour comparer le "cœur"
# du produit. Retirées en tant que mots entiers (bornes \b).
_MOTS_BRUIT = {
    "kg", "g", "gr", "cl", "l", "ml", "pv", "sv", "s", "v", "pce", "pc", "pch",
    "col", "bcl", "bqt", "sal", "seau", "sacht", "scht", "ecu", "tp", "tg", "plat",
    "atm", "ab", "pad", "nsv", "nsy", "vpf", "vf", "igp", "aop", "aoc", "rg",
    "label", "rouge", "x", "env", "sous", "vide", "s/v", "s/atm", "a/os", "a/ab",
    "pv", "cru", "frais", "fraiche", "surgele", "surgelee",
}
_RE_POIDS = re.compile(r"\b\d+[.,]?\d*\s*(kg|g|gr|cl|ml|l|p|pc|pce)\b")
_RE_MULTI = re.compile(r"\b\d+\s*[x/]\s*\d*")     # 12P/2,1 ; 2x170 ; 15P/9,75
_RE_NONALNUM = re.compile(r"[^a-z0-9 ]+")
_RE_ESPACES = re.compile(r"\s+")


def normaliser(designation: str) -> str:
    """Réduit une désignation à son 'cœur' comparable."""
    s = designation or ""
    # Sans accents
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = _RE_MULTI.sub(" ", s)
    s = _RE_POIDS.sub(" ", s)
    s = _RE_NONALNUM.sub(" ", s)
    mots = [m for m in _RE_ESPACES.sub(" ", s).split()
            if m and m not in _MOTS_BRUIT and not m.isdigit()]
    return " ".join(mots).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("db", nargs="?",
                    default=str(Path(__file__).resolve().parent.parent / "haccp.db"))
    ap.add_argument("--meme-fournisseur", action="store_true",
                    help="Ne montrer que les doublons chez le même fournisseur")
    ap.add_argument("--min-mots", type=int, default=2,
                    help="Ignore les clés normalisées trop courtes (défaut 2 mots)")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[X] Base introuvable : {db_path}", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row

    # Toutes les fiches actives + nb de relevés d'historique (pour juger l'impact).
    rows = con.execute(
        """
        SELECT cf.id, cf.designation, cf.code_article, cf.fournisseur_id,
               COALESCE(f.nom, '?') AS fournisseur_nom,
               cf.prix_achat_ht, cf.format_prix,
               (SELECT COUNT(*) FROM historique_prix_achat h
                WHERE h.catalogue_fournisseur_id = cf.id) AS nb_hist
        FROM catalogue_fournisseur cf
        LEFT JOIN fournisseurs f ON f.id = cf.fournisseur_id
        WHERE cf.actif = 1
        ORDER BY cf.designation
        """
    ).fetchall()

    # Regroupe par clé normalisée (+ fournisseur si demandé).
    groupes: dict = {}
    for r in rows:
        cle = normaliser(r["designation"])
        if len(cle.split()) < args.min_mots:
            continue  # trop court pour être fiable
        gkey = (cle, r["fournisseur_id"]) if args.meme_fournisseur else cle
        groupes.setdefault(gkey, []).append(r)

    doublons = {k: v for k, v in groupes.items() if len(v) >= 2}

    print(f"Base          : {db_path}")
    print(f"Fiches actives: {len(rows)}")
    print(f"Portée        : {'même fournisseur uniquement' if args.meme_fournisseur else 'tous fournisseurs'}")
    print(f"Groupes doublon: {len(doublons)}")
    print("=" * 92)

    if not doublons:
        print("Aucun doublon probable détecté avec ces critères.")
        con.close()
        return

    # Tri : d'abord ceux où au moins 2 fiches ont de l'historique (vrai impact
    # sur la vue Variations), puis par nombre de fiches.
    def impact(v):
        avec_hist = sum(1 for r in v if r["nb_hist"] > 0)
        return (avec_hist >= 2, avec_hist, len(v))

    for gkey, fiches in sorted(doublons.items(), key=lambda kv: impact(kv[1]), reverse=True):
        cle = gkey[0] if isinstance(gkey, tuple) else gkey
        avec_hist = sum(1 for r in fiches if r["nb_hist"] > 0)
        flag = "  <-- masque une variation" if avec_hist >= 2 else ""
        print(f"\n« {cle} »  ({len(fiches)} fiches, {avec_hist} avec historique){flag}")
        for r in fiches:
            print(f"   #{r['id']:<5} [{r['fournisseur_nom'][:18]:<18}] "
                  f"code={str(r['code_article'])[:14]:<14} "
                  f"{r['prix_achat_ht']:>7.2f}€  "
                  f"{r['nb_hist']} relevé(s)   {r['designation']}")

    # Récap actionnable
    critiques = [v for v in doublons.values()
                 if sum(1 for r in v if r["nb_hist"] > 0) >= 2]
    print("\n" + "=" * 92)
    print(f"TOTAL groupes doublon           : {len(doublons)}")
    print(f"  dont MASQUENT une variation   : {len(critiques)}  "
          f"(2+ fiches avec historique => hausse invisible dans Variations)")
    print("\nRien n'a été modifié (lecture seule). Examine surtout les groupes marqués <--.")
    con.close()


if __name__ == "__main__":
    main()

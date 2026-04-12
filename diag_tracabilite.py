#!/usr/bin/env python3
"""
diag_tracabilite.py — Audit FIFO / Matching par Lexique
========================================================
Simule l'algorithme de substitution JS pour vérifier que chaque ingrédient
de recette (ou chaque produit du catalogue) trouve une correspondance en stock.

READ-ONLY : aucune modification de la base de données.
Bibliotheques : sqlite3, re, sys (stdlib uniquement — aucun pip install).

Usage :
  python diag_tracabilite.py           # audit complet sur recette_ingredients
                                       # (fallback : catalogue produits si absent)
  python diag_tracabilite.py --demo    # test rapide sur un jeu de données simulé
"""

import sqlite3
import re
import sys
import io

# Force UTF-8 sur la sortie (Windows cmd/PowerShell en cp1252 par defaut)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Codes ANSI ───────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

# ── Chemin de la base ────────────────────────────────────────────────────────
DB_PATH = "haccp.db"

# ── Lexique espèces → synonymes ──────────────────────────────────────────────
# Couvre tous les codes préfixes observés dans produits.nom
LEXIQUE = {
    # Bœuf
    "VB":       ["boeuf", "bœuf", "vache", "bovine", "bf", "viande bovine"],
    # Veau
    "VX":       ["veau", "vx"],
    # Porc
    "PC":       ["porc", "cochon", "porcin"],
    # Agneau (deux formes de préfixe dans le catalogue)
    "AG":       ["agneau", "agn"],
    "AGN":      ["agneau", "agn"],
    # Gibier (préfixe long dans le catalogue)
    "GI":       ["gibier", "cerf", "sanglier"],
    "GIBIER":   ["gibier", "cerf", "sanglier", "chevreuil", "daim", "chevreau"],
    # Volaille
    "VOLAILLE": ["volaille", "poulet", "canard", "dinde", "pintade",
                 "lapin", "oie", "pigeon", "caille", "poularde", "coq", "coquelet"],
    # Cheval
    "CHEVAL":   ["cheval", "equin"],
    # Exotique
    "EXOTIQUE": ["exotique", "autruche", "kangourou", "bison",
                 "zebre", "lama", "crocodile"],
}

# ── Mots parasites (ignorés pour l'extraction du muscle) ────────────────────
MOTS_PARASITES = frozenset({
    "sans", "avec", "os", "pad", "vrac", "de", "la", "le", "du", "des",
    "ac", "ent", "entier", "entiere", "tranche", "coupe", "par", "une",
    "les", "au", "aux", "et", "en", "sur", "un", "pf",
})

# ── Ingrédients de démonstration (utilisés avec --demo) ─────────────────────
DEMO_INGREDIENTS = [
    "VB-COLLIER SANS OS",
    "VB-PALERON",
    "VB-MACREUSE A BIFTECK",
    "VX-QUASI",
    "VX-NOIX",
    "PC-ECHINE",
    "AGN-GIGOT SANS OS",
    "GIBIER-CERF CIVET",
    "VOLAILLE- AIGUILLETTE DE CANARD",
    "CHEVAL- STEAK DE CHEVAL",
    "VB-FICTIF INEXISTANT 999",   # intentionnellement sans match
]

# ── Table de remplacement accents → ASCII ────────────────────────────────────
_ACCENTS = str.maketrans(
    "éèêëàâäôöœûüùîïçæÉÈÊËÀÂÄÔÖŒÛÜÙÎÏÇÆ",
    "eeeaaaoooeuuuiicaEEEAAAOOOEUUUIICA"
)


# ─────────────────────────────────────────────────────────────────────────────
# Fonctions utilitaires
# ─────────────────────────────────────────────────────────────────────────────

def normaliser(texte: str) -> str:
    """Minuscule + suppression des accents courants (pas d'import unicodedata)."""
    return texte.lower().translate(_ACCENTS)


# Regex pour détecter le code préfixe (avec ou sans tiret, avec espace optionnel)
# Ex: "VB-COLLIER", "AGN- GIGOT", "VB COEUR CUBE", "VOLAILLE- AIGUILLETTE"
_RE_PREFIXE = re.compile(r'^([A-Z]{2,8})\s*-\s*(.+)$|^([A-Z]{2,3})\s+(.+)$')


def extraire_code_et_muscle(nom: str):
    """
    Retourne (code, muscle) depuis un nom de produit.

    Exemples :
      "VB-COLLIER SANS OS"             → ("VB",       "collier")
      "AGN-GIGOT SANS OS"              → ("AGN",      "gigot")
      "GIBIER-CERF CIVET"              → ("GIBIER",   "cerf")
      "VOLAILLE- AIGUILLETTE DE CANARD"→ ("VOLAILLE", "aiguillette")
      "VB COEUR CUBE VRAC"             → ("VB",       "coeur")
      "AG FOIE TRANCHE"                → ("AG",       "foie")
    """
    nom = nom.strip()
    m = _RE_PREFIXE.match(nom)
    if m:
        # Groupe 1+2 = tiret, groupe 3+4 = espace
        code  = (m.group(1) or m.group(3)).strip().upper()
        reste = (m.group(2) or m.group(4)).strip()
    else:
        code  = ""
        reste = nom

    # Retire les non-lettres (chiffres, slashes…) et passe en minuscules
    mots = re.sub(r"[^a-zA-Z\xc0-\xff\s]", " ", reste.lower()).split()

    # Filtre les mots parasites et les trop courts (≤ 2 caractères)
    utiles = [
        w for w in mots
        if len(w) > 2 and normaliser(w) not in MOTS_PARASITES
    ]

    muscle = normaliser(utiles[0]) if utiles else normaliser(reste)
    return code, muscle


def synonymes_code(code: str) -> list:
    """Renvoie code + tous ses synonymes, normalisés."""
    syns = LEXIQUE.get(code, [])
    return [normaliser(code)] + [normaliser(s) for s in syns]


# ─────────────────────────────────────────────────────────────────────────────
# Algorithme de matching (simulateur JS)
# ─────────────────────────────────────────────────────────────────────────────

def match_produit(ingredient: str, stock_norm: list):
    """
    Cherche dans stock_norm (liste de tuples (nom_original, nom_normalise))
    un article qui contient à la fois :
      - le MUSCLE extrait de l'ingrédient
      - le CODE espèce ou un de ses SYNONYMES

    Retourne le nom original du premier match, ou None.
    """
    code, muscle = extraire_code_et_muscle(ingredient)
    syns = synonymes_code(code)

    for nom_orig, nom_nrm in stock_norm:
        has_muscle = muscle in nom_nrm
        has_espece = any(s in nom_nrm for s in syns)
        if has_muscle and has_espece:
            return nom_orig
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Chargement des données (READ-ONLY)
# ─────────────────────────────────────────────────────────────────────────────

def charger_donnees(db_path: str, demo: bool, catalogue: bool = False):
    """
    Ouvre la base en lecture seule et retourne :
      (besoins, stock, source_a, source_b)

    Liste A (besoins) :
      - En mode --demo : DEMO_INGREDIENTS
      - Si recette_ingredients existe : SELECT DISTINCT <col_nom>
      - Sinon (Phase 2 non encore déployée) : SELECT DISTINCT nom FROM produits

    Liste B (stock) :
      - reception_lignes JOIN produits WHERE quantite_restante > 0  (idéal)
      - reception_lignes.produit_nom WHERE quantite > 0             (fallback 1)
      - produits.nom catalogue complet                              (fallback 2 = simulation)
    """
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except Exception:
        # SQLite < 3.5 ne supporte pas uri=True ; fallback mode normal
        conn = sqlite3.connect(db_path)

    cur = conn.cursor()

    def tables():
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return {r[0] for r in cur.fetchall()}

    tbls = tables()

    # ── Liste A : Besoins ─────────────────────────────────────────────────────
    if demo:
        besoins  = DEMO_INGREDIENTS
        source_a = "Jeu de demo interne (--demo)"

    elif catalogue:
        # --catalogue : scan direct du catalogue, sans toucher recette_ingredients
        cur.execute("SELECT DISTINCT nom FROM produits WHERE actif = 1 ORDER BY nom")
        besoins  = [r[0] for r in cur.fetchall() if r[0]]
        source_a = "produits.nom [--catalogue : audit force du catalogue complet]"

    elif "recette_ingredients" in tbls:
        # Mode normal : jointure produits pour récupérer le nom depuis produit_id
        cur.execute("PRAGMA table_info(recette_ingredients)")
        cols = {r[1] for r in cur.fetchall()}

        if "produit_id" in cols and "produits" in tbls:
            cur.execute("""
                SELECT DISTINCT p.nom
                FROM   recette_ingredients ri
                JOIN   produits p ON ri.produit_id = p.id
                WHERE  p.nom IS NOT NULL
            """)
            besoins  = [r[0] for r in cur.fetchall() if r[0]]
            source_a = "recette_ingredients JOIN produits ON produit_id (p.nom)"
        else:
            # Fallback : colonne nom textuelle directe
            candidats = ["nom_ingredient", "nom", "ingredient", "libelle", "designation", "produit"]
            col_nom = next((c for c in candidats if c in cols), None)
            if col_nom:
                cur.execute(
                    f"SELECT DISTINCT {col_nom} FROM recette_ingredients "
                    f"WHERE {col_nom} IS NOT NULL"
                )
                besoins  = [r[0] for r in cur.fetchall() if r[0]]
                source_a = f"recette_ingredients.{col_nom} (colonne texte directe)"
            else:
                besoins  = []
                source_a = f"recette_ingredients (aucune colonne utilisable parmi {sorted(cols)})"

    else:
        # Pas de table de recettes → on audite le catalogue complet
        cur.execute("SELECT DISTINCT nom FROM produits WHERE actif = 1 ORDER BY nom")
        besoins  = [r[0] for r in cur.fetchall() if r[0]]
        source_a = "produits.nom [recette_ingredients absente — audit catalogue complet]"

    # ── Liste B : Stock disponible ────────────────────────────────────────────
    stock, source_b = [], ""

    if "reception_lignes" in tbls:
        cur.execute("PRAGMA table_info(reception_lignes)")
        rl_cols = {r[1] for r in cur.fetchall()}

        # Cas idéal : produit_id + quantite_restante
        if "produit_id" in rl_cols and "quantite_restante" in rl_cols and "produits" in tbls:
            cur.execute("""
                SELECT DISTINCT p.nom
                FROM   reception_lignes rl
                JOIN   produits p ON rl.produit_id = p.id
                WHERE  rl.quantite_restante > 0
            """)
            stock    = [r[0] for r in cur.fetchall() if r[0]]
            source_b = "reception_lignes JOIN produits (quantite_restante > 0)"

        # Fallback 1 : produit_nom + quantite
        if not stock and "produit_nom" in rl_cols:
            col_qty = "quantite_restante" if "quantite_restante" in rl_cols else "quantite"
            cur.execute(
                f"SELECT DISTINCT produit_nom FROM reception_lignes WHERE {col_qty} > 0"
            )
            stock = [r[0] for r in cur.fetchall() if r[0]]
            if stock:
                source_b = f"reception_lignes.produit_nom ({col_qty} > 0)"

    # Fallback final : catalogue produits comme stock simulé
    if not stock and "produits" in tbls:
        cur.execute("SELECT DISTINCT nom FROM produits WHERE actif = 1 ORDER BY nom")
        stock    = [r[0] for r in cur.fetchall() if r[0]]
        source_b = "produits.nom [MODE SIMULATION — aucun stock reel en reception_lignes]"

    conn.close()
    return besoins, stock, source_a, source_b


# ─────────────────────────────────────────────────────────────────────────────
# Rapport terminal
# ─────────────────────────────────────────────────────────────────────────────

SEP  = "-" * 72
SEP2 = "=" * 72


def afficher_rapport(besoins, stock_norm, source_a, source_b):
    print(f"\n{BOLD}{CYAN}{SEP2}{RESET}")
    print(f"{BOLD}{CYAN}  DIAGNOSTIC TRACABILITE — MATCHING FIFO / LEXIQUE ESPECES{RESET}")
    print(f"{BOLD}{CYAN}  Base : {DB_PATH}{RESET}")
    print(f"{BOLD}{CYAN}{SEP2}{RESET}\n")
    print(f"  {BOLD}Liste A — Besoins  :{RESET} {len(besoins):>4} entree(s)")
    print(f"  {DIM}  Source : {source_a}{RESET}")
    print(f"  {BOLD}Liste B — Stock    :{RESET} {len(stock_norm):>4} entree(s)")
    print(f"  {DIM}  Source : {source_b}{RESET}")
    print(f"\n{SEP}")

    succes, echecs = [], []

    for ing in besoins:
        match = match_produit(ing, stock_norm)
        code, muscle = extraire_code_et_muscle(ing)

        if match:
            print(
                f"  {GREEN}[OK]   {ing:<46}{RESET}"
                f"  {GREEN}---> {match}{RESET}"
            )
            succes.append(ing)
        else:
            print(
                f"  {RED}[ECHEC] {ing:<45}{RESET}"
                f"  {RED}---> Aucune correspondance stock.{RESET}"
                f"  {DIM}[code={code!r} muscle={muscle!r}]{RESET}"
            )
            echecs.append(ing)

    print(f"{SEP}\n")

    # ── Statistiques finales ──────────────────────────────────────────────────
    total      = len(besoins)
    nb_ok      = len(succes)
    nb_ko      = len(echecs)
    couverture = (nb_ok / total * 100) if total > 0 else 0.0

    couleur_taux = GREEN if couverture >= 80 else (YELLOW if couverture >= 50 else RED)

    print(
        f"  {BOLD}RECAPITULATIF :{RESET}"
        f"  Total testes : {BOLD}{total}{RESET}"
        f"  |  Succes : {GREEN}{BOLD}{nb_ok}{RESET}"
        f"  |  Echecs : {RED}{BOLD}{nb_ko}{RESET}"
        f"  |  Couverture : {couleur_taux}{BOLD}{couverture:.1f}%{RESET}"
    )

    if echecs:
        print(f"\n  {BOLD}{RED}Ingredients sans correspondance ({nb_ko}) :{RESET}")
        for nom in echecs:
            code, muscle = extraire_code_et_muscle(nom)
            print(
                f"    {RED}•{RESET} {nom:<48}"
                f"  {DIM}code={code!r}  muscle={muscle!r}{RESET}"
            )

    print()
    return nb_ko  # code de retour : 0 si tout est OK


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

def main():
    demo      = "--demo"      in sys.argv
    catalogue = "--catalogue" in sys.argv

    besoins, stock, source_a, source_b = charger_donnees(DB_PATH, demo, catalogue)

    if not besoins:
        print(f"\n{YELLOW}Aucun besoin a auditer. "
              f"Utilisez --demo pour un test rapide.{RESET}\n")
        sys.exit(0)

    # Pré-calcul du stock normalisé (1 seule fois pour tous les matchings)
    stock_norm = [(nom, normaliser(nom)) for nom in stock]

    nb_echecs = afficher_rapport(besoins, stock_norm, source_a, source_b)
    sys.exit(0 if nb_echecs == 0 else 1)


if __name__ == "__main__":
    main()

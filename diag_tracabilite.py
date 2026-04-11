#!/usr/bin/env python3
"""
diag_tracabilite.py
-------------------
Vérifie la correspondance entre les ingrédients des recettes et les produits
présents en stock (réceptions) dans la base haccp.db.

Usage :
  python diag_tracabilite.py           # mode normal (recette_ingredients réelle)
  python diag_tracabilite.py --demo    # mode démo avec ingrédients simulés
"""

import sqlite3
import sys
import os
import io

# Force UTF-8 sur Windows pour les emojis et caractères accentués
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = os.path.join(os.path.dirname(__file__), "haccp.db")

LEXIQUE = {
    "VB": ["bœuf", "vache", "bovine", "bf", "boeuf", "viande bovine"],
    "VX": ["veau", "vx"],
    "PC": ["porc", "cochon", "pork"],
    "AG": ["agneau", "agn"],
    "GI": ["gibier", "cerf", "sanglier"],
    "CH": ["cheval", "equin", "chevalin"],
    "VO": ["volaille", "poulet", "dinde", "canard", "pintade"],
    "EX": ["exotique"],
}

# Tous les synonymes indexés par valeur (pour recherche inverse)
_SYNONYMES_INVERSE = {
    syn.lower(): code
    for code, syns in LEXIQUE.items()
    for syn in syns
}

MOTS_PARASITES = {
    "sans", "avec", "os", "pad", "vrac", "de", "la", "le", "les", "du",
    "et", "en", "sur", "par", "un", "une", "des", "au", "aux",
    "carcasse", "entier", "entière", "desossé", "désossé",
}

# Ingrédients de démo quand recette_ingredients n'existe pas encore
DEMO_INGREDIENTS = [
    "VB-COLLIER SANS OS",
    "VB-PALERON",
    "VB-MACREUSE À BIFTECK",
    "VX-QUASI",
    "VX-NOIX",
    "PC-ECHINE",
    "AG-GIGOT",
    "GI-FILET DE CERF",
    "VO-POULET ENTIER",
    "VB-FICTIF INEXISTANT",   # intentionnellement sans match
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normaliser(texte: str) -> str:
    """Minuscule + suppression des accents courants."""
    remplacement = str.maketrans(
        "àâäéèêëîïôùûüç",
        "aaaeeeeiioouuc"
    )
    return texte.lower().translate(remplacement)


def extraire_code(ingredient: str) -> tuple[str, str]:
    """
    Retourne (code, reste) depuis un ingredient type "VB-COLLIER SANS OS".
    Le code est la partie avant le premier tiret s'il existe dans le LEXIQUE,
    sinon on tente de déduire le code depuis les synonymes du lexique.
    """
    ingredient = ingredient.strip()
    if "-" in ingredient:
        parties = ingredient.split("-", 1)
        code_candidat = parties[0].strip().upper()
        reste = parties[1].strip()
        if code_candidat in LEXIQUE:
            return code_candidat, reste
        # Le préfixe n'est pas un code connu → on cherche dans le reste
        return "", ingredient
    return "", ingredient


def extraire_muscle(reste: str) -> str:
    """
    Supprime les mots parasites et le code pour ne garder que le muscle.
    Exemple : "COLLIER SANS OS PAD" → "COLLIER"
    """
    mots = normaliser(reste).split()
    mots_filtres = [m for m in mots if m not in MOTS_PARASITES and len(m) > 1]
    # Retourne le premier mot significatif (la coupe principale)
    return mots_filtres[0] if mots_filtres else normaliser(reste)


def synonymes_pour_code(code: str) -> list[str]:
    """Retourne tous les synonymes (normalisés) associés à un code espèce."""
    return [normaliser(s) for s in LEXIQUE.get(code, [])]


# ---------------------------------------------------------------------------
# Chargement des données
# ---------------------------------------------------------------------------

def charger_produits_en_stock(conn: sqlite3.Connection) -> list[dict]:
    """
    Retourne les produits qui ont au moins une ligne de réception en stock
    (quantite > 0 et dlc >= aujourd'hui).
    Si reception_lignes est vide, retourne tous les produits du catalogue.
    """
    cursor = conn.cursor()

    # Vérifie s'il y a du stock réel
    cursor.execute("SELECT COUNT(*) FROM reception_lignes WHERE quantite > 0")
    nb_stock = cursor.fetchone()[0]

    if nb_stock > 0:
        cursor.execute("""
            SELECT DISTINCT p.nom, p.espece, p.code_unique
            FROM produits p
            JOIN reception_lignes rl ON rl.produit_nom = p.nom
            WHERE rl.quantite > 0
              AND (rl.dlc IS NULL OR rl.dlc >= date('now'))
        """)
        source = "stock réel (réceptions)"
    else:
        # Fallback : catalogue complet (base de comparaison théorique)
        cursor.execute("SELECT nom, espece, code_unique FROM produits")
        source = "catalogue produits (aucun stock reçu pour l'instant)"

    rows = cursor.fetchall()
    produits = [{"nom": r[0], "espece": r[1], "code_unique": r[2]} for r in rows]
    return produits, source


def charger_ingredients(conn: sqlite3.Connection, demo: bool) -> list[str]:
    """
    Retourne la liste des ingrédients uniques.
    En mode démo, utilise DEMO_INGREDIENTS.
    Sinon, tente de lire recette_ingredients.
    """
    if demo:
        return DEMO_INGREDIENTS

    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='recette_ingredients'"
    )
    if not cursor.fetchone():
        return None  # Table absente

    # Découverte dynamique des colonnes
    cursor.execute("PRAGMA table_info(recette_ingredients)")
    colonnes = [row[1] for row in cursor.fetchall()]

    # Candidats possibles pour le nom de l'ingrédient (ordre de priorité)
    candidats = [
        "nom_ingredient", "nom", "ingredient", "libelle",
        "designation", "produit", "article", "name",
    ]
    col = next((c for c in candidats if c in colonnes), None)

    if col is None:
        print(f"⚠️  Colonnes trouvées dans recette_ingredients : {colonnes}")
        print("    Aucune colonne reconnue comme nom d'ingrédient.")
        print("    Ajoutez le nom de la colonne correcte dans la liste 'candidats' du script.")
        return []

    cursor.execute(
        f"SELECT DISTINCT {col} FROM recette_ingredients WHERE {col} IS NOT NULL"
    )
    return [r[0] for r in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Moteur de correspondance
# ---------------------------------------------------------------------------

def chercher_correspondance(ingredient: str, produits: list[dict]) -> dict | None:
    """
    Cherche parmi `produits` un produit qui correspond à `ingredient`.
    Critère : le nom du produit doit contenir le muscle ET (le code OU un synonyme).
    Retourne le premier produit matchant, ou None.
    """
    code, reste = extraire_code(ingredient)
    muscle = extraire_muscle(reste if reste else ingredient)

    for produit in produits:
        nom_produit = normaliser(produit["nom"])
        espece_produit = normaliser(produit["espece"] or "")

        # 1. Le nom du produit contient-il le muscle ?
        if muscle not in nom_produit:
            continue

        # 2. Le code correspond-il ?
        if code:
            # Vérification directe : le nom commence par "CODE-"
            if nom_produit.startswith(code.lower() + "-"):
                return produit
            # Vérification via synonymes du lexique dans l'espèce du produit
            for syn in synonymes_pour_code(code):
                if syn in espece_produit or syn in nom_produit:
                    return produit
        else:
            # Pas de code → correspondance muscle seul (moins fiable)
            return produit

    return None


# ---------------------------------------------------------------------------
# Affichage
# ---------------------------------------------------------------------------

VERT  = "\033[92m"
ROUGE = "\033[91m"
RESET = "\033[0m"
GRAS  = "\033[1m"

def icone_ok(ok: bool) -> str:
    return "🟢" if ok else "🔴"


def afficher_rapport(resultats: list[dict], source_stock: str, demo: bool):
    mode_label = " [MODE DÉMO]" if demo else ""
    print()
    print(f"{GRAS}{'=' * 62}{RESET}")
    print(f"{GRAS}  DIAGNOSTIC TRAÇABILITÉ INGRÉDIENTS → STOCK{mode_label}{RESET}")
    print(f"{'=' * 62}")
    print(f"  Source stock : {source_stock}")
    print(f"{'=' * 62}{RESET}")
    print()

    nb_match = 0
    for r in resultats:
        ok = r["match"] is not None
        if ok:
            nb_match += 1
        couleur = VERT if ok else ROUGE
        icone = icone_ok(ok)
        ingredient = r["ingredient"]
        code = r["code"] or "??"
        muscle = r["muscle"]

        if ok:
            detail = f"  → {r['match']['nom']}"
        else:
            detail = "  → Aucun lot en stock"

        print(f"  {icone} {couleur}{ingredient:<35}{RESET}  [{code}] muscle={muscle}")
        print(f"        {couleur}{detail}{RESET}")
        print()

    total = len(resultats)
    taux = (nb_match / total * 100) if total > 0 else 0
    couleur_taux = VERT if taux >= 80 else (ROUGE if taux < 50 else "\033[93m")

    print(f"{'=' * 62}")
    print(f"{GRAS}  Résultats : {nb_match}/{total} ingrédients couverts{RESET}")
    print(f"{GRAS}  {couleur_taux}Taux de couverture de la traçabilité : {taux:.1f}%{RESET}")
    print(f"{'=' * 62}")
    print()

    if total == 0:
        print("  ⚠️  Aucun ingrédient trouvé dans recette_ingredients.")
        print("      Utilisez --demo pour tester le moteur de correspondance.")
        print()


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main():
    demo = "--demo" in sys.argv

    if not os.path.exists(DB_PATH):
        print(f"❌ Base de données introuvable : {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    try:
        # Chargement des ingrédients
        ingredients = charger_ingredients(conn, demo)

        if ingredients is None:
            print()
            print("⚠️  La table 'recette_ingredients' n'existe pas encore dans la base.")
            print("    Elle sera créée lors de la Phase 2 (module Recettes).")
            print()
            print("    Pour tester le moteur dès maintenant :")
            print("      python diag_tracabilite.py --demo")
            print()
            conn.close()
            return

        if not ingredients:
            print()
            print("ℹ️  La table recette_ingredients existe mais est vide.")
            print("   Ajoutez des recettes pour lancer le diagnostic.")
            print()
            conn.close()
            return

        # Chargement du stock
        produits, source_stock = charger_produits_en_stock(conn)

        # Analyse de chaque ingrédient
        resultats = []
        for ing in ingredients:
            code, reste = extraire_code(ing)
            muscle = extraire_muscle(reste if reste else ing)
            match = chercher_correspondance(ing, produits)
            resultats.append({
                "ingredient": ing,
                "code": code,
                "muscle": muscle,
                "match": match,
            })

        # Tri : 🔴 en premier pour repérer rapidement les manques
        resultats.sort(key=lambda r: (r["match"] is not None, r["ingredient"]))

        afficher_rapport(resultats, source_stock, demo)

    finally:
        conn.close()


if __name__ == "__main__":
    main()

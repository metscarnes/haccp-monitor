"""
seed_taches_nettoyage.py — Popule la table taches_nettoyage dans haccp.db
Usage : python scripts/seed_taches_nettoyage.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "haccp.db"

TACHES = [
    # zone                  | nom_tache                                        | frequence     | methode_produit
    # ─── CHAMBRE FROIDE ──────────────────────────────────────────────────────────
    ("CHAMBRE FROIDE",      "SOL",                                            "Quotidien",    "KING FLASH GERM"),
    ("CHAMBRE FROIDE",      "SIPHON",                                         "Quotidien",    "KING FLASH GERM"),
    ("CHAMBRE FROIDE",      "MURS",                                           "Hebdomadaire", "KING FLASH GERM"),
    ("CHAMBRE FROIDE",      "PORTE ET POIGNEE",                               "Quotidien",    "KING FLASH GERM"),
    # ─── ESPACE PREPARATION ──────────────────────────────────────────────────────
    ("ESPACE PREPARATION",  "SOL",                                            "Quotidien",    "KING FLASH GERM"),
    ("ESPACE PREPARATION",  "BILLOT",                                         "Quotidien",    "KING FLASH GERM"),
    ("ESPACE PREPARATION",  "PLONGE MANUELLE, DOUCHETTES",                    "Quotidien",    "KING FLASH GERM"),
    ("ESPACE PREPARATION",  "SIPHON",                                         "Quotidien",    "KING FLASH GERM"),
    ("ESPACE PREPARATION",  "ARMOIRE UV",                                     "Hebdomadaire", "KING FLASH GERM"),
    ("ESPACE PREPARATION",  "COUTEAUX ET USTENSILES",                         "Quotidien",    "KING FLASH GERM"),
    ("ESPACE PREPARATION",  "SCIES A OS",                                     "Quotidien",    "KING FLASH GERM"),
    ("ESPACE PREPARATION",  "TABLIERS",                                       "Quotidien",    "KING FLASH GERM"),
    ("ESPACE PREPARATION",  "GANTS EN COTE DE MAILLE",                        "Quotidien",    "KING FLASH GERM"),
    ("ESPACE PREPARATION",  "MACHINE A HACHER",                               "Quotidien",    "KING FLASH GERM"),
    ("ESPACE PREPARATION",  "PORTE ET POIGNEE",                               "Quotidien",    "KING FLASH GERM"),
    ("ESPACE PREPARATION",  "PLATEAUX",                                       "Quotidien",    "KING FLASH GERM"),
    ("ESPACE PREPARATION",  "MURS 1M50",                                      "Quotidien",    "KING FLASH GERM"),
    # ─── ESPACE DE VENTE ─────────────────────────────────────────────────────────
    ("ESPACE DE VENTE",     "RAYON",                                          "Quotidien",    "KING FLASH GERM"),
    ("ESPACE DE VENTE",     "SOL",                                            "Quotidien",    "KING FLASH GERM"),
    ("ESPACE DE VENTE",     "PIC PRIX",                                       "Quotidien",    "KING FLASH GERM"),
    ("ESPACE DE VENTE",     "BALANCE",                                        "Quotidien",    "KING FLASH GERM"),
    ("ESPACE DE VENTE",     "MEUBLES FROIDS",                                 "Quotidien",    "KING FLASH GERM"),
    ("ESPACE DE VENTE",     "TRANCHEUSES",                                    "Quotidien",    "KING FLASH GERM"),
    ("ESPACE DE VENTE",     "MACHINE A HACHER",                               "Quotidien",    "KING FLASH GERM"),
    ("ESPACE DE VENTE",     "VITRE",                                          "Quotidien",    "METRO LAVE VITRE ANTI TRACE"),
    # ─── CUISINE ─────────────────────────────────────────────────────────────────
    ("CUISINE",             "PORTE ET POIGNEE",                               "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "MUR 1M50",                                       "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "PORTES",                                         "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "LAVE MAIN (DISTRIB. SAVON + ESSUIE MAINS)",      "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "POIGNEES",                                       "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "INTERRUPTEURS",                                  "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "SOL / SIPHON",                                   "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "CELLULE DE REFROIDISSEMENT",                     "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "BALANCE",                                        "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "PLANS DE TRAVAIL",                               "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "FOUR",                                           "Quotidien",    "iCareSystem AutoDose"),
    ("CUISINE",             "SUPPORT SAC POUBELLES",                          "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "PLAQUE CUISSON",                                 "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "MELANGEUR",                                      "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "POUSSOIR HYDRAULIQUE PHX25",                     "Quotidien",    "KING FLASH GERM"),
    ("CUISINE",             "MACHINE SOUS VIDE",                              "Quotidien",    "KING FLASH GERM"),
    # ─── JARDINET ────────────────────────────────────────────────────────────────
    ("JARDINET",            "MURS",                                           "Hebdomadaire", "KING FLASH GERM"),
    ("JARDINET",            "PORTES",                                         "Hebdomadaire", "KING FLASH GERM"),
    ("JARDINET",            "POIGNEES",                                       "Quotidien",    "KING FLASH GERM"),
    ("JARDINET",            "SOL",                                            "Hebdomadaire", "KING FLASH GERM"),
    # ─── WC ──────────────────────────────────────────────────────────────────────
    ("WC",                  "MURS",                                           "Hebdomadaire", "KING FLASH GERM"),
    ("WC",                  "SOL",                                            "Quotidien",    "KING FLASH GERM"),
    ("WC",                  "SANITAIRE",                                      "Quotidien",    "KING FLASH GERM"),
    ("WC",                  "PORTES / POIGNEES",                              "Quotidien",    "KING FLASH GERM"),
    ("WC",                  "LAVE MAIN (DISTRIB. SAVON + ESSUIE MAINS)",      "Quotidien",    "KING FLASH GERM"),
    # ─── ROTISSERIE ──────────────────────────────────────────────────────────────
    ("ROTISSERIE",          "ROTISSOIRE",                                     "Quotidien",    "KING FLASH GERM"),
    ("ROTISSERIE",          "BROCHE",                                         "Quotidien",    "KING FLASH GERM"),
    ("ROTISSERIE",          "ACCESSOIRES",                                    "Quotidien",    "KING FLASH GERM"),
    ("ROTISSERIE",          "VITRE",                                          "Quotidien",    "KING FLASH GERM"),
]


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS taches_nettoyage (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            zone            TEXT    NOT NULL,
            nom_tache       TEXT    NOT NULL,
            frequence       TEXT    NOT NULL,
            methode_produit TEXT    NOT NULL
        )
    """)

    cur.execute("DELETE FROM taches_nettoyage")

    cur.executemany(
        "INSERT INTO taches_nettoyage (zone, nom_tache, frequence, methode_produit) VALUES (?, ?, ?, ?)",
        TACHES,
    )

    conn.commit()
    conn.close()

    print(f"{len(TACHES)} tâches insérées avec succès dans {DB_PATH}")


if __name__ == "__main__":
    main()

"""
import_matieres_premieres.py
----------------------------
1. Crée les tables Phase 2 manquantes dans data/haccp.db
2. Insère les seed data Phase 2 (INSERT OR IGNORE — idempotent)
3. Ajoute les colonnes manquantes à `produits`
4. Purge les doublons dans personnel, pieges, plan_nettoyage
5. Importe 365 matières premières depuis data/extraction_matiere_premiere.xlsx
"""

import sqlite3
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("Installation de openpyxl...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "-q"])
    import openpyxl

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "haccp.db"
XLSX_PATH = ROOT / "data" / "extraction_matiere_premiere.xlsx"

# ---------------------------------------------------------------------------
# Schéma Phase 2 (CREATE TABLE IF NOT EXISTS — idempotent)
# ---------------------------------------------------------------------------
PHASE2_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS produits (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id              INTEGER NOT NULL,
    nom                      TEXT    NOT NULL,
    categorie                TEXT    NOT NULL,
    dlc_jours                INTEGER NOT NULL,
    temperature_conservation TEXT    NOT NULL,
    format_etiquette         TEXT    DEFAULT 'standard_60x40',
    actif                    BOOLEAN DEFAULT 1,
    created_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

CREATE TABLE IF NOT EXISTS regles_dlc (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id INTEGER NOT NULL,
    categorie   TEXT    NOT NULL,
    dlc_jours   INTEGER NOT NULL,
    note        TEXT,
    UNIQUE(boutique_id, categorie),
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

CREATE TABLE IF NOT EXISTS etiquettes_generees (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id              INTEGER NOT NULL,
    produit_id               INTEGER,
    produit_nom              TEXT    NOT NULL,
    type_date                TEXT    NOT NULL,
    date_etiquette           DATE    NOT NULL,
    dlc                      DATE    NOT NULL,
    temperature_conservation TEXT,
    operateur                TEXT    NOT NULL,
    numero_lot               TEXT    NOT NULL,
    lot_type                 TEXT    NOT NULL,
    info_complementaire      TEXT,
    mode_impression          TEXT    NOT NULL DEFAULT 'manuel',
    imprime_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id),
    FOREIGN KEY (produit_id)  REFERENCES produits(id)
);

CREATE INDEX IF NOT EXISTS idx_etiquettes_boutique_date
    ON etiquettes_generees(boutique_id, imprime_at);

CREATE INDEX IF NOT EXISTS idx_etiquettes_dlc
    ON etiquettes_generees(boutique_id, dlc);

CREATE TABLE IF NOT EXISTS fournisseurs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id INTEGER NOT NULL,
    nom         TEXT    NOT NULL,
    actif       BOOLEAN DEFAULT 1,
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

CREATE TABLE IF NOT EXISTS receptions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id          INTEGER NOT NULL,
    fournisseur_id       INTEGER,
    fournisseur_nom      TEXT    NOT NULL,
    numero_bon_livraison TEXT,
    operateur            TEXT    NOT NULL,
    date_reception       DATETIME DEFAULT CURRENT_TIMESTAMP,
    heure_livraison      TEXT,
    temperature_camion   REAL,
    proprete_camion      TEXT,
    conforme             BOOLEAN,
    commentaire          TEXT,
    FOREIGN KEY (boutique_id)    REFERENCES boutiques(id),
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
);

CREATE INDEX IF NOT EXISTS idx_receptions_boutique_date
    ON receptions(boutique_id, date_reception);

CREATE TABLE IF NOT EXISTS reception_lignes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    reception_id        INTEGER NOT NULL,
    produit_nom         TEXT    NOT NULL,
    temperature_produit REAL,
    integrite_emballage TEXT,
    dlc                 DATE,
    numero_lot          TEXT,
    quantite            REAL,
    heure_stockage      TEXT,
    conforme            BOOLEAN,
    FOREIGN KEY (reception_id) REFERENCES receptions(id)
);

CREATE TABLE IF NOT EXISTS non_conformites_fournisseur (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id         INTEGER NOT NULL,
    reception_id        INTEGER,
    reception_ligne_id  INTEGER,
    operateur           TEXT    NOT NULL,
    date_livraison      DATE,
    fournisseur_nom     TEXT,
    produits            TEXT,
    date_fabrication    DATE,
    dlc                 DATE,
    nombre_barquettes   INTEGER,
    nature_nc           TEXT,
    commentaires        TEXT,
    refuse_livraison    BOOLEAN DEFAULT 0,
    nc_apres_livraison  BOOLEAN DEFAULT 0,
    info_ddpp           BOOLEAN DEFAULT 0,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boutique_id)        REFERENCES boutiques(id),
    FOREIGN KEY (reception_id)       REFERENCES receptions(id),
    FOREIGN KEY (reception_ligne_id) REFERENCES reception_lignes(id)
);

CREATE TABLE IF NOT EXISTS personnel (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id INTEGER NOT NULL,
    prenom      TEXT    NOT NULL,
    actif       BOOLEAN DEFAULT 1,
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

CREATE TABLE IF NOT EXISTS tache_types (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id   INTEGER NOT NULL,
    code          TEXT    NOT NULL,
    libelle       TEXT    NOT NULL,
    frequence     TEXT    NOT NULL,
    heure_cible   TEXT,
    photo_requise BOOLEAN DEFAULT 0,
    actif         BOOLEAN DEFAULT 1,
    UNIQUE(boutique_id, code),
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

CREATE TABLE IF NOT EXISTS tache_validations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id         INTEGER NOT NULL,
    tache_type_id       INTEGER NOT NULL,
    operateur           TEXT    NOT NULL,
    date_tache          DATE    NOT NULL,
    heure_validation    DATETIME DEFAULT CURRENT_TIMESTAMP,
    conforme            BOOLEAN,
    photo_path          TEXT,
    commentaire         TEXT,
    donnees_specifiques TEXT,
    FOREIGN KEY (boutique_id)   REFERENCES boutiques(id),
    FOREIGN KEY (tache_type_id) REFERENCES tache_types(id)
);

CREATE INDEX IF NOT EXISTS idx_validations_boutique_date
    ON tache_validations(boutique_id, date_tache);

CREATE INDEX IF NOT EXISTS idx_validations_type_date
    ON tache_validations(tache_type_id, date_tache);

CREATE TABLE IF NOT EXISTS pieges (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id  INTEGER NOT NULL,
    type         TEXT    NOT NULL,
    identifiant  TEXT    NOT NULL,
    localisation TEXT,
    actif        BOOLEAN DEFAULT 1,
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

CREATE TABLE IF NOT EXISTS plan_nettoyage (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id        INTEGER NOT NULL,
    local              TEXT    NOT NULL,
    surface_equipement TEXT    NOT NULL,
    frequence          TEXT    NOT NULL,
    actif              BOOLEAN DEFAULT 1,
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);
"""

SEED_PHASE2 = """
INSERT OR IGNORE INTO regles_dlc (boutique_id, categorie, dlc_jours, note) VALUES
(1, 'viande_hachee',         1,   'Viande hachée fraîche'),
(1, 'viande_pieces',         3,   'Pièces de viande entières'),
(1, 'preparation_crue',      2,   'Préparations crues : merguez, saucisses...'),
(1, 'charcuterie_tranchee',  5,   'Charcuterie tranchée à la coupe'),
(1, 'plat_cuisine',          3,   'Plats cuisinés maison'),
(1, 'produit_deconge',       3,   'Calculé depuis date de décongélation (réglementaire)'),
(1, 'produit_congele',       180, 'Selon DLC initiale — congélation maison');

INSERT OR IGNORE INTO personnel (boutique_id, prenom) VALUES
(1, 'Éric'),
(1, 'Ulysse');

INSERT OR IGNORE INTO tache_types (boutique_id, code, libelle, frequence, heure_cible, photo_requise) VALUES
(1, 'etalonnage_thermometres',     'Étalonnage thermomètres',                     'ponctuel',     NULL,    0),
(1, 'releve_temp_enceintes_matin', 'Relevé températures enceintes — Matin',        'quotidien',    '08:00', 0),
(1, 'releve_temp_enceintes_soir',  'Relevé températures enceintes — Soir',         'quotidien',    '18:00', 0),
(1, 'action_corrective_temp',      'Action corrective température',                'evenementiel', NULL,    0),
(1, 'pieges_rongeurs',             'Présence rongeurs sur pièges',                 'hebdomadaire', NULL,    0),
(1, 'nettoyage_pieges_oiseaux',    'Nettoyage pièges oiseaux',                     'hebdomadaire', NULL,    0),
(1, 'temp_lave_vaisselle',         'Températures lave-vaisselle',                  'quotidien',    '12:00', 0),
(1, 'controle_huile_friture',      'Contrôle huile de friture',                    'evenementiel', NULL,    0),
(1, 'suivi_temp_production',       'Suivi températures production/service',        'quotidien',    '12:00', 0),
(1, 'suivi_decongélation',         'Suivi décongélation',                          'evenementiel', NULL,    0),
(1, 'suivi_congelation',           'Suivi congélation',                            'evenementiel', NULL,    0),
(1, 'nettoyage_desinfection',      'Nettoyage et désinfection',                    'quotidien',    '19:00', 0),
(1, 'tiac',                        'TIAC — Toxi-infection alimentaire collective',  'exceptionnel', NULL,    1);

INSERT OR IGNORE INTO pieges (boutique_id, type, identifiant, localisation) VALUES
(1, 'rongeur', 'P1', 'Entrée laboratoire'),
(1, 'rongeur', 'P2', 'Fond laboratoire'),
(1, 'oiseau',  'P3', 'Entrée boutique');

INSERT OR IGNORE INTO plan_nettoyage (boutique_id, local, surface_equipement, frequence) VALUES
(1, 'Laboratoire', 'Plan de travail inox',  'quotidien'),
(1, 'Laboratoire', 'Sol laboratoire',        'quotidien'),
(1, 'Boutique',    'Vitrine réfrigérée',     'quotidien'),
(1, 'Boutique',    'Sol boutique',           'quotidien'),
(1, 'Laboratoire', 'Chambre froide 1',       'hebdomadaire'),
(1, 'Laboratoire', 'Chambre froide 2',       'hebdomadaire'),
(1, 'Laboratoire', 'Hotte aspiration',       'mensuel'),
(1, 'Boutique',    'Trancheur',              'quotidien');
"""

# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------
ESPECE_MAP = {
    "VB": "Bœuf",
    "VX": "Veau",
    "PC": "Porc",
    "AG": "Agneau",
    "GI": "Gibier",
    "VC": "Volaille",
    "VD": "Volaille",
    "VL": "Volaille",
    "VP": "Volaille",
    "VE": "Exotique",
    "CH": "Cheval",
}

COUPE_MAP = {
    "COUPE PRIMAIRE":    (1, "COUPE PRIMAIRE"),
    "COUPE PREMIERE":    (1, "COUPE PRIMAIRE"),   # alias/typo
    "COUPE DE GROS":     (2, "COUPE DE GROS"),
    "COUPE SECONDAIRE":  (3, "COUPE SECONDAIRE"),
    "PAV":               (4, "PAV"),
}

TEMP_MAP = {
    "0-4": "0°C à +4°C",
    "0-7": "0°C à +7°C",
    "0-3": "0°C à +3°C",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def add_column_if_missing(cur, table, col, col_def):
    """Ajoute la colonne si absente. UNIQUE est géré via un index séparé."""
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    # Retire UNIQUE de col_def pour ALTER TABLE (SQLite ne le supporte pas)
    alter_def = col_def.replace("UNIQUE", "").strip()
    if col not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {alter_def}")
        print(f"  + colonne ajoutee : {table}.{col}")
    else:
        print(f"  ok colonne existante : {table}.{col}")


def dedup_table(cur, table, boutique_id, key_col):
    """Garde le premier enregistrement de chaque valeur distincte de key_col."""
    cur.execute(f"""
        DELETE FROM {table}
        WHERE boutique_id = ?
          AND id NOT IN (
              SELECT MIN(id) FROM {table}
              WHERE boutique_id = ?
              GROUP BY {key_col}
          )
    """, (boutique_id, boutique_id))
    deleted = cur.rowcount
    if deleted:
        print(f"  - {table} : {deleted} doublon(s) supprimé(s)")
    else:
        print(f"  ✓ {table} : pas de doublons")


# ---------------------------------------------------------------------------
# Script principal
# ---------------------------------------------------------------------------
def main():
    print(f"Base : {DB_PATH}")
    print(f"Excel : {XLSX_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # -----------------------------------------------------------------------
    # Étape 1 — Tables Phase 2
    # -----------------------------------------------------------------------
    print("\n[1/4] Création tables Phase 2...")
    conn.executescript(PHASE2_SCHEMA)
    conn.executescript(SEED_PHASE2)
    conn.commit()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  Tables présentes ({len(tables)}) : {', '.join(tables)}")

    # -----------------------------------------------------------------------
    # Étape 2 — Colonnes manquantes dans produits
    # -----------------------------------------------------------------------
    print("\n[2/4] Ajout colonnes manquantes dans produits...")
    add_column_if_missing(cur, "produits", "code_unique",    "TEXT UNIQUE")
    add_column_if_missing(cur, "produits", "espece",         "TEXT")
    add_column_if_missing(cur, "produits", "etape",          "INTEGER")
    add_column_if_missing(cur, "produits", "coupe_niveau",   "TEXT")
    add_column_if_missing(cur, "produits", "conditionnement","TEXT")
    # Index unique sur code_unique (CREATE INDEX IF NOT EXISTS — idempotent)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_produits_code_unique
        ON produits(code_unique)
    """)
    conn.commit()

    # -----------------------------------------------------------------------
    # Étape 3 — Purge des doublons
    # -----------------------------------------------------------------------
    print("\n[3/4] Purge des doublons...")
    dedup_table(cur, "personnel",      1, "prenom")
    dedup_table(cur, "pieges",         1, "identifiant")
    dedup_table(cur, "plan_nettoyage", 1, "surface_equipement")
    conn.commit()

    # -----------------------------------------------------------------------
    # Étape 4 — Import Excel
    # -----------------------------------------------------------------------
    print("\n[4/4] Import Excel → produits...")
    wb = openpyxl.load_workbook(XLSX_PATH)
    ws = wb.active

    inserted = 0
    skipped = 0
    errors = []

    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        nom, code_unique, coupe_raw, temp_raw, conditionnement = (
            row[0], row[1], row[2], row[3], row[4]
        )

        # Filtre : ligne valide si les 3 colonnes clés sont remplies
        if not (nom and code_unique and coupe_raw):
            continue

        nom         = str(nom).strip()
        code_unique = str(code_unique).strip()
        coupe_raw   = str(coupe_raw).strip().upper()

        # Espèce depuis les 2 premiers caractères du code
        prefix = code_unique[:2].upper()
        espece = ESPECE_MAP.get(prefix)
        if not espece:
            errors.append(f"  ligne {row_num} — préfixe inconnu : {prefix!r} ({code_unique})")
            espece = "Inconnu"

        # Coupe → etape + coupe_niveau
        coupe_entry = COUPE_MAP.get(coupe_raw)
        if coupe_entry:
            etape, coupe_niveau = coupe_entry
        else:
            errors.append(f"  ligne {row_num} — coupe inconnue : {coupe_raw!r} ({code_unique})")
            etape, coupe_niveau = (0, coupe_raw)

        # Température
        temp_str = str(temp_raw).strip() if temp_raw else "0-4"
        temperature_conservation = TEMP_MAP.get(temp_str, "0°C à +4°C")

        # Conditionnement
        cond = str(conditionnement).strip().upper() if conditionnement else "SOUS_VIDE"
        if cond not in ("SOUS_VIDE", "CARCASSE"):
            cond = "SOUS_VIDE"

        try:
            # Vérifie si le produit existe déjà
            cur.execute("SELECT id FROM produits WHERE code_unique = ?", (code_unique,))
            existing = cur.fetchone()
            if existing:
                cur.execute("""
                    UPDATE produits SET
                        nom                      = ?,
                        espece                   = ?,
                        etape                    = ?,
                        coupe_niveau             = ?,
                        temperature_conservation = ?,
                        conditionnement          = ?,
                        actif                    = 1
                    WHERE code_unique = ?
                """, (nom, espece, etape, coupe_niveau,
                      temperature_conservation, cond, code_unique))
            else:
                cur.execute("""
                    INSERT INTO produits
                        (boutique_id, nom, code_unique, espece, etape, coupe_niveau,
                         categorie, dlc_jours, temperature_conservation, conditionnement, actif)
                    VALUES (1, ?, ?, ?, ?, ?, 'matiere_premiere', 0, ?, ?, 1)
                """, (nom, code_unique, espece, etape, coupe_niveau,
                      temperature_conservation, cond))
            inserted += 1
        except sqlite3.Error as e:
            errors.append(f"  ligne {row_num} — erreur SQL : {e} ({code_unique})")
            skipped += 1

    conn.commit()
    conn.close()

    # -----------------------------------------------------------------------
    # Résumé
    # -----------------------------------------------------------------------
    print(f"\n  Résultat : {inserted} produits importés/mis à jour, {skipped} erreur(s)")
    if errors:
        print("\n  Anomalies :")
        for e in errors:
            print(e)

    print("\nImport terminé.")


if __name__ == "__main__":
    main()

"""
database.py — Couche d'accès SQLite (aiosqlite, async)

Responsabilités :
- Initialisation du schéma (CREATE TABLE IF NOT EXISTS)
- Fonctions d'insertion : relevés, alertes, rapports
- Fonctions de lecture : dashboard, historique, alertes en cours
- Purge automatique selon la politique de rétention
"""

import hashlib
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "haccp.db"

# ---------------------------------------------------------------------------
# Schéma
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ===========================================================================
-- PHASE 1 — Tables existantes
-- ===========================================================================

CREATE TABLE IF NOT EXISTS boutiques (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nom        TEXT NOT NULL,
    adresse    TEXT,
    siret      TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS enceintes (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id           INTEGER NOT NULL,
    nom                   TEXT NOT NULL,
    type                  TEXT NOT NULL,
    sonde_zigbee_id       TEXT,
    seuil_temp_min        REAL    DEFAULT 0.0,
    seuil_temp_max        REAL    DEFAULT 4.0,
    seuil_hum_max         REAL    DEFAULT 90.0,
    delai_alerte_minutes  INTEGER DEFAULT 5,
    actif                 BOOLEAN DEFAULT 1,
    created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(boutique_id, nom),
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

CREATE TABLE IF NOT EXISTS releves (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    enceinte_id    INTEGER NOT NULL,
    temperature    REAL    NOT NULL,
    humidite       REAL,
    batterie       INTEGER,
    qualite_signal INTEGER,
    horodatage     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (enceinte_id) REFERENCES enceintes(id)
);

CREATE INDEX IF NOT EXISTS idx_releves_enceinte_date
    ON releves(enceinte_id, horodatage);

CREATE TABLE IF NOT EXISTS alertes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    enceinte_id INTEGER NOT NULL,
    type        TEXT    NOT NULL,
    valeur      REAL,
    seuil       REAL,
    debut       DATETIME NOT NULL,
    fin         DATETIME,
    notifie     BOOLEAN  DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (enceinte_id) REFERENCES enceintes(id)
);

CREATE TABLE IF NOT EXISTS destinataires (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nom       TEXT NOT NULL,
    email     TEXT,
    telephone TEXT,
    actif     BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS rapports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id INTEGER NOT NULL,
    type        TEXT    NOT NULL,
    date_debut  DATE    NOT NULL,
    date_fin    DATE    NOT NULL,
    conforme    BOOLEAN,
    fichier_path TEXT,
    sha256      TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

-- ===========================================================================
-- PHASE 2 — Module DLC / Étiquettes
-- ===========================================================================

CREATE TABLE IF NOT EXISTS produits (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id              INTEGER NOT NULL DEFAULT 1,
    nom                      TEXT    NOT NULL,
    code_unique              TEXT    UNIQUE,
    espece                   TEXT,
    etape                    INTEGER,
    coupe_niveau             TEXT,
    conditionnement          TEXT    DEFAULT 'SOUS_VIDE',
    categorie                TEXT    NOT NULL DEFAULT 'matiere_premiere',
    dlc_jours                INTEGER NOT NULL DEFAULT 0,
    temperature_conservation TEXT    NOT NULL DEFAULT '0°C à +4°C',
    format_etiquette         TEXT    DEFAULT 'standard_60x40',
    type_produit             TEXT    NOT NULL DEFAULT 'brut',
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

-- ===========================================================================
-- PHASE 2 — Module Réception
-- ===========================================================================

CREATE TABLE IF NOT EXISTS fournisseurs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id INTEGER NOT NULL,
    nom         TEXT    NOT NULL,
    actif       BOOLEAN DEFAULT 1,
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

CREATE TABLE IF NOT EXISTS receptions (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    personnel_id             INTEGER NOT NULL,
    date_reception           DATE    DEFAULT CURRENT_DATE,
    heure_reception          TEXT    NOT NULL,
    temperature_camion       REAL,
    proprete_camion          TEXT    DEFAULT 'satisfaisant',
    camion_conforme          INTEGER DEFAULT 1,
    fournisseur_principal_id INTEGER,
    photo_bl_filename        TEXT,
    commentaire              TEXT,
    conformite_globale       TEXT    DEFAULT 'conforme',
    livraison_refusee        INTEGER DEFAULT 0,
    information_ddpp         INTEGER DEFAULT 0,
    commentaire_nc           TEXT,
    created_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (personnel_id)             REFERENCES personnel(id),
    FOREIGN KEY (fournisseur_principal_id) REFERENCES fournisseurs(id)
);

CREATE INDEX IF NOT EXISTS idx_receptions_date
    ON receptions(date_reception);

CREATE TABLE IF NOT EXISTS reception_lignes (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    reception_id              INTEGER NOT NULL,
    produit_id                INTEGER NOT NULL,
    fournisseur_id            INTEGER,
    numero_lot                TEXT,
    dlc                       DATE,
    dluo                      DATE,
    origine                   TEXT    DEFAULT 'France',
    poids_kg                  REAL,
    temperature_reception     REAL,
    temperature_conforme      INTEGER,
    couleur_conforme          INTEGER DEFAULT 1,
    couleur_observation       TEXT,
    consistance_conforme      INTEGER DEFAULT 1,
    consistance_observation   TEXT,
    exsudat_conforme          INTEGER DEFAULT 1,
    exsudat_observation       TEXT,
    odeur_conforme            INTEGER DEFAULT 1,
    odeur_observation         TEXT,
    ph_valeur                 REAL,
    ph_conforme               INTEGER,
    conforme                  INTEGER DEFAULT 1,
    created_at                DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reception_id)  REFERENCES receptions(id),
    FOREIGN KEY (produit_id)    REFERENCES produits(id),
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
);

CREATE TABLE IF NOT EXISTS fiches_incident (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    reception_id               INTEGER NOT NULL,
    reception_ligne_id         INTEGER,
    date_incident              DATE    DEFAULT CURRENT_DATE,
    heure_incident             TEXT    NOT NULL,
    fournisseur_id             INTEGER,
    produit_id                 INTEGER,
    numero_lot                 TEXT,
    nature_probleme            TEXT    NOT NULL,
    description                TEXT,
    action_immediate           TEXT    NOT NULL,
    livreur_present            INTEGER NOT NULL DEFAULT 0,
    signature_livreur_filename TEXT,
    etiquette_reprise_imprimee INTEGER DEFAULT 0,
    action_corrective          TEXT,
    suivi                      TEXT,
    statut                     TEXT    DEFAULT 'ouverte',
    cloturee_par               INTEGER,
    cloturee_le                DATETIME,
    created_at                 DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reception_id)       REFERENCES receptions(id),
    FOREIGN KEY (reception_ligne_id) REFERENCES reception_lignes(id),
    FOREIGN KEY (fournisseur_id)     REFERENCES fournisseurs(id),
    FOREIGN KEY (produit_id)         REFERENCES produits(id),
    FOREIGN KEY (cloturee_par)       REFERENCES personnel(id)
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

-- ===========================================================================
-- PHASE 2 — Module Tâches HACCP
-- ===========================================================================

CREATE TABLE IF NOT EXISTS personnel (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id INTEGER NOT NULL,
    prenom      TEXT    NOT NULL,
    actif       BOOLEAN DEFAULT 1,
    UNIQUE(boutique_id, prenom),
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

CREATE TABLE IF NOT EXISTS tache_types (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id  INTEGER NOT NULL,
    code         TEXT    NOT NULL,
    libelle      TEXT    NOT NULL,
    frequence    TEXT    NOT NULL,
    heure_cible  TEXT,
    photo_requise BOOLEAN DEFAULT 0,
    actif        BOOLEAN DEFAULT 1,
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
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id INTEGER NOT NULL,
    type        TEXT    NOT NULL,
    identifiant TEXT    NOT NULL,
    localisation TEXT,
    actif       BOOLEAN DEFAULT 1,
    UNIQUE(boutique_id, type, identifiant),
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

-- ===========================================================================
-- PHASE 2 — Module Ouvertures
-- ===========================================================================

CREATE TABLE IF NOT EXISTS ouvertures (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    produit_id         INTEGER NOT NULL,
    personnel_id       INTEGER NOT NULL,
    photo_filename     TEXT    NOT NULL,
    timestamp          DATETIME DEFAULT CURRENT_TIMESTAMP,
    source             TEXT    DEFAULT 'catalogue',
    reception_ligne_id INTEGER,
    FOREIGN KEY (produit_id)         REFERENCES produits(id),
    FOREIGN KEY (personnel_id)       REFERENCES personnel(id),
    FOREIGN KEY (reception_ligne_id) REFERENCES reception_lignes(id)
);

CREATE INDEX IF NOT EXISTS idx_ouvertures_produit
    ON ouvertures(produit_id);

CREATE INDEX IF NOT EXISTS idx_ouvertures_timestamp
    ON ouvertures(timestamp);

-- ===========================================================================
-- PHASE 3 — Module Fabrication (Recettes & Traçabilité)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS recettes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nom             TEXT    NOT NULL,
    produit_fini_id INTEGER NOT NULL,
    dlc_jours       INTEGER NOT NULL,
    instructions    TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (produit_fini_id) REFERENCES produits(id)
);

CREATE TABLE IF NOT EXISTS recette_ingredients (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    recette_id  INTEGER NOT NULL,
    produit_id  INTEGER NOT NULL,
    quantite    REAL,
    unite       TEXT,
    FOREIGN KEY (recette_id) REFERENCES recettes(id) ON DELETE CASCADE,
    FOREIGN KEY (produit_id) REFERENCES produits(id)
);

CREATE TABLE IF NOT EXISTS fabrications (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    recette_id           INTEGER NOT NULL,
    date                 TEXT    NOT NULL,
    lot_interne          TEXT    NOT NULL UNIQUE,
    personnel_id         INTEGER NOT NULL,
    info_complementaire  TEXT,
    poids_fabrique       REAL,
    dlc_finale           TEXT,
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recette_id)   REFERENCES recettes(id),
    FOREIGN KEY (personnel_id) REFERENCES personnel(id)
);

CREATE INDEX IF NOT EXISTS idx_fabrications_date
    ON fabrications(date);

CREATE INDEX IF NOT EXISTS idx_fabrications_lot
    ON fabrications(lot_interne);

-- ===========================================================================
-- Module Étalonnage Thermomètres (EET01)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS thermometres_ref (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id  INTEGER NOT NULL DEFAULT 1,
    nom          TEXT    NOT NULL,
    numero_serie TEXT,
    actif        BOOLEAN DEFAULT 1,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(boutique_id, nom)
);

CREATE TABLE IF NOT EXISTS etalonnages (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    reference           TEXT    NOT NULL DEFAULT 'EET01',
    date_etalonnage     DATE    NOT NULL,
    thermometre_ref_id  INTEGER NOT NULL,
    temperature_mesuree REAL    NOT NULL,
    conforme            INTEGER NOT NULL,
    action_corrective   TEXT    NOT NULL,
    operateur           TEXT    NOT NULL,
    commentaire         TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thermometre_ref_id) REFERENCES thermometres_ref(id)
);

CREATE INDEX IF NOT EXISTS idx_etalonnages_date
    ON etalonnages(date_etalonnage);

CREATE TABLE IF NOT EXISTS etalonnage_comparaisons (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    etalonnage_id   INTEGER NOT NULL,
    enceinte_id     INTEGER NOT NULL,
    enceinte_nom    TEXT    NOT NULL,
    temp_zigbee     REAL    NOT NULL,
    temp_reference  REAL    NOT NULL,
    ecart           REAL    NOT NULL,
    conforme        INTEGER NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (etalonnage_id) REFERENCES etalonnages(id),
    FOREIGN KEY (enceinte_id)   REFERENCES enceintes(id)
);

CREATE TABLE IF NOT EXISTS fabrication_lots (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    fabrication_id         INTEGER NOT NULL,
    recette_ingredient_id  INTEGER NOT NULL,
    reception_ligne_id     INTEGER NOT NULL,
    FOREIGN KEY (fabrication_id)        REFERENCES fabrications(id) ON DELETE CASCADE,
    FOREIGN KEY (recette_ingredient_id) REFERENCES recette_ingredients(id),
    FOREIGN KEY (reception_ligne_id)    REFERENCES reception_lignes(id)
);
"""

SEED_SQL = """
INSERT OR IGNORE INTO boutiques (id, nom, adresse, siret)
VALUES (1, 'Au Comptoir des Lilas', '122 rue de Paris, Les Lilas, 93260', '');

INSERT OR IGNORE INTO enceintes (id, boutique_id, nom, type, sonde_zigbee_id, seuil_temp_min, seuil_temp_max, seuil_hum_max, delai_alerte_minutes)
VALUES
(1, 1, 'Chambre froide 1', 'chambre_froide', 'chambre_froide_1',  0.0,  4.0, 90.0, 5),
(2, 1, 'Chambre froide 2', 'chambre_froide', 'chambre_froide_2',  0.0,  4.0, 90.0, 5),
(3, 1, 'vitrine',          'vitrine',        'vitrine',            0.0,  4.0, 90.0, 5),
(4, 1, 'laboratoire',      'laboratoire',    'laboratoire',       10.0, 15.0, 80.0, 5);
"""

SEED_SQL_PHASE2 = """
-- Règles DLC par défaut (boutique 1)
INSERT OR IGNORE INTO regles_dlc (boutique_id, categorie, dlc_jours, note) VALUES
(1, 'viande_hachee',         1, 'Viande hachée fraîche'),
(1, 'viande_pieces',         3, 'Pièces de viande entières'),
(1, 'preparation_crue',      2, 'Préparations crues : merguez, saucisses...'),
(1, 'charcuterie_tranchee',  5, 'Charcuterie tranchée à la coupe'),
(1, 'plat_cuisine',          3, 'Plats cuisinés maison'),
(1, 'produit_deconge',       3, 'Calculé depuis date de décongélation (réglementaire)'),
(1, 'produit_congele',       180, 'Selon DLC initiale — congélation maison');

-- Personnel par défaut (boutique 1)
INSERT OR IGNORE INTO personnel (boutique_id, prenom) VALUES
(1, 'Éric'),
(1, 'Ulysse');

-- Types de tâches HACCP par défaut (boutique 1) — 12 fiches (8+9 dans module Réception)
INSERT OR IGNORE INTO tache_types (boutique_id, code, libelle, frequence, heure_cible, photo_requise) VALUES
(1, 'etalonnage_thermometres',    'Étalonnage thermomètres',                    'ponctuel',      NULL,    0),
(1, 'releve_temp_enceintes_matin','Relevé températures enceintes — Matin',       'quotidien',     '08:00', 0),
(1, 'releve_temp_enceintes_soir', 'Relevé températures enceintes — Soir',        'quotidien',     '18:00', 0),
(1, 'action_corrective_temp',     'Action corrective température',               'evenementiel',  NULL,    0),
(1, 'pieges_rongeurs',            'Présence rongeurs sur pièges',                'hebdomadaire',  NULL,    0),
(1, 'nettoyage_pieges_oiseaux',   'Nettoyage pièges oiseaux',                    'hebdomadaire',  NULL,    0),
(1, 'temp_lave_vaisselle',        'Températures lave-vaisselle',                 'quotidien',     '12:00', 0),
(1, 'controle_huile_friture',     'Contrôle huile de friture',                   'evenementiel',  NULL,    0),
(1, 'suivi_temp_production',      'Suivi températures production/service',       'quotidien',     '12:00', 0),
(1, 'suivi_decongélation',        'Suivi décongélation',                         'evenementiel',  NULL,    0),
(1, 'suivi_congelation',          'Suivi congélation',                           'evenementiel',  NULL,    0),
(1, 'nettoyage_desinfection',     'Nettoyage et désinfection',                   'quotidien',     '19:00', 0),
(1, 'tiac',                       'TIAC — Toxi-infection alimentaire collective', 'exceptionnel',  NULL,    1);

-- Pièges rongeurs par défaut (boutique 1)
INSERT OR IGNORE INTO pieges (boutique_id, type, identifiant, localisation) VALUES
(1, 'rongeur', 'P1', 'Entrée laboratoire'),
(1, 'rongeur', 'P2', 'Fond laboratoire'),
(1, 'oiseau',  'P3', 'Entrée boutique');

"""

# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------

@asynccontextmanager
async def get_db():
    """Context manager : ouvre et ferme proprement la connexion SQLite."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        yield db


async def init_db() -> None:
    """Crée le schéma et insère les données initiales si la base est vide."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.executescript(SCHEMA_SQL)
        await db.executescript(SEED_SQL)
        await db.executescript(SEED_SQL_PHASE2)
        # Migration : refonte schéma réception (tables vides en prod, recréation si ancien schéma)
        cur = await db.execute("PRAGMA table_info(receptions)")
        cols_rec = {row[1] for row in await cur.fetchall()}
        if "personnel_id" not in cols_rec:
            logger.info("Migration : refonte tables receptions / reception_lignes")
            await db.execute("DROP TABLE IF EXISTS reception_lignes")
            await db.execute("DROP TABLE IF EXISTS receptions")
            await db.executescript("""
CREATE TABLE IF NOT EXISTS receptions (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    personnel_id             INTEGER NOT NULL,
    date_reception           DATE    DEFAULT CURRENT_DATE,
    heure_reception          TEXT    NOT NULL,
    temperature_camion       REAL,
    proprete_camion          TEXT    DEFAULT 'satisfaisant',
    camion_conforme          INTEGER DEFAULT 1,
    fournisseur_principal_id INTEGER,
    photo_bl_filename        TEXT,
    commentaire              TEXT,
    conformite_globale       TEXT    DEFAULT 'conforme',
    livraison_refusee        INTEGER DEFAULT 0,
    information_ddpp         INTEGER DEFAULT 0,
    commentaire_nc           TEXT,
    created_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (personnel_id)             REFERENCES personnel(id),
    FOREIGN KEY (fournisseur_principal_id) REFERENCES fournisseurs(id)
);
CREATE TABLE IF NOT EXISTS reception_lignes (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    reception_id              INTEGER NOT NULL,
    produit_id                INTEGER NOT NULL,
    fournisseur_id            INTEGER,
    numero_lot                TEXT,
    dlc                       DATE,
    dluo                      DATE,
    origine                   TEXT    DEFAULT 'France',
    poids_kg                  REAL,
    temperature_reception     REAL,
    temperature_conforme      INTEGER,
    couleur_conforme          INTEGER DEFAULT 1,
    couleur_observation       TEXT,
    consistance_conforme      INTEGER DEFAULT 1,
    consistance_observation   TEXT,
    exsudat_conforme          INTEGER DEFAULT 1,
    exsudat_observation       TEXT,
    odeur_conforme            INTEGER DEFAULT 1,
    odeur_observation         TEXT,
    ph_valeur                 REAL,
    ph_conforme               INTEGER,
    conforme                  INTEGER DEFAULT 1,
    created_at                DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reception_id)   REFERENCES receptions(id),
    FOREIGN KEY (produit_id)     REFERENCES produits(id),
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
);
""")

        # Migration : table fiches_incident (ajout v2.1)
        cur_fi = await db.execute("PRAGMA table_info(fiches_incident)")
        if not await cur_fi.fetchone():
            await db.execute("""
CREATE TABLE IF NOT EXISTS fiches_incident (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    reception_id               INTEGER NOT NULL,
    reception_ligne_id         INTEGER,
    date_incident              DATE    DEFAULT CURRENT_DATE,
    heure_incident             TEXT    NOT NULL,
    fournisseur_id             INTEGER,
    produit_id                 INTEGER,
    numero_lot                 TEXT,
    nature_probleme            TEXT    NOT NULL,
    description                TEXT,
    action_immediate           TEXT    NOT NULL,
    livreur_present            INTEGER NOT NULL DEFAULT 0,
    signature_livreur_filename TEXT,
    etiquette_reprise_imprimee INTEGER DEFAULT 0,
    action_corrective          TEXT,
    suivi                      TEXT,
    statut                     TEXT    DEFAULT 'ouverte',
    cloturee_par               INTEGER,
    cloturee_le                DATETIME,
    created_at                 DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reception_id)       REFERENCES receptions(id),
    FOREIGN KEY (reception_ligne_id) REFERENCES reception_lignes(id),
    FOREIGN KEY (fournisseur_id)     REFERENCES fournisseurs(id),
    FOREIGN KEY (produit_id)         REFERENCES produits(id),
    FOREIGN KEY (cloturee_par)       REFERENCES personnel(id)
)
""")

        # Autres migrations incrémentales
        migrations = [
            # reception_lignes : nouveaux champs v2.2
            "ALTER TABLE reception_lignes ADD COLUMN temperature_coeur REAL",
            "ALTER TABLE reception_lignes ADD COLUMN lot_interne INTEGER DEFAULT 0",
            # fiches_incident : temperature_coeur + commentaire (remplace suivi)
            "ALTER TABLE fiches_incident ADD COLUMN temperature_coeur REAL",
            "ALTER TABLE fiches_incident ADD COLUMN commentaire TEXT",
            # Table compteur lots internes
            """CREATE TABLE IF NOT EXISTS lot_interne_counters (
                code_unique TEXT NOT NULL,
                date_jjmmyy TEXT NOT NULL,
                counter     INTEGER DEFAULT 0,
                PRIMARY KEY (code_unique, date_jjmmyy)
            )""",
            # produits : tolerance temperature (v2.3)
            "ALTER TABLE produits ADD COLUMN temperature_tolerance REAL DEFAULT 2.0",
            # fiches_incident : fournisseur_nom pour fournisseurs sans ID (v2.4)
            "ALTER TABLE fiches_incident ADD COLUMN fournisseur_nom TEXT",
            # produits : type_produit pour distinguer brut / fini (v2.6)
            "ALTER TABLE produits ADD COLUMN type_produit TEXT NOT NULL DEFAULT 'brut'",
            # fabrications : dlc_finale calculée selon HACCP (v2.7)
            "ALTER TABLE fabrications ADD COLUMN dlc_finale TEXT",
            # fabrications : poids fabriqué en kg pour traçabilité légale (v2.9)
            "ALTER TABLE fabrications ADD COLUMN poids_fabrique REAL",
            # receptions : fournisseur_nom pour saisies manuelles sans ID (v2.8)
            "ALTER TABLE receptions ADD COLUMN fournisseur_nom TEXT",
            # reception_lignes : fournisseur_nom pour saisies manuelles sans ID (v2.8)
            "ALTER TABLE reception_lignes ADD COLUMN fournisseur_nom TEXT",
        ]
        for sql in migrations:
            try:
                await db.execute(sql)
            except Exception:
                pass

        # Migration v2.4 : rendre fournisseur_id nullable dans fiches_incident
        # (nécessaire quand le fournisseur est saisi manuellement sans ID BDD)
        try:
            cur_col = await db.execute("PRAGMA table_info(fiches_incident)")
            cols = await cur_col.fetchall()
            fourn_col = next((c for c in cols if c[1] == 'fournisseur_id'), None)
            # col[3] = notnull flag (1 = NOT NULL)
            if fourn_col and fourn_col[3] == 1:
                await db.execute("PRAGMA foreign_keys = OFF")
                await db.execute("DROP TABLE IF EXISTS fiches_incident_new")
                await db.execute("""
                    CREATE TABLE fiches_incident_new (
                        id                         INTEGER PRIMARY KEY AUTOINCREMENT,
                        reception_id               INTEGER NOT NULL,
                        reception_ligne_id         INTEGER,
                        date_incident              DATE    DEFAULT CURRENT_DATE,
                        heure_incident             TEXT    NOT NULL,
                        fournisseur_id             INTEGER,
                        fournisseur_nom            TEXT,
                        produit_id                 INTEGER,
                        numero_lot                 TEXT,
                        nature_probleme            TEXT    NOT NULL,
                        description                TEXT,
                        action_immediate           TEXT    NOT NULL,
                        livreur_present            INTEGER NOT NULL DEFAULT 0,
                        signature_livreur_filename TEXT,
                        etiquette_reprise_imprimee INTEGER DEFAULT 0,
                        action_corrective          TEXT,
                        suivi                      TEXT,
                        commentaire                TEXT,
                        temperature_coeur          REAL,
                        statut                     TEXT    DEFAULT 'ouverte',
                        cloturee_par               INTEGER,
                        cloturee_le                DATETIME,
                        created_at                 DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Déterminer les colonnes existantes pour le SELECT
                has_fourn_nom = any(c[1] == 'fournisseur_nom' for c in cols)
                has_commentaire = any(c[1] == 'commentaire' for c in cols)
                has_temp_coeur = any(c[1] == 'temperature_coeur' for c in cols)
                fourn_nom_sel = "fournisseur_nom" if has_fourn_nom else "NULL"
                commentaire_sel = "commentaire" if has_commentaire else "NULL"
                temp_coeur_sel = "temperature_coeur" if has_temp_coeur else "NULL"
                await db.execute(f"""
                    INSERT INTO fiches_incident_new
                        SELECT id, reception_id, reception_ligne_id, date_incident,
                               heure_incident, fournisseur_id,
                               {fourn_nom_sel},
                               produit_id, numero_lot, nature_probleme, description,
                               action_immediate, livreur_present,
                               signature_livreur_filename, etiquette_reprise_imprimee,
                               action_corrective, suivi, {commentaire_sel}, {temp_coeur_sel},
                               statut, cloturee_par, cloturee_le, created_at
                        FROM fiches_incident
                """)
                await db.execute("DROP TABLE fiches_incident")
                await db.execute("ALTER TABLE fiches_incident_new RENAME TO fiches_incident")
                await db.execute("PRAGMA foreign_keys = ON")
                logger.info("Migration v2.4 : fournisseur_id rendu nullable dans fiches_incident")
        except Exception as e:
            logger.warning("Migration v2.4 fiches_incident : %s", e)
            await db.execute("PRAGMA foreign_keys = ON")

        # Migration v2.5 : rendre produit_id nullable dans fiches_incident
        # (nécessaire pour les fiches de refus livraison camion, sans produit spécifique)
        try:
            cur_col2 = await db.execute("PRAGMA table_info(fiches_incident)")
            cols2 = await cur_col2.fetchall()
            prod_col = next((c for c in cols2 if c[1] == 'produit_id'), None)
            if prod_col and prod_col[3] == 1:  # notnull == 1
                await db.execute("PRAGMA foreign_keys = OFF")
                await db.execute("DROP TABLE IF EXISTS fiches_incident_new")
                await db.execute("""
                    CREATE TABLE fiches_incident_new (
                        id                         INTEGER PRIMARY KEY AUTOINCREMENT,
                        reception_id               INTEGER NOT NULL,
                        reception_ligne_id         INTEGER,
                        date_incident              DATE    DEFAULT CURRENT_DATE,
                        heure_incident             TEXT    NOT NULL,
                        fournisseur_id             INTEGER,
                        fournisseur_nom            TEXT,
                        produit_id                 INTEGER,
                        numero_lot                 TEXT,
                        nature_probleme            TEXT    NOT NULL,
                        description                TEXT,
                        action_immediate           TEXT    NOT NULL,
                        livreur_present            INTEGER NOT NULL DEFAULT 0,
                        signature_livreur_filename TEXT,
                        etiquette_reprise_imprimee INTEGER DEFAULT 0,
                        action_corrective          TEXT,
                        suivi                      TEXT,
                        commentaire                TEXT,
                        temperature_coeur          REAL,
                        statut                     TEXT    DEFAULT 'ouverte',
                        cloturee_par               INTEGER,
                        cloturee_le                DATETIME,
                        created_at                 DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                has_fourn_nom2  = any(c[1] == 'fournisseur_nom'   for c in cols2)
                has_commentaire2 = any(c[1] == 'commentaire'      for c in cols2)
                has_temp_coeur2  = any(c[1] == 'temperature_coeur' for c in cols2)
                fourn_nom_sel2  = "fournisseur_nom"   if has_fourn_nom2  else "NULL"
                commentaire_sel2 = "commentaire"      if has_commentaire2 else "NULL"
                temp_coeur_sel2  = "temperature_coeur" if has_temp_coeur2  else "NULL"
                await db.execute(f"""
                    INSERT INTO fiches_incident_new
                        SELECT id, reception_id, reception_ligne_id, date_incident,
                               heure_incident, fournisseur_id,
                               {fourn_nom_sel2},
                               produit_id, numero_lot, nature_probleme, description,
                               action_immediate, livreur_present,
                               signature_livreur_filename, etiquette_reprise_imprimee,
                               action_corrective, suivi, {commentaire_sel2}, {temp_coeur_sel2},
                               statut, cloturee_par, cloturee_le, created_at
                        FROM fiches_incident
                """)
                await db.execute("DROP TABLE fiches_incident")
                await db.execute("ALTER TABLE fiches_incident_new RENAME TO fiches_incident")
                await db.execute("PRAGMA foreign_keys = ON")
                logger.info("Migration v2.5 : produit_id rendu nullable dans fiches_incident")
        except Exception as e:
            logger.warning("Migration v2.5 fiches_incident : %s", e)
            await db.execute("PRAGMA foreign_keys = ON")

        # Appliquer les tolérances correctes via CASE WHEN (robuste, toujours exécuté)
        try:
            await db.execute("""
                UPDATE produits SET temperature_tolerance = CASE
                    WHEN temperature_conservation LIKE '%+4°C%' OR temperature_conservation LIKE '% 4°C%' THEN 5.0
                    WHEN temperature_conservation LIKE '%+3°C%' OR temperature_conservation LIKE '% 3°C%' THEN 4.0
                    WHEN temperature_conservation LIKE '%+7°C%' OR temperature_conservation LIKE '% 7°C%' THEN 8.0
                    ELSE COALESCE(temperature_tolerance, 2.0)
                END
            """)
            logger.info("Tolérances temperature mises à jour")
        except Exception as e:
            logger.warning("Erreur lors de l'application des tolérances: %s", e)

        await db.commit()
    logger.info("Base de données initialisée : %s", DB_PATH)


# ---------------------------------------------------------------------------
# Relevés
# ---------------------------------------------------------------------------

async def insert_releve(
    db: aiosqlite.Connection,
    enceinte_id: int,
    temperature: float,
    humidite: Optional[float],
    batterie: Optional[int],
    qualite_signal: Optional[int],
    horodatage: Optional[datetime] = None,
) -> int:
    ts = (horodatage or datetime.now(timezone.utc)).isoformat()
    cursor = await db.execute(
        """
        INSERT INTO releves (enceinte_id, temperature, humidite, batterie, qualite_signal, horodatage)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (enceinte_id, temperature, humidite, batterie, qualite_signal, ts),
    )
    await db.commit()
    return cursor.lastrowid


async def get_latest_releve(db: aiosqlite.Connection, enceinte_id: int) -> Optional[dict]:
    cursor = await db.execute(
        """
        SELECT * FROM releves
        WHERE enceinte_id = ?
        ORDER BY horodatage DESC
        LIMIT 1
        """,
        (enceinte_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_releves(
    db: aiosqlite.Connection,
    enceinte_id: int,
    depuis: datetime,
    jusqu_a: Optional[datetime] = None,
) -> list[dict]:
    jusqu_a = jusqu_a or datetime.now(timezone.utc)
    cursor = await db.execute(
        """
        SELECT * FROM releves
        WHERE enceinte_id = ?
          AND horodatage >= ?
          AND horodatage <= ?
        ORDER BY horodatage ASC
        """,
        (enceinte_id, depuis.isoformat(), jusqu_a.isoformat()),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_stats_releves(
    db: aiosqlite.Connection,
    enceinte_id: int,
    depuis: datetime,
    jusqu_a: Optional[datetime] = None,
) -> dict:
    """Min / max / moyenne sur une période."""
    jusqu_a = jusqu_a or datetime.now(timezone.utc)
    cursor = await db.execute(
        """
        SELECT
            MIN(temperature) AS temp_min,
            MAX(temperature) AS temp_max,
            AVG(temperature) AS temp_moy,
            MIN(humidite)    AS hum_min,
            MAX(humidite)    AS hum_max,
            AVG(humidite)    AS hum_moy,
            COUNT(*)         AS nb_releves
        FROM releves
        WHERE enceinte_id = ?
          AND horodatage >= ?
          AND horodatage <= ?
        """,
        (enceinte_id, depuis.isoformat(), jusqu_a.isoformat()),
    )
    row = await cursor.fetchone()
    return dict(row) if row else {}


# ---------------------------------------------------------------------------
# Enceintes
# ---------------------------------------------------------------------------

async def get_enceintes(db: aiosqlite.Connection, boutique_id: int) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM enceintes WHERE boutique_id = ? AND actif = 1",
        (boutique_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_enceinte(db: aiosqlite.Connection, enceinte_id: int) -> Optional[dict]:
    cursor = await db.execute(
        "SELECT * FROM enceintes WHERE id = ?", (enceinte_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_enceinte_by_zigbee_id(
    db: aiosqlite.Connection, zigbee_id: str
) -> Optional[dict]:
    cursor = await db.execute(
        "SELECT * FROM enceintes WHERE sonde_zigbee_id = ? AND actif = 1",
        (zigbee_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def create_enceinte(db: aiosqlite.Connection, data: dict) -> int:
    cursor = await db.execute(
        """
        INSERT INTO enceintes
            (boutique_id, nom, type, sonde_zigbee_id,
             seuil_temp_min, seuil_temp_max, seuil_hum_max, delai_alerte_minutes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["boutique_id"],
            data["nom"],
            data["type"],
            data.get("sonde_zigbee_id"),
            data.get("seuil_temp_min", 0.0),
            data.get("seuil_temp_max", 4.0),
            data.get("seuil_hum_max", 90.0),
            data.get("delai_alerte_minutes", 5),
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def update_enceinte(
    db: aiosqlite.Connection, enceinte_id: int, data: dict
) -> bool:
    fields = {
        k: v
        for k, v in data.items()
        if k in (
            "nom", "type", "sonde_zigbee_id",
            "seuil_temp_min", "seuil_temp_max", "seuil_hum_max",
            "delai_alerte_minutes", "actif",
        )
    }
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [enceinte_id]
    await db.execute(f"UPDATE enceintes SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return True


async def delete_enceinte(db: aiosqlite.Connection, enceinte_id: int) -> bool:
    """Supprime une enceinte et toutes ses données associées."""
    cur = await db.execute("SELECT id FROM enceintes WHERE id = ?", (enceinte_id,))
    if not await cur.fetchone():
        return False
    await db.execute("DELETE FROM releves WHERE enceinte_id = ?", (enceinte_id,))
    await db.execute("DELETE FROM alertes WHERE enceinte_id = ?", (enceinte_id,))
    await db.execute("DELETE FROM enceintes WHERE id = ?", (enceinte_id,))
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Boutiques
# ---------------------------------------------------------------------------

async def get_boutiques(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute("SELECT * FROM boutiques")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_boutique(db: aiosqlite.Connection, boutique_id: int) -> Optional[dict]:
    cursor = await db.execute(
        "SELECT * FROM boutiques WHERE id = ?", (boutique_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Alertes
# ---------------------------------------------------------------------------

async def get_alerte_en_cours(
    db: aiosqlite.Connection, enceinte_id: int, type_alerte: str
) -> Optional[dict]:
    """Retourne l'alerte ouverte (fin IS NULL) d'un type donné pour une enceinte."""
    cursor = await db.execute(
        """
        SELECT * FROM alertes
        WHERE enceinte_id = ? AND type = ? AND fin IS NULL
        ORDER BY debut DESC
        LIMIT 1
        """,
        (enceinte_id, type_alerte),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def ouvrir_alerte(
    db: aiosqlite.Connection,
    enceinte_id: int,
    type_alerte: str,
    valeur: float,
    seuil: float,
    debut: Optional[datetime] = None,
) -> int:
    ts = (debut or datetime.now(timezone.utc)).isoformat()
    cursor = await db.execute(
        """
        INSERT INTO alertes (enceinte_id, type, valeur, seuil, debut)
        VALUES (?, ?, ?, ?, ?)
        """,
        (enceinte_id, type_alerte, valeur, seuil, ts),
    )
    await db.commit()
    return cursor.lastrowid


async def fermer_alerte(
    db: aiosqlite.Connection, alerte_id: int, fin: Optional[datetime] = None
) -> None:
    ts = (fin or datetime.now(timezone.utc)).isoformat()
    await db.execute(
        "UPDATE alertes SET fin = ? WHERE id = ?", (ts, alerte_id)
    )
    await db.commit()


async def marquer_alerte_notifiee(
    db: aiosqlite.Connection, alerte_id: int
) -> None:
    await db.execute(
        "UPDATE alertes SET notifie = 1 WHERE id = ?", (alerte_id,)
    )
    await db.commit()


async def get_alertes_en_cours(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute(
        """
        SELECT a.*, e.nom AS enceinte_nom, b.nom AS boutique_nom
        FROM alertes a
        JOIN enceintes e ON e.id = a.enceinte_id
        JOIN boutiques b ON b.id = e.boutique_id
        WHERE a.fin IS NULL
        ORDER BY a.debut DESC
        """
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_alertes_enceinte(
    db: aiosqlite.Connection,
    enceinte_id: int,
    depuis: Optional[datetime] = None,
) -> list[dict]:
    depuis = depuis or (datetime.now(timezone.utc) - timedelta(days=30))
    cursor = await db.execute(
        """
        SELECT * FROM alertes
        WHERE enceinte_id = ? AND debut >= ?
        ORDER BY debut DESC
        """,
        (enceinte_id, depuis.isoformat()),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_duree_depassements(
    db: aiosqlite.Connection,
    enceinte_id: int,
    depuis: datetime,
    jusqu_a: Optional[datetime] = None,
) -> int:
    """Retourne la durée cumulée des dépassements en secondes sur une période."""
    jusqu_a = jusqu_a or datetime.now(timezone.utc)
    cursor = await db.execute(
        """
        SELECT
            SUM(
                CAST(
                    (julianday(COALESCE(fin, ?)) - julianday(debut)) * 86400
                AS INTEGER)
            ) AS duree_secondes
        FROM alertes
        WHERE enceinte_id = ?
          AND type IN ('temperature_haute', 'temperature_basse')
          AND debut <= ?
          AND (fin IS NULL OR fin >= ?)
        """,
        (jusqu_a.isoformat(), enceinte_id, jusqu_a.isoformat(), depuis.isoformat()),
    )
    row = await cursor.fetchone()
    return int(row["duree_secondes"] or 0)


# ---------------------------------------------------------------------------
# Destinataires
# ---------------------------------------------------------------------------

async def get_destinataires(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM destinataires WHERE actif = 1"
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def create_destinataire(db: aiosqlite.Connection, data: dict) -> int:
    cursor = await db.execute(
        "INSERT INTO destinataires (nom, email, telephone) VALUES (?, ?, ?)",
        (data["nom"], data.get("email"), data.get("telephone")),
    )
    await db.commit()
    return cursor.lastrowid


# ---------------------------------------------------------------------------
# Rapports
# ---------------------------------------------------------------------------

async def create_rapport(db: aiosqlite.Connection, data: dict) -> int:
    cursor = await db.execute(
        """
        INSERT INTO rapports (boutique_id, type, date_debut, date_fin, conforme, fichier_path, sha256)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["boutique_id"],
            data["type"],
            data["date_debut"],
            data["date_fin"],
            data.get("conforme"),
            data.get("fichier_path"),
            data.get("sha256"),
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def get_rapport(db: aiosqlite.Connection, rapport_id: int) -> Optional[dict]:
    cursor = await db.execute(
        "SELECT * FROM rapports WHERE id = ?", (rapport_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Dashboard — données agrégées
# ---------------------------------------------------------------------------

async def get_dashboard_boutique(db: aiosqlite.Connection, boutique_id: int) -> dict:
    """
    Retourne en une seule passe toutes les données nécessaires au dashboard :
    dernière mesure + statut + alerte en cours pour chaque enceinte.
    """
    boutique = await get_boutique(db, boutique_id)
    if not boutique:
        return {}

    enceintes = await get_enceintes(db, boutique_id)
    result_enceintes = []

    for enc in enceintes:
        eid = enc["id"]
        dernier = await get_latest_releve(db, eid)

        # Statut de l'enceinte
        statut = "inconnu"
        if dernier:
            t = dernier["temperature"]
            if t < enc["seuil_temp_min"] or t > enc["seuil_temp_max"]:
                statut = "alerte"
            elif t < enc["seuil_temp_min"] + 0.5 or t > enc["seuil_temp_max"] - 0.5:
                statut = "attention"
            else:
                statut = "ok"

            # Vérifier si la dernière mesure est trop ancienne (> 15 min)
            try:
                last_ts = datetime.fromisoformat(dernier["horodatage"].replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - last_ts).total_seconds()
                if age > 900:
                    statut = "hors_ligne"
            except Exception:
                pass

        # Alerte en cours
        alerte = None
        for type_alerte in ("temperature_haute", "temperature_basse", "perte_signal", "batterie_faible"):
            a = await get_alerte_en_cours(db, eid, type_alerte)
            if a:
                alerte = {
                    "type": a["type"],
                    "debut": a["debut"],
                    "valeur": a["valeur"],
                    "seuil": a["seuil"],
                }
                break

        result_enceintes.append(
            {
                "id": eid,
                "nom": enc["nom"],
                "type": enc["type"],
                "temperature_actuelle": dernier["temperature"] if dernier else None,
                "humidite_actuelle": dernier["humidite"] if dernier else None,
                "batterie_sonde": dernier["batterie"] if dernier else None,
                "derniere_mesure": dernier["horodatage"] if dernier else None,
                "seuil_min": enc["seuil_temp_min"],
                "seuil_max": enc["seuil_temp_max"],
                "statut": statut,
                "alerte_en_cours": alerte,
            }
        )

    statut_global = "ok"
    if any(e["statut"] == "alerte" for e in result_enceintes):
        statut_global = "alerte"
    elif any(e["statut"] in ("attention", "hors_ligne") for e in result_enceintes):
        statut_global = "attention"

    return {
        "boutique": {"id": boutique_id, "nom": boutique["nom"], "statut": statut_global},
        "enceintes": result_enceintes,
    }


# ---------------------------------------------------------------------------
# Export CSV + Purge (rétention)
# ---------------------------------------------------------------------------

CSV_EXPORT_DIR = Path(__file__).parent.parent / "data" / "exports"

# Relevés bruts gardés en base (le reste est exporté en CSV)
RETENTION_RELEVES_JOURS = 30
# Alertes gardées en base
RETENTION_ALERTES_JOURS = 365 * 3


async def exporter_jour_csv(
    db: aiosqlite.Connection,
    enceinte_id: int,
    nom_enceinte: str,
    jour: datetime,
) -> Optional[Path]:
    """
    Exporte les relevés d'une enceinte pour un jour donné dans un fichier CSV.
    Retourne le chemin du fichier créé, ou None si aucun relevé.
    Nom du fichier : {nom_enceinte}_{YYYY-MM-DD}.csv
    """
    import csv

    debut = jour.replace(hour=0, minute=0, second=0, microsecond=0)
    fin   = debut + timedelta(days=1)

    cursor = await db.execute(
        """
        SELECT horodatage, temperature, humidite, batterie, qualite_signal
        FROM releves
        WHERE enceinte_id = ? AND horodatage >= ? AND horodatage < ?
        ORDER BY horodatage ASC
        """,
        (enceinte_id, debut.isoformat(), fin.isoformat()),
    )
    rows = await cursor.fetchall()
    if not rows:
        return None

    # Sanitize nom pour le filesystem (retire les caractères interdits)
    nom_safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in nom_enceinte)
    dossier = CSV_EXPORT_DIR / nom_safe
    dossier.mkdir(parents=True, exist_ok=True)

    fichier = dossier / f"{nom_safe}_{debut.strftime('%Y-%m-%d')}.csv"

    # Ne pas réécrire si le fichier existe déjà (idempotent)
    if fichier.exists():
        return fichier

    with fichier.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["horodatage", "temperature", "humidite", "batterie", "qualite_signal"])
        for row in rows:
            writer.writerow([row[0], row[1], row[2], row[3], row[4]])

    logger.info("📄 CSV exporté : %s (%d relevés)", fichier, len(rows))
    return fichier


async def purger_anciens_releves(db: aiosqlite.Connection) -> dict:
    """
    Applique la politique de rétention :
    - Relevés bruts > 30 jours : supprimés (après export CSV)
    - Alertes > 3 ans : supprimées
    Lance aussi VACUUM pour libérer l'espace sur la SD card.
    """
    now = datetime.now(timezone.utc)
    limite_releves = (now - timedelta(days=RETENTION_RELEVES_JOURS)).isoformat()
    limite_alertes = (now - timedelta(days=RETENTION_ALERTES_JOURS)).isoformat()

    cur_r = await db.execute(
        "DELETE FROM releves WHERE horodatage < ?", (limite_releves,)
    )
    cur_a = await db.execute(
        "DELETE FROM alertes WHERE created_at < ?", (limite_alertes,)
    )
    await db.commit()

    # VACUUM libère l'espace disque sur la SD (important sur Pi Zero)
    await db.execute("VACUUM")

    return {
        "releves_supprimes": cur_r.rowcount,
        "alertes_supprimees": cur_a.rowcount,
    }


# ===========================================================================
# PHASE 2 — Module DLC / Étiquettes
# ===========================================================================

# ---------------------------------------------------------------------------
# Produits
# ---------------------------------------------------------------------------

async def get_produits(
    db: aiosqlite.Connection,
    boutique_id: int,
    type_produit: Optional[str] = None,
) -> list[dict]:
    if type_produit:
        cursor = await db.execute(
            "SELECT * FROM produits WHERE boutique_id = ? AND actif = 1 AND type_produit = ? ORDER BY nom",
            (boutique_id, type_produit),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM produits WHERE boutique_id = ? AND actif = 1 ORDER BY nom",
            (boutique_id,),
        )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_produit(db: aiosqlite.Connection, produit_id: int) -> Optional[dict]:
    cursor = await db.execute("SELECT * FROM produits WHERE id = ?", (produit_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def create_produit(db: aiosqlite.Connection, data: dict) -> int:
    cursor = await db.execute(
        """
        INSERT INTO produits
            (boutique_id, nom, categorie, dlc_jours, temperature_conservation, format_etiquette)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data["boutique_id"],
            data["nom"],
            data["categorie"],
            data["dlc_jours"],
            data["temperature_conservation"],
            data.get("format_etiquette", "standard_60x40"),
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def update_produit(db: aiosqlite.Connection, produit_id: int, data: dict) -> bool:
    fields = {
        k: v for k, v in data.items()
        if k in ("nom", "categorie", "dlc_jours", "temperature_conservation", "format_etiquette", "actif")
    }
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [produit_id]
    await db.execute(f"UPDATE produits SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Règles DLC
# ---------------------------------------------------------------------------

async def get_regles_dlc(db: aiosqlite.Connection, boutique_id: int) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM regles_dlc WHERE boutique_id = ? ORDER BY categorie",
        (boutique_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def update_regle_dlc(
    db: aiosqlite.Connection, boutique_id: int, categorie: str, dlc_jours: int, note: Optional[str] = None
) -> None:
    await db.execute(
        """
        INSERT INTO regles_dlc (boutique_id, categorie, dlc_jours, note)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(boutique_id, categorie) DO UPDATE SET dlc_jours = excluded.dlc_jours, note = excluded.note
        """,
        (boutique_id, categorie, dlc_jours, note),
    )
    await db.commit()


def calculer_dlc(categorie: str, date_ref: "date", dlc_jours: int) -> "date":
    """
    Calcule la DLC à partir d'une date de référence et du nombre de jours.
    Pour 'produit_deconge', la règle J+3 est fixe et non modifiable.
    """
    from datetime import date as date_type, timedelta as td
    return date_ref + td(days=dlc_jours)


# ---------------------------------------------------------------------------
# Numérotation des lots internes
# ---------------------------------------------------------------------------

async def get_next_numero_lot(db: aiosqlite.Connection, boutique_id: int, jour: "date") -> str:
    """Génère le prochain numéro de lot MC-YYYYMMDD-XXXX pour le jour donné."""
    jour_str = jour.strftime("%Y%m%d")
    cursor = await db.execute(
        """
        SELECT COUNT(*) AS nb FROM etiquettes_generees
        WHERE boutique_id = ? AND lot_type = 'interne'
          AND date(imprime_at) = date(?)
        """,
        (boutique_id, jour.isoformat()),
    )
    row = await cursor.fetchone()
    nb = (row["nb"] if row else 0) + 1
    return f"MC-{jour_str}-{nb:04d}"


# ---------------------------------------------------------------------------
# Étiquettes générées
# ---------------------------------------------------------------------------

async def create_etiquette(db: aiosqlite.Connection, data: dict) -> int:
    cursor = await db.execute(
        """
        INSERT INTO etiquettes_generees
            (boutique_id, produit_id, produit_nom, type_date, date_etiquette,
             dlc, temperature_conservation, operateur, numero_lot, lot_type,
             info_complementaire, mode_impression)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["boutique_id"],
            data.get("produit_id"),
            data["produit_nom"],
            data["type_date"],
            data["date_etiquette"],
            data["dlc"],
            data.get("temperature_conservation"),
            data["operateur"],
            data["numero_lot"],
            data["lot_type"],
            data.get("info_complementaire"),
            data.get("mode_impression", "manuel"),
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def get_etiquettes(
    db: aiosqlite.Connection,
    boutique_id: int,
    depuis: Optional[datetime] = None,
    limit: int = 100,
) -> list[dict]:
    depuis = depuis or (datetime.now(timezone.utc) - timedelta(days=30))
    cursor = await db.execute(
        """
        SELECT * FROM etiquettes_generees
        WHERE boutique_id = ? AND imprime_at >= ?
        ORDER BY imprime_at DESC
        LIMIT ?
        """,
        (boutique_id, depuis.isoformat(), limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_alertes_dlc(
    db: aiosqlite.Connection, boutique_id: int, jours_seuil: int = 2
) -> list[dict]:
    """Retourne les étiquettes dont la DLC est dans les prochains `jours_seuil` jours."""
    from datetime import date
    aujourd_hui = date.today().isoformat()
    limite = (datetime.now(timezone.utc) + timedelta(days=jours_seuil)).date().isoformat()
    cursor = await db.execute(
        """
        SELECT * FROM etiquettes_generees
        WHERE boutique_id = ? AND dlc >= ? AND dlc <= ?
        ORDER BY dlc ASC
        """,
        (boutique_id, aujourd_hui, limite),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


# ===========================================================================
# PHASE 2 — Module Réception
# ===========================================================================

# ---------------------------------------------------------------------------
# Fournisseurs
# ---------------------------------------------------------------------------

async def get_fournisseurs(db: aiosqlite.Connection, boutique_id: int) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM fournisseurs WHERE boutique_id = ? AND actif = 1 ORDER BY nom",
        (boutique_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def create_fournisseur(db: aiosqlite.Connection, data: dict) -> int:
    cursor = await db.execute(
        "INSERT INTO fournisseurs (boutique_id, nom) VALUES (?, ?)",
        (data["boutique_id"], data["nom"]),
    )
    await db.commit()
    return cursor.lastrowid


async def update_fournisseur(db: aiosqlite.Connection, fournisseur_id: int, data: dict) -> bool:
    fields = {k: v for k, v in data.items() if k in ("nom", "actif")}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [fournisseur_id]
    await db.execute(f"UPDATE fournisseurs SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Réceptions
# ---------------------------------------------------------------------------

async def create_reception(db: aiosqlite.Connection, data: dict) -> int:
    """Crée une réception. data doit contenir personnel_id et heure_reception."""
    temp = data.get("temperature_camion")
    proprete = data.get("proprete_camion", "satisfaisant")
    # La température camion >= 2°C est un signal d'alerte, pas une NC en soi.
    # Seule la propreté non satisfaisante rend le camion non-conforme.
    camion_conforme = 0 if proprete == "non_satisfaisant" else 1
    date_reception = data.get("date_reception")  # format YYYY-MM-DD ou None → DEFAULT CURRENT_DATE

    if date_reception:
        cursor = await db.execute(
            """
            INSERT INTO receptions
                (personnel_id, date_reception, heure_reception, temperature_camion, proprete_camion,
                 camion_conforme, fournisseur_principal_id, fournisseur_nom, photo_bl_filename, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["personnel_id"],
                date_reception,
                data["heure_reception"],
                temp,
                proprete,
                camion_conforme,
                data.get("fournisseur_principal_id"),
                data.get("fournisseur_nom"),
                data.get("photo_bl_filename"),
                data.get("commentaire"),
            ),
        )
    else:
        cursor = await db.execute(
            """
            INSERT INTO receptions
                (personnel_id, heure_reception, temperature_camion, proprete_camion,
                 camion_conforme, fournisseur_principal_id, fournisseur_nom, photo_bl_filename, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["personnel_id"],
                data["heure_reception"],
                temp,
                proprete,
                camion_conforme,
                data.get("fournisseur_principal_id"),
                data.get("fournisseur_nom"),
                data.get("photo_bl_filename"),
                data.get("commentaire"),
            ),
        )
    await db.commit()
    return cursor.lastrowid


def parse_temperature_range(temp_str: Optional[str]) -> Optional[tuple]:
    """Parse '0°C à +4°C' → (0.0, 4.0). Retourne None si non parsable."""
    import re
    if not temp_str:
        return None
    nums = re.findall(r'[+\-]?\d+(?:\.\d+)?', temp_str)
    if len(nums) < 2:
        return None
    vals = [float(n) for n in nums]
    return (min(vals), max(vals))


def _calc_temperature_conforme(temp_recep: Optional[float], temp_conservation: Optional[str]) -> Optional[int]:
    """
    Calcule la conformité température selon les plages HACCP.
    Retourne : 1=Conforme, 0=NON CONFORME (trop chaud), 2=Attention température basse, None=non évalué
    Tolérance : borne_min - 1°C à borne_max + 1°C
    """
    if temp_recep is None:
        return None
    rng = parse_temperature_range(temp_conservation)
    if rng is None:
        return None
    borne_min, borne_max = rng
    tol_min = borne_min - 1.0
    tol_max = borne_max + 1.0
    if temp_recep >= tol_max:
        return 0   # NON CONFORME — trop chaud
    if temp_recep < tol_min:
        return 2   # Attention — température basse
    return 1       # Conforme


async def add_reception_ligne(db: aiosqlite.Connection, reception_id: int, data: dict) -> int:
    """Ajoute une ligne produit à une réception avec calcul automatique de conformité."""
    # Récupérer la réception pour savoir si le camion était conforme
    cur = await db.execute(
        "SELECT temperature_camion FROM receptions WHERE id = ?", (reception_id,)
    )
    rec_row = await cur.fetchone()
    temp_camion = rec_row["temperature_camion"] if rec_row else None

    # Récupérer temperature_conservation du produit
    cur2 = await db.execute(
        "SELECT temperature_conservation FROM produits WHERE id = ?", (data["produit_id"],)
    )
    prod_row = await cur2.fetchone()
    temp_conservation = prod_row["temperature_conservation"] if prod_row else None

    # Calculer temperature_conforme selon la logique de tolérance HACCP
    temp_recep = data.get("temperature_reception")
    temperature_conforme = _calc_temperature_conforme(temp_recep, temp_conservation)

    # Calculer ph_conforme
    ph_valeur = data.get("ph_valeur")
    ph_conforme: Optional[int] = None
    if ph_valeur is not None:
        ph_conforme = 1 if 5.5 <= ph_valeur <= 5.7 else 0

    # Conformité globale ligne
    couleur_conforme     = int(data.get("couleur_conforme",     1))
    consistance_conforme = int(data.get("consistance_conforme", 1))
    exsudat_conforme     = int(data.get("exsudat_conforme",     1))
    odeur_conforme       = int(data.get("odeur_conforme",       1))

    conforme = 1
    for flag in (temperature_conforme, ph_conforme,
                 couleur_conforme, consistance_conforme,
                 exsudat_conforme, odeur_conforme):
        if flag is not None and flag == 0:
            conforme = 0
            break

    cursor = await db.execute(
        """
        INSERT INTO reception_lignes
            (reception_id, produit_id, fournisseur_id, fournisseur_nom, numero_lot, lot_interne, dlc, dluo,
             origine, poids_kg, temperature_reception, temperature_conforme,
             temperature_coeur,
             couleur_conforme, couleur_observation,
             consistance_conforme, consistance_observation,
             exsudat_conforme, exsudat_observation,
             odeur_conforme, odeur_observation,
             ph_valeur, ph_conforme, conforme)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reception_id,
            data["produit_id"],
            data.get("fournisseur_id"),
            data.get("fournisseur_nom"),
            data.get("numero_lot"),
            int(data.get("lot_interne", 0)),
            data.get("dlc"),
            data.get("dluo"),
            data.get("origine", "France"),
            data.get("poids_kg"),
            temp_recep,
            temperature_conforme,
            data.get("temperature_coeur"),
            couleur_conforme,
            data.get("couleur_observation"),
            consistance_conforme,
            data.get("consistance_observation"),
            exsudat_conforme,
            data.get("exsudat_observation"),
            odeur_conforme,
            data.get("odeur_observation"),
            ph_valeur,
            ph_conforme,
            conforme,
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def cloturer_reception(
    db: aiosqlite.Connection,
    reception_id: int,
    livraison_refusee: bool = False,
    information_ddpp: bool = False,
    commentaire_nc: Optional[str] = None,
    coeur_conformes: list = None,
    coeur_temperatures: dict = None,
) -> Optional[dict]:
    """Clôture une réception : calcule conformite_globale depuis les lignes."""
    # Persister les températures à cœur mesurées
    if coeur_temperatures:
        for ligne_id, temp in coeur_temperatures.items():
            await db.execute(
                "UPDATE reception_lignes SET temperature_coeur = ? WHERE id = ? AND reception_id = ?",
                (float(temp), int(ligne_id), reception_id),
            )

    # Mettre à jour les lignes conformes après contrôle à cœur
    if coeur_conformes:
        for ligne_id in coeur_conformes:
            await db.execute(
                "UPDATE reception_lignes SET conforme = 1 WHERE id = ? AND reception_id = ?",
                (ligne_id, reception_id),
            )

    # Vérifier s'il y a des lignes non conformes
    cur = await db.execute(
        "SELECT COUNT(*) FROM reception_lignes WHERE reception_id = ? AND conforme = 0",
        (reception_id,),
    )
    row = await cur.fetchone()
    nb_nc = row[0] if row else 0
    conformite_globale = "non_conforme" if nb_nc > 0 else "conforme"

    await db.execute(
        """
        UPDATE receptions
        SET conformite_globale = ?, livraison_refusee = ?,
            information_ddpp = ?, commentaire_nc = ?
        WHERE id = ?
        """,
        (conformite_globale, int(livraison_refusee),
         int(information_ddpp), commentaire_nc, reception_id),
    )
    await db.commit()
    return await get_reception(db, reception_id)


async def generer_lot_interne(db: aiosqlite.Connection, code_unique: str) -> str:
    """Génère et retourne un numéro de lot interne unique : {code_unique}-{JJMMYY}-{XXX}."""
    from datetime import date
    today = date.today()
    date_jjmmyy = today.strftime("%d%m%y")

    # Incrémenter le compteur atomiquement
    await db.execute(
        """
        INSERT INTO lot_interne_counters (code_unique, date_jjmmyy, counter)
        VALUES (?, ?, 1)
        ON CONFLICT(code_unique, date_jjmmyy) DO UPDATE SET counter = counter + 1
        """,
        (code_unique, date_jjmmyy),
    )
    await db.commit()

    cur = await db.execute(
        "SELECT counter FROM lot_interne_counters WHERE code_unique = ? AND date_jjmmyy = ?",
        (code_unique, date_jjmmyy),
    )
    row = await cur.fetchone()
    counter = row[0] if row else 1
    return f"{code_unique}-{date_jjmmyy}-{counter:03d}"


async def update_reception_ligne(
    db: aiosqlite.Connection,
    ligne_id: int,
    data: dict,
) -> Optional[dict]:
    """Met à jour une ligne de réception et recalcule la conformité."""
    # Récupérer la réception associée pour avoir la temp camion
    cur = await db.execute(
        "SELECT reception_id, produit_id FROM reception_lignes WHERE id = ?", (ligne_id,)
    )
    row = await cur.fetchone()
    if not row:
        return None
    reception_id = row["reception_id"]
    produit_id = data.get("produit_id", row["produit_id"])

    cur2 = await db.execute(
        "SELECT temperature_camion FROM receptions WHERE id = ?", (reception_id,)
    )
    rec_row = await cur2.fetchone()
    temp_camion = rec_row["temperature_camion"] if rec_row else None

    cur3 = await db.execute(
        "SELECT temperature_conservation FROM produits WHERE id = ?", (produit_id,)
    )
    prod_row = await cur3.fetchone()
    temp_conservation = prod_row["temperature_conservation"] if prod_row else None

    # Recalculer temperature_conforme selon la logique de tolérance HACCP
    temp_recep = data.get("temperature_reception")
    temperature_conforme = _calc_temperature_conforme(temp_recep, temp_conservation)

    # pH
    ph_valeur = data.get("ph_valeur")
    ph_conforme: Optional[int] = None
    if ph_valeur is not None:
        ph_conforme = 1 if 5.5 <= ph_valeur <= 5.7 else 0

    couleur_conforme     = int(data.get("couleur_conforme",     1))
    consistance_conforme = int(data.get("consistance_conforme", 1))
    exsudat_conforme     = int(data.get("exsudat_conforme",     1))
    odeur_conforme       = int(data.get("odeur_conforme",       1))

    conforme = 1
    for flag in (temperature_conforme, ph_conforme,
                 couleur_conforme, consistance_conforme,
                 exsudat_conforme, odeur_conforme):
        if flag is not None and flag == 0:
            conforme = 0
            break

    await db.execute(
        """
        UPDATE reception_lignes SET
            produit_id = ?, fournisseur_id = ?, numero_lot = ?, lot_interne = ?,
            dlc = ?, dluo = ?, origine = ?, poids_kg = ?,
            temperature_reception = ?, temperature_conforme = ?,
            temperature_coeur = ?,
            couleur_conforme = ?, couleur_observation = ?,
            consistance_conforme = ?, consistance_observation = ?,
            exsudat_conforme = ?, exsudat_observation = ?,
            odeur_conforme = ?, odeur_observation = ?,
            ph_valeur = ?, ph_conforme = ?, conforme = ?
        WHERE id = ?
        """,
        (
            produit_id,
            data.get("fournisseur_id"),
            data.get("numero_lot"),
            int(data.get("lot_interne", 0)),
            data.get("dlc"),
            data.get("dluo"),
            data.get("origine", "France"),
            data.get("poids_kg"),
            temp_recep,
            temperature_conforme,
            data.get("temperature_coeur"),
            couleur_conforme,
            data.get("couleur_observation"),
            consistance_conforme,
            data.get("consistance_observation"),
            exsudat_conforme,
            data.get("exsudat_observation"),
            odeur_conforme,
            data.get("odeur_observation"),
            ph_valeur,
            ph_conforme,
            conforme,
            ligne_id,
        ),
    )
    await db.commit()

    cur4 = await db.execute(
        "SELECT * FROM reception_lignes WHERE id = ?", (ligne_id,)
    )
    updated = await cur4.fetchone()
    return dict(updated) if updated else None


async def get_receptions(
    db: aiosqlite.Connection,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    fournisseur_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    conditions = []
    params: list = []

    if date_debut:
        conditions.append("r.date_reception >= ?")
        params.append(date_debut)
    if date_fin:
        conditions.append("r.date_reception <= ?")
        params.append(date_fin)
    if fournisseur_id is not None:
        conditions.append("r.fournisseur_principal_id = ?")
        params.append(fournisseur_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    cursor = await db.execute(
        f"""
        SELECT
            r.*,
            p.prenom            AS personnel_prenom,
            COALESCE(f.nom, r.fournisseur_nom) AS fournisseur_nom,
            COUNT(rl.id)        AS nb_lignes,
            SUM(CASE WHEN rl.conforme = 0 THEN 1 ELSE 0 END) AS nb_nc
        FROM receptions r
        LEFT JOIN personnel         p  ON p.id  = r.personnel_id
        LEFT JOIN fournisseurs      f  ON f.id  = r.fournisseur_principal_id
        LEFT JOIN reception_lignes  rl ON rl.reception_id = r.id
        {where}
        GROUP BY r.id
        ORDER BY r.created_at DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_reception(db: aiosqlite.Connection, reception_id: int) -> Optional[dict]:
    cursor = await db.execute(
        """
        SELECT r.*,
               p.prenom AS personnel_prenom,
               COALESCE(f.nom, r.fournisseur_nom) AS fournisseur_nom
        FROM receptions r
        LEFT JOIN personnel    p ON p.id = r.personnel_id
        LEFT JOIN fournisseurs f ON f.id = r.fournisseur_principal_id
        WHERE r.id = ?
        """,
        (reception_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    reception = dict(row)

    cur2 = await db.execute(
        """
        SELECT rl.*,
               pr.nom  AS produit_nom,
               pr.espece,
               COALESCE(fv.nom, rl.fournisseur_nom) AS fournisseur_nom
        FROM reception_lignes rl
        LEFT JOIN produits     pr ON pr.id = rl.produit_id
        LEFT JOIN fournisseurs fv ON fv.id = rl.fournisseur_id
        WHERE rl.reception_id = ?
        ORDER BY rl.id
        """,
        (reception_id,),
    )
    lignes = await cur2.fetchall()
    reception["lignes"] = [dict(l) for l in lignes]
    return reception


# ---------------------------------------------------------------------------
# Non-conformités fournisseur
# ---------------------------------------------------------------------------

async def create_non_conformite(db: aiosqlite.Connection, data: dict) -> int:
    cursor = await db.execute(
        """
        INSERT INTO non_conformites_fournisseur
            (boutique_id, reception_id, reception_ligne_id, operateur, date_livraison,
             fournisseur_nom, produits, date_fabrication, dlc, nombre_barquettes,
             nature_nc, commentaires, refuse_livraison, nc_apres_livraison, info_ddpp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["boutique_id"],
            data.get("reception_id"),
            data.get("reception_ligne_id"),
            data["operateur"],
            data.get("date_livraison"),
            data.get("fournisseur_nom"),
            data.get("produits"),
            data.get("date_fabrication"),
            data.get("dlc"),
            data.get("nombre_barquettes"),
            json.dumps(data.get("nature_nc", []), ensure_ascii=False) if isinstance(data.get("nature_nc"), list) else data.get("nature_nc"),
            data.get("commentaires"),
            data.get("refuse_livraison", False),
            data.get("nc_apres_livraison", False),
            data.get("info_ddpp", False),
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def get_non_conformites(
    db: aiosqlite.Connection, boutique_id: int, limit: int = 50
) -> list[dict]:
    cursor = await db.execute(
        """
        SELECT * FROM non_conformites_fournisseur
        WHERE boutique_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (boutique_id, limit),
    )
    rows = await cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("nature_nc"):
            try:
                d["nature_nc"] = json.loads(d["nature_nc"])
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(d)
    return result


# ===========================================================================
# PHASE 2 — Module Tâches HACCP
# ===========================================================================

# ---------------------------------------------------------------------------
# Personnel
# ---------------------------------------------------------------------------

async def get_personnel(db: aiosqlite.Connection, boutique_id: int) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM personnel WHERE boutique_id = ? AND actif = 1 ORDER BY prenom",
        (boutique_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def create_personnel(db: aiosqlite.Connection, data: dict) -> int:
    cursor = await db.execute(
        "INSERT INTO personnel (boutique_id, prenom) VALUES (?, ?)",
        (data["boutique_id"], data["prenom"]),
    )
    await db.commit()
    return cursor.lastrowid


async def update_personnel(db: aiosqlite.Connection, personnel_id: int, data: dict) -> bool:
    fields = {k: v for k, v in data.items() if k in ("prenom", "actif")}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [personnel_id]
    await db.execute(f"UPDATE personnel SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Types de tâches
# ---------------------------------------------------------------------------

async def get_tache_types(db: aiosqlite.Connection, boutique_id: int) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM tache_types WHERE boutique_id = ? AND actif = 1 ORDER BY frequence, libelle",
        (boutique_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_tache_type(db: aiosqlite.Connection, tache_type_id: int) -> Optional[dict]:
    cursor = await db.execute(
        "SELECT * FROM tache_types WHERE id = ?", (tache_type_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def create_tache_type(db: aiosqlite.Connection, data: dict) -> int:
    cursor = await db.execute(
        """
        INSERT INTO tache_types
            (boutique_id, code, libelle, frequence, heure_cible, photo_requise)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data["boutique_id"],
            data["code"],
            data["libelle"],
            data["frequence"],
            data.get("heure_cible"),
            data.get("photo_requise", False),
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def update_tache_type(db: aiosqlite.Connection, tache_type_id: int, data: dict) -> bool:
    fields = {
        k: v for k, v in data.items()
        if k in ("libelle", "frequence", "heure_cible", "photo_requise", "actif")
    }
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [tache_type_id]
    await db.execute(f"UPDATE tache_types SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Validations de tâches
# ---------------------------------------------------------------------------

async def create_validation(db: aiosqlite.Connection, data: dict) -> int:
    donnees = data.get("donnees_specifiques")
    if isinstance(donnees, dict):
        donnees = json.dumps(donnees, ensure_ascii=False)
    cursor = await db.execute(
        """
        INSERT INTO tache_validations
            (boutique_id, tache_type_id, operateur, date_tache,
             conforme, photo_path, commentaire, donnees_specifiques)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["boutique_id"],
            data["tache_type_id"],
            data["operateur"],
            data["date_tache"],
            data.get("conforme"),
            data.get("photo_path"),
            data.get("commentaire"),
            donnees,
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def get_validations(
    db: aiosqlite.Connection,
    boutique_id: int,
    depuis: Optional[datetime] = None,
    jusqu_a: Optional[datetime] = None,
    tache_type_id: Optional[int] = None,
) -> list[dict]:
    depuis = depuis or (datetime.now(timezone.utc) - timedelta(days=30))
    jusqu_a = jusqu_a or datetime.now(timezone.utc)
    params: list = [boutique_id, depuis.date().isoformat(), jusqu_a.date().isoformat()]
    filtre_type = ""
    if tache_type_id:
        filtre_type = " AND tache_type_id = ?"
        params.append(tache_type_id)
    cursor = await db.execute(
        f"""
        SELECT v.*, t.code, t.libelle
        FROM tache_validations v
        JOIN tache_types t ON t.id = v.tache_type_id
        WHERE v.boutique_id = ? AND v.date_tache >= ? AND v.date_tache <= ?
        {filtre_type}
        ORDER BY v.heure_validation DESC
        """,
        params,
    )
    rows = await cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("donnees_specifiques"):
            try:
                d["donnees_specifiques"] = json.loads(d["donnees_specifiques"])
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(d)
    return result


async def get_taches_today(
    db: aiosqlite.Connection, boutique_id: int
) -> dict:
    """
    Retourne les tâches du jour (quotidiennes + hebdomadaires si bonne semaine
    + éventuelles) avec leur statut : fait / a_faire / en_retard.
    """
    from datetime import date, time as time_type
    from datetime import datetime as dt

    aujourd_hui = date.today()
    now = dt.now()
    jour_semaine = aujourd_hui.weekday()  # 0=lundi ... 6=dimanche

    # Types actifs
    cursor = await db.execute(
        "SELECT * FROM tache_types WHERE boutique_id = ? AND actif = 1",
        (boutique_id,),
    )
    types = [dict(r) for r in await cursor.fetchall()]

    # Validations déjà faites aujourd'hui
    cursor2 = await db.execute(
        """
        SELECT tache_type_id, COUNT(*) AS nb
        FROM tache_validations
        WHERE boutique_id = ? AND date_tache = ?
        GROUP BY tache_type_id
        """,
        (boutique_id, aujourd_hui.isoformat()),
    )
    faits_raw = await cursor2.fetchall()
    faits = {r["tache_type_id"]: r["nb"] for r in faits_raw}

    a_faire, fait, en_retard = [], [], []

    for t in types:
        freq = t["frequence"]
        # Filtre fréquence
        if freq == "quotidien":
            pass  # toujours inclus
        elif freq == "hebdomadaire":
            if jour_semaine != 0:  # lundi uniquement par défaut
                continue
        elif freq in ("evenementiel", "exceptionnel", "ponctuel"):
            continue  # pas dans la vue automatique du jour

        deja_fait = faits.get(t["id"], 0) > 0
        en_retard_flag = False

        if not deja_fait and t.get("heure_cible"):
            try:
                h, m = t["heure_cible"].split(":")
                heure_cible_dt = now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
                if now > heure_cible_dt:
                    en_retard_flag = True
            except Exception:
                pass

        tache_info = {
            "id": t["id"],
            "code": t["code"],
            "libelle": t["libelle"],
            "frequence": t["frequence"],
            "heure_cible": t.get("heure_cible"),
            "photo_requise": t.get("photo_requise", False),
        }

        if deja_fait:
            fait.append(tache_info)
        elif en_retard_flag:
            en_retard.append(tache_info)
        else:
            a_faire.append(tache_info)

    return {
        "date": aujourd_hui.isoformat(),
        "en_retard": en_retard,
        "a_faire": a_faire,
        "fait": fait,
    }


async def get_taches_en_retard(
    db: aiosqlite.Connection, boutique_id: int
) -> list[dict]:
    """Tâches quotidiennes/hebdomadaires non validées dont l'heure cible est dépassée."""
    data = await get_taches_today(db, boutique_id)
    return data["en_retard"]


# ===========================================================================
# PHASE 2 — Admin : pièges
# ===========================================================================

async def get_pieges(db: aiosqlite.Connection, boutique_id: int) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM pieges WHERE boutique_id = ? AND actif = 1 ORDER BY type, identifiant",
        (boutique_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def create_piege(db: aiosqlite.Connection, data: dict) -> int:
    cursor = await db.execute(
        "INSERT INTO pieges (boutique_id, type, identifiant, localisation) VALUES (?, ?, ?, ?)",
        (data["boutique_id"], data["type"], data["identifiant"], data.get("localisation")),
    )
    await db.commit()
    return cursor.lastrowid


# ---------------------------------------------------------------------------
# Fiches incident (PCR01)
# ---------------------------------------------------------------------------

async def create_fiche_incident(db: aiosqlite.Connection, data: dict) -> int:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    cursor = await db.execute(
        """
        INSERT INTO fiches_incident
            (reception_id, reception_ligne_id, date_incident, heure_incident,
             fournisseur_id, fournisseur_nom, produit_id, numero_lot, nature_probleme,
             description, action_immediate, livreur_present, signature_livreur_filename,
             etiquette_reprise_imprimee, action_corrective, commentaire,
             temperature_coeur, statut)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["reception_id"],
            data.get("reception_ligne_id"),
            data.get("date_incident", now.strftime("%Y-%m-%d")),
            data.get("heure_incident", now.strftime("%H:%M")),
            data.get("fournisseur_id"),
            data.get("fournisseur_nom"),
            data.get("produit_id"),
            data.get("numero_lot"),
            data["nature_probleme"],
            data.get("description"),
            data["action_immediate"],
            int(data.get("livreur_present", 0)),
            data.get("signature_livreur_filename"),
            int(data.get("etiquette_reprise_imprimee", 0)),
            data.get("action_corrective"),
            data.get("commentaire"),
            data.get("temperature_coeur"),
            data.get("statut", "ouverte"),
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def get_fiches_incident(
    db: aiosqlite.Connection,
    statut: Optional[str] = None,
    fournisseur_id: Optional[int] = None,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    limit: int = 50,
) -> list:
    conditions = []
    params: list = []
    if statut:
        conditions.append("fi.statut = ?")
        params.append(statut)
    if fournisseur_id is not None:
        conditions.append("fi.fournisseur_id = ?")
        params.append(fournisseur_id)
    if date_debut:
        conditions.append("fi.date_incident >= ?")
        params.append(date_debut)
    if date_fin:
        conditions.append("fi.date_incident <= ?")
        params.append(date_fin)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)

    cursor = await db.execute(
        f"""
        SELECT
            fi.*,
            f.nom  AS fournisseur_nom,
            p.nom  AS produit_nom,
            per.prenom AS cloturee_par_prenom
        FROM fiches_incident fi
        LEFT JOIN fournisseurs f   ON f.id  = fi.fournisseur_id
        LEFT JOIN produits     p   ON p.id  = fi.produit_id
        LEFT JOIN personnel    per ON per.id = fi.cloturee_par
        {where}
        ORDER BY fi.created_at DESC
        LIMIT ?
        """,
        params,
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_fiche_incident(db: aiosqlite.Connection, fiche_id: int) -> Optional[dict]:
    cursor = await db.execute(
        """
        SELECT
            fi.*,
            f.nom  AS fournisseur_nom,
            p.nom  AS produit_nom,
            per.prenom AS cloturee_par_prenom
        FROM fiches_incident fi
        LEFT JOIN fournisseurs f   ON f.id  = fi.fournisseur_id
        LEFT JOIN produits     p   ON p.id  = fi.produit_id
        LEFT JOIN personnel    per ON per.id = fi.cloturee_par
        WHERE fi.id = ?
        """,
        (fiche_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def update_fiche_incident(db: aiosqlite.Connection, fiche_id: int, data: dict) -> bool:
    from datetime import datetime, timezone
    allowed = {"action_corrective", "suivi", "statut", "cloturee_par",
               "etiquette_reprise_imprimee"}
    updates = {k: v for k, v in data.items() if k in allowed and v is not None}
    if not updates:
        return False

    # Auto-remplir cloturee_le si passage à 'cloturee'
    if updates.get("statut") == "cloturee" and "cloturee_le" not in updates:
        updates["cloturee_le"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [fiche_id]
    cursor = await db.execute(
        f"UPDATE fiches_incident SET {set_clause} WHERE id = ?", params
    )
    await db.commit()
    return cursor.rowcount > 0


# ===========================================================================
# PHASE 3 — Module Fabrication (Recettes & Traçabilité)
# ===========================================================================

async def get_recettes(db: aiosqlite.Connection) -> list[dict]:
    """Retourne la liste des recettes avec le nom du produit fini."""
    cur = await db.execute(
        """
        SELECT r.id, r.nom, r.dlc_jours, r.instructions, r.created_at,
               p.id   AS produit_fini_id,
               p.nom  AS produit_fini_nom
        FROM recettes r
        JOIN produits p ON p.id = r.produit_fini_id
        ORDER BY r.nom
        """
    )
    rows = await cur.fetchall()
    return [dict(row) for row in rows]


async def get_recette(db: aiosqlite.Connection, recette_id: int) -> Optional[dict]:
    """Retourne une recette avec ses ingrédients."""
    cur = await db.execute(
        """
        SELECT r.id, r.nom, r.dlc_jours, r.instructions, r.created_at,
               p.id  AS produit_fini_id,
               p.nom AS produit_fini_nom
        FROM recettes r
        JOIN produits p ON p.id = r.produit_fini_id
        WHERE r.id = ?
        """,
        (recette_id,),
    )
    row = await cur.fetchone()
    if not row:
        return None
    recette = dict(row)

    cur2 = await db.execute(
        """
        SELECT ri.id, ri.quantite, ri.unite,
               p.id  AS produit_id,
               p.nom AS produit_nom
        FROM recette_ingredients ri
        JOIN produits p ON p.id = ri.produit_id
        WHERE ri.recette_id = ?
        ORDER BY ri.id
        """,
        (recette_id,),
    )
    recette["ingredients"] = [dict(r) for r in await cur2.fetchall()]
    return recette


async def create_recette(
    db: aiosqlite.Connection,
    nom: str,
    produit_fini_id: int,
    dlc_jours: int,
    instructions: Optional[str],
    ingredients: list[dict],
) -> dict:
    """
    Crée une recette complète (recette + recette_ingredients).
    Chaque item de `ingredients` doit contenir : produit_id, quantite?, unite?
    """
    cur = await db.execute(
        "INSERT INTO recettes (nom, produit_fini_id, dlc_jours, instructions) VALUES (?,?,?,?)",
        (nom, produit_fini_id, dlc_jours, instructions),
    )
    recette_id = cur.lastrowid

    for ing in ingredients:
        await db.execute(
            "INSERT INTO recette_ingredients (recette_id, produit_id, quantite, unite) VALUES (?,?,?,?)",
            (recette_id, ing["produit_id"], ing.get("quantite"), ing.get("unite")),
        )

    await db.commit()
    result = await get_recette(db, recette_id)
    return result


async def get_fifo_lots(db: aiosqlite.Connection, recette_id: int) -> list[dict]:
    """
    Moteur FIFO : pour chaque ingrédient de la recette, retourne le lot de
    réception le plus ancien à utiliser en priorité.

    Règle FIFO :
      1. DLC la plus courte en premier (produit qui expire le plus tôt)
      2. À DLC égale, date de réception la plus ancienne
      3. Si aucun lot en stock → lot = None (le front demande la saisie manuelle)
    """
    recette = await get_recette(db, recette_id)
    if not recette:
        return []

    result = []
    for ing in recette["ingredients"]:
        cur = await db.execute(
            """
            SELECT rl.id        AS reception_ligne_id,
                   rl.numero_lot,
                   rl.dlc,
                   rl.poids_kg,
                   r.date_reception
            FROM   reception_lignes rl
            JOIN   receptions r ON r.id = rl.reception_id
            WHERE  rl.produit_id = ?
            ORDER BY
                CASE WHEN rl.dlc IS NOT NULL THEN 0 ELSE 1 END,
                rl.dlc          ASC,
                r.date_reception ASC
            LIMIT 1
            """,
            (ing["produit_id"],),
        )
        lot_row = await cur.fetchone()
        lot = dict(lot_row) if lot_row else None

        result.append({
            "recette_ingredient_id": ing["id"],
            "produit_id":            ing["produit_id"],
            "produit_nom":           ing["produit_nom"],
            "quantite_prevue":       ing["quantite"],
            "unite":                 ing["unite"],
            "lot_fifo":              lot,
        })

    return result


def _initiales_recette(nom: str) -> str:
    """Calcule les initiales d'un nom de recette (mots > 2 lettres), en majuscules.

    Exemple : "Merguez forte de boeuf" → "MFB"
    Les mots de 2 lettres ou moins (de, la, le, du…) sont ignorés.
    Retourne "FAB" si aucune lettre n'est trouvée.
    """
    mots = nom.strip().split()
    initiales = "".join(m[0].upper() for m in mots if len(m) > 2)
    return initiales or "FAB"


async def generer_lot_fabrication(db: aiosqlite.Connection, recette_nom: str) -> str:
    """
    Génère un numéro de lot interne fabrication unique.
    Format : {INITIALES}-YYYYMMDD-XXXX  (XXXX = compteur 4 chiffres, remis à 0 chaque jour)
    Les initiales sont dérivées du nom de la recette (mots > 2 lettres).
    """
    from datetime import date as _date
    today = _date.today()
    date_str    = today.strftime("%Y%m%d")
    code_unique = _initiales_recette(recette_nom)

    await db.execute(
        """
        INSERT INTO lot_interne_counters (code_unique, date_jjmmyy, counter)
        VALUES (?, ?, 1)
        ON CONFLICT(code_unique, date_jjmmyy) DO UPDATE SET counter = counter + 1
        """,
        (code_unique, date_str),
    )
    await db.commit()

    cur = await db.execute(
        "SELECT counter FROM lot_interne_counters WHERE code_unique = ? AND date_jjmmyy = ?",
        (code_unique, date_str),
    )
    row = await cur.fetchone()
    counter = row[0] if row else 1
    return f"{code_unique}-{date_str}-{counter:04d}"


async def create_fabrication(
    db: aiosqlite.Connection,
    recette_id: int,
    date: str,
    personnel_id: int,
    lots: list[dict],
    info_complementaire: Optional[str] = None,
    recette_nom: str = "FAB",
    dlc_finale: Optional[str] = None,
    poids_fabrique: Optional[float] = None,
) -> dict:
    """
    Enregistre une fabrication complète.

    `lots` : liste de dicts avec :
        - recette_ingredient_id : int
        - reception_ligne_id    : int  (lot fournisseur utilisé)

    `dlc_finale` : date ISO "YYYY-MM-DD" calculée côté client selon règle HACCP
    (min entre DLC théorique produit et DLC la plus courte des ingrédients).

    Retourne la fabrication créée avec son lot_interne.
    """
    lot_interne = await generer_lot_fabrication(db, recette_nom)

    cur = await db.execute(
        """
        INSERT INTO fabrications
            (recette_id, date, lot_interne, personnel_id, info_complementaire, dlc_finale, poids_fabrique)
        VALUES (?,?,?,?,?,?,?)
        """,
        (recette_id, date, lot_interne, personnel_id, info_complementaire, dlc_finale, poids_fabrique),
    )
    fabrication_id = cur.lastrowid

    for lot in lots:
        await db.execute(
            """
            INSERT INTO fabrication_lots
                (fabrication_id, recette_ingredient_id, reception_ligne_id)
            VALUES (?,?,?)
            """,
            (fabrication_id, lot["recette_ingredient_id"], lot["reception_ligne_id"]),
        )

    await db.commit()

    cur2 = await db.execute(
        "SELECT * FROM fabrications WHERE id = ?", (fabrication_id,)
    )
    row = await cur2.fetchone()
    return dict(row)


async def get_fabrications_historique(
    db: aiosqlite.Connection,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    recette_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> list:
    """
    Retourne la liste des fabrications (ordre anti-chronologique) avec,
    pour chaque fabrication, la liste des ingrédients utilisés.
    """
    conditions: list[str] = []
    params: list = []

    if date_debut:
        conditions.append("f.date >= ?")
        params.append(date_debut)
    if date_fin:
        conditions.append("f.date <= ?")
        params.append(date_fin)
    if recette_id is not None:
        conditions.append("f.recette_id = ?")
        params.append(recette_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    cur = await db.execute(
        f"""
        SELECT
            f.id,
            f.lot_interne,
            f.date,
            f.dlc_finale,
            f.poids_fabrique,
            f.info_complementaire,
            r.nom           AS recette_nom,
            r.instructions  AS recette_instructions,
            pe.prenom       AS personnel_prenom
        FROM fabrications f
        JOIN recettes  r  ON r.id  = f.recette_id
        JOIN personnel pe ON pe.id = f.personnel_id
        {where}
        ORDER BY f.date DESC, f.id DESC
        LIMIT ? OFFSET ?
        """,
        (*params, limit, offset),
    )
    rows = await cur.fetchall()
    fabrications = [dict(r) for r in rows]

    for fab in fabrications:
        cur2 = await db.execute(
            """
            SELECT
                p.nom           AS produit_nom,
                rl.numero_lot,
                rl.dlc,
                ri.quantite     AS quantite_base,
                ri.unite,
                rec.id          AS reception_id
            FROM fabrication_lots fl
            JOIN recette_ingredients ri ON ri.id  = fl.recette_ingredient_id
            JOIN produits           p   ON p.id   = ri.produit_id
            LEFT JOIN reception_lignes rl  ON rl.id  = fl.reception_ligne_id
            LEFT JOIN receptions       rec ON rec.id = rl.reception_id
            WHERE fl.fabrication_id = ?
            ORDER BY p.nom
            """,
            (fab["id"],),
        )
        ing_rows = await cur2.fetchall()
        fab["ingredients"] = [dict(r) for r in ing_rows]

    return fabrications

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

# DLC (en jours) appliquée aux produits transformés sur place :
# cuisson, refroidissement, fabrication HACCP. Règle métier non modifiable.
DLC_JOURS_TRANSFORMATION = 3

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
    delai_alerte_minutes         INTEGER DEFAULT 30,
    delai_perte_signal_minutes   INTEGER DEFAULT 720,
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
    source_type              TEXT,
    source_id                INTEGER,
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
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id          INTEGER NOT NULL,
    nom                  TEXT    NOT NULL,
    email_commercial     TEXT,
    telephone            TEXT,
    adresse              TEXT,
    conditions_paiement  TEXT,
    nom_commercial        TEXT,
    delai_paiement_jours  INTEGER,
    jours_livraison       TEXT,    -- JSON array ["lundi","mercredi",...]
    rythme_livraison      TEXT,    -- 'A-B' | 'A-C' | 'A-D'
    heure_limite_commande TEXT,    -- "12:00"
    heure_livraison       TEXT,    -- "08:00"
    commentaire           TEXT,
    actif                 BOOLEAN DEFAULT 1,
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

CREATE TABLE IF NOT EXISTS receptions (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    personnel_id             INTEGER NOT NULL,
    date_reception           DATE    DEFAULT CURRENT_DATE,
    heure_reception          TEXT    NOT NULL,
    temperature_camion       REAL,
    proprete_camion          TEXT    DEFAULT 'satisfaisant',
    proprete_photo_filename  TEXT,
    camion_conforme          INTEGER DEFAULT 1,
    fournisseur_principal_id INTEGER,
    photo_bl_filename        TEXT,
    commentaire              TEXT,
    conformite_globale       TEXT    DEFAULT 'conforme',
    livraison_refusee        INTEGER DEFAULT 0,
    information_ddpp         INTEGER DEFAULT 0,
    commentaire_nc           TEXT,
    statut                   TEXT    DEFAULT 'en_cours',
    created_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (personnel_id)             REFERENCES personnel(id),
    FOREIGN KEY (fournisseur_principal_id) REFERENCES fournisseurs(id)
);

CREATE INDEX IF NOT EXISTS idx_receptions_date
    ON receptions(date_reception);

CREATE TABLE IF NOT EXISTS reception_lignes (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    reception_id              INTEGER NOT NULL,
    produit_id                INTEGER,
    catalogue_fournisseur_id  INTEGER,
    fournisseur_id            INTEGER,
    fournisseur_nom           TEXT,
    numero_lot                TEXT,
    dlc                       DATE,
    dluo                      DATE,
    date_abattage             DATE,
    origine                   TEXT    DEFAULT 'France',
    poids_kg                  REAL,
    temperature_reception     REAL,
    temperature_conforme      INTEGER,
    temperature_coeur         REAL,
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
    lot_interne               INTEGER DEFAULT 0,
    created_at                DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reception_id)             REFERENCES receptions(id),
    FOREIGN KEY (produit_id)               REFERENCES produits(id),
    FOREIGN KEY (catalogue_fournisseur_id) REFERENCES catalogue_fournisseur(id),
    FOREIGN KEY (fournisseur_id)           REFERENCES fournisseurs(id)
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
    nom         TEXT,
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
    personnel_id        INTEGER,
    date_tache          DATE    NOT NULL,
    heure_validation    DATETIME DEFAULT CURRENT_TIMESTAMP,
    conforme            BOOLEAN,
    photo_path          TEXT,
    commentaire         TEXT,
    donnees_specifiques TEXT,
    FOREIGN KEY (boutique_id)   REFERENCES boutiques(id),
    FOREIGN KEY (tache_type_id) REFERENCES tache_types(id),
    FOREIGN KEY (personnel_id)  REFERENCES personnel(id)
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
    personnel_id        INTEGER,
    commentaire         TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thermometre_ref_id) REFERENCES thermometres_ref(id),
    FOREIGN KEY (personnel_id)       REFERENCES personnel(id)
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

-- ===========================================================================
-- Paramètres génériques (key/value par boutique)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS parametres (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id INTEGER NOT NULL,
    cle         TEXT    NOT NULL,
    valeur      TEXT    NOT NULL,
    UNIQUE(boutique_id, cle),
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

-- ===========================================================================
-- PHASE 2 — Module Cuisson (rôtissoire / cuissons HACCP, ≥ 75 °C à cœur)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS cuissons (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id         INTEGER NOT NULL DEFAULT 1,
    type_cuisson        TEXT    NOT NULL,           -- 'rotissoire', ...
    date_cuisson        DATE    NOT NULL,
    personnel_id        INTEGER NOT NULL,
    produit_id          INTEGER NOT NULL,
    reception_ligne_id  INTEGER,                     -- source = lot de réception (brut)
    fabrication_id      INTEGER,                     -- source = lot de fabrication (produit fini cru)
    quantite            REAL,
    unite               TEXT    DEFAULT 'kg',
    heure_debut         TEXT    NOT NULL,
    heure_fin           TEXT    NOT NULL,
    temperature_sortie  REAL    NOT NULL,
    temperature_cible   REAL    NOT NULL DEFAULT 75.0,
    conforme            INTEGER NOT NULL,
    action_corrective   TEXT,
    dlc_finale          DATE,                        -- date_cuisson + DLC_JOURS_TRANSFORMATION
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boutique_id)        REFERENCES boutiques(id),
    FOREIGN KEY (personnel_id)       REFERENCES personnel(id),
    FOREIGN KEY (produit_id)         REFERENCES produits(id),
    FOREIGN KEY (reception_ligne_id) REFERENCES reception_lignes(id),
    FOREIGN KEY (fabrication_id)     REFERENCES fabrications(id)
);

CREATE INDEX IF NOT EXISTS idx_cuissons_type_date
    ON cuissons(type_cuisson, date_cuisson);

-- ===========================================================================
-- PHASE 2 — Module Refroidissement (≤ 10 °C à cœur en ≤ 2 h)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS refroidissements (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id           INTEGER NOT NULL DEFAULT 1,
    date_refroidissement  DATE    NOT NULL,
    personnel_id          INTEGER NOT NULL,
    produit_id            INTEGER NOT NULL,
    cuisson_id            INTEGER,
    numero_lot            TEXT,
    reception_ligne_id    INTEGER,
    heure_debut           TEXT    NOT NULL,
    heure_fin             TEXT    NOT NULL,
    duree_minutes         INTEGER NOT NULL,
    temperature_initiale  REAL    DEFAULT 75.0,
    temperature_finale    REAL    NOT NULL,
    temperature_cible     REAL    NOT NULL DEFAULT 10.0,
    duree_max_minutes     INTEGER NOT NULL DEFAULT 120,
    conforme              INTEGER NOT NULL,
    jeter                 INTEGER NOT NULL DEFAULT 0,
    action_corrective     TEXT,
    dlc_finale            DATE,                       -- date_refroidissement + DLC_JOURS_TRANSFORMATION
    created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boutique_id)        REFERENCES boutiques(id),
    FOREIGN KEY (personnel_id)       REFERENCES personnel(id),
    FOREIGN KEY (produit_id)         REFERENCES produits(id),
    FOREIGN KEY (cuisson_id)         REFERENCES cuissons(id),
    FOREIGN KEY (reception_ligne_id) REFERENCES reception_lignes(id)
);

CREATE INDEX IF NOT EXISTS idx_refroidissements_date
    ON refroidissements(date_refroidissement);

-- ===========================================================================
-- PHASE 2 — Module Plan de nettoyage & désinfection
-- ===========================================================================

CREATE TABLE IF NOT EXISTS taches_nettoyage (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id     INTEGER NOT NULL DEFAULT 1,
    zone            TEXT    NOT NULL,
    nom_tache       TEXT    NOT NULL,
    frequence       TEXT    NOT NULL,
    methode_produit TEXT    NOT NULL,
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

CREATE TABLE IF NOT EXISTS registre_nettoyage (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id  INTEGER NOT NULL DEFAULT 1,
    tache_id     INTEGER NOT NULL,
    operateur    TEXT    NOT NULL,
    personnel_id INTEGER,
    date_val     TEXT    NOT NULL,
    signature    TEXT    NOT NULL DEFAULT 'OK',
    FOREIGN KEY (boutique_id)  REFERENCES boutiques(id),
    FOREIGN KEY (tache_id)     REFERENCES taches_nettoyage(id),
    FOREIGN KEY (personnel_id) REFERENCES personnel(id)
);

CREATE INDEX IF NOT EXISTS idx_registre_nettoyage_date
    ON registre_nettoyage(date_val);

-- ===========================================================================
-- PHASE 2 — Module Nuisibles (lutte IPM hebdomadaire)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS nuisibles_controles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id  INTEGER NOT NULL DEFAULT 1,
    type_id      INTEGER NOT NULL,    -- 1=rongeurs 2=ins.vol 3=ins.ramp 4=oiseaux
    annee        INTEGER NOT NULL,
    semaine      INTEGER NOT NULL,
    resultats    TEXT    NOT NULL DEFAULT '{}',
    visa         TEXT    NOT NULL DEFAULT '',
    personnel_id INTEGER,
    date_saisie  TEXT    NOT NULL,
    UNIQUE(type_id, annee, semaine),
    FOREIGN KEY (boutique_id)  REFERENCES boutiques(id),
    FOREIGN KEY (personnel_id) REFERENCES personnel(id)
);

-- Position des pièges sur le plan de la boutique (un point par piège & par type).
-- pos_x / pos_y sont des pourcentages (0..100) relatifs à l'image → responsive.
CREATE TABLE IF NOT EXISTS nuisibles_pieges_carte (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id INTEGER NOT NULL DEFAULT 1,
    type_id     INTEGER NOT NULL,    -- 1=rongeurs 2=ins.vol 3=ins.ramp 4=oiseaux
    piege_num   INTEGER NOT NULL,    -- 1..N (correspond à P1..Pn du tableau)
    pos_x       REAL    NOT NULL,    -- pourcentage horizontal 0..100
    pos_y       REAL    NOT NULL,    -- pourcentage vertical 0..100
    UNIQUE(boutique_id, type_id, piege_num),
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

-- ===========================================================================
-- Module DLC — devenir des produits expirés
-- ===========================================================================

CREATE TABLE IF NOT EXISTS dlc_devenir (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type  TEXT    NOT NULL,    -- 'reception_ligne' | 'fabrication'
    source_id    INTEGER NOT NULL,
    statut       TEXT    NOT NULL,    -- 'jete' | 'vendu' | 'consomme' | 'autre'
    personnel_id INTEGER,
    commentaire  TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_type, source_id),
    FOREIGN KEY (personnel_id) REFERENCES personnel(id)
);

CREATE INDEX IF NOT EXISTS idx_dlc_devenir_source
    ON dlc_devenir(source_type, source_id);

-- ===========================================================================
-- Module E-Learning — traçabilité des formations suivies
-- ===========================================================================

CREATE TABLE IF NOT EXISTS elearning_completions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id     INTEGER NOT NULL DEFAULT 1,
    module          TEXT    NOT NULL,    -- 'hygiene-pdf' | 'decoupe-pdf' | 'hygiene-module' ...
    personnel_id    INTEGER NOT NULL,
    date_completion DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boutique_id)  REFERENCES boutiques(id),
    FOREIGN KEY (personnel_id) REFERENCES personnel(id)
);

CREATE INDEX IF NOT EXISTS idx_elearning_module
    ON elearning_completions(module, date_completion);

CREATE INDEX IF NOT EXISTS idx_elearning_personnel
    ON elearning_completions(personnel_id, date_completion);

-- ===========================================================================
-- Module Quiz E-Learning — résultats des quiz (attestation de formation)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS quiz_resultats (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id       INTEGER NOT NULL DEFAULT 1,
    quiz_id           INTEGER NOT NULL,            -- 1..10 (numéro du quiz hygiène)
    personnel_id      INTEGER NOT NULL,
    score             INTEGER NOT NULL,            -- nb de bonnes réponses
    total             INTEGER NOT NULL,            -- nb total de questions
    pourcentage       INTEGER NOT NULL,            -- 0..100
    reussi            INTEGER NOT NULL DEFAULT 0,  -- 1 si pourcentage >= seuil (80)
    signature         TEXT,                        -- signature opérateur (PNG base64 data-URL)
    date_completion   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boutique_id)  REFERENCES boutiques(id),
    FOREIGN KEY (personnel_id) REFERENCES personnel(id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_resultats_quiz
    ON quiz_resultats(quiz_id, date_completion);

CREATE INDEX IF NOT EXISTS idx_quiz_resultats_personnel
    ON quiz_resultats(personnel_id, quiz_id, date_completion);

-- Progression d'un quiz en cours (reprise plus tard si non terminé).
-- Une seule ligne par (boutique, quiz, personnel) : écrasée à chaque avancée,
-- supprimée quand le quiz est terminé (résultat enregistré dans quiz_resultats).
CREATE TABLE IF NOT EXISTS quiz_progression (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id       INTEGER NOT NULL DEFAULT 1,
    quiz_id           INTEGER NOT NULL,            -- 1..10 (numéro du quiz hygiène)
    personnel_id      INTEGER NOT NULL,
    q_index           INTEGER NOT NULL,            -- index de la question en cours (0-based)
    score             INTEGER NOT NULL,            -- bonnes réponses cumulées
    total             INTEGER NOT NULL,            -- nb total de questions du quiz
    reponses          TEXT,                        -- JSON : {"0":"A","1":"C",...} réponses données
    date_maj          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boutique_id)  REFERENCES boutiques(id),
    FOREIGN KEY (personnel_id) REFERENCES personnel(id),
    UNIQUE (boutique_id, quiz_id, personnel_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_progression_personnel
    ON quiz_progression(personnel_id, quiz_id);

-- ===========================================================================
-- MODULE ACHATS — Fournisseurs, Catalogue, Commandes, Maturation carcasses
-- ===========================================================================

CREATE TABLE IF NOT EXISTS catalogue_fournisseur (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    fournisseur_id   INTEGER NOT NULL,
    code_article     TEXT    NOT NULL,
    designation      TEXT    NOT NULL,
    prix_achat_ht    REAL    NOT NULL DEFAULT 0.0,
    tva_percent      REAL    DEFAULT 5.5,
    conditionnement  TEXT,
    dlc_type         TEXT    DEFAULT 'dlc',   -- 'dlc' | 'date_abattage' | 'no_dlc'
    dlc_jours        INTEGER,
    actif            INTEGER DEFAULT 1,
    date_maj         DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id),
    UNIQUE(fournisseur_id, code_article)
);

CREATE INDEX IF NOT EXISTS idx_catalogue_fournisseur_fournisseur
    ON catalogue_fournisseur(fournisseur_id);

CREATE TABLE IF NOT EXISTS commandes (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id           INTEGER NOT NULL DEFAULT 1,
    fournisseur_id        INTEGER NOT NULL,
    numero_commande       TEXT    UNIQUE,
    date_commande         DATE    NOT NULL DEFAULT CURRENT_DATE,
    date_livraison_prevue DATE,
    statut                TEXT    NOT NULL DEFAULT 'brouillon',  -- brouillon|confirmee|livree|annulee
    montant_total_ht      REAL    DEFAULT 0.0,
    commentaire           TEXT,
    personnel_id          INTEGER,
    date_envoi_mail       DATETIME,
    created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boutique_id)    REFERENCES boutiques(id),
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id),
    FOREIGN KEY (personnel_id)   REFERENCES personnel(id)
);

CREATE INDEX IF NOT EXISTS idx_commandes_fournisseur
    ON commandes(fournisseur_id, date_commande DESC);
CREATE INDEX IF NOT EXISTS idx_commandes_statut
    ON commandes(statut, date_commande DESC);

CREATE TABLE IF NOT EXISTS commande_lignes (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    commande_id            INTEGER NOT NULL,
    catalogue_fournisseur_id INTEGER,
    code_article           TEXT    NOT NULL,
    designation            TEXT    NOT NULL,
    prix_unitaire_ht       REAL    NOT NULL DEFAULT 0.0,
    quantite_commandee     REAL    NOT NULL,
    unite                  TEXT    NOT NULL DEFAULT 'kg',
    montant_ht             REAL    DEFAULT 0.0,
    commentaire_ligne      TEXT,
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (commande_id)              REFERENCES commandes(id) ON DELETE CASCADE,
    FOREIGN KEY (catalogue_fournisseur_id) REFERENCES catalogue_fournisseur(id)
);

CREATE INDEX IF NOT EXISTS idx_commande_lignes_commande
    ON commande_lignes(commande_id);

CREATE TABLE IF NOT EXISTS commande_receptions_mapping (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    commande_id  INTEGER NOT NULL,
    reception_id INTEGER NOT NULL,
    date_liaison DATETIME DEFAULT CURRENT_TIMESTAMP,
    personnel_id INTEGER,
    FOREIGN KEY (commande_id)  REFERENCES commandes(id),
    FOREIGN KEY (reception_id) REFERENCES receptions(id),
    FOREIGN KEY (personnel_id) REFERENCES personnel(id),
    UNIQUE(commande_id, reception_id)
);

CREATE INDEX IF NOT EXISTS idx_mapping_commande
    ON commande_receptions_mapping(commande_id);

CREATE TABLE IF NOT EXISTS panier_lignes (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id              INTEGER NOT NULL DEFAULT 1,
    catalogue_fournisseur_id INTEGER,
    fournisseur_id           INTEGER NOT NULL,
    fournisseur_nom          TEXT    NOT NULL,
    code_article             TEXT    NOT NULL,
    designation              TEXT    NOT NULL,
    quantite                 REAL    NOT NULL DEFAULT 1.0,
    unite                    TEXT    NOT NULL DEFAULT 'kg',
    prix_ht                  REAL    NOT NULL DEFAULT 0.0,
    created_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fournisseur_id)           REFERENCES fournisseurs(id),
    FOREIGN KEY (catalogue_fournisseur_id) REFERENCES catalogue_fournisseur(id)
);
CREATE INDEX IF NOT EXISTS idx_mapping_reception
    ON commande_receptions_mapping(reception_id);

CREATE TABLE IF NOT EXISTS maturation_carcasses (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    reception_ligne_id     INTEGER NOT NULL,
    numero_lot             TEXT    NOT NULL,
    date_abattage          DATE    NOT NULL,
    date_dernier_controle  DATE,
    etat_controle          TEXT,   -- 'OK' | 'A_SURVEILLER' | 'NON_CONFORME'
    aspect                 TEXT,
    odeur                  TEXT,
    dessiccation           TEXT,
    poissage               TEXT,
    parage_effectue        INTEGER DEFAULT 0,
    commentaire_controle   TEXT,
    decision_humaine       TEXT,   -- 'Maturation' | 'Decoupe' | 'Declassement' | 'Destruction'
    date_prochain_controle DATE,
    personnel_id           INTEGER,
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reception_ligne_id) REFERENCES reception_lignes(id),
    FOREIGN KEY (personnel_id)       REFERENCES personnel(id)
);

CREATE INDEX IF NOT EXISTS idx_maturation_reception_ligne
    ON maturation_carcasses(reception_ligne_id);
CREATE INDEX IF NOT EXISTS idx_maturation_etat
    ON maturation_carcasses(etat_controle, date_prochain_controle);
"""

SEED_SQL = """
INSERT OR IGNORE INTO boutiques (id, nom, adresse, siret)
VALUES (1, 'Au Comptoir des Lilas', '122 rue de Paris, Les Lilas, 93260', '');

INSERT OR IGNORE INTO enceintes (id, boutique_id, nom, type, sonde_zigbee_id, seuil_temp_min, seuil_temp_max, seuil_hum_max, delai_alerte_minutes)
VALUES
(1, 1, 'Chambre froide 1', 'chambre_froide', 'chambre_froide_1',  0.0,  4.0, 90.0, 30),
(2, 1, 'Chambre froide 2', 'chambre_froide', 'chambre_froide_2',  0.0,  4.0, 90.0, 30),
(3, 1, 'vitrine',          'vitrine',        'vitrine',            0.0,  4.0, 90.0, 30),
(4, 1, 'laboratoire',      'laboratoire',    'laboratoire',       10.0, 15.0, 80.0, 30);
"""

SEED_SQL_PHASE2 = """
-- Règles DLC par défaut (boutique 1)
INSERT OR IGNORE INTO regles_dlc (boutique_id, categorie, dlc_jours, note) VALUES
(1, 'viande_hachee',    1, 'Viande hachée fraîche'),
(1, 'viande_pieces',    3, 'Pièces de viande entières'),
(1, 'preparation_crue', 2, 'Préparations crues : merguez, saucisses...'),
(1, 'charcuterie',      5, 'Charcuterie'),
(1, 'traiteur',         3, 'Traiteur');

-- Types de tâches HACCP par défaut (boutique 1)
-- Quotidien : géré par module Nettoyage (nettoyage.html, table dédiée)
-- Hebdomadaire : géré par module Nuisibles (nuisibles.html)
-- Trimestriel : géré par module Étalonnage (etalonnage.html)
INSERT OR IGNORE INTO tache_types (boutique_id, code, libelle, frequence, heure_cible, photo_requise) VALUES
(1, 'etalonnage_thermometres',    'Étalonnage thermomètres',                    'trimestriel',   NULL,    0),
(1, 'action_corrective_temp',     'Action corrective température',               'evenementiel',  NULL,    0),
(1, 'pieges_rongeurs',            'Présence rongeurs sur pièges',                'hebdomadaire',  NULL,    0),
(1, 'nettoyage_pieges_oiseaux',   'Nettoyage pièges oiseaux',                    'hebdomadaire',  NULL,    0),
(1, 'controle_huile_friture',     'Contrôle huile de friture',                   'evenementiel',  NULL,    0),
(1, 'suivi_decongélation',        'Suivi décongélation',                         'evenementiel',  NULL,    0),
(1, 'suivi_congelation',          'Suivi congélation',                           'evenementiel',  NULL,    0),
(1, 'tiac',                       'TIAC — Toxi-infection alimentaire collective', 'exceptionnel',  NULL,    1);

-- Pièges rongeurs par défaut (boutique 1)
INSERT OR IGNORE INTO pieges (boutique_id, type, identifiant, localisation) VALUES
(1, 'rongeur', 'P1', 'Entrée laboratoire'),
(1, 'rongeur', 'P2', 'Fond laboratoire'),
(1, 'oiseau',  'P3', 'Entrée boutique');

-- Paramètres DLC par défaut (boutique 1) — seuils en jours
INSERT OR IGNORE INTO parametres (boutique_id, cle, valeur) VALUES
(1, 'dlc_alerte_rouge_jours',  '1'),
(1, 'dlc_alerte_orange_jours', '3'),
(1, 'dlc_alerte_jaune_jours',  '7');

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

        # SEED_SQL_PHASE2 (pièges, types de tâches, règles/paramètres DLC) :
        # données de configuration modifiables par l'admin. On ne les insère
        # qu'UNE SEULE FOIS, à la création de la base, sinon un INSERT OR IGNORE
        # à chaque démarrage ressusciterait les éléments supprimés via l'admin.
        # Drapeau idempotent stocké dans `parametres`.
        cur = await db.execute(
            "SELECT 1 FROM parametres WHERE boutique_id = 1 AND cle = 'seed_phase2_done'"
        )
        seed_deja_fait = await cur.fetchone() is not None
        if not seed_deja_fait:
            # La base est-elle réellement neuve, ou déjà exploitée ?
            # (bases d'avant ce drapeau : on ne doit PAS relancer le seed, sinon
            #  on ressusciterait les pièges / tâches déjà supprimés par l'admin.)
            cur = await db.execute(
                "SELECT "
                "(SELECT COUNT(*) FROM pieges) + "
                "(SELECT COUNT(*) FROM tache_types) + "
                "(SELECT COUNT(*) FROM personnel)"
            )
            base_deja_exploitee = (await cur.fetchone())[0] > 0
            if not base_deja_exploitee:
                await db.executescript(SEED_SQL_PHASE2)
                logger.info("Seed initial Phase 2 inséré (première création de la base)")
            else:
                logger.info("Base existante : seed Phase 2 ignoré, drapeau posé")
            await db.execute(
                "INSERT OR IGNORE INTO parametres (boutique_id, cle, valeur) "
                "VALUES (1, 'seed_phase2_done', '1')"
            )
            await db.commit()
        # Migration : ajout colonne nom dans personnel (nullable, rétrocompatible)
        cur = await db.execute("PRAGMA table_info(personnel)")
        cols_pers = {row[1] for row in await cur.fetchall()}
        if "nom" not in cols_pers:
            logger.info("Migration : ajout colonne nom dans personnel")
            await db.execute("ALTER TABLE personnel ADD COLUMN nom TEXT")
            await db.commit()

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
    proprete_photo_filename  TEXT,
    camion_conforme          INTEGER DEFAULT 1,
    fournisseur_principal_id INTEGER,
    photo_bl_filename        TEXT,
    commentaire              TEXT,
    conformite_globale       TEXT    DEFAULT 'conforme',
    livraison_refusee        INTEGER DEFAULT 0,
    information_ddpp         INTEGER DEFAULT 0,
    commentaire_nc           TEXT,
    statut                   TEXT    DEFAULT 'en_cours',
    created_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (personnel_id)             REFERENCES personnel(id),
    FOREIGN KEY (fournisseur_principal_id) REFERENCES fournisseurs(id)
);
CREATE TABLE IF NOT EXISTS reception_lignes (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    reception_id              INTEGER NOT NULL,
    produit_id                INTEGER,
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
            # EET01 — Thermomètres de référence (v3.0)
            """CREATE TABLE IF NOT EXISTS thermometres_ref (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                boutique_id  INTEGER NOT NULL DEFAULT 1,
                nom          TEXT    NOT NULL,
                numero_serie TEXT,
                actif        BOOLEAN DEFAULT 1,
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(boutique_id, nom)
            )""",
            # EET01 — Étalonnages (v3.0)
            """CREATE TABLE IF NOT EXISTS etalonnages (
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
            )""",
            "CREATE INDEX IF NOT EXISTS idx_etalonnages_date ON etalonnages(date_etalonnage)",
            # EET01 — Comparaisons sondes (v3.0)
            """CREATE TABLE IF NOT EXISTS etalonnage_comparaisons (
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
            )""",
            # v3.1 — Rapatriement dans SCHEMA_SQL des tables auparavant créées
            # à la volée par les routes (cuissons, refroidissements, nettoyage,
            # nuisibles). Pour les bases déjà déployées, on ajoute boutique_id.
            "ALTER TABLE cuissons            ADD COLUMN boutique_id INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE refroidissements    ADD COLUMN boutique_id INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE refroidissements    ADD COLUMN temperature_initiale REAL DEFAULT 75.0",
            "ALTER TABLE taches_nettoyage    ADD COLUMN boutique_id INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE registre_nettoyage  ADD COLUMN boutique_id INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE nuisibles_controles ADD COLUMN boutique_id INTEGER NOT NULL DEFAULT 1",
            # v3.2 — DLC = J+3 sur cuisson / refroidissement (règle HACCP transformation)
            "ALTER TABLE cuissons         ADD COLUMN dlc_finale DATE",
            "ALTER TABLE refroidissements ADD COLUMN dlc_finale DATE",
            # Rétro-remplissage des lignes existantes
            f"UPDATE cuissons         SET dlc_finale = date(date_cuisson,         '+{DLC_JOURS_TRANSFORMATION} days') WHERE dlc_finale IS NULL",
            f"UPDATE refroidissements SET dlc_finale = date(date_refroidissement, '+{DLC_JOURS_TRANSFORMATION} days') WHERE dlc_finale IS NULL",
            # v3.3 — Traçabilité refroidissement : numerotet reception_ligne_id pour retrouver le lot
            "ALTER TABLE refroidissements ADD COLUMN numero_lot TEXT",
            "ALTER TABLE refroidissements ADD COLUMN reception_ligne_id INTEGER",
            # v3.4 — Étiquettes des produits transformés (cuisson / refroidissement / fabrication)
            "ALTER TABLE etiquettes_generees ADD COLUMN source_type TEXT",
            "ALTER TABLE etiquettes_generees ADD COLUMN source_id INTEGER",
            # v3.5 — Statut réception : produits visibles en stock uniquement après clôture
            "ALTER TABLE receptions ADD COLUMN statut TEXT DEFAULT 'en_cours'",
            # v3.6 — Refus livraison multi-BL : 1 BL par fournisseur (au-delà du fournisseur principal)
            """CREATE TABLE IF NOT EXISTS reception_bls_supplementaires (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                reception_id      INTEGER NOT NULL,
                fournisseur_id    INTEGER,
                fournisseur_nom   TEXT,
                photo_bl_filename TEXT,
                ordre             INTEGER DEFAULT 0,
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reception_id)   REFERENCES receptions(id),
                FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_reception_bls_reception ON reception_bls_supplementaires(reception_id)",
            # v3.7 — Photo du problème de propreté camion (NC propreté)
            "ALTER TABLE receptions ADD COLUMN proprete_photo_filename TEXT",
            # v3.8 — Cuisson depuis une fabrication (produit fini cru → cuisson)
            "ALTER TABLE cuissons ADD COLUMN fabrication_id INTEGER",
            # v4.0 — Signature opérateur sur les résultats de quiz (attestation)
            "ALTER TABLE quiz_resultats ADD COLUMN signature TEXT",
            # v4.1 — Carte des pièges (positions sur le plan de la boutique)
            """CREATE TABLE IF NOT EXISTS nuisibles_pieges_carte (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                boutique_id INTEGER NOT NULL DEFAULT 1,
                type_id     INTEGER NOT NULL,
                piege_num   INTEGER NOT NULL,
                pos_x       REAL    NOT NULL,
                pos_y       REAL    NOT NULL,
                UNIQUE(boutique_id, type_id, piege_num),
                FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
            )""",
            # v4.3 — Délai notification perte de signal indépendant du délai température
            "ALTER TABLE enceintes ADD COLUMN delai_perte_signal_minutes INTEGER DEFAULT 720",
            # v4.2 — Opérateur en FK personnel (au lieu de prénom TEXT) sur 4 modules
            "ALTER TABLE registre_nettoyage ADD COLUMN personnel_id INTEGER REFERENCES personnel(id)",
            "ALTER TABLE etalonnages        ADD COLUMN personnel_id INTEGER REFERENCES personnel(id)",
            "ALTER TABLE tache_validations  ADD COLUMN personnel_id INTEGER REFERENCES personnel(id)",
            "ALTER TABLE nuisibles_controles ADD COLUMN personnel_id INTEGER REFERENCES personnel(id)",
            # v5.0 — Module Achats : enrichissement fournisseurs
            "ALTER TABLE fournisseurs ADD COLUMN email_commercial TEXT",
            "ALTER TABLE fournisseurs ADD COLUMN telephone TEXT",
            "ALTER TABLE fournisseurs ADD COLUMN adresse TEXT",
            "ALTER TABLE fournisseurs ADD COLUMN conditions_paiement TEXT",
            # v5.1 — Fournisseurs : délai paiement, jours livraison, commentaire, rythme, heures
            "ALTER TABLE fournisseurs ADD COLUMN delai_paiement_jours INTEGER",
            "ALTER TABLE fournisseurs ADD COLUMN jours_livraison TEXT",
            "ALTER TABLE fournisseurs ADD COLUMN commentaire TEXT",
            "ALTER TABLE fournisseurs ADD COLUMN rythme_livraison TEXT",
            "ALTER TABLE fournisseurs ADD COLUMN heure_limite_commande TEXT",
            "ALTER TABLE fournisseurs ADD COLUMN heure_livraison TEXT",
            "ALTER TABLE fournisseurs ADD COLUMN nom_commercial TEXT",
            # v5.2 — Catalogue fournisseur : format prix + unité colis
            "ALTER TABLE catalogue_fournisseur ADD COLUMN format_prix TEXT DEFAULT 'kg'",
            "ALTER TABLE catalogue_fournisseur ADD COLUMN unite_colis TEXT",
            # v5.3 — Catalogue fournisseur : conditionnement chiffré pour calcul du coût
            # qte_par_colis et poids_unitaire_kg = données brutes saisies.
            # poids_colis_kg = calculé (qte_par_colis × poids_unitaire_kg) côté code.
            "ALTER TABLE catalogue_fournisseur ADD COLUMN qte_par_colis REAL",
            "ALTER TABLE catalogue_fournisseur ADD COLUMN poids_unitaire_kg REAL",
            "ALTER TABLE catalogue_fournisseur ADD COLUMN poids_colis_kg REAL",
            # v5.0 — reception_lignes : lien vers catalogue fournisseur + date abattage carcasses
            "ALTER TABLE reception_lignes ADD COLUMN catalogue_fournisseur_id INTEGER REFERENCES catalogue_fournisseur(id)",
            "ALTER TABLE reception_lignes ADD COLUMN date_abattage DATE",
            # v5.0 — nouvelles tables module Achats (idempotent via SCHEMA_SQL)
            """CREATE TABLE IF NOT EXISTS catalogue_fournisseur (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                fournisseur_id   INTEGER NOT NULL,
                code_article     TEXT    NOT NULL,
                designation      TEXT    NOT NULL,
                prix_achat_ht    REAL    NOT NULL DEFAULT 0.0,
                tva_percent      REAL    DEFAULT 5.5,
                conditionnement  TEXT,
                dlc_type         TEXT    DEFAULT 'dlc',
                dlc_jours        INTEGER,
                actif            INTEGER DEFAULT 1,
                date_maj         DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id),
                UNIQUE(fournisseur_id, code_article)
            )""",
            """CREATE TABLE IF NOT EXISTS commandes (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                boutique_id           INTEGER NOT NULL DEFAULT 1,
                fournisseur_id        INTEGER NOT NULL,
                numero_commande       TEXT    UNIQUE,
                date_commande         DATE    NOT NULL DEFAULT CURRENT_DATE,
                date_livraison_prevue DATE,
                statut                TEXT    NOT NULL DEFAULT 'brouillon',
                montant_total_ht      REAL    DEFAULT 0.0,
                commentaire           TEXT,
                personnel_id          INTEGER,
                date_envoi_mail       DATETIME,
                created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (boutique_id)    REFERENCES boutiques(id),
                FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id),
                FOREIGN KEY (personnel_id)   REFERENCES personnel(id)
            )""",
            """CREATE TABLE IF NOT EXISTS commande_lignes (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                commande_id              INTEGER NOT NULL,
                catalogue_fournisseur_id INTEGER,
                code_article             TEXT    NOT NULL,
                designation              TEXT    NOT NULL,
                prix_unitaire_ht         REAL    NOT NULL DEFAULT 0.0,
                quantite_commandee       REAL    NOT NULL,
                unite                    TEXT    NOT NULL DEFAULT 'kg',
                montant_ht               REAL    DEFAULT 0.0,
                commentaire_ligne        TEXT,
                created_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (commande_id)              REFERENCES commandes(id) ON DELETE CASCADE,
                FOREIGN KEY (catalogue_fournisseur_id) REFERENCES catalogue_fournisseur(id)
            )""",
            """CREATE TABLE IF NOT EXISTS commande_receptions_mapping (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                commande_id  INTEGER NOT NULL,
                reception_id INTEGER NOT NULL,
                date_liaison DATETIME DEFAULT CURRENT_TIMESTAMP,
                personnel_id INTEGER,
                FOREIGN KEY (commande_id)  REFERENCES commandes(id),
                FOREIGN KEY (reception_id) REFERENCES receptions(id),
                FOREIGN KEY (personnel_id) REFERENCES personnel(id),
                UNIQUE(commande_id, reception_id)
            )""",
            """CREATE TABLE IF NOT EXISTS panier_lignes (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                boutique_id              INTEGER NOT NULL DEFAULT 1,
                catalogue_fournisseur_id INTEGER,
                fournisseur_id           INTEGER NOT NULL,
                fournisseur_nom          TEXT    NOT NULL,
                code_article             TEXT    NOT NULL,
                designation              TEXT    NOT NULL,
                quantite                 REAL    NOT NULL DEFAULT 1.0,
                unite                    TEXT    NOT NULL DEFAULT 'kg',
                prix_ht                  REAL    NOT NULL DEFAULT 0.0,
                created_at               DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fournisseur_id)           REFERENCES fournisseurs(id),
                FOREIGN KEY (catalogue_fournisseur_id) REFERENCES catalogue_fournisseur(id)
            )""",
            """CREATE TABLE IF NOT EXISTS maturation_carcasses (
                id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                reception_ligne_id     INTEGER NOT NULL,
                numero_lot             TEXT    NOT NULL,
                date_abattage          DATE    NOT NULL,
                date_dernier_controle  DATE,
                etat_controle          TEXT,
                aspect                 TEXT,
                odeur                  TEXT,
                dessiccation           TEXT,
                poissage               TEXT,
                parage_effectue        INTEGER DEFAULT 0,
                commentaire_controle   TEXT,
                decision_humaine       TEXT,
                date_prochain_controle DATE,
                personnel_id           INTEGER,
                created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reception_ligne_id) REFERENCES reception_lignes(id),
                FOREIGN KEY (personnel_id)       REFERENCES personnel(id)
            )""",
            # v5.4 — Produits en attente de complétion (lot/DLC manquant à la réception).
            # statut='en_attente' → le produit n'entre PAS en stock tant que lot/DLC non saisis.
            "ALTER TABLE reception_lignes ADD COLUMN statut TEXT DEFAULT 'complet'",
            "ALTER TABLE reception_lignes ADD COLUMN dlc_type TEXT",        # 'dlc' | 'date_abattage' | 'no_dlc'
            "ALTER TABLE reception_lignes ADD COLUMN attente_motif TEXT",   # 'lot' | 'dlc' | 'lot_dlc' | 'produit'
            "CREATE INDEX IF NOT EXISTS idx_reception_lignes_statut ON reception_lignes(statut)",
            # v5.5 — Réception basée sur le catalogue achats : produit interne facultatif.
            # designation_libre = libellé de l'article catalogue fournisseur quand aucun
            # produit interne (table produits) n'est rattaché (produit_id NULL).
            "ALTER TABLE reception_lignes ADD COLUMN designation_libre TEXT",
            # v5.6 — produit_id devient nullable dans reception_lignes.
            # La migration d'origine (refonte v2.2) créait la table avec NOT NULL,
            # ce qui bloque les réceptions sans produit interne (catalogue achats).
            # SQLite ne supporte pas ALTER COLUMN → recréation complète de la table.
            """CREATE TABLE IF NOT EXISTS reception_lignes_v56 (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    reception_id              INTEGER NOT NULL,
    produit_id                INTEGER,
    catalogue_fournisseur_id  INTEGER,
    fournisseur_id            INTEGER,
    fournisseur_nom           TEXT,
    numero_lot                TEXT,
    lot_interne               INTEGER DEFAULT 0,
    dlc                       DATE,
    dluo                      DATE,
    date_abattage             DATE,
    dlc_type                  TEXT,
    statut                    TEXT    DEFAULT 'complet',
    attente_motif             TEXT,
    designation_libre         TEXT,
    origine                   TEXT    DEFAULT 'France',
    poids_kg                  REAL,
    temperature_reception     REAL,
    temperature_conforme      INTEGER,
    temperature_coeur         REAL,
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
    FOREIGN KEY (reception_id)             REFERENCES receptions(id),
    FOREIGN KEY (produit_id)               REFERENCES produits(id),
    FOREIGN KEY (catalogue_fournisseur_id) REFERENCES catalogue_fournisseur(id),
    FOREIGN KEY (fournisseur_id)           REFERENCES fournisseurs(id)
)""",
            """INSERT OR IGNORE INTO reception_lignes_v56
    SELECT id, reception_id, produit_id, catalogue_fournisseur_id,
           fournisseur_id, fournisseur_nom, numero_lot, lot_interne,
           dlc, dluo, date_abattage, dlc_type, statut, attente_motif,
           designation_libre, origine, poids_kg, temperature_reception,
           temperature_conforme, temperature_coeur,
           couleur_conforme, couleur_observation,
           consistance_conforme, consistance_observation,
           exsudat_conforme, exsudat_observation,
           odeur_conforme, odeur_observation,
           ph_valeur, ph_conforme, conforme, created_at
    FROM reception_lignes
    WHERE typeof(reception_lignes.id) = 'integer'""",
            "DROP TABLE IF EXISTS reception_lignes",
            "ALTER TABLE reception_lignes_v56 RENAME TO reception_lignes",
            "CREATE INDEX IF NOT EXISTS idx_reception_lignes_statut ON reception_lignes(statut)",
        ]
        for sql in migrations:
            try:
                await db.execute(sql)
            except Exception:
                pass

        # Migration v3.5 — baseline historique du statut réception
        # ALTER TABLE remplit les lignes existantes avec 'en_cours' (default),
        # mais ces réceptions sont historiques et doivent être considérées clôturées.
        # Heuristique idempotente : si aucune réception n'a encore le statut 'cloturee',
        # on suppose qu'on vient d'ajouter la colonne → on marque tout le baseline.
        # Une fois exécutée, la condition est fausse et la migration ne tourne plus.
        try:
            cur_check = await db.execute("PRAGMA table_info(receptions)")
            cols_check = {row[1] for row in await cur_check.fetchall()}
            if 'statut' in cols_check:
                cur_count = await db.execute(
                    "SELECT "
                    "  (SELECT COUNT(*) FROM receptions) AS total, "
                    "  (SELECT COUNT(*) FROM receptions WHERE statut = 'cloturee') AS cloturee"
                )
                counts = await cur_count.fetchone()
                if counts and counts[0] > 0 and counts[1] == 0:
                    await db.execute("UPDATE receptions SET statut = 'cloturee'")
                    await db.commit()
                    logger.info(
                        "Migration v3.5 : %d réception(s) historique(s) "
                        "marquée(s) comme clôturée(s)",
                        counts[0],
                    )
        except Exception as e:
            logger.warning("Migration v3.5 statut réception : %s", e)

        # Migration v4.2 : backfill personnel_id depuis l'ancien prénom TEXT.
        # Idempotent : ne remplit que les lignes où personnel_id est encore NULL.
        # Le match se fait sur personnel.prenom (insensible à la casse / espaces).
        try:
            backfills = [
                ("registre_nettoyage", "operateur", True),
                ("etalonnages",        "operateur", False),  # pas de boutique_id
                ("tache_validations",  "operateur", True),
                ("nuisibles_controles", "visa",     True),
            ]
            for table, col_texte, a_boutique in backfills:
                # Vérifier que la colonne personnel_id existe bien (ALTER a pu déjà passer)
                cur_cols = await db.execute(f"PRAGMA table_info({table})")
                cols_t = {row[1] for row in await cur_cols.fetchall()}
                if "personnel_id" not in cols_t or col_texte not in cols_t:
                    continue
                if a_boutique:
                    await db.execute(
                        f"""
                        UPDATE {table}
                        SET personnel_id = (
                            SELECT p.id FROM personnel p
                            WHERE p.boutique_id = {table}.boutique_id
                              AND LOWER(TRIM(p.prenom)) = LOWER(TRIM({table}.{col_texte}))
                            LIMIT 1
                        )
                        WHERE personnel_id IS NULL
                          AND {col_texte} IS NOT NULL AND TRIM({col_texte}) <> ''
                        """
                    )
                else:
                    await db.execute(
                        f"""
                        UPDATE {table}
                        SET personnel_id = (
                            SELECT p.id FROM personnel p
                            WHERE LOWER(TRIM(p.prenom)) = LOWER(TRIM({table}.{col_texte}))
                            LIMIT 1
                        )
                        WHERE personnel_id IS NULL
                          AND {col_texte} IS NOT NULL AND TRIM({col_texte}) <> ''
                        """
                    )
            await db.commit()
            logger.info("Migration v4.2 : backfill personnel_id terminé")
        except Exception as e:
            logger.warning("Migration v4.2 backfill personnel_id : %s", e)

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

        # Migration v5.0 : rendre produit_id nullable dans reception_lignes
        # Nécessaire pour que la réception puisse être liée au catalogue fournisseur
        # sans produit interne obligatoire.
        try:
            cur_rl = await db.execute("PRAGMA table_info(reception_lignes)")
            cols_rl = await cur_rl.fetchall()
            produit_col = next((c for c in cols_rl if c[1] == 'produit_id'), None)
            if produit_col and produit_col[3] == 1:  # notnull == 1 → on doit migrer
                logger.info("Migration v5.0 : produit_id rendu nullable dans reception_lignes")
                await db.execute("PRAGMA foreign_keys = OFF")
                await db.execute("DROP TABLE IF EXISTS reception_lignes_new")
                await db.execute("""
                    CREATE TABLE reception_lignes_new (
                        id                        INTEGER PRIMARY KEY AUTOINCREMENT,
                        reception_id              INTEGER NOT NULL,
                        produit_id                INTEGER,
                        catalogue_fournisseur_id  INTEGER,
                        fournisseur_id            INTEGER,
                        fournisseur_nom           TEXT,
                        numero_lot                TEXT,
                        dlc                       DATE,
                        dluo                      DATE,
                        date_abattage             DATE,
                        origine                   TEXT    DEFAULT 'France',
                        poids_kg                  REAL,
                        temperature_reception     REAL,
                        temperature_conforme      INTEGER,
                        temperature_coeur         REAL,
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
                        lot_interne               INTEGER DEFAULT 0,
                        created_at                DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (reception_id)             REFERENCES receptions(id),
                        FOREIGN KEY (produit_id)               REFERENCES produits(id),
                        FOREIGN KEY (catalogue_fournisseur_id) REFERENCES catalogue_fournisseur(id),
                        FOREIGN KEY (fournisseur_id)           REFERENCES fournisseurs(id)
                    )
                """)
                # Déterminer les colonnes existantes pour le SELECT
                existing_cols = {c[1] for c in cols_rl}
                fournisseur_nom_sel  = "fournisseur_nom"  if "fournisseur_nom"  in existing_cols else "NULL"
                temperature_coeur_sel = "temperature_coeur" if "temperature_coeur" in existing_cols else "NULL"
                lot_interne_sel      = "lot_interne"      if "lot_interne"      in existing_cols else "0"
                date_abattage_sel    = "date_abattage"    if "date_abattage"    in existing_cols else "NULL"
                cat_fourn_sel        = "catalogue_fournisseur_id" if "catalogue_fournisseur_id" in existing_cols else "NULL"
                await db.execute(f"""
                    INSERT INTO reception_lignes_new
                        SELECT id, reception_id, produit_id,
                               {cat_fourn_sel},
                               fournisseur_id, {fournisseur_nom_sel},
                               numero_lot, dlc, dluo, {date_abattage_sel},
                               origine, poids_kg,
                               temperature_reception, temperature_conforme, {temperature_coeur_sel},
                               couleur_conforme, couleur_observation,
                               consistance_conforme, consistance_observation,
                               exsudat_conforme, exsudat_observation,
                               odeur_conforme, odeur_observation,
                               ph_valeur, ph_conforme, conforme, {lot_interne_sel},
                               created_at
                        FROM reception_lignes
                """)
                await db.execute("DROP TABLE reception_lignes")
                await db.execute("ALTER TABLE reception_lignes_new RENAME TO reception_lignes")
                await db.execute("PRAGMA foreign_keys = ON")
                logger.info("Migration v5.0 : reception_lignes migrée avec produit_id nullable")
        except Exception as e:
            logger.warning("Migration v5.0 reception_lignes : %s", e)
            await db.execute("PRAGMA foreign_keys = ON")

        # Migration v3.0 : refonte table etalonnages
        # (thermometre_id TEXT → thermometre_ref_id INTEGER FK vers thermometres_ref)
        try:
            cur_et = await db.execute("PRAGMA table_info(etalonnages)")
            cols_et = {row[1] for row in await cur_et.fetchall()}
            if "thermometre_id" in cols_et and "thermometre_ref_id" not in cols_et:
                logger.info("Migration v3.0 : refonte table etalonnages")
                await db.execute("DROP TABLE IF EXISTS etalonnages")
                await db.execute("""
                    CREATE TABLE etalonnages (
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
                    )
                """)
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_etalonnages_date ON etalonnages(date_etalonnage)"
                )
                logger.info("Migration v3.0 : table etalonnages recrée avec thermometre_ref_id")
        except Exception as e:
            logger.warning("Migration v3.0 etalonnages : %s", e)

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
             seuil_temp_min, seuil_temp_max, seuil_hum_max,
             delai_alerte_minutes, delai_perte_signal_minutes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["boutique_id"],
            data["nom"],
            data["type"],
            data.get("sonde_zigbee_id"),
            data.get("seuil_temp_min", 0.0),
            data.get("seuil_temp_max", 4.0),
            data.get("seuil_hum_max", 90.0),
            data.get("delai_alerte_minutes", 30),
            data.get("delai_perte_signal_minutes", 720),
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
            "delai_alerte_minutes", "delai_perte_signal_minutes", "actif",
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


async def update_destinataire(db: aiosqlite.Connection, dest_id: int, data: dict) -> bool:
    cursor = await db.execute(
        "UPDATE destinataires SET nom=?, email=?, telephone=? WHERE id=? AND actif=1",
        (data["nom"], data.get("email"), data.get("telephone"), dest_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def delete_destinataire(db: aiosqlite.Connection, dest_id: int) -> bool:
    cursor = await db.execute(
        "UPDATE destinataires SET actif=0 WHERE id=?",
        (dest_id,),
    )
    await db.commit()
    return cursor.rowcount > 0


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
    inclure_inactifs: bool = False,
) -> list[dict]:
    where = ["boutique_id = ?"]
    params: list = [boutique_id]
    if not inclure_inactifs:
        where.append("actif = 1")
    if type_produit:
        where.append("type_produit = ?")
        params.append(type_produit)
    sql = f"SELECT * FROM produits WHERE {' AND '.join(where)} ORDER BY nom"
    cursor = await db.execute(sql, params)
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_produit(db: aiosqlite.Connection, produit_id: int) -> Optional[dict]:
    cursor = await db.execute("SELECT * FROM produits WHERE id = ?", (produit_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


PRODUIT_COLONNES_EDITABLES = (
    "nom", "code_unique", "espece", "etape", "coupe_niveau",
    "conditionnement", "categorie", "dlc_jours", "temperature_conservation",
    "format_etiquette", "type_produit", "actif",
)


async def create_produit(db: aiosqlite.Connection, data: dict) -> int:
    colonnes = ["boutique_id"] + [c for c in PRODUIT_COLONNES_EDITABLES if c in data]
    valeurs = [data["boutique_id"]] + [data[c] for c in colonnes if c != "boutique_id"]
    placeholders = ", ".join("?" for _ in colonnes)
    cursor = await db.execute(
        f"INSERT INTO produits ({', '.join(colonnes)}) VALUES ({placeholders})",
        valeurs,
    )
    await db.commit()
    return cursor.lastrowid


async def update_produit(db: aiosqlite.Connection, produit_id: int, data: dict) -> bool:
    fields = {k: v for k, v in data.items() if k in PRODUIT_COLONNES_EDITABLES}
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
             info_complementaire, mode_impression, source_type, source_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            data.get("source_type"),
            data.get("source_id"),
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


def _calc_statut_attente(data: dict) -> tuple[str, Optional[str]]:
    """Détermine si une ligne de réception est complète ou en attente de traçabilité.

    Un produit est mis « en_attente » s'il manque le N° de lot et/ou la date selon
    son dlc_type. Tant qu'il est en attente, il n'entre pas au stock (filtré dans
    get_stock_unifie). Renvoie (statut, attente_motif).

    dlc_type :
        'no_dlc'        → aucune date requise
        'date_abattage' → date d'abattage requise (carcasses en maturation)
        'dlc' / None    → DLC ou DLUO requise
    """
    dlc_type = data.get("dlc_type")
    manque_lot = not (data.get("numero_lot") or "").strip()

    if dlc_type == "no_dlc":
        manque_date = False
    elif dlc_type == "date_abattage":
        manque_date = not data.get("date_abattage")
    else:  # 'dlc' ou inconnu
        manque_date = not (data.get("dlc") or data.get("dluo"))

    if manque_lot and manque_date:
        return "en_attente", "lot_dlc"
    if manque_lot:
        return "en_attente", "lot"
    if manque_date:
        return "en_attente", "dlc"
    return "complet", None


async def add_reception_ligne(db: aiosqlite.Connection, reception_id: int, data: dict) -> int:
    """Ajoute une ligne produit à une réception avec calcul automatique de conformité."""
    # Récupérer la réception pour savoir si le camion était conforme
    cur = await db.execute(
        "SELECT temperature_camion FROM receptions WHERE id = ?", (reception_id,)
    )
    rec_row = await cur.fetchone()
    temp_camion = rec_row["temperature_camion"] if rec_row else None

    # Récupérer temperature_conservation du produit interne (facultatif).
    # En réception basée sur le catalogue achats, produit_id peut être NULL :
    # la ligne reste valable, identifiée par designation_libre + catalogue_fournisseur_id.
    produit_id = data.get("produit_id")
    temp_conservation = None
    if produit_id:
        cur2 = await db.execute(
            "SELECT temperature_conservation FROM produits WHERE id = ?", (produit_id,)
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

    # Statut traçabilité : en_attente si lot/DLC manquant → exclu du stock
    statut, attente_motif = _calc_statut_attente(data)

    cursor = await db.execute(
        """
        INSERT INTO reception_lignes
            (reception_id, produit_id, catalogue_fournisseur_id, fournisseur_id, fournisseur_nom, numero_lot, lot_interne, dlc, dluo,
             date_abattage, dlc_type, statut, attente_motif, designation_libre,
             origine, poids_kg, temperature_reception, temperature_conforme,
             temperature_coeur,
             couleur_conforme, couleur_observation,
             consistance_conforme, consistance_observation,
             exsudat_conforme, exsudat_observation,
             odeur_conforme, odeur_observation,
             ph_valeur, ph_conforme, conforme)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reception_id,
            produit_id,
            data.get("catalogue_fournisseur_id"),
            data.get("fournisseur_id"),
            data.get("fournisseur_nom"),
            data.get("numero_lot"),
            int(data.get("lot_interne", 0)),
            data.get("dlc"),
            data.get("dluo"),
            data.get("date_abattage"),
            data.get("dlc_type"),
            statut,
            attente_motif,
            data.get("designation_libre"),
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

    # Une NC propreté camion rend la réception non conforme même sans NC produit
    cur_cam = await db.execute(
        "SELECT camion_conforme, proprete_camion FROM receptions WHERE id = ?",
        (reception_id,),
    )
    row_cam = await cur_cam.fetchone()
    camion_nc = bool(row_cam) and (
        row_cam[0] == 0 or (row_cam[1] and row_cam[1] != "satisfaisant")
    )

    conformite_globale = "non_conforme" if (nb_nc > 0 or camion_nc) else "conforme"

    await db.execute(
        """
        UPDATE receptions
        SET conformite_globale = ?, livraison_refusee = ?,
            information_ddpp = ?, commentaire_nc = ?,
            statut = 'cloturee'
        WHERE id = ?
        """,
        (conformite_globale, int(livraison_refusee),
         int(information_ddpp), commentaire_nc, reception_id),
    )

    # Marquer « livrée » les commandes liées à cette réception — uniquement à la
    # clôture (et pas si la livraison a été refusée). Le simple lien créé à
    # l'étape « Créer la fiche » ne suffit plus à passer la commande en livrée.
    if not livraison_refusee:
        await db.execute(
            """
            UPDATE commandes
            SET statut = 'livree'
            WHERE id IN (
                SELECT commande_id FROM commande_receptions_mapping
                WHERE reception_id = ?
            )
            AND statut != 'annulee'
            """,
            (reception_id,),
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
    # Récupérer la ligne existante (valeurs de traçabilité à conserver si non fournies)
    cur = await db.execute(
        "SELECT reception_id, produit_id, numero_lot, dlc, dluo, date_abattage, dlc_type "
        "FROM reception_lignes WHERE id = ?", (ligne_id,)
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

    # Traçabilité : fusionner avec l'existant (une complétion partielle ne doit pas
    # écraser une valeur déjà saisie), puis recalculer le statut en_attente/complet.
    def _merge(key: str):
        v = data.get(key)
        if v is None or (isinstance(v, str) and not v.strip()):
            return row[key]
        return v

    numero_lot    = _merge("numero_lot")
    dlc           = _merge("dlc")
    dluo          = _merge("dluo")
    date_abattage = _merge("date_abattage")
    dlc_type      = _merge("dlc_type")

    statut, attente_motif = _calc_statut_attente({
        "numero_lot":    numero_lot,
        "dlc":           dlc,
        "dluo":          dluo,
        "date_abattage": date_abattage,
        "dlc_type":      dlc_type,
    })

    await db.execute(
        """
        UPDATE reception_lignes SET
            produit_id = ?, fournisseur_id = ?, numero_lot = ?, lot_interne = ?,
            dlc = ?, dluo = ?, date_abattage = ?, dlc_type = ?,
            statut = ?, attente_motif = ?,
            origine = ?, poids_kg = ?,
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
            numero_lot,
            int(data.get("lot_interne", 0)),
            dlc,
            dluo,
            date_abattage,
            dlc_type,
            statut,
            attente_motif,
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


async def get_lignes_en_attente(db: aiosqlite.Connection) -> list[dict]:
    """Liste les lignes de réception en attente de complétion (lot/DLC manquant).

    Ces produits ne sont PAS encore en stock. Renvoie de quoi les afficher et les
    compléter : produit, fournisseur, réception (date/heure/n°), motif manquant.
    """
    cur = await db.execute(
        """
        SELECT
            rl.id              AS ligne_id,
            rl.reception_id    AS reception_id,
            rl.numero_lot      AS numero_lot,
            rl.dlc             AS dlc,
            rl.dluo            AS dluo,
            rl.date_abattage   AS date_abattage,
            rl.dlc_type        AS dlc_type,
            rl.attente_motif   AS attente_motif,
            rl.poids_kg        AS poids_kg,
            rl.origine         AS origine,
            p.id               AS produit_id,
            COALESCE(p.nom, cf.designation, rl.designation_libre) AS produit_nom,
            p.code_unique      AS code_unique,
            COALESCE(f.nom, rl.fournisseur_nom) AS fournisseur_nom,
            r.date_reception   AS date_reception,
            r.heure_reception  AS heure_reception,
            r.statut           AS reception_statut
        FROM reception_lignes rl
        JOIN receptions   r ON r.id = rl.reception_id
        LEFT JOIN produits     p ON p.id = rl.produit_id
        LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
        LEFT JOIN fournisseurs f ON f.id = rl.fournisseur_id
        WHERE COALESCE(rl.statut, 'complet') = 'en_attente'
        ORDER BY r.date_reception DESC, r.heure_reception DESC, rl.id DESC
        """
    )
    return [dict(r) for r in await cur.fetchall()]


async def count_lignes_en_attente(db: aiosqlite.Connection) -> int:
    """Nombre de lignes de réception en attente de complétion (pour le Hub)."""
    cur = await db.execute(
        "SELECT COUNT(*) FROM reception_lignes "
        "WHERE COALESCE(statut, 'complet') = 'en_attente'"
    )
    row = await cur.fetchone()
    return row[0] if row else 0


async def completer_ligne_attente(
    db: aiosqlite.Connection,
    ligne_id: int,
    numero_lot: Optional[str] = None,
    dlc: Optional[str] = None,
    dluo: Optional[str] = None,
    date_abattage: Optional[str] = None,
) -> Optional[dict]:
    """Complète les infos de traçabilité d'une ligne en attente et recalcule le statut.

    Ne touche qu'aux champs lot/DLC/DLUO/date_abattage (préserve conformité et
    observations). Si lot + date sont désormais présents, statut repasse à 'complet'
    et le produit entre en stock. Renvoie la ligne mise à jour, ou None si introuvable.
    """
    cur = await db.execute(
        "SELECT numero_lot, dlc, dluo, date_abattage, dlc_type "
        "FROM reception_lignes WHERE id = ?", (ligne_id,)
    )
    row = await cur.fetchone()
    if not row:
        return None

    def _pick(new, old):
        if new is None or (isinstance(new, str) and not new.strip()):
            return old
        return new

    numero_lot    = _pick(numero_lot, row["numero_lot"])
    dlc           = _pick(dlc, row["dlc"])
    dluo          = _pick(dluo, row["dluo"])
    date_abattage = _pick(date_abattage, row["date_abattage"])
    dlc_type      = row["dlc_type"]

    statut, attente_motif = _calc_statut_attente({
        "numero_lot":    numero_lot,
        "dlc":           dlc,
        "dluo":          dluo,
        "date_abattage": date_abattage,
        "dlc_type":      dlc_type,
    })

    await db.execute(
        """
        UPDATE reception_lignes SET
            numero_lot = ?, dlc = ?, dluo = ?, date_abattage = ?,
            statut = ?, attente_motif = ?
        WHERE id = ?
        """,
        (numero_lot, dlc, dluo, date_abattage, statut, attente_motif, ligne_id),
    )
    await db.commit()

    cur2 = await db.execute("SELECT * FROM reception_lignes WHERE id = ?", (ligne_id,))
    updated = await cur2.fetchone()
    return dict(updated) if updated else None


async def update_reception_temperature_camion(
    db: aiosqlite.Connection,
    reception_id: int,
    new_temp: Optional[float],
) -> Optional[list[dict]]:
    """Met à jour la temp camion ET propage aux lignes (recalcule conformité).

    Renvoie la liste des lignes mises à jour, ou None si la réception n'existe pas.
    """
    cur = await db.execute("SELECT id FROM receptions WHERE id = ?", (reception_id,))
    if not await cur.fetchone():
        return None

    await db.execute(
        "UPDATE receptions SET temperature_camion = ? WHERE id = ?",
        (new_temp, reception_id),
    )

    cur2 = await db.execute(
        """
        SELECT rl.id, rl.produit_id, rl.ph_conforme,
               rl.couleur_conforme, rl.consistance_conforme,
               rl.exsudat_conforme, rl.odeur_conforme,
               p.temperature_conservation
        FROM reception_lignes rl
        LEFT JOIN produits p ON p.id = rl.produit_id
        WHERE rl.reception_id = ?
        """,
        (reception_id,),
    )
    rows = await cur2.fetchall()

    for r in rows:
        temp_conforme = _calc_temperature_conforme(new_temp, r["temperature_conservation"])
        conforme = 1
        for flag in (temp_conforme, r["ph_conforme"],
                     r["couleur_conforme"], r["consistance_conforme"],
                     r["exsudat_conforme"], r["odeur_conforme"]):
            if flag is not None and flag == 0:
                conforme = 0
                break
        await db.execute(
            """
            UPDATE reception_lignes
               SET temperature_reception = ?,
                   temperature_conforme  = ?,
                   conforme              = ?
             WHERE id = ?
            """,
            (new_temp, temp_conforme, conforme, r["id"]),
        )

    await db.commit()

    cur3 = await db.execute(
        "SELECT * FROM reception_lignes WHERE reception_id = ? ORDER BY id",
        (reception_id,),
    )
    updated = await cur3.fetchall()
    return [dict(row) for row in updated]


async def get_receptions(
    db: aiosqlite.Connection,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    fournisseur_id: Optional[int] = None,
    fournisseur_nom: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    conditions = ["r.statut = 'cloturee'"]
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
    if fournisseur_nom and fournisseur_nom.strip():
        # Match les réceptions liées à ce fournisseur via id ou champs texte libre,
        # côté en-tête (receptions) ou côté lignes (reception_lignes).
        nom = fournisseur_nom.strip()
        conditions.append(
            "("
            "  COALESCE("
            "    (SELECT f1.nom FROM fournisseurs f1 WHERE f1.id = r.fournisseur_principal_id),"
            "    r.fournisseur_nom"
            "  ) LIKE ? COLLATE NOCASE"
            "  OR EXISTS ("
            "    SELECT 1 FROM reception_lignes rl3"
            "    LEFT JOIN fournisseurs f3 ON f3.id = rl3.fournisseur_id"
            "    WHERE rl3.reception_id = r.id"
            "      AND COALESCE(f3.nom, rl3.fournisseur_nom) LIKE ? COLLATE NOCASE"
            "  )"
            ")"
        )
        params.extend([nom, nom])
    if q:
        # Filtre les réceptions dont au moins une ligne contient un produit
        # ou un N° de lot correspondant (recherche insensible à la casse, sous-chaîne).
        like = f"%{q.strip()}%"
        conditions.append(
            "EXISTS ("
            "  SELECT 1 FROM reception_lignes rl2 "
            "  LEFT JOIN produits pr2 ON pr2.id = rl2.produit_id "
            "  WHERE rl2.reception_id = r.id "
            "    AND (pr2.nom LIKE ? COLLATE NOCASE "
            "         OR rl2.numero_lot LIKE ? COLLATE NOCASE)"
            ")"
        )
        params.extend([like, like])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    cursor = await db.execute(
        f"""
        SELECT
            r.*,
            TRIM(p.prenom || ' ' || COALESCE(p.nom, '')) AS personnel_prenom,
            COALESCE(f.nom, r.fournisseur_nom) AS fournisseur_nom,
            COUNT(rl.id)        AS nb_lignes,
            SUM(CASE WHEN rl.conforme = 0 THEN 1 ELSE 0 END) AS nb_nc,
            (
                SELECT GROUP_CONCAT(COALESCE(fs.nom, rb.fournisseur_nom), '||')
                FROM reception_bls_supplementaires rb
                LEFT JOIN fournisseurs fs ON fs.id = rb.fournisseur_id
                WHERE rb.reception_id = r.id
            ) AS bls_supp_noms_concat,
            (
                SELECT COUNT(*) FROM reception_bls_supplementaires rb2
                WHERE rb2.reception_id = r.id
            ) AS nb_bls_supp
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
    out = []
    for r in rows:
        d = dict(r)
        concat = d.pop("bls_supp_noms_concat", None)
        d["bls_supplementaires_noms"] = (
            [n for n in concat.split("||") if n] if concat else []
        )
        out.append(d)
    return out


async def get_reception(db: aiosqlite.Connection, reception_id: int) -> Optional[dict]:
    cursor = await db.execute(
        """
        SELECT r.*,
               TRIM(p.prenom || ' ' || COALESCE(p.nom, '')) AS personnel_prenom,
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
               COALESCE(pr.nom, cf.designation, rl.designation_libre) AS produit_nom,
               pr.espece,
               COALESCE(fv.nom, rl.fournisseur_nom) AS fournisseur_nom
        FROM reception_lignes rl
        LEFT JOIN produits     pr ON pr.id = rl.produit_id
        LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
        LEFT JOIN fournisseurs fv ON fv.id = rl.fournisseur_id
        WHERE rl.reception_id = ?
        ORDER BY rl.id
        """,
        (reception_id,),
    )
    lignes = await cur2.fetchall()
    reception["lignes"] = [dict(l) for l in lignes]

    # BLs supplémentaires (cas refus livraison multi-fournisseur)
    cur3 = await db.execute(
        """
        SELECT b.id, b.reception_id, b.fournisseur_id, b.photo_bl_filename, b.ordre,
               COALESCE(f.nom, b.fournisseur_nom) AS fournisseur_nom
        FROM reception_bls_supplementaires b
        LEFT JOIN fournisseurs f ON f.id = b.fournisseur_id
        WHERE b.reception_id = ?
        ORDER BY b.ordre, b.id
        """,
        (reception_id,),
    )
    bls = await cur3.fetchall()
    reception["bls_supplementaires"] = [dict(b) for b in bls]
    return reception


async def add_reception_bl_supplementaire(
    db: aiosqlite.Connection,
    reception_id: int,
    data: dict,
) -> int:
    """Ajoute un BL supplémentaire à une réception (refus livraison multi-fournisseur)."""
    cur = await db.execute(
        "SELECT COALESCE(MAX(ordre), 0) + 1 AS o FROM reception_bls_supplementaires WHERE reception_id = ?",
        (reception_id,),
    )
    row = await cur.fetchone()
    ordre = row["o"] if row else 1
    cursor = await db.execute(
        """
        INSERT INTO reception_bls_supplementaires
            (reception_id, fournisseur_id, fournisseur_nom, photo_bl_filename, ordre)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            reception_id,
            data.get("fournisseur_id"),
            data.get("fournisseur_nom"),
            data.get("photo_bl_filename"),
            ordre,
        ),
    )
    await db.commit()
    return cursor.lastrowid


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
        "INSERT INTO personnel (boutique_id, prenom, nom) VALUES (?, ?, ?)",
        (data["boutique_id"], data["prenom"], data.get("nom")),
    )
    await db.commit()
    return cursor.lastrowid


async def update_personnel(db: aiosqlite.Connection, personnel_id: int, data: dict) -> bool:
    fields = {k: v for k, v in data.items() if k in ("prenom", "nom", "actif")}
    if not fields:
        return False

    # Si le prénom change, propager dans les tables qui stockent l'opérateur en TEXT
    ancien_prenom = None
    nouveau_prenom = fields.get("prenom")
    if nouveau_prenom:
        cursor = await db.execute(
            "SELECT prenom, boutique_id FROM personnel WHERE id = ?", (personnel_id,)
        )
        row = await cursor.fetchone()
        if row and row["prenom"] != nouveau_prenom:
            ancien_prenom = row["prenom"]
            boutique_id = row["boutique_id"]

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [personnel_id]
    await db.execute(f"UPDATE personnel SET {set_clause} WHERE id = ?", values)

    # Propager le changement de prénom dans les tables qui stockent encore l'opérateur
    # en TEXT brut (sans FK personnel_id). Les modules nettoyage/étalonnage/tâches/nuisibles
    # lisent désormais le nom via la FK personnel_id, donc n'ont plus besoin de propagation.
    if ancien_prenom is not None:
        for table in ("etiquettes_generees", "non_conformites_fournisseur"):
            await db.execute(
                f"UPDATE {table} SET operateur = ? WHERE operateur = ? AND boutique_id = ?",
                (nouveau_prenom, ancien_prenom, boutique_id),
            )

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

    # Résout le prénom courant pour la colonne operateur (compat historique)
    personnel_id = data["personnel_id"]
    cur_p = await db.execute("SELECT prenom FROM personnel WHERE id = ?", (personnel_id,))
    prow = await cur_p.fetchone()
    if not prow:
        raise ValueError("Personnel introuvable")
    operateur = prow["prenom"]

    cursor = await db.execute(
        """
        INSERT INTO tache_validations
            (boutique_id, tache_type_id, operateur, personnel_id, date_tache,
             conforme, photo_path, commentaire, donnees_specifiques)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["boutique_id"],
            data["tache_type_id"],
            operateur,
            personnel_id,
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
        SELECT v.*, t.code, t.libelle,
               COALESCE(TRIM(p.prenom || ' ' || COALESCE(p.nom, '')), v.operateur) AS operateur_nom
        FROM tache_validations v
        JOIN tache_types t ON t.id = v.tache_type_id
        LEFT JOIN personnel p ON p.id = v.personnel_id
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
        # Affichage : nom courant (prénom + nom) via la FK, fallback ancien operateur TEXT
        if d.get("operateur_nom"):
            d["operateur"] = d["operateur_nom"]
        d.pop("operateur_nom", None)
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
            COALESCE(NULLIF(fi.fournisseur_nom, ''), f.nom) AS fournisseur_nom,
            p.nom  AS produit_nom,
            rl.origine AS origine,
            TRIM(per.prenom || ' ' || COALESCE(per.nom, '')) AS cloturee_par_prenom
        FROM fiches_incident fi
        LEFT JOIN fournisseurs f   ON f.id  = fi.fournisseur_id
        LEFT JOIN produits     p   ON p.id  = fi.produit_id
        LEFT JOIN reception_lignes rl ON rl.id = fi.reception_ligne_id
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
            COALESCE(NULLIF(fi.fournisseur_nom, ''), f.nom) AS fournisseur_nom,
            p.nom  AS produit_nom,
            rl.origine AS origine,
            TRIM(per.prenom || ' ' || COALESCE(per.nom, '')) AS cloturee_par_prenom
        FROM fiches_incident fi
        LEFT JOIN fournisseurs f   ON f.id  = fi.fournisseur_id
        LEFT JOIN produits     p   ON p.id  = fi.produit_id
        LEFT JOIN reception_lignes rl ON rl.id = fi.reception_ligne_id
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


class RecetteIngredientEnUsage(Exception):
    """Levée quand on tente de retirer un ingrédient référencé par une fabrication."""
    def __init__(self, nom: str):
        super().__init__(nom)
        self.nom = nom


async def update_recette(
    db: aiosqlite.Connection,
    recette_id: int,
    nom: str,
    produit_fini_id: int,
    dlc_jours: int,
    instructions: Optional[str],
    ingredients: list[dict],
) -> Optional[dict]:
    """
    Met à jour une recette existante (champs + ingrédients).

    Diff intelligent sur les ingrédients (préserve la traçabilité) :
      - Item avec `id` connu  → UPDATE quantite/unite (le produit_id n'est pas modifiable)
      - Item sans `id`        → INSERT
      - Id existant absent du payload → DELETE si non référencé par fabrication_lots,
        sinon RecetteIngredientEnUsage est levée.

    Retourne la recette mise à jour (via get_recette) ou None si la recette n'existe pas.
    """
    cur = await db.execute("SELECT id FROM recettes WHERE id = ?", (recette_id,))
    if not await cur.fetchone():
        return None

    await db.execute(
        "UPDATE recettes SET nom = ?, produit_fini_id = ?, dlc_jours = ?, instructions = ? WHERE id = ?",
        (nom, produit_fini_id, dlc_jours, instructions, recette_id),
    )

    cur = await db.execute(
        """
        SELECT ri.id, p.nom AS produit_nom
        FROM recette_ingredients ri
        JOIN produits p ON p.id = ri.produit_id
        WHERE ri.recette_id = ?
        """,
        (recette_id,),
    )
    existants = {row["id"]: row["produit_nom"] for row in await cur.fetchall()}

    ids_payload = {int(ing["id"]) for ing in ingredients if ing.get("id") is not None}
    a_supprimer = set(existants.keys()) - ids_payload

    for ri_id in a_supprimer:
        cur = await db.execute(
            "SELECT 1 FROM fabrication_lots WHERE recette_ingredient_id = ? LIMIT 1",
            (ri_id,),
        )
        if await cur.fetchone():
            await db.rollback()
            raise RecetteIngredientEnUsage(existants[ri_id])
        await db.execute("DELETE FROM recette_ingredients WHERE id = ?", (ri_id,))

    for ing in ingredients:
        if ing.get("id") is not None and int(ing["id"]) in existants:
            await db.execute(
                "UPDATE recette_ingredients SET quantite = ?, unite = ? WHERE id = ?",
                (ing.get("quantite"), ing.get("unite"), int(ing["id"])),
            )
        else:
            await db.execute(
                "INSERT INTO recette_ingredients (recette_id, produit_id, quantite, unite) VALUES (?,?,?,?)",
                (recette_id, ing["produit_id"], ing.get("quantite"), ing.get("unite")),
            )

    await db.commit()
    return await get_recette(db, recette_id)


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
                   rl.origine    AS origine,
                   rl.dlc,
                   rl.dluo,
                   rl.poids_kg,
                   r.date_reception
            FROM   reception_lignes rl
            JOIN   receptions r ON r.id = rl.reception_id
            WHERE  rl.produit_id = ?
              AND r.statut = 'cloturee'
              AND rl.conforme = 1
              AND r.livraison_refusee = 0
              AND (COALESCE(rl.dlc, rl.dluo) IS NULL
                   OR COALESCE(rl.dlc, rl.dluo) >= DATE('now'))
              AND NOT EXISTS (
                  SELECT 1 FROM dlc_devenir d
                  WHERE d.source_type = 'reception_ligne' AND d.source_id = rl.id
              )
            ORDER BY
                CASE WHEN COALESCE(rl.dlc, rl.dluo) IS NOT NULL THEN 0 ELSE 1 END,
                COALESCE(rl.dlc, rl.dluo) ASC,
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
            TRIM(pe.prenom || ' ' || COALESCE(pe.nom, '')) AS personnel_prenom
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
                rl.origine      AS origine,
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


# ===========================================================================
# Paramètres génériques (key/value)
# ===========================================================================

async def get_parametre(
    db: aiosqlite.Connection, boutique_id: int, cle: str, defaut: Optional[str] = None
) -> Optional[str]:
    cur = await db.execute(
        "SELECT valeur FROM parametres WHERE boutique_id = ? AND cle = ?",
        (boutique_id, cle),
    )
    row = await cur.fetchone()
    return row["valeur"] if row else defaut


async def get_parametres_prefix(
    db: aiosqlite.Connection, boutique_id: int, prefixe: str
) -> dict:
    cur = await db.execute(
        "SELECT cle, valeur FROM parametres WHERE boutique_id = ? AND cle LIKE ?",
        (boutique_id, f"{prefixe}%"),
    )
    rows = await cur.fetchall()
    return {r["cle"]: r["valeur"] for r in rows}


async def set_parametre(
    db: aiosqlite.Connection, boutique_id: int, cle: str, valeur: str
) -> None:
    await db.execute(
        """
        INSERT INTO parametres (boutique_id, cle, valeur) VALUES (?, ?, ?)
        ON CONFLICT(boutique_id, cle) DO UPDATE SET valeur = excluded.valeur
        """,
        (boutique_id, cle, valeur),
    )
    await db.commit()


# ===========================================================================
# DLC — Calendrier & devenir
# ===========================================================================

async def get_dlc_calendrier(
    db: aiosqlite.Connection,
    boutique_id: int,
    date_debut: str,   # "YYYY-MM-DD"
    date_fin: str,     # "YYYY-MM-DD"
    source: Optional[str] = None,       # 'reception' | 'fabrication' | 'cuisson' | 'refroidissement' | None
    categorie: Optional[str] = None,    # filtre produit
) -> list[dict]:
    """
    Retourne la liste des DLCs (réceptions + fabrications + cuissons + refroidissements)
    sur la période, enrichie du statut devenir s'il est renseigné.

    Émojis source pour le frontend :
        📦 reception_ligne    🔪 fabrication    🔥 cuisson    ❄️ refroidissement
    """
    items: list[dict] = []

    if source in (None, "reception"):
        cat_filter = "AND p.categorie = ?" if categorie else ""
        cat_params = (categorie,) if categorie else ()
        cur = await db.execute(
            f"""
            SELECT
                rl.id                AS source_id,
                'reception_ligne'    AS source_type,
                rl.dlc               AS dlc,
                rl.numero_lot        AS numero_lot,
                rl.origine           AS origine,
                rl.poids_kg          AS quantite,
                'kg'                 AS unite,
                p.id                 AS produit_id,
                COALESCE(p.nom, cf.designation, rl.designation_libre) AS produit_nom,
                COALESCE(p.categorie, 'matiere_premiere') AS categorie,
                f.nom                AS fournisseur_nom,
                r.date_reception     AS date_origine,
                r.heure_reception    AS heure_origine,
                TRIM(pers_recep.prenom || ' ' || COALESCE(pers_recep.nom, '')) AS receveur_prenom,
                r.id                 AS reception_id,
                dd.statut            AS devenir_statut,
                dd.commentaire       AS devenir_commentaire,
                dd.created_at        AS devenir_at,
                TRIM(pers.prenom || ' ' || COALESCE(pers.nom, '')) AS devenir_prenom
            FROM reception_lignes rl
            JOIN receptions r       ON r.id  = rl.reception_id
            LEFT JOIN produits   p       ON p.id  = rl.produit_id
            LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
            LEFT JOIN fournisseurs f ON f.id = rl.fournisseur_id
            LEFT JOIN personnel pers_recep ON pers_recep.id = r.personnel_id
            LEFT JOIN dlc_devenir dd
                   ON dd.source_type = 'reception_ligne' AND dd.source_id = rl.id
            LEFT JOIN personnel pers ON pers.id = dd.personnel_id
            WHERE rl.dlc IS NOT NULL
              AND rl.dlc BETWEEN ? AND ?
              AND (p.id IS NULL OR p.boutique_id = ?)
              AND r.statut = 'cloturee'
              AND rl.conforme = 1
              AND r.livraison_refusee = 0
              AND COALESCE(rl.statut, 'complet') <> 'en_attente'
              {cat_filter}
            """,
            (date_debut, date_fin, boutique_id, *cat_params),
        )
        for row in await cur.fetchall():
            items.append(dict(row))

    if source in (None, "fabrication"):
        cat_filter = "AND p.categorie = ?" if categorie else ""
        cat_params = (categorie,) if categorie else ()
        cur = await db.execute(
            f"""
            SELECT
                fab.id               AS source_id,
                'fabrication'        AS source_type,
                fab.dlc_finale       AS dlc,
                fab.lot_interne      AS numero_lot,
                fab.poids_fabrique   AS quantite,
                fab.poids_fabrique   AS poids_fabrique,
                r.instructions       AS recette_instructions,
                'kg'                 AS unite,
                p.id                 AS produit_id,
                p.nom                AS produit_nom,
                p.categorie          AS categorie,
                NULL                 AS fournisseur_nom,
                fab.date             AS date_origine,
                fab.created_at       AS fabrication_created_at,
                NULL                 AS reception_id,
                dd.statut            AS devenir_statut,
                dd.commentaire       AS devenir_commentaire,
                dd.created_at        AS devenir_at,
                TRIM(pers.prenom || ' ' || COALESCE(pers.nom, '')) AS devenir_prenom
            FROM fabrications fab
            JOIN recettes   r ON r.id = fab.recette_id
            JOIN produits   p ON p.id = r.produit_fini_id
            LEFT JOIN dlc_devenir dd
                   ON dd.source_type = 'fabrication' AND dd.source_id = fab.id
            LEFT JOIN personnel pers ON pers.id = dd.personnel_id
            WHERE fab.dlc_finale IS NOT NULL
              AND fab.dlc_finale BETWEEN ? AND ?
              AND p.boutique_id = ?
              {cat_filter}
            """,
            (date_debut, date_fin, boutique_id, *cat_params),
        )
        fab_rows = [dict(r) for r in await cur.fetchall()]

        # Récupère les ingrédients de chaque fabrication (pour déroulé dans modal)
        for fab in fab_rows:
            cur2 = await db.execute(
                """
                SELECT
                    p.nom           AS produit_nom,
                    rl.numero_lot,
                    rl.origine      AS origine,
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
                (fab["source_id"],),
            )
            fab["ingredients"] = [dict(r) for r in await cur2.fetchall()]
            items.append(fab)

    if source in (None, "cuisson"):
        cat_filter = "AND p.categorie = ?" if categorie else ""
        cat_params = (categorie,) if categorie else ()
        cur = await db.execute(
            f"""
            SELECT
                c.id                 AS source_id,
                'cuisson'            AS source_type,
                c.dlc_finale         AS dlc,
                COALESCE(rl.numero_lot, fab.lot_interne, 'C-' || c.id) AS numero_lot,
                rl.origine           AS origine,
                c.quantite           AS quantite,
                COALESCE(c.unite, 'kg') AS unite,
                p.id                 AS produit_id,
                p.nom                AS produit_nom,
                p.categorie          AS categorie,
                NULL                 AS fournisseur_nom,
                c.date_cuisson       AS date_origine,
                c.heure_fin          AS heure_origine,
                NULL                 AS reception_id,
                c.type_cuisson       AS type_cuisson,
                c.temperature_sortie AS temperature_sortie,
                dd.statut            AS devenir_statut,
                dd.commentaire       AS devenir_commentaire,
                dd.created_at        AS devenir_at,
                TRIM(pers.prenom || ' ' || COALESCE(pers.nom, '')) AS devenir_prenom
            FROM cuissons c
            JOIN produits p ON p.id = c.produit_id
            LEFT JOIN reception_lignes rl ON rl.id = c.reception_ligne_id
            LEFT JOIN fabrications     fab ON fab.id = c.fabrication_id
            LEFT JOIN dlc_devenir dd
                   ON dd.source_type = 'cuisson' AND dd.source_id = c.id
            LEFT JOIN personnel pers ON pers.id = dd.personnel_id
            WHERE c.dlc_finale IS NOT NULL
              AND c.dlc_finale BETWEEN ? AND ?
              AND c.boutique_id = ?
              -- Si la cuisson a été refroidie, on ne l'affiche plus (seul le refroidissement reste pertinent)
              AND NOT EXISTS (
                  SELECT 1 FROM refroidissements rf WHERE rf.cuisson_id = c.id
              )
              {cat_filter}
            """,
            (date_debut, date_fin, boutique_id, *cat_params),
        )
        for row in await cur.fetchall():
            items.append(dict(row))

    if source in (None, "refroidissement"):
        cat_filter = "AND p.categorie = ?" if categorie else ""
        cat_params = (categorie,) if categorie else ()
        cur = await db.execute(
            f"""
            SELECT
                rf.id                  AS source_id,
                'refroidissement'      AS source_type,
                rf.dlc_finale          AS dlc,
                COALESCE(rf.numero_lot, rl.numero_lot, fab.lot_interne, 'R-' || rf.id) AS numero_lot,
                rl.origine             AS origine,
                NULL                   AS quantite,
                'kg'                   AS unite,
                p.id                   AS produit_id,
                p.nom                  AS produit_nom,
                p.categorie            AS categorie,
                NULL                   AS fournisseur_nom,
                rf.date_refroidissement AS date_origine,
                rf.heure_fin           AS heure_origine,
                NULL                   AS reception_id,
                rf.cuisson_id          AS cuisson_id,
                rf.temperature_finale  AS temperature_finale,
                rf.duree_minutes       AS duree_minutes,
                dd.statut              AS devenir_statut,
                dd.commentaire         AS devenir_commentaire,
                dd.created_at          AS devenir_at,
                TRIM(pers.prenom || ' ' || COALESCE(pers.nom, '')) AS devenir_prenom
            FROM refroidissements rf
            JOIN produits p ON p.id = rf.produit_id
            LEFT JOIN cuissons c2 ON c2.id = rf.cuisson_id
            LEFT JOIN reception_lignes rl ON rl.id = c2.reception_ligne_id
            LEFT JOIN fabrications     fab ON fab.id = c2.fabrication_id
            LEFT JOIN dlc_devenir dd
                   ON dd.source_type = 'refroidissement' AND dd.source_id = rf.id
            LEFT JOIN personnel pers ON pers.id = dd.personnel_id
            WHERE rf.dlc_finale IS NOT NULL
              AND rf.dlc_finale BETWEEN ? AND ?
              AND rf.boutique_id = ?
              -- Refroidissements jetés à la saisie (cuisson ratée) : déjà tracés via dlc_devenir
              AND rf.jeter = 0
              {cat_filter}
            """,
            (date_debut, date_fin, boutique_id, *cat_params),
        )
        for row in await cur.fetchall():
            items.append(dict(row))

    items.sort(key=lambda x: (x["dlc"], x["produit_nom"]))
    return items


# ===========================================================================
# Stock unifié — vue FIFO toutes sources confondues
# ===========================================================================

# Émoji par source — utilisé par le frontend pour identification visuelle
_SRC_ICONS = {
    "reception_ligne": "📦",
    "fabrication":     "🔪",
    "cuisson":         "🔥",
    "refroidissement": "❄️",
}


async def get_stock_unifie(
    db: aiosqlite.Connection,
    boutique_id: int,
    type_produit: str = "tous",         # 'tous' | 'brut' | 'fini'
    categorie: Optional[str] = None,
    produit_id: Optional[int] = None,
    inclure_expires: bool = False,
    dlc_max: Optional[str] = None,      # 'YYYY-MM-DD' inclusif
    sources: Optional[list[str]] = None,  # restreint aux source_type listés
) -> list[dict]:
    """
    Retourne le stock vivant FIFO, toutes sources confondues :
        📦 reception_lignes   🔪 fabrications   🔥 cuissons   ❄️ refroidissements

    Filtres communs : DLC future (sauf si inclure_expires=True), pas dans dlc_devenir,
    refroidissements jetés exclus, cuissons déjà refroidies masquées.

    `sources` : si fourni, ne retourne que les source_type listés (ex:
    ['reception_ligne'] pour le module Cuisson, ['cuisson'] pour Refroidissement).
    Source unique de vérité du stock disponible à chaque étape de la chaîne HACCP.

    Tri : DLC croissante (plus pressé en premier), puis date_origine croissante.
    """
    from datetime import date as _date

    today = _date.today().isoformat()
    items: list[dict] = []

    def _src_actif(src: str) -> bool:
        return sources is None or src in sources

    inclure_brut = type_produit in ("tous", "brut")
    inclure_fini = type_produit in ("tous", "fini")

    def _build_filters(dlc_col: str) -> tuple[str, list]:
        """Construit le SQL et les paramètres pour les filtres optionnels communs."""
        sql_parts = []
        params: list = []
        if not inclure_expires:
            sql_parts.append(f"AND ({dlc_col} IS NULL OR {dlc_col} >= ?)")
            params.append(today)
        if dlc_max:
            sql_parts.append(f"AND {dlc_col} <= ?")
            params.append(dlc_max)
        if categorie:
            sql_parts.append("AND p.categorie = ?")
            params.append(categorie)
        if produit_id:
            sql_parts.append("AND p.id = ?")
            params.append(produit_id)
        return "\n              ".join(sql_parts), params

    # ── 📦 reception_lignes ────────────────────────────────────────────────
    if inclure_brut and _src_actif("reception_ligne"):
        extra_sql, extra_params = _build_filters("COALESCE(rl.dlc, rl.dluo)")
        cur = await db.execute(
            f"""
            SELECT
                'reception_ligne'  AS source_type,
                rl.id              AS source_id,
                p.id               AS produit_id,
                COALESCE(p.nom, cf.designation, rl.designation_libre) AS produit_nom,
                COALESCE(p.categorie, 'matiere_premiere') AS categorie,
                COALESCE(p.type_produit, 'brut')          AS type_produit,
                p.espece           AS espece,
                COALESCE(rl.dlc, rl.dluo) AS dlc,
                rl.dlc IS NULL AND rl.dluo IS NOT NULL AS est_dluo,
                rl.numero_lot      AS numero_lot,
                rl.origine         AS origine,
                rl.poids_kg        AS quantite,
                'kg'               AS unite,
                r.date_reception   AS date_origine,
                r.heure_reception  AS heure_origine,
                TRIM(pers_recep.prenom || ' ' || COALESCE(pers_recep.nom, '')) AS receveur_prenom,
                f.nom              AS fournisseur_nom
            FROM reception_lignes rl
            JOIN receptions   r ON r.id = rl.reception_id
            LEFT JOIN produits     p ON p.id = rl.produit_id
            LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
            LEFT JOIN fournisseurs f ON f.id = rl.fournisseur_id
            LEFT JOIN personnel pers_recep ON pers_recep.id = r.personnel_id
            WHERE (p.id IS NULL OR p.boutique_id = ?)
              AND r.statut = 'cloturee'
              AND rl.conforme = 1
              AND r.livraison_refusee = 0
              AND COALESCE(rl.statut, 'complet') <> 'en_attente'
              {extra_sql}
              AND NOT EXISTS (
                  SELECT 1 FROM dlc_devenir dd
                  WHERE dd.source_type = 'reception_ligne' AND dd.source_id = rl.id
              )
            """,
            (boutique_id, *extra_params),
        )
        items.extend(dict(r) for r in await cur.fetchall())

    # ── 🔪 fabrications ────────────────────────────────────────────────────
    if inclure_fini and _src_actif("fabrication"):
        extra_sql, extra_params = _build_filters("fab.dlc_finale")
        cur = await db.execute(
            f"""
            SELECT
                'fabrication'      AS source_type,
                fab.id             AS source_id,
                p.id               AS produit_id,
                p.nom              AS produit_nom,
                p.categorie        AS categorie,
                p.type_produit     AS type_produit,
                p.espece           AS espece,
                fab.dlc_finale     AS dlc,
                fab.lot_interne    AS numero_lot,
                fab.poids_fabrique AS quantite,
                'kg'               AS unite,
                fab.date           AS date_origine,
                fab.created_at     AS fabrication_created_at,
                NULL               AS fournisseur_nom
            FROM fabrications fab
            JOIN recettes rec ON rec.id = fab.recette_id
            JOIN produits p   ON p.id   = rec.produit_fini_id
            WHERE p.boutique_id = ?
              AND fab.dlc_finale IS NOT NULL
              {extra_sql}
              AND NOT EXISTS (
                  SELECT 1 FROM dlc_devenir dd
                  WHERE dd.source_type = 'fabrication' AND dd.source_id = fab.id
              )
            """,
            (boutique_id, *extra_params),
        )
        items.extend(dict(r) for r in await cur.fetchall())

    # ── 🔥 cuissons (hors celles refroidies) ───────────────────────────────
    if inclure_fini and _src_actif("cuisson"):
        extra_sql, extra_params = _build_filters("c.dlc_finale")
        cur = await db.execute(
            f"""
            SELECT
                'cuisson'             AS source_type,
                c.id                  AS source_id,
                p.id                  AS produit_id,
                p.nom                 AS produit_nom,
                p.categorie           AS categorie,
                p.type_produit        AS type_produit,
                p.espece              AS espece,
                c.dlc_finale          AS dlc,
                COALESCE(rl.numero_lot, fab.lot_interne, 'C-' || c.id) AS numero_lot,
                rl.origine            AS origine,
                c.quantite            AS quantite,
                COALESCE(c.unite,'kg') AS unite,
                c.date_cuisson        AS date_origine,
                c.heure_fin           AS heure_origine,
                NULL                  AS fournisseur_nom
            FROM cuissons c
            JOIN produits p ON p.id = c.produit_id
            LEFT JOIN reception_lignes rl ON rl.id = c.reception_ligne_id
            LEFT JOIN fabrications fab ON fab.id = c.fabrication_id
            WHERE c.boutique_id = ?
              AND c.dlc_finale IS NOT NULL
              {extra_sql}
              AND NOT EXISTS (
                  SELECT 1 FROM refroidissements rf WHERE rf.cuisson_id = c.id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM dlc_devenir dd
                  WHERE dd.source_type = 'cuisson' AND dd.source_id = c.id
              )
            """,
            (boutique_id, *extra_params),
        )
        items.extend(dict(r) for r in await cur.fetchall())

    # ── ❄️ refroidissements (jeter=0) ──────────────────────────────────────
    if inclure_fini and _src_actif("refroidissement"):
        extra_sql, extra_params = _build_filters("rf.dlc_finale")
        cur = await db.execute(
            f"""
            SELECT
                'refroidissement'      AS source_type,
                rf.id                  AS source_id,
                p.id                   AS produit_id,
                p.nom                  AS produit_nom,
                p.categorie            AS categorie,
                p.type_produit         AS type_produit,
                p.espece               AS espece,
                rf.dlc_finale          AS dlc,
                COALESCE(rf.numero_lot, rl.numero_lot, fab.lot_interne, 'R-' || rf.id) AS numero_lot,
                rl.origine             AS origine,
                NULL                   AS quantite,
                'kg'                   AS unite,
                rf.date_refroidissement AS date_origine,
                rf.heure_fin           AS heure_origine,
                NULL                   AS fournisseur_nom
            FROM refroidissements rf
            JOIN produits p ON p.id = rf.produit_id
            LEFT JOIN cuissons c2 ON c2.id = rf.cuisson_id
            LEFT JOIN reception_lignes rl ON rl.id = c2.reception_ligne_id
            LEFT JOIN fabrications fab ON fab.id = c2.fabrication_id
            WHERE rf.boutique_id = ?
              AND rf.dlc_finale IS NOT NULL
              AND rf.jeter = 0
              {extra_sql}
              AND NOT EXISTS (
                  SELECT 1 FROM dlc_devenir dd
                  WHERE dd.source_type = 'refroidissement' AND dd.source_id = rf.id
              )
            """,
            (boutique_id, *extra_params),
        )
        items.extend(dict(r) for r in await cur.fetchall())

    # ── Enrichissement Python : icône + jours_restants + tri FIFO ──────────
    today_d = _date.fromisoformat(today)
    for it in items:
        it["source_icon"] = _SRC_ICONS.get(it["source_type"], "")
        if it["dlc"]:
            try:
                it["jours_restants"] = (_date.fromisoformat(it["dlc"]) - today_d).days
            except ValueError:
                it["jours_restants"] = None
        else:
            it["jours_restants"] = None

    items.sort(key=lambda x: (x["dlc"] or "9999-12-31",
                              x.get("date_origine") or "9999-12-31",
                              x["produit_nom"] or ""))
    return items


async def update_stock_item(
    db: aiosqlite.Connection,
    source_type: str,
    source_id: int,
    dlc: str | None = None,
    quantite: float | None = None,
) -> bool:
    """
    Modifie la DLC et/ou la quantité d'un article en stock.
    Le N° de lot (numero_lot / lot_interne) n'est jamais touché.
    Retourne True si la ligne a été modifiée, False si introuvable.
    """
    SOURCES = {
        "reception_ligne": {
            "table":    "reception_lignes",
            "col_dlc":  "dlc",
            "col_qte":  "poids_kg",
        },
        "fabrication": {
            "table":    "fabrications",
            "col_dlc":  "dlc_finale",
            "col_qte":  "poids_fabrique",
        },
        "cuisson": {
            "table":    "cuissons",
            "col_dlc":  "dlc_finale",
            "col_qte":  "quantite",
        },
        "refroidissement": {
            "table":    "refroidissements",
            "col_dlc":  "dlc_finale",
            "col_qte":  None,  # pas de colonne quantité
        },
    }
    if source_type not in SOURCES:
        raise ValueError(f"source_type inconnu : {source_type}")

    cfg = SOURCES[source_type]
    sets, params = [], []

    if dlc is not None:
        sets.append(f"{cfg['col_dlc']} = ?")
        params.append(dlc)

    if quantite is not None and cfg["col_qte"] is not None:
        sets.append(f"{cfg['col_qte']} = ?")
        params.append(quantite)

    if not sets:
        return True  # rien à faire

    params.append(source_id)
    sql = f"UPDATE {cfg['table']} SET {', '.join(sets)} WHERE id = ?"
    async with db.execute(sql, params) as cur:
        await db.commit()
        return cur.rowcount > 0


async def _insert_dlc_devenir(
    db: aiosqlite.Connection,
    source_type: str,
    source_id: int,
    statut: str,
    personnel_id: Optional[int],
    commentaire: Optional[str],
    replace: bool,
) -> int:
    """Insert atomique dans dlc_devenir, sans commit. `replace=False` préserve un statut existant."""
    if replace:
        sql = """
            INSERT INTO dlc_devenir (source_type, source_id, statut, personnel_id, commentaire)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source_type, source_id) DO UPDATE SET
                statut       = excluded.statut,
                personnel_id = excluded.personnel_id,
                commentaire  = excluded.commentaire,
                created_at   = CURRENT_TIMESTAMP
        """
    else:
        sql = """
            INSERT OR IGNORE INTO dlc_devenir
                (source_type, source_id, statut, personnel_id, commentaire)
            VALUES (?, ?, ?, ?, ?)
        """
    cur = await db.execute(sql, (source_type, source_id, statut, personnel_id, commentaire))
    return cur.lastrowid or 0


async def _cascade_dlc_aval(
    db: aiosqlite.Connection,
    source_type: str,
    source_id: int,
    statut: str,
    personnel_id: Optional[int],
    commentaire_amont: Optional[str],
) -> None:
    """
    Propage la sortie de stock vers l'aval de la chaîne HACCP :
        reception_ligne → cuissons → refroidissements
        cuisson         → refroidissements

    Utilise INSERT OR IGNORE : si l'aval a déjà été tracé (ex: cuisson marquée
    "consommée"), on préserve l'historique existant.
    """
    cascade_msg = f"Cascade depuis sortie {source_type} #{source_id} ({statut})"
    if commentaire_amont:
        cascade_msg += f" — {commentaire_amont}"

    cuisson_ids: list[int] = []
    if source_type == "reception_ligne":
        cur = await db.execute(
            "SELECT id FROM cuissons WHERE reception_ligne_id = ?", (source_id,)
        )
        cuisson_ids = [r[0] for r in await cur.fetchall()]
        for cid in cuisson_ids:
            await _insert_dlc_devenir(
                db, "cuisson", cid, statut, personnel_id, cascade_msg, replace=False,
            )
    elif source_type == "cuisson":
        cuisson_ids = [source_id]

    if cuisson_ids:
        placeholders = ",".join("?" * len(cuisson_ids))
        cur = await db.execute(
            f"SELECT id FROM refroidissements WHERE cuisson_id IN ({placeholders})",
            cuisson_ids,
        )
        for rid in [r[0] for r in await cur.fetchall()]:
            await _insert_dlc_devenir(
                db, "refroidissement", rid, statut, personnel_id, cascade_msg, replace=False,
            )


async def create_dlc_devenir(
    db: aiosqlite.Connection,
    source_type: str,
    source_id: int,
    statut: str,
    personnel_id: Optional[int] = None,
    commentaire: Optional[str] = None,
) -> int:
    """
    Sortie de stock (jeté/vendu/consommé/autre) avec cascade aval.

    Logique métier : la matière première alimente la cuisson qui alimente le
    refroidissement. Sortir un maillon amont sort tout l'aval qui en dépend.
    """
    nouveau_id = await _insert_dlc_devenir(
        db, source_type, source_id, statut, personnel_id, commentaire, replace=True,
    )
    await _cascade_dlc_aval(db, source_type, source_id, statut, personnel_id, commentaire)
    await db.commit()
    return nouveau_id


_DLC_SOURCE_TABLE_FIELD = {
    "reception_ligne":  ("reception_lignes",   "dlc"),
    "fabrication":      ("fabrications",        "dlc_finale"),
    "cuisson":          ("cuissons",            "dlc_finale"),
    "refroidissement":  ("refroidissements",    "dlc_finale"),
}


async def update_dlc_source_date(
    db: aiosqlite.Connection,
    source_type: str,
    source_id: int,
    nouvelle_dlc: str,
) -> None:
    """Met à jour la date DLC d'un enregistrement source (toute table)."""
    table, field = _DLC_SOURCE_TABLE_FIELD[source_type]
    await db.execute(
        f"UPDATE {table} SET {field} = ? WHERE id = ?",
        (nouvelle_dlc, source_id),
    )
    await db.commit()

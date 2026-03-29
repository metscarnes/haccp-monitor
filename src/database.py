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

DB_PATH = Path(__file__).parent.parent / "data" / "haccp.db"

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

-- ===========================================================================
-- PHASE 2 — Module Tâches HACCP
-- ===========================================================================

CREATE TABLE IF NOT EXISTS personnel (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id INTEGER NOT NULL,
    prenom      TEXT    NOT NULL,
    actif       BOOLEAN DEFAULT 1,
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
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);

CREATE TABLE IF NOT EXISTS plan_nettoyage (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id       INTEGER NOT NULL,
    local             TEXT    NOT NULL,
    surface_equipement TEXT   NOT NULL,
    frequence         TEXT    NOT NULL,
    actif             BOOLEAN DEFAULT 1,
    FOREIGN KEY (boutique_id) REFERENCES boutiques(id)
);
"""

SEED_SQL = """
INSERT OR IGNORE INTO boutiques (id, nom, adresse, siret)
VALUES (1, 'Au Comptoir des Lilas', '122 rue de Paris, Les Lilas, 93260', '');

INSERT OR IGNORE INTO enceintes (id, boutique_id, nom, type, sonde_zigbee_id, seuil_temp_min, seuil_temp_max, seuil_hum_max, delai_alerte_minutes)
VALUES
(1, 1, 'Chambre froide 1', 'chambre_froide', 'chambre_froide_1',  0.0,  4.0, 90.0, 5),
(2, 1, 'Chambre froide 2', 'chambre_froide', 'chambre_froide_2',  0.0,  4.0, 90.0, 5),
(3, 1, 'Vitrine',          'vitrine',        'vitrine_1',          0.0,  4.0, 90.0, 5),
(4, 1, 'Laboratoire',      'laboratoire',    'laboratoire_1',     10.0, 15.0, 80.0, 5);
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

-- Plan de nettoyage par défaut (boutique 1)
INSERT OR IGNORE INTO plan_nettoyage (boutique_id, local, surface_equipement, frequence) VALUES
(1, 'Laboratoire',  'Plan de travail inox',        'quotidien'),
(1, 'Laboratoire',  'Sol laboratoire',              'quotidien'),
(1, 'Boutique',     'Vitrine réfrigérée',           'quotidien'),
(1, 'Boutique',     'Sol boutique',                 'quotidien'),
(1, 'Laboratoire',  'Chambre froide 1',             'hebdomadaire'),
(1, 'Laboratoire',  'Chambre froide 2',             'hebdomadaire'),
(1, 'Laboratoire',  'Hotte aspiration',             'mensuel'),
(1, 'Boutique',     'Trancheur',                    'quotidien');
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

async def get_produits(db: aiosqlite.Connection, boutique_id: int) -> list[dict]:
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
    cursor = await db.execute(
        """
        INSERT INTO receptions
            (boutique_id, fournisseur_id, fournisseur_nom, numero_bon_livraison,
             operateur, heure_livraison, temperature_camion, proprete_camion, commentaire)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["boutique_id"],
            data.get("fournisseur_id"),
            data["fournisseur_nom"],
            data.get("numero_bon_livraison"),
            data["operateur"],
            data.get("heure_livraison"),
            data.get("temperature_camion"),
            data.get("proprete_camion"),
            data.get("commentaire"),
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def add_reception_ligne(db: aiosqlite.Connection, reception_id: int, data: dict) -> int:
    cursor = await db.execute(
        """
        INSERT INTO reception_lignes
            (reception_id, produit_nom, temperature_produit, integrite_emballage,
             dlc, numero_lot, quantite, heure_stockage, conforme)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reception_id,
            data["produit_nom"],
            data.get("temperature_produit"),
            data.get("integrite_emballage"),
            data.get("dlc"),
            data.get("numero_lot"),
            data.get("quantite"),
            data.get("heure_stockage"),
            data.get("conforme"),
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def finaliser_reception(
    db: aiosqlite.Connection, reception_id: int, conforme: bool
) -> None:
    await db.execute(
        "UPDATE receptions SET conforme = ? WHERE id = ?", (conforme, reception_id)
    )
    await db.commit()


async def get_receptions(
    db: aiosqlite.Connection, boutique_id: int, limit: int = 50
) -> list[dict]:
    cursor = await db.execute(
        """
        SELECT r.*, COUNT(rl.id) AS nb_lignes,
               SUM(CASE WHEN rl.conforme = 0 THEN 1 ELSE 0 END) AS nb_nc
        FROM receptions r
        LEFT JOIN reception_lignes rl ON rl.reception_id = r.id
        WHERE r.boutique_id = ?
        GROUP BY r.id
        ORDER BY r.date_reception DESC
        LIMIT ?
        """,
        (boutique_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_reception(db: aiosqlite.Connection, reception_id: int) -> Optional[dict]:
    cursor = await db.execute(
        "SELECT * FROM receptions WHERE id = ?", (reception_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return None
    reception = dict(row)
    # Lignes
    cursor2 = await db.execute(
        "SELECT * FROM reception_lignes WHERE reception_id = ? ORDER BY id",
        (reception_id,),
    )
    lignes = await cursor2.fetchall()
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
# PHASE 2 — Admin : pièges + plan nettoyage
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


async def get_plan_nettoyage(db: aiosqlite.Connection, boutique_id: int) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM plan_nettoyage WHERE boutique_id = ? AND actif = 1 ORDER BY local, frequence",
        (boutique_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def create_plan_nettoyage_item(db: aiosqlite.Connection, data: dict) -> int:
    cursor = await db.execute(
        "INSERT INTO plan_nettoyage (boutique_id, local, surface_equipement, frequence) VALUES (?, ?, ?, ?)",
        (data["boutique_id"], data["local"], data["surface_equipement"], data["frequence"]),
    )
    await db.commit()
    return cursor.lastrowid

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
"""

SEED_SQL = """
INSERT OR IGNORE INTO boutiques (id, nom, adresse, siret)
VALUES (1, 'Au Comptoir des Lilas', '122 rue de Paris, Les Lilas, 93260', '');
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
# Purge (rétention)
# ---------------------------------------------------------------------------

async def purger_anciens_releves(db: aiosqlite.Connection) -> dict:
    """
    Applique la politique de rétention :
    - Relevés bruts > 12 mois : supprimés
    - Alertes > 3 ans : supprimées
    """
    now = datetime.now(timezone.utc)
    limite_releves = (now - timedelta(days=365)).isoformat()
    limite_alertes = (now - timedelta(days=365 * 3)).isoformat()

    cur_r = await db.execute(
        "DELETE FROM releves WHERE horodatage < ?", (limite_releves,)
    )
    cur_a = await db.execute(
        "DELETE FROM alertes WHERE created_at < ?", (limite_alertes,)
    )
    await db.commit()

    return {
        "releves_supprimes": cur_r.rowcount,
        "alertes_supprimees": cur_a.rowcount,
    }

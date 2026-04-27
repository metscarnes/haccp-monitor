"""
routes_refroidissement.py — Module Refroidissement (HACCP)

Refroidissement rapide après cuisson : passer de chaud à ≤ +10 °C à cœur
en ≤ 2 heures. Si le couple temps/température n'est pas respecté
(durée > 2 h ET T° > 10 °C), les produits doivent être JETÉS.

GET  /api/refroidissement/produits
GET  /api/refroidissement/enregistrements?limit=50
POST /api/refroidissement/enregistrements
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.database import get_db, create_dlc_devenir

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/refroidissement", tags=["refroidissement"])

TEMPERATURE_CIBLE        = 10.0   # °C max à cœur après refroidissement
TEMPERATURE_MIN_CUISSON  = 63.0   # °C min à cœur en sortie de cuisson
DUREE_MAX_MINUTES        = 120    # 2 h


# ---------------------------------------------------------------------------
# Schéma DB (créé à la volée, comme cuisson / nuisibles)
# ---------------------------------------------------------------------------

_ENSURE_TABLE = """
    CREATE TABLE IF NOT EXISTS refroidissements (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        date_refroidissement  DATE    NOT NULL,
        personnel_id          INTEGER NOT NULL,
        produit_id            INTEGER NOT NULL,
        cuisson_id            INTEGER,
        heure_debut           TEXT    NOT NULL,
        heure_fin             TEXT    NOT NULL,
        duree_minutes         INTEGER NOT NULL,
        temperature_initiale  REAL    DEFAULT 63.0,
        temperature_finale    REAL    NOT NULL,
        temperature_cible     REAL    NOT NULL DEFAULT 10.0,
        duree_max_minutes     INTEGER NOT NULL DEFAULT 120,
        conforme              INTEGER NOT NULL,
        jeter                 INTEGER NOT NULL DEFAULT 0,
        action_corrective     TEXT,
        created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (personnel_id) REFERENCES personnel(id),
        FOREIGN KEY (produit_id)   REFERENCES produits(id),
        FOREIGN KEY (cuisson_id)   REFERENCES cuissons(id)
    )
"""

# Migration : ajoute la colonne si la table existait avant
_ENSURE_COL_TEMP_INIT = """
    ALTER TABLE refroidissements ADD COLUMN temperature_initiale REAL DEFAULT 63.0
"""

_ENSURE_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_refroidissements_date
        ON refroidissements(date_refroidissement)
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _duree_minutes(heure_debut: str, heure_fin: str) -> int:
    """Durée en minutes entre deux 'HH:MM'. Si fin <= debut on suppose +24 h."""
    try:
        h1, m1 = map(int, heure_debut.split(":"))
        h2, m2 = map(int, heure_fin.split(":"))
    except Exception:
        raise HTTPException(status_code=422, detail="Format d'heure invalide (HH:MM).")
    debut = h1 * 60 + m1
    fin   = h2 * 60 + m2
    if fin <= debut:
        fin += 24 * 60
    return fin - debut


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class RefroidissementCreate(BaseModel):
    date_refroidissement: str   = Field(..., description="YYYY-MM-DD")
    personnel_id:         int
    produit_id:           int
    cuisson_id:           Optional[int] = None
    heure_debut:          str   = Field(..., description="HH:MM mise en refroidissement")
    heure_fin:            str   = Field(..., description="HH:MM fin de refroidissement")
    temperature_initiale: Optional[float] = Field(63.0, description="T° à cœur avant refroidissement")
    temperature_finale:   float = Field(..., description="T° à cœur après refroidissement")
    jeter_action:         bool  = Field(False, description="True = jeter le produit + créer entrée devenir")
    action_corrective:    Optional[str] = None


# ---------------------------------------------------------------------------
# GET /api/refroidissement/produits
# Liste des produits déjà cuits (déduit de la table cuissons)
# ---------------------------------------------------------------------------

@router.get("/produits")
async def lister_produits_cuisson():
    """Renvoie les produits enregistrés dans le module Cuisson."""
    async with get_db() as db:
        # cuissons est créée à la volée par routes_cuisson — on s'assure qu'elle existe
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cuissons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produit_id INTEGER NOT NULL
            )
        """)
        cur = await db.execute(
            """
            SELECT p.id, p.nom, p.espece,
                   MAX(c.id)           AS dernier_cuisson_id,
                   MAX(c.date_cuisson) AS derniere_cuisson_date,
                   COUNT(c.id)         AS nb_cuissons
            FROM   cuissons c
            JOIN   produits p ON p.id = c.produit_id
            GROUP  BY p.id
            ORDER  BY derniere_cuisson_date DESC, p.nom ASC
            """
        )
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# POST /api/refroidissement/enregistrements
# ---------------------------------------------------------------------------

@router.post("/enregistrements", status_code=201)
async def creer_refroidissement(body: RefroidissementCreate):
    duree = _duree_minutes(body.heure_debut, body.heure_fin)

    temp_init = body.temperature_initiale if body.temperature_initiale is not None else 63.0
    cuisson_ok = temp_init >= TEMPERATURE_MIN_CUISSON
    duree_ok   = duree <= DUREE_MAX_MINUTES
    temp_ok    = body.temperature_finale <= TEMPERATURE_CIBLE
    conforme   = cuisson_ok and duree_ok and temp_ok

    # Règle "JETER cuisson" : pasteurisation non atteinte
    jeter_cuisson = not cuisson_ok
    # Règle "JETER refroidissement" : couple temps/T° finale non respecté
    jeter_refroidissement = (not duree_ok) and (not temp_ok)
    jeter = jeter_cuisson or jeter_refroidissement

    if not conforme and not (body.action_corrective and body.action_corrective.strip()):
        raisons = []
        if not cuisson_ok:
            raisons.append(
                f"cuisson insuffisante ({temp_init:.1f} °C < {TEMPERATURE_MIN_CUISSON} °C)"
            )
        if not temp_ok:
            raisons.append(f"T° finale trop haute ({body.temperature_finale:.1f} °C > {TEMPERATURE_CIBLE} °C)")
        if not duree_ok:
            raisons.append(f"durée dépassée ({duree} min > {DUREE_MAX_MINUTES} min)")
        raise HTTPException(
            status_code=422,
            detail=f"Action corrective obligatoire : {' · '.join(raisons)}.",
        )

    async with get_db() as db:
        await db.execute(_ENSURE_TABLE)
        await db.execute(_ENSURE_INDEX)
        try:
            await db.execute(_ENSURE_COL_TEMP_INIT)
        except Exception:
            pass  # colonne déjà présente

        cur = await db.execute(
            """
            INSERT INTO refroidissements (
                date_refroidissement, personnel_id, produit_id, cuisson_id,
                heure_debut, heure_fin, duree_minutes,
                temperature_initiale, temperature_finale,
                temperature_cible, duree_max_minutes,
                conforme, jeter, action_corrective
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                body.date_refroidissement,
                body.personnel_id,
                body.produit_id,
                body.cuisson_id,
                body.heure_debut,
                body.heure_fin,
                duree,
                body.temperature_initiale if body.temperature_initiale is not None else 63.0,
                body.temperature_finale,
                TEMPERATURE_CIBLE,
                DUREE_MAX_MINUTES,
                1 if conforme else 0,
                1 if jeter else 0,
                (body.action_corrective or "").strip() or None,
            ),
        )
        nouveau_id = cur.lastrowid

        # Entrée "devenir" dans le calendrier DLC si l'opérateur confirme le jet
        if body.jeter_action:
            try:
                await create_dlc_devenir(
                    db,
                    source_type="refroidissement",
                    source_id=nouveau_id,
                    statut="jete",
                    personnel_id=body.personnel_id,
                    commentaire=(body.action_corrective or "").strip() or "Produit jeté — refroidissement non conforme",
                )
            except Exception as exc:
                logger.warning("dlc_devenir non créé pour refroidissement #%d : %s", nouveau_id, exc)

        await db.commit()

    logger.info(
        "Refroidissement #%d — produit=%d durée=%dmin T°init=%.1f T°=%.1f conforme=%s jeter=%s jeter_action=%s",
        nouveau_id, body.produit_id, duree, temp_init, body.temperature_finale,
        conforme, jeter, body.jeter_action,
    )
    return {
        "ok":            True,
        "id":            nouveau_id,
        "duree_minutes": duree,
        "conforme":      conforme,
        "jeter":         jeter,
        "jeter_cuisson": jeter_cuisson,
        "cuisson_ok":    cuisson_ok,
        "devenir_cree":  body.jeter_action,
    }


# ---------------------------------------------------------------------------
# GET /api/refroidissement/enregistrements
# ---------------------------------------------------------------------------

@router.get("/enregistrements")
async def lister_refroidissements(
    date_debut: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_fin:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit:      int = Query(50, ge=1, le=500),
):
    clauses: list = []
    params:  list = []
    if date_debut:
        clauses.append("r.date_refroidissement >= ?")
        params.append(date_debut)
    if date_fin:
        clauses.append("r.date_refroidissement <= ?")
        params.append(date_fin)
    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)

    async with get_db() as db:
        await db.execute(_ENSURE_TABLE)
        await db.execute(_ENSURE_INDEX)

        cur = await db.execute(
            f"""
            SELECT r.*,
                   p.nom        AS produit_nom,
                   pers.prenom  AS personnel_prenom
            FROM   refroidissements r
            LEFT   JOIN produits  p    ON p.id    = r.produit_id
            LEFT   JOIN personnel pers ON pers.id = r.personnel_id
            {where_sql}
            ORDER BY r.date_refroidissement DESC, r.id DESC
            LIMIT ?
            """,
            tuple(params),
        )
        rows = await cur.fetchall()

    return [dict(r) for r in rows]

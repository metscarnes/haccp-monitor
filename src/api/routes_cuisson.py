"""
routes_cuisson.py — Module Cuisson (HACCP)

Enregistrement des cuissons avec contrôle température de fin de cuisson.
Cible réglementaire : ≥ 63 °C à cœur.

GET  /api/cuisson/enregistrements?type=rotissoire&limit=50
POST /api/cuisson/enregistrements
"""

import logging
from datetime import date as _date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cuisson", tags=["cuisson"])

TEMPERATURE_CIBLE = 63.0

# ---------------------------------------------------------------------------
# Schéma DB (créé à la volée, comme nuisibles)
# ---------------------------------------------------------------------------

_ENSURE_TABLE = """
    CREATE TABLE IF NOT EXISTS cuissons (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        type_cuisson        TEXT    NOT NULL,           -- 'rotissoire', ...
        date_cuisson        DATE    NOT NULL,
        personnel_id        INTEGER NOT NULL,
        produit_id          INTEGER NOT NULL,
        reception_ligne_id  INTEGER,
        quantite            REAL,
        unite               TEXT    DEFAULT 'kg',
        heure_debut         TEXT    NOT NULL,
        heure_fin           TEXT    NOT NULL,
        temperature_sortie  REAL    NOT NULL,
        temperature_cible   REAL    NOT NULL DEFAULT 63.0,
        conforme            INTEGER NOT NULL,
        action_corrective   TEXT,
        created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (personnel_id)       REFERENCES personnel(id),
        FOREIGN KEY (produit_id)         REFERENCES produits(id),
        FOREIGN KEY (reception_ligne_id) REFERENCES reception_lignes(id)
    )
"""

_ENSURE_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_cuissons_type_date
        ON cuissons(type_cuisson, date_cuisson)
"""


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class CuissonCreate(BaseModel):
    type_cuisson:       str   = Field(..., description="'rotissoire' pour l'instant")
    date_cuisson:       str   = Field(..., description="YYYY-MM-DD")
    personnel_id:       int
    produit_id:         int
    reception_ligne_id: Optional[int]   = None
    quantite:           Optional[float] = None
    unite:              Optional[str]   = "kg"
    heure_debut:        str   = Field(..., description="HH:MM")
    heure_fin:          str   = Field(..., description="HH:MM")
    temperature_sortie: float
    action_corrective:  Optional[str]   = None


# ---------------------------------------------------------------------------
# POST /api/cuisson/enregistrements
# ---------------------------------------------------------------------------

@router.post("/enregistrements", status_code=201)
async def creer_cuisson(body: CuissonCreate):
    conforme = 1 if body.temperature_sortie >= TEMPERATURE_CIBLE else 0
    if not conforme and not (body.action_corrective and body.action_corrective.strip()):
        raise HTTPException(
            status_code=422,
            detail="Action corrective obligatoire si température < 63 °C",
        )

    async with get_db() as db:
        await db.execute(_ENSURE_TABLE)
        await db.execute(_ENSURE_INDEX)

        cur = await db.execute(
            """
            INSERT INTO cuissons (
                type_cuisson, date_cuisson, personnel_id, produit_id,
                reception_ligne_id, quantite, unite,
                heure_debut, heure_fin,
                temperature_sortie, temperature_cible,
                conforme, action_corrective
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                body.type_cuisson.lower(),
                body.date_cuisson,
                body.personnel_id,
                body.produit_id,
                body.reception_ligne_id,
                body.quantite,
                body.unite or "kg",
                body.heure_debut,
                body.heure_fin,
                body.temperature_sortie,
                TEMPERATURE_CIBLE,
                conforme,
                (body.action_corrective or "").strip() or None,
            ),
        )
        await db.commit()
        nouveau_id = cur.lastrowid

    logger.info(
        "Cuisson %s #%d — produit=%d T°=%.1f conforme=%s",
        body.type_cuisson, nouveau_id, body.produit_id,
        body.temperature_sortie, bool(conforme),
    )
    return {"ok": True, "id": nouveau_id, "conforme": bool(conforme)}


# ---------------------------------------------------------------------------
# GET /api/cuisson/enregistrements
# ---------------------------------------------------------------------------

@router.get("/enregistrements")
async def lister_cuissons(
    type:       str = Query("rotissoire"),
    date_debut: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_fin:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit:      int = Query(50, ge=1, le=500),
):
    """Liste des cuissons d'un type donné, du plus récent au plus ancien."""
    clauses = ["c.type_cuisson = ?"]
    params: list = [type.lower()]
    if date_debut:
        clauses.append("c.date_cuisson >= ?")
        params.append(date_debut)
    if date_fin:
        clauses.append("c.date_cuisson <= ?")
        params.append(date_fin)

    where_sql = " AND ".join(clauses)
    params.append(limit)

    async with get_db() as db:
        await db.execute(_ENSURE_TABLE)
        await db.execute(_ENSURE_INDEX)

        cur = await db.execute(
            f"""
            SELECT c.*,
                   p.nom      AS produit_nom,
                   pers.prenom AS personnel_prenom
            FROM   cuissons c
            LEFT   JOIN produits  p    ON p.id    = c.produit_id
            LEFT   JOIN personnel pers ON pers.id = c.personnel_id
            WHERE  {where_sql}
            ORDER BY c.date_cuisson DESC, c.id DESC
            LIMIT ?
            """,
            tuple(params),
        )
        rows = await cur.fetchall()

    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# GET /api/cuisson/produits/{produit_id}/receptions
# Historique des réceptions pour un produit donné
# ---------------------------------------------------------------------------

@router.get("/produits/{produit_id}/receptions")
async def historique_receptions_produit(produit_id: int, limit: int = Query(20, ge=1, le=100)):
    async with get_db() as db:
        cur = await db.execute(
            """
            SELECT rl.id                AS reception_ligne_id,
                   rl.reception_id      AS reception_id,
                   rl.numero_lot,
                   rl.dlc,
                   rl.poids_kg,
                   rl.temperature_reception,
                   r.date_reception,
                   r.heure_reception,
                   f.nom                AS fournisseur_nom
            FROM   reception_lignes rl
            JOIN   receptions  r ON r.id = rl.reception_id
            LEFT JOIN fournisseurs f ON f.id = rl.fournisseur_id
            WHERE  rl.produit_id = ?
            ORDER BY r.date_reception DESC, r.id DESC
            LIMIT ?
            """,
            (produit_id, limit),
        )
        rows = await cur.fetchall()

    return [dict(r) for r in rows]

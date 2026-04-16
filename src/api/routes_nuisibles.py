"""
routes_nuisibles.py — Lutte contre nuisibles (IPM — Integrated Pest Management)

GET  /api/nuisibles/controles?type_id=1&annee=2026  → registre semaines 1-52
POST /api/nuisibles/controles                        → sauvegarder / mettre à jour une semaine
"""

import json
import logging
from datetime import date as _date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nuisibles", tags=["nuisibles"])

# ---------------------------------------------------------------------------
# Schéma DB (créé à la volée)
# ---------------------------------------------------------------------------

_ENSURE_TABLE = """
    CREATE TABLE IF NOT EXISTS nuisibles_controles (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        type_id     INTEGER NOT NULL,
        annee       INTEGER NOT NULL,
        semaine     INTEGER NOT NULL,
        resultats   TEXT    NOT NULL DEFAULT '{}',
        visa        TEXT    NOT NULL DEFAULT '',
        date_saisie TEXT    NOT NULL,
        UNIQUE(type_id, annee, semaine)
    )
"""

# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class ControleNuisible(BaseModel):
    type_id:   int         # 1=rongeurs  2=ins.volants  3=ins.rampants  4=oiseaux
    annee:     int
    semaine:   int         # 1-53
    resultats: dict        # {"p1": "O"/"N"/None, "p2": ..., ...}
    visa:      str = ""

# ---------------------------------------------------------------------------
# GET /api/nuisibles/controles
# ---------------------------------------------------------------------------

@router.get("/controles")
async def lister_controles(
    type_id: int = Query(..., ge=1, le=4, description="1=rongeurs 2=ins.vol 3=ins.ramp 4=oiseaux"),
    annee:   int = Query(..., description="Année civile"),
):
    """
    Retourne tous les enregistrements de l'année pour un type de nuisible.
    Format : { semaine_num: { resultats: {p1: "O"/"N"/null}, visa, date_saisie } }
    """
    async with get_db() as db:
        await db.execute(_ENSURE_TABLE)
        await db.commit()

        rows = await db.execute_fetchall(
            "SELECT semaine, resultats, visa, date_saisie "
            "FROM nuisibles_controles "
            "WHERE type_id = ? AND annee = ? ORDER BY semaine",
            (type_id, annee),
        )

    result = {}
    for row in rows:
        semaine, resultats_json, visa, date_saisie = row
        try:
            resultats = json.loads(resultats_json)
        except Exception:
            resultats = {}
        result[str(semaine)] = {
            "resultats":    resultats,
            "visa":         visa,
            "date_saisie":  date_saisie,
        }

    return result


# ---------------------------------------------------------------------------
# POST /api/nuisibles/controles
# ---------------------------------------------------------------------------

@router.post("/controles", status_code=201)
async def sauvegarder_controle(body: ControleNuisible):
    """
    Insère ou met à jour le contrôle d'une semaine pour un type de nuisible.
    """
    if not (1 <= body.semaine <= 53):
        raise HTTPException(400, "semaine invalide (1-53)")

    aujourd_hui    = _date.today().isoformat()
    resultats_json = json.dumps(body.resultats)

    async with get_db() as db:
        await db.execute(_ENSURE_TABLE)
        await db.execute(
            """
            INSERT INTO nuisibles_controles
                (type_id, annee, semaine, resultats, visa, date_saisie)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(type_id, annee, semaine) DO UPDATE SET
                resultats   = excluded.resultats,
                visa        = excluded.visa,
                date_saisie = excluded.date_saisie
            """,
            (body.type_id, body.annee, body.semaine,
             resultats_json, body.visa, aujourd_hui),
        )
        await db.commit()

    logger.info(
        "Nuisibles — type=%d  sem=%d/%d  visa=%s",
        body.type_id, body.semaine, body.annee, body.visa or "—",
    )
    return {
        "ok":       True,
        "type_id":  body.type_id,
        "semaine":  body.semaine,
        "annee":    body.annee,
    }

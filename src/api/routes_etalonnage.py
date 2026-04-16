"""
routes_etalonnage.py — Étalonnage des thermomètres (EET01)

POST /api/etalonnage           → enregistrer un étalonnage
GET  /api/etalonnage/historique → liste des enregistrements (du plus récent)
GET  /api/etalonnage/status     → statut trimestriel (alerte si dépassé)

Règle de conformité : 0°C ± 0,5°C
Fréquence           : trimestrielle (4 fois par an)
"""

import logging
from datetime import date as _date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/etalonnage", tags=["etalonnage"])

TEMP_MIN     = -0.5   # borne basse conformité (°C)
TEMP_MAX     =  0.5   # borne haute conformité (°C)
DELAI_JOURS  =  92    # ~3 mois (trimestriel)

_ENSURE_TABLE = """
    CREATE TABLE IF NOT EXISTS etalonnages (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        reference           TEXT    NOT NULL DEFAULT 'EET01',
        date_etalonnage     DATE    NOT NULL,
        thermometre_id      TEXT    NOT NULL,
        temperature_mesuree REAL    NOT NULL,
        conforme            INTEGER NOT NULL,
        action_corrective   TEXT    NOT NULL,
        operateur           TEXT    NOT NULL,
        commentaire         TEXT,
        created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
    )
"""


# ---------------------------------------------------------------------------
# Pydantic
# ---------------------------------------------------------------------------

class EtalonnageIn(BaseModel):
    date_etalonnage:     str
    thermometre_id:      str
    temperature_mesuree: float
    action_corrective:   str   # 'conforme' | 'calibrage' | 'remplace'
    operateur:           str
    commentaire:         Optional[str] = None

    @field_validator("action_corrective")
    @classmethod
    def valider_action(cls, v: str) -> str:
        valides = {"conforme", "calibrage", "remplace"}
        if v not in valides:
            raise ValueError(f"action_corrective doit être parmi {valides}")
        return v

    @field_validator("thermometre_id", "operateur")
    @classmethod
    def non_vide(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Ce champ est obligatoire")
        return v.strip()


# ---------------------------------------------------------------------------
# POST /api/etalonnage
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
async def creer_etalonnage(body: EtalonnageIn):
    from src.database import get_db

    conforme = 1 if TEMP_MIN <= body.temperature_mesuree <= TEMP_MAX else 0

    # Vérifier cohérence : action 'conforme' seulement si temp OK
    if body.action_corrective == "conforme" and not conforme:
        raise HTTPException(
            400,
            f"La température {body.temperature_mesuree}°C est hors tolérance "
            f"(0°C ± 0,5°C) — action corrective doit être 'calibrage' ou 'remplace'"
        )

    async with get_db() as db:
        await db.execute(_ENSURE_TABLE)
        cur = await db.execute(
            """
            INSERT INTO etalonnages
                (date_etalonnage, thermometre_id, temperature_mesuree,
                 conforme, action_corrective, operateur, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                body.date_etalonnage,
                body.thermometre_id,
                body.temperature_mesuree,
                conforme,
                body.action_corrective,
                body.operateur,
                body.commentaire,
            ),
        )
        await db.commit()
        row_id = cur.lastrowid
        row = await db.execute_fetchall(
            "SELECT * FROM etalonnages WHERE id = ?", (row_id,)
        )

    logger.info(
        "Étalonnage EET01 enregistré — thermo=%s temp=%.1f conforme=%s par %s",
        body.thermometre_id, body.temperature_mesuree,
        "oui" if conforme else "non", body.operateur,
    )
    return dict(zip(
        ["id","reference","date_etalonnage","thermometre_id",
         "temperature_mesuree","conforme","action_corrective",
         "operateur","commentaire","created_at"],
        row[0],
    ))


# ---------------------------------------------------------------------------
# GET /api/etalonnage/historique
# ---------------------------------------------------------------------------

@router.get("/historique")
async def historique_etalonnages(limit: int = Query(50, ge=1, le=500)):
    from src.database import get_db

    async with get_db() as db:
        await db.execute(_ENSURE_TABLE)
        rows = await db.execute_fetchall(
            """
            SELECT id, reference, date_etalonnage, thermometre_id,
                   temperature_mesuree, conforme, action_corrective,
                   operateur, commentaire, created_at
            FROM etalonnages
            ORDER BY date_etalonnage DESC, created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    cols = ["id","reference","date_etalonnage","thermometre_id",
            "temperature_mesuree","conforme","action_corrective",
            "operateur","commentaire","created_at"]
    return [dict(zip(cols, r)) for r in rows]


# ---------------------------------------------------------------------------
# GET /api/etalonnage/status
# ---------------------------------------------------------------------------

@router.get("/status")
async def statut_etalonnage():
    """
    Retourne le statut trimestriel :
    - dernier étalonnage enregistré
    - date du prochain prévu (+3 mois)
    - 'en_retard' si dépassé ou jamais fait
    """
    from src.database import get_db

    async with get_db() as db:
        await db.execute(_ENSURE_TABLE)
        rows = await db.execute_fetchall(
            """
            SELECT date_etalonnage, thermometre_id, operateur
            FROM etalonnages
            ORDER BY date_etalonnage DESC
            LIMIT 1
            """
        )

    today = _date.today()

    if not rows:
        return {
            "en_retard":         True,
            "jamais_fait":       True,
            "dernier_date":      None,
            "dernier_thermo":    None,
            "dernier_operateur": None,
            "prochain_date":     None,
            "jours_restants":    None,
        }

    dernier_date_str = rows[0][0]
    dernier_date     = _date.fromisoformat(dernier_date_str)
    prochain_date    = dernier_date + timedelta(days=DELAI_JOURS)
    jours_restants   = (prochain_date - today).days

    return {
        "en_retard":         jours_restants < 0,
        "jamais_fait":       False,
        "dernier_date":      dernier_date_str,
        "dernier_thermo":    rows[0][1],
        "dernier_operateur": rows[0][2],
        "prochain_date":     prochain_date.isoformat(),
        "jours_restants":    jours_restants,
    }

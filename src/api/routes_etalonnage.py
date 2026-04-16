"""
routes_etalonnage.py — Étalonnage des thermomètres (EET01)

POST /api/etalonnage                        → Phase 1 : enregistrer l'étalonnage du thermo de référence
GET  /api/etalonnage/{id}                   → détail d'un étalonnage
POST /api/etalonnage/{id}/comparaisons      → Phase 2 : enregistrer les comparaisons enceintes
GET  /api/etalonnage/{id}/comparaisons      → liste des comparaisons d'un étalonnage
GET  /api/etalonnage/historique             → liste de tous les étalonnages
GET  /api/etalonnage/status                 → statut trimestriel (alerte si dépassé)

Règle Phase 1 : 0°C ± 0,5°C (thermo de référence dans eau glacée)
Règle Phase 2 : écart thermo_ref vs sonde Zigbee ≤ ±0,5°C
Fréquence     : trimestrielle (4 fois par an)
"""

import logging
from datetime import date as _date, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/etalonnage", tags=["etalonnage"])

ECART_MAX    =  0.5   # ±0,5°C — seuil conformité pour les deux phases
TEMP_MIN     = -0.5
TEMP_MAX     =  0.5
DELAI_JOURS  =  92    # ~3 mois (trimestriel)


# ---------------------------------------------------------------------------
# Pydantic
# ---------------------------------------------------------------------------

class EtalonnageIn(BaseModel):
    date_etalonnage:     str
    thermometre_ref_id:  int
    temperature_mesuree: float
    action_corrective:   str   # 'conforme' | 'calibrage' | 'remplace'
    operateur:           str
    commentaire:         Optional[str] = None

    @field_validator("action_corrective")
    @classmethod
    def valider_action(cls, v: str) -> str:
        if v not in {"conforme", "calibrage", "remplace"}:
            raise ValueError("action_corrective invalide")
        return v

    @field_validator("operateur")
    @classmethod
    def non_vide(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("L'opérateur est obligatoire")
        return v.strip()


class ComparaisonItem(BaseModel):
    enceinte_id:    int
    enceinte_nom:   str
    temp_zigbee:    float
    temp_reference: float


class ComparaisonsIn(BaseModel):
    comparaisons: List[ComparaisonItem]


# ---------------------------------------------------------------------------
# POST /api/etalonnage
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
async def creer_etalonnage(body: EtalonnageIn):
    from src.database import get_db

    conforme = 1 if TEMP_MIN <= body.temperature_mesuree <= TEMP_MAX else 0

    if body.action_corrective == "conforme" and not conforme:
        raise HTTPException(
            400,
            f"Température {body.temperature_mesuree}°C hors tolérance — "
            "action doit être 'calibrage' ou 'remplace'"
        )
    if body.action_corrective in {"calibrage", "remplace"} and conforme:
        raise HTTPException(
            400,
            "Température conforme — seule l'action 'conforme' est autorisée"
        )

    async with get_db() as db:
        # Vérifier que le thermomètre existe
        row_t = await db.execute_fetchall(
            "SELECT id, nom FROM thermometres_ref WHERE id = ? AND actif = 1",
            (body.thermometre_ref_id,),
        )
        if not row_t:
            raise HTTPException(404, "Thermomètre de référence non trouvé")

        cur = await db.execute(
            """
            INSERT INTO etalonnages
                (date_etalonnage, thermometre_ref_id, temperature_mesuree,
                 conforme, action_corrective, operateur, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                body.date_etalonnage,
                body.thermometre_ref_id,
                body.temperature_mesuree,
                conforme,
                body.action_corrective,
                body.operateur,
                body.commentaire,
            ),
        )
        await db.commit()
        row_id = cur.lastrowid
        rows = await db.execute_fetchall(
            """
            SELECT e.id, e.reference, e.date_etalonnage, e.thermometre_ref_id,
                   t.nom AS thermometre_nom, e.temperature_mesuree, e.conforme,
                   e.action_corrective, e.operateur, e.commentaire, e.created_at
            FROM etalonnages e
            JOIN thermometres_ref t ON t.id = e.thermometre_ref_id
            WHERE e.id = ?
            """,
            (row_id,),
        )

    logger.info(
        "Étalonnage EET01 — thermo=%s temp=%.1f conforme=%s par %s",
        row_t[0][1], body.temperature_mesuree,
        "oui" if conforme else "non", body.operateur,
    )
    return _row_to_dict(rows[0])


# ---------------------------------------------------------------------------
# GET /api/etalonnage/historique   (AVANT /{id} pour éviter collision)
# ---------------------------------------------------------------------------

@router.get("/historique")
async def historique_etalonnages(limit: int = Query(50, ge=1, le=500)):
    from src.database import get_db

    async with get_db() as db:
        rows = await db.execute_fetchall(
            """
            SELECT e.id, e.reference, e.date_etalonnage, e.thermometre_ref_id,
                   t.nom AS thermometre_nom, e.temperature_mesuree, e.conforme,
                   e.action_corrective, e.operateur, e.commentaire, e.created_at
            FROM etalonnages e
            JOIN thermometres_ref t ON t.id = e.thermometre_ref_id
            ORDER BY e.date_etalonnage DESC, e.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# GET /api/etalonnage/status       (AVANT /{id} pour éviter collision)
# ---------------------------------------------------------------------------

@router.get("/status")
async def statut_etalonnage():
    from src.database import get_db

    async with get_db() as db:
        rows = await db.execute_fetchall(
            """
            SELECT e.date_etalonnage, t.nom, e.operateur
            FROM etalonnages e
            JOIN thermometres_ref t ON t.id = e.thermometre_ref_id
            ORDER BY e.date_etalonnage DESC
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

    dernier_date  = _date.fromisoformat(rows[0][0])
    prochain_date = dernier_date + timedelta(days=DELAI_JOURS)
    jours_restants = (prochain_date - today).days

    return {
        "en_retard":         jours_restants < 0,
        "jamais_fait":       False,
        "dernier_date":      rows[0][0],
        "dernier_thermo":    rows[0][1],
        "dernier_operateur": rows[0][2],
        "prochain_date":     prochain_date.isoformat(),
        "jours_restants":    jours_restants,
    }


# ---------------------------------------------------------------------------
# GET /api/etalonnage/{id}
# ---------------------------------------------------------------------------

@router.get("/{etalonnage_id}")
async def detail_etalonnage(etalonnage_id: int):
    from src.database import get_db

    async with get_db() as db:
        rows = await db.execute_fetchall(
            """
            SELECT e.id, e.reference, e.date_etalonnage, e.thermometre_ref_id,
                   t.nom AS thermometre_nom, e.temperature_mesuree, e.conforme,
                   e.action_corrective, e.operateur, e.commentaire, e.created_at
            FROM etalonnages e
            JOIN thermometres_ref t ON t.id = e.thermometre_ref_id
            WHERE e.id = ?
            """,
            (etalonnage_id,),
        )
    if not rows:
        raise HTTPException(404, "Étalonnage non trouvé")
    return _row_to_dict(rows[0])


# ---------------------------------------------------------------------------
# POST /api/etalonnage/{id}/comparaisons
# ---------------------------------------------------------------------------

@router.post("/{etalonnage_id}/comparaisons", status_code=201)
async def enregistrer_comparaisons(etalonnage_id: int, body: ComparaisonsIn):
    from src.database import get_db

    if not body.comparaisons:
        raise HTTPException(400, "Aucune comparaison fournie")

    async with get_db() as db:
        # Vérifier que l'étalonnage existe et est validé
        rows = await db.execute_fetchall(
            "SELECT id, action_corrective FROM etalonnages WHERE id = ?",
            (etalonnage_id,),
        )
        if not rows:
            raise HTTPException(404, "Étalonnage non trouvé")
        if rows[0][1] not in ("conforme", "remplace"):
            raise HTTPException(
                400,
                "Le thermomètre de référence doit être conforme ou remplacé "
                "avant de réaliser les comparaisons"
            )

        # Supprimer les comparaisons existantes si re-soumission
        await db.execute(
            "DELETE FROM etalonnage_comparaisons WHERE etalonnage_id = ?",
            (etalonnage_id,),
        )

        for c in body.comparaisons:
            ecart    = round(c.temp_reference - c.temp_zigbee, 2)
            conforme = 1 if abs(ecart) <= ECART_MAX else 0
            await db.execute(
                """
                INSERT INTO etalonnage_comparaisons
                    (etalonnage_id, enceinte_id, enceinte_nom,
                     temp_zigbee, temp_reference, ecart, conforme)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (etalonnage_id, c.enceinte_id, c.enceinte_nom,
                 c.temp_zigbee, c.temp_reference, ecart, conforme),
            )

        await db.commit()

    logger.info(
        "Comparaisons EET01 enregistrées — étalonnage_id=%d (%d enceintes)",
        etalonnage_id, len(body.comparaisons),
    )
    return {"ok": True, "etalonnage_id": etalonnage_id, "nb": len(body.comparaisons)}


# ---------------------------------------------------------------------------
# GET /api/etalonnage/{id}/comparaisons
# ---------------------------------------------------------------------------

@router.get("/{etalonnage_id}/comparaisons")
async def lister_comparaisons(etalonnage_id: int):
    from src.database import get_db

    async with get_db() as db:
        rows = await db.execute_fetchall(
            """
            SELECT id, enceinte_id, enceinte_nom,
                   temp_zigbee, temp_reference, ecart, conforme, created_at
            FROM etalonnage_comparaisons
            WHERE etalonnage_id = ?
            ORDER BY enceinte_nom
            """,
            (etalonnage_id,),
        )

    cols = ["id","enceinte_id","enceinte_nom","temp_zigbee",
            "temp_reference","ecart","conforme","created_at"]
    return [dict(zip(cols, r)) for r in rows]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _row_to_dict(r) -> dict:
    cols = ["id","reference","date_etalonnage","thermometre_ref_id",
            "thermometre_nom","temperature_mesuree","conforme",
            "action_corrective","operateur","commentaire","created_at"]
    return dict(zip(cols, r))

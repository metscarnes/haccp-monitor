"""
routes_dlc.py — Module Calendrier DLC

GET  /api/dlc/calendrier                → liste des DLCs entre deux dates
POST /api/dlc/devenir                   → enregistrer le devenir d'un produit expiré
GET  /api/dlc/parametres                → seuils d'alerte (rouge / orange / jaune)
PUT  /api/dlc/parametres                → modifier les seuils
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.database import (
    get_db,
    get_dlc_calendrier,
    create_dlc_devenir,
    get_parametres_prefix,
    set_parametre,
)

router = APIRouter(prefix="/api/dlc", tags=["dlc"])

BOUTIQUE_ID = 1

STATUTS_DEVENIR = {"jete", "vendu", "consomme", "autre"}
SOURCES_VALIDES = {"reception_ligne", "fabrication"}


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class DevenirCreate(BaseModel):
    source_type: str                         # 'reception_ligne' | 'fabrication'
    source_id: int
    statut: str                              # 'jete' | 'vendu' | 'consomme' | 'autre'
    personnel_id: Optional[int] = None
    commentaire: Optional[str] = None


class ParametresDlc(BaseModel):
    rouge_jours: int = Field(ge=0, le=365)
    orange_jours: int = Field(ge=0, le=365)
    jaune_jours: int = Field(ge=0, le=365)


# ---------------------------------------------------------------------------
# Calendrier
# ---------------------------------------------------------------------------

@router.get("/calendrier")
async def calendrier(
    date_debut: str = Query(..., description="YYYY-MM-DD"),
    date_fin: str = Query(..., description="YYYY-MM-DD"),
    source: Optional[str] = Query(None, pattern="^(reception|fabrication)$"),
    categorie: Optional[str] = None,
):
    """Retourne les DLCs comprises entre deux dates, toutes sources confondues."""
    async with get_db() as db:
        items = await get_dlc_calendrier(
            db, BOUTIQUE_ID, date_debut, date_fin, source=source, categorie=categorie
        )
        params = await get_parametres_prefix(db, BOUTIQUE_ID, "dlc_alerte_")
    seuils = {
        "rouge_jours":  int(params.get("dlc_alerte_rouge_jours",  "1")),
        "orange_jours": int(params.get("dlc_alerte_orange_jours", "3")),
        "jaune_jours":  int(params.get("dlc_alerte_jaune_jours",  "7")),
    }
    return {"items": items, "seuils": seuils}


# ---------------------------------------------------------------------------
# Devenir (jeté / vendu / consommé)
# ---------------------------------------------------------------------------

@router.post("/devenir", status_code=201)
async def enregistrer_devenir(body: DevenirCreate):
    if body.source_type not in SOURCES_VALIDES:
        raise HTTPException(400, f"source_type invalide (attendu : {SOURCES_VALIDES})")
    if body.statut not in STATUTS_DEVENIR:
        raise HTTPException(400, f"statut invalide (attendu : {STATUTS_DEVENIR})")

    async with get_db() as db:
        await create_dlc_devenir(
            db,
            source_type=body.source_type,
            source_id=body.source_id,
            statut=body.statut,
            personnel_id=body.personnel_id,
            commentaire=body.commentaire,
        )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Paramètres (seuils d'alerte)
# ---------------------------------------------------------------------------

@router.get("/parametres")
async def get_parametres():
    async with get_db() as db:
        params = await get_parametres_prefix(db, BOUTIQUE_ID, "dlc_alerte_")
    return {
        "rouge_jours":  int(params.get("dlc_alerte_rouge_jours",  "1")),
        "orange_jours": int(params.get("dlc_alerte_orange_jours", "3")),
        "jaune_jours":  int(params.get("dlc_alerte_jaune_jours",  "7")),
    }


@router.put("/parametres")
async def update_parametres(body: ParametresDlc):
    if not (body.rouge_jours <= body.orange_jours <= body.jaune_jours):
        raise HTTPException(
            400,
            "Les seuils doivent être croissants : rouge ≤ orange ≤ jaune",
        )
    async with get_db() as db:
        await set_parametre(db, BOUTIQUE_ID, "dlc_alerte_rouge_jours",  str(body.rouge_jours))
        await set_parametre(db, BOUTIQUE_ID, "dlc_alerte_orange_jours", str(body.orange_jours))
        await set_parametre(db, BOUTIQUE_ID, "dlc_alerte_jaune_jours",  str(body.jaune_jours))
    return {"ok": True}

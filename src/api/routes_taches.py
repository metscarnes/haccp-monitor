"""
routes_taches.py — Module Tâches HACCP (12 fiches)

GET    /api/taches/today               → tâches du jour avec statut
GET    /api/taches/types               → types de tâches configurés
POST   /api/taches/types               → créer un type
PUT    /api/taches/types/{id}          → modifier un type
POST   /api/taches/valider             → valider une tâche
GET    /api/taches/historique          → historique des validations
GET    /api/taches/en-retard           → tâches en retard
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.database import (
    get_db,
    get_tache_types, get_tache_type, create_tache_type, update_tache_type,
    create_validation, get_validations,
    get_taches_today, get_taches_en_retard,
)

router = APIRouter(prefix="/api/taches", tags=["taches"])

BOUTIQUE_ID = 1


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class TacheTypeCreate(BaseModel):
    code: str
    libelle: str
    frequence: str          # "quotidien" | "hebdomadaire" | "mensuel" | "evenementiel" | "exceptionnel" | "ponctuel"
    heure_cible: Optional[str] = None
    photo_requise: bool = False


class TacheTypeUpdate(BaseModel):
    libelle: Optional[str] = None
    frequence: Optional[str] = None
    heure_cible: Optional[str] = None
    photo_requise: Optional[bool] = None
    actif: Optional[bool] = None


class ValidationCreate(BaseModel):
    tache_type_id: int
    operateur: str
    date_tache: str                         # "YYYY-MM-DD"
    conforme: Optional[bool] = None
    photo_path: Optional[str] = None
    commentaire: Optional[str] = None
    donnees_specifiques: Optional[Any] = None  # dict JSON propre à chaque fiche


# ---------------------------------------------------------------------------
# Vue du jour
# ---------------------------------------------------------------------------

@router.get("/today")
async def taches_du_jour():
    async with get_db() as db:
        return await get_taches_today(db, BOUTIQUE_ID)


@router.get("/en-retard")
async def taches_en_retard():
    async with get_db() as db:
        return await get_taches_en_retard(db, BOUTIQUE_ID)


# ---------------------------------------------------------------------------
# Types de tâches
# ---------------------------------------------------------------------------

@router.get("/types")
async def lister_types():
    async with get_db() as db:
        return await get_tache_types(db, BOUTIQUE_ID)


@router.post("/types", status_code=201)
async def creer_type(body: TacheTypeCreate):
    async with get_db() as db:
        tid = await create_tache_type(db, {"boutique_id": BOUTIQUE_ID, **body.model_dump()})
        tache = await get_tache_type(db, tid)
    return tache


@router.put("/types/{tache_type_id}")
async def modifier_type(tache_type_id: int, body: TacheTypeUpdate):
    async with get_db() as db:
        ok = await update_tache_type(db, tache_type_id, body.model_dump(exclude_none=True))
        if not ok:
            raise HTTPException(404, "Type de tâche non trouvé ou aucun champ à modifier")
        tache = await get_tache_type(db, tache_type_id)
    return tache


# ---------------------------------------------------------------------------
# Validations
# ---------------------------------------------------------------------------

@router.post("/valider", status_code=201)
async def valider_tache(body: ValidationCreate):
    async with get_db() as db:
        tache = await get_tache_type(db, body.tache_type_id)
        if not tache:
            raise HTTPException(404, "Type de tâche non trouvé")

        vid = await create_validation(db, {
            "boutique_id": BOUTIQUE_ID,
            **body.model_dump(),
        })
    return {"id": vid, "valide": True}


@router.get("/historique")
async def historique_validations(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    type_id: Optional[int] = None,
):
    depuis = datetime.fromisoformat(from_date) if from_date else datetime.now(timezone.utc) - timedelta(days=30)
    jusqu_a = datetime.fromisoformat(to_date) if to_date else datetime.now(timezone.utc)
    async with get_db() as db:
        validations = await get_validations(
            db, BOUTIQUE_ID,
            depuis=depuis,
            jusqu_a=jusqu_a,
            tache_type_id=type_id,
        )
    return validations

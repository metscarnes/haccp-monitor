from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.database import (
    get_db, get_alertes_en_cours, get_alertes_enceinte,
    get_destinataires, create_destinataire,
)

router = APIRouter(tags=["alertes"])


# ---------------------------------------------------------------------------
# Alertes
# ---------------------------------------------------------------------------

@router.get("/api/alertes/en-cours")
async def alertes_en_cours():
    async with get_db() as db:
        return await get_alertes_en_cours(db)


@router.get("/api/enceintes/{enceinte_id}/alertes")
async def alertes_enceinte(enceinte_id: int):
    async with get_db() as db:
        return await get_alertes_enceinte(db, enceinte_id)


# ---------------------------------------------------------------------------
# Destinataires
# ---------------------------------------------------------------------------

class DestinataireCreate(BaseModel):
    nom: str
    email: Optional[str] = None
    telephone: Optional[str] = None


@router.get("/api/destinataires")
async def liste_destinataires():
    async with get_db() as db:
        return await get_destinataires(db)


@router.post("/api/destinataires", status_code=201)
async def ajouter_destinataire(data: DestinataireCreate):
    if not data.email and not data.telephone:
        raise HTTPException(400, "Au moins un email ou un téléphone est requis")
    async with get_db() as db:
        did = await create_destinataire(db, data.model_dump())
    return {"id": did}

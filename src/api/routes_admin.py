"""
routes_admin.py — Configuration admin (personnel, pièges)

GET    /api/admin/personnel             → liste du personnel
POST   /api/admin/personnel             → ajouter un membre
PUT    /api/admin/personnel/{id}        → modifier
GET    /api/admin/pieges                → configuration des pièges
POST   /api/admin/pieges                → ajouter un piège
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.database import (
    get_db,
    get_personnel, create_personnel, update_personnel,
    get_pieges, create_piege,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

BOUTIQUE_ID = 1


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class PersonnelCreate(BaseModel):
    prenom: str


class PersonnelUpdate(BaseModel):
    prenom: Optional[str] = None
    actif: Optional[bool] = None


class PiegeCreate(BaseModel):
    type: str           # "rongeur" | "oiseau"
    identifiant: str    # "P1", "P2", ...
    localisation: Optional[str] = None


# ---------------------------------------------------------------------------
# Personnel
# ---------------------------------------------------------------------------

@router.get("/personnel")
async def lister_personnel():
    async with get_db() as db:
        return await get_personnel(db, BOUTIQUE_ID)


@router.post("/personnel", status_code=201)
async def ajouter_personnel(body: PersonnelCreate):
    async with get_db() as db:
        pid = await create_personnel(db, {"boutique_id": BOUTIQUE_ID, "prenom": body.prenom})
        cursor = await db.execute("SELECT * FROM personnel WHERE id = ?", (pid,))
        row = await cursor.fetchone()
    return dict(row) if row else {"id": pid}


@router.put("/personnel/{personnel_id}")
async def modifier_personnel(personnel_id: int, body: PersonnelUpdate):
    async with get_db() as db:
        ok = await update_personnel(db, personnel_id, body.model_dump(exclude_none=True))
    if not ok:
        raise HTTPException(404, "Personnel non trouvé")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Pièges
# ---------------------------------------------------------------------------

@router.get("/pieges")
async def lister_pieges():
    async with get_db() as db:
        return await get_pieges(db, BOUTIQUE_ID)


@router.post("/pieges", status_code=201)
async def ajouter_piege(body: PiegeCreate):
    async with get_db() as db:
        pid = await create_piege(db, {"boutique_id": BOUTIQUE_ID, **body.model_dump()})
        cursor = await db.execute("SELECT * FROM pieges WHERE id = ?", (pid,))
        row = await cursor.fetchone()
    return dict(row) if row else {"id": pid}


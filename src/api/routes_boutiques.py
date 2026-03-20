from fastapi import APIRouter, HTTPException
from src.database import get_db, get_boutiques, get_boutique, get_dashboard_boutique

router = APIRouter(prefix="/api/boutiques", tags=["boutiques"])


@router.get("")
async def liste_boutiques():
    async with get_db() as db:
        return await get_boutiques(db)


@router.get("/{boutique_id}")
async def detail_boutique(boutique_id: int):
    async with get_db() as db:
        b = await get_boutique(db, boutique_id)
    if not b:
        raise HTTPException(404, "Boutique introuvable")
    return b


@router.get("/{boutique_id}/dashboard")
async def dashboard_boutique(boutique_id: int):
    async with get_db() as db:
        data = await get_dashboard_boutique(db, boutique_id)
    if not data:
        raise HTTPException(404, "Boutique introuvable")
    return data


@router.get("/{boutique_id}/enceintes")
async def enceintes_boutique(boutique_id: int):
    from src.database import get_enceintes
    async with get_db() as db:
        return await get_enceintes(db, boutique_id)

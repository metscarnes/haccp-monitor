from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.database import get_db, get_rapport, create_rapport, get_boutique

router = APIRouter(prefix="/api/rapports", tags=["rapports"])


class RapportDemande(BaseModel):
    boutique_id: int
    type: str = "journalier"          # "journalier" | "mensuel"
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None


@router.post("/generer", status_code=202)
async def generer_rapport(data: RapportDemande):
    from src.report_generator import generer

    now = datetime.now(timezone.utc).date()

    if data.type == "journalier":
        debut = data.date_debut or (now - timedelta(days=1))
        fin   = data.date_fin   or debut
    elif data.type == "mensuel":
        debut = data.date_debut or date(now.year, now.month, 1)
        fin   = data.date_fin   or now
    else:
        raise HTTPException(400, "type doit être 'journalier' ou 'mensuel'")

    async with get_db() as db:
        boutique = await get_boutique(db, data.boutique_id)
        if not boutique:
            raise HTTPException(404, "Boutique introuvable")

        rapport_id = await generer(db, data.boutique_id, data.type, debut, fin)

    return {"rapport_id": rapport_id, "statut": "généré"}


@router.get("/{rapport_id}/pdf")
async def telecharger_rapport(rapport_id: int):
    async with get_db() as db:
        rapport = await get_rapport(db, rapport_id)

    if not rapport:
        raise HTTPException(404, "Rapport introuvable")
    if not rapport.get("fichier_path"):
        raise HTTPException(404, "Fichier PDF non encore généré")

    from pathlib import Path
    path = Path(rapport["fichier_path"])
    if not path.exists():
        raise HTTPException(404, "Fichier PDF introuvable sur le disque")

    return FileResponse(
        str(path),
        media_type="application/pdf",
        filename=path.name,
    )


@router.get("")
async def liste_rapports(boutique_id: Optional[int] = None):
    async with get_db() as db:
        if boutique_id:
            cursor = await db.execute(
                "SELECT * FROM rapports WHERE boutique_id = ? ORDER BY created_at DESC",
                (boutique_id,),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM rapports ORDER BY created_at DESC LIMIT 50"
            )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]

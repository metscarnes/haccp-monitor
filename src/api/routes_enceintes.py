from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from src.database import (
    get_db, get_enceinte, get_enceintes, get_latest_releve,
    create_enceinte, update_enceinte, delete_enceinte, get_alerte_en_cours,
    get_boutiques,
)

router = APIRouter(prefix="/api/enceintes", tags=["enceintes"])


class EnceinteCree(BaseModel):
    boutique_id: int
    nom: str
    type: str
    sonde_zigbee_id: Optional[str] = None
    seuil_temp_min: float = 0.0
    seuil_temp_max: float = 4.0
    seuil_hum_max: float = 90.0
    delai_alerte_minutes: int = 5


class EnceinteMaj(BaseModel):
    nom: Optional[str] = None
    type: Optional[str] = None
    sonde_zigbee_id: Optional[str] = None
    seuil_temp_min: Optional[float] = None
    seuil_temp_max: Optional[float] = None
    seuil_hum_max: Optional[float] = None
    delai_alerte_minutes: Optional[int] = None
    actif: Optional[bool] = None


@router.get("")
async def lister_enceintes(boutique_id: Optional[int] = Query(None)):
    async with get_db() as db:
        if boutique_id is not None:
            rows = await get_enceintes(db, boutique_id)
        else:
            boutiques = await get_boutiques(db)
            rows = []
            for b in boutiques:
                rows.extend(await get_enceintes(db, b["id"]))
    return [{"id": e["id"], "nom": e["nom"], "type": e["type"], "boutique_id": e["boutique_id"]} for e in rows]


@router.post("", status_code=201)
async def creer_enceinte(data: EnceinteCree):
    async with get_db() as db:
        eid = await create_enceinte(db, data.model_dump())
        return {"id": eid}


@router.get("/{enceinte_id}")
async def detail_enceinte(enceinte_id: int):
    async with get_db() as db:
        enc = await get_enceinte(db, enceinte_id)
    if not enc:
        raise HTTPException(404, "Enceinte introuvable")
    return enc


@router.delete("/{enceinte_id}", status_code=200)
async def supprimer_enceinte(enceinte_id: int):
    async with get_db() as db:
        ok = await delete_enceinte(db, enceinte_id)
    if not ok:
        raise HTTPException(404, "Enceinte introuvable")
    return {"ok": True}


@router.put("/{enceinte_id}")
async def modifier_enceinte(enceinte_id: int, data: EnceinteMaj):
    async with get_db() as db:
        ok = await update_enceinte(db, enceinte_id, data.model_dump(exclude_none=True))
    if not ok:
        raise HTTPException(400, "Aucun champ à mettre à jour")
    return {"ok": True}


@router.get("/{enceinte_id}/status")
async def statut_enceinte(enceinte_id: int):
    async with get_db() as db:
        enc = await get_enceinte(db, enceinte_id)
        if not enc:
            raise HTTPException(404, "Enceinte introuvable")
        dernier = await get_latest_releve(db, enceinte_id)

        alertes_actives = []
        for t in ("temperature_haute", "temperature_basse", "perte_signal", "batterie_faible"):
            a = await get_alerte_en_cours(db, enceinte_id, t)
            if a:
                alertes_actives.append(a)

    statut = "inconnu"
    if dernier:
        t = dernier["temperature"]
        if t < enc["seuil_temp_min"] or t > enc["seuil_temp_max"]:
            statut = "alerte"
        elif t < enc["seuil_temp_min"] + 0.5 or t > enc["seuil_temp_max"] - 0.5:
            statut = "attention"
        else:
            statut = "ok"

    return {
        **enc,
        "temperature_actuelle": dernier["temperature"] if dernier else None,
        "humidite_actuelle": dernier["humidite"] if dernier else None,
        "batterie_sonde": dernier["batterie"] if dernier else None,
        "derniere_mesure": dernier["horodatage"] if dernier else None,
        "statut": statut,
        "alertes_actives": alertes_actives,
    }

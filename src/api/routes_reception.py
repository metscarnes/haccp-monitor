"""
routes_reception.py — Module Contrôles Réception (fiches 8 et 9)

GET    /api/fournisseurs                → liste
POST   /api/fournisseurs                → ajouter
POST   /api/receptions                  → créer réception (étape 1)
POST   /api/receptions/{id}/lignes      → ajouter ligne produit (étape 2)
POST   /api/receptions/{id}/finaliser   → clôturer la fiche
GET    /api/receptions                  → historique
GET    /api/receptions/{id}             → détail
POST   /api/non-conformites             → déclarer NC fournisseur
GET    /api/non-conformites             → historique NC
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.database import (
    get_db,
    get_fournisseurs, create_fournisseur, update_fournisseur,
    create_reception, add_reception_ligne, finaliser_reception,
    get_receptions, get_reception,
    create_non_conformite, get_non_conformites,
)

router = APIRouter(prefix="/api", tags=["reception"])

BOUTIQUE_ID = 1


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class FournisseurCreate(BaseModel):
    nom: str


class FournisseurUpdate(BaseModel):
    nom: Optional[str] = None
    actif: Optional[bool] = None


class ReceptionCreate(BaseModel):
    fournisseur_id: Optional[int] = None
    fournisseur_nom: str
    numero_bon_livraison: Optional[str] = None
    operateur: str
    heure_livraison: Optional[str] = None
    temperature_camion: Optional[float] = None
    proprete_camion: Optional[str] = None   # "S" | "NS"
    commentaire: Optional[str] = None


class ReceptionLigneCreate(BaseModel):
    produit_nom: str
    temperature_produit: Optional[float] = None
    integrite_emballage: Optional[str] = None   # "S" | "NS"
    dlc: Optional[str] = None
    numero_lot: Optional[str] = None
    quantite: Optional[float] = None
    heure_stockage: Optional[str] = None
    conforme: Optional[bool] = None


class ReceptionFinaliser(BaseModel):
    conforme: bool


class NonConformiteCreate(BaseModel):
    reception_id: Optional[int] = None
    reception_ligne_id: Optional[int] = None
    operateur: str
    date_livraison: Optional[str] = None
    fournisseur_nom: Optional[str] = None
    produits: Optional[str] = None
    date_fabrication: Optional[str] = None
    dlc: Optional[str] = None
    nombre_barquettes: Optional[int] = None
    nature_nc: Optional[list[str]] = None      # ["temperature", "dlc", ...]
    commentaires: Optional[str] = None
    refuse_livraison: bool = False
    nc_apres_livraison: bool = False
    info_ddpp: bool = False


# ---------------------------------------------------------------------------
# Fournisseurs
# ---------------------------------------------------------------------------

@router.get("/fournisseurs")
async def lister_fournisseurs():
    async with get_db() as db:
        return await get_fournisseurs(db, BOUTIQUE_ID)


@router.post("/fournisseurs", status_code=201)
async def ajouter_fournisseur(body: FournisseurCreate):
    async with get_db() as db:
        fid = await create_fournisseur(db, {"boutique_id": BOUTIQUE_ID, "nom": body.nom})
        cursor = await db.execute("SELECT * FROM fournisseurs WHERE id = ?", (fid,))
        row = await cursor.fetchone()
    return dict(row) if row else {"id": fid}


@router.put("/fournisseurs/{fournisseur_id}")
async def modifier_fournisseur(fournisseur_id: int, body: FournisseurUpdate):
    async with get_db() as db:
        ok = await update_fournisseur(db, fournisseur_id, body.model_dump(exclude_none=True))
    if not ok:
        raise HTTPException(404, "Fournisseur non trouvé")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Réceptions
# ---------------------------------------------------------------------------

@router.post("/receptions", status_code=201)
async def creer_reception(body: ReceptionCreate):
    async with get_db() as db:
        rid = await create_reception(db, {"boutique_id": BOUTIQUE_ID, **body.model_dump()})
    return {"id": rid}


@router.post("/receptions/{reception_id}/lignes", status_code=201)
async def ajouter_ligne(reception_id: int, body: ReceptionLigneCreate):
    async with get_db() as db:
        # Vérifier que la réception existe
        rec = await get_reception(db, reception_id)
        if not rec:
            raise HTTPException(404, "Réception non trouvée")
        lid = await add_reception_ligne(db, reception_id, body.model_dump())
    return {"id": lid}


@router.post("/receptions/{reception_id}/finaliser")
async def finaliser(reception_id: int, body: ReceptionFinaliser):
    async with get_db() as db:
        rec = await get_reception(db, reception_id)
        if not rec:
            raise HTTPException(404, "Réception non trouvée")
        await finaliser_reception(db, reception_id, body.conforme)
        reception = await get_reception(db, reception_id)
    return reception


@router.get("/receptions")
async def historique_receptions(limit: int = 50):
    async with get_db() as db:
        return await get_receptions(db, BOUTIQUE_ID, limit=limit)


@router.get("/receptions/{reception_id}")
async def detail_reception(reception_id: int):
    async with get_db() as db:
        rec = await get_reception(db, reception_id)
    if not rec:
        raise HTTPException(404, "Réception non trouvée")
    return rec


# ---------------------------------------------------------------------------
# Non-conformités
# ---------------------------------------------------------------------------

@router.post("/non-conformites", status_code=201)
async def declarer_non_conformite(body: NonConformiteCreate):
    async with get_db() as db:
        nc_id = await create_non_conformite(db, {"boutique_id": BOUTIQUE_ID, **body.model_dump()})
    return {"id": nc_id}


@router.get("/non-conformites")
async def historique_non_conformites(limit: int = 50):
    async with get_db() as db:
        return await get_non_conformites(db, BOUTIQUE_ID, limit=limit)

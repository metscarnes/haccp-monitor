"""
routes_attente.py — Produits en attente de traçabilité (lot/DLC manquant à la réception).

À la réception, un produit sans N° de lot et/ou sans DLC est accepté mais marqué
« en_attente » : il n'entre PAS au stock tant que les infos ne sont pas complétées.
Cette file est rappelée par une tâche HACCP non-masquable dans le Hub.

GET    /api/attente/lignes            → liste des produits en attente
GET    /api/attente/count             → nombre (léger, pour le Hub)
PUT    /api/attente/lignes/{id}       → compléter lot/DLC/DLUO/date_abattage
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.database import (
    get_db,
    get_lignes_en_attente,
    count_lignes_en_attente,
    completer_ligne_attente,
    marquer_non_recu,
    changer_produit_ligne_attente,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/attente", tags=["attente"])


class CompletionBody(BaseModel):
    numero_lot: Optional[str] = None
    dlc: Optional[str] = None
    dluo: Optional[str] = None
    date_abattage: Optional[str] = None
    lot_interne: int = 0


@router.get("/lignes")
async def lignes_en_attente():
    """Liste des produits en attente de complétion (lot/DLC manquant)."""
    async with get_db() as db:
        lignes = await get_lignes_en_attente(db)
    return {"lignes": lignes, "count": len(lignes)}


@router.get("/count")
async def count_en_attente():
    """Nombre de produits en attente — utilisé par le résumé du Hub."""
    async with get_db() as db:
        n = await count_lignes_en_attente(db)
    return {"count": n}


@router.put("/lignes/{ligne_id}")
async def completer(ligne_id: int, body: CompletionBody):
    """Complète les infos de traçabilité. Si lot + date présents → entre en stock."""
    async with get_db() as db:
        ligne = await completer_ligne_attente(
            db, ligne_id,
            numero_lot=body.numero_lot,
            dlc=body.dlc,
            dluo=body.dluo,
            date_abattage=body.date_abattage,
            lot_interne=body.lot_interne,
        )
    if ligne is None:
        raise HTTPException(404, "Ligne de réception introuvable")
    return ligne


@router.put("/lignes/{ligne_id}/non-recu")
async def non_recu(ligne_id: int):
    """Marque la ligne comme non reçue — quitte la file d'attente sans entrer en stock."""
    async with get_db() as db:
        ligne = await marquer_non_recu(db, ligne_id)
    if ligne is None:
        raise HTTPException(404, "Ligne de réception introuvable")
    return {"statut": "non_recu", "ligne_id": ligne_id}


class ChangerProduitBody(BaseModel):
    catalogue_fournisseur_id: int


@router.put("/lignes/{ligne_id}/produit")
async def changer_produit(ligne_id: int, body: ChangerProduitBody):
    """Remplace l'article catalogue d'une ligne en_attente (correction d'identification)."""
    async with get_db() as db:
        ligne = await changer_produit_ligne_attente(db, ligne_id, body.catalogue_fournisseur_id)
    if ligne is None:
        raise HTTPException(404, "Ligne ou article introuvable")
    return ligne

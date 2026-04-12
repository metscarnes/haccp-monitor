"""
routes_fabrication.py — Module Fabrication (Recettes & Traçabilité)

GET  /api/recettes                          → liste des recettes
POST /api/recettes                          → créer recette + ingrédients
GET  /api/fabrications/fifo-lots            → suggestions FIFO par recette
POST /api/fabrications                      → enregistrer une fabrication
"""

import logging
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.database import (
    get_db,
    get_recettes,
    get_recette,
    create_recette,
    get_fifo_lots,
    create_fabrication,
    get_fabrications_historique,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["fabrication"])


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class IngredientCreate(BaseModel):
    produit_id: int
    quantite: Optional[float] = None
    unite: Optional[str] = None          # kg, g, L, pièce…


class RecetteCreate(BaseModel):
    nom: str
    produit_fini_id: int
    dlc_jours: int
    instructions: Optional[str] = None
    ingredients: list[IngredientCreate] = []


class LotValide(BaseModel):
    """Un lot confirmé ou saisi manuellement pour un ingrédient."""
    recette_ingredient_id: int
    reception_ligne_id: int


class FabricationCreate(BaseModel):
    recette_id: int
    date: str                            # "YYYY-MM-DD"
    personnel_id: int
    lots: list[LotValide]
    info_complementaire: Optional[str] = None
    dlc_finale: Optional[str] = None    # "YYYY-MM-DD" calculée côté client (règle HACCP)


# ---------------------------------------------------------------------------
# A. Gestion des recettes
# ---------------------------------------------------------------------------

@router.get("/recettes")
async def liste_recettes():
    """Retourne la liste de toutes les recettes avec le produit fini associé."""
    async with get_db() as db:
        recettes = await get_recettes(db)
    return recettes


@router.get("/recettes/{recette_id}")
async def detail_recette(recette_id: int):
    """Retourne le détail d'une recette avec ses ingrédients."""
    async with get_db() as db:
        recette = await get_recette(db, recette_id)
    if not recette:
        raise HTTPException(status_code=404, detail="Recette introuvable")
    return recette


@router.post("/recettes", status_code=201)
async def creer_recette(payload: RecetteCreate):
    """
    Crée une recette complète avec sa liste d'ingrédients.

    Retourne la recette créée (avec ses ingrédients) et le statut 201.
    """
    async with get_db() as db:
        try:
            recette = await create_recette(
                db,
                nom=payload.nom,
                produit_fini_id=payload.produit_fini_id,
                dlc_jours=payload.dlc_jours,
                instructions=payload.instructions,
                ingredients=[ing.model_dump() for ing in payload.ingredients],
            )
        except Exception as exc:
            logger.error("Erreur création recette : %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))
    return recette


# ---------------------------------------------------------------------------
# B. Moteur FIFO
# ---------------------------------------------------------------------------

@router.get("/fabrications/fifo-lots")
async def fifo_lots(recette_id: int = Query(..., description="ID de la recette à préparer")):
    """
    Pour chaque ingrédient de la recette, retourne le lot disponible le plus
    ancien selon la logique FIFO (DLC la plus courte → date réception la plus
    ancienne). Si aucun lot n'est disponible, `lot_fifo` est null.
    """
    async with get_db() as db:
        recette = await get_recette(db, recette_id)
        if not recette:
            raise HTTPException(status_code=404, detail="Recette introuvable")
        suggestions = await get_fifo_lots(db, recette_id)
    return {
        "recette_id":  recette_id,
        "recette_nom": recette["nom"],
        "ingredients": suggestions,
    }


# ---------------------------------------------------------------------------
# B2. Lot FIFO unitaire pour un produit donné (utilisé par le wizard substitution)
# ---------------------------------------------------------------------------

@router.get("/fabrications/produit-fifo/{produit_id}")
async def fifo_produit(produit_id: int):
    """
    Retourne le meilleur lot FIFO disponible pour un produit donné :
    la ligne de reception_lignes avec la DLC la plus courte
    (à égalité : date de réception la plus ancienne).

    Retourne 404 si aucune réception n'existe pour ce produit.
    """
    async with get_db() as db:
        cur = await db.execute(
            """
            SELECT rl.id              AS id,
                   rl.numero_lot,
                   rl.dlc,
                   rl.poids_kg,
                   r.date_reception
            FROM   reception_lignes rl
            JOIN   receptions r ON r.id = rl.reception_id
            WHERE  rl.produit_id = ?
            ORDER BY
                CASE WHEN rl.dlc IS NOT NULL THEN 0 ELSE 1 END,
                rl.dlc           ASC,
                r.date_reception ASC
            LIMIT 1
            """,
            (produit_id,),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Aucun lot disponible pour ce produit")
    return dict(row)


# ---------------------------------------------------------------------------
# C. Historique des fabrications
# ---------------------------------------------------------------------------

@router.get("/fabrications")
async def historique_fabrications(
    date_debut: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    date_fin:   Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    recette_id: Optional[int] = Query(None, description="Filtrer par recette"),
    limit:  int = Query(50, ge=1, le=200),
    offset: int = Query(0,  ge=0),
):
    """
    Retourne la liste des fabrications avec, pour chaque fabrication,
    les ingrédients utilisés (produit, lot, DLC).
    """
    async with get_db() as db:
        fabrications = await get_fabrications_historique(
            db,
            date_debut=date_debut,
            date_fin=date_fin,
            recette_id=recette_id,
            limit=limit,
            offset=offset,
        )
    return fabrications


# ---------------------------------------------------------------------------
# D. Enregistrement d'une fabrication
# ---------------------------------------------------------------------------

@router.post("/fabrications", status_code=201)
async def enregistrer_fabrication(payload: FabricationCreate):
    """
    Enregistre une fabrication :
    - Génère le lot interne MC-YYYYMMDD-XXXX
    - Insère dans `fabrications`
    - Insère les liens de traçabilité dans `fabrication_lots`

    Retourne l'objet fabrication créé (201).
    """
    if not payload.lots:
        raise HTTPException(status_code=422, detail="Au moins un lot doit être renseigné")

    async with get_db() as db:
        # Vérifier que la recette existe
        recette = await get_recette(db, payload.recette_id)
        if not recette:
            raise HTTPException(status_code=404, detail="Recette introuvable")

        try:
            fabrication = await create_fabrication(
                db,
                recette_id=payload.recette_id,
                date=payload.date,
                personnel_id=payload.personnel_id,
                lots=[lot.model_dump() for lot in payload.lots],
                info_complementaire=payload.info_complementaire,
                recette_nom=recette["nom"],
                dlc_finale=payload.dlc_finale,
            )
        except Exception as exc:
            logger.error("Erreur création fabrication : %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))

    return fabrication

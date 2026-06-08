"""
routes_vente.py — Catalogue de VENTE (produits finis fabriqués)

Le catalogue de vente est la source des « produits finis » des recettes
(sortie de production, étiquette). Il est indépendant du catalogue interne
(produits) et du catalogue d'achats (catalogue_fournisseur).

GET    /api/vente/catalogue            → liste des produits finis (filtres)
GET    /api/vente/catalogue/{id}       → détail
POST   /api/vente/catalogue            → créer un produit fini
PUT    /api/vente/catalogue/{id}       → modifier
DELETE /api/vente/catalogue/{id}       → désactiver (ou supprimer si permanent=true)
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.routes_auth import require_admin
from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vente", tags=["vente"])


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class ProduitVenteCreate(BaseModel):
    nom: str
    code_vente: Optional[str] = None
    prix_vente_ttc: Optional[float] = None
    tva_percent: Optional[float] = 5.5
    dlc_jours: int = 3
    temperature_conservation: Optional[str] = "0°C à +4°C"
    format_etiquette: Optional[str] = "standard_60x40"
    famille: Optional[str] = None
    sous_famille: Optional[str] = None


class ProduitVenteUpdate(BaseModel):
    nom: Optional[str] = None
    code_vente: Optional[str] = None
    prix_vente_ttc: Optional[float] = None
    tva_percent: Optional[float] = None
    dlc_jours: Optional[int] = None
    temperature_conservation: Optional[str] = None
    format_etiquette: Optional[str] = None
    famille: Optional[str] = None
    sous_famille: Optional[str] = None
    actif: Optional[bool] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/catalogue")
async def liste_catalogue_vente(
    q: Optional[str] = Query(None),
    actif_only: bool = Query(True),
):
    async with get_db() as db:
        sql = "SELECT * FROM catalogue_vente WHERE boutique_id = 1"
        params: list = []
        if actif_only:
            sql += " AND actif = 1"
        if q:
            sql += " AND nom LIKE ?"
            params.append(f"%{q}%")
        sql += " ORDER BY famille, sous_famille, nom"
        cur = await db.execute(sql, params)
        return [dict(r) for r in await cur.fetchall()]


@router.get("/catalogue/{produit_id}")
async def detail_produit_vente(produit_id: int):
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM catalogue_vente WHERE id = ?", (produit_id,))
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Produit de vente introuvable")
    return dict(row)


@router.post("/catalogue", status_code=201)
async def creer_produit_vente(body: ProduitVenteCreate, _=Depends(require_admin)):
    async with get_db() as db:
        cur = await db.execute(
            """INSERT INTO catalogue_vente
                   (boutique_id, nom, code_vente, prix_vente_ttc, tva_percent,
                    dlc_jours, temperature_conservation, format_etiquette, famille, sous_famille)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (body.nom, body.code_vente, body.prix_vente_ttc, body.tva_percent,
             body.dlc_jours, body.temperature_conservation, body.format_etiquette,
             body.famille, body.sous_famille),
        )
        await db.commit()
        cur2 = await db.execute("SELECT * FROM catalogue_vente WHERE id = ?", (cur.lastrowid,))
        return dict(await cur2.fetchone())


@router.put("/catalogue/{produit_id}")
async def modifier_produit_vente(produit_id: int, body: ProduitVenteUpdate, _=Depends(require_admin)):
    async with get_db() as db:
        cur = await db.execute("SELECT id FROM catalogue_vente WHERE id = ?", (produit_id,))
        if not await cur.fetchone():
            raise HTTPException(404, "Produit de vente introuvable")

        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        if not fields:
            raise HTTPException(400, "Aucun champ à modifier")

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [produit_id]
        await db.execute(f"UPDATE catalogue_vente SET {set_clause} WHERE id = ?", values)
        await db.commit()

        cur2 = await db.execute("SELECT * FROM catalogue_vente WHERE id = ?", (produit_id,))
        return dict(await cur2.fetchone())


@router.delete("/catalogue/{produit_id}", status_code=200)
async def supprimer_produit_vente(
    produit_id: int, permanent: bool = Query(False), _=Depends(require_admin)
):
    async with get_db() as db:
        if permanent:
            # Une recette peut référencer ce produit fini : on délie avant suppression.
            await db.execute(
                "UPDATE recettes SET catalogue_vente_id = NULL WHERE catalogue_vente_id = ?",
                (produit_id,),
            )
            await db.execute("DELETE FROM catalogue_vente WHERE id = ?", (produit_id,))
        else:
            await db.execute("UPDATE catalogue_vente SET actif = 0 WHERE id = ?", (produit_id,))
        await db.commit()
    return {"ok": True}

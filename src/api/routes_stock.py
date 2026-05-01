"""
routes_stock.py — Vue stock unifiée (FIFO toutes sources confondues)

GET /api/stock
    ?type=tous|brut|fini       (défaut: tous)
    &categorie=plat_cuisine    (filtre catégorie produit)
    &produit_id=42             (zoom sur un produit)
    &dlc_max=2026-05-15        (planning : DLC <= cette date)
    &inclure_expires=false     (par défaut on n'inclut pas les périmés)

Sources unifiées :
    📦 reception_lignes (matières premières fournisseur)
    🔪 fabrications     (produits finis maison)
    🔥 cuissons         (cuits non refroidis)
    ❄️ refroidissements (cuits-refroidis prêts à vendre/servir)

Tri FIFO : DLC ascendante, puis date_origine ascendante.
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.database import get_db, get_stock_unifie

router = APIRouter(prefix="/api/stock", tags=["stock"])

BOUTIQUE_ID = 1


@router.get("")
async def stock_unifie(
    type: str = Query("tous", pattern="^(tous|brut|fini)$"),
    categorie: Optional[str] = Query(None),
    produit_id: Optional[int] = Query(None, ge=1),
    dlc_max: Optional[str] = Query(None, description="YYYY-MM-DD inclusif"),
    inclure_expires: bool = Query(False),
):
    """Stock vivant FIFO, multi-sources, prêt à afficher avec emojis."""
    async with get_db() as db:
        items = await get_stock_unifie(
            db,
            boutique_id=BOUTIQUE_ID,
            type_produit=type,
            categorie=categorie,
            produit_id=produit_id,
            inclure_expires=inclure_expires,
            dlc_max=dlc_max,
        )

    # Statistiques agrégées (utiles pour bandeau d'en-tête côté UI)
    par_source = {"reception_ligne": 0, "fabrication": 0, "cuisson": 0, "refroidissement": 0}
    expirent_3j = 0
    for it in items:
        par_source[it["source_type"]] = par_source.get(it["source_type"], 0) + 1
        jr = it.get("jours_restants")
        if jr is not None and 0 <= jr <= 3:
            expirent_3j += 1

    return {
        "items": items,
        "total": len(items),
        "par_source": par_source,
        "expirent_3j": expirent_3j,
    }

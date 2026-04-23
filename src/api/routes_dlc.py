"""
routes_dlc.py — Module Calendrier DLC

GET  /api/dlc/calendrier                → liste des DLCs entre deux dates
POST /api/dlc/devenir                   → enregistrer le devenir d'un produit expiré
GET  /api/dlc/devenir                   → historique des devenirs enregistrés
GET  /api/dlc/parametres                → seuils d'alerte (rouge / orange / jaune)
PUT  /api/dlc/parametres                → modifier les seuils
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.database import (
    get_db,
    get_dlc_calendrier,
    create_dlc_devenir,
    get_parametres_prefix,
    set_parametre,
)

router = APIRouter(prefix="/api/dlc", tags=["dlc"])

BOUTIQUE_ID = 1

STATUTS_DEVENIR = {"jete", "vendu", "consomme", "autre"}
SOURCES_VALIDES = {"reception_ligne", "fabrication"}


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class DevenirCreate(BaseModel):
    source_type: str                         # 'reception_ligne' | 'fabrication'
    source_id: int
    statut: str                              # 'jete' | 'vendu' | 'consomme' | 'autre'
    personnel_id: Optional[int] = None
    commentaire: Optional[str] = None


class ParametresDlc(BaseModel):
    rouge_jours: int = Field(ge=0, le=365)
    orange_jours: int = Field(ge=0, le=365)
    jaune_jours: int = Field(ge=0, le=365)


# ---------------------------------------------------------------------------
# Calendrier
# ---------------------------------------------------------------------------

@router.get("/calendrier")
async def calendrier(
    date_debut: str = Query(..., description="YYYY-MM-DD"),
    date_fin: str = Query(..., description="YYYY-MM-DD"),
    source: Optional[str] = Query(None, pattern="^(reception|fabrication)$"),
    categorie: Optional[str] = None,
):
    """Retourne les DLCs comprises entre deux dates, toutes sources confondues."""
    async with get_db() as db:
        items = await get_dlc_calendrier(
            db, BOUTIQUE_ID, date_debut, date_fin, source=source, categorie=categorie
        )
        params = await get_parametres_prefix(db, BOUTIQUE_ID, "dlc_alerte_")
    seuils = {
        "rouge_jours":  int(params.get("dlc_alerte_rouge_jours",  "1")),
        "orange_jours": int(params.get("dlc_alerte_orange_jours", "3")),
        "jaune_jours":  int(params.get("dlc_alerte_jaune_jours",  "7")),
    }
    return {"items": items, "seuils": seuils}


# ---------------------------------------------------------------------------
# Devenir (jeté / vendu / consommé)
# ---------------------------------------------------------------------------

@router.post("/devenir", status_code=201)
async def enregistrer_devenir(body: DevenirCreate):
    if body.source_type not in SOURCES_VALIDES:
        raise HTTPException(400, f"source_type invalide (attendu : {SOURCES_VALIDES})")
    if body.statut not in STATUTS_DEVENIR:
        raise HTTPException(400, f"statut invalide (attendu : {STATUTS_DEVENIR})")

    async with get_db() as db:
        await create_dlc_devenir(
            db,
            source_type=body.source_type,
            source_id=body.source_id,
            statut=body.statut,
            personnel_id=body.personnel_id,
            commentaire=body.commentaire,
        )
    return {"ok": True}


@router.get("/devenir")
async def historique_devenir(
    date_debut:  Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_fin:    Optional[str] = Query(None, description="YYYY-MM-DD"),
    statut:      Optional[str] = Query(None, description="jete | vendu | consomme | autre"),
    source_type: Optional[str] = Query(None, description="reception_ligne | fabrication"),
    limit:       int = Query(100, ge=1, le=500),
):
    """Historique des devenirs DLC (jetés / vendus / consommés / autre).

    Joint les tables `reception_lignes` / `fabrications` pour enrichir chaque
    enregistrement avec le nom du produit, le n° de lot et la DLC d'origine.
    """
    if statut is not None and statut not in STATUTS_DEVENIR:
        raise HTTPException(400, f"statut invalide (attendu : {STATUTS_DEVENIR})")
    if source_type is not None and source_type not in SOURCES_VALIDES:
        raise HTTPException(400, f"source_type invalide (attendu : {SOURCES_VALIDES})")

    clauses: list[str] = []
    params:  list = []
    if date_debut:
        clauses.append("DATE(d.created_at) >= ?")
        params.append(date_debut)
    if date_fin:
        clauses.append("DATE(d.created_at) <= ?")
        params.append(date_fin)
    if statut:
        clauses.append("d.statut = ?")
        params.append(statut)
    if source_type:
        clauses.append("d.source_type = ?")
        params.append(source_type)
    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)

    sql = f"""
        SELECT
            d.id,
            d.source_type,
            d.source_id,
            d.statut,
            d.commentaire,
            d.created_at,
            pers.prenom AS personnel_prenom,
            CASE d.source_type
                WHEN 'reception_ligne' THEN p.nom
                WHEN 'fabrication'     THEN r.nom
            END AS produit_nom,
            CASE d.source_type
                WHEN 'reception_ligne' THEN rl.dlc
                WHEN 'fabrication'     THEN f.dlc_finale
            END AS dlc,
            CASE d.source_type
                WHEN 'reception_ligne' THEN rl.numero_lot
                WHEN 'fabrication'     THEN f.lot_interne
            END AS numero_lot,
            CASE d.source_type
                WHEN 'reception_ligne' THEN rl.poids_kg
                WHEN 'fabrication'     THEN f.poids_fabrique
            END AS poids_kg,
            CASE d.source_type
                WHEN 'reception_ligne' THEN fo.nom
                WHEN 'fabrication'     THEN NULL
            END AS fournisseur_nom
        FROM       dlc_devenir     d
        LEFT JOIN  reception_lignes rl ON d.source_type = 'reception_ligne' AND rl.id = d.source_id
        LEFT JOIN  produits         p  ON p.id = rl.produit_id
        LEFT JOIN  fournisseurs     fo ON fo.id = rl.fournisseur_id
        LEFT JOIN  fabrications     f  ON d.source_type = 'fabrication' AND f.id = d.source_id
        LEFT JOIN  recettes         r  ON r.id = f.recette_id
        LEFT JOIN  personnel        pers ON pers.id = d.personnel_id
        {where_sql}
        ORDER BY d.created_at DESC, d.id DESC
        LIMIT ?
    """

    async with get_db() as db:
        cur = await db.execute(sql, tuple(params))
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Paramètres (seuils d'alerte)
# ---------------------------------------------------------------------------

@router.get("/parametres")
async def get_parametres():
    async with get_db() as db:
        params = await get_parametres_prefix(db, BOUTIQUE_ID, "dlc_alerte_")
    return {
        "rouge_jours":  int(params.get("dlc_alerte_rouge_jours",  "1")),
        "orange_jours": int(params.get("dlc_alerte_orange_jours", "3")),
        "jaune_jours":  int(params.get("dlc_alerte_jaune_jours",  "7")),
    }


@router.put("/parametres")
async def update_parametres(body: ParametresDlc):
    if not (body.rouge_jours <= body.orange_jours <= body.jaune_jours):
        raise HTTPException(
            400,
            "Les seuils doivent être croissants : rouge ≤ orange ≤ jaune",
        )
    async with get_db() as db:
        await set_parametre(db, BOUTIQUE_ID, "dlc_alerte_rouge_jours",  str(body.rouge_jours))
        await set_parametre(db, BOUTIQUE_ID, "dlc_alerte_orange_jours", str(body.orange_jours))
        await set_parametre(db, BOUTIQUE_ID, "dlc_alerte_jaune_jours",  str(body.jaune_jours))
    return {"ok": True}

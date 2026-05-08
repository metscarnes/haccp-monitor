"""
routes_cuisson.py — Module Cuisson (HACCP)

Enregistrement des cuissons avec contrôle température de fin de cuisson.
Cible réglementaire : ≥ 75 °C à cœur.

GET  /api/cuisson/enregistrements?type=rotissoire&limit=50
POST /api/cuisson/enregistrements
"""

import logging
from datetime import date as _date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.database import get_db, get_stock_unifie, DLC_JOURS_TRANSFORMATION

BOUTIQUE_ID = 1  # mono-boutique Phase 2

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cuisson", tags=["cuisson"])

TEMPERATURE_CIBLE = 75.0


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class CuissonCreate(BaseModel):
    type_cuisson:       str   = Field(..., description="'rotissoire' pour l'instant")
    date_cuisson:       str   = Field(..., description="YYYY-MM-DD")
    personnel_id:       int
    produit_id:         int
    reception_ligne_id: Optional[int]   = None     # source = lot de réception (brut)
    fabrication_id:     Optional[int]   = None     # source = lot de fabrication (fini cru)
    quantite:           Optional[float] = None
    unite:              Optional[str]   = "kg"
    heure_debut:        str   = Field(..., description="HH:MM")
    heure_fin:          str   = Field(..., description="HH:MM")
    temperature_sortie: float
    action_corrective:  Optional[str]   = None


# ---------------------------------------------------------------------------
# POST /api/cuisson/enregistrements
# ---------------------------------------------------------------------------

@router.post("/enregistrements", status_code=201)
async def creer_cuisson(body: CuissonCreate):
    conforme = 1 if body.temperature_sortie >= TEMPERATURE_CIBLE else 0
    if not conforme and not (body.action_corrective and body.action_corrective.strip()):
        raise HTTPException(
            status_code=422,
            detail="Action corrective obligatoire si température < 75 °C",
        )

    # Une cuisson ne peut pas avoir deux sources amont en même temps
    if body.reception_ligne_id and body.fabrication_id:
        raise HTTPException(
            status_code=422,
            detail="Une cuisson ne peut pas être liée simultanément à une réception et à une fabrication.",
        )

    # DLC J+3 calculée côté serveur (règle HACCP transformation)
    try:
        dlc_calculee = (datetime.strptime(body.date_cuisson, "%Y-%m-%d").date()
                        + timedelta(days=DLC_JOURS_TRANSFORMATION))
    except ValueError:
        raise HTTPException(status_code=422, detail="date_cuisson invalide (YYYY-MM-DD attendu).")

    async with get_db() as db:
        # Règle métier absolue : la DLC ne peut pas dépasser la DLC du lot d'origine
        # (réception OU fabrication, selon la source amont sélectionnée).
        dlc_finale = dlc_calculee
        dlc_origine = None
        dlc_ajustee = False

        if body.reception_ligne_id:
            cur_rl = await db.execute(
                "SELECT dlc FROM reception_lignes WHERE id = ?",
                (body.reception_ligne_id,),
            )
            rl = await cur_rl.fetchone()
            if rl and rl["dlc"]:
                dlc_origine = datetime.strptime(rl["dlc"], "%Y-%m-%d").date()
        elif body.fabrication_id:
            cur_fab = await db.execute(
                "SELECT dlc_finale FROM fabrications WHERE id = ?",
                (body.fabrication_id,),
            )
            fab = await cur_fab.fetchone()
            if fab and fab["dlc_finale"]:
                dlc_origine = datetime.strptime(fab["dlc_finale"], "%Y-%m-%d").date()

        if dlc_origine and dlc_calculee > dlc_origine:
            dlc_finale = dlc_origine
            dlc_ajustee = True

        dlc_finale_iso = dlc_finale.isoformat()

        cur = await db.execute(
            """
            INSERT INTO cuissons (
                type_cuisson, date_cuisson, personnel_id, produit_id,
                reception_ligne_id, fabrication_id, quantite, unite,
                heure_debut, heure_fin,
                temperature_sortie, temperature_cible,
                conforme, action_corrective, dlc_finale
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                body.type_cuisson.lower(),
                body.date_cuisson,
                body.personnel_id,
                body.produit_id,
                body.reception_ligne_id,
                body.fabrication_id,
                body.quantite,
                body.unite or "kg",
                body.heure_debut,
                body.heure_fin,
                body.temperature_sortie,
                TEMPERATURE_CIBLE,
                conforme,
                (body.action_corrective or "").strip() or None,
                dlc_finale_iso,
            ),
        )
        await db.commit()
        nouveau_id = cur.lastrowid

    logger.info(
        "Cuisson %s #%d — produit=%d T°=%.1f conforme=%s",
        body.type_cuisson, nouveau_id, body.produit_id,
        body.temperature_sortie, bool(conforme),
    )
    return {
        "ok": True,
        "id": nouveau_id,
        "conforme": bool(conforme),
        "dlc_ajustee": dlc_ajustee,
        "dlc_origine": dlc_origine.isoformat() if dlc_origine else None,
    }


# ---------------------------------------------------------------------------
# GET /api/cuisson/enregistrements
# ---------------------------------------------------------------------------

@router.get("/enregistrements")
async def lister_cuissons(
    type:       str = Query("rotissoire"),
    date_debut: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_fin:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit:      int = Query(50, ge=1, le=500),
):
    """Liste des cuissons d'un type donné, du plus récent au plus ancien."""
    clauses = ["c.type_cuisson = ?"]
    params: list = [type.lower()]
    if date_debut:
        clauses.append("c.date_cuisson >= ?")
        params.append(date_debut)
    if date_fin:
        clauses.append("c.date_cuisson <= ?")
        params.append(date_fin)

    where_sql = " AND ".join(clauses)
    params.append(limit)

    async with get_db() as db:
        cur = await db.execute(
            f"""
            SELECT c.*,
                   p.nom       AS produit_nom,
                   p.espece    AS espece,
                   pers.prenom AS personnel_prenom,
                   COALESCE(rl.numero_lot, fab.lot_interne) AS numero_lot,
                   rl.reception_id AS reception_id
            FROM   cuissons c
            LEFT   JOIN produits        p    ON p.id    = c.produit_id
            LEFT   JOIN personnel       pers ON pers.id = c.personnel_id
            LEFT   JOIN reception_lignes rl  ON rl.id   = c.reception_ligne_id
            LEFT   JOIN fabrications    fab  ON fab.id  = c.fabrication_id
            WHERE  {where_sql}
            ORDER BY c.date_cuisson DESC, c.id DESC
            LIMIT ?
            """,
            tuple(params),
        )
        rows = await cur.fetchall()

    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# GET /api/cuisson/produits-disponibles
# Source unique du stock disponible à cuire — alimentée par get_stock_unifie()
# ---------------------------------------------------------------------------

@router.get("/produits-disponibles")
async def produits_disponibles_pour_cuisson():
    """
    Produits bruts ayant au moins un lot de réception disponible (DLC future,
    non sortis via dlc_devenir). Une ligne par produit, avec le lot FIFO
    (DLC la plus courte, puis date de réception la plus ancienne).

    Si l'inventaire est vide, cette liste l'est aussi : on ne peut pas cuire
    ce qu'on n'a pas reçu.
    """
    async with get_db() as db:
        stock = await get_stock_unifie(
            db, BOUTIQUE_ID,
            type_produit="tous",
            sources=["reception_ligne", "fabrication"],
        )

    # get_stock_unifie est déjà trié par DLC croissante, date_origine croissante.
    # On garde le premier lot rencontré pour chaque produit (= FIFO).
    par_produit: dict[int, dict] = {}
    for lot in stock:
        pid = lot["produit_id"]
        if pid in par_produit:
            continue
        src_type = lot["source_type"]
        src_id   = lot["source_id"]
        par_produit[pid] = {
            "id":                 pid,
            "nom":                lot["produit_nom"],
            "espece":             lot.get("espece"),
            "categorie":          lot.get("categorie"),
            "type_produit":       lot.get("type_produit"),
            "en_stock":           True,
            "numero_lot":         lot.get("numero_lot"),
            "dlc":                lot.get("dlc"),
            "source_type":        src_type,
            "source_id":          src_id,
            "reception_ligne_id": src_id if src_type == "reception_ligne" else None,
            "fabrication_id":     src_id if src_type == "fabrication"     else None,
        }

    return sorted(par_produit.values(), key=lambda p: (p["nom"] or "").lower())


# ---------------------------------------------------------------------------
# GET /api/cuisson/produits/{produit_id}/receptions
# Historique des réceptions pour un produit donné
# ---------------------------------------------------------------------------

@router.get("/produits/{produit_id}/receptions")
async def historique_receptions_produit(produit_id: int, limit: int = Query(20, ge=1, le=100)):
    """
    Lots disponibles pour cuisson : DLC non dépassée ET non traitée via le calendrier DLC.

    Inclut deux sources :
      • réceptions (produits bruts livrés)         — source_type='reception_ligne'
      • fabrications (produits finis crus)         — source_type='fabrication'

    Chaque lot expose `source_type` + `source_id` (à privilégier) ainsi que
    `reception_ligne_id` (legacy, conservé pour l'affichage).
    """
    async with get_db() as db:
        # ── Lots issus de réception ───────────────────────────────────────────
        cur = await db.execute(
            """
            SELECT 'reception_ligne'   AS source_type,
                   rl.id                AS source_id,
                   rl.id                AS reception_ligne_id,
                   rl.reception_id      AS reception_id,
                   rl.numero_lot,
                   COALESCE(rl.dlc, rl.dluo) AS dlc,
                   rl.poids_kg,
                   rl.temperature_reception,
                   r.date_reception,
                   r.heure_reception,
                   f.nom                AS fournisseur_nom
            FROM   reception_lignes rl
            JOIN   receptions  r ON r.id = rl.reception_id
            LEFT JOIN fournisseurs f ON f.id = rl.fournisseur_id
            WHERE  rl.produit_id = ?
              AND r.statut = 'cloturee'
              AND rl.conforme = 1
              AND r.livraison_refusee = 0
              AND (COALESCE(rl.dlc, rl.dluo) IS NULL
                   OR COALESCE(rl.dlc, rl.dluo) >= DATE('now'))
              AND NOT EXISTS (
                  SELECT 1 FROM dlc_devenir d
                  WHERE d.source_type = 'reception_ligne' AND d.source_id = rl.id
              )
            ORDER BY r.date_reception DESC, r.id DESC
            LIMIT ?
            """,
            (produit_id, limit),
        )
        receptions = [dict(r) for r in await cur.fetchall()]

        # ── Lots issus de fabrication ─────────────────────────────────────────
        cur = await db.execute(
            """
            SELECT 'fabrication'        AS source_type,
                   fab.id               AS source_id,
                   NULL                 AS reception_ligne_id,
                   NULL                 AS reception_id,
                   fab.lot_interne      AS numero_lot,
                   fab.dlc_finale       AS dlc,
                   fab.poids_fabrique   AS poids_kg,
                   NULL                 AS temperature_reception,
                   fab.date             AS date_reception,
                   NULL                 AS heure_reception,
                   'Fabrication maison' AS fournisseur_nom
            FROM   fabrications fab
            JOIN   recettes rec ON rec.id = fab.recette_id
            WHERE  rec.produit_fini_id = ?
              AND  fab.dlc_finale IS NOT NULL
              AND  fab.dlc_finale >= DATE('now')
              AND NOT EXISTS (
                  SELECT 1 FROM dlc_devenir d
                  WHERE d.source_type = 'fabrication' AND d.source_id = fab.id
              )
            ORDER BY fab.date DESC, fab.id DESC
            LIMIT ?
            """,
            (produit_id, limit),
        )
        fabrications = [dict(r) for r in await cur.fetchall()]

    return receptions + fabrications

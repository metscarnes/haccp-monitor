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
    update_recette,
    RecetteIngredientEnUsage,
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


class IngredientUpdate(BaseModel):
    id: Optional[int] = None             # présent → mise à jour, absent → nouvel ingrédient
    produit_id: int
    quantite: Optional[float] = None
    unite: Optional[str] = None


class RecetteUpdate(BaseModel):
    nom: str
    produit_fini_id: int
    dlc_jours: int
    instructions: Optional[str] = None
    ingredients: list[IngredientUpdate] = []


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
    poids_fabrique: Optional[float] = None  # poids fabriqué en kg (traçabilité légale)


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


@router.put("/recettes/{recette_id}")
async def modifier_recette(recette_id: int, payload: RecetteUpdate):
    """
    Met à jour une recette existante (champs + ingrédients).

    Les ingrédients référencés par une fabrication ne peuvent pas être supprimés
    (préservation de la traçabilité HACCP) — un 409 est renvoyé dans ce cas.
    """
    async with get_db() as db:
        try:
            recette = await update_recette(
                db,
                recette_id=recette_id,
                nom=payload.nom,
                produit_fini_id=payload.produit_fini_id,
                dlc_jours=payload.dlc_jours,
                instructions=payload.instructions,
                ingredients=[ing.model_dump() for ing in payload.ingredients],
            )
        except RecetteIngredientEnUsage as exc:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Impossible de retirer l'ingrédient « {exc.nom} » : "
                    "il est utilisé dans une fabrication existante (traçabilité HACCP)."
                ),
            )
        except Exception as exc:
            logger.error("Erreur modification recette : %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))
    if not recette:
        raise HTTPException(status_code=404, detail="Recette introuvable")
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
                   rl.dluo,
                   rl.poids_kg,
                   r.date_reception
            FROM   reception_lignes rl
            JOIN   receptions r ON r.id = rl.reception_id
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
            ORDER BY
                CASE WHEN COALESCE(rl.dlc, rl.dluo) IS NOT NULL THEN 0 ELSE 1 END,
                COALESCE(rl.dlc, rl.dluo) ASC,
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
# B3. Diagnostic FIFO : tous les lots d'un produit avec leur statut d'éligibilité
# ---------------------------------------------------------------------------

@router.get("/fabrications/debug-fifo/{produit_id}")
async def debug_fifo(produit_id: int):
    """Retourne TOUS les lots d'un produit avec le détail de leur éligibilité FIFO."""
    async with get_db() as db:
        cur = await db.execute(
            """
            SELECT
                rl.id,
                rl.numero_lot,
                rl.dlc,
                rl.dluo,
                rl.conforme,
                rl.temperature_reception,
                rl.temperature_conforme,
                r.statut,
                r.livraison_refusee,
                r.date_reception,
                COALESCE(rl.dlc, rl.dluo)                          AS date_fifo,
                COALESCE(rl.dlc, rl.dluo) >= DATE('now')           AS date_ok,
                EXISTS (
                    SELECT 1 FROM dlc_devenir d
                    WHERE d.source_type = 'reception_ligne' AND d.source_id = rl.id
                )                                                   AS has_dlc_devenir,
                CASE
                    WHEN r.statut != 'cloturee'          THEN 'statut_non_cloture'
                    WHEN rl.conforme != 1                THEN 'non_conforme'
                    WHEN r.livraison_refusee = 1         THEN 'livraison_refusee'
                    WHEN COALESCE(rl.dlc, rl.dluo) IS NOT NULL
                         AND COALESCE(rl.dlc, rl.dluo) < DATE('now') THEN 'perime'
                    WHEN EXISTS (
                        SELECT 1 FROM dlc_devenir d
                        WHERE d.source_type = 'reception_ligne' AND d.source_id = rl.id
                    )                                    THEN 'dlc_devenir_existe'
                    ELSE 'eligible_fifo'
                END AS raison_exclusion
            FROM reception_lignes rl
            JOIN receptions r ON r.id = rl.reception_id
            WHERE rl.produit_id = ?
            ORDER BY r.date_reception DESC, rl.id DESC
            """,
            (produit_id,),
        )
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# B4. Admin : remap d'un ingrédient de recette vers un autre produit
# ---------------------------------------------------------------------------

@router.get("/admin/remap-produit-recette/{recette_id}/{old_produit_id}/{new_produit_id}")
async def remap_produit_recette(
    recette_id: int,
    old_produit_id: int,
    new_produit_id: int,
    confirm: int = Query(0, description="0 = dry-run (preview), 1 = exécution"),
):
    """Reroute les recette_ingredients d'une recette : old_produit_id → new_produit_id."""
    async with get_db() as db:
        # Aperçu : lignes ciblées
        cur = await db.execute(
            """SELECT ri.id, ri.recette_id, ri.produit_id,
                      p.nom AS produit_nom
               FROM recette_ingredients ri
               LEFT JOIN produits p ON p.id = ri.produit_id
               WHERE ri.recette_id = ? AND ri.produit_id = ?""",
            (recette_id, old_produit_id),
        )
        cibles = [dict(r) for r in await cur.fetchall()]

        # Validation : le nouveau produit existe ?
        cur2 = await db.execute("SELECT id, nom FROM produits WHERE id = ?", (new_produit_id,))
        new_prod = await cur2.fetchone()
        if not new_prod:
            raise HTTPException(404, f"Nouveau produit {new_produit_id} introuvable")

        if confirm != 1:
            return {
                "mode": "dry-run",
                "recette_id": recette_id,
                "old_produit_id": old_produit_id,
                "new_produit_id": new_produit_id,
                "new_produit_nom": new_prod["nom"],
                "lignes_concernees": cibles,
                "info": "Ajoute ?confirm=1 à l'URL pour exécuter.",
            }

        await db.execute(
            "UPDATE recette_ingredients SET produit_id = ? WHERE recette_id = ? AND produit_id = ?",
            (new_produit_id, recette_id, old_produit_id),
        )
        await db.commit()
        return {
            "mode": "executed",
            "lignes_modifiees": len(cibles),
            "details": cibles,
            "new_produit_nom": new_prod["nom"],
        }


# ---------------------------------------------------------------------------
# B5. Admin : suppression sécurisée d'un produit orphelin
# ---------------------------------------------------------------------------

async def _tables_referencant_produit(db) -> list[tuple[str, str]]:
    """Découvre dynamiquement toutes les tables ayant une colonne 'produit_id'
    (ou 'produit_fini_id', 'produit_brut_id') susceptible de référencer produits.id."""
    cur = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [r[0] for r in await cur.fetchall()]
    refs: list[tuple[str, str]] = []
    candidate_cols = {"produit_id", "produit_fini_id", "produit_brut_id"}
    for tbl in tables:
        if tbl == "produits":
            continue
        cur_info = await db.execute(f"PRAGMA table_info({tbl})")
        cols = [c[1] for c in await cur_info.fetchall()]
        for c in cols:
            if c in candidate_cols:
                refs.append((tbl, c))
    return refs


@router.get("/admin/delete-produit/{produit_id}")
async def delete_produit_orphelin(
    produit_id: int,
    confirm: int = Query(0, description="0 = dry-run (vérifie les refs), 1 = DELETE"),
):
    """Supprime un produit. Refuse si une autre table le référence."""
    async with get_db() as db:
        cur = await db.execute("SELECT id, nom, code_unique FROM produits WHERE id = ?", (produit_id,))
        prod = await cur.fetchone()
        if not prod:
            raise HTTPException(404, f"Produit {produit_id} introuvable")

        refs_a_verifier = await _tables_referencant_produit(db)
        refs_trouvees = []
        for table, col in refs_a_verifier:
            cur_ref = await db.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {col} = ?", (produit_id,)
            )
            n = (await cur_ref.fetchone())[0]
            if n > 0:
                refs_trouvees.append({"table": table, "colonne": col, "nb_lignes": n})

        if refs_trouvees:
            return {
                "mode": "blocked",
                "produit_id": produit_id,
                "produit_nom": prod["nom"],
                "code_unique": prod["code_unique"],
                "references_existantes": refs_trouvees,
                "info": "Suppression refusée — d'autres tables référencent ce produit. Utilise /admin/migrate-produit pour transférer puis supprimer.",
            }

        if confirm != 1:
            return {
                "mode": "dry-run",
                "produit_id": produit_id,
                "produit_nom": prod["nom"],
                "code_unique": prod["code_unique"],
                "references_existantes": [],
                "info": "Aucune référence trouvée. Ajoute ?confirm=1 pour DELETE.",
            }

        await db.execute("DELETE FROM produits WHERE id = ?", (produit_id,))
        await db.commit()
        return {
            "mode": "deleted",
            "produit_id": produit_id,
            "produit_nom": prod["nom"],
        }


# ---------------------------------------------------------------------------
# B6. Admin : migration complète d'un produit vers un autre + suppression
# ---------------------------------------------------------------------------

@router.get("/admin/migrate-produit/{old_produit_id}/{new_produit_id}")
async def migrate_produit(
    old_produit_id: int,
    new_produit_id: int,
    confirm: int = Query(0, description="0 = dry-run, 1 = exécution + DELETE final"),
):
    """Transfère TOUTES les références d'un produit vers un autre, puis supprime l'ancien.

    UPDATE chaque table ayant une colonne produit_id : old → new.
    Préserve numero_lot, dlc, dluo, dates de réception (la traçabilité du lot
    n'est pas altérée — seul le pointeur produit change)."""
    async with get_db() as db:
        cur_old = await db.execute(
            "SELECT id, nom, code_unique FROM produits WHERE id = ?", (old_produit_id,)
        )
        old = await cur_old.fetchone()
        if not old:
            raise HTTPException(404, f"Produit {old_produit_id} introuvable")
        cur_new = await db.execute(
            "SELECT id, nom, code_unique FROM produits WHERE id = ?", (new_produit_id,)
        )
        new = await cur_new.fetchone()
        if not new:
            raise HTTPException(404, f"Produit {new_produit_id} introuvable")

        # Aperçu des références à migrer
        refs = await _tables_referencant_produit(db)
        plan = []
        for table, col in refs:
            cur_n = await db.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {col} = ?", (old_produit_id,)
            )
            n = (await cur_n.fetchone())[0]
            if n > 0:
                plan.append({"table": table, "colonne": col, "nb_lignes": n})

        if confirm != 1:
            return {
                "mode": "dry-run",
                "old": {"id": old["id"], "nom": old["nom"], "code_unique": old["code_unique"]},
                "new": {"id": new["id"], "nom": new["nom"], "code_unique": new["code_unique"]},
                "operations_prevues": plan,
                "info": "Ajoute ?confirm=1 pour transférer puis supprimer l'ancien produit.",
            }

        # Exécution : UPDATE chaque table puis DELETE le produit orphelin
        modifications = []
        for table, col in refs:
            cur_upd = await db.execute(
                f"UPDATE {table} SET {col} = ? WHERE {col} = ?",
                (new_produit_id, old_produit_id),
            )
            if cur_upd.rowcount > 0:
                modifications.append(
                    {"table": table, "colonne": col, "lignes_modifiees": cur_upd.rowcount}
                )

        await db.execute("DELETE FROM produits WHERE id = ?", (old_produit_id,))
        await db.commit()
        return {
            "mode": "migrated",
            "old_produit_id_supprime": old_produit_id,
            "new_produit_id": new_produit_id,
            "modifications": modifications,
        }


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
                poids_fabrique=payload.poids_fabrique,
            )
        except Exception as exc:
            logger.error("Erreur création fabrication : %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))

    return fabrication

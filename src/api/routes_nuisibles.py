"""
routes_nuisibles.py — Lutte contre nuisibles (IPM — Integrated Pest Management)

GET  /api/nuisibles/controles?type_id=1&annee=2026  → registre semaines 1-52
POST /api/nuisibles/controles                        → sauvegarder / mettre à jour une semaine
GET  /api/nuisibles/config                           → nombre de pièges configuré
PUT  /api/nuisibles/config                           → modifier le nombre de pièges
GET  /api/nuisibles/carte?type_id=1                  → positions des pièges sur le plan
POST /api/nuisibles/carte                            → enregistrer les positions des pièges
"""

import json
import logging
from datetime import date as _date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.database import get_db, get_parametre, set_parametre

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nuisibles", tags=["nuisibles"])

BOUTIQUE_ID = 1

# Nombre de pièges par défaut (avant toute configuration explicite).
NB_PIEGES_DEFAUT = 15
# Bornes raisonnables pour le réglage.
NB_PIEGES_MIN = 1
NB_PIEGES_MAX = 50

# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class ControleNuisible(BaseModel):
    type_id:      int      # 1=rongeurs  2=ins.volants  3=ins.rampants  4=oiseaux
    annee:        int
    semaine:      int      # 1-53
    resultats:    dict     # {"p1": "O"/"N"/None, "p2": ..., ...}
    personnel_id: Optional[int] = None


class ConfigNuisibles(BaseModel):
    nb_pieges: int         # nombre de pièges suivis (P1..Pn)


class PiegePosition(BaseModel):
    piege_num: int         # 1..N
    pos_x:     float       # pourcentage 0..100
    pos_y:     float       # pourcentage 0..100


class CartePieges(BaseModel):
    type_id: int
    pieges:  List[PiegePosition]

# ---------------------------------------------------------------------------
# GET /api/nuisibles/controles
# ---------------------------------------------------------------------------

@router.get("/controles")
async def lister_controles(
    type_id: int = Query(..., ge=1, le=4, description="1=rongeurs 2=ins.vol 3=ins.ramp 4=oiseaux"),
    annee:   int = Query(..., description="Année civile"),
):
    """
    Retourne tous les enregistrements de l'année pour un type de nuisible.
    Format : { semaine_num: { resultats: {p1: "O"/"N"/null}, visa, date_saisie } }
    """
    async with get_db() as db:
        rows = await db.execute_fetchall(
            """
            SELECT nc.semaine, nc.resultats,
                   COALESCE(TRIM(p.prenom || ' ' || COALESCE(p.nom, '')), nc.visa) AS visa,
                   nc.personnel_id, nc.date_saisie
            FROM nuisibles_controles nc
            LEFT JOIN personnel p ON p.id = nc.personnel_id
            WHERE nc.type_id = ? AND nc.annee = ? ORDER BY nc.semaine
            """,
            (type_id, annee),
        )

    result = {}
    for row in rows:
        semaine, resultats_json, visa, personnel_id, date_saisie = row
        try:
            resultats = json.loads(resultats_json)
        except Exception:
            resultats = {}
        result[str(semaine)] = {
            "resultats":    resultats,
            "visa":         visa,
            "personnel_id": personnel_id,
            "date_saisie":  date_saisie,
        }

    return result


# ---------------------------------------------------------------------------
# POST /api/nuisibles/controles
# ---------------------------------------------------------------------------

@router.post("/controles", status_code=201)
async def sauvegarder_controle(body: ControleNuisible):
    """
    Insère ou met à jour le contrôle d'une semaine pour un type de nuisible.
    """
    if not (1 <= body.semaine <= 53):
        raise HTTPException(400, "semaine invalide (1-53)")

    aujourd_hui    = _date.today().isoformat()
    resultats_json = json.dumps(body.resultats)

    async with get_db() as db:
        # Résout le prénom courant pour la colonne visa (compat historique)
        visa = ""
        if body.personnel_id is not None:
            cur = await db.execute("SELECT prenom FROM personnel WHERE id = ?", (body.personnel_id,))
            prow = await cur.fetchone()
            if not prow:
                raise HTTPException(400, "Personnel introuvable")
            visa = prow["prenom"]

        await db.execute(
            """
            INSERT INTO nuisibles_controles
                (type_id, annee, semaine, resultats, visa, personnel_id, date_saisie)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(type_id, annee, semaine) DO UPDATE SET
                resultats    = excluded.resultats,
                visa         = excluded.visa,
                personnel_id = excluded.personnel_id,
                date_saisie  = excluded.date_saisie
            """,
            (body.type_id, body.annee, body.semaine,
             resultats_json, visa, body.personnel_id, aujourd_hui),
        )
        await db.commit()

    logger.info(
        "Nuisibles — type=%d  sem=%d/%d  visa=%s",
        body.type_id, body.semaine, body.annee, visa or "—",
    )
    return {
        "ok":       True,
        "type_id":  body.type_id,
        "semaine":  body.semaine,
        "annee":    body.annee,
    }


# ---------------------------------------------------------------------------
# GET / PUT /api/nuisibles/config  — nombre de pièges configurable
# ---------------------------------------------------------------------------

@router.get("/config")
async def get_config():
    """Retourne le nombre de pièges configuré (P1..Pn) pour la boutique."""
    async with get_db() as db:
        valeur = await get_parametre(
            db, BOUTIQUE_ID, "nuisibles_nb_pieges", str(NB_PIEGES_DEFAUT)
        )
    try:
        nb = int(valeur)
    except (TypeError, ValueError):
        nb = NB_PIEGES_DEFAUT
    nb = max(NB_PIEGES_MIN, min(NB_PIEGES_MAX, nb))
    return {"nb_pieges": nb}


@router.put("/config")
async def update_config(body: ConfigNuisibles):
    """Modifie le nombre de pièges suivis. Les pièges retirés gardent leur
    historique en base (colonnes simplement masquées côté affichage)."""
    if not (NB_PIEGES_MIN <= body.nb_pieges <= NB_PIEGES_MAX):
        raise HTTPException(
            400, f"nb_pieges doit être compris entre {NB_PIEGES_MIN} et {NB_PIEGES_MAX}"
        )
    async with get_db() as db:
        await set_parametre(db, BOUTIQUE_ID, "nuisibles_nb_pieges", str(body.nb_pieges))
    logger.info("Nuisibles — nb_pieges réglé à %d", body.nb_pieges)
    return {"ok": True, "nb_pieges": body.nb_pieges}


# ---------------------------------------------------------------------------
# GET /api/nuisibles/carte  — positions des pièges sur le plan
# ---------------------------------------------------------------------------

@router.get("/carte")
async def lister_positions(
    type_id: int = Query(..., ge=1, le=4, description="1=rongeurs 2=ins.vol 3=ins.ramp 4=oiseaux"),
):
    """Retourne les positions enregistrées des pièges pour un type de nuisible."""
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT piege_num, pos_x, pos_y "
            "FROM nuisibles_pieges_carte "
            "WHERE boutique_id = ? AND type_id = ? ORDER BY piege_num",
            (BOUTIQUE_ID, type_id),
        )

    return {
        "type_id": type_id,
        "pieges": [
            {"piege_num": r[0], "pos_x": r[1], "pos_y": r[2]} for r in rows
        ],
    }


# ---------------------------------------------------------------------------
# POST /api/nuisibles/carte  — enregistrer les positions des pièges
# ---------------------------------------------------------------------------

@router.post("/carte", status_code=201)
async def sauvegarder_positions(body: CartePieges):
    """
    Remplace l'ensemble des positions de pièges pour un type de nuisible.
    Un piège absent de la liste est considéré comme retiré de la carte.
    """
    if not (1 <= body.type_id <= 4):
        raise HTTPException(400, "type_id invalide (1-4)")

    for p in body.pieges:
        if p.piege_num < 1:
            raise HTTPException(400, "piege_num invalide")
        if not (0.0 <= p.pos_x <= 100.0 and 0.0 <= p.pos_y <= 100.0):
            raise HTTPException(400, "pos_x / pos_y doivent être des pourcentages (0-100)")

    async with get_db() as db:
        await db.execute(
            "DELETE FROM nuisibles_pieges_carte WHERE boutique_id = ? AND type_id = ?",
            (BOUTIQUE_ID, body.type_id),
        )
        if body.pieges:
            await db.executemany(
                "INSERT INTO nuisibles_pieges_carte "
                "(boutique_id, type_id, piege_num, pos_x, pos_y) VALUES (?, ?, ?, ?, ?)",
                [(BOUTIQUE_ID, body.type_id, p.piege_num, p.pos_x, p.pos_y) for p in body.pieges],
            )
        await db.commit()

    logger.info(
        "Nuisibles — carte type=%d : %d piège(s) positionné(s)",
        body.type_id, len(body.pieges),
    )
    return {"ok": True, "type_id": body.type_id, "nb": len(body.pieges)}

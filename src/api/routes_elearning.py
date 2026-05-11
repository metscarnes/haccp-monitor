"""
routes_elearning.py — Module E-Learning HACCP (traçabilité des formations)

GET  /api/elearning/completions?module=hygiene-pdf  → historique des lectures
POST /api/elearning/completions                      → enregistrer une lecture validée
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/elearning", tags=["elearning"])

BOUTIQUE_ID = 1

# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class CompletionCreate(BaseModel):
    module:       str
    personnel_id: int


# ---------------------------------------------------------------------------
# GET /api/elearning/completions
# ---------------------------------------------------------------------------

@router.get("/completions")
async def lister_completions(
    module: str | None = Query(None, description="Filtrer par module (ex: hygiene-pdf)"),
    limit:  int        = Query(50,   ge=1, le=500),
):
    """Retourne l'historique des formations validées, le plus récent en premier."""
    sql = (
        "SELECT c.id, c.module, c.personnel_id, p.prenom AS personnel_prenom, "
        "       c.date_completion "
        "FROM elearning_completions c "
        "JOIN personnel p ON p.id = c.personnel_id "
        "WHERE c.boutique_id = ? "
    )
    params: list = [BOUTIQUE_ID]
    if module:
        sql += "AND c.module = ? "
        params.append(module)
    sql += "ORDER BY c.date_completion DESC LIMIT ?"
    params.append(limit)

    async with get_db() as db:
        rows = await db.execute_fetchall(sql, tuple(params))

    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# POST /api/elearning/completions
# ---------------------------------------------------------------------------

@router.post("/completions", status_code=201)
async def enregistrer_completion(body: CompletionCreate):
    """Enregistre qu'un membre du personnel a terminé une formation."""
    module = body.module.strip()
    if not module:
        raise HTTPException(400, "module requis")

    async with get_db() as db:
        row = await db.execute("SELECT id FROM personnel WHERE id = ?", (body.personnel_id,))
        if not await row.fetchone():
            raise HTTPException(404, "personnel_id introuvable")

        cursor = await db.execute(
            "INSERT INTO elearning_completions (boutique_id, module, personnel_id) "
            "VALUES (?, ?, ?)",
            (BOUTIQUE_ID, module, body.personnel_id),
        )
        await db.commit()
        new_id = cursor.lastrowid

        row = await db.execute(
            "SELECT c.id, c.module, c.personnel_id, p.prenom AS personnel_prenom, "
            "       c.date_completion "
            "FROM elearning_completions c "
            "JOIN personnel p ON p.id = c.personnel_id "
            "WHERE c.id = ?",
            (new_id,),
        )
        created = await row.fetchone()

    return dict(created)

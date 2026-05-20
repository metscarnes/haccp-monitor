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


class QuizResultatCreate(BaseModel):
    quiz_id:      int
    personnel_id: int
    score:        int
    total:        int
    signature:    str | None = None   # PNG base64 (data-URL), requis si quiz réussi


SEUIL_VALIDATION = 80  # % minimum pour valider un quiz


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


# ===========================================================================
# Quiz E-Learning — résultats (attestation de formation, seuil 80 %)
# ===========================================================================

# ---------------------------------------------------------------------------
# GET /api/elearning/quiz/resultats
# ---------------------------------------------------------------------------

@router.get("/quiz/resultats")
async def lister_resultats_quiz(
    quiz_id:      int | None = Query(None, description="Filtrer par numéro de quiz"),
    personnel_id: int | None = Query(None, description="Filtrer par membre du personnel"),
    limit:        int        = Query(100, ge=1, le=500),
):
    """Historique des résultats de quiz, le plus récent en premier."""
    sql = (
        "SELECT r.id, r.quiz_id, r.personnel_id, p.prenom AS personnel_prenom, "
        "       r.score, r.total, r.pourcentage, r.reussi, r.date_completion "
        "FROM quiz_resultats r "
        "JOIN personnel p ON p.id = r.personnel_id "
        "WHERE r.boutique_id = ? "
    )
    params: list = [BOUTIQUE_ID]
    if quiz_id is not None:
        sql += "AND r.quiz_id = ? "
        params.append(quiz_id)
    if personnel_id is not None:
        sql += "AND r.personnel_id = ? "
        params.append(personnel_id)
    sql += "ORDER BY r.date_completion DESC LIMIT ?"
    params.append(limit)

    async with get_db() as db:
        rows = await db.execute_fetchall(sql, tuple(params))

    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# GET /api/elearning/quiz/meilleur
# ---------------------------------------------------------------------------

@router.get("/quiz/meilleur")
async def meilleur_resultat_quiz(
    quiz_id:      int = Query(..., description="Numéro du quiz"),
    personnel_id: int = Query(..., description="Membre du personnel"),
):
    """Meilleur résultat d'un membre pour un quiz (meilleur %, le plus récent
    en cas d'égalité). Retourne null si la personne n'a jamais passé ce quiz."""
    sql = (
        "SELECT r.id, r.quiz_id, r.personnel_id, p.prenom AS personnel_prenom, "
        "       r.score, r.total, r.pourcentage, r.reussi, r.signature, r.date_completion, "
        "       (SELECT COUNT(*) FROM quiz_resultats r2 "
        "        WHERE r2.boutique_id = r.boutique_id AND r2.quiz_id = r.quiz_id "
        "          AND r2.personnel_id = r.personnel_id) AS nb_tentatives "
        "FROM quiz_resultats r "
        "JOIN personnel p ON p.id = r.personnel_id "
        "WHERE r.boutique_id = ? AND r.quiz_id = ? AND r.personnel_id = ? "
        "ORDER BY r.pourcentage DESC, r.date_completion DESC "
        "LIMIT 1"
    )
    async with get_db() as db:
        row = await db.execute(sql, (BOUTIQUE_ID, quiz_id, personnel_id))
        result = await row.fetchone()

    return dict(result) if result else None


# ---------------------------------------------------------------------------
# POST /api/elearning/quiz/resultats
# ---------------------------------------------------------------------------

@router.post("/quiz/resultats", status_code=201)
async def enregistrer_resultat_quiz(body: QuizResultatCreate):
    """Enregistre le résultat d'un quiz (score, pourcentage, réussite)."""
    if body.total <= 0:
        raise HTTPException(400, "total doit être > 0")
    if body.score < 0 or body.score > body.total:
        raise HTTPException(400, "score invalide")

    pourcentage = round(body.score * 100 / body.total)
    reussi = 1 if pourcentage >= SEUIL_VALIDATION else 0

    signature = (body.signature or "").strip() or None
    # Signature opérateur obligatoire quand le quiz est réussi (attestation traçable)
    if reussi and not signature:
        raise HTTPException(400, "signature opérateur requise pour valider le quiz")

    async with get_db() as db:
        row = await db.execute("SELECT id FROM personnel WHERE id = ?", (body.personnel_id,))
        if not await row.fetchone():
            raise HTTPException(404, "personnel_id introuvable")

        cursor = await db.execute(
            "INSERT INTO quiz_resultats "
            "(boutique_id, quiz_id, personnel_id, score, total, pourcentage, reussi, signature) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (BOUTIQUE_ID, body.quiz_id, body.personnel_id,
             body.score, body.total, pourcentage, reussi, signature),
        )
        await db.commit()
        new_id = cursor.lastrowid

        row = await db.execute(
            "SELECT r.id, r.quiz_id, r.personnel_id, p.prenom AS personnel_prenom, "
            "       r.score, r.total, r.pourcentage, r.reussi, r.signature, r.date_completion "
            "FROM quiz_resultats r "
            "JOIN personnel p ON p.id = r.personnel_id "
            "WHERE r.id = ?",
            (new_id,),
        )
        created = await row.fetchone()

    return dict(created)

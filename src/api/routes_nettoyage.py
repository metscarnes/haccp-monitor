"""
routes_nettoyage.py — Plan de nettoyage & désinfection

GET  /api/nettoyage/taches      → liste des tâches groupées par zone
POST /api/nettoyage/validation  → enregistre une session de validation
"""

import logging
from datetime import date
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nettoyage", tags=["nettoyage"])


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class ValidationNettoyage(BaseModel):
    operateur: str
    taches_ids: List[int]
    signature: str = "OK"


# ---------------------------------------------------------------------------
# GET /api/nettoyage/taches
# ---------------------------------------------------------------------------

@router.get("/taches")
async def lister_taches():
    """
    Retourne toutes les tâches groupées par zone.
    Format : [{ "zone": "...", "taches": [{id, nom_tache, frequence, methode_produit}, ...] }]
    """
    async with get_db() as db:
        # S'assure que la table existe même si le seed n'a pas été lancé
        await db.execute("""
            CREATE TABLE IF NOT EXISTS taches_nettoyage (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                zone            TEXT NOT NULL,
                nom_tache       TEXT NOT NULL,
                frequence       TEXT NOT NULL,
                methode_produit TEXT NOT NULL
            )
        """)
        await db.commit()

        rows = await db.execute_fetchall(
            "SELECT id, zone, nom_tache, frequence, methode_produit "
            "FROM taches_nettoyage ORDER BY zone, id"
        )

    # Groupement par zone côté Python
    zones: dict = {}
    for row in rows:
        z = row[1]
        if z not in zones:
            zones[z] = []
        zones[z].append({
            "id":              row[0],
            "nom_tache":       row[2],
            "frequence":       row[3],
            "methode_produit": row[4],
        })

    return [{"zone": z, "taches": t} for z, t in zones.items()]


# ---------------------------------------------------------------------------
# POST /api/nettoyage/validation
# ---------------------------------------------------------------------------

@router.post("/validation", status_code=201)
async def valider_nettoyage(body: ValidationNettoyage):
    """
    Enregistre une session de validation dans registre_nettoyage.
    Un enregistrement par tâche cochée.
    """
    if not body.operateur.strip():
        raise HTTPException(400, "L'opérateur est obligatoire")
    if not body.taches_ids:
        raise HTTPException(400, "Aucune tâche sélectionnée")

    aujourd_hui = date.today().isoformat()

    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS registre_nettoyage (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tache_id    INTEGER NOT NULL,
                operateur   TEXT    NOT NULL,
                date_val    TEXT    NOT NULL,
                signature   TEXT    NOT NULL DEFAULT 'OK'
            )
        """)

        for tid in body.taches_ids:
            await db.execute(
                "INSERT INTO registre_nettoyage (tache_id, operateur, date_val, signature) "
                "VALUES (?, ?, ?, ?)",
                (tid, body.operateur.strip(), aujourd_hui, body.signature),
            )

        await db.commit()
        nb = len(body.taches_ids)

    logger.info("Nettoyage validé par %s — %d tâche(s) — %s", body.operateur, nb, aujourd_hui)
    return {
        "ok":        True,
        "operateur": body.operateur,
        "date":      aujourd_hui,
        "nb_taches": nb,
    }

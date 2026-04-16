"""
routes_nettoyage.py — Plan de nettoyage & désinfection

GET  /api/nettoyage/taches      → liste des tâches groupées par zone
POST /api/nettoyage/validation  → enregistre une session de validation
GET  /api/nettoyage/status      → statut de validation pour une date (restauration UI)
GET  /api/nettoyage/historique  → arborescence Année > Mois > Semaine > Jours
"""

import logging
from collections import Counter
from datetime import date as _date, datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
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


# ---------------------------------------------------------------------------
# GET /api/nettoyage/status
# ---------------------------------------------------------------------------

_ENSURE_REGISTRE = """
    CREATE TABLE IF NOT EXISTS registre_nettoyage (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tache_id    INTEGER NOT NULL,
        operateur   TEXT    NOT NULL,
        date_val    TEXT    NOT NULL,
        signature   TEXT    NOT NULL DEFAULT 'OK'
    )
"""

@router.get("/status")
async def statut_validation(date: Optional[str] = Query(default=None)):
    """
    Retourne le statut de validation pour une date (défaut = aujourd'hui).
    Utilisé par le frontend au chargement pour restaurer l'état visuel du bouton et des cellules.
    """
    target = date or _date.today().isoformat()

    async with get_db() as db:
        await db.execute(_ENSURE_REGISTRE)
        await db.commit()

        rows = await db.execute_fetchall(
            "SELECT tache_id, operateur FROM registre_nettoyage WHERE date_val = ?",
            (target,),
        )

    if not rows:
        return {"valide": False, "date": target, "operateur": None, "nb_taches": 0, "taches_ids": []}

    ops = Counter(r[1] for r in rows)
    operateur_principal = ops.most_common(1)[0][0]
    taches_ids = [r[0] for r in rows]

    return {
        "valide":    True,
        "date":      target,
        "operateur": operateur_principal,
        "nb_taches": len(taches_ids),
        "taches_ids": taches_ids,
    }


# ---------------------------------------------------------------------------
# GET /api/nettoyage/historique
# ---------------------------------------------------------------------------

_MOIS_FR = {
    1: "Janvier", 2: "Février",  3: "Mars",      4: "Avril",
    5: "Mai",     6: "Juin",     7: "Juillet",   8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
}
_JOURS_FR = {
    0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi",
    4: "Vendredi", 5: "Samedi", 6: "Dimanche",
}


@router.get("/historique")
async def historique_nettoyage():
    """
    Retourne toutes les validations groupées selon l'arborescence :
    Année → Mois → N° Semaine ISO → Jours
    """
    async with get_db() as db:
        await db.execute(_ENSURE_REGISTRE)
        await db.commit()

        rows = await db.execute_fetchall("""
            SELECT date_val,
                   GROUP_CONCAT(DISTINCT operateur) AS operateurs,
                   COUNT(DISTINCT tache_id)          AS nb_taches
            FROM registre_nettoyage
            GROUP BY date_val
            ORDER BY date_val DESC
        """)

    if not rows:
        return []

    # Construire l'arbre : annee → mois_num → (annee_iso, semaine_num) → [jours]
    tree: dict = {}

    for row in rows:
        date_str, operateurs_raw, nb_taches = row[0], row[1], row[2]
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        annee     = d.year
        mois_num  = d.month
        iso_cal   = d.isocalendar()          # (iso_year, iso_week, iso_weekday)
        sem_key   = (iso_cal[0], iso_cal[1]) # (iso_year, week_number)
        jour_idx  = d.weekday()              # 0=Lun … 6=Dim

        tree.setdefault(annee, {}).setdefault(mois_num, {}).setdefault(sem_key, [])
        tree[annee][mois_num][sem_key].append({
            "date":       date_str,
            "jour_nom":   f"{_JOURS_FR[jour_idx]} {d.day}",
            "operateurs": [o.strip() for o in operateurs_raw.split(",")] if operateurs_raw else [],
            "nb_taches":  nb_taches,
        })

    # Sérialiser en liste triée (plus récent en premier)
    result = []
    for annee in sorted(tree, reverse=True):
        mois_list = []
        for mois_num in sorted(tree[annee], reverse=True):
            semaines_list = []
            for sem_key in sorted(tree[annee][mois_num], reverse=True):
                jours = sorted(
                    tree[annee][mois_num][sem_key],
                    key=lambda x: x["date"],
                    reverse=True,
                )
                semaines_list.append({
                    "annee_iso": sem_key[0],
                    "numero":    sem_key[1],
                    "jours":     jours,
                })
            mois_list.append({
                "numero":   mois_num,
                "nom":      _MOIS_FR[mois_num],
                "semaines": semaines_list,
            })
        result.append({"annee": annee, "mois": mois_list})

    return result

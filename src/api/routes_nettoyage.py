"""
routes_nettoyage.py — Plan de nettoyage & désinfection

GET    /api/nettoyage/taches        → liste des tâches groupées par zone
POST   /api/nettoyage/taches        → créer une nouvelle tâche
PUT    /api/nettoyage/taches/{id}   → modifier une tâche existante
DELETE /api/nettoyage/taches/{id}   → supprimer une tâche
POST   /api/nettoyage/validation    → enregistre une session de validation
GET    /api/nettoyage/status        → statut de validation pour une date (restauration UI)
GET    /api/nettoyage/historique    → arborescence Année > Mois > Semaine > Jours
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
    date: Optional[str] = None   # si absent → date du jour


class TachePayload(BaseModel):
    zone: str
    nom_tache: str
    frequence: str
    methode_produit: str


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
# POST /api/nettoyage/taches  — créer une tâche
# ---------------------------------------------------------------------------

@router.post("/taches", status_code=201)
async def creer_tache(body: TachePayload):
    """Ajoute une nouvelle tâche au plan de nettoyage."""
    if not body.zone.strip() or not body.nom_tache.strip():
        raise HTTPException(400, "Zone et nom de tâche obligatoires")

    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO taches_nettoyage (zone, nom_tache, frequence, methode_produit) VALUES (?, ?, ?, ?)",
            (body.zone.strip(), body.nom_tache.strip(), body.frequence.strip(), body.methode_produit.strip()),
        )
        await db.commit()
        new_id = cursor.lastrowid

    return {"id": new_id, "zone": body.zone.strip(), "nom_tache": body.nom_tache.strip(),
            "frequence": body.frequence.strip(), "methode_produit": body.methode_produit.strip()}


# ---------------------------------------------------------------------------
# PUT /api/nettoyage/taches/{tache_id}  — modifier une tâche
# ---------------------------------------------------------------------------

@router.put("/taches/{tache_id}")
async def modifier_tache(tache_id: int, body: TachePayload):
    """Modifie une tâche existante."""
    if not body.zone.strip() or not body.nom_tache.strip():
        raise HTTPException(400, "Zone et nom de tâche obligatoires")

    async with get_db() as db:
        result = await db.execute(
            "UPDATE taches_nettoyage SET zone=?, nom_tache=?, frequence=?, methode_produit=? WHERE id=?",
            (body.zone.strip(), body.nom_tache.strip(), body.frequence.strip(), body.methode_produit.strip(), tache_id),
        )
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(404, f"Tâche {tache_id} introuvable")

    return {"id": tache_id, "zone": body.zone.strip(), "nom_tache": body.nom_tache.strip(),
            "frequence": body.frequence.strip(), "methode_produit": body.methode_produit.strip()}


# ---------------------------------------------------------------------------
# DELETE /api/nettoyage/taches/{tache_id}  — supprimer une tâche
# ---------------------------------------------------------------------------

@router.delete("/taches/{tache_id}", status_code=200)
async def supprimer_tache(tache_id: int):
    """Supprime une tâche du plan de nettoyage."""
    async with get_db() as db:
        result = await db.execute(
            "DELETE FROM taches_nettoyage WHERE id=?",
            (tache_id,),
        )
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(404, f"Tâche {tache_id} introuvable")

    return {"ok": True, "id": tache_id}


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

    aujourd_hui = body.date or _date.today().isoformat()

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
        # Garantit l'unicité (tache_id, date_val) — tolère les tables existantes
        await db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_nett_tache_date
            ON registre_nettoyage(tache_id, date_val)
        """)

        nb = 0
        for tid in body.taches_ids:
            result = await db.execute(
                "INSERT OR IGNORE INTO registre_nettoyage (tache_id, operateur, date_val, signature) "
                "VALUES (?, ?, ?, ?)",
                (tid, body.operateur.strip(), aujourd_hui, body.signature),
            )
            nb += result.rowcount  # 1 si inséré, 0 si déjà présent

        await db.commit()

    logger.info("Nettoyage validé par %s — %d tâche(s) — %s", body.operateur, nb, aujourd_hui)
    return {
        "ok":        True,
        "operateur": body.operateur,
        "date":      aujourd_hui,
        "nb_taches": nb,
    }


# ---------------------------------------------------------------------------
# DELETE /api/nettoyage/validation  — décocher une tâche pour une date
# ---------------------------------------------------------------------------

@router.delete("/validation", status_code=200)
async def supprimer_validation_tache(
    tache_id: int = Query(..., description="ID de la tâche à décocher"),
    date: str      = Query(..., description="Date ISO (YYYY-MM-DD)"),
):
    """Supprime toutes les validations d'une tâche pour une date donnée."""
    async with get_db() as db:
        await db.execute(_ENSURE_REGISTRE)
        await db.commit()

        await db.execute(
            "DELETE FROM registre_nettoyage WHERE tache_id = ? AND date_val = ?",
            (tache_id, date),
        )
        await db.commit()

    logger.info("Validation supprimée — tache_id=%s, date=%s", tache_id, date)
    return {"ok": True, "tache_id": tache_id, "date": date}


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
            "SELECT DISTINCT tache_id, operateur FROM registre_nettoyage WHERE date_val = ?",
            (target,),
        )

    if not rows:
        return {"valide": False, "date": target, "operateur": None, "nb_taches": 0, "taches_ids": []}

    # Opérateur le plus fréquent
    ops = Counter(r[1] for r in rows)
    operateur_principal = ops.most_common(1)[0][0]
    # IDs uniques des tâches validées
    taches_ids = list({r[0] for r in rows})

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


# ---------------------------------------------------------------------------
# GET /api/nettoyage/historique/semaine
# ---------------------------------------------------------------------------

_JOURS_NOMS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


@router.get("/historique/semaine")
async def historique_semaine(
    annee_iso: int = Query(..., description="Année ISO de la semaine"),
    semaine:   int = Query(..., description="Numéro de semaine ISO (1-53)"),
):
    """
    Retourne le planning complet pour une semaine ISO donnée.
    Pour chaque tâche, indique quels jours ont été validés et par qui.
    """
    from datetime import timedelta

    # Calcul du lundi de la semaine ISO cible
    # Le 4 janvier est toujours en semaine 1
    jan4 = _date(annee_iso, 1, 4)
    monday_sem1 = jan4 - timedelta(days=jan4.isoweekday() - 1)
    monday = monday_sem1 + timedelta(weeks=semaine - 1)
    dates_semaine = [monday + timedelta(days=i) for i in range(7)]
    date_strs = [d.isoformat() for d in dates_semaine]

    async with get_db() as db:
        await db.execute(_ENSURE_REGISTRE)
        await db.commit()

        taches_rows = await db.execute_fetchall(
            "SELECT id, zone, nom_tache, frequence, methode_produit "
            "FROM taches_nettoyage ORDER BY zone, id"
        )

        placeholders = ",".join("?" * len(date_strs))
        val_rows = await db.execute_fetchall(
            f"SELECT date_val, tache_id, operateur FROM registre_nettoyage "
            f"WHERE date_val IN ({placeholders})",
            date_strs,
        )

    # Map validations : {date_str: {tache_id: "É."}}
    validations: dict = {}
    for vrow in val_rows:
        dv, tid, op = vrow[0], vrow[1], vrow[2]
        validations.setdefault(dv, {})
        if tid not in validations[dv]:
            validations[dv][tid] = (op[0].upper() + ".") if op else "?"

    # Groupement par zone
    zones: dict = {}
    for row in taches_rows:
        z = row[1]
        zones.setdefault(z, [])
        zones[z].append({
            "id":              row[0],
            "nom_tache":       row[2],
            "frequence":       row[3],
            "methode_produit": row[4],
            "validations": {
                ds: validations.get(ds, {}).get(row[0])
                for ds in date_strs
            },
        })

    return {
        "semaine":    semaine,
        "annee_iso":  annee_iso,
        "dates":      date_strs,
        "jours_noms": [f"{_JOURS_NOMS[i]} {dates_semaine[i].day}" for i in range(7)],
        "zones":      [{"zone": z, "taches": t} for z, t in zones.items()],
    }

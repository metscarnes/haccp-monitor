"""
routes_refroidissement.py — Module Refroidissement (HACCP)

Refroidissement rapide après cuisson : passer de chaud à ≤ +10 °C à cœur
en ≤ 2 heures. Si le couple temps/température n'est pas respecté
(durée > 2 h ET T° > 10 °C), les produits doivent être JETÉS.

GET  /api/refroidissement/produits
GET  /api/refroidissement/enregistrements?limit=50
POST /api/refroidissement/enregistrements
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.database import get_db, get_stock_unifie, create_dlc_devenir, DLC_JOURS_TRANSFORMATION

BOUTIQUE_ID = 1  # mono-boutique Phase 2

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/refroidissement", tags=["refroidissement"])

TEMPERATURE_CIBLE        = 10.0   # °C max à cœur après refroidissement
TEMPERATURE_MIN_CUISSON  = 75.0   # °C min à cœur en sortie de cuisson
DUREE_MAX_MINUTES        = 120    # 2 h


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _duree_minutes(heure_debut: str, heure_fin: str) -> int:
    """Durée en minutes entre deux 'HH:MM'. Si fin <= debut on suppose +24 h."""
    try:
        h1, m1 = map(int, heure_debut.split(":"))
        h2, m2 = map(int, heure_fin.split(":"))
    except Exception:
        raise HTTPException(status_code=422, detail="Format d'heure invalide (HH:MM).")
    debut = h1 * 60 + m1
    fin   = h2 * 60 + m2
    if fin <= debut:
        fin += 24 * 60
    return fin - debut


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class RefroidissementCreate(BaseModel):
    date_refroidissement: str   = Field(..., description="YYYY-MM-DD")
    personnel_id:         int
    produit_id:           int
    cuisson_id:           Optional[int] = None
    heure_debut:          str   = Field(..., description="HH:MM mise en refroidissement")
    heure_fin:            str   = Field(..., description="HH:MM fin de refroidissement")
    temperature_initiale: Optional[float] = Field(75.0, description="T° à cœur avant refroidissement")
    temperature_finale:   float = Field(..., description="T° à cœur après refroidissement")
    jeter_action:         bool  = Field(False, description="True = jeter le produit + créer entrée devenir")
    action_corrective:    Optional[str] = None


# ---------------------------------------------------------------------------
# GET /api/refroidissement/produits
# Liste des produits déjà cuits (déduit de la table cuissons)
# ---------------------------------------------------------------------------

@router.get("/produits")
async def lister_produits_cuisson():
    """
    Cuissons disponibles à refroidir : produites mais ni encore refroidies, ni jetées,
    ni périmées. Une ligne par produit, avec la cuisson FIFO (DLC la plus courte).

    Source unique : get_stock_unifie() restreint aux cuissons. Si toutes les cuissons
    sont refroidies/jetées (ou si la matière première source a été sortie en cascade),
    la liste est vide — pas de refroidissement possible.
    """
    async with get_db() as db:
        stock = await get_stock_unifie(
            db, BOUTIQUE_ID,
            type_produit="fini",
            sources=["cuisson"],
        )

    par_produit: dict[int, dict] = {}
    for lot in stock:
        pid = lot["produit_id"]
        if pid in par_produit:
            par_produit[pid]["nb_cuissons_disponibles"] += 1
            continue
        par_produit[pid] = {
            "id":                       pid,
            "nom":                      lot["produit_nom"],
            "espece":                   lot.get("espece"),
            "cuisson_id":               lot["source_id"],     # FIFO (plus pressé)
            "cuisson_date":             lot.get("date_origine"),
            "dlc":                      lot.get("dlc"),
            "numero_lot":               lot.get("numero_lot"),
            "nb_cuissons_disponibles":  1,
        }

    return sorted(par_produit.values(), key=lambda p: (p["nom"] or "").lower())


# ---------------------------------------------------------------------------
# POST /api/refroidissement/enregistrements
# ---------------------------------------------------------------------------

@router.post("/enregistrements", status_code=201)
async def creer_refroidissement(body: RefroidissementCreate):
    duree = _duree_minutes(body.heure_debut, body.heure_fin)

    temp_init = body.temperature_initiale if body.temperature_initiale is not None else 75.0
    cuisson_ok = temp_init >= TEMPERATURE_MIN_CUISSON
    duree_ok   = duree <= DUREE_MAX_MINUTES
    temp_ok    = body.temperature_finale <= TEMPERATURE_CIBLE
    conforme   = cuisson_ok and duree_ok and temp_ok

    # Règle "JETER cuisson" : pasteurisation non atteinte
    jeter_cuisson = not cuisson_ok
    # Règle "JETER refroidissement" : couple temps/T° finale non respecté
    jeter_refroidissement = (not duree_ok) and (not temp_ok)
    jeter = jeter_cuisson or jeter_refroidissement

    if not conforme and not (body.action_corrective and body.action_corrective.strip()):
        raisons = []
        if not cuisson_ok:
            raisons.append(
                f"cuisson insuffisante ({temp_init:.1f} °C < {TEMPERATURE_MIN_CUISSON} °C)"
            )
        if not temp_ok:
            raisons.append(f"T° finale trop haute ({body.temperature_finale:.1f} °C > {TEMPERATURE_CIBLE} °C)")
        if not duree_ok:
            raisons.append(f"durée dépassée ({duree} min > {DUREE_MAX_MINUTES} min)")
        raise HTTPException(
            status_code=422,
            detail=f"Action corrective obligatoire : {' · '.join(raisons)}.",
        )

    # DLC J+3 calculée côté serveur (règle HACCP transformation)
    try:
        dlc_calculee = (datetime.strptime(body.date_refroidissement, "%Y-%m-%d").date()
                        + timedelta(days=DLC_JOURS_TRANSFORMATION))
    except ValueError:
        raise HTTPException(status_code=422, detail="date_refroidissement invalide (YYYY-MM-DD attendu).")

    async with get_db() as db:
        numero_lot = None
        reception_ligne_id = None

        # Récupérer la traçabilité depuis la cuisson
        if body.cuisson_id:
            cur_cuisson = await db.execute(
                """
                SELECT c.reception_ligne_id
                FROM cuissons c
                WHERE c.id = ?
                """,
                (body.cuisson_id,),
            )
            cuisson = await cur_cuisson.fetchone()
            if cuisson and cuisson["reception_ligne_id"]:
                reception_ligne_id = cuisson["reception_ligne_id"]
                # Récupérer le numéro de lot et la DLC d'origine depuis reception_lignes
                cur_reception = await db.execute(
                    """
                    SELECT numero_lot, dlc FROM reception_lignes WHERE id = ?
                    """,
                    (reception_ligne_id,),
                )
                reception_ligne = await cur_reception.fetchone()
                if reception_ligne:
                    numero_lot = reception_ligne["numero_lot"]

        # Règle métier absolue : la DLC ne peut pas dépasser la DLC de réception d'origine
        dlc_finale = dlc_calculee
        dlc_origine = None
        dlc_ajustee = False
        if reception_ligne_id and reception_ligne and reception_ligne["dlc"]:
            dlc_origine = datetime.strptime(reception_ligne["dlc"], "%Y-%m-%d").date()
            if dlc_calculee > dlc_origine:
                dlc_finale = dlc_origine
                dlc_ajustee = True
            else:
                dlc_finale = dlc_calculee
        dlc_finale_iso = dlc_finale.isoformat()

        cur = await db.execute(
            """
            INSERT INTO refroidissements (
                date_refroidissement, personnel_id, produit_id, cuisson_id,
                numero_lot, reception_ligne_id,
                heure_debut, heure_fin, duree_minutes,
                temperature_initiale, temperature_finale,
                temperature_cible, duree_max_minutes,
                conforme, jeter, action_corrective, dlc_finale
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                body.date_refroidissement,
                body.personnel_id,
                body.produit_id,
                body.cuisson_id,
                numero_lot,
                reception_ligne_id,
                body.heure_debut,
                body.heure_fin,
                duree,
                body.temperature_initiale if body.temperature_initiale is not None else 75.0,
                body.temperature_finale,
                TEMPERATURE_CIBLE,
                DUREE_MAX_MINUTES,
                1 if conforme else 0,
                1 if jeter else 0,
                (body.action_corrective or "").strip() or None,
                dlc_finale_iso,
            ),
        )
        nouveau_id = cur.lastrowid

        # Entrée "devenir" dans le calendrier DLC si l'opérateur confirme le jet
        if body.jeter_action:
            try:
                await create_dlc_devenir(
                    db,
                    source_type="refroidissement",
                    source_id=nouveau_id,
                    statut="jete",
                    personnel_id=body.personnel_id,
                    commentaire=(body.action_corrective or "").strip() or "Produit jeté — refroidissement non conforme",
                )
            except Exception as exc:
                logger.warning("dlc_devenir non créé pour refroidissement #%d : %s", nouveau_id, exc)

        await db.commit()

    logger.info(
        "Refroidissement #%d — produit=%d durée=%dmin T°init=%.1f T°=%.1f conforme=%s jeter=%s jeter_action=%s",
        nouveau_id, body.produit_id, duree, temp_init, body.temperature_finale,
        conforme, jeter, body.jeter_action,
    )
    return {
        "ok":            True,
        "id":            nouveau_id,
        "duree_minutes": duree,
        "conforme":      conforme,
        "jeter":         jeter,
        "jeter_cuisson": jeter_cuisson,
        "cuisson_ok":    cuisson_ok,
        "devenir_cree":  body.jeter_action,
        "dlc_ajustee":   dlc_ajustee,
        "dlc_origine":   dlc_origine.isoformat() if dlc_origine else None,
    }


# ---------------------------------------------------------------------------
# GET /api/refroidissement/enregistrements
# ---------------------------------------------------------------------------

@router.get("/enregistrements")
async def lister_refroidissements(
    date_debut: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_fin:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit:      int = Query(50, ge=1, le=500),
):
    clauses: list = []
    params:  list = []
    if date_debut:
        clauses.append("r.date_refroidissement >= ?")
        params.append(date_debut)
    if date_fin:
        clauses.append("r.date_refroidissement <= ?")
        params.append(date_fin)
    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)

    async with get_db() as db:
        cur = await db.execute(
            f"""
            SELECT r.*,
                   p.nom        AS produit_nom,
                   p.espece     AS espece,
                   pers.prenom  AS personnel_prenom,
                   rl.numero_lot AS reception_numero_lot
            FROM   refroidissements r
            LEFT   JOIN produits  p    ON p.id    = r.produit_id
            LEFT   JOIN personnel pers ON pers.id = r.personnel_id
            LEFT   JOIN reception_lignes rl ON rl.id = r.reception_ligne_id
            {where_sql}
            ORDER BY r.date_refroidissement DESC, r.id DESC
            LIMIT ?
            """,
            tuple(params),
        )
        rows = await cur.fetchall()

    return [dict(r) for r in rows]

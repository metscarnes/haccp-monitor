"""
routes_actions_correctives.py — Agrégateur des actions correctives HACCP

GET /api/actions-correctives?source=incidents|etalonnages|cuissons|refroidissements
                            &date_debut=YYYY-MM-DD&date_fin=YYYY-MM-DD&limit=50&offset=0

Agrège les non-conformités tracées dans 4 modules :
  - fiches_incident (PCR01 — réceptions NC)
  - etalonnages (conforme=0)
  - cuissons (conforme=0)
  - refroidissements (conforme=0)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query

from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/actions-correctives", tags=["actions-correctives"])


def _date_clause(col: str, date_debut: Optional[str], date_fin: Optional[str]) -> tuple[str, list]:
    parts: list[str] = []
    params: list = []
    if date_debut:
        parts.append(f"{col} >= ?")
        params.append(date_debut)
    if date_fin:
        parts.append(f"{col} <= ?")
        params.append(date_fin)
    return (" AND ".join(parts), params)


@router.get("/incidents")
async def lister_incidents(
    date_debut: Optional[str] = Query(None),
    date_fin:   Optional[str] = Query(None),
    limit:      int           = Query(50, ge=1, le=500),
    offset:     int           = Query(0,  ge=0),
):
    """Fiches PCR01 — non-conformités à réception avec action corrective."""
    where, params = _date_clause("fi.date_incident", date_debut, date_fin)
    where_sql = f"WHERE {where}" if where else ""
    sql = f"""
        SELECT
            fi.id,
            fi.date_incident   AS date,
            fi.heure_incident  AS heure,
            fi.nature_probleme,
            fi.action_immediate,
            fi.action_corrective,
            fi.statut,
            fi.reception_id,
            COALESCE(f.nom, fi.fournisseur_nom) AS fournisseur_nom,
            p.nom AS produit_nom,
            fi.numero_lot
        FROM fiches_incident fi
        LEFT JOIN fournisseurs f ON f.id = fi.fournisseur_id
        LEFT JOIN produits     p ON p.id = fi.produit_id
        {where_sql}
        ORDER BY fi.date_incident DESC, fi.heure_incident DESC
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]
    async with get_db() as db:
        cur = await db.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.get("/etalonnages")
async def lister_etalonnages_nc(
    date_debut: Optional[str] = Query(None),
    date_fin:   Optional[str] = Query(None),
    limit:      int           = Query(50, ge=1, le=500),
    offset:     int           = Query(0,  ge=0),
):
    """
    Étalonnages non conformes — agrège deux sources :
      - Phase 1 : table etalonnages (conforme=0, écart > ±0,5 °C sur le thermomètre de référence)
      - Phase 2 : table etalonnage_comparaisons (conforme=0, sonde Zigbee à recalibrer)
    """
    # ── Phase 1 : étalonnage du thermomètre de référence ──
    where_p1, params_p1 = _date_clause("e.date_etalonnage", date_debut, date_fin)
    extra_p1 = "e.conforme = 0"
    where_sql_p1 = f"WHERE {extra_p1}" + (f" AND {where_p1}" if where_p1 else "")
    sql_p1 = f"""
        SELECT
            'phase1'              AS type,
            e.id                  AS id,
            e.date_etalonnage     AS date,
            e.temperature_mesuree AS temperature_mesuree,
            e.action_corrective   AS action_corrective,
            e.operateur           AS operateur,
            e.commentaire         AS commentaire,
            tr.nom                AS thermometre_nom,
            NULL                  AS enceinte_nom,
            NULL                  AS temp_zigbee,
            NULL                  AS temp_reference,
            NULL                  AS ecart
        FROM etalonnages e
        LEFT JOIN thermometres_ref tr ON tr.id = e.thermometre_ref_id
        {where_sql_p1}
    """

    # ── Phase 2 : comparaisons sondes Zigbee ──
    where_p2, params_p2 = _date_clause("e.date_etalonnage", date_debut, date_fin)
    extra_p2 = "c.conforme = 0"
    where_sql_p2 = f"WHERE {extra_p2}" + (f" AND {where_p2}" if where_p2 else "")
    sql_p2 = f"""
        SELECT
            'phase2'                                          AS type,
            c.id                                              AS id,
            e.date_etalonnage                                 AS date,
            NULL                                              AS temperature_mesuree,
            'Sonde Zigbee à recalibrer (responsable prévenu)' AS action_corrective,
            e.operateur                                       AS operateur,
            NULL                                              AS commentaire,
            tr.nom                                            AS thermometre_nom,
            c.enceinte_nom                                    AS enceinte_nom,
            c.temp_zigbee                                     AS temp_zigbee,
            c.temp_reference                                  AS temp_reference,
            c.ecart                                           AS ecart
        FROM etalonnage_comparaisons c
        JOIN etalonnages e        ON e.id  = c.etalonnage_id
        LEFT JOIN thermometres_ref tr ON tr.id = e.thermometre_ref_id
        {where_sql_p2}
    """

    sql = f"""
        SELECT * FROM (
            {sql_p1}
            UNION ALL
            {sql_p2}
        ) AS u
        ORDER BY date DESC, id DESC
        LIMIT ? OFFSET ?
    """
    params = params_p1 + params_p2 + [limit, offset]
    async with get_db() as db:
        cur = await db.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.get("/cuissons")
async def lister_cuissons_nc(
    date_debut: Optional[str] = Query(None),
    date_fin:   Optional[str] = Query(None),
    limit:      int           = Query(50, ge=1, le=500),
    offset:     int           = Query(0,  ge=0),
):
    """Cuissons non conformes (sous la température cible)."""
    where, params = _date_clause("c.date_cuisson", date_debut, date_fin)
    extra = "c.conforme = 0 AND c.action_corrective IS NOT NULL AND c.action_corrective != ''"
    where_sql = f"WHERE {extra}" + (f" AND {where}" if where else "")
    sql = f"""
        SELECT
            c.id,
            c.date_cuisson        AS date,
            c.heure_debut,
            c.heure_fin,
            c.type_cuisson,
            c.temperature_sortie,
            c.temperature_cible,
            c.action_corrective,
            c.quantite,
            c.unite,
            p.nom AS produit_nom,
            pe.prenom || ' ' || COALESCE(pe.nom, '') AS operateur
        FROM cuissons c
        LEFT JOIN produits  p  ON p.id  = c.produit_id
        LEFT JOIN personnel pe ON pe.id = c.personnel_id
        {where_sql}
        ORDER BY c.date_cuisson DESC, c.heure_debut DESC
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]
    async with get_db() as db:
        cur = await db.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.get("/refroidissements")
async def lister_refroidissements_nc(
    date_debut: Optional[str] = Query(None),
    date_fin:   Optional[str] = Query(None),
    limit:      int           = Query(50, ge=1, le=500),
    offset:     int           = Query(0,  ge=0),
):
    """Refroidissements non conformes (> 10 °C ou > 2 h)."""
    where, params = _date_clause("r.date_refroidissement", date_debut, date_fin)
    extra = "r.conforme = 0 AND r.action_corrective IS NOT NULL AND r.action_corrective != ''"
    where_sql = f"WHERE {extra}" + (f" AND {where}" if where else "")
    sql = f"""
        SELECT
            r.id,
            r.date_refroidissement AS date,
            r.heure_debut,
            r.heure_fin,
            r.duree_minutes,
            r.duree_max_minutes,
            r.temperature_initiale,
            r.temperature_finale,
            r.temperature_cible,
            r.action_corrective,
            r.jeter,
            r.numero_lot,
            p.nom AS produit_nom,
            pe.prenom || ' ' || COALESCE(pe.nom, '') AS operateur
        FROM refroidissements r
        LEFT JOIN produits  p  ON p.id  = r.produit_id
        LEFT JOIN personnel pe ON pe.id = r.personnel_id
        {where_sql}
        ORDER BY r.date_refroidissement DESC, r.heure_debut DESC
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]
    async with get_db() as db:
        cur = await db.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]

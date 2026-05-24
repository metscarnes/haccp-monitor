"""
routes_admin.py — Configuration admin (personnel, pièges)

GET    /api/admin/personnel             → liste du personnel
POST   /api/admin/personnel             → ajouter un membre
PUT    /api/admin/personnel/{id}        → modifier
GET    /api/admin/pieges                → configuration des pièges
POST   /api/admin/pieges                → ajouter un piège
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.database import (
    get_db,
    get_personnel, create_personnel, update_personnel,
    get_pieges, create_piege,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

BOUTIQUE_ID = 1


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class PersonnelCreate(BaseModel):
    prenom: str


class PersonnelUpdate(BaseModel):
    prenom: Optional[str] = None
    actif: Optional[bool] = None


class PiegeCreate(BaseModel):
    type: str           # "rongeur" | "oiseau"
    identifiant: str    # "P1", "P2", ...
    localisation: Optional[str] = None


# ---------------------------------------------------------------------------
# Personnel
# ---------------------------------------------------------------------------

@router.get("/personnel")
async def lister_personnel():
    async with get_db() as db:
        return await get_personnel(db, BOUTIQUE_ID)


@router.post("/personnel", status_code=201)
async def ajouter_personnel(body: PersonnelCreate):
    async with get_db() as db:
        pid = await create_personnel(db, {"boutique_id": BOUTIQUE_ID, "prenom": body.prenom})
        cursor = await db.execute("SELECT * FROM personnel WHERE id = ?", (pid,))
        row = await cursor.fetchone()
    return dict(row) if row else {"id": pid}


@router.put("/personnel/{personnel_id}")
async def modifier_personnel(personnel_id: int, body: PersonnelUpdate):
    async with get_db() as db:
        ok = await update_personnel(db, personnel_id, body.model_dump(exclude_none=True))
    if not ok:
        raise HTTPException(404, "Personnel non trouvé")
    return {"ok": True}


CATEGORIES_PURGE = {
    "receptions":   "Réceptions (lignes, BLs, fiches incident, non-conformités)",
    "production":   "Production (cuissons, refroidissements, fabrications)",
    "etiquettes":   "Étiquettes générées",
    "taches":       "Tâches & nettoyage",
    "etalonnage":   "Étalonnage thermomètres",
    "nuisibles":    "Contrôles nuisibles",
    "dlc":          "DLC (devenirs)",
    "formation":    "Formation (e-learning, quiz)",
    "ouvertures":   "Contrôles ouvertures",
}


class PurgeBody(BaseModel):
    categories: Optional[list] = None  # None = toutes


@router.delete("/personnel/{personnel_id}/entrees")
async def purger_entrees_personnel(personnel_id: int, body: PurgeBody = PurgeBody()):
    """Supprime les entrées créées par un membre du personnel, par catégorie.

    `categories` : liste parmi receptions, production, etiquettes, taches,
    etalonnage, nuisibles, dlc, formation, ouvertures.
    Si absent ou null → toutes les catégories.
    Le membre du personnel est conservé.
    """
    cats = set(body.categories) if body.categories else set(CATEGORIES_PURGE)

    async with get_db() as db:
        cur = await db.execute("SELECT prenom FROM personnel WHERE id = ?", (personnel_id,))
        row = await cur.fetchone()
        if row is None:
            raise HTTPException(404, "Personnel non trouvé")
        prenom = row["prenom"]

        supprime: dict[str, int] = {}
        erreurs: dict[str, str] = {}

        existing_tables = {
            r[0] for r in await db.execute_fetchall(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

        async def _cols(table: str) -> set:
            rows = await db.execute_fetchall(f"PRAGMA table_info({table})")
            return {r[1] for r in rows}

        async def _del(table: str, col: str, where: str, params: tuple) -> None:
            if table not in existing_tables:
                return
            if col not in await _cols(table):
                return
            try:
                c = await db.execute(f"DELETE FROM {table} WHERE {where}", params)
                if c.rowcount:
                    supprime[table] = supprime.get(table, 0) + c.rowcount
            except Exception as exc:  # noqa: BLE001
                erreurs[table] = str(exc)

        # ── Collecte des IDs parents (utilisés par plusieurs catégories) ─────
        rec_ids: list = []
        if ("receptions" in cats or "production" in cats) \
                and "receptions" in existing_tables \
                and "personnel_id" in await _cols("receptions"):
            rows = await db.execute_fetchall(
                "SELECT id FROM receptions WHERE personnel_id = ?", (personnel_id,)
            )
            rec_ids = [r[0] for r in rows]

        fabric_ids: list = []
        if "production" in cats \
                and "fabrications" in existing_tables \
                and "personnel_id" in await _cols("fabrications"):
            rows = await db.execute_fetchall(
                "SELECT id FROM fabrications WHERE personnel_id = ?", (personnel_id,)
            )
            fabric_ids = [r[0] for r in rows]

        etalon_ids: list = []
        if "etalonnage" in cats \
                and "etalonnages" in existing_tables \
                and "operateur" in await _cols("etalonnages"):
            rows = await db.execute_fetchall(
                "SELECT id FROM etalonnages WHERE operateur = ?", (prenom,)
            )
            etalon_ids = [r[0] for r in rows]

        # ── Suppressions dans l'ordre FK (enfants avant parents) ─────────────

        # PRODUCTION ─────────────────────────────────────────────────────────
        if "production" in cats:
            await _del("refroidissements", "personnel_id", "personnel_id = ?", (personnel_id,))
            if fabric_ids:
                ph = ",".join("?" * len(fabric_ids))
                await _del("fabrication_lots", "fabrication_id",
                           f"fabrication_id IN ({ph})", tuple(fabric_ids))
            await _del("cuissons", "personnel_id", "personnel_id = ?", (personnel_id,))

        # RÉCEPTIONS ─────────────────────────────────────────────────────────
        if "receptions" in cats and rec_ids:
            ph = ",".join("?" * len(rec_ids))
            await _del("fiches_incident", "reception_id",
                       f"reception_id IN ({ph})", tuple(rec_ids))
            await _del("non_conformites_fournisseur", "reception_id",
                       f"reception_id IN ({ph})", tuple(rec_ids))
            await _del("reception_bls_supplementaires", "reception_id",
                       f"reception_id IN ({ph})", tuple(rec_ids))
            # Ouvertures liées à ces lignes de réception
            await _del("ouvertures", "reception_ligne_id",
                       f"reception_ligne_id IN (SELECT id FROM reception_lignes WHERE reception_id IN ({ph}))",
                       tuple(rec_ids))
            await _del("reception_lignes", "reception_id",
                       f"reception_id IN ({ph})", tuple(rec_ids))

        if "receptions" in cats:
            await _del("receptions", "personnel_id", "personnel_id = ?", (personnel_id,))
            await _del("fiches_incident", "cloturee_par", "cloturee_par = ?", (personnel_id,))

        # OUVERTURES (hors réceptions) ────────────────────────────────────────
        if "ouvertures" in cats:
            await _del("ouvertures", "personnel_id", "personnel_id = ?", (personnel_id,))

        # FABRICATIONS (table principale, orpheline si pas dans production) ───
        if "production" in cats:
            await _del("fabrications", "personnel_id", "personnel_id = ?", (personnel_id,))

        # ÉTALONNAGE ──────────────────────────────────────────────────────────
        if "etalonnage" in cats:
            if etalon_ids:
                ph = ",".join("?" * len(etalon_ids))
                await _del("etalonnage_comparaisons", "etalonnage_id",
                           f"etalonnage_id IN ({ph})", tuple(etalon_ids))
            await _del("etalonnages", "operateur", "operateur = ?", (prenom,))

        # ÉTIQUETTES ──────────────────────────────────────────────────────────
        if "etiquettes" in cats:
            await _del("etiquettes_generees", "operateur", "operateur = ?", (prenom,))

        # TÂCHES & NETTOYAGE ──────────────────────────────────────────────────
        if "taches" in cats:
            await _del("tache_validations", "operateur", "operateur = ?", (prenom,))
            await _del("registre_nettoyage", "operateur", "operateur = ?", (prenom,))

        # NUISIBLES ───────────────────────────────────────────────────────────
        if "nuisibles" in cats:
            await _del("nuisibles_controles", "visa", "visa = ?", (prenom,))

        # DLC ─────────────────────────────────────────────────────────────────
        if "dlc" in cats:
            await _del("dlc_devenir", "personnel_id", "personnel_id = ?", (personnel_id,))

        # FORMATION ───────────────────────────────────────────────────────────
        if "formation" in cats:
            await _del("elearning_completions", "personnel_id", "personnel_id = ?", (personnel_id,))
            await _del("quiz_resultats", "personnel_id", "personnel_id = ?", (personnel_id,))
            await _del("quiz_progression", "personnel_id", "personnel_id = ?", (personnel_id,))

        await db.commit()

    total = sum(supprime.values())
    return {"ok": True, "personnel_id": personnel_id, "prenom": prenom,
            "total": total, "detail": supprime, "erreurs": erreurs}


# ---------------------------------------------------------------------------
# Pièges
# ---------------------------------------------------------------------------

@router.get("/pieges")
async def lister_pieges():
    async with get_db() as db:
        return await get_pieges(db, BOUTIQUE_ID)


@router.post("/pieges", status_code=201)
async def ajouter_piege(body: PiegeCreate):
    async with get_db() as db:
        pid = await create_piege(db, {"boutique_id": BOUTIQUE_ID, **body.model_dump()})
        cursor = await db.execute("SELECT * FROM pieges WHERE id = ?", (pid,))
        row = await cursor.fetchone()
    return dict(row) if row else {"id": pid}


# ---------------------------------------------------------------------------
# Thermomètres de référence
# ---------------------------------------------------------------------------

class ThermometreCreate(BaseModel):
    nom:          str
    numero_serie: Optional[str] = None


class ThermometreUpdate(BaseModel):
    nom:          Optional[str]  = None
    numero_serie: Optional[str]  = None
    actif:        Optional[bool] = None


@router.get("/thermometres")
async def lister_thermometres():
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT id, nom, numero_serie, actif FROM thermometres_ref "
            "WHERE boutique_id = ? ORDER BY nom",
            (BOUTIQUE_ID,),
        )
    return [{"id": r[0], "nom": r[1], "numero_serie": r[2], "actif": bool(r[3])}
            for r in rows]


@router.post("/thermometres", status_code=201)
async def ajouter_thermometre(body: ThermometreCreate):
    async with get_db() as db:
        cur = await db.execute(
            "INSERT INTO thermometres_ref (boutique_id, nom, numero_serie) VALUES (?, ?, ?)",
            (BOUTIQUE_ID, body.nom.strip(), body.numero_serie),
        )
        await db.commit()
        row = await db.execute_fetchall(
            "SELECT id, nom, numero_serie, actif FROM thermometres_ref WHERE id = ?",
            (cur.lastrowid,),
        )
    r = row[0]
    return {"id": r[0], "nom": r[1], "numero_serie": r[2], "actif": bool(r[3])}


@router.put("/thermometres/{thermo_id}")
async def modifier_thermometre(thermo_id: int, body: ThermometreUpdate):
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(400, "Aucun champ à modifier")
    sets = ", ".join(f"{k} = ?" for k in data)
    async with get_db() as db:
        cur = await db.execute(
            f"UPDATE thermometres_ref SET {sets} WHERE id = ?",
            (*data.values(), thermo_id),
        )
        await db.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "Thermomètre non trouvé")
    return {"ok": True}


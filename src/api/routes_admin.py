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


@router.delete("/personnel/{personnel_id}/entrees")
async def purger_entrees_personnel(personnel_id: int):
    """Supprime TOUTES les entrées créées par un membre du personnel.

    Utilisé pour réinitialiser le compte « test » servant aux essais et aux
    formations. Le membre du personnel lui-même est conservé : seules ses
    données sont effacées.

    Couvre les deux modes de liaison opérateur du schéma :
      - clé étrangère personnel_id / cloturee_par
      - texte libre operateur / visa (comparé au prénom exact)
    """
    async with get_db() as db:
        cur = await db.execute("SELECT prenom FROM personnel WHERE id = ?", (personnel_id,))
        row = await cur.fetchone()
        if row is None:
            raise HTTPException(404, "Personnel non trouvé")
        prenom = row["prenom"]

        supprime: dict[str, int] = {}

        async def _del(table: str, where: str, params: tuple) -> None:
            c = await db.execute(f"DELETE FROM {table} WHERE {where}", params)
            if c.rowcount:
                supprime[table] = supprime.get(table, 0) + c.rowcount

        # 1) Enfants des réceptions de l'utilisateur (évite les orphelins) ----
        #    On récupère d'abord les réceptions concernées.
        rec_rows = await db.execute_fetchall(
            "SELECT id FROM receptions WHERE personnel_id = ?", (personnel_id,)
        )
        rec_ids = [r[0] for r in rec_rows]
        if rec_ids:
            placeholders = ",".join("?" * len(rec_ids))
            await _del("fiches_incident", f"reception_id IN ({placeholders})", tuple(rec_ids))
            await _del("non_conformites_fournisseur", f"reception_id IN ({placeholders})", tuple(rec_ids))
            await _del("reception_lignes", f"reception_id IN ({placeholders})", tuple(rec_ids))

        # 2) Tables liées par clé étrangère personnel_id ----------------------
        for table in (
            "receptions", "ouvertures", "cuissons", "refroidissements",
            "fabrications", "dlc_devenir", "elearning_completions",
            "quiz_resultats", "quiz_progression",
        ):
            await _del(table, "personnel_id = ?", (personnel_id,))

        # 3) Fiches incident clôturées par l'utilisateur (FK cloturee_par) ----
        await _del("fiches_incident", "cloturee_par = ?", (personnel_id,))

        # 4) Tables liées par texte operateur = prénom ------------------------
        for table in (
            "etiquettes_generees", "tache_validations", "etalonnages",
            "registre_nettoyage", "non_conformites_fournisseur",
        ):
            await _del(table, "operateur = ?", (prenom,))

        # 5) Contrôles nuisibles visés par l'utilisateur (texte visa) ---------
        await _del("nuisibles_controles", "visa = ?", (prenom,))

        await db.commit()

    total = sum(supprime.values())
    return {"ok": True, "personnel_id": personnel_id, "prenom": prenom,
            "total": total, "detail": supprime}


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


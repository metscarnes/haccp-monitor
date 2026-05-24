"""
routes_admin.py — Configuration admin (personnel, pièges)

GET    /api/admin/personnel             → liste du personnel
POST   /api/admin/personnel             → ajouter un membre
PUT    /api/admin/personnel/{id}        → modifier
GET    /api/admin/pieges                → configuration des pièges
POST   /api/admin/pieges                → ajouter un piège
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

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


# Sous-catégories disponibles pour la purge sélective.
# Clé = identifiant envoyé par le frontend.
# Les suppressions qui ont des dépendances FK sont gérées dans l'endpoint.
SOUS_CATEGORIES = {
    # Réceptions
    "rec_receptions":        "Réceptions & lignes de produits",
    "rec_bls":               "BLs supplémentaires",
    "rec_fiches_incident":   "Fiches incident (PCR01)",
    "rec_non_conformites":   "Non-conformités fournisseur",
    # Production
    "prod_cuissons":         "Cuissons",
    "prod_refroidissements": "Refroidissements",
    "prod_fabrications":     "Fabrications & lots",
    # Étiquettes
    "etiquettes":            "Étiquettes générées",
    # Tâches
    "taches_haccp":          "Validations tâches HACCP",
    "taches_nettoyage":      "Registre nettoyage",
    # Étalonnage
    "etal_mesures":          "Étalonnages (mesures eau glacée)",
    "etal_comparaisons":     "Comparaisons enceintes",
    # Nuisibles
    "nuisibles":             "Contrôles nuisibles",
    # DLC
    "dlc":                   "Devenirs DLC",
    # Formation
    "form_elearning":          "E-learning (modules PDF/vidéo)",
    "form_quiz_resultats":     "Quiz — résultats (score, date)",
    "form_quiz_signatures":    "Quiz — signatures (attestations)",
    "form_quiz_progression":   "Quiz — progression (réponses en cours)",
    # Ouvertures
    "ouvertures":            "Contrôles ouvertures produits",
}


class PurgeBody(BaseModel):
    sous_categories: Optional[list] = None  # None = toutes


@router.delete("/personnel/{personnel_id}/entrees")
async def purger_entrees_personnel(personnel_id: int, body: PurgeBody = PurgeBody()):
    """Supprime les entrées d'un membre du personnel par sous-catégorie.

    `sous_categories` : liste de clés parmi SOUS_CATEGORIES.
    Si absent ou null → tout supprimer.
    Le membre du personnel est conservé.
    """
    cats = set(body.sous_categories) if body.sous_categories else set(SOUS_CATEGORIES)

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

        # ── Collecte des IDs parents nécessaires aux cascades FK ─────────────

        # IDs réceptions de l'utilisateur (utiles à plusieurs sous-cats)
        rec_ids: list = []
        need_rec_ids = cats & {"rec_receptions", "rec_bls", "rec_fiches_incident",
                               "rec_non_conformites", "ouvertures",
                               "prod_cuissons", "prod_refroidissements", "prod_fabrications"}
        if need_rec_ids and "receptions" in existing_tables \
                and "personnel_id" in await _cols("receptions"):
            rows = await db.execute_fetchall(
                "SELECT id FROM receptions WHERE personnel_id = ?", (personnel_id,)
            )
            rec_ids = [r[0] for r in rows]

        # IDs fabrications (pour supprimer les lots enfants)
        fabric_ids: list = []
        if "prod_fabrications" in cats and "fabrications" in existing_tables \
                and "personnel_id" in await _cols("fabrications"):
            rows = await db.execute_fetchall(
                "SELECT id FROM fabrications WHERE personnel_id = ?", (personnel_id,)
            )
            fabric_ids = [r[0] for r in rows]

        # IDs étalonnages (pour supprimer les comparaisons enfants)
        etalon_ids: list = []
        if cats & {"etal_mesures", "etal_comparaisons"} and "etalonnages" in existing_tables \
                and "operateur" in await _cols("etalonnages"):
            rows = await db.execute_fetchall(
                "SELECT id FROM etalonnages WHERE operateur = ?", (prenom,)
            )
            etalon_ids = [r[0] for r in rows]

        # ── Suppressions dans l'ordre FK (enfants avant parents) ─────────────

        # REFROIDISSEMENTS (enfant de cuissons) ───────────────────────────────
        if "prod_refroidissements" in cats:
            await _del("refroidissements", "personnel_id", "personnel_id = ?", (personnel_id,))

        # COMPARAISONS ÉTALONNAGE (enfant d'étalonnages) ──────────────────────
        if "etal_comparaisons" in cats and etalon_ids:
            ph = ",".join("?" * len(etalon_ids))
            await _del("etalonnage_comparaisons", "etalonnage_id",
                       f"etalonnage_id IN ({ph})", tuple(etalon_ids))

        # LOTS FABRICATION (enfant de fabrications) ───────────────────────────
        if "prod_fabrications" in cats and fabric_ids:
            ph = ",".join("?" * len(fabric_ids))
            await _del("fabrication_lots", "fabrication_id",
                       f"fabrication_id IN ({ph})", tuple(fabric_ids))

        # CUISSONS (enfant de reception_lignes) ───────────────────────────────
        if "prod_cuissons" in cats:
            await _del("cuissons", "personnel_id", "personnel_id = ?", (personnel_id,))

        # Dépendants de receptions / reception_lignes ─────────────────────────
        if rec_ids:
            ph = ",".join("?" * len(rec_ids))
            if "rec_fiches_incident" in cats:
                await _del("fiches_incident", "reception_id",
                           f"reception_id IN ({ph})", tuple(rec_ids))
            if "rec_non_conformites" in cats:
                await _del("non_conformites_fournisseur", "reception_id",
                           f"reception_id IN ({ph})", tuple(rec_ids))
            if "rec_bls" in cats:
                await _del("reception_bls_supplementaires", "reception_id",
                           f"reception_id IN ({ph})", tuple(rec_ids))
            if "ouvertures" in cats:
                # Ouvertures liées aux lignes de réception de cet utilisateur
                await _del("ouvertures", "reception_ligne_id",
                           f"reception_ligne_id IN "
                           f"(SELECT id FROM reception_lignes WHERE reception_id IN ({ph}))",
                           tuple(rec_ids))
            if "rec_receptions" in cats:
                await _del("reception_lignes", "reception_id",
                           f"reception_id IN ({ph})", tuple(rec_ids))

        # RÉCEPTIONS (racine) ─────────────────────────────────────────────────
        if "rec_receptions" in cats:
            await _del("receptions", "personnel_id", "personnel_id = ?", (personnel_id,))
            # Fiches clôturées par l'utilisateur (FK cloturee_par)
            await _del("fiches_incident", "cloturee_par", "cloturee_par = ?", (personnel_id,))

        # OUVERTURES directes (par personnel_id, pas liées à une réception) ───
        if "ouvertures" in cats:
            await _del("ouvertures", "personnel_id", "personnel_id = ?", (personnel_id,))

        # FABRICATIONS ────────────────────────────────────────────────────────
        if "prod_fabrications" in cats:
            await _del("fabrications", "personnel_id", "personnel_id = ?", (personnel_id,))

        # ÉTALONNAGES (mesures) ───────────────────────────────────────────────
        if "etal_mesures" in cats:
            if etalon_ids and "etal_comparaisons" not in cats:
                # Comparaisons enfants à supprimer d'abord si pas déjà fait
                ph = ",".join("?" * len(etalon_ids))
                await _del("etalonnage_comparaisons", "etalonnage_id",
                           f"etalonnage_id IN ({ph})", tuple(etalon_ids))
            await _del("etalonnages", "operateur", "operateur = ?", (prenom,))

        # ÉTIQUETTES ──────────────────────────────────────────────────────────
        if "etiquettes" in cats:
            await _del("etiquettes_generees", "operateur", "operateur = ?", (prenom,))

        # TÂCHES HACCP ────────────────────────────────────────────────────────
        if "taches_haccp" in cats:
            await _del("tache_validations", "operateur", "operateur = ?", (prenom,))

        # NETTOYAGE ───────────────────────────────────────────────────────────
        if "taches_nettoyage" in cats:
            await _del("registre_nettoyage", "operateur", "operateur = ?", (prenom,))

        # NUISIBLES ───────────────────────────────────────────────────────────
        if "nuisibles" in cats:
            await _del("nuisibles_controles", "visa", "visa = ?", (prenom,))

        # DLC ─────────────────────────────────────────────────────────────────
        if "dlc" in cats:
            await _del("dlc_devenir", "personnel_id", "personnel_id = ?", (personnel_id,))

        # E-LEARNING ──────────────────────────────────────────────────────────
        if "form_elearning" in cats:
            await _del("elearning_completions", "personnel_id", "personnel_id = ?", (personnel_id,))

        # QUIZ résultats (suppression ligne entière — inclut score + date) ─────
        if "form_quiz_resultats" in cats:
            await _del("quiz_resultats", "personnel_id", "personnel_id = ?", (personnel_id,))

        # QUIZ signatures seulement (UPDATE SET signature=NULL) ───────────────
        elif "form_quiz_signatures" in cats:
            if "quiz_resultats" in existing_tables \
                    and "signature" in await _cols("quiz_resultats"):
                try:
                    c = await db.execute(
                        "UPDATE quiz_resultats SET signature = NULL "
                        "WHERE personnel_id = ? AND signature IS NOT NULL",
                        (personnel_id,)
                    )
                    if c.rowcount:
                        supprime["quiz_resultats(signatures)"] = c.rowcount
                except Exception as exc:  # noqa: BLE001
                    erreurs["quiz_resultats(signatures)"] = str(exc)

        # QUIZ progression (réponses en cours) ────────────────────────────────
        if "form_quiz_progression" in cats:
            await _del("quiz_progression", "personnel_id", "personnel_id = ?", (personnel_id,))

        await db.commit()

    total = sum(supprime.values())
    return {"ok": True, "personnel_id": personnel_id, "prenom": prenom,
            "total": total, "detail": supprime, "erreurs": erreurs}


# ---------------------------------------------------------------------------
# Purge historique température
# ---------------------------------------------------------------------------

class PurgeTempBody(BaseModel):
    avant_date: Optional[str] = None   # "YYYY-MM-DD" — si None : tout supprimer
    inclure_alertes: bool = True       # supprimer aussi les alertes associées


@router.delete("/historique-temperature")
async def purger_historique_temperature(body: PurgeTempBody = PurgeTempBody()):
    """Supprime les relevés de température (et alertes associées).

    Si `avant_date` est fourni, ne supprime que les relevés antérieurs à cette
    date (horodatage < avant_date). Sinon, vide tout l'historique.
    """
    async with get_db() as db:
        supprime: dict[str, int] = {}
        erreurs: dict[str, str] = {}

        existing_tables = {
            r[0] for r in await db.execute_fetchall(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

        async def _del(table: str, where: str, params: tuple) -> None:
            if table not in existing_tables:
                return
            try:
                c = await db.execute(f"DELETE FROM {table} WHERE {where}", params)
                if c.rowcount:
                    supprime[table] = c.rowcount
            except Exception as exc:  # noqa: BLE001
                erreurs[table] = str(exc)

        if body.avant_date:
            await _del("releves", "horodatage < ?", (body.avant_date,))
            if body.inclure_alertes:
                await _del("alertes", "debut < ?", (body.avant_date,))
        else:
            await _del("releves", "1 = 1", ())
            if body.inclure_alertes:
                await _del("alertes", "1 = 1", ())

        await db.commit()

    total = sum(supprime.values())
    return {"ok": True, "total": total, "detail": supprime, "erreurs": erreurs}


# ---------------------------------------------------------------------------
# Purge rapports générés
# ---------------------------------------------------------------------------

RAPPORTS_DIR = Path(__file__).parent.parent.parent / "data" / "rapports"


@router.delete("/rapports")
async def purger_rapports():
    """Supprime tous les rapports générés (entrées BDD + fichiers PDF sur disque)."""
    supprime_db   = 0
    supprime_disk = 0
    erreurs: list[str] = []

    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT id, fichier_path FROM rapports WHERE boutique_id = ?", (BOUTIQUE_ID,)
        )
        for row in rows:
            fichier = row[1]
            if fichier:
                p = Path(fichier)
                try:
                    if p.exists():
                        p.unlink()
                        supprime_disk += 1
                except Exception as exc:  # noqa: BLE001
                    erreurs.append(f"{p.name} : {exc}")

        cur = await db.execute(
            "DELETE FROM rapports WHERE boutique_id = ?", (BOUTIQUE_ID,)
        )
        supprime_db = cur.rowcount
        await db.commit()

    return {
        "ok": True,
        "supprime_db": supprime_db,
        "supprime_disk": supprime_disk,
        "erreurs": erreurs,
    }


# ---------------------------------------------------------------------------
# Stats espace disque
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent.parent / "data"


@router.get("/stats-disque")
async def stats_disque():
    """Retourne les stats d'espace disque par dossier + infos disque total."""
    stats = {}

    if not DATA_DIR.exists():
        return {
            "dossiers": stats,
            "total_data_mo": 0,
            "disque_total_gb": 0,
            "disque_libre_gb": 0,
            "disque_utilise_pct": 0,
        }

    # Stats par dossier
    for subdir in DATA_DIR.iterdir():
        if subdir.is_dir():
            nom = subdir.name
            taille_bytes = 0
            nb_fichiers = 0

            try:
                for fichier in subdir.rglob("*"):
                    if fichier.is_file():
                        taille_bytes += fichier.stat().st_size
                        nb_fichiers += 1
            except Exception:  # noqa: BLE001
                pass

            stats[nom] = {
                "taille_mo": round(taille_bytes / (1024 * 1024), 2),
                "nb_fichiers": nb_fichiers,
            }

    total_data_mo = sum(s["taille_mo"] for s in stats.values())

    # Espace disque du système
    disque_total_gb = 0
    disque_libre_gb = 0
    disque_utilise_pct = 0

    if HAS_PSUTIL:
        try:
            # Utilise le répertoire parent du projet (la partition)
            usage = psutil.disk_usage(str(DATA_DIR.parent.parent))
            disque_total_gb = round(usage.total / (1024**3), 2)
            disque_libre_gb = round(usage.free / (1024**3), 2)
            disque_utilise_pct = usage.percent
        except Exception:  # noqa: BLE001
            pass

    return {
        "dossiers": stats,
        "total_mo": round(total_data_mo, 2),
        "total_data_mo": round(total_data_mo, 2),
        "disque_total_gb": disque_total_gb,
        "disque_libre_gb": disque_libre_gb,
        "disque_utilise_pct": disque_utilise_pct,
    }


@router.get("/stats-disque/{dossier}")
async def stats_disque_detail(dossier: str):
    """Retourne le détail des fichiers d'un dossier spécifique."""
    # Sécurité : évite les traversées de répertoire
    if "/" in dossier or "\\" in dossier or dossier == "..":
        raise HTTPException(400, "Dossier invalide")

    subdir = DATA_DIR / dossier
    if not subdir.exists() or not subdir.is_dir():
        raise HTTPException(404, "Dossier non trouvé")

    fichiers = []
    try:
        for fichier in sorted(subdir.rglob("*")):
            if fichier.is_file():
                taille_bytes = fichier.stat().st_size
                fichiers.append({
                    "chemin": str(fichier.relative_to(subdir)).replace("\\", "/"),
                    "taille_mo": round(taille_bytes / (1024 * 1024), 2),
                    "taille_ko": round(taille_bytes / 1024, 1),
                })
    except Exception:  # noqa: BLE001
        pass

    # Tri par taille décroissante
    fichiers.sort(key=lambda f: f["taille_mo"], reverse=True)
    total_mo = sum(f["taille_mo"] for f in fichiers)

    return {
        "dossier": dossier,
        "fichiers": fichiers,
        "total_mo": round(total_mo, 2),
        "nb_fichiers": len(fichiers),
    }


# ---------------------------------------------------------------------------
# Nettoyage photos orphelines
# ---------------------------------------------------------------------------

PHOTOS_DIR = Path(__file__).parent.parent.parent / "data" / "photos"


@router.get("/photos-orphelines")
async def lister_photos_orphelines():
    """Liste les fichiers photos sur disque qui ne sont plus référencés en base."""
    if not PHOTOS_DIR.exists():
        return {"orphelines": [], "total": 0}

    # Collecte tous les chemins photos en base
    async with get_db() as db:
        fichiers_en_base = set()
        for col_table in [
            ("receptions", "photo_bl_filename"),
            ("receptions", "proprete_photo_filename"),
            ("reception_bls_supplementaires", "photo_bl_filename"),
            ("ouvertures", "photo_filename"),
            ("fiches_incident", "signature_livreur_filename"),
            ("tache_validations", "photo_path"),
        ]:
            table, col = col_table
            try:
                rows = await db.execute_fetchall(
                    f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL AND {col} != ''",
                )
                for row in rows:
                    if row[0]:
                        fichiers_en_base.add(row[0])
            except Exception:  # noqa: BLE001
                pass

    # Parcoure le dossier et identifie les orphelines
    orphelines = []
    try:
        for photo in PHOTOS_DIR.rglob("*"):
            if photo.is_file():
                nom_photo = str(photo.relative_to(PHOTOS_DIR))
                # Normalise les chemins (forward slash)
                nom_normalise = nom_photo.replace("\\", "/")
                if nom_normalise not in fichiers_en_base:
                    orphelines.append({
                        "chemin": nom_normalise,
                        "taille_ko": photo.stat().st_size / 1024,
                    })
    except Exception:  # noqa: BLE001
        pass

    return {"orphelines": sorted(orphelines, key=lambda x: x["chemin"]), "total": len(orphelines)}


@router.delete("/photos-orphelines")
async def supprimer_photos_orphelines():
    """Supprime tous les fichiers photos orphelines du disque."""
    supprime = 0
    erreurs: list[str] = []

    if not PHOTOS_DIR.exists():
        return {"ok": True, "supprime": 0, "erreurs": []}

    async with get_db() as db:
        fichiers_en_base = set()
        for col_table in [
            ("receptions", "photo_bl_filename"),
            ("receptions", "proprete_photo_filename"),
            ("reception_bls_supplementaires", "photo_bl_filename"),
            ("ouvertures", "photo_filename"),
            ("fiches_incident", "signature_livreur_filename"),
            ("tache_validations", "photo_path"),
        ]:
            table, col = col_table
            try:
                rows = await db.execute_fetchall(
                    f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL AND {col} != ''",
                )
                for row in rows:
                    if row[0]:
                        fichiers_en_base.add(row[0])
            except Exception:  # noqa: BLE001
                pass

    # Supprime les orphelines
    try:
        for photo in PHOTOS_DIR.rglob("*"):
            if photo.is_file():
                nom_photo = str(photo.relative_to(PHOTOS_DIR)).replace("\\", "/")
                if nom_photo not in fichiers_en_base:
                    try:
                        photo.unlink()
                        supprime += 1
                    except Exception as exc:  # noqa: BLE001
                        erreurs.append(f"{nom_photo}: {exc}")
    except Exception as exc:  # noqa: BLE001
        erreurs.append(str(exc))

    return {"ok": True, "supprime": supprime, "erreurs": erreurs}


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


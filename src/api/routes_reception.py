"""
routes_reception.py — Module Contrôles Réception (refonte v2)

GET    /api/fournisseurs                          → liste
POST   /api/fournisseurs                          → ajouter
PUT    /api/fournisseurs/{id}                     → modifier

POST   /api/receptions                            → créer réception (multipart)
POST   /api/receptions/{id}/lignes                → ajouter ligne produit
PUT    /api/receptions/{id}/cloturer              → clôturer la fiche
GET    /api/receptions                            → historique (filtres)
GET    /api/receptions/textes-aide-visuel         → référentiel contrôle visuel
GET    /api/receptions/{id}                       → détail + lignes
GET    /api/receptions/{id}/photo-bl              → BL photo (FileResponse)
GET    /api/receptions/{id}/photo-proprete        → Photo NC propreté camion (FileResponse)
"""

import io
import logging
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from PIL import Image, ImageOps
from pydantic import BaseModel

from src.database import (
    get_db,
    get_fournisseurs, create_fournisseur, update_fournisseur,
    create_reception, add_reception_ligne, cloturer_reception,
    get_receptions, get_reception,
    get_non_conformites, create_non_conformite,
    generer_lot_interne, update_reception_ligne,
    add_reception_bl_supplementaire,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["reception"])

BASE_DIR   = Path(__file__).parent.parent.parent
PHOTOS_BL_DIR = BASE_DIR / "data" / "photos" / "bons_livraison"
PHOTOS_BL_DIR.mkdir(parents=True, exist_ok=True)
PHOTOS_PROPRETE_DIR = BASE_DIR / "data" / "photos" / "proprete_camion"
PHOTOS_PROPRETE_DIR.mkdir(parents=True, exist_ok=True)

MAX_SIDE     = 1280
JPEG_QUALITY = 80


# ---------------------------------------------------------------------------
# Compression photo (identique ouvertures)
# ---------------------------------------------------------------------------

def _compress_photo(raw_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(raw_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_SIDE:
        if w >= h:
            new_w, new_h = MAX_SIDE, int(h * MAX_SIDE / w)
        else:
            new_w, new_h = int(w * MAX_SIDE / h), MAX_SIDE
        img = img.resize((new_w, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Référentiel aide visuel
# ---------------------------------------------------------------------------

TEXTES_AIDE_VISUEL = {
    "Boeuf": {
        "couleur":      {"normal": "Rouge vif",                  "anomalies": ["Brunâtre", "Grisâtre", "Verdâtre", "Taches noires"]},
        "consistance":  {"normal": "Ferme, bonne tenue",         "anomalies": ["Molle", "Visqueuse", "Collante", "Déchirée"]},
        "exsudat":      {"normal": "Poche ferme, peu de liquide","anomalies": ["Exsudation excessive", "Liquide laiteux ou trouble"]},
        "odeur":        {"normal": "Acidulée, fruitée",          "anomalies": ["Ammoniacale", "Putride", "Soufrée", "Acide fort"]},
        "ph":           {"normal": "Entre 5.5 et 5.7",           "anomalies": ["< 5.4 : trop acide (stress)", "> 5.8 : début d'altération"]},
    },
    "Veau": {
        "couleur":      {"normal": "Rose pâle à rose vif",       "anomalies": ["Grisâtre", "Brunâtre", "Verdâtre"]},
        "consistance":  {"normal": "Ferme, fine texture",        "anomalies": ["Molle", "Visqueuse", "Déchirée"]},
        "exsudat":      {"normal": "Poche ferme, peu de liquide","anomalies": ["Exsudation excessive", "Liquide laiteux"]},
        "odeur":        {"normal": "Douce, légèrement lactique", "anomalies": ["Ammoniaque", "Putride", "Acide fort"]},
        "ph":           {"normal": "Entre 5.5 et 5.7",           "anomalies": ["< 5.4 : trop acide", "> 5.8 : début d'altération"]},
    },
    "Porc": {
        "couleur":      {"normal": "Rose pâle",                  "anomalies": ["Grisâtre", "Brunâtre", "Pâle excessif (PSE)"]},
        "consistance":  {"normal": "Ferme, bonne tenue",         "anomalies": ["Molle (PSE)", "Aqueuse", "Collante"]},
        "exsudat":      {"normal": "Poche ferme, peu de liquide","anomalies": ["Exsudation excessive (PSE)", "Liquide trouble"]},
        "odeur":        {"normal": "Neutre, légèrement sucrée",  "anomalies": ["Rance", "Putride", "Soufrée"]},
        "ph":           {"normal": "Entre 5.5 et 5.7",           "anomalies": ["< 5.4 : viande PSE", "> 6.0 : viande DFD (sombre, dure)"]},
    },
    "Agneau": {
        "couleur":      {"normal": "Rouge rosé",                 "anomalies": ["Brunâtre", "Grisâtre", "Décoloré"]},
        "consistance":  {"normal": "Ferme, légèrement persillée","anomalies": ["Molle", "Collante"]},
        "exsudat":      {"normal": "Peu de liquide",             "anomalies": ["Exsudation excessive", "Liquide trouble"]},
        "odeur":        {"normal": "Caractéristique, légèrement sucrée","anomalies": ["Rance", "Putride", "Caprine forte"]},
        "ph":           {"normal": "Entre 5.5 et 5.7",           "anomalies": ["< 5.4 : trop acide", "> 5.8 : altération"]},
    },
    "Volaille": {
        "couleur":      {"normal": "Chair blanche à jaune pâle", "anomalies": ["Grisâtre", "Verdâtre", "Taches violacées"]},
        "consistance":  {"normal": "Ferme, élastique",           "anomalies": ["Molle", "Visqueuse", "Aqueuse"]},
        "exsudat":      {"normal": "Peu ou pas de liquide",      "anomalies": ["Exsudation abondante", "Liquide rosé trouble"]},
        "odeur":        {"normal": "Neutre, légèrement animale", "anomalies": ["Acide", "Putride", "Soufrée"]},
        "ph":           {"normal": "Entre 5.5 et 5.7",           "anomalies": ["< 5.4 : trop acide", "> 5.8 : altération"]},
    },
    "Gibier": {
        "couleur":      {"normal": "Rouge foncé à bordeaux",     "anomalies": ["Noirâtre", "Verdâtre", "Grisâtre"]},
        "consistance":  {"normal": "Ferme, dense",               "anomalies": ["Molle", "Collante"]},
        "exsudat":      {"normal": "Peu de liquide",             "anomalies": ["Exsudation excessive", "Liquide trouble"]},
        "odeur":        {"normal": "Caractéristique gibier, sauvage", "anomalies": ["Putride", "Ammoniaque forte"]},
        "ph":           {"normal": "Entre 5.5 et 5.7",           "anomalies": ["< 5.4 : trop acide", "> 5.8 : altération"]},
    },
    "Cheval": {
        "couleur":      {"normal": "Rouge foncé",                "anomalies": ["Brunâtre", "Grisâtre", "Noirâtre"]},
        "consistance":  {"normal": "Ferme, dense",               "anomalies": ["Molle", "Collante"]},
        "exsudat":      {"normal": "Peu de liquide",             "anomalies": ["Exsudation excessive"]},
        "odeur":        {"normal": "Caractéristique, douce",     "anomalies": ["Rance", "Putride"]},
        "ph":           {"normal": "Entre 5.5 et 5.7",           "anomalies": ["< 5.4 : trop acide", "> 5.8 : altération"]},
    },
}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class FournisseurCreate(BaseModel):
    nom: str


class FournisseurUpdate(BaseModel):
    nom: Optional[str] = None
    actif: Optional[bool] = None


class LigneCreate(BaseModel):
    produit_id: int
    fournisseur_id: Optional[int] = None
    fournisseur_nom: Optional[str] = None
    numero_lot: Optional[str] = None
    lot_interne: int = 0
    dlc: Optional[str] = None
    dluo: Optional[str] = None
    origine: str = "France"
    poids_kg: Optional[float] = None
    temperature_reception: Optional[float] = None
    temperature_coeur: Optional[float] = None
    couleur_conforme: int = 1
    couleur_observation: Optional[str] = None
    consistance_conforme: int = 1
    consistance_observation: Optional[str] = None
    exsudat_conforme: int = 1
    exsudat_observation: Optional[str] = None
    odeur_conforme: int = 1
    odeur_observation: Optional[str] = None
    ph_valeur: Optional[float] = None


class LigneUpdate(BaseModel):
    produit_id: Optional[int] = None
    fournisseur_id: Optional[int] = None
    fournisseur_nom: Optional[str] = None
    numero_lot: Optional[str] = None
    lot_interne: int = 0
    dlc: Optional[str] = None
    dluo: Optional[str] = None
    origine: Optional[str] = None
    poids_kg: Optional[float] = None
    temperature_reception: Optional[float] = None
    temperature_coeur: Optional[float] = None
    couleur_conforme: int = 1
    couleur_observation: Optional[str] = None
    consistance_conforme: int = 1
    consistance_observation: Optional[str] = None
    exsudat_conforme: int = 1
    exsudat_observation: Optional[str] = None
    odeur_conforme: int = 1
    odeur_observation: Optional[str] = None
    ph_valeur: Optional[float] = None


class CloturerBody(BaseModel):
    livraison_refusee: bool = False
    information_ddpp: bool = False
    commentaire_nc: Optional[str] = None
    coeur_conformes: list[int] = []              # IDs des lignes conformes après contrôle à cœur
    coeur_temperatures: Dict[int, float] = {}    # {ligne_id: temp_coeur} pour persistance


class NonConformiteCreate(BaseModel):
    reception_id: Optional[int] = None
    reception_ligne_id: Optional[int] = None
    operateur: str
    date_livraison: Optional[str] = None
    fournisseur_nom: Optional[str] = None
    produits: Optional[str] = None
    date_fabrication: Optional[str] = None
    dlc: Optional[str] = None
    nombre_barquettes: Optional[int] = None
    nature_nc: Optional[list[str]] = None
    commentaires: Optional[str] = None
    refuse_livraison: bool = False
    nc_apres_livraison: bool = False
    info_ddpp: bool = False


# ---------------------------------------------------------------------------
# Fournisseurs
# ---------------------------------------------------------------------------

@router.get("/fournisseurs")
async def lister_fournisseurs():
    async with get_db() as db:
        return await get_fournisseurs(db, boutique_id=1)


@router.post("/fournisseurs", status_code=201)
async def ajouter_fournisseur(body: FournisseurCreate):
    async with get_db() as db:
        fid = await create_fournisseur(db, {"boutique_id": 1, "nom": body.nom})
        cursor = await db.execute("SELECT * FROM fournisseurs WHERE id = ?", (fid,))
        row = await cursor.fetchone()
    return dict(row) if row else {"id": fid}


@router.put("/fournisseurs/{fournisseur_id}")
async def modifier_fournisseur(fournisseur_id: int, body: FournisseurUpdate):
    async with get_db() as db:
        ok = await update_fournisseur(db, fournisseur_id, body.model_dump(exclude_none=True))
    if not ok:
        raise HTTPException(404, "Fournisseur non trouvé")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Réceptions
# ---------------------------------------------------------------------------

@router.post("/receptions", status_code=201)
async def creer_reception(
    personnel_id:            int            = Form(...),
    heure_reception:         str            = Form(...),
    date_reception:          Optional[str]  = Form(None),
    temperature_camion:      Optional[float]= Form(None),
    proprete_camion:         str            = Form("satisfaisant"),
    fournisseur_principal_id: Optional[int] = Form(None),
    fournisseur_nom:         Optional[str]  = Form(None),
    commentaire:             Optional[str]  = Form(None),
    photo_bl:                Optional[UploadFile] = File(None),
    photo_proprete:          Optional[UploadFile] = File(None),
):
    data = {
        "personnel_id":            personnel_id,
        "date_reception":          date_reception,
        "heure_reception":         heure_reception,
        "temperature_camion":      temperature_camion,
        "proprete_camion":         proprete_camion,
        "fournisseur_principal_id": fournisseur_principal_id,
        "fournisseur_nom":         fournisseur_nom,
        "commentaire":             commentaire,
    }

    async with get_db() as db:
        # Vérifier personnel
        cur = await db.execute("SELECT id FROM personnel WHERE id = ?", (personnel_id,))
        if not await cur.fetchone():
            raise HTTPException(400, "personnel_id introuvable")

        rid = await create_reception(db, data)

        # Photo BL optionnelle
        if photo_bl and photo_bl.filename:
            from datetime import datetime, timezone
            raw = await photo_bl.read()
            jpeg = _compress_photo(raw)
            now_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            filename = f"BL-{now_str}-{rid}.jpg"
            (PHOTOS_BL_DIR / filename).write_bytes(jpeg)
            await db.execute(
                "UPDATE receptions SET photo_bl_filename = ? WHERE id = ?",
                (filename, rid),
            )
            await db.commit()

        # Photo NC propreté camion (optionnelle, uniquement si proprete=non_satisfaisant)
        if photo_proprete and photo_proprete.filename and proprete_camion == "non_satisfaisant":
            from datetime import datetime, timezone
            raw = await photo_proprete.read()
            jpeg = _compress_photo(raw)
            now_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            filename = f"PROPRETE-{now_str}-{rid}.jpg"
            (PHOTOS_PROPRETE_DIR / filename).write_bytes(jpeg)
            await db.execute(
                "UPDATE receptions SET proprete_photo_filename = ? WHERE id = ?",
                (filename, rid),
            )
            await db.commit()

        cur2 = await db.execute(
            "SELECT * FROM receptions WHERE id = ?", (rid,)
        )
        row = await cur2.fetchone()
    return dict(row)


@router.post("/receptions/{reception_id}/lignes", status_code=201)
async def ajouter_ligne(reception_id: int, body: LigneCreate):
    async with get_db() as db:
        cur = await db.execute(
            "SELECT id FROM receptions WHERE id = ?", (reception_id,)
        )
        if not await cur.fetchone():
            raise HTTPException(404, "Réception non trouvée")

        cur2 = await db.execute(
            "SELECT id FROM produits WHERE id = ?", (body.produit_id,)
        )
        if not await cur2.fetchone():
            raise HTTPException(400, "produit_id introuvable")

        lid = await add_reception_ligne(db, reception_id, body.model_dump())

        cur3 = await db.execute(
            "SELECT * FROM reception_lignes WHERE id = ?", (lid,)
        )
        row = await cur3.fetchone()
    return dict(row)


@router.get("/receptions/{reception_id}/lot-interne")
async def get_lot_interne_par_code(reception_id: int, code_unique: str = Query(...)):
    """Génère un numéro de lot interne à partir du code_unique produit."""
    async with get_db() as db:
        lot = await generer_lot_interne(db, code_unique)
    return {"lot_interne": lot}


@router.get("/receptions/{reception_id}/lignes/{ligne_id}/lot-interne")
async def get_lot_interne(reception_id: int, ligne_id: int):
    """Génère un numéro de lot interne unique pour la ligne donnée."""
    async with get_db() as db:
        cur = await db.execute(
            """
            SELECT p.code_unique FROM reception_lignes rl
            JOIN produits p ON p.id = rl.produit_id
            WHERE rl.id = ? AND rl.reception_id = ?
            """,
            (ligne_id, reception_id),
        )
        row = await cur.fetchone()
    if not row or not row["code_unique"]:
        raise HTTPException(400, "Ligne ou code produit introuvable")
    async with get_db() as db:
        lot = await generer_lot_interne(db, row["code_unique"])
    return {"lot_interne": lot}


@router.put("/receptions/{reception_id}/lignes/{ligne_id}")
async def modifier_ligne(reception_id: int, ligne_id: int, body: LigneUpdate):
    async with get_db() as db:
        cur = await db.execute(
            "SELECT id FROM receptions WHERE id = ?", (reception_id,)
        )
        if not await cur.fetchone():
            raise HTTPException(404, "Réception non trouvée")

        updated = await update_reception_ligne(db, ligne_id, body.model_dump(exclude_none=False))
    if not updated:
        raise HTTPException(404, "Ligne non trouvée")
    return updated


@router.put("/receptions/{reception_id}/cloturer")
async def cloturer(reception_id: int, body: CloturerBody = CloturerBody()):
    async with get_db() as db:
        cur = await db.execute(
            "SELECT id FROM receptions WHERE id = ?", (reception_id,)
        )
        if not await cur.fetchone():
            raise HTTPException(404, "Réception non trouvée")

        reception = await cloturer_reception(
            db, reception_id,
            livraison_refusee=body.livraison_refusee,
            information_ddpp=body.information_ddpp,
            commentaire_nc=body.commentaire_nc,
            coeur_conformes=body.coeur_conformes,
            coeur_temperatures=body.coeur_temperatures,
        )
    return reception


# IMPORTANT : cette route doit être AVANT /receptions/{id}
@router.get("/receptions/textes-aide-visuel")
async def textes_aide_visuel():
    """Référentiel des critères de contrôle visuel par espèce."""
    return TEXTES_AIDE_VISUEL


@router.get("/receptions")
async def historique_receptions(
    date_debut:    Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_fin:      Optional[str] = Query(None, description="YYYY-MM-DD"),
    fournisseur_id: Optional[int] = Query(None),
    fournisseur_nom: Optional[str] = Query(None, description="Filtre par nom de fournisseur (exact, insensible casse/accents)"),
    q:             Optional[str] = Query(None, description="Recherche produit ou N° de lot dans les lignes"),
    limit:         int            = Query(50, ge=1, le=500),
    offset:        int            = Query(0, ge=0),
):
    async with get_db() as db:
        return await get_receptions(
            db,
            date_debut=date_debut,
            date_fin=date_fin,
            fournisseur_id=fournisseur_id,
            fournisseur_nom=fournisseur_nom,
            q=q,
            limit=limit,
            offset=offset,
        )


@router.get("/receptions/fournisseurs-suggestions")
async def suggestions_fournisseurs_receptions(
    q_produit: Optional[str] = Query(None, description="Filtre les fournisseurs aux livraisons d'un produit/lot précis"),
    limit: int = Query(200, ge=1, le=500),
):
    """
    Liste des fournisseurs vus en réception (dérivée des données réelles, pas de la table fournisseurs).
    Si `q_produit` est fourni, ne renvoie que les fournisseurs ayant livré ce produit/lot.
    Capture les fournisseurs renseignés en texte libre ET ceux liés par FK.
    """
    import unicodedata

    _C = "COALESCE(fl.nom, fr.nom, rl.fournisseur_nom, r.fournisseur_nom)"

    if q_produit and q_produit.strip():
        like = f"%{q_produit.strip()}%"
        produits_join = "LEFT JOIN produits p ON p.id = rl.produit_id"
        where = (
            f"(p.nom LIKE ? COLLATE NOCASE OR rl.numero_lot LIKE ? COLLATE NOCASE)"
            f" AND {_C} IS NOT NULL AND TRIM({_C}) <> ''"
        )
        params: list = [like, like]
    else:
        produits_join = ""
        where = f"{_C} IS NOT NULL AND TRIM({_C}) <> ''"
        params = []

    sql = f"""
        SELECT
            COALESCE(fl.id, fr.id) AS id,
            {_C}                   AS nom,
            MAX(r.date_reception)  AS derniere_reception
        FROM reception_lignes rl
        JOIN receptions   r  ON r.id  = rl.reception_id
        {produits_join}
        LEFT JOIN fournisseurs fl ON fl.id = rl.fournisseur_id
        LEFT JOIN fournisseurs fr ON fr.id = r.fournisseur_principal_id
        WHERE {where}
        GROUP BY COALESCE(fl.id, fr.id), {_C}
        ORDER BY derniere_reception DESC
        LIMIT ?
    """

    async with get_db() as db:
        cursor = await db.execute(sql, params + [limit])
        rows = await cursor.fetchall()

    def _norm(s: str) -> str:
        s = (s or "").strip().lower()
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

    vus: dict[str, dict] = {}
    for row in rows:
        d = dict(row)
        k = _norm(d["nom"])
        if not k:
            continue
        existant = vus.get(k)
        if existant is None:
            vus[k] = d
        elif existant.get("id") is None and d.get("id") is not None:
            vus[k] = d

    return list(vus.values())


@router.get("/receptions/produits-suggestions")
async def suggestions_produits_receptions(
    q: Optional[str] = Query(None, description="Filtre nom produit ou N° de lot"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Auto-complétion produits/lots vus en réception.
    Retourne, pour chaque produit ayant au moins une ligne de réception correspondant à `q` :
        - produit_id, nom, espece
        - fournisseurs : liste distincte des fournisseurs ayant livré ce produit
        - dernier_lot, derniere_dlc, derniere_reception
    Trié par dernière réception (plus récent en premier).
    Si `q` est vide → tous les produits jamais réceptionnés (limité à `limit`).
    """
    like = f"%{q.strip()}%" if q else None
    where_q = ""
    params: list = []
    if like:
        where_q = "AND (p.nom LIKE ? COLLATE NOCASE OR rl.numero_lot LIKE ? COLLATE NOCASE)"
        params.extend([like, like])

    async with get_db() as db:
        cursor = await db.execute(
            f"""
            SELECT
                p.id           AS produit_id,
                p.nom          AS nom,
                p.espece       AS espece,
                -- Fournisseur de la ligne si défini, sinon de la réception parente
                COALESCE(fl.nom, fr.nom, rl.fournisseur_nom, r.fournisseur_nom) AS fournisseur_nom,
                rl.numero_lot  AS numero_lot,
                rl.dlc         AS dlc,
                r.date_reception AS date_reception
            FROM reception_lignes rl
            JOIN receptions   r ON r.id = rl.reception_id
            JOIN produits     p ON p.id = rl.produit_id
            LEFT JOIN fournisseurs fl ON fl.id = rl.fournisseur_id
            LEFT JOIN fournisseurs fr ON fr.id = r.fournisseur_principal_id
            WHERE 1=1
              {where_q}
            ORDER BY r.date_reception DESC, rl.id DESC
            """,
            tuple(params),
        )
        rows = await cursor.fetchall()

    par_produit: dict[int, dict] = {}
    for row in rows:
        d = dict(row)
        pid = d["produit_id"]
        entry = par_produit.get(pid)
        if entry is None:
            entry = {
                "produit_id": pid,
                "nom": d["nom"],
                "espece": d["espece"],
                "fournisseurs": [],
                "dernier_lot": d["numero_lot"],
                "derniere_dlc": d["dlc"],
                "derniere_reception": d["date_reception"],
            }
            par_produit[pid] = entry
        f_nom = (d["fournisseur_nom"] or "").strip()
        if f_nom and f_nom not in entry["fournisseurs"]:
            entry["fournisseurs"].append(f_nom)

    # Tri global par date de dernière réception (DESC), produits sans date à la fin
    out = sorted(
        par_produit.values(),
        key=lambda e: (e["derniere_reception"] is None, e["derniere_reception"] or ""),
    )
    out.reverse()
    return out[:limit]


@router.get("/receptions/{reception_id}")
async def detail_reception(reception_id: int):
    async with get_db() as db:
        rec = await get_reception(db, reception_id)
    if not rec:
        raise HTTPException(404, "Réception non trouvée")
    return rec


@router.get("/receptions/{reception_id}/photo-bl")
async def get_photo_bl(reception_id: int):
    async with get_db() as db:
        cur = await db.execute(
            "SELECT photo_bl_filename FROM receptions WHERE id = ?", (reception_id,)
        )
        row = await cur.fetchone()
    if not row or not row["photo_bl_filename"]:
        raise HTTPException(404, "Pas de photo BL pour cette réception")
    filepath = PHOTOS_BL_DIR / row["photo_bl_filename"]
    if not filepath.exists():
        raise HTTPException(404, "Fichier photo introuvable")
    return FileResponse(str(filepath), media_type="image/jpeg")


@router.get("/receptions/{reception_id}/photo-proprete")
async def get_photo_proprete(reception_id: int):
    async with get_db() as db:
        cur = await db.execute(
            "SELECT proprete_photo_filename FROM receptions WHERE id = ?", (reception_id,)
        )
        row = await cur.fetchone()
    if not row or not row["proprete_photo_filename"]:
        raise HTTPException(404, "Pas de photo de propreté pour cette réception")
    filepath = PHOTOS_PROPRETE_DIR / row["proprete_photo_filename"]
    if not filepath.exists():
        raise HTTPException(404, "Fichier photo introuvable")
    return FileResponse(str(filepath), media_type="image/jpeg")


# ---------------------------------------------------------------------------
# BLs supplémentaires (refus livraison multi-fournisseur)
# ---------------------------------------------------------------------------

@router.post("/receptions/{reception_id}/bls-supplementaires", status_code=201)
async def ajouter_bl_supplementaire(
    reception_id:    int,
    fournisseur_id:  Optional[int] = Form(None),
    fournisseur_nom: Optional[str] = Form(None),
    photo:           Optional[UploadFile] = File(None),
):
    """Ajoute un BL supplémentaire à une réception (refus livraison multi-fournisseur).
    1 BL par fournisseur. Le 1er BL/fournisseur reste sur la table `receptions`.
    """
    if not fournisseur_id and not (fournisseur_nom and fournisseur_nom.strip()):
        raise HTTPException(400, "fournisseur_id ou fournisseur_nom requis")

    photo_filename = None
    async with get_db() as db:
        cur = await db.execute("SELECT id FROM receptions WHERE id = ?", (reception_id,))
        if not await cur.fetchone():
            raise HTTPException(404, "Réception non trouvée")

        if photo and photo.filename:
            from datetime import datetime, timezone
            raw = await photo.read()
            jpeg = _compress_photo(raw)
            now_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            photo_filename = f"BL-{now_str}-{reception_id}-supp.jpg"
            (PHOTOS_BL_DIR / photo_filename).write_bytes(jpeg)

        bl_id = await add_reception_bl_supplementaire(db, reception_id, {
            "fournisseur_id":    fournisseur_id,
            "fournisseur_nom":   (fournisseur_nom or "").strip() or None,
            "photo_bl_filename": photo_filename,
        })
    return {"id": bl_id, "photo_bl_filename": photo_filename}


@router.get("/receptions/{reception_id}/bls-supplementaires/{bl_id}/photo")
async def get_photo_bl_supplementaire(reception_id: int, bl_id: int):
    async with get_db() as db:
        cur = await db.execute(
            """
            SELECT photo_bl_filename FROM reception_bls_supplementaires
            WHERE id = ? AND reception_id = ?
            """,
            (bl_id, reception_id),
        )
        row = await cur.fetchone()
    if not row or not row["photo_bl_filename"]:
        raise HTTPException(404, "Pas de photo pour ce BL")
    filepath = PHOTOS_BL_DIR / row["photo_bl_filename"]
    if not filepath.exists():
        raise HTTPException(404, "Fichier photo introuvable")
    return FileResponse(str(filepath), media_type="image/jpeg")


# ---------------------------------------------------------------------------
# Non-conformités (inchangé)
# ---------------------------------------------------------------------------

@router.post("/non-conformites", status_code=201)
async def declarer_non_conformite(body: NonConformiteCreate):
    async with get_db() as db:
        nc_id = await create_non_conformite(
            db, {"boutique_id": 1, **body.model_dump()}
        )
    return {"id": nc_id}


@router.get("/non-conformites")
async def historique_non_conformites(
    reception_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    async with get_db() as db:
        if reception_id:
            # Filtrer par reception_id
            cursor = await db.execute(
                """
                SELECT * FROM non_conformites_fournisseur
                WHERE reception_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (reception_id, limit),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
        else:
            return await get_non_conformites(db, 1, limit=limit)

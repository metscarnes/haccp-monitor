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
"""

import io
import logging
from pathlib import Path
from typing import Optional

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
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["reception"])

BASE_DIR   = Path(__file__).parent.parent.parent
PHOTOS_BL_DIR = BASE_DIR / "data" / "photos" / "bons_livraison"
PHOTOS_BL_DIR.mkdir(parents=True, exist_ok=True)

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
    coeur_conformes: list[int] = []  # IDs des lignes conformes après contrôle à cœur


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
    commentaire:             Optional[str]  = Form(None),
    photo_bl:                Optional[UploadFile] = File(None),
):
    data = {
        "personnel_id":            personnel_id,
        "date_reception":          date_reception,
        "heure_reception":         heure_reception,
        "temperature_camion":      temperature_camion,
        "proprete_camion":         proprete_camion,
        "fournisseur_principal_id": fournisseur_principal_id,
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
    limit:         int            = Query(50, ge=1, le=500),
    offset:        int            = Query(0, ge=0),
):
    async with get_db() as db:
        return await get_receptions(
            db,
            date_debut=date_debut,
            date_fin=date_fin,
            fournisseur_id=fournisseur_id,
            limit=limit,
            offset=offset,
        )


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
async def historique_non_conformites(limit: int = 50):
    async with get_db() as db:
        return await get_non_conformites(db, 1, limit=limit)

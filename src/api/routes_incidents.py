"""
routes_incidents.py — Fiches incident PCR01 + Étiquette À REPRENDRE

POST   /api/fiches-incident                   → créer une fiche
GET    /api/fiches-incident                   → liste (filtres : statut, fournisseur_id, dates)
GET    /api/fiches-incident/{id}              → détail
PUT    /api/fiches-incident/{id}              → mise à jour partielle
GET    /api/fiches-incident/{id}/signature    → PNG signature livreur

POST   /api/impression/etiquette-reprise      → imprimer étiquette "À RETOURNER"
"""

import io
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.database import (
    get_db,
    create_fiche_incident,
    get_fiches_incident,
    get_fiche_incident,
    update_fiche_incident,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["incidents"])

BASE_DIR  = Path(__file__).parent.parent.parent
SIGS_DIR  = BASE_DIR / "data" / "photos" / "signatures"
SIGS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class FicheUpdate(BaseModel):
    action_corrective: Optional[str] = None
    suivi:             Optional[str] = None
    statut:            Optional[str] = None
    cloturee_par:      Optional[int] = None
    etiquette_reprise_imprimee: Optional[int] = None


class EtiquetteRepriseBody(BaseModel):
    produit_nom:      str
    fournisseur_nom:  str
    motif:            str
    operateur_prenom: str
    date_refus:       str   # YYYY-MM-DD


# ---------------------------------------------------------------------------
# POST /api/fiches-incident
# ---------------------------------------------------------------------------

@router.post("/fiches-incident", status_code=201)
async def creer_fiche(
    reception_id:               int           = Form(...),
    fournisseur_id:             int           = Form(...),
    produit_id:                 int           = Form(...),
    nature_probleme:            str           = Form(...),
    action_immediate:           str           = Form(...),
    livreur_present:            int           = Form(0),
    reception_ligne_id:         Optional[int] = Form(None),
    numero_lot:                 Optional[str] = Form(None),
    description:                Optional[str] = Form(None),
    action_corrective:          Optional[str] = Form(None),
    suivi:                      Optional[str] = Form(None),
    signature_livreur:          Optional[UploadFile] = File(None),
):
    now = datetime.now(timezone.utc)

    data = {
        "reception_id":      reception_id,
        "reception_ligne_id": reception_ligne_id,
        "heure_incident":    now.strftime("%H:%M"),
        "fournisseur_id":    fournisseur_id,
        "produit_id":        produit_id,
        "numero_lot":        numero_lot,
        "nature_probleme":   nature_probleme,
        "description":       description,
        "action_immediate":  action_immediate,
        "livreur_present":   livreur_present,
        "action_corrective": action_corrective,
        "suivi":             suivi,
    }

    async with get_db() as db:
        fiche_id = await create_fiche_incident(db, data)

        # Sauvegarder la signature si présente
        if signature_livreur and signature_livreur.filename:
            raw = await signature_livreur.read()
            ts = now.strftime("%Y%m%d-%H%M%S")
            sig_filename = f"SIG-{ts}-{fiche_id}.png"
            (SIGS_DIR / sig_filename).write_bytes(raw)
            await db.execute(
                "UPDATE fiches_incident SET signature_livreur_filename = ? WHERE id = ?",
                (sig_filename, fiche_id),
            )
            await db.commit()

        fiche = await get_fiche_incident(db, fiche_id)

    return fiche


# ---------------------------------------------------------------------------
# GET /api/fiches-incident
# ---------------------------------------------------------------------------

@router.get("/fiches-incident")
async def lister_fiches(
    statut:        Optional[str] = Query(None),
    fournisseur_id: Optional[int] = Query(None),
    date_debut:    Optional[str] = Query(None),
    date_fin:      Optional[str] = Query(None),
    limit:         int           = Query(50, ge=1, le=500),
):
    async with get_db() as db:
        return await get_fiches_incident(
            db,
            statut=statut,
            fournisseur_id=fournisseur_id,
            date_debut=date_debut,
            date_fin=date_fin,
            limit=limit,
        )


# ---------------------------------------------------------------------------
# GET /api/fiches-incident/{id}
# ---------------------------------------------------------------------------

@router.get("/fiches-incident/{fiche_id}")
async def detail_fiche(fiche_id: int):
    async with get_db() as db:
        fiche = await get_fiche_incident(db, fiche_id)
    if not fiche:
        raise HTTPException(404, "Fiche incident non trouvée")
    return fiche


# ---------------------------------------------------------------------------
# PUT /api/fiches-incident/{id}
# ---------------------------------------------------------------------------

@router.put("/fiches-incident/{fiche_id}")
async def modifier_fiche(fiche_id: int, body: FicheUpdate):
    async with get_db() as db:
        ok = await update_fiche_incident(db, fiche_id, body.model_dump(exclude_none=True))
        if not ok:
            raise HTTPException(404, "Fiche non trouvée ou aucun champ à modifier")
        fiche = await get_fiche_incident(db, fiche_id)
    return fiche


# ---------------------------------------------------------------------------
# GET /api/fiches-incident/{id}/signature
# ---------------------------------------------------------------------------

@router.get("/fiches-incident/{fiche_id}/signature")
async def get_signature(fiche_id: int):
    async with get_db() as db:
        fiche = await get_fiche_incident(db, fiche_id)
    if not fiche or not fiche.get("signature_livreur_filename"):
        raise HTTPException(404, "Pas de signature pour cette fiche")
    path = SIGS_DIR / fiche["signature_livreur_filename"]
    if not path.exists():
        raise HTTPException(404, "Fichier signature introuvable")
    return FileResponse(str(path), media_type="image/png")


# ---------------------------------------------------------------------------
# POST /api/impression/etiquette-reprise
# ---------------------------------------------------------------------------

@router.post("/impression/etiquette-reprise")
async def imprimer_etiquette_reprise(body: EtiquetteRepriseBody):
    """
    Génère et imprime une étiquette Brother QL "⚠️ À RETOURNER ⚠️".
    Retourne {"imprime": bool, "message": str}.
    """
    try:
        from datetime import date
        date_affiche = body.date_refus
        try:
            date_affiche = date.fromisoformat(body.date_refus).strftime("%d/%m/%Y")
        except Exception:
            pass

        result = _generer_et_imprimer_reprise({
            "produit_nom":      body.produit_nom,
            "fournisseur_nom":  body.fournisseur_nom,
            "motif":            body.motif,
            "operateur_prenom": body.operateur_prenom,
            "date_refus":       date_affiche,
        })
        return result
    except Exception as e:
        logger.error("Erreur impression reprise : %s", e)
        return {"imprime": False, "message": str(e)}


def _generer_et_imprimer_reprise(data: dict) -> dict:
    """Génère l'image étiquette reprise et tente l'impression."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return {"imprime": False, "message": "Pillow non installé"}

    W, H = 708, 472
    img  = Image.new("RGB", (W, H), color="white")
    draw = ImageDraw.Draw(img)

    try:
        from PIL import ImageFont
        font_xl   = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
        font_bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        font_norm = ImageFont.truetype("DejaVuSans.ttf", 24)
    except (IOError, OSError):
        font_xl   = ImageFont.load_default()
        font_bold = font_xl
        font_norm = font_xl

    mx, y, lh = 16, 14, 50

    # Titre
    titre = "\u26a0  \u00c0 RETOURNER  \u26a0"
    bbox  = draw.textbbox((0, 0), titre, font=font_xl)
    tw    = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y), titre, font=font_xl, fill="black")
    y += 70

    draw.line([(mx, y), (W - mx, y)], fill="black", width=3)
    y += 10

    lines = [
        ("Produit",     data["produit_nom"],      font_bold),
        ("Fournisseur", data["fournisseur_nom"],   font_norm),
        ("Motif",       data["motif"],             font_norm),
        ("Refusé par",  data["operateur_prenom"],  font_norm),
        ("Date",        data["date_refus"],         font_norm),
    ]
    for label, valeur, font in lines:
        draw.text((mx, y), f"{label} :", font=font_norm, fill="#555")
        draw.text((mx + 180, y), valeur, font=font, fill="black")
        y += lh

    # Impression
    try:
        from src.printing.brother_ql_driver import PRINTER_IDENTIFIER, LABEL_TYPE
        from brother_ql.conversion import convert
        from brother_ql.backends.helpers import send
        from brother_ql.raster import BrotherQLRaster

        qlr = BrotherQLRaster(PRINTER_IDENTIFIER)
        instructions = convert(
            qlr=qlr, images=[img], label=LABEL_TYPE,
            rotate="auto", threshold=70, dither=False,
            compress=False, red=False, dpi_600=False, hq=True, cut=True,
        )
        send(instructions=instructions, printer_identifier=PRINTER_IDENTIFIER,
             backend_identifier="pyusb", blocking=True)
        logger.info("Étiquette reprise imprimée : %s", data["produit_nom"])
        return {"imprime": True, "message": "Étiquette imprimée"}
    except ImportError:
        logger.warning("brother_ql non installé — impression simulée")
        return {"imprime": False, "message": "Imprimante non disponible (brother_ql absent)"}
    except Exception as e:
        logger.error("Erreur impression reprise : %s", e)
        return {"imprime": False, "message": str(e)}

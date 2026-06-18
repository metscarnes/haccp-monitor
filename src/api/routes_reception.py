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
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from PIL import Image, ImageOps
from pydantic import BaseModel

from src.database import (
    get_db,
    get_fournisseurs, create_fournisseur, update_fournisseur,
    create_reception, add_reception_ligne, cloturer_reception,
    get_receptions, get_reception, get_reception_en_cours,
    get_non_conformites, create_non_conformite,
    generer_lot_interne, format_lot_interne_bl, update_reception_ligne,
    update_reception_temperature_camion,
    add_reception_bl_supplementaire,
    supprimer_reception,
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


def _est_pdf(raw_bytes: bytes, filename: Optional[str]) -> bool:
    """Détecte un PDF par sa signature (%PDF) ou son extension."""
    if raw_bytes[:5] == b"%PDF-":
        return True
    return bool(filename) and filename.lower().endswith(".pdf")


def _fichier_bl_vers_jpegs(raw_bytes: bytes, filename: Optional[str]) -> List[bytes]:
    """Transforme un fichier BL (image OU PDF) en une liste de JPEG compressés,
    un par page. Un fichier image → 1 JPEG ; un PDF → 1 JPEG par page.
    Lève ValueError si le contenu est illisible.
    """
    if _est_pdf(raw_bytes, filename):
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ValueError("Lecture des PDF indisponible (PyMuPDF non installé).")
        jpegs: List[bytes] = []
        try:
            doc = fitz.open(stream=raw_bytes, filetype="pdf")
        except Exception as e:
            raise ValueError(f"PDF illisible : {e}")
        try:
            # Rendu à ~150 dpi (zoom 2) : suffisant pour l'OCR, taille raisonnable.
            mat = fitz.Matrix(2, 2)
            for page in doc:
                pix = page.get_pixmap(matrix=mat)
                jpegs.append(_compress_photo(pix.tobytes("png")))
        finally:
            doc.close()
        if not jpegs:
            raise ValueError("PDF sans page exploitable.")
        return jpegs

    # Sinon : fichier image
    try:
        return [_compress_photo(raw_bytes)]
    except Exception as e:
        raise ValueError(f"Image illisible : {e}")


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
    produit_id: Optional[int] = None        # facultatif : réception basée catalogue achats
    designation_libre: Optional[str] = None # libellé article si pas de produit interne
    catalogue_fournisseur_id: Optional[int] = None
    fournisseur_id: Optional[int] = None
    fournisseur_nom: Optional[str] = None
    numero_lot: Optional[str] = None
    lot_interne: int = 0
    dlc: Optional[str] = None
    dluo: Optional[str] = None
    date_abattage: Optional[str] = None
    dlc_type: Optional[str] = None          # 'dlc' | 'date_abattage' | 'no_dlc'
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
    substitution_article: Optional[str] = None   # article commandé livré en substitut


class LigneUpdate(BaseModel):
    produit_id: Optional[int] = None
    catalogue_fournisseur_id: Optional[int] = None
    fournisseur_id: Optional[int] = None
    fournisseur_nom: Optional[str] = None
    numero_lot: Optional[str] = None
    lot_interne: int = 0
    dlc: Optional[str] = None
    dluo: Optional[str] = None
    date_abattage: Optional[str] = None
    dlc_type: Optional[str] = None          # 'dlc' | 'date_abattage' | 'no_dlc'
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
    substitution_article: Optional[str] = None


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
    photo_bl:                List[UploadFile] = File(default=[]),
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

        # Photos BL (multi-pages) : page 0 → colonne existante, pages suivantes → reception_bl_pages
        from datetime import datetime, timezone
        photos_bl_valides = [f for f in photo_bl if f and f.filename]
        for page_num, upload in enumerate(photos_bl_valides):
            raw = await upload.read()
            jpeg = _compress_photo(raw)
            now_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            if page_num == 0:
                filename = f"BL-{now_str}-{rid}.jpg"
                (PHOTOS_BL_DIR / filename).write_bytes(jpeg)
                await db.execute(
                    "UPDATE receptions SET photo_bl_filename = ? WHERE id = ?",
                    (filename, rid),
                )
            else:
                filename = f"BL-{now_str}-{rid}-p{page_num}.jpg"
                (PHOTOS_BL_DIR / filename).write_bytes(jpeg)
                await db.execute(
                    "INSERT INTO reception_bl_pages (reception_id, bl_supplementaire_id, page_num, photo_filename) VALUES (?, NULL, ?, ?)",
                    (rid, page_num, filename),
                )
        if photos_bl_valides:
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

        # produit_id facultatif (réception basée catalogue achats). S'il est fourni,
        # il doit exister. Sinon, designation_libre identifie l'article.
        if body.produit_id is not None:
            cur2 = await db.execute(
                "SELECT id FROM produits WHERE id = ?", (body.produit_id,)
            )
            if not await cur2.fetchone():
                raise HTTPException(400, "produit_id introuvable")
        elif not (body.designation_libre or "").strip():
            raise HTTPException(400, "produit_id ou designation_libre requis")

        lid = await add_reception_ligne(db, reception_id, body.model_dump())

        cur3 = await db.execute(
            "SELECT * FROM reception_lignes WHERE id = ?", (lid,)
        )
        row = await cur3.fetchone()
    return dict(row)


class NumeroBLBody(BaseModel):
    numero_bon_livraison: str


@router.put("/receptions/{reception_id}/numero-bl")
async def set_numero_bl(reception_id: int, body: NumeroBLBody):
    """Enregistre le n° de bon de livraison de la réception (1 par réception).

    Sert de préfixe au lot interne {BL}-{code_article}-{JJMMAA}. Saisi manuellement
    ou confirmé depuis l'OCR, une seule fois pour toute la réception.
    """
    numero = (body.numero_bon_livraison or "").strip()
    if not numero:
        raise HTTPException(400, "Numéro de bon de livraison vide")
    async with get_db() as db:
        cur = await db.execute("SELECT id FROM receptions WHERE id = ?", (reception_id,))
        if not await cur.fetchone():
            raise HTTPException(404, "Réception introuvable")
        await db.execute(
            "UPDATE receptions SET numero_bon_livraison = ? WHERE id = ?",
            (numero, reception_id),
        )
        await db.commit()
    return {"numero_bon_livraison": numero}


async def _generer_lot_bl(db, reception_id: int, ligne_id: int) -> str:
    """Construit le lot interne {BL}-{code_article}-{JJMMAA} pour une ligne de réception.

    Récupère le n° BL + date de la réception et le code_article catalogue de la ligne.
    Lève une 400 explicite si le n° BL n'a pas encore été saisi.
    """
    cur = await db.execute(
        """
        SELECT r.numero_bon_livraison AS bl,
               r.date_reception       AS date_reception,
               COALESCE(cf.code_article, p.code_unique) AS code_article
        FROM reception_lignes rl
        JOIN receptions r ON r.id = rl.reception_id
        LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
        LEFT JOIN produits p ON p.id = rl.produit_id
        WHERE rl.id = ? AND rl.reception_id = ?
        """,
        (ligne_id, reception_id),
    )
    row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Ligne de réception introuvable")
    if not row["bl"] or not str(row["bl"]).strip():
        raise HTTPException(
            400, "Saisir le n° de bon de livraison de la réception avant de générer un lot interne."
        )
    if not row["code_article"] or not str(row["code_article"]).strip():
        raise HTTPException(400, "Aucun code article (catalogue) pour cette ligne.")
    return format_lot_interne_bl(row["bl"], row["code_article"], row["date_reception"])


@router.get("/receptions/{reception_id}/lot-interne")
async def get_lot_interne_par_code(reception_id: int, code_article: str = Query(...)):
    """Génère le lot interne {BL}-{code_article}-{JJMMAA} avant enregistrement de la ligne.

    Utilisé pendant la saisie de réception, où la ligne n'existe pas encore en base.
    Le n° BL et la date sont lus sur la réception ; le code_article (catalogue) vient du front.
    """
    async with get_db() as db:
        cur = await db.execute(
            "SELECT numero_bon_livraison AS bl, date_reception FROM receptions WHERE id = ?",
            (reception_id,),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Réception introuvable")
    if not row["bl"] or not str(row["bl"]).strip():
        raise HTTPException(
            400, "Saisir le n° de bon de livraison de la réception avant de générer un lot interne."
        )
    code = (code_article or "").strip()
    if not code:
        raise HTTPException(400, "Code article manquant.")
    lot = format_lot_interne_bl(row["bl"], code, row["date_reception"])
    return {"lot_interne": lot}


@router.get("/receptions/{reception_id}/lignes/{ligne_id}/lot-interne")
async def get_lot_interne(reception_id: int, ligne_id: int):
    """Génère le lot interne {BL}-{code_article}-{JJMMAA} pour une ligne déjà enregistrée."""
    async with get_db() as db:
        lot = await _generer_lot_bl(db, reception_id, ligne_id)
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


class TempCamionBody(BaseModel):
    temperature_camion: Optional[float] = None


@router.put("/receptions/{reception_id}/temperature-camion")
async def maj_temperature_camion(reception_id: int, body: TempCamionBody):
    """Met à jour la temp camion + recalcule la conformité de toutes les lignes."""
    async with get_db() as db:
        lignes = await update_reception_temperature_camion(
            db, reception_id, body.temperature_camion
        )
    if lignes is None:
        raise HTTPException(404, "Réception non trouvée")
    return {"lignes": lignes}


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


@router.delete("/receptions/{reception_id}")
async def annuler_reception(reception_id: int):
    """
    Annule (supprime) une réception entière : ses lignes (donc le stock dérivé),
    ses BL et son lien commande. Bloqué si des données aval existent (facture,
    lot de fabrication, cuisson, refroidissement, ouverture, maturation, incident,
    NC fournisseur) → renvoie 409 avec la liste des blocages.

    La commande liée redevient « confirmee » et donc à nouveau sélectionnable dans
    le module réception (utile pour refaire la saisie, ex. avec l'OCR du BL).
    """
    async with get_db() as db:
        res = await supprimer_reception(db, reception_id)

    if not res["deleted"]:
        if res.get("raison") == "introuvable":
            raise HTTPException(404, "Réception non trouvée")
        blocages = res.get("blocages", [])
        raise HTTPException(
            409,
            "Annulation impossible — données liées : " + ", ".join(blocages),
        )
    return res


# IMPORTANT : cette route doit être AVANT /receptions/{id}
@router.get("/receptions/textes-aide-visuel")
async def textes_aide_visuel():
    """Référentiel des critères de contrôle visuel par espèce."""
    return TEXTES_AIDE_VISUEL


# IMPORTANT : cette route doit être AVANT /receptions/{id}
@router.get("/receptions/en-cours")
async def reception_en_cours():
    """Réception 'en_cours' la plus récente (fiche créée mais non clôturée), ou null.
    Permet au module réception de proposer de reprendre/abandonner une fiche
    quittée sans clôture (sinon elle disparaît du stock et piège sa commande liée).
    """
    async with get_db() as db:
        return await get_reception_en_cours(db)


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
                rl.origine     AS origine,
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
                "derniere_origine": d.get("origine"),
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


@router.post("/receptions/{reception_id}/ocr-bl")
async def ocr_bl(reception_id: int):
    """Lit la/les photo(s) BL stockée(s) pour cette réception et en extrait,
    via Claude vision, les articles (désignation / lot / DLC / DLUO) sous forme
    structurée. Aucune écriture en base : le front affiche le résultat dans un
    écran de validation, l'utilisateur corrige, puis enregistre les lignes
    normalement.
    """
    from src.ocr_bl import extraire_bl, OCRError

    async with get_db() as db:
        cur = await db.execute(
            "SELECT photo_bl_filename FROM receptions WHERE id = ?", (reception_id,)
        )
        row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Réception non trouvée")

        # Rassembler tous les fichiers : photo principale + pages supplémentaires
        fichiers: List[str] = []
        if row["photo_bl_filename"]:
            fichiers.append(row["photo_bl_filename"])

        cur2 = await db.execute(
            "SELECT photo_filename FROM reception_bl_pages "
            "WHERE reception_id = ? AND bl_supplementaire_id IS NULL ORDER BY page_num",
            (reception_id,),
        )
        for r in await cur2.fetchall():
            if r["photo_filename"]:
                fichiers.append(r["photo_filename"])

    if not fichiers:
        raise HTTPException(400, "Aucune photo de BL pour cette réception")

    # Charger les images depuis le disque
    images: List[bytes] = []
    for nom in fichiers:
        chemin = PHOTOS_BL_DIR / nom
        if chemin.exists():
            images.append(chemin.read_bytes())
    if not images:
        raise HTTPException(404, "Fichiers photo BL introuvables sur le disque")

    try:
        data = extraire_bl(images)
    except OCRError as e:
        raise HTTPException(502, str(e))

    return data


@router.get("/receptions/{reception_id}/bl-apercu")
async def get_bl_apercu(reception_id: int):
    """Liste TOUTES les pages du BL principal d'une réception, prêtes à afficher :
    page 0 (photo_bl_filename) + pages supplémentaires (reception_bl_pages).
    Renvoie pour chacune une URL d'image servie par les routes photo existantes.
    Permet de contrôler visuellement le BL enregistré et de repérer une page manquante.
    """
    async with get_db() as db:
        cur = await db.execute(
            "SELECT id, photo_bl_filename FROM receptions WHERE id = ?", (reception_id,)
        )
        rec = await cur.fetchone()
        if not rec:
            raise HTTPException(404, "Réception non trouvée")

        pages: List[dict] = []
        if rec["photo_bl_filename"]:
            pages.append({
                "page_num": 0,
                "url": f"/api/receptions/{reception_id}/photo-bl",
            })

        cur2 = await db.execute(
            "SELECT id, page_num FROM reception_bl_pages "
            "WHERE reception_id = ? AND bl_supplementaire_id IS NULL ORDER BY page_num",
            (reception_id,),
        )
        for r in await cur2.fetchall():
            pages.append({
                "page_num": r["page_num"],
                "url": f"/api/receptions/{reception_id}/bl-pages/{r['id']}/photo",
            })

    return {"reception_id": reception_id, "nb_pages": len(pages), "pages": pages}


@router.post("/receptions/{reception_id}/bl-pages", status_code=201)
async def ajouter_bl_pages(
    reception_id: int,
    fichier: List[UploadFile] = File(default=[]),
):
    """Ajoute une ou plusieurs page(s) au BL principal d'une réception.
    Accepte des images (JPG/PNG) et des PDF (convertis en 1 image par page).
    La 1re page va dans receptions.photo_bl_filename si vide, les suivantes dans
    reception_bl_pages (page_num croissant). Permet de compléter un BL incomplet
    puis de relancer l'OCR.
    """
    from datetime import datetime, timezone

    fichiers_valides = [f for f in fichier if f and f.filename]
    if not fichiers_valides:
        raise HTTPException(400, "Aucun fichier fourni")

    async with get_db() as db:
        cur = await db.execute(
            "SELECT id, photo_bl_filename FROM receptions WHERE id = ?", (reception_id,)
        )
        rec = await cur.fetchone()
        if not rec:
            raise HTTPException(404, "Réception non trouvée")

        a_page0 = bool(rec["photo_bl_filename"])

        cur2 = await db.execute(
            "SELECT COALESCE(MAX(page_num), 0) AS m FROM reception_bl_pages "
            "WHERE reception_id = ? AND bl_supplementaire_id IS NULL",
            (reception_id,),
        )
        prochain_num = ((await cur2.fetchone())["m"] or 0) + 1

        # Convertir tous les fichiers (image/PDF) en JPEG (1+ par fichier)
        jpegs: List[bytes] = []
        for upload in fichiers_valides:
            raw = await upload.read()
            try:
                jpegs.extend(_fichier_bl_vers_jpegs(raw, upload.filename))
            except ValueError as e:
                raise HTTPException(400, str(e))

        ajoutees = 0
        for jpeg in jpegs:
            now_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            if not a_page0:
                # Première page = page 0 (colonne receptions)
                filename = f"BL-{now_str}-{reception_id}.jpg"
                (PHOTOS_BL_DIR / filename).write_bytes(jpeg)
                await db.execute(
                    "UPDATE receptions SET photo_bl_filename = ? WHERE id = ?",
                    (filename, reception_id),
                )
                a_page0 = True
            else:
                filename = f"BL-{now_str}-{reception_id}-p{prochain_num}.jpg"
                (PHOTOS_BL_DIR / filename).write_bytes(jpeg)
                await db.execute(
                    "INSERT INTO reception_bl_pages "
                    "(reception_id, bl_supplementaire_id, page_num, photo_filename) "
                    "VALUES (?, NULL, ?, ?)",
                    (reception_id, prochain_num, filename),
                )
                prochain_num += 1
            ajoutees += 1

        await db.commit()

    return {"ok": True, "pages_ajoutees": ajoutees}


@router.get("/receptions/{reception_id}/bl-pages")
async def get_bl_pages(reception_id: int, bl_supplementaire_id: Optional[int] = None):
    """Retourne la liste des pages BL supplémentaires (page_num >= 1).
    bl_supplementaire_id=None → BL principal ; sinon BL supplémentaire.
    """
    async with get_db() as db:
        if bl_supplementaire_id is None:
            cur = await db.execute(
                "SELECT id, page_num FROM reception_bl_pages WHERE reception_id = ? AND bl_supplementaire_id IS NULL ORDER BY page_num",
                (reception_id,),
            )
        else:
            cur = await db.execute(
                "SELECT id, page_num FROM reception_bl_pages WHERE reception_id = ? AND bl_supplementaire_id = ? ORDER BY page_num",
                (reception_id, bl_supplementaire_id),
            )
        rows = await cur.fetchall()
    return [{"id": r["id"], "page_num": r["page_num"]} for r in rows]


@router.get("/receptions/{reception_id}/bl-pages/{page_id}/photo")
async def get_bl_page_photo(reception_id: int, page_id: int):
    async with get_db() as db:
        cur = await db.execute(
            "SELECT photo_filename FROM reception_bl_pages WHERE id = ? AND reception_id = ?",
            (page_id, reception_id),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Page introuvable")
    filepath = PHOTOS_BL_DIR / row["photo_filename"]
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
    photo:           List[UploadFile] = File(default=[]),
):
    """Ajoute un BL supplémentaire à une réception (refus livraison multi-fournisseur).
    1 BL par fournisseur. Le 1er BL/fournisseur reste sur la table `receptions`.
    Accepte plusieurs pages via le champ `photo` (multi-file).
    """
    if not fournisseur_id and not (fournisseur_nom and fournisseur_nom.strip()):
        raise HTTPException(400, "fournisseur_id ou fournisseur_nom requis")

    photo_filename = None
    async with get_db() as db:
        cur = await db.execute("SELECT id FROM receptions WHERE id = ?", (reception_id,))
        if not await cur.fetchone():
            raise HTTPException(404, "Réception non trouvée")

        from datetime import datetime, timezone
        photos_valides = [f for f in photo if f and f.filename]

        if photos_valides:
            raw = await photos_valides[0].read()
            jpeg = _compress_photo(raw)
            now_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            photo_filename = f"BL-{now_str}-{reception_id}-supp.jpg"
            (PHOTOS_BL_DIR / photo_filename).write_bytes(jpeg)

        bl_id = await add_reception_bl_supplementaire(db, reception_id, {
            "fournisseur_id":    fournisseur_id,
            "fournisseur_nom":   (fournisseur_nom or "").strip() or None,
            "photo_bl_filename": photo_filename,
        })

        # Pages supplémentaires (page_num >= 1)
        for page_num, upload in enumerate(photos_valides[1:], start=1):
            raw = await upload.read()
            jpeg = _compress_photo(raw)
            now_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            filename = f"BL-{now_str}-{reception_id}-supp-p{page_num}.jpg"
            (PHOTOS_BL_DIR / filename).write_bytes(jpeg)
            await db.execute(
                "INSERT INTO reception_bl_pages (reception_id, bl_supplementaire_id, page_num, photo_filename) VALUES (?, ?, ?, ?)",
                (reception_id, bl_id, page_num, filename),
            )
        await db.commit()
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

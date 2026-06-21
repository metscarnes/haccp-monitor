"""
routes_prix_etiquettes.py — API étiquettes prix Brother QL-820NWBc

Endpoints :
  POST /api/prix-etiquettes/preview         → PNG base64 (prévisualisation live)
  POST /api/prix-etiquettes/imprimer        → impression USB
  GET  /api/prix-etiquettes/fonts           → liste polices TTF custom
  POST /api/prix-etiquettes/upload-font     → upload TTF/OTF
  GET  /api/prix-etiquettes/modeles         → modèles sauvegardés
  POST /api/prix-etiquettes/modeles         → sauvegarder un modèle
  PUT  /api/prix-etiquettes/modeles/{id}    → modifier un modèle
  DELETE /api/prix-etiquettes/modeles/{id}  → supprimer un modèle
  GET  /api/prix-etiquettes/catalogue       → recherche catalogue achats (import)
"""

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

from src.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

FONTS_DIR = Path(__file__).parent.parent.parent / "static" / "fonts" / "custom"
FONTS_DIR.mkdir(parents=True, exist_ok=True)

EXTENSIONS_AUTORISEES = {".ttf", ".otf"}
TAILLE_MAX_FONT = 5 * 1024 * 1024  # 5 Mo


# ---------------------------------------------------------------------------
# Modèles Pydantic
# ---------------------------------------------------------------------------

class LigneTexte(BaseModel):
    texte: str = ""
    poids: float = 1.0   # poids relatif (mode auto) : 2.0 = deux fois plus grand
    taille_px: int = 0   # > 0 = taille FIXE en px imposée ; 0 = auto-fit
    gras: bool = False
    police: Optional[str] = None
    alignement: str = "center"   # left | center | right


class ConfigEtiquette(BaseModel):
    largeur_cm: float = 10.0
    hauteur_cm: float = 7.5
    fond_noir: bool = False
    lignes: list[LigneTexte] = []


class ModeleCreate(BaseModel):
    nom: str
    config: ConfigEtiquette


# ---------------------------------------------------------------------------
# Prévisualisation
# ---------------------------------------------------------------------------

@router.post("/api/prix-etiquettes/preview")
async def preview_etiquette(config: ConfigEtiquette):
    """Génère un PNG base64 de l'étiquette pour la prévisualisation live."""
    from src.printing.brother_ql_prix import generer_preview_base64
    try:
        data = config.model_dump()
        png_b64 = generer_preview_base64(data)
        return {"image": f"data:image/png;base64,{png_b64}"}
    except Exception as e:
        logger.error("Erreur preview étiquette prix : %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Impression
# ---------------------------------------------------------------------------

@router.post("/api/prix-etiquettes/imprimer")
async def imprimer_etiquette(config: ConfigEtiquette):
    """Envoie l'étiquette à l'imprimante Brother via USB."""
    from src.printing.brother_ql_prix import imprimer_etiquette_prix
    data = config.model_dump()
    ok, message = imprimer_etiquette_prix(data)
    if not ok:
        raise HTTPException(status_code=503, detail=message)
    return {"ok": True, "message": message}


# ---------------------------------------------------------------------------
# Polices custom
# ---------------------------------------------------------------------------

@router.get("/api/prix-etiquettes/fonts")
async def lister_fonts():
    """Retourne la liste des polices TTF/OTF uploadées."""
    from src.printing.brother_ql_prix import lister_polices
    return {"fonts": lister_polices()}


@router.post("/api/prix-etiquettes/upload-font", status_code=201)
async def upload_font(fichier: UploadFile = File(...)):
    """Upload une police TTF ou OTF custom (max 5 Mo)."""
    ext = Path(fichier.filename).suffix.lower()
    if ext not in EXTENSIONS_AUTORISEES:
        raise HTTPException(status_code=400, detail="Seuls les fichiers .ttf et .otf sont acceptés")

    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_FONT:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 5 Mo)")

    # Nom sécurisé : on garde uniquement lettres, chiffres, tirets, underscores
    nom_safe = "".join(c for c in Path(fichier.filename).stem if c.isalnum() or c in "-_") + ext
    dest = FONTS_DIR / nom_safe
    dest.write_bytes(contenu)

    logger.info("Police uploadée : %s", nom_safe)
    return {"nom": nom_safe, "label": Path(nom_safe).stem}


@router.delete("/api/prix-etiquettes/fonts/{nom_fichier}", status_code=200)
async def supprimer_font(nom_fichier: str):
    """Supprime une police custom uploadée."""
    chemin = FONTS_DIR / nom_fichier
    if not chemin.exists() or chemin.suffix.lower() not in EXTENSIONS_AUTORISEES:
        raise HTTPException(status_code=404, detail="Police introuvable")
    chemin.unlink()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Modèles sauvegardés
# ---------------------------------------------------------------------------

@router.get("/api/prix-etiquettes/modeles")
async def get_modeles():
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT id, nom, config_json, created_at FROM modeles_etiquettes_prix ORDER BY nom"
        )
        return {"modeles": [
            {"id": r[0], "nom": r[1], "config": json.loads(r[2]), "created_at": r[3]}
            for r in rows
        ]}


@router.post("/api/prix-etiquettes/modeles", status_code=201)
async def creer_modele(body: ModeleCreate):
    config_json = json.dumps(body.config.model_dump(), ensure_ascii=False)
    async with get_db() as db:
        cur = await db.execute(
            "INSERT INTO modeles_etiquettes_prix (nom, config_json) VALUES (?, ?)",
            (body.nom.strip(), config_json),
        )
        await db.commit()
        return {"id": cur.lastrowid, "nom": body.nom}


@router.put("/api/prix-etiquettes/modeles/{modele_id}")
async def modifier_modele(modele_id: int, body: ModeleCreate):
    config_json = json.dumps(body.config.model_dump(), ensure_ascii=False)
    async with get_db() as db:
        cur = await db.execute(
            "UPDATE modeles_etiquettes_prix SET nom=?, config_json=? WHERE id=?",
            (body.nom.strip(), config_json, modele_id),
        )
        await db.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Modèle introuvable")
        return {"ok": True}


@router.delete("/api/prix-etiquettes/modeles/{modele_id}", status_code=200)
async def supprimer_modele(modele_id: int):
    async with get_db() as db:
        cur = await db.execute(
            "DELETE FROM modeles_etiquettes_prix WHERE id=?", (modele_id,)
        )
        await db.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Modèle introuvable")
        return {"ok": True}


# ---------------------------------------------------------------------------
# Import catalogue achats (recherche live pour pré-remplissage)
# ---------------------------------------------------------------------------

@router.get("/api/prix-etiquettes/catalogue")
async def rechercher_catalogue(q: str = Query("", min_length=0)):
    """
    Recherche dans le catalogue vente pour pré-remplir l'étiquette prix.
    Retourne id, nom, prix_vente_ttc, famille.
    """
    async with get_db() as db:
        sql = """
            SELECT id, nom, prix_vente_ttc, famille, sous_famille
            FROM catalogue_vente
            WHERE boutique_id = 1 AND actif = 1
        """
        params = []
        if q.strip():
            sql += " AND nom LIKE ?"
            params.append(f"%{q}%")
        sql += " ORDER BY famille, nom LIMIT 30"

        cur = await db.execute(sql, params)
        rows = await cur.fetchall()
        return {"articles": [
            {
                "id": r[0],
                "designation": r[1],
                "prix_vente_ttc": r[2],
                "famille": r[3],
                "sous_famille": r[4],
            }
            for r in rows
        ]}

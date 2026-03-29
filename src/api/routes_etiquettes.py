"""
routes_etiquettes.py — Module DLC / Étiquettes

GET    /api/produits                    → liste catalogue
POST   /api/produits                    → créer produit
PUT    /api/produits/{id}               → modifier produit
DELETE /api/produits/{id}               → désactiver produit
GET    /api/regles-dlc                  → règles DLC par catégorie
PUT    /api/regles-dlc/{categorie}      → modifier une règle
POST   /api/etiquettes/generer          → générer + imprimer étiquette
GET    /api/etiquettes                  → historique
GET    /api/etiquettes/alertes-dlc      → produits DLC proche
"""

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.database import (
    get_db,
    get_produits, get_produit, create_produit, update_produit,
    get_regles_dlc, update_regle_dlc,
    get_next_numero_lot, create_etiquette, get_etiquettes, get_alertes_dlc,
    calculer_dlc,
)

router = APIRouter(prefix="/api", tags=["etiquettes"])

BOUTIQUE_ID = 1  # mono-boutique Phase 2


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class ProduitCreate(BaseModel):
    nom: str
    categorie: str
    dlc_jours: int
    temperature_conservation: str
    format_etiquette: str = "standard_60x40"


class ProduitUpdate(BaseModel):
    nom: Optional[str] = None
    categorie: Optional[str] = None
    dlc_jours: Optional[int] = None
    temperature_conservation: Optional[str] = None
    format_etiquette: Optional[str] = None
    actif: Optional[bool] = None


class RegleDLCUpdate(BaseModel):
    dlc_jours: int
    note: Optional[str] = None


class EtiquetteGenerer(BaseModel):
    produit_id: Optional[int] = None
    produit_nom: str
    type_date: str                      # "fabrication" | "ouverture" | "decongélation"
    date_etiquette: date
    operateur: str
    lot_type: str = "interne"           # "interne" | "fournisseur"
    numero_lot_fournisseur: Optional[str] = None  # si lot_type == "fournisseur"
    info_complementaire: Optional[str] = None
    temperature_conservation: Optional[str] = None
    dlc_jours: Optional[int] = None     # override si pas de produit_id


# ---------------------------------------------------------------------------
# Produits
# ---------------------------------------------------------------------------

@router.get("/produits")
async def lister_produits():
    async with get_db() as db:
        produits = await get_produits(db, BOUTIQUE_ID)
    return produits


@router.post("/produits", status_code=201)
async def nouveau_produit(body: ProduitCreate):
    async with get_db() as db:
        produit_id = await create_produit(db, {"boutique_id": BOUTIQUE_ID, **body.model_dump()})
        produit = await get_produit(db, produit_id)
    return produit


@router.put("/produits/{produit_id}")
async def modifier_produit(produit_id: int, body: ProduitUpdate):
    async with get_db() as db:
        ok = await update_produit(db, produit_id, body.model_dump(exclude_none=True))
        if not ok:
            raise HTTPException(404, "Produit non trouvé ou aucun champ à modifier")
        produit = await get_produit(db, produit_id)
    return produit


@router.delete("/produits/{produit_id}", status_code=204)
async def supprimer_produit(produit_id: int):
    async with get_db() as db:
        await update_produit(db, produit_id, {"actif": False})


# ---------------------------------------------------------------------------
# Règles DLC
# ---------------------------------------------------------------------------

@router.get("/regles-dlc")
async def lister_regles_dlc():
    async with get_db() as db:
        regles = await get_regles_dlc(db, BOUTIQUE_ID)
    return regles


@router.put("/regles-dlc/{categorie}")
async def modifier_regle_dlc(categorie: str, body: RegleDLCUpdate):
    async with get_db() as db:
        await update_regle_dlc(db, BOUTIQUE_ID, categorie, body.dlc_jours, body.note)
        regles = await get_regles_dlc(db, BOUTIQUE_ID)
    regle = next((r for r in regles if r["categorie"] == categorie), None)
    return regle


# ---------------------------------------------------------------------------
# Étiquettes
# ---------------------------------------------------------------------------

@router.post("/etiquettes/generer", status_code=201)
async def generer_etiquette(body: EtiquetteGenerer):
    async with get_db() as db:
        # Récupérer infos produit si fourni
        produit = None
        if body.produit_id:
            produit = await get_produit(db, body.produit_id)
            if not produit:
                raise HTTPException(404, "Produit non trouvé")

        # Calculer la DLC
        if body.type_date == "decongélation":
            # Règle réglementaire : J+3, non modifiable
            dlc = calculer_dlc("produit_deconge", body.date_etiquette, 3)
        elif produit:
            dlc = calculer_dlc(produit["categorie"], body.date_etiquette, produit["dlc_jours"])
        elif body.dlc_jours is not None:
            dlc = calculer_dlc("manuel", body.date_etiquette, body.dlc_jours)
        else:
            raise HTTPException(400, "dlc_jours requis si produit_id non fourni")

        # Numéro de lot
        if body.lot_type == "interne":
            numero_lot = await get_next_numero_lot(db, BOUTIQUE_ID, body.date_etiquette)
        else:
            if not body.numero_lot_fournisseur:
                raise HTTPException(400, "numero_lot_fournisseur requis pour lot_type=fournisseur")
            numero_lot = body.numero_lot_fournisseur

        temp_conservation = body.temperature_conservation or (produit["temperature_conservation"] if produit else None)

        etiquette_data = {
            "boutique_id": BOUTIQUE_ID,
            "produit_id": body.produit_id,
            "produit_nom": body.produit_nom,
            "type_date": body.type_date,
            "date_etiquette": body.date_etiquette.isoformat(),
            "dlc": dlc.isoformat(),
            "temperature_conservation": temp_conservation,
            "operateur": body.operateur,
            "numero_lot": numero_lot,
            "lot_type": body.lot_type,
            "info_complementaire": body.info_complementaire,
            "mode_impression": "manuel",
        }
        etiquette_id = await create_etiquette(db, etiquette_data)

    # Tenter l'impression
    impression_ok = False
    impression_erreur = None
    try:
        from src.printing.brother_ql_driver import imprimer_etiquette
        impression_ok = imprimer_etiquette({**etiquette_data, "dlc_affichage": dlc.strftime("%d/%m/%y")})
    except ImportError:
        impression_erreur = "Driver imprimante non disponible (brother_ql non installé)"
    except Exception as e:
        impression_erreur = str(e)

    return {
        "id": etiquette_id,
        "numero_lot": numero_lot,
        "dlc": dlc.isoformat(),
        "impression_ok": impression_ok,
        "impression_erreur": impression_erreur,
    }


@router.get("/etiquettes")
async def historique_etiquettes(jours: int = 30):
    from datetime import timedelta
    depuis = datetime.now(timezone.utc) - timedelta(days=jours)
    async with get_db() as db:
        etiquettes = await get_etiquettes(db, BOUTIQUE_ID, depuis=depuis)
    return etiquettes


@router.get("/etiquettes/alertes-dlc")
async def alertes_dlc(jours_seuil: int = 2):
    async with get_db() as db:
        alertes = await get_alertes_dlc(db, BOUTIQUE_ID, jours_seuil=jours_seuil)
    return alertes


# ---------------------------------------------------------------------------
# Statut imprimante
# ---------------------------------------------------------------------------

@router.get("/impression/status")
async def statut_imprimante():
    from src.printing.brother_ql_driver import verifier_imprimante
    return verifier_imprimante()

"""
routes_etiquettes.py — Module DLC / Étiquettes

GET    /api/regles-dlc                  → règles DLC par catégorie
PUT    /api/regles-dlc/{categorie}      → modifier une règle
POST   /api/etiquettes/generer          → générer + imprimer étiquette
POST   /api/etiquettes/transformes      → étiquette produit transformé (cuisson / refroidissement)
GET    /api/etiquettes                  → historique
GET    /api/etiquettes/alertes-dlc      → produits DLC proche

Note : le CRUD `/api/produits` est défini dans routes_produits.py.
"""

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.database import (
    get_db,
    get_produit,
    get_regles_dlc, update_regle_dlc,
    get_next_numero_lot, create_etiquette, get_etiquettes, get_alertes_dlc,
    calculer_dlc,
)

router = APIRouter(prefix="/api", tags=["etiquettes"])

BOUTIQUE_ID = 1  # mono-boutique Phase 2


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

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


class EtiquetteTransforme(BaseModel):
    source_type: str                          # "cuisson" | "refroidissement"
    source_id:   int
    personnel_id: int


SOURCE_CONFIG = {
    "cuisson": {
        "tag":          "CUIT",
        "verbe":        "Cuit",
        "lot_prefix":   "C",
        "type_date":    "fabrication",
        "table":        "cuissons",
        "date_col":     "date_cuisson",
        "temp_label":   "T° fin cuisson",
    },
    "refroidissement": {
        "tag":          "REFROIDI",
        "verbe":        "Refroidi",
        "lot_prefix":   "R",
        "type_date":    "fabrication",
        "table":        "refroidissements",
        "date_col":     "date_refroidissement",
        "temp_label":   "T° fin refroidissement",
    },
}


@router.post("/etiquettes/transformes", status_code=201)
async def imprimer_etiquette_transforme(body: EtiquetteTransforme):
    """
    Imprime une étiquette pour un produit transformé (cuisson / refroidissement)
    et trace l'opération dans `etiquettes_generees` avec source_type / source_id.
    """
    cfg = SOURCE_CONFIG.get(body.source_type)
    if not cfg:
        raise HTTPException(400, f"source_type invalide : {body.source_type}")

    async with get_db() as db:
        # Pour les deux sources, on essaie de remonter le numéro de lot
        # de la réception d'origine (vrai numéro de lot HACCP). Pour la cuisson
        # → via reception_ligne_id ; pour le refroidissement → champ déjà rempli
        # à l'enregistrement (cf. routes_refroidissement.py).
        # Quantité : disponible directement sur cuisson, et cascadée depuis
        # la cuisson source pour le refroidissement.
        # Température : sortie cuisson pour CUIT, finale pour REFROIDI.
        if body.source_type == "refroidissement":
            lot_select = "s.numero_lot AS lot_origine"
            qte_select = "c.quantite AS quantite, c.unite AS unite"
            temp_select = "s.temperature_finale AS temperature"
            extra_join = "LEFT JOIN cuissons c ON c.id = s.cuisson_id"
        else:
            # Cuisson : le lot d'origine peut venir d'une réception (brut)
            # ou d'une fabrication (produit fini cru). On essaie les deux.
            lot_select = "COALESCE(rl.numero_lot, fab.lot_interne) AS lot_origine"
            qte_select = "s.quantite AS quantite, s.unite AS unite"
            temp_select = "s.temperature_sortie AS temperature"
            extra_join = (
                "LEFT JOIN reception_lignes rl ON rl.id = s.reception_ligne_id "
                "LEFT JOIN fabrications fab    ON fab.id = s.fabrication_id"
            )

        cur = await db.execute(
            f"""
            SELECT s.id            AS source_id,
                   s.{cfg['date_col']} AS date_action,
                   s.heure_fin     AS heure_action,
                   s.produit_id    AS produit_id,
                   s.dlc_finale    AS dlc,
                   p.nom           AS produit_nom,
                   p.temperature_conservation AS temperature_conservation,
                   TRIM(pers.prenom || ' ' || COALESCE(pers.nom, '')) AS operateur,
                   {lot_select},
                   {qte_select},
                   {temp_select}
            FROM   {cfg['table']} s
            LEFT   JOIN produits  p    ON p.id    = s.produit_id
            LEFT   JOIN personnel pers ON pers.id = ?
            {extra_join}
            WHERE  s.id = ?
            """,
            (body.personnel_id, body.source_id),
        )
        row = await cur.fetchone()
        if not row:
            raise HTTPException(404, f"{body.source_type} #{body.source_id} introuvable")

        if not row["dlc"]:
            raise HTTPException(422, "DLC absente sur l'enregistrement source")

        produit_nom  = row["produit_nom"] or ""
        operateur    = row["operateur"] or ""
        date_action  = row["date_action"]
        heure_action = row["heure_action"] or ""
        dlc_iso      = row["dlc"]
        lot_origine  = row["lot_origine"]
        quantite     = row["quantite"]
        unite        = row["unite"] or "kg"
        temperature  = row["temperature"]

        # Numéro de lot affiché : on privilégie le vrai lot HACCP issu de la
        # réception. Fallback synthétique C-{id} / R-{id} uniquement si la
        # source n'a pas de lot rattaché (cas exceptionnel).
        numero_lot = lot_origine or f"{cfg['lot_prefix']}-{row['source_id']}"
        info_compl = None

        etiquette_data = {
            "boutique_id":              BOUTIQUE_ID,
            "produit_id":               row["produit_id"],
            "produit_nom":              produit_nom,
            "type_date":                cfg["type_date"],
            "date_etiquette":           date_action,
            "dlc":                      dlc_iso,
            "temperature_conservation": row["temperature_conservation"],
            "operateur":                operateur,
            "numero_lot":               numero_lot,
            "lot_type":                 "interne",
            "info_complementaire":      info_compl,
            "mode_impression":          "auto",
            "source_type":              body.source_type,
            "source_id":                body.source_id,
        }
        etiquette_id = await create_etiquette(db, etiquette_data)

    # L'impression elle-même est faite côté client via window.print()
    # (même mécanisme que le module fabrication). On retourne ici les données
    # nécessaires au rendu du gabarit thermique.
    return {
        "id":           etiquette_id,
        "numero_lot":   numero_lot,
        "dlc":          dlc_iso,
        "tag":          cfg["tag"],
        "produit_nom":  produit_nom,
        "action_verbe": cfg["verbe"],
        "date_action":  date_action,
        "heure_action": heure_action,
        "operateur":    operateur,
        "quantite":     quantite,
        "unite":        unite,
        "temperature":  temperature,
        "temp_label":   cfg["temp_label"],
        "info_complementaire": info_compl,
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
# Statut & configuration imprimante
# ---------------------------------------------------------------------------

@router.get("/impression/status")
async def statut_imprimante():
    from src.printing.brother_ql_driver import verifier_imprimante
    return verifier_imprimante()


class PrinterConfigUpdate(BaseModel):
    identifier: str          # ex. "tcp://192.168.1.42"
    model: Optional[str] = None
    backend: Optional[str] = None


@router.get("/impression/config")
async def get_config_imprimante():
    from src.printing.printer_config import get_printer_config
    return get_printer_config()


@router.post("/impression/config")
async def set_config_imprimante(body: PrinterConfigUpdate):
    from src.printing.printer_config import save_printer_config
    if not body.identifier.strip():
        raise HTTPException(status_code=422, detail="L'adresse de l'imprimante ne peut pas être vide.")
    cfg = save_printer_config(
        identifier=body.identifier,
        model=body.model,
        backend=body.backend,
    )
    return {"ok": True, "config": cfg}

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.database import (
    get_db, get_alertes_en_cours, get_alertes_enceinte,
    get_destinataires, create_destinataire,
    update_destinataire, delete_destinataire,
    get_parametre, set_parametre,
)
from src.alert_manager import envoyer_alerte, SMTP_USER, SMTP_PASSWORD

router = APIRouter(tags=["alertes"])

BOUTIQUE_ID = 1  # mono-boutique Phase 2
CLE_ALERTES_EMAIL_ACTIF = "alertes_email_actif"


# ---------------------------------------------------------------------------
# Alertes
# ---------------------------------------------------------------------------

@router.get("/api/alertes/en-cours")
async def alertes_en_cours():
    async with get_db() as db:
        return await get_alertes_en_cours(db)


@router.get("/api/enceintes/{enceinte_id}/alertes")
async def alertes_enceinte(enceinte_id: int):
    async with get_db() as db:
        return await get_alertes_enceinte(db, enceinte_id)


# ---------------------------------------------------------------------------
# Destinataires
# ---------------------------------------------------------------------------

class DestinataireCreate(BaseModel):
    nom: str
    email: Optional[str] = None
    telephone: Optional[str] = None


@router.get("/api/destinataires")
async def liste_destinataires():
    async with get_db() as db:
        return await get_destinataires(db)


@router.post("/api/destinataires", status_code=201)
async def ajouter_destinataire(data: DestinataireCreate):
    if not data.email and not data.telephone:
        raise HTTPException(400, "Au moins un email ou un téléphone est requis")
    async with get_db() as db:
        did = await create_destinataire(db, data.model_dump())
    return {"id": did}


@router.put("/api/destinataires/{dest_id}")
async def modifier_destinataire(dest_id: int, data: DestinataireCreate):
    if not data.email and not data.telephone:
        raise HTTPException(400, "Au moins un email ou un téléphone est requis")
    async with get_db() as db:
        ok = await update_destinataire(db, dest_id, data.model_dump())
    if not ok:
        raise HTTPException(404, "Destinataire introuvable")
    return {"ok": True}


@router.delete("/api/destinataires/{dest_id}", status_code=204)
async def supprimer_destinataire(dest_id: int):
    async with get_db() as db:
        ok = await delete_destinataire(db, dest_id)
    if not ok:
        raise HTTPException(404, "Destinataire introuvable")


# ---------------------------------------------------------------------------
# Activation / désactivation des alertes email
# ---------------------------------------------------------------------------

class AlertesEmailActifUpdate(BaseModel):
    actif: bool


@router.get("/api/alertes/email-actif")
async def get_alertes_email_actif():
    async with get_db() as db:
        valeur = await get_parametre(db, BOUTIQUE_ID, CLE_ALERTES_EMAIL_ACTIF, "1")
    return {"actif": valeur != "0"}


@router.put("/api/alertes/email-actif")
async def set_alertes_email_actif(data: AlertesEmailActifUpdate):
    async with get_db() as db:
        await set_parametre(db, BOUTIQUE_ID, CLE_ALERTES_EMAIL_ACTIF, "1" if data.actif else "0")
    return {"ok": True, "actif": data.actif}


# ---------------------------------------------------------------------------
# Test email
# ---------------------------------------------------------------------------

@router.post("/api/alertes/test-email")
async def test_email():
    if not SMTP_USER or not SMTP_PASSWORD:
        raise HTTPException(400, "SMTP non configuré (SMTP_USER / SMTP_PASSWORD manquants)")

    async with get_db() as db:
        destinataires = await get_destinataires(db)

    emails = [d for d in destinataires if d.get("email")]
    if not emails:
        raise HTTPException(400, "Aucun destinataire avec une adresse email configurée")

    now = datetime.now(timezone.utc)
    enceinte_test = {"nom": "Enceinte Test", "boutique_nom": "Test"}
    await envoyer_alerte(
        enceinte=enceinte_test,
        type_alerte="temperature_haute",
        valeur=8.5,
        seuil=4.0,
        debut=now,
        maintenant=now,
        destinataires=emails,
    )
    return {"ok": True, "destinataires": [d["email"] for d in emails]}

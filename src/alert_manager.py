"""
alert_manager.py — Envoi des notifications (email SMTP + SMS OVH)

Appelé par mqtt_subscriber quand un seuil est dépassé depuis trop longtemps.
Configuration via variables d'environnement (voir .env.example).
"""

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration SMTP (Gmail, OVH, Infomaniak…)
# ---------------------------------------------------------------------------

SMTP_HOST     = os.getenv("SMTP_HOST") or "smtp.gmail.com"
SMTP_PORT     = int(os.getenv("SMTP_PORT") or "587")
SMTP_USER     = os.getenv("SMTP_USER")     or ""
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") or ""
SMTP_FROM     = os.getenv("SMTP_FROM")     or SMTP_USER

# ---------------------------------------------------------------------------
# Configuration SMS OVH (optionnel)
# ---------------------------------------------------------------------------

OVH_APP_KEY        = os.getenv("OVH_APP_KEY",        "")
OVH_APP_SECRET     = os.getenv("OVH_APP_SECRET",     "")
OVH_CONSUMER_KEY   = os.getenv("OVH_CONSUMER_KEY",   "")
OVH_SMS_ACCOUNT    = os.getenv("OVH_SMS_ACCOUNT",    "")   # ex: sms-ab12345-1
OVH_SMS_SENDER     = os.getenv("OVH_SMS_SENDER",     "HACCP")

# ---------------------------------------------------------------------------
# Libellés
# ---------------------------------------------------------------------------

LABELS_TYPE = {
    "temperature_haute": "Température trop haute",
    "temperature_basse": "Température trop basse",
    "perte_signal":      "Perte de signal",
    "batterie_faible":   "Batterie faible",
}

UNITES = {
    "temperature_haute": "°C",
    "temperature_basse": "°C",
    "perte_signal":      " min sans signal",
    "batterie_faible":   "%",
}


def _formater_duree(debut: datetime, maintenant: datetime) -> str:
    delta = maintenant - debut
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes > 1 else ''}"
    heures = minutes // 60
    mins   = minutes % 60
    return f"{heures}h{mins:02d}"


def _corps_alerte(
    enceinte: dict,
    type_alerte: str,
    valeur: float,
    seuil: float,
    debut: datetime,
    maintenant: datetime,
) -> str:
    label   = LABELS_TYPE.get(type_alerte, type_alerte)
    unite   = UNITES.get(type_alerte, "")
    duree   = _formater_duree(debut, maintenant)
    boutique_nom = enceinte.get("boutique_nom", "Boutique")

    lines = [
        f"⚠️  ALERTE HACCP — {boutique_nom}",
        "",
        f"Enceinte   : {enceinte['nom']}",
        f"Type       : {label}",
        f"Valeur     : {valeur:.1f}{unite}",
        f"Seuil      : {seuil:.1f}{unite}",
        f"Début      : {debut.strftime('%d/%m/%Y à %H:%M')}",
        f"Durée      : {duree}",
        "",
        "Action requise : vérifier la porte, le compresseur ou la sonde.",
        "",
        "— Système HACCP Au Comptoir des Lilas",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

async def _envoyer_email(destinataires_email: list[str], sujet: str, corps: str) -> None:
    if not destinataires_email:
        return
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP non configuré — email non envoyé")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = sujet
    msg["From"]    = SMTP_FROM
    msg["To"]      = ", ".join(destinataires_email)
    msg.attach(MIMEText(corps, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, destinataires_email, msg.as_string())
        logger.info("Email envoyé à %s", destinataires_email)
    except Exception as exc:
        logger.error("Échec envoi email : %s", exc)


# ---------------------------------------------------------------------------
# SMS OVH
# ---------------------------------------------------------------------------

async def _envoyer_sms(numeros: list[str], message: str) -> None:
    if not numeros:
        return
    if not OVH_APP_KEY:
        logger.warning("OVH SMS non configuré — SMS non envoyé")
        return

    try:
        import ovh  # pip install ovh
    except ImportError:
        logger.warning("Librairie 'ovh' absente — pip install ovh")
        return

    try:
        client = ovh.Client(
            endpoint="ovh-eu",
            application_key=OVH_APP_KEY,
            application_secret=OVH_APP_SECRET,
            consumer_key=OVH_CONSUMER_KEY,
        )
        # Tronquer à 160 caractères (SMS standard)
        sms_body = message[:160]
        client.post(
            f"/sms/{OVH_SMS_ACCOUNT}/jobs",
            charset="UTF-8",
            coding="7bit",
            message=sms_body,
            noStopClause=False,
            priority="high",
            receivers=numeros,
            sender=OVH_SMS_SENDER,
            senderForResponse=False,
            validityPeriod=2880,
        )
        logger.info("SMS envoyé à %s", numeros)
    except Exception as exc:
        logger.error("Échec envoi SMS : %s", exc)


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------

async def envoyer_alerte(
    enceinte: dict,
    type_alerte: str,
    valeur: float,
    seuil: float,
    debut: datetime,
    maintenant: Optional[datetime],
    destinataires: list[dict],
) -> None:
    """
    Notifie tous les destinataires actifs par email et/ou SMS.
    `destinataires` : liste de dicts {nom, email, telephone}.
    """
    if not destinataires:
        logger.info("Aucun destinataire configuré — alerte non notifiée")
        return

    maintenant = maintenant or datetime.now(timezone.utc)
    label      = LABELS_TYPE.get(type_alerte, type_alerte)
    corps      = _corps_alerte(enceinte, type_alerte, valeur, seuil, debut, maintenant)
    sujet      = f"⚠️ ALERTE HACCP — {enceinte['nom']} — {label}"

    emails   = [d["email"]     for d in destinataires if d.get("email")]
    numeros  = [d["telephone"] for d in destinataires if d.get("telephone")]

    await _envoyer_email(emails, sujet, corps)
    await _envoyer_sms(numeros, corps)

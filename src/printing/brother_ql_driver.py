"""
brother_ql_driver.py — Driver imprimante Brother QL-820NWB (USB → Raspberry Pi)

Pilotage via la bibliothèque `brother_ql` + Pillow.
Format cible : 60mm × 40mm sur rouleau DK-22246 (62mm continu).

En développement/test (sans imprimante), les fonctions retournent False
avec un message d'erreur explicite — elles ne font jamais planter l'API.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Imprimante Brother QL-820NWB (USB).
# brother_ql distingue le MODÈLE (pour BrotherQLRaster) de l'IDENTIFIANT de
# connexion USB (pour send). Les confondre déclenche BrotherQLUnknownModel.
PRINTER_MODEL = os.getenv("BROTHER_QL_MODEL", "QL-820NWB")
# Format USB : "usb://0x04f9:0x209b" — à ajuster selon le modèle exact détecté par lsusb
PRINTER_IDENTIFIER = os.getenv("BROTHER_QL_PRINTER", "usb://0x04f9:0x209b")

# Rouleau DK-22246 (62mm continu) — couvre le format 60mm
LABEL_TYPE = "62"

# Résolution : 300 dpi
# 60mm × 40mm à 300dpi ≈ 708 × 472 pixels
LABEL_W_PX = 708
LABEL_H_PX = 472


def generer_image_etiquette(data: dict) -> "Image":
    """
    Génère une image PIL (RGB) de l'étiquette à partir des données.

    Champs attendus dans data :
      - produit_nom       str
      - type_date         str  ("fabrication" | "ouverture" | "decongélation")
      - date_etiquette    str  (YYYY-MM-DD)
      - dlc               str  (YYYY-MM-DD)
      - dlc_affichage     str  optionnel (JJ/MM/AA si déjà formaté)
      - temperature_conservation  str
      - operateur         str
      - numero_lot        str
      - info_complementaire  str  optionnel
    """
    from PIL import Image, ImageDraw, ImageFont
    from datetime import date

    img = Image.new("RGB", (LABEL_W_PX, LABEL_H_PX), color="white")
    draw = ImageDraw.Draw(img)

    # Chargement des polices (fallback sur la police PIL par défaut si absentes)
    try:
        from PIL import ImageFont
        font_normal = ImageFont.truetype("DejaVuSans.ttf", 22)
        font_bold   = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
        font_large  = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
        font_small  = ImageFont.truetype("DejaVuSans.ttf", 18)
    except (IOError, OSError):
        font_normal = ImageFont.load_default()
        font_bold   = font_normal
        font_large  = font_normal
        font_small  = font_normal

    # Marges
    mx, my = 12, 10
    lh = 44  # hauteur de ligne
    y = my

    # Formatage des dates
    def fmt_date(d_str: str) -> str:
        try:
            return date.fromisoformat(d_str).strftime("%d/%m/%y")
        except Exception:
            return d_str or ""

    date_affiche = fmt_date(data.get("date_etiquette", ""))
    dlc_affiche  = data.get("dlc_affichage") or fmt_date(data.get("dlc", ""))
    type_date    = data.get("type_date", "")

    # --- Ligne 1 : Date + case type ---
    draw.text((mx, y), f"Date : {date_affiche}", font=font_normal, fill="black")
    # Cases à cocher simulées
    types = [("fabrication", "Fabrication"), ("ouverture", "Ouverture"), ("decongélation", "Décongélation")]
    x_check = 340
    for code, label in types:
        coche = "[x]" if type_date == code else "[ ]"
        draw.text((x_check, y), f"{coche} {label}", font=font_small, fill="black")
        y += 20
        x_check = 340
    y = my + lh

    # Séparateur
    draw.line([(mx, y), (LABEL_W_PX - mx, y)], fill="black", width=1)
    y += 6

    # --- Ligne 2 : Produit ---
    draw.text((mx, y), "PRODUIT :", font=font_bold, fill="black")
    draw.text((mx + 130, y), data.get("produit_nom", ""), font=font_large, fill="black")
    y += lh + 4

    # Séparateur
    draw.line([(mx, y), (LABEL_W_PX - mx, y)], fill="black", width=1)
    y += 6

    # --- Ligne 3 : Opérateur ---
    draw.text((mx, y), f"Opérateur : {data.get('operateur', '')}", font=font_normal, fill="black")
    y += lh

    # Séparateur
    draw.line([(mx, y), (LABEL_W_PX - mx, y)], fill="black", width=1)
    y += 6

    # --- Ligne 4 : N° LOT ---
    draw.text((mx, y), f"N° LOT : {data.get('numero_lot', '')}", font=font_normal, fill="black")
    y += lh

    # Séparateur
    draw.line([(mx, y), (LABEL_W_PX - mx, y)], fill="black", width=1)
    y += 6

    # --- Ligne 5 : DLC + T°C ---
    draw.text((mx, y), f"D.L.C : {dlc_affiche}", font=font_bold, fill="black")
    temp = data.get("temperature_conservation", "")
    if temp:
        draw.text((mx + 320, y), f"T°C : {temp}", font=font_normal, fill="black")
    y += lh

    # --- Ligne 6 : Info complémentaire (optionnel) ---
    info = data.get("info_complementaire", "")
    if info:
        draw.line([(mx, y), (LABEL_W_PX - mx, y)], fill="black", width=1)
        y += 4
        draw.text((mx, y), f"Info : {info}", font=font_small, fill="black")

    return img


def generer_image_etiquette_transforme(data: dict) -> "Image":
    """
    Génère une image PIL (RGB) pour un produit transformé (cuisson / refroidissement
    / fabrication). Format compact :

      [TAG]
      Produit
      DLC : jj/mm/aa     Lot : C-42
      <Action> le jj/mm à HHhMM
      Par : Prénom

    Champs attendus dans data :
      - tag                 str  ("CUIT" | "REFROIDI" | "MAISON")
      - produit_nom         str
      - dlc                 str  (YYYY-MM-DD)
      - numero_lot          str
      - action_verbe        str  ("Cuit" | "Refroidi" | "Fabriqué")
      - date_action         str  (YYYY-MM-DD)
      - heure_action        str  ("HH:MM")
      - operateur           str
    """
    from PIL import Image, ImageDraw, ImageFont
    from datetime import date

    img = Image.new("RGB", (LABEL_W_PX, LABEL_H_PX), color="white")
    draw = ImageDraw.Draw(img)

    try:
        font_tag      = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
        font_produit  = ImageFont.truetype("DejaVuSans-Bold.ttf", 38)
        font_dlc      = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
        font_normal   = ImageFont.truetype("DejaVuSans.ttf", 24)
    except (IOError, OSError):
        font_tag = font_produit = font_dlc = font_normal = ImageFont.load_default()

    def fmt_date(d_str: str) -> str:
        try:
            return date.fromisoformat(d_str).strftime("%d/%m/%y")
        except Exception:
            return d_str or ""

    def fmt_heure(h_str: str) -> str:
        if not h_str:
            return ""
        return h_str.replace(":", "h")

    mx, my = 14, 12
    y = my

    # Tag encadré
    tag = (data.get("tag") or "").upper()
    draw.rectangle([(mx, y), (mx + 230, y + 50)], outline="black", width=3)
    draw.text((mx + 10, y + 2), f"[{tag}]", font=font_tag, fill="black")
    y += 60

    # Nom du produit
    draw.text((mx, y), str(data.get("produit_nom", "")), font=font_produit, fill="black")
    y += 50

    # DLC + Lot
    dlc_str = fmt_date(data.get("dlc", ""))
    lot_str = data.get("numero_lot", "") or "—"
    draw.text((mx, y), f"DLC : {dlc_str}", font=font_dlc, fill="black")
    draw.text((mx + 360, y), f"Lot : {lot_str}", font=font_dlc, fill="black")
    y += 50

    draw.line([(mx, y), (LABEL_W_PX - mx, y)], fill="black", width=1)
    y += 10

    # Ligne action
    verbe   = data.get("action_verbe", "Préparé")
    date_a  = fmt_date(data.get("date_action", ""))
    heure_a = fmt_heure(data.get("heure_action", ""))
    ligne_action = f"{verbe} le {date_a}"
    if heure_a:
        ligne_action += f" à {heure_a}"
    draw.text((mx, y), ligne_action, font=font_normal, fill="black")
    y += 36

    # Opérateur
    op = data.get("operateur", "")
    if op:
        draw.text((mx, y), f"Par : {op}", font=font_normal, fill="black")

    return img


def generer_image_etiquette_simple(data: dict) -> "Image":
    """
    Étiquette minimaliste pour réimpression depuis le calendrier DLC :

      PRODUIT
      <Nom du produit>             (gros)
      ─────────────────────────────
      N° LOT : ...     DLC : jj/mm/aa

    Champs attendus dans data :
      - produit_nom   str
      - numero_lot    str
      - dlc           str  (YYYY-MM-DD)
    """
    from PIL import Image, ImageDraw, ImageFont
    from datetime import date

    img = Image.new("RGB", (LABEL_W_PX, LABEL_H_PX), color="white")
    draw = ImageDraw.Draw(img)

    try:
        font_label   = ImageFont.truetype("DejaVuSans.ttf", 24)
        font_produit = ImageFont.truetype("DejaVuSans-Bold.ttf", 56)
        font_value   = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
    except (IOError, OSError):
        font_label = font_produit = font_value = ImageFont.load_default()

    def fmt_date(d_str: str) -> str:
        try:
            return date.fromisoformat(d_str).strftime("%d/%m/%y")
        except Exception:
            return d_str or ""

    mx, my = 18, 18
    y = my

    draw.text((mx, y), "PRODUIT", font=font_label, fill="black")
    y += 32
    draw.text((mx, y), str(data.get("produit_nom", "") or ""), font=font_produit, fill="black")
    y += 80

    draw.line([(mx, y), (LABEL_W_PX - mx, y)], fill="black", width=2)
    y += 18

    lot = data.get("numero_lot", "") or "—"
    dlc = fmt_date(data.get("dlc", ""))
    draw.text((mx, y), "N° LOT", font=font_label, fill="black")
    draw.text((mx + 360, y), "DLC", font=font_label, fill="black")
    y += 32
    draw.text((mx, y), str(lot), font=font_value, fill="black")
    draw.text((mx + 360, y), dlc, font=font_value, fill="black")

    return img


def imprimer_etiquette(data: dict) -> bool:
    """
    Génère et envoie l'étiquette à l'imprimante Brother QL via USB.

    Retourne True si succès, False si erreur.
    Ne propage jamais d'exception — l'API reste disponible même sans imprimante.

    Si data["template"] == "transforme", utilise le rendu compact pour produit
    transformé (cuisson / refroidissement / fabrication).
    Si data["template"] == "simple", utilise le rendu minimal (nom / lot / DLC)
    pour réimpression depuis le calendrier DLC.
    """
    try:
        from brother_ql.conversion import convert
        from brother_ql.backends.helpers import send
        from brother_ql.raster import BrotherQLRaster
    except ImportError:
        logger.warning("brother_ql non installé — impression simulée")
        return False

    try:
        template = data.get("template")
        if template == "transforme":
            image = generer_image_etiquette_transforme(data)
        elif template == "simple":
            image = generer_image_etiquette_simple(data)
        else:
            image = generer_image_etiquette(data)

        qlr = BrotherQLRaster(PRINTER_MODEL)
        instructions = convert(
            qlr=qlr,
            images=[image],
            label=LABEL_TYPE,
            rotate="auto",
            threshold=70,
            dither=False,
            compress=False,
            red=False,
            dpi_600=False,
            hq=True,
            cut=True,
        )
        send(
            instructions=instructions,
            printer_identifier=PRINTER_IDENTIFIER,
            backend_identifier="pyusb",
            blocking=True,
        )
        logger.info("Étiquette imprimée : %s — lot %s", data.get("produit_nom"), data.get("numero_lot"))
        return True

    except Exception as e:
        logger.error("Erreur impression : %s", e)
        return False


def verifier_imprimante() -> dict:
    """
    Vérifie que l'imprimante est détectée et accessible via USB.
    Retourne un dict {"disponible": bool, "message": str}.
    """
    try:
        import usb.core
        # Vendor ID Brother = 0x04f9
        devices = list(usb.core.find(find_all=True, idVendor=0x04f9))
        if devices:
            return {"disponible": True, "message": f"{len(devices)} imprimante(s) Brother détectée(s)"}
        return {"disponible": False, "message": "Aucune imprimante Brother détectée sur USB"}
    except ImportError:
        return {"disponible": False, "message": "libusb/pyusb non installé"}
    except Exception as e:
        return {"disponible": False, "message": str(e)}

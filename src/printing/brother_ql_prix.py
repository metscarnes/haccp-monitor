"""
brother_ql_prix.py — Impression d'étiquettes prix sur Brother QL-820NWBc

Même connexion USB que brother_ql_driver.py (PRINTER_IDENTIFIER / pyusb).
Dimensions paramétrables (cm → px à 300dpi). Polices TTF custom supportées.
"""

import base64
import io
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Même identifiant USB que le driver HACCP existant
PRINTER_IDENTIFIER = os.getenv("BROTHER_QL_PRINTER", "usb://0x04f9:0x209b")
LABEL_TYPE = "62"

# Résolution 300dpi : 1 cm = 118.11 px → arrondi à 118
PX_PAR_CM = 118

# Largeur physique max du rouleau 62mm = 708px
LABEL_W_MAX_PX = 708

# Dossier polices custom uploadées
FONTS_DIR = Path(__file__).parent.parent.parent / "static" / "fonts" / "custom"
FONTS_DIR.mkdir(parents=True, exist_ok=True)


def cm_to_px(cm: float) -> int:
    return max(1, round(cm * PX_PAR_CM))


def _charger_police(nom_fichier: Optional[str], taille: int):
    """Charge une police TTF custom ou retombe sur DejaVuSans."""
    from PIL import ImageFont

    if nom_fichier:
        chemin = FONTS_DIR / nom_fichier
        if chemin.exists():
            try:
                return ImageFont.truetype(str(chemin), taille)
            except Exception:
                pass
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", taille)
    except Exception:
        return ImageFont.load_default()


def generer_image_prix(data: dict):
    """
    Génère une image PIL pour une étiquette prix.

    Champs attendus dans data :
      largeur_cm      float   — largeur de l'étiquette (ex: 10.0)
      hauteur_cm      float   — hauteur de l'étiquette (ex: 7.5)
      fond_noir       bool    — True = fond noir, texte blanc
      lignes          list    — liste de dicts décrivant chaque ligne de texte :
        {
          "texte"       : str,
          "taille"      : int,    # taille en pt (ex: 48)
          "gras"        : bool,
          "police"      : str,    # nom de fichier TTF custom (ou null)
          "alignement"  : str,    # "left" | "center" | "right"
        }
    """
    from PIL import Image, ImageDraw, ImageFont

    largeur_cm = float(data.get("largeur_cm", 10.0))
    hauteur_cm = float(data.get("hauteur_cm", 7.5))
    fond_noir  = bool(data.get("fond_noir", False))

    w = min(cm_to_px(largeur_cm), LABEL_W_MAX_PX)
    h = cm_to_px(hauteur_cm)

    couleur_fond  = "black" if fond_noir else "white"
    couleur_texte = "white" if fond_noir else "black"

    lignes_brutes = data.get("lignes", [])
    marge_h = round(w * 0.04)   # marge latérale 4%
    marge_v = round(h * 0.04)   # marge verticale 4%
    zone_w  = w - 2 * marge_h
    inter   = round(h * 0.02)   # espacement inter-ligne = 2% de la hauteur

    # ── Passe 1 : charger chaque police et auto-réduire si le texte dépasse la largeur
    lignes_rendues = []
    for ligne in lignes_brutes:
        texte      = str(ligne.get("texte", "")).strip()
        taille     = max(8, int(ligne.get("taille", 36)))
        gras       = bool(ligne.get("gras", False))
        police_fic = ligne.get("police") or None
        alignement = ligne.get("alignement", "center")

        if not texte:
            lignes_rendues.append(None)  # ligne vide = espacement
            continue

        # Charger la police à la taille demandée
        def _font(sz):
            if police_fic:
                return _charger_police(police_fic, sz)
            try:
                nom = "DejaVuSans-Bold.ttf" if gras else "DejaVuSans.ttf"
                return ImageFont.truetype(nom, sz)
            except Exception:
                return ImageFont.load_default()

        font = _font(taille)

        # Auto-réduire si le texte dépasse la largeur disponible
        tmp_draw = ImageDraw.Draw(Image.new("RGB", (w, h)))
        bbox = tmp_draw.textbbox((0, 0), texte, font=font)
        text_w = bbox[2] - bbox[0]
        while text_w > zone_w and taille > 8:
            taille -= 2
            font    = _font(taille)
            bbox    = tmp_draw.textbbox((0, 0), texte, font=font)
            text_w  = bbox[2] - bbox[0]

        line_h = bbox[3] - bbox[1]
        lignes_rendues.append({
            "texte": texte, "font": font, "taille": taille,
            "alignement": alignement, "text_w": text_w, "line_h": line_h,
        })

    # ── Passe 2 : calculer la hauteur totale du bloc texte et centrer verticalement
    hauteur_totale = sum(
        (l["line_h"] + inter) if l else inter * 2
        for l in lignes_rendues
    )
    # Retire le dernier inter
    if lignes_rendues:
        hauteur_totale -= inter

    y_start = max(marge_v, (h - hauteur_totale) // 2)

    # ── Passe 3 : dessiner
    img  = Image.new("RGB", (w, h), color=couleur_fond)
    draw = ImageDraw.Draw(img)
    y    = y_start

    for l in lignes_rendues:
        if l is None:
            y += inter * 2
            continue

        if l["alignement"] == "center":
            x = (w - l["text_w"]) // 2
        elif l["alignement"] == "right":
            x = w - marge_h - l["text_w"]
        else:
            x = marge_h

        draw.text((x, y), l["texte"], font=l["font"], fill=couleur_texte)
        y += l["line_h"] + inter

    return img


def generer_preview_base64(data: dict) -> str:
    """Retourne l'image PIL encodée en PNG base64 pour la prévisualisation."""
    img = generer_image_prix(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def imprimer_etiquette_prix(data: dict) -> bool:
    """
    Génère et envoie l'étiquette prix à l'imprimante Brother via USB.
    Retourne True si succès, False sinon — ne propage jamais d'exception.
    """
    try:
        from brother_ql.conversion import convert
        from brother_ql.backends.helpers import send
        from brother_ql.raster import BrotherQLRaster
    except ImportError:
        logger.warning("brother_ql non installé — impression simulée")
        return False

    try:
        image = generer_image_prix(data)

        qlr = BrotherQLRaster(PRINTER_IDENTIFIER)
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
        logger.info("Étiquette prix imprimée — %s", data.get("lignes", [{}])[0].get("texte", ""))
        return True

    except Exception as e:
        logger.error("Erreur impression étiquette prix : %s", e)
        return False


def lister_polices() -> list[dict]:
    """Retourne la liste des polices custom disponibles."""
    polices = []
    for f in sorted(FONTS_DIR.iterdir()):
        if f.suffix.lower() in (".ttf", ".otf"):
            polices.append({"nom": f.name, "label": f.stem})
    return polices

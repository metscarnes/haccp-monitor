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


def _charger_police(nom_fichier: Optional[str], taille: int, gras: bool = False):
    """
    Charge une police TTF à la bonne taille.
    Ordre de recherche :
      1. Police custom uploadée (FONTS_DIR)
      2. DejaVu par chemin absolu (Raspberry Pi / Linux)
      3. Arial (Windows)
      4. Toute autre police système via fonttools/fc-match
      5. load_default() en dernier recours (taille fixe — à éviter)
    """
    from PIL import ImageFont

    # 1. Police custom
    if nom_fichier:
        chemin = FONTS_DIR / nom_fichier
        if chemin.exists():
            try:
                return ImageFont.truetype(str(chemin), taille)
            except Exception:
                pass

    # 2. DejaVu chemin absolu (Pi/Linux — installé via apt install fonts-dejavu)
    suffixe = "-Bold" if gras else ""
    candidats_dejavu = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{suffixe}.ttf",
        f"/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans{suffixe}.ttf",
        f"DejaVuSans{suffixe}.ttf",  # si dans le PATH
    ]
    for chemin in candidats_dejavu:
        try:
            return ImageFont.truetype(chemin, taille)
        except Exception:
            pass

    # 3. Arial (Windows)
    candidats_windows = [
        "C:/Windows/Fonts/arialbd.ttf" if gras else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for chemin in candidats_windows:
        try:
            return ImageFont.truetype(chemin, taille)
        except Exception:
            pass

    # 4. Première police TTF trouvable dans le dossier custom du projet
    for f in sorted(FONTS_DIR.iterdir()) if FONTS_DIR.exists() else []:
        if f.suffix.lower() in (".ttf", ".otf"):
            try:
                return ImageFont.truetype(str(f), taille)
            except Exception:
                pass

    # 5. Fallback — taille ignorée mais ne plante pas
    logger.warning("Aucune police TTF trouvée — utilisation du rendu par défaut (taille fixe)")
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

    lignes_brutes = [l for l in data.get("lignes", []) if str(l.get("texte", "")).strip()]
    if not lignes_brutes:
        return Image.new("RGB", (w, h), color=couleur_fond)

    marge_h   = round(w * 0.04)
    marge_v   = round(h * 0.05)
    zone_w    = w - 2 * marge_h
    zone_h    = h - 2 * marge_v
    n_lignes  = len(lignes_brutes)
    inter     = round(h * 0.015)  # espace entre lignes

    # Hauteur disponible à répartir entre les lignes (hors espacement)
    hauteur_dispo = zone_h - inter * (n_lignes - 1)

    # Poids total pour répartition proportionnelle
    poids_total = sum(max(0.1, float(l.get("poids", 1))) for l in lignes_brutes)

    # ── Passe 1 : calculer la taille de police pour chaque ligne
    # Taille cible = hauteur allouée à cette ligne (proportionnelle au poids)
    # Puis réduire si le texte dépasse la largeur
    lignes_rendues = []
    tmp_img  = Image.new("RGB", (w, h))
    tmp_draw = ImageDraw.Draw(tmp_img)

    for ligne in lignes_brutes:
        texte      = str(ligne.get("texte", "")).strip()
        poids      = max(0.1, float(ligne.get("poids", 1)))
        gras       = bool(ligne.get("gras", False))
        police_fic = ligne.get("police") or None
        alignement = ligne.get("alignement", "center")

        # Hauteur allouée à cette ligne
        hauteur_ligne = max(8, round(hauteur_dispo * poids / poids_total))

        # Taille de départ = 85% de la hauteur allouée (laisse un peu d'espace)
        taille = max(8, round(hauteur_ligne * 0.85))

        def _font(sz):
            return _charger_police(police_fic, sz, gras=gras)

        font = _font(taille)

        # Réduire jusqu'à ce que le texte tienne en largeur ET en hauteur
        for _ in range(60):
            bbox   = tmp_draw.textbbox((0, 0), texte, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            if text_w <= zone_w and text_h <= hauteur_ligne:
                break
            taille -= 1
            if taille < 8:
                taille = 8
                font   = _font(taille)
                break
            font = _font(taille)

        bbox   = tmp_draw.textbbox((0, 0), texte, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        lignes_rendues.append({
            "texte": texte, "font": font,
            "alignement": alignement,
            "text_w": text_w, "text_h": text_h,
            "hauteur_ligne": hauteur_ligne,
        })

    # ── Passe 2 : centrage vertical du bloc
    bloc_h  = sum(l["hauteur_ligne"] for l in lignes_rendues) + inter * (n_lignes - 1)
    y_start = max(marge_v, (h - bloc_h) // 2)

    # ── Passe 3 : dessiner
    img  = Image.new("RGB", (w, h), color=couleur_fond)
    draw = ImageDraw.Draw(img)
    y    = y_start

    for l in lignes_rendues:
        # Centrage vertical du texte dans sa hauteur allouée
        y_texte = y + (l["hauteur_ligne"] - l["text_h"]) // 2

        if l["alignement"] == "center":
            x = (w - l["text_w"]) // 2
        elif l["alignement"] == "right":
            x = w - marge_h - l["text_w"]
        else:
            x = marge_h

        draw.text((x, y_texte), l["texte"], font=l["font"], fill=couleur_texte)
        y += l["hauteur_ligne"] + inter

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

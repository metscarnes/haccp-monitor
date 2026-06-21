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


def _mesurer(draw, texte, font):
    """
    Mesure une ligne de texte avec une police donnée.

    Retourne (largeur, hauteur, offset_y) où :
      - largeur  : largeur réelle des glyphes
      - hauteur  : hauteur de ligne basée sur les MÉTRIQUES de la police
                   (ascent + descent), pas la bbox des glyphes — c'est ce qui
                   garantit un dimensionnement cohérent quelle que soit la casse.
      - offset_y : décalage du haut de la bbox réelle vs l'origine, pour pouvoir
                   recoller le texte précisément lors du dessin.
    """
    ascent, descent = font.getmetrics()
    hauteur = ascent + descent
    bbox = draw.textbbox((0, 0), texte, font=font)
    largeur = bbox[2] - bbox[0]
    return largeur, hauteur, bbox[1]


def generer_image_prix(data: dict):
    """
    Génère une image PIL pour une étiquette prix.

    Principe — AUTO-FIT MAX : le texte est rendu aussi GROS que possible tout
    en tenant dans l'étiquette. Le champ "poids" de chaque ligne n'est plus une
    hauteur allouée mais un simple RATIO de taille relative entre lignes
    (poids 2 = deux fois plus haut que poids 1). On cherche le facteur d'échelle
    global maximal tel que toutes les lignes tiennent en largeur ET en hauteur.

    Champs attendus dans data :
      largeur_cm  float   — largeur de l'étiquette (ex: 10.0)
      hauteur_cm  float   — hauteur de l'étiquette (ex: 7.5)
      fond_noir   bool    — True = fond noir, texte blanc
      lignes      list    — liste de dicts décrivant chaque ligne :
        {
          "texte"      : str,
          "poids"      : float,   # ratio de taille relative (1=normal, 2=grand…)
          "gras"       : bool,
          "police"     : str,     # nom de fichier TTF custom (ou null)
          "alignement" : str,     # "left" | "center" | "right"
        }
    """
    from PIL import Image, ImageDraw

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

    marge_h  = round(w * 0.05)
    marge_v  = round(h * 0.06)
    zone_w   = max(1, w - 2 * marge_h)
    zone_h   = max(1, h - 2 * marge_v)
    n_lignes = len(lignes_brutes)
    inter    = round(h * 0.025)  # espace vertical entre lignes

    tmp_img  = Image.new("RGB", (w, h))
    tmp_draw = ImageDraw.Draw(tmp_img)

    # Normaliser les lignes (texte + métadonnées) une fois.
    lignes = []
    for ligne in lignes_brutes:
        lignes.append({
            "texte":      str(ligne.get("texte", "")).strip(),
            "poids":      max(0.1, float(ligne.get("poids", 1))),
            "gras":       bool(ligne.get("gras", False)),
            "police":     ligne.get("police") or None,
            "alignement": ligne.get("alignement", "center"),
        })

    def _font(ligne, sz):
        return _charger_police(ligne["police"], max(6, int(sz)), gras=ligne["gras"])

    # ── Recherche dichotomique du facteur d'échelle "px par unité de poids" ──
    # Pour un facteur f donné, la taille de police de chaque ligne = f * poids.
    # On veut le plus grand f tel que tout tienne dans zone_w × zone_h.
    def _tient(f):
        total_h = inter * (n_lignes - 1)
        for ligne in lignes:
            font = _font(ligne, f * ligne["poids"])
            lw, lh, _ = _mesurer(tmp_draw, ligne["texte"], font)
            if lw > zone_w:
                return False
            total_h += lh
        return total_h <= zone_h

    lo, hi = 1.0, float(max(zone_h, zone_w))  # borne haute généreuse
    # S'assurer que hi ne tient PAS (sinon on rate le vrai max) : déjà garanti
    # par la borne, mais on protège contre les cas dégénérés.
    for _ in range(40):
        mid = (lo + hi) / 2
        if _tient(mid):
            lo = mid
        else:
            hi = mid
    facteur = lo

    # ── Construction finale des lignes à la taille trouvée ──
    lignes_rendues = []
    for ligne in lignes:
        font = _font(ligne, facteur * ligne["poids"])
        lw, lh, off_y = _mesurer(tmp_draw, ligne["texte"], font)
        lignes_rendues.append({
            **ligne, "font": font,
            "text_w": lw, "line_h": lh, "off_y": off_y,
        })

    # ── Centrage vertical du bloc ──
    bloc_h  = sum(l["line_h"] for l in lignes_rendues) + inter * (n_lignes - 1)
    y_start = max(marge_v, (h - bloc_h) // 2)

    # ── Dessin ──
    img  = Image.new("RGB", (w, h), color=couleur_fond)
    draw = ImageDraw.Draw(img)
    y    = y_start

    for l in lignes_rendues:
        if l["alignement"] == "right":
            x = w - marge_h - l["text_w"]
        elif l["alignement"] == "left":
            x = marge_h
        else:
            x = (w - l["text_w"]) // 2

        # off_y recolle le haut réel des glyphes sur la position voulue.
        draw.text((x, y - l["off_y"]), l["texte"], font=l["font"], fill=couleur_texte)
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

"""
brother_ql_driver.py — Driver imprimante Brother QL-820NWB (étiquettes traçabilité)

Pilotage via la bibliothèque `brother_ql` + Pillow.
Rouleau DK-22246 (62mm continu). L'IP de l'imprimante est configurable depuis
l'UI (cf. printer_config.py) — plus aucune adresse codée en dur ici.

IMPORTANT — dimensions : pour le rouleau « 62 » continu, brother_ql exige que
l'axe correspondant à la largeur physique du rouleau fasse EXACTEMENT 696px à
300dpi, sinon convert() échoue ("image width X doesn't match printable width 696").
On reproduit donc le pipeline éprouvé du driver prix : on construit l'étiquette en
PORTRAIT (largeur 62mm = 696px, hauteur libre le long du rouleau), puis on
normalise/oriente l'image avant l'envoi.

En développement/test (sans imprimante), les fonctions retournent False/erreur
explicite — elles ne font jamais planter l'API.
"""

import logging
from pathlib import Path

# Compat Pillow ≥ 10 : Image.ANTIALIAS supprimé mais brother_ql 0.9.4 l'utilise.
from PIL import Image as _PILImage
if not hasattr(_PILImage, "ANTIALIAS"):
    _PILImage.ANTIALIAS = _PILImage.LANCZOS

logger = logging.getLogger(__name__)

# Rouleau DK-22246 (62mm continu).
LABEL_TYPE = "62"

# Largeur imprimable EXACTE du rouleau 62mm à 300dpi (axe = largeur physique).
# Nos étiquettes sont construites en portrait : largeur image = ROLL_PX.
ROLL_PX = 696

# Rotation appliquée à l'image AVANT envoi pour orienter le texte sur le rouleau.
# Par défaut 0 : l'étiquette est déjà construite en portrait (largeur = 696px =
# 62mm), donc le texte sort à l'endroit, l'étiquette s'allonge le long du rouleau.
# Si une étiquette test sort « couchée » ou à l'envers, basculer 0 → 90/180/270.
LABEL_ROTATION_DEG = 0

# Marge latérale par défaut (px).
MARGE = 22

# Polices DejaVu embarquées dans le projet (€, gras, rendu identique dev/prod).
FONTS_SYSTEM_DIR = Path(__file__).parent.parent.parent / "static" / "fonts" / "system"
DEJAVU_REGULAR = FONTS_SYSTEM_DIR / "DejaVuSans.ttf"
DEJAVU_BOLD    = FONTS_SYSTEM_DIR / "DejaVuSans-Bold.ttf"


# ---------------------------------------------------------------------------
# Polices & mesure
# ---------------------------------------------------------------------------

def _font(taille: int, gras: bool = False):
    """Charge DejaVu (embarquée en priorité, puis système, puis défaut)."""
    from PIL import ImageFont
    embarquee = DEJAVU_BOLD if gras else DEJAVU_REGULAR
    if embarquee.exists():
        try:
            return ImageFont.truetype(str(embarquee), taille)
        except Exception:
            pass
    suffixe = "-Bold" if gras else ""
    for chemin in (
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{suffixe}.ttf",
        f"DejaVuSans{suffixe}.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if gras else "C:/Windows/Fonts/arial.ttf",
    ):
        try:
            return ImageFont.truetype(chemin, taille)
        except Exception:
            pass
    logger.warning("Police TTF introuvable — rendu par défaut (taille fixe).")
    return ImageFont.load_default()


def _text_w(draw, texte, font):
    bbox = draw.textbbox((0, 0), texte, font=font)
    return bbox[2] - bbox[0]


def _line_h(font):
    a, d = font.getmetrics()
    return a + d


def _wrap(draw, texte, font, max_w):
    """Découpe un texte en lignes tenant dans max_w (coupe les mots si besoin)."""
    mots = str(texte).split()
    if not mots:
        return [""]
    lignes, courante = [], ""
    for mot in mots:
        essai = (courante + " " + mot).strip()
        if _text_w(draw, essai, font) <= max_w or not courante:
            # Mot seul trop large : on le coupe caractère par caractère.
            if _text_w(draw, essai, font) > max_w and not courante:
                buf = ""
                for ch in mot:
                    if _text_w(draw, buf + ch, font) <= max_w or not buf:
                        buf += ch
                    else:
                        lignes.append(buf)
                        buf = ch
                courante = buf
            else:
                courante = essai
        else:
            lignes.append(courante)
            courante = mot
    if courante:
        lignes.append(courante)
    return lignes


# ---------------------------------------------------------------------------
# Moteur de mise en page vertical — empile des « éléments » dans une image
# de largeur ROLL_PX, hauteur calculée dynamiquement.
#
# Chaque élément est un dict :
#   {"type": "text",   "texte": str, "size": int, "gras": bool,
#                       "align": "left|center|right", "wrap": bool}
#   {"type": "two_col","gauche": str, "droite": str, "size": int, "gras": bool}
#   {"type": "line"}                       — séparateur horizontal plein
#   {"type": "dash"}                       — séparateur tireté
#   {"type": "box_text","texte": str, "size": int, "gras": bool,
#                       "label": str|None} — encadré centré (DLC, tag…)
#   {"type": "space",  "px": int}
# ---------------------------------------------------------------------------

def _rendre_pile(elements: list) -> "Image":
    from PIL import Image, ImageDraw

    W = ROLL_PX
    zone_w = W - 2 * MARGE
    tmp = ImageDraw.Draw(Image.new("RGB", (W, 10)))

    GAP = 10  # espace vertical par défaut entre éléments

    # ── Passe 1 : préparer chaque élément (lignes wrappées) + mesurer la hauteur
    prepares = []
    total_h = MARGE
    for el in elements:
        t = el.get("type", "text")

        if t == "space":
            prepares.append(("space", el.get("px", GAP)))
            total_h += el.get("px", GAP)
            continue

        if t == "line":
            prepares.append(("line", None))
            total_h += 1 + GAP
            continue

        if t == "dash":
            prepares.append(("dash", None))
            total_h += 2 + GAP
            continue

        if t == "box_text":
            font = _font(el["size"], el.get("gras", True))
            label_font = _font(max(14, el["size"] // 3), False) if el.get("label") else None
            lab_h = _line_h(label_font) if label_font else 0
            val_h = _line_h(font)
            pad = 10
            h = pad + lab_h + val_h + pad
            prepares.append(("box_text", {
                "texte": el["texte"], "font": font,
                "label": el.get("label"), "label_font": label_font,
                "lab_h": lab_h, "val_h": val_h, "pad": pad,
            }))
            total_h += h + GAP
            continue

        if t == "two_col":
            font = _font(el["size"], el.get("gras", False))
            h = _line_h(font)
            prepares.append(("two_col", {
                "gauche": el.get("gauche", ""), "droite": el.get("droite", ""),
                "font": font, "h": h,
            }))
            total_h += h + GAP
            continue

        # text (défaut)
        font = _font(el["size"], el.get("gras", False))
        texte = str(el.get("texte", ""))
        if el.get("upper"):
            texte = texte.upper()
        lignes = _wrap(tmp, texte, font, zone_w) if el.get("wrap", True) else [texte]
        lh = _line_h(font)
        h = lh * len(lignes)
        prepares.append(("text", {
            "lignes": lignes, "font": font, "lh": lh,
            "align": el.get("align", "left"),
        }))
        total_h += h + GAP

    total_h += MARGE - GAP  # le dernier élément n'a pas de gap après lui
    total_h = max(total_h, 80)

    # ── Passe 2 : dessin
    img = Image.new("RGB", (W, total_h), "white")
    draw = ImageDraw.Draw(img)
    y = MARGE

    def _x(texte, font, align):
        if align == "center":
            return (W - _text_w(draw, texte, font)) // 2
        if align == "right":
            return W - MARGE - _text_w(draw, texte, font)
        return MARGE

    for kind, data in prepares:
        if kind == "space":
            y += data
            continue
        if kind == "line":
            draw.line([(MARGE, y), (W - MARGE, y)], fill="black", width=2)
            y += 1 + GAP
            continue
        if kind == "dash":
            x = MARGE
            while x < W - MARGE:
                draw.line([(x, y), (min(x + 10, W - MARGE), y)], fill="black", width=2)
                x += 18
            y += 2 + GAP
            continue
        if kind == "box_text":
            pad = data["pad"]
            box_h = pad + data["lab_h"] + data["val_h"] + pad
            draw.rectangle([(MARGE, y), (W - MARGE, y + box_h)], outline="black", width=3)
            yy = y + pad
            if data["label_font"]:
                lab = data["label"]
                draw.text((_x(lab, data["label_font"], "center"), yy), lab,
                          font=data["label_font"], fill="black")
                yy += data["lab_h"]
            val = data["texte"]
            draw.text((_x(val, data["font"], "center"), yy), val, font=data["font"], fill="black")
            y += box_h + GAP
            continue
        if kind == "two_col":
            font = data["font"]
            draw.text((MARGE, y), data["gauche"], font=font, fill="black")
            dr = data["droite"]
            draw.text((W - MARGE - _text_w(draw, dr, font), y), dr, font=font, fill="black")
            y += data["h"] + GAP
            continue
        # text
        font = data["font"]
        for ligne in data["lignes"]:
            draw.text((_x(ligne, font, data["align"]), y), ligne, font=font, fill="black")
            y += data["lh"]
        y += GAP

    return img


# ---------------------------------------------------------------------------
# Helpers de formatage
# ---------------------------------------------------------------------------

def _fmt_date(d_str: str) -> str:
    from datetime import date
    try:
        return date.fromisoformat(str(d_str)[:10]).strftime("%d/%m/%y")
    except Exception:
        return d_str or ""


# ---------------------------------------------------------------------------
# Templates d'étiquettes (chacun renvoie une image PIL portrait, largeur ROLL_PX)
# ---------------------------------------------------------------------------

def generer_image_etiquette(data: dict) -> "Image":
    """Étiquette standard de traçabilité (fabrication / ouverture / décongélation)."""
    els = []
    date_aff = data.get("dlc_affichage_date") or _fmt_date(data.get("date_etiquette", ""))
    type_date = (data.get("type_date") or "").capitalize()
    els.append({"type": "two_col", "gauche": f"Date : {date_aff}",
                "droite": type_date, "size": 24})
    els.append({"type": "line"})
    els.append({"type": "text", "texte": data.get("produit_nom", ""),
                "size": 42, "gras": True, "align": "center", "upper": True})
    els.append({"type": "line"})
    els.append({"type": "text", "texte": f"Opérateur : {data.get('operateur', '')}", "size": 24})
    els.append({"type": "two_col",
                "gauche": f"N° Lot : {data.get('numero_lot', '')}",
                "droite": "", "size": 26, "gras": True})
    dlc_aff = data.get("dlc_affichage") or _fmt_date(data.get("dlc", ""))
    els.append({"type": "box_text", "texte": dlc_aff, "label": "D.L.C", "size": 48})
    temp = data.get("temperature_conservation")
    if temp:
        els.append({"type": "text", "texte": f"T°C : {temp}", "size": 24, "align": "center"})
    info = data.get("info_complementaire")
    if info:
        els.append({"type": "line"})
        els.append({"type": "text", "texte": f"Info : {info}", "size": 20})
    return _rendre_pile(els)


def generer_image_etiquette_transforme(data: dict) -> "Image":
    """Produit transformé (cuisson / refroidissement) — tag, qté, T°, action."""
    tag = (data.get("tag") or "").upper()
    els = [{"type": "box_text", "texte": f"[{tag}]", "size": 40}]
    els.append({"type": "text", "texte": data.get("produit_nom", ""),
                "size": 38, "gras": True, "align": "center"})

    qte = data.get("quantite")
    unite = data.get("unite") or "kg"
    if qte not in (None, ""):
        els.append({"type": "text", "texte": f"Quantité : {qte} {unite}", "size": 24, "align": "center"})

    els.append({"type": "box_text", "texte": _fmt_date(data.get("dlc", "")), "label": "DLC", "size": 44})
    els.append({"type": "text", "texte": f"Lot : {data.get('numero_lot', '') or '—'}",
                "size": 28, "gras": True, "align": "center"})

    temp = data.get("temperature")
    if temp not in (None, ""):
        try:
            temp = f"{float(temp):.1f} °C"
        except (TypeError, ValueError):
            temp = f"{temp} °C"
        label = data.get("temp_label") or "T°"
        els.append({"type": "text", "texte": f"{label} : {temp}", "size": 24, "align": "center"})

    els.append({"type": "line"})
    verbe = data.get("action_verbe", "Préparé")
    date_a = _fmt_date(data.get("date_action", ""))
    heure_a = (data.get("heure_action") or "").replace(":", "h")
    ligne = f"{verbe} le {date_a}" + (f" à {heure_a}" if heure_a else "")
    els.append({"type": "text", "texte": ligne, "size": 24, "align": "center"})
    if data.get("operateur"):
        els.append({"type": "text", "texte": f"Par : {data['operateur']}", "size": 24, "align": "center"})
    return _rendre_pile(els)


def generer_image_etiquette_ouverture(data: dict) -> "Image":
    """Étiquette d'ouverture de produit (DLC secondaire après ouverture)."""
    els = [{"type": "box_text", "texte": "[OUVERT]", "size": 38}]
    els.append({"type": "text", "texte": data.get("produit_nom", ""),
                "size": 40, "gras": True, "align": "center", "upper": True})
    els.append({"type": "box_text", "texte": _fmt_date(data.get("dlc", "")), "label": "DLC", "size": 44})
    els.append({"type": "text", "texte": f"Lot : {data.get('numero_lot', '') or '—'}",
                "size": 28, "gras": True, "align": "center"})
    action = data.get("action") or "Ouvert"
    els.append({"type": "line"})
    els.append({"type": "text", "texte": action, "size": 24, "align": "center"})
    if data.get("operateur"):
        els.append({"type": "text", "texte": f"Par : {data['operateur']}", "size": 24, "align": "center"})
    return _rendre_pile(els)


def generer_image_etiquette_simple(data: dict) -> "Image":
    """
    Étiquette minimale (réimpression DLC / inventaire) :
    tag optionnel, PRODUIT, lot + DLC, ligne d'origine optionnelle.
    """
    els = []
    tag = data.get("tag")
    if tag:
        els.append({"type": "box_text", "texte": f"[{str(tag).upper()}]", "size": 34})
    els.append({"type": "text", "texte": "PRODUIT", "size": 22})
    els.append({"type": "text", "texte": data.get("produit_nom", "") or "",
                "size": 50, "gras": True, "align": "left"})
    els.append({"type": "line"})
    els.append({"type": "two_col",
                "gauche": f"N° Lot : {data.get('numero_lot', '') or '—'}",
                "droite": f"DLC : {_fmt_date(data.get('dlc', ''))}",
                "size": 28, "gras": True})
    origine = data.get("ligne_origine")
    if origine:
        els.append({"type": "text", "texte": origine, "size": 20})
    return _rendre_pile(els)


def generer_image_etiquette_fabrication(data: dict) -> "Image":
    """
    Étiquette de fabrication riche : nom, poids, DLC encadrée, lot, liste
    complète des ingrédients (qté/nom/lot/DLC), pied de page.

    Champs attendus :
      produit_nom, poids (str affiché), dlc (YYYY-MM-DD ou affichage),
      numero_lot, meta (str pied de page),
      ingredients : liste de str déjà formatées (ex. "1.2kg Bœuf (L:42 | DLC:01/02/25)")
    """
    els = []
    els.append({"type": "text", "texte": data.get("produit_nom", ""),
                "size": 44, "gras": True, "align": "center", "upper": True})
    poids = data.get("poids")
    if poids:
        els.append({"type": "text", "texte": poids, "size": 24, "align": "center"})
    els.append({"type": "line"})

    dlc_aff = data.get("dlc_affichage") or _fmt_date(data.get("dlc", ""))
    els.append({"type": "box_text", "texte": dlc_aff, "label": "DLC", "size": 50})

    els.append({"type": "box_text", "texte": f"Lot : {data.get('numero_lot', '') or '—'}", "size": 26})

    ingredients = data.get("ingredients") or []
    if ingredients:
        els.append({"type": "text", "texte": "Ingrédients & Lots :", "size": 20, "gras": True})
        for ing in ingredients:
            els.append({"type": "text", "texte": f"• {ing}", "size": 19, "align": "left"})

    meta = data.get("meta")
    if meta:
        els.append({"type": "line"})
        els.append({"type": "text", "texte": meta, "size": 18, "align": "center"})
    return _rendre_pile(els)


# ---------------------------------------------------------------------------
# Impression — pipeline calqué sur le driver prix (éprouvé en production)
# ---------------------------------------------------------------------------

_TEMPLATES = {
    "transforme":  generer_image_etiquette_transforme,
    "simple":      generer_image_etiquette_simple,
    "ouverture":   generer_image_etiquette_ouverture,
    "fabrication": generer_image_etiquette_fabrication,
}


def imprimer_etiquette(data: dict) -> bool:
    """
    Génère et envoie une étiquette de traçabilité à l'imprimante Brother QL
    (réseau ou USB selon printer_config). Retourne True si succès, False sinon.
    Ne propage jamais d'exception.

    data["template"] sélectionne le rendu :
      "fabrication" | "transforme" | "ouverture" | "simple" | (défaut: standard)
    """
    try:
        from brother_ql.conversion import convert
        from brother_ql.backends.helpers import send
        from brother_ql.raster import BrotherQLRaster
    except ImportError:
        logger.warning("brother_ql non installé — impression simulée")
        return False

    try:
        from PIL import Image
        from src.printing.printer_config import get_printer_config

        generateur = _TEMPLATES.get(data.get("template"), generer_image_etiquette)
        image = generateur(data)

        # Normalisation 62mm : on porte l'axe « largeur du rouleau » à 696px.
        # L'étiquette est construite en portrait (largeur = ROLL_PX) ; on la
        # tourne pour présenter une image dont la hauteur vaut 696px, comme le
        # fait le driver prix (rotate="auto" attend cette géométrie).
        if image.width != ROLL_PX:
            ratio = ROLL_PX / image.width
            image = image.resize((ROLL_PX, max(1, round(image.height * ratio))), Image.LANCZOS)
        if LABEL_ROTATION_DEG:
            image = image.rotate(-LABEL_ROTATION_DEG, expand=True)

        # Seuillage binaire (noir pur / blanc pur) pour un rendu thermique net.
        image = image.convert("L").point(lambda p: 0 if p < 180 else 255, "1")

        cfg = get_printer_config()
        qlr = BrotherQLRaster(cfg["model"])
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
            printer_identifier=cfg["identifier"],
            backend_identifier=cfg["backend"],
            blocking=True,
        )
        logger.info("Étiquette imprimée (%s) : %s — lot %s",
                    data.get("template") or "standard",
                    data.get("produit_nom"), data.get("numero_lot"))
        return True

    except Exception as e:
        logger.error("Erreur impression : %s", e, exc_info=True)
        return False


def verifier_imprimante() -> dict:
    """
    Vérifie que l'imprimante est accessible selon le backend configuré.
    - network : test d'ouverture TCP sur le port d'impression (9100).
    - pyusb   : détection du périphérique Brother (vendor 0x04f9) sur le bus USB.
    Retourne {"disponible": bool, "message": str}.
    """
    from src.printing.printer_config import get_printer_config
    cfg = get_printer_config()

    if cfg["backend"] == "network":
        import socket
        hostport = cfg["identifier"].replace("tcp://", "", 1)
        host, _, port = hostport.partition(":")
        port = int(port) if port else 9100
        try:
            with socket.create_connection((host, port), timeout=2):
                return {"disponible": True, "message": f"Imprimante joignable sur {host}:{port}"}
        except OSError as e:
            return {"disponible": False, "message": f"Imprimante injoignable sur {host}:{port} ({e})"}

    try:
        import usb.core
        devices = list(usb.core.find(find_all=True, idVendor=0x04f9))
        if devices:
            return {"disponible": True, "message": f"{len(devices)} imprimante(s) Brother détectée(s)"}
        return {"disponible": False, "message": "Aucune imprimante Brother détectée sur USB"}
    except ImportError:
        return {"disponible": False, "message": "libusb/pyusb non installé"}
    except Exception as e:
        return {"disponible": False, "message": str(e)}

"""
brother_ql_prix.py — Impression d'étiquettes prix sur Brother QL-820NWBc

Même connexion que brother_ql_driver.py (Wi-Fi réseau par défaut, USB possible).
Dimensions paramétrables (cm → px à 300dpi). Polices TTF custom supportées.
"""

import base64
import io
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Optional

# Compat Pillow ≥ 10 : Image.ANTIALIAS a été supprimé mais brother_ql 0.9.4
# l'utilise encore en interne dans convert(). On rétablit l'alias vers LANCZOS.
from PIL import Image as _PILImage
if not hasattr(_PILImage, "ANTIALIAS"):
    _PILImage.ANTIALIAS = _PILImage.LANCZOS

logger = logging.getLogger(__name__)

# brother_ql distingue trois notions —
#   - PRINTER_MODEL : le nom du modèle (ex. "QL-820NWB"), attendu par BrotherQLRaster()
#   - PRINTER_BACKEND : "network" (Wi-Fi/Ethernet) ou "pyusb" (USB direct sur le Pi)
#   - PRINTER_IDENTIFIER : l'adresse de connexion, format selon le backend :
#       network → "tcp://192.168.1.56"   |   pyusb → "usb://0x04f9:0x209b"
# Confondre modèle et identifiant déclenche BrotherQLUnknownModel.
#
# Cible boutique : imprimante en Wi-Fi sur la box (pas d'USB, tablette mobile).
PRINTER_MODEL = os.getenv("BROTHER_QL_MODEL", "QL-820NWB")
PRINTER_BACKEND = os.getenv("BROTHER_QL_BACKEND", "network")
PRINTER_IDENTIFIER = os.getenv("BROTHER_QL_PRINTER", "tcp://192.168.1.56")
LABEL_TYPE = "62"

# Résolution 300dpi : 1 cm = 118.11 px → arrondi à 118
PX_PAR_CM = 118

# Rouleau continu 62mm : la HAUTEUR de l'étiquette (= largeur du rouleau) est
# bridée à 62mm. La LARGEUR (le long du rouleau) est libre.
HAUTEUR_MAX_CM = 6.2

# Dossier polices custom uploadées
FONTS_DIR = Path(__file__).parent.parent.parent / "static" / "fonts" / "custom"
FONTS_DIR.mkdir(parents=True, exist_ok=True)

# Polices DejaVu embarquées dans le projet (contiennent le glyphe € et le gras).
# Garantit un rendu IDENTIQUE sur Windows (dev) et Raspberry Pi (prod) sans
# dépendre des chemins de polices système.
FONTS_SYSTEM_DIR = Path(__file__).parent.parent.parent / "static" / "fonts" / "system"
DEJAVU_REGULAR = FONTS_SYSTEM_DIR / "DejaVuSans.ttf"
DEJAVU_BOLD    = FONTS_SYSTEM_DIR / "DejaVuSans-Bold.ttf"


# Épaisseur du trait d'un texte barré, en fraction de la taille de police.
EPAISSEUR_BARRE = 0.07


def cm_to_px(cm: float) -> int:
    return max(1, round(cm * PX_PAR_CM))


def _charger_police(nom_fichier: Optional[str], taille: int, gras: bool = False):
    """
    Charge une police TTF à la bonne taille.
    Ordre de recherche :
      1. Police custom uploadée (FONTS_DIR)
      2. DejaVu EMBARQUÉE dans le projet (static/fonts/system) — source unique
         de vérité, contient le € et le gras, identique dev/prod.
      3. DejaVu / Arial système (sécurité si l'embarquée manque)
      4. load_default() en tout dernier recours (taille fixe — à éviter)
    """
    from PIL import ImageFont

    # 1. Police custom uploadée
    if nom_fichier:
        chemin = FONTS_DIR / nom_fichier
        if chemin.exists():
            try:
                return ImageFont.truetype(str(chemin), taille)
            except Exception:
                pass

    # 2. DejaVu embarquée dans le projet (PRIORITAIRE — règle le € et la taille)
    embarquee = DEJAVU_BOLD if gras else DEJAVU_REGULAR
    if embarquee.exists():
        try:
            return ImageFont.truetype(str(embarquee), taille)
        except Exception:
            pass

    # 3. Polices système (filet de sécurité)
    suffixe = "-Bold" if gras else ""
    candidats = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{suffixe}.ttf",
        f"/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans{suffixe}.ttf",
        f"DejaVuSans{suffixe}.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if gras else "C:/Windows/Fonts/arial.ttf",
    ]
    for chemin in candidats:
        try:
            return ImageFont.truetype(chemin, taille)
        except Exception:
            pass

    # 4. Fallback — taille ignorée mais ne plante pas
    logger.warning("Aucune police TTF trouvée — rendu par défaut (taille fixe). "
                   "Vérifier static/fonts/system/DejaVuSans.ttf")
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

    # La hauteur est bridée à la largeur physique du rouleau 62mm ; la largeur
    # (le long du rouleau) reste libre.
    hauteur_cm = min(hauteur_cm, HAUTEUR_MAX_CM)
    w = cm_to_px(largeur_cm)
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
    # taille_px > 0  →  taille FIXE imposée par l'utilisateur (mode manuel).
    # taille_px nul  →  AUTO-FIT (la taille est calculée pour remplir l'étiquette).
    lignes = []
    for ligne in lignes_brutes:
        try:
            taille_px = int(float(ligne.get("taille_px") or 0))
        except (TypeError, ValueError):
            taille_px = 0
        lignes.append({
            "texte":      str(ligne.get("texte", "")).strip(),
            "poids":      max(0.1, float(ligne.get("poids", 1))),
            "taille_px":  taille_px if taille_px > 0 else 0,
            "gras":       bool(ligne.get("gras", False)),
            "police":     ligne.get("police") or None,
            "alignement": ligne.get("alignement", "center"),
            "barre":      bool(ligne.get("barre", False)),   # ancien prix d'une promo
        })

    def _font(ligne, sz):
        return _charger_police(ligne["police"], max(6, int(sz)), gras=ligne["gras"])

    auto = [l for l in lignes if not l["taille_px"]]

    # ── Auto-fit : facteur d'échelle "px par unité de poids" pour les lignes auto.
    # Pour un facteur f, la taille des lignes auto = f * poids. On cherche le plus
    # grand f tel que TOUTES les lignes (auto + manuelles) tiennent dans la zone.
    def _taille(ligne, f):
        return ligne["taille_px"] if ligne["taille_px"] else f * ligne["poids"]

    def _tient(f):
        total_h = inter * (n_lignes - 1)
        for ligne in lignes:
            font = _font(ligne, _taille(ligne, f))
            lw, lh, _ = _mesurer(tmp_draw, ligne["texte"], font)
            if lw > zone_w:
                # Une ligne manuelle trop large ne doit pas bloquer l'auto-fit
                # des autres : on ne rejette que si c'est une ligne auto.
                if not ligne["taille_px"]:
                    return False
            total_h += lh
        return total_h <= zone_h

    if auto:
        lo, hi = 1.0, float(max(zone_h, zone_w))  # borne haute généreuse
        for _ in range(40):
            mid = (lo + hi) / 2
            if _tient(mid):
                lo = mid
            else:
                hi = mid
        facteur = lo
    else:
        facteur = 0.0  # toutes les lignes sont en taille fixe

    # ── Construction finale des lignes à la taille retenue ──
    lignes_rendues = []
    for ligne in lignes:
        font = _font(ligne, _taille(ligne, facteur))
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
        if l["barre"]:
            # Trait horizontal au milieu de l'encre (prix de référence barré).
            g, haut, d, bas = draw.textbbox((0, 0), l["texte"], font=l["font"])
            y_trait = y + (bas - haut) // 2
            epaisseur = max(2, round(getattr(l["font"], "size", 20) * EPAISSEUR_BARRE))
            draw.line([(x + g, y_trait), (x + d, y_trait)], fill=couleur_texte, width=epaisseur)
        y += l["line_h"] + inter

    return img


def generer_preview_base64(data: dict) -> str:
    """Retourne l'image PIL encodée en PNG base64 pour la prévisualisation."""
    img = generer_image_prix(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# Substitution de variables — impression de masse depuis le catalogue de vente
# ---------------------------------------------------------------------------

def formater_prix(valeur) -> str:
    """Formate un prix en '26,90 €' (virgule décimale). Vide si non renseigné."""
    if valeur is None or valeur == "":
        return ""
    try:
        return f"{float(valeur):.2f}".replace(".", ",") + " €"
    except (TypeError, ValueError):
        return ""


def _capitaliser(texte: str) -> str:
    """
    Normalise la casse : tout en minuscules puis 1re lettre en majuscule.
    Unifie des désignations catalogue incohérentes, qu'elles soient saisies
    TOUT EN MAJUSCULES ou en casse normale.
      'ARAIGNÉE A LA PROVENÇAL' → 'Araignée a la provençal'
      'cordon bleu'            → 'Cordon bleu'
    """
    if not texte:
        return texte
    bas = texte.lower()
    return bas[:1].upper() + bas[1:]


def appliquer_variables(config: dict, produit: dict) -> dict:
    """
    Retourne une COPIE de la config d'un modèle où les variables des textes de
    lignes sont remplacées à partir d'un produit du catalogue de vente.

    Variables reconnues (insensibles aux valeurs manquantes → chaîne vide) :
      {nom} {prix} {prix_kg} {prix_unite} {unite} {famille} {sous_famille}
    Variantes de casse pour le nom (unifie l'affichage sans toucher au catalogue) :
      {Nom} = Première lettre majuscule    {NOM} = TOUT EN MAJUSCULES
    L'unité ({unite}, {prix_unite}, {prix_kg}) s'adapte à unite_vente du
    catalogue de vente : 'kg' → « kg » / « le kg », 'piece' → « pièce » / « la pièce ».
    Un modèle sans variable est renvoyé tel quel (texte littéral conservé).
    """
    prix = formater_prix(produit.get("prix_vente_ttc"))
    nom = str(produit.get("nom") or produit.get("designation") or "")

    # Unité de vente : 'kg' (défaut) ou 'piece'.
    a_la_piece = str(produit.get("unite_vente") or "kg").lower() == "piece"
    unite = "pièce" if a_la_piece else "kg"
    article_unite = "la pièce" if a_la_piece else "le kg"          # ex. "le kg"
    prix_unite = (prix + " / " + unite) if prix else ""           # ex. "49,90 € / pièce"

    # Promo (étiquette seulement, le prix du catalogue ne change pas) :
    # produit["promo"] = {"prix_reference_ttc": prix barré, "prix_promo_ttc": prix promo}.
    promo = produit.get("promo") or {}
    ref, prix_promo = promo.get("prix_reference_ttc"), promo.get("prix_promo_ttc")
    economie = ""
    if ref is not None and prix_promo is not None:
        economie = formater_prix(round(float(ref) - float(prix_promo), 2))

    remplacements = {
        "{nom}":          nom,
        "{Nom}":          _capitaliser(nom),
        "{NOM}":          nom.upper(),
        "{prix}":         prix,
        "{prix_kg}":      prix_unite,        # rétro-compat : suit désormais l'unité réelle
        "{prix_unite}":   prix_unite,        # alias explicite
        "{unite}":        unite,             # "kg" / "pièce"
        "{article_unite}": article_unite,    # "le kg" / "la pièce"
        "{famille}":      str(produit.get("famille") or ""),
        "{sous_famille}": str(produit.get("sous_famille") or ""),
        "{prix_reference}": formater_prix(ref),          # prix barré (plus bas des 30 j)
        "{prix_promo}":     formater_prix(prix_promo),
        "{economie_unite}": (economie + " / " + unite) if economie else "",
    }

    def substituer(texte: str) -> str:
        for cle, val in remplacements.items():
            texte = texte.replace(cle, val)
        return texte

    nouvelle = dict(config)
    nouvelle["lignes"] = [
        {**ligne, "texte": substituer(ligne.get("texte", ""))}
        for ligne in config.get("lignes", [])
    ]
    return nouvelle


# ---------------------------------------------------------------------------
# Styles à ZONES — l'écran « Style » ne montre jamais de {variables}
# ---------------------------------------------------------------------------
# Chaque ligne d'un style porte une `zone` qui fixe son texte : le style ne contient
# que l'apparence (police, taille, alignement…), le texte vient toujours du produit.
# Une zone 'texte' est un texte fixe saisi par l'utilisateur (ex. « Fait maison »).

TEXTE_ZONES = {
    "nom":            "{Nom}",
    "prix":           "{prix}",
    "unite":          "{article_unite}",
    "prix_reference": "{prix_reference}",
    "prix_promo":     "{prix_promo}",
    "economie":       "Économisez {economie_unite}",
}
TYPES_STYLE = ("normal", "promo")

_RE_PRIX = re.compile(r"€|\d+[.,]\d{2}")
_RE_UNITE = re.compile(r"^(le\s+kg|la\s+pi[èe]ce|au\s+kg|/\s*kg|kg|pi[èe]ce)$", re.IGNORECASE)
_ZONE_DE_VARIABLE = (
    ("{prix_reference}", "prix_reference"), ("{prix_promo}", "prix_promo"),
    ("{economie", "economie"), ("{prix", "prix"),
    ("{article_unite}", "unite"), ("{unite}", "unite"),
    ("{Nom}", "nom"), ("{nom}", "nom"), ("{NOM}", "nom"),
)


def normaliser_style(config: dict) -> tuple[dict, bool]:
    """
    Garantit que chaque ligne d'un style a une `zone` et le texte de cette zone.

    Les anciens modèles (texte écrit en dur, ex. « Graisse de canard » / « 9,90 € » /
    « le kg ») sont repris AUTOMATIQUEMENT : une ligne qui ressemble à un prix devient
    la zone Prix, « le kg » la zone Unité, la première autre ligne la zone Nom, le
    reste des textes fixes. Apparence (police, taille, fond…) inchangée.
    Renvoie (style, converti) — converti=True si au moins une ligne a été interprétée.
    """
    lignes = [dict(l) for l in (config.get("lignes") or [])]
    converti = False
    deja = {l.get("zone") for l in lignes if l.get("zone")}
    for l in lignes:
        if l.get("zone") in TEXTE_ZONES or l.get("zone") == "texte":
            continue
        texte = str(l.get("texte") or "").strip()
        zone = next((z for motif, z in _ZONE_DE_VARIABLE if motif in texte), None)
        if zone is None and texte and "{" not in texte:   # autre variable → texte fixe
            if "prix" not in deja and _RE_PRIX.search(texte):
                zone = "prix"
            elif "unite" not in deja and _RE_UNITE.match(texte):
                zone = "unite"
            elif "nom" not in deja and len(texte) > 3:
                zone = "nom"
        l["zone"] = zone or "texte"
        converti = True
        deja.add(l["zone"])
    for l in lignes:
        if l["zone"] in TEXTE_ZONES:
            l["texte"] = TEXTE_ZONES[l["zone"]]
        l["barre"] = l["zone"] == "prix_reference"
    style = {**config, "lignes": lignes}
    style["type"] = config.get("type") if config.get("type") in TYPES_STYLE else (
        "promo" if any(l["zone"] == "prix_promo" for l in lignes) else "normal")
    return style, converti


def style_promo_par_defaut(normal: dict) -> dict:
    """Style promo proposé tant qu'aucun n'est enregistré : même format, même fond et
    même police que le style normal ; ancien prix barré, prix promo, économie."""
    lignes = normal.get("lignes") or []
    poids = {l.get("zone"): l.get("poids", 1) for l in lignes}
    base = {"taille_px": 0, "gras": False, "alignement": "center",
            "police": lignes[0].get("police") if lignes else None}
    zones = [("nom", poids.get("nom", 1)), ("prix_reference", 0.8),
             ("prix_promo", poids.get("prix", 2)), ("unite", poids.get("unite", 0.6)),
             ("economie", 0.6)]
    style, _ = normaliser_style({
        "largeur_cm": normal.get("largeur_cm", 10), "hauteur_cm": normal.get("hauteur_cm", 6),
        "fond_noir": normal.get("fond_noir", False), "type": "promo",
        "lignes": [{**base, "zone": z, "poids": p} for z, p in zones],
    })
    return style


# Largeur imprimable EXACTE pour le rouleau continu 62mm à 300dpi.
# brother_ql exige cette largeur précise pour le type "62", sinon le convert
# échoue ("image width X doesn't match printable width 696").
# C'est la dimension EN TRAVERS du rouleau (≈ 58,9 mm imprimables sur 62 mm).
LABEL_62_PRINTABLE_W = 696


# Un seul envoi à la fois vers l'imprimante : deux impressions simultanées
# (deux tablettes) ne doivent pas mélanger leurs données dans le flux.
_VERROU_IMPRESSION = threading.Lock()


def _image_pour_rouleau(data: dict):
    """Image de l'étiquette prête pour le rouleau 62mm (taille physique, noir/blanc)."""
    from PIL import Image
    # Image en paysage, à 300 dpi, identique à l'aperçu :
    #   largeur = longueur de l'étiquette le long du rouleau (ex. 10 cm),
    #   hauteur = dimension EN TRAVERS du rouleau (≤ 6,2 cm).
    image = generer_image_prix(data)
    w, h = image.size

    # En travers du rouleau, brother_ql exige EXACTEMENT 696 px (≈ 5,9 cm
    # imprimables sur 62 mm) — sinon il réduit toute l'image pour l'y faire
    # tenir, ce qui donnait une mini-étiquette. Une étiquette plus haute
    # (6,2 cm) est légèrement resserrée en travers (≤ 5 %) ; une plus basse
    # est centrée sur une bande blanche de 696 px. La longueur, elle, n'est
    # jamais touchée : 300 dpi exact, comme l'impression navigateur.
    if h > LABEL_62_PRINTABLE_W:
        image = image.resize((w, LABEL_62_PRINTABLE_W), Image.LANCZOS)
    elif h < LABEL_62_PRINTABLE_W:
        bande = Image.new("RGB", (w, LABEL_62_PRINTABLE_W), "white")
        bande.paste(image, (0, (LABEL_62_PRINTABLE_W - h) // 2))
        image = bande

    # Seuillage binaire : convertit chaque pixel en noir pur ou blanc pur
    # avant d'envoyer à brother_ql. Évite le gris dû à l'anticrénelage du
    # texte, indépendamment du paramètre demi-ton du driver.
    image = image.convert("L").point(lambda p: 0 if p < 180 else 255, "1")

    # brother_ql ne tourne JAMAIS une image sur rouleau continu (rotate="auto"
    # n'agit que sur les étiquettes prédécoupées) : on la tourne nous-mêmes
    # d'un quart de tour pour que sa largeur (696 px) soit en travers du
    # rouleau et sa longueur dans le sens de défilement.
    return image.rotate(90, expand=True)


def imprimer_lot(configs: list[dict]) -> tuple[bool, str]:
    """
    Génère et envoie une SÉRIE d'étiquettes prix en UN SEUL envoi (une seule
    connexion à travers le tunnel), avec coupe entre chaque étiquette.
    Les données sont compressées (supporté par la QL-820NWB) : une étiquette
    de prix est surtout blanche, le volume transmis est bien plus faible.

    Bloquant (réseau) : à appeler hors de la boucle async (run_in_threadpool).
    Retourne (succès, message). Ne propage jamais d'exception — le message
    décrit précisément la cause de l'échec pour l'afficher à l'utilisateur.
    """
    if not configs:
        return True, "Aucune étiquette à imprimer."
    try:
        from brother_ql.conversion import convert
        from brother_ql.backends.helpers import send
        from brother_ql.raster import BrotherQLRaster
    except ImportError:
        return False, "Bibliothèque brother_ql non installée sur le serveur."

    try:
        from src.printing.printer_config import get_printer_config
        images = [_image_pour_rouleau(data) for data in configs]
        cfg = get_printer_config()

        qlr = BrotherQLRaster(cfg["model"])
        instructions = convert(
            qlr=qlr,
            images=images,
            label=LABEL_TYPE,
            rotate="auto",
            threshold=70,
            dither=False,
            compress=True,
            red=False,
            dpi_600=False,
            hq=True,
            cut=True,
        )
        debut = time.monotonic()
        with _VERROU_IMPRESSION:
            send(
                instructions=instructions,
                printer_identifier=cfg["identifier"],
                backend_identifier=cfg["backend"],
                blocking=True,
            )
        premier = configs[0].get("lignes") or [{}]
        logger.info("Étiquettes prix envoyées : %d (%d octets, %.1f s) — %s",
                    len(images), len(instructions), time.monotonic() - debut,
                    premier[0].get("texte", ""))
        n = len(images)
        return True, "Étiquette imprimée." if n == 1 else f"{n} étiquettes imprimées."

    except Exception as e:
        msg = str(e) or e.__class__.__name__
        logger.error("Erreur impression étiquettes prix : %s", msg, exc_info=True)
        return False, f"Erreur imprimante : {msg}"


def imprimer_etiquette_prix(data: dict) -> tuple[bool, str]:
    """Imprime une seule étiquette prix (voir imprimer_lot)."""
    return imprimer_lot([data])


# Taille de référence pour exprimer les métriques en ratio de la taille de police.
_TAILLE_REF_METRIQUES = 1000


def metriques_police(nom_fichier: Optional[str], gras: bool = False) -> dict:
    """
    Hauteur de ligne (ascent, descent) de la police, en fraction de sa taille,
    telle que la mesure PIL à l'impression (font.getmetrics()).

    Envoyée à l'aperçu Canvas du navigateur, qui s'en sert au lieu de ses
    propres mesures : l'auto-fit de l'écran et celui de l'impression calculent
    alors exactement la même hauteur de ligne, quelle que soit la police.
    """
    font = _charger_police(nom_fichier, _TAILLE_REF_METRIQUES, gras=gras)
    try:
        ascent, descent = font.getmetrics()
    except Exception:
        return {"ascent": 0.93, "descent": 0.24}
    return {"ascent": ascent / _TAILLE_REF_METRIQUES,
            "descent": descent / _TAILLE_REF_METRIQUES}


def metriques_defaut() -> dict:
    """Métriques de la police par défaut (DejaVu embarquée), regular et gras."""
    return {"regular": metriques_police(None, gras=False),
            "bold":    metriques_police(None, gras=True)}


def lister_polices() -> list[dict]:
    """Retourne la liste des polices custom disponibles (avec leurs métriques)."""
    polices = []
    for f in sorted(FONTS_DIR.iterdir()):
        if f.suffix.lower() in (".ttf", ".otf"):
            polices.append({"nom": f.name, "label": f.stem,
                            **metriques_police(f.name)})
    return polices

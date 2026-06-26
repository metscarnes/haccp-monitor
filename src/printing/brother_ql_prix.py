"""
brother_ql_prix.py — Impression d'étiquettes prix sur Brother QL-820NWBc

Même connexion que brother_ql_driver.py (Wi-Fi réseau par défaut, USB possible).
Dimensions paramétrables (cm → px à 300dpi). Polices TTF custom supportées.
"""

import base64
import io
import logging
import os
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


# Largeur imprimable EXACTE pour le rouleau continu 62mm à 300dpi.
# brother_ql exige cette largeur précise pour le type "62", sinon le convert
# échoue ("image width X doesn't match printable width 696").
# C'est la dimension EN TRAVERS du rouleau (≈ 58,9 mm imprimables sur 62 mm).
LABEL_62_PRINTABLE_W = 696

# Résolution DANS LE SENS DE DÉFILEMENT du rouleau. La QL-820NWB avance le
# papier à 600 dpi (mode haute résolution 300×600). Calculer la longueur en
# 300 dpi donne une étiquette deux fois trop courte ; on la calcule donc à
# 600 dpi pour que la largeur demandée (ex. 10 cm) corresponde au réel.
# ⚠️ Si la longueur imprimée reste fausse, ajuster CETTE valeur (mesurer puis
# multiplier : nouvelle_valeur = 600 × longueur_demandée / longueur_mesurée).
FEED_DPI = 600
CM_PAR_POUCE = 2.54


def imprimer_etiquette_prix(data: dict) -> tuple[bool, str]:
    """
    Génère et envoie l'étiquette prix à l'imprimante Brother via USB.

    Retourne (succès, message). Ne propage jamais d'exception — le message
    décrit précisément la cause de l'échec pour l'afficher à l'utilisateur.
    """
    try:
        from brother_ql.conversion import convert
        from brother_ql.backends.helpers import send
        from brother_ql.raster import BrotherQLRaster
    except ImportError:
        return False, "Bibliothèque brother_ql non installée sur le serveur."

    try:
        from PIL import Image
        image = generer_image_prix(data)

        # Rouleau continu 62mm — on fixe CHAQUE axe à sa vraie taille physique,
        # indépendamment (comme l'impression navigateur via @page), au lieu de
        # déduire la largeur depuis le ratio. C'est ce qui garantit que les
        # dimensions saisies (ex. 10 × 6,2 cm) sortent exactes :
        #   • EN TRAVERS du rouleau  = la HAUTEUR de l'étiquette → 696 px (300 dpi,
        #     bridé à la largeur imprimable du 62mm, soit ≈ 5,9 cm max).
        #   • SENS DE DÉFILEMENT     = la LARGEUR de l'étiquette → calculée à
        #     FEED_DPI (600 dpi) car c'est la résolution réelle de défilement.
        # L'image générée est en paysage (largeur horizontale) ; brother_ql la
        # tourne de 90° via rotate="auto" pour la poser sur le rouleau.
        largeur_cm = float(data.get("largeur_cm", 10.0))
        feed_px = max(1, round(largeur_cm / CM_PAR_POUCE * FEED_DPI))
        image = image.resize((feed_px, LABEL_62_PRINTABLE_W), Image.LANCZOS)

        # Seuillage binaire : convertit chaque pixel en noir pur ou blanc pur
        # avant d'envoyer à brother_ql. Évite le gris dû à l'anticrénelage du
        # texte, indépendamment du paramètre demi-ton du driver.
        image = image.convert("L").point(lambda p: 0 if p < 180 else 255, "1")

        from src.printing.printer_config import get_printer_config
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
        premier = data.get("lignes", [{}])
        logger.info("Étiquette prix imprimée — %s",
                    premier[0].get("texte", "") if premier else "")
        return True, "Étiquette imprimée."

    except Exception as e:
        msg = str(e) or e.__class__.__name__
        logger.error("Erreur impression étiquette prix : %s", msg, exc_info=True)
        return False, f"Erreur imprimante : {msg}"


def lister_polices() -> list[dict]:
    """Retourne la liste des polices custom disponibles."""
    polices = []
    for f in sorted(FONTS_DIR.iterdir()):
        if f.suffix.lower() in (".ttf", ".otf"):
            polices.append({"nom": f.name, "label": f.stem})
    return polices

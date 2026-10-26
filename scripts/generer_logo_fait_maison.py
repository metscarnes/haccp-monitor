"""
generer_logo_fait_maison.py — Dessine le logo « Fait maison » des étiquettes prix.

Sortie : static/img/fait-maison.png — maison pleine (toit en pointe) avec « FAIT /
MAISON » évidé à l'intérieur et un liseré. Blanc + transparence : l'impression
(brother_ql_prix) et l'aperçu (prix_etiquettes.js) n'en gardent que la forme et la
peignent de la couleur du texte (blanc sur fond noir, noir sur fond blanc).

Logo propre à la boutique, volontairement différent du logo officiel « fait maison »
des restaurateurs (décret n° 2014-797).

Usage : python scripts/generer_logo_fait_maison.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RACINE = Path(__file__).resolve().parent.parent
POLICE = RACINE / "static" / "fonts" / "system" / "DejaVuSans-Bold.ttf"
SORTIE = RACINE / "static" / "img" / "fait-maison.png"
HAUTEUR = 600           # px du fichier final (≈ 5 cm à 300 dpi : on ne fait que réduire)
RATIO = 0.86            # largeur / hauteur — repris par le dessin des étiquettes
SS = 4                  # sur-échantillonnage pour des bords lisses


def _texte_centre(d, cx, y_bas, txt, taille):
    f = ImageFont.truetype(str(POLICE), int(taille))
    g, h, dr, b = d.textbbox((0, 0), txt, font=f)
    d.text((cx - (dr - g) / 2 - g, y_bas - h), txt, font=f, fill=0)


def dessiner() -> Image.Image:
    t = HAUTEUR * SS
    l, hh = int(t * RATIO), t
    m = Image.new("L", (l, hh), 0)
    d = ImageDraw.Draw(m)
    toit = hh * 0.34
    d.polygon([(l / 2, 0), (l, toit), (l, hh), (0, hh), (0, toit)], fill=255)
    ep = t * 0.05
    liseré = [(l / 2, ep * 1.9), (l - ep, toit + ep * .55), (l - ep, hh - ep),
              (ep, hh - ep), (ep, toit + ep * .55)]
    d.line(liseré + [liseré[0]], fill=0, width=int(ep * .45), joint="curve")
    _texte_centre(d, l / 2, hh * 0.47, "FAIT", t * 0.17)
    _texte_centre(d, l / 2, hh * 0.69, "MAISON", t * 0.155)
    masque = m.resize((l // SS, hh // SS), Image.LANCZOS)
    logo = Image.new("RGBA", masque.size, (255, 255, 255, 0))
    logo.putalpha(masque)
    return logo


if __name__ == "__main__":
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    dessiner().save(SORTIE, optimize=True)
    print(SORTIE)

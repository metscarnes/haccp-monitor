"""
generer_logos_mentions.py — Dessine les mentions des étiquettes prix.

Sortie : static/img/mentions/<clé>.png — forme blanche + transparence, peinte de la
couleur du texte par l'impression (brother_ql_prix) et l'aperçu (prix_etiquettes.js).
Chaque fichier est rendu à une hauteur de REFERENCE × facteur : le facteur (plus grand
pour AOP/IGP, dont la légende est sous le cercle) est donc dans la taille du fichier.

- AOP, IGP, Label Rouge, Bio (marque AB) : logos officiels de l'INAO (inao.gouv.fr, « Logos et règles
  d'étiquetage »), convertis en une encre par scripts/convertir_logos_officiels.py →
  scripts/sources_mentions/. Dessin non modifié, posé sur une pastille claire ; AOP et
  IGP ont leur sigle écrit en gros dessous (le texte du cercle est illisible en petit).
- Artisanal, Sans nitrite ajouté, Local, Race à viande : pictogramme + texte évidés dans
  une pastille pleine, dans l'esprit du logo « Fait maison ».

Usage : python scripts/generer_logos_mentions.py
"""

import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

RACINE = Path(__file__).resolve().parent.parent
SOURCES = Path(__file__).resolve().parent / "sources_mentions"
SORTIE = RACINE / "static" / "img" / "mentions"
GRAS = str(RACINE / "static" / "fonts" / "system" / "DejaVuSans-Bold.ttf")
NORMAL = str(RACINE / "static" / "fonts" / "system" / "DejaVuSans.ttf")
REFERENCE = 300          # px de haut d'une mention ordinaire (≈ facteur 1)
SS = 4                   # sur-échantillonnage pour des bords lisses


def police(t, gras=True):
    return ImageFont.truetype(GRAS if gras else NORMAL, max(6, int(t)))


# ── Pictogrammes (dessinés en 255 sur un masque, dans une boîte s×s) ──────────
def picto_vache(d, x, y, s, f=255, fond=0):
    """Tête de bovin de face : cornes, oreilles, museau."""
    cx = x + s / 2
    # cornes
    d.line([(cx - s * .30, y + s * .30), (cx - s * .42, y + s * .12), (cx - s * .34, y + s * .02)], fill=f, width=int(s * .09), joint="curve")
    d.line([(cx + s * .30, y + s * .30), (cx + s * .42, y + s * .12), (cx + s * .34, y + s * .02)], fill=f, width=int(s * .09), joint="curve")
    # oreilles
    d.polygon([(cx - s * .28, y + s * .34), (cx - s * .50, y + s * .30), (cx - s * .30, y + s * .46)], fill=f)
    d.polygon([(cx + s * .28, y + s * .34), (cx + s * .50, y + s * .30), (cx + s * .30, y + s * .46)], fill=f)
    # tête
    d.polygon([(cx - s * .30, y + s * .24), (cx + s * .30, y + s * .24), (cx + s * .22, y + s * .78),
               (cx - s * .22, y + s * .78)], fill=f)
    d.ellipse([cx - s * .26, y + s * .66, cx + s * .26, y + s * .98], fill=f)
    # naseaux + yeux (évidés)
    r = s * .045
    for dx in (-.10, .10):
        d.ellipse([cx + s * dx - r, y + s * .84 - r, cx + s * dx + r, y + s * .84 + r], fill=fond)
    for dx in (-.15, .15):
        d.ellipse([cx + s * dx - r, y + s * .44 - r, cx + s * dx + r, y + s * .44 + r], fill=fond)


def picto_pin(d, x, y, s, f=255, fond=0):
    """Repère de carte (local)."""
    cx, r = x + s / 2, s * .32
    cy = y + s * .36
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=f)
    d.polygon([(cx - r * .82, cy + r * .55), (cx + r * .82, cy + r * .55), (cx, y + s * .98)], fill=f)
    ri = r * .42
    d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=fond)


def picto_couperet(d, x, y, s, f=255, fond=0):
    """Feuille de boucher (artisanal)."""
    ang = math.radians(-35)
    def rot(px, py):
        cx, cy = x + s / 2, y + s / 2
        px, py = px - cx, py - cy
        return (cx + px * math.cos(ang) - py * math.sin(ang), cy + px * math.sin(ang) + py * math.cos(ang))
    # lame
    lame = [(x + s * .05, y + s * .30), (x + s * .62, y + s * .30), (x + s * .62, y + s * .72), (x + s * .05, y + s * .72)]
    d.polygon([rot(*p) for p in lame], fill=f)
    trou = (x + s * .16, y + s * .42)
    tx, ty = rot(*trou)
    rt = s * .055
    d.ellipse([tx - rt, ty - rt, tx + rt, ty + rt], fill=fond)
    # manche
    manche = [(x + s * .62, y + s * .40), (x + s * .98, y + s * .40), (x + s * .98, y + s * .58), (x + s * .62, y + s * .58)]
    d.polygon([rot(*p) for p in manche], fill=f)


def picto_feuille(d, x, y, s, f=255, fond=0):
    """Feuille (sans nitrite ajouté)."""
    cx, cy = x + s / 2, y + s / 2
    d.ellipse([x + s * .12, y + s * .05, x + s * .88, y + s * .80], fill=f)
    d.polygon([(x + s * .16, y + s * .55), (x + s * .5, y + s * 1.0), (x + s * .84, y + s * .55)], fill=f)
    d.line([(cx, y + s * .22), (cx, y + s * .92)], fill=fond, width=max(1, int(s * .06)))
    for k in (0.38, 0.56, 0.74):
        d.line([(cx, y + s * k), (cx - s * .2, y + s * (k - .14))], fill=fond, width=max(1, int(s * .05)))
        d.line([(cx, y + s * k), (cx + s * .2, y + s * (k - .14))], fill=fond, width=max(1, int(s * .05)))


# ── Pastilles ─────────────────────────────────────────────────────────────────
def pastille(texte, picto, h, lignes=None):
    """Pastille pleine arrondie : pictogramme + texte évidés. Renvoie un masque."""
    lignes = lignes or [texte]
    f = police(h * (0.40 if len(lignes) == 1 else 0.30))
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    tw = max(tmp.textlength(l, font=f) for l in lignes)
    pad = h * .22
    ps = h * .70 if picto else 0
    w = int(pad + (ps + pad * .6 if picto else 0) + tw + pad)
    m = Image.new("L", (w, int(h)), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h * .22, fill=255)
    x = pad
    if picto:
        picto(d, x, (h - ps) / 2, ps, f=0, fond=255)
        x += ps + pad * .6
    asc, desc = f.getmetrics()
    lh = asc + desc
    y = (h - lh * len(lignes)) / 2
    for l in lignes:
        d.text((x, y), l, font=f, fill=0)
        y += lh
    return m


def logo_officiel(cle, h, legende=None):
    """Logo officiel (une encre) sur pastille claire : masque = pastille moins l'encre du
    logo. `legende` : sigle écrit en gros sous le logo (AOP / IGP, illisibles en petit)."""
    logo = Image.open(SOURCES / f"{cle}.png").getchannel("A")
    pad = h * .06
    hl = h * .27 if legende else 0              # hauteur réservée à la légende
    lh = int(h - 2 * pad - hl)
    lw = int(logo.width * lh / logo.height)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    trou = Image.new("L", (1, 1), 0)
    f = police(hl * .95) if legende else None
    tw = ImageDraw.Draw(trou).textlength(legende, font=f) if legende else 0
    w = int(max(lw, tw) + 2 * pad)
    m = Image.new("L", (w, int(h)), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=h * .10, fill=255)
    trou = Image.new("L", m.size, 0)
    trou.paste(logo, (int((w - lw) / 2), int(pad)))
    if legende:
        d = ImageDraw.Draw(trou)
        g, hh, dr, b = d.textbbox((0, 0), legende, font=f)
        y_haut = pad + lh + (hl - (b - hh)) / 2
        d.text(((w - (dr - g)) / 2 - g, y_haut - hh), legende, font=f, fill=255)
    return ImageChops.subtract(m, trou)



# clé → (dessin(h), facteur de hauteur)
MENTIONS = {
    "aop":          (lambda h: logo_officiel("aop", h, "AOP"), 1.6),
    "igp":          (lambda h: logo_officiel("igp", h, "IGP"), 1.6),
    "label_rouge":  (lambda h: logo_officiel("label_rouge", h), 1.1),
    "bio":          (lambda h: logo_officiel("bio", h), 1.4),
    "artisanal":    (lambda h: pastille("ARTISANAL", picto_couperet, h), 1.0),
    "sans_nitrite": (lambda h: pastille("", picto_feuille, h, ["SANS NITRITE", "AJOUTÉ"]), 1.0),
    "local":        (lambda h: pastille("LOCAL", picto_pin, h), 1.0),
    "race_viande":  (lambda h: pastille("", picto_vache, h, ["RACE", "À VIANDE"]), 1.0),
}


if __name__ == "__main__":
    SORTIE.mkdir(parents=True, exist_ok=True)
    for cle, (dessin, facteur) in MENTIONS.items():
        masque = dessin(REFERENCE * facteur * SS)
        masque = masque.resize((round(masque.width / SS), round(masque.height / SS)), Image.LANCZOS)
        logo = Image.new("RGBA", masque.size, (255, 255, 255, 0))
        logo.putalpha(masque)
        logo.save(SORTIE / f"{cle}.png", optimize=True)
        print(cle, logo.size)

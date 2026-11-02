"""Convertit les logos officiels INAO (couleur) en une seule encre pour l'imprimante
thermique : partie foncée (rouge, bleu) = encre noire, partie claire (jaune, blanc) =
papier. Le dessin n'est pas modifié. Sortie : PNG RGBA, encre noire opaque sur fond
transparent (l'étiquette pose dessous une pastille blanche sur fond noir).

Usage : python -I scripts/convertir_logos_officiels.py <dossier des fichiers INAO> scripts/sources_mentions
Sources : https://www.inao.gouv.fr/logos-regles-etiquetage (AOP.jpg, IGP.jpg, LR.png).
"""
import sys
from pathlib import Path

from PIL import Image, ImageFilter

SRC, DST = Path(sys.argv[1]), Path(sys.argv[2])
DST.mkdir(parents=True, exist_ok=True)
SEUIL_VERT = 150      # canal vert : rouge ≈ 60, bleu ≈ 80, jaune ≈ 220, blanc 255

for fichier, cle in (("AOP.jpg", "aop"), ("IGP.jpg", "igp"), ("LR.png", "label_rouge")):
    im = Image.open(SRC / fichier).convert("RGBA")
    fond = Image.new("RGBA", im.size, (255, 255, 255, 255))
    im = Image.alpha_composite(fond, im).convert("RGB")
    # agrandi avant seuillage : bords plus propres (sources 318 px pour AOP/IGP)
    k = max(1, round(1200 / max(im.size)))
    im = im.resize((im.width * k, im.height * k), Image.LANCZOS)
    vert = im.getchannel("G").filter(ImageFilter.GaussianBlur(k * 0.4))
    encre = vert.point(lambda v: 255 if v < SEUIL_VERT else 0)
    boite = encre.getbbox()
    encre = encre.crop(boite)
    sortie = Image.new("RGBA", encre.size, (0, 0, 0, 0))
    sortie.putalpha(encre)
    sortie.save(DST / f"{cle}.png", optimize=True)
    print(cle, sortie.size)

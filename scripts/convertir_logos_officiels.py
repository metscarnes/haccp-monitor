"""Convertit les logos officiels INAO (couleur) en une seule encre pour l'imprimante
thermique : partie foncée (rouge, bleu, vert du logo AB) = encre noire, partie claire
(jaune, blanc) = papier. Le dessin n'est pas modifié. Sortie : PNG RGBA, encre noire opaque sur fond
transparent (l'étiquette pose dessous une pastille blanche sur fond noir).

Usage : python -I scripts/convertir_logos_officiels.py <dossier des fichiers INAO> scripts/sources_mentions
Sources : https://www.inao.gouv.fr/logos-regles-etiquetage (AOP.jpg, IGP.jpg, LR.png, AB.jpg).
"""
import sys
from pathlib import Path

from PIL import Image, ImageFilter

SRC, DST = Path(sys.argv[1]), Path(sys.argv[2])
DST.mkdir(parents=True, exist_ok=True)
SEUIL = 150           # sur le canal choisi : encre en dessous, papier au-dessus

# Canal qui sépare l'encre du papier : vert pour AOP/IGP/LR (rouge ≈ 60, bleu ≈ 80,
# jaune ≈ 220, blanc 255) ; rouge pour AB (vert du logo ≈ 50, blanc 255).
for fichier, cle, canal in (("AOP.jpg", "aop", "G"), ("IGP.jpg", "igp", "G"),
                            ("LR.png", "label_rouge", "G"), ("AB.jpg", "bio", "R")):
    im = Image.open(SRC / fichier).convert("RGBA")
    fond = Image.new("RGBA", im.size, (255, 255, 255, 255))
    im = Image.alpha_composite(fond, im).convert("RGB")
    # agrandi avant seuillage : bords plus propres (sources 318 px pour AOP/IGP)
    k = max(1, round(1200 / max(im.size)))
    im = im.resize((im.width * k, im.height * k), Image.LANCZOS)
    valeurs = im.getchannel(canal).filter(ImageFilter.GaussianBlur(k * 0.4))
    encre = valeurs.point(lambda v: 255 if v < SEUIL else 0)
    boite = encre.getbbox()
    encre = encre.crop(boite)
    sortie = Image.new("RGBA", encre.size, (0, 0, 0, 0))
    sortie.putalpha(encre)
    sortie.save(DST / f"{cle}.png", optimize=True)
    print(cle, sortie.size)

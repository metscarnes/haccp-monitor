"""
proto_ocr_bl.py — Prototype OCR de bon de livraison (BL)

But : juger la qualité de lecture (DLC + N° de lot + articles) par Claude vision
AVANT de s'engager dans l'intégration complète. Standalone, n'interfère pas avec l'app.

Usage :
    # 1. Installer le SDK (une fois) :
    pip install anthropic

    # 2. Renseigner la clé API (une fois par session shell) :
    #    PowerShell :  $env:ANTHROPIC_API_KEY = "sk-ant-..."
    #    Bash :        export ANTHROPIC_API_KEY="sk-ant-..."

    # 3. Lancer sur une vraie photo de BL :
    python scripts/proto_ocr_bl.py chemin/vers/photo_bl.jpg

    # Plusieurs pages d'un même BL :
    python scripts/proto_ocr_bl.py page1.jpg page2.jpg

Sortie : le JSON extrait + le coût réel de l'appel API.
"""

import base64
import io
import json
import os
import sys
import time
from pathlib import Path

try:
    import anthropic
except ImportError:
    sys.exit("Le SDK n'est pas installé. Lance :  pip install anthropic")

from PIL import Image, ImageOps

# --- Paramètres -----------------------------------------------------------

MODEL = "claude-sonnet-4-6"          # bon rapport qualité/prix pour extraction structurée
MAX_SIDE = 1600                       # côté max de l'image (px) ; BL imprimés = texte fin
JPEG_QUALITY = 85

# Tarifs Sonnet 4.6 ($/million de tokens) — pour estimer le coût réel
PRIX_INPUT_PAR_MTOK = 3.00
PRIX_OUTPUT_PAR_MTOK = 15.00

# --- Compression image (proche de l'app, mais un peu plus haute déf) -------

def compresser(chemin: Path) -> bytes:
    img = Image.open(chemin)
    img = ImageOps.exif_transpose(img)          # respecte l'orientation du téléphone
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_SIDE:
        if w >= h:
            img = img.resize((MAX_SIDE, int(h * MAX_SIDE / w)), Image.LANCZOS)
        else:
            img = img.resize((int(w * MAX_SIDE / h), MAX_SIDE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


# --- Prompt d'extraction ---------------------------------------------------

SCHEMA = {
    "type": "object",
    "properties": {
        "fournisseur": {"type": ["string", "null"], "description": "Nom du fournisseur émetteur du BL"},
        "numero_bl": {"type": ["string", "null"], "description": "Numéro du bon de livraison"},
        "date_bl": {"type": ["string", "null"], "description": "Date du BL au format AAAA-MM-JJ si lisible"},
        "lignes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "designation": {"type": "string", "description": "Libellé de l'article tel qu'écrit sur le BL"},
                    "reference": {"type": ["string", "null"], "description": "Code/référence article fournisseur si présent"},
                    "numero_lot": {"type": ["string", "null"], "description": "Numéro de lot de l'article"},
                    "dlc": {"type": ["string", "null"], "description": "DLC au format AAAA-MM-JJ. null si absente"},
                    "dluo": {"type": ["string", "null"], "description": "DLUO/DDM au format AAAA-MM-JJ. null si absente"},
                    "poids_kg": {"type": ["number", "null"], "description": "Poids en kg si indiqué"},
                    "quantite": {"type": ["number", "null"], "description": "Quantité/nombre de colis si indiqué"},
                    "confiance": {
                        "type": "string",
                        "enum": ["haute", "moyenne", "basse"],
                        "description": "Ton niveau de confiance dans la lecture de CETTE ligne (lot + DLC)",
                    },
                },
                "required": ["designation", "numero_lot", "dlc", "dluo", "poids_kg", "quantite", "confiance", "reference"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["fournisseur", "numero_bl", "date_bl", "lignes"],
    "additionalProperties": False,
}

INSTRUCTIONS = """Tu es un assistant de saisie pour une boucherie. On te donne la photo d'un bon de livraison (BL) d'un fournisseur de viande.

Extrais, ligne par article, les informations de traçabilité. Concentre-toi en priorité sur :
- la désignation de l'article
- le NUMÉRO DE LOT
- la DLC (date limite de consommation) — c'est l'information critique

Règles :
- Une ligne du tableau = un article = un objet dans "lignes". N'invente jamais d'article.
- Les dates : convertis tout au format AAAA-MM-JJ. Si une date est ambiguë (ex. 03/04 sans année), garde l'année du BL ou laisse null plutôt que de deviner.
- Distingue DLC (consommer jusqu'au) et DLUO/DDM (à consommer de préférence avant) : ne mets pas une DLUO dans le champ dlc.
- Si une information n'est pas lisible ou absente, mets null. Ne devine pas.
- Pour chaque ligne, indique ta "confiance" sur la lecture du lot et de la DLC (haute/moyenne/basse). Sois honnête : une saisie HACCP erronée est pire qu'un champ à vérifier.
- Ignore les totaux, conditions de vente, mentions légales en bas de page.

Réponds uniquement via le format structuré demandé."""


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage : python scripts/proto_ocr_bl.py <photo_bl.jpg> [page2.jpg ...]")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Variable ANTHROPIC_API_KEY absente. Renseigne ta clé API d'abord "
                 "(voir l'en-tête du fichier).")

    chemins = [Path(p) for p in sys.argv[1:]]
    for c in chemins:
        if not c.exists():
            sys.exit(f"Fichier introuvable : {c}")
        if c.stat().st_size < 5_000:
            print(f"  ⚠️  {c.name} fait {c.stat().st_size} octets — c'est probablement "
                  f"un placeholder, pas une vraie photo. La lecture échouera.")

    # Construire le contenu : toutes les images puis l'instruction
    contenu = []
    for c in chemins:
        jpeg = compresser(c)
        b64 = base64.standard_b64encode(jpeg).decode()
        contenu.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
        })
        print(f"  • {c.name} → {len(jpeg)//1024} Ko envoyés")
    contenu.append({"type": "text", "text": INSTRUCTIONS})

    client = anthropic.Anthropic()

    print(f"\n  Envoi à {MODEL}…\n")
    t0 = time.time()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        messages=[{"role": "user", "content": contenu}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    dt = time.time() - t0

    # Le format json_schema garantit que le 1er bloc texte est du JSON valide
    texte = next(b.text for b in resp.content if b.type == "text")
    data = json.loads(texte)

    print("=" * 70)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("=" * 70)

    # Résumé lisible
    lignes = data.get("lignes", [])
    print(f"\n  Fournisseur : {data.get('fournisseur')}   "
          f"BL n° {data.get('numero_bl')}   du {data.get('date_bl')}")
    print(f"  {len(lignes)} article(s) extrait(s) :")
    for i, lg in enumerate(lignes, 1):
        flag = {"haute": "✓", "moyenne": "≈", "basse": "⚠"}.get(lg.get("confiance"), "?")
        print(f"    {flag} {i:>2}. {lg.get('designation','?')[:40]:<40} "
              f"lot={lg.get('numero_lot') or '—':<14} DLC={lg.get('dlc') or '—'}")

    # Coût réel
    u = resp.usage
    cout = (u.input_tokens * PRIX_INPUT_PAR_MTOK
            + u.output_tokens * PRIX_OUTPUT_PAR_MTOK) / 1_000_000
    print(f"\n  Tokens : {u.input_tokens} entrée + {u.output_tokens} sortie")
    print(f"  Coût de cet appel : ${cout:.4f}  (~{cout*0.92:.4f} €)")
    print(f"  Temps de réponse : {dt:.1f} s")


if __name__ == "__main__":
    main()

"""
ocr_bl.py — Extraction OCR des bons de livraison (BL) via Claude vision.

Lit une ou plusieurs images de BL (JPEG déjà compressé par l'app) et renvoie
un dict structuré : fournisseur, n° BL, date, et une ligne par article avec
désignation / numéro de lot / DLC / DLUO / poids, plus un niveau de confiance.

Utilisé par l'endpoint POST /api/receptions/{id}/ocr-bl.

Garde-fou HACCP : le prompt interdit de deviner une date. Tout champ illisible
revient à null, et chaque ligne porte un niveau de confiance que l'écran de
validation côté front utilise pour signaler ce qui doit être vérifié.
"""

import base64
import json
import logging
import os

logger = logging.getLogger(__name__)

# Modèle par défaut : bon compromis fiabilité/prix pour des BL imprimés.
# Surchargé par la variable d'environnement OCR_MODEL si présente.
MODEL = os.environ.get("OCR_MODEL", "claude-sonnet-4-6")

# Tarifs ($/million de tokens) pour journaliser le coût réel de chaque appel.
_PRIX = {
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5":  (1.00, 5.00),
    "claude-opus-4-8":   (5.00, 25.00),
}

_SCHEMA = {
    "type": "object",
    "properties": {
        "fournisseur": {"type": ["string", "null"]},
        "numero_bl":   {"type": ["string", "null"]},
        "date_bl":     {"type": ["string", "null"]},
        "lignes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "designation": {"type": "string"},
                    "reference":   {"type": ["string", "null"]},
                    "numero_lot":  {"type": ["string", "null"]},
                    "dlc":         {"type": ["string", "null"]},
                    "dluo":        {"type": ["string", "null"]},
                    "poids_kg":    {"type": ["number", "null"]},
                    "quantite":    {"type": ["number", "null"]},
                    "confiance":   {"type": "string", "enum": ["haute", "moyenne", "basse"]},
                },
                "required": ["designation", "reference", "numero_lot", "dlc",
                             "dluo", "poids_kg", "quantite", "confiance"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["fournisseur", "numero_bl", "date_bl", "lignes"],
    "additionalProperties": False,
}

_INSTRUCTIONS = """Tu es un assistant de saisie pour une boucherie. On te donne la ou les photo(s) d'un bon de livraison (BL) d'un fournisseur de viande.

Extrais, ligne par article, les informations de traçabilité. Concentre-toi en priorité sur :
- la désignation de l'article
- le NUMÉRO DE LOT
- la DLC (date limite de consommation) — c'est l'information critique

Règles :
- Une ligne du tableau = un article = un objet dans "lignes". N'invente jamais d'article.
- Les dates : convertis tout au format AAAA-MM-JJ. Si une date est ambiguë (ex. 03/04 sans année), garde l'année du BL ; si tu ne peux pas la déterminer, mets null plutôt que de deviner.
- Distingue DLC (consommer jusqu'au) et DLUO/DDM (à consommer de préférence avant) : ne mets jamais une DLUO dans le champ dlc.
- Si une information n'est pas lisible ou absente, mets null. Ne devine pas.
- Pour chaque ligne, indique ta "confiance" sur la lecture du lot et de la DLC (haute / moyenne / basse). Sois honnête : une saisie HACCP erronée est pire qu'un champ laissé à vérifier.
- Si plusieurs images sont fournies, ce sont les pages d'un même BL : fusionne-les en une seule liste d'articles.
- Ignore les totaux, conditions de vente, mentions légales en bas de page.

Réponds uniquement via le format structuré demandé."""


class OCRError(Exception):
    """Erreur fonctionnelle d'OCR (clé absente, appel API échoué, etc.)."""


def extraire_bl(images_jpeg: list[bytes]) -> dict:
    """Envoie les images du BL à Claude et renvoie le dict structuré.

    Args:
        images_jpeg: liste d'images JPEG (bytes), une par page de BL.

    Returns:
        dict conforme à _SCHEMA, enrichi d'un bloc "_meta" (modèle, coût, tokens).

    Raises:
        OCRError: si la clé API est absente, ou si l'appel/réponse échoue.
    """
    if not images_jpeg:
        raise OCRError("Aucune image de BL à analyser.")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or api_key == "sk-ant-REMPLACE-MOI":
        raise OCRError(
            "Clé API Anthropic non configurée. Renseigne ANTHROPIC_API_KEY dans le fichier .env."
        )

    try:
        import anthropic
    except ImportError:
        raise OCRError("Le paquet 'anthropic' n'est pas installé (pip install anthropic).")

    contenu = []
    for jpeg in images_jpeg:
        contenu.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64.standard_b64encode(jpeg).decode(),
            },
        })
    contenu.append({"type": "text", "text": _INSTRUCTIONS})

    client = anthropic.Anthropic(api_key=api_key)
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=8000,
            messages=[{"role": "user", "content": contenu}],
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        )
    except anthropic.APIError as e:
        logger.error("Appel OCR échoué : %s", e)
        raise OCRError(f"Appel à l'API Claude échoué : {e}")

    try:
        texte = next(b.text for b in resp.content if b.type == "text")
        data = json.loads(texte)
    except (StopIteration, json.JSONDecodeError) as e:
        logger.error("Réponse OCR illisible : %s", e)
        raise OCRError("Réponse de l'OCR illisible.")

    # Coût réel, pour journalisation et suivi
    prix_in, prix_out = _PRIX.get(MODEL, (3.00, 15.00))
    u = resp.usage
    cout = (u.input_tokens * prix_in + u.output_tokens * prix_out) / 1_000_000
    logger.info(
        "OCR BL : %d ligne(s), modèle=%s, %d+%d tokens, coût≈$%.4f",
        len(data.get("lignes", [])), MODEL, u.input_tokens, u.output_tokens, cout,
    )

    data["_meta"] = {
        "modele": MODEL,
        "tokens_entree": u.input_tokens,
        "tokens_sortie": u.output_tokens,
        "cout_usd": round(cout, 4),
    }
    return data

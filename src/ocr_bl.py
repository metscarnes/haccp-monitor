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
        "fournisseur":  {"type": ["string", "null"]},
        "numero_bl":    {"type": ["string", "null"]},
        "date_bl_brut": {"type": ["string", "null"]},
        "lignes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "designation": {"type": "string"},
                    "reference":   {"type": ["string", "null"]},
                    "numero_lot":  {"type": ["string", "null"]},
                    "dlc_brut":    {"type": ["string", "null"]},
                    "dluo_brut":   {"type": ["string", "null"]},
                    "poids_kg":    {"type": ["number", "null"]},
                    "quantite":    {"type": ["number", "null"]},
                    "confiance":   {"type": "string", "enum": ["haute", "moyenne", "basse"]},
                },
                "required": ["designation", "reference", "numero_lot", "dlc_brut",
                             "dluo_brut", "poids_kg", "quantite", "confiance"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["fournisseur", "numero_bl", "date_bl_brut", "lignes"],
    "additionalProperties": False,
}

_INSTRUCTIONS = """Tu es un assistant de saisie pour une boucherie. On te donne la ou les photo(s) d'un bon de livraison (BL) d'un fournisseur de viande. Chaque fournisseur a sa propre mise en page : n'en présume aucune, lis ce que tu vois.

Extrais, article par article, les informations de traçabilité. Pour chaque article du BL, donne un objet dans "lignes" avec :
- designation : le libellé de l'article
- numero_lot : le numéro de lot s'il est indiqué pour cet article
- dlc_brut / dluo_brut : la DLC / la DLUO (DDM) de cet article
- poids_kg : le poids livré (en kg) de cet article
- quantite : le nombre d'unités/pièces livrées

POINT CRITIQUE — appariement DLC ↔ article :
Sur certains BL, le lot et la DLC d'un article sont écrits sur une LIGNE SÉPARÉE (souvent juste en dessous de l'article, parfois préfixée "lot"). Cette DLC/ce lot appartiennent à l'article AUQUEL ILS SE RAPPORTENT visuellement (le plus proche, en général juste au-dessus) — surtout PAS à l'article suivant. Vérifie l'alignement avant d'associer : ne décale jamais une DLC d'un article à l'autre. En cas de doute sur l'appariement, baisse la "confiance" de la ligne plutôt que de risquer une erreur.

POINT CRITIQUE — plusieurs lots / DLC pour un même article :
Un même article peut être livré en PLUSIEURS lots, chacun avec son propre numéro de lot et parfois sa propre DLC (par ex. "Côte de bœuf" avec lot A DLC 12/07 et lot B DLC 15/07). Dans ce cas, produis UNE LIGNE PAR COUPLE (lot, DLC) : répète la même "designation", mais mets le bon "numero_lot" et la bonne "dlc_brut"/"dluo_brut" sur chacune. Répartis aussi le poids/la quantité par lot si le BL les distingue, sinon laisse null sur les lignes où ce n'est pas précisé. Ne fusionne JAMAIS plusieurs lots dans une seule ligne et n'invente pas de lot qui n'est pas écrit.

Règles générales :
- Un couple (article, lot) = un objet dans "lignes". Un article à lot unique = une seule ligne ; un article à plusieurs lots = une ligne par lot. N'invente jamais de ligne, n'en oublie aucune.
- DATES — recopie chaque date EXACTEMENT comme écrite, caractère pour caractère, dans "dlc_brut" / "dluo_brut" / "date_bl_brut". NE CONVERTIS RIEN, ne réordonne pas jour/mois. "07/12/26" → mets exactement "07/12/26". La conversion est faite ensuite par le programme.
- Distingue DLC (consommer jusqu'au) et DLUO/DDM (à consommer de préférence avant) : ne mets jamais une DLUO dans dlc_brut.
- Si une information est illisible ou absente, mets null. Ne devine pas.
- "confiance" (haute/moyenne/basse) sur la lecture du lot ET de la DLC de la ligne. Sois honnête : une saisie HACCP erronée est pire qu'un champ à vérifier.
- Plusieurs images = pages d'un même BL : fusionne en une seule liste d'articles.
- Ignore les totaux, conditions de vente, mentions légales.

Réponds uniquement via le format structuré demandé."""


class OCRError(Exception):
    """Erreur fonctionnelle d'OCR (clé absente, appel API échoué, etc.)."""


import re
from datetime import date

# Sépare une date écrite en chiffres : 07/12/26, 07-12-2026, 07.12.26, 7/12...
_SEP = re.compile(r"[/\-.\s]+")


def _parse_date_fr(brut: str | None, annee_defaut: int | None = None) -> tuple[str | None, str | None]:
    """Convertit une date française BRUTE (jour en premier) en (iso, fr).

    Le jour est TOUJOURS le premier nombre (convention française), donc plus
    aucune inversion jour/mois possible — c'est tout l'intérêt par rapport à
    laisser le modèle convertir.

    Args:
        brut: la date telle qu'écrite sur le BL ("07/12/26", "7 déc", ...).
        annee_defaut: année à utiliser si le BL n'écrit pas l'année (jj/mm seul).

    Returns:
        (iso, fr) = ("2026-12-07", "07/12/2026"), ou (None, None) si illisible.
    """
    if not brut:
        return None, None

    nums = [int(n) for n in re.findall(r"\d+", brut)]
    # On attend jour, mois, [année]. Sans au moins jour+mois, on ne devine pas.
    if len(nums) < 2:
        return None, None

    jour, mois = nums[0], nums[1]
    if len(nums) >= 3:
        annee = nums[2]
        if annee < 100:           # "26" -> 2026
            annee += 2000
    elif annee_defaut:
        annee = annee_defaut
    else:
        return None, None         # année absente et pas de défaut : on s'abstient

    try:
        d = date(annee, mois, jour)
    except ValueError:
        return None, None         # 31/02, mois=13, etc. : date impossible
    return d.isoformat(), f"{d.day:02d}/{d.month:02d}/{d.year}"


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

    # Conversion des dates côté Python (jour en premier = convention française),
    # pour éliminer toute inversion jour/mois que le modèle pourrait faire.
    # On ajoute aussi un drapeau "dlc_suspecte" : une DLC antérieure à la date du
    # BL est forcément une erreur de lecture → à vérifier à l'écran de validation.
    date_bl_iso, date_bl_fr = _parse_date_fr(data.get("date_bl_brut"))
    data["date_bl"] = date_bl_iso
    data["date_bl_fr"] = date_bl_fr
    annee_bl = int(date_bl_iso[:4]) if date_bl_iso else None
    jour_bl = date.fromisoformat(date_bl_iso) if date_bl_iso else None

    for ligne in data.get("lignes", []):
        dlc_iso, dlc_fr = _parse_date_fr(ligne.get("dlc_brut"), annee_bl)
        dluo_iso, dluo_fr = _parse_date_fr(ligne.get("dluo_brut"), annee_bl)
        ligne["dlc"] = dlc_iso
        ligne["dlc_fr"] = dlc_fr
        ligne["dluo"] = dluo_iso
        ligne["dluo_fr"] = dluo_fr

        # Vérifs GÉNÉRIQUES de cohérence (valables pour TOUS les fournisseurs,
        # indépendantes de la mise en page). Elles ne corrigent pas la DLC : elles
        # signalent les lignes à revérifier à l'écran de validation.
        alerte = None
        if dlc_iso and jour_bl:
            d = date.fromisoformat(dlc_iso)
            if d < jour_bl:
                alerte = "DLC antérieure à la livraison"
            elif (d - jour_bl).days > 730:
                alerte = "DLC très lointaine (> 2 ans) — à vérifier"

        ligne["dlc_suspecte"] = alerte is not None
        ligne["alerte"] = alerte

    data["_meta"] = {
        "modele": MODEL,
        "tokens_entree": u.input_tokens,
        "tokens_sortie": u.output_tokens,
        "cout_usd": round(cout, 4),
    }
    return data

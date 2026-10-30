"""
ocr_facture.py — Extraction OCR d'une FACTURE fournisseur via Claude vision.

Distinct de ocr_bl.py : un bon de livraison porte lot/DLC/poids (traçabilité HACCP),
une FACTURE porte la valeur — lignes chiffrées, LIGNES ANNEXES (transport, taxes,
consignes, remises), VENTILATION DE TVA PAR TAUX et TOTAUX (HT/TVA/TTC). C'est ce
schéma-là qu'on extrait ici, pour remplir exactement les champs qui font boucler la
facture (module facture étape 2).

Ordre d'usage (routes_achats) : on tente d'abord Factur-X (facturx_reader, XML
embarqué, fiable à 100 %) ; l'OCR n'est le repli QUE pour les PDF/images scannés
sans XML. Le résultat suit le MÊME format que facturx_reader.parser_facturx pour
que l'écran de rapprochement soit identique quelle que soit la source.

Leçon du projet (OCR BL) : la fiabilité d'extraction vient du PROMPT, pas du schéma.
Un champ ["number","null"] AUTORISE null, il ne le force pas — d'où des instructions
explicites, colonne par colonne.
"""

import base64
import json
import logging
import os

logger = logging.getLogger(__name__)

MODEL = os.environ.get("OCR_FACTURE_MODEL", "claude-sonnet-5-5")
EFFORT = os.environ.get("OCR_FACTURE_EFFORT", "low")

# Prix par million de tokens (entrée, sortie), en USD.
_PRIX = {
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5":  (0.10, 0.50),
    "claude-sonnet-5":   (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5":  (1.00, 5.00),
    "claude-opus-4-8":   (5.00, 25.00),
}

_SCHEMA = {
    "type": "object",
    "properties": {
        "fournisseur":    {"type": ["string", "null"]},
        "numero_facture": {"type": ["string", "null"]},
        "date_facture_brut": {"type": ["string", "null"]},
        # 'facture' | 'avoir' (cadré par l'instruction, normalisé en Python)
        "type_document":  {"type": "string"},
        "lignes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "designation":   {"type": "string"},
                    "reference":     {"type": ["string", "null"]},
                    "quantite":      {"type": ["number", "null"]},
                    # Poids livré, lu EN PLUS de la quantité : permet le contrôle
                    # prix × base = montant (cf. _controler_base_ligne).
                    "poids_kg":      {"type": ["number", "null"]},
                    "prix_unitaire": {"type": ["number", "null"]},
                    "unite_prix":    {"type": ["string", "null"]},  # kg|piece|colis
                    "montant_ht":    {"type": ["number", "null"]},
                    "tva_pct":       {"type": ["number", "null"]},
                    "confiance":     {"type": "string", "enum": ["haute", "moyenne", "basse"]},
                },
                "required": ["designation", "reference", "quantite", "poids_kg", "prix_unitaire",
                             "unite_prix", "montant_ht", "tva_pct", "confiance"],
                "additionalProperties": False,
            },
        },
        "annexes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "designation": {"type": "string"},
                    # transport|taxe|consigne|remise (cadré par l'instruction)
                    "type_ligne":  {"type": ["string", "null"]},
                    "montant_ht":  {"type": ["number", "null"]},
                    "tva_pct":     {"type": ["number", "null"]},
                },
                "required": ["designation", "type_ligne", "montant_ht", "tva_pct"],
                "additionalProperties": False,
            },
        },
        "recap_tva": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "taux":    {"type": "number"},
                    "base_ht": {"type": "number"},
                    "tva":     {"type": "number"},
                },
                "required": ["taux", "base_ht", "tva"],
                "additionalProperties": False,
            },
        },
        "total_ht":  {"type": ["number", "null"]},
        "total_tva": {"type": ["number", "null"]},
        "total_ttc": {"type": ["number", "null"]},
    },
    "required": ["fournisseur", "numero_facture", "date_facture_brut", "type_document",
                 "lignes", "annexes", "recap_tva", "total_ht", "total_tva", "total_ttc"],
    "additionalProperties": False,
}

_INSTRUCTIONS = """Tu es un assistant de saisie comptable pour une boucherie. On te donne la ou les photo(s)/page(s) d'une FACTURE (ou d'un avoir) d'un fournisseur. Chaque fournisseur a sa propre mise en page : n'en présume aucune, lis ce que tu vois.

Ton objectif : extraire tout ce qui permet de VÉRIFIER LE MONTANT FINAL. Contrairement à un bon de livraison, une facture porte des lignes chiffrées, des frais annexes, la TVA et les totaux. Extrais :

ENTÊTE :
- fournisseur : le nom du fournisseur (l'émetteur de la facture)
- numero_facture : le numéro de la facture (souvent "Facture n°", "N°", "Invoice")
- date_facture_brut : la date de la facture, RECOPIÉE EXACTEMENT comme écrite (ne convertis pas)
- type_document : "facture" en général, "avoir" si le document est un avoir / une note de crédit (cherche "AVOIR", "Note de crédit", des montants négatifs systématiques)

LIGNES DE MARCHANDISE (tableau principal), une par article :
- designation : le libellé de l'article
- reference : le code article s'il est indiqué
- quantite : la quantité facturée, celle que MULTIPLIE le prix unitaire : un nombre de kg si le prix est au kilo, un nombre de pièces si le prix est à la pièce, un nombre de colis si le prix est au colis
- poids_kg : le poids livré/facturé en kg s'il est imprimé sur la ligne (même quand le prix est à la pièce), sinon null
- prix_unitaire : le prix d'UNE unité HORS TAXES, tel qu'écrit, sans le symbole €
- unite_prix : à quoi se rapporte le prix → "kg" (prix au kilo), "piece" (à la pièce/unité), "colis" (au colis/carton)
- montant_ht : le montant HORS TAXES total de la ligne
- tva_pct : le taux de TVA de la ligne s'il est indiqué (souvent 5,5 pour l'alimentaire, 20 pour les prestations/frais). Si un code TVA renvoie à un taux en pied de facture, mets ce taux.

LIGNES ANNEXES (ce qui n'est PAS de la marchandise mais compte dans le total) :
Cherche activement, souvent en bas du tableau ou avant les totaux : frais de port/transport, taxes (taxe d'équarrissage, éco-contribution…), consignes (palettes, bacs), remises/ristournes. Pour chacune, un objet dans "annexes" :
- designation : le libellé exact (ex. "Frais de transport", "Taxe équarrissage", "Remise 2%")
- type_ligne : "transport" (port, livraison, franco), "taxe" (toute taxe/contribution), "consigne" (palette/bac/emballage consigné), "remise" (remise, ristourne, escompte — le montant sera NÉGATIF)
- montant_ht : le montant HORS TAXES ; NÉGATIF pour une remise
- tva_pct : le taux de TVA de cette ligne annexe

RÉCAPITULATIF DE TVA (le tableau de ventilation, souvent en pied de facture) :
Pour chaque taux présent, un objet dans "recap_tva" : taux (ex. 5.5), base_ht (base soumise à ce taux), tva (montant de TVA de ce taux). N'ajoute une ligne dans "recap_tva" QUE si tu peux lire les trois valeurs ; sinon n'ajoute rien pour ce taux (pas de valeur inventée).

TOTAUX (en bas de la facture) :
- total_ht : total hors taxes
- total_tva : total de la TVA
- total_ttc : total toutes taxes comprises (le montant à payer, le chiffre en bas de page)

Règles :
- N'invente JAMAIS un chiffre. Si une valeur est illisible ou absente, mets null. Ne devine pas.
- Recopie les nombres tels qu'écrits, point décimal (18,50 → 18.50), sans symbole monétaire.
- Ne recalcule pas : recopie les montants imprimés. Si seul le montant total d'une ligne est écrit, mets-le dans montant_ht et laisse prix_unitaire à null.
- Distingue bien MARCHANDISE (va dans "lignes") et FRAIS/REMISES (va dans "annexes"). Une remise est une annexe à montant négatif.
- Plusieurs pages = une seule facture : fusionne les lignes, ne prends les totaux qu'une fois (ceux de la dernière page / du récapitulatif).
- "confiance" (haute/moyenne/basse) par ligne de marchandise sur la lecture du montant et du prix.
- Vérifie chaque ligne : quantite × prix_unitaire doit redonner montant_ht. Si ça ne colle pas, c'est en général que tu as pris le poids au lieu du nombre de pièces (ou l'inverse) : relis la ligne.

Réponds uniquement via le format structuré demandé."""


# Consignes par fournisseur (mise en page connue), reconnues par nom via
# ocr_bl.cle_fournisseur. Sans elles, l'unité du prix est mal lue (BQT pris pour
# un colis, poids pris pour un nombre de pièces).
_CONSIGNES_FOURNISSEUR = {
    "saveurs": """Document SAVEURS D'ANTOINE (traiteur / charcuterie), 1 à 3 pages. Deux mises en page existent :
- « FACTURE » (jusqu'à début octobre 2026) — colonnes : DESIGNATION PRODUIT | QTE CMD | QTE LIVREE en UCde | QTE LIVREE en UF | UF | PRIX BRUT | REMISES | PRIX NET | Montant H.T | TVA. numero_facture = « N° Pièce » (ex. 010780326).
- « BON DE LIVRAISON » (depuis mi-octobre 2026) — colonnes : DESIGNATION PRODUIT | QTE CDE | PCB | NB COL | NB PIECES | POIDS NET | UF | PRIX | REMISE | PRIX NET | Montant H.T | TVA. numero_facture = « N° Pièce » (ex. 0770580).
Chaque article = code 6 chiffres (reference) + libellé (parfois sur 2 lignes), suivi de sous-lignes « lot / dlc jj/mm/aa / N p. X,XXX kg » : ce ne sont PAS des articles, mais « N p. X,XXX kg » donne le nombre de pièces N et le poids X de l'article (additionne si plusieurs sous-lignes).
LA COLONNE UF DÉCIDE DE L'UNITÉ DU PRIX :
- UF = KG → unite_prix "kg", quantite = le POIDS en kg (POIDS NET ou QTE LIVREE en UF), poids_kg = ce même poids.
- UF = toute autre unité (BQT, PIECE, SCHT, BCL, BTL, SEAU, PLAT, BRAS, PCH, COL…) → unite_prix "piece", quantite = le NOMBRE de pièces (NB PIECES, ou le nombre de « QTE LIVREE en UF », ou N de « N p. »), poids_kg = le poids imprimé. Ex. « Cordon bleu … 2 BQT | 2 | 1 | 2 | 1,800 BQT | 14,950 | 14,950 | 29,90 » → quantite 2, poids_kg 1.8, prix 14.95, piece, montant 29.90 (2 × 14,95), surtout PAS 1,8 × 14,95.
- Le libellé (« BQT 2,5KG », « SCHT 250G », « PCE 3,5KG ») ne décide PAS de l'unité : seule la colonne UF compte. Un article « 1 PIECE » avec UF = KG est au kilo.
prix_unitaire = PRIX NET (un « P » à côté signale une promo, ignore-le). montant_ht = Montant H.T. Le « 1 » collé au montant est le CODE TVA (→ 5,5 % via le récapitulatif), pas un chiffre du montant.
Ignore « Poids : … - Pièces : … », les lignes « BL n° … Votre Commande du … », « Total Colis Expédiés », « Total Poids Net ». Les totaux sont en bas de la dernière page : BASE HT, %TVA, MTT TVA, Net à payer TTC.""",
}


class OCRFactureError(Exception):
    """Erreur fonctionnelle d'OCR facture."""


import re
import unicodedata
from datetime import date


def _parse_date_fr(brut):
    """Convertit une date française BRUTE (jour d'abord) en ISO, ou None."""
    if not brut:
        return None
    nums = [int(n) for n in re.findall(r"\d+", brut)]
    if len(nums) < 3:
        return None
    jour, mois, annee = nums[0], nums[1], nums[2]
    if annee < 100:
        annee += 2000
    try:
        return date(annee, mois, jour).isoformat()
    except ValueError:
        return None


def _normaliser_unite_prix(valeur):
    """Ramène l'unité de prix vers 'kg'|'piece'|'colis', défaut 'kg' (le plus fréquent).

    Recherche par sous-chaîne (pas seulement en début) : « à la pièce », « /pièce »,
    « prix au colis » doivent être reconnus quel que soit le mot qui précède.
    """
    if not valeur:
        return "kg"
    v = str(valeur).strip().lower()
    v = "".join(c for c in unicodedata.normalize("NFD", v) if unicodedata.category(c) != "Mn")
    if "piece" in v or v in ("u", "unite", "unites", "pc", "pce"):
        return "piece"
    if "colis" in v or "carton" in v or "caisse" in v:
        return "colis"
    return "kg"


_TYPES_ANNEXE = ("transport", "taxe", "consigne", "remise")


def _normaliser_type_annexe(valeur, montant):
    """Cadre le type d'annexe ; un montant négatif force 'remise'."""
    if montant is not None and montant < 0:
        return "remise"
    if not valeur:
        return "taxe"
    v = str(valeur).strip().lower()
    v = "".join(c for c in unicodedata.normalize("NFD", v) if unicodedata.category(c) != "Mn")
    for t in _TYPES_ANNEXE:
        if t in v:
            return t
    if "port" in v or "livraison" in v or "fret" in v or "franco" in v:
        return "transport"
    if "ristourne" in v or "escompte" in v or "rabais" in v:
        return "remise"
    return "taxe"


def _colle(base, prix, montant) -> bool:
    """base × prix redonne-t-il le montant imprimé (aux arrondis de facture près) ?"""
    if base is None or base <= 0:
        return False
    return abs(base * prix - montant) <= max(0.02, 0.002 * abs(montant))


def _controler_base_ligne(ligne: dict) -> None:
    """Recoupe quantite × prix_unitaire avec le montant IMPRIMÉ, qui est la valeur
    la plus fiable de la ligne (le total de la facture boucle dessus).

    L'app recalcule le montant d'une ligne = base × prix : une quantité lue sur la
    mauvaise base (nombre de pièces au lieu du poids, ou l'inverse) fausse donc la
    ligne alors que le total papier reste juste. Ici, si le montant colle avec
    l'AUTRE base, on corrige unité + quantité ; si rien ne colle, on signale.
    Ajoute 'prix_suspect' et 'alerte_prix' (None si la ligne est cohérente).
    """
    ligne["prix_suspect"] = False
    ligne["alerte_prix"] = None
    pu, mt = ligne.get("prix_unitaire"), ligne.get("montant_ht")
    if not pu or mt is None:
        return
    q, poids, unite = ligne.get("quantite"), ligne.get("poids_kg"), ligne["unite_prix"]
    if _colle(q, pu, mt):
        return
    if _colle(poids, pu, mt):
        ligne["quantite"] = poids
        if unite != "kg":
            ligne["unite_prix"] = "kg"
            ligne["alerte_prix"] = "Unité corrigée en kg (prix × poids = montant)"
        return
    # Montant ÷ prix entier → c'est un nombre de pièces (le poids, lui, ne colle pas).
    n = abs(mt / pu)
    if round(n) >= 1 and abs(n - round(n)) < 0.01:
        ligne["quantite"] = float(round(n))
        if unite == "kg":
            ligne["unite_prix"] = "piece"
            ligne["alerte_prix"] = "Unité corrigée en pièce (prix × nb pièces = montant)"
        return
    ligne["prix_suspect"] = True
    ligne["alerte_prix"] = "Quantité × prix ne redonne pas le montant — à vérifier"


def extraire_facture(images_jpeg: list[bytes], fournisseur: str | None = None) -> dict:
    """Envoie les images d'une facture à Claude et renvoie un dict structuré,
    au même format que facturx_reader (source='ocr').

    fournisseur : nom du fournisseur de la facture (facultatif) ; s'il a une mise
    en page connue, sa consigne est ajoutée au prompt.

    Raises:
        OCRFactureError si clé absente, appel échoué ou réponse illisible.
    """
    if not images_jpeg:
        raise OCRFactureError("Aucune image de facture à analyser.")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or api_key == "sk-ant-REMPLACE-MOI":
        raise OCRFactureError(
            "Clé API Anthropic non configurée. Renseigne ANTHROPIC_API_KEY dans .env."
        )

    try:
        import anthropic
    except ImportError:
        raise OCRFactureError("Le paquet 'anthropic' n'est pas installé.")

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
    from src.ocr_bl import cle_fournisseur
    cle = cle_fournisseur(fournisseur)
    texte = _INSTRUCTIONS
    if cle in _CONSIGNES_FOURNISSEUR:
        texte += ("\n\nCONSIGNES SPÉCIFIQUES À CE FOURNISSEUR (mise en page connue) :\n"
                  + _CONSIGNES_FOURNISSEUR[cle])
    contenu.append({"type": "text", "text": texte})

    # Timeout borné (le défaut du SDK est ~10 min) : cf. ocr_bl.py — un incident
    # réseau doit échouer proprement plutôt que de laisser la requête pendre.
    # Streaming : le timeout borne le silence entre morceaux, pas la durée totale
    # (une facture longue dépasse 90 s de génération).
    client = anthropic.Anthropic(api_key=api_key, timeout=90.0, max_retries=1)
    output_config = {"format": {"type": "json_schema", "schema": _SCHEMA}}
    if EFFORT:
        output_config["effort"] = EFFORT
    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=16000,
            messages=[{"role": "user", "content": contenu}],
            output_config=output_config,
        ) as stream:
            resp = stream.get_final_message()
    except anthropic.APIError as e:
        logger.error("Appel OCR facture échoué : %s", e)
        raise OCRFactureError(f"Appel à l'API Claude échoué : {e}")

    texte = None
    try:
        texte = next(b.text for b in resp.content if b.type == "text")
        brut = json.loads(texte)
    except (StopIteration, json.JSONDecodeError) as e:
        logger.error(
            "Réponse OCR facture illisible : %s | stop_reason=%s | extrait=%r",
            e, resp.stop_reason, texte[-300:] if texte else None,
        )
        if resp.stop_reason == "max_tokens":
            raise OCRFactureError(
                "La facture est trop volumineuse pour l'OCR (réponse tronquée). "
                "Essaie de la scinder ou de saisir cette facture manuellement."
            )
        raise OCRFactureError("Réponse de l'OCR illisible.")

    prix_in, prix_out = _PRIX.get(MODEL, (3.00, 15.00))
    u = resp.usage
    cout = (u.input_tokens * prix_in + u.output_tokens * prix_out) / 1_000_000
    logger.info(
        "OCR facture : %d ligne(s) + %d annexe(s), modèle=%s, %d+%d tokens, coût≈$%.4f",
        len(brut.get("lignes", [])), len(brut.get("annexes", [])),
        MODEL, u.input_tokens, u.output_tokens, cout,
    )

    data = _normaliser_sortie(brut)
    data["_meta"] = {
        "consigne_fournisseur": cle if cle in _CONSIGNES_FOURNISSEUR else None,
        "modele": MODEL,
        "tokens_entree": u.input_tokens,
        "tokens_sortie": u.output_tokens,
        "cout_usd": round(cout, 4),
    }
    return data


def _normaliser_sortie(brut: dict) -> dict:
    """Met la sortie OCR au FORMAT COMMUN (identique à facturx_reader) :
    unités/types normalisés, date ISO, type_document cadré."""
    type_doc = (brut.get("type_document") or "facture").strip().lower()
    type_doc = "avoir" if type_doc.startswith("avoir") or "credit" in type_doc else "facture"

    lignes = []
    for l in brut.get("lignes", []):
        ligne = {
            "designation": l.get("designation") or "Article",
            "code_article": l.get("reference"),
            "quantite": l.get("quantite"),
            "poids_kg": l.get("poids_kg"),
            "prix_unitaire": l.get("prix_unitaire"),
            "unite_prix": _normaliser_unite_prix(l.get("unite_prix")),
            "montant_ht": l.get("montant_ht"),
            "tva_pct": l.get("tva_pct"),
            "type_ligne": "marchandise",
            "confiance": l.get("confiance"),
        }
        _controler_base_ligne(ligne)
        lignes.append(ligne)

    annexes = []
    for a in brut.get("annexes", []):
        montant = a.get("montant_ht")
        annexes.append({
            "designation": a.get("designation") or "Frais",
            "type_ligne": _normaliser_type_annexe(a.get("type_ligne"), montant),
            "montant_ht": montant,
            "tva_pct": a.get("tva_pct"),
        })

    recap = [t for t in brut.get("recap_tva", []) if t.get("taux") is not None]

    return {
        "source": "ocr",
        "fournisseur": brut.get("fournisseur"),
        "numero_facture": brut.get("numero_facture"),
        "date_facture": _parse_date_fr(brut.get("date_facture_brut")),
        "type_document": type_doc,
        "lignes": lignes,
        "annexes": annexes,
        "recap_tva": recap,
        "total_ht": brut.get("total_ht"),
        "total_tva": brut.get("total_tva"),
        "total_ttc": brut.get("total_ttc"),
    }

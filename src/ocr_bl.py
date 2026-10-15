"""
ocr_bl.py — Extraction OCR des bons de livraison (BL) via Claude vision.

Lit une ou plusieurs images de BL (JPEG déjà compressé par l'app) et renvoie
un dict structuré : fournisseur, n° BL, date, et une ligne par article avec
désignation / numéro de lot / DLC / DLUO / poids, plus un niveau de confiance.

Utilisé par l'endpoint POST /api/receptions/{id}/ocr-bl.

Garde-fou HACCP : le prompt interdit de deviner une date. Tout champ illisible
revient à null, et chaque ligne porte un niveau de confiance que l'écran de
validation côté front utilise pour signaler ce qui doit être vérifié.

Vitesse (banc chronométré du 15/10/2026 sur de vrais BL Saveurs d'Antoine,
Bourdicaud, Dipsa, Elivia) : le temps est dominé par l'ÉCRITURE de la réponse
(~0,6 s par ligne). D'où : effort bas, une page par appel en parallèle, sortie
JSON à clés courtes remise au format complet ici, et une consigne de mise en
page par fournisseur connu (sans elle la précision chute). Résultat : un BL
Saveurs de 46 lignes passe de ~107 s à ~13 s, sans perte de précision.
"""

import base64
import io
import json
import logging
import os
import unicodedata
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Modèle et effort par défaut, retenus au banc (cf. docstring). Surchargés par
# OCR_BL_MODEL / OCR_BL_EFFORT — variables propres au BL, pour que l'ancien
# OCR_MODEL (partagé avec ocr_facture) ne ramène pas l'ancien réglage lent.
MODEL = os.environ.get("OCR_BL_MODEL", "claude-sonnet-5-5")
EFFORT = os.environ.get("OCR_BL_EFFORT", "low")

# Tarifs ($/million de tokens) pour journaliser le coût réel de chaque appel.
# Sonnet 5 : tarif intro 2/10 jusqu'au 31/08/2026, puis 3/15 (standard retenu
# ici — coût affiché légèrement surestimé pendant l'intro, jamais sous-estimé).
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
        "fournisseur":  {"type": ["string", "null"]},
        "numero_bl":    {"type": ["string", "null"]},
        "date_bl_brut": {"type": ["string", "null"]},
        "lignes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "designation":   {"type": "string"},
                    "reference":     {"type": ["string", "null"]},
                    "numero_lot":    {"type": ["string", "null"]},
                    "dlc_brut":      {"type": ["string", "null"]},
                    "dluo_brut":     {"type": ["string", "null"]},
                    "poids_kg":      {"type": ["number", "null"]},
                    "quantite":      {"type": ["number", "null"]},
                    "prix_unitaire": {"type": ["number", "null"]},
                    # Valeurs attendues 'kg'|'piece'|'colis' (cadrées par l'instruction).
                    # Pas d'enum dans le schéma : éviter qu'un enum mêlant string+null soit
                    # refusé par la validation stricte des structured outputs. Normalisé en Python.
                    "unite_prix":    {"type": ["string", "null"]},
                    "montant_ligne": {"type": ["number", "null"]},
                    "confiance":     {"type": "string", "enum": ["haute", "moyenne", "basse"]},
                },
                "required": ["designation", "reference", "numero_lot", "dlc_brut",
                             "dluo_brut", "poids_kg", "quantite",
                             "prix_unitaire", "unite_prix", "montant_ligne", "confiance"],
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
- prix_unitaire : le prix unitaire HORS TAXES de cet article (un seul nombre, sans le symbole €)
- unite_prix : l'unité à laquelle se rapporte ce prix unitaire — "kg" si c'est un prix au kilo, "piece" si c'est un prix à la pièce/à l'unité, "colis" si c'est un prix au colis/carton. C'est l'information qui dit "ce prix, c'est par quoi". Si tu ne peux pas la déterminer avec certitude, mets null.
- montant_ligne : le montant total HORS TAXES de la ligne (prix × quantité/poids), tel qu'écrit sur le BL

POINT CRITIQUE — appariement DLC ↔ article :
Sur certains BL, le lot et la DLC d'un article sont écrits sur une LIGNE SÉPARÉE (souvent juste en dessous de l'article, parfois préfixée "lot"). Cette DLC/ce lot appartiennent à l'article AUQUEL ILS SE RAPPORTENT visuellement (le plus proche, en général juste au-dessus) — surtout PAS à l'article suivant. Vérifie l'alignement avant d'associer : ne décale jamais une DLC d'un article à l'autre. En cas de doute sur l'appariement, baisse la "confiance" de la ligne plutôt que de risquer une erreur.

POINT CRITIQUE — plusieurs lots / DLC pour un même article :
Un même article peut être livré en PLUSIEURS lots, chacun avec son propre numéro de lot et parfois sa propre DLC (par ex. "Côte de bœuf" avec lot A DLC 12/07 et lot B DLC 15/07). Dans ce cas, produis UNE LIGNE PAR COUPLE (lot, DLC) : répète la même "designation", mais mets le bon "numero_lot" et la bonne "dlc_brut"/"dluo_brut" sur chacune. Répartis aussi le poids/la quantité par lot si le BL les distingue, sinon laisse null sur les lignes où ce n'est pas précisé. Ne fusionne JAMAIS plusieurs lots dans une seule ligne et n'invente pas de lot qui n'est pas écrit.

POINT CRITIQUE — PRIX D'ACHAT (à extraire systématiquement) :
Un bon de livraison de viande comporte presque toujours un PRIX par article — c'est une information aussi importante que le lot et la DLC, NE L'OUBLIE PAS. Pour CHAQUE ligne, cherche activement dans le tableau la colonne du prix unitaire (souvent intitulée "P.U.", "Prix U.", "Prix unitaire", "Prix HT", "P.U. HT", "€/kg", "Tarif") et la colonne du montant total de la ligne ("Montant", "Total", "Total HT", "Montant HT").
- prix_unitaire : le prix d'UNE unité (un kilo, une pièce ou un colis selon le BL), tel qu'écrit, sans le symbole €.
- unite_prix : à quoi se rapporte ce prix unitaire → "kg" (prix au kilo, le cas le plus fréquent en boucherie), "piece" (prix à la pièce/unité) ou "colis" (prix au colis/carton).
- montant_ligne : le montant total HT de la ligne.
Exemple : une ligne "ENTRECOTE VBF   12,340 kg   18,50 €/kg   228,29 €" donne prix_unitaire=18.50, unite_prix="kg", poids_kg=12.34, montant_ligne=228.29.
Si VRAIMENT aucun prix n'est écrit pour un article (ça arrive sur certains BL), alors et seulement alors mets prix_unitaire, unite_prix et montant_ligne à null. Mais ne te contente pas de mettre null par facilité : regarde bien tout le tableau, le prix y est presque toujours.

Règles générales :
- Un couple (article, lot) = un objet dans "lignes". Un article à lot unique = une seule ligne ; un article à plusieurs lots = une ligne par lot. N'invente jamais de ligne, n'en oublie aucune.
- DATES — recopie chaque date EXACTEMENT comme écrite, caractère pour caractère, dans "dlc_brut" / "dluo_brut" / "date_bl_brut". NE CONVERTIS RIEN, ne réordonne pas jour/mois. "07/12/26" → mets exactement "07/12/26". La conversion est faite ensuite par le programme.
- Distingue DLC (consommer jusqu'au) et DLUO/DDM (à consommer de préférence avant) : ne mets jamais une DLUO dans dlc_brut.
- PRIX — recopie le prix unitaire et le montant TELS QU'ÉCRITS, en HORS TAXES quand le BL distingue HT et TTC (les BL de viande sont en général en HT). N'additionne pas, ne recalcule pas un prix : si seul le montant total est écrit, mets-le dans montant_ligne et laisse prix_unitaire à null. Utilise le point comme séparateur décimal (18,50 → 18.50). N'invente JAMAIS un prix : si le prix d'un article n'est pas écrit, mets prix_unitaire, unite_prix et montant_ligne à null.
- PRIX & lots multiples — quand un même article est livré en plusieurs lots (donc plusieurs lignes), le prix unitaire est en général le même pour tous ces lots : reporte-le sur chaque ligne. Ne répartis le montant_ligne par lot que si le BL le détaille, sinon laisse-le sur la ligne qui le porte et null ailleurs.
- Si une information est illisible ou absente, mets null. Ne devine pas.
- "confiance" (haute/moyenne/basse) sur la lecture du lot, de la DLC ET du prix de la ligne. Si l'un des trois est douteux, baisse la confiance. Sois honnête : une saisie erronée (traçabilité ou prix) est pire qu'un champ signalé à vérifier.
- Plusieurs images = pages d'un même BL : fusionne en une seule liste d'articles.
- Ignore les totaux, conditions de vente, mentions légales.

Réponds uniquement via le format structuré demandé."""


# ---------------------------------------------------------------------------
# Consignes par fournisseur (mise en page connue) — sans elles, la précision
# chute nettement au banc (lots/DLC décalés, lignes manquées).
# ---------------------------------------------------------------------------

_CONSIGNES_FOURNISSEUR = {
    "saveurs": """Document SAVEURS D'ANTOINE (traiteur / charcuterie), « FACTURE LIVRAISON » souvent sur 2 ou 3 pages. Le n° de BL est sur la ligne « BL n° : 0745721 Votre Commande du … ».
Colonnes : DESIGNATION PRODUIT (code 6 chiffres + libellé, parfois sur 2 lignes) | QTE CMD | QTE LIVREE en UCde | QTE LIVREE en UF | UF | PRIX BRUT | REMISES | PRIX NET | Montant H.T | TVA.
Sous chaque article, une ou plusieurs sous-lignes en italique « lot [numéro] dlc jj/mm/aa  N p. X,XXX kg » : produis UNE ligne par sous-ligne, avec SA dlc, quantite = N et poids_kg = X de CETTE sous-ligne.
Le numéro de lot est presque toujours VIDE (seul le mot « lot » est imprimé) → numero_lot null ; ne prends jamais le code article ni un autre nombre pour un lot.
prix_unitaire = PRIX NET (un « P » devant signale une promo, ignore-le) ; unite_prix = colonne UF (KG → "kg", SCHT/BQT/PIECE/SEAU/COL/ECU/TER → "piece") ; montant_ligne = Montant H.T sur la première sous-ligne de l'article seulement, null sur les suivantes.
Ignore « Poids : … - Pièces : … », les totaux, conditions et mentions.""",
    "bourdicaud": """Document BOURDICAUD (volailles). C'est souvent la FACTURE qui sert de BL ; le n° de BL est sur la ligne "BL N° xxxxxxxx du jj/mm/aaaa" au-dessus des articles.
Colonnes : CODE | DESIGNATION | EAN13 | QTE | POIDS | COLIS | PRIX BASE | UN | P.U. H.T. | MONTANT H.T.
Sous chaque article, une ligne en italique "LOT <numéro>   DLC <jj/mm/aaaa>" (suivie de qte/poids/colis répétés) : ce lot et cette DLC appartiennent à l'article JUSTE AU-DESSUS.
Les lignes "Né, élevé, abattu…", "Produit …", "Poulet JA …" sont des mentions, pas des articles. Le code EAN13 (13 chiffres) n'est PAS un lot.
prix_unitaire = P.U. H.T. ; unite_prix = colonne UN (KG → "kg"). Ignore les annotations manuscrites.""",
    "dipsa": """Document DIPSA (charcuterie / traiteur). Le fichier peut contenir plusieurs BL ("Bon de livraison 0165xxxx").
Colonnes : Article (code 6 chiffres) | DESIGNATION | T | NOMBRE | Quantité | LOT | D.L.C. | P.U. Net | MT NET. Tout tient sur UNE ligne par article :
NOMBRE "1 P" = quantité (pièces) ; Quantité "4,288 K" = poids en kg ; LOT = 7 chiffres (parfois une lettre + chiffres, ex. A024217) ; D.L.C. au format jj/mm/aa ; P.U. Net "x,xxxx /K" = prix au kg.
Une ligne de type T = "M" (manquant) n'a ni lot ni poids : ne la produis pas. Ignore "Date de commande", "Préparé pour", "01 FRAIS/SEC", les totaux et récapitulatifs.""",
    "elivia": """Document ELIVIA / SELVI (viande).
Chaque article = une ligne en gras (désignation, code "Produit VL" ex. 07991-07, Colis, Pièces, Poids net, Poids fact, PU base, PU net "13.3500K" = €/kg, Montant HT), puis un sous-tableau avec UN LOT PAR LIGNE : "N° lot" (ex. AL60046992 ; "N° tuerie" pour les carcasses), "Poids" du lot, et "DLC / DLUO" (jj/mm/aaaa).
Si la colonne s'appelle "Date abattage", ce n'est PAS une DLC → dlc_brut null. Article à plusieurs lots → une ligne par lot avec le poids DU LOT, prix_unitaire = PU net sur chaque ligne, montant_ligne sur la première seulement.
Ignore la section Atelier (Interbev, redevances, prestations), Emballage et Support.""",
}

# Mots-clés (nom fournisseur normalisé) → clé de consigne.
_MOTS_FOURNISSEUR = {
    "saveurs": ("saveur", "antoine", "yvas"),
    "bourdicaud": ("bourdicaud",),
    "dipsa": ("dipsa",),
    "elivia": ("elivia", "selvi"),
}

# Les BL Elivia arrivent toujours à l'horizontale : on les redresse avant l'OCR
# (sans redressement, lots/DLC mal lus sur ~15 % des lignes au banc).
_ROTATION_FOURNISSEUR = {"elivia": 90}


def _sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")


def cle_fournisseur(nom: str | None) -> str | None:
    """Reconnaît un fournisseur à mise en page connue d'après son nom (None sinon)."""
    if not nom:
        return None
    n = _sans_accents(nom).lower()
    for cle, mots in _MOTS_FOURNISSEUR.items():
        if any(m in n for m in mots):
            return cle
    return None


def _pivoter_jpeg(jpeg: bytes, angle: int) -> bytes:
    """Pivote une image JPEG (sens anti-horaire, comme PIL) et la ré-encode."""
    from PIL import Image
    img = Image.open(io.BytesIO(jpeg)).convert("RGB").rotate(angle, expand=True)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Sortie compacte : le modèle écrit des clés courtes (moins de tokens à générer,
# donc plus rapide), remises ensuite au format complet de _SCHEMA.
# ---------------------------------------------------------------------------

_CLES_COURTES = {
    "d": "designation", "r": "reference", "l": "numero_lot", "dlc": "dlc_brut", "dluo": "dluo_brut",
    "kg": "poids_kg", "q": "quantite", "pu": "prix_unitaire", "u": "unite_prix",
    "mt": "montant_ligne", "c": "confiance",
}
_CONFIANCE_COURTE = {"h": "haute", "m": "moyenne", "b": "basse"}
_PROPS_LIGNE = _SCHEMA["properties"]["lignes"]["items"]["properties"]

_SCHEMA_COMPACT = {
    "type": "object",
    "properties": {
        "f": {"type": ["string", "null"]},
        "bl": {"type": ["string", "null"]},
        "date": {"type": ["string", "null"]},
        "L": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    court: ({"type": "string", "enum": ["h", "m", "b"]} if court == "c" else _PROPS_LIGNE[long])
                    for court, long in _CLES_COURTES.items()
                },
                "required": list(_CLES_COURTES),
                "additionalProperties": False,
            },
        },
    },
    "required": ["f", "bl", "date", "L"],
    "additionalProperties": False,
}

_NOTE_COMPACT = (
    "\n\nFORMAT DE SORTIE COMPACT (clés courtes) : f=fournisseur, bl=numero_bl, date=date_bl_brut, L=lignes ; "
    "dans chaque ligne : d=designation, r=reference, l=numero_lot, dlc=dlc_brut, dluo=dluo_brut, kg=poids_kg, "
    "q=quantite, pu=prix_unitaire, u=unite_prix, mt=montant_ligne, c=confiance (h=haute, m=moyenne, b=basse)."
)

_DESIGNATION_SUITE = "(suite)"


def _depuis_compact(d: dict) -> dict:
    """Remet une réponse compacte au format complet de _SCHEMA."""
    lignes = []
    for l in d.get("L", []):
        ligne = {_CLES_COURTES[k]: v for k, v in l.items() if k in _CLES_COURTES}
        ligne["confiance"] = _CONFIANCE_COURTE.get(l.get("c"), "basse")
        lignes.append(ligne)
    return {"fournisseur": d.get("f"), "numero_bl": d.get("bl"), "date_bl_brut": d.get("date"), "lignes": lignes}


def _fusionner_pages(pages: list[dict]) -> dict:
    """Fusionne les résultats page par page en un seul BL.

    En-tête : première valeur non vide. Une sous-ligne en haut de page qui
    prolonge l'article de la page précédente arrive avec la désignation
    « (suite) » : on lui redonne la désignation du dernier article vu.
    """
    data = {k: next((p.get(k) for p in pages if p.get(k)), None)
            for k in ("fournisseur", "numero_bl", "date_bl_brut")}
    lignes: list[dict] = []
    for p in pages:
        for ligne in p.get("lignes", []):
            if (ligne.get("designation") or "").strip().lower() == _DESIGNATION_SUITE and lignes:
                ligne["designation"] = lignes[-1]["designation"]
                ligne["reference"] = ligne.get("reference") or lignes[-1].get("reference")
            lignes.append(ligne)
    data["lignes"] = lignes
    return data


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


def _normaliser_unite_prix(valeur) -> str | None:
    """Ramène l'unité de prix lue par l'OCR vers 'kg' | 'piece' | 'colis' | None.

    L'enum n'est plus dans le schéma (cf. _SCHEMA) : on cadre ici les variantes que
    le modèle pourrait écrire malgré l'instruction. None si vide ou non reconnu.
    """
    if not valeur:
        return None
    v = str(valeur).strip().lower()
    import unicodedata
    v = "".join(c for c in unicodedata.normalize("NFD", v) if unicodedata.category(c) != "Mn")
    if v in ("kg", "kilo", "kilos", "kilogramme", "kilogrammes", "/kg", "le kg", "au kg"):
        return "kg"
    if v in ("piece", "pieces", "u", "unite", "unites", "pc", "pce", "/piece", "la piece"):
        return "piece"
    if v in ("colis", "carton", "cartons", "caisse", "caisses", "/colis", "le colis"):
        return "colis"
    return None


def _verifier_coherence_prix(prix_unitaire, unite_prix, poids_kg, quantite, montant_ligne):
    """Contrôle générique prix × base ≈ montant, indépendant du fournisseur.

    Ne corrige rien : signale une ligne dont le prix unitaire et le montant ne se
    recoupent pas (lecture probablement erronée), comme `dlc_suspecte` pour les dates.
    La conversion en €/kg et la comparaison au catalogue se font plus tard (côté Achats),
    car elles dépendent du poids_colis_kg du catalogue, inconnu du BL.

    Returns:
        (prix_suspect: bool, alerte_prix: str | None)
    """
    if prix_unitaire is None or montant_ligne is None:
        return False, None
    # Base = ce que multiplie le prix unitaire : le poids si prix au kg, sinon la quantité.
    base = poids_kg if unite_prix == "kg" else quantite
    if not base:
        return False, None  # pas de quoi recouper sans inventer
    attendu = prix_unitaire * base
    if attendu <= 0:
        return False, None
    ecart_rel = abs(montant_ligne - attendu) / attendu
    if ecart_rel > 0.02:  # tolérance 2 % (arrondis BL)
        return True, "Prix × quantité ne correspond pas au montant — à vérifier"
    return False, None


def _appel_page(client, anthropic, images: list[bytes], texte: str) -> tuple[dict, int, int]:
    """Un appel Claude (sortie compacte) → (données au format complet, tokens entrée, tokens sortie)."""
    contenu = [{
        "type": "image",
        "source": {"type": "base64", "media_type": "image/jpeg",
                   "data": base64.standard_b64encode(jpeg).decode()},
    } for jpeg in images]
    contenu.append({"type": "text", "text": texte + _NOTE_COMPACT})

    output_config = {"format": {"type": "json_schema", "schema": _SCHEMA_COMPACT}}
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
        logger.error("Appel OCR échoué : %s", e)
        raise OCRError(f"Appel à l'API Claude échoué : {e}")

    brut = None
    try:
        brut = next(b.text for b in resp.content if b.type == "text")
        data = _depuis_compact(json.loads(brut))
    except (StopIteration, json.JSONDecodeError) as e:
        logger.error(
            "Réponse OCR illisible : %s | stop_reason=%s | extrait=%r",
            e, resp.stop_reason, brut[-300:] if brut else None,
        )
        if resp.stop_reason == "max_tokens":
            raise OCRError(
                "Le BL est trop volumineux pour l'OCR (réponse tronquée). "
                "Essaie de le scinder ou de saisir ce BL manuellement."
            )
        raise OCRError("Réponse de l'OCR illisible.")
    return data, resp.usage.input_tokens, resp.usage.output_tokens


def extraire_bl(images_jpeg: list[bytes], fournisseur: str | None = None) -> dict:
    """Envoie les images du BL à Claude et renvoie le dict structuré.

    Une page = un appel, lancés en parallèle (le temps est celui de la page la
    plus longue, pas la somme). Si le fournisseur est reconnu, sa consigne de
    mise en page est ajoutée et ses photos sont redressées si besoin (Elivia).

    Args:
        images_jpeg: liste d'images JPEG (bytes), une par page de BL.
        fournisseur: nom du fournisseur de la réception (facultatif).

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

    cle = cle_fournisseur(fournisseur)
    angle = _ROTATION_FOURNISSEUR.get(cle)
    if angle:
        images_jpeg = [_pivoter_jpeg(j, angle) for j in images_jpeg]

    texte = _INSTRUCTIONS
    if cle:
        texte += ("\n\nCONSIGNES SPÉCIFIQUES À CE FOURNISSEUR (mise en page connue) :\n"
                  + _CONSIGNES_FOURNISSEUR[cle])

    # Timeout borné (le défaut du SDK est ~10 min) : sur la connexion du Pi, un
    # incident réseau doit échouer proprement (message clair, HTTP 502) plutôt que
    # de laisser la requête pendre — c'est ça qui, côté navigateur, finit par
    # remonter en "Failed to fetch" sans explication après une longue attente.
    # En streaming, ce timeout borne le SILENCE entre deux morceaux et non la durée
    # totale : un BL long (beaucoup de lignes à générer, > 90 s) va au bout, alors
    # qu'en appel simple il était coupé ("Request timed out").
    client = anthropic.Anthropic(api_key=api_key, timeout=90.0, max_retries=1)

    n = len(images_jpeg)
    if n == 1:
        resultats = [_appel_page(client, anthropic, images_jpeg, texte)]
    else:
        textes = [
            texte + f"\n\nIMPORTANT : cette image est la PAGE {k + 1}/{n} du BL. Extrais UNIQUEMENT les "
            "articles imprimés sur cette page. Si des sous-lignes (lot/DLC) en haut de page appartiennent à "
            "un article commencé à la page précédente, produis-les avec la désignation de cet article si "
            f"elle est visible, sinon \"{_DESIGNATION_SUITE}\"."
            for k in range(n)
        ]
        with ThreadPoolExecutor(max_workers=min(n, 6)) as pool:
            resultats = list(pool.map(
                lambda a: _appel_page(client, anthropic, [a[0]], a[1]), zip(images_jpeg, textes)
            ))
    data = _fusionner_pages([r[0] for r in resultats])
    tokens_in = sum(r[1] for r in resultats)
    tokens_out = sum(r[2] for r in resultats)

    # Coût réel, pour journalisation et suivi
    prix_in, prix_out = _PRIX.get(MODEL, (3.00, 15.00))
    cout = (tokens_in * prix_in + tokens_out * prix_out) / 1_000_000
    logger.info(
        "OCR BL : %d ligne(s), %d page(s), fournisseur=%s, modèle=%s, %d+%d tokens, coût≈$%.4f",
        len(data.get("lignes", [])), n, cle or "générique", MODEL, tokens_in, tokens_out, cout,
    )
    # Suivi qualité : combien de lignes ont un prix extrait (signale un BL/fournisseur
    # sans prix lisible si le ratio tombe à 0 sur un BL qui devrait en avoir).
    _lignes = data.get("lignes", [])
    _avec_prix = sum(1 for l in _lignes if l.get("prix_unitaire") is not None)
    logger.info("OCR BL : prix extrait sur %d/%d ligne(s)", _avec_prix, len(_lignes))

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

        # Normalise l'unité de prix vers le vocabulaire attendu ('kg'|'piece'|'colis'),
        # pour que l'étape de rapprochement (€/kg via _calc_prix_kg) reçoive une valeur propre.
        ligne["unite_prix"] = _normaliser_unite_prix(ligne.get("unite_prix"))

        # Contrôle de cohérence du prix (générique, ne corrige rien).
        prix_suspect, alerte_prix = _verifier_coherence_prix(
            ligne.get("prix_unitaire"), ligne.get("unite_prix"),
            ligne.get("poids_kg"), ligne.get("quantite"), ligne.get("montant_ligne"),
        )
        ligne["prix_suspect"] = prix_suspect
        ligne["alerte_prix"] = alerte_prix

    data["_meta"] = {
        "modele": MODEL,
        "tokens_entree": tokens_in,
        "tokens_sortie": tokens_out,
        "cout_usd": round(cout, 4),
        "pages": n,
        "consigne_fournisseur": cle,
    }
    return data

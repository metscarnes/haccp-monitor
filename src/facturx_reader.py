"""
facturx_reader.py — Lecture des factures électroniques Factur-X / ZUGFeRD.

Une facture Factur-X est un PDF/A-3 classique avec un fichier XML STRUCTURÉ
embarqué (norme EN 16931, syntaxe CII — Cross Industry Invoice). À partir du
1er septembre 2026, la réception de ces factures devient obligatoire en France ;
nos fournisseurs ETI/grandes entreprises en émettent dès cette date. Quand le PDF
en contient un, on lit les données du XML — fiables à 100 %, ZÉRO erreur d'OCR —
plutôt que de faire de la vision. L'OCR (ocr_facture.py) reste le repli pour les
PDF/images scannés sans XML.

Choix d'implémentation : extraction du XML via PyMuPDF (déjà installé pour les BL)
et parsing via la lib XML de la stdlib — AUCUNE dépendance nouvelle (la lib
`facturx` a des dépendances lourdes/fragiles sur le Pi ARM). On ne lit que ce dont
le module facture a besoin : entête, lignes, ventilation TVA, totaux.

Le résultat suit le MÊME format que ocr_facture.extraire_facture (lignes marchandise
+ annexes + recap_tva + totaux), pour que l'écran de rapprochement soit identique
quelle que soit la source.
"""

import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# Noms de fichiers XML normalisés d'une facture Factur-X / ZUGFeRD / Factur-X.
# On teste par nom ET, en dernier recours, on prend n'importe quel embed XML.
_NOMS_XML_FACTURX = (
    "factur-x.xml",
    "zugferd-invoice.xml",
    "xrechnung.xml",
    "order-x.xml",
)

# Espaces de noms CII (Cross Industry Invoice) — cœur de Factur-X.
_NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}

# Codes « type de charge » CII fréquents → notre type_ligne annexe.
# 'FC' = Freight/transport, 'ABK'/'ADR' divers frais… on reste simple : transport
# si le libellé/le code évoque le port, sinon 'taxe' pour les charges fiscales.
_MOTS_TRANSPORT = ("transport", "port", "livraison", "fret", "freight", "franco")


class FacturXError(Exception):
    """Erreur fonctionnelle de lecture Factur-X (PDF/XML illisible) — repli OCR normal."""


class FacturXIndisponible(Exception):
    """Erreur d'ENVIRONNEMENT (PyMuPDF absent/cassé) — PAS un cas de repli normal :
    un vrai Factur-X basculerait silencieusement sur l'OCR sans que rien ne l'indique.
    À logger en ERROR (pas warning) et à faire remonter, pas à avaler."""


def extraire_xml_facturx(pdf_bytes: bytes) -> bytes | None:
    """Renvoie le XML Factur-X embarqué dans le PDF, ou None s'il n'y en a pas.

    N'échoue jamais sur un PDF ordinaire (scan sans XML) : renvoie simplement None
    pour laisser l'appelant basculer sur l'OCR.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise FacturXIndisponible("Lecture PDF indisponible (PyMuPDF non installé).")

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise FacturXError(f"PDF illisible : {e}")

    try:
        noms = list(doc.embfile_names())
        if not noms:
            return None
        # 1) nom normalisé connu (insensible à la casse)
        cible = None
        bas = {n.lower(): n for n in noms}
        for candidat in _NOMS_XML_FACTURX:
            if candidat in bas:
                cible = bas[candidat]
                break
        # 2) sinon, le premier embed qui ressemble à du XML
        if cible is None:
            for n in noms:
                if n.lower().endswith(".xml"):
                    cible = n
                    break
        if cible is None:
            return None
        return doc.embfile_get(cible)
    finally:
        doc.close()


def _txt(elem, chemin: str) -> str | None:
    """Texte d'un sous-élément (chemin ElementTree avec préfixes _NS), ou None."""
    if elem is None:
        return None
    trouve = elem.find(chemin, _NS)
    if trouve is None or trouve.text is None:
        return None
    val = trouve.text.strip()
    return val or None


def _nombre(elem, chemin: str):
    """Convertit en float le texte d'un sous-élément, ou None si absent/illisible."""
    v = _txt(elem, chemin)
    if v is None:
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return None


def _type_annexe(libelle: str | None) -> str:
    """Devine le type d'une ligne de charge annexe depuis son libellé."""
    bas = (libelle or "").lower()
    if any(m in bas for m in _MOTS_TRANSPORT):
        return "transport"
    return "taxe"


def parser_facturx(xml_bytes: bytes) -> dict:
    """Parse le XML CII d'une facture Factur-X et renvoie un dict structuré,
    au même format que l'OCR facture.

    Returns:
        {
          "source": "facturx",
          "fournisseur": str|None, "numero_facture": str|None, "date_facture": iso|None,
          "type_document": "facture"|"avoir",
          "lignes": [ {designation, code_article, quantite, prix_unitaire, unite_prix,
                       montant_ht, tva_pct, type_ligne='marchandise'} ],
          "annexes": [ {designation, type_ligne, montant_ht, tva_pct} ],
          "recap_tva": [ {taux, base_ht, tva} ],
          "total_ht": float|None, "total_tva": float|None, "total_ttc": float|None,
        }
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise FacturXError(f"XML Factur-X illisible : {e}")

    doc_ctx = root.find(".//rsm:ExchangedDocument", _NS)
    numero = _txt(doc_ctx, "ram:ID")
    # Date : ram:IssueDateTime/udt:DateTimeString (format 102 = AAAAMMJJ)
    date_iso = None
    dt = None
    if doc_ctx is not None:
        dt = doc_ctx.find("ram:IssueDateTime/udt:DateTimeString", _NS)
    if dt is not None and dt.text:
        brut = dt.text.strip()
        if len(brut) == 8 and brut.isdigit():
            date_iso = f"{brut[0:4]}-{brut[4:6]}-{brut[6:8]}"

    # Type document : code 380 = facture, 381 = avoir (le plus fréquent).
    type_code = _txt(doc_ctx, "ram:TypeCode")
    type_document = "avoir" if type_code == "381" else "facture"

    transaction = root.find(".//rsm:SupplyChainTradeTransaction", _NS)

    # Fournisseur = vendeur (SellerTradeParty)
    fournisseur = None
    accord = transaction.find("ram:ApplicableHeaderTradeAgreement", _NS) if transaction is not None else None
    if accord is not None:
        fournisseur = _txt(accord, "ram:SellerTradeParty/ram:Name")

    # Lignes marchandise
    lignes = []
    for item in (transaction.findall("ram:IncludedSupplyChainTradeLineItem", _NS)
                 if transaction is not None else []):
        produit = item.find("ram:SpecifiedTradeProduct", _NS)
        designation = _txt(produit, "ram:Name") or "Article"
        code_article = (_txt(produit, "ram:SellerAssignedID")
                        or _txt(produit, "ram:GlobalID"))

        accord_l = item.find("ram:SpecifiedLineTradeAgreement", _NS)
        # Prix net unitaire ; à défaut prix brut
        prix_unitaire = (_nombre(accord_l, "ram:NetPriceProductTradePrice/ram:ChargeAmount")
                         or _nombre(accord_l, "ram:GrossPriceProductTradePrice/ram:ChargeAmount"))

        livraison_l = item.find("ram:SpecifiedLineTradeDelivery", _NS)
        quantite = _nombre(livraison_l, "ram:BilledQuantity")
        unite_code = None
        if livraison_l is not None:
            q = livraison_l.find("ram:BilledQuantity", _NS)
            if q is not None:
                unite_code = q.get("unitCode")

        reglement_l = item.find("ram:SpecifiedLineTradeSettlement", _NS)
        montant_ht = _nombre(reglement_l, "ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount")
        tva_pct = _nombre(reglement_l, "ram:ApplicableTradeTax/ram:RateApplicablePercent")

        lignes.append({
            "designation": designation,
            "code_article": code_article,
            "quantite": quantite,
            "prix_unitaire": prix_unitaire,
            "unite_prix": _unite_depuis_code(unite_code),
            "montant_ht": montant_ht,
            "tva_pct": tva_pct,
            "type_ligne": "marchandise",
        })

    # Charges/remises au niveau document → lignes annexes
    annexes = []
    reglement = (transaction.find("ram:ApplicableHeaderTradeSettlement", _NS)
                 if transaction is not None else None)
    if reglement is not None:
        for charge in reglement.findall("ram:SpecifiedTradeAllowanceCharge", _NS):
            indicateur = _txt(charge, "ram:ChargeIndicator/udt:Indicator")
            montant = _nombre(charge, "ram:ActualAmount")
            if montant is None:
                continue
            motif = _txt(charge, "ram:Reason")
            tva = _nombre(charge, "ram:CategoryTradeTax/ram:RateApplicablePercent")
            # ChargeIndicator=true → charge (frais, +) ; false → remise (−)
            est_charge = (indicateur or "").lower() == "true"
            if est_charge:
                annexes.append({
                    "designation": motif or "Frais",
                    "type_ligne": _type_annexe(motif),
                    "montant_ht": montant,
                    "tva_pct": tva,
                })
            else:
                annexes.append({
                    "designation": motif or "Remise",
                    "type_ligne": "remise",
                    "montant_ht": -abs(montant),
                    "tva_pct": tva,
                })

    # Ventilation TVA + totaux (ram:ApplicableTradeTax multiples, puis Summation)
    recap_tva = []
    if reglement is not None:
        for tax in reglement.findall("ram:ApplicableTradeTax", _NS):
            base = _nombre(tax, "ram:BasisAmount")
            montant_tva = _nombre(tax, "ram:CalculatedAmount")
            taux = _nombre(tax, "ram:RateApplicablePercent")
            if taux is not None:
                recap_tva.append({"taux": taux, "base_ht": base, "tva": montant_tva})

    somm = (reglement.find("ram:SpecifiedTradeSettlementHeaderMonetarySummation", _NS)
            if reglement is not None else None)
    total_ht = _nombre(somm, "ram:TaxBasisTotalAmount") or _nombre(somm, "ram:LineTotalAmount")
    total_tva = _nombre(somm, "ram:TaxTotalAmount")
    total_ttc = _nombre(somm, "ram:GrandTotalAmount")

    return {
        "source": "facturx",
        "fournisseur": fournisseur,
        "numero_facture": numero,
        "date_facture": date_iso,
        "type_document": type_document,
        "lignes": lignes,
        "annexes": annexes,
        "recap_tva": recap_tva,
        "total_ht": total_ht,
        "total_tva": total_tva,
        "total_ttc": total_ttc,
    }


# Codes d'unité UN/ECE Rec 20 fréquents → notre vocabulaire kg|piece|colis.
_UNITES_CII = {
    "KGM": "kg",       # kilogramme
    "C62": "piece",    # unité (one)
    "H87": "piece",    # piece
    "EA":  "piece",    # each
    "PCE": "piece",
    "XPK": "colis",    # package
    "XCT": "colis",    # carton
    "XBX": "colis",    # box
}


def _unite_depuis_code(code: str | None) -> str:
    """Unité de prix (kg|piece|colis) depuis le unitCode CII, défaut 'kg'."""
    if not code:
        return "kg"
    return _UNITES_CII.get(code.upper(), "kg")


def lire_facture_pdf(pdf_bytes: bytes) -> dict | None:
    """Point d'entrée : si le PDF contient un XML Factur-X, renvoie les données
    structurées ; sinon None (l'appelant bascule sur l'OCR).

    N'échoue pas sur un PDF ordinaire : None signifie simplement « pas de Factur-X ».
    """
    xml = extraire_xml_facturx(pdf_bytes)
    if xml is None:
        return None
    return parser_facturx(xml)

"""
test_factures_refonte_etape4.py — Refonte facture étape 4 : import Factur-X + OCR.

Règles testées :
- Le lecteur Factur-X extrait entête/lignes/annexes/TVA/totaux d'un PDF à XML
  embarqué, et renvoie None pour un PDF ordinaire (→ bascule OCR).
- Import d'un document Factur-X → extraction fiable, document conservé.
- Application d'une extraction validée : remplace les lignes, reporte n°/date +
  totaux papier, passe par les calculs standard (unités/arrondis/TVA), bascule
  le statut si ça boucle. Rien n'est appliqué sans validation.
- L'import respecte le verrouillage (facture validée → 409).

Les appels OCR vision réels ne sont pas testés ici (couverts par l'écran de
validation) ; on teste le pipeline Factur-X (déterministe) et l'application.
"""
import io

import fitz
import pytest

from test_factures_refonte_etape0 import _setup


# XML CII minimal : 1 ligne kg + 1 transport + TVA + totaux.
_XML_FACTURX = """<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
  xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
  xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
  xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocument>
    <ram:ID>FX-2026-001</ram:ID>
    <ram:TypeCode>380</ram:TypeCode>
    <ram:IssueDateTime><udt:DateTimeString format="102">20260705</udt:DateTimeString></ram:IssueDateTime>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:IncludedSupplyChainTradeLineItem>
      <ram:SpecifiedTradeProduct>
        <ram:SellerAssignedID>BOEUF01</ram:SellerAssignedID>
        <ram:Name>Entrecote VBF</ram:Name>
      </ram:SpecifiedTradeProduct>
      <ram:SpecifiedLineTradeAgreement>
        <ram:NetPriceProductTradePrice><ram:ChargeAmount>18.50</ram:ChargeAmount></ram:NetPriceProductTradePrice>
      </ram:SpecifiedLineTradeAgreement>
      <ram:SpecifiedLineTradeDelivery>
        <ram:BilledQuantity unitCode="KGM">10</ram:BilledQuantity>
      </ram:SpecifiedLineTradeDelivery>
      <ram:SpecifiedLineTradeSettlement>
        <ram:ApplicableTradeTax><ram:RateApplicablePercent>5.5</ram:RateApplicablePercent></ram:ApplicableTradeTax>
        <ram:SpecifiedTradeSettlementLineMonetarySummation>
          <ram:LineTotalAmount>185.00</ram:LineTotalAmount>
        </ram:SpecifiedTradeSettlementLineMonetarySummation>
      </ram:SpecifiedLineTradeSettlement>
    </ram:IncludedSupplyChainTradeLineItem>
    <ram:ApplicableHeaderTradeAgreement>
      <ram:SellerTradeParty><ram:Name>Bourdicaud SAS</ram:Name></ram:SellerTradeParty>
    </ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:SpecifiedTradeAllowanceCharge>
        <ram:ChargeIndicator><udt:Indicator>true</udt:Indicator></ram:ChargeIndicator>
        <ram:ActualAmount>15.00</ram:ActualAmount>
        <ram:CategoryTradeTax><ram:RateApplicablePercent>20</ram:RateApplicablePercent></ram:CategoryTradeTax>
        <ram:Reason>Frais de transport</ram:Reason>
      </ram:SpecifiedTradeAllowanceCharge>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:LineTotalAmount>185.00</ram:LineTotalAmount>
        <ram:TaxBasisTotalAmount>200.00</ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount>13.18</ram:TaxTotalAmount>
        <ram:GrandTotalAmount>213.18</ram:GrandTotalAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""


def _pdf_facturx() -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Facture Bourdicaud FX-2026-001")
    doc.embfile_add("factur-x.xml", _XML_FACTURX.encode("utf-8"), filename="factur-x.xml")
    data = doc.tobytes()
    doc.close()
    return data


def _pdf_ordinaire() -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Scan sans XML")
    data = doc.tobytes()
    doc.close()
    return data


# ─── Lecteur Factur-X (unitaire) ────────────────────────────────────────────

def test_facturx_reader_extrait_les_donnees():
    from src.facturx_reader import lire_facture_pdf
    data = lire_facture_pdf(_pdf_facturx())
    assert data is not None
    assert data["source"] == "facturx"
    assert data["fournisseur"] == "Bourdicaud SAS"
    assert data["numero_facture"] == "FX-2026-001"
    assert data["date_facture"] == "2026-07-05"
    assert len(data["lignes"]) == 1
    assert data["lignes"][0]["unite_prix"] == "kg"
    assert data["lignes"][0]["code_article"] == "BOEUF01"
    assert len(data["annexes"]) == 1
    assert data["annexes"][0]["type_ligne"] == "transport"
    assert data["total_ttc"] == 213.18


def test_facturx_reader_pdf_ordinaire_renvoie_none():
    from src.facturx_reader import lire_facture_pdf
    assert lire_facture_pdf(_pdf_ordinaire()) is None


# ─── Import via l'API ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_importer_document_facturx(app_client, db):
    ids = await _setup(app_client, db)
    fac = (await app_client.post(
        f"/api/achats/factures/depuis-reception/{ids['reception_id']}")).json()

    r = await app_client.post(
        f"/api/achats/factures/{fac['id']}/importer-document",
        files={"fichier": ("facture.pdf", _pdf_facturx(), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["source"] == "facturx"
    assert data["has_facturx"] is True
    assert data["numero_facture"] == "FX-2026-001"
    assert len(data["lignes"]) == 1
    assert len(data["annexes"]) == 1

    # Le document est conservé (facture_documents)
    cur = await db.execute(
        "SELECT COUNT(*) AS n, MAX(has_facturx) AS fx FROM facture_documents WHERE facture_id = ?",
        (fac["id"],),
    )
    row = await cur.fetchone()
    assert row["n"] == 1
    assert row["fx"] == 1


@pytest.mark.asyncio
async def test_appliquer_import(app_client, db):
    """Application d'une extraction validée : remplace les lignes, reporte entête +
    totaux papier, recalcule montants (10 kg × 18,50 = 185) + annexe, bascule statut."""
    ids = await _setup(app_client, db)
    fac = (await app_client.post(
        f"/api/achats/factures/depuis-reception/{ids['reception_id']}")).json()

    r = await app_client.post(
        f"/api/achats/factures/{fac['id']}/appliquer-import",
        json={
            "numero_facture": "FX-2026-001",
            "date_facture": "2026-07-05",
            "total_ht_papier": 200.00,
            "total_ttc_papier": 213.18,
            "remplacer_lignes": True,
            "lignes": [
                {"designation": "Entrecote VBF", "code_article": "BOEUF01",
                 "type_ligne": "marchandise", "unite_prix": "kg",
                 "poids_facture_kg": 10.0, "prix_facture_ht": 18.50, "tva_pct": 5.5},
                {"designation": "Frais de transport", "type_ligne": "transport",
                 "montant_facture_ht": 15.00, "tva_pct": 20.0},
            ],
        },
    )
    assert r.status_code == 200, r.text
    facture = r.json()
    assert facture["numero_facture"] == "FX-2026-001"
    assert len(facture["lignes"]) == 2
    marchandise = [l for l in facture["lignes"] if l["type_ligne"] == "marchandise"]
    assert marchandise[0]["montant_facture_ht"] == pytest.approx(185.00)  # 10 × 18,50
    # Total facturé = marchandise + transport = 200,00 → boucle HT → rapprochée
    assert facture["montant_total_ht_facture"] == pytest.approx(200.00)
    assert facture["recap"]["total_ttc_calcule"] == pytest.approx(213.18, abs=0.02)
    assert facture["recap"]["boucle"] is True
    assert facture["statut"] == "rapprochee"


@pytest.mark.asyncio
async def test_reception_bl_id_expose_pour_bouton_bl(app_client, db):
    """get_facture expose reception_bl_id (réception liée directement OU via commande
    mappée) → pilote l'affichage du bouton « importer depuis le BL »."""
    ids = await _setup(app_client, db)
    fac = (await app_client.post(
        f"/api/achats/factures/depuis-reception/{ids['reception_id']}")).json()

    detail = (await app_client.get(f"/api/achats/factures/{fac['id']}")).json()
    # Cette facture est reliée à la réception (directement et/ou via commande)
    assert detail["reception_bl_id"] == ids["reception_id"]

    # Une facture manuelle sans aucun lien → reception_bl_id null (bouton masqué)
    manuelle = (await app_client.post("/api/achats/factures", json={
        "fournisseur_id": ids["fournisseur_id"], "lignes": [],
    })).json()
    detail2 = (await app_client.get(f"/api/achats/factures/{manuelle['id']}")).json()
    assert detail2["reception_bl_id"] is None


@pytest.mark.asyncio
async def test_import_respecte_verrou(app_client, db):
    ids = await _setup(app_client, db)
    fac = (await app_client.post(
        f"/api/achats/factures/depuis-reception/{ids['reception_id']}")).json()
    await app_client.put(f"/api/achats/factures/{fac['id']}",
                         json={"numero_facture": "FA-V", "statut": "validee"})

    r = await app_client.post(
        f"/api/achats/factures/{fac['id']}/importer-document",
        files={"fichier": ("facture.pdf", _pdf_facturx(), "application/pdf")},
    )
    assert r.status_code == 409
    r = await app_client.post(
        f"/api/achats/factures/{fac['id']}/appliquer-import",
        json={"remplacer_lignes": True, "lignes": []},
    )
    assert r.status_code == 409

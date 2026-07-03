"""
test_liaison_vente_achat.py — Liaison bidirectionnelle catalogue vente ↔ achat.

Couvre le sens VENTE → ACHAT (nouveau) : depuis un produit de vente on retrouve les
articles d'achat (recherche-achats), on crée le groupe de comparaison (from-vente),
on rattache l'article d'achat (lignes) puis on le désigne comme référence
(reference) → la marge devient calculable. C'est le flux exact déclenché par la
modale « Relier à un article d'achat » du catalogue de vente.
"""
import pytest


async def _fournisseur(client, nom):
    r = await client.post("/api/achats/fournisseurs", json={"nom": nom})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _article(client, fournisseur_id, code, designation, **kw):
    body = {
        "fournisseur_id": fournisseur_id,
        "code_article": code,
        "designation": designation,
        "prix_achat_ht": kw.pop("prix_achat_ht", 10.0),
        "format_prix": kw.pop("format_prix", "kg"),
    }
    body.update(kw)
    r = await client.post("/api/achats/catalogue", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _produit_vente(client, nom, **kw):
    body = {"nom": nom}
    body.update(kw)
    r = await client.post("/api/vente/catalogue", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_recherche_achats_renvoie_prix_kg_et_groupe(app_client, db):
    """recherche-achats trouve l'article (nom/code) avec son €/kg ; sans groupe → groupe_id null."""
    fid = await _fournisseur(app_client, "Boucherie Test")
    await _article(app_client, fid, "ENT01", "Entrecôte de bœuf",
                   prix_achat_ht=18.0, format_prix="kg")

    r = await app_client.get("/api/achats/comparatif/recherche-achats?q=Entrecôte")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 1
    art = data["articles"][0]
    assert art["designation"] == "Entrecôte de bœuf"
    assert art["prix_kg"] == pytest.approx(18.0)   # format kg → €/kg = prix brut
    assert art["groupe_id"] is None                 # pas encore relié

    # Recherche par code article aussi.
    r2 = await app_client.get("/api/achats/comparatif/recherche-achats?q=ENT01")
    assert r2.json()["total"] == 1


@pytest.mark.asyncio
async def test_flux_vente_vers_achat_calcule_la_marge(app_client, db):
    """Flux complet : produit de vente → from-vente → lignes → reference → marge OK."""
    fid = await _fournisseur(app_client, "Boucherie Test")
    achat = await _article(app_client, fid, "ENT01", "Entrecôte de bœuf",
                           prix_achat_ht=18.0, format_prix="kg")
    vente = await _produit_vente(app_client, "Entrecôte", prix_vente_ttc=30.0,
                                 tva_percent=5.5, unite_vente="kg")

    # 1) Le produit apparaît dans recherche-achats côté "cible" — ici on vérifie surtout
    #    que l'article d'achat est bien trouvable.
    r = await app_client.get("/api/achats/comparatif/recherche-achats?q=Entrecôte")
    assert any(a["id"] == achat for a in r.json()["articles"])

    # 2) Créer le groupe depuis le produit de vente.
    rg = await app_client.post("/api/achats/comparatif/groupes/from-vente",
                               json={"catalogue_vente_id": vente})
    assert rg.status_code == 201, rg.text
    groupe = rg.json()["id"]

    # 3) Rattacher l'article d'achat au groupe.
    rl = await app_client.post(f"/api/achats/comparatif/groupes/{groupe}/lignes",
                               json={"catalogue_fournisseur_id": achat})
    assert rl.status_code == 201, rl.text

    # 4) Définir cet achat comme référence du produit de vente → marge calculable.
    rr = await app_client.put(
        f"/api/achats/comparatif/groupes/{groupe}/ventes/{vente}/reference",
        json={"ligne_choisie_id": achat},
    )
    assert rr.status_code == 200, rr.text
    detail = rr.json()
    pv = next(p for p in detail["produits_vente"] if p["id"] == vente)
    marge = pv["marge"]
    assert marge is not None
    # Vente HT = 30 / 1.055 ≈ 28.44 ; coût = 18 → marge ≈ 10.44 €/kg.
    assert marge["marge"] == pytest.approx(30 / 1.055 - 18.0, abs=0.01)

    # 5) recherche-achats reflète désormais le rattachement (groupe_id renseigné).
    r2 = await app_client.get("/api/achats/comparatif/recherche-achats?q=Entrecôte")
    art = next(a for a in r2.json()["articles"] if a["id"] == achat)
    assert art["groupe_id"] == groupe


@pytest.mark.asyncio
async def test_from_vente_refuse_doublon(app_client, db):
    """Un produit de vente déjà relié à un groupe → 409 (cardinalité vente unique)."""
    vente = await _produit_vente(app_client, "Saucisse", prix_vente_ttc=12.0)
    r1 = await app_client.post("/api/achats/comparatif/groupes/from-vente",
                               json={"catalogue_vente_id": vente})
    assert r1.status_code == 201, r1.text
    r2 = await app_client.post("/api/achats/comparatif/groupes/from-vente",
                               json={"catalogue_vente_id": vente})
    assert r2.status_code == 409, r2.text

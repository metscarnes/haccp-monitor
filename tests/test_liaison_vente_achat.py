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
    # prix_piece exposé aussi (nécessaire à la marge à la pièce côté vente).
    assert "prix_piece" in art


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
async def test_creation_article_renvoie_prix_kg_et_prix_piece(app_client, db):
    """POST /catalogue renvoie prix_kg + prix_piece dérivés (pour la marge/poids à la vente)."""
    fid = await _fournisseur(app_client, "Boucherie Test")

    # Format kg : prix_kg = prix brut ; prix_piece dérivé du poids d'une pièce.
    r = await app_client.post("/api/achats/catalogue", json={
        "fournisseur_id": fid, "code_article": "KG01", "designation": "Bavette",
        "prix_achat_ht": 18.0, "format_prix": "kg", "poids_unitaire_kg": 0.2,
    })
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["prix_kg"] == pytest.approx(18.0)
    assert a["prix_piece"] == pytest.approx(18.0 * 0.2)   # kg → prix pièce = €/kg × poids

    # Format colis : prix_kg = prix ÷ poids colis ; prix_piece = prix ÷ qté.
    r2 = await app_client.post("/api/achats/catalogue", json={
        "fournisseur_id": fid, "code_article": "COL01", "designation": "Paupiette",
        "prix_achat_ht": 12.0, "format_prix": "colis",
        "qte_par_colis": 4, "poids_unitaire_kg": 0.15,
    })
    a2 = r2.json()
    assert a2["prix_piece"] == pytest.approx(12.0 / 4)             # 3 € la pièce
    assert a2["prix_kg"] == pytest.approx(12.0 / (4 * 0.15))       # ÷ poids colis (0.6 kg)


@pytest.mark.asyncio
async def test_prix_kg_viande_repli_legacy_sans_format(app_client, db):
    """Le format EXPLICITE prime, même pour la viande : colis avec poids → €/kg = prix ÷ poids
    colis. Le repli « viande = €/kg brut » ne s'applique QUE sur un format legacy/inconnu."""
    fid = await _fournisseur(app_client, "Boucherie Test")
    # Format colis explicite : la règle format prime → 16 / (8 × 1.0) = 2 €/kg.
    r = await app_client.post("/api/achats/catalogue", json={
        "fournisseur_id": fid, "code_article": "BAV01", "designation": "Bavette colis",
        "prix_achat_ht": 16.0, "format_prix": "colis",
        "qte_par_colis": 8, "poids_unitaire_kg": 1.0,
        "famille": "Viande", "sous_famille": "Boeuf",
    })
    assert r.json()["prix_kg"] == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_marge_limonade_kg_et_piece(app_client, db):
    """Cas limonade réel : bouteille 0,75 kg achetée 3,30 €/pièce, vendue 9,90 €. Marge sur HT.
    - au kg    : achat €/kg = 3,30/0,75 = 4,40 ; marge = 9,90/1,055 − 4,40 ≈ 4,98 (53 %).
    - à la pièce : coût = 3,30 € la pièce ; marge = 9,90/1,055 − 3,30 ≈ 6,08."""
    from src.api.routes_achats import _calc_marge, _prix_kg_article, _prix_piece_article

    # format 'piece' : le prix saisi EST le prix d'une pièce (3,30 €) ; poids 0,75 kg.
    art = {"format_prix": "piece", "prix_achat_ht": 3.30,
           "poids_unitaire_kg": 0.75, "famille": "Traiteur"}
    prix_kg    = _prix_kg_article(art)      # 3.30 / 0.75 = 4.40 €/kg
    prix_piece = _prix_piece_article(art)   # 3.30 € la pièce
    assert prix_kg == pytest.approx(4.40)
    assert prix_piece == pytest.approx(3.30)

    # Vente au kg 9,90 €/kg.
    mk = _calc_marge(9.90, 5.5, prix_kg, unite_vente="kg")
    assert mk["cout_matiere"] == pytest.approx(4.40)
    assert mk["marge"] == pytest.approx(9.90 / 1.055 - 4.40, abs=0.01)   # ≈ 4,98 €
    assert round(mk["taux_marge"] * 100) == 53

    # Vente à la pièce 9,90 € la bouteille → coût = 3,30 € (prix pièce, pas via le poids).
    mp = _calc_marge(9.90, 5.5, prix_kg, unite_vente="piece",
                     poids_piece_kg=0.75, achat_ref_piece=prix_piece)
    assert mp["cout_matiere"] == pytest.approx(3.30)
    assert mp["marge"] == pytest.approx(9.90 / 1.055 - 3.30, abs=0.01)


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


@pytest.mark.asyncio
async def test_lier_direct_et_voir_des_deux_cotes(app_client, db):
    """POST /comparatif/lier : crée le groupe, prend le 1er achat comme référence ; un 2e achat
    s'ajoute SANS voler la référence ; reference=True la bascule. Les deux vues de lecture
    (liaison-vente / liaison-achat) reflètent l'état."""
    fid = await _fournisseur(app_client, "Boucherie Test")
    a1 = await _article(app_client, fid, "ENT01", "Entrecôte A", prix_achat_ht=18.0)
    a2 = await _article(app_client, fid, "ENT02", "Entrecôte B", prix_achat_ht=16.0)
    vente = await _produit_vente(app_client, "Entrecôte", prix_vente_ttc=30.0,
                                 tva_percent=5.5, unite_vente="kg")

    # Non relié au départ.
    r0 = await app_client.get(f"/api/achats/comparatif/liaison-vente/{vente}")
    assert r0.status_code == 200 and r0.json()["groupe_id"] is None
    assert (await app_client.get(f"/api/achats/comparatif/liaison-achat/{a1}")).json()["ventes"] == []

    # 1er lien → groupe créé + référence = a1 + marge.
    r1 = await app_client.post("/api/achats/comparatif/lier",
                               json={"catalogue_vente_id": vente, "catalogue_fournisseur_id": a1})
    assert r1.status_code == 200, r1.text
    l1 = r1.json()
    assert l1["reference_id"] == a1
    assert l1["marge"]["marge"] == pytest.approx(30 / 1.055 - 18.0, abs=0.01)

    # 2e lien sans précision → ajouté, la référence reste a1.
    l2 = (await app_client.post("/api/achats/comparatif/lier",
                                json={"catalogue_vente_id": vente, "catalogue_fournisseur_id": a2})).json()
    assert l2["groupe_id"] == l1["groupe_id"]
    assert l2["reference_id"] == a1
    assert {a["id"] for a in l2["achats"]} == {a1, a2}
    assert l2["achats"][0]["id"] == a1 and l2["achats"][0]["est_reference"]

    # Côté achat : a2 voit la vente, sans en être la référence (réf = Entrecôte A).
    va = (await app_client.get(f"/api/achats/comparatif/liaison-achat/{a2}")).json()["ventes"]
    assert len(va) == 1 and va[0]["id"] == vente
    assert va[0]["est_reference"] is False
    assert va[0]["reference_designation"] == "Entrecôte A"

    # reference=True → bascule sur a2.
    l3 = (await app_client.post("/api/achats/comparatif/lier",
                                json={"catalogue_vente_id": vente, "catalogue_fournisseur_id": a2,
                                      "reference": True})).json()
    assert l3["reference_id"] == a2
    assert l3["marge"]["marge"] == pytest.approx(30 / 1.055 - 16.0, abs=0.01)
    vb = (await app_client.get(f"/api/achats/comparatif/liaison-achat/{a2}")).json()["ventes"]
    assert vb[0]["est_reference"] is True


@pytest.mark.asyncio
async def test_catalogue_vente_expose_achat_ref_pour_marge_en_direct(app_client, db):
    """GET /api/vente/catalogue renvoie le coût de l'achat de référence (marge en direct fiche)."""
    fid = await _fournisseur(app_client, "Boucherie Test")
    a1 = await _article(app_client, fid, "R1", "Rumsteck", prix_achat_ht=20.0)
    vente = await _produit_vente(app_client, "Rumsteck", prix_vente_ttc=35.0)
    seul = await _produit_vente(app_client, "Sans lien", prix_vente_ttc=10.0)
    await app_client.post("/api/achats/comparatif/lier",
                          json={"catalogue_vente_id": vente, "catalogue_fournisseur_id": a1})
    produits = {p["id"]: p for p in (await app_client.get("/api/vente/catalogue")).json()}
    ref = produits[vente]["achat_ref"]
    assert ref["prix_kg"] == pytest.approx(20.0)
    assert ref["designation"] == "Rumsteck" and ref["fournisseur_nom"] == "Boucherie Test"
    assert produits[seul]["achat_ref"] is None


@pytest.mark.asyncio
async def test_lier_reprend_reference_si_ancienne_inactive(app_client, db):
    """Groupe existant dont la référence a été désactivée : un nouveau lien la remplace."""
    fid = await _fournisseur(app_client, "Boucherie Test")
    a1 = await _article(app_client, fid, "X1", "Bavette A", prix_achat_ht=14.0)
    a2 = await _article(app_client, fid, "X2", "Bavette B", prix_achat_ht=15.0)
    vente = await _produit_vente(app_client, "Bavette", prix_vente_ttc=25.0)
    await app_client.post("/api/achats/comparatif/lier",
                          json={"catalogue_vente_id": vente, "catalogue_fournisseur_id": a1})
    await db.execute("UPDATE catalogue_fournisseur SET actif = 0 WHERE id = ?", (a1,))
    await db.commit()
    l = (await app_client.post("/api/achats/comparatif/lier",
                               json={"catalogue_vente_id": vente, "catalogue_fournisseur_id": a2})).json()
    assert l["reference_id"] == a2


@pytest.mark.asyncio
async def test_catalogue_achats_expose_ventes_liees_et_marge_cet_achat(app_client, db):
    """GET /achats/catalogue : chaque article porte ses produits de vente liés, avec la marge
    calculée sur CE coût d'achat — même quand l'achat sert plusieurs produits (escargots
    vendus ×12 et ×24) ou n'est pas la référence officielle du produit."""
    fid = await _fournisseur(app_client, "Dipsa Test")
    # Colis 16,45 € HT, 48 escargots, 500 g.
    esc = await _article(app_client, fid, "062303", "Escargots de Bourgogne",
                         prix_achat_ht=16.45, format_prix="colis",
                         qte_par_colis=48, poids_unitaire_kg=0.5 / 48)
    autre = await _article(app_client, fid, "AUT", "Escargots autre", prix_achat_ht=40.0)
    v12 = await _produit_vente(app_client, "Escargots x12", prix_vente_ttc=19.90,
                               tva_percent=5.5, unite_vente="piece", poids_piece_kg=0.125)
    v24 = await _produit_vente(app_client, "Escargots x24", prix_vente_ttc=36.00,
                               tva_percent=5.5, unite_vente="piece", poids_piece_kg=0.25)
    # x24 a pour référence un AUTRE achat ; on y ajoute quand même les escargots Dipsa.
    await app_client.post("/api/achats/comparatif/lier",
                          json={"catalogue_vente_id": v12, "catalogue_fournisseur_id": esc})
    await app_client.post("/api/achats/comparatif/lier",
                          json={"catalogue_vente_id": v24, "catalogue_fournisseur_id": autre})
    await app_client.post("/api/achats/comparatif/lier",
                          json={"catalogue_vente_id": v24, "catalogue_fournisseur_id": esc,
                                "reference": False})

    cat = {a["id"]: a for a in (await app_client.get("/api/achats/catalogue")).json()}
    ventes = {v["id"]: v for v in cat[esc]["ventes"]}
    assert set(ventes) == {v12, v24}
    assert ventes[v12]["est_reference"] is True
    assert ventes[v24]["est_reference"] is False
    # x12 : coût 32,90 €/kg × 0,125 = 4,1125 → coef 4,59, taux de marque 78 %.
    m12 = ventes[v12]["marge"]
    assert m12["cout_matiere"] == pytest.approx(4.1125, abs=1e-4)
    assert m12["coef"] == pytest.approx(4.587, abs=1e-3)
    assert m12["marge"] == pytest.approx(19.90 / 1.055 - 4.1125, abs=0.01)
    # x24 calculé sur CET achat (32,90 × 0,25), pas sur l'achat de référence à 40 €/kg.
    assert ventes[v24]["marge"]["cout_matiere"] == pytest.approx(8.225, abs=1e-4)
    # Article sans lien → liste vide.
    sans = await _article(app_client, fid, "SL", "Sans lien")
    cat2 = {a["id"]: a for a in (await app_client.get("/api/achats/catalogue")).json()}
    assert cat2[sans]["ventes"] == []

    # Vue détail côté achat : marge avec cet achat + marge officielle (sur l'autre achat).
    va = {v["id"]: v for v in (await app_client.get(
        f"/api/achats/comparatif/liaison-achat/{esc}")).json()["ventes"]}
    assert va[v24]["marge_cet_achat"]["cout_matiere"] == pytest.approx(8.225, abs=1e-4)
    assert va[v24]["marge"]["cout_matiere"] == pytest.approx(40.0 * 0.25, abs=1e-4)

"""
test_inventaire.py — Module Inventaire VALORISÉ (stock comptable en €).

Vérifie :
- création d'une session datée + ajout de lignes valorisées (kg / colis / pièce) ;
- valorisation €/kg figée depuis le catalogue (via _calc_prix_kg, règle Viande) ;
- conversion colis → kg (poids_colis_kg) et pièce → kg (poids saisi / catalogue) ;
- cas non valorisable honnêtement (prix absent / pièce sans poids) → valeur None,
  quantité conservée ;
- total recalculé, clôture qui fige la valeur, verrouillage après clôture ;
- recherche catalogue + familles.
"""
import pytest


async def _fournisseur(client, nom="Bourdicaud"):
    r = await client.post("/api/achats/fournisseurs", json={"nom": nom})
    return r.json()["id"]


async def _article(client, fid, **kw):
    payload = {
        "fournisseur_id": fid,
        "code_article": kw.get("code_article", "A01"),
        "designation": kw.get("designation", "Article"),
        "prix_achat_ht": kw.get("prix_achat_ht", 10.0),
        "format_prix": kw.get("format_prix", "kg"),
    }
    for k in ("famille", "sous_famille", "poids_colis_kg", "qte_par_colis",
              "poids_unitaire_kg"):
        if k in kw:
            payload[k] = kw[k]
    r = await client.post("/api/achats/catalogue", json=payload)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


async def _session(client, **kw):
    r = await client.post("/api/inventaire/sessions", json=kw)
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_ligne_kg_viande_valorisee(app_client, db):
    """Viande au kg : valeur = quantité × prix_achat_ht (€/kg direct)."""
    fid = await _fournisseur(app_client)
    cat = await _article(app_client, fid, designation="Côte de boeuf",
                         prix_achat_ht=18.0, format_prix="kg", famille="Viande")
    inv = await _session(app_client, libelle="Test")

    r = await app_client.post(f"/api/inventaire/sessions/{inv}/lignes", json={
        "catalogue_fournisseur_id": cat, "quantite": 9.4, "unite_saisie": "kg",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["prix_kg_fige"] == 18.0
    assert body["poids_kg_calcule"] == 9.4
    assert body["valeur_ht"] == pytest.approx(169.2, abs=0.01)
    assert body["total_ht"] == pytest.approx(169.2, abs=0.01)


@pytest.mark.anyio
async def test_ligne_colis_converti_en_kg(app_client, db):
    """Article au colis : valeur = nb_colis × poids_colis_kg × (prix_colis / poids_colis)."""
    fid = await _fournisseur(app_client)
    # colis de 5 kg à 40 € → 8 €/kg (poids_colis_kg = 10 × 0.5, calculé côté API)
    cat = await _article(app_client, fid, designation="Saucisson",
                         prix_achat_ht=40.0, format_prix="colis",
                         qte_par_colis=10, poids_unitaire_kg=0.5, famille="Charcuterie")
    inv = await _session(app_client)

    r = await app_client.post(f"/api/inventaire/sessions/{inv}/lignes", json={
        "catalogue_fournisseur_id": cat, "quantite": 3, "unite_saisie": "colis",
    })
    body = r.json()
    assert body["prix_kg_fige"] == 8.0
    assert body["poids_kg_calcule"] == 15.0       # 3 × 5 kg
    assert body["valeur_ht"] == pytest.approx(120.0, abs=0.01)  # 15 × 8


@pytest.mark.anyio
async def test_ligne_piece_poids_saisi(app_client, db):
    """Pièce avec poids saisi par l'opérateur : valeur = nb × poids_piece × €/kg."""
    fid = await _fournisseur(app_client)
    cat = await _article(app_client, fid, designation="Terrine",
                         prix_achat_ht=12.0, format_prix="kg", famille="Traiteur")
    inv = await _session(app_client)

    r = await app_client.post(f"/api/inventaire/sessions/{inv}/lignes", json={
        "catalogue_fournisseur_id": cat, "quantite": 4,
        "unite_saisie": "piece", "poids_piece_kg": 0.25,
    })
    body = r.json()
    assert body["poids_kg_calcule"] == 1.0        # 4 × 0.25
    assert body["valeur_ht"] == pytest.approx(12.0, abs=0.01)


@pytest.mark.anyio
async def test_ligne_piece_sans_poids_non_valorisee(app_client, db):
    """Pièce sans poids saisi ni dérivable du catalogue → valeur None, quantité gardée."""
    fid = await _fournisseur(app_client)
    cat = await _article(app_client, fid, designation="Bocal",
                         prix_achat_ht=12.0, format_prix="kg")
    inv = await _session(app_client)

    r = await app_client.post(f"/api/inventaire/sessions/{inv}/lignes", json={
        "catalogue_fournisseur_id": cat, "quantite": 4, "unite_saisie": "piece",
    })
    body = r.json()
    assert body["poids_kg_calcule"] is None
    assert body["valeur_ht"] is None
    assert body["total_ht"] == 0.0

    # La ligne existe quand même (quantité enregistrée, valeur indisponible)
    r = await app_client.get(f"/api/inventaire/sessions/{inv}")
    detail = r.json()
    assert detail["nb_lignes"] == 1
    assert detail["nb_non_valorisees"] == 1


@pytest.mark.anyio
async def test_modifier_et_supprimer_ligne(app_client, db):
    fid = await _fournisseur(app_client)
    cat = await _article(app_client, fid, prix_achat_ht=10.0, format_prix="kg", famille="Viande")
    inv = await _session(app_client)
    r = await app_client.post(f"/api/inventaire/sessions/{inv}/lignes", json={
        "catalogue_fournisseur_id": cat, "quantite": 2, "unite_saisie": "kg",
    })
    ligne_id = r.json()["id"]
    assert r.json()["total_ht"] == pytest.approx(20.0)

    # Corriger la quantité → revalorise
    r = await app_client.put(f"/api/inventaire/lignes/{ligne_id}", json={"quantite": 5})
    assert r.json()["valeur_ht"] == pytest.approx(50.0)
    assert r.json()["total_ht"] == pytest.approx(50.0)

    # Supprimer
    r = await app_client.delete(f"/api/inventaire/lignes/{ligne_id}")
    assert r.json()["total_ht"] == 0.0


@pytest.mark.anyio
async def test_cloture_fige_total_et_verrouille(app_client, db):
    fid = await _fournisseur(app_client)
    cat = await _article(app_client, fid, prix_achat_ht=10.0, format_prix="kg", famille="Viande")
    inv = await _session(app_client)
    await app_client.post(f"/api/inventaire/sessions/{inv}/lignes", json={
        "catalogue_fournisseur_id": cat, "quantite": 3, "unite_saisie": "kg",
    })

    r = await app_client.put(f"/api/inventaire/sessions/{inv}/cloturer")
    assert r.status_code == 200, r.text
    assert r.json()["valeur_totale_ht"] == pytest.approx(30.0)

    # Re-clôture interdite
    r = await app_client.put(f"/api/inventaire/sessions/{inv}/cloturer")
    assert r.status_code == 409

    # Ajout interdit après clôture
    r = await app_client.post(f"/api/inventaire/sessions/{inv}/lignes", json={
        "catalogue_fournisseur_id": cat, "quantite": 1, "unite_saisie": "kg",
    })
    assert r.status_code == 409

    # Le détail expose le total figé
    r = await app_client.get(f"/api/inventaire/sessions/{inv}")
    assert r.json()["total_ht"] == pytest.approx(30.0)
    assert r.json()["inventaire"]["statut"] == "cloture"


@pytest.mark.anyio
async def test_ligne_hors_catalogue_designation_libre(app_client, db):
    """Article hors catalogue : designation_libre acceptée, valeur indisponible."""
    inv = await _session(app_client)
    r = await app_client.post(f"/api/inventaire/sessions/{inv}/lignes", json={
        "designation_libre": "Article divers", "quantite": 2, "unite_saisie": "kg",
    })
    assert r.status_code == 201, r.text
    assert r.json()["valeur_ht"] is None

    # Ni catalogue ni designation → 422
    r = await app_client.post(f"/api/inventaire/sessions/{inv}/lignes", json={
        "quantite": 1, "unite_saisie": "kg",
    })
    assert r.status_code == 422

    # Article catalogue inexistant → 404 propre (pas un 500 SQLite)
    r = await app_client.post(f"/api/inventaire/sessions/{inv}/lignes", json={
        "catalogue_fournisseur_id": 999999, "quantite": 1, "unite_saisie": "kg",
    })
    assert r.status_code == 404


@pytest.mark.anyio
async def test_memoriser_poids_piece(app_client, db):
    """Le poids unitaire saisi à la pièce est mémorisé → ligne suivante valorisée auto."""
    fid = await _fournisseur(app_client)
    cat = await _article(app_client, fid, designation="Bocal terrine",
                         prix_achat_ht=12.0, format_prix="kg", famille="Traiteur")
    inv = await _session(app_client)

    # Sans poids connu → ligne pièce non valorisée
    r = await app_client.post(f"/api/inventaire/sessions/{inv}/lignes", json={
        "catalogue_fournisseur_id": cat, "quantite": 2, "unite_saisie": "piece",
    })
    assert r.json()["valeur_ht"] is None

    # On mémorise le poids d'une pièce (0.3 kg)
    r = await app_client.put(f"/api/inventaire/catalogue/{cat}/poids-piece",
                             json={"poids_unitaire_kg": 0.3})
    assert r.status_code == 200, r.text

    # Nouvelle ligne pièce SANS poids saisi → valorisée via le poids mémorisé
    r = await app_client.post(f"/api/inventaire/sessions/{inv}/lignes", json={
        "catalogue_fournisseur_id": cat, "quantite": 2, "unite_saisie": "piece",
    })
    assert r.json()["poids_kg_calcule"] == pytest.approx(0.6)   # 2 × 0.3
    assert r.json()["valeur_ht"] == pytest.approx(7.2)          # 0.6 × 12


@pytest.mark.anyio
async def test_recherche_catalogue_et_familles(app_client, db):
    fid = await _fournisseur(app_client)
    await _article(app_client, fid, code_article="CB01", designation="Côte de boeuf",
                   prix_achat_ht=18.0, format_prix="kg", famille="Viande", sous_famille="Boeuf")
    await _article(app_client, fid, code_article="SAU1", designation="Saucisson sec",
                   prix_achat_ht=40.0, format_prix="colis", qte_par_colis=10,
                   poids_unitaire_kg=0.5, famille="Charcuterie")

    r = await app_client.get("/api/inventaire/catalogue-recherche", params={"q": "boeuf"})
    arts = r.json()["articles"]
    assert len(arts) == 1
    assert arts[0]["prix_kg"] == 18.0

    r = await app_client.get("/api/inventaire/catalogue-recherche", params={"famille": "Charcuterie"})
    arts = r.json()["articles"]
    assert len(arts) == 1
    assert arts[0]["prix_kg"] == 8.0      # 40 / 5

    r = await app_client.get("/api/inventaire/familles")
    fams = {f["famille"]: f for f in r.json()["familles"]}
    assert "Viande" in fams and "Charcuterie" in fams
    assert any(sf["nom"] == "Boeuf" for sf in fams["Viande"]["sous_familles"])

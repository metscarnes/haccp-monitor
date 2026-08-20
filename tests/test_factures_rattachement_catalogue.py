"""
test_factures_rattachement_catalogue.py — Prévention des lignes facture orphelines.

Contexte : 707 lignes / 38 245 € HT s'étaient retrouvées sans `catalogue_fournisseur_id`
sur ~2 mois (invisibles dans l'analyse achats). Le premier correctif ne couvrait que
l'import OCR, et seulement par code_article STRICT — inopérant en réel puisque le code
du papier n'est pas celui du catalogue (Elivia « 07991-07 » vs « 7991-7 »).

Règles testées ici :
- création manuelle et ajout de ligne rattachent aussi au catalogue (chemins qui
  n'étaient pas protégés du tout) ;
- la cascade tolère les écarts de format de code réels (zéros, séparateurs, suffixe) ;
- AUCUN blocage en saisie : une marchandise hors catalogue passe, avec des suggestions ;
- les suggestions classent par similarité de libellé PUIS par fréquence de réception ;
- une ligne annexe (transport/taxe) n'est jamais rattachée ni signalée ;
- un article catalogue d'un AUTRE fournisseur est refusé (incohérence jamais légitime).
"""
import pytest

from test_factures_refonte_etape0 import _setup


async def _creer_article(client, fournisseur_id, code, designation, prix=10.0):
    r = await client.post("/api/achats/catalogue", json={
        "fournisseur_id": fournisseur_id, "code_article": code,
        "designation": designation, "prix_achat_ht": prix, "format_prix": "kg",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("code_papier", ["ART01", "0ART01", "ART-01", " art01 "])
async def test_creation_manuelle_rattache_au_catalogue(app_client, db, code_papier):
    """Facture saisie à la main (sans réception) : le lien doit être retrouvé depuis le
    catalogue du fournisseur, quel que soit le format du code lu sur le papier."""
    ids = await _setup(app_client, db)
    r = await app_client.post("/api/achats/factures", json={
        "fournisseur_id": ids["fournisseur_id"],
        "numero_facture": "FA-MANUELLE-1",
        "lignes": [{"designation": "Libelle du papier", "code_article": code_papier,
                    "type_ligne": "marchandise", "unite_prix": "kg",
                    "poids_facture_kg": 5.0, "prix_facture_ht": 12.0}],
    })
    assert r.status_code == 201, r.text
    ligne = [l for l in r.json()["lignes"] if l["type_ligne"] == "marchandise"][0]
    assert ligne["catalogue_fournisseur_id"] == ids["cat_id"]


@pytest.mark.asyncio
async def test_creation_manuelle_rattache_par_designation(app_client, db):
    """Sans code_article exploitable, la désignation identique suffit."""
    ids = await _setup(app_client, db)
    r = await app_client.post("/api/achats/factures", json={
        "fournisseur_id": ids["fournisseur_id"],
        "numero_facture": "FA-MANUELLE-2",
        "lignes": [{"designation": "  article refonte  ", "type_ligne": "marchandise",
                    "unite_prix": "kg", "poids_facture_kg": 5.0, "prix_facture_ht": 12.0}],
    })
    assert r.status_code == 201, r.text
    ligne = [l for l in r.json()["lignes"] if l["type_ligne"] == "marchandise"][0]
    assert ligne["catalogue_fournisseur_id"] == ids["cat_id"]


@pytest.mark.asyncio
async def test_ajout_ligne_rattache_et_ne_bloque_jamais(app_client, db):
    """Ajout d'une ligne sur une facture existante : rattachement automatique si
    possible, et SURTOUT aucun blocage si l'article est inconnu — une saisie ne doit
    jamais être empêchée parce qu'une fiche catalogue manque."""
    ids = await _setup(app_client, db)
    fac = (await app_client.post(
        f"/api/achats/factures/depuis-reception/{ids['reception_id']}")).json()

    r = await app_client.post(f"/api/achats/factures/{fac['id']}/lignes", json={
        "designation": "Article refonte", "code_article": "ART01",
        "type_ligne": "marchandise", "unite_prix": "kg",
        "poids_facture_kg": 2.0, "prix_facture_ht": 12.0})
    assert r.status_code == 201, r.text
    assert r.json()["catalogue_fournisseur_id"] == ids["cat_id"]

    r = await app_client.post(f"/api/achats/factures/{fac['id']}/lignes", json={
        "designation": "Article totalement inconnu", "code_article": "ZZ999",
        "type_ligne": "marchandise", "unite_prix": "kg",
        "poids_facture_kg": 1.0, "prix_facture_ht": 9.0})
    assert r.status_code == 201, r.text
    assert r.json()["catalogue_fournisseur_id"] is None
    assert "suggestions_catalogue" in r.json()


@pytest.mark.asyncio
async def test_ligne_annexe_jamais_rattachee_ni_signalee(app_client, db):
    """Transport/taxe/remise n'ont légitimement aucun article catalogue : ni tentative
    de rattachement, ni signalement (127 lignes de ce type en prod, toutes normales)."""
    ids = await _setup(app_client, db)
    fac = (await app_client.post(
        f"/api/achats/factures/depuis-reception/{ids['reception_id']}")).json()

    r = await app_client.post(f"/api/achats/factures/{fac['id']}/lignes", json={
        "designation": "Article refonte", "type_ligne": "transport",
        "montant_facture_ht": 7.5})
    assert r.status_code == 201, r.text
    assert r.json()["catalogue_fournisseur_id"] is None

    r = await app_client.get(f"/api/achats/factures/{fac['id']}/lignes-non-rattachees")
    assert r.status_code == 200, r.text
    assert all(l["designation"] != "Article refonte" or l["id"] != r.json()["nb"]
               for l in r.json()["lignes"])
    assert r.json()["nb"] == 0


@pytest.mark.asyncio
async def test_refus_article_autre_fournisseur(app_client, db):
    """Rattacher un article du fournisseur B sur une facture du fournisseur A
    imputerait l'achat au mauvais fournisseur : incohérence refusée."""
    ids = await _setup(app_client, db)
    r = await app_client.post("/api/achats/fournisseurs", json={"nom": "Autre Fournisseur"})
    assert r.status_code == 201, r.text
    autre_id = r.json()["id"]
    cat_autre = await _creer_article(app_client, autre_id, "XX01", "Article de l autre")

    r = await app_client.post("/api/achats/factures", json={
        "fournisseur_id": ids["fournisseur_id"],
        "numero_facture": "FA-INCOHERENTE",
        "lignes": [{"designation": "Article de l autre", "code_article": "XX01",
                    "catalogue_fournisseur_id": cat_autre, "type_ligne": "marchandise",
                    "unite_prix": "kg", "poids_facture_kg": 1.0, "prix_facture_ht": 5.0}],
    })
    assert r.status_code == 422, r.text
    assert "fournisseur" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_suggestions_classees_par_similarite(app_client, db):
    """Une ligne non rattachée doit proposer l'article au libellé le plus proche."""
    ids = await _setup(app_client, db)
    await _creer_article(app_client, ids["fournisseur_id"], "BF01", "Entrecote de boeuf VBF")
    await _creer_article(app_client, ids["fournisseur_id"], "PO01", "Poitrine de porc fumee")

    fac = (await app_client.post(
        f"/api/achats/factures/depuis-reception/{ids['reception_id']}")).json()
    await app_client.post(f"/api/achats/factures/{fac['id']}/lignes", json={
        "designation": "ENTRECOTE BOEUF VBF", "code_article": "ZZZ",
        "type_ligne": "marchandise", "unite_prix": "kg",
        "poids_facture_kg": 3.0, "prix_facture_ht": 18.0})

    r = await app_client.get(f"/api/achats/factures/{fac['id']}/lignes-non-rattachees")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["nb"] == 1
    suggestions = data["lignes"][0]["suggestions"]
    assert suggestions, "au moins une suggestion attendue"
    assert suggestions[0]["code_article"] == "BF01"


@pytest.mark.asyncio
async def test_recherche_catalogue_priorise_les_plus_recus(app_client, db):
    """« On commande toujours la même chose » : à défaut de terme de recherche, les
    articles les plus RÉCEPTIONNÉS sur 6 mois remontent en tête."""
    ids = await _setup(app_client, db)
    jamais_recu = await _creer_article(
        app_client, ids["fournisseur_id"], "RARE01", "Article jamais recu")

    r = await app_client.get(
        f"/api/achats/catalogue/recherche?fournisseur_id={ids['fournisseur_id']}")
    assert r.status_code == 200, r.text
    articles = r.json()["articles"]
    assert articles, "le catalogue du fournisseur doit remonter"
    # L'article de la réception du _setup a été reçu ; l'autre jamais.
    par_id = {a["id"]: a for a in articles}
    assert par_id[ids["cat_id"]]["nb_receptions_6mois"] >= 1
    assert par_id[jamais_recu]["nb_receptions_6mois"] == 0
    assert articles[0]["id"] == ids["cat_id"]


@pytest.mark.asyncio
async def test_rattachement_manuel_depuis_ecran(app_client, db):
    """Le bouton « Rattacher » de l'écran : PUT du seul catalogue_fournisseur_id sur la
    ligne, après quoi elle disparaît du signalement."""
    ids = await _setup(app_client, db)
    cible = await _creer_article(
        app_client, ids["fournisseur_id"], "BF01", "Entrecote de boeuf VBF", 18.5)
    fac = (await app_client.post(
        f"/api/achats/factures/depuis-reception/{ids['reception_id']}")).json()
    ligne = (await app_client.post(f"/api/achats/factures/{fac['id']}/lignes", json={
        "designation": "Libelle illisible OCR", "code_article": "ZZZ",
        "type_ligne": "marchandise", "unite_prix": "kg",
        "poids_facture_kg": 3.0, "prix_facture_ht": 18.5})).json()
    assert ligne["catalogue_fournisseur_id"] is None

    r = await app_client.get(f"/api/achats/factures/{fac['id']}/lignes-non-rattachees")
    assert r.json()["nb"] == 1

    r = await app_client.put(
        f"/api/achats/factures/{fac['id']}/lignes/{ligne['id']}",
        json={"catalogue_fournisseur_id": cible},
    )
    assert r.status_code == 200, r.text
    assert r.json()["catalogue_fournisseur_id"] == cible

    r = await app_client.get(f"/api/achats/factures/{fac['id']}/lignes-non-rattachees")
    assert r.json()["nb"] == 0


@pytest.mark.asyncio
async def test_rattachement_manuel_refuse_autre_fournisseur(app_client, db):
    """Même garde-fou sur le rattachement manuel que sur la création : impossible de
    pointer un article appartenant à un autre fournisseur."""
    ids = await _setup(app_client, db)
    autre_id = (await app_client.post(
        "/api/achats/fournisseurs", json={"nom": "Autre Fournisseur"})).json()["id"]
    cat_autre = await _creer_article(app_client, autre_id, "XX01", "Article de l autre")
    fac = (await app_client.post(
        f"/api/achats/factures/depuis-reception/{ids['reception_id']}")).json()
    ligne = [l for l in fac["lignes"] if l["type_ligne"] == "marchandise"][0]

    r = await app_client.put(
        f"/api/achats/factures/{fac['id']}/lignes/{ligne['id']}",
        json={"catalogue_fournisseur_id": cat_autre},
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_recherche_catalogue_par_texte_et_par_code(app_client, db):
    """La recherche accepte un fragment de libellé comme un code, même mal formaté."""
    ids = await _setup(app_client, db)
    await _creer_article(app_client, ids["fournisseur_id"], "BF01", "Entrecote de boeuf VBF")

    r = await app_client.get(
        f"/api/achats/catalogue/recherche?fournisseur_id={ids['fournisseur_id']}&q=entrecote")
    assert r.status_code == 200, r.text
    assert any(a["code_article"] == "BF01" for a in r.json()["articles"])

    r = await app_client.get(
        f"/api/achats/catalogue/recherche?fournisseur_id={ids['fournisseur_id']}&q=0ART01")
    assert r.status_code == 200, r.text
    assert any(a["id"] == ids["cat_id"] for a in r.json()["articles"])

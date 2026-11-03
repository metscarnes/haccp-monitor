"""
Réception — brouillon de saisie (reprise après rafraîchissement de la page).

Les cartes de la liste commande ne deviennent des lignes de réception qu'à la
validation. Entre-temps, leur contenu est sauvegardé sur la fiche (PUT
/receptions/{id}/brouillon) : il doit être relu à la reprise, compté dans le
bandeau « réception non terminée », n'écrire AUCUNE ligne (donc rien au stock)
et disparaître à la clôture.
"""
import pytest


async def _fiche(app_client, db):
    await db.execute("INSERT OR IGNORE INTO personnel (boutique_id, prenom) VALUES (1, 'Brouillon')")
    cur = await db.execute("SELECT id FROM personnel WHERE prenom = 'Brouillon'")
    pid = (await cur.fetchone())[0]
    fid = (await db.execute(
        "INSERT INTO fournisseurs (boutique_id, nom) VALUES (1, 'Fourn Brouillon')")).lastrowid
    await db.commit()
    r = await app_client.post("/api/receptions", data={
        "personnel_id": str(pid), "heure_reception": "07:30", "temperature_camion": "2",
        "fournisseur_principal_id": str(fid)})
    assert r.status_code == 201, r.text
    return r.json()["id"]


BROUILLON = {
    "version": 1,
    "titre": "Articles de la commande",
    "ocrFait": True,
    "cartes": [
        {"designation": "Entrecôte", "lot": "L123", "date": "2099-01-10", "poids": "4.2",
         "prix": "18.5", "unitePrix": "kg", "recu": True,
         "lotsSupp": [{"lot": "L124", "dlc": "2099-01-12", "poids": "1.1", "interne": False}]},
        {"designation": "Merguez", "lot": "", "poids": "", "recu": False, "lotsSupp": []},
    ],
}


@pytest.mark.anyio
async def test_brouillon_sauve_relu_et_compte(app_client, db):
    rid = await _fiche(app_client, db)

    r = await app_client.put(f"/api/receptions/{rid}/brouillon", json={"brouillon": BROUILLON})
    assert r.status_code == 200, r.text

    # Relu tel quel à la reprise
    detail = (await app_client.get(f"/api/receptions/{rid}")).json()
    assert detail["brouillon"] == BROUILLON
    assert "brouillon_saisie" not in detail

    # Bandeau « non terminée » : produits en cours de saisie comptés, 0 ligne en base
    fiches = (await app_client.get("/api/receptions/non-terminees")).json()
    fiche = next(f for f in fiches if f["id"] == rid)
    assert fiche["nb_brouillon"] == 2
    assert fiche["nb_lignes"] == 0
    assert "brouillon_saisie" not in fiche

    # Aucune ligne de réception écrite → rien au stock
    cur = await db.execute("SELECT COUNT(*) FROM reception_lignes WHERE reception_id = ?", (rid,))
    assert (await cur.fetchone())[0] == 0


@pytest.mark.anyio
async def test_brouillon_efface_par_null(app_client, db):
    rid = await _fiche(app_client, db)
    await app_client.put(f"/api/receptions/{rid}/brouillon", json={"brouillon": BROUILLON})
    r = await app_client.put(f"/api/receptions/{rid}/brouillon", json={"brouillon": None})
    assert r.status_code == 200, r.text
    assert (await app_client.get(f"/api/receptions/{rid}")).json()["brouillon"] is None
    fiches = (await app_client.get("/api/receptions/non-terminees")).json()
    assert next(f for f in fiches if f["id"] == rid)["nb_brouillon"] == 0


@pytest.mark.anyio
async def test_brouillon_vide_a_la_cloture_et_fige_ensuite(app_client, db):
    rid = await _fiche(app_client, db)
    await app_client.put(f"/api/receptions/{rid}/brouillon", json={"brouillon": BROUILLON})
    r = await app_client.put(f"/api/receptions/{rid}/cloturer", json={})
    assert r.status_code == 200, r.text

    cur = await db.execute("SELECT brouillon_saisie FROM receptions WHERE id = ?", (rid,))
    assert (await cur.fetchone())[0] is None

    # Une fiche clôturée ne reçoit plus de brouillon
    r = await app_client.put(f"/api/receptions/{rid}/brouillon", json={"brouillon": BROUILLON})
    assert r.status_code == 409


@pytest.mark.anyio
async def test_brouillon_fiche_inconnue(app_client):
    r = await app_client.put("/api/receptions/999999/brouillon", json={"brouillon": BROUILLON})
    assert r.status_code == 404

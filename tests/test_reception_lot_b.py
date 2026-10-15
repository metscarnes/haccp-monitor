"""
Audit réception — lot B (fiabilité / sécurité), partie serveur.

- Filtre `statut` de l'historique passé en paramètre SQL (plus d'injection).
- Réception clôturée : plus d'ajout / modification de ligne ni de changement de T° camion.
- En-tête modifiable avant clôture (fournisseur, propreté + problèmes, date, heure).
- Problèmes de propreté conservés dans le commentaire de la fiche.
- Photo illisible : refus sans fiche orpheline.
- Commandes liées exposées par le détail, et déliables avant clôture.
"""
import pytest


async def _setup(db):
    await db.execute("INSERT OR IGNORE INTO personnel (boutique_id, prenom) VALUES (1, 'LotB')")
    cur = await db.execute("SELECT id FROM personnel WHERE prenom = 'LotB'")
    pid = (await cur.fetchone())[0]
    f1 = (await db.execute("INSERT INTO fournisseurs (boutique_id, nom) VALUES (1, 'Fourn B1')")).lastrowid
    f2 = (await db.execute("INSERT INTO fournisseurs (boutique_id, nom) VALUES (1, 'Fourn B2')")).lastrowid
    await db.commit()
    return pid, f1, f2


async def _reception(client, pid, fid, **extra):
    data = {"personnel_id": str(pid), "heure_reception": "07:30", "temperature_camion": "2",
            "fournisseur_principal_id": str(fid), **extra}
    r = await client.post("/api/receptions", data=data)
    assert r.status_code == 201, r.text
    return r.json()


async def _nb_receptions(db):
    cur = await db.execute("SELECT COUNT(*) FROM receptions")
    return (await cur.fetchone())[0]


@pytest.mark.anyio
async def test_filtre_statut_sans_injection(app_client, db):
    pid, f1, _ = await _setup(db)
    await _reception(app_client, pid, f1)  # reste en_cours
    r = await app_client.get("/api/receptions", params={"statut": "x' OR '1'='1"})
    assert r.status_code == 200
    assert r.json() == []
    r = await app_client.get("/api/receptions", params={"statut": "en_cours"})
    assert len(r.json()) == 1


@pytest.mark.anyio
async def test_reception_cloturee_verrouillee(app_client, db):
    pid, f1, _ = await _setup(db)
    rid = (await _reception(app_client, pid, f1, numero_bon_livraison="BL9"))["id"]
    r = await app_client.post(f"/api/receptions/{rid}/lignes",
                              json={"designation_libre": "Bavette", "poids_kg": 2})
    lid = r.json()["id"]
    assert (await app_client.put(f"/api/receptions/{rid}/cloturer", json={})).status_code == 200

    r = await app_client.post(f"/api/receptions/{rid}/lignes", json={"designation_libre": "X"})
    assert r.status_code == 409
    r = await app_client.put(f"/api/receptions/{rid}/lignes/{lid}", json={"poids_kg": 9})
    assert r.status_code == 409
    r = await app_client.put(f"/api/receptions/{rid}/temperature-camion", json={"temperature_camion": 9})
    assert r.status_code == 409
    r = await app_client.put(f"/api/receptions/{rid}/entete", json={"heure_reception": "09:00"})
    assert r.status_code == 409
    # La complétion des produits en attente (lots internes) reste possible
    r = await app_client.post(f"/api/receptions/{rid}/lots-internes")
    assert r.status_code == 200


@pytest.mark.anyio
async def test_ligne_d_une_autre_reception_refusee(app_client, db):
    pid, f1, _ = await _setup(db)
    r1 = (await _reception(app_client, pid, f1))["id"]
    r2 = (await _reception(app_client, pid, f1))["id"]
    lid = (await app_client.post(f"/api/receptions/{r1}/lignes",
                                 json={"designation_libre": "A"})).json()["id"]
    r = await app_client.put(f"/api/receptions/{r2}/lignes/{lid}", json={"poids_kg": 1})
    assert r.status_code == 404


@pytest.mark.anyio
async def test_proprete_et_entete(app_client, db):
    pid, f1, f2 = await _setup(db)
    rec = await _reception(app_client, pid, f1, proprete_camion="non_satisfaisant",
                           proprete_problemes="Tenue du livreur, Palette cassée / instable")
    assert "Tenue du livreur" in rec["commentaire"]
    assert rec["camion_conforme"] == 0

    r = await app_client.put(f"/api/receptions/{rec['id']}/entete", json={
        "fournisseur_principal_id": f2, "proprete_camion": "satisfaisant",
        "date_reception": "2026-10-14", "heure_reception": "10:15",
    })
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["fournisseur_principal_id"] == f2 and d["fournisseur_nom"] == "Fourn B2"
    assert d["camion_conforme"] == 1 and d["proprete_camion"] == "satisfaisant"
    assert not (d["commentaire"] or "")          # mention de propreté retirée
    assert d["date_reception"] == "2026-10-14" and d["heure_reception"] == "10:15"

    # Fournisseur saisi à la main (hors table fournisseurs)
    r = await app_client.put(f"/api/receptions/{rec['id']}/entete", json={
        "fournisseur_principal_id": None, "fournisseur_nom": "Boucherie Dupont"})
    d = r.json()
    assert d["fournisseur_principal_id"] is None and d["fournisseur_nom"] == "Boucherie Dupont"


@pytest.mark.anyio
async def test_photo_illisible_sans_fiche_orpheline(app_client, db):
    pid, f1, _ = await _setup(db)
    avant = await _nb_receptions(db)
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(pid), "heure_reception": "07:30",
              "fournisseur_principal_id": str(f1)},
        files={"photo_bl": ("bl.jpg", b"pas une image", "image/jpeg")},
    )
    assert r.status_code == 400
    assert await _nb_receptions(db) == avant


@pytest.mark.anyio
async def test_commandes_liees_et_deliage(app_client, db):
    pid, f1, _ = await _setup(db)
    cid = (await db.execute(
        "INSERT INTO commandes (fournisseur_id, numero_commande, statut) VALUES (?, 'CMD-B1', 'confirmee')",
        (f1,))).lastrowid
    await db.commit()
    rid = (await _reception(app_client, pid, f1))["id"]
    r = await app_client.post("/api/achats/commande_receptions_mapping",
                              json={"commande_id": cid, "reception_id": rid})
    assert r.status_code == 201, r.text
    assert (await app_client.get(f"/api/receptions/{rid}")).json()["commande_ids"] == [cid]

    r = await app_client.delete(f"/api/receptions/{rid}/commandes/{cid}")
    assert r.status_code == 200
    assert (await app_client.get(f"/api/receptions/{rid}")).json()["commande_ids"] == []

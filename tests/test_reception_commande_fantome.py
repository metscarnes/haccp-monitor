"""
test_reception_commande_fantome.py — Régression : réception « en_cours » abandonnée.

Bug : quand on lie une commande à une réception puis qu'on quitte la page sans
clôturer, la réception reste 'en_cours'. Ses produits n'apparaissent ni au stock
ni en attente, et la commande liée disparaît partout (ni sélectionnable, ni livrée).

Correctifs couverts :
- GET /api/achats/commandes?non_liee=true ne masque une commande que si elle est
  liée à une réception CLÔTURÉE → une commande liée à une réception 'en_cours'
  reste sélectionnable.
- GET /api/receptions/en-cours expose la réception 'en_cours' la plus récente pour
  le bandeau « reprise/abandon ».
- POST /api/achats/commande_receptions_mapping nettoie le lien vers une réception
  non clôturée quand on relie la commande à une nouvelle réception.
"""

import pytest


async def _seed(db):
    await db.execute("INSERT OR IGNORE INTO personnel (boutique_id, prenom) VALUES (1, 'Éric')")
    cur = await db.execute("SELECT id FROM personnel WHERE boutique_id = 1 AND prenom = 'Éric'")
    personnel_id = (await cur.fetchone())[0]
    await db.execute("INSERT OR IGNORE INTO fournisseurs (id, boutique_id, nom) VALUES (99, 1, 'Bigard')")
    await db.execute(
        """INSERT INTO commandes (id, boutique_id, fournisseur_id, numero_commande,
                                  date_commande, statut)
           VALUES (777, 1, 99, 'CMD-FANTOME-001', '2026-06-15', 'confirmee')"""
    )
    await db.commit()
    return personnel_id


async def _creer_reception_en_cours(app_client, personnel_id):
    """Crée une réception (statut 'en_cours' par défaut) avec une ligne, sans clôture."""
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00",
              "temperature_camion": "1.0"},
    )
    rid = r.json()["id"]
    await app_client.post(
        f"/api/receptions/{rid}/lignes",
        json={"designation_libre": "VB-PALERON", "temperature_reception": 2.0,
              "numero_lot": "LOT-001", "dlc": "2026-12-31", "poids_kg": 10.0},
    )
    return rid


@pytest.mark.anyio
async def test_commande_liee_reception_en_cours_reste_selectionnable(app_client, db):
    personnel_id = await _seed(db)
    rid = await _creer_reception_en_cours(app_client, personnel_id)

    # Lier la commande à la réception 'en_cours'
    r = await app_client.post(
        "/api/achats/commande_receptions_mapping",
        json={"commande_id": 777, "reception_id": rid},
    )
    assert r.status_code == 201, r.text

    # La commande reste sélectionnable tant que la réception n'est pas clôturée
    r = await app_client.get("/api/achats/commandes?statut=confirmee&non_liee=true")
    ids = [c["id"] for c in r.json()]
    assert 777 in ids, "commande liée à une réception 'en_cours' doit rester sélectionnable"


@pytest.mark.anyio
async def test_commande_masquee_apres_cloture(app_client, db):
    personnel_id = await _seed(db)
    rid = await _creer_reception_en_cours(app_client, personnel_id)
    await app_client.post(
        "/api/achats/commande_receptions_mapping",
        json={"commande_id": 777, "reception_id": rid},
    )

    # Clôturer → la commande devient 'livree' et disparaît des sélectionnables
    r = await app_client.put(f"/api/receptions/{rid}/cloturer", json={})
    assert r.status_code == 200, r.text

    cur = await db.execute("SELECT statut FROM commandes WHERE id = 777")
    assert (await cur.fetchone())[0] == "livree"

    r = await app_client.get("/api/achats/commandes?statut=livree&non_liee=true")
    ids = [c["id"] for c in r.json()]
    assert 777 not in ids, "commande liée à une réception clôturée doit être masquée"


@pytest.mark.anyio
async def test_endpoint_reception_en_cours(app_client, db):
    personnel_id = await _seed(db)

    # Aucune réception en cours → null
    r = await app_client.get("/api/receptions/en-cours")
    assert r.status_code == 200
    assert r.json() is None

    rid = await _creer_reception_en_cours(app_client, personnel_id)
    r = await app_client.get("/api/receptions/en-cours")
    data = r.json()
    assert data is not None and data["id"] == rid
    assert data["nb_lignes"] == 1

    # Après clôture → plus rien en cours
    await app_client.put(f"/api/receptions/{rid}/cloturer", json={})
    r = await app_client.get("/api/receptions/en-cours")
    assert r.json() is None


@pytest.mark.anyio
async def test_bl_apercu_liste_toutes_les_pages(app_client, db):
    personnel_id = await _seed(db)

    # Réception avec une photo BL principale (page 0)
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00",
              "temperature_camion": "1.0"},
    )
    rid = r.json()["id"]
    await db.execute(
        "UPDATE receptions SET photo_bl_filename = 'BL-test-p0.jpg' WHERE id = ?", (rid,)
    )
    # Deux pages supplémentaires (page_num 1 et 2)
    await db.execute(
        "INSERT INTO reception_bl_pages (reception_id, bl_supplementaire_id, page_num, photo_filename) "
        "VALUES (?, NULL, 1, 'BL-test-p1.jpg')", (rid,)
    )
    await db.execute(
        "INSERT INTO reception_bl_pages (reception_id, bl_supplementaire_id, page_num, photo_filename) "
        "VALUES (?, NULL, 2, 'BL-test-p2.jpg')", (rid,)
    )
    await db.commit()

    r = await app_client.get(f"/api/receptions/{rid}/bl-apercu")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["nb_pages"] == 3
    nums = [p["page_num"] for p in data["pages"]]
    assert nums == [0, 1, 2]
    # La page 0 pointe vers la route photo-bl, les autres vers bl-pages
    assert data["pages"][0]["url"].endswith("/photo-bl")
    assert "/bl-pages/" in data["pages"][1]["url"]


def _jpeg_bytes():
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (60, 40), (200, 100, 50)).save(buf, format="JPEG")
    return buf.getvalue()


def _pdf_bytes(nb_pages=2):
    import fitz
    doc = fitz.open()
    for _ in range(nb_pages):
        doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


@pytest.mark.anyio
async def test_ajout_bl_premiere_page_devient_page0(app_client, db):
    personnel_id = await _seed(db)
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00",
              "temperature_camion": "1.0"},
    )
    rid = r.json()["id"]

    r = await app_client.post(
        f"/api/receptions/{rid}/bl-pages",
        files={"fichier": ("bl.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    assert r.json()["pages_ajoutees"] == 1

    # photo_bl_filename (page 0) maintenant renseignée
    cur = await db.execute("SELECT photo_bl_filename FROM receptions WHERE id = ?", (rid,))
    assert (await cur.fetchone())[0] is not None

    r = await app_client.get(f"/api/receptions/{rid}/bl-apercu")
    assert r.json()["nb_pages"] == 1


@pytest.mark.anyio
async def test_ajout_bl_pages_suivantes(app_client, db):
    personnel_id = await _seed(db)
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00",
              "temperature_camion": "1.0"},
    )
    rid = r.json()["id"]
    # Page 0 déjà présente
    await db.execute("UPDATE receptions SET photo_bl_filename = 'BL-existant.jpg' WHERE id = ?", (rid,))
    await db.commit()

    r = await app_client.post(
        f"/api/receptions/{rid}/bl-pages",
        files={"fichier": ("page2.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert r.status_code == 201, r.text

    r = await app_client.get(f"/api/receptions/{rid}/bl-apercu")
    data = r.json()
    assert data["nb_pages"] == 2
    assert [p["page_num"] for p in data["pages"]] == [0, 1]


@pytest.mark.anyio
async def test_ajout_bl_pdf_multipage(app_client, db):
    personnel_id = await _seed(db)
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00",
              "temperature_camion": "1.0"},
    )
    rid = r.json()["id"]

    r = await app_client.post(
        f"/api/receptions/{rid}/bl-pages",
        files={"fichier": ("bl.pdf", _pdf_bytes(3), "application/pdf")},
    )
    assert r.status_code == 201, r.text
    assert r.json()["pages_ajoutees"] == 3

    r = await app_client.get(f"/api/receptions/{rid}/bl-apercu")
    data = r.json()
    assert data["nb_pages"] == 3
    assert [p["page_num"] for p in data["pages"]] == [0, 1, 2]


@pytest.mark.anyio
async def test_ajout_bl_sans_fichier_400(app_client, db):
    personnel_id = await _seed(db)
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00",
              "temperature_camion": "1.0"},
    )
    rid = r.json()["id"]
    r = await app_client.post(f"/api/receptions/{rid}/bl-pages", files={})
    assert r.status_code in (400, 422)


@pytest.mark.anyio
async def test_bl_apercu_sans_photo(app_client, db):
    personnel_id = await _seed(db)
    r = await app_client.post(
        "/api/receptions",
        data={"personnel_id": str(personnel_id), "heure_reception": "08:00",
              "temperature_camion": "1.0"},
    )
    rid = r.json()["id"]
    r = await app_client.get(f"/api/receptions/{rid}/bl-apercu")
    assert r.status_code == 200
    assert r.json()["nb_pages"] == 0


@pytest.mark.anyio
async def test_relier_nettoie_ancien_lien_non_cloture(app_client, db):
    personnel_id = await _seed(db)
    rid1 = await _creer_reception_en_cours(app_client, personnel_id)
    await app_client.post(
        "/api/achats/commande_receptions_mapping",
        json={"commande_id": 777, "reception_id": rid1},
    )

    # Nouvelle réception, on relie la même commande : l'ancien lien (réception
    # non clôturée) doit être supprimé pour ne pas multiplier les fantômes.
    rid2 = await _creer_reception_en_cours(app_client, personnel_id)
    await app_client.post(
        "/api/achats/commande_receptions_mapping",
        json={"commande_id": 777, "reception_id": rid2},
    )

    cur = await db.execute(
        "SELECT reception_id FROM commande_receptions_mapping WHERE commande_id = 777"
    )
    rows = [r[0] for r in await cur.fetchall()]
    assert rows == [rid2], f"un seul lien attendu vers la nouvelle réception, obtenu {rows}"

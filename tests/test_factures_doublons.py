"""
test_factures_doublons.py — Détection et annulation tracée des factures doublon.

Contexte terrain : une même livraison saisie deux fois en réception (même
fournisseur, même n° de BL papier) génère potentiellement deux factures pour
le même arrivage → double comptage dans le CMV/marge. Règles testées :

- GET /factures/doublons-potentiels repère les réceptions du même fournisseur
  partageant un n° de BL renseigné (≥ 2 réceptions), sans rien modifier.
- POST /factures/{id}/annuler-doublon exige un motif, passe le statut à
  'annulee' (jamais de DELETE réel), trace la facture conservée si fournie.
- Une facture annulée disparaît de GET /factures par défaut mais reste
  consultable via ?statut=annulee.
- Une facture validée (verrouillée) refuse l'annulation-doublon (409), comme
  toute autre modification.
"""
import pytest


async def _fournisseur(client, nom="Doublon SAS"):
    r = await client.post("/api/achats/fournisseurs", json={"nom": nom})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _reception(db, fournisseur_id, bl, date="2026-06-13"):
    await db.execute(
        "INSERT OR IGNORE INTO personnel (id, boutique_id, prenom, actif) VALUES (1, 1, 'Test', 1)"
    )
    cur = await db.execute(
        """INSERT INTO receptions (personnel_id, heure_reception, fournisseur_principal_id,
                                    statut, numero_bon_livraison, date_reception)
           VALUES (1, '08:00', ?, 'cloturee', ?, ?)""",
        (fournisseur_id, bl, date),
    )
    await db.commit()
    return cur.lastrowid


async def _facture(client, fournisseur_id, reception_id=None):
    payload = {"fournisseur_id": fournisseur_id, "lignes": []}
    if reception_id:
        payload["reception_id"] = reception_id
    r = await client.post("/api/achats/factures", json=payload)
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_detecte_doublon_meme_bl(app_client, db):
    fid = await _fournisseur(app_client)
    r1 = await _reception(db, fid, "BL-0001", "2026-06-13")
    r2 = await _reception(db, fid, "BL-0001", "2026-06-25")
    await _reception(db, fid, "BL-0002", "2026-06-14")  # BL différent, pas un doublon

    r = await app_client.get(f"/api/achats/factures/doublons-potentiels?fournisseur_id={fid}")
    assert r.status_code == 200, r.text
    groupes = r.json()
    assert len(groupes) == 1
    g = groupes[0]
    assert g["numero_bon_livraison"] == "BL-0001"
    ids = {x["reception_id"] for x in g["receptions"]}
    assert ids == {r1, r2}


@pytest.mark.asyncio
async def test_pas_de_doublon_si_bl_unique(app_client, db):
    fid = await _fournisseur(app_client)
    await _reception(db, fid, "BL-UNIQUE", "2026-06-13")

    r = await app_client.get(f"/api/achats/factures/doublons-potentiels?fournisseur_id={fid}")
    assert r.status_code == 200, r.text
    assert r.json() == []


@pytest.mark.asyncio
async def test_annuler_doublon_exige_motif(app_client, db):
    fid = await _fournisseur(app_client)
    fac_id = await _facture(app_client, fid)

    r = await app_client.post(f"/api/achats/factures/{fac_id}/annuler-doublon", json={"motif": ""})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_annuler_doublon_change_statut_et_trace_motif(app_client, db):
    fid = await _fournisseur(app_client)
    fac_conservee = await _facture(app_client, fid)
    fac_doublon = await _facture(app_client, fid)

    r = await app_client.post(
        f"/api/achats/factures/{fac_doublon}/annuler-doublon",
        json={"motif": "même BL 010760322 que la facture conservée",
              "facture_conservee_id": fac_conservee},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["statut"] == "annulee"
    assert "010760322" in data["commentaire"]
    assert f"#{fac_conservee}" in data["commentaire"]


@pytest.mark.asyncio
async def test_facture_annulee_disparait_de_la_liste_par_defaut(app_client, db):
    fid = await _fournisseur(app_client)
    fac_id = await _facture(app_client, fid)
    await app_client.post(f"/api/achats/factures/{fac_id}/annuler-doublon",
                          json={"motif": "doublon de saisie"})

    r = await app_client.get(f"/api/achats/factures?fournisseur_id={fid}")
    assert r.status_code == 200
    assert fac_id not in [f["id"] for f in r.json()]

    # Toujours consultable explicitement (rien n'est perdu)
    r2 = await app_client.get(f"/api/achats/factures?fournisseur_id={fid}&statut=annulee")
    assert fac_id in [f["id"] for f in r2.json()]


@pytest.mark.asyncio
async def test_annulation_doublon_respecte_le_verrou(app_client, db):
    fid = await _fournisseur(app_client)
    fac_id = await _facture(app_client, fid)
    await app_client.put(f"/api/achats/factures/{fac_id}",
                         json={"numero_facture": "FA-V", "statut": "validee"})

    r = await app_client.post(f"/api/achats/factures/{fac_id}/annuler-doublon",
                              json={"motif": "tentative sur facture verrouillée"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_annuler_doublon_404_si_facture_conservee_inexistante(app_client, db):
    fid = await _fournisseur(app_client)
    fac_id = await _facture(app_client, fid)

    r = await app_client.post(
        f"/api/achats/factures/{fac_id}/annuler-doublon",
        json={"motif": "test", "facture_conservee_id": 999999},
    )
    assert r.status_code == 404

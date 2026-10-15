"""
Audit réception — lot A (intégrité du registre HACCP).

- Température contrôlée aussi pour les articles du catalogue achats.
- Modification d'une ligne = mise à jour PARTIELLE (rien n'est effacé).
- Contrôle à cœur re-vérifié par le serveur ; ne corrige pas une NC visuelle.
- Lots internes jamais en double dans une même réception.
"""
import pytest


async def _setup(db):
    await db.execute("INSERT OR IGNORE INTO personnel (boutique_id, prenom) VALUES (1, 'LotA')")
    cur = await db.execute("SELECT id FROM personnel WHERE prenom = 'LotA'")
    pid = (await cur.fetchone())[0]
    cur = await db.execute("INSERT INTO fournisseurs (boutique_id, nom) VALUES (1, 'Fourn LotA')")
    fid = cur.lastrowid

    async def article(code, designation, famille, dlc_type="dlc"):
        c = await db.execute(
            "INSERT INTO catalogue_fournisseur (fournisseur_id, code_article, designation, famille, dlc_type) "
            "VALUES (?, ?, ?, ?, ?)", (fid, code, designation, famille, dlc_type))
        return c.lastrowid

    ids = {
        "viande":   await article("V1", "Bavette", "Viande"),
        "epice":    await article("E1", "Poivre", "Aide culinaire"),
        "carcasse": await article("C1", "Carcasse agneau", "Viande", "date_abattage"),
    }
    await db.commit()
    return pid, fid, ids


async def _reception(client, pid, fid, temp="9", bl="BL42"):
    r = await client.post("/api/receptions", data={
        "personnel_id": str(pid), "heure_reception": "07:30", "temperature_camion": temp,
        "fournisseur_principal_id": str(fid), "numero_bon_livraison": bl,
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _ligne(client, rid, cid, **extra):
    body = {"designation_libre": "Article", "catalogue_fournisseur_id": cid, **extra}
    r = await client.post(f"/api/receptions/{rid}/lignes", json=body)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.anyio
async def test_temperature_controlee_pour_articles_catalogue(app_client, db):
    pid, fid, ids = await _setup(db)
    rid = await _reception(app_client, pid, fid, temp="6")

    viande = await _ligne(app_client, rid, ids["viande"], temperature_reception=6)
    assert viande["temperature_cible"] == "0°C à +4°C"
    assert viande["temperature_conforme"] == 0 and viande["conforme"] == 0

    carcasse = await _ligne(app_client, rid, ids["carcasse"], temperature_reception=6)
    assert carcasse["temperature_cible"] == "0°C à +7°C"
    assert carcasse["temperature_conforme"] == 1 and carcasse["conforme"] == 1

    epice = await _ligne(app_client, rid, ids["epice"], temperature_reception=6)
    assert epice["temperature_cible"] is None
    assert epice["temperature_conforme"] is None and epice["conforme"] == 1

    # Changement de la température camion : recalcul aussi pour le catalogue
    r = await app_client.put(f"/api/receptions/{rid}/temperature-camion",
                             json={"temperature_camion": 2})
    assert r.status_code == 200, r.text
    par_id = {l["id"]: l for l in r.json()["lignes"]}
    assert par_id[viande["id"]]["conforme"] == 1


@pytest.mark.anyio
async def test_modifier_ligne_n_efface_rien(app_client, db):
    pid, fid, ids = await _setup(db)
    rid = await _reception(app_client, pid, fid, temp="2")
    l = await _ligne(app_client, rid, ids["viande"], fournisseur_id=fid, numero_lot="L1",
                     dlc="2099-01-01", origine="Irlande", poids_kg=12.5, nb_colis=3,
                     temperature_reception=2, odeur_conforme=0, odeur_observation="putride")

    # Correction du seul n° de lot
    r = await app_client.put(f"/api/receptions/{rid}/lignes/{l['id']}",
                             json={"numero_lot": "L1-corrige"})
    assert r.status_code == 200, r.text
    u = r.json()
    assert u["numero_lot"] == "L1-corrige"
    assert u["poids_kg"] == 12.5 and u["nb_colis"] == 3
    assert u["fournisseur_id"] == fid and u["origine"] == "Irlande"
    assert u["catalogue_fournisseur_id"] == ids["viande"]
    assert u["odeur_conforme"] == 0 and u["odeur_observation"] == "putride"
    assert u["conforme"] == 0

    # Remise en conforme explicite + effacement de l'observation
    r = await app_client.put(f"/api/receptions/{rid}/lignes/{l['id']}",
                             json={"odeur_conforme": 1, "odeur_observation": None})
    u = r.json()
    assert u["odeur_conforme"] == 1 and u["odeur_observation"] is None
    assert u["conforme"] == 1 and u["poids_kg"] == 12.5


@pytest.mark.anyio
async def test_controle_a_coeur_verifie_par_le_serveur(app_client, db):
    pid, fid, ids = await _setup(db)
    rid = await _reception(app_client, pid, fid, temp="7")
    temp_seule  = await _ligne(app_client, rid, ids["viande"], temperature_reception=7)
    temp_odeur  = await _ligne(app_client, rid, ids["viande"], temperature_reception=7,
                               odeur_conforme=0)
    coeur_chaud = await _ligne(app_client, rid, ids["viande"], temperature_reception=7)
    for l in (temp_seule, temp_odeur, coeur_chaud):
        assert l["conforme"] == 0

    r = await app_client.put(f"/api/receptions/{rid}/cloturer", json={
        "coeur_conformes": [temp_seule["id"], temp_odeur["id"], coeur_chaud["id"]],
        "coeur_temperatures": {
            str(temp_seule["id"]): 3.0, str(temp_odeur["id"]): 3.0, str(coeur_chaud["id"]): 6.0,
        },
    })
    assert r.status_code == 200, r.text
    par_id = {l["id"]: l for l in r.json()["lignes"]}
    assert par_id[temp_seule["id"]]["conforme"] == 1    # T° seule en cause, cœur OK
    assert par_id[temp_odeur["id"]]["conforme"] == 0    # l'odeur reste NC
    assert par_id[coeur_chaud["id"]]["conforme"] == 0   # cœur à 6 °C : NC confirmée
    assert r.json()["conformite_globale"] == "non_conforme"


@pytest.mark.anyio
async def test_lots_internes_jamais_en_double(app_client, db):
    pid, fid, ids = await _setup(db)
    rid = await _reception(app_client, pid, fid, temp="2")

    r = await app_client.get(f"/api/receptions/{rid}/lot-interne", params={"code_article": "V1"})
    lot = r.json()["lot_interne"]
    a = await _ligne(app_client, rid, ids["viande"], numero_lot=lot, lot_interne=1, dlc="2099-01-01")
    b = await _ligne(app_client, rid, ids["viande"], numero_lot=lot, lot_interne=1, dlc="2099-01-02")
    assert a["numero_lot"] == lot
    assert b["numero_lot"] == f"{lot}-B"

    # « Lot interne sur toute la commande » : deux lignes du même article sans lot
    c = await _ligne(app_client, rid, ids["carcasse"], date_abattage="2026-10-01")
    d = await _ligne(app_client, rid, ids["carcasse"], date_abattage="2026-10-02")
    r = await app_client.post(f"/api/receptions/{rid}/lots-internes")
    assert r.status_code == 200, r.text
    r = await app_client.get(f"/api/receptions/{rid}")
    lots = [l["numero_lot"] for l in r.json()["lignes"]]
    assert len(lots) == len(set(lots)), lots

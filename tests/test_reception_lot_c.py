"""
Audit réception — lot C, partie serveur.

- Suppression d'une commande depuis l'écran réception : mot de passe admin exigé.
- Unité du prix (kg / pièce / colis) enregistrée sur la ligne de réception et
  reprise par la facture brouillon : un prix à la pièce n'est plus multiplié par
  le poids ; un lot supplémentaire à 0 colis ne recompte pas la quantité.
"""
import os

import pytest


async def _setup(db):
    await db.execute("INSERT OR IGNORE INTO personnel (boutique_id, prenom) VALUES (1, 'LotC')")
    cur = await db.execute("SELECT id FROM personnel WHERE prenom = 'LotC'")
    pid = (await cur.fetchone())[0]
    fid = (await db.execute(
        "INSERT INTO fournisseurs (boutique_id, nom) VALUES (1, 'Fourn C')")).lastrowid
    cid = (await db.execute(
        "INSERT INTO catalogue_fournisseur (fournisseur_id, code_article, designation, famille, format_prix) "
        "VALUES (?, 'P1', 'Pâté en croûte', 'Charcuterie', 'kg')", (fid,))).lastrowid
    await db.commit()
    return pid, fid, cid


@pytest.mark.anyio
async def test_suppression_commande_protegee_par_mot_de_passe(app_client, db):
    _, fid, _ = await _setup(db)
    cmd = (await db.execute(
        "INSERT INTO commandes (fournisseur_id, numero_commande, statut) VALUES (?, 'CMD-C1', 'confirmee')",
        (fid,))).lastrowid
    await db.commit()

    r = await app_client.post(f"/api/achats/commandes/{cmd}/supprimer-protege",
                              json={"password": "faux"})
    assert r.status_code == 401
    cur = await db.execute("SELECT COUNT(*) FROM commandes WHERE id = ?", (cmd,))
    assert (await cur.fetchone())[0] == 1

    r = await app_client.post(f"/api/achats/commandes/{cmd}/supprimer-protege",
                              json={"password": os.environ["ADMIN_PASSWORD"]})
    assert r.status_code == 204, r.text
    cur = await db.execute("SELECT COUNT(*) FROM commandes WHERE id = ?", (cmd,))
    assert (await cur.fetchone())[0] == 0


@pytest.mark.anyio
async def test_toutes_les_fiches_non_terminees_listees(app_client, db):
    pid, fid, _ = await _setup(db)
    ids = []
    for _ in range(3):
        r = await app_client.post("/api/receptions", data={
            "personnel_id": str(pid), "heure_reception": "07:30",
            "fournisseur_principal_id": str(fid)})
        ids.append(r.json()["id"])
    await app_client.put(f"/api/receptions/{ids[1]}/cloturer", json={})

    r = await app_client.get("/api/receptions/non-terminees")
    assert r.status_code == 200, r.text
    fiches = r.json()
    trouves = [f["id"] for f in fiches if f["id"] in ids]
    assert trouves == [ids[2], ids[0]]          # les 2 non clôturées, la plus récente d'abord
    assert all(f["fournisseur_nom"] == "Fourn C" for f in fiches if f["id"] in ids)


@pytest.mark.anyio
async def test_prix_a_la_piece_jusqu_a_la_facture(app_client, db):
    pid, fid, cid = await _setup(db)
    r = await app_client.post("/api/receptions", data={
        "personnel_id": str(pid), "heure_reception": "07:30", "temperature_camion": "2",
        "fournisseur_principal_id": str(fid)})
    rid = r.json()["id"]

    # Article payé 12 € la pièce, 3 pièces (3,2 kg au total), livré en 2 lots
    base = {"designation_libre": "Pâté en croûte", "catalogue_fournisseur_id": cid,
            "fournisseur_id": fid, "dlc": "2099-01-01", "prix_unitaire_ht": 12.0,
            "unite_prix": "piece"}
    l1 = (await app_client.post(f"/api/receptions/{rid}/lignes", json={
        **base, "numero_lot": "A", "poids_kg": 2.0, "nb_colis": 3, "montant_ht": 36.0})).json()
    l2 = (await app_client.post(f"/api/receptions/{rid}/lignes", json={
        **base, "numero_lot": "B", "poids_kg": 1.2, "nb_colis": 0, "montant_ht": 0})).json()
    assert l1["unite_prix"] == "piece" and l1["montant_ht"] == 36.0

    r = await app_client.put(f"/api/receptions/{rid}/cloturer", json={})
    assert r.status_code == 200, r.text
    fac = r.json()["facture_auto"]
    assert fac["creee"], fac

    cur = await db.execute(
        "SELECT reception_ligne_id, unite_prix, quantite_facturee, montant_facture_ht "
        "FROM facture_lignes WHERE facture_id = ? ORDER BY reception_ligne_id", (fac["facture_id"],))
    lignes = {r["reception_ligne_id"]: dict(r) for r in await cur.fetchall()}
    assert lignes[l1["id"]]["unite_prix"] == "piece"
    assert lignes[l1["id"]]["quantite_facturee"] == 3
    assert lignes[l1["id"]]["montant_facture_ht"] == pytest.approx(36.0)
    assert lignes[l2["id"]]["montant_facture_ht"] == pytest.approx(0.0)

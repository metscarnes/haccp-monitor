"""
test_attente_multi.py — Dédoublement d'une ligne en attente en plusieurs lots.

Un produit reçu en plusieurs lots (lot/DLC/poids propres) doit pouvoir se scinder :
la ligne d'origine prend le 1er lot, chaque lot suivant crée une ligne clonée.
"""

import pytest

from src.database import (
    get_db,
    add_reception_ligne,
    get_lignes_en_attente,
    completer_ligne_attente_multi,
)


async def _seed_reception(db) -> int:
    """Crée un personnel, un fournisseur et une réception ; renvoie reception_id."""
    await db.execute(
        "INSERT INTO personnel (boutique_id, prenom, nom, actif) VALUES (1, 'Test', 'Op', 1)"
    )
    await db.execute(
        "INSERT INTO fournisseurs (boutique_id, nom, actif) VALUES (1, 'Frnss', 1)"
    )
    cur = await db.execute("SELECT id FROM personnel LIMIT 1")
    pid = (await cur.fetchone())[0]
    cur = await db.execute(
        "INSERT INTO receptions (personnel_id, date_reception, heure_reception, "
        "temperature_camion, numero_bon_livraison, statut) "
        "VALUES (?, '2026-06-19', '07:30', 1.0, 'BL-1', 'en_cours')",
        (pid,),
    )
    await db.commit()
    return cur.lastrowid


@pytest.mark.asyncio
async def test_split_deux_lots(db):
    reception_id = await _seed_reception(db)

    # Ligne reçue SANS lot/DLC → en_attente (dlc_type='dlc')
    ligne_id = await add_reception_ligne(db, reception_id, {
        "designation_libre": "Côte de bœuf",
        "fournisseur_nom": "Frnss",
        "dlc_type": "dlc",
        "poids_kg": 10.0,
        "temperature_reception": 1.0,
    })

    lignes = await get_lignes_en_attente(db)
    assert any(l["ligne_id"] == ligne_id for l in lignes)

    res = await completer_ligne_attente_multi(db, ligne_id, [
        {"numero_lot": "LOT-A", "dlc": "2026-12-01", "poids_kg": 6.0},
        {"numero_lot": "LOT-B", "dlc": "2026-12-05", "poids_kg": 4.0},
    ])

    assert res is not None
    assert res["total"] == 2
    assert res["complets"] == 2
    assert res["en_attente"] == 0
    assert len(res["lignes_ids"]) == 2
    assert res["lignes_ids"][0] == ligne_id  # 1re section = ligne d'origine

    # Plus aucune ligne en attente
    assert await get_lignes_en_attente(db) == []

    # Deux lignes complètes avec lots/DLC/poids distincts
    cur = await db.execute(
        "SELECT numero_lot, dlc, poids_kg, statut FROM reception_lignes "
        "WHERE reception_id = ? ORDER BY id", (reception_id,)
    )
    rows = [dict(r) for r in await cur.fetchall()]
    assert len(rows) == 2
    lots = {r["numero_lot"]: r for r in rows}
    assert lots["LOT-A"]["dlc"] == "2026-12-01"
    assert lots["LOT-A"]["poids_kg"] == 6.0
    assert lots["LOT-A"]["statut"] == "complet"
    assert lots["LOT-B"]["dlc"] == "2026-12-05"
    assert lots["LOT-B"]["poids_kg"] == 4.0
    assert lots["LOT-B"]["statut"] == "complet"


@pytest.mark.asyncio
async def test_split_lot_incomplet_reste_en_attente(db):
    reception_id = await _seed_reception(db)
    ligne_id = await add_reception_ligne(db, reception_id, {
        "designation_libre": "Filet",
        "dlc_type": "dlc",
        "poids_kg": 5.0,
    })

    # 2e lot sans date → doit rester en_attente, mais la ligne créée existe.
    res = await completer_ligne_attente_multi(db, ligne_id, [
        {"numero_lot": "LOT-A", "dlc": "2026-12-01", "poids_kg": 3.0},
        {"numero_lot": "LOT-B", "poids_kg": 2.0},  # pas de date
    ])
    assert res["complets"] == 1
    assert res["en_attente"] == 1

    restantes = await get_lignes_en_attente(db)
    assert len(restantes) == 1
    assert restantes[0]["numero_lot"] == "LOT-B"

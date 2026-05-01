"""
test_stock.py — Vue stock unifiée FIFO multi-sources.
"""

import pytest
from datetime import date, timedelta

from src.database import get_stock_unifie

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers de fabrication de données
# ---------------------------------------------------------------------------

async def _insert_produit(db, nom, categorie="plat_cuisine", type_produit="brut"):
    cur = await db.execute(
        "INSERT INTO produits (boutique_id, nom, categorie, type_produit) VALUES (1, ?, ?, ?)",
        (nom, categorie, type_produit),
    )
    return cur.lastrowid


async def _insert_personnel(db, prenom="TestOp"):
    """Idempotent : récupère l'id si le prénom existe déjà (seed Éric/Ulysse)."""
    cur = await db.execute(
        "SELECT id FROM personnel WHERE boutique_id = 1 AND prenom = ?", (prenom,)
    )
    row = await cur.fetchone()
    if row:
        return row[0]
    cur = await db.execute(
        "INSERT INTO personnel (boutique_id, prenom) VALUES (1, ?)", (prenom,)
    )
    return cur.lastrowid


async def _insert_reception_ligne(db, produit_id, dlc, lot="LOT1"):
    pers = await _insert_personnel(db, "OpRcp")
    cur = await db.execute(
        "INSERT INTO receptions (personnel_id, heure_reception) VALUES (?, '10:00')",
        (pers,),
    )
    rec_id = cur.lastrowid
    cur = await db.execute(
        "INSERT INTO reception_lignes (reception_id, produit_id, numero_lot, dlc, poids_kg) "
        "VALUES (?, ?, ?, ?, ?)",
        (rec_id, produit_id, lot, dlc, 5.0),
    )
    return cur.lastrowid


async def _insert_cuisson(db, produit_id, personnel_id, date_cuisson, dlc_finale, refroidie=False):
    cur = await db.execute(
        """INSERT INTO cuissons
        (boutique_id, type_cuisson, date_cuisson, personnel_id, produit_id,
         heure_debut, heure_fin, temperature_sortie, conforme, dlc_finale)
        VALUES (1, 'rotissoire', ?, ?, ?, '10:00', '11:00', 80.0, 1, ?)""",
        (date_cuisson, personnel_id, produit_id, dlc_finale),
    )
    cuisson_id = cur.lastrowid
    if refroidie:
        await db.execute(
            """INSERT INTO refroidissements
            (boutique_id, date_refroidissement, personnel_id, produit_id, cuisson_id,
             heure_debut, heure_fin, duree_minutes, temperature_finale,
             conforme, jeter, dlc_finale)
            VALUES (1, ?, ?, ?, ?, '12:00', '13:30', 90, 8.0, 1, 0, ?)""",
            (date_cuisson, personnel_id, produit_id, cuisson_id, dlc_finale),
        )
    return cuisson_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_stock_unifie_vide_quand_pas_de_donnees(db):
    items = await get_stock_unifie(db, 1)
    assert items == []


async def test_stock_inclut_les_4_sources(db):
    today = date.today()
    j_plus_5 = (today + timedelta(days=5)).isoformat()
    pid_brut = await _insert_produit(db, "Bœuf", type_produit="brut")
    pid_fini = await _insert_produit(db, "Poulet", type_produit="brut")
    pers = await _insert_personnel(db, "Éric")

    # 📦 Réception
    await _insert_reception_ligne(db, pid_brut, j_plus_5, "BL-001")
    # 🔥 Cuisson seule
    await _insert_cuisson(db, pid_fini, pers, today.isoformat(), j_plus_5)
    # ❄️ Cuisson + refroidissement
    await _insert_cuisson(db, pid_fini, pers, today.isoformat(), j_plus_5, refroidie=True)

    items = await get_stock_unifie(db, 1)
    sources = {it["source_type"] for it in items}
    # cuisson refroidie est masquée → on n'a que reception_ligne, cuisson (la non-refroidie), refroidissement
    assert "reception_ligne" in sources
    assert "cuisson" in sources
    assert "refroidissement" in sources
    # Chaque item a son icône + jours_restants
    for it in items:
        assert it["source_icon"] in ("📦", "🔪", "🔥", "❄️")
        assert it["jours_restants"] == 5


async def test_stock_filtre_type_brut(db):
    today = date.today()
    j_plus_3 = (today + timedelta(days=3)).isoformat()
    pid = await _insert_produit(db, "Bœuf")
    pers = await _insert_personnel(db, "Éric")
    await _insert_reception_ligne(db, pid, j_plus_3, "L-1")
    await _insert_cuisson(db, pid, pers, today.isoformat(), j_plus_3)

    items = await get_stock_unifie(db, 1, type_produit="brut")
    assert len(items) == 1
    assert items[0]["source_type"] == "reception_ligne"


async def test_stock_filtre_type_fini(db):
    today = date.today()
    j_plus_3 = (today + timedelta(days=3)).isoformat()
    pid = await _insert_produit(db, "Bœuf")
    pers = await _insert_personnel(db, "Éric")
    await _insert_reception_ligne(db, pid, j_plus_3, "L-1")
    await _insert_cuisson(db, pid, pers, today.isoformat(), j_plus_3)

    items = await get_stock_unifie(db, 1, type_produit="fini")
    assert len(items) == 1
    assert items[0]["source_type"] == "cuisson"


async def test_stock_exclut_periimes_par_defaut(db):
    today = date.today()
    hier = (today - timedelta(days=1)).isoformat()
    j_plus_3 = (today + timedelta(days=3)).isoformat()
    pid = await _insert_produit(db, "Bœuf")
    await _insert_reception_ligne(db, pid, hier, "PERIME")
    await _insert_reception_ligne(db, pid, j_plus_3, "FRAIS")

    items = await get_stock_unifie(db, 1)
    lots = {it["numero_lot"] for it in items}
    assert "FRAIS" in lots
    assert "PERIME" not in lots


async def test_stock_inclut_periimes_si_demande(db):
    today = date.today()
    hier = (today - timedelta(days=1)).isoformat()
    pid = await _insert_produit(db, "Bœuf")
    await _insert_reception_ligne(db, pid, hier, "PERIME")

    items = await get_stock_unifie(db, 1, inclure_expires=True)
    assert len(items) == 1
    assert items[0]["jours_restants"] == -1


async def test_stock_exclut_devenir_traite(db):
    today = date.today()
    j_plus_3 = (today + timedelta(days=3)).isoformat()
    pid = await _insert_produit(db, "Bœuf")
    pers = await _insert_personnel(db, "Éric")
    rl_id = await _insert_reception_ligne(db, pid, j_plus_3, "L-1")
    # Marqué jeté via dlc_devenir
    await db.execute(
        "INSERT INTO dlc_devenir (source_type, source_id, statut, personnel_id) VALUES (?, ?, ?, ?)",
        ("reception_ligne", rl_id, "jete", pers),
    )

    items = await get_stock_unifie(db, 1)
    assert len(items) == 0


async def test_stock_filtre_dlc_max(db):
    today = date.today()
    j_plus_2 = (today + timedelta(days=2)).isoformat()
    j_plus_10 = (today + timedelta(days=10)).isoformat()
    pid = await _insert_produit(db, "Bœuf")
    await _insert_reception_ligne(db, pid, j_plus_2, "PROCHE")
    await _insert_reception_ligne(db, pid, j_plus_10, "LOIN")

    items = await get_stock_unifie(db, 1, dlc_max=(today + timedelta(days=5)).isoformat())
    lots = {it["numero_lot"] for it in items}
    assert "PROCHE" in lots
    assert "LOIN" not in lots


async def test_stock_tri_fifo(db):
    today = date.today()
    pid = await _insert_produit(db, "Bœuf")
    # Insertion dans le désordre
    await _insert_reception_ligne(db, pid, (today + timedelta(days=10)).isoformat(), "DLC10")
    await _insert_reception_ligne(db, pid, (today + timedelta(days=2)).isoformat(),  "DLC2")
    await _insert_reception_ligne(db, pid, (today + timedelta(days=5)).isoformat(),  "DLC5")

    items = await get_stock_unifie(db, 1)
    assert [it["numero_lot"] for it in items] == ["DLC2", "DLC5", "DLC10"]


async def test_stock_refroidissement_jete_exclu(db):
    today = date.today()
    j_plus_3 = (today + timedelta(days=3)).isoformat()
    pid = await _insert_produit(db, "Poulet")
    pers = await _insert_personnel(db, "Éric")
    cuisson_id = await _insert_cuisson(db, pid, pers, today.isoformat(), j_plus_3)
    # refroidissement jeté (cuisson ratée)
    await db.execute(
        """INSERT INTO refroidissements
        (boutique_id, date_refroidissement, personnel_id, produit_id, cuisson_id,
         heure_debut, heure_fin, duree_minutes, temperature_finale,
         conforme, jeter, dlc_finale)
        VALUES (1, ?, ?, ?, ?, '12:00', '13:30', 90, 8.0, 0, 1, ?)""",
        (today.isoformat(), pers, pid, cuisson_id, j_plus_3),
    )

    items = await get_stock_unifie(db, 1)
    sources = [it["source_type"] for it in items]
    # Le refroidissement jeté est exclu, mais comme la cuisson a un refroidissement
    # (même jeté) elle est aussi masquée → liste vide
    assert "refroidissement" not in sources
    assert "cuisson" not in sources

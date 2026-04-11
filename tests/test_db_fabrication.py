"""
test_db_fabrication.py — Tests unitaires : Module Fabrication (BDD)

Vérifie :
  - Insertion recette + ingrédients
  - Création fabrication + liaison lot via fabrication_lots
  - Respect des contraintes FOREIGN KEY
"""

import os
import pytest
import pytest_asyncio
import aiosqlite
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Fixture : base de données isolée en mémoire
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def fab_db():
    """
    Base SQLite dédiée aux tests fabrication.
    Schéma complet initialisé, données bouchons minimales insérées.
    """
    from src.database import SCHEMA_SQL

    tmp = tempfile.mktemp(suffix="_fab_test.db")
    db_path = Path(tmp)

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await db.executescript(SCHEMA_SQL)

        # --- Données bouchons minimales ---
        # Boutique obligatoire (contrainte FK partout)
        await db.execute(
            "INSERT INTO boutiques (id, nom) VALUES (1, 'Test Boucherie')"
        )

        # Produit fini (ex: saucisse maison)
        await db.execute(
            "INSERT INTO produits (id, boutique_id, nom, categorie, dlc_jours) "
            "VALUES (1, 1, 'Saucisse maison', 'plat_cuisine', 3)"
        )

        # Produit ingrédient (ex: porc haché)
        await db.execute(
            "INSERT INTO produits (id, boutique_id, nom, categorie, dlc_jours) "
            "VALUES (2, 1, 'Porc haché', 'matiere_premiere', 2)"
        )

        # Personnel
        await db.execute(
            "INSERT INTO personnel (id, boutique_id, prenom) VALUES (1, 1, 'Éric')"
        )

        # Fournisseur
        await db.execute(
            "INSERT INTO fournisseurs (id, boutique_id, nom) VALUES (1, 1, 'Fournisseur Test')"
        )

        # Réception + ligne (pour la traçabilité fabrication_lots)
        await db.execute(
            "INSERT INTO receptions (id, personnel_id, heure_reception) "
            "VALUES (1, 1, '08:00')"
        )
        await db.execute(
            "INSERT INTO reception_lignes (id, reception_id, produit_id, numero_lot) "
            "VALUES (1, 1, 2, 'LOT-FOURN-001')"
        )

        await db.commit()
        yield db

    db_path.unlink(missing_ok=True)


pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Test 1 : Création recette + ingrédient
# ---------------------------------------------------------------------------

async def test_creer_recette_avec_ingredient(fab_db):
    """Insère une recette avec 1 ingrédient et vérifie la lecture."""
    # Insertion recette
    cur = await fab_db.execute(
        "INSERT INTO recettes (nom, produit_fini_id, dlc_jours, instructions) "
        "VALUES ('Saucisse maison v1', 1, 3, 'Mélanger, embosser, ficeler.')"
    )
    recette_id = cur.lastrowid
    assert recette_id is not None and recette_id > 0

    # Insertion ingrédient lié à cette recette
    cur2 = await fab_db.execute(
        "INSERT INTO recette_ingredients (recette_id, produit_id, quantite, unite) "
        "VALUES (?, 2, 1.5, 'kg')",
        (recette_id,)
    )
    ingredient_id = cur2.lastrowid
    await fab_db.commit()

    # Vérifications
    row = await fab_db.execute(
        "SELECT * FROM recettes WHERE id = ?", (recette_id,)
    )
    recette = await row.fetchone()
    assert recette["nom"] == "Saucisse maison v1"
    assert recette["dlc_jours"] == 3
    assert recette["produit_fini_id"] == 1

    row2 = await fab_db.execute(
        "SELECT * FROM recette_ingredients WHERE recette_id = ?", (recette_id,)
    )
    ing = await row2.fetchone()
    assert ing["quantite"] == 1.5
    assert ing["unite"] == "kg"
    assert ing["produit_id"] == 2


# ---------------------------------------------------------------------------
# Test 2 : Création fabrication + traçabilité via fabrication_lots
# ---------------------------------------------------------------------------

async def test_creer_fabrication_avec_lot(fab_db):
    """Crée une fabrication et lie l'ingrédient au lot fournisseur."""
    # Prérequis : recette + ingrédient
    cur = await fab_db.execute(
        "INSERT INTO recettes (nom, produit_fini_id, dlc_jours) "
        "VALUES ('Recette Traçabilité', 1, 3)"
    )
    recette_id = cur.lastrowid

    cur2 = await fab_db.execute(
        "INSERT INTO recette_ingredients (recette_id, produit_id, quantite, unite) "
        "VALUES (?, 2, 2.0, 'kg')",
        (recette_id,)
    )
    ingredient_id = cur2.lastrowid
    await fab_db.commit()

    # Création fabrication
    cur3 = await fab_db.execute(
        "INSERT INTO fabrications (recette_id, date, lot_interne, personnel_id) "
        "VALUES (?, '2026-04-11', 'MC-20260411-0001', 1)",
        (recette_id,)
    )
    fabrication_id = cur3.lastrowid
    await fab_db.commit()

    assert fabrication_id is not None and fabrication_id > 0

    # Liaison traçabilité : ingrédient → lot fournisseur
    cur4 = await fab_db.execute(
        "INSERT INTO fabrication_lots (fabrication_id, recette_ingredient_id, reception_ligne_id) "
        "VALUES (?, ?, 1)",
        (fabrication_id, ingredient_id)
    )
    await fab_db.commit()

    # Vérification jointure complète
    row = await fab_db.execute(
        """
        SELECT f.lot_interne, rl.numero_lot, p.nom AS ingredient
        FROM fabrications f
        JOIN fabrication_lots fl ON fl.fabrication_id = f.id
        JOIN recette_ingredients ri ON ri.id = fl.recette_ingredient_id
        JOIN produits p ON p.id = ri.produit_id
        JOIN reception_lignes rl ON rl.id = fl.reception_ligne_id
        WHERE f.id = ?
        """,
        (fabrication_id,)
    )
    tracabilite = await row.fetchone()
    assert tracabilite is not None
    assert tracabilite["lot_interne"] == "MC-20260411-0001"
    assert tracabilite["numero_lot"] == "LOT-FOURN-001"
    assert tracabilite["ingredient"] == "Porc haché"


# ---------------------------------------------------------------------------
# Test 3 : Les FOREIGN KEY bloquent les insertions invalides
# ---------------------------------------------------------------------------

async def test_fk_bloque_recette_produit_inexistant(fab_db):
    """Une recette avec produit_fini_id inexistant doit lever une erreur FK."""
    with pytest.raises(aiosqlite.IntegrityError):
        await fab_db.execute(
            "INSERT INTO recettes (nom, produit_fini_id, dlc_jours) "
            "VALUES ('Recette invalide', 9999, 3)"
        )
        await fab_db.commit()


async def test_fk_bloque_fabrication_recette_inexistante(fab_db):
    """Une fabrication avec recette_id inexistant doit lever une erreur FK."""
    with pytest.raises(aiosqlite.IntegrityError):
        await fab_db.execute(
            "INSERT INTO fabrications (recette_id, date, lot_interne, personnel_id) "
            "VALUES (9999, '2026-04-11', 'MC-20260411-9999', 1)"
        )
        await fab_db.commit()


async def test_fk_bloque_fabrication_lots_reception_inexistante(fab_db):
    """fabrication_lots avec reception_ligne_id inexistant doit lever une erreur FK."""
    # Créer une recette + fabrication valides d'abord
    cur = await fab_db.execute(
        "INSERT INTO recettes (nom, produit_fini_id, dlc_jours) "
        "VALUES ('Recette FK test', 1, 3)"
    )
    recette_id = cur.lastrowid
    cur2 = await fab_db.execute(
        "INSERT INTO recette_ingredients (recette_id, produit_id) VALUES (?, 2)",
        (recette_id,)
    )
    ingredient_id = cur2.lastrowid
    cur3 = await fab_db.execute(
        "INSERT INTO fabrications (recette_id, date, lot_interne, personnel_id) "
        "VALUES (?, '2026-04-11', 'MC-20260411-FK01', 1)",
        (recette_id,)
    )
    fabrication_id = cur3.lastrowid
    await fab_db.commit()

    # Tenter de lier un lot inexistant
    with pytest.raises(aiosqlite.IntegrityError):
        await fab_db.execute(
            "INSERT INTO fabrication_lots (fabrication_id, recette_ingredient_id, reception_ligne_id) "
            "VALUES (?, ?, 9999)",
            (fabrication_id, ingredient_id)
        )
        await fab_db.commit()


async def test_cascade_delete_recette_supprime_ingredients(fab_db):
    """Supprimer une recette doit supprimer en cascade ses recette_ingredients."""
    cur = await fab_db.execute(
        "INSERT INTO recettes (nom, produit_fini_id, dlc_jours) "
        "VALUES ('Recette Cascade', 1, 2)"
    )
    recette_id = cur.lastrowid
    await fab_db.execute(
        "INSERT INTO recette_ingredients (recette_id, produit_id, quantite) "
        "VALUES (?, 2, 0.5)",
        (recette_id,)
    )
    await fab_db.commit()

    # Vérifier que l'ingrédient existe bien
    row = await fab_db.execute(
        "SELECT COUNT(*) AS cnt FROM recette_ingredients WHERE recette_id = ?",
        (recette_id,)
    )
    result = await row.fetchone()
    assert result["cnt"] == 1

    # Supprimer la recette → cascade
    await fab_db.execute("DELETE FROM recettes WHERE id = ?", (recette_id,))
    await fab_db.commit()

    row2 = await fab_db.execute(
        "SELECT COUNT(*) AS cnt FROM recette_ingredients WHERE recette_id = ?",
        (recette_id,)
    )
    result2 = await row2.fetchone()
    assert result2["cnt"] == 0

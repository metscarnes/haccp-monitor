"""
produits_a_creer.py — Produits étiquetés hors catalogue, à ajouter au catalogue de vente.

Quand l'équipe imprime une « étiquette prix » pour un article absent du catalogue de
vente (onglet Étiquette libre → Étiquette prix), c'est qu'un nouveau produit est en
rayon : on le note ici (nom, prix, unité) et une tâche apparaît dans les Tâches HACCP
du Hub jusqu'à ce qu'il soit créé dans le catalogue de vente (pré-rempli avec ces
infos), puis relié à un article d'achat comme d'habitude.

Une seule demande en attente par nom (sans accents ni majuscules) : réimprimer la même
étiquette met à jour le prix et le compteur, sans créer de doublon. Une demande dont le
produit existe désormais au catalogue (créé par n'importe quel chemin) se clôt d'elle-même.
  statut : en_attente | cree | ignore

Les fonctions prennent une connexion aiosqlite ouverte et ne commitent pas.
"""

import re
import unicodedata
from datetime import datetime
from typing import Optional

UNITES = ("kg", "piece")
NOM_MAX = 40


def _maintenant() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")   # heure locale (boutique)


def normaliser_nom(nom: str) -> str:
    """« Paupiette  de LAPIN » → « paupiette de lapin » ; « Pâté » → « pate »."""
    sans_accents = unicodedata.normalize("NFD", str(nom or ""))
    sans_accents = "".join(c for c in sans_accents if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sans_accents).strip().lower()


async def produit_existant(db, nom: str) -> Optional[dict]:
    """Produit ACTIF du catalogue de vente portant ce nom (accents/majuscules ignorés)."""
    cle = normaliser_nom(nom)
    if not cle:
        return None
    rows = await db.execute_fetchall(
        "SELECT id, nom, prix_vente_ttc, unite_vente FROM catalogue_vente "
        "WHERE boutique_id = 1 AND actif = 1")
    for r in rows:
        if normaliser_nom(r["nom"]) == cle:
            return dict(r)
    return None


async def noter_demande(db, nom: str, prix_ttc: Optional[float], unite: str) -> Optional[int]:
    """Note (ou met à jour) la demande pour ce produit. Renvoie son id, ou None si le
    produit existe déjà au catalogue de vente (rien à créer)."""
    nom = re.sub(r"\s+", " ", str(nom or "")).strip()[:NOM_MAX]
    cle = normaliser_nom(nom)
    if not cle or await produit_existant(db, nom):
        return None
    unite = unite if unite in UNITES else "kg"
    quand = _maintenant()
    rows = await db.execute_fetchall(
        "SELECT id FROM produits_a_creer WHERE nom_normalise = ? AND statut = 'en_attente'", (cle,))
    if rows:
        await db.execute(
            """UPDATE produits_a_creer SET nom = ?, prix_vente_ttc = ?, unite_vente = ?,
                      nb_etiquettes = nb_etiquettes + 1, derniere_at = ?
               WHERE id = ?""", (nom, prix_ttc, unite, quand, rows[0]["id"]))
        return rows[0]["id"]
    cur = await db.execute(
        """INSERT INTO produits_a_creer
               (nom, nom_normalise, prix_vente_ttc, unite_vente, nb_etiquettes,
                premiere_at, derniere_at, statut)
           VALUES (?, ?, ?, ?, 1, ?, ?, 'en_attente')""", (nom, cle, prix_ttc, unite, quand, quand))
    return cur.lastrowid


async def _clore_les_existants(db) -> None:
    """Demandes dont le produit a été créé entre-temps (par n'importe quel chemin) → cree."""
    for d in await db.execute_fetchall(
            "SELECT id, nom FROM produits_a_creer WHERE statut = 'en_attente'"):
        p = await produit_existant(db, d["nom"])
        if p:
            await marquer_cree(db, d["id"], p["id"])


async def lister_demandes(db) -> list[dict]:
    """Demandes en attente, la plus récente d'abord."""
    await _clore_les_existants(db)
    rows = await db.execute_fetchall(
        """SELECT id, nom, prix_vente_ttc, unite_vente, nb_etiquettes, premiere_at, derniere_at
           FROM produits_a_creer WHERE statut = 'en_attente'
           ORDER BY derniere_at DESC, id DESC""")
    return [dict(r) for r in rows]


async def compter_demandes(db) -> int:
    await _clore_les_existants(db)
    rows = await db.execute_fetchall(
        "SELECT COUNT(*) FROM produits_a_creer WHERE statut = 'en_attente'")
    return rows[0][0] if rows else 0


async def marquer_cree(db, demande_id: int, catalogue_vente_id: Optional[int]) -> bool:
    cur = await db.execute(
        """UPDATE produits_a_creer SET statut = 'cree', catalogue_vente_id = ?, traite_at = ?
           WHERE id = ? AND statut = 'en_attente'""",
        (catalogue_vente_id, _maintenant(), demande_id))
    return cur.rowcount > 0


async def ignorer(db, demande_id: int) -> bool:
    cur = await db.execute(
        "UPDATE produits_a_creer SET statut = 'ignore', traite_at = ? "
        "WHERE id = ? AND statut = 'en_attente'", (_maintenant(), demande_id))
    return cur.rowcount > 0

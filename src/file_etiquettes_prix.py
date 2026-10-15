"""
file_etiquettes_prix.py — File des étiquettes prix à réimprimer.

Chaîne : prix d'achat → proposition de prix de vente → prix validé → ÉTIQUETTE À REFAIRE.

Tout changement de catalogue_vente.prix_vente_ttc passe par
`prix_vente.tracer_changement_prix_vente`, qui appelle `ajouter_a_la_file` : le produit
entre dans la file quelle que soit l'origine du nouveau prix (proposition validée à la
réception, fiche produit, comparateur, import Excel, création).

Règles :
  - UNE ligne 'en_attente' par produit. Un 2e changement avant impression met à jour le
    nouveau prix mais garde l'ancien (= prix de l'étiquette encore en rayon).
  - Si le prix revient à celui de l'étiquette en rayon, plus rien à refaire : la ligne
    est retirée d'elle-même.
  - L'impression porte toujours le prix ACTUEL du catalogue (jamais un prix figé) ;
    elle sort le produit de la file (`sortir_de_la_file`).
  - Les produits désactivés ne sont pas proposés à l'impression.

Les fonctions prennent une connexion aiosqlite ouverte et ne commitent pas.
"""

from datetime import datetime
from typing import Iterable, Optional

STATUTS_TRAITES = ("imprimee", "retiree")
MODES = ("serveur", "navigateur", "manuel", "auto")


def _maintenant() -> str:
    # Heure locale, comme l'historique et les propositions de prix (affichage boutique).
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _meme_prix(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return round(float(a), 2) == round(float(b), 2)


async def ajouter_a_la_file(db, catalogue_vente_id: int, ancien_ttc, nouveau_ttc, *,
                            motif: Optional[str] = None) -> Optional[str]:
    """Met (ou garde) le produit dans la file après un changement de prix.

    Renvoie 'ajoute', 'mis_a_jour', 'retire' (prix revenu à celui de l'étiquette en
    rayon) ou None si le prix n'a pas changé.
    """
    if _meme_prix(ancien_ttc, nouveau_ttc):
        return None
    maintenant = _maintenant()
    cur = await db.execute(
        "SELECT id, prix_ancien_ttc FROM etiquettes_a_reimprimer "
        "WHERE catalogue_vente_id = ? AND statut = 'en_attente'",
        (catalogue_vente_id,),
    )
    ligne = await cur.fetchone()
    if ligne is None:
        await db.execute(
            """INSERT INTO etiquettes_a_reimprimer
                   (catalogue_vente_id, prix_ancien_ttc, prix_nouveau_ttc, motif,
                    created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (catalogue_vente_id, ancien_ttc, nouveau_ttc, motif, maintenant, maintenant),
        )
        return "ajoute"
    if ligne["prix_ancien_ttc"] is not None and _meme_prix(ligne["prix_ancien_ttc"], nouveau_ttc):
        await db.execute(
            """UPDATE etiquettes_a_reimprimer
               SET statut = 'retiree', mode = 'auto', prix_nouveau_ttc = ?,
                   updated_at = ?, traite_at = ?
               WHERE id = ?""",
            (nouveau_ttc, maintenant, maintenant, ligne["id"]),
        )
        return "retire"
    await db.execute(
        "UPDATE etiquettes_a_reimprimer SET prix_nouveau_ttc = ?, motif = ?, updated_at = ? "
        "WHERE id = ?",
        (nouveau_ttc, motif, maintenant, ligne["id"]),
    )
    return "mis_a_jour"


async def lister_file(db) -> list[dict]:
    """Produits actifs dont l'étiquette est à refaire, avec leur prix ACTUEL."""
    rows = await db.execute_fetchall(
        """SELECT e.id, e.catalogue_vente_id, e.prix_ancien_ttc, e.motif,
                  e.created_at, e.updated_at,
                  v.nom, v.prix_vente_ttc AS prix_actuel_ttc, v.famille, v.sous_famille,
                  v.unite_vente
           FROM etiquettes_a_reimprimer e
           JOIN catalogue_vente v ON v.id = e.catalogue_vente_id
           WHERE e.statut = 'en_attente' AND v.actif = 1 AND v.boutique_id = 1
           ORDER BY v.famille, v.nom"""
    )
    return [dict(r) for r in rows]


async def compter_file(db) -> int:
    cur = await db.execute(
        """SELECT COUNT(*) FROM etiquettes_a_reimprimer e
           JOIN catalogue_vente v ON v.id = e.catalogue_vente_id
           WHERE e.statut = 'en_attente' AND v.actif = 1 AND v.boutique_id = 1"""
    )
    return (await cur.fetchone())[0]


async def sortir_de_la_file(db, catalogue_vente_ids: Iterable[int], *,
                            statut: str = "imprimee", mode: str = "serveur") -> int:
    """Sort les produits de la file (étiquette imprimée, ou retirée à la main).
    Sans effet sur un produit qui n'y est pas. Renvoie le nombre de lignes traitées."""
    if statut not in STATUTS_TRAITES:
        raise ValueError(f"Statut inconnu : {statut}")
    if mode not in MODES:
        raise ValueError(f"Mode inconnu : {mode}")
    ids = sorted({int(i) for i in catalogue_vente_ids})
    if not ids:
        return 0
    maintenant = _maintenant()
    marques = ",".join("?" for _ in ids)
    cur = await db.execute(
        f"""UPDATE etiquettes_a_reimprimer
            SET statut = ?, mode = ?, updated_at = ?, traite_at = ?
            WHERE statut = 'en_attente' AND catalogue_vente_id IN ({marques})""",
        (statut, mode, maintenant, maintenant, *ids),
    )
    return cur.rowcount


async def historique_file(db, limit: int = 50) -> list[dict]:
    """Dernières étiquettes traitées (imprimées ou retirées), de la plus récente."""
    rows = await db.execute_fetchall(
        """SELECT e.catalogue_vente_id, e.prix_ancien_ttc, e.prix_nouveau_ttc, e.statut,
                  e.mode, e.motif, e.created_at, e.traite_at, v.nom
           FROM etiquettes_a_reimprimer e
           JOIN catalogue_vente v ON v.id = e.catalogue_vente_id
           WHERE e.statut IN ('imprimee', 'retiree')
           ORDER BY e.traite_at DESC, e.id DESC
           LIMIT ?""",
        (limit,),
    )
    return [dict(r) for r in rows]

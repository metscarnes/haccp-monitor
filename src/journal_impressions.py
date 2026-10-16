"""
journal_impressions.py — Historique des impressions d'étiquettes prix.

Journal en ajout seul : une ligne par produit et par impression, regroupées par `lot`
(un clic « Imprimer »). Le prix noté est le prix IMPRIMÉ sur l'étiquette (prix promo
pour une étiquette promo) : on sait ainsi quel prix était affiché en rayon et quand.

Les impressions par le navigateur sont notées à l'ouverture de la fenêtre
d'impression (on ne peut pas savoir si la feuille est vraiment sortie).

Les fonctions prennent une connexion aiosqlite ouverte et ne commitent pas.
"""

import uuid
from datetime import datetime
from typing import Optional

# hors_catalogue : étiquette prix d'un article absent du catalogue de vente (nom, prix
# et unité tapés à la main), cf. src/produits_a_creer.py.
TYPES = ("normal", "promo", "libre", "hors_catalogue")
MODES = ("serveur", "navigateur")
# Étiquette libre : ses lignes séparées par « \n » (5 lignes × 40 caractères au plus).
LIBELLE_MAX = 250


def _maintenant() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")   # heure locale (boutique)


def prix_imprime(produit: dict, type_etiquette: str) -> Optional[float]:
    """Prix porté par l'étiquette : prix promo pour le style promo, sinon prix catalogue."""
    promo = produit.get("promo") or {}
    if type_etiquette == "promo" and promo.get("prix_promo_ttc") is not None:
        return promo["prix_promo_ttc"]
    return produit.get("prix_vente_ttc")


async def journaliser(db, lignes: list[dict], *, mode: str = "serveur",
                      role: Optional[str] = None) -> Optional[str]:
    """Note une impression. lignes = [{catalogue_vente_id?, libelle, quantite, type,
    prix_ttc, unite_vente?}]. Renvoie l'identifiant du lot (None si rien à noter)."""
    lignes = [l for l in lignes if (l.get("quantite") or 0) > 0]
    if not lignes:
        return None
    if mode not in MODES:
        raise ValueError(f"Mode inconnu : {mode}")
    lot, quand = uuid.uuid4().hex[:12], _maintenant()
    for l in lignes:
        type_ = l.get("type") if l.get("type") in TYPES else "normal"
        await db.execute(
            """INSERT INTO impressions_etiquettes
                   (lot, imprime_at, catalogue_vente_id, libelle, quantite, type, prix_ttc,
                    mode, role, unite_vente)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (lot, quand, l.get("catalogue_vente_id"), (l.get("libelle") or "")[:LIBELLE_MAX],
             int(l["quantite"]), type_, l.get("prix_ttc"), mode, role, l.get("unite_vente")),
        )
    return lot


async def lister_impressions(db, limit: int = 50) -> list[dict]:
    """Dernières impressions (lots), de la plus récente : {lot, imprime_at, mode,
    total, lignes:[{libelle, quantite, type, prix_ttc, catalogue_vente_id, unite_vente}]}."""
    lots = await db.execute_fetchall(
        """SELECT lot, MAX(imprime_at) AS imprime_at, MAX(mode) AS mode, SUM(quantite) AS total
           FROM impressions_etiquettes GROUP BY lot
           ORDER BY MAX(imprime_at) DESC, MAX(id) DESC LIMIT ?""", (limit,))
    if not lots:
        return []
    ids = [l["lot"] for l in lots]
    marques = ",".join("?" for _ in ids)
    lignes = await db.execute_fetchall(
        f"""SELECT i.lot, COALESCE(v.nom, i.libelle) AS libelle, i.quantite, i.type, i.prix_ttc,
                   i.catalogue_vente_id, i.unite_vente
            FROM impressions_etiquettes i
            LEFT JOIN catalogue_vente v ON v.id = i.catalogue_vente_id
            WHERE i.lot IN ({marques}) ORDER BY i.id""", ids)
    par_lot: dict[str, list] = {}
    for l in lignes:
        par_lot.setdefault(l["lot"], []).append(
            {k: l[k] for k in ("libelle", "quantite", "type", "prix_ttc", "catalogue_vente_id",
                               "unite_vente")})
    return [{**dict(l), "lignes": par_lot.get(l["lot"], [])} for l in lots]

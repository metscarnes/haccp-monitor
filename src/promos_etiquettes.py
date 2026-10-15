"""
promos_etiquettes.py — Promotions sur étiquette prix.

Une promo est SEULEMENT une étiquette : le prix du catalogue de vente ne change pas
(marges et inventaire intacts). L'étiquette promo affiche :
  - le prix de RÉFÉRENCE barré = prix le plus bas pratiqué pendant les 30 jours qui
    précèdent la promo (Code de la consommation, art. L112-1-1, issu de la directive
    « Omnibus » 2019/2161, en vigueur depuis le 28/05/2022) ;
  - le prix promo, et l'économie par kg / par pièce.

Calcul du prix de référence (`prix_reference_30j`) — on retient le MINIMUM de :
  - chaque prix de vente en vigueur pendant la fenêtre [début − 30 j ; début[ (lu dans
    historique_prix_vente, qui trace chaque changement depuis le 04/10/2026) et le
    prix actuel ;
  - les prix des promos précédentes qui ont couru pendant cette fenêtre (ce sont aussi
    des prix pratiqués). C'est prudent : la règle des réductions successives
    permettrait parfois un prix barré plus haut, jamais plus bas — on ne risque donc
    jamais d'afficher une réduction exagérée.

Le prix de référence est figé à la création de la promo. À la date de fin, la promo se
termine d'elle-même (`terminer_promos_echues`, appelée à la lecture) et l'étiquette
normale repart dans la file « À réimprimer ».

Les fonctions prennent une connexion aiosqlite ouverte et ne commitent pas.
"""

from datetime import date, datetime, timedelta
from typing import Optional

JOURS_REFERENCE = 30


def _maintenant() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _jour(valeur) -> date:
    if isinstance(valeur, date):
        return valeur
    return date.fromisoformat(str(valeur)[:10])


async def prix_reference_30j(db, catalogue_vente_id: int,
                             date_debut: Optional[date] = None) -> dict:
    """Prix le plus bas pratiqué dans les 30 jours précédant `date_debut` (aujourd'hui
    par défaut). Renvoie {prix_reference_ttc, prix_actuel_ttc, depuis, prix_releves}."""
    debut = _jour(date_debut or date.today())
    fenetre = debut - timedelta(days=JOURS_REFERENCE)
    cur = await db.execute("SELECT prix_vente_ttc FROM catalogue_vente WHERE id = ?",
                           (catalogue_vente_id,))
    row = await cur.fetchone()
    if row is None:
        raise ValueError("Produit introuvable")
    actuel = row["prix_vente_ttc"]

    changements = await db.execute_fetchall(
        """SELECT prix_ancien_ttc, prix_nouveau_ttc, created_at FROM historique_prix_vente
           WHERE catalogue_vente_id = ? ORDER BY created_at, id""",
        (catalogue_vente_id,),
    )
    avant = [c for c in changements if _jour(c["created_at"]) < fenetre]
    pendant = [c for c in changements if fenetre <= _jour(c["created_at"]) < debut]
    prix = []
    # Prix en vigueur au début de la fenêtre.
    if avant:
        prix.append(avant[-1]["prix_nouveau_ttc"])
    elif pendant:
        prix.append(pendant[0]["prix_ancien_ttc"])
    # Chaque prix fixé pendant la fenêtre, puis le prix actuel.
    prix += [c["prix_nouveau_ttc"] for c in pendant]
    prix.append(actuel)

    # Promos précédentes ayant couru pendant la fenêtre.
    promos = await db.execute_fetchall(
        """SELECT prix_promo_ttc FROM promotions_etiquettes
           WHERE catalogue_vente_id = ? AND date_debut < ? AND date_fin >= ?""",
        (catalogue_vente_id, debut.isoformat(), fenetre.isoformat()),
    )
    prix += [p["prix_promo_ttc"] for p in promos]

    releves = sorted({round(float(p), 2) for p in prix if p is not None})
    return {
        "prix_reference_ttc": releves[0] if releves else None,
        "prix_actuel_ttc": actuel,
        "depuis": fenetre.isoformat(),
        "prix_releves": releves,
    }


async def marge_produit(db, catalogue_vente_id: int) -> dict:
    """Coût d'achat de référence (choisi dans le comparateur) et marge actuelle du
    produit, pour juger une promo. Même calcul que les propositions de prix
    (taux de marque sur HT). `cout_ht` None si le produit n'est relié à aucun achat."""
    from src.prix_vente import couts_produits, taux_marque
    cur = await db.execute(
        "SELECT groupe_id FROM comparatif_groupe_vente WHERE catalogue_vente_id = ?",
        (catalogue_vente_id,))
    groupe = await cur.fetchone()
    infos = (await couts_produits(db, cv_ids=[catalogue_vente_id],
                                  actifs_seulement=False)).get(catalogue_vente_id)
    if infos is None or infos["cout"] is None:
        return {"cout_ht": None, "groupe_id": groupe["groupe_id"] if groupe else None}
    return {
        "cout_ht": infos["cout"],
        "tva_percent": infos["tva_percent"],
        "taux_actuel": taux_marque(infos["prix_vente_ttc"], infos["tva_percent"], infos["cout"]),
        "article": infos["cf_designation"],
        "fournisseur": infos["fournisseur_nom"],
        "groupe_id": groupe["groupe_id"] if groupe else None,
    }


async def promos_actives(db) -> dict[int, dict]:
    """Promos en cours, par produit : {catalogue_vente_id: promo}."""
    rows = await db.execute_fetchall(
        "SELECT * FROM promotions_etiquettes WHERE statut = 'active'")
    return {r["catalogue_vente_id"]: dict(r) for r in rows}


async def lister_promos(db) -> list[dict]:
    rows = await db.execute_fetchall(
        """SELECT p.*, v.nom, v.unite_vente, v.prix_vente_ttc AS prix_actuel_ttc
           FROM promotions_etiquettes p
           JOIN catalogue_vente v ON v.id = p.catalogue_vente_id
           WHERE p.statut = 'active'
           ORDER BY p.date_fin, v.nom""")
    return [dict(r) for r in rows]


async def creer_promo(db, catalogue_vente_id: int, prix_promo_ttc: float, date_fin,
                      aujourd_hui: Optional[date] = None) -> dict:
    """Crée la promo du produit, ou met à jour sa promo en cours (prix, date de fin) en
    gardant son prix de référence figé. ValueError si la promo n'est pas valable."""
    jour = _jour(aujourd_hui or date.today())
    fin = _jour(date_fin)
    if fin < jour:
        raise ValueError("La date de fin ne peut pas être passée.")
    prix_promo = round(float(prix_promo_ttc), 2)
    if prix_promo <= 0:
        raise ValueError("Le prix promo doit être positif.")

    cur = await db.execute(
        "SELECT id, actif, prix_vente_ttc FROM catalogue_vente WHERE id = ?",
        (catalogue_vente_id,))
    produit = await cur.fetchone()
    if produit is None or not produit["actif"]:
        raise ValueError("Produit introuvable ou désactivé.")
    if produit["prix_vente_ttc"] is None:
        raise ValueError("Ce produit n'a pas de prix de vente.")

    en_cours = (await promos_actives(db)).get(catalogue_vente_id)
    reference = (en_cours["prix_reference_ttc"] if en_cours else
                 (await prix_reference_30j(db, catalogue_vente_id, jour))["prix_reference_ttc"])
    if prix_promo >= reference:
        ref_txt = f"{reference:.2f}".replace(".", ",")
        raise ValueError(f"Le prix promo doit être inférieur au prix de référence "
                         f"({ref_txt} €, plus bas prix des 30 derniers jours).")

    if en_cours:
        await db.execute(
            "UPDATE promotions_etiquettes SET prix_promo_ttc = ?, date_fin = ? WHERE id = ?",
            (prix_promo, fin.isoformat(), en_cours["id"]))
        promo_id = en_cours["id"]
    else:
        cur = await db.execute(
            """INSERT INTO promotions_etiquettes
                   (catalogue_vente_id, prix_reference_ttc, prix_promo_ttc, date_debut,
                    date_fin, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (catalogue_vente_id, reference, prix_promo, jour.isoformat(), fin.isoformat(),
             _maintenant()))
        promo_id = cur.lastrowid
    cur = await db.execute("SELECT * FROM promotions_etiquettes WHERE id = ?", (promo_id,))
    return dict(await cur.fetchone())


async def terminer_promo(db, promo_id: int) -> Optional[dict]:
    """Termine une promo : l'étiquette normale (prix actuel) repart dans « À réimprimer »."""
    from src.file_etiquettes_prix import ajouter_a_la_file
    cur = await db.execute(
        """SELECT p.*, v.prix_vente_ttc AS prix_actuel_ttc FROM promotions_etiquettes p
           JOIN catalogue_vente v ON v.id = p.catalogue_vente_id
           WHERE p.id = ? AND p.statut = 'active'""", (promo_id,))
    promo = await cur.fetchone()
    if promo is None:
        return None
    await db.execute(
        "UPDATE promotions_etiquettes SET statut = 'terminee', terminee_at = ? WHERE id = ?",
        (_maintenant(), promo_id))
    await ajouter_a_la_file(db, promo["catalogue_vente_id"], promo["prix_promo_ttc"],
                            promo["prix_actuel_ttc"], motif="fin_promo")
    return dict(promo)


async def terminer_promos_echues(db, aujourd_hui: Optional[date] = None) -> int:
    """Termine les promos dont la date de fin est passée. Renvoie leur nombre."""
    jour = _jour(aujourd_hui or date.today())
    rows = await db.execute_fetchall(
        "SELECT id FROM promotions_etiquettes WHERE statut = 'active' AND date_fin < ?",
        (jour.isoformat(),))
    for r in rows:
        await terminer_promo(db, r["id"])
    return len(rows)

"""
routes_inventaire.py — Module Inventaire VALORISÉ (stock comptable en €)

Brique DISTINCTE du stock FIFO traçabilité (routes_stock.py, qui suit les lots/DLC).
Ici : une « photo » datée du stock physique. Chaque ligne est valorisée au prix
d'achat €/kg figé À LA SAISIE (via _calc_prix_kg du module achats), de sorte que la
photo reste juste même si le prix catalogue évolue ensuite.

La somme des lignes = stock comptable à l'instant T. Sert au calcul de marge :
    Marge brute = CA HT − (Achats HT période + Stock Initial − Stock Final)

GET    /api/inventaire/sessions                    → historique des photos d'inventaire
POST   /api/inventaire/sessions                    → créer une session datée
GET    /api/inventaire/sessions/{id}               → détail + lignes + total
PUT    /api/inventaire/sessions/{id}/cloturer      → fige valeur_totale_ht
DELETE /api/inventaire/sessions/{id}               → supprimer une session (en_cours)

POST   /api/inventaire/sessions/{id}/lignes        → ajouter une ligne (valorisée)
PUT    /api/inventaire/lignes/{id}                 → corriger une ligne (revalorise)
DELETE /api/inventaire/lignes/{id}                 → supprimer une ligne

GET    /api/inventaire/catalogue-recherche?q=      → autocomplete article + €/kg pré-calculé + badges (réf/habituel/reçu)
GET    /api/inventaire/familles                    → familles/sous-familles (navigation rayon)
GET    /api/inventaire/fournisseurs                → fournisseurs du catalogue (filtre rayon)

GET    /api/inventaire/marge?date_debut=&date_fin= → tableau de bord marge (CA−CMV)
GET    /api/inventaire/marge/tva                   → taux TVA paramétré (CA TTC→HT)
PUT    /api/inventaire/marge/tva                   → modifier le taux TVA
GET    /api/inventaire/marge/achats-reels?date_debut=&date_fin= → achats HT réels de la période
PUT    /api/inventaire/marge/achats-reels          → saisir/effacer les achats réels d'une période
PUT    /api/inventaire/marge/ca-ajuster            → caler le CA TTC total (ligne d'ajustement)
"""
import logging
from datetime import date, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.database import get_db, get_parametre, set_parametre
from src.api.routes_achats import _calc_prix_kg

# Taux de TVA par défaut pour convertir le CA TTC → HT (boucherie = 5,5 %).
TVA_DEFAUT_PCT = 5.5
CLE_TVA = "marge_tva_ca_pct"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inventaire", tags=["inventaire"])

BOUTIQUE_ID = 1
UNITES_VALIDES = ("kg", "piece", "colis")


# ---------------------------------------------------------------------------
# Modèles Pydantic
# ---------------------------------------------------------------------------

class InventaireCreate(BaseModel):
    libelle: Optional[str] = None
    date_inventaire: Optional[str] = None  # YYYY-MM-DD, défaut = aujourd'hui (DB)
    personnel_id: Optional[int] = None


class LigneCreate(BaseModel):
    catalogue_fournisseur_id: Optional[int] = None
    designation_libre: Optional[str] = None
    quantite: float
    unite_saisie: str = "kg"          # kg | piece | colis
    # Poids d'une pièce (kg) : fourni par l'opérateur quand il saisit « à la pièce »
    # et qu'on ne peut pas le déduire du catalogue. Permet de valoriser honnêtement.
    poids_piece_kg: Optional[float] = None


class LigneUpdate(BaseModel):
    quantite: Optional[float] = None
    unite_saisie: Optional[str] = None
    poids_piece_kg: Optional[float] = None


# ---------------------------------------------------------------------------
# Valorisation d'une ligne — cœur du module
# ---------------------------------------------------------------------------

def _valoriser_ligne(unite_saisie, quantite, poids_piece_kg, article):
    """Ramène une ligne d'inventaire à (prix_kg_fige, poids_kg_calcule, valeur_ht).

    `article` = dict catalogue (format_prix, prix_achat_ht, poids_colis_kg, famille,
    qte_par_colis, poids_unitaire_kg) ou None (article hors catalogue).

    Principe (même esprit que _calc_prix_kg) : on ne renvoie JAMAIS un chiffre faux.
    Si on ne peut pas valoriser honnêtement → (prix_kg, None, None) : la quantité est
    quand même enregistrée mais la valeur reste « indisponible » (l'UI le signale).

    - unité 'kg'    : poids = quantité telle quelle.
    - unité 'colis' : poids = quantité × poids_colis_kg du catalogue.
    - unité 'piece' : poids = quantité × poids unitaire. Poids unitaire = poids_piece_kg
                      saisi en priorité, sinon dérivé du catalogue
                      (poids_unitaire_kg, ou poids_colis_kg / qte_par_colis).
    Le prix €/kg de référence vient toujours du catalogue via _calc_prix_kg.
    """
    prix_kg = None
    if article is not None:
        prix_kg = _calc_prix_kg(
            article.get("format_prix"),
            article.get("prix_achat_ht"),
            article.get("poids_colis_kg"),
            article.get("famille"),
        )

    poids_kg = None
    u = (unite_saisie or "kg").lower()
    q = float(quantite)

    if u == "kg":
        poids_kg = q
    elif u == "colis":
        pc = article.get("poids_colis_kg") if article else None
        if pc:
            poids_kg = q * float(pc)
    elif u == "piece":
        # 1) poids saisi par l'opérateur (le plus fiable terrain)
        ppk = poids_piece_kg
        # 2) sinon poids unitaire catalogue
        if not ppk and article:
            if article.get("poids_unitaire_kg"):
                ppk = article["poids_unitaire_kg"]
            elif article.get("poids_colis_kg") and article.get("qte_par_colis"):
                try:
                    ppk = float(article["poids_colis_kg"]) / float(article["qte_par_colis"])
                except (ZeroDivisionError, TypeError):
                    ppk = None
        if ppk:
            poids_kg = q * float(ppk)

    valeur_ht = None
    if poids_kg is not None and prix_kg is not None:
        valeur_ht = round(poids_kg * prix_kg, 2)

    poids_kg = round(poids_kg, 4) if poids_kg is not None else None
    return prix_kg, poids_kg, valeur_ht


async def _charger_article(db, catalogue_fournisseur_id):
    """Charge les champs catalogue utiles à la valorisation, ou None."""
    if not catalogue_fournisseur_id:
        return None
    async with db.execute(
        """SELECT id, designation, code_article, famille, sous_famille,
                  format_prix, prix_achat_ht, poids_colis_kg,
                  qte_par_colis, poids_unitaire_kg
           FROM catalogue_fournisseur WHERE id = ?""",
        (catalogue_fournisseur_id,),
    ) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def _recalculer_total(db, inventaire_id):
    """Somme des valeurs des lignes (les NULL = non valorisées sont ignorées)."""
    async with db.execute(
        "SELECT COALESCE(SUM(valeur_ht), 0) AS tot FROM inventaire_lignes WHERE inventaire_id = ?",
        (inventaire_id,),
    ) as cur:
        row = await cur.fetchone()
    return round(float(row["tot"]), 2)


# ---------------------------------------------------------------------------
# Sessions d'inventaire
# ---------------------------------------------------------------------------

@router.get("/sessions")
async def liste_sessions(limit: int = Query(50, ge=1, le=500)):
    """Historique des photos d'inventaire (pour comparer Stock Initial / Stock Final)."""
    async with get_db() as db:
        async with db.execute(
            """SELECT i.id, i.date_inventaire, i.libelle, i.statut,
                      i.valeur_totale_ht, i.created_at, i.cloture_at,
                      p.prenom AS personnel_prenom,
                      (SELECT COUNT(*) FROM inventaire_lignes l WHERE l.inventaire_id = i.id) AS nb_lignes
               FROM inventaires i
               LEFT JOIN personnel p ON p.id = i.personnel_id
               WHERE i.boutique_id = ?
               ORDER BY i.date_inventaire DESC, i.id DESC
               LIMIT ?""",
            (BOUTIQUE_ID, limit),
        ) as cur:
            rows = await cur.fetchall()
        return {"sessions": [dict(r) for r in rows]}


@router.post("/sessions", status_code=201)
async def creer_session(data: InventaireCreate):
    """Crée une nouvelle session d'inventaire (statut en_cours)."""
    async with get_db() as db:
        cur = await db.execute(
            """INSERT INTO inventaires (boutique_id, date_inventaire, libelle, personnel_id)
               VALUES (?, COALESCE(?, CURRENT_DATE), ?, ?)""",
            (BOUTIQUE_ID, data.date_inventaire, data.libelle, data.personnel_id),
        )
        await db.commit()
        return {"ok": True, "id": cur.lastrowid}


@router.get("/sessions/{inventaire_id}")
async def detail_session(inventaire_id: int):
    """Détail d'une session : entête + lignes valorisées + total recalculé."""
    async with get_db() as db:
        async with db.execute(
            """SELECT i.*, p.prenom AS personnel_prenom
               FROM inventaires i
               LEFT JOIN personnel p ON p.id = i.personnel_id
               WHERE i.id = ? AND i.boutique_id = ?""",
            (inventaire_id, BOUTIQUE_ID),
        ) as cur:
            inv = await cur.fetchone()
        if not inv:
            raise HTTPException(404, "Inventaire introuvable")

        async with db.execute(
            """SELECT l.*, c.designation AS catalogue_designation,
                      c.code_article, c.famille, c.sous_famille,
                      f.nom AS fournisseur_nom
               FROM inventaire_lignes l
               LEFT JOIN catalogue_fournisseur c ON c.id = l.catalogue_fournisseur_id
               LEFT JOIN fournisseurs f ON f.id = c.fournisseur_id
               WHERE l.inventaire_id = ?
               ORDER BY l.id DESC""",
            (inventaire_id,),
        ) as cur:
            lignes = [dict(r) for r in await cur.fetchall()]

        for l in lignes:
            l["designation"] = l.get("catalogue_designation") or l.get("designation_libre") or "—"

        inv = dict(inv)
        # Total « vivant » tant que la session est en cours ; figé après clôture.
        total_vivant = await _recalculer_total(db, inventaire_id)
        return {
            "inventaire": inv,
            "lignes": lignes,
            "total_ht": inv["valeur_totale_ht"] if inv["statut"] == "cloture" else total_vivant,
            "nb_lignes": len(lignes),
            "nb_non_valorisees": sum(1 for l in lignes if l["valeur_ht"] is None),
        }


@router.put("/sessions/{inventaire_id}/cloturer")
async def cloturer_session(inventaire_id: int):
    """Fige la valeur totale HT de la session (statut → cloture)."""
    async with get_db() as db:
        async with db.execute(
            "SELECT statut FROM inventaires WHERE id = ? AND boutique_id = ?",
            (inventaire_id, BOUTIQUE_ID),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Inventaire introuvable")
        if row["statut"] == "cloture":
            raise HTTPException(409, "Inventaire déjà clôturé")

        total = await _recalculer_total(db, inventaire_id)
        await db.execute(
            """UPDATE inventaires
               SET statut = 'cloture', valeur_totale_ht = ?, cloture_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (total, inventaire_id),
        )
        await db.commit()
        return {"ok": True, "id": inventaire_id, "valeur_totale_ht": total}


@router.delete("/sessions/{inventaire_id}", status_code=204)
async def supprimer_session(inventaire_id: int):
    """Supprime une session en cours (et ses lignes via ON DELETE CASCADE)."""
    async with get_db() as db:
        async with db.execute(
            "SELECT statut FROM inventaires WHERE id = ? AND boutique_id = ?",
            (inventaire_id, BOUTIQUE_ID),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Inventaire introuvable")
        if row["statut"] == "cloture":
            raise HTTPException(409, "Inventaire clôturé : suppression interdite (historique comptable)")
        # CASCADE n'est pas garanti sans PRAGMA foreign_keys=ON → on supprime explicitement.
        await db.execute("DELETE FROM inventaire_lignes WHERE inventaire_id = ?", (inventaire_id,))
        await db.execute("DELETE FROM inventaires WHERE id = ?", (inventaire_id,))
        await db.commit()
        return None


# ---------------------------------------------------------------------------
# Lignes d'inventaire
# ---------------------------------------------------------------------------

async def _assert_session_modifiable(db, inventaire_id):
    async with db.execute(
        "SELECT statut FROM inventaires WHERE id = ? AND boutique_id = ?",
        (inventaire_id, BOUTIQUE_ID),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Inventaire introuvable")
    if row["statut"] == "cloture":
        raise HTTPException(409, "Inventaire clôturé : ajout/modification impossible")


@router.post("/sessions/{inventaire_id}/lignes", status_code=201)
async def ajouter_ligne(inventaire_id: int, data: LigneCreate):
    """Ajoute une ligne à l'inventaire, valorisée à la volée."""
    if (data.unite_saisie or "kg").lower() not in UNITES_VALIDES:
        raise HTTPException(422, f"unite_saisie doit être l'une de {UNITES_VALIDES}")
    if not data.catalogue_fournisseur_id and not (data.designation_libre or "").strip():
        raise HTTPException(422, "catalogue_fournisseur_id ou designation_libre requis")

    async with get_db() as db:
        await _assert_session_modifiable(db, inventaire_id)
        article = await _charger_article(db, data.catalogue_fournisseur_id)
        # FK explicite : un id catalogue fourni mais inconnu → 404 propre (pas un 500 SQLite).
        if data.catalogue_fournisseur_id and article is None:
            raise HTTPException(404, "Article catalogue introuvable")
        prix_kg, poids_kg, valeur = _valoriser_ligne(
            data.unite_saisie, data.quantite, data.poids_piece_kg, article
        )
        cur = await db.execute(
            """INSERT INTO inventaire_lignes
                 (inventaire_id, catalogue_fournisseur_id, designation_libre,
                  quantite, unite_saisie, prix_kg_fige, poids_kg_calcule, valeur_ht)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (inventaire_id, data.catalogue_fournisseur_id, data.designation_libre,
             data.quantite, data.unite_saisie.lower(), prix_kg, poids_kg, valeur),
        )
        await db.commit()
        total = await _recalculer_total(db, inventaire_id)
        return {
            "ok": True, "id": cur.lastrowid,
            "prix_kg_fige": prix_kg, "poids_kg_calcule": poids_kg,
            "valeur_ht": valeur, "total_ht": total,
        }


@router.put("/lignes/{ligne_id}")
async def modifier_ligne(ligne_id: int, data: LigneUpdate):
    """Modifie quantité/unité d'une ligne → revalorise (prix €/kg article inchangé)."""
    async with get_db() as db:
        async with db.execute(
            """SELECT l.*, i.statut AS inv_statut
               FROM inventaire_lignes l
               JOIN inventaires i ON i.id = l.inventaire_id
               WHERE l.id = ?""",
            (ligne_id,),
        ) as cur:
            ligne = await cur.fetchone()
        if not ligne:
            raise HTTPException(404, "Ligne introuvable")
        if ligne["inv_statut"] == "cloture":
            raise HTTPException(409, "Inventaire clôturé : modification impossible")

        ligne = dict(ligne)
        unite = (data.unite_saisie or ligne["unite_saisie"]).lower()
        if unite not in UNITES_VALIDES:
            raise HTTPException(422, f"unite_saisie doit être l'une de {UNITES_VALIDES}")
        quantite = data.quantite if data.quantite is not None else ligne["quantite"]
        poids_piece = data.poids_piece_kg

        article = await _charger_article(db, ligne["catalogue_fournisseur_id"])
        prix_kg, poids_kg, valeur = _valoriser_ligne(unite, quantite, poids_piece, article)

        await db.execute(
            """UPDATE inventaire_lignes
               SET quantite = ?, unite_saisie = ?, prix_kg_fige = ?,
                   poids_kg_calcule = ?, valeur_ht = ?
               WHERE id = ?""",
            (quantite, unite, prix_kg, poids_kg, valeur, ligne_id),
        )
        await db.commit()
        total = await _recalculer_total(db, ligne["inventaire_id"])
        return {
            "ok": True, "id": ligne_id,
            "prix_kg_fige": prix_kg, "poids_kg_calcule": poids_kg,
            "valeur_ht": valeur, "total_ht": total,
        }


@router.delete("/lignes/{ligne_id}", status_code=200)
async def supprimer_ligne(ligne_id: int):
    async with get_db() as db:
        async with db.execute(
            """SELECT l.inventaire_id, i.statut AS inv_statut
               FROM inventaire_lignes l
               JOIN inventaires i ON i.id = l.inventaire_id
               WHERE l.id = ?""",
            (ligne_id,),
        ) as cur:
            ligne = await cur.fetchone()
        if not ligne:
            raise HTTPException(404, "Ligne introuvable")
        if ligne["inv_statut"] == "cloture":
            raise HTTPException(409, "Inventaire clôturé : suppression impossible")
        await db.execute("DELETE FROM inventaire_lignes WHERE id = ?", (ligne_id,))
        await db.commit()
        total = await _recalculer_total(db, ligne["inventaire_id"])
        return {"ok": True, "total_ht": total}


# ---------------------------------------------------------------------------
# Aides à la saisie : recherche article + familles
# ---------------------------------------------------------------------------

# Fenêtre (jours) pour considérer un article comme « reçu récemment » (badge 📦).
RECU_RECEMMENT_JOURS = 30


async def _flags_articles(db, cat_ids: set):
    """Pour un ensemble d'articles catalogue, renvoie 3 ensembles d'ids :
    référencés (⭐ comparateur), habituels (🔁 déjà commandés), reçus récemment (📦).

    Permet de baliser les résultats de recherche de l'inventaire sans 3 appels
    cross-module côté client.
    """
    if not cat_ids:
        return set(), set(), set()
    placeholders = ",".join("?" * len(cat_ids))
    ids = list(cat_ids)

    # ⭐ Références = lignes d'achat choisies dans le comparateur fournisseurs.
    async with db.execute(
        f"""SELECT DISTINCT gv.ligne_choisie_id AS id
            FROM comparatif_groupe_vente gv
            JOIN comparatif_groupe g ON g.id = gv.groupe_id
            WHERE gv.ligne_choisie_id IN ({placeholders})
              AND g.boutique_id = ?""",
        ids + [BOUTIQUE_ID],
    ) as cur:
        refs = {r["id"] for r in await cur.fetchall()}

    # 🔁 Habituels = déjà commandés (commandes confirmées ou livrées).
    async with db.execute(
        f"""SELECT DISTINCT cl.catalogue_fournisseur_id AS id
            FROM commande_lignes cl
            JOIN commandes c ON c.id = cl.commande_id
            WHERE cl.catalogue_fournisseur_id IN ({placeholders})
              AND c.boutique_id = ?
              AND c.statut IN ('confirmee', 'livree')""",
        ids + [BOUTIQUE_ID],
    ) as cur:
        habituels = {r["id"] for r in await cur.fetchall()}

    # 📦 Reçus récemment = présents dans une réception des N derniers jours.
    seuil = (date.today() - timedelta(days=RECU_RECEMMENT_JOURS)).isoformat()
    async with db.execute(
        f"""SELECT DISTINCT rl.catalogue_fournisseur_id AS id
            FROM reception_lignes rl
            JOIN receptions r ON r.id = rl.reception_id
            WHERE rl.catalogue_fournisseur_id IN ({placeholders})
              AND r.date_reception >= ?""",
        ids + [seuil],
    ) as cur:
        recus = {r["id"] for r in await cur.fetchall()}

    return refs, habituels, recus


@router.get("/catalogue-recherche")
async def recherche_catalogue(
    q: Optional[str] = Query(None),
    famille: Optional[str] = Query(None),
    sous_famille: Optional[str] = Query(None),
    fournisseur_id: Optional[int] = Query(None),
    badge: Optional[str] = Query(None, description="reference | habituel | recu"),
    limit: int = Query(40, ge=1, le=200),
):
    """Recherche d'articles catalogue avec €/kg pré-calculé (autocomplete + rayon).

    Filtres combinables : `q` (texte sur designation/code), `famille`,
    `sous_famille`, `fournisseur_id`, et `badge` (référencé / habituel / reçu
    récemment). Chaque article renvoyé porte les flags `est_reference`,
    `est_habituel`, `recu_recemment` pour l'affichage de pastilles.
    """
    clauses = ["c.actif = 1"]
    params: List = []
    if q and q.strip():
        clauses.append("(c.designation LIKE ? OR c.code_article LIKE ?)")
        like = f"%{q.strip()}%"
        params += [like, like]
    if famille:
        clauses.append("c.famille = ?")
        params.append(famille)
    if sous_famille:
        clauses.append("c.sous_famille = ?")
        params.append(sous_famille)
    if fournisseur_id:
        clauses.append("c.fournisseur_id = ?")
        params.append(fournisseur_id)

    where = " AND ".join(clauses)
    # On élargit la limite SQL si un filtre badge est demandé : le filtrage
    # par badge se fait en Python (sur les flags), donc on récupère un peu plus
    # large avant de retrancher à `limit`.
    sql_limit = limit if not badge else min(limit * 5, 1000)
    params.append(sql_limit)
    async with get_db() as db:
        async with db.execute(
            f"""SELECT c.id, c.designation, c.code_article, c.famille, c.sous_famille,
                       c.format_prix, c.prix_achat_ht, c.poids_colis_kg,
                       c.qte_par_colis, c.poids_unitaire_kg, c.unites_autorisees,
                       c.fournisseur_id, f.nom AS fournisseur_nom
                FROM catalogue_fournisseur c
                LEFT JOIN fournisseurs f ON f.id = c.fournisseur_id
                WHERE {where}
                ORDER BY c.designation
                LIMIT ?""",
            params,
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]

        refs, habituels, recus = await _flags_articles(db, {r["id"] for r in rows})

        for r in rows:
            r["prix_kg"] = _calc_prix_kg(
                r.get("format_prix"), r.get("prix_achat_ht"),
                r.get("poids_colis_kg"), r.get("famille"),
            )
            r["est_reference"] = r["id"] in refs
            r["est_habituel"] = r["id"] in habituels
            r["recu_recemment"] = r["id"] in recus

        if badge == "reference":
            rows = [r for r in rows if r["est_reference"]]
        elif badge == "habituel":
            rows = [r for r in rows if r["est_habituel"]]
        elif badge == "recu":
            rows = [r for r in rows if r["recu_recemment"]]

        return {"articles": rows[:limit]}


@router.get("/fournisseurs")
async def liste_fournisseurs_catalogue():
    """Fournisseurs ayant au moins un article actif au catalogue (filtre rayon)."""
    async with get_db() as db:
        async with db.execute(
            """SELECT f.id, f.nom, COUNT(*) AS nb
               FROM catalogue_fournisseur c
               JOIN fournisseurs f ON f.id = c.fournisseur_id
               WHERE c.actif = 1
               GROUP BY f.id, f.nom
               ORDER BY f.nom""",
        ) as cur:
            return {"fournisseurs": [dict(r) for r in await cur.fetchall()]}


class PoidsPieceUpdate(BaseModel):
    poids_unitaire_kg: float


@router.put("/catalogue/{catalogue_fournisseur_id}/poids-piece")
async def memoriser_poids_piece(catalogue_fournisseur_id: int, data: PoidsPieceUpdate):
    """Mémorise le poids unitaire (kg) d'une pièce sur l'article catalogue.

    Appelé quand l'opérateur saisit « à la pièce » un article dont le poids unitaire
    était inconnu : on l'enregistre une fois (poids_unitaire_kg) pour ne plus le
    redemander. On ne touche QUE poids_unitaire_kg (pas au format_prix ni au prix) ;
    poids_colis_kg reste géré par le module achats (qte_par_colis × poids_unitaire_kg).
    """
    if data.poids_unitaire_kg <= 0:
        raise HTTPException(422, "poids_unitaire_kg doit être > 0")
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM catalogue_fournisseur WHERE id = ?", (catalogue_fournisseur_id,),
        ) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, "Article catalogue introuvable")
        await db.execute(
            "UPDATE catalogue_fournisseur SET poids_unitaire_kg = ? WHERE id = ?",
            (data.poids_unitaire_kg, catalogue_fournisseur_id),
        )
        await db.commit()
        return {"ok": True, "id": catalogue_fournisseur_id,
                "poids_unitaire_kg": data.poids_unitaire_kg}


class PrixKgUpdate(BaseModel):
    prix_kg: float


@router.put("/catalogue/{catalogue_fournisseur_id}/prix-kg")
async def modifier_prix_kg(catalogue_fournisseur_id: int, data: PrixKgUpdate):
    """Met à jour le prix d'achat du catalogue à partir d'un prix €/kg saisi à l'inventaire.

    L'opérateur saisit un prix AU KILO ; on le reconvertit en `prix_achat_ht` selon le
    format de l'article, de façon à ce que `_calc_prix_kg` redonne EXACTEMENT ce €/kg :
      - viande / format 'kg' : prix_achat_ht = prix_kg (le prix d'achat EST le €/kg).
      - format 'colis'       : prix_achat_ht = prix_kg × poids_colis_kg (prix du colis),
                               donc poids_colis_kg DOIT être connu.
    La correction REMONTE au catalogue achats (référence partagée). Les lignes d'inventaire
    déjà saisies ne sont pas touchées ici (le front revalorise la ligne courante à part).
    """
    if data.prix_kg < 0:
        raise HTTPException(422, "prix_kg ne peut pas être négatif")
    async with get_db() as db:
        article = await _charger_article(db, catalogue_fournisseur_id)
        if article is None:
            raise HTTPException(404, "Article catalogue introuvable")

        famille = (article.get("famille") or "").strip().lower()
        format_prix = article.get("format_prix")
        if famille == "viande" or format_prix == "kg":
            nouveau_prix_achat = round(float(data.prix_kg), 4)
        elif format_prix == "colis":
            poids_colis = article.get("poids_colis_kg")
            if not poids_colis:
                raise HTTPException(
                    422,
                    "Article au colis sans poids de colis renseigné : "
                    "impossible de reconvertir le €/kg en prix de colis.",
                )
            nouveau_prix_achat = round(float(data.prix_kg) * float(poids_colis), 4)
        else:
            raise HTTPException(
                422,
                f"Format de prix '{format_prix}' non géré pour la saisie au €/kg.",
            )

        await db.execute(
            "UPDATE catalogue_fournisseur SET prix_achat_ht = ? WHERE id = ?",
            (nouveau_prix_achat, catalogue_fournisseur_id),
        )
        await db.commit()
        # Renvoie le €/kg effectif recalculé (sanity check côté front).
        prix_kg_effectif = _calc_prix_kg(
            format_prix, nouveau_prix_achat,
            article.get("poids_colis_kg"), article.get("famille"),
        )
        return {
            "ok": True, "id": catalogue_fournisseur_id,
            "prix_achat_ht": nouveau_prix_achat,
            "prix_kg": prix_kg_effectif,
        }


@router.get("/familles")
async def liste_familles():
    """Familles et sous-familles présentes au catalogue (navigation par rayon)."""
    async with get_db() as db:
        async with db.execute(
            """SELECT famille, sous_famille, COUNT(*) AS nb
               FROM catalogue_fournisseur
               WHERE actif = 1 AND famille IS NOT NULL AND famille <> ''
               GROUP BY famille, sous_famille
               ORDER BY famille, sous_famille""",
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]

    familles = {}
    for r in rows:
        fam = r["famille"]
        familles.setdefault(fam, {"famille": fam, "nb": 0, "sous_familles": []})
        familles[fam]["nb"] += r["nb"]
        if r["sous_famille"]:
            familles[fam]["sous_familles"].append({"nom": r["sous_famille"], "nb": r["nb"]})
    return {"familles": list(familles.values())}


# ---------------------------------------------------------------------------
# Tableau de bord MARGE  —  CA HT − (Achats HT + Stock Initial − Stock Final)
# ---------------------------------------------------------------------------

class TvaUpdate(BaseModel):
    tva_pct: float


async def _get_tva_pct(db):
    val = await get_parametre(db, BOUTIQUE_ID, CLE_TVA, str(TVA_DEFAUT_PCT))
    try:
        return float(val)
    except (TypeError, ValueError):
        return TVA_DEFAUT_PCT


@router.get("/marge/tva")
async def get_tva():
    async with get_db() as db:
        return {"tva_pct": await _get_tva_pct(db)}


@router.put("/marge/tva")
async def set_tva(data: TvaUpdate):
    if data.tva_pct < 0 or data.tva_pct > 100:
        raise HTTPException(422, "tva_pct doit être entre 0 et 100")
    async with get_db() as db:
        await set_parametre(db, BOUTIQUE_ID, CLE_TVA, str(data.tva_pct))
        return {"ok": True, "tva_pct": data.tva_pct}


# ── Achats HT réels saisis par PÉRIODE (vérité comptable, date de facture) ──

class AchatsReelsUpdate(BaseModel):
    date_debut: str                       # 'YYYY-MM-DD'
    date_fin: str                         # 'YYYY-MM-DD'
    montant_ht: Optional[float] = None    # None ou absent = effacer la saisie réelle
    commentaire: Optional[str] = None
    personnel_id: Optional[int] = None


def _valider_periode(debut, fin):
    try:
        d1 = date.fromisoformat(debut)
        d2 = date.fromisoformat(fin)
    except (ValueError, TypeError):
        raise HTTPException(422, "dates au format 'YYYY-MM-DD' requises")
    if d1 > d2:
        raise HTTPException(422, "date_debut doit précéder date_fin")


async def _get_achats_reels(db, debut, fin):
    """Montant achats réel saisi pour la période exacte [debut, fin], ou None."""
    async with db.execute(
        """SELECT montant_ht, commentaire FROM achats_reels_periode
           WHERE boutique_id = ? AND date_debut = ? AND date_fin = ?""",
        (BOUTIQUE_ID, debut, fin),
    ) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


@router.get("/marge/achats-reels")
async def get_achats_reels(
    date_debut: str = Query(..., description="YYYY-MM-DD"),
    date_fin: str = Query(..., description="YYYY-MM-DD"),
):
    _valider_periode(date_debut, date_fin)
    async with get_db() as db:
        saisie = await _get_achats_reels(db, date_debut, date_fin)
    return {"date_debut": date_debut, "date_fin": date_fin, "saisie": saisie}


@router.put("/marge/achats-reels")
async def set_achats_reels(data: AchatsReelsUpdate):
    """Saisit (ou efface) le montant d'achats HT réel d'une PÉRIODE (date de facture).

    Rattaché aux dates exactes analysées → éditable quelle que soit la période.
    montant_ht absent/None → on EFFACE la saisie (retour au calcul auto).
    """
    _valider_periode(data.date_debut, data.date_fin)
    if data.montant_ht is not None and data.montant_ht < 0:
        raise HTTPException(422, "montant_ht ne peut pas être négatif")
    async with get_db() as db:
        if data.montant_ht is None:
            await db.execute(
                """DELETE FROM achats_reels_periode
                   WHERE boutique_id = ? AND date_debut = ? AND date_fin = ?""",
                (BOUTIQUE_ID, data.date_debut, data.date_fin),
            )
            await db.commit()
            return {"ok": True, "date_debut": data.date_debut,
                    "date_fin": data.date_fin, "saisie": None}
        await db.execute(
            """INSERT INTO achats_reels_periode
                   (boutique_id, date_debut, date_fin, montant_ht, commentaire, personnel_id)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(boutique_id, date_debut, date_fin) DO UPDATE SET
                   montant_ht   = excluded.montant_ht,
                   commentaire  = excluded.commentaire,
                   personnel_id = excluded.personnel_id,
                   updated_at   = CURRENT_TIMESTAMP""",
            (BOUTIQUE_ID, data.date_debut, data.date_fin, data.montant_ht,
             data.commentaire, data.personnel_id),
        )
        await db.commit()
        return {"ok": True, "date_debut": data.date_debut, "date_fin": data.date_fin,
                "saisie": {"montant_ht": data.montant_ht, "commentaire": data.commentaire}}


# ── CA TTC : caler le total d'une période via une ligne d'ajustement datée ──

class CaAjustementBody(BaseModel):
    date_debut: str
    date_fin: str
    montant_ttc_cible: float              # le total TTC voulu pour la période
    personnel_id: Optional[int] = None


# Date dédiée pour la ligne d'ajustement (le dernier jour de la période).
LIBELLE_AJUSTEMENT = "Ajustement caisse/banque"


@router.put("/marge/ca-ajuster")
async def ajuster_ca_periode(body: CaAjustementBody):
    """Cale le CA TTC TOTAL d'une période sur une valeur cible (rapprochement banque).

    Non destructif : les saisies journalières restent intactes. L'écart (cible − somme
    actuelle hors ligne d'ajustement existante) est porté par UNE ligne d'ajustement datée
    au dernier jour de la période (commentaire dédié). Réappeler recalcule l'écart depuis la
    base réelle, donc c'est idempotent (pas d'empilement).
    """
    if body.date_debut > body.date_fin:
        raise HTTPException(422, "date_debut doit précéder date_fin")
    if body.montant_ttc_cible < 0:
        raise HTTPException(422, "le montant cible ne peut pas être négatif")

    async with get_db() as db:
        # Somme RÉELLE hors ligne d'ajustement (pour repartir d'une base propre).
        async with db.execute(
            """SELECT COALESCE(SUM(montant_ttc), 0) AS ttc
               FROM ca_journalier
               WHERE boutique_id = ? AND date_ca >= ? AND date_ca <= ?
                 AND COALESCE(commentaire, '') <> ?""",
            (BOUTIQUE_ID, body.date_debut, body.date_fin, LIBELLE_AJUSTEMENT),
        ) as cur:
            base = float((await cur.fetchone())["ttc"] or 0)

        ecart = round(body.montant_ttc_cible - base, 2)
        date_ajust = body.date_fin

        # Si la date d'ajustement porte une VRAIE saisie (pas l'ajustement), on refuse
        # d'écraser : on déplace l'ajustement sur cette même date en additionnant — mais
        # pour rester simple et lisible, on stocke l'ajustement comme une ligne dédiée
        # SEULEMENT si la date est libre ou ne contient que l'ancien ajustement.
        async with db.execute(
            """SELECT montant_ttc, commentaire FROM ca_journalier
               WHERE boutique_id = ? AND date_ca = ?""",
            (BOUTIQUE_ID, date_ajust),
        ) as cur:
            existant = await cur.fetchone()

        if existant and (existant["commentaire"] or "") != LIBELLE_AJUSTEMENT:
            # Le dernier jour a une vraie saisie → on porte l'ajustement la veille libre.
            # On cherche une date libre en remontant (max 7 jours) sinon on empile sur fin.
            d = date.fromisoformat(body.date_fin)
            d1 = date.fromisoformat(body.date_debut)
            date_ajust = None
            for _ in range(7):
                d = d - timedelta(days=1)
                if d < d1:
                    break
                async with db.execute(
                    "SELECT 1 FROM ca_journalier WHERE boutique_id = ? AND date_ca = ?",
                    (BOUTIQUE_ID, d.isoformat()),
                ) as cur:
                    if not await cur.fetchone():
                        date_ajust = d.isoformat()
                        break
            if date_ajust is None:
                raise HTTPException(
                    409,
                    "Aucun jour libre pour l'ajustement sur cette période. "
                    "Corrigez le CA jour par jour dans Pilotage.",
                )

        if abs(ecart) < 0.005:
            # Cible = base : on supprime toute ligne d'ajustement résiduelle.
            await db.execute(
                "DELETE FROM ca_journalier WHERE boutique_id = ? AND date_ca >= ? AND date_ca <= ? AND commentaire = ?",
                (BOUTIQUE_ID, body.date_debut, body.date_fin, LIBELLE_AJUSTEMENT),
            )
            await db.commit()
            return {"ok": True, "ecart": 0.0, "base_ttc": round(base, 2),
                    "cible_ttc": body.montant_ttc_cible, "ligne_ajustement": None}

        await db.execute(
            """INSERT INTO ca_journalier
                   (boutique_id, date_ca, montant_ttc, nb_tickets, commentaire, personnel_id)
               VALUES (?, ?, ?, NULL, ?, ?)
               ON CONFLICT(boutique_id, date_ca) DO UPDATE SET
                   montant_ttc  = excluded.montant_ttc,
                   commentaire  = excluded.commentaire,
                   personnel_id = excluded.personnel_id,
                   updated_at   = CURRENT_TIMESTAMP""",
            (BOUTIQUE_ID, date_ajust, ecart, LIBELLE_AJUSTEMENT, body.personnel_id),
        )
        await db.commit()
        return {"ok": True, "ecart": ecart, "base_ttc": round(base, 2),
                "cible_ttc": body.montant_ttc_cible,
                "ligne_ajustement": {"date_ca": date_ajust, "montant_ttc": ecart}}


async def _ca_periode_ht(db, debut, fin, tva_pct):
    """CA HT de la période = somme TTC ca_journalier [debut, fin] / (1 + tva/100)."""
    async with db.execute(
        """SELECT COALESCE(SUM(montant_ttc), 0) AS ttc, COUNT(*) AS nb_jours
           FROM ca_journalier
           WHERE boutique_id = ? AND date_ca >= ? AND date_ca <= ?""",
        (BOUTIQUE_ID, debut, fin),
    ) as cur:
        row = await cur.fetchone()
    ttc = float(row["ttc"] or 0)
    ht = round(ttc / (1 + tva_pct / 100), 2) if tva_pct >= 0 else ttc
    return {"ttc": round(ttc, 2), "ht": ht, "nb_jours": row["nb_jours"]}


async def _achats_periode_ht(db, debut, fin):
    """Achats HT = réceptions CLÔTURÉES sur [debut, fin], valorisées poids × €/kg catalogue.

    Même logique que l'inventaire : on ne compte que ce qu'on sait valoriser honnêtement
    (poids ET prix catalogue présents). nb_non_valorisees signale les lignes ignorées.
    """
    async with db.execute(
        """SELECT rl.poids_kg,
                  c.format_prix, c.prix_achat_ht, c.poids_colis_kg, c.famille
           FROM reception_lignes rl
           JOIN receptions r ON r.id = rl.reception_id
           LEFT JOIN catalogue_fournisseur c ON c.id = rl.catalogue_fournisseur_id
           WHERE r.statut = 'cloturee'
             AND r.date_reception >= ? AND r.date_reception <= ?""",
        (debut, fin),
    ) as cur:
        lignes = [dict(r) for r in await cur.fetchall()]

    total = 0.0
    nb = 0
    nb_non_valo = 0
    for l in lignes:
        nb += 1
        prix_kg = _calc_prix_kg(l.get("format_prix"), l.get("prix_achat_ht"),
                                l.get("poids_colis_kg"), l.get("famille"))
        poids = l.get("poids_kg")
        if prix_kg is not None and poids is not None:
            total += float(poids) * prix_kg
        else:
            nb_non_valo += 1
    return {"ht": round(total, 2), "nb_lignes": nb, "nb_non_valorisees": nb_non_valo}


async def _inventaire_proche(db, cible, sens):
    """Inventaire CLÔTURÉ le plus proche d'une date.

    sens='avant' : dernier clôturé dont date_inventaire <= cible (Stock Initial).
    sens='apres' : dernier clôturé dont date_inventaire <= cible également (Stock Final
    = la photo la plus récente jusqu'à la fin de période incluse).
    Retourne le dict session ou None.
    """
    async with db.execute(
        """SELECT id, date_inventaire, libelle, valeur_totale_ht
           FROM inventaires
           WHERE boutique_id = ? AND statut = 'cloture' AND date_inventaire <= ?
           ORDER BY date_inventaire DESC, id DESC
           LIMIT 1""",
        (BOUTIQUE_ID, cible),
    ) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


@router.get("/marge")
async def tableau_marge(
    date_debut: str = Query(..., description="YYYY-MM-DD (inclus)"),
    date_fin: str = Query(..., description="YYYY-MM-DD (inclus)"),
    stock_initial_id: Optional[int] = Query(None, description="override inventaire Stock Initial"),
    stock_final_id: Optional[int] = Query(None, description="override inventaire Stock Final"),
    stock_initial_zero: bool = Query(False, description="démarrage d'activité : stock initial = 0 € fiable"),
):
    """Calcule la marge brute de la période.

        Marge = CA HT − CMV
        CMV   = Achats HT période + Stock Initial − Stock Final

    Stock Initial/Final : par défaut, l'inventaire clôturé le plus proche AVANT le début
    (≤ date_debut) et le plus proche jusqu'à la fin (≤ date_fin). L'utilisateur peut forcer
    une autre photo via stock_initial_id / stock_final_id. La liste de tous les inventaires
    clôturés est renvoyée pour permettre la correction côté UI.

    stock_initial_zero : cas du DÉMARRAGE d'activité (stock réellement nul, pas de photo à
    faire). Quand activé ET qu'aucun inventaire initial n'est trouvé/forcé, le Stock Initial
    vaut 0 € et compte comme une VRAIE valeur → la marge reste fiable.
    """
    if date_debut > date_fin:
        raise HTTPException(422, "date_debut doit précéder date_fin")

    async with get_db() as db:
        tva_pct = await _get_tva_pct(db)
        ca = await _ca_periode_ht(db, date_debut, date_fin, tva_pct)
        achats_calcule = await _achats_periode_ht(db, date_debut, date_fin)

        # Achats RÉELS saisis : rattachés à la PÉRIODE exacte analysée → éditables quelle
        # que soit la période (jamais bloqué). Quand un montant réel existe pour ces dates,
        # il PRIME mais le calcul (réceptions valorisées) reste en référence.
        achats_reel_saisie = await _get_achats_reels(db, date_debut, date_fin)
        achats = dict(achats_calcule)
        achats["ht_calcule"] = achats_calcule["ht"]
        achats["saisie_possible"] = True
        if achats_reel_saisie is not None:
            achats["ht_reel"] = round(float(achats_reel_saisie["montant_ht"]), 2)
            achats["source"] = "reel"
            achats["ht"] = achats["ht_reel"]
            achats["ecart_reel_calcule"] = round(achats["ht_reel"] - achats_calcule["ht"], 2)
        else:
            achats["ht_reel"] = None
            achats["source"] = "calcule"
            achats["ecart_reel_calcule"] = None

        # Stock Initial : photo ≤ veille du début (l'inventaire de DÉBUT de période).
        # On cible la veille pour capter la photo prise avant la période, mais on tolère
        # une photo prise le jour même du début (cas fréquent : inventaire le 1er du mois).
        async def _charger_override(inv_id):
            async with db.execute(
                """SELECT id, date_inventaire, libelle, valeur_totale_ht
                   FROM inventaires WHERE id = ? AND boutique_id = ? AND statut = 'cloture'""",
                (inv_id, BOUTIQUE_ID),
            ) as cur:
                row = await cur.fetchone()
            return dict(row) if row else None

        if stock_initial_id:
            inv_init = await _charger_override(stock_initial_id)
        else:
            inv_init = await _inventaire_proche(db, date_debut, "avant")

        if stock_final_id:
            inv_final = await _charger_override(stock_final_id)
        else:
            inv_final = await _inventaire_proche(db, date_fin, "apres")

        # Liste de tous les inventaires clôturés (pour le sélecteur de correction côté UI).
        async with db.execute(
            """SELECT id, date_inventaire, libelle, valeur_totale_ht
               FROM inventaires
               WHERE boutique_id = ? AND statut = 'cloture'
               ORDER BY date_inventaire DESC, id DESC""",
            (BOUTIQUE_ID,),
        ) as cur:
            inventaires = [dict(r) for r in await cur.fetchall()]

    si = float(inv_init["valeur_totale_ht"]) if inv_init else None
    sf = float(inv_final["valeur_totale_ht"]) if inv_final else None

    # Démarrage d'activité : stock initial réellement nul (pas une photo manquante).
    # On ne l'applique que si aucune photo initiale n'a été trouvée/forcée (une vraie
    # photo prime toujours sur la convention « zéro »).
    si_zero_applique = bool(stock_initial_zero and inv_init is None)
    if si_zero_applique:
        si = 0.0

    # CMV = Achats + Stock Initial − Stock Final. Les stocks absents comptent 0 mais on
    # le signale (marge_fiable=False) pour ne pas laisser croire à un calcul complet.
    variation_stock = (si or 0) - (sf or 0)   # Stock Initial − Stock Final
    cmv = round(achats["ht"] + variation_stock, 2)
    marge = round(ca["ht"] - cmv, 2)
    marge_pct = round(100 * marge / ca["ht"], 1) if ca["ht"] else None
    # Fiable si Stock Initial connu (vraie photo OU zéro démarrage assumé) ET Stock Final connu.
    marge_fiable = (si is not None) and (sf is not None)

    return {
        "periode": {"debut": date_debut, "fin": date_fin},
        "tva_pct": tva_pct,
        "ca": ca,                       # {ttc, ht, nb_jours}
        "achats": achats,               # {ht, nb_lignes, nb_non_valorisees}
        "stock_initial": inv_init,      # session ou None
        "stock_final": inv_final,       # session ou None
        "stock_initial_zero": si_zero_applique,  # True = SI=0 démarrage d'activité assumé
        "variation_stock": round(variation_stock, 2),
        "cmv": cmv,
        "marge_brute_ht": marge,
        "marge_pct": marge_pct,
        "marge_fiable": marge_fiable,
        "inventaires_clotures": inventaires,
    }

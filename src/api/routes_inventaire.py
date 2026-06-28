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

GET    /api/inventaire/catalogue-recherche?q=      → autocomplete article + €/kg pré-calculé
GET    /api/inventaire/familles                    → familles/sous-familles (navigation rayon)
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.database import get_db
from src.api.routes_achats import _calc_prix_kg

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

@router.get("/catalogue-recherche")
async def recherche_catalogue(
    q: Optional[str] = Query(None),
    famille: Optional[str] = Query(None),
    sous_famille: Optional[str] = Query(None),
    limit: int = Query(40, ge=1, le=200),
):
    """Recherche d'articles catalogue avec €/kg pré-calculé (autocomplete + rayon).

    Filtres combinables : `q` (texte sur designation/code), `famille`, `sous_famille`.
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

    where = " AND ".join(clauses)
    params.append(limit)
    async with get_db() as db:
        async with db.execute(
            f"""SELECT c.id, c.designation, c.code_article, c.famille, c.sous_famille,
                       c.format_prix, c.prix_achat_ht, c.poids_colis_kg,
                       c.qte_par_colis, c.poids_unitaire_kg, c.unites_autorisees,
                       f.nom AS fournisseur_nom
                FROM catalogue_fournisseur c
                LEFT JOIN fournisseurs f ON f.id = c.fournisseur_id
                WHERE {where}
                ORDER BY c.designation
                LIMIT ?""",
            params,
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]

        for r in rows:
            r["prix_kg"] = _calc_prix_kg(
                r.get("format_prix"), r.get("prix_achat_ht"),
                r.get("poids_colis_kg"), r.get("famille"),
            )
        return {"articles": rows}


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

"""
routes_cuisson.py — Module Cuisson (HACCP)

Enregistrement des cuissons avec contrôle température de fin de cuisson.
Cible réglementaire : ≥ 75 °C à cœur.

GET  /api/cuisson/enregistrements?type=rotissoire&limit=50
POST /api/cuisson/enregistrements
GET  /api/cuisson/a-traiter
GET  /api/cuisson/produits-vente-suggeres
"""

import logging
from datetime import date as _date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.database import get_db, get_stock_unifie, DLC_JOURS_TRANSFORMATION

BOUTIQUE_ID = 1  # mono-boutique Phase 2

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cuisson", tags=["cuisson"])

TEMPERATURE_CIBLE = 75.0

# Exception "viande rouge en pièce entière" (28/08/2026) — cf. affiche interne
# "Règle de cuisson simplifiée" : Bœuf/Agneau, pièces entières, non hachées,
# non injectées, peuvent être cuits en dessous de 75 °C selon le degré visé.
# Plus exigeant que le GBPH Bouchers Charcutiers Traiteurs (70 °C / 10 min).
DEGRES_CUISSON = {
    "saignant": 55.0,
    "a_point":  63.0,
    "bien_cuit": 75.0,
    "generale": TEMPERATURE_CIBLE,
}


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class CuissonCreate(BaseModel):
    type_cuisson:       str   = Field(..., description="'rotissoire' pour l'instant")
    date_cuisson:       str   = Field(..., description="YYYY-MM-DD")
    personnel_id:       int
    # v7.4 — trois espaces d'identifiants possibles, au moins un requis (cf. validation
    # dans creer_cuisson). `produit_id` est l'ancien modèle interne, conservé pour
    # l'historique ; le stock réel s'identifie par le catalogue d'ACHATS, et ce que l'on
    # produit par le catalogue de VENTE.
    produit_id:               Optional[int] = None
    catalogue_fournisseur_id: Optional[int] = None
    catalogue_vente_id:       Optional[int] = None
    reception_ligne_id: Optional[int]   = None     # source = lot de réception (brut)
    fabrication_id:     Optional[int]   = None     # source = lot de fabrication (fini cru)
    quantite:           Optional[float] = None
    unite:              Optional[str]   = "kg"
    heure_debut:        str   = Field(..., description="HH:MM")
    heure_fin:          str   = Field(..., description="HH:MM")
    temperature_sortie: float
    # v7.5 — degré de cuisson choisi par l'opérateur pour l'exception viande rouge
    # (cf. DEGRES_CUISSON). None ou absent = règle générale (75 °C), comme avant.
    degre_cuisson:       Optional[str]   = None
    action_corrective:  Optional[str]   = None


# ---------------------------------------------------------------------------
# POST /api/cuisson/enregistrements
# ---------------------------------------------------------------------------

@router.post("/enregistrements", status_code=201)
async def creer_cuisson(body: CuissonCreate):
    degre = body.degre_cuisson or "generale"
    if degre not in DEGRES_CUISSON:
        raise HTTPException(
            status_code=422,
            detail=f"degre_cuisson invalide : {degre!r} (attendu : {', '.join(DEGRES_CUISSON)}).",
        )
    temperature_cible = DEGRES_CUISSON[degre]

    conforme = 1 if body.temperature_sortie >= temperature_cible else 0
    if not conforme and not (body.action_corrective and body.action_corrective.strip()):
        raise HTTPException(
            status_code=422,
            detail=f"Action corrective obligatoire si température < {temperature_cible:.0f} °C",
        )

    # Une cuisson ne peut pas avoir deux sources amont en même temps
    if body.reception_ligne_id and body.fabrication_id:
        raise HTTPException(
            status_code=422,
            detail="Une cuisson ne peut pas être liée simultanément à une réception et à une fabrication.",
        )

    # Le produit cuit doit être identifiable dans au moins un des trois référentiels,
    # sinon la cuisson serait intraçable (exigence HACCP).
    if not (body.produit_id or body.catalogue_fournisseur_id or body.catalogue_vente_id):
        raise HTTPException(
            status_code=422,
            detail="Produit non identifié : renseignez produit_id, "
                   "catalogue_fournisseur_id ou catalogue_vente_id.",
        )

    # DLC J+3 calculée côté serveur (règle HACCP transformation)
    try:
        dlc_calculee = (datetime.strptime(body.date_cuisson, "%Y-%m-%d").date()
                        + timedelta(days=DLC_JOURS_TRANSFORMATION))
    except ValueError:
        raise HTTPException(status_code=422, detail="date_cuisson invalide (YYYY-MM-DD attendu).")

    async with get_db() as db:
        # Règle métier absolue : la DLC ne peut pas dépasser la DLC du lot d'origine
        # (réception OU fabrication, selon la source amont sélectionnée).
        dlc_finale = dlc_calculee
        dlc_origine = None
        dlc_ajustee = False

        if body.reception_ligne_id:
            cur_rl = await db.execute(
                "SELECT dlc FROM reception_lignes WHERE id = ?",
                (body.reception_ligne_id,),
            )
            rl = await cur_rl.fetchone()
            if rl and rl["dlc"]:
                dlc_origine = datetime.strptime(rl["dlc"], "%Y-%m-%d").date()
        elif body.fabrication_id:
            cur_fab = await db.execute(
                "SELECT dlc_finale FROM fabrications WHERE id = ?",
                (body.fabrication_id,),
            )
            fab = await cur_fab.fetchone()
            if fab and fab["dlc_finale"]:
                dlc_origine = datetime.strptime(fab["dlc_finale"], "%Y-%m-%d").date()

        # Produit marqué "suivi cuisson auto" (ex. Lasagnes, Gratin dauphinois, Parmentier
        # canard) : reçu déjà fini, la cuisson n'est qu'un RÉCHAUFFAGE avant vente, pas une
        # transformation. La DLC fournisseur reste seule valable — on ne lui ajoute jamais
        # J+3 (28/08/2026 : la règle J+3-cappée écourtait à tort la DLC d'origine dès qu'elle
        # dépassait 3 jours après la date de cuisson).
        reste_produit_fini = False
        if dlc_origine and body.catalogue_vente_id:
            cur_sca = await db.execute(
                "SELECT suivi_cuisson_auto FROM catalogue_vente WHERE id = ?",
                (body.catalogue_vente_id,),
            )
            cv = await cur_sca.fetchone()
            reste_produit_fini = bool(cv and cv["suivi_cuisson_auto"])

        if reste_produit_fini:
            dlc_finale = dlc_origine
            dlc_ajustee = dlc_calculee != dlc_origine
        elif dlc_origine and dlc_calculee > dlc_origine:
            dlc_finale = dlc_origine
            dlc_ajustee = True

        dlc_finale_iso = dlc_finale.isoformat()

        cur = await db.execute(
            """
            INSERT INTO cuissons (
                type_cuisson, date_cuisson, personnel_id, produit_id,
                catalogue_fournisseur_id, catalogue_vente_id,
                reception_ligne_id, fabrication_id, quantite, unite,
                heure_debut, heure_fin,
                temperature_sortie, temperature_cible, degre_cuisson,
                conforme, action_corrective, dlc_finale
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                body.type_cuisson.lower(),
                body.date_cuisson,
                body.personnel_id,
                body.produit_id,
                body.catalogue_fournisseur_id,
                body.catalogue_vente_id,
                body.reception_ligne_id,
                body.fabrication_id,
                body.quantite,
                body.unite or "kg",
                body.heure_debut,
                body.heure_fin,
                body.temperature_sortie,
                temperature_cible,
                degre,
                conforme,
                (body.action_corrective or "").strip() or None,
                dlc_finale_iso,
            ),
        )
        await db.commit()
        nouveau_id = cur.lastrowid

    logger.info(
        "Cuisson %s #%d — produit=%s/%s/%s degré=%s T°cible=%.1f T°=%.1f conforme=%s",
        body.type_cuisson, nouveau_id,
        body.produit_id, body.catalogue_fournisseur_id, body.catalogue_vente_id,
        degre, temperature_cible, body.temperature_sortie, bool(conforme),
    )
    return {
        "ok": True,
        "id": nouveau_id,
        "conforme": bool(conforme),
        "temperature_cible": temperature_cible,
        "degre_cuisson": degre,
        "dlc_ajustee": dlc_ajustee,
        "dlc_origine": dlc_origine.isoformat() if dlc_origine else None,
    }


# ---------------------------------------------------------------------------
# GET /api/cuisson/enregistrements
# ---------------------------------------------------------------------------

@router.get("/enregistrements")
async def lister_cuissons(
    type:       str = Query("rotissoire"),
    date_debut: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_fin:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit:      int = Query(50, ge=1, le=500),
):
    """Liste des cuissons d'un type donné, du plus récent au plus ancien."""
    clauses = ["c.type_cuisson = ?"]
    params: list = [type.lower()]
    if date_debut:
        clauses.append("c.date_cuisson >= ?")
        params.append(date_debut)
    if date_fin:
        clauses.append("c.date_cuisson <= ?")
        params.append(date_fin)

    where_sql = " AND ".join(clauses)
    params.append(limit)

    async with get_db() as db:
        cur = await db.execute(
            f"""
            SELECT c.*,
                   COALESCE(p.nom, cv.nom, cf.designation) AS produit_nom,
                   p.espece    AS espece,
                   TRIM(pers.prenom || ' ' || COALESCE(pers.nom, '')) AS personnel_prenom,
                   COALESCE(rl.numero_lot, fab.lot_interne) AS numero_lot,
                   rl.origine  AS origine,
                   rl.reception_id AS reception_id
            FROM   cuissons c
            LEFT   JOIN produits        p    ON p.id    = c.produit_id
            LEFT   JOIN catalogue_vente cv   ON cv.id   = c.catalogue_vente_id
            LEFT   JOIN catalogue_fournisseur cf ON cf.id = c.catalogue_fournisseur_id
            LEFT   JOIN personnel       pers ON pers.id = c.personnel_id
            LEFT   JOIN reception_lignes rl  ON rl.id   = c.reception_ligne_id
            LEFT   JOIN fabrications    fab  ON fab.id  = c.fabrication_id
            WHERE  {where_sql}
            ORDER BY c.date_cuisson DESC, c.id DESC
            LIMIT ?
            """,
            tuple(params),
        )
        rows = await cur.fetchall()

    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# GET /api/cuisson/produits-disponibles
# Source unique du stock disponible à cuire — alimentée par get_stock_unifie()
# ---------------------------------------------------------------------------

@router.get("/produits-disponibles")
async def produits_disponibles_pour_cuisson():
    """
    Produits bruts ayant au moins un lot de réception disponible (DLC future,
    non sortis via dlc_devenir). Une ligne par produit, avec le lot FIFO
    (DLC la plus courte, puis date de réception la plus ancienne).

    Si l'inventaire est vide, cette liste l'est aussi : on ne peut pas cuire
    ce qu'on n'a pas reçu.
    """
    async with get_db() as db:
        stock = await get_stock_unifie(
            db, BOUTIQUE_ID,
            type_produit="tous",
            sources=["reception_ligne", "fabrication"],
        )

    # get_stock_unifie est déjà trié par DLC croissante, date_origine croissante.
    # On garde le premier lot rencontré pour chaque produit (= FIFO).
    #
    # Clé d'identité : depuis la v6, `produit_id` est NULL pour 99 % des lots (le stock
    # vient du catalogue d'achats). S'en servir seul faisait s'écraser TOUS ces lots dans
    # une unique entrée `None` — un seul produit remontait au lieu de plusieurs centaines.
    # On identifie donc par (espace d'identifiants, valeur).
    par_produit: dict[tuple[str, int], dict] = {}
    for lot in stock:
        pid = lot.get("produit_id")
        cfid = lot.get("catalogue_fournisseur_id")
        cvid = lot.get("catalogue_vente_id")
        if pid is not None:
            cle = ("produit", pid)
        elif cvid is not None:
            cle = ("vente", cvid)
        elif cfid is not None:
            cle = ("achat", cfid)
        else:
            continue        # lot non identifiable : on ne peut pas le proposer à la cuisson
        if cle in par_produit:
            continue
        src_type = lot["source_type"]
        src_id   = lot["source_id"]
        par_produit[cle] = {
            # `id` reste l'identifiant historique (produits) quand il existe, sinon None :
            # le front s'appuie désormais sur cle_type/cle_id pour désigner un produit.
            "id":                 pid,
            "cle_type":           cle[0],
            "cle_id":             cle[1],
            "catalogue_fournisseur_id": cfid,
            "catalogue_vente_id":       cvid,
            "nom":                lot["produit_nom"],
            "espece":             lot.get("espece"),
            "categorie":          lot.get("categorie"),
            "type_produit":       lot.get("type_produit"),
            "en_stock":           True,
            "numero_lot":         lot.get("numero_lot"),
            "origine":            lot.get("origine"),
            "dlc":                lot.get("dlc"),
            "source_type":        src_type,
            "source_id":          src_id,
            "reception_ligne_id": src_id if src_type == "reception_ligne" else None,
            "fabrication_id":     src_id if src_type == "fabrication"     else None,
        }

    return sorted(par_produit.values(), key=lambda p: (p["nom"] or "").lower())


# ---------------------------------------------------------------------------
# GET /api/cuisson/produits/{produit_id}/receptions
# Historique des réceptions pour un produit donné
# ---------------------------------------------------------------------------

@router.get("/produits/{produit_id}/receptions")
async def historique_receptions_produit(produit_id: int, limit: int = Query(20, ge=1, le=100)):
    """Lots d'un produit identifié par l'ancien référentiel `produits` (compatibilité).

    Conservé pour ne pas casser les appels existants ; le wizard utilise désormais
    GET /api/cuisson/lots, qui accepte aussi les identifiants catalogue.
    """
    return await _lots_disponibles(produit_id=produit_id, limit=limit)


@router.get("/lots")
async def lots_disponibles_pour_cuisson(
    produit_id:               Optional[int] = Query(None),
    catalogue_fournisseur_id: Optional[int] = Query(None),
    catalogue_vente_id:       Optional[int] = Query(None),
    limit:                    int = Query(20, ge=1, le=100),
):
    """Lots disponibles à cuire pour un produit, quel que soit son référentiel.

    Depuis la v6, un produit peut être identifié par `produits` (historique),
    par le catalogue d'ACHATS (le stock réel) ou par le catalogue de VENTE
    (les fabrications). Exactement un de ces identifiants est attendu.
    """
    fournis = [x for x in (produit_id, catalogue_fournisseur_id, catalogue_vente_id) if x]
    if len(fournis) != 1:
        raise HTTPException(
            status_code=422,
            detail="Fournissez exactement un identifiant : produit_id, "
                   "catalogue_fournisseur_id ou catalogue_vente_id.",
        )
    return await _lots_disponibles(
        produit_id=produit_id,
        catalogue_fournisseur_id=catalogue_fournisseur_id,
        catalogue_vente_id=catalogue_vente_id,
        limit=limit,
    )


async def _lots_disponibles(
    produit_id:               Optional[int] = None,
    catalogue_fournisseur_id: Optional[int] = None,
    catalogue_vente_id:       Optional[int] = None,
    limit:                    int = 20,
):
    """
    Lots disponibles pour cuisson : DLC non dépassée ET non traitée via le calendrier DLC.

    Inclut deux sources :
      • réceptions (produits bruts livrés)         — source_type='reception_ligne'
      • fabrications (produits finis crus)         — source_type='fabrication'

    Chaque lot expose `source_type` + `source_id` (à privilégier) ainsi que
    `reception_ligne_id` (legacy, conservé pour l'affichage).
    """
    # Le filtre porte sur la colonne correspondant au référentiel demandé.
    # Un identifiant de vente ne désigne aucune ligne de réception : dans ce cas
    # seules les fabrications remontent (clause volontairement impossible).
    if catalogue_fournisseur_id:
        filtre_reception, param_reception = "rl.catalogue_fournisseur_id = ?", catalogue_fournisseur_id
    elif produit_id:
        filtre_reception, param_reception = "rl.produit_id = ?", produit_id
    else:
        filtre_reception, param_reception = "1 = 0", None

    # Les fabrications sont rattachées au catalogue de VENTE via la recette.
    param_fabrication = catalogue_vente_id or produit_id

    async with get_db() as db:
        # ── Lots issus de réception ───────────────────────────────────────────
        cur = await db.execute(
            """
            SELECT 'reception_ligne'   AS source_type,
                   rl.id                AS source_id,
                   rl.id                AS reception_ligne_id,
                   rl.reception_id      AS reception_id,
                   rl.numero_lot,
                   rl.origine           AS origine,
                   COALESCE(rl.dlc, rl.dluo) AS dlc,
                   rl.poids_kg,
                   rl.temperature_reception,
                   r.date_reception,
                   r.heure_reception,
                   f.nom                AS fournisseur_nom
            FROM   reception_lignes rl
            JOIN   receptions  r ON r.id = rl.reception_id
            LEFT JOIN fournisseurs f ON f.id = rl.fournisseur_id
            WHERE  """ + filtre_reception + """
              AND r.statut = 'cloturee'
              AND rl.conforme = 1
              AND r.livraison_refusee = 0
              AND (COALESCE(rl.dlc, rl.dluo) IS NULL
                   OR COALESCE(rl.dlc, rl.dluo) >= DATE('now'))
              AND NOT EXISTS (
                  SELECT 1 FROM dlc_devenir d
                  WHERE d.source_type = 'reception_ligne' AND d.source_id = rl.id
              )
            ORDER BY r.date_reception DESC, r.id DESC
            LIMIT ?
            """,
            ((param_reception, limit) if param_reception is not None else (limit,)),
        )
        receptions = [dict(r) for r in await cur.fetchall()]

        # ── Lots issus de fabrication ─────────────────────────────────────────
        # Depuis la migration v6.0, une recette pointe son produit fini vers le
        # catalogue de VENTE (`recettes.catalogue_vente_id`) et non plus vers
        # `produits` (`produit_fini_id`, colonne supprimée). Le `produit_id` reçu
        # ici est donc à interpréter comme un `catalogue_vente.id` pour les lots
        # de fabrication — c'est déjà la convention de get_stock_unifie(), qui
        # expose `cv.id AS produit_id` pour cette source.
        cur = await db.execute(
            """
            SELECT 'fabrication'        AS source_type,
                   fab.id               AS source_id,
                   NULL                 AS reception_ligne_id,
                   NULL                 AS reception_id,
                   fab.lot_interne      AS numero_lot,
                   fab.dlc_finale       AS dlc,
                   fab.poids_fabrique   AS poids_kg,
                   NULL                 AS temperature_reception,
                   fab.date             AS date_reception,
                   NULL                 AS heure_reception,
                   'Fabrication maison' AS fournisseur_nom
            FROM   fabrications fab
            JOIN   recettes rec ON rec.id = fab.recette_id
            WHERE  rec.catalogue_vente_id = ?
              AND  fab.dlc_finale IS NOT NULL
              AND  fab.dlc_finale >= DATE('now')
              AND NOT EXISTS (
                  SELECT 1 FROM dlc_devenir d
                  WHERE d.source_type = 'fabrication' AND d.source_id = fab.id
              )
            ORDER BY fab.date DESC, fab.id DESC
            LIMIT ?
            """,
            (param_fabrication, limit),
        )
        fabrications = [dict(r) for r in await cur.fetchall()]

    return receptions + fabrications


# ---------------------------------------------------------------------------
# GET /api/cuisson/a-traiter
# Lots de produits "suivi cuisson auto" (reçus déjà préparés) pas encore cuits.
# Alimente la tuile Hub "🍽 À CUIRE" — voir routes_hub.py.
# ---------------------------------------------------------------------------

@router.get("/a-traiter")
async def lots_a_traiter():
    """
    Réceptions closes, conformes, non refusées, d'un produit marqué
    `suivi_cuisson_auto = 1` (ex. Lasagne, Gratin dauphinois, Parmentier de
    canard — reçus tout prêts, sans étape de fabrication), et n'ayant pas
    encore de cuisson liée. Triés par DLC croissante (le plus urgent d'abord).
    """
    async with get_db() as db:
        cur = await db.execute(
            """
            SELECT rl.id              AS reception_ligne_id,
                   rl.produit_id,
                   p.nom              AS produit_nom,
                   rl.numero_lot,
                   COALESCE(rl.dlc, rl.dluo) AS dlc,
                   r.date_reception,
                   f.nom              AS fournisseur_nom
            FROM   reception_lignes rl
            JOIN   receptions r ON r.id = rl.reception_id
            JOIN   produits   p ON p.id = rl.produit_id
            LEFT JOIN fournisseurs f ON f.id = rl.fournisseur_id
            WHERE  p.suivi_cuisson_auto = 1
              AND  r.statut = 'cloturee'
              AND  rl.conforme = 1
              AND  r.livraison_refusee = 0
              AND  NOT EXISTS (SELECT 1 FROM cuissons c WHERE c.reception_ligne_id = rl.id)
            ORDER BY CASE WHEN COALESCE(rl.dlc, rl.dluo) IS NOT NULL THEN 0 ELSE 1 END,
                     COALESCE(rl.dlc, rl.dluo) ASC,
                     r.date_reception ASC
            """
        )
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# GET /api/cuisson/produits-vente-suggeres
# Alimente la modale "ça devient quel produit ?" à l'étape 2 du wizard : on ne
# sait pas encore, pour un article de matière brute reçu, quel produit du
# catalogue de VENTE en résultera une fois cuit (aucun champ ne le distingue
# côté catalogue achats — cf. décision du 28/08/2026, volontairement pas de
# nouveau champ pour rester simple).
# ---------------------------------------------------------------------------

@router.get("/produits-vente-suggeres")
async def produits_vente_suggeres(catalogue_fournisseur_id: int = Query(...)):
    """
    Suggestions de produit fini pour un article du catalogue d'achats :
      1. `dernier_choix` — le catalogue_vente_id utilisé la dernière fois qu'une
         cuisson a été enregistrée pour ce même article (mémorisation simple,
         sans nouvelle table : on relit l'historique `cuissons`).
      2. `groupe` — les produits de vente actifs du groupe comparatif auquel
         appartient l'article (ex. groupe "Boeuf" → Rosbeef cuit, Entrecote…),
         via comparatif_groupe_ligne → comparatif_groupe_vente.
    Le front complète toujours avec une recherche libre sur tout le catalogue
    vente : ces suggestions n'ont rien d'exhaustif ni d'obligatoire.
    """
    async with get_db() as db:
        cur_dernier = await db.execute(
            """
            SELECT c.catalogue_vente_id, cv.nom
            FROM   cuissons c
            JOIN   catalogue_vente cv ON cv.id = c.catalogue_vente_id
            WHERE  c.catalogue_fournisseur_id = ?
              AND  c.catalogue_vente_id IS NOT NULL
            ORDER BY c.id DESC
            LIMIT 1
            """,
            (catalogue_fournisseur_id,),
        )
        dernier = await cur_dernier.fetchone()

        cur_groupe = await db.execute(
            """
            SELECT DISTINCT cv.id, cv.nom
            FROM   comparatif_groupe_ligne gl
            JOIN   comparatif_groupe_vente gv ON gv.groupe_id = gl.groupe_id
            JOIN   catalogue_vente cv         ON cv.id        = gv.catalogue_vente_id
            WHERE  gl.catalogue_fournisseur_id = ?
              AND  cv.actif = 1
            ORDER BY cv.nom COLLATE NOCASE
            """,
            (catalogue_fournisseur_id,),
        )
        groupe = await cur_groupe.fetchall()

    return {
        "dernier_choix": (
            {"id": dernier["catalogue_vente_id"], "nom": dernier["nom"]}
            if dernier else None
        ),
        "groupe": [{"id": r["id"], "nom": r["nom"]} for r in groupe],
    }


# ---------------------------------------------------------------------------
# GET /api/cuisson/produits-vente-recherche
# Recherche libre dans le catalogue vente pour la même modale, quand les
# suggestions ci-dessus ne contiennent pas le bon produit. Pas d'auth admin :
# utilisé depuis le wizard cuisson en atelier (opérateur, pas un gestionnaire).
# ---------------------------------------------------------------------------

@router.get("/produits-vente-recherche")
async def produits_vente_recherche(q: str = Query("", description="Terme de recherche (nom)")):
    terme = (q or "").strip()
    async with get_db() as db:
        sql = """
            SELECT id, nom
            FROM   catalogue_vente
            WHERE  boutique_id = 1 AND actif = 1
        """
        params: list = []
        if terme:
            sql += " AND nom LIKE ?"
            params.append(f"%{terme}%")
        sql += " ORDER BY nom COLLATE NOCASE LIMIT 30"
        cur = await db.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]

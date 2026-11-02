"""
routes_refroidissement.py — Module Refroidissement (HACCP)

Refroidissement rapide après cuisson : passer de chaud à ≤ +10 °C à cœur
en ≤ 2 heures. Si le couple temps/température n'est pas respecté
(durée > 2 h ET T° > 10 °C), les produits doivent être JETÉS.

GET  /api/refroidissement/produits
GET  /api/refroidissement/enregistrements?limit=50
POST /api/refroidissement/enregistrements
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.database import get_db, get_stock_unifie, create_dlc_devenir, DLC_JOURS_TRANSFORMATION

BOUTIQUE_ID = 1  # mono-boutique Phase 2

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/refroidissement", tags=["refroidissement"])

TEMPERATURE_CIBLE        = 10.0   # °C max à cœur après refroidissement
TEMPERATURE_MIN_CUISSON  = 75.0   # °C min à cœur en sortie de cuisson
DUREE_MAX_MINUTES        = 120    # 2 h


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TOLERANCE_FUTUR_MINUTES = 5   # décalage d'horloge tablette/serveur toléré


def maintenant_local() -> datetime:
    """Heure de la boutique. Le VPS tourne en UTC : comparer une heure saisie à
    datetime.now() refuserait à tort une saisie faite il y a moins d'une heure."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def minutes_hhmm(heure: str, libelle: str = "heure") -> int:
    """'HH:MM' → minutes depuis minuit (422 si le format est faux)."""
    try:
        h, m = map(int, heure.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except Exception:
        raise HTTPException(status_code=422, detail=f"{libelle} invalide (HH:MM attendu).")
    return h * 60 + m


def verifier_pas_dans_le_futur(date_iso: str, heure: Optional[str], libelle: str) -> None:
    """Un registre HACCP ne peut pas contenir une mesure qui n'a pas encore eu lieu."""
    try:
        jour = datetime.strptime(date_iso, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=422, detail="Date invalide (YYYY-MM-DD attendu).")
    limite = maintenant_local() + timedelta(minutes=TOLERANCE_FUTUR_MINUTES)
    instant = jour + timedelta(minutes=minutes_hhmm(heure, libelle)) if heure else jour
    if instant > limite:
        quand = f"{date_iso} {heure}" if heure else date_iso
        raise HTTPException(
            status_code=422,
            detail=f"{libelle} dans le futur ({quand}). "
                   "Saisissez l'heure réelle, pas une heure prévue.",
        )


def _duree_minutes(heure_debut: str, heure_fin: str) -> int:
    """Durée en minutes entre deux 'HH:MM' d'une même journée.

    v8.7 : une fin antérieure ou égale au début est refusée. Avant, elle était lue
    comme « le lendemain », si bien qu'une faute de frappe (14:00 → 13:59) donnait
    un refroidissement de 23 h 59 enregistré sans alerte.
    """
    debut = minutes_hhmm(heure_debut, "Heure de mise au froid")
    fin   = minutes_hhmm(heure_fin, "Heure de fin de refroidissement")
    if fin <= debut:
        raise HTTPException(
            status_code=422,
            detail=f"Fin du refroidissement ({heure_fin}) avant ou égale à la mise au froid ({heure_debut}).",
        )
    return fin - debut


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class RefroidissementCreate(BaseModel):
    date_refroidissement: str   = Field(..., description="YYYY-MM-DD")
    personnel_id:         int
    # v7.4 — mêmes trois espaces d'identifiants que la Cuisson (au moins un requis).
    produit_id:               Optional[int] = None
    catalogue_fournisseur_id: Optional[int] = None
    catalogue_vente_id:       Optional[int] = None
    cuisson_id:           Optional[int] = None
    heure_debut:          str   = Field(..., description="HH:MM mise en refroidissement")
    heure_fin:            str   = Field(..., description="HH:MM fin de refroidissement")
    temperature_initiale: Optional[float] = Field(None, description="T° à cœur avant refroidissement (par défaut : T° de sortie de la cuisson liée)")
    temperature_finale:   float = Field(..., description="T° à cœur après refroidissement")
    jeter_action:         bool  = Field(False, description="True = jeter le produit + créer entrée devenir")
    action_corrective:    Optional[str] = None


# ---------------------------------------------------------------------------
# GET /api/refroidissement/produits
# Liste des produits déjà cuits (déduit de la table cuissons)
# ---------------------------------------------------------------------------

@router.get("/produits")
async def lister_produits_cuisson():
    """
    Cuissons disponibles à refroidir : produites mais ni encore refroidies, ni jetées,
    ni périmées. Une ligne par produit, avec la cuisson FIFO (DLC la plus courte).

    Source unique : get_stock_unifie() restreint aux cuissons. Si toutes les cuissons
    sont refroidies/jetées (ou si la matière première source a été sortie en cascade),
    la liste est vide — pas de refroidissement possible.
    """
    async with get_db() as db:
        stock = await get_stock_unifie(
            db, BOUTIQUE_ID,
            type_produit="fini",
            sources=["cuisson"],
        )

    # Même clé d'identité composite que le module Cuisson : `produit_id` est NULL pour
    # les cuissons issues du catalogue d'achats, et les regrouper dessus les ferait
    # toutes fusionner en une seule entrée.
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
            continue
        if cle in par_produit:
            par_produit[cle]["nb_cuissons_disponibles"] += 1
            continue
        par_produit[cle] = {
            "id":                       pid,
            "cle_type":                 cle[0],
            "cle_id":                   cle[1],
            "catalogue_fournisseur_id": cfid,
            "catalogue_vente_id":       cvid,
            "nom":                      lot["produit_nom"],
            "espece":                   lot.get("espece"),
            "cuisson_id":               lot["source_id"],     # FIFO (plus pressé)
            "cuisson_date":             lot.get("date_origine"),
            "dlc":                      lot.get("dlc"),
            "numero_lot":               lot.get("numero_lot"),
            "origine":                  lot.get("origine"),
            "nb_cuissons_disponibles":  1,
        }

    return sorted(par_produit.values(), key=lambda p: (p["nom"] or "").lower())


# ---------------------------------------------------------------------------
# POST /api/refroidissement/enregistrements
# ---------------------------------------------------------------------------

@router.post("/enregistrements", status_code=201)
async def creer_refroidissement(body: RefroidissementCreate):
    async with get_db() as db:
        return await enregistrer_refroidissement(db, body)


async def enregistrer_refroidissement(db, body: RefroidissementCreate,
                                     juger_cuisson: bool = True) -> dict:
    """Contrôle et enregistre un refroidissement. Partagé par POST /enregistrements
    et par la fiche cuisson unique (routes_cuisson, v8.7). Commit inclus.

    `juger_cuisson=False` (fiche unique) : la T° de sortie est déjà jugée sur la
    ligne cuisson, avec son action corrective (ex. remise en cuisson). La rejuger ici
    déclarerait « à jeter » un produit recuit correctement.
    """
    duree = _duree_minutes(body.heure_debut, body.heure_fin)
    verifier_pas_dans_le_futur(body.date_refroidissement, body.heure_fin,
                               "Fin de refroidissement")
    if not (-30 <= body.temperature_finale <= 120):
        raise HTTPException(status_code=422, detail="T° après refroidissement hors plage (-30 à 120 °C).")

    # DLC J+3 calculée côté serveur (règle HACCP transformation)
    try:
        dlc_calculee = (datetime.strptime(body.date_refroidissement, "%Y-%m-%d").date()
                        + timedelta(days=DLC_JOURS_TRANSFORMATION))
    except ValueError:
        raise HTTPException(status_code=422, detail="date_refroidissement invalide (YYYY-MM-DD attendu).")

    numero_lot = None
    reception_ligne_id = None
    dlc_origine = None  # DLC du lot amont (réception OU fabrication)
    cuisson = None
    # Identifiants produit : hérités de la cuisson si le client ne les fournit pas.
    produit_id = body.produit_id
    cat_fournisseur_id = body.catalogue_fournisseur_id
    cat_vente_id = body.catalogue_vente_id

    # Récupérer la traçabilité depuis la cuisson
    if body.cuisson_id:
        cur_cuisson = await db.execute(
            """
            SELECT c.reception_ligne_id, c.fabrication_id,
                   c.produit_id, c.catalogue_fournisseur_id, c.catalogue_vente_id,
                   c.date_cuisson, c.heure_fin, c.temperature_sortie,
                   c.temperature_cible, c.dlc_finale
            FROM cuissons c
            WHERE c.id = ?
            """,
            (body.cuisson_id,),
        )
        cuisson = await cur_cuisson.fetchone()
        if cuisson:
            # Le refroidissement porte sur le produit qui vient d'être cuit :
            # on reprend son identité plutôt que de la faire redéclarer au front.
            if produit_id is None:
                produit_id = cuisson["produit_id"]
            if cat_fournisseur_id is None:
                cat_fournisseur_id = cuisson["catalogue_fournisseur_id"]
            if cat_vente_id is None:
                cat_vente_id = cuisson["catalogue_vente_id"]
            if cuisson["reception_ligne_id"]:
                reception_ligne_id = cuisson["reception_ligne_id"]
                cur_reception = await db.execute(
                    "SELECT numero_lot, dlc FROM reception_lignes WHERE id = ?",
                    (reception_ligne_id,),
                )
                reception_ligne = await cur_reception.fetchone()
                if reception_ligne:
                    numero_lot = reception_ligne["numero_lot"]
                    if reception_ligne["dlc"]:
                        dlc_origine = datetime.strptime(reception_ligne["dlc"], "%Y-%m-%d").date()
            elif cuisson["fabrication_id"]:
                cur_fab = await db.execute(
                    "SELECT lot_interne, dlc_finale FROM fabrications WHERE id = ?",
                    (cuisson["fabrication_id"],),
                )
                fab = await cur_fab.fetchone()
                if fab:
                    numero_lot = fab["lot_interne"]
                    if fab["dlc_finale"]:
                        dlc_origine = datetime.strptime(fab["dlc_finale"], "%Y-%m-%d").date()

    # Chronologie (v8.7) : on ne refroidit pas un produit avant de l'avoir cuit.
    if cuisson and cuisson["heure_fin"] and cuisson["date_cuisson"]:
        if body.date_refroidissement < cuisson["date_cuisson"]:
            raise HTTPException(
                status_code=422,
                detail=f"Refroidissement daté du {body.date_refroidissement}, "
                       f"avant la cuisson du {cuisson['date_cuisson']}.",
            )
        if (body.date_refroidissement == cuisson["date_cuisson"]
                and minutes_hhmm(body.heure_debut) < minutes_hhmm(cuisson["heure_fin"])):
            raise HTTPException(
                status_code=422,
                detail=f"Mise au froid ({body.heure_debut}) avant la fin de la cuisson "
                       f"({cuisson['heure_fin']}).",
            )

    # T° de départ = T° de sortie de cuisson. Elle se juge sur la cible de CETTE
    # cuisson (55 °C pour un rosbeef saignant), pas sur 75 °C en dur : sans ça, une
    # cuisson conforme était déclarée « insuffisante, à jeter » au refroidissement.
    temp_init = body.temperature_initiale
    if temp_init is None and cuisson and cuisson["temperature_sortie"] is not None:
        temp_init = cuisson["temperature_sortie"]
    cible_cuisson = (cuisson["temperature_cible"]
                     if cuisson and cuisson["temperature_cible"] is not None
                     else TEMPERATURE_MIN_CUISSON)
    cuisson_ok = (not juger_cuisson) or temp_init is None or temp_init >= cible_cuisson
    duree_ok   = duree <= DUREE_MAX_MINUTES
    temp_ok    = body.temperature_finale <= TEMPERATURE_CIBLE
    conforme   = cuisson_ok and duree_ok and temp_ok

    # Règle "JETER cuisson" : pasteurisation non atteinte
    jeter_cuisson = not cuisson_ok
    # Règle "JETER refroidissement" : couple temps/T° finale non respecté
    jeter_refroidissement = (not duree_ok) and (not temp_ok)
    jeter = jeter_cuisson or jeter_refroidissement

    if not conforme and not (body.action_corrective and body.action_corrective.strip()):
        raisons = []
        if not cuisson_ok:
            raisons.append(
                f"cuisson insuffisante ({temp_init:.1f} °C < {cible_cuisson:.0f} °C)"
            )
        if not temp_ok:
            raisons.append(f"T° finale trop haute ({body.temperature_finale:.1f} °C > {TEMPERATURE_CIBLE} °C)")
        if not duree_ok:
            raisons.append(f"durée dépassée ({duree} min > {DUREE_MAX_MINUTES} min)")
        raise HTTPException(
            status_code=422,
            detail=f"Action corrective obligatoire : {' · '.join(raisons)}.",
        )

    # DLC (v8.7) : le produit refroidi EST le produit cuit — il en garde la DLC, déjà
    # plafonnée par le lot d'origine. La recalculer depuis la date de refroidissement
    # la rallongeait d'un jour quand le refroidissement était daté du lendemain.
    dlc_ajustee = False
    if cuisson and cuisson["dlc_finale"]:
        dlc_finale_iso = cuisson["dlc_finale"]
    else:
        # Refroidissement sans cuisson rattachée (ancien écran) : règle historique.
        # Exception "suivi cuisson auto" (Lasagnes, Gratin, Parmentier…) : produit reçu
        # déjà fini, la DLC fournisseur reste seule valable (cf. routes_cuisson.py).
        reste_produit_fini = False
        if dlc_origine and cat_vente_id:
            cur_sca = await db.execute(
                "SELECT suivi_cuisson_auto FROM catalogue_vente WHERE id = ?",
                (cat_vente_id,),
            )
            cv = await cur_sca.fetchone()
            reste_produit_fini = bool(cv and cv["suivi_cuisson_auto"])
        dlc_finale = dlc_calculee
        if reste_produit_fini:
            dlc_finale = dlc_origine
        elif dlc_origine and dlc_calculee > dlc_origine:
            dlc_finale = dlc_origine
            dlc_ajustee = True
        dlc_finale_iso = dlc_finale.isoformat()

    # Après héritage depuis la cuisson : le produit doit rester identifiable,
    # sinon le refroidissement serait intraçable (exigence HACCP).
    if not (produit_id or cat_fournisseur_id or cat_vente_id):
        raise HTTPException(
            status_code=422,
            detail="Produit non identifié : renseignez produit_id, "
                   "catalogue_fournisseur_id ou catalogue_vente_id "
                   "(ou un cuisson_id valide dont ils seront hérités).",
        )

    cur = await db.execute(
        """
        INSERT INTO refroidissements (
            date_refroidissement, personnel_id, produit_id,
            catalogue_fournisseur_id, catalogue_vente_id, cuisson_id,
            numero_lot, reception_ligne_id,
            heure_debut, heure_fin, duree_minutes,
            temperature_initiale, temperature_finale,
            temperature_cible, duree_max_minutes,
            conforme, jeter, action_corrective, dlc_finale
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            body.date_refroidissement,
            body.personnel_id,
            produit_id,
            cat_fournisseur_id,
            cat_vente_id,
            body.cuisson_id,
            numero_lot,
            reception_ligne_id,
            body.heure_debut,
            body.heure_fin,
            duree,
            temp_init,
            body.temperature_finale,
            TEMPERATURE_CIBLE,
            DUREE_MAX_MINUTES,
            1 if conforme else 0,
            1 if jeter else 0,
            (body.action_corrective or "").strip() or None,
            dlc_finale_iso,
        ),
    )
    nouveau_id = cur.lastrowid

    # Entrée "devenir" dans le calendrier DLC si l'opérateur confirme le jet
    if body.jeter_action:
        try:
            await create_dlc_devenir(
                db,
                source_type="refroidissement",
                source_id=nouveau_id,
                statut="jete",
                personnel_id=body.personnel_id,
                commentaire=(body.action_corrective or "").strip() or "Produit jeté — refroidissement non conforme",
            )
        except Exception as exc:
            logger.warning("dlc_devenir non créé pour refroidissement #%d : %s", nouveau_id, exc)

    await db.commit()

    logger.info(
        "Refroidissement #%d — produit=%s/%s/%s durée=%dmin T°init=%s T°=%.1f conforme=%s jeter=%s jeter_action=%s",
        nouveau_id, produit_id, cat_fournisseur_id, cat_vente_id,
        duree, temp_init, body.temperature_finale,
        conforme, jeter, body.jeter_action,
    )
    return {
        "ok":            True,
        "id":            nouveau_id,
        "duree_minutes": duree,
        "conforme":      conforme,
        "jeter":         jeter,
        "jeter_cuisson": jeter_cuisson,
        "cuisson_ok":    cuisson_ok,
        "devenir_cree":  body.jeter_action,
        "dlc_ajustee":   dlc_ajustee,
        "dlc_origine":   dlc_origine.isoformat() if dlc_origine else None,
        "dlc_finale":    dlc_finale_iso,
    }


# ---------------------------------------------------------------------------
# GET /api/refroidissement/enregistrements
# ---------------------------------------------------------------------------

@router.get("/enregistrements")
async def lister_refroidissements(
    date_debut: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_fin:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit:      int = Query(50, ge=1, le=500),
):
    clauses: list = []
    params:  list = []
    if date_debut:
        clauses.append("r.date_refroidissement >= ?")
        params.append(date_debut)
    if date_fin:
        clauses.append("r.date_refroidissement <= ?")
        params.append(date_fin)
    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)

    async with get_db() as db:
        cur = await db.execute(
            f"""
            SELECT r.*,
                   COALESCE(p.nom, cv.nom, cf.designation) AS produit_nom,
                   p.espece     AS espece,
                   TRIM(pers.prenom || ' ' || COALESCE(pers.nom, '')) AS personnel_prenom,
                   rl.numero_lot AS reception_numero_lot,
                   rl.origine    AS origine,
                   rl.reception_id AS reception_id
            FROM   refroidissements r
            LEFT   JOIN produits  p    ON p.id    = r.produit_id
            LEFT   JOIN catalogue_vente cv   ON cv.id   = r.catalogue_vente_id
            LEFT   JOIN catalogue_fournisseur cf ON cf.id = r.catalogue_fournisseur_id
            LEFT   JOIN personnel pers ON pers.id = r.personnel_id
            LEFT   JOIN reception_lignes rl ON rl.id = r.reception_ligne_id
            {where_sql}
            ORDER BY r.date_refroidissement DESC, r.id DESC
            LIMIT ?
            """,
            tuple(params),
        )
        rows = await cur.fetchall()

    return [dict(r) for r in rows]

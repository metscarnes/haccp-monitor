"""
routes_cuisson.py — Module Cuisson (HACCP)

Enregistrement des cuissons avec contrôle température de fin de cuisson.
Cible réglementaire : ≥ 75 °C à cœur.

GET  /api/cuisson/enregistrements?type=rotissoire&limit=50
POST /api/cuisson/enregistrements
GET  /api/cuisson/a-traiter
GET  /api/cuisson/a-traiter/exclusions
POST /api/cuisson/a-traiter/{reception_ligne_id}/exclure
POST /api/cuisson/a-traiter/{reception_ligne_id}/reintegrer
GET  /api/cuisson/produits-vente-suggeres
GET  /api/cuisson/fiches                 (v8.7 — fiche unique cuisson + refroidissement)
GET  /api/cuisson/fiches/{id}
POST /api/cuisson/fiches
PUT  /api/cuisson/fiches/{id}
POST /api/cuisson/fiches/{id}/supprimer  (mot de passe admin si la fiche contient des mesures)
POST /api/cuisson/fiches/{id}/corriger   (mot de passe admin — date, heures, T°)
"""

import logging
from datetime import date as _date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from src.database import (
    get_db, get_stock_unifie, create_dlc_devenir, _insert_dlc_devenir, DLC_JOURS_TRANSFORMATION,
)
from src.api.routes_refroidissement import (
    RefroidissementCreate, enregistrer_refroidissement, _duree_minutes,
    TEMPERATURE_CIBLE as T_MAX_REFROID, DUREE_MAX_MINUTES as DUREE_MAX_REFROID,
    maintenant_local, minutes_hhmm, verifier_pas_dans_le_futur,
)

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
# Contrôles communs (POST /enregistrements et fiche unique v8.7)
# ---------------------------------------------------------------------------

def _controler_cuisson(date_cuisson: str, heure_debut: Optional[str], heure_fin: Optional[str],
                       temperature: Optional[float], degre: Optional[str],
                       action_corrective: Optional[str]) -> tuple[float, Optional[int]]:
    """Vérifie une cuisson (complète ou en cours) et renvoie (T° cible, conforme).

    `conforme` vaut None tant que la T° de sortie n'est pas saisie. Une cuisson est
    terminée quand heure de fin ET T° sont saisies — l'une ne va pas sans l'autre.
    """
    degre = degre or "generale"
    if degre not in DEGRES_CUISSON:
        raise HTTPException(
            status_code=422,
            detail=f"degre_cuisson invalide : {degre!r} (attendu : {', '.join(DEGRES_CUISSON)}).",
        )
    cible = DEGRES_CUISSON[degre]

    verifier_pas_dans_le_futur(date_cuisson, None, "Date de cuisson")
    if heure_debut:
        verifier_pas_dans_le_futur(date_cuisson, heure_debut, "Début de cuisson")
    if (heure_fin is None) != (temperature is None):
        raise HTTPException(
            status_code=422,
            detail="Heure de fin et T° de sortie vont ensemble : saisissez les deux "
                   "pour terminer la cuisson, ou aucune pour la compléter plus tard.",
        )
    if heure_fin is not None:
        if not heure_debut:
            raise HTTPException(status_code=422, detail="Heure de début de cuisson requise.")
        if minutes_hhmm(heure_fin, "Heure de fin de cuisson") <= minutes_hhmm(heure_debut, "Heure de début de cuisson"):
            raise HTTPException(
                status_code=422,
                detail=f"Fin de cuisson ({heure_fin}) avant ou égale au début ({heure_debut}).",
            )
        verifier_pas_dans_le_futur(date_cuisson, heure_fin, "Fin de cuisson")

    conforme = None
    if temperature is not None:
        if not (0 <= temperature <= 120):
            raise HTTPException(status_code=422, detail="T° de sortie hors plage (0 à 120 °C).")
        conforme = 1 if temperature >= cible else 0
        if not conforme and not (action_corrective and action_corrective.strip()):
            raise HTTPException(
                status_code=422,
                detail=f"Action corrective obligatoire si température < {cible:.0f} °C",
            )
    return cible, conforme


async def _dlc_cuisson(db, date_cuisson: str, reception_ligne_id: Optional[int],
                       fabrication_id: Optional[int],
                       catalogue_vente_id: Optional[int]) -> tuple[str, bool, Optional[str]]:
    """DLC du produit cuit → (dlc_finale ISO, dlc_ajustee, dlc_origine ISO).

    J+3 après la cuisson, jamais au-delà de la DLC du lot d'origine (réception OU
    fabrication). Produit « suivi cuisson auto » (Lasagnes, Gratin, Parmentier…) :
    reçu déjà fini, la cuisson n'est qu'un réchauffage → DLC fournisseur telle quelle
    (28/08/2026). Ce n'est pas un « ajustement » à signaler à l'opérateur.
    """
    try:
        dlc_calculee = (datetime.strptime(date_cuisson, "%Y-%m-%d").date()
                        + timedelta(days=DLC_JOURS_TRANSFORMATION))
    except ValueError:
        raise HTTPException(status_code=422, detail="date_cuisson invalide (YYYY-MM-DD attendu).")

    dlc_origine = None
    if reception_ligne_id:
        cur_rl = await db.execute(
            "SELECT COALESCE(dlc, dluo) AS dlc FROM reception_lignes WHERE id = ?",
            (reception_ligne_id,),
        )
        rl = await cur_rl.fetchone()
        if rl and rl["dlc"]:
            dlc_origine = datetime.strptime(rl["dlc"], "%Y-%m-%d").date()
    elif fabrication_id:
        cur_fab = await db.execute(
            "SELECT dlc_finale FROM fabrications WHERE id = ?", (fabrication_id,),
        )
        fab = await cur_fab.fetchone()
        if fab and fab["dlc_finale"]:
            dlc_origine = datetime.strptime(fab["dlc_finale"], "%Y-%m-%d").date()

    reste_produit_fini = False
    if dlc_origine and catalogue_vente_id:
        cur_sca = await db.execute(
            "SELECT suivi_cuisson_auto FROM catalogue_vente WHERE id = ?",
            (catalogue_vente_id,),
        )
        cv = await cur_sca.fetchone()
        reste_produit_fini = bool(cv and cv["suivi_cuisson_auto"])

    dlc_finale, dlc_ajustee = dlc_calculee, False
    if reste_produit_fini:
        dlc_finale = dlc_origine
    elif dlc_origine and dlc_calculee > dlc_origine:
        dlc_finale, dlc_ajustee = dlc_origine, True
    return (dlc_finale.isoformat(), dlc_ajustee,
            dlc_origine.isoformat() if dlc_origine else None)


# ---------------------------------------------------------------------------
# POST /api/cuisson/enregistrements  (cuisson complète en un appel — historique)
# ---------------------------------------------------------------------------

@router.post("/enregistrements", status_code=201)
async def creer_cuisson(body: CuissonCreate):
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
    degre = body.degre_cuisson or "generale"
    temperature_cible, conforme = _controler_cuisson(
        body.date_cuisson, body.heure_debut, body.heure_fin,
        body.temperature_sortie, degre, body.action_corrective,
    )

    async with get_db() as db:
        dlc_finale_iso, dlc_ajustee, dlc_origine = await _dlc_cuisson(
            db, body.date_cuisson, body.reception_ligne_id,
            body.fabrication_id, body.catalogue_vente_id,
        )
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
                body.type_cuisson.lower(), body.date_cuisson, body.personnel_id,
                body.produit_id, body.catalogue_fournisseur_id, body.catalogue_vente_id,
                body.reception_ligne_id, body.fabrication_id,
                body.quantite, body.unite or "kg",
                body.heure_debut, body.heure_fin,
                body.temperature_sortie, temperature_cible, degre,
                conforme, (body.action_corrective or "").strip() or None,
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
        "dlc_origine": dlc_origine,
    }


# ---------------------------------------------------------------------------
# Fiche cuisson unique (v8.7) — cuisson + suite (refroidi / vendu chaud) +
# refroidissement, pensée pour la saisie après coup (rattrapage du soir).
#
# GET  /api/cuisson/fiches            fiches récentes, avec leur état
# GET  /api/cuisson/fiches/{id}
# POST /api/cuisson/fiches            ouvre une fiche (complète ou non)
# PUT  /api/cuisson/fiches/{id}       complète une fiche
#
# États : cuisson_a_saisir → suite_a_choisir → refroidissement_a_saisir → terminee
# (« vendu chaud » ou une sortie de stock terminent aussi la fiche).
# ---------------------------------------------------------------------------

SUITES = ("refroidi", "vendu_chaud")
TYPES_CUISSON = ("four", "rotissoire", "marmite", "autre")
JOURS_A_COMPLETER = 30   # une fiche oubliée reste à compléter un mois
JOURS_TERMINEES   = 7


class RefroidissementFiche(BaseModel):
    heure_debut:        str   = Field(..., description="HH:MM mise au froid")
    heure_fin:          str   = Field(..., description="HH:MM fin de refroidissement")
    temperature_finale: float
    jeter_action:       bool  = False
    action_corrective:  Optional[str] = None


class FicheCuisson(BaseModel):
    personnel_id:             int
    date_cuisson:             Optional[str] = None   # requis à la création
    type_cuisson:             Optional[str] = None
    produit_id:               Optional[int] = None
    catalogue_fournisseur_id: Optional[int] = None
    catalogue_vente_id:       Optional[int] = None
    reception_ligne_id:       Optional[int] = None
    fabrication_id:           Optional[int] = None
    quantite:                 Optional[float] = None
    unite:                    Optional[str] = None
    heure_debut:              Optional[str] = None
    heure_fin:                Optional[str] = None
    temperature_sortie:       Optional[float] = None
    degre_cuisson:            Optional[str] = None
    action_corrective:        Optional[str] = None
    suite:                    Optional[str] = None
    refroidissement:          Optional[RefroidissementFiche] = None
    # Le lot cru est entièrement utilisé : il sort du stock cru (sinon il restait
    # disponible à la cuisson et compté en stock après avoir été cuit). Décoché
    # quand il en reste (cuisson d'une partie du lot). Pris en compte à la création.
    lot_epuise:               bool = False


_SQL_FICHES = """
    SELECT c.*,
           COALESCE(cv.nom, p.nom, cf.designation) AS produit_nom,
           cf.designation                           AS article_nom,
           COALESCE(rl.numero_lot, fab.lot_interne) AS numero_lot,
           COALESCE(rl.dlc, rl.dluo, fab.dlc_finale) AS dlc_lot,
           rl.origine                               AS origine,
           r_rec.date_reception                     AS date_reception,
           COALESCE(p.espece, CASE WHEN cf.famille = 'Viande' THEN cf.sous_famille END) AS espece,
           TRIM(pers.prenom || ' ' || COALESCE(pers.nom, '')) AS personnel_nom,
           rf.id                 AS refroid_id,
           rf.heure_debut        AS refroid_debut,
           rf.heure_fin          AS refroid_fin,
           rf.duree_minutes      AS refroid_duree,
           rf.temperature_finale AS refroid_temperature,
           rf.conforme           AS refroid_conforme,
           rf.jeter              AS refroid_jeter,
           rf.action_corrective  AS refroid_action,
           rf.dlc_finale         AS refroid_dlc,
           TRIM(pers_rf.prenom || ' ' || COALESCE(pers_rf.nom, '')) AS refroid_personnel_nom,
           dd.statut             AS devenir_statut
    FROM   cuissons c
    LEFT JOIN produits              p   ON p.id   = c.produit_id
    LEFT JOIN catalogue_vente       cv  ON cv.id  = c.catalogue_vente_id
    LEFT JOIN catalogue_fournisseur cf  ON cf.id  = c.catalogue_fournisseur_id
    LEFT JOIN reception_lignes      rl  ON rl.id  = c.reception_ligne_id
    LEFT JOIN receptions            r_rec ON r_rec.id = rl.reception_id
    LEFT JOIN fabrications          fab ON fab.id = c.fabrication_id
    LEFT JOIN personnel             pers ON pers.id = c.personnel_id
    LEFT JOIN refroidissements      rf  ON rf.id = (
              SELECT MAX(id) FROM refroidissements WHERE cuisson_id = c.id)
    LEFT JOIN personnel             pers_rf ON pers_rf.id = rf.personnel_id
    LEFT JOIN dlc_devenir           dd  ON dd.source_type = 'cuisson' AND dd.source_id = c.id
"""


def _etat_fiche(f: dict) -> str:
    if f["heure_fin"] is None or f["temperature_sortie"] is None:
        # Un lot sorti du stock (jeté en amont…) n'a plus de cuisson à saisir.
        return "terminee" if f["devenir_statut"] else "cuisson_a_saisir"
    if f["refroid_id"] or f["suite"] == "vendu_chaud" or f["devenir_statut"]:
        return "terminee"
    if f["suite"] == "refroidi":
        return "refroidissement_a_saisir"
    return "suite_a_choisir"


def _fiche_dict(row) -> dict:
    f = dict(row)
    f["etat"] = _etat_fiche(f)
    return f


async def _lire_fiche(db, fiche_id: int) -> dict:
    cur = await db.execute(_SQL_FICHES + " WHERE c.id = ?", (fiche_id,))
    row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Fiche cuisson introuvable.")
    return _fiche_dict(row)


async def compter_fiches_a_completer(db) -> int:
    """Nombre de fiches non terminées (même règle que _etat_fiche) — rappel Hub."""
    debut = (maintenant_local().date() - timedelta(days=JOURS_A_COMPLETER)).isoformat()
    cur = await db.execute(
        """
        SELECT COUNT(*) FROM cuissons c
        WHERE  c.date_cuisson >= ?
          AND  COALESCE(c.suite, '') <> 'vendu_chaud'
          AND  NOT EXISTS (SELECT 1 FROM refroidissements r WHERE r.cuisson_id = c.id)
          AND  NOT EXISTS (SELECT 1 FROM dlc_devenir d
                           WHERE d.source_type = 'cuisson' AND d.source_id = c.id)
        """,
        (debut,),
    )
    return (await cur.fetchone())[0]


@router.get("/fiches")
async def lister_fiches():
    """Fiches à compléter (≤ 30 jours) et terminées récemment (≤ 7 jours)."""
    aujourdhui = maintenant_local().date()
    debut = (aujourdhui - timedelta(days=JOURS_A_COMPLETER)).isoformat()
    debut_terminees = (aujourdhui - timedelta(days=JOURS_TERMINEES)).isoformat()
    async with get_db() as db:
        cur = await db.execute(
            _SQL_FICHES + """
            WHERE c.date_cuisson >= ?
            ORDER BY c.date_cuisson DESC,
                     COALESCE(c.heure_fin, c.heure_debut, '99:99') DESC, c.id DESC
            """,
            (debut,),
        )
        fiches = [_fiche_dict(r) for r in await cur.fetchall()]
    return {
        "a_completer": [f for f in fiches if f["etat"] != "terminee"],
        "terminees":   [f for f in fiches
                        if f["etat"] == "terminee" and f["date_cuisson"] >= debut_terminees],
    }


@router.get("/fiches/{fiche_id}")
async def lire_fiche(fiche_id: int):
    async with get_db() as db:
        return await _lire_fiche(db, fiche_id)


@router.post("/fiches", status_code=201)
async def creer_fiche(body: FicheCuisson):
    if not body.date_cuisson:
        raise HTTPException(status_code=422, detail="Date de cuisson requise.")
    if body.reception_ligne_id and body.fabrication_id:
        raise HTTPException(
            status_code=422,
            detail="Une cuisson ne peut pas être liée simultanément à une réception et à une fabrication.",
        )
    if not (body.produit_id or body.catalogue_fournisseur_id or body.catalogue_vente_id):
        raise HTTPException(status_code=422, detail="Choisissez le produit cuit.")
    async with get_db() as db:
        return await _enregistrer_fiche(db, None, body)


@router.put("/fiches/{fiche_id}")
async def completer_fiche(fiche_id: int, body: FicheCuisson):
    async with get_db() as db:
        existante = await _lire_fiche(db, fiche_id)
        return await _enregistrer_fiche(db, existante, body)


class SuppressionFiche(BaseModel):
    password: Optional[str] = None   # mot de passe ADMINISTRATEUR (fiche avec mesures)
    motif:    Optional[str] = None


def _fiche_sans_mesure(f: dict) -> bool:
    """Fiche ouverte dans la journée (produit + lot) sans aucune mesure saisie :
    la supprimer n'efface rien du registre HACCP."""
    return f["heure_fin"] is None and f["temperature_sortie"] is None and not f["refroid_id"]


@router.post("/fiches/{fiche_id}/supprimer")
async def supprimer_fiche(fiche_id: int, body: SuppressionFiche, request: Request):
    """Supprime une fiche (cuisson + refroidissement + sorties de stock qu'elle a créées).

    Sans mesure saisie → libre (erreur de produit, fiche en double…). Dès qu'il y a
    une heure de fin, une T° ou un refroidissement, c'est un enregistrement du registre
    HACCP : mot de passe administrateur obligatoire, comme pour les commandes.
    Le lot cru que la fiche avait sorti du stock (« lot entièrement utilisé ») y revient.
    """
    async with get_db() as db:
        fiche = await _lire_fiche(db, fiche_id)
        protegee = not _fiche_sans_mesure(fiche)
        if protegee:
            from src.api.routes_auth import verifier_mot_de_passe_admin
            verifier_mot_de_passe_admin(request, body.password)

        cur = await db.execute("SELECT id FROM refroidissements WHERE cuisson_id = ?", (fiche_id,))
        refroid_ids = [r[0] for r in await cur.fetchall()]
        for rid in refroid_ids:
            await db.execute(
                "DELETE FROM dlc_devenir WHERE source_type = 'refroidissement' AND source_id = ?", (rid,))
        await db.execute("DELETE FROM refroidissements WHERE cuisson_id = ?", (fiche_id,))
        await db.execute(
            "DELETE FROM dlc_devenir WHERE source_type = 'cuisson' AND source_id = ?", (fiche_id,))
        # Seule la sortie créée PAR cette fiche est annulée : un lot jeté ou vendu
        # par ailleurs reste sorti.
        for source_type, source_id in (("reception_ligne", fiche["reception_ligne_id"]),
                                       ("fabrication", fiche["fabrication_id"])):
            if source_id:
                await db.execute(
                    "DELETE FROM dlc_devenir WHERE source_type = ? AND source_id = ? "
                    "AND statut = 'consomme' AND commentaire = ?",
                    (source_type, source_id, f"Utilisé en cuisson (fiche #{fiche_id})"),
                )
        await db.execute("DELETE FROM cuissons WHERE id = ?", (fiche_id,))
        await db.commit()

    # Trace dans le journal du serveur : une suppression du registre doit rester retrouvable.
    logger.warning(
        "Fiche cuisson #%d SUPPRIMÉE (%s) — %s, lot %s, du %s, %s→%s, T° %s, refroid. %s — motif : %s",
        fiche_id, "mot de passe admin" if protegee else "sans mesure",
        fiche["produit_nom"], fiche["numero_lot"], fiche["date_cuisson"],
        fiche["heure_debut"], fiche["heure_fin"], fiche["temperature_sortie"],
        refroid_ids or "aucun", (body.motif or "").strip() or "—",
    )
    return {"ok": True}


class CorrectionRefroidissement(BaseModel):
    heure_debut:        Optional[str]   = None
    heure_fin:          Optional[str]   = None
    temperature_finale: Optional[float] = None
    action_corrective:  Optional[str]   = None


class CorrectionFiche(BaseModel):
    password:           Optional[str]   = None   # mot de passe ADMINISTRATEUR
    motif:              Optional[str]   = None
    date_cuisson:       Optional[str]   = None
    type_cuisson:       Optional[str]   = None
    quantite:           Optional[float] = None
    unite:              Optional[str]   = None
    heure_debut:        Optional[str]   = None
    heure_fin:          Optional[str]   = None
    temperature_sortie: Optional[float] = None
    degre_cuisson:      Optional[str]   = None
    action_corrective:  Optional[str]   = None
    refroidissement:    Optional[CorrectionRefroidissement] = None


def _texte(v: Optional[str]) -> Optional[str]:
    return (v or "").strip() or None


@router.post("/fiches/{fiche_id}/corriger")
async def corriger_fiche(fiche_id: int, body: CorrectionFiche, request: Request):
    """Corrige une fiche dont la cuisson est terminée : date, type, quantité, heures,
    T°, degré, et le refroidissement s'il existe. Mot de passe administrateur.

    Mêmes contrôles qu'à la saisie. Les DLC (cuisson, refroidissement) sont
    recalculées ; le refroidissement suit la date de la cuisson. Une correction qui
    ferait passer le produit de « jeté » à « non jeté » (ou l'inverse) est refusée :
    le produit a réellement été jeté ou gardé — supprimer et ressaisir la fiche.
    `etiquette_a_reimprimer` signale une étiquette imprimée avec une DLC devenue fausse.
    Champ absent (None) = valeur inchangée.
    """
    from src.api.routes_auth import verifier_mot_de_passe_admin
    verifier_mot_de_passe_admin(request, body.password)

    async with get_db() as db:
        avant = await _lire_fiche(db, fiche_id)
        if avant["heure_fin"] is None:
            raise HTTPException(status_code=422,
                                detail="Cuisson pas encore terminée : utilisez « Compléter ».")

        def val(source, champ, cle=None):
            v = getattr(source, champ)
            return avant[cle or champ] if v is None else v

        date_cuisson = val(body, "date_cuisson")
        heure_debut, heure_fin = val(body, "heure_debut"), val(body, "heure_fin")
        temperature = val(body, "temperature_sortie")
        degre = val(body, "degre_cuisson") or "generale"
        action = val(body, "action_corrective")
        type_cuisson = (val(body, "type_cuisson") or "rotissoire").lower()
        if type_cuisson not in TYPES_CUISSON:
            raise HTTPException(status_code=422, detail=f"Type de cuisson invalide : {type_cuisson!r}.")
        cible, conforme = _controler_cuisson(date_cuisson, heure_debut, heure_fin,
                                             temperature, degre, action)
        dlc_cuisson, _, _ = await _dlc_cuisson(
            db, date_cuisson, avant["reception_ligne_id"], avant["fabrication_id"],
            avant["catalogue_vente_id"],
        )

        refroid = None
        if avant["refroid_id"]:
            rb = body.refroidissement or CorrectionRefroidissement()
            r_debut = val(rb, "heure_debut", "refroid_debut")
            r_fin = val(rb, "heure_fin", "refroid_fin")
            r_temp = val(rb, "temperature_finale", "refroid_temperature")
            r_action = val(rb, "action_corrective", "refroid_action")
            duree = _duree_minutes(r_debut, r_fin)
            verifier_pas_dans_le_futur(date_cuisson, r_fin, "Fin de refroidissement")
            if minutes_hhmm(r_debut) < minutes_hhmm(heure_fin):
                raise HTTPException(
                    status_code=422,
                    detail=f"Mise au froid ({r_debut}) avant la fin de la cuisson ({heure_fin}).",
                )
            if not (-30 <= r_temp <= 120):
                raise HTTPException(status_code=422, detail="T° après refroidissement hors plage (-30 à 120 °C).")
            temp_ok, duree_ok = r_temp <= T_MAX_REFROID, duree <= DUREE_MAX_REFROID
            r_conforme = temp_ok and duree_ok
            if ((not temp_ok) and (not duree_ok)) != bool(avant["refroid_jeter"]):
                raise HTTPException(
                    status_code=422,
                    detail="Cette correction change la décision de jeter le produit. "
                           "Supprimez la fiche et ressaisissez-la.",
                )
            if not r_conforme and not _texte(r_action):
                raise HTTPException(status_code=422,
                                    detail="Refroidissement non conforme : action corrective obligatoire.")
            refroid = (date_cuisson, r_debut, r_fin, duree, temperature, r_temp,
                       1 if r_conforme else 0, _texte(r_action), dlc_cuisson, avant["refroid_id"])

        await db.execute(
            """UPDATE cuissons SET date_cuisson = ?, type_cuisson = ?, quantite = ?, unite = ?,
                   heure_debut = ?, heure_fin = ?, temperature_sortie = ?, temperature_cible = ?,
                   degre_cuisson = ?, conforme = ?, action_corrective = ?, dlc_finale = ?
               WHERE id = ?""",
            (date_cuisson, type_cuisson, val(body, "quantite"), val(body, "unite") or "kg",
             heure_debut, heure_fin, temperature, cible, degre, conforme,
             None if conforme else _texte(action), dlc_cuisson, fiche_id),
        )
        if refroid:
            await db.execute(
                """UPDATE refroidissements SET date_refroidissement = ?, heure_debut = ?,
                       heure_fin = ?, duree_minutes = ?, temperature_initiale = ?,
                       temperature_finale = ?, conforme = ?, action_corrective = ?, dlc_finale = ?
                   WHERE id = ?""",
                refroid,
            )

        # Étiquettes déjà imprimées dont la DLC n'est plus la bonne.
        cur = await db.execute(
            """SELECT COUNT(*) FROM etiquettes_generees
               WHERE dlc <> ? AND ((source_type = 'cuisson' AND source_id = ?)
                                   OR (source_type = 'refroidissement' AND source_id = ?))""",
            (dlc_cuisson, fiche_id, avant["refroid_id"] or -1),
        )
        etiquette_a_reimprimer = (await cur.fetchone())[0] > 0
        await db.commit()
        apres = await _lire_fiche(db, fiche_id)

    # Trace dans le journal : une correction du registre doit rester retrouvable.
    champs = ("date_cuisson", "type_cuisson", "quantite", "heure_debut", "heure_fin",
              "temperature_sortie", "degre_cuisson", "action_corrective", "dlc_finale",
              "refroid_debut", "refroid_fin", "refroid_temperature", "refroid_action", "refroid_dlc")
    changes = [f"{c} {avant[c]}→{apres[c]}" for c in champs if avant[c] != apres[c]]
    logger.warning("Fiche cuisson #%d CORRIGÉE (mot de passe admin) — %s — %s — motif : %s",
                   fiche_id, apres["produit_nom"], ", ".join(changes) or "aucun changement",
                   _texte(body.motif) or "—")
    apres["etiquette_a_reimprimer"] = etiquette_a_reimprimer
    apres["dlc_avant"] = avant["dlc_finale"]
    return apres


async def _enregistrer_fiche(db, existante: Optional[dict], body: FicheCuisson) -> dict:
    """Crée ou complète une fiche. Tout ou rien : si le refroidissement est refusé,
    la cuisson saisie dans le même envoi ne l'est pas non plus (sinon l'opérateur,
    voyant l'erreur, renverrait la fiche et créerait un doublon)."""
    try:
        fiche_id, info_dlc = await _ecrire_partie_cuisson(db, existante, body)
        fiche = await _lire_fiche(db, fiche_id)

        if body.lot_epuise and not existante:
            source = (("reception_ligne", fiche["reception_ligne_id"]) if fiche["reception_ligne_id"]
                      else ("fabrication", fiche["fabrication_id"]) if fiche["fabrication_id"]
                      else None)
            if source:
                # Sans cascade : create_dlc_devenir sortirait aussi en aval la cuisson
                # qu'on vient de créer. replace=False garde un devenir déjà saisi.
                await _insert_dlc_devenir(
                    db, source[0], source[1], "consomme", body.personnel_id,
                    f"Utilisé en cuisson (fiche #{fiche_id})", replace=False,
                )

        suite = body.suite or fiche["suite"]
        nouvelle_suite = bool(body.suite) and body.suite != fiche["suite"]
        if nouvelle_suite:
            if body.suite not in SUITES:
                raise HTTPException(status_code=422, detail=f"Suite invalide : {body.suite!r}.")
            if fiche["heure_fin"] is None:
                raise HTTPException(
                    status_code=422,
                    detail="Terminez d'abord la cuisson (heure de fin et T°).",
                )
            if fiche["refroid_id"] or fiche["suite"] == "vendu_chaud":
                raise HTTPException(status_code=422, detail="La suite de cette cuisson est déjà enregistrée.")
            await db.execute("UPDATE cuissons SET suite = ? WHERE id = ?", (body.suite, fiche_id))

        refroid = None
        if body.refroidissement:
            if suite != "refroidi":
                raise HTTPException(status_code=422, detail="Indiquez « Refroidi » pour saisir le refroidissement.")
            if fiche["refroid_id"]:
                raise HTTPException(status_code=422, detail="Le refroidissement de cette cuisson est déjà enregistré.")
            if fiche["heure_fin"] is None:
                raise HTTPException(status_code=422, detail="Terminez d'abord la cuisson (heure de fin et T°).")
            rb = body.refroidissement
            refroid = await enregistrer_refroidissement(db, RefroidissementCreate(
                date_refroidissement=fiche["date_cuisson"],
                personnel_id=body.personnel_id,
                cuisson_id=fiche_id,
                heure_debut=rb.heure_debut,
                heure_fin=rb.heure_fin,
                temperature_finale=rb.temperature_finale,
                jeter_action=rb.jeter_action,
                action_corrective=rb.action_corrective,
            ), juger_cuisson=False)   # commit inclus

        if nouvelle_suite and suite == "vendu_chaud":
            # Vendu chaud = sorti du stock, rien à refroidir (commit inclus).
            await create_dlc_devenir(
                db, source_type="cuisson", source_id=fiche_id, statut="vendu",
                personnel_id=body.personnel_id, commentaire="Vendu chaud",
            )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    fiche = await _lire_fiche(db, fiche_id)
    fiche.update(info_dlc)
    fiche["refroidissement_resultat"] = refroid
    logger.info("Fiche cuisson #%d enregistrée — état %s", fiche_id, fiche["etat"])
    return fiche


async def _ecrire_partie_cuisson(db, existante: Optional[dict], body: FicheCuisson) -> tuple[int, dict]:
    """Insère ou met à jour la partie cuisson. Une cuisson terminée (fin + T°) est
    figée : on n'en modifie plus les mesures, on ne fait qu'y ajouter la suite."""
    if existante and existante["heure_fin"] is not None:
        return existante["id"], {}

    def val(champ):
        v = getattr(body, champ)
        return v if v is not None or not existante else existante[champ]

    date_cuisson = val("date_cuisson")
    heure_debut, heure_fin = val("heure_debut"), val("heure_fin")
    temperature = val("temperature_sortie")
    degre = val("degre_cuisson") or "generale"
    action = val("action_corrective")
    cible, conforme = _controler_cuisson(date_cuisson, heure_debut, heure_fin,
                                         temperature, degre, action)
    reception_ligne_id, fabrication_id = val("reception_ligne_id"), val("fabrication_id")
    catalogue_vente_id = val("catalogue_vente_id")
    dlc_finale, dlc_ajustee, dlc_origine = await _dlc_cuisson(
        db, date_cuisson, reception_ligne_id, fabrication_id, catalogue_vente_id,
    )
    type_cuisson = (val("type_cuisson") or "rotissoire").lower()
    if type_cuisson not in TYPES_CUISSON:
        raise HTTPException(status_code=422, detail=f"Type de cuisson invalide : {type_cuisson!r}.")
    valeurs = {
        "type_cuisson":             type_cuisson,
        "date_cuisson":             date_cuisson,
        "personnel_id":             existante["personnel_id"] if existante else body.personnel_id,
        "produit_id":               val("produit_id"),
        "catalogue_fournisseur_id": val("catalogue_fournisseur_id"),
        "catalogue_vente_id":       catalogue_vente_id,
        "reception_ligne_id":       reception_ligne_id,
        "fabrication_id":           fabrication_id,
        "quantite":                 val("quantite"),
        "unite":                    val("unite") or "kg",
        "heure_debut":              heure_debut,
        "heure_fin":                heure_fin,
        "temperature_sortie":       temperature,
        "temperature_cible":        cible,
        "degre_cuisson":            degre,
        "conforme":                 conforme,
        "action_corrective":        (action or "").strip() or None,
        "dlc_finale":               dlc_finale,
    }
    if existante:
        sets = ", ".join(f"{k} = ?" for k in valeurs)
        await db.execute(f"UPDATE cuissons SET {sets} WHERE id = ?",
                         (*valeurs.values(), existante["id"]))
        fiche_id = existante["id"]
    else:
        cols = ", ".join(valeurs)
        marques = ", ".join("?" * len(valeurs))
        cur = await db.execute(f"INSERT INTO cuissons ({cols}) VALUES ({marques})",
                               tuple(valeurs.values()))
        fiche_id = cur.lastrowid
    return fiche_id, {"dlc_ajustee": dlc_ajustee, "dlc_origine": dlc_origine}


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
            -- FIFO d'abord : trié par date de réception décroissante, le LIMIT pouvait
            -- couper précisément le lot le plus urgent.
            ORDER BY COALESCE(rl.dlc, rl.dluo, '9999-12-31') ASC, r.date_reception ASC, r.id ASC
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
    Réceptions closes, conformes, non refusées, d'un article catalogue ACHATS
    dont le produit de vente correspondant (via le groupe comparatif) est
    marqué `suivi_cuisson_auto = 1` (ex. Lasagne, Gratin dauphinois, Parmentier
    de canard — reçus tout prêts, sans étape de fabrication), et n'ayant pas
    encore de cuisson liée. Triés par DLC croissante (le plus urgent d'abord).

    v7.6 (28/08/2026) : réécrit sur le catalogue achats/vente. La v7.4 gardait
    `p.suivi_cuisson_auto` sur l'ancienne table `produits`, vide pour 99% du
    stock réel depuis la v6.0 — cette route ne trouvait donc jamais rien.
    Le lien passe par comparatif_groupe_ligne → comparatif_groupe_vente, comme
    la modale "ça devient quel produit ?" du wizard Cuisson.

    Un même lot reçu peut en théorie matcher PLUSIEURS produits de vente
    marqués suivi_cuisson_auto=1 s'ils partagent le même groupe comparatif
    (ex. un groupe à la fois "plat traiteur A" et "plat traiteur B" reliés
    au même article d'achat — cas non rencontré à ce jour, les plats visés
    par ce flag ont chacun leur groupe dédié). GROUP BY ci-dessous évite un
    doublon de tâche Hub dans ce cas plutôt que de planter ou dupliquer.

    v7.6 (30/08/2026) : exclut les lots marqués `exclu_cuisson_auto = 1`
    (cf. POST .../exclure) et renvoie en plus `article_designation` — le nom
    de l'article tel que reçu au catalogue ACHATS, potentiellement différent
    du nom du produit fini `produit_nom` (catalogue VENTE). Utile à l'écran
    pour vérifier qu'un lot n'est pas mal rattaché avant de le cuisiner.
    """
    async with get_db() as db:
        cur = await db.execute(
            """
            SELECT rl.id                       AS reception_ligne_id,
                   r.id                         AS reception_id,
                   rl.catalogue_fournisseur_id,
                   MIN(cv.id)                   AS catalogue_vente_id,
                   COALESCE(MIN(cv.nom), cf.designation) AS produit_nom,
                   cf.designation                AS article_designation,
                   cf.code_article                AS article_code,
                   rl.numero_lot,
                   COALESCE(rl.dlc, rl.dluo)    AS dlc,
                   r.date_reception,
                   f.nom                        AS fournisseur_nom
            FROM   reception_lignes rl
            JOIN   receptions r ON r.id = rl.reception_id
            JOIN   catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
            JOIN   comparatif_groupe_ligne gl ON gl.catalogue_fournisseur_id = rl.catalogue_fournisseur_id
            JOIN   comparatif_groupe_vente gv ON gv.groupe_id = gl.groupe_id
            JOIN   catalogue_vente cv ON cv.id = gv.catalogue_vente_id
            LEFT JOIN fournisseurs f ON f.id = rl.fournisseur_id
            WHERE  cv.suivi_cuisson_auto = 1
              AND  r.statut = 'cloturee'
              AND  rl.conforme = 1
              AND  r.livraison_refusee = 0
              AND  rl.exclu_cuisson_auto = 0
              AND  (COALESCE(rl.dlc, rl.dluo) IS NULL OR COALESCE(rl.dlc, rl.dluo) >= DATE('now'))
              AND  NOT EXISTS (SELECT 1 FROM cuissons c WHERE c.reception_ligne_id = rl.id)
            GROUP BY rl.id
            ORDER BY CASE WHEN COALESCE(rl.dlc, rl.dluo) IS NOT NULL THEN 0 ELSE 1 END,
                     COALESCE(rl.dlc, rl.dluo) ASC,
                     r.date_reception ASC
            """
        )
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Exclusion manuelle de la liste "À cuire"
# GET  /api/cuisson/a-traiter/exclusions
# POST /api/cuisson/a-traiter/{reception_ligne_id}/exclure
# POST /api/cuisson/a-traiter/{reception_ligne_id}/reintegrer
# ---------------------------------------------------------------------------

class ExclureLotBody(BaseModel):
    motif: Optional[str] = None


@router.get("/a-traiter/exclusions")
async def lots_exclus():
    """Lots actuellement exclus de la liste "À cuire" (pour l'écran de gestion
    des exclusions : vérifier/réintégrer). Même jointure que `/a-traiter`,
    sans le filtre `exclu_cuisson_auto = 0` ni le filtre DLC/cuisson déjà faite
    (un lot exclu reste dans la liste même après sa DLC passée ou une fois cuit,
    tant qu'il n'est pas explicitement réintégré)."""
    async with get_db() as db:
        cur = await db.execute(
            """
            SELECT rl.id                       AS reception_ligne_id,
                   r.id                         AS reception_id,
                   rl.catalogue_fournisseur_id,
                   MIN(cv.id)                   AS catalogue_vente_id,
                   COALESCE(MIN(cv.nom), cf.designation) AS produit_nom,
                   cf.designation                AS article_designation,
                   cf.code_article                AS article_code,
                   rl.numero_lot,
                   COALESCE(rl.dlc, rl.dluo)    AS dlc,
                   r.date_reception,
                   f.nom                        AS fournisseur_nom,
                   rl.exclu_cuisson_auto_motif   AS motif
            FROM   reception_lignes rl
            JOIN   receptions r ON r.id = rl.reception_id
            JOIN   catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
            JOIN   comparatif_groupe_ligne gl ON gl.catalogue_fournisseur_id = rl.catalogue_fournisseur_id
            JOIN   comparatif_groupe_vente gv ON gv.groupe_id = gl.groupe_id
            JOIN   catalogue_vente cv ON cv.id = gv.catalogue_vente_id
            LEFT JOIN fournisseurs f ON f.id = rl.fournisseur_id
            WHERE  cv.suivi_cuisson_auto = 1
              AND  rl.exclu_cuisson_auto = 1
            GROUP BY rl.id
            ORDER BY r.date_reception DESC
            """
        )
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/a-traiter/{reception_ligne_id}/exclure")
async def exclure_lot(reception_ligne_id: int, body: ExclureLotBody):
    async with get_db() as db:
        cur = await db.execute(
            "SELECT id FROM reception_lignes WHERE id = ?", (reception_ligne_id,)
        )
        if not await cur.fetchone():
            raise HTTPException(status_code=404, detail="Ligne de réception introuvable")
        await db.execute(
            "UPDATE reception_lignes SET exclu_cuisson_auto = 1, exclu_cuisson_auto_motif = ? WHERE id = ?",
            (body.motif.strip() if body.motif else None, reception_ligne_id),
        )
        await db.commit()
    return {"ok": True}


@router.post("/a-traiter/{reception_ligne_id}/reintegrer")
async def reintegrer_lot(reception_ligne_id: int):
    async with get_db() as db:
        cur = await db.execute(
            "SELECT id FROM reception_lignes WHERE id = ?", (reception_ligne_id,)
        )
        if not await cur.fetchone():
            raise HTTPException(status_code=404, detail="Ligne de réception introuvable")
        await db.execute(
            "UPDATE reception_lignes SET exclu_cuisson_auto = 0, exclu_cuisson_auto_motif = NULL WHERE id = ?",
            (reception_ligne_id,),
        )
        await db.commit()
    return {"ok": True}


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

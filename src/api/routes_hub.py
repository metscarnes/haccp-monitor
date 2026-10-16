"""
routes_hub.py — Agrégation des tâches HACCP pour le popup du Hub.

GET /api/hub/taches-resume
    Retourne deux listes :
    - aujourd_hui : tâches à faire aujourd'hui ou en retard
    - a_venir    : tâches dont l'échéance approche (≤ 14 jours)

Sources agrégées :
- Nettoyage  (quotidien)    → table registre_nettoyage
- Nuisibles  (hebdomadaire) → table nuisibles_controles, semaine ISO en cours
- Étalonnage (trimestriel)  → table etalonnages, dernier + 92 jours
- DLC        (continu)      → reception_lignes + fabrications (get_dlc_calendrier),
                              avec exclusion des items dont le devenir est déjà saisi
"""

import json
import logging
import re
import time
from datetime import date as _date, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.database import get_db, get_dlc_calendrier, get_parametre, set_parametre

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hub", tags=["hub"])

DELAI_ETALONNAGE_JOURS = 92      # ~3 mois (aligné sur routes_etalonnage.py)
SEUIL_A_VENIR_JOURS    = 14
BOUTIQUE_ID            = 1

# ===========================================================================
# Disposition des tuiles du Hub (personnalisée par l'administrateur)
# ===========================================================================
# Le serveur ne garde que des identifiants ; la liste des tuiles possibles
# (titre, icône, lien) et la disposition d'origine sont dans hub.js. Une seule
# disposition pour la boutique : tablette, Surface et téléphone affichent le même Hub.
#   accueil  : tuiles et dossiers de l'écran d'accueil, dans l'ordre de la grille
#   dossiers : {id: {titre, icone, tuiles}} — un dossier peut en contenir d'autres
#   connues  : toutes les tuiles existantes au moment de l'enregistrement — une
#              tuile ajoutée plus tard dans le code (absente de « connues »)
#              apparaît donc d'elle-même au lieu d'être prise pour une retirée.
CLE_DISPOSITION = "hub_disposition"
VERSION_DISPOSITION = 2
JETON_DISPOSITION_SUJET = "disposition-hub"
JETON_DISPOSITION_DUREE_S = 15 * 60
_ID_TUILE = re.compile(r"^[a-z0-9-]{1,40}$")
_ID_DOSSIER = re.compile(r"^dossier-[a-z0-9-]{1,32}$")
_VIDE = {"personnalisee": False, "accueil": [], "dossiers": {}, "connues": []}


class Dossier(BaseModel):
    titre: str = Field(min_length=1, max_length=40)
    icone: str = Field(default="📁", min_length=1, max_length=8)
    tuiles: List[str] = Field(default_factory=list, max_length=80)


class Disposition(BaseModel):
    accueil: List[str] = Field(default_factory=list, max_length=80)
    dossiers: Dict[str, Dossier] = Field(default_factory=dict, max_length=40)
    connues: List[str] = Field(default_factory=list, max_length=200)
    jeton: Optional[str] = None      # autorisation remise par /disposition/deverrouiller


class MotDePasse(BaseModel):
    password: Optional[str] = None   # mot de passe ADMINISTRATEUR (même en session équipe)


def _exiger_jeton_disposition(jeton: Optional[str]) -> None:
    from jose import JWTError, jwt
    from src.api.routes_auth import _JWT_ALGO, _JWT_SECRET
    try:
        if jwt.decode(jeton or "", _JWT_SECRET, algorithms=[_JWT_ALGO]).get("sub") == JETON_DISPOSITION_SUJET:
            return
    except JWTError:
        pass
    raise HTTPException(status_code=401, detail="Personnalisation du Hub réservée à "
                        "l'administrateur : déverrouillez avec le mot de passe administrateur.")


def _verifier_id(i: str) -> None:
    if not _ID_TUILE.match(i):
        raise HTTPException(status_code=422, detail=f"Tuile inconnue : {i!r}")


def _nettoyer(body: Disposition) -> dict:
    """Arbre propre à partir de l'accueil : chaque tuile / dossier une seule fois
    (un dossier placé dans lui-même ou dans un de ses sous-dossiers est ignoré),
    dossiers cités mais inexistants retirés, dossiers non rangés abandonnés."""
    for i in body.accueil + body.connues + [t for d in body.dossiers.values() for t in d.tuiles]:
        _verifier_id(i)
    for i in body.dossiers:
        if not _ID_DOSSIER.match(i):
            raise HTTPException(status_code=422, detail=f"Dossier invalide : {i!r}")
    vus: set = set()
    dossiers: dict = {}

    def parcourir(ids: List[str]) -> List[str]:
        garde = []
        for i in ids:
            if i in vus or (i.startswith("dossier-") and i not in body.dossiers):
                continue
            vus.add(i)
            garde.append(i)
            if i in body.dossiers:
                d = body.dossiers[i]
                dossiers[i] = {"titre": d.titre.strip() or "Dossier", "icone": d.icone.strip() or "📁",
                               "tuiles": parcourir(d.tuiles)}
        return garde

    accueil = parcourir(body.accueil)
    connues = list(dict.fromkeys(body.connues + [i for i in vus if not i.startswith("dossier-")]))
    return {"version": VERSION_DISPOSITION, "accueil": accueil, "dossiers": dossiers,
            "connues": connues}


@router.get("/disposition")
async def lire_disposition():
    """Disposition enregistrée, ou {"personnalisee": false} (Hub d'origine)."""
    async with get_db() as db:
        brut = await get_parametre(db, BOUTIQUE_ID, CLE_DISPOSITION)
    if not brut:
        return _VIDE
    try:
        d = json.loads(brut)
        if d.get("version") != VERSION_DISPOSITION:
            return _VIDE
        return {"personnalisee": True, "accueil": d["accueil"], "dossiers": d["dossiers"],
                "connues": d["connues"]}
    except (ValueError, AttributeError, KeyError):
        logger.warning("hub_disposition illisible, Hub d'origine affiché")
        return _VIDE


@router.post("/disposition/deverrouiller")
async def deverrouiller_disposition(body: MotDePasse, request: Request):
    """Vérifie le mot de passe administrateur et remet l'autorisation (15 min)."""
    from jose import jwt
    from src.api.routes_auth import _JWT_ALGO, _JWT_SECRET, verifier_mot_de_passe_admin
    verifier_mot_de_passe_admin(request, body.password)
    jeton = jwt.encode({"sub": JETON_DISPOSITION_SUJET,
                        "exp": int(time.time()) + JETON_DISPOSITION_DUREE_S},
                       _JWT_SECRET, algorithm=_JWT_ALGO)
    return {"jeton": jeton, "expire_dans": JETON_DISPOSITION_DUREE_S}


@router.put("/disposition")
async def enregistrer_disposition(body: Disposition):
    _exiger_jeton_disposition(body.jeton)
    d = _nettoyer(body)
    async with get_db() as db:
        await set_parametre(db, BOUTIQUE_ID, CLE_DISPOSITION, json.dumps(d, ensure_ascii=False))
    return {"personnalisee": True, "accueil": d["accueil"], "dossiers": d["dossiers"],
            "connues": d["connues"]}


@router.post("/disposition/reinitialiser")
async def reinitialiser_disposition(body: Disposition):
    """« Revenir à l'origine » : efface la disposition personnalisée."""
    _exiger_jeton_disposition(body.jeton)
    async with get_db() as db:
        await db.execute("DELETE FROM parametres WHERE boutique_id = ? AND cle = ?",
                         (BOUTIQUE_ID, CLE_DISPOSITION))
        await db.commit()
    return _VIDE


NUISIBLES_TYPES = {
    1: "Rongeurs",
    2: "Insectes volants",
    3: "Insectes rampants",
    4: "Oiseaux",
}

# Types désactivés dans le module nuisibles (aucun dispositif installé) :
# ils ne sont plus attendus dans le contrôle hebdomadaire.
# Doit rester aligné sur TYPES_DESACTIVES (routes_nuisibles.py) et sur
# le drapeau `actif` de TYPES dans static/js/nuisibles.js.
NUISIBLES_TYPES_DESACTIVES = {4}


@router.get("/taches-resume")
async def taches_resume():
    today = _date.today()
    iso_year, iso_week, _ = today.isocalendar()

    aujourd_hui: list[dict] = []
    a_venir:     list[dict] = []

    async with get_db() as db:

        # ── 0. Produits en attente de traçabilité (PRIORITÉ 1, NON-MASQUABLE) ──
        # Tant qu'un produit reçu n'a pas son lot/DLC, il est bloqué hors stock.
        # Cette alerte ne peut pas être masquée par le snooze (cf. hub.js).
        try:
            rows = await db.execute_fetchall(
                "SELECT COUNT(*) FROM reception_lignes "
                "WHERE COALESCE(statut, 'complet') = 'en_attente'"
            )
            n_attente = rows[0][0] if rows else 0
            if n_attente:
                aujourd_hui.append({
                    "code":          "produits_attente",
                    "libelle":       "Produits en attente de traçabilité",
                    "url":           "/produits-attente.html",
                    "icone":         "⛔",
                    "etat":          "en_retard",
                    "priorite":      1,
                    "non_masquable": True,
                    "detail":        f"{n_attente} produit(s) sans lot/DLC — "
                                     "à compléter (stock bloqué)",
                })
        except Exception as exc:
            logger.warning("hub résumé produits en attente : %s", exc)

        # ── 0bis. Chiffre d'affaires de la veille ───────────────
        # On rappelle de saisir le CA du jour précédent (saisie le matin
        # pour la veille). Pas de rappel le lendemain d'un jour de fermeture
        # impossible à deviner ici → l'utilisateur peut saisir 0 si fermé.
        try:
            veille = (today - timedelta(days=1)).isoformat()
            rows = await db.execute_fetchall(
                "SELECT 1 FROM ca_journalier "
                "WHERE boutique_id = ? AND date_ca = ? LIMIT 1",
                (BOUTIQUE_ID, veille),
            )
            if not rows:
                d_fr = (today - timedelta(days=1)).strftime("%d/%m")
                aujourd_hui.append({
                    "code":    "ca_veille",
                    "libelle": "Chiffre d'affaires",
                    "url":     "/pilotage-ca.html",
                    "icone":   "💶",
                    "etat":    "a_faire",
                    "detail":  f"Saisir le CA du {d_fr}",
                })
        except Exception as exc:
            logger.warning("hub résumé CA veille : %s", exc)

        # ── 1. Nettoyage quotidien ──────────────────────────────
        try:
            rows = await db.execute_fetchall(
                "SELECT 1 FROM registre_nettoyage WHERE date_val = ? LIMIT 1",
                (today.isoformat(),),
            )
            if not rows:
                aujourd_hui.append({
                    "code":    "nettoyage",
                    "libelle": "Nettoyage & désinfection",
                    "url":     "/nettoyage.html",
                    "icone":   "🧹",
                    "etat":    "a_faire",
                    "detail":  "Quotidien — à valider",
                })
        except Exception as exc:
            logger.warning("hub résumé nettoyage : %s", exc)

        # ── 2. Nuisibles hebdomadaires ──────────────────────────
        # Affichage seulement le lundi (jour ISO 1), pour la semaine précédente
        try:
            day_of_week = today.isoweekday()  # 1 = lundi, 7 = dimanche
            if day_of_week == 1:  # Lundi uniquement
                # Semaine précédente
                prev_week_date = today - timedelta(days=7)
                prev_iso_year, prev_iso_week, _ = prev_week_date.isocalendar()

                rows = await db.execute_fetchall(
                    "SELECT type_id FROM nuisibles_controles "
                    "WHERE annee = ? AND semaine = ?",
                    (prev_iso_year, prev_iso_week),
                )
                types_faits = {r[0] for r in rows} | NUISIBLES_TYPES_DESACTIVES
                manquants   = [tid for tid in NUISIBLES_TYPES if tid not in types_faits]
                if manquants:
                    noms = ", ".join(NUISIBLES_TYPES[t] for t in manquants)
                    aujourd_hui.append({
                        "code":    "nuisibles",
                        "libelle": "Contrôle nuisibles",
                        "url":     "/nuisibles.html",
                        "icone":   "🪤",
                        "etat":    "a_faire",
                        "detail":  f"Semaine {prev_iso_week} — manque : {noms}",
                    })
        except Exception as exc:
            logger.warning("hub résumé nuisibles : %s", exc)

        # ── 3. Étalonnage trimestriel ───────────────────────────
        try:
            rows = await db.execute_fetchall(
                "SELECT date_etalonnage FROM etalonnages "
                "ORDER BY date_etalonnage DESC LIMIT 1"
            )
            if not rows:
                aujourd_hui.append({
                    "code":    "etalonnage",
                    "libelle": "Étalonnage thermomètres",
                    "url":     "/etalonnage.html",
                    "icone":   "🌡️",
                    "etat":    "en_retard",
                    "detail":  "Jamais effectué",
                })
            else:
                dernier  = _date.fromisoformat(rows[0][0])
                prochain = dernier + timedelta(days=DELAI_ETALONNAGE_JOURS)
                jours    = (prochain - today).days

                if jours < 0:
                    aujourd_hui.append({
                        "code":    "etalonnage",
                        "libelle": "Étalonnage thermomètres",
                        "url":     "/etalonnage.html",
                        "icone":   "🌡️",
                        "etat":    "en_retard",
                        "detail":  f"En retard de {-jours} jour(s)",
                    })
                elif jours <= SEUIL_A_VENIR_JOURS:
                    a_venir.append({
                        "code":           "etalonnage",
                        "libelle":        "Étalonnage thermomètres",
                        "url":            "/etalonnage.html",
                        "icone":          "🌡️",
                        "jours_restants": jours,
                        "echeance":       prochain.isoformat(),
                        "detail":         f"Dans {jours} jour(s) — {prochain.strftime('%d/%m/%Y')}",
                    })
        except Exception as exc:
            logger.warning("hub résumé étalonnage : %s", exc)

        # ── 4. DLC (réceptions + fabrications) ──────────────────
        try:
            params = await db.execute_fetchall(
                "SELECT cle, valeur FROM parametres "
                "WHERE boutique_id = ? AND cle LIKE 'dlc_alerte_%_jours'",
                (BOUTIQUE_ID,),
            )
            seuils = {r[0]: int(r[1]) for r in params}
            seuil_rouge = seuils.get("dlc_alerte_rouge_jours", 1)

            # Plage : on remonte jusqu'à 30 jours en arrière pour couvrir les DLC
            # déjà dépassées encore ouvertes (devenir non saisi)
            date_debut = (today - timedelta(days=30)).isoformat()
            date_fin   = (today + timedelta(days=SEUIL_A_VENIR_JOURS)).isoformat()

            items = await get_dlc_calendrier(db, BOUTIQUE_ID, date_debut, date_fin)
            # On ne garde que les items dont le devenir n'est pas encore saisi
            ouverts = [it for it in items if not it.get("devenir_statut")]

            n_expirees   = 0
            n_critiques  = 0
            n_surveiller = 0
            for it in ouverts:
                dlc_iso = it.get("dlc")
                if not dlc_iso:
                    continue
                try:
                    dlc = _date.fromisoformat(dlc_iso[:10])
                except ValueError:
                    continue
                jours = (dlc - today).days
                if jours < 0:
                    n_expirees += 1
                elif jours <= seuil_rouge:
                    n_critiques += 1
                elif jours <= SEUIL_A_VENIR_JOURS:
                    n_surveiller += 1

            if n_expirees > 0:
                aujourd_hui.append({
                    "code":    "dlc_expirees",
                    "libelle": "DLC dépassées",
                    "url":     "/dlc.html",
                    "icone":   "🚨",
                    "etat":    "en_retard",
                    "detail":  f"{n_expirees} produit(s) à retirer",
                })
            if n_critiques > 0:
                aujourd_hui.append({
                    "code":    "dlc_critiques",
                    "libelle": "DLC critiques",
                    "url":     "/dlc.html",
                    "icone":   "🔴",
                    "etat":    "a_faire",
                    "detail":  f"{n_critiques} produit(s) — DLC dans ≤ {seuil_rouge} j",
                })
            if n_surveiller > 0:
                a_venir.append({
                    "code":    "dlc_surveiller",
                    "libelle": "DLC à surveiller",
                    "url":     "/dlc.html",
                    "icone":   "🟠",
                    "detail":  f"{n_surveiller} produit(s) — DLC dans ≤ {SEUIL_A_VENIR_JOURS} j",
                })
        except Exception as exc:
            logger.warning("hub résumé dlc : %s", exc)

        # ── 5. Production à cuire (produits reçus déjà préparés) ─
        # Ex. Lasagne / Gratin dauphinois / Parmentier de canard, marqués
        # `suivi_cuisson_auto` sur le produit de VENTE (catalogue_vente), relié
        # à l'article d'achat reçu via le groupe comparatif — même règle que
        # GET /api/cuisson/a-traiter (v7.6, 28/08/2026 : la v7.4 interrogeait
        # encore `produits.suivi_cuisson_auto`, vide pour le stock réel).
        # exclu_cuisson_auto = 0 (v7.6, 30/08/2026) : un lot exclu manuellement
        # depuis l'écran "À cuire" ne doit pas non plus compter ici, sinon la
        # tuile Hub reste allumée pour un lot qu'on a volontairement écarté.
        try:
            rows = await db.execute_fetchall(
                """
                SELECT COUNT(DISTINCT rl.id)
                FROM   reception_lignes rl
                JOIN   receptions r ON r.id = rl.reception_id
                JOIN   comparatif_groupe_ligne gl ON gl.catalogue_fournisseur_id = rl.catalogue_fournisseur_id
                JOIN   comparatif_groupe_vente gv ON gv.groupe_id = gl.groupe_id
                JOIN   catalogue_vente cv ON cv.id = gv.catalogue_vente_id
                WHERE  cv.suivi_cuisson_auto = 1
                  AND  r.statut = 'cloturee'
                  AND  rl.conforme = 1
                  AND  r.livraison_refusee = 0
                  AND  rl.exclu_cuisson_auto = 0
                  AND  (COALESCE(rl.dlc, rl.dluo) IS NULL OR COALESCE(rl.dlc, rl.dluo) >= DATE('now'))
                  AND  NOT EXISTS (SELECT 1 FROM cuissons c WHERE c.reception_ligne_id = rl.id)
                """
            )
            n_a_cuire = rows[0][0] if rows else 0
            if n_a_cuire:
                aujourd_hui.append({
                    "code":    "production_a_cuire",
                    "libelle": "Production à cuire",
                    "url":     "/production-a-cuire.html",
                    "icone":   "🍽",
                    "etat":    "a_faire",
                    "detail":  f"{n_a_cuire} lot(s) reçu(s) en attente de cuisson",
                })
        except Exception as exc:
            logger.warning("hub résumé production à cuire : %s", exc)

        # ── 6. Produits à ajouter au catalogue de vente ─────────
        # Étiquette prix imprimée pour un article absent du catalogue = l'équipe a
        # mis un nouveau produit en rayon (cf. src/produits_a_creer.py).
        try:
            from src.produits_a_creer import compter_demandes
            n_a_creer = await compter_demandes(db)
            await db.commit()               # demandes closes d'elles-mêmes
            if n_a_creer:
                aujourd_hui.append({
                    "code":    "produits_a_creer",
                    "libelle": "Nouveau produit en rayon",
                    "url":     "/catalogue-vente.html?a_creer=1",
                    "icone":   "🆕",
                    "etat":    "a_faire",
                    "detail":  f"{n_a_creer} produit(s) étiqueté(s) hors catalogue — "
                               "à ajouter au catalogue de vente",
                })
        except Exception as exc:
            logger.warning("hub résumé produits à créer : %s", exc)

    return {
        "date":        today.isoformat(),
        "aujourd_hui": aujourd_hui,
        "a_venir":     a_venir,
    }

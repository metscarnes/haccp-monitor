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

import logging
from datetime import date as _date, timedelta

from fastapi import APIRouter

from src.database import get_db, get_dlc_calendrier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hub", tags=["hub"])

DELAI_ETALONNAGE_JOURS = 92      # ~3 mois (aligné sur routes_etalonnage.py)
SEUIL_A_VENIR_JOURS    = 14
BOUTIQUE_ID            = 1

NUISIBLES_TYPES = {
    1: "Rongeurs",
    2: "Insectes volants",
    3: "Insectes rampants",
    4: "Oiseaux",
}


@router.get("/taches-resume")
async def taches_resume():
    today = _date.today()
    iso_year, iso_week, _ = today.isocalendar()

    aujourd_hui: list[dict] = []
    a_venir:     list[dict] = []

    async with get_db() as db:

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
        try:
            rows = await db.execute_fetchall(
                "SELECT type_id FROM nuisibles_controles "
                "WHERE annee = ? AND semaine = ?",
                (iso_year, iso_week),
            )
            types_faits = {r[0] for r in rows}
            manquants   = [tid for tid in NUISIBLES_TYPES if tid not in types_faits]
            if manquants:
                noms = ", ".join(NUISIBLES_TYPES[t] for t in manquants)
                aujourd_hui.append({
                    "code":    "nuisibles",
                    "libelle": "Contrôle nuisibles",
                    "url":     "/nuisibles.html",
                    "icone":   "🪤",
                    "etat":    "a_faire",
                    "detail":  f"Semaine {iso_week} — manque : {noms}",
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
            seuil_rouge  = seuils.get("dlc_alerte_rouge_jours",  1)
            seuil_orange = seuils.get("dlc_alerte_orange_jours", 3)

            # Plage : on remonte jusqu'à 30 jours en arrière pour couvrir les DLC
            # déjà dépassées encore ouvertes (devenir non saisi)
            date_debut = (today - timedelta(days=30)).isoformat()
            date_fin   = (today + timedelta(days=seuil_orange)).isoformat()

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
                elif jours <= seuil_orange:
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
                    "detail":  f"{n_surveiller} produit(s) — DLC dans ≤ {seuil_orange} j",
                })
        except Exception as exc:
            logger.warning("hub résumé dlc : %s", exc)

    return {
        "date":        today.isoformat(),
        "aujourd_hui": aujourd_hui,
        "a_venir":     a_venir,
    }

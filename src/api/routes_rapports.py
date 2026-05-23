import csv
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Libellés métier réutilisés dans le rapport interactif
_TYPES_NUISIBLES = {
    1: "Rongeurs",
    2: "Insectes volants",
    3: "Insectes rampants",
    4: "Oiseaux",
}

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from src.database import (
    get_db, get_rapport, create_rapport, get_boutique, CSV_EXPORT_DIR,
    get_enceintes, get_releves, get_alertes_enceinte,
)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

router = APIRouter(prefix="/api/rapports", tags=["rapports"])


def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError(f"Type non sérialisable : {type(o)}")


class RapportDemande(BaseModel):
    boutique_id: int
    type: str = "journalier"          # "journalier" | "mensuel"
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None


@router.post("/generer", status_code=202)
async def generer_rapport(data: RapportDemande):
    from src.report_generator import generer

    now = datetime.now(timezone.utc).date()

    if data.type == "journalier":
        debut = data.date_debut or (now - timedelta(days=1))
        fin   = data.date_fin   or debut
    elif data.type == "mensuel":
        debut = data.date_debut or date(now.year, now.month, 1)
        fin   = data.date_fin   or now
    else:
        raise HTTPException(400, "type doit être 'journalier' ou 'mensuel'")

    async with get_db() as db:
        boutique = await get_boutique(db, data.boutique_id)
        if not boutique:
            raise HTTPException(404, "Boutique introuvable")

        rapport_id = await generer(db, data.boutique_id, data.type, debut, fin)

    return {"rapport_id": rapport_id, "statut": "généré"}


@router.get("/interactif/{boutique_id}", response_class=HTMLResponse)
async def rapport_interactif(boutique_id: int, jours: int = 90):
    """
    Retourne une page HTML interactive autonome avec les données
    des N derniers jours embarquées (graphiques dynamiques, filtres,
    export PDF via navigateur).
    """
    jours = max(1, min(jours, 365))
    depuis = datetime.now(timezone.utc) - timedelta(days=jours)

    async with get_db() as db:
        boutique = await get_boutique(db, boutique_id)
        if not boutique:
            raise HTTPException(404, "Boutique introuvable")

        enceintes = await get_enceintes(db, boutique_id)

        releves_total: list[dict] = []
        alertes_total: list[dict] = []
        for enc in enceintes:
            r = await get_releves(db, enc["id"], depuis)
            for rel in r:
                releves_total.append({
                    "enceinte_id": rel["enceinte_id"],
                    "horodatage":  rel["horodatage"],
                    "temperature": rel.get("temperature"),
                    "humidite":    rel.get("humidite"),
                })
            a = await get_alertes_enceinte(db, enc["id"], depuis)
            for al in a:
                alertes_total.append({
                    "id":          al["id"],
                    "enceinte_id": al["enceinte_id"],
                    "type":        al["type"],
                    "debut":       al["debut"],
                    "fin":         al.get("fin"),
                    "valeur":      al.get("valeur"),
                    "seuil":       al.get("seuil"),
                })

        depuis_iso = depuis.date().isoformat()

        nettoyage = await _collecter_nettoyage(db, depuis_iso)
        nuisibles = await _collecter_nuisibles(db, depuis)
        etalonnage = await _collecter_etalonnage(db, depuis_iso)

    template = _jinja_env.get_template("rapport_interactif.html")
    html = template.render(
        boutique=boutique,
        enceintes=enceintes,
        genere_le=datetime.now().strftime("%d/%m/%Y à %H:%M"),
        boutique_json=json.dumps(boutique, default=_json_default),
        enceintes_json=json.dumps(enceintes, default=_json_default),
        releves_json=json.dumps(releves_total, default=_json_default),
        alertes_json=json.dumps(alertes_total, default=_json_default),
        nettoyage_json=json.dumps(nettoyage, default=_json_default),
        nuisibles_json=json.dumps(nuisibles, default=_json_default),
        etalonnage_json=json.dumps(etalonnage, default=_json_default),
    )
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# Collecte des données complémentaires pour le rapport inspecteur
# ---------------------------------------------------------------------------

_JOURS_NOMS_RAPPORT = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


def _lundi_semaine_iso(annee_iso: int, semaine: int) -> date:
    """Renvoie le lundi de la semaine ISO donnée (le 4 janvier est toujours en S1)."""
    jan4 = date(annee_iso, 1, 4)
    monday_sem1 = jan4 - timedelta(days=jan4.isoweekday() - 1)
    return monday_sem1 + timedelta(weeks=semaine - 1)


async def _collecter_nettoyage(db, depuis_iso: str) -> dict:
    """
    Historique du plan de nettoyage sur la période, présenté par semaine ISO
    sous la forme d'un planning tâches × 7 jours (même format que le module).
    """
    # Plan de nettoyage (référentiel des tâches attendues), groupé par zone
    taches_rows = await db.execute_fetchall(
        "SELECT id, zone, nom_tache, frequence, methode_produit "
        "FROM taches_nettoyage ORDER BY zone, id"
    )
    plan_total = len(taches_rows)

    # Toutes les validations sur la période
    val_rows = await db.execute_fetchall(
        "SELECT date_val, tache_id, operateur FROM registre_nettoyage "
        "WHERE date_val >= ? ORDER BY date_val",
        (depuis_iso,),
    )

    # Map validations : {date_str: {tache_id: "É."}}  (initiale opérateur)
    validations: dict = {}
    jours_distincts: set = set()
    for dv, tid, op in val_rows:
        jours_distincts.add(dv)
        validations.setdefault(dv, {})
        if tid not in validations[dv]:
            validations[dv][tid] = (op[0].upper() + ".") if op else "?"

    # Semaines ISO couvertes par les validations
    semaines_couvertes: set = set()
    for dv in jours_distincts:
        d = datetime.strptime(dv, "%Y-%m-%d").date()
        iso = d.isocalendar()
        semaines_couvertes.add((iso[0], iso[1]))

    # Construire un planning par semaine (plus récente en premier)
    semaines = []
    for annee_iso, num in sorted(semaines_couvertes, reverse=True):
        monday = _lundi_semaine_iso(annee_iso, num)
        dates_sem = [monday + timedelta(days=i) for i in range(7)]
        date_strs = [d.isoformat() for d in dates_sem]

        zones: dict = {}
        nb_validations_sem = 0
        for tid, zone, nom_tache, frequence, methode in taches_rows:
            zones.setdefault(zone, [])
            vals = {}
            for ds in date_strs:
                signet = validations.get(ds, {}).get(tid)
                vals[ds] = signet
                if signet:
                    nb_validations_sem += 1
            zones[zone].append({
                "id":              tid,
                "nom_tache":       nom_tache,
                "frequence":       frequence,
                "methode_produit": methode,
                "validations":     vals,
            })

        semaines.append({
            "annee_iso":  annee_iso,
            "numero":     num,
            "dates":      date_strs,
            "jours_noms": [f"{_JOURS_NOMS_RAPPORT[i]} {dates_sem[i].day}" for i in range(7)],
            "nb_validations": nb_validations_sem,
            "zones":      [{"zone": z, "taches": t} for z, t in zones.items()],
        })

    return {
        "plan_total":    plan_total,
        "jours_valides": len(jours_distincts),
        "nb_semaines":   len(semaines),
        "semaines":      semaines,
    }


async def _collecter_nuisibles(db, depuis: datetime) -> dict:
    """
    Contrôles nuisibles couvrant la période, présentés par semaine ISO.
    Convention métier : "O" = présence/anomalie détectée, "N" = RAS (conforme).
    """
    annee_debut = depuis.year
    annee_fin = datetime.now(timezone.utc).year
    annees = list(range(annee_debut, annee_fin + 1))
    placeholders = ",".join("?" * len(annees))

    rows = await db.execute_fetchall(
        f"""
        SELECT type_id, annee, semaine, resultats, visa, date_saisie
        FROM nuisibles_controles
        WHERE annee IN ({placeholders})
        ORDER BY annee DESC, semaine DESC, type_id
        """,
        annees,
    )

    # Regrouper par (annee, semaine) → {type_id: {...}}
    par_semaine: dict = {}
    nb_anomalies = 0
    nb_controles = 0
    for type_id, annee, semaine, resultats_json, visa, date_saisie in rows:
        try:
            resultats = json.loads(resultats_json) if resultats_json else {}
        except Exception:
            resultats = {}
        # "O" = présence (anomalie). "N" = RAS.
        anomalies = [k for k, v in resultats.items() if v == "O"]
        nb_anomalies += len(anomalies)
        nb_controles += 1

        key = (annee, semaine)
        par_semaine.setdefault(key, {})[type_id] = {
            "type_id":      type_id,
            "type_nom":     _TYPES_NUISIBLES.get(type_id, f"Type {type_id}"),
            "resultats":    resultats,
            "nb_postes":    len(resultats),
            "nb_anomalies": len(anomalies),
            "visa":         visa,
            "date_saisie":  date_saisie,
        }

    # Sérialiser par semaine (plus récente en premier)
    semaines = []
    for (annee, semaine) in sorted(par_semaine, reverse=True):
        types = par_semaine[(annee, semaine)]
        anomalies_sem = sum(t["nb_anomalies"] for t in types.values())
        # Ordre fixe des types 1..4 ; n'inclure que ceux saisis
        controles = [types[tid] for tid in sorted(types)]
        semaines.append({
            "annee":        annee,
            "semaine":      semaine,
            "nb_anomalies": anomalies_sem,
            "controles":    controles,
        })

    return {
        "nb_controles": nb_controles,
        "nb_anomalies": nb_anomalies,
        "nb_semaines":  len(semaines),
        "semaines":     semaines,
    }


async def _collecter_etalonnage(db, depuis_iso: str) -> dict:
    """Historique des étalonnages de thermomètres sur la période + comparaisons."""
    from collections import defaultdict

    rows = await db.execute_fetchall(
        """
        SELECT e.id, e.reference, e.date_etalonnage, t.nom AS thermometre_nom,
               e.temperature_mesuree, e.conforme, e.action_corrective,
               e.operateur, e.commentaire
        FROM etalonnages e
        JOIN thermometres_ref t ON t.id = e.thermometre_ref_id
        WHERE e.date_etalonnage >= ?
        ORDER BY e.date_etalonnage DESC, e.created_at DESC
        """,
        (depuis_iso,),
    )

    etalonnages = []
    for r in rows:
        etalonnages.append({
            "id":                r[0],
            "reference":         r[1],
            "date_etalonnage":   r[2],
            "thermometre_nom":   r[3],
            "temperature_mesuree": r[4],
            "conforme":          r[5],
            "action_corrective": r[6],
            "operateur":         r[7],
            "commentaire":       r[8],
            "comparaisons":      [],
        })

    if etalonnages:
        ids = [e["id"] for e in etalonnages]
        placeholders = ",".join("?" * len(ids))
        comp_rows = await db.execute_fetchall(
            f"""
            SELECT etalonnage_id, enceinte_nom, temp_zigbee,
                   temp_reference, ecart, conforme
            FROM etalonnage_comparaisons
            WHERE etalonnage_id IN ({placeholders})
            ORDER BY enceinte_nom
            """,
            ids,
        )
        comps = defaultdict(list)
        for cr in comp_rows:
            comps[cr[0]].append({
                "enceinte_nom":   cr[1],
                "temp_zigbee":    cr[2],
                "temp_reference": cr[3],
                "ecart":          cr[4],
                "conforme":       cr[5],
            })
        for e in etalonnages:
            e["comparaisons"] = comps.get(e["id"], [])

    # Statut trimestriel (dernier étalonnage tous périodes confondues)
    statut_rows = await db.execute_fetchall(
        """
        SELECT e.date_etalonnage, t.nom
        FROM etalonnages e
        JOIN thermometres_ref t ON t.id = e.thermometre_ref_id
        ORDER BY e.date_etalonnage DESC
        LIMIT 1
        """
    )
    DELAI_JOURS = 92
    statut = None
    if statut_rows:
        dernier = date.fromisoformat(statut_rows[0][0])
        prochain = dernier + timedelta(days=DELAI_JOURS)
        jours_restants = (prochain - date.today()).days
        statut = {
            "dernier_date":   statut_rows[0][0],
            "dernier_thermo": statut_rows[0][1],
            "prochain_date":  prochain.isoformat(),
            "jours_restants": jours_restants,
            "en_retard":      jours_restants < 0,
        }

    return {
        "nb_etalonnages": len(etalonnages),
        "etalonnages":    etalonnages,
        "statut":         statut,
    }


@router.get("/{rapport_id}/pdf")
async def telecharger_rapport(rapport_id: int):
    async with get_db() as db:
        rapport = await get_rapport(db, rapport_id)

    if not rapport:
        raise HTTPException(404, "Rapport introuvable")
    if not rapport.get("fichier_path"):
        raise HTTPException(404, "Fichier PDF non encore généré")

    from pathlib import Path
    path = Path(rapport["fichier_path"])
    if not path.exists():
        raise HTTPException(404, "Fichier PDF introuvable sur le disque")

    # Déterminer le media type basé sur l'extension
    media_type = "application/pdf"
    if path.suffix.lower() == ".html":
        media_type = "text/html; charset=utf-8"

    return FileResponse(
        str(path),
        media_type=media_type,
        filename=path.name,
    )


# ---------------------------------------------------------------------------
# Routes CSV
# ---------------------------------------------------------------------------

@router.get("/csv/disponibles")
async def csv_disponibles():
    """Liste les jours et sondes pour lesquels des CSV existent."""
    jours: set[str] = set()
    sondes: set[str] = set()
    if CSV_EXPORT_DIR.exists():
        for f in CSV_EXPORT_DIR.glob("**/*.csv"):
            m = re.search(r"(\d{4}-\d{2}-\d{2})$", f.stem)
            if m:
                jours.add(m.group(1))
                sondes.add(f.parent.name)
    return {"jours": sorted(jours, reverse=True), "sondes": sorted(sondes)}


@router.get("/csv/rapport/{jour}")
async def rapport_csv_jour(jour: str):
    """Lit les CSV d'un jour et retourne les statistiques par sonde."""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", jour):
        raise HTTPException(400, "Format de date invalide (YYYY-MM-DD)")

    resultats = []
    if not CSV_EXPORT_DIR.exists():
        return {"jour": jour, "sondes": resultats}

    for csv_file in sorted(CSV_EXPORT_DIR.glob(f"**/*_{jour}.csv")):
        temperatures: list[float] = []
        humidites: list[float] = []
        nb_releves = 0
        try:
            with csv_file.open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    nb_releves += 1
                    try:
                        temperatures.append(float(row["temperature"]))
                    except (ValueError, KeyError):
                        pass
                    try:
                        h = row.get("humidite")
                        if h and h.strip() not in ("", "None"):
                            humidites.append(float(h))
                    except (ValueError, KeyError):
                        pass
        except Exception:
            continue

        if not temperatures:
            continue

        resultats.append({
            "sonde":      csv_file.parent.name,
            "nb_releves": nb_releves,
            "temp_min":   round(min(temperatures), 1),
            "temp_max":   round(max(temperatures), 1),
            "temp_moy":   round(sum(temperatures) / len(temperatures), 1),
            "hum_min":    round(min(humidites), 1) if humidites else None,
            "hum_max":    round(max(humidites), 1) if humidites else None,
            "fichier":    csv_file.name,
        })

    return {"jour": jour, "sondes": resultats}


@router.get("/csv/telecharger/{sonde}/{jour}")
async def telecharger_csv(sonde: str, jour: str):
    """Télécharge le CSV d'une sonde pour un jour donné."""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", jour):
        raise HTTPException(400, "Format de date invalide")
    nom_safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in sonde)
    fichier = CSV_EXPORT_DIR / nom_safe / f"{nom_safe}_{jour}.csv"
    if not fichier.exists():
        raise HTTPException(404, "CSV introuvable")
    return FileResponse(str(fichier), media_type="text/csv", filename=fichier.name)


# ---------------------------------------------------------------------------

@router.get("/debug/list")
async def debug_list_rapports():
    """Debug endpoint pour voir tous les rapports."""
    from pathlib import Path
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM rapports ORDER BY id DESC LIMIT 10")
        rows = await cursor.fetchall()

    result = []
    for r in rows:
        d = dict(r)
        if d.get("fichier_path"):
            path = Path(d["fichier_path"])
            d["file_exists"] = path.exists()
            d["file_size"] = path.stat().st_size if path.exists() else None
        result.append(d)
    return result


@router.get("")
async def liste_rapports(boutique_id: Optional[int] = None):
    async with get_db() as db:
        if boutique_id:
            cursor = await db.execute(
                "SELECT * FROM rapports WHERE boutique_id = ? ORDER BY created_at DESC",
                (boutique_id,),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM rapports ORDER BY created_at DESC LIMIT 50"
            )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]

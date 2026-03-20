import csv
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.database import get_db, get_rapport, create_rapport, get_boutique, CSV_EXPORT_DIR

router = APIRouter(prefix="/api/rapports", tags=["rapports"])


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

    return FileResponse(
        str(path),
        media_type="application/pdf",
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

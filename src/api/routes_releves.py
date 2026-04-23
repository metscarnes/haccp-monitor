import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.database import get_db, get_enceinte, get_releves, get_stats_releves

router = APIRouter(prefix="/api/enceintes", tags=["relevés"])


def _parse_dt(s: Optional[str], defaut: datetime) -> datetime:
    if not s:
        return defaut
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, f"Date invalide : {s!r} (format attendu : ISO 8601)")


@router.get("/{enceinte_id}/releves")
async def historique_releves(
    enceinte_id: int,
    from_: Optional[str] = Query(None, alias="from", description="ISO 8601"),
    to: Optional[str] = Query(None, description="ISO 8601"),
    periode: Optional[str] = Query(None, description="24h | 7j | 30j"),
):
    now = datetime.now(timezone.utc)

    # Raccourcis période
    if periode:
        if periode not in ["24h", "7j", "30j"]:
            raise HTTPException(400, "periode doit être 24h, 7j ou 30j")

        if periode == "24h":
            # 24h = jour courant entier (0h00 à 23h59)
            depuis = now.replace(hour=0, minute=0, second=0, microsecond=0)
            jusqu_a = depuis + timedelta(days=1) - timedelta(microseconds=1)
        else:
            # 7j, 30j = derniers N jours
            mapping = {"7j": timedelta(days=7), "30j": timedelta(days=30)}
            depuis = now - mapping[periode]
            jusqu_a = now
    else:
        depuis  = _parse_dt(from_, now - timedelta(hours=24))
        jusqu_a = _parse_dt(to, now)

    async with get_db() as db:
        enc = await get_enceinte(db, enceinte_id)
        if not enc:
            raise HTTPException(404, "Enceinte introuvable")
        releves = await get_releves(db, enceinte_id, depuis, jusqu_a)

    return {
        "enceinte_id": enceinte_id,
        "depuis": depuis.isoformat(),
        "jusqu_a": jusqu_a.isoformat(),
        "nb_releves": len(releves),
        "releves": releves,
    }


@router.get("/{enceinte_id}/releves/stats")
async def stats_releves(
    enceinte_id: int,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    periode: Optional[str] = Query(None, description="24h | 7j | 30j"),
):
    now = datetime.now(timezone.utc)
    if periode:
        if periode == "24h":
            # 24h = jour courant entier (0h00 à 23h59)
            depuis = now.replace(hour=0, minute=0, second=0, microsecond=0)
            jusqu_a = depuis + timedelta(days=1) - timedelta(microseconds=1)
        else:
            # 7j, 30j = derniers N jours
            mapping = {"7j": timedelta(days=7), "30j": timedelta(days=30)}
            depuis  = now - mapping.get(periode, timedelta(hours=24))
            jusqu_a = now
    else:
        depuis  = _parse_dt(from_, now - timedelta(hours=24))
        jusqu_a = _parse_dt(to, now)

    async with get_db() as db:
        enc = await get_enceinte(db, enceinte_id)
        if not enc:
            raise HTTPException(404, "Enceinte introuvable")
        stats = await get_stats_releves(db, enceinte_id, depuis, jusqu_a)

    return {"enceinte_id": enceinte_id, "periode": {"depuis": depuis.isoformat(), "jusqu_a": jusqu_a.isoformat()}, **stats}


@router.get("/{enceinte_id}/releves/export.csv")
async def exporter_csv(
    enceinte_id: int,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    periode: Optional[str] = Query(None),
):
    now = datetime.now(timezone.utc)
    if periode:
        if periode == "24h":
            # 24h = jour courant entier (0h00 à 23h59)
            depuis = now.replace(hour=0, minute=0, second=0, microsecond=0)
            jusqu_a = depuis + timedelta(days=1) - timedelta(microseconds=1)
        else:
            # 7j, 30j = derniers N jours
            mapping = {"7j": timedelta(days=7), "30j": timedelta(days=30)}
            depuis  = now - mapping.get(periode, timedelta(hours=24))
            jusqu_a = now
    else:
        depuis  = _parse_dt(from_, now - timedelta(hours=24))
        jusqu_a = _parse_dt(to, now)

    async with get_db() as db:
        enc = await get_enceinte(db, enceinte_id)
        if not enc:
            raise HTTPException(404, "Enceinte introuvable")
        releves = await get_releves(db, enceinte_id, depuis, jusqu_a)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["horodatage", "temperature_c", "humidite_pct", "batterie_pct", "qualite_signal"])
    for r in releves:
        writer.writerow([r["horodatage"], r["temperature"], r["humidite"], r["batterie"], r["qualite_signal"]])

    output.seek(0)
    nom_fichier = f"releves_{enc['nom'].replace(' ', '_')}_{depuis.date()}__{jusqu_a.date()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )

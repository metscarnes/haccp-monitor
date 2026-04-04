"""
routes_ouvertures.py — Module Ouvertures produits

POST   /api/ouvertures                  → créer une ouverture (multipart : photo + produit_id + personnel_id)
GET    /api/ouvertures                  → liste (filtres : produit_id, date_debut, date_fin, limit)
GET    /api/ouvertures/{id}/photo       → servir le fichier photo
GET    /api/ouvertures/suggestions      → autocomplete produits (réceptions récentes en premier)
"""

import io
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from PIL import Image, ImageOps

from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ouvertures"])

BASE_DIR    = Path(__file__).parent.parent.parent
PHOTOS_DIR  = BASE_DIR / "data" / "photos" / "ouvertures"

# Créer le dossier au chargement du module (idempotent)
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

MAX_SIDE    = 1280
JPEG_QUALITY = 80


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compress_photo(raw_bytes: bytes) -> bytes:
    """Applique exif_transpose, resize à MAX_SIDE et compression JPEG 80."""
    img = Image.open(io.BytesIO(raw_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_SIDE:
        if w >= h:
            new_w = MAX_SIDE
            new_h = int(h * MAX_SIDE / w)
        else:
            new_h = MAX_SIDE
            new_w = int(w * MAX_SIDE / h)
        img = img.resize((new_w, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# POST /api/ouvertures
# ---------------------------------------------------------------------------

@router.post("/ouvertures", status_code=201)
async def creer_ouverture(
    photo: UploadFile = File(...),
    produit_id: int = Form(...),
    personnel_id: int = Form(...),
    reception_ligne_id: Optional[int] = Form(None),
):
    raw = await photo.read()
    jpeg_bytes = _compress_photo(raw)

    async with get_db() as db:
        # Vérifier que le produit et le personnel existent
        row = await db.execute("SELECT id FROM produits WHERE id = ?", (produit_id,))
        if not await row.fetchone():
            raise HTTPException(status_code=404, detail="produit_id introuvable")

        row = await db.execute("SELECT id FROM personnel WHERE id = ?", (personnel_id,))
        if not await row.fetchone():
            raise HTTPException(status_code=404, detail="personnel_id introuvable")

        source = "catalogue"
        if reception_ligne_id is not None:
            row = await db.execute(
                "SELECT id FROM reception_lignes WHERE id = ?", (reception_ligne_id,)
            )
            if not await row.fetchone():
                raise HTTPException(status_code=404, detail="reception_ligne_id introuvable")
            source = "reception"

        # Insérer d'abord pour obtenir l'id
        cursor = await db.execute(
            """
            INSERT INTO ouvertures (produit_id, personnel_id, photo_filename, source, reception_ligne_id)
            VALUES (?, ?, '', ?, ?)
            """,
            (produit_id, personnel_id, source, reception_ligne_id),
        )
        ouverture_id = cursor.lastrowid

        # Construire le nom de fichier avec l'id
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"OUV-{now_str}-{ouverture_id}.jpg"
        filepath = PHOTOS_DIR / filename

        # Sauvegarder sur disque
        filepath.write_bytes(jpeg_bytes)

        # Mettre à jour le nom de fichier en base
        await db.execute(
            "UPDATE ouvertures SET photo_filename = ? WHERE id = ?",
            (filename, ouverture_id),
        )
        await db.commit()

        # Lire l'enregistrement créé
        cursor = await db.execute(
            "SELECT * FROM ouvertures WHERE id = ?", (ouverture_id,)
        )
        row = await cursor.fetchone()
        return dict(row)


# ---------------------------------------------------------------------------
# GET /api/ouvertures/suggestions  (doit être AVANT /{id}/photo)
# ---------------------------------------------------------------------------

@router.get("/ouvertures/suggestions")
async def suggestions_ouvertures(
    q: Optional[str] = Query(None, description="Filtre sur nom ou code_unique"),
):
    """
    Retourne les produits matière_première pour l'autocomplete :
    1. Produits issus de réceptions des 21 derniers jours (triés par date DESC, dédupliqués)
    2. Reste du catalogue matière_première
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=21)).strftime("%Y-%m-%d %H:%M:%S")

    like = f"%{q}%" if q else None

    async with get_db() as db:
        # --- Produits récents depuis réceptions ---
        params_recent: list = [cutoff]
        filter_sql = ""
        if like:
            filter_sql = "AND (p.nom LIKE ? OR p.code_unique LIKE ?)"
            params_recent += [like, like]

        cursor = await db.execute(
            f"""
            SELECT
                p.id        AS produit_id,
                p.nom,
                p.code_unique,
                p.espece,
                MAX(r.date_reception) AS last_reception
            FROM reception_lignes rl
            JOIN receptions r ON r.id = rl.reception_id
            JOIN produits p   ON p.id = rl.produit_id
            WHERE r.date_reception >= ?
              AND p.categorie = 'matiere_premiere'
              {filter_sql}
            GROUP BY p.id
            ORDER BY last_reception DESC
            """,
            params_recent,
        )
        recent_rows = await cursor.fetchall()
        recent_ids = {row["produit_id"] for row in recent_rows}

        # --- Reste du catalogue ---
        params_cat: list = []
        filter_cat_sql = ""
        if like:
            filter_cat_sql = "AND (nom LIKE ? OR code_unique LIKE ?)"
            params_cat += [like, like]

        cursor = await db.execute(
            f"""
            SELECT id AS produit_id, nom, code_unique, espece
            FROM produits
            WHERE categorie = 'matiere_premiere'
              {filter_cat_sql}
            ORDER BY nom ASC
            """,
            params_cat,
        )
        all_rows = await cursor.fetchall()

    results = [
        {
            "produit_id": row["produit_id"],
            "nom": row["nom"],
            "code_unique": row["code_unique"],
            "espece": row["espece"],
            "is_recent": True,
            "last_reception": row["last_reception"],
        }
        for row in recent_rows
    ]
    for row in all_rows:
        if row["produit_id"] not in recent_ids:
            results.append({
                "produit_id": row["produit_id"],
                "nom": row["nom"],
                "code_unique": row["code_unique"],
                "espece": row["espece"],
                "is_recent": False,
                "last_reception": None,
            })

    return results


# ---------------------------------------------------------------------------
# GET /api/ouvertures
# ---------------------------------------------------------------------------

@router.get("/ouvertures")
async def lister_ouvertures(
    produit_id:  Optional[int] = Query(None),
    date_debut:  Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_fin:    Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit:       int           = Query(50, ge=1, le=500),
):
    conditions = []
    params: list = []

    if produit_id is not None:
        conditions.append("o.produit_id = ?")
        params.append(produit_id)
    if date_debut:
        conditions.append("o.timestamp >= ?")
        params.append(f"{date_debut} 00:00:00")
    if date_fin:
        conditions.append("o.timestamp <= ?")
        params.append(f"{date_fin} 23:59:59")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    async with get_db() as db:
        cursor = await db.execute(
            f"""
            SELECT
                o.id,
                o.produit_id,
                p.nom          AS produit_nom,
                p.code_unique,
                o.personnel_id,
                per.prenom     AS personnel_prenom,
                o.photo_filename,
                o.timestamp,
                o.source,
                o.reception_ligne_id
            FROM ouvertures o
            JOIN produits  p   ON p.id   = o.produit_id
            JOIN personnel per ON per.id = o.personnel_id
            {where}
            ORDER BY o.timestamp DESC
            LIMIT ?
            """,
            params + [limit],
        )
        rows = await cursor.fetchall()

    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# GET /api/ouvertures/{id}/photo
# ---------------------------------------------------------------------------

@router.get("/ouvertures/{ouverture_id}/photo")
async def get_photo_ouverture(ouverture_id: int):
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT photo_filename FROM ouvertures WHERE id = ?", (ouverture_id,)
        )
        row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Ouverture introuvable")

    filepath = PHOTOS_DIR / row["photo_filename"]
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Fichier photo introuvable")

    return FileResponse(str(filepath), media_type="image/jpeg")

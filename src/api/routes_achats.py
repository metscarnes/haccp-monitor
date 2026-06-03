"""
routes_achats.py — Module Achats : Fournisseurs, Catalogue, Commandes

GET    /api/achats/fournisseurs                          → liste fournisseurs enrichis
POST   /api/achats/fournisseurs                          → créer fournisseur
PUT    /api/achats/fournisseurs/{id}                     → modifier fournisseur

GET    /api/achats/catalogue                             → catalogue fournisseur (filtres)
GET    /api/achats/catalogue/{id}                        → détail article
POST   /api/achats/catalogue                             → créer article
PUT    /api/achats/catalogue/{id}                        → modifier article
DELETE /api/achats/catalogue/{id}                        → désactiver article
POST   /api/achats/catalogue/import                      → import Excel
GET    /api/achats/catalogue/template                    → télécharger template Excel

GET    /api/achats/commandes                             → liste commandes (filtres)
GET    /api/achats/commandes/{id}                        → détail commande + lignes
POST   /api/achats/commandes                             → créer commande
PUT    /api/achats/commandes/{id}                        → modifier commande
POST   /api/achats/commandes/{id}/envoyer                → envoyer mail fournisseur
POST   /api/achats/commandes/{id}/dupliquer              → dupliquer commande
GET    /api/achats/commandes/{id}/lignes                 → lignes de commande
POST   /api/achats/commandes/{id}/lignes                 → ajouter ligne
PUT    /api/achats/commandes/{id}/lignes/{ligne_id}      → modifier ligne
DELETE /api/achats/commandes/{id}/lignes/{ligne_id}      → supprimer ligne
"""

import io
import logging
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/achats", tags=["achats"])


# ---------------------------------------------------------------------------
# Modèles Pydantic
# ---------------------------------------------------------------------------

class FournisseurCreate(BaseModel):
    nom: str
    email_commercial: Optional[str] = None
    telephone: Optional[str] = None
    adresse: Optional[str] = None
    conditions_paiement: Optional[str] = None
    actif: Optional[bool] = True


class FournisseurUpdate(BaseModel):
    nom: Optional[str] = None
    email_commercial: Optional[str] = None
    telephone: Optional[str] = None
    adresse: Optional[str] = None
    conditions_paiement: Optional[str] = None
    actif: Optional[bool] = None


class CatalogueArticleCreate(BaseModel):
    fournisseur_id: int
    code_article: str
    designation: str
    prix_achat_ht: float
    tva_percent: Optional[float] = 5.5
    conditionnement: Optional[str] = None
    dlc_type: Optional[str] = "dlc"   # 'dlc' | 'date_abattage' | 'no_dlc'
    dlc_jours: Optional[int] = None


class CatalogueArticleUpdate(BaseModel):
    designation: Optional[str] = None
    prix_achat_ht: Optional[float] = None
    tva_percent: Optional[float] = None
    conditionnement: Optional[str] = None
    dlc_type: Optional[str] = None
    dlc_jours: Optional[int] = None
    actif: Optional[bool] = None


class CommandeLigneCreate(BaseModel):
    catalogue_fournisseur_id: Optional[int] = None
    code_article: str
    designation: str
    prix_unitaire_ht: float
    quantite_commandee: float
    unite: Optional[str] = "kg"
    commentaire_ligne: Optional[str] = None


class CommandeLigneUpdate(BaseModel):
    quantite_commandee: Optional[float] = None
    prix_unitaire_ht: Optional[float] = None
    unite: Optional[str] = None
    commentaire_ligne: Optional[str] = None


class CommandeCreate(BaseModel):
    fournisseur_id: int
    date_commande: Optional[str] = None
    date_livraison_prevue: Optional[str] = None
    commentaire: Optional[str] = None
    personnel_id: Optional[int] = None
    lignes: Optional[List[CommandeLigneCreate]] = []


class CommandeUpdate(BaseModel):
    date_livraison_prevue: Optional[str] = None
    statut: Optional[str] = None
    commentaire: Optional[str] = None


# ---------------------------------------------------------------------------
# Fournisseurs
# ---------------------------------------------------------------------------

@router.get("/fournisseurs")
async def get_fournisseurs_achats(actif_only: bool = Query(True)):
    async with get_db() as db:
        q = "SELECT * FROM fournisseurs WHERE boutique_id = 1"
        if actif_only:
            q += " AND actif = 1"
        q += " ORDER BY nom"
        cur = await db.execute(q)
        rows = await cur.fetchall()
        fournisseurs = [dict(r) for r in rows]

        # Ajouter le nombre d'articles catalogue pour chaque fournisseur
        for f in fournisseurs:
            cur2 = await db.execute(
                "SELECT COUNT(*) FROM catalogue_fournisseur WHERE fournisseur_id = ? AND actif = 1",
                (f["id"],)
            )
            f["nb_articles"] = (await cur2.fetchone())[0]

        return fournisseurs


@router.post("/fournisseurs", status_code=201)
async def create_fournisseur_achats(body: FournisseurCreate):
    async with get_db() as db:
        cur = await db.execute(
            """INSERT INTO fournisseurs (boutique_id, nom, email_commercial, telephone, adresse, conditions_paiement, actif)
               VALUES (1, ?, ?, ?, ?, ?, ?)""",
            (body.nom, body.email_commercial, body.telephone, body.adresse, body.conditions_paiement, 1 if body.actif else 0)
        )
        await db.commit()
        fid = cur.lastrowid
        cur2 = await db.execute("SELECT * FROM fournisseurs WHERE id = ?", (fid,))
        return dict(await cur2.fetchone())


@router.put("/fournisseurs/{fid}")
async def update_fournisseur_achats(fid: int, body: FournisseurUpdate):
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM fournisseurs WHERE id = ?", (fid,))
        existing = await cur.fetchone()
        if not existing:
            raise HTTPException(404, "Fournisseur introuvable")

        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        if not fields:
            return dict(existing)

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [fid]
        await db.execute(f"UPDATE fournisseurs SET {set_clause} WHERE id = ?", values)
        await db.commit()

        cur2 = await db.execute("SELECT * FROM fournisseurs WHERE id = ?", (fid,))
        return dict(await cur2.fetchone())


# ---------------------------------------------------------------------------
# Catalogue fournisseur
# ---------------------------------------------------------------------------

@router.get("/catalogue")
async def get_catalogue(
    fournisseur_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    actif_only: bool = Query(True),
):
    async with get_db() as db:
        sql = """
            SELECT c.*, f.nom AS fournisseur_nom
            FROM catalogue_fournisseur c
            JOIN fournisseurs f ON f.id = c.fournisseur_id
            WHERE f.boutique_id = 1
        """
        params = []
        if fournisseur_id:
            sql += " AND c.fournisseur_id = ?"
            params.append(fournisseur_id)
        if actif_only:
            sql += " AND c.actif = 1"
        if q:
            sql += " AND (c.designation LIKE ? OR c.code_article LIKE ?)"
            params += [f"%{q}%", f"%{q}%"]
        sql += " ORDER BY f.nom, c.designation"
        cur = await db.execute(sql, params)
        return [dict(r) for r in await cur.fetchall()]


@router.get("/catalogue/template")
async def download_template():
    """Télécharger le template Excel d'import catalogue fournisseur."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        raise HTTPException(500, "openpyxl requis pour générer le template")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Catalogue Fournisseur"

    headers = [
        "fournisseur_nom", "code_article", "designation",
        "prix_achat_ht", "tva_percent", "conditionnement",
        "dlc_type", "dlc_jours"
    ]
    notes = [
        "Nom exact du fournisseur (doit exister dans l'app)",
        "Référence article fournisseur (ex: BF-250G)",
        "Désignation complète du produit",
        "Prix d'achat HT en euros (ex: 12.50)",
        "Taux TVA en % (5.5 ou 20)",
        "Ex: Carton 4kg / Carcasse / Barquette x20",
        "dlc | date_abattage | no_dlc",
        "Nombre de jours (si dlc_type = dlc)"
    ]
    examples = [
        "Fournisseur A", "BF-250G", "Filet de boeuf",
        "12.50", "5.5", "Carton 4kg", "dlc", "3"
    ]

    header_fill = PatternFill("solid", fgColor="2D7D46")
    note_fill   = PatternFill("solid", fgColor="E8F5E9")

    for col, (h, n, e) in enumerate(zip(headers, notes, examples), 1):
        # Ligne 1 : en-têtes
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        # Ligne 2 : notes
        note_cell = ws.cell(row=2, column=col, value=n)
        note_cell.fill = note_fill
        note_cell.font = Font(italic=True, size=9)
        # Ligne 3 : exemple
        ws.cell(row=3, column=col, value=e)
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 20

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=template_catalogue_fournisseur.xlsx"}
    )


@router.post("/catalogue/import")
async def import_catalogue(fichier: bytes = None):
    """Import Excel catalogue fournisseur — voir /catalogue/template pour le format."""
    raise HTTPException(501, "Utiliser POST multipart/form-data avec champ 'fichier'")


@router.post("/catalogue/import/xlsx", status_code=200)
async def import_catalogue_xlsx(fichier: bytes):
    from fastapi import UploadFile, File
    raise HTTPException(501, "Route implémentée via form upload — voir import_catalogue_form")


from fastapi import UploadFile, File

@router.post("/catalogue/import/upload", status_code=200)
async def import_catalogue_upload(fichier: UploadFile = File(...)):
    """Import Excel catalogue fournisseur."""
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(500, "openpyxl requis")

    content = await fichier.read()
    wb = openpyxl.load_workbook(io.BytesIO(content))
    ws = wb.active

    headers = [str(ws.cell(row=1, column=c).value or "").strip().lower() for c in range(1, ws.max_column + 1)]
    required = {"fournisseur_nom", "code_article", "designation", "prix_achat_ht"}
    missing = required - set(headers)
    if missing:
        raise HTTPException(400, f"Colonnes manquantes : {missing}")

    def col(row, name):
        idx = headers.index(name) + 1
        v = ws.cell(row=row, column=idx).value
        return str(v).strip() if v is not None else ""

    stats = {"crees": 0, "mis_a_jour": 0, "erreurs": []}

    async with get_db() as db:
        for row_num in range(3, ws.max_row + 1):  # ligne 2 = notes, données dès ligne 3
            nom_fourn = col(row_num, "fournisseur_nom")
            code = col(row_num, "code_article")
            if not nom_fourn or not code:
                continue

            # Trouver le fournisseur
            cur = await db.execute(
                "SELECT id FROM fournisseurs WHERE boutique_id = 1 AND LOWER(TRIM(nom)) = LOWER(TRIM(?))",
                (nom_fourn,)
            )
            fourn = await cur.fetchone()
            if not fourn:
                stats["erreurs"].append(f"Ligne {row_num} : fournisseur '{nom_fourn}' introuvable")
                continue

            designation = col(row_num, "designation")
            try:
                prix = float(col(row_num, "prix_achat_ht") or 0)
            except ValueError:
                stats["erreurs"].append(f"Ligne {row_num} : prix invalide")
                continue

            tva_raw = col(row_num, "tva_percent") if "tva_percent" in headers else "5.5"
            try:
                tva = float(tva_raw or 5.5)
            except ValueError:
                tva = 5.5

            conditionnement = col(row_num, "conditionnement") if "conditionnement" in headers else None
            dlc_type = col(row_num, "dlc_type") if "dlc_type" in headers else "dlc"
            dlc_jours_raw = col(row_num, "dlc_jours") if "dlc_jours" in headers else None
            try:
                dlc_jours = int(dlc_jours_raw) if dlc_jours_raw else None
            except ValueError:
                dlc_jours = None

            # UPSERT
            cur2 = await db.execute(
                "SELECT id FROM catalogue_fournisseur WHERE fournisseur_id = ? AND code_article = ?",
                (fourn["id"], code)
            )
            existing = await cur2.fetchone()
            if existing:
                await db.execute(
                    """UPDATE catalogue_fournisseur
                       SET designation=?, prix_achat_ht=?, tva_percent=?, conditionnement=?,
                           dlc_type=?, dlc_jours=?, date_maj=CURRENT_TIMESTAMP
                       WHERE id=?""",
                    (designation, prix, tva, conditionnement or None, dlc_type or "dlc", dlc_jours, existing["id"])
                )
                stats["mis_a_jour"] += 1
            else:
                await db.execute(
                    """INSERT INTO catalogue_fournisseur
                       (fournisseur_id, code_article, designation, prix_achat_ht, tva_percent, conditionnement, dlc_type, dlc_jours)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (fourn["id"], code, designation, prix, tva, conditionnement or None, dlc_type or "dlc", dlc_jours)
                )
                stats["crees"] += 1

        await db.commit()

    return stats


@router.get("/catalogue/{article_id}")
async def get_article(article_id: int):
    async with get_db() as db:
        cur = await db.execute(
            "SELECT c.*, f.nom AS fournisseur_nom FROM catalogue_fournisseur c JOIN fournisseurs f ON f.id = c.fournisseur_id WHERE c.id = ?",
            (article_id,)
        )
        row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Article introuvable")
        return dict(row)


@router.post("/catalogue", status_code=201)
async def create_article(body: CatalogueArticleCreate):
    async with get_db() as db:
        cur_f = await db.execute("SELECT id FROM fournisseurs WHERE id = ? AND boutique_id = 1", (body.fournisseur_id,))
        if not await cur_f.fetchone():
            raise HTTPException(404, "Fournisseur introuvable")

        cur_dup = await db.execute(
            "SELECT id FROM catalogue_fournisseur WHERE fournisseur_id = ? AND code_article = ?",
            (body.fournisseur_id, body.code_article)
        )
        if await cur_dup.fetchone():
            raise HTTPException(409, f"Code article '{body.code_article}' déjà existant pour ce fournisseur")

        cur = await db.execute(
            """INSERT INTO catalogue_fournisseur
               (fournisseur_id, code_article, designation, prix_achat_ht, tva_percent, conditionnement, dlc_type, dlc_jours)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (body.fournisseur_id, body.code_article, body.designation, body.prix_achat_ht,
             body.tva_percent, body.conditionnement, body.dlc_type, body.dlc_jours)
        )
        await db.commit()
        cur2 = await db.execute("SELECT * FROM catalogue_fournisseur WHERE id = ?", (cur.lastrowid,))
        return dict(await cur2.fetchone())


@router.put("/catalogue/{article_id}")
async def update_article(article_id: int, body: CatalogueArticleUpdate):
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM catalogue_fournisseur WHERE id = ?", (article_id,))
        if not await cur.fetchone():
            raise HTTPException(404, "Article introuvable")

        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        if not fields:
            raise HTTPException(400, "Aucun champ à modifier")

        fields["date_maj"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [article_id]
        await db.execute(f"UPDATE catalogue_fournisseur SET {set_clause} WHERE id = ?", values)
        await db.commit()

        cur2 = await db.execute("SELECT * FROM catalogue_fournisseur WHERE id = ?", (article_id,))
        return dict(await cur2.fetchone())


@router.delete("/catalogue/{article_id}", status_code=204)
async def delete_article(article_id: int):
    async with get_db() as db:
        await db.execute("UPDATE catalogue_fournisseur SET actif = 0 WHERE id = ?", (article_id,))
        await db.commit()


# ---------------------------------------------------------------------------
# Commandes
# ---------------------------------------------------------------------------

async def _generer_numero_commande(db) -> str:
    today = date.today().strftime("%Y%m%d")
    cur = await db.execute(
        "SELECT COUNT(*) FROM commandes WHERE date_commande = ?",
        (date.today().isoformat(),)
    )
    count = (await cur.fetchone())[0] + 1
    return f"CMD-{today}-{count:03d}"


async def _recalculer_total(db, commande_id: int):
    cur = await db.execute(
        "SELECT COALESCE(SUM(montant_ht), 0) FROM commande_lignes WHERE commande_id = ?",
        (commande_id,)
    )
    total = (await cur.fetchone())[0]
    await db.execute("UPDATE commandes SET montant_total_ht = ? WHERE id = ?", (total, commande_id))


@router.get("/commandes")
async def get_commandes(
    fournisseur_id: Optional[int] = Query(None),
    statut: Optional[str] = Query(None),
    limit: int = Query(50),
):
    async with get_db() as db:
        sql = """
            SELECT c.*, f.nom AS fournisseur_nom, f.email_commercial,
                   p.prenom AS personnel_prenom
            FROM commandes c
            JOIN fournisseurs f ON f.id = c.fournisseur_id
            LEFT JOIN personnel p ON p.id = c.personnel_id
            WHERE c.boutique_id = 1
        """
        params = []
        if fournisseur_id:
            sql += " AND c.fournisseur_id = ?"
            params.append(fournisseur_id)
        if statut:
            sql += " AND c.statut = ?"
            params.append(statut)
        sql += " ORDER BY c.date_commande DESC LIMIT ?"
        params.append(limit)
        cur = await db.execute(sql, params)
        commandes = [dict(r) for r in await cur.fetchall()]

        # Ajouter le nombre de lignes pour chaque commande
        for cmd in commandes:
            cur2 = await db.execute(
                "SELECT COUNT(*) FROM commande_lignes WHERE commande_id = ?", (cmd["id"],)
            )
            cmd["nb_lignes"] = (await cur2.fetchone())[0]

        return commandes


@router.get("/commandes/{commande_id}")
async def get_commande(commande_id: int):
    async with get_db() as db:
        cur = await db.execute(
            """SELECT c.*, f.nom AS fournisseur_nom, f.email_commercial, f.telephone, f.adresse,
                      p.prenom AS personnel_prenom
               FROM commandes c
               JOIN fournisseurs f ON f.id = c.fournisseur_id
               LEFT JOIN personnel p ON p.id = c.personnel_id
               WHERE c.id = ?""",
            (commande_id,)
        )
        commande = await cur.fetchone()
        if not commande:
            raise HTTPException(404, "Commande introuvable")
        result = dict(commande)

        cur2 = await db.execute(
            "SELECT * FROM commande_lignes WHERE commande_id = ? ORDER BY id",
            (commande_id,)
        )
        result["lignes"] = [dict(r) for r in await cur2.fetchall()]
        return result


@router.post("/commandes", status_code=201)
async def create_commande(body: CommandeCreate):
    async with get_db() as db:
        cur_f = await db.execute(
            "SELECT * FROM fournisseurs WHERE id = ? AND boutique_id = 1",
            (body.fournisseur_id,)
        )
        if not await cur_f.fetchone():
            raise HTTPException(404, "Fournisseur introuvable")

        numero = await _generer_numero_commande(db)
        date_cmd = body.date_commande or date.today().isoformat()

        cur = await db.execute(
            """INSERT INTO commandes (boutique_id, fournisseur_id, numero_commande, date_commande,
                                      date_livraison_prevue, commentaire, personnel_id)
               VALUES (1, ?, ?, ?, ?, ?, ?)""",
            (body.fournisseur_id, numero, date_cmd, body.date_livraison_prevue,
             body.commentaire, body.personnel_id)
        )
        await db.commit()
        commande_id = cur.lastrowid

        # Insérer les lignes si fournies
        for ligne in (body.lignes or []):
            montant = ligne.quantite_commandee * ligne.prix_unitaire_ht
            await db.execute(
                """INSERT INTO commande_lignes
                   (commande_id, catalogue_fournisseur_id, code_article, designation,
                    prix_unitaire_ht, quantite_commandee, unite, montant_ht, commentaire_ligne)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (commande_id, ligne.catalogue_fournisseur_id, ligne.code_article,
                 ligne.designation, ligne.prix_unitaire_ht, ligne.quantite_commandee,
                 ligne.unite, montant, ligne.commentaire_ligne)
            )

        await _recalculer_total(db, commande_id)
        await db.commit()

        return await get_commande(commande_id)


@router.put("/commandes/{commande_id}")
async def update_commande(commande_id: int, body: CommandeUpdate):
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM commandes WHERE id = ?", (commande_id,))
        if not await cur.fetchone():
            raise HTTPException(404, "Commande introuvable")

        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        if not fields:
            raise HTTPException(400, "Aucun champ à modifier")

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [commande_id]
        await db.execute(f"UPDATE commandes SET {set_clause} WHERE id = ?", values)
        await db.commit()

        return await get_commande(commande_id)


@router.post("/commandes/{commande_id}/lignes", status_code=201)
async def add_ligne(commande_id: int, body: CommandeLigneCreate):
    async with get_db() as db:
        cur = await db.execute("SELECT statut FROM commandes WHERE id = ?", (commande_id,))
        cmd = await cur.fetchone()
        if not cmd:
            raise HTTPException(404, "Commande introuvable")
        if cmd["statut"] not in ("brouillon",):
            raise HTTPException(400, "Impossible de modifier une commande déjà confirmée")

        montant = body.quantite_commandee * body.prix_unitaire_ht
        cur2 = await db.execute(
            """INSERT INTO commande_lignes
               (commande_id, catalogue_fournisseur_id, code_article, designation,
                prix_unitaire_ht, quantite_commandee, unite, montant_ht, commentaire_ligne)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (commande_id, body.catalogue_fournisseur_id, body.code_article, body.designation,
             body.prix_unitaire_ht, body.quantite_commandee, body.unite, montant, body.commentaire_ligne)
        )
        await _recalculer_total(db, commande_id)
        await db.commit()

        cur3 = await db.execute("SELECT * FROM commande_lignes WHERE id = ?", (cur2.lastrowid,))
        return dict(await cur3.fetchone())


@router.put("/commandes/{commande_id}/lignes/{ligne_id}")
async def update_ligne(commande_id: int, ligne_id: int, body: CommandeLigneUpdate):
    async with get_db() as db:
        cur = await db.execute(
            "SELECT * FROM commande_lignes WHERE id = ? AND commande_id = ?",
            (ligne_id, commande_id)
        )
        ligne = await cur.fetchone()
        if not ligne:
            raise HTTPException(404, "Ligne introuvable")

        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        if not fields:
            raise HTTPException(400, "Aucun champ à modifier")

        # Recalculer montant si quantité ou prix change
        qte = fields.get("quantite_commandee", ligne["quantite_commandee"])
        prix = fields.get("prix_unitaire_ht", ligne["prix_unitaire_ht"])
        fields["montant_ht"] = qte * prix

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [ligne_id]
        await db.execute(f"UPDATE commande_lignes SET {set_clause} WHERE id = ?", values)
        await _recalculer_total(db, commande_id)
        await db.commit()

        cur2 = await db.execute("SELECT * FROM commande_lignes WHERE id = ?", (ligne_id,))
        return dict(await cur2.fetchone())


@router.delete("/commandes/{commande_id}/lignes/{ligne_id}", status_code=204)
async def delete_ligne(commande_id: int, ligne_id: int):
    async with get_db() as db:
        await db.execute(
            "DELETE FROM commande_lignes WHERE id = ? AND commande_id = ?",
            (ligne_id, commande_id)
        )
        await _recalculer_total(db, commande_id)
        await db.commit()


@router.post("/commandes/{commande_id}/dupliquer", status_code=201)
async def dupliquer_commande(commande_id: int, personnel_id: Optional[int] = None):
    """Duplique une commande existante en brouillon avec les mêmes lignes."""
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM commandes WHERE id = ?", (commande_id,))
        source = await cur.fetchone()
        if not source:
            raise HTTPException(404, "Commande introuvable")

        numero = await _generer_numero_commande(db)
        cur2 = await db.execute(
            """INSERT INTO commandes (boutique_id, fournisseur_id, numero_commande, date_commande,
                                      date_livraison_prevue, commentaire, personnel_id, statut)
               VALUES (1, ?, ?, ?, ?, ?, ?, 'brouillon')""",
            (source["fournisseur_id"], numero, date.today().isoformat(),
             source["date_livraison_prevue"], source["commentaire"], personnel_id or source["personnel_id"])
        )
        await db.commit()
        new_id = cur2.lastrowid

        # Copier les lignes
        cur3 = await db.execute(
            "SELECT * FROM commande_lignes WHERE commande_id = ?", (commande_id,)
        )
        lignes = await cur3.fetchall()
        for l in lignes:
            await db.execute(
                """INSERT INTO commande_lignes
                   (commande_id, catalogue_fournisseur_id, code_article, designation,
                    prix_unitaire_ht, quantite_commandee, unite, montant_ht, commentaire_ligne)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (new_id, l["catalogue_fournisseur_id"], l["code_article"], l["designation"],
                 l["prix_unitaire_ht"], l["quantite_commandee"], l["unite"], l["montant_ht"],
                 l["commentaire_ligne"])
            )

        await _recalculer_total(db, new_id)
        await db.commit()

        return await get_commande(new_id)


class MappingCreate(BaseModel):
    commande_id: int
    reception_id: int
    personnel_id: Optional[int] = None


@router.post("/commande_receptions_mapping", status_code=201)
async def create_mapping(body: MappingCreate):
    """Lie une réception à une commande (appelé depuis le module réception)."""
    async with get_db() as db:
        try:
            await db.execute(
                """INSERT OR IGNORE INTO commande_receptions_mapping
                   (commande_id, reception_id, personnel_id)
                   VALUES (?, ?, ?)""",
                (body.commande_id, body.reception_id, body.personnel_id)
            )
            await db.commit()
        except Exception as e:
            raise HTTPException(400, str(e))
        return {"ok": True, "commande_id": body.commande_id, "reception_id": body.reception_id}


@router.post("/commandes/{commande_id}/envoyer")
async def envoyer_commande(commande_id: int):
    """Envoie le récapitulatif de commande par mail au commercial fournisseur."""
    async with get_db() as db:
        cur = await db.execute(
            """SELECT c.*, f.nom AS fournisseur_nom, f.email_commercial
               FROM commandes c JOIN fournisseurs f ON f.id = c.fournisseur_id
               WHERE c.id = ?""",
            (commande_id,)
        )
        commande = await cur.fetchone()
        if not commande:
            raise HTTPException(404, "Commande introuvable")

        if not commande["email_commercial"]:
            raise HTTPException(400, "Aucun email commercial renseigné pour ce fournisseur")

        cur2 = await db.execute(
            "SELECT * FROM commande_lignes WHERE commande_id = ? ORDER BY id",
            (commande_id,)
        )
        lignes = [dict(r) for r in await cur2.fetchall()]

        # Construire le corps du mail
        lignes_txt = "\n".join(
            f"  • {l['code_article']} — {l['designation']} : {l['quantite_commandee']} {l['unite']} "
            f"× {l['prix_unitaire_ht']:.2f}€ HT = {l['montant_ht']:.2f}€ HT"
            for l in lignes
        )
        corps = f"""Bonjour,

Veuillez trouver ci-dessous notre commande {commande['numero_commande']} du {commande['date_commande']} :

{lignes_txt}

TOTAL HT : {commande['montant_total_ht']:.2f}€

Date de livraison souhaitée : {commande['date_livraison_prevue'] or 'À définir'}

{commande['commentaire'] or ''}

Cordialement,
Au Comptoir des Lilas"""

        # Envoi mail via smtplib (config dans variables d'env)
        import os, smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "")
        from_addr = os.getenv("SMTP_FROM", smtp_user)

        if not smtp_host or not smtp_user:
            # Pas de config SMTP → retourner le contenu du mail sans l'envoyer
            return {
                "envoye": False,
                "message": "Configuration SMTP manquante (SMTP_HOST, SMTP_USER, SMTP_PASS non définis)",
                "destinataire": commande["email_commercial"],
                "sujet": f"Commande {commande['numero_commande']} — Au Comptoir des Lilas",
                "corps": corps,
            }

        msg = MIMEMultipart()
        msg["From"]    = from_addr
        msg["To"]      = commande["email_commercial"]
        msg["Subject"] = f"Commande {commande['numero_commande']} — Au Comptoir des Lilas"
        msg.attach(MIMEText(corps, "plain", "utf-8"))

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            await db.execute(
                "UPDATE commandes SET statut = 'confirmee', date_envoi_mail = CURRENT_TIMESTAMP WHERE id = ?",
                (commande_id,)
            )
            await db.commit()
            return {"envoye": True, "destinataire": commande["email_commercial"]}

        except Exception as e:
            logger.error("Erreur envoi mail commande %d : %s", commande_id, e)
            raise HTTPException(500, f"Erreur envoi mail : {e}")

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

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.routes_auth import require_admin
from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/achats", tags=["achats"])


# ---------------------------------------------------------------------------
# Modèles Pydantic
# ---------------------------------------------------------------------------

class FournisseurCreate(BaseModel):
    nom: str
    nom_commercial: Optional[str] = None
    email_commercial: Optional[str] = None
    telephone: Optional[str] = None
    adresse: Optional[str] = None
    conditions_paiement: Optional[str] = None
    delai_paiement_jours: Optional[int] = None
    jours_livraison: Optional[str] = None
    rythme_livraison: Optional[str] = None
    heure_limite_commande: Optional[str] = None
    heure_livraison: Optional[str] = None
    commentaire: Optional[str] = None
    actif: Optional[bool] = True


class FournisseurUpdate(BaseModel):
    nom: Optional[str] = None
    nom_commercial: Optional[str] = None
    email_commercial: Optional[str] = None
    telephone: Optional[str] = None
    adresse: Optional[str] = None
    conditions_paiement: Optional[str] = None
    delai_paiement_jours: Optional[int] = None
    jours_livraison: Optional[str] = None
    rythme_livraison: Optional[str] = None
    heure_limite_commande: Optional[str] = None
    heure_livraison: Optional[str] = None
    commentaire: Optional[str] = None
    actif: Optional[bool] = None


class CatalogueArticleCreate(BaseModel):
    fournisseur_id: int
    code_article: str
    designation: str
    prix_achat_ht: float
    format_prix: Optional[str] = "kg"        # 'kg' (prix au kilo) | 'colis' (prix au colis/pièce)
    qte_par_colis: Optional[float] = None     # nb de pièces par colis (brut, si format 'colis')
    poids_unitaire_kg: Optional[float] = None # poids d'une pièce en kg (brut, si format 'colis')
    tva_percent: Optional[float] = 5.5
    conditionnement: Optional[str] = None
    famille: Optional[str] = None
    sous_famille: Optional[str] = None
    dlc_type: Optional[str] = "dlc"
    produit_id: Optional[int] = None          # pont vers le produit interne (Production/FIFO)


class CatalogueArticleUpdate(BaseModel):
    fournisseur_id: Optional[int] = None
    code_article: Optional[str] = None
    designation: Optional[str] = None
    prix_achat_ht: Optional[float] = None
    format_prix: Optional[str] = None
    qte_par_colis: Optional[float] = None
    poids_unitaire_kg: Optional[float] = None
    tva_percent: Optional[float] = None
    conditionnement: Optional[str] = None
    famille: Optional[str] = None
    sous_famille: Optional[str] = None
    dlc_type: Optional[str] = None
    actif: Optional[bool] = None
    produit_id: Optional[int] = None          # pont vers le produit interne ; 0 = délier


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
# Helpers catalogue
# ---------------------------------------------------------------------------

def _normaliser_format_prix(valeur) -> str:
    """Ramène le format de prix à 'kg' ou 'colis'.

    Tolère les anciennes valeurs ('piece' → 'colis') et les libellés saisis
    par un fournisseur dans le template ('au kilo', 'au colis', 'pièce'...).
    """
    v = (str(valeur) if valeur is not None else "").strip().lower()
    if v in ("kg", "kilo", "au kilo", "kilogramme", "/kg"):
        return "kg"
    if v in ("colis", "piece", "pièce", "au colis", "carton", "unite", "unité"):
        return "colis"
    return "kg"  # défaut prudent : au kilo


def _calc_poids_colis_kg(qte_par_colis, poids_unitaire_kg):
    """Champ généré : poids total d'un colis = qte_par_colis × poids_unitaire_kg.

    Retourne None si une des deux données brutes manque (cas prix au kg, où le
    poids du colis n'est pas fixe).
    """
    try:
        if qte_par_colis in (None, "") or poids_unitaire_kg in (None, ""):
            return None
        return round(float(qte_par_colis) * float(poids_unitaire_kg), 3)
    except (TypeError, ValueError):
        return None


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
async def create_fournisseur_achats(body: FournisseurCreate, _=Depends(require_admin)):
    async with get_db() as db:
        cur = await db.execute(
            """INSERT INTO fournisseurs
               (boutique_id, nom, nom_commercial, email_commercial, telephone, adresse,
                conditions_paiement, delai_paiement_jours, jours_livraison,
                rythme_livraison, heure_limite_commande, heure_livraison,
                commentaire, actif)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (body.nom, body.nom_commercial, body.email_commercial, body.telephone, body.adresse,
             body.conditions_paiement, body.delai_paiement_jours, body.jours_livraison,
             body.rythme_livraison, body.heure_limite_commande, body.heure_livraison,
             body.commentaire, 1 if body.actif else 0)
        )
        await db.commit()
        fid = cur.lastrowid
        cur2 = await db.execute("SELECT * FROM fournisseurs WHERE id = ?", (fid,))
        return dict(await cur2.fetchone())


@router.put("/fournisseurs/{fid}")
async def update_fournisseur_achats(fid: int, body: FournisseurUpdate, _=Depends(require_admin)):
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


@router.delete("/fournisseurs/{fid}", status_code=200)
async def delete_fournisseur(fid: int, _=Depends(require_admin)):
    async with get_db() as db:
        cur = await db.execute("SELECT id, nom FROM fournisseurs WHERE id = ?", (fid,))
        existing = await cur.fetchone()
        if not existing:
            raise HTTPException(404, "Fournisseur introuvable")
        cur2 = await db.execute(
            "SELECT COUNT(*) AS nb FROM catalogue_fournisseur WHERE fournisseur_id = ?", (fid,)
        )
        nb_articles = (await cur2.fetchone())["nb"]
        if nb_articles > 0:
            raise HTTPException(
                409,
                f"Impossible de supprimer : ce fournisseur a {nb_articles} article(s) dans le catalogue. "
                "Supprimez d'abord les articles ou réassignez-les."
            )
        await db.execute("DELETE FROM fournisseurs WHERE id = ?", (fid,))
        await db.commit()
        return {"ok": True, "nom": existing["nom"]}


# ---------------------------------------------------------------------------
# Catalogue fournisseur
# ---------------------------------------------------------------------------

@router.get("/catalogue")
async def get_catalogue(
    fournisseur_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    actif_only: bool = Query(True),
    avec_stock: bool = Query(False),
):
    async with get_db() as db:
        sql = """
            SELECT c.*, f.nom AS fournisseur_nom, p.nom AS produit_nom
            FROM catalogue_fournisseur c
            JOIN fournisseurs f ON f.id = c.fournisseur_id
            LEFT JOIN produits p ON p.id = c.produit_id
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
        articles = [dict(r) for r in await cur.fetchall()]

        if avec_stock and articles:
            stocks = await _compter_stock_par_article(db)
            for a in articles:
                a["stock"] = stocks.get(a["id"], 0)

        return articles


async def _compter_stock_par_article(db) -> dict:
    """Compte le nombre de lignes de réception encore en stock, groupées par
    catalogue_fournisseur_id. « En stock » = réception clôturée + conforme +
    non refusée + DLC non dépassée + pas encore sortie (dlc_devenir).

    Une ligne de réception = une unité reçue (carcasse, colis, pièce…) toujours
    présente. Retourne { catalogue_fournisseur_id: nombre }.
    """
    today = date.today().isoformat()
    cur = await db.execute(
        """
        SELECT rl.catalogue_fournisseur_id AS cat_id, COUNT(*) AS nb
        FROM reception_lignes rl
        JOIN receptions r ON r.id = rl.reception_id
        WHERE rl.catalogue_fournisseur_id IS NOT NULL
          AND r.statut = 'cloturee'
          AND rl.conforme = 1
          AND r.livraison_refusee = 0
          AND (COALESCE(rl.dlc, rl.dluo) IS NULL OR COALESCE(rl.dlc, rl.dluo) >= ?)
          AND NOT EXISTS (
              SELECT 1 FROM dlc_devenir dd
              WHERE dd.source_type = 'reception_ligne' AND dd.source_id = rl.id
          )
        GROUP BY rl.catalogue_fournisseur_id
        """,
        (today,),
    )
    return {row["cat_id"]: row["nb"] for row in await cur.fetchall()}


@router.get("/catalogue/export")
async def export_catalogue(fournisseur_id: Optional[int] = Query(None)):
    """Exporte le catalogue fournisseur en Excel (filtre optionnel par fournisseur)."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        raise HTTPException(500, "openpyxl requis")

    async with get_db() as db:
        sql = """
            SELECT c.*, f.nom AS fournisseur_nom
            FROM catalogue_fournisseur c
            JOIN fournisseurs f ON f.id = c.fournisseur_id
            WHERE f.boutique_id = 1 AND c.actif = 1
        """
        params = []
        if fournisseur_id:
            sql += " AND c.fournisseur_id = ?"
            params.append(fournisseur_id)
        sql += " ORDER BY f.nom, c.designation"
        cur = await db.execute(sql, params)
        articles = [dict(r) for r in await cur.fetchall()]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Catalogue Fournisseur"

    cols = [
        ("fournisseur_nom",   "Fournisseur"),
        ("code_article",      "Code article"),
        ("designation",       "Désignation"),
        ("prix_achat_ht",     "Prix achat HT (€)"),
        ("format_prix",       "Prix au (kg / colis)"),
        ("qte_par_colis",     "Qté par colis"),
        ("poids_unitaire_kg", "Poids unitaire (kg)"),
        ("poids_colis_kg",    "Poids total colis (kg)"),
        ("tva_percent",       "TVA (%)"),
        ("conditionnement",   "Conditionnement"),
        ("famille",           "Famille"),
        ("sous_famille",      "Sous-famille"),
        ("dlc_type",          "Type DLC"),
    ]

    header_fill = PatternFill("solid", fgColor="2D7D46")
    for col_idx, (_, label) in enumerate(cols, 1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[cell.column_letter].width = 22

    for row_idx, art in enumerate(articles, 2):
        for col_idx, (key, _) in enumerate(cols, 1):
            ws.cell(row=row_idx, column=col_idx, value=art.get(key) or "")

    ws.auto_filter.ref = f"A1:{ws.cell(row=1, column=len(cols)).column_letter}1"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fname = "catalogue_fournisseur.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"}
    )


@router.get("/catalogue/template")
async def download_template():
    """Télécharger le template Excel d'import catalogue fournisseur."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        raise HTTPException(500, "openpyxl requis pour générer le template")

    from openpyxl.comments import Comment
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Catalogue"

    # Chaque colonne : (clé, en-tête lisible, note d'aide, ex. au kg, ex. au colis)
    colonnes = [
        ("fournisseur_nom",   "Fournisseur",
         "Nom exact de votre société (tel qu'enregistré chez le client).",
         "Boucherie Martin", "Boucherie Martin"),
        ("code_article",      "Code article",
         "Votre référence produit. Obligatoire.",
         "CARC-BF", "STK-185"),
        ("designation",       "Désignation",
         "Libellé complet du produit. Obligatoire.",
         "Carcasse boeuf", "Steak haché 185g"),
        ("prix_achat_ht",     "Prix achat HT (€)",
         "Prix HT. ATTENTION : prix AU KILO ou prix AU COLIS selon la colonne suivante. Obligatoire.",
         "9.70", "18.00"),
        ("format_prix",       "Prix au (kg / colis)",
         "Écrire 'kg' si le prix ci-contre est au kilo, ou 'colis' s'il est pour un colis/une pièce entière. Obligatoire.",
         "kg", "colis"),
        ("qte_par_colis",     "Qté par colis",
         "Nombre de pièces dans un colis. LAISSER VIDE si le prix est au kg.",
         "", "10"),
        ("poids_unitaire_kg", "Poids unitaire (kg)",
         "Poids d'UNE pièce en kg (ex: 0.185 pour 185 g). LAISSER VIDE si le prix est au kg.",
         "", "0.185"),
        ("tva_percent",       "TVA (%)",
         "Taux de TVA : 5.5 pour la viande, 20 sinon.",
         "5.5", "5.5"),
        ("conditionnement",   "Conditionnement (texte libre)",
         "Précision libre : 'Carcasse ~150kg', 'Carton de 10', 'Sous-vide'... Facultatif.",
         "Carcasse ~150kg", "Carton de 10"),
        ("famille",           "Famille",
         "Catégorie : Viande | Charcuterie | Traiteur | Aide culinaire | Hygiène et emballage. Facultatif.",
         "Viande", "Viande"),
        ("sous_famille",      "Sous-famille",
         "Sous-catégorie selon la famille (ex pour Viande : Boeuf, Veau, Agneau, Porc, Volaille, Cheval). Facultatif.",
         "Boeuf", "Boeuf"),
        ("dlc_type",          "Type de DLC",
         "dlc = date limite classique | date_abattage = produit carcasse daté à l'abattage | no_dlc = sans DLC.",
         "date_abattage", "dlc"),
    ]

    header_fill = PatternFill("solid", fgColor="2D7D46")
    note_fill   = PatternFill("solid", fgColor="E8F5E9")
    ex_fill     = PatternFill("solid", fgColor="FFF8E1")
    wrap_top    = Alignment(horizontal="left", vertical="top", wrap_text=True)

    # Colonnes numériques → format Excel appliqué aux cellules de données.
    # Les exemples sont convertis en nombre pour ne pas rester du texte.
    FORMATS_NUM = {
        "prix_achat_ht":     "0.00",    # D — prix : 2 décimales
        "qte_par_colis":     "0",       # F — quantité : entier
        "poids_unitaire_kg": "0.000",   # G — poids : 3 décimales
        "tva_percent":       "0.0",     # H — TVA : 1 décimale
    }

    def _to_num(v):
        """Convertit une valeur d'exemple en nombre, ou la laisse vide/texte."""
        if v in (None, ""):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return v

    DERNIERE_LIGNE = 500  # plage de saisie sur laquelle on applique le format

    for col, (key, header, note, ex_kg, ex_colis) in enumerate(colonnes, 1):
        letter = ws.cell(row=1, column=col).column_letter
        est_num = key in FORMATS_NUM

        # Ligne 1 : en-tête lisible
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        # Le nom technique reste en commentaire (pour l'import, insensible à l'ordre)
        cell.comment = Comment(f"Colonne technique : {key}", "HACCP")

        # Ligne 2 : note d'aide
        note_cell = ws.cell(row=2, column=col, value=note)
        note_cell.fill = note_fill
        note_cell.font = Font(italic=True, size=9, color="2D5A3A")
        note_cell.alignment = wrap_top

        # Lignes 3 et 4 : deux exemples concrets (au kg / au colis)
        v3, v4 = (_to_num(ex_kg), _to_num(ex_colis)) if est_num else (ex_kg, ex_colis)
        c3 = ws.cell(row=3, column=col, value=v3)
        c4 = ws.cell(row=4, column=col, value=v4)
        for c in (c3, c4):
            c.fill = ex_fill
            c.font = Font(size=10, color="8A6D3B")
            c.alignment = wrap_top

        # Format nombre appliqué aux exemples ET à toute la zone de saisie
        if est_num:
            for r in range(3, DERNIERE_LIGNE + 1):
                ws.cell(row=r, column=col).number_format = FORMATS_NUM[key]

        ws.column_dimensions[letter].width = 20

    # Étiquettes des lignes d'exemple, dans une colonne hors tableau (à droite)
    note_col = len(colonnes) + 2
    ws.cell(row=3, column=note_col, value="◀ Exemple : produit vendu AU KILO (carcasse)").font = Font(italic=True, size=9, color="8A6D3B")
    ws.cell(row=4, column=note_col, value="◀ Exemple : produit vendu AU COLIS (10 steaks de 185g)").font = Font(italic=True, size=9, color="8A6D3B")

    ws.row_dimensions[2].height = 58
    ws.freeze_panes = "A5"  # données à saisir à partir de la ligne 5

    # Liste déroulante kg/colis sur la colonne format_prix (anti-erreur)
    fmt_letter = ws.cell(row=1, column=5).column_letter
    dv = DataValidation(type="list", formula1='"kg,colis"', allow_blank=False)
    dv.prompt = "Choisir : kg (prix au kilo) ou colis (prix au colis/pièce)"
    dv.promptTitle = "Le prix est au..."
    ws.add_data_validation(dv)
    dv.add(f"{fmt_letter}5:{fmt_letter}500")

    # Liste déroulante des familles (colonne « famille »)
    fam_col = next(i for i, (k, *_rest) in enumerate(colonnes, 1) if k == "famille")
    fam_letter = ws.cell(row=1, column=fam_col).column_letter
    dv_fam = DataValidation(
        type="list",
        formula1='"Viande,Charcuterie,Traiteur,Aide culinaire,Hygiène et emballage"',
        allow_blank=True,
    )
    dv_fam.prompt = "Choisir une famille de produit"
    dv_fam.promptTitle = "Famille"
    ws.add_data_validation(dv_fam)
    dv_fam.add(f"{fam_letter}5:{fam_letter}500")

    # --- Onglet « Mode d'emploi » -------------------------------------------
    guide = wb.create_sheet("Mode d'emploi")
    guide.column_dimensions["A"].width = 95
    lignes_guide = [
        ("COMMENT REMPLIR CE CATALOGUE", True),
        ("", False),
        ("1. Une ligne = un produit. Commencez à saisir à partir de la ligne 5 de l'onglet « Catalogue ».", False),
        ("   (les lignes 3 et 4 sont des exemples, vous pouvez les écraser ou les supprimer).", False),
        ("", False),
        ("2. La colonne la plus importante est « Prix au (kg / colis) » :", True),
        ("     • Écrivez « kg »    si le prix indiqué est le prix d'UN KILO.", False),
        ("     • Écrivez « colis » si le prix indiqué est le prix d'UN COLIS entier (ou d'une pièce).", False),
        ("", False),
        ("3. Si le prix est AU KILO (kg) :", True),
        ("     → laissez VIDES les colonnes « Qté par colis » et « Poids unitaire ».", False),
        ("     → le coût d'une commande sera : poids commandé × prix au kilo.", False),
        ("", False),
        ("4. Si le prix est AU COLIS :", True),
        ("     → remplissez « Qté par colis » (nb de pièces) et « Poids unitaire (kg) ».", False),
        ("     → exemple : 10 steaks de 185 g  →  Qté par colis = 10, Poids unitaire = 0.185.", False),
        ("     → le poids total du colis (10 × 0,185 = 1,85 kg) est calculé automatiquement, ne le saisissez pas.", False),
        ("", False),
        ("5. Les poids sont en KILOS avec un point décimal (0.185 et non 185 g).", False),
        ("   Le point ou la virgule sont acceptés.", False),
        ("", False),
        ("Merci ! En cas de doute sur une ligne, laissez un commentaire ou contactez-nous.", True),
    ]
    for i, (txt, bold) in enumerate(lignes_guide, 1):
        c = guide.cell(row=i, column=1, value=txt)
        c.font = Font(bold=bold, size=12 if (bold and i == 1) else 11,
                      color="2D7D46" if bold else "333333")
        c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.active = wb.sheetnames.index("Catalogue")

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
async def import_catalogue_upload(fichier: UploadFile = File(...), _=Depends(require_admin)):
    """Import Excel catalogue fournisseur."""
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(500, "openpyxl requis")

    content = await fichier.read()
    wb = openpyxl.load_workbook(io.BytesIO(content))
    # L'onglet de données s'appelle "Catalogue" dans le template ; sinon onglet actif.
    ws = wb["Catalogue"] if "Catalogue" in wb.sheetnames else wb.active

    # Correspondance libellé lisible (template fournisseur) → clé technique.
    # On accepte aussi directement les clés techniques (anciens exports).
    LIBELLE_VERS_CLE = {
        "fournisseur": "fournisseur_nom",
        "code article": "code_article",
        "désignation": "designation", "designation": "designation",
        "prix achat ht (€)": "prix_achat_ht", "prix achat ht": "prix_achat_ht",
        "prix au (kg / colis)": "format_prix", "prix au": "format_prix",
        "qté par colis": "qte_par_colis", "qte par colis": "qte_par_colis",
        "poids unitaire (kg)": "poids_unitaire_kg", "poids unitaire": "poids_unitaire_kg",
        "poids total colis (kg)": "poids_colis_kg",
        "tva (%)": "tva_percent", "tva": "tva_percent",
        "conditionnement (texte libre)": "conditionnement", "conditionnement": "conditionnement",
        "famille": "famille",
        "sous-famille": "sous_famille", "sous famille": "sous_famille", "sous_famille": "sous_famille",
        "type de dlc": "dlc_type", "type dlc": "dlc_type",
    }

    def _cle(libelle):
        l = libelle.strip().lower()
        return LIBELLE_VERS_CLE.get(l, l)  # libellé connu → clé, sinon tel quel

    headers = [_cle(str(ws.cell(row=1, column=c).value or "")) for c in range(1, ws.max_column + 1)]
    required = {"fournisseur_nom", "code_article", "designation", "prix_achat_ht"}
    missing = required - set(headers)
    if missing:
        raise HTTPException(400, f"Colonnes manquantes : {missing}")

    def col(row, name):
        idx = headers.index(name) + 1
        v = ws.cell(row=row, column=idx).value
        return str(v).strip() if v is not None else ""

    stats = {"crees": 0, "mis_a_jour": 0, "erreurs": []}

    # Lignes 1=en-têtes, 2=notes, 3-4=exemples → vraies données à partir de la ligne 5.
    # On saute aussi toute ligne d'exemple résiduelle laissée par le fournisseur.
    EXEMPLES_CODES = {"carc-bf", "stk-185"}

    async with get_db() as db:
        for row_num in range(5, ws.max_row + 1):
            nom_fourn = col(row_num, "fournisseur_nom")
            code = col(row_num, "code_article")
            if not nom_fourn or not code:
                continue
            # Ignorer une ligne d'exemple que le fournisseur aurait laissée en place
            if code.strip().lower() in EXEMPLES_CODES and nom_fourn.strip().lower() == "boucherie martin":
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

            format_prix     = _normaliser_format_prix(col(row_num, "format_prix")) if "format_prix" in headers else "kg"
            conditionnement = col(row_num, "conditionnement") if "conditionnement" in headers else None
            famille         = col(row_num, "famille")         if "famille"         in headers else None
            sous_famille    = col(row_num, "sous_famille")    if "sous_famille"    in headers else None
            dlc_type        = col(row_num, "dlc_type")        if "dlc_type"        in headers else "dlc"

            def _num(name):
                """Lit une cellule numérique optionnelle (qte/poids), '' → None."""
                if name not in headers:
                    return None
                raw = col(row_num, name).replace(",", ".")  # tolère la virgule décimale
                if not raw:
                    return None
                try:
                    return float(raw)
                except ValueError:
                    return None

            qte_par_colis     = _num("qte_par_colis")
            poids_unitaire_kg = _num("poids_unitaire_kg")
            poids_colis_kg    = _calc_poids_colis_kg(qte_par_colis, poids_unitaire_kg)

            # UPSERT
            cur2 = await db.execute(
                "SELECT id FROM catalogue_fournisseur WHERE fournisseur_id = ? AND code_article = ?",
                (fourn["id"], code)
            )
            existing = await cur2.fetchone()
            if existing:
                await db.execute(
                    """UPDATE catalogue_fournisseur
                       SET designation=?, prix_achat_ht=?, format_prix=?,
                           qte_par_colis=?, poids_unitaire_kg=?, poids_colis_kg=?,
                           tva_percent=?, conditionnement=?, famille=?, sous_famille=?,
                           dlc_type=?, date_maj=CURRENT_TIMESTAMP
                       WHERE id=?""",
                    (designation, prix, format_prix,
                     qte_par_colis, poids_unitaire_kg, poids_colis_kg,
                     tva, conditionnement or None, famille or None, sous_famille or None,
                     dlc_type or "dlc", existing["id"])
                )
                stats["mis_a_jour"] += 1
            else:
                await db.execute(
                    """INSERT INTO catalogue_fournisseur
                       (fournisseur_id, code_article, designation, prix_achat_ht, format_prix,
                        qte_par_colis, poids_unitaire_kg, poids_colis_kg, tva_percent, conditionnement,
                        famille, sous_famille, dlc_type)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (fourn["id"], code, designation, prix, format_prix,
                     qte_par_colis, poids_unitaire_kg, poids_colis_kg,
                     tva, conditionnement or None, famille or None, sous_famille or None,
                     dlc_type or "dlc")
                )
                stats["crees"] += 1

        await db.commit()

    return stats


@router.get("/catalogue/{article_id}")
async def get_article(article_id: int):
    async with get_db() as db:
        cur = await db.execute(
            "SELECT c.*, f.nom AS fournisseur_nom, p.nom AS produit_nom "
            "FROM catalogue_fournisseur c "
            "JOIN fournisseurs f ON f.id = c.fournisseur_id "
            "LEFT JOIN produits p ON p.id = c.produit_id "
            "WHERE c.id = ?",
            (article_id,)
        )
        row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Article introuvable")
        return dict(row)


@router.post("/catalogue", status_code=201)
async def create_article(body: CatalogueArticleCreate, _=Depends(require_admin)):
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

        format_prix = _normaliser_format_prix(body.format_prix)
        poids_colis = _calc_poids_colis_kg(body.qte_par_colis, body.poids_unitaire_kg)
        cur = await db.execute(
            """INSERT INTO catalogue_fournisseur
               (fournisseur_id, code_article, designation, prix_achat_ht, format_prix,
                qte_par_colis, poids_unitaire_kg, poids_colis_kg, tva_percent, conditionnement,
                famille, sous_famille, dlc_type, produit_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (body.fournisseur_id, body.code_article, body.designation, body.prix_achat_ht,
             format_prix, body.qte_par_colis, body.poids_unitaire_kg,
             poids_colis, body.tva_percent, body.conditionnement,
             body.famille, body.sous_famille, body.dlc_type, body.produit_id)
        )
        await db.commit()
        cur2 = await db.execute("SELECT * FROM catalogue_fournisseur WHERE id = ?", (cur.lastrowid,))
        return dict(await cur2.fetchone())


@router.put("/catalogue/{article_id}")
async def update_article(article_id: int, body: CatalogueArticleUpdate, _=Depends(require_admin)):
    async with get_db() as db:
        cur = await db.execute("SELECT * FROM catalogue_fournisseur WHERE id = ?", (article_id,))
        existing = await cur.fetchone()
        if not existing:
            raise HTTPException(404, "Article introuvable")

        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        if not fields:
            raise HTTPException(400, "Aucun champ à modifier")

        # Pont produit interne : produit_id = 0 signifie « délier » → NULL en base.
        if fields.get("produit_id") == 0:
            fields["produit_id"] = None

        if "format_prix" in fields:
            fields["format_prix"] = _normaliser_format_prix(fields["format_prix"])

        # Recalcule le poids du colis si une des deux données brutes est modifiée,
        # en repartant des valeurs existantes pour celle qui ne change pas.
        if "qte_par_colis" in fields or "poids_unitaire_kg" in fields:
            qte = fields.get("qte_par_colis", existing["qte_par_colis"])
            pu = fields.get("poids_unitaire_kg", existing["poids_unitaire_kg"])
            fields["poids_colis_kg"] = _calc_poids_colis_kg(qte, pu)

        fields["date_maj"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [article_id]
        await db.execute(f"UPDATE catalogue_fournisseur SET {set_clause} WHERE id = ?", values)
        await db.commit()

        cur2 = await db.execute("SELECT * FROM catalogue_fournisseur WHERE id = ?", (article_id,))
        return dict(await cur2.fetchone())


@router.delete("/catalogue/{article_id}", status_code=200)
async def delete_article(article_id: int, permanent: bool = Query(False), _=Depends(require_admin)):
    async with get_db() as db:
        if permanent:
            # Couper les liens FK avant suppression (les lignes historiques restent, juste délié)
            await db.execute(
                "UPDATE commande_lignes SET catalogue_fournisseur_id = NULL WHERE catalogue_fournisseur_id = ?",
                (article_id,)
            )
            await db.execute(
                "UPDATE reception_lignes SET catalogue_fournisseur_id = NULL WHERE catalogue_fournisseur_id = ?",
                (article_id,)
            )
            await db.execute("DELETE FROM catalogue_fournisseur WHERE id = ?", (article_id,))
        else:
            await db.execute("UPDATE catalogue_fournisseur SET actif = 0 WHERE id = ?", (article_id,))
        await db.commit()
    return {"ok": True}


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
            """SELECT cl.*, cf.dlc_type AS dlc_type
               FROM commande_lignes cl
               LEFT JOIN catalogue_fournisseur cf ON cf.id = cl.catalogue_fournisseur_id
               WHERE cl.commande_id = ? ORDER BY cl.id""",
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


# ---------------------------------------------------------------------------
# Panier multi-fournisseurs
# ---------------------------------------------------------------------------

class PanierLigneCreate(BaseModel):
    catalogue_fournisseur_id: Optional[int] = None
    fournisseur_id: int
    fournisseur_nom: str
    code_article: str
    designation: str
    quantite: float
    unite: Optional[str] = "kg"
    prix_ht: float


class PanierSave(BaseModel):
    lignes: List[PanierLigneCreate]


class PanierGenerer(BaseModel):
    date_livraison_prevue: Optional[str] = None
    commentaire: Optional[str] = None


@router.get("/panier")
async def get_panier():
    async with get_db() as db:
        cur = await db.execute(
            "SELECT * FROM panier_lignes WHERE boutique_id = 1 ORDER BY fournisseur_nom, designation"
        )
        return [dict(r) for r in await cur.fetchall()]


@router.put("/panier", status_code=200)
async def save_panier(body: PanierSave):
    async with get_db() as db:
        await db.execute("DELETE FROM panier_lignes WHERE boutique_id = 1")
        for l in body.lignes:
            await db.execute(
                """INSERT INTO panier_lignes
                   (boutique_id, catalogue_fournisseur_id, fournisseur_id, fournisseur_nom,
                    code_article, designation, quantite, unite, prix_ht)
                   VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (l.catalogue_fournisseur_id, l.fournisseur_id, l.fournisseur_nom,
                 l.code_article, l.designation, l.quantite, l.unite, l.prix_ht)
            )
        await db.commit()
    return {"ok": True, "nb_lignes": len(body.lignes)}


@router.delete("/panier", status_code=204)
async def delete_panier():
    async with get_db() as db:
        await db.execute("DELETE FROM panier_lignes WHERE boutique_id = 1")
        await db.commit()


@router.post("/panier/generer", status_code=201)
async def generer_commandes_depuis_panier(body: PanierGenerer):
    """Regroupe le panier par fournisseur et crée une commande brouillon par fournisseur."""
    async with get_db() as db:
        cur = await db.execute(
            "SELECT * FROM panier_lignes WHERE boutique_id = 1 ORDER BY fournisseur_id"
        )
        lignes = [dict(r) for r in await cur.fetchall()]

    if not lignes:
        raise HTTPException(400, "Le panier est vide")

    # Regrouper par fournisseur
    from collections import defaultdict
    par_fournisseur = defaultdict(list)
    for l in lignes:
        par_fournisseur[l["fournisseur_id"]].append(l)

    commandes_creees = []
    for fournisseur_id, items in par_fournisseur.items():
        cmd_body = CommandeCreate(
            fournisseur_id=fournisseur_id,
            date_livraison_prevue=body.date_livraison_prevue,
            commentaire=body.commentaire,
            lignes=[
                CommandeLigneCreate(
                    catalogue_fournisseur_id=i["catalogue_fournisseur_id"],
                    code_article=i["code_article"],
                    designation=i["designation"],
                    quantite_commandee=i["quantite"],
                    unite=i["unite"],
                    prix_unitaire_ht=i["prix_ht"],
                )
                for i in items
            ]
        )
        cmd = await create_commande(cmd_body)
        commandes_creees.append(cmd)

    # Vider le panier
    async with get_db() as db:
        await db.execute("DELETE FROM panier_lignes WHERE boutique_id = 1")
        await db.commit()

    return {"nb_commandes": len(commandes_creees), "commandes": commandes_creees}


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

        # Lire config SMTP avant de construire le HTML (from_addr utilisé dans le pied)
        import os, smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASSWORD", "")
        from_addr = os.getenv("SMTP_FROM", smtp_user)

        # Construire le corps du mail (HTML + fallback texte)
        lignes_rows = "".join(
            f"""<tr>
              <td style="padding:10px 12px;border-bottom:1px solid #f1ead9;font-family:monospace;font-size:13px;color:#5a3e28;">{l['code_article'] or '—'}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #f1ead9;font-size:14px;">{l['designation']}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #f1ead9;text-align:right;white-space:nowrap;">{l['quantite_commandee']} {l['unite']}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #f1ead9;text-align:right;white-space:nowrap;">{l['prix_unitaire_ht']:.2f} €</td>
              <td style="padding:10px 12px;border-bottom:1px solid #f1ead9;text-align:right;font-weight:700;white-space:nowrap;">{l['montant_ht']:.2f} €</td>
            </tr>"""
            for l in lignes
        )
        commentaire_bloc = f"""<tr><td colspan="5" style="padding:10px 12px;font-style:italic;color:#6b7280;font-size:13px;">{commande['commentaire']}</td></tr>""" if commande['commentaire'] else ""

        app_url = os.getenv("APP_URL", "http://localhost:8000").rstrip("/")
        logo_url = f"{app_url}/static/assets/logo.png"

        corps_html = (
            '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"></head>'
            '<body style="margin:0;padding:0;background:#f5f0e8;font-family:Georgia,serif;color:#2d1f0f;">'
            '<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f0e8;padding:32px 16px;">'
            '<tr><td align="center">'
            '<table width="620" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.1);">'
            '<tr><td style="background:#6b2d0f;padding:24px 32px;text-align:center;">'
            f'<img src="{logo_url}" alt="Au Comptoir des Lilas" style="max-width:140px;height:auto;margin-bottom:12px;display:block;margin-left:auto;margin-right:auto;">'
            '<p style="margin:0;font-size:20px;font-weight:700;color:#fff;letter-spacing:1px;">Au Comptoir des Lilas</p>'
            '<p style="margin:4px 0 0;font-size:12px;color:#f9d5b0;letter-spacing:2px;text-transform:uppercase;">Boucherie &#8226; Charcuterie</p>'
            '</td></tr>'
            '<tr><td style="padding:24px 32px 8px;border-bottom:2px solid #e8d9c4;">'
            '<p style="margin:0;font-size:18px;font-weight:700;color:#6b2d0f;">Bon de commande</p>'
            '<p style="margin:4px 0 0;font-size:13px;color:#6b7280;">'
            'N&#176; <strong style="color:#2d1f0f;">' + commande['numero_commande'] + '</strong>'
            ' &nbsp;&#183;&nbsp; Date : <strong style="color:#2d1f0f;">' + commande['date_commande'] + '</strong>'
            ' &nbsp;&#183;&nbsp; Heure d\'envoi : <strong style="color:#2d1f0f;">' + datetime.now().strftime('%H:%M') + '</strong>'
            ' &nbsp;&#183;&nbsp; Livraison souhait&#233;e : <strong style="color:#2d1f0f;">' + (commande['date_livraison_prevue'] or '&#192; d&#233;finir') + '</strong>'
            '</p></td></tr>'
            '<tr><td style="padding:0 32px;">'
            '<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:20px;">'
            '<thead><tr style="background:#f3ebdf;">'
            '<th style="padding:10px 12px;text-align:left;font-size:12px;color:#5a3e28;text-transform:uppercase;border-bottom:2px solid #d4c5af;">Code</th>'
            '<th style="padding:10px 12px;text-align:left;font-size:12px;color:#5a3e28;text-transform:uppercase;border-bottom:2px solid #d4c5af;">D&#233;signation</th>'
            '<th style="padding:10px 12px;text-align:right;font-size:12px;color:#5a3e28;text-transform:uppercase;border-bottom:2px solid #d4c5af;">Qt&#233;</th>'
            '<th style="padding:10px 12px;text-align:right;font-size:12px;color:#5a3e28;text-transform:uppercase;border-bottom:2px solid #d4c5af;">Prix HT</th>'
            '<th style="padding:10px 12px;text-align:right;font-size:12px;color:#5a3e28;text-transform:uppercase;border-bottom:2px solid #d4c5af;">Montant HT</th>'
            '</tr></thead>'
            '<tbody>' + lignes_rows + commentaire_bloc + '</tbody>'
            '</table></td></tr>'
            '<tr><td style="padding:0 32px 24px;">'
            '<table width="100%" cellpadding="0" cellspacing="0"><tr>'
            '<td style="padding:14px 12px;background:#f3ebdf;border-top:2px solid #d4c5af;text-align:right;">'
            '<span style="font-size:15px;color:#5a3e28;font-weight:700;">TOTAL HT : </span>'
            f'<span style="font-size:20px;font-weight:800;color:#6b2d0f;">{commande["montant_total_ht"]:.2f} &#8364;</span>'
            '</td></tr></table></td></tr>'
            '<tr><td style="background:#f9f4ed;padding:16px 32px;border-top:1px solid #e8d9c4;">'
            '<table width="100%" cellpadding="0" cellspacing="0"><tr>'
            '<td style="font-size:11px;color:#6b7280;line-height:1.6;">'
            '<p style="margin:0 0 8px;font-weight:700;color:#5a3e28;">Au Comptoir des Lilas</p>'
            '<p style="margin:0 0 2px;">122 rue de Paris &nbsp;&#183;&nbsp; 93260 Les Lilas &nbsp;&#183;&nbsp; France</p>'
            '<p style="margin:0;">Tel. 06 88 50 43 41 &nbsp;&#183;&nbsp; ' + from_addr + '</p>'
            '<p style="margin:4px 0 0;font-size:10px;color:#9a7c5a;">SIRET : 103 577 607 00015</p>'
            '</td></tr></table>'
            '</td></tr>'
            '</table></td></tr></table></body></html>'
        )

        corps_txt = "\n".join(
            f"  • {l['code_article']} — {l['designation']} : {l['quantite_commandee']} {l['unite']} "
            f"× {l['prix_unitaire_ht']:.2f}€ HT = {l['montant_ht']:.2f}€ HT"
            for l in lignes
        )
        corps = f"Commande {commande['numero_commande']} du {commande['date_commande']}\n\n{corps_txt}\n\nTOTAL HT : {commande['montant_total_ht']:.2f}€"

        # Envoi mail via smtplib (config dans variables d'env)
        if not smtp_host or not smtp_user:
            return {
                "envoye": False,
                "message": "Configuration SMTP manquante (SMTP_HOST, SMTP_USER, SMTP_PASSWORD non définis)",
                "destinataire": commande["email_commercial"],
                "sujet": f"Commande {commande['numero_commande']} — Au Comptoir des Lilas",
                "corps": corps,
            }

        msg = MIMEMultipart("alternative")
        msg["From"]    = from_addr
        msg["To"]      = commande["email_commercial"]
        msg["Subject"] = f"Commande {commande['numero_commande']} — Au Comptoir des Lilas"
        msg.attach(MIMEText(corps, "plain", "utf-8"))
        msg.attach(MIMEText(corps_html, "html", "utf-8"))

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

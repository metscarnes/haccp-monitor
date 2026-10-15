"""
routes_prix_etiquettes.py — API étiquettes prix Brother QL-820NWBc

Endpoints :
  POST /api/prix-etiquettes/preview         → PNG base64 (prévisualisation live)
  POST /api/prix-etiquettes/imprimer        → impression USB
  GET  /api/prix-etiquettes/fonts           → liste polices TTF custom
  POST /api/prix-etiquettes/upload-font     → upload TTF/OTF
  GET  /api/prix-etiquettes/modeles         → modèles sauvegardés
  POST /api/prix-etiquettes/modeles         → sauvegarder un modèle
  PUT  /api/prix-etiquettes/modeles/{id}    → modifier un modèle
  DELETE /api/prix-etiquettes/modeles/{id}  → supprimer un modèle
  GET  /api/prix-etiquettes/catalogue       → recherche catalogue vente (import)
  POST /api/prix-etiquettes/imprimer-masse  → série depuis le catalogue de vente
  GET/PUT /api/prix-etiquettes/modele-defaut → modèle des réimpressions
  GET  /api/prix-etiquettes/a-reimprimer    → file des étiquettes à refaire (+ /compte, /historique)
  POST /api/prix-etiquettes/a-reimprimer/sortir → imprimées via navigateur / retirées
"""

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from src.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

FONTS_DIR = Path(__file__).parent.parent.parent / "static" / "fonts" / "custom"
FONTS_DIR.mkdir(parents=True, exist_ok=True)

EXTENSIONS_AUTORISEES = {".ttf", ".otf"}
TAILLE_MAX_FONT = 5 * 1024 * 1024  # 5 Mo


# ---------------------------------------------------------------------------
# Modèles Pydantic
# ---------------------------------------------------------------------------

class LigneTexte(BaseModel):
    texte: str = ""
    poids: float = 1.0   # poids relatif (mode auto) : 2.0 = deux fois plus grand
    taille_px: int = 0   # > 0 = taille FIXE en px imposée ; 0 = auto-fit
    gras: bool = False
    police: Optional[str] = None
    alignement: str = "center"   # left | center | right


class ConfigEtiquette(BaseModel):
    largeur_cm: float = 10.0
    hauteur_cm: float = 7.5
    fond_noir: bool = False
    lignes: list[LigneTexte] = []


class ModeleCreate(BaseModel):
    nom: str
    config: ConfigEtiquette


# ---------------------------------------------------------------------------
# Prévisualisation
# ---------------------------------------------------------------------------

@router.post("/api/prix-etiquettes/preview")
async def preview_etiquette(config: ConfigEtiquette):
    """Génère un PNG base64 de l'étiquette pour la prévisualisation live."""
    from src.printing.brother_ql_prix import generer_preview_base64
    try:
        data = config.model_dump()
        png_b64 = generer_preview_base64(data)
        return {"image": f"data:image/png;base64,{png_b64}"}
    except Exception as e:
        logger.error("Erreur preview étiquette prix : %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Impression
# ---------------------------------------------------------------------------

class ImpressionUnitaire(ConfigEtiquette):
    # Produit du catalogue de vente importé dans l'éditeur (facultatif) : ses
    # variables {Nom} {prix}… sont remplies avec son prix ACTUEL relu en base, et
    # il sort de la file « à réimprimer » une fois l'étiquette partie.
    produit_id: Optional[int] = None


@router.post("/api/prix-etiquettes/imprimer")
async def imprimer_etiquette(body: ImpressionUnitaire):
    """Envoie l'étiquette à l'imprimante Brother (réseau via tunnel, ou USB)."""
    from src.printing.brother_ql_prix import appliquer_variables, imprimer_etiquette_prix
    data = body.model_dump(exclude={"produit_id"})
    if body.produit_id is not None:
        produit = (await _charger_produits_vente([body.produit_id])).get(body.produit_id)
        if produit is None:
            raise HTTPException(status_code=404, detail="Produit introuvable ou désactivé")
        data = appliquer_variables(data, produit)
    # Envoi réseau bloquant → exécuté hors de la boucle async pour ne pas
    # figer toute l'application pendant l'impression.
    ok, message = await run_in_threadpool(imprimer_etiquette_prix, data)
    if not ok:
        raise HTTPException(status_code=503, detail=message)
    if body.produit_id is not None:
        await _sortir_de_la_file([body.produit_id], mode="serveur")
    return {"ok": True, "message": message}


# ---------------------------------------------------------------------------
# Polices custom
# ---------------------------------------------------------------------------

@router.get("/api/prix-etiquettes/fonts")
async def lister_fonts():
    """
    Retourne la liste des polices TTF/OTF uploadées, avec leurs métriques
    (ascent/descent en fraction de la taille) et celles de la police par défaut :
    l'aperçu Canvas les utilise pour calculer les tailles comme l'impression.
    """
    from src.printing.brother_ql_prix import lister_polices, metriques_defaut
    return {"fonts": lister_polices(), "defaut": metriques_defaut()}


@router.post("/api/prix-etiquettes/upload-font", status_code=201)
async def upload_font(fichier: UploadFile = File(...)):
    """Upload une police TTF ou OTF custom (max 5 Mo)."""
    ext = Path(fichier.filename).suffix.lower()
    if ext not in EXTENSIONS_AUTORISEES:
        raise HTTPException(status_code=400, detail="Seuls les fichiers .ttf et .otf sont acceptés")

    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_FONT:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 5 Mo)")

    # Nom sécurisé : on garde uniquement lettres, chiffres, tirets, underscores
    nom_safe = "".join(c for c in Path(fichier.filename).stem if c.isalnum() or c in "-_") + ext
    dest = FONTS_DIR / nom_safe
    dest.write_bytes(contenu)

    logger.info("Police uploadée : %s", nom_safe)
    return {"nom": nom_safe, "label": Path(nom_safe).stem}


@router.delete("/api/prix-etiquettes/fonts/{nom_fichier}", status_code=200)
async def supprimer_font(nom_fichier: str):
    """Supprime une police custom uploadée."""
    chemin = FONTS_DIR / nom_fichier
    if not chemin.exists() or chemin.suffix.lower() not in EXTENSIONS_AUTORISEES:
        raise HTTPException(status_code=404, detail="Police introuvable")
    chemin.unlink()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Modèles sauvegardés
# ---------------------------------------------------------------------------

@router.get("/api/prix-etiquettes/modeles")
async def get_modeles():
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT id, nom, config_json, created_at FROM modeles_etiquettes_prix ORDER BY nom"
        )
        return {"modeles": [
            {"id": r[0], "nom": r[1], "config": json.loads(r[2]), "created_at": r[3]}
            for r in rows
        ]}


@router.post("/api/prix-etiquettes/modeles", status_code=201)
async def creer_modele(body: ModeleCreate):
    config_json = json.dumps(body.config.model_dump(), ensure_ascii=False)
    async with get_db() as db:
        cur = await db.execute(
            "INSERT INTO modeles_etiquettes_prix (nom, config_json) VALUES (?, ?)",
            (body.nom.strip(), config_json),
        )
        await db.commit()
        return {"id": cur.lastrowid, "nom": body.nom}


@router.put("/api/prix-etiquettes/modeles/{modele_id}")
async def modifier_modele(modele_id: int, body: ModeleCreate):
    config_json = json.dumps(body.config.model_dump(), ensure_ascii=False)
    async with get_db() as db:
        cur = await db.execute(
            "UPDATE modeles_etiquettes_prix SET nom=?, config_json=? WHERE id=?",
            (body.nom.strip(), config_json, modele_id),
        )
        await db.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Modèle introuvable")
        return {"ok": True}


@router.delete("/api/prix-etiquettes/modeles/{modele_id}", status_code=200)
async def supprimer_modele(modele_id: int):
    async with get_db() as db:
        cur = await db.execute(
            "DELETE FROM modeles_etiquettes_prix WHERE id=?", (modele_id,)
        )
        await db.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Modèle introuvable")
        return {"ok": True}


# ---------------------------------------------------------------------------
# Import catalogue achats (recherche live pour pré-remplissage)
# ---------------------------------------------------------------------------

@router.get("/api/prix-etiquettes/catalogue")
async def rechercher_catalogue(
    q: str = Query("", min_length=0),
    limit: int = Query(30, ge=1, le=2000),
):
    """
    Recherche dans le catalogue vente pour pré-remplir l'étiquette prix.
    Retourne id, nom, prix_vente_ttc, famille, sous_famille.

    - limit=30 (défaut) : autocomplete d'import (mono-étiquette).
    - limit élevé : chargement complet pour l'impression de masse.
    """
    async with get_db() as db:
        sql = """
            SELECT id, nom, prix_vente_ttc, famille, sous_famille, unite_vente
            FROM catalogue_vente
            WHERE boutique_id = 1 AND actif = 1
        """
        params = []
        if q.strip():
            sql += " AND nom LIKE ?"
            params.append(f"%{q}%")
        sql += " ORDER BY famille, nom LIMIT ?"
        params.append(limit)

        cur = await db.execute(sql, params)
        rows = await cur.fetchall()
        return {"articles": [
            {
                "id": r[0],
                "designation": r[1],
                "nom": r[1],
                "prix_vente_ttc": r[2],
                "famille": r[3],
                "sous_famille": r[4],
                "unite_vente": r[5],
            }
            for r in rows
        ]}


@router.get("/api/prix-etiquettes/catalogue/familles")
async def lister_familles_catalogue():
    """Liste des familles distinctes du catalogue de vente (pour le filtre masse)."""
    async with get_db() as db:
        cur = await db.execute(
            """
            SELECT DISTINCT famille FROM catalogue_vente
            WHERE boutique_id = 1 AND actif = 1 AND famille IS NOT NULL AND famille <> ''
            ORDER BY famille
            """
        )
        rows = await cur.fetchall()
        return {"familles": [r[0] for r in rows]}


# ---------------------------------------------------------------------------
# Impression de masse (série depuis le catalogue de vente)
# ---------------------------------------------------------------------------

# Étiquettes envoyées par connexion lors d'une impression de masse : assez
# pour supprimer l'aller-retour par étiquette, assez peu pour qu'une panne en
# cours de série ne fasse pas tout perdre.
TAILLE_LOT_IMPRESSION = 20


class LigneMasse(BaseModel):
    produit_id: int
    quantite: int = 1


class ImpressionMasse(BaseModel):
    config: ConfigEtiquette          # modèle choisi, lignes avec variables {nom}…
    produits: list[LigneMasse]       # produits sélectionnés + quantités


async def _charger_produits_vente(ids: list[int]) -> dict[int, dict]:
    """Charge les produits du catalogue de vente par id → dict {id: produit}."""
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    async with get_db() as db:
        cur = await db.execute(
            f"""
            SELECT id, nom, prix_vente_ttc, famille, sous_famille, unite_vente
            FROM catalogue_vente
            WHERE boutique_id = 1 AND actif = 1 AND id IN ({placeholders})
            """,
            ids,
        )
        rows = await cur.fetchall()
    return {
        r[0]: {
            "id": r[0],
            "nom": r[1],
            "prix_vente_ttc": r[2],
            "famille": r[3],
            "sous_famille": r[4],
            "unite_vente": r[5],
        }
        for r in rows
    }


@router.post("/api/prix-etiquettes/preview-masse")
async def preview_masse(body: ImpressionMasse):
    """
    Génère les images (PNG base64) d'une série d'étiquettes, une par produit
    (sans tenir compte de la quantité — le navigateur répétera l'image).
    Sert à l'aperçu/impression navigateur.
    """
    from src.printing.brother_ql_prix import appliquer_variables, generer_preview_base64

    produits = await _charger_produits_vente([p.produit_id for p in body.produits])
    base = body.config.model_dump()

    # Rendu PIL (CPU) hors de la boucle async : l'app reste réactive.
    def _generer() -> list[dict]:
        etiquettes = []
        for ligne in body.produits:
            produit = produits.get(ligne.produit_id)
            if not produit:
                continue
            config = appliquer_variables(base, produit)
            try:
                png_b64 = generer_preview_base64(config)
            except Exception as e:
                logger.error("Preview masse — produit %s : %s", ligne.produit_id, e)
                continue
            etiquettes.append({
                "produit_id": ligne.produit_id,
                "nom": produit["nom"],
                "quantite": max(1, ligne.quantite),
                "image": f"data:image/png;base64,{png_b64}",
            })
        return etiquettes

    return {"etiquettes": await run_in_threadpool(_generer)}


@router.post("/api/prix-etiquettes/imprimer-masse")
async def imprimer_masse(body: ImpressionMasse):
    """
    Imprime une série d'étiquettes via le serveur (Wi-Fi). Pour chaque produit,
    applique les variables au modèle, répète `quantite` exemplaires, puis
    envoie le tout par LOTS (une connexion par lot au lieu d'une par
    étiquette). Si un lot échoue, l'imprimante est injoignable : on s'arrête
    et on indique combien d'étiquettes sont déjà parties.
    """
    from src.printing.brother_ql_prix import appliquer_variables, imprimer_lot

    produits = await _charger_produits_vente([p.produit_id for p in body.produits])
    base = body.config.model_dump()
    imprimees = 0
    erreurs: list[str] = []

    a_imprimer: list[dict] = []
    produit_par_exemplaire: list[int] = []
    for ligne in body.produits:
        produit = produits.get(ligne.produit_id)
        if not produit:
            erreurs.append(f"Produit #{ligne.produit_id} introuvable")
            continue
        config = appliquer_variables(base, produit)
        n = max(1, ligne.quantite)
        a_imprimer.extend([config] * n)
        produit_par_exemplaire.extend([ligne.produit_id] * n)

    for i in range(0, len(a_imprimer), TAILLE_LOT_IMPRESSION):
        lot = a_imprimer[i:i + TAILLE_LOT_IMPRESSION]
        ok, message = await run_in_threadpool(imprimer_lot, lot)
        if not ok:
            reste = len(a_imprimer) - imprimees
            erreurs.append(f"{message} — {reste} étiquette(s) non imprimée(s)")
            break
        imprimees += len(lot)

    # Sortent de la file les produits dont TOUS les exemplaires sont partis.
    non_partis = set(produit_par_exemplaire[imprimees:])
    partis = set(produit_par_exemplaire[:imprimees]) - non_partis
    await _sortir_de_la_file(partis, mode="serveur")

    if imprimees == 0 and erreurs:
        raise HTTPException(status_code=503, detail=erreurs[0])
    return {"imprimees": imprimees, "erreurs": erreurs}


# ---------------------------------------------------------------------------
# File des étiquettes à réimprimer (prix de vente modifiés)
# ---------------------------------------------------------------------------

CLE_MODELE_DEFAUT = "etiquette_prix_modele_defaut"


async def _sortir_de_la_file(produit_ids, *, mode: str, statut: str = "imprimee") -> int:
    from src.file_etiquettes_prix import sortir_de_la_file
    async with get_db() as db:
        n = await sortir_de_la_file(db, produit_ids, statut=statut, mode=mode)
        await db.commit()
    return n


async def _modele_defaut_id(db) -> Optional[int]:
    """Modèle utilisé pour les réimpressions : celui choisi dans les réglages, sinon
    le seul modèle existant (cas boutique : un modèle unique pour les prix)."""
    from src.database import get_parametre
    rows = await db.execute_fetchall("SELECT id FROM modeles_etiquettes_prix ORDER BY nom")
    ids = [r[0] for r in rows]
    choisi = await get_parametre(db, 1, CLE_MODELE_DEFAUT)
    if choisi and choisi.isdigit() and int(choisi) in ids:
        return int(choisi)
    return ids[0] if len(ids) == 1 else None


class ModeleDefaut(BaseModel):
    modele_id: Optional[int] = None


@router.get("/api/prix-etiquettes/modele-defaut")
async def get_modele_defaut():
    async with get_db() as db:
        return {"modele_id": await _modele_defaut_id(db)}


@router.put("/api/prix-etiquettes/modele-defaut")
async def set_modele_defaut(body: ModeleDefaut):
    from src.database import set_parametre
    async with get_db() as db:
        if body.modele_id is not None:
            cur = await db.execute("SELECT 1 FROM modeles_etiquettes_prix WHERE id = ?",
                                   (body.modele_id,))
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="Modèle introuvable")
        await set_parametre(db, 1, CLE_MODELE_DEFAUT,
                            "" if body.modele_id is None else str(body.modele_id))
        return {"modele_id": await _modele_defaut_id(db)}


@router.get("/api/prix-etiquettes/a-reimprimer")
async def lister_a_reimprimer():
    """Produits dont le prix a changé depuis la dernière étiquette (prix ACTUEL)."""
    from src.file_etiquettes_prix import lister_file
    async with get_db() as db:
        elements = await lister_file(db)
        return {"elements": elements, "total": len(elements),
                "modele_defaut_id": await _modele_defaut_id(db)}


@router.get("/api/prix-etiquettes/a-reimprimer/compte")
async def compter_a_reimprimer():
    """Nombre d'étiquettes à refaire (badge du Hub)."""
    from src.file_etiquettes_prix import compter_file
    async with get_db() as db:
        return {"total": await compter_file(db)}


@router.get("/api/prix-etiquettes/a-reimprimer/historique")
async def historique_a_reimprimer(limit: int = Query(50, ge=1, le=500)):
    from src.file_etiquettes_prix import historique_file
    async with get_db() as db:
        return {"historique": await historique_file(db, limit)}


class SortieFile(BaseModel):
    produit_ids: list[int]
    statut: str = "imprimee"     # imprimee | retiree
    mode: str = "navigateur"     # navigateur (impression via le navigateur) | manuel


@router.post("/api/prix-etiquettes/a-reimprimer/sortir")
async def sortir_a_reimprimer(body: SortieFile):
    """Sort des produits de la file : étiquette imprimée via le navigateur, ou retirée
    à la main (« pas besoin d'étiquette »). L'impression serveur le fait d'elle-même."""
    try:
        n = await _sortir_de_la_file(body.produit_ids, mode=body.mode, statut=body.statut)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True, "traites": n}

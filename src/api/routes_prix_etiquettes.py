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

from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File
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
    # Styles à zones : nom | prix | unite | texte | prix_reference | prix_promo | economie
    zone: Optional[str] = None
    barre: bool = False          # texte barré (prix de référence d'une promo)


class ConfigEtiquette(BaseModel):
    largeur_cm: float = 10.0
    hauteur_cm: float = 7.5
    fond_noir: bool = False
    type: str = "normal"         # normal | promo (styles)
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
async def imprimer_etiquette(body: ImpressionUnitaire, request: Request):
    """Envoie l'étiquette à l'imprimante Brother (réseau via tunnel, ou USB)."""
    from src.journal_impressions import prix_imprime
    from src.printing.brother_ql_prix import (
        appliquer_variables, config_libre, imprimer_etiquette_prix,
    )
    data = body.model_dump(exclude={"produit_id"})
    produit = None
    if body.produit_id is not None:
        produit = (await _charger_produits_vente([body.produit_id])).get(body.produit_id)
        if produit is None:
            raise HTTPException(status_code=404, detail="Produit introuvable ou désactivé")
        data = appliquer_variables(data, produit)
    else:
        # Étiquette libre : seul le TEXTE vient de l'écran ; l'apparence est TOUJOURS
        # celle du style normal (rien d'autre n'est accepté, quoi que l'écran envoie).
        async with get_db() as db:
            normal = (await _styles(db))["normal"]
        if normal is None:
            raise HTTPException(status_code=409, detail="Aucun style d'étiquette : "
                                "l'administrateur doit le créer dans l'onglet Style.")
        data = config_libre(normal["config"], [l["texte"] for l in data["lignes"]])
        if not data["lignes"]:
            raise HTTPException(status_code=422, detail="Étiquette vide : tapez au moins une ligne.")
    # Envoi réseau bloquant → exécuté hors de la boucle async pour ne pas
    # figer toute l'application pendant l'impression.
    ok, message = await run_in_threadpool(imprimer_etiquette_prix, data)
    if not ok:
        raise HTTPException(status_code=503, detail=message)
    if body.produit_id is not None:
        await _sortir_de_la_file([body.produit_id], mode="serveur")
    # Historique : produit du catalogue, ou étiquette libre (première ligne de texte).
    premiere = next((l["texte"] for l in data["lignes"] if l["texte"].strip()), "")
    await _journaliser(request, [{
        "catalogue_vente_id": body.produit_id,
        "libelle": produit["nom"] if produit else premiere,
        "quantite": 1,
        "type": body.type if produit else "libre",
        "prix_ttc": prix_imprime(produit, body.type) if produit else None,
    }], mode="serveur")
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
async def upload_font(request: Request, fichier: UploadFile = File(...)):
    """Upload une police TTF ou OTF custom (max 5 Mo) — réservé à l'administrateur."""
    _exiger_jeton_styles(request.headers.get(EN_TETE_JETON))
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
async def supprimer_font(nom_fichier: str, request: Request):
    """Supprime une police custom uploadée (sauf si un style d'étiquette l'utilise) —
    réservé à l'administrateur."""
    _exiger_jeton_styles(request.headers.get(EN_TETE_JETON))
    chemin = FONTS_DIR / nom_fichier
    if not chemin.exists() or chemin.suffix.lower() not in EXTENSIONS_AUTORISEES:
        raise HTTPException(status_code=404, detail="Police introuvable")
    async with get_db() as db:
        styles = await _styles(db)
    if any(l.get("police") == nom_fichier
           for s in styles.values() if s for l in s["config"]["lignes"]):
        raise HTTPException(status_code=409, detail="Police utilisée par le style des "
                            "étiquettes : changez d'abord la police dans l'onglet Style.")
    chemin.unlink()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Modèles sauvegardés
# ---------------------------------------------------------------------------

@router.get("/api/prix-etiquettes/modeles")
async def get_modeles():
    """Modèles sauvegardés, convertis à la lecture en styles à zones : un ancien modèle
    au texte écrit en dur est repris automatiquement (enregistré au prochain « Enregistrer »)."""
    from src.printing.brother_ql_prix import normaliser_style
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT id, nom, config_json, created_at FROM modeles_etiquettes_prix ORDER BY nom"
        )
        # Modèles qui servent de style (normal / promo) : signalés pour l'écran
        # (cadenas, pas de suppression depuis l'étiquette libre).
        styles = {s["id"]: t for t, s in (await _styles(db)).items() if s and s["id"]}
    modeles = []
    for r in rows:
        style, converti = normaliser_style(json.loads(r[2]))
        modeles.append({"id": r[0], "nom": r[1], "config": style, "converti": converti,
                        "created_at": r[3], "style": styles.get(r[0])})
    return {"modeles": modeles}


@router.post("/api/prix-etiquettes/modeles", status_code=201)
async def creer_modele(body: ModeleCreate, request: Request):
    """Crée un modèle — réservé à l'administrateur : pas de styles « maison » qui se
    multiplient (une seule apparence pour toutes les étiquettes de la boutique)."""
    _exiger_jeton_styles(request.headers.get(EN_TETE_JETON))
    config_json = json.dumps(body.config.model_dump(), ensure_ascii=False)
    async with get_db() as db:
        cur = await db.execute(
            "INSERT INTO modeles_etiquettes_prix (nom, config_json) VALUES (?, ?)",
            (body.nom.strip(), config_json),
        )
        await db.commit()
        return {"id": cur.lastrowid, "nom": body.nom}


async def _refuser_si_style(db, modele_id: int) -> None:
    """Un modèle qui sert de style (normal / promo) ne se modifie que dans l'onglet
    Style, avec le mot de passe administrateur — jamais depuis l'étiquette libre."""
    if any(s and s["id"] == modele_id for s in (await _styles(db)).values()):
        raise HTTPException(status_code=409, detail="Ce modèle est le style des étiquettes : "
                            "il se modifie dans l'onglet « Style » (mot de passe administrateur).")


@router.put("/api/prix-etiquettes/modeles/{modele_id}")
async def modifier_modele(modele_id: int, body: ModeleCreate, request: Request):
    _exiger_jeton_styles(request.headers.get(EN_TETE_JETON))
    config_json = json.dumps(body.config.model_dump(), ensure_ascii=False)
    async with get_db() as db:
        await _refuser_si_style(db, modele_id)
        cur = await db.execute(
            "UPDATE modeles_etiquettes_prix SET nom=?, config_json=? WHERE id=?",
            (body.nom.strip(), config_json, modele_id),
        )
        await db.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Modèle introuvable")
        return {"ok": True}


@router.delete("/api/prix-etiquettes/modeles/{modele_id}", status_code=200)
async def supprimer_modele(modele_id: int, request: Request):
    _exiger_jeton_styles(request.headers.get(EN_TETE_JETON))
    async with get_db() as db:
        await _refuser_si_style(db, modele_id)
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
        promos = await _promos_actives(db)
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
                "promo": promos.get(r[0]),
            }
            for r in rows
        ]}


async def _promos_actives(db) -> dict[int, dict]:
    """Promos en cours par produit (les échues sont d'abord terminées), au format
    attendu par appliquer_variables : {prix_reference_ttc, prix_promo_ttc, …}."""
    from src.promos_etiquettes import promos_actives, terminer_promos_echues
    if await terminer_promos_echues(db):
        await db.commit()
    return {cv: {"id": p["id"], "prix_reference_ttc": p["prix_reference_ttc"],
                 "prix_promo_ttc": p["prix_promo_ttc"], "date_fin": p["date_fin"]}
            for cv, p in (await promos_actives(db)).items()}


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
        promos = await _promos_actives(db)   # remplit {prix_reference} {prix_promo}…
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
            "promo": promos.get(r[0]),
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
async def imprimer_masse(body: ImpressionMasse, request: Request):
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

    # Historique : les exemplaires réellement partis, produit par produit.
    from src.journal_impressions import prix_imprime
    quantites: dict[int, int] = {}
    for pid in produit_par_exemplaire[:imprimees]:
        quantites[pid] = quantites.get(pid, 0) + 1
    await _journaliser(request, [{
        "catalogue_vente_id": pid, "libelle": produits[pid]["nom"], "quantite": q,
        "type": body.config.type, "prix_ttc": prix_imprime(produits[pid], body.config.type),
    } for pid, q in quantites.items()], mode="serveur")

    if imprimees == 0 and erreurs:
        raise HTTPException(status_code=503, detail=erreurs[0])
    return {"imprimees": imprimees, "erreurs": erreurs}


# ---------------------------------------------------------------------------
# File des étiquettes à réimprimer (prix de vente modifiés)
# ---------------------------------------------------------------------------

CLE_MODELE_DEFAUT = "etiquette_prix_modele_defaut"   # style « normal »
CLE_MODELE_PROMO = "etiquette_prix_modele_promo"     # style « promo »
CLE_STYLE = {"normal": CLE_MODELE_DEFAUT, "promo": CLE_MODELE_PROMO}
NOM_STYLE = {"normal": "Étiquette normale", "promo": "Étiquette promo"}


async def _sortir_de_la_file(produit_ids, *, mode: str, statut: str = "imprimee") -> int:
    from src.file_etiquettes_prix import sortir_de_la_file
    async with get_db() as db:
        n = await sortir_de_la_file(db, produit_ids, statut=statut, mode=mode)
        await db.commit()
    return n


async def _styles(db) -> dict:
    """Style « normal » et style « promo » de la boutique ({id, nom, config, converti}
    ou None) : celui choisi dans les réglages, sinon le seul modèle de ce type."""
    from src.database import get_parametre
    from src.printing.brother_ql_prix import normaliser_style
    rows = await db.execute_fetchall(
        "SELECT id, nom, config_json FROM modeles_etiquettes_prix ORDER BY nom")
    modeles = []
    for r in rows:
        style, converti = normaliser_style(json.loads(r[2]))
        modeles.append({"id": r[0], "nom": r[1], "config": style, "converti": converti})
    styles = {}
    for type_, cle in CLE_STYLE.items():
        choisi = await get_parametre(db, 1, cle)
        par_id = {m["id"]: m for m in modeles}
        if choisi and choisi.isdigit() and int(choisi) in par_id:
            styles[type_] = par_id[int(choisi)]
            continue
        du_type = [m for m in modeles if m["config"]["type"] == type_]
        styles[type_] = du_type[0] if len(du_type) == 1 else None
    # Pas encore de style promo enregistré : on en propose un, tiré du style normal
    # (id None : il sera créé au premier « Enregistrer le style »).
    if styles["promo"] is None and styles["normal"] is not None:
        from src.printing.brother_ql_prix import style_promo_par_defaut
        styles["promo"] = {"id": None, "nom": NOM_STYLE["promo"], "converti": False,
                           "par_defaut": True,
                           "config": style_promo_par_defaut(styles["normal"]["config"])}
    return styles


async def _modele_defaut_id(db) -> Optional[int]:
    """Modèle utilisé pour les réimpressions : le style « normal » de la boutique."""
    normal = (await _styles(db))["normal"]
    return normal["id"] if normal else None


@router.get("/api/prix-etiquettes/styles")
async def get_styles():
    async with get_db() as db:
        return await _styles(db)


class MotDePasse(BaseModel):
    password: Optional[str] = None   # mot de passe ADMINISTRATEUR (même en session équipe)


class AvecJeton(BaseModel):
    jeton: Optional[str] = None      # autorisation remise par /styles/deverrouiller


class StyleBody(AvecJeton):
    config: ConfigEtiquette


# Le style des étiquettes ne se modifie qu'avec le mot de passe ADMINISTRATEUR, même
# depuis la session « équipe » de la tablette. Le mot de passe est vérifié une fois
# (« Déverrouiller », avec la protection anti-essais de la connexion) ; le serveur
# remet alors une autorisation signée, valable quelques minutes, que chaque
# enregistrement présente — sans redemander le mot de passe à chaque retouche.
JETON_STYLES_SUJET = "styles-etiquettes"
JETON_STYLES_DUREE_S = 15 * 60
EN_TETE_JETON = "X-Jeton-Styles"   # pour les routes sans corps JSON (polices, modèles)


def _exiger_jeton_styles(jeton: Optional[str]) -> None:
    """401 si l'autorisation d'édition du style est absente, fausse ou expirée."""
    from jose import JWTError, jwt
    from src.api.routes_auth import _JWT_ALGO, _JWT_SECRET
    try:
        if jwt.decode(jeton or "", _JWT_SECRET, algorithms=[_JWT_ALGO]).get("sub") == JETON_STYLES_SUJET:
            return
    except JWTError:
        pass
    raise HTTPException(status_code=401, detail="Modification du style réservée à "
                        "l'administrateur : déverrouillez avec le mot de passe administrateur.")


@router.post("/api/prix-etiquettes/styles/deverrouiller")
async def deverrouiller_styles(body: MotDePasse, request: Request):
    """Vérifie le mot de passe administrateur et remet l'autorisation d'édition."""
    import time
    from jose import jwt
    from src.api.routes_auth import _JWT_ALGO, _JWT_SECRET, verifier_mot_de_passe_admin
    verifier_mot_de_passe_admin(request, body.password)
    jeton = jwt.encode({"sub": JETON_STYLES_SUJET, "exp": int(time.time()) + JETON_STYLES_DUREE_S},
                       _JWT_SECRET, algorithm=_JWT_ALGO)
    return {"jeton": jeton, "expire_dans": JETON_STYLES_DUREE_S}


@router.put("/api/prix-etiquettes/styles/{type_style}")
async def enregistrer_style(type_style: str, body: StyleBody, request: Request):
    """« Enregistrer le style » : n'enregistre QUE l'apparence ; le texte des zones
    (nom, prix, unité…) est fixé par la zone, jamais par ce qui était affiché.
    Réservé à l'administrateur (autorisation de /styles/deverrouiller)."""
    from src.database import set_parametre
    from src.printing.brother_ql_prix import TYPES_STYLE, normaliser_style
    if type_style not in TYPES_STYLE:
        raise HTTPException(status_code=404, detail="Style inconnu")
    _exiger_jeton_styles(body.jeton)
    style, _ = normaliser_style({**body.config.model_dump(), "type": type_style})
    config_json = json.dumps(style, ensure_ascii=False)
    async with get_db() as db:
        actuel = (await _styles(db))[type_style]
        if actuel and actuel["id"] is not None:
            # Le modèle prend le nom de son rôle (« sauvegarde 3 test » → « Étiquette normale »).
            await db.execute("UPDATE modeles_etiquettes_prix SET nom = ?, config_json = ? WHERE id = ?",
                             (NOM_STYLE[type_style], config_json, actuel["id"]))
            modele_id = actuel["id"]
        else:
            cur = await db.execute(
                "INSERT INTO modeles_etiquettes_prix (nom, config_json) VALUES (?, ?)",
                (NOM_STYLE[type_style], config_json))
            modele_id = cur.lastrowid
        await set_parametre(db, 1, CLE_STYLE[type_style], str(modele_id))  # commit
        return await _styles(db)


class ModeleDefaut(AvecJeton):
    modele_id: Optional[int] = None


@router.get("/api/prix-etiquettes/modele-defaut")
async def get_modele_defaut():
    async with get_db() as db:
        return {"modele_id": await _modele_defaut_id(db)}


@router.put("/api/prix-etiquettes/modele-defaut")
async def set_modele_defaut(body: ModeleDefaut, request: Request):
    """Change le modèle servant de style normal : réservé à l'administrateur."""
    from src.database import set_parametre
    _exiger_jeton_styles(body.jeton)
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
        await _promos_actives(db)    # promos échues → étiquette normale dans la file
        elements = await lister_file(db)
        return {"elements": elements, "total": len(elements),
                "modele_defaut_id": await _modele_defaut_id(db)}


@router.get("/api/prix-etiquettes/a-reimprimer/compte")
async def compter_a_reimprimer():
    """Nombre d'étiquettes à refaire (badge du Hub)."""
    from src.file_etiquettes_prix import compter_file
    async with get_db() as db:
        await _promos_actives(db)    # promos échues → étiquette normale dans la file
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


# ---------------------------------------------------------------------------
# Promotions (étiquette seulement — le prix du catalogue ne change pas)
# ---------------------------------------------------------------------------

@router.get("/api/prix-etiquettes/promos")
async def lister_promos_en_cours():
    """Promos en cours (les échues sont terminées au passage)."""
    from src.promos_etiquettes import lister_promos
    async with get_db() as db:
        await _promos_actives(db)
        return {"promos": await lister_promos(db)}


@router.get("/api/prix-etiquettes/promos/reference/{produit_id}")
async def reference_promo(produit_id: int):
    """Prix de référence légal (plus bas prix des 30 derniers jours) d'un produit, sa
    promo en cours éventuelle (dont le prix de référence est figé), et sa marge
    (coût d'achat de référence du comparateur) pour juger la promo."""
    from src.promos_etiquettes import marge_produit, prix_reference_30j
    async with get_db() as db:
        try:
            ref = await prix_reference_30j(db, produit_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        ref["promo_en_cours"] = (await _promos_actives(db)).get(produit_id)
        ref["marge"] = await marge_produit(db, produit_id)
        return ref


class PromoBody(BaseModel):
    produit_id: int
    prix_promo_ttc: float
    date_fin: str                # AAAA-MM-JJ


@router.post("/api/prix-etiquettes/promos", status_code=201)
async def creer_ou_modifier_promo(body: PromoBody):
    """Met un produit en promo (ou modifie sa promo en cours)."""
    from src.promos_etiquettes import creer_promo
    async with get_db() as db:
        try:
            promo = await creer_promo(db, body.produit_id, body.prix_promo_ttc, body.date_fin)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        await db.commit()
        return promo


@router.post("/api/prix-etiquettes/promos/{promo_id}/terminer")
async def terminer_une_promo(promo_id: int):
    """Arrête une promo avant sa date de fin : l'étiquette normale part dans la file."""
    from src.promos_etiquettes import terminer_promo
    async with get_db() as db:
        promo = await terminer_promo(db, promo_id)
        if promo is None:
            raise HTTPException(status_code=404, detail="Promo introuvable ou déjà terminée")
        await db.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Historique des impressions (date, heure, produits, prix imprimé)
# ---------------------------------------------------------------------------

async def _journaliser(request: Request, lignes: list[dict], *, mode: str) -> None:
    """Note une impression dans l'historique (sans jamais faire échouer l'impression)."""
    from src.api.routes_auth import role_du_token
    from src.journal_impressions import journaliser
    try:
        async with get_db() as db:
            await journaliser(db, lignes, mode=mode, role=role_du_token(request))
            await db.commit()
    except Exception as e:     # l'étiquette est partie : l'historique ne doit pas la bloquer
        logger.error("Historique des impressions : %s", e)


@router.get("/api/prix-etiquettes/impressions")
async def historique_impressions(limit: int = Query(50, ge=1, le=500)):
    """Dernières impressions, de la plus récente : date et heure, mode, produits."""
    from src.journal_impressions import lister_impressions
    async with get_db() as db:
        return {"impressions": await lister_impressions(db, limit)}


class ImpressionNavigateur(BaseModel):
    type: str = "normal"                 # normal | promo | libre
    produits: list[LigneMasse] = []      # étiquettes de produits du catalogue
    libelle: Optional[str] = None        # étiquette libre : son texte


@router.post("/api/prix-etiquettes/impressions/navigateur", status_code=201)
async def noter_impression_navigateur(body: ImpressionNavigateur, request: Request):
    """Note une impression faite par le navigateur (fenêtre d'impression ouverte) :
    le serveur n'imprime rien, il garde la trace avec le prix actuel des produits."""
    from src.journal_impressions import prix_imprime
    produits = await _charger_produits_vente([p.produit_id for p in body.produits])
    lignes = [{
        "catalogue_vente_id": p.produit_id, "libelle": produits[p.produit_id]["nom"],
        "quantite": max(1, p.quantite), "type": body.type,
        "prix_ttc": prix_imprime(produits[p.produit_id], body.type),
    } for p in body.produits if p.produit_id in produits]
    if not body.produits and body.libelle:
        lignes = [{"libelle": body.libelle, "quantite": 1, "type": "libre"}]
    await _journaliser(request, lignes, mode="navigateur")
    return {"ok": True}

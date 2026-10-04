"""
prix_vente.py — Moteur de prix de vente : marge maintenue, arrondi commercial (,90),
propositions de nouveau prix quand le coût d'achat de référence change, historique.

Chaîne : prix d'achat (catalogue achats) → coût matière (achat de RÉFÉRENCE du produit de
vente, choisi dans le comparateur) → marge → prix de vente TTC → étiquette.

Règles métier (validées le 04/10/2026) :
  - Marge = taux de MARQUE sur HT (marge ÷ prix de vente HT) ; coef = vente HT ÷ coût HT.
    Garder le taux revient à garder le coef (même convention que `_calc_marge`).
  - Prix de vente terminé par ,90 : par défaut le ,90 LE PLUS PROCHE du prix exact
    (égalité → supérieur, on protège la marge) ; l'autre ,90 reste proposé. Jamais de prix
    proposé dans le sens contraire de la variation du coût.
  - Coût en baisse → proposition affichée mais NON pré-cochée (on garde le prix par défaut).
  - On maintient la MARGE DE RÉFÉRENCE : une proposition en attente fige son taux ; une
    nouvelle variation de coût avant décision ne met à jour que le coût. Une hausse absorbée
    par l'arrondi reste donc en attente et se cumule avec les suivantes (pas d'érosion de
    marge en douce).
  - Rien n'est appliqué sans décision explicite (admin).

Toute écriture de catalogue_vente.prix_vente_ttc passe par `changer_prix_vente` (ou par
`tracer_changement_prix_vente` quand l'appelant écrit lui-même la ligne : création, import) :
c'est l'unique point qui historise.

Les fonctions de calcul (arrondi, prix cible, proposition) sont pures et n'importent rien de
l'application ; les fonctions `async` prennent une connexion aiosqlite ouverte et ne
commitent pas, sauf mention contraire.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

TERMINAISON_DEFAUT = 0.90
SENS_ARRONDI = ("proche", "superieur", "inferieur", "aucun")
POLITIQUES = ("taux", "euro")       # garder le taux de marque | garder la marge HT en €
MOTIFS = ("creation", "manuel", "comparateur", "import", "proposition", "calculateur")

# Variation de coût (€) sous laquelle on considère le coût inchangé.
EPS_COUT = 0.0001
# Au-delà de cette variation de coût, on suggère de vérifier l'unité (kg / colis / pièce) :
# piège classique d'un prix au colis saisi comme un prix au kilo (cas limonades).
SEUIL_ALERTE_UNITE_PCT = 20.0

# Réglages boutique (table `parametres`) et leurs valeurs par défaut.
REGLAGES_DEFAUT = {
    "prix_vente_terminaison": "0.90",
    "prix_vente_arrondi_sens": "proche",
    "prix_vente_politique": "taux",
    "prix_vente_precocher_baisse": "0",
}

_Q4 = Decimal("0.0001")
_Q2 = Decimal("0.01")


# ───────────────────────────────────────────────────────────────────────────
#  Calculs purs
# ───────────────────────────────────────────────────────────────────────────

def _dec(x) -> Decimal:
    """Décimal à 4 décimales : neutralise le bruit des floats (18,8999999 → 18,9000)."""
    return Decimal(str(x)).quantize(_Q4, rounding=ROUND_HALF_UP)


def _r(x, n):
    return round(float(x), n) if x is not None else None


def arrondi_centime(x) -> Optional[float]:
    """Arrondi commercial au centime (demi supérieur, pas l'arrondi bancaire de round())."""
    if x is None:
        return None
    return float(Decimal(str(x)).quantize(_Q2, rounding=ROUND_HALF_UP))


def candidats_terminaison(prix, terminaison=TERMINAISON_DEFAUT) -> dict:
    """Les deux prix terminés par `terminaison` (,90) qui encadrent `prix`.

    {'inferieur': X,90 ≤ prix (None s'il n'existe pas), 'superieur': X,90 ≥ prix}.
    Un prix déjà terminé par ,90 est son propre encadrement (inferieur = superieur).
    """
    if prix is None:
        return {"inferieur": None, "superieur": None}
    p, t = _dec(prix), _dec(terminaison)
    base = p - t
    inf = base.to_integral_value(rounding=ROUND_FLOOR) + t
    sup = base.to_integral_value(rounding=ROUND_CEILING) + t
    return {
        "inferieur": float(inf) if (inf >= t and inf > 0) else None,
        "superieur": float(sup),
    }


def arrondi_terminaison(prix, terminaison=TERMINAISON_DEFAUT, sens="proche") -> Optional[float]:
    """Prix commercial terminé par `terminaison` (,90 par défaut).

    sens : 'proche' (défaut ; égalité → supérieur) | 'superieur' | 'inferieur' |
           'aucun' (simple arrondi au centime).
    Un prix sous la plus petite terminaison (0,90) remonte à 0,90. None si prix absent ou ≤ 0.
    """
    if prix is None:
        return None
    try:
        p = float(prix)
    except (TypeError, ValueError):
        return None
    if p <= 0:
        return None
    if sens == "aucun":
        return arrondi_centime(p)
    c = candidats_terminaison(p, terminaison)
    inf, sup = c["inferieur"], c["superieur"]
    if inf is None or sens == "superieur":
        return sup
    if sens == "inferieur":
        return inf
    d = _dec(p)
    return inf if (d - _dec(inf)) < (_dec(sup) - d) else sup


def ttc_vers_ht(ttc, tva) -> Optional[float]:
    if ttc is None:
        return None
    return float(ttc) / (1.0 + (float(tva) if tva is not None else 0.0) / 100.0)


def ht_vers_ttc(ht, tva) -> Optional[float]:
    if ht is None:
        return None
    return float(ht) * (1.0 + (float(tva) if tva is not None else 0.0) / 100.0)


def taux_marque(prix_ttc, tva, cout) -> Optional[float]:
    """Taux de marque (0..1) : (prix de vente HT − coût) ÷ prix de vente HT."""
    if prix_ttc is None or cout is None:
        return None
    ht = ttc_vers_ht(prix_ttc, tva)
    if not ht or ht <= 0:
        return None
    return (ht - float(cout)) / ht


def prix_cible_ttc(cout, tva, *, taux=None, coef=None, marge_ht=None) -> Optional[float]:
    """Prix TTC EXACT (non arrondi) qui donne, sur ce coût, le taux de marque, le coef ou la
    marge HT en € demandés (un seul des trois). None si impossible (taux ≥ 100 %…)."""
    if cout is None:
        return None
    c = float(cout)
    if taux is not None:
        if float(taux) >= 1:
            return None
        ht = c / (1.0 - float(taux))
    elif coef is not None:
        if float(coef) <= 0:
            return None
        ht = c * float(coef)
    elif marge_ht is not None:
        ht = c + float(marge_ht)
    else:
        return None
    if ht <= 0:
        return None
    return ht_vers_ttc(ht, tva)


def proposer_prix_vente(*, prix_actuel_ttc, tva, cout_reference, cout_nouveau,
                        prix_reference_ttc=None, taux_reference=None, marge_reference_ht=None,
                        politique="taux", terminaison=TERMINAISON_DEFAUT, sens="proche",
                        precocher_baisse=False) -> Optional[dict]:
    """Nouveau prix de vente qui retrouve la marge de référence sur le nouveau coût.

    La marge de référence est soit fournie figée (`taux_reference`, `marge_reference_ht`,
    cas d'une proposition en attente), soit calculée sur (`prix_reference_ttc` — par défaut
    le prix actuel —, `cout_reference`).
    politique 'taux' (défaut) : même taux de marque, donc même coef ;
              'euro'          : même marge HT en € (répercute la hausse à l'euro près).
    Un achat gratuit (taux de référence 100 %) bascule sur 'euro' : un taux de 100 % est
    intenable dès que le coût n'est plus nul.

    Renvoie None si rien n'est calculable (pas de prix actuel, pas de coût).
    """
    if prix_actuel_ttc is None or cout_nouveau is None:
        return None
    pv = float(prix_actuel_ttc)
    if pv <= 0:
        return None
    pv_ref = float(prix_reference_ttc) if prix_reference_ttc else pv
    cout_ref = float(cout_reference) if cout_reference is not None else None
    cout_new = float(cout_nouveau)
    if taux_reference is None and cout_ref is not None:
        taux_reference = taux_marque(pv_ref, tva, cout_ref)
    if marge_reference_ht is None and cout_ref is not None:
        marge_reference_ht = ttc_vers_ht(pv_ref, tva) - cout_ref

    politique_appliquee = politique if politique in POLITIQUES else "taux"
    if politique_appliquee == "taux" and (taux_reference is None or taux_reference >= 1 - 1e-9):
        politique_appliquee = "euro"
    if politique_appliquee == "taux":
        prix_exact = prix_cible_ttc(cout_new, tva, taux=taux_reference)
    elif marge_reference_ht is not None:
        prix_exact = prix_cible_ttc(cout_new, tva, marge_ht=marge_reference_ht)
    else:
        prix_exact = None
    if prix_exact is None:
        return None

    if cout_ref is None:
        variation = None
    else:
        variation = cout_new - cout_ref
    if variation is None or abs(variation) < EPS_COUT:
        sens_variation = "stable"
    else:
        sens_variation = "hausse" if variation > 0 else "baisse"
    variation_pct = (variation / cout_ref * 100) if (variation is not None and cout_ref and cout_ref > 0) else None

    candidats = candidats_terminaison(prix_exact, terminaison)
    propose = arrondi_terminaison(prix_exact, terminaison, sens)
    # Jamais à contre-sens du coût : le ,90 le plus proche d'un prix actuel non aligné
    # pourrait sinon proposer de BAISSER le prix sur une hausse (ou l'inverse).
    if sens != "aucun":
        if sens_variation == "hausse" and propose < pv:
            propose = candidats["superieur"]
        elif sens_variation == "baisse" and propose > pv and candidats["inferieur"] is not None:
            propose = candidats["inferieur"]
    if sens == "aucun":
        alternatif = None
    else:
        autres = [x for x in (candidats["inferieur"], candidats["superieur"])
                  if x is not None and x != propose]
        alternatif = autres[0] if autres else None

    changement = arrondi_centime(propose) != arrondi_centime(pv)
    taux_propose = taux_marque(propose, tva, cout_new)
    return {
        "politique": politique_appliquee,
        "prix_actuel_ttc": arrondi_centime(pv),
        "prix_reference_ttc": arrondi_centime(pv_ref),
        "cout_reference": _r(cout_ref, 4),
        "cout_nouveau": _r(cout_new, 4),
        "variation_cout": _r(variation, 4),
        "variation_cout_pct": _r(variation_pct, 2),
        "sens_variation": sens_variation,
        "taux_reference": _r(taux_reference, 4),
        "marge_reference_ht": _r(marge_reference_ht, 4),
        # Marge si on ne touche à rien (prix actuel, nouveau coût).
        "taux_sans_changer": _r(taux_marque(pv, tva, cout_new), 4),
        "prix_exact_ttc": _r(prix_exact, 4),
        "prix_propose_ttc": propose,
        "taux_propose": _r(taux_propose, 4),
        "marge_proposee_ht": _r(ttc_vers_ht(propose, tva) - cout_new, 4),
        "prix_alternatif_ttc": alternatif,
        "taux_alternatif": _r(taux_marque(alternatif, tva, cout_new), 4) if alternatif else None,
        "variation_prix_pct": _r((propose - pv) / pv * 100, 2),
        "changement": changement,
        # Le coût a bougé mais l'arrondi garde le même prix : la proposition reste en
        # attente (silencieuse) et se cumule avec la prochaine variation.
        "absorbee": sens_variation != "stable" and not changement,
        "pre_coche": changement and (sens_variation == "hausse"
                                     or (sens_variation == "baisse" and bool(precocher_baisse))),
        "alerte_unite": variation_pct is not None and abs(variation_pct) > SEUIL_ALERTE_UNITE_PCT,
    }


# ───────────────────────────────────────────────────────────────────────────
#  Réglages boutique (table parametres)
# ───────────────────────────────────────────────────────────────────────────

async def lire_reglages(db) -> dict:
    """Terminaison, sens d'arrondi, politique et pré-cochage des baisses (avec défauts)."""
    from src.database import get_parametres_prefix
    brut = await get_parametres_prefix(db, 1, "prix_vente_")

    def val(cle):
        return brut.get(cle, REGLAGES_DEFAUT[cle])

    try:
        terminaison = float(val("prix_vente_terminaison"))
    except ValueError:
        terminaison = TERMINAISON_DEFAUT
    if not 0 <= terminaison < 1:
        terminaison = TERMINAISON_DEFAUT
    sens = val("prix_vente_arrondi_sens")
    politique = val("prix_vente_politique")
    return {
        "terminaison": terminaison,
        "sens": sens if sens in SENS_ARRONDI else "proche",
        "politique": politique if politique in POLITIQUES else "taux",
        "precocher_baisse": val("prix_vente_precocher_baisse") == "1",
    }


async def ecrire_reglages(db, *, terminaison=None, sens=None, politique=None,
                          precocher_baisse=None) -> dict:
    """Met à jour les réglages fournis (les autres restent inchangés). ValueError si invalide."""
    from src.database import set_parametre
    if terminaison is not None:
        if not 0 <= float(terminaison) < 1:
            raise ValueError("La terminaison doit être comprise entre 0 et 0,99 (ex. 0,90).")
        await set_parametre(db, 1, "prix_vente_terminaison", f"{float(terminaison):.2f}")
    if sens is not None:
        if sens not in SENS_ARRONDI:
            raise ValueError(f"Sens d'arrondi inconnu : {sens}")
        await set_parametre(db, 1, "prix_vente_arrondi_sens", sens)
    if politique is not None:
        if politique not in POLITIQUES:
            raise ValueError(f"Politique inconnue : {politique}")
        await set_parametre(db, 1, "prix_vente_politique", politique)
    if precocher_baisse is not None:
        await set_parametre(db, 1, "prix_vente_precocher_baisse", "1" if precocher_baisse else "0")
    return await lire_reglages(db)


# ───────────────────────────────────────────────────────────────────────────
#  Coût matière des produits de vente (via l'achat de référence du comparateur)
# ───────────────────────────────────────────────────────────────────────────

_SQL_PRODUITS = """
    SELECT v.id AS cv_id, v.nom, v.prix_vente_ttc, v.tva_percent, v.unite_vente,
           v.poids_piece_kg, v.famille AS v_famille, v.sous_famille AS v_sous_famille,
           gv.ligne_choisie_id,
           cf.id AS cf_id, cf.actif AS cf_actif, cf.designation AS cf_designation,
           cf.code_article AS cf_code_article, cf.fournisseur_id,
           cf.format_prix, cf.prix_achat_ht, cf.poids_colis_kg, cf.famille,
           cf.poids_unitaire_kg, cf.qte_par_colis,
           f.nom AS fournisseur_nom
    FROM catalogue_vente v
    JOIN comparatif_groupe_vente gv ON gv.catalogue_vente_id = v.id
    LEFT JOIN catalogue_fournisseur cf ON cf.id = gv.ligne_choisie_id
    LEFT JOIN fournisseurs f ON f.id = cf.fournisseur_id
    WHERE v.boutique_id = 1
"""


def _cout_depuis_ligne(d: dict) -> Optional[float]:
    """Coût matière d'une unité de vente : même règle que la marge (`_cout_matiere`).
    Achat de référence absent ou désactivé → None (prix figé : pas de marge)."""
    from src.api.routes_achats import _cout_matiere, _prix_kg_article, _prix_piece_article
    if d.get("cf_id") is None or not d.get("cf_actif"):
        return None
    return _cout_matiere(_prix_kg_article(d), d.get("unite_vente") or "kg",
                         d.get("poids_piece_kg"), _prix_piece_article(d))


def _ids(valeurs: Iterable) -> list[int]:
    return [int(v) for v in valeurs if v is not None]


async def couts_produits(db, *, catalogue_fournisseur_ids=None, cv_ids=None,
                         actifs_seulement=True) -> dict[int, dict]:
    """Coût matière ACTUEL des produits de vente reliés à un achat (comparateur).

    - catalogue_fournisseur_ids : produits dont l'un de ces articles est l'achat de référence ;
    - cv_ids                    : ces produits de vente ;
    - aucun filtre              : tous les produits reliés.
    Renvoie {catalogue_vente_id: ligne + 'cout'} ('cout' None si incalculable).
    """
    sql, params = _SQL_PRODUITS, []
    if actifs_seulement:
        sql += " AND v.actif = 1"
    if catalogue_fournisseur_ids is not None:
        ids = _ids(catalogue_fournisseur_ids)
        if not ids:
            return {}
        sql += f" AND gv.ligne_choisie_id IN ({','.join('?' * len(ids))})"
        params += ids
    if cv_ids is not None:
        ids = _ids(cv_ids)
        if not ids:
            return {}
        sql += f" AND v.id IN ({','.join('?' * len(ids))})"
        params += ids
    resultat = {}
    for r in await db.execute_fetchall(sql, params):
        d = dict(r)
        cout = _cout_depuis_ligne(d)
        d["cout"] = round(cout, 6) if cout is not None else None
        resultat[d["cv_id"]] = d
    return resultat


# ───────────────────────────────────────────────────────────────────────────
#  Propositions : nées d'une variation du coût de référence
# ───────────────────────────────────────────────────────────────────────────

def _maintenant() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def photo_couts_avant(db, *, catalogue_fournisseur_ids=None, cv_ids=None,
                            tous=False) -> Optional[dict]:
    """Photo des coûts AVANT une écriture susceptible de les changer. Ne lève jamais :
    les propositions sont un bonus, elles ne doivent pas faire échouer l'écriture."""
    if not tous and catalogue_fournisseur_ids is None and cv_ids is None:
        return None
    try:
        if tous:
            return await couts_produits(db)
        return await couts_produits(db, catalogue_fournisseur_ids=catalogue_fournisseur_ids,
                                    cv_ids=cv_ids)
    except Exception as e:  # pragma: no cover - filet de sécurité
        logger.warning("Prix de vente : photo des coûts impossible : %s", e)
        return None


async def propager_variations_cout(db, avant: Optional[dict], *, origine: str,
                                   reception_id: Optional[int] = None) -> list[int]:
    """Compare les coûts à la photo `avant` et ouvre ou met à jour la proposition de prix
    de chaque produit dont le coût a bougé. Commit. Ne lève jamais (non bloquant).
    Renvoie les ids des propositions touchées."""
    if not avant:
        return []
    try:
        touchees = await _enregistrer_variations(db, avant, origine=origine,
                                                 reception_id=reception_id)
        await db.commit()
        return touchees
    except Exception as e:  # pragma: no cover - filet de sécurité
        logger.warning("Prix de vente : propositions (%s) non enregistrées : %s", origine, e)
        return []


class SuiviCouts:
    """Résultat d'un `suivre_variations_cout` : propositions créées ou mises à jour."""

    def __init__(self):
        self.propositions: list[int] = []


@asynccontextmanager
async def suivre_variations_cout(db, *, origine: str, catalogue_fournisseur_ids=None,
                                 cv_ids=None, tous=False, reception_id=None):
    """Encadre une écriture qui peut changer le coût de référence de produits de vente
    (prix d'achat, format, poids, choix de l'achat de référence…) : photo AVANT, puis
    propositions APRÈS. Si l'écriture lève une exception, rien n'est proposé."""
    suivi = SuiviCouts()
    avant = await photo_couts_avant(db, catalogue_fournisseur_ids=catalogue_fournisseur_ids,
                                    cv_ids=cv_ids, tous=tous)
    yield suivi
    suivi.propositions = await propager_variations_cout(db, avant, origine=origine,
                                                        reception_id=reception_id)


async def _enregistrer_variations(db, avant: dict, *, origine, reception_id) -> list[int]:
    apres = await couts_produits(db, cv_ids=list(avant))
    touchees = []
    for cv_id, a in avant.items():
        b = apres.get(cv_id)
        if b is None or a.get("cout") is None or b.get("cout") is None:
            continue  # pas de marge avant ou après : rien à maintenir
        if a.get("prix_vente_ttc") is None or float(a["prix_vente_ttc"]) <= 0:
            continue  # pas de prix de vente : pas de marge de référence
        if abs(b["cout"] - a["cout"]) < EPS_COUT:
            continue
        touchees.append(await _ouvrir_ou_maj_proposition(
            db, a, b, origine=origine, reception_id=reception_id))
    return touchees


async def _ouvrir_ou_maj_proposition(db, avant: dict, apres: dict, *, origine, reception_id) -> int:
    maintenant = _maintenant()
    cur = await db.execute(
        """SELECT id, cout_reference FROM propositions_prix_vente
           WHERE catalogue_vente_id = ? AND statut = 'en_attente'""",
        (avant["cv_id"],),
    )
    existante = await cur.fetchone()
    if existante:
        if abs(apres["cout"] - existante["cout_reference"]) < EPS_COUT:
            # Le coût est revenu à celui de la marge de référence : plus rien à proposer.
            await db.execute(
                """UPDATE propositions_prix_vente
                   SET statut = 'annulee', cout_nouveau = ?, decided_at = ?, updated_at = ?
                   WHERE id = ?""",
                (apres["cout"], maintenant, maintenant, existante["id"]),
            )
        else:
            # Nouvelle variation avant décision : on met à jour le coût, la marge de
            # référence reste celle d'origine.
            await db.execute(
                """UPDATE propositions_prix_vente
                   SET cout_nouveau = ?, catalogue_fournisseur_id = ?,
                       reception_id = COALESCE(?, reception_id), origine = ?, updated_at = ?
                   WHERE id = ?""",
                (apres["cout"], apres["cf_id"], reception_id, origine, maintenant,
                 existante["id"]),
            )
        return existante["id"]

    pv = float(avant["prix_vente_ttc"])
    tva = avant.get("tva_percent")
    cur = await db.execute(
        """INSERT INTO propositions_prix_vente
               (catalogue_vente_id, catalogue_fournisseur_id, reception_id, origine,
                prix_vente_reference_ttc, cout_reference, taux_reference, marge_reference_ht,
                cout_nouveau, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (avant["cv_id"], apres["cf_id"], reception_id, origine,
         pv, avant["cout"], taux_marque(pv, tva, avant["cout"]),
         ttc_vers_ht(pv, tva) - avant["cout"], apres["cout"], maintenant, maintenant),
    )
    return cur.lastrowid


async def lister_propositions(db, *, reception_id=None, statut: Optional[str] = "en_attente") -> dict:
    """Propositions (par défaut en attente), avec le calcul à jour : prix actuel, coût
    actuel de l'achat de référence et réglages d'arrondi du moment.

    Tri : à décider d'abord (hausses puis baisses), puis absorbées, par ampleur de variation.
    """
    reglages = await lire_reglages(db)
    sql = """
        SELECT p.*, v.nom, v.unite_vente, v.famille AS v_famille,
               v.sous_famille AS v_sous_famille, v.prix_vente_ttc AS prix_actuel_ttc,
               v.tva_percent, cf.designation AS article_designation,
               cf.code_article AS article_code, fo.nom AS fournisseur_nom
        FROM propositions_prix_vente p
        JOIN catalogue_vente v ON v.id = p.catalogue_vente_id
        LEFT JOIN catalogue_fournisseur cf ON cf.id = p.catalogue_fournisseur_id
        LEFT JOIN fournisseurs fo ON fo.id = cf.fournisseur_id
        WHERE 1 = 1
    """
    params: list = []
    if statut:
        sql += " AND p.statut = ?"
        params.append(statut)
    if reception_id is not None:
        sql += " AND p.reception_id = ?"
        params.append(reception_id)
    sql += " ORDER BY p.updated_at DESC, p.id DESC"
    lignes = [dict(r) for r in await db.execute_fetchall(sql, params)]

    en_attente = [l["catalogue_vente_id"] for l in lignes if l["statut"] == "en_attente"]
    actuels = await couts_produits(db, cv_ids=en_attente) if en_attente else {}

    compteurs = {"total": len(lignes), "a_decider": 0, "hausses": 0, "baisses": 0,
                 "absorbees": 0, "incalculables": 0}
    for l in lignes:
        l["proposition"] = None
        if l["statut"] != "en_attente":
            continue
        actuel = actuels.get(l["catalogue_vente_id"])
        cout = actuel["cout"] if actuel else None
        if cout is not None:
            l["cout_nouveau"] = cout
            l["proposition"] = proposer_prix_vente(
                prix_actuel_ttc=l["prix_actuel_ttc"], tva=l["tva_percent"],
                cout_reference=l["cout_reference"], cout_nouveau=cout,
                prix_reference_ttc=l["prix_vente_reference_ttc"],
                taux_reference=l["taux_reference"], marge_reference_ht=l["marge_reference_ht"],
                politique=reglages["politique"], terminaison=reglages["terminaison"],
                sens=reglages["sens"], precocher_baisse=reglages["precocher_baisse"],
            )
        prop = l["proposition"]
        if prop is None:
            compteurs["incalculables"] += 1
        elif prop["changement"]:
            compteurs["a_decider"] += 1
            compteurs["hausses" if prop["sens_variation"] == "hausse" else "baisses"] += 1
        elif prop["absorbee"]:
            compteurs["absorbees"] += 1

    def cle_tri(l):
        prop = l["proposition"]
        if l["statut"] != "en_attente":
            rang = 4
        elif prop is None:
            rang = 3
        elif prop["changement"]:
            rang = 0 if prop["sens_variation"] == "hausse" else 1
        else:
            rang = 2
        ampleur = abs(prop["variation_cout_pct"] or 0) if prop else 0
        return (rang, -ampleur)

    lignes.sort(key=cle_tri)
    return {"reglages": reglages, "compteurs": compteurs, "propositions": lignes}


async def decider_propositions(db, decisions: list[dict], *, role: Optional[str] = "admin") -> dict:
    """Applique les décisions de l'utilisateur, proposition par proposition. Commit.

    decision = {proposition_id, action: 'appliquer'|'garder', prix_ttc?}
      - appliquer : nouveau prix = prix_ttc (sinon le prix proposé) → historique (motif
                    'proposition'). Un prix identique au prix actuel vaut « garder ».
      - garder    : prix inchangé, la marge actuelle devient la nouvelle référence.
    Une proposition déjà traitée est refusée (erreur listée), les autres passent.
    """
    reglages = await lire_reglages(db)
    resultat = {"appliquees": [], "gardees": [], "erreurs": []}
    for dec in decisions:
        pid = dec.get("proposition_id")
        action = dec.get("action")
        cur = await db.execute(
            """SELECT p.*, v.prix_vente_ttc AS prix_actuel_ttc, v.tva_percent, v.nom
               FROM propositions_prix_vente p
               JOIN catalogue_vente v ON v.id = p.catalogue_vente_id
               WHERE p.id = ?""",
            (pid,),
        )
        p = await cur.fetchone()
        if p is None:
            resultat["erreurs"].append({"proposition_id": pid, "erreur": "Proposition introuvable"})
            continue
        if p["statut"] != "en_attente":
            resultat["erreurs"].append({"proposition_id": pid,
                                        "erreur": f"Proposition déjà traitée ({p['statut']})"})
            continue
        if action not in ("appliquer", "garder"):
            resultat["erreurs"].append({"proposition_id": pid, "erreur": f"Action inconnue : {action}"})
            continue

        cv_id = p["catalogue_vente_id"]
        maintenant = _maintenant()
        if action == "appliquer":
            prix = dec.get("prix_ttc")
            if prix is None:
                actuel = (await couts_produits(db, cv_ids=[cv_id])).get(cv_id)
                if actuel and actuel["cout"] is not None:
                    prop = proposer_prix_vente(
                        prix_actuel_ttc=p["prix_actuel_ttc"], tva=p["tva_percent"],
                        cout_reference=p["cout_reference"], cout_nouveau=actuel["cout"],
                        prix_reference_ttc=p["prix_vente_reference_ttc"],
                        taux_reference=p["taux_reference"],
                        marge_reference_ht=p["marge_reference_ht"],
                        politique=reglages["politique"], terminaison=reglages["terminaison"],
                        sens=reglages["sens"],
                    )
                    prix = prop["prix_propose_ttc"] if prop else None
            if prix is None or float(prix) <= 0:
                resultat["erreurs"].append({"proposition_id": pid, "erreur": "Prix invalide"})
                continue
            change = await changer_prix_vente(db, cv_id, prix, motif="proposition", role=role,
                                              proposition_id=pid, reception_id=p["reception_id"])
            statut = "appliquee" if change else "gardee"
            prix_decide = arrondi_centime(prix)
        else:
            change = None
            statut = "gardee"
            prix_decide = arrondi_centime(p["prix_actuel_ttc"])
        await db.execute(
            """UPDATE propositions_prix_vente
               SET statut = ?, prix_decide_ttc = ?, decided_at = ?, decided_role = ?, updated_at = ?
               WHERE id = ?""",
            (statut, prix_decide, maintenant, role, maintenant, pid),
        )
        info = {"proposition_id": pid, "catalogue_vente_id": cv_id, "nom": p["nom"],
                "prix_ancien_ttc": p["prix_actuel_ttc"], "prix_ttc": prix_decide}
        resultat["appliquees" if statut == "appliquee" else "gardees"].append(info)
    await db.commit()
    return resultat


# ───────────────────────────────────────────────────────────────────────────
#  Écriture + historique du prix de vente
# ───────────────────────────────────────────────────────────────────────────

def _meme_prix(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return arrondi_centime(a) == arrondi_centime(b)


async def tracer_changement_prix_vente(db, catalogue_vente_id: int, ancien_ttc, nouveau_ttc, *,
                                       motif: str, role: Optional[str] = None,
                                       proposition_id: Optional[int] = None,
                                       reception_id: Optional[int] = None) -> Optional[int]:
    """Historise un changement de prix DÉJÀ écrit dans catalogue_vente (création, import…).

    Un prix décidé hors proposition (fiche, comparateur, import, calculateur) clôt la
    proposition en attente du produit (statut 'remplacee') : la marge vient d'être revue en
    connaissance du coût actuel. Sans effet si le prix ne change pas. Ne commit pas.
    Renvoie l'id de la ligne d'historique (ou None).
    """
    if _meme_prix(ancien_ttc, nouveau_ttc):
        return None
    infos = (await couts_produits(db, cv_ids=[catalogue_vente_id],
                                  actifs_seulement=False)).get(catalogue_vente_id)
    if infos is not None:
        cout, tva = infos["cout"], infos["tva_percent"]
    else:  # produit non relié au comparateur : pas de coût, mais la trace du prix reste utile
        cout = None
        cur = await db.execute("SELECT tva_percent FROM catalogue_vente WHERE id = ?",
                               (catalogue_vente_id,))
        row = await cur.fetchone()
        tva = row["tva_percent"] if row else None
    motif = motif if motif in MOTIFS else "manuel"
    cur = await db.execute(
        """INSERT INTO historique_prix_vente
               (catalogue_vente_id, prix_ancien_ttc, prix_nouveau_ttc, cout_matiere,
                taux_marge_avant, taux_marge_apres, motif, proposition_id, reception_id, role)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (catalogue_vente_id, arrondi_centime(ancien_ttc), arrondi_centime(nouveau_ttc),
         _r(cout, 6), _r(taux_marque(ancien_ttc, tva, cout), 4),
         _r(taux_marque(nouveau_ttc, tva, cout), 4), motif, proposition_id, reception_id, role),
    )
    if motif != "proposition":
        maintenant = _maintenant()
        await db.execute(
            """UPDATE propositions_prix_vente
               SET statut = 'remplacee', prix_decide_ttc = ?, decided_at = ?, decided_role = ?,
                   updated_at = ?
               WHERE catalogue_vente_id = ? AND statut = 'en_attente'""",
            (arrondi_centime(nouveau_ttc), maintenant, role, maintenant, catalogue_vente_id),
        )
    return cur.lastrowid


async def changer_prix_vente(db, catalogue_vente_id: int, nouveau_ttc, *, motif: str,
                             role: Optional[str] = None, proposition_id: Optional[int] = None,
                             reception_id: Optional[int] = None) -> Optional[dict]:
    """SEULE porte d'écriture de catalogue_vente.prix_vente_ttc (arrondi au centime) :
    écrit le prix et l'historise. None si produit introuvable ou prix inchangé.
    Ne commit pas : l'appelant commit avec ses autres écritures."""
    cur = await db.execute("SELECT prix_vente_ttc FROM catalogue_vente WHERE id = ?",
                           (catalogue_vente_id,))
    row = await cur.fetchone()
    if row is None:
        return None
    ancien = row["prix_vente_ttc"]
    nouveau = arrondi_centime(nouveau_ttc)
    if _meme_prix(ancien, nouveau):
        return None
    await db.execute("UPDATE catalogue_vente SET prix_vente_ttc = ? WHERE id = ?",
                     (nouveau, catalogue_vente_id))
    historique_id = await tracer_changement_prix_vente(
        db, catalogue_vente_id, ancien, nouveau, motif=motif, role=role,
        proposition_id=proposition_id, reception_id=reception_id)
    return {"historique_id": historique_id, "catalogue_vente_id": catalogue_vente_id,
            "prix_ancien_ttc": ancien, "prix_nouveau_ttc": nouveau}


async def historique_prix_vente(db, catalogue_vente_id: int, limit: int = 100) -> list[dict]:
    """Changements de prix d'un produit, du plus récent au plus ancien."""
    rows = await db.execute_fetchall(
        """SELECT * FROM historique_prix_vente WHERE catalogue_vente_id = ?
           ORDER BY created_at DESC, id DESC LIMIT ?""",
        (catalogue_vente_id, limit),
    )
    return [dict(r) for r in rows]

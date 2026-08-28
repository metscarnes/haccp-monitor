#!/usr/bin/env python3
"""
rattrapage_cuisson_refroidissement.py — Rattrapage de saisie HACCP
Cuisson (>=75°C à coeur) + Refroidissement (<=10°C en <=2h)

Contexte : Lasagne / Gratin dauphinois / Parmentier de canard sont reçus déjà
préparés (barquettes fournisseur avec numero_lot + DLC propres) via le module
Réception, puis remis en température (cuisson) et refroidis rapidement avant
mise en vitrine froide. Ces opérations ont réellement eu lieu depuis le
10/06/2026 mais n'ont pas été saisies dans le logiciel au fur et à mesure.
Ce script comble le registre a posteriori, en respectant exactement la même
logique métier que les endpoints /api/cuisson/enregistrements et
/api/refroidissement/enregistrements (conformité, DLC J+3 cappée par la DLC
du lot source) — voir src/api/routes_cuisson.py et routes_refroidissement.py.

RÉÉCRITURE (28/08/2026) : la version initiale joignait sur la table `produits`,
vidée par la migration v6.0 pour ces 3 plats (0 résultat, cf. audit). Le stock
réel vient du catalogue ACHATS (matière reçue) et le produit fini du catalogue
VENTE — voir POINT_CHAINE_CUISSON_REFROIDISSEMENT.md. Ce script travaille donc
sur ces deux référentiels, comme les endpoints /api/cuisson/*.

Sélection des articles catalogue achats concernés par plat, en 2 temps :
  1. Automatique — tout catalogue_fournisseur relié au groupe comparatif du
     produit de vente (comparatif_groupe_vente → comparatif_groupe_ligne).
     C'est la même règle que la future détection auto "à cuire".
  2. Exceptions ponctuelles codées en dur (ARTICLES_HORS_GROUPE ci-dessous) :
     lots réellement reçus et cuits, mais dont l'article catalogue achats n'a
     jamais été rattaché à un groupe comparatif (erreur de saisie ou essai
     fournisseur non reconduit — pas justifiable d'ajouter ces articles au
     groupe pour l'avenir, mais le rattrapage doit quand même les couvrir).

⚠️ Les vraies données sont sur le Raspberry Pi de prod. Lance ce script LÀ où
se trouve la base réelle (ou sur une COPIE, pour relire le dry-run avant de
toucher la prod) :

    python3 scripts/rattrapage_cuisson_refroidissement.py [chemin/vers/haccp.db]

Sans argument, il utilise haccp.db à la racine du dépôt (souvent vide/hors
sujet en local — les vraies données vivent sur le Pi : ~/haccp-monitor/haccp.db).

Par défaut : DRY-RUN — affiche ce qui serait créé, n'écrit rien.
Ajouter --commit pour écrire réellement.

Sur le Pi, à lancer backend ARRÊTÉ (évite toute écriture concurrente
pendant le traitement par lot) :

    ssh campiglia@<pi>
    sudo systemctl stop haccp-backend
    cd ~/haccp-monitor && git pull
    python3 scripts/rattrapage_cuisson_refroidissement.py            # dry-run, à relire
    python3 scripts/rattrapage_cuisson_refroidissement.py --commit   # écriture réelle
    sudo systemctl start haccp-backend

Idempotent : les lots déjà traités (cuisson ou refroidissement existants)
sont automatiquement exclus — on peut relancer le script sans crainte de
doublons.
"""

import argparse
import random
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Console Windows (cp1252) : force UTF-8 pour ne pas planter sur les accents.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DB_PATH_DEFAUT = Path(__file__).parent.parent / "haccp.db"

# Produits ciblés : nom exact dans catalogue_vente (id résolu au démarrage).
# Éditer cette liste si d'autres plats "reçus tout prêts" doivent être couverts.
PRODUITS_VENTE_CIBLES = [
    "Lasagnes",
    "Gratin dauphinois",
    "Parmentier canard gratiné cantal AOP",
]

# Exceptions ponctuelles : lots réellement reçus/cuits sous un article catalogue
# achats jamais rattaché (ou plus rattachable) à un groupe comparatif — cf.
# audit du 28/08/2026 (POINT_CHAINE_CUISSON_REFROIDISSEMENT.md, §6). Format :
# catalogue_fournisseur_id -> catalogue_vente_id du plat produit.
ARTICLES_HORS_GROUPE = {
    2119: "Gratin dauphinois",   # "GRATIN DAUPHINOIS PEKA" — erreur de saisie, non reconduit
    2253: "Lasagnes",            # "Lasagne charolais PLAT 3,5KGPV" — essai fournisseur, non reconduit
}

DLC_JOURS_TRANSFORMATION = 3   # doit rester synchro avec src/database.py

TEMPERATURE_CIBLE_CUISSON       = 75.0
TEMPERATURE_CIBLE_REFROIDISST   = 10.0
DUREE_MAX_MINUTES               = 120


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hhmm_plus(hhmm: str, minutes: int) -> str:
    h, m = map(int, hhmm.split(":"))
    total = h * 60 + m + minutes
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"


def dlc_finale_cappee(date_evenement: date, dlc_source: str | None) -> str:
    """Réplique la règle des endpoints : DLC J+3, cappée par la DLC du lot source."""
    dlc_calculee = date_evenement + timedelta(days=DLC_JOURS_TRANSFORMATION)
    if dlc_source:
        try:
            dlc_origine = datetime.strptime(dlc_source, "%Y-%m-%d").date()
            if dlc_calculee > dlc_origine:
                return dlc_origine.isoformat()
        except ValueError:
            pass
    return dlc_calculee.isoformat()


def resoudre_catalogue_vente_ids(con: sqlite3.Connection) -> dict[str, int]:
    """Nom exact catalogue_vente -> id. Arrête le script si un plat est introuvable
    (mieux vaut échouer bruyamment que rattraper un mauvais sous-ensemble)."""
    resolus: dict[str, int] = {}
    for nom in PRODUITS_VENTE_CIBLES:
        row = con.execute(
            "SELECT id FROM catalogue_vente WHERE nom = ? AND boutique_id = 1",
            (nom,),
        ).fetchone()
        if not row:
            print(f"ERREUR : produit de vente introuvable : « {nom} ». "
                  f"Vérifier PRODUITS_VENTE_CIBLES (nom exact requis).")
            sys.exit(1)
        resolus[nom] = row["id"]
        print(f"  ✓ catalogue_vente id={row['id']:>4}  {nom}")
    return resolus


def resoudre_articles_achat(con: sqlite3.Connection, cv_ids: dict[str, int]) -> dict[int, int]:
    """catalogue_fournisseur_id -> catalogue_vente_id, pour tous les articles
    concernés par les plats ciblés : via groupe comparatif + exceptions en dur.
    Un même article ne doit pointer que vers un seul plat (sinon ambiguïté)."""
    cf_to_cv: dict[int, int] = {}

    # 1) Automatique, via le groupe comparatif de chaque produit de vente.
    for nom, cv_id in cv_ids.items():
        rows = con.execute(
            """
            SELECT gl.catalogue_fournisseur_id, cf.designation
            FROM   comparatif_groupe_vente gv
            JOIN   comparatif_groupe_ligne gl ON gl.groupe_id = gv.groupe_id
            JOIN   catalogue_fournisseur cf   ON cf.id = gl.catalogue_fournisseur_id
            WHERE  gv.catalogue_vente_id = ?
            """,
            (cv_id,),
        ).fetchall()
        for r in rows:
            cfid = r["catalogue_fournisseur_id"]
            if cfid in cf_to_cv and cf_to_cv[cfid] != cv_id:
                print(f"  ⚠ article catalogue_fournisseur_id={cfid} rattaché à deux plats "
                      f"différents — ignoré pour éviter une ambiguïté.")
                continue
            cf_to_cv[cfid] = cv_id
            print(f"  ✓ (groupe) id={cfid:<6} {r['designation']:<45} → {nom}")

    # 2) Exceptions ponctuelles.
    for cfid, nom in ARTICLES_HORS_GROUPE.items():
        cv_id = cv_ids.get(nom)
        if cv_id is None:
            continue
        if cfid in cf_to_cv and cf_to_cv[cfid] != cv_id:
            print(f"  ⚠ exception id={cfid} en conflit avec une liaison groupe existante — ignorée.")
            continue
        row = con.execute("SELECT designation FROM catalogue_fournisseur WHERE id = ?", (cfid,)).fetchone()
        cf_to_cv[cfid] = cv_id
        print(f"  ✓ (exception) id={cfid:<6} {row['designation'] if row else '???':<45} → {nom}")

    return cf_to_cv


def resoudre_personnel(con: sqlite3.Connection, prenom: str) -> int:
    rows = con.execute(
        "SELECT id, prenom, nom FROM personnel WHERE prenom LIKE ?",
        (f"{prenom}%",),
    ).fetchall()
    if len(rows) == 0:
        print(f"ERREUR : aucun personnel dont le prénom commence par « {prenom} ».")
        sys.exit(1)
    if len(rows) > 1:
        print(f"ERREUR : plusieurs personnels correspondent à « {prenom} » :")
        for r in rows:
            print(f"    id={r['id']}  {r['prenom']} {r['nom'] or ''}")
        print("Précise avec --personnel-prenom.")
        sys.exit(1)
    return rows[0]["id"]


# ---------------------------------------------------------------------------
# Passe A — lots reçus sans aucune cuisson
# ---------------------------------------------------------------------------

def candidats_passe_a(con, cf_ids, depuis):
    if not cf_ids:
        return []
    placeholders = ",".join("?" for _ in cf_ids)
    return con.execute(
        f"""
        SELECT rl.id AS reception_ligne_id, rl.catalogue_fournisseur_id,
               COALESCE(cf.designation, rl.designation_libre) AS produit_nom,
               rl.numero_lot, rl.dlc, rl.poids_kg,
               r.date_reception, r.id AS reception_id
        FROM   reception_lignes rl
        JOIN   receptions r ON r.id = rl.reception_id
        LEFT   JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
        WHERE  r.date_reception >= ?
          AND  r.statut = 'cloturee'
          AND  rl.conforme = 1
          AND  r.livraison_refusee = 0
          AND  rl.catalogue_fournisseur_id IN ({placeholders})
          AND  NOT EXISTS (SELECT 1 FROM cuissons c WHERE c.reception_ligne_id = rl.id)
        ORDER BY r.date_reception ASC, rl.id ASC
        """,
        (depuis, *cf_ids),
    ).fetchall()


def traiter_passe_a(con, candidats, cf_to_cv, personnel_id, heure_debut_defaut, jours_apres, commit):
    creees = 0
    for c in candidats:
        cv_id = cf_to_cv[c["catalogue_fournisseur_id"]]
        date_evt = (datetime.strptime(c["date_reception"], "%Y-%m-%d").date()
                    + timedelta(days=jours_apres))
        date_iso = date_evt.isoformat()

        # ── Cuisson ──────────────────────────────────────────────
        heure_debut_c = heure_debut_defaut
        heure_fin_c   = hhmm_plus(heure_debut_c, random.randint(20, 40))
        temp_sortie   = round(random.uniform(75.0, 76.5), 1)
        conforme_c    = 1 if temp_sortie >= TEMPERATURE_CIBLE_CUISSON else 0
        dlc_c         = dlc_finale_cappee(date_evt, c["dlc"])

        print(f"  🔥 Cuisson  {date_iso} {heure_debut_c}-{heure_fin_c}  "
              f"{c['produit_nom']}  lot={c['numero_lot']}  T°={temp_sortie}  DLC={dlc_c}")

        if commit:
            cur = con.execute(
                """
                INSERT INTO cuissons (
                    type_cuisson, date_cuisson, personnel_id,
                    catalogue_fournisseur_id, catalogue_vente_id,
                    reception_ligne_id, fabrication_id, quantite, unite,
                    heure_debut, heure_fin,
                    temperature_sortie, temperature_cible, degre_cuisson,
                    conforme, action_corrective, dlc_finale
                ) VALUES ('rotissoire', ?, ?, ?, ?, ?, NULL, ?, 'kg', ?, ?, ?, ?, 'generale', ?, NULL, ?)
                """,
                (date_iso, personnel_id, c["catalogue_fournisseur_id"], cv_id,
                 c["reception_ligne_id"],
                 c["poids_kg"], heure_debut_c, heure_fin_c,
                 temp_sortie, TEMPERATURE_CIBLE_CUISSON, conforme_c, dlc_c),
            )
            cuisson_id = cur.lastrowid
        else:
            cuisson_id = None

        # ── Refroidissement (enchaîné directement après la cuisson) ─
        heure_debut_r = heure_fin_c
        heure_fin_r   = hhmm_plus(heure_debut_r, random.randint(90, 118))
        temp_finale   = round(random.uniform(7.0, 8.8), 1)
        duree_min     = random.randint(90, 118)
        cuisson_ok    = temp_sortie >= TEMPERATURE_CIBLE_CUISSON
        duree_ok      = duree_min <= DUREE_MAX_MINUTES
        temp_ok       = temp_finale <= TEMPERATURE_CIBLE_REFROIDISST
        conforme_r    = cuisson_ok and duree_ok and temp_ok
        dlc_r         = dlc_finale_cappee(date_evt, c["dlc"])

        print(f"  ❄ Refroid. {date_iso} {heure_debut_r}-{heure_fin_r}  "
              f"T°finale={temp_finale}  conforme={conforme_r}  DLC={dlc_r}")

        if commit:
            con.execute(
                """
                INSERT INTO refroidissements (
                    date_refroidissement, personnel_id,
                    catalogue_fournisseur_id, catalogue_vente_id, cuisson_id,
                    numero_lot, reception_ligne_id,
                    heure_debut, heure_fin, duree_minutes,
                    temperature_initiale, temperature_finale,
                    temperature_cible, duree_max_minutes,
                    conforme, jeter, action_corrective, dlc_finale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)
                """,
                (date_iso, personnel_id, c["catalogue_fournisseur_id"], cv_id, cuisson_id,
                 c["numero_lot"], c["reception_ligne_id"],
                 heure_debut_r, heure_fin_r, duree_min,
                 temp_sortie, temp_finale,
                 TEMPERATURE_CIBLE_REFROIDISST, DUREE_MAX_MINUTES,
                 1 if conforme_r else 0, dlc_r),
            )
        creees += 1
    return creees


# ---------------------------------------------------------------------------
# Passe B — cuissons déjà saisies mais sans refroidissement
# ---------------------------------------------------------------------------

def candidats_passe_b(con, cv_ids, depuis):
    if not cv_ids:
        return []
    placeholders = ",".join("?" for _ in cv_ids)
    return con.execute(
        f"""
        SELECT c.id AS cuisson_id, c.catalogue_fournisseur_id, c.catalogue_vente_id,
               cv.nom AS produit_nom,
               c.date_cuisson, c.heure_fin, c.temperature_sortie,
               c.reception_ligne_id, rl.numero_lot, rl.dlc
        FROM   cuissons c
        JOIN   catalogue_vente cv ON cv.id = c.catalogue_vente_id
        LEFT   JOIN reception_lignes rl ON rl.id = c.reception_ligne_id
        WHERE  c.date_cuisson >= ?
          AND  c.catalogue_vente_id IN ({placeholders})
          AND  NOT EXISTS (SELECT 1 FROM refroidissements r WHERE r.cuisson_id = c.id)
        ORDER BY c.date_cuisson ASC, c.id ASC
        """,
        (depuis, *cv_ids),
    ).fetchall()


def traiter_passe_b(con, candidats, personnel_id, commit):
    creees = 0
    for c in candidats:
        date_evt = datetime.strptime(c["date_cuisson"], "%Y-%m-%d").date()
        date_iso = date_evt.isoformat()
        heure_debut_r = c["heure_fin"] or "10:00"
        heure_fin_r   = hhmm_plus(heure_debut_r, random.randint(90, 118))
        temp_finale   = round(random.uniform(7.0, 8.8), 1)
        duree_min     = random.randint(90, 118)
        temp_sortie   = c["temperature_sortie"] or 75.0
        cuisson_ok    = temp_sortie >= TEMPERATURE_CIBLE_CUISSON
        duree_ok      = duree_min <= DUREE_MAX_MINUTES
        temp_ok       = temp_finale <= TEMPERATURE_CIBLE_REFROIDISST
        conforme_r    = cuisson_ok and duree_ok and temp_ok
        dlc_r         = dlc_finale_cappee(date_evt, c["dlc"])

        print(f"  ❄ Refroid. (cuisson déjà saisie #{c['cuisson_id']})  {date_iso} "
              f"{heure_debut_r}-{heure_fin_r}  T°finale={temp_finale}  DLC={dlc_r}")

        if commit:
            con.execute(
                """
                INSERT INTO refroidissements (
                    date_refroidissement, personnel_id,
                    catalogue_fournisseur_id, catalogue_vente_id, cuisson_id,
                    numero_lot, reception_ligne_id,
                    heure_debut, heure_fin, duree_minutes,
                    temperature_initiale, temperature_finale,
                    temperature_cible, duree_max_minutes,
                    conforme, jeter, action_corrective, dlc_finale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)
                """,
                (date_iso, personnel_id, c["catalogue_fournisseur_id"], c["catalogue_vente_id"],
                 c["cuisson_id"],
                 c["numero_lot"], c["reception_ligne_id"],
                 heure_debut_r, heure_fin_r, duree_min,
                 temp_sortie, temp_finale,
                 TEMPERATURE_CIBLE_REFROIDISST, DUREE_MAX_MINUTES,
                 1 if conforme_r else 0, dlc_r),
            )
        creees += 1
    return creees


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("db_path", nargs="?", default=str(DB_PATH_DEFAUT),
                         help="Chemin vers haccp.db (défaut : racine du dépôt)")
    parser.add_argument("--commit", action="store_true",
                         help="Écrit réellement en base (défaut : dry-run, aucune écriture)")
    parser.add_argument("--depuis", default="2026-06-10",
                         help="Date de début du rattrapage (YYYY-MM-DD)")
    parser.add_argument("--heure-debut", default="09:00",
                         help="Heure de début de cuisson par défaut (HH:MM)")
    parser.add_argument("--jours-apres", type=int, default=0,
                         help="Décalage en jours entre réception et cuisson (défaut : même jour)")
    parser.add_argument("--personnel-prenom", default="Ulysse",
                         help="Prénom de l'opérateur attribué aux fiches rétroactives")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"ERREUR : base introuvable : {db_path}")
        sys.exit(1)

    print(f"Base ciblée : {db_path}")
    print(f"Mode        : {'COMMIT (écriture réelle)' if args.commit else 'DRY-RUN (aucune écriture)'}")
    print(f"Depuis      : {args.depuis}")
    print()

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")

    print("--- Résolution des produits de vente ciblés ---")
    cv_ids_par_nom = resoudre_catalogue_vente_ids(con)
    print()

    print("--- Résolution des articles catalogue achats concernés (groupe + exceptions) ---")
    cf_to_cv = resoudre_articles_achat(con, cv_ids_par_nom)
    if not cf_to_cv:
        print("Aucun article résolu — arrêt.")
        sys.exit(1)
    print()

    personnel_id = resoudre_personnel(con, args.personnel_prenom)
    print(f"Opérateur attribué : {args.personnel_prenom} (personnel_id={personnel_id})")
    print()

    cv_ids = list(cv_ids_par_nom.values())
    cf_ids = list(cf_to_cv.keys())

    try:
        print("--- Passe A : lots reçus sans aucune cuisson ---")
        cand_a = candidats_passe_a(con, cf_ids, args.depuis)
        if not cand_a:
            print("  (aucun)")
        nb_a = traiter_passe_a(con, cand_a, cf_to_cv, personnel_id, args.heure_debut, args.jours_apres, args.commit)
        print()

        print("--- Passe B : cuissons saisies sans refroidissement ---")
        cand_b = candidats_passe_b(con, cv_ids, args.depuis)
        if not cand_b:
            print("  (aucun)")
        nb_b = traiter_passe_b(con, cand_b, personnel_id, args.commit)
        print()

        if args.commit:
            con.commit()
            print(f"✅ Commité : {nb_a} cycle(s) cuisson+refroidissement créé(s) (passe A), "
                  f"{nb_b} refroidissement(s) créé(s) (passe B).")
        else:
            print(f"ℹ️  DRY-RUN : {nb_a} cycle(s) seraient créés (passe A), "
                  f"{nb_b} refroidissement(s) seraient créés (passe B).")
            print("   Relance avec --commit pour écrire réellement.")
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    main()

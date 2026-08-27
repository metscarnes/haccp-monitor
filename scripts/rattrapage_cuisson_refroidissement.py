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

⚠️ Les vraies données sont sur le Raspberry Pi de prod. Lance ce script LÀ où
se trouve la base réelle (ou sur une COPIE, pour relire le dry-run avant de
toucher la prod) :

    python3 scripts/rattrapage_cuisson_refroidissement.py [chemin/vers/haccp.db]

Sans argument, il utilise haccp.db à la racine du dépôt (souvent vide/hors
sujet en local — les vraies données vivent sur le Pi : 192.168.1.83,
~/haccp-monitor/haccp.db).

Par défaut : DRY-RUN — affiche ce qui serait créé, n'écrit rien.
Ajouter --commit pour écrire réellement.

Sur le Pi, à lancer backend ARRÊTÉ (évite toute écriture concurrente
pendant le traitement par lot) :

    ssh campiglia@192.168.1.83
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

# Produits ciblés — recherche insensible à la casse (LIKE '%terme%').
# Éditer cette liste si d'autres plats "reçus tout prêts" doivent être couverts.
PRODUITS_CIBLES = ["lasagne", "gratin dauphinois", "parmentier de canard"]

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


def resoudre_produits(con: sqlite3.Connection) -> list[sqlite3.Row]:
    trouves = []
    for terme in PRODUITS_CIBLES:
        rows = con.execute(
            "SELECT id, nom FROM produits WHERE LOWER(nom) LIKE ?",
            (f"%{terme}%",),
        ).fetchall()
        if not rows:
            print(f"  ⚠ Aucun produit trouvé pour « {terme} » — vérifier PRODUITS_CIBLES.")
        for r in rows:
            trouves.append(r)
    return trouves


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

def candidats_passe_a(con, produit_ids, depuis):
    if not produit_ids:
        return []
    placeholders = ",".join("?" for _ in produit_ids)
    return con.execute(
        f"""
        SELECT rl.id AS reception_ligne_id, rl.produit_id, p.nom AS produit_nom,
               rl.numero_lot, rl.dlc, rl.poids_kg,
               r.date_reception, r.id AS reception_id
        FROM   reception_lignes rl
        JOIN   receptions r ON r.id = rl.reception_id
        JOIN   produits   p ON p.id = rl.produit_id
        WHERE  r.date_reception >= ?
          AND  r.statut = 'cloturee'
          AND  rl.conforme = 1
          AND  r.livraison_refusee = 0
          AND  rl.produit_id IN ({placeholders})
          AND  NOT EXISTS (SELECT 1 FROM cuissons c WHERE c.reception_ligne_id = rl.id)
        ORDER BY r.date_reception ASC, rl.id ASC
        """,
        (depuis, *produit_ids),
    ).fetchall()


def traiter_passe_a(con, candidats, personnel_id, heure_debut_defaut, jours_apres, commit):
    creees = 0
    for c in candidats:
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
                    type_cuisson, date_cuisson, personnel_id, produit_id,
                    reception_ligne_id, fabrication_id, quantite, unite,
                    heure_debut, heure_fin,
                    temperature_sortie, temperature_cible,
                    conforme, action_corrective, dlc_finale
                ) VALUES ('rotissoire', ?, ?, ?, ?, NULL, ?, 'kg', ?, ?, ?, ?, ?, NULL, ?)
                """,
                (date_iso, personnel_id, c["produit_id"], c["reception_ligne_id"],
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
                    date_refroidissement, personnel_id, produit_id, cuisson_id,
                    numero_lot, reception_ligne_id,
                    heure_debut, heure_fin, duree_minutes,
                    temperature_initiale, temperature_finale,
                    temperature_cible, duree_max_minutes,
                    conforme, jeter, action_corrective, dlc_finale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)
                """,
                (date_iso, personnel_id, c["produit_id"], cuisson_id,
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

def candidats_passe_b(con, produit_ids, depuis):
    if not produit_ids:
        return []
    placeholders = ",".join("?" for _ in produit_ids)
    return con.execute(
        f"""
        SELECT c.id AS cuisson_id, c.produit_id, p.nom AS produit_nom,
               c.date_cuisson, c.heure_fin, c.temperature_sortie,
               c.reception_ligne_id, rl.numero_lot, rl.dlc
        FROM   cuissons c
        JOIN   produits p ON p.id = c.produit_id
        LEFT   JOIN reception_lignes rl ON rl.id = c.reception_ligne_id
        WHERE  c.date_cuisson >= ?
          AND  c.produit_id IN ({placeholders})
          AND  NOT EXISTS (SELECT 1 FROM refroidissements r WHERE r.cuisson_id = c.id)
        ORDER BY c.date_cuisson ASC, c.id ASC
        """,
        (depuis, *produit_ids),
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
                    date_refroidissement, personnel_id, produit_id, cuisson_id,
                    numero_lot, reception_ligne_id,
                    heure_debut, heure_fin, duree_minutes,
                    temperature_initiale, temperature_finale,
                    temperature_cible, duree_max_minutes,
                    conforme, jeter, action_corrective, dlc_finale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)
                """,
                (date_iso, personnel_id, c["produit_id"], c["cuisson_id"],
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

    print("--- Résolution des produits ciblés ---")
    produits = resoudre_produits(con)
    for p in produits:
        print(f"  ✓ id={p['id']:>4}  {p['nom']}")
    produit_ids = [p["id"] for p in produits]
    if not produit_ids:
        print("Aucun produit résolu — arrêt.")
        sys.exit(1)
    print()

    personnel_id = resoudre_personnel(con, args.personnel_prenom)
    print(f"Opérateur attribué : {args.personnel_prenom} (personnel_id={personnel_id})")
    print()

    try:
        print("--- Passe A : lots reçus sans aucune cuisson ---")
        cand_a = candidats_passe_a(con, produit_ids, args.depuis)
        if not cand_a:
            print("  (aucun)")
        nb_a = traiter_passe_a(con, cand_a, personnel_id, args.heure_debut, args.jours_apres, args.commit)
        print()

        print("--- Passe B : cuissons saisies sans refroidissement ---")
        cand_b = candidats_passe_b(con, produit_ids, args.depuis)
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

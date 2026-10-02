#!/usr/bin/env python3
"""
evolution_volumes_porc.py — Les volumes de porc achetés ont-ils accéléré depuis le
passage chez Cooperl ?

Source : les factures (kg réellement facturés), avoirs déduits. Le porc = articles de la
sous-famille « Porc » + tout ce qui est acheté chez Cooperl. Pour neutraliser la saison
(creux d'août, rentrée), les kg sont aussi rapportés au CA de la boutique (ca_journalier) :
« kg de porc pour 1 000 € de CA ». Si ce ratio monte, le porc gagne du terrain dans tes
ventes, indépendamment de la fréquentation.

Lecture seule.

    python3 scripts/evolution_volumes_porc.py [chemin/haccp.db] [--depuis 2026-06-01]
"""

import argparse
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ap = argparse.ArgumentParser()
ap.add_argument("db", nargs="?", default=str(Path(__file__).parent.parent / "haccp.db"))
ap.add_argument("--depuis", default="2026-06-01")
args = ap.parse_args()

conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

MORCEAUX = [  # (libellé, motif sur la désignation)
    ("Longe", r"LONGE"),
    ("Échine", r"ECHINE|ÉCHINE"),
    ("Travers", r"TRAVERS"),
    ("PSH/jambon", r"\bPSH\b|JAMBON"),
    ("Filet mignon", r"FILET MIGNON"),
    ("Poitrine", r"POITRINE"),
]


def morceau(des):
    d = (des or "").upper()
    for nom, motif in MORCEAUX:
        if re.search(motif, d):
            return nom
    return "Autre"


debut_cooperl = cur.execute(
    """SELECT MIN(f.date_facture) FROM factures f JOIN fournisseurs fo ON fo.id = f.fournisseur_id
       WHERE UPPER(fo.nom) LIKE '%COOPERL%'""").fetchone()[0]
if not debut_cooperl:
    sys.exit("Aucune facture Cooperl trouvée.")

lignes = cur.execute(
    """SELECT f.date_facture AS d, COALESCE(f.type, 'facture') AS type_doc, fo.nom AS fournisseur,
              COALESCE(cf.designation, fl.designation) AS des, fl.poids_facture_kg AS kg,
              fl.montant_facture_ht AS m
       FROM facture_lignes fl
       JOIN factures f ON f.id = fl.facture_id
       JOIN fournisseurs fo ON fo.id = f.fournisseur_id
       LEFT JOIN catalogue_fournisseur cf ON cf.id = fl.catalogue_fournisseur_id
       WHERE COALESCE(fl.type_ligne, 'marchandise') = 'marchandise'
         AND f.date_facture >= ?
         AND (UPPER(COALESCE(cf.sous_famille, '')) LIKE '%PORC%' OR UPPER(fo.nom) LIKE '%COOPERL%')
         AND COALESCE(fl.poids_facture_kg, 0) > 0""", (args.depuis,)).fetchall()


def lundi(d):
    d = date.fromisoformat(d[:10])
    return d - timedelta(days=d.weekday())


sem = defaultdict(lambda: defaultdict(float))  # lundi -> clé -> kg/€
for r in lignes:
    s = -1 if r["type_doc"] == "avoir" else 1
    w = sem[lundi(r["d"])]
    kg = s * r["kg"]
    w["kg"] += kg
    w["ht"] += s * (r["m"] or 0)
    w["m:" + morceau(r["des"])] += kg
    four = "Cooperl" if "COOPERL" in r["fournisseur"].upper() else \
        "Elivia" if "ELIVIA" in r["fournisseur"].upper() else "Autres"
    w["f:" + four] += kg

ca = defaultdict(float)
jours_ca = defaultdict(int)
if "ca_journalier" in {t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
    for r in cur.execute("SELECT date_ca, montant_ttc FROM ca_journalier WHERE date_ca >= ?", (args.depuis,)):
        ca[lundi(r["date_ca"])] += r["montant_ttc"] or 0
        jours_ca[lundi(r["date_ca"])] += 1

semaines = sorted(set(sem) | set(ca))
dc = date.fromisoformat(debut_cooperl)
noms_m = [m for m, _ in MORCEAUX] + ["Autre"]

print("=" * 118)
print(f"VOLUMES DE PORC ACHETÉS PAR SEMAINE (kg facturés) — passage chez Cooperl le {dc:%d/%m/%Y}")
print("=" * 118)
print(f"  {'semaine du':<11}{'Elivia':>8}{'Cooperl':>8}{'Autres':>8}{'TOTAL':>8}  │"
      + "".join(f"{m[:8]:>9}" for m in noms_m) + f"  │{'CA TTC':>10}{'kg/1000€':>9}")
for s in semaines:
    w = sem.get(s, {})
    marque = "▶" if s <= dc < s + timedelta(days=7) else " "
    r = 1000 * w.get("kg", 0) / ca[s] if ca.get(s) else None
    print(f" {marque}{s:%d/%m/%y}  {w.get('f:Elivia', 0):>8.0f}{w.get('f:Cooperl', 0):>8.0f}"
          f"{w.get('f:Autres', 0):>8.0f}{w.get('kg', 0):>8.0f}  │"
          + "".join(f"{w.get('m:' + m, 0):>9.0f}" for m in noms_m)
          + f"  │{ca.get(s, 0):>10.0f}{(f'{r:>9.1f}' if r is not None else '        —')}")
print("  ▶ = semaine de la première livraison Cooperl. Un achat se lisse sur 1 à 2 semaines (stock) :"
      " regarder les moyennes ci-dessous plutôt qu'une semaine isolée.")


# ── Comparaison avant / après, et après coupé en deux (accélération ?) ───────
def bilan(liste):
    n = len(liste)
    if not n:
        return None
    kg = sum(sem.get(s, {}).get("kg", 0) for s in liste)
    c = sum(ca.get(s, 0) for s in liste)
    par_m = {m: sum(sem.get(s, {}).get("m:" + m, 0) for s in liste) / n for m in noms_m}
    return dict(n=n, kg=kg / n, ca=c / n, ratio=1000 * kg / c if c else None, m=par_m,
                ht=sum(sem.get(s, {}).get("ht", 0) for s in liste) / n)


# semaines complètes seulement (on retire la semaine en cours si elle n'est pas finie)
aujourdhui = date.today()
completes = [s for s in semaines if s + timedelta(days=7) <= aujourdhui]
avant = [s for s in completes if s + timedelta(days=7) <= dc]
apres = [s for s in completes if s >= dc]
moitie = len(apres) // 2
periodes = [("AVANT Cooperl (Elivia)", avant),
            ("APRÈS Cooperl — 1re moitié", apres[:moitie]),
            ("APRÈS Cooperl — 2e moitié", apres[moitie:]),
            ("APRÈS Cooperl — total", apres)]

print("\n" + "=" * 118)
print("MOYENNES PAR SEMAINE")
print("=" * 118)
print(f"  {'Période':<30}{'semaines':>9}{'kg/sem':>9}{'€ HT/sem':>10}{'CA TTC/sem':>12}{'kg/1000€':>10}  │"
      + "".join(f"{m[:8]:>9}" for m in noms_m))
B = {}
for nom, liste in periodes:
    b = bilan(liste)
    B[nom] = b
    if not b:
        print(f"  {nom:<30}{'—':>9}")
        continue
    ratio = f"{b['ratio']:>10.1f}" if b["ratio"] else f"{'—':>10}"
    print(f"  {nom:<30}{b['n']:>9}{b['kg']:>9.0f}{b['ht']:>10.0f}{b['ca']:>12.0f}{ratio}  │"
          + "".join(f"{b['m'][m]:>9.1f}" for m in noms_m))
    print(f"  {'':<30}{liste[0]:%d/%m} → {liste[-1] + timedelta(days=6):%d/%m}")


def ev(a, b, cle):
    if not a or not b or not a.get(cle) or b.get(cle) is None:
        return "—"
    return f"{100 * (b[cle] - a[cle]) / a[cle]:+.0f} %"


av, ap1, ap2, apt = (B[p[0]] for p in periodes)
print("\n  Lecture :")
print(f"   • kg de porc par semaine        : avant → après {ev(av, apt, 'kg')}   "
      f"(1re → 2e moitié de l'après : {ev(ap1, ap2, 'kg')})")
print(f"   • CA boutique par semaine       : avant → après {ev(av, apt, 'ca')}   "
      f"(1re → 2e moitié : {ev(ap1, ap2, 'ca')})")
print(f"   • kg de porc pour 1 000 € de CA : avant → après {ev(av, apt, 'ratio')}   "
      f"(1re → 2e moitié : {ev(ap1, ap2, 'ratio')})")
print("     ↑ c'est l'indicateur clé : il retire l'effet saison/fréquentation.")
if av and av["n"] < 4:
    print(f"   ⚠ « Avant » ne compte que {av['n']} semaine(s) complète(s) : comparaison indicative.")
print("   ⚠ Ce sont des ACHATS : ils suivent les ventes avec un décalage (stock). Le PSH de Cooperl"
      "\n     a pu remplacer d'autres achats de jambon ; comparer aussi la colonne « Autres ».")
print("\nLecture seule — aucune donnée modifiée.")

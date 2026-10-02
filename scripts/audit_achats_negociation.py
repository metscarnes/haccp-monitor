#!/usr/bin/env python3
"""
audit_achats_negociation.py — Où porter l'effort de négociation fournisseur ?

Source : le module Facture (poids/prix réellement facturés), rattaché au catalogue
achats. Les avoirs viennent en déduction. Sections :

  1. Vue d'ensemble (marchandise / prestations / annexes / avoirs, contrôles)
  2. Poids par fournisseur (+ poids des frais annexes)
  3. Poids par famille / sous-famille
  4. Pareto des articles (les quelques articles qui font 80 % de la dépense)
  5. Dérive de prix (début vs fin de période, par article) + volatilité
  6. Facturé vs commandé (surfacturation récupérable)
  7. Même produit chez plusieurs fournisseurs (groupes du comparateur)
  8. Frais annexes et prestations (transport, taxes, désossage…)
  9. PRIORITÉS DE NÉGOCIATION (levier €/an par article et par fournisseur)

Lecture seule (base ouverte en mode=ro), ne modifie rien.

    python3 scripts/audit_achats_negociation.py [chemin/haccp.db]
            [--depuis 2026-06-10] [--jusqu AAAA-MM-JJ] [--cible 3] [--top 25]
            [--csv fichier.csv]

--cible : % de baisse visé en négociation, pour chiffrer le levier (défaut 3 %).
Un CSV des priorités par article est écrit (défaut audit_achats_AAAAMMJJ.csv).
"""

import argparse
import csv
import sqlite3
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ap = argparse.ArgumentParser()
ap.add_argument("db", nargs="?", default=str(Path(__file__).parent.parent / "haccp.db"))
ap.add_argument("--depuis", default="2026-06-10")
ap.add_argument("--jusqu", default=date.today().isoformat())
ap.add_argument("--cible", type=float, default=3.0)
ap.add_argument("--top", type=int, default=25)
ap.add_argument("--csv", default=f"audit_achats_{date.today():%Y%m%d}.csv")
args = ap.parse_args()

conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
cur = conn.cursor()


def tables():
    return {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def colonnes(t):
    return {r[1] for r in cur.execute(f"PRAGMA table_info({t})")}


def col(alias, table, c, defaut="NULL"):
    """Colonne si elle existe dans la base, sinon une valeur par défaut (base plus ancienne)."""
    return f"{alias}.{c}" if c in colonnes(table) else defaut


def eur(x):
    return f"{x:,.0f} €".replace(",", " ")


def eur2(x):
    return f"{x:,.2f}".replace(",", " ")


def pct(x):
    return f"{x:5.1f} %"


def court(s, n):
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def titre(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


TABLES = tables()

# ── Chargement des lignes facture de la période ──────────────────────────────
lignes = cur.execute(
    f"""SELECT fl.id, f.id AS facture_id, f.date_facture AS d,
               {col('f', 'factures', 'type', "'facture'")} AS type_doc,
               f.statut, f.fournisseur_id, fo.nom AS fournisseur, f.reception_id,
               fl.catalogue_fournisseur_id AS cf_id, fl.code_article, fl.designation,
               {col('fl', 'facture_lignes', 'type_ligne', "'marchandise'")} AS type_ligne,
               {col('fl', 'facture_lignes', 'unite_prix', "'kg'")} AS unite_prix,
               {col('fl', 'facture_lignes', 'quantite_facturee')} AS qte_fact,
               fl.poids_facture_kg, fl.prix_facture_ht, fl.montant_facture_ht,
               fl.prix_commande_ht,
               cf.designation AS cf_designation, cf.code_article AS cf_code,
               {col('cf', 'catalogue_fournisseur', 'famille')} AS famille,
               {col('cf', 'catalogue_fournisseur', 'sous_famille')} AS sous_famille,
               cf.prix_achat_ht AS cf_prix,
               {col('cf', 'catalogue_fournisseur', 'format_prix', "'kg'")} AS cf_format
        FROM facture_lignes fl
        JOIN factures f ON f.id = fl.facture_id
        LEFT JOIN fournisseurs fo ON fo.id = f.fournisseur_id
        LEFT JOIN catalogue_fournisseur cf ON cf.id = fl.catalogue_fournisseur_id
        WHERE f.date_facture BETWEEN ? AND ?
        ORDER BY f.date_facture, fl.id""",
    (args.depuis, args.jusqu),
).fetchall()

if not lignes:
    print(f"Aucune ligne facture entre {args.depuis} et {args.jusqu} dans {args.db}")
    sys.exit(0)

dates = sorted(r["d"] for r in lignes)
d_min, d_max = date.fromisoformat(dates[0][:10]), date.fromisoformat(dates[-1][:10])
JOURS = (d_max - d_min).days + 1
ANNU = 365.0 / JOURS  # facteur d'annualisation


def est_prestation(r):
    des = (r["designation"] or "").upper()
    code = (r["code_article"] or r["cf_code"] or "").lstrip("0")
    return "PREST" in des or code.startswith("99864")


def article_cle(r):
    if r["cf_id"]:
        return ("cf", r["cf_id"])
    return ("libre", r["fournisseur_id"], (r["designation"] or "").strip().upper())


L = []  # lignes enrichies
for r in lignes:
    signe = -1 if (r["type_doc"] or "facture") == "avoir" else 1
    m = signe * (r["montant_facture_ht"] or 0.0)
    tl = r["type_ligne"] or "marchandise"
    if tl == "marchandise" and est_prestation(r):
        cat = "prestation"
    elif tl == "marchandise":
        cat = "marchandise"
    else:
        cat = tl
    kg = r["poids_facture_kg"] if (r["poids_facture_kg"] or 0) > 0 else None
    # Observation de prix (hors avoirs) : €/kg si poids, sinon €/unité facturée
    obs = None
    if signe == 1 and cat == "marchandise" and (r["montant_facture_ht"] or 0) > 0:
        if kg:
            obs = ("kg", r["montant_facture_ht"] / kg, kg)
        elif (r["qte_fact"] or 0) > 0:
            obs = (r["unite_prix"] or "u", r["montant_facture_ht"] / r["qte_fact"], r["qte_fact"])
    L.append(dict(
        r=r, d=r["d"][:10], signe=signe, m=m, cat=cat, kg=kg, obs=obs,
        cle=article_cle(r),
        nom=r["cf_designation"] or r["designation"],
        fournisseur=r["fournisseur"] or f"#{r['fournisseur_id']}",
        famille=r["famille"] or "(sans famille)",
        sous_famille=r["sous_famille"] or "(sans sous-famille)",
    ))

MARCH = [x for x in L if x["cat"] == "marchandise"]
TOTAL_MARCH = sum(x["m"] for x in MARCH)

# ════════════════════════════════════════════════════════════════════════════
titre(f"1. VUE D'ENSEMBLE — factures du {d_min:%d/%m/%Y} au {d_max:%d/%m/%Y} "
      f"({JOURS} j, annualisation ×{ANNU:.2f})")
print(f"Base : {args.db}\n")
par_cat = defaultdict(float)
for x in L:
    par_cat[x["cat"]] += x["m"]
total = sum(par_cat.values())
for c, v in sorted(par_cat.items(), key=lambda kv: -abs(kv[1])):
    print(f"  {c:<14} {eur(v):>14}   {pct(100 * v / total if total else 0)}")
print(f"  {'TOTAL HT':<14} {eur(total):>14}")
avoirs = sum(x["m"] for x in L if x["signe"] == -1)
nb_fact = len({x["r"]["facture_id"] for x in L})
print(f"\n  Factures/avoirs : {nb_fact}   dont avoirs : {eur(avoirs)}")
print(f"  Marchandise annualisée : {eur(TOTAL_MARCH * ANNU)} / an")

statuts = defaultdict(lambda: [0, 0.0])
for x in L:
    s = statuts[x["r"]["statut"]]
    s[1] += x["m"]
statuts_fact = defaultdict(set)
for x in L:
    statuts_fact[x["r"]["statut"]].add(x["r"]["facture_id"])
print("\n  Par statut de facture :")
for s, (_, v) in statuts.items():
    print(f"    {s or '?':<12} {len(statuts_fact[s]):>4} factures  {eur(v):>12}")
if statuts.get("brouillon"):
    print("    ⚠ Les brouillons = souvent la facture auto de réception, pas encore confrontée au papier.")

orph = [x for x in MARCH if not x["r"]["cf_id"]]
if orph:
    print(f"\n  ⚠ Lignes marchandise non rattachées au catalogue : {len(orph)} "
          f"({eur(sum(x['m'] for x in orph))}) — comptées sous leur libellé brut.")

# Doublons possibles : une réception portée par 2 factures (hors avoirs)
rec = defaultdict(set)
for x in L:
    if x["r"]["reception_id"] and x["signe"] == 1:
        rec[x["r"]["reception_id"]].add(x["r"]["facture_id"])
doubles = {k: v for k, v in rec.items() if len(v) > 1}
if doubles:
    print(f"\n  ⚠ {len(doubles)} réception(s) rattachée(s) à plusieurs factures (double comptage possible) :")
    for k, v in list(doubles.items())[:10]:
        print(f"    réception {k} → factures {sorted(v)}")

# ════════════════════════════════════════════════════════════════════════════
titre("2. POIDS PAR FOURNISSEUR (marchandise) — qui pèse dans la négociation")
pf = defaultdict(lambda: dict(m=0.0, annexes=0.0, presta=0.0, fact=set(), art=set()))
for x in L:
    p = pf[x["fournisseur"]]
    if x["cat"] == "marchandise":
        p["m"] += x["m"]
        p["art"].add(x["cle"])
    elif x["cat"] == "prestation":
        p["presta"] += x["m"]
    else:
        p["annexes"] += x["m"]
    p["fact"].add(x["r"]["facture_id"])
print(f"  {'Fournisseur':<28}{'Marchandise':>13}{'part':>9}{'€/an':>12}{'annexes':>10}{'% march':>9}"
      f"{'presta':>9}{'fact.':>6}{'panier':>9}{'art.':>6}")
for n, p in sorted(pf.items(), key=lambda kv: -kv[1]["m"]):
    nf = len(p["fact"])
    print(f"  {court(n, 27):<28}{eur(p['m']):>13}{pct(100 * p['m'] / TOTAL_MARCH):>9}"
          f"{eur(p['m'] * ANNU):>12}{eur(p['annexes']):>10}"
          f"{pct(100 * p['annexes'] / p['m'] if p['m'] else 0):>9}{eur(p['presta']):>9}"
          f"{nf:>6}{eur((p['m'] + p['annexes']) / nf if nf else 0):>9}{len(p['art']):>6}")

# ════════════════════════════════════════════════════════════════════════════
titre("3. POIDS PAR FAMILLE / SOUS-FAMILLE (marchandise)")
fam = defaultdict(lambda: dict(m=0.0, kg=0.0, mkg=0.0))
for x in MARCH:
    for k in ((x["famille"], ""), (x["famille"], x["sous_famille"])):
        f_ = fam[k]
        f_["m"] += x["m"]
        if x["kg"] and x["signe"] == 1:
            f_["kg"] += x["kg"]
            f_["mkg"] += x["m"]
familles = sorted({k[0] for k in fam}, key=lambda f_: -fam[(f_, "")]["m"])
print(f"  {'Famille / sous-famille':<40}{'HT':>13}{'part':>9}{'kg':>10}{'€/kg moy':>10}")
for f_ in familles:
    v = fam[(f_, "")]
    print(f"  {court(f_, 39):<40}{eur(v['m']):>13}{pct(100 * v['m'] / TOTAL_MARCH):>9}"
          f"{v['kg']:>10.0f}{(v['mkg'] / v['kg'] if v['kg'] else 0):>10.2f}")
    subs = sorted([k for k in fam if k[0] == f_ and k[1]], key=lambda k: -fam[k]["m"])
    for k in subs:
        v = fam[k]
        print(f"     └ {court(k[1], 34):<35}{eur(v['m']):>13}{pct(100 * v['m'] / TOTAL_MARCH):>9}"
              f"{v['kg']:>10.0f}{(v['mkg'] / v['kg'] if v['kg'] else 0):>10.2f}")

# ════════════════════════════════════════════════════════════════════════════
# Agrégat par article
art = {}
for x in MARCH:
    a = art.setdefault(x["cle"], dict(
        nom=x["nom"], fournisseur=x["fournisseur"], famille=x["famille"],
        sous_famille=x["sous_famille"], cf_id=x["r"]["cf_id"], m=0.0, kg=0.0, n=0, obs=[],
        surfact=0.0, cf_prix=x["r"]["cf_prix"], cf_format=x["r"]["cf_format"]))
    a["m"] += x["m"]
    if x["signe"] == 1:
        a["n"] += 1
        if x["kg"]:
            a["kg"] += x["kg"]
    if x["obs"]:
        a["obs"].append((x["d"],) + x["obs"])

for a in art.values():
    # unité de prix dominante de l'article
    unites = defaultdict(float)
    for o in a["obs"]:
        unites[o[1]] += o[3]
    a["unite"] = max(unites, key=unites.get) if unites else None
    obs = [o for o in a["obs"] if o[1] == a["unite"]]
    a["obs_u"] = obs
    q = sum(o[3] for o in obs)
    a["q"] = q
    a["pmoy"] = sum(o[2] * o[3] for o in obs) / q if q else None
    a["pmin"] = min((o[2] for o in obs), default=None)
    a["pmax"] = max((o[2] for o in obs), default=None)

titre(f"4. PARETO DES ARTICLES — ce qui fait 80 % de la dépense marchandise "
      f"({len(art)} articles achetés)")
print(f"  {'#':>3} {'Article':<34}{'Fournisseur':<18}{'HT':>11}{'cumul':>8}{'qté':>9}"
      f"{'prix moy':>10}{'min':>9}{'max':>9}{'nb':>4}")
cumul, rang80 = 0.0, None
tri = sorted(art.values(), key=lambda a: -a["m"])
for i, a in enumerate(tri, 1):
    cumul += a["m"]
    c = 100 * cumul / TOTAL_MARCH
    if i <= max(args.top, 0) or rang80 is None:
        u = a["unite"] or ""
        print(f"  {i:>3} {court(a['nom'], 33):<34}{court(a['fournisseur'], 17):<18}{eur(a['m']):>11}"
              f"{c:>7.1f}%{a['q']:>7.0f}{u[:2]:>2}"
              f"{(a['pmoy'] or 0):>10.2f}{(a['pmin'] or 0):>9.2f}{(a['pmax'] or 0):>9.2f}{a['n']:>4}")
    if rang80 is None and c >= 80:
        rang80 = i
        print(f"  {'':>3} ─── 80 % atteint avec {i} articles sur {len(art)} "
              f"({100 * i / len(art):.0f} % des références) ───")
    if i >= args.top and rang80 is not None:
        break

# ════════════════════════════════════════════════════════════════════════════
titre("5. DÉRIVE DE PRIX — prix moyen du 1er tiers des achats vs dernier tiers (≥ 4 achats)")
derives = []
for cle, a in art.items():
    obs = sorted(a["obs_u"])
    if len(obs) < 4:
        continue
    n3 = max(1, len(obs) // 3)

    def pm(o):
        q = sum(x[3] for x in o)
        return sum(x[2] * x[3] for x in o) / q if q else 0

    p_old, p_new = pm(obs[:n3]), pm(obs[-n3:])
    if not p_old:
        continue
    var = 100 * (p_new - p_old) / p_old
    impact_an = (p_new - p_old) * a["q"] * ANNU
    vol = 100 * (a["pmax"] - a["pmin"]) / a["pmoy"] if a["pmoy"] else 0
    a["derive_an"] = impact_an
    a["var"] = var
    a["vol"] = vol
    derives.append((cle, a, p_old, p_new, var, impact_an, vol, obs[0][0], obs[-1][0]))

print("  ▲ Hausses — classées par impact annuel (à contester / renégocier en premier) :")
print(f"  {'Article':<34}{'Fournisseur':<18}{'avant':>9}{'après':>9}{'var':>9}{'impact/an':>12}{'période':>24}")
for cle, a, po, pn, v, imp, vol, d1, d2 in sorted(derives, key=lambda t: -t[5])[: args.top]:
    if imp <= 0:
        break
    print(f"  {court(a['nom'], 33):<34}{court(a['fournisseur'], 17):<18}{po:>9.2f}{pn:>9.2f}"
          f"{v:>+8.1f}%{eur(imp):>12}   {d1} → {d2}")
print("\n  ▼ Baisses obtenues (pour mémoire) :")
for cle, a, po, pn, v, imp, vol, d1, d2 in sorted(derives, key=lambda t: t[5])[:10]:
    if imp >= 0:
        break
    print(f"  {court(a['nom'], 33):<34}{court(a['fournisseur'], 17):<18}{po:>9.2f}{pn:>9.2f}"
          f"{v:>+8.1f}%{eur(imp):>12}")
print("\n  ≈ Prix instables (écart max-min > 15 % du prix moyen) — exiger un prix ferme / contrat :")
inst = [t for t in derives if t[6] > 15]
for cle, a, po, pn, v, imp, vol, d1, d2 in sorted(inst, key=lambda t: -t[1]["m"])[:15]:
    print(f"  {court(a['nom'], 33):<34}{court(a['fournisseur'], 17):<18}"
          f"min {a['pmin']:>7.2f}  max {a['pmax']:>7.2f}  écart {vol:>5.0f} %   HT {eur(a['m'])}")

# ════════════════════════════════════════════════════════════════════════════
titre("6. FACTURÉ vs COMMANDÉ — prix facturé au-dessus du prix de commande (au kg)")
sf = defaultdict(lambda: [0.0, 0.0, 0])  # fournisseur -> [surfacturé, sous-facturé, nb lignes]
sf_art = defaultdict(float)
nb_comp = 0
for x in MARCH:
    r = x["r"]
    if x["signe"] != 1 or not x["kg"] or (r["unite_prix"] or "kg") != "kg":
        continue
    pc, pfh = r["prix_commande_ht"] or 0, r["prix_facture_ht"] or 0
    if pc <= 0 or pfh <= 0:
        continue
    nb_comp += 1
    e = (pfh - pc) * x["kg"]
    s = sf[x["fournisseur"]]
    if e > 0.005:
        s[0] += e
        s[2] += 1
        sf_art[x["cle"]] += e
    elif e < -0.005:
        s[1] += e
for cle, v in sf_art.items():
    art[cle]["surfact"] = v
print(f"  {nb_comp} lignes comparables (prix de commande connu, facturées au kg).")
print(f"  {'Fournisseur':<30}{'surfacturé':>12}{'lignes':>8}{'sous-facturé':>14}{'net':>10}{'net/an':>10}")
for n, (p, m_, k) in sorted(sf.items(), key=lambda kv: -kv[1][0]):
    print(f"  {court(n, 29):<30}{eur(p):>12}{k:>8}{eur(m_):>14}{eur(p + m_):>10}{eur((p + m_) * ANNU):>10}")
print("\n  Articles les plus surfacturés vs commande :")
for cle, v in sorted(sf_art.items(), key=lambda kv: -kv[1])[:15]:
    a = art[cle]
    print(f"  {court(a['nom'], 40):<41}{court(a['fournisseur'], 20):<21}{eur(v):>10}")

# ════════════════════════════════════════════════════════════════════════════
titre("7. MÊME PRODUIT CHEZ PLUSIEURS FOURNISSEURS (groupes du comparateur)")
gain_art = defaultdict(float)
if {"comparatif_groupe", "comparatif_groupe_ligne"} <= TABLES:
    grp = cur.execute(
        """SELECT g.id, g.nom, gl.catalogue_fournisseur_id AS cf_id, cf.fournisseur_id,
                  fo.nom AS fournisseur, cf.designation, cf.prix_achat_ht,
                  COALESCE(cf.format_prix,'kg') AS format_prix, cf.actif
           FROM comparatif_groupe g
           JOIN comparatif_groupe_ligne gl ON gl.groupe_id = g.id
           JOIN catalogue_fournisseur cf ON cf.id = gl.catalogue_fournisseur_id
           LEFT JOIN fournisseurs fo ON fo.id = cf.fournisseur_id"""
        if "format_prix" in colonnes("catalogue_fournisseur") else
        """SELECT g.id, g.nom, gl.catalogue_fournisseur_id AS cf_id, cf.fournisseur_id,
                  fo.nom AS fournisseur, cf.designation, cf.prix_achat_ht,
                  'kg' AS format_prix, cf.actif
           FROM comparatif_groupe g
           JOIN comparatif_groupe_ligne gl ON gl.groupe_id = g.id
           JOIN catalogue_fournisseur cf ON cf.id = gl.catalogue_fournisseur_id
           LEFT JOIN fournisseurs fo ON fo.id = cf.fournisseur_id""").fetchall()
    groupes = defaultdict(list)
    for g in grp:
        groupes[(g["id"], g["nom"])].append(g)
    res = []
    for (gid, gnom), membres in groupes.items():
        cand = []  # (fournisseur_id, fournisseur, cf_id, designation, prix €/kg, source, kg achetés)
        for mb in membres:
            a = art.get(("cf", mb["cf_id"]))
            if a and a["unite"] == "kg" and a["pmoy"]:
                cand.append((mb["fournisseur_id"], mb["fournisseur"], mb["cf_id"], mb["designation"],
                             a["pmoy"], "payé", a["q"]))
            elif mb["actif"] and mb["format_prix"] == "kg" and (mb["prix_achat_ht"] or 0) > 0:
                cand.append((mb["fournisseur_id"], mb["fournisseur"], mb["cf_id"], mb["designation"],
                             mb["prix_achat_ht"], "catalogue", 0.0))
        if len({c[0] for c in cand}) < 2 or not any(c[6] for c in cand):
            continue
        gain, detail = 0.0, []
        for c in cand:
            if not c[6]:
                continue
            autres = [o for o in cand if o[0] != c[0]]
            meilleur = min(autres, key=lambda o: o[4])
            if meilleur[4] < c[4]:
                g_ = (c[4] - meilleur[4]) * c[6]
                gain += g_
                gain_art[("cf", c[2])] += g_ * ANNU
                detail.append((c, meilleur, g_))
        res.append((gain, gnom, cand, detail))
    print("  Gain = kg achetés × (prix payé − meilleur prix d'un AUTRE fournisseur du groupe).")
    print("  ⚠ Vérifier l'équivalence qualité (label, race, calibre) avant de basculer.\n")
    for gain, gnom, cand, detail in sorted(res, key=lambda t: -t[0])[: args.top]:
        if gain <= 0:
            continue
        print(f"  ■ {gnom} — gain potentiel {eur(gain)} sur la période ({eur(gain * ANNU)}/an)")
        for c in sorted(cand, key=lambda c: c[4]):
            print(f"      {court(c[1], 20):<21}{court(c[3], 36):<37}{c[4]:>7.2f} €/kg ({c[5]:<9})"
                  f"{('  ' + format(c[6], '.0f') + ' kg achetés') if c[6] else ''}")
    if not any(t[0] > 0 for t in res):
        print("  Aucun groupe où un autre fournisseur est moins cher sur un article acheté.")
else:
    print("  Tables du comparateur absentes.")

# ════════════════════════════════════════════════════════════════════════════
titre("8. FRAIS ANNEXES ET PRESTATIONS (hors marchandise)")
ann = defaultdict(lambda: [0.0, 0])
for x in L:
    if x["cat"] == "marchandise":
        continue
    k = (x["fournisseur"], x["cat"], (x["r"]["designation"] or "").strip().upper())
    ann[k][0] += x["m"]
    ann[k][1] += 1
print(f"  {'Fournisseur':<24}{'type':<12}{'libellé':<40}{'HT':>10}{'nb':>5}{'€/an':>10}")
for (f_, c, d_), (v, n) in sorted(ann.items(), key=lambda kv: -kv[1][0])[:30]:
    print(f"  {court(f_, 23):<24}{c:<12}{court(d_, 39):<40}{eur(v):>10}{n:>5}{eur(v * ANNU):>10}")
tot_ann = sum(v for (f_, c, d_), (v, n) in ann.items())
print(f"\n  Total annexes + prestations : {eur(tot_ann)} ({eur(tot_ann * ANNU)}/an) "
      f"= {pct(100 * tot_ann / TOTAL_MARCH)} de la marchandise")
print("  Leviers : franco de port, regroupement des livraisons, désossage intégré au prix.")

# ════════════════════════════════════════════════════════════════════════════
titre(f"9. PRIORITÉS DE NÉGOCIATION — levier annuel par article (cible {args.cible:g} %)")
print("  levier = cible % × dépense/an  +  max(dérive de prix/an, surfacturation/an)"
      "  +  écart vs autre fournisseur/an\n")
prio = []
for cle, a in art.items():
    dep_an = a["m"] * ANNU
    l_cible = dep_an * args.cible / 100
    l_derive = max(0.0, a.get("derive_an", 0.0))
    l_surf = a["surfact"] * ANNU
    l_four = gain_art.get(cle, 0.0)
    # dérive et surfacturation mesurent souvent la même hausse : on ne garde que la plus forte
    tot = l_cible + max(l_derive, l_surf) + l_four
    prio.append((tot, cle, a, dep_an, l_cible, l_derive, l_surf, l_four))
prio.sort(key=lambda t: -t[0])
print(f"  {'#':>3} {'Article':<34}{'Fournisseur':<18}{'dépense/an':>11}{'cible':>8}{'dérive':>8}"
      f"{'surfact':>8}{'autre f.':>9}{'LEVIER/an':>11}")
for i, (tot, cle, a, dep, lc, ld, ls, lf) in enumerate(prio[: args.top], 1):
    print(f"  {i:>3} {court(a['nom'], 33):<34}{court(a['fournisseur'], 17):<18}{eur(dep):>11}"
          f"{eur(lc):>8}{eur(ld):>8}{eur(ls):>8}{eur(lf):>9}{eur(tot):>11}")

print("\n  Par fournisseur (somme des leviers articles + annexes à négocier) :")
pf2 = defaultdict(lambda: [0.0, 0.0, 0.0])
for tot, cle, a, dep, lc, ld, ls, lf in prio:
    pf2[a["fournisseur"]][0] += dep
    pf2[a["fournisseur"]][1] += tot
for (f_, c, d_), (v, n) in ann.items():
    pf2[f_][2] += v * ANNU
print(f"  {'Fournisseur':<30}{'dépense/an':>12}{'levier art./an':>16}{'annexes/an':>12}")
for f_, (dep, lev, an_) in sorted(pf2.items(), key=lambda kv: -kv[1][1]):
    print(f"  {court(f_, 29):<30}{eur(dep):>12}{eur(lev):>16}{eur(an_):>12}")

# ── CSV ──────────────────────────────────────────────────────────────────────
try:
    with open(args.csv, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["rang", "article", "fournisseur", "famille", "sous_famille", "catalogue_id",
                    "depense_periode_ht", "depense_an_ht", "quantite", "unite", "prix_moyen",
                    "prix_min", "prix_max", "nb_achats", "variation_prix_pct",
                    "levier_cible_an", "levier_derive_an", "levier_surfacturation_an",
                    "levier_autre_fournisseur_an", "levier_total_an"])
        for i, (tot, cle, a, dep, lc, ld, ls, lf) in enumerate(prio, 1):
            w.writerow([i, a["nom"], a["fournisseur"], a["famille"], a["sous_famille"], a["cf_id"] or "",
                        eur2(a["m"]), eur2(dep), f"{a['q']:.2f}", a["unite"] or "",
                        eur2(a["pmoy"] or 0), eur2(a["pmin"] or 0), eur2(a["pmax"] or 0), a["n"],
                        f"{a['var']:.1f}" if "var" in a else "",
                        eur2(lc), eur2(ld), eur2(ls), eur2(lf), eur2(tot)])
    print(f"\n  CSV des priorités : {Path(args.csv).resolve()}")
except OSError as e:
    print(f"\n  (CSV non écrit : {e})")

print("\nLecture seule — aucune donnée modifiée.")

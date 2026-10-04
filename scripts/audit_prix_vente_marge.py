#!/usr/bin/env python3
"""
audit_prix_vente_marge.py — État des lieux AVANT le moteur « prix de vente à marge maintenue »
(popup réception → nouveau prix de vente arrondi à ,90 → étiquette à réimprimer).

Répond à 5 questions, sur la vraie base :
  1. Les prix de vente actuels finissent-ils déjà par ,90 ?
  2. Combien de produits de vente ont une marge calculable ? (les autres ne recevront
     jamais de proposition de prix : pas d'achat de référence, référence inactive…)
  3. Quel taux de marque actuel par famille / sous-famille ?
  4. Quels articles d'achat servent de référence à plusieurs produits de vente ?
     (une hausse sur eux touche N prix de vente d'un coup)
  5. Combien de hausses/baisses d'achat sur 90 jours, et combien de prix de vente
     auraient changé avec la règle retenue (taux maintenu, ,90 le plus proche) ?

Lecture seule, ne modifie rien.

    python3 scripts/audit_prix_vente_marge.py [chemin/vers/haccp.db] [--jours 90]
"""

import argparse
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

ap = argparse.ArgumentParser()
ap.add_argument("db", nargs="?", default=str(RACINE / "haccp.db"))
ap.add_argument("--jours", type=int, default=90, help="fenêtre d'analyse des prix d'achat")
args = ap.parse_args()

# Mêmes règles de calcul que l'application (aucune copie à faire diverger).
try:
    from src.api.routes_achats import _calc_marge, _prix_kg_article, _prix_piece_article
except Exception as e:  # pragma: no cover - dépend de l'environnement
    sys.exit(f"Import des règles de marge impossible ({e}). Lancer depuis ~/haccp-monitor.")

conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row

SEUIL_PCT = 2.0     # écart relatif jugé significatif (même seuil que le bandeau réception)
SEUIL_ABS = 0.01    # ou 1 ct/kg (SEUIL_ECART_ABS_KG)


def titre(t):
    print("\n" + "=" * 96)
    print(t)
    print("=" * 96)


def arrondi_90_proche(prix):
    """X,90 le plus proche (égalité → supérieur) — règle retenue le 04/10/2026."""
    d = Decimal(str(prix)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    t = Decimal("0.90")
    inf = (d - t).to_integral_value(rounding=ROUND_FLOOR) + t
    sup = (d - t).to_integral_value(rounding=ROUND_CEILING) + t
    if inf < t:
        return float(sup)
    return float(inf) if (d - inf) < (sup - d) else float(sup)


def pct(n, total):
    return f"{100 * n / total:5.1f} %" if total else "   — "


print(f"Base : {args.db}   (lecture seule)   —   {date.today():%d/%m/%Y}")

# ── Produits de vente actifs + liaison achat de référence ──────────────────────
produits = [dict(r) for r in conn.execute(
    """SELECT v.id, v.nom, v.prix_vente_ttc, v.tva_percent, v.unite_vente, v.poids_piece_kg,
              v.famille AS v_famille, v.sous_famille AS v_sous_famille,
              gv.groupe_id, gv.ligne_choisie_id,
              cf.id AS cf_id, cf.actif AS cf_actif, cf.designation AS cf_designation,
              cf.format_prix, cf.prix_achat_ht, cf.poids_colis_kg, cf.famille,
              cf.poids_unitaire_kg, cf.qte_par_colis
       FROM catalogue_vente v
       LEFT JOIN comparatif_groupe_vente gv ON gv.catalogue_vente_id = v.id
       LEFT JOIN catalogue_fournisseur cf ON cf.id = gv.ligne_choisie_id
       WHERE v.boutique_id = 1 AND v.actif = 1
       ORDER BY v.famille, v.sous_famille, v.nom""")]

for p in produits:
    p["marge"] = None
    if p["cf_id"] is not None and p["cf_actif"]:
        p["marge"] = _calc_marge(
            p["prix_vente_ttc"], p["tva_percent"], _prix_kg_article(p),
            unite_vente=p["unite_vente"] or "kg", poids_piece_kg=p["poids_piece_kg"],
            achat_ref_piece=_prix_piece_article(p),
        )

# ── 1. Terminaisons ───────────────────────────────────────────────────────────
titre("1. TERMINAISON DES PRIX DE VENTE ACTUELS (centimes)")
avec_prix = [p for p in produits if p["prix_vente_ttc"] and p["prix_vente_ttc"] > 0]
fins = Counter(round(p["prix_vente_ttc"] * 100) % 100 for p in avec_prix)
print(f"  Produits actifs : {len(produits)}   dont avec un prix de vente : {len(avec_prix)}")
for cents, n in fins.most_common(12):
    print(f"    ,{cents:02d}  {n:>4}  {pct(n, len(avec_prix))}")
for unite, libelle in (("kg", "au kg"), ("piece", "à la pièce")):
    sous = [p for p in avec_prix if (p["unite_vente"] or "kg") == unite]
    n90 = sum(1 for p in sous if round(p["prix_vente_ttc"] * 100) % 100 == 90)
    print(f"  Vendus {libelle:<10}: {len(sous):>4} produits, {n90} finissent par ,90 ({pct(n90, len(sous)).strip()})")
autres = [p for p in avec_prix if round(p["prix_vente_ttc"] * 100) % 100 != 90]
if autres:
    print("  Exemples hors ,90 :")
    for p in autres[:15]:
        print(f"    {p['prix_vente_ttc']:>8.2f} €  {p['nom']}")

# ── 2. Couverture marge ───────────────────────────────────────────────────────
titre("2. COUVERTURE : QUI POURRA RECEVOIR UNE PROPOSITION DE PRIX ?")


def motif_couverture(p):
    """Première raison qui bloque la marge (catégories exclusives)."""
    if p["marge"] is not None:
        return "calculable"
    if p["groupe_id"] is None:
        return "non_relie"
    if p["ligne_choisie_id"] is None:
        return "sans_ref"
    if p["cf_id"] is None or not p["cf_actif"]:
        return "ref_inactive"
    if not p["prix_vente_ttc"] or p["prix_vente_ttc"] <= 0:
        return "sans_prix"
    return "autre"


LIBELLES_COUVERTURE = [
    ("calculable", "Marge calculable (proposition possible)"),
    ("non_relie", "Non reliés à un achat (comparateur)"),
    ("sans_ref", "Reliés mais sans achat de référence"),
    ("ref_inactive", "Achat de référence désactivé / supprimé"),
    ("sans_prix", "Reliés mais sans prix de vente"),
    ("autre", "Prix d'achat ou poids de pièce manquant"),
]
for p in produits:
    p["couverture"] = motif_couverture(p)
calculables = [p for p in produits if p["couverture"] == "calculable"]
compte = Counter(p["couverture"] for p in produits)
total = len(produits)
for cle, libelle in LIBELLES_COUVERTURE:
    print(f"  {libelle:<42}: {compte[cle]:>4}  {pct(compte[cle], total)}")
par_famille = Counter((p["v_famille"] or "non classé") for p in produits
                      if p["couverture"] in ("non_relie", "sans_ref"))
if par_famille:
    print("  Produits non reliés / sans référence, par famille :")
    for fam, n in par_famille.most_common():
        print(f"    {fam:<28} {n:>4}")

# ── 3. Taux de marque par famille / sous-famille ──────────────────────────────
titre("3. TAUX DE MARQUE ACTUEL (marge ÷ prix de vente HT) PAR FAMILLE / SOUS-FAMILLE")
groupes = defaultdict(list)
for p in calculables:
    if p["marge"]["taux_marge"] is not None:
        groupes[(p["v_famille"] or "non classé", p["v_sous_famille"] or "—")].append(
            p["marge"]["taux_marge"] * 100)
print(f"  {'Famille':<22} {'Sous-famille':<34} {'n':>4} {'min':>7} {'médiane':>8} {'max':>7}")
for (fam, sf), taux in sorted(groupes.items()):
    print(f"  {fam[:22]:<22} {sf[:34]:<34} {len(taux):>4} {min(taux):>6.1f}% "
          f"{statistics.median(taux):>7.1f}% {max(taux):>6.1f}%")
faibles = sorted(calculables, key=lambda p: p["marge"]["taux_marge"] if p["marge"]["taux_marge"] is not None else 9)[:10]
print("  10 marges les plus faibles :")
for p in faibles:
    m = p["marge"]
    if m["taux_marge"] is None:
        continue
    print(f"    {m['taux_marge'] * 100:>6.1f} %  {p['prix_vente_ttc']:>7.2f} € / {m['unite']:<5} "
          f"coût {m['cout_matiere']:>6.2f}  {p['nom']}  ← {p['cf_designation']}")

# ── 4. Effet multiplicateur ───────────────────────────────────────────────────
titre("4. ARTICLES D'ACHAT RÉFÉRENCE DE PLUSIEURS PRODUITS DE VENTE")
par_ref = defaultdict(list)
for p in calculables:
    par_ref[(p["cf_id"], p["cf_designation"])].append(p["nom"])
multi = sorted(((k, v) for k, v in par_ref.items() if len(v) >= 2), key=lambda kv: -len(kv[1]))
print(f"  {len(multi)} article(s) servent de référence à 2 produits ou plus.")
for (cf_id, desig), noms in multi[:12]:
    print(f"    {len(noms):>2} produits ← {desig} (#{cf_id}) : {', '.join(noms[:6])}{' …' if len(noms) > 6 else ''}")

# ── 5. Variations d'achat sur la fenêtre + simulation de la règle ─────────────
titre(f"5. VARIATIONS DE PRIX D'ACHAT SUR {args.jours} JOURS ET SIMULATION DE LA RÈGLE")
borne = (date.today() - timedelta(days=args.jours)).isoformat()
try:
    obs = [dict(r) for r in conn.execute(
        """SELECT catalogue_fournisseur_id AS cf_id, date_constat, prix_kg, prix_kg_precedent,
                  applique_au_catalogue
           FROM historique_prix_achat
           WHERE date_constat >= ? AND prix_kg IS NOT NULL
           ORDER BY catalogue_fournisseur_id, date_constat, id""", (borne,))]
except sqlite3.OperationalError as e:
    obs = []
    print(f"  historique_prix_achat illisible : {e}")

signif = []
for o in obs:
    ref = o["prix_kg_precedent"]
    if ref is None or ref <= 0:
        continue
    ecart = o["prix_kg"] - ref
    if abs(ecart) >= SEUIL_ABS or abs(ecart / ref * 100) > SEUIL_PCT:
        signif.append(o)
appliques = [o for o in signif if o["applique_au_catalogue"]]
hausses = [o for o in signif if o["prix_kg"] > o["prix_kg_precedent"]]
semaines = max(1, args.jours / 7)
print(f"  Prix constatés en réception          : {len(obs)}")
print(f"  Écarts significatifs vs catalogue    : {len(signif)}  (≈ {len(signif) / semaines:.1f} / semaine)"
      f" — {len(hausses)} hausses, {len(signif) - len(hausses)} baisses")
print(f"  Écarts appliqués au catalogue (clic) : {len(appliques)}  {pct(len(appliques), len(signif)).strip()}")

# Simulation : pour chaque article de référence dont le prix a été APPLIQUÉ sur la période,
# rapport cumulé premier prix de référence → dernier prix appliqué. Le coût matière d'un
# produit de vente est proportionnel au €/kg d'achat, donc garder le coef revient à
# multiplier le prix de vente par ce rapport, puis arrondir au ,90 le plus proche.
par_article = defaultdict(list)
for o in appliques:
    par_article[o["cf_id"]].append(o)
change, absorbe, details = 0, 0, []
produits_par_ref = defaultdict(list)
for p in calculables:
    produits_par_ref[p["cf_id"]].append(p)
for cf_id, pts in par_article.items():
    rapport = pts[-1]["prix_kg"] / pts[0]["prix_kg_precedent"]
    for p in produits_par_ref.get(cf_id, []):
        cible = p["prix_vente_ttc"] * rapport
        propose = arrondi_90_proche(cible)
        if round(propose, 2) != round(p["prix_vente_ttc"], 2):
            change += 1
            details.append((rapport, p, propose))
        else:
            absorbe += 1
print(f"  Articles de référence touchés        : {len(par_article)}")
print(f"  Prix de vente qui auraient changé    : {change}   (absorbés par l'arrondi : {absorbe})")
print(f"  → environ {change / semaines:.1f} étiquette(s) à réimprimer par semaine")
for rapport, p, propose in sorted(details, key=lambda d: -abs(d[0] - 1))[:15]:
    print(f"    {(rapport - 1) * 100:+6.1f} % achat → {p['prix_vente_ttc']:>7.2f} → {propose:>7.2f} €  {p['nom']}")

print("\nLecture seule — aucune donnée modifiée.")

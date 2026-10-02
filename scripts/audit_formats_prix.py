#!/usr/bin/env python3
"""
audit_formats_prix.py — Contrôle la cohérence du format de prix (kg / colis / pièce)
des articles du catalogue achats, et liste les produits de vente dont la marge
repose sur un article suspect.

Cause visée : un prix de PIÈCE enregistré en format « colis » (ex. Saucisson monts
lyonnais 4,10 € en colis de 12 × 0,28 kg → 1,22 €/kg au lieu de 14,64 €/kg). Le
formulaire d'édition convertissait 'piece' → 'colis' à l'ouverture, donc tout
Enregistrer écrasait le format (corrigé le 02/10/2026).

Lecture seule, ne modifie rien.

    python3 scripts/audit_formats_prix.py [chemin/vers/haccp.db]
"""

import sqlite3
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DB_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "haccp.db"

# Plage de €/kg plausible pour de l'alimentaire en boucherie-traiteur.
KG_MIN, KG_MAX = 2.0, 120.0

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cur = conn.cursor()


def prix_kg(a):
    """Miroir de _calc_prix_kg (routes_achats.py)."""
    p, f = a["prix_achat_ht"], a["format_prix"]
    if p is None:
        return None
    if f == "kg":
        return p
    if f == "piece":
        return p / a["poids_unitaire_kg"] if a["poids_unitaire_kg"] else None
    if f == "colis":
        return p / a["poids_colis_kg"] if a["poids_colis_kg"] else None
    if (a["famille"] or "").strip().lower() == "viande":
        return p
    return None


def fmt(v, suffixe=""):
    return "—" if v is None else f"{v:.2f}{suffixe}"


print(f"=== Base : {DB_PATH} ===\n")

articles = [dict(r) for r in cur.execute(
    """SELECT cf.*, f.nom AS fournisseur
       FROM catalogue_fournisseur cf
       LEFT JOIN fournisseurs f ON f.id = cf.fournisseur_id
       WHERE cf.actif = 1
       ORDER BY f.nom, cf.designation""")]

print("--- 1. Répartition des formats (articles actifs) ---")
repart = {}
for a in articles:
    repart[a["format_prix"]] = repart.get(a["format_prix"], 0) + 1
for k, n in sorted(repart.items(), key=lambda x: -x[1]):
    print(f"  {k!r:10} {n}")
print()

anomalies = {}   # id article → liste de motifs


def signaler(a, motif):
    anomalies.setdefault(a["id"], []).append(motif)


for a in articles:
    f, p = a["format_prix"], a["prix_achat_ht"]
    pu, qte, pc = a["poids_unitaire_kg"], a["qte_par_colis"], a["poids_colis_kg"]
    kg = prix_kg(a)
    if f not in ("kg", "colis", "piece"):
        signaler(a, f"format inconnu {f!r}")
    if f == "colis" and not pc:
        signaler(a, "colis sans poids colis → €/kg incalculable")
    if f == "colis" and not qte:
        signaler(a, "colis sans qté/colis → prix pièce incalculable")
    if f == "piece" and not pu:
        signaler(a, "pièce sans poids unitaire → €/kg incalculable")
    # Le poids unitaire et le poids colis n'entrent dans le €/kg qu'en format pièce/colis :
    # en format kg (pièce entière de viande, jambon…) un gros poids est normal et sans effet.
    if f == "piece" and pu and pu > 5:
        signaler(a, f"poids unitaire {pu} kg (poids du colis saisi par erreur ?)")
    if f == "colis" and pc and pu and qte and abs(pc - pu * qte) > 0.01:
        signaler(a, f"poids colis {pc} ≠ {qte} × {pu}")
    if kg is not None and kg > 0 and not (KG_MIN <= kg <= KG_MAX):
        motif = f"€/kg dérivé {kg:.2f} hors plage {KG_MIN:.0f}–{KG_MAX:.0f}"
        # Signature typique du bug : prix d'une pièce stocké en « colis ».
        if f == "colis" and pu and p is not None and KG_MIN <= p / pu <= KG_MAX:
            motif += f" → si {p:.2f} € est le prix d'UNE pièce : {p / pu:.2f} €/kg (format « pièce » probable)"
        signaler(a, motif)

print(f"--- 2. Articles suspects : {len(anomalies)} / {len(articles)} ---")
for a in articles:
    if a["id"] not in anomalies:
        continue
    print(f"  #{a['id']:<5} {a['fournisseur'] or '?'} · {a['code_article']} · {a['designation']}")
    print(f"         {fmt(a['prix_achat_ht'], ' €')} / {a['format_prix']} · qté {a['qte_par_colis']} · "
          f"pu {a['poids_unitaire_kg']} kg · colis {a['poids_colis_kg']} kg · €/kg {fmt(prix_kg(a))}")
    for m in anomalies[a["id"]]:
        print(f"         ⚠ {m}")
print()

def prix_piece(a):
    """Miroir de _calc_prix_piece (routes_achats.py)."""
    p, f = a["prix_achat_ht"], a["format_prix"]
    if p is None:
        return None
    if f == "piece":
        return p
    if f == "colis" and a["qte_par_colis"]:
        return p / a["qte_par_colis"]
    if f == "kg" and a["poids_unitaire_kg"]:
        return p * a["poids_unitaire_kg"]
    return None


# Marge RÉELLE de chaque produit de vente, calculée comme _calc_marge (base HT/HT).
# On ne signale que ce qui fausse effectivement le chiffre affiché.
TAUX_MAX = 0.80
print(f"--- 3. Marges de vente aberrantes (taux < 0 ou > {TAUX_MAX:.0%}, incalculable, "
      "ou pièce sans poids vente) ---")
par_id = {a["id"]: a for a in articles}
liaisons = cur.execute(
    """SELECT v.id, v.nom, v.prix_vente_ttc, v.tva_percent, v.unite_vente, v.poids_piece_kg,
              gv.ligne_choisie_id
       FROM comparatif_groupe_vente gv
       JOIN catalogue_vente v ON v.id = gv.catalogue_vente_id
       WHERE gv.ligne_choisie_id IS NOT NULL AND v.actif = 1
       ORDER BY v.nom""").fetchall()
n = 0
for r in liaisons:
    a = par_id.get(r["ligne_choisie_id"])
    unite = r["unite_vente"] or "kg"
    motifs, taux, cout, ht = [], None, None, None
    if a is None:
        motifs.append("article d'achat de référence inactif ou supprimé")
    elif r["prix_vente_ttc"]:
        ht = r["prix_vente_ttc"] / (1 + (r["tva_percent"] or 0) / 100)
        kg, ppk = prix_kg(a), r["poids_piece_kg"]
        if unite == "piece":
            # Poids pièce vente ≠ poids pièce achat d'un facteur ≥ 5 : faute de virgule probable
            # (ex. bocal 0,72 kg saisi 0,072 côté vente → coût ÷ 10).
            pu = a["poids_unitaire_kg"] if a["format_prix"] == "piece" else None
            if ppk and pu and not (0.2 <= ppk / pu <= 5):
                motifs.append(f"poids pièce vente {ppk} kg vs achat {pu} kg : faute de virgule ?")
            if kg is not None and ppk:
                cout = kg * ppk
            else:
                cout = prix_piece(a)
                motifs.append("vendu à la pièce SANS poids pièce côté vente → coût = "
                              "prix pièce achat (repli peu fiable)")
        else:
            cout = kg
        if cout is None:
            motifs.append("marge incalculable (coût d'achat indérivable)")
        elif cout == 0:
            motifs.append("prix d'achat à 0 € dans le catalogue achats")
        elif ht > 0:
            taux = (ht - cout) / ht
            if taux < 0 or taux > TAUX_MAX:
                motifs.append(f"taux de marque {taux:.0%}")
    if motifs:
        n += 1
        detail = (f"vente HT {ht:.2f} − coût {cout:.2f} €/{unite}" if ht and cout is not None else "")
        print(f"  {r['nom']} ({fmt(r['prix_vente_ttc'], ' € TTC')}/{unite}) → achat #{r['ligne_choisie_id']} "
              f"{(a or {}).get('designation', '')}")
        if detail:
            print(f"         {detail}")
        for m in motifs:
            print(f"         ⚠ {m}")
print(f"  {n} produit(s) de vente à revoir sur {len(liaisons)} reliés." if n else "  Aucun.")

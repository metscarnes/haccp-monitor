#!/usr/bin/env python3
"""
corriger_annexes_produit.py — Lignes facture classées en ANNEXE (transport, taxe…) alors que
leur libellé ou leur code correspond à un ARTICLE du catalogue du même fournisseur
(ex. « ART8 » chez Elivia, saisi en transport). Les repasse en marchandise et les
rattache à la fiche catalogue.

Par défaut : DIAGNOSTIC SEUL (rien n'est écrit). Pour chaque ligne, le script montre la
facture entière et contrôle le risque de DOUBLON (même article déjà présent en marchandise
sur la facture, ou ligne égale au total papier) : un doublon ne doit pas être reclassé
mais supprimé dans l'écran Facture — il est alors ignoré.

    python3 scripts/corriger_annexes_produit.py                      # diagnostic
    python3 scripts/corriger_annexes_produit.py --designation ART8   # un seul libellé
    python3 scripts/corriger_annexes_produit.py --ligne 1234 --appliquer

--appliquer : sauvegarde la base dans backups/ puis corrige les lignes NON suspectes.
--ligne     : restreint à une (ou plusieurs) ligne(s) par id — recommandé avec --appliquer.

Compléter le poids/prix (une seule --ligne) et, si la ligne englobait des frais, les
ressortir en lignes annexes. Le total de la facture doit rester identique, sinon refus :

    python3 scripts/corriger_annexes_produit.py --ligne 1589 --poids 53 --prix 13.75 --appliquer
    python3 scripts/corriger_annexes_produit.py --ligne 1363 --poids 119 --prix 12.50 \\
            --annexe "transport:Transport:2.50" --annexe "taxe:Taxes ART8:9.82" --appliquer
"""

import argparse
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ap = argparse.ArgumentParser()
ap.add_argument("db", nargs="?", default=str(Path(__file__).parent.parent / "haccp.db"))
ap.add_argument("--designation", help="ne traiter que ce libellé (insensible à la casse)")
ap.add_argument("--ligne", type=int, action="append", help="id de ligne facture (répétable)")
ap.add_argument("--appliquer", action="store_true", help="écrire en base (sinon diagnostic seul)")
ap.add_argument("--poids", type=float, help="poids facturé (kg) à renseigner — une seule --ligne")
ap.add_argument("--prix", type=float, help="prix HT au kg à renseigner — une seule --ligne")
ap.add_argument("--annexe", action="append", default=[],
                help="frais à ressortir de la ligne : 'type:libellé:montant' (type = transport|taxe|consigne)")
args = ap.parse_args()

if (args.poids is None) != (args.prix is None):
    sys.exit("--poids et --prix vont ensemble.")
if (args.poids is not None or args.annexe) and len(args.ligne or []) != 1:
    sys.exit("--poids/--prix/--annexe exigent exactement une --ligne.")
ANNEXES = []
for a in args.annexe:
    try:
        t, lib, m = a.split(":", 2)
        ANNEXES.append((t.strip(), lib.strip(), round(float(m.replace(",", ".")), 2)))
    except ValueError:
        sys.exit(f"--annexe invalide : {a!r} (attendu 'type:libellé:montant')")
    if t.strip() not in ("transport", "taxe", "consigne"):
        sys.exit(f"--annexe : type {t!r} non autorisé (transport|taxe|consigne)")

DB = Path(args.db)
conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row
cur = conn.cursor()


def norm_txt(s):
    return re.sub(r"\s+", " ", (s or "").strip().upper())


def racine_code(code):
    """'07991-07' → '7991' ; '7991-7' → '7991' ; '001295' → '1295' (cf. codes papier ≠ catalogue)."""
    c = re.sub(r"[\s.]", "", code or "")
    if not c:
        return ""
    return c.split("-")[0].lstrip("0") or "0"


def eur(x):
    return f"{(x or 0):,.2f} €".replace(",", " ")


# ── Catalogue par fournisseur ────────────────────────────────────────────────
catalogue = {}
_tva = "tva_percent" if "tva_percent" in {c[1] for c in cur.execute("PRAGMA table_info(catalogue_fournisseur)")} \
    else "5.5"
for r in cur.execute(f"SELECT id, fournisseur_id, code_article, designation, actif, "
                     f"COALESCE({_tva}, 5.5) AS tva FROM catalogue_fournisseur"):
    catalogue.setdefault(r["fournisseur_id"], []).append(r)


def fiche_pour(ligne):
    """Fiche catalogue unique du même fournisseur : par racine de code, sinon par libellé exact."""
    fiches = catalogue.get(ligne["fournisseur_id"], [])
    if ligne["catalogue_fournisseur_id"]:
        return next((f for f in fiches if f["id"] == ligne["catalogue_fournisseur_id"]), None), "déjà liée"
    rc = racine_code(ligne["code_article"])
    if rc:
        c = [f for f in fiches if racine_code(f["code_article"]) == rc]
        if len(c) == 1:
            return c[0], "code"
    d = norm_txt(ligne["designation"])
    c = [f for f in fiches if norm_txt(f["designation"]) == d]
    if len(c) == 1:
        return c[0], "libellé"
    # libellé court type « ART8 » contenu dans la désignation catalogue (« ART8 BOVIN »)
    c = [f for f in fiches if d and re.search(rf"\b{re.escape(d)}\b", norm_txt(f["designation"]))]
    if len(c) == 1:
        return c[0], "libellé partiel"
    return None, f"{len(c)} candidat(s)" if c else "aucune fiche"


# ── Lignes annexes candidates ────────────────────────────────────────────────
sql = """SELECT fl.*, f.fournisseur_id, f.numero_facture, f.date_facture, f.statut,
                f.total_ht_papier, f.montant_total_ht_facture, fo.nom AS fournisseur
         FROM facture_lignes fl
         JOIN factures f ON f.id = fl.facture_id
         LEFT JOIN fournisseurs fo ON fo.id = f.fournisseur_id
         WHERE COALESCE(fl.type_ligne, 'marchandise') <> 'marchandise'"""
params = []
if args.ligne:
    sql += f" AND fl.id IN ({','.join('?' * len(args.ligne))})"
    params += args.ligne
if args.designation:
    sql += " AND UPPER(TRIM(fl.designation)) = ?"
    params.append(norm_txt(args.designation))
sql += " ORDER BY f.date_facture, fl.id"

candidates = []
for l in cur.execute(sql, params).fetchall():
    fiche, mode = fiche_pour(l)
    if fiche:
        candidates.append((l, fiche, mode))

print(f"=== Base : {DB} — mode {'APPLICATION' if args.appliquer else 'DIAGNOSTIC (rien n écrit)'} ===\n")
if not candidates:
    print("Aucune ligne annexe correspondant à un article du catalogue.")
    sys.exit(0)

a_corriger = []
for l, fiche, mode in candidates:
    print("─" * 100)
    print(f"Ligne {l['id']}  [{l['type_ligne']}]  « {l['designation']} »  code {l['code_article'] or '-'}")
    print(f"  {l['fournisseur']} — facture {l['numero_facture'] or '(sans n°)'} du {l['date_facture']} "
          f"(id {l['facture_id']}, statut {l['statut']})")
    print(f"  poids {l['poids_facture_kg'] or '-'} kg   prix {l['prix_facture_ht'] or '-'}   "
          f"montant {eur(l['montant_facture_ht'])}")
    print(f"  → fiche catalogue id {fiche['id']} : {fiche['code_article']} « {fiche['designation']} » "
          f"(trouvée par {mode}{'' if fiche['actif'] else ', INACTIVE'})")

    autres = cur.execute(
        """SELECT id, type_ligne, code_article, designation, poids_facture_kg, prix_facture_ht,
                  montant_facture_ht, catalogue_fournisseur_id
           FROM facture_lignes WHERE facture_id = ? ORDER BY id""", (l["facture_id"],)).fetchall()
    print("  Lignes de cette facture :")
    for o in autres:
        moi = " ◄" if o["id"] == l["id"] else ""
        print(f"     #{o['id']:<6} {(o['type_ligne'] or 'marchandise'):<12} {(o['designation'] or '')[:40]:<41}"
              f"{(o['poids_facture_kg'] or 0):>8.2f} kg {(o['prix_facture_ht'] or 0):>8.2f} "
              f"{eur(o['montant_facture_ht']):>14}{moi}")
    somme = sum(o["montant_facture_ht"] or 0 for o in autres)
    papier = l["total_ht_papier"]
    print(f"  Somme des lignes {eur(somme)}   total papier {eur(papier) if papier is not None else 'non saisi'}")

    # ── Contrôles anti-doublon ───────────────────────────────────────────────
    alertes = []
    for o in autres:
        if o["id"] == l["id"] or (o["type_ligne"] or "marchandise") != "marchandise":
            continue
        if o["catalogue_fournisseur_id"] == fiche["id"] or \
                racine_code(o["code_article"]) and racine_code(o["code_article"]) == racine_code(fiche["code_article"]) or \
                norm_txt(o["designation"]) == norm_txt(l["designation"]):
            alertes.append(f"l'article est DÉJÀ facturé en marchandise sur la ligne #{o['id']} "
                           f"({eur(o['montant_facture_ht'])})")
    if papier is not None and abs(somme - papier) > 0.05 and abs((somme - papier) - (l["montant_facture_ht"] or 0)) < 1.0:
        alertes.append("sans cette ligne, la facture boucle avec le total papier → ligne en trop")
    if papier is not None and abs((l["montant_facture_ht"] or 0) - papier) < 1.0 and len(autres) > 1:
        alertes.append("le montant de la ligne = total papier de la facture → probablement le TOTAL saisi comme ligne")
    # Ligne égale au total d'une AUTRE facture du fournisseur → deux factures fusionnées ?
    for f2 in cur.execute(
            """SELECT id, numero_facture, date_facture, total_ht_papier, montant_total_ht_facture
               FROM factures WHERE fournisseur_id = ? AND id <> ?
                 AND (ABS(COALESCE(total_ht_papier, -1) - ?) < 0.05
                      OR ABS(COALESCE(montant_total_ht_facture, -1) - ?) < 0.05)""",
            (l["fournisseur_id"], l["facture_id"], l["montant_facture_ht"] or 0, l["montant_facture_ht"] or 0)):
        alertes.append(f"montant = total de la facture {f2['numero_facture']} du {f2['date_facture']} "
                       f"(id {f2['id']}) déjà en base → DOUBLON entre factures")
    if not (l["poids_facture_kg"] or 0) > 0 and args.poids is None:
        alertes.append("pas de poids facturé : relancer avec --poids et --prix (voir le PDF de la facture)")

    doublon = any("DÉJÀ" in a or "en trop" in a or "TOTAL" in a or "DOUBLON" in a for a in alertes)
    for a in alertes:
        print(f"  ⚠ {a}")
    if doublon:
        print("  ✗ DOUBLON PROBABLE — non corrigé. À supprimer depuis l'écran Facture, pas à reclasser.")
    else:
        print("  ✓ Reclassable en marchandise.")
        a_corriger.append((l, fiche))

print("─" * 100)
print(f"\n{len(candidates)} ligne(s) examinée(s), {len(a_corriger)} reclassable(s).")

# ── Contrôle poids/prix/annexes : le total de la ligne d'origine doit être conservé ──
if args.poids is not None or ANNEXES:
    if not a_corriger:
        sys.exit("La ligne demandée n'est pas reclassable (voir ci-dessus) — rien n'est fait.")
    l0 = a_corriger[0][0]
    m0 = round(l0["montant_facture_ht"] or 0, 2)
    m_march = round(args.poids * args.prix, 2) if args.poids is not None else m0 - sum(a[2] for a in ANNEXES)
    m_ann = sum(a[2] for a in ANNEXES)
    print(f"\nRépartition de la ligne {l0['id']} ({m0:.2f} €) :")
    if args.poids is not None:
        print(f"  marchandise {args.poids:g} kg × {args.prix:.2f} = {m_march:.2f} €")
    for t, lib, m in ANNEXES:
        print(f"  {t:<11} « {lib} » {m:.2f} €")
    print(f"  total {m_march + m_ann:.2f} € (écart {m_march + m_ann - m0:+.2f} €)")
    if abs(m_march + m_ann - m0) > 0.02:
        sys.exit("✗ Le total ne correspond pas au montant d'origine : vérifier poids/prix/frais sur le PDF. "
                 "Rien n'est fait.")
    print("  ✓ Total de la facture conservé.")

if not args.appliquer:
    if a_corriger:
        ids = " ".join(f"--ligne {l['id']}" for l, _ in a_corriger)
        print(f"\nPour corriger :\n  python3 scripts/corriger_annexes_produit.py {ids} --appliquer")
    sys.exit(0)

if not a_corriger:
    print("Rien à écrire.")
    sys.exit(0)

# ── Application : sauvegarde puis UPDATE borné ───────────────────────────────
bdir = DB.parent / "backups"
bdir.mkdir(exist_ok=True)
bfile = bdir / f"haccp_avant_reclassement_annexes_{datetime.now():%Y%m%d_%H%M%S}.db"
dst = sqlite3.connect(str(bfile))
conn.backup(dst)
ok = dst.execute("PRAGMA integrity_check").fetchone()[0]
dst.close()
if ok != "ok":
    print(f"Sauvegarde invalide ({ok}) — abandon, rien n'a été modifié.")
    sys.exit(1)
print(f"\nSauvegarde : {bfile} (integrity_check = ok)")

with conn:
    for l, fiche in a_corriger:
        cur.execute(
            """UPDATE facture_lignes
               SET type_ligne = 'marchandise',
                   catalogue_fournisseur_id = COALESCE(catalogue_fournisseur_id, ?),
                   tva_pct = ?
               WHERE id = ? AND COALESCE(type_ligne, 'marchandise') <> 'marchandise'""",
            (fiche["id"], fiche["tva"], l["id"]))
        print(f"  ligne {l['id']} → marchandise, fiche {fiche['id']}, TVA {fiche['tva']:g} % "
              f"({cur.rowcount} modifiée)")
        if args.poids is not None:
            cur.execute(
                """UPDATE facture_lignes
                   SET poids_facture_kg = ?, prix_facture_ht = ?, montant_facture_ht = ?, unite_prix = 'kg'
                   WHERE id = ?""", (args.poids, args.prix, round(args.poids * args.prix, 2), l["id"]))
            print(f"  ligne {l['id']} → {args.poids:g} kg × {args.prix:.2f} = {args.poids * args.prix:.2f} €")
        elif ANNEXES:
            cur.execute("UPDATE facture_lignes SET montant_facture_ht = ? WHERE id = ?",
                        (round((l["montant_facture_ht"] or 0) - sum(a[2] for a in ANNEXES), 2), l["id"]))
        for t, lib, m in ANNEXES:
            # TVA reprise d'une ligne du même type sur la facture, s'il y en a une
            tva = cur.execute(
                "SELECT tva_pct FROM facture_lignes WHERE facture_id = ? AND type_ligne = ? "
                "AND tva_pct IS NOT NULL LIMIT 1", (l["facture_id"], t)).fetchone()
            cur.execute(
                """INSERT INTO facture_lignes (facture_id, designation, type_ligne, unite, unite_prix,
                                              montant_facture_ht, tva_pct)
                   VALUES (?, ?, ?, 'kg', 'kg', ?, ?)""",
                (l["facture_id"], lib, t, m, tva[0] if tva else None))
            print(f"  + ligne {t} « {lib} » {m:.2f} € (id {cur.lastrowid})")
        tot = cur.execute("SELECT ROUND(SUM(montant_facture_ht), 2) FROM facture_lignes WHERE facture_id = ?",
                          (l["facture_id"],)).fetchone()[0]
        print(f"  somme des lignes de la facture : {tot:.2f} €")
print("\nTerminé. Le total de chaque facture est inchangé : seules la nature des lignes, le lien "
      "catalogue et, si demandé, le poids/prix sont mis à jour.")

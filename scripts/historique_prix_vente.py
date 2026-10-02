#!/usr/bin/env python3
"""
historique_prix_vente.py — Reconstitue l'évolution des PRIX DE VENTE à partir des
sauvegardes de la base (.db).

L'application ne conserve qu'un prix de vente par produit (catalogue_vente.prix_vente_ttc,
écrasé à chaque modification) : il n'y a pas d'historique. En revanche, chaque sauvegarde
.db est une photo du catalogue à sa date. Le script les lit toutes (lecture seule) et
liste, produit par produit, les changements de prix d'une photo à l'autre.

Le porc est mis en avant (sous-famille « porc » ou produit relié à un article Cooperl
dans le comparateur), avec la date du passage chez Cooperl (1re facture).

    python3 scripts/historique_prix_vente.py [dossiers ou fichiers .db ...] [--tout]

Sans argument : cherche les .db dans ~/haccp-monitor (sous-dossiers compris).
--tout : liste aussi les produits hors porc.
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
ap.add_argument("chemins", nargs="*", default=[str(Path(__file__).parent.parent)])
ap.add_argument("--tout", action="store_true", help="tous les produits, pas seulement le porc")
args = ap.parse_args()

BASE_ACTUELLE = (Path(__file__).parent.parent / "haccp.db").resolve()


def date_photo(p: Path):
    """Date de la photo : horodatage dans le nom (AAAAMMJJ[_HHMMSS]) sinon date du fichier."""
    if p.resolve() == BASE_ACTUELLE:
        return datetime.now(), "base actuelle"
    m = re.search(r"(20\d{6})[_-]?(\d{6})?", p.name)
    if m:
        try:
            return datetime.strptime(m.group(1) + (m.group(2) or "000000"), "%Y%m%d%H%M%S"), "nom"
        except ValueError:
            pass
    return datetime.fromtimestamp(p.stat().st_mtime), "date fichier"


fichiers = set()
for c in args.chemins:
    p = Path(c).expanduser()
    if p.is_file():
        fichiers.add(p.resolve())
    elif p.is_dir():
        fichiers |= {f.resolve() for f in p.rglob("*.db") if f.is_file()}

photos = []  # (date, source, fichier, {id: (nom, prix, famille, sous_famille, unite)})
for f in fichiers:
    try:
        conn = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(catalogue_vente)")}
        if "prix_vente_ttc" not in cols:
            continue
        sf = "sous_famille" if "sous_famille" in cols else "NULL"
        fa = "famille" if "famille" in cols else "NULL"
        un = "unite_vente" if "unite_vente" in cols else "'kg'"
        prix = {r[0]: r[1:] for r in conn.execute(
            f"SELECT id, nom, prix_vente_ttc, {fa}, {sf}, {un} FROM catalogue_vente")}
        conn.close()
    except sqlite3.DatabaseError:
        continue
    if not prix:
        continue
    d, src = date_photo(f)
    photos.append((d, src, f, prix))

photos.sort(key=lambda t: t[0])
if not photos:
    sys.exit("Aucune sauvegarde contenant le catalogue de vente n'a été trouvée.")

# ── Repères depuis la base actuelle : date d'arrivée de Cooperl, produits liés à Cooperl ─
debut_cooperl, lies_cooperl = None, set()
try:
    cur = sqlite3.connect(f"file:{BASE_ACTUELLE}?mode=ro", uri=True)
    r = cur.execute("""SELECT MIN(f.date_facture) FROM factures f JOIN fournisseurs fo ON fo.id = f.fournisseur_id
                       WHERE UPPER(fo.nom) LIKE '%COOPERL%'""").fetchone()
    debut_cooperl = r[0] if r else None
    tables = {t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if {"comparatif_groupe_vente", "comparatif_groupe_ligne"} <= tables:
        lies_cooperl = {t[0] for t in cur.execute(
            """SELECT DISTINCT gv.catalogue_vente_id
               FROM comparatif_groupe_vente gv
               JOIN comparatif_groupe_ligne gl ON gl.groupe_id = gv.groupe_id
               JOIN catalogue_fournisseur cf ON cf.id = gl.catalogue_fournisseur_id
               JOIN fournisseurs fo ON fo.id = cf.fournisseur_id
               WHERE UPPER(fo.nom) LIKE '%COOPERL%'""")}
except sqlite3.DatabaseError:
    pass

print("=" * 100)
print(f"PHOTOS DU CATALOGUE DE VENTE TROUVÉES : {len(photos)}")
print("=" * 100)
for d, src, f, prix in photos:
    print(f"  {d:%d/%m/%Y %H:%M}  ({src:<13}) {len(prix):>4} produits   {f}")
if debut_cooperl:
    avant = [p for p in photos if p[0].strftime("%Y-%m-%d") < debut_cooperl]
    print(f"\n  Première facture Cooperl : {debut_cooperl}. Photos ANTÉRIEURES : {len(avant)}")
    if not avant:
        print("  ⚠ Aucune photo du catalogue avant Cooperl : impossible de voir les prix de vente d'avant\n"
              "    dans ces fichiers. Chercher une sauvegarde plus ancienne (copie cloud rclone, clé USB…).")


def est_porc(pid, info):
    nom, _, fam, sfam, _ = info
    txt = f"{fam or ''} {sfam or ''} {nom or ''}".upper()
    return pid in lies_cooperl or "PORC" in (sfam or "").upper() or \
        re.search(r"\b(PORC|ECHINE|TRAVERS|FILET MIGNON|COTE.? (DE )?PORC|ROTI DE PORC|LONGE|POITRINE|SAUCISSE)\b",
                  txt) is not None


# ── Chronologie par produit ──────────────────────────────────────────────────
ids = set().union(*(p[3].keys() for p in photos))
lignes = []
for pid in ids:
    histo, dernier = [], None
    for d, src, f, prix in photos:
        if pid not in prix:
            continue
        info = prix[pid]
        if info[1] != dernier:
            histo.append((d, info[1]))
            dernier = info[1]
    info = next(p[3][pid] for p in reversed(photos) if pid in p[3])
    porc = est_porc(pid, info)
    if not porc and not args.tout:
        continue
    lignes.append((porc, info, histo, pid))

print("\n" + "=" * 100)
print("PRODUITS DONT LE PRIX A CHANGÉ" + ("" if args.tout else " — PORC (option --tout pour tout voir)"))
print("=" * 100)
changes = [l for l in lignes if len([h for h in l[2] if h[1] is not None]) > 1]
for porc, info, histo, pid in sorted(changes, key=lambda l: (not l[0], l[1][0] or "")):
    nom, prix_act, fam, sfam, unite = info
    tag = "Cooperl" if pid in lies_cooperl else ""
    print(f"\n  {nom}  [{sfam or fam or '-'}] {tag}  (€ TTC/{unite or 'kg'})")
    prec = None
    for d, p in histo:
        var = f"  {100 * (p - prec) / prec:+.1f} %" if prec and p else ""
        print(f"     {d:%d/%m/%Y}  {p if p is not None else '—':>8}{var}")
        prec = p if p else prec
    first = next((p for _, p in histo if p), None)
    if first and prix_act and first != prix_act:
        print(f"     → total : {first} → {prix_act} ({100 * (prix_act - first) / first:+.1f} %)")
if not changes:
    print("\n  Aucun changement de prix entre les photos disponibles.")

print("\n" + "=" * 100)
print(f"PRIX INCHANGÉS sur toute la période couverte ({len(lignes) - len(changes)} produits)")
print("=" * 100)
for porc, info, histo, pid in sorted([l for l in lignes if l not in changes], key=lambda l: l[1][0] or ""):
    print(f"  {(info[0] or '')[:50]:<51} {info[1] if info[1] is not None else '—':>8} € TTC/{info[4] or 'kg'}")

print("\nLecture seule — aucune donnée modifiée.")

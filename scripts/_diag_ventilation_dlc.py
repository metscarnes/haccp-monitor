import sqlite3, sys
db = sys.argv[1] if len(sys.argv)>1 else "haccp.db"
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True); c.row_factory = sqlite3.Row

BASE = """
FROM reception_lignes rl
JOIN receptions r ON r.id = rl.reception_id
LEFT JOIN produits p ON p.id = rl.produit_id
LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
LEFT JOIN fournisseurs f ON f.id = rl.fournisseur_id
WHERE r.statut='cloturee' AND rl.conforme=1 AND r.livraison_refusee=0
  AND COALESCE(rl.statut,'complet') <> 'en_attente'
  AND rl.dlc IS NULL
  AND NOT EXISTS (SELECT 1 FROM dlc_devenir dd
                  WHERE dd.source_type='reception_ligne' AND dd.source_id=rl.id)
"""

print("=== VENTILATION des lignes sans DLC, par dlc_type effectif ===\n")
q = c.execute(f"""
SELECT COALESCE(NULLIF(rl.dlc_type,''), cf.dlc_type, 'dlc(defaut)') AS type_eff,
       COUNT(*) n,
       SUM(CASE WHEN rl.date_abattage IS NOT NULL THEN 1 ELSE 0 END) avec_abattage,
       SUM(CASE WHEN rl.dluo IS NOT NULL THEN 1 ELSE 0 END) avec_dluo
{BASE} GROUP BY type_eff ORDER BY n DESC""").fetchall()
for r in q:
    print(f"  {r['type_eff']:<18} {r['n']:>4} lignes   (dont date_abattage renseignee: {r['avec_abattage']}, dluo: {r['avec_dluo']})")

print("\n=== LES VRAIS OUBLIS : ni carcasse, ni no_dlc, aucune date ===\n")
rows = c.execute(f"""
SELECT rl.id, COALESCE(p.nom, cf.designation, rl.designation_libre) AS nom,
       rl.numero_lot, rl.poids_kg, r.date_reception, f.nom AS fourn,
       COALESCE(NULLIF(rl.dlc_type,''), cf.dlc_type, 'dlc(defaut)') AS type_eff,
       cf.famille, cf.sous_famille
{BASE}
  AND COALESCE(NULLIF(rl.dlc_type,''), cf.dlc_type, 'dlc') NOT IN ('no_dlc','date_abattage')
  AND rl.date_abattage IS NULL AND rl.dluo IS NULL
ORDER BY r.date_reception DESC""").fetchall()
print(f"TOTAL VRAIS OUBLIS : {len(rows)}\n")
for r in rows:
    print(f"  #{r['id']:<6} {str(r['nom'])[:44]:<44} lot={str(r['numero_lot'] or '-')[:18]:<18} {r['poids_kg']:>7} kg  {r['date_reception']}  {r['fourn'] or '-'}  [{r['famille'] or '?'}/{r['sous_famille'] or '?'}]")

print("\n=== RECHERCHE : Pate campagne / roti four / calvados ===\n")
for r in c.execute("""
SELECT rl.id, COALESCE(p.nom, cf.designation, rl.designation_libre) AS nom,
       rl.dlc, rl.dluo, rl.date_abattage, rl.dlc_type AS type_ligne, cf.dlc_type AS type_cat,
       rl.numero_lot, rl.statut, rl.conforme, r.statut AS rstatut, r.date_reception,
       r.livraison_refusee, cf.famille, cf.sous_famille,
       (SELECT statut FROM dlc_devenir dd WHERE dd.source_type='reception_ligne' AND dd.source_id=rl.id) AS devenir
FROM reception_lignes rl
JOIN receptions r ON r.id = rl.reception_id
LEFT JOIN produits p ON p.id = rl.produit_id
LEFT JOIN catalogue_fournisseur cf ON cf.id = rl.catalogue_fournisseur_id
WHERE LOWER(COALESCE(p.nom, cf.designation, rl.designation_libre)) LIKE '%pate%'
   OR LOWER(COALESCE(p.nom, cf.designation, rl.designation_libre)) LIKE '%calvados%'
   OR LOWER(COALESCE(p.nom, cf.designation, rl.designation_libre)) LIKE '%roti%four%'
ORDER BY r.date_reception DESC LIMIT 25"""):
    print(f"  #{r['id']:<6} {str(r['nom'])[:46]:<46}")
    print(f"          dlc={r['dlc']}  dluo={r['dluo']}  abattage={r['date_abattage']}  type_ligne={r['type_ligne']}  type_cat={r['type_cat']}")
    print(f"          lot={r['numero_lot']}  statut_ligne={r['statut']}  conforme={r['conforme']}  recep={r['rstatut']}  refusee={r['livraison_refusee']}  devenir={r['devenir']}  recu_le={r['date_reception']}  [{r['famille']}/{r['sous_famille']}]")

"""
fix_produit_id_nullable.py
Rend produit_id (et fournisseur_id si nécessaire) nullable dans fiches_incident.
À lancer UNE SEULE FOIS sur le serveur avec le backend arrêté :
    sudo systemctl stop haccp-backend
    cd ~/haccp-monitor && python3 scripts/fix_produit_id_nullable.py
    sudo systemctl start haccp-backend
"""
import asyncio
from pathlib import Path
import aiosqlite

DB_PATH = Path(__file__).parent.parent / "haccp.db"


async def main():
    print(f"Base : {DB_PATH}")
    if not DB_PATH.exists():
        print("ERREUR : base introuvable")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        # Lire l'état actuel des colonnes
        cur = await db.execute("PRAGMA table_info(fiches_incident)")
        cols = await cur.fetchall()
        if not cols:
            print("Table fiches_incident introuvable — rien à faire.")
            return

        prod_col  = next((c for c in cols if c[1] == 'produit_id'),    None)
        fourn_col = next((c for c in cols if c[1] == 'fournisseur_id'), None)

        prod_nn  = prod_col  and prod_col[3]  == 1   # notnull flag
        fourn_nn = fourn_col and fourn_col[3] == 1

        if not prod_nn and not fourn_nn:
            print("✓ produit_id et fournisseur_id sont déjà nullable — rien à faire.")
            return

        print(f"produit_id NOT NULL = {prod_nn}  |  fournisseur_id NOT NULL = {fourn_nn}")
        print("Reconstruction de la table fiches_incident…")

        has_fourn_nom   = any(c[1] == 'fournisseur_nom'    for c in cols)
        has_commentaire = any(c[1] == 'commentaire'        for c in cols)
        has_temp_coeur  = any(c[1] == 'temperature_coeur'  for c in cols)
        fourn_nom_sel   = "fournisseur_nom"   if has_fourn_nom   else "NULL"
        commentaire_sel = "commentaire"       if has_commentaire else "NULL"
        temp_coeur_sel  = "temperature_coeur" if has_temp_coeur  else "NULL"

        await db.execute("PRAGMA foreign_keys = OFF")
        await db.execute("DROP TABLE IF EXISTS fiches_incident_new")
        await db.execute("""
            CREATE TABLE fiches_incident_new (
                id                         INTEGER PRIMARY KEY AUTOINCREMENT,
                reception_id               INTEGER NOT NULL,
                reception_ligne_id         INTEGER,
                date_incident              DATE    DEFAULT CURRENT_DATE,
                heure_incident             TEXT    NOT NULL,
                fournisseur_id             INTEGER,
                fournisseur_nom            TEXT,
                produit_id                 INTEGER,
                numero_lot                 TEXT,
                nature_probleme            TEXT    NOT NULL,
                description                TEXT,
                action_immediate           TEXT    NOT NULL,
                livreur_present            INTEGER NOT NULL DEFAULT 0,
                signature_livreur_filename TEXT,
                etiquette_reprise_imprimee INTEGER DEFAULT 0,
                action_corrective          TEXT,
                suivi                      TEXT,
                commentaire                TEXT,
                temperature_coeur          REAL,
                statut                     TEXT    DEFAULT 'ouverte',
                cloturee_par               INTEGER,
                cloturee_le                DATETIME,
                created_at                 DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute(f"""
            INSERT INTO fiches_incident_new
                SELECT id, reception_id, reception_ligne_id, date_incident,
                       heure_incident, fournisseur_id,
                       {fourn_nom_sel},
                       produit_id, numero_lot, nature_probleme, description,
                       action_immediate, livreur_present,
                       signature_livreur_filename, etiquette_reprise_imprimee,
                       action_corrective, suivi, {commentaire_sel}, {temp_coeur_sel},
                       statut, cloturee_par, cloturee_le, created_at
                FROM fiches_incident
        """)
        await db.execute("DROP TABLE fiches_incident")
        await db.execute("ALTER TABLE fiches_incident_new RENAME TO fiches_incident")
        await db.execute("PRAGMA foreign_keys = ON")
        await db.commit()
        print("✓ Migration terminée — produit_id et fournisseur_id sont maintenant nullable.")

        # Vérification
        cur2 = await db.execute("PRAGMA table_info(fiches_incident)")
        cols2 = await cur2.fetchall()
        for c in cols2:
            if c[1] in ('produit_id', 'fournisseur_id'):
                status = "NOT NULL" if c[3] else "nullable"
                print(f"  {c[1]}: {status}")


asyncio.run(main())

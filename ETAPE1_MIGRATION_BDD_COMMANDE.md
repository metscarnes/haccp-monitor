# ÉTAPE 1 — Migration BDD pour Module Commande

## 📋 Vue d'ensemble

**Objectif** : Enrichir la BDD pour supporter commandes + catalogue fournisseur + maturation carcasses, **SANS casser** le code existant.

**Principe** : Toutes les colonnes nouvelles sont **NULLABLE** → l'app actuelle fonctionne même si ces colonnes ne sont jamais remplies.

---

## 1️⃣ TABLES À MODIFIER (ALTER TABLE)

### A. Table `fournisseurs` (enrichissement)

| Colonne | Type | Actuellement | À ajouter ? | Nullable | Raison |
|---------|------|--------------|------------|----------|--------|
| id | INTEGER | ✅ | Non | — | PK |
| boutique_id | INTEGER | ✅ | Non | — | FK |
| nom | TEXT | ✅ | Non | — | Nom court |
| **email_commercial** | TEXT | ❌ | **OUI** | **OUI** | Mail pour envoi commande |
| **telephone** | TEXT | ❌ | **OUI** | **OUI** | Contact fournisseur |
| **adresse** | TEXT | ❌ | **OUI** | **OUI** | Livraison |
| **conditions_paiement** | TEXT | ❌ | **OUI** | **OUI** | Crédit/délai |
| actif | BOOLEAN | ✅ | Non | — | Déjà là |
| **date_maj** | DATETIME | ❌ | **OUI** | **OUI** | Historique |
| created_at | DATETIME | ✅ | Non | — | Déjà là |

**SQL de migration** :
```sql
ALTER TABLE fournisseurs ADD COLUMN email_commercial TEXT;
ALTER TABLE fournisseurs ADD COLUMN telephone TEXT;
ALTER TABLE fournisseurs ADD COLUMN adresse TEXT;
ALTER TABLE fournisseurs ADD COLUMN conditions_paiement TEXT;
ALTER TABLE fournisseurs ADD COLUMN date_maj DATETIME DEFAULT CURRENT_TIMESTAMP;
```

---

### B. Table `reception_lignes` (pour multi-lots carcasses)

**ATTENTION** : Cette table sert 6 modules existants (cuisson, refroidissement, fabrication, stock, ouvertures, DLC).  
Le changement sera fait à l'Étape 4 (multi-lots). Pour l'instant : on ajoute juste `date_abattage`.

| Colonne | Type | Actuellement | À ajouter ? | Nullable | Raison |
|---------|------|--------------|------------|----------|--------|
| id | INTEGER | ✅ | Non | — | PK |
| reception_id | INTEGER | ✅ | Non | — | FK |
| produit_id | INTEGER | ✅ | Non | — | FK |
| fournisseur_id | INTEGER | ✅ | Non | — | FK |
| numero_lot | TEXT | ✅ | Non | — | Lot fournisseur |
| dlc | DATE | ✅ | Non | — | DLC fournisseur |
| **date_abattage** | DATE | ❌ | **OUI** | **OUI** | Carcasses (sans DLC) |
| ... | ... | ✅ | Non | — | Autres champs |

**SQL de migration** :
```sql
ALTER TABLE reception_lignes ADD COLUMN date_abattage DATE;
```

---

## 2️⃣ TABLES À CRÉER (NEW)

### C. Table `commandes` (orchestration)

```sql
CREATE TABLE IF NOT EXISTS commandes (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id          INTEGER NOT NULL DEFAULT 1,
    fournisseur_id       INTEGER NOT NULL,
    date_commande        DATE    NOT NULL DEFAULT CURRENT_DATE,
    numero_commande      TEXT    UNIQUE,                    -- "CMD-2026-001"
    statut               TEXT    NOT NULL DEFAULT 'brouillon', -- brouillon|confirmee|livree|annulee
    montant_total_ht     REAL    DEFAULT 0.0,
    montant_total_ttc    REAL    DEFAULT 0.0,
    date_livraison_prevue DATE,
    commentaire          TEXT,
    personnel_id         INTEGER,                          -- Qui a créé
    date_envoi_mail      DATETIME,                         -- Quand le mail a été envoyé
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boutique_id)  REFERENCES boutiques(id),
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id),
    FOREIGN KEY (personnel_id)   REFERENCES personnel(id)
);

CREATE INDEX IF NOT EXISTS idx_commandes_fournisseur
    ON commandes(fournisseur_id, date_commande DESC);
CREATE INDEX IF NOT EXISTS idx_commandes_statut
    ON commandes(statut, date_commande DESC);
```

| Colonne | Type | Nullable | Raison |
|---------|------|----------|--------|
| id | INTEGER | — | PK auto-généré |
| boutique_id | INTEGER | Non | FK boutique (défaut=1) |
| fournisseur_id | INTEGER | Non | FK fournisseur |
| date_commande | DATE | Non | Quand commandé |
| numero_commande | TEXT | Oui | "CMD-20260603-001" (unique, auto-généré) |
| statut | TEXT | Non | brouillon / confirmee / livree / annulee |
| montant_total_ht | REAL | Oui | Calculé depuis lignes |
| montant_total_ttc | REAL | Oui | Calculé depuis lignes + TVA |
| date_livraison_prevue | DATE | Oui | Calendrier |
| commentaire | TEXT | Oui | Notes libres |
| personnel_id | INTEGER | Oui | Qui a créé |
| date_envoi_mail | DATETIME | Oui | Traçabilité mail |
| created_at | DATETIME | Non | Auto |

---

### D. Table `commande_lignes` (articles ordonnés)

```sql
CREATE TABLE IF NOT EXISTS commande_lignes (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    commande_id          INTEGER NOT NULL,
    code_fournisseur     TEXT    NOT NULL,                -- Code article fournisseur (ex: "BF-250G")
    designation          TEXT    NOT NULL,                -- "Filet de boeuf"
    prix_unitaire_ht     REAL    NOT NULL DEFAULT 0.0,
    quantite_commandee   REAL    NOT NULL,
    unite                TEXT    NOT NULL DEFAULT 'kg',   -- kg, piece, boite, ...
    montant_ht           REAL    DEFAULT 0.0,             -- qty × prix (calculé)
    en_stock             INTEGER DEFAULT 0,               -- 0=non 1=oui
    dlc_prevue           DATE,                            -- Si connu
    commentaire_ligne    TEXT,
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (commande_id) REFERENCES commandes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_commande_lignes_commande
    ON commande_lignes(commande_id);
```

| Colonne | Type | Nullable | Raison |
|---------|------|----------|--------|
| id | INTEGER | — | PK |
| commande_id | INTEGER | Non | FK commande |
| code_fournisseur | TEXT | Non | Référence exact du fournisseur |
| designation | TEXT | Non | Nom produit (libre) |
| prix_unitaire_ht | REAL | Non | Prix TTC → géré côté app |
| quantite_commandee | REAL | Non | Quantité |
| unite | TEXT | Non | kg/piece/boite/... |
| montant_ht | REAL | Oui | Calculé (qty × prix) |
| en_stock | BOOLEAN | Oui | Fournisseur confirm stock ? |
| dlc_prevue | DATE | Oui | Si fournisseur indique |
| commentaire_ligne | TEXT | Oui | Notes ("+ 2 jours" etc) |
| created_at | DATETIME | Non | Auto |

---

### E. Table `catalogue_fournisseur` (référenciel par fournisseur)

```sql
CREATE TABLE IF NOT EXISTS catalogue_fournisseur (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    fournisseur_id       INTEGER NOT NULL,
    produit_id           INTEGER,                         -- FK nullable (matching optionnel)
    code_article         TEXT    NOT NULL,                -- "BF-250G"
    designation          TEXT    NOT NULL,                -- "Filet de boeuf 250g"
    prix_achat_ht        REAL    NOT NULL,
    prix_achat_ttc       REAL,                            -- Si fourni
    tva_percent          REAL    DEFAULT 5.5,             -- Boeuf
    conditionnement      TEXT,                            -- "carton 4kg", "carcasse", ...
    dlc_type             TEXT,                            -- "dlc" | "date_abattage" | "no_dlc"
    dlc_jours            INTEGER,                         -- Si applicable
    stock_dispo          INTEGER DEFAULT 0,               -- 0/1 dispo chez fournisseur
    date_maj             DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id),
    FOREIGN KEY (produit_id)     REFERENCES produits(id),
    UNIQUE(fournisseur_id, code_article)
);

CREATE INDEX IF NOT EXISTS idx_catalogue_fournisseur_code
    ON catalogue_fournisseur(fournisseur_id, code_article);
CREATE INDEX IF NOT EXISTS idx_catalogue_fournisseur_produit
    ON catalogue_fournisseur(fournisseur_id, produit_id);
```

| Colonne | Type | Nullable | Raison |
|---------|------|----------|--------|
| id | INTEGER | — | PK |
| fournisseur_id | INTEGER | Non | FK fournisseur |
| produit_id | INTEGER | **Oui** | FK produit local (matching optionnel) |
| code_article | TEXT | Non | "BF-250G" exact du fournisseur |
| designation | TEXT | Non | Nom complet |
| prix_achat_ht | REAL | Non | Votre coût d'achat |
| prix_achat_ttc | REAL | Oui | Calculé ou fourni |
| tva_percent | REAL | Oui | 5.5% boeuf / 20% autres |
| conditionnement | TEXT | Oui | Info emballage |
| dlc_type | TEXT | Oui | dlc / date_abattage / no_dlc |
| dlc_jours | INTEGER | Oui | Jours si dlc_type=dlc |
| stock_dispo | BOOLEAN | Oui | Infos fournisseur |
| date_maj | DATETIME | Non | Quand mis à jour |

---

### F. Table `maturation_carcasses` (logs de contrôle)

```sql
CREATE TABLE IF NOT EXISTS maturation_carcasses (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    reception_ligne_id   INTEGER NOT NULL,                -- FK carcasse reçue
    date_abattage        DATE    NOT NULL,
    numero_lot           TEXT    NOT NULL,
    age_jours            INTEGER,                         -- Calculé = today - date_abattage
    date_dernier_controle DATE,
    etat_controle        TEXT,                            -- OK | A_SURVEILLER | NON_CONFORME
    aspect               TEXT,                            -- Normal / Anomalie
    odeur                TEXT,                            -- Normal / Anomalie
    dessiccation         TEXT,                            -- Normal / Anomalie
    poissage             TEXT,                            -- Normal / Anomalie
    parage_effectue      BOOLEAN DEFAULT 0,
    commentaire_controle TEXT,
    decision_humaine     TEXT,                            -- Maturation | Decoupe | Declassement | Destruction
    date_prochain_controle DATE,                          -- J+14, J+21, J+28
    personnel_id         INTEGER,                         -- Qui a contrôlé
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reception_ligne_id) REFERENCES reception_lignes(id),
    FOREIGN KEY (personnel_id)       REFERENCES personnel(id)
);

CREATE INDEX IF NOT EXISTS idx_maturation_reception_ligne
    ON maturation_carcasses(reception_ligne_id);
CREATE INDEX IF NOT EXISTS idx_maturation_date_controle
    ON maturation_carcasses(date_dernier_controle);
```

| Colonne | Type | Nullable | Raison |
|---------|------|----------|--------|
| id | INTEGER | — | PK |
| reception_ligne_id | INTEGER | Non | FK vers carcasse |
| date_abattage | DATE | Non | Ref carcasse |
| numero_lot | TEXT | Non | Identification carcasse |
| age_jours | INTEGER | Oui | Calculé (today - abattage) |
| date_dernier_controle | DATE | Oui | Quand dernier contrôle |
| etat_controle | TEXT | Oui | OK / A_SURVEILLER / NON_CONFORME |
| aspect | TEXT | Oui | Observation |
| odeur | TEXT | Oui | Observation |
| dessiccation | TEXT | Oui | Observation |
| poissage | TEXT | Oui | Observation |
| parage_effectue | BOOLEAN | Oui | Oui/non |
| commentaire_controle | TEXT | Oui | Notes |
| decision_humaine | TEXT | Oui | Maturation / Decoupe / Declassement / Destruction |
| date_prochain_controle | DATE | Oui | Calendrier |
| personnel_id | INTEGER | Oui | Qui a contrôlé |
| created_at | DATETIME | Non | Auto |

---

### G. Table `commande_receptions_mapping` (lien commande ↔ réception)

Optionnel mais très utile : tracer quand une réception correspond à une commande.

```sql
CREATE TABLE IF NOT EXISTS commande_receptions_mapping (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    commande_id          INTEGER NOT NULL,
    reception_id         INTEGER NOT NULL,
    date_liaison         DATETIME DEFAULT CURRENT_TIMESTAMP,
    personnel_id         INTEGER,                         -- Qui a matché
    FOREIGN KEY (commande_id)  REFERENCES commandes(id),
    FOREIGN KEY (reception_id) REFERENCES receptions(id),
    FOREIGN KEY (personnel_id) REFERENCES personnel(id),
    UNIQUE(commande_id, reception_id)
);

CREATE INDEX IF NOT EXISTS idx_mapping_commande
    ON commande_receptions_mapping(commande_id);
CREATE INDEX IF NOT EXISTS idx_mapping_reception
    ON commande_receptions_mapping(reception_id);
```

---

## 3️⃣ SCRIPT DE MIGRATION COMPLET

```sql
-- ============================================================================
-- ÉTAPE 1 — Migrations (backward-compatible)
-- ============================================================================

PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

-- ALTER TABLE fournisseurs
ALTER TABLE fournisseurs ADD COLUMN email_commercial TEXT;
ALTER TABLE fournisseurs ADD COLUMN telephone TEXT;
ALTER TABLE fournisseurs ADD COLUMN adresse TEXT;
ALTER TABLE fournisseurs ADD COLUMN conditions_paiement TEXT;
ALTER TABLE fournisseurs ADD COLUMN date_maj DATETIME DEFAULT CURRENT_TIMESTAMP;

-- ALTER TABLE reception_lignes
ALTER TABLE reception_lignes ADD COLUMN date_abattage DATE;

-- CREATE TABLE commandes
CREATE TABLE IF NOT EXISTS commandes (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id          INTEGER NOT NULL DEFAULT 1,
    fournisseur_id       INTEGER NOT NULL,
    date_commande        DATE    NOT NULL DEFAULT CURRENT_DATE,
    numero_commande      TEXT    UNIQUE,
    statut               TEXT    NOT NULL DEFAULT 'brouillon',
    montant_total_ht     REAL    DEFAULT 0.0,
    montant_total_ttc    REAL    DEFAULT 0.0,
    date_livraison_prevue DATE,
    commentaire          TEXT,
    personnel_id         INTEGER,
    date_envoi_mail      DATETIME,
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boutique_id)  REFERENCES boutiques(id),
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id),
    FOREIGN KEY (personnel_id)   REFERENCES personnel(id)
);

CREATE INDEX IF NOT EXISTS idx_commandes_fournisseur
    ON commandes(fournisseur_id, date_commande DESC);
CREATE INDEX IF NOT EXISTS idx_commandes_statut
    ON commandes(statut, date_commande DESC);

-- CREATE TABLE commande_lignes
CREATE TABLE IF NOT EXISTS commande_lignes (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    commande_id          INTEGER NOT NULL,
    code_fournisseur     TEXT    NOT NULL,
    designation          TEXT    NOT NULL,
    prix_unitaire_ht     REAL    NOT NULL DEFAULT 0.0,
    quantite_commandee   REAL    NOT NULL,
    unite                TEXT    NOT NULL DEFAULT 'kg',
    montant_ht           REAL    DEFAULT 0.0,
    en_stock             INTEGER DEFAULT 0,
    dlc_prevue           DATE,
    commentaire_ligne    TEXT,
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (commande_id) REFERENCES commandes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_commande_lignes_commande
    ON commande_lignes(commande_id);

-- CREATE TABLE catalogue_fournisseur
CREATE TABLE IF NOT EXISTS catalogue_fournisseur (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    fournisseur_id       INTEGER NOT NULL,
    produit_id           INTEGER,
    code_article         TEXT    NOT NULL,
    designation          TEXT    NOT NULL,
    prix_achat_ht        REAL    NOT NULL,
    prix_achat_ttc       REAL,
    tva_percent          REAL    DEFAULT 5.5,
    conditionnement      TEXT,
    dlc_type             TEXT,
    dlc_jours            INTEGER,
    stock_dispo          INTEGER DEFAULT 0,
    date_maj             DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id),
    FOREIGN KEY (produit_id)     REFERENCES produits(id),
    UNIQUE(fournisseur_id, code_article)
);

CREATE INDEX IF NOT EXISTS idx_catalogue_fournisseur_code
    ON catalogue_fournisseur(fournisseur_id, code_article);
CREATE INDEX IF NOT EXISTS idx_catalogue_fournisseur_produit
    ON catalogue_fournisseur(fournisseur_id, produit_id);

-- CREATE TABLE maturation_carcasses
CREATE TABLE IF NOT EXISTS maturation_carcasses (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    reception_ligne_id   INTEGER NOT NULL,
    date_abattage        DATE    NOT NULL,
    numero_lot           TEXT    NOT NULL,
    age_jours            INTEGER,
    date_dernier_controle DATE,
    etat_controle        TEXT,
    aspect               TEXT,
    odeur                TEXT,
    dessiccation         TEXT,
    poissage             TEXT,
    parage_effectue      BOOLEAN DEFAULT 0,
    commentaire_controle TEXT,
    decision_humaine     TEXT,
    date_prochain_controle DATE,
    personnel_id         INTEGER,
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reception_ligne_id) REFERENCES reception_lignes(id),
    FOREIGN KEY (personnel_id)       REFERENCES personnel(id)
);

CREATE INDEX IF NOT EXISTS idx_maturation_reception_ligne
    ON maturation_carcasses(reception_ligne_id);
CREATE INDEX IF NOT EXISTS idx_maturation_date_controle
    ON maturation_carcasses(date_dernier_controle);

-- CREATE TABLE commande_receptions_mapping
CREATE TABLE IF NOT EXISTS commande_receptions_mapping (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    commande_id          INTEGER NOT NULL,
    reception_id         INTEGER NOT NULL,
    date_liaison         DATETIME DEFAULT CURRENT_TIMESTAMP,
    personnel_id         INTEGER,
    FOREIGN KEY (commande_id)  REFERENCES commandes(id),
    FOREIGN KEY (reception_id) REFERENCES receptions(id),
    FOREIGN KEY (personnel_id) REFERENCES personnel(id),
    UNIQUE(commande_id, reception_id)
);

CREATE INDEX IF NOT EXISTS idx_mapping_commande
    ON commande_receptions_mapping(commande_id);
CREATE INDEX IF NOT EXISTS idx_mapping_reception
    ON commande_receptions_mapping(reception_id);

COMMIT;
```

---

## ✅ VÉRIFICATION POST-MIGRATION

```sql
-- Vérifier ALTER TABLE
PRAGMA table_info(fournisseurs);
PRAGMA table_info(reception_lignes);

-- Vérifier CREATE TABLE
SELECT name FROM sqlite_master WHERE type='table' AND name IN (
    'commandes',
    'commande_lignes',
    'catalogue_fournisseur',
    'maturation_carcasses',
    'commande_receptions_mapping'
);

-- Vérifier index
SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%commande%';
```

---

## 🚀 IMPACT SUR L'APP EXISTANTE

### Modules **AFFECTÉS** ✅ (pas de casse, juste nouvelles colonnes nullable)
- **Réception** : `reception_lignes` a une colonne `date_abattage` → aucune validation existante, pas de régression
- **Stock** : Lit `reception_lignes` → nouvelles colonnes ignorées ✅
- **Fabrication** : Lit `reception_lignes` → nouvelles colonnes ignorées ✅
- **Fournisseurs** : GET/POST/PUT existants → nouvelles colonnes optionnelles ✅

### Modules **INCHANGÉS** 🔒
- Cuisson, refroidissement, ouvertures, nettoyage, nuisibles, étalonnage, DLC, tâches : Aucun impact

---

## 📦 Comment appliquer cette migration

### Option 1 : Script Python (recommandé pour Raspberry)
```python
import aiosqlite
import asyncio

async def migrate():
    async with aiosqlite.connect("/data/haccp.db") as db:
        await db.executescript("""
            -- SQL du script complet ci-dessus
        """)
        await db.commit()
        print("Migration Étape 1 appliquée ✅")

asyncio.run(migrate())
```

### Option 2 : SQLite CLI
```bash
sqlite3 /data/haccp.db < etape1_migration.sql
```

### Option 3 : Ajouter à database.py (init_db)
Ajouter les CREATE TABLE à la liste `migrations` existante dans init_db().

---

## 📝 Notes importantes

1. **Idempotence** : Tous les `CREATE TABLE IF NOT EXISTS` sont sûrs (peuvent être rejoués)
2. **Rollback** : Si problème, supprimer les 5 tables nouvelles + restaurer fournisseurs/reception_lignes depuis backup
3. **Tests** : Vérifier que `GET /api/fournisseurs` et `GET /api/reception/{id}` retournent les nouvelles colonnes sans erreur
4. **Déploiement Raspberry** : Stop systemd, apply script, restart

# CONTEXT MASTER — HACCP Monitor
## Document de référence absolu — Handover IA

> **Version** : 1.0 — généré le 2026-04-12  
> **Auteur** : Architecte Logiciel (Claude Sonnet 4.6 / session de handover)  
> **But** : Permettre à toute IA future de reprendre le développement sans rien casser,  
> avec une compréhension totale des règles métier, des contraintes techniques et des choix d'architecture.

---

## TABLE DES MATIÈRES

1. [Vision Globale](#1-vision-globale)
2. [Infrastructure Matérielle](#2-infrastructure-matérielle)
3. [Stack Technique](#3-stack-technique)
4. [Architecture des Fichiers](#4-architecture-des-fichiers)
5. [Schéma de la Base de Données](#5-schéma-de-la-base-de-données)
6. [Logique Métier & Workflows](#6-logique-métier--workflows)
7. [Mécanique d'Impression — Le Ticket Fantôme](#7-mécanique-dimpression--le-ticket-fantôme)
8. [UX & Charte Graphique](#8-ux--charte-graphique)
9. [API — Endpoints Principaux](#9-api--endpoints-principaux)
10. [Tests & Qualité](#10-tests--qualité)
11. [Infrastructure & Déploiement](#11-infrastructure--déploiement)
12. [État du Projet (Phase par Phase)](#12-état-du-projet-phase-par-phase)
13. [DIRECTIVES STRICTES POUR L'IA — RÈGLES D'OR](#13-directives-strictes-pour-lia--règles-dor)

---

## 1. Vision Globale

**HACCP Monitor** est une application web de gestion de la traçabilité alimentaire conçue spécifiquement pour la boucherie **Mets Carnés** (enseigne "Au Comptoir des Lilas").

### Objectif principal

Digitaliser l'ensemble du plan de maîtrise sanitaire (PMS) d'une boucherie artisanale afin de :
- Automatiser la surveillance des températures des enceintes réfrigérées (Phase 1)
- Assurer la traçabilité complète des produits reçus, transformés et vendus (Phase 2 & 3)
- Générer automatiquement les étiquettes DLC réglementaires (Phase 2 & 3)
- Conserver l'historique HACCP (réceptions, tâches, non-conformités, fabrications) en cas de contrôle vétérinaire ou DDPP

### Public cible (utilisateurs réels)

- **Bouchers** (Éric, Ulysse) : tablette Android murale en laboratoire, gants souvent portés → interface tactile avec grands boutons
- **Gérant** : consultation des alertes et rapports depuis PC
- **DDPP / Services vétérinaires** : inspection des enregistrements numériques

### Entité commerciale

- **Boutique principale** : Au Comptoir des Lilas, 122 rue de Paris, Les Lilas, 93260 (`boutique_id = 1`)
- **Groupe** : Mets Carnés Holding
- **Référence interne** : Tous les lots fabriqués portent le préfixe `MC-`

---

## 2. Infrastructure Matérielle

| Composant | Détail |
|-----------|--------|
| **Serveur backend** | Raspberry Pi ZERO2 W W, 4x 1 GHz, 512 MB RAM, WLAN, BT — IP locale `192.168.1.83`, port `8081` |
| **Interface utilisateur** | Tablette Android murale en mode kiosque (laboratoire) |
| **Sondes température** | Zigbee SNZB-02D × 4 (chambre_froide_1, chambre_froide_2, vitrine, laboratoire) |
| **Broker MQTT** | Mosquitto (local, port 1883) via Zigbee2MQTT |
| **Imprimante étiquettes** | Brother QL-820NWB — USB connecté au Pi — rouleau **DK-22251 (62mm continu)** |
| **Base de données** | SQLite — fichier `haccp.db` à la racine du projet |
| **Stockage photos** | `data/photos/bons_livraison/`, `data/photos/ouvertures/`, `data/photos/signatures/` |

### Accès SSH au Pi

```bash
ssh campiglia@192.168.1.83
```

### Services systemd sur le Pi

```bash
sudo systemctl status haccp-backend zigbee2mqtt mosquitto --no-pager
sudo systemctl restart haccp-backend
sudo journalctl -u haccp-backend -f --no-pager
```

---

## 3. Stack Technique

### Backend

| Élément | Choix | Fichier clé |
|---------|-------|-------------|
| Framework API | **FastAPI** 0.115.0 | `src/main.py` |
| Serveur ASGI | **Uvicorn** 0.30.0 (standard) | démarré par systemd |
| Base de données | **SQLite** (mode WAL) via **aiosqlite** 0.20.0 | `src/database.py` |
| Validation données | **Pydantic** v2 (intégré à FastAPI) | dans chaque `routes_*.py` |
| MQTT | **paho-mqtt** 2.1.0 | `src/mqtt_subscriber.py` |
| Templates HTML | **Jinja2** 3.1.4 | `src/templates/` |
| Génération PDF | **WeasyPrint** 62.3 | `src/report_generator.py` |
| Traitement images | **Pillow** (PIL) | `src/api/routes_reception.py` |
| Python | **3.11** | |

### Frontend

| Élément | Choix | Raison |
|---------|-------|--------|
| JavaScript | **Vanilla JS** (ES2020, modules non-bundlés) | Pas de Node.js sur Pi, simplicité |
| CSS | **Custom tokens** + utilitaires — **PAS de Tailwind CDN runtime** | Performance, contrôle total |
| Graphiques | **Chart.js** (via CDN) | Uniquement pour le dashboard température Phase 1 |
| Fonts | Système | Pas de Google Fonts (mode offline requis) |
| PWA | `manifest.json` + `sw.js` (Service Worker) | Installation sur tablette, mode hors-ligne |

### Règle d'or frontend

> **JAMAIS de framework JS lourd** (React, Vue, Angular, Svelte…). L'app doit fonctionner offline, sur un Pi, sans build step. Chaque page HTML est autonome et charge ses scripts directement.

### Conventions de code backend

- Toutes les fonctions de base de données sont `async` (aiosqlite)
- Les fonctions CRUD sont dans `src/database.py` — les routes FastAPI ne font **que** appeler ces fonctions
- Les modèles Pydantic sont définis **dans** le fichier `routes_*.py` correspondant (pas de fichier `models.py` central)
- Pas d'ORM (SQLAlchemy, Tortoise…) — SQL brut via `aiosqlite`

---

## 4. Architecture des Fichiers

```
haccp-monitor/
├── CONTEXT.md                          ← contexte projet (raccourci, voir CONTEXT_MASTER.md)
├── CONTEXT_MASTER.md                   ← CE FICHIER — document de référence absolu
├── haccp.db                            ← base SQLite de production (NE JAMAIS SUPPRIMER)
├── haccp.db-shm / haccp.db-wal         ← fichiers WAL SQLite (normaux)
├── requirements.txt
├── pytest.ini
├── .env.example                        ← template variables d'environnement
├── .gitignore                          ← haccp.db exclu du git
│
├── src/
│   ├── main.py                         ← entrée FastAPI (lifespan, routes, static)
│   ├── database.py                     ← SCHÉMA SQL + TOUTES les fonctions CRUD
│   ├── mqtt_subscriber.py              ← thread MQTT → stockage relevés + alertes
│   ├── alert_manager.py                ← SMTP email + SMS OVH
│   ├── report_generator.py             ← Jinja2 + WeasyPrint → PDF
│   ├── api/
│   │   ├── routes_boutiques.py         ← GET /api/boutiques
│   │   ├── routes_enceintes.py         ← GET/POST/PUT/DELETE /api/enceintes
│   │   ├── routes_releves.py           ← GET /api/enceintes/{id}/releves
│   │   ├── routes_alertes.py           ← GET /api/alertes/en-cours
│   │   ├── routes_rapports.py          ← POST /api/rapports/generer
│   │   ├── routes_etiquettes.py        ← /api/produits, /api/etiquettes
│   │   ├── routes_reception.py         ← /api/receptions, /api/fournisseurs
│   │   ├── routes_taches.py            ← /api/taches
│   │   ├── routes_admin.py             ← /api/admin/personnel, pieges, plan_nettoyage
│   │   ├── routes_ouvertures.py        ← /api/ouvertures
│   │   ├── routes_incidents.py         ← /api/fiches-incident (PCR01)
│   │   └── routes_fabrication.py       ← /api/recettes, /api/fabrications
│   └── printing/
│       └── brother_ql_driver.py        ← driver imprimante (stub actuel)
│
├── static/                             ← servi par FastAPI en tant que fichiers statiques
│   ├── manifest.json                   ← PWA manifest
│   ├── index.html                      ← dashboard Phase 1 (températures)
│   ├── hub.html                        ← accueil Phase 2 (tuiles de navigation)
│   ├── taches.html                     ← module Tâches HACCP
│   ├── etiquettes.html                 ← module Fabrication + impression étiquettes
│   ├── reception.html                  ← création fiche réception
│   ├── reception-detail.html           ← ajout lignes produit à une réception
│   ├── ouverture.html                  ← enregistrement ouverture de produit
│   ├── ouvertures-historique.html      ← historique ouvertures
│   ├── historique.html                 ← historique unifié (ouvertures, réceptions, fabrications, nettoyage)
│   ├── incidents.html                  ← fiches incident PCR01 (liste)
│   ├── pcr01.html                      ← création fiche incident
│   ├── pcr01-detail.html               ← détail fiche incident
│   ├── admin.html                      ← panneau admin général
│   ├── admin-recettes.html             ← gestion des recettes
│   ├── css/
│   │   ├── reset.css
│   │   ├── tokens.css                  ← variables CSS (couleurs, espacements, typographie)
│   │   ├── base.css
│   │   ├── components.css              ← boutons, modales, spinners, tableaux
│   │   ├── layouts.css
│   │   └── pages/                      ← CSS spécifique par page
│   └── js/
│       ├── core/
│       │   ├── api.js                  ← client HTTP global (fetch wrapper)
│       │   ├── utils.js                ← timer inactivité, helpers
│       │   └── sw-register.js          ← enregistrement Service Worker PWA
│       ├── dashboard.js
│       ├── hub.js
│       ├── taches.js
│       ├── etiquettes.js               ← wizard fabrication (4 étapes)
│       ├── reception.js
│       ├── reception-detail.js
│       ├── ouverture.js
│       ├── ouvertures-historique.js
│       ├── historique.js
│       ├── incidents.js
│       ├── pcr01.js
│       ├── pcr01-detail.js
│       ├── admin-recettes.js
│       ├── charts.js
│       └── sw.js                       ← Service Worker (cache offline)
│
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_api_fabrication.py
│   ├── test_alerts.py
│   ├── test_database.py
│   ├── test_db_fabrication.py
│   ├── test_etiquette_reprise.py
│   ├── test_etiquettes.py
│   ├── test_incidents.py
│   ├── test_ouvertures.py
│   ├── test_reception.py
│   ├── test_reception_v2.py
│   └── test_taches.py
│
├── scripts/
│   ├── fix_produit_id_nullable.py      ← migration ad hoc (déjà exécutée)
│   ├── import_matieres_premieres.py    ← import Excel → BDD
│   ├── seed_data.py
│   └── simulate_sensors.py            ← simulation MQTT pour dev
│
└── data/
    ├── extraction_matiere_premiere.xlsx  ← 365 produits à importer
    ├── haccp.db                          ← copie de backup
    ├── photos/
    │   ├── bons_livraison/              ← photos BL (compression 1280px JPEG 80%)
    │   ├── ouvertures/
    │   └── signatures/
    └── rapports/                        ← PDF générés
```

---

## 5. Schéma de la Base de Données

> **CRITIQUE** : La base est gérée intégralement dans `src/database.py` via `SCHEMA_SQL` (chaîne Python).  
> Ne jamais modifier le schéma sans lire la section [Règle n°1](#règle-n1--ne-jamais-migrer-la-bdd-sans-accord).

### 5.1 PRAGMA globaux

```sql
PRAGMA journal_mode = WAL;    -- Write-Ahead Logging (meilleure concurrence)
PRAGMA foreign_keys = ON;     -- Clés étrangères activées
```

### 5.2 Phase 1 — Surveillance températures

#### `boutiques`
```sql
id, nom, adresse, siret, created_at
```
- **1 seule boutique en prod** : `id=1`, "Au Comptoir des Lilas"

#### `enceintes`
```sql
id, boutique_id, nom, type, sonde_zigbee_id,
seuil_temp_min, seuil_temp_max, seuil_hum_max,
delai_alerte_minutes DEFAULT 5, actif, created_at
-- UNIQUE(boutique_id, nom)
```
- 4 enceintes de prod (ids: 1, 2, 7, 8 — les ids peuvent varier selon les migrations)
- `type` : `chambre_froide`, `vitrine`, `laboratoire`, `congelateur`

#### `releves`
```sql
id, enceinte_id, temperature, humidite, batterie,
qualite_signal, horodatage DEFAULT CURRENT_TIMESTAMP
-- INDEX sur (enceinte_id, horodatage)
```
- Table INSERT-only (pas de mise à jour, pas de suppression en dehors de la purge)
- Volume : plusieurs milliers d'enregistrements par jour

#### `alertes`
```sql
id, enceinte_id, type, valeur, seuil,
debut, fin, notifie DEFAULT 0, created_at
```
- `type` : `temperature_haute`, `temperature_basse`, `batterie_faible`, `perte_signal`
- `fin = NULL` → alerte toujours active
- `notifie = 0` → notification pas encore envoyée

#### `destinataires`
```sql
id, nom, email, telephone, actif DEFAULT 1
```

#### `rapports`
```sql
id, boutique_id, type, date_debut, date_fin,
conforme, fichier_path, sha256, created_at
```

---

### 5.3 Phase 2 — Traçabilité métier

#### `produits`
```sql
id, boutique_id DEFAULT 1, nom, code_unique TEXT UNIQUE,
espece, etape, coupe_niveau, conditionnement DEFAULT 'SOUS_VIDE',
categorie NOT NULL DEFAULT 'matiere_premiere',
dlc_jours NOT NULL DEFAULT 0,
temperature_conservation NOT NULL DEFAULT '0°C à +4°C',
format_etiquette DEFAULT 'standard_60x40',
type_produit NOT NULL DEFAULT 'brut',
actif DEFAULT 1, created_at
```

**Champs importants :**
- `code_unique` : ex. "VBR06" — index UNIQUE, peut être NULL
- `espece` : Bœuf / Veau / Porc / Agneau / Gibier / Volaille / Exotique / Cheval
- `etape` : 1=Coupe primaire, 2=Coupe de gros, 3=Coupe secondaire, 4=PAV
- `categorie` : `matiere_premiere`, `pav`, `viande_hachee`, `preparation_crue`, `charcuterie_tranchee`, `plat_cuisine`, `produit_deconge`, `produit_congele`
- `dlc_jours = 0` : matière première (DLC vient du fournisseur, saisie manuelle à la réception)
- `type_produit` : `brut` (matière première) ou `fini` (produit transformé)

#### `regles_dlc`
```sql
id, boutique_id, categorie, dlc_jours, note
-- UNIQUE(boutique_id, categorie)
```

**Valeurs de seed par défaut :**
| Catégorie | DLC (jours) | Note |
|-----------|-------------|------|
| `viande_hachee` | **1** | Viande hachée fraîche |
| `preparation_crue` | **2** | Merguez, saucisses… |
| `viande_pieces` | **3** | Pièces entières |
| `plat_cuisine` | **3** | Plats cuisinés maison |
| `produit_deconge` | **3** | ⚠️ Réglementaire — NON MODIFIABLE |
| `charcuterie_tranchee` | **5** | Tranchée à la coupe |
| `produit_congele` | **180** | Congélation maison |

#### `etiquettes_generees`
```sql
id, boutique_id, produit_id, produit_nom NOT NULL,
type_date NOT NULL, date_etiquette NOT NULL, dlc NOT NULL,
temperature_conservation, operateur NOT NULL,
numero_lot NOT NULL, lot_type NOT NULL,
info_complementaire, mode_impression DEFAULT 'manuel',
imprime_at DEFAULT CURRENT_TIMESTAMP
-- FK: boutique_id, produit_id (nullable)
-- INDEX sur (boutique_id, imprime_at) et (boutique_id, dlc)
```

**⚠️ LIMITE ACTUELLE** : Cette table enregistre les étiquettes générées via l'ancien module étiquettes simple. Depuis la refonte Phase 3 (module Fabrication), les fabrications sont enregistrées dans `fabrications` + `fabrication_lots`. Les deux coexistent.

#### `fournisseurs`
```sql
id, boutique_id, nom NOT NULL, actif DEFAULT 1
```

#### `receptions`
```sql
id, personnel_id NOT NULL,
date_reception DEFAULT CURRENT_DATE, heure_reception NOT NULL,
temperature_camion, proprete_camion DEFAULT 'satisfaisant',
camion_conforme DEFAULT 1,
fournisseur_principal_id (nullable),
photo_bl_filename, commentaire,
conformite_globale DEFAULT 'conforme',
livraison_refusee DEFAULT 0, information_ddpp DEFAULT 0,
commentaire_nc, created_at
-- INDEX sur date_reception
```

#### `reception_lignes`
```sql
id, reception_id NOT NULL, produit_id NOT NULL,
fournisseur_id (nullable), numero_lot, dlc, dluo,
origine DEFAULT 'France', poids_kg,
temperature_reception, temperature_conforme,
couleur_conforme DEFAULT 1, couleur_observation,
consistance_conforme DEFAULT 1, consistance_observation,
exsudat_conforme DEFAULT 1, exsudat_observation,
odeur_conforme DEFAULT 1, odeur_observation,
ph_valeur, ph_conforme,
conforme DEFAULT 1, created_at
```

#### `fiches_incident` (PCR01)
```sql
id, reception_id NOT NULL,
reception_ligne_id (NULLABLE — Optional[int]),
date_incident, heure_incident NOT NULL,
fournisseur_id (NULLABLE), produit_id (NULLABLE),
numero_lot, nature_probleme NOT NULL,
description, action_immediate NOT NULL,
livreur_present DEFAULT 0, signature_livreur_filename,
etiquette_reprise_imprimee DEFAULT 0,
action_corrective, suivi,
statut DEFAULT 'ouverte',
cloturee_par, cloturee_le, created_at
```

**⚠️ LIMITES CONNUES :**
- `reception_ligne_id` est `Optional[int]` (nullable) — une fiche incident peut exister sans ligne produit associée
- `fournisseur_id` et `produit_id` sont nullable (migration déjà appliquée via `fix_produit_id_nullable.py`)

#### `non_conformites_fournisseur`
```sql
id, boutique_id, reception_id (nullable), reception_ligne_id (nullable),
operateur, date_livraison, fournisseur_nom, produits,
date_fabrication, dlc, nombre_barquettes, nature_nc, commentaires,
refuse_livraison DEFAULT 0, nc_apres_livraison DEFAULT 0,
info_ddpp DEFAULT 0, created_at
```

#### `personnel`
```sql
id, boutique_id, prenom NOT NULL, actif DEFAULT 1
-- UNIQUE(boutique_id, prenom)
```
- Seed : Éric (id=1), Ulysse (id=2)

#### `tache_types`
```sql
id, boutique_id, code NOT NULL, libelle NOT NULL,
frequence NOT NULL, heure_cible,
photo_requise DEFAULT 0, actif DEFAULT 1
-- UNIQUE(boutique_id, code)
```
- `frequence` : `quotidien`, `hebdomadaire`, `mensuel`, `ponctuel`, `evenementiel`, `exceptionnel`

#### `tache_validations`
```sql
id, boutique_id, tache_type_id, operateur NOT NULL,
date_tache DATE NOT NULL, heure_validation,
conforme, photo_path, commentaire, donnees_specifiques
-- INDEX sur (boutique_id, date_tache) et (tache_type_id, date_tache)
```

#### `pieges`
```sql
id, boutique_id, type, identifiant, localisation, actif
-- UNIQUE(boutique_id, type, identifiant)
```
- Seed : P1 (rongeur, entrée labo), P2 (rongeur, fond labo), P3 (oiseau, entrée boutique)

#### `plan_nettoyage`
```sql
id, boutique_id, local, surface_equipement, frequence, actif
-- UNIQUE(boutique_id, local, surface_equipement, frequence)
```

#### `ouvertures`
```sql
id, produit_id NOT NULL, personnel_id NOT NULL,
photo_filename NOT NULL, timestamp DEFAULT CURRENT_TIMESTAMP,
source DEFAULT 'catalogue', reception_ligne_id (nullable)
-- INDEX sur produit_id et timestamp
```

---

### 5.4 Phase 3 — Module Fabrication

#### `recettes`
```sql
id, nom NOT NULL, produit_fini_id NOT NULL,
dlc_jours NOT NULL, instructions, created_at
-- FK: produit_fini_id → produits(id)
```

**Convention instructions** : Le champ `instructions` peut contenir une ligne au format  
`Base pour X kg` (ou `X pièces`, `X L`) — ce texte est parsé par le JS pour le calculateur de production.

#### `recette_ingredients`
```sql
id, recette_id NOT NULL, produit_id NOT NULL,
quantite, unite
-- ON DELETE CASCADE depuis recettes
```

#### `fabrications`
```sql
id, recette_id NOT NULL, date TEXT NOT NULL,
lot_interne TEXT NOT NULL UNIQUE,
personnel_id NOT NULL, info_complementaire, created_at
-- INDEX sur date et lot_interne
```

**⚠️ LIMITE CRITIQUE** : La table `fabrications` **ne contient PAS encore** les champs suivants :
- `poids_fabrique` — le poids réellement produit (disponible côté client dans `state.productionCiblee` mais pas persisté en base)
- `dlc_finale` — la DLC calculée par la règle du maillon faible (transmise à l'API dans le payload mais la colonne n'existe peut-être pas encore en base selon l'état de la migration)

**Avant d'ajouter ces colonnes**, vérifier si elles existent avec :
```python
cur = await db.execute("PRAGMA table_info(fabrications)")
cols = {row[1] for row in await cur.fetchall()}
```

#### `fabrication_lots`
```sql
id, fabrication_id NOT NULL, recette_ingredient_id NOT NULL,
reception_ligne_id NOT NULL
-- ON DELETE CASCADE depuis fabrications
```
- Assure la traçabilité lot-à-lot : pour chaque ingrédient d'une fabrication, on sait exactement quelle ligne de réception a été utilisée.

### 5.5 Format du numéro de lot interne

```
MC-YYYYMMDD-XXXX
```
- `MC` = Mets Carnés (préfixe fixe)
- `YYYYMMDD` = date de fabrication
- `XXXX` = numéro séquentiel du jour (auto-incrémenté, zéro-paddé sur 4 chiffres)

Exemple : `MC-20260412-0001`, `MC-20260412-0002`…

La génération est faite dans `database.py` via la fonction `generer_lot_interne()`.

---

## 6. Logique Métier & Workflows

### 6.1 Module Réception (BL + Contrôle qualité)

**Fichiers clés** : `src/api/routes_reception.py`, `static/reception.html`, `static/reception-detail.html`

#### Workflow en 3 étapes

**Étape 1 — Création de la fiche de réception** (`POST /api/receptions`)
- Saisie multipart (FormData) car inclut une photo du bon de livraison
- Champs obligatoires : `personnel_id`, `heure_reception`
- Champs de contrôle camion : `temperature_camion`, `proprete_camion` (`satisfaisant`/`insuffisant`/`mauvais`), `camion_conforme`
- Photo BL : compressée côté serveur (max 1280px, JPEG 80%) et stockée dans `data/photos/bons_livraison/`
- La réception est créée avec `conformite_globale = 'conforme'` par défaut

**Étape 2 — Ajout des lignes produit** (`POST /api/receptions/{id}/lignes`)
- Une ligne par produit livré
- Pour chaque ligne, contrôle visuel HACCP obligatoire :

| Critère | Type | Valeurs possibles |
|---------|------|-------------------|
| Couleur | Boolean + texte libre | `couleur_conforme`, `couleur_observation` |
| Consistance | Boolean + texte libre | `consistance_conforme`, `consistance_observation` |
| Exsudat | Boolean + texte libre | `exsudat_conforme`, `exsudat_observation` |
| Odeur | Boolean + texte libre | `odeur_conforme`, `odeur_observation` |
| pH | Float + Boolean | `ph_valeur`, `ph_conforme` |
| Température à cœur | Float + Boolean | `temperature_reception`, `temperature_conforme` |

- **Référentiel aide visuel** par espèce : `GET /api/receptions/textes-aide-visuel`  
  Retourne les valeurs normales et anomalies pour : Bœuf, Veau, Porc, Agneau, Volaille, Gibier, Cheval

**Étape 3 — Clôture de la réception** (`PUT /api/receptions/{id}/cloturer`)
- Verdict global : `conforme` ou `non_conforme`
- Si non-conforme : `livraison_refusee` (boolean), `information_ddpp` (boolean), `commentaire_nc`
- Une non-conformité peut déclencher la création d'une fiche incident (PCR01)

#### Gestion des Non-Conformités (PCR01)

- **Fiche incident** = PCR01 (Procédure Corrective et Réclamation n°01)
- Créée depuis la réception (`POST /api/fiches-incident`)
- Contient : nature du problème, action immédiate, présence du livreur, signature
- Peut déclencher l'impression d'une **étiquette de reprise** (`POST /api/impression/etiquette-reprise`)
- Suivi et clôture ultérieure via `PUT /api/fiches-incident/{id}`

---

### 6.2 Module Fabrication — Le Wizard en 4 Étapes

**Fichiers clés** : `static/etiquettes.html`, `static/js/etiquettes.js`, `src/api/routes_fabrication.py`

Le wizard est entièrement côté client (SPA single-page sans rechargement). L'état global est maintenu dans l'objet `state` (JavaScript).

#### ÉTAPE 1 : Choix de la recette

- Affiche une grille de tuiles (toutes les recettes depuis `GET /api/recettes`)
- Filtre texte en temps réel
- Chaque tuile affiche : emoji 🍖, nom de la recette, DLC théorique (J+X)
- Sélection → chargement des ingrédients (`GET /api/recettes/{id}`) + passage étape 2

#### ÉTAPE 2 : Calculateur de production

- Le champ `instructions` de la recette peut contenir `"Base pour X kg"` (regex : `/base pour (\d+(?:[.,]\d+)?)\s*(kg|g|pièces?|pc|l)?/i`)
- Si une base est détectée, l'utilisateur saisit la **production ciblée du jour** (ex: 15 kg)
- Les quantités de chaque ingrédient sont recalculées proportionnellement :
  ```
  quantite_calculee = (quantite_base / rendement_base) × production_ciblee
  ```
- Si aucune base trouvée : les quantités de la recette s'affichent telles quelles (fixes)
- La production ciblée est **obligatoire** si une base existe (bloquant)

#### ÉTAPE 3 : Traçabilité & Lots (FIFO forcé)

- Appel `GET /api/fabrications/fifo-lots?recette_id={id}`
- Le moteur FIFO dans `database.py` sélectionne, pour chaque ingrédient, la ligne de réception avec :
  1. DLC la plus courte (nulls en dernier)
  2. À égalité : date de réception la plus ancienne
- **Affichage par ligne** :
  - ✓ Vert : lot FIFO trouvé (`lot_numero`, `dlc`)
  - ⚠️ Orange clignotant : lot manquant (aucune réception pour ce produit) → bouton "🔄 Remplacer"

#### Mécanisme de Substitution (quand un lot est manquant)

La substitution s'opère en **2 niveaux** :

**Niveau 3 (défaut)** — Stock réel + filtre sémantique intelligent :
- Charge `GET /api/produits?en_stock=true&type=brut`
- Filtre automatiquement par espèce et muscle grâce au lexique :
  - Codes viande : `VB` (Bœuf), `VX` (Veau), `PC` (Porc), `AG` (Agneau), `GI` (Gibier)
  - Extraction du mot-muscle principal (après nettoyage des mots parasites : SANS, AVEC, OS, PAD…)
- Si un produit est sélectionné : confirmation simple (⚠️ modale)

**Niveau 4 (déverrouillage manuel)** — Catalogue complet :
- Bouton "🔍 Recherche manuelle dans tout le catalogue"
- Charge `GET /api/produits?en_stock=false&type=brut` (tout le catalogue)
- Bandeau rouge d'alerte : "MODE MANUEL : Traçabilité critique"
- Confirmation avec alerte critique 🚨 (modale rouge) : "Ce produit n'est pas issu du filtrage recommandé"

**⚠️ BLOCAGE VALIDATION** : Le bouton "Confirmer les lots" est **désactivé** tant qu'il reste des lignes manquantes sans substitut. Il n'est jamais possible de passer à l'étape 4 avec un ingrédient non résolu.

#### ÉTAPE 4 : Récapitulatif & Impression

**Calcul DLC finale — Règle du maillon faible (HACCP critique)** :

```
dlc_theorique = date_du_jour + recette.dlc_jours

pour chaque ingredient dans fifoLots:
    si ingredient.lot_fifo.dlc < dlc_theorique:
        dlc_theorique = ingredient.lot_fifo.dlc
        ingredient_critique = ingredient.nom

dlc_finale = dlc_theorique  # la DLC la plus courte gagne
```

- Si la DLC est réduite par un ingrédient : un toast orange s'affiche → "⚠️ DLC réduite à JJ/MM/AAAA à cause de : [NOM_INGREDIENT]"
- La DLC finale est stockée dans `state.dlcFinale` au format `YYYY-MM-DD` (calcul en heure locale, pas UTC pour éviter le décalage)

**Soumission** (`POST /api/fabrications`) :
```json
{
  "recette_id": 1,
  "personnel_id": 2,
  "date": "2026-04-12",
  "lots": [
    {"recette_ingredient_id": 1, "reception_ligne_id": 42},
    {"recette_ingredient_id": 2, "reception_ligne_id": 17}
  ],
  "dlc_finale": "2026-04-15"
}
```
- Après succès : remplissage du gabarit d'impression + `window.print()` (délai 100ms pour le rendu DOM)
- Écran de succès avec le numéro de lot généré
- Actions post-impression : "Même recette" (reload étape 2) ou "Nouvelle fabrication" (reset total)

---

### 6.3 Module Tâches HACCP

**Fichiers clés** : `static/taches.html`, `static/js/taches.js`, `src/api/routes_taches.py`

- 13 types de tâches configurés par défaut (relevés températures, étalonnage, nettoyage, etc.)
- `GET /api/taches/today` : tâches du jour avec statut (validées / en retard / à faire)
- `GET /api/taches/en-retard` : tâches en retard (utilisé par le badge rouge dans le hub)
- Validation : `POST /api/taches/valider` avec `operateur`, `conforme`, `commentaire`, optionnellement une photo
- `donnees_specifiques` : champ JSON libre pour les données spécifiques à chaque type de tâche (ex: températures mesurées)

---

### 6.4 Module Ouvertures

- Enregistrement de l'ouverture d'un emballage (cuit, charcuterie…)
- Photo obligatoire (caméra ou fichier)
- Autocomplete produit : priorité aux réceptions récentes (`GET /api/ouvertures/suggestions`)
- Photo compressée côté serveur (identique module réception : 1280px, JPEG 80%)

---

## 7. Mécanique d'Impression — Le Ticket Fantôme

> **C'est le mécanisme le plus critique et le plus fragile à ne pas casser.**

### 7.1 Vue d'ensemble

L'impression n'utilise **pas** le driver Brother QL-820NWB directement depuis Python. Elle repose sur le `@media print` du navigateur (Chrome/Chromium sur la tablette), qui envoie la commande d'impression à l'imprimante Brother configurée comme imprimante par défaut du système Android.

### 7.2 Le Gabarit Invisible (#print-label)

Dans `static/etiquettes.html` (lignes 371–395), un div `<div id="print-label">` existe dans le DOM mais est **invisible à l'écran** (`display: none`) :

```html
<div id="print-label" style="background: white; color: black; font-family: sans-serif;">
  <div>  <!-- En-tête : nom produit -->
    <h1 id="print-nom">NOM PRODUIT</h1>
    <div id="print-poids">-- kg fabriqués</div>
  </div>
  <div>  <!-- DLC encadrée en rouge -->
    <div>DLC :</div>
    <div id="print-dlc" style="color: red;">--/--/----</div>
  </div>
  <div id="print-lot">Lot : ---------</div>  <!-- Numéro lot -->
  <ul id="print-ingredients">...</ul>         <!-- Liste ingrédients + lots -->
  <div id="print-meta">Fabriqué le --/--/----</div>  <!-- Métadonnées -->
</div>
```

### 7.3 Le CSS @media print (Ticket Fantôme)

```css
/* Déclaré dans <style> dans etiquettes.html */
#print-label { display: none; }          /* Invisible à l'écran */

@media print {
  body * { visibility: hidden; }         /* Cache TOUT le body */
  #print-label, #print-label * {
    visibility: visible;                  /* Rend UNIQUEMENT le label visible */
  }
  #print-label {
    display: block;
    position: absolute;
    left: 0; top: 0;
    width: 62mm;                          /* Format DK-22251 — 62mm ABSOLU */
    padding: 2mm;
    margin: 0;
    color: black;
    font-family: sans-serif;
    background: white;
  }
  @page { margin: 0; }                   /* Supprime les marges d'impression navigateur */
}
```

**Pourquoi 62mm ?** : Le rouleau Brother DK-22251 est un rouleau **continu** de 62mm de large. La hauteur est variable (le navigateur coupe après le contenu).

### 7.4 Remplissage et déclenchement (JS)

Après un POST `/api/fabrications` réussi, le JS remplit le gabarit puis déclenche l'impression :

```javascript
// Remplissage du gabarit
document.getElementById('print-nom').textContent = state.recetteNom;
document.getElementById('print-poids').textContent = `${state.productionCiblee} kg fabriqués`;
document.getElementById('print-dlc').textContent = dlcFormatee; // "JJ/MM/AAAA"
document.getElementById('print-lot').textContent = `Lot : ${result.lot_interne}`;
document.getElementById('print-meta').textContent = `Fabriqué le ${date} par ${operateur}`;

// Ingrédients : "0.5kg VB-COLLIER (L:MC-20260412-0001 | DLC:12/04/26)"
ulIngredients.innerHTML = ...; // <li> par ingrédient

// Déclenchement impression (délai pour rendu DOM)
setTimeout(() => window.print(), 100);
```

### 7.5 Masquage volontaire des poids dans l'historique

**Règle importante** : Dans la page d'historique des fabrications (`historique.html`), les poids ne sont **intentionnellement pas affichés**. Raison : `poids_fabrique` n'est pas encore stocké en base (voir [Limite de la table `fabrications`](#--limite-critique-)). Afficher "— kg" serait confusant pour l'utilisateur. Il ne faut pas exposer cette donnée manquante.

### 7.6 Étiquette de reprise (PCR01)

Imprimée depuis `POST /api/impression/etiquette-reprise` quand une livraison est refusée. Contient : mention "REPRISE", nom produit, numéro lot, date incident. Suit le même mécanisme `@media print`.

---

## 8. UX & Charte Graphique

### 8.1 Règles UX Non Négociables

| Règle | Détail |
|-------|--------|
| Navigation | Hub central (Option B) — pas d'onglets permanents |
| Profondeur max | **3 taps** pour toute action |
| Boutons | Minimum **64px** de hauteur, texte minimum **18px** |
| Inactivité | Retour hub automatique après **5 minutes** (`setTimeout 5 * 60 * 1000 → /hub.html`) |
| Clavier numérique | `inputmode="decimal"` ou `inputmode="numeric"` sur tous les champs numériques |
| Confirmation | Modale personnalisée (jamais `window.confirm()` → non fonctionnel sur certains navigateurs kiosque) |
| Traçabilité | Sélecteur prénom obligatoire avant toute action traçable |

### 8.2 Charte Graphique Mets Carnés

Définie dans `static/css/tokens.css` :

| Rôle | Variable CSS | Valeur Hex |
|------|-------------|------------|
| Fond principal | `--couleur-fond` | `#F5ECD7` (Ivoire) |
| Texte principal | `--couleur-texte` | `#3D2008` (Noyer foncé) |
| Accent principal | `--couleur-accent` | `#6B3A1F` (Brun moyen) |
| Secondaire | `--couleur-secondaire` | `#D4A574` (Crème) |
| Statut OK | `--couleur-ok` | `#2D7D46` (Vert) |
| Statut attention | `--couleur-attention` | `#E8913A` (Orange) |
| Statut alerte | `--couleur-alerte` | `#C93030` (Rouge) |

### 8.3 Composants UI Existants

Définis dans `static/css/components.css` :
- Boutons : `.btn-primary`, `.btn-secondary`, `.btn-danger` — hauteur 64px min
- Modales : `.modal-overlay`, `.modal` — overlay 55% opacité noire
- Spinners : `.spinner`
- Tables : `.table-responsive`, `.table`
- Cards : `.card`, `.card-header`

**Ne jamais recréer ces composants dans un CSS de page** — toujours réutiliser les classes existantes.

---

## 9. API — Endpoints Principaux

### Phase 1 — Températures

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/boutiques/1/dashboard` | Statut temps réel toutes enceintes |
| GET | `/api/enceintes` | Liste des enceintes |
| GET | `/api/enceintes/{id}/releves` | Historique températures |
| GET | `/api/alertes/en-cours` | Alertes actives |
| POST | `/api/rapports/generer` | Générer rapport PDF |

### Phase 2 — Traçabilité

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/produits` | Catalogue (`?type=brut\|fini`, `?en_stock=true`) |
| GET | `/api/regles-dlc` | Règles DLC par catégorie |
| POST | `/api/etiquettes/generer` | Générer + imprimer étiquette |
| GET | `/api/etiquettes/alertes-dlc` | Produits DLC ≤ 2 jours |
| GET | `/api/fournisseurs` | Liste fournisseurs |
| POST | `/api/receptions` | Créer réception (multipart) |
| POST | `/api/receptions/{id}/lignes` | Ajouter ligne produit |
| PUT | `/api/receptions/{id}/cloturer` | Clôturer réception |
| GET | `/api/receptions` | Historique réceptions |
| GET | `/api/receptions/textes-aide-visuel` | Référentiel contrôle visuel |
| GET | `/api/taches/today` | Tâches du jour |
| GET | `/api/taches/en-retard` | Tâches en retard |
| POST | `/api/taches/valider` | Valider une tâche |
| POST | `/api/fiches-incident` | Créer fiche incident (PCR01) |
| PUT | `/api/fiches-incident/{id}` | Mettre à jour statut fiche |
| POST | `/api/ouvertures` | Enregistrer ouverture produit |
| GET | `/api/admin/personnel` | Liste du personnel |

### Phase 3 — Fabrication

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/recettes` | Liste des recettes |
| POST | `/api/recettes` | Créer recette + ingrédients |
| GET | `/api/recettes/{id}` | Détail recette + ingrédients |
| GET | `/api/fabrications/fifo-lots?recette_id={id}` | Suggestions FIFO |
| GET | `/api/fabrications/produit-fifo/{produit_id}` | Meilleur lot FIFO unitaire |
| POST | `/api/fabrications` | Enregistrer fabrication (201) |
| GET | `/api/fabrications` | Historique fabrications |

---

## 10. Tests & Qualité

### Configuration pytest

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
testpaths = tests
```

### Lancer les tests

```bash
cd ~/haccp-monitor
python -m pytest tests/ -v
```

### Suites de tests existantes

| Fichier | Module testé |
|---------|-------------|
| `test_api.py` | Routes générales Phase 1 |
| `test_api_fabrication.py` | Routes fabrication Phase 3 |
| `test_alerts.py` | Logique alertes |
| `test_database.py` | CRUD base de données |
| `test_db_fabrication.py` | CRUD fabrication |
| `test_etiquette_reprise.py` | Étiquette PCR01 |
| `test_etiquettes.py` | Module étiquettes/DLC |
| `test_incidents.py` | Fiches incident |
| `test_ouvertures.py` | Module ouvertures |
| `test_reception.py` | Module réception v1 |
| `test_reception_v2.py` | Module réception v2 |
| `test_taches.py` | Module tâches HACCP |

**État actuel** : 105/105 tests passent (Phase 2 backend).

### Règle impérative

> **Avant toute modification de `database.py` ou d'un modèle Pydantic**, lancer les tests pour établir la baseline. Après modification, tous les tests doivent repasser.

---

## 11. Infrastructure & Déploiement

### Variables d'environnement (.env)

```bash
# MQTT
MQTT_BROKER=localhost
MQTT_PORT=1883
DELAI_PERTE_SIGNAL_S=900    # 15 minutes avant alerte perte signal

# Email SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=haccp@mondomaine.fr
SMTP_PASSWORD=...
SMTP_FROM=haccp@mondomaine.fr

# SMS OVH (optionnel)
OVH_APP_KEY=...
OVH_SMS_SENDER=HACCP
```

### Démarrage du backend

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8081 --reload
```

### Mise à jour depuis GitHub

```bash
cd ~/haccp-monitor
git pull origin master
sudo systemctl restart haccp-backend
```

### Backup de la base de données

```bash
# La base haccp.db est exclue du git (.gitignore)
# Backup manuel recommandé avant toute migration :
cp haccp.db haccp.db.backup.$(date +%Y%m%d)
```

---

## 12. État du Projet (Phase par Phase)

### Phase 1 — Opérationnelle ✅

- Sondes Zigbee SNZB-02D × 4 actives
- Relevés toutes les 5-10 secondes
- Alertes email/SMS fonctionnelles
- Dashboard températures temps réel (`/static/index.html`)
- Export CSV journalier

### Phase 2 — Backend 100% ✅, Frontend avancé 🟡

**Backend (105/105 tests)** :
- Module DLC / Étiquettes ✅
- Module Réception (fiches 8 & 9) ✅
- Module Tâches HACCP (13 fiches) ✅
- Module Admin (personnel, pièges, plan nettoyage) ✅
- Module Ouvertures ✅
- Module Incidents PCR01 ✅

**Frontend** :
- Hub + navigation ✅
- Tâches HACCP ✅
- Étiquettes / Fabrication wizard ✅
- Réception (création + lignes + clôture) ✅
- Ouvertures ✅
- Incidents PCR01 ✅
- Admin général 🟡 (en cours)
- Admin recettes ✅

### Phase 3 — En cours 🟡

- Module Fabrication (recettes + FIFO + traçabilité lots) :
  - Backend ✅ (API complète)
  - Frontend wizard 4 étapes ✅
  - Historique fabrications 🟡 (UI à finaliser)
- Import catalogue matières premières (`data/extraction_matiere_premiere.xlsx` — 365 produits) 🔴 Non fait
- Nettoyage doublons en base (seed exécuté plusieurs fois) 🔴

### Prochaines priorités identifiées

1. Import catalogue `scripts/import_matieres_premieres.py`
2. Tests fonctionnels terrain sur tablette
3. Supprimer les anciens fichiers `historique-enregistrement.html` et `historique-enregistrement.js` (tous les redirects sont maintenant en place)
4. Ajouter `poids_fabrique` et `dlc_finale` dans la table `fabrications`
5. Installation PWA sur tablette Android (mode kiosque)

---

## 13. DIRECTIVES STRICTES POUR L'IA — RÈGLES D'OR

> Ces règles prévalent sur tout autre raisonnement. Les enfreindre peut casser la production d'une vraie boucherie en activité.

---

### RÈGLE N°1 : Ne jamais migrer la BDD sans accord explicite

**Interdiction absolue** de :
- Modifier `SCHEMA_SQL` dans `database.py` sans accord de l'utilisateur
- Ajouter/supprimer des colonnes dans une table existante
- Modifier un modèle Pydantic (ajout de champ obligatoire) sans vérifier l'impact sur les données existantes
- Lancer `DROP TABLE` ou `ALTER TABLE` sans backup préalable

**Pourquoi** : SQLite ne supporte pas `ALTER TABLE ... ADD COLUMN NOT NULL` sans valeur par défaut. Une migration mal écrite crashera le serveur au démarrage (appel à `init_db()` dans le lifespan FastAPI). En production, cela coupe la surveillance des températures.

**Procédure correcte** :
1. Proposer la migration à l'utilisateur
2. Attendre la confirmation explicite
3. Toujours ajouter des colonnes avec `DEFAULT` ou en `NULLABLE`
4. Tester en local avant de déployer
5. Backup de `haccp.db` avant toute migration

**Pattern sécurisé pour ajout de colonne** :
```python
# Dans init_db(), après le SCHEMA_SQL de base :
cur = await db.execute("PRAGMA table_info(fabrications)")
cols = {row[1] for row in await cur.fetchall()}
if "poids_fabrique" not in cols:
    await db.execute("ALTER TABLE fabrications ADD COLUMN poids_fabrique REAL")
    await db.commit()
```

---

### RÈGLE N°2 : Respecter l'HACCP — Ne jamais falsifier la traçabilité

**Interdiction absolue** de :
- Générer des données de traçabilité fictives (faux lots, fausses DLC, faux relevés de température)
- Permettre de bypasser la validation FIFO (choisir un lot manuellement sans laisser de trace)
- Supprimer des enregistrements de `releves`, `tache_validations`, `receptions`, `fabrications`, `fabrication_lots`
- Modifier rétroactivement une DLC ou un numéro de lot déjà imprimé

**Pourquoi** : Ces données constituent le registre HACCP légal. Falsifier ou supprimer ces données expose le boucher à des sanctions pénales lors d'un contrôle DDPP ou d'une TIAC (Toxi-Infection Alimentaire Collective).

**Règle spécifique DLC produit décongelé** :
- La DLC d'un produit décongelé est **toujours** = date de décongélation + 3 jours
- Cette valeur est réglementaire (Règlement CE 853/2004)
- Elle ne doit **jamais** être rendue modifiable par l'utilisateur dans l'UI

---

### RÈGLE N°3 : Maintenir le code UI existant

**Interdiction** de :
- Remplacer les éléments HTML existants par des versions "améliorées" sans demande explicite
- Changer les tailles de boutons sous 64px de hauteur
- Changer la taille de texte sous 18px dans les zones interactives
- Introduire un framework CSS (Tailwind, Bootstrap) qui remplacerait le système de tokens existant
- Modifier les couleurs de la charte graphique Mets Carnés

**Pourquoi** : L'interface est conçue pour des bouchers en laboratoire, avec des gants, sur une tablette murale. Les boutons surdimensionnés et les couleurs contrastées sont des exigences ergonomiques critiques, pas des préférences esthétiques.

**Pattern à suivre** pour tout nouveau composant :
```html
<!-- Bouton principal : toujours au moins 64px de hauteur -->
<button class="btn-primary" style="min-height: 64px; font-size: 1.125rem;">
  ACTION
</button>
```

---

### RÈGLE N°4 : Ne pas introduire de dépendances npm/build

- **Aucun** `package.json`, `webpack.config.js`, `vite.config.js`, `tsconfig.json`
- Le frontend est du HTML + CSS + JS vanilla, servi directement par FastAPI (`StaticFiles`)
- Toute bibliothèque JS doit être chargée via CDN (`<script src="https://cdn...">`) ou copiée dans `static/js/`
- Le Pi n'a pas Node.js et ne doit pas en avoir besoin

---

### RÈGLE N°5 : Vérifier l'existence des colonnes avant de les utiliser

Avant tout code qui lit `fabrications.poids_fabrique` ou `fabrications.dlc_finale` :

```python
cur = await db.execute("PRAGMA table_info(fabrications)")
cols = {row[1] for row in await cur.fetchall()}
if "poids_fabrique" not in cols:
    # Ne pas utiliser cette colonne — retourner None ou gérer l'absence
```

Ces colonnes peuvent ou non exister selon l'état de la migration sur l'instance en cours.

---

### RÈGLE N°6 : Pattern de modification de database.py

Toute nouvelle fonction CRUD dans `database.py` doit :
1. Utiliser `async with get_db() as db:` (jamais de connexion directe)
2. Retourner `dict(row)` ou une liste de `dict(row)` (jamais un objet `aiosqlite.Row` brut)
3. Gérer les `Optional` nullable avec `or None` (pas avec des exceptions)
4. Appeler `await db.commit()` après chaque INSERT/UPDATE/DELETE

```python
async def ma_fonction(db, param: int) -> Optional[dict]:
    cur = await db.execute("SELECT * FROM ma_table WHERE id = ?", (param,))
    row = await cur.fetchone()
    return dict(row) if row else None
```

---

### RÈGLE N°7 : Contexte monoboutique

Toute l'application est conçue pour **une seule boutique** (`boutique_id = 1`). Il n'existe pas de système multi-tenant opérationnel. Ne pas introduire de logique de sélection de boutique dans le frontend — toutes les requêtes API utilisent `boutique_id = 1` implicitement.

---

### RÉCAPITULATIF DES RÈGLES D'OR

| N° | Règle | Risque si non respectée |
|----|-------|------------------------|
| 1 | Ne jamais migrer la BDD sans accord | Crash serveur en production |
| 2 | Ne jamais falsifier la traçabilité | Infraction légale HACCP |
| 3 | Maintenir l'UI existante (64px, 18px, couleurs) | Inuti lisabilité en condition réelle |
| 4 | Pas de dépendances npm/build | Déploiement impossible sur Pi |
| 5 | Vérifier les colonnes avant usage | Erreur SQL en production |
| 6 | Pattern CRUD async database.py | Bugs concurrence SQLite |
| 7 | Mono-boutique (id=1) | Données mélangées |

---

*Fin du document CONTEXT_MASTER.md — Version 1.0 — 2026-04-12*

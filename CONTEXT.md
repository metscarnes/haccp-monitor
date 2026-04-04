# Contexte projet — HACCP Monitor
## Au Comptoir des Lilas / Mets Carnés Holding

---

## Stack technique

- **Serveur** : Raspberry Pi 4, IP locale `192.168.1.83`, port `8081`
- **Backend** : Python 3.11 + FastAPI + SQLite (aiosqlite)
- **Sondes** : Zigbee2MQTT + Mosquitto (broker MQTT local)
- **Frontend** : HTML/CSS/JS vanilla dans `static/` — servi par FastAPI
- **Imprimante** : Brother QL-820NWB en USB sur le Pi (driver `brother_ql`)
- **Interface** : Web app PWA, tablette Android murale en mode kiosque
- **Versionning** : Git + GitHub (repo privé metscarnes/haccp-monitor)

---

## État du projet

### Phase 1 — Opérationnelle
- Sondes Zigbee SNZB-02D (x4) : chambre_froide_1, chambre_froide_2, vitrine, laboratoire
- Relevés de température toutes les 5-10 secondes en base SQLite
- Alertes email/SMS sur dépassement de seuil
- Dashboard températures temps réel (`/static/index.html`)

### Phase 2 — Backend opérationnel (105/105 tests)
- Module DLC / Étiquettes
- Module Réception (fiches 8 + 9)
- Module Tâches HACCP (12 fiches)
- Module Admin
- Frontend Phase 2 : hub + tâches + étiquettes + réception créés

### En cours
- Import catalogue matières premières (365 produits, `data/extraction_matiere_premiere.xlsx`)
- Écran Admin frontend
- Nettoyage doublons en base (seed data exécuté plusieurs fois)

---

## Architecture fichiers

```
haccp-monitor/
├── CONTEXT.md                  ← ce fichier
├── haccp.db                    ← base SQLite (NE PAS SUPPRIMER)
├── requirements.txt
├── data/
│   └── extraction_matiere_premiere.xlsx   ← catalogue matières premières
├── src/
│   ├── main.py                 ← FastAPI app, port 8081
│   ├── database.py             ← toutes les tables + CRUD
│   ├── mqtt_subscriber.py      ← écoute MQTT → stockage relevés
│   ├── alert_manager.py        ← logique alertes + SMTP
│   ├── api/
│   │   ├── routes_boutiques.py
│   │   ├── routes_enceintes.py
│   │   ├── routes_releves.py
│   │   ├── routes_alertes.py
│   │   ├── routes_rapports.py
│   │   ├── routes_etiquettes.py
│   │   ├── routes_reception.py
│   │   ├── routes_taches.py
│   │   └── routes_admin.py
│   └── printing/
│       └── brother_ql_driver.py
├── static/
│   ├── index.html              ← dashboard Phase 1 (températures)
│   ├── hub.html                ← accueil Phase 2
│   ├── taches.html
│   ├── etiquettes.html
│   ├── reception.html
│   ├── manifest.json           ← PWA manifest
│   ├── css/style.css
│   └── js/
│       ├── dashboard.js
│       ├── hub.js
│       ├── taches.js
│       ├── etiquettes.js
│       └── reception.js
├── tests/
│   ├── test_api.py
│   ├── test_alerts.py
│   ├── test_database.py
│   ├── test_etiquettes.py
│   ├── test_reception.py
│   └── test_taches.py
└── scripts/
    ├── setup_pi.sh
    └── backup.sh
```

---

## Base de données — tables principales

```sql
boutiques         -- 1 enregistrement : Au Comptoir des Lilas (id=1)
enceintes         -- 4 sondes (ids: 1, 2, 7, 8)
releves           -- relevés de température (INSERT only)
alertes           -- alertes déclenchées
produits          -- catalogue matières premières + PAV
regles_dlc        -- règles de calcul DLC par catégorie
etiquettes_generees
fournisseurs
receptions
reception_lignes
non_conformites_fournisseur
tache_types
tache_validations
personnel
pieges
plan_nettoyage
```

---

## Catalogue produits — structure

| Champ | Description |
|---|---|
| `nom` | Dénomination (ex: "VB-PALERON") |
| `code_unique` | Code unique (ex: "VBR06") — index UNIQUE |
| `espece` | Bœuf / Veau / Porc / Agneau / Gibier / Volaille / Exotique / Cheval |
| `etape` | 1=Coupe primaire, 2=Coupe de gros, 3=Coupe secondaire, 4=PAV |
| `coupe_niveau` | Libellé exact du niveau de coupe |
| `conditionnement` | SOUS_VIDE ou CARCASSE (valeur par défaut, modifiable par l'utilisateur) |
| `categorie` | matiere_premiere / pav / viande_hachee / preparation_crue / etc. |
| `dlc_jours` | 0 si matiere_premiere (DLC fournisseur), sinon J+1/2/3/5 |
| `temperature_conservation` | "0°C à +4°C" affiché sur l'étiquette |

---

## Règles métier critiques

- **Matière première sous vide** : `dlc_jours = 0`, DLC = celle du fournisseur, saisie manuelle obligatoire
- **Produit décongelé** : DLC = date décongélation + 3 jours, automatique, non modifiable
- **Numéro de lot fabrication** : format `MC-YYYYMMDD-XXXX`, auto-incrémenté
- **Numéro de lot fournisseur** : saisie texte libre, recopie de l'étiquette
- **Seuil CF viandes** : 0°C à +3°C (pas +4°C) avec +2°C max si viande hachée fraîche
- **Toute configuration passe par l'UI admin** — aucune valeur codée en dur

---

## UX — règles non négociables

- Navigation **Option B** : hub central, pas d'onglets permanents
- **3 taps maximum** par action
- Boutons minimum **64px** hauteur, texte minimum **18px**
- **Sélecteur prénom** avant toute action traçable (liste configurable en admin)
- Retour accueil automatique après **5 minutes** d'inactivité
- Clavier numérique natif sur tous les champs numériques

---

## Charte graphique Mets Carnés

| Rôle | Couleur | Code |
|---|---|---|
| Fond principal | Ivoire | `#F5ECD7` |
| Texte principal | Noyer foncé | `#3D2008` |
| Accent | Brun moyen | `#6B3A1F` |
| Secondaire | Crème | `#D4A574` |
| Statut OK | Vert | `#2D7D46` |
| Statut attention | Orange | `#E8913A` |
| Statut alerte | Rouge | `#C93030` |

---

## Endpoints API principaux

```
GET  /api/boutiques/1/dashboard       → statut temps réel toutes enceintes
GET  /api/boutiques/1/enceintes       → liste des enceintes
GET  /api/taches/today                → tâches du jour avec statut
GET  /api/produits                    → catalogue produits
GET  /api/regles-dlc                  → règles DLC par catégorie
GET  /api/receptions                  → historique réceptions
GET  /api/etiquettes/alertes-dlc      → produits DLC proche
GET  /api/admin/personnel             → liste du personnel
GET  /api/impression/status           → statut imprimante
```

---

## Commandes utiles sur le Pi

```bash
# Connexion SSH
ssh campiglia@192.168.1.83

# Redémarrer le backend
sudo systemctl restart haccp-backend

# Voir les logs en temps réel
sudo journalctl -u haccp-backend -f --no-pager

# Filtrer par sonde
sudo journalctl -u haccp-backend -f --no-pager | grep "chambre_froide_2"

# Statut tous les services
sudo systemctl status haccp-backend zigbee2mqtt mosquitto --no-pager

# Mettre à jour depuis GitHub
cd ~/haccp-monitor && git pull origin master && sudo systemctl restart haccp-backend

# Lancer les tests
cd ~/haccp-monitor && python -m pytest tests/ -v
```


---

## Prochaines étapes

1. Import catalogue matières premières (`data/extraction_matiere_premiere.xlsx`)
2. Écran Admin frontend (`static/admin.html`)
3. Tests fonctionnels terrain sur tablette
4. Installation PWA sur tablette Android
5. Correction seuils températures via UI admin

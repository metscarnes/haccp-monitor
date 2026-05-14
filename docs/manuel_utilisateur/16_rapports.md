# Module 16 — Rapports & Historique Unifié

---

## 1. Objectif

Ce module regroupe deux espaces distincts :
- La **génération de rapports de conformité** températures (PDF, HTML interactif, CSV) pour les contrôleurs DDPP et la traçabilité réglementaire.
- La page **Historique Unifié** (`/historique.html`), portail de consultation de toutes les données historiques de l'application : relevés, flux produits, HACCP quotidien, rapports générés.

---

## 2. Chemins d'accès

| Page | URL | Accès |
|---|---|---|
| **Rapports (depuis le dashboard)** | `/index.html` → onglet Rapports | Températures → onglet "Rapports" |
| **Rapport interactif DDPP** | `/api/rapports/interactif/1?jours=90` | Bouton "✨ Ouvrir le rapport" (s'ouvre dans un nouvel onglet) |
| **Historique unifié** | `/historique.html` | Hub principal → tuile Historique |

---

## 3. Rapports — 3 types disponibles

### 3.1 Rapport interactif DDPP *(recommandé)*

Le rapport le plus complet, généré à la demande pour les **90 derniers jours**. Il s'ouvre dans un nouvel onglet et contient :
- Données de température de toutes les enceintes **embarquées dans la page HTML** (pas d'appel API nécessaire pour la navigation)
- Graphiques dynamiques Chart.js avec filtres de période
- Liste de toutes les alertes de dépassement de température
- **Export PDF** directement via le navigateur (impression native)

> Ce rapport est idéal pour une présentation aux autorités sanitaires (DDPP). Il peut être sauvegardé en PDF ou transmis tel quel.

### 3.2 Rapport figé (archive PDF)

Génération depuis le formulaire dans l'onglet Rapports :

| Champ | Valeurs | Notes |
|---|---|---|
| **Type** | Journalier / Mensuel | |
| **Date début** | Pré-remplie à hier | Format AAAA-MM-JJ |
| **Date fin** | Pré-remplie à hier | Format AAAA-MM-JJ |

Bouton **`Générer le rapport`** → `POST /api/rapports/generer` (HTTP 202 Accepted). Le rapport est immédiatement disponible dans la liste "Rapports générés" sous le formulaire.

Chaque rapport généré affiche : type, plage de dates, date de génération, badge **✅ Conforme** / **❌ Non conforme**, et lien **`📄 PDF`** pour téléchargement.

> Note : si le fichier PDF est au format `.html`, le navigateur l'ouvre directement ; sinon il est téléchargé.

### 3.3 Rapport journalier depuis CSV

Outil d'analyse basé sur les **fichiers CSV bruts** exportés par les sondes :

1. Saisir une **Date** (pré-remplie à hier)
2. Cliquer **`Charger`**
3. Le système scanne le dossier `CSV_EXPORT_DIR` et affiche une grille de cartes, une par sonde présente.

Chaque carte sonde affiche :
- Nom de la sonde
- T° min · T° moy · T° max
- Humidité min–max (si disponible)
- Nombre de relevés
- Badge `Conforme` (T° max ≤ 4°C) ou `Hors seuil` (T° max > 4°C) — indicateur visuel simplifié
- Bouton **`⬇ Télécharger CSV`** → télécharge le fichier brut `[sonde]_YYYY-MM-DD.csv`

Colonnes du CSV téléchargé : `horodatage ; temperature_c ; humidite_pct ; batterie_pct ; qualite_signal`

---

## 4. Page Historique Unifié (`/historique.html`)

### 4.1 Architecture — 4 catégories, 10 sous-onglets

La page est organisée en **2 niveaux de navigation** :

#### Niveau 1 — Catégories

| Catégorie | Sous-onglets |
|---|---|
| 🌡️ **Températures** | 🌡️ Relevés · 📏 Étalonnages |
| 📦 **Flux produits** | 📦 Réceptions · 🏭 Fabrications · 🔥 Cuissons · ❄️ Refroidissements · 🗑️ Devenir DLC |
| 🧹 **HACCP** *(actif par défaut)* | ✂️ Ouvertures · 🧹 Nettoyage · 🐀 Nuisibles |
| 📄 **Rapports** | 📄 Rapports générés |

#### Niveau 2 — Sous-onglets

Cliquer sur une catégorie affiche ses sous-onglets. Le contenu du sous-onglet actif se charge automatiquement.

---

### 4.2 🌡️ Températures — Onglet Relevés

Redirige vers `/index.html?vue=historique` (module Températures, vue Historique). L'onglet affiche :

> *"Géré par le module Température (graphiques, stats, export CSV par enceinte)."*  
> Bouton `📊 Ouvrir le module Température →`

### 4.3 🌡️ Températures — Onglet Étalonnages

Historique des étalonnages EET01 (liste avec compteur).

---

### 4.4 📦 Flux produits — Onglet Réceptions

**Filtres** : Recherche produit/lot (avec autocomplete ▾) · Fournisseur (avec autocomplete ▾) · Du · Au · `🔍 Rechercher` · `✕ Reset`

**Cartes réceptions** : cliquer sur une carte déplie/replier les détails.

Chaque carte affiche en-tête : date, fournisseur, statut (Conforme / NC / En cours / Refusée). En détail déroulé : informations camion, lien photo BL, liste des produits réceptionnés avec critères visuels et badges NC.

### 4.5 📦 Flux produits — Onglet Fabrications

**Filtres** : Recherche produit/lot (autocomplete ▾) · Tri (Date ↑↓ / DLC ↑↓ / Nom A-Z / Z-A) · Du · Au

Cartes avec : icône 🏭, nom du produit fini, N° lot interne, date fabrication, DLC, poids fabriqués. Déroulé : liste des ingrédients avec quantité, N° lot source et DLC.

### 4.6 📦 Flux produits — Onglet Cuissons

**Filtres** : Recherche produit/lot · Espèce · Tri · Type (Rôtissoire / Four) · Du · Au

Cartes avec : T° sortie colorée (vert ≥ 75°C / rouge < 75°C), conformité HACCP.

### 4.7 📦 Flux produits — Onglet Refroidissements

**Filtres** : Recherche produit/lot · Espèce · Tri · Du · Au

Cartes avec : durée, T° initiale/finale, conformité (vert si conforme, rouge si JETER).

### 4.8 📦 Flux produits — Onglet Devenir DLC

**Filtres** : Recherche produit/lot · Tri · **Devenir** (Jetés / Vendus / Consommés / Autre) · **Source** (Réceptions / Fabrications) · Du · Au

Historique de toutes les sorties de stock via le Calendrier DLC.

---

### 4.9 🧹 HACCP — Onglet Ouvertures *(actif par défaut)*

**Filtres** : Produit (autocomplete) · Du · Au · `🔍 Rechercher` · `✕ Reset`

Identique à la page `/ouvertures-historique.html` : cartes avec miniature photo cliquable (plein écran), badge Tracée/Manuelle, infos réception si tracée. Pagination "Voir plus…".

### 4.10 🧹 HACCP — Onglet Nettoyage

Arborescence Année → Mois → Semaine ISO → jours. Pour chaque semaine ouverte : tableau de planning complet (Secteur × Tâche × Produit × 7 jours). Les jours validés affichent l'initiale de l'opérateur en vert.

### 4.11 🧹 HACCP — Onglet Nuisibles

**Filtres** : Type (Rongeurs / Insectes volants / Insectes rampants / Oiseaux) · Année · `🔍 Rechercher`

Grille des semaines ISO avec résultats par piège (O / N / vide).

---

### 4.12 📄 Rapports — Onglet Rapports générés

Liste paginée des rapports générés (identique à la liste de l'onglet Rapports du dashboard).

---

## 5. Impression depuis l'historique

La page `historique.html` intègre **deux gabarits d'impression thermique** invisibles à l'écran :

| Gabarit | Usage | Déclencheur |
|---|---|---|
| `#print-label` | Étiquette fabrication (avec ingrédients) | Bouton ré-impression sur une fabrication |
| `#print-label-transforme` | Étiquette transformé (cuisson/refroidissement) | Bouton ré-impression sur cuisson ou refroidissement |

La bascule entre les deux gabarits se fait via `body.classList.toggle('printing-transforme')`.

---

## 6. Règles de conformité invisibles

### 6.1 Rapport interactif : données embarquées

Le rapport interactif est une **page HTML autonome** : toutes les données (relevés, alertes) sont sérialisées en JSON directement dans le HTML lors de sa génération. Une fois ouvert, il ne fait plus d'appels API. Il peut être sauvegardé localement ou envoyé par email.

### 6.2 Paramètre `jours` du rapport interactif

Le rapport interactif charge par défaut les **90 derniers jours** (`?jours=90`). La valeur est limitée entre 1 et 365 côté serveur.

### 6.3 Sécurité du chemin CSV

Le nom de la sonde est sanitisé avant construction du chemin fichier : tout caractère non alphanumérique (hors `-` et `_`) est remplacé par `_`. Cela évite les traversées de répertoire.

### 6.4 Conformité CSV : seuil 4°C simplifié

Dans l'onglet "Rapport CSV", la conformité est calculée avec le seuil fixe `T° max ≤ 4°C`. Ce n'est pas la conformité réglementaire de l'enceinte (qui dépend de ses seuils configurés) — c'est un indicateur visuel rapide.

---

## 7. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Boutique introuvable (rapport interactif) | HTTP 404 |
| Rapport sans fichier PDF | HTTP 404 avec message : *"Fichier PDF non encore généré"* |
| Rapport PDF introuvable sur disque | HTTP 404 avec message : *"Fichier PDF introuvable sur le disque"* |
| Aucun CSV pour la date choisie | Message : *"Aucun CSV disponible pour le [date]."* |
| Erreur génération rapport | `alert("Erreur lors de la génération : [détail]")` |
| Date invalide (téléchargement CSV) | HTTP 400 : *"Format de date invalide"* |

---

[Passer au module suivant : Hub](17_hub.md)

# Module 15 — Enceintes Frigorifiques & Relevés

---

## 1. Objectif

Ce module est le cœur du **monitoring de température en temps réel**. Il affiche l'état de toutes les enceintes frigorifiques (chambres froides, vitrines, laboratoire) connectées via sondes Zigbee, l'historique graphique des relevés, les alertes de dépassement de seuil et la génération de rapports de conformité.

---

## 2. Chemin d'accès

Hub principal → tuile **🌡️ TEMPÉRATURES** (ou lien direct `/index.html`).

L'URL accepte un paramètre `?vue=historique` pour ouvrir directement la vue Historique.

---

## 3. Architecture — 4 vues dans une page unique

La page est organisée en 4 onglets :

| Onglet | Vue | Contenu |
|---|---|---|
| **Tableau de bord** | Actif par défaut | Cartes temps réel de toutes les enceintes |
| **Historique** | — | Graphique + tableau agrégé des relevés |
| **Alertes** | — | Journal des dépassements de température |
| **Rapports** | — | Génération et téléchargement de rapports |

**Rafraîchissement automatique** : le tableau de bord se recharge automatiquement **toutes les 30 secondes**, uniquement quand l'onglet "Tableau de bord" est visible.

---

## 4. Vue Tableau de bord

### 4.1 Statut global

En haut à droite de l'en-tête, un badge indique l'état général :

| Statut | Signification |
|---|---|
| `OK` | Toutes les enceintes dans les seuils |
| `Attention` | Au moins une enceinte en zone limite |
| `Alerte` | Au moins une enceinte hors seuils |
| `Hors ligne` | Au moins une enceinte sans signal |
| `—` | Données en cours de chargement |

### 4.2 Bandeau d'alerte

Un **bandeau rouge** apparaît en haut de page si au moins une enceinte est en alerte :  
`⚠️ N alerte(s) en cours — [Nom enceinte 1], [Nom enceinte 2]…`

### 4.3 Cartes enceinte

Une carte par enceinte configurée. Chaque carte contient :

| Élément | Contenu |
|---|---|
| **Nom** + **Type** | Identifiant de l'enceinte (ex. : "Chambre froide 1") |
| **Badge statut** | OK / Attention / Alerte / Hors ligne (coloré) |
| **Détail alerte** (si en cours) | Type d'alerte + durée écoulée (ex. : `🌡️ Température trop haute — depuis 23min`) |
| **Température principale** | Valeur actuelle en grand format (°C) |
| **Humidité** | `Humidité : X,X%` |
| **Mini graphique** | Courbe des dernières 24h (invisible si aucun relevé) |
| **Batterie** | Pourcentage + indicateur couleur : 🟢 ≥40% · 🟠 20–39% · 🔴 <20% |
| **Mise à jour** | `Mis à jour JJ/MM/AAAA HH:MM` |

**Cliquer sur une carte** → bascule vers la vue **Historique** avec cette enceinte présélectionnée sur la période **24h**.

---

## 5. Vue Historique

### 5.1 Sélection enceinte

Boutons pour chaque enceinte. L'enceinte sélectionnée est mise en évidence. La première est sélectionnée par défaut à l'ouverture de la vue.

### 5.2 Sélection de période

| Option | Plage temporelle |
|---|---|
| **24h** | Jour courant entier (00:00 → 23:59) |
| **7 jours** | 7 derniers jours depuis maintenant |
| **30 jours** | 30 derniers jours depuis maintenant |
| **Personnalisée** | Deux champs Date début / Date fin + bouton **`Appliquer`** |

### 5.3 Bandeau de statistiques

5 métriques calculées sur la période sélectionnée :
- **T° min** (en rouge si inférieure au seuil minimum de l'enceinte)
- **T° moy**
- **T° max** (en rouge si supérieure au seuil maximum)
- **Humidité moy**
- **Nombre de relevés**

### 5.4 Graphique Chart.js

Courbe de température avec lignes de seuil (min et max) tracées. Les dépassements sont visuellement identifiables.

### 5.5 Tableau agrégé

Le tableau s'affiche sous le graphique et regroupe les relevés par :
- **Par heure** si période = 24h
- **Par jour** si période = 7j, 30j ou personnalisée

Colonnes : **Heure/Date** · **T° min** · **T° moy** · **T° max** · **Humidité moy** · **Relevés** · **Conformité**

La colonne **Conformité** affiche `✓ Conforme` si toutes les températures de la période sont dans les seuils, sinon `✗ Hors seuil`.

### 5.6 Export CSV

Bouton **`Exporter CSV`** → télécharge un fichier CSV nommé `releves_[Nom]_[debut]__[fin].csv` avec les colonnes : `horodatage ; temperature_c ; humidite_pct ; batterie_pct ; qualite_signal`.

---

## 6. Vue Alertes

### 6.1 Filtres

Case à cocher **"Afficher les alertes fermées"** : si cochée, charge toutes les alertes historiques par enceinte et les affiche avec les alertes en cours, triées par date décroissante.

### 6.2 Filtre sur les types

Seules les alertes de **dépassement de température** sont affichées (`temperature_haute` et `temperature_basse`). Les alertes de perte de signal et batterie faible sont **filtrées** dans cette vue.

### 6.3 Présentation d'une alerte

| Élément | En cours | Fermée |
|---|---|---|
| Icône | 🔴 | ✅ |
| Type | 🌡️ Température trop haute / ❄️ Température trop basse | Idem |
| Localisation | Boutique — Enceinte | Idem |
| Valeur et seuil | `Valeur : X,X · Seuil : X,X` | Idem |
| Durée | Durée écoulée depuis le début | — |
| Début / Fin | Début | Début · Fin |

---

## 7. Vue Rapports

### 7.1 Rapport interactif pour contrôleur DDPP

Bouton **`✨ Ouvrir le rapport`** (en haut de la vue). Ouvre dans un **nouvel onglet** le rapport interactif des 90 derniers jours (`/api/rapports/interactif/1?jours=90`). Ce rapport est exportable en PDF directement depuis la page.

### 7.2 Rapport figé (archive)

Formulaire avec :
- **Type** : Journalier / Mensuel
- **Date début** et **Date fin** (pré-remplies avec hier)
- Bouton **`Générer le rapport`** → `POST /api/rapports/generer` → le rapport apparaît dans la liste ci-dessous

Liste des rapports générés avec : type, plage de dates, date de génération, badge Conforme/Non conforme, lien **`📄 PDF`**.

### 7.3 Rapport journalier depuis CSV

Champ date + bouton **`Charger`**. Affiche une grille de cartes, une par sonde avec :
- T° min · moy · max
- Humidité (min–max) si disponible
- Nombre de relevés
- Badge `Conforme` (T° max ≤ 4°C) ou `Hors seuil` (T° max > 4°C) — indicateur visuel simplifié
- Bouton **`⬇ Télécharger CSV`** pour télécharger le fichier brut de chaque sonde

---

## 8. Règles de conformité invisibles

### 8.1 Seuils par enceinte

Chaque enceinte a ses propres seuils configurés en administration :

| Paramètre | Défaut | Rôle |
|---|---|---|
| `seuil_temp_min` | 0°C | Seuil bas |
| `seuil_temp_max` | 4°C | Seuil haut |
| `seuil_hum_max` | 90% | Seuil humidité |
| `delai_alerte_minutes` | 5 min | Anti-faux positifs |

Les 4 enceintes typiques de l'établissement :
- 2 chambres froides (0°C – 4°C)
- 1 vitrine réfrigérée (0°C – 4°C)
- 1 laboratoire (10°C – 15°C)

### 8.2 Calcul des statuts enceinte

La logique de statut est calculée côté backend à chaque appel `GET /api/enceintes/{id}/status` :

| Statut | Condition |
|---|---|
| `ok` | `seuil_min ≤ T° ≤ seuil_max` |
| `attention` | T° proche des limites : `T° < seuil_min + 0,5°C` OU `T° > seuil_max − 0,5°C` |
| `alerte` | `T° < seuil_min` OU `T° > seuil_max` |
| `inconnu` | Aucun relevé disponible |

### 8.3 Délai anti-faux positifs

Les alertes ne se déclenchent pas instantanément. Un dépassement doit persister pendant **5 minutes** (`delai_alerte_minutes`) avant de créer une alerte. Cela évite les alertes intempestives lors d'ouvertures/fermetures de portes.

### 8.4 "24h" = jour courant, pas les 24 dernières heures

La période `24h` est définie comme **le jour courant entier** (00:00:00 → 23:59:59 en heure locale), **non** les 24 dernières heures glissantes. Cela correspond à la journée HACCP.

### 8.5 Polling uniquement sur la vue active

Le rafraîchissement automatique des données dashboard (toutes les 30s) ne s'exécute **que si l'onglet "Tableau de bord" est visible**. Cela évite de consommer des ressources réseau inutilement si l'utilisateur est sur une autre vue.

### 8.6 Alimenté par les sondes Zigbee (MQTT)

Les données de température, humidité et batterie sont injectées en base de données par le service `mqtt_subscriber.py` qui écoute le broker MQTT auquel les capteurs Zigbee envoient leurs mesures. Ce composant fonctionne en arrière-plan, indépendamment du frontend.

---

## 9. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Erreur chargement dashboard | Log console, page reste affichée (donnée potentiellement périmée) |
| Aucune enceinte configurée | Dashboard vide |
| Sonde sans signal récent | Statut `inconnu` sur la carte |
| Erreur chargement historique | `alert("Erreur lors du chargement des données.")` |
| Période personnalisée sans dates | `alert("Sélectionne les deux dates.")` |
| Erreur génération rapport | `alert("Erreur lors de la génération : [détail]")` |
| Aucun rapport généré | Message : *"Aucun rapport généré."* |
| Aucun CSV pour la date choisie | Message : *"Aucun CSV disponible pour le [date]."* |
| Aucune alerte de température | Message : *"Aucune alerte de température."* |
| Erreur chargement alertes | Message rouge : *"Erreur de chargement."* |

---

[Passer au module suivant : Rapports](16_rapports.md)

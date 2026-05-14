# Module 5 — Tâches HACCP

---

## 1. Objectif

Ce module regroupe le suivi quotidien des tâches de surveillance HACCP : il affiche en temps réel l'état des contrôles à effectuer, en retard ou déjà validés. Il sert également de **portail de navigation** vers tous les sous-modules de conformité réglementaire (nettoyage, étalonnage, nuisibles, températures, e-learning).

---

## 2. Architecture — deux pages distinctes

| Page | Rôle | URL |
|---|---|---|
| **Hub Tâches HACCP** | Portail de navigation vers les sous-modules | `/taches-hub.html` |
| **Tableau du jour** | Kanban des tâches pièges du jour | `/taches.html` |

---

## 3. Page 1 — Hub Tâches HACCP (`taches-hub.html`)

### 3.1 Chemin d'accès

Hub principal → bouton ou carte **Tâches HACCP**.

### 3.2 Interface

La page affiche une grille de 5 tuiles de navigation, chacune avec une icône, un titre et un statut dynamique :

| Tuile | Icône | Destination | Statut |
|---|---|---|---|
| **NETTOYAGE** | 🧹 | `/nettoyage.html` | Dynamique (validé aujourd'hui / à faire) |
| **ÉTALONNAGE** | 🌡️ | `/etalonnage.html` | Dynamique (date du prochain étalonnage) |
| **TEMPÉRATURES** | 🌡️ | `/` (dashboard) | Dynamique (alertes actives) |
| **NUISIBLES** | 🐛 | `/nuisibles.html` | `IPM — Plan de lutte` (statique) |
| **E-LEARNING** | 🎓 | `/elearning.html` | `Formation HACCP` (statique) |

Les statuts des tuiles Nettoyage, Étalonnage et Températures sont chargés depuis l'API au démarrage et mis à jour dynamiquement.

---

## 4. Page 2 — Tableau du jour (`taches.html`)

### 4.1 Chemin d'accès

Hub Tâches HACCP → aucune tuile directe (accessible via le lien `← Tâches` depuis d'autres pages, ou directement via l'URL `/taches.html`).

> **Important** : Cette page gère uniquement les tâches de **contrôle des pièges** (rongeurs et oiseaux). Les autres tâches HACCP (nettoyage, étalonnage, nuisibles) disposent chacune de leur propre module dédié.

### 4.2 Interface — Structure de la page

#### En-tête

| Élément | Contenu |
|---|---|
| Bouton `← Tâches` | Retour vers `/taches-hub.html` |
| Titre | `TÂCHES HACCP` |
| Date | Date du jour en toutes lettres (ex : `Mercredi 14 mai 2026`) |
| Horloge | Heure courante mise à jour toutes les secondes |

#### Barre opérateur

Barre permanente sous l'en-tête affichant les boutons prénoms du personnel. **L'opérateur doit être sélectionné avant toute validation.** Le bouton sélectionné est mis en évidence visuellement.

Si aucun opérateur n'est sélectionné et que l'on clique sur une tâche : la barre opérateur **clignote** (animation flash orange de 800 ms) pour attirer l'attention.

#### Colonnes Kanban

La page est divisée en **3 colonnes** avec compteur de tâches :

| Colonne | Couleur | Contenu |
|---|---|---|
| **EN RETARD** | Rouge | Tâches dont l'heure cible est dépassée sans validation |
| **À FAIRE** | Orange | Tâches planifiées pour aujourd'hui, pas encore validées |
| **FAIT** | Vert | Tâches validées aujourd'hui |

Chaque colonne affiche `✓ Aucune tâche en retard` / `Aucune tâche en attente` / `Aucune validation aujourd'hui` si elle est vide.

#### Cartes de tâche

Chaque carte affiche :
- Icône de la tâche 🪤
- Heure cible (si définie) au format `HH:MM`
- Libellé de la tâche

Les cartes des colonnes **EN RETARD** et **À FAIRE** sont **cliquables** (ouvrent la modale de validation). Les cartes de la colonne **FAIT** sont affichées en lecture seule (non cliquables).

### 4.3 Tâches actuellement gérées

Deux tâches sont actuellement actives sur cette page (code interne → libellé) :

| Code | Libellé | Icône | Champs spécifiques |
|---|---|---|---|
| `pieges_rongeurs` | Présence rongeurs sur pièges | 🪤 | Case à cocher par piège rongeur |
| `nettoyage_pieges_oiseaux` | Nettoyage pièges oiseaux | 🪤 | Case à cocher par piège oiseau |

---

## 5. Mode d'emploi pas-à-pas — Valider une tâche

1. Sélectionner son prénom dans la **barre opérateur** en haut de l'écran.
2. Repérer la tâche dans la colonne **EN RETARD** ou **À FAIRE**.
3. Cliquer sur la carte → la **modale de validation** s'ouvre.
4. Remplir les champs spécifiques selon la tâche (voir section 6).
5. Sélectionner la **Conformité** : `✅ Conforme` ou `❌ Non conforme`.
6. Ajouter un **Commentaire** si nécessaire (optionnel).
7. Cliquer **`Valider ✓`**.
8. La modale se ferme, la tâche passe dans la colonne **FAIT** et les compteurs sont mis à jour.

---

## 6. Détail de la modale de validation

### En-tête de la modale

| Élément | Contenu |
|---|---|
| Icône | 🪤 (pièges) |
| Titre | Libellé exact de la tâche |
| Sous-titre | `Heure cible : HH:MM` si planifiée, sinon `Tâche événementielle` |
| Bouton `✕` | Ferme la modale sans valider |

### Champs spécifiques par tâche

#### Tâche `pieges_rongeurs` — Présence rongeurs

Une **case à cocher par piège rongeur** configuré dans l'administration :
```
☐  [Identifiant piège] — [Localisation]  — Rongeur présent
```
Cocher une case indique qu'un rongeur a été détecté sur ce piège. Les cases non cochées signifient l'absence de rongeur.

> Si aucun piège rongeur n'est configuré dans l'administration, un message s'affiche : *"Aucun piège rongeur configuré — [lien configurer]"*

#### Tâche `nettoyage_pieges_oiseaux` — Nettoyage pièges oiseaux

Une **case à cocher par piège oiseau** configuré dans l'administration :
```
☐  [Identifiant piège] — [Localisation]  — Nettoyé
```
Cocher une case indique que ce piège a été nettoyé.

> Si aucun piège oiseau n'est configuré : *"Aucun piège oiseau configuré — [lien configurer]"*

### Champs communs (toutes tâches)

| Champ | Obligatoire | Notes |
|---|---|---|
| **Conformité** | Oui ✱ | Radio : `✅ Conforme` / `❌ Non conforme` |
| **Commentaire** | Non | Zone de texte libre (ex. : observation, action corrective) |

### Boutons de la modale

| Bouton | Action |
|---|---|
| `Annuler` | Ferme la modale sans enregistrer |
| `Valider ✓` | Soumet la validation → passe en `Envoi…` → ferme et rafraîchit |

---

## 7. Règles de conformité invisibles

### 7.1 Rafraîchissement automatique

La liste des tâches est rechargée automatiquement **toutes les 60 secondes** en arrière-plan, sans action de l'opérateur. Cela garantit que l'affichage reste synchronisé si une autre personne valide une tâche sur une autre tablette.

### 7.2 Fréquences de tâches

Le backend supporte 6 fréquences de planification pour les types de tâches :

| Fréquence | Signification |
|---|---|
| `quotidien` | Apparaît chaque jour |
| `hebdomadaire` | Apparaît une fois par semaine |
| `mensuel` | Apparaît une fois par mois |
| `evenementiel` | Déclenchée par un événement (pas de récurrence) |
| `exceptionnel` | Tâche ponctuelle exceptionnelle |
| `ponctuel` | Usage unique |

### 7.3 Données spécifiques JSON

L'état des pièges cochés est stocké en JSON dans le champ `donnees_specifiques` de chaque validation :
- Pour `pieges_rongeurs` : `{"pieges_rongeurs": {"[identifiant]": true/false, ...}}`
- Pour `nettoyage_pieges_oiseaux` : `{"pieges_oiseaux": {"[identifiant]": true/false, ...}}`

Ce JSON est consultable dans l'historique des validations via l'API.

### 7.4 Filtre sur les codes actifs

La page `taches.html` n'affiche que les tâches dont le code est dans la liste `{pieges_rongeurs, nettoyage_pieges_oiseaux}`. Les autres types de tâches enregistrés en base sont ignorés par ce filtre côté frontend. Les autres modules (nettoyage, nuisibles, étalonnage) gèrent leurs propres validations de façon indépendante.

### 7.5 Heure cible et statut "en retard"

La logique de calcul du statut (à faire, en retard, fait) est déterminée **côté serveur** par `GET /api/taches/today`, qui compare la fréquence planifiée aux validations existantes du jour. Le frontend affiche simplement les tâches dans la colonne correspondant à leur statut.

---

## 8. Fermeture de la modale

| Méthode | Comportement |
|---|---|
| Bouton `✕` (en-tête) | Ferme sans enregistrer |
| Bouton `Annuler` | Ferme sans enregistrer |
| Clic en dehors de la modale | Ferme sans enregistrer |
| Touche `Escape` | Ferme sans enregistrer |

---

## 9. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Clic sur une tâche sans opérateur sélectionné | Barre opérateur clignotant en orange (800 ms), modale non ouverte |
| Conformité non sélectionnée à la soumission | Message rouge : *"Veuillez indiquer si la tâche est conforme ou non."* |
| Erreur réseau lors de la validation | Message rouge dans la modale : *"Erreur : [détail]"*, bouton Valider réactivé |
| Connexion perdue lors du chargement | Chaque colonne affiche : *"⚠ Connexion perdue"* |
| Aucun personnel configuré | Barre opérateur : *"Aucun personnel configuré"* |
| Pièges non configurés | Message dans la modale : *"Aucun piège [type] configuré — [lien admin]"* |

---

[Passer au module suivant : Nettoyage & Désinfection](06_nettoyage.md)

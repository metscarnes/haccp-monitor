# Module 2 — Réception de Marchandises

---

## 1. Objectif

Ce module enregistre chaque livraison de matières premières : identité de l'opérateur, contrôle du camion (température + propreté), photo du bon de livraison, saisie des produits reçus avec leurs numéros de lot et dates limites, et contrôle visuel par espèce. En cas de non-conformité, il déclenche automatiquement la procédure réglementaire PCR01.

---

## 2. Chemin d'accès

Depuis le Hub principal → bouton **Réception** (ou carte dédiée).

URL directe : `/reception.html`

Historique des réceptions : `/receptions-historique.html`

---

## 3. Structure générale : le wizard en 5 étapes

La réception est guidée par un **wizard à 5 étapes** matérialisé par une barre de 5 points de progression en haut d'écran. Un bandeau `👤 [Prénom]` reste visible dès l'étape 1. La navigation arrière est possible jusqu'à l'étape 3 incluse (retour impossible une fois la fiche créée en base, mais la saisie reste modifiable).

| Dot | Étape | Titre |
|---|---|---|
| ● | 0 | Sélection de l'opérateur |
| ● | 1 | Contrôle camion |
| ● | 2 | Bon de livraison & Fournisseur |
| ● | 3 | Saisie des produits (boucle) |
| ● | 4 | Récapitulatif & Clôture |

---

## 4. Mode d'emploi pas-à-pas

### 4.1 Étape 0 — Qui réceptionne ?

L'écran affiche la grille des membres du personnel (prénoms uniquement). Appuyer sur un prénom pour le sélectionner.

**Ce qui se passe automatiquement :** la date du jour et l'heure courante sont pré-remplis dans les champs de l'étape suivante.

> Si aucun personnel n'est enregistré dans l'administration, le message "Aucun personnel enregistré." s'affiche et il est impossible de continuer.

---

### 4.2 Étape 1 — Contrôle du camion

| Champ | Obligatoire | Notes |
|---|---|---|
| **Date de réception** | Oui ✱ | Pré-remplie avec la date du jour. Ne peut pas être dans le passé. |
| **Heure de réception** | Non | Pré-remplie avec l'heure courante. |
| **Température du camion (°C)** | Oui ✱ | Saisie décimale (ex : `1.5`). Plage : −10 à 30°C. |
| **Propreté du camion** | Oui ✱ | Toggle : `✓ Satisfaisante` (défaut) / `✗ Non satisfaisante` |

#### Si "✗ Non satisfaisante" est sélectionné

Une section supplémentaire apparaît avec des cases à cocher :

- `Propreté / Insalubrité`
- `Tenue du livreur`
- `Marchandise sale ou abîmée`
- `Palette cassée / instable`

Une zone photo **"Photo du problème"** s'affiche :
- Si **aucune case n'est cochée** → la photo est **obligatoire** (mention "Obligatoire si rien n'est coché").
- Si au moins une case est cochée → la photo devient **optionnelle** (mention "Optionnel").

#### Badge "Conformité camion"

- `— Non évalué` : température non saisie
- `✓ Conforme` : propreté satisfaisante (la T° camion seule ne crée PAS de non-conformité à cette étape)
- `✗ Propreté non satisfaisante` : propreté déclarée non satisfaisante

#### Bouton "Suivant →"

- Si date passée → le champ Date est mis en évidence, navigation bloquée.
- Si température vide → la validation native du navigateur s'active.
- Si propreté NC → **Dialog "Accepter la livraison ?"** s'affiche :
  - **`✓ Oui — Accepter`** : continue vers l'étape 2 normalement.
  - **`✗ Non — Refuser`** : déclenche le **flux de refus de livraison** (voir section 4.2.1).

#### 4.2.1 Flux refus de livraison (cas exceptionnel)

Un dialog **"Refus de livraison"** s'ouvre. Pour chaque bon de livraison refusé, l'opérateur doit fournir :
- **Photo du bon de livraison** (obligatoire, prise par l'appareil photo du tablet)
- **Nom du fournisseur** (recherche dans la liste ou saisie libre — obligatoire)

Bouton **`+ Ajouter un autre bon de livraison`** : ajoute un bloc supplémentaire (un bloc par fournisseur différent).

Bouton **`Aller à PCR01 →`** : valide chaque bloc (photo + fournisseur requis pour chacun), crée la fiche de réception en base, puis redirige vers le formulaire PCR01.

---

### 4.3 Étape 2 — Bon de livraison & Fournisseur

#### Nombre de fournisseurs

Toggle : `Non — un seul` (défaut) / `Oui — plusieurs`

**Mode un seul fournisseur** : un seul bloc photo + fournisseur.

**Mode plusieurs fournisseurs** : autant de blocs que nécessaire. Bouton **`+ Ajouter un fournisseur`** pour ajouter. Chaque bloc a son propre BL et son propre fournisseur.

#### Pour chaque fournisseur

| Élément | Obligatoire | Notes |
|---|---|---|
| **Photo du bon de livraison** | Oui ✱ | Appuyer sur la zone `📋` pour déclencher l'appareil photo. |
| **Nom du fournisseur** | Oui ✱ | Champ de recherche avec autocomplete. Sélectionner dans la liste ou saisir un nom libre. |

> Dès qu'un fournisseur est sélectionné dans la liste, son nom s'affiche dans une pastille verte avec un bouton `✕` pour effacer et recommencer.

#### Bouton "Créer la fiche →"

Valide et envoie au serveur : crée la fiche de réception (statut `en_cours`) et passe à l'étape 3. **La fiche est maintenant enregistrée en base de données.** Si l'on revient en arrière puis reclique sur "Créer la fiche", aucune duplication n'est créée.

---

### 4.4 Étape 3 — Saisie des produits (boucle)

Cette étape est répétée autant de fois que nécessaire. Le compteur **"Produits ajoutés : N"** se met à jour à chaque ajout.

#### Partie haute — Liste des produits déjà ajoutés

Chaque produit ajouté apparaît sous forme de carte avec :
- Nom du produit, fournisseur, température, N° de lot
- Badge `✓ OK` ou `✗ NC`
- Bouton `✎ Modifier` pour ré-ouvrir le formulaire en mode édition

#### Partie basse — Formulaire d'ajout

| Champ | Obligatoire | Notes |
|---|---|---|
| **Fournisseur** | Non (visible seulement en mode multi, si ≥2 fournisseurs) | Menu déroulant des fournisseurs de l'étape 2. |
| **Produit** | Oui ✱ | Champ de recherche avec autocomplete (produits de type "brut" uniquement). Synonymes reconnus : bœuf/bovin → VB, agneau/mouton/ovin → AGN, veau → VX, porc/cochon → PC. |
| **N° de lot fournisseur** | Oui ✱ | Saisie manuelle. OU cliquer **"Pas de N° de lot"** pour générer un lot interne automatique. |
| **DLC / DLUO** | Oui ✱ | Toggle `DLC` / `DLUO`. Date saisie, ne peut pas être dans le passé. |
| **Couleur** | Oui | Toggle `✓ Conforme` (défaut) / `✗ NC`. Si NC → champ observation visible. |
| **Consistance** | Oui | Toggle `✓ Conforme` (défaut) / `✗ NC`. Si NC → champ observation visible. |
| **Exsudat** | Oui | Toggle `✓ Conforme` (défaut) / `✗ NC`. Si NC → champ observation visible. |
| **Odeur** | Oui | Toggle `✓ Conforme` (défaut) / `✗ NC`. Si NC → champ observation visible. |
| **pH** | Non | Valeur décimale 0–14. Plage normale affichée selon l'espèce. |

> **Aide visuelle** : dès qu'un produit est sélectionné, chaque critère affiche la norme de l'espèce (ex : *Normal : Rouge vif* pour la couleur du boeuf). Cette aide provient du référentiel espèces intégré (Boeuf, Veau, Porc, Agneau, Volaille, Gibier, Cheval).

#### Fonctionnement de la génération de lot interne

Cliquer **"Pas de N° de lot"** appelle l'API `/api/receptions/{id}/lot-interne?code_unique=...` et génère un numéro au format **`{CODE}-YYYYMMDD-{incr}`** (ex : `VB-20260514-001`). Le champ passe en lecture seule avec fond vert clair. Cliquer **"↺ Saisie manuelle"** pour annuler et revenir à la saisie libre.

#### Bouton "+ Ajouter"

Actif seulement si : produit sélectionné **ET** lot renseigné **ET** DLC/DLUO renseignée et non passée. Si on appuie sur la zone du bouton grisé, les champs manquants sont mis en évidence.

#### Bouton "✓ Enregistrer"

Visible uniquement en mode édition (remplacement du bouton "+ Ajouter"). Envoie une requête PUT pour modifier la ligne existante.

#### Bouton "Récap →"

Actif dès qu'au moins 1 produit a été ajouté. Passe à l'étape 4.

#### Dialog "Même fournisseur ?"

En mode multi-fournisseur, après chaque ajout de produit, un dialog s'affiche : *"Même fournisseur que le produit précédent ? (NomFournisseur)"*. Répondre `Oui` pré-sélectionne le même fournisseur pour le produit suivant.

---

### 4.5 Étape 4 — Récapitulatif & Clôture

#### Bloc "Camion"

Affiche la température et la propreté enregistrées, avec un badge `✓ Conforme` ou `✗ Propreté NC`.

#### Conformité globale

Affichage calculé avant clôture :
- `✓ Tout conforme` : tous les produits sont conformes ET la propreté camion est satisfaisante.
- `✗ Présence de non-conformité(s)` : au moins un produit NC ou propreté NC.

#### Liste des produits réceptionnés

Chaque produit affiche son nom, son fournisseur, sa température, son lot, et un badge `✓ OK` ou `✗ NC`.

#### Procédure NC (visible uniquement si des produits sont NC)

Si des produits ont au moins un critère non conforme, la section **Procédure NC** s'affiche et le bouton **"✔ Clôturer la fiche"** est bloqué tant que la procédure n'est pas complétée.

##### Sous-étape A : Contrôle à cœur *(Étape 1/3)*

Pour chaque produit NC, saisir la **température à cœur** mesurée. Le badge se met à jour instantanément :
- `✓ Conforme après contrôle` : T°cœur ≤ borne_max du produit + 1°C
- `✗ Non conforme confirmé` : T°cœur dépasse le seuil

Une fois tous les produits NC renseignés, le bouton **"Suivant →"** s'active.
- Si tous les produits sont conformes après contrôle à cœur → le bouton devient **"Clôturer →"** et la clôture est débloquée directement.
- Si des produits restent NC → passage à la sous-étape B.

##### Sous-étape B : Le livreur est encore là ? *(Étape 2/3)*

Deux boutons : **`✔ Oui, il est là`** / **`✕ Non, il est parti`**.

Dès qu'une réponse est sélectionnée, le bouton **`Remplir fiche PCR01 →`** s'active. Cliquer dessus sauvegarde l'état complet du wizard en `sessionStorage` et redirige vers `/pcr01.html`. Au retour depuis PCR01, le badge **`✓ Fiches PCR01 enregistrées`** s'affiche et la clôture est débloquée.

#### Champ "Commentaire / non-conformité"

Zone de texte libre pour décrire les non-conformités ou ajouter une remarque.

#### Bouton "✔ Clôturer la fiche"

- Bloqué si la procédure NC n'est pas complétée.
- Cliquer → envoie PUT `/api/receptions/{id}/cloturer` → la fiche passe au statut `cloturee`.

---

### 4.6 Écran de confirmation

Après clôture réussie :
- ✅ **"Réception enregistrée"**
- Détail de la réception et badge de conformité globale
- Countdown : retour automatique au Hub après 5 secondes
- Bouton **`← Retour au menu`** pour revenir immédiatement

---

## 5. Règles de conformité invisibles

### 5.1 Conformité température produit

La **température du camion** est utilisée comme température de réception de chaque produit. La conformité est calculée par rapport à la plage `temperature_conservation` du produit avec une **tolérance de ±1°C sur chaque borne** :

| Résultat | Condition | Badge |
|---|---|---|
| Conforme | Borne_min − 1°C ≤ T° ≤ Borne_max + 1°C | `✓ Conforme` |
| NON CONFORME | T° ≥ Borne_max + 1°C | `✗ NC — température` |
| Attention | T° < Borne_min − 1°C | Temperature basse |

Exemple pour un produit conservé à `0°C à +4°C` : NC si T° ≥ 5°C, attention si T° < −1°C.

> **Important** : La T° camion saisie à l'étape 1 ne génère PAS de non-conformité camion directe. Elle influe sur la conformité de chaque ligne produit à l'étape 3.

### 5.2 Recalcul automatique en cas de modification de T° camion

Si l'opérateur retourne à l'étape 1 et modifie la température du camion **après** avoir créé la fiche, le système envoie automatiquement un PUT `/api/receptions/{id}/temperature-camion` qui **recalcule la conformité de toutes les lignes produits** déjà enregistrées. Les badges NC/OK de la liste sont mis à jour.

### 5.3 Conformité à cœur

À l'étape 4, le seuil de conformité à cœur est identique à la tolérance camion : **T°cœur ≤ borne_max + 1°C** (ex. ≤ 5°C pour un produit à `0-4°C`). Passer le contrôle à cœur peut "lever" une NC initiale due à la température.

### 5.4 Critères visuels : référentiel espèces

Le système contient un référentiel intégré pour 7 espèces : **Boeuf, Veau, Porc, Agneau, Volaille, Gibier, Cheval**. Pour chaque espèce, les normes attendues pour couleur, consistance, exsudat, odeur et pH sont affichées sous les toggles lors de la saisie.

| Espèce | Couleur normale | pH normal |
|---|---|---|
| Boeuf | Rouge vif | 5.5 – 5.7 |
| Veau | Rose pâle à rose vif | 5.5 – 5.7 |
| Porc | Rose pâle | 5.5 – 5.7 |
| Agneau | Rouge rosé | 5.5 – 5.7 |
| Volaille | Chair blanche à jaune pâle | 5.5 – 5.7 |
| Gibier | Rouge foncé à bordeaux | 5.5 – 5.7 |
| Cheval | Rouge foncé | 5.5 – 5.7 |

### 5.5 Compression automatique des photos

Toutes les photos (BL, propreté NC) sont automatiquement :
1. Réorientées selon les métadonnées EXIF (correction rotation tablette)
2. Redimensionnées à maximum 1280 pixels de côté
3. Converties en JPEG qualité 80%
4. Stockées dans `data/photos/bons_livraison/` ou `data/photos/proprete_camion/`

### 5.6 Autocomplete produits avec synonymes

La recherche produit à l'étape 3 reconnaît des synonymes courants :

| Terme saisi | Code cherché |
|---|---|
| bœuf, boeuf, bovin | VB |
| agneau, mouton, ovin | AGN |
| veau | VX |
| porc, cochon, porcin | PC |

Les mots vides (`de`, `du`, `la`, `le`, etc.) sont ignorés lors de la recherche.

---

## 6. Comportements de sécurité UX

### 6.1 Inactivité 5 minutes

Si aucune interaction pendant **5 minutes** :
- Si des produits ont été ajoutés mais la fiche n'est pas clôturée → Dialog **"Session inactive"** avec les boutons `Continuer` et `Quitter`.
- Sinon → redirection automatique vers le Hub sans dialog.

### 6.2 Anti-crash sessionStorage

Avant toute redirection vers PCR01 (`/pcr01.html`), l'état complet du wizard (receptionId, personnelId, personnelPrenom, fournisseurId, lignesAjoutees, tempCamion, propreteCamion) est sauvegardé en `sessionStorage`. Au retour de PCR01, le wizard reprend exactement à l'étape 4 avec toutes les données intactes.

### 6.3 Horloge temps réel

L'heure courante est affichée dans l'en-tête et se met à jour toutes les secondes (format HH:MM).

---

## 7. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Date de réception dans le passé | Champ date mis en rouge, navigation "Suivant" bloquée |
| Température camion vide | Validation native navigateur, focus sur le champ |
| Propreté NC + aucune case cochée + pas de photo | Zone photo mise en évidence (contour rouge), scroll vers la zone |
| Fournisseur non renseigné (étape 2) | Champ mis en rouge, message : *"Le nom du fournisseur est obligatoire."* |
| Photo BL manquante (étape 2) | Zone photo mise en évidence, message : *"La photo du bon de livraison est obligatoire."* |
| Fournisseur N+1 (mode multi) manquant | Message : *"Le nom du fournisseur 2 est obligatoire."* etc. |
| Produit non sélectionné (bouton "+ Ajouter" cliqué) | Champ recherche mis en évidence, tooltip : *"Sélectionnez un produit dans la liste"* |
| N° de lot vide | Champ lot mis en évidence, tooltip : *"Saisissez un N° de lot ou cliquez 'Pas de N° de lot'"* |
| DLC passée ou vide | Champ DLC mis en évidence, tooltip : *"La DLC ne peut pas être dans le passé"* ou *"La DLC/DLUO est obligatoire"* |
| Erreur serveur lors de la création de la fiche | Message en rouge sous le formulaire : *"Erreur : [détail]"* |
| Personnel introuvable en base | Chargement échoue, message dans la grille |
| Refus livraison multi-BL : photo ou fournisseur manquant | Message : *"⚠️ Manquant : photo du bon de livraison et/ou nom du fournisseur. Chaque BL doit avoir une photo ET un fournisseur."* |

---

[Passer au module suivant : Étiquettes & Traçabilité DLC](03_etiquettes.md)

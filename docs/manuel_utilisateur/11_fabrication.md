# Module 11 — Fabrication & Recettes

---

## 1. Objectif

Ce module couvre deux fonctions complémentaires :
- **Administration des recettes** (`/admin-recettes.html`) : création et modification des fiches recettes avec la liste des ingrédients et leur rendement de base — réservé aux responsables.
- **Wizard de fabrication** (`/etiquettes.html`) : utilisation quotidienne pour produire selon une recette avec traçabilité FIFO complète — déjà documenté au [Module 3](03_etiquettes.md).

Ce chapitre documente exclusivement la page **Gestion des Recettes**.

---

## 2. Chemins d'accès

| Page | URL | Accès |
|---|---|---|
| **Créer une recette** | `/admin-recettes.html` | Hub → Production → FABRICATION → bouton **✏️ Gérer les recettes** → **+ Créer une nouvelle recette** |
| **Modifier une recette** | `/admin-recettes.html?id=XXX` | Hub → Production → FABRICATION → bouton **✏️ Gérer les recettes** → clic sur une recette existante |

---

## 3. Architecture de la page

La page est structurée en 3 sections verticales :

1. **Informations générales** : nom, produit fini, DLC, rendement
2. **Ingrédients** : tableau + formulaire d'ajout
3. **Validation** : bouton "Enregistrer la recette"

En mode **édition** (`?id=XXX`) : le titre de la page devient `Modifier : [Nom recette]` et le bouton devient `✓ Mettre à jour la recette`.

---

## 4. Section 1 — Informations générales

### 4.1 Champs

| Champ | Obligatoire | Notes |
|---|---|---|
| **Nom de la recette** | Oui ✱ | Texte libre. Auto-rempli avec le nom du produit fini si laissé vide lors de la sélection du produit. |
| **Produit fini associé** | Oui ✱ | Autocomplete sur le catalogue — sélection obligatoire dans la liste. Affiche un tag `[Nom] (code)` avec bouton `✕` pour effacer. |
| **DLC (en jours)** | Oui | **Verrouillée à 3 jours** — champ en lecture seule, non modifiable. |
| **Rendement de base** | Non | Quantité + unité (`kg` / `L` / `pièces`). Exemple : `1 kg`. Utilisé par le calculateur de production dans le wizard. |

### 4.2 Après sélection du produit fini

Un encart de détails apparaît sous le champ avec : Catégorie, Destination, Température de conservation du produit fini sélectionné.

---

## 5. Section 2 — Ingrédients

### 5.1 Tableau des ingrédients

Colonnes : **Ingrédient** · **Quantité** · **Unité** · **%** · (Supprimer)

- La colonne **%** affiche la proportion pondérale de chaque ingrédient en temps réel (calculée en convertissant toutes les quantités en kg : `kg=1, L=1, g=0,001, ml=0,001`). Les unités non convertibles (pièce…) affichent `—`.
- **Cliquer sur une ligne** ouvre la modale de modification (quantité + unité uniquement — le nom de l'ingrédient ne peut pas être changé).
- **Bouton `✕`** en fin de ligne : supprime immédiatement l'ingrédient de la liste.

> En mode édition : la suppression d'un ingrédient **déjà utilisé dans une fabrication** est bloquée par le serveur (HTTP 409) pour préserver la traçabilité HACCP.

### 5.2 Formulaire d'ajout d'ingrédient

| Champ | Notes |
|---|---|
| **Produit** | Autocomplete sur le catalogue. Saisie libre autorisée (ingrédient inconnu). |
| **Quantité** | Décimale > 0. Valider avec la touche `Entrée`. |
| **Unité** | `kg` · `g` · `L` · `pièce`. Défaut : `g`. |

Bouton **`+ Ajouter cet ingrédient`** ou `Entrée` depuis le champ quantité.

**Deux cas de figure :**

| Situation | Ce qui se passe |
|---|---|
| Produit sélectionné depuis l'autocomplete (ID connu) | Ingrédient ajouté directement au tableau |
| Texte libre saisi sans sélection (pas d'ID) | **Modale "Nouvel ingrédient"** s'ouvre (voir section 6) |

---

## 6. Modale "Nouvel ingrédient" — Créer un produit à la volée

S'ouvre automatiquement quand l'opérateur saisit un nom d'ingrédient qui n'existe pas dans le catalogue.

Le produit sera créé en base de données lors de l'enregistrement de la recette.

### Champs de la modale

| Champ | Obligatoire | Notes |
|---|---|---|
| **Nom** | — | Pré-rempli depuis la saisie libre (lecture seule) |
| **Code unique** | — | Généré automatiquement (lecture seule) selon espèce + séquence |
| **Catégorie** | Oui ✱ | `Matière première` · `Viande hachée` · `Pièces de viande` · `Préparation crue` · `Charcuterie` · `Traiteur` |
| **Espèce** | Oui ✱ | 11 espèces disponibles (mêmes que le Catalogue) |
| **Abats** | Non | Case à cocher — modifie le préfixe du code (ex. VBA au lieu de VB) |
| **Niveau de coupe** | Non | Texte libre (ex. : entier, demi, pavé…) |
| **Étape** | Non | Numérique entier |
| **Conditionnement** | Non | `SOUS_VIDE` (défaut) · `VRAC` · `CARTON` · `BARQUETTE` · `AUTRE` |
| **Type produit** | Non | `Brut` (défaut) · `Fini` |
| **DLC en jours** | Non | Défaut : `0` (sans DLC) |
| **Température de conservation** | Oui ✱ | `Ambiant` (défaut) · `+4°C` · `-18°C` · `+2°C / +4°C` |

Bouton **`+ Ajouter l'ingrédient`** : valide et ajoute l'ingrédient au tableau (marqué `nouveau` en badge).  
Bouton **`Annuler`** : ferme sans ajouter.

> L'espèce est **obligatoire** : si elle n'est pas sélectionnée, le champ clignote en rouge pendant 2 secondes.

---

## 7. Modale "Modifier l'ingrédient"

Ouverte par clic sur une ligne du tableau. Permet de modifier uniquement :
- **Quantité** (décimale > 0)
- **Unité** (même liste que l'ajout)

Le nom de l'ingrédient est affiché en lecture seule.

Bouton **`✓ Enregistrer`** ou `Entrée` depuis le champ quantité.

---

## 8. Bouton "Enregistrer la recette"

### Validations avant envoi

| Condition | Message |
|---|---|
| Nom de recette vide | *"Le nom de la recette est obligatoire."* |
| Produit fini non sélectionné | *"Sélectionnez un produit fini associé."* |
| Aucun ingrédient | *"Ajoutez au moins un ingrédient avant d'enregistrer."* |

### Processus en 2 étapes

**Étape 1 — Création silencieuse des ingrédients libres :**  
Pour chaque ingrédient marqué `nouveau` (sans ID catalogue), le système appelle silencieusement `POST /api/produits` pour le créer dans le catalogue. Le code unique est **régénéré à cet instant** (pour tenir compte des produits créés entre-temps). Si la création échoue, une erreur est affichée et la recette n'est pas sauvegardée.

**Étape 2 — Sauvegarde de la recette :**  
`POST /api/recettes` (création) ou `PUT /api/recettes/{id}` (modification).

### Stockage du rendement

Le rendement est stocké dans le champ `instructions` de la recette sous la forme :
```
Base pour X unite.

[autres instructions…]
```
Cette convention est lue par le wizard de fabrication pour calculer les quantités proportionnelles.

### Résultat

- **Création** : toast de succès + formulaire réinitialisé
- **Édition** : toast de succès + tableau des ingrédients rechargé avec les IDs à jour (pour permettre une seconde sauvegarde cohérente)

---

## 9. Règles de conformité invisibles

### 9.1 DLC verrouillée à 3 jours

La DLC des recettes est **fixée à 3 jours** dans le code JS (`const dlcJours = 3`) et dans le HTML (champs `min=3`, `max=3`, `readonly`). Elle correspond à `DLC_JOURS_TRANSFORMATION` dans la base, la règle HACCP non modifiable pour les produits transformés. Le produit fini associé peut avoir une DLC différente dans son fiche catalogue — elle ne sert pas ici.

### 9.2 Protection des ingrédients utilisés

En mode édition, le backend vérifie si un ingrédient supprimé est référencé dans une fabrication existante (`fabrication_lots`). Si oui, HTTP 409 :  
*"Impossible de retirer l'ingrédient « [Nom] » : il est utilisé dans une fabrication existante (traçabilité HACCP)."*

Conséquence : on peut modifier la quantité ou l'unité d'un ingrédient (via la modale d'édition), mais pas le supprimer s'il a déjà été utilisé en production.

### 9.3 Critères d'éligibilité FIFO

Les lots éligibles à la sélection FIFO lors d'une fabrication doivent satisfaire **toutes** ces conditions :

| Critère | Raison d'exclusion si non respecté |
|---|---|
| Réception `statut = cloturee` | `statut_non_cloture` |
| Ligne de réception `conforme = 1` | `non_conforme` |
| Livraison non refusée | `livraison_refusee` |
| DLC non dépassée (ou sans DLC) | `perime` |
| Pas d'entrée `dlc_devenir` | `dlc_devenir_existe` |

Un lot passant tous ces critères est `eligible_fifo`. Ces raisons d'exclusion sont consultables via le endpoint de diagnostic `/api/fabrications/debug-fifo/{produit_id}`.

### 9.4 Format du lot interne de fabrication

Chaque fabrication enregistrée génère un numéro de lot interne au format : **`MC-YYYYMMDD-XXXX`** (ex. : `MC-20260514-0001`). Ce numéro apparaît sur le ticket thermique imprimé et reste lié à la fabrication dans l'historique.

### 9.5 DLC de fabrication = min(DLC théorique, DLC ingrédients)

Lors d'une fabrication dans le wizard, la DLC du produit fini est calculée comme le **minimum** entre :
- `date_fabrication + 3j` (DLC théorique HACCP)
- La DLC la plus proche parmi tous les lots FIFO utilisés

Si la DLC est réduite à cause d'un ingrédient limitant, un toast d'alerte orange est affiché dans le wizard.

---

## 10. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Espèce non sélectionnée dans "Nouvel ingrédient" | Champ flashe rouge 2s, message : *"Sélectionnez une espèce."* |
| Quantité ≤ 0 lors de l'ajout | Champ flashe rouge 2s, message : *"Saisissez une quantité valide."* |
| Création d'ingrédient libre échouée (étape 1) | Message : *"Création "[nom]" : [détail erreur]"* — recette non sauvegardée |
| Tentative de suppression d'un ingrédient en usage (étape 2) | HTTP 409 affiché comme message d'erreur |
| Recette non trouvée (mode édition) | Message d'erreur, page inutilisable |
| Chargement produits échoué | Message : *"Impossible de charger la liste des produits."* |

---

[Passer au module suivant : Stock Unifié FIFO](12_stock.md)

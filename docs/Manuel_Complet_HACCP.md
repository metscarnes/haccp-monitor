# Module 1 — Catalogue Produits

---

## 1. Objectif

Le Catalogue Produits est le référentiel central de HACCP Monitor. Il répertorie toutes les **matières premières** (viandes, produits bruts reçus de fournisseurs) et les **produits finis** (préparations maison, charcuteries, plats traiteur). Chaque produit défini ici devient disponible dans tous les autres modules : réception, étiquetage, cuisson, fabrication, gestion DLC, stock.

Un produit incomplet (sans code unique, sans catégorie ou sans DLC) est signalé visuellement afin de garantir la traçabilité complète.

---

## 2. Chemin d'accès

Depuis le Hub principal → bouton ou carte **📚 Catalogue produits**.

URL directe : `/catalogue.html`

---

## 3. Interface — Vue tableau

### 3.1 Barre d'en-tête

| Élément | Libellé exact | Rôle |
|---|---|---|
| Lien retour | `← Accueil` | Retour au Hub |
| Titre | `📚 Catalogue produits` | Identification de la page |
| Bouton | `+ Nouveau` | Ouvre la modale de création |
| Bouton | `📥 Importer Excel` | Ouvre la modale d'import en masse |
| Lien | `📤 Exporter Excel` | Télécharge immédiatement le fichier Excel du catalogue complet |

### 3.2 Bandeau de statistiques

Cinq compteurs mis à jour à chaque chargement :

| Compteur | Couleur | Ce qu'il affiche |
|---|---|---|
| **Total** | Neutre | Nombre total de produits (actifs + archivés) |
| **Bruts** | Vert | Produits actifs de type "brut" |
| **Finis** | Bleu | Produits actifs de type "fini" |
| **Archivés** | Gris | Produits désactivés (soft-delete) |
| **Incomplets** | Orange/alerte | Produits actifs sans code unique, sans catégorie OU sans DLC |

### 3.3 Filtres

Tous les filtres s'appliquent **instantanément** (sans rechargement de page). Le compteur `X / Y` en bas à droite indique le nombre de lignes affichées sur le total chargé.

| Filtre | Identifiant | Valeurs possibles |
|---|---|---|
| **Recherche** | Champ texte libre | Cherche dans : nom, code unique, espèce, catégorie, coupe |
| **Type** | Menu déroulant | Tous / Brut / Fini |
| **Catégorie** | Menu déroulant | Toutes + catégories présentes dans la base |
| **Conditionnement** | Menu déroulant | Tous + conditionnements présents dans la base |
| **Voir archivés** | Case à cocher | Si cochée, recharge la liste depuis le serveur en incluant les archivés |
| **Incomplets uniquement** | Case à cocher | N'affiche que les produits sans code unique, catégorie ou DLC |

> **Important** : Cocher ou décocher "Voir archivés" déclenche un nouvel appel API et recharge complètement la liste.

### 3.4 Colonnes du tableau

| Colonne | Contenu |
|---|---|
| **Nom** | Nom commercial du produit |
| **Code** | Code unique (`VB1`, `PC3`…), affiché en monospace |
| **Catégorie** | Catégorie réglementaire |
| **Type** | `brut` ou `fini` |
| **Cond.** | Conditionnement (`SOUS_VIDE`, `VRAC`…) |
| **DLC (j)** | Durée de vie en jours après réception/fabrication |
| **Temp.** | Température de conservation |
| **Statut** | Badge coloré : **Actif** (vert) / **Archivé** (gris) / **Incomplet** (orange) |
| **Actions** | Bouton `✎ Éditer` qui ouvre la modale d'édition |

---

## 4. Mode d'emploi pas-à-pas

### 4.1 Créer un nouveau produit

1. Cliquer sur **`+ Nouveau`** dans la barre d'en-tête.
2. La modale **"Nouveau produit"** s'ouvre. Le curseur se place automatiquement sur le champ **Nom**.
3. Remplir les champs (voir détail section 5).
4. Sélectionner une **Espèce** → le champ **Code unique** se remplit automatiquement.
5. Cliquer sur **`Enregistrer`**.
6. La modale se ferme et le tableau se recharge automatiquement.

### 4.2 Modifier un produit existant

1. Repérer le produit dans le tableau.
2. Cliquer sur **`✎ Éditer`** dans la colonne Actions.
3. La modale **"Édition : [Nom du produit]"** s'ouvre avec les valeurs actuelles pré-remplies.
4. Modifier les champs souhaités.
5. Cliquer sur **`Enregistrer`**.

> **Note** : En mode édition, le Code unique est modifiable manuellement (il n'est PAS régénéré automatiquement si vous changez l'espèce).

### 4.3 Archiver un produit

1. Ouvrir la modale d'édition du produit (bouton `✎ Éditer`).
2. Cliquer sur le bouton rouge **`🗑 Archiver`** (visible uniquement si le produit est actif).
3. Une confirmation apparaît : *"Archiver ce produit ? Il restera lié aux historiques mais ne sera plus proposé."*
4. Confirmer → le produit passe en statut **Archivé**, il disparaît des listes de travail mais conserve tout son historique.

> Le bouton **`🗑 Archiver`** n'apparaît PAS si le produit est déjà archivé.

### 4.4 Exporter le catalogue en Excel

Cliquer directement sur **`📤 Exporter Excel`** dans la barre d'en-tête. Le navigateur télécharge immédiatement un fichier nommé `catalogue_produits_YYYY-MM-DD.xlsx` contenant toutes les colonnes du catalogue (produits actifs et archivés).

### 4.5 Importer des produits depuis Excel

1. Cliquer sur **`📥 Importer Excel`**.
2. La modale d'import s'ouvre.
3. (Optionnel) Cliquer sur **`📥 Télécharger le modèle Excel`** pour obtenir un fichier vierge avec les bonnes colonnes et une ligne exemple.
4. Sélectionner votre fichier `.xlsx` via le champ **"Fichier .xlsx"**.
5. Choisir le **Mode** d'import (voir section 7).
6. Cliquer sur **`Lancer l'import`**.
7. Le résultat s'affiche dans la modale : nombre de produits créés, mis à jour, ignorés, et liste des erreurs éventuelles.

---

## 5. Détail des champs de la modale création/édition

| Champ | Obligatoire | Valeurs / format | Notes |
|---|---|---|---|
| **Nom** | Oui ✱ | Texte libre, ≥ 1 caractère | Nom commercial affiché partout |
| **Code unique** | Non (auto) | Lecture seule en création | Généré automatiquement selon l'espèce ; voir section 6 |
| **Catégorie** | Oui ✱ | Menu déroulant (6 choix) | Voir valeurs ci-dessous |
| **Espèce** | Non | Menu déroulant (11 espèces) | Détermine le préfixe du code unique |
| **Abats** | Non | Case à cocher | Modifie le préfixe du code unique (ex. VBA au lieu de VB) |
| **Conditionnement** | Non | Menu déroulant (5 choix) | Défaut : `SOUS_VIDE` |
| **Type produit** | Non | Menu déroulant : Brut / Fini | Défaut : `Brut` |
| **DLC (jours)** | Non | Nombre entier ≥ 0 | Défaut : `0` — À renseigner pour activer les alertes DLC |
| **Température conservation** | Non | Menu déroulant (4 choix) | Défaut : `0°C à +4°C` |
| **Actif (non archivé)** | Non | Case à cocher | Cochée par défaut — décocher = archivage immédiat |

### Catégories disponibles

| Valeur interne | Libellé affiché |
|---|---|
| `matiere_premiere` | Matière première |
| `viande_hachee` | Viande hachée |
| `viande_pieces` | Pièces de viande |
| `preparation_crue` | Préparation crue |
| `charcuterie` | Charcuterie |
| `traiteur` | Traiteur |

### Températures de conservation disponibles

| Valeur |
|---|
| `0°C à +4°C` (réfrigéré) — défaut |
| `+2°C / +4°C` (viande fraîche) |
| `-18°C` (congelé) |
| `Ambiant` |

### Conditionnements disponibles

`SOUS_VIDE` · `VRAC` · `CARTON` · `BARQUETTE` · `AUTRE`

---

## 6. Règles de conformité invisibles

### 6.1 Génération automatique du code unique

Le code est généré **uniquement lors de la création** d'un produit. Il ne se régénère pas en mode édition.

La règle de construction est : **préfixe espèce + numéro séquentiel**.

Le préfixe est déterminé selon le tableau suivant :

| Espèce | Préfixe normal | Préfixe si "Abats" coché |
|---|---|---|
| Bovin | `VB` | `VBA` |
| Veau | `VX` | `VXAB` |
| Agneau / ovin | `AGN` | `AGNAB` |
| Porc | `PC` | `PACAB` |
| Gibier | `GIB` | *(pas d'abats)* |
| Volaille — canard | `VC` | *(pas d'abats)* |
| Volaille — dinde | `VD` | *(pas d'abats)* |
| Volaille — lapin | `VL` | *(pas d'abats)* |
| Volaille — autre | `VP` | *(pas d'abats)* |
| Cheval | `CH` | *(pas d'abats)* |
| Viande exotique | `VEXOA` | *(pas d'abats)* |

Le numéro séquentiel est calculé automatiquement : le système recherche le numéro le plus élevé déjà utilisé avec ce préfixe et ajoute 1. Exemple : si `VB3` existe déjà, le prochain code sera `VB4`.

> Si aucune espèce n'est sélectionnée, le champ code reste vide et affiche le placeholder *"sélectionnez une espèce…"*

### 6.2 Unicité du code unique

Le backend vérifie que le code unique n'est pas déjà utilisé par un autre produit. Si le code est dupliqué, la sauvegarde est bloquée avec un message d'erreur (code HTTP 409).

### 6.3 Archivage non destructif (soft delete)

Archiver un produit ne le supprime pas de la base de données : le champ `actif` passe à `0`. Toutes les réceptions, étiquettes, cuissons et fabrications liées à ce produit restent intactes et consultables dans les historiques.

### 6.4 Définition d'un produit "Incomplet"

Un produit actif est signalé **Incomplet** (badge orange) si l'une de ces trois conditions est vraie :
- `code_unique` est absent ou vide
- `categorie` est absente ou vide
- `dlc_jours` est absent, vide ou égal à `0`

Les produits incomplets peuvent être filtrés via la case **"Incomplets uniquement"** pour traitement rapide.

---

## 7. Import Excel — Règles et modes

### Format attendu du fichier

La **première ligne** doit contenir les en-têtes. La colonne **`nom`** est obligatoire. Les autres colonnes reconnues sont :

`code_unique` · `espece` · `conditionnement` · `categorie` · `dlc_jours` · `temperature_conservation` · `type_produit` · `actif`

Toute colonne non reconnue est ignorée silencieusement.

### Mode Fusionner (`merge`) — défaut recommandé

- Si un produit avec le même `code_unique` existe → il est **mis à jour**.
- Si le `code_unique` est nouveau ou absent → le produit est **créé**.
- Les produits non présents dans le fichier ne sont **pas touchés**.

### Mode Remplacer (`replace`)

- **Avant l'import** : tous les produits existants sont archivés (`actif = 0`).
- **Ensuite** : les produits du fichier sont importés comme de nouveaux produits.
- Utiliser avec précaution : tous les produits non inclus dans le fichier deviennent archivés.

### Règles de validation lors de l'import

| Champ | Règle |
|---|---|
| `nom` | Obligatoire. Ligne ignorée si absent. |
| `dlc_jours` | Doit être un entier. Si invalide, erreur signalée pour la ligne. |
| `actif` | Accepte : `1`, `true`, `oui`, `yes`, `vrai` (insensible à la casse). |
| `categorie` | Si absent dans le fichier, défaut = `matiere_premiere`. |

Le résultat de l'import affiche :
- **Mode** utilisé
- **Créés** : nombre de nouveaux produits
- **Mis à jour** : nombre de produits modifiés
- **Ignorés** : lignes sans nom
- **Erreurs** : liste des lignes en erreur (max 10 affichées + compteur du reste)

---

## 8. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Champ **Nom** vide à la soumission | Message sous le formulaire : *"Le nom est obligatoire"* — sauvegarde bloquée |
| Champ **Catégorie** non sélectionné | Message : *"La catégorie est obligatoire"* — sauvegarde bloquée |
| **Code unique** déjà utilisé par un autre produit | Message retourné par le serveur : *"Code unique 'XXX' déjà utilisé"* — sauvegarde bloquée |
| Produit non trouvé (édition) | Message serveur : *"Produit non trouvé"* |
| Import sans fichier sélectionné | Message dans la modale : *"Choisissez un fichier .xlsx"* |
| Fichier Excel corrompu ou invalide | Message : *"Fichier Excel invalide : [détail technique]"* |
| Fichier Excel vide | Message : *"Fichier vide"* |
| Colonne `nom` absente du fichier | Message : *"Colonne 'nom' obligatoire dans l'en-tête"* — import annulé |
| Erreur réseau | Message dans le tableau : *"Erreur : [détail]"* |
| Fermeture modale | Clic en dehors de la carte modale OU touche `Échap` |

---

## 9. Comportements UX spécifiques

- La **recherche textuelle** s'applique avec un délai de 120 ms après la dernière frappe (anti-rebond) pour éviter des rafraîchissements inutiles lors de la saisie.
- En mode création, le focus est automatiquement placé sur le champ **Nom** à l'ouverture de la modale.
- En mode édition, le focus est également placé sur le champ **Nom**.
- Le lien **`📤 Exporter Excel`** est un lien direct vers l'API (pas de modale) : le navigateur déclenche immédiatement le téléchargement.

---

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

# Module 3 — Fabrication & Étiquettes (Wizard Production)

> **Note de navigation** : Ce module est accessible depuis la page **Production Hub** sous la tuile intitulée **"FABRICATION — Étiquettes & traçabilité"**. L'URL de la page est `/etiquettes.html`.

---

## 1. Objectif

Ce module guide l'opérateur pas à pas dans la réalisation d'une fabrication maison : sélection de la recette, calcul automatique des quantités selon la production ciblée, affectation FIFO des lots de matières premières, puis enregistrement de la traçabilité et impression d'un ticket thermique (étiquette) au format Brother 62 mm contenant le nom du produit fini, son numéro de lot interne, sa DLC et la liste des ingrédients.

---

## 2. Chemin d'accès

Hub principal → tuile **Production** → tuile **🔪 FABRICATION** (Production Hub).

URL directe : `/etiquettes.html`

---

## 3. Structure générale : wizard 4 étapes

La fabrication est guidée par un wizard à **4 étapes** matérialisé par une barre de progression numérotée 1-2-3-4. Un bandeau affiche en permanence le nom de la recette sélectionnée et sa DLC de référence (dès l'étape 2).

| Dot | Étape | Titre |
|---|---|---|
| 1 | 1 | Choisir une recette |
| 2 | 2 | Calculateur de production |
| 3 | 3 | Traçabilité & Lots |
| 4 | 4 | Récapitulatif & Impression |

Navigation arrière disponible à toutes les étapes (bouton `←`). Depuis l'étape 1, le retour pointe vers `/production-hub.html`.

---

## 4. Mode d'emploi pas-à-pas

### 4.1 Étape 1 — Choisir une recette

L'écran affiche une **grille de tuiles**, une tuile par recette disponible. Chaque tuile indique :
- Icône 🍖
- Nom de la recette
- Badge `DLC J+X` (durée de vie du produit fini)

Un champ **"Filtrer les recettes…"** permet de réduire la grille en temps réel par nom.

Bouton **`✏️ Gérer les recettes`** (haut droite) : ouvre une modale de gestion permettant de :
- Chercher et ouvrir une recette existante (redirige vers `/admin-recettes.html?id=X`)
- Créer une nouvelle recette (redirige vers `/admin-recettes.html`)

**Cliquer sur une tuile** → charge les ingrédients de la recette et passe à l'étape 2.

---

### 4.2 Étape 2 — Calculateur de production

#### Champs

| Champ | Obligatoire | Notes |
|---|---|---|
| **Production ciblée du jour** | Oui ✱ si la recette a une base de rendement | Valeur décimale (ex : `4.5`). L'unité (kg, g, pièces…) s'affiche à droite. |

#### Fonctionnement du calcul

La recette peut inclure une **base de rendement** dans son champ Instructions, sous la forme `Base pour X kg`. Si cette base est présente :
- Saisir la production ciblée recalcule **en temps réel** toutes les quantités d'ingrédients proportionnellement :  `Quantité = (quantité_base ÷ rendement_base) × production_ciblée`
- L'info `Base recette : X kg` est affichée sous le champ.
- La production ciblée est **obligatoire** pour passer à l'étape 3.

Si **aucune base de rendement** n'est trouvée dans les instructions :
- Les quantités des ingrédients sont affichées telles quelles (valeurs fixes).
- La production ciblée n'est pas bloquante (le système utilise la somme des quantités de base comme fallback).
- L'avertissement `Aucune base de rendement trouvée — quantités fixes affichées.` est affiché.

#### Liste des ingrédients (lecture seule)

Chaque ingrédient est affiché avec son nom, sa quantité calculée et son unité. Les quantités se mettent à jour à chaque frappe.

Bouton **`Suivant →`** : charge les lots FIFO depuis le stock réel et passe à l'étape 3.

---

### 4.3 Étape 3 — Traçabilité & Lots

Cette étape affiche pour chaque ingrédient de la recette le **lot FIFO** à utiliser, pré-sélectionné automatiquement depuis le stock.

#### Affichage pour chaque ingrédient

**Lot FIFO disponible (ligne verte `✓`) :**
- Nom de l'ingrédient
- `Lot [numéro] | DLC [date]` ou `DLUO [date]`
- Bouton **`✏️ Personnaliser`** (clignotant si FIFO alternatif disponible) : ouvre la modale de substitution

**Lot manquant (ligne rouge `⚠`) :**
- Nom de l'ingrédient
- Bouton **`🔄 Remplacer`** (clignotant) : obligatoire avant de pouvoir valider

#### Modale de substitution / remplacement

S'ouvre au clic sur `✏️ Personnaliser` ou `🔄 Remplacer`. Affiche une **grille de tuiles produits** disponibles en stock réel (produits bruts uniquement).

**Tri et filtrage intelligent :**
- La recherche textuelle tient compte des codes d'espèce (`VB`, `VX`, `PC`, `AG`, `GI`) et de leurs synonymes (Bœuf/Bovin, Veau, Porc/Cochon, Agneau, Gibier/Cerf/Sanglier).
- Les produits dont le nom contient à la fois le muscle ET le code espèce sont affichés en priorité (score 1000).
- Ensuite : muscle seul (score 100) → code seul (score 10) → reste du stock.
- À l'intérieur de chaque groupe, tri par DLC ascendante (FIFO).

**Structure d'une tuile produit :**
- Badge `⭐ PRIORITÉ FIFO` sur la première tuile (DLC la plus urgente)
- Nom du produit, compteur de lots disponibles, N° de lot + DLC du lot le plus urgent
- Couleur d'urgence DLC : rouge (`≤ 2 jours`), orange (`≤ 5 jours`), gris (OK)
- Si plusieurs lots : flèche `▼` + dépliage de la zone de lots au clic

**Sélection d'un lot :**
- Tuile mono-lot → substitution directe
- Tuile multi-lots → cliquer la tuile pour dépiler `▼ / ▲`, puis cliquer le lot précis
- Si le produit sélectionné est différent de l'ingrédient d'origine → dialog de confirmation : *"Vous utilisez du "[NomProduit]" à la place du "[NomOriginal]". Confirmer ?"*

Après confirmation, la ligne revient en état `✓` avec le badge `→ NomProduit (substitut) | Lot … | DLC …`.

#### Bouton "Confirmer les lots →"

Actif **uniquement** si tous les ingrédients ont un lot assigné (aucune ligne `⚠` restante). Passe à l'étape 4.

---

### 4.4 Étape 4 — Récapitulatif & Impression

#### Affichage récapitulatif

| Élément | Contenu |
|---|---|
| Nom de la recette | Titre en haut |
| Date de fabrication | Date du jour formatée (ex : `lundi 14 mai 2026`) |
| Poids fabriqués | Production ciblée + unité |
| **DLC** | Date calculée selon règle HACCP (voir section 5) |
| Liste ingrédients & lots | Nom, quantité, N° de lot (+ mention "Substitut" si remplacement) |

> **Alerte DLC réduite** : si la DLC calculée est inférieure à `date + DLC_jours_recette` à cause d'un ingrédient limitant, un toast d'alerte orange s'affiche : *"⚠️ DLC réduite à [date] à cause de : [nom ingrédient]"*

#### Champs de saisie

| Champ | Obligatoire | Notes |
|---|---|---|
| **Opérateur** | Oui ✱ | Menu déroulant du personnel enregistré |

#### Bouton "🖨 Générer & imprimer"

1. Valide que l'opérateur est sélectionné (sinon : *"Veuillez sélectionner un opérateur."*)
2. Envoie `POST /api/fabrications` avec la recette, les lots, la DLC finale et le poids fabriqué
3. Génère un **numéro de lot interne** automatique (format `MC-YYYYMMDD-XXXX`)
4. Remplit le **gabarit d'impression thermique** (invisible à l'écran) avec toutes les données
5. Lance `window.print()` → impression sur l'imprimante Brother 62 mm

#### Écran de succès

Après impression :
- ✓ **"Fabrication enregistrée !"**
- N° de lot interne généré
- Trois boutons :
  - **`Même recette`** : repart à l'étape 2 avec la même recette (nouveau calcul)
  - **`Nouvelle fabrication`** : repart à l'étape 1 (état complet réinitialisé)
  - **`← Retour au hub production`** : retour immédiat
- Compte à rebours : retour automatique vers `/production-hub.html` après **20 secondes**

---

## 5. Contenu du ticket thermique imprimé (62 mm)

Le gabarit est formaté pour l'imprimante Brother en mode `62mm auto`, sans marges. Il contient dans l'ordre :

| Zone | Contenu |
|---|---|
| **En-tête** | Nom du produit fini (majuscules) + poids fabriqués |
| **DLC** | Date en grand format rouge (ex : `14/05/2026`) — encadrée |
| **Numéro de lot** | Format `Lot : MC-20260514-0001` — en pointillés |
| **Ingrédients & Lots** | Liste à puces : `Xkg NomIngrédient (L:XXXXX \| DLC:DD/MM/AA)` |
| **Pied** | `Fabriqué le DD/MM/YYYY par [Prénom opérateur]` |

---

## 6. Règles de conformité invisibles

### 6.1 Calcul de la DLC du produit fini (règle HACCP)

La DLC finale retenue est la **plus courte** entre :
- **DLC théorique** : date du jour + `dlc_jours` de la recette
- **DLC minimale des ingrédients** : la DLC la plus proche parmi tous les lots FIFO utilisés

> Si un ingrédient expire dans 2 jours alors que la recette prévoit J+7, la DLC du produit fini sera le surlendemain, pas J+7.

Cette règle garantit que le produit fini n'a jamais une DLC supérieure à la DLC des ingrédients qui le composent.

### 6.2 Sélection FIFO

À l'étape 3, le système charge les lots via `/api/fabrications/fifo-lots?recette_id=X`. Pour chaque ingrédient, le lot retenu par défaut est :
1. DLC ascendante (lot le plus proche d'expiration en premier)
2. Date de réception ascendante (à DLC égale, le plus ancien arrivé en premier)

Les lots exclus de la sélection FIFO :
- DLC dépassée
- Lot ayant un enregistrement `dlc_devenir` (déjà utilisé/jeté)
- Livraisons non conformes ou refusées

### 6.3 Substitution : exclusion du lot courant

Dans la modale de substitution, le lot FIFO déjà assigné à l'ingrédient (identifié par son `reception_ligne_id`) est **exclu** de la liste des choix possibles, pour éviter de sélectionner le même lot deux fois.

### 6.4 Rendement proportionnel

La formule de calcul des quantités est strictement proportionnelle :
```
Quantité ingrédient = (quantité_base ÷ rendement_base) × production_ciblée
```
Le résultat est arrondi à 2 décimales.

---

## 7. Étiquettes pour produits transformés (Cuisson & Refroidissement)

Le backend expose également `POST /api/etiquettes/transformes`, utilisé depuis les modules **Cuisson** et **Refroidissement** pour générer des étiquettes post-transformation. Ces étiquettes incluent :

- Pour une cuisson : tag `CUIT`, lot d'origine de la réception, T° de fin de cuisson, DLC calculée (cuisson + 3j, capée par DLC source)
- Pour un refroidissement : tag `REFROIDI`, lot d'origine, T° finale, DLC calculée (refroidissement + 3j, capée par DLC source)

Ces étiquettes sont accessibles directement depuis chaque module de transformation concerné (voir chapitres 9 et 10).

---

## 8. Comportements de sécurité UX

- **Inactivité 5 minutes** → redirection automatique vers `/hub.html`
- La modale de confirmation "Substitution" utilise une boîte de dialogue CSS custom (pas `window.confirm`) pour un meilleur rendu sur tablette
- Fermeture des modales : clic en dehors de la carte ou bouton `✕ Annuler`

---

## 9. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Aucune recette disponible | Grille vide : *"Aucune recette disponible."* |
| Erreur chargement recettes | Message : *"⚠ Impossible de charger les recettes ([détail])"* |
| Production ciblée vide (recette avec base) | Message : *"Veuillez saisir la production ciblée du jour."* , focus sur le champ |
| Ingrédient sans lot en stock | Ligne `⚠ Remplacer` — bouton "Confirmer les lots" désactivé |
| Modale substitution : aucun produit trouvé | *"Aucun produit trouvé."* |
| Modale substitution : substitut sans stock | Toast : *"⚠️ Aucun lot en stock pour ce produit. Substitution impossible."* |
| Opérateur non sélectionné (étape 4) | Message rouge : *"Veuillez sélectionner un opérateur."* |
| Erreur API enregistrement fabrication | Message rouge : *"Erreur : [détail]"* |
| DLC réduite par un ingrédient limitant | Toast orange affiché 5 secondes |

---

# Module 4 — Fiches Incident PCR01

---

## 1. Objectif

La fiche PCR01 est le document réglementaire de traçabilité des non-conformités détectées à la réception. Elle enregistre le produit ou le lot concerné, les motifs de NC, les actions prises (contrôle à cœur, retour fournisseur), et recueille si possible la signature du livreur. Ce module est **toujours déclenché automatiquement** depuis le wizard de réception — il n'a pas de bouton d'accès direct dans le Hub.

---

## 2. Chemins d'accès

| Page | Déclencheur | URL |
|---|---|---|
| **Formulaire PCR01** | Procédure NC du wizard réception (étape 4) | `/pcr01.html` |
| **Liste des fiches d'une réception** | Bouton "Voir incidents" depuis l'historique réception | `/incidents.html?reception_id=XXX` |
| **Consultation d'une fiche** | Clic sur une carte dans la liste | `/pcr01-detail.html?id=XXX` |

> Si l'on accède directement à `/pcr01.html` sans session active (pas de données en `sessionStorage`), le système redirige automatiquement vers `/reception.html`.

---

## 3. Deux modes de la fiche PCR01

### Mode standard — NC produit(s)

Déclenché lorsque des produits restent non conformes après le contrôle à cœur (étape 4 du wizard réception). Une fiche est créée **pour chaque produit NC confirmé**. Si plusieurs produits sont NC, la page affiche un badge de pagination **"X/Y"** et l'opérateur valide les fiches une par une.

### Mode camion — Refus livraison pour propreté NC

Déclenché lorsque l'opérateur refuse la livraison en raison de la propreté du camion non satisfaisante. Une **seule fiche** est créée pour l'ensemble du refus (tous les fournisseurs concernés). Le badge dans l'en-tête indique **"Camion"**.

---

## 4. Interface de la page pcr01.html

### 4.1 En-tête

| Élément | Contenu |
|---|---|
| Bouton `← Retour` | Retour vers le wizard réception (sans enregistrer) |
| Titre | `FICHE INCIDENT PCR01` |
| Badge | `X/Y` (numéro de fiche courant / total) en mode standard — `Camion` en mode camion |

### 4.2 En-tête du document

Rempli automatiquement :
- `Réf. PCR01 — Non-conformité réception`
- Date du jour (format long : lundi 14 mai 2026)
- `Opérateur : [Prénom] à [HH:MM]`

### 4.3 Bloc "Produit non conforme"

Affiché uniquement en mode standard. Rempli automatiquement depuis la session réception :

| Champ | Contenu |
|---|---|
| **Produit** | Nom du produit réceptionné |
| **Fournisseur** | Nom du fournisseur (masqué si absent) |
| **N° lot** | Numéro de lot fournisseur ou lot interne (masqué si absent) |
| **DLC / DLUO** | Date limite (masquée si absente) |
| **Non-conformité** | Liste des motifs NC : `température`, `couleur`, `consistance`, `exsudat`, `odeur`, `pH` |
| **Action immédiate** | `🌡️ Contrôle à cœur effectué — NC confirmé (T° à cœur : X°C)` |

En mode camion, le bloc affiche le ou les **Fournisseur(s) concerné(s)** (tous les fournisseurs du refus, séparés par `, `).

### 4.4 Bloc "Étapes d'identification et de traitement"

Timeline chronologique générée **automatiquement** selon le contexte :

#### Mode standard

1. `Contrôle à la réception (visuel / température) → Non-conformité détectée : [motifs] (température camion : X°C).`
2. `Lot isolé immédiatement pour prise de température à cœur.`
3. Si livreur présent : `Livreur présent : feuille de reprise avec retour marchandise signée par le livreur.`  
   Si livreur absent : `Livreur absent : lot isolé avec apposition de l'étiquette À REPRENDRE en attente de retour fournisseur.`

#### Mode camion

1. `Contrôle du camion à la réception → Non-conformité détectée : [problèmes relevés] [+ température camion X°C si > 4°C].`
2. `Fournisseur(s) concerné(s) : [noms].`
3. `Photo du bon de livraison prise : oui (1 par fournisseur).`
4. `Livraison refusée pour l'ensemble du camion.`
5. Selon présence livreur : `Livreur présent : feuille de reprise signée.` ou `Livreur absent : incident enregistré pour suivi fournisseur.`

### 4.5 Bloc "Le livreur est encore là ?" — mode camion uniquement

Affiché uniquement en mode camion (le choix livreur a déjà été fait à l'étape 4 du wizard en mode standard). Deux boutons :
- **`✔ Oui, il est là`** → affiche le bloc signature, masque l'étiquette "À RETOURNER"
- **`✕ Non, il est parti`** → masque la signature, affiche le bouton d'impression

### 4.6 Bloc "Action corrective"

Zone de texte **pré-remplie automatiquement** selon les données de la session. Le texte généré varie selon les motifs NC, la présence du livreur et son attestation (voir section 6). Ce texte est **modifiable** par l'opérateur.

L'action corrective est **obligatoire** pour enregistrer la fiche.

### 4.7 Bloc "Commentaire"

Zone de texte libre, optionnelle. Exemple suggéré : `Relancer fournisseur le …, vérifier prochain lot`.

### 4.8 Bloc "Signature du livreur" — livreur présent uniquement

Visible si le livreur est présent (mode standard ou mode camion après sélection "Oui, il est là").

**Choix livreur :**
- **`✓ Atteste de la NC et accepte le retour`** → le texte de l'action corrective se met à jour pour refléter l'acceptation du retour. Le bouton "À RETOURNER" reste masqué.
- **`✕ N'atteste pas la NC et refuse le retour`** → le texte de l'action corrective se met à jour pour mentionner l'isolement du produit. Le bouton **"🖨️ Imprimer étiquette À RETOURNER"** apparaît.

**Canvas de signature :**
- Zone de dessin tactile (stylet ou doigt sur tablette)
- Bouton **`↺ Effacer`** : efface le canvas pour recommencer
- La signature est **obligatoire** si le livreur est présent (la zone canvas doit contenir au moins un trait)

### 4.9 Bouton "🖨️ Imprimer étiquette À RETOURNER"

Visible dans deux cas :
1. Livreur présent mais **refuse d'attester** la NC
2. Livreur **absent** (mode standard ou mode camion)

Cliquer ce bouton déclenche `window.print()` et imprime l'étiquette À RETOURNER (voir section 7). Le bouton devient `✓ Imprimé — [Nom produit]` après impression.

### 4.10 Bloc "Étiquettes À RETOURNER" — livreur absent, mode standard

Visible uniquement si le livreur est absent en mode standard. Affiche un **bouton d'impression par produit NC** :
- `🖨️ Étiquette — [Nom produit]`
- Devient `✓ Imprimé — [Nom produit]` après impression

### 4.11 Bouton fixe "💾 Enregistrer cette fiche"

Bouton permanent en bas d'écran. Le bouton change visuellement (légère opacité) si des champs obligatoires manquent, mais reste cliquable — c'est au clic que les erreurs sont signalées avec vibration et animation.

---

## 5. Mode d'emploi pas-à-pas

### 5.1 Fiche standard (N produits NC)

1. La page s'ouvre automatiquement au retour de l'étape 4 du wizard réception.
2. Vérifier les informations pré-remplies (produit, motifs, action immédiate).
3. Si livreur présent : sélectionner `✓ Atteste` ou `✕ N'atteste pas`, puis signer le canvas.
4. Si livreur absent : imprimer l'étiquette "À RETOURNER" en cliquant le bouton correspondant.
5. Compléter ou ajuster le texte de l'**Action corrective** si nécessaire.
6. Ajouter un commentaire (optionnel).
7. Cliquer **`💾 Enregistrer cette fiche`**.
8. Si plusieurs fiches : la page passe automatiquement à la fiche suivante (badge `2/N`, `3/N`…).
9. Après la dernière fiche : redirection automatique vers `/reception.html` → le wizard reprend à l'étape 4 pour la clôture finale.

### 5.2 Fiche camion (refus propreté)

1. La page s'ouvre automatiquement après le flux de refus livraison (étape 1 du wizard réception).
2. Répondre à la question **"Le livreur est encore là ?"** :
   - `✔ Oui` → zone signature apparaît, choisir l'attestation, signer.
   - `✕ Non` → bouton "🖨️ Imprimer étiquette À RETOURNER" apparaît.
3. Vérifier / compléter l'**Action corrective**.
4. Cliquer **`💾 Enregistrer cette fiche`**.
5. La réception est **clôturée automatiquement** avec `livraison_refusee=true`.
6. Redirection vers `/hub.html`.

---

## 6. Règles de conformité invisibles

### 6.1 Auto-remplissage de l'action corrective

Le texte est généré automatiquement et **se met à jour en temps réel** lorsque l'opérateur modifie son choix (présence livreur, attestation). Les formulations exactes sont :

**Mode standard :**

| Situation | Texte généré |
|---|---|
| Base (tous cas) | `Non-conformité constatée à la réception : [motifs] sur [produit] (lot [num]).`<br>`Contrôle à cœur effectué : non-conformité confirmée. La température à cœur mesurée est de X°C.` |
| Livreur présent + atteste et accepte | `…La non-conformité est attestée et le retour accepté, la feuille de reprise avec retour marchandise a été signée par le livreur.` |
| Livreur présent + refuse le retour | `…La non-conformité n'est pas attestée par le livreur et le retour n'est pas accepté. Le produit est isolé et balisé en attente de la résolution du litige.` |
| Livreur absent | `…En l'absence du livreur, le lot a été isolé avec apposition de l'étiquette À RETOURNER en attente de retour fournisseur.` |

**Mode camion :**

Le texte cite les problèmes de propreté cochés à l'étape 1, la température camion si elle dépasse 4°C, les noms de fournisseurs concernés, et se termine par la mention de la livraison refusée + situation livreur.

### 6.2 Seuil température camion en mode camion

La condition `tempCamion > 4` (strictement supérieur à 4°C) déclenche l'ajout de la mention *"Température camion NC : X°C (seuil ≤ 4°C)"* dans les étapes d'identification et dans l'action corrective.

### 6.3 Une seule fiche en mode camion

En mode camion, il n'y a qu'une seule fiche PCR01 quel que soit le nombre de fournisseurs concernés. Tous les noms de fournisseurs sont concaténés avec ` + ` et stockés dans le champ `fournisseur_nom`. Le premier fournisseur avec un ID connu est utilisé comme clé étrangère `fournisseur_id`.

### 6.4 Clôture automatique de la réception en mode camion

Après enregistrement de la fiche PCR01 en mode camion, le système appelle automatiquement `PUT /api/receptions/{id}/cloturer` avec `livraison_refusee: true`. L'opérateur n'a pas besoin de retourner dans le wizard.

### 6.5 Sauvegarde de la signature

La signature dessinée sur le canvas est convertie en PNG (via `canvas.toDataURL('image/png')`) et envoyée au serveur comme fichier joint (`signature_livreur`). Elle est stockée dans `data/photos/signatures/SIG-YYYYMMDD-HHMMSS-{id}.png`.

### 6.6 Vérification "signature vide"

Avant l'enregistrement, le système lit tous les pixels du canvas. Si chaque pixel est à zéro (canvas entièrement blanc), la signature est considérée vide → message d'erreur.

---

## 7. Contenu de l'étiquette "À RETOURNER" imprimée

Format `window.print()` (feuille A4, pas d'imprimante thermique pour ce gabarit). Contenu :

| Zone | Contenu |
|---|---|
| **Bandeau rouge** | `PRODUIT NON CONFORME` |
| **Titre** | `À RETOURNER` |
| **Référence** | `Réf. PCR01 — Non-conformité réception` |
| **Date/heure/opérateur** | Date longue, prénom opérateur, heure réception |
| **Tableau** | Produit, Fournisseur, N° lot, DLC/DLUO, Non-conformité, Action immédiate |
| **Pied** | `Au Comptoir des Lilas — Réf. PCR01` |

> En mode camion, le produit est affiché comme `Livraison refusée — Propreté camion`, et le motif liste les problèmes cochés à l'étape 1.

---

## 8. Page incidents.html — Liste des fiches d'une réception

**Accès :** depuis le détail d'une réception dans l'historique, via un lien `?reception_id=XXX`.

### 8.1 Interface

- **Compteur** : `N fiche(s) PCR01`
- **Liste de cartes** (une par fiche) :
  - Date de l'incident
  - Badge statut : `🔄 Ouverte` ou `✓ Fermée`
  - Nature du problème
  - Action immédiate
- **Clic sur une carte** → redirection vers `/pcr01-detail.html?id=XXX`

### 8.2 Comportements UX

- Inactivité 5 minutes → redirection automatique vers `/hub.html`
- Bouton `← Retour` : retour à la page précédente (`window.history.back()`)
- Si `reception_id` manquant dans l'URL : message d'erreur `⚠️ ID de réception manquant.`

---

## 9. Cas d'erreurs et validations

| Situation | Ce qui se passe |
|---|---|
| Action corrective vide | Message : *"L'action corrective est obligatoire."* + contour rouge animé + scroll + vibration |
| Mode camion : présence livreur non précisée | Message : *"Veuillez indiquer si le livreur est présent ou absent."* + animation sur les deux boutons |
| Livreur présent : attestation non choisie | Message : *"Veuillez indiquer si le livreur atteste ou n'atteste pas la NC."* + animation |
| Canvas signature vide (livreur présent) | Message : *"La signature du livreur est obligatoire."* + contour rouge sur le canvas |
| Erreur API enregistrement | Message rouge : *"Erreur : [détail]"* |
| Page ouverte sans session PCR01 | Redirection immédiate vers `/reception.html` |

---

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

# Module 6 — Nettoyage & Désinfection

---

## 1. Objectif

Ce module matérialise le **Plan de Nettoyage et Désinfection (PND)** hebdomadaire. Il affiche un tableau à double entrée (secteur × jour de la semaine) qui permet de valider, case par case ou en une seule action, l'ensemble des tâches de nettoyage du jour. Chaque validation est tracée avec le prénom de l'opérateur et la date, et consultable dans l'historique.

---

## 2. Chemins d'accès

| Page | URL | Accès |
|---|---|---|
| **Planning hebdomadaire** | `/nettoyage.html` | Hub Tâches HACCP → tuile 🧹 NETTOYAGE |
| **Historique des validations** | `/historique-nettoyage.html` | Bouton `📋 Historique` dans la barre de la page planning |

---

## 3. Page principale — Planning hebdomadaire

### 3.1 Barre de contrôle (sticky)

La barre reste visible en haut de l'écran lors du défilement. Elle contient :

| Élément | Libellé exact | Rôle |
|---|---|---|
| Lien retour | `← Tâches` | Retour vers `/taches-hub.html` |
| Date | `Aujourd'hui : [Jour] [N] [Mois]` | Date courante |
| Bouton | `⚙ Tâches` | Ouvre la modale de gestion des tâches |
| Lien | `📋 Historique` | Ouvre `/historique.html?tab=nettoyage` |
| Menu déroulant | `👤 Opérateur…` | Sélection de l'opérateur (prénoms actifs du personnel) |
| Bouton principal | `✅ VALIDER LE NETTOYAGE DU [JOUR]` | Valide toutes les tâches applicables du jour |

### 3.2 Tableau de planning

Le tableau a les colonnes suivantes :

| Colonne | Contenu |
|---|---|
| **Secteur** | Zone / secteur de l'établissement (cellules fusionnées sur N lignes) |
| **Quoi** | Nom de la tâche (texte complet visible au survol si tronqué) |
| **Quand** | Fréquence : `Quotidien` ou `Hebdomadaire` |
| **Produit** | Produit/méthode de nettoyage |
| **Lun / Mar / Mer / Jeu / Ven / Sam / Dim** | Colonne par jour — case cochée = `✅ [initiale].` |

La **colonne du jour courant** est surlignée visuellement.

---

## 4. Mode d'emploi pas-à-pas

### 4.1 Validation globale du jour (méthode principale)

1. Sélectionner son prénom dans le menu déroulant **`👤 Opérateur…`**.
2. Cliquer sur le bouton **`✅ VALIDER LE NETTOYAGE DU [JOUR]`**.
3. Une boîte de confirmation s'affiche :  
   *"En validant, je confirme sur l'honneur avoir effectué l'intégralité des tâches de nettoyage et de désinfection listées pour aujourd'hui, en respectant le Plan de Nettoyage."*
4. Confirmer → toutes les cases applicables du jour se cochent avec l'initiale de l'opérateur, et un toast de confirmation s'affiche.

### 4.2 Validation d'une colonne entière (jour passé ou autre)

Cliquer sur l'**en-tête d'un jour** (ex. : `Lun`, `Mar`…) coche toutes les tâches **quotidiennes** de ce jour. Les tâches hebdomadaires sont **ignorées** par cette action.

> Cette méthode est utile pour valider un jour passé que l'on aurait oublié de saisir.

### 4.3 Coche individuelle d'une cellule

Cliquer directement sur n'importe quelle **cellule de la grille** pour cocher ou décocher cette tâche précise.

- **Cocher** : requiert un opérateur sélectionné. La case affiche `✅ [Initiale].`
- **Décocher** : ne requiert **pas** d'opérateur. La validation est immédiatement supprimée de la base.

---

## 5. États du bouton principal

Le libellé du bouton évolue dynamiquement selon l'avancement :

| État | Libellé du bouton |
|---|---|
| Aucune tâche validée | `✅ VALIDER LE NETTOYAGE DU [JOUR]` |
| Validation partielle | `✅ VALIDER LE RESTE (X/Y)` |
| Toutes tâches validées | `✔ VALIDÉ — N tâche(s)` (bouton vert) |

---

## 6. Modale "⚙ Gérer les tâches"

Accessible via le bouton **`⚙ Tâches`** dans la barre. Permet au responsable de **créer, modifier et supprimer** les tâches du plan de nettoyage.

### 6.1 Interface

La modale affiche :
1. La liste des tâches existantes, groupées par zone, avec pour chaque tâche :
   - Nom, fréquence, produit
   - Bouton `✏ Modifier` → pré-remplit le formulaire d'édition ci-dessous
   - Bouton `🗑` → suppression avec confirmation

2. Le formulaire d'ajout / édition :

| Champ | Obligatoire | Valeurs | Notes |
|---|---|---|---|
| **Zone** | Oui ✱ | Texte libre | Forcé en MAJUSCULES à la sauvegarde (ex : `CUISINE`) |
| **Tâche** | Oui ✱ | Texte libre | Forcé en MAJUSCULES (ex : `SOL / SIPHON`) |
| **Fréquence** | Oui | `Quotidien` / `Hebdomadaire` | Défaut : `Quotidien` |
| **Produit** | Non | Texte libre | Forcé en MAJUSCULES (ex : `KING FLASH GERM`) |

Boutons du formulaire :
- **`Enregistrer`** : crée ou met à jour la tâche, recharge la liste et le tableau principal
- **`Annuler`** (visible en mode édition) : réinitialise le formulaire sans sauvegarder

### 6.2 Suppression d'une tâche

Cliquer le bouton `🗑` d'une tâche affiche un `confirm` :  
*"Supprimer la tâche "[Nom]" ? Les validations passées ne seront pas effacées."*

La suppression est définitive (pas de soft-delete). L'historique existant reste intact.

---

## 7. Règles de conformité invisibles

### 7.1 Règle JOUR_HEBDO — grand nettoyage du samedi

Les tâches de fréquence `Hebdomadaire` ne sont **applicables que le samedi** (jour 6 de la semaine). Cette règle est codée en dur (`JOUR_HEBDO = 6`). Conséquences :
- La validation globale (bouton principal) n'inclut les tâches hebdomadaires **que le samedi**.
- La validation par clic sur un en-tête de colonne **exclut toujours** les tâches hebdomadaires.
- Une case hebdomadaire peut quand même être cochée **individuellement** n'importe quel jour.

### 7.2 Anti-doublon à la validation

Le backend vérifie avant chaque insertion si une validation (`tache_id` + `date`) existe déjà. Si oui, l'insertion est ignorée silencieusement. Le bouton "Valider" peut donc être cliqué plusieurs fois sans créer de doublons.

### 7.3 Restauration de l'état au rechargement

Au chargement de la page, le système appelle `GET /api/nettoyage/status?date=[aujourd'hui]`. Si des validations existent pour le jour courant, les cellules correspondantes sont ré-affichées avec `✅ [Initiale].` et l'opérateur principal est présélectionné dans le menu déroulant. Les validations de la semaine entière (jours passés) sont également récupérées via `GET /api/nettoyage/historique/semaine`.

### 7.4 Initiales affichées dans les cellules

L'initiale affichée est la **première lettre en majuscule** du prénom de l'opérateur suivie d'un point (ex. : opérateur "Émile" → `É.`). Pour l'historique semaine, c'est le premier opérateur ayant validé la tâche ce jour-là qui s'affiche.

### 7.5 Calcul de la semaine ISO

Le planning hebdomadaire et l'historique utilisent le standard **ISO 8601** (semaine 1 = semaine contenant le premier jeudi de l'année). Le lundi est le premier jour de la semaine.

---

## 8. Page Historique des validations

### 8.1 Structure en accordéon

L'historique est présenté sous forme d'**arborescence repliable** à 3 niveaux :

```
▼ 2026                                ← Année (cliquable pour déplier/replier)
  ▼ Mai                                ← Mois (cliquable)
    ▼ Semaine 20                       ← Semaine ISO (cliquable)
      🧹 Mercredi 14  É., M.  [8 tâches]
      🧹 Mardi 13     É.      [8 tâches]
```

### 8.2 Carte jour

Chaque jour validé affiche :
- 🧹 icône
- Nom du jour + numéro (ex. : `Mercredi 14`)
- Opérateurs ayant validé ce jour (prénoms séparés par `, `)
- Badge vert `N tâches`

### 8.3 Navigation

- Bouton `← Retour` → retour vers `/nettoyage.html`
- Tous les niveaux sont repliés par défaut au chargement

---

## 9. Notifications toast

Des notifications courtes (3,5 secondes) confirment chaque action :

| Action | Message toast |
|---|---|
| Validation globale réussie | `✅ N tâche(s) du jour validées par [Opérateur] !` |
| Coche par colonne réussie | `✅ N tâche(s) cochées.` |
| Coche individuelle réussie | `Case cochée et enregistrée.` |
| Décoche réussie | `Case décochée et enregistrée.` |
| Tâche ajoutée | `✅ Tâche ajoutée.` |
| Tâche modifiée | `✅ Tâche modifiée.` |
| Tâche supprimée | `🗑 Tâche supprimée.` |

Les toasts d'erreur s'affichent en rouge.

---

## 10. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Validation sans opérateur sélectionné | Toast erreur : *"Sélectionnez votre nom avant de valider."* + focus sur le select |
| Coche individuelle sans opérateur | Toast erreur : *"Sélectionnez votre nom avant de cocher."* + focus sur le select |
| Aucune tâche applicable aujourd'hui | Toast : *"Aucune tâche applicable aujourd'hui."* (si aucune tâche de type quotidien ni hebdo-samedi) |
| Zone ou nom de tâche vides (formulaire) | Toast erreur : *"Zone et nom de tâche obligatoires."* |
| Erreur réseau (validation) | Toast erreur + **rollback visuel** : les cellules qui venaient d'être cochées sont vidées |
| Erreur chargement du tableau | Message centré dans le tableau : *"Erreur : [détail]"* |

---

# Module 7 — Lutte contre les Nuisibles (IPM)

---

## 1. Objectif

Ce module assure le suivi du plan **IPM (Integrated Pest Management)** — Lutte intégrée contre les nuisibles. Il enregistre, semaine par semaine sur une année entière, le résultat du contrôle de chacun des 15 pièges pour les 4 familles de nuisibles surveillées : rongeurs, insectes volants, insectes rampants et oiseaux.

---

## 2. Chemin d'accès

Hub Tâches HACCP → tuile **🐛 NUISIBLES**.

URL directe : `/nuisibles.html`

---

## 3. Interface générale

### 3.1 Barre supérieure

| Élément | Contenu |
|---|---|
| Lien `← Tâches` | Retour vers `/taches-hub.html` |
| Titre | `🐛 Lutte contre Nuisibles` |
| Sélecteur d'année | Menu déroulant : année courante et 4 années précédentes |

### 3.2 Onglets (4 types de nuisibles)

| Onglet | ID | Emoji | Nuisibles ciblés |
|---|---|---|---|
| **Rongeurs** | 1 | 🐀 | Souris, Rats, Mulots… |
| **Ins. Volants** | 2 | 🪰 | Mouches, Moucherons, Guêpes… |
| **Ins. Rampants** | 3 | 🪳 | Cafards, Fourmis… |
| **Oiseaux** | 4 | 🐦 | Pigeons, Moineaux, Étourneaux… |

Cliquer un onglet recharge immédiatement le tableau pour ce type et l'année sélectionnée.

### 3.3 Fiche info "Méthodes & Fréquences" (repliable)

Un bandeau cliquable **`ℹ️ Méthodes & Fréquences`** affiche/masque la fiche de référence pour l'onglet actif. Contenu par espèce :

| Espèce | Méthodes de lutte | Fréquence / Protocole |
|---|---|---|
| **Rongeurs** | Plaques de glue avec attractif — Rodenticide fluorescent en boîte sécurisée | Inspection hebdomadaire des pièges à glue — Changement + vérification rodenticides mensuel |
| **Insectes Volants** | DEIV à glu (zones alimentaires) — DEIV à électrocution (zones non alimentaires) | Plaque glu : mensuelle (avril–septembre), tous les 2 mois (octobre–mars) — Tubes UV : remplacement annuel |
| **Insectes Rampants** | Piège à phéromones et à glu dans zones critiques — Gel anti-cafard/fourmis en boîte sécurisée | Inspection hebdomadaire des pièges à glue — Remplacement pièges et gel tous les 3 mois |
| **Oiseaux** | Pics anti-pigeons — Filets de protection | Inspection hebdomadaire des pics et filets — Nettoyage et désinfection immédiats si fientes |

### 3.4 Tableau 52 semaines

Le tableau affiche une ligne par semaine ISO (S1 à S52 ou S53) pour l'espèce et l'année sélectionnées :

| Colonne | Contenu |
|---|---|
| **Sem** | Numéro de semaine ISO |
| **P1 à P15** | Résultat du piège : `O` (ok, vert), `N` (non ok, rouge), `·` (non vérifié, vide) |
| **VISA** | Prénom de l'opérateur ayant saisi |

La **semaine courante** est surlignée et la page défile automatiquement vers elle au chargement (si l'année affichée est l'année en cours).

**Cliquer sur une ligne** du tableau ouvre la modale d'édition de cette semaine.

### 3.5 Bouton flottant "⚡ Saisie rapide"

Un bouton flottant (FAB) en bas d'écran indique `⚡ Saisie rapide` avec sous-titre `S[N] · 4 espèces · 15 pièges`. Il ouvre la modale de **saisie rapide multi-espèces** directement pour la semaine courante.

---

## 4. Mode d'emploi pas-à-pas

### 4.1 Saisir le contrôle d'une semaine (méthode simple)

1. Sélectionner l'**onglet** de l'espèce à contrôler.
2. Cliquer sur la **ligne de la semaine** souhaitée dans le tableau.
3. La modale d'édition s'ouvre (voir section 5).
4. Saisir l'état de chaque piège.
5. Sélectionner le **Visa** (opérateur).
6. Cliquer **`✅ Enregistrer`**.

### 4.2 Saisie rapide de toutes les espèces en une fois

1. Cliquer le bouton flottant **`⚡ Saisie rapide`**.
2. La modale multi-espèces s'ouvre sur la semaine courante (voir section 6).
3. Utiliser les actions globales pour préremplir rapidement.
4. Ajuster les pièges individuels si nécessaire.
5. Sélectionner le **Visa** partagé.
6. Cliquer **`✅ Enregistrer tout`**.

---

## 5. Modale d'édition simple (une espèce)

### En-tête

`[Emoji] [NomEspèce] — Semaine N / AAAA ⚡` (l'éclair ⚡ apparaît si c'est la semaine courante).

### Actions rapides

| Bouton | Effet |
|---|---|
| `✗ Tout N (RAS)` | Met tous les 15 pièges à `N` |
| `✓ Tout O` | Met tous les 15 pièges à `O` |
| `· Vider` | Remet tous les 15 pièges à `·` (non vérifié) |

### Grille des 15 pièges

15 boutons carrés **P1 à P15**. Chaque clic fait **cycler** l'état du piège dans l'ordre :
```
· (non vérifié)  →  O (ok)  →  N (non ok)  →  · (non vérifié) …
```

Couleurs :
- `O` : bouton vert
- `N` : bouton rouge
- `·` : bouton neutre (gris clair)

### Visa (opérateur)

Menu déroulant avec le personnel actif. La dernière valeur utilisée est **mémorisée localement** (localStorage) et pré-remplie automatiquement à la prochaine ouverture.

### Boutons

| Bouton | Action |
|---|---|
| `Annuler` | Ferme la modale sans sauvegarder |
| `✅ Enregistrer` | Sauvegarde et met à jour la ligne dans le tableau |

---

## 6. Modale saisie rapide multi-espèces

### Navigateur de semaine

Boutons **`‹`** (semaine précédente) et **`›`** (semaine suivante) pour naviguer d'une semaine à l'autre sans fermer la modale. Label : `Semaine N / AAAA ⚡` (l'éclair si semaine courante).

Les données de chaque semaine naviguée sont rechargées depuis le cache local (données déjà chargées à l'ouverture de la modale).

### Visa partagé

Menu déroulant unique, appliqué à **toutes les espèces** lors de l'enregistrement.

### Bloc "Action globale portée"

Permet d'appliquer en un clic une valeur à un ensemble de pièges sur une ou toutes les espèces :

| Contrôle | Description |
|---|---|
| **Stepper P1–Pn** | Définit la portée (1 à 15). Boutons `−` et `+`. Défaut : P1–P15 (tous). |
| **Sélection espèce** | `Toutes` (défaut) / `🐀 Rongeurs` / `🪰 Ins. Volants` / `🪳 Ins. Rampants` / `🐦 Oiseaux` |
| **`✗ N`** | Applique `N` aux pièges P1–Pn pour l'espèce sélectionnée |
| **`✓ O`** | Applique `O` aux pièges P1–Pn pour l'espèce sélectionnée |
| **`· Vider`** | Applique `·` (non vérifié) aux pièges P1–Pn |

**Exemple** : stepper à P1–P8, espèce = Rongeurs, clic `✗ N` → les pièges P1 à P8 passent à `N` pour les Rongeurs uniquement.

### Sections par espèce

Une section dédiée par espèce (4 sections au total), chacune avec :
- En-tête `[Emoji] [Nom] — 15 pièges`
- Boutons rapides `✗ N` / `✓ O` / `·` pour cette espèce uniquement
- Grille de 15 pièges (même cycle de clic que la modale simple)

### Enregistrement

**`✅ Enregistrer tout`** envoie en parallèle une requête API pour **chaque espèce ayant au moins 1 piège non-vide** (`!= null`). Les espèces dont tous les pièges sont à `·` (null) ne sont **pas envoyées**.

---

## 7. Règles de conformité invisibles

### 7.1 UPSERT — remplacement complet par semaine

Chaque sauvegarde effectue un **UPSERT** (`INSERT OR CONFLICT ... DO UPDATE`) sur la clé unique `(type_id, annee, semaine)`. La sauvegarde d'une semaine **remplace intégralement** les données précédentes de cette semaine pour ce type de nuisible. Il n'y a pas d'accumulation — seule la dernière saisie est conservée.

### 7.2 Semaines ISO (1-53)

Le module utilise la numérotation **ISO 8601**. Certaines années ont 53 semaines. Le tableau affiche le nombre correct de lignes selon l'année sélectionnée.

### 7.3 Mémorisation du dernier visa

La valeur du Visa sélectionné est sauvegardée dans `localStorage` sous la clé `nu-last-visa`. Elle est pré-remplie automatiquement à la prochaine ouverture de n'importe quelle modale de saisie. Cette mémorisation est locale au navigateur/tablette.

### 7.4 Mise à jour partielle du tableau

Après une sauvegarde réussie, seule la **ligne concernée** est mise à jour visuellement — le tableau entier n'est pas re-rendu. Cela garantit un affichage rapide même sur un tableau de 52 lignes.

### 7.5 Résultats non envoyés en saisie rapide

Lors de la saisie rapide multi-espèces, si une espèce n'a **aucun piège renseigné** (tous à `·`), elle est ignorée à l'enregistrement. Ses données existantes en base ne sont pas écrasées.

---

## 8. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Erreur de chargement des données | Tableau avec message centré : *"Erreur de chargement : [détail]"* |
| Semaine invalide (hors 1-53) | Erreur HTTP 400 retournée par le backend |
| Erreur lors de la sauvegarde simple | Toast rouge : *"Erreur : [détail]"*, bouton Enregistrer réactivé |
| Erreur lors d'une espèce en saisie rapide | Toast rouge : *"Erreur : [NomEspèce]: HTTP [code]"* |
| Aucune donnée à enregistrer (saisie rapide) | Toast : *"Aucune donnée à enregistrer"* (si tous les pièges sont à `·`) |

---

## 9. Fermeture des modales

| Méthode | Effet |
|---|---|
| Bouton `✕` | Ferme sans sauvegarder |
| Bouton `Annuler` | Ferme sans sauvegarder |
| Clic en dehors de la modale | Ferme sans sauvegarder |

---

# Module 8 — Étalonnage Thermomètres (EET01)

---

## 1. Objectif

Ce module enregistre l'étalonnage trimestriel des thermomètres selon la procédure **EET01**. L'opération se déroule en **deux phases** : d'abord la vérification du thermomètre de référence dans l'eau glacée (0°C ± 0,5°C), puis la comparaison de chaque sonde Zigbee des enceintes frigorifiques avec ce même thermomètre.

---

## 2. Chemins d'accès

| Page | URL | Accès |
|---|---|---|
| **Phase 1 — Étalonnage référence** | `/etalonnage.html` | Hub Tâches HACCP → tuile 🌡️ ÉTALONNAGE |
| **Phase 2 — Comparaison sondes** | `/etalonnage-comparaison.html?id=XXX` | Automatique après validation Phase 1 |

---

## 3. Architecture en deux phases

```
Phase 1 (etalonnage.html)
  ↓ Conforme OU Remplacé
Phase 2 (etalonnage-comparaison.html)
  ↓ Enregistrer
Retour à etalonnage.html

Phase 1
  ↓ Calibrage seulement
Message + formulaire réinitialisé (PAS de Phase 2)
```

> Si la Phase 1 aboutit à un **Calibrage**, la Phase 2 n'est pas accessible immédiatement. L'opérateur doit d'abord effectuer le calibrage physique du thermomètre, puis créer un nouvel enregistrement de Phase 1.

---

## 4. Page Phase 1 — Étalonnage du thermomètre de référence

### 4.1 Encart règle (permanent)

> *"Règle de conformité : 0°C ± 0,5°C (de −0,5°C à +0,5°C) — Hors intervalle : remplacer le thermomètre. Dans tous les cas : nettoyer la sonde et la ranger."*

### 4.2 Formulaire "Nouvel enregistrement"

| Champ | Obligatoire | Notes |
|---|---|---|
| **Date** | Oui ✱ | Pré-remplie avec la date du jour |
| **Opérateur** | Oui ✱ | Menu déroulant — personnel actif |
| **Thermomètre de référence** | Oui ✱ | Menu déroulant — thermomètres actifs configurés dans l'administration. Affiché : `Nom — N° série` (ou juste `Nom` si pas de numéro) |
| **Température mesurée (°C)** | Oui ✱ | Saisie décimale (ex. : `0,2`). Pas de borne min/max imposée. |
| **Résultat** | Auto | Badge mis à jour en temps réel dès la saisie de la température |
| **Action corrective** | Oui ✱ | Radio — disponibilité des options dépend du résultat (voir section 5) |
| **Commentaire** | Non | Zone de texte libre (ex. : numéro de série, marque…) |

### 4.3 Badge de conformité temps réel

Mis à jour à chaque frappe dans le champ Température :

| Valeur saisie | Badge affiché |
|---|---|
| Vide | `— Saisir une température` (gris) |
| T° ∈ [−0,5°C ; +0,5°C] | `✅ Conforme — X,X°C dans [−0,5 ; +0,5]` (vert) |
| T° hors intervalle | `❌ Non conforme — X,X°C hors tolérance` (rouge) |

### 4.4 Tableau historique

Sous le formulaire, un tableau affiche les 50 derniers étalonnages avec les colonnes :
**Date** · **Thermomètre** · **Température** · **Résultat** (badge vert/rouge) · **Action corrective** · **Opérateur**

---

## 5. Mode d'emploi Phase 1

1. Préparer un bain d'eau glacée (eau + glaçons, brassée pour homogénéité).
2. Plonger le thermomètre de référence, attendre stabilisation.
3. Ouvrir la page `/etalonnage.html`.
4. Vérifier/ajuster la **Date** et sélectionner l'**Opérateur**.
5. Sélectionner le **Thermomètre de référence** utilisé.
6. Saisir la **Température mesurée** → le badge de conformité s'affiche immédiatement.
7. Sélectionner l'**Action corrective** (les options non applicables sont grisées automatiquement).
8. Ajouter un **Commentaire** si nécessaire.
9. Cliquer **`Enregistrer ✓`**.

---

## 6. Règles de sélection des actions correctives

Les options sont activées/désactivées **automatiquement** selon la température saisie. Aucune saisie manuelle contraire n'est possible (le frontend désactive les mauvaises options, le backend rejette les incohérences) :

| Température | Options disponibles | Option auto-sélectionnée |
|---|---|---|
| Vide | Toutes désactivées | — |
| Conforme (∈ [−0,5 ; +0,5°C]) | `✅ Conforme` uniquement | **Conforme** (automatique) |
| Non conforme (hors tolérance) | `🔧 Calibrage` et `🔄 Remplacé` uniquement | Aucune |

### Signification des actions

| Action | Signification | Suite |
|---|---|---|
| `✅ Conforme` | Le thermomètre est précis dans les tolérances | → Passe à la **Phase 2** |
| `🔧 Calibrage` | Le thermomètre a été recalibré | → **Pas de Phase 2** — formulaire réinitialisé |
| `🔄 Remplacé` | Le thermomètre a été remplacé par un nouveau | → Passe à la **Phase 2** |

---

## 7. Après la soumission Phase 1

### Cas Calibrage

Un message vert s'affiche :  
*"🔧 Calibrage enregistré. Effectuez le calibrage puis créez un nouvel enregistrement pour passer aux comparaisons."*

Le formulaire se réinitialise. L'historique se recharge. L'opérateur doit physiquement calibrer le thermomètre, puis créer un nouvel enregistrement Phase 1 jusqu'à obtenir un résultat Conforme ou Remplacé.

### Cas Conforme ou Remplacé

Redirection automatique vers `/etalonnage-comparaison.html?id={id}` — Phase 2.

---

## 8. Page Phase 2 — Comparaison des sondes Zigbee

### 8.1 En-tête et contexte

- Bouton **`← Étape 1`** : retour vers `/etalonnage.html`
- Bandeau **"✅ Étape 1 validée"** avec résumé de la Phase 1 : nom du thermomètre, T° mesurée, action corrective, opérateur

Instruction permanente :  
*"Plongez le thermomètre de référence dans chaque enceinte et saisissez sa lecture. La sonde connectée est relevée automatiquement. Conformité : écart ≤ ±0,5°C."*

### 8.2 Grille des enceintes

Une **carte par enceinte** frigorifique configurée. Chaque carte contient :

| Élément | Contenu |
|---|---|
| **Nom de l'enceinte** | Identifiant de l'enceinte (ex. : "Chambre froide 1") |
| **Sonde Zigbee** | Température actuelle relevée automatiquement depuis l'API (ex. : `2,1 °C`) |
| **Thermo de référence** | Champ de saisie décimale obligatoire (ex. : `2,4`) |
| **Badge écart** | Résultat affiché en temps réel dès la saisie |

### 8.3 Badge d'écart temps réel

L'écart est calculé comme `T°référence − T°Zigbee` :

| Écart | Badge |
|---|---|
| Non saisi | `— Saisir la température de référence` (gris) |
| \|écart\| ≤ 0,5°C | `✅ Conforme — écart : +X,X°C dans [−0,5 ; +0,5]` (vert) |
| \|écart\| > 0,5°C | `❌ Non conforme — écart : +X,X°C hors tolérance` (rouge) |

### 8.4 Actualisation des sondes Zigbee

Les températures des sondes sont **rechargées automatiquement toutes les 30 secondes** depuis l'API. Seules les valeurs affichées sont mises à jour (les cartes ne sont pas reconstruites).

### 8.5 Bouton "Enregistrer les comparaisons ✓"

Reste **désactivé** tant que tous les champs de température de référence ne sont pas renseignés. Dès que toutes les enceintes ont une valeur valide, il s'active.

Après soumission réussie → redirection vers `/etalonnage.html`.

---

## 9. Mode d'emploi Phase 2

1. Pour chaque enceinte, plonger le thermomètre de référence et attendre la stabilisation.
2. Saisir la lecture dans le champ **"Thermo de référence"** de la carte correspondante.
3. Observer le badge écart — vérifier la conformité.
4. Répéter pour toutes les enceintes.
5. Quand toutes les cartes sont renseignées, cliquer **`Enregistrer les comparaisons ✓`**.

---

## 10. Règles de conformité invisibles

### 10.1 Fréquence trimestrielle — 92 jours

La fréquence réglementaire est de **92 jours** (~3 mois). Le système calcule la date du prochain étalonnage : `date_dernier + 92j`. Si cette date est dépassée, l'étalonnage est marqué **"en retard"** dans le Hub HACCP.

L'API `GET /api/etalonnage/status` retourne :
- `en_retard` : booléen
- `jamais_fait` : booléen (si aucun étalonnage en base)
- `dernier_date`, `dernier_thermo`, `dernier_operateur`
- `prochain_date`, `jours_restants`

### 10.2 Double validation côté frontend ET backend

La règle de cohérence action/température est vérifiée **deux fois** :
1. **Frontend** : désactive visuellement les mauvaises options dès la saisie
2. **Backend** : rejette avec HTTP 400 si l'incohérence persiste (ex. : action="conforme" envoyée avec une T° hors tolérance)

Ce double contrôle garantit l'intégrité même si quelqu'un contourne l'interface.

### 10.3 Re-soumission de Phase 2 sécurisée

Si la Phase 2 est soumise plusieurs fois pour le même étalonnage (ex. : retour arrière), le backend **supprime d'abord** toutes les comparaisons existantes avant de réinsérer les nouvelles. Il n'y a pas de duplication.

### 10.4 Accès Phase 2 conditionnel

Le backend vérifie que l'étalonnage référencé par l'`id` en URL est en état `conforme` ou `remplace`. Si l'état est `calibrage`, l'enregistrement des comparaisons est rejeté avec HTTP 400 :  
*"Le thermomètre de référence doit être conforme ou remplacé avant de réaliser les comparaisons."*

Si aucun `id` n'est présent dans l'URL de Phase 2, redirection automatique vers `/etalonnage.html`.

### 10.5 Calcul de l'écart (Phase 2)

`écart = round(temp_reference − temp_zigbee, 2)`

Conforme si `|écart| ≤ 0,5°C`. L'écart est stocké tel quel (avec signe) en base.

---

## 11. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Date vide | Message rouge : *"La date est obligatoire."* |
| Opérateur non sélectionné | Message rouge : *"Sélectionnez un opérateur."* |
| Thermomètre non sélectionné | Message rouge : *"Sélectionnez un thermomètre de référence."* |
| Température vide | Message rouge : *"La température est obligatoire."* |
| Action corrective non sélectionnée | Message rouge : *"Sélectionnez une action corrective."* |
| Aucun thermomètre configuré | Menu déroulant affiche `⚠ Aucun thermomètre configuré` (option désactivée) |
| Incohérence action/T° (backend) | HTTP 400 avec message explicite |
| Erreur réseau Phase 1 | Message rouge sous le formulaire : *"Erreur : [détail]"* |
| Températures Zigbee non disponibles | Enceinte affiche `— °C`, badge reste vide |
| Enceinte sans T° Zigbee (soumission Phase 2) | La valeur `0` est utilisée par défaut pour le calcul d'écart |
| T° de référence manquante (soumission Phase 2) | Message rouge : *"Toutes les températures de référence sont obligatoires."* |
| Erreur réseau Phase 2 | Message rouge, bouton réactivé |

---
# Module 9 — Cuisson HACCP (≥ 75°C)

---

## 1. Objectif

Ce module enregistre chaque opération de cuisson avec traçabilité complète : produit, lot source, opérateur, heures de début et de fin, et surtout la **température à la sortie** par rapport à la cible réglementaire HACCP de **75°C à cœur**. Si la température est atteinte, une DLC J+3 est calculée automatiquement et une étiquette thermique peut être imprimée. Après cuisson, le module propose directement de lancer le suivi de refroidissement.

---

## 2. Chemin d'accès

Hub principal → **Production** → tuile **🔥 CUISSON**.

URL directe : `/cuisson.html`

---

## 3. Structure générale : wizard 3 étapes

Wizard guidé avec barre de progression numérotée 1-2-3. Un bandeau `👤 [Opérateur] · 📦 [Produit]` reste visible dès que les deux premiers choix sont faits.

| Étape | Titre |
|---|---|
| 1 | Qui cuisine ? |
| 2 | Quel produit ? |
| 3 | Paramètres de cuisson |

Navigation arrière disponible à toutes les étapes. Inactivité 5 minutes → redirection vers `/hub.html`.

---

## 4. Étape 1 — Sélection de l'opérateur

Grille de tuiles avec l'initiale et le prénom de chaque membre du personnel actif, triés alphabétiquement. Un clic sur une tuile la sélectionne (mise en évidence) et fait avancer automatiquement vers l'étape 2 après 150 ms.

---

## 5. Étape 2 — Sélection du produit

### 5.1 Filtres

- **Filtres espèces** : boutons `Toutes` + un bouton par espèce présente en stock (🐂 Bœuf, 🐄 Veau, 🐑 Agneau, 🐖 Porc, 🦌 Gibier, 🐔 Volaille, 🐎 Cheval, 🦬 Exotique). Générés dynamiquement selon le stock disponible.
- **Champ de recherche** : filtre les tuiles par nom (insensible à la casse).

### 5.2 Grille de produits

Seuls les produits **en stock** (réceptions non expirées, non traitées DLC) sont affichés. Ordre de tri :
1. En stock en premier
2. Par DLC croissante (FIFO)
3. Alphabétique

Chaque tuile affiche :
- Badge `⭐ EN STOCK`
- Icône espèce
- Nom du produit
- DLC du lot FIFO (ex. : `DLC 17/05/2026`)
- N° de lot FIFO

**Sources** : le module accepte deux origines de stock — **réceptions de matières premières** et **fabrications maison** (produits finis crus). Un lot de fabrication est identifié par le badge `🔪 Fabrication` dans le sélecteur de lot.

### 5.3 Sélecteur de lot (visible si ≥ 2 lots disponibles)

Après sélection d'un produit ayant plusieurs lots, un sélecteur apparaît :
- Le **lot FIFO** (DLC la plus courte) est pré-sélectionné et marqué `⭐ FIFO`
- Format de chaque option : `⭐ FIFO — Lot XXX · DLC JJ/MM/AAAA · reçu JJ/MM/AAAA · Fournisseur`
- Les lots issus de fabrication indiquent `· fabriqué` et `· Fabrication maison`

Sous le sélecteur :
- **`📋 Historique de réception`** : ouvre une modale avec la liste de tous les lots, DLC, poids, fournisseur et un lien vers la fiche de réception
- **`Suivant →`** : confirme le lot choisi et passe à l'étape 3

Si le produit n'a qu'un seul lot, l'étape 3 s'ouvre automatiquement.

---

## 6. Étape 3 — Paramètres de cuisson

### 6.1 Formulaire

| Champ | Obligatoire | Notes |
|---|---|---|
| **Date** | Oui ✱ | Pré-remplie avec la date du jour |
| **Quantité** | Oui ✱ | Décimale (> 0) |
| **Unité** | Oui | Menu : `kg` (défaut) · `g` · `pièces` |
| **Heure début cuisson** | Oui ✱ | Pré-remplie avec l'heure courante |
| **Heure fin cuisson** | Oui ✱ | Saisie directe ou via raccourcis (voir 6.2) |
| **Température produit — sortie rôtissoire** | Oui ✱ | 0–120°C, décimale. Bouton rapide `75°C`. |
| **Action corrective** | Oui ✱ si T° < 75°C | Textarea, pré-remplie automatiquement si NC (voir 6.3) |

### 6.2 Raccourcis heure de fin

Deux méthodes de saisie rapide pour l'heure de fin :

**Boutons durée prédéfinis** (calculés depuis l'heure de début) :
`+1h` · `+1h30` · `+2h` · `+2h30` · `+3h`

**Saisie manuelle durée** : champs `h` + `min` + bouton `→` pour calculer et appliquer l'heure de fin.

> Si l'heure de début n'est pas renseignée au moment du clic, un message d'erreur s'affiche.

### 6.3 Badge de conformité et action corrective

Mis à jour en temps réel à chaque frappe dans le champ Température :

| Température | Badge affiché | Action corrective |
|---|---|---|
| Non saisie | *(masqué)* | *(masquée)* |
| ≥ 75°C | `✓ Conforme — X,X °C ≥ 75 °C` (vert) | Champ masqué et vidé |
| < 75°C | `⚠ Non conforme — X,X °C < 75 °C — action corrective requise` (rouge) | Champ visible, pré-rempli automatiquement |

**Texte pré-rempli automatiquement si T° < 75°C :**
> *"Remettre le produit en cuisson (four, rôtissoire, marmite) et prolonger le temps de cuisson jusqu'à l'atteinte de la température de 75 °C à cœur"*

Ce texte est **modifiable**. Si l'opérateur efface le texte et que la T° repasse au-dessus de 75°C, le champ action corrective est automatiquement masqué et vidé.

### 6.4 Historique récent

Sous le formulaire, un tableau affiche les **20 dernières cuissons de type rôtissoire**, avec : date, plage horaire, produit, quantité, opérateur, température (vert si ≥ 75°C, rouge sinon).

---

## 7. Après l'enregistrement — Modal de choix

Après une sauvegarde réussie, une modale **"Cuisson enregistrée"** (ou **"⚠ Cuisson enregistrée — non conforme"** si T° < 75°C) affiche 4 boutons :

| Bouton | Action |
|---|---|
| **🖨 Imprimer étiquette** | Génère et imprime l'étiquette thermique Brother 62 mm (voir section 9) |
| **🍗 Nouvelle cuisson** | Réinitialise entièrement le wizard (retour à l'étape 1) |
| **🏠 Retour au hub** | Redirige vers `/taches-hub.html` |
| **❄ Refroidissement du produit** | Sauvegarde les données en `sessionStorage` et redirige vers `/refroidissement.html` avec pré-remplissage |

---

## 8. Règles de conformité invisibles

### 8.1 Cible réglementaire : 75°C

La constante `TEMPERATURE_CIBLE = 75.0` est définie dans le backend. Une T° de sortie **strictement inférieure** à 75°C déclenche :
1. Le marquage `conforme = 0` en base de données
2. L'obligation d'une action corrective (rejet HTTP 422 si absente)

### 8.2 DLC automatique J+3, capée par la source

La DLC est calculée **exclusivement côté serveur** :
```
dlc_calculee = date_cuisson + DLC_JOURS_TRANSFORMATION (= 3 jours)
```

**Règle de plafonnement :** si la DLC du lot source (réception ou fabrication) est antérieure à `dlc_calculee`, alors :
```
dlc_finale = dlc_source  (et non dlc_calculee)
```

Dans ce cas, `dlc_ajustee = True` est retourné et une **alerte popup** s'affiche côté frontend :  
*"⚠ DLC ajustée — Le module Cuisson a ajusté la DLC calculée à la DLC d'origine du produit : JJ/MM/AAAA"*

### 8.3 Unicité de la source amont

Une cuisson ne peut être liée **qu'à une seule source** : soit un lot de réception (`reception_ligne_id`), soit un lot de fabrication (`fabrication_id`), jamais les deux simultanément. Le backend rejette une telle requête avec HTTP 422.

### 8.4 FIFO dans la sélection de lots

Lorsque le produit a plusieurs lots, le **lot FIFO** est identifié par le tri :
1. DLC ascendante (lot expirant le plus tôt en premier)
2. Date de réception/fabrication ascendante (à DLC égale, le plus ancien)

Le lot FIFO est pré-sélectionné automatiquement. L'opérateur peut le changer manuellement via le sélecteur.

### 8.5 Pré-remplissage depuis d'autres modules

Si la clé `cuisson_prefill` est présente en `sessionStorage` à l'ouverture de la page, le wizard pré-remplit automatiquement l'opérateur, le produit, la quantité et l'unité. Cette clé est supprimée immédiatement après lecture (usage unique).

### 8.6 Lien vers le refroidissement

Le bouton **"❄ Refroidissement du produit"** injecte les données suivantes dans `sessionStorage` (`refroidissement_prefill`) pour la page de refroidissement :
- `operateur_id`, `operateur_prenom`
- `produit_id`, `produit_nom`
- `cuisson_id` (pour lier les deux opérations)
- `temperature_sortie` (T° de fin de cuisson → T° initiale du refroidissement)
- `quantite`, `unite`

---

## 9. Ticket thermique imprimé (format 62 mm)

Déclenché par le bouton "🖨 Imprimer étiquette" via `POST /api/etiquettes/transformes` + `window.print()`.

| Zone | Contenu |
|---|---|
| **Tag** | `[CUIT]` encadré |
| **Nom produit** | Majuscules |
| **Quantité** | `Quantité : X kg` |
| **DLC** | Date en rouge format `JJ/MM/AA` — encadrée |
| **Lot** | `Lot : [numéro lot origine]` — pointillés |
| **Température** | `T° fin cuisson : X,X °C` |
| **Ligne action** | `Cuit le JJ/MM/AA à HHhMM` |
| **Pied** | `Par : [Prénom opérateur]` |

---

## 10. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Soumission sans opérateur | Retour étape 1 + erreur : *"Veuillez sélectionner un opérateur."* |
| Soumission sans produit | Retour étape 2 + erreur : *"Veuillez sélectionner un produit."* |
| Quantité ≤ 0 ou vide | Erreur : *"Quantité requise (> 0)."* |
| Heures manquantes | Erreur : *"Heures de début et fin requises."* |
| Température vide | Erreur : *"Température de sortie requise."* |
| T° < 75°C sans action corrective | Erreur : *"Action corrective obligatoire si T° < 75 °C."* |
| T° < 75°C + action vide (backend) | HTTP 422 : *"Action corrective obligatoire si température < 75 °C"* |
| Deux sources liées (backend) | HTTP 422 : *"Une cuisson ne peut pas être liée simultanément à une réception et à une fabrication."* |
| DLC ajustée à la DLC source | Popup alert : *"⚠ DLC ajustée — [date origine]"* |
| Heure de fin calculée sans heure de début | Erreur : *"Renseignez d'abord l'heure de début."* |
| Durée manuelle (champ h+min) sans heure de début | Erreur : *"Renseignez d'abord l'heure de début."* |
| Erreur API lors de l'impression étiquette | Toast : *"Erreur impression : [détail]"* |
| Erreur API sauvegarde | Erreur rouge sous le formulaire, bouton réactivé |
| Aucun produit en stock | Grille vide : *"Aucun produit trouvé."* |
| Aucun opérateur actif | Grille vide : *"Aucun opérateur actif."* |

---

# Module 10 — Refroidissement Rapide (≤ 10°C en ≤ 2h)

---

## 1. Objectif

Ce module enregistre le contrôle de refroidissement post-cuisson selon la règle HACCP : le produit cuit doit passer de sa température de sortie (minimum 75°C) à une température à cœur **≤ 10°C en 2 heures maximum**. Si le couple temps/température n'est pas respecté, le module guide obligatoirement vers la décision de jet du produit avec traçabilité automatique dans le calendrier DLC.

---

## 2. Chemin d'accès

Hub principal → **Production** → tuile **❄️ REFROIDISSEMENT**.

URL directe : `/refroidissement.html`

---

## 3. Structure générale : wizard 3 étapes

Identique à la structure du module Cuisson (même architecture). Bandeau `👤 [Opérateur] · 📦 [Produit]` visible dès les deux premiers choix faits.

| Étape | Titre |
|---|---|
| 1 | Qui refroidit ? |
| 2 | Quel produit ? |
| 3 | Données du refroidissement |

Inactivité 5 minutes → redirection vers `/hub.html`.

---

## 4. Étape 1 — Sélection de l'opérateur

Identique au module Cuisson : grille de tuiles avec initiale et prénom, triés alphabétiquement. Un clic sélectionne et avance à l'étape 2 après 150 ms.

---

## 5. Étape 2 — Sélection du produit

> *"Uniquement les produits passés en cuisson."*

La liste provient de `GET /api/refroidissement/produits` qui retourne **uniquement les cuissons disponibles à refroidir** : cuissons non encore refroidies, non jetées, DLC non dépassée.

Chaque tuile affiche :
- Icône 🥩
- Nom du produit
- Date de cuisson (ex. : `Cuisson du 14/05/2026`)
- N° de lot

Si la liste est vide : *"Aucun produit cuit. Enregistrez d'abord une cuisson."*

Un clic sur une tuile avance automatiquement à l'étape 3 après 150 ms.

---

## 6. Étape 3 — Données du refroidissement

### 6.1 Formulaire

| Champ | Obligatoire | Notes |
|---|---|---|
| **Date** | Oui ✱ | Pré-remplie avec la date du jour |
| **Heure mise en refroidissement** | Oui ✱ | Pré-remplie avec l'heure courante à l'arrivée à l'étape 3 |
| **Heure fin refroidissement** | Oui ✱ | Pré-remplie automatiquement à `début + 2h` (maximum réglementaire). Boutons rapides disponibles. |
| **T° à cœur avant refroidissement** | Oui ✱ | Pré-remplie à `75` (ou depuis la cuisson liée si navigation directe). Cible minimum : ≥ 75°C. |
| **T° à cœur après refroidissement** | Oui ✱ | Décimale. Cible réglementaire : ≤ 10°C. |

### 6.2 Raccourcis heure de fin

Boutons de durée prédéfinis (calculés depuis l'heure de début) :
- `+1h`
- `+1h30`
- **`+2h (max)`** — mis en évidence, c'est la durée maximale réglementaire, pré-sélectionné par défaut

> Si l'heure de début n'est pas renseignée au clic, un message d'erreur s'affiche.

---

## 7. Bandeaux de conformité (temps réel)

Mis à jour à chaque frappe dans les champs Température initiale, Température finale et Heures.

La conformité globale combine **trois vérifications indépendantes** :

| Vérification | Cible | Libellé si KO |
|---|---|---|
| Cuisson suffisante | T°initiale ≥ 75°C | `cuisson insuffisante X,X °C < 75 °C` |
| T° finale atteinte | T°finale ≤ 10°C | `T° finale X,X °C > 10 °C` |
| Durée respectée | Durée ≤ 120 min | `durée Xh XX > 2 h` |

### Bandeau vert — Conforme

`✓ Conforme — cuisson X,X °C · refroidissement X,X °C en Xh`

Affiché uniquement si les **trois** conditions sont vérifiées.

### Bandeau rouge — Non conforme

`⚠ Non conforme — [raison 1] · [raison 2] …— action corrective requise`

Affiché dès qu'une condition n'est pas respectée.

### Bandeau spécifique "CUISSON INSUFFISANTE" — T°initiale < 75°C

```
⚠ CUISSON INSUFFISANTE — T° à cœur < 75 °C à la sortie cuisson.
Pourquoi : En dessous de 75 °C à cœur, les bactéries pathogènes ne sont pas éliminées.
Action corrective : Remettre le produit en cuisson...
```

Ce bandeau inclut un bouton **`🔥 Remettre en cuisson`** qui injecte les données du refroidissement en cours dans `sessionStorage` (`cuisson_prefill`) et redirige vers `/cuisson.html` avec opérateur et produit pré-sélectionnés.

### Bandeau "JETER LES PRODUITS"

`⛔ JETER LES PRODUITS — couple temps/température de refroidissement non respecté (durée > 2 h ET T° finale > 10 °C).`

Ce bandeau s'affiche **uniquement si les deux conditions refroidissement sont simultanément KO** : durée > 2h ET T° finale > 10°C.

---

## 8. Section "Action corrective" — Procédure de jet

Visible dès qu'un cas non conforme est détecté.

### Étape 1 — Bouton de confirmation

Bouton rouge foncé : **`⛔ Confirmer : Jeter le produit`**

Note sous le bouton : *"Ce produit sera retiré du stock et enregistré comme jeté dans le calendrier."*

### Étape 2 — Après confirmation (irréversible sauf annulation explicite)

- Bandeau vert foncé : `✓ Produit marqué comme JETÉ — retiré du stock`
- Champ **"Note optionnelle"** : cause, quantité, N° lot…
- Bouton **`✕ Annuler`** : remet le formulaire à l'état "en attente de confirmation" (le jet n'est pas encore enregistré tant que la fiche n'est pas soumise)

> **Important** : le jet n'est effectif en base de données qu'à la soumission du formulaire, pas au clic sur "Confirmer". Annuler avant de soumettre reste possible.

### Blocage de soumission sans confirmation

Si le refroidissement est non conforme et que l'opérateur n'a pas cliqué sur "Confirmer : Jeter le produit", la soumission est bloquée avec le message :  
*"Confirmez l'action 'Jeter le produit' avant d'enregistrer ([raisons])."*

---

## 9. Historique récent

20 derniers refroidissements avec : date, plage horaire, durée, produit, N° lot, opérateur, T° finale (vert si conforme, rouge sinon). Préfixe `⛔ JETER` pour les produits jetés.

---

## 10. Après l'enregistrement — Modal de choix

| Titre modal | Condition |
|---|---|
| `✓ Refroidissement enregistré` | Conforme |
| `⚠ Refroidissement enregistré — non conforme` | NC sans jet |
| `⛔ Refroidissement enregistré — produits à jeter` | Jet confirmé |

Boutons disponibles :

| Bouton | Condition | Action |
|---|---|---|
| **🖨 Imprimer étiquette** | **Masqué si produit jeté** | Génère étiquette thermique 62 mm avec tag `[REFROIDI]` |
| **❄ Nouveau refroidissement** | Toujours visible | Réinitialise le wizard |
| **🏠 Retour au hub** | Toujours visible | Redirige vers `/taches-hub.html` |

---

## 11. Règles de conformité invisibles

### 11.1 Règle de jet — Conjonction obligatoire

La règle de jet **refroidissement** exige que les **deux** conditions soient simultanément non respectées :

```
jeter_refroidissement = (durée > 2h) ET (T°finale > 10°C)
```

Si seulement la durée dépasse 2h mais que la T° finale est ≤ 10°C → NC mais **pas de jet**.  
Si seulement la T° finale dépasse 10°C mais que la durée est ≤ 2h → NC mais **pas de jet**.

La règle de jet **cuisson** est distincte et indépendante :

```
jeter_cuisson = (T°initiale < 75°C)
```

Le `jeter` global = `jeter_cuisson OU jeter_refroidissement`.

### 11.2 DLC automatique J+3, capée par la source

Même règle que la Cuisson :
```
dlc_calculee = date_refroidissement + 3j
dlc_finale = min(dlc_calculee, dlc_source)
```

La DLC source est remontée depuis la cuisson liée → ligne de réception d'origine (ou fabrication). Si la DLC est ajustée → popup alert.

### 11.3 Entrée `dlc_devenir` créée automatiquement si jet

Si `jeter_action = True` à la soumission, le backend crée automatiquement une entrée dans la table `dlc_devenir` avec `statut = "jete"`. **Le produit disparaît alors du stock et du calendrier DLC** dès l'enregistrement. Cette action est **définitive** (elle peut être annulée ultérieurement via le calendrier DLC en marquant le devenir comme "annule").

### 11.4 Pré-remplissage depuis la Cuisson

Si la page est ouverte depuis le bouton **"❄ Refroidissement du produit"** du module Cuisson, les données de `sessionStorage` (`refroidissement_prefill`) sont lues et appliquées :

| Donnée | Application |
|---|---|
| `operateur_id` | Opérateur pré-sélectionné (tuile mise en évidence) |
| `produit_id` + `produit_nom` | Produit pré-sélectionné (tuile mise en évidence, ou objet virtuel si absent de la liste) |
| `cuisson_id` | Lien avec la cuisson source |
| `temperature_sortie` | Pré-remplit la T° à cœur avant refroidissement |
| `quantite` + `unite` | Conservés pour le bouton "Remettre en cuisson" |

Si opérateur ET produit sont présents → **saut direct à l'étape 3** (étapes 1 et 2 ignorées).

### 11.5 Calcul de la durée — Passage minuit

La durée est calculée comme `fin - début` en minutes. Si `fin ≤ début`, le système suppose un passage minuit et ajoute 24h :  
*Exemple : début 23:30, fin 01:30 → 120 minutes.*

### 11.6 Heure de fin pré-remplie à `+2h`

À l'arrivée à l'étape 3, si aucune heure de fin n'est déjà saisie, le système calcule automatiquement `heure_fin = heure_debut + 120 min` et active le bouton `+2h (max)`. Ce comportement est déclenché par un `MutationObserver` sur la visibilité de l'étape 3.

---

## 12. Ticket thermique imprimé (format 62 mm)

Déclenché par le bouton "🖨 Imprimer étiquette" via `POST /api/etiquettes/transformes` avec `source_type = "refroidissement"`.

| Zone | Contenu |
|---|---|
| **Tag** | `[REFROIDI]` encadré |
| **Nom produit** | Majuscules |
| **Quantité** | Quantité héritée de la cuisson source |
| **DLC** | Date en rouge format `JJ/MM/AA` — encadrée |
| **Lot** | N° de lot de la réception d'origine |
| **Température** | `T° fin refroidissement : X,X °C` |
| **Ligne action** | `Refroidi le JJ/MM/AA à HHhMM` |
| **Pied** | `Par : [Prénom opérateur]` |

---

## 13. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Soumission sans opérateur | Retour étape 1 + erreur |
| Soumission sans produit | Retour étape 2 + erreur |
| Heures manquantes | Erreur : *"Heures de début et fin requises."* |
| Durée ≤ 0 | Erreur : *"Durée de refroidissement invalide."* |
| T° initiale vide | Erreur : *"Température à cœur avant refroidissement requise."* |
| T° finale vide | Erreur : *"Température à cœur après refroidissement requise."* |
| NC sans confirmation jet | Erreur : *"Confirmez l'action 'Jeter le produit' avant d'enregistrer ([raisons])."* |
| NC sans action corrective (backend) | HTTP 422 avec détail des raisons |
| DLC ajustée à la DLC source | Popup alert : *"⚠ DLC ajustée — [date origine]"* |
| Heure de fin rapide sans heure de début | Erreur : *"Renseignez d'abord l'heure de mise en refroidissement."* |
| Erreur impression étiquette | Toast : *"Erreur impression : [détail]"* |
| Liste produits vide | *"Aucun produit cuit. Enregistrez d'abord une cuisson."* |

---

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

# Module 12 — Stock Unifié FIFO

---

## 1. Objectif

Ce module offre une **vue unifiée et en temps réel de tout le stock** de l'établissement, quel que soit son origine : matières premières réceptionnées, fabrications maison, produits cuits, produits refroidis. Il permet de consulter l'état FIFO, de filtrer par n'importe quel critère, et de traiter les produits (sortie du stock par vente, consommation, jet) ou de corriger une DLC / une quantité.

---

## 2. Chemin d'accès

Hub principal → **📋 Stock unifié** (ou lien direct `/inventaire.html`).

---

## 3. Les quatre sources du stock

Le stock unifié agrège **quatre tables source** avec une icône distinctive par type :

| Icône | Source | Type | Description |
|---|---|---|---|
| 📦 | `reception_ligne` | Brut | Matières premières reçues de fournisseurs |
| 🔪 | `fabrication` | Fini | Produits fabriqués maison (non cuits) |
| 🔥 | `cuisson` | Fini | Produits cuits, pas encore refroidis |
| ❄️ | `refroidissement` | Fini | Produits cuits+refroidis, prêts à vendre |

**Tri FIFO appliqué** : DLC ascendante (lot expirant le plus tôt en premier), puis date d'origine ascendante (à DLC égale, lot le plus ancien en premier).

**Exclusions automatiques** : les lots ayant un enregistrement `dlc_devenir` (déjà traités comme vendus, consommés, jetés…) sont invisibles dans le stock.

---

## 4. Interface

### 4.1 Bandeau de statistiques

Six compteurs mis à jour à chaque chargement :

| Compteur | Contenu |
|---|---|
| **Total** | Nombre total de lots en stock |
| **📦 Réceptions** | Lots issus de réceptions fournisseur |
| **🔪 Fabrications** | Lots issus de fabrications maison |
| **🔥 Cuissons** | Lots issus de cuissons |
| **❄️ Refroidis** | Lots issus de refroidissements |
| **⏰ ≤ 3 jours** | Lots dont la DLC expire dans 0 à 3 jours (hors périmés) |

### 4.2 Filtres

Les filtres se divisent en deux catégories :

#### Filtres serveur (déclenchent un rechargement depuis l'API)

| Filtre | Valeurs | Notes |
|---|---|---|
| **Type** | Tous / 📦 Bruts (réception) / 🔪🔥❄️ Finis (transformés) | — |
| **Catégorie** | Toutes + catégories présentes | Menu dynamique |
| **DLC max** | Date au format AAAA-MM-JJ | Affiche uniquement les lots expirant avant cette date |
| **Inclure périmés** | Case à cocher | Par défaut : périmés exclus |

#### Filtres client (instantanés, sans rechargement réseau)

| Filtre | Notes |
|---|---|
| **Recherche** | Texte libre : nom du produit OU N° de lot. Insensible à la casse et aux accents. Délai 150 ms après la dernière frappe. Autocomplete avec bouton chevron `▾`. |
| **Espèce** | Menu dynamique alimenté par les espèces présentes dans le stock chargé. |
| **Tri** | DLC ↑ (urgent en premier — défaut) / DLC ↓ / Nom A→Z / Nom Z→A / Plus récent / Plus ancien |

Bouton **`Réinitialiser`** : remet tous les filtres à leur valeur par défaut et recharge depuis l'API.

#### Autocomplete de la recherche

Cliquer sur le bouton **`▾`** ou saisir dans le champ affiche une liste déroulante des produits correspondants, avec pour chaque produit : nom, nombre d'unités en stock, espèce(s). Cliquer sur un produit filtre la liste.

### 4.3 Carte d'article

Chaque lot est représenté par une carte colorée selon l'urgence DLC :

| Couleur | Condition |
|---|---|
| ⬛ Noir | Périmé (jours_restants < 0) — badge `Périmé J-X` |
| 🔴 Rouge | ≤ 1 jour — badge `Demain` ou `Aujourd'hui` |
| 🟠 Orange | ≤ 3 jours — badge `J+X` |
| 🟡 Jaune | ≤ 7 jours — badge `J+X` |
| 🟢 Vert | ≥ 8 jours — badge `J+X` |
| ⬜ Gris | Pas de DLC — badge `—` |

Contenu d'une carte :
- Icône source (📦 / 🔪 / 🔥 / ❄️)
- Nom du produit
- Méta : `Lot [N°] · [Quantité] [Unité] · Frn : [Fournisseur] · Origine : [Date]`
- Catégorie du produit
- Badge jours restants + date `DLC : JJ/MM/AAAA` ou `DLUO : JJ/MM/AAAA`

---

## 5. Mode Gestion

### Activation

Cliquer sur le bouton **`✏️ Gérer`** dans la barre de titre active le mode gestion :
- Les cartes affichent des cases à cocher
- Cliquer sur une carte = toggle sélection (au lieu d'ouvrir la modale de modification)
- Une **barre d'action flottante** apparaît en bas de l'écran

### Barre d'action flottante

| Élément | Comportement |
|---|---|
| Compteur | `N produit(s) sélectionné(s)` |
| Bouton `✏️ Modifier` | Actif uniquement si **exactement 1** article sélectionné. Ouvre la modale de modification. |
| Bouton `🗑️ Traiter la sélection` | Actif si ≥ 1 article sélectionné. Ouvre la modale de traitement en masse. |

### Désactivation

Re-cliquer sur `✏️ Gérer` désactive le mode, efface la sélection et referme la barre flottante.

---

## 6. Modale "Traitement des produits sélectionnés"

Ouverte via le bouton **`🗑️ Traiter la sélection`**.

| Élément | Notes |
|---|---|
| Résumé | `N produit(s) sélectionné(s) à traiter` |
| Case "Tout sélectionner" | Coche/décoche toutes les cases de la liste |
| Liste des produits | Cases à cocher individuelles. Chaque ligne affiche : icône, nom, DLC, lot, quantité, fournisseur. Couleur selon urgence DLC. |
| **Prénom opérateur** | Obligatoire ✱ — menu déroulant personnel |
| **Devenir** | Obligatoire ✱ — 4 options : `🗑️ Jeté` / `💰 Vendu` / `✅ Consommé` / `❓ Autre` |
| Commentaire | Optionnel — raison commune |
| Bouton `Confirmer le traitement` | Actif si ≥ 1 coché + opérateur + devenir sélectionnés |

Après confirmation : les produits traités disparaissent du stock (entrée `dlc_devenir` créée), le stock est rechargé, un `alert` indique le nombre de produits traités.

---

## 7. Modale "Modifier le produit"

Ouverte en cliquant directement sur une carte (hors mode gestion) ou via `✏️ Modifier` en mode gestion.

| Champ | Modifiable | Notes |
|---|---|---|
| Nom du produit | Non | Lecture seule |
| N° de lot | **Non — jamais** 🔒 | Affiché en lecture seule avec icône cadenas |
| **DLC** | Oui | Obligatoire si une valeur existe. Format `AAAA-MM-JJ`. |
| **Quantité** | Oui (sauf refroidissement) | Décimale ≥ 0. **Masquée pour les articles de source `refroidissement`** (pas de champ quantité dans cette table). Unité affichée entre parenthèses. |

Boutons :
- **`Enregistrer les modifications`** → `PATCH /api/stock/{source_type}/{source_id}` avec DLC et/ou quantité
- **`🖨️ Imprimer étiquette`** → impression locale via `window.print()` (sans appel à l'imprimante Brother)

---

## 8. Étiquette imprimée depuis l'inventaire

Imprimée via `window.print()` avec le gabarit caché `#print-label-inv` (format 62 mm). Elle est générée **sans appel API supplémentaire** à partir des données déjà affichées dans la modale.

| Zone | Contenu |
|---|---|
| **Tag** (optionnel) | `[FABRIQUÉ]` / `[CUIT]` / `[REFROIDI]` — absent pour les réceptions |
| **Nom produit** | Majuscules |
| **N° Lot** | `N° Lot : [numéro]` |
| **DLC** | `DLC : JJ/MM/AA` (format court) |
| **Ligne d'origine** | Selon la source : |
| | Réception : `Réceptionné le JJ/MM/AA à HHhMM par [Prénom]` |
| | Fabrication : `Fabriqué le JJ/MM/AA à HHhMM` |
| | Cuisson : `Cuit le JJ/MM/AA à HHhMM` |
| | Refroidissement : `Refroidi le JJ/MM/AA à HHhMM` |

---

## 9. Règles de conformité invisibles

### 9.1 Le numéro de lot est immuable

Le numéro de lot n'est **jamais modifiable**, ni depuis l'interface (champ verrouillé avec icône 🔒), ni par l'API (le backend ignore tout changement de lot dans `PATCH`). Seuls la **DLC** et la **quantité** peuvent être corrigés après coup.

### 9.2 Clé d'identification unique

Chaque article en stock est identifié par la clé composite **`source_type:source_id`** (ex. : `reception_ligne:42`). Cette clé est utilisée en interne pour la sélection, la modification et le traitement batch.

### 9.3 Deux niveaux de filtrage distincts

| Type | Déclenchement | Données concernées |
|---|---|---|
| **Filtres serveur** (Type, Catégorie, DLC max, Inclure périmés) | Rechargement API complet | Toutes les données, incluant les articles hors des filtres client |
| **Filtres client** (Recherche, Espèce, Tri) | Instantané, côté JS | Uniquement les données déjà chargées en mémoire |

**Conséquence pratique** : si un article n'est pas visible après application d'un filtre Espèce, il faut vérifier que les filtres serveur (Type, Catégorie) ne l'excluent pas.

### 9.4 Quantité masquée pour les refroidissements

Les articles de type `refroidissement` n'ont pas de champ `quantite` dans la base de données (la quantité est héritée de la cuisson source). Le champ est donc **masqué** dans la modale de modification pour ce type.

### 9.5 Compteur ≤ 3 jours

Le compteur `⏰ ≤ 3 jours` du bandeau de statistiques compte les articles dont `0 ≤ jours_restants ≤ 3` — les périmés (jours_restants < 0) sont **exclus** de ce compteur.

---

## 10. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Erreur de chargement du stock | Message rouge dans la liste : *"Erreur de chargement : [détail]"* |
| DLC vide lors de la modification (si valeur existante) | `alert("La date DLC est obligatoire.")` |
| Quantité invalide (< 0 ou non numérique) | `alert("Quantité invalide.")` |
| Erreur API lors de la modification | `alert("Erreur : [détail]")` |
| Erreur API lors du traitement batch | `alert("Erreur : [détail]")` |
| Aucun produit pour les filtres actifs | *"Aucun produit en stock pour ces filtres."* |

---

# Module 13 — Calendrier DLC

---

## 1. Objectif

Le Calendrier DLC offre une visualisation temporelle de toutes les dates limites de consommation du stock — toutes sources confondues. Il permet de repérer d'un coup d'œil les produits urgents, d'enregistrer leur devenir (vendu, consommé, jeté) et de corriger une DLC erronée. C'est le principal outil de gestion des sorties de stock par date.

---

## 2. Chemin d'accès

Hub principal → **CALENDRIER DLC** (ou lien direct `/dlc.html`).

---

## 3. Interface générale

### 3.1 Barre de navigation

| Élément | Rôle |
|---|---|
| Boutons `Semaine` · `Mois` · `Annuel` | Changer la vue (vue **Mois** active par défaut) |
| Bouton `‹` | Reculer d'une période (−7j / −1 mois / −1 an) |
| Label central | Période affichée (ex. : `Mai 2026`, `S21 2026`, `2026`) |
| Bouton `›` | Avancer d'une période |
| Bouton `Aujourd'hui` | Revenir à la période courante |

### 3.2 Filtres

| Filtre | Comportement |
|---|---|
| **Recherche** (texte) | Nom du produit OU N° de lot, insensible casse/accents. Filtre le rendu **sans rechargement API**. Autocomplete ▾. |
| **Source** | Toutes / 📦 Réception / 🔪 Fabrication / 🔥 Cuisson / ❄️ Refroidissement. Envoyé à l'API → rechargement. |
| **Statut** | Tous / À traiter (expirés non traités) / Traités / Actifs (non expirés). Appliqué côté client après chargement. |
| **⚡ Traiter les expirés (N)** | Bouton visible **uniquement** s'il existe des produits expirés non traités dans la période affichée. Ouvre la modale de traitement en masse. |

### 3.3 Légende

```
🔴 Expiré / critique  🟠 Urgent  🟡 Attention  🟢 OK  ⬜ Traité
```

---

## 4. Vue Mois (défaut)

Grille calendrier standard **lundi → dimanche**, couvrant le mois complet (avec les jours des mois adjacents en grisé).

- Le **jour courant** est surlighné.
- Les jours d'un autre mois sont estompés.
- Chaque case de jour affiche des **badges colorés** avec compteur :
  - `🔴 N` : produits expirés ou critiques (badge clignote si produits expirés non traités)
  - `🟠 N` : produits urgents
  - `🟡 N` : produits en attention
  - `🟢 N` : produits OK
  - `⬜ N` : produits déjà traités
- Cliquer sur un jour avec badges → ouvre la **modale du jour**.

---

## 5. Vue Semaine

Grille à 7 colonnes (Lun → Dim) affichant la semaine ISO courante.

- Colonne du jour actuel surlignée.
- Chaque case affiche directement les noms des produits avec leur icône source (📦🔪🔥❄️).
- Cliquer sur une colonne ayant des produits → ouvre la **modale du jour**.

---

## 6. Vue Annuelle

Grille **3 × 4** de mini-mois (Janvier → Décembre).

Pour chaque mois :
- Nom du mois
- Points colorés avec compteurs (`🔴 N 🟠 N 🟡 N 🟢 N ⬜ N`)
- `N produit(s)` total (ou `—` si vide)
- Mois courant mis en évidence

**Cliquer sur un mois** → bascule en **vue Mois** sur ce mois.

---

## 7. Modale du jour

Titre : `DLC du JJ/MM/AAAA`

### Contenu pour chaque produit

| Élément | Détail |
|---|---|
| **Nom du produit** | Coloré selon l'urgence DLC |
| **Méta** | Icône source · `Lot : X` · `Quantité X unité` · `Frn : X` · `Origine : JJ/MM/AAAA` |
| **Bloc devenir** (si déjà traité) | `✓ [Statut] — [Opérateur] le JJ/MM/AAAA`<br>Et si commentaire : `« [Commentaire] »` |
| **Action primaire** | Selon source (voir tableau ci-dessous) |
| **🖨️ Imprimer** | Toujours visible |
| **📅 Modifier DLC** | Visible uniquement si produit non traité |
| **🗑️ Supprimer** | Visible uniquement si produit non traité |
| **✏️ Correction / ✏️ Actualiser** | Toujours visible — "Correction" si non traité, "Actualiser" si déjà traité |

### Actions primaires selon la source

| Source | Action affichée |
|---|---|
| 📦 Réception | `🔗 Voir la fiche` → lien vers `/reception-detail.html?id=X&retour=dlc` |
| 🔪 Fabrication | `▾ N ingrédient(s)` → zone dépliable avec détail des ingrédients |
| 🔥 Cuisson | *(aucune action primaire)* |
| ❄️ Refroidissement | *(aucune action primaire)* |

### Dépliable ingrédients (fabrication)

Cliquer sur `▾ N ingrédient(s)` (devient `▴` quand ouvert) affiche :
- Poids fabriqué `⚖️ X kg fabriqués`
- Par ingrédient : **Nom** · **Quantité** (calculée proportionnellement si poids connu) · **Lot** · **DLC** · **🔗** (lien vers la réception d'origine si disponible)

---

## 8. Modale "Devenir du produit" (✏️ Correction / ✏️ Actualiser)

S'ouvre au clic sur **✏️ Correction** (produit non traité) ou **✏️ Actualiser** (produit déjà traité, pour corriger).

| Champ | Obligatoire | Notes |
|---|---|---|
| **Prénom opérateur** | Oui ✱ | Menu déroulant personnel |
| **Devenir** | Oui ✱ | 4 options : `🗑️ Jeté` / `💰 Vendu` / `✅ Consommé` / `❓ Autre` |
| **Commentaire** | Non | Raison, quantité... |

Bouton **`Confirmer`** : actif uniquement si opérateur et devenir sont sélectionnés. Après confirmation : calendrier rechargé, produit affiché en gris (traité).

---

## 9. Modale "Modifier la DLC"

S'ouvre au clic sur **📅 Modifier DLC** (uniquement pour produits non traités).

Affiche le nom du produit et la DLC actuelle. Champ de saisie **Nouvelle date DLC** (obligatoire).

Bouton **`Confirmer`** : actif uniquement si une date est saisie. Appelle `PUT /api/dlc/modifier-dlc` qui modifie la DLC directement dans la table source (réception, fabrication, cuisson ou refroidissement). Après confirmation : calendrier rechargé.

---

## 10. Suppression (🗑️ Supprimer)

Cliquer **🗑️ Supprimer** affiche un dialog de confirmation :  
*"Supprimer « [Nom produit] » du calendrier DLC ? Cette action est réversible via le bouton Correction."*

Si confirmé → crée une entrée `dlc_devenir` avec `statut = "annule"` (sans opérateur ni commentaire). Le produit disparaît du calendrier dans les vues filtrées. Il reste visible en filtrant sur "Traités" et peut être "réactivé" en cliquant **✏️ Actualiser** et en choisissant un autre statut.

---

## 11. Modale "Traitement en masse — DLC dépassées"

S'ouvre au clic sur **⚡ Traiter les expirés (N)**.

Affiche uniquement les produits **expirés non traités** (`DLC < aujourd'hui` + pas de `devenir_statut`), triés par DLC ascendante.

| Élément | Notes |
|---|---|
| Résumé | `N produit(s) dépassé(s) non traité(s)` |
| Case "Tout sélectionner" | Coche/décoche tous |
| Liste produits | Cases à cocher individuelles. Chaque ligne : icône, nom, DLC, lot, quantité, fournisseur. |
| **Prénom opérateur** | Obligatoire ✱ |
| **Devenir** | Obligatoire ✱ — même 4 options |
| **Commentaire** | Optionnel — raison commune |
| Bouton `Confirmer le traitement` | Actif si ≥1 coché + opérateur + devenir |

Après confirmation → `POST /api/dlc/devenir/batch` → calendrier rechargé + `alert("✅ N produit(s) traité(s).")`.

---

## 12. Règles de conformité invisibles

### 12.1 Seuils d'alerte DLC configurables

Les seuils de couleur sont stockés en base de données (table `parametres`) et retournés par l'API à chaque chargement :

| Couleur | Seuil par défaut | Condition |
|---|---|---|
| 🔴 Rouge | ≤ 1 jour | `jours_restants ≤ rouge_jours` OU `jours_restants < 0` (périmé) |
| 🟠 Orange | ≤ 3 jours | `jours_restants ≤ orange_jours` |
| 🟡 Jaune | ≤ 7 jours | `jours_restants ≤ jaune_jours` |
| 🟢 Vert | > 7 jours | Aucun seuil dépassé |
| ⬜ Gris | — | Produit avec `devenir_statut` renseigné |

Les seuils doivent respecter la contrainte : `rouge ≤ orange ≤ jaune`. Ils sont modifiables via `PUT /api/dlc/parametres` (accessible depuis l'administration).

### 12.2 5 statuts "devenir"

| Statut interne | Libellé affiché |
|---|---|
| `jete` | Jeté |
| `vendu` | Vendu |
| `consomme` | Consommé |
| `autre` | Autre |
| `annule` | Annulé (suppression réversible) |

Le statut `annule` est le seul créé **sans opérateur** (via le bouton "🗑️ Supprimer"). Les 4 autres nécessitent un opérateur.

### 12.3 Plage de chargement selon la vue

L'API reçoit `date_debut` et `date_fin` calculées côté JavaScript :

| Vue | Plage envoyée à l'API |
|---|---|
| Semaine | Du lundi au dimanche de la semaine ISO courante |
| Mois | Du premier au dernier jour du mois (étendu pour la grille 7 colonnes) |
| Annuel | Du 01/01 au 31/12 de l'année |

**Conséquence** : en vue Mois, les cases des jours des mois adjacents (hors mois cible) sont visibles et cliquables — elles contiennent des données réelles si des DLC tombent ces jours-là.

### 12.4 Filtre Statut côté client

Le filtre **Statut** (À traiter / Traités / Actifs) est appliqué **côté JavaScript** via `passeFiltreStatut()`, après chargement des données. Il ne réduit pas les données récupérées de l'API. Les définitions exactes :

| Filtre Statut | Condition JavaScript |
|---|---|
| `À traiter` | `DLC < aujourd'hui AND pas de devenir_statut` |
| `Traités` | `devenir_statut` renseigné |
| `Actifs` | `DLC ≥ aujourd'hui` (inclut les produits traités actifs) |

### 12.5 Badge rouge clignotant

Un badge rouge **clignote** si des produits **expirés** (DLC < aujourd'hui) et **non traités** existent pour ce jour. Ce clignotement est l'indicateur le plus urgent du calendrier.

### 12.6 Impression étiquette DLC

Via `window.print()` sans appel à l'imprimante Brother. Gabarit `#print-label-dlc` format 62 mm :
- Tag optionnel `[FABRIQUÉ]` / `[CUIT]` / `[REFROIDI]` (absent pour réception)
- Nom produit, N° lot, DLC
- Ligne d'origine selon source

---

## 13. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Erreur chargement calendrier | Message d'erreur dans la zone principale |
| Modification DLC sans date | Bouton "Confirmer" reste désactivé |
| Devenir sans opérateur ou statut | Bouton "Confirmer" reste désactivé |
| Erreur API devenir | `alert("Erreur : [détail]")` |
| Erreur API modifier DLC | `alert("Erreur : [détail]")` |
| Suppression annulée par l'utilisateur | Rien (le `confirm` a été refusé) |
| Traitement batch sans sélection | Bouton "Confirmer le traitement" désactivé |

---

# Module 14 — Ouvertures de Conditionnement

---

## 1. Objectif

Ce module enregistre chaque ouverture de produit sous-vide avec photo à l'appui. Il trace qui a ouvert quoi, quand, et si possible à quel lot de réception le produit correspond. La photo sert de preuve en cas de contrôle sanitaire. Une étiquette thermique `[OUVERT]` peut être imprimée immédiatement.

---

## 2. Chemins d'accès

| Page | URL | Accès |
|---|---|---|
| **Enregistrer une ouverture** | `/ouverture.html` | Hub principal → tuile ou lien **Ouverture sous-vide** |
| **Historique des ouvertures** | `/ouvertures-historique.html` | Accessible depuis le Hub (lien dédié) |

---

## 3. Page d'ouverture — Wizard 3 étapes

Wizard guidé avec barre de 3 points de progression. Un bandeau `👤 [Prénom]` est affiché aux étapes 2 et 3.

| Dot | Étape | Titre |
|---|---|---|
| ● | 1 | Qui ouvre ? |
| ● | 2 | Prendre la photo |
| ● | 3 | Choisir le produit |

Inactivité 5 minutes → redirection automatique vers `/hub.html`.

---

## 4. Mode d'emploi pas-à-pas

### 4.1 Étape 1 — Qui ouvre ?

Grille de boutons avec le prénom de chaque membre du personnel actif.

Cliquer un prénom → le sélectionne (mis en évidence) et avance **automatiquement** vers l'étape 2 après 200 ms.

---

### 4.2 Étape 2 — Prendre la photo

Bouton central **`📷 PRENDRE LA PHOTO`** qui déclenche la caméra de l'appareil.

Après prise de la photo :
- Un **aperçu miniature** s'affiche avec la mention `✓ Photo prise`
- L'avance vers l'étape 3 est **automatique** après 450 ms

> La photo est **obligatoire**. Le backend rejette toute ouverture sans photo.

---

### 4.3 Étape 3 — Choisir le produit

#### Champ de recherche

Recherche par nom de produit ou code unique. Deux comportements :
1. **Filtrage immédiat** sur la liste déjà chargée (insensible à la casse)
2. **Appel API** après 350 ms pour enrichir les résultats avec les lots disponibles

#### Liste organisée en deux sections

| Section | Contenu |
|---|---|
| **Produits en stock** | Produits ayant une réception dans les 21 derniers jours — triés par date de réception décroissante |
| **Catalogue** | Reste du catalogue matières premières (sans lot lié) |

Chaque carte produit affiche :
- **Nom** du produit
- **Espèce** (si renseignée)
- **N° de lot** et **DLC** (si produit issu d'une réception récente)
- **"Reçu le JJ/MM/AA"** (si réception mais sans lot ni DLC)
- **Code unique** (affiché à droite de la carte)

Cliquer sur une carte → la sélectionne (mise en évidence) et active le bouton d'enregistrement.

#### Bouton "✔ Enregistrer l'ouverture"

Actif uniquement si un produit est sélectionné. Si cliqué sans sélection → message d'erreur : *"Veuillez sélectionner un produit."*

---

### 4.4 Écran de confirmation

Après enregistrement réussi :

- ✅ **"Ouverture enregistrée"**
- Détail : Nom du produit · Opérateur · Lot (si disponible) · DLC (si disponible)

Trois boutons :

| Bouton | Action |
|---|---|
| **🖨️ Imprimer l'étiquette** | Remplit et imprime le gabarit thermique. Annule le compte à rebours. |
| **↩ Même produit** | Retour à l'étape 2 (Photo) en **conservant** opérateur et produit sélectionné |
| **✦ Nouvelle ouverture** | Reset complet, retour à l'étape 1 |

**Compte à rebours** : retour automatique vers `/hub.html` après **5 secondes** (affichage `Retour à l'accueil dans Xs…`).

---

## 5. Ticket thermique `[OUVERT]`

Imprimé via `window.print()` (gabarit local, sans appel à l'imprimante Brother). Format 62 mm.

| Zone | Contenu |
|---|---|
| **Tag** | `[OUVERT]` encadré |
| **Nom produit** | Majuscules |
| **DLC** | Format `JJ/MM/AA` en rouge — encadrée |
| **Lot** | `Lot : [numéro]` ou `Lot : —` |
| **Ligne action** | `Ouvert le JJ/MM/AA à HHhMM` |
| **Pied** | `Par : [Prénom opérateur]` |

---

## 6. Page Historique des ouvertures

### 6.1 Filtres

| Filtre | Notes |
|---|---|
| **Produit** | Champ de recherche avec autocomplete (nom + espèce) |
| **Du** | Date de début (AAAA-MM-JJ) |
| **Au** | Date de fin (AAAA-MM-JJ) |
| Bouton **🔍 Rechercher** | Applique les filtres et recharge |
| Bouton **✕ Reset** | Réinitialise tous les filtres |

### 6.2 Liste des ouvertures

Chaque ouverture est une carte contenant :
- **Miniature photo** (80×80 px) — clic → agrandie en plein écran (fond noir)
- **Nom du produit** + **Espèce**
- **Date et heure** de l'ouverture + **Opérateur**
- **Badge de traçabilité** (voir section 7)
- **Encart informations réception** (si traçabilité complète)

### 6.3 Pagination

La liste charge par tranches de 50. Bouton **`Voir plus…`** visible si d'autres résultats sont disponibles.

### 6.4 Modal photo plein écran

Cliquer sur une miniature ouvre la photo en plein écran sur fond noir. Cliquer n'importe où ferme la modale.

---

## 7. Règles de conformité invisibles

### 7.1 Deux niveaux de traçabilité

| Source tracée | Condition | Badge |
|---|---|---|
| **`reception`** | Le produit sélectionné est issu d'une réception récente avec `reception_ligne_id` | `✓ Tracée` (vert) |
| **`catalogue`** | Le produit est sélectionné depuis le catalogue sans lien avec une réception | `⚠ Manuelle` (orange) |

Quand la traçabilité est complète (`source = "reception"`), l'historique affiche un encart vert avec : **N° lot** · **Fournisseur** · **DLC** · **Date de réception** · **Origine**.

### 7.2 Produits proposés : uniquement les matières premières

L'API `/api/ouvertures/suggestions` ne retourne **que les produits de catégorie `matiere_premiere`**. Les produits finis (fabrications, recettes) ne sont pas proposés dans ce module.

### 7.3 Fenêtre de 21 jours pour les produits "en stock"

Un produit est affiché dans la section **"Produits en stock"** si :
- Il a une réception clôturée dans les **21 derniers jours**
- La ligne de réception est conforme et la livraison n'a pas été refusée
- La DLC n'est pas dépassée
- Aucun enregistrement `dlc_devenir` n'existe pour ce lot

Le lot FIFO disponible est pré-sélectionné (DLC la plus proche, puis date de réception la plus ancienne).

### 7.4 Bouton "↩ Même produit" : retour à l'étape Photo

Le bouton "Même produit" repart à l'**étape 2** (Photo), pas à l'étape 1 (Opérateur). L'opérateur et le produit sont conservés. Seule la photo doit être reprise pour la prochaine ouverture.

### 7.5 Compression automatique de la photo

La photo est compressée côté serveur : réorientation EXIF, redimensionnement max 1280 px, JPEG qualité 80%. Stockée dans `data/photos/ouvertures/OUV-YYYYMMDD-HHMMSS-{id}.jpg`.

### 7.6 Recherche hybride (local + API)

La recherche en étape 3 fonctionne en deux temps :
1. **Filtrage local immédiat** sur la liste déjà chargée (nom OU code_unique, insensible casse)
2. **Appel API debounced** (350 ms) vers `/api/ouvertures/suggestions?q=...` pour résultats enrichis si le terme correspond à quelque chose hors de la liste initiale

Effacer le champ de recherche restaure la liste complète initiale sans appel API.

---

## 8. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Enregistrement sans produit sélectionné | Message rouge : *"Veuillez sélectionner un produit."* |
| Erreur API lors de l'enregistrement | Message rouge : *"Erreur : [détail]"*, bouton réactivé |
| Chargement personnel échoué | Message dans la grille : *"Impossible de charger le personnel."* |
| Chargement produits échoué | Message dans la liste : *"Impossible de charger les produits."* |
| Aucun produit correspondant à la recherche | *"Aucun produit trouvé."* |
| Photo introuvable (historique) | La miniature affiche un espace vide |

---

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

# Module 17 — Hub (Accueil)

---

## 1. Objectif

Le Hub est la **page d'accueil centrale** de HACCP Monitor. Il affiche une grille de navigation vers tous les modules opérationnels, signale en temps réel les tâches HACCP à effectuer ou en retard, et indique l'état de la dernière réception. C'est le point de départ de chaque session de travail.

---

## 2. Chemin d'accès

Page d'accueil de l'application — URL directe : `/hub.html`

Tous les modules renvoient vers le Hub via leurs boutons `← Accueil`, `← Hub` ou `← Retour`.

---

## 3. Interface

### 3.1 En-tête

| Élément | Contenu |
|---|---|
| **Titre** | `Au Comptoir des Lilas` |
| **Horloge** | Date + heure courante (ex. : `lun. 14 mai — 10:30`), mise à jour chaque seconde |
| **🔔 Cloche** | Bouton avec badge numérique rouge — visible seulement si des tâches HACCP sont à signaler. Rouge/clignotant si tâches urgentes du jour. |
| **⚙ Admin** | Lien vers `/admin.html` (gestion du personnel, paramètres) |

### 3.2 Bandeau "Connexion perdue"

Un bandeau orange discret s'affiche si **toutes les requêtes API du Hub échouent simultanément** :  
`⚠ Connexion au serveur perdue — vérifiez le Raspberry Pi`

---

## 4. Grille de navigation — 8 tuiles

| Icône | Titre | Destination | Statut |
|---|---|---|---|
| ✅ | **TÂCHES HACCP** | `/taches-hub.html` | `Nettoyage & contrôles` |
| 🏭 | **PRODUCTION** | `/production-hub.html` | `Fabrication, Cuisson, Refroidissement` |
| 📦 | **RÉCEPTION** | `/reception.html` | **Dynamique** (voir section 5) |
| ✂️ | **OUVERTURE** | `/ouverture.html` | `Traçabilité ouvertures` |
| 📅 | **CALENDRIER DLC** | `/dlc.html` | `4 sources unifiées` |
| 📋 | **STOCK** | `/inventaire.html` | `FIFO toutes sources` |
| 🗂️ | **HISTORIQUE** | `/historique.html` | `Tous les enregistrements` |
| 📚 | **CATALOGUE** | `/catalogue.html` | `Produits & matières premières` |

---

## 5. Tuile RÉCEPTION — statut dynamique

La tuile Réception charge automatiquement l'état de la **dernière réception enregistrée** :

| État | Couleur tuile | Texte statut |
|---|---|---|
| Aucune réception | Gris | `● Aucune réception récente` |
| Dernière réception conforme | Vert | `● JJ mois · N produit(s) · OK` |
| Dernière réception NC | Orange | `● JJ mois · N produit(s) · NC` |
| Erreur de connexion | Rouge | `⚠ Connexion perdue` |

---

## 6. Popup "Tâches HACCP" (🔔)

### 6.1 Déclenchement

La popup s'ouvre **automatiquement** au premier chargement du Hub si :
1. Des tâches sont à signaler (liste non vide)
2. La cloche n'est pas en mode "snooze"

Les chargements suivants (toutes les 30s) ne rouvrent **pas** la popup automatiquement.

Cliquer sur la cloche 🔔 ouvre la popup manuellement à tout moment.

### 6.2 Structure de la popup

| Section | Pastille | Contenu |
|---|---|---|
| **À faire aujourd'hui** | 🔴 Rouge | Tâches non faites aujourd'hui ou en retard |
| **À venir (≤ 14 jours)** | 🟠 Orange | Échéances approchant dans les 14 prochains jours |

Chaque ligne est **cliquable** (lien direct vers le module concerné).

### 6.3 Bouton Snooze

**`🔕 Ne plus afficher pendant 2h`** : masque la popup automatique pour 2 heures. L'état de snooze est stocké en `localStorage` (clé `hub_popup_snooze_until`).

Si le snooze est actif, le bouton devient **`🔔 Réafficher l'alerte`** pour annuler le snooze immédiatement.

### 6.4 Fermeture

- Bouton `✕`
- Clic en dehors de la popup
- Touche `Échap`

---

## 7. Sources agrégées du résumé tâches

Le backend `/api/hub/taches-resume` interroge **4 sources** pour construire les listes :

### 7.1 Nettoyage (quotidien)

Vérifie si au moins une validation de nettoyage existe pour **aujourd'hui** dans `registre_nettoyage`.

| Condition | Apparaît dans | Libellé | Détail |
|---|---|---|---|
| Pas encore validé | Aujourd'hui | `🧹 Nettoyage & désinfection` | `Quotidien — à valider` |
| Validé | *(absent)* | — | — |

### 7.2 Nuisibles (hebdomadaire — semaine ISO)

Vérifie les 4 types de nuisibles (1=Rongeurs, 2=Ins. Volants, 3=Ins. Rampants, 4=Oiseaux) dans `nuisibles_controles` pour la **semaine ISO en cours**.

| Condition | Apparaît dans | Libellé | Détail |
|---|---|---|---|
| ≥ 1 type manquant | Aujourd'hui | `🪤 Contrôle nuisibles` | `Semaine N — manque : [noms des types]` |
| Tous faits | *(absent)* | — | — |

### 7.3 Étalonnage (trimestriel — 92 jours)

| Condition | Apparaît dans | État | Détail |
|---|---|---|---|
| Jamais fait | Aujourd'hui | `en_retard` | `Jamais effectué` |
| En retard (> 92j depuis dernier) | Aujourd'hui | `en_retard` | `En retard de N jour(s)` |
| Dans ≤ 14 jours | À venir | — | `Dans N jour(s) — JJ/MM/AAAA` |
| Dans > 14 jours | *(absent)* | — | — |

### 7.4 DLC (continu — 4 sources stock)

Analyse les DLC entre **-30 jours et +14 jours** (produits expirés non traités inclus). Seuls les produits sans `devenir_statut` sont pris en compte.

| Condition | Icône | Libellé | Apparaît dans | Détail |
|---|---|---|---|---|
| DLC dépassée (jours < 0) | 🚨 | `DLC dépassées` | Aujourd'hui (`en_retard`) | `N produit(s) à retirer` |
| DLC critique (0 ≤ jours ≤ seuil rouge) | 🔴 | `DLC critiques` | Aujourd'hui (`a_faire`) | `N produit(s) — DLC dans ≤ X j` |
| DLC à surveiller (seuil rouge < jours ≤ 14) | 🟠 | `DLC à surveiller` | À venir | `N produit(s) — DLC dans ≤ 14 j` |

> Le seuil rouge est celui configuré dans les paramètres DLC (défaut : 1 jour).

---

## 8. Règles de conformité invisibles

### 8.1 Rafraîchissement automatique 30 secondes

Les données des tuiles ET du résumé tâches se rechargent **toutes les 30 secondes** en arrière-plan, sans intervention de l'utilisateur.

### 8.2 Inactivité 5 minutes → rechargement

Après 5 minutes sans interaction (clic, touche, défilement, mouvement souris, toucher), le Hub s'**auto-recharge** (`location.reload()`). Cela réinitialise l'état et rafraîchit les données. Ce n'est pas une redirection vers une autre page.

### 8.3 Bandeau connexion perdue

Le bandeau orange ne s'affiche que si **les deux appels API principaux** (`/api/etiquettes/alertes-dlc` ET `/api/receptions?limit=1`) ont tous les deux échoué simultanément. Un seul échec ne déclenche pas le bandeau.

### 8.4 Popup : une seule ouverture automatique par chargement

Le flag `popupDejaOuvert` garantit que la popup HACCP ne s'ouvre automatiquement qu'**une seule fois** par chargement de page, même si le rafraîchissement 30s détecte de nouvelles tâches. L'utilisateur reste libre de naviguer sans que la popup réapparaisse à chaque cycle.

### 8.5 Snooze 2 heures

Le snooze est stocké dans `localStorage` avec la clé `hub_popup_snooze_until` contenant un timestamp Unix (millisecondes). Toute ouverture automatique de la popup vérifie `Date.now() < snooze_until` avant d'afficher. Le snooze survit aux rechargements de page pendant 2 heures.

### 8.6 Application PWA

Le Hub est configuré comme une **Progressive Web App** :
- `manifest.json` permet l'installation sur tablette Android (icône sur l'écran d'accueil, plein écran sans barres navigateur)
- `sw.js` (Service Worker) assure une disponibilité partielle hors ligne
- `theme-color: #3D2008` (brun foncé) colore la barre système Android

---

## 9. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Toutes les API échouent | Bandeau orange : *"⚠ Connexion au serveur perdue — vérifiez le Raspberry Pi"* |
| API réceptions seule échoue | Tuile RÉCEPTION : rouge, `⚠ Connexion perdue` |
| API hub/taches-resume échoue | Cloche masquée, popup non chargée |
| Aucune tâche HACCP à signaler | Cloche masquée (invisible dans l'en-tête) |

---

# Module 18 — E-Learning (Formation du Personnel)

---

## 1. Objectif

Le module E-Learning met à disposition du personnel des documents de formation en ligne (guides PDF) avec **validation traçable** : chaque lecture est enregistrée en base de données avec l'identifiant de la personne et l'horodatage. Il inclut également un tutoriel interactif de l'application HACCP Monitor.

---

## 2. Chemin d'accès

Hub Tâches HACCP → tuile **🎓 E-LEARNING**.

URL directe : `/elearning.html`

---

## 3. Architecture — 3 sous-modules

La page d'accueil E-Learning affiche 3 tuiles :

| Icône | Titre | Destination | Contenu |
|---|---|---|---|
| 🧼 | **HYGIÈNE** | `/elearning-hygiene.html` | Guide des bonnes pratiques |
| 🔪 | **DÉCOUPE** | `/elearning-decoupe.html` | Techniques & sécurité |
| 📋 | **TUTO HACCP MONITOR** | `/tutoriel-slideshow.html` | Mode d'emploi pas à pas |

---

## 4. Sous-module Hygiène (`/elearning-hygiene.html`)

2 tuiles :

| Icône | Titre | Statut | Action |
|---|---|---|---|
| 📄 | **DOCUMENT** | `Lire le guide PDF · Validation traçable` | Ouvre la visionneuse PDF avec le guide hygiène |
| 🎓 | **MODULE** | `Cours interactif + quiz · Bientôt disponible` | Affiche un message : *"Module interactif disponible prochainement."* (non encore implémenté) |

La tuile **DOCUMENT** ouvre :  
`/elearning-pdf-viewer.html?module=hygiene-pdf&titre=Hygiène&pdf=/static/docs/hygiene.pdf`

---

## 5. Sous-module Découpe (`/elearning-decoupe.html`)

4 tuiles, une par espèce :

| Icône | Titre | Module ID | Document PDF |
|---|---|---|---|
| 🐂 | **BŒUF** | `decoupe-boeuf` | `/static/docs/decoupe_boeuf.pdf` |
| 🐄 | **VEAU** | `decoupe-veau` | `/static/docs/decoupe_veau.pdf` |
| 🐑 | **AGNEAU** | `decoupe-agneau` | `/static/docs/decoupe_agneau.pdf` |
| 🐖 | **PORC** | `decoupe-porc` | `/static/docs/decoupe_porc.pdf` |

Chaque tuile ouvre la visionneuse PDF avec le document correspondant et le paramètre `retour=/elearning-decoupe.html` pour revenir à cette page après validation.

---

## 6. Visionneuse PDF et validation (`/elearning-pdf-viewer.html`)

### 6.1 Paramètres URL

La visionneuse est une page **générique** pilotée par 4 paramètres dans l'URL :

| Paramètre | Rôle | Exemple |
|---|---|---|
| `module` | Identifiant de traçabilité en base | `hygiene-pdf` |
| `pdf` | Chemin du fichier PDF | `/static/docs/hygiene.pdf` |
| `titre` | Titre affiché dans l'en-tête | `Hygiène` |
| `retour` | Page de retour après validation | `/elearning-hygiene.html` |

### 6.2 Interface

- **Iframe plein écran** affichant le PDF avec la barre de navigation native du navigateur (`#toolbar=1&view=FitH`)
- **Barre sticky en bas** contenant :
  - Mention de la dernière lecture (ex. : `Dernière lecture : Émile — 14/05/2026 à 10:30`)
  - Menu déroulant **"— Qui a lu ? —"** avec les prénoms du personnel actif
  - Bouton **`✅ J'AI LU ET COMPRIS`** — désactivé tant qu'aucun personnel n'est sélectionné

### 6.3 Mode d'emploi

1. Lire le document PDF affiché dans l'iframe.
2. Sélectionner son prénom dans le menu déroulant.
3. Cliquer **`✅ J'AI LU ET COMPRIS`**.
4. Un overlay de succès s'affiche avec la confirmation.
5. Cliquer **`TERMINER`** → retour à la page d'origine.

### 6.4 Overlay de succès

Après validation :
- Titre : **"Lecture enregistrée !"**
- Message : *"[Prénom], votre lecture a été enregistrée à HH:MM. La validation est désormais traçable."*
- Bouton **`TERMINER`** → redirige vers la page `retour` définie dans l'URL

---

## 7. Tutoriel HACCP Monitor (`/tutoriel-slideshow.html`)

Présentation slideshow interactive du fonctionnement de l'application. Ce fichier est **autonome** : il embarque son propre CSS de secours et charge tous les CSS modules de l'application pour reproduire fidèlement les interfaces réelles. Il peut être parcouru directement sans serveur (ouverture en `file://`).

> Ce tutoriel ne génère pas d'enregistrement de complétion en base de données.

---

## 8. Règles de conformité invisibles

### 8.1 Traçabilité sans unicité

Chaque clic sur **"J'AI LU ET COMPRIS"** crée **un nouvel enregistrement** en base de données. Il n'y a pas de contrainte d'unicité : un même employé peut valider plusieurs fois le même module. La barre de la visionneuse affiche uniquement la **dernière** validation du module.

### 8.2 Identifiant de module

Le paramètre `module` dans l'URL est l'identifiant stocké en base (`elearning_completions.module`). Les identifiants actuels sont :

| Identifiant | Document |
|---|---|
| `hygiene-pdf` | Guide hygiène |
| `decoupe-boeuf` | Guide découpe bœuf |
| `decoupe-veau` | Guide découpe veau |
| `decoupe-agneau` | Guide découpe agneau |
| `decoupe-porc` | Guide découpe porc |

Ces identifiants permettent de filtrer les validations par module dans l'API (`GET /api/elearning/completions?module=hygiene-pdf`).

### 8.3 Page de retour par défaut

Si le paramètre `retour` est absent de l'URL, la visionneuse calcule automatiquement la page de retour depuis l'identifiant de module : `/elearning-[préfixe].html`. Exemple : module `decoupe-boeuf` → retour vers `/elearning-decoupe.html`.

### 8.4 Dernière complétion affichée dès l'ouverture

Au chargement de la visionneuse, un appel `GET /api/elearning/completions?module=...&limit=1` récupère la dernière validation enregistrée pour ce module et l'affiche dans la barre inférieure. Si aucune validation n'existe : `Aucune lecture enregistrée pour ce module.`

---

## 9. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Bouton "J'AI LU ET COMPRIS" sans personnel sélectionné | Bouton désactivé, aucune action |
| `personnel_id` inexistant (backend) | HTTP 404 : *"personnel_id introuvable"* |
| Module vide (backend) | HTTP 400 : *"module requis"* |
| Erreur API validation | Toast rouge : *"Erreur : [détail]"*, bouton réactivé |
| PDF introuvable | L'iframe affiche un message d'erreur navigateur (page blanche ou 404) |
| Chargement personnel échoué | Menu déroulant vide, bouton reste désactivé |
| Clic sur tuile "MODULE" (interactif) | `alert("Module interactif disponible prochainement.")` |

---

*Ce document constitue le dernier chapitre du Manuel d'Utilisation de HACCP Monitor v2.0.0.*

*Pour retrouver tous les chapitres, consultez le dossier `docs/manuel_utilisateur/`.*















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

[Passer au module suivant : Réception de marchandises](02_reception.md)

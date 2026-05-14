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

[Passer au module suivant : Calendrier DLC](13_dlc.md)

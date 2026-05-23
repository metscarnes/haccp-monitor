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
| **Produits en stock** | Produits ayant une réception dans les 2 derniers mois — triés par date de réception décroissante |
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

### 7.3 Fenêtre de 2 mois pour les produits "en stock"

Un produit est affiché dans la section **"Produits en stock"** si :
- Il a une réception clôturée dans les **2 derniers mois**
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

[Passer au module suivant : Enceintes Frigorifiques & Relevés](15_enceintes.md)

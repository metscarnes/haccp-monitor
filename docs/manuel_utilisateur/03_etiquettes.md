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

[Passer au module suivant : Fiches Incident PCR01](04_incidents.md)

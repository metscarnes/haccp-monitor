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

[Passer au module suivant : Ouvertures de conditionnement](14_ouvertures.md)

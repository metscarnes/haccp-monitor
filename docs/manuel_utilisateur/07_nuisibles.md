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

[Passer au module suivant : Étalonnage Thermomètres (EET01)](08_etalonnage.md)

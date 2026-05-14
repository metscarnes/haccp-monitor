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

[Passer au module suivant : Lutte contre les Nuisibles (IPM)](07_nuisibles.md)

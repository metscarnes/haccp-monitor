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

[Passer au module suivant : E-Learning](18_elearning.md)

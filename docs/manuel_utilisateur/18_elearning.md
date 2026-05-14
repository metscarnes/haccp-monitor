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

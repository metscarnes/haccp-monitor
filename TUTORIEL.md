<link rel="stylesheet" href="static/css/reset.css">
<link rel="stylesheet" href="static/css/tokens.css">
<link rel="stylesheet" href="static/css/base.css">
<link rel="stylesheet" href="static/css/components.css">
<link rel="stylesheet" href="static/css/layouts.css">
<link rel="stylesheet" href="static/css/pages/hub.css">
<link rel="stylesheet" href="static/css/pages/catalogue.css">
<link rel="stylesheet" href="static/css/pages/reception.css">
<link rel="stylesheet" href="static/css/pages/etiquettes.css">
<link rel="stylesheet" href="static/css/pages/nettoyage.css">
<link rel="stylesheet" href="static/css/pages/nuisibles.css">
<link rel="stylesheet" href="static/css/pages/etalonnage.css">
<link rel="stylesheet" href="static/css/pages/cuisson.css">
<link rel="stylesheet" href="static/css/pages/ouverture.css">
<link rel="stylesheet" href="static/css/pages/taches.css">
<link rel="stylesheet" href="static/css/pages/inventaire.css">
<link rel="stylesheet" href="static/css/pages/dlc.css">
<link rel="stylesheet" href="static/css/pages/elearning.css">

# Manuel Utilisateur — Au Comptoir des Lilas
## Application HACCP Monitor

---

## Sommaire

- [Avant de commencer — les bases](#avant-de-commencer--les-bases)
- [L'écran d'accueil (le Hub)](#lécran-daccueil-le-hub)
- [Module 1 — Catalogue Produits](#module-1--catalogue-produits)

---

## Avant de commencer — les bases

### Les règles d'or de la tablette

> Ces règles suffisent pour tout. Lisez-les une fois, puis oubliez-les — elles deviendront un réflexe.

- **Pas de double-clic** : on tape **une seule fois**, doucement, comme on appuie sur une sonnette. L'application répond toujours.
- **Pas peur de se tromper** : rien n'est enregistré définitivement tant que vous n'avez pas tapé **Enregistrer** ou **Valider**.
- **Sélectionnez toujours votre prénom** quand l'application vous le demande — c'est obligatoire pour la traçabilité.
- Si l'écran est **noir ou en veille**, posez le doigt dessus une seconde : il se réveille seul.
- Si l'application semble bloquée, **attendez 3 secondes** avant de retaper : parfois elle réfléchit.

### Le vocabulaire de ce guide

| Mot | Ce que ça veut dire |
|---|---|
| **Tuile** | Un grand carré coloré avec une icône. On tape dessus pour aller dans un module. |
| **Bouton** | Une zone rectangulaire sur laquelle on tape pour faire une action (ex : « Valider »). |
| **Champ** | Une case blanche où on écrit quelque chose (un nombre, un texte). |
| **Menu déroulant** | Une case avec une flèche — on tape dessus et une liste de choix apparaît. |
| **Modale** | Une fenêtre qui s'ouvre par-dessus l'écran pour remplir un formulaire. On la ferme avec ✕ ou en tapant en dehors. |
| **DLC** | Date Limite de Consommation — après cette date, on ne vend plus. |
| **Lot** | Un numéro unique donné à chaque production pour retrouver un produit en cas de problème. |
| **FIFO** | « Premier entré, premier sorti » — on utilise d'abord ce qui est arrivé en premier. |

---

## L'écran d'accueil (le Hub)

Quand vous lancez l'application, vous arrivez sur le **Hub** — c'est la page d'accueil avec toutes les grandes tuiles colorées.

<div class="hub-body" style="position:relative;background:var(--color-bg);padding:1rem;border-radius:var(--radius);border:2px solid var(--color-secondary);max-width:700px;">

<header class="hub-header" style="border-radius:var(--radius-sm);margin-bottom:1rem;">
  <div class="hub-titre">Au Comptoir des Lilas</div>
  <div style="color:#fff;opacity:.7;font-size:var(--text-sm);">08:32 — Mercredi 14 mai</div>
  <a style="background:rgba(255,255,255,.15);color:#fff;padding:.4rem .8rem;border-radius:var(--radius-sm);text-decoration:none;font-size:var(--text-sm);">⚙ Admin</a>
</header>

<main class="hub-grille" role="main" style="display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;">
  <a class="hub-tuile" style="text-decoration:none;">
    <div class="hub-tuile-icone">✅</div>
    <div class="hub-tuile-titre">TÂCHES HACCP</div>
    <div class="hub-tuile-statut">Nettoyage &amp; contrôles</div>
  </a>
  <a class="hub-tuile" style="text-decoration:none;">
    <div class="hub-tuile-icone">🏭</div>
    <div class="hub-tuile-titre">PRODUCTION</div>
    <div class="hub-tuile-statut">Fabrication, Cuisson, Refroidissement</div>
  </a>
  <a class="hub-tuile" style="text-decoration:none;">
    <div class="hub-tuile-icone">📦</div>
    <div class="hub-tuile-titre">RÉCEPTION</div>
    <div class="hub-tuile-statut">Contrôles à la livraison</div>
  </a>
  <a class="hub-tuile" style="text-decoration:none;">
    <div class="hub-tuile-icone">✂️</div>
    <div class="hub-tuile-titre">OUVERTURE</div>
    <div class="hub-tuile-statut">Traçabilité ouvertures</div>
  </a>
  <a class="hub-tuile" style="text-decoration:none;">
    <div class="hub-tuile-icone">📅</div>
    <div class="hub-tuile-titre">CALENDRIER DLC</div>
    <div class="hub-tuile-statut">4 sources unifiées</div>
  </a>
  <a class="hub-tuile" style="text-decoration:none;">
    <div class="hub-tuile-icone">📋</div>
    <div class="hub-tuile-titre">STOCK</div>
    <div class="hub-tuile-statut">FIFO toutes sources</div>
  </a>
  <a class="hub-tuile" style="text-decoration:none;">
    <div class="hub-tuile-icone">🗂️</div>
    <div class="hub-tuile-titre">HISTORIQUE</div>
    <div class="hub-tuile-statut">Tous les enregistrements</div>
  </a>
  <a class="hub-tuile" style="text-decoration:none;">
    <div class="hub-tuile-icone">📚</div>
    <div class="hub-tuile-titre">CATALOGUE</div>
    <div class="hub-tuile-statut">Produits &amp; matières premières</div>
  </a>
</main>

</div>

### Comment naviguer

- **Tapez une tuile** pour entrer dans un module.
- En haut à gauche de chaque module, le lien **← Accueil** vous ramène ici.
- La **🔔 cloche** (si elle apparaît) signale des tâches HACCP à faire aujourd'hui.
- Si une tuile affiche un message en **rouge ou orange**, c'est une alerte — lisez-la avant de continuer.

---

## Module 1 — Catalogue Produits

### À quoi ça sert ?

Le Catalogue, c'est la **liste officielle de tous vos produits** : viandes brutes reçues des fournisseurs, et préparations maison (boulettes, rôtis farcis, plats traiteur, charcuteries…). C'est ici qu'on définit leur nom, leur code d'identification, leur durée de vie, leur température de conservation.

> **Pourquoi c'est important ?** Tous les autres modules (réception, étiquettes, cuisson, fabrication…) piochent dans ce catalogue. Si un produit n'est pas dans le catalogue, il ne peut pas être utilisé ailleurs.

Pour y accéder : tapez la tuile **📚 CATALOGUE** sur l'écran d'accueil.

---

### Ce que vous voyez en arrivant

<div class="cat-body" style="background:var(--color-bg);border-radius:var(--radius);border:2px solid var(--color-secondary);overflow:hidden;max-width:100%;">

<header class="cat-bar">
  <span class="cat-retour">← Accueil</span>
  <div class="cat-bar-titre">📚 Catalogue produits</div>
  <div class="cat-bar-actions">
    <button class="cat-btn cat-btn--primary" type="button">+ Nouveau</button>
    <button class="cat-btn" type="button">📥 Importer Excel</button>
    <span class="cat-btn">📤 Exporter Excel</span>
  </div>
</header>

<section class="cat-stats">
  <div class="cat-stat">
    <div class="cat-stat-num">47</div>
    <div class="cat-stat-lbl">Total</div>
  </div>
  <div class="cat-stat cat-stat--brut">
    <div class="cat-stat-num">28</div>
    <div class="cat-stat-lbl">Bruts</div>
  </div>
  <div class="cat-stat cat-stat--fini">
    <div class="cat-stat-num">16</div>
    <div class="cat-stat-lbl">Finis</div>
  </div>
  <div class="cat-stat cat-stat--archive">
    <div class="cat-stat-num">3</div>
    <div class="cat-stat-lbl">Archivés</div>
  </div>
  <div class="cat-stat cat-stat--alerte">
    <div class="cat-stat-num">2</div>
    <div class="cat-stat-lbl">Incomplets</div>
  </div>
</section>

</div>

**Ce que veulent dire ces chiffres :**

| Chiffre | Ce que ça veut dire |
|---|---|
| **Total** | Tous les produits dans le système (actifs + archivés) |
| **Bruts** | Matières premières reçues des fournisseurs (viandes, volailles…) |
| **Finis** | Préparations maison prêtes à la vente |
| **Archivés** | Produits qu'on ne vend plus, mais conservés dans l'historique |
| **Incomplets** ⚠️ | Produits auxquels il manque un code, une catégorie ou une durée de vie — **à corriger en priorité** |

> Si **Incomplets** est en rouge et affiche un chiffre supérieur à 0, allez corriger ces produits dès que possible — ils bloquent la traçabilité.

---

### Les filtres pour trouver un produit

<div class="cat-body" style="background:var(--color-bg);border-radius:var(--radius);border:2px solid var(--color-secondary);overflow:hidden;max-width:100%;">
<section class="cat-filtres">
  <label class="cat-filtre cat-filtre--search">
    <span>Recherche</span>
    <input type="search" placeholder="nom, code, espèce…" style="pointer-events:none;">
  </label>
  <label class="cat-filtre">
    <span>Type</span>
    <select style="pointer-events:none;"><option>Tous</option><option>Brut</option><option>Fini</option></select>
  </label>
  <label class="cat-filtre">
    <span>Catégorie</span>
    <select style="pointer-events:none;"><option>Toutes</option></select>
  </label>
  <label class="cat-filtre">
    <span>Conditionnement</span>
    <select style="pointer-events:none;"><option>Tous</option></select>
  </label>
  <label class="cat-filtre cat-filtre--check">
    <input type="checkbox" style="pointer-events:none;">
    <span>Voir archivés</span>
  </label>
  <label class="cat-filtre cat-filtre--check">
    <input type="checkbox" style="pointer-events:none;">
    <span>Incomplets uniquement</span>
  </label>
  <div class="cat-resultat">44 / 47</div>
</section>
</div>

- **Recherche** : tapez le début du nom, le code (ex : `VB3`) ou l'espèce. La liste se met à jour automatiquement au fur et à mesure que vous tapez.
- **Type** : filtrez par « Brut » (matière première) ou « Fini » (préparation maison).
- **Catégorie** : filtrez par catégorie réglementaire (viande hachée, charcuterie, traiteur…).
- **Conditionnement** : filtrez par emballage (sous-vide, barquette, vrac…).
- **Voir archivés** : cochez cette case pour afficher aussi les anciens produits qu'on ne vend plus.
- **Incomplets uniquement** : cochez pour ne voir que les produits à corriger en priorité.

Le chiffre en bas à droite (`44 / 47`) indique combien de produits sont affichés par rapport au total.

---

### Le tableau des produits

<div class="cat-body" style="background:var(--color-bg);border-radius:var(--radius);border:2px solid var(--color-secondary);overflow:hidden;max-width:100%;">
<main class="cat-table-wrap" style="padding:.5rem;">
<table class="cat-table">
  <thead>
    <tr>
      <th>Nom</th>
      <th>Code</th>
      <th>Catégorie</th>
      <th>Type</th>
      <th>Cond.</th>
      <th class="cat-col-num">DLC (j)</th>
      <th>Temp.</th>
      <th>Statut</th>
      <th class="cat-col-actions">Actions</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="cat-cell-nom">Entrecôte charolaise</td>
      <td><code>VB3</code></td>
      <td>Pièces de viande</td>
      <td>Brut</td>
      <td>SOUS_VIDE</td>
      <td class="cat-col-num">10</td>
      <td>0°C à +4°C</td>
      <td><span class="cat-badge cat-badge--ok">Actif</span></td>
      <td class="cat-col-actions"><button class="cat-btn cat-btn--small" type="button">✎ Éditer</button></td>
    </tr>
    <tr class="cat-row--incomplet">
      <td class="cat-cell-nom">Merguez maison</td>
      <td><code>PC7</code></td>
      <td></td>
      <td>Fini</td>
      <td>VRAC</td>
      <td class="cat-col-num">0</td>
      <td>0°C à +4°C</td>
      <td><span class="cat-badge cat-badge--incomplet">Incomplet</span></td>
      <td class="cat-col-actions"><button class="cat-btn cat-btn--small" type="button">✎ Éditer</button></td>
    </tr>
    <tr class="cat-row--archive">
      <td class="cat-cell-nom">Andouillette (ancienne)</td>
      <td><code>PC2</code></td>
      <td>Charcuterie</td>
      <td>Fini</td>
      <td>VRAC</td>
      <td class="cat-col-num">5</td>
      <td>0°C à +4°C</td>
      <td><span class="cat-badge cat-badge--archive">Archivé</span></td>
      <td class="cat-col-actions"><button class="cat-btn cat-btn--small" type="button">✎ Éditer</button></td>
    </tr>
  </tbody>
</table>
</main>
</div>

**Signification des badges de statut :**

<div style="display:flex;gap:.75rem;flex-wrap:wrap;padding:.75rem;background:var(--color-card);border-radius:var(--radius);border:1px solid var(--color-secondary);margin:.5rem 0;">
  <span class="cat-badge cat-badge--ok">Actif</span> — Produit en service, disponible dans tous les modules.
  &nbsp;|&nbsp;
  <span class="cat-badge cat-badge--incomplet">Incomplet</span> — Il manque une information obligatoire : à corriger.
  &nbsp;|&nbsp;
  <span class="cat-badge cat-badge--archive">Archivé</span> — Produit retiré de la vente, visible dans l'historique.
</div>

---

### Créer un nouveau produit

**Quand l'utiliser ?** Chaque fois qu'on référence un nouveau produit chez un fournisseur, ou qu'on crée une nouvelle préparation maison.

**Étapes :**

1. Tapez le bouton **`+ Nouveau`** en haut à droite.
2. Une fenêtre s'ouvre avec le formulaire. Le curseur se place directement dans le champ **Nom**.

<div class="cat-body" style="border-radius:var(--radius);border:2px solid var(--color-secondary);overflow:hidden;max-width:600px;">
<div class="cat-modal-card">
  <header class="cat-modal-header">
    <h2 class="cat-modal-titre" style="margin:0;">Nouveau produit</h2>
    <button class="cat-modal-fermer" type="button" style="cursor:default;">✕</button>
  </header>
  <div class="cat-form" style="pointer-events:none;">
    <label class="cat-champ cat-champ--full">
      <span>Nom <span class="cat-req">*</span></span>
      <input type="text" placeholder="Ex : Rôti de bœuf farci" value="">
    </label>
    <label class="cat-champ">
      <span>Espèce</span>
      <select><option>Bovin</option><option>Porc</option><option>Volaille — canard</option></select>
    </label>
    <label class="cat-champ">
      <span>Code unique <span class="cat-hint">— généré automatiquement</span></span>
      <input type="text" readonly value="VB12" placeholder="sélectionnez une espèce…">
    </label>
    <label class="cat-champ">
      <span>Catégorie <span class="cat-req">*</span></span>
      <select><option>Pièces de viande</option><option>Viande hachée</option><option>Traiteur</option></select>
    </label>
    <label class="cat-champ">
      <span>Type produit</span>
      <select><option>Fini</option><option>Brut</option></select>
    </label>
    <label class="cat-champ">
      <span>DLC (jours)</span>
      <input type="number" value="3">
    </label>
    <label class="cat-champ">
      <span>Température conservation</span>
      <select><option>0°C à +4°C</option><option>-18°C</option></select>
    </label>
    <label class="cat-champ">
      <span>Conditionnement</span>
      <select><option>SOUS_VIDE</option><option>BARQUETTE</option><option>VRAC</option></select>
    </label>
    <div class="cat-modal-footer">
      <div></div>
      <div class="cat-modal-footer-droite">
        <button class="cat-btn" type="button">Annuler</button>
        <button class="cat-btn cat-btn--primary" type="button">Enregistrer</button>
      </div>
    </div>
  </div>
</div>
</div>

**Remplissez les champs :**

| Champ | Obligatoire ? | Comment remplir |
|---|---|---|
| **Nom** | ✅ Oui | Nom commercial du produit (celui qui apparaîtra sur les étiquettes et dans les listes) |
| **Espèce** | Recommandé | Choisissez dans la liste : Bovin, Porc, Agneau, Volaille… |
| **Code unique** | Automatique | Se remplit tout seul dès que vous choisissez une espèce. Ne modifiez pas. |
| **Catégorie** | ✅ Oui | Matière première / Viande hachée / Pièces de viande / Préparation crue / Charcuterie / Traiteur |
| **Type produit** | Non | **Brut** = acheté chez le fournisseur ; **Fini** = fabriqué sur place |
| **DLC (jours)** | Recommandé | Nombre de jours de conservation après réception ou fabrication. **Ne pas laisser à 0.** |
| **Température** | Non | Choisissez selon le type : `0°C à +4°C` pour la viande fraîche, `-18°C` pour le congelé |
| **Conditionnement** | Non | Comment le produit est emballé : sous-vide, barquette, vrac… |

3. Tapez **`Enregistrer`** pour valider.
4. La fenêtre se ferme et le produit apparaît dans le tableau.

> **Bon à savoir sur le code unique :** Il est généré automatiquement selon l'espèce choisie. Exemples : `VB12` pour du Bovin (VB = Viande Bovine), `PC5` pour du Porc, `AGN3` pour de l'Agneau. Ce code sert à identifier le produit dans toute l'application.

---

### Modifier un produit existant

1. Repérez le produit dans le tableau.
2. Tapez le bouton **`✎ Éditer`** dans la colonne Actions à droite.
3. La fenêtre s'ouvre avec les informations déjà remplies.
4. Modifiez ce qui doit l'être.
5. Tapez **`Enregistrer`**.

> **Attention :** En mode modification, le code unique n'est pas recalculé automatiquement si vous changez d'espèce. Si vous avez besoin de changer le code, modifiez-le manuellement — mais vérifiez qu'il n'existe pas déjà.

---

### Archiver un produit (retirer de la vente)

Archiver un produit, c'est le **retirer des listes de travail** sans effacer son historique. Toutes les réceptions, cuissons et étiquettes passées restent consultables.

1. Ouvrez la fiche du produit avec **`✎ Éditer`**.
2. Tapez le bouton rouge **`🗑 Archiver`** en bas du formulaire.
3. Un message de confirmation apparaît : tapez **Confirmer**.
4. Le produit passe en statut <span class="cat-badge cat-badge--archive">Archivé</span> et disparaît des listes de travail.

> Pour retrouver un produit archivé, cochez **"Voir archivés"** dans les filtres.

---

### Exporter et importer le catalogue en fichier Excel

#### Exporter (sauvegarder ou partager la liste)

Tapez le bouton **`📤 Exporter Excel`** dans la barre du haut. Un fichier Excel se télécharge immédiatement sur la tablette, nommé `catalogue_produits_2026-05-14.xlsx`. Il contient tous les produits (actifs et archivés).

#### Importer depuis Excel (ajouter des produits en masse)

Utile pour la mise en place initiale ou pour ajouter beaucoup de produits d'un coup.

1. Tapez **`📥 Importer Excel`**.
2. La fenêtre d'import s'ouvre.
3. Si vous n'avez pas encore de fichier, tapez **`📥 Télécharger le modèle Excel`** — vous obtenez un fichier vierge avec les bonnes colonnes.
4. Remplissez le fichier Excel : **la colonne `nom` est obligatoire**.
5. Sélectionnez votre fichier `.xlsx` sur la tablette.
6. Choisissez le mode d'import :
   - **Fusionner** *(recommandé)* : les produits existants sont mis à jour, les nouveaux sont créés, les autres ne sont pas touchés.
   - **Remplacer** : tous les produits existants sont d'abord archivés, puis ceux du fichier sont créés. À utiliser avec précaution.
7. Tapez **`Lancer l'import`**.
8. Un résumé s'affiche : nombre de produits créés, mis à jour, ignorés, et la liste des erreurs éventuelles.

---

### Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Ce que ça veut dire | Que faire |
|---|---|---|
| *"Le nom est obligatoire"* | Vous avez oublié de remplir le champ Nom | Remplissez le nom et réessayez |
| *"La catégorie est obligatoire"* | Aucune catégorie sélectionnée | Choisissez une catégorie dans la liste |
| *"Code unique 'VB3' déjà utilisé"* | Ce code existe déjà pour un autre produit | Changez le numéro du code (ex : `VB13`) |
| *"Choisissez un fichier .xlsx"* | Vous avez lancé l'import sans sélectionner de fichier | Sélectionnez d'abord votre fichier Excel |
| Ligne en **jaune pâle** dans le tableau | Produit incomplet (DLC à 0, catégorie manquante…) | Tapez ✎ Éditer et complétez les informations |
| *"Aucun produit trouvé"* | Le filtre actif n'a rien trouvé | Effacez la recherche ou changez les filtres |

---

---

## Module 2 — Réception de Marchandises

### À quoi ça sert ?

À chaque livraison de matières premières, la loi vous oblige à contrôler et enregistrer : qui a réceptionné, l'état du camion, la température, les produits reçus avec leurs numéros de lot et leurs dates limites, et l'aspect visuel de chaque produit.

Ce module guide l'opérateur **étape par étape** comme un formulaire guidé. Il y a **5 étapes** à faire dans l'ordre. On ne peut pas en sauter une.

Pour y accéder : tapez la tuile **📦 RÉCEPTION** sur l'écran d'accueil.

---

### La barre de progression en haut d'écran

<div style="background:var(--color-card);border-radius:var(--radius);border:2px solid var(--color-secondary);padding:1rem;max-width:500px;">

<header class="rec-header" style="border-radius:var(--radius-sm);margin-bottom:.75rem;">
  <button class="rec-btn-retour" type="button" style="cursor:default;">← Retour</button>
  <div class="rec-header-titre">RÉCEPTION MARCHANDISES</div>
  <div class="rec-horloge">08:32</div>
</header>

<div class="rec-progress" style="border-radius:var(--radius-sm);">
  <div class="rec-dot complet"></div>
  <div class="rec-dot complet"></div>
  <div class="rec-dot actif"></div>
  <div class="rec-dot"></div>
  <div class="rec-dot"></div>
</div>

<div class="rec-bandeau" style="border-radius:var(--radius-sm);margin-top:.5rem;">👤 Marie</div>

</div>

Chaque **rond** représente une étape :
- **Rond marron foncé** (plus grand) = étape en cours
- **Rond vert** = étape validée
- **Rond gris** = étape pas encore faite

Une fois votre prénom sélectionné, un **bandeau brun** affiche votre nom en permanence en haut de toutes les étapes.

---

### Étape 1 — Qui réceptionne ?

Le premier écran affiche les prénoms de tous les membres de l'équipe.

<div style="background:var(--color-bg);border-radius:var(--radius);border:2px solid var(--color-secondary);padding:2rem;max-width:500px;text-align:center;">
  <div class="rec-personnel-titre">Qui réceptionne ?</div>
  <div class="rec-personnel-grille" style="margin-top:1.5rem;">
    <button class="rec-btn-prenom" type="button" style="cursor:default;">Marie</button>
    <button class="rec-btn-prenom" type="button" style="cursor:default;">Jean</button>
    <button class="rec-btn-prenom" type="button" style="cursor:default;">Lucie</button>
    <button class="rec-btn-prenom" type="button" style="cursor:default;">Paulo</button>
  </div>
</div>

- **Tapez votre prénom.** C'est tout ce qu'il y a à faire ici.
- La date et l'heure se remplissent automatiquement à l'étape suivante.

> Si aucun prénom n'apparaît, contactez le responsable : les prénoms se configurent dans l'espace **⚙ Admin**.

---

### Étape 2 — Contrôle du camion

C'est ici que vous vérifiez l'état du camion de livraison avant de toucher aux marchandises.

<div style="background:var(--color-bg);border-radius:var(--radius);border:2px solid var(--color-secondary);padding:1.5rem;max-width:500px;display:flex;flex-direction:column;gap:1.25rem;">

  <div class="rec-section-titre">Contrôle du camion</div>

  <div class="rec-form-group">
    <label class="rec-champ-label">Date de réception *</label>
    <input class="rec-input" type="text" value="2026-05-14" style="pointer-events:none;" readonly>
  </div>

  <div class="rec-form-group">
    <label class="rec-champ-label">Heure de réception</label>
    <input class="rec-input" type="text" value="08:32" style="pointer-events:none;" readonly>
  </div>

  <div class="rec-form-group">
    <label class="rec-champ-label">Température du camion (°C) *</label>
    <input class="rec-input" type="text" placeholder="ex : 1.5" style="pointer-events:none;">
  </div>

  <div class="rec-form-group">
    <div class="rec-champ-label">Propreté du camion *</div>
    <div class="rec-toggle-pair">
      <button class="rec-toggle-btn ok-sel" type="button" style="cursor:default;">✓ Satisfaisante</button>
      <button class="rec-toggle-btn" type="button" style="cursor:default;">✗ Non satisfaisante</button>
    </div>
  </div>

  <button class="rec-btn-suivant" type="button" style="cursor:default;">Suivant →</button>

</div>

**Ce que vous devez faire :**

| Champ | Comment remplir |
|---|---|
| **Date** | Remplie automatiquement avec aujourd'hui. Ne modifiez que si la livraison a eu lieu à une autre date. **La date ne peut pas être dans le passé.** |
| **Heure** | Remplie automatiquement. Modifiez si besoin. |
| **Température du camion** | Lisez le thermomètre du camion et tapez la valeur (ex : `1.5`). Utilisez le point pour les décimales. Plage autorisée : -10 à 30°C. |
| **Propreté du camion** | Tapez **✓ Satisfaisante** (vert) ou **✗ Non satisfaisante** (rouge). |

#### Si le camion est sale ou non conforme

Quand vous tapez **✗ Non satisfaisante**, des cases à cocher apparaissent pour décrire le problème :

- ☐ Propreté / Insalubrité
- ☐ Tenue du livreur
- ☐ Marchandise sale ou abîmée
- ☐ Palette cassée / instable

Et une zone de photo s'affiche :
- Si vous **cochez au moins une case** → la photo du problème est facultative.
- Si vous **ne cochez rien** → la photo est **obligatoire**.

Quand vous tapez **Suivant →** avec un camion non satisfaisant, une fenêtre de confirmation apparaît :

<div style="background:var(--color-card);border-radius:var(--radius);border:2px solid var(--color-secondary);padding:1.25rem;max-width:400px;">
  <div style="font-weight:700;margin-bottom:.75rem;color:var(--color-text);">Accepter la livraison ?</div>
  <div style="font-size:var(--text-sm);color:#4b5563;margin-bottom:1rem;">Le camion a été jugé non satisfaisant. Que souhaitez-vous faire ?</div>
  <div style="display:flex;gap:.75rem;">
    <button class="rec-toggle-btn ok-sel" type="button" style="cursor:default;flex:1;">✓ Oui — Accepter</button>
    <button class="rec-toggle-btn nc-sel" type="button" style="cursor:default;flex:1;">✗ Non — Refuser</button>
  </div>
</div>

- **✓ Oui — Accepter** : vous continuez la réception normalement. La non-conformité camion est enregistrée dans la fiche.
- **✗ Non — Refuser** : vous déclarez le refus total de la livraison (voir ci-dessous).

#### Cas exceptionnel — Refus total de la livraison

Si vous refusez la livraison, une fenêtre s'ouvre. Pour chaque bon de livraison refusé, vous devez :
1. Prendre une **photo du bon de livraison** (obligatoire).
2. Indiquer le **nom du fournisseur** (obligatoire).

Si vous avez plusieurs fournisseurs à refuser, tapez **`+ Ajouter un autre bon de livraison`** pour en ajouter un.

Tapez ensuite **`Aller à PCR01 →`** pour remplir le formulaire de non-conformité réglementaire (PCR01).

> **Règle importante :** La température du camion saisie ici ne crée pas directement de problème. C'est à l'étape suivante, quand vous enregistrez chaque produit, que le système calcule automatiquement si la température était trop élevée pour ce produit.

---

### Étape 3 — Bon de livraison & Fournisseur

Ici, vous photographiez le bon de livraison papier et indiquez le nom du fournisseur.

**Si vous avez un seul fournisseur** (cas habituel) :
1. Tapez la zone avec l'icône **📋** pour déclencher l'appareil photo de la tablette.
2. Photographiez le bon de livraison.
3. Tapez dans le champ **Fournisseur**, commencez à écrire le nom — une liste de suggestions apparaît.
4. Tapez le bon nom dans la liste. Un badge vert confirme la sélection.
5. Tapez **`Créer la fiche →`**.

**Si vous avez plusieurs fournisseurs** : activez le toggle **"Oui — plusieurs"** et ajoutez un bloc photo + fournisseur pour chacun.

> Dès que vous tapez **Créer la fiche**, la réception est enregistrée. Si vous revenez en arrière et retapez ce bouton, cela ne crée pas de doublon.

---

### Étape 4 — Saisie des produits (répétez pour chaque article)

C'est l'étape principale. Vous ajoutez **un produit à la fois**. Le compteur en haut de l'écran indique combien vous en avez déjà saisi.

#### Le formulaire d'un produit

<div style="background:var(--color-bg);border-radius:var(--radius);border:2px solid var(--color-secondary);padding:1.5rem;max-width:500px;display:flex;flex-direction:column;gap:1.1rem;">

  <div class="rec-form-group">
    <label class="rec-champ-label">Produit *</label>
    <input class="rec-input" type="text" placeholder="Commencez à taper : entrecôte, poulet…" style="pointer-events:none;">
  </div>

  <div class="rec-form-group">
    <label class="rec-champ-label">N° de lot fournisseur *</label>
    <input class="rec-input" type="text" placeholder="Ex : LOT-2026-045" style="pointer-events:none;">
  </div>

  <div class="rec-form-group">
    <div class="rec-champ-label">DLC / DLUO *</div>
    <div class="rec-toggle-pair" style="margin-bottom:.5rem;">
      <button class="rec-toggle-btn ok-sel" type="button" style="cursor:default;min-height:40px;">DLC</button>
      <button class="rec-toggle-btn" type="button" style="cursor:default;min-height:40px;">DLUO</button>
    </div>
    <input class="rec-input" type="text" placeholder="jj/mm/aaaa" style="pointer-events:none;">
  </div>

  <div style="background:var(--color-card);border-radius:var(--radius-sm);padding:1rem;border:1px solid var(--color-secondary);">
    <div class="rec-champ-label" style="margin-bottom:.75rem;">Contrôle visuel</div>
    <div style="display:grid;gap:.6rem;">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:.5rem;">
        <span style="font-size:var(--text-sm);color:var(--color-text);font-weight:600;">Couleur</span>
        <div class="rec-toggle-pair" style="gap:.35rem;">
          <button class="rec-toggle-btn ok-sel" type="button" style="cursor:default;min-height:36px;padding:.4rem .75rem;font-size:var(--text-sm);">✓ Conforme</button>
          <button class="rec-toggle-btn" type="button" style="cursor:default;min-height:36px;padding:.4rem .75rem;font-size:var(--text-sm);">✗ NC</button>
        </div>
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;gap:.5rem;">
        <span style="font-size:var(--text-sm);color:var(--color-text);font-weight:600;">Consistance</span>
        <div class="rec-toggle-pair" style="gap:.35rem;">
          <button class="rec-toggle-btn ok-sel" type="button" style="cursor:default;min-height:36px;padding:.4rem .75rem;font-size:var(--text-sm);">✓ Conforme</button>
          <button class="rec-toggle-btn" type="button" style="cursor:default;min-height:36px;padding:.4rem .75rem;font-size:var(--text-sm);">✗ NC</button>
        </div>
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;gap:.5rem;">
        <span style="font-size:var(--text-sm);color:var(--color-text);font-weight:600;">Exsudat</span>
        <div class="rec-toggle-pair" style="gap:.35rem;">
          <button class="rec-toggle-btn ok-sel" type="button" style="cursor:default;min-height:36px;padding:.4rem .75rem;font-size:var(--text-sm);">✓ Conforme</button>
          <button class="rec-toggle-btn" type="button" style="cursor:default;min-height:36px;padding:.4rem .75rem;font-size:var(--text-sm);">✗ NC</button>
        </div>
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;gap:.5rem;">
        <span style="font-size:var(--text-sm);color:var(--color-text);font-weight:600;">Odeur</span>
        <div class="rec-toggle-pair" style="gap:.35rem;">
          <button class="rec-toggle-btn ok-sel" type="button" style="cursor:default;min-height:36px;padding:.4rem .75rem;font-size:var(--text-sm);">✓ Conforme</button>
          <button class="rec-toggle-btn" type="button" style="cursor:default;min-height:36px;padding:.4rem .75rem;font-size:var(--text-sm);">✗ NC</button>
        </div>
      </div>
    </div>
  </div>

  <button class="rec-btn-suivant" type="button" style="cursor:default;">+ Ajouter</button>

</div>

**Comment remplir chaque champ :**

| Champ | Comment remplir |
|---|---|
| **Produit** | Tapez le début du nom ou de l'espèce. La liste propose les produits du catalogue. Exemples : tapez "bœuf" ou "VB" pour les viandes bovines, "porc" ou "cochon" pour le porc. |
| **N° de lot fournisseur** | Recopiez le numéro de lot imprimé sur l'étiquette du carton ou du colis. Si le fournisseur n'a pas mis de numéro, tapez **"Pas de N° de lot"** — le système en génère un automatiquement (format : `VB-20260514-001`). |
| **DLC ou DLUO** | Tapez la date limite inscrite sur l'emballage. **La date ne peut pas être déjà passée.** |
| **Couleur / Consistance / Exsudat / Odeur** | Pour chaque critère, tapez **✓ Conforme** si c'est normal, **✗ NC** si c'est anormal. Dès qu'un produit est sélectionné, l'application affiche la norme attendue pour cette espèce (ex. : *Couleur normale pour le bœuf : Rouge vif*). |

> **Astuce :** Le bouton **`+ Ajouter`** reste grisé tant que le produit, le lot et la DLC ne sont pas tous renseignés. Si vous tapez dessus et qu'il ne se passe rien, regardez quel champ est mis en évidence — c'est celui qu'il faut compléter.

#### Après avoir tapé "+ Ajouter"

Le produit apparaît dans la liste en haut de l'écran avec son badge de conformité :

<div style="display:flex;gap:.75rem;flex-wrap:wrap;padding:.75rem;background:var(--color-card);border-radius:var(--radius);border:1px solid var(--color-secondary);margin:.5rem 0;">
  <div style="display:flex;align-items:center;gap:.5rem;">
    <span class="rec-badge conforme">✓ OK</span> Produit conforme sur tous les critères
  </div>
  <div style="display:flex;align-items:center;gap:.5rem;">
    <span class="rec-badge nc">✗ NC</span> Au moins un critère visuel non conforme — procédure à suivre à l'étape 5
  </div>
</div>

Vous pouvez modifier un produit déjà ajouté en tapant **`✎ Modifier`** sur sa carte.

Répétez l'opération pour chaque article de la livraison. Quand vous avez tout saisi, tapez **`Récap →`**.

#### Normes visuelles par espèce

| Espèce | Couleur normale |
|---|---|
| **Bœuf** | Rouge vif |
| **Veau** | Rose pâle à rose vif |
| **Porc** | Rose pâle |
| **Agneau** | Rouge rosé |
| **Volaille** | Chair blanche à jaune pâle |
| **Gibier** | Rouge foncé à bordeaux |
| **Cheval** | Rouge foncé |

pH normal pour toutes les espèces : **5,5 à 5,7**

---

### Étape 5 — Récapitulatif & Clôture

Cette page résume tout ce que vous avez saisi. **Lisez-la attentivement avant de clôturer.**

#### Si tout est conforme

Le bandeau affiche :

<div style="padding:.75rem 1.25rem;border-radius:var(--radius);margin:.5rem 0;display:inline-flex;align-items:center;gap:.5rem;">
  <span class="rec-badge conforme">✓ Tout conforme</span>
</div>

Tapez **`✔ Clôturer la fiche`** (bouton vert). C'est terminé.

#### Si des produits sont non conformes — Procédure NC obligatoire

Le bandeau affiche :

<div style="padding:.75rem 1.25rem;border-radius:var(--radius);margin:.5rem 0;display:inline-flex;align-items:center;gap:.5rem;">
  <span class="rec-badge nc">✗ Présence de non-conformité(s)</span>
</div>

Le bouton **Clôturer** est **bloqué**. Vous devez suivre la procédure en 3 sous-étapes qui s'affiche automatiquement.

##### Sous-étape 1 sur 3 — Mesurer la température à cœur

Pour chaque produit non conforme, sortez votre thermomètre à sonde et mesurez la température **au cœur** du produit. Saisissez la valeur dans le champ.

Le badge se met à jour immédiatement :
- <span class="rec-badge conforme">✓ Conforme après contrôle</span> : la température à cœur est dans les limites autorisées — le produit peut être accepté.
- <span class="rec-badge nc">✗ Non conforme confirmé</span> : la température est trop haute — le produit doit faire l'objet d'une fiche PCR01.

> **Règle :** Pour les produits conservés à 0-4°C, la température à cœur ne doit pas dépasser **5°C** (tolérance de +1°C sur la borne haute).

Quand tous les produits NC ont leur température saisie, tapez **Suivant →**.

##### Sous-étape 2 sur 3 — Le livreur est encore là ?

<div style="display:flex;gap:.75rem;max-width:400px;margin:.5rem 0;">
  <button class="rec-toggle-btn ok-sel" type="button" style="cursor:default;flex:1;">✔ Oui, il est là</button>
  <button class="rec-toggle-btn nc-sel" type="button" style="cursor:default;flex:1;">✕ Non, il est parti</button>
</div>

Répondez. Dans les deux cas, le bouton **`Remplir fiche PCR01 →`** s'active.

##### Sous-étape 3 sur 3 — Fiche PCR01

Tapez **`Remplir fiche PCR01 →`**. Vous êtes redirigé vers le formulaire de non-conformité réglementaire. Remplissez-le, puis revenez ici. Le badge **`✓ Fiches PCR01 enregistrées`** confirmera le retour et débloquera la clôture.

#### Clôturer la fiche

Tapez **`✔ Clôturer la fiche`**. Un écran de confirmation s'affiche avec un récapitulatif et un retour automatique à l'accueil au bout de 5 secondes.

---

### Si l'application reste inactive 5 minutes

Si personne ne touche l'écran pendant 5 minutes pendant une réception en cours, un message d'alerte apparaît :
- Tapez **Continuer** pour reprendre où vous en étiez.
- Tapez **Quitter** pour abandonner et revenir à l'accueil.

---

### Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Ce que ça veut dire | Que faire |
|---|---|---|
| Champ Date en rouge | La date saisie est dans le passé | Corrigez la date |
| *"Le nom du fournisseur est obligatoire"* | Champ fournisseur vide | Cherchez et sélectionnez le fournisseur |
| *"La photo du bon de livraison est obligatoire"* | Pas de photo prise | Tapez la zone 📋 et photographiez le BL |
| Bouton `+ Ajouter` grisé | Un champ obligatoire est vide | Regardez quel champ est mis en évidence et complétez-le |
| Champ DLC en rouge | La date est déjà passée ou vide | Vérifiez la date sur l'emballage et resaisissez |
| *"Sélectionnez un produit dans la liste"* | Vous avez tapé un nom mais pas sélectionné dans la liste déroulante | Tapez le nom et choisissez un résultat dans la liste |
| *"Aucun personnel enregistré"* | Aucun prénom configuré | Contactez le responsable pour configurer les prénoms dans Admin |

---

---

## Module 3 — Fabrication & Étiquettes

### À quoi ça sert ?

Ce module sert à **enregistrer une fabrication maison** (rôti farci, boulettes, plat traiteur, charcuterie…) et à **imprimer l'étiquette** qui part sur le produit. Il calcule automatiquement les quantités d'ingrédients, choisit les bons lots à utiliser (les plus anciens en premier), calcule la DLC du produit fini, et imprime un ticket thermique sur l'imprimante Brother du labo.

Pour y accéder : tapez la tuile **🏭 PRODUCTION** sur l'écran d'accueil, puis tapez **🔪 FABRICATION**.

---

### La barre de progression — 4 étapes numérotées

<div style="background:var(--color-card);border-radius:var(--radius);border:2px solid var(--color-secondary);overflow:hidden;max-width:560px;">

<header class="fab-header" style="height:56px;">
  <button class="fab-btn-retour" type="button" style="cursor:default;">←</button>
  <div class="fab-header-titre">FABRICATION</div>
  <div class="fab-horloge">09:15</div>
</header>

<div class="fab-topbar">
  <div class="fab-progress">
    <div class="fab-dot fab-dot--done">✓</div>
    <div class="fab-dot-line fab-dot-line--done"></div>
    <div class="fab-dot fab-dot--done">✓</div>
    <div class="fab-dot-line fab-dot-line--done"></div>
    <div class="fab-dot fab-dot--active">3</div>
    <div class="fab-dot-line"></div>
    <div class="fab-dot">4</div>
  </div>
  <div class="fab-bandeau">
    <div class="fab-bandeau-nom">🍖 Rôti de bœuf farci</div>
    <div class="fab-bandeau-dlc">DLC J+3</div>
  </div>
</div>

</div>

Chaque **rond numéroté** représente une étape. Les ronds verts avec une coche sont les étapes déjà validées. Le rond brun foncé est l'étape en cours. À partir de l'étape 2, un bandeau affiche le nom de la recette choisie et sa durée de vie par défaut.

---

### Étape 1 — Choisir une recette

L'écran affiche une grille de tuiles, **une tuile par recette** disponible. Chaque tuile affiche l'icône 🍖, le nom de la recette, et un badge de durée de vie (ex. `DLC J+3`).

<div style="background:var(--color-bg);border-radius:var(--radius);border:2px solid var(--color-secondary);padding:1.25rem;max-width:560px;">

  <div style="margin-bottom:1rem;">
    <input class="fab-filter-input" type="text" placeholder="Filtrer les recettes…" style="pointer-events:none;">
  </div>

  <div class="recettes-grid">
    <div class="recette-tuile" style="cursor:default;">
      <div class="recette-tuile-img">🍖</div>
      <div class="recette-tuile-nom">Rôti de bœuf farci</div>
      <div class="recette-tuile-dlc">DLC J+3</div>
    </div>
    <div class="recette-tuile" style="cursor:default;">
      <div class="recette-tuile-img">🍖</div>
      <div class="recette-tuile-nom">Boulettes maison</div>
      <div class="recette-tuile-dlc">DLC J+3</div>
    </div>
    <div class="recette-tuile" style="cursor:default;">
      <div class="recette-tuile-img">🍖</div>
      <div class="recette-tuile-nom">Merguez artisanales</div>
      <div class="recette-tuile-dlc">DLC J+2</div>
    </div>
  </div>

</div>

- **Cherchez** votre recette dans le champ de filtre si la liste est longue.
- **Tapez la tuile** de la recette à fabriquer. La page passe automatiquement à l'étape 2.
- Si vous voulez créer ou modifier une recette, tapez **`✏️ Gérer les recettes`** (en haut à droite) — cela ouvre le module d'administration des recettes.

> Si la grille est vide (*"Aucune recette disponible"*), aucune recette n'a encore été créée. Contactez le responsable pour en ajouter via **⚙ Admin** → Recettes.

---

### Étape 2 — Calculateur de production

Vous indiquez ici **combien vous faites aujourd'hui**. L'application calcule automatiquement les quantités de chaque ingrédient.

<div style="background:var(--color-bg);border-radius:var(--radius);border:2px solid var(--color-secondary);padding:1.5rem;max-width:500px;display:flex;flex-direction:column;gap:1.1rem;">

  <div style="font-size:var(--text-xl);font-weight:800;color:var(--color-accent);text-transform:uppercase;letter-spacing:.05em;">Calculateur de production</div>

  <div>
    <label style="font-size:var(--text-sm);font-weight:700;color:var(--color-accent);display:block;margin-bottom:.4rem;">Production ciblée du jour</label>
    <div style="display:flex;align-items:center;gap:.5rem;">
      <input class="fab-input" type="text" placeholder="ex : 4.5" style="pointer-events:none;flex:1;">
      <span style="font-weight:700;color:var(--color-text);white-space:nowrap;">kg</span>
    </div>
    <div style="font-size:var(--text-xs);color:#6b7280;margin-top:.3rem;">Base recette : 3 kg</div>
  </div>

  <div style="background:var(--color-card);border-radius:var(--radius-sm);border:1px solid var(--color-secondary);padding:1rem;">
    <div style="font-size:var(--text-sm);font-weight:700;color:var(--color-accent);margin-bottom:.5rem;">Ingrédients calculés</div>
    <div style="display:flex;flex-direction:column;gap:.4rem;">
      <div style="display:flex;justify-content:space-between;font-size:var(--text-sm);">
        <span>Bœuf haché</span><strong>1,50 kg</strong>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:var(--text-sm);">
        <span>Veau haché</span><strong>0,75 kg</strong>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:var(--text-sm);">
        <span>Porc haché</span><strong>0,38 kg</strong>
      </div>
    </div>
  </div>

  <button style="width:100%;padding:1.1rem;background:var(--color-accent);color:white;border:none;border-radius:var(--radius);font-size:1.1rem;font-weight:700;cursor:default;min-height:64px;">Suivant →</button>

</div>

- Tapez le champ et saisissez la quantité que vous voulez fabriquer (ex : `4.5` pour 4,5 kg). Utilisez le point pour les décimales.
- Les quantités de tous les ingrédients se recalculent **au fur et à mesure que vous tapez**.
- Si la recette n'a pas de base de rendement configurée, les quantités s'affichent telles quelles (fixes) avec un avertissement.
- Tapez **`Suivant →`** quand vous êtes prêt.

---

### Étape 3 — Traçabilité & Lots

C'est ici que l'application vous indique **quel lot de matière première utiliser** pour chaque ingrédient. Elle applique automatiquement la règle **FIFO** : on utilise d'abord le lot qui expire le plus tôt.

<div style="background:var(--color-bg);border-radius:var(--radius);border:2px solid var(--color-secondary);padding:1.5rem;max-width:560px;display:flex;flex-direction:column;gap:.75rem;">

  <div style="font-size:var(--text-xl);font-weight:800;color:var(--color-accent);text-transform:uppercase;letter-spacing:.05em;">Traçabilité &amp; Lots</div>

  <!-- Ligne OK -->
  <div style="background:#f0fdf4;border:1.5px solid var(--color-ok);border-radius:var(--radius-sm);padding:.85rem 1rem;display:flex;align-items:center;justify-content:space-between;gap:.75rem;">
    <div>
      <div style="font-weight:700;color:var(--color-text);font-size:var(--text-sm);">✓ &nbsp;Bœuf haché</div>
      <div style="font-size:var(--text-xs);color:#4b5563;margin-top:.2rem;">Lot VB-20260510-002 &nbsp;|&nbsp; DLC 17/05/2026</div>
    </div>
    <button style="background:#e8f5ec;border:1px solid var(--color-ok);color:var(--color-ok);padding:.35rem .75rem;border-radius:var(--radius-sm);font-size:var(--text-xs);font-weight:700;cursor:default;white-space:nowrap;">✏️ Personnaliser</button>
  </div>

  <!-- Ligne OK -->
  <div style="background:#f0fdf4;border:1.5px solid var(--color-ok);border-radius:var(--radius-sm);padding:.85rem 1rem;display:flex;align-items:center;justify-content:space-between;gap:.75rem;">
    <div>
      <div style="font-weight:700;color:var(--color-text);font-size:var(--text-sm);">✓ &nbsp;Veau haché</div>
      <div style="font-size:var(--text-xs);color:#4b5563;margin-top:.2rem;">Lot VX-20260511-001 &nbsp;|&nbsp; DLC 18/05/2026</div>
    </div>
    <button style="background:#e8f5ec;border:1px solid var(--color-ok);color:var(--color-ok);padding:.35rem .75rem;border-radius:var(--radius-sm);font-size:var(--text-xs);font-weight:700;cursor:default;white-space:nowrap;">✏️ Personnaliser</button>
  </div>

  <!-- Ligne MANQUANTE -->
  <div style="background:#fef2f2;border:1.5px solid var(--color-alert);border-radius:var(--radius-sm);padding:.85rem 1rem;display:flex;align-items:center;justify-content:space-between;gap:.75rem;">
    <div>
      <div style="font-weight:700;color:var(--color-alert);font-size:var(--text-sm);">⚠ &nbsp;Porc haché</div>
      <div style="font-size:var(--text-xs);color:#991b1b;margin-top:.2rem;">Aucun lot disponible en stock</div>
    </div>
    <button style="background:#fee2e2;border:1px solid var(--color-alert);color:var(--color-alert);padding:.35rem .75rem;border-radius:var(--radius-sm);font-size:var(--text-xs);font-weight:700;cursor:default;white-space:nowrap;animation:none;">🔄 Remplacer</button>
  </div>

  <button style="width:100%;padding:1.1rem;background:#ccc;color:white;border:none;border-radius:var(--radius);font-size:1.1rem;font-weight:700;cursor:default;min-height:64px;opacity:.5;">Confirmer les lots →</button>

</div>

**Ce que veulent dire les lignes :**

- **Ligne verte ✓** : l'application a trouvé un lot en stock pour cet ingrédient. Le numéro de lot et la DLC sont affichés. C'est ce lot qui sera utilisé.
- **Ligne rouge ⚠** : aucun lot n'est disponible en stock pour cet ingrédient. **Vous devez remplacer** avant de pouvoir continuer.

#### Changer de lot manuellement — bouton `✏️ Personnaliser`

Tapez **`✏️ Personnaliser`** sur une ligne verte pour choisir un autre lot que celui proposé. Une fenêtre s'ouvre avec tous les produits disponibles en stock, triés par date d'expiration (le plus urgent en premier, marqué ⭐ PRIORITÉ FIFO).

Si vous choisissez un produit **différent** de l'ingrédient d'origine, une confirmation s'affiche : *"Vous utilisez du [nom] à la place du [original]. Confirmer ?"* Tapez **Confirmer**.

#### Remplacer un ingrédient manquant — bouton `🔄 Remplacer`

Tapez **`🔄 Remplacer`** sur une ligne rouge. La même fenêtre de sélection s'ouvre. Choisissez le produit de substitution dans le stock disponible.

> Le bouton **`Confirmer les lots →`** reste grisé tant qu'il reste au moins une ligne rouge. Toutes les lignes doivent être vertes pour continuer.

#### Urgence DLC dans la fenêtre de sélection

Les tuiles de produits dans la fenêtre de choix affichent une couleur selon l'urgence :
- **Rouge** : DLC dans 2 jours ou moins — à utiliser en priorité absolue
- **Orange** : DLC dans 5 jours ou moins — à utiliser rapidement
- **Sans couleur** : DLC confortable

---

### Étape 4 — Récapitulatif & Impression

Cette étape affiche un résumé complet avant d'imprimer. **Vérifiez attentivement la DLC calculée.**

<div style="background:var(--color-card);border-radius:var(--radius);border:2px solid var(--color-secondary);padding:1.5rem;max-width:500px;display:flex;flex-direction:column;gap:1rem;">

  <div style="font-size:var(--text-xl);font-weight:800;color:var(--color-accent);text-transform:uppercase;">Récapitulatif</div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem;">
    <div>
      <div style="font-size:var(--text-xs);color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em;">Recette</div>
      <div style="font-weight:700;">Rôti de bœuf farci</div>
    </div>
    <div>
      <div style="font-size:var(--text-xs);color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em;">Date fabrication</div>
      <div style="font-weight:700;">mercredi 14 mai 2026</div>
    </div>
    <div>
      <div style="font-size:var(--text-xs);color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em;">Poids fabriqués</div>
      <div style="font-weight:700;">4,5 kg</div>
    </div>
    <div>
      <div style="font-size:var(--text-xs);color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em;">DLC calculée</div>
      <div style="font-weight:800;color:var(--color-alert);font-size:var(--text-lg);">17/05/2026</div>
    </div>
  </div>

  <div style="background:#f5ede0;border-radius:var(--radius-sm);padding:.85rem 1rem;border-left:4px solid var(--color-accent);">
    <div style="font-size:var(--text-xs);font-weight:700;color:var(--color-accent);margin-bottom:.4rem;">Ingrédients &amp; lots utilisés</div>
    <div style="font-size:var(--text-sm);display:flex;flex-direction:column;gap:.25rem;">
      <div>1,50 kg Bœuf haché — Lot VB-20260510-002</div>
      <div>0,75 kg Veau haché — Lot VX-20260511-001</div>
      <div>0,38 kg Porc haché — Lot PC-20260512-001 <em>(substitut)</em></div>
    </div>
  </div>

  <div>
    <label style="font-size:var(--text-sm);font-weight:700;color:var(--color-accent);display:block;margin-bottom:.4rem;">Opérateur *</label>
    <select class="fab-input" style="pointer-events:none;">
      <option>Marie</option>
      <option>Jean</option>
    </select>
  </div>

  <button style="width:100%;padding:1.1rem;background:var(--color-ok);color:white;border:none;border-radius:var(--radius);font-size:1.1rem;font-weight:700;cursor:default;min-height:64px;">🖨 Générer &amp; imprimer</button>

</div>

**Vérifiez :**
- Le nom de la recette et la date sont corrects.
- La **DLC calculée** — c'est la date qui sera imprimée sur l'étiquette. Elle peut être plus courte que prévu si un ingrédient expire bientôt (voir règle ci-dessous).
- La liste des lots utilisés — vérifiez qu'il n'y a pas de "substitut" inattendu.
- Sélectionnez votre **prénom** dans le menu Opérateur.

Tapez **`🖨 Générer & imprimer`** pour enregistrer la fabrication et lancer l'impression.

---

### La règle de la DLC — ce qu'il faut absolument savoir

> **Règle HACCP interne :** La DLC du produit fini est toujours la date la plus courte entre :
> - La date du jour + la durée de vie de la recette (ex. : J+3)
> - La date d'expiration du lot d'ingrédient qui expire le plus tôt

**Exemple concret :** Vous faites un rôti farci (DLC théorique J+3, soit jusqu'au 17/05). Mais le bœuf haché que vous utilisez a une DLC au 15/05. La DLC du rôti sera le **15/05**, pas le 17/05.

Si une DLC est réduite par un ingrédient, un message orange apparaît à l'écran :
> *"⚠️ DLC réduite à 15/05/2026 à cause de : Bœuf haché"*

Ce message disparaît seul après 5 secondes.

---

### L'étiquette imprimée (ticket thermique Brother 62 mm)

L'imprimante du labo imprime automatiquement un ticket qui contient dans l'ordre :

| Zone | Ce qu'on y lit |
|---|---|
| **Nom du produit** | En majuscules, avec le poids fabriqué |
| **DLC** | La date en grand, en rouge, encadrée |
| **Numéro de lot** | Format : `Lot : MC-20260514-0001` |
| **Ingrédients & lots** | La liste de tous les ingrédients avec leur lot et leur DLC |
| **Pied** | `Fabriqué le 14/05/2026 par Marie` |

Ce ticket se colle directement sur le produit ou sur le bac de conservation.

---

### Après l'impression — que faire ensuite ?

Un écran de confirmation s'affiche avec le numéro de lot généré. Trois choix :

- **`Même recette`** : vous refaites la même recette en plus ou moins grande quantité — repart à l'étape 2 directement.
- **`Nouvelle fabrication`** : vous passez à une recette différente — repart à l'étape 1.
- **`← Retour au hub production`** : vous avez terminé, retour à l'écran de production.

L'écran revient automatiquement au hub de production après **20 secondes** si vous ne touchez rien.

---

### Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Ce que ça veut dire | Que faire |
|---|---|---|
| *"Aucune recette disponible"* | Aucune recette n'a été créée | Contactez le responsable pour en créer une |
| *"Veuillez saisir la production ciblée du jour"* | Le champ quantité est vide | Saisissez la quantité et réessayez |
| Ligne rouge ⚠ sur un ingrédient | Cet ingrédient n'est pas en stock | Tapez 🔄 Remplacer et choisissez un substitut |
| *"Aucun lot en stock pour ce produit"* | Le substitut choisi n'a pas de stock non plus | Choisissez un autre produit |
| *"Veuillez sélectionner un opérateur"* | Aucun prénom sélectionné à l'étape 4 | Sélectionnez votre prénom avant d'imprimer |
| Message orange sur la DLC | La DLC a été raccourcie par un ingrédient | Vérifiez la DLC sur l'étiquette — elle est correcte et obligatoire |
| Rien ne s'imprime | L'imprimante est éteinte ou déconnectée | Vérifiez que l'imprimante Brother est allumée et connectée |

---

---

## Module 4 — Fiche Incident PCR01

### À quoi ça sert ?

La fiche PCR01 est le **document officiel de non-conformité réception**. Elle s'ouvre **automatiquement** depuis le module Réception quand un produit est déclaré non conforme après le contrôle à cœur — ou quand une livraison entière est refusée pour cause de camion sale. Vous n'avez **pas besoin de la chercher** sur l'écran d'accueil : elle apparaît au bon moment.

Elle sert à enregistrer ce qui s'est passé, les mesures prises, et si le livreur est encore là, à recueillir sa signature sur la tablette.

---

### Les deux situations qui déclenchent une fiche PCR01

| Situation | Ce qui se passe |
|---|---|
| **Un ou plusieurs produits restent NC après contrôle à cœur** | Une fiche PCR01 est créée pour chaque produit NC. Si vous avez 3 produits NC, vous remplissez 3 fiches à la suite. |
| **Refus total de la livraison (camion sale)** | Une seule fiche PCR01 est créée pour l'ensemble du refus, quel que soit le nombre de fournisseurs. |

---

### Ce que vous voyez en arrivant sur la fiche

L'en-tête de la page est **rouge vif** — c'est voulu, pour que tout le monde voit qu'il y a un problème à traiter.

<div style="background:var(--color-bg);border-radius:var(--radius);border:2px solid var(--color-alert);overflow:hidden;max-width:560px;">

<header class="pcr-header">
  <button class="pcr-btn-retour" type="button" style="cursor:default;">← Retour</button>
  <div class="pcr-header-titre">FICHE INCIDENT PCR01</div>
  <div class="pcr-header-badge">1/2</div>
</header>

<main class="pcr-main" style="position:relative;overflow:visible;padding-bottom:1rem;">

  <div class="pcr-doc-header">
    <div class="pcr-ref">Réf. PCR01 — Non-conformité réception</div>
    <div class="pcr-date">mercredi 14 mai 2026</div>
    <div class="pcr-operateur">Opérateur : Marie à 09:15</div>
  </div>

  <div class="pcr-bloc pcr-bloc-produit">
    <div class="pcr-bloc-titre">Produit non conforme</div>
    <div class="pcr-bloc-corps">
      <div class="pcr-champ-ligne">
        <span class="pcr-champ-label">Produit</span>
        <span class="pcr-champ-val">Entrecôte charolaise</span>
      </div>
      <div class="pcr-champ-ligne">
        <span class="pcr-champ-label">Fournisseur</span>
        <span class="pcr-champ-val">Établissements Bernard</span>
      </div>
      <div class="pcr-champ-ligne">
        <span class="pcr-champ-label">N° lot</span>
        <span class="pcr-champ-val">LOT-2026-047</span>
      </div>
      <div class="pcr-champ-ligne">
        <span class="pcr-champ-label">DLC</span>
        <span class="pcr-champ-val">20/05/2026</span>
      </div>
      <div class="pcr-champ-ligne">
        <span class="pcr-champ-label">Non-conformité</span>
        <span class="pcr-champ-val pcr-nc-badge">température · couleur</span>
      </div>
      <div class="pcr-champ-ligne">
        <span class="pcr-champ-label">Action immédiate</span>
        <span class="pcr-champ-val pcr-action-badge">🌡️ Contrôle à cœur — NC confirmé (T° : 7,2°C)</span>
      </div>
    </div>
  </div>

  <div class="pcr-bloc pcr-bloc-etapes">
    <div class="pcr-bloc-titre">Étapes d'identification et de traitement</div>
    <div class="pcr-etapes-liste">
      <div class="pcr-etape-item">
        <div class="pcr-etape-puce"></div>
        <div class="pcr-etape-texte">Contrôle à la réception (visuel / température) → Non-conformité détectée : température, couleur (température camion : 7,2°C).</div>
      </div>
      <div class="pcr-etape-item">
        <div class="pcr-etape-puce"></div>
        <div class="pcr-etape-texte">Lot isolé immédiatement pour prise de température à cœur.</div>
      </div>
      <div class="pcr-etape-item">
        <div class="pcr-etape-puce"></div>
        <div class="pcr-etape-texte">Livreur présent : feuille de reprise avec retour marchandise signée par le livreur.</div>
      </div>
    </div>
  </div>

</main>
</div>

**Ce que vous voyez et ce que ça veut dire :**

- **Badge `1/2` en haut à droite** : vous êtes sur la première des deux fiches à remplir. Après avoir enregistré celle-ci, la deuxième s'affichera automatiquement.
- **Bloc rouge "Produit non conforme"** : toutes les informations sont pré-remplies depuis ce que vous avez saisi à la réception. Vérifiez qu'elles sont correctes.
- **"Non-conformité"** en rouge : les critères qui ont été déclarés non conformes (température, couleur, consistance, exsudat, odeur, pH).
- **"Action immédiate"** en orange : ce qui a déjà été fait (le contrôle à cœur avec la température mesurée).
- **Timeline verte** : le résumé chronologique des étapes, généré automatiquement.

---

### Ce que vous devez faire — étape par étape

#### 1. Vérifiez les informations pré-remplies

Tout est déjà rempli. Lisez simplement pour vérifier que le nom du produit, le fournisseur, le lot et les motifs NC sont corrects.

#### 2. Le livreur est encore là ? (si refus camion)

En cas de refus total de livraison pour camion non conforme, une question s'affiche :

<div style="background:white;border-radius:var(--radius);border:2px solid var(--color-secondary);padding:1rem;max-width:400px;">
  <div class="pcr-bloc-titre" style="margin:-1rem -1rem .85rem;border-radius:var(--radius-sm) var(--radius-sm) 0 0;">Le livreur est encore là ?</div>
  <div style="display:flex;gap:.75rem;">
    <button class="rec-toggle-btn ok-sel" type="button" style="cursor:default;flex:1;">✔ Oui, il est là</button>
    <button class="rec-toggle-btn nc-sel" type="button" style="cursor:default;flex:1;">✕ Non, il est parti</button>
  </div>
</div>

Tapez la bonne réponse. Elle conditionne ce qui s'affiche ensuite.

#### 3. Si le livreur est présent — bloc Signature

Un bloc "Signature du livreur" apparaît. Vous devez d'abord choisir son attitude :

<div style="background:white;border-radius:var(--radius);border:2px solid var(--color-secondary);padding:1rem;max-width:500px;display:flex;flex-direction:column;gap:.75rem;">
  <div class="pcr-bloc-titre" style="margin:-1rem -1rem .5rem;border-radius:var(--radius-sm) var(--radius-sm) 0 0;">Signature du livreur *</div>
  <div style="display:flex;gap:.75rem;">
    <button class="rec-toggle-btn ok-sel" type="button" style="cursor:default;flex:1;font-size:var(--text-sm);">✓ Atteste de la NC et accepte le retour</button>
    <button class="rec-toggle-btn nc-sel" type="button" style="cursor:default;flex:1;font-size:var(--text-sm);">✕ N'atteste pas la NC et refuse le retour</button>
  </div>
  <div style="background:#f5f5f5;border:1.5px solid var(--color-secondary);border-radius:var(--radius-sm);height:80px;display:flex;align-items:center;justify-content:center;color:#888;font-style:italic;font-size:var(--text-sm);">
    Zone de signature — faire signer le livreur ici avec le doigt ou le stylet
  </div>
  <button style="background:#f3ebdf;border:1px solid var(--color-secondary);border-radius:var(--radius-sm);padding:.4rem .85rem;font-size:var(--text-sm);font-weight:600;color:var(--color-text);cursor:default;">↺ Effacer</button>
</div>

- **✓ Atteste et accepte le retour** : le livreur reconnaît le problème et reprend la marchandise. Faites-lui signer la zone de signature avec le doigt ou le stylet. Le texte de l'action corrective se met à jour automatiquement.
- **✕ N'atteste pas et refuse le retour** : le livreur nie le problème ou refuse de reprendre. Un bouton **"🖨️ Imprimer étiquette À RETOURNER"** apparaît — imprimez-la et collez-la sur le produit.

> La signature est **obligatoire** si le livreur est présent. Si vous vous êtes trompé dans le dessin, tapez **↺ Effacer** et recommencez.

#### 4. Si le livreur est parti

Un bouton **"🖨️ Imprimer étiquette À RETOURNER"** apparaît. Tapez-le pour imprimer l'étiquette et collez-la sur le produit isolé en chambre froide. Le bouton affiche ensuite `✓ Imprimé — [Nom produit]` pour confirmer.

#### 5. Action corrective — vérifiez et ajustez si nécessaire

<div style="background:white;border-radius:var(--radius);border:2px solid var(--color-secondary);padding:1rem;max-width:500px;">
  <div class="pcr-bloc-titre" style="margin:-1rem -1rem .85rem;border-radius:var(--radius-sm) var(--radius-sm) 0 0;">Action corrective *</div>
  <div style="background:#FFFAF5;border:2px solid var(--color-alert);border-radius:var(--radius-sm);padding:.85rem 1rem;font-size:.9rem;color:var(--color-text);line-height:1.55;">
    Non-conformité constatée à la réception : température, couleur sur Entrecôte charolaise (lot LOT-2026-047). Contrôle à cœur effectué : non-conformité confirmée. La température à cœur mesurée est de 7,2°C. La non-conformité est attestée et le retour accepté, la feuille de reprise avec retour marchandise a été signée par le livreur.
  </div>
</div>

Le texte est **pré-rempli automatiquement** selon ce que vous avez saisi pendant la réception. Dans la plupart des cas, vous n'avez rien à modifier. Si vous voulez préciser quelque chose, tapez dans la zone de texte et écrivez librement.

> Ce champ est **obligatoire**. Vous ne pouvez pas enregistrer si cette zone est vide.

#### 6. Commentaire (optionnel)

Une deuxième zone de texte vous permet d'ajouter une note libre, par exemple : *"Relancer le fournisseur la semaine prochaine"* ou *"Vérifier le prochain lot à la livraison suivante"*.

#### 7. Enregistrez la fiche

Tapez le bouton **`💾 Enregistrer cette fiche`** tout en bas de l'écran.

- Si des champs obligatoires manquent, un message d'erreur apparaît et la zone concernée se met en évidence (contour rouge, la page défile automatiquement vers le problème).
- Si tout est correct, la fiche est enregistrée.

---

### Si vous avez plusieurs fiches à remplir (plusieurs produits NC)

Après avoir enregistré la première fiche, la page passe **automatiquement** à la suivante. Le badge en haut passe à `2/2`, puis `3/3`, etc. Recommencez la même procédure pour chaque produit.

Après la dernière fiche, vous revenez automatiquement dans le module Réception pour **clôturer la fiche de réception**.

---

### L'étiquette "À RETOURNER" imprimée

Quand vous tapez le bouton d'impression, une étiquette s'imprime (sur l'imprimante habituelle, **pas** sur la thermique Brother — c'est une feuille A4). Elle contient :

| Zone | Contenu |
|---|---|
| **Bandeau rouge** | `PRODUIT NON CONFORME` |
| **Titre** | `À RETOURNER` |
| **Référence** | `Réf. PCR01 — Non-conformité réception` |
| **Tableau** | Produit, fournisseur, N° lot, DLC, motif NC, action immédiate |
| **Pied** | `Au Comptoir des Lilas — Réf. PCR01` |

Collez cette feuille directement sur le colis ou la boîte et isolez le produit en chambre froide dans une zone identifiée "retour fournisseur".

---

### Consulter les fiches PCR01 passées

Pour retrouver les fiches d'incident d'une réception passée :
1. Allez dans **🗂️ HISTORIQUE** depuis l'écran d'accueil.
2. Ouvrez le détail d'une réception.
3. Tapez le bouton **"Voir incidents"** — la liste des fiches PCR01 s'affiche.
4. Tapez une fiche pour la consulter en détail.

---

### Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Ce que ça veut dire | Que faire |
|---|---|---|
| *"L'action corrective est obligatoire"* | Le champ action corrective est vide | Tapez un texte dans la zone (ou vérifiez qu'il n'a pas été effacé) |
| *"Veuillez indiquer si le livreur est présent ou absent"* | Vous n'avez pas tapé Oui ou Non | Tapez l'un des deux boutons |
| *"La signature du livreur est obligatoire"* | Canvas vide alors que le livreur est présent | Faites signer le livreur dans la zone de dessin |
| La page s'ouvre sur la réception | Vous avez accédé à PCR01 directement, sans passer par la réception | Revenez au module Réception et suivez la procédure NC |

---

---

## Module 5 — Tâches HACCP

### À quoi ça sert ?

Ce module regroupe **tout le suivi quotidien HACCP** : l'état des contrôles à faire, ceux en retard et ceux déjà faits. Il sert aussi de **portail** vers les sous-modules de contrôle réglementaire (nettoyage, étalonnage des thermomètres, températures des enceintes, lutte antiparasitaire, e-learning).

Pour y accéder : tapez la tuile **✅ TÂCHES HACCP** sur l'écran d'accueil.

---

### L'écran d'accueil des tâches — le portail

<div class="hub-body" style="position:relative;background:var(--color-bg);padding:1rem;border-radius:var(--radius);border:2px solid var(--color-secondary);max-width:600px;">

<header class="hub-header" style="border-radius:var(--radius-sm);margin-bottom:1rem;">
  <a style="background:rgba(255,255,255,.15);color:#fff;padding:.4rem .8rem;border-radius:var(--radius-sm);text-decoration:none;font-size:var(--text-sm);">← Hub</a>
  <div class="hub-titre">TÂCHES HACCP</div>
  <div style="color:var(--color-secondary);font-size:var(--text-sm);">09:15</div>
</header>

<main style="display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;">
  <a class="hub-tuile" style="text-decoration:none;">
    <div class="hub-tuile-icone">🧹</div>
    <div class="hub-tuile-titre">NETTOYAGE</div>
    <div class="hub-tuile-statut">✓ Validé aujourd'hui</div>
  </a>
  <a class="hub-tuile" style="text-decoration:none;">
    <div class="hub-tuile-icone">🌡️</div>
    <div class="hub-tuile-titre">ÉTALONNAGE</div>
    <div class="hub-tuile-statut">Prochain : 20/05</div>
  </a>
  <a class="hub-tuile" style="text-decoration:none;">
    <div class="hub-tuile-icone">🌡️</div>
    <div class="hub-tuile-titre">TEMPÉRATURES</div>
    <div class="hub-tuile-statut">2 alertes actives</div>
  </a>
  <a class="hub-tuile" style="text-decoration:none;">
    <div class="hub-tuile-icone">🐛</div>
    <div class="hub-tuile-titre">NUISIBLES</div>
    <div class="hub-tuile-statut">IPM — Plan de lutte</div>
  </a>
  <a class="hub-tuile" style="text-decoration:none;">
    <div class="hub-tuile-icone">🎓</div>
    <div class="hub-tuile-titre">E-LEARNING</div>
    <div class="hub-tuile-statut">Formation HACCP</div>
  </a>
</main>

</div>

Tapez la tuile du sous-module que vous voulez ouvrir. Les statuts affichés sur chaque tuile se mettent à jour automatiquement au chargement de la page :

| Tuile | Ce que le statut indique |
|---|---|
| **🧹 NETTOYAGE** | Si le nettoyage du jour a été validé ou reste à faire |
| **🌡️ ÉTALONNAGE** | La date du prochain étalonnage obligatoire des thermomètres |
| **🌡️ TEMPÉRATURES** | Le nombre d'alertes de température active dans les enceintes |
| **🐛 NUISIBLES** | Accès au plan de lutte antiparasitaire (IPM) |
| **🎓 E-LEARNING** | Accès aux modules de formation HACCP |

---

### Le tableau du jour — contrôle des pièges

Le tableau du jour s'affiche dans une vue à **3 colonnes** (Kanban). Il montre en temps réel l'état de toutes les tâches de contrôle des pièges : rongeurs et oiseaux.

<div class="taches-body" style="position:relative;height:auto;overflow:visible;border-radius:var(--radius);border:2px solid var(--color-secondary);max-width:700px;display:flex;flex-direction:column;">

<header class="taches-header" style="border-radius:var(--radius-sm) var(--radius-sm) 0 0;">
  <a class="taches-btn-retour" style="cursor:default;">← Tâches</a>
  <div class="taches-header-centre">
    <div class="taches-titre">TÂCHES HACCP</div>
    <div class="taches-date">Mercredi 14 mai 2026</div>
  </div>
  <div class="taches-horloge">09:15</div>
</header>

<div class="operateur-bar operateur-bar--actif" style="border-radius:0;">
  <span class="operateur-label">👤 Opérateur :</span>
  <div class="operateur-boutons">
    <button class="operateur-btn" type="button" style="cursor:default;">Marie</button>
    <button class="operateur-btn operateur-btn--actif" type="button" style="cursor:default;">Jean</button>
    <button class="operateur-btn" type="button" style="cursor:default;">Lucie</button>
  </div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr 1fr;border-top:1px solid #e8d9c4;">

  <div class="taches-colonne taches-colonne--retard" style="min-width:0;">
    <div class="taches-colonne-titre">
      <span class="taches-colonne-dot taches-colonne-dot--retard"></span>
      EN RETARD
      <span class="taches-colonne-nb">1</span>
    </div>
    <div class="taches-liste" style="overflow:visible;">
      <div class="tache-carte tache-carte--retard tache-carte--cliquable" style="cursor:default;">
        <div class="tache-carte-haut">
          <span class="tache-icone">🪤</span>
          <span class="tache-heure">08:00</span>
        </div>
        <div class="tache-libelle">Présence rongeurs sur pièges</div>
      </div>
    </div>
  </div>

  <div class="taches-colonne taches-colonne--afaire" style="min-width:0;">
    <div class="taches-colonne-titre">
      <span class="taches-colonne-dot taches-colonne-dot--afaire"></span>
      À FAIRE
      <span class="taches-colonne-nb">1</span>
    </div>
    <div class="taches-liste" style="overflow:visible;">
      <div class="tache-carte tache-carte--afaire tache-carte--cliquable" style="cursor:default;">
        <div class="tache-carte-haut">
          <span class="tache-icone">🪤</span>
          <span class="tache-heure">12:00</span>
        </div>
        <div class="tache-libelle">Nettoyage pièges oiseaux</div>
      </div>
    </div>
  </div>

  <div class="taches-colonne taches-colonne--fait" style="min-width:0;">
    <div class="taches-colonne-titre">
      <span class="taches-colonne-dot taches-colonne-dot--fait"></span>
      FAIT
      <span class="taches-colonne-nb">0</span>
    </div>
    <div class="taches-liste" style="overflow:visible;">
      <div class="taches-vide">Aucune validation aujourd'hui</div>
    </div>
  </div>

</div>
</div>

**Ce que veulent dire les colonnes :**

| Colonne | Couleur | Ce qu'elle contient |
|---|---|---|
| **EN RETARD** | Rouge | Tâches dont l'heure prévue est dépassée et qui n'ont pas encore été faites — à traiter en priorité |
| **À FAIRE** | Orange | Tâches planifiées pour aujourd'hui, pas encore faites, dans les délais |
| **FAIT** | Vert | Tâches validées aujourd'hui — lecture seule, rien à faire |

> La liste se met à jour automatiquement toutes les 60 secondes. Si un collègue valide une tâche sur une autre tablette, vous le verrez apparaître sans avoir à recharger la page.

---

### Valider une tâche — pas à pas

#### 1. Sélectionnez votre prénom

La barre en haut de l'écran affiche tous les prénoms du personnel. **Tapez le vôtre.**

- La barre passe du fond orange (personne sélectionné) au fond vert (vous êtes sélectionné).
- Si vous oubliez et que vous tapez une tâche, la barre clignote en orange pour attirer votre attention — pas de panique, tapez simplement votre prénom.

#### 2. Tapez la carte de la tâche à valider

Tapez n'importe quelle carte dans la colonne **EN RETARD** ou **À FAIRE**. Une fenêtre s'ouvre.

<div style="background:rgba(0,0,0,.45);border-radius:var(--radius);padding:1rem;max-width:560px;">
<div class="modal-boite" style="max-height:none;">

  <div class="modal-entete">
    <div class="modal-icone">🪤</div>
    <div style="flex:1;">
      <div class="modal-titre">Présence rongeurs sur pièges</div>
      <div class="modal-sous-titre">Heure cible : 08:00</div>
    </div>
    <button class="modal-fermer" type="button" style="cursor:default;">✕</button>
  </div>

  <div class="modal-form">

    <div class="modal-fieldset">
      <legend class="modal-fieldset-titre">Pièges à contrôler</legend>
      <label class="modal-checkbox-ligne" style="cursor:default;">
        <input type="checkbox" style="pointer-events:none;">
        <span>R1 — Entrée laboratoire &nbsp;— Rongeur présent</span>
      </label>
      <label class="modal-checkbox-ligne" style="cursor:default;">
        <input type="checkbox" style="pointer-events:none;">
        <span>R2 — Chambre froide — Rongeur présent</span>
      </label>
      <label class="modal-checkbox-ligne" style="cursor:default;">
        <input type="checkbox" style="pointer-events:none;">
        <span>R3 — Reserve sèche — Rongeur présent</span>
      </label>
    </div>

    <fieldset class="modal-fieldset">
      <legend class="modal-fieldset-titre">Conformité</legend>
      <div class="modal-conforme-choix">
        <label class="modal-conforme-label modal-conforme-label--oui" style="cursor:default;">
          <input type="radio" name="conforme-ex" style="pointer-events:none;">
          <span>✅ Conforme</span>
        </label>
        <label class="modal-conforme-label modal-conforme-label--non" style="cursor:default;">
          <input type="radio" name="conforme-ex" style="pointer-events:none;">
          <span>❌ Non conforme</span>
        </label>
      </div>
    </fieldset>

    <div class="modal-champ">
      <label class="modal-champ-label">Commentaire <span class="modal-optionnel">(optionnel)</span></label>
      <textarea class="modal-textarea" placeholder="Observation, action corrective…" style="pointer-events:none;"></textarea>
    </div>

    <div class="modal-actions">
      <button class="btn-outline" type="button" style="cursor:default;">Annuler</button>
      <button class="btn-valider" type="button" style="cursor:default;">Valider ✓</button>
    </div>

  </div>

</div>
</div>

#### 3. Cochez les pièges

Selon la tâche, vous voyez la liste de tous les pièges configurés :

**Tâche "Présence rongeurs sur pièges"** :
- Chaque piège est listé avec son identifiant et sa localisation.
- **Cochez uniquement les pièges où vous avez trouvé un rongeur.**
- Les pièges non cochés indiquent l'absence de rongeur — c'est normal.

**Tâche "Nettoyage pièges oiseaux"** :
- **Cochez chaque piège que vous avez nettoyé.**

#### 4. Choisissez la conformité

Tapez **✅ Conforme** ou **❌ Non conforme** selon l'état général constaté. Ce champ est **obligatoire**.

#### 5. Ajoutez un commentaire si nécessaire (optionnel)

Si vous avez trouvé quelque chose d'anormal, si vous avez dû faire une action particulière, ou si vous voulez laisser une note pour le prochain contrôle — écrivez-le ici.

#### 6. Tapez "Valider ✓"

Le bouton vert enregistre la tâche. La fenêtre se ferme, la carte passe dans la colonne **FAIT** et les compteurs se mettent à jour.

---

### Ce qui se passe si vous oubliez de sélectionner votre prénom

La barre opérateur **clignote en orange** pendant une seconde pour attirer votre attention. La fenêtre ne s'ouvre pas. Tapez votre prénom, puis retapez la tâche.

---

### Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Ce que ça veut dire | Que faire |
|---|---|---|
| Barre orange qui clignote | Aucun opérateur sélectionné | Tapez votre prénom dans la barre, puis retapez la tâche |
| *"Veuillez indiquer si la tâche est conforme ou non"* | Vous n'avez pas choisi Conforme / Non conforme | Tapez l'un des deux boutons radio |
| *"Aucun piège rongeur configuré"* | Aucun piège n'est enregistré dans l'administration | Contactez le responsable pour les configurer dans Admin |
| *"⚠ Connexion perdue"* dans les colonnes | La tablette ne peut plus joindre le serveur | Vérifiez que le Raspberry Pi est allumé et que le Wi-Fi fonctionne |
| Colonne EN RETARD avec plusieurs cartes | Des tâches n'ont pas été faites à l'heure | Traitez-les dans l'ordre — la plus ancienne en premier |

---

---

## Module 6 — Nettoyage & Désinfection

### À quoi ça sert ?

Ce module affiche le **Plan de Nettoyage et Désinfection (PND)** de la semaine sous forme d'un grand tableau. Chaque case représente une tâche de nettoyage pour un jour donné. Vous cochez les cases au fur et à mesure que les tâches sont faites — ou vous validez tout le nettoyage du jour en un seul geste.

Pour y accéder : tapez **✅ TÂCHES HACCP** sur l'écran d'accueil, puis la tuile **🧹 NETTOYAGE**.

---

### Ce que vous voyez en arrivant

<div class="nett-body" style="position:relative;height:auto;overflow:visible;border-radius:var(--radius);border:2px solid var(--color-secondary);max-width:100%;">

<header class="nett-bar">
  <a class="nett-retour" style="cursor:default;">← Tâches</a>
  <div class="nett-bar-date">Aujourd'hui : MERCREDI 14 MAI</div>
  <div class="nett-bar-actions">
    <button class="nett-btn-gerer" type="button" style="cursor:default;">⚙ Tâches</button>
    <a class="nett-btn-historique" style="cursor:default;">📋 Historique</a>
    <select class="nett-select" style="pointer-events:none;">
      <option>👤 Opérateur…</option>
      <option>Marie</option>
    </select>
    <button class="nett-btn-valider" type="button" style="cursor:default;">✅ VALIDER LE NETTOYAGE DU MERCREDI</button>
  </div>
</header>

<div class="nett-table-wrap" style="overflow:auto;max-height:220px;">
<table class="nett-table">
  <thead>
    <tr>
      <th class="nett-th-secteur">Secteur</th>
      <th class="nett-th-quoi">Quoi</th>
      <th class="nett-th-quand">Quand</th>
      <th class="nett-th-comment">Produit</th>
      <th class="nett-th-day">Lun</th>
      <th class="nett-th-day">Mar</th>
      <th class="nett-th-day nett-today-col">Mer</th>
      <th class="nett-th-day">Jeu</th>
      <th class="nett-th-day">Ven</th>
      <th class="nett-th-day">Sam</th>
      <th class="nett-th-day">Dim</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="nett-secteur-cell" rowspan="3">LABO</td>
      <td class="nett-quoi-cell">Sol / Siphon</td>
      <td class="nett-quand-cell">Quotidien</td>
      <td class="nett-comment-cell">KING FLASH</td>
      <td><span class="nett-check">✅</span><span class="nett-initial">M.</span></td>
      <td><span class="nett-check">✅</span><span class="nett-initial">J.</span></td>
      <td class="nett-today-col nett-day-cell" style="cursor:default;">—</td>
      <td class="nett-day-cell" style="cursor:default;">—</td>
      <td class="nett-day-cell" style="cursor:default;">—</td>
      <td class="nett-day-cell" style="cursor:default;">—</td>
      <td class="nett-day-cell" style="cursor:default;">—</td>
    </tr>
    <tr>
      <td class="nett-quoi-cell">Plans de travail</td>
      <td class="nett-quand-cell">Quotidien</td>
      <td class="nett-comment-cell">SURFA CLEAN</td>
      <td><span class="nett-check">✅</span><span class="nett-initial">M.</span></td>
      <td><span class="nett-check">✅</span><span class="nett-initial">J.</span></td>
      <td class="nett-today-col nett-day-cell" style="cursor:default;">—</td>
      <td class="nett-day-cell" style="cursor:default;">—</td>
      <td class="nett-day-cell" style="cursor:default;">—</td>
      <td class="nett-day-cell" style="cursor:default;">—</td>
      <td class="nett-day-cell" style="cursor:default;">—</td>
    </tr>
    <tr>
      <td class="nett-quoi-cell">Murs / Carrelage</td>
      <td class="nett-quand-cell nett-quand-cell--hebdo">Hebdo</td>
      <td class="nett-comment-cell">KING FLASH</td>
      <td>—</td>
      <td>—</td>
      <td class="nett-today-col nett-day-cell" style="cursor:default;">—</td>
      <td>—</td>
      <td>—</td>
      <td class="nett-day-cell" style="cursor:default;">—</td>
      <td>—</td>
    </tr>
    <tr class="nett-row-even">
      <td class="nett-secteur-cell" rowspan="2">FRIGO</td>
      <td class="nett-quoi-cell">Étagères intérieures</td>
      <td class="nett-quand-cell">Quotidien</td>
      <td class="nett-comment-cell">SURFA CLEAN</td>
      <td><span class="nett-check">✅</span><span class="nett-initial">L.</span></td>
      <td><span class="nett-check">✅</span><span class="nett-initial">M.</span></td>
      <td class="nett-today-col nett-day-cell" style="cursor:default;">—</td>
      <td>—</td>
      <td>—</td>
      <td>—</td>
      <td>—</td>
    </tr>
    <tr class="nett-row-even">
      <td class="nett-quoi-cell">Joint de porte</td>
      <td class="nett-quand-cell nett-quand-cell--hebdo">Hebdo</td>
      <td class="nett-comment-cell">SURFA CLEAN</td>
      <td>—</td><td>—</td>
      <td class="nett-today-col" style="">—</td>
      <td>—</td><td>—</td>
      <td>—</td><td>—</td>
    </tr>
  </tbody>
</table>
</div>

</div>

**Ce que veulent dire les colonnes du tableau :**

| Colonne | Ce qu'elle contient |
|---|---|
| **Secteur** | Le nom de la zone (écrit verticalement, en fond beige foncé) |
| **Quoi** | Le nom de la tâche de nettoyage |
| **Quand** | `Quotidien` = à faire tous les jours / `Hebdo` en brun = uniquement le samedi (grand nettoyage) |
| **Produit** | Le produit à utiliser (fond orange pâle) |
| **Lun à Dim** | Une colonne par jour — la case se coche quand la tâche est faite |

La **colonne du jour** est surlignée en jaune (en-tête orange). C'est là que vous validez.

**Ce que veut dire ✅ M. dans une case :** la tâche a été validée ce jour-là par "Marie" (initiale M.).

---

### Comment valider le nettoyage du jour

#### Méthode 1 — Tout valider en un seul geste (recommandé)

C'est la méthode la plus rapide pour valider tout le nettoyage du jour en même temps.

1. **Sélectionnez votre prénom** dans le menu déroulant **`👤 Opérateur…`** en haut à droite.
2. Tapez le bouton vert **`✅ VALIDER LE NETTOYAGE DU [JOUR]`**.
3. Une confirmation s'affiche à l'écran :

<div style="background:var(--color-card);border-radius:var(--radius);border:2px solid var(--color-ok);padding:1.25rem;max-width:500px;">
  <div style="font-weight:700;font-size:var(--text-base);margin-bottom:.75rem;">Confirmer la validation</div>
  <div style="font-size:var(--text-sm);color:#4b5563;line-height:1.6;margin-bottom:1rem;">"En validant, je confirme sur l'honneur avoir effectué l'intégralité des tâches de nettoyage et de désinfection listées pour aujourd'hui, en respectant le Plan de Nettoyage."</div>
  <div style="display:flex;gap:.75rem;">
    <button class="nett-btn-valider" type="button" style="cursor:default;flex:1;">✅ Confirmer</button>
    <button class="nett-btn-annuler" type="button" style="cursor:default;">Annuler</button>
  </div>
</div>

4. Tapez **Confirmer**. Toutes les cases du jour se cochent avec votre initiale. Un message de confirmation apparaît brièvement en haut de l'écran.

> **Le bouton change d'apparence selon l'avancement :**

<div style="display:flex;flex-wrap:wrap;gap:.75rem;margin:.5rem 0;">
  <button class="nett-btn-valider" type="button" style="cursor:default;">✅ VALIDER LE NETTOYAGE DU MERCREDI</button>
  <button class="nett-btn-valider" type="button" style="cursor:default;">✅ VALIDER LE RESTE (3/8)</button>
  <button class="nett-btn-valider nett-btn-valider--done" type="button" style="cursor:default;">✔ VALIDÉ — 8 tâche(s)</button>
</div>

- **`✅ VALIDER LE NETTOYAGE DU [JOUR]`** : aucune tâche validée pour l'instant.
- **`✅ VALIDER LE RESTE (3/8)`** : vous avez déjà validé certaines tâches, il en reste 3 sur 8.
- **`✔ VALIDÉ — 8 tâche(s)`** (vert foncé) : tout le nettoyage du jour est fait.

#### Méthode 2 — Cocher case par case

Si vous voulez cocher tâche par tâche (par exemple, certaines zones ne sont pas encore faites), tapez directement sur la **case** dans la colonne du jour. La case affiche immédiatement votre initiale.

> Pour cocher une case individuelle, votre prénom doit être sélectionné dans le menu.

#### Méthode 3 — Valider une colonne entière en tapant sur l'en-tête

Tapez directement sur le nom d'un jour en haut du tableau (`Lun`, `Mar`, `Mer`…) pour cocher toutes les tâches **quotidiennes** de ce jour. Utile pour rattraper un jour passé oublié.

> Les tâches **Hebdo** (grand nettoyage) ne sont **jamais** incluses dans cette validation rapide par colonne — elles doivent être cochées individuellement.

#### Pour décocher une case

Tapez sur une case déjà cochée pour la décocher. Vous n'avez pas besoin d'être sélectionné comme opérateur pour décocher.

---

### Le grand nettoyage du samedi

Les tâches marquées **Hebdo** (en brun dans la colonne "Quand") ne doivent être faites **que le samedi**. Ce sont les nettoyages en profondeur : murs, joints de portes, hottes, etc.

- **Du lundi au vendredi** : seules les tâches Quotidiennes apparaissent dans le bouton de validation globale.
- **Le samedi** : toutes les tâches (Quotidiennes + Hebdomadaires) sont incluses dans la validation globale.
- N'importe quel autre jour, vous pouvez quand même cocher individuellement une case Hebdo si nécessaire.

---

### Consulter l'historique des nettoyages

Tapez **`📋 Historique`** dans la barre du haut. L'historique s'affiche par arborescence repliable :

```
▼ 2026
  ▼ Mai
    ▼ Semaine 20
      🧹 Mercredi 14  Marie, Jean  [8 tâches]
      🧹 Mardi 13     Marie        [8 tâches]
      🧹 Lundi 12     Lucie        [8 tâches]
```

Chaque ligne indique la date, les prénoms des opérateurs ayant validé ce jour-là, et le nombre de tâches enregistrées.

---

### Gérer les tâches du plan — réservé au responsable

Le bouton **`⚙ Tâches`** ouvre une fenêtre permettant d'ajouter, modifier ou supprimer des tâches du plan de nettoyage.

<div style="background:var(--color-card);border-radius:var(--radius);border:2px solid var(--color-secondary);overflow:hidden;max-width:600px;">
  <div class="nett-modal-header">
    <h2 class="nett-modal-title">⚙ Gérer les tâches de nettoyage</h2>
    <button class="nett-modal-close" type="button" style="cursor:default;">✕</button>
  </div>
  <div style="padding:.75rem 1rem;border-bottom:1px solid rgba(61,32,8,.15);">
    <div class="nett-zone-titre">LABO</div>
    <div class="nett-tache-row">
      <span class="nett-tache-nom">Sol / Siphon</span>
      <span class="nett-tache-freq">Quotidien</span>
      <span class="nett-tache-produit">KING FLASH</span>
      <button class="nett-btn-edit" type="button" style="cursor:default;">✏ Modifier</button>
      <button class="nett-btn-del" type="button" style="cursor:default;">🗑</button>
    </div>
    <div class="nett-tache-row">
      <span class="nett-tache-nom">Murs / Carrelage</span>
      <span class="nett-tache-freq">Hebdomadaire</span>
      <span class="nett-tache-produit">KING FLASH</span>
      <button class="nett-btn-edit" type="button" style="cursor:default;">✏ Modifier</button>
      <button class="nett-btn-del" type="button" style="cursor:default;">🗑</button>
    </div>
  </div>
  <div class="nett-modal-form">
    <h3 class="nett-modal-form-title">+ Ajouter une tâche</h3>
    <div class="nett-form-grid">
      <label>Zone<input class="nett-form-input" type="text" placeholder="ex : CUISINE" style="pointer-events:none;"></label>
      <label>Tâche<input class="nett-form-input" type="text" placeholder="ex : SOL / SIPHON" style="pointer-events:none;"></label>
      <label>Fréquence<select class="nett-form-input" style="pointer-events:none;"><option>Quotidien</option><option>Hebdomadaire</option></select></label>
      <label>Produit<input class="nett-form-input" type="text" placeholder="ex : KING FLASH GERM" style="pointer-events:none;"></label>
    </div>
    <div class="nett-form-actions">
      <button class="nett-btn-sauver" type="button" style="cursor:default;">Enregistrer</button>
    </div>
  </div>
</div>

**Pour ajouter une tâche :**
1. Remplissez les 4 champs : **Zone** (ex. `CUISINE`), **Tâche** (ex. `SOL / SIPHON`), **Fréquence** (Quotidien ou Hebdomadaire), **Produit** (ex. `KING FLASH GERM`).
2. Tapez **Enregistrer**. La tâche apparaît dans le tableau.

**Pour modifier** : tapez **✏ Modifier** sur la ligne de la tâche — le formulaire se pré-remplit. Modifiez et tapez **Enregistrer**.

**Pour supprimer** : tapez **🗑** sur la ligne. Une confirmation apparaît. La suppression est définitive, mais l'historique des validations passées est conservé.

---

### Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Ce que ça veut dire | Que faire |
|---|---|---|
| *"Sélectionnez votre nom avant de valider"* | Aucun opérateur sélectionné dans le menu | Choisissez votre prénom dans le menu `👤 Opérateur…` |
| *"Aucune tâche applicable aujourd'hui"* | Aucune tâche quotidienne n'est configurée | Vérifiez que des tâches existent dans ⚙ Tâches |
| *"Zone et nom de tâche obligatoires"* | Champs Zone ou Tâche vides dans le formulaire | Remplissez les deux champs avant d'enregistrer |
| Cases qui se vident après la validation | Erreur de connexion au serveur | Vérifiez que le Raspberry Pi est allumé et revalidez |

---

---

## Module 7 — Lutte contre les Nuisibles (IPM)

### À quoi ça sert ?

Ce module enregistre semaine par semaine le résultat du contrôle de tous les **pièges antiparasitaires** du laboratoire : rongeurs, insectes volants (mouches, guêpes…), insectes rampants (cafards, fourmis…) et oiseaux. Il y a **15 pièges par espèce**, sur **52 semaines**, soit un registre annuel complet conforme au plan IPM.

Pour y accéder : tapez **✅ TÂCHES HACCP** sur l'écran d'accueil, puis la tuile **🐛 NUISIBLES**.

---

### Ce que vous voyez en arrivant

<div class="nu-body" style="position:relative;height:auto;overflow:visible;border-radius:var(--radius);border:2px solid var(--color-secondary);max-width:100%;">

<header class="nu-bar" style="position:relative;border-radius:var(--radius-sm) var(--radius-sm) 0 0;">
  <a class="nu-retour" style="cursor:default;">← Tâches</a>
  <div class="nu-bar-titre">🐛 Lutte contre Nuisibles</div>
  <select class="nu-annee-select" style="pointer-events:none;">
    <option>2026</option>
    <option>2025</option>
  </select>
</header>

<nav class="nu-tabs">
  <button class="nu-tab actif" type="button" style="cursor:default;">🐀 Rongeurs</button>
  <button class="nu-tab" type="button" style="cursor:default;">🪰 Ins. Volants</button>
  <button class="nu-tab" type="button" style="cursor:default;">🪳 Ins. Rampants</button>
  <button class="nu-tab" type="button" style="cursor:default;">🐦 Oiseaux</button>
</nav>

<div class="nu-info-wrap">
  <button class="nu-info-toggle" type="button" style="cursor:default;">
    ℹ️ Méthodes &amp; Fréquences
    <span class="nu-info-chev">▼</span>
  </button>
</div>

<div class="nu-table-wrap" style="max-height:160px;overflow:auto;">
<table class="nu-table">
  <thead>
    <tr>
      <th>Sem</th>
      <th class="nu-th-piege">P1</th>
      <th class="nu-th-piege">P2</th>
      <th class="nu-th-piege">P3</th>
      <th class="nu-th-piege">P4</th>
      <th class="nu-th-piege">P5</th>
      <th class="nu-th-piege">P6</th>
      <th class="nu-th-piege">P7</th>
      <th class="nu-th-piege">P8</th>
      <th class="nu-th-piege">P9</th>
      <th class="nu-th-piege">P10</th>
      <th class="nu-th-piege">P11</th>
      <th class="nu-th-piege">P12</th>
      <th class="nu-th-piege">P13</th>
      <th class="nu-th-piege">P14</th>
      <th class="nu-th-piege">P15</th>
      <th class="nu-th-visa">VISA</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="nu-td-sem">S18</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-visa">Marie</td>
    </tr>
    <tr class="nu-tr--today">
      <td class="nu-td-sem">S19</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--O">O</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-piege nu-td-piege--N">N</td>
      <td class="nu-td-visa">Jean</td>
    </tr>
    <tr>
      <td class="nu-td-sem">S20</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-piege nu-td-piege--vide">·</td>
      <td class="nu-td-visa"></td>
    </tr>
  </tbody>
</table>
</div>

</div>

**Ce que veulent dire les colonnes et les couleurs :**

| Ce que vous voyez | Ce que ça veut dire |
|---|---|
| **Sem** | Numéro de semaine (S1 à S52) |
| **P1 à P15** | Résultat du contrôle de chaque piège |
| <span class="nu-badge-n" style="padding:2px 8px;">N</span> **vert** | Piège **négatif** — rien dans le piège, tout va bien |
| <span class="nu-badge-o" style="padding:2px 8px;">O</span> **rouge** | Piège **occupé** — présence détectée, à signaler |
| **·** gris clair | Piège **non encore vérifié** cette semaine |
| **VISA** | Prénom de l'opérateur qui a fait le contrôle |
| Ligne surlignée en orange | **Semaine en cours** — la page défile automatiquement dessus à l'ouverture |

Les 4 **onglets** en haut permettent de basculer entre les espèces : 🐀 **Rongeurs** / 🪰 **Ins. Volants** / 🪳 **Ins. Rampants** / 🐦 **Oiseaux**. Chaque onglet a son propre tableau indépendant.

---

### Méthodes et fréquences de contrôle

Tapez **`ℹ️ Méthodes & Fréquences`** pour afficher le rappel des protocoles. Les voici résumés :

| Espèce | Type de piège | À quelle fréquence vérifier |
|---|---|---|
| 🐀 **Rongeurs** | Plaques de glue + rodenticide en boîte sécurisée | Pièges à glue : **chaque semaine** — Rodenticides : 1 fois par mois |
| 🪰 **Insectes volants** | DEIV (glu en zones alimentaires, UV en zones non alimentaires) | Plaque glu : **1 fois/mois** (avril–sept.) ou tous les 2 mois (oct.–mars) — Tubes UV : 1 fois par an |
| 🪳 **Insectes rampants** | Pièges à phéromones + gel en boîte sécurisée | Pièges à glue : **chaque semaine** — Remplacement total : 1 fois tous les 3 mois |
| 🐦 **Oiseaux** | Pics anti-pigeons + filets de protection | Inspection : **chaque semaine** — Nettoyage immédiat si fientes détectées |

---

### Saisir le contrôle d'une semaine — méthode simple

1. Tapez l'**onglet** de l'espèce que vous venez de contrôler (ex. : 🐀 Rongeurs).
2. Tapez la **ligne de la semaine** dans le tableau — la fenêtre de saisie s'ouvre par le bas de l'écran.

<div style="background:rgba(0,0,0,.35);padding:1rem;border-radius:var(--radius);max-width:560px;">
<div class="nu-modal-panel" style="position:relative;border-radius:var(--radius);max-height:none;">

  <div class="nu-modal-entete">
    <div class="nu-modal-titre">🐀 Rongeurs — Semaine 20 / 2026 ⚡</div>
    <button class="nu-modal-fermer" type="button" style="cursor:default;">✕</button>
  </div>

  <div class="nu-quick-actions" style="display:flex;gap:.5rem;flex-wrap:wrap;">
    <button class="nu-btn-quick nu-btn-quick--n" type="button" style="cursor:default;background:rgba(45,125,70,.15);border:2px solid #2D7D46;color:#2D7D46;border-radius:8px;padding:.45rem .85rem;font-weight:700;font-size:.82rem;">✗ Tout N (RAS)</button>
    <button class="nu-btn-quick nu-btn-quick--o" type="button" style="cursor:default;background:rgba(201,48,48,.12);border:2px solid #C93030;color:#C93030;border-radius:8px;padding:.45rem .85rem;font-weight:700;font-size:.82rem;">✓ Tout O</button>
    <button class="nu-btn-quick nu-btn-quick--vide" type="button" style="cursor:default;background:#F0E8DC;border:2px solid #DDD;color:#888;border-radius:8px;padding:.45rem .85rem;font-weight:700;font-size:.82rem;">· Vider</button>
  </div>

  <div class="nu-piege-grid">
    <button class="nu-piege-btn nu-piege-btn--N" type="button" style="cursor:default;"><span class="nu-piege-num">P1</span><span class="nu-piege-etat">N</span></button>
    <button class="nu-piege-btn nu-piege-btn--N" type="button" style="cursor:default;"><span class="nu-piege-num">P2</span><span class="nu-piege-etat">N</span></button>
    <button class="nu-piege-btn nu-piege-btn--O" type="button" style="cursor:default;"><span class="nu-piege-num">P3</span><span class="nu-piege-etat">O</span></button>
    <button class="nu-piege-btn" type="button" style="cursor:default;"><span class="nu-piege-num">P4</span><span class="nu-piege-etat">·</span></button>
    <button class="nu-piege-btn nu-piege-btn--N" type="button" style="cursor:default;"><span class="nu-piege-num">P5</span><span class="nu-piege-etat">N</span></button>
    <button class="nu-piege-btn nu-piege-btn--N" type="button" style="cursor:default;"><span class="nu-piege-num">P6</span><span class="nu-piege-etat">N</span></button>
    <button class="nu-piege-btn nu-piege-btn--N" type="button" style="cursor:default;"><span class="nu-piege-num">P7</span><span class="nu-piege-etat">N</span></button>
    <button class="nu-piege-btn nu-piege-btn--N" type="button" style="cursor:default;"><span class="nu-piege-num">P8</span><span class="nu-piege-etat">N</span></button>
    <button class="nu-piege-btn nu-piege-btn--N" type="button" style="cursor:default;"><span class="nu-piege-num">P9</span><span class="nu-piege-etat">N</span></button>
    <button class="nu-piege-btn nu-piege-btn--N" type="button" style="cursor:default;"><span class="nu-piege-num">P10</span><span class="nu-piege-etat">N</span></button>
    <button class="nu-piege-btn nu-piege-btn--N" type="button" style="cursor:default;"><span class="nu-piege-num">P11</span><span class="nu-piege-etat">N</span></button>
    <button class="nu-piege-btn nu-piege-btn--N" type="button" style="cursor:default;"><span class="nu-piege-num">P12</span><span class="nu-piege-etat">N</span></button>
    <button class="nu-piege-btn nu-piege-btn--N" type="button" style="cursor:default;"><span class="nu-piege-num">P13</span><span class="nu-piege-etat">N</span></button>
    <button class="nu-piege-btn nu-piege-btn--N" type="button" style="cursor:default;"><span class="nu-piege-num">P14</span><span class="nu-piege-etat">N</span></button>
    <button class="nu-piege-btn nu-piege-btn--N" type="button" style="cursor:default;"><span class="nu-piege-num">P15</span><span class="nu-piege-etat">N</span></button>
  </div>

  <div class="nu-modal-visa">
    <label>Visa (opérateur)</label>
    <select class="nu-visa-select" style="pointer-events:none;">
      <option>Marie</option>
    </select>
  </div>

  <div class="nu-modal-actions">
    <button class="nu-btn-annuler" type="button" style="cursor:default;">Annuler</button>
    <button class="nu-btn-sauvegarder" type="button" style="cursor:default;">✅ Enregistrer</button>
  </div>

</div>
</div>

3. **Tapez chaque bouton de piège** (P1 à P15) pour faire défiler son état à chaque tap :

<div style="display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;padding:.75rem;background:var(--color-card);border-radius:var(--radius);border:1px solid var(--color-secondary);margin:.5rem 0;">
  <button class="nu-piege-btn" style="cursor:default;"><span class="nu-piege-num">·</span><span class="nu-piege-etat">·</span></button>
  <span style="font-size:1.5rem;">→</span>
  <button class="nu-piege-btn nu-piege-btn--N" style="cursor:default;"><span class="nu-piege-num">N</span><span class="nu-piege-etat">N</span></button>
  <span style="font-size:1.5rem;">→</span>
  <button class="nu-piege-btn nu-piege-btn--O" style="cursor:default;"><span class="nu-piege-num">O</span><span class="nu-piege-etat">O</span></button>
  <span style="font-size:1.5rem;">→</span>
  <button class="nu-piege-btn" style="cursor:default;"><span class="nu-piege-num">·</span><span class="nu-piege-etat">·</span></button>
  <span style="color:#6b7280;font-size:var(--text-sm);">→ et ainsi de suite…</span>
</div>

| État | Couleur | Signification |
|---|---|---|
| **·** gris | Non vérifié | Piège pas encore inspecté |
| **N** vert | Négatif | Piège vide — rien à signaler |
| **O** rouge | Occupé | Présence détectée — à consigner et à traiter |

4. **Action rapide disponible** : si tous les pièges sont vides cette semaine (cas habituel), tapez simplement **`✗ Tout N (RAS)`** pour mettre tous les 15 pièges sur N en une seule fois. Si vous avez détecté une présence sur certains, corrigez ensuite les pièges concernés individuellement.

5. **Sélectionnez votre prénom** dans le menu Visa.

6. Tapez **`✅ Enregistrer`**.

> La fenêtre se ferme et la ligne de la semaine se met à jour dans le tableau. Votre prénom apparaît dans la colonne VISA.

---

### Saisie rapide — 4 espèces en une seule opération

Le bouton orange **⚡ Saisie rapide** (en bas à droite de l'écran) ouvre une fenêtre qui permet de remplir **les 4 espèces en même temps** pour la semaine en cours.

<div style="display:flex;justify-content:flex-end;margin:.5rem 0;">
  <button class="nu-fab" type="button" style="position:relative;bottom:auto;right:auto;cursor:default;">
    <span>⚡ Saisie rapide</span>
    <span class="nu-fab-sub">S20 · 4 espèces · 15 pièges</span>
  </button>
</div>

**Comment utiliser la saisie rapide :**

1. Tapez **⚡ Saisie rapide**.
2. En haut de la fenêtre, naviguez avec les boutons **`‹`** et **`›`** si vous voulez saisir une autre semaine que la semaine courante.
3. Le bloc **"Action globale"** permet d'appliquer un résultat à plusieurs pièges et plusieurs espèces en une fois :
   - Choisissez jusqu'à quel piège appliquer (stepper P1 à P15 avec les boutons − et +).
   - Choisissez l'espèce : Toutes / 🐀 / 🪰 / 🪳 / 🐦.
   - Tapez **`✗ N`** (rien dans les pièges) ou **`✓ O`** (présence détectée).
4. Affinez espèce par espèce si nécessaire dans les 4 sections dédiées.
5. Sélectionnez votre **prénom** (Visa partagé — s'applique à toutes les espèces).
6. Tapez **`✅ Enregistrer tout`**.

> Si une espèce n'a aucun piège renseigné (tous sur ·), elle n'est pas enregistrée et ses données précédentes restent intactes.

---

### Changer d'année

Le menu déroulant en haut à droite affiche l'année courante et les 4 années précédentes. Changez l'année pour consulter ou saisir un historique passé.

---

### Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Ce que ça veut dire | Que faire |
|---|---|---|
| *"Erreur de chargement : [détail]"* | Le serveur ne répond pas | Vérifiez que le Raspberry Pi est allumé |
| *"Aucune donnée à enregistrer"* | Tous les pièges sont sur · en saisie rapide | Renseignez au moins un piège avant d'enregistrer |
| Toast rouge *"Erreur : [espèce]"* | Échec d'enregistrement pour cette espèce | Retapez ✅ Enregistrer tout — les espèces réussies ne sont pas renvoyées |

---

---

---

# Module 8 — Étalonnage des Thermomètres (EET01)

<div style="background:rgba(212,165,116,.15);border-left:4px solid #D4A574;border-radius:0 8px 8px 0;padding:.65rem 1rem;font-size:.9rem;line-height:1.5;color:#3D2008;margin-bottom:1.2rem">
<strong style="color:#6B3A1F">Accès :</strong> Hub principal → <strong>✅ TÂCHES HACCP</strong> → tuile <strong>🌡️ ÉTALONNAGE</strong>
</div>

L'étalonnage consiste à vérifier, tous les **3 mois environ**, que nos thermomètres mesurent correctement la température. Cette opération se fait en **deux phases** l'une après l'autre :

1. **Phase 1** — On vérifie le thermomètre de référence dans un bain d'eau glacée.
2. **Phase 2** — On compare chaque sonde des chambres froides avec ce même thermomètre.

> **Règle générale : pas de double-clic. On tape une seule fois et on attend.**

---

## Préparer le bain d'eau glacée (avant d'ouvrir la tablette)

Avant toute saisie sur la tablette, préparez physiquement le bain :

1. Remplir un récipient d'**eau + glaçons** (au moins la moitié de glaçons).
2. Brasser le mélange pendant 30 secondes pour homogénéiser la température.
3. Plonger le **thermomètre de référence** dans le bain, attendre que la lecture se stabilise (30 à 60 secondes).
4. Mémoriser (ou noter) la valeur affichée sur le thermomètre.
5. Ouvrir la tablette et remplir le formulaire.

---

## Phase 1 — Vérification du thermomètre de référence

### L'écran Phase 1

<div style="background:#FFFDF7;border-radius:12px;padding:1.1rem 1.25rem;border:1.5px solid #D4A574;margin-bottom:1rem">
  <div style="background:#3D2008;color:#F5ECD7;padding:.4rem 1rem;border-radius:8px;display:inline-block;font-size:.8rem;font-weight:700;margin-bottom:.75rem">ÉTALONNAGE THERMOMÈTRES &nbsp;·&nbsp; <span style="opacity:.7">Réf. EET01 — Trimestriel</span></div>
  <div style="background:rgba(212,165,116,.15);border-left:4px solid #D4A574;border-radius:0 8px 8px 0;padding:.55rem .9rem;font-size:.85rem;margin-bottom:.9rem">
    <strong style="color:#6B3A1F">Règle de conformité :</strong> 0°C ± 0,5°C (de −0,5°C à +0,5°C) — Hors intervalle : remplacer le thermomètre. Dans tous les cas : <strong>nettoyer la sonde et la ranger.</strong>
  </div>
  <div style="font-size:.85rem;font-weight:700;color:#3D2008;margin-bottom:.5rem">📋 Nouvel enregistrement</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:.6rem .8rem;font-size:.82rem">
    <div><div style="color:#6B3A1F;font-weight:600;font-size:.75rem;margin-bottom:.2rem">Date *</div><div style="border:1.5px solid #D4A574;border-radius:8px;padding:.4rem .6rem;background:#F5ECD7">2026-05-14</div></div>
    <div><div style="color:#6B3A1F;font-weight:600;font-size:.75rem;margin-bottom:.2rem">Opérateur *</div><div style="border:1.5px solid #D4A574;border-radius:8px;padding:.4rem .6rem;background:#F5ECD7">Sélectionner…</div></div>
    <div><div style="color:#6B3A1F;font-weight:600;font-size:.75rem;margin-bottom:.2rem">Thermomètre de référence *</div><div style="border:1.5px solid #D4A574;border-radius:8px;padding:.4rem .6rem;background:#F5ECD7">Sélectionner…</div></div>
    <div><div style="color:#6B3A1F;font-weight:600;font-size:.75rem;margin-bottom:.2rem">Température mesurée (°C) *</div><div style="border:1.5px solid #D4A574;border-radius:8px;padding:.4rem .6rem;background:#F5ECD7">Ex : 0,2</div></div>
    <div><div style="color:#6B3A1F;font-weight:600;font-size:.75rem;margin-bottom:.2rem">Résultat</div><div style="display:inline-flex;align-items:center;gap:.4rem;padding:.35rem .8rem;border-radius:20px;font-size:.75rem;font-weight:700;background:rgba(0,0,0,.05);color:#888;border:1.5px solid #aaa">— Saisir une température</div></div>
  </div>
  <div style="margin-top:.6rem;font-size:.82rem"><div style="color:#6B3A1F;font-weight:600;font-size:.75rem;margin-bottom:.3rem">Action corrective *</div><div style="display:flex;gap:.5rem;flex-wrap:wrap"><span style="padding:.4rem .8rem;border:2px solid #D4A574;border-radius:20px;font-size:.78rem;font-weight:600;opacity:.4">✅ Conforme</span><span style="padding:.4rem .8rem;border:2px solid #D4A574;border-radius:20px;font-size:.78rem;font-weight:600;opacity:.4">🔧 Calibrage</span><span style="padding:.4rem .8rem;border:2px solid #D4A574;border-radius:20px;font-size:.78rem;font-weight:600;opacity:.4">🔄 Remplacé</span></div></div>
  <div style="margin-top:.7rem"><button style="background:#3D2008;color:#F5ECD7;border:none;border-radius:8px;padding:.7rem;font-weight:700;font-size:.85rem;width:100%">Enregistrer ✓</button></div>
</div>

---

### Remplir le formulaire étape par étape

**1 — Date**
La date du jour est pré-remplie automatiquement. Ne la changez que si vous saisissez un étalonnage qui a eu lieu un autre jour.

**2 — Opérateur**
Tapez sur le menu déroulant et sélectionnez votre prénom.

**3 — Thermomètre de référence**
Tapez sur le menu déroulant et choisissez le thermomètre que vous avez utilisé. Le nom et le numéro de série sont affichés.

> Si le menu affiche **⚠ Aucun thermomètre configuré**, contactez le responsable : il faut enregistrer le thermomètre dans l'administration.

**4 — Température mesurée**
Tapez la valeur lue sur votre thermomètre (ex. : `0,2` ou `-0,3`). Utilisez la virgule comme séparateur décimal.

Dès que vous avez tapé une valeur, le **badge Résultat** se met à jour immédiatement :

<div style="display:flex;flex-direction:column;gap:.5rem;margin:.5rem 0 .8rem">
  <div style="display:inline-flex;align-items:center;gap:.4rem;padding:.35rem .8rem;border-radius:20px;font-size:.82rem;font-weight:700;background:rgba(45,125,70,.12);color:#2D7D46;border:1.5px solid #2D7D46;width:fit-content">✅ Conforme — 0,2°C dans [−0,5 ; +0,5]</div>
  <div style="display:inline-flex;align-items:center;gap:.4rem;padding:.35rem .8rem;border-radius:20px;font-size:.82rem;font-weight:700;background:rgba(201,48,48,.10);color:#C93030;border:1.5px solid #C93030;width:fit-content">❌ Non conforme — 1,2°C hors tolérance</div>
</div>

**5 — Action corrective**
Les boutons d'action se déverrouillent automatiquement selon le résultat :

| Résultat | Boutons disponibles | Ce qui s'active automatiquement |
|---|---|---|
| Conforme (entre −0,5 et +0,5°C) | **✅ Conforme** seulement | ✅ Conforme — sélectionné d'office |
| Non conforme (hors tolérance) | **🔧 Calibrage** et **🔄 Remplacé** | Rien — vous choisissez |
| Rien de saisi | Tous grisés | — |

Tapez sur l'action souhaitée : le bouton prend un fond sombre pour indiquer qu'il est sélectionné.

**6 — Commentaire** (facultatif)
Notez ici toute observation utile : numéro de série du nouveau thermomètre, marque, remarque particulière…

**7 — Enregistrer ✓**
Tapez le bouton **`Enregistrer ✓`** en bas du formulaire.

---

### Ce qui se passe après l'enregistrement

**Si vous avez sélectionné ✅ Conforme ou 🔄 Remplacé :**
La page bascule automatiquement vers la **Phase 2** (comparaison des sondes). Continuez sans rien faire.

**Si vous avez sélectionné 🔧 Calibrage :**
Un message vert s'affiche :
<div style="padding:.6rem 1rem;border-radius:8px;background:rgba(45,125,70,.10);color:#2D7D46;border:1px solid #2D7D46;font-size:.85rem;font-weight:600;margin:.5rem 0">🔧 Calibrage enregistré. Effectuez le calibrage puis créez un nouvel enregistrement pour passer aux comparaisons.</div>

Le formulaire se vide. Vous devez d'abord **calibrer physiquement le thermomètre**, puis revenir faire un nouvel enregistrement Phase 1. Quand ce second enregistrement obtient "Conforme", vous passez alors à la Phase 2.

---

## Phase 2 — Comparaison des sondes des chambres froides

### L'écran Phase 2

<div style="background:#FFFDF7;border-radius:12px;padding:1.1rem 1.25rem;border:1.5px solid #D4A574;margin-bottom:1rem">
  <div style="background:#3D2008;color:#F5ECD7;padding:.4rem 1rem;border-radius:8px;display:inline-block;font-size:.8rem;font-weight:700;margin-bottom:.75rem">← Étape 1 &nbsp;&nbsp;&nbsp; COMPARAISON SONDES</div>
  <div style="background:rgba(45,125,70,.06);border-left:4px solid #2D7D46;border-radius:0 8px 8px 0;padding:.55rem .9rem;font-size:.82rem;margin-bottom:.75rem">
    <div style="font-size:.8rem;font-weight:700;color:#2D7D46;margin-bottom:.2rem">✅ Étape 1 validée</div>
    <div style="color:#3D2008;opacity:.85">Thermomètre Pro — N°SN001 · 0,2°C · Conforme · Émile</div>
  </div>
  <div style="font-size:.8rem;color:#3D2008;margin-bottom:.75rem;opacity:.85"><em>Plongez le thermomètre de référence dans chaque enceinte et saisissez sa lecture. La sonde connectée est relevée automatiquement. Conformité : écart ≤ ±0,5°C.</em></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem">
    <div style="background:#FFFDF7;border-radius:12px;padding:.85rem 1rem;border:2px solid #D4A574">
      <div style="font-size:.85rem;font-weight:800;color:#6B3A1F;margin-bottom:.5rem">CHAMBRE FROIDE 1</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;align-items:end">
        <div><div style="font-size:.65rem;font-weight:600;color:#6B3A1F;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.2rem">Sonde connectée</div><div style="font-size:1.1rem;font-weight:700;color:#3D2008">2,1 °C</div></div>
        <div><div style="font-size:.65rem;font-weight:600;color:#6B3A1F;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.2rem">Thermo référence</div><div style="border:1.5px solid #D4A574;border-radius:8px;padding:.35rem .5rem;background:#F5ECD7;font-size:.9rem;font-weight:700;text-align:center">2,4</div></div>
      </div>
      <div style="margin-top:.5rem;display:inline-flex;align-items:center;gap:.3rem;padding:.25rem .65rem;border-radius:20px;font-size:.75rem;font-weight:700;background:rgba(45,125,70,.12);color:#2D7D46;border:1.5px solid #2D7D46">✅ Conforme — écart : +0,3°C dans [−0,5 ; +0,5]</div>
    </div>
    <div style="background:#FFFDF7;border-radius:12px;padding:.85rem 1rem;border:2px solid #D4A574">
      <div style="font-size:.85rem;font-weight:800;color:#6B3A1F;margin-bottom:.5rem">VITRINE BOUCHERIE</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;align-items:end">
        <div><div style="font-size:.65rem;font-weight:600;color:#6B3A1F;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.2rem">Sonde connectée</div><div style="font-size:1.1rem;font-weight:700;color:#3D2008">4,0 °C</div></div>
        <div><div style="font-size:.65rem;font-weight:600;color:#6B3A1F;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.2rem">Thermo référence</div><div style="border:1.5px solid #D4A574;border-radius:8px;padding:.35rem .5rem;background:#F5ECD7;font-size:.9rem;font-weight:700;text-align:center"></div></div>
      </div>
      <div style="margin-top:.5rem;display:inline-flex;align-items:center;gap:.3rem;padding:.25rem .65rem;border-radius:20px;font-size:.75rem;font-weight:700;background:rgba(0,0,0,.05);color:#888;border:1.5px solid #aaa">— Saisir la température de référence</div>
    </div>
  </div>
  <div style="margin-top:.75rem"><button style="background:#3D2008;color:#F5ECD7;border:none;border-radius:8px;padding:.7rem;font-weight:700;font-size:.85rem;width:100%;opacity:.5">Enregistrer les comparaisons ✓</button></div>
</div>

---

### Remplir la Phase 2 étape par étape

Pour **chaque enceinte** (chambre froide, vitrine, armoire…), répétez les mêmes gestes :

1. Plongez le thermomètre de référence dans l'enceinte (ou dans un produit représentatif).
2. Attendez que la lecture se stabilise.
3. Tapez la valeur dans le champ **"Thermo référence"** de la carte correspondante.
4. Le **badge d'écart** s'affiche immédiatement :

<div style="display:flex;flex-direction:column;gap:.4rem;margin:.4rem 0 .8rem">
  <div style="display:inline-flex;align-items:center;gap:.4rem;padding:.3rem .7rem;border-radius:20px;font-size:.8rem;font-weight:700;background:rgba(45,125,70,.12);color:#2D7D46;border:1.5px solid #2D7D46;width:fit-content">✅ Conforme — écart : +0,3°C dans [−0,5 ; +0,5]</div>
  <div style="display:inline-flex;align-items:center;gap:.4rem;padding:.3rem .7rem;border-radius:20px;font-size:.8rem;font-weight:700;background:rgba(201,48,48,.10);color:#C93030;border:1.5px solid #C93030;width:fit-content">❌ Non conforme — écart : +0,8°C hors tolérance</div>
</div>

> La **"Sonde connectée"** affiche automatiquement la dernière valeur lue par la sonde. Vous n'avez pas à la relever manuellement — elle se rafraîchit toutes les 30 secondes.

5. Recommencez pour toutes les enceintes de la liste.
6. Quand toutes les cartes sont renseignées, le bouton **`Enregistrer les comparaisons ✓`** devient actif (il était grisé tant qu'une carte manquait).
7. Tapez **`Enregistrer les comparaisons ✓`**.
8. La page revient automatiquement à l'écran Phase 1 avec les étalonnages mis à jour dans l'historique.

---

### Le résumé de Phase 1 affiché en haut

En haut de la Phase 2, le bandeau vert rappelle ce que vous venez de valider :

<div style="background:rgba(45,125,70,.06);border-left:4px solid #2D7D46;border-radius:0 8px 8px 0;padding:.55rem .9rem;font-size:.85rem;margin:.5rem 0 .8rem">
  <div style="font-size:.8rem;font-weight:700;color:#2D7D46;margin-bottom:.2rem">✅ Étape 1 validée</div>
  <div style="color:#3D2008;opacity:.85">Thermomètre Pro — N°SN001 · 0,2°C · Conforme · Émile</div>
</div>

Cela confirme que l'étalonnage du thermomètre de référence est bien enregistré avant d'entamer les comparaisons.

---

## L'historique des étalonnages

En bas de la Phase 1, un tableau liste les **50 derniers étalonnages** réalisés :

<div style="overflow-x:auto;border-radius:8px;border:1px solid #D4A574;margin:.5rem 0 .9rem">
<table style="width:100%;border-collapse:collapse;font-size:.82rem;min-width:480px">
<thead><tr style="background:#3D2008;color:#F5ECD7">
  <th style="padding:.5rem .7rem;text-align:left;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase">Date</th>
  <th style="padding:.5rem .7rem;text-align:left;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase">Thermomètre</th>
  <th style="padding:.5rem .7rem;text-align:left;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase">Température</th>
  <th style="padding:.5rem .7rem;text-align:left;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase">Résultat</th>
  <th style="padding:.5rem .7rem;text-align:left;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase">Action</th>
  <th style="padding:.5rem .7rem;text-align:left;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase">Opérateur</th>
</tr></thead>
<tbody>
<tr><td style="padding:.55rem .7rem;border-bottom:1px solid rgba(212,165,116,.25)">14/05/2026</td><td style="padding:.55rem .7rem;border-bottom:1px solid rgba(212,165,116,.25)">Thermomètre Pro</td><td style="padding:.55rem .7rem;border-bottom:1px solid rgba(212,165,116,.25)">0,2°C</td><td style="padding:.55rem .7rem;border-bottom:1px solid rgba(212,165,116,.25)"><span style="display:inline-flex;padding:.18rem .55rem;border-radius:20px;font-size:.72rem;font-weight:700;background:rgba(45,125,70,.12);color:#2D7D46">✅ Conforme</span></td><td style="padding:.55rem .7rem;border-bottom:1px solid rgba(212,165,116,.25)">Conforme</td><td style="padding:.55rem .7rem;border-bottom:1px solid rgba(212,165,116,.25)">Émile</td></tr>
<tr style="background:rgba(212,165,116,.07)"><td style="padding:.55rem .7rem">12/02/2026</td><td style="padding:.55rem .7rem">Thermomètre Pro</td><td style="padding:.55rem .7rem">0,8°C</td><td style="padding:.55rem .7rem"><span style="display:inline-flex;padding:.18rem .55rem;border-radius:20px;font-size:.72rem;font-weight:700;background:rgba(201,48,48,.10);color:#C93030">❌ Non conforme</span></td><td style="padding:.55rem .7rem">Remplacé</td><td style="padding:.55rem .7rem">Marie</td></tr>
</tbody>
</table>
</div>

Ce tableau vous permet de vérifier rapidement les étalonnages passés et de retrouver la date du dernier contrôle.

---

## Quand faut-il étalonner ?

L'étalonnage est **trimestriel** : toutes les **12 semaines environ** (92 jours).

La tuile **🌡️ ÉTALONNAGE** sur le Hub Tâches HACCP indique automatiquement la situation :

| Ce que vous voyez sur la tuile | Signification |
|---|---|
| Date du prochain étalonnage | Tout va bien, pas d'urgence |
| Badge rouge "En retard" | Le délai de 92 jours est dépassé — faire l'étalonnage dès que possible |
| "Jamais effectué" | Premier étalonnage à faire impérativement |

---

## Ce qu'il faut faire si une sonde est non conforme

Si le badge d'écart d'une enceinte s'affiche en rouge **(❌ Non conforme — écart > 0,5°C)** :

1. Enregistrez quand même la comparaison — la valeur est conservée dans l'historique pour la traçabilité.
2. Signalez le problème au responsable : la sonde de cette enceinte doit être recalculée ou remplacée.
3. En attendant la correction, contrôlez les températures de cette enceinte plus fréquemment avec le thermomètre de référence.

---

## Revenir à l'étape 1 depuis la Phase 2

Si vous avez besoin de corriger quelque chose dans la Phase 1, tapez le bouton **`← Étape 1`** en haut à gauche. Vous revenez sur le formulaire Phase 1. Attention : les valeurs que vous aviez saisies en Phase 2 **ne sont pas sauvegardées** si vous quittez avant d'avoir tapé `Enregistrer les comparaisons ✓`.

---

## Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Ce que ça veut dire | Que faire |
|---|---|---|
| *"La date est obligatoire."* | Le champ Date est vide | Vérifiez que la date est bien remplie |
| *"Sélectionnez un opérateur."* | Aucun prénom choisi | Tapez sur le menu Opérateur et sélectionnez votre prénom |
| *"Sélectionnez un thermomètre de référence."* | Thermomètre non choisi | Tapez sur le menu et sélectionnez le bon thermomètre |
| *"La température est obligatoire."* | Champ Température vide | Saisissez la valeur mesurée |
| *"Sélectionnez une action corrective."* | Aucun bouton d'action tapé | Tapez ✅ Conforme, 🔧 Calibrage ou 🔄 Remplacé selon le cas |
| *"⚠ Aucun thermomètre configuré"* | Aucun thermomètre dans l'administration | Contactez le responsable pour qu'il configure le thermomètre |
| *"Toutes les températures de référence sont obligatoires."* | Une carte enceinte n'est pas remplie en Phase 2 | Remplissez tous les champs avant d'enregistrer |
| Sonde connectée affiche `— °C` | La sonde de cette enceinte ne répond pas | Notez "sonde indisponible" dans le commentaire et signalez au responsable |
| Message rouge sous le formulaire | Erreur d'enregistrement | Vérifiez que le Raspberry Pi est allumé et réessayez |

---

---

---

# Module 9 — Cuisson HACCP (🔥 ≥ 75°C)

<div style="background:rgba(212,165,116,.15);border-left:4px solid #D4A574;border-radius:0 8px 8px 0;padding:.65rem 1rem;font-size:.9rem;line-height:1.5;color:#3D2008;margin-bottom:1.2rem">
<strong style="color:#6B3A1F">Accès :</strong> Hub principal → <strong>🏭 PRODUCTION</strong> → tuile <strong>🔥 CUISSON</strong>
</div>

Ce module enregistre chaque opération de rôtissoire avec traçabilité complète : qui a cuisiné, quel produit, quel lot, les heures, et surtout **la température mesurée à la sortie**. La règle HACCP est claire : **la température à cœur doit atteindre 75°C minimum**. Si elle n'est pas atteinte, une action corrective est obligatoire. Après la cuisson, vous pouvez imprimer l'étiquette et enchaîner directement avec le suivi de refroidissement.

> **Règle de base : pas de double-clic. On tape une seule fois et on attend.**  
> En cas d'inactivité de 5 minutes, la tablette retourne automatiquement à l'accueil.

---

## Vue d'ensemble du wizard — 3 étapes

La page utilise un formulaire guidé en **3 étapes** numérotées, avec une barre de progression visible en haut :

<div style="background:#FFFDF7;border-radius:12px;padding:1rem 1.25rem;border:1.5px solid #D4A574;margin-bottom:1rem">
  <div style="background:#3D2008;color:#FFF;padding:.45rem .9rem;border-radius:6px 6px 0 0;margin:-1rem -1.25rem 1rem;font-size:.85rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase;display:flex;align-items:center;gap:.5rem">
    <a style="color:#FFF;text-decoration:none;font-size:.78rem;border:1.5px solid rgba(255,255,255,.45);border-radius:6px;padding:.25rem .6rem">← Production</a>
    <span style="flex:1;text-align:center">🔥 Cuisson</span>
    <span style="opacity:.9;font-size:.82rem">09:14</span>
  </div>
  <div style="background:#6B3A1F;padding:.6rem 1rem;margin:0 -1.25rem .9rem;display:flex;gap:.4rem;justify-content:flex-start">
    <span style="padding:.55rem 1rem;color:#FFF;font-size:.85rem;font-weight:700;border-bottom:3px solid #F5ECD7">🍗 Rôtissoire</span>
  </div>
  <div style="display:flex;align-items:center;gap:.35rem;justify-content:center;margin-bottom:.6rem">
    <div style="width:34px;height:34px;border-radius:50%;background:#6B3A1F;color:#FFF;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.9rem">1</div>
    <div style="flex:1;max-width:80px;height:2.5px;background:#d8c9b2;border-radius:2px"></div>
    <div style="width:34px;height:34px;border-radius:50%;background:#FFF;border:2px solid #d8c9b2;color:#6B3A1F;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.9rem">2</div>
    <div style="flex:1;max-width:80px;height:2.5px;background:#d8c9b2;border-radius:2px"></div>
    <div style="width:34px;height:34px;border-radius:50%;background:#FFF;border:2px solid #d8c9b2;color:#6B3A1F;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.9rem">3</div>
  </div>
  <div style="text-align:center;font-size:.85rem;color:#888;font-style:italic">Étape 1 active — Qui cuisine ?</div>
</div>

Une fois l'étape 1 (opérateur) et l'étape 2 (produit) remplies, un **bandeau de contexte** apparaît en permanence sous la barre de progression :

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:10px;padding:.45rem .8rem;font-size:.85rem;color:#3D2008;font-weight:700;text-align:center;margin:.5rem 0 .9rem">
  👤 Émile &nbsp;&nbsp;·&nbsp;&nbsp; 📦 Poulet rôti — DLC 17/05/2026
</div>

---

## Étape 1 — Qui cuisine ?

La page affiche les prénoms du personnel sous forme de **tuiles** avec l'initiale en grand :

<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:.5rem 0 .9rem">
  <div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;padding:.9rem .7rem;text-align:center;min-height:100px;display:flex;flex-direction:column;align-items:center;gap:.4rem">
    <div style="width:52px;height:52px;border-radius:50%;background:#f0e8dc;display:flex;align-items:center;justify-content:center;font-size:1.6rem;font-weight:800;color:#6B3A1F">É</div>
    <div style="font-size:.95rem;font-weight:800;color:#3D2008">Émile</div>
  </div>
  <div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;padding:.9rem .7rem;text-align:center;min-height:100px;display:flex;flex-direction:column;align-items:center;gap:.4rem">
    <div style="width:52px;height:52px;border-radius:50%;background:#f0e8dc;display:flex;align-items:center;justify-content:center;font-size:1.6rem;font-weight:800;color:#6B3A1F">M</div>
    <div style="font-size:.95rem;font-weight:800;color:#3D2008">Marie</div>
  </div>
  <div style="background:#f5ede0;border:2px solid #6B3A1F;border-radius:14px;padding:.9rem .7rem;text-align:center;min-height:100px;display:flex;flex-direction:column;align-items:center;gap:.4rem;box-shadow:0 0 0 3px rgba(107,58,31,.18)">
    <div style="width:52px;height:52px;border-radius:50%;background:#f0e8dc;display:flex;align-items:center;justify-content:center;font-size:1.6rem;font-weight:800;color:#6B3A1F">S</div>
    <div style="font-size:.95rem;font-weight:800;color:#3D2008">Simon</div>
  </div>
</div>

**Tapez votre prénom.** La page passe automatiquement à l'étape 2 après un bref instant — inutile de chercher un bouton "Suivant".

---

## Étape 2 — Quel produit ?

### Filtrer par espèce

Des boutons de filtre permettent de n'afficher que les produits d'une espèce :

<div style="display:flex;flex-wrap:wrap;gap:.4rem;margin:.4rem 0 .7rem">
  <span style="padding:.45rem .9rem;border:1.5px solid #6B3A1F;border-radius:20px;font-size:.88rem;font-weight:700;background:#6B3A1F;color:#FFF">Toutes</span>
  <span style="padding:.45rem .9rem;border:1.5px solid #d8c9b2;border-radius:20px;font-size:.88rem;font-weight:700;color:#6B3A1F;background:#FFF">🐂 Bœuf</span>
  <span style="padding:.45rem .9rem;border:1.5px solid #d8c9b2;border-radius:20px;font-size:.88rem;font-weight:700;color:#6B3A1F;background:#FFF">🐔 Volaille</span>
  <span style="padding:.45rem .9rem;border:1.5px solid #d8c9b2;border-radius:20px;font-size:.88rem;font-weight:700;color:#6B3A1F;background:#FFF">🐖 Porc</span>
</div>

Seuls les filtres correspondant aux produits réellement en stock s'affichent.

### Chercher un produit

Un champ de recherche permet de taper les premières lettres du nom du produit pour filtrer la grille.

### Les tuiles produit

Chaque produit est présenté sous forme de tuile :

<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:.4rem 0 .8rem">
  <div style="position:relative;background:#fffbf0;border:1.5px solid #D97706;border-radius:14px;padding:1rem .8rem .9rem;text-align:center;display:flex;flex-direction:column;align-items:center;gap:.4rem">
    <div style="position:absolute;top:-1px;left:50%;transform:translateX(-50%);background:#D97706;color:#FFF;font-size:.65rem;font-weight:700;padding:.12rem .5rem;border-radius:0 0 8px 8px;white-space:nowrap">⭐ EN STOCK</div>
    <div style="width:52px;height:52px;border-radius:50%;background:#f0e8dc;display:flex;align-items:center;justify-content:center;font-size:1.7rem">🐔</div>
    <div style="font-size:.95rem;font-weight:800;color:#3D2008">Poulet rôti</div>
    <div style="font-size:.72rem;font-weight:700;color:#6B3A1F;background:#f5ede0;padding:.12rem .5rem;border-radius:20px">DLC 17/05/2026</div>
    <div style="font-size:.68rem;color:#6b7280">Lot A0514-003</div>
  </div>
  <div style="position:relative;background:#fffbf0;border:1.5px solid #D97706;border-radius:14px;padding:1rem .8rem .9rem;text-align:center;display:flex;flex-direction:column;align-items:center;gap:.4rem">
    <div style="position:absolute;top:-1px;left:50%;transform:translateX(-50%);background:#D97706;color:#FFF;font-size:.65rem;font-weight:700;padding:.12rem .5rem;border-radius:0 0 8px 8px;white-space:nowrap">⭐ EN STOCK</div>
    <div style="width:52px;height:52px;border-radius:50%;background:#f0e8dc;display:flex;align-items:center;justify-content:center;font-size:1.7rem">🐂</div>
    <div style="font-size:.95rem;font-weight:800;color:#3D2008">Rosbeef</div>
    <div style="font-size:.72rem;font-weight:700;color:#6B3A1F;background:#f5ede0;padding:.12rem .5rem;border-radius:20px">DLC 16/05/2026</div>
    <div style="font-size:.68rem;color:#6b7280">Lot B0512-001</div>
  </div>
</div>

> **Important — Règle FIFO :** les produits sont triés par DLC croissante : le produit dont la DLC est la plus proche apparaît en premier. C'est toujours ce produit qu'il faut utiliser en priorité.

Seuls les produits **réellement en stock** s'affichent (réceptions non expirées, ou productions maison en attente). Si un produit vient de la fabrication maison, sa tuile porte le badge `🔪 Fabrication`.

**Tapez la tuile du produit** à cuire.

### Choisir le lot (si plusieurs lots disponibles)

Si le produit a plusieurs lots en stock, un sélecteur apparaît :

<div style="background:#FFF;border:1.5px dashed #D4A574;border-radius:10px;padding:.65rem .8rem;margin:.4rem 0 .8rem">
  <div style="font-size:.82rem;font-weight:700;color:#3D2008;margin-bottom:.4rem">Lot utilisé <span style="color:#C0392B">*</span> <span style="font-weight:500;font-size:.75rem;color:#7a5b3d">(3 lots disponibles)</span></div>
  <select style="width:100%;min-height:48px;font-size:.88rem;font-weight:600;border:1.5px solid #d8c9b2;border-radius:8px;padding:.4rem .6rem;background:#F5ECD7;color:#3D2008">
    <option>⭐ FIFO — Lot A0514-003 · DLC 17/05/2026 · reçu 14/05/2026 · Volailles du Sud</option>
  </select>
  <div style="font-size:.78rem;color:#6B3A1F;margin-top:.35rem">DLC 17/05/2026 · Lot A0514-003</div>
  <button style="margin-top:.5rem;background:#FFF;border:1.5px solid #6B3A1F;color:#6B3A1F;font-weight:700;font-size:.82rem;padding:.4rem .8rem;border-radius:8px">📋 Historique de réception</button>
  <button style="margin-top:.5rem;margin-left:.5rem;background:#6B3A1F;color:#FFF;font-weight:800;font-size:.92rem;padding:.6rem 1.1rem;border-radius:10px;border:none">Suivant →</button>
</div>

Le lot **⭐ FIFO** (celui dont la DLC est la plus courte) est pré-sélectionné automatiquement. En principe, ne le changez pas : c'est le règle FIFO. Si vous avez une bonne raison de choisir un autre lot, sélectionnez-le dans le menu.

Le bouton **`📋 Historique de réception`** ouvre une fenêtre listant tous les lots, leurs DLC, poids, et le fournisseur d'origine.

Si le produit n'a qu'un seul lot, l'étape 3 s'ouvre directement sans ce sélecteur.

Tapez **`Suivant →`** pour passer à l'étape 3.

---

## Étape 3 — Paramètres de cuisson

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;padding:1.1rem 1rem 1.2rem;margin:.5rem 0 .9rem">
  <div style="font-size:1rem;font-weight:800;color:#3D2008;margin-bottom:.8rem">Paramètres de cuisson</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:.8rem;font-size:.85rem">
    <div><div style="font-size:.82rem;font-weight:700;color:#3D2008;margin-bottom:.25rem">Date <span style="color:#C0392B">*</span></div><div style="border:1.5px solid #d8c9b2;border-radius:10px;padding:.6rem .8rem;background:#FFF">2026-05-14</div></div>
    <div><div style="font-size:.82rem;font-weight:700;color:#3D2008;margin-bottom:.25rem">Quantité <span style="color:#C0392B">*</span></div><div style="display:flex;gap:.4rem"><div style="border:1.5px solid #d8c9b2;border-radius:10px;padding:.6rem .8rem;background:#FFF;flex:1">8</div><div style="border:1.5px solid #d8c9b2;border-radius:10px;padding:.6rem .8rem;background:#F5ECD7;color:#6B3A1F;font-weight:700">kg</div></div></div>
    <div><div style="font-size:.82rem;font-weight:700;color:#3D2008;margin-bottom:.25rem">Heure début <span style="color:#C0392B">*</span></div><div style="border:1.5px solid #d8c9b2;border-radius:10px;padding:.6rem .8rem;background:#FFF">09:00</div></div>
    <div>
      <div style="font-size:.82rem;font-weight:700;color:#3D2008;margin-bottom:.25rem">Heure fin <span style="color:#C0392B">*</span></div>
      <div style="border:1.5px solid #d8c9b2;border-radius:10px;padding:.6rem .8rem;background:#FFF;margin-bottom:.35rem">11:00</div>
      <div style="display:flex;gap:.35rem;flex-wrap:wrap">
        <span style="padding:.4rem .5rem;border:1.5px solid #d8c9b2;border-radius:8px;font-size:.82rem;font-weight:700;color:#6B3A1F;background:#FFF">+1h</span>
        <span style="padding:.4rem .5rem;border:1.5px solid #d8c9b2;border-radius:8px;font-size:.82rem;font-weight:700;color:#6B3A1F;background:#FFF">+1h30</span>
        <span style="padding:.4rem .5rem;border:1.5px solid #6B3A1F;border-radius:8px;font-size:.82rem;font-weight:700;color:#FFF;background:#6B3A1F">+2h</span>
        <span style="padding:.4rem .5rem;border:1.5px solid #d8c9b2;border-radius:8px;font-size:.82rem;font-weight:700;color:#6B3A1F;background:#FFF">+2h30</span>
        <span style="padding:.4rem .5rem;border:1.5px solid #d8c9b2;border-radius:8px;font-size:.82rem;font-weight:700;color:#6B3A1F;background:#FFF">+3h</span>
      </div>
    </div>
    <div style="grid-column:1/-1">
      <div style="font-size:.82rem;font-weight:700;color:#3D2008;margin-bottom:.25rem">Température produit — sortie rôtissoire <span style="color:#C0392B">*</span></div>
      <div style="display:flex;gap:.4rem;margin-bottom:.3rem"><div style="border:1.5px solid #d8c9b2;border-radius:10px;padding:.6rem .8rem;background:#FFF;flex:1">ex : 72,5</div><span style="display:flex;align-items:center;padding:0 .8rem;background:#f5ede0;border:1.5px solid #d8c9b2;border-radius:10px;font-weight:700;color:#6B3A1F">°C</span></div>
      <div style="font-size:.78rem;color:#6B3A1F;font-weight:600;margin-bottom:.3rem">🎯 Cible réglementaire : ≥ 75 °C</div>
      <span style="padding:.4rem .6rem;border:1.5px solid #d8c9b2;border-radius:8px;font-size:.82rem;font-weight:700;color:#6B3A1F;background:#FFF">75°C</span>
    </div>
  </div>
</div>

### Remplir le formulaire étape par étape

**Date :** pré-remplie avec aujourd'hui. Ne changez que si vous saisissez une cuisson rétroactive.

**Quantité + Unité :** tapez le poids ou le nombre de pièces. L'unité se choisit dans le menu à droite (`kg`, `g`, `pièces`).

**Heure de début :** saisissez l'heure à laquelle la rôtissoire a démarré.

**Heure de fin :** deux méthodes au choix :
- **Boutons rapides** : tapez `+1h`, `+1h30`, `+2h`, `+2h30` ou `+3h` — l'heure de fin est calculée automatiquement depuis l'heure de début.
- **Saisie manuelle** : tapez la durée en heures + minutes dans les deux petits champs, puis tapez la flèche **`→`** pour appliquer.

> Si vous tapez un bouton de durée sans avoir renseigné l'heure de début, un message d'erreur s'affiche : *"Renseignez d'abord l'heure de début."*

**Température produit — sortie rôtissoire :**
C'est le champ le plus important. Mesurez la **température à cœur** du produit avec le thermomètre à sonde à la sortie de la rôtissoire et saisissez la valeur.

Le bouton rapide **`75°C`** remplit le champ directement si le thermomètre affiche exactement 75°C.

Dès que vous tapez une valeur, un badge de conformité s'affiche immédiatement :

<div style="display:flex;flex-direction:column;gap:.5rem;margin:.4rem 0 .8rem">
  <div style="background:#E1F2DF;color:#2D7D46;border:1.5px solid #2D7D46;border-radius:10px;padding:.6rem .85rem;font-weight:700;font-size:.88rem;text-align:center">✓ Conforme — 78,5 °C ≥ 75 °C</div>
  <div style="background:#FCE6E3;color:#C0392B;border:1.5px solid #C0392B;border-radius:10px;padding:.6rem .85rem;font-weight:700;font-size:.88rem;text-align:center">⚠ Non conforme — 68,0 °C &lt; 75 °C — action corrective requise</div>
</div>

**Action corrective (si T° < 75°C) :**
Si la température est insuffisante, un champ de texte apparaît automatiquement, déjà pré-rempli avec la procédure à suivre :

<div style="background:#FFF;border:1.5px solid #d8c9b2;border-radius:10px;padding:.6rem .85rem;font-size:.85rem;color:#3D2008;margin:.4rem 0 .8rem;font-style:italic">
Remettre le produit en cuisson (four, rôtissoire, marmite) et prolonger le temps de cuisson jusqu'à l'atteinte de la température de 75 °C à cœur
</div>

Ce texte est **modifiable**. Si finalement la deuxième mesure donne ≥ 75°C, revenez corriger la température dans le formulaire — le champ action corrective disparaît automatiquement.

**Bouton `✓ Enregistrer la cuisson` :** tapez pour valider. Si un champ obligatoire manque, un message rouge s'affiche en bas du formulaire.

---

## Après l'enregistrement — Que faire ensuite ?

Après une sauvegarde réussie, une **fenêtre de choix** s'ouvre :

<div style="background:#FFFDF7;border-radius:14px;overflow:hidden;border:1.5px solid #D4A574;margin:.5rem 0 .9rem;max-width:380px">
  <div style="background:#6B3A1F;color:#FFF;padding:.75rem 1rem;font-size:.95rem;font-weight:800">Cuisson enregistrée</div>
  <div style="padding:.85rem 1rem;display:flex;flex-direction:column;gap:.6rem">
    <div style="background:#f5ede0;border-radius:8px;padding:.45rem .8rem;font-size:.85rem;font-weight:700;color:#6B3A1F;text-align:center">Poulet rôti · 8 kg · DLC 17/05/2026</div>
    <button style="display:flex;align-items:center;gap:.8rem;width:100%;background:#FFFDF7;border:1.5px solid #d8c9b2;border-radius:12px;padding:.85rem .95rem;font-weight:800;font-size:.95rem;color:#3D2008;text-align:left"><span style="width:42px;height:42px;background:#f0e8dc;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.5rem;flex-shrink:0">🖨</span> Imprimer étiquette</button>
    <button style="display:flex;align-items:center;gap:.8rem;width:100%;background:#FFFDF7;border:1.5px solid #d8c9b2;border-radius:12px;padding:.85rem .95rem;font-weight:800;font-size:.95rem;color:#3D2008;text-align:left"><span style="width:42px;height:42px;background:#f0e8dc;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.5rem;flex-shrink:0">🍗</span> Nouvelle cuisson</button>
    <button style="display:flex;align-items:center;gap:.8rem;width:100%;background:#FFFDF7;border:1.5px solid #d8c9b2;border-radius:12px;padding:.85rem .95rem;font-weight:800;font-size:.95rem;color:#3D2008;text-align:left"><span style="width:42px;height:42px;background:#f0e8dc;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.5rem;flex-shrink:0">🏠</span> Retour au hub</button>
    <button style="display:flex;align-items:center;gap:.8rem;width:100%;background:#EBF6EF;border:1.5px solid #2D7D46;border-radius:12px;padding:.85rem .95rem;font-weight:800;font-size:.95rem;color:#2D7D46;text-align:left"><span style="width:42px;height:42px;background:#d2ecda;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.5rem;flex-shrink:0">❄</span> Refroidissement du produit</button>
  </div>
</div>

| Bouton | Ce qu'il fait |
|---|---|
| **🖨 Imprimer étiquette** | Génère et envoie l'étiquette à l'imprimante thermique Brother 62mm (voir ci-dessous) |
| **🍗 Nouvelle cuisson** | Réinitialise entièrement le formulaire et revient à l'étape 1 |
| **🏠 Retour au hub** | Retourne à l'écran d'accueil |
| **❄ Refroidissement du produit** *(vert)* | Ouvre directement le module Refroidissement avec les données de cette cuisson pré-remplies |

> Le bouton **❄ Refroidissement** est en vert pour signaler que c'est l'action à privilégier : après une cuisson, le produit doit être mis en refroidissement rapide. Le module 10 explique cette procédure.

---

## L'étiquette thermique imprimée (Brother 62mm)

En tapant **🖨 Imprimer étiquette**, l'étiquette est envoyée à l'imprimante Brother :

<div style="border:2px solid black;border-radius:6px;padding:6px;width:160px;font-family:sans-serif;font-size:11px;margin:.5rem auto .9rem">
  <div style="text-align:center;border:2px solid black;border-radius:4px;padding:3px;margin-bottom:5px"><div style="font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.05em">[CUIT]</div></div>
  <h1 style="font-size:12px;font-weight:900;margin:0 0 5px;text-transform:uppercase;text-align:center;line-height:1.1">POULET RÔTI</h1>
  <div style="font-weight:bold;text-align:center;margin-bottom:5px;font-size:10px">Quantité : 8 kg</div>
  <div style="border:2px solid black;border-radius:4px;padding:3px;text-align:center;margin-bottom:5px">
    <div style="font-size:9px;font-weight:bold;text-transform:uppercase">DLC :</div>
    <div style="font-size:14px;font-weight:900;color:red">17/05/26</div>
  </div>
  <div style="font-weight:bold;text-align:center;margin-bottom:4px;padding:2px;border:1px dashed black;font-size:10px">Lot : A0514-003</div>
  <div style="font-weight:bold;text-align:center;margin-bottom:3px;font-size:9px">T° fin cuisson : 78,5 °C</div>
  <div style="text-align:center;margin-bottom:3px;font-size:9px">Cuit le 14/05/26 à 11h00</div>
  <div style="text-align:center;border-top:1px solid black;padding-top:2px;font-size:9px">Par : Émile</div>
</div>

L'étiquette indique : `[CUIT]`, le nom du produit en majuscules, la quantité, la **DLC en rouge et encadrée**, le lot d'origine, la température mesurée, la date et heure de fin de cuisson, et le prénom de l'opérateur.

---

## La DLC calculée — règle des 3 jours

Après enregistrement, le système calcule automatiquement la **DLC du produit cuit** :

> **DLC = date de cuisson + 3 jours**

Par exemple : cuisson le 14/05 → DLC le 17/05.

**Attention — règle de plafonnement :** si le lot de matière première utilisé avait une DLC plus courte que ces 3 jours, la DLC finale est celle du lot source. Exemple : cuisson le 14/05 avec un lot dont la DLC était le 15/05 → la DLC finale est le 15/05 (pas le 17/05).

Dans ce cas, une alerte s'affiche avant l'impression :

<div style="background:#FFF8E1;border-left:4px solid #D97706;border-radius:0 8px 8px 0;padding:.6rem 1rem;font-size:.85rem;color:#3D2008;margin:.4rem 0 .8rem">
⚠ DLC ajustée — Le module Cuisson a ajusté la DLC calculée à la DLC d'origine du produit : 15/05/2026
</div>

Tapez **OK** pour fermer cette alerte et continuer normalement.

---

## L'historique récent

En bas de l'étape 3, un tableau affiche les **20 dernières cuissons** :

<div style="display:flex;flex-direction:column;gap:.4rem;margin:.4rem 0 .8rem">
  <div style="background:#FFF;border:1.5px solid #e8d9c4;border-radius:10px;padding:.65rem .85rem;display:grid;grid-template-columns:auto 1fr auto;gap:.6rem;align-items:center;font-size:.85rem">
    <div style="font-weight:700;color:#6B3A1F;white-space:nowrap">14/05 · 09h–11h</div>
    <div style="color:#3D2008"><strong>Poulet rôti</strong> · 8 kg · Émile</div>
    <div style="background:#E1F2DF;color:#2D7D46;font-weight:800;font-size:.9rem;padding:.25rem .6rem;border-radius:20px">78,5°C</div>
  </div>
  <div style="background:#FFF6F4;border:1.5px solid #C0392B;border-radius:10px;padding:.65rem .85rem;display:grid;grid-template-columns:auto 1fr auto;gap:.6rem;align-items:center;font-size:.85rem">
    <div style="font-weight:700;color:#6B3A1F;white-space:nowrap">12/05 · 10h–12h</div>
    <div style="color:#3D2008"><strong>Rôti de porc</strong> · 5 kg · Marie</div>
    <div style="background:#FCE6E3;color:#C0392B;font-weight:800;font-size:.9rem;padding:.25rem .6rem;border-radius:20px">68,0°C</div>
  </div>
</div>

Les températures conformes (≥ 75°C) s'affichent en **vert**, les non-conformes en **rouge**. Les lignes rouges ont également un fond légèrement rosé pour attirer l'attention.

---

## Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Ce que ça veut dire | Que faire |
|---|---|---|
| *"Veuillez sélectionner un opérateur."* | Étape 1 non complétée | Tapez votre prénom sur la tuile |
| *"Veuillez sélectionner un produit."* | Étape 2 non complétée | Sélectionnez le produit et tapez Suivant → |
| *"Quantité requise (> 0)."* | Champ Quantité vide ou nul | Saisissez un nombre supérieur à zéro |
| *"Heures de début et fin requises."* | Une heure manque | Renseignez les deux heures |
| *"Température de sortie requise."* | Champ T° vide | Mesurez et saisissez la température |
| *"Action corrective obligatoire si T° < 75 °C."* | T° insuffisante + zone action vide | Remplissez la zone action corrective |
| *"Renseignez d'abord l'heure de début."* | Clic sur durée rapide sans heure début | Saisissez d'abord l'heure de début |
| *"Aucun produit trouvé."* | Aucun produit en stock | Il n'y a pas de lot disponible pour ce type de produit |
| *"Aucun opérateur actif."* | Personnel non configuré | Contactez le responsable |
| Alerte popup ⚠ DLC ajustée | DLC réduite car lot source expirait plus tôt | Normal — tapez OK, la DLC sur l'étiquette est correcte |
| Message rouge sous le formulaire | Erreur d'enregistrement | Vérifiez que le Raspberry Pi est allumé et réessayez |

---

---

---

# Module 10 — Refroidissement Rapide (❄️ ≤ 10°C en ≤ 2h)

<div style="background:rgba(212,165,116,.15);border-left:4px solid #D4A574;border-radius:0 8px 8px 0;padding:.65rem 1rem;font-size:.9rem;line-height:1.5;color:#3D2008;margin-bottom:1.2rem">
<strong style="color:#6B3A1F">Accès :</strong> Hub principal → <strong>🏭 PRODUCTION</strong> → tuile <strong>❄️ REFROIDISSEMENT</strong> — ou directement depuis le bouton <strong>❄ Refroidissement du produit</strong> après une cuisson.
</div>

Après chaque cuisson, le produit chaud doit être refroidi le plus vite possible. La règle HACCP est stricte :

> **Le produit doit passer de ≥ 75°C à ≤ 10°C à cœur en 2 heures maximum.**

Ce module enregistre cette opération et vérifie automatiquement que la règle est respectée. Si ce n'est pas le cas, il guide obligatoirement vers la décision à prendre — selon la situation, soit **remettre en cuisson**, soit **jeter le produit**.

> **Règle de base : pas de double-clic. On tape une seule fois et on attend.**  
> En cas d'inactivité de 5 minutes, la tablette retourne automatiquement à l'accueil.

---

## Cas le plus fréquent — arriver depuis la Cuisson

Quand vous tapez **❄ Refroidissement du produit** à la fin d'une cuisson, la tablette ouvre automatiquement ce module **avec l'opérateur et le produit déjà sélectionnés**. Vous arrivez directement à l'étape 3 (Données du refroidissement) sans avoir à refaire les étapes 1 et 2.

Si vous ouvrez le module depuis le menu Production, vous passez par les 3 étapes normalement.

---

## Vue d'ensemble — wizard 3 étapes

Même structure que le module Cuisson : barre de progression numérotée 1-2-3, bandeau de contexte `👤 Opérateur · 📦 Produit` visible dès les deux premiers choix faits.

---

## Étape 1 — Qui refroidit ?

Même interface qu'à la Cuisson : grille de tuiles avec l'initiale et le prénom du personnel. Tapez votre prénom — la page avance automatiquement à l'étape 2.

---

## Étape 2 — Quel produit ?

> *Uniquement les produits passés en cuisson.*

Cette liste n'affiche **que les produits cuits** qui sont encore en attente de refroidissement (ni déjà refroidis, ni jetés, ni avec DLC dépassée).

<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:.4rem 0 .8rem">
  <div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;padding:.9rem .8rem;text-align:center;display:flex;flex-direction:column;align-items:center;gap:.4rem">
    <div style="width:52px;height:52px;border-radius:50%;background:#f0e8dc;display:flex;align-items:center;justify-content:center;font-size:1.7rem">🥩</div>
    <div style="font-size:.95rem;font-weight:800;color:#3D2008">Poulet rôti</div>
    <div style="font-size:.72rem;color:#6B3A1F">Cuisson du 14/05/2026</div>
    <div style="font-size:.68rem;color:#6b7280">Lot A0514-003</div>
  </div>
  <div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;padding:.9rem .8rem;text-align:center;display:flex;flex-direction:column;align-items:center;gap:.4rem">
    <div style="width:52px;height:52px;border-radius:50%;background:#f0e8dc;display:flex;align-items:center;justify-content:center;font-size:1.7rem">🥩</div>
    <div style="font-size:.95rem;font-weight:800;color:#3D2008">Rosbeef</div>
    <div style="font-size:.72rem;color:#6B3A1F">Cuisson du 14/05/2026</div>
    <div style="font-size:.68rem;color:#6b7280">Lot B0512-001</div>
  </div>
</div>

Si la liste est vide : *"Aucun produit cuit. Enregistrez d'abord une cuisson."* — retournez au module Cuisson.

Un champ de recherche permet de filtrer par nom. Tapez la tuile du produit concerné — la page avance automatiquement à l'étape 3.

---

## Étape 3 — Données du refroidissement

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;padding:1.1rem 1rem 1.2rem;margin:.5rem 0 .9rem">
  <div style="font-size:1rem;font-weight:800;color:#3D2008;margin-bottom:.8rem">Données du refroidissement</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:.8rem;font-size:.85rem">
    <div style="grid-column:1/-1"><div style="font-size:.82rem;font-weight:700;color:#3D2008;margin-bottom:.25rem">Date <span style="color:#C0392B">*</span></div><div style="border:1.5px solid #d8c9b2;border-radius:10px;padding:.6rem .8rem;background:#FFF;max-width:200px">2026-05-14</div></div>
    <div>
      <div style="font-size:.82rem;font-weight:700;color:#3D2008;margin-bottom:.25rem">Heure mise en refroidissement <span style="color:#C0392B">*</span></div>
      <div style="border:1.5px solid #d8c9b2;border-radius:10px;padding:.6rem .8rem;background:#FFF;margin-bottom:.3rem">11:05</div>
    </div>
    <div>
      <div style="font-size:.82rem;font-weight:700;color:#3D2008;margin-bottom:.25rem">Heure fin refroidissement <span style="color:#C0392B">*</span></div>
      <div style="border:1.5px solid #d8c9b2;border-radius:10px;padding:.6rem .8rem;background:#FFF;margin-bottom:.3rem">13:05</div>
      <div style="display:flex;gap:.35rem;flex-wrap:wrap;margin-bottom:.25rem">
        <span style="padding:.4rem .5rem;border:1.5px solid #d8c9b2;border-radius:8px;font-size:.82rem;font-weight:700;color:#6B3A1F;background:#FFF">+1h</span>
        <span style="padding:.4rem .5rem;border:1.5px solid #d8c9b2;border-radius:8px;font-size:.82rem;font-weight:700;color:#6B3A1F;background:#FFF">+1h30</span>
        <span style="padding:.4rem .5rem;border:1.5px solid #6B3A1F;border-radius:8px;font-size:.82rem;font-weight:700;color:#FFF;background:#6B3A1F">+2h (max)</span>
      </div>
      <div style="font-size:.75rem;color:#6B3A1F;font-weight:600">⏱ Durée maxi réglementaire : 2 h</div>
    </div>
    <div>
      <div style="font-size:.82rem;font-weight:700;color:#3D2008;margin-bottom:.25rem">T° à cœur avant refroidissement <span style="color:#C0392B">*</span></div>
      <div style="display:flex;gap:.4rem;margin-bottom:.25rem"><div style="border:1.5px solid #d8c9b2;border-radius:10px;padding:.6rem .8rem;background:#FFF;flex:1">78,5</div><span style="display:flex;align-items:center;padding:0 .8rem;background:#f5ede0;border:1.5px solid #d8c9b2;border-radius:10px;font-weight:700;color:#6B3A1F">°C</span></div>
      <div style="font-size:.75rem;color:#6B3A1F;font-weight:600">⚠️ Sortie cuisson : minimum 75 °C obligatoire</div>
    </div>
    <div>
      <div style="font-size:.82rem;font-weight:700;color:#3D2008;margin-bottom:.25rem">T° à cœur après refroidissement <span style="color:#C0392B">*</span></div>
      <div style="display:flex;gap:.4rem;margin-bottom:.25rem"><div style="border:1.5px solid #d8c9b2;border-radius:10px;padding:.6rem .8rem;background:#FFF;flex:1">ex : 8,0</div><span style="display:flex;align-items:center;padding:0 .8rem;background:#f5ede0;border:1.5px solid #d8c9b2;border-radius:10px;font-weight:700;color:#6B3A1F">°C</span></div>
      <div style="font-size:.75rem;color:#6B3A1F;font-weight:600">🎯 Cible réglementaire : ≤ 10 °C</div>
    </div>
  </div>
</div>

### Remplir le formulaire

**Date :** pré-remplie avec aujourd'hui.

**Heure de mise en refroidissement :** pré-remplie avec l'heure actuelle à votre arrivée sur cette étape. Corrigez si besoin.

**Heure de fin de refroidissement :** le bouton **`+2h (max)`** est déjà activé par défaut, car 2 heures est la limite réglementaire. Si le refroidissement a pris moins de temps, tapez `+1h` ou `+1h30`.

> Si vous tapez un bouton de durée sans avoir renseigné l'heure de début, un message s'affiche : *"Renseignez d'abord l'heure de mise en refroidissement."*

**T° à cœur avant refroidissement :** température mesurée à cœur **à la sortie de la rôtissoire**. Si vous arrivez depuis le module Cuisson, ce champ est déjà rempli avec la valeur que vous avez saisie lors de la cuisson. La valeur minimale requise est 75°C.

**T° à cœur après refroidissement :** température mesurée à cœur **après le passage au froid**. La cible est ≤ 10°C. Prenez cette mesure avec la sonde thermomètre au cœur du produit.

---

## Les bandeaux de conformité (mis à jour en temps réel)

Dès que vous remplissez les températures et les heures, un bandeau s'affiche et se met à jour automatiquement.

### ✅ Tout est conforme

<div style="background:#E1F2DF;color:#2D7D46;border:1.5px solid #2D7D46;border-radius:10px;padding:.6rem .85rem;font-weight:700;font-size:.88rem;text-align:center;margin:.4rem 0 .6rem">✓ Conforme — cuisson 78,5 °C · refroidissement 8,0 °C en 1h55</div>

Ce bandeau vert s'affiche uniquement quand **les trois conditions** sont toutes respectées :
- Température de cuisson ≥ 75°C
- Température finale ≤ 10°C
- Durée ≤ 2 heures

### ⚠️ Non conforme — une ou deux conditions ratées

<div style="background:#FCE6E3;color:#C0392B;border:1.5px solid #C0392B;border-radius:10px;padding:.6rem .85rem;font-weight:700;font-size:.88rem;text-align:center;margin:.4rem 0 .6rem">⚠ Non conforme — T° finale 12,0 °C > 10 °C — action corrective requise</div>

Le bandeau rouge précise exactement quelle(s) condition(s) sont KO. Plusieurs causes peuvent s'afficher simultanément.

### ⚠️ CUISSON INSUFFISANTE — T° initiale < 75°C

<div style="background:#FCE6E3;color:#C0392B;border:1.5px solid #C0392B;border-radius:10px;padding:.7rem .9rem;font-size:.85rem;margin:.4rem 0 .6rem">
<strong>⚠ CUISSON INSUFFISANTE — T° à cœur &lt; 75 °C à la sortie cuisson.</strong><br>
<strong>Pourquoi :</strong> En dessous de 75 °C à cœur, les bactéries pathogènes ne sont pas éliminées.<br>
<strong>Action corrective :</strong> Remettre le produit en cuisson (four, rôtissoire, marmite) et prolonger le temps de cuisson jusqu'à l'atteinte de 75 °C à cœur.
<div style="margin-top:.6rem">
<button style="width:100%;padding:.85rem;font-size:1rem;font-weight:800;background:#B45309;color:#FFF;border:none;border-radius:10px;min-height:52px">🔥 Remettre en cuisson</button>
<div style="font-size:.78rem;color:#7f1d1d;margin:.4rem 0 0;text-align:center;font-weight:600">Bascule vers le module Cuisson avec le même opérateur et le même produit pré-sélectionnés.</div>
</div>
</div>

Ce bandeau s'affiche si vous avez saisi une température initiale **inférieure à 75°C**. Dans ce cas la bonne action est de **remettre le produit en cuisson**, pas de le jeter. Tapez le bouton orange **`🔥 Remettre en cuisson`** — la tablette vous ramène directement au module Cuisson avec l'opérateur et le produit déjà sélectionnés.

### ⛔ JETER LES PRODUITS — les deux conditions de refroidissement KO

<div style="background:#FCE6E3;color:#C0392B;border:1.5px solid #C0392B;border-radius:10px;padding:.6rem .85rem;font-weight:700;font-size:.85rem;margin:.4rem 0 .6rem">
⛔ JETER LES PRODUITS — couple temps/température de refroidissement non respecté (durée &gt; 2 h ET T° finale &gt; 10 °C).
</div>

Ce bandeau rouge foncé s'affiche **uniquement si les deux conditions sont ratées en même temps** : la durée dépasse 2 heures **ET** la température finale est encore au-dessus de 10°C. Dans ce cas, le produit représente un risque sanitaire et doit être jeté.

> **Important à bien comprendre :**
> - Durée > 2h mais T° finale ≤ 10°C → non conforme, mais pas de jet obligatoire
> - T° finale > 10°C mais durée ≤ 2h → non conforme, mais pas de jet obligatoire
> - Durée > 2h **ET** T° finale > 10°C → **jet obligatoire**

---

## La procédure de jet — étapes obligatoires

Quand le bandeau ⛔ s'affiche, une section **Action corrective** apparaît en dessous avec un bouton rouge foncé :

<div style="background:#FFF;border:1.5px solid #d8c9b2;border-radius:10px;padding:.85rem 1rem;margin:.4rem 0 .8rem">
  <div style="font-size:.82rem;font-weight:700;color:#3D2008;margin-bottom:.5rem">Action corrective <span style="color:#C0392B">*</span></div>
  <button style="width:100%;padding:.9rem;font-size:1rem;font-weight:800;background:#7f1d1d;color:#FFF;border:none;border-radius:10px;min-height:52px;display:flex;align-items:center;justify-content:center;gap:.5rem">⛔ Confirmer : Jeter le produit</button>
  <div style="font-size:.78rem;color:#7f1d1d;margin:.4rem 0 0;text-align:center;font-weight:600">Ce produit sera retiré du stock et enregistré comme jeté dans le calendrier.</div>
</div>

**Tapez `⛔ Confirmer : Jeter le produit`.**

Après ce clic, l'interface change :

<div style="background:#FFF;border:1.5px solid #d8c9b2;border-radius:10px;padding:.85rem 1rem;margin:.4rem 0 .8rem">
  <div style="background:#7f1d1d;color:#FFF;padding:.75rem 1rem;border-radius:10px;font-weight:800;font-size:.95rem;text-align:center;margin-bottom:.55rem">✓ Produit marqué comme JETÉ — retiré du stock</div>
  <textarea style="width:100%;min-height:60px;border:1.5px solid #d8c9b2;border-radius:10px;padding:.55rem .8rem;font-size:.85rem;background:#FFF;box-sizing:border-box" placeholder="Note optionnelle : cause, quantité, n° lot…"></textarea>
  <button style="margin-top:.5rem;width:100%;padding:.55rem;background:transparent;border:1.5px solid #9E8572;border-radius:8px;color:#6B3A1F;font-size:.85rem;font-weight:700">✕ Annuler</button>
</div>

- Le bandeau rouge foncé **"✓ Produit marqué comme JETÉ"** confirme que la décision est prise.
- Vous pouvez ajouter une **note optionnelle** (cause du problème, quantité précise, numéro de lot, observations).
- Si vous vous êtes trompé, tapez **`✕ Annuler`** pour revenir en arrière — le jet n'est pas encore définitif à ce stade.

> **Le jet ne devient définitif qu'au moment où vous tapez `✓ Enregistrer le refroidissement`**. Jusqu'à ce bouton, vous pouvez encore annuler.

Une fois enregistré avec jet confirmé, **le produit est retiré du stock** et ne réapparaîtra plus dans le calendrier DLC.

---

## Bloquer la soumission sans avoir confirmé le jet

Si le bandeau ⛔ est affiché mais que vous essayez d'enregistrer sans avoir tapé "Confirmer : Jeter le produit", le système **refuse l'enregistrement** avec ce message :

<div style="background:#FCE6E3;color:#C0392B;border:1.5px solid #C0392B;border-radius:10px;padding:.6rem .85rem;font-size:.85rem;font-weight:600;margin:.4rem 0 .8rem">
Confirmez l'action 'Jeter le produit' avant d'enregistrer (durée > 2h · T° finale > 10°C).
</div>

Vous devez obligatoirement taper le bouton de confirmation avant de pouvoir enregistrer.

---

## Enregistrer et choisir la suite

Quand tout est rempli, tapez **`✓ Enregistrer le refroidissement`**. Une fenêtre de choix apparaît :

<div style="background:#FFFDF7;border-radius:14px;overflow:hidden;border:1.5px solid #D4A574;margin:.5rem 0 .9rem;max-width:380px">
  <div style="background:#6B3A1F;color:#FFF;padding:.75rem 1rem;font-size:.95rem;font-weight:800">✓ Refroidissement enregistré</div>
  <div style="padding:.85rem 1rem;display:flex;flex-direction:column;gap:.6rem">
    <div style="background:#f5ede0;border-radius:8px;padding:.45rem .8rem;font-size:.85rem;font-weight:700;color:#6B3A1F;text-align:center">Poulet rôti · 8 kg · DLC 17/05/2026</div>
    <button style="display:flex;align-items:center;gap:.8rem;width:100%;background:#FFFDF7;border:1.5px solid #d8c9b2;border-radius:12px;padding:.85rem .95rem;font-weight:800;font-size:.95rem;color:#3D2008;text-align:left"><span style="width:42px;height:42px;background:#f0e8dc;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.5rem;flex-shrink:0">🖨</span> Imprimer étiquette</button>
    <button style="display:flex;align-items:center;gap:.8rem;width:100%;background:#FFFDF7;border:1.5px solid #d8c9b2;border-radius:12px;padding:.85rem .95rem;font-weight:800;font-size:.95rem;color:#3D2008;text-align:left"><span style="width:42px;height:42px;background:#f0e8dc;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.5rem;flex-shrink:0">❄</span> Nouveau refroidissement</button>
    <button style="display:flex;align-items:center;gap:.8rem;width:100%;background:#FFFDF7;border:1.5px solid #d8c9b2;border-radius:12px;padding:.85rem .95rem;font-weight:800;font-size:.95rem;color:#3D2008;text-align:left"><span style="width:42px;height:42px;background:#f0e8dc;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.5rem;flex-shrink:0">🏠</span> Retour au hub</button>
  </div>
</div>

| Bouton | Condition | Ce qu'il fait |
|---|---|---|
| **🖨 Imprimer étiquette** | **Masqué si le produit a été jeté** | Imprime l'étiquette thermique `[REFROIDI]` sur l'imprimante Brother |
| **❄ Nouveau refroidissement** | Toujours visible | Repart au début du wizard |
| **🏠 Retour au hub** | Toujours visible | Retourne à l'écran d'accueil |

Si le produit a été jeté, le titre de la fenêtre est **"⛔ Refroidissement enregistré — produits à jeter"** et le bouton d'impression est masqué (un produit jeté ne reçoit pas d'étiquette).

---

## L'étiquette thermique imprimée (Brother 62mm)

<div style="border:2px solid black;border-radius:6px;padding:6px;width:160px;font-family:sans-serif;font-size:11px;margin:.5rem auto .9rem">
  <div style="text-align:center;border:2px solid black;border-radius:4px;padding:3px;margin-bottom:5px"><div style="font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.05em">[REFROIDI]</div></div>
  <h1 style="font-size:12px;font-weight:900;margin:0 0 5px;text-transform:uppercase;text-align:center;line-height:1.1">POULET RÔTI</h1>
  <div style="font-weight:bold;text-align:center;margin-bottom:5px;font-size:10px">Quantité : 8 kg</div>
  <div style="border:2px solid black;border-radius:4px;padding:3px;text-align:center;margin-bottom:5px">
    <div style="font-size:9px;font-weight:bold;text-transform:uppercase">DLC :</div>
    <div style="font-size:14px;font-weight:900;color:red">17/05/26</div>
  </div>
  <div style="font-weight:bold;text-align:center;margin-bottom:4px;padding:2px;border:1px dashed black;font-size:10px">Lot : A0514-003</div>
  <div style="font-weight:bold;text-align:center;margin-bottom:3px;font-size:9px">T° fin refroidissement : 8,0 °C</div>
  <div style="text-align:center;margin-bottom:3px;font-size:9px">Refroidi le 14/05/26 à 13h05</div>
  <div style="text-align:center;border-top:1px solid black;padding-top:2px;font-size:9px">Par : Émile</div>
</div>

Identique au format Cuisson, mais avec le tag `[REFROIDI]` et la **T° de fin de refroidissement**.

---

## L'historique récent

En bas du formulaire, les 20 derniers refroidissements sont affichés :

<div style="display:flex;flex-direction:column;gap:.4rem;margin:.4rem 0 .8rem">
  <div style="background:#FFF;border:1.5px solid #e8d9c4;border-radius:10px;padding:.65rem .85rem;display:grid;grid-template-columns:auto 1fr auto;gap:.6rem;align-items:center;font-size:.85rem">
    <div style="font-weight:700;color:#6B3A1F;white-space:nowrap">14/05 · 11h–13h · 2h00</div>
    <div style="color:#3D2008"><strong>Poulet rôti</strong> · Lot A0514 · Émile</div>
    <div style="background:#E1F2DF;color:#2D7D46;font-weight:800;font-size:.9rem;padding:.25rem .6rem;border-radius:20px">8,0°C</div>
  </div>
  <div style="background:#FFF6F4;border:1.5px solid #C0392B;border-radius:10px;padding:.65rem .85rem;display:grid;grid-template-columns:auto 1fr auto;gap:.6rem;align-items:center;font-size:.85rem">
    <div style="font-weight:700;color:#6B3A1F;white-space:nowrap">12/05 · 12h–15h · 3h00</div>
    <div style="color:#3D2008"><strong>⛔ JETER · Rôti de porc</strong> · Lot B0512 · Marie</div>
    <div style="background:#FCE6E3;color:#C0392B;font-weight:800;font-size:.9rem;padding:.25rem .6rem;border-radius:20px">14,0°C</div>
  </div>
</div>

Les lignes de produits jetés affichent le préfixe **⛔ JETER** et ont un fond rosé avec bordure rouge.

---

## Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Ce que ça veut dire | Que faire |
|---|---|---|
| *"Heures de début et fin requises."* | Une heure manque | Renseignez les deux heures |
| *"Durée de refroidissement invalide."* | Heure fin = heure début | Vérifiez les heures saisies |
| *"Température à cœur avant refroidissement requise."* | Champ T° initiale vide | Saisissez la température de sortie de cuisson |
| *"Température à cœur après refroidissement requise."* | Champ T° finale vide | Mesurez et saisissez la T° après refroidissement |
| *"Confirmez l'action 'Jeter le produit'…"* | Bandeau ⛔ affiché mais non confirmé | Tapez le bouton rouge ⛔ de confirmation avant d'enregistrer |
| *"Renseignez d'abord l'heure de mise en refroidissement."* | Clic sur durée sans heure début | Saisissez l'heure de début d'abord |
| *"Aucun produit cuit."* | Liste vide | Enregistrez d'abord une cuisson dans le module 9 |
| Alerte popup ⚠ DLC ajustée | DLC réduite car lot source expirait plus tôt | Normal — tapez OK, la DLC sur l'étiquette est correcte |
| Bouton 🖨 Imprimer étiquette absent | Produit marqué comme jeté | C'est normal, on n'imprime pas d'étiquette pour un produit jeté |
| Message rouge sous le formulaire | Erreur d'enregistrement | Vérifiez que le Raspberry Pi est allumé et réessayez |

---

---

---

# Module 11 — Gestion des Recettes (Administration)

<div style="background:rgba(212,165,116,.15);border-left:4px solid #D4A574;border-radius:0 8px 8px 0;padding:.65rem 1rem;font-size:.9rem;line-height:1.5;color:#3D2008;margin-bottom:1rem">
<strong style="color:#6B3A1F">Accès :</strong> Hub principal → <strong>🏭 PRODUCTION</strong> → <strong>FABRICATION</strong> → bouton <strong>✏️ Gérer les recettes</strong> → <strong>+ Créer une nouvelle recette</strong>
</div>

<div style="background:rgba(201,48,48,.08);border-left:4px solid #C93030;border-radius:0 8px 8px 0;padding:.6rem 1rem;font-size:.88rem;color:#3D2008;margin-bottom:1.2rem">
<strong style="color:#C93030">⚠️ Page réservée aux responsables.</strong> La saisie quotidienne de production (wizard Fabrication & Étiquettes) est documentée au <strong>Module 3</strong>. Cette page sert uniquement à créer et modifier les recettes que les opérateurs utiliseront ensuite.
</div>

Une **recette** définit :
- Le **produit fini** qu'elle permet de fabriquer
- La **liste des ingrédients** avec leurs quantités de base
- Le **rendement de base** (ex. : 1 kg de saucisse Toulouse)

Une fois la recette enregistrée, les opérateurs peuvent la sélectionner dans le wizard de fabrication pour produire en renseignant la quantité souhaitée — les quantités d'ingrédients sont calculées automatiquement de façon proportionnelle.

---

## Créer une recette — vue d'ensemble

<div style="background:#FFFDF7;border-radius:16px;overflow:hidden;border:1.5px solid #D4A574;margin:.5rem 0 .9rem">
  <div style="background:#6B3A1F;color:#F5ECD7;padding:.65rem 1rem;display:flex;align-items:center;gap:.75rem">
    <a style="color:#F5ECD7;border:1.5px solid rgba(255,255,255,.3);border-radius:8px;padding:.3rem .7rem;font-size:.82rem;font-weight:700;text-decoration:none">← Retour</a>
    <div style="flex:1;text-align:center;font-size:1rem;font-weight:700;letter-spacing:.03em">Gestion des Recettes</div>
  </div>
  <div style="padding:1rem;display:flex;flex-direction:column;gap:1rem">
    <div style="background:#FFFDF7;border-radius:16px;padding:1rem;border:1px solid rgba(212,165,116,.3);box-shadow:0 2px 8px rgba(61,32,8,.06)">
      <div style="font-size:1rem;font-weight:700;color:#6B3A1F;margin-bottom:.8rem">Informations générales</div>
      <div style="display:flex;flex-direction:column;gap:.6rem;font-size:.85rem">
        <div><div style="font-weight:700;color:#6B3A1F;margin-bottom:.2rem">Nom de la recette <span style="color:#C93030">*</span></div><div style="border:2px solid #D4A574;border-radius:8px;padding:.55rem .75rem;background:#F5ECD7">ex : Saucisse Toulouse</div></div>
        <div><div style="font-weight:700;color:#6B3A1F;margin-bottom:.2rem">Produit fini associé <span style="color:#C93030">*</span></div><div style="border:2px solid #D4A574;border-radius:8px;padding:.55rem .75rem;background:#F5ECD7">Rechercher un produit fini…</div></div>
        <div style="display:flex;gap:.75rem">
          <div style="flex:1"><div style="font-weight:700;color:#6B3A1F;margin-bottom:.2rem">DLC (jours) <span style="color:#C93030">*</span> <span style="font-weight:400;color:#888;font-size:.78rem">— verrouillée à 3 jours</span></div><div style="border:2px solid #D4A574;border-radius:8px;padding:.55rem .75rem;background:#F5ECD7;max-width:120px;opacity:.7">3</div></div>
          <div style="flex:2"><div style="font-weight:700;color:#6B3A1F;margin-bottom:.2rem">Rendement de base</div><div style="display:flex;gap:.4rem"><div style="border:2px solid #D4A574;border-radius:8px;padding:.55rem .75rem;background:#F5ECD7;flex:1">ex : 1</div><div style="border:2px solid #D4A574;border-radius:8px;padding:.55rem .75rem;background:#F5ECD7;max-width:80px">kg</div></div></div>
        </div>
      </div>
    </div>
    <div style="background:#FFFDF7;border-radius:16px;padding:1rem;border:1px solid rgba(212,165,116,.3)">
      <div style="font-size:1rem;font-weight:700;color:#6B3A1F;margin-bottom:.6rem">Ingrédients</div>
      <div style="color:#888;font-style:italic;font-size:.85rem;margin-bottom:.7rem">Aucun ingrédient ajouté</div>
      <div style="background:#F5ECD7;border:2px dashed #D4A574;border-radius:12px;padding:.85rem;font-size:.82rem">
        <div style="font-size:.78rem;font-weight:700;color:#6B3A1F;text-transform:uppercase;letter-spacing:.04em;margin-bottom:.6rem">Ajouter un ingrédient</div>
        <div style="border:2px solid #D4A574;border-radius:8px;padding:.5rem .7rem;background:#FFFDF7;margin-bottom:.4rem">ex : Sel, Poivre, Viande bœuf…</div>
        <div style="display:flex;gap:.4rem;margin-bottom:.5rem"><div style="border:2px solid #D4A574;border-radius:8px;padding:.5rem .7rem;background:#FFFDF7;flex:1">ex : 500</div><div style="border:2px solid #D4A574;border-radius:8px;padding:.5rem .7rem;background:#FFFDF7;width:80px">g</div></div>
        <button style="width:100%;background:#6B3A1F;color:#F5ECD7;border:none;border-radius:8px;padding:.7rem;font-weight:700;font-size:.88rem">+ Ajouter cet ingrédient</button>
      </div>
    </div>
    <button style="width:100%;background:#2D7D46;color:#FFF;border:none;border-radius:12px;padding:.9rem;font-size:1.05rem;font-weight:700;box-shadow:0 4px 16px rgba(45,125,70,.25)">✓ Enregistrer la recette</button>
  </div>
</div>

---

## Section 1 — Informations générales

### Nom de la recette
Saisissez un nom clair et reconnaissable (ex. : `Saucisse Toulouse`, `Pâté de campagne`). Si vous laissez ce champ vide lors de la sélection du produit fini, il sera rempli automatiquement avec le nom du produit.

### Produit fini associé
Tapez les premières lettres dans le champ de recherche — une liste de suggestions apparaît :

<div style="position:relative;margin:.4rem 0 .8rem">
  <div style="border:2px solid #6B3A1F;border-radius:8px;padding:.55rem .75rem;background:#F5ECD7;font-size:.88rem">sauci</div>
  <div style="background:#FFFDF7;border:2px solid #6B3A1F;border-radius:8px;margin-top:4px;font-size:.88rem">
    <div style="padding:.55rem .75rem;border-bottom:1px solid rgba(61,32,8,.08);color:#3D2008">Saucisse Toulouse (PC-TR-001)</div>
    <div style="padding:.55rem .75rem;color:#3D2008">Saucisse Merguez (PC-TR-002)</div>
  </div>
</div>

Tapez sur le produit dans la liste. Un tag vert confirme la sélection :

<div style="display:inline-flex;align-items:center;gap:.5rem;background:#e8f5ee;border:1.5px solid #2D7D46;border-radius:20px;padding:.35rem .85rem;font-size:.85rem;font-weight:600;color:#2D7D46;margin:.3rem 0 .5rem">
  Saucisse Toulouse (PC-TR-001) <button style="background:none;border:none;color:#2D7D46;font-size:.85rem;cursor:pointer;padding:0 .2rem">✕</button>
</div>

Après la sélection, un encart de détails s'affiche (catégorie, destination, température de conservation).

Tapez **`✕`** sur le tag pour effacer et recommencer la recherche.

### DLC (en jours) — verrouillée à 3 jours
Ce champ affiche `3` et ne peut pas être modifié. La règle HACCP impose 3 jours maximum pour tous les produits transformés fabriqués en boucherie. Cette valeur est non négociable.

### Rendement de base
Indiquez la quantité produite par cette recette de base (ex. : `1 kg`). Ce rendement sert de référence dans le wizard de fabrication pour calculer les quantités proportionnelles si vous voulez produire plus ou moins.

**Exemple :** recette de base = 1 kg. Si l'opérateur veut produire 5 kg, le wizard multiplie automatiquement toutes les quantités d'ingrédients par 5.

---

## Section 2 — Ingrédients

### Le tableau des ingrédients

Une fois les premiers ingrédients ajoutés, un tableau s'affiche :

<div style="overflow-x:auto;border-radius:8px;border:1.5px solid #D4A574;margin:.4rem 0 .8rem">
<table style="width:100%;border-collapse:collapse;font-size:.85rem">
<thead><tr style="background:#6B3A1F;color:#F5ECD7">
  <th style="padding:.5rem .7rem;text-align:left">Ingrédient</th>
  <th style="padding:.5rem .7rem;text-align:left">Quantité</th>
  <th style="padding:.5rem .7rem;text-align:left">Unité</th>
  <th style="padding:.5rem .7rem;text-align:left">%</th>
  <th style="padding:.5rem .7rem"></th>
</tr></thead>
<tbody>
<tr style="cursor:pointer"><td style="padding:.5rem .7rem;font-weight:600;color:#3D2008;border-top:1px solid rgba(61,32,8,.08)">Porc haché</td><td style="padding:.5rem .7rem;color:#6B3A1F">800</td><td style="padding:.5rem .7rem;color:#6B3A1F">g</td><td style="padding:.5rem .7rem;font-weight:700;color:#2D7D46">80,0%</td><td style="padding:.5rem .7rem;text-align:right"><button style="border:1.5px solid #C93030;border-radius:6px;color:#C93030;background:none;padding:.3rem .5rem;font-size:1rem">✕</button></td></tr>
<tr style="cursor:pointer"><td style="padding:.5rem .7rem;font-weight:600;color:#3D2008;border-top:1px solid rgba(61,32,8,.08)">Sel fin <span style="display:inline-block;font-size:10px;font-weight:700;background:rgba(107,58,31,.12);color:#6B3A1F;border-radius:20px;padding:1px 7px;margin-left:4px">nouveau</span></td><td style="padding:.5rem .7rem;color:#6B3A1F">18</td><td style="padding:.5rem .7rem;color:#6B3A1F">g</td><td style="padding:.5rem .7rem;font-weight:700;color:#2D7D46">1,8%</td><td style="padding:.5rem .7rem;text-align:right"><button style="border:1.5px solid #C93030;border-radius:6px;color:#C93030;background:none;padding:.3rem .5rem;font-size:1rem">✕</button></td></tr>
<tr style="cursor:pointer"><td style="padding:.5rem .7rem;font-weight:600;color:#3D2008;border-top:1px solid rgba(61,32,8,.08)">Épices Toulouse</td><td style="padding:.5rem .7rem;color:#6B3A1F">12</td><td style="padding:.5rem .7rem;color:#6B3A1F">g</td><td style="padding:.5rem .7rem;font-weight:700;color:#2D7D46">1,2%</td><td style="padding:.5rem .7rem;text-align:right"><button style="border:1.5px solid #C93030;border-radius:6px;color:#C93030;background:none;padding:.3rem .5rem;font-size:1rem">✕</button></td></tr>
</tbody>
</table>
</div>

- La colonne **%** calcule automatiquement la proportion en poids de chaque ingrédient par rapport au total (tous les poids sont convertis en kg pour le calcul). Les ingrédients en "pièces" affichent `—` dans cette colonne.
- **Taper sur une ligne** ouvre la modale pour modifier la quantité ou l'unité.
- Le bouton **`✕`** rouge en fin de ligne supprime l'ingrédient.
- Le badge <span style="display:inline-block;font-size:11px;font-weight:700;background:rgba(107,58,31,.12);color:#6B3A1F;border-radius:20px;padding:1px 7px">nouveau</span> indique un ingrédient qui n'existait pas encore dans le catalogue — il sera créé automatiquement à l'enregistrement de la recette.

> **En mode modification d'une recette existante :** si un ingrédient a déjà été utilisé dans une production passée, sa suppression est **bloquée** pour ne pas effacer la traçabilité. Vous pouvez toujours modifier sa quantité ou son unité, mais pas le supprimer.

### Ajouter un ingrédient

Le formulaire d'ajout est dans le bloc avec la bordure en pointillés :

**1 — Produit :**
Commencez à taper dans le champ — les produits du catalogue s'affichent en suggestions. Deux cas possibles :
- **Vous sélectionnez un produit dans la liste** → il est ajouté directement au tableau.
- **Vous tapez un nom libre qui n'existe pas** → la fenêtre "Nouvel ingrédient" s'ouvre (voir ci-dessous).

**2 — Quantité :** saisissez le nombre (décimal accepté). Vous pouvez valider avec la touche Entrée.

**3 — Unité :** choisissez `kg`, `g`, `L` ou `pièce`.

**4 — Tapez `+ Ajouter cet ingrédient`** pour ajouter l'ingrédient au tableau.

---

## La fenêtre "Nouvel ingrédient"

S'ouvre automatiquement quand vous tapez le nom d'un ingrédient qui n'existe pas dans le catalogue. Elle vous permet de créer ce produit à la volée sans quitter la page recette.

<div style="background:#FFFDF7;border-radius:16px;padding:1.1rem 1.25rem;border:1.5px solid #D4A574;margin:.5rem 0 .9rem;max-width:450px">
  <div style="font-size:1rem;font-weight:700;color:#6B3A1F;margin-bottom:.4rem">Nouvel ingrédient</div>
  <div style="font-size:.82rem;color:#888;margin-bottom:.8rem;line-height:1.4">Cet ingrédient n'existe pas encore en base. Complétez les informations pour le créer.</div>
  <div style="display:flex;flex-direction:column;gap:.5rem;font-size:.85rem">
    <div><div style="font-weight:700;color:#6B3A1F;margin-bottom:.2rem">Nom <span style="color:#C93030">*</span></div><div style="border:2px solid #D4A574;border-radius:8px;padding:.5rem .7rem;background:#F5ECD7;opacity:.8">Sel fin</div></div>
    <div><div style="font-weight:700;color:#6B3A1F;margin-bottom:.2rem">Code unique <span style="font-weight:400;color:#888;font-size:.78rem">— généré automatiquement</span></div><div style="border:2px solid #D4A574;border-radius:8px;padding:.5rem .7rem;background:#F5ECD7;opacity:.6">sélectionnez une espèce…</div></div>
    <div><div style="font-weight:700;color:#6B3A1F;margin-bottom:.2rem">Catégorie <span style="color:#C93030">*</span></div><div style="border:2px solid #D4A574;border-radius:8px;padding:.5rem .7rem;background:#F5ECD7">Matière première</div></div>
    <div><div style="font-weight:700;color:#6B3A1F;margin-bottom:.2rem">Espèce <span style="color:#C93030">*</span></div><div style="border:2px solid #D4A574;border-radius:8px;padding:.5rem .7rem;background:#F5ECD7">— Sélectionner —</div></div>
    <div><div style="font-weight:700;color:#6B3A1F;margin-bottom:.2rem">Température de conservation <span style="color:#C93030">*</span></div><div style="border:2px solid #D4A574;border-radius:8px;padding:.5rem .7rem;background:#F5ECD7">Ambiant</div></div>
  </div>
  <div style="display:flex;gap:.5rem;margin-top:.8rem">
    <button style="flex:1;border:2px solid #D4A574;border-radius:8px;padding:.6rem;background:transparent;font-size:.85rem;font-weight:600;color:#3D2008">Annuler</button>
    <button style="flex:2;background:#6B3A1F;color:#F5ECD7;border:none;border-radius:8px;padding:.6rem;font-size:.88rem;font-weight:700">+ Ajouter l'ingrédient</button>
  </div>
</div>

| Champ | Obligatoire | À renseigner |
|---|---|---|
| **Nom** | — | Pré-rempli depuis votre saisie (lecture seule) |
| **Code unique** | — | Généré automatiquement dès que vous choisissez l'espèce |
| **Catégorie** | Oui ✱ | Choisir le type : `Matière première`, `Viande hachée`, `Pièces de viande`, `Préparation crue`, `Charcuterie` ou `Traiteur` |
| **Espèce** | Oui ✱ | Choisir l'espèce animale — déclenche la génération du code unique |
| **Abats** | Non | Cochez si c'est un produit abat (foie, langue, rognon…) |
| **Niveau de coupe** | Non | Ex. : `entier`, `demi`, `pavé`… |
| **Conditionnement** | Non | Défaut : `SOUS_VIDE` |
| **Type produit** | Non | `Brut` (matière première) ou `Fini` (transformé) |
| **DLC en jours** | Non | 0 = sans DLC |
| **Température de conservation** | Oui ✱ | `Ambiant`, `+4°C`, `-18°C` ou `+2°C / +4°C` |

> **Attention :** si vous oubliez de sélectionner l'**Espèce**, le champ clignote en rouge et un message *"Sélectionnez une espèce."* s'affiche pendant 2 secondes. Vous ne pouvez pas valider sans.

Tapez **`+ Ajouter l'ingrédient`** — il s'ajoute au tableau avec le badge `nouveau`. Tapez **`Annuler`** pour fermer sans créer.

---

## Modifier la quantité d'un ingrédient

Tapez sur une ligne du tableau d'ingrédients. Une petite fenêtre s'ouvre :

<div style="background:#FFFDF7;border-radius:16px;padding:1rem 1.25rem;border:1.5px solid #D4A574;margin:.4rem 0 .8rem;max-width:380px">
  <div style="font-size:1rem;font-weight:700;color:#6B3A1F;margin-bottom:.7rem">Modifier l'ingrédient</div>
  <div style="font-size:.85rem;margin-bottom:.6rem"><div style="font-weight:700;color:#6B3A1F;margin-bottom:.2rem">Ingrédient</div><div style="border:2px solid #D4A574;border-radius:8px;padding:.5rem .7rem;background:#F5ECD7;opacity:.8">Porc haché</div></div>
  <div style="display:flex;gap:.5rem;margin-bottom:.7rem">
    <div style="flex:2"><div style="font-size:.85rem;font-weight:700;color:#6B3A1F;margin-bottom:.2rem">Quantité</div><div style="border:2px solid #D4A574;border-radius:8px;padding:.5rem .7rem;background:#F5ECD7;font-size:.85rem">800</div></div>
    <div style="flex:1"><div style="font-size:.85rem;font-weight:700;color:#6B3A1F;margin-bottom:.2rem">Unité</div><div style="border:2px solid #D4A574;border-radius:8px;padding:.5rem .7rem;background:#F5ECD7;font-size:.85rem">g</div></div>
  </div>
  <div style="display:flex;gap:.5rem">
    <button style="flex:1;border:2px solid #D4A574;border-radius:8px;padding:.55rem;background:transparent;font-size:.85rem;font-weight:600;color:#3D2008">Annuler</button>
    <button style="flex:2;background:#6B3A1F;color:#F5ECD7;border:none;border-radius:8px;padding:.55rem;font-size:.88rem;font-weight:700">✓ Enregistrer</button>
  </div>
</div>

Vous pouvez modifier uniquement la **quantité** et l'**unité** — le nom de l'ingrédient ne peut pas être changé ici.

---

## Enregistrer la recette

Quand vous avez rempli les informations générales et ajouté au moins un ingrédient, tapez le bouton vert en bas :

<div style="margin:.4rem 0 .8rem"><button style="width:100%;background:#2D7D46;color:#FFF;border:none;border-radius:12px;padding:.9rem;font-size:1.05rem;font-weight:700;max-width:400px">✓ Enregistrer la recette</button></div>

Le système vérifie d'abord :
- Le nom de la recette est renseigné
- Un produit fini est sélectionné
- Au moins un ingrédient est présent

Si tout est bon, les éventuels ingrédients marqués `nouveau` sont créés en catalogue, puis la recette est sauvegardée.

Un message vert (toast) apparaît en bas de l'écran pour confirmer la réussite, et le formulaire se vide pour permettre la création d'une nouvelle recette.

---

## Modifier une recette existante

Pour modifier une recette déjà créée :
1. Allez dans le wizard Fabrication.
2. Tapez le bouton **`✏️ Gérer les recettes`**.
3. Tapez sur la recette à modifier dans la liste.
4. Le formulaire se remplit avec les données existantes, le titre devient `Modifier : [Nom recette]` et le bouton devient **`✓ Mettre à jour la recette`**.

> **Règle importante :** si un ingrédient de cette recette a déjà été utilisé dans une fabrication passée, son bouton `✕` de suppression est bloqué. Un message explique : *"Impossible de retirer l'ingrédient « [Nom] » : il est utilisé dans une fabrication existante (traçabilité HACCP)."* Vous pouvez toujours modifier sa quantité via la modale d'édition.

---

## Règles invisibles importantes

**DLC de 3 jours — non modifiable :** la règle HACCP impose que tout produit transformé en boucherie ait une durée de vie de 3 jours maximum. Cette règle s'applique aussi dans le wizard de fabrication : la DLC du produit fini est calculée automatiquement.

**DLC plafonnée par les ingrédients :** lors d'une fabrication dans le wizard, si un lot d'ingrédient utilisé expire avant la DLC théorique des 3 jours, la DLC finale du produit fini est réduite en conséquence. Un avertissement orange s'affiche dans le wizard.

**Numéro de lot interne :** chaque fabrication reçoit automatiquement un numéro de lot au format `MC-AAAAMMJJ-XXXX` (ex. : `MC-20260514-0001`). Ce numéro figure sur l'étiquette thermique et dans l'historique.

**Ordre FIFO :** dans le wizard, les lots d'ingrédients proposés sont toujours triés avec le lot expirant le plus tôt en premier. Pour être proposé, un lot doit avoir été correctement réceptionné (clôturé et conforme), ne pas être expiré, et ne pas avoir déjà été traité.

---

## Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Ce que ça veut dire | Que faire |
|---|---|---|
| *"Le nom de la recette est obligatoire."* | Champ Nom vide | Saisissez un nom de recette |
| *"Sélectionnez un produit fini associé."* | Produit fini non choisi | Tapez dans le champ de recherche et sélectionnez un produit dans la liste |
| *"Ajoutez au moins un ingrédient avant d'enregistrer."* | Tableau vide | Ajoutez au moins un ingrédient |
| Champ Espèce clignote rouge | Espèce oubliée dans "Nouvel ingrédient" | Sélectionnez l'espèce dans le menu |
| *"Saisissez une quantité valide."* | Quantité ≤ 0 | Saisissez un nombre supérieur à zéro |
| *"Impossible de retirer l'ingrédient…"* | Ingrédient déjà utilisé en production | Modifiez sa quantité plutôt que le supprimer |
| *"Impossible de charger la liste des produits."* | Problème de connexion | Vérifiez que le Raspberry Pi est allumé et rechargez la page |
| Message rouge après enregistrement | Erreur de sauvegarde | Vérifiez la connexion et réessayez |

---

---

---

# Module 12 — Stock Unifié FIFO (📋)

<div style="background:rgba(212,165,116,.15);border-left:4px solid #D4A574;border-radius:0 8px 8px 0;padding:.65rem 1rem;font-size:.9rem;line-height:1.5;color:#3D2008;margin-bottom:1.2rem">
<strong style="color:#6B3A1F">Accès :</strong> Hub principal → tuile <strong>📋 STOCK</strong> (ou directement <code>/inventaire.html</code>)
</div>

Cette page affiche **tout le stock en un seul endroit**, quelle que soit son origine. Elle permet de savoir en un coup d'œil ce qui est disponible, ce qui va expirer bientôt, et de traiter les produits vendus, consommés ou jetés.

---

## Les quatre types de produits en stock

| Icône | Ce que c'est |
|---|---|
| 📦 | Matières premières reçues de fournisseurs |
| 🔪 | Produits fabriqués en atelier (non cuits) |
| 🔥 | Produits cuits, pas encore passés au refroidissement |
| ❄️ | Produits cuits puis refroidis — prêts à être vendus |

Les lots sont triés automatiquement par **ordre FIFO** : le produit dont la DLC est la plus proche apparaît en premier. Les produits déjà traités (vendus, jetés…) n'apparaissent pas.

---

## Le bandeau de statistiques

<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem;margin:.4rem 0 .8rem">
  <div style="background:#FFF;border-radius:12px;padding:.55rem .7rem;text-align:center;border-left:4px solid #6B3A1F"><div style="font-size:1.5rem;font-weight:800;color:#3D2008">24</div><div style="font-size:.7rem;color:#6b7280;margin-top:2px">Total</div></div>
  <div style="background:#FFF;border-radius:12px;padding:.55rem .7rem;text-align:center;border-left:4px solid #6b7280"><div style="font-size:1.5rem;font-weight:800;color:#3D2008">12</div><div style="font-size:.7rem;color:#6b7280;margin-top:2px">📦 Réceptions</div></div>
  <div style="background:#FFF;border-radius:12px;padding:.55rem .7rem;text-align:center;border-left:4px solid #16a34a"><div style="font-size:1.5rem;font-weight:800;color:#3D2008">5</div><div style="font-size:.7rem;color:#6b7280;margin-top:2px">🔪 Fabrications</div></div>
  <div style="background:#FFF;border-radius:12px;padding:.55rem .7rem;text-align:center;border-left:4px solid #d97706"><div style="font-size:1.5rem;font-weight:800;color:#3D2008">3</div><div style="font-size:.7rem;color:#6b7280;margin-top:2px">🔥 Cuissons</div></div>
  <div style="background:#FFF;border-radius:12px;padding:.55rem .7rem;text-align:center;border-left:4px solid #2563eb"><div style="font-size:1.5rem;font-weight:800;color:#3D2008">4</div><div style="font-size:.7rem;color:#6b7280;margin-top:2px">❄️ Refroidis</div></div>
  <div style="background:#FFF;border-radius:12px;padding:.55rem .7rem;text-align:center;border-left:4px solid #dc2626"><div style="font-size:1.5rem;font-weight:800;color:#dc2626">6</div><div style="font-size:.7rem;color:#6b7280;margin-top:2px">⏰ ≤ 3 jours</div></div>
</div>

Le compteur **⏰ ≤ 3 jours** (en rouge) attire l'attention sur les produits qui vont bientôt expirer. Il ne compte que les produits encore valides — les produits déjà périmés ne sont pas inclus dans ce compteur.

---

## Le code couleur des cartes

Chaque lot est affiché sur une carte avec une **bande colorée à gauche** et un **badge** indiquant les jours restants :

<div style="display:flex;flex-direction:column;gap:.4rem;margin:.4rem 0 .8rem">
  <div style="display:grid;grid-template-columns:56px 1fr auto;gap:.7rem;align-items:center;background:#f3f4f6;border-radius:12px;padding:.6rem;border-left:6px solid #1f2937">
    <div style="font-size:1.8rem;text-align:center">📦</div>
    <div><div style="font-size:.9rem;font-weight:700;color:#3D2008">Côte de bœuf</div><div style="font-size:.78rem;color:#4b5563">Lot REC-001 · 3,5 kg · Frn : Bovins du Sud · Origine : 10/05/2026</div><div style="font-size:.7rem;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;margin-top:3px">Pièces de viande</div></div>
    <div style="text-align:right"><span style="background:#1f2937;color:#FFF;font-size:.85rem;font-weight:800;padding:.2rem .55rem;border-radius:6px">Périmé J-2</span><div style="font-size:.7rem;color:#6b7280;margin-top:4px">DLC : 12/05/2026</div></div>
  </div>
  <div style="display:grid;grid-template-columns:56px 1fr auto;gap:.7rem;align-items:center;background:#fef2f2;border-radius:12px;padding:.6rem;border-left:6px solid #dc2626">
    <div style="font-size:1.8rem;text-align:center">❄️</div>
    <div><div style="font-size:.9rem;font-weight:700;color:#3D2008">Poulet rôti</div><div style="font-size:.78rem;color:#4b5563">Lot MC-20260514-0001 · 8 kg · Origine : 14/05/2026</div></div>
    <div style="text-align:right"><span style="background:#fecaca;color:#991b1b;font-size:.85rem;font-weight:800;padding:.2rem .55rem;border-radius:6px">Aujourd'hui</span><div style="font-size:.7rem;color:#6b7280;margin-top:4px">DLC : 17/05/2026</div></div>
  </div>
  <div style="display:grid;grid-template-columns:56px 1fr auto;gap:.7rem;align-items:center;background:#FFF;border-radius:12px;padding:.6rem;border-left:6px solid #ea580c">
    <div style="font-size:1.8rem;text-align:center">🔪</div>
    <div><div style="font-size:.9rem;font-weight:700;color:#3D2008">Saucisse Toulouse</div><div style="font-size:.78rem;color:#4b5563">Lot MC-20260513-0003 · 5,2 kg · Origine : 13/05/2026</div></div>
    <div style="text-align:right"><span style="background:#fed7aa;color:#9a3412;font-size:.85rem;font-weight:800;padding:.2rem .55rem;border-radius:6px">J+2</span><div style="font-size:.7rem;color:#6b7280;margin-top:4px">DLC : 16/05/2026</div></div>
  </div>
  <div style="display:grid;grid-template-columns:56px 1fr auto;gap:.7rem;align-items:center;background:#FFF;border-radius:12px;padding:.6rem;border-left:6px solid #eab308">
    <div style="font-size:1.8rem;text-align:center">📦</div>
    <div><div style="font-size:.9rem;font-weight:700;color:#3D2008">Veau haché</div><div style="font-size:.78rem;color:#4b5563">Lot VX-0514-07 · 2 kg · Frn : Veau Premium</div></div>
    <div style="text-align:right"><span style="background:#fef9c3;color:#854d0e;font-size:.85rem;font-weight:800;padding:.2rem .55rem;border-radius:6px">J+5</span><div style="font-size:.7rem;color:#6b7280;margin-top:4px">DLC : 19/05/2026</div></div>
  </div>
  <div style="display:grid;grid-template-columns:56px 1fr auto;gap:.7rem;align-items:center;background:#FFF;border-radius:12px;padding:.6rem;border-left:6px solid #16a34a">
    <div style="font-size:1.8rem;text-align:center">📦</div>
    <div><div style="font-size:.9rem;font-weight:700;color:#3D2008">Agneau gigot</div><div style="font-size:.78rem;color:#4b5563">Lot AGN-0510-02 · 4,8 kg · Frn : Agneau de Sisteron</div></div>
    <div style="text-align:right"><span style="background:#dcfce7;color:#166534;font-size:.85rem;font-weight:800;padding:.2rem .55rem;border-radius:6px">J+12</span><div style="font-size:.7rem;color:#6b7280;margin-top:4px">DLC : 26/05/2026</div></div>
  </div>
</div>

| Couleur de la bande | Urgence | Badge |
|---|---|---|
| ⬛ Noir (fond gris) | **Périmé** | `Périmé J-X` |
| 🔴 Rouge (fond rosé) | **0 ou 1 jour** | `Aujourd'hui` ou `Demain` |
| 🟠 Orange | **2 à 3 jours** | `J+2`, `J+3` |
| 🟡 Jaune | **4 à 7 jours** | `J+4`… `J+7` |
| 🟢 Vert | **8 jours ou plus** | `J+8`, `J+12`… |
| ⬜ Gris (semi-transparent) | **Sans DLC** | `—` |

---

## Filtrer le stock

La zone de filtres se trouve sous le bandeau de statistiques.

### Filtres principaux (rechargent la liste)

Ces filtres affectent l'ensemble des données récupérées — ils déclenchent un rechargement complet de la liste :

| Filtre | Options |
|---|---|
| **Type** | Tous / 📦 Bruts (réceptions) / 🔪🔥❄️ Finis (transformés) |
| **Catégorie** | Toutes + les catégories présentes dans le stock |
| **DLC max** | Saisir une date — n'affiche que les lots expirant avant cette date |
| **Inclure périmés** | Case à cocher — par défaut, les périmés sont masqués |

### Filtres rapides (instantanés, sans attente)

Ces filtres s'appliquent instantanément sur les données déjà chargées :

| Filtre | Notes |
|---|---|
| **Recherche** | Tapez le nom d'un produit ou un numéro de lot — la liste se filtre après un bref délai. Tapez le bouton **`▾`** pour afficher toutes les suggestions disponibles. |
| **Espèce** | Menu avec les espèces présentes dans le stock chargé |
| **Tri** | DLC ↑ (urgent en premier — par défaut) / DLC ↓ / Nom A→Z / Nom Z→A / Plus récent / Plus ancien |

**Bouton `Réinitialiser`** : remet tous les filtres à zéro et recharge la liste depuis le début.

> **Astuce :** si un produit ne s'affiche pas après un filtre rapide (Espèce, Recherche), vérifiez que les filtres principaux (Type, Catégorie) ne l'excluent pas. Tapez `Réinitialiser` pour tout remettre à zéro.

---

## Corriger un lot — DLC ou Quantité

Tapez directement sur une carte pour ouvrir la fenêtre de modification :

<div style="background:#FFFDF7;border-radius:12px;overflow:hidden;border:1.5px solid #D4A574;margin:.5rem 0 .9rem;max-width:420px">
  <div style="background:#6B3A1F;color:#FFF;padding:.7rem 1rem;display:flex;align-items:center;justify-content:space-between">
    <div style="font-size:.95rem;font-weight:800">Modifier le produit</div>
    <button style="background:transparent;border:none;color:#FFF;font-size:1.3rem;cursor:pointer">✕</button>
  </div>
  <div style="padding:1rem;font-size:.88rem">
    <div style="font-size:1rem;font-weight:700;color:#3D2008;margin-bottom:.6rem">Poulet rôti</div>
    <div style="display:flex;align-items:center;gap:.5rem;background:#f5ede0;border-radius:8px;border:1px solid #d8c9b2;padding:.45rem .7rem;margin-bottom:.8rem">
      <div style="font-size:.7rem;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap">N° de lot</div>
      <div style="font-size:.85rem;font-weight:700;color:#6B3A1F;flex:1">MC-20260514-0001</div>
      <div style="font-size:.85rem;color:#9ca3af">🔒</div>
    </div>
    <div style="margin-bottom:.5rem"><div style="font-weight:600;font-size:.82rem;color:#6B3A1F;margin-bottom:.25rem">DLC</div><div style="border:1.5px solid #d8c9b2;border-radius:8px;padding:.55rem .75rem;background:#FFF">2026-05-17</div></div>
    <div style="margin-bottom:.8rem"><div style="font-weight:600;font-size:.82rem;color:#6B3A1F;margin-bottom:.25rem">Quantité (kg)</div><div style="border:1.5px solid #d8c9b2;border-radius:8px;padding:.55rem .75rem;background:#FFF">8</div></div>
    <button style="width:100%;background:#2D7D46;color:#FFF;border:none;border-radius:12px;padding:.85rem;font-size:.95rem;font-weight:700;margin-bottom:.4rem">Enregistrer les modifications</button>
    <button style="width:100%;background:#eaf3ff;color:#1a5fb4;border:1.5px solid #1a5fb4;border-radius:12px;padding:.75rem;font-size:.9rem;font-weight:700">🖨️ Imprimer étiquette</button>
  </div>
</div>

**Ce que vous pouvez modifier :**
- **DLC** : corrigez la date si une erreur a été faite lors de la saisie
- **Quantité** : corrigez le poids si une erreur a été faite *(non disponible pour les produits refroidis — leur quantité est héritée de la cuisson)*

**Ce que vous ne pouvez PAS modifier :**
- **N° de lot** : le numéro de lot est **verrouillé définitivement** (icône 🔒). Il ne peut jamais être changé pour garantir la traçabilité. Si une erreur a été faite sur le lot, il faut créer un nouvel enregistrement.

**Bouton `🖨️ Imprimer étiquette`** : imprime une étiquette thermique 62mm à partir des données affichées, avec le tag approprié selon l'origine (📦 réception = sans tag / 🔪 `[FABRIQUÉ]` / 🔥 `[CUIT]` / ❄️ `[REFROIDI]`).

---

## Traiter des produits — Mode Gestion

Le Mode Gestion permet de déclarer la sortie de stock de un ou plusieurs produits en une seule opération (vente, consommation ou jet).

### Activer le Mode Gestion

Tapez le bouton **`✏️ Gérer`** dans la barre en haut à droite. L'interface change :
- Chaque carte affiche une **case à cocher**
- Taper sur une carte **sélectionne/désélectionne** le lot (plus d'ouverture de modale)
- Une **barre d'action** apparaît en bas de l'écran

<div style="background:#6B3A1F;color:#FFF;border-radius:10px;padding:.65rem 1rem;display:flex;align-items:center;justify-content:space-between;gap:.5rem;margin:.4rem 0 .7rem;max-width:480px">
  <div style="font-size:.9rem;font-weight:700;flex:1">3 produit(s) sélectionné(s)</div>
  <div style="display:flex;gap:.5rem">
    <button style="background:#FFF;color:#6B3A1F;border:2px solid rgba(255,255,255,.6);padding:.5rem .9rem;border-radius:8px;font-size:.82rem;font-weight:700">✏️ Modifier</button>
    <button style="background:#dc2626;color:#FFF;border:none;padding:.5rem .9rem;border-radius:8px;font-size:.82rem;font-weight:700">🗑️ Traiter la sélection</button>
  </div>
</div>

- **`✏️ Modifier`** : actif seulement si **exactement 1 article** est sélectionné — ouvre la fenêtre de modification.
- **`🗑️ Traiter la sélection`** : actif dès qu'**au moins 1** article est sélectionné — ouvre la fenêtre de traitement.

Pour **désactiver** le Mode Gestion, tapez à nouveau **`✏️ Gérer`** — la sélection est effacée.

### La fenêtre de traitement

<div style="background:#FFFDF7;border-radius:12px;overflow:hidden;border:1.5px solid #D4A574;margin:.5rem 0 .9rem;max-width:460px">
  <div style="background:#6B3A1F;color:#FFF;padding:.7rem 1rem;display:flex;align-items:center;justify-content:space-between">
    <div style="font-size:.95rem;font-weight:800">Traitement des produits sélectionnés</div>
    <button style="background:transparent;border:none;color:#FFF;font-size:1.3rem">✕</button>
  </div>
  <div style="padding:.9rem 1rem;font-size:.85rem">
    <div style="font-weight:700;color:#6B3A1F;margin-bottom:.6rem">3 produit(s) sélectionné(s) à traiter</div>
    <div style="border:1px solid #e8d9c4;border-radius:8px;margin-bottom:.75rem;max-height:160px;overflow-y:auto">
      <div style="display:grid;grid-template-columns:26px 26px 1fr auto;gap:3px 8px;padding:.5rem .7rem;border-bottom:1px solid #f0e8dc;align-items:center"><input type="checkbox" checked style="width:18px;height:18px"><span>📦</span><span style="font-weight:600;font-size:.82rem;color:#3D2008">Côte de bœuf</span><span style="font-size:.8rem;font-weight:700;color:#dc2626">12/05</span></div>
      <div style="display:grid;grid-template-columns:26px 26px 1fr auto;gap:3px 8px;padding:.5rem .7rem;border-bottom:1px solid #f0e8dc;align-items:center"><input type="checkbox" checked style="width:18px;height:18px"><span>🔪</span><span style="font-weight:600;font-size:.82rem;color:#3D2008">Saucisse Toulouse</span><span style="font-size:.8rem;font-weight:700;color:#9a3412">J+2</span></div>
      <div style="display:grid;grid-template-columns:26px 26px 1fr auto;gap:3px 8px;padding:.5rem .7rem;align-items:center"><input type="checkbox" checked style="width:18px;height:18px"><span>❄️</span><span style="font-weight:600;font-size:.82rem;color:#3D2008">Poulet rôti</span><span style="font-size:.8rem;font-weight:700;color:#991b1b">Auj.</span></div>
    </div>
    <div style="font-weight:600;font-size:.82rem;color:#6B3A1F;margin-bottom:.3rem">Prénom opérateur <span style="color:#C93030">*</span></div>
    <select style="width:100%;border:1.5px solid #d8c9b2;border-radius:8px;padding:.5rem .7rem;background:#FFF;font-size:.85rem;margin-bottom:.5rem"><option>Sélectionner…</option><option>Émile</option></select>
    <div style="font-weight:600;font-size:.82rem;color:#6B3A1F;margin-bottom:.35rem">Devenir <span style="color:#C93030">*</span></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:.4rem;margin-bottom:.5rem">
      <button style="padding:.7rem .4rem;border-radius:12px;border:2px solid #6B3A1F;background:#6B3A1F;font-size:.85rem;font-weight:600;color:#FFF;min-height:52px">🗑️ Jeté</button>
      <button style="padding:.7rem .4rem;border-radius:12px;border:2px solid #d8c9b2;background:#FFF;font-size:.85rem;font-weight:600;color:#3D2008;min-height:52px">💰 Vendu</button>
      <button style="padding:.7rem .4rem;border-radius:12px;border:2px solid #d8c9b2;background:#FFF;font-size:.85rem;font-weight:600;color:#3D2008;min-height:52px">✅ Consommé</button>
      <button style="padding:.7rem .4rem;border-radius:12px;border:2px solid #d8c9b2;background:#FFF;font-size:.85rem;font-weight:600;color:#3D2008;min-height:52px">❓ Autre</button>
    </div>
    <div style="font-weight:600;font-size:.82rem;color:#6B3A1F;margin-bottom:.25rem">Commentaire <span style="font-weight:400;color:#888;font-size:.78rem">(optionnel)</span></div>
    <textarea style="width:100%;min-height:52px;border:1.5px solid #d8c9b2;border-radius:8px;padding:.5rem .7rem;font-size:.82rem;box-sizing:border-box;margin-bottom:.5rem" placeholder="Raison, observations…"></textarea>
    <button style="width:100%;background:#2D7D46;color:#FFF;border:none;border-radius:12px;padding:.9rem;font-size:.95rem;font-weight:700">Confirmer le traitement</button>
  </div>
</div>

**Étapes de traitement :**
1. **Vérifiez la liste** des produits dans la fenêtre. Vous pouvez décocher individuellement un produit si vous avez changé d'avis.
2. **Sélectionnez votre prénom** dans le menu Opérateur.
3. **Choisissez le devenir** en tapant un des 4 boutons : `🗑️ Jeté`, `💰 Vendu`, `✅ Consommé` ou `❓ Autre`. Le bouton sélectionné prend un fond sombre.
4. **Commentaire** (facultatif) : précisez la raison, la quantité vendue, etc.
5. Tapez **`Confirmer le traitement`**.

Après confirmation, les produits traités **disparaissent instantanément du stock**. Un message indique le nombre de produits traités. Le stock est rechargé automatiquement.

> **Attention :** cette action est définitive. Les produits traités ne réapparaissent plus dans le stock. Si vous avez fait une erreur, contactez le responsable — il peut annuler un traitement depuis le calendrier DLC.

---

## Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Ce que ça veut dire | Que faire |
|---|---|---|
| *"Erreur de chargement : [détail]"* | Le serveur ne répond pas | Vérifiez que le Raspberry Pi est allumé et rechargez |
| *"Aucun produit en stock pour ces filtres."* | Filtres trop restrictifs | Tapez `Réinitialiser` pour tout afficher |
| *"La date DLC est obligatoire."* | Champ DLC vidé dans la modale de modification | Saisissez une date de DLC valide |
| *"Quantité invalide."* | Valeur incorrecte dans la modale de modification | Saisissez un nombre supérieur ou égal à 0 |
| Bouton `✏️ Modifier` grisé en mode gestion | 0 ou 2+ articles sélectionnés | Sélectionnez exactement 1 seul article |
| Bouton `🗑️ Traiter la sélection` grisé | Aucun article sélectionné | Tapez au moins une carte pour la sélectionner |
| Message rouge lors du traitement | Erreur d'enregistrement | Vérifiez la connexion et réessayez |

---

---

# Module 13 — Calendrier DLC

Le **Calendrier DLC** est le tableau de bord des dates limites de consommation. Il rassemble sur un seul écran **tous les produits en stock** — qu'ils viennent d'une réception, d'une fabrication, d'une cuisson ou d'un refroidissement — et les positionne sur un calendrier coloré selon leur urgence. C'est l'outil principal pour décider chaque jour quels produits vendre en priorité, lesquels jeter, lesquels sont encore tranquilles.

**Accès :** Hub principal → **CALENDRIER DLC** (ou directement `/dlc.html`).

---

## L'écran d'accueil — Vue Mois (par défaut)

À l'ouverture, l'écran affiche le **mois courant** sous forme de grille semblable à un agenda mural :

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;overflow:hidden;margin:.5rem 0 .9rem">
  <!-- Header -->
  <div style="background:#6B3A1F;color:#FFF;padding:.7rem 1rem;display:flex;align-items:center;justify-content:space-between">
    <span style="font-size:.82rem;background:rgba(255,255,255,.15);padding:.35rem .7rem;border-radius:8px">← Hub</span>
    <span style="font-weight:700;letter-spacing:.5px;font-size:.95rem">CALENDRIER DLC</span>
    <span style="font-size:.95rem;font-variant-numeric:tabular-nums">09:42</span>
  </div>
  <!-- Toolbar -->
  <div style="background:#FFFDF7;border-bottom:1px solid #e8d9c4;padding:.6rem .8rem;display:flex;flex-wrap:wrap;gap:.6rem;align-items:center">
    <div style="display:flex;gap:4px;background:#f0e8dc;padding:4px;border-radius:12px">
      <span style="padding:.5rem .9rem;border-radius:8px;font-size:.82rem;font-weight:600;color:#6B3A1F;background:transparent">Semaine</span>
      <span style="padding:.5rem .9rem;border-radius:8px;font-size:.82rem;font-weight:700;background:#6B3A1F;color:#FFF;box-shadow:0 2px 6px rgba(107,58,31,.2)">Mois</span>
      <span style="padding:.5rem .9rem;border-radius:8px;font-size:.82rem;font-weight:600;color:#6B3A1F;background:transparent">Annuel</span>
    </div>
    <div style="display:flex;align-items:center;gap:.6rem">
      <span style="border:1.5px solid #6B3A1F;color:#6B3A1F;width:44px;height:44px;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;font-size:1.6rem;font-weight:700">‹</span>
      <span style="font-size:1.05rem;font-weight:700;min-width:9em;text-align:center">Mai 2026</span>
      <span style="border:1.5px solid #6B3A1F;color:#6B3A1F;width:44px;height:44px;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;font-size:1.6rem;font-weight:700">›</span>
      <span style="background:#6B3A1F;color:#FFF;padding:.5rem 1rem;border-radius:12px;font-weight:600;font-size:.85rem">Aujourd'hui</span>
    </div>
  </div>
  <!-- Légende -->
  <div style="background:#F5ECD7;border-bottom:1px solid #e8d9c4;padding:.4rem .8rem;display:flex;flex-wrap:wrap;gap:.4rem">
    <span style="background:#C93030;color:#FFF;padding:.2rem .6rem;border-radius:20px;font-size:.78rem;font-weight:700">Expiré / critique</span>
    <span style="background:#E8913A;color:#FFF;padding:.2rem .6rem;border-radius:20px;font-size:.78rem;font-weight:700">Urgent</span>
    <span style="background:#E8C83A;color:#3D2008;padding:.2rem .6rem;border-radius:20px;font-size:.78rem;font-weight:700">Attention</span>
    <span style="background:#2D7D46;color:#FFF;padding:.2rem .6rem;border-radius:20px;font-size:.78rem;font-weight:700">OK</span>
    <span style="background:#888;color:#FFF;padding:.2rem .6rem;border-radius:20px;font-size:.78rem;font-weight:700">Traité</span>
  </div>
  <!-- Calendrier -->
  <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:5px;padding:6px;background:#e8d9c4">
    <div style="text-align:center;font-weight:700;font-size:.75rem;color:#6B3A1F;background:#F5ECD7;border-radius:6px;padding:.4rem 0">LUN</div>
    <div style="text-align:center;font-weight:700;font-size:.75rem;color:#6B3A1F;background:#F5ECD7;border-radius:6px;padding:.4rem 0">MAR</div>
    <div style="text-align:center;font-weight:700;font-size:.75rem;color:#6B3A1F;background:#F5ECD7;border-radius:6px;padding:.4rem 0">MER</div>
    <div style="text-align:center;font-weight:700;font-size:.75rem;color:#6B3A1F;background:#F5ECD7;border-radius:6px;padding:.4rem 0">JEU</div>
    <div style="text-align:center;font-weight:700;font-size:.75rem;color:#6B3A1F;background:#F5ECD7;border-radius:6px;padding:.4rem 0">VEN</div>
    <div style="text-align:center;font-weight:700;font-size:.75rem;color:#6B3A1F;background:#F5ECD7;border-radius:6px;padding:.4rem 0">SAM</div>
    <div style="text-align:center;font-weight:700;font-size:.75rem;color:#6B3A1F;background:#F5ECD7;border-radius:6px;padding:.4rem 0">DIM</div>
    <!-- Ligne 1 : jours du mois précédent grisés + début mai -->
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;opacity:.35"><span style="font-weight:700;font-size:.85rem">27</span></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;opacity:.35"><span style="font-weight:700;font-size:.85rem">28</span></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;opacity:.35"><span style="font-weight:700;font-size:.85rem">29</span></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;opacity:.35"><span style="font-weight:700;font-size:.85rem">30</span></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px"><span style="font-weight:700;font-size:.85rem">1</span></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px"><span style="font-weight:700;font-size:.85rem">2</span></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px"><span style="font-weight:700;font-size:.85rem">3</span></div>
    <!-- Ligne 2 -->
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem">4</span></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem">5</span></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem">6</span></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem">7</span></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem">8</span></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem">9</span><div style="display:flex;flex-wrap:wrap;gap:3px;margin-top:auto"><span style="background:#2D7D46;color:#FFF;padding:2px 7px;border-radius:20px;font-size:.72rem;font-weight:700">🟢 3</span></div></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem">10</span></div>
    <!-- Ligne 3 — semaine avec le 14 (aujourd'hui) -->
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem">11</span></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem">12</span></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem">13</span></div>
    <div style="background:#FFFDF7;border:2px solid #6B3A1F;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem;color:#6B3A1F">14</span><div style="display:flex;flex-wrap:wrap;gap:3px;margin-top:auto"><span style="background:#C93030;color:#FFF;padding:2px 7px;border-radius:20px;font-size:.72rem;font-weight:700">🔴 2</span><span style="background:#E8913A;color:#FFF;padding:2px 7px;border-radius:20px;font-size:.72rem;font-weight:700">🟠 1</span></div></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem">15</span><div style="display:flex;flex-wrap:wrap;gap:3px;margin-top:auto"><span style="background:#E8913A;color:#FFF;padding:2px 7px;border-radius:20px;font-size:.72rem;font-weight:700">🟠 2</span></div></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem">16</span><div style="display:flex;flex-wrap:wrap;gap:3px;margin-top:auto"><span style="background:#E8C83A;color:#3D2008;padding:2px 7px;border-radius:20px;font-size:.72rem;font-weight:700">🟡 1</span></div></div>
    <div style="background:#FFFDF7;border-radius:8px;min-height:80px;padding:5px;display:flex;flex-direction:column;gap:3px"><span style="font-weight:700;font-size:.85rem">17</span><div style="display:flex;flex-wrap:wrap;gap:3px;margin-top:auto"><span style="background:#E8C83A;color:#3D2008;padding:2px 7px;border-radius:20px;font-size:.72rem;font-weight:700">🟡 2</span></div></div>
  </div>
</div>

### Lire le calendrier

Chaque case du calendrier représente un jour. Si des produits ont leur DLC ce jour-là, des **badges colorés** apparaissent en bas de la case :

| Badge | Signification | À faire |
|---|---|---|
| <span style="background:#C93030;color:#FFF;padding:1px 7px;border-radius:20px;font-size:.8rem;font-weight:700">🔴 2</span> | 2 produits **expirés ou critiques** (DLC aujourd'hui ou dépassée) | À traiter sans attendre |
| <span style="background:#E8913A;color:#FFF;padding:1px 7px;border-radius:20px;font-size:.8rem;font-weight:700">🟠 3</span> | 3 produits **urgents** (expire dans ≤ 3 jours) | Vendre ou utiliser en priorité |
| <span style="background:#E8C83A;color:#3D2008;padding:1px 7px;border-radius:20px;font-size:.8rem;font-weight:700">🟡 1</span> | 1 produit en **attention** (≤ 7 jours) | À surveiller |
| <span style="background:#2D7D46;color:#FFF;padding:1px 7px;border-radius:20px;font-size:.8rem;font-weight:700">🟢 4</span> | 4 produits **tranquilles** (> 7 jours) | Aucune action immédiate |
| <span style="background:#888;color:#FFF;padding:1px 7px;border-radius:20px;font-size:.8rem;font-weight:700">⬜ 2</span> | 2 produits **déjà traités** (vendus, jetés, etc.) | Déjà pris en charge |

Le jour courant est **encadré en marron foncé**.

> **Badge rouge clignotant :** si le badge rouge d'un jour clignote, cela signifie qu'il y a des produits expirés **non encore traités** pour ce jour. C'est l'alerte la plus urgente de l'application. Tapez immédiatement sur ce jour pour les traiter.

Les jours grisés (en fondu) appartiennent au mois précédent ou suivant — ils sont visibles mais non cliquables.

---

## Naviguer dans le calendrier

### Changer de période

<div style="background:#FFFDF7;border:1.5px dashed #D4A574;border-radius:10px;padding:.7rem .9rem;display:flex;align-items:center;gap:.7rem;margin:.4rem 0 .8rem;flex-wrap:wrap">
  <span style="border:1.5px solid #6B3A1F;color:#6B3A1F;width:44px;height:44px;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;font-size:1.6rem;font-weight:700;cursor:pointer">‹</span>
  <span style="font-size:1.05rem;font-weight:700;text-align:center;flex:1;min-width:120px">Mai 2026</span>
  <span style="border:1.5px solid #6B3A1F;color:#6B3A1F;width:44px;height:44px;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;font-size:1.6rem;font-weight:700;cursor:pointer">›</span>
  <span style="background:#6B3A1F;color:#FFF;padding:.5rem 1rem;border-radius:12px;font-weight:600;font-size:.85rem">Aujourd'hui</span>
</div>

- **`‹`** : reculer d'une période (−1 mois en vue Mois, −1 semaine en vue Semaine, −1 an en vue Annuelle)
- **`›`** : avancer d'une période
- **`Aujourd'hui`** : revenir immédiatement à la période en cours

### Changer de vue

<div style="display:inline-flex;gap:4px;background:#f0e8dc;padding:4px;border-radius:12px;margin:.3rem 0 .7rem">
  <span style="padding:.5rem .9rem;border-radius:8px;font-size:.85rem;font-weight:700;color:#6B3A1F;background:transparent">Semaine</span>
  <span style="padding:.5rem .9rem;border-radius:8px;font-size:.85rem;font-weight:700;background:#6B3A1F;color:#FFF">Mois</span>
  <span style="padding:.5rem .9rem;border-radius:8px;font-size:.85rem;font-weight:700;color:#6B3A1F;background:transparent">Annuel</span>
</div>

Trois vues sont disponibles. Tapez le nom de la vue pour basculer :

| Vue | Ce qu'on voit |
|---|---|
| **Semaine** | Les 7 jours de la semaine en colonnes — noms de produits visibles directement |
| **Mois** | Le mois complet en grille — badges compteurs par jour *(défaut)* |
| **Annuel** | Les 12 mois de l'année en mini-tuiles — vue d'ensemble |

---

## Vue Semaine

La vue Semaine affiche **7 colonnes** (Lundi → Dimanche) avec le détail des produits lisible directement, sans avoir à taper :

<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:5px;padding:8px;background:#F5ECD7;border-radius:12px;margin:.4rem 0 .8rem">
  <div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:10px;min-height:130px;overflow:hidden;display:flex;flex-direction:column">
    <div style="background:#f5ede0;padding:.3rem .4rem;border-bottom:1px solid #e8d9c4;text-align:center"><div style="font-size:.65rem;font-weight:700;color:#6B3A1F;text-transform:uppercase">LUN</div><div style="font-size:1rem;font-weight:700;line-height:1.1">12</div></div>
    <div style="padding:3px;display:flex;flex-direction:column;gap:3px;overflow-y:auto;flex:1"><div style="background:#fce9e9;border-left:3px solid #C93030;border-radius:4px;padding:3px 5px;font-size:.67rem;display:flex;gap:3px"><span>📦</span><span style="line-height:1.3;word-break:break-word">Entrecôte</span></div></div>
  </div>
  <div style="background:#FFFDF7;border:2px solid #6B3A1F;border-radius:10px;min-height:130px;overflow:hidden;display:flex;flex-direction:column">
    <div style="background:#f5ede0;padding:.3rem .4rem;border-bottom:1px solid #e8d9c4;text-align:center"><div style="font-size:.65rem;font-weight:700;color:#6B3A1F;text-transform:uppercase">MAR</div><div style="font-size:1rem;font-weight:700;line-height:1.1">13</div></div>
    <div style="padding:3px;display:flex;flex-direction:column;gap:3px;overflow-y:auto;flex:1"><div style="background:#fce9e9;border-left:3px solid #C93030;border-radius:4px;padding:3px 5px;font-size:.67rem;display:flex;gap:3px"><span>❄️</span><span style="line-height:1.3;word-break:break-word">Rôti de porc</span></div><div style="background:#fef3e7;border-left:3px solid #E8913A;border-radius:4px;padding:3px 5px;font-size:.67rem;display:flex;gap:3px"><span>🔪</span><span style="line-height:1.3;word-break:break-word">Merguez maison</span></div></div>
  </div>
  <div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:10px;min-height:130px;overflow:hidden;display:flex;flex-direction:column">
    <div style="background:#f5ede0;padding:.3rem .4rem;border-bottom:1px solid #e8d9c4;text-align:center"><div style="font-size:.65rem;font-weight:700;color:#6B3A1F;text-transform:uppercase">MER</div><div style="font-size:1rem;font-weight:700;line-height:1.1">14</div></div>
    <div style="padding:3px;display:flex;flex-direction:column;gap:3px;flex:1"><div style="text-align:center;color:#ccc;padding:8px;font-size:.72rem">—</div></div>
  </div>
  <div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:10px;min-height:130px;overflow:hidden;display:flex;flex-direction:column">
    <div style="background:#f5ede0;padding:.3rem .4rem;border-bottom:1px solid #e8d9c4;text-align:center"><div style="font-size:.65rem;font-weight:700;color:#6B3A1F;text-transform:uppercase">JEU</div><div style="font-size:1rem;font-weight:700;line-height:1.1">15</div></div>
    <div style="padding:3px;display:flex;flex-direction:column;gap:3px;overflow-y:auto;flex:1"><div style="background:#fef3e7;border-left:3px solid #E8913A;border-radius:4px;padding:3px 5px;font-size:.67rem;display:flex;gap:3px"><span>🔥</span><span>Poulet rôti</span></div></div>
  </div>
  <div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:10px;min-height:130px;overflow:hidden;display:flex;flex-direction:column">
    <div style="background:#f5ede0;padding:.3rem .4rem;border-bottom:1px solid #e8d9c4;text-align:center"><div style="font-size:.65rem;font-weight:700;color:#6B3A1F;text-transform:uppercase">VEN</div><div style="font-size:1rem;font-weight:700;line-height:1.1">16</div></div>
    <div style="padding:3px;display:flex;flex-direction:column;gap:3px;overflow-y:auto;flex:1"><div style="background:#fefbe6;border-left:3px solid #E8C83A;border-radius:4px;padding:3px 5px;font-size:.67rem;display:flex;gap:3px"><span>📦</span><span>Agneau gigot</span></div></div>
  </div>
  <div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:10px;min-height:130px;overflow:hidden;display:flex;flex-direction:column">
    <div style="background:#f5ede0;padding:.3rem .4rem;border-bottom:1px solid #e8d9c4;text-align:center"><div style="font-size:.65rem;font-weight:700;color:#6B3A1F;text-transform:uppercase">SAM</div><div style="font-size:1rem;font-weight:700;line-height:1.1">17</div></div>
    <div style="padding:3px;display:flex;flex-direction:column;gap:3px;overflow-y:auto;flex:1"><div style="background:#eaf5ed;border-left:3px solid #2D7D46;border-radius:4px;padding:3px 5px;font-size:.67rem;display:flex;gap:3px"><span>📦</span><span>Côtelettes</span></div><div style="background:#eaf5ed;border-left:3px solid #2D7D46;border-radius:4px;padding:3px 5px;font-size:.67rem;display:flex;gap:3px"><span>📦</span><span>Rosbeef</span></div></div>
  </div>
  <div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:10px;min-height:130px;overflow:hidden;display:flex;flex-direction:column">
    <div style="background:#f5ede0;padding:.3rem .4rem;border-bottom:1px solid #e8d9c4;text-align:center"><div style="font-size:.65rem;font-weight:700;color:#6B3A1F;text-transform:uppercase">DIM</div><div style="font-size:1rem;font-weight:700;line-height:1.1">18</div></div>
    <div style="padding:3px;display:flex;flex-direction:column;gap:3px;flex:1"><div style="text-align:center;color:#ccc;padding:8px;font-size:.72rem">—</div></div>
  </div>
</div>

Chaque ligne de produit dans une colonne est colorée selon l'urgence (même code que la vue Mois). L'icône devant le nom indique l'origine : 📦 réception, 🔪 fabrication maison, 🔥 cuit, ❄️ refroidi.

Tapez sur une colonne (n'importe où dans la case d'un jour) pour ouvrir la **fenêtre du jour** avec le détail de tous les produits.

---

## Vue Annuelle

La vue Annuelle affiche les **12 mois de l'année** en grille 3 colonnes × 4 lignes :

<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:10px;background:#F5ECD7;border-radius:12px;margin:.4rem 0 .8rem">
  <div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:10px;padding:.7rem;display:flex;flex-direction:column;gap:.4rem">
    <div style="font-weight:700;color:#6B3A1F;text-transform:capitalize;font-size:.9rem">Janvier</div>
    <div style="display:flex;flex-wrap:wrap;gap:4px">
      <span style="background:#888;color:#FFF;padding:2px 8px;border-radius:20px;font-size:.72rem;font-weight:700">⬜ 8</span>
    </div>
    <div style="font-size:.72rem;color:#888">8 produit(s)</div>
  </div>
  <div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:10px;padding:.7rem;display:flex;flex-direction:column;gap:.4rem;opacity:.6">
    <div style="font-weight:700;color:#6B3A1F;text-transform:capitalize;font-size:.9rem">Février</div>
    <div style="color:#ccc;font-size:.82rem">—</div>
  </div>
  <div style="background:#FFFDF7;border:2px solid #6B3A1F;border-radius:10px;padding:.7rem;display:flex;flex-direction:column;gap:.4rem">
    <div style="font-weight:700;color:#6B3A1F;text-transform:capitalize;font-size:.9rem">Mai</div>
    <div style="display:flex;flex-wrap:wrap;gap:4px">
      <span style="background:#C93030;color:#FFF;padding:2px 8px;border-radius:20px;font-size:.72rem;font-weight:700">🔴 2</span>
      <span style="background:#E8913A;color:#FFF;padding:2px 8px;border-radius:20px;font-size:.72rem;font-weight:700">🟠 3</span>
      <span style="background:#2D7D46;color:#FFF;padding:2px 8px;border-radius:20px;font-size:.72rem;font-weight:700">🟢 5</span>
    </div>
    <div style="font-size:.72rem;color:#888">10 produit(s)</div>
  </div>
</div>

Chaque tuile affiche le nom du mois, des points colorés avec les compteurs, et le total de produits. Le mois courant est encadré en marron foncé.

**Tapez un mois** pour basculer automatiquement en **vue Mois** sur ce mois.

---

## Filtrer l'affichage

Sous la barre de navigation, plusieurs filtres permettent de cibler ce qui vous intéresse :

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:12px;padding:.8rem;margin:.4rem 0 .8rem;display:flex;flex-direction:column;gap:.7rem">
  <div style="display:flex;flex-direction:column;gap:2px">
    <span style="font-weight:700;font-size:.82rem;color:#6B3A1F">Recherche</span>
    <div style="display:flex;gap:4px">
      <input type="text" placeholder="Nom du produit ou N° de lot…" style="flex:1;padding:.55rem .75rem;border:1.5px solid #d8c9b2;border-radius:8px;font-size:.85rem;min-height:44px;background:#FFF" />
      <button style="background:#FFF;border:1.5px solid #d8c9b2;border-radius:8px;padding:0 .6rem;color:#6B3A1F;min-height:44px;font-size:.9rem">▾</button>
    </div>
  </div>
  <div style="display:flex;gap:.7rem;flex-wrap:wrap">
    <div style="display:flex;flex-direction:column;gap:2px">
      <span style="font-weight:700;font-size:.82rem;color:#6B3A1F">Source</span>
      <select style="padding:.55rem .75rem;border:1.5px solid #d8c9b2;border-radius:8px;background:#FFF;font-size:.85rem;min-height:44px;min-width:160px"><option>Toutes</option><option>📦 Réception</option><option>🔪 Fabrication</option><option>🔥 Cuisson</option><option>❄️ Refroidissement</option></select>
    </div>
    <div style="display:flex;flex-direction:column;gap:2px">
      <span style="font-weight:700;font-size:.82rem;color:#6B3A1F">Statut</span>
      <select style="padding:.55rem .75rem;border:1.5px solid #d8c9b2;border-radius:8px;background:#FFF;font-size:.85rem;min-height:44px;min-width:160px"><option>Tous</option><option>À traiter (expirés)</option><option>Traités</option><option>Actifs (non expirés)</option></select>
    </div>
  </div>
</div>

| Filtre | Comment ça fonctionne |
|---|---|
| **Recherche** | Tapez le début du nom d'un produit, ou son numéro de lot. Le calendrier se met à jour instantanément sans recharger. Tapez **`▾`** pour voir tous les produits disponibles dans la période. |
| **Source** | Affiche uniquement les produits d'une origine précise — réception fournisseur, fabrication maison, cuisson ou refroidissement. Ce filtre recharge le calendrier depuis le serveur. |
| **Statut** | **Tous** : tout est affiché. **À traiter (expirés)** : uniquement les produits dont la DLC est dépassée et pas encore traités. **Traités** : uniquement les produits déjà vendus, jetés, etc. **Actifs** : uniquement les produits dont la DLC n'est pas encore passée. |

---

## Bouton ⚡ Traiter les expirés

Quand des produits **expirés non traités** existent dans la période affichée, un bouton rouge clignotant apparaît automatiquement :

<div style="margin:.4rem 0 .8rem">
  <button style="background:#C93030;color:#FFF;border:none;border-radius:8px;padding:.6rem 1rem;font-size:.9rem;font-weight:700;min-height:44px;display:inline-flex;align-items:center;gap:.4rem;box-shadow:0 0 0 4px rgba(201,48,48,.25)">⚡ Traiter les expirés (3)</button>
</div>

Le chiffre entre parenthèses indique le nombre de produits concernés. Ce bouton ouvre directement la **fenêtre de traitement en masse** — voir plus bas.

---

## Taper sur un jour — La fenêtre du jour

Tapez n'importe quelle case du calendrier qui contient des badges pour ouvrir la fenêtre listant **tous les produits dont la DLC tombe ce jour-là** :

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;overflow:hidden;margin:.5rem 0 .9rem">
  <!-- Header fenêtre -->
  <div style="background:#6B3A1F;color:#FFF;padding:.7rem 1rem;display:flex;align-items:center;justify-content:space-between">
    <span style="font-weight:700;font-size:.95rem">DLC du 14/05/2026</span>
    <button style="background:transparent;border:none;color:#FFF;font-size:1.3rem;min-width:40px;min-height:40px">✕</button>
  </div>
  <div style="padding:.8rem">
    <!-- Produit 1 : rouge, réception -->
    <div style="border:1.5px solid #e8d9c4;border-left:6px solid #C93030;border-radius:8px;padding:.75rem;margin-bottom:.7rem;background:#FFF;display:flex;flex-direction:column;gap:4px">
      <div style="font-weight:700;font-size:.95rem;color:#C93030">Entrecôte de bœuf</div>
      <div style="display:flex;flex-wrap:wrap;gap:.3rem">
        <span style="background:#f5ede0;padding:2px 8px;border-radius:20px;font-size:.78rem;color:#6B3A1F">📦 Réception</span>
        <span style="background:#f5ede0;padding:2px 8px;border-radius:20px;font-size:.78rem;color:#6B3A1F">Lot VB0510-002</span>
        <span style="background:#f5ede0;padding:2px 8px;border-radius:20px;font-size:.78rem;color:#6B3A1F">12 kg</span>
        <span style="background:#f5ede0;padding:2px 8px;border-radius:20px;font-size:.78rem;color:#6B3A1F">Frn : Bovins du Gers</span>
        <span style="background:#f5ede0;padding:2px 8px;border-radius:20px;font-size:.78rem;color:#6B3A1F">Origine : 10/05/2026</span>
      </div>
      <div style="display:flex;gap:.4rem;flex-wrap:wrap;margin-top:.3rem">
        <a href="#" style="display:inline-flex;align-items:center;gap:4px;padding:.45rem .8rem;background:#f0e8dc;color:#6B3A1F;border:1.5px solid #6B3A1F;border-radius:8px;font-weight:600;font-size:.8rem;text-decoration:none">🔗 Voir la fiche</a>
        <button style="background:#C93030;color:#FFF;border:none;padding:.45rem .8rem;border-radius:8px;font-weight:600;font-size:.8rem;min-height:40px">✏️ Correction</button>
        <button style="background:#f0e8dc;color:#6B3A1F;border:1.5px solid #6B3A1F;padding:.45rem .8rem;border-radius:8px;font-weight:600;font-size:.8rem;min-height:40px">📅 Modifier DLC</button>
        <button style="background:#fff5f5;color:#c0392b;border:1.5px solid #c0392b;padding:.45rem .8rem;border-radius:8px;font-weight:600;font-size:.8rem;min-height:40px">🗑️ Supprimer</button>
        <button style="background:#eaf3ff;color:#1a5fb4;border:1.5px solid #1a5fb4;padding:.45rem .8rem;border-radius:8px;font-weight:600;font-size:.8rem;min-height:40px">🖨️ Imprimer</button>
      </div>
    </div>
    <!-- Produit 2 : gris, déjà traité -->
    <div style="border:1.5px solid #e8d9c4;border-left:6px solid #888;border-radius:8px;padding:.75rem;background:#FFF;opacity:.8;display:flex;flex-direction:column;gap:4px">
      <div style="font-weight:700;font-size:.95rem;color:#555">Rôti de porc</div>
      <div style="display:flex;flex-wrap:wrap;gap:.3rem">
        <span style="background:#f5ede0;padding:2px 8px;border-radius:20px;font-size:.78rem;color:#6B3A1F">❄️ Refroidissement</span>
        <span style="background:#f5ede0;padding:2px 8px;border-radius:20px;font-size:.78rem;color:#6B3A1F">Lot VB0513-001</span>
      </div>
      <div style="font-style:italic;font-size:.82rem;color:#444;margin-top:4px">✓ Vendu — Marie le 14/05/2026</div>
      <div style="display:flex;gap:.4rem;flex-wrap:wrap;margin-top:.3rem">
        <button style="background:#6B3A1F;color:#FFF;border:none;padding:.45rem .8rem;border-radius:8px;font-weight:600;font-size:.8rem;min-height:40px">✏️ Actualiser</button>
        <button style="background:#eaf3ff;color:#1a5fb4;border:1.5px solid #1a5fb4;padding:.45rem .8rem;border-radius:8px;font-weight:600;font-size:.8rem;min-height:40px">🖨️ Imprimer</button>
      </div>
    </div>
  </div>
</div>

### Lire une fiche produit dans la fenêtre

Chaque produit affiché dans la fenêtre présente :

- **Nom du produit** — coloré selon l'urgence (rouge si expiré, orange si urgent, etc.)
- **Méta** — petits tags ronds : icône source, numéro de lot, quantité et unité, fournisseur, date d'origine
- **Devenir enregistré** *(si déjà traité)* — ligne en italique : `✓ [Statut] — [Opérateur] le [Date]`
- **Boutons d'action**

### Les boutons d'action

| Bouton | Quand visible | Ce qu'il fait |
|---|---|---|
| **🔗 Voir la fiche** | Produit de réception uniquement | Ouvre la fiche de réception fournisseur complète |
| **▾ N ingrédient(s)** | Produit de fabrication uniquement | Déplie la liste des ingrédients avec lots et DLC |
| **✏️ Correction** | Produit non encore traité | Ouvre la fenêtre "Que devient ce produit ?" |
| **✏️ Actualiser** | Produit déjà traité | Rouvre la fenêtre pour corriger le devenir enregistré |
| **📅 Modifier DLC** | Produit non encore traité | Ouvre la fenêtre pour corriger la date DLC |
| **🗑️ Supprimer** | Produit non encore traité | Retire le produit du calendrier (réversible) |
| **🖨️ Imprimer** | Toujours | Imprime une étiquette thermique 62 mm pour ce produit |

### Voir les ingrédients d'une fabrication

Pour les produits issus d'une fabrication maison, un bouton **`▾ N ingrédient(s)`** est affiché. Tapez-le pour déplier la liste des ingrédients utilisés :

<div style="background:#fbf6ee;border:1px solid #e5d9c3;border-radius:8px;padding:.6rem .8rem;margin:.4rem 0 .7rem">
  <div style="font-size:.82rem;font-weight:700;color:#6B3A1F;margin-bottom:6px">⚖️ 3 kg fabriqués</div>
  <div style="display:flex;flex-direction:column;gap:4px">
    <div style="display:grid;grid-template-columns:1.4fr 0.8fr 1.4fr;gap:8px;align-items:center;padding:6px 4px;border-bottom:1px dashed #e5d9c3;font-size:.8rem">
      <span style="font-weight:700">Bœuf haché 15%</span>
      <span style="color:#6B3A1F">2 kg</span>
      <span style="color:#555;text-align:right">Lot VB0510-001 · DLC 14/05 <a href="#" style="color:#6B3A1F;text-decoration:none;margin-left:4px">🔗</a></span>
    </div>
    <div style="display:grid;grid-template-columns:1.4fr 0.8fr 1.4fr;gap:8px;align-items:center;padding:6px 4px;font-size:.8rem">
      <span style="font-weight:700">Épices mélange</span>
      <span style="color:#6B3A1F">150 g</span>
      <span style="color:#555;text-align:right">Lot EP0512-001</span>
    </div>
  </div>
</div>

Pour chaque ingrédient : son nom, la quantité utilisée, le numéro de lot, la DLC, et si c'est un produit issu d'une réception, un lien 🔗 vers la fiche fournisseur. Tapez à nouveau le bouton (devenu **`▴`**) pour replier.

---

## Enregistrer le devenir d'un produit (✏️ Correction)

Tapez **`✏️ Correction`** sur un produit pour déclarer ce qu'il est devenu :

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;overflow:hidden;margin:.5rem 0 .9rem">
  <div style="background:#6B3A1F;color:#FFF;padding:.65rem 1rem;display:flex;align-items:center;justify-content:space-between">
    <span style="font-weight:700;font-size:.92rem">Devenir du produit</span>
    <button style="background:transparent;border:none;color:#FFF;font-size:1.3rem;min-width:40px;min-height:40px">✕</button>
  </div>
  <div style="padding:.9rem">
    <div style="font-weight:700;font-size:1rem;margin-bottom:4px">Entrecôte de bœuf</div>
    <div style="font-size:.82rem;color:#6B3A1F;margin-bottom:1rem">DLC 14/05/2026 · Lot VB0510-002</div>
    <div style="font-weight:700;font-size:.82rem;color:#6B3A1F;margin-bottom:.4rem">Prénom opérateur *</div>
    <select style="width:100%;padding:.6rem .8rem;border:1.5px solid #d8c9b2;border-radius:8px;font-size:.88rem;min-height:44px;background:#FFF;margin-bottom:.8rem"><option>Marie</option></select>
    <div style="font-weight:700;font-size:.82rem;color:#6B3A1F;margin-bottom:.4rem">Que devient ce produit ? *</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-bottom:.5rem">
      <button style="padding:.8rem .5rem;border-radius:12px;border:2px solid #6B3A1F;background:#6B3A1F;color:#FFF;font-size:.9rem;font-weight:700;min-height:56px">🗑️ Jeté</button>
      <button style="padding:.8rem .5rem;border-radius:12px;border:2px solid #d8c9b2;background:#FFF;font-size:.9rem;font-weight:700;min-height:56px;color:#3D2008">💰 Vendu</button>
      <button style="padding:.8rem .5rem;border-radius:12px;border:2px solid #d8c9b2;background:#FFF;font-size:.9rem;font-weight:700;min-height:56px;color:#3D2008">✅ Consommé</button>
      <button style="padding:.8rem .5rem;border-radius:12px;border:2px solid #d8c9b2;background:#FFF;font-size:.9rem;font-weight:700;min-height:56px;color:#3D2008">❓ Autre</button>
    </div>
    <div style="font-weight:700;font-size:.82rem;color:#6B3A1F;margin-bottom:.3rem">Commentaire (optionnel)</div>
    <textarea style="width:100%;min-height:44px;border:1.5px solid #d8c9b2;border-radius:8px;padding:.5rem .7rem;font-size:.85rem;box-sizing:border-box;margin-bottom:.7rem" placeholder="Raison, quantité…"></textarea>
    <button style="width:100%;background:#2D7D46;color:#FFF;border:none;border-radius:12px;padding:.9rem;font-size:.95rem;font-weight:700;min-height:56px">Confirmer</button>
  </div>
</div>

**Mode d'emploi :**
1. **Sélectionnez votre prénom** dans le menu.
2. **Tapez le devenir** du produit — un seul bouton s'active (fond marron foncé) :
   - `🗑️ Jeté` : produit mis à la poubelle
   - `💰 Vendu` : passé en caisse ou vendu au comptoir
   - `✅ Consommé` : utilisé en interne (consommation du personnel, dégustation…)
   - `❓ Autre` : tout autre motif — précisez dans le commentaire
3. **Commentaire** (facultatif) : ajoutez une précision si nécessaire.
4. Tapez **`Confirmer`**.

Après confirmation, le produit passe en gris (traité) dans le calendrier. Il n'est plus compté dans les badges colorés et disparaît de la vue filtrée "Actifs".

> **Correction possible :** si vous avez fait une erreur, rouvrez le produit (il affichera `✏️ Actualiser` à la place de `✏️ Correction`) et enregistrez le bon devenir. La correction remplace l'enregistrement précédent.

---

## Modifier la date DLC d'un produit (📅 Modifier DLC)

Tapez **`📅 Modifier DLC`** pour corriger une date limite erronée :

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;overflow:hidden;margin:.5rem 0 .9rem;max-width:420px">
  <div style="background:#6B3A1F;color:#FFF;padding:.65rem 1rem;display:flex;align-items:center;justify-content:space-between">
    <span style="font-weight:700;font-size:.92rem">Modifier la DLC</span>
    <button style="background:transparent;border:none;color:#FFF;font-size:1.3rem;min-width:40px;min-height:40px">✕</button>
  </div>
  <div style="padding:.9rem">
    <div style="font-weight:700;font-size:1rem;margin-bottom:4px">Entrecôte de bœuf</div>
    <div style="font-size:.82rem;color:#6B3A1F;margin-bottom:1rem">DLC actuelle : 14/05/2026</div>
    <div style="font-weight:700;font-size:.82rem;color:#6B3A1F;margin-bottom:.4rem">Nouvelle date DLC *</div>
    <input type="date" style="width:100%;padding:.6rem .8rem;border:1.5px solid #d8c9b2;border-radius:8px;font-size:.88rem;min-height:44px;background:#FFF;box-sizing:border-box;margin-bottom:.8rem" />
    <button style="width:100%;background:#2D7D46;color:#FFF;border:none;border-radius:12px;padding:.9rem;font-size:.95rem;font-weight:700;min-height:56px">Confirmer</button>
  </div>
</div>

La DLC actuelle est rappelée sous le nom du produit. Choisissez la nouvelle date et tapez **`Confirmer`**. Le calendrier repositionne immédiatement le produit sur le bon jour.

> **Nota :** cette action ne modifie que la DLC. Le numéro de lot reste inchangeable.

---

## Retirer un produit du calendrier (🗑️ Supprimer)

Tapez **`🗑️ Supprimer`** pour faire disparaître un produit du calendrier. Une fenêtre de confirmation s'affiche :

> *Supprimer « Entrecôte de bœuf » du calendrier DLC ? Cette action est réversible via le bouton Correction.*

Si vous confirmez, le produit est marqué "annulé" et disparaît des vues normales. **Cette action est réversible** : il reste visible en changeant le filtre Statut sur "Traités", et vous pouvez l'y rouvrir avec `✏️ Actualiser` pour lui attribuer un vrai devenir (vendu, jeté, etc.).

---

## Traitement en masse — Produits expirés

Quand plusieurs produits sont en retard de traitement, le bouton **`⚡ Traiter les expirés (N)`** permet de les traiter tous d'un coup :

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;overflow:hidden;margin:.5rem 0 .9rem">
  <div style="background:#6B3A1F;color:#FFF;padding:.65rem 1rem;display:flex;align-items:center;justify-content:space-between">
    <span style="font-weight:700;font-size:.92rem">Traitement en masse — DLC dépassées</span>
    <button style="background:transparent;border:none;color:#FFF;font-size:1.3rem;min-width:40px;min-height:40px">✕</button>
  </div>
  <div style="padding:.9rem">
    <div style="font-weight:700;font-size:.88rem;color:#C93030;margin-bottom:.7rem">3 produit(s) dépassé(s) non traité(s)</div>
    <div style="display:flex;justify-content:space-between;align-items:center;padding:.4rem 0;border-bottom:1px solid #e8d9c4;margin-bottom:.4rem">
      <label style="display:inline-flex;align-items:center;gap:.4rem;font-weight:700;font-size:.85rem"><input type="checkbox" checked /> Tout sélectionner</label>
      <span style="font-size:.8rem;color:#666">3 sélectionné(s)</span>
    </div>
    <div style="max-height:160px;overflow-y:auto;border:1px solid #e8d9c4;border-radius:8px;margin-bottom:.7rem">
      <div style="display:grid;grid-template-columns:auto auto 1fr auto;gap:.25rem .75rem;align-items:center;padding:.5rem .75rem;border-bottom:1px solid #eee;border-left:4px solid #C93030">
        <input type="checkbox" checked style="width:20px;height:20px" />
        <span style="font-size:1.1rem">📦</span>
        <span style="font-weight:700;font-size:.85rem">Entrecôte de bœuf</span>
        <span style="font-size:.78rem;font-weight:700;color:#C93030">14/05</span>
      </div>
      <div style="display:grid;grid-template-columns:auto auto 1fr auto;gap:.25rem .75rem;align-items:center;padding:.5rem .75rem;border-bottom:1px solid #eee;border-left:4px solid #C93030">
        <input type="checkbox" checked style="width:20px;height:20px" />
        <span style="font-size:1.1rem">❄️</span>
        <span style="font-weight:700;font-size:.85rem">Rôti de porc refroidi</span>
        <span style="font-size:.78rem;font-weight:700;color:#C93030">13/05</span>
      </div>
      <div style="display:grid;grid-template-columns:auto auto 1fr auto;gap:.25rem .75rem;align-items:center;padding:.5rem .75rem;border-left:4px solid #E8913A">
        <input type="checkbox" checked style="width:20px;height:20px" />
        <span style="font-size:1.1rem">🔪</span>
        <span style="font-weight:700;font-size:.85rem">Merguez maison</span>
        <span style="font-size:.78rem;font-weight:700;color:#E8913A">15/05</span>
      </div>
    </div>
    <div style="font-weight:700;font-size:.82rem;color:#6B3A1F;margin-bottom:.4rem">Prénom opérateur *</div>
    <select style="width:100%;padding:.6rem .8rem;border:1.5px solid #d8c9b2;border-radius:8px;font-size:.88rem;min-height:44px;background:#FFF;margin-bottom:.7rem"><option>Marie</option></select>
    <div style="font-weight:700;font-size:.82rem;color:#6B3A1F;margin-bottom:.4rem">Devenir appliqué à tous *</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-bottom:.5rem">
      <button style="padding:.8rem .5rem;border-radius:12px;border:2px solid #d8c9b2;background:#FFF;font-size:.88rem;font-weight:700;min-height:52px;color:#3D2008">🗑️ Jeté</button>
      <button style="padding:.8rem .5rem;border-radius:12px;border:2px solid #d8c9b2;background:#FFF;font-size:.88rem;font-weight:700;min-height:52px;color:#3D2008">💰 Vendu</button>
      <button style="padding:.8rem .5rem;border-radius:12px;border:2px solid #d8c9b2;background:#FFF;font-size:.88rem;font-weight:700;min-height:52px;color:#3D2008">✅ Consommé</button>
      <button style="padding:.8rem .5rem;border-radius:12px;border:2px solid #d8c9b2;background:#FFF;font-size:.88rem;font-weight:700;min-height:52px;color:#3D2008">❓ Autre</button>
    </div>
    <div style="font-weight:700;font-size:.82rem;color:#6B3A1F;margin-bottom:.3rem">Commentaire (optionnel)</div>
    <textarea style="width:100%;min-height:44px;border:1.5px solid #d8c9b2;border-radius:8px;padding:.5rem .7rem;font-size:.85rem;box-sizing:border-box;margin-bottom:.7rem" placeholder="Raison commune, lot…"></textarea>
    <button style="width:100%;background:#2D7D46;color:#FFF;border:none;border-radius:12px;padding:.9rem;font-size:.95rem;font-weight:700">Confirmer le traitement</button>
  </div>
</div>

**Étapes :**
1. La liste affiche **uniquement les produits dont la DLC est dépassée et pas encore traités**, triés du plus ancien au plus récent.
2. **Tout sélectionner** est coché par défaut. Décochez les produits que vous ne voulez pas traiter maintenant.
3. **Sélectionnez votre prénom.**
4. **Choisissez le devenir commun** — ce devenir sera appliqué à tous les produits cochés.
5. **Commentaire** (facultatif) — s'applique à tous.
6. Tapez **`Confirmer le traitement`**.

Un message confirme le nombre de produits traités. Le calendrier est rechargé et les badges rouges disparaissent pour ces produits.

> **Cas pratique :** tous les matins, vérifiez si le bouton `⚡ Traiter les expirés` est présent. Si oui, tapez-le et traitez les produits de la nuit.

---

## Imprimer une étiquette depuis le calendrier (🖨️ Imprimer)

Tapez **`🖨️ Imprimer`** sur n'importe quel produit dans la fenêtre du jour. L'étiquette s'imprime directement sur l'imprimante Brother 62 mm avec :

- Un tag **`[FABRIQUÉ]`**, **`[CUIT]`** ou **`[REFROIDI]`** selon l'origine (absent pour les réceptions)
- Le **nom du produit** en majuscules
- Le **numéro de lot**
- La **date DLC**
- La **ligne d'origine** : date et heure de réception, fabrication, cuisson ou refroidissement

---

## Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Que faire |
|---|---|
| Message d'erreur dans la zone principale | Le serveur est inaccessible — vérifiez que le Raspberry Pi est allumé et rechargez |
| Le bouton `Confirmer` reste grisé dans "Devenir" | Vous n'avez pas sélectionné de prénom ou pas tapé un bouton de devenir — remplissez les deux champs obligatoires |
| Le bouton `Confirmer` reste grisé dans "Modifier DLC" | Vous n'avez pas saisi de nouvelle date — renseignez le champ |
| Message `Erreur : [détail]` après confirmation | Problème réseau ou serveur — réessayez ; si ça persiste, vérifiez la connexion |
| La case est grisée et non cliquable | Le jour appartient au mois précédent ou suivant — naviguez sur le bon mois |
| Le produit "supprimé" ne réapparaît pas | Changez le filtre Statut sur "Traités" puis tapez `✏️ Actualiser` pour le modifier |

---

---

# Module 14 — Ouvertures de Conditionnement

Ce module enregistre chaque ouverture de produit sous-vide avec une **photo à l'appui**. Il trace qui a ouvert quoi, quand, et à quel lot fournisseur le produit correspond. La photo sert de preuve en cas de contrôle sanitaire. Une étiquette thermique `[OUVERT]` peut être imprimée immédiatement.

**Deux pages :**

| Page | Accès |
|---|---|
| **Enregistrer une ouverture** | Hub → tuile **Ouverture sous-vide** (`/ouverture.html`) |
| **Consulter l'historique** | Hub → lien **Hist. ouvertures** (`/ouvertures-historique.html`) |

---

## Page d'enregistrement — Wizard 3 étapes

La page se découpe en un wizard guidé de 3 étapes. La progression est matérialisée par 3 points sous l'en-tête :

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;overflow:hidden;margin:.5rem 0 .9rem">
  <div style="background:#3D2008;color:#F5ECD7;padding:0 1rem;height:56px;display:flex;align-items:center;justify-content:space-between">
    <button style="background:rgba(255,255,255,.12);border:1.5px solid rgba(255,255,255,.3);color:#F5ECD7;padding:.4rem .9rem;border-radius:8px;font-size:.88rem;font-weight:600;min-height:40px">← Retour</button>
    <span style="font-weight:700;letter-spacing:.04em;font-size:.95rem">OUVERTURE SOUS-VIDE</span>
    <span style="font-size:.82rem;color:#D4A574;min-width:48px;text-align:right">09:42</span>
  </div>
  <div style="height:48px;background:#FFFDF7;display:flex;align-items:center;justify-content:center;gap:1.8rem;border-bottom:1px solid rgba(107,58,31,.15)">
    <div style="width:14px;height:14px;border-radius:50%;background:#6B3A1F;transform:scale(1.35)"></div>
    <div style="width:14px;height:14px;border-radius:50%;background:rgba(107,58,31,.22)"></div>
    <div style="width:14px;height:14px;border-radius:50%;background:rgba(107,58,31,.22)"></div>
  </div>
</div>

- Le **point actif** est agrandi et marron foncé
- Les **points terminés** deviennent verts
- Les **points à venir** restent discrets

Au-dessus du contenu aux étapes 2 et 3, un **bandeau marron** rappelle le prénom de l'opérateur sélectionné.

Si la tablette reste inactive 5 minutes, l'application revient automatiquement au hub.

---

## Étape 1 — Qui ouvre ?

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:12px;padding:1.1rem;margin:.4rem 0 .8rem">
  <div style="font-size:1.05rem;font-weight:700;color:#3D2008;margin-bottom:.9rem">Qui ouvre ?</div>
  <div style="display:flex;flex-wrap:wrap;gap:.7rem">
    <button style="padding:.85rem 1.5rem;border-radius:10px;border:2.5px solid #D4A574;background:#FFFDF7;color:#3D2008;font-size:1.05rem;font-weight:600;min-height:64px">Marie</button>
    <button style="padding:.85rem 1.5rem;border-radius:10px;border:2.5px solid #6B3A1F;background:#6B3A1F;color:#F5ECD7;font-size:1.05rem;font-weight:600;min-height:64px">Julien</button>
    <button style="padding:.85rem 1.5rem;border-radius:10px;border:2.5px solid #D4A574;background:#FFFDF7;color:#3D2008;font-size:1.05rem;font-weight:600;min-height:64px">Lucas</button>
    <button style="padding:.85rem 1.5rem;border-radius:10px;border:2.5px solid #D4A574;background:#FFFDF7;color:#3D2008;font-size:1.05rem;font-weight:600;min-height:64px">Sophie</button>
  </div>
</div>

**Tapez votre prénom.** Le bouton sélectionné prend un fond marron foncé. L'écran avance **automatiquement** à l'étape 2 après 200 ms, sans qu'il faille taper un bouton "Suivant".

---

## Étape 2 — Prendre la photo

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:12px;padding:1.5rem;margin:.4rem 0 .8rem;display:flex;flex-direction:column;align-items:center;gap:1.5rem">
  <div style="background:#6B3A1F;color:#F5ECD7;padding:.6rem 1rem;border-radius:8px;font-weight:600;font-size:.88rem;width:100%;text-align:center;letter-spacing:.02em">👤 Julien</div>
  <button style="width:180px;height:180px;border-radius:50%;background:#6B3A1F;color:#F5ECD7;border:none;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.5rem;box-shadow:0 6px 28px rgba(107,58,31,.45)">
    <span style="font-size:3rem;line-height:1">📷</span>
    <span style="font-size:.75rem;font-weight:700;letter-spacing:.06em;text-align:center;padding:0 .5rem">PRENDRE LA PHOTO</span>
  </button>
</div>

**Tapez le grand bouton rond 📷 PRENDRE LA PHOTO.** La caméra de la tablette s'ouvre. Prenez la photo du produit sous-vide que vous êtes en train d'ouvrir — assurez-vous que l'étiquette du produit et le numéro de lot soient lisibles.

Après la prise de vue, un **aperçu miniature** s'affiche avec la mention `✓ Photo prise` :

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:12px;padding:1.2rem;margin:.4rem 0 .8rem;display:flex;flex-direction:column;align-items:center;gap:.7rem">
  <div style="width:110px;height:110px;border-radius:12px;border:3px solid #2D7D46;background:#e0e0e0;display:flex;align-items:center;justify-content:center;font-size:2.5rem;box-shadow:0 2px 8px rgba(0,0,0,.15)">📸</div>
  <div style="color:#2D7D46;font-weight:700;font-size:.92rem">✓ Photo prise</div>
</div>

L'écran passe **automatiquement** à l'étape 3 après 450 ms.

> **La photo est obligatoire.** Sans photo, l'ouverture ne peut pas être enregistrée. Si la caméra ne s'ouvre pas, vérifiez que la tablette a bien autorisé l'accès à la caméra dans ses paramètres.

---

## Étape 3 — Choisir le produit

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:12px;padding:1rem;margin:.4rem 0 .8rem;display:flex;flex-direction:column;gap:.6rem">
  <div style="background:#6B3A1F;color:#F5ECD7;padding:.55rem .8rem;border-radius:8px;font-weight:600;font-size:.88rem;text-align:center">👤 Julien</div>
  <div style="position:relative">
    <span style="position:absolute;left:.9rem;top:50%;transform:translateY(-50%);font-size:1.1rem">🔍</span>
    <input type="search" placeholder="Rechercher un produit…" style="width:100%;padding:.9rem 1rem .9rem 3rem;border-radius:12px;border:2px solid #D4A574;background:#FFF;font-size:1.05rem;color:#3D2008;box-sizing:border-box" />
  </div>
  <div style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;color:#6B3A1F;padding:.15rem 0 .2rem">Produits en stock</div>
  <!-- Carte en stock (bord vert) -->
  <div style="background:#FFFDF7;border-radius:12px;box-shadow:0 2px 6px rgba(61,32,8,.1);padding:.85rem 1rem;border-left:5px solid #2D7D46;display:flex;justify-content:space-between;align-items:center;min-height:70px">
    <div style="display:flex;flex-direction:column;gap:.18rem">
      <div style="font-size:1rem;font-weight:700;color:#3D2008">Entrecôte de bœuf</div>
      <div style="font-size:.8rem;color:#6B3A1F">Bœuf</div>
      <div style="font-size:.76rem;font-weight:600;color:#3D2008;opacity:.75">Lot VB0510-002</div>
      <div style="font-size:.76rem;font-weight:700;color:#C93030">DLC 14/05/2026</div>
    </div>
    <div style="font-size:.73rem;color:#888;white-space:nowrap;margin-left:.75rem">VB-1042</div>
  </div>
  <!-- Carte sélectionnée (fond marron) -->
  <div style="background:#6B3A1F;border-radius:12px;box-shadow:0 2px 6px rgba(61,32,8,.15);padding:.85rem 1rem;border-left:5px solid #6B3A1F;display:flex;justify-content:space-between;align-items:center;min-height:70px">
    <div style="display:flex;flex-direction:column;gap:.18rem">
      <div style="font-size:1rem;font-weight:700;color:#F5ECD7">Poulet entier</div>
      <div style="font-size:.8rem;color:#F5ECD7">Volaille</div>
      <div style="font-size:.76rem;font-weight:600;color:#F5ECD7">Lot VL0512-001</div>
      <div style="font-size:.76rem;font-weight:700;color:#F5ECD7">DLC 17/05/2026</div>
    </div>
    <div style="font-size:.73rem;color:#F5ECD7;opacity:.8;white-space:nowrap;margin-left:.75rem">VL-0215</div>
  </div>
  <div style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#888;padding:.5rem 0 .3rem">Catalogue</div>
  <div style="background:#FFFDF7;border-radius:12px;box-shadow:0 2px 6px rgba(61,32,8,.1);padding:.85rem 1rem;border-left:5px solid #D4A574;display:flex;justify-content:space-between;align-items:center;min-height:70px">
    <div style="display:flex;flex-direction:column;gap:.18rem">
      <div style="font-size:1rem;font-weight:700;color:#3D2008">Agneau gigot</div>
      <div style="font-size:.8rem;color:#6B3A1F">Agneau</div>
    </div>
    <div style="font-size:.73rem;color:#888;white-space:nowrap;margin-left:.75rem">AG-0088</div>
  </div>
  <button style="width:100%;padding:1rem;background:#2D7D46;color:#FFF;border:none;border-radius:12px;font-size:1.1rem;font-weight:700;min-height:60px;letter-spacing:.03em">✔ Enregistrer l'ouverture</button>
</div>

### La liste de produits

La liste est divisée en deux sections :

**PRODUITS EN STOCK** (bord gauche vert) — les produits dont une réception a été faite dans les 21 derniers jours. Pour chaque carte : nom, espèce, numéro de lot, DLC du lot FIFO. Ce sont les produits les plus susceptibles d'être ouverts ce jour-là. Ils apparaissent en premier.

**CATALOGUE** (bord gauche sable) — tous les autres produits du catalogue qui ne sont pas en réception récente. Pas de numéro de lot ni de DLC affiché, car il n'y a pas de lot lié.

Le code unique du produit est affiché en petit à droite de chaque carte (ex. `VB-1042`).

### Rechercher un produit

Tapez dans le champ de recherche (avec l'icône 🔍) pour filtrer la liste. La recherche est insensible à la casse et fonctionne sur le nom ou le code unique. La liste se filtre immédiatement, et si le produit n'est pas visible, une recherche plus complète se lance automatiquement après une courte pause.

Pour retrouver la liste complète, effacez le champ de recherche.

### Sélectionner le produit

**Tapez la carte du produit ouvert.** La carte sélectionnée prend un fond marron foncé avec le texte en blanc. Une seule sélection est possible à la fois.

### Enregistrer

Tapez **`✔ Enregistrer l'ouverture`** (bouton vert en bas). Si aucun produit n'est sélectionné, un message rouge s'affiche : *"Veuillez sélectionner un produit."*

---

## Écran de confirmation

Après enregistrement réussi, un écran de confirmation s'affiche avec une animation :

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:12px;padding:1.8rem;margin:.4rem 0 .8rem;display:flex;flex-direction:column;align-items:center;gap:1.1rem;text-align:center">
  <div style="font-size:4.5rem;line-height:1">✅</div>
  <div style="font-size:1.4rem;font-weight:800;color:#2D7D46">Ouverture enregistrée</div>
  <div style="font-size:.95rem;color:#6B3A1F;font-weight:600;line-height:1.6">Poulet entier · Julien<br>Lot VL0512-001 · DLC 17/05/2026</div>
  <div style="display:flex;flex-direction:column;gap:.7rem;width:100%;max-width:320px">
    <button style="width:100%;padding:1rem;background:#3D2008;color:#F5ECD7;border:none;border-radius:12px;font-size:1rem;font-weight:600;min-height:60px">🖨️ Imprimer l'étiquette</button>
    <button style="width:100%;padding:1rem;background:#6B3A1F;color:#F5ECD7;border:none;border-radius:12px;font-size:1rem;font-weight:600;min-height:60px">↩ Même produit</button>
    <button style="width:100%;padding:1rem;background:#FFFDF7;color:#3D2008;border:2px solid #D4A574;border-radius:12px;font-size:1rem;font-weight:600;min-height:60px">✦ Nouvelle ouverture</button>
  </div>
  <div style="font-size:.8rem;color:#888">Retour à l'accueil dans 5 s…</div>
</div>

Le détail rappelle le **nom du produit**, **l'opérateur**, le **numéro de lot** et la **DLC** (si disponibles).

### Les trois boutons

| Bouton | Ce qu'il fait |
|---|---|
| **🖨️ Imprimer l'étiquette** | Imprime immédiatement l'étiquette thermique `[OUVERT]` et annule le compte à rebours |
| **↩ Même produit** | Revient à l'étape 2 (Photo) en conservant l'opérateur et le produit — pour ouvrir un deuxième exemplaire du même produit sans retaper les informations |
| **✦ Nouvelle ouverture** | Repart entièrement à l'étape 1 (Opérateur) — pour une ouverture complètement différente |

**Compte à rebours automatique :** si vous ne touchez rien, l'application retourne au hub après **5 secondes**. Le message `Retour à l'accueil dans Xs…` décompte en bas de l'écran. Taper un des 3 boutons annule le compte à rebours.

---

## Étiquette thermique `[OUVERT]`

Tapez **`🖨️ Imprimer l'étiquette`** pour imprimer sur l'imprimante Brother 62 mm. L'étiquette contient :

<div style="width:200px;margin:.5rem auto .9rem;background:#FFF;border:1px solid #ccc;border-radius:6px;padding:6px;font-family:sans-serif;font-size:.78rem;text-align:center">
  <div style="border:2px solid #000;border-radius:4px;padding:4px;margin-bottom:5px"><span style="font-size:.85rem;font-weight:900;text-transform:uppercase;letter-spacing:.05em">[OUVERT]</span></div>
  <div style="font-size:.85rem;font-weight:900;text-transform:uppercase;line-height:1.1;margin-bottom:5px">POULET ENTIER</div>
  <div style="border:2px solid #000;border-radius:4px;padding:3px;margin-bottom:5px">
    <div style="font-size:.65rem;font-weight:700;text-transform:uppercase">DLC :</div>
    <div style="font-size:1.1rem;font-weight:900;color:red">17/05/26</div>
  </div>
  <div style="border:1px dashed #000;padding:3px;margin-bottom:4px;font-weight:700;font-size:.78rem">Lot : VL0512-001</div>
  <div style="font-size:.7rem;margin-bottom:3px">Ouvert le 14/05/26 à 09h42</div>
  <div style="border-top:1px solid #000;padding-top:3px;font-size:.7rem">Par : Julien</div>
</div>

| Zone | Contenu |
|---|---|
| **Tag** | `[OUVERT]` encadré |
| **Nom produit** | Majuscules |
| **DLC** | Format JJ/MM/AA en rouge — encadrée |
| **Lot** | Numéro de lot (ou `—` si produit du catalogue sans réception liée) |
| **Ligne action** | `Ouvert le JJ/MM/AA à HHhMM` |
| **Pied** | `Par : [Prénom opérateur]` |

---

## Historique des ouvertures (`/ouvertures-historique.html`)

La page Historique liste toutes les ouvertures enregistrées, avec photo et traçabilité. Accès : Hub → **Hist. ouvertures**.

### Filtres

<div style="background:#D4A574;padding:.8rem 1rem;border-radius:12px;display:flex;flex-wrap:wrap;gap:.6rem;align-items:flex-end;margin:.4rem 0 .8rem">
  <div style="display:flex;flex-direction:column;gap:3px;flex:2;min-width:180px">
    <span style="font-size:.75rem;font-weight:700;color:#6B3A1F;text-transform:uppercase;letter-spacing:.04em">Produit</span>
    <input type="search" placeholder="Tous les produits" style="background:#FFF;border:2px solid #6B3A1F;border-radius:8px;font-size:.9rem;height:48px;padding:0 12px;width:100%;box-sizing:border-box" />
  </div>
  <div style="display:flex;flex-direction:column;gap:3px;flex:1;min-width:120px">
    <span style="font-size:.75rem;font-weight:700;color:#6B3A1F;text-transform:uppercase;letter-spacing:.04em">Du</span>
    <input type="date" style="background:#FFF;border:2px solid #6B3A1F;border-radius:8px;font-size:.9rem;height:48px;padding:0 12px;box-sizing:border-box" />
  </div>
  <div style="display:flex;flex-direction:column;gap:3px;flex:1;min-width:120px">
    <span style="font-size:.75rem;font-weight:700;color:#6B3A1F;text-transform:uppercase;letter-spacing:.04em">Au</span>
    <input type="date" style="background:#FFF;border:2px solid #6B3A1F;border-radius:8px;font-size:.9rem;height:48px;padding:0 12px;box-sizing:border-box" />
  </div>
  <button style="background:#6B3A1F;border:none;border-radius:8px;color:#FFF;font-size:.95rem;font-weight:700;height:48px;padding:0 18px;white-space:nowrap">🔍 Rechercher</button>
  <button style="background:none;border:2px solid #6B3A1F;border-radius:8px;color:#6B3A1F;font-size:.88rem;font-weight:600;height:48px;padding:0 14px;white-space:nowrap">✕ Reset</button>
</div>

Saisissez un nom de produit (avec autocomplétion), une date de début et/ou de fin, puis tapez **`🔍 Rechercher`**. Tapez **`✕ Reset`** pour revenir à la liste complète.

### Lire une carte d'ouverture

<div style="display:flex;flex-direction:column;gap:10px;margin:.4rem 0 .8rem">
  <!-- Carte tracée (bord vert) -->
  <div style="background:#FFF;border-radius:12px;border-left:5px solid #2D7D46;box-shadow:0 2px 6px rgba(61,32,8,.1);display:flex;gap:12px;padding:14px;align-items:flex-start">
    <div style="flex-shrink:0;width:80px;height:80px;border-radius:8px;background:#e0e0e0;display:flex;align-items:center;justify-content:center;font-size:2rem;border:2px solid transparent;cursor:pointer">📸</div>
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:4px">
        <div style="font-size:1.1rem;font-weight:700;color:#3D2008">Poulet entier</div>
        <span style="background:rgba(45,125,70,.15);color:#2D7D46;border-radius:20px;font-size:.78rem;font-weight:700;padding:4px 10px;white-space:nowrap">✓ Tracée</span>
      </div>
      <div style="font-size:.82rem;color:#777;margin-bottom:6px">Volaille</div>
      <div style="font-size:.88rem;color:#6B3A1F;margin-bottom:8px">14/05/2026 à 09h42 — Julien</div>
      <div style="background:rgba(45,125,70,.06);border-radius:8px;border:1px solid rgba(45,125,70,.2);display:grid;grid-template-columns:1fr 1fr;gap:6px 12px;padding:10px 12px">
        <div style="display:flex;flex-direction:column;gap:1px"><span style="font-size:.72rem;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:.03em">Lot</span><span style="font-size:.88rem;color:#3D2008">VL0512-001</span></div>
        <div style="display:flex;flex-direction:column;gap:1px"><span style="font-size:.72rem;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:.03em">Fournisseur</span><span style="font-size:.88rem;color:#3D2008">Volailles du Sud</span></div>
        <div style="display:flex;flex-direction:column;gap:1px"><span style="font-size:.72rem;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:.03em">DLC</span><span style="font-size:.88rem;color:#3D2008">17/05/2026</span></div>
        <div style="display:flex;flex-direction:column;gap:1px"><span style="font-size:.72rem;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:.03em">Réceptionné le</span><span style="font-size:.88rem;color:#3D2008">12/05/2026</span></div>
      </div>
    </div>
  </div>
  <!-- Carte manuelle (bord orange) -->
  <div style="background:#FFF;border-radius:12px;border-left:5px solid #E8913A;box-shadow:0 2px 6px rgba(61,32,8,.1);display:flex;gap:12px;padding:14px;align-items:flex-start">
    <div style="flex-shrink:0;width:80px;height:80px;border-radius:8px;background:#e0e0e0;display:flex;align-items:center;justify-content:center;font-size:2rem;cursor:pointer">📸</div>
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:4px">
        <div style="font-size:1.1rem;font-weight:700;color:#3D2008">Agneau gigot</div>
        <span style="background:rgba(232,145,58,.15);color:#E8913A;border-radius:20px;font-size:.78rem;font-weight:700;padding:4px 10px;white-space:nowrap">⚠ Manuelle</span>
      </div>
      <div style="font-size:.82rem;color:#777;margin-bottom:6px">Agneau</div>
      <div style="font-size:.88rem;color:#6B3A1F">13/05/2026 à 14h10 — Marie</div>
    </div>
  </div>
</div>

### Lire les badges de traçabilité

| Badge | Signification | Que faire |
|---|---|---|
| <span style="background:rgba(45,125,70,.15);color:#2D7D46;border-radius:20px;font-size:.82rem;font-weight:700;padding:3px 10px">✓ Tracée</span> | Le produit est lié à une réception fournisseur : lot, fournisseur, DLC et date de réception sont enregistrés | Rien — la traçabilité est complète |
| <span style="background:rgba(232,145,58,.15);color:#E8913A;border-radius:20px;font-size:.82rem;font-weight:700;padding:3px 10px">⚠ Manuelle</span> | Le produit a été sélectionné depuis le catalogue sans réception récente liée | Si possible, améliorer la traçabilité en réceptionnant le produit avant de l'ouvrir |

Une carte **✓ Tracée** (bord gauche vert) affiche un encart vert avec : N° lot · Fournisseur · DLC · Date de réception.

Une carte **⚠ Manuelle** (bord gauche orange) n'a pas cet encart.

### Voir la photo en grand

Tapez sur la **miniature photo** (carré 80×80 px) pour l'agrandir en plein écran sur fond noir. Tapez n'importe où pour la refermer.

### Pagination

La liste affiche 50 ouvertures à la fois. Si d'autres résultats sont disponibles, un bouton **`Voir plus…`** apparaît en bas. Tapez-le pour charger les 50 suivantes.

---

## Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Que faire |
|---|---|
| *"Veuillez sélectionner un produit."* | Tapez une carte produit avant d'appuyer sur Enregistrer |
| *"Erreur : [détail]"* après Enregistrer | Problème de connexion — vérifiez que le Raspberry Pi est allumé et réessayez |
| *"Impossible de charger le personnel."* | Le serveur est inaccessible — rechargez la page |
| *"Impossible de charger les produits."* | Idem — rechargez |
| *"Aucun produit trouvé."* | Votre recherche ne correspond à rien — vérifiez l'orthographe ou effacez le champ |
| La caméra ne s'ouvre pas | Vérifiez que la tablette a autorisé l'accès à la caméra dans ses paramètres système |
| La miniature photo est vide dans l'historique | La photo a été supprimée manuellement du serveur — aucune action possible depuis l'application |

---

---

# Module 15 — Enceintes Frigorifiques & Relevés de Température

Ce module est le **tableau de bord de la chaîne du froid** en temps réel. Il affiche la température actuelle de chaque enceinte frigorifique (chambres froides, vitrines, laboratoire), l'historique des relevés, les alertes de dépassement et les outils de reporting. Les données proviennent de capteurs Zigbee installés dans chaque enceinte — aucune saisie manuelle n'est requise.

**Accès :** Hub principal → tuile **🌡️ TEMPÉRATURES** (ou directement `/index.html`).

---

## Les 4 onglets de la page

La page est organisée en 4 onglets accessibles depuis la barre en haut :

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;overflow:hidden;margin:.5rem 0 .9rem">
  <div style="background:#3D2008;color:#F5ECD7;padding:0 1rem;height:56px;display:flex;align-items:center;justify-content:space-between">
    <a style="color:#F5ECD7;text-decoration:none;font-size:.88rem">← Hub</a>
    <span style="font-weight:700;font-size:.95rem">HACCP — Au Comptoir des Lilas</span>
    <span style="background:#2D7D46;color:#FFF;font-size:.78rem;padding:.2rem .75rem;border-radius:20px;font-weight:700;text-transform:uppercase;letter-spacing:.05em">OK</span>
  </div>
  <nav style="display:flex;gap:.25rem;padding:.8rem 1.2rem .4rem;border-bottom:2px solid #D4A574;overflow-x:auto">
    <button style="background:#3D2008;color:#F5ECD7;border:none;padding:.45rem 1rem;border-radius:8px 8px 0 0;font-size:.85rem;font-weight:600;white-space:nowrap;min-height:44px">Tableau de bord</button>
    <button style="background:none;border:none;padding:.45rem 1rem;border-radius:8px 8px 0 0;font-size:.85rem;color:#6B3A1F;font-weight:500;white-space:nowrap;min-height:44px">Historique</button>
    <button style="background:none;border:none;padding:.45rem 1rem;border-radius:8px 8px 0 0;font-size:.85rem;color:#6B3A1F;font-weight:500;white-space:nowrap;min-height:44px">Alertes</button>
    <button style="background:none;border:none;padding:.45rem 1rem;border-radius:8px 8px 0 0;font-size:.85rem;color:#6B3A1F;font-weight:500;white-space:nowrap;min-height:44px">Rapports</button>
  </nav>
</div>

| Onglet | Ce qu'on y fait |
|---|---|
| **Tableau de bord** | Vue d'ensemble temps réel de toutes les enceintes *(onglet par défaut)* |
| **Historique** | Graphique et tableau des relevés sur une période choisie |
| **Alertes** | Journal des dépassements de température |
| **Rapports** | Génération et téléchargement de rapports PDF/CSV |

L'onglet actif est affiché sur fond marron foncé. Tapez un onglet pour basculer.

---

## Onglet Tableau de bord

### Le statut global

Dans l'en-tête en haut à droite, un **badge coloré** résume l'état de toutes les enceintes d'un coup d'œil :

| Badge | Couleur | Signification |
|---|---|---|
| <span style="background:#2D7D46;color:#FFF;font-size:.8rem;padding:2px 8px;border-radius:20px;font-weight:700">OK</span> | Vert | Toutes les enceintes sont dans leurs seuils |
| <span style="background:#E8913A;color:#FFF;font-size:.8rem;padding:2px 8px;border-radius:20px;font-weight:700">Attention</span> | Orange | Au moins une enceinte s'approche d'un seuil |
| <span style="background:#C93030;color:#FFF;font-size:.8rem;padding:2px 8px;border-radius:20px;font-weight:700">Alerte</span> | Rouge clignotant | Au moins une enceinte a dépassé un seuil |
| <span style="background:#888;color:#FFF;font-size:.8rem;padding:2px 8px;border-radius:20px;font-weight:700">Hors ligne</span> | Gris | Au moins un capteur ne répond plus |

Quand le statut est **Alerte**, un **bandeau rouge** apparaît aussi en haut de la page :

<div style="background:#C93030;color:#FFF;text-align:center;padding:.5rem 1rem;font-weight:600;font-size:.88rem;border-radius:8px;margin:.3rem 0 .7rem">
  ⚠️ 1 alerte(s) en cours — Chambre froide 2
</div>

Le bandeau disparaît dès que les températures reviennent dans les seuils.

### Les cartes enceinte

Une carte par enceinte configurée, rafraîchie automatiquement **toutes les 30 secondes** :

<div style="display:grid;grid-template-columns:1fr 1fr;gap:.8rem;margin:.4rem 0 .9rem">
  <!-- Carte OK -->
  <div style="background:#FFFDF7;border-radius:12px;box-shadow:0 2px 6px rgba(61,32,8,.1);padding:1.1rem;border-left:5px solid #2D7D46">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:.65rem">
      <div><div style="font-weight:700;font-size:.92rem;color:#3D2008">Chambre froide 1</div><div style="font-size:.72rem;color:#6B3A1F;margin-top:.1rem">chambre_froide</div></div>
      <span style="background:#e6f4eb;color:#2D7D46;font-size:.68rem;padding:.18rem .55rem;border-radius:12px;font-weight:700;text-transform:uppercase;flex-shrink:0">OK</span>
    </div>
    <div style="font-size:1.8rem;font-weight:800;line-height:1;margin:.4rem 0 .2rem;font-variant-numeric:tabular-nums">2,1 <span style="font-size:1.1rem;font-weight:400;color:#6B3A1F">°C</span></div>
    <div style="font-size:.8rem;color:#6B3A1F;margin-bottom:.65rem">Humidité : 78,4%</div>
    <div style="height:52px;background:linear-gradient(to right, #e6f4eb, #c8e6d0);border-radius:6px;margin-bottom:.6rem;opacity:.7"></div>
    <div style="display:flex;justify-content:space-between;font-size:.7rem;color:#888;border-top:1px solid #eee;padding-top:.5rem;margin-top:.2rem">
      <span>🟢 85%</span>
      <span>Mis à jour 14/05 09:41</span>
    </div>
  </div>
  <!-- Carte Alerte -->
  <div style="background:#FFFDF7;border-radius:12px;box-shadow:0 2px 6px rgba(61,32,8,.1);padding:1.1rem;border-left:5px solid #C93030">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:.65rem">
      <div><div style="font-weight:700;font-size:.92rem;color:#3D2008">Chambre froide 2</div><div style="font-size:.72rem;color:#6B3A1F;margin-top:.1rem">chambre_froide</div></div>
      <span style="background:#fce8e8;color:#C93030;font-size:.68rem;padding:.18rem .55rem;border-radius:12px;font-weight:700;text-transform:uppercase;flex-shrink:0">Alerte</span>
    </div>
    <div style="background:#fce8e8;border-radius:6px;padding:.35rem .55rem;font-size:.72rem;color:#C93030;font-weight:600;margin-bottom:.5rem">🌡️ Température trop haute — depuis 23 min</div>
    <div style="font-size:1.8rem;font-weight:800;line-height:1;margin:.2rem 0 .2rem;font-variant-numeric:tabular-nums;color:#C93030">5,8 <span style="font-size:1.1rem;font-weight:400">°C</span></div>
    <div style="font-size:.8rem;color:#6B3A1F;margin-bottom:.65rem">Humidité : 82,1%</div>
    <div style="height:52px;background:linear-gradient(to right, #fce8e8, #f5c0c0);border-radius:6px;margin-bottom:.6rem;opacity:.7"></div>
    <div style="display:flex;justify-content:space-between;font-size:.7rem;color:#888;border-top:1px solid #eee;padding-top:.5rem;margin-top:.2rem">
      <span>🟠 31%</span>
      <span>Mis à jour 14/05 09:41</span>
    </div>
  </div>
  <!-- Carte Attention -->
  <div style="background:#FFFDF7;border-radius:12px;box-shadow:0 2px 6px rgba(61,32,8,.1);padding:1.1rem;border-left:5px solid #E8913A">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:.65rem">
      <div><div style="font-weight:700;font-size:.92rem;color:#3D2008">Vitrine réfrigérée</div><div style="font-size:.72rem;color:#6B3A1F;margin-top:.1rem">vitrine</div></div>
      <span style="background:#fdf0e0;color:#E8913A;font-size:.68rem;padding:.18rem .55rem;border-radius:12px;font-weight:700;text-transform:uppercase;flex-shrink:0">Attention</span>
    </div>
    <div style="font-size:1.8rem;font-weight:800;line-height:1;margin:.4rem 0 .2rem;font-variant-numeric:tabular-nums">3,6 <span style="font-size:1.1rem;font-weight:400;color:#6B3A1F">°C</span></div>
    <div style="font-size:.8rem;color:#6B3A1F;margin-bottom:.65rem">Humidité : 71,0%</div>
    <div style="height:52px;background:linear-gradient(to right, #fef3e7, #fde8c8);border-radius:6px;margin-bottom:.6rem;opacity:.7"></div>
    <div style="display:flex;justify-content:space-between;font-size:.7rem;color:#888;border-top:1px solid #eee;padding-top:.5rem;margin-top:.2rem">
      <span>🟢 62%</span>
      <span>Mis à jour 14/05 09:41</span>
    </div>
  </div>
  <!-- Carte Hors ligne -->
  <div style="background:#FFFDF7;border-radius:12px;box-shadow:0 2px 6px rgba(61,32,8,.1);padding:1.1rem;border-left:5px solid #888;opacity:.75">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:.65rem">
      <div><div style="font-weight:700;font-size:.92rem;color:#3D2008">Laboratoire</div><div style="font-size:.72rem;color:#6B3A1F;margin-top:.1rem">laboratoire</div></div>
      <span style="background:#eee;color:#888;font-size:.68rem;padding:.18rem .55rem;border-radius:12px;font-weight:700;text-transform:uppercase;flex-shrink:0">Hors ligne</span>
    </div>
    <div style="font-size:1.8rem;font-weight:800;line-height:1;margin:.4rem 0 .2rem;font-variant-numeric:tabular-nums;color:#888">— <span style="font-size:1.1rem;font-weight:400">°C</span></div>
    <div style="font-size:.8rem;color:#888;margin-bottom:.65rem">Humidité : —</div>
    <div style="height:52px;background:#eee;border-radius:6px;margin-bottom:.6rem;opacity:.5"></div>
    <div style="display:flex;justify-content:space-between;font-size:.7rem;color:#888;border-top:1px solid #eee;padding-top:.5rem;margin-top:.2rem">
      <span>🔴 12%</span>
      <span>Aucun signal récent</span>
    </div>
  </div>
</div>

### Lire une carte

| Zone de la carte | Signification |
|---|---|
| **Bord gauche coloré** | Vert = OK · Orange = Attention · Rouge = Alerte · Gris = Hors ligne |
| **Badge statut** (coin haut droit) | Résumé de l'état : OK / Attention / Alerte / Hors ligne |
| **Encart rouge** (si alerte) | Type d'alerte et durée écoulée — *"Température trop haute — depuis 23 min"* |
| **Grande valeur** | Température actuelle en °C — rouge si hors seuil |
| **Humidité** | Taux d'humidité actuel |
| **Mini courbe** | Évolution des dernières 24h (invisible si aucun relevé disponible) |
| **Batterie** | Niveau de batterie de la sonde : 🟢 ≥ 40% · 🟠 20–39% · 🔴 < 20% |
| **Mis à jour** | Date et heure du dernier relevé reçu |

> **Tapez une carte** pour basculer automatiquement sur l'onglet **Historique** avec cette enceinte déjà sélectionnée en période **24h**.

### Seuils normaux des enceintes

Les seuils par défaut configurés pour l'établissement :

| Enceinte | Seuil bas | Seuil haut | Zone |
|---|---|---|---|
| Chambres froides | 0°C | 4°C | Contact direct avec les viandes |
| Vitrine réfrigérée | 0°C | 4°C | Présentation des produits |
| Laboratoire | 10°C | 15°C | Zone de travail et découpe |

La zone **Attention** s'active quand la température s'approche d'une limite (moins de 0,5°C d'écart). Une **alerte** ne se déclenche qu'après 5 minutes de dépassement continu — un simple courant d'air lors de l'ouverture d'une porte ne crée pas d'alerte.

---

## Onglet Historique

Tapez **Historique** dans la barre d'onglets pour consulter les relevés sur une période.

### Choisir l'enceinte et la période

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:12px;padding:.9rem;margin:.4rem 0 .8rem;display:flex;flex-direction:column;gap:.7rem">
  <div>
    <div style="font-size:.82rem;font-weight:600;color:#6B3A1F;margin-bottom:.4rem">Enceinte</div>
    <div style="display:flex;flex-wrap:wrap;gap:.4rem">
      <button style="padding:.45rem .9rem;border:1.5px solid #6B3A1F;background:#6B3A1F;border-radius:8px;font-size:.85rem;font-weight:600;color:#FFF">Chambre froide 1</button>
      <button style="padding:.45rem .9rem;border:1.5px solid #D4A574;background:#FFF;border-radius:8px;font-size:.85rem;font-weight:500;color:#6B3A1F">Chambre froide 2</button>
      <button style="padding:.45rem .9rem;border:1.5px solid #D4A574;background:#FFF;border-radius:8px;font-size:.85rem;font-weight:500;color:#6B3A1F">Vitrine</button>
      <button style="padding:.45rem .9rem;border:1.5px solid #D4A574;background:#FFF;border-radius:8px;font-size:.85rem;font-weight:500;color:#6B3A1F">Laboratoire</button>
    </div>
  </div>
  <div>
    <div style="font-size:.82rem;font-weight:600;color:#6B3A1F;margin-bottom:.4rem">Période</div>
    <div style="display:flex;flex-wrap:wrap;gap:.4rem">
      <button style="padding:.45rem .9rem;border:1.5px solid #6B3A1F;background:#6B3A1F;border-radius:8px;font-size:.85rem;font-weight:600;color:#FFF">24h</button>
      <button style="padding:.45rem .9rem;border:1.5px solid #D4A574;background:#FFF;border-radius:8px;font-size:.85rem;font-weight:500;color:#6B3A1F">7 jours</button>
      <button style="padding:.45rem .9rem;border:1.5px solid #D4A574;background:#FFF;border-radius:8px;font-size:.85rem;font-weight:500;color:#6B3A1F">30 jours</button>
      <button style="padding:.45rem .9rem;border:1.5px solid #D4A574;background:#FFF;border-radius:8px;font-size:.85rem;font-weight:500;color:#6B3A1F">Personnalisée</button>
    </div>
  </div>
  <button style="background:#FFF;border:1.5px solid #D4A574;color:#6B3A1F;padding:.4rem .85rem;border-radius:8px;font-size:.82rem;font-weight:600;align-self:flex-start">Exporter CSV</button>
</div>

**1 — Choisissez l'enceinte** en tapant un bouton dans la rangée du haut. L'enceinte active est sur fond marron.

**2 — Choisissez la période :**

| Bouton | Données affichées |
|---|---|
| **24h** | Aujourd'hui en entier (de 00:00 à 23:59) — correspond à la **journée HACCP** |
| **7 jours** | Les 7 derniers jours depuis maintenant |
| **30 jours** | Les 30 derniers jours depuis maintenant |
| **Personnalisée** | Deux champs Date début / Date fin s'affichent → tapez **`Appliquer`** |

> **Important — "24h" ne signifie pas "les 24 dernières heures"**, mais bien **la journée en cours** de 00h00 à 23h59. Cela correspond à la journée HACCP standard.

**3 — Export CSV :** tapez **`Exporter CSV`** pour télécharger un fichier tableur avec tous les relevés bruts (horodatage, température, humidité, batterie, qualité du signal) pour cette enceinte et cette période.

### Le bandeau de statistiques

Cinq métriques calculées sur la période sélectionnée :

<div style="display:flex;gap:.6rem;flex-wrap:wrap;margin:.4rem 0 .8rem">
  <div style="background:#FFFDF7;border-radius:10px;box-shadow:0 2px 6px rgba(61,32,8,.08);padding:.8rem 1rem;flex:1;min-width:100px;text-align:center">
    <div style="font-size:1.2rem;font-weight:800;color:#C93030">0,8°C</div>
    <div style="font-size:.7rem;color:#6B3A1F;margin-top:.2rem">T° min</div>
  </div>
  <div style="background:#FFFDF7;border-radius:10px;box-shadow:0 2px 6px rgba(61,32,8,.08);padding:.8rem 1rem;flex:1;min-width:100px;text-align:center">
    <div style="font-size:1.2rem;font-weight:800;color:#3D2008">2,4°C</div>
    <div style="font-size:.7rem;color:#6B3A1F;margin-top:.2rem">T° moy</div>
  </div>
  <div style="background:#FFFDF7;border-radius:10px;box-shadow:0 2px 6px rgba(61,32,8,.08);padding:.8rem 1rem;flex:1;min-width:100px;text-align:center">
    <div style="font-size:1.2rem;font-weight:800;color:#C93030">5,8°C</div>
    <div style="font-size:.7rem;color:#6B3A1F;margin-top:.2rem">T° max</div>
  </div>
  <div style="background:#FFFDF7;border-radius:10px;box-shadow:0 2px 6px rgba(61,32,8,.08);padding:.8rem 1rem;flex:1;min-width:100px;text-align:center">
    <div style="font-size:1.2rem;font-weight:800;color:#3D2008">79,2%</div>
    <div style="font-size:.7rem;color:#6B3A1F;margin-top:.2rem">Hum. moy</div>
  </div>
  <div style="background:#FFFDF7;border-radius:10px;box-shadow:0 2px 6px rgba(61,32,8,.08);padding:.8rem 1rem;flex:1;min-width:100px;text-align:center">
    <div style="font-size:1.2rem;font-weight:800;color:#3D2008">288</div>
    <div style="font-size:.7rem;color:#6B3A1F;margin-top:.2rem">Relevés</div>
  </div>
</div>

La **T° min** et la **T° max** s'affichent en rouge si elles sortent des seuils de l'enceinte.

### Le graphique

Le graphique affiche la courbe de température dans le temps, avec deux lignes pointillées : le **seuil minimum** et le **seuil maximum** de l'enceinte. Les dépassements sont visuellement identifiables car la courbe franchit une ligne de seuil.

### Le tableau agrégé

Sous le graphique, un tableau résume les relevés :
- **Par heure** si la période est 24h
- **Par jour** si la période est 7j, 30j ou personnalisée

<div style="overflow-x:auto;border-radius:10px;box-shadow:0 2px 6px rgba(61,32,8,.08);margin:.4rem 0 .8rem">
  <table style="width:100%;border-collapse:collapse;background:#FFFDF7;font-size:.82rem">
    <thead><tr style="background:#3D2008;color:#F5ECD7"><th style="padding:.55rem .8rem;text-align:left;white-space:nowrap">Heure</th><th style="padding:.55rem .8rem;text-align:left">T° min</th><th style="padding:.55rem .8rem;text-align:left">T° moy</th><th style="padding:.55rem .8rem;text-align:left">T° max</th><th style="padding:.55rem .8rem;text-align:left">Hum. moy</th><th style="padding:.55rem .8rem;text-align:left">Relevés</th><th style="padding:.55rem .8rem;text-align:left">Conformité</th></tr></thead>
    <tbody>
      <tr style="border-bottom:1px solid #ede7dc"><td style="padding:.45rem .8rem">08:00</td><td style="padding:.45rem .8rem">1,2</td><td style="padding:.45rem .8rem">1,8</td><td style="padding:.45rem .8rem">2,4</td><td style="padding:.45rem .8rem">77%</td><td style="padding:.45rem .8rem">12</td><td style="padding:.45rem .8rem;font-weight:700;color:#2D7D46">✓ Conforme</td></tr>
      <tr style="border-bottom:1px solid #ede7dc"><td style="padding:.45rem .8rem">09:00</td><td style="padding:.45rem .8rem">2,1</td><td style="padding:.45rem .8rem">3,4</td><td style="padding:.45rem .8rem;font-weight:700;color:#C93030">5,8</td><td style="padding:.45rem .8rem">81%</td><td style="padding:.45rem .8rem">11</td><td style="padding:.45rem .8rem;font-weight:700;color:#C93030">✗ Hors seuil</td></tr>
      <tr><td style="padding:.45rem .8rem">10:00</td><td style="padding:.45rem .8rem">1,9</td><td style="padding:.45rem .8rem">2,2</td><td style="padding:.45rem .8rem">2,7</td><td style="padding:.45rem .8rem">79%</td><td style="padding:.45rem .8rem">12</td><td style="padding:.45rem .8rem;font-weight:700;color:#2D7D46">✓ Conforme</td></tr>
    </tbody>
  </table>
</div>

La colonne **Conformité** est verte (`✓ Conforme`) si toutes les températures de la tranche sont dans les seuils, rouge (`✗ Hors seuil`) dès qu'une seule valeur en sort. Les valeurs individuelles hors seuil sont aussi affichées en rouge dans leur colonne.

---

## Onglet Alertes

Tapez **Alertes** pour consulter l'historique des dépassements de température.

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:12px;padding:.9rem;margin:.4rem 0 .8rem">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.9rem">
    <span style="font-size:.92rem;font-weight:700;color:#3D2008">Alertes de dépassement de température</span>
    <label style="font-size:.82rem;font-weight:600;display:flex;align-items:center;gap:.3rem"><input type="checkbox" /> Afficher les alertes fermées</label>
  </div>
  <div style="display:flex;flex-direction:column;gap:.7rem">
    <!-- Alerte en cours -->
    <div style="background:#FFFDF7;border-radius:12px;box-shadow:0 2px 6px rgba(61,32,8,.08);padding:1rem 1.2rem;display:grid;grid-template-columns:auto 1fr auto;gap:.5rem 1rem;align-items:center;border-left:4px solid #C93030">
      <span style="font-size:1.3rem">🔴</span>
      <div>
        <div style="font-size:.9rem;font-weight:700;color:#3D2008">🌡️ Température trop haute</div>
        <div style="font-size:.72rem;color:#666;margin-top:.15rem">Boutique — Chambre froide 2 · Valeur : 5,8°C · Seuil : 4,0°C · Début : 14/05 09:18</div>
      </div>
      <span style="font-size:.72rem;color:#6B3A1F;text-align:right;font-weight:600">depuis 23 min</span>
    </div>
    <!-- Alerte fermée -->
    <div style="background:#FFFDF7;border-radius:12px;box-shadow:0 2px 6px rgba(61,32,8,.08);padding:1rem 1.2rem;display:grid;grid-template-columns:auto 1fr auto;gap:.5rem 1rem;align-items:center;border-left:4px solid #2D7D46;opacity:.75">
      <span style="font-size:1.3rem">✅</span>
      <div>
        <div style="font-size:.9rem;font-weight:700;color:#3D2008">❄️ Température trop basse</div>
        <div style="font-size:.72rem;color:#666;margin-top:.15rem">Boutique — Vitrine réfrigérée · Valeur : -0,3°C · Seuil : 0,0°C · Début : 13/05 22:05 · Fin : 13/05 22:31</div>
      </div>
      <span style="font-size:.72rem;color:#6B3A1F;text-align:right;font-weight:600">26 min</span>
    </div>
  </div>
</div>

### Lire les alertes

| Icône | Bord | Signification |
|---|---|---|
| 🔴 | Rouge | Alerte **en cours** — la température est encore hors seuil |
| ✅ | Vert (estompé) | Alerte **fermée** — la température est revenue dans les seuils |

Pour chaque alerte : type (`🌡️ Température trop haute` ou `❄️ Température trop basse`), enceinte concernée, valeur mesurée, seuil dépassé, heure de début (et heure de fin pour les alertes fermées), durée.

**Seules les alertes de température** sont listées ici (pas les alertes de perte de signal ou de batterie faible).

Par défaut, seules les **alertes en cours** sont affichées. Cochez **"Afficher les alertes fermées"** pour voir aussi l'historique des alertes passées, triées par date décroissante.

---

## Onglet Rapports

Tapez **Rapports** pour accéder aux outils de génération de rapports.

### Rapport interactif pour le contrôleur DDPP

<div style="background:linear-gradient(135deg, #3D2008, #6B3A1F);color:#F5ECD7;padding:1.1rem 1.3rem;border-radius:12px;margin:.4rem 0 .8rem;display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap;box-shadow:0 4px 20px rgba(61,32,8,.15)">
  <div>
    <div style="font-size:.95rem;font-weight:700;margin-bottom:.2rem">📊 Rapport interactif pour contrôleur DDPP</div>
    <div style="font-size:.82rem;color:#D4A574">Graphiques dynamiques, filtres de période, export PDF en 1 clic</div>
  </div>
  <button style="background:#D4A574;color:#3D2008;border:none;padding:.65rem 1.3rem;border-radius:8px;font-weight:700;font-size:.9rem">✨ Ouvrir le rapport</button>
</div>

Tapez **`✨ Ouvrir le rapport`** pour afficher dans un nouvel onglet le rapport officiel des **90 derniers jours** — celui à montrer lors d'un contrôle DDPP. Il comprend des graphiques interactifs et un bouton d'export PDF.

### Rapport figé (archive PDF)

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:12px;padding:.9rem;margin:.4rem 0 .8rem">
  <div style="display:flex;flex-wrap:wrap;gap:.7rem;align-items:flex-end">
    <div><div style="font-size:.75rem;font-weight:600;margin-bottom:.3rem">Type de rapport</div><select style="border:1.5px solid #D4A574;border-radius:8px;padding:.4rem .7rem;font-size:.85rem;background:#FFF"><option>Journalier</option><option>Mensuel</option></select></div>
    <div><div style="font-size:.75rem;font-weight:600;margin-bottom:.3rem">Date début</div><input type="date" style="border:1.5px solid #D4A574;border-radius:8px;padding:.4rem .7rem;font-size:.85rem;background:#FFF" /></div>
    <div><div style="font-size:.75rem;font-weight:600;margin-bottom:.3rem">Date fin</div><input type="date" style="border:1.5px solid #D4A574;border-radius:8px;padding:.4rem .7rem;font-size:.85rem;background:#FFF" /></div>
    <button style="background:#6B3A1F;color:#FFF;border:none;border-radius:8px;padding:.55rem 1rem;font-size:.88rem;font-weight:700">Générer le rapport</button>
  </div>
</div>

Pour générer un rapport archivé :
1. Choisissez le **type** : Journalier (une journée) ou Mensuel (un mois complet)
2. Renseignez la **date début** et la **date fin**
3. Tapez **`Générer le rapport`**

Le rapport apparaît dans la liste **"Rapports générés"** sous le formulaire, avec : type, plage de dates, date de génération, badge `Conforme` (vert) ou `Non conforme` (rouge), et un lien **`📄 PDF`** pour le télécharger.

### Rapport journalier depuis les données brutes CSV

Choisissez une **date** et tapez **`Charger`** pour voir une grille de cartes récapitulatives, une carte par sonde :

<div style="display:grid;grid-template-columns:1fr 1fr;gap:.7rem;margin:.4rem 0 .8rem">
  <div style="background:#FFFDF7;border-radius:10px;padding:.9rem;box-shadow:0 1px 4px rgba(0,0,0,.06);display:flex;flex-direction:column;gap:.5rem">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:.4rem"><span style="font-size:.85rem;color:#6B3A1F;font-weight:700;text-transform:capitalize">chambre_froide_1</span><span style="background:#e6f4ea;color:#2D7D46;font-size:.7rem;font-weight:700;padding:.15rem .5rem;border-radius:20px">Conforme</span></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:.25rem .5rem;font-size:.82rem"><div style="display:flex;justify-content:space-between"><span style="color:#888">T° min</span><span style="font-weight:600">0,8°C</span></div><div style="display:flex;justify-content:space-between"><span style="color:#888">T° moy</span><span style="font-weight:600">2,1°C</span></div><div style="display:flex;justify-content:space-between"><span style="color:#888">T° max</span><span style="font-weight:600">3,9°C</span></div><div style="display:flex;justify-content:space-between"><span style="color:#888">Relevés</span><span style="font-weight:600">288</span></div></div>
    <a href="#" style="text-align:center;font-size:.78rem;padding:.3rem .55rem;background:#f0e8dc;color:#6B3A1F;border-radius:6px;text-decoration:none;font-weight:600">⬇ Télécharger CSV</a>
  </div>
  <div style="background:#FFFDF7;border-radius:10px;padding:.9rem;box-shadow:0 1px 4px rgba(0,0,0,.06);display:flex;flex-direction:column;gap:.5rem">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:.4rem"><span style="font-size:.85rem;color:#6B3A1F;font-weight:700;text-transform:capitalize">chambre_froide_2</span><span style="background:#fdecea;color:#C93030;font-size:.7rem;font-weight:700;padding:.15rem .5rem;border-radius:20px">Hors seuil</span></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:.25rem .5rem;font-size:.82rem"><div style="display:flex;justify-content:space-between"><span style="color:#888">T° min</span><span style="font-weight:600">1,1°C</span></div><div style="display:flex;justify-content:space-between"><span style="color:#888">T° moy</span><span style="font-weight:600">3,2°C</span></div><div style="display:flex;justify-content:space-between"><span style="color:#888">T° max</span><span style="font-weight:600;color:#C93030">5,8°C</span></div><div style="display:flex;justify-content:space-between"><span style="color:#888">Relevés</span><span style="font-weight:600">285</span></div></div>
    <a href="#" style="text-align:center;font-size:.78rem;padding:.3rem .55rem;background:#f0e8dc;color:#6B3A1F;border-radius:6px;text-decoration:none;font-weight:600">⬇ Télécharger CSV</a>
  </div>
</div>

Chaque carte affiche T° min/moy/max, humidité si disponible, nombre de relevés, et un badge **`Conforme`** (T° max ≤ 4°C) ou **`Hors seuil`** (T° max > 4°C). Tapez **`⬇ Télécharger CSV`** pour obtenir le fichier brut de chaque sonde.

---

## Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Que faire |
|---|---|
| Badge **Hors ligne** sur une carte | Le capteur Zigbee ne répond plus — vérifiez sa batterie et qu'il est bien en place dans l'enceinte |
| Badge **Alerte** + bandeau rouge | La température dépasse le seuil depuis plus de 5 minutes — vérifiez physiquement l'enceinte et agissez |
| Tableau de bord vide (aucune carte) | Aucune enceinte n'est configurée — contactez le responsable |
| Message *"Erreur lors du chargement des données."* | Problème de connexion au serveur — rafraîchissez la page |
| Message *"Sélectionne les deux dates."* | En période personnalisée, les deux champs Date début et Date fin doivent être remplis |
| Message *"Erreur lors de la génération."* | Le serveur n'a pas pu créer le rapport — vérifiez la connexion et réessayez |
| Message *"Aucun CSV disponible pour le [date]."* | Pas de données pour cette journée — vérifiez que les capteurs fonctionnaient ce jour-là |
| Message *"Aucune alerte de température."* | Bonne nouvelle : aucun dépassement enregistré sur la période |

---

---

# Module 16 — Rapports & Historique Unifié

Ce module regroupe deux espaces distincts mais complémentaires :
- La **génération de rapports** de conformité températures (couverte au Module 15, onglet Rapports)
- La page **Historique Unifié** (`/historique.html`) : portail unique pour consulter toutes les données historiques de l'application — relevés, réceptions, fabrications, cuissons, refroidissements, ouvertures, nettoyage, nuisibles et rapports.

**Accès :** Hub principal → tuile **Historique** (`/historique.html`).

---

## Rappel — Les 3 types de rapports de température

Les rapports sont accessibles depuis l'onglet **Rapports** de la page Températures (Module 15). Un résumé rapide :

| Rapport | Usage | Comment y accéder |
|---|---|---|
| **Rapport interactif DDPP** | À montrer lors d'un contrôle sanitaire — graphiques des 90 derniers jours, exportable en PDF | Températures → Rapports → `✨ Ouvrir le rapport` |
| **Rapport figé (archive PDF)** | Archivage réglementaire — générez un PDF pour une période précise | Températures → Rapports → formulaire Type + dates → `Générer le rapport` |
| **Rapport CSV brut** | Analyse tableur par sonde pour une journée | Températures → Rapports → choisissez une date → `Charger` |

> Pour le détail complet de ces outils, reportez-vous au **Module 15 — onglet Rapports**.

---

## Page Historique Unifié (`/historique.html`)

La page Historique Unifié est le **portail central d'archivage** de l'application. Toutes les données enregistrées au fil du temps sont consultables depuis un seul endroit, organisées en 4 catégories et 10 sous-onglets.

### La navigation à deux niveaux

<div style="background:#FFFDF7;border:1.5px solid #e8d9c4;border-radius:14px;overflow:hidden;margin:.5rem 0 .9rem">
  <!-- Header -->
  <div style="background:#6B3A1F;color:#FFF;padding:0 12px;height:64px;display:flex;align-items:center;justify-content:space-between">
    <button style="background:none;border:2px solid rgba(255,255,255,.5);border-radius:8px;color:#FFF;font-size:.88rem;font-weight:600;height:48px;padding:0 12px">← Retour</button>
    <span style="font-weight:700;font-size:.92rem;text-align:center;flex:1;padding:0 .5rem">HISTORIQUE</span>
    <span style="font-size:.85rem;font-weight:600;min-width:48px;text-align:right">09:42</span>
  </div>
  <!-- Niveau 1 — Catégories -->
  <div style="display:flex;background:#6B3A1F;border-bottom:2px solid #3D2008;overflow-x:auto">
    <button style="flex:1 0 auto;min-width:130px;background:transparent;border:none;color:rgba(255,255,255,.75);font-size:.82rem;font-weight:700;padding:12px 12px;text-transform:uppercase;letter-spacing:.04em;border-bottom:4px solid transparent;white-space:nowrap">🌡️ Températures</button>
    <button style="flex:1 0 auto;min-width:130px;background:transparent;border:none;color:rgba(255,255,255,.75);font-size:.82rem;font-weight:700;padding:12px 12px;text-transform:uppercase;letter-spacing:.04em;border-bottom:4px solid transparent;white-space:nowrap">📦 Flux produits</button>
    <button style="flex:1 0 auto;min-width:130px;background:rgba(0,0,0,.18);border:none;color:#FFF;font-size:.82rem;font-weight:700;padding:12px 12px;text-transform:uppercase;letter-spacing:.04em;border-bottom:4px solid #D4A574;white-space:nowrap">🧹 HACCP</button>
    <button style="flex:1 0 auto;min-width:100px;background:transparent;border:none;color:rgba(255,255,255,.75);font-size:.82rem;font-weight:700;padding:12px 12px;text-transform:uppercase;letter-spacing:.04em;border-bottom:4px solid transparent;white-space:nowrap">📄 Rapports</button>
  </div>
  <!-- Niveau 2 — Sous-onglets HACCP -->
  <div style="background:#D4A574;border-bottom:2px solid #6B3A1F;display:flex;overflow-x:auto">
    <button style="flex:1 0 auto;background:#6B3A1F;border:none;color:#FFF;font-size:.82rem;font-weight:700;padding:10px 14px;text-transform:uppercase;letter-spacing:.04em;border-bottom:4px solid #FFF;white-space:nowrap">✂️ Ouvertures</button>
    <button style="flex:1 0 auto;background:transparent;border:none;color:#6B3A1F;font-size:.82rem;font-weight:700;padding:10px 14px;text-transform:uppercase;letter-spacing:.04em;border-bottom:4px solid transparent;white-space:nowrap">🧹 Nettoyage</button>
    <button style="flex:1 0 auto;background:transparent;border:none;color:#6B3A1F;font-size:.82rem;font-weight:700;padding:10px 14px;text-transform:uppercase;letter-spacing:.04em;border-bottom:4px solid transparent;white-space:nowrap">🐀 Nuisibles</button>
  </div>
</div>

**Niveau 1 — Catégories** (barre sombre) : tapez une catégorie pour afficher ses sous-onglets. La catégorie active a un fond légèrement plus sombre et un soulignement sable.

**Niveau 2 — Sous-onglets** (barre sable) : tapez un sous-onglet pour charger son contenu. Le sous-onglet actif est sur fond marron foncé.

L'onglet **🧹 HACCP → ✂️ Ouvertures** est actif par défaut à l'ouverture de la page.

---

### Catégorie 🌡️ Températures

#### Sous-onglet : Relevés

Affiche un message de renvoi vers le module dédié avec un bouton **`📊 Ouvrir le module Température →`** qui vous ramène directement sur la page Températures en vue Historique. Les graphiques, statistiques et exports CSV sont gérés là-bas (Module 15).

#### Sous-onglet : Étalonnages

Liste des étalonnages EET01 enregistrés (voir Module 8). Chaque ligne indique la date, le thermomètre étalonné, la température mesurée, le résultat et l'opérateur.

---

### Catégorie 📦 Flux produits

#### Sous-onglet : Réceptions

Consultez toutes les réceptions fournisseurs enregistrées. Filtres disponibles : Recherche produit/lot (avec autocomplétion `▾`), Fournisseur (avec autocomplétion `▾`), dates **Du** et **Au**, boutons `🔍 Rechercher` et `✕ Reset`.

Chaque réception est une **carte cliquable** qui se déplie pour révéler les détails :

<div style="display:flex;flex-direction:column;gap:8px;margin:.4rem 0 .8rem">
  <!-- Carte réception repliée -->
  <div style="background:#FFF;border-radius:10px;border-left:5px solid #2D7D46;box-shadow:0 2px 6px rgba(61,32,8,.1);padding:12px 14px">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
      <div>
        <div style="font-size:.95rem;font-weight:700;color:#3D2008">12/05/2026 — Bovins du Gers</div>
        <div style="font-size:.82rem;color:#777;margin-top:2px">3 produits réceptionnés</div>
      </div>
      <span style="background:rgba(45,125,70,.15);color:#2D7D46;font-size:.75rem;font-weight:700;border-radius:12px;padding:3px 8px;white-space:nowrap">Conforme</span>
    </div>
  </div>
  <!-- Carte réception dépliée -->
  <div style="background:#FFF;border-radius:10px;border-left:5px solid #C93030;box-shadow:0 2px 6px rgba(61,32,8,.1);padding:12px 14px">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:10px">
      <div>
        <div style="font-size:.95rem;font-weight:700;color:#3D2008">13/05/2026 — Volailles du Sud</div>
        <div style="font-size:.82rem;color:#777;margin-top:2px">2 produits réceptionnés</div>
      </div>
      <span style="background:rgba(201,48,48,.12);color:#C93030;font-size:.75rem;font-weight:700;border-radius:12px;padding:3px 8px;white-space:nowrap">NC</span>
    </div>
    <!-- Détails dépliés -->
    <div style="font-size:.72rem;font-weight:700;color:#6B3A1F;text-transform:uppercase;letter-spacing:.04em;margin:10px 0 5px;border-bottom:1px solid #D4A574;padding-bottom:3px">Informations camion</div>
    <div style="display:flex;flex-wrap:wrap;gap:14px;margin-bottom:10px">
      <div style="display:flex;flex-direction:column;gap:1px"><span style="font-size:.7rem;color:#888;text-transform:uppercase;letter-spacing:.03em">Températ. camion</span><span style="font-size:.88rem;font-weight:600">3,2°C</span></div>
      <div style="display:flex;flex-direction:column;gap:1px"><span style="font-size:.7rem;color:#888;text-transform:uppercase;letter-spacing:.03em">Transporteur</span><span style="font-size:.88rem;font-weight:600">TransFroid</span></div>
    </div>
    <div style="font-size:.72rem;font-weight:700;color:#6B3A1F;text-transform:uppercase;letter-spacing:.04em;margin:8px 0 5px;border-bottom:1px solid #D4A574;padding-bottom:3px">Produits</div>
    <div style="display:flex;flex-direction:column;gap:8px">
      <div style="background:#F5ECD7;border-radius:8px;border:1px solid #D4A574;padding:9px 11px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:5px">
          <span style="font-size:.92rem;font-weight:700">Poulet entier</span>
          <span style="background:rgba(45,125,70,.15);color:#2D7D46;font-size:.72rem;font-weight:700;border-radius:12px;padding:2px 7px">Conforme</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:3px 10px;font-size:.78rem"><div style="display:flex;flex-direction:column;gap:1px"><span style="font-size:.68rem;color:#888;text-transform:uppercase">Lot</span><span style="font-weight:500">VL0513-001</span></div><div style="display:flex;flex-direction:column;gap:1px"><span style="font-size:.68rem;color:#888;text-transform:uppercase">DLC</span><span style="font-weight:500">17/05/2026</span></div></div>
      </div>
      <div style="background:rgba(201,48,48,.04);border-radius:8px;border:1px solid #C93030;padding:9px 11px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:5px">
          <span style="font-size:.92rem;font-weight:700">Dinde cuisse</span>
          <span style="background:rgba(201,48,48,.12);color:#C93030;font-size:.72rem;font-weight:700;border-radius:12px;padding:2px 7px">NC</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:3px 10px;font-size:.78rem"><div style="display:flex;flex-direction:column;gap:1px"><span style="font-size:.68rem;color:#888;text-transform:uppercase">Lot</span><span style="font-weight:500">VL0513-002</span></div><div style="display:flex;flex-direction:column;gap:1px"><span style="font-size:.68rem;color:#888;text-transform:uppercase">DLC</span><span style="font-weight:500">16/05/2026</span></div></div>
      </div>
    </div>
  </div>
</div>

En-tête d'une carte : date, fournisseur, nombre de produits, badge **Conforme** (vert) / **NC** (rouge) / **En cours** / **Refusée**. En dépliée : informations camion (température, transporteur), lien vers la photo du bon de livraison, et la liste complète des produits réceptionnés avec leurs critères visuels et badges NC.

#### Sous-onglet : Fabrications

Filtres : Recherche produit/lot (`▾`), Tri, dates Du/Au.

Chaque carte affiche l'icône 🏭, le nom du produit fini, le numéro de lot interne (format `MC-AAAAMMJJ-XXXX`), la date de fabrication, la DLC et le poids fabriqué. Dépliée : liste des ingrédients avec quantité, lot source et DLC de chaque ingrédient.

#### Sous-onglet : Cuissons

Filtres : Recherche produit/lot, Espèce, Tri, Type (Rôtissoire / Four), dates Du/Au.

Chaque carte affiche la température de sortie colorée : **verte** si ≥ 75°C (conforme HACCP), **rouge** si < 75°C (non conforme). Le badge de conformité, le nom du produit, le lot, la date et l'heure sont aussi affichés.

#### Sous-onglet : Refroidissements

Filtres : Recherche produit/lot, Espèce, Tri, dates Du/Au.

Chaque carte indique la durée du refroidissement, la température initiale (à la sortie cuisson) et la température finale. La carte est verte si conforme (≤ 10°C en ≤ 2h), rouge si la règle HACCP n'a pas été respectée (mention JETER).

#### Sous-onglet : Devenir DLC

Filtres : Recherche produit/lot, Tri, **Devenir** (Jetés / Vendus / Consommés / Autre), **Source** (Réceptions / Fabrications), dates Du/Au.

Historique de toutes les sorties de stock enregistrées depuis le Calendrier DLC : qui a traité quoi, quand, pour quel motif.

---

### Catégorie 🧹 HACCP

#### Sous-onglet : Ouvertures *(actif par défaut)*

Contenu identique à la page Historique des ouvertures (Module 14) : filtres Produit / dates, cartes avec miniature photo, badges Tracée (vert) / Manuelle (orange), infos réception si tracée. Tapez sur la miniature pour agrandir la photo en plein écran. Bouton **`Voir plus…`** pour charger les suivantes.

#### Sous-onglet : Nettoyage

Consultez le planning de nettoyage historique. Les données sont organisées en arborescence **Année → Mois → Semaine ISO**. Pour chaque semaine, le tableau complet du planning s'affiche (Secteur × Tâche × Produit × 7 jours). Les jours validés affichent l'initiale de l'opérateur en vert.

#### Sous-onglet : Nuisibles

Filtres : Type de piège (Rongeurs / Insectes volants / Insectes rampants / Oiseaux), Année, bouton `🔍 Rechercher`.

Les résultats sont présentés en grille de cases semaine :

<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(65px,1fr));gap:5px;margin:.4rem 0 .8rem">
  <div style="background:rgba(45,125,70,.12);border:1px solid #2D7D46;border-radius:6px;padding:5px 3px;text-align:center">
    <div style="font-weight:700;color:#6B3A1F;font-size:.78rem">S18</div>
    <div style="font-size:.95rem;margin:2px 0">N</div>
    <div style="font-size:.68rem;color:#666">M.</div>
  </div>
  <div style="background:rgba(201,48,48,.12);border:1px solid #C93030;border-radius:6px;padding:5px 3px;text-align:center">
    <div style="font-weight:700;color:#6B3A1F;font-size:.78rem">S19</div>
    <div style="font-size:.95rem;margin:2px 0">O</div>
    <div style="font-size:.68rem;color:#666">J.</div>
  </div>
  <div style="background:#FFF;border:1px solid #D4A574;border-radius:6px;padding:5px 3px;text-align:center;opacity:.4">
    <div style="font-weight:700;color:#6B3A1F;font-size:.78rem">S20</div>
    <div style="font-size:.95rem;margin:2px 0">—</div>
    <div style="font-size:.68rem;color:#666"> </div>
  </div>
  <div style="background:rgba(45,125,70,.12);border:1px solid #2D7D46;border-radius:6px;padding:5px 3px;text-align:center">
    <div style="font-weight:700;color:#6B3A1F;font-size:.78rem">S21</div>
    <div style="font-size:.95rem;margin:2px 0">N</div>
    <div style="font-size:.68rem;color:#666">M.</div>
  </div>
</div>

| Case | Couleur | Signification |
|---|---|---|
| **N** (fond vert) | Vert | Piège **N**égatif — rien capturé, aucun nuisible |
| **O** (fond rouge) | Rouge | Piège **O**ccupé — nuisible détecté, action requise |
| **—** (estompé) | Gris pâle | Semaine non encore contrôlée |

Sous chaque case : initiale de l'opérateur ayant fait le relevé.

---

### Catégorie 📄 Rapports

#### Sous-onglet : Rapports générés

Liste paginée de tous les rapports PDF générés. Identique à la liste de l'onglet Rapports du module Températures : type, plage de dates, date de génération, badge Conforme/Non conforme, et lien **`📄 PDF`** pour téléchargement.

---

## Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Que faire |
|---|---|
| Les données ne se chargent pas dans un onglet | Vérifiez la connexion au serveur et tapez de nouveau le sous-onglet |
| *"Aucun CSV disponible pour le [date]."* | Aucun capteur n'a envoyé de données ce jour-là, ou la date est trop ancienne |
| *"Aucun rapport généré."* | Aucun rapport n'a encore été généré — utilisez le formulaire pour en créer un |
| Le bouton `📄 PDF` ne télécharge rien | Le fichier PDF n'existe plus sur le serveur — régénérez le rapport |
| Photo vide dans les ouvertures | La photo a été supprimée manuellement du serveur |

---

---

# Module 17 — Hub Principal

Le Hub est la **page d'accueil** de HACCP Monitor. C'est là que commence chaque session de travail : il affiche toutes les tuiles de navigation, signale en temps réel les tâches HACCP à faire ou en retard, et indique l'état de la dernière réception.

---

## Vue d'ensemble de l'écran

<div style="background:#F5ECD7;border:2px solid #6B3A1F;border-radius:12px;padding:1.2rem;margin:1rem 0;">

**En-tête (bande sombre en haut)**

<div style="background:#3D2008;color:#F5ECD7;border-radius:8px;padding:0.8rem 1rem;display:flex;align-items:center;justify-content:space-between;gap:0.5rem;font-size:0.95rem;">
  <span style="font-weight:800;letter-spacing:.04em;">Au Comptoir des Lilas</span>
  <span style="color:#D4A574;font-size:0.9rem;">lun. 14 mai — 10:30</span>
  <span style="display:flex;align-items:center;gap:0.5rem;">
    <button style="background:transparent;border:1px solid rgba(255,255,255,.35);border-radius:50%;width:44px;height:44px;font-size:1.3rem;cursor:pointer;">🔔<sup style="background:#C93030;color:#fff;border-radius:50%;font-size:0.6rem;padding:1px 4px;">3</sup></button>
    <a style="border:1px solid rgba(255,255,255,.35);color:#F5ECD7;border-radius:6px;padding:6px 12px;font-size:0.85rem;text-decoration:none;">⚙ Admin</a>
  </span>
</div>

**Grille de navigation (8 tuiles)**

<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:0.75rem;margin-top:0.75rem;">
  <div style="background:#fff;border:3px solid #D4A574;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2rem;">✅</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">TÂCHES HACCP</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">Nettoyage &amp; contrôles</div>
  </div>
  <div style="background:#fff;border:3px solid #D4A574;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2rem;">🏭</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">PRODUCTION</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">Fabrication, Cuisson, Refroidissement</div>
  </div>
  <div style="background:#fff;border:3px solid #2D7D46;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2rem;">📦</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">RÉCEPTION</div>
    <div style="font-size:0.75rem;color:#2D7D46;"><span style="display:inline-block;width:8px;height:8px;background:#2D7D46;border-radius:50%;margin-right:4px;"></span>12 mai · 4 produit(s) · OK</div>
  </div>
  <div style="background:#fff;border:3px solid #D4A574;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2rem;">✂️</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">OUVERTURE</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">Traçabilité ouvertures</div>
  </div>
  <div style="background:#fff;border:3px solid #D4A574;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2rem;">📅</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">CALENDRIER DLC</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">4 sources unifiées</div>
  </div>
  <div style="background:#fff;border:3px solid #D4A574;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2rem;">📋</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">STOCK</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">FIFO toutes sources</div>
  </div>
  <div style="background:#fff;border:3px solid #D4A574;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2rem;">🗂️</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">HISTORIQUE</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">Tous les enregistrements</div>
  </div>
  <div style="background:#fff;border:3px solid #D4A574;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2rem;">📚</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">CATALOGUE</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">Produits &amp; matières premières</div>
  </div>
</div>
</div>

---

## L'en-tête

La barre sombre en haut de l'écran contient quatre éléments :

### Nom de l'établissement
<div style="display:inline-block;background:#3D2008;color:#F5ECD7;font-weight:800;letter-spacing:.04em;padding:6px 14px;border-radius:6px;font-size:0.95rem;">Au Comptoir des Lilas</div>

Fixe, non modifiable depuis cette page.

---

### Horloge en direct
<div style="display:inline-block;background:#3D2008;color:#D4A574;padding:6px 14px;border-radius:6px;font-size:0.9rem;">lun. 14 mai — 10:30</div>

L'horloge affiche le jour de la semaine, la date et l'heure, mis à jour chaque seconde. Elle sert de repère immédiat pour vérifier l'heure sans quitter l'application.

---

### Cloche des tâches HACCP 🔔

La cloche n'est **visible que lorsqu'il y a des tâches à signaler**. Quand tout est en ordre, elle disparaît.

**Cloche normale (tâches à venir) :**
<div style="display:inline-flex;align-items:center;gap:4px;">
  <button style="background:transparent;border:1px solid rgba(255,255,255,.35);border-radius:50%;width:44px;height:44px;font-size:1.3rem;color:#F5ECD7;background:#3D2008;">🔔<sup style="background:#C93030;color:#fff;border-radius:50%;font-size:0.55rem;padding:1px 4px;margin-left:1px;">2</sup></button>
</div>

**Cloche urgente (tâches du jour non faites — animation pulsante) :**
<div style="display:inline-flex;align-items:center;gap:4px;">
  <button style="background:transparent;border:2px solid #C93030;border-radius:50%;width:44px;height:44px;font-size:1.3rem;color:#F5ECD7;background:#3D2008;animation:hub-cloche-pulse 1s ease-in-out infinite;">🔔<sup style="background:#C93030;color:#fff;border-radius:50%;font-size:0.55rem;padding:1px 4px;margin-left:1px;">5</sup></button>
</div>

Le **chiffre rouge** dans le coin supérieur droit de la cloche indique le nombre total de tâches signalées. Un chiffre élevé ou une animation pulsante indique des tâches urgentes du jour.

Tapper la cloche ouvre la popup des tâches HACCP (voir plus bas).

---

### Bouton Admin ⚙

<a style="border:1px solid rgba(255,255,255,.35);color:#F5ECD7;border-radius:6px;padding:6px 12px;font-size:0.85rem;text-decoration:none;background:#3D2008;cursor:pointer;">⚙ Admin</a>

Accès direct à la page d'administration (gestion du personnel, paramètres DLC, enceintes…).

---

## Le bandeau "Connexion perdue"

<div style="background:#E8913A;color:#fff;border-radius:6px;padding:0.6rem 1rem;font-size:0.9rem;font-weight:600;margin:0.5rem 0;">
⚠ Connexion au serveur perdue — vérifiez le Raspberry Pi
</div>

Ce bandeau orange **n'apparaît que dans un cas précis** : quand **toutes les communications avec le serveur échouent simultanément**. Si seulement une partie des données ne charge pas, le bandeau reste masqué.

Que faire si ce bandeau apparaît :
1. Vérifier que la tablette est bien connectée au réseau Wi-Fi de la boucherie
2. Vérifier que le Raspberry Pi est allumé (voyant vert clignotant)
3. Recharger la page après 30 secondes

---

## Les 8 tuiles de navigation

Chaque tuile est un **raccourci direct** vers un module de l'application. Taper dessus ouvre le module correspondant.

### Tuile standard (état normal)

<div style="background:#fff;border:3px solid #D4A574;border-radius:10px;padding:1rem;text-align:center;max-width:200px;display:inline-block;">
  <div style="font-size:2.2rem;">📦</div>
  <div style="font-weight:800;font-size:0.95rem;color:#3D2008;">RÉCEPTION</div>
  <div style="font-size:0.78rem;color:#6B3A1F;">4 sources unifiées</div>
</div>

---

### États des tuiles

Les tuiles peuvent changer d'aspect pour refléter une situation particulière. Seule la tuile **RÉCEPTION** change d'état dynamiquement — les autres restent dans leur état standard.

**Tuile RÉCEPTION — dernière réception conforme :**
<div style="background:#fff;border:3px solid #2D7D46;border-radius:10px;padding:1rem;text-align:center;max-width:200px;display:inline-block;">
  <div style="font-size:2.2rem;">📦</div>
  <div style="font-weight:800;font-size:0.95rem;color:#3D2008;">RÉCEPTION</div>
  <div style="font-size:0.78rem;color:#2D7D46;">
    <span style="display:inline-block;width:8px;height:8px;background:#2D7D46;border-radius:50%;margin-right:4px;vertical-align:middle;"></span>12 mai · 4 produit(s) · OK
  </div>
</div>

**Tuile RÉCEPTION — dernière réception non conforme :**
<div style="background:#fff;border:3px solid #E8913A;border-radius:10px;padding:1rem;text-align:center;max-width:200px;display:inline-block;">
  <div style="font-size:2.2rem;">📦</div>
  <div style="font-weight:800;font-size:0.95rem;color:#3D2008;">RÉCEPTION</div>
  <div style="font-size:0.78rem;color:#E8913A;">
    <span style="display:inline-block;width:8px;height:8px;background:#E8913A;border-radius:50%;margin-right:4px;vertical-align:middle;"></span>11 mai · 2 produit(s) · NC
  </div>
</div>

**Tuile RÉCEPTION — aucune réception récente :**
<div style="background:#fff;border:3px solid #999;border-radius:10px;padding:1rem;text-align:center;max-width:200px;display:inline-block;opacity:0.75;">
  <div style="font-size:2.2rem;">📦</div>
  <div style="font-weight:800;font-size:0.95rem;color:#3D2008;">RÉCEPTION</div>
  <div style="font-size:0.78rem;color:#999;">
    <span style="display:inline-block;width:8px;height:8px;background:#999;border-radius:50%;margin-right:4px;vertical-align:middle;"></span>Aucune réception récente
  </div>
</div>

**Tuile RÉCEPTION — erreur de connexion :**
<div style="background:#fff;border:3px solid #C93030;border-radius:10px;padding:1rem;text-align:center;max-width:200px;display:inline-block;">
  <div style="font-size:2.2rem;">📦</div>
  <div style="font-weight:800;font-size:0.95rem;color:#3D2008;">RÉCEPTION</div>
  <div style="font-size:0.78rem;color:#C93030;">⚠ Connexion perdue</div>
</div>

---

### Résumé des états de la tuile RÉCEPTION

| Couleur de la bordure | Texte affiché | Signification |
|---|---|---|
| Verte | `● JJ mois · N produit(s) · OK` | Dernière réception conforme |
| Orange | `● JJ mois · N produit(s) · NC` | Dernière réception avec non-conformité |
| Grise (atténuée) | `● Aucune réception récente` | Pas encore de réception enregistrée |
| Rouge | `⚠ Connexion perdue` | Le serveur ne répond pas |

---

## La popup "Tâches HACCP"

### Comment s'ouvre-t-elle ?

La popup s'ouvre **automatiquement à chaque arrivée sur le Hub** si des tâches sont à signaler — à condition que le snooze ne soit pas actif. Les rafraîchissements automatiques toutes les 30 secondes ne rouvrent pas la popup : elle ne s'ouvre qu'une seule fois par chargement de page.

Elle peut aussi être ouverte **à tout moment** en tapant la cloche 🔔.

---

### Apparence de la popup

<div style="background:rgba(0,0,0,.55);border-radius:8px;padding:1rem;max-width:540px;margin:0.5rem 0;">
<div style="background:#F5ECD7;border-radius:10px;overflow:hidden;">

  <div style="background:#3D2008;color:#F5ECD7;padding:0.8rem 1rem;display:flex;justify-content:space-between;align-items:center;">
    <span style="font-weight:800;font-size:1rem;">📋 Tâches HACCP</span>
    <button style="background:transparent;border:none;color:#F5ECD7;font-size:1.2rem;cursor:pointer;">✕</button>
  </div>

  <div style="padding:1rem;">
    <h3 style="display:flex;align-items:center;gap:8px;font-size:0.9rem;color:#3D2008;margin-bottom:0.6rem;">
      <span style="display:inline-block;width:12px;height:12px;background:#C93030;border-radius:50%;"></span>
      À faire aujourd'hui
    </h3>
    <ul style="list-style:none;padding:0;margin:0 0 1rem 0;">
      <li style="background:#fde8e8;border-left:4px solid #C93030;border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;font-size:0.88rem;color:#3D2008;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:8px;">
        <span>🧹</span><span><strong>Nettoyage &amp; désinfection</strong><br><small style="color:#6B3A1F;">Quotidien — à valider</small></span><span style="color:#C93030;">›</span>
      </li>
      <li style="background:#fde8e8;border-left:4px solid #C93030;border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;font-size:0.88rem;color:#3D2008;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:8px;">
        <span>🚨</span><span><strong>DLC dépassées</strong><br><small style="color:#6B3A1F;">2 produit(s) à retirer</small></span><span style="color:#C93030;">›</span>
      </li>
    </ul>

    <h3 style="display:flex;align-items:center;gap:8px;font-size:0.9rem;color:#3D2008;margin-bottom:0.6rem;">
      <span style="display:inline-block;width:12px;height:12px;background:#E8913A;border-radius:50%;"></span>
      À venir (≤ 14 jours)
    </h3>
    <ul style="list-style:none;padding:0;margin:0 0 1rem 0;">
      <li style="background:#fff;border-left:4px solid #E8913A;border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;font-size:0.88rem;color:#3D2008;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:8px;">
        <span>🔧</span><span><strong>Étalonnage thermomètre</strong><br><small style="color:#6B3A1F;">Dans 8 jour(s) — 22/05/2026</small></span><span style="color:#E8913A;">›</span>
      </li>
      <li style="background:#fff;border-left:4px solid #E8913A;border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;font-size:0.88rem;color:#3D2008;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:8px;">
        <span>🟠</span><span><strong>DLC à surveiller</strong><br><small style="color:#6B3A1F;">3 produit(s) — DLC dans ≤ 14 j</small></span><span style="color:#E8913A;">›</span>
      </li>
    </ul>

    <button style="width:100%;background:#fff;border:1px solid #6B3A1F;color:#3D2008;border-radius:8px;padding:0.6rem;font-size:0.9rem;cursor:pointer;">🔕 Ne plus afficher pendant 2h</button>
  </div>
</div>
</div>

---

### Sections de la popup

La popup est divisée en deux sections distinctes :

**Section "À faire aujourd'hui"** — pastille rouge 🔴

Contient toutes les tâches qui auraient dû être faites aujourd'hui et qui ne l'ont pas encore été, ainsi que les tâches en retard :

| Icône | Tâche | Détail affiché |
|---|---|---|
| 🧹 | Nettoyage & désinfection | `Quotidien — à valider` |
| 🪤 | Contrôle nuisibles | `Semaine N — manque : [types]` |
| 🔧 | Étalonnage thermomètre | `En retard de N jour(s)` ou `Jamais effectué` |
| 🚨 | DLC dépassées | `N produit(s) à retirer` |
| 🔴 | DLC critiques | `N produit(s) — DLC dans ≤ X j` |

Chaque ligne est **cliquable** : taper dessus ouvre directement le module concerné (Nettoyage, Calendrier DLC…).

**Section "À venir (≤ 14 jours)"** — pastille orange 🟠

Contient les tâches dont l'échéance approche dans les deux prochaines semaines, sans être urgentes aujourd'hui :

| Icône | Tâche | Détail affiché |
|---|---|---|
| 🔧 | Étalonnage thermomètre | `Dans N jour(s) — JJ/MM/AAAA` |
| 🟠 | DLC à surveiller | `N produit(s) — DLC dans ≤ 14 j` |

---

### Ce que vérifie l'application pour construire la popup

L'application consulte quatre sources pour savoir quoi afficher :

**1. Nettoyage (tous les jours)**
Si aucune validation de nettoyage n'a été saisie aujourd'hui → la tâche `🧹 Nettoyage & désinfection` apparaît dans "À faire aujourd'hui".

**2. Nuisibles (toutes les semaines)**
Si au moins un des quatre types de nuisibles (rongeurs, insectes volants, insectes rampants, oiseaux) n'a pas encore été contrôlé cette semaine → la tâche `🪤 Contrôle nuisibles` apparaît avec le détail des types manquants.

**3. Étalonnage thermomètre (tous les 3 mois)**
- Si l'étalonnage n'a jamais été fait, ou s'il est en retard de plus de 92 jours → "À faire aujourd'hui"
- Si l'échéance est dans moins de 14 jours → "À venir"

**4. DLC (en continu — 4 sources de stock)**
- Produits dont la DLC est dépassée et non traités → "À faire aujourd'hui"
- Produits dont la DLC approche du seuil critique → "À faire aujourd'hui"
- Produits dont la DLC arrive dans les 14 jours → "À venir"

> Seuls les produits sans décision de devenir (non encore jetés, vendus ou consommés) sont pris en compte.

---

### Bouton Snooze

<button style="background:#fff;border:1px solid #6B3A1F;color:#3D2008;border-radius:8px;padding:0.6rem 1rem;font-size:0.9rem;cursor:pointer;">🔕 Ne plus afficher pendant 2h</button>

Taper ce bouton **masque la popup automatique pour 2 heures**. Pendant ce temps :
- La popup ne s'ouvre plus toute seule
- La cloche reste visible pour un accès manuel
- Le bouton change d'aspect :

<button style="background:#fff;border:1px solid #C93030;color:#C93030;border-radius:8px;padding:0.6rem 1rem;font-size:0.9rem;cursor:pointer;">🔔 Réafficher l'alerte</button>

Tapper ce bouton annule le snooze immédiatement.

> Le snooze survit à un rechargement de page. Même si vous quittez le Hub et revenez, il reste actif pendant 2 heures.

---

### Fermer la popup

Trois façons de fermer la popup :
- Taper le bouton **✕** en haut à droite
- Taper en dehors de la popup (sur le fond sombre)
- Appuyer sur la touche **Échap** du clavier

---

## Actualisation automatique des données

### Toutes les 30 secondes
L'état de la tuile RÉCEPTION et le résumé des tâches HACCP se mettent à jour **toutes les 30 secondes** en arrière-plan, sans que vous ayez besoin de faire quoi que ce soit. Si une nouvelle tâche urgente apparaît, la cloche se met à clignoter.

### Après 5 minutes d'inactivité
Si personne n'utilise la tablette pendant 5 minutes (aucun toucher, aucun défilement), le Hub **recharge automatiquement la page**. Cela réinitialise l'écran et s'assure que les données affichées sont fraîches.

> Cette fonction est utile lorsque la tablette est posée au comptoir entre les opérations : elle évite d'afficher des données périmées.

---

## Utilisation depuis la tablette (application installée)

HACCP Monitor est configuré comme une **application installable** sur la tablette Android. Une fois installée :
- L'icône apparaît directement sur l'écran d'accueil de la tablette
- L'application s'ouvre en **plein écran**, sans barres de navigation du navigateur
- La barre système Android prend la couleur brun foncé de l'application
- L'application reste partiellement utilisable même si la connexion Wi-Fi est temporairement interrompue

Pour l'installer : ouvrir le Hub dans le navigateur Chrome de la tablette → taper les trois points `⋮` → *"Ajouter à l'écran d'accueil"*.

---

## Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Que faire |
|---|---|
| Bandeau orange `⚠ Connexion au serveur perdue` | Vérifier le Wi-Fi et l'état du Raspberry Pi |
| Tuile RÉCEPTION rouge `⚠ Connexion perdue` | Seule la communication avec les données de réception a échoué — les autres tuiles fonctionnent |
| La cloche a disparu | Il n'y a aucune tâche à signaler — tout est en ordre |
| La popup ne s'affiche plus automatiquement | Le snooze est actif — tapper la cloche manuellement pour voir les tâches |
| La tuile RÉCEPTION affiche "Chargement…" | Les données sont en cours de chargement — attendre quelques secondes |

---

---

# Module 18 — E-Learning (Formation du Personnel)

Le module E-Learning regroupe les **documents de formation** mis à disposition du personnel : guides PDF d'hygiène, guides de découpe par espèce, et le tutoriel interactif de HACCP Monitor. Chaque lecture peut être **validée et tracée** : le prénom de la personne et l'heure de validation sont enregistrés, ce qui permet de prouver lors d'un contrôle que le personnel a bien été formé.

---

## Accès au module

Depuis la page des **Tâches HACCP** → tuile **🎓 E-LEARNING**.

---

## Page d'accueil E-Learning — 3 tuiles

<div style="background:#F5ECD7;border:2px solid #6B3A1F;border-radius:12px;padding:1.2rem;margin:1rem 0;">

<div style="background:#3D2008;color:#F5ECD7;border-radius:8px;padding:0.6rem 1rem;display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
  <a style="border:1px solid rgba(255,255,255,.35);color:#F5ECD7;border-radius:6px;padding:4px 10px;font-size:0.82rem;text-decoration:none;">← Tâches</a>
  <span style="font-weight:800;letter-spacing:.04em;">E-LEARNING</span>
  <span style="color:#D4A574;font-size:0.85rem;">10:30</span>
</div>

<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;">
  <div style="background:#fff;border:3px solid #2D7D46;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2.2rem;">🧼</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">HYGIÈNE</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">Guide des bonnes pratiques</div>
  </div>
  <div style="background:#fff;border:3px solid #2D7D46;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2.2rem;">🔪</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">DÉCOUPE</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">Techniques &amp; sécurité</div>
  </div>
  <div style="background:#fff;border:3px solid #2D7D46;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2.2rem;">📋</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">TUTO HACCP MONITOR</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">Mode d'emploi pas à pas</div>
  </div>
</div>
</div>

Les trois tuiles sont identifiables à leur **bordure verte** — elles sont toutes accessibles.

---

## Formation Hygiène

Taper la tuile **🧼 HYGIÈNE** ouvre une page intermédiaire avec deux choix :

<div style="background:#F5ECD7;border:2px solid #6B3A1F;border-radius:12px;padding:1.2rem;margin:1rem 0;">

<div style="background:#3D2008;color:#F5ECD7;border-radius:8px;padding:0.6rem 1rem;display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
  <a style="border:1px solid rgba(255,255,255,.35);color:#F5ECD7;border-radius:6px;padding:4px 10px;font-size:0.82rem;text-decoration:none;">← E-Learning</a>
  <span style="font-weight:800;letter-spacing:.04em;">HYGIÈNE</span>
  <span style="color:#D4A574;font-size:0.85rem;">10:30</span>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
  <div style="background:#fff;border:3px solid #2D7D46;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2.2rem;">📄</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">DOCUMENT</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">Lire le guide PDF<br><em>Validation traçable</em></div>
  </div>
  <div style="background:#fff;border:3px solid #aaa;border-radius:10px;padding:1rem;text-align:center;opacity:.7;">
    <div style="font-size:2.2rem;">🎓</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">MODULE</div>
    <div style="font-size:0.75rem;color:#999;">Cours interactif + quiz<br><em>Bientôt disponible</em></div>
  </div>
</div>
</div>

| Tuile | Bordure | Ce qu'elle fait |
|---|---|---|
| **📄 DOCUMENT** | Verte | Ouvre le guide PDF hygiène dans la visionneuse avec validation traçable |
| **🎓 MODULE** | Grise (atténuée) | Affiche un message : *"Module interactif disponible prochainement."* — pas encore actif |

---

## Formation Découpe

Taper la tuile **🔪 DÉCOUPE** ouvre une grille de 4 espèces :

<div style="background:#F5ECD7;border:2px solid #6B3A1F;border-radius:12px;padding:1.2rem;margin:1rem 0;">

<div style="background:#3D2008;color:#F5ECD7;border-radius:8px;padding:0.6rem 1rem;display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
  <a style="border:1px solid rgba(255,255,255,.35);color:#F5ECD7;border-radius:6px;padding:4px 10px;font-size:0.82rem;text-decoration:none;">← E-Learning</a>
  <span style="font-weight:800;letter-spacing:.04em;">DÉCOUPE</span>
  <span style="color:#D4A574;font-size:0.85rem;">10:30</span>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
  <div style="background:#fff;border:3px solid #2D7D46;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2.2rem;">🐂</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">BŒUF</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">Guide de découpe<br><em>Validation traçable</em></div>
  </div>
  <div style="background:#fff;border:3px solid #2D7D46;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2.2rem;">🐄</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">VEAU</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">Guide de découpe<br><em>Validation traçable</em></div>
  </div>
  <div style="background:#fff;border:3px solid #2D7D46;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2.2rem;">🐑</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">AGNEAU</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">Guide de découpe<br><em>Validation traçable</em></div>
  </div>
  <div style="background:#fff;border:3px solid #2D7D46;border-radius:10px;padding:1rem;text-align:center;">
    <div style="font-size:2.2rem;">🐖</div>
    <div style="font-weight:800;font-size:0.9rem;color:#3D2008;">PORC</div>
    <div style="font-size:0.75rem;color:#6B3A1F;">Guide de découpe<br><em>Validation traçable</em></div>
  </div>
</div>
</div>

Taper une espèce ouvre directement la **visionneuse PDF** du guide de découpe correspondant.

---

## La visionneuse PDF avec validation traçable

C'est la page centrale du module E-Learning. Elle affiche un document de formation en plein écran et permet d'enregistrer qui l'a lu.

<div style="background:#F5ECD7;border:2px solid #6B3A1F;border-radius:12px;padding:1.2rem;margin:1rem 0;">

<div style="background:#3D2008;color:#F5ECD7;border-radius:8px;padding:0.6rem 1rem;display:flex;align-items:center;justify-content:space-between;margin-bottom:0.5rem;">
  <a style="border:1px solid rgba(255,255,255,.35);color:#F5ECD7;border-radius:6px;padding:4px 10px;font-size:0.82rem;text-decoration:none;">← Retour</a>
  <span style="font-weight:800;letter-spacing:.04em;">HYGIÈNE</span>
  <span style="color:#D4A574;font-size:0.85rem;">10:30</span>
</div>

<div style="background:#2a2a2a;border-radius:6px;height:200px;display:flex;align-items:center;justify-content:center;color:#aaa;font-size:0.9rem;margin-bottom:0.75rem;">
  [ Document PDF affiché ici — lecture libre ]
</div>

<div style="background:#fff;border-top:3px solid #D4A574;border-radius:0 0 8px 8px;padding:0.8rem 1rem;display:flex;align-items:center;justify-content:space-between;gap:0.75rem;flex-wrap:wrap;">
  <span style="font-size:0.8rem;color:rgba(0,0,0,.5);">Dernière lecture : Émile — 14/05/2026 à 09:15</span>
  <div style="display:flex;align-items:center;gap:0.5rem;">
    <select style="border:2px solid #D4A574;border-radius:8px;padding:0.5rem 0.8rem;font-size:0.9rem;font-weight:600;min-width:160px;min-height:44px;">
      <option>— Qui a lu ? —</option>
      <option>Émile</option>
      <option>Marie</option>
    </select>
    <button style="background:#2D7D46;color:#fff;border:none;border-radius:8px;padding:0.7rem 1.2rem;font-size:0.88rem;font-weight:800;min-height:48px;cursor:pointer;">✅ J'AI LU ET COMPRIS</button>
  </div>
</div>
</div>

### Éléments de la barre de validation (en bas de page)

**Dernière lecture :**
<span style="background:#f5f5f5;border-radius:4px;padding:2px 8px;font-size:0.87rem;color:rgba(0,0,0,.55);">Dernière lecture : Émile — 14/05/2026 à 09:15</span>

Indique qui a validé ce document en dernier et à quelle heure. Si personne ne l'a encore lu, le message affiché est : *"Aucune lecture enregistrée pour ce module."*

**Menu déroulant "— Qui a lu ? —" :**
<select style="border:2px solid #D4A574;border-radius:8px;padding:5px 10px;font-size:0.88rem;font-weight:600;min-width:160px;min-height:44px;">
  <option>— Qui a lu ? —</option>
  <option>Émile</option>
  <option>Marie</option>
</select>

Contient les prénoms de tous les membres du personnel actif. Sélectionner son prénom avant de valider.

**Bouton de validation (actif) :**
<button style="background:#2D7D46;color:#fff;border:none;border-radius:8px;padding:0.6rem 1.2rem;font-size:0.88rem;font-weight:800;min-height:48px;cursor:pointer;">✅ J'AI LU ET COMPRIS</button>

**Bouton de validation (désactivé — aucun prénom sélectionné) :**
<button style="background:#2D7D46;color:#fff;border:none;border-radius:8px;padding:0.6rem 1.2rem;font-size:0.88rem;font-weight:800;min-height:48px;cursor:not-allowed;opacity:.45;">✅ J'AI LU ET COMPRIS</button>

Le bouton reste grisé tant qu'aucun prénom n'est choisi dans le menu. Tenter de le taper sans sélection n'a aucun effet.

---

### Mode d'emploi pas-à-pas : lire et valider un document

**Étape 1 — Lire le document**

Le document PDF s'affiche en plein écran. Faire défiler pour tout lire. La barre de navigation native du navigateur permet de passer d'une page à l'autre.

**Étape 2 — Sélectionner son prénom**

Dans la barre en bas de l'écran, taper le menu déroulant et choisir son prénom.

**Étape 3 — Valider la lecture**

Taper le bouton **`✅ J'AI LU ET COMPRIS`** (maintenant actif en vert).

**Étape 4 — Écran de confirmation**

Un écran de confirmation apparaît par-dessus la page :

<div style="background:rgba(0,0,0,.55);border-radius:8px;padding:1rem;max-width:480px;margin:0.5rem 0;">
<div style="background:#F5ECD7;border-radius:12px;padding:2rem 1.5rem;text-align:center;max-width:400px;margin:0 auto;">
  <div style="font-size:3.5rem;line-height:1;margin-bottom:0.8rem;">✅</div>
  <h2 style="font-size:1.3rem;font-weight:800;color:#3D2008;margin:0 0 0.5rem 0;">Lecture enregistrée !</h2>
  <p style="font-size:0.88rem;color:rgba(0,0,0,.6);margin:0 0 1.2rem 0;line-height:1.4;">Émile, votre lecture a été enregistrée à 10:30.<br>La validation est désormais traçable.</p>
  <button style="background:#2D7D46;color:#fff;border:none;border-radius:8px;padding:0.7rem 2rem;font-size:0.9rem;font-weight:800;cursor:pointer;">TERMINER</button>
</div>
</div>

**Étape 5 — Terminer**

Taper **`TERMINER`** ferme l'écran de confirmation et revient à la page précédente (Hygiène ou Découpe selon le document lu).

---

### Ce que signifie "traçable"

Chaque clic sur **`✅ J'AI LU ET COMPRIS`** crée une nouvelle entrée dans le registre de formation avec :
- Le prénom de la personne
- Le document concerné (hygiène, découpe bœuf, découpe veau…)
- La date et l'heure exactes

**Une même personne peut valider plusieurs fois le même document** — il n'y a pas de blocage. Chaque validation s'ajoute au registre, et la barre de la visionneuse affiche toujours la **dernière** en date.

---

## Tutoriel HACCP Monitor (Slideshow)

Taper la tuile **📋 TUTO HACCP MONITOR** ouvre une présentation interactive qui explique pas à pas le fonctionnement de l'application. Ce tutoriel :
- Reproduit fidèlement les vraies interfaces de l'application
- Se parcourt librement (boutons Précédent / Suivant)
- Ne génère **pas** de validation traçable — c'est un support de formation libre, pas un document à signer

---

## Ce qui se passe si quelque chose ne va pas

| Ce que vous voyez | Que faire |
|---|---|
| Le bouton `✅ J'AI LU ET COMPRIS` est grisé | Sélectionner d'abord son prénom dans le menu déroulant |
| Le menu déroulant est vide | La connexion au serveur a échoué — vérifier le Wi-Fi et recharger la page |
| Toast rouge `⚠ Erreur : [détail]` en bas de l'écran | La validation n'a pas pu être enregistrée — réessayer ou signaler le problème |
| Le document PDF ne s'affiche pas | Le fichier PDF est introuvable ou la connexion est coupée |
| Taper **MODULE** (cours interactif) → message pop-up | *"Module interactif disponible prochainement."* — ce module n'est pas encore actif |

---

> **Le tutoriel HACCP Monitor est maintenant complet — 18 modules couverts.**

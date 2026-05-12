# Tutoriel HACCP Monitor — Au Comptoir des Lilas

**Le guide complet, pas à pas, pour utiliser l'application sur la tablette du laboratoire.**

Ce guide est fait pour vous, que vous soyez déjà à l'aise avec un téléphone ou que vous n'ayez jamais touché une tablette. On explique **tout**, dans l'ordre, sans rien sauter.

---

## 1. Avant de commencer — les bases

### 1.1 Qu'est-ce que c'est ?

Sur le mur du labo, il y a une **tablette** (une grande dalle plate avec un écran). C'est elle qui fait tourner l'application HACCP. Vous n'avez **rien à installer**. L'écran s'allume tout seul quand on l'utilise.

À côté, il y a une **imprimante d'étiquettes** (une petite boîte blanche/noire). C'est elle qui imprime les étiquettes collées sur les barquettes, sous-vide, plats cuisinés, etc.

### 1.2 Le vocabulaire qu'on utilise dans ce guide

| Mot | Ce que ça veut dire |
|---|---|
| **Tapoter** ou **appuyer** | Toucher l'écran avec le bout du doigt, **une seule fois**, comme on appuie sur une sonnette. Pas besoin de presser fort. |
| **Faire défiler** ou **scroller** | Poser le doigt sur l'écran et le faire glisser vers le haut ou vers le bas (comme tourner une page). |
| **Tuile** | Un gros carré coloré avec une icône et un titre. C'est un raccourci : on tape dessus pour y aller. |
| **Champ** | Une case blanche où on doit écrire quelque chose (un nombre, du texte). |
| **Bouton** | Une zone rectangulaire ou ronde sur laquelle on tape pour faire une action (ex : « Valider »). |
| **Étape** | Une page de l'application. On en fait plusieurs à la suite. Une **barre de petits ronds** en haut montre à quelle étape on en est. |
| **HACCP** | Les règles d'hygiène alimentaire qu'on est obligés de suivre par la loi. |
| **DLC** | « Date Limite de Consommation ». Après cette date, on ne vend pas. |
| **Lot** | Un numéro unique attribué à une production. Ça sert à retrouver un produit en cas de problème. |

### 1.3 Trois règles d'or

1. **Pas de clic droit, pas de double-clic.** On tape **une seule fois**, doucement. Si rien ne se passe au bout de 2 secondes, on retape une fois.
2. **Pas peur de se tromper.** Tant qu'on n'a pas tapé sur **« Valider »** ou **« Enregistrer »**, **rien n'est sauvegardé**. On peut reculer et recommencer.
3. **Toujours sélectionner son prénom au début.** L'application a besoin de savoir qui fait l'action, c'est obligatoire par la loi.

### 1.4 Comment revenir en arrière ?

En haut **à gauche** de chaque page, il y a un bouton **« ← Hub »**, **« ← Retour »** ou **« ← Tâches »**. Il sert à revenir à l'écran précédent. **Tapez dessus**, jamais sur le bouton « Précédent » du navigateur (celui-là peut faire perdre ce que vous avez tapé).

### 1.5 Si vous ne touchez à rien pendant 5 minutes

L'application revient toute seule à l'écran d'accueil. Ce n'est **pas** une panne. Reprenez à zéro.

---

## 2. L'écran d'accueil (« Hub »)

C'est l'écran de départ. Il s'appelle le **Hub**. Vous y reviendrez toujours entre deux tâches.

En haut, vous voyez :
- **« Au Comptoir des Lilas »** : le nom de la boutique.
- **L'heure** : elle est toujours à jour.
- **Une cloche 🔔** (si elle s'affiche) : il y a des tâches HACCP à faire aujourd'hui. Tapotez-la pour les voir.
- **« ⚙ Admin »** : la configuration. **Ne touchez à rien là-dedans** si vous n'êtes pas le responsable.

En dessous, 8 grandes **tuiles** (gros carrés). Chacune ouvre un module :

| Tuile | À quoi ça sert |
|---|---|
| ✅ **TÂCHES HACCP** | Nettoyage, étalonnage des thermomètres, températures, nuisibles, formation |
| 🏭 **PRODUCTION** | Étiquetage de fabrication, cuisson, refroidissement |
| 📦 **RÉCEPTION** | Quand un camion livre de la marchandise |
| ✂️ **OUVERTURE** | Quand vous ouvrez un sous-vide |
| 📅 **CALENDRIER DLC** | Voir toutes les dates limites par jour, semaine, mois |
| 📋 **STOCK** | Tout ce qui est en stock, classé par ordre d'utilisation (FIFO) |
| 🗂️ **HISTORIQUE** | Voir tout ce qui a été enregistré dans le passé |
| 📚 **CATALOGUE** | La liste des produits et matières premières |

> **Si une bande orange apparaît** en haut (« Connexion au serveur perdue »), c'est que la tablette ne parle plus avec le Raspberry Pi. **Prévenez le responsable**. Vous pouvez quand même finir ce que vous étiez en train de faire ; ce sera envoyé plus tard.

---

## 3. Module RÉCEPTION — quand un camion livre

**Quand l'utiliser :** chaque fois qu'un fournisseur livre de la marchandise.

### 3.1 Ouvrir le module
1. Sur le Hub, tapotez la tuile **📦 RÉCEPTION**.
2. Vous arrivez sur la première étape. En haut, **5 petits ronds** : c'est votre progression.

### 3.2 Étape 1 — Qui réceptionne ?
- L'écran demande **« Qui réceptionne ? »**.
- Une grille de prénoms s'affiche. **Tapotez votre prénom**.
- Si votre prénom n'est pas là : prévenez le responsable, il doit vous ajouter dans Admin.

### 3.3 Étape 2 — Le camion
Remplissez les champs **de haut en bas** :
1. **Date de réception** : tapotez le champ, un petit calendrier s'ouvre, choisissez le jour (généralement aujourd'hui, déjà rempli).
2. **Heure de réception** : tapotez, choisissez l'heure.
3. **Température du camion (°C)** : tapotez la case, **un clavier numérique** s'affiche en bas. Tapez la température lue sur la sonde du camion (exemple : `2.5`). Pour le point décimal, utilisez la touche `.` du clavier.
4. **Propreté du camion** : deux boutons.
   - ✓ Satisfaisante (par défaut)
   - ✗ Non satisfaisante (tapotez **seulement** si le camion est sale)

5. Quand tout est rempli, descendez et tapotez le gros bouton **« Suivant »** en bas.

> 💡 Si vous avez tapé un nombre faux : tapotez la case, effacez avec la touche `⌫` (flèche-retour en haut à droite du clavier), retapez.

### 3.4 Étape 3 — Le fournisseur et les produits
1. Choisissez le fournisseur dans la liste déroulante (tapotez la flèche ▾).
2. **Numéro de bon de livraison** : recopiez le numéro écrit sur le papier (la facture/bon).
3. Ajoutez les produits livrés :
   - Tapotez **« + Ajouter un produit »**.
   - Cherchez le produit dans la liste (tapez les premières lettres pour filtrer).
   - **Quantité** : nombre de pièces ou poids selon le produit.
   - **N° de lot fournisseur** : recopiez **exactement** ce qui est écrit sur l'étiquette du produit.
   - **DLC fournisseur** : recopiez la date imprimée sur l'emballage.
   - **Température produit** : prenez la température à cœur avec votre thermomètre sonde et tapez la valeur.
4. Recommencez pour chaque produit.

### 3.5 Étape 4 — Non-conformités (si tout va bien, ignorez)
Si un produit a un problème (DLC trop courte, emballage abîmé, mauvaise température…) :
- Tapotez **« Déclarer une non-conformité »**.
- Choisissez le type de problème.
- Tapez une description courte.
- Choisissez l'action (refus total, refus partiel, acceptation conditionnelle).

### 3.6 Étape 5 — Valider
- Relisez le récapitulatif.
- Tapotez le gros bouton vert **« Enregistrer la réception »**.
- L'imprimante imprime les **étiquettes** pour chaque produit reçu. Collez-les sur les emballages, à l'endroit prévu, sans masquer les informations du fournisseur.

> ✅ C'est terminé. Vous revenez au Hub.

---

## 4. Module PRODUCTION — fabriquer, cuire, refroidir

Sur le Hub, tapotez 🏭 **PRODUCTION**. Trois tuiles apparaissent.

### 4.1 FABRICATION (étiquettes) — 🔪

**Quand l'utiliser :** quand vous découpez, hachez, préparez un produit à partir d'une matière première.

1. Tapotez **FABRICATION**.
2. **Étape 1 — Qui fabrique ?** : tapotez votre prénom.
3. **Étape 2 — Quel produit ?**
   - Une grille de **recettes** ou produits s'affiche.
   - Utilisez la **barre de recherche** en haut pour taper les premières lettres (ex : `mer` pour merguez).
   - Tapotez la tuile du produit.
4. **Étape 3 — Détails**
   - **Quantité** : nombre de pièces ou poids.
   - **Matière(s) première(s) utilisée(s)** : sélectionnez le lot d'origine (très important pour la traçabilité — c'est ce qui permet de remonter en cas de problème).
   - **Date de fabrication** : aujourd'hui par défaut.
   - **DLC** : calculée automatiquement selon les règles. **N'y touchez pas** sauf instruction du responsable.
5. Tapotez **« Imprimer l'étiquette »**.
6. L'imprimante sort l'étiquette. Collez-la sur le produit fini.

### 4.2 CUISSON — 🔥

**Quand l'utiliser :** chaque fois que vous mettez quelque chose à la rôtissoire ou au four.

1. Tapotez **CUISSON**.
2. **Étape 1** : tapotez votre prénom (« Qui cuisine ? »).
3. **Étape 2 — Quel produit ?** : sélectionnez ce que vous mettez à cuire.
4. **Étape 3 — Contrôles** :
   - **Heure de début** : enregistrée automatiquement quand vous lancez.
   - À la fin de la cuisson, **prenez la température à cœur** avec le thermomètre.
   - Tapez la température : elle doit être **≥ 75 °C** (le système vous prévient si c'est trop bas).
   - Si la cuisson est OK, tapotez **« Valider la cuisson »**.
   - L'étiquette du produit cuit s'imprime.

> ⚠️ Si la température est < 75 °C : **remettez à cuire**. Ne validez pas. C'est une règle de sécurité alimentaire.

### 4.3 REFROIDISSEMENT — ❄️

**Quand l'utiliser :** **immédiatement après cuisson**, pour passer le produit en cellule de refroidissement rapide.

**Règle HACCP :** il faut passer de cuisson à **≤ 10 °C en moins de 2 heures**.

1. Tapotez **REFROIDISSEMENT**.
2. **Étape 1** : votre prénom.
3. **Étape 2 — Quel produit ?** : seuls les produits récemment cuits apparaissent.
4. **Étape 3** :
   - Le compte à rebours de 2 h démarre.
   - À la fin (ou avant si vous atteignez 10 °C), tapez la température à cœur.
   - Tapotez **« Valider »**.
   - L'étiquette finale s'imprime avec la DLC réelle.

---

## 5. Module OUVERTURE — ouvrir un sous-vide

**Quand l'utiliser :** chaque fois que vous **ouvrez** un sachet sous-vide pour entamer le produit.

1. Hub → ✂️ **OUVERTURE**.
2. **Étape 1** : votre prénom.
3. **Étape 2** : sélectionnez le sous-vide que vous ouvrez (cherchez par nom ou par n° de lot).
4. **Étape 3** : confirmez. Une nouvelle DLC est calculée automatiquement (généralement **J+3** après ouverture).
5. L'imprimante sort une **nouvelle étiquette d'ouverture**. Collez-la **par-dessus** l'ancienne.

---

## 6. Module CALENDRIER DLC

**À quoi ça sert :** voir tout ce qui va périmer et **quand**, pour ne rien jeter par oubli.

1. Hub → 📅 **CALENDRIER DLC**.
2. En haut, choisissez la vue : **Semaine**, **Mois**, ou **Annuel**.
3. Utilisez les flèches **‹** et **›** pour avancer/reculer dans le temps.
4. Le bouton **« Aujourd'hui »** vous ramène à la date du jour.

### Les codes couleurs
- 🟢 **Vert** : produit OK, DLC lointaine.
- 🟠 **Orange** : DLC dans **≤ 3 jours**. À utiliser en priorité.
- 🔴 **Rouge** : DLC dépassée. **À traiter** (jeter ou transformer si la procédure le permet).

### Filtrer
- **Recherche** : tapez un nom de produit ou un n° de lot.
- **Source** : filtrer par réception / fabrication / cuisson / refroidissement.
- **Statut** : actifs / à traiter / traités.

### Réimprimer une étiquette
Tapotez sur une ligne du calendrier → un encadré s'ouvre → bouton **« Réimprimer l'étiquette »**.

---

## 7. Module STOCK

**À quoi ça sert :** voir **tout ce qui est en stock**, classé par **FIFO** (le plus ancien en premier — c'est lui qu'il faut utiliser d'abord).

1. Hub → 📋 **STOCK**.
2. En haut, le **bandeau de statistiques** :
   - **Total** : tout ce qui est en stock.
   - **📦 Réceptions / 🔪 Fabrications / 🔥 Cuissons / ❄️ Refroidis** : combien de chaque type.
   - **⏰ ≤ 3 jours** : produits dont la DLC arrive dans 3 jours ou moins.
3. La liste affiche les produits du plus ancien au plus récent.
4. Tapotez sur une ligne pour voir le détail (lot, fournisseur, date, traçabilité complète).

### Mode « Gérer »
Tapotez **« ✏️ Gérer »** en haut à droite pour pouvoir :
- Marquer un produit comme **utilisé** ou **jeté**.
- Réimprimer une étiquette.

---

## 8. Module HISTORIQUE

**À quoi ça sert :** retrouver tout ce qui a été enregistré (utile en cas de contrôle ou pour vérifier).

1. Hub → 🗂️ **HISTORIQUE**.
2. Des onglets en haut : **Réceptions**, **Fabrications**, **Cuissons**, **Refroidissements**, **Ouvertures**, **Nettoyages**, etc.
3. Tapotez un onglet, puis une ligne pour voir le détail complet.
4. Vous pouvez filtrer par date avec les sélecteurs en haut.

---

## 9. Module CATALOGUE

**À quoi ça sert :** voir la fiche d'un produit ou d'une matière première (DLC théorique, conditionnement, conservation, etc.).

1. Hub → 📚 **CATALOGUE**.
2. **Tapez les premières lettres** d'un nom de produit dans la barre de recherche.
3. Tapotez le produit pour voir sa fiche.

> 🔒 **C'est en lecture seule** pour les opérateurs. Pour modifier, il faut passer par Admin.

---

## 10. Module TÂCHES HACCP

Hub → ✅ **TÂCHES HACCP**. Cinq sous-tuiles s'affichent.

### 10.1 🧹 NETTOYAGE

**À quoi ça sert :** valider chaque jour les nettoyages prévus par le plan.

1. Tapotez **NETTOYAGE**.
2. En haut : la date du jour, votre prénom à choisir dans le menu **« 👤 Opérateur »**.
3. Un grand tableau affiche les tâches par **secteur** (cuisine, frigos, sols…) et par **jour de la semaine**.
4. Pour chaque tâche faite, tapotez la **case** du jour correspondant : elle devient verte ✓.
5. Quand vous avez tout coché, tapotez **« ✅ VALIDER LE NETTOYAGE »** en haut à droite.

**Ajouter ou modifier une tâche** (responsable uniquement) :
- Bouton **« ⚙ Tâches »** → modale avec liste + formulaire d'ajout.

### 10.2 🌡️ ÉTALONNAGE

**À quoi ça sert :** vérifier que les thermomètres donnent la bonne température (obligatoire pour le HACCP).

1. Tapotez **ÉTALONNAGE**.
2. Suivez la procédure à l'écran : généralement, on plonge le thermomètre dans un mélange d'eau et de glace (= 0 °C) et on compare la valeur affichée.
3. Tapez la valeur lue. Le système indique si c'est conforme.
4. Validez.

### 10.3 🌡️ TEMPÉRATURES

**À quoi ça sert :** voir en direct la température de chaque enceinte (chambres froides, vitrine, laboratoire).

1. Tapotez **TEMPÉRATURES**.
2. Vous voyez chaque sonde avec sa température actuelle.
3. **Vert** = OK, **Orange** = limite, **Rouge** = dépassement.
4. Tapotez une enceinte pour voir le **graphique** des dernières heures.

> Pas d'action à faire ici : c'est juste pour surveiller. Les alertes par email/SMS sont envoyées automatiquement si une sonde dépasse le seuil.

### 10.4 🐛 NUISIBLES

**À quoi ça sert :** enregistrer les contrôles des pièges (rongeurs, insectes, oiseaux), semaine par semaine.

1. Tapotez **NUISIBLES**.
2. En haut : onglets **🐀 Rongeurs / 🪰 Insectes Volants / 🪳 Insectes Rampants / 🐦 Oiseaux**.
3. Un tableau de 52 semaines × les pièges (P1, P2, …).
4. Tapotez une case (semaine × piège) pour enregistrer l'état :
   - ✓ RAS (rien à signaler)
   - ⚠ Activité détectée
   - ✗ Piège manquant / cassé
5. Choisissez l'année en haut à droite si besoin.

### 10.5 🎓 E-LEARNING

**À quoi ça sert :** consulter les fiches de formation (hygiène, découpe).

1. Tapotez **E-LEARNING**.
2. Choisissez **🧼 HYGIÈNE** ou **🔪 DÉCOUPE**.
3. Faites défiler les pages (glisser le doigt de bas en haut).

> C'est juste de la lecture. Aucune action à valider.

---

## 11. Cas particuliers — incidents

Si un produit pose problème (corps étranger, suspicion de contamination, retrait fournisseur…), il faut ouvrir une **fiche incident PCR01**.

1. Accédez à la page incidents (via Admin ou le lien direct **/incidents.html**).
2. Choisissez **« Nouvelle fiche »**.
3. Remplissez : produit, lot, nature du problème, mesure prise.
4. Validez.

> Le responsable est notifié.

---

## 12. Module ADMIN (responsable uniquement)

**⚠️ Ne touchez à cette section que si vous êtes le responsable.**

Hub → **⚙ Admin** en haut à droite.

Sections disponibles :
- **👥 Personnel** : ajouter / retirer des prénoms qui apparaissent dans les sélecteurs.
- **🌡️ Thermomètres de référence** : enregistrer les thermomètres sondes.
- **🌡️ Enceintes / Sondes** : configurer chaque chambre froide (seuils min/max).
- **Catalogue produits** : modifier les fiches produits.
- **Recettes** : créer/modifier les recettes de fabrication.
- **Plan de nettoyage** : éditer la liste des tâches récurrentes.

Chaque section a :
- Une **liste** des éléments existants.
- Un **formulaire** en bas pour ajouter.
- Des boutons **✏️ Modifier** et **🗑️ Supprimer** sur chaque ligne.

---

## 13. Imprimante d'étiquettes — au quotidien

L'imprimante **Brother QL-820NWB** est branchée en USB sur le Raspberry Pi.

### Ça n'imprime pas ?
1. Vérifiez que le **voyant** de l'imprimante est **vert**.
   - **Rouge** ou **orange clignotant** = plus de rouleau ou bourrage.
2. Ouvrez le capot, vérifiez que le rouleau d'étiquettes est bien en place et qu'il n'y a pas de bout d'étiquette coincé.
3. Fermez le capot, refaites un test en réimprimant depuis le **Calendrier DLC** ou le **Stock**.
4. Si toujours rien : prévenez le responsable.

### Changer le rouleau
1. Ouvrez le capot (bouton sur le côté).
2. Retirez l'ancien support.
3. Placez le nouveau rouleau, la sortie de l'étiquette **vers l'avant**.
4. Fermez le capot fermement (clic).

---

## 14. Que faire si… (FAQ)

| Problème | Que faire |
|---|---|
| L'écran reste noir | Tapotez-le une fois, il se réveille. Sinon, prévenez. |
| Je me suis trompé dans un champ | Tapotez la case, effacez avec ⌫, retapez. |
| J'ai validé trop vite | Allez dans **Historique**, ouvrez l'enregistrement, modifiez si possible. Sinon, ouvrez une **fiche incident**. |
| Plus de prénom dans la liste | Le responsable doit vous ajouter dans **Admin → Personnel**. |
| L'application ne répond plus | Attendez 10 secondes. Si rien, revenez au Hub avec **← Hub**. Si toujours rien : prévenez. |
| Bandeau orange « Connexion perdue » | Le serveur ne répond plus. Continuez votre travail si possible, prévenez le responsable. |
| Erreur « Température hors plage » | C'est normal : le système vous protège. Reprenez la mesure, vérifiez le thermomètre. Si l'écart est réel, **n'acceptez pas le produit**. |

---

## 15. Mémo des bons réflexes au quotidien

✔️ Toujours **sélectionner son prénom** au début de chaque action.
✔️ Toujours **prendre la température à cœur** (au centre du produit, pas en surface).
✔️ **Recopier exactement** les n° de lot et DLC fournisseur.
✔️ **Coller les étiquettes** dès leur sortie, **sur le bon produit**.
✔️ Valider le **nettoyage** chaque jour.
✔️ En cas de doute : **demander au responsable**, ne pas valider à l'aveugle.

---

**Fin du tutoriel.** Prenez votre temps, c'est mieux que d'aller vite. L'application est faite pour aider, pas pour piéger : si elle vous bloque, c'est qu'elle protège la sécurité alimentaire.

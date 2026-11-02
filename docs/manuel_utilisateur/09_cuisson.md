# Module 9 — Cuisson & refroidissement

---

## 1. Objectif

Ce module tient le registre HACCP de chaque cuisson et de ce qu'elle devient : **refroidie** (≤ 10 °C à cœur en ≤ 2 h) ou **vendue chaude**. Une seule **fiche** regroupe produit, lot, cuisson et refroidissement.

L'écran est pensé pour la **saisie après coup** : on peut ouvrir une fiche dans la journée avec seulement le produit et le lot, puis la compléter le soir. Aucune heure n'est remplie à la place de l'opérateur.

---

## 2. Chemin d'accès

Hub principal → **Production** → tuile **🔥 CUISSON** (la tuile **❄️ REFROIDISSEMENT** ouvre le même écran).

URL directe : `/cuisson.html` (l'ancienne adresse `/refroidissement.html` y renvoie).

Un rappel **« Cuisson / refroidissement à compléter »** apparaît dans les tâches du jour du Hub tant qu'une fiche n'est pas terminée.

---

## 3. L'accueil

| Zone | Contenu |
|---|---|
| **+ Nouvelle cuisson** | Ouvre une fiche vide |
| **À compléter** | Fiches non terminées des 30 derniers jours, avec ce qui manque. Badge `⚠ pas d'aujourd'hui` pour une fiche d'un autre jour. Bouton **Compléter →** |
| **Terminées ces 7 derniers jours** | Repliée par défaut. Résumé cuisson / refroidissement (vert = conforme, rouge = non conforme). Bouton **🖨 Étiquette** |

États d'une fiche :

| État affiché | Ce qui manque |
|---|---|
| 🔥 Cuisson à saisir | Heure de fin + T° de la cuisson |
| ❓ Refroidi ou vendu chaud ? | Choisir la suite |
| ❄ Refroidissement à saisir | Heure de fin + T° du refroidissement |

Une fiche est **terminée** quand elle est refroidie, vendue chaude, ou que son produit est sorti du stock (ex. lot jeté depuis le calendrier DLC).

---

## 4. La fiche

### 4.1 Produit (nouvelle fiche)

| Champ | Notes |
|---|---|
| **Qui ?** ✱ | La personne qui saisit. Pour une fiche ouverte dans la journée, le cuisinier reste celui qui l'a ouverte |
| **Date de la cuisson** ✱ | Aujourd'hui par défaut, modifiable (rattrapage de la veille). Jamais dans le futur |
| **Quantité** | Facultative, en kg, g ou pièces |
| **Produit cuit** ✱ | Recherche parmi le stock disponible, les DLC les plus courtes en premier |
| **Lot utilisé** ✱ | Lot FIFO (DLC la plus courte) présélectionné, marqué ⭐. Lien **📋 Voir les réceptions** vers les fiches de réception |
| **Lot entièrement utilisé** | Cochée par défaut : le lot cru sort du stock (statut « consommé »). **Décochez s'il en reste** : le lot reste disponible pour une autre cuisson |
| **Devient** ✱ | Uniquement pour une matière brute du catalogue achats : le produit du catalogue vente obtenu (ex. Tende de tranche → Rosbeef cuit). Le dernier choix fait pour cet article est présélectionné |

Sur une fiche existante, produit et lot sont rappelés en tête et ne se changent plus.

### 4.2 Cuisson

| Champ | Notes |
|---|---|
| **Cuit au** | Four · Rôtissoire · Marmite / plaque · Autre. Le dernier type utilisé sur la tablette est proposé |
| **Début / Fin** | Vides au départ. Boutons **A cuit : 30 min · 45 min · 1 h · 1 h 30 · 2 h · 3 h** : si le début est saisi, ils calculent la fin ; si seule la fin est saisie, ils calculent le début. La durée s'affiche (`→ a cuit 1 h 15`) |
| **Degré de cuisson** | Bœuf / agneau en pièce entière uniquement : Saignant 55 °C · À point 63 °C · Bien cuit 75 °C · Règle générale 75 °C |
| **T° à cœur en fin de cuisson** | Vide au départ : c'est une mesure. Bandeau vert ou rouge selon la cible |
| **Action corrective** ✱ si T° < cible | Proposée : *« Remise en cuisson jusqu'à X °C à cœur »*, modifiable |

Heure de fin et T° vont ensemble : on les saisit toutes les deux pour terminer la cuisson, ou on les laisse vides pour compléter plus tard.

Une fois enregistrée comme terminée, **la cuisson n'est plus modifiable** (registre HACCP).

### 4.3 Ensuite

Trois choix, disponibles une fois la cuisson terminée :

| Choix | Effet |
|---|---|
| **❄ Refroidi** | Ouvre la partie refroidissement |
| **🔥 Vendu chaud** | Termine la fiche ; le produit cuit sort du stock (statut « vendu ») |
| **Plus tard** | La fiche reste dans « À compléter » |

### 4.4 Refroidissement

| Champ | Notes |
|---|---|
| **Mise au froid** | Reprend automatiquement l'heure de fin de cuisson (`= fin de cuisson`), modifiable |
| **Fin** | Vide au départ. Boutons **A refroidi : 1 h · 1 h 30 · 2 h** |
| **T° à cœur après refroidissement** | Mesure, cible ≤ 10 °C |

Alertes affichées :
- `⚠ Avant la fin de la cuisson` — la mise au froid est antérieure à la sortie de cuisson (refusé à l'enregistrement).
- `⚠ X après la sortie de cuisson : à mettre au froid sans attendre` — plus de 30 min d'écart (accepté, mais visible).

Conformité :

| Situation | Résultat |
|---|---|
| ≤ 10 °C en ≤ 2 h | ✓ Conforme |
| Une seule des deux limites dépassée | ⚠ Non conforme — action corrective obligatoire |
| > 10 °C **et** > 2 h | ⛔ Produit à **jeter** — cocher la confirmation « produit jeté » pour enregistrer. Le produit sort du stock |

### 4.5 Enregistrer

- **Enregistrer** : enregistre ce qui est rempli, la fiche reste « À compléter » s'il manque quelque chose.
- **Enregistrer + étiquette** : idem, puis imprime l'étiquette du dernier maillon : `[REFROIDI]` si le refroidissement est saisi, sinon `[CUIT]`. Pas d'étiquette pour un produit jeté ou une cuisson non terminée.

L'enregistrement est **tout ou rien** : si le refroidissement est refusé, la cuisson saisie dans le même envoi ne l'est pas non plus (pas de doublon en renvoyant la fiche).

L'écran ne revient pas tout seul au Hub pendant qu'une fiche est ouverte (seulement après 5 min d'inactivité sur l'accueil).

---

## 5. Règles enregistrées par le serveur

### 5.1 Chronologie

Refusé :
- fin de cuisson avant ou égale au début ;
- fin de refroidissement avant ou égale à la mise au froid (plus de « passage minuit » implicite) ;
- mise au froid avant la fin de la cuisson ;
- toute heure ou date dans le futur (heure de Paris, 5 min de tolérance).

Le refroidissement prend la **date de la cuisson**.

### 5.2 DLC

- **Produit cuit** : date de cuisson + 3 jours, jamais au-delà de la DLC du lot d'origine.
- **Produits « suivi cuisson auto »** (lasagnes, gratins, parmentiers reçus prêts) : la DLC fournisseur, telle quelle.
- **Produit refroidi** : **la DLC du produit cuit** (le refroidissement ne la rallonge jamais).

### 5.3 Températures

- T° de sortie de cuisson : 0 à 120 °C ; cible selon le degré choisi (75 °C par défaut).
- Le refroidissement ne rejuge pas la cuisson : une cuisson à 55 °C « saignant » conforme n'est pas déclarée à jeter.

### 5.4 Stock

- Une fiche dont la cuisson n'est pas terminée n'apparaît ni en stock ni au calendrier DLC.
- Le produit cuit apparaît en stock (🔥) jusqu'à son refroidissement (❄️), sa vente chaude ou sa sortie.

---

## 6. Depuis « Production à cuire »

Le bouton de cuisson d'un lot (lasagnes, gratins…) ouvre une nouvelle fiche avec le produit, le produit fini et **le lot exact** présélectionnés.

---

## 7. Ticket thermique (62 mm)

| Zone | Contenu |
|---|---|
| **Tag** | `[CUIT]` ou `[REFROIDI]` |
| **Nom produit** | Majuscules |
| **Quantité** | Quantité de la cuisson |
| **DLC** | Rouge, `JJ/MM/AA`, encadrée |
| **Lot** | N° de lot d'origine |
| **Température** | `T° fin cuisson` ou `T° fin refroidissement` |
| **Ligne action** | `Cuit le …` / `Refroidi le … à HHhMM` |
| **Pied** | `Par : [opérateur]` |

---

## 8. Messages d'erreur

| Situation | Message |
|---|---|
| Personne non choisie | *« Indiquez qui saisit la fiche. »* |
| Produit / lot / « Devient » manquant | *« Choisissez le produit cuit. »* · *« Choisissez le lot utilisé. »* · *« Indiquez ce que devient le produit… »* |
| Fin ou T° saisie seule | *« Pour terminer la cuisson : début, fin ET T° à cœur… »* |
| Fin avant début | *« Cuisson : la fin est avant le début. »* |
| Heure future | *« … heure dans le futur. Saisissez l'heure réelle. »* |
| T° sous la cible sans action | *« Action corrective obligatoire (T° < X °C). »* |
| Refroidissement incomplet | *« Refroidissement : mise au froid, fin ET T° à cœur… »* |
| Jet non confirmé | *« Plus de 2 h et plus de 10 °C : cochez la confirmation « produit jeté ». »* |
| Bouton de durée sans heure | *« … saisissez d'abord l'heure de début ou de fin. »* |

---

[Passer au module suivant : Refroidissement](10_refroidissement.md)

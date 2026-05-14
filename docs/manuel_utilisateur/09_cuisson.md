# Module 9 — Cuisson HACCP (≥ 75°C)

---

## 1. Objectif

Ce module enregistre chaque opération de cuisson avec traçabilité complète : produit, lot source, opérateur, heures de début et de fin, et surtout la **température à la sortie** par rapport à la cible réglementaire HACCP de **75°C à cœur**. Si la température est atteinte, une DLC J+3 est calculée automatiquement et une étiquette thermique peut être imprimée. Après cuisson, le module propose directement de lancer le suivi de refroidissement.

---

## 2. Chemin d'accès

Hub principal → **Production** → tuile **🔥 CUISSON**.

URL directe : `/cuisson.html`

---

## 3. Structure générale : wizard 3 étapes

Wizard guidé avec barre de progression numérotée 1-2-3. Un bandeau `👤 [Opérateur] · 📦 [Produit]` reste visible dès que les deux premiers choix sont faits.

| Étape | Titre |
|---|---|
| 1 | Qui cuisine ? |
| 2 | Quel produit ? |
| 3 | Paramètres de cuisson |

Navigation arrière disponible à toutes les étapes. Inactivité 5 minutes → redirection vers `/hub.html`.

---

## 4. Étape 1 — Sélection de l'opérateur

Grille de tuiles avec l'initiale et le prénom de chaque membre du personnel actif, triés alphabétiquement. Un clic sur une tuile la sélectionne (mise en évidence) et fait avancer automatiquement vers l'étape 2 après 150 ms.

---

## 5. Étape 2 — Sélection du produit

### 5.1 Filtres

- **Filtres espèces** : boutons `Toutes` + un bouton par espèce présente en stock (🐂 Bœuf, 🐄 Veau, 🐑 Agneau, 🐖 Porc, 🦌 Gibier, 🐔 Volaille, 🐎 Cheval, 🦬 Exotique). Générés dynamiquement selon le stock disponible.
- **Champ de recherche** : filtre les tuiles par nom (insensible à la casse).

### 5.2 Grille de produits

Seuls les produits **en stock** (réceptions non expirées, non traitées DLC) sont affichés. Ordre de tri :
1. En stock en premier
2. Par DLC croissante (FIFO)
3. Alphabétique

Chaque tuile affiche :
- Badge `⭐ EN STOCK`
- Icône espèce
- Nom du produit
- DLC du lot FIFO (ex. : `DLC 17/05/2026`)
- N° de lot FIFO

**Sources** : le module accepte deux origines de stock — **réceptions de matières premières** et **fabrications maison** (produits finis crus). Un lot de fabrication est identifié par le badge `🔪 Fabrication` dans le sélecteur de lot.

### 5.3 Sélecteur de lot (visible si ≥ 2 lots disponibles)

Après sélection d'un produit ayant plusieurs lots, un sélecteur apparaît :
- Le **lot FIFO** (DLC la plus courte) est pré-sélectionné et marqué `⭐ FIFO`
- Format de chaque option : `⭐ FIFO — Lot XXX · DLC JJ/MM/AAAA · reçu JJ/MM/AAAA · Fournisseur`
- Les lots issus de fabrication indiquent `· fabriqué` et `· Fabrication maison`

Sous le sélecteur :
- **`📋 Historique de réception`** : ouvre une modale avec la liste de tous les lots, DLC, poids, fournisseur et un lien vers la fiche de réception
- **`Suivant →`** : confirme le lot choisi et passe à l'étape 3

Si le produit n'a qu'un seul lot, l'étape 3 s'ouvre automatiquement.

---

## 6. Étape 3 — Paramètres de cuisson

### 6.1 Formulaire

| Champ | Obligatoire | Notes |
|---|---|---|
| **Date** | Oui ✱ | Pré-remplie avec la date du jour |
| **Quantité** | Oui ✱ | Décimale (> 0) |
| **Unité** | Oui | Menu : `kg` (défaut) · `g` · `pièces` |
| **Heure début cuisson** | Oui ✱ | Pré-remplie avec l'heure courante |
| **Heure fin cuisson** | Oui ✱ | Saisie directe ou via raccourcis (voir 6.2) |
| **Température produit — sortie rôtissoire** | Oui ✱ | 0–120°C, décimale. Bouton rapide `75°C`. |
| **Action corrective** | Oui ✱ si T° < 75°C | Textarea, pré-remplie automatiquement si NC (voir 6.3) |

### 6.2 Raccourcis heure de fin

Deux méthodes de saisie rapide pour l'heure de fin :

**Boutons durée prédéfinis** (calculés depuis l'heure de début) :
`+1h` · `+1h30` · `+2h` · `+2h30` · `+3h`

**Saisie manuelle durée** : champs `h` + `min` + bouton `→` pour calculer et appliquer l'heure de fin.

> Si l'heure de début n'est pas renseignée au moment du clic, un message d'erreur s'affiche.

### 6.3 Badge de conformité et action corrective

Mis à jour en temps réel à chaque frappe dans le champ Température :

| Température | Badge affiché | Action corrective |
|---|---|---|
| Non saisie | *(masqué)* | *(masquée)* |
| ≥ 75°C | `✓ Conforme — X,X °C ≥ 75 °C` (vert) | Champ masqué et vidé |
| < 75°C | `⚠ Non conforme — X,X °C < 75 °C — action corrective requise` (rouge) | Champ visible, pré-rempli automatiquement |

**Texte pré-rempli automatiquement si T° < 75°C :**
> *"Remettre le produit en cuisson (four, rôtissoire, marmite) et prolonger le temps de cuisson jusqu'à l'atteinte de la température de 75 °C à cœur"*

Ce texte est **modifiable**. Si l'opérateur efface le texte et que la T° repasse au-dessus de 75°C, le champ action corrective est automatiquement masqué et vidé.

### 6.4 Historique récent

Sous le formulaire, un tableau affiche les **20 dernières cuissons de type rôtissoire**, avec : date, plage horaire, produit, quantité, opérateur, température (vert si ≥ 75°C, rouge sinon).

---

## 7. Après l'enregistrement — Modal de choix

Après une sauvegarde réussie, une modale **"Cuisson enregistrée"** (ou **"⚠ Cuisson enregistrée — non conforme"** si T° < 75°C) affiche 4 boutons :

| Bouton | Action |
|---|---|
| **🖨 Imprimer étiquette** | Génère et imprime l'étiquette thermique Brother 62 mm (voir section 9) |
| **🍗 Nouvelle cuisson** | Réinitialise entièrement le wizard (retour à l'étape 1) |
| **🏠 Retour au hub** | Redirige vers `/taches-hub.html` |
| **❄ Refroidissement du produit** | Sauvegarde les données en `sessionStorage` et redirige vers `/refroidissement.html` avec pré-remplissage |

---

## 8. Règles de conformité invisibles

### 8.1 Cible réglementaire : 75°C

La constante `TEMPERATURE_CIBLE = 75.0` est définie dans le backend. Une T° de sortie **strictement inférieure** à 75°C déclenche :
1. Le marquage `conforme = 0` en base de données
2. L'obligation d'une action corrective (rejet HTTP 422 si absente)

### 8.2 DLC automatique J+3, capée par la source

La DLC est calculée **exclusivement côté serveur** :
```
dlc_calculee = date_cuisson + DLC_JOURS_TRANSFORMATION (= 3 jours)
```

**Règle de plafonnement :** si la DLC du lot source (réception ou fabrication) est antérieure à `dlc_calculee`, alors :
```
dlc_finale = dlc_source  (et non dlc_calculee)
```

Dans ce cas, `dlc_ajustee = True` est retourné et une **alerte popup** s'affiche côté frontend :  
*"⚠ DLC ajustée — Le module Cuisson a ajusté la DLC calculée à la DLC d'origine du produit : JJ/MM/AAAA"*

### 8.3 Unicité de la source amont

Une cuisson ne peut être liée **qu'à une seule source** : soit un lot de réception (`reception_ligne_id`), soit un lot de fabrication (`fabrication_id`), jamais les deux simultanément. Le backend rejette une telle requête avec HTTP 422.

### 8.4 FIFO dans la sélection de lots

Lorsque le produit a plusieurs lots, le **lot FIFO** est identifié par le tri :
1. DLC ascendante (lot expirant le plus tôt en premier)
2. Date de réception/fabrication ascendante (à DLC égale, le plus ancien)

Le lot FIFO est pré-sélectionné automatiquement. L'opérateur peut le changer manuellement via le sélecteur.

### 8.5 Pré-remplissage depuis d'autres modules

Si la clé `cuisson_prefill` est présente en `sessionStorage` à l'ouverture de la page, le wizard pré-remplit automatiquement l'opérateur, le produit, la quantité et l'unité. Cette clé est supprimée immédiatement après lecture (usage unique).

### 8.6 Lien vers le refroidissement

Le bouton **"❄ Refroidissement du produit"** injecte les données suivantes dans `sessionStorage` (`refroidissement_prefill`) pour la page de refroidissement :
- `operateur_id`, `operateur_prenom`
- `produit_id`, `produit_nom`
- `cuisson_id` (pour lier les deux opérations)
- `temperature_sortie` (T° de fin de cuisson → T° initiale du refroidissement)
- `quantite`, `unite`

---

## 9. Ticket thermique imprimé (format 62 mm)

Déclenché par le bouton "🖨 Imprimer étiquette" via `POST /api/etiquettes/transformes` + `window.print()`.

| Zone | Contenu |
|---|---|
| **Tag** | `[CUIT]` encadré |
| **Nom produit** | Majuscules |
| **Quantité** | `Quantité : X kg` |
| **DLC** | Date en rouge format `JJ/MM/AA` — encadrée |
| **Lot** | `Lot : [numéro lot origine]` — pointillés |
| **Température** | `T° fin cuisson : X,X °C` |
| **Ligne action** | `Cuit le JJ/MM/AA à HHhMM` |
| **Pied** | `Par : [Prénom opérateur]` |

---

## 10. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Soumission sans opérateur | Retour étape 1 + erreur : *"Veuillez sélectionner un opérateur."* |
| Soumission sans produit | Retour étape 2 + erreur : *"Veuillez sélectionner un produit."* |
| Quantité ≤ 0 ou vide | Erreur : *"Quantité requise (> 0)."* |
| Heures manquantes | Erreur : *"Heures de début et fin requises."* |
| Température vide | Erreur : *"Température de sortie requise."* |
| T° < 75°C sans action corrective | Erreur : *"Action corrective obligatoire si T° < 75 °C."* |
| T° < 75°C + action vide (backend) | HTTP 422 : *"Action corrective obligatoire si température < 75 °C"* |
| Deux sources liées (backend) | HTTP 422 : *"Une cuisson ne peut pas être liée simultanément à une réception et à une fabrication."* |
| DLC ajustée à la DLC source | Popup alert : *"⚠ DLC ajustée — [date origine]"* |
| Heure de fin calculée sans heure de début | Erreur : *"Renseignez d'abord l'heure de début."* |
| Durée manuelle (champ h+min) sans heure de début | Erreur : *"Renseignez d'abord l'heure de début."* |
| Erreur API lors de l'impression étiquette | Toast : *"Erreur impression : [détail]"* |
| Erreur API sauvegarde | Erreur rouge sous le formulaire, bouton réactivé |
| Aucun produit en stock | Grille vide : *"Aucun produit trouvé."* |
| Aucun opérateur actif | Grille vide : *"Aucun opérateur actif."* |

---

[Passer au module suivant : Refroidissement rapide (≤ 10°C en ≤ 2h)](10_refroidissement.md)

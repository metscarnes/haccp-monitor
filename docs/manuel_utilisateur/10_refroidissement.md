# Module 10 — Refroidissement Rapide (≤ 10°C en ≤ 2h)

---

## 1. Objectif

Ce module enregistre le contrôle de refroidissement post-cuisson selon la règle HACCP : le produit cuit doit passer de sa température de sortie (minimum 75°C) à une température à cœur **≤ 10°C en 2 heures maximum**. Si le couple temps/température n'est pas respecté, le module guide obligatoirement vers la décision de jet du produit avec traçabilité automatique dans le calendrier DLC.

---

## 2. Chemin d'accès

Hub principal → **Production** → tuile **❄️ REFROIDISSEMENT**.

URL directe : `/refroidissement.html`

---

## 3. Structure générale : wizard 3 étapes

Identique à la structure du module Cuisson (même architecture). Bandeau `👤 [Opérateur] · 📦 [Produit]` visible dès les deux premiers choix faits.

| Étape | Titre |
|---|---|
| 1 | Qui refroidit ? |
| 2 | Quel produit ? |
| 3 | Données du refroidissement |

Inactivité 5 minutes → redirection vers `/hub.html`.

---

## 4. Étape 1 — Sélection de l'opérateur

Identique au module Cuisson : grille de tuiles avec initiale et prénom, triés alphabétiquement. Un clic sélectionne et avance à l'étape 2 après 150 ms.

---

## 5. Étape 2 — Sélection du produit

> *"Uniquement les produits passés en cuisson."*

La liste provient de `GET /api/refroidissement/produits` qui retourne **uniquement les cuissons disponibles à refroidir** : cuissons non encore refroidies, non jetées, DLC non dépassée.

Chaque tuile affiche :
- Icône 🥩
- Nom du produit
- Date de cuisson (ex. : `Cuisson du 14/05/2026`)
- N° de lot

Si la liste est vide : *"Aucun produit cuit. Enregistrez d'abord une cuisson."*

Un clic sur une tuile avance automatiquement à l'étape 3 après 150 ms.

---

## 6. Étape 3 — Données du refroidissement

### 6.1 Formulaire

| Champ | Obligatoire | Notes |
|---|---|---|
| **Date** | Oui ✱ | Pré-remplie avec la date du jour |
| **Heure mise en refroidissement** | Oui ✱ | Pré-remplie avec l'heure courante à l'arrivée à l'étape 3 |
| **Heure fin refroidissement** | Oui ✱ | Pré-remplie automatiquement à `début + 2h` (maximum réglementaire). Boutons rapides disponibles. |
| **T° à cœur avant refroidissement** | Oui ✱ | Pré-remplie à `75` (ou depuis la cuisson liée si navigation directe). Cible minimum : ≥ 75°C. |
| **T° à cœur après refroidissement** | Oui ✱ | Décimale. Cible réglementaire : ≤ 10°C. |

### 6.2 Raccourcis heure de fin

Boutons de durée prédéfinis (calculés depuis l'heure de début) :
- `+1h`
- `+1h30`
- **`+2h (max)`** — mis en évidence, c'est la durée maximale réglementaire, pré-sélectionné par défaut

> Si l'heure de début n'est pas renseignée au clic, un message d'erreur s'affiche.

---

## 7. Bandeaux de conformité (temps réel)

Mis à jour à chaque frappe dans les champs Température initiale, Température finale et Heures.

La conformité globale combine **trois vérifications indépendantes** :

| Vérification | Cible | Libellé si KO |
|---|---|---|
| Cuisson suffisante | T°initiale ≥ 75°C | `cuisson insuffisante X,X °C < 75 °C` |
| T° finale atteinte | T°finale ≤ 10°C | `T° finale X,X °C > 10 °C` |
| Durée respectée | Durée ≤ 120 min | `durée Xh XX > 2 h` |

### Bandeau vert — Conforme

`✓ Conforme — cuisson X,X °C · refroidissement X,X °C en Xh`

Affiché uniquement si les **trois** conditions sont vérifiées.

### Bandeau rouge — Non conforme

`⚠ Non conforme — [raison 1] · [raison 2] …— action corrective requise`

Affiché dès qu'une condition n'est pas respectée.

### Bandeau spécifique "CUISSON INSUFFISANTE" — T°initiale < 75°C

```
⚠ CUISSON INSUFFISANTE — T° à cœur < 75 °C à la sortie cuisson.
Pourquoi : En dessous de 75 °C à cœur, les bactéries pathogènes ne sont pas éliminées.
Action corrective : Remettre le produit en cuisson...
```

Ce bandeau inclut un bouton **`🔥 Remettre en cuisson`** qui injecte les données du refroidissement en cours dans `sessionStorage` (`cuisson_prefill`) et redirige vers `/cuisson.html` avec opérateur et produit pré-sélectionnés.

### Bandeau "JETER LES PRODUITS"

`⛔ JETER LES PRODUITS — couple temps/température de refroidissement non respecté (durée > 2 h ET T° finale > 10 °C).`

Ce bandeau s'affiche **uniquement si les deux conditions refroidissement sont simultanément KO** : durée > 2h ET T° finale > 10°C.

---

## 8. Section "Action corrective" — Procédure de jet

Visible dès qu'un cas non conforme est détecté.

### Étape 1 — Bouton de confirmation

Bouton rouge foncé : **`⛔ Confirmer : Jeter le produit`**

Note sous le bouton : *"Ce produit sera retiré du stock et enregistré comme jeté dans le calendrier."*

### Étape 2 — Après confirmation (irréversible sauf annulation explicite)

- Bandeau vert foncé : `✓ Produit marqué comme JETÉ — retiré du stock`
- Champ **"Note optionnelle"** : cause, quantité, N° lot…
- Bouton **`✕ Annuler`** : remet le formulaire à l'état "en attente de confirmation" (le jet n'est pas encore enregistré tant que la fiche n'est pas soumise)

> **Important** : le jet n'est effectif en base de données qu'à la soumission du formulaire, pas au clic sur "Confirmer". Annuler avant de soumettre reste possible.

### Blocage de soumission sans confirmation

Si le refroidissement est non conforme et que l'opérateur n'a pas cliqué sur "Confirmer : Jeter le produit", la soumission est bloquée avec le message :  
*"Confirmez l'action 'Jeter le produit' avant d'enregistrer ([raisons])."*

---

## 9. Historique récent

20 derniers refroidissements avec : date, plage horaire, durée, produit, N° lot, opérateur, T° finale (vert si conforme, rouge sinon). Préfixe `⛔ JETER` pour les produits jetés.

---

## 10. Après l'enregistrement — Modal de choix

| Titre modal | Condition |
|---|---|
| `✓ Refroidissement enregistré` | Conforme |
| `⚠ Refroidissement enregistré — non conforme` | NC sans jet |
| `⛔ Refroidissement enregistré — produits à jeter` | Jet confirmé |

Boutons disponibles :

| Bouton | Condition | Action |
|---|---|---|
| **🖨 Imprimer étiquette** | **Masqué si produit jeté** | Génère étiquette thermique 62 mm avec tag `[REFROIDI]` |
| **❄ Nouveau refroidissement** | Toujours visible | Réinitialise le wizard |
| **🏠 Retour au hub** | Toujours visible | Redirige vers `/taches-hub.html` |

---

## 11. Règles de conformité invisibles

### 11.1 Règle de jet — Conjonction obligatoire

La règle de jet **refroidissement** exige que les **deux** conditions soient simultanément non respectées :

```
jeter_refroidissement = (durée > 2h) ET (T°finale > 10°C)
```

Si seulement la durée dépasse 2h mais que la T° finale est ≤ 10°C → NC mais **pas de jet**.  
Si seulement la T° finale dépasse 10°C mais que la durée est ≤ 2h → NC mais **pas de jet**.

La règle de jet **cuisson** est distincte et indépendante :

```
jeter_cuisson = (T°initiale < 75°C)
```

Le `jeter` global = `jeter_cuisson OU jeter_refroidissement`.

### 11.2 DLC automatique J+3, capée par la source

Même règle que la Cuisson :
```
dlc_calculee = date_refroidissement + 3j
dlc_finale = min(dlc_calculee, dlc_source)
```

La DLC source est remontée depuis la cuisson liée → ligne de réception d'origine (ou fabrication). Si la DLC est ajustée → popup alert.

### 11.3 Entrée `dlc_devenir` créée automatiquement si jet

Si `jeter_action = True` à la soumission, le backend crée automatiquement une entrée dans la table `dlc_devenir` avec `statut = "jete"`. **Le produit disparaît alors du stock et du calendrier DLC** dès l'enregistrement. Cette action est **définitive** (elle peut être annulée ultérieurement via le calendrier DLC en marquant le devenir comme "annule").

### 11.4 Pré-remplissage depuis la Cuisson

Si la page est ouverte depuis le bouton **"❄ Refroidissement du produit"** du module Cuisson, les données de `sessionStorage` (`refroidissement_prefill`) sont lues et appliquées :

| Donnée | Application |
|---|---|
| `operateur_id` | Opérateur pré-sélectionné (tuile mise en évidence) |
| `produit_id` + `produit_nom` | Produit pré-sélectionné (tuile mise en évidence, ou objet virtuel si absent de la liste) |
| `cuisson_id` | Lien avec la cuisson source |
| `temperature_sortie` | Pré-remplit la T° à cœur avant refroidissement |
| `quantite` + `unite` | Conservés pour le bouton "Remettre en cuisson" |

Si opérateur ET produit sont présents → **saut direct à l'étape 3** (étapes 1 et 2 ignorées).

### 11.5 Calcul de la durée — Passage minuit

La durée est calculée comme `fin - début` en minutes. Si `fin ≤ début`, le système suppose un passage minuit et ajoute 24h :  
*Exemple : début 23:30, fin 01:30 → 120 minutes.*

### 11.6 Heure de fin pré-remplie à `+2h`

À l'arrivée à l'étape 3, si aucune heure de fin n'est déjà saisie, le système calcule automatiquement `heure_fin = heure_debut + 120 min` et active le bouton `+2h (max)`. Ce comportement est déclenché par un `MutationObserver` sur la visibilité de l'étape 3.

---

## 12. Ticket thermique imprimé (format 62 mm)

Déclenché par le bouton "🖨 Imprimer étiquette" via `POST /api/etiquettes/transformes` avec `source_type = "refroidissement"`.

| Zone | Contenu |
|---|---|
| **Tag** | `[REFROIDI]` encadré |
| **Nom produit** | Majuscules |
| **Quantité** | Quantité héritée de la cuisson source |
| **DLC** | Date en rouge format `JJ/MM/AA` — encadrée |
| **Lot** | N° de lot de la réception d'origine |
| **Température** | `T° fin refroidissement : X,X °C` |
| **Ligne action** | `Refroidi le JJ/MM/AA à HHhMM` |
| **Pied** | `Par : [Prénom opérateur]` |

---

## 13. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Soumission sans opérateur | Retour étape 1 + erreur |
| Soumission sans produit | Retour étape 2 + erreur |
| Heures manquantes | Erreur : *"Heures de début et fin requises."* |
| Durée ≤ 0 | Erreur : *"Durée de refroidissement invalide."* |
| T° initiale vide | Erreur : *"Température à cœur avant refroidissement requise."* |
| T° finale vide | Erreur : *"Température à cœur après refroidissement requise."* |
| NC sans confirmation jet | Erreur : *"Confirmez l'action 'Jeter le produit' avant d'enregistrer ([raisons])."* |
| NC sans action corrective (backend) | HTTP 422 avec détail des raisons |
| DLC ajustée à la DLC source | Popup alert : *"⚠ DLC ajustée — [date origine]"* |
| Heure de fin rapide sans heure de début | Erreur : *"Renseignez d'abord l'heure de mise en refroidissement."* |
| Erreur impression étiquette | Toast : *"Erreur impression : [détail]"* |
| Liste produits vide | *"Aucun produit cuit. Enregistrez d'abord une cuisson."* |

---

[Passer au module suivant : Fabrication & Recettes](11_fabrication.md)

# Module 4 — Fiches Incident PCR01

---

## 1. Objectif

La fiche PCR01 est le document réglementaire de traçabilité des non-conformités détectées à la réception. Elle enregistre le produit ou le lot concerné, les motifs de NC, les actions prises (contrôle à cœur, retour fournisseur), et recueille si possible la signature du livreur. Ce module est **toujours déclenché automatiquement** depuis le wizard de réception — il n'a pas de bouton d'accès direct dans le Hub.

---

## 2. Chemins d'accès

| Page | Déclencheur | URL |
|---|---|---|
| **Formulaire PCR01** | Procédure NC du wizard réception (étape 4) | `/pcr01.html` |
| **Liste des fiches d'une réception** | Bouton "Voir incidents" depuis l'historique réception | `/incidents.html?reception_id=XXX` |
| **Consultation d'une fiche** | Clic sur une carte dans la liste | `/pcr01-detail.html?id=XXX` |

> Si l'on accède directement à `/pcr01.html` sans session active (pas de données en `sessionStorage`), le système redirige automatiquement vers `/reception.html`.

---

## 3. Deux modes de la fiche PCR01

### Mode standard — NC produit(s)

Déclenché lorsque des produits restent non conformes après le contrôle à cœur (étape 4 du wizard réception). Une fiche est créée **pour chaque produit NC confirmé**. Si plusieurs produits sont NC, la page affiche un badge de pagination **"X/Y"** et l'opérateur valide les fiches une par une.

### Mode camion — Refus livraison pour propreté NC

Déclenché lorsque l'opérateur refuse la livraison en raison de la propreté du camion non satisfaisante. Une **seule fiche** est créée pour l'ensemble du refus (tous les fournisseurs concernés). Le badge dans l'en-tête indique **"Camion"**.

---

## 4. Interface de la page pcr01.html

### 4.1 En-tête

| Élément | Contenu |
|---|---|
| Bouton `← Retour` | Retour vers le wizard réception (sans enregistrer) |
| Titre | `FICHE INCIDENT PCR01` |
| Badge | `X/Y` (numéro de fiche courant / total) en mode standard — `Camion` en mode camion |

### 4.2 En-tête du document

Rempli automatiquement :
- `Réf. PCR01 — Non-conformité réception`
- Date du jour (format long : lundi 14 mai 2026)
- `Opérateur : [Prénom] à [HH:MM]`

### 4.3 Bloc "Produit non conforme"

Affiché uniquement en mode standard. Rempli automatiquement depuis la session réception :

| Champ | Contenu |
|---|---|
| **Produit** | Nom du produit réceptionné |
| **Fournisseur** | Nom du fournisseur (masqué si absent) |
| **N° lot** | Numéro de lot fournisseur ou lot interne (masqué si absent) |
| **DLC / DLUO** | Date limite (masquée si absente) |
| **Non-conformité** | Liste des motifs NC : `température`, `couleur`, `consistance`, `exsudat`, `odeur`, `pH` |
| **Action immédiate** | `🌡️ Contrôle à cœur effectué — NC confirmé (T° à cœur : X°C)` |

En mode camion, le bloc affiche le ou les **Fournisseur(s) concerné(s)** (tous les fournisseurs du refus, séparés par `, `).

### 4.4 Bloc "Étapes d'identification et de traitement"

Timeline chronologique générée **automatiquement** selon le contexte :

#### Mode standard

1. `Contrôle à la réception (visuel / température) → Non-conformité détectée : [motifs] (température camion : X°C).`
2. `Lot isolé immédiatement pour prise de température à cœur.`
3. Si livreur présent : `Livreur présent : feuille de reprise avec retour marchandise signée par le livreur.`  
   Si livreur absent : `Livreur absent : lot isolé avec apposition de l'étiquette À REPRENDRE en attente de retour fournisseur.`

#### Mode camion

1. `Contrôle du camion à la réception → Non-conformité détectée : [problèmes relevés] [+ température camion X°C si > 4°C].`
2. `Fournisseur(s) concerné(s) : [noms].`
3. `Photo du bon de livraison prise : oui (1 par fournisseur).`
4. `Livraison refusée pour l'ensemble du camion.`
5. Selon présence livreur : `Livreur présent : feuille de reprise signée.` ou `Livreur absent : incident enregistré pour suivi fournisseur.`

### 4.5 Bloc "Le livreur est encore là ?" — mode camion uniquement

Affiché uniquement en mode camion (le choix livreur a déjà été fait à l'étape 4 du wizard en mode standard). Deux boutons :
- **`✔ Oui, il est là`** → affiche le bloc signature, masque l'étiquette "À RETOURNER"
- **`✕ Non, il est parti`** → masque la signature, affiche le bouton d'impression

### 4.6 Bloc "Action corrective"

Zone de texte **pré-remplie automatiquement** selon les données de la session. Le texte généré varie selon les motifs NC, la présence du livreur et son attestation (voir section 6). Ce texte est **modifiable** par l'opérateur.

L'action corrective est **obligatoire** pour enregistrer la fiche.

### 4.7 Bloc "Commentaire"

Zone de texte libre, optionnelle. Exemple suggéré : `Relancer fournisseur le …, vérifier prochain lot`.

### 4.8 Bloc "Signature du livreur" — livreur présent uniquement

Visible si le livreur est présent (mode standard ou mode camion après sélection "Oui, il est là").

**Choix livreur :**
- **`✓ Atteste de la NC et accepte le retour`** → le texte de l'action corrective se met à jour pour refléter l'acceptation du retour. Le bouton "À RETOURNER" reste masqué.
- **`✕ N'atteste pas la NC et refuse le retour`** → le texte de l'action corrective se met à jour pour mentionner l'isolement du produit. Le bouton **"🖨️ Imprimer étiquette À RETOURNER"** apparaît.

**Canvas de signature :**
- Zone de dessin tactile (stylet ou doigt sur tablette)
- Bouton **`↺ Effacer`** : efface le canvas pour recommencer
- La signature est **obligatoire** si le livreur est présent (la zone canvas doit contenir au moins un trait)

### 4.9 Bouton "🖨️ Imprimer étiquette À RETOURNER"

Visible dans deux cas :
1. Livreur présent mais **refuse d'attester** la NC
2. Livreur **absent** (mode standard ou mode camion)

Cliquer ce bouton déclenche `window.print()` et imprime l'étiquette À RETOURNER (voir section 7). Le bouton devient `✓ Imprimé — [Nom produit]` après impression.

### 4.10 Bloc "Étiquettes À RETOURNER" — livreur absent, mode standard

Visible uniquement si le livreur est absent en mode standard. Affiche un **bouton d'impression par produit NC** :
- `🖨️ Étiquette — [Nom produit]`
- Devient `✓ Imprimé — [Nom produit]` après impression

### 4.11 Bouton fixe "💾 Enregistrer cette fiche"

Bouton permanent en bas d'écran. Le bouton change visuellement (légère opacité) si des champs obligatoires manquent, mais reste cliquable — c'est au clic que les erreurs sont signalées avec vibration et animation.

---

## 5. Mode d'emploi pas-à-pas

### 5.1 Fiche standard (N produits NC)

1. La page s'ouvre automatiquement au retour de l'étape 4 du wizard réception.
2. Vérifier les informations pré-remplies (produit, motifs, action immédiate).
3. Si livreur présent : sélectionner `✓ Atteste` ou `✕ N'atteste pas`, puis signer le canvas.
4. Si livreur absent : imprimer l'étiquette "À RETOURNER" en cliquant le bouton correspondant.
5. Compléter ou ajuster le texte de l'**Action corrective** si nécessaire.
6. Ajouter un commentaire (optionnel).
7. Cliquer **`💾 Enregistrer cette fiche`**.
8. Si plusieurs fiches : la page passe automatiquement à la fiche suivante (badge `2/N`, `3/N`…).
9. Après la dernière fiche : redirection automatique vers `/reception.html` → le wizard reprend à l'étape 4 pour la clôture finale.

### 5.2 Fiche camion (refus propreté)

1. La page s'ouvre automatiquement après le flux de refus livraison (étape 1 du wizard réception).
2. Répondre à la question **"Le livreur est encore là ?"** :
   - `✔ Oui` → zone signature apparaît, choisir l'attestation, signer.
   - `✕ Non` → bouton "🖨️ Imprimer étiquette À RETOURNER" apparaît.
3. Vérifier / compléter l'**Action corrective**.
4. Cliquer **`💾 Enregistrer cette fiche`**.
5. La réception est **clôturée automatiquement** avec `livraison_refusee=true`.
6. Redirection vers `/hub.html`.

---

## 6. Règles de conformité invisibles

### 6.1 Auto-remplissage de l'action corrective

Le texte est généré automatiquement et **se met à jour en temps réel** lorsque l'opérateur modifie son choix (présence livreur, attestation). Les formulations exactes sont :

**Mode standard :**

| Situation | Texte généré |
|---|---|
| Base (tous cas) | `Non-conformité constatée à la réception : [motifs] sur [produit] (lot [num]).`<br>`Contrôle à cœur effectué : non-conformité confirmée. La température à cœur mesurée est de X°C.` |
| Livreur présent + atteste et accepte | `…La non-conformité est attestée et le retour accepté, la feuille de reprise avec retour marchandise a été signée par le livreur.` |
| Livreur présent + refuse le retour | `…La non-conformité n'est pas attestée par le livreur et le retour n'est pas accepté. Le produit est isolé et balisé en attente de la résolution du litige.` |
| Livreur absent | `…En l'absence du livreur, le lot a été isolé avec apposition de l'étiquette À RETOURNER en attente de retour fournisseur.` |

**Mode camion :**

Le texte cite les problèmes de propreté cochés à l'étape 1, la température camion si elle dépasse 4°C, les noms de fournisseurs concernés, et se termine par la mention de la livraison refusée + situation livreur.

### 6.2 Seuil température camion en mode camion

La condition `tempCamion > 4` (strictement supérieur à 4°C) déclenche l'ajout de la mention *"Température camion NC : X°C (seuil ≤ 4°C)"* dans les étapes d'identification et dans l'action corrective.

### 6.3 Une seule fiche en mode camion

En mode camion, il n'y a qu'une seule fiche PCR01 quel que soit le nombre de fournisseurs concernés. Tous les noms de fournisseurs sont concaténés avec ` + ` et stockés dans le champ `fournisseur_nom`. Le premier fournisseur avec un ID connu est utilisé comme clé étrangère `fournisseur_id`.

### 6.4 Clôture automatique de la réception en mode camion

Après enregistrement de la fiche PCR01 en mode camion, le système appelle automatiquement `PUT /api/receptions/{id}/cloturer` avec `livraison_refusee: true`. L'opérateur n'a pas besoin de retourner dans le wizard.

### 6.5 Sauvegarde de la signature

La signature dessinée sur le canvas est convertie en PNG (via `canvas.toDataURL('image/png')`) et envoyée au serveur comme fichier joint (`signature_livreur`). Elle est stockée dans `data/photos/signatures/SIG-YYYYMMDD-HHMMSS-{id}.png`.

### 6.6 Vérification "signature vide"

Avant l'enregistrement, le système lit tous les pixels du canvas. Si chaque pixel est à zéro (canvas entièrement blanc), la signature est considérée vide → message d'erreur.

---

## 7. Contenu de l'étiquette "À RETOURNER" imprimée

Format `window.print()` (feuille A4, pas d'imprimante thermique pour ce gabarit). Contenu :

| Zone | Contenu |
|---|---|
| **Bandeau rouge** | `PRODUIT NON CONFORME` |
| **Titre** | `À RETOURNER` |
| **Référence** | `Réf. PCR01 — Non-conformité réception` |
| **Date/heure/opérateur** | Date longue, prénom opérateur, heure réception |
| **Tableau** | Produit, Fournisseur, N° lot, DLC/DLUO, Non-conformité, Action immédiate |
| **Pied** | `Au Comptoir des Lilas — Réf. PCR01` |

> En mode camion, le produit est affiché comme `Livraison refusée — Propreté camion`, et le motif liste les problèmes cochés à l'étape 1.

---

## 8. Page incidents.html — Liste des fiches d'une réception

**Accès :** depuis le détail d'une réception dans l'historique, via un lien `?reception_id=XXX`.

### 8.1 Interface

- **Compteur** : `N fiche(s) PCR01`
- **Liste de cartes** (une par fiche) :
  - Date de l'incident
  - Badge statut : `🔄 Ouverte` ou `✓ Fermée`
  - Nature du problème
  - Action immédiate
- **Clic sur une carte** → redirection vers `/pcr01-detail.html?id=XXX`

### 8.2 Comportements UX

- Inactivité 5 minutes → redirection automatique vers `/hub.html`
- Bouton `← Retour` : retour à la page précédente (`window.history.back()`)
- Si `reception_id` manquant dans l'URL : message d'erreur `⚠️ ID de réception manquant.`

---

## 9. Cas d'erreurs et validations

| Situation | Ce qui se passe |
|---|---|
| Action corrective vide | Message : *"L'action corrective est obligatoire."* + contour rouge animé + scroll + vibration |
| Mode camion : présence livreur non précisée | Message : *"Veuillez indiquer si le livreur est présent ou absent."* + animation sur les deux boutons |
| Livreur présent : attestation non choisie | Message : *"Veuillez indiquer si le livreur atteste ou n'atteste pas la NC."* + animation |
| Canvas signature vide (livreur présent) | Message : *"La signature du livreur est obligatoire."* + contour rouge sur le canvas |
| Erreur API enregistrement | Message rouge : *"Erreur : [détail]"* |
| Page ouverte sans session PCR01 | Redirection immédiate vers `/reception.html` |

---

[Passer au module suivant : Tâches HACCP](05_taches.md)

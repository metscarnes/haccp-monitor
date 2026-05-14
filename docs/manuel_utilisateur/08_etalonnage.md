# Module 8 — Étalonnage Thermomètres (EET01)

---

## 1. Objectif

Ce module enregistre l'étalonnage trimestriel des thermomètres selon la procédure **EET01**. L'opération se déroule en **deux phases** : d'abord la vérification du thermomètre de référence dans l'eau glacée (0°C ± 0,5°C), puis la comparaison de chaque sonde Zigbee des enceintes frigorifiques avec ce même thermomètre.

---

## 2. Chemins d'accès

| Page | URL | Accès |
|---|---|---|
| **Phase 1 — Étalonnage référence** | `/etalonnage.html` | Hub Tâches HACCP → tuile 🌡️ ÉTALONNAGE |
| **Phase 2 — Comparaison sondes** | `/etalonnage-comparaison.html?id=XXX` | Automatique après validation Phase 1 |

---

## 3. Architecture en deux phases

```
Phase 1 (etalonnage.html)
  ↓ Conforme OU Remplacé
Phase 2 (etalonnage-comparaison.html)
  ↓ Enregistrer
Retour à etalonnage.html

Phase 1
  ↓ Calibrage seulement
Message + formulaire réinitialisé (PAS de Phase 2)
```

> Si la Phase 1 aboutit à un **Calibrage**, la Phase 2 n'est pas accessible immédiatement. L'opérateur doit d'abord effectuer le calibrage physique du thermomètre, puis créer un nouvel enregistrement de Phase 1.

---

## 4. Page Phase 1 — Étalonnage du thermomètre de référence

### 4.1 Encart règle (permanent)

> *"Règle de conformité : 0°C ± 0,5°C (de −0,5°C à +0,5°C) — Hors intervalle : remplacer le thermomètre. Dans tous les cas : nettoyer la sonde et la ranger."*

### 4.2 Formulaire "Nouvel enregistrement"

| Champ | Obligatoire | Notes |
|---|---|---|
| **Date** | Oui ✱ | Pré-remplie avec la date du jour |
| **Opérateur** | Oui ✱ | Menu déroulant — personnel actif |
| **Thermomètre de référence** | Oui ✱ | Menu déroulant — thermomètres actifs configurés dans l'administration. Affiché : `Nom — N° série` (ou juste `Nom` si pas de numéro) |
| **Température mesurée (°C)** | Oui ✱ | Saisie décimale (ex. : `0,2`). Pas de borne min/max imposée. |
| **Résultat** | Auto | Badge mis à jour en temps réel dès la saisie de la température |
| **Action corrective** | Oui ✱ | Radio — disponibilité des options dépend du résultat (voir section 5) |
| **Commentaire** | Non | Zone de texte libre (ex. : numéro de série, marque…) |

### 4.3 Badge de conformité temps réel

Mis à jour à chaque frappe dans le champ Température :

| Valeur saisie | Badge affiché |
|---|---|
| Vide | `— Saisir une température` (gris) |
| T° ∈ [−0,5°C ; +0,5°C] | `✅ Conforme — X,X°C dans [−0,5 ; +0,5]` (vert) |
| T° hors intervalle | `❌ Non conforme — X,X°C hors tolérance` (rouge) |

### 4.4 Tableau historique

Sous le formulaire, un tableau affiche les 50 derniers étalonnages avec les colonnes :
**Date** · **Thermomètre** · **Température** · **Résultat** (badge vert/rouge) · **Action corrective** · **Opérateur**

---

## 5. Mode d'emploi Phase 1

1. Préparer un bain d'eau glacée (eau + glaçons, brassée pour homogénéité).
2. Plonger le thermomètre de référence, attendre stabilisation.
3. Ouvrir la page `/etalonnage.html`.
4. Vérifier/ajuster la **Date** et sélectionner l'**Opérateur**.
5. Sélectionner le **Thermomètre de référence** utilisé.
6. Saisir la **Température mesurée** → le badge de conformité s'affiche immédiatement.
7. Sélectionner l'**Action corrective** (les options non applicables sont grisées automatiquement).
8. Ajouter un **Commentaire** si nécessaire.
9. Cliquer **`Enregistrer ✓`**.

---

## 6. Règles de sélection des actions correctives

Les options sont activées/désactivées **automatiquement** selon la température saisie. Aucune saisie manuelle contraire n'est possible (le frontend désactive les mauvaises options, le backend rejette les incohérences) :

| Température | Options disponibles | Option auto-sélectionnée |
|---|---|---|
| Vide | Toutes désactivées | — |
| Conforme (∈ [−0,5 ; +0,5°C]) | `✅ Conforme` uniquement | **Conforme** (automatique) |
| Non conforme (hors tolérance) | `🔧 Calibrage` et `🔄 Remplacé` uniquement | Aucune |

### Signification des actions

| Action | Signification | Suite |
|---|---|---|
| `✅ Conforme` | Le thermomètre est précis dans les tolérances | → Passe à la **Phase 2** |
| `🔧 Calibrage` | Le thermomètre a été recalibré | → **Pas de Phase 2** — formulaire réinitialisé |
| `🔄 Remplacé` | Le thermomètre a été remplacé par un nouveau | → Passe à la **Phase 2** |

---

## 7. Après la soumission Phase 1

### Cas Calibrage

Un message vert s'affiche :  
*"🔧 Calibrage enregistré. Effectuez le calibrage puis créez un nouvel enregistrement pour passer aux comparaisons."*

Le formulaire se réinitialise. L'historique se recharge. L'opérateur doit physiquement calibrer le thermomètre, puis créer un nouvel enregistrement Phase 1 jusqu'à obtenir un résultat Conforme ou Remplacé.

### Cas Conforme ou Remplacé

Redirection automatique vers `/etalonnage-comparaison.html?id={id}` — Phase 2.

---

## 8. Page Phase 2 — Comparaison des sondes Zigbee

### 8.1 En-tête et contexte

- Bouton **`← Étape 1`** : retour vers `/etalonnage.html`
- Bandeau **"✅ Étape 1 validée"** avec résumé de la Phase 1 : nom du thermomètre, T° mesurée, action corrective, opérateur

Instruction permanente :  
*"Plongez le thermomètre de référence dans chaque enceinte et saisissez sa lecture. La sonde connectée est relevée automatiquement. Conformité : écart ≤ ±0,5°C."*

### 8.2 Grille des enceintes

Une **carte par enceinte** frigorifique configurée. Chaque carte contient :

| Élément | Contenu |
|---|---|
| **Nom de l'enceinte** | Identifiant de l'enceinte (ex. : "Chambre froide 1") |
| **Sonde Zigbee** | Température actuelle relevée automatiquement depuis l'API (ex. : `2,1 °C`) |
| **Thermo de référence** | Champ de saisie décimale obligatoire (ex. : `2,4`) |
| **Badge écart** | Résultat affiché en temps réel dès la saisie |

### 8.3 Badge d'écart temps réel

L'écart est calculé comme `T°référence − T°Zigbee` :

| Écart | Badge |
|---|---|
| Non saisi | `— Saisir la température de référence` (gris) |
| \|écart\| ≤ 0,5°C | `✅ Conforme — écart : +X,X°C dans [−0,5 ; +0,5]` (vert) |
| \|écart\| > 0,5°C | `❌ Non conforme — écart : +X,X°C hors tolérance` (rouge) |

### 8.4 Actualisation des sondes Zigbee

Les températures des sondes sont **rechargées automatiquement toutes les 30 secondes** depuis l'API. Seules les valeurs affichées sont mises à jour (les cartes ne sont pas reconstruites).

### 8.5 Bouton "Enregistrer les comparaisons ✓"

Reste **désactivé** tant que tous les champs de température de référence ne sont pas renseignés. Dès que toutes les enceintes ont une valeur valide, il s'active.

Après soumission réussie → redirection vers `/etalonnage.html`.

---

## 9. Mode d'emploi Phase 2

1. Pour chaque enceinte, plonger le thermomètre de référence et attendre la stabilisation.
2. Saisir la lecture dans le champ **"Thermo de référence"** de la carte correspondante.
3. Observer le badge écart — vérifier la conformité.
4. Répéter pour toutes les enceintes.
5. Quand toutes les cartes sont renseignées, cliquer **`Enregistrer les comparaisons ✓`**.

---

## 10. Règles de conformité invisibles

### 10.1 Fréquence trimestrielle — 92 jours

La fréquence réglementaire est de **92 jours** (~3 mois). Le système calcule la date du prochain étalonnage : `date_dernier + 92j`. Si cette date est dépassée, l'étalonnage est marqué **"en retard"** dans le Hub HACCP.

L'API `GET /api/etalonnage/status` retourne :
- `en_retard` : booléen
- `jamais_fait` : booléen (si aucun étalonnage en base)
- `dernier_date`, `dernier_thermo`, `dernier_operateur`
- `prochain_date`, `jours_restants`

### 10.2 Double validation côté frontend ET backend

La règle de cohérence action/température est vérifiée **deux fois** :
1. **Frontend** : désactive visuellement les mauvaises options dès la saisie
2. **Backend** : rejette avec HTTP 400 si l'incohérence persiste (ex. : action="conforme" envoyée avec une T° hors tolérance)

Ce double contrôle garantit l'intégrité même si quelqu'un contourne l'interface.

### 10.3 Re-soumission de Phase 2 sécurisée

Si la Phase 2 est soumise plusieurs fois pour le même étalonnage (ex. : retour arrière), le backend **supprime d'abord** toutes les comparaisons existantes avant de réinsérer les nouvelles. Il n'y a pas de duplication.

### 10.4 Accès Phase 2 conditionnel

Le backend vérifie que l'étalonnage référencé par l'`id` en URL est en état `conforme` ou `remplace`. Si l'état est `calibrage`, l'enregistrement des comparaisons est rejeté avec HTTP 400 :  
*"Le thermomètre de référence doit être conforme ou remplacé avant de réaliser les comparaisons."*

Si aucun `id` n'est présent dans l'URL de Phase 2, redirection automatique vers `/etalonnage.html`.

### 10.5 Calcul de l'écart (Phase 2)

`écart = round(temp_reference − temp_zigbee, 2)`

Conforme si `|écart| ≤ 0,5°C`. L'écart est stocké tel quel (avec signe) en base.

---

## 11. Cas d'erreurs et alertes

| Situation | Ce qui se passe |
|---|---|
| Date vide | Message rouge : *"La date est obligatoire."* |
| Opérateur non sélectionné | Message rouge : *"Sélectionnez un opérateur."* |
| Thermomètre non sélectionné | Message rouge : *"Sélectionnez un thermomètre de référence."* |
| Température vide | Message rouge : *"La température est obligatoire."* |
| Action corrective non sélectionnée | Message rouge : *"Sélectionnez une action corrective."* |
| Aucun thermomètre configuré | Menu déroulant affiche `⚠ Aucun thermomètre configuré` (option désactivée) |
| Incohérence action/T° (backend) | HTTP 400 avec message explicite |
| Erreur réseau Phase 1 | Message rouge sous le formulaire : *"Erreur : [détail]"* |
| Températures Zigbee non disponibles | Enceinte affiche `— °C`, badge reste vide |
| Enceinte sans T° Zigbee (soumission Phase 2) | La valeur `0` est utilisée par défaut pour le calcul d'écart |
| T° de référence manquante (soumission Phase 2) | Message rouge : *"Toutes les températures de référence sont obligatoires."* |
| Erreur réseau Phase 2 | Message rouge, bouton réactivé |

---

[Passer au module suivant : Cuisson HACCP (≥ 75°C)](09_cuisson.md)

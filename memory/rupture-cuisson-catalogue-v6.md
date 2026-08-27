---
name: rupture-cuisson-catalogue-v6
description: Cuisson/Refroidissement sont restés sur la table `produits` après la migration v6.0 vers les catalogues Achats/Vente — 100 % du stock réel est non cuisinable. Chantier en cours au 2026-08-27.
metadata:
  type: project
---

La migration **v6.0** (`_migrer_production_v6`, `src/database.py` ~L2455) a basculé Réception
et Production vers les catalogues Achats/Vente :

| Table | Avant v6 | Après v6 |
|---|---|---|
| `recettes` | `produit_fini_id` → `produits` | `catalogue_vente_id` → `catalogue_vente` |
| `recette_ingredients` | `produit_id` | `catalogue_fournisseur_id` |
| `reception_lignes` | `produit_id` NOT NULL | `produit_id` **nullable** + `catalogue_fournisseur_id` |

**Cuisson et Refroidissement n'ont jamais été migrés** : `cuissons.produit_id` et
`refroidissements.produit_id` sont toujours NOT NULL → FK `produits`.

## Mesures sur la base de PROD (Pi, 2026-08-27)

Via `scripts/diag_rupture_reception_cuisson.py` (lecture seule, à relancer pour réévaluer) :

- 858 lignes de réception, dont **855 (99 %) sans `produit_id`**
- Stock vivant : **320 lots, dont 320 (100 %) non cuisinables** (POST cuisson → HTTP 422)
- **2 cuissons** enregistrées en tout → le module est mort en pratique, pas seulement dégradé
- Lasagne / Gratin dauphinois / Parmentier de canard : **0 dans `produits`**, 29 dans
  `catalogue_fournisseur` (9 + 12 + 8)

## Les deux bugs

1. **`src/api/routes_cuisson.py:320`** interroge `rec.produit_fini_id`, colonne supprimée par
   la v6 → `GET /api/cuisson/produits/{id}/receptions` renvoie **HTTP 500 systématiquement**.
   C'est le chemin critique du wizard (`static/js/cuisson.js:433`, à la sélection du produit).
2. **`static/js/cuisson.js:483`** avale l'erreur (`console.warn` seul) et avance quand même à
   l'étape 3 → la cuisson est enregistrée avec `reception_ligne_id = NULL`.
   Conséquence HACCP : **traçabilité amont perdue et DLC non plafonnée par la DLC source**,
   sans aucun signal visible pour l'opérateur.

## ⚠️ Travail existant à NE PAS lancer tel quel

Écrits le 2026-08-27 **avant** la découverte de la rupture, donc ciblés sur la mauvaise table
(`produits`) — ils trouveraient zéro ligne et ne feraient rien, silencieusement :

- `scripts/rattrapage_cuisson_refroidissement.py` (rattrapage des cycles depuis le 2026-06-10)
- `GET /api/cuisson/a-traiter` + colonne `produits.suivi_cuisson_auto` + tuile Hub
  `production_a_cuire` + `static/production-a-cuire.html` + case à cocher dans
  `static/catalogue.html` + `tests/test_production_a_cuire.py`

Tout cela doit être re-pointé vers les catalogues avant usage. Le rattrapage ne peut se faire
qu'**après** la reconnexion (sinon rien à rattacher).

## Décisions prises

- **Reconnexion** : ajouter `catalogue_fournisseur_id` à `cuissons` et `refroidissements`,
  rendre `produit_id` nullable — même bascule que celle déjà faite sur `reception_lignes`.
  Les 2 cuissons existantes restent valides.
- **Déclenchement du cycle** : ne PAS se limiter à une case sur `catalogue_fournisseur`.
  Ulysse doit pouvoir choisir depuis le **catalogue de vente ET d'achat**, reliés par le
  rapprochement qu'utilise déjà le **comparatif achats** (`static/catalogue-achats.html`,
  `static/js/achats/comparatif-achats.js`). Exemple donné : un *rosbeef cuit* (produit de
  vente) provient de morceaux précis du catalogue d'achat qui ne portent pas le même nom.
- Valeurs de rattrapage : ~75–76,5 °C en cuisson, ~7–8,8 °C en refroidissement, durée < 2 h,
  avec variation réaliste (jamais une colonne de valeurs identiques). Opérateur = Ulysse.

## Prochaine étape

Lire comment le comparatif achats relie vente ↔ achat (vraie table de liaison ou matching par
nom à la volée ?) avant de concevoir le déclencheur. Puis : corriger les 2 bugs, migrer le
schéma, re-cibler la détection, et seulement ensuite lancer le rattrapage depuis le 2026-06-10.

**Why:** ces chiffres viennent d'un audit ponctuel sur la base de prod, non déductibles du code ;
et le piège (travail déjà écrit mais mal ciblé) ferait perdre du temps ou produirait un
rattrapage vide et silencieux.
**How to apply:** relancer `python3 scripts/diag_rupture_reception_cuisson.py` sur le Pi
(cf. [[pi-deploiement-oom-reception]] pour l'accès) pour réévaluer avant toute reprise.

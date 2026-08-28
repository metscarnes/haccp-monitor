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

## Les deux bugs — CORRIGÉS le 2026-08-27

1. ~~**`src/api/routes_cuisson.py:320`** interrogeait `rec.produit_fini_id`~~ → corrigé en
   `rec.catalogue_vente_id`. Vérifié : l'endpoint passe de HTTP 500 à HTTP 200.
   Convention retenue : pour les lots de **fabrication**, le `produit_id` de l'URL est un
   `catalogue_vente.id` — c'est déjà ce que fait `get_stock_unifie` (`cv.id AS produit_id`).
2. ~~**`static/js/cuisson.js:483`** avalait l'erreur~~ → affiche désormais un message explicite
   nommant la conséquence (pas de lot, DLC non plafonnée). La production n'est pas bloquée,
   mais le silence — pire cas pour un registre HACCP — est supprimé.

## Migration v7.4 — faite le 2026-08-27

`cuissons` et `refroidissements` ont désormais `catalogue_fournisseur_id` (le lot d'achat cuit)
et `catalogue_vente_id` (ce qu'on produit) ; `produit_id` est passé **nullable** (rebuild de
table, SQLite ne sait pas retirer un NOT NULL). `catalogue_vente.suivi_cuisson_auto` ajouté.

**Piège rencontré, à ne pas réintroduire :** le rebuild ne peut PAS tourner dans le bloc
principal de `init_db()`. La connexion d'init garde ~100 curseurs ouverts (la liste `migrations`)
et un DROP/CREATE la laisse verrouillée → les migrations suivantes (v4.2, v5.8, v5.9, tolérances)
échouent toutes en « database is locked ». Le rebuild vit donc dans
`_migrer_cuisson_catalogues_v74()`, appelée **après** l'init sur une connexion dédiée — même
parade que la v6.0. Validé sur une base rétrogradée à l'ancien schéma : données préservées,
idempotent, sans table orpheline, et suite de tests inchangée (33 échecs préexistants / 283 OK).

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

## Liaison vente ↔ achat — confirmée exploitable (audit Pi 2026-08-27)

Il existe une vraie chaîne de liaison, pas un matching par nom :

```
catalogue_vente  --comparatif_groupe_vente-->  comparatif_groupe
                 --comparatif_groupe_ligne-->  catalogue_fournisseur
```

`comparatif_groupe_vente` a un `ligne_choisie_id` = l'article d'achat de référence **propre à
chaque produit de vente** (v6.5). Le commentaire de la v6.4 décrit exactement le cas d'Ulysse :
« un même achat sert PLUSIEURS produits de vente (cuisse → steak haché, rôti, bourguignon…) ».

État mesuré : 181 produits de vente actifs, 116 groupes, 176 liens vente, 292 liens achat.
Les plats visés sont **tous déjà reliés** : Lasagnes (groupe #7, 3 achats), Gratin dauphinois
(#12), Parmentier canard (#8, 4 achats), Rosbeef cuit (#132, 14 achats).

⚠️ Deux points à arbitrer avec Ulysse : « Rosbeef cuit » existe en doublon (id=106 avec double
espace, id=114), et il **partage le groupe #132 avec « Rosbeef cru »** — un lot reçu peut donc
alimenter l'un ou l'autre ; le déclencheur ne peut pas deviner lequel.

## Reste à faire

1. `POST /api/cuisson/enregistrements` et `/api/refroidissement/enregistrements` : accepter
   `catalogue_fournisseur_id` / `catalogue_vente_id` (aujourd'hui `produit_id: int` obligatoire
   → HTTP 422 sur tout lot du catalogue achats).
2. `GET /api/cuisson/produits-disponibles` : les lots sans produit interne remontent avec
   `produit_id=None` et s'écrasent entre eux (dict keyé sur cette valeur).
3. Re-cibler la détection auto sur `catalogue_vente.suivi_cuisson_auto` + la chaîne comparatif ;
   déplacer la case à cocher de `catalogue.html` (table `produits`) vers le catalogue de vente.
4. Corriger `scripts/rattrapage_cuisson_refroidissement.py` (joint encore `produits`), puis le
   lancer sur le Pi pour la période depuis le 2026-06-10.

**Why:** ces chiffres viennent d'un audit ponctuel sur la base de prod, non déductibles du code ;
et le piège (travail déjà écrit mais mal ciblé) ferait perdre du temps ou produirait un
rattrapage vide et silencieux.
**How to apply:** relancer `python3 scripts/diag_rupture_reception_cuisson.py` sur le Pi
(cf. [[pi-deploiement-oom-reception]] pour l'accès) pour réévaluer avant toute reprise.

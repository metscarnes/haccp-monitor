# Point d'étape — Chaîne Réception → Cuisson → Refroidissement

> **Dernière mise à jour :** 28/08/2026
> **Objectif initial :** mettre en place un cycle automatique cuisson/refroidissement
> déclenché par les réceptions et les n° de lot (lasagnes, gratin dauphinois,
> parmentier de canard).

---

## 1. Résumé

Le besoin de départ était un **déclencheur automatique**. L'analyse a révélé un problème
bien plus profond en amont : le module Cuisson était **inutilisable sur la totalité du
stock réel**. Il fallait donc réparer la chaîne avant de pouvoir automatiser quoi que ce soit.

À ce jour, la chaîne est réparée et fonctionnelle de bout en bout. Le déclencheur
automatique reste à brancher.

| Verrou | État |
|---|---|
| Bug HTTP 500 systématique dans le wizard Cuisson | ✅ Corrigé |
| Perte silencieuse de traçabilité | ✅ Corrigé |
| Schéma incompatible avec le stock réel (migration v7.4) | ✅ Corrigé — appliqué en prod |
| API refusant les lots du catalogue achats | ✅ Corrigé |
| Détection automatique « à cuire » | ⬜ À faire |
| Rattrapage depuis le 10/06 | ⬜ À faire |

---

## 2. Le problème découvert

### 2.1 Origine — une migration inachevée

La migration **v6.0** avait basculé la Réception et la Production vers les catalogues
Achats/Vente :

| Table | Avant v6 | Après v6 |
|---|---|---|
| `recettes` | `produit_fini_id` → `produits` | `catalogue_vente_id` → `catalogue_vente` |
| `recette_ingredients` | `produit_id` | `catalogue_fournisseur_id` |
| `reception_lignes` | `produit_id` NOT NULL | `produit_id` **nullable** + `catalogue_fournisseur_id` |

**Cuisson et Refroidissement n'avaient jamais suivi.** Ils exigeaient encore un produit
interne (`produits`), alors que le stock n'en a plus.

### 2.2 Ampleur mesurée sur la base de production (27/08/2026)

| Mesure | Valeur |
|---|---|
| Lignes de réception au total | 858 |
| Dont **sans `produit_id`** | **855 (99 %)** |
| Stock vivant | 320 lots |
| Dont **non cuisinables** | **320 (100 %)** |
| Cuissons enregistrées depuis toujours | **2** |
| Plats traiteur présents dans `produits` | **0** (29 dans le catalogue achats) |

> Le module n'était pas dégradé : il était **mort**. Aucun lot du stock réel ne pouvait
> être cuit. C'est cohérent avec la demande initiale de rattrapage — les cuissons
> existaient en boutique, mais ne pouvaient pas être tracées dans le logiciel.

---

## 3. Ce qui a été corrigé

### 3.1 Crash du wizard Cuisson

`routes_cuisson.py` interrogeait `rec.produit_fini_id`, colonne supprimée par la v6.
→ `GET /api/cuisson/produits/{id}/receptions` renvoyait **HTTP 500 à chaque appel**.

Corrigé en `rec.catalogue_vente_id`. **Vérifié : HTTP 500 → HTTP 200.**

### 3.2 Perte silencieuse de traçabilité

`cuisson.js` avalait l'erreur (`console.warn` seul) et avançait quand même à l'étape 3.
La cuisson était alors enregistrée **sans lot source et avec une DLC non plafonnée** par
la DLC d'origine, sans aucun signal pour l'opérateur.

L'erreur est désormais affichée en clair, en nommant la conséquence. La production n'est
pas bloquée — un blocage dur arrêterait la boutique — mais le silence, pire cas pour un
registre HACCP, est supprimé.

### 3.3 Migration v7.4 — le schéma rejoint les catalogues

`cuissons` et `refroidissements` reçoivent :

- `catalogue_fournisseur_id` — le lot d'achat réellement cuit
- `catalogue_vente_id` — ce que l'on produit (ex. « Rosbeef cuit »)
- `produit_id` devient **nullable** (rebuild de table : SQLite ne sait pas retirer un NOT NULL)

`catalogue_vente.suivi_cuisson_auto` est ajouté pour le futur déclencheur.

> **Piège rencontré — à ne pas réintroduire.** Le rebuild ne peut pas tourner dans le bloc
> principal de `init_db()` : la connexion d'init garde une centaine de curseurs ouverts, et
> un `DROP/CREATE` la laisse verrouillée, faisant échouer **toutes** les migrations suivantes
> (v4.2, v5.8, v5.9, tolérances) — dont celles qui recalculent les statuts de réception.
> Le rebuild vit donc dans `_migrer_cuisson_catalogues_v74()`, exécutée après l'init sur une
> connexion dédiée. Même parade que la v6.0.

### 3.4 API rebranchée sur les catalogues

Un produit s'identifie désormais par une **clé composite** `(cle_type, cle_id)` avec
`cle_type ∈ {produit, vente, achat}`, côté API comme côté interface.

- `CuissonCreate` / `RefroidissementCreate` : `produit_id` optionnel, ajout des deux
  identifiants catalogue. **Au moins un des trois est exigé** (422 sinon) — une cuisson
  sans identité serait intraçable.
- Le refroidissement **hérite** l'identité de sa cuisson quand `cuisson_id` est fourni.
- Nouvel endpoint `GET /api/cuisson/lots?<referentiel>_id=…` — exactement un identifiant
  attendu. L'ancienne route est conservée pour compatibilité.

### 3.5 Deux bugs sérieux trouvés en chemin

**Les lots s'écrasaient entre eux.** `produits-disponibles` regroupait par `produit_id`.
Comme il vaut `NULL` pour 99 % du stock, tous ces lots fusionnaient dans une **unique
entrée** : un seul produit s'affichait au lieu de plusieurs centaines.

**La chaîne s'arrêtait après la cuisson.** Dans `get_stock_unifie`, les branches cuisson et
refroidissement faisaient un `JOIN produits` strict. Une cuisson issue du catalogue
n'apparaissait donc pas en stock, et **jamais dans le module Refroidissement** : on pouvait
cuire un produit sans jamais pouvoir enregistrer son refroidissement. Passé en `LEFT JOIN`
+ `COALESCE` sur les catalogues.

Côté interface, la sélection comparait `produitChoisi.id === p.id`. Avec `id` à `null`,
`null === null` est vrai : **toutes** les tuiles catalogue seraient apparues sélectionnées
simultanément.

---

## 4. Vérifications effectuées

Test de bout en bout sur le scénario réel — lasagne reçue, cuite, refroidie, sur un lot
**sans produit interne** :

| Étape | Résultat |
|---|---|
| Deux articles distincts proposés (plus de fusion) | ✅ |
| `POST` cuisson avec `produit_id` NULL | **201** (était 422) |
| Refus si aucun identifiant fourni | 422 ✅ |
| La cuisson apparaît au refroidissement | ✅ nommée « Lasagnes » |
| `POST` refroidissement, identité héritée | 201, lot `LOT-LAS-001` conservé |

La migration a également été testée sur une base **rétrogradée à l'ancien schéma**, pour
exercer le vrai chemin de rebuild : données préservées, idempotent, aucune table orpheline.

**Suite de tests : 33 échecs / 283 réussis** — strictement identique à la mesure de référence
prise avant toute modification. Aucune régression. *(Ces 33 échecs sont préexistants et
concernent des tests écrits contre le schéma pré-v6.)*

---

## 5. Ce qui reste à faire

1. **Détection automatique « à cuire »** — à brancher sur `catalogue_vente.suivi_cuisson_auto`
   et la chaîne du comparatif achats. La case à cocher doit être déplacée de `catalogue.html`
   (table `produits`, vide pour ces plats) vers le catalogue de vente.
2. **`refroidissement.js`** — même bascule que `cuisson.js` : il envoie encore l'ancien
   identifiant seul.
3. **Rattrapage depuis le 10/06** — `scripts/rattrapage_cuisson_refroidissement.py` joint
   encore `produits` et ne trouverait aucun candidat. À corriger avant tout lancement.
4. **Arbitrage produit** (décision métier, voir §6).

---

## 6. Décision qui t'appartient

La liaison vente ↔ achat est en place et exploitable :

```
catalogue_vente  --comparatif_groupe_vente-->  comparatif_groupe
                 --comparatif_groupe_ligne-->  catalogue_fournisseur
```

Tes plats cibles sont **tous déjà reliés** : Lasagnes (groupe #7), Gratin dauphinois (#12),
Parmentier canard (#8), Rosbeef cuit (#132, 14 articles d'achat).

Deux points bloquent la suite :

- **« Rosbeef cuit » existe en double** — id 106 (avec un double espace dans le nom) et id 114.
- **« Rosbeef cuit » et « Rosbeef cru » partagent le groupe #132.** Un lot reçu peut donc
  alimenter l'un ou l'autre : le déclencheur ne peut pas deviner lequel.

→ Soit on dédoublonne et on sépare les groupes, soit le système propose les deux et
l'opérateur choisit. À trancher avant de brancher la détection automatique.

---

## 7. Commandes utiles

**Audit complet** (lecture seule, ne modifie rien) :

```bash
cd ~/haccp-monitor && git pull && sudo systemctl restart haccp-backend && sleep 5 && python3 scripts/diag_rupture_reception_cuisson.py
```

> Le `sleep 5` laisse le backend démarrer : la migration s'applique **au lancement**, pas au
> `git pull`. Lancé trop tôt, l'audit annoncerait à tort que la migration n'est pas passée.

Le script constate l'état réel (schéma, données, code source) au lieu de le supposer, et
termine par un verdict listant ce qui reste à faire.

**En cas de migration non appliquée :**

```bash
journalctl -u haccp-backend --since "5 min ago" | grep -i "v7.4\|locked"
```

---

## 8. Note importante sur l'automatisation

La mesure de température à cœur (≥ 75 °C en cuisson, ≤ 10 °C en moins de 2 h) se fait à la
sonde, à la main. Il n'existe **aucun capteur connecté** sur ces étapes, contrairement aux
enceintes froides.

« Automatique » ne peut donc pas signifier « la température se remplit toute seule » — et
c'est souhaitable : ce geste de mesure *est* la preuve réglementaire. Un contrôle qu'un
logiciel remplirait seul n'aurait aucune valeur en cas d'audit.

Ce qui est automatisable, et qui constitue l'objectif : **le déclenchement, le chaînage entre
étapes, le pré-remplissage** (opérateur, produit, lot, DLC) **et les rappels de délai**.

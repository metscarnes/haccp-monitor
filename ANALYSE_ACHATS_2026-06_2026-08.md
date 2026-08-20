# Analyse achats/marge — période 10/06/2026 → 20/08/2026

**Statut : rattachement catalogue TERMINÉ (20/08/2026) — 99,4 % du montant récupéré.**
L'analyse achats par produit/famille sur la période est désormais fiable ; reliquat
assumé de 11 lignes / 237,16 € (0,6 %). Le bug de perte du lien à l'import OCR est
corrigé ET déployé (§7). Reste à mener : l'analyse achats elle-même.

---

## Contexte

Objectif initial : établir le volume d'achat réel (poids/valeur) par produit puis par
famille, à partir du module Facture (source la plus fiable pour poids/prix réels — plus
fiable que le module Réception, qui reflète l'estimation avant correction facture), en
vue d'une future analyse de marge (CA − CMV) sur la période démarrée le 10/06/2026.

Hypothèse retenue pour la marge : 5 % de pertes → 95 % du poids acheté est vendu.

---

## Ce qui a été fait

### 1. Vue macro fiable (CMV réel par variation de stock)

Sur la sous-période **28/06 → 29/07/2026** (32 jours, seule fenêtre bornée par deux
inventaires clôturés existants — id=1 au 28/06, id=4 au 29/07) :

| Indicateur | Valeur |
|---|---|
| Stock initial HT (28/06) | 5 825,33 € |
| Stock final HT (29/07) | 2 433,11 € |
| Achats HT sur la sous-période | 13 594,18 € |
| CA TTC sur la sous-période | 32 765,02 € |
| **CMV réel** (stock initial + achats − stock final) | **16 986,40 €** |
| **CA HT** (CA TTC / 1,055) | **≈ 31 057,84 €** |
| **Marge brute HT** | **≈ 14 071,44 €** |
| **Taux de marge / CA** | **≈ 45,3 %** |
| Coefficient multiplicateur (CA HT / CMV) | ≈ 1,83 |

Sur la période longue complète (10/06→20/08, 71 jours), sans variation de stock connue
aux deux bornes : CA TTC 76 156,72 € / Achats HT 43 843,68 €. Le taux de marge apparent
(~39,4 %) est **sous-estimé** par rapport au calcul CMV réel, car une partie des achats
de fin de période dormait encore en stock au 20/08.

→ **Pour affiner** : refaire un inventaire proche du 20/08/2026 permettrait un CMV
précis sur la quasi-totalité des ~3 mois de données.

### 2. Diagnostic du problème de rattachement catalogue (le vrai sujet de cette note)

Objectif dévié : au moment de vouloir classer les achats par produit fiable, on a
découvert que **le comparateur (`comparatif_groupe_ligne`) ne représente pas une
relation de transformation achat→produit vendu** (un article acheté peut être lié à
plusieurs produits vente sans rapport de recette réel — ex. Poulet Blanc Fermier lié à
la fois à Pintade, Poulet fermier ET Poulet roti). **Ce module est donc invalidé pour
une marge par article** — il sert uniquement à comparer des prix fournisseurs, pas à
mapper une recette de transformation.

En creusant le classement par désignation brute, on a découvert un problème plus grave :
**87 % de la valeur des achats facturés (38 244,62 € HT sur 43 843,68 €, soit 707
lignes sur 71 jours) n'avait aucun `catalogue_fournisseur_id` renseigné dans
`facture_lignes`**, alors que ces mêmes lignes provenaient de réceptions où le lien
catalogue était présent à 95 % (725/763 lignes de réception liées).

**Cause racine identifiée et confirmée par lecture de code** (`src/api/routes_achats.py`,
route `POST /factures/{id}/appliquer-import`) :

1. Tu clôtures une réception → facture brouillon auto-générée, lignes correctement
   liées au catalogue (`catalogue_fournisseur_id` + `reception_ligne_id` présents).
2. Tu importes ensuite la facture papier réelle via OCR (Claude vision / Factur-X) pour
   avoir les vrais prix/poids facturés — la bonne pratique, plus fiable que l'estimation
   réception.
3. `appliquer_import` avec `remplacer_lignes=True` fait un `DELETE FROM facture_lignes
   WHERE facture_id = ?` puis réinsère les lignes extraites par l'OCR.
4. **L'OCR ne connaît que le texte/code lus sur le papier, jamais l'ID interne
   `catalogue_fournisseur_id`** — donc les nouvelles lignes étaient insérées avec ce
   champ à `NULL`, perdant le lien qui existait avant le remplacement.

Ce n'était donc **pas** un problème de catalogue incomplet (le workflow catalogue →
commande → réception empêche structurellement de commander un article non catalogué,
comme confirmé par l'utilisateur), mais un vrai bug de perte de lien au remplacement.

### 3. Correctif de code (déployé)

- **Commit** `b520984` — `fix: préserver catalogue_fournisseur_id lors du remplacement
  de lignes facture (import OCR)`.
- Modification de `appliquer_import` (`src/api/routes_achats.py`) : avant le `DELETE`,
  sauvegarde d'une correspondance `code_article → (catalogue_fournisseur_id,
  reception_ligne_id)` depuis les anciennes lignes de la facture ; réinjection sur les
  nouvelles lignes OCR partageant le même `code_article`.
- Test ajouté : `test_appliquer_import_preserve_lien_catalogue`
  (`tests/test_factures_refonte_etape4.py`). Suite complète facture : **68/68 tests
  passent**, aucune régression.
- **Déployé sur le Pi** le 20/08/2026 (`git pull` → `696b60d`, restart
  `haccp-backend` confirmé actif).
- **Effet** : les futurs imports OCR de facture préserveront désormais le lien
  catalogue automatiquement. N'affecte pas les lignes déjà en base.

### 4. Rattrapage rétroactif — première passe (faite)

- **Sauvegarde préalable** : `backups/haccp_avant_rattrapage_catalogue_20260820_135630.db`
  (24,8 Mo) sur le Pi, avant toute écriture.
- **Script exécuté** : `UPDATE facture_lignes SET catalogue_fournisseur_id = ...` limité
  aux cas de correspondance **stricte et non ambiguë** : `code_article` de la ligne
  facture matchant exactement une fiche `catalogue_fournisseur` du **même fournisseur**
  (vérifié : aucun `code_article` en doublon chez un même fournisseur, donc aucun risque
  de mauvais rattachement).
- **Résultat** : **42 lignes rattachées** (2 111,33 € HT) — confirmé par `changes()`
  après exécution. Aucune ligne supprimée, aucun montant/poids modifié, uniquement le
  lien catalogue complété.

### 5. Cause racine du "code sans fiche catalogue" : padding des zéros (trouvée le 20/08/2026)

Le diagnostic initial "aucune fiche catalogue pour ce code" était une fausse piste. Les
tests menés le 20/08 ont montré :

- match sur code normalisé (espaces/tirets/points retirés), même fournisseur : **0 ligne** ;
- match sur code exact chez un autre fournisseur : **0 ligne** ;
- orphelines dont la facture est rattachée à une réception : **662 / 665** ;
- match par **désignation exacte** via la réception liée, candidat unique : **310 lignes**.

Exemple décisif : catalogue Elivia `07991-07` = "BATEAU PAD BOVIN L" ; ligne facture OCR
`7991-7` = "BATEAU PAD BOVIN L". **Même article, désignation identique, code différant
uniquement par les zéros de tête.**

Deux conventions de codage en cause :

| Fournisseur | Catalogue | Lu par l'OCR sur le papier |
|---|---|---|
| Elivia/Selvi | `0XXXXX-0Y` (zéros de tête sur les 2 segments) | `XXXXX-Y` |
| Saveur d'Antoine | `NNNN` (sans zéros) | `00NNNN` (avec zéros) |

Ce n'était donc ni un catalogue incomplet, ni une coquille OCR, mais une **différence de
format de code entre le catalogue et le papier fournisseur**.

### 6. Rattrapage rétroactif — deuxième passe via la réception (faite le 20/08/2026)

- **Sauvegarde préalable** : `backups/haccp_avant_rattrapage_via_reception_20260820_142502.db`
  (24 Mo) sur le Pi.
- **Critère de rattachement (double preuve, non ambigu)** : ligne facture orpheline dont
  la facture porte un `reception_id`, avec **un seul** article de cette réception dont la
  `designation` catalogue est identique (UPPER/TRIM) à celle de la ligne facture, **ET**
  dont le `code_article` est compatible une fois les zéros de tête retirés segment par
  segment.
- **Résultat** : **283 lignes rattachées (16 798,73 € HT)** — `changes()` = 283.
- `UPDATE` borné par `AND catalogue_fournisseur_id IS NULL` (impossible d'écraser un lien
  existant), colonne `catalogue_fournisseur_id` seule modifiée : aucun montant, poids ni
  libellé touché.

**État après cette passe : 382 lignes orphelines / 19 334,56 € HT** (contre 665 / 36 133 €).

### 7. Le correctif de code b520984 était INSUFFISANT — corrigé le 20/08/2026

Le correctif initial réappariait le lien catalogue par **`code_article` en égalité
stricte**. Or la cause racine découverte au §5 est justement que le code du papier n'est
jamais celui du catalogue chez les 2 principaux fournisseurs : **le réappariement ne
récupérait donc 0 ligne** sur Elivia et Saveur d'Antoine (test A : 0 match strict). Le
bug était corrigé sur le papier, pas dans les faits.

Efficacité réelle mesurée des critères, sur les données de prod :

| Critère | Lignes récupérées |
|---|---|
| `code_article` strict | **0** |
| code normalisé (zéros de tête) | 89 |
| **désignation exacte via la réception** | **310** |

`appliquer_import` (`src/api/routes_achats.py`) applique désormais les 3 critères en
cascade, du plus sûr au moins sûr : **code exact → code normalisé → désignation**.
Helper `_cles_code_article()` : deux normalisations (par segment pour `07991-07`↔`7991-7`,
et sans tiret pour `ART-01`↔`ART01`).

Garde-fou : si aucun critère ne correspond, le lien reste `NULL` — jamais de rattachement
au hasard (un faux lien fausserait l'analyse plus discrètement qu'une ligne orpheline).

Tests ajoutés (`tests/test_factures_refonte_etape4.py`) :
`test_appliquer_import_lien_catalogue_code_non_strict` (paramétré `0ART01` / `ART-01` /
` art01 `), `test_appliquer_import_lien_catalogue_par_designation`,
`test_appliquer_import_pas_de_lien_invente`. Suite facture : **73/73 passent**.

**À déployer sur le Pi** (non commité à ce stade).

### 8. Vérification par les PDF fournisseur (27 factures Elivia, 10/06→17/08)

Les PDF originaux (`OneDrive\Les lilas\fournisseur\Alimentaire\EliviaSelvi\Factures`)
confirment deux points :

- **La ligne « art8 » à 1 499,82 € n'est PAS un artefact OCR.** Facture 26481608 du
  10/08/2026 : `ART8 BOVIN / VBF / 26504-1 / 119,000 kg / 12,50 €/kg = 1 487,50 € HT`
  (+2,50 transport +9,82 taxes). C'est le vrai libellé Elivia, le candidat catalogue
  `26504-1` est le bon → rattachable sans risque.
- **Le suffixe du code Elivia n'est pas un identifiant produit stable** : le même article
  part sous plusieurs suffixes selon la livraison, à prix identique — TENDE TRANCHE
  `43549-1` et `43549-2` (13,65 €/kg dans les deux cas), AGNEAU ENTIER `2802-4` et
  `2802-1`, RUMSTECK `7983-1` et `7983-2`, TRAVERS `79111-4` et `79111-2`, LONGE
  `76803-4`/`76803-2`, BARDE `70297-5`/`70297-1`, CARRE FILET `26501-3`/`26501-1`,
  MLTC `43514-1`/`43514-3`. Rattacher `43549-1` à la fiche `43549-02` est donc **correct
  au niveau produit** — la réserve du §"passe 2" est levée.

### 9. Rattrapage — passe 3 par code normalisé (faite le 20/08/2026)

- **Sauvegarde** : `backups/haccp_avant_passe3_code_normalise_20260820_150453.db`.
- **Critère** : ligne orpheline de type `marchandise` avec un `code_article`, rattachée à
  la fiche `catalogue_fournisseur` du **même fournisseur** dont le code est identique
  après neutralisation des séparateurs et des zéros de tête (les deux normalisations du
  helper `_cles_code_article`), **candidat unique** exigé.
- Aperçu vérifié avant écriture : padding de zéros systématique côté Saveur d'Antoine
  (`001004`↔`1004`, `019423`↔`19423`, `000071`↔`71`), désignations concordantes ; 3 paires
  à libellé différent contrôlées et validées (`002910` 10 FLT POULET BLANC IGP ↔ `2910`
  Filet poulet Gretel IGP ; `004000` FILET DE DINDE S/VID ↔ `4000` Filet Dinde S/V ;
  `000291` Rillette canard TG 2KG ↔ `291` Rillette canard).
- **Résultat** : **182 lignes rattachées (7 296,10 € HT)**.

### 10. Rattrapage — passe 4 par racine de code (faite le 20/08/2026)

- **Sauvegarde** : `backups/haccp_avant_passe4_racine_code_20260820_151015.db`.
- **Motif** : le catalogue Elivia ne compte que **42 fiches** alors que les PDF montrent
  bien plus de références achetées → catalogue partiel. Mais plusieurs articles y étaient
  bien présents, sous un **suffixe différent** seulement (`43514-1` facturé vs `43514-01`
  au catalogue). La requête SQL de la passe 3 était plus faible que le helper Python
  déployé : son `LTRIM(code,'0')` s'applique à la chaîne entière, pas segment par segment,
  donc `43514-01` et `43514-1` n'y étaient pas reconnus égaux.
- **Critère** : appariement sur la **racine du code** (partie avant le tiret, zéros
  neutralisés), même fournisseur, candidat unique — légitime car les PDF ont établi que
  le suffixe Elivia n'est pas un identifiant produit stable (§8).
- Les 15 paires ont été contrôlées une par une avant écriture ; désignations concordantes
  partout, y compris les variantes d'écriture (`FRANÇAIS`/`FRANCAIS`, `PALERON SP BOVIN
  SV`/`SY` — coquille catalogue, `FOIE EXTRA VEAU NSV`/`Foie de veau`).
- **Résultat** : **29 lignes rattachées (4 611,40 € HT)**.

### 11. Prévention : plus aucune ligne orpheline ne doit se créer (20/08/2026)

Le rattrapage règle le passé ; il fallait fermer les robinets. Cartographie des chemins
qui créent une ligne de facture, et état de chacun **avant** :

| Chemin | Lien catalogue | Risque |
|---|---|---|
| clôture réception → facture auto | copié de la réception | nul |
| import OCR / Factur-X | cascade (§7) | résiduel |
| `POST /factures` (saisie manuelle) | ce que le front envoie | **non protégé** |
| `POST /factures/{id}/lignes` | ce que le front envoie | **non protégé** |
| `solder-ecart` / `avoir-depuis-litiges` | NULL volontaire | nul (annexes) |

**Choix retenu : assistance, PAS blocage.** Un blocage dur aurait cassé trois usages
légitimes : les annexes (transport/taxe n'ont aucun article), `solder-ecart` (crée exprès
une ligne d'ajustement), et surtout la saisie d'un article hors catalogue en pleine
réception — bouchon inacceptable à 6 h du matin.

1. **Rattrapage serveur avant insertion** (`_resoudre_lien_catalogue`) sur les chemins
   manuels et l'import : cascade code exact → code normalisé → racine → désignation,
   candidat **unique** exigé à chaque niveau, sinon NULL.
2. **Seul blocage ajouté** (`_verifier_coherence_catalogue`, 422) : article catalogue
   appartenant à un AUTRE fournisseur que la facture — incohérence jamais légitime, qui
   imputerait l'achat au mauvais fournisseur. Rien ne l'empêchait auparavant.
3. **Suggestions classées** (`_suggerer_articles_catalogue`) : similarité de libellé
   (Jaccard, accents neutralisés → `FRANÇAIS` trouve `FRANCAIS`) + bonus de **fréquence
   de réception sur 6 mois glissants** + bonus fort si racine de code commune. Fondement :
   « on commande toujours la même chose », donc l'article reçu 18 fois passe devant celui
   reçu une fois. La fréquence vient des RÉCEPTIONS (95 % ont le lien, non affectées par
   le bug facture).

**Endpoints** : `GET /factures/{id}/lignes-non-rattachees` (lignes + suggestions +
montant), `GET /catalogue/recherche?fournisseur_id=&q=` (recherche libre, les plus reçus
en tête ; déclarée AVANT `/catalogue/{article_id}` sinon FastAPI la capture).
`FactureLigneUpdate` accepte désormais `catalogue_fournisseur_id` (rattachement manuel).

**Écran** (`factures-achats.html`) : bandeau bleu dans la modale facture listant les
lignes non rattachées avec leur montant, bouton « Rattacher… » par ligne ouvrant une
modale (suggestions d'abord, recherche libre ensuite). Masqué sur facture validée
(verrouillée) : le constat reste visible pour l'audit, l'action est retirée.

Tests : `tests/test_factures_rattachement_catalogue.py` — 13 tests (rattachement sur les
4 formats de code réels, par désignation, non-blocage d'un article inconnu, annexes
jamais rattachées, refus inter-fournisseur, classement des suggestions, priorisation par
fréquence, rattachement manuel). **110/110 sur tout le périmètre achats.**

### 12. Intégrité des sauvegardes — vérifiée le 20/08/2026

`PRAGMA integrity_check` = `ok` sur les 5 sauvegardes, et le nombre d'orphelines de chacune
correspond exactement à l'état attendu au moment de sa création :

| Heure | Sauvegarde | Orphelines |
|---|---|---|
| 13:56 | `haccp_avant_rattrapage_catalogue_20260820_135630.db` | 707 |
| 14:25 | `haccp_avant_rattrapage_via_reception_20260820_142502.db` | 665 |
| 14:42 | `haccp_avant_passe2_suffixes_20260820_144226.db` | 382 |
| 15:01 | `haccp_avant_passe2_suffixes_20260820_150156.db` | 355 |
| 15:04 | `haccp_avant_passe3_code_normalise_20260820_150453.db` | 355 |
| 15:10 | `haccp_avant_passe4_racine_code_20260820_151015.db` | 173 |
| — | base actuelle | **144** |

Point de retour disponible à chaque étape. (Piège à éviter : `ls | tail` trie par ordre
**alphabétique** — utiliser `ls -lht` pour un tri chronologique réel.)

---

## Bilan du rattrapage

| Étape | Lignes | Montant HT |
|---|---|---|
| Départ | 707 | 38 244,62 € |
| Code strict (§4) | −42 | −2 111,33 € |
| Via réception, passes 1+2 (§6) | −310 | −21 754,16 € |
| Code normalisé, passe 3 (§9) | −182 | −7 296,10 € |
| Racine de code, passe 4 (§10) | −29 | −4 611,40 € |
| Cuisses Bourdicaud, rattachement manuel (§13) | −3 | −130,85 € |
| Fiches catalogue créées puis rattachées, passe 5 (§13) | −3 | −1 830,05 € |
| **Reste marchandise** | **11** | **237,16 €** |

**99,4 % du montant orphelin récupéré**, sans aucun rattachement douteux.
→ **Le rattrapage est terminé.** L'analyse achats par produit/famille est exploitable.

### 13. Fin du rattrapage — fiches manquantes (20/08/2026)

Le reliquat de la passe 4 était constitué d'articles **réellement achetés mais absents du
catalogue** (Elivia n'avait que 42 fiches pour bien plus de références facturées).

- **Cuisses Bourdicaud** (lignes 727, 882, 1298 — `025201`, 3 × 8,95 €/kg, 130,85 €) :
  rattachées manuellement à la fiche existante **id 2432** (code article `2480`, « Cuisse
  Poulet Blanc Fermier Label Rouge IDF », 8,95 €/kg — prix catalogue identique au prix
  facturé). ⚠️ Piège évité : l'ID interne 2480 correspond à une tout autre fiche (« Filet
  Pintade Sans/Peau S/V », 20 €, inactive) — ne pas confondre `code_article` et `id`.
- **Fiches créées par l'utilisateur** puis rattachées par la même règle que la passe 4 :
  `47049-02` PAN EPAULE PAD VEAU PCA (id 3194, 2 lignes, 1 685,75 €) et `81109-08` COTE
  BOVIN S/V (id 3195, 1 ligne, 144,30 €). Prix relevés sur les PDF : 13,75 €/kg et
  19,50 €/kg.

---

## À FAIRE

### Reliquat accepté : 11 lignes marchandise / 237,16 € (0,6 %)

Non bloquant. Composition : 3 lignes à 0,00 € (TARTARE DE TOMATES, 2 Fuet catalan),
2 petites lignes Saveur d'Antoine (48 €), filets mignons Elivia (`76548-5`/`76548-1`,
`70451-2`), `43662-2` ONGLET SP X2, `43471-1` GORGE S/COUENNE. À traiter seulement si de
nouvelles fiches catalogue sont créées pour ces références.

### Point de vigilance : prestations comptées en marchandise

`PREST DESOSSAGE VX PAD` (`99864-01`) est rattachée mais porte `type_ligne='marchandise'`
alors que c'est une **prestation de service** — elle gonfle artificiellement le volume
d'achat produit. À reclasser avant une analyse fine par produit.

Les 127 autres lignes orphelines (taxe 102, transport 20, remise 4, ajustement 1 — soit
≈ 274 € net) **n'ont pas vocation à être rattachées** : ce sont des annexes de facture
(Transport, INTERBEV, REDEVANCE SANITAIRE DE DECOUPE, CVO/CSE INAPORC, PREST DESOSSAGE)
qui n'ont légitimement aucun article catalogue. À exclure du dénominateur, pas à réparer.

Pour les 46 marchandises restantes (sans `code_article` exploitable, ou à candidats
multiples) : rattrapage par **désignation normalisée** (accents compris — la base contient
`AGNEAU ENTIER FRANCAIS U` et `AGNEAU ENTIER FRANÇAIS U`, `10 FLT POULET BLANC IGP` et
`10 FLT POULET BLANC IGP - Né, élevé, abattu...`), avec validation ligne par ligne.

### Déploiement en attente

Le correctif du §7 (cascade code exact → code normalisé → désignation) est **déployé sur
le Pi** (`ade39b7`, restart confirmé). Sa validation réelle viendra du prochain import OCR
de facture : vérifier alors que les lignes gardent leur `catalogue_fournisseur_id`.

**Sous-question à trancher en premier** : comme le workflow (catalogue → commande →
réception) garantit que l'article existe forcément au catalogue au moment de la
commande, ces 536 lignes avec un `code_article` "sans fiche" sont suspectes — il faut
vérifier si le vrai problème n'est pas plutôt :
- un `code_article` mal extrait par l'OCR sur le papier (chiffre inversé, caractère
  manquant) qui ne matche donc pas le vrai code existant ;
- des factures dont la réception d'origine remonte à **avant** le 10/06/2026 (hors
  fenêtre d'analyse) et dont le catalogue de l'époque a changé depuis ;
- des lignes de factures **jamais rattachées à aucune réception** (`reception_id IS
  NULL` sur la facture — création manuelle ou import sans réception source) : dans ce
  cas il n'existe nulle part de `reception_ligne_id` à retrouver, donc pas de
  raccourci possible, il faut une autre méthode de rapprochement.

**Pistes de résolution, à explorer dans cet ordre** :

1. **Réappariement par désignation + fournisseur** plutôt que par code strict — score
   de similarité texte entre `facture_lignes.designation` et
   `catalogue_fournisseur.designation` pour le même fournisseur, avec un seuil
   suffisamment strict pour éviter les faux positifs (à valider ligne par ligne avant
   tout `UPDATE` en masse, contrairement au rattrapage par code qui était non ambigu).
2. **Remonter via `reception_id` de la facture** (même si `reception_ligne_id` a été
   perdu sur la ligne facture) : retrouver les lignes de la réception d'origine de la
   facture et les rapprocher par désignation/poids/prix pour reconstituer le lien.
3. **Vérifier les codes_article mal OCRisés** : comparer chaque `code_article` orphelin
   à la liste des vrais codes du fournisseur pour repérer des quasi-doublons
   (distance d'édition faible → coquille OCR probable), à valider manuellement avant
   correction.
4. **Pour les 129 lignes sans code du tout** : uniquement une correspondance par
   désignation + fournisseur + montant/poids approximatif, à valider une par une
   (trop peu fiable pour un script automatique en masse).

**Important : contrairement au rattrapage des 42 lignes (critère non ambigu, `UPDATE`
en une passe), toute correction sur les 665 lignes restantes nécessitera un examen plus
fin avant d'écrire en base — refaire une sauvegarde avant toute nouvelle passe
d'écriture, et valider un échantillon avant un `UPDATE` en masse.**

### Une fois les 665 lignes traitées (ou un maximum réparé)

- Reprendre l'analyse achats par produit / famille / fournisseur sur la base
  `facture_lignes.catalogue_fournisseur_id` désormais fiable.
- Croiser avec le catalogue vente pour une vraie marge par produit — **mais pas via
  `comparatif_groupe_ligne`** (invalidé, voir ci-dessus) : il faudra soit une vraie
  table de recette/transformation achat→vente (n'existe pas actuellement), soit se
  limiter à une marge par famille (bœuf/porc/veau/agneau/volaille/charcuterie/traiteur),
  qui elle ne dépend pas d'un mapping fin par article.
- Envisager un inventaire proche de la date du jour pour un CMV réel sur la quasi-
  totalité des 3 mois plutôt que sur les 32 jours actuellement couverts.

---

## Requêtes de référence (à relancer en l'état pour un état des lieux rapide)

```sql
-- Nombre de lignes encore orphelines et montant associé
SELECT COUNT(*) AS nb, ROUND(SUM(montant_facture_ht),2) AS montant_ht
FROM facture_lignes
WHERE catalogue_fournisseur_id IS NULL;
```

```sql
-- Répartition des orphelines par cause (code présent sans fiche / code absent)
SELECT
  SUM(CASE WHEN code_article IS NULL OR code_article = '' THEN 1 ELSE 0 END) AS sans_code,
  SUM(CASE WHEN code_article IS NOT NULL AND code_article != '' THEN 1 ELSE 0 END) AS avec_code_orphelin
FROM facture_lignes
WHERE catalogue_fournisseur_id IS NULL;
```

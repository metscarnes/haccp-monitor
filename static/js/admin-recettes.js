'use strict';

// ─────────────────────────────────────────────────────────────
//  État interne
// ─────────────────────────────────────────────────────────────
let produits     = [];   // liste complète chargée depuis /api/produits
let ingredients  = [];   // { id?, produit_id|null, nom, quantite, unite }
let recetteId    = null; // null = création, integer = édition

// ─────────────────────────────────────────────────────────────
//  Utilitaires DOM
// ─────────────────────────────────────────────────────────────
function $(id) { return document.getElementById(id); }

function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ─────────────────────────────────────────────────────────────
//  Chargement des produits
// ─────────────────────────────────────────────────────────────
async function loadProduits() {
  try {
    const res = await fetch('/api/produits');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    produits = await res.json();
  } catch (err) {
    console.error('Impossible de charger les produits :', err);
    showErreur('Impossible de charger la liste des produits. Vérifiez la connexion au serveur.');
  }
}

// ─────────────────────────────────────────────────────────────
//  Autocomplete générique (produit fini — sélection obligatoire)
//  options : { inputEl, listeEl, tagEl, tagNomEl, clearEl, hiddenEl, onSelect }
// ─────────────────────────────────────────────────────────────
function initAutocomplete({ inputEl, listeEl, tagEl, tagNomEl, clearEl, hiddenEl, onSelect }) {

  inputEl.addEventListener('input', () => {
    const q = inputEl.value.trim().toLowerCase();
    if (!q) { listeEl.hidden = true; return; }

    const matches = produits.filter(p =>
      (p.nom || '').toLowerCase().includes(q) ||
      (p.code || '').toLowerCase().includes(q)
    ).slice(0, 10);

    listeEl.innerHTML = '';
    if (matches.length === 0) { listeEl.hidden = true; return; }

    matches.forEach(p => {
      const opt = document.createElement('div');
      opt.className = 'ar-autocomplete-option';
      opt.setAttribute('role', 'option');
      opt.textContent = p.nom + (p.code ? ` (${p.code})` : '');
      opt.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        selectProduit(p, { inputEl, listeEl, tagEl, tagNomEl, hiddenEl });
        if (onSelect) onSelect(p);
      });
      listeEl.appendChild(opt);
    });
    listeEl.hidden = false;
  });

  inputEl.addEventListener('blur', () => {
    setTimeout(() => { listeEl.hidden = true; }, 150);
  });

  if (clearEl) {
    clearEl.addEventListener('click', () => {
      clearSelection({ inputEl, listeEl, tagEl, hiddenEl });
      if (onSelect) onSelect(null);
    });
  }
}

function selectProduit(p, { inputEl, listeEl, tagEl, tagNomEl, hiddenEl }) {
  hiddenEl.value = p.id;
  tagNomEl.textContent = p.nom + (p.code ? ` (${p.code})` : '');
  tagEl.hidden = false;
  inputEl.value = '';
  inputEl.hidden = true;
  listeEl.hidden = true;
}

function clearSelection({ inputEl, listeEl, tagEl, hiddenEl }) {
  hiddenEl.value = '';
  tagEl.hidden = true;
  inputEl.hidden = false;
  inputEl.value = '';
  inputEl.focus();
  listeEl.hidden = true;
}

// ─────────────────────────────────────────────────────────────
//  Autocomplete ingrédient — saisie libre autorisée
// ─────────────────────────────────────────────────────────────
function initIngrAutocomplete() {
  const inputEl  = $('ar-ingr-produit');
  const listeEl  = $('ar-ingr-produit-liste');
  const hiddenEl = $('ar-ingr-produit-id');
  const hintEl   = $('ar-ingr-hint');

  function updateHint() {
    // Hint visible uniquement si du texte est saisi mais sans ID (= ingrédient libre)
    hintEl.hidden = !inputEl.value.trim() || !!hiddenEl.value;
  }

  inputEl.addEventListener('input', () => {
    // Toute frappe manuelle efface l'ID stocké (retour en mode libre)
    hiddenEl.value = '';
    updateHint();

    const q = inputEl.value.trim().toLowerCase();
    if (!q) { listeEl.hidden = true; return; }

    const matches = produits.filter(p =>
      (p.nom || '').toLowerCase().includes(q) ||
      (p.code || '').toLowerCase().includes(q)
    ).slice(0, 10);

    listeEl.innerHTML = '';
    if (matches.length === 0) { listeEl.hidden = true; return; }

    matches.forEach(p => {
      const opt = document.createElement('div');
      opt.className = 'ar-autocomplete-option';
      opt.setAttribute('role', 'option');
      opt.textContent = p.nom + (p.code ? ` (${p.code})` : '');
      opt.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        // Sélection depuis l'autocomplete : on stocke l'ID et le nom propre
        inputEl.value  = p.nom;
        hiddenEl.value = p.id;
        listeEl.hidden = true;
        updateHint();
      });
      listeEl.appendChild(opt);
    });
    listeEl.hidden = false;
  });

  inputEl.addEventListener('blur', () => {
    setTimeout(() => { listeEl.hidden = true; }, 150);
  });
}

// ─────────────────────────────────────────────────────────────
//  Sélection du produit fini — auto-fill DLC + affichage détails
// ─────────────────────────────────────────────────────────────
function onProduitFiniSelect(p) {
  const details  = $('produit-details');

  if (!p) {
    details.hidden    = true;
    details.innerHTML = '';
    return;
  }

  // DLC recette verrouillée à 3 jours — pas d'auto-fill depuis le produit fini.

  const nomRecetteInput = $('ar-nom-recette');
  if (!nomRecetteInput.value.trim()) nomRecetteInput.value = p.nom;

  const rows = [
    { label: 'Catégorie',   val: p.categorie               },
    { label: 'Destination', val: p.destination             },
    { label: 'Température', val: p.temperature_conservation },
  ];

  details.innerHTML = rows.map(r => `
    <div class="ar-produit-details-row">
      <span class="ar-produit-details-label">${escHtml(r.label)}</span>
      <span class="ar-produit-details-val">${escHtml(r.val || '—')}</span>
    </div>
  `).join('');

  details.hidden = false;
}

// ─────────────────────────────────────────────────────────────
//  Calcul des proportions par groupe d'unité
// ─────────────────────────────────────────────────────────────
const FACTEURS_KG = { kg: 1, L: 1, g: 0.001, ml: 0.001, mL: 0.001 };

function calcProportions(list) {
  const enKg = ing => ing.quantite * (FACTEURS_KG[ing.unite] ?? null);

  const totalKg = list.reduce((sum, ing) => {
    const v = enKg(ing);
    return sum + (v !== null ? v : 0);
  }, 0);

  return list.map(ing => {
    const v = enKg(ing);
    if (v === null || totalKg === 0) return '—';
    return (v / totalKg * 100).toFixed(1);
  });
}

// ─────────────────────────────────────────────────────────────
//  Rendu du tableau des ingrédients
// ─────────────────────────────────────────────────────────────
function renderIngredients() {
  const tbody = $('ar-ingredients-tbody');
  const vide  = $('ar-ingredients-vide');
  const wrap  = $('ar-table-wrap');

  if (ingredients.length === 0) {
    wrap.hidden  = true;
    vide.hidden  = false;
    return;
  }

  vide.hidden = true;
  wrap.hidden = false;

  const proportions = calcProportions(ingredients);
  tbody.innerHTML   = '';

  ingredients.forEach((ing, idx) => {
    const tr = document.createElement('tr');
    const badgeNouv = ing.produit_id === null
      ? ' <span class="ar-badge-nouveau">nouveau</span>'
      : '';
    tr.className = 'ar-tr-clickable';
    tr.setAttribute('role', 'button');
    tr.setAttribute('tabindex', '0');
    tr.setAttribute('aria-label', `Modifier ${ing.nom}`);
    tr.innerHTML = `
      <td class="ar-td-nom">${escHtml(ing.nom)}${badgeNouv}</td>
      <td class="ar-td-qte">${escHtml(String(ing.quantite))}</td>
      <td class="ar-td-unite">${escHtml(ing.unite)}</td>
      <td class="ar-td-prop">${escHtml(String(proportions[idx]))}%</td>
      <td class="ar-td-action">
        <button type="button" class="ar-btn-suppr" aria-label="Supprimer ${escHtml(ing.nom)}">✕</button>
      </td>
    `;
    tr.querySelector('.ar-btn-suppr').addEventListener('click', (e) => {
      e.stopPropagation();
      ingredients.splice(idx, 1);
      renderIngredients();
    });
    tr.addEventListener('click', () => ouvrirModalEditIngredient(idx));
    tr.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        ouvrirModalEditIngredient(idx);
      }
    });
    tbody.appendChild(tr);
  });
}

// ─────────────────────────────────────────────────────────────
//  Modale — Modifier un ingrédient existant (qty + unité)
// ─────────────────────────────────────────────────────────────
let _editIdx = null;

const UNITES_DISPO = ['kg', 'g', 'L', 'ml', 'mL', 'pièce', 'pièces'];

function ouvrirModalEditIngredient(idx) {
  const ing = ingredients[idx];
  if (!ing) return;
  _editIdx = idx;

  $('ar-modal-edit-nom').value = ing.nom;
  $('ar-modal-edit-qte').value = ing.quantite ?? '';

  // Garantir que l'unité actuelle existe dans le <select>
  const selectUnite = $('ar-modal-edit-unite');
  const valeurs = Array.from(selectUnite.options).map(o => o.value);
  if (ing.unite && !valeurs.includes(ing.unite)) {
    const opt = document.createElement('option');
    opt.value = ing.unite;
    opt.textContent = ing.unite;
    selectUnite.appendChild(opt);
  }
  selectUnite.value = ing.unite || 'g';

  $('ar-modal-edit-overlay').hidden = false;
  setTimeout(() => $('ar-modal-edit-qte').focus(), 50);
}

function fermerModalEditIngredient() {
  $('ar-modal-edit-overlay').hidden = true;
  _editIdx = null;
}

function confirmerEditIngredient() {
  if (_editIdx === null) return;
  const qte   = parseFloat($('ar-modal-edit-qte').value);
  const unite = $('ar-modal-edit-unite').value;

  if (!qte || qte <= 0) {
    flashErreurChamp($('ar-modal-edit-qte'), 'Saisissez une quantité valide.');
    return;
  }

  ingredients[_editIdx].quantite = qte;
  ingredients[_editIdx].unite    = unite;
  fermerModalEditIngredient();
  renderIngredients();
}

// ─────────────────────────────────────────────────────────────
//  Mode édition : chargement d'une recette existante
// ─────────────────────────────────────────────────────────────
async function chargerRecettePourEdition(id) {
  try {
    const res = await fetch(`/api/recettes/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const recette = await res.json();

    recetteId = recette.id;

    // En-tête + bouton submit
    const titreEl = document.querySelector('.ar-header-titre');
    if (titreEl) titreEl.textContent = `Modifier : ${recette.nom}`;
    document.title = `Modifier ${recette.nom} — HACCP Monitor`;
    const btnSubmit = $('ar-btn-submit');
    btnSubmit.textContent = '✓ Mettre à jour la recette';

    // Champs principaux (la DLC est verrouillée à 3 — on ignore l'historique)
    $('ar-nom-recette').value = recette.nom || '';
    $('ar-dlc-jours').value   = '3';

    // Préfixe rendement extrait des instructions ("Base pour X unite.\n\n…")
    const m = (recette.instructions || '').match(/^Base pour\s+([\d.,]+)\s+(kg|L|pi[èe]ces?)\b/i);
    if (m) {
      $('ar-rendement-qte').value = m[1].replace(',', '.');
      const u = m[2].toLowerCase();
      $('ar-rendement-unite').value = u.startsWith('pi') ? 'pièces' : (u === 'l' ? 'L' : 'kg');
    }

    // Produit fini (sélectionné via tag)
    const produitFini = produits.find(p => p.id === recette.produit_fini_id);
    if (produitFini) {
      selectProduit(produitFini, {
        inputEl:  $('ar-produit-fini'),
        listeEl:  $('ar-produit-fini-liste'),
        tagEl:    $('ar-produit-fini-tag'),
        tagNomEl: $('ar-produit-fini-tag-nom'),
        hiddenEl: $('ar-produit-fini-id'),
      });
      onProduitFiniSelect(produitFini);
      // onProduitFiniSelect peut écraser le nom : on le remet (DLC reste verrouillée à 3)
      $('ar-nom-recette').value = recette.nom || '';
      $('ar-dlc-jours').value   = '3';
    }

    // Ingrédients existants (avec leur id BDD pour le diff côté serveur)
    ingredients = (recette.ingredients || []).map(ing => ({
      id:         ing.id,
      produit_id: ing.produit_id,
      nom:        ing.produit_nom,
      quantite:   ing.quantite,
      unite:      ing.unite,
    }));
    renderIngredients();
  } catch (err) {
    console.error('Chargement recette pour édition :', err);
    showErreur(`Impossible de charger la recette : ${err.message}`);
  }
}

// ─────────────────────────────────────────────────────────────
//  Modale — Nouvel ingrédient libre
// ─────────────────────────────────────────────────────────────
let _pendingIngredient = null; // { nom, quantite, unite } en attente de confirmation

// Mapping espèce → préfixe de code_unique (+ variante abats si définie)
const PREFIXES_ESPECE = {
  bovin:          { normal: 'VB',    abats: 'VBA'   },
  veau:           { normal: 'VX',    abats: 'VXAB'  },
  agneau:         { normal: 'AGN',   abats: 'AGNAB' },
  porc:           { normal: 'PC',    abats: 'PACAB' },
  gibier:         { normal: 'GIB',   abats: null    },
  canard:         { normal: 'VC',    abats: null    },
  dinde:          { normal: 'VD',    abats: null    },
  lapin:          { normal: 'VL',    abats: null    },
  volaille_autre: { normal: 'VP',    abats: null    },
  cheval:         { normal: 'CH',    abats: null    },
  exotique:       { normal: 'VEXOA', abats: null    },
};

function prefixePourCode(espece, abats) {
  const m = PREFIXES_ESPECE[espece];
  if (!m) return null;
  return (abats && m.abats) ? m.abats : m.normal;
}

function prochainCodeUnique(prefixe) {
  // Cherche le plus grand suffixe numérique parmi les codes existants
  // de la forme PREFIXE + chiffres uniquement (ex : PC + 31, pas PC + 30A).
  const re = new RegExp(`^${prefixe}(\\d+)$`);
  let max = 0;
  for (const p of produits) {
    const code = (p.code_unique || '').toUpperCase();
    const m = code.match(re);
    if (m) {
      const n = parseInt(m[1], 10);
      if (n > max) max = n;
    }
  }
  return `${prefixe}${max + 1}`;
}

function rafraichirCodePreview() {
  const espece = $('ar-modal-espece').value;
  const abats  = $('ar-modal-abats').checked;
  const codeEl = $('ar-modal-code');
  const prefixe = prefixePourCode(espece, abats);
  if (!prefixe) {
    codeEl.value = '';
    codeEl.placeholder = 'sélectionnez une espèce…';
    return;
  }
  codeEl.value = prochainCodeUnique(prefixe);
}

function ouvrirModalNouvelIngredient(nom, quantite, unite) {
  _pendingIngredient = { nom, quantite, unite };
  $('ar-modal-nom').value        = nom;
  $('ar-modal-categorie').value  = 'matiere_premiere';
  $('ar-modal-espece').value     = '';
  $('ar-modal-abats').checked    = false;
  $('ar-modal-coupe').value      = '';
  $('ar-modal-etape').value      = '';
  $('ar-modal-cond').value       = 'SOUS_VIDE';
  $('ar-modal-type').value       = 'brut';
  $('ar-modal-dlc').value        = '0';
  $('ar-modal-temp').value       = 'Ambiant';
  rafraichirCodePreview();
  $('ar-modal-overlay').hidden   = false;
  $('ar-modal-espece').focus();
}

function fermerModal() {
  $('ar-modal-overlay').hidden = true;
  _pendingIngredient = null;
}

function confirmerNouvelIngredient() {
  if (!_pendingIngredient) return;

  const espece = $('ar-modal-espece').value;
  if (!espece) {
    flashErreurChamp($('ar-modal-espece'), 'Sélectionnez une espèce.');
    return;
  }

  const dlcVal   = parseInt($('ar-modal-dlc').value);
  const etapeVal = parseInt($('ar-modal-etape').value);

  ingredients.push({
    produit_id:               null,
    nom:                      _pendingIngredient.nom,
    quantite:                 _pendingIngredient.quantite,
    unite:                    _pendingIngredient.unite,
    // Champs pour la création BDD (POST /api/produits)
    categorie:                $('ar-modal-categorie').value,
    espece:                   espece,
    abats:                    $('ar-modal-abats').checked,
    coupe_niveau:             $('ar-modal-coupe').value.trim() || null,
    etape:                    isNaN(etapeVal) ? null : etapeVal,
    conditionnement:          $('ar-modal-cond').value,
    type_produit:             $('ar-modal-type').value,
    dlc_jours:                isNaN(dlcVal) ? 0 : dlcVal,
    temperature_conservation: $('ar-modal-temp').value,
  });

  fermerModal();
  renderIngredients();
  resetBlocAjout();
}

// ─────────────────────────────────────────────────────────────
//  Ajout d'un ingrédient (saisie libre ou sélection autocomplete)
// ─────────────────────────────────────────────────────────────
function ajouterIngredient() {
  const produitId = $('ar-ingr-produit-id').value;
  const nomSaisi  = $('ar-ingr-produit').value.trim();
  const qte       = parseFloat($('ar-ingr-qte').value);
  const unite     = $('ar-ingr-unite').value;

  if (!nomSaisi) {
    flashErreurChamp($('ar-ingr-produit'), 'Saisissez un nom d\'ingrédient.');
    return;
  }
  if (!qte || qte <= 0) {
    flashErreurChamp($('ar-ingr-qte'), 'Saisissez une quantité valide.');
    return;
  }

  if (produitId) {
    // Produit existant — ajout direct
    const nomFinal = produits.find(p => p.id === parseInt(produitId))?.nom || nomSaisi;
    ingredients.push({ produit_id: parseInt(produitId), nom: nomFinal, quantite: qte, unite });
    renderIngredients();
    resetBlocAjout();
  } else {
    // Ingrédient libre — ouvrir la modale de complétion
    ouvrirModalNouvelIngredient(nomSaisi, qte, unite);
  }
}

function resetBlocAjout() {
  $('ar-ingr-produit').value    = '';
  $('ar-ingr-produit-id').value = '';
  $('ar-ingr-hint').hidden      = true;
  $('ar-ingr-qte').value        = '';
  $('ar-ingr-unite').value      = 'g';
  $('ar-ingr-produit').focus();
}

// ─────────────────────────────────────────────────────────────
//  Enregistrement de la recette
// ─────────────────────────────────────────────────────────────
async function enregistrerRecette() {
  hideErreur();

  const nom       = $('ar-nom-recette').value.trim();
  const produitId = $('ar-produit-fini-id').value;
  const dlcJours  = 3; // DLC recette verrouillée à 3 jours

  if (!nom) {
    showErreur('Le nom de la recette est obligatoire.');
    $('ar-nom-recette').focus();
    return;
  }
  if (!produitId) {
    showErreur('Sélectionnez un produit fini associé.');
    return;
  }
  if (ingredients.length === 0) {
    showErreur('Ajoutez au moins un ingrédient avant d\'enregistrer.');
    return;
  }

  // Préfixe rendement → instructions
  const rendQte   = parseFloat($('ar-rendement-qte').value);
  const rendUnite = $('ar-rendement-unite').value;
  const instructionsPrefix = rendQte && rendQte > 0
    ? `Base pour ${rendQte} ${rendUnite}.\n\n`
    : '';

  const btn = $('ar-btn-submit');
  const enEdition = recetteId !== null;
  const labelInitial = enEdition ? '✓ Mettre à jour la recette' : '✓ Enregistrer la recette';
  btn.disabled    = true;
  btn.textContent = enEdition ? 'Mise à jour…' : 'Enregistrement…';

  try {
    // ── Étape 1 : créer silencieusement les ingrédients libres ──
    for (const ing of ingredients) {
      if (ing.produit_id === null) {
        // Régénère le code juste avant POST (au cas où d'autres produits ont été
        // créés entre l'ouverture de la modale et la sauvegarde de la recette).
        const prefixe   = prefixePourCode(ing.espece, ing.abats);
        const codeFinal = prefixe ? prochainCodeUnique(prefixe) : null;

        const payload = {
          nom:                      ing.nom,
          code_unique:              codeFinal,
          categorie:                ing.categorie                || 'matiere_premiere',
          espece:                   ing.espece                   || null,
          coupe_niveau:             ing.coupe_niveau             || null,
          etape:                    ing.etape                    ?? null,
          conditionnement:          ing.conditionnement          || 'SOUS_VIDE',
          type_produit:             ing.type_produit             || 'brut',
          dlc_jours:                ing.dlc_jours                ?? 0,
          temperature_conservation: ing.temperature_conservation || 'Ambiant',
        };
        // Nettoie les null (l'API accepte exclude_none côté Pydantic)
        Object.keys(payload).forEach(k => payload[k] == null && delete payload[k]);

        const res = await fetch('/api/produits', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify(payload),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(`Création "${ing.nom}" : ${err.detail || err.message || `HTTP ${res.status}`}`);
        }
        const nouveau = await res.json();
        ing.produit_id = nouveau.id;
        produits.push(nouveau); // mise à jour du cache local
      }
    }

    // ── Étape 2 : envoyer la recette ──
    const payload = {
      nom,
      produit_fini_id: parseInt(produitId),
      dlc_jours:       dlcJours,
      instructions:    instructionsPrefix,
      ingredients:     ingredients.map(ing => {
        const item = {
          produit_id: ing.produit_id,
          quantite:   ing.quantite,
          unite:      ing.unite,
        };
        if (enEdition && ing.id != null) item.id = ing.id;
        return item;
      })
    };

    const url    = enEdition ? `/api/recettes/${recetteId}` : '/api/recettes';
    const method = enEdition ? 'PUT' : 'POST';
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.message || `HTTP ${res.status}`);
    }

    if (enEdition) {
      showToast(`✓ Recette "${nom}" mise à jour !`);
      // Récupérer les nouveaux ids d'ingrédients pour permettre une 2e sauvegarde cohérente
      const recetteMaj = await res.json();
      ingredients = (recetteMaj.ingredients || []).map(ing => ({
        id:         ing.id,
        produit_id: ing.produit_id,
        nom:        ing.produit_nom,
        quantite:   ing.quantite,
        unite:      ing.unite,
      }));
      renderIngredients();
    } else {
      showToast(`✓ Recette "${nom}" enregistrée avec succès !`);
      resetFormulaire();
    }

  } catch (err) {
    showErreur(`Erreur lors de l'enregistrement : ${err.message}`);
  } finally {
    btn.disabled    = false;
    btn.textContent = labelInitial;
  }
}

// ─────────────────────────────────────────────────────────────
//  Reset du formulaire après succès
// ─────────────────────────────────────────────────────────────
function resetFormulaire() {
  $('ar-nom-recette').value  = '';
  $('ar-dlc-jours').value    = '3';
  $('ar-rendement-qte').value = '';
  $('ar-rendement-unite').value = 'kg';

  // Reset produit fini
  clearSelection({
    inputEl:  $('ar-produit-fini'),
    listeEl:  $('ar-produit-fini-liste'),
    tagEl:    $('ar-produit-fini-tag'),
    hiddenEl: $('ar-produit-fini-id')
  });
  $('ar-produit-fini-tag-nom').textContent = '';

  // Reset encart détails produit
  const details     = $('produit-details');
  details.hidden    = true;
  details.innerHTML = '';

  // Reset ingrédients
  ingredients = [];
  renderIngredients();

  $('ar-nom-recette').focus();
}

// ─────────────────────────────────────────────────────────────
//  Feedback visuel
// ─────────────────────────────────────────────────────────────
function showErreur(msg) {
  const el = $('ar-erreur');
  el.textContent = msg;
  el.hidden = false;
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideErreur() {
  const el = $('ar-erreur');
  el.hidden    = true;
  el.textContent = '';
}

function flashErreurChamp(input, msg) {
  input.classList.add('ar-input--erreur');
  input.focus();
  setTimeout(() => input.classList.remove('ar-input--erreur'), 2000);
  showErreur(msg);
}

let toastTimer = null;
function showToast(msg) {
  const toast = $('ar-toast');
  toast.textContent = msg;
  toast.hidden = false;
  toast.classList.add('ar-toast--visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.classList.remove('ar-toast--visible');
    setTimeout(() => { toast.hidden = true; }, 400);
  }, 3500);
}

// ─────────────────────────────────────────────────────────────
//  Initialisation
// ─────────────────────────────────────────────────────────────
async function init() {
  await loadProduits();

  // Autocomplete — produit fini (sélection obligatoire avec tag)
  initAutocomplete({
    inputEl:  $('ar-produit-fini'),
    listeEl:  $('ar-produit-fini-liste'),
    tagEl:    $('ar-produit-fini-tag'),
    tagNomEl: $('ar-produit-fini-tag-nom'),
    clearEl:  $('ar-produit-fini-clear'),
    hiddenEl: $('ar-produit-fini-id'),
    onSelect: onProduitFiniSelect,
  });

  // Autocomplete — ingrédient (saisie libre autorisée)
  initIngrAutocomplete();

  $('ar-btn-ajouter').addEventListener('click', ajouterIngredient);
  $('ar-btn-submit').addEventListener('click', enregistrerRecette);

  // Valider ajout avec Entrée depuis les champs quantité/unité
  $('ar-ingr-qte').addEventListener('keydown', e => {
    if (e.key === 'Enter') ajouterIngredient();
  });

  // Modale nouvel ingrédient
  $('ar-modal-annuler').addEventListener('click', fermerModal);
  $('ar-modal-confirmer').addEventListener('click', confirmerNouvelIngredient);
  $('ar-modal-overlay').addEventListener('click', e => {
    if (e.target === $('ar-modal-overlay')) fermerModal();
  });
  $('ar-modal-espece').addEventListener('change', rafraichirCodePreview);
  $('ar-modal-abats').addEventListener('change', rafraichirCodePreview);

  // Modale édition d'un ingrédient existant
  $('ar-modal-edit-annuler').addEventListener('click', fermerModalEditIngredient);
  $('ar-modal-edit-confirmer').addEventListener('click', confirmerEditIngredient);
  $('ar-modal-edit-overlay').addEventListener('click', e => {
    if (e.target === $('ar-modal-edit-overlay')) fermerModalEditIngredient();
  });
  $('ar-modal-edit-qte').addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); confirmerEditIngredient(); }
  });

  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    if (!$('ar-modal-overlay').hidden) fermerModal();
    else if (!$('ar-modal-edit-overlay').hidden) fermerModalEditIngredient();
  });

  renderIngredients();

  // Mode édition si ?id=X est présent dans l'URL
  const params = new URLSearchParams(window.location.search);
  const idParam = params.get('id');
  if (idParam && /^\d+$/.test(idParam)) {
    await chargerRecettePourEdition(parseInt(idParam, 10));
  }
}

document.addEventListener('DOMContentLoaded', init);

'use strict';

// ─────────────────────────────────────────────────────────────
//  État interne
// ─────────────────────────────────────────────────────────────
let produits     = [];   // liste complète chargée depuis /api/produits
let ingredients  = [];   // { produit_id|null, nom, quantite, unite }

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
  const dlcInput = $('ar-dlc-jours');

  if (!p) {
    details.hidden    = true;
    details.innerHTML = '';
    dlcInput.value    = '';
    return;
  }

  if (p.dlc_jours != null) dlcInput.value = p.dlc_jours;

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
function calcProportions(list) {
  const totaux = {};
  list.forEach(ing => {
    totaux[ing.unite] = (totaux[ing.unite] || 0) + ing.quantite;
  });
  return list.map(ing => {
    const total = totaux[ing.unite];
    return total > 0 ? (ing.quantite / total * 100).toFixed(1) : '—';
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
    tr.innerHTML = `
      <td class="ar-td-nom">${escHtml(ing.nom)}${badgeNouv}</td>
      <td class="ar-td-qte">${escHtml(String(ing.quantite))}</td>
      <td class="ar-td-unite">${escHtml(ing.unite)}</td>
      <td class="ar-td-prop">${escHtml(String(proportions[idx]))}%</td>
      <td class="ar-td-action">
        <button type="button" class="ar-btn-suppr" aria-label="Supprimer ${escHtml(ing.nom)}">✕</button>
      </td>
    `;
    tr.querySelector('.ar-btn-suppr').addEventListener('click', () => {
      ingredients.splice(idx, 1);
      renderIngredients();
    });
    tbody.appendChild(tr);
  });
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

  // Si sélectionné depuis l'autocomplete, utilise le nom canonique du produit
  const nomFinal = produitId
    ? (produits.find(p => p.id === parseInt(produitId))?.nom || nomSaisi)
    : nomSaisi;

  ingredients.push({
    produit_id: produitId ? parseInt(produitId) : null,
    nom:        nomFinal,
    quantite:   qte,
    unite
  });

  renderIngredients();

  // Reset du bloc ajout
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
  const dlcJours  = parseInt($('ar-dlc-jours').value);

  if (!nom) {
    showErreur('Le nom de la recette est obligatoire.');
    $('ar-nom-recette').focus();
    return;
  }
  if (!produitId) {
    showErreur('Sélectionnez un produit fini associé.');
    return;
  }
  if (!dlcJours || dlcJours < 1) {
    showErreur('Saisissez une DLC valide (en jours).');
    $('ar-dlc-jours').focus();
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
  btn.disabled    = true;
  btn.textContent = 'Enregistrement…';

  try {
    // ── Étape 1 : créer silencieusement les ingrédients libres ──
    for (const ing of ingredients) {
      if (ing.produit_id === null) {
        const res = await fetch('/api/produits', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({
            nom:          ing.nom,
            type_produit: 'brut',
            categorie:    'Ingrédient'
          })
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(`Création "${ing.nom}" : ${err.message || `HTTP ${res.status}`}`);
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
      ingredients:     ingredients.map(ing => ({
        produit_id: ing.produit_id,
        quantite:   ing.quantite,
        unite:      ing.unite
      }))
    };

    const res = await fetch('/api/recettes', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || `HTTP ${res.status}`);
    }

    showToast(`✓ Recette "${nom}" enregistrée avec succès !`);
    resetFormulaire();

  } catch (err) {
    showErreur(`Erreur lors de l'enregistrement : ${err.message}`);
  } finally {
    btn.disabled    = false;
    btn.textContent = '✓ Enregistrer la recette';
  }
}

// ─────────────────────────────────────────────────────────────
//  Reset du formulaire après succès
// ─────────────────────────────────────────────────────────────
function resetFormulaire() {
  $('ar-nom-recette').value  = '';
  $('ar-dlc-jours').value    = '';
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

  renderIngredients();
}

document.addEventListener('DOMContentLoaded', init);

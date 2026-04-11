'use strict';

// ─────────────────────────────────────────────────────────────
//  État interne
// ─────────────────────────────────────────────────────────────
let produits = [];          // liste complète chargée depuis /api/produits
let ingredients = [];       // ingrédients sélectionnés pour la recette en cours

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
//  Autocomplete générique
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
    if (matches.length === 0) {
      listeEl.hidden = true;
      return;
    }

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
//  Rendu de la liste des ingrédients
// ─────────────────────────────────────────────────────────────
function renderIngredients() {
  const ul    = $('ar-ingredients-ul');
  const vide  = $('ar-ingredients-vide');

  if (ingredients.length === 0) {
    ul.hidden = true;
    vide.hidden = false;
    return;
  }

  vide.hidden = true;
  ul.hidden = false;
  ul.innerHTML = '';

  ingredients.forEach((ing, idx) => {
    const li = document.createElement('li');
    li.className = 'ar-ingredient-item';
    li.innerHTML = `
      <div class="ar-ingredient-info">
        <span class="ar-ingredient-nom">${escHtml(ing.nom)}</span>
        <span class="ar-ingredient-qte">${escHtml(String(ing.quantite))} ${escHtml(ing.unite)}</span>
      </div>
      <button type="button" class="ar-btn-suppr" aria-label="Supprimer ${escHtml(ing.nom)}">🗑</button>
    `;
    li.querySelector('.ar-btn-suppr').addEventListener('click', () => {
      ingredients.splice(idx, 1);
      renderIngredients();
    });
    ul.appendChild(li);
  });
}

// ─────────────────────────────────────────────────────────────
//  Ajout d'un ingrédient
// ─────────────────────────────────────────────────────────────
function ajouterIngredient() {
  const produitId  = $('ar-ingr-produit-id').value;
  const tagNom     = $('ar-ingr-tag-nom').textContent;
  const qte        = parseFloat($('ar-ingr-qte').value);
  const unite      = $('ar-ingr-unite').value;

  if (!produitId) {
    flashErreurChamp($('ar-ingr-produit'), 'Sélectionnez un produit ingrédient.');
    return;
  }
  if (!qte || qte <= 0) {
    flashErreurChamp($('ar-ingr-qte'), 'Saisissez une quantité valide.');
    return;
  }

  ingredients.push({ produit_id: parseInt(produitId), nom: tagNom, quantite: qte, unite });
  renderIngredients();

  // Reset du bloc ajout
  clearSelection({
    inputEl:  $('ar-ingr-produit'),
    listeEl:  $('ar-ingr-produit-liste'),
    tagEl:    $('ar-ingr-tag'),
    hiddenEl: $('ar-ingr-produit-id')
  });
  $('ar-ingr-tag-nom').textContent = '';
  $('ar-ingr-qte').value = '';
  $('ar-ingr-unite').value = 'g';
}

// ─────────────────────────────────────────────────────────────
//  Enregistrement de la recette
// ─────────────────────────────────────────────────────────────
async function enregistrerRecette() {
  hideErreur();

  const nom        = $('ar-nom-recette').value.trim();
  const produitId  = $('ar-produit-fini-id').value;
  const dlcJours   = parseInt($('ar-dlc-jours').value);

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

  const payload = {
    nom,
    produit_fini_id: parseInt(produitId),
    dlc_jours: dlcJours,
    ingredients: ingredients.map(ing => ({
      produit_id: ing.produit_id,
      quantite:   ing.quantite,
      unite:      ing.unite
    }))
  };

  const btn = $('ar-btn-submit');
  btn.disabled = true;
  btn.textContent = 'Enregistrement…';

  try {
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
    btn.disabled = false;
    btn.textContent = '✓ Enregistrer la recette';
  }
}

// ─────────────────────────────────────────────────────────────
//  Reset du formulaire après succès
// ─────────────────────────────────────────────────────────────
function resetFormulaire() {
  $('ar-nom-recette').value = '';
  $('ar-dlc-jours').value  = '';

  // Reset produit fini
  clearSelection({
    inputEl:  $('ar-produit-fini'),
    listeEl:  $('ar-produit-fini-liste'),
    tagEl:    $('ar-produit-fini-tag'),
    hiddenEl: $('ar-produit-fini-id')
  });
  $('ar-produit-fini-tag-nom').textContent = '';

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
  el.hidden = true;
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

  // Autocomplete — produit fini
  initAutocomplete({
    inputEl:  $('ar-produit-fini'),
    listeEl:  $('ar-produit-fini-liste'),
    tagEl:    $('ar-produit-fini-tag'),
    tagNomEl: $('ar-produit-fini-tag-nom'),
    clearEl:  $('ar-produit-fini-clear'),
    hiddenEl: $('ar-produit-fini-id'),
  });

  // Autocomplete — ingrédient
  initAutocomplete({
    inputEl:  $('ar-ingr-produit'),
    listeEl:  $('ar-ingr-produit-liste'),
    tagEl:    $('ar-ingr-tag'),
    tagNomEl: $('ar-ingr-tag-nom'),
    clearEl:  $('ar-ingr-clear'),
    hiddenEl: $('ar-ingr-produit-id'),
  });

  $('ar-btn-ajouter').addEventListener('click', ajouterIngredient);
  $('ar-btn-submit').addEventListener('click', enregistrerRecette);

  renderIngredients();
}

document.addEventListener('DOMContentLoaded', init);

'use strict';

// ─────────────────────────────────────────────────────────────
//  Modèle : ingrédients = catalogue ACHATS, produit fini = catalogue VENTE.
//  Le catalogue interne (produits) n'est plus utilisé par la Production.
// ─────────────────────────────────────────────────────────────
let articles    = [];   // catalogue achats : { id, designation, code_article, fournisseur_nom }
let produitsVente = []; // catalogue vente  : { id, nom, prix_vente_ttc, temperature_conservation }
let ingredients = [];   // { id?, catalogue_fournisseur_id|null, designation, quantite, unite }
let recetteId   = null; // null = création, integer = édition

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
//  Chargement des catalogues
// ─────────────────────────────────────────────────────────────
async function loadCatalogues() {
  try {
    const [rA, rV] = await Promise.all([
      fetch('/api/achats/catalogue?actif_only=true'),
      fetch('/api/vente/catalogue?actif_only=true'),
    ]);
    if (!rA.ok) throw new Error(`Catalogue achats HTTP ${rA.status}`);
    if (!rV.ok) throw new Error(`Catalogue vente HTTP ${rV.status}`);
    articles      = await rA.json();
    produitsVente = await rV.json();
  } catch (err) {
    console.error('Chargement catalogues :', err);
    showErreur('Impossible de charger les catalogues (achats / vente). Vérifiez la connexion au serveur.');
  }
}

// ─────────────────────────────────────────────────────────────
//  Autocomplete produit fini (catalogue de vente) — saisie libre = création
// ─────────────────────────────────────────────────────────────
function initProduitFiniAutocomplete() {
  const inputEl  = $('ar-produit-fini');
  const listeEl  = $('ar-produit-fini-liste');
  const tagEl    = $('ar-produit-fini-tag');
  const tagNomEl = $('ar-produit-fini-tag-nom');
  const clearEl  = $('ar-produit-fini-clear');
  const hiddenEl = $('ar-produit-fini-id');

  inputEl.addEventListener('input', () => {
    // Toute frappe efface l'id : sélection requise via la liste, ou création libre.
    hiddenEl.value = '';
    const q = inputEl.value.trim().toLowerCase();
    if (!q) { listeEl.hidden = true; onProduitFiniSelect(null); return; }

    const matches = produitsVente
      .filter(p => (p.nom || '').toLowerCase().includes(q))
      .slice(0, 10);

    listeEl.innerHTML = '';
    if (matches.length === 0) { listeEl.hidden = true; return; }

    matches.forEach(p => {
      const opt = document.createElement('div');
      opt.className = 'ar-autocomplete-option';
      opt.setAttribute('role', 'option');
      opt.textContent = p.nom + (p.prix_vente_ttc ? ` — ${p.prix_vente_ttc.toFixed(2)} €` : '');
      opt.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        selectProduitFini(p);
      });
      listeEl.appendChild(opt);
    });
    listeEl.hidden = false;
  });

  inputEl.addEventListener('blur', () => {
    setTimeout(() => { listeEl.hidden = true; }, 150);
  });

  clearEl.addEventListener('click', () => {
    hiddenEl.value = '';
    tagEl.hidden = true;
    inputEl.hidden = false;
    inputEl.value = '';
    inputEl.focus();
    listeEl.hidden = true;
    onProduitFiniSelect(null);
  });
}

function selectProduitFini(p) {
  $('ar-produit-fini-id').value = p.id;
  $('ar-produit-fini-tag-nom').textContent = p.nom;
  $('ar-produit-fini-tag').hidden = false;
  const inputEl = $('ar-produit-fini');
  inputEl.value = '';
  inputEl.hidden = true;
  $('ar-produit-fini-liste').hidden = true;
  onProduitFiniSelect(p);
}

// Affiche les détails du produit fini + pré-remplit le nom de recette
function onProduitFiniSelect(p) {
  const details = $('produit-details');
  if (!p) { details.hidden = true; details.innerHTML = ''; return; }

  const nomRecetteInput = $('ar-nom-recette');
  if (!nomRecetteInput.value.trim()) nomRecetteInput.value = p.nom;

  const rows = [
    { label: 'Prix de vente', val: p.prix_vente_ttc != null ? `${p.prix_vente_ttc.toFixed(2)} €` : null },
    { label: 'Température',   val: p.temperature_conservation },
    { label: 'DLC',          val: p.dlc_jours != null ? `J+${p.dlc_jours}` : null },
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
//  Autocomplete ingrédient (catalogue achats) — saisie libre autorisée
// ─────────────────────────────────────────────────────────────
function initIngrAutocomplete() {
  const inputEl  = $('ar-ingr-produit');
  const listeEl  = $('ar-ingr-produit-liste');
  const hiddenEl = $('ar-ingr-produit-id');
  const hintEl   = $('ar-ingr-hint');

  function updateHint() {
    // Hint visible si du texte est saisi sans article relié (= ingrédient à raccorder)
    hintEl.hidden = !inputEl.value.trim() || !!hiddenEl.value;
  }

  inputEl.addEventListener('input', () => {
    hiddenEl.value = '';      // toute frappe repasse en mode libre
    updateHint();

    const q = inputEl.value.trim().toLowerCase();
    if (!q) { listeEl.hidden = true; return; }

    const matches = articles.filter(a =>
      (a.designation || '').toLowerCase().includes(q) ||
      (a.code_article || '').toLowerCase().includes(q)
    ).slice(0, 10);

    listeEl.innerHTML = '';
    if (matches.length === 0) { listeEl.hidden = true; return; }

    matches.forEach(a => {
      const opt = document.createElement('div');
      opt.className = 'ar-autocomplete-option';
      opt.setAttribute('role', 'option');
      const fourn = a.fournisseur_nom ? ` · ${a.fournisseur_nom}` : '';
      opt.textContent = a.designation + (a.code_article ? ` (${a.code_article})` : '') + fourn;
      opt.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        inputEl.value  = a.designation;
        hiddenEl.value = a.id;          // catalogue_fournisseur_id
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
    wrap.hidden = true;
    vide.hidden = false;
    return;
  }
  vide.hidden = true;
  wrap.hidden = false;

  const proportions = calcProportions(ingredients);
  tbody.innerHTML = '';

  ingredients.forEach((ing, idx) => {
    const tr = document.createElement('tr');
    const badge = ing.catalogue_fournisseur_id == null
      ? ' <span class="ar-badge-nouveau">à raccorder</span>'
      : '';
    tr.className = 'ar-tr-clickable';
    tr.setAttribute('role', 'button');
    tr.setAttribute('tabindex', '0');
    tr.setAttribute('aria-label', `Modifier ${ing.designation}`);
    tr.innerHTML = `
      <td class="ar-td-nom">${escHtml(ing.designation)}${badge}</td>
      <td class="ar-td-qte">${escHtml(String(ing.quantite))}</td>
      <td class="ar-td-unite">${escHtml(ing.unite)}</td>
      <td class="ar-td-prop">${escHtml(String(proportions[idx]))}%</td>
      <td class="ar-td-action">
        <button type="button" class="ar-btn-suppr" aria-label="Supprimer ${escHtml(ing.designation)}">✕</button>
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

function ouvrirModalEditIngredient(idx) {
  const ing = ingredients[idx];
  if (!ing) return;
  _editIdx = idx;

  $('ar-modal-edit-nom').value = ing.designation;
  $('ar-modal-edit-qte').value = ing.quantite ?? '';

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
//  Ajout d'un ingrédient
// ─────────────────────────────────────────────────────────────
function ajouterIngredient() {
  const catId    = $('ar-ingr-produit-id').value;
  const nomSaisi = $('ar-ingr-produit').value.trim();
  const qte      = parseFloat($('ar-ingr-qte').value);
  const unite    = $('ar-ingr-unite').value;

  if (!nomSaisi) {
    flashErreurChamp($('ar-ingr-produit'), 'Saisissez ou choisissez un ingrédient.');
    return;
  }
  if (!qte || qte <= 0) {
    flashErreurChamp($('ar-ingr-qte'), 'Saisissez une quantité valide.');
    return;
  }

  // Article relié : désignation officielle ; sinon saisie libre (à raccorder).
  let designation = nomSaisi;
  let catalogueId = null;
  if (catId) {
    const art = articles.find(a => a.id === parseInt(catId, 10));
    catalogueId = parseInt(catId, 10);
    designation = art ? art.designation : nomSaisi;
  }

  ingredients.push({ catalogue_fournisseur_id: catalogueId, designation, quantite: qte, unite });
  renderIngredients();
  resetBlocAjout();
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
//  Mode édition : chargement d'une recette existante
// ─────────────────────────────────────────────────────────────
async function chargerRecettePourEdition(id) {
  try {
    const res = await fetch(`/api/recettes/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const recette = await res.json();
    recetteId = recette.id;

    const titreEl = document.querySelector('.ar-header-titre');
    if (titreEl) titreEl.textContent = `Modifier : ${recette.nom}`;
    document.title = `Modifier ${recette.nom} — HACCP Monitor`;
    $('ar-btn-submit').textContent = '✓ Mettre à jour la recette';

    $('ar-nom-recette').value = recette.nom || '';
    $('ar-dlc-jours').value   = '3';

    // Préfixe rendement extrait des instructions
    const m = (recette.instructions || '').match(/^Base pour\s+([\d.,]+)\s+(kg|L|pi[èe]ces?)\b/i);
    if (m) {
      $('ar-rendement-qte').value = m[1].replace(',', '.');
      const u = m[2].toLowerCase();
      $('ar-rendement-unite').value = u.startsWith('pi') ? 'pièces' : (u === 'l' ? 'L' : 'kg');
    }

    // Produit fini (catalogue de vente)
    if (recette.catalogue_vente_id) {
      const pf = produitsVente.find(p => p.id === recette.catalogue_vente_id)
              || { id: recette.catalogue_vente_id, nom: recette.produit_fini_nom };
      selectProduitFini(pf);
      $('ar-nom-recette').value = recette.nom || '';
    }

    // Ingrédients existants
    ingredients = (recette.ingredients || []).map(ing => ({
      id:                       ing.id,
      catalogue_fournisseur_id: ing.catalogue_fournisseur_id ?? null,
      designation:              ing.designation || ing.produit_nom || '',
      quantite:                 ing.quantite,
      unite:                    ing.unite,
    }));
    renderIngredients();
  } catch (err) {
    console.error('Chargement recette pour édition :', err);
    showErreur(`Impossible de charger la recette : ${err.message}`);
  }
}

// ─────────────────────────────────────────────────────────────
//  Création silencieuse d'un produit de vente (produit fini saisi libre)
// ─────────────────────────────────────────────────────────────
async function creerProduitVente(nom) {
  const res = await fetch('/api/vente/catalogue', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ nom, dlc_jours: 3 }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(`Création produit de vente "${nom}" : ${err.detail || `HTTP ${res.status}`}`);
  }
  const nouveau = await res.json();
  produitsVente.push(nouveau);
  return nouveau;
}

// ─────────────────────────────────────────────────────────────
//  Enregistrement de la recette
// ─────────────────────────────────────────────────────────────
async function enregistrerRecette() {
  hideErreur();

  const nom         = $('ar-nom-recette').value.trim();
  let   venteId     = $('ar-produit-fini-id').value;
  const venteSaisie = $('ar-produit-fini').value.trim();  // si saisie libre non sélectionnée

  if (!nom) {
    showErreur('Le nom de la recette est obligatoire.');
    $('ar-nom-recette').focus();
    return;
  }
  if (!venteId && !venteSaisie) {
    showErreur('Sélectionnez (ou saisissez) un produit fini du catalogue de vente.');
    return;
  }
  if (ingredients.length === 0) {
    showErreur('Ajoutez au moins un ingrédient avant d\'enregistrer.');
    return;
  }

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
    // Produit fini saisi librement → on le crée dans le catalogue de vente
    if (!venteId && venteSaisie) {
      const nouveau = await creerProduitVente(venteSaisie);
      venteId = nouveau.id;
    }

    const payload = {
      nom,
      catalogue_vente_id: venteId ? parseInt(venteId, 10) : null,
      dlc_jours:          3,
      instructions:       instructionsPrefix,
      ingredients:        ingredients.map(ing => {
        const item = {
          catalogue_fournisseur_id: ing.catalogue_fournisseur_id ?? null,
          designation:              ing.designation,
          quantite:                 ing.quantite,
          unite:                    ing.unite,
        };
        if (enEdition && ing.id != null) item.id = ing.id;
        return item;
      }),
    };

    const url    = enEdition ? `/api/recettes/${recetteId}` : '/api/recettes';
    const method = enEdition ? 'PUT' : 'POST';
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.message || `HTTP ${res.status}`);
    }

    if (enEdition) {
      showToast(`✓ Recette "${nom}" mise à jour !`);
      const recetteMaj = await res.json();
      ingredients = (recetteMaj.ingredients || []).map(ing => ({
        id:                       ing.id,
        catalogue_fournisseur_id: ing.catalogue_fournisseur_id ?? null,
        designation:              ing.designation || ing.produit_nom || '',
        quantite:                 ing.quantite,
        unite:                    ing.unite,
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
  $('ar-nom-recette').value     = '';
  $('ar-dlc-jours').value       = '3';
  $('ar-rendement-qte').value   = '';
  $('ar-rendement-unite').value = 'kg';

  $('ar-produit-fini-id').value = '';
  $('ar-produit-fini-tag').hidden = true;
  $('ar-produit-fini-tag-nom').textContent = '';
  const fini = $('ar-produit-fini');
  fini.hidden = false;
  fini.value  = '';

  const details = $('produit-details');
  details.hidden = true;
  details.innerHTML = '';

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
  await loadCatalogues();

  initProduitFiniAutocomplete();
  initIngrAutocomplete();

  $('ar-btn-ajouter').addEventListener('click', ajouterIngredient);
  $('ar-btn-submit').addEventListener('click', enregistrerRecette);

  $('ar-ingr-qte').addEventListener('keydown', e => {
    if (e.key === 'Enter') ajouterIngredient();
  });

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
    if (e.key === 'Escape' && !$('ar-modal-edit-overlay').hidden) fermerModalEditIngredient();
  });

  renderIngredients();

  // Mode édition si ?id=X
  const params = new URLSearchParams(window.location.search);
  const idParam = params.get('id');
  if (idParam && /^\d+$/.test(idParam)) {
    await chargerRecettePourEdition(parseInt(idParam, 10));
  }
}

document.addEventListener('DOMContentLoaded', init);

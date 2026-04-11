'use strict';
/* ============================================================
   etiquettes.js — Wizard Fabrication & Traçabilité
   Mets Carnés — HACCP Monitor

   Flux : Étape 1 (recette) → 2 (quantités) → 3 (lots FIFO)
          → 4 (récap + impression) → Écran succès
   ============================================================ */

// ── Helpers ──────────────────────────────────────────────────
function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function apiFetch(url, options = {}) {
  const res = await fetch(url, { cache: 'no-store', ...options });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} — ${txt || url}`);
  }
  return res.json();
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
    });
  } catch { return String(dateStr); }
}

// ── État global ───────────────────────────────────────────────
const state = {
  etape: 1,
  recetteId:       null,
  recetteNom:      null,
  recetteDlcJours: null,
  ingredients:     [],   // [{produit_id, nom, quantite, unite}, ...]
  quantities:      {},   // {produit_id: valeur}
  fifoLots:        [],   // [{ingredient_id, ingredient_nom, lot_numero, lot_dlc}, ...]
  lotsManuel:      {},   // {produit_id: {numero_lot, dlc}}
};

// ── Références DOM ────────────────────────────────────────────
const elHorloge        = document.getElementById('fab-horloge');
const elBtnRetour      = document.getElementById('fab-btn-retour');
const elBandeau        = document.getElementById('fab-bandeau');
const elBandeauNom     = document.getElementById('fab-bandeau-nom');
const elBandeauDlc     = document.getElementById('fab-bandeau-dlc');
const elSearch         = document.getElementById('fab-recette-search');
const elGrid           = document.getElementById('recettes-grid');
const elIngredients    = document.getElementById('fab-ingredients-liste');
const elBtnStep2Next   = document.getElementById('fab-btn-step2-next');
const elLots           = document.getElementById('fab-lots-liste');
const elBtnConfLots    = document.getElementById('fab-btn-confirmer-lots');
const elRecap          = document.getElementById('fab-recap-content');
const elOperateur      = document.getElementById('fab-operateur');
const elBtnGenerer     = document.getElementById('fab-btn-generer');
const elErreur         = document.getElementById('fab-erreur');
const elSucces         = document.getElementById('fab-succes');
const elSuccesLot      = document.getElementById('fab-succes-lot');
const elBtnMemeRecette = document.getElementById('fab-btn-meme-recette');
const elBtnNouvelleFab = document.getElementById('fab-btn-nouvelle-fab');

// ── Horloge ───────────────────────────────────────────────────
(function majHorloge() {
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
  setTimeout(majHorloge, 1000);
})();

// ── Timer inactivité 5 min → hub ──────────────────────────────
let timerInactivite;
function resetInactivite() {
  clearTimeout(timerInactivite);
  timerInactivite = setTimeout(() => { window.location.href = '/hub.html'; }, 5 * 60 * 1000);
}
['touchstart', 'mousedown', 'keydown'].forEach(evt =>
  document.addEventListener(evt, resetInactivite, true)
);
resetInactivite();

// ── Navigation wizard ─────────────────────────────────────────
function allerEtape(suivante) {
  const precedente = state.etape;
  if (suivante === precedente) return;

  const elPrev  = document.getElementById(`fab-step-${precedente}`);
  const elNext  = document.getElementById(`fab-step-${suivante}`);
  const forward = suivante > precedente;

  elNext.classList.remove('fab-step--active', 'fab-step--left', 'fab-step--right');
  elNext.classList.add(forward ? 'fab-step--right' : 'fab-step--left');

  // Forcer le reflow pour que la position de départ soit peinte avant la transition
  elNext.getBoundingClientRect();

  elNext.classList.remove('fab-step--left', 'fab-step--right');
  elNext.classList.add('fab-step--active');

  elPrev.classList.remove('fab-step--active');
  elPrev.classList.add(forward ? 'fab-step--left' : 'fab-step--right');

  state.etape = suivante;
  majProgress();
  elBandeau.hidden = suivante < 2;
}

function majProgress() {
  document.querySelectorAll('.fab-dot').forEach(dot => {
    const n = Number(dot.dataset.step);
    dot.classList.remove('fab-dot--active', 'fab-dot--done');
    if (n < state.etape)      dot.classList.add('fab-dot--done');
    else if (n === state.etape) dot.classList.add('fab-dot--active');
  });
  document.querySelectorAll('.fab-dot-line').forEach(line => {
    line.classList.toggle('fab-dot-line--done', Number(line.dataset.line) < state.etape);
  });
}

// ── Bouton Retour ─────────────────────────────────────────────
elBtnRetour.addEventListener('click', () => {
  if (state.etape === 1) {
    window.location.href = '/hub.html';
  } else {
    allerEtape(state.etape - 1);
  }
});

// ─────────────────────────────────────────────────────────────
//  ÉTAPE 1 : Grille de tuiles recettes
// ─────────────────────────────────────────────────────────────
let recettes = [];

async function chargerRecettes() {
  elGrid.innerHTML = `<div class="recettes-grid-vide">Chargement des recettes…</div>`;
  try {
    recettes = await apiFetch('/api/recettes');
  } catch (err) {
    recettes = [];
    elGrid.innerHTML = `<div class="recettes-grid-vide">⚠ Impossible de charger les recettes (${escHtml(err.message)})</div>`;
    return;
  }
  genererTuiles(recettes);
}

function genererTuiles(liste) {
  if (liste.length === 0) {
    elGrid.innerHTML = `<div class="recettes-grid-vide">Aucune recette disponible.</div>`;
    return;
  }
  elGrid.innerHTML = liste.map(r => `
    <div class="recette-tuile" data-id="${r.id}" role="listitem" tabindex="0"
         aria-label="${escHtml(r.nom)}, DLC J+${r.dlc_jours ?? '?'}">
      <div class="recette-tuile-img">🍖</div>
      <div class="recette-tuile-nom">${escHtml(r.nom)}</div>
      <div class="recette-tuile-dlc">DLC J+${r.dlc_jours ?? '?'}</div>
    </div>
  `).join('');
}

// Clic sur une tuile
elGrid.addEventListener('click', e => {
  const tuile = e.target.closest('.recette-tuile[data-id]');
  if (tuile) selectionnerRecette(Number(tuile.dataset.id));
});

elGrid.addEventListener('keydown', e => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const tuile = e.target.closest('.recette-tuile[data-id]');
  if (tuile) { e.preventDefault(); selectionnerRecette(Number(tuile.dataset.id)); }
});

// Filtre textuel instantané
elSearch.addEventListener('input', () => {
  const q = elSearch.value.trim().toLowerCase();
  if (!q) {
    // Réaffiche toutes les tuiles
    elGrid.querySelectorAll('.recette-tuile').forEach(t => { t.style.display = ''; });
    return;
  }
  elGrid.querySelectorAll('.recette-tuile').forEach(t => {
    const nom = (t.querySelector('.recette-tuile-nom')?.textContent ?? '').toLowerCase();
    t.style.display = nom.includes(q) ? '' : 'none';
  });
});

async function selectionnerRecette(id) {
  const recette = recettes.find(r => r.id === id);
  if (!recette) return;

  state.recetteId       = recette.id;
  state.recetteNom      = recette.nom;
  state.recetteDlcJours = recette.dlc_jours ?? null;

  elBandeauNom.textContent = recette.nom;
  elBandeauDlc.textContent = recette.dlc_jours ? `DLC J+${recette.dlc_jours}` : '';

  // Réinitialise le filtre pour la prochaine fois
  elSearch.value = '';

  await chargerIngredientsRecette(id);
  allerEtape(2);
}

// ─────────────────────────────────────────────────────────────
//  ÉTAPE 2 : Ingrédients + quantités
// ─────────────────────────────────────────────────────────────
async function chargerIngredientsRecette(id) {
  elIngredients.innerHTML = `<div class="fab-chargement">Chargement des ingrédients…</div>`;
  try {
    const detail = await apiFetch(`/api/recettes/${id}`);
    // Normalise le tableau d'ingrédients (gère plusieurs noms de propriété possibles)
    const raw = detail.ingredients ?? detail.lignes ?? [];
    state.ingredients = raw.map(ing => ({
      produit_id: ing.produit_id,
      nom:        ing.produit_nom ?? ing.nom ?? '',
      quantite:   ing.quantite ?? 0,
      unite:      ing.unite ?? 'kg',
    }));
  } catch {
    state.ingredients = [];
  }
  // Initialise les quantités
  state.quantities = {};
  state.ingredients.forEach(ing => {
    state.quantities[ing.produit_id] = ing.quantite;
  });
  afficherIngredients();
}

function afficherIngredients() {
  if (state.ingredients.length === 0) {
    elIngredients.innerHTML = `<div class="fab-chargement">Aucun ingrédient trouvé pour cette recette.</div>`;
    return;
  }
  elIngredients.innerHTML = state.ingredients.map(ing => `
    <div class="fab-ingredient-ligne">
      <div class="fab-ingredient-nom">${escHtml(ing.nom)}</div>
      <input class="fab-ingredient-qty"
             type="number" inputmode="numeric" min="0" step="any"
             value="${escHtml(String(ing.quantite ?? 0))}"
             data-pid="${ing.produit_id}"
             aria-label="Quantité de ${escHtml(ing.nom)}">
      <div class="fab-ingredient-unite">${escHtml(ing.unite)}</div>
    </div>
  `).join('');

  elIngredients.querySelectorAll('.fab-ingredient-qty').forEach(input => {
    input.addEventListener('change', () => {
      state.quantities[input.dataset.pid] = parseFloat(input.value) || 0;
    });
  });
}

elBtnStep2Next.addEventListener('click', async () => {
  // Persiste les quantités actuelles
  elIngredients.querySelectorAll('.fab-ingredient-qty').forEach(input => {
    state.quantities[input.dataset.pid] = parseFloat(input.value) || 0;
  });
  await chargerFifoLots();
  allerEtape(3);
});

// ─────────────────────────────────────────────────────────────
//  ÉTAPE 3 : Traçabilité & Lots (FIFO auto)
// ─────────────────────────────────────────────────────────────
async function chargerFifoLots() {
  elLots.innerHTML = `<div class="fab-chargement">Chargement des lots FIFO…</div>`;
  try {
    state.fifoLots = await apiFetch(`/api/fabrications/fifo-lots?recette_id=${state.recetteId}`);
  } catch {
    state.fifoLots = [];
  }
  state.lotsManuel = {};
  afficherLots();
}

function afficherLots() {
  // Si l'API ne renvoie rien, afficher une ligne manuelle pour chaque ingrédient
  if (!state.fifoLots || state.fifoLots.length === 0) {
    elLots.innerHTML = state.ingredients.map(ing =>
      htmlLigneManuelle(ing.produit_id, ing.nom)
    ).join('');
    attachListenersManuel();
    return;
  }

  elLots.innerHTML = state.fifoLots.map(lot => {
    if (lot.lot_numero != null) {
      return `
        <div class="fab-lot-ligne">
          <span class="fab-lot-check">✓</span>
          <div class="fab-lot-nom">${escHtml(lot.ingredient_nom ?? '')}</div>
          <div class="fab-lot-info">
            Lot ${escHtml(lot.lot_numero)} | DLC ${formatDate(lot.lot_dlc)}
          </div>
        </div>`;
    }
    return htmlLigneManuelle(lot.ingredient_id, lot.ingredient_nom ?? '');
  }).join('');

  attachListenersManuel();
}

function htmlLigneManuelle(ingId, ingNom) {
  return `
    <div class="fab-lot-ligne fab-lot-ligne--manquant" data-pid="${ingId}">
      <div class="fab-lot-manquant-titre">
        <span>⚠</span>
        <span>${escHtml(ingNom)} — Lot manquant, saisie manuelle</span>
      </div>
      <div class="fab-lot-manquant-champs">
        <input class="fab-lot-manquant-input" type="text"
               placeholder="N° lot (ex: FR-20260401-087)"
               data-pid="${ingId}" data-field="numero_lot">
        <input class="fab-lot-manquant-input" type="text"
               placeholder="DLC (ex: 18/04/2026)"
               data-pid="${ingId}" data-field="dlc" inputmode="numeric">
      </div>
    </div>`;
}

function attachListenersManuel() {
  elLots.querySelectorAll('.fab-lot-manquant-input').forEach(input => {
    input.addEventListener('input', syncLotsManuel);
  });
}

function syncLotsManuel() {
  state.lotsManuel = {};
  elLots.querySelectorAll('.fab-lot-ligne--manquant').forEach(ligne => {
    const pid = ligne.dataset.pid;
    const numeroLot = ligne.querySelector('[data-field="numero_lot"]')?.value?.trim() ?? '';
    const dlc       = ligne.querySelector('[data-field="dlc"]')?.value?.trim() ?? '';
    state.lotsManuel[pid] = { numero_lot: numeroLot, dlc };
  });
}

elBtnConfLots.addEventListener('click', () => {
  syncLotsManuel();
  afficherRecap();
  allerEtape(4);
});

// ─────────────────────────────────────────────────────────────
//  ÉTAPE 4 : Récapitulatif
// ─────────────────────────────────────────────────────────────
function afficherRecap() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dateFabFmt = new Date().toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });

  const dlcDate = new Date(today);
  dlcDate.setDate(dlcDate.getDate() + (state.recetteDlcJours ?? 0));
  const dlcFmt = dlcDate.toLocaleDateString('fr-FR', {
    weekday: 'short', day: '2-digit', month: 'long', year: 'numeric',
  });
  const diff = Math.ceil((dlcDate - today) / 86400000);
  const dlcClass = diff > 2 ? 'fab-recap-dlc--ok' : 'fab-recap-dlc--attention';

  // Construit une map lot par produit_id (FIFO en priorité, manuel en fallback)
  const lotsMap = {};
  (state.fifoLots ?? []).forEach(lot => {
    if (lot.lot_numero) lotsMap[String(lot.ingredient_id)] = lot.lot_numero;
  });
  Object.entries(state.lotsManuel).forEach(([pid, v]) => {
    if (v.numero_lot) lotsMap[String(pid)] = v.numero_lot;
  });

  const linesHtml = state.ingredients.map(ing => {
    const qty   = state.quantities[ing.produit_id] ?? 0;
    const lot   = lotsMap[String(ing.produit_id)] ?? '—';
    return `
      <div class="fab-recap-ing-ligne">
        <span class="fab-recap-ing-nom">${escHtml(ing.nom)}</span>
        <span class="fab-recap-ing-qty">${qty} ${escHtml(ing.unite)}</span>
        <span class="fab-recap-ing-lot">${escHtml(lot)}</span>
      </div>`;
  }).join('');

  elRecap.innerHTML = `
    <div class="fab-recap-recette">${escHtml(state.recetteNom)}</div>
    <div class="fab-recap-date">Fabrication du ${dateFabFmt}</div>
    <div class="fab-recap-dlc ${dlcClass}">DLC : ${dlcFmt}</div>
    <div class="fab-recap-sep"></div>
    <div class="fab-recap-ing-titre">Ingrédients &amp; lots</div>
    ${linesHtml}
  `;
}

// ─────────────────────────────────────────────────────────────
//  Soumission — POST /api/fabrications
// ─────────────────────────────────────────────────────────────
elBtnGenerer.addEventListener('click', async () => {
  elErreur.hidden = true;

  const personnelId = elOperateur.value;
  if (!personnelId) {
    elErreur.textContent = 'Veuillez sélectionner un opérateur.';
    elErreur.hidden = false;
    return;
  }

  // Construit le tableau lots_utilises
  const lotsUtilises = [];
  const lotsParPid   = {};

  // Lots FIFO valides
  (state.fifoLots ?? []).forEach(lot => {
    const pid = String(lot.ingredient_id);
    lotsParPid[pid] = {
      ingredient_id: lot.ingredient_id,
      lot_numero:    lot.lot_numero ?? null,
      lot_dlc:       lot.lot_dlc    ?? null,
      quantite:      state.quantities[pid] ?? state.quantities[Number(pid)] ?? 0,
    };
  });

  // Surcharge / complète avec les lots saisis manuellement
  Object.entries(state.lotsManuel).forEach(([pid, v]) => {
    if (!lotsParPid[pid]) {
      lotsParPid[pid] = {
        ingredient_id: Number(pid),
        lot_numero:    null,
        lot_dlc:       null,
        quantite:      state.quantities[pid] ?? 0,
      };
    }
    if (v.numero_lot) lotsParPid[pid].lot_numero = v.numero_lot;
    if (v.dlc)        lotsParPid[pid].lot_dlc    = v.dlc;
  });

  // Cas où fifoLots est vide : tous les ingrédients vont en manquants
  if (Object.keys(lotsParPid).length === 0) {
    state.ingredients.forEach(ing => {
      const pid = String(ing.produit_id);
      const manuel = state.lotsManuel[pid] ?? {};
      lotsParPid[pid] = {
        ingredient_id: ing.produit_id,
        lot_numero:    manuel.numero_lot || null,
        lot_dlc:       manuel.dlc || null,
        quantite:      state.quantities[pid] ?? 0,
      };
    });
  }

  Object.values(lotsParPid).forEach(l => lotsUtilises.push(l));

  const payload = {
    recette_id:    state.recetteId,
    personnel_id:  Number(personnelId),
    lots_utilises: lotsUtilises,
  };

  elBtnGenerer.disabled    = true;
  elBtnGenerer.textContent = '⏳ Enregistrement…';

  try {
    const result = await apiFetch('/api/fabrications', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    elSuccesLot.textContent = result.numero_lot ? `Lot : ${result.numero_lot}` : '';
    elSucces.hidden = false;
  } catch (err) {
    elErreur.textContent = `Erreur : ${err.message}`;
    elErreur.hidden = false;
  } finally {
    elBtnGenerer.disabled    = false;
    elBtnGenerer.textContent = '🖨 Générer & imprimer';
  }
});

// ─────────────────────────────────────────────────────────────
//  Écran de succès — actions post-impression
// ─────────────────────────────────────────────────────────────
elBtnMemeRecette.addEventListener('click', async () => {
  elSucces.hidden = true;
  // Conserve la recette, recharge les ingrédients et repart à l'étape 2
  await chargerIngredientsRecette(state.recetteId);
  allerEtape(2);
});

elBtnNouvelleFab.addEventListener('click', () => {
  elSucces.hidden = true;
  // Réinitialise tout
  Object.assign(state, {
    recetteId: null, recetteNom: null, recetteDlcJours: null,
    ingredients: [], quantities: {}, fifoLots: [], lotsManuel: {},
  });
  elSearch.value = '';
  elOperateur.value = '';
  elErreur.hidden = true;
  elBandeau.hidden = true;
  // Ramène toutes les étapes à leur position initiale
  [2, 3, 4].forEach(n => {
    const el = document.getElementById(`fab-step-${n}`);
    el.classList.remove('fab-step--active', 'fab-step--left');
    el.classList.add('fab-step--right');
  });
  const step1 = document.getElementById('fab-step-1');
  step1.classList.remove('fab-step--left', 'fab-step--right');
  step1.classList.add('fab-step--active');
  state.etape = 1;
  majProgress();
});

// ─────────────────────────────────────────────────────────────
//  Chargement personnel (étape 4)
// ─────────────────────────────────────────────────────────────
async function chargerPersonnel() {
  try {
    const personnel = await apiFetch('/api/admin/personnel');
    personnel.forEach(p => {
      const opt = document.createElement('option');
      opt.value       = p.id;
      opt.textContent = p.prenom;
      elOperateur.appendChild(opt);
    });
  } catch {
    // Non bloquant
  }
}

// ─────────────────────────────────────────────────────────────
//  Init
// ─────────────────────────────────────────────────────────────
async function init() {
  await Promise.all([chargerRecettes(), chargerPersonnel()]);
}

init();

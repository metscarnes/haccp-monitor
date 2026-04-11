'use strict';
/* ============================================================
   etiquettes.js — Wizard Fabrication & Traçabilité
   Mets Carnés — HACCP Monitor

   Flux : Étape 1 (recette) → 2 (calculateur) → 3 (lots FIFO)
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

function arrondir(v) {
  return Math.round(v * 100) / 100;
}

// ── État global ───────────────────────────────────────────────
const state = {
  etape:            1,
  recetteId:        null,
  recetteNom:       null,
  recetteDlcJours:  null,
  rendementBase:    null,   // nombre extrait de "Base pour X kg"
  rendementUnite:   'kg',   // unité extraite
  productionCiblee: 0,      // valeur saisie à l'étape 2
  ingredients:      [],     // [{produit_id, nom, quantite_base, unite}, ...]
  quantities:       {},     // {produit_id: valeur calculée}
  fifoLots:         [],     // [{ingredient_id, ingredient_nom, lot_numero, lot_dlc}, ...]
  lotsSubstitues:   {},     // {produit_id: {produit_id_sub, nom_sub}} — substituts choisis
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
const elProdCiblee     = document.getElementById('fab-prod-ciblee');
const elProdUnite      = document.getElementById('fab-prod-unite');
const elCalcBaseInfo   = document.getElementById('fab-calc-base-info');
const elCalcErreur     = document.getElementById('fab-calc-erreur');
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
const elSubOverlay     = document.getElementById('fab-sub-overlay');
const elSubTitre       = document.getElementById('fab-sub-titre');
const elSubGrid        = document.getElementById('fab-sub-grid');
const elSubCancel      = document.getElementById('fab-sub-cancel');

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

  elNext.getBoundingClientRect(); // forcer reflow

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
    if (n < state.etape)       dot.classList.add('fab-dot--done');
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

elGrid.addEventListener('click', e => {
  const tuile = e.target.closest('.recette-tuile[data-id]');
  if (tuile) selectionnerRecette(Number(tuile.dataset.id));
});

elGrid.addEventListener('keydown', e => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const tuile = e.target.closest('.recette-tuile[data-id]');
  if (tuile) { e.preventDefault(); selectionnerRecette(Number(tuile.dataset.id)); }
});

elSearch.addEventListener('input', () => {
  const q = elSearch.value.trim().toLowerCase();
  elGrid.querySelectorAll('.recette-tuile').forEach(t => {
    const nom = (t.querySelector('.recette-tuile-nom')?.textContent ?? '').toLowerCase();
    t.style.display = (!q || nom.includes(q)) ? '' : 'none';
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
  elSearch.value = '';

  await chargerIngredientsRecette(id);
  allerEtape(2);
}

// ─────────────────────────────────────────────────────────────
//  ÉTAPE 2 : Calculateur de production
// ─────────────────────────────────────────────────────────────

/** Extrait "Base pour X kg/pièces" depuis le champ instructions */
function extraireRendement(instructions) {
  if (!instructions) return { base: null, unite: 'kg' };
  const m = String(instructions).match(/base pour (\d+(?:[.,]\d+)?)\s*(kg|g|pièces?|pc|l)?/i);
  if (!m) return { base: null, unite: 'kg' };
  const base = parseFloat(m[1].replace(',', '.'));
  if (isNaN(base) || base <= 0) return { base: null, unite: 'kg' };
  const unite = (m[2] ?? 'kg').replace(/pièces?/i, 'pièces').toLowerCase();
  return { base, unite };
}

async function chargerIngredientsRecette(id) {
  elIngredients.innerHTML = `<div class="fab-chargement">Chargement des ingrédients…</div>`;
  try {
    const detail = await apiFetch(`/api/recettes/${id}`);

    // Rendement de base depuis les instructions
    const { base, unite } = extraireRendement(detail.instructions);
    state.rendementBase  = base;
    state.rendementUnite = unite;

    const raw = detail.ingredients ?? detail.lignes ?? [];
    state.ingredients = raw.map(ing => ({
      recette_ingredient_id: ing.id ?? ing.recette_ingredient_id,
      produit_id:            ing.produit_id,
      nom:                   ing.produit_nom ?? ing.nom ?? '',
      quantite_base:         ing.quantite ?? 0,
      unite:                 ing.unite ?? 'kg',
    }));
  } catch {
    state.ingredients    = [];
    state.rendementBase  = null;
    state.rendementUnite = 'kg';
  }

  // Réinitialise la production ciblée
  state.productionCiblee = 0;
  elProdCiblee.value = '';

  // Affiche l'unité et l'info de base
  elProdUnite.textContent = state.rendementUnite;
  if (state.rendementBase) {
    elCalcBaseInfo.textContent = `Base recette : ${state.rendementBase} ${state.rendementUnite}`;
    elCalcBaseInfo.classList.remove('fab-calc-base-info--warn');
  } else {
    elCalcBaseInfo.textContent = 'Aucune base de rendement trouvée — quantités fixes affichées.';
    elCalcBaseInfo.classList.add('fab-calc-base-info--warn');
  }

  recalculerQuantites();
  afficherIngredients();
}

/** Recalcule les quantités selon la production ciblée */
function recalculerQuantites() {
  state.quantities = {};
  state.ingredients.forEach(ing => {
    let qty;
    if (state.rendementBase && state.productionCiblee > 0) {
      qty = arrondir((ing.quantite_base / state.rendementBase) * state.productionCiblee);
    } else {
      qty = ing.quantite_base;
    }
    state.quantities[ing.produit_id] = qty;
  });
}

function afficherIngredients() {
  if (state.ingredients.length === 0) {
    elIngredients.innerHTML = `<div class="fab-chargement">Aucun ingrédient trouvé pour cette recette.</div>`;
    return;
  }
  elIngredients.innerHTML = state.ingredients.map(ing => {
    const qty = state.quantities[ing.produit_id] ?? 0;
    return `
      <div class="fab-ingredient-ligne">
        <div class="fab-ingredient-nom">${escHtml(ing.nom)}</div>
        <div class="fab-ingredient-qty-display" data-pid="${ing.produit_id}">
          ${qty > 0 ? qty : '—'}
        </div>
        <div class="fab-ingredient-unite">${escHtml(ing.unite)}</div>
      </div>
    `;
  }).join('');
}

// Recalcul live à chaque frappe dans le champ de production
elProdCiblee.addEventListener('input', () => {
  state.productionCiblee = parseFloat(elProdCiblee.value) || 0;
  recalculerQuantites();
  elIngredients.querySelectorAll('.fab-ingredient-qty-display[data-pid]').forEach(el => {
    const qty = state.quantities[el.dataset.pid] ?? 0;
    el.textContent = qty > 0 ? qty : '—';
  });
});

elBtnStep2Next.addEventListener('click', async () => {
  elCalcErreur.hidden = true;

  // Si la recette a un rendement et que rien n'est saisi → bloquer
  if (state.rendementBase && state.productionCiblee <= 0) {
    elCalcErreur.textContent = 'Veuillez saisir la production ciblée du jour.';
    elCalcErreur.hidden = false;
    elProdCiblee.focus();
    return;
  }

  await chargerFifoLots();
  allerEtape(3);
});

// ─────────────────────────────────────────────────────────────
//  ÉTAPE 3 : Traçabilité & Lots (FIFO + Substitution Zéro Clavier)
// ─────────────────────────────────────────────────────────────
async function chargerFifoLots() {
  elLots.innerHTML = `<div class="fab-chargement">Chargement des lots FIFO…</div>`;
  try {
    const raw = await apiFetch(`/api/fabrications/fifo-lots?recette_id=${state.recetteId}`);
    console.log('[FIFO] Réponse brute API :', JSON.stringify(raw, null, 2));
    // L'API retourne { recette_id, recette_nom, ingredients: [...] }
    state.fifoLots = Array.isArray(raw) ? raw : (raw?.ingredients ?? raw?.lots ?? raw?.data ?? []);
    console.log('[FIFO] state.fifoLots après parsing :', state.fifoLots);
  } catch (err) {
    console.error('[FIFO] Erreur chargement lots :', err);
    state.fifoLots = [];
  }
  state.lotsSubstitues = {};
  afficherLots();
}

function afficherLots() {
  if (!state.fifoLots || state.fifoLots.length === 0) {
    // Aucun lot FIFO du tout → tout manquant
    elLots.innerHTML = state.ingredients.map(ing =>
      htmlLigneManquante(ing.recette_ingredient_id, ing.nom)
    ).join('');
    return;
  }

  elLots.innerHTML = state.fifoLots.map(lot => {
    const riId = lot.recette_ingredient_id ?? lot.ingredient_id;
    console.log('[FIFO] lot affiché :', riId, lot.produit_nom, '→ lot_fifo:', lot.lot_fifo);
    if (lot.lot_fifo != null) {
      return htmlLigneFifoOk(lot);
    }
    return htmlLigneManquante(riId, lot.produit_nom ?? lot.ingredient_nom ?? '');
  }).join('');
}

function htmlLigneFifoOk(lot) {
  const lotFifo = lot.lot_fifo ?? {};
  return `
    <div class="fab-lot-ligne fab-lot-ligne--ok">
      <span class="fab-lot-check">✓</span>
      <div class="fab-lot-nom">${escHtml(lot.produit_nom ?? lot.ingredient_nom ?? '')}</div>
      <div class="fab-lot-info">
        Lot ${escHtml(lotFifo.numero_lot ?? '—')} | DLC ${formatDate(lotFifo.dlc ?? '')}
      </div>
    </div>`;
}

function htmlLigneManquante(ingId, ingNom) {
  return `
    <div class="fab-lot-ligne fab-lot-ligne--manquant" data-pid="${ingId}">
      <span class="fab-lot-manquant-icon">⚠</span>
      <div class="fab-lot-nom">${escHtml(ingNom)}</div>
      <button class="fab-lot-btn-remplacer"
              data-pid="${ingId}"
              data-nom="${escHtml(ingNom)}"
              aria-label="Remplacer le lot de ${escHtml(ingNom)}">
        🔄 Remplacer
      </button>
    </div>`;
}

// ── Substitution produit — logique modale ─────────────────────
let subPidCourant = null;
let subNomCourant = null;

elLots.addEventListener('click', async e => {
  const btn = e.target.closest('.fab-lot-btn-remplacer');
  if (!btn) return;
  subPidCourant = btn.dataset.pid;
  subNomCourant = btn.dataset.nom;
  await ouvrirModalSubstitution(subNomCourant);
});

async function ouvrirModalSubstitution(ingNom) {
  elSubTitre.textContent = `Substitut pour : ${ingNom}`;
  elSubGrid.innerHTML = `<div class="fab-chargement">Recherche de produits…</div>`;
  elSubOverlay.hidden = false;

  try {
    const produits = await apiFetch('/api/produits?type=brut');

    // Filtre : premier mot-clé du nom de l'ingrédient
    const motCle = (ingNom ?? '').trim().split(/[\s\-_]+/)[0].toUpperCase();
    const filtres = produits.filter(p =>
      (p.nom ?? '').toUpperCase().includes(motCle)
    );

    if (filtres.length === 0) {
      elSubGrid.innerHTML = `
        <div class="fab-sub-vide">
          Aucun produit trouvé pour « ${escHtml(motCle)} ».<br>
          Contactez votre responsable.
        </div>`;
      return;
    }

    elSubGrid.innerHTML = filtres.map(p => `
      <div class="fab-sub-tuile" data-produit-id="${p.id}"
           data-produit-nom="${escHtml(p.nom)}" role="button" tabindex="0">
        <div class="fab-sub-tuile-icon">📦</div>
        <div class="fab-sub-tuile-nom">${escHtml(p.nom)}</div>
        ${p.stock != null
          ? `<div class="fab-sub-tuile-stock">${p.stock} ${escHtml(p.unite ?? '')}</div>`
          : ''}
      </div>
    `).join('');
  } catch (err) {
    elSubGrid.innerHTML = `<div class="fab-sub-vide">Erreur : ${escHtml(err.message)}</div>`;
  }
}

elSubGrid.addEventListener('click', e => {
  const tuile = e.target.closest('.fab-sub-tuile');
  if (!tuile) return;
  validerSubstitution(tuile.dataset.produitId, tuile.dataset.produitNom);
});

elSubGrid.addEventListener('keydown', e => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const tuile = e.target.closest('.fab-sub-tuile');
  if (tuile) { e.preventDefault(); validerSubstitution(tuile.dataset.produitId, tuile.dataset.produitNom); }
});

function validerSubstitution(produitId, produitNom) {
  // Enregistre la substitution
  state.lotsSubstitues[subPidCourant] = { produit_id: produitId, nom: produitNom };

  // Met à jour la ligne dans le DOM → verte
  const ligne = elLots.querySelector(`.fab-lot-ligne[data-pid="${subPidCourant}"]`);
  if (ligne) {
    ligne.outerHTML = `
      <div class="fab-lot-ligne fab-lot-ligne--substitue" data-pid="${subPidCourant}">
        <span class="fab-lot-check">✓</span>
        <div class="fab-lot-nom">${escHtml(subNomCourant)}</div>
        <div class="fab-lot-info fab-lot-sub-badge">→ ${escHtml(produitNom)} (substitut)</div>
      </div>`;
  }

  elSubOverlay.hidden = true;
}

elSubCancel.addEventListener('click', () => { elSubOverlay.hidden = true; });
elSubOverlay.addEventListener('click', e => {
  if (e.target === elSubOverlay) elSubOverlay.hidden = true;
});

elBtnConfLots.addEventListener('click', () => {
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

  // Poids total fabriqué
  const poidsTotal = state.productionCiblee > 0
    ? `${state.productionCiblee} ${state.rendementUnite}`
    : '—';

  // Map lot par recette_ingredient_id
  const lotsMap = {};
  (state.fifoLots ?? []).forEach(lot => {
    const riId = lot.recette_ingredient_id ?? lot.ingredient_id;
    const numLot = lot.lot_fifo?.numero_lot;
    if (numLot) lotsMap[String(riId)] = numLot;
  });
  Object.entries(state.lotsSubstitues).forEach(([riId, v]) => {
    lotsMap[String(riId)] = `Substitut : ${v.nom}`;
  });

  const linesHtml = state.ingredients.map(ing => {
    const qty = state.quantities[ing.produit_id] ?? 0;
    const lot = lotsMap[String(ing.recette_ingredient_id)] ?? '—';
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
    <div class="fab-recap-poids">⚖ ${escHtml(poidsTotal)} fabriqués</div>
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

  // Helper : quantité calculée pour un recette_ingredient_id
  function qtyFor(riId) {
    const ing = state.ingredients.find(
      i => String(i.recette_ingredient_id) === String(riId)
    );
    return ing ? (state.quantities[ing.produit_id] ?? 0) : 0;
  }

  // Construit la map lots par recette_ingredient_id
  const lotsParRiId = {};

  // 1) Lots FIFO (trouvés ou manquants, avec reception_ligne_id)
  (state.fifoLots ?? []).forEach(lot => {
    const riId = String(lot.recette_ingredient_id ?? lot.ingredient_id);
    lotsParRiId[riId] = {
      recette_ingredient_id: Number(riId),
      reception_ligne_id:    lot.lot_fifo?.reception_ligne_id ?? null,
      quantite:              qtyFor(riId),
    };
  });

  // 2) Ingrédients non couverts par FIFO (fifoLots vide ou ingredient absent)
  state.ingredients.forEach(ing => {
    const riId = String(ing.recette_ingredient_id);
    if (!lotsParRiId[riId]) {
      lotsParRiId[riId] = {
        recette_ingredient_id: ing.recette_ingredient_id,
        reception_ligne_id:    null,
        quantite:              state.quantities[ing.produit_id] ?? 0,
      };
    }
  });

  const lotsUtilises = Object.values(lotsParRiId);

  const payload = {
    recette_id:   state.recetteId,
    personnel_id: Number(personnelId),
    date:         new Date().toISOString().slice(0, 10),
    lots:         lotsUtilises,
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
  await chargerIngredientsRecette(state.recetteId);
  allerEtape(2);
});

elBtnNouvelleFab.addEventListener('click', () => {
  elSucces.hidden = true;
  Object.assign(state, {
    recetteId: null, recetteNom: null, recetteDlcJours: null,
    rendementBase: null, rendementUnite: 'kg', productionCiblee: 0,
    ingredients: [], quantities: {}, fifoLots: [], lotsSubstitues: {},
  });
  elSearch.value     = '';
  elProdCiblee.value = '';
  elOperateur.value  = '';
  elErreur.hidden    = true;
  elCalcErreur.hidden = true;
  elBandeau.hidden   = true;

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

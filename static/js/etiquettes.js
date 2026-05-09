'use strict';
/* ============================================================
   etiquettes.js — Wizard Fabrication & Traçabilité
   Mets Carnés — HACCP Monitor

   Flux : Étape 1 (recette) → 2 (calculateur) → 3 (lots FIFO)
          → 4 (récap + impression) → Écran succès
   ============================================================ */

// ── Lexique codes viande ──────────────────────────────────────
const LEXIQUE = {
  VB: ['Bœuf', 'Boeuf', 'Vache', 'Bovine', 'Bf'],
  VX: ['Veau'],
  PC: ['Porc', 'Cochon'],
  AG: ['Agneau'],
  GI: ['Gibier', 'Cerf', 'Sanglier'],
};
const CODES_VIANDE = Object.keys(LEXIQUE);
const MOTS_PARASITES = new Set(['SANS', 'AVEC', 'OS', 'PAD', 'VRAC', 'DE', 'LA', 'LE', 'LES', 'DU', 'EN', 'ET', 'AU']);

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

// ── Modale confirmation personnalisée (remplace window.confirm) ───────────
function afficherCustomConfirm(titre, message, callbackOui) {
  const overlay  = document.getElementById('modal-custom-confirm');
  const elTitre  = document.getElementById('custom-confirm-title');
  const elMsg    = document.getElementById('custom-confirm-message');
  const btnOk    = document.getElementById('custom-confirm-ok');
  const btnCancel = document.getElementById('custom-confirm-cancel');

  elTitre.textContent = titre;
  elMsg.textContent   = message;
  overlay.style.display = 'flex';

  function fermer() {
    overlay.style.display = 'none';
    btnOk.removeEventListener('click', onOk);
    btnCancel.removeEventListener('click', onCancel);
  }
  function onOk()     { fermer(); callbackOui(); }
  function onCancel() { fermer(); }

  btnOk.addEventListener('click', onOk);
  btnCancel.addEventListener('click', onCancel);
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
  dlcFinale:        null,   // "YYYY-MM-DD" calculée selon règle HACCP (min théorique/ingrédients)
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
const elBtnMemeRecette  = document.getElementById('fab-btn-meme-recette');
const elBtnNouvelleFab  = document.getElementById('fab-btn-nouvelle-fab');
const elBtnHub          = document.getElementById('fab-btn-hub');
const elSuccesCountdown = document.getElementById('fab-succes-countdown');
const elCountdownSec    = document.getElementById('fab-countdown-sec');
const elSubOverlay     = document.getElementById('fab-sub-overlay');
const elSubTitre       = document.getElementById('fab-sub-titre');
const elSubSearch      = document.getElementById('search-substitut');
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
    window.location.href = '/production-hub.html';
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

  // Relecture explicite de l'input au moment du clic (capture coller/autofill/navigation clavier)
  const saisi = parseFloat(elProdCiblee.value) || 0;
  state.productionCiblee = saisi;
  recalculerQuantites();

  if (state.rendementBase) {
    // Recette avec base de rendement : le poids est obligatoire
    if (state.productionCiblee <= 0) {
      elCalcErreur.textContent = 'Veuillez saisir la production ciblée du jour.';
      elCalcErreur.hidden = false;
      elProdCiblee.focus();
      return;
    }
  } else if (state.productionCiblee <= 0) {
    // Recette sans base : fallback sur la somme des quantités de base
    const totalBase = state.ingredients.reduce((s, ing) => s + (ing.quantite_base ?? 0), 0);
    state.productionCiblee = totalBase > 0 ? totalBase : null;
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
    verifierLotsComplets();
    return;
  }

  elLots.innerHTML = state.fifoLots.map(lot => {
    const riId = lot.recette_ingredient_id ?? lot.ingredient_id;
    console.log('[FIFO] lot affiché :', riId, lot.produit_nom, '→ lot_fifo:', lot.lot_fifo);
    if (lot.lot_fifo != null) {
      return htmlLigneFifoOk(lot, riId);
    }
    return htmlLigneManquante(riId, lot.produit_nom ?? lot.ingredient_nom ?? '');
  }).join('');
  verifierLotsComplets();
}

/** Active ou désactive le bouton "Confirmer les lots" selon l'état des lots FIFO. */
function verifierLotsComplets() {
  const tousLotsValides = state.fifoLots.every(ing => ing.lot_fifo != null);
  if (elBtnConfLots) {
    if (tousLotsValides) {
      elBtnConfLots.disabled = false;
      elBtnConfLots.classList.remove('opacity-50', 'cursor-not-allowed');
      elBtnConfLots.title = '';
    } else {
      elBtnConfLots.disabled = true;
      elBtnConfLots.classList.add('opacity-50', 'cursor-not-allowed');
      elBtnConfLots.title = 'Veuillez substituer les produits manquants avant de valider.';
    }
  }
}

function htmlLigneFifoOk(lot, ingId) {
  const lotFifo   = lot.lot_fifo ?? {};
  const ingNom    = lot.produit_nom ?? lot.ingredient_nom ?? '';
  const dateVal   = lotFifo.dlc || lotFifo.dluo;
  const dateLabel = lotFifo.dluo && !lotFifo.dlc ? 'DLUO' : 'DLC';
  return `
    <div class="fab-lot-ligne fab-lot-ligne--ok" data-pid="${ingId}">
      <span class="fab-lot-check">✓</span>
      <div class="fab-lot-nom">${escHtml(ingNom)}</div>
      <div class="fab-lot-info">
        Lot ${escHtml(lotFifo.numero_lot ?? '—')} | ${dateLabel} ${formatDate(dateVal ?? '')}
      </div>
      <button class="fab-lot-btn-remplacer fab-lot-btn-personnaliser"
              data-pid="${ingId}"
              data-nom="${escHtml(ingNom)}"
              aria-label="Personnaliser le lot de ${escHtml(ingNom)}">
        ✏️ Personnaliser
      </button>
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
let subPidCourant  = null;   // recette_ingredient_id de la ligne en cours
let subNomCourant  = null;
let subLotCourant  = null;   // lot FIFO actuel (pour exclure la même ligne de réception)
let subAllProduits = [];     // cache produits bruts en stock chargés

/** Exclut le lot actuellement sélectionné (même ligne de réception) du choix. */
function exclureLotCourant(produits) {
  const ridCourant = subLotCourant?.lot_fifo?.reception_ligne_id;
  if (!ridCourant) return produits;
  return produits.filter(p =>
    p.reception_ligne_id == null || Number(p.reception_ligne_id) !== Number(ridCourant)
  );
}

/** Détecte le code viande en tête du nom (ex: "VB-COLLIER" → "VB") */
function extraireCode(nom) {
  const m = (nom ?? '').trim().toUpperCase().match(/^(VB|VX|PC|AG|GI)\b/);
  return m ? m[1] : null;
}

/** Isole le mot-muscle principal après nettoyage du nom */
function extraireMotMuscle(nom) {
  let clean = (nom ?? '').toUpperCase()
    .replace(new RegExp(`^(${CODES_VIANDE.join('|')})\\b[\\s\\-_]*`, 'i'), '')
    .replace(/[\-_]+/g, ' ')
    .trim();
  const mots = clean.split(/\s+/).filter(m => m.length > 1 && !MOTS_PARASITES.has(m));
  return mots[0] ?? '';
}

/** Filtre intelligent : muscle + catégorie via lexique. Fallback = tout le catalogue. */
function filtrerProduitsIntelligent(produits, ingNom) {
  const motMuscle = extraireMotMuscle(ingNom);
  const code      = extraireCode(ingNom);

  if (!motMuscle) return produits;

  let resultats;
  if (code && LEXIQUE[code]) {
    // Synonymes = le code lui-même + les mots du lexique
    const synonymes = [code, ...LEXIQUE[code]].map(s => s.toUpperCase());
    resultats = produits.filter(p => {
      const nomP = (p.nom ?? '').toUpperCase();
      return nomP.includes(motMuscle) && synonymes.some(s => nomP.includes(s));
    });
  } else {
    resultats = produits.filter(p => (p.nom ?? '').toUpperCase().includes(motMuscle));
  }

  return resultats.length > 0 ? resultats : produits;
}

function htmlSubTuile(p, index = 0) {
  const isPriority = index === 0;

  // Calcul urgence DLC/DLUO
  const dateVal   = p.dlc || p.dluo;
  const dateLabel = p.dluo && !p.dlc ? 'DLUO' : 'DLC';
  let dlcClasse = '';
  let dlcTexte  = formatDate(dateVal);
  if (dateVal) {
    const jours = Math.ceil((new Date(dateVal) - new Date()) / (1000 * 60 * 60 * 24));
    if (jours <= 2)      dlcClasse = 'dlc-critique';
    else if (jours <= 5) dlcClasse = 'dlc-attention';
    else                 dlcClasse = 'dlc-ok';
  }

  const lotInfo = (p.numero_lot || dateVal)
    ? `<div style="font-size:.75rem;margin-top:.35rem">
         Lot&nbsp;: ${escHtml(p.numero_lot ?? '—')} | ${dateLabel}&nbsp;: <span class="${dlcClasse}">${dlcTexte}</span>
       </div>`
    : '';

  return `
    <div class="fab-sub-tuile${isPriority ? ' tuile-priorite' : ''}" data-produit-id="${p.id}"
         data-produit-nom="${escHtml(p.nom)}"
         data-reception-ligne-id="${p.reception_ligne_id ?? ''}"
         role="button" tabindex="0"
         style="position:relative;">
      ${isPriority ? `<div class="badge-fifo">⭐ PRIORITÉ FIFO</div>` : ''}
      <div class="fab-sub-tuile-icon">📦</div>
      <div class="fab-sub-tuile-nom">${escHtml(p.nom)}</div>
      ${p.stock != null
        ? `<div class="fab-sub-tuile-stock">${p.stock} ${escHtml(p.unite ?? '')}</div>`
        : ''}
      ${lotInfo}
    </div>`;
}

function afficherSubProduits(produits) {
  if (produits.length === 0) {
    elSubGrid.innerHTML = `<div class="fab-sub-vide">Aucun produit trouvé.</div>`;
    return;
  }
  const tries = [...produits].sort((a, b) => {
    const da = (a.dlc || a.dluo) ? new Date(a.dlc || a.dluo) : null;
    const db = (b.dlc || b.dluo) ? new Date(b.dlc || b.dluo) : null;
    if (!da && !db) return 0;
    if (!da) return 1;   // sans date → fin de liste
    if (!db) return -1;
    return da - db;
  });
  elSubGrid.innerHTML = tries.map((p, i) => htmlSubTuile(p, i)).join('');
}

elLots.addEventListener('click', async e => {
  const btn = e.target.closest('.fab-lot-btn-remplacer');
  if (!btn) return;
  subPidCourant = btn.dataset.pid;
  subNomCourant = btn.dataset.nom;
  subLotCourant = (state.fifoLots ?? []).find(l =>
    String(l.recette_ingredient_id ?? l.ingredient_id) === String(subPidCourant)
  ) ?? null;
  await ouvrirModalSubstitution(subNomCourant);
});

async function ouvrirModalSubstitution(ingNom) {
  elSubTitre.textContent = `Substitut pour : ${ingNom}`;
  elSubSearch.value = '';
  elSubGrid.innerHTML = `<div class="fab-chargement">Recherche dans le stock réel…</div>`;
  elSubOverlay.hidden = false;

  try {
    // Un row par lot disponible (et non par produit) : permet de choisir
    // un lot spécifique parmi plusieurs lots du même produit.
    const lots = await apiFetch('/api/produits/lots-disponibles?type=brut');
    subAllProduits = exclureLotCourant(lots);
    const filtres = filtrerProduitsIntelligent(subAllProduits, ingNom);
    afficherSubProduits(filtres);
  } catch (err) {
    elSubGrid.innerHTML = `<div class="fab-sub-vide">Erreur : ${escHtml(err.message)}</div>`;
  }
}

// Recherche texte — filtre sur les produits en stock
elSubSearch.addEventListener('input', () => {
  const q = elSubSearch.value.trim().toUpperCase();
  if (!q) {
    afficherSubProduits(filtrerProduitsIntelligent(subAllProduits, subNomCourant));
    return;
  }
  afficherSubProduits(subAllProduits.filter(p => (p.nom ?? '').toUpperCase().includes(q)));
});

elSubGrid.addEventListener('click', e => {
  const tuile = e.target.closest('.fab-sub-tuile');
  if (!tuile) return;
  validerSubstitution(
    tuile.dataset.produitId,
    tuile.dataset.produitNom,
    tuile.dataset.receptionLigneId,
  );
});

elSubGrid.addEventListener('keydown', e => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const tuile = e.target.closest('.fab-sub-tuile');
  if (tuile) {
    e.preventDefault();
    validerSubstitution(
      tuile.dataset.produitId,
      tuile.dataset.produitNom,
      tuile.dataset.receptionLigneId,
    );
  }
});

function validerSubstitution(produitId, produitNom, receptionLigneId) {
  // Application directe : la DLC vient TOUJOURS de la réception FIFO,
  // jamais d'une saisie manuelle (règle HACCP : stock unifié).
  function appliquerSubstitution(fifoData) {
    if (!fifoData || !fifoData.id) {
      afficherToast(
        '⚠️ Aucun lot en stock pour ce produit. Substitution impossible.',
        'error'
      );
      return;
    }
    const isDluo  = !fifoData.dlc && !!fifoData.dluo;
    const dateVal = isDluo ? fifoData.dluo : fifoData.dlc;
    const memeProduit = produitNom === subNomCourant;
    const suffixe = memeProduit ? '' : ' (substitut)';

    const lot = state.fifoLots.find(l =>
      String(l.recette_ingredient_id ?? l.ingredient_id) === String(subPidCourant)
    );
    if (lot) {
      lot.lot_fifo = {
        reception_ligne_id: fifoData.id,
        numero_lot:         fifoData.numero_lot ?? null,
        dlc:  isDluo ? null : dateVal,
        dluo: isDluo ? dateVal : null,
      };
      lot.produit_id     = Number(produitId);
      lot.produit_nom    = produitNom + suffixe;
      lot.ingredient_nom = produitNom + suffixe;
    }
    state.lotsSubstitues[subPidCourant] = {
      produit_id: produitId,
      nom:        produitNom,
      numero_lot: fifoData.numero_lot ?? null,
    };

    elSubOverlay.hidden = true;

    const dateLabel = isDluo ? 'DLUO' : 'DLC';
    const ligne = elLots.querySelector(`.fab-lot-ligne[data-pid="${subPidCourant}"]`);
    if (ligne) {
      const badgeContenu = memeProduit
        ? `Lot ${escHtml(fifoData.numero_lot ?? '—')} | ${dateLabel} ${formatDate(dateVal)}`
        : `→ ${escHtml(produitNom)} (substitut) | Lot ${escHtml(fifoData.numero_lot ?? '—')} | ${dateLabel} ${formatDate(dateVal)}`;
      ligne.outerHTML = `
        <div class="fab-lot-ligne fab-lot-ligne--substitue" data-pid="${subPidCourant}">
          <span class="fab-lot-check">✓</span>
          <div class="fab-lot-nom">${escHtml(subNomCourant)}</div>
          <div class="fab-lot-info fab-lot-sub-badge">
            ${badgeContenu}
          </div>
        </div>`;
    }
    verifierLotsComplets();
  }

  function recupererFifoEtAppliquer() {
    // Le lot a déjà été récupéré dans subAllProduits — on le retrouve par son
    // reception_ligne_id, pas besoin de recontacter le serveur.
    const lotChoisi = (subAllProduits ?? []).find(
      p => String(p.reception_ligne_id) === String(receptionLigneId)
    );
    if (lotChoisi) {
      appliquerSubstitution({
        id:         lotChoisi.reception_ligne_id,
        numero_lot: lotChoisi.numero_lot,
        dlc:        lotChoisi.dlc,
        dluo:       lotChoisi.dluo,
        poids_kg:   lotChoisi.poids_kg,
      });
    } else {
      appliquerSubstitution(null);
    }
  }

  // Confirmation si le produit sélectionné diffère de l'ingrédient d'origine
  if (produitNom !== subNomCourant) {
    afficherCustomConfirm(
      '⚠️ Substitution',
      `Vous utilisez du "${produitNom}" à la place du "${subNomCourant}".\n\nConfirmer ?`,
      recupererFifoEtAppliquer
    );
  } else {
    recupererFifoEtAppliquer();
  }
}

elSubCancel.addEventListener('click', () => { elSubOverlay.hidden = true; });
elSubOverlay.addEventListener('click', e => {
  if (e.target === elSubOverlay) elSubOverlay.hidden = true;
});

elBtnConfLots.addEventListener('click', () => {
  afficherRecap();
  allerEtape(4);
});

// ── Toast notification ────────────────────────────────────────
function afficherToast(message, type = 'warning') {
  const toast = document.createElement('div');
  toast.className = `fab-toast fab-toast--${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('fab-toast--visible'));
  setTimeout(() => {
    toast.classList.remove('fab-toast--visible');
    setTimeout(() => toast.remove(), 400);
  }, 5000);
}

// ─────────────────────────────────────────────────────────────
//  ÉTAPE 4 : Récapitulatif
// ─────────────────────────────────────────────────────────────
function afficherRecap() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dateFabFmt = new Date().toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });

  // ── DLC théorique du produit fini ────────────────────────
  const dlcJours = parseInt(state.recetteDlcJours, 10) || 3;
  const dlcTheorique = new Date(today);
  dlcTheorique.setDate(dlcTheorique.getDate() + dlcJours);

  // ── DLC minimale parmi les ingrédients FIFO ───────────────
  let dlcIngredientMin = null;
  let ingredientCritique = null;
  (state.fifoLots ?? []).forEach(lot => {
    const dlcStr = lot.lot_fifo?.dlc;
    if (!dlcStr) return;
    const dlcIng = new Date(dlcStr);
    dlcIng.setHours(0, 0, 0, 0);
    if (dlcIngredientMin === null || dlcIng < dlcIngredientMin) {
      dlcIngredientMin = dlcIng;
      ingredientCritique = lot.produit_nom ?? lot.ingredient_nom ?? 'ingrédient';
    }
  });

  // ── Règle HACCP : retenir la date la plus courte ─────────
  let dlcDate = dlcTheorique;
  let dlcReduite = false;
  if (dlcIngredientMin !== null && dlcIngredientMin < dlcTheorique) {
    dlcDate = dlcIngredientMin;
    dlcReduite = true;
  }

  // Stocker en YYYY-MM-DD local (évite le décalage UTC de toISOString)
  const _p = n => String(n).padStart(2, '0');
  state.dlcFinale = `${dlcDate.getFullYear()}-${_p(dlcDate.getMonth() + 1)}-${_p(dlcDate.getDate())}`;

  const dlcFmt = dlcDate.toLocaleDateString('fr-FR', {
    weekday: 'short', day: '2-digit', month: 'long', year: 'numeric',
  });
  const diff = Math.ceil((dlcDate - today) / 86400000);
  const dlcClass = diff > 2 ? 'fab-recap-dlc--ok' : 'fab-recap-dlc--attention';

  // ── Toast d'alerte si DLC réduite ─────────────────────────
  if (dlcReduite) {
    const dlcAfficheeCourte = dlcDate.toLocaleDateString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
    });
    afficherToast(`⚠️ DLC réduite à ${dlcAfficheeCourte} à cause de : ${ingredientCritique}`, 'warning');
  }

  // Poids total fabriqué
  const poidsTotal = state.productionCiblee > 0
    ? `${state.productionCiblee} ${state.rendementUnite}`
    : '—';

  // Map lot par recette_ingredient_id — le numero_lot est toujours préservé,
  // même en cas de substitution (la DLC vient de la réception FIFO du substitut).
  const lotsMap = {};
  (state.fifoLots ?? []).forEach(lot => {
    const riId   = String(lot.recette_ingredient_id ?? lot.ingredient_id);
    const numLot = lot.lot_fifo?.numero_lot ?? '—';
    const sub    = state.lotsSubstitues[riId];
    lotsMap[riId] = sub
      ? `${numLot} (Substitut : ${sub.nom})`
      : numLot;
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
    recette_id:     state.recetteId,
    personnel_id:   Number(personnelId),
    date:           new Date().toLocaleDateString('en-CA'),
    lots:           lotsUtilises,
    dlc_finale:     state.dlcFinale ?? null,
    poids_fabrique: state.productionCiblee > 0 ? state.productionCiblee : null,
  };

  elBtnGenerer.disabled    = true;
  elBtnGenerer.textContent = '⏳ Enregistrement…';

  try {
    const result = await apiFetch('/api/fabrications', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    console.log('[Fabrication] Réponse API :', result);
    elSuccesLot.textContent = result.lot_interne ? `Lot : ${result.lot_interne}` : '';
    elSucces.hidden = false;
    demarrerCompteurSucces();

    // ── Remplissage du gabarit d'impression ──────────────────
    const dlcFormatee = state.dlcFinale
      ? state.dlcFinale.split('-').reverse().join('/')
      : '--/--/----';
    const operateurNom = elOperateur.options[elOperateur.selectedIndex]?.text ?? '';

    document.getElementById('print-nom').textContent = state.recetteNom ?? '';
    document.getElementById('print-poids').textContent = state.productionCiblee > 0
      ? `${state.productionCiblee} ${state.rendementUnite} fabriqués`
      : '— fabriqués';
    document.getElementById('print-dlc').textContent = dlcFormatee;
    document.getElementById('print-lot').textContent = result.lot_interne
      ? `Lot : ${result.lot_interne}`
      : 'Lot : —';
    document.getElementById('print-meta').textContent =
      `Fabriqué le ${new Date().toLocaleDateString('fr-FR')} par ${operateurNom}`;

    const ulIngredients = document.getElementById('print-ingredients');
    ulIngredients.innerHTML = '';
    (state.fifoLots ?? []).forEach(lot => {
      const li = document.createElement('li');
      const nom    = lot.produit_nom ?? lot.ingredient_nom ?? '?';
      const numLot = lot.lot_fifo?.numero_lot ?? 'N/A';

      // DLC de l'ingrédient — format court DD/MM/AA pour gagner de la place
      let dlcIng = 'N/A';
      if (lot.lot_fifo?.dlc) {
        dlcIng = new Date(lot.lot_fifo.dlc).toLocaleDateString('fr-FR', {
          day: '2-digit', month: '2-digit', year: '2-digit',
        });
      }

      // Quantité — dans state.quantities[produit_id], jointure via state.ingredients
      const riId  = lot.recette_ingredient_id ?? lot.ingredient_id;
      const ing   = state.ingredients.find(i => String(i.recette_ingredient_id) === String(riId));
      const qte   = ing ? (state.quantities[ing.produit_id] ?? '') : '';
      const unite = ing?.unite ?? '';
      const qteTexte = qte !== '' ? `${qte}${unite} ` : '';

      li.textContent = `${qteTexte}${nom} (L:${numLot} | DLC:${dlcIng})`;
      ulIngredients.appendChild(li);
    });

    // ── Déclenchement impression (léger délai pour rendu DOM) ─
    setTimeout(() => window.print(), 100);
  } catch (err) {
    elErreur.textContent = `Erreur : ${err.message}`;
    elErreur.hidden = false;
  } finally {
    elBtnGenerer.disabled    = false;
    elBtnGenerer.textContent = '🖨 Générer & imprimer';
  }
});

// ─────────────────────────────────────────────────────────────
//  Compte à rebours 20 s — retour hub automatique (écran succès)
// ─────────────────────────────────────────────────────────────
let _timerSucces = null;

function demarrerCompteurSucces() {
  let restant = 20;
  elCountdownSec.textContent = restant;
  elSuccesCountdown.hidden = false;
  _timerSucces = setInterval(() => {
    restant--;
    elCountdownSec.textContent = restant;
    if (restant <= 0) {
      arreterCompteurSucces();
      window.location.href = '/production-hub.html';
    }
  }, 1000);
}

function arreterCompteurSucces() {
  clearInterval(_timerSucces);
  _timerSucces = null;
  elSuccesCountdown.hidden = true;
}

// ─────────────────────────────────────────────────────────────
//  Écran de succès — actions post-impression
// ─────────────────────────────────────────────────────────────
elBtnHub.addEventListener('click', () => {
  arreterCompteurSucces();
  window.location.href = '/production-hub.html';
});

elBtnMemeRecette.addEventListener('click', async () => {
  arreterCompteurSucces();
  elSucces.hidden = true;
  await chargerIngredientsRecette(state.recetteId);
  allerEtape(2);
});

elBtnNouvelleFab.addEventListener('click', () => {
  arreterCompteurSucces();
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
//  Modale Gestion des recettes
// ─────────────────────────────────────────────────────────────
const elGrModalOverlay = document.getElementById('gr-modal-overlay');
const elGrModalClose   = document.getElementById('gr-modal-close');
const elGrModalSearch  = document.getElementById('gr-modal-search');
const elGrModalListe   = document.getElementById('gr-modal-liste');
const elGrModalCreer   = document.getElementById('gr-modal-btn-creer');
const elBtnAdminRec    = document.getElementById('fab-btn-admin-recettes');

function rendreListeGestionRecettes(filtre = '') {
  if (!elGrModalListe) return;
  const q = filtre.trim().toLowerCase();
  const liste = q
    ? recettes.filter(r => (r.nom || '').toLowerCase().includes(q))
    : recettes;

  if (liste.length === 0) {
    elGrModalListe.innerHTML = `<div class="gr-modal-vide">${
      q ? 'Aucune recette ne correspond.' : 'Aucune recette enregistrée.'
    }</div>`;
    return;
  }

  elGrModalListe.innerHTML = liste.map(r => `
    <button type="button" class="gr-modal-item" data-id="${r.id}" role="listitem">
      <span class="gr-modal-item-nom">${escHtml(r.nom)}</span>
      <span class="gr-modal-item-dlc">DLC J+${r.dlc_jours ?? '?'}</span>
      <span class="gr-modal-item-fleche" aria-hidden="true">›</span>
    </button>
  `).join('');
}

function ouvrirModaleGestionRecettes() {
  if (!elGrModalOverlay) return;
  elGrModalSearch.value = '';
  rendreListeGestionRecettes('');
  elGrModalOverlay.hidden = false;
  setTimeout(() => elGrModalSearch.focus(), 50);
}

function fermerModaleGestionRecettes() {
  if (!elGrModalOverlay) return;
  elGrModalOverlay.hidden = true;
}

if (elBtnAdminRec) {
  elBtnAdminRec.addEventListener('click', ouvrirModaleGestionRecettes);
}
if (elGrModalClose) {
  elGrModalClose.addEventListener('click', fermerModaleGestionRecettes);
}
if (elGrModalOverlay) {
  elGrModalOverlay.addEventListener('click', e => {
    if (e.target === elGrModalOverlay) fermerModaleGestionRecettes();
  });
}
if (elGrModalSearch) {
  elGrModalSearch.addEventListener('input', e => {
    rendreListeGestionRecettes(e.target.value);
  });
}
if (elGrModalListe) {
  elGrModalListe.addEventListener('click', e => {
    const item = e.target.closest('.gr-modal-item[data-id]');
    if (!item) return;
    window.location.href = `/admin-recettes.html?id=${encodeURIComponent(item.dataset.id)}`;
  });
}
if (elGrModalCreer) {
  elGrModalCreer.addEventListener('click', () => {
    window.location.href = '/admin-recettes.html';
  });
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && elGrModalOverlay && !elGrModalOverlay.hidden) {
    fermerModaleGestionRecettes();
  }
});

// ─────────────────────────────────────────────────────────────
//  Init
// ─────────────────────────────────────────────────────────────
async function init() {
  await Promise.all([chargerRecettes(), chargerPersonnel()]);
}

init();

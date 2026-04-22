'use strict';
/* ============================================================
   cuisson.js — Module Cuisson (wizard 3 étapes)
   Au Comptoir des Lilas — Mets Carnés Holding

   Flux :
     Étape 1 — sélection opérateur (grille de tuiles)
     Étape 2 — sélection produit (grille de tuiles, FIFO ⭐)
              + sélecteur de lot si ≥ 2 réceptions
     Étape 3 — quantité / heures / température + conformité HACCP
   ============================================================ */

const TEMP_CIBLE = 63.0;

// ── Helpers ────────────────────────────────────────────────
function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function apiFetch(url, options = {}) {
  const res = await fetch(url, { cache: 'no-store', ...options });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    let msg = txt;
    try {
      const j = JSON.parse(txt);
      if (j && j.detail) msg = j.detail;
    } catch { /* noop */ }
    throw new Error(msg || `HTTP ${res.status}`);
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

function formatTemp(v) {
  if (v === null || v === undefined || v === '') return '—';
  return `${parseFloat(v).toFixed(1)} °C`;
}

function todayISO() {
  const d = new Date();
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function initialePrenom(prenom) {
  const p = (prenom ?? '').trim();
  if (!p) return '?';
  return p.charAt(0).toUpperCase();
}

// ── Références DOM ─────────────────────────────────────────
const $ = id => document.getElementById(id);

const elHorloge      = $('cu-horloge');
const elSteps        = [null, $('cu-step-1'), $('cu-step-2'), $('cu-step-3')];
const elDots         = document.querySelectorAll('.cu-dot');
const elLines        = document.querySelectorAll('.cu-dot-line');
const elBandeau      = $('cu-bandeau');
const elBandeauOp    = $('cu-bandeau-op');
const elBandeauProd  = $('cu-bandeau-prod');

const elOperateursGrid = $('cu-operateurs-grid');

const elProdSearch   = $('cu-produit-search');
const elProduitsGrid = $('cu-produits-grid');
const elLotWrap      = $('cu-lot-wrap');
const elLotSelect    = $('cu-lot-select');
const elLotCompteur  = $('cu-lot-compteur');
const elProdLot      = $('cu-produit-lot');
const elProdDlc      = $('cu-produit-dlc');
const elBtnHisto     = $('cu-btn-historique');
const elBtnStep2Next = $('cu-btn-step2-next');

const elDate         = $('cu-date');
const elQuantite     = $('cu-quantite');
const elUnite        = $('cu-unite');
const elHeureDebut   = $('cu-heure-debut');
const elHeureFin     = $('cu-heure-fin');
const elTemperature  = $('cu-temperature');
const elConformite   = $('cu-conformite');
const elConfTxt      = $('cu-conformite-texte');
const elActionWrap   = $('cu-action-wrap');
const elAction       = $('cu-action');
const elErreur       = $('cu-erreur');
const elForm         = $('cu-form');
const elBtnSave      = $('cu-btn-save');
const elHisto        = $('cu-histo');
const elToast        = $('cu-toast');
const elModal        = $('cu-modal-histo');
const elModalTitre   = $('cu-modal-titre');
const elModalCorps   = $('cu-modal-corps');
const elModalClose   = $('cu-modal-close');

// ── Horloge ────────────────────────────────────────────────
(function majHorloge() {
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
  setTimeout(majHorloge, 1000);
})();

// ── Inactivité (5 min → hub) ───────────────────────────────
let timerInactivite;
function resetInactivite() {
  clearTimeout(timerInactivite);
  timerInactivite = setTimeout(() => {
    window.location.href = '/hub.html';
  }, 5 * 60 * 1000);
}
['click', 'touchstart', 'input', 'keydown'].forEach(ev =>
  document.addEventListener(ev, resetInactivite, { capture: true, passive: true })
);
resetInactivite();

// ── État ───────────────────────────────────────────────────
const state = {
  step:            1,
  personnel:       [],
  produits:        [],
  operateurChoisi: null,   // { id, prenom }
  produitChoisi:   null,   // { id, nom, numero_lot, dlc, reception_ligne_id }
  lotsProduit:     [],
  fifoLotId:       null,
};

// ── Navigation wizard ──────────────────────────────────────
function goStep(n) {
  state.step = n;
  for (let i = 1; i <= 3; i++) {
    elSteps[i].hidden = (i !== n);
    elSteps[i].classList.toggle('cu-step--active', i === n);
  }
  elDots.forEach(d => {
    const s = Number(d.dataset.step);
    d.classList.toggle('cu-dot--active', s === n);
    d.classList.toggle('cu-dot--done', s < n);
  });
  elLines.forEach(l => {
    const s = Number(l.dataset.line);
    l.dataset.done = s < n ? '1' : '0';
  });
  majBandeau();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function majBandeau() {
  const parts = [];
  if (state.operateurChoisi) parts.push(`👤 ${state.operateurChoisi.prenom}`);
  if (state.produitChoisi)   parts.push(`📦 ${state.produitChoisi.nom}`);
  elBandeauOp.textContent   = parts[0] ?? '';
  elBandeauProd.textContent = parts[1] ?? '';
  elBandeau.hidden = parts.length === 0;
}

// ── Init : personnel, catalogue, historique ───────────────
async function init() {
  elDate.value = todayISO();

  await Promise.all([
    chargerPersonnel(),
    chargerProduits(),
    chargerHistorique(),
  ]);

  afficherOperateurs();
  afficherProduits();
}

async function chargerPersonnel() {
  try {
    const personnel = await apiFetch('/api/admin/personnel');
    state.personnel = (personnel ?? [])
      .filter(p => p.actif !== 0 && p.actif !== false)
      .sort((a, b) => (a.prenom ?? '').localeCompare(b.prenom ?? '', 'fr'));
  } catch (err) {
    state.personnel = [];
    console.warn('[cuisson] Personnel KO :', err);
  }
}

async function chargerProduits() {
  try {
    const [brut, enStock] = await Promise.all([
      apiFetch('/api/produits?type=brut'),
      apiFetch('/api/produits?type=brut&en_stock=true').catch(() => []),
    ]);

    const stockMap = new Map();
    (enStock ?? []).forEach(p => {
      stockMap.set(p.id, {
        numero_lot:         p.numero_lot ?? null,
        dlc:                p.dlc ?? null,
        reception_ligne_id: p.reception_ligne_id ?? null,
      });
    });

    state.produits = (brut ?? []).map(p => {
      const s = stockMap.get(p.id);
      return {
        ...p,
        en_stock:           !!s,
        numero_lot:         s?.numero_lot ?? null,
        dlc:                s?.dlc ?? null,
        reception_ligne_id: s?.reception_ligne_id ?? null,
      };
    });
  } catch (err) {
    state.produits = [];
    console.warn('[cuisson] Produits KO :', err);
  }
}

// ═══ Étape 1 : Opérateurs ═══════════════════════════════
function afficherOperateurs() {
  if (!state.personnel.length) {
    elOperateursGrid.innerHTML = `<div class="cu-tuiles-vide">Aucun opérateur actif.</div>`;
    return;
  }
  elOperateursGrid.innerHTML = state.personnel.map(p => `
    <button type="button" class="cu-tuile" role="listitem"
            data-op-id="${p.id}" data-op-prenom="${escHtml(p.prenom)}">
      <div class="cu-tuile-icone">${escHtml(initialePrenom(p.prenom))}</div>
      <div class="cu-tuile-nom">${escHtml(p.prenom)}</div>
    </button>
  `).join('');
}

elOperateursGrid.addEventListener('click', e => {
  const tuile = e.target.closest('.cu-tuile[data-op-id]');
  if (!tuile) return;
  state.operateurChoisi = {
    id:     Number(tuile.dataset.opId),
    prenom: tuile.dataset.opPrenom,
  };
  elOperateursGrid.querySelectorAll('.cu-tuile').forEach(t =>
    t.classList.toggle('cu-tuile--selected', t === tuile));
  setTimeout(() => goStep(2), 150);
});

// ═══ Étape 2 : Produits ═════════════════════════════════
function produitsFiltres() {
  const needle = (elProdSearch.value || '').trim().toUpperCase();
  let liste = state.produits.slice();
  if (needle) {
    liste = liste.filter(p => (p.nom ?? '').toUpperCase().includes(needle));
  }
  liste.sort((a, b) => {
    if (a.en_stock !== b.en_stock) return a.en_stock ? -1 : 1;
    if (a.en_stock && b.en_stock) {
      const da = a.dlc ? new Date(a.dlc).getTime() : Infinity;
      const db = b.dlc ? new Date(b.dlc).getTime() : Infinity;
      if (da !== db) return da - db;
    }
    return (a.nom ?? '').localeCompare(b.nom ?? '', 'fr');
  });
  return liste;
}

function afficherProduits() {
  const liste = produitsFiltres();
  if (!liste.length) {
    elProduitsGrid.innerHTML = `<div class="cu-tuiles-vide">Aucun produit trouvé.</div>`;
    return;
  }
  elProduitsGrid.innerHTML = liste.map(p => {
    const classes = ['cu-tuile'];
    if (p.en_stock) classes.push('cu-tuile--stock');
    if (state.produitChoisi && state.produitChoisi.id === p.id) classes.push('cu-tuile--selected');
    const badge = p.en_stock ? `<div class="cu-tuile-badge">⭐ EN STOCK</div>` : '';
    const dlc   = p.en_stock && p.dlc
      ? `<div class="cu-tuile-dlc">DLC ${formatDate(p.dlc)}</div>` : '';
    return `
      <button type="button" class="${classes.join(' ')}" role="listitem"
              data-prod-id="${p.id}" data-prod-nom="${escHtml(p.nom)}">
        ${badge}
        <div class="cu-tuile-icone">🥩</div>
        <div class="cu-tuile-nom">${escHtml(p.nom)}</div>
        ${dlc}
      </button>
    `;
  }).join('');
}

elProdSearch.addEventListener('input', afficherProduits);

elProduitsGrid.addEventListener('click', e => {
  const tuile = e.target.closest('.cu-tuile[data-prod-id]');
  if (!tuile) return;
  const id  = Number(tuile.dataset.prodId);
  const nom = tuile.dataset.prodNom;
  selectionnerProduit(id, nom);
});

async function selectionnerProduit(id, nom) {
  state.produitChoisi = { id, nom, numero_lot: null, dlc: null, reception_ligne_id: null };
  state.lotsProduit = [];
  state.fifoLotId   = null;

  // MAJ visuelle des tuiles
  elProduitsGrid.querySelectorAll('.cu-tuile').forEach(t => {
    t.classList.toggle('cu-tuile--selected', Number(t.dataset.prodId) === id);
  });

  // Reset panneau lot
  elLotWrap.hidden = true;
  elLotSelect.innerHTML = '';
  elProdLot.innerHTML = '';
  elProdDlc.textContent = '';

  try {
    const receptions = await apiFetch(`/api/cuisson/produits/${id}/receptions?limit=50`);
    state.lotsProduit = receptions ?? [];

    if (state.lotsProduit.length === 0) {
      // Pas de réception enregistrée — on avance quand même
      majBandeau();
      setTimeout(() => goStep(3), 120);
      return;
    }

    // FIFO : DLC la plus courte, puis réception la plus ancienne
    const lotsAvecIdx = state.lotsProduit.map((lot, idx) => ({ lot, idx }));
    lotsAvecIdx.sort((a, b) => {
      const da = a.lot.dlc ? new Date(a.lot.dlc).getTime() : Infinity;
      const db = b.lot.dlc ? new Date(b.lot.dlc).getTime() : Infinity;
      if (da !== db) return da - db;
      const ra = a.lot.date_reception ? new Date(a.lot.date_reception).getTime() : Infinity;
      const rb = b.lot.date_reception ? new Date(b.lot.date_reception).getTime() : Infinity;
      return ra - rb;
    });
    state.fifoLotId = lotsAvecIdx[0].lot.reception_ligne_id;

    if (state.lotsProduit.length === 1) {
      appliquerLotChoisi(state.lotsProduit[0]);
      majBandeau();
      setTimeout(() => goStep(3), 120);
    } else {
      // Plusieurs lots → on affiche le sélecteur, l'utilisateur clique "Suivant"
      elLotWrap.hidden = false;
      elLotCompteur.textContent = `(${state.lotsProduit.length} réceptions)`;
      elLotSelect.innerHTML = lotsAvecIdx.map(({ lot }) => {
        const estFifo = lot.reception_ligne_id === state.fifoLotId;
        const label = [
          estFifo ? '⭐ FIFO —' : '',
          `Lot ${lot.numero_lot ?? '—'}`,
          `· DLC ${formatDate(lot.dlc)}`,
          `· reçu ${formatDate(lot.date_reception)}`,
          lot.fournisseur_nom ? `· ${lot.fournisseur_nom}` : '',
        ].filter(Boolean).join(' ');
        return `<option value="${lot.reception_ligne_id}"${estFifo ? ' selected' : ''}>${escHtml(label)}</option>`;
      }).join('');
      const lotFifo = state.lotsProduit.find(l => l.reception_ligne_id === state.fifoLotId);
      appliquerLotChoisi(lotFifo);
      majBandeau();
      elLotWrap.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  } catch (err) {
    console.warn('[cuisson] Historique réceptions KO :', err);
    majBandeau();
    setTimeout(() => goStep(3), 120);
  }
}

function appliquerLotChoisi(lot) {
  if (!lot) return;
  state.produitChoisi.numero_lot         = lot.numero_lot ?? null;
  state.produitChoisi.dlc                = lot.dlc ?? null;
  state.produitChoisi.reception_ligne_id = lot.reception_ligne_id ?? null;

  const estFifo = lot.reception_ligne_id === state.fifoLotId;
  const badgeFifo = estFifo && state.lotsProduit.length > 1
    ? ' <span class="cu-fifo-badge">⭐ FIFO</span>'
    : '';
  elProdLot.innerHTML = lot.numero_lot
    ? `Lot : ${escHtml(lot.numero_lot)}${badgeFifo}`
    : '';
  elProdDlc.textContent = lot.dlc ? `DLC : ${formatDate(lot.dlc)}` : '';
}

elLotSelect.addEventListener('change', () => {
  const recId = Number(elLotSelect.value);
  const lot = state.lotsProduit.find(l => l.reception_ligne_id === recId);
  if (lot) appliquerLotChoisi(lot);
});

elBtnStep2Next.addEventListener('click', () => goStep(3));

// Historique réception produit — modale
elBtnHisto.addEventListener('click', async () => {
  if (!state.produitChoisi) return;
  const { id, nom } = state.produitChoisi;
  elModalTitre.textContent = `Historique — ${nom}`;
  elModalCorps.innerHTML = `<div class="cu-histo-vide">Chargement…</div>`;
  elModal.hidden = false;

  try {
    const receptions = await apiFetch(`/api/cuisson/produits/${id}/receptions?limit=20`);
    if (!receptions.length) {
      elModalCorps.innerHTML = `<div class="cu-histo-vide">Aucune réception enregistrée pour ce produit.</div>`;
      return;
    }
    elModalCorps.innerHTML = receptions.map(r => `
      <div class="cu-histo-ligne">
        <div class="cu-histo-date">${formatDate(r.date_reception)}</div>
        <div class="cu-histo-info">
          <strong>Lot :</strong> ${escHtml(r.numero_lot ?? '—')}
          &nbsp;·&nbsp; <strong>DLC :</strong> ${formatDate(r.dlc)}
          ${r.fournisseur_nom ? `<br><small>${escHtml(r.fournisseur_nom)}</small>` : ''}
          ${r.poids_kg ? `&nbsp;·&nbsp;${r.poids_kg} kg` : ''}
          ${r.reception_id ? `<br><a href="/reception-detail.html?id=${r.reception_id}" style="color:#6B3A1F;font-weight:700">→ Fiche réception</a>` : ''}
        </div>
      </div>
    `).join('');
  } catch (err) {
    elModalCorps.innerHTML = `<div class="cu-erreur">Erreur : ${escHtml(err.message)}</div>`;
  }
});

elModalClose.addEventListener('click', () => { elModal.hidden = true; });
elModal.addEventListener('click', e => {
  if (e.target === elModal) elModal.hidden = true;
});

// ═══ Boutons "← Retour" ═════════════════════════════════
document.querySelectorAll('[data-back]').forEach(btn => {
  btn.addEventListener('click', () => {
    const n = Number(btn.dataset.back);
    if (n >= 1 && n <= 3) goStep(n);
  });
});

// ═══ Étape 3 : formulaire ═══════════════════════════════
// ── Heure fin — boutons rapides ─────────────────────────
const elQuickFin = $('cu-quick-fin');

function ajouterMinutes(hhmm, minutes) {
  const [h, m] = (hhmm || '').split(':').map(Number);
  if (isNaN(h) || isNaN(m)) return null;
  const total = h * 60 + m + minutes;
  const hh = Math.floor((total % (24 * 60)) / 60);
  const mm = total % 60;
  const p = n => String(n).padStart(2, '0');
  return `${p(hh)}:${p(mm)}`;
}

elQuickFin.addEventListener('click', e => {
  const btn = e.target.closest('.cu-quick-btn[data-minutes]');
  if (!btn) return;
  if (!elHeureDebut.value) {
    afficherErreur('Renseignez d\u2019abord l\u2019heure de d\u00e9but.');
    return;
  }
  const minutes = Number(btn.dataset.minutes);
  const fin = ajouterMinutes(elHeureDebut.value, minutes);
  if (fin) {
    elHeureFin.value = fin;
    elQuickFin.querySelectorAll('.cu-quick-btn').forEach(b =>
      b.classList.toggle('cu-quick-btn--actif', b === btn));
    elErreur.hidden = true;
  }
});

elHeureFin.addEventListener('input', () => {
  elQuickFin.querySelectorAll('.cu-quick-btn').forEach(b =>
    b.classList.remove('cu-quick-btn--actif'));
});
elHeureDebut.addEventListener('input', () => {
  elQuickFin.querySelectorAll('.cu-quick-btn').forEach(b =>
    b.classList.remove('cu-quick-btn--actif'));
});

// ── Conformité température — live ────────────────────────
function majConformite() {
  const v = parseFloat(elTemperature.value);
  if (isNaN(v)) {
    elConformite.hidden = true;
    elActionWrap.hidden = true;
    return;
  }
  const ok = v >= TEMP_CIBLE;
  elConformite.hidden = false;
  elConformite.classList.toggle('cu-conformite--ok', ok);
  elConformite.classList.toggle('cu-conformite--ko', !ok);
  elConfTxt.textContent = ok
    ? `✓ Conforme — ${v.toFixed(1)} °C ≥ ${TEMP_CIBLE} °C`
    : `⚠ Non conforme — ${v.toFixed(1)} °C < ${TEMP_CIBLE} °C — action corrective requise`;
  elActionWrap.hidden = ok;
}
elTemperature.addEventListener('input', majConformite);

// ── Soumission ───────────────────────────────────────────
elForm.addEventListener('submit', async e => {
  e.preventDefault();
  elErreur.hidden = true;

  if (!state.operateurChoisi) {
    goStep(1);
    return afficherErreur('Veuillez sélectionner un opérateur.');
  }
  if (!state.produitChoisi) {
    goStep(2);
    return afficherErreur('Veuillez sélectionner un produit.');
  }
  const qte = parseFloat(elQuantite.value);
  if (isNaN(qte) || qte <= 0) {
    return afficherErreur('Quantité requise (> 0).');
  }
  if (!elHeureDebut.value || !elHeureFin.value) {
    return afficherErreur('Heures de début et fin requises.');
  }
  const temp = parseFloat(elTemperature.value);
  if (isNaN(temp)) {
    return afficherErreur('Température de sortie requise.');
  }
  if (temp < TEMP_CIBLE && !elAction.value.trim()) {
    return afficherErreur('Action corrective obligatoire si T° < 63 °C.');
  }

  const payload = {
    type_cuisson:       'rotissoire',
    date_cuisson:       elDate.value,
    personnel_id:       Number(state.operateurChoisi.id),
    produit_id:         Number(state.produitChoisi.id),
    reception_ligne_id: state.produitChoisi.reception_ligne_id
                         ? Number(state.produitChoisi.reception_ligne_id) : null,
    quantite:           qte,
    unite:              elUnite.value || 'kg',
    heure_debut:        elHeureDebut.value,
    heure_fin:          elHeureFin.value,
    temperature_sortie: temp,
    action_corrective:  elAction.value.trim() || null,
  };

  elBtnSave.disabled    = true;
  elBtnSave.textContent = '⏳ Enregistrement…';

  try {
    const res = await apiFetch('/api/cuisson/enregistrements', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    afficherToast(res.conforme ? '✓ Cuisson enregistrée' : '⚠ Cuisson enregistrée — non conforme', res.conforme);
    resetWizard();
    await chargerHistorique();
  } catch (err) {
    afficherErreur(err.message);
  } finally {
    elBtnSave.disabled    = false;
    elBtnSave.textContent = '✓ Enregistrer la cuisson';
  }
});

function afficherErreur(msg) {
  elErreur.textContent = msg;
  elErreur.hidden = false;
  elErreur.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function afficherToast(message, ok = true) {
  elToast.textContent = message;
  elToast.classList.toggle('cu-toast--ko', !ok);
  elToast.hidden = false;
  requestAnimationFrame(() => elToast.classList.add('cu-toast--visible'));
  setTimeout(() => {
    elToast.classList.remove('cu-toast--visible');
    setTimeout(() => { elToast.hidden = true; }, 300);
  }, 3500);
}

function resetWizard() {
  state.operateurChoisi = null;
  state.produitChoisi   = null;
  state.lotsProduit     = [];
  state.fifoLotId       = null;

  elOperateursGrid.querySelectorAll('.cu-tuile').forEach(t =>
    t.classList.remove('cu-tuile--selected'));
  elProduitsGrid.querySelectorAll('.cu-tuile').forEach(t =>
    t.classList.remove('cu-tuile--selected'));
  elProdSearch.value = '';
  afficherProduits();

  elLotWrap.hidden = true;
  elLotSelect.innerHTML = '';
  elProdLot.innerHTML = '';
  elProdDlc.textContent = '';

  elQuantite.value    = '';
  elHeureDebut.value  = '';
  elHeureFin.value    = '';
  elTemperature.value = '';
  elAction.value      = '';
  elConformite.hidden = true;
  elActionWrap.hidden = true;
  elDate.value        = todayISO();
  elQuickFin.querySelectorAll('.cu-quick-btn').forEach(b =>
    b.classList.remove('cu-quick-btn--actif'));

  goStep(1);
}

// ── Historique récent ────────────────────────────────────
async function chargerHistorique() {
  elHisto.innerHTML = `<div class="cu-histo-vide">Chargement…</div>`;
  try {
    const rows = await apiFetch('/api/cuisson/enregistrements?type=rotissoire&limit=20');
    if (!rows.length) {
      elHisto.innerHTML = `<div class="cu-histo-vide">Aucune cuisson enregistrée pour l'instant.</div>`;
      return;
    }
    elHisto.innerHTML = rows.map(r => {
      const ok = !!r.conforme;
      const qte = r.quantite != null ? `${r.quantite} ${escHtml(r.unite ?? '')}` : '';
      return `
        <div class="cu-histo-ligne ${ok ? '' : 'cu-histo-ligne--ko'}">
          <div class="cu-histo-date">
            ${formatDate(r.date_cuisson)}<br>
            <small>${escHtml(r.heure_debut ?? '')}→${escHtml(r.heure_fin ?? '')}</small>
          </div>
          <div class="cu-histo-info">
            <strong>${escHtml(r.produit_nom ?? '—')}</strong>
            ${qte ? ` · ${qte}` : ''}
            <br>
            <small>
              Opérateur : ${escHtml(r.personnel_prenom ?? '—')}
              ${r.action_corrective ? `· Action : ${escHtml(r.action_corrective)}` : ''}
            </small>
          </div>
          <div class="cu-histo-temp ${ok ? 'cu-histo-temp--ok' : 'cu-histo-temp--ko'}">
            ${formatTemp(r.temperature_sortie)}
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    elHisto.innerHTML = `<div class="cu-erreur">Erreur : ${escHtml(err.message)}</div>`;
  }
}

// ── Go ──────────────────────────────────────────────────
init();

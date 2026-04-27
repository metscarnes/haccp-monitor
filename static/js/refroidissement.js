'use strict';
/* ============================================================
   refroidissement.js — Module Refroidissement (wizard 3 étapes)
   Au Comptoir des Lilas — Mets Carnés Holding

   Règle HACCP :
     - T° à cœur ≤ +10 °C
     - Durée ≤ 2 h
     - Si durée > 2 h ET T° > 10 °C → JETER les produits
   ============================================================ */

const TEMP_CIBLE     = 10.0;     // °C max
const DUREE_MAX_MIN  = 120;      // 2 h

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
    try { const j = JSON.parse(txt); if (j && j.detail) msg = j.detail; } catch { /* noop */ }
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
function formatDuree(min) {
  if (min == null) return '—';
  const h = Math.floor(min / 60), m = min % 60;
  return h ? `${h}h${String(m).padStart(2, '0')}` : `${m} min`;
}
function todayISO() {
  const d = new Date(), p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
function initialePrenom(prenom) {
  const p = (prenom ?? '').trim();
  return p ? p.charAt(0).toUpperCase() : '?';
}
function ajouterMinutes(hhmm, minutes) {
  const [h, m] = (hhmm || '').split(':').map(Number);
  if (isNaN(h) || isNaN(m)) return null;
  const total = h * 60 + m + minutes;
  const hh = Math.floor((total % (24 * 60)) / 60);
  const mm = total % 60;
  const p = n => String(n).padStart(2, '0');
  return `${p(hh)}:${p(mm)}`;
}
function dureeMinutes(debut, fin) {
  const [h1, m1] = (debut || '').split(':').map(Number);
  const [h2, m2] = (fin   || '').split(':').map(Number);
  if ([h1, m1, h2, m2].some(isNaN)) return null;
  let d = h2 * 60 + m2 - (h1 * 60 + m1);
  if (d <= 0) d += 24 * 60;
  return d;
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
const elProdSearch     = $('cu-produit-search');
const elProduitsGrid   = $('cu-produits-grid');

const elDate         = $('cu-date');
const elHeureDebut   = $('cu-heure-debut');
const elHeureFin     = $('cu-heure-fin');
const elQuickFin     = $('cu-quick-fin');
const elTempInitiale = $('cu-temperature-initiale');
const elTemperature  = $('cu-temperature');
const elConformite   = $('cu-conformite');
const elConfTxt      = $('cu-conformite-texte');
const elJeter        = $('cu-jeter');
const elActionWrap   = $('cu-action-wrap');
const elAction       = $('cu-action');
const elErreur       = $('cu-erreur');
const elForm         = $('cu-form');
const elBtnSave      = $('cu-btn-save');
const elHisto        = $('cu-histo');
const elToast        = $('cu-toast');

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
  operateurChoisi: null,
  produitChoisi:   null,
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

// ── Init ───────────────────────────────────────────────────
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
    console.warn('[refroidissement] Personnel KO :', err);
  }
}

async function chargerProduits() {
  try {
    state.produits = await apiFetch('/api/refroidissement/produits') ?? [];
  } catch (err) {
    state.produits = [];
    console.warn('[refroidissement] Produits cuisson KO :', err);
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
  let liste = [...state.produits];
  if (needle) liste = liste.filter(p => (p.nom ?? '').toUpperCase().includes(needle));
  return liste;
}

function afficherProduits() {
  const liste = produitsFiltres();
  if (!liste.length) {
    elProduitsGrid.innerHTML = `<div class="cu-tuiles-vide">Aucun produit cuit. Enregistrez d'abord une cuisson.</div>`;
    return;
  }
  elProduitsGrid.innerHTML = liste.map(p => {
    const classes = ['cu-tuile'];
    if (state.produitChoisi && state.produitChoisi.id === p.id) classes.push('cu-tuile--selected');
    const meta = p.derniere_cuisson_date
      ? `<div class="cu-tuile-dlc">Dernière cuisson : ${formatDate(p.derniere_cuisson_date)}</div>`
      : '';
    return `
      <button type="button" class="${classes.join(' ')}" role="listitem"
              data-prod-id="${p.id}"
              data-prod-nom="${escHtml(p.nom)}"
              data-cuisson-id="${p.dernier_cuisson_id ?? ''}">
        <div class="cu-tuile-icone">🥩</div>
        <div class="cu-tuile-nom">${escHtml(p.nom)}</div>
        ${meta}
      </button>
    `;
  }).join('');
}

elProdSearch.addEventListener('input', afficherProduits);

elProduitsGrid.addEventListener('click', e => {
  const tuile = e.target.closest('.cu-tuile[data-prod-id]');
  if (!tuile) return;
  state.produitChoisi = {
    id:         Number(tuile.dataset.prodId),
    nom:        tuile.dataset.prodNom,
    cuisson_id: tuile.dataset.cuissonId ? Number(tuile.dataset.cuissonId) : null,
  };
  elProduitsGrid.querySelectorAll('.cu-tuile').forEach(t =>
    t.classList.toggle('cu-tuile--selected', t === tuile));
  majBandeau();
  setTimeout(() => goStep(3), 150);
});

// ═══ Boutons "← Retour" ═════════════════════════════════
document.querySelectorAll('[data-back]').forEach(btn => {
  btn.addEventListener('click', () => {
    const n = Number(btn.dataset.back);
    if (n >= 1 && n <= 3) goStep(n);
  });
});

// ═══ Étape 3 : formulaire ═══════════════════════════════
// Heure début — pré-remplir avec l'heure courante au 1er affichage de l'étape
function preremplirHeureDebut() {
  if (elHeureDebut.value) return;
  const d = new Date(), p = n => String(n).padStart(2, '0');
  elHeureDebut.value = `${p(d.getHours())}:${p(d.getMinutes())}`;
  // Heure fin par défaut = +2h
  if (!elHeureFin.value) {
    elHeureFin.value = ajouterMinutes(elHeureDebut.value, DUREE_MAX_MIN);
    elQuickFin.querySelector('[data-minutes="120"]')?.classList.add('cu-quick-btn--actif');
  }
  majConformite();
}

elQuickFin.addEventListener('click', e => {
  const btn = e.target.closest('.cu-quick-btn[data-minutes]');
  if (!btn) return;
  if (!elHeureDebut.value) {
    afficherErreur("Renseignez d'abord l'heure de mise en refroidissement.");
    return;
  }
  const minutes = Number(btn.dataset.minutes);
  const fin = ajouterMinutes(elHeureDebut.value, minutes);
  if (fin) {
    elHeureFin.value = fin;
    elQuickFin.querySelectorAll('.cu-quick-btn').forEach(b =>
      b.classList.toggle('cu-quick-btn--actif', b === btn));
    elErreur.hidden = true;
    majConformite();
  }
});

[elHeureDebut, elHeureFin].forEach(el =>
  el.addEventListener('input', () => {
    elQuickFin.querySelectorAll('.cu-quick-btn').forEach(b =>
      b.classList.remove('cu-quick-btn--actif'));
    majConformite();
  })
);

// ── Conformité live (T° + durée) ─────────────────────────
function majConformite() {
  const t = parseFloat(elTemperature.value);
  const d = dureeMinutes(elHeureDebut.value, elHeureFin.value);
  const tValide = !isNaN(t);
  const dValide = d != null;

  if (!tValide && !dValide) {
    elConformite.hidden = true;
    elJeter.hidden = true;
    elActionWrap.hidden = true;
    return;
  }

  const tempOk  = tValide ? t <= TEMP_CIBLE : true;
  const dureeOk = dValide ? d <= DUREE_MAX_MIN : true;
  const ok = tempOk && dureeOk && tValide && dValide;
  const jeter = tValide && dValide && !tempOk && !dureeOk;

  elConformite.hidden = false;
  elConformite.classList.toggle('cu-conformite--ok', ok);
  elConformite.classList.toggle('cu-conformite--ko', !ok);

  const partsKo = [];
  if (tValide && !tempOk) partsKo.push(`T° ${t.toFixed(1)} °C > ${TEMP_CIBLE} °C`);
  if (dValide && !dureeOk) partsKo.push(`durée ${formatDuree(d)} > 2 h`);

  if (ok) {
    elConfTxt.textContent =
      `✓ Conforme — ${t.toFixed(1)} °C en ${formatDuree(d)} (≤ 10 °C, ≤ 2 h)`;
  } else {
    elConfTxt.textContent =
      `⚠ Non conforme — ${partsKo.join(' · ')} — action corrective requise`;
  }

  elJeter.hidden = !jeter;
  elActionWrap.hidden = ok;
}
elTemperature.addEventListener('input', majConformite);

// ── Soumission ───────────────────────────────────────────
elForm.addEventListener('submit', async e => {
  e.preventDefault();
  elErreur.hidden = true;

  if (!state.operateurChoisi) { goStep(1); return afficherErreur('Veuillez sélectionner un opérateur.'); }
  if (!state.produitChoisi)   { goStep(2); return afficherErreur('Veuillez sélectionner un produit.'); }

  if (!elHeureDebut.value || !elHeureFin.value) return afficherErreur('Heures de début et fin requises.');

  const d = dureeMinutes(elHeureDebut.value, elHeureFin.value);
  if (d == null || d <= 0) return afficherErreur('Durée de refroidissement invalide.');

  const tInit = parseFloat(elTempInitiale.value);
  if (isNaN(tInit)) return afficherErreur('Température à cœur avant refroidissement requise.');
  if (tInit < 63) return afficherErreur('Température avant refroidissement doit être ≥ 63 °C.');

  const t = parseFloat(elTemperature.value);
  if (isNaN(t)) return afficherErreur('Température à cœur après refroidissement requise.');

  const tempOk  = t <= TEMP_CIBLE;
  const dureeOk = d <= DUREE_MAX_MIN;
  const conforme = tempOk && dureeOk;
  if (!conforme && !elAction.value.trim()) {
    return afficherErreur('Action corrective obligatoire si refroidissement non conforme.');
  }

  const payload = {
    date_refroidissement:  elDate.value,
    personnel_id:          Number(state.operateurChoisi.id),
    produit_id:            Number(state.produitChoisi.id),
    cuisson_id:            state.produitChoisi.cuisson_id ?? null,
    heure_debut:           elHeureDebut.value,
    heure_fin:             elHeureFin.value,
    temperature_initiale:  tInit,
    temperature_finale:    t,
    action_corrective:     elAction.value.trim() || null,
  };

  elBtnSave.disabled    = true;
  elBtnSave.textContent = '⏳ Enregistrement…';

  try {
    const res = await apiFetch('/api/refroidissement/enregistrements', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    let msg = '✓ Refroidissement enregistré';
    if (res.jeter)         msg = '⛔ Enregistré — PRODUITS À JETER';
    else if (!res.conforme) msg = '⚠ Enregistré — non conforme';
    afficherToast(msg, !!res.conforme);
    resetWizard();
    await chargerHistorique();
  } catch (err) {
    afficherErreur(err.message);
  } finally {
    elBtnSave.disabled    = false;
    elBtnSave.textContent = '✓ Enregistrer le refroidissement';
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

  elOperateursGrid.querySelectorAll('.cu-tuile').forEach(t =>
    t.classList.remove('cu-tuile--selected'));
  elProduitsGrid.querySelectorAll('.cu-tuile').forEach(t =>
    t.classList.remove('cu-tuile--selected'));
  elProdSearch.value = '';
  afficherProduits();

  elHeureDebut.value      = '';
  elHeureFin.value        = '';
  elTempInitiale.value    = '63';
  elTemperature.value     = '';
  elAction.value      = '';
  elConformite.hidden = true;
  elJeter.hidden      = true;
  elActionWrap.hidden = true;
  elDate.value        = todayISO();
  elQuickFin.querySelectorAll('.cu-quick-btn').forEach(b =>
    b.classList.remove('cu-quick-btn--actif'));

  goStep(1);
}

// Préremplir heure début quand on arrive à l'étape 3
new MutationObserver(() => {
  if (!elSteps[3].hidden) preremplirHeureDebut();
}).observe(elSteps[3], { attributes: true, attributeFilter: ['hidden'] });

// ── Historique récent ────────────────────────────────────
async function chargerHistorique() {
  elHisto.innerHTML = `<div class="cu-histo-vide">Chargement…</div>`;
  try {
    const rows = await apiFetch('/api/refroidissement/enregistrements?limit=20');
    if (!rows.length) {
      elHisto.innerHTML = `<div class="cu-histo-vide">Aucun refroidissement enregistré pour l'instant.</div>`;
      return;
    }
    elHisto.innerHTML = rows.map(r => {
      const ok = !!r.conforme;
      const jeter = !!r.jeter;
      const badge = jeter ? '⛔ JETER ' : (ok ? '' : '⚠ ');
      return `
        <div class="cu-histo-ligne ${ok ? '' : 'cu-histo-ligne--ko'}">
          <div class="cu-histo-date">
            ${formatDate(r.date_refroidissement)}<br>
            <small>${escHtml(r.heure_debut ?? '')}→${escHtml(r.heure_fin ?? '')}</small><br>
            <small>${formatDuree(r.duree_minutes)}</small>
          </div>
          <div class="cu-histo-info">
            <strong>${badge}${escHtml(r.produit_nom ?? '—')}</strong>
            <br>
            <small>
              Opérateur : ${escHtml(r.personnel_prenom ?? '—')}
              ${r.action_corrective ? `· Action : ${escHtml(r.action_corrective)}` : ''}
            </small>
          </div>
          <div class="cu-histo-temp ${ok ? 'cu-histo-temp--ok' : 'cu-histo-temp--ko'}">
            ${formatTemp(r.temperature_finale)}
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

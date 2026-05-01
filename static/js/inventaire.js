'use strict';
/* ============================================================
   inventaire.js — Stock unifié FIFO multi-sources
   📦 Réception · 🔪 Fabrication · 🔥 Cuisson · ❄️ Refroidissement
   ============================================================ */

const $ = (id) => document.getElementById(id);

function escHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatDateFr(iso) {
  if (!iso) return '';
  const [y, m, j] = iso.split('-');
  return `${j}/${m}/${y}`;
}

function niveauJoursRestants(jr) {
  if (jr == null) return 'gris';
  if (jr < 0)  return 'noir';
  if (jr <= 1) return 'rouge';
  if (jr <= 3) return 'orange';
  if (jr <= 7) return 'jaune';
  return 'vert';
}

function libelleJoursRestants(jr) {
  if (jr == null) return '—';
  if (jr < 0)  return `Périmé J${jr}`;
  if (jr === 0) return "Aujourd'hui";
  if (jr === 1) return 'Demain';
  return `J+${jr}`;
}

const state = {
  type: 'tous',
  categorie: '',
  dlc_max: '',
  inclure_expires: false,
};

// ── Horloge ─────────────────────────────────────────────────────────────
function tickHorloge() {
  const h = $('inv-horloge');
  if (!h) return;
  const d = new Date();
  h.textContent = d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}
setInterval(tickHorloge, 30000);
tickHorloge();

// ── Chargement liste ────────────────────────────────────────────────────
async function chargerStock() {
  const params = new URLSearchParams();
  if (state.type) params.set('type', state.type);
  if (state.categorie) params.set('categorie', state.categorie);
  if (state.dlc_max) params.set('dlc_max', state.dlc_max);
  if (state.inclure_expires) params.set('inclure_expires', 'true');

  const liste = $('inv-liste');
  liste.innerHTML = `<div class="inv-vide">Chargement…</div>`;

  let data;
  try {
    const r = await fetch(`/api/stock?${params.toString()}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    data = await r.json();
  } catch (e) {
    liste.innerHTML = `<div class="inv-erreur">Erreur de chargement : ${escHtml(e.message)}</div>`;
    return;
  }

  // Stats
  $('inv-stat-total').textContent           = data.total ?? 0;
  $('inv-stat-reception').textContent       = data.par_source?.reception_ligne ?? 0;
  $('inv-stat-fabrication').textContent     = data.par_source?.fabrication ?? 0;
  $('inv-stat-cuisson').textContent         = data.par_source?.cuisson ?? 0;
  $('inv-stat-refroidissement').textContent = data.par_source?.refroidissement ?? 0;
  $('inv-stat-3j').textContent              = data.expirent_3j ?? 0;

  // Liste
  if (!data.items || data.items.length === 0) {
    liste.innerHTML = `<div class="inv-vide">Aucun produit en stock pour ces filtres.</div>`;
    return;
  }

  liste.innerHTML = data.items.map(it => {
    const niveau = niveauJoursRestants(it.jours_restants);
    const lblJr = libelleJoursRestants(it.jours_restants);
    const meta = [];
    if (it.numero_lot)      meta.push(`Lot ${escHtml(it.numero_lot)}`);
    if (it.quantite != null) meta.push(`${it.quantite} ${escHtml(it.unite || '')}`);
    if (it.fournisseur_nom) meta.push(`Frn : ${escHtml(it.fournisseur_nom)}`);
    if (it.date_origine)    meta.push(`Origine : ${formatDateFr(it.date_origine)}`);

    return `
      <article class="inv-item inv-item--${niveau}" data-source="${escHtml(it.source_type)}">
        <div class="inv-item-icone" aria-hidden="true">${it.source_icon || ''}</div>
        <div class="inv-item-corps">
          <div class="inv-item-nom">${escHtml(it.produit_nom)}</div>
          <div class="inv-item-meta">${meta.join(' · ')}</div>
          <div class="inv-item-cat">${escHtml(it.categorie || '')}</div>
        </div>
        <div class="inv-item-dlc">
          <div class="inv-item-jr inv-item-jr--${niveau}">${escHtml(lblJr)}</div>
          <div class="inv-item-dlc-date">DLC : ${formatDateFr(it.dlc)}</div>
        </div>
      </article>
    `;
  }).join('');
}

// ── Bindings filtres ────────────────────────────────────────────────────
function bindFiltres() {
  $('inv-filtre-type').addEventListener('change', (e) => {
    state.type = e.target.value;
    chargerStock();
  });
  $('inv-filtre-categorie').addEventListener('change', (e) => {
    state.categorie = e.target.value;
    chargerStock();
  });
  $('inv-filtre-dlc-max').addEventListener('change', (e) => {
    state.dlc_max = e.target.value;
    chargerStock();
  });
  $('inv-filtre-expires').addEventListener('change', (e) => {
    state.inclure_expires = e.target.checked;
    chargerStock();
  });
  $('inv-reset').addEventListener('click', () => {
    state.type = 'tous';
    state.categorie = '';
    state.dlc_max = '';
    state.inclure_expires = false;
    $('inv-filtre-type').value = 'tous';
    $('inv-filtre-categorie').value = '';
    $('inv-filtre-dlc-max').value = '';
    $('inv-filtre-expires').checked = false;
    chargerStock();
  });
}

// ── Init ────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  bindFiltres();
  chargerStock();
});

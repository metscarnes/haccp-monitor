'use strict';
/* ============================================================
   cuisson.js — Module Cuisson (onglet Rôtissoire)
   Au Comptoir des Lilas — Mets Carnés Holding

   Flux :
     - Sélection produit (recherche dans le catalogue)
     - Lien FIFO vers le dernier lot de réception
     - Bouton "Historique de réception" → modal
     - Validation HACCP : T° ≥ 63 °C sinon action corrective obligatoire
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

// ── Références DOM ─────────────────────────────────────────
const $ = id => document.getElementById(id);

const elHorloge      = $('cu-horloge');
const elDate         = $('cu-date');
const elOperateur    = $('cu-operateur');
const elProdSearch   = $('cu-produit-search');
const elProdClear    = $('cu-produit-clear');
const elProdSuggest  = $('cu-produit-suggest');
const elProdSelected = $('cu-produit-selected');
const elProdSelNom   = $('cu-produit-selected-nom');
const elProdLot      = $('cu-produit-lot');
const elProdDlc      = $('cu-produit-dlc');
const elProdId       = $('cu-produit-id');
const elRecLigneId   = $('cu-reception-ligne-id');
const elBtnHisto     = $('cu-btn-historique');
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
  produits:        [],    // cache catalogue complet
  produitChoisi:   null,  // {id, nom, numero_lot, dlc, reception_ligne_id}
};

// ── Init : date, personnel, catalogue, historique ─────────
async function init() {
  elDate.value = todayISO();

  await Promise.all([
    chargerPersonnel(),
    chargerProduits(),
    chargerHistorique(),
  ]);
}

async function chargerPersonnel() {
  try {
    const personnel = await apiFetch('/api/admin/personnel');
    personnel
      .filter(p => p.actif !== 0 && p.actif !== false)
      .forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.prenom;
        elOperateur.appendChild(opt);
      });
  } catch (err) {
    console.warn('[cuisson] Personnel KO :', err);
  }
}

async function chargerProduits() {
  try {
    // Catalogue matière première (brut) + info stock/FIFO pour marquer ⭐
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

// ── Recherche produit : suggestions live ─────────────────
function filtrerProduits(q) {
  const needle = q.trim().toUpperCase();
  const matchs = needle
    ? state.produits.filter(p => (p.nom ?? '').toUpperCase().includes(needle))
    : [];

  // Tri : en stock (DLC la plus courte) d'abord, puis reste alphabétique
  matchs.sort((a, b) => {
    if (a.en_stock !== b.en_stock) return a.en_stock ? -1 : 1;
    if (a.en_stock && b.en_stock) {
      const da = a.dlc ? new Date(a.dlc).getTime() : Infinity;
      const db = b.dlc ? new Date(b.dlc).getTime() : Infinity;
      if (da !== db) return da - db;
    }
    return (a.nom ?? '').localeCompare(b.nom ?? '', 'fr');
  });

  return matchs.slice(0, 15);
}

function afficherSuggestions(liste) {
  if (!liste.length) {
    elProdSuggest.innerHTML = `<div class="cu-suggest-vide">Aucun produit trouvé</div>`;
    elProdSuggest.hidden = false;
    return;
  }
  elProdSuggest.innerHTML = liste.map(p => {
    const etoile = p.en_stock
      ? `<span class="cu-suggest-star" title="Réception disponible">⭐</span>`
      : `<span class="cu-suggest-star cu-suggest-star--off"></span>`;
    const dlcBadge = p.en_stock && p.dlc
      ? `<span class="cu-suggest-dlc">DLC ${formatDate(p.dlc)}</span>`
      : '';
    return `
      <div class="cu-suggest-item"
           data-id="${p.id}"
           data-nom="${escHtml(p.nom)}"
           role="option" tabindex="0">
        ${etoile}
        <span class="cu-suggest-nom">${escHtml(p.nom)}</span>
        ${dlcBadge}
      </div>
    `;
  }).join('');
  elProdSuggest.hidden = false;
}

elProdSearch.addEventListener('input', () => {
  const q = elProdSearch.value;
  if (!q.trim()) {
    elProdSuggest.hidden = true;
    return;
  }
  afficherSuggestions(filtrerProduits(q));
});

elProdSearch.addEventListener('focus', () => {
  const q = elProdSearch.value;
  if (q.trim()) afficherSuggestions(filtrerProduits(q));
});

document.addEventListener('click', e => {
  if (!elProdSuggest.contains(e.target) && e.target !== elProdSearch) {
    elProdSuggest.hidden = true;
  }
});

elProdSuggest.addEventListener('click', e => {
  const item = e.target.closest('.cu-suggest-item[data-id]');
  if (!item) return;
  selectionnerProduit(Number(item.dataset.id), item.dataset.nom);
});
elProdSuggest.addEventListener('keydown', e => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const item = e.target.closest('.cu-suggest-item[data-id]');
  if (item) { e.preventDefault(); selectionnerProduit(Number(item.dataset.id), item.dataset.nom); }
});

async function selectionnerProduit(id, nom) {
  elProdSuggest.hidden = true;
  elProdSearch.value = nom;
  elProdClear.hidden = false;

  state.produitChoisi = { id, nom, numero_lot: null, dlc: null, reception_ligne_id: null };
  elProdId.value = id;
  elRecLigneId.value = '';
  elProdSelNom.textContent = nom;
  elProdLot.textContent = '';
  elProdDlc.textContent = '';
  elProdSelected.hidden = false;
  elBtnHisto.hidden = false;

  // Essaie de récupérer le lot FIFO (peut ne pas exister → 404 toléré)
  try {
    const lot = await apiFetch(`/api/fabrications/produit-fifo/${id}`);
    state.produitChoisi.numero_lot         = lot.numero_lot ?? null;
    state.produitChoisi.dlc                = lot.dlc ?? null;
    state.produitChoisi.reception_ligne_id = lot.id ?? null;
    elRecLigneId.value = lot.id ?? '';
    elProdLot.textContent = lot.numero_lot ? `Lot : ${lot.numero_lot}` : '';
    elProdDlc.textContent = lot.dlc ? `DLC : ${formatDate(lot.dlc)}` : '';
  } catch {
    elProdLot.textContent = 'Aucune réception enregistrée pour ce produit';
    elProdDlc.textContent = '';
  }
}

elProdClear.addEventListener('click', () => {
  elProdSearch.value = '';
  elProdClear.hidden = true;
  elProdSuggest.hidden = true;
  elProdSelected.hidden = true;
  elBtnHisto.hidden = true;
  state.produitChoisi = null;
  elProdId.value = '';
  elRecLigneId.value = '';
});

// ── Historique réception produit — modale ────────────────
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
          <strong>Lot&nbsp;:</strong> ${escHtml(r.numero_lot ?? '—')}
          &nbsp;·&nbsp; <strong>DLC&nbsp;:</strong> ${formatDate(r.dlc)}
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

// ── Heure fin — boutons rapides (+1h, +1h30…) ────────────
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

// Reset du bouton actif si l'utilisateur change manuellement
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

  if (!state.produitChoisi) {
    return afficherErreur('Veuillez sélectionner un produit.');
  }
  if (!elOperateur.value) {
    return afficherErreur('Veuillez sélectionner un opérateur.');
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
    personnel_id:       Number(elOperateur.value),
    produit_id:         Number(state.produitChoisi.id),
    reception_ligne_id: elRecLigneId.value ? Number(elRecLigneId.value) : null,
    quantite:           elQuantite.value ? parseFloat(elQuantite.value) : null,
    unite:              elUnite.value || 'kg',
    heure_debut:        elHeureDebut.value,
    heure_fin:          elHeureFin.value,
    temperature_sortie: temp,
    action_corrective:  elAction.value.trim() || null,
  };

  elBtnSave.disabled   = true;
  elBtnSave.textContent = '⏳ Enregistrement…';

  try {
    const res = await apiFetch('/api/cuisson/enregistrements', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    afficherToast(res.conforme ? '✓ Cuisson enregistrée' : '⚠ Cuisson enregistrée — non conforme', res.conforme);
    resetFormulaire();
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

function resetFormulaire() {
  elProdClear.click();
  elProdSearch.value = '';
  elQuantite.value = '';
  elHeureDebut.value = '';
  elHeureFin.value = '';
  elTemperature.value = '';
  elAction.value = '';
  elConformite.hidden = true;
  elActionWrap.hidden = true;
  elDate.value = todayISO();
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

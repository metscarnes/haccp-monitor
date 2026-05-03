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

// ── État principal ───────────────────────────────────────────
const state = {
  type: 'tous',
  categorie: '',
  dlc_max: '',
  inclure_expires: false,
  // Filtres client (appliqués sans rechargement réseau)
  recherche: '',       // texte (nom OU N° de lot, insensible à la casse/accents)
  espece: '',          // espèce sélectionnée (vide = toutes)
  tri: 'dlc_asc',      // dlc_asc | dlc_desc | nom_asc | nom_desc | origine_desc | origine_asc
  itemsRaw: [],        // données brutes renvoyées par /api/stock
  items: [],           // données filtrées+triées affichées
  personnel: [],       // chargé une fois
};

const gestionState = {
  mode: false,
  selection: new Set(), // clés "source_type:source_id"
};

const batchState = {
  statut: null,
};

const editState = {
  cible: null, // { source_type, source_id, produit_nom, numero_lot, dlc, quantite, unite }
};

function clefItem(it) { return `${it.source_type}:${it.source_id}`; }

// ── Horloge ─────────────────────────────────────────────────
function tickHorloge() {
  const h = $('inv-horloge');
  if (!h) return;
  h.textContent = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}
setInterval(tickHorloge, 30000);
tickHorloge();

// ── Personnel ────────────────────────────────────────────────
async function chargerPersonnel() {
  try {
    const r = await fetch('/api/admin/personnel', { cache: 'no-store' });
    if (!r.ok) return;
    const data = await r.json();
    state.personnel = Array.isArray(data) ? data : (data.personnel ?? []);
  } catch (_) { /* silencieux */ }
}

// ── Rendu liste ──────────────────────────────────────────────
function renderItems() {
  const liste = $('inv-liste');
  const items = state.items;

  if (!items || items.length === 0) {
    liste.innerHTML = `<div class="inv-vide">Aucun produit en stock pour ces filtres.</div>`;
    return;
  }

  liste.innerHTML = items.map(it => {
    const niveau  = niveauJoursRestants(it.jours_restants);
    const lblJr   = libelleJoursRestants(it.jours_restants);
    const cle     = clefItem(it);
    const selecne = gestionState.selection.has(cle) ? ' selectionne' : '';
    const meta    = [];
    if (it.numero_lot)       meta.push(`Lot ${escHtml(it.numero_lot)}`);
    if (it.quantite != null) meta.push(`${it.quantite} ${escHtml(it.unite || '')}`);
    if (it.fournisseur_nom)  meta.push(`Frn : ${escHtml(it.fournisseur_nom)}`);
    if (it.date_origine)     meta.push(`Origine : ${formatDateFr(it.date_origine)}`);

    return `
      <article class="inv-item inv-item--${niveau}${selecne}"
               data-cle="${escHtml(cle)}"
               data-source="${escHtml(it.source_type)}">
        <input type="checkbox" class="inv-item-check"
               data-cle="${escHtml(cle)}"
               ${gestionState.selection.has(cle) ? 'checked' : ''}
               aria-label="Sélectionner ${escHtml(it.produit_nom)}">
        <div class="inv-item-icone" aria-hidden="true">${it.source_icon || ''}</div>
        <div class="inv-item-corps">
          <div class="inv-item-nom">${escHtml(it.produit_nom)}</div>
          <div class="inv-item-meta">${meta.join(' · ')}</div>
          <div class="inv-item-cat">${escHtml(it.categorie || '')}</div>
        </div>
        <div class="inv-item-dlc">
          <div class="inv-item-jr inv-item-jr--${niveau}">${escHtml(lblJr)}</div>
          <div class="inv-item-dlc-date">${it.est_dluo ? 'DLUO' : 'DLC'} : ${formatDateFr(it.dlc)}</div>
        </div>
      </article>
    `;
  }).join('');

  // ── Événements sur les items ────────────────────────────────
  liste.querySelectorAll('.inv-item').forEach(article => {
    article.addEventListener('click', (e) => {
      if (gestionState.mode) {
        // En mode gestion : sélection par clic sur l'article
        const cle = article.dataset.cle;
        const cb  = article.querySelector('.inv-item-check');
        if (e.target === cb) return; // la checkbox gère elle-même
        toggleSelection(cle, cb);
      } else {
        // Hors mode gestion : ouvre la modale de modification
        const it = state.items.find(x => clefItem(x) === article.dataset.cle);
        if (it) ouvrirEditModal(it);
      }
    });
  });

  liste.querySelectorAll('.inv-item-check').forEach(cb => {
    cb.addEventListener('change', () => toggleSelection(cb.dataset.cle, cb));
  });
}

// ── Filtre/tri client ────────────────────────────────────────
function normaliser(s) {
  return String(s ?? '')
    .toLowerCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function majSelectEspeces() {
  const sel = $('inv-filtre-espece');
  if (!sel) return;
  const especes = [...new Set(
    state.itemsRaw.map(it => (it.espece || '').trim()).filter(Boolean)
  )].sort((a, b) => a.localeCompare(b, 'fr', { sensitivity: 'base' }));

  const valeurCourante = state.espece;
  sel.innerHTML = '<option value="">Toutes</option>' +
    especes.map(e => `<option value="${escHtml(e)}">${escHtml(e)}</option>`).join('');
  // Préserver la sélection si toujours présente
  if (especes.includes(valeurCourante)) {
    sel.value = valeurCourante;
  } else {
    state.espece = '';
    sel.value = '';
  }
}

function comparer(a, b) {
  switch (state.tri) {
    case 'dlc_desc': {
      const da = a.dlc || '';
      const db_ = b.dlc || '';
      if (!da && !db_) return 0;
      if (!da) return 1;
      if (!db_) return -1;
      return db_.localeCompare(da);
    }
    case 'nom_asc':
      return String(a.produit_nom || '').localeCompare(b.produit_nom || '', 'fr', { sensitivity: 'base' });
    case 'nom_desc':
      return String(b.produit_nom || '').localeCompare(a.produit_nom || '', 'fr', { sensitivity: 'base' });
    case 'origine_desc':
      return String(b.date_origine || '').localeCompare(a.date_origine || '');
    case 'origine_asc':
      return String(a.date_origine || '').localeCompare(b.date_origine || '');
    case 'dlc_asc':
    default: {
      const da = a.dlc || '';
      const db_ = b.dlc || '';
      // null/vide en dernier
      if (!da && !db_) return 0;
      if (!da) return 1;
      if (!db_) return -1;
      return da.localeCompare(db_);
    }
  }
}

function appliquerFiltresClient() {
  const q = normaliser(state.recherche).trim();
  const esp = state.espece;
  let liste = state.itemsRaw;

  if (q) {
    liste = liste.filter(it =>
      normaliser(it.produit_nom).includes(q) ||
      normaliser(it.numero_lot).includes(q)
    );
  }
  if (esp) {
    liste = liste.filter(it => (it.espece || '') === esp);
  }
  liste = [...liste].sort(comparer);
  state.items = liste;

  // Purger la sélection des items qui ne sont plus visibles
  const clesVisibles = new Set(state.items.map(clefItem));
  for (const k of gestionState.selection) {
    if (!clesVisibles.has(k)) gestionState.selection.delete(k);
  }

  renderItems();
  mettreAJourActionBar();
}

// ── Chargement stock ─────────────────────────────────────────
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

  state.itemsRaw = data.items ?? [];
  majSelectEspeces();
  appliquerFiltresClient();
}

// ══════════════════════════════════════════════════════════════
//   MODE GESTION
// ══════════════════════════════════════════════════════════════

function toggleGestionMode() {
  gestionState.mode = !gestionState.mode;
  const btn   = $('inv-btn-gestion');
  const liste = $('inv-liste');
  const main  = $('inv-main');

  btn.classList.toggle('actif', gestionState.mode);
  btn.setAttribute('aria-pressed', String(gestionState.mode));
  liste.classList.toggle('gestion-mode', gestionState.mode);
  main.classList.toggle('gestion-active', gestionState.mode);

  if (!gestionState.mode) {
    gestionState.selection.clear();
    $('inv-action-bar').hidden = true;
    renderItems();
  } else {
    $('inv-action-bar').hidden = false;
    renderItems();
    mettreAJourActionBar();
  }
}

function toggleSelection(cle, cb) {
  if (gestionState.selection.has(cle)) {
    gestionState.selection.delete(cle);
    if (cb) cb.checked = false;
  } else {
    gestionState.selection.add(cle);
    if (cb) cb.checked = true;
  }
  // Mettre à jour la classe visuelle sur l'article
  const article = $('inv-liste').querySelector(`[data-cle="${CSS.escape(cle)}"]`);
  if (article) article.classList.toggle('selectionne', gestionState.selection.has(cle));
  mettreAJourActionBar();
}

function mettreAJourActionBar() {
  const n     = gestionState.selection.size;
  const btn   = $('inv-btn-traiter-sel');
  const btnM  = $('inv-btn-modifier-sel');
  const label = $('inv-action-sel');

  label.textContent   = `${n} produit${n > 1 ? 's' : ''} sélectionné${n > 1 ? 's' : ''}`;
  btn.disabled        = n === 0;
  btnM.disabled       = n !== 1; // modification uniquement sur 1 seul produit à la fois
}

// ══════════════════════════════════════════════════════════════
//   MODAL BATCH — Traitement en masse (même que DLC)
// ══════════════════════════════════════════════════════════════

function ouvrirBatchModal() {
  const selItems = state.items.filter(it => gestionState.selection.has(clefItem(it)));
  if (selItems.length === 0) return;

  batchState.statut = null;

  // Résumé
  $('inv-batch-resume').textContent =
    `${selItems.length} produit${selItems.length > 1 ? 's' : ''} sélectionné${selItems.length > 1 ? 's' : ''} à traiter`;

  // "Tout sélectionner"
  $('inv-batch-tout').checked = true;

  // Commentaire
  $('inv-batch-commentaire').value = '';

  // Personnel
  const sel = $('inv-batch-personnel');
  sel.innerHTML = '<option value="">— Sélectionner —</option>';
  state.personnel.forEach(p => {
    const label = [p.prenom, p.nom].filter(Boolean).join(' ');
    sel.innerHTML += `<option value="${p.id}">${escHtml(label)}</option>`;
  });
  sel.value = '';

  // Liste des produits avec checkboxes
  const liste = $('inv-batch-liste');
  liste.innerHTML = '';
  selItems.forEach(it => {
    const k      = clefItem(it);
    const niveau = niveauJoursRestants(it.jours_restants);
    const meta   = [];
    if (it.numero_lot)       meta.push(`Lot ${escHtml(it.numero_lot)}`);
    if (it.quantite != null) meta.push(`${it.quantite} ${escHtml(it.unite || '')}`);
    if (it.fournisseur_nom)  meta.push(escHtml(it.fournisseur_nom));

    const row = document.createElement('label');
    row.className = `inv-batch-row inv-batch-row--${niveau}`;
    row.innerHTML = `
      <input type="checkbox" class="inv-batch-check" data-key="${escHtml(k)}" checked>
      <span class="inv-batch-src">${it.source_icon || ''}</span>
      <span class="inv-batch-nom">${escHtml(it.produit_nom)}</span>
      <span class="inv-batch-dlc">${it.est_dluo ? 'DLUO' : 'DLC'} ${formatDateFr(it.dlc)}</span>
      <span class="inv-batch-meta">${meta.join(' · ')}</span>
    `;
    liste.appendChild(row);
  });

  liste.querySelectorAll('.inv-batch-check').forEach(cb => {
    cb.addEventListener('change', rafraichirBatchUi);
  });

  // Réinitialiser les boutons statut
  document.querySelectorAll('[data-inv-statut]').forEach(b => b.classList.remove('actif'));
  rafraichirBatchUi();

  $('inv-batch-modal').hidden = false;
}

function fermerBatchModal() {
  $('inv-batch-modal').hidden = true;
  batchState.statut = null;
}

function rafraichirBatchUi() {
  const checked = $('inv-batch-liste').querySelectorAll('.inv-batch-check:checked');
  const n = checked.length;
  const total = $('inv-batch-liste').querySelectorAll('.inv-batch-check').length;

  $('inv-batch-compteur').textContent = `${n} sélectionné${n > 1 ? 's' : ''}`;
  $('inv-batch-tout').checked = (n === total && n > 0);
  $('inv-batch-valider').disabled = !(
    n > 0 && batchState.statut && $('inv-batch-personnel').value
  );
}

// ── Bindings batch modal ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  $('inv-batch-close').addEventListener('click', fermerBatchModal);
  $('inv-batch-backdrop').addEventListener('click', fermerBatchModal);

  $('inv-batch-tout').addEventListener('change', (e) => {
    $('inv-batch-liste').querySelectorAll('.inv-batch-check').forEach(cb => {
      cb.checked = e.target.checked;
    });
    rafraichirBatchUi();
  });

  document.querySelectorAll('[data-inv-statut]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-inv-statut]').forEach(b => b.classList.remove('actif'));
      btn.classList.add('actif');
      batchState.statut = btn.dataset.invStatut;
      rafraichirBatchUi();
    });
  });

  $('inv-batch-personnel').addEventListener('change', rafraichirBatchUi);

  $('inv-batch-valider').addEventListener('click', async () => {
    const btn = $('inv-batch-valider');
    btn.disabled = true;
    btn.textContent = 'Traitement…';

    try {
      const checked = [...$('inv-batch-liste').querySelectorAll('.inv-batch-check:checked')];
      const items = checked.map(cb => {
        const [source_type, source_id] = cb.dataset.key.split(':');
        return { source_type, source_id: parseInt(source_id, 10) };
      });

      const res = await fetch('/api/dlc/devenir/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items,
          statut: batchState.statut,
          personnel_id: parseInt($('inv-batch-personnel').value, 10),
          commentaire: $('inv-batch-commentaire').value.trim() || null,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      fermerBatchModal();
      gestionState.selection.clear();
      await chargerStock();
      alert(`✅ ${data.traites} produit${data.traites > 1 ? 's' : ''} traité${data.traites > 1 ? 's' : ''}.`);
    } catch (e) {
      alert(`Erreur : ${e.message}`);
    } finally {
      btn.textContent = 'Confirmer le traitement';
      rafraichirBatchUi();
    }
  });
});

// ══════════════════════════════════════════════════════════════
//   MODAL EDIT — Modification d'un seul produit
//   Le N° de lot est affiché mais NON modifiable
// ══════════════════════════════════════════════════════════════

function ouvrirEditModal(it) {
  editState.cible = it;

  $('inv-edit-nom').textContent  = it.produit_nom;
  $('inv-edit-lot').textContent  = it.numero_lot || '—';
  $('inv-edit-dlc').value        = it.dlc || '';

  // Quantité : masquée pour les refroidissements (pas de champ quantité dans la table)
  const qtBloc = $('inv-edit-qte-bloc');
  if (it.source_type === 'refroidissement') {
    qtBloc.hidden = true;
    $('inv-edit-qte').value = '';
  } else {
    qtBloc.hidden = false;
    $('inv-edit-unite').textContent = it.unite ? `(${it.unite})` : '';
    $('inv-edit-qte').value = it.quantite != null ? it.quantite : '';
  }

  $('inv-edit-modal').hidden = false;
}

function fermerEditModal() {
  $('inv-edit-modal').hidden = true;
  editState.cible = null;
}

document.addEventListener('DOMContentLoaded', () => {
  $('inv-edit-close').addEventListener('click', fermerEditModal);
  $('inv-edit-backdrop').addEventListener('click', fermerEditModal);

  $('inv-edit-valider').addEventListener('click', async () => {
    const it  = editState.cible;
    const btn = $('inv-edit-valider');
    if (!it) return;

    const dlcVal = $('inv-edit-dlc').value;
    const qteVal = $('inv-edit-qte').value;

    if (!dlcVal && it.dlc != null) {
      alert('La date DLC est obligatoire.');
      return;
    }

    const body = { dlc: dlcVal };
    if (it.source_type !== 'refroidissement' && qteVal !== '') {
      const q = parseFloat(qteVal);
      if (isNaN(q) || q < 0) { alert('Quantité invalide.'); return; }
      body.quantite = q;
    }

    btn.disabled = true;
    btn.textContent = 'Enregistrement…';
    try {
      const res = await fetch(`/api/stock/${it.source_type}/${it.source_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      fermerEditModal();
      // Quitter le mode gestion si ouvert
      if (gestionState.mode) {
        gestionState.selection.clear();
      }
      await chargerStock();
    } catch (e) {
      alert(`Erreur : ${e.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Enregistrer les modifications';
    }
  });
});

// ══════════════════════════════════════════════════════════════
//   BINDINGS GLOBAUX
// ══════════════════════════════════════════════════════════════

function bindFiltres() {
  // Filtres serveur (déclenchent un rechargement)
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

  // Filtres client (instantanés, sans rechargement réseau)
  let debounceRecherche;
  $('inv-filtre-recherche').addEventListener('input', (e) => {
    clearTimeout(debounceRecherche);
    debounceRecherche = setTimeout(() => {
      state.recherche = e.target.value;
      appliquerFiltresClient();
    }, 150);
  });
  $('inv-filtre-espece').addEventListener('change', (e) => {
    state.espece = e.target.value;
    appliquerFiltresClient();
  });
  $('inv-filtre-tri').addEventListener('change', (e) => {
    state.tri = e.target.value;
    appliquerFiltresClient();
  });

  $('inv-reset').addEventListener('click', () => {
    state.type = 'tous';
    state.categorie = '';
    state.dlc_max = '';
    state.inclure_expires = false;
    state.recherche = '';
    state.espece = '';
    state.tri = 'dlc_asc';
    $('inv-filtre-type').value = 'tous';
    $('inv-filtre-categorie').value = '';
    $('inv-filtre-dlc-max').value = '';
    $('inv-filtre-expires').checked = false;
    $('inv-filtre-recherche').value = '';
    $('inv-filtre-espece').value = '';
    $('inv-filtre-tri').value = 'dlc_asc';
    chargerStock();
  });
  $('inv-btn-gestion').addEventListener('click', toggleGestionMode);
  $('inv-btn-traiter-sel').addEventListener('click', ouvrirBatchModal);
  $('inv-btn-modifier-sel').addEventListener('click', () => {
    const [cle] = gestionState.selection;
    const it = state.items.find(x => clefItem(x) === cle);
    if (it) ouvrirEditModal(it);
  });
}

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  bindFiltres();
  chargerPersonnel();
  chargerStock();
});

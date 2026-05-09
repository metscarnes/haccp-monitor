'use strict';
/* ============================================================
   catalogue.js — Module Catalogue produits
   Au Comptoir des Lilas — Mets Carnés Holding

   Vue tableau de tous les produits, filtres, recherche,
   modal édition/création, import/export Excel.
   ============================================================ */

// ── Helpers ────────────────────────────────────────────────
function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function apiFetch(url, options = {}) {
  const res = await fetch(url, { cache: 'no-store', ...options });
  if (res.status === 204) return null;
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    let msg = txt;
    try {
      const j = JSON.parse(txt);
      if (j && j.detail) msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail);
    } catch { /* noop */ }
    throw new Error(msg || `HTTP ${res.status}`);
  }
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return res.text();
}

// ── État ───────────────────────────────────────────────────
let tousProduits = [];
let categoriesConnues = [];

// ── Génération automatique du code unique ──────────────────
const PREFIXES_ESPECE = {
  bovin:          { normal: 'VB',    abats: 'VBA'   },
  veau:           { normal: 'VX',    abats: 'VXAB'  },
  agneau:         { normal: 'AGN',   abats: 'AGNAB' },
  porc:           { normal: 'PC',    abats: 'PACAB' },
  gibier:         { normal: 'GIB',   abats: null    },
  canard:         { normal: 'VC',    abats: null    },
  dinde:          { normal: 'VD',    abats: null    },
  lapin:          { normal: 'VL',    abats: null    },
  volaille_autre: { normal: 'VP',    abats: null    },
  cheval:         { normal: 'CH',    abats: null    },
  exotique:       { normal: 'VEXOA', abats: null    },
};

function prefixePourCode(espece, abats) {
  const m = PREFIXES_ESPECE[espece];
  if (!m) return null;
  return (abats && m.abats) ? m.abats : m.normal;
}

function prochainCodeUnique(prefixe) {
  const re = new RegExp(`^${prefixe}(\\d+)$`);
  let max = 0;
  for (const p of tousProduits) {
    const code = (p.code_unique || '').toUpperCase();
    const m = code.match(re);
    if (m) {
      const n = parseInt(m[1], 10);
      if (n > max) max = n;
    }
  }
  return `${prefixe}${max + 1}`;
}

function rafraichirCodePreview() {
  const espece = f.espece.value;
  const abats  = f.abats.checked;
  const prefixe = prefixePourCode(espece, abats);
  if (!prefixe) {
    f.code.value = '';
    f.code.placeholder = 'sélectionnez une espèce…';
    return;
  }
  f.code.value = prochainCodeUnique(prefixe);
}

// ── Éléments DOM ───────────────────────────────────────────
const $ = id => document.getElementById(id);
const elTbody = $('cat-tbody');
const elVide = $('cat-vide');
const elResultat = $('cat-resultat');
const elSearch = $('cat-search');
const elFType = $('cat-filtre-type');
const elFCateg = $('cat-filtre-categorie');
const elFCond = $('cat-filtre-cond');
const elFArchives = $('cat-filtre-archives');
const elFIncomplets = $('cat-filtre-incomplets');

const elModal = $('cat-modal');
const elModalTitre = $('cat-modal-titre');
const elForm = $('cat-form');
const elFErreur = $('cat-form-erreur');
const elBtnSupprimer = $('cat-btn-supprimer');

// Champs formulaire
const f = {
  id:      $('cat-f-id'),
  nom:     $('cat-f-nom'),
  code:    $('cat-f-code'),
  categ:   $('cat-f-categorie'),
  espece:  $('cat-f-espece'),
  abats:   $('cat-f-abats'),
  cond:    $('cat-f-cond'),
  type:    $('cat-f-type'),
  dlc:     $('cat-f-dlc'),
  temp:    $('cat-f-temp'),
  actif:   $('cat-f-actif'),
};

// ── Chargement initial ─────────────────────────────────────
async function chargerProduits() {
  const inclureInactifs = elFArchives.checked;
  const url = `/api/produits?inclure_inactifs=${inclureInactifs ? 'true' : 'false'}`;
  try {
    tousProduits = await apiFetch(url);
  } catch (e) {
    elTbody.innerHTML = `<tr><td colspan="9" class="cat-erreur">Erreur : ${escHtml(e.message)}</td></tr>`;
    return;
  }
  remplirFiltreConditionnement();
  rendre();
  majStats();
}

async function chargerCategories() {
  try {
    categoriesConnues = await apiFetch('/api/produits/categories');
  } catch { categoriesConnues = []; }
  remplirSelectCategories();
  remplirDatalistCategories();
}

function remplirSelectCategories() {
  const courant = elFCateg.value;
  elFCateg.innerHTML = '<option value="">Toutes</option>' +
    categoriesConnues.map(c => `<option value="${escHtml(c)}">${escHtml(c)}</option>`).join('');
  elFCateg.value = courant;
}

function remplirDatalistCategories() {
  const dl = $('cat-categories-datalist');
  dl.innerHTML = categoriesConnues.map(c => `<option value="${escHtml(c)}">`).join('');
}

function remplirFiltreConditionnement() {
  const conds = [...new Set(tousProduits.map(p => p.conditionnement).filter(Boolean))].sort();
  const courant = elFCond.value;
  elFCond.innerHTML = '<option value="">Tous</option>' +
    conds.map(c => `<option value="${escHtml(c)}">${escHtml(c)}</option>`).join('');
  elFCond.value = courant;
}

// ── Filtrage / rendu ───────────────────────────────────────
function estIncomplet(p) {
  return !p.code_unique || !p.categorie || !p.dlc_jours;
}

function filtrerProduits() {
  const q = elSearch.value.trim().toLowerCase();
  const ft = elFType.value;
  const fc = elFCateg.value;
  const fcond = elFCond.value;
  const fIncomp = elFIncomplets.checked;

  return tousProduits.filter(p => {
    if (ft && p.type_produit !== ft) return false;
    if (fc && p.categorie !== fc) return false;
    if (fcond && p.conditionnement !== fcond) return false;
    if (fIncomp && !estIncomplet(p)) return false;
    if (q) {
      const hay = [p.nom, p.code_unique, p.espece, p.categorie, p.coupe_niveau]
        .filter(Boolean).join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function rendre() {
  const liste = filtrerProduits();
  elResultat.textContent = `${liste.length} / ${tousProduits.length}`;

  if (liste.length === 0) {
    elTbody.innerHTML = '';
    elVide.hidden = false;
    return;
  }
  elVide.hidden = true;

  elTbody.innerHTML = liste.map(p => {
    const incompl = estIncomplet(p);
    const archive = !p.actif;
    const cls = [
      archive ? 'cat-row--archive' : '',
      incompl ? 'cat-row--incomplet' : '',
    ].filter(Boolean).join(' ');
    const statut = archive
      ? '<span class="cat-badge cat-badge--archive">Archivé</span>'
      : incompl
        ? '<span class="cat-badge cat-badge--incomplet">Incomplet</span>'
        : '<span class="cat-badge cat-badge--ok">Actif</span>';
    return `
      <tr class="${cls}" data-id="${p.id}">
        <td class="cat-cell-nom">${escHtml(p.nom)}</td>
        <td><code>${escHtml(p.code_unique || '—')}</code></td>
        <td>${escHtml(p.categorie || '—')}</td>
        <td>${escHtml(p.type_produit || '—')}</td>
        <td>${escHtml(p.conditionnement || '—')}</td>
        <td class="cat-col-num">${p.dlc_jours ?? '—'}</td>
        <td>${escHtml(p.temperature_conservation || '—')}</td>
        <td>${statut}</td>
        <td class="cat-col-actions">
          <button type="button" class="cat-btn cat-btn--small cat-btn-edit" data-id="${p.id}">✎ Éditer</button>
        </td>
      </tr>`;
  }).join('');

  elTbody.querySelectorAll('.cat-btn-edit').forEach(btn => {
    btn.addEventListener('click', () => ouvrirModalEdition(parseInt(btn.dataset.id, 10)));
  });
}

function majStats() {
  const total = tousProduits.length;
  const brut = tousProduits.filter(p => p.type_produit === 'brut' && p.actif).length;
  const fini = tousProduits.filter(p => p.type_produit === 'fini' && p.actif).length;
  const archive = tousProduits.filter(p => !p.actif).length;
  const incomp = tousProduits.filter(p => p.actif && estIncomplet(p)).length;
  $('cat-stat-total').textContent = total;
  $('cat-stat-brut').textContent = brut;
  $('cat-stat-fini').textContent = fini;
  $('cat-stat-archive').textContent = archive;
  $('cat-stat-incomplet').textContent = incomp;
}

// ── Modal édition / création ───────────────────────────────
function ouvrirModalCreation() {
  elModalTitre.textContent = 'Nouveau produit';
  elBtnSupprimer.hidden = true;
  elFErreur.hidden = true;
  elForm.reset();
  f.id.value = '';
  f.espece.value = '';
  f.abats.checked = false;
  f.cond.value = 'SOUS_VIDE';
  f.type.value = 'brut';
  f.dlc.value = 0;
  f.temp.value = '0°C à +4°C';
  f.actif.checked = true;
  rafraichirCodePreview();
  elModal.hidden = false;
  setTimeout(() => f.nom.focus(), 50);
}

function ouvrirModalEdition(id) {
  const p = tousProduits.find(x => x.id === id);
  if (!p) return;
  elModalTitre.textContent = `Édition : ${p.nom}`;
  elBtnSupprimer.hidden = !p.actif;
  elFErreur.hidden = true;
  f.id.value = p.id;
  f.nom.value = p.nom || '';
  f.code.value = p.code_unique || '';
  f.categ.value = p.categorie || '';
  f.espece.value = p.espece || '';
  f.abats.checked = false;
  f.cond.value = p.conditionnement || 'SOUS_VIDE';
  f.type.value = p.type_produit || 'brut';
  f.dlc.value = p.dlc_jours ?? 0;
  f.temp.value = p.temperature_conservation || '0°C à +4°C';
  f.actif.checked = !!p.actif;
  elModal.hidden = false;
  setTimeout(() => f.nom.focus(), 50);
}

function fermerModal() {
  elModal.hidden = true;
}

function lirePayload() {
  const data = {
    nom: f.nom.value.trim(),
    code_unique: f.code.value.trim() || null,
    categorie: f.categ.value.trim(),
    espece: f.espece.value || null,
    conditionnement: f.cond.value || null,
    type_produit: f.type.value,
    dlc_jours: f.dlc.value === '' ? 0 : parseInt(f.dlc.value, 10),
    temperature_conservation: f.temp.value || null,
    actif: f.actif.checked,
  };
  // null → champs omis (POST/PUT acceptent omission)
  Object.keys(data).forEach(k => {
    if (data[k] === null) delete data[k];
  });
  return data;
}

async function soumettre(e) {
  e.preventDefault();
  elFErreur.hidden = true;
  const payload = lirePayload();
  if (!payload.nom) {
    afficherErreur('Le nom est obligatoire');
    return;
  }
  if (!payload.categorie) {
    afficherErreur('La catégorie est obligatoire');
    return;
  }
  const id = f.id.value;
  const url = id ? `/api/produits/${id}` : '/api/produits';
  const method = id ? 'PUT' : 'POST';
  try {
    await apiFetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    fermerModal();
    await chargerProduits();
    await chargerCategories();
  } catch (err) {
    afficherErreur(err.message);
  }
}

function afficherErreur(msg) {
  elFErreur.textContent = msg;
  elFErreur.hidden = false;
}

async function archiverProduit() {
  const id = f.id.value;
  if (!id) return;
  if (!confirm('Archiver ce produit ? Il restera lié aux historiques mais ne sera plus proposé.')) return;
  try {
    await apiFetch(`/api/produits/${id}`, { method: 'DELETE' });
    fermerModal();
    await chargerProduits();
  } catch (err) {
    afficherErreur(err.message);
  }
}

// ── Import Excel ───────────────────────────────────────────
const elImportModal = $('cat-import-modal');
const elImportFichier = $('cat-import-fichier');
const elImportMode = $('cat-import-mode');
const elImportResultat = $('cat-import-resultat');

function ouvrirImport() {
  elImportFichier.value = '';
  elImportMode.value = 'merge';
  elImportResultat.hidden = true;
  elImportResultat.textContent = '';
  elImportModal.hidden = false;
}

function fermerImport() {
  elImportModal.hidden = true;
}

async function lancerImport() {
  const file = elImportFichier.files[0];
  if (!file) {
    elImportResultat.hidden = false;
    elImportResultat.className = 'cat-import-resultat cat-import-resultat--err';
    elImportResultat.textContent = 'Choisissez un fichier .xlsx';
    return;
  }
  const fd = new FormData();
  fd.append('fichier', file);
  fd.append('mode', elImportMode.value);
  elImportResultat.hidden = false;
  elImportResultat.className = 'cat-import-resultat';
  elImportResultat.textContent = '⏳ Import en cours…';
  try {
    const r = await apiFetch('/api/produits/import/xlsx', { method: 'POST', body: fd });
    const lignes = [
      `Mode : ${r.mode}`,
      `Créés : ${r.crees}`,
      `Mis à jour : ${r.mis_a_jour}`,
      `Ignorés : ${r.ignores}`,
    ];
    if (r.erreurs && r.erreurs.length) {
      lignes.push(`Erreurs (${r.erreurs.length}) :`);
      r.erreurs.slice(0, 10).forEach(e => lignes.push(`  • ${e}`));
      if (r.erreurs.length > 10) lignes.push(`  … (+${r.erreurs.length - 10})`);
    }
    elImportResultat.className = 'cat-import-resultat cat-import-resultat--ok';
    elImportResultat.textContent = lignes.join('\n');
    await chargerProduits();
    await chargerCategories();
  } catch (err) {
    elImportResultat.className = 'cat-import-resultat cat-import-resultat--err';
    elImportResultat.textContent = `Erreur : ${err.message}`;
  }
}

// ── Listeners ──────────────────────────────────────────────
$('cat-btn-nouveau').addEventListener('click', ouvrirModalCreation);
$('cat-modal-fermer').addEventListener('click', fermerModal);
$('cat-btn-annuler').addEventListener('click', fermerModal);
elBtnSupprimer.addEventListener('click', archiverProduit);
elForm.addEventListener('submit', soumettre);

// Rafraîchir le code auto uniquement en mode création (pas d'id)
f.espece.addEventListener('change', () => { if (!f.id.value) rafraichirCodePreview(); });
f.abats.addEventListener('change',  () => { if (!f.id.value) rafraichirCodePreview(); });

$('cat-btn-import').addEventListener('click', ouvrirImport);
$('cat-import-fermer').addEventListener('click', fermerImport);
$('cat-import-annuler').addEventListener('click', fermerImport);
$('cat-import-lancer').addEventListener('click', lancerImport);

// Recherche / filtres avec debounce léger
let debounceId = null;
function debounceRendre() {
  clearTimeout(debounceId);
  debounceId = setTimeout(rendre, 120);
}
elSearch.addEventListener('input', debounceRendre);
elFType.addEventListener('change', rendre);
elFCateg.addEventListener('change', rendre);
elFCond.addEventListener('change', rendre);
elFIncomplets.addEventListener('change', rendre);
elFArchives.addEventListener('change', chargerProduits);

// Fermer modal au clic hors carte
[elModal, elImportModal].forEach(m => {
  m.addEventListener('click', e => {
    if (e.target === m) m.hidden = true;
  });
});

// Échap = ferme
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    if (!elModal.hidden) fermerModal();
    if (!elImportModal.hidden) fermerImport();
  }
});

// ── Init ───────────────────────────────────────────────────
(async function init() {
  await Promise.all([chargerProduits(), chargerCategories()]);
})();

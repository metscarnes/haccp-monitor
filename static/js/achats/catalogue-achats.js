/* catalogue-achats.js — Catalogue fournisseur */

const API_CAT   = '/api/achats/catalogue';
const API_FOURN = '/api/achats/fournisseurs';

let articles     = [];
let fournisseurs = [];
let modeEdition  = false;
let listeFiltree = [];   // résultat du dernier filtrer()

// Tri
let triColonne   = 'designation';
let triSens      = 'asc';   // 'asc' | 'desc'

const DLC_LABELS = { dlc: 'DLC', date_abattage: 'Abattage', no_dlc: 'Sans DLC' };

const COLONNES = [
  { key: 'fournisseur_nom', label: 'Fournisseur' },
  { key: 'code_article',    label: 'Code article' },
  { key: 'designation',     label: 'Désignation' },
  { key: 'prix_achat_ht',   label: 'Prix HT' },
  { key: 'format_prix',     label: 'Format' },
  { key: 'unite_colis',     label: 'Unité colis' },
  { key: 'tva_percent',     label: 'TVA' },
  { key: 'conditionnement', label: 'Conditionnement' },
  { key: 'dlc_type',        label: 'DLC type' },
];

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await Promise.all([chargerFournisseurs(), chargerCatalogue()]);
  bindEvents();
  const params = new URLSearchParams(location.search);
  if (params.get('fournisseur')) {
    document.getElementById('filtre-fournisseur').value = params.get('fournisseur');
    filtrer();
  }
});

function bindEvents() {
  document.getElementById('btn-nouveau').addEventListener('click', ouvrirNouveauModal);
  document.getElementById('btn-export').addEventListener('click', exporterCatalogue);
  document.getElementById('btn-import').addEventListener('click', () => {
    document.getElementById('modal-import').hidden = false;
  });
  document.getElementById('modal-fermer').addEventListener('click', fermerModal);
  document.getElementById('btn-annuler').addEventListener('click', fermerModal);
  document.getElementById('import-fermer').addEventListener('click', () => { document.getElementById('modal-import').hidden = true; });
  document.getElementById('import-annuler').addEventListener('click', () => { document.getElementById('modal-import').hidden = true; });
  document.getElementById('import-lancer').addEventListener('click', lancerImport);
  document.getElementById('form-article').addEventListener('submit', sauver);

  // Filtres
  document.getElementById('filtre-fournisseur').addEventListener('change', filtrer);
  document.getElementById('filtre-format-prix').addEventListener('change', filtrer);
  document.getElementById('filtre-unite-colis').addEventListener('change', filtrer);
  document.getElementById('filtre-dlc').addEventListener('change', filtrer);
  document.getElementById('filtre-search').addEventListener('input', filtrer);
  document.getElementById('filtre-afficher-test').addEventListener('change', filtrer);
  document.getElementById('filtre-inactifs').addEventListener('change', filtrer);
  document.getElementById('filtre-sans-prix').addEventListener('change', filtrer);

  // Actions en masse
  document.getElementById('btn-masse-desactiver').addEventListener('click', () => actionMasse('desactiver'));
  document.getElementById('btn-masse-reactiver').addEventListener('click', () => actionMasse('reactiver'));
  document.getElementById('btn-masse-supprimer').addEventListener('click', () => actionMasse('supprimer'));
}

// ── Chargement ───────────────────────────────────────────────
async function chargerFournisseurs() {
  const r = await fetch(API_FOURN);
  fournisseurs = await r.json();
  const sel     = document.getElementById('filtre-fournisseur');
  const selForm = document.getElementById('a-fournisseur');
  fournisseurs.forEach(f => {
    sel.insertAdjacentHTML('beforeend', `<option value="${f.id}">${escHtml(f.nom)}</option>`);
    selForm.insertAdjacentHTML('beforeend', `<option value="${f.id}">${escHtml(f.nom)}</option>`);
  });
}

async function chargerCatalogue() {
  try {
    const r = await fetch(`${API_CAT}?actif_only=false`);
    articles = await r.json();
    afficherStats();
    filtrer();
  } catch(e) {
    afficherErreur('Impossible de charger le catalogue : ' + e.message);
  }
}

function estTest(a) {
  return (a.fournisseur_nom || '').toLowerCase().includes('test');
}

function afficherStats() {
  const actifs   = articles.filter(a => a.actif && !estTest(a));
  const fourn    = new Set(actifs.map(a => a.fournisseur_id)).size;
  const sansPrix = actifs.filter(a => !a.prix_achat_ht || a.prix_achat_ht === 0);
  document.getElementById('stat-total').textContent       = actifs.length;
  document.getElementById('stat-fournisseurs').textContent = fourn;
  document.getElementById('stat-sans-prix').textContent   = sansPrix.length;
}

// ── Filtrer + Trier ──────────────────────────────────────────
function filtrer() {
  const fourn            = document.getElementById('filtre-fournisseur').value;
  const formatPrix       = document.getElementById('filtre-format-prix').value;
  const uniteColis       = document.getElementById('filtre-unite-colis').value;
  const dlc              = document.getElementById('filtre-dlc').value;
  const search           = document.getElementById('filtre-search').value.toLowerCase();
  const afficherTest     = document.getElementById('filtre-afficher-test').checked;
  const afficherInactifs = document.getElementById('filtre-inactifs').checked;
  const sansPrixOnly     = document.getElementById('filtre-sans-prix').checked;

  listeFiltree = articles.filter(a => {
    if (!afficherTest     && estTest(a))                              return false;
    if (!afficherInactifs && !a.actif)                               return false;
    if (fourn      && String(a.fournisseur_id) !== fourn)            return false;
    if (formatPrix && a.format_prix !== formatPrix)                  return false;
    if (uniteColis && a.unite_colis !== uniteColis)                  return false;
    if (dlc        && a.dlc_type !== dlc)                            return false;
    if (sansPrixOnly && a.prix_achat_ht > 0)                        return false;
    if (search && !a.designation.toLowerCase().includes(search)
               && !a.code_article.toLowerCase().includes(search))   return false;
    return true;
  });

  trier();
}

function trier() {
  const k = triColonne;
  listeFiltree.sort((a, b) => {
    let va = a[k] ?? '';
    let vb = b[k] ?? '';
    if (typeof va === 'number' && typeof vb === 'number') {
      return triSens === 'asc' ? va - vb : vb - va;
    }
    va = String(va).toLowerCase();
    vb = String(vb).toLowerCase();
    if (va < vb) return triSens === 'asc' ? -1 : 1;
    if (va > vb) return triSens === 'asc' ?  1 : -1;
    return 0;
  });
  afficherTable(listeFiltree);
  document.getElementById('stat-affiches').textContent   = listeFiltree.length;
  document.getElementById('resultat-count').textContent  = `${listeFiltree.length} article${listeFiltree.length > 1 ? 's' : ''}`;
  majEnTetes();
  majBarreMasse();
}

function changerTri(key) {
  if (triColonne === key) {
    triSens = triSens === 'asc' ? 'desc' : 'asc';
  } else {
    triColonne = key;
    triSens    = 'asc';
  }
  trier();
}

function majEnTetes() {
  COLONNES.forEach(c => {
    const th = document.getElementById(`th-${c.key}`);
    if (!th) return;
    const fleche = triColonne === c.key ? (triSens === 'asc' ? ' ▲' : ' ▼') : ' ⇅';
    th.textContent = c.label + fleche;
  });
}

// ── Tableau ──────────────────────────────────────────────────
function afficherTable(liste) {
  const tbody = document.getElementById('tbody-catalogue');
  if (!liste.length) {
    tbody.innerHTML = `<tr><td colspan="${COLONNES.length + 2}" class="ach-vide">Aucun article trouvé</td></tr>`;
    return;
  }
  tbody.innerHTML = liste.map(a => `
    <tr class="${!a.actif ? 'ach-row--inactif' : ''}">
      <td style="width:36px;text-align:center;">
        <input type="checkbox" class="chk-article" data-id="${a.id}"
               style="width:18px;height:18px;accent-color:var(--color-accent);">
      </td>
      <td>${escHtml(a.fournisseur_nom)}</td>
      <td><code>${escHtml(a.code_article)}</code></td>
      <td class="ach-cell-nom">
        ${escHtml(a.designation)}
        ${!a.actif ? ' <span class="ach-badge ach-badge--annulee">Inactif</span>' : ''}
      </td>
      <td class="ach-col-num">${fmtPrix(a.prix_achat_ht)} €</td>
      <td><span class="ach-badge ach-badge--${a.format_prix === 'piece' ? 'abattage' : 'dlc'}">${a.format_prix === 'piece' ? '€/pièce' : '€/kg'}</span></td>
      <td>${a.unite_colis ? escHtml(a.unite_colis) : '<span style="color:#9ca3af">—</span>'}</td>
      <td>${a.tva_percent ?? 5.5}%</td>
      <td>${escHtml(a.conditionnement || '—')}</td>
      <td>
        <span class="ach-badge ach-badge--${a.dlc_type === 'dlc' ? 'dlc' : a.dlc_type === 'date_abattage' ? 'abattage' : 'no-dlc'}">
          ${DLC_LABELS[a.dlc_type] || a.dlc_type}
        </span>
      </td>
      <td class="ach-col-actions">
        <button class="ach-btn ach-btn--small" onclick="ouvrirEditionModal(${a.id})">Modifier</button>
        ${a.actif
          ? `<button class="ach-btn ach-btn--small ach-btn--danger" onclick="toggleActif(${a.id}, false)" title="Désactiver">✕</button>`
          : `<button class="ach-btn ach-btn--small ach-btn--ok"    onclick="toggleActif(${a.id}, true)"  title="Réactiver">↺</button>`
        }
      </td>
    </tr>
  `).join('');

  // Checkbox "tout sélectionner"
  document.getElementById('chk-tout').checked = false;
  document.getElementById('chk-tout').addEventListener('change', e => {
    document.querySelectorAll('.chk-article').forEach(c => c.checked = e.target.checked);
    majBarreMasse();
  });
  document.querySelectorAll('.chk-article').forEach(c => {
    c.addEventListener('change', majBarreMasse);
  });
}

// ── Sélection & Actions en masse ─────────────────────────────
function idsSelectionnes() {
  return [...document.querySelectorAll('.chk-article:checked')].map(c => parseInt(c.dataset.id));
}

function majBarreMasse() {
  const ids = idsSelectionnes();
  const barre = document.getElementById('barre-masse');
  const nbEl  = document.getElementById('masse-nb');
  barre.hidden = ids.length === 0;
  if (nbEl) nbEl.textContent = ids.length;
}

async function actionMasse(action) {
  const ids = idsSelectionnes();
  if (!ids.length) return;

  const labels = { desactiver: 'désactiver', reactiver: 'réactiver', supprimer: 'supprimer définitivement' };
  if (!confirm(`${labels[action]} ${ids.length} article(s) ?`)) return;

  const btn = document.getElementById(`btn-masse-${action}`);
  btn.disabled = true;

  try {
    await Promise.all(ids.map(id => {
      if (action === 'desactiver') return fetch(`${API_CAT}/${id}`, { method: 'DELETE' });
      if (action === 'reactiver')  return fetch(`${API_CAT}/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actif: true }) });
      if (action === 'supprimer')  return fetch(`${API_CAT}/${id}`, { method: 'DELETE' }); // même endpoint pour l'instant
    }));
    await chargerCatalogue();
  } finally {
    btn.disabled = false;
  }
}

// ── Activer / Désactiver ligne ───────────────────────────────
async function toggleActif(id, actif) {
  await fetch(`${API_CAT}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ actif }),
  });
  await chargerCatalogue();
}

// ── Modal article ────────────────────────────────────────────
function ouvrirNouveauModal() {
  modeEdition = false;
  document.getElementById('modal-titre').textContent = 'Nouvel article';
  viderForm();
  document.getElementById('modal-article').hidden = false;
  document.getElementById('a-code').focus();
}

function ouvrirEditionModal(id) {
  const a = articles.find(x => x.id === id);
  if (!a) return;
  modeEdition = true;
  document.getElementById('modal-titre').textContent = 'Modifier — ' + a.designation;
  document.getElementById('a-id').value = a.id;
  document.getElementById('a-fournisseur').value = a.fournisseur_id;
  document.getElementById('a-code').value = a.code_article;
  document.getElementById('a-designation').value = a.designation;
  document.getElementById('a-prix').value = a.prix_achat_ht;
  document.getElementById('a-format-prix').value = a.format_prix || 'kg';
  document.getElementById('a-unite-colis').value = a.unite_colis || '';
  document.getElementById('a-tva').value = a.tva_percent ?? 5.5;
  document.getElementById('a-conditionnement').value = a.conditionnement || '';
  document.getElementById('a-dlc-type').value = a.dlc_type || 'dlc';
  document.getElementById('form-erreur').hidden = true;
  document.getElementById('modal-article').hidden = false;
}

function fermerModal() {
  document.getElementById('modal-article').hidden = true;
}

function viderForm() {
  ['a-id','a-code','a-designation','a-prix','a-conditionnement'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('a-format-prix').value = 'kg';
  document.getElementById('a-unite-colis').value = '';
  document.getElementById('a-tva').value = '5.5';
  document.getElementById('a-dlc-type').value = 'dlc';
  document.getElementById('form-erreur').hidden = true;
}

async function sauver(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-sauver');
  btn.disabled = true; btn.textContent = 'Enregistrement…';

  const body = {
    fournisseur_id:  parseInt(document.getElementById('a-fournisseur').value),
    code_article:    document.getElementById('a-code').value.trim(),
    designation:     document.getElementById('a-designation').value.trim(),
    prix_achat_ht:   parseFloat(document.getElementById('a-prix').value),
    format_prix:     document.getElementById('a-format-prix').value,
    unite_colis:     document.getElementById('a-unite-colis').value || null,
    tva_percent:     parseFloat(document.getElementById('a-tva').value),
    conditionnement: document.getElementById('a-conditionnement').value.trim() || null,
    dlc_type:        document.getElementById('a-dlc-type').value,
  };

  try {
    const id = document.getElementById('a-id').value;
    const url    = modeEdition ? `${API_CAT}/${id}` : API_CAT;
    const method = modeEdition ? 'PUT' : 'POST';
    const r = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error((await r.json()).detail || 'Erreur');
    fermerModal();
    await chargerCatalogue();
  } catch(err) {
    const z = document.getElementById('form-erreur');
    z.textContent = err.message; z.hidden = false;
  } finally {
    btn.disabled = false; btn.textContent = 'Enregistrer';
  }
}

// ── Export Excel ─────────────────────────────────────────────
function exporterCatalogue() {
  const fournisseurId = document.getElementById('filtre-fournisseur').value;
  const url = '/api/achats/catalogue/export' + (fournisseurId ? `?fournisseur_id=${fournisseurId}` : '');
  window.location.href = url;
}

// ── Import Excel ─────────────────────────────────────────────
async function lancerImport() {
  const fichier = document.getElementById('import-fichier').files[0];
  if (!fichier) { alert('Sélectionnez un fichier Excel'); return; }

  const btn = document.getElementById('import-lancer');
  btn.disabled = true; btn.textContent = 'Import en cours…';

  const formData = new FormData();
  formData.append('fichier', fichier);

  try {
    const r = await fetch(`${API_CAT}/import/upload`, { method: 'POST', body: formData });
    const result = await r.json();
    const zone = document.getElementById('import-resultat');
    zone.hidden = false;
    if (r.ok) {
      zone.className = 'ach-import-resultat ach-import-resultat--ok';
      zone.textContent = `✅ Import terminé\nCréés : ${result.crees}\nMis à jour : ${result.mis_a_jour}\n${result.erreurs?.length ? 'Erreurs :\n' + result.erreurs.join('\n') : ''}`;
      await chargerCatalogue();
    } else {
      zone.className = 'ach-import-resultat ach-import-resultat--err';
      zone.textContent = '❌ Erreur : ' + (result.detail || JSON.stringify(result));
    }
  } catch(e) {
    alert('Erreur : ' + e.message);
  } finally {
    btn.disabled = false; btn.textContent = 'Importer';
  }
}

// ── Utilitaires ──────────────────────────────────────────────
function afficherErreur(msg) {
  const z = document.getElementById('zone-erreur');
  z.textContent = msg; z.hidden = false;
}
function fmtPrix(v) { return (v ?? 0).toFixed(2); }
function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

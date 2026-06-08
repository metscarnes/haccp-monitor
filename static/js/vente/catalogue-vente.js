/* catalogue-vente.js — Catalogue de vente (produits finis fabriqués) */

const API_VENTE = '/api/vente/catalogue';

function triggerDownload(url, filename) {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

let produits     = [];
let modeEdition  = false;
let listeFiltree = [];

// Tri
let triColonne = 'nom';
let triSens    = 'asc';

const COLONNES = [
  { key: 'nom',                      label: 'Nom' },
  { key: 'code_vente',               label: 'Code' },
  { key: 'prix_vente_ttc',           label: 'Prix TTC' },
  { key: 'tva_percent',              label: 'TVA' },
  { key: 'dlc_jours',               label: 'DLC (j)' },
  { key: 'temperature_conservation', label: 'Température' },
  { key: 'famille',                  label: 'Famille' },
  { key: 'sous_famille',             label: 'Sous-famille' },
];

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  peuplerSelectFamille(document.getElementById('v-famille'), document.getElementById('v-sous-famille'), '');
  bindEvents();
  charger();
});

function bindEvents() {
  document.getElementById('btn-nouveau').addEventListener('click', ouvrirNouveau);
  document.getElementById('btn-export').addEventListener('click', () => { triggerDownload('/api/vente/catalogue/export', 'catalogue_vente.xlsx'); });
  document.getElementById('btn-template').addEventListener('click', () => { triggerDownload('/api/vente/catalogue/template', 'template_catalogue_vente.xlsx'); });
  document.getElementById('btn-import').addEventListener('click', () => {
    document.getElementById('import-fichier').value = '';
    document.getElementById('import-resultat').hidden = true;
    document.getElementById('import-lancer').disabled = true;
    document.getElementById('modal-import').hidden = false;
  });
  document.getElementById('import-fermer').addEventListener('click', () => { document.getElementById('modal-import').hidden = true; });
  document.getElementById('import-annuler').addEventListener('click', () => { document.getElementById('modal-import').hidden = true; });
  document.getElementById('import-fichier').addEventListener('change', e => {
    document.getElementById('import-lancer').disabled = !e.target.files.length;
  });
  document.getElementById('import-lancer').addEventListener('click', lancerImport);

  document.getElementById('modal-fermer').addEventListener('click', fermerModal);
  document.getElementById('btn-annuler').addEventListener('click', fermerModal);
  document.getElementById('btn-supprimer').addEventListener('click', supprimer);
  document.getElementById('form-vente').addEventListener('submit', sauver);

  // Filtres
  document.getElementById('filtre-search').addEventListener('input', filtrer);
  document.getElementById('filtre-inactifs').addEventListener('change', charger);
  document.getElementById('filtre-sans-prix').addEventListener('change', filtrer);
  document.getElementById('filtre-famille').addEventListener('change', () => {
    const fam = document.getElementById('filtre-famille').value;
    const sel = document.getElementById('filtre-sous-famille');
    majSousFamille(fam, sel, '');
    const opt0 = document.createElement('option');
    opt0.value = ''; opt0.textContent = 'Toutes';
    sel.insertBefore(opt0, sel.firstChild);
    sel.value = '';
    filtrer();
  });
  document.getElementById('filtre-sous-famille').addEventListener('change', filtrer);

  // Formulaire modal
  document.getElementById('v-famille').addEventListener('change', () => {
    majSousFamille(
      document.getElementById('v-famille').value,
      document.getElementById('v-sous-famille'),
      ''
    );
  });

  // Checkbox "tout sélectionner"
  document.getElementById('chk-tout').addEventListener('change', e => {
    document.querySelectorAll('.chk-produit').forEach(c => c.checked = e.target.checked);
    majBarreMasse();
  });

  // Délégation : checkboxes lignes
  document.getElementById('tbody-vente').addEventListener('change', e => {
    if (e.target.classList.contains('chk-produit')) majBarreMasse();
  });

  // Actions en masse
  document.getElementById('btn-masse-modifier').addEventListener('click', ouvrirModalMasse);
  document.getElementById('btn-masse-desactiver').addEventListener('click', () => actionMasse('desactiver'));
  document.getElementById('btn-masse-reactiver').addEventListener('click', () => actionMasse('reactiver'));
  document.getElementById('btn-masse-supprimer').addEventListener('click', () => actionMasse('supprimer'));
  document.getElementById('modal-masse-fermer').addEventListener('click', fermerModalMasse);
  document.getElementById('masse-annuler').addEventListener('click', fermerModalMasse);
  document.getElementById('masse-champ').addEventListener('change', majZoneValeurMasse);
  document.getElementById('masse-appliquer').addEventListener('click', appliquerMasse);
}

// ── Chargement ───────────────────────────────────────────────
async function charger() {
  const inactifs = document.getElementById('filtre-inactifs').checked;
  try {
    const r = await fetch(`${API_VENTE}?actif_only=${inactifs ? 'false' : 'true'}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    produits = await r.json();
    afficherStats();
    filtrer();
  } catch (e) {
    afficherErreur('Impossible de charger le catalogue de vente : ' + e.message);
  }
}

function afficherStats() {
  const actifs    = produits.filter(p => p.actif);
  const sansPrix  = actifs.filter(p => !p.prix_vente_ttc || p.prix_vente_ttc === 0);
  document.getElementById('stat-total').textContent    = actifs.length;
  document.getElementById('stat-sans-prix').textContent = sansPrix.length;
}

// ── Filtrer + Trier ──────────────────────────────────────────
function filtrer() {
  const search      = document.getElementById('filtre-search').value.toLowerCase();
  const famille     = document.getElementById('filtre-famille').value;
  const sousFamille = document.getElementById('filtre-sous-famille').value;
  const sansPrixOnly = document.getElementById('filtre-sans-prix').checked;

  listeFiltree = produits.filter(p => {
    if (famille     && p.famille     !== famille)      return false;
    if (sousFamille && p.sous_famille !== sousFamille)  return false;
    if (sansPrixOnly && p.prix_vente_ttc > 0)           return false;
    if (search && !(p.nom || '').toLowerCase().includes(search)
               && !(p.code_vente || '').toLowerCase().includes(search)) return false;
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
  document.getElementById('stat-affiches').textContent  = listeFiltree.length;
  document.getElementById('resultat-count').textContent = `${listeFiltree.length} produit${listeFiltree.length > 1 ? 's' : ''}`;
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
  const tbody = document.getElementById('tbody-vente');
  if (!liste.length) {
    tbody.innerHTML = `<tr><td colspan="${COLONNES.length + 2}" class="ach-vide">Aucun produit fini trouvé</td></tr>`;
    return;
  }
  tbody.innerHTML = liste.map(p => `
    <tr class="${!p.actif ? 'ach-row--inactif' : ''}">
      <td style="width:36px;text-align:center;padding:0 8px;">
        <input type="checkbox" class="chk-produit" data-id="${p.id}"
               style="width:20px;height:20px;accent-color:var(--color-accent);display:block;margin:auto;cursor:pointer;opacity:1;visibility:visible;appearance:checkbox;-webkit-appearance:checkbox;">
      </td>
      <td class="ach-cell-nom">
        ${escHtml(p.nom)}
        ${!p.actif ? ' <span class="ach-badge ach-badge--annulee">Inactif</span>' : ''}
      </td>
      <td>${p.code_vente ? `<code>${escHtml(p.code_vente)}</code>` : '<span style="color:#9ca3af">—</span>'}</td>
      <td class="ach-col-num">${p.prix_vente_ttc != null ? p.prix_vente_ttc.toFixed(2) + ' €' : '<span style="color:#9ca3af">—</span>'}</td>
      <td>${fmtTva(p.tva_percent)}%</td>
      <td class="ach-col-num">${p.dlc_jours ?? '—'}</td>
      <td>${escHtml(p.temperature_conservation || '—')}</td>
      <td>${p.famille ? escHtml(p.famille) : '<span style="color:#9ca3af">—</span>'}</td>
      <td>${p.sous_famille ? escHtml(p.sous_famille) : '<span style="color:#9ca3af">—</span>'}</td>
      <td class="ach-col-actions">
        <button class="ach-btn ach-btn--small" onclick="ouvrirEdition(${p.id})">Modifier</button>
        ${p.actif
          ? `<button class="ach-btn ach-btn--small ach-btn--danger" onclick="toggleActif(${p.id}, false)" title="Désactiver">✕</button>`
          : `<button class="ach-btn ach-btn--small ach-btn--ok" onclick="toggleActif(${p.id}, true)" title="Réactiver">↺</button>`
        }
      </td>
    </tr>`).join('');

  document.getElementById('chk-tout').checked = false;
}

// ── Sélection & Actions en masse ─────────────────────────────
function idsSelectionnes() {
  return [...document.querySelectorAll('.chk-produit:checked')].map(c => parseInt(c.dataset.id));
}

function majBarreMasse() {
  const ids  = idsSelectionnes();
  const barre = document.getElementById('barre-masse');
  if (ids.length > 0) {
    barre.removeAttribute('hidden');
  } else {
    barre.setAttribute('hidden', '');
  }
  document.getElementById('masse-nb').textContent = ids.length;
  const modalNb = document.getElementById('masse-modal-nb');
  if (modalNb) modalNb.textContent = ids.length;
}

async function actionMasse(action) {
  const ids = idsSelectionnes();
  if (!ids.length) return;

  const labels = { desactiver: 'désactiver', reactiver: 'réactiver', supprimer: 'supprimer définitivement' };
  if (!confirm(`${labels[action]} ${ids.length} produit(s) ?`)) return;

  const btn = document.getElementById(`btn-masse-${action}`);
  btn.disabled = true;

  try {
    await Promise.all(ids.map(id => {
      if (action === 'desactiver') return fetch(`${API_VENTE}/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actif: false }) });
      if (action === 'reactiver')  return fetch(`${API_VENTE}/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actif: true }) });
      if (action === 'supprimer')  return fetch(`${API_VENTE}/${id}?permanent=true`, { method: 'DELETE' });
    }));
    await charger();
  } finally {
    btn.disabled = false;
  }
}

// ── Modal modification en masse ──────────────────────────────
function ouvrirModalMasse() {
  const ids = idsSelectionnes();
  if (!ids.length) return;
  document.getElementById('masse-modal-nb').textContent = ids.length;
  document.getElementById('masse-champ').value = '';
  document.getElementById('masse-valeur-zone').hidden = true;
  document.getElementById('masse-valeur-zone').innerHTML = '';
  document.getElementById('masse-erreur').hidden = true;
  document.getElementById('masse-appliquer').disabled = true;
  document.getElementById('modal-masse').hidden = false;
}

function fermerModalMasse() {
  document.getElementById('modal-masse').hidden = true;
}

function majZoneValeurMasse() {
  const champ = document.getElementById('masse-champ').value;
  const zone  = document.getElementById('masse-valeur-zone');
  document.getElementById('masse-appliquer').disabled = !champ;
  if (!champ) { zone.hidden = true; zone.innerHTML = ''; return; }

  const champStyle = 'min-height:44px;padding:.5rem .75rem;border:1px solid #d4c5af;border-radius:8px;font-size:1rem;width:100%;';

  const CHAMPS = {
    tva_percent: {
      label: 'Nouveau taux TVA (%)',
      html: () => `<select id="masse-val" style="${champStyle}">
        <option value="5.5">5,5% (alimentaire)</option>
        <option value="10">10%</option>
        <option value="20">20%</option></select>`,
    },
    dlc_jours: {
      label: 'Nouvelle DLC (jours)',
      html: () => `<input type="number" id="masse-val" min="0" max="365" placeholder="ex : 3"
        style="${champStyle}">`,
    },
    temperature_conservation: {
      label: 'Nouvelle température',
      html: () => `<select id="masse-val" style="${champStyle}">
        <option value="0°C à +4°C">0°C à +4°C (réfrigéré)</option>
        <option value="+2°C / +4°C">+2°C / +4°C (viande fraîche)</option>
        <option value="-18°C">-18°C (congelé)</option>
        <option value="Ambiant">Ambiant</option></select>`,
    },
    format_etiquette: {
      label: 'Nouveau format d\'étiquette',
      html: () => `<select id="masse-val" style="${champStyle}">
        <option value="standard_60x40">Standard 60×40</option>
        <option value="grand_100x60">Grand 100×60</option>
        <option value="petit_40x30">Petit 40×30</option></select>`,
    },
    famille: {
      label: 'Nouvelle famille',
      html: () => {
        const opts = Object.keys(FAMILLES).map(f => `<option value="${escHtml(f)}">${escHtml(f)}</option>`).join('');
        return `
          <select id="masse-val" style="${champStyle}">
            <option value="">— Sélectionnez —</option>${opts}
          </select>
          <label style="font-size:var(--text-sm);font-weight:600;color:#4b5563;margin-top:8px;">Sous-famille (facultatif)</label>
          <select id="masse-val-sf" disabled style="${champStyle}">
            <option value="">— Choisir une famille d'abord —</option>
          </select>`;
      },
    },
  };

  const cfg = CHAMPS[champ];
  if (!cfg) { zone.hidden = true; return; }

  zone.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:4px;">
      <label style="font-size:var(--text-sm);font-weight:600;color:#4b5563;">${cfg.label}</label>
      ${cfg.html()}
    </div>`;
  zone.hidden = false;

  if (champ === 'famille') {
    const selFam = document.getElementById('masse-val');
    const selSf  = document.getElementById('masse-val-sf');
    selFam.addEventListener('change', () => {
      const liste = FAMILLES[selFam.value] || [];
      if (!selFam.value) {
        selSf.innerHTML = '<option value="">— Choisir une famille d\'abord —</option>';
        selSf.disabled  = true;
        return;
      }
      selSf.disabled = false;
      selSf.innerHTML = '<option value="">— Aucune —</option>'
        + liste.map(s => `<option value="${escHtml(s)}">${escHtml(s)}</option>`).join('');
    });
  }
}

async function appliquerMasse() {
  const ids   = idsSelectionnes();
  const champ = document.getElementById('masse-champ').value;
  const valEl = document.getElementById('masse-val');
  if (!ids.length || !champ || !valEl) return;

  let valeur = valEl.value;
  if (champ === 'tva_percent') valeur = parseFloat(valeur);
  if (champ === 'dlc_jours')  valeur = parseInt(valeur, 10);
  if (!valeur && valeur !== 0) {
    const z = document.getElementById('masse-erreur');
    z.textContent = 'Valeur obligatoire'; z.hidden = false;
    return;
  }

  let payload = { [champ]: valeur };
  if (champ === 'famille') {
    payload.sous_famille = document.getElementById('masse-val-sf').value || '';
  }

  const btn = document.getElementById('masse-appliquer');
  btn.disabled = true; btn.textContent = 'Application…';

  try {
    await Promise.all(ids.map(id =>
      fetch(`${API_VENTE}/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    ));
    fermerModalMasse();
    await charger();
  } catch(e) {
    const z = document.getElementById('masse-erreur');
    z.textContent = 'Erreur : ' + e.message; z.hidden = false;
  } finally {
    btn.disabled = false; btn.textContent = 'Appliquer';
  }
}

// ── Activer / désactiver ─────────────────────────────────────
async function toggleActif(id, actif) {
  await fetch(`${API_VENTE}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ actif }),
  });
  await charger();
}

// ── Modal ────────────────────────────────────────────────────
function ouvrirNouveau() {
  modeEdition = false;
  document.getElementById('modal-titre').textContent = 'Nouveau produit fini';
  document.getElementById('btn-supprimer').hidden = true;
  viderForm();
  peuplerSelectFamille(document.getElementById('v-famille'), document.getElementById('v-sous-famille'), '');
  document.getElementById('modal-vente').hidden = false;
  document.getElementById('v-nom').focus();
}

function ouvrirEdition(id) {
  const p = produits.find(x => x.id === id);
  if (!p) return;
  modeEdition = true;
  document.getElementById('modal-titre').textContent = 'Modifier — ' + p.nom;
  document.getElementById('v-id').value = p.id;
  document.getElementById('v-nom').value = p.nom || '';
  document.getElementById('v-prix').value = p.prix_vente_ttc ?? '';
  document.getElementById('v-tva').value = p.tva_percent ?? 5.5;
  document.getElementById('v-dlc').value = p.dlc_jours ?? 3;
  document.getElementById('v-temp').value = p.temperature_conservation || '0°C à +4°C';
  document.getElementById('v-format').value = p.format_etiquette || 'standard_60x40';
  peuplerSelectFamille(document.getElementById('v-famille'), document.getElementById('v-sous-famille'), p.famille || '');
  majSousFamille(p.famille || '', document.getElementById('v-sous-famille'), p.sous_famille || '');
  document.getElementById('v-code').value = p.code_vente || '';
  document.getElementById('btn-supprimer').hidden = false;
  document.getElementById('form-erreur').hidden = true;
  document.getElementById('modal-vente').hidden = false;
}

function fermerModal() {
  document.getElementById('modal-vente').hidden = true;
}

function viderForm() {
  document.getElementById('v-id').value = '';
  document.getElementById('v-nom').value = '';
  document.getElementById('v-prix').value = '';
  document.getElementById('v-tva').value = '5.5';
  document.getElementById('v-dlc').value = '3';
  document.getElementById('v-temp').value = '0°C à +4°C';
  document.getElementById('v-format').value = 'standard_60x40';
  document.getElementById('v-code').value = '';
  document.getElementById('form-erreur').hidden = true;
}

async function sauver(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-sauver');
  btn.disabled = true; btn.textContent = 'Enregistrement…';

  const body = {
    nom:                      document.getElementById('v-nom').value.trim(),
    prix_vente_ttc:           parseFloat(document.getElementById('v-prix').value) || null,
    tva_percent:              parseFloat(document.getElementById('v-tva').value),
    dlc_jours:                parseInt(document.getElementById('v-dlc').value, 10) || 3,
    temperature_conservation: document.getElementById('v-temp').value,
    format_etiquette:         document.getElementById('v-format').value,
    famille:                  document.getElementById('v-famille').value || null,
    sous_famille:             document.getElementById('v-sous-famille').value || null,
    code_vente:               document.getElementById('v-code').value.trim() || null,
  };

  try {
    const id = document.getElementById('v-id').value;
    const url    = modeEdition ? `${API_VENTE}/${id}` : API_VENTE;
    const method = modeEdition ? 'PUT' : 'POST';
    const r = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error((await r.json()).detail || 'Erreur');
    fermerModal();
    await charger();
  } catch (err) {
    const z = document.getElementById('form-erreur');
    z.textContent = err.message; z.hidden = false;
  } finally {
    btn.disabled = false; btn.textContent = 'Enregistrer';
  }
}

async function supprimer() {
  const id  = document.getElementById('v-id').value;
  const nom = document.getElementById('v-nom').value;
  if (!confirm(`Supprimer définitivement "${nom}" ?\n\nLes recettes qui l'utilisent seront déliées. Cette action est irréversible.`)) return;
  const btn = document.getElementById('btn-supprimer');
  btn.disabled = true; btn.textContent = 'Suppression…';
  try {
    const r = await fetch(`${API_VENTE}/${id}?permanent=true`, { method: 'DELETE' });
    if (!r.ok) throw new Error((await r.json()).detail || 'Erreur serveur');
    fermerModal();
    await charger();
  } catch (err) {
    const z = document.getElementById('form-erreur');
    z.textContent = err.message; z.hidden = false;
  } finally {
    btn.disabled = false; btn.textContent = 'Supprimer';
  }
}

// ── Import Excel ─────────────────────────────────────────────
let importEnCours = false;

async function lancerImport() {
  if (importEnCours) return;
  const inputFichier = document.getElementById('import-fichier');
  const fichier = inputFichier.files[0];
  if (!fichier) { alert('Sélectionnez un fichier Excel'); return; }

  const btn = document.getElementById('import-lancer');
  importEnCours = true;
  btn.disabled = true; btn.textContent = 'Import en cours…';

  const formData = new FormData();
  formData.append('fichier', fichier);

  try {
    const r = await fetch('/api/vente/catalogue/import', { method: 'POST', body: formData });
    const result = await r.json();
    const zone = document.getElementById('import-resultat');
    zone.hidden = false;

    if (r.ok) {
      const erreurs = result.erreurs?.length ? `\nErreurs : ${result.erreurs.length}` : '';
      zone.className = 'ach-import-resultat ach-import-resultat--ok';
      zone.textContent = `✅ Import terminé\nCréés : ${result.crees}\nMis à jour : ${result.mis_a_jour}${result.erreurs?.length ? '\nErreurs :\n' + result.erreurs.join('\n') : ''}`;
      await charger();
      alert(`✅ Import validé\n\nProduits créés : ${result.crees}\nProduits mis à jour : ${result.mis_a_jour}${erreurs}`);
      document.getElementById('modal-import').hidden = true;
      inputFichier.value = '';
      zone.hidden = true;
      btn.textContent = 'Importer';
      return;
    }

    zone.className = 'ach-import-resultat ach-import-resultat--err';
    zone.textContent = '❌ Erreur : ' + (result.detail || JSON.stringify(result));
    btn.disabled = false; btn.textContent = 'Importer';
  } catch(e) {
    alert('Erreur : ' + e.message);
    btn.disabled = false; btn.textContent = 'Importer';
  } finally {
    importEnCours = false;
  }
}

// ── Utilitaires ──────────────────────────────────────────────
function afficherErreur(msg) {
  const z = document.getElementById('zone-erreur');
  z.textContent = msg; z.hidden = false;
}
function fmtTva(v) {
  const n = v ?? 5.5;
  return Number.isInteger(n) ? String(n) : String(n).replace('.', ',');
}
function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

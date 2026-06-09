/* catalogue-achats.js — Catalogue fournisseur */

const API_CAT   = '/api/achats/catalogue';

function triggerDownload(url, filename) {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}
const API_FOURN = '/api/achats/fournisseurs';

let articles     = [];
let fournisseurs = [];
let modeEdition  = false;
let listeFiltree = [];   // résultat du dernier filtrer()

// Tri
let triColonne   = 'designation';
let triSens      = 'asc';   // 'asc' | 'desc'

const DLC_LABELS = { dlc: 'DLC', date_abattage: 'Abattage', no_dlc: 'Sans DLC' };

// FAMILLES est défini dans /static/js/core/familles.js (chargé avant ce script).

const COLONNES = [
  { key: 'fournisseur_nom', label: 'Fournisseur' },
  { key: 'code_article',    label: 'Code article' },
  { key: 'designation',     label: 'Désignation' },
  { key: 'prix_achat_ht',   label: 'Prix HT' },
  { key: 'format_prix',     label: 'Format' },
  { key: 'qte_par_colis',     label: 'Qté/colis' },
  { key: 'poids_unitaire_kg', label: 'Poids unit.' },
  { key: 'poids_colis_kg',    label: 'Poids colis' },
  { key: 'tva_percent',     label: 'TVA' },
  { key: 'unites_autorisees', label: 'Unités cmd' },
  { key: 'famille',         label: 'Famille' },
  { key: 'sous_famille',    label: 'Sous-famille' },
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
    // Ouvre la modale propre : pas de fichier → bouton désactivé, résultat masqué
    document.getElementById('import-fichier').value = '';
    document.getElementById('import-resultat').hidden = true;
    document.getElementById('import-lancer').disabled = true;
    document.getElementById('modal-import').hidden = false;
  });
  // Le bouton Importer ne s'active qu'une fois un fichier choisi
  document.getElementById('import-fichier').addEventListener('change', (e) => {
    document.getElementById('import-lancer').disabled = !e.target.files.length;
  });
  document.getElementById('modal-fermer').addEventListener('click', fermerModal);
  document.getElementById('btn-annuler').addEventListener('click', fermerModal);
  document.getElementById('btn-supprimer-article').addEventListener('click', supprimerArticle);
  document.getElementById('import-fermer').addEventListener('click', () => { document.getElementById('modal-import').hidden = true; });
  document.getElementById('import-annuler').addEventListener('click', () => { document.getElementById('modal-import').hidden = true; });
  document.getElementById('import-lancer').addEventListener('click', lancerImport);
  document.getElementById('form-article').addEventListener('submit', sauver);
  document.getElementById('a-qte-colis').addEventListener('input', recalcPoidsColis);
  document.getElementById('a-poids-unitaire').addEventListener('input', recalcPoidsColis);
  document.getElementById('a-famille').addEventListener('change', () => majSousFamilleForm());

  // Filtres
  document.getElementById('filtre-fournisseur').addEventListener('change', filtrer);
  document.getElementById('filtre-format-prix').addEventListener('change', filtrer);
  document.getElementById('filtre-famille').addEventListener('change', () => {
    const fam = document.getElementById('filtre-famille').value;
    const sel = document.getElementById('filtre-sous-famille');
    majSousFamille(fam, sel, '');
    // réinsérer "Toutes" en tête et forcer la sélection vide
    const opt0 = document.createElement('option');
    opt0.value = ''; opt0.textContent = 'Toutes';
    sel.insertBefore(opt0, sel.firstChild);
    sel.value = '';
    filtrer();
  });
  document.getElementById('filtre-sous-famille').addEventListener('change', filtrer);
  document.getElementById('filtre-dlc').addEventListener('change', filtrer);
  document.getElementById('filtre-search').addEventListener('input', filtrer);
  document.getElementById('filtre-afficher-test').addEventListener('change', filtrer);
  document.getElementById('filtre-inactifs').addEventListener('change', filtrer);
  document.getElementById('filtre-sans-prix').addEventListener('change', filtrer);
  document.getElementById('filtre-incomplets').addEventListener('change', filtrer);

  // Checkbox "tout sélectionner" — bindé une seule fois ici
  document.getElementById('chk-tout').addEventListener('change', e => {
    document.querySelectorAll('.chk-article').forEach(c => c.checked = e.target.checked);
    majBarreMasse();
  });

  // Délégation : un seul listener sur tbody pour toutes les checkboxes lignes
  document.getElementById('tbody-catalogue').addEventListener('change', e => {
    if (e.target.classList.contains('chk-article')) {
      majBarreMasse();
    }
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

function estIncomplet(a) {
  if (!a.code_article)  return true;
  if (!a.designation)   return true;
  if (!a.prix_achat_ht) return true;
  if (!a.format_prix)   return true;
  if (a.format_prix === 'colis') {
    if (a.qte_par_colis == null)     return true;
    if (a.poids_unitaire_kg == null) return true;
  }
  return false;
}

function champsManquants(a) {
  const m = [];
  if (!a.code_article)  m.push('Code article');
  if (!a.designation)   m.push('Désignation');
  if (!a.prix_achat_ht) m.push('Prix HT');
  if (!a.format_prix)   m.push('Format');
  if (a.format_prix === 'colis') {
    if (a.qte_par_colis == null)     m.push('Qté/colis');
    if (a.poids_unitaire_kg == null) m.push('Poids unitaire');
  }
  return m;
}

function afficherStats() {
  const actifs      = articles.filter(a => a.actif && !estTest(a));
  const fourn       = new Set(actifs.map(a => a.fournisseur_id)).size;
  const sansPrix    = actifs.filter(a => !a.prix_achat_ht || a.prix_achat_ht === 0);
  const incomplets  = actifs.filter(a => estIncomplet(a));
  document.getElementById('stat-total').textContent        = actifs.length;
  document.getElementById('stat-fournisseurs').textContent = fourn;
  document.getElementById('stat-sans-prix').textContent    = sansPrix.length;
  document.getElementById('stat-incomplets').textContent   = incomplets.length;
}

// ── Filtrer + Trier ──────────────────────────────────────────
function filtrer() {
  const fourn            = document.getElementById('filtre-fournisseur').value;
  const formatPrix       = document.getElementById('filtre-format-prix').value;
  const famille          = document.getElementById('filtre-famille').value;
  const sousFamille      = document.getElementById('filtre-sous-famille').value;
  const dlc              = document.getElementById('filtre-dlc').value;
  const search           = document.getElementById('filtre-search').value.toLowerCase();
  const afficherTest     = document.getElementById('filtre-afficher-test').checked;
  const afficherInactifs  = document.getElementById('filtre-inactifs').checked;
  const sansPrixOnly      = document.getElementById('filtre-sans-prix').checked;
  const incompletsOnly    = document.getElementById('filtre-incomplets').checked;

  listeFiltree = articles.filter(a => {
    if (!afficherTest     && estTest(a))                              return false;
    if (!afficherInactifs && !a.actif)                               return false;
    if (fourn      && String(a.fournisseur_id) !== fourn)            return false;
    if (formatPrix && a.format_prix !== formatPrix)                  return false;
    if (famille    && a.famille !== famille)                         return false;
    if (sousFamille && a.sous_famille !== sousFamille)               return false;
    if (dlc        && a.dlc_type !== dlc)                            return false;
    if (sansPrixOnly   && a.prix_achat_ht > 0)                      return false;
    if (incompletsOnly && !estIncomplet(a))                         return false;
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
  const manquantsSet = (a) => new Set(champsManquants(a));
  const surbrillance = 'background:#fff3e0;';

  tbody.innerHTML = liste.map(a => {
    const manque = manquantsSet(a);
    const hl = (champ) => manque.has(champ) ? surbrillance : '';
    const estColis = a.format_prix === 'colis';
    return `
    <tr class="${!a.actif ? 'ach-row--inactif' : ''}">
      <td style="width:36px;text-align:center;padding:0 8px;">
        <input type="checkbox" class="chk-article" data-id="${a.id}"
               style="width:20px;height:20px;accent-color:var(--color-accent);display:block;margin:auto;cursor:pointer;opacity:1;visibility:visible;appearance:checkbox;-webkit-appearance:checkbox;">
      </td>
      <td>${escHtml(a.fournisseur_nom)}</td>
      <td ondblclick="editerInline(this,${a.id},'code_article','text')" style="cursor:pointer;${hl('Code article')}"><code>${escHtml(a.code_article)}</code></td>
      <td class="ach-cell-nom" ondblclick="editerInline(this,${a.id},'designation','text')" style="cursor:pointer;${hl('Désignation')}">
        ${escHtml(a.designation)}
        ${!a.actif ? ' <span class="ach-badge ach-badge--annulee">Inactif</span>' : ''}
        ${estIncomplet(a) ? `<span style="font-size:var(--text-xs);color:#e8913a;font-weight:600;margin-left:6px;">⚠ ${[...manque].join(', ')}</span>` : ''}
      </td>
      <td class="ach-col-num" ondblclick="editerInline(this,${a.id},'prix_achat_ht','number')" style="cursor:pointer;${hl('Prix HT')}">${fmtPrix(a.prix_achat_ht)} €</td>
      <td ondblclick="editerInline(this,${a.id},'format_prix','select')" style="cursor:pointer;${hl('Format')}">
        <span class="ach-badge ach-badge--${a.format_prix === 'kg' ? 'dlc' : 'abattage'}">${a.format_prix === 'kg' ? '€/kg' : '€/colis'}</span>
      </td>
      <td class="ach-col-num" ondblclick="editerInline(this,${a.id},'qte_par_colis','number')" style="cursor:pointer;${estColis && hl('Qté/colis')}">${a.qte_par_colis != null ? a.qte_par_colis : '<span style="color:#9ca3af">—</span>'}</td>
      <td class="ach-col-num" ondblclick="editerInline(this,${a.id},'poids_unitaire_kg','number')" style="cursor:pointer;${estColis && hl('Poids unitaire')}">${a.poids_unitaire_kg != null ? a.poids_unitaire_kg.toFixed(3) + ' kg' : '<span style="color:#9ca3af">—</span>'}</td>
      <td class="ach-col-num">${a.poids_colis_kg != null ? '<strong>' + a.poids_colis_kg.toFixed(3) + ' kg</strong>' : '<span style="color:#9ca3af">—</span>'}</td>
      <td ondblclick="editerInline(this,${a.id},'tva_percent','number')" style="cursor:pointer;">${a.tva_percent ?? 5.5}%</td>
      <td>${fmtUnitesAutorisees(a.unites_autorisees)}</td>
      <td ondblclick="editerInline(this,${a.id},'famille','select')" style="cursor:pointer;">${a.famille ? escHtml(a.famille) : '<span style="color:#9ca3af">—</span>'}</td>
      <td ondblclick="editerInline(this,${a.id},'sous_famille','select')" style="cursor:pointer;">${a.sous_famille ? escHtml(a.sous_famille) : '<span style="color:#9ca3af">—</span>'}</td>
      <td ondblclick="editerInline(this,${a.id},'dlc_type','select')" style="cursor:pointer;">
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
    </tr>`;
  }).join('');

  // Reset checkbox "tout sélectionner"
  document.getElementById('chk-tout').checked = false;
}

// ── Sélection & Actions en masse ─────────────────────────────
function idsSelectionnes() {
  return [...document.querySelectorAll('.chk-article:checked')].map(c => parseInt(c.dataset.id));
}

function majBarreMasse() {
  const ids   = idsSelectionnes();
  const barre = document.getElementById('barre-masse');
  const nbEl  = document.getElementById('masse-nb');
  if (ids.length > 0) {
    barre.removeAttribute('hidden');
  } else {
    barre.setAttribute('hidden', '');
  }
  if (nbEl) nbEl.textContent = ids.length;
  const modalNb = document.getElementById('masse-modal-nb');
  if (modalNb) modalNb.textContent = ids.length;
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
      if (action === 'supprimer')  return fetch(`${API_CAT}/${id}?permanent=true`, { method: 'DELETE' });
    }));
    await chargerCatalogue();
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

  const CHAMPS = {
    fournisseur_id: {
      label: 'Nouveau fournisseur',
      html: () => {
        const opts = fournisseurs.map(f => `<option value="${f.id}">${escHtml(f.nom)}</option>`).join('');
        return `<select id="masse-val" class="ach-champ" style="min-height:44px;padding:.5rem .75rem;border:1px solid #d4c5af;border-radius:8px;font-size:1rem;width:100%;">
          <option value="">— Sélectionnez —</option>${opts}</select>`;
      },
    },
    prix_achat_ht: {
      label: 'Nouveau prix HT (€)',
      html: () => `<input type="number" id="masse-val" min="0" step="0.01" placeholder="0.00"
        style="min-height:44px;padding:.5rem .75rem;border:1px solid #d4c5af;border-radius:8px;font-size:1rem;width:100%;">`,
    },
    format_prix: {
      label: 'Nouveau format prix',
      html: () => `<select id="masse-val" style="min-height:44px;padding:.5rem .75rem;border:1px solid #d4c5af;border-radius:8px;font-size:1rem;width:100%;">
        <option value="kg">€ / kg (au kilo)</option>
        <option value="colis">€ / colis (à la pièce)</option></select>`,
    },
    tva_percent: {
      label: 'Nouveau taux TVA (%)',
      html: () => `<select id="masse-val" style="min-height:44px;padding:.5rem .75rem;border:1px solid #d4c5af;border-radius:8px;font-size:1rem;width:100%;">
        <option value="5.5">5.5% (alimentaire)</option>
        <option value="10">10%</option>
        <option value="20">20%</option></select>`,
    },
    unites_autorisees: {
      label: 'Unités de commande autorisées',
      html: () => `<div id="masse-unites" style="display:flex;gap:10px;flex-wrap:wrap;padding:6px 0;">
        <button type="button" class="ach-unite-toggle ach-unite-toggle--on" data-val="kg">kg</button>
        <button type="button" class="ach-unite-toggle ach-unite-toggle--on" data-val="piece">pièce</button>
        <button type="button" class="ach-unite-toggle ach-unite-toggle--on" data-val="colis">colis</button>
      </div>`,
    },
    famille: {
      label: 'Nouvelle famille',
      html: () => {
        const champStyle = 'min-height:44px;padding:.5rem .75rem;border:1px solid #d4c5af;border-radius:8px;font-size:1rem;width:100%;';
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
    dlc_type: {
      label: 'Nouveau type DLC',
      html: () => `<select id="masse-val" style="min-height:44px;padding:.5rem .75rem;border:1px solid #d4c5af;border-radius:8px;font-size:1rem;width:100%;">
        <option value="dlc">DLC (date limite)</option>
        <option value="date_abattage">Date d'abattage</option>
        <option value="no_dlc">Sans DLC</option></select>`,
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

  // Boutons toggle unités de commande
  if (champ === 'unites_autorisees') {
    document.getElementById('masse-unites').addEventListener('click', e => {
      const btn = e.target.closest('.ach-unite-toggle');
      if (!btn) return;
      btn.classList.toggle('ach-unite-toggle--on');
    });
  }

  // Famille → sous-famille dépendante dans la modale d'édition en masse
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
  if (!ids.length || !champ) return;

  // Cas spécial : unités autorisées = boutons toggle → chaîne CSV
  if (champ === 'unites_autorisees') {
    const zone = document.getElementById('masse-unites');
    const sel = [...zone.querySelectorAll('.ach-unite-toggle--on')].map(b => b.dataset.val);
    if (!sel.length) {
      const z = document.getElementById('masse-erreur');
      z.textContent = 'Sélectionnez au moins une unité'; z.hidden = false;
      return;
    }
    await appliquerMassePayload(ids, { unites_autorisees: sel.join(',') });
    return;
  }

  const valEl = document.getElementById('masse-val');
  if (!valEl) return;

  let valeur = valEl.value;
  if (champ === 'prix_achat_ht') valeur = parseFloat(valeur);
  if (champ === 'tva_percent')   valeur = parseFloat(valeur);
  if (champ === 'fournisseur_id') valeur = parseInt(valeur);
  if (!valeur && valeur !== 0) {
    const z = document.getElementById('masse-erreur');
    z.textContent = 'Valeur obligatoire'; z.hidden = false;
    return;
  }

  // La famille embarque une sous-famille facultative (envoyée ensemble).
  let payload = { [champ]: valeur };
  if (champ === 'famille') {
    payload.sous_famille = document.getElementById('masse-val-sf').value || '';
  }
  await appliquerMassePayload(ids, payload);
}

// Applique un payload à tous les articles sélectionnés (PUT en parallèle).
async function appliquerMassePayload(ids, payload) {
  const btn = document.getElementById('masse-appliquer');
  btn.disabled = true; btn.textContent = 'Application…';
  try {
    const resultats = await Promise.all(ids.map(id =>
      fetch(`${API_CAT}/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).then(r => ({ id, ok: r.ok, status: r.status }))
    ));
    const echecs = resultats.filter(r => !r.ok);
    if (echecs.length) {
      const z = document.getElementById('masse-erreur');
      z.textContent = `${echecs.length} article(s) non mis à jour (IDs : ${echecs.map(r => r.id).join(', ')})`;
      z.hidden = false;
    }
    fermerModalMasse();
    await chargerCatalogue();
  } catch(e) {
    const z = document.getElementById('masse-erreur');
    z.textContent = 'Erreur : ' + e.message; z.hidden = false;
  } finally {
    btn.disabled = false; btn.textContent = 'Appliquer';
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
  document.getElementById('btn-supprimer-article').hidden = true;
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
  // Rétrocompat : ancienne valeur 'piece' → 'colis'
  document.getElementById('a-format-prix').value = (a.format_prix === 'piece' ? 'colis' : (a.format_prix || 'kg'));
  document.getElementById('a-qte-colis').value = a.qte_par_colis ?? '';
  document.getElementById('a-poids-unitaire').value = a.poids_unitaire_kg ?? '';
  document.getElementById('a-tva').value = a.tva_percent ?? 5.5;
  setUnitesForm(a.unites_autorisees);
  document.getElementById('a-famille').value = a.famille || '';
  majSousFamilleForm(a.sous_famille || '');
  document.getElementById('a-dlc-type').value = a.dlc_type || 'dlc';
  recalcPoidsColis();
  document.getElementById('btn-supprimer-article').hidden = false;
  document.getElementById('form-erreur').hidden = true;
  document.getElementById('modal-article').hidden = false;
}

// Sous-famille du formulaire : peuplée selon la famille choisie.
// `valeurAGarder` permet de re-sélectionner la sous-famille existante en mode édition.
function majSousFamilleForm(valeurAGarder) {
  majSousFamille(
    document.getElementById('a-famille').value,
    document.getElementById('a-sous-famille'),
    valeurAGarder || ''
  );
}

// ── Unités de commande autorisées (checkboxes kg/pièce/colis) ──
const UNITES_IDS = { kg: 'a-unite-kg', piece: 'a-unite-piece', colis: 'a-unite-colis' };

// Coche les cases selon la chaîne CSV (ex. "kg,colis"). Vide/null → tout coché.
function setUnitesForm(csv) {
  const liste = (csv && csv.trim())
    ? csv.split(',').map(s => s.trim()).filter(Boolean)
    : ['kg', 'piece', 'colis'];
  for (const [unite, id] of Object.entries(UNITES_IDS)) {
    document.getElementById(id).checked = liste.includes(unite);
  }
}

// Lit les cases cochées → chaîne CSV. Si rien coché, repli sur tout autorisé.
function getUnitesForm() {
  const sel = Object.entries(UNITES_IDS)
    .filter(([, id]) => document.getElementById(id).checked)
    .map(([unite]) => unite);
  return (sel.length ? sel : ['kg', 'piece', 'colis']).join(',');
}

// Champ généré : poids total colis = qté par colis × poids unitaire
function recalcPoidsColis() {
  const qte   = parseFloat(document.getElementById('a-qte-colis').value);
  const poids = parseFloat(document.getElementById('a-poids-unitaire').value);
  const out   = document.getElementById('a-poids-colis');
  if (qte > 0 && poids > 0) {
    out.value = (Math.round(qte * poids * 1000) / 1000) + ' kg';
  } else {
    out.value = '';
  }
}

// ── Édition inline (double-clic sur cellule) ─────────────────
const SELECT_OPTIONS = {
  format_prix: [['kg','€/kg'], ['colis','€/colis']],
  dlc_type:    [['dlc','DLC'], ['date_abattage','Abattage'], ['no_dlc','Sans DLC']],
  famille:     () => [['', '— Aucune —'], ...Object.keys(FAMILLES).map(f => [f, f])],
};

// Options de sous-famille en édition inline, dérivées de la famille de l'article.
function sousFamilleOptions(article) {
  const sf = FAMILLES[article?.famille] || [];
  return [['', '— Aucune —'], ...sf.map(s => [s, s])];
}

function editerInline(td, articleId, champ, type) {
  if (td.querySelector('input,select')) return; // déjà en édition
  const article = articles.find(a => a.id === articleId);
  const valActuelle = article?.[champ] ?? '';

  let ctrl;
  if (type === 'select') {
    ctrl = document.createElement('select');
    ctrl.style.cssText = 'width:100%;font:inherit;border:2px solid var(--color-accent);border-radius:4px;padding:2px 4px;';
    let opts = champ === 'sous_famille' ? sousFamilleOptions(article) : SELECT_OPTIONS[champ];
    if (typeof opts === 'function') opts = opts();
    opts.forEach(([val, lbl]) => {
      const opt = document.createElement('option');
      opt.value = val; opt.textContent = lbl;
      if (val === String(valActuelle)) opt.selected = true;
      ctrl.appendChild(opt);
    });
  } else {
    ctrl = document.createElement('input');
    ctrl.type = type === 'number' ? 'number' : 'text';
    ctrl.value = valActuelle ?? '';
    ctrl.step = 'any';
    ctrl.style.cssText = 'width:100%;font:inherit;border:2px solid var(--color-accent);border-radius:4px;padding:2px 4px;box-sizing:border-box;';
  }

  const contenuOriginal = td.innerHTML;
  td.innerHTML = '';
  td.appendChild(ctrl);
  ctrl.focus();
  if (ctrl.select) ctrl.select();

  async function valider() {
    let nouvelleVal = type === 'number' ? (parseFloat(ctrl.value) || null) : ctrl.value.trim() || null;
    td.innerHTML = contenuOriginal; // restaure pendant la requête
    if (nouvelleVal === valActuelle) return;
    const payload = { [champ]: nouvelleVal };
    // Changer la famille invalide l'ancienne sous-famille → on la réinitialise.
    if (champ === 'famille') {
      const sfOk = (FAMILLES[nouvelleVal] || []).includes(article?.sous_famille);
      if (!sfOk) payload.sous_famille = '';
    }
    try {
      const r = await fetch(`${API_CAT}/${articleId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'Erreur');
      await chargerCatalogue();
    } catch(err) {
      alert('Erreur : ' + err.message);
    }
  }

  ctrl.addEventListener('blur', valider);
  ctrl.addEventListener('keydown', e => {
    if (e.key === 'Enter')  { ctrl.blur(); }
    if (e.key === 'Escape') { td.innerHTML = contenuOriginal; ctrl.removeEventListener('blur', valider); }
  });
  // Pour select : valider immédiatement au changement
  if (type === 'select') ctrl.addEventListener('change', () => ctrl.blur());
}

async function supprimerArticle() {
  const id          = document.getElementById('a-id').value;
  const designation = document.getElementById('a-designation').value;
  if (!confirm(`Supprimer définitivement "${designation}" ?\n\nL'article sera effacé de la base de données. Cette action est irréversible.`)) return;

  const btn = document.getElementById('btn-supprimer-article');
  btn.disabled = true; btn.textContent = 'Suppression…';

  try {
    const r = await fetch(`${API_CAT}/${id}?permanent=true`, { method: 'DELETE' });
    if (!r.ok) {
      const err = await r.json();
      throw new Error(err.detail || 'Erreur serveur');
    }
    fermerModal();
    await chargerCatalogue();
  } catch(err) {
    const z = document.getElementById('form-erreur');
    z.textContent = err.message; z.hidden = false;
  } finally {
    btn.disabled = false; btn.textContent = 'Supprimer';
  }
}

function fermerModal() {
  document.getElementById('modal-article').hidden = true;
}

function viderForm() {
  ['a-id','a-code','a-designation','a-prix',
   'a-qte-colis','a-poids-unitaire','a-poids-colis'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('a-format-prix').value = 'kg';
  document.getElementById('a-tva').value = '5.5';
  setUnitesForm(null);   // tout coché par défaut
  document.getElementById('a-famille').value = '';
  majSousFamilleForm();
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
    qte_par_colis:     parseFloat(document.getElementById('a-qte-colis').value) || null,
    poids_unitaire_kg: parseFloat(document.getElementById('a-poids-unitaire').value) || null,
    tva_percent:     parseFloat(document.getElementById('a-tva').value),
    unites_autorisees: getUnitesForm(),
    famille:         document.getElementById('a-famille').value || null,
    sous_famille:    document.getElementById('a-sous-famille').value || null,
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
let importEnCours = false;

async function lancerImport() {
  if (importEnCours) return;                    // anti double-clic / spam
  const inputFichier = document.getElementById('import-fichier');
  const fichier = inputFichier.files[0];
  if (!fichier) { alert('Sélectionnez un fichier Excel'); return; }

  const btn = document.getElementById('import-lancer');
  importEnCours = true;
  btn.disabled = true; btn.textContent = 'Import en cours…';

  const formData = new FormData();
  formData.append('fichier', fichier);

  try {
    const r = await fetch(`${API_CAT}/import/upload`, { method: 'POST', body: formData });
    const result = await r.json();
    const zone = document.getElementById('import-resultat');
    zone.hidden = false;

    if (r.ok) {
      const erreurs = result.erreurs?.length ? `\nErreurs : ${result.erreurs.length}` : '';
      zone.className = 'ach-import-resultat ach-import-resultat--ok';
      zone.textContent = `✅ Import terminé\nCréés : ${result.crees}\nMis à jour : ${result.mis_a_jour}${result.erreurs?.length ? '\nErreurs :\n' + result.erreurs.join('\n') : ''}`;

      await chargerCatalogue();

      // Pop-up de confirmation explicite
      alert(`✅ Import validé\n\nArticles créés : ${result.crees}\nArticles mis à jour : ${result.mis_a_jour}${erreurs}`);

      // Fermer la modale et réinitialiser (évite le ré-import du même fichier par spam)
      document.getElementById('modal-import').hidden = true;
      inputFichier.value = '';
      zone.hidden = true;
      btn.textContent = 'Importer';
      return;   // le bouton reste désactivé tant qu'aucun nouveau fichier n'est choisi
    }

    // Erreur serveur
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
function fmtPrix(v) { return (v ?? 0).toFixed(2); }

// Affiche les unités autorisées sous forme de petits badges (kg · pièce · colis).
const UNITE_LABELS = { kg: 'kg', piece: 'pièce', colis: 'colis' };
function fmtUnitesAutorisees(csv) {
  const liste = (csv && csv.trim())
    ? csv.split(',').map(s => s.trim()).filter(Boolean)
    : ['kg', 'piece', 'colis'];
  if (!liste.length) return '<span style="color:#9ca3af">—</span>';
  return liste.map(u =>
    `<span class="ach-badge ach-badge--dlc" style="margin:1px;">${escHtml(UNITE_LABELS[u] || u)}</span>`
  ).join(' ');
}
function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

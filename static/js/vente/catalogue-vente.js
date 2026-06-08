/* catalogue-vente.js — Catalogue de vente (produits finis fabriqués) */

const API_VENTE = '/api/vente/catalogue';

let produits   = [];
let modeEdition = false;

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  peuplerSelectFamille(document.getElementById('filtre-famille'), null, '');
  // Réinsérer "Toutes" en tête du filtre famille (peuplerSelectFamille met "— Famille —")
  document.getElementById('filtre-famille').firstChild.textContent = 'Toutes';
  document.getElementById('filtre-famille').firstChild.value = '';
  bindEvents();
  charger();
});

function bindEvents() {
  document.getElementById('btn-nouveau').addEventListener('click', ouvrirNouveau);
  document.getElementById('modal-fermer').addEventListener('click', fermerModal);
  document.getElementById('btn-annuler').addEventListener('click', fermerModal);
  document.getElementById('btn-supprimer').addEventListener('click', supprimer);
  document.getElementById('form-vente').addEventListener('submit', sauver);
  document.getElementById('filtre-search').addEventListener('input', render);
  document.getElementById('filtre-inactifs').addEventListener('change', charger);
  document.getElementById('filtre-famille').addEventListener('change', () => {
    const fam = document.getElementById('filtre-famille').value;
    const sel = document.getElementById('filtre-sous-famille');
    majSousFamille(fam, sel, '');
    const opt0 = document.createElement('option');
    opt0.value = ''; opt0.textContent = 'Toutes';
    sel.insertBefore(opt0, sel.firstChild);
    sel.value = '';
    render();
  });
  document.getElementById('filtre-sous-famille').addEventListener('change', render);
  document.getElementById('v-famille').addEventListener('change', () => {
    majSousFamille(
      document.getElementById('v-famille').value,
      document.getElementById('v-sous-famille'),
      ''
    );
  });
}

// ── Chargement ───────────────────────────────────────────────
async function charger() {
  const inactifs = document.getElementById('filtre-inactifs').checked;
  try {
    const r = await fetch(`${API_VENTE}?actif_only=${inactifs ? 'false' : 'true'}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    produits = await r.json();
    render();
  } catch (e) {
    afficherErreur('Impossible de charger le catalogue de vente : ' + e.message);
  }
}

function render() {
  const search      = document.getElementById('filtre-search').value.toLowerCase();
  const famille     = document.getElementById('filtre-famille').value;
  const sousFamille = document.getElementById('filtre-sous-famille').value;

  const liste = produits.filter(p => {
    if (search      && !(p.nom || '').toLowerCase().includes(search))   return false;
    if (famille     && p.famille     !== famille)                        return false;
    if (sousFamille && p.sous_famille !== sousFamille)                   return false;
    return true;
  });

  const actifs = produits.filter(p => p.actif);
  document.getElementById('stat-total').textContent = actifs.length;
  document.getElementById('resultat-count').textContent =
    `${liste.length} produit${liste.length > 1 ? 's' : ''}`;

  const tbody = document.getElementById('tbody-vente');
  if (!liste.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="ach-vide">Aucun produit fini</td></tr>`;
    return;
  }
  tbody.innerHTML = liste.map(p => `
    <tr class="${!p.actif ? 'ach-row--inactif' : ''}">
      <td class="ach-cell-nom">
        ${escHtml(p.nom)}
        ${!p.actif ? ' <span class="ach-badge ach-badge--annulee">Inactif</span>' : ''}
      </td>
      <td class="ach-col-num">${p.prix_vente_ttc != null ? p.prix_vente_ttc.toFixed(2) + ' €' : '<span style="color:#9ca3af">—</span>'}</td>
      <td>${p.tva_percent ?? 5.5}%</td>
      <td class="ach-col-num">${p.dlc_jours ?? '—'}</td>
      <td>${escHtml(p.temperature_conservation || '—')}</td>
      <td>${escHtml(p.famille || '—')}</td>
      <td>${escHtml(p.sous_famille || '—')}</td>
      <td class="ach-col-actions">
        <button class="ach-btn ach-btn--small" onclick="ouvrirEdition(${p.id})">Modifier</button>
        ${p.actif
          ? `<button class="ach-btn ach-btn--small ach-btn--danger" onclick="toggleActif(${p.id}, false)" title="Désactiver">✕</button>`
          : `<button class="ach-btn ach-btn--small ach-btn--ok" onclick="toggleActif(${p.id}, true)" title="Réactiver">↺</button>`
        }
      </td>
    </tr>`).join('');
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

// ── Utilitaires ──────────────────────────────────────────────
function afficherErreur(msg) {
  const z = document.getElementById('zone-erreur');
  z.textContent = msg; z.hidden = false;
}
function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

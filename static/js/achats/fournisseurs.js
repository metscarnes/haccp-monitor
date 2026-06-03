/* fournisseurs.js — Gestion des fournisseurs */

const API = '/api/achats/fournisseurs';
let fournisseurs = [];
let modeEdition = false;

const DELAI_LABELS = {
  '0': 'Comptant',
  '30': 'Net 30j',
  '45': 'Net 45j',
  '60': 'Net 60j',
  '90': 'Net 90j',
};

const JOURS_ORDRE = ['lundi','mardi','mercredi','jeudi','vendredi','samedi'];
const JOURS_ABREV = { lundi:'L', mardi:'Ma', mercredi:'Me', jeudi:'J', vendredi:'V', samedi:'S' };

// ── Init ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  charger();
  document.getElementById('btn-nouveau').addEventListener('click', ouvrirNouveauModal);
  document.getElementById('modal-fermer').addEventListener('click', fermerModal);
  document.getElementById('btn-annuler').addEventListener('click', fermerModal);
  document.getElementById('form-fournisseur').addEventListener('submit', sauver);
});

// ── Chargement ───────────────────────────────────────────────
async function charger() {
  try {
    const r = await fetch(`${API}?actif_only=false`);
    fournisseurs = await r.json();
    afficherStats();
    afficherTable();
  } catch(e) {
    afficherErreur('Impossible de charger les fournisseurs : ' + e.message);
  }
}

function afficherStats() {
  const actifs = fournisseurs.filter(f => f.actif);
  const avecEmail = actifs.filter(f => f.email_commercial);
  document.getElementById('stat-total').textContent = actifs.length;
  document.getElementById('stat-avec-email').textContent = avecEmail.length;
  document.getElementById('stat-sans-email').textContent = actifs.length - avecEmail.length;
}

function fmtJoursLivraison(json) {
  if (!json) return '<span style="color:#9ca3af">—</span>';
  try {
    const jours = typeof json === 'string' ? JSON.parse(json) : json;
    if (!jours.length) return '<span style="color:#9ca3af">—</span>';
    return jours
      .sort((a,b) => JOURS_ORDRE.indexOf(a) - JOURS_ORDRE.indexOf(b))
      .map(j => `<span class="ach-badge ach-badge--confirmee">${JOURS_ABREV[j] ?? j}</span>`)
      .join(' ');
  } catch { return escHtml(json); }
}

function afficherTable() {
  const tbody = document.getElementById('tbody-fournisseurs');
  if (!fournisseurs.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="ach-vide">Aucun fournisseur — cliquez sur "+ Nouveau"</td></tr>';
    return;
  }
  tbody.innerHTML = fournisseurs.map(f => `
    <tr>
      <td class="ach-cell-nom">
        ${escHtml(f.nom)}${!f.actif ? ' <span class="ach-badge ach-badge--annulee">Inactif</span>' : ''}
        ${f.commentaire ? `<div style="font-size:var(--text-xs);color:#6b7280;font-weight:400;margin-top:2px;">${escHtml(f.commentaire.slice(0,60))}${f.commentaire.length>60?'…':''}</div>` : ''}
      </td>
      <td>${f.email_commercial
        ? `<a href="mailto:${escHtml(f.email_commercial)}">${escHtml(f.email_commercial)}</a>`
        : '<span style="color:#9ca3af">—</span>'}</td>
      <td>${escHtml(f.telephone || '—')}</td>
      <td>${f.delai_paiement_jours !== null && f.delai_paiement_jours !== undefined
        ? `<span class="ach-badge ach-badge--dlc">${DELAI_LABELS[String(f.delai_paiement_jours)] ?? f.delai_paiement_jours+'j'}</span>`
        : '<span style="color:#9ca3af">—</span>'}</td>
      <td>${fmtJoursLivraison(f.jours_livraison)}</td>
      <td class="ach-col-num">${f.nb_articles ?? 0}</td>
      <td class="ach-col-actions">
        <button class="ach-btn ach-btn--small" onclick="ouvrirEditionModal(${f.id})">Modifier</button>
        <button class="ach-btn ach-btn--small" onclick="window.location='/catalogue-achats.html?fournisseur=${f.id}'">Catalogue</button>
      </td>
    </tr>
  `).join('');
}

// ── Modal ────────────────────────────────────────────────────
function ouvrirNouveauModal() {
  modeEdition = false;
  document.getElementById('modal-titre').textContent = 'Nouveau fournisseur';
  viderForm();
  document.getElementById('modal-fournisseur').hidden = false;
  document.getElementById('f-nom').focus();
}

function ouvrirEditionModal(id) {
  const f = fournisseurs.find(x => x.id === id);
  if (!f) return;
  modeEdition = true;
  document.getElementById('modal-titre').textContent = 'Modifier — ' + f.nom;
  document.getElementById('f-id').value = f.id;
  document.getElementById('f-nom').value = f.nom;
  document.getElementById('f-email').value = f.email_commercial || '';
  document.getElementById('f-telephone').value = f.telephone || '';
  document.getElementById('f-adresse').value = f.adresse || '';
  document.getElementById('f-delai-paiement').value =
    f.delai_paiement_jours !== null && f.delai_paiement_jours !== undefined
      ? String(f.delai_paiement_jours) : '';
  document.getElementById('f-commentaire').value = f.commentaire || '';

  // Cocher les jours de livraison
  const joursCoches = parseJours(f.jours_livraison);
  document.querySelectorAll('#f-jours-livraison-wrap input[type="checkbox"]').forEach(cb => {
    cb.checked = joursCoches.includes(cb.value);
  });

  document.getElementById('form-erreur').hidden = true;
  document.getElementById('modal-fournisseur').hidden = false;
}

function fermerModal() {
  document.getElementById('modal-fournisseur').hidden = true;
}

function viderForm() {
  ['f-id','f-nom','f-email','f-telephone','f-adresse','f-commentaire'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('f-delai-paiement').value = '';
  document.querySelectorAll('#f-jours-livraison-wrap input[type="checkbox"]').forEach(cb => {
    cb.checked = false;
  });
  document.getElementById('form-erreur').hidden = true;
}

function parseJours(json) {
  if (!json) return [];
  try { return typeof json === 'string' ? JSON.parse(json) : json; }
  catch { return []; }
}

function lireJoursCochés() {
  return [...document.querySelectorAll('#f-jours-livraison-wrap input[type="checkbox"]:checked')]
    .map(cb => cb.value);
}

// ── Sauvegarde ───────────────────────────────────────────────
async function sauver(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-sauver');
  btn.disabled = true;
  btn.textContent = 'Enregistrement…';

  const delaiRaw = document.getElementById('f-delai-paiement').value;
  const jours = lireJoursCochés();

  const body = {
    nom:                  document.getElementById('f-nom').value.trim(),
    email_commercial:     document.getElementById('f-email').value.trim() || null,
    telephone:            document.getElementById('f-telephone').value.trim() || null,
    adresse:              document.getElementById('f-adresse').value.trim() || null,
    delai_paiement_jours: delaiRaw !== '' ? parseInt(delaiRaw) : null,
    jours_livraison:      jours.length ? JSON.stringify(jours) : null,
    commentaire:          document.getElementById('f-commentaire').value.trim() || null,
  };

  try {
    const id = document.getElementById('f-id').value;
    const url = modeEdition ? `${API}/${id}` : API;
    const method = modeEdition ? 'PUT' : 'POST';
    const r = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const err = await r.json();
      throw new Error(err.detail || 'Erreur serveur');
    }
    fermerModal();
    await charger();
  } catch(err) {
    const zone = document.getElementById('form-erreur');
    zone.textContent = err.message;
    zone.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Enregistrer';
  }
}

// ── Utilitaires ──────────────────────────────────────────────
function afficherErreur(msg) {
  const z = document.getElementById('zone-erreur');
  z.textContent = msg;
  z.hidden = false;
}

function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* fournisseurs.js — Gestion des fournisseurs */

const API = '/api/achats/fournisseurs';
let fournisseurs = [];
let modeEdition = false;

const RYTHME_LABELS = {
  'A-B': 'A-B (J+1)',
  'A-C': 'A-C (J+2)',
  'A-D': 'A-D (J+3)',
};

const JOURS_ORDRE = ['lundi','mardi','mercredi','jeudi','vendredi','samedi'];
const JOURS_ABREV = { lundi:'L', mardi:'Ma', mercredi:'Me', jeudi:'J', vendredi:'V', samedi:'S' };

function fmtDelai(v) {
  if (v === null || v === undefined || v === '') return '—';
  const n = parseInt(v);
  return n === 0 ? 'Comptant' : `Net ${n}j`;
}

function majSliderDelai(val) {
  const n = parseInt(val);
  document.getElementById('f-delai-paiement-val').textContent = n === 0 ? 'Comptant' : `${n} jours`;
}

// ── Init ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  charger();
  document.getElementById('btn-nouveau').addEventListener('click', ouvrirNouveauModal);
  document.getElementById('modal-fermer').addEventListener('click', fermerModal);
  document.getElementById('btn-annuler').addEventListener('click', fermerModal);
  document.getElementById('btn-supprimer').addEventListener('click', supprimerFournisseur);
  document.getElementById('form-fournisseur').addEventListener('submit', sauver);

  // Slider délai paiement — mise à jour label en temps réel
  const slider = document.getElementById('f-delai-paiement');
  slider.addEventListener('input', () => majSliderDelai(slider.value));
  majSliderDelai(slider.value);
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
      <td>
        ${f.nom_commercial ? `<div style="font-weight:600;">${escHtml(f.nom_commercial)}</div>` : ''}
        ${f.email_commercial
          ? `<a href="mailto:${escHtml(f.email_commercial)}" style="font-size:var(--text-xs);">${escHtml(f.email_commercial)}</a>`
          : '<span style="color:#9ca3af">—</span>'}
      </td>
      <td>${escHtml(f.telephone || '—')}</td>
      <td>${f.delai_paiement_jours !== null && f.delai_paiement_jours !== undefined
        ? `<span class="ach-badge ach-badge--dlc">${fmtDelai(f.delai_paiement_jours)}</span>`
        : '<span style="color:#9ca3af">—</span>'}</td>
      <td>
        ${f.rythme_livraison ? `<span class="ach-badge ach-badge--confirmee">${escHtml(f.rythme_livraison)}</span> ` : ''}
        ${f.heure_limite_commande ? `<span style="font-size:var(--text-xs);color:#6b7280;">cmd avant ${escHtml(f.heure_limite_commande)}</span>` : ''}
        ${f.heure_livraison ? `<span style="font-size:var(--text-xs);color:#6b7280;"> · liv. ${escHtml(f.heure_livraison)}</span>` : ''}
        <div style="margin-top:2px;">${fmtJoursLivraison(f.jours_livraison)}</div>
      </td>
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
  document.getElementById('btn-supprimer').hidden = true;
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
  document.getElementById('f-nom-commercial').value = f.nom_commercial || '';
  document.getElementById('f-email').value = f.email_commercial || '';
  document.getElementById('f-telephone').value = f.telephone || '';
  document.getElementById('f-adresse').value = f.adresse || '';
  const delai = f.delai_paiement_jours !== null && f.delai_paiement_jours !== undefined
    ? f.delai_paiement_jours : 0;
  document.getElementById('f-delai-paiement').value = delai;
  majSliderDelai(delai);
  document.getElementById('f-rythme-livraison').value = f.rythme_livraison || '';
  document.getElementById('f-heure-limite-commande').value = f.heure_limite_commande || '';
  document.getElementById('f-heure-livraison').value = f.heure_livraison || '';
  document.getElementById('f-commentaire').value = f.commentaire || '';

  // Cocher les jours de livraison
  const joursCoches = parseJours(f.jours_livraison);
  document.querySelectorAll('#f-jours-livraison-wrap input[type="checkbox"]').forEach(cb => {
    cb.checked = joursCoches.includes(cb.value);
  });

  document.getElementById('btn-supprimer').hidden = false;
  document.getElementById('form-erreur').hidden = true;
  document.getElementById('modal-fournisseur').hidden = false;
}

function fermerModal() {
  document.getElementById('modal-fournisseur').hidden = true;
}

function viderForm() {
  ['f-id','f-nom','f-nom-commercial','f-email','f-telephone','f-adresse',
   'f-heure-limite-commande','f-heure-livraison','f-commentaire'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('f-delai-paiement').value = 0;
  majSliderDelai(0);
  document.getElementById('f-rythme-livraison').value = '';
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

  const jours = lireJoursCochés();

  const body = {
    nom:                    document.getElementById('f-nom').value.trim(),
    nom_commercial:         document.getElementById('f-nom-commercial').value.trim() || null,
    email_commercial:       document.getElementById('f-email').value.trim() || null,
    telephone:              document.getElementById('f-telephone').value.trim() || null,
    adresse:                document.getElementById('f-adresse').value.trim() || null,
    delai_paiement_jours:   parseInt(document.getElementById('f-delai-paiement').value),
    rythme_livraison:       document.getElementById('f-rythme-livraison').value || null,
    heure_limite_commande:  document.getElementById('f-heure-limite-commande').value || null,
    heure_livraison:        document.getElementById('f-heure-livraison').value || null,
    jours_livraison:        jours.length ? JSON.stringify(jours) : null,
    commentaire:            document.getElementById('f-commentaire').value.trim() || null,
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

// ── Suppression ─────────────────────────────────────────────
async function supprimerFournisseur() {
  const id  = document.getElementById('f-id').value;
  const nom = document.getElementById('f-nom').value;
  if (!confirm(`Supprimer définitivement "${nom}" ?\n\nCette action est irréversible.`)) return;

  const btn = document.getElementById('btn-supprimer');
  btn.disabled = true; btn.textContent = 'Suppression…';

  try {
    const r = await fetch(`${API}/${id}`, { method: 'DELETE' });
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
    btn.disabled = false; btn.textContent = 'Supprimer';
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

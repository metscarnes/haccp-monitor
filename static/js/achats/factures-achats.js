/* factures-achats.js — Sous-module Facture.
   Rapproche une commande (prix négocié) et une réception (poids HACCP pesé) avec
   ce que le fournisseur facture, et met en évidence les écarts. La réception n'est
   jamais modifiée : la facture vit à côté. */

const API_FAC   = '/api/achats/factures';
const API_FOURN = '/api/achats/fournisseurs';
const API_RECEPTIONS = '/api/receptions';

let factures     = [];
let fournisseurs = [];
let receptions   = [];     // pour la modale "nouvelle facture"
let facCourante  = null;   // facture en cours d'édition (détail)

const STATUT_LABELS = { brouillon: 'Brouillon', validee: 'Validée', litige: 'En litige' };

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await Promise.all([chargerFournisseurs(), chargerFactures()]);
  bindEvents();
});

function bindEvents() {
  document.getElementById('filtre-fournisseur').addEventListener('change', chargerFactures);
  document.getElementById('filtre-statut').addEventListener('change', chargerFactures);
  document.getElementById('btn-nouvelle-facture').addEventListener('click', ouvrirChoixReception);

  // Modale choix réception
  document.getElementById('modal-choix-fermer').addEventListener('click', fermerChoixReception);
  document.getElementById('btn-choix-annuler').addEventListener('click', fermerChoixReception);
  document.getElementById('choix-search').addEventListener('input', afficherChoixReceptions);

  // Modale détail facture
  document.getElementById('modal-fac-fermer').addEventListener('click', fermerModalFacture);
  document.getElementById('btn-fermer-fac').addEventListener('click', fermerModalFacture);
  document.getElementById('btn-sauver-fac').addEventListener('click', () => sauverFacture(false));
  document.getElementById('btn-valider-fac').addEventListener('click', () => sauverFacture(true));
  document.getElementById('btn-supprimer-fac').addEventListener('click', supprimerFacture);
  document.getElementById('btn-export-pdf').addEventListener('click', exporterPdf);
  document.getElementById('btn-export-xlsx').addEventListener('click', exporterXlsx);

  // Modale litige
  document.getElementById('modal-litige-fermer').addEventListener('click', fermerModalLitige);
  document.getElementById('btn-litige-annuler').addEventListener('click', fermerModalLitige);
  document.getElementById('btn-litige-confirmer').addEventListener('click', confirmerLitige);
}

// ── Chargement ───────────────────────────────────────────────
async function chargerFournisseurs() {
  const r = await fetch(API_FOURN);
  fournisseurs = await r.json();
  const sel = document.getElementById('filtre-fournisseur');
  for (const f of fournisseurs) {
    const opt = document.createElement('option');
    opt.value = f.id; opt.textContent = f.nom;
    sel.appendChild(opt);
  }
}

async function chargerFactures() {
  const fournisseur = document.getElementById('filtre-fournisseur').value;
  const statut = document.getElementById('filtre-statut').value;
  const params = new URLSearchParams({ limit: '100' });
  if (fournisseur) params.set('fournisseur_id', fournisseur);
  if (statut) params.set('statut', statut);

  const r = await fetch(`${API_FAC}?${params}`);
  factures = await r.json();
  rendreFactures();
  rendreStats();
}

function rendreStats() {
  const par = (s) => factures.filter(f => f.statut === s).length;
  document.getElementById('stat-brouillon').textContent = par('brouillon');
  document.getElementById('stat-validee').textContent   = par('validee');
  document.getElementById('stat-litige').textContent    = par('litige');
}

function rendreFactures() {
  const tbody = document.getElementById('tbody-factures');
  if (!factures.length) {
    tbody.innerHTML = '<tr><td colspan="9" class="ach-vide">Aucune facture. Cliquez sur « + Nouvelle facture ».</td></tr>';
    return;
  }
  tbody.innerHTML = factures.map(f => {
    const ecart = f.ecart_total_ht ?? 0;
    const cls = classeEcart(ecart);
    return `
      <tr data-id="${f.id}" style="cursor:pointer;">
        <td>${escHtml(f.numero_facture) || '<em style="color:#9ca3af;">— à saisir —</em>'}</td>
        <td>${escHtml(f.date_facture || '')}</td>
        <td>${escHtml(f.fournisseur_nom || '')}</td>
        <td>${escHtml(f.numero_commande) || '<span style="color:#9ca3af;">—</span>'}</td>
        <td class="ach-col-num">${f.nb_lignes ?? 0}</td>
        <td class="ach-col-num">${fmtPrix(f.montant_total_ht_facture)} €</td>
        <td class="ach-col-num fac-ecart ${cls}">${signe(ecart)}${fmtPrix(Math.abs(ecart))} €</td>
        <td><span class="ach-badge ach-badge--${f.statut}">${STATUT_LABELS[f.statut] || f.statut}${f.nb_litiges ? ` · ${f.nb_litiges}⚠` : ''}</span></td>
        <td class="ach-col-actions"><button class="ach-btn" data-open="${f.id}">Ouvrir</button></td>
      </tr>`;
  }).join('');

  tbody.querySelectorAll('tr[data-id]').forEach(tr => {
    tr.addEventListener('click', () => ouvrirFacture(tr.dataset.id));
  });
}

// ── Nouvelle facture : choisir la réception ──────────────────
async function ouvrirChoixReception() {
  document.getElementById('choix-search').value = '';
  // Endpoint dédié : nom du fournisseur résolu (entête OU lignes) + flag déjà facturée.
  const r = await fetch(`${API_FAC}/receptions-disponibles?limit=100`);
  receptions = await r.json();
  receptions.forEach(rec => { rec._deja = rec.deja_facturee; });
  afficherChoixReceptions();
  document.getElementById('modal-choix-reception').hidden = false;
}

function afficherChoixReceptions() {
  const q = (document.getElementById('choix-search').value || '').trim().toLowerCase();
  const liste = receptions.filter(rec => {
    if (!q) return true;
    return `${rec.fournisseur_nom || ''} ${rec.date_reception || ''}`.toLowerCase().includes(q);
  });
  const zone = document.getElementById('choix-resultats');
  if (!liste.length) {
    zone.innerHTML = '<div class="ach-vide" style="padding:1rem;">Aucune réception clôturée.</div>';
    return;
  }
  zone.innerHTML = liste.map(rec => `
    <div class="fac-choix-item ${rec._deja ? 'deja-facturee' : ''}" data-rid="${rec._deja ? '' : rec.id}">
      <div>
        <strong>${escHtml(rec.fournisseur_nom || 'Fournisseur ?')}</strong>
        <div class="fac-choix-meta">${escHtml(rec.date_reception || '')} · ${rec.nb_lignes ?? 0} article(s)</div>
      </div>
      <div class="fac-choix-meta">${rec._deja ? '✓ déjà facturée' : 'Facturer →'}</div>
    </div>`).join('');

  zone.querySelectorAll('.fac-choix-item[data-rid]').forEach(el => {
    if (!el.dataset.rid) return;
    el.addEventListener('click', () => creerDepuisReception(el.dataset.rid));
  });
}

async function creerDepuisReception(receptionId) {
  const r = await fetch(`${API_FAC}/depuis-reception/${receptionId}`, { method: 'POST' });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    alert(err.detail || 'Impossible de créer la facture.');
    return;
  }
  const fac = await r.json();
  fermerChoixReception();
  await chargerFactures();
  ouvrirFacture(fac.id, fac);
}

function fermerChoixReception() {
  document.getElementById('modal-choix-reception').hidden = true;
}

// ── Détail / rapprochement ───────────────────────────────────
async function ouvrirFacture(id, prefetch) {
  const fac = prefetch || await fetch(`${API_FAC}/${id}`).then(r => r.json());
  facCourante = fac;

  document.getElementById('modal-fac-titre').textContent =
    `Facture ${fac.numero_facture || '(brouillon)'} — ${fac.fournisseur_nom || ''}`;
  document.getElementById('fac-id').value = fac.id;
  document.getElementById('fac-fournisseur-nom').value = fac.fournisseur_nom || '';
  document.getElementById('fac-numero').value = fac.numero_facture || '';
  document.getElementById('fac-date').value = fac.date_facture || '';
  document.getElementById('fac-commande').value = fac.numero_commande || '(aucune commande rapprochée)';
  document.getElementById('fac-commentaire').value = fac.commentaire || '';
  document.getElementById('fac-form-erreur').hidden = true;

  rendreLignes(fac.lignes || []);
  rendreTotaux(fac);
  document.getElementById('modal-facture').hidden = false;
}

function rendreLignes(lignes) {
  const tbody = document.getElementById('tbody-lignes-facture');
  if (!lignes.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="ach-vide">Aucune ligne.</td></tr>';
    return;
  }
  tbody.innerHTML = lignes.map(l => {
    const ecart = l.ecart_montant_ht ?? 0;
    const enLitige = l.statut_ligne === 'litige';
    return `
      <tr data-lid="${l.id}" class="${enLitige ? 'fac-ligne--litige' : ''}">
        <td>${escHtml(l.designation)}${l.code_article ? `<div class="fac-choix-meta">${escHtml(l.code_article)}</div>` : ''}</td>
        <td class="ach-col-num">${l.poids_recu_kg != null ? fmtPrix(l.poids_recu_kg) : '—'}</td>
        <td class="ach-col-num">
          <input type="number" step="0.001" min="0" class="fac-input" data-champ="poids_facture_kg"
                 value="${l.poids_facture_kg != null ? l.poids_facture_kg : ''}">
        </td>
        <td class="ach-col-num">${l.prix_commande_ht != null ? fmtPrix(l.prix_commande_ht) + ' €' : '—'}</td>
        <td class="ach-col-num">
          <input type="number" step="0.01" min="0" class="fac-input" data-champ="prix_facture_ht"
                 value="${l.prix_facture_ht != null ? l.prix_facture_ht : ''}">
        </td>
        <td class="ach-col-num">${fmtPrix(l.montant_facture_ht)} €</td>
        <td class="ach-col-num fac-ecart ${classeEcart(ecart)}">${signe(ecart)}${fmtPrix(Math.abs(ecart))} €</td>
        <td style="text-align:center;">
          <button class="fac-btn-litige ${enLitige ? 'actif' : ''}" data-litige="${l.id}"
                  title="${enLitige ? (l.commentaire_litige || 'En litige') : 'Marquer en litige'}">
            ${enLitige ? '⚠' : '○'}
          </button>
        </td>
      </tr>`;
  }).join('');

  // Saisie inline : recalcul serveur au blur (Enter = blur)
  tbody.querySelectorAll('input.fac-input').forEach(inp => {
    inp.addEventListener('change', () => majLigne(inp));
    inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') inp.blur(); });
  });
  tbody.querySelectorAll('[data-litige]').forEach(btn => {
    btn.addEventListener('click', () => basculerLitige(btn.dataset.litige));
  });
}

async function majLigne(input) {
  const tr = input.closest('tr');
  const ligneId = tr.dataset.lid;
  const champ = input.dataset.champ;
  const val = input.value === '' ? null : parseFloat(input.value);

  const r = await fetch(`${API_FAC}/${facCourante.id}/lignes/${ligneId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ [champ]: val }),
  });
  if (!r.ok) { alert('Échec de la mise à jour.'); return; }
  // Recharger la facture pour rafraîchir écarts + totaux (source de vérité = serveur)
  facCourante = await fetch(`${API_FAC}/${facCourante.id}`).then(x => x.json());
  rendreLignes(facCourante.lignes || []);
  rendreTotaux(facCourante);
}

function rendreTotaux(fac) {
  document.getElementById('fac-total-attendu').textContent = fmtPrix(fac.montant_total_ht_attendu) + ' €';
  document.getElementById('fac-total-facture').textContent = fmtPrix(fac.montant_total_ht_facture) + ' €';
  const ecart = fac.ecart_total_ht ?? 0;
  const span = document.getElementById('fac-total-ecart');
  span.textContent = signe(ecart) + fmtPrix(Math.abs(ecart)) + ' €';
  const bar = span.closest('.ach-total-bar');
  bar.classList.remove('fac-total-ecart--haut', 'fac-total-ecart--bas', 'fac-total-ecart--nul');
  bar.classList.add(`fac-total-ecart--${niveauEcart(ecart)}`);
}

// ── Litige ───────────────────────────────────────────────────
function basculerLitige(ligneId) {
  const ligne = (facCourante.lignes || []).find(l => String(l.id) === String(ligneId));
  if (ligne && ligne.statut_ligne === 'litige') {
    // Déjà en litige → on lève le litige directement
    appliquerLitige(ligneId, 'ok', null);
  } else {
    document.getElementById('litige-ligne-id').value = ligneId;
    document.getElementById('litige-commentaire').value = ligne?.commentaire_litige || '';
    document.getElementById('modal-litige').hidden = false;
  }
}

async function confirmerLitige() {
  const ligneId = document.getElementById('litige-ligne-id').value;
  const commentaire = document.getElementById('litige-commentaire').value.trim();
  await appliquerLitige(ligneId, 'litige', commentaire || null);
  fermerModalLitige();
}

async function appliquerLitige(ligneId, statut, commentaire) {
  const body = { statut_ligne: statut };
  if (commentaire !== undefined) body.commentaire_litige = commentaire || '';
  const r = await fetch(`${API_FAC}/${facCourante.id}/lignes/${ligneId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) { alert('Échec.'); return; }
  facCourante = await fetch(`${API_FAC}/${facCourante.id}`).then(x => x.json());
  rendreLignes(facCourante.lignes || []);
  rendreTotaux(facCourante);
}

function fermerModalLitige() {
  document.getElementById('modal-litige').hidden = true;
}

// ── Enregistrer / valider entête ─────────────────────────────
async function sauverFacture(valider) {
  const body = {
    numero_facture: document.getElementById('fac-numero').value.trim() || null,
    date_facture: document.getElementById('fac-date').value || null,
    commentaire: document.getElementById('fac-commentaire').value.trim() || null,
  };
  if (valider) {
    // Une ligne en litige ⇒ statut "litige", sinon "validee"
    const litiges = (facCourante.lignes || []).some(l => l.statut_ligne === 'litige');
    body.statut = litiges ? 'litige' : 'validee';
  }
  const r = await fetch(`${API_FAC}/${facCourante.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    const zone = document.getElementById('fac-form-erreur');
    zone.textContent = err.detail || 'Échec de l\'enregistrement.';
    zone.hidden = false;
    return;
  }
  fermerModalFacture();
  await chargerFactures();
}

async function supprimerFacture() {
  if (!confirm('Supprimer cette facture ? La réception n\'est pas affectée.')) return;
  const r = await fetch(`${API_FAC}/${facCourante.id}`, { method: 'DELETE' });
  if (!r.ok) { alert('Échec de la suppression.'); return; }
  fermerModalFacture();
  await chargerFactures();
}

function fermerModalFacture() {
  document.getElementById('modal-facture').hidden = true;
  facCourante = null;
}

// ── Exports ──────────────────────────────────────────────────
// PDF : ouvre la page imprimable dans un onglet ; le navigateur fait « Enregistrer en PDF ».
function exporterPdf() {
  if (!facCourante) return;
  window.open(`${API_FAC}/${facCourante.id}/imprimer`, '_blank');
}

// Excel : déclenche le téléchargement du vrai fichier .xlsx.
function exporterXlsx() {
  if (!facCourante) return;
  window.location.href = `${API_FAC}/${facCourante.id}/export.xlsx`;
}

// ── Helpers ──────────────────────────────────────────────────
function fmtPrix(v) { return (v ?? 0).toFixed(2).replace('.', ','); }
function signe(v) { return v > 0.0001 ? '+' : (v < -0.0001 ? '−' : ''); }
function niveauEcart(v) { return v > 0.0001 ? 'haut' : (v < -0.0001 ? 'bas' : 'nul'); }
function classeEcart(v) { return 'fac-ecart--' + niveauEcart(v); }
function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

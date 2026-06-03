/* commandes.js — Module Commandes */

const API_CMD   = '/api/achats/commandes';
const API_FOURN = '/api/achats/fournisseurs';
const API_CAT   = '/api/achats/catalogue';

let commandes    = [];
let fournisseurs = [];
let catalogue    = [];
let cmdCourante  = null; // commande en cours d'édition

const STATUT_LABELS = { brouillon: 'Brouillon', confirmee: 'Confirmée', livree: 'Livrée', annulee: 'Annulée' };

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await Promise.all([chargerFournisseurs(), chargerCommandes()]);
  bindEvents();
});

function bindEvents() {
  document.getElementById('btn-nouvelle').addEventListener('click', ouvrirNouvelleCommande);
  document.getElementById('modal-cmd-fermer').addEventListener('click', fermerModalCmd);
  document.getElementById('btn-fermer-cmd').addEventListener('click', fermerModalCmd);
  document.getElementById('btn-sauver-cmd').addEventListener('click', sauverCommande);
  document.getElementById('btn-envoyer-cmd').addEventListener('click', envoyerCommande);
  document.getElementById('btn-dupliquer').addEventListener('click', dupliquerCommande);
  document.getElementById('btn-annuler-cmd').addEventListener('click', annulerCommande);
  document.getElementById('btn-ajouter-ligne').addEventListener('click', ouvrirModalLigne);
  document.getElementById('modal-ligne-fermer').addEventListener('click', fermerModalLigne);
  document.getElementById('btn-ligne-annuler').addEventListener('click', fermerModalLigne);
  document.getElementById('form-ligne').addEventListener('submit', ajouterLigne);
  document.getElementById('filtre-fournisseur').addEventListener('change', filtrer);
  document.getElementById('filtre-statut').addEventListener('change', filtrer);
  document.getElementById('ligne-search').addEventListener('input', rechercherCatalogue);
  document.getElementById('cmd-fournisseur').addEventListener('change', onFournisseurChange);
}

// ── Chargement ───────────────────────────────────────────────
async function chargerFournisseurs() {
  const r = await fetch(API_FOURN);
  fournisseurs = await r.json();
  const selFiltre = document.getElementById('filtre-fournisseur');
  const selForm   = document.getElementById('cmd-fournisseur');
  fournisseurs.forEach(f => {
    selFiltre.insertAdjacentHTML('beforeend', `<option value="${f.id}">${escHtml(f.nom)}</option>`);
    selForm.insertAdjacentHTML('beforeend', `<option value="${f.id}">${escHtml(f.nom)}</option>`);
  });
}

async function chargerCommandes() {
  try {
    const r = await fetch(`${API_CMD}?limit=200`);
    commandes = await r.json();
    afficherStats();
    afficherTable(commandes);
  } catch(e) {
    afficherErreur('Impossible de charger les commandes : ' + e.message);
  }
}

function afficherStats() {
  document.getElementById('stat-brouillon').textContent = commandes.filter(c => c.statut === 'brouillon').length;
  document.getElementById('stat-confirmee').textContent = commandes.filter(c => c.statut === 'confirmee').length;
  document.getElementById('stat-livree').textContent    = commandes.filter(c => c.statut === 'livree').length;
}

function filtrer() {
  const fourn  = document.getElementById('filtre-fournisseur').value;
  const statut = document.getElementById('filtre-statut').value;
  const filtre = commandes.filter(c => {
    if (fourn  && String(c.fournisseur_id) !== fourn)  return false;
    if (statut && c.statut !== statut) return false;
    return true;
  });
  afficherTable(filtre);
}

function afficherTable(liste) {
  const tbody = document.getElementById('tbody-commandes');
  if (!liste.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="ach-vide">Aucune commande</td></tr>';
    return;
  }
  tbody.innerHTML = liste.map(c => `
    <tr>
      <td><code>${escHtml(c.numero_commande)}</code></td>
      <td>${fmtDate(c.date_commande)}</td>
      <td class="ach-cell-nom">${escHtml(c.fournisseur_nom)}</td>
      <td>${c.date_livraison_prevue ? fmtDate(c.date_livraison_prevue) : '<span style="color:#9ca3af">—</span>'}</td>
      <td class="ach-col-num">${c.nb_lignes ?? 0}</td>
      <td class="ach-col-num">${fmtPrix(c.montant_total_ht)} €</td>
      <td><span class="ach-badge ach-badge--${c.statut}">${STATUT_LABELS[c.statut] ?? c.statut}</span></td>
      <td class="ach-col-actions">
        <button class="ach-btn ach-btn--small" onclick="ouvrirCommande(${c.id})">Ouvrir</button>
      </td>
    </tr>
  `).join('');
}

// ── Modal commande ───────────────────────────────────────────
function ouvrirNouvelleCommande() {
  cmdCourante = null;
  document.getElementById('modal-cmd-titre').textContent = 'Nouvelle commande';
  document.getElementById('cmd-id').value = '';
  document.getElementById('cmd-fournisseur').value = '';
  document.getElementById('cmd-date').value = new Date().toISOString().slice(0,10);
  document.getElementById('cmd-livraison').value = '';
  document.getElementById('cmd-commentaire').value = '';
  document.getElementById('zone-lignes').innerHTML = '';
  document.getElementById('lignes-vide').hidden = false;
  document.getElementById('cmd-total').textContent = '0,00 €';
  document.getElementById('btn-envoyer-cmd').hidden = true;
  document.getElementById('btn-dupliquer').hidden = true;
  document.getElementById('btn-annuler-cmd').hidden = true;
  document.getElementById('btn-ajouter-ligne').disabled = true;
  document.getElementById('cmd-form-erreur').hidden = true;
  document.getElementById('modal-commande').hidden = false;
}

async function ouvrirCommande(id) {
  try {
    const r = await fetch(`${API_CMD}/${id}`);
    cmdCourante = await r.json();

    document.getElementById('modal-cmd-titre').textContent = cmdCourante.numero_commande;
    document.getElementById('cmd-id').value = cmdCourante.id;
    document.getElementById('cmd-fournisseur').value = cmdCourante.fournisseur_id;
    document.getElementById('cmd-date').value = cmdCourante.date_commande;
    document.getElementById('cmd-livraison').value = cmdCourante.date_livraison_prevue || '';
    document.getElementById('cmd-commentaire').value = cmdCourante.commentaire || '';

    const editable = cmdCourante.statut === 'brouillon';
    document.getElementById('btn-ajouter-ligne').disabled = !editable;
    document.getElementById('btn-envoyer-cmd').hidden = !editable;
    document.getElementById('btn-dupliquer').hidden = false;
    document.getElementById('btn-annuler-cmd').hidden = cmdCourante.statut === 'annulee' || cmdCourante.statut === 'livree';
    document.getElementById('cmd-form-erreur').hidden = true;

    // Charger catalogue fournisseur
    const rc = await fetch(`${API_CAT}?fournisseur_id=${cmdCourante.fournisseur_id}`);
    catalogue = await rc.json();

    afficherLignes(cmdCourante.lignes);
    document.getElementById('modal-commande').hidden = false;
  } catch(e) {
    afficherErreur('Erreur chargement commande : ' + e.message);
  }
}

function fermerModalCmd() {
  document.getElementById('modal-commande').hidden = true;
  cmdCourante = null;
}

function afficherLignes(lignes) {
  const zone = document.getElementById('zone-lignes');
  document.getElementById('lignes-vide').hidden = lignes.length > 0;
  if (!lignes.length) { zone.innerHTML = ''; calculerTotal([]); return; }

  zone.innerHTML = `
    <table class="ach-table" style="margin-top:var(--space-2);">
      <thead><tr>
        <th>Code</th><th>Désignation</th>
        <th class="ach-col-num">Qté</th><th>Unité</th>
        <th class="ach-col-num">Prix HT</th><th class="ach-col-num">Montant HT</th>
        <th class="ach-col-actions">Actions</th>
      </tr></thead>
      <tbody>
        ${lignes.map(l => `
          <tr>
            <td><code>${escHtml(l.code_article)}</code></td>
            <td class="ach-cell-nom">${escHtml(l.designation)}</td>
            <td class="ach-col-num">${l.quantite_commandee}</td>
            <td>${escHtml(l.unite)}</td>
            <td class="ach-col-num">${fmtPrix(l.prix_unitaire_ht)} €</td>
            <td class="ach-col-num"><strong>${fmtPrix(l.montant_ht)} €</strong></td>
            <td class="ach-col-actions">
              ${cmdCourante?.statut === 'brouillon'
                ? `<button class="ach-btn ach-btn--small ach-btn--danger" onclick="supprimerLigne(${l.id})">✕</button>`
                : ''}
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>`;
  calculerTotal(lignes);
}

function calculerTotal(lignes) {
  const total = lignes.reduce((s, l) => s + (l.montant_ht || 0), 0);
  document.getElementById('cmd-total').textContent = fmtPrix(total) + ' €';
}

// ── Sauvegarder commande ─────────────────────────────────────
async function sauverCommande() {
  const btn = document.getElementById('btn-sauver-cmd');
  btn.disabled = true; btn.textContent = 'Enregistrement…';

  const body = {
    fournisseur_id:       parseInt(document.getElementById('cmd-fournisseur').value),
    date_commande:        document.getElementById('cmd-date').value,
    date_livraison_prevue: document.getElementById('cmd-livraison').value || null,
    commentaire:          document.getElementById('cmd-commentaire').value.trim() || null,
  };

  try {
    const id = document.getElementById('cmd-id').value;
    if (id) {
      // Mise à jour
      await fetch(`${API_CMD}/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    } else {
      // Création
      const r = await fetch(API_CMD, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!r.ok) throw new Error((await r.json()).detail || 'Erreur');
      cmdCourante = await r.json();
      document.getElementById('cmd-id').value = cmdCourante.id;
      document.getElementById('modal-cmd-titre').textContent = cmdCourante.numero_commande;
      document.getElementById('btn-envoyer-cmd').hidden = false;
      document.getElementById('btn-dupliquer').hidden = false;
      document.getElementById('btn-ajouter-ligne').disabled = false;
      // Charger catalogue du fournisseur
      const rc = await fetch(`${API_CAT}?fournisseur_id=${cmdCourante.fournisseur_id}`);
      catalogue = await rc.json();
    }
    await chargerCommandes();
  } catch(err) {
    const z = document.getElementById('cmd-form-erreur');
    z.textContent = err.message; z.hidden = false;
  } finally {
    btn.disabled = false; btn.textContent = 'Enregistrer';
  }
}

async function envoyerCommande() {
  const id = document.getElementById('cmd-id').value;
  if (!id) return;
  const btn = document.getElementById('btn-envoyer-cmd');
  btn.disabled = true; btn.textContent = 'Envoi…';
  try {
    const r = await fetch(`${API_CMD}/${id}/envoyer`, { method: 'POST' });
    const result = await r.json();
    if (result.envoye) {
      alert(`✅ Commande envoyée à ${result.destinataire}`);
    } else {
      // Pas de config SMTP → afficher le contenu du mail
      alert(`⚠️ SMTP non configuré.\n\nDestinataire : ${result.destinataire}\n\n${result.corps}`);
    }
    await chargerCommandes();
    fermerModalCmd();
  } catch(e) {
    alert('Erreur : ' + e.message);
  } finally {
    btn.disabled = false; btn.textContent = '📧 Envoyer';
  }
}

async function dupliquerCommande() {
  const id = document.getElementById('cmd-id').value;
  if (!id || !confirm('Dupliquer cette commande ?')) return;
  const r = await fetch(`${API_CMD}/${id}/dupliquer`, { method: 'POST' });
  const nova = await r.json();
  await chargerCommandes();
  fermerModalCmd();
  ouvrirCommande(nova.id);
}

async function annulerCommande() {
  const id = document.getElementById('cmd-id').value;
  if (!id || !confirm('Annuler cette commande ? Cette action est irréversible.')) return;
  await fetch(`${API_CMD}/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ statut: 'annulee' }) });
  await chargerCommandes();
  fermerModalCmd();
}

// ── Modal ligne ───────────────────────────────────────────────
function ouvrirModalLigne() {
  document.getElementById('l-catalogue-id').value = '';
  document.getElementById('l-code').value = '';
  document.getElementById('l-designation').value = '';
  document.getElementById('l-quantite').value = '';
  document.getElementById('l-prix').value = '';
  document.getElementById('l-commentaire').value = '';
  document.getElementById('ligne-search').value = '';
  document.getElementById('ligne-resultats').innerHTML = '';
  document.getElementById('ligne-erreur').hidden = true;
  document.getElementById('modal-ligne').hidden = false;
  document.getElementById('ligne-search').focus();
}

function fermerModalLigne() {
  document.getElementById('modal-ligne').hidden = true;
}

function rechercherCatalogue() {
  const q = document.getElementById('ligne-search').value.toLowerCase();
  const zone = document.getElementById('ligne-resultats');
  if (!q) { zone.innerHTML = ''; return; }
  const resultats = catalogue.filter(a =>
    a.designation.toLowerCase().includes(q) || a.code_article.toLowerCase().includes(q)
  ).slice(0, 20);
  if (!resultats.length) {
    zone.innerHTML = '<p class="ach-vide" style="padding:var(--space-2);">Aucun article trouvé dans le catalogue</p>';
    return;
  }
  zone.innerHTML = resultats.map(a => `
    <div onclick="selectionnerArticle(${a.id})" style="padding:.65rem 1rem; cursor:pointer; border-bottom:1px solid #f1ead9; display:flex; justify-content:space-between; align-items:center;">
      <div>
        <strong style="font-size:var(--text-sm);">${escHtml(a.designation)}</strong>
        <span style="font-size:var(--text-xs); color:#6b7280; margin-left:.5rem;"><code>${escHtml(a.code_article)}</code></span>
      </div>
      <span style="font-weight:700; font-size:var(--text-sm);">${fmtPrix(a.prix_achat_ht)} €</span>
    </div>
  `).join('');
}

function selectionnerArticle(id) {
  const a = catalogue.find(x => x.id === id);
  if (!a) return;
  document.getElementById('l-catalogue-id').value = a.id;
  document.getElementById('l-code').value = a.code_article;
  document.getElementById('l-designation').value = a.designation;
  document.getElementById('l-prix').value = a.prix_achat_ht;
  document.getElementById('ligne-search').value = a.designation;
  document.getElementById('ligne-resultats').innerHTML = '';
  document.getElementById('l-quantite').focus();
}

async function ajouterLigne(e) {
  e.preventDefault();
  const id = document.getElementById('cmd-id').value;
  if (!id) { alert('Sauvegardez la commande d\'abord'); return; }

  const body = {
    catalogue_fournisseur_id: document.getElementById('l-catalogue-id').value ? parseInt(document.getElementById('l-catalogue-id').value) : null,
    code_article:   document.getElementById('l-code').value.trim(),
    designation:    document.getElementById('l-designation').value.trim(),
    quantite_commandee: parseFloat(document.getElementById('l-quantite').value),
    unite:          document.getElementById('l-unite').value,
    prix_unitaire_ht: parseFloat(document.getElementById('l-prix').value || 0),
    commentaire_ligne: document.getElementById('l-commentaire').value.trim() || null,
  };

  try {
    const r = await fetch(`${API_CMD}/${id}/lignes`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error((await r.json()).detail || 'Erreur');
    fermerModalLigne();
    // Recharger la commande
    const rc = await fetch(`${API_CMD}/${id}`);
    cmdCourante = await rc.json();
    afficherLignes(cmdCourante.lignes);
    await chargerCommandes();
  } catch(err) {
    const z = document.getElementById('ligne-erreur');
    z.textContent = err.message; z.hidden = false;
  }
}

async function supprimerLigne(ligneId) {
  const id = document.getElementById('cmd-id').value;
  if (!confirm('Supprimer cet article ?')) return;
  await fetch(`${API_CMD}/${id}/lignes/${ligneId}`, { method: 'DELETE' });
  const rc = await fetch(`${API_CMD}/${id}`);
  cmdCourante = await rc.json();
  afficherLignes(cmdCourante.lignes);
  await chargerCommandes();
}

async function onFournisseurChange() {
  const fid = document.getElementById('cmd-fournisseur').value;
  if (!fid) { catalogue = []; return; }
  const r = await fetch(`${API_CAT}?fournisseur_id=${fid}`);
  catalogue = await r.json();
  document.getElementById('btn-ajouter-ligne').disabled = false;
}

// ── Utilitaires ──────────────────────────────────────────────
function afficherErreur(msg) {
  const z = document.getElementById('zone-erreur');
  z.textContent = msg; z.hidden = false;
}
function fmtDate(d) { if (!d) return '—'; return d.split('-').reverse().join('/'); }
function fmtPrix(v) { return (v ?? 0).toFixed(2).replace('.', ','); }
function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

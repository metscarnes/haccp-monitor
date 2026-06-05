/* commandes.js — Module Commandes v2 (panier multi-fournisseurs) */

const API_CMD   = '/api/achats/commandes';
const API_FOURN = '/api/achats/fournisseurs';
const API_CAT   = '/api/achats/catalogue';
const API_PANIER = '/api/achats/panier';
const LS_KEY    = 'haccp_panier';

let commandes    = [];
let fournisseurs = [];
let catalogueTous = [];   // tout le catalogue, tous fournisseurs
let catalogueCourant = []; // catalogue du fournisseur de la commande en édition
let cmdCourante  = null;
let panier       = [];    // [{ catalogueId, fournisseurId, fournisseurNom, code, designation, quantite, unite, prix }]

const STATUT_LABELS = { brouillon: 'Brouillon', confirmee: 'Confirmée', livree: 'Livrée', annulee: 'Annulée' };

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await Promise.all([chargerFournisseurs(), chargerCommandes(), chargerCatalogueTous()]);
  panierCharger();
  bindEvents();
});

function bindEvents() {
  // Panier
  document.getElementById('btn-panier').addEventListener('click', ouvrirPanier);
  document.getElementById('modal-panier-fermer').addEventListener('click', fermerPanier);
  document.getElementById('btn-panier-fermer').addEventListener('click', fermerPanier);
  document.getElementById('btn-panier-sauver').addEventListener('click', panierSauverBDD);
  document.getElementById('btn-panier-vider').addEventListener('click', panierVider);
  document.getElementById('btn-panier-generer').addEventListener('click', panierGenerer);
  document.getElementById('panier-search').addEventListener('input', rechercherCataloguePanier);
  document.getElementById('form-qte').addEventListener('submit', panierAjouterArticle);
  document.getElementById('modal-qte-fermer').addEventListener('click', fermerModalQte);
  document.getElementById('btn-qte-annuler').addEventListener('click', fermerModalQte);

  // Commande existante
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
  document.getElementById('ligne-search').addEventListener('input', rechercherCatalogueCmd);
}

// ── Chargement ───────────────────────────────────────────────
async function chargerFournisseurs() {
  const r = await fetch(API_FOURN);
  fournisseurs = await r.json();
  const selFiltre = document.getElementById('filtre-fournisseur');
  fournisseurs.forEach(f => {
    selFiltre.insertAdjacentHTML('beforeend', `<option value="${f.id}">${escHtml(f.nom)}</option>`);
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

async function chargerCatalogueTous() {
  try {
    const r = await fetch(API_CAT);
    catalogueTous = await r.json();
  } catch(e) {
    catalogueTous = [];
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
  afficherTable(commandes.filter(c => {
    if (fourn  && String(c.fournisseur_id) !== fourn) return false;
    if (statut && c.statut !== statut) return false;
    return true;
  }));
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

// ── Panier localStorage ──────────────────────────────────────
function panierCharger() {
  try {
    panier = JSON.parse(localStorage.getItem(LS_KEY) || '[]');
  } catch { panier = []; }
  majBadgePanier();
}

function panierSauver() {
  localStorage.setItem(LS_KEY, JSON.stringify(panier));
  majBadgePanier();
}

function majBadgePanier() {
  const badge = document.getElementById('badge-panier');
  if (panier.length > 0) {
    badge.textContent = panier.length;
    badge.hidden = false;
  } else {
    badge.hidden = true;
  }
}

async function panierSauverBDD() {
  const btn = document.getElementById('btn-panier-sauver');
  btn.disabled = true; btn.textContent = 'Sauvegarde…';
  try {
    const r = await fetch(API_PANIER, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lignes: panier.map(l => ({
          catalogue_fournisseur_id: l.catalogueId || null,
          fournisseur_id: l.fournisseurId,
          fournisseur_nom: l.fournisseurNom,
          code_article: l.code,
          designation: l.designation,
          quantite: l.quantite,
          unite: l.unite,
          prix_ht: l.prix,
        }))
      })
    });
    if (!r.ok) throw new Error('Erreur serveur');
    btn.textContent = '✅ Sauvegardé';
    setTimeout(() => { btn.textContent = '💾 Sauvegarder'; btn.disabled = false; }, 1500);
  } catch(e) {
    alert('Erreur sauvegarde : ' + e.message);
    btn.disabled = false; btn.textContent = '💾 Sauvegarder';
  }
}

async function panierRestaurerBDD() {
  try {
    const r = await fetch(API_PANIER);
    const lignes = await r.json();
    if (!lignes.length) return;
    if (!confirm(`Un panier sauvegardé contient ${lignes.length} article(s). Le restaurer ?`)) return;
    panier = lignes.map(l => ({
      catalogueId:   l.catalogue_fournisseur_id,
      fournisseurId: l.fournisseur_id,
      fournisseurNom: l.fournisseur_nom,
      code:          l.code_article,
      designation:   l.designation,
      quantite:      l.quantite,
      unite:         l.unite,
      prix:          l.prix_ht,
    }));
    panierSauver();
    afficherPanier();
  } catch(e) { /* silencieux */ }
}

function panierVider() {
  if (!panier.length || !confirm('Vider le panier ?')) return;
  panier = [];
  panierSauver();
  afficherPanier();
  // Vider aussi la BDD
  fetch(API_PANIER, { method: 'DELETE' }).catch(() => {});
}

// ── Modal panier ─────────────────────────────────────────────
async function ouvrirPanier() {
  // Proposer restauration BDD si panier local vide
  if (!panier.length) {
    await panierRestaurerBDD();
  }
  afficherPanier();
  document.getElementById('modal-panier').hidden = false;
  document.getElementById('panier-search').focus();
}

function fermerPanier() {
  document.getElementById('modal-panier').hidden = true;
  document.getElementById('panier-search').value = '';
  document.getElementById('panier-resultats').style.display = 'none';
  document.getElementById('panier-resultats').innerHTML = '';
}

function afficherPanier() {
  const zone = document.getElementById('panier-lignes-zone');

  if (!panier.length) {
    zone.innerHTML = '<p class="ach-vide" id="panier-vide">Votre panier est vide — recherchez des articles ci-dessus</p>';
    document.getElementById('panier-total').textContent = '0,00 €';
    majBadgePanier();
    return;
  }

  // Grouper par fournisseur
  const groupes = {};
  panier.forEach((l, idx) => {
    if (!groupes[l.fournisseurNom]) groupes[l.fournisseurNom] = [];
    groupes[l.fournisseurNom].push({ ...l, idx });
  });

  let html = '';
  Object.entries(groupes).forEach(([nomFourn, lignes]) => {
    const totalFourn = lignes.reduce((s, l) => s + l.quantite * l.prix, 0);
    html += `
      <div style="margin-bottom:var(--space-3);">
        <div style="font-weight:700; font-size:var(--text-sm); color:#5a3e28; padding:.4rem 0; border-bottom:2px solid #e8d9c4; display:flex; justify-content:space-between;">
          <span>🏪 ${escHtml(nomFourn)}</span>
          <span>${fmtPrix(totalFourn)} €</span>
        </div>
        <table class="ach-table" style="margin-top:var(--space-1);">
          <thead><tr>
            <th>Désignation</th>
            <th class="ach-col-num">Qté</th>
            <th>Unité</th>
            <th class="ach-col-num">Prix HT</th>
            <th class="ach-col-num">Montant</th>
            <th class="ach-col-actions"></th>
          </tr></thead>
          <tbody>
            ${lignes.map(l => `
              <tr>
                <td>
                  <div style="font-weight:600; font-size:var(--text-sm);">${escHtml(l.designation)}</div>
                  <div style="font-size:var(--text-xs); color:#6b7280;"><code>${escHtml(l.code)}</code></div>
                </td>
                <td class="ach-col-num">
                  <input type="number" value="${l.quantite}" min="0.001" step="0.001"
                    style="width:70px; text-align:right; border:1px solid #e8d9c4; border-radius:4px; padding:2px 4px;"
                    onchange="panierMajQuantite(${l.idx}, this.value)">
                </td>
                <td>${escHtml(l.unite)}</td>
                <td class="ach-col-num">${fmtPrix(l.prix)} €</td>
                <td class="ach-col-num"><strong>${fmtPrix(l.quantite * l.prix)} €</strong></td>
                <td class="ach-col-actions">
                  <button class="ach-btn ach-btn--small ach-btn--danger" onclick="panierSupprimerLigne(${l.idx})">✕</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>`;
  });

  zone.innerHTML = html;

  const total = panier.reduce((s, l) => s + l.quantite * l.prix, 0);
  document.getElementById('panier-total').textContent = fmtPrix(total) + ' €';
  majBadgePanier();
}

function panierMajQuantite(idx, valeur) {
  const qte = parseFloat(valeur);
  if (isNaN(qte) || qte <= 0) return;
  panier[idx].quantite = qte;
  panierSauver();
  // Recalculer seulement le montant de la ligne sans re-rendre tout
  const total = panier.reduce((s, l) => s + l.quantite * l.prix, 0);
  document.getElementById('panier-total').textContent = fmtPrix(total) + ' €';
  majBadgePanier();
}

function panierSupprimerLigne(idx) {
  panier.splice(idx, 1);
  panierSauver();
  afficherPanier();
}

// ── Recherche catalogue dans le panier ───────────────────────
function rechercherCataloguePanier() {
  const q = document.getElementById('panier-search').value.toLowerCase().trim();
  const zone = document.getElementById('panier-resultats');
  if (!q) { zone.style.display = 'none'; zone.innerHTML = ''; return; }

  const resultats = catalogueTous.filter(a =>
    a.designation.toLowerCase().includes(q) || a.code_article.toLowerCase().includes(q)
  ).slice(0, 30);

  zone.style.display = 'block';
  if (!resultats.length) {
    zone.innerHTML = '<p class="ach-vide" style="padding:var(--space-2);">Aucun article trouvé</p>';
    return;
  }

  zone.innerHTML = resultats.map(a => `
    <div onclick="ouvrirModalQte(${a.id})"
      style="padding:.6rem 1rem; cursor:pointer; border-bottom:1px solid #f1ead9; display:flex; justify-content:space-between; align-items:center;">
      <div>
        <strong style="font-size:var(--text-sm);">${escHtml(a.designation)}</strong>
        <span style="font-size:var(--text-xs); color:#6b7280; margin-left:.5rem;"><code>${escHtml(a.code_article)}</code></span>
        <span style="font-size:var(--text-xs); color:#9ca3af; margin-left:.5rem;">— ${escHtml(a.fournisseur_nom)}</span>
      </div>
      <span style="font-weight:700; font-size:var(--text-sm); white-space:nowrap; margin-left:.5rem;">${fmtPrix(a.prix_achat_ht)} €</span>
    </div>
  `).join('');
}

// ── Modal quantité ────────────────────────────────────────────
function ouvrirModalQte(catalogueId) {
  const a = catalogueTous.find(x => x.id === catalogueId);
  if (!a) return;
  const fourn = fournisseurs.find(f => f.id === a.fournisseur_id);

  document.getElementById('qte-catalogue-id').value  = a.id;
  document.getElementById('qte-fournisseur-id').value = a.fournisseur_id;
  document.getElementById('qte-fournisseur-nom').value = fourn ? fourn.nom : (a.fournisseur_nom || '');
  document.getElementById('qte-code').value        = a.code_article;
  document.getElementById('qte-designation').value = a.designation;
  document.getElementById('qte-prix').value        = a.prix_achat_ht;
  document.getElementById('modal-qte-titre').textContent = a.designation;
  document.getElementById('qte-valeur').value = '';

  // Pré-sélectionner l'unité selon format_prix
  const sel = document.getElementById('qte-unite');
  sel.value = (a.format_prix === 'piece') ? 'piece' : 'kg';

  document.getElementById('modal-qte').hidden = false;
  document.getElementById('qte-valeur').focus();
}

function fermerModalQte() {
  document.getElementById('modal-qte').hidden = true;
}

function panierAjouterArticle(e) {
  e.preventDefault();
  const item = {
    catalogueId:   parseInt(document.getElementById('qte-catalogue-id').value) || null,
    fournisseurId: parseInt(document.getElementById('qte-fournisseur-id').value),
    fournisseurNom: document.getElementById('qte-fournisseur-nom').value,
    code:          document.getElementById('qte-code').value,
    designation:   document.getElementById('qte-designation').value,
    quantite:      parseFloat(document.getElementById('qte-valeur').value),
    unite:         document.getElementById('qte-unite').value,
    prix:          parseFloat(document.getElementById('qte-prix').value),
  };

  // Si l'article existe déjà dans le panier (même catalogueId), additionner les quantités
  const existant = panier.findIndex(l => l.catalogueId && l.catalogueId === item.catalogueId);
  if (existant >= 0) {
    panier[existant].quantite += item.quantite;
  } else {
    panier.push(item);
  }

  panierSauver();
  fermerModalQte();

  // Vider la recherche et re-focus
  document.getElementById('panier-search').value = '';
  document.getElementById('panier-resultats').style.display = 'none';
  document.getElementById('panier-resultats').innerHTML = '';
  document.getElementById('panier-search').focus();

  afficherPanier();
}

// ── Génération des commandes ──────────────────────────────────
async function panierGenerer() {
  if (!panier.length) {
    alert('Le panier est vide.');
    return;
  }

  // Compter les fournisseurs distincts
  const fournIds = [...new Set(panier.map(l => l.fournisseurId))];
  const msg = `Générer ${fournIds.length} commande(s) brouillon pour :\n` +
    fournIds.map(id => {
      const f = fournisseurs.find(x => x.id === id);
      const nb = panier.filter(l => l.fournisseurId === id).length;
      return `  • ${f ? f.nom : id} (${nb} article(s))`;
    }).join('\n');

  if (!confirm(msg + '\n\nContinuer ?')) return;

  const btn = document.getElementById('btn-panier-generer');
  btn.disabled = true; btn.textContent = 'Génération…';

  try {
    const r = await fetch(`${API_PANIER}/generer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        date_livraison_prevue: document.getElementById('panier-livraison').value || null,
        commentaire: document.getElementById('panier-commentaire').value.trim() || null,
      })
    });
    if (!r.ok) throw new Error((await r.json()).detail || 'Erreur serveur');
    const result = await r.json();

    // Vider le panier local
    panier = [];
    panierSauver();
    fermerPanier();
    await chargerCommandes();

    alert(`✅ ${result.nb_commandes} commande(s) créée(s) en brouillon.`);
  } catch(e) {
    alert('Erreur : ' + e.message);
  } finally {
    btn.disabled = false; btn.textContent = '✅ Générer les commandes';
  }
}

// ── Modal commande existante ──────────────────────────────────
async function ouvrirCommande(id) {
  try {
    const r = await fetch(`${API_CMD}/${id}`);
    cmdCourante = await r.json();

    document.getElementById('modal-cmd-titre').textContent = cmdCourante.numero_commande;
    document.getElementById('cmd-id').value = cmdCourante.id;
    document.getElementById('cmd-fournisseur').value = cmdCourante.fournisseur_id;
    document.getElementById('cmd-fournisseur-nom').value = cmdCourante.fournisseur_nom;
    document.getElementById('cmd-date').value = cmdCourante.date_commande;
    document.getElementById('cmd-livraison').value = cmdCourante.date_livraison_prevue || '';
    document.getElementById('cmd-commentaire').value = cmdCourante.commentaire || '';

    const editable = cmdCourante.statut === 'brouillon';
    document.getElementById('btn-ajouter-ligne').disabled = !editable;
    document.getElementById('btn-envoyer-cmd').hidden = !editable;
    document.getElementById('btn-dupliquer').hidden = false;
    document.getElementById('btn-annuler-cmd').hidden = cmdCourante.statut === 'annulee' || cmdCourante.statut === 'livree';
    document.getElementById('btn-sauver-cmd').hidden = !editable;
    document.getElementById('cmd-form-erreur').hidden = true;

    const rc = await fetch(`${API_CAT}?fournisseur_id=${cmdCourante.fournisseur_id}`);
    catalogueCourant = await rc.json();

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
  if (!lignes.length) {
    zone.innerHTML = '<p class="ach-vide">Aucun article</p>';
    calculerTotal([]);
    return;
  }
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

async function sauverCommande() {
  const btn = document.getElementById('btn-sauver-cmd');
  btn.disabled = true; btn.textContent = 'Enregistrement…';
  const id = document.getElementById('cmd-id').value;
  const body = {
    date_livraison_prevue: document.getElementById('cmd-livraison').value || null,
    commentaire:           document.getElementById('cmd-commentaire').value.trim() || null,
  };
  try {
    await fetch(`${API_CMD}/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
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

// ── Modal ajout ligne (commande existante) ────────────────────
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

function rechercherCatalogueCmd() {
  const q = document.getElementById('ligne-search').value.toLowerCase();
  const zone = document.getElementById('ligne-resultats');
  if (!q) { zone.innerHTML = ''; return; }
  const resultats = catalogueCourant.filter(a =>
    a.designation.toLowerCase().includes(q) || a.code_article.toLowerCase().includes(q)
  ).slice(0, 20);
  if (!resultats.length) {
    zone.innerHTML = '<p class="ach-vide" style="padding:var(--space-2);">Aucun article trouvé dans le catalogue</p>';
    return;
  }
  zone.innerHTML = resultats.map(a => `
    <div onclick="selectionnerArticleCmd(${a.id})" style="padding:.65rem 1rem; cursor:pointer; border-bottom:1px solid #f1ead9; display:flex; justify-content:space-between; align-items:center;">
      <div>
        <strong style="font-size:var(--text-sm);">${escHtml(a.designation)}</strong>
        <span style="font-size:var(--text-xs); color:#6b7280; margin-left:.5rem;"><code>${escHtml(a.code_article)}</code></span>
      </div>
      <span style="font-weight:700; font-size:var(--text-sm);">${fmtPrix(a.prix_achat_ht)} €</span>
    </div>
  `).join('');
}

function selectionnerArticleCmd(id) {
  const a = catalogueCourant.find(x => x.id === id);
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

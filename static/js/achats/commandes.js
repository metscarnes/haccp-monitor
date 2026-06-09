/* commandes.js — Module Commandes v2 (panier multi-fournisseurs) */

const API_CMD   = '/api/achats/commandes';
const API_FOURN = '/api/achats/fournisseurs';
const API_CAT   = '/api/achats/catalogue';
const API_PANIER = '/api/achats/panier';
const LS_KEY    = 'haccp_panier';

let commandes    = [];
let fournisseurs = [];
let catalogueTous = [];   // tout le catalogue, tous fournisseurs (avec stock)
let catalogueCourant = []; // catalogue du fournisseur de la commande en édition
let cmdCourante  = null;
let forcerEnvoiFlag = false; // Flag pour forcer l'envoi malgré les délais
// Panier : map { catalogueId → { quantite, unite } }. unite ∈ { 'kg','piece','colis' }.
// Les autres infos (prix, designation…) sont relues dans catalogueTous au
// moment de l'affichage / génération.
let panier       = {};
// Unité choisie par ligne même sans quantité (UX tablette : on peut cliquer
// l'unité avant de taper). Non persistée — réinitialisée à chaque session.
let uniteChoisies = {};

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
  document.getElementById('panier-search').addEventListener('input', afficherCataloguePanier);
  document.getElementById('panier-filtre-fournisseur').addEventListener('change', afficherCataloguePanier);
  document.getElementById('panier-filtre-selection').addEventListener('change', afficherCataloguePanier);
  document.getElementById('btn-test-plus1').addEventListener('click', testPlus1);

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
  document.getElementById('panier-livraison').addEventListener('change', verifierDelaisPanier);
  document.getElementById('cmd-livraison').addEventListener('change', verifierDelaisCommande);
}

// ── Chargement ───────────────────────────────────────────────
async function chargerFournisseurs() {
  const r = await fetch(API_FOURN);
  fournisseurs = await r.json();
  const selFiltre  = document.getElementById('filtre-fournisseur');
  const selPanier  = document.getElementById('panier-filtre-fournisseur');
  fournisseurs.forEach(f => {
    const opt = `<option value="${f.id}">${escHtml(f.nom)}</option>`;
    selFiltre.insertAdjacentHTML('beforeend', opt);
    selPanier.insertAdjacentHTML('beforeend', opt);
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
    const r = await fetch(`${API_CAT}?avec_stock=true`);
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

// ── Panier (localStorage) ────────────────────────────────────
// Modèle : panier = { [catalogueId]: quantite }. Le détail article (prix,
// fournisseur, unité…) est relu dans catalogueTous au moment voulu.

function panierCharger() {
  try {
    panier = JSON.parse(localStorage.getItem(LS_KEY) || '{}');
    if (Array.isArray(panier)) panier = {};   // compat ancien format (tableau)
  } catch { panier = {}; }
  panierNormaliser();
  majBadgePanier();
}

// Convertit toute entrée au format objet { quantite, unite }.
// Ancien format : la valeur était directement un nombre (= quantité).
function panierNormaliser() {
  for (const [catId, val] of Object.entries(panier)) {
    if (typeof val === 'number') {
      const a = catalogueTous.find(x => x.id === parseInt(catId));
      panier[catId] = { quantite: val, unite: a ? uniteParDefaut(a) : 'kg' };
    } else if (val && typeof val === 'object') {
      if (typeof val.quantite !== 'number') val.quantite = parseFloat(val.quantite) || 0;
      if (!val.unite) {
        const a = catalogueTous.find(x => x.id === parseInt(catId));
        val.unite = a ? uniteParDefaut(a) : 'kg';
      }
    } else {
      delete panier[catId];
    }
  }
}

// Accès aux deux composantes du panier
function panierQte(catId)   { const e = panier[catId]; return e ? (e.quantite || 0) : 0; }
// Unité d'une ligne : celle du panier si présent, sinon le choix mémorisé
// (uniteChoisies), sinon l'unité par défaut de l'article.
function panierUnite(catId) {
  const e = panier[catId];
  if (e && e.unite) return e.unite;
  if (uniteChoisies[catId]) return uniteChoisies[catId];
  const a = catalogueTous.find(x => x.id === parseInt(catId));
  return a ? uniteParDefaut(a) : 'kg';
}

function panierSauver() {
  localStorage.setItem(LS_KEY, JSON.stringify(panier));
  majBadgePanier();
}

function panierNbArticles() {
  return Object.keys(panier).length;
}

function majBadgePanier() {
  const badge = document.getElementById('badge-panier');
  const n = panierNbArticles();
  if (n > 0) { badge.textContent = n; badge.hidden = false; }
  else { badge.hidden = true; }
}

// Unité de commande par défaut = unité naturelle du prix de l'article si elle
// est commandable, sinon la première unité commandable disponible.
function uniteParDefaut(a) {
  const naturelle = (a.format_prix === 'kg') ? 'kg' : 'colis';
  if (peutCommander(a, naturelle)) return naturelle;
  return ['colis', 'kg', 'piece'].find(u => peutCommander(a, u)) || naturelle;
}

// Poids d'un colis en kg (champ généré, peut être absent/0 → null).
function poidsColisKg(a) {
  const p = parseFloat(a.poids_colis_kg);
  return (!isNaN(p) && p > 0) ? p : null;
}
// Poids d'une pièce en kg (peut être absent/0 → null).
function poidsUnitKg(a) {
  const p = parseFloat(a.poids_unitaire_kg);
  return (!isNaN(p) && p > 0) ? p : null;
}
// Nb de pièces par colis (peut être absent/0 → null).
function qteParColis(a) {
  const n = parseFloat(a.qte_par_colis);
  return (!isNaN(n) && n > 0) ? n : null;
}

// Liste des unités autorisées par le fournisseur (CSV en BDD).
// Vide/absent → tout autorisé (rétrocompat articles sans la colonne).
function unitesAutorisees(a) {
  const csv = a.unites_autorisees;
  if (!csv || !csv.trim()) return ['kg', 'piece', 'colis'];
  return csv.split(',').map(s => s.trim()).filter(Boolean);
}

// Une unité de commande est-elle possible pour cet article ? Il faut À LA FOIS :
//  1) que le fournisseur l'autorise (unites_autorisees)
//  2) que la conversion soit calculable (données qte/poids présentes)
function peutCommander(a, unite) {
  return unitesAutorisees(a).includes(unite);
}
function peutCommanderKg(a)    { return peutCommander(a, 'kg'); }
function peutCommanderPiece(a) { return peutCommander(a, 'piece'); }
function peutCommanderColis(a) { return peutCommander(a, 'colis'); }

// Prix unitaire HT pour une unité de commande ('kg' | 'piece' | 'colis').
// Renvoie null si la conversion est impossible (donnée manquante).
//   format kg    : prix = €/kg     → pièce = prix×poids_unit ; colis = prix×poids_colis
//   format colis : prix = €/colis  → kg = prix÷poids_colis ; pièce = prix÷qte_par_colis
function prixUnitaire(a, unite) {
  const prix       = parseFloat(a.prix_achat_ht) || 0;
  const poidsColis = poidsColisKg(a);
  const poidsUnit  = poidsUnitKg(a);
  const parColis   = qteParColis(a);
  if (a.format_prix === 'kg') {
    if (unite === 'piece') return poidsUnit  !== null ? prix * poidsUnit  : null;
    if (unite === 'colis') return poidsColis !== null ? prix * poidsColis : null;
    return prix;                       // kg
  }
  // format 'colis' (ou ancien 'piece') : prix = €/colis
  if (unite === 'kg')    return poidsColis !== null ? prix / poidsColis : null;
  if (unite === 'piece') return parColis   !== null ? prix / parColis   : null;
  return prix;                         // colis
}

// Libellé court d'une unité de commande.
function uniteLabel(unite) {
  return unite === 'piece' ? 'pièce' : unite;   // 'kg' | 'pièce' | 'colis'
}

// Badges des unités réellement commandables pour cet article (autorisées par
// le fournisseur ET calculables). Affiché dans la colonne « Unités cmd ».
function fmtUnitesAutorisees(a) {
  const dispo = ['kg', 'piece', 'colis'].filter(u => peutCommander(a, u));
  if (!dispo.length) return '<span style="color:#9ca3af">—</span>';
  return dispo.map(u =>
    `<span class="ach-badge ach-badge--dlc" style="margin:1px;">${uniteLabel(u)}</span>`
  ).join(' ');
}

// Formate un poids en kg (3 décimales max, virgule, sans zéros inutiles).
function fmtKg(v) {
  return parseFloat(v.toFixed(3)).toString().replace('.', ',');
}
// Formate un nb de pièces/colis (entier si rond, sinon ~).
function fmtUnites(v) {
  const arrondi = Math.round(v);
  const proche = Math.abs(v - arrondi) < 0.01;
  return (proche ? arrondi : parseFloat(v.toFixed(1))).toString().replace('.', ',');
}

// Détail « ce qu'on reçoit » pour une quantité dans une unité donnée.
// Renvoie une string descriptive (ex. "≈ 11 pièces · 93,5 kg") ou '' si rien d'utile.
function detailReception(a, qte, unite) {
  if (!qte) return '';
  const poidsColis = poidsColisKg(a);
  const poidsUnit  = poidsUnitKg(a);
  const parColis   = qteParColis(a);
  const parts = [];

  if (unite === 'colis') {
    if (parColis !== null)   parts.push(`${fmtUnites(qte * parColis)} pièce(s)`);
    if (poidsColis !== null) parts.push(`${fmtKg(qte * poidsColis)} kg`);
  } else if (unite === 'piece') {
    if (poidsUnit !== null)  parts.push(`${fmtKg(qte * poidsUnit)} kg`);
  } else { // kg
    if (poidsColis !== null) parts.push(`${fmtUnites(qte / poidsColis)} colis`);
    if (poidsUnit !== null)  parts.push(`${fmtUnites(qte / poidsUnit)} pièce(s)`);
  }
  return parts.length ? '≈ ' + parts.join(' · ') : '';
}

// Total estimé d'une ligne du panier (qté × prix unitaire selon l'unité choisie).
function totalLignePanier(a, qte, unite) {
  const pu = prixUnitaire(a, unite);
  return pu !== null ? qte * pu : null;
}

async function panierSauverBDD() {
  const btn = document.getElementById('btn-panier-sauver');
  btn.disabled = true; btn.textContent = 'Sauvegarde…';
  try {
    const r = await fetch(API_PANIER, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lignes: panierVersLignes() })
    });
    if (!r.ok) throw new Error('Erreur serveur');
    btn.textContent = '✅ Sauvegardé';
    setTimeout(() => { btn.textContent = '💾 Sauvegarder'; btn.disabled = false; }, 1500);
  } catch(e) {
    alert('Erreur sauvegarde : ' + e.message);
    btn.disabled = false; btn.textContent = '💾 Sauvegarder';
  }
}

// Construit la liste détaillée du panier à partir de catalogueTous
function panierVersLignes() {
  const lignes = [];
  for (const catId of Object.keys(panier)) {
    const a = catalogueTous.find(x => x.id === parseInt(catId));
    const qte = panierQte(catId);
    if (!a || !qte) continue;
    const unite = panierUnite(catId);
    const pu = prixUnitaire(a, unite);
    lignes.push({
      catalogue_fournisseur_id: a.id,
      fournisseur_id:  a.fournisseur_id,
      fournisseur_nom: a.fournisseur_nom,
      code_article:    a.code_article,
      designation:     a.designation,
      quantite:        qte,
      unite:           unite,
      prix_ht:         pu !== null ? pu : (parseFloat(a.prix_achat_ht) || 0),
    });
  }
  return lignes;
}

async function panierRestaurerBDD() {
  try {
    const r = await fetch(API_PANIER);
    const lignes = await r.json();
    if (!lignes.length) return;
    if (!confirm(`Un panier sauvegardé contient ${lignes.length} article(s). Le restaurer ?`)) return;
    panier = {};
    lignes.forEach(l => {
      if (!l.catalogue_fournisseur_id) return;
      const a = catalogueTous.find(x => x.id === l.catalogue_fournisseur_id);
      const unite = l.unite || (a ? uniteParDefaut(a) : 'kg');
      panier[l.catalogue_fournisseur_id] = { quantite: l.quantite, unite };
    });
    panierSauver();
  } catch(e) { /* silencieux */ }
}

function panierVider() {
  if (!panierNbArticles() || !confirm('Vider le panier ?')) return;
  panier = {};
  panierSauver();
  afficherCataloguePanier();
  fetch(API_PANIER, { method: 'DELETE' }).catch(() => {});
}

// ── Modal panier ─────────────────────────────────────────────
async function ouvrirPanier() {
  if (!panierNbArticles()) {
    await panierRestaurerBDD();
  }
  document.getElementById('panier-search').value = '';
  document.getElementById('panier-filtre-fournisseur').value = '';
  document.getElementById('panier-filtre-selection').checked = false;
  afficherCataloguePanier();
  document.getElementById('modal-panier').hidden = false;
}

function fermerPanier() {
  document.getElementById('modal-panier').hidden = true;
}

// Affiche le catalogue filtré, avec stepper de quantité par ligne
function afficherCataloguePanier() {
  const q      = document.getElementById('panier-search').value.toLowerCase().trim();
  const fourn  = document.getElementById('panier-filtre-fournisseur').value;
  const selOnly = document.getElementById('panier-filtre-selection').checked;
  const tbody  = document.getElementById('tbody-panier-catalogue');

  let liste = catalogueTous.filter(a => {
    if (fourn && String(a.fournisseur_id) !== fourn) return false;
    if (selOnly && !panierQte(String(a.id))) return false;
    if (q && !(a.designation.toLowerCase().includes(q) || a.code_article.toLowerCase().includes(q))) return false;
    return true;
  });

  if (!liste.length) {
    tbody.innerHTML = '<tr><td colspan="11" class="ach-vide">Aucun article</td></tr>';
    majTotalPanier();
    return;
  }

  tbody.innerHTML = liste.map(a => {
    const id = String(a.id);
    const qte = panierQte(id);
    const unite = panierUnite(id);
    const formatLbl = a.format_prix === 'kg' ? '€/kg' : '€/colis';
    const stock = a.stock ?? 0;
    const kgOk = peutCommanderKg(a);
    const pieceOk = peutCommanderPiece(a);
    const colisOk = peutCommanderColis(a);
    const totalLigne = qte > 0 ? totalLignePanier(a, qte, unite) : null;
    // Indice de conversion : prix équivalent dans l'autre unité
    const puAffiche = prixUnitaire(a, unite);
    return `
      <tr class="${qte > 0 ? 'ach-row--au-panier' : ''}">
        <td class="ach-cell-nom">${escHtml(a.fournisseur_nom)}</td>
        <td><code>${escHtml(a.code_article)}</code></td>
        <td class="ach-cell-nom">${escHtml(a.designation)}</td>
        <td class="ach-col-num">${fmtPrix(a.prix_achat_ht)} ${formatLbl}</td>
        <td>${a.format_prix === 'kg' ? 'kg' : 'colis'}</td>
        <td class="ach-col-num">${a.tva_percent != null ? a.tva_percent + '%' : '—'}</td>
        <td>${fmtUnitesAutorisees(a)}</td>
        <td class="ach-col-num">${stock > 0
            ? `<strong>${stock}</strong>`
            : '<span style="color:#9ca3af">0</span>'}</td>
        <td>
          <div class="ach-qte-cell">
            <input type="number" min="0" step="any" value="${qte || ''}" placeholder="0"
                   class="ach-qte-input" onchange="panierSetQte(${a.id}, this.value)">
            <div class="ach-unite-btns" role="group">
              <button type="button" class="ach-unite-btn ${unite === 'kg' ? 'is-active' : ''}"
                      ${kgOk ? '' : 'disabled'} onclick="panierSetUnite(${a.id}, 'kg')">kg</button>
              <button type="button" class="ach-unite-btn ${unite === 'piece' ? 'is-active' : ''}"
                      ${pieceOk ? '' : 'disabled'} onclick="panierSetUnite(${a.id}, 'piece')">pièce</button>
              <button type="button" class="ach-unite-btn ${unite === 'colis' ? 'is-active' : ''}"
                      ${colisOk ? '' : 'disabled'} onclick="panierSetUnite(${a.id}, 'colis')">colis</button>
            </div>
          </div>
          ${puAffiche !== null
            ? `<div class="ach-stepper-hint">${fmtPrix(puAffiche)} €/${uniteLabel(unite)}</div>`
            : `<div class="ach-stepper-hint" style="color:#b45309">conversion impossible</div>`}
          ${qte > 0 && detailReception(a, qte, unite)
            ? `<div class="ach-recep-detail">${detailReception(a, qte, unite)}</div>`
            : ''}
        </td>
        <td class="ach-col-num">${totalLigne !== null
            ? `<strong>${fmtPrix(totalLigne)} €</strong>`
            : '<span style="color:#9ca3af">—</span>'}</td>
      </tr>`;
  }).join('');

  majTotalPanier();
}

function majTotalPanier() {
  let totalHT = 0, totalTTC = 0;
  for (const catId of Object.keys(panier)) {
    const a = catalogueTous.find(x => x.id === parseInt(catId));
    const qte = panierQte(catId);
    if (a && qte) {
      const t = totalLignePanier(a, qte, panierUnite(catId));
      if (t !== null) {
        totalHT += t;
        totalTTC += t * (1 + (parseFloat(a.tva_percent) || 5.5) / 100);
      }
    }
  }
  document.getElementById('panier-total').textContent = fmtPrix(totalHT) + ' €';
  document.getElementById('panier-total-ttc').textContent = fmtPrix(totalTTC) + ' €';
  document.getElementById('panier-nb-articles').textContent = panierNbArticles();
}

// Saisie directe de la quantité (saisie libre)
function panierSetQte(catId, valeur) {
  let qte = parseFloat(valeur);
  if (isNaN(qte) || qte < 0) qte = 0;
  if (qte > 0) {
    panier[catId] = { quantite: qte, unite: panierUnite(catId) };
  } else {
    delete panier[catId];   // l'unité reste mémorisée dans uniteChoisies
  }
  panierSauver();
  afficherCataloguePanier();
}

// Changement de l'unité de commande (kg / pièce / colis) pour une ligne
function panierSetUnite(catId, unite) {
  const a = catalogueTous.find(x => x.id === parseInt(catId));
  if (a && !peutCommander(a, unite)) unite = uniteParDefaut(a); // garde-fou : unité commandable
  uniteChoisies[catId] = unite;                       // mémorise le choix (même sans qté)
  if (panier[catId]) panier[catId].unite = unite;
  panierSauver();
  afficherCataloguePanier();
}

// Bouton de test : ajoute 1 à la quantité de tous les articles visibles
function testPlus1() {
  const tbody = document.getElementById('tbody-panier-catalogue');
  const inputs = tbody.querySelectorAll('input[type="number"]');
  inputs.forEach(input => {
    const catId = parseInt(input.getAttribute('onchange').match(/\d+/)[0]);
    const qteActuelle = panierQte(String(catId));
    const nouvelleQte = qteActuelle + 1;
    panier[catId] = { quantite: nouvelleQte, unite: panierUnite(String(catId)) };
  });
  panierSauver();
  afficherCataloguePanier();
}

// ── Génération des commandes ──────────────────────────────────
async function panierGenerer() {
  const lignes = panierVersLignes();
  if (!lignes.length) {
    alert('Le panier est vide.');
    return;
  }
  const dateLivraison = document.getElementById('panier-livraison').value;
  if (!dateLivraison) {
    alert('Veuillez renseigner une date de livraison souhaitée.');
    document.getElementById('panier-livraison').focus();
    return;
  }

  // Sauvegarde le panier en BDD juste avant génération (l'endpoint /generer lit la BDD)
  const fournIds = [...new Set(lignes.map(l => l.fournisseur_id))];
  const msg = `Générer ${fournIds.length} commande(s) brouillon pour :\n` +
    fournIds.map(id => {
      const f = fournisseurs.find(x => x.id === id);
      const nb = lignes.filter(l => l.fournisseur_id === id).length;
      return `  • ${f ? f.nom : id} (${nb} article(s))`;
    }).join('\n');

  if (!confirm(msg + '\n\nContinuer ?')) return;

  const btn = document.getElementById('btn-panier-generer');
  btn.disabled = true; btn.textContent = 'Génération…';

  try {
    // 1) Pousser le panier courant en BDD
    const rs = await fetch(API_PANIER, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lignes })
    });
    if (!rs.ok) throw new Error('Erreur sauvegarde panier');

    // 2) Générer les commandes
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

    panier = {};
    panierSauver();
    fermerPanier();
    await Promise.all([chargerCommandes(), chargerCatalogueTous()]);

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
    document.getElementById('cmd-alerte-livraison').hidden = true;

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
    // Vérifier les délais si une date est déjà renseignée
    if (cmdCourante.date_livraison_prevue) verifierDelaisCommande();
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
  const totalHT  = lignes.reduce((s, l) => s + (l.montant_ht || 0), 0);
  const totalTTC = lignes.reduce((s, l) => s + (l.montant_ht || 0) * (1 + (parseFloat(l.tva_percent) || 5.5) / 100), 0);
  document.getElementById('cmd-total').textContent     = fmtPrix(totalHT)  + ' €';
  document.getElementById('cmd-total-ttc').textContent = fmtPrix(totalTTC) + ' €';
}

async function sauverCommande() {
  const dateLivraison = document.getElementById('cmd-livraison').value;
  if (!dateLivraison) {
    const z = document.getElementById('cmd-form-erreur');
    z.textContent = 'La date de livraison souhaitée est obligatoire.'; z.hidden = false;
    document.getElementById('cmd-livraison').focus();
    return;
  }
  const btn = document.getElementById('btn-sauver-cmd');
  btn.disabled = true; btn.textContent = 'Enregistrement…';
  const id = document.getElementById('cmd-id').value;
  const body = {
    date_livraison_prevue: dateLivraison,
    // chaîne vide (pas null) pour permettre l'effacement : le backend ignore null
    commentaire:           document.getElementById('cmd-commentaire').value.trim(),
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

function forcerEnvoi() {
  const f = fournisseurs.find(x => x.id === parseInt(document.getElementById('cmd-fournisseur').value));
  const tel = f?.telephone ? formaterTel(f.telephone) : '(numéro non renseigné)';
  if (confirm(`⚠️ Vous forcez l'envoi de la commande hors délai.\n\nN'oubliez pas d'appeler le commercial :\n📞 ${tel}\n\nContinuer ?`)) {
    forcerEnvoiFlag = true;
    envoyerCommande();
  }
}

async function envoyerCommande() {
  const id = document.getElementById('cmd-id').value;
  if (!id) return;

  // Vérifier si les délais sont respectés (sauf si flag forcerEnvoiFlag)
  if (!forcerEnvoiFlag && !document.getElementById('cmd-alerte-livraison').hidden) {
    const f = fournisseurs.find(x => x.id === parseInt(document.getElementById('cmd-fournisseur').value));
    const tel = f?.telephone ? formaterTel(f.telephone) : '(numéro non renseigné)';
    alert(`⚠️ Livraison hors délai pour ce fournisseur.\n\nAppellez le commercial : 📞 ${tel}\n\nVoulez-vous forcer l'envoi malgré tout ?`);
    forcerEnvoiFlag = false;
    return;
  }

  const btn = document.getElementById('btn-envoyer-cmd');
  btn.disabled = true; btn.textContent = 'Envoi…';
  try {
    // Persister le commentaire et la date saisis avant l'envoi : le mail est
    // construit à partir de la BDD, pas du formulaire. Sans ça un commentaire
    // tapé sans cliquer « Enregistrer » serait perdu.
    await fetch(`${API_CMD}/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        date_livraison_prevue: document.getElementById('cmd-livraison').value || null,
        commentaire: document.getElementById('cmd-commentaire').value.trim(),
      }),
    });
    const r = await fetch(`${API_CMD}/${id}/envoyer`, { method: 'POST' });
    const result = await r.json();
    if (!r.ok) {
      alert(`❌ Erreur : ${result.detail || 'Erreur serveur'}`);
      return;
    }
    if (result.envoye) {
      alert(`✅ Commande envoyée à ${result.destinataire}`);
    } else {
      const dest = result.destinataire || '(email non renseigné)';
      alert(`⚠️ SMTP non configuré.\n\nDestinataire : ${dest}\n\n${result.corps || ''}`);
    }
    await chargerCommandes();
    fermerModalCmd();
  } catch(e) {
    alert('Erreur : ' + e.message);
  } finally {
    forcerEnvoiFlag = false;
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
  // Remettre toutes les unités (saisie manuelle sans article catalogue)
  document.getElementById('l-unite').innerHTML =
    '<option value="kg">kg</option><option value="piece">pièce</option><option value="colis">colis</option>';
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

  // Reconstruire les options d'unité selon ce qu'autorise le catalogue
  const uniteLabels = { kg: 'kg', piece: 'pièce', colis: 'colis' };
  const unitesSel = document.getElementById('l-unite');
  const unitesDispo = ['kg', 'piece', 'colis'].filter(u => peutCommander(a, u));
  unitesSel.innerHTML = unitesDispo.length
    ? unitesDispo.map(u => `<option value="${u}">${uniteLabels[u] || u}</option>`).join('')
    : '<option value="kg">kg</option>';
  unitesSel.value = uniteParDefaut(a);

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
    document.getElementById('cmd-form-erreur').hidden = true; // Masquer les erreurs
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
  document.getElementById('cmd-form-erreur').hidden = true; // Masquer les erreurs potentielles
  await chargerCommandes();
}

// ── Vérification contraintes livraison fournisseur ───────────
const JOURS_NOMS = ['dimanche','lundi','mardi','mercredi','jeudi','vendredi','samedi'];

function formaterTel(tel) {
  if (!tel) return '';
  const digits = tel.replace(/\D/g, '');
  return digits.replace(/(\d{2})(?=\d)/g, '$1 ');
}

function verifierDelais(dateStr, fournisseurId, alerteEl) {
  const alerte = document.getElementById(alerteEl);
  if (!dateStr || !fournisseurId) { alerte.hidden = true; return; }

  const f = fournisseurs.find(x => x.id === parseInt(fournisseurId));
  if (!f) { alerte.hidden = true; return; }

  const problemes = [];
  const dateObj = new Date(dateStr + 'T00:00:00');
  const jourNom = JOURS_NOMS[dateObj.getDay()];

  // Vérifier si le jour est autorisé
  if (f.jours_livraison) {
    let jours = [];
    try { jours = JSON.parse(f.jours_livraison); } catch { jours = []; }
    if (jours.length && !jours.includes(jourNom)) {
      const joursStr = jours.map(j => j.charAt(0).toUpperCase() + j.slice(1)).join(', ');
      problemes.push(`⚠️ Le ${jourNom} n'est pas un jour de livraison — jours autorisés : ${joursStr}.`);
    }
  }

  // Vérifier l'heure limite de commande (par rapport à maintenant)
  if (f.heure_limite_commande) {
    const maintenant = new Date();
    const today = maintenant.toISOString().slice(0, 10);
    const diffJours = Math.round((dateObj - new Date(today + 'T00:00:00')) / 86400000);
    if (diffJours <= 1) {
      const [hLim, mLim] = f.heure_limite_commande.split(':').map(Number);
      const limiteMs = hLim * 60 + mLim;
      const maintMs = maintenant.getHours() * 60 + maintenant.getMinutes();
      if (maintMs >= limiteMs) {
        problemes.push(`⚠️ Heure limite de commande dépassée (${f.heure_limite_commande}) — livraison hors délai, appelez le commercial.`);
      }
    }
  }

  if (problemes.length) {
    const telFormate = f.telephone ? formaterTel(f.telephone) : '';
    const btnForcer = alerteEl === 'cmd-alerte-livraison' ? ' <button type="button" class="ach-btn ach-btn--small" style="margin-left:8px;" onclick="forcerEnvoi()">Forcer l\'envoi</button>' : '';
    alerte.innerHTML = problemes.join('<br>') + (telFormate ? `<br><strong>Livraison hors délai — Appeler le commercial : 📞 ${telFormate}${btnForcer}</strong>` : '');
    alerte.hidden = false;
  } else {
    alerte.hidden = true;
  }
}

function verifierDelaisPanier() {
  const date = document.getElementById('panier-livraison').value;
  const lignes = panierVersLignes();
  const fournIds = [...new Set(lignes.map(l => l.fournisseur_id))];
  const alerte = document.getElementById('panier-alerte-livraison');
  if (!date || !fournIds.length) { alerte.hidden = true; return; }

  const problemes = [];
  const dateObj = new Date(date + 'T00:00:00');
  const jourNom = JOURS_NOMS[dateObj.getDay()];
  const today = new Date().toISOString().slice(0, 10);
  const diffJours = Math.round((dateObj - new Date(today + 'T00:00:00')) / 86400000);
  const maintenant = new Date();
  const maintMs = maintenant.getHours() * 60 + maintenant.getMinutes();

  fournIds.forEach(fid => {
    const f = fournisseurs.find(x => x.id === fid);
    if (!f) return;
    const msgs = [];

    if (f.jours_livraison) {
      let jours = [];
      try { jours = JSON.parse(f.jours_livraison); } catch { jours = []; }
      if (jours.length && !jours.includes(jourNom)) {
        const joursStr = jours.map(j => j.charAt(0).toUpperCase() + j.slice(1)).join(', ');
        msgs.push(`Le ${jourNom} n'est pas livré (jours autorisés : ${joursStr})`);
      }
    }
    if (f.heure_limite_commande && diffJours <= 1) {
      const [hLim, mLim] = f.heure_limite_commande.split(':').map(Number);
      if (maintMs >= hLim * 60 + mLim) {
        msgs.push(`Heure limite ${f.heure_limite_commande} dépassée`);
      }
    }
    if (msgs.length) {
      const telFormate = f.telephone ? formaterTel(f.telephone) : '';
      problemes.push(`<strong>${escHtml(f.nom)}</strong> : ${msgs.join(', ')}${telFormate ? ` — 📞 ${telFormate}` : ''}`);
    }
  });

  if (problemes.length) {
    alerte.innerHTML = '⚠️ Livraison hors délai pour certains fournisseurs — Appeler le commercial :<br>' + problemes.join('<br>');
    alerte.hidden = false;
  } else {
    alerte.hidden = true;
  }
}

function verifierDelaisCommande() {
  const date = document.getElementById('cmd-livraison').value;
  const fournId = document.getElementById('cmd-fournisseur').value;
  verifierDelais(date, fournId, 'cmd-alerte-livraison');
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

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

const STATUT_LABELS = {
  brouillon: 'Brouillon', rapprochee: 'Rapprochée', validee: 'Validée', litige: 'En litige',
};

// Une facture validée est VERROUILLÉE (correction = avoir) — le front grise tout.
function estVerrouillee() { return facCourante?.statut === 'validee'; }

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

  // Lignes annexes : boutons d'ajout par type
  document.querySelectorAll('[data-ajout-annexe]').forEach(btn => {
    btn.addEventListener('click', () => ajouterAnnexe(btn.dataset.ajoutAnnexe));
  });

  // Bouclage : totaux lus sur le papier (effaçables → null)
  document.getElementById('fac-papier-ht').addEventListener('change',
    (e) => majPapier('total_ht_papier', e.target));
  document.getElementById('fac-papier-ttc').addEventListener('change',
    (e) => majPapier('total_ttc_papier', e.target));

  // Étape 3 : solder l'écart / créer l'avoir / déverrouiller
  document.getElementById('btn-solder-ecart').addEventListener('click', solderEcart);
  document.getElementById('btn-avoir-fac').addEventListener('click', creerAvoir);
  document.getElementById('btn-deverrouiller-fac').addEventListener('click', deverrouillerFacture);

  // Étape 4 : import Factur-X / OCR
  document.getElementById('fac-import-fichier').addEventListener('change', importerDocument);
  document.getElementById('btn-import-bl').addEventListener('click', importerDepuisBl);
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
        <td>${f.type === 'avoir' ? '<span class="fac-badge-avoir">↩ AVOIR</span> ' : ''}${escHtml(f.numero_facture) || '<em style="color:#9ca3af;">— à saisir —</em>'}</td>
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

  const prefixe = fac.type === 'avoir' ? 'Avoir' : 'Facture';
  document.getElementById('modal-fac-titre').textContent =
    `${prefixe} ${fac.numero_facture || '(brouillon)'} — ${fac.fournisseur_nom || ''}`
    + (fac.statut === 'validee' ? ' 🔒' : '');
  document.getElementById('fac-id').value = fac.id;
  document.getElementById('fac-fournisseur-nom').value = fac.fournisseur_nom || '';
  document.getElementById('fac-numero').value = fac.numero_facture || '';
  document.getElementById('fac-date').value = fac.date_facture || '';
  document.getElementById('fac-commande').value = fac.numero_commande || '(aucune commande rapprochée)';
  document.getElementById('fac-commentaire').value = fac.commentaire || '';
  document.getElementById('fac-form-erreur').hidden = true;

  rendreLignes(fac.lignes || []);
  rendreTotaux(fac);
  chargerSuggestionsAnnexes(fac);
  appliquerVerrou(fac);
  // Import « depuis le BL » : si une réception est rattachée (directement ou via
  // la commande mappée — reception_bl_id résout les deux cas côté serveur).
  document.getElementById('btn-import-bl').hidden = !(fac.reception_bl_id || fac.reception_id);
  document.getElementById('fac-import-resultat').hidden = true;
  document.getElementById('fac-import-etat').textContent = '';
  document.getElementById('modal-facture').hidden = false;
}

// ── Import de facture : Factur-X (fiable) sinon OCR ─────────────
let extractionCourante = null;   // dernière extraction pour l'application

async function importerDocument(e) {
  const fichier = e.target.files && e.target.files[0];
  if (!fichier) return;
  const fd = new FormData();
  fd.append('fichier', fichier);
  await lancerImport(`${API_FAC}/${facCourante.id}/importer-document`, { body: fd });
  e.target.value = '';   // permet de réimporter le même fichier
}

async function importerDepuisBl() {
  await lancerImport(`${API_FAC}/${facCourante.id}/importer-depuis-bl`, { method: 'POST' });
}

async function lancerImport(url, opts) {
  const etat = document.getElementById('fac-import-etat');
  etat.textContent = '⏳ Analyse en cours… (l\'OCR peut prendre 10-20 s)';
  try {
    const r = await fetch(url, { method: opts.method || 'POST', body: opts.body });
    if (!r.ok) {
      // Un 500 renvoie souvent du HTML/texte, pas du JSON : on lit le corps brut
      // pour donner un message utile plutôt qu'un silence.
      let detail = '';
      try { detail = (await r.json()).detail; }
      catch (_) { detail = (await r.text().catch(() => '')).slice(0, 200); }
      if (r.status === 500) {
        detail = 'Erreur serveur (500). Si le module vient d\'être mis à jour, '
          + 'redémarrez le service backend sur le serveur (la base doit se mettre à jour).';
      }
      etat.textContent = '❌ ' + (detail || `Échec (HTTP ${r.status}).`);
      return;
    }
    extractionCourante = await r.json();
    const src = extractionCourante.source === 'facturx'
      ? '✓ Facture électronique (Factur-X) — données fiables'
      : '✓ Lecture OCR — vérifiez les montants';
    etat.textContent = src;
    rendreExtraction(extractionCourante);
  } catch (err) {
    etat.textContent = '❌ Erreur réseau pendant l\'analyse : ' + (err.message || err);
  }
}

function rendreExtraction(data) {
  const zone = document.getElementById('fac-import-resultat');
  const lignes = data.lignes || [];
  const annexes = data.annexes || [];
  const ligneHtml = (l, i, type) => `
    <tr>
      <td><input type="checkbox" class="imp-check" data-type="${type}" data-i="${i}" checked></td>
      <td>${escHtml(l.designation)}</td>
      <td class="ach-col-num">${l.quantite != null ? l.quantite : (l.poids_facture_kg ?? '—')}</td>
      <td class="ach-col-num">${l.prix_unitaire != null ? fmtPrix(l.prix_unitaire) : '—'}</td>
      <td>${escHtml(l.unite_prix || (type === 'annexe' ? l.type_ligne : ''))}</td>
      <td class="ach-col-num">${l.montant_ht != null ? fmtPrix(l.montant_ht) + ' €' : '—'}</td>
      <td class="ach-col-num">${l.tva_pct != null ? fmtPrix(l.tva_pct) + ' %' : '—'}</td>
    </tr>`;

  zone.innerHTML = `
    <div class="fac-import-entete">
      <span>Fournisseur : <strong>${escHtml(data.fournisseur) || '—'}</strong></span>
      <span>N° : <strong>${escHtml(data.numero_facture) || '—'}</strong></span>
      <span>Date : <strong>${escHtml(data.date_facture) || '—'}</strong></span>
      ${data.type_document === 'avoir' ? '<span class="fac-badge-avoir">↩ AVOIR</span>' : ''}
      <span>Total TTC : <strong>${data.total_ttc != null ? fmtPrix(data.total_ttc) + ' €' : '—'}</strong></span>
    </div>
    <table class="ach-table fac-table">
      <thead><tr><th>✓</th><th>Désignation</th><th class="ach-col-num">Qté</th>
        <th class="ach-col-num">P.U.</th><th>Unité / type</th>
        <th class="ach-col-num">Montant HT</th><th class="ach-col-num">TVA</th></tr></thead>
      <tbody>
        ${lignes.map((l, i) => ligneHtml(l, i, 'marchandise')).join('')}
        ${annexes.map((l, i) => ligneHtml(l, i, 'annexe')).join('')}
      </tbody>
    </table>
    <div class="fac-import-actions">
      <label class="fac-import-opt">
        <input type="checkbox" id="imp-remplacer" checked>
        Remplacer les lignes actuelles de la facture
      </label>
      <button type="button" class="ach-btn ach-btn--primary" id="btn-appliquer-import">
        Appliquer les lignes cochées
      </button>
    </div>`;
  zone.hidden = false;
  document.getElementById('btn-appliquer-import').addEventListener('click', appliquerImport);
}

async function appliquerImport() {
  const data = extractionCourante;
  if (!data) return;
  const coche = (type, i) => document.querySelector(
    `.imp-check[data-type="${type}"][data-i="${i}"]`)?.checked;

  const lignes = [];
  (data.lignes || []).forEach((l, i) => {
    if (!coche('marchandise', i)) return;
    // Marchandise : au kg → poids_facture_kg ; sinon quantité facturée.
    const auKg = (l.unite_prix || 'kg') === 'kg';
    lignes.push({
      designation: l.designation,
      code_article: l.code_article || null,
      type_ligne: 'marchandise',
      unite_prix: l.unite_prix || 'kg',
      tva_pct: l.tva_pct,
      poids_facture_kg: auKg ? (l.quantite ?? l.poids_facture_kg ?? null) : null,
      quantite_facturee: auKg ? null : (l.quantite ?? null),
      prix_facture_ht: l.prix_unitaire ?? null,
      montant_facture_ht: l.prix_unitaire == null ? (l.montant_ht ?? null) : null,
    });
  });
  (data.annexes || []).forEach((l, i) => {
    if (!coche('annexe', i)) return;
    lignes.push({
      designation: l.designation,
      type_ligne: l.type_ligne || 'taxe',
      tva_pct: l.tva_pct,
      montant_facture_ht: l.montant_ht ?? 0,
    });
  });

  const body = {
    numero_facture: data.numero_facture || null,
    date_facture: data.date_facture || null,
    type_document: data.type_document || null,
    total_ht_papier: data.total_ht ?? null,
    total_ttc_papier: data.total_ttc ?? null,
    remplacer_lignes: document.getElementById('imp-remplacer').checked,
    lignes,
  };
  const r = await fetch(`${API_FAC}/${facCourante.id}/appliquer-import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    alert(err.detail || 'Échec de l\'application.');
    return;
  }
  facCourante = await r.json();
  document.getElementById('fac-import-resultat').hidden = true;
  document.getElementById('fac-import-etat').textContent = '✓ Import appliqué';
  extractionCourante = null;
  // Rafraîchit l'écran + les champs entête
  document.getElementById('fac-numero').value = facCourante.numero_facture || '';
  document.getElementById('fac-date').value = facCourante.date_facture || '';
  rendreLignes(facCourante.lignes || []);
  rendreTotaux(facCourante);
  appliquerVerrou(facCourante);
  await chargerFactures();
}

// Verrouillage visuel : facture validée = tout en lecture seule sauf le commentaire.
function appliquerVerrou(fac) {
  const verrou = fac.statut === 'validee';
  document.getElementById('fac-numero').disabled = verrou;
  document.getElementById('fac-date').disabled = verrou;
  document.getElementById('fac-papier-ht').disabled = verrou;
  document.getElementById('fac-papier-ttc').disabled = verrou;
  document.querySelectorAll('#tbody-lignes-facture input, #tbody-lignes-facture select, ' +
    '#tbody-lignes-facture button, #tbody-annexes-facture input, ' +
    '#tbody-annexes-facture select, #tbody-annexes-facture button')
    .forEach(el => { el.disabled = verrou; });
  document.querySelectorAll('[data-ajout-annexe]').forEach(b => { b.hidden = verrou; });
  document.getElementById('fac-annexes-suggestions').hidden = verrou;
  document.getElementById('btn-sauver-fac').hidden = verrou;
  document.getElementById('btn-valider-fac').hidden = verrou;
  document.getElementById('btn-supprimer-fac').hidden = verrou;
  document.getElementById('btn-deverrouiller-fac').hidden = !verrou;
  // Avoir : proposé si la facture (pas un avoir) a des litiges
  const aLitiges = (fac.lignes || []).some(l => l.statut_ligne === 'litige');
  document.getElementById('btn-avoir-fac').hidden = !(fac.type !== 'avoir' && aLitiges);
}

async function deverrouillerFacture() {
  if (!confirm('Déverrouiller cette facture validée ?\nElle redeviendra modifiable — '
    + 'à réserver aux erreurs de saisie (sinon, passer par un avoir).')) return;
  const r = await fetch(`${API_FAC}/${facCourante.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ statut: 'brouillon' }),
  });
  if (!r.ok) { alert('Échec du déverrouillage.'); return; }
  await chargerFactures();
  ouvrirFacture(facCourante.id);
}

async function solderEcart() {
  const r = await fetch(`${API_FAC}/${facCourante.id}/solder-ecart`, { method: 'POST' });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    alert(err.detail || 'Impossible de solder l\'écart.');
    return;
  }
  await rafraichirFacture();
  appliquerVerrou(facCourante);
}

async function creerAvoir() {
  const r = await fetch(`${API_FAC}/${facCourante.id}/avoir-depuis-litiges`, { method: 'POST' });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    alert(err.detail || 'Impossible de créer l\'avoir.');
    return;
  }
  const avoir = await r.json();
  await chargerFactures();
  ouvrirFacture(avoir.id, avoir);   // ouvre directement l'avoir pré-rempli
}

function rendreLignes(lignes) {
  const marchandises = lignes.filter(l => (l.type_ligne || 'marchandise') === 'marchandise');
  rendreAnnexes(lignes.filter(l => (l.type_ligne || 'marchandise') !== 'marchandise'));

  const tbody = document.getElementById('tbody-lignes-facture');
  if (!marchandises.length) {
    tbody.innerHTML = '<tr><td colspan="10" class="ach-vide">Aucune ligne.</td></tr>';
    return;
  }
  tbody.innerHTML = marchandises.map(l => {
    const ecart = l.ecart_montant_ht ?? 0;
    const enLitige = l.statut_ligne === 'litige';
    // Unité du PRIX : pour colis/pièce le montant = quantité × prix (le poids reste
    // affiché à titre HACCP) ; pour le kg, le montant = poids × prix.
    const auQuantite = l.unite_prix === 'colis' || l.unite_prix === 'piece';
    const unite = libelleUnite(l.unite_prix);
    return `
      <tr data-lid="${l.id}" class="${enLitige ? 'fac-ligne--litige' : ''}">
        <td>${escHtml(l.designation)}
          <div class="fac-choix-meta">${l.code_article ? escHtml(l.code_article) + ' · ' : ''}prix ${auQuantite ? 'au ' + unite : 'au kg'}</div>
        </td>
        <td class="ach-col-num">${l.poids_recu_kg != null ? fmtPrix(l.poids_recu_kg) : '—'}</td>
        <td class="ach-col-num">
          <input type="number" step="0.001" min="0" class="fac-input" data-champ="poids_facture_kg"
                 value="${l.poids_facture_kg != null ? l.poids_facture_kg : ''}"
                 ${auQuantite ? 'title="Poids indicatif (HACCP) — le montant de cette ligne se calcule quantité × prix"' : ''}>
        </td>
        <td class="ach-col-num">
          ${auQuantite ? `
          <input type="number" step="1" min="0" class="fac-input" data-champ="quantite_facturee"
                 value="${l.quantite_facturee != null ? l.quantite_facturee : ''}"
                 title="Quantité facturée (${unite}) — montant = quantité × prix">` : '—'}
        </td>
        <td class="ach-col-num">${l.prix_commande_ht != null ? fmtPrix(l.prix_commande_ht) + ' €' : '—'}</td>
        <td class="ach-col-num">
          <input type="number" step="0.01" min="0" class="fac-input" data-champ="prix_facture_ht"
                 value="${l.prix_facture_ht != null ? arrondiAffichagePrix(l.prix_facture_ht) : ''}"
                 title="Prix facturé HT (€/${unite})">
        </td>
        <td class="ach-col-num">
          <input type="number" step="0.01" min="0" class="fac-input" data-champ="montant_facture_ht"
                 value="${l.montant_facture_ht != null ? l.montant_facture_ht : ''}"
                 title="Montant HT de la ligne tel que facturé — saisie directe possible">
        </td>
        <td class="ach-col-num">${selectTva(l.tva_pct)}</td>
        <td class="ach-col-num fac-ecart ${classeEcart(ecart)}">${signe(ecart)}${fmtPrix(Math.abs(ecart))} €</td>
        <td style="text-align:center;">
          <button class="fac-btn-litige ${enLitige ? 'actif' : ''}" data-litige="${l.id}"
                  title="${enLitige ? (l.commentaire_litige || 'En litige') : 'Marquer en litige'}">
            ${enLitige ? '⚠' : '○'}
          </button>
        </td>
      </tr>`;
  }).join('');

  brancherSaisieLignes(tbody);
  tbody.querySelectorAll('[data-litige]').forEach(btn => {
    btn.addEventListener('click', () => basculerLitige(btn.dataset.litige));
  });
}

// ── Lignes annexes (transport, taxe, consigne, remise, ajustement) ──
const TYPE_ANNEXE_LABELS = {
  transport: '🚚 Transport', taxe: '🏛 Taxe', consigne: '📦 Consigne',
  remise: '➖ Remise', ajustement: '🔧 Ajustement',
};

function rendreAnnexes(annexes) {
  const tbody = document.getElementById('tbody-annexes-facture');
  if (!annexes.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="ach-vide">Aucun frais annexe — ajoutez transport, taxe, consigne ou remise si la facture en comporte.</td></tr>';
    return;
  }
  tbody.innerHTML = annexes.map(l => `
    <tr data-lid="${l.id}">
      <td>${TYPE_ANNEXE_LABELS[l.type_ligne] || escHtml(l.type_ligne)}</td>
      <td>
        <input type="text" class="fac-input fac-input--texte" data-champ="designation"
               value="${escHtml(l.designation)}">
      </td>
      <td class="ach-col-num">
        <input type="number" step="0.01" class="fac-input" data-champ="montant_facture_ht"
               value="${l.montant_facture_ht != null ? l.montant_facture_ht : ''}"
               title="Montant HT — négatif pour une remise">
      </td>
      <td class="ach-col-num">${selectTva(l.tva_pct)}</td>
      <td style="text-align:center;">
        <button class="fac-btn-litige" data-suppr-annexe="${l.id}" title="Supprimer la ligne">🗑</button>
      </td>
    </tr>`).join('');

  brancherSaisieLignes(tbody);
  tbody.querySelectorAll('[data-suppr-annexe]').forEach(btn => {
    btn.addEventListener('click', () => supprimerAnnexe(btn.dataset.supprAnnexe));
  });
}

function selectTva(valeur) {
  const taux = [0, 2.1, 5.5, 10, 20];
  const opts = taux.map(t =>
    `<option value="${t}" ${valeur === t ? 'selected' : ''}>${String(t).replace('.', ',')} %</option>`
  ).join('');
  return `<select class="fac-select" data-champ="tva_pct" title="Taux de TVA de la ligne">
    <option value="" ${valeur == null ? 'selected' : ''}>—</option>${opts}</select>`;
}

function brancherSaisieLignes(tbody) {
  // Saisie inline : recalcul serveur au change (Enter = blur)
  tbody.querySelectorAll('input.fac-input, select.fac-select').forEach(inp => {
    inp.addEventListener('change', () => majLigne(inp));
    inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') inp.blur(); });
  });
}

async function ajouterAnnexe(type, prefill) {
  const defauts = {
    transport: { designation: 'Frais de transport', tva_pct: 20 },
    taxe:      { designation: 'Taxe', tva_pct: 20 },
    consigne:  { designation: 'Consigne', tva_pct: 20 },
    remise:    { designation: 'Remise', tva_pct: 5.5 },
    ajustement:{ designation: 'Ajustement', tva_pct: 5.5 },
  };
  const base = defauts[type] || { designation: 'Ligne', tva_pct: 20 };
  const body = {
    designation: prefill?.designation ?? base.designation,
    type_ligne: type,
    montant_facture_ht: prefill?.montant_facture_ht ?? 0,
    tva_pct: prefill?.tva_pct ?? base.tva_pct,
  };
  const r = await fetch(`${API_FAC}/${facCourante.id}/lignes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) { alert('Impossible d\'ajouter la ligne.'); return; }
  await rafraichirFacture();
}

async function supprimerAnnexe(ligneId) {
  const r = await fetch(`${API_FAC}/${facCourante.id}/lignes/${ligneId}`, { method: 'DELETE' });
  if (!r.ok) { alert('Échec de la suppression.'); return; }
  await rafraichirFacture();
}

// Annexes habituelles du fournisseur (mémoire des factures passées) → chips cliquables.
async function chargerSuggestionsAnnexes(fac) {
  const zone = document.getElementById('fac-annexes-suggestions');
  zone.innerHTML = '';
  if (!fac.fournisseur_id) return;
  try {
    const sugg = await fetch(`${API_FAC}/annexes-frequentes?fournisseur_id=${fac.fournisseur_id}`)
      .then(r => r.ok ? r.json() : []);
    const dejaLa = new Set((fac.lignes || [])
      .filter(l => l.type_ligne !== 'marchandise')
      .map(l => `${l.type_ligne}|${(l.designation || '').toLowerCase()}`));
    const utiles = sugg.filter(s => !dejaLa.has(`${s.type_ligne}|${(s.designation || '').toLowerCase()}`));
    if (!utiles.length) return;
    zone.innerHTML = 'Habituels chez ce fournisseur : ' + utiles.map((s, i) =>
      `<button type="button" class="fac-chip" data-sugg="${i}">
         ${escHtml(s.designation)} · ${fmtPrix(s.dernier_montant_ht)} €
       </button>`).join(' ');
    zone.querySelectorAll('[data-sugg]').forEach(btn => {
      const s = utiles[parseInt(btn.dataset.sugg, 10)];
      btn.addEventListener('click', () => ajouterAnnexe(s.type_ligne, {
        designation: s.designation,
        montant_facture_ht: s.dernier_montant_ht,
        tva_pct: s.tva_pct,
      }));
    });
  } catch (_) { /* suggestions = confort, jamais bloquant */ }
}

async function rafraichirFacture() {
  facCourante = await fetch(`${API_FAC}/${facCourante.id}`).then(x => x.json());
  rendreLignes(facCourante.lignes || []);
  rendreTotaux(facCourante);
  chargerSuggestionsAnnexes(facCourante);
  appliquerVerrou(facCourante);
}

async function majLigne(input) {
  const tr = input.closest('tr');
  const ligneId = tr.dataset.lid;
  const champ = input.dataset.champ;
  const val = input.value === ''
    ? null
    : (champ === 'designation' ? input.value : parseFloat(input.value));

  const r = await fetch(`${API_FAC}/${facCourante.id}/lignes/${ligneId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ [champ]: val }),
  });
  if (!r.ok) { alert('Échec de la mise à jour.'); return; }
  // Recharger la facture pour rafraîchir écarts + totaux (source de vérité = serveur)
  await rafraichirFacture();
}

// ── Bouclage : totaux papier ─────────────────────────────────
async function majPapier(champ, input) {
  const val = input.value === '' ? null : parseFloat(input.value);
  const r = await fetch(`${API_FAC}/${facCourante.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ [champ]: val }),
  });
  if (!r.ok) { alert('Échec de l\'enregistrement du total papier.'); return; }
  facCourante = await r.json();
  rendreTotaux(facCourante);
  appliquerVerrou(facCourante);   // le statut a pu basculer brouillon ⇄ rapprochée
}

function rendreTotaux(fac) {
  document.getElementById('fac-total-attendu').textContent = fmtPrix(fac.montant_total_ht_attendu) + ' €';
  document.getElementById('fac-total-facture').textContent = fmtPrix(fac.montant_total_ht_facture) + ' €';
  const ecart = fac.ecart_total_ht ?? 0;
  const span = document.getElementById('fac-total-ecart');
  span.textContent = signe(ecart, SEUIL_ECART_TOTAL) + fmtPrix(Math.abs(ecart)) + ' €';
  const bar = span.closest('.ach-total-bar');
  bar.classList.remove('fac-total-ecart--haut', 'fac-total-ecart--bas', 'fac-total-ecart--nul');
  bar.classList.add(`fac-total-ecart--${niveauEcart(ecart, SEUIL_ECART_TOTAL)}`);

  // Récapitulatif de bouclage (marchandise/annexes, TVA par taux, TTC, reste à expliquer)
  const rec = fac.recap || {};
  document.getElementById('fac-recap-marchandise').textContent = fmtPrix(rec.marchandise_ht) + ' €';
  document.getElementById('fac-recap-annexes').textContent = fmtPrix(rec.annexes_ht) + ' €';
  document.getElementById('fac-recap-ttc').textContent = fmtPrix(rec.total_ttc_calcule) + ' €';
  const detTva = (rec.tva_par_taux || [])
    .map(t => `${String(t.taux).replace('.', ',')} % → ${fmtPrix(t.tva)} €`).join(' · ');
  document.getElementById('fac-recap-tva').textContent =
    'TVA : ' + (detTva || '—') + (rec.nb_lignes_sans_tva ? ` (${rec.nb_lignes_sans_tva} ligne(s) sans taux)` : '');

  // Inputs papier : reflète l'état serveur sans écraser une saisie en cours
  const inpHt = document.getElementById('fac-papier-ht');
  const inpTtc = document.getElementById('fac-papier-ttc');
  if (document.activeElement !== inpHt) inpHt.value = rec.total_ht_papier ?? '';
  if (document.activeElement !== inpTtc) inpTtc.value = rec.total_ttc_papier ?? '';

  const zone = document.getElementById('fac-reste');
  zone.classList.remove('fac-reste--ok', 'fac-reste--ko');
  const resteTtc = rec.reste_a_expliquer_ttc;
  const resteHt = rec.reste_a_expliquer_ht;
  if (resteTtc == null && resteHt == null) {
    zone.textContent = 'Saisir le total du papier pour vérifier le bouclage';
  } else if (rec.boucle) {
    zone.textContent = '✓ La facture boucle';
    zone.classList.add('fac-reste--ok');
  } else {
    const parties = [];
    if (resteTtc != null) parties.push(`${signe(resteTtc, 0.005) || ''}${fmtPrix(Math.abs(resteTtc))} € TTC`);
    if (resteHt != null) parties.push(`${signe(resteHt, 0.005) || ''}${fmtPrix(Math.abs(resteHt))} € HT`);
    zone.textContent = `Reste à expliquer : ${parties.join(' · ')}`;
    zone.classList.add('fac-reste--ko');
  }

  // « Solder l'écart » : correction rapide, seulement quand il y a un reste HT
  // significatif à poser (total HT papier saisi) et que la facture est modifiable.
  document.getElementById('btn-solder-ecart').hidden = !(
    rec.total_ht_papier != null
    && resteHt != null && Math.abs(resteHt) > SEUIL_ECART_TOTAL
    && fac.statut !== 'validee'
  );
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
  await rafraichirFacture();
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
// Tolérance de rapprochement : sous ces seuils, l'écart est du bruit d'arrondi
// (le fournisseur arrondit chaque ligne au centime) → affiché neutre, pas rouge.
const SEUIL_ECART_LIGNE = 0.02;
const SEUIL_ECART_TOTAL = 0.05;

function fmtPrix(v) { return (v ?? 0).toFixed(2).replace('.', ','); }
function libelleUnite(u) { return u === 'colis' ? 'colis' : (u === 'piece' ? 'pièce' : 'kg'); }
// Les prix unitaires peuvent avoir 3-4 décimales (ex. 12,456 €/kg) : on n'affiche
// dans l'input que 4 décimales max, sans zéros inutiles (12.5 reste 12.5).
function arrondiAffichagePrix(v) { return Math.round(v * 10000) / 10000; }
function signe(v, seuil = SEUIL_ECART_LIGNE) { return v > seuil ? '+' : (v < -seuil ? '−' : ''); }
function niveauEcart(v, seuil = SEUIL_ECART_LIGNE) { return v > seuil ? 'haut' : (v < -seuil ? 'bas' : 'nul'); }
function classeEcart(v) { return 'fac-ecart--' + niveauEcart(v); }
function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

'use strict';
/* ============================================================
   inventaire-valorise.js — Inventaire VALORISÉ (stock comptable €)
   UX chambre froide / Surface Go : recherche + familles, saisie
   au choix kg/pièce/colis, prix €/kg figé, total live.
   ============================================================ */

const $ = (id) => document.getElementById(id);

const fmtEur = (v) => (v == null)
  ? '—'
  : new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(v);
const fmtKg = (v) => (v == null) ? '—' : `${(+v).toLocaleString('fr-FR', { maximumFractionDigits: 3 })} kg`;

// ── API (fetch direct, comme catalogue-achats) ───────────────
const api = {
  async get(url) {
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  },
  async send(method, url, body) {
    const opt = { method, headers: {} };
    if (body !== undefined) {
      opt.headers['Content-Type'] = 'application/json';
      opt.body = JSON.stringify(body);
    }
    const r = await fetch(url, opt);
    if (!r.ok) {
      let msg = `HTTP ${r.status}`;
      try { const j = await r.json(); if (j.detail) msg = j.detail; } catch (_) {}
      throw new Error(msg);
    }
    return r.status === 204 ? null : r.json();
  },
  post(url, body) { return this.send('POST', url, body); },
  put(url, body) { return this.send('PUT', url, body); },
  del(url) { return this.send('DELETE', url); },
};

// ── État ─────────────────────────────────────────────────────
const state = {
  session: null,        // { id, libelle, date_inventaire, statut }
  lignes: [],
  total: 0,
  familles: [],
  familleActive: null,
  sousFamilleActive: null,
  fournisseurs: [],
  fournisseurActif: null,   // id fournisseur, ou null = tous
  badgeActif: null,         // 'reference' | 'habituel' | 'recu' | null
  // article en cours de saisie dans la modale
  article: null,
  unite: 'kg',
};

// ── Toast ────────────────────────────────────────────────────
let _toastTimer = null;
function toast(msg, type = '') {
  const el = $('invv-toast');
  el.textContent = msg;
  el.className = 'invv-toast' + (type ? ` invv-toast--${type}` : '');
  el.hidden = false;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { el.hidden = true; }, 2600);
}

// ════════════════════════════════════════════════════════════
//  Écran 1 : sessions
// ════════════════════════════════════════════════════════════

function montrerEcran(nom) {
  $('invv-ecran-sessions').hidden = (nom !== 'sessions');
  $('invv-ecran-saisie').hidden = (nom !== 'saisie');
}

async function chargerSessions() {
  const liste = $('invv-sessions-liste');
  liste.innerHTML = '<div class="invv-vide">Chargement…</div>';
  try {
    const d = await api.get('/api/inventaire/sessions?limit=50');
    const sessions = d.sessions || [];
    if (!sessions.length) {
      liste.innerHTML = '<div class="invv-vide">Aucun inventaire. Créez-en un pour démarrer.</div>';
      return;
    }
    liste.innerHTML = '';
    for (const s of sessions) {
      const card = document.createElement('div');
      card.className = 'invv-session-card';
      const date = new Date(s.date_inventaire).toLocaleDateString('fr-FR',
        { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' });
      const cloture = s.statut === 'cloture';
      card.innerHTML = `
        <div class="invv-session-card-main">
          <span class="invv-session-card-titre">${esc(s.libelle || 'Inventaire')}</span>
          <span class="invv-session-card-sub">${date} · ${s.nb_lignes} article(s)${cloture ? ' · clôturé' : ' · en cours'}</span>
        </div>
        <span class="invv-session-card-val">${cloture ? fmtEur(s.valeur_totale_ht) : '…'}</span>
        ${cloture ? '' : `<button type="button" class="invv-session-card-del" data-del="${s.id}" aria-label="Supprimer">🗑️</button>`}
      `;
      card.querySelector('.invv-session-card-main').onclick = () => ouvrirSession(s.id);
      card.querySelector('.invv-session-card-val').onclick = () => ouvrirSession(s.id);
      const del = card.querySelector('[data-del]');
      if (del) del.onclick = (e) => { e.stopPropagation(); supprimerSession(s.id); };
      liste.appendChild(card);
    }
  } catch (e) {
    liste.innerHTML = `<div class="invv-vide">Erreur : ${esc(e.message)}</div>`;
  }
}

async function nouvelInventaire() {
  const libelle = prompt('Libellé de l\'inventaire :',
    'Inventaire ' + new Date().toLocaleDateString('fr-FR'));
  if (libelle === null) return;
  try {
    const r = await api.post('/api/inventaire/sessions', { libelle: libelle.trim() || null });
    await ouvrirSession(r.id);
  } catch (e) {
    toast('Création impossible : ' + e.message, 'err');
  }
}

async function supprimerSession(id) {
  if (!confirm('Supprimer cet inventaire et toutes ses lignes ?')) return;
  try {
    await api.del(`/api/inventaire/sessions/${id}`);
    chargerSessions();
  } catch (e) {
    toast('Suppression impossible : ' + e.message, 'err');
  }
}

// ════════════════════════════════════════════════════════════
//  Écran 2 : saisie
// ════════════════════════════════════════════════════════════

async function ouvrirSession(id) {
  try {
    const d = await api.get(`/api/inventaire/sessions/${id}`);
    state.session = d.inventaire;
    state.lignes = d.lignes;
    state.total = d.total_ht;
    rendreBandeau();
    rendreLignes();
    rendreTotal(d.nb_non_valorisees);
    montrerEcran('saisie');
    if (!state.familles.length) await chargerFamilles();
    rendreFamilles();
    if (!state.fournisseurs.length) await chargerFournisseurs();
    // Réinitialise la recherche et les filtres
    $('invv-search').value = '';
    state.badgeActif = null;
    state.fournisseurActif = null;
    rendreFiltresBadges();
    rendreFournisseurs();
    $('invv-articles').innerHTML = '';
  } catch (e) {
    toast('Ouverture impossible : ' + e.message, 'err');
  }
}

function estCloture() { return state.session && state.session.statut === 'cloture'; }

function rendreBandeau() {
  const s = state.session;
  $('invv-session-libelle').textContent = s.libelle || 'Inventaire';
  $('invv-session-date').textContent = new Date(s.date_inventaire)
    .toLocaleDateString('fr-FR', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' });
  const badge = $('invv-session-statut');
  if (estCloture()) {
    badge.textContent = '🔒 clôturé';
    badge.className = 'invv-badge invv-badge--cloture';
    $('invv-btn-cloturer').hidden = true;
  } else {
    badge.textContent = 'en cours';
    badge.className = 'invv-badge';
    $('invv-btn-cloturer').hidden = false;
  }
  // Verrouillage visuel de la saisie quand l'inventaire est clôturé.
  const verrou = estCloture();
  document.querySelector('.invv-search-zone').style.display = verrou ? 'none' : '';
  const zf = document.querySelector('.invv-filtres');
  if (zf) zf.style.display = verrou ? 'none' : '';
  $('invv-familles').style.display = verrou ? 'none' : '';
  $('invv-sous-familles').style.display = verrou ? 'none' : '';
  $('invv-articles').style.display = verrou ? 'none' : '';
  $('invv-btn-cloturer').disabled = verrou;
}

// ── Familles ──
async function chargerFamilles() {
  try {
    const d = await api.get('/api/inventaire/familles');
    state.familles = d.familles || [];
  } catch (_) { state.familles = []; }
}

// ── Fournisseurs (filtre) ──
async function chargerFournisseurs() {
  try {
    const d = await api.get('/api/inventaire/fournisseurs');
    state.fournisseurs = d.fournisseurs || [];
  } catch (_) { state.fournisseurs = []; }
  rendreFournisseurs();
}

function rendreFournisseurs() {
  const sel = $('invv-filtre-fournisseur');
  if (!sel) return;
  sel.innerHTML = '<option value="">Tous fournisseurs</option>';
  for (const f of state.fournisseurs) {
    const o = document.createElement('option');
    o.value = f.id;
    o.textContent = `${f.nom} (${f.nb})`;
    sel.appendChild(o);
  }
  sel.value = state.fournisseurActif || '';
}

function rendreFiltresBadges() {
  document.querySelectorAll('.invv-filtre-badge').forEach((btn) => {
    btn.setAttribute('aria-pressed', String(state.badgeActif === btn.dataset.badge));
  });
}

function rendreFamilles() {
  const box = $('invv-familles');
  box.innerHTML = '';
  for (const f of state.familles) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'invv-fam-btn';
    b.setAttribute('aria-pressed', String(state.familleActive === f.famille));
    b.innerHTML = `${esc(f.famille)} <span class="invv-fam-nb">${f.nb}</span>`;
    b.onclick = () => toggleFamille(f);
    box.appendChild(b);
  }
  rendreSousFamilles();
}

function toggleFamille(f) {
  if (state.familleActive === f.famille) {
    state.familleActive = null;
    state.sousFamilleActive = null;
  } else {
    state.familleActive = f.famille;
    state.sousFamilleActive = null;
  }
  rendreFamilles();
  lancerRecherche();
}

function rendreSousFamilles() {
  const box = $('invv-sous-familles');
  const fam = state.familles.find((f) => f.famille === state.familleActive);
  if (!fam || !fam.sous_familles.length) { box.hidden = true; box.innerHTML = ''; return; }
  box.hidden = false;
  box.innerHTML = '';
  for (const sf of fam.sous_familles) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'invv-fam-btn';
    b.setAttribute('aria-pressed', String(state.sousFamilleActive === sf.nom));
    b.innerHTML = `${esc(sf.nom)} <span class="invv-fam-nb">${sf.nb}</span>`;
    b.onclick = () => {
      state.sousFamilleActive = (state.sousFamilleActive === sf.nom) ? null : sf.nom;
      rendreSousFamilles();
      lancerRecherche();
    };
    box.appendChild(b);
  }
}

// ── Recherche articles ──
let _searchTimer = null;
function lancerRecherche() {
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(rechercherArticles, 180);
}

async function rechercherArticles() {
  const q = $('invv-search').value.trim();
  $('invv-search-clear').hidden = !q;
  // On n'affiche rien tant qu'aucun critère (évite de tout charger d'un coup).
  // Un filtre seul (badge, fournisseur, famille) suffit désormais à lister.
  const aCritere = q || state.familleActive || state.badgeActif || state.fournisseurActif;
  if (!aCritere) { $('invv-articles').innerHTML = ''; return; }
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (state.familleActive) params.set('famille', state.familleActive);
  if (state.sousFamilleActive) params.set('sous_famille', state.sousFamilleActive);
  if (state.fournisseurActif) params.set('fournisseur_id', state.fournisseurActif);
  if (state.badgeActif) params.set('badge', state.badgeActif);
  try {
    const d = await api.get('/api/inventaire/catalogue-recherche?' + params.toString());
    rendreArticles(d.articles || []);
  } catch (e) {
    $('invv-articles').innerHTML = `<div class="invv-vide">Erreur : ${esc(e.message)}</div>`;
  }
}

function rendreArticles(articles) {
  const box = $('invv-articles');
  box.innerHTML = '';
  if (!articles.length) {
    box.innerHTML = '<div class="invv-vide">Aucun article.</div>';
    return;
  }
  for (const a of articles) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'invv-article-btn';
    const prix = (a.prix_kg != null)
      ? `<span class="invv-article-prix">${fmtEur(a.prix_kg)}/kg</span>`
      : `<span class="invv-article-prix invv-article-prix--na">€/kg n/d</span>`;
    let badges = '';
    if (a.recu_recemment) badges += '<span class="invv-pastille invv-pastille--recu" title="Reçu récemment">📦</span>';
    if (a.est_habituel) badges += '<span class="invv-pastille invv-pastille--habituel" title="Commandé habituellement">🔁</span>';
    if (a.est_reference) badges += '<span class="invv-pastille invv-pastille--ref" title="Référencé (comparateur)">⭐</span>';
    b.innerHTML = `
      <span class="invv-article-main">
        <span class="invv-article-nom">${esc(a.designation)}${badges ? ' <span class="invv-pastilles">' + badges + '</span>' : ''}</span>
        <span class="invv-article-sub">${esc(a.fournisseur_nom || '')}${a.code_article ? ' · ' + esc(a.code_article) : ''}</span>
      </span>
      ${prix}`;
    b.onclick = () => ouvrirModaleQte(a);
    box.appendChild(b);
  }
}

// ════════════════════════════════════════════════════════════
//  Modale quantité
// ════════════════════════════════════════════════════════════

function ouvrirModaleQte(article) {
  if (estCloture()) return;
  state.article = article;
  state.unite = 'kg';
  $('invv-modal-nom').textContent = article.designation;
  const pk = $('invv-modal-prixkg');
  if (article.prix_kg != null) {
    pk.textContent = `${fmtEur(article.prix_kg)} / kg`;
    pk.className = 'invv-modal-prixkg';
  } else {
    pk.textContent = '€/kg indisponible — la valeur ne pourra pas être calculée';
    pk.className = 'invv-modal-prixkg invv-modal-prixkg--na';
  }
  $('invv-modal-qte-input').value = '';
  $('invv-modal-poids-input').value = '';
  // Replie l'éditeur de prix et masque le bouton ✏️ si l'article n'est pas modifiable au €/kg.
  $('invv-modal-prix-editor').hidden = true;
  $('invv-modal-prix-edit').hidden = !prixKgModifiable(article);
  majToggleUnite();
  majPoidsPieceVisible();
  majApercu();
  $('invv-modal-qte').hidden = false;
  setTimeout(() => $('invv-modal-qte-input').focus(), 60);
}

function fermerModale() {
  $('invv-modal-qte').hidden = true;
  state.article = null;
}

function majToggleUnite() {
  document.querySelectorAll('.invv-unite-btn').forEach((btn) => {
    btn.setAttribute('aria-pressed', String(btn.dataset.unite === state.unite));
  });
}

// Poids unitaire dérivable du catalogue ? (poids_unitaire_kg, ou colis/qte)
function poidsPieceConnu() {
  const a = state.article;
  if (!a) return null;
  if (a.poids_unitaire_kg) return +a.poids_unitaire_kg;
  if (a.poids_colis_kg && a.qte_par_colis) return +a.poids_colis_kg / +a.qte_par_colis;
  return null;
}

function majPoidsPieceVisible() {
  // On ne demande le poids que pour l'unité « pièce » ET si on ne le connaît pas.
  const besoin = (state.unite === 'piece') && (poidsPieceConnu() == null);
  $('invv-modal-poids-piece').hidden = !besoin;
}

function majApercu() {
  const a = state.article;
  const ap = $('invv-modal-apercu');
  const q = parseFloat($('invv-modal-qte-input').value);
  if (!a || isNaN(q) || q <= 0) { ap.textContent = '—'; ap.className = 'invv-modal-apercu'; return; }

  const { poidsKg, valeur } = calculerApercu(q);
  if (valeur != null) {
    ap.textContent = `${fmtKg(poidsKg)} → ${fmtEur(valeur)} HT`;
    ap.className = 'invv-modal-apercu';
  } else {
    ap.textContent = 'Valeur non calculable (renseignez le poids ou le €/kg)';
    ap.className = 'invv-modal-apercu invv-modal-apercu--na';
  }
}

// Réplique côté client la valorisation backend pour l'aperçu live.
function calculerApercu(q) {
  const a = state.article;
  let poidsKg = null;
  if (state.unite === 'kg') {
    poidsKg = q;
  } else if (state.unite === 'colis') {
    if (a.poids_colis_kg) poidsKg = q * (+a.poids_colis_kg);
  } else if (state.unite === 'piece') {
    let ppk = parseFloat($('invv-modal-poids-input').value);
    if (isNaN(ppk) || ppk <= 0) ppk = poidsPieceConnu();
    if (ppk) poidsKg = q * ppk;
  }
  const valeur = (poidsKg != null && a.prix_kg != null) ? Math.round(poidsKg * a.prix_kg * 100) / 100 : null;
  return { poidsKg, valeur };
}

async function validerLigne() {
  const a = state.article;
  const q = parseFloat($('invv-modal-qte-input').value);
  if (!a || isNaN(q) || q <= 0) { toast('Saisissez une quantité', 'err'); return; }

  const body = {
    catalogue_fournisseur_id: a.id,
    quantite: q,
    unite_saisie: state.unite,
  };
  const ppkSaisi = parseFloat($('invv-modal-poids-input').value);
  const memoriser = (state.unite === 'piece') && !isNaN(ppkSaisi) && ppkSaisi > 0 && (poidsPieceConnu() == null);
  if (memoriser) body.poids_piece_kg = ppkSaisi;

  try {
    // Mémorise le poids de la pièce sur le catalogue (une fois) pour ne plus le redemander.
    if (memoriser) {
      await api.put(`/api/inventaire/catalogue/${a.id}/poids-piece`, { poids_unitaire_kg: ppkSaisi });
      a.poids_unitaire_kg = ppkSaisi; // l'article courant connaît désormais son poids
    }
    const r = await api.post(`/api/inventaire/sessions/${state.session.id}/lignes`, body);
    fermerModale();
    toast(r.valeur_ht != null ? `Ajouté : ${fmtEur(r.valeur_ht)}` : 'Ajouté (valeur indisponible)', 'ok');
    await rechargerLignes();
  } catch (e) {
    toast('Ajout impossible : ' + e.message, 'err');
  }
}

// ════════════════════════════════════════════════════════════
//  Modification du prix €/kg (remonte au catalogue achats)
// ════════════════════════════════════════════════════════════

// Le prix €/kg n'est modifiable que pour les formats que le backend sait reconvertir :
// viande / format 'kg' (prix = €/kg direct) ou colis AVEC poids de colis connu.
function prixKgModifiable(a) {
  if (!a) return false;
  const fam = String(a.famille || '').trim().toLowerCase();
  if (fam === 'viande' || a.format_prix === 'kg') return true;
  if (a.format_prix === 'colis' && a.poids_colis_kg) return true;
  return false;
}

function ouvrirEditeurPrix() {
  const a = state.article;
  if (!a) return;
  const ed = $('invv-modal-prix-editor');
  const ouvert = !ed.hidden;
  ed.hidden = ouvert; // toggle
  if (!ouvert) {
    const inp = $('invv-modal-prix-input');
    inp.value = (a.prix_kg != null) ? a.prix_kg : '';
    setTimeout(() => { inp.focus(); inp.select(); }, 60);
  }
}

async function enregistrerPrixKg() {
  const a = state.article;
  if (!a) return;
  const prix = parseFloat($('invv-modal-prix-input').value);
  if (isNaN(prix) || prix < 0) { toast('Prix invalide', 'err'); return; }

  try {
    const r = await api.put(`/api/inventaire/catalogue/${a.id}/prix-kg`, { prix_kg: prix });
    // Met à jour l'article courant avec le €/kg effectif renvoyé par le backend.
    a.prix_kg = r.prix_kg;
    a.prix_achat_ht = r.prix_achat_ht;
    // Rafraîchit l'affichage du prix dans la modale + l'aperçu.
    const pk = $('invv-modal-prixkg');
    pk.textContent = (a.prix_kg != null) ? `${fmtEur(a.prix_kg)} / kg` : '€/kg indisponible';
    pk.className = 'invv-modal-prixkg' + (a.prix_kg == null ? ' invv-modal-prixkg--na' : '');
    $('invv-modal-prix-editor').hidden = true;
    majApercu();
    // Revalorise les lignes DÉJÀ saisies de cet article dans la session en cours.
    await revaloriserLignesArticle(a.id);
    toast('Prix mis à jour (catalogue + inventaire)', 'ok');
  } catch (e) {
    toast('Mise à jour impossible : ' + e.message, 'err');
  }
}

// Re-déclenche la valorisation backend (PUT /lignes/{id}) des lignes de cet article :
// le serveur recharge le catalogue (nouveau prix) et recalcule prix_kg_fige + valeur_ht.
async function revaloriserLignesArticle(catalogueId) {
  const lignes = state.lignes.filter((l) => l.catalogue_fournisseur_id === catalogueId);
  if (!lignes.length) return;
  for (const l of lignes) {
    try {
      await api.put(`/api/inventaire/lignes/${l.id}`, {
        quantite: l.quantite,
        unite_saisie: l.unite_saisie,
        poids_piece_kg: l.poids_kg_calcule && l.unite_saisie === 'piece'
          ? l.poids_kg_calcule / l.quantite : undefined,
      });
    } catch (_) { /* on continue : une ligne en échec ne bloque pas les autres */ }
  }
  await rechargerLignes();
}

// ════════════════════════════════════════════════════════════
//  Lignes & total
// ════════════════════════════════════════════════════════════

async function rechargerLignes() {
  const d = await api.get(`/api/inventaire/sessions/${state.session.id}`);
  state.lignes = d.lignes;
  state.total = d.total_ht;
  rendreLignes();
  rendreTotal(d.nb_non_valorisees);
}

const UNITE_LBL = { kg: 'kg', piece: 'pièce(s)', colis: 'colis' };

function rendreLignes() {
  const box = $('invv-lignes');
  $('invv-nb-lignes').textContent = state.lignes.length;
  box.innerHTML = '';
  if (!state.lignes.length) {
    box.innerHTML = '<div class="invv-vide">Aucun article compté.</div>';
    return;
  }
  for (const l of state.lignes) {
    const row = document.createElement('div');
    row.className = 'invv-ligne';
    const qte = (+l.quantite).toLocaleString('fr-FR', { maximumFractionDigits: 3 });
    const detail = `${qte} ${UNITE_LBL[l.unite_saisie] || l.unite_saisie}`
      + (l.prix_kg_fige != null ? ` · ${fmtEur(l.prix_kg_fige)}/kg` : '');
    const val = (l.valeur_ht != null)
      ? `<span class="invv-ligne-val">${fmtEur(l.valeur_ht)}</span>`
      : `<span class="invv-ligne-val invv-ligne-val--na">n/d</span>`;
    row.innerHTML = `
      <div class="invv-ligne-main">
        <span class="invv-ligne-nom">${esc(l.designation)}</span>
        <span class="invv-ligne-detail">${detail}</span>
      </div>
      ${val}
      ${estCloture() ? '' : `<button type="button" class="invv-ligne-del" data-del="${l.id}" aria-label="Supprimer">✕</button>`}`;
    const del = row.querySelector('[data-del]');
    if (del) del.onclick = () => supprimerLigne(l.id);
    box.appendChild(row);
  }
}

function rendreTotal(nbNonValo) {
  $('invv-total').textContent = fmtEur(state.total);
  const nv = $('invv-non-valo');
  if (nbNonValo > 0) {
    nv.hidden = false;
    nv.textContent = `⚠️ ${nbNonValo} article(s) sans valeur (poids ou €/kg manquant)`;
  } else {
    nv.hidden = true;
  }
}

async function supprimerLigne(id) {
  try {
    await api.del(`/api/inventaire/lignes/${id}`);
    await rechargerLignes();
  } catch (e) {
    toast('Suppression impossible : ' + e.message, 'err');
  }
}

async function cloturer() {
  if (!confirm('Clôturer cet inventaire ? La valeur sera figée et la saisie verrouillée.')) return;
  try {
    const r = await api.put(`/api/inventaire/sessions/${state.session.id}/cloturer`);
    state.session.statut = 'cloture';
    state.session.valeur_totale_ht = r.valeur_totale_ht;
    state.total = r.valeur_totale_ht;
    toast(`Inventaire clôturé : ${fmtEur(r.valeur_totale_ht)}`, 'ok');
    rendreBandeau();
    rendreLignes();
  } catch (e) {
    toast('Clôture impossible : ' + e.message, 'err');
  }
}

// ── Utilitaire ──
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// ════════════════════════════════════════════════════════════
//  Init
// ════════════════════════════════════════════════════════════

function init() {
  $('invv-btn-nouveau').onclick = nouvelInventaire;
  $('invv-btn-sessions').onclick = () => { montrerEcran('sessions'); chargerSessions(); };

  $('invv-search').oninput = lancerRecherche;
  $('invv-search-clear').onclick = () => {
    $('invv-search').value = '';
    $('invv-search-clear').hidden = true;
    rechercherArticles();
  };

  // Filtres rapides badges (un clic = (dé)sélection exclusive)
  document.querySelectorAll('.invv-filtre-badge').forEach((btn) => {
    btn.onclick = () => {
      const b = btn.dataset.badge;
      state.badgeActif = (state.badgeActif === b) ? null : b;
      rendreFiltresBadges();
      rechercherArticles();
    };
  });

  // Filtre fournisseur
  $('invv-filtre-fournisseur').onchange = (e) => {
    state.fournisseurActif = e.target.value || null;
    rechercherArticles();
  };

  // Modale
  $('invv-modal-qte').querySelectorAll('[data-close]').forEach((el) => { el.onclick = fermerModale; });
  document.querySelectorAll('.invv-unite-btn').forEach((btn) => {
    btn.onclick = () => {
      state.unite = btn.dataset.unite;
      majToggleUnite();
      majPoidsPieceVisible();
      majApercu();
    };
  });
  $('invv-modal-qte-input').oninput = majApercu;
  $('invv-modal-poids-input').oninput = majApercu;
  $('invv-modal-valider').onclick = validerLigne;
  $('invv-modal-prix-edit').onclick = ouvrirEditeurPrix;
  $('invv-modal-prix-save').onclick = enregistrerPrixKg;
  $('invv-modal-prix-input').onkeydown = (e) => { if (e.key === 'Enter') enregistrerPrixKg(); };

  $('invv-btn-cloturer').onclick = cloturer;

  montrerEcran('sessions');
  chargerSessions();
}

document.addEventListener('DOMContentLoaded', init);

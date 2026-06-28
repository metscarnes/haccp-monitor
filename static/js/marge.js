'use strict';
/* ============================================================
   marge.js — Tableau de bord MARGE
   Marge = CA HT − (Achats HT + Stock Initial − Stock Final)
   ============================================================ */

const $ = (id) => document.getElementById(id);
const fmtEur = (v) => (v == null)
  ? '—'
  : new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(v);
const iso = (d) => d.toISOString().slice(0, 10);

const api = {
  async get(url) {
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  },
  async put(url, body) {
    const r = await fetch(url, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    if (!r.ok) { let m = `HTTP ${r.status}`; try { m = (await r.json()).detail || m; } catch (_) {} throw new Error(m); }
    return r.json();
  },
};

const state = { tva: 5.5, data: null };

let _toastTimer = null;
function toast(msg, type = '') {
  const el = $('marge-toast');
  el.textContent = msg; el.className = 'marge-toast' + (type ? ` marge-toast--${type}` : '');
  el.hidden = false; clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { el.hidden = true; }, 2600);
}

// ── Périodes prédéfinies ─────────────────────────────────────
function moisCourant() {
  const n = new Date();
  return { debut: new Date(n.getFullYear(), n.getMonth(), 1), fin: new Date(n.getFullYear(), n.getMonth() + 1, 0) };
}
function moisPrecedent() {
  const n = new Date();
  return { debut: new Date(n.getFullYear(), n.getMonth() - 1, 1), fin: new Date(n.getFullYear(), n.getMonth(), 0) };
}
function anneeCourante() {
  const n = new Date();
  return { debut: new Date(n.getFullYear(), 0, 1), fin: new Date(n.getFullYear(), 11, 31) };
}

const PRESETS = [
  { id: 'mois', label: 'Mois en cours', calc: moisCourant },
  { id: 'mois-1', label: 'Mois dernier', calc: moisPrecedent },
  { id: 'annee', label: 'Année', calc: anneeCourante },
];

function rendrePresets() {
  const box = $('marge-presets');
  box.innerHTML = '';
  for (const p of PRESETS) {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'marge-preset-btn'; b.textContent = p.label;
    b.setAttribute('aria-pressed', 'false');
    b.onclick = () => {
      const { debut, fin } = p.calc();
      $('marge-debut').value = iso(debut);
      $('marge-fin').value = iso(fin);
      document.querySelectorAll('.marge-preset-btn').forEach((x) => x.setAttribute('aria-pressed', 'false'));
      b.setAttribute('aria-pressed', 'true');
      calculer();
    };
    box.appendChild(b);
  }
}

// ── Calcul ───────────────────────────────────────────────────
async function calculer() {
  const debut = $('marge-debut').value, fin = $('marge-fin').value;
  if (!debut || !fin) { toast('Choisissez une période', 'err'); return; }
  if (debut > fin) { toast('La date de début doit précéder la fin', 'err'); return; }
  try {
    const params = new URLSearchParams({ date_debut: debut, date_fin: fin });
    const siZero = $('marge-si-zero').checked;
    if (siZero) params.set('stock_initial_zero', 'true');
    // Conserver l'override de stock si l'utilisateur en a choisi un
    // (un override de stock initial prime sur la convention « zéro » → on ne l'envoie pas si zéro coché)
    const si = $('pick-si').value, sf = $('pick-sf').value;
    if (!siZero && si && si !== 'auto') params.set('stock_initial_id', si);
    if (sf && sf !== 'auto') params.set('stock_final_id', sf);
    state.data = await api.get('/api/inventaire/marge?' + params.toString());
    rendre();
  } catch (e) {
    toast('Calcul impossible : ' + e.message, 'err');
  }
}

function rendre() {
  const d = state.data;
  // Carte résultat
  $('marge-val').textContent = fmtEur(d.marge_brute_ht);
  $('marge-pct').textContent = (d.marge_pct != null) ? `${d.marge_pct} % du CA HT` : '';
  const note = $('marge-note');
  const result = $('marge-result');
  if (!d.marge_fiable) {
    note.hidden = false;
    note.textContent = '⚠️ Estimation : il manque une photo d\'inventaire (stock initial et/ou final). La marge n\'intègre pas la variation de stock.';
    result.classList.add('marge-result--na');
  } else {
    note.hidden = true;
    result.classList.remove('marge-result--na');
  }

  // Décomposition
  $('d-ca').textContent = fmtEur(d.ca.ht);
  $('d-ca-sub').textContent = `${fmtEur(d.ca.ttc)} TTC ÷ ${1 + d.tva_pct / 100} (TVA ${d.tva_pct} %) · ${d.ca.nb_jours} jour(s) saisis`;
  const a = d.achats;
  const achatsEl = $('d-achats');
  achatsEl.textContent = fmtEur(a.ht);
  achatsEl.classList.toggle('marge-val--reel', a.source === 'reel');
  if (a.source === 'reel') {
    const ecart = (a.ecart_reel_calcule != null)
      ? ` · écart calcul ${a.ecart_reel_calcule >= 0 ? '+' : ''}${fmtEur(a.ecart_reel_calcule)}` : '';
    $('d-achats-sub').textContent =
      `📑 Réel (factures) · calcul auto : ${fmtEur(a.ht_calcule)}${ecart}`;
  } else {
    let sub = `${a.nb_lignes} ligne(s) de réception clôturée (calcul auto)`;
    if (a.nb_non_valorisees > 0) sub += ` · ⚠️ ${a.nb_non_valorisees} sans valeur`;
    if (!a.saisie_possible) sub += ' · saisie réelle = période dans un seul mois';
    $('d-achats-sub').textContent = sub;
  }
  // Le crayon achats n'a de sens que si la période tient dans un seul mois civil.
  $('edit-achats').style.display = a.saisie_possible ? '' : 'none';

  if (d.stock_initial) {
    $('d-si').textContent = fmtEur(d.stock_initial.valeur_totale_ht);
  } else if (d.stock_initial_zero) {
    $('d-si').textContent = fmtEur(0) + ' (démarrage)';
  } else {
    $('d-si').textContent = '— (aucune photo)';
  }
  $('d-sf').textContent = d.stock_final ? fmtEur(d.stock_final.valeur_totale_ht) : '— (aucune photo)';

  // Le sélecteur de stock initial n'a pas de sens quand « démarrage à 0 » est coché.
  $('pick-si').disabled = $('marge-si-zero').checked;
  $('d-marge').textContent = fmtEur(d.marge_brute_ht);
  $('d-cmv').textContent = fmtEur(d.cmv);

  // Sélecteurs de stock
  remplirPickers();
}

function remplirPickers() {
  const d = state.data;
  for (const [sel, courant] of [['pick-si', d.stock_initial], ['pick-sf', d.stock_final]]) {
    const el = $(sel);
    const prev = el.value;
    el.innerHTML = '<option value="auto">Auto (plus proche)</option>';
    for (const inv of d.inventaires_clotures) {
      const o = document.createElement('option');
      o.value = inv.id;
      const date = new Date(inv.date_inventaire).toLocaleDateString('fr-FR');
      o.textContent = `${date} · ${fmtEur(inv.valeur_totale_ht)}${inv.libelle ? ' · ' + inv.libelle : ''}`;
      el.appendChild(o);
    }
    // Refléter le choix courant : override conservé, sinon 'auto'
    el.value = (prev && prev !== 'auto') ? prev : 'auto';
  }
}

// ── TVA ──────────────────────────────────────────────────────
async function chargerTva() {
  try {
    const d = await api.get('/api/inventaire/marge/tva');
    state.tva = d.tva_pct;
    $('marge-tva-val').textContent = `${d.tva_pct} %`;
  } catch (_) {}
}

function ouvrirTva() {
  $('marge-modal-tva-input').value = state.tva;
  $('marge-modal-tva').hidden = false;
  setTimeout(() => $('marge-modal-tva-input').focus(), 50);
}
function fermerTva() { $('marge-modal-tva').hidden = true; }

async function enregistrerTva() {
  const v = parseFloat($('marge-modal-tva-input').value);
  if (isNaN(v) || v < 0 || v > 100) { toast('Taux invalide', 'err'); return; }
  try {
    await api.put('/api/inventaire/marge/tva', { tva_pct: v });
    state.tva = v;
    $('marge-tva-val').textContent = `${v} %`;
    fermerTva();
    toast('TVA enregistrée', '');
    if (state.data) calculer();
  } catch (e) {
    toast('Erreur : ' + e.message, 'err');
  }
}

// ── Édition CA TTC (rapprochement banque) ────────────────────
function ouvrirEditCa() {
  if (!state.data) return;
  // Pré-remplit avec le CA TTC actuel de la période
  $('input-ca-ttc').value = state.data.ca.ttc || '';
  $('editor-ca').hidden = false;
  setTimeout(() => $('input-ca-ttc').focus(), 50);
}
function fermerEditCa() { $('editor-ca').hidden = true; }

async function enregistrerCa() {
  const v = parseFloat($('input-ca-ttc').value);
  if (isNaN(v) || v < 0) { toast('Montant invalide', 'err'); return; }
  try {
    const r = await api.put('/api/inventaire/marge/ca-ajuster', {
      date_debut: $('marge-debut').value, date_fin: $('marge-fin').value,
      montant_ttc_cible: v,
    });
    fermerEditCa();
    const msg = (r.ecart === 0) ? 'CA calé (aucun écart)' : `CA calé · ajustement ${fmtEur(r.ecart)}`;
    toast(msg, '');
    calculer();   // recharge (le CA mis à jour est aussi visible dans Pilotage)
  } catch (e) {
    toast('Erreur : ' + e.message, 'err');
  }
}

// ── Édition Achats réels (factures du mois) ──────────────────
function ouvrirEditAchats() {
  if (!state.data || !state.data.achats.saisie_possible) return;
  const a = state.data.achats;
  $('input-achats-ht').value = (a.ht_reel != null) ? a.ht_reel : '';
  $('achats-editor-hint').textContent =
    `Mois ${a.annee_mois} · base date de facture · calcul auto : ${fmtEur(a.ht_calcule)}`;
  $('editor-achats').hidden = false;
  setTimeout(() => $('input-achats-ht').focus(), 50);
}
function fermerEditAchats() { $('editor-achats').hidden = true; }

async function enregistrerAchats(effacer) {
  const am = state.data && state.data.achats.annee_mois;
  if (!am) return;
  const body = { annee_mois: am };
  if (!effacer) {
    const v = parseFloat($('input-achats-ht').value);
    if (isNaN(v) || v < 0) { toast('Montant invalide', 'err'); return; }
    body.montant_ht = v;
  }
  try {
    await api.put('/api/inventaire/marge/achats-reels', body);
    fermerEditAchats();
    toast(effacer ? 'Retour au calcul auto' : 'Achats réels enregistrés', '');
    calculer();
  } catch (e) {
    toast('Erreur : ' + e.message, 'err');
  }
}

// ── Init ─────────────────────────────────────────────────────
function init() {
  rendrePresets();
  $('marge-calc').onclick = calculer;
  $('pick-si').onchange = calculer;
  $('pick-sf').onchange = calculer;
  $('marge-si-zero').onchange = calculer;

  $('marge-btn-tva').onclick = ouvrirTva;
  $('marge-modal-tva').querySelectorAll('[data-close]').forEach((el) => { el.onclick = fermerTva; });
  $('marge-modal-tva-ok').onclick = enregistrerTva;

  // Éditeurs CA / Achats
  $('edit-ca').onclick = ouvrirEditCa;
  $('editor-ca').querySelector('[data-cancel-ca]').onclick = fermerEditCa;
  $('save-ca').onclick = enregistrerCa;
  $('edit-achats').onclick = ouvrirEditAchats;
  $('save-achats').onclick = () => enregistrerAchats(false);
  $('clear-achats').onclick = () => enregistrerAchats(true);

  chargerTva();
  // Par défaut : mois en cours
  const { debut, fin } = moisCourant();
  $('marge-debut').value = iso(debut);
  $('marge-fin').value = iso(fin);
  document.querySelector('.marge-preset-btn')?.setAttribute('aria-pressed', 'true');
  calculer();
}

document.addEventListener('DOMContentLoaded', init);

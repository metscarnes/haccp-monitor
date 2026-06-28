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
    // Conserver l'override de stock si l'utilisateur en a choisi un
    const si = $('pick-si').value, sf = $('pick-sf').value;
    if (si && si !== 'auto') params.set('stock_initial_id', si);
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
  $('d-achats').textContent = fmtEur(d.achats.ht);
  let achatsSub = `${d.achats.nb_lignes} ligne(s) de réception clôturée`;
  if (d.achats.nb_non_valorisees > 0) achatsSub += ` · ⚠️ ${d.achats.nb_non_valorisees} sans valeur`;
  $('d-achats-sub').textContent = achatsSub;

  $('d-si').textContent = d.stock_initial ? fmtEur(d.stock_initial.valeur_totale_ht) : '— (aucune photo)';
  $('d-sf').textContent = d.stock_final ? fmtEur(d.stock_final.valeur_totale_ht) : '— (aucune photo)';
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

// ── Init ─────────────────────────────────────────────────────
function init() {
  rendrePresets();
  $('marge-calc').onclick = calculer;
  $('pick-si').onchange = calculer;
  $('pick-sf').onchange = calculer;

  $('marge-btn-tva').onclick = ouvrirTva;
  $('marge-modal-tva').querySelectorAll('[data-close]').forEach((el) => { el.onclick = fermerTva; });
  $('marge-modal-tva-ok').onclick = enregistrerTva;

  chargerTva();
  // Par défaut : mois en cours
  const { debut, fin } = moisCourant();
  $('marge-debut').value = iso(debut);
  $('marge-fin').value = iso(fin);
  document.querySelector('.marge-preset-btn')?.setAttribute('aria-pressed', 'true');
  calculer();
}

document.addEventListener('DOMContentLoaded', init);

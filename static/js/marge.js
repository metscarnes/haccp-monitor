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
// Le Stock Final n'existe que là où une photo d'inventaire a été clôturée :
// calculer une marge jusqu'à la fin calendaire du mois quand la dernière
// photo s'arrête plus tôt donnerait un CMV/marge non fiable (variation de
// stock inconnue sur les jours restants). On plafonne donc la fin de période
// à la date du dernier inventaire clôturé, jamais au-delà.
let _dernierInventaireDate = null;   // cache : Date | null

async function dernierInventaireCloture() {
  if (_dernierInventaireDate !== null) return _dernierInventaireDate;
  try {
    // limit=1 ne suffit pas : la session la PLUS RÉCENTE peut être 'en_cours'
    // (pas encore clôturée) alors qu'une plus ancienne l'est déjà — on regarde
    // les dernières sessions pour trouver la première réellement clôturée.
    const d = await api.get('/api/inventaire/sessions?limit=20');
    const s = (d.sessions || []).find(s => s.statut === 'cloture');
    _dernierInventaireDate = s ? new Date(s.date_inventaire) : undefined;
  } catch (_) {
    _dernierInventaireDate = undefined;   // échec réseau : pas de plafond, tant pis
  }
  return _dernierInventaireDate;
}

// Ramène `fin` à la date du dernier inventaire clôturé si elle est plus tôt
// (jamais l'inverse : un inventaire fait en avance n'étend pas la période).
async function plafonnerFin(fin) {
  const dernier = await dernierInventaireCloture();
  return (dernier && dernier < fin) ? dernier : fin;
}

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
  { id: 'mois', label: 'Mois en cours', calc: moisCourant, plafonner: true },
  { id: 'mois-1', label: 'Mois dernier', calc: moisPrecedent, plafonner: false },
  { id: 'annee', label: 'Année', calc: anneeCourante, plafonner: true },
];

function rendrePresets() {
  const box = $('marge-presets');
  box.innerHTML = '';
  for (const p of PRESETS) {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'marge-preset-btn'; b.textContent = p.label;
    b.setAttribute('aria-pressed', 'false');
    b.onclick = async () => {
      let { debut, fin } = p.calc();
      const finCalendaire = fin;
      // Seuls les presets « en cours » (mois en cours, année en cours) sont
      // plafonnés : « mois dernier » est une période close, le stock final
      // théorique (fin de mois) doit déjà avoir sa photo si l'utilisateur la fait.
      if (p.plafonner) fin = await plafonnerFin(fin);
      $('marge-debut').value = iso(debut);
      $('marge-fin').value = iso(fin);
      document.querySelectorAll('.marge-preset-btn').forEach((x) => x.setAttribute('aria-pressed', 'false'));
      b.setAttribute('aria-pressed', 'true');
      if (fin < finCalendaire) {
        toast(`Période calée au ${fin.toLocaleDateString('fr-FR')} : dernier inventaire clôturé`, '');
      }
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
  achatsEl.classList.toggle('marge-val--reel', a.source === 'par_reception' || a.source === 'reel');
  const ecartTxt = (a.ecart_reel_calcule != null)
    ? ` · écart vs calcul catalogue ${a.ecart_reel_calcule >= 0 ? '+' : ''}${fmtEur(a.ecart_reel_calcule)}` : '';
  if (a.source === 'par_reception') {
    // Calcul réception par réception : facture (validée/litige) > prix BL saisi
    // > catalogue. Jamais de trou — chaque réception contribue toujours.
    const compo = [];
    if (a.nb_source_facture) compo.push(`🧾 ${a.nb_source_facture} facture(s)`);
    if (a.nb_source_bl) compo.push(`📋 ${a.nb_source_bl} prix BL`);
    if (a.nb_source_catalogue) compo.push(`📚 ${a.nb_source_catalogue} catalogue`);
    $('d-achats-sub').textContent =
      `${compo.join(' · ')} sur ${a.nb_receptions} réception(s) · calcul catalogue seul : ${fmtEur(a.ht_calcule)}${ecartTxt}`;
  } else if (a.source === 'reel') {
    // Override manuel : montant saisi à la main pour cette période (prime volontairement).
    $('d-achats-sub').textContent =
      `📝 Saisie manuelle (prime sur le calcul) · calcul catalogue : ${fmtEur(a.ht_calcule)}${ecartTxt}`;
  } else {
    let sub = `${a.nb_lignes} ligne(s) de réception clôturée (calcul catalogue)`;
    if (a.nb_non_valorisees > 0) sub += ` · ⚠️ ${a.nb_non_valorisees} sans valeur`;
    $('d-achats-sub').textContent = sub;
  }
  // Le crayon achats est toujours disponible (saisie rattachée à la période exacte).

  // Anomalie opérationnelle : réception clôturée sans AUCUNE facture (même
  // brouillon). Le hook de clôture doit toujours en créer une — son absence
  // signale un problème à corriger (créer la facture manquante), pas un cas
  // normal. Le montant de ces réceptions reste compté (BL ou catalogue), donc
  // la marge n'est pas faussée, mais leur prix n'est pas encore vérifié.
  const zoneAnomalie = $('d-achats-anomalie');
  const anomalies = a.anomalies_sans_facture || [];
  if (zoneAnomalie) {
    if (anomalies.length) {
      zoneAnomalie.hidden = false;
      zoneAnomalie.innerHTML = `⚠️ ${anomalies.length} réception(s) sans AUCUNE facture — `
        + `anomalie à corriger dans le module Achats :<br>`
        + anomalies.map(x => `• ${x.date_reception} — ${x.fournisseur_nom || '?'} (réception #${x.reception_id})`).join('<br>');
    } else {
      zoneAnomalie.hidden = true;
    }
  }

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

// ── Édition Achats réels (factures de la période) ────────────
function ouvrirEditAchats() {
  if (!state.data) return;
  const a = state.data.achats;
  $('input-achats-ht').value = (a.ht_reel != null) ? a.ht_reel : '';
  const base = (a.source === 'par_reception' || a.source === 'reel')
    ? `Calcul par réception actuel : ${fmtEur(a.ht_par_reception ?? a.ht_calcule)} `
      + `(${a.nb_source_facture || 0} facture(s), ${a.nb_source_bl || 0} prix BL, `
      + `${a.nb_source_catalogue || 0} catalogue). Une saisie ici PRIME volontairement sur ce calcul.`
    : `Période ${$('marge-debut').value} → ${$('marge-fin').value} · base date de réception · calcul catalogue : ${fmtEur(a.ht_calcule)}`;
  $('achats-editor-hint').textContent = base;
  $('editor-achats').hidden = false;
  setTimeout(() => $('input-achats-ht').focus(), 50);
}
function fermerEditAchats() { $('editor-achats').hidden = true; }

async function enregistrerAchats(effacer) {
  if (!state.data) return;
  const body = { date_debut: $('marge-debut').value, date_fin: $('marge-fin').value };
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
async function init() {
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
  // Par défaut : mois en cours, plafonné au dernier inventaire clôturé.
  const { debut, fin: finCalendaire } = moisCourant();
  const fin = await plafonnerFin(finCalendaire);
  $('marge-debut').value = iso(debut);
  $('marge-fin').value = iso(fin);
  document.querySelector('.marge-preset-btn')?.setAttribute('aria-pressed', 'true');
  calculer();
}

document.addEventListener('DOMContentLoaded', init);

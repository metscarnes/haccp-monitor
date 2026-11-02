'use strict';
/* ============================================================
   cuisson.js — Cuisson & refroidissement (fiche unique, v8.7)
   Au Comptoir des Lilas — Mets Carnés Holding

   Pensé pour la saisie après coup (rattrapage du soir) :
     • Accueil : fiches « À compléter » + terminées des 7 derniers jours.
     • Fiche   : produit + lot → cuisson → ensuite (refroidi / vendu chaud /
                 plus tard) → refroidissement. Une fiche peut être ouverte dans
                 la journée (produit + lot) et complétée le soir.
   Aucune heure n'est remplie d'avance : seule la mise au froid reprend la fin
   de cuisson. Les boutons rapides calculent la fin depuis le début (ou le
   début depuis la fin). Le serveur refuse les heures incohérentes ou futures.
   ============================================================ */

const TEMP_CIBLE_REFROID = 10;
const DUREE_MAX_REFROID  = 120;
const ECART_MAX_MISE_AU_FROID = 30;   // min entre sortie de cuisson et mise au froid
const ESPECES_DEGRE = ['Bœuf', 'Boeuf', 'Agneau'];
const TYPES_CUISSON = { four: 'Four', rotissoire: 'Rôtissoire', marmite: 'Marmite / plaque', autre: 'Autre' };
const CLE_TYPE_DEFAUT = 'cuisson_type_defaut';   // dernier type utilisé sur cette tablette
const DEGRES = {
  saignant:  55,
  a_point:   63,
  bien_cuit: 75,
  generale:  75,
};

// ── Helpers ────────────────────────────────────────────────
const $ = id => document.getElementById(id);

function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function apiFetch(url, options = {}) {
  const res = await fetch(url, { cache: 'no-store', ...options });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    let msg = txt;
    try {
      const j = JSON.parse(txt);
      if (j && j.detail) msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail);
    } catch { /* noop */ }
    throw new Error(msg || `HTTP ${res.status}`);
  }
  return res.json();
}

const pad = n => String(n).padStart(2, '0');

function aujourdhuiISO() {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** 'YYYY-MM-DD' → Date locale (sans le décalage UTC de new Date(iso)). */
function dateLocale(iso) {
  const [y, m, d] = (iso || '').split('-').map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}

function formatDate(iso) {
  if (!iso) return '—';
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

function formatJour(iso) {
  if (!iso) return '—';
  if (iso === aujourdhuiISO()) return "aujourd'hui";
  const j = dateLocale(iso).toLocaleDateString('fr-FR', { weekday: 'short' });
  const [, m, d] = iso.split('-');
  return `${j} ${d}/${m}`;
}

function minutes(hhmm) {
  const [h, m] = (hhmm || '').split(':').map(Number);
  return (isNaN(h) || isNaN(m)) ? null : h * 60 + m;
}

function hhmm(total) {
  if (total == null || total < 0 || total >= 24 * 60) return null;
  return `${pad(Math.floor(total / 60))}:${pad(total % 60)}`;
}

function formatDuree(min) {
  if (min == null) return '';
  const h = Math.floor(min / 60), m = min % 60;
  return h ? `${h} h${m ? ' ' + pad(m) : ''}` : `${m} min`;
}

function nombre(el) {
  const v = parseFloat(String(el.value).replace(',', '.'));
  return isNaN(v) ? null : v;
}

// ── DOM ─────────────────────────────────────────────────────
const elVueAccueil   = $('cu-vue-accueil');
const elVueFiche     = $('cu-vue-fiche');
const elListeAC      = $('cu-liste-a-completer');
const elListeTerm    = $('cu-liste-terminees');
const elNbAC         = $('cu-nb-a-completer');
const elNbTerm       = $('cu-nb-terminees');

const elForm         = $('cu-form');
const elOperateurs   = $('cu-operateurs');
const elDate         = $('cu-date');
const elQuantite     = $('cu-quantite');
const elUnite        = $('cu-unite');
const elProduitChoix = $('cu-produit-choix');
const elProduitSearch = $('cu-produit-search');
const elProduitSuggest = $('cu-produit-suggest');
const elProduitResume = $('cu-produit-resume');
const elLotWrap      = $('cu-lot-wrap');
const elLot          = $('cu-lot');
const elLotEpuise    = $('cu-lot-epuise');
const elTypeChoix    = $('cu-type-choix');
const elDevientWrap  = $('cu-devient-wrap');
const elDevientChoix = $('cu-devient-choix');
const elDevientSearch = $('cu-devient-search');

const elCuissonResume = $('cu-cuisson-resume');
const elCuissonSaisie = $('cu-cuisson-saisie');
const elHeureDebut   = $('cu-heure-debut');
const elHeureFin     = $('cu-heure-fin');
const elQuickCuisson = $('cu-quick-cuisson');
const elDureeCuisson = $('cu-duree-cuisson');
const elDegreWrap    = $('cu-degre-wrap');
const elDegreChoix   = $('cu-degre-choix');
const elTemperature  = $('cu-temperature');
const elCible        = $('cu-cible-texte');
const elConformite   = $('cu-conformite');
const elActionWrap   = $('cu-action-wrap');
const elAction       = $('cu-action');

const elBlocSuite    = $('cu-bloc-suite');
const elSuiteAide    = $('cu-suite-aide');
const elBlocRefroid  = $('cu-bloc-refroid');
const elRefroidDebut = $('cu-refroid-debut');
const elRefroidDebutAide = $('cu-refroid-debut-aide');
const elRefroidFin   = $('cu-refroid-fin');
const elQuickRefroid = $('cu-quick-refroid');
const elDureeRefroid = $('cu-duree-refroid');
const elRefroidTemp  = $('cu-refroid-temp');
const elRefroidConf  = $('cu-refroid-conformite');
const elRefroidActionWrap = $('cu-refroid-action-wrap');
const elRefroidAction = $('cu-refroid-action');
const elJeterWrap    = $('cu-jeter-wrap');
const elJeter        = $('cu-jeter');

const elErreur       = $('cu-erreur');
const elBtnSave      = $('cu-btn-save');
const elBtnSaveEtiq  = $('cu-btn-save-etiquette');
const elToast        = $('cu-toast');
const elModal        = $('cu-modal-receptions');
const elModalTitre   = $('cu-modal-titre');
const elModalCorps   = $('cu-modal-corps');

// ── État ───────────────────────────────────────────────────
const state = {
  personnel: [],
  produits:  [],          // stock cuisinable (GET /produits-disponibles)
  fiches:    { a_completer: [], terminees: [] },
  fiche:     null,        // fiche existante en cours de complément (null = nouvelle)
  operateurId: null,
  produit:   null,        // produit choisi (nouvelle fiche)
  lots:      [],
  devient:   null,        // { id, nom } — produit du catalogue vente
  degre:     'generale',
  typeCuisson: 'four',
  suite:     '',          // '' (plus tard) | 'refroidi' | 'vendu_chaud'
  refroidDebutManuel: false,
  envoiEnCours: false,
};

// ── Horloge & inactivité ───────────────────────────────────
(function majHorloge() {
  $('cu-horloge').textContent = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  setTimeout(majHorloge, 1000);
})();

// Retour au hub après 5 min sans activité — jamais pendant une saisie : une fiche
// de rattrapage se remplit lentement, la perdre ferait tout recommencer.
let timerInactivite;
function resetInactivite() {
  clearTimeout(timerInactivite);
  timerInactivite = setTimeout(() => {
    if (elVueFiche.hidden) window.location.href = '/hub.html';
  }, 5 * 60 * 1000);
}
['click', 'touchstart', 'input', 'keydown'].forEach(ev =>
  document.addEventListener(ev, resetInactivite, { capture: true, passive: true }));
resetInactivite();

// ═══ Chargements ════════════════════════════════════════════
async function chargerPersonnel() {
  try {
    const rows = await apiFetch('/api/admin/personnel');
    state.personnel = (rows ?? [])
      .filter(p => p.actif !== 0 && p.actif !== false)
      .sort((a, b) => (a.prenom ?? '').localeCompare(b.prenom ?? '', 'fr'));
  } catch (err) {
    console.warn('[cuisson] Personnel KO :', err);
  }
}

async function chargerProduits() {
  try {
    state.produits = await apiFetch('/api/cuisson/produits-disponibles') ?? [];
  } catch (err) {
    state.produits = [];
    console.warn('[cuisson] Produits KO :', err);
  }
}

async function chargerFiches() {
  try {
    state.fiches = await apiFetch('/api/cuisson/fiches');
  } catch (err) {
    elListeAC.innerHTML = `<div class="cu-erreur">Erreur : ${escHtml(err.message)}</div>`;
    return;
  }
  afficherAccueil();
}

// ═══ Accueil ════════════════════════════════════════════════
function ligneCuisson(f) {
  if (f.heure_fin == null) return '';
  const ok = f.conforme === 1;
  const type = TYPES_CUISSON[f.type_cuisson] ? `${TYPES_CUISSON[f.type_cuisson]} · ` : '';
  return `<span class="${ok ? 'cu-ok' : 'cu-ko'}">🔥 ${type}${escHtml(f.heure_debut)}→${escHtml(f.heure_fin)} · ${Number(f.temperature_sortie).toFixed(1)} °C${ok ? '' : ' ⚠'}</span>`;
}

function ligneRefroid(f) {
  if (f.refroid_id) {
    const ok = f.refroid_conforme === 1;
    const jete = f.refroid_jeter === 1 ? ' ⛔ jeté' : '';
    return `<span class="${ok ? 'cu-ok' : 'cu-ko'}">❄ ${escHtml(f.refroid_debut)}→${escHtml(f.refroid_fin)} (${formatDuree(f.refroid_duree)}) · ${Number(f.refroid_temperature).toFixed(1)} °C${jete}</span>`;
  }
  if (f.suite === 'vendu_chaud') return '<span>🔥 Vendu chaud</span>';
  if (f.devenir_statut) return '<span>Sorti du stock</span>';
  return '';
}

const ETATS = {
  cuisson_a_saisir:         '🔥 Cuisson à saisir',
  suite_a_choisir:          '❓ Refroidi ou vendu chaud ?',
  refroidissement_a_saisir: '❄ Refroidissement à saisir',
};

function carteFiche(f, terminee) {
  const veille = !terminee && f.date_cuisson < aujourdhuiISO()
    ? ' <span class="cu-badge-veille">⚠ pas d\'aujourd\'hui</span>' : '';
  const meta = [
    f.numero_lot ? `Lot ${escHtml(f.numero_lot)}` : null,
    formatJour(f.date_cuisson),
    f.personnel_nom ? `par ${escHtml(f.personnel_nom)}` : null,
  ].filter(Boolean).join(' · ');
  const lignes = [ligneCuisson(f), ligneRefroid(f)].filter(Boolean).join('<br>');
  const action = terminee
    ? (f.refroid_jeter === 1 || f.heure_fin == null ? ''
       : `<button type="button" class="cu-btn-secondaire" data-etiquette="${f.id}">🖨 Étiquette</button>`)
    : `<button type="button" class="cu-btn-primaire cu-btn-petit" data-completer="${f.id}">Compléter →</button>`;
  const poubelle = `<button type="button" class="cu-btn-poubelle" data-supprimer="${f.id}"
                     aria-label="Supprimer la fiche" title="Supprimer la fiche">🗑</button>`;
  return `
    <div class="cu-fiche-carte${terminee ? ' cu-fiche-carte--terminee' : ''}">
      <div class="cu-fiche-info">
        <div class="cu-fiche-nom">${escHtml(f.produit_nom ?? '—')}${veille}</div>
        <div class="cu-fiche-meta">${meta}</div>
        ${lignes ? `<div class="cu-fiche-lignes">${lignes}</div>` : ''}
        ${terminee ? '' : `<div class="cu-fiche-etat">${ETATS[f.etat] ?? ''}</div>`}
      </div>
      <div class="cu-fiche-action">${action}${poubelle}</div>
    </div>`;
}

function afficherAccueil() {
  const { a_completer: ac = [], terminees: te = [] } = state.fiches;
  elNbAC.textContent   = ac.length ? `(${ac.length})` : '';
  elNbTerm.textContent = te.length ? `(${te.length})` : '';
  elListeAC.innerHTML = ac.length
    ? ac.map(f => carteFiche(f, false)).join('')
    : '<div class="cu-vide">Rien à compléter. 👍</div>';
  elListeTerm.innerHTML = te.length
    ? te.map(f => carteFiche(f, true)).join('')
    : '<div class="cu-vide">Aucune fiche terminée ces 7 derniers jours.</div>';
}

function ficheParId(id) {
  const { a_completer: ac = [], terminees: te = [] } = state.fiches;
  return ac.concat(te).find(x => x.id === id) ?? null;
}

[elListeAC, elListeTerm].forEach(el => el.addEventListener('click', e => {
  const btn = e.target.closest('[data-supprimer]');
  if (!btn) return;
  const f = ficheParId(Number(btn.dataset.supprimer));
  if (f) ouvrirSuppression(f);
}));

elListeAC.addEventListener('click', e => {
  const btn = e.target.closest('[data-completer]');
  if (!btn) return;
  const f = state.fiches.a_completer.find(x => x.id === Number(btn.dataset.completer));
  if (f) ouvrirFiche(f);
});

elListeTerm.addEventListener('click', async e => {
  const btn = e.target.closest('[data-etiquette]');
  if (!btn) return;
  const f = state.fiches.terminees.find(x => x.id === Number(btn.dataset.etiquette));
  if (!f) return;
  btn.disabled = true;
  try { await imprimer(f, f.personnel_id); } finally { btn.disabled = false; }
});

$('cu-btn-nouvelle').addEventListener('click', () => ouvrirFiche(null));

function montrerAccueil() {
  elVueFiche.hidden = true;
  elVueAccueil.hidden = false;
  window.scrollTo({ top: 0 });
}

// ═══ Fiche ═════════════════════════════════════════════════
function cuissonDejaTerminee() {
  return !!(state.fiche && state.fiche.heure_fin != null);
}

function ouvrirFiche(fiche, prefill = null) {
  state.fiche = fiche;
  state.produit = null;
  state.lots = [];
  state.devient = null;
  state.suite = fiche?.suite ?? '';
  state.degre = fiche?.degre_cuisson ?? 'generale';
  state.typeCuisson = fiche?.type_cuisson
    ?? localStorage.getItem(CLE_TYPE_DEFAUT) ?? 'four';
  majType();
  state.refroidDebutManuel = false;
  state.operateurId = null;

  elForm.reset();
  elErreur.hidden = true;
  elProduitSuggest.hidden = true;
  elDevientWrap.hidden = true;
  elLotWrap.hidden = true;
  elJeter.checked = false;
  elQuickCuisson.querySelectorAll('.cu-quick-btn').forEach(b => b.classList.remove('cu-quick-btn--actif'));
  elQuickRefroid.querySelectorAll('.cu-quick-btn').forEach(b => b.classList.remove('cu-quick-btn--actif'));

  afficherOperateurs();

  if (fiche) {
    // Fiche existante : le produit et le lot sont déjà tracés.
    elProduitChoix.hidden = true;
    elProduitResume.hidden = false;
    elProduitResume.innerHTML = `
      <div class="cu-produit-resume-nom">${escHtml(fiche.produit_nom ?? '—')}</div>
      <div class="cu-produit-resume-meta">
        ${fiche.article_nom && fiche.article_nom !== fiche.produit_nom ? `Matière : ${escHtml(fiche.article_nom)} · ` : ''}
        Lot ${escHtml(fiche.numero_lot ?? '—')}${fiche.dlc_lot ? ` · DLC lot ${formatDate(fiche.dlc_lot)}` : ''}
        ${fiche.personnel_nom ? ` · ouverte par ${escHtml(fiche.personnel_nom)}` : ''}
      </div>`;
    elDate.value = fiche.date_cuisson;
    if (fiche.quantite != null) elQuantite.value = fiche.quantite;
    if (fiche.unite) elUnite.value = fiche.unite;
    elDegreWrap.hidden = !ESPECES_DEGRE.includes(fiche.espece);
  } else {
    elProduitChoix.hidden = false;
    elProduitResume.hidden = true;
    elDate.value = aujourdhuiISO();
    elDegreWrap.hidden = true;
  }

  $('cu-btn-supprimer').hidden = !fiche;
  const figee = cuissonDejaTerminee();
  elDate.disabled = figee;
  elQuantite.disabled = figee;
  elUnite.disabled = figee;
  elCuissonSaisie.hidden = figee;
  elCuissonResume.hidden = !figee;
  if (figee) {
    elCuissonResume.innerHTML = `${ligneCuisson(fiche)}
      <span class="cu-aide">Cuisson enregistrée — elle n'est plus modifiable.</span>`;
  } else if (fiche) {
    if (fiche.heure_debut) elHeureDebut.value = fiche.heure_debut;
  }

  majDegre();
  majSuite();
  majCuisson();

  elVueAccueil.hidden = true;
  elVueFiche.hidden = false;
  window.scrollTo({ top: 0 });

  if (prefill) appliquerPrefill(prefill);
}

$('cu-btn-annuler').addEventListener('click', montrerAccueil);
$('cu-btn-supprimer').addEventListener('click', () => { if (state.fiche) ouvrirSuppression(state.fiche); });

// ── Opérateur ──────────────────────────────────────────────
function afficherOperateurs() {
  if (!state.personnel.length) {
    elOperateurs.innerHTML = '<span class="cu-aide">Aucun opérateur actif.</span>';
    return;
  }
  elOperateurs.innerHTML = state.personnel.map(p => `
    <button type="button" class="cu-pastille${state.operateurId === p.id ? ' cu-pastille--actif' : ''}"
            data-op-id="${p.id}">${escHtml([p.prenom, p.nom].filter(Boolean).join(' '))}</button>`).join('');
}

elOperateurs.addEventListener('click', e => {
  const b = e.target.closest('[data-op-id]');
  if (!b) return;
  state.operateurId = Number(b.dataset.opId);
  elOperateurs.querySelectorAll('.cu-pastille').forEach(x => x.classList.toggle('cu-pastille--actif', x === b));
});

function nomOperateur(id) {
  const p = state.personnel.find(x => x.id === id);
  return p ? [p.prenom, p.nom].filter(Boolean).join(' ') : '';
}

// ── Produit (nouvelle fiche) ───────────────────────────────
function afficherSuggestions() {
  const needle = elProduitSearch.value.trim().toUpperCase();
  const liste = state.produits
    .filter(p => !needle || (p.nom ?? '').toUpperCase().includes(needle))
    .sort((a, b) => (a.dlc ?? '9999').localeCompare(b.dlc ?? '9999'))
    .slice(0, 40);
  elProduitSuggest.innerHTML = liste.length
    ? liste.map(p => `
        <button type="button" class="cu-suggest-item" data-cle-type="${escHtml(p.cle_type)}" data-cle-id="${p.cle_id}">
          <span class="cu-suggest-nom">${escHtml(p.nom)}</span>
          ${p.dlc ? `<span class="cu-suggest-dlc">DLC ${formatDate(p.dlc)}</span>` : ''}
        </button>`).join('')
    : '<div class="cu-suggest-vide">Aucun produit en stock ne correspond.</div>';
  elProduitSuggest.hidden = false;
}

elProduitSearch.addEventListener('input', afficherSuggestions);
elProduitSearch.addEventListener('focus', afficherSuggestions);
document.addEventListener('click', e => {
  if (!e.target.closest('.cu-recherche')) elProduitSuggest.hidden = true;
});

elProduitSuggest.addEventListener('click', e => {
  const b = e.target.closest('[data-cle-id]');
  if (!b) return;
  const prod = state.produits.find(p => p.cle_type === b.dataset.cleType && p.cle_id === Number(b.dataset.cleId));
  if (prod) choisirProduit(prod);
});

async function choisirProduit(prod, opts = {}) {
  state.produit = prod;
  state.devient = null;
  elProduitSearch.value = prod.nom;
  elProduitSuggest.hidden = true;
  elDegreWrap.hidden = !ESPECES_DEGRE.includes(prod.espece);
  state.degre = 'generale';
  majDegre();

  // Lots disponibles, FIFO en tête (le serveur trie par DLC croissante).
  const champ = prod.cle_type === 'achat' ? 'catalogue_fournisseur_id'
              : prod.cle_type === 'vente' ? 'catalogue_vente_id' : 'produit_id';
  elLotWrap.hidden = false;
  elLot.innerHTML = '<option>Chargement…</option>';
  try {
    state.lots = await apiFetch(`/api/cuisson/lots?${champ}=${prod.cle_id}&limit=100`) ?? [];
  } catch (err) {
    state.lots = [];
    afficherErreur(`Lots indisponibles : ${err.message}`);
  }
  elLot.innerHTML = state.lots.length
    ? state.lots.map((l, i) => {
        const cle = `${l.source_type}:${l.source_id}`;
        const verbe = l.source_type === 'fabrication' ? 'fabriqué' : 'reçu';
        const label = [
          i === 0 && state.lots.length > 1 ? '⭐ FIFO —' : '',
          `Lot ${l.numero_lot ?? '—'}`,
          `· DLC ${formatDate(l.dlc)}`,
          `· ${verbe} le ${formatDate(l.date_reception)}`,
          l.fournisseur_nom ? `· ${l.fournisseur_nom}` : '',
        ].filter(Boolean).join(' ');
        return `<option value="${escHtml(cle)}">${escHtml(label)}</option>`;
      }).join('')
    : '<option value="">Aucun lot disponible</option>';
  if (opts.reception_ligne_id) {
    const cle = `reception_ligne:${opts.reception_ligne_id}`;
    if (state.lots.some(l => `${l.source_type}:${l.source_id}` === cle)) elLot.value = cle;
  }

  // Matière brute du catalogue ACHATS : on demande ce qu'elle devient (catalogue VENTE).
  const cvConnu = prod.catalogue_vente_id ?? opts.catalogue_vente_id ?? null;
  if (prod.cle_type === 'achat' && !cvConnu) {
    await chargerDevient(prod);
  } else {
    elDevientWrap.hidden = true;
    if (cvConnu) state.devient = { id: Number(cvConnu), nom: prod.nom };
  }
}

function lotChoisi() {
  return state.lots.find(l => `${l.source_type}:${l.source_id}` === elLot.value) ?? null;
}

$('cu-btn-receptions').addEventListener('click', () => {
  if (!state.produit) return;
  elModalTitre.textContent = `Réceptions — ${state.produit.nom}`;
  elModalCorps.innerHTML = state.lots.length
    ? state.lots.map(l => `
        <div class="cu-histo-ligne">
          <div class="cu-histo-date">${formatDate(l.date_reception)}</div>
          <div class="cu-histo-info">
            <strong>Lot :</strong> ${escHtml(l.numero_lot ?? '—')}
            · <strong>DLC :</strong> ${formatDate(l.dlc)}
            ${l.poids_kg ? ` · ${l.poids_kg} kg` : ''}
            ${l.fournisseur_nom ? `<br><small>${escHtml(l.fournisseur_nom)}</small>` : ''}
            ${l.reception_id ? `<br><a href="/reception-detail.html?id=${l.reception_id}" class="cu-lien">→ Fiche réception</a>` : ''}
          </div>
        </div>`).join('')
    : '<div class="cu-vide">Aucun lot disponible pour ce produit.</div>';
  elModal.hidden = false;
});
$('cu-modal-close').addEventListener('click', () => { elModal.hidden = true; });
elModal.addEventListener('click', e => { if (e.target === elModal) elModal.hidden = true; });

// ── « Devient » : matière brute → produit du catalogue vente ─
async function chargerDevient(prod) {
  elDevientWrap.hidden = false;
  elDevientSearch.value = '';
  elDevientChoix.innerHTML = '<span class="cu-aide">Chargement…</span>';
  let suggestions = [];
  try {
    const res = await apiFetch(`/api/cuisson/produits-vente-suggeres?catalogue_fournisseur_id=${prod.cle_id}`);
    if (res.dernier_choix) suggestions.push({ ...res.dernier_choix, dernier: true });
    (res.groupe ?? []).forEach(g => { if (!suggestions.some(s => s.id === g.id)) suggestions.push(g); });
    // Présélection : le dernier choix pour cet article, ou l'unique produit du groupe.
    const auto = res.dernier_choix ?? (res.groupe?.length === 1 ? res.groupe[0] : null);
    if (auto) state.devient = { id: auto.id, nom: auto.nom };
  } catch (err) {
    console.warn('[cuisson] Suggestions produit fini KO :', err);
  }
  afficherDevient(suggestions);
}

function afficherDevient(liste) {
  elDevientChoix.innerHTML = liste.length
    ? liste.map(p => `
        <button type="button" class="cu-pastille${state.devient?.id === p.id ? ' cu-pastille--actif' : ''}"
                data-pf-id="${p.id}" data-pf-nom="${escHtml(p.nom)}">${p.dernier ? '⭐ ' : ''}${escHtml(p.nom)}</button>`).join('')
    : '<span class="cu-aide">Aucune suggestion — cherchez le produit ci-dessous.</span>';
}

elDevientChoix.addEventListener('click', e => {
  const b = e.target.closest('[data-pf-id]');
  if (!b) return;
  state.devient = { id: Number(b.dataset.pfId), nom: b.dataset.pfNom };
  elDevientChoix.querySelectorAll('.cu-pastille').forEach(x => x.classList.toggle('cu-pastille--actif', x === b));
});

let devientTimer = null;
elDevientSearch.addEventListener('input', () => {
  clearTimeout(devientTimer);
  const terme = elDevientSearch.value;
  devientTimer = setTimeout(async () => {
    try {
      afficherDevient(await apiFetch(`/api/cuisson/produits-vente-recherche?q=${encodeURIComponent(terme)}`));
    } catch (err) {
      console.warn('[cuisson] Recherche produit fini KO :', err);
    }
  }, 250);
});

// ── Cuisson ────────────────────────────────────────────────
function majType() {
  elTypeChoix.querySelectorAll('[data-type]').forEach(b =>
    b.classList.toggle('cu-pastille--actif', b.dataset.type === state.typeCuisson));
}

elTypeChoix.addEventListener('click', e => {
  const b = e.target.closest('[data-type]');
  if (!b) return;
  state.typeCuisson = b.dataset.type;
  majType();
});

function cibleCuisson() {
  return DEGRES[state.degre] ?? 75;
}

function majDegre() {
  elDegreChoix.querySelectorAll('.cu-quick-btn').forEach(b =>
    b.classList.toggle('cu-quick-btn--actif', b.dataset.degre === state.degre));
  elCible.textContent = `Cible : ≥ ${cibleCuisson()} °C`;
}

elDegreChoix.addEventListener('click', e => {
  const b = e.target.closest('[data-degre]');
  if (!b) return;
  state.degre = b.dataset.degre;
  majDegre();
  majCuisson();
});

/** Boutons de durée : fin = début + durée ; si seul la fin est connue, début = fin − durée. */
function appliquerDuree(elDebut, elFin, quick, btn, quoi) {
  const duree = Number(btn.dataset.minutes);
  const d = minutes(elDebut.value), f = minutes(elFin.value);
  if (d != null) {
    const fin = hhmm(d + duree);
    if (!fin) return afficherErreur(`${quoi} : la fin tomberait après minuit.`);
    elFin.value = fin;
  } else if (f != null) {
    const debut = hhmm(f - duree);
    if (!debut) return afficherErreur(`${quoi} : le début tomberait la veille.`);
    elDebut.value = debut;
  } else {
    return afficherErreur(`${quoi} : saisissez d'abord l'heure de début ou de fin.`);
  }
  elErreur.hidden = true;
  quick.querySelectorAll('.cu-quick-btn').forEach(b => b.classList.toggle('cu-quick-btn--actif', b === btn));
}

elQuickCuisson.addEventListener('click', e => {
  const b = e.target.closest('[data-minutes]');
  if (!b) return;
  appliquerDuree(elHeureDebut, elHeureFin, elQuickCuisson, b, 'Cuisson');
  majCuisson();
});

[elHeureDebut, elHeureFin].forEach(el => el.addEventListener('input', () => {
  elQuickCuisson.querySelectorAll('.cu-quick-btn').forEach(b => b.classList.remove('cu-quick-btn--actif'));
  majCuisson();
}));
elTemperature.addEventListener('input', majCuisson);

/** Fin de cuisson connue (enregistrée ou saisie) : point de départ du refroidissement. */
function finCuisson() {
  return cuissonDejaTerminee() ? state.fiche.heure_fin : (elHeureFin.value || null);
}

function cuissonComplete() {
  return cuissonDejaTerminee() || (!!elHeureFin.value && nombre(elTemperature) != null);
}

function majCuisson() {
  if (!cuissonDejaTerminee()) {
    const d = minutes(elHeureDebut.value), f = minutes(elHeureFin.value);
    if (d != null && f != null) {
      elDureeCuisson.textContent = f > d ? `→ a cuit ${formatDuree(f - d)}` : '⚠ La fin est avant le début.';
      elDureeCuisson.classList.toggle('cu-duree--ko', f <= d);
    } else {
      elDureeCuisson.textContent = '';
    }
    const t = nombre(elTemperature);
    const cible = cibleCuisson();
    if (t == null) {
      elConformite.hidden = true;
      elActionWrap.hidden = true;
    } else {
      const ok = t >= cible;
      elConformite.hidden = false;
      elConformite.className = `cu-conformite ${ok ? 'cu-conformite--ok' : 'cu-conformite--ko'}`;
      elConformite.textContent = ok
        ? `✓ Conforme — ${t.toFixed(1)} °C ≥ ${cible} °C`
        : `⚠ Non conforme — ${t.toFixed(1)} °C < ${cible} °C — action corrective requise`;
      elActionWrap.hidden = ok;
      if (!ok && !elAction.value.trim()) {
        elAction.value = `Remise en cuisson jusqu'à ${cible} °C à cœur`;
      }
    }
  }

  // Mise au froid = fin de cuisson, tant que l'opérateur ne l'a pas changée.
  const fin = finCuisson();
  if (!state.refroidDebutManuel) elRefroidDebut.value = fin ?? '';
  majSuite();
  majRefroid();
}

// ── Ensuite ────────────────────────────────────────────────
function majSuite() {
  const complete = cuissonComplete();
  const verrouillee = !!(state.fiche && state.fiche.suite);   // suite déjà enregistrée
  elBlocSuite.querySelectorAll('.cu-suite-btn').forEach(b => {
    b.classList.toggle('cu-suite-btn--actif', b.dataset.suite === state.suite);
    b.disabled = verrouillee || (!complete && b.dataset.suite !== '');
  });
  if (!complete && state.suite) state.suite = '';
  elSuiteAide.textContent = verrouillee
    ? 'Suite déjà enregistrée.'
    : complete ? '« Plus tard » garde la fiche dans « À compléter ».'
               : 'Terminez la cuisson (heure de fin + T°) pour choisir la suite.';
  elBlocRefroid.hidden = state.suite !== 'refroidi';
}

elBlocSuite.addEventListener('click', e => {
  const b = e.target.closest('.cu-suite-btn');
  if (!b || b.disabled) return;
  state.suite = b.dataset.suite;
  majSuite();
  majRefroid();
});

// ── Refroidissement ────────────────────────────────────────
elQuickRefroid.addEventListener('click', e => {
  const b = e.target.closest('[data-minutes]');
  if (!b) return;
  appliquerDuree(elRefroidDebut, elRefroidFin, elQuickRefroid, b, 'Refroidissement');
  majRefroid();
});

elRefroidDebut.addEventListener('input', () => {
  state.refroidDebutManuel = true;
  elQuickRefroid.querySelectorAll('.cu-quick-btn').forEach(b => b.classList.remove('cu-quick-btn--actif'));
  majRefroid();
});
elRefroidFin.addEventListener('input', () => {
  elQuickRefroid.querySelectorAll('.cu-quick-btn').forEach(b => b.classList.remove('cu-quick-btn--actif'));
  majRefroid();
});
elRefroidTemp.addEventListener('input', majRefroid);

function etatRefroid() {
  const d = minutes(elRefroidDebut.value), f = minutes(elRefroidFin.value);
  const duree = (d != null && f != null && f > d) ? f - d : null;
  const t = nombre(elRefroidTemp);
  const tempOk = t == null ? null : t <= TEMP_CIBLE_REFROID;
  const dureeOk = duree == null ? null : duree <= DUREE_MAX_REFROID;
  return { d, f, duree, t, tempOk, dureeOk, jeter: tempOk === false && dureeOk === false };
}

function majRefroid() {
  const r = etatRefroid();
  const fc = minutes(finCuisson());

  // Écart sortie de cuisson → mise au froid
  if (r.d != null && fc != null && r.d < fc) {
    elRefroidDebutAide.textContent = '⚠ Avant la fin de la cuisson.';
    elRefroidDebutAide.className = 'cu-aide cu-aide--ko';
  } else if (r.d != null && fc != null && r.d - fc > ECART_MAX_MISE_AU_FROID) {
    elRefroidDebutAide.textContent = `⚠ ${formatDuree(r.d - fc)} après la sortie de cuisson : à mettre au froid sans attendre.`;
    elRefroidDebutAide.className = 'cu-aide cu-aide--alerte';
  } else {
    elRefroidDebutAide.textContent = fc != null && !state.refroidDebutManuel ? '= fin de cuisson' : '';
    elRefroidDebutAide.className = 'cu-aide';
  }

  if (r.d != null && r.f != null) {
    elDureeRefroid.textContent = r.f > r.d ? `→ a refroidi ${formatDuree(r.f - r.d)}` : '⚠ La fin est avant la mise au froid.';
    elDureeRefroid.classList.toggle('cu-duree--ko', r.f <= r.d || r.dureeOk === false);
  } else {
    elDureeRefroid.textContent = '';
  }

  if (r.t == null || r.duree == null) {
    elRefroidConf.hidden = true;
    elRefroidActionWrap.hidden = true;
    elJeterWrap.hidden = true;
    return;
  }
  const ok = r.tempOk && r.dureeOk;
  elRefroidConf.hidden = false;
  elRefroidConf.className = `cu-conformite ${ok ? 'cu-conformite--ok' : 'cu-conformite--ko'}`;
  const ko = [];
  if (!r.tempOk) ko.push(`${r.t.toFixed(1)} °C > ${TEMP_CIBLE_REFROID} °C`);
  if (!r.dureeOk) ko.push(`${formatDuree(r.duree)} > 2 h`);
  elRefroidConf.textContent = ok
    ? `✓ Conforme — ${r.t.toFixed(1)} °C en ${formatDuree(r.duree)}`
    : r.jeter ? `⛔ ${ko.join(' et ')} : le produit doit être JETÉ`
              : `⚠ Non conforme — ${ko.join(' · ')} — action corrective requise`;
  elJeterWrap.hidden = !r.jeter;
  if (!r.jeter) elJeter.checked = false;
  elRefroidActionWrap.hidden = ok || r.jeter;
}

// ═══ Enregistrement ════════════════════════════════════════
function afficherErreur(msg) {
  elErreur.textContent = msg;
  elErreur.hidden = false;
  elErreur.scrollIntoView({ behavior: 'smooth', block: 'center' });
  return null;
}

function afficherToast(message, ok = true) {
  elToast.textContent = message;
  elToast.classList.toggle('cu-toast--ko', !ok);
  elToast.hidden = false;
  requestAnimationFrame(() => elToast.classList.add('cu-toast--visible'));
  setTimeout(() => {
    elToast.classList.remove('cu-toast--visible');
    setTimeout(() => { elToast.hidden = true; }, 300);
  }, 3500);
}

/** Contrôles avant envoi (le serveur refait les mêmes) → payload, ou null. */
function construirePayload() {
  if (!state.operateurId) return afficherErreur('Indiquez qui saisit la fiche.');
  const fiche = state.fiche;
  const payload = { personnel_id: state.operateurId };
  const figee = cuissonDejaTerminee();

  if (!figee) {
    const date = elDate.value;
    if (!date) return afficherErreur('Date de la cuisson requise.');
    if (date > aujourdhuiISO()) return afficherErreur('La date de cuisson est dans le futur.');
    payload.date_cuisson = date;
    const q = nombre(elQuantite);
    if (q != null) payload.quantite = q;
    payload.unite = elUnite.value || 'kg';
  }

  if (!fiche) {
    const p = state.produit;
    if (!p) return afficherErreur('Choisissez le produit cuit.');
    const lot = lotChoisi();
    if (state.lots.length && !lot) return afficherErreur('Choisissez le lot utilisé.');
    if (!elDevientWrap.hidden && !state.devient) return afficherErreur('Indiquez ce que devient le produit (catalogue vente).');
    Object.assign(payload, {
      produit_id:               p.id ?? null,
      catalogue_fournisseur_id: p.catalogue_fournisseur_id ?? null,
      catalogue_vente_id:       state.devient?.id ?? p.catalogue_vente_id ?? null,
      reception_ligne_id:       lot?.source_type === 'reception_ligne' ? lot.source_id : null,
      fabrication_id:           lot?.source_type === 'fabrication' ? lot.source_id : null,
      lot_epuise:               !!lot && elLotEpuise.checked,
    });
  }

  // Cuisson
  if (!figee) {
    const debut = elHeureDebut.value || null;
    const fin = elHeureFin.value || null;
    const t = nombre(elTemperature);
    if ((fin || t != null) && !(debut && fin && t != null)) {
      return afficherErreur('Pour terminer la cuisson : début, fin ET T° à cœur. Sinon laissez fin et T° vides.');
    }
    if (debut && fin && minutes(fin) <= minutes(debut)) return afficherErreur('Cuisson : la fin est avant le début.');
    if (payload.date_cuisson === aujourdhuiISO()) {
      const maintenant = new Date().getHours() * 60 + new Date().getMinutes();
      if ([debut, fin].some(h => h && minutes(h) > maintenant + 5)) {
        return afficherErreur("Cuisson : heure dans le futur. Saisissez l'heure réelle.");
      }
    }
    if (t != null && t < cibleCuisson() && !elAction.value.trim()) {
      return afficherErreur(`Action corrective obligatoire (T° < ${cibleCuisson()} °C).`);
    }
    Object.assign(payload, {
      type_cuisson:       state.typeCuisson,
      heure_debut:        debut,
      heure_fin:          fin,
      temperature_sortie: t,
      degre_cuisson:      state.degre,
      action_corrective:  t != null && t < cibleCuisson() ? elAction.value.trim() : null,
    });
  }

  // Suite
  if (state.suite && !(fiche && fiche.suite)) payload.suite = state.suite;

  // Refroidissement : envoyé dès que fin ou T° est saisie (sinon reste « à saisir »).
  if (state.suite === 'refroidi') {
    const r = etatRefroid();
    const saisi = elRefroidFin.value || r.t != null;
    if (saisi) {
      if (!(elRefroidDebut.value && elRefroidFin.value && r.t != null)) {
        return afficherErreur('Refroidissement : mise au froid, fin ET T° à cœur. Sinon laissez fin et T° vides.');
      }
      if (r.f <= r.d) return afficherErreur('Refroidissement : la fin est avant la mise au froid.');
      const fc = minutes(finCuisson());
      if (fc != null && r.d < fc) return afficherErreur('Refroidissement : la mise au froid est avant la fin de la cuisson.');
      const dateRef = payload.date_cuisson ?? fiche?.date_cuisson;
      if (dateRef === aujourdhuiISO()) {
        const maintenant = new Date().getHours() * 60 + new Date().getMinutes();
        if (r.f > maintenant + 5) return afficherErreur("Refroidissement : heure de fin dans le futur. Saisissez l'heure réelle.");
      }
      const ok = r.tempOk && r.dureeOk;
      if (r.jeter && !elJeter.checked) return afficherErreur('Plus de 2 h et plus de 10 °C : cochez la confirmation « produit jeté ».');
      if (!ok && !r.jeter && !elRefroidAction.value.trim()) return afficherErreur('Refroidissement non conforme : action corrective obligatoire.');
      payload.refroidissement = {
        heure_debut:        elRefroidDebut.value,
        heure_fin:          elRefroidFin.value,
        temperature_finale: r.t,
        jeter_action:       r.jeter,
        action_corrective:  r.jeter
          ? ['Produit jeté', elRefroidAction.value.trim()].filter(Boolean).join(' — ')
          : (ok ? null : elRefroidAction.value.trim()),
      };
    }
  }
  return payload;
}

async function enregistrer(avecEtiquette) {
  if (state.envoiEnCours) return;
  elErreur.hidden = true;
  const payload = construirePayload();
  if (!payload) return;

  state.envoiEnCours = true;
  [elBtnSave, elBtnSaveEtiq].forEach(b => { b.disabled = true; });
  try {
    if (payload.type_cuisson) localStorage.setItem(CLE_TYPE_DEFAUT, payload.type_cuisson);
    const fiche = state.fiche
      ? await apiFetch(`/api/cuisson/fiches/${state.fiche.id}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      : await apiFetch('/api/cuisson/fiches', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });

    const nonConforme = fiche.conforme === 0 || fiche.refroid_conforme === 0;
    const message = fiche.refroid_jeter === 1 ? '⛔ Enregistré — produit à jeter'
      : fiche.etat === 'terminee' ? `✓ Fiche terminée${nonConforme ? ' — non conforme' : ''}`
      : `✓ Enregistré — reste : ${(ETATS[fiche.etat] ?? '').replace(/^\S+\s/, '').toLowerCase()}`;
    afficherToast(message, !nonConforme && fiche.refroid_jeter !== 1);

    if (avecEtiquette) await imprimer(fiche, state.operateurId);
    await Promise.all([chargerFiches(), chargerProduits()]);
    montrerAccueil();
  } catch (err) {
    afficherErreur(err.message);
  } finally {
    state.envoiEnCours = false;
    [elBtnSave, elBtnSaveEtiq].forEach(b => { b.disabled = false; });
  }
}

elForm.addEventListener('submit', e => { e.preventDefault(); enregistrer(false); });
elBtnSaveEtiq.addEventListener('click', () => enregistrer(true));

// ── Suppression ────────────────────────────────────────────
const elModalSuppr   = $('cu-modal-suppr');
const elSupprMdpWrap = $('cu-suppr-mdp-wrap');
const elSupprMdp     = $('cu-suppr-mdp');
const elSupprMotif   = $('cu-suppr-motif');
const elSupprErreur  = $('cu-suppr-erreur');
const elSupprOk      = $('cu-suppr-confirmer');
let ficheASupprimer = null;

/** Sans heure de fin, T° ni refroidissement : rien du registre n'est effacé. */
function ficheSansMesure(f) {
  return f.heure_fin == null && f.temperature_sortie == null && !f.refroid_id;
}

function ouvrirSuppression(f) {
  ficheASupprimer = f;
  const lignes = [ligneCuisson(f), ligneRefroid(f)].filter(Boolean).join('<br>');
  $('cu-suppr-resume').innerHTML = `
    <div class="cu-produit-resume-nom">${escHtml(f.produit_nom ?? '—')}</div>
    <div class="cu-produit-resume-meta">Lot ${escHtml(f.numero_lot ?? '—')} · ${formatJour(f.date_cuisson)}</div>
    ${lignes ? `<div class="cu-fiche-lignes">${lignes}</div>` : ''}`;
  const libre = ficheSansMesure(f);
  $('cu-suppr-explication').textContent = libre
    ? "Aucune mesure n'a encore été saisie sur cette fiche. Le lot cru, s'il avait été sorti du stock, y revient."
    : 'Cette fiche contient des mesures du registre HACCP (cuisson et/ou refroidissement) : '
      + "la suppression est définitive et demande le mot de passe administrateur. Le lot cru, s'il avait été sorti du stock, y revient.";
  elSupprMdpWrap.hidden = libre;
  elSupprMdp.value = '';
  elSupprMotif.value = '';
  elSupprErreur.hidden = true;
  elModalSuppr.hidden = false;
  (libre ? elSupprMotif : elSupprMdp).focus();
}

function fermerSuppression() {
  elModalSuppr.hidden = true;
  ficheASupprimer = null;
}
$('cu-suppr-annuler').addEventListener('click', fermerSuppression);
$('cu-suppr-fermer').addEventListener('click', fermerSuppression);

elSupprOk.addEventListener('click', async () => {
  const f = ficheASupprimer;
  if (!f) return;
  if (!elSupprMdpWrap.hidden && !elSupprMdp.value) {
    elSupprErreur.textContent = 'Mot de passe administrateur requis.';
    elSupprErreur.hidden = false;
    return;
  }
  elSupprOk.disabled = true;
  try {
    await apiFetch(`/api/cuisson/fiches/${f.id}/supprimer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        password: elSupprMdpWrap.hidden ? null : elSupprMdp.value,
        motif: elSupprMotif.value.trim() || null,
      }),
    });
    fermerSuppression();
    afficherToast('🗑 Fiche supprimée', true);
    await Promise.all([chargerFiches(), chargerProduits()]);
    montrerAccueil();
  } catch (err) {
    elSupprErreur.textContent = err.message;
    elSupprErreur.hidden = false;
  } finally {
    elSupprOk.disabled = false;
  }
});

// ── Étiquette ──────────────────────────────────────────────
function remplirGabaritEtiquette(data) {
  const fmt = iso => {
    if (!iso) return '--/--/--';
    const [y, m, d] = iso.split('-');
    return `${d}/${m}/${(y || '').slice(-2)}`;
  };
  const heure = (data.heure_action || '').replace(':', 'h');
  $('pt-tag').textContent = `[${data.tag}]`;
  $('pt-nom').textContent = data.produit_nom || '—';
  $('pt-quantite').textContent = (data.quantite != null && data.quantite !== '')
    ? `Quantité : ${data.quantite} ${data.unite || 'kg'}` : 'Quantité : —';
  $('pt-dlc').textContent = fmt(data.dlc);
  $('pt-lot').textContent = `Lot : ${data.numero_lot || '—'}`;
  $('pt-temperature').textContent = (data.temperature != null && data.temperature !== '')
    ? `${data.temp_label || 'T°'} : ${parseFloat(data.temperature).toFixed(1)} °C`
    : `${data.temp_label || 'T°'} : —`;
  $('pt-action').textContent = `${data.action_verbe} le ${fmt(data.date_action)}${heure ? ` à ${heure}` : ''}`;
  $('pt-meta').textContent = `Par : ${data.operateur || '—'}`;
}

/** Étiquette du dernier maillon : REFROIDI s'il existe, sinon CUIT. */
async function imprimer(fiche, personnelId) {
  if (fiche.refroid_jeter === 1) return afficherToast('Produit jeté : pas d\'étiquette.', false);
  const source = fiche.refroid_id
    ? { source_type: 'refroidissement', source_id: fiche.refroid_id }
    : fiche.heure_fin != null ? { source_type: 'cuisson', source_id: fiche.id } : null;
  if (!source) return afficherToast("Pas d'étiquette tant que la cuisson n'est pas terminée.", false);
  try {
    const res = await apiFetch('/api/etiquettes/transformes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...source, personnel_id: Number(personnelId) }),
    });
    remplirGabaritEtiquette(res);
    afficherToast(`✓ Étiquette envoyée (Lot ${res.numero_lot})`, true);
    imprimerEtiquette($('print-label-transforme'));
  } catch (err) {
    afficherToast(`Erreur impression : ${err.message}`, false);
  }
}

// ── Pré-remplissage (Production > À cuire) ─────────────────
function appliquerPrefill(data) {
  const prod = state.produits.find(p =>
       (data.catalogue_fournisseur_id != null && Number(p.catalogue_fournisseur_id) === Number(data.catalogue_fournisseur_id))
    || (data.catalogue_vente_id != null && Number(p.catalogue_vente_id) === Number(data.catalogue_vente_id))
    || (data.produit_id != null && p.id != null && Number(p.id) === Number(data.produit_id)));
  if (prod) {
    choisirProduit(prod, {
      catalogue_vente_id: data.catalogue_vente_id ?? null,
      reception_ligne_id: data.reception_ligne_id ?? null,
    });
  } else if (data.produit_nom) {
    afficherErreur(`« ${data.produit_nom} » n'est plus en stock (lot périmé ou sorti).`);
  }
}

// ── Go ──────────────────────────────────────────────────────
async function init() {
  await Promise.all([chargerPersonnel(), chargerProduits(), chargerFiches()]);
  const prefillRaw = sessionStorage.getItem('cuisson_prefill');
  if (prefillRaw) {
    sessionStorage.removeItem('cuisson_prefill');
    try { ouvrirFiche(null, JSON.parse(prefillRaw)); } catch { /* noop */ }
  }
}

init();

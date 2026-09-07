'use strict';
/* ============================================================
   nuisibles.js — Lutte contre Nuisibles (IPM)
   1 onglet par espèce active × 52 semaines × pièges installés sur le plan
   ============================================================ */

// ── Constantes types de nuisibles ────────────────────────────
// `actif: false` retire complètement l'espèce du module (onglet, registre,
// saisie rapide, plan). L'historique déjà saisi reste consultable dans
// /historique.html et les rapports. À garder aligné avec TYPES_DESACTIVES
// (src/api/routes_nuisibles.py) et NUISIBLES_TYPES_DESACTIVES (routes_hub.py).
const TYPES = [
  {
    id: 1,
    nom: 'Rongeurs',
    court: 'Rongeurs',        // libellé compact (onglets, filtres)
    emoji: '🐀',
    nuisibles: 'Souris, Rats, Mulots…',
    methodes:  '• Plaques de glue avec attractif\n• Rodenticide fluorescent dans boîte sécurisée',
    frequence: '• Inspection hebdomadaire des plaques de glue\n• Changement des pièges à glue et vérification des rodenticides tous les mois',
  },
  {
    id: 2,
    nom: 'Insectes Volants',
    court: 'Ins. Volants',
    emoji: '🪰',
    nuisibles: 'Mouches, Moucherons, Guêpes…',
    methodes:  '• DEIV à glu pour les zones alimentaires\n• DEIV à électrocution pour les zones non alimentaires',
    frequence: '• Plaque de glu — Période chaude (avril–septembre) : remplacement mensuel\n• Plaque de glu — Période froide (octobre–mars) : remplacement tous les 2 mois\n• Tubes UV : remplacement annuel',
  },
  {
    id: 3,
    nom: 'Insectes Rampants',
    court: 'Ins. Rampants',
    emoji: '🪳',
    nuisibles: 'Cafards, Fourmis…',
    methodes:  '• Piège à phéromones et à glu dans les zones critiques\n• Gel anti-cafard / fourmis dans boîte sécurisée',
    frequence: '• Inspection hebdomadaire des plaques de glue\n• Remplacer les plaques tous les 3 mois\n• Remplacer le gel tous les 3 mois',
  },
  {
    id: 4,
    nom: 'Oiseaux',
    court: 'Oiseaux',
    emoji: '🐦',
    nuisibles: 'Pigeons, Moineaux, Étourneaux…',
    methodes:  '• Pics anti-pigeons\n• Filets de protection',
    frequence: '• Inspection hebdomadaire des pics et filets\n• Nettoyage et désinfection immédiats en cas de présence de fientes',
    actif: false,   // désactivé — aucun dispositif oiseaux installé
  },
];

// Espèces réellement suivies : seule liste parcourue par le module.
const TYPES_ACTIFS = TYPES.filter(t => t.actif !== false);

// Nombre de pièges disponibles (P1..Pn) dans la palette du plan.
// Réglable via /api/nuisibles/config. Écrasé par chargerConfig() au démarrage.
let NB_PIEGES = 15;

// Pièges réellement installés sur le plan : { typeId: [1, 2, 5, ...] }.
// Renseigné par chargerPiegesCarte() et mis à jour à chaque enregistrement du plan.
let piegesParType = {};

// ── État ──────────────────────────────────────────────────────
let currentTypeId  = 1;
let currentAnnee   = new Date().getFullYear();
let currentSemaine = getISOWeek(new Date());
let donneesAnnee   = {};   // { "17": {resultats: {p1:"O",...}, visa:"Éric"}, ... }
let personnel      = [];

// Vue active : 'tableau' | 'carte'
let currentVue = 'tableau';

// Carte des pièges
let cartePositions = {};   // { piegeNum: {pos_x, pos_y}, ... } pour le type courant
let cartePiegeActif = null; // piège sélectionné dans la palette (à placer)
let carteDirty = false;     // modifications non enregistrées

// Édition simple (clic sur ligne tableau)
let editSemaine   = null;
let editResultats = {};    // {"p1": "O"/"N"/null, ...}

// Saisie rapide multi-espèce
let rapideSemaine   = null;
let rapideResultats = {};  // { typeId: { p1: val, ... }, ... }
let rapideDonnees   = {};  // { typeId: allYearData }

// Action globale portée
let globalNbPieges = NB_PIEGES;
let globalEspece   = 'all';  // 'all' | number (typeId)

// ── Références DOM ────────────────────────────────────────────
const elTabs             = document.getElementById('nu-tabs');
const elAnnee            = document.getElementById('nu-annee');
const elInfoWrap         = document.getElementById('nu-info-wrap');
const elInfoToggle       = document.getElementById('nu-info-toggle');
const elInfoCorps        = document.getElementById('nu-info-corps');
const elTbody            = document.getElementById('nu-tbody');
const elModal            = document.getElementById('nu-modal');
const elModalTitre       = document.getElementById('nu-modal-titre');
const elPiegeGrid        = document.getElementById('nu-piege-grid');
const elVisaSelect       = document.getElementById('nu-visa-select');
const elBtnAnnuler       = document.getElementById('nu-btn-annuler');
const elBtnSave          = document.getElementById('nu-btn-sauvegarder');
const elModalFermer      = document.getElementById('nu-modal-fermer');
const elToast            = document.getElementById('nu-toast');
const elFab              = document.getElementById('nu-fab-rapide');
const elFabSub           = document.getElementById('nu-fab-sub');
const elModalRapide      = document.getElementById('nu-modal-rapide');
const elModalRapideTitre = document.getElementById('nu-modal-rapide-titre');
const elVisaRapide       = document.getElementById('nu-visa-rapide');
const elRapideSections   = document.getElementById('nu-rapide-sections');
const elBtnRapideSave    = document.getElementById('nu-btn-rapide-save');
const elTheadRow         = document.getElementById('nu-thead-row');

// Vue / carte
const elVueTableauBtn    = document.getElementById('nu-vue-tableau');
const elVueCarteBtn      = document.getElementById('nu-vue-carte');
const elVueTableauCorps  = document.getElementById('nu-vue-tableau-corps');
const elVueCarteCorps    = document.getElementById('nu-vue-carte-corps');
const elCartePalette     = document.getElementById('nu-carte-palette');
const elCarteStage       = document.getElementById('nu-carte-stage');
const elCartePings       = document.getElementById('nu-carte-pings');
const elCarteHint        = document.getElementById('nu-carte-hint');
const elCarteReset       = document.getElementById('nu-carte-reset');
const elCarteSave        = document.getElementById('nu-carte-save');

// Config nb pièges
const elConfigBtn        = document.getElementById('nu-config-btn');
const elConfigLabel      = document.getElementById('nu-config-label');
const elModalConfig      = document.getElementById('nu-modal-config');

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initAnnees();
  initTabs();
  initInfoToggle();
  initModal();
  initModalRapide();
  initFab();
  initVueSwitch();
  initCarte();
  initConfig();
  chargerPersonnel();
  // NB_PIEGES (palette) puis pièges installés sur le plan : les deux
  // conditionnent les colonnes du registre → à charger avant le 1er rendu.
  await chargerConfig();
  await chargerPiegesCarte();
  renderTheadPieges();
  majConfigLabel();
  chargerDonnees();
});

// ── Chargement de la configuration (nombre de pièges) ─────────
async function chargerConfig() {
  try {
    const res = await fetch('/api/nuisibles/config');
    if (res.ok) {
      const data = await res.json();
      if (Number.isInteger(data.nb_pieges) && data.nb_pieges > 0) {
        NB_PIEGES = data.nb_pieges;
      }
    }
  } catch { /* on garde la valeur par défaut */ }
  globalNbPieges = NB_PIEGES;
}

// ── Pièges installés sur le plan (mémoire du module) ──────────
async function chargerPiegesCarte() {
  try {
    const res = await fetch('/api/nuisibles/carte/resume');
    if (res.ok) {
      const data = await res.json();
      piegesParType = data.pieges_par_type || {};
    }
  } catch { piegesParType = {}; }
}

/**
 * Numéros des pièges à saisir pour une espèce : ceux placés sur le plan.
 * Tant qu'aucun piège n'a été positionné, on retombe sur P1..NB_PIEGES pour
 * ne pas présenter un registre vide.
 */
function piegesDuType(typeId) {
  const liste = (piegesParType[String(typeId)] || [])
    .filter(n => n >= 1 && n <= NB_PIEGES)
    .sort((a, b) => a - b);
  if (liste.length) return liste;
  return Array.from({ length: NB_PIEGES }, (_, i) => i + 1);
}

// Nombre de pièges du plus grand jeu de pièges parmi les espèces actives
// (borne du stepper « N premiers pièges » de la saisie rapide).
function maxPiegesActifs() {
  return Math.max(...TYPES_ACTIFS.map(t => piegesDuType(t.id).length));
}

/**
 * Résultats d'une semaine prêts à l'édition : une entrée par piège installé,
 * les clés des pièges retirés du plan sont conservées telles quelles pour ne
 * pas effacer leur historique lors du prochain enregistrement.
 */
function initResultats(typeId, existants = {}) {
  const out = { ...existants };
  piegesDuType(typeId).forEach(num => {
    out[`p${num}`] = existants[`p${num}`] || null;
  });
  return out;
}

function majConfigLabel() {
  if (elConfigLabel) elConfigLabel.textContent = `${NB_PIEGES} max`;
  if (elFabSub) {
    const total = TYPES_ACTIFS.reduce((s, t) => s + piegesDuType(t.id).length, 0);
    elFabSub.textContent = `S${currentSemaine} · ${TYPES_ACTIFS.length} espèces · ${total} pièges`;
  }
}

// En-tête du tableau : une colonne par piège installé pour l'espèce affichée
function renderTheadPieges() {
  if (!elTheadRow) return;
  elTheadRow.querySelectorAll('.nu-th-piege').forEach(th => th.remove());
  const visaTh = elTheadRow.querySelector('.nu-th-visa');
  piegesDuType(currentTypeId).forEach(num => {
    const th = document.createElement('th');
    th.className = 'nu-th-piege';
    th.textContent = `P${num}`;
    elTheadRow.insertBefore(th, visaTh);
  });
}

// ── Sélecteur d'années ────────────────────────────────────────
function initAnnees() {
  const anneeActuelle = new Date().getFullYear();
  for (let a = anneeActuelle; a >= anneeActuelle - 4; a--) {
    const opt = document.createElement('option');
    opt.value = a;
    opt.textContent = a;
    if (a === anneeActuelle) opt.selected = true;
    elAnnee.appendChild(opt);
  }
  elAnnee.addEventListener('change', () => {
    currentAnnee = parseInt(elAnnee.value, 10);
    chargerDonnees().then(() => { if (currentVue === 'carte') majPingsCouleurs(); });
  });
}

// ── Onglets (un par espèce active) ────────────────────────────
function initTabs() {
  currentTypeId = TYPES_ACTIFS[0].id;

  TYPES_ACTIFS.forEach((type, i) => {
    const btn = document.createElement('button');
    btn.className = 'nu-tab' + (i === 0 ? ' actif' : '');
    btn.dataset.type = type.id;
    btn.setAttribute('role', 'tab');
    btn.setAttribute('aria-selected', String(i === 0));
    btn.textContent = `${type.emoji} ${type.court}`;
    elTabs.appendChild(btn);
  });

  elTabs.addEventListener('click', e => {
    const btn = e.target.closest('.nu-tab');
    if (!btn) return;
    elTabs.querySelectorAll('.nu-tab').forEach(b => {
      b.classList.remove('actif');
      b.setAttribute('aria-selected', 'false');
    });
    btn.classList.add('actif');
    btn.setAttribute('aria-selected', 'true');
    currentTypeId = parseInt(btn.dataset.type, 10);
    renderInfoCard();
    renderTheadPieges();      // le jeu de pièges dépend de l'espèce
    chargerDonnees();
    if (currentVue === 'carte') chargerCarte();
  });
}

// ── Info card ─────────────────────────────────────────────────
function initInfoToggle() {
  elInfoToggle.addEventListener('click', () => {
    const ouvert = elInfoWrap.classList.toggle('ouvert');
    elInfoToggle.setAttribute('aria-expanded', String(ouvert));
  });
}

function renderInfoCard() {
  const type = TYPES.find(t => t.id === currentTypeId);
  elInfoCorps.innerHTML = '';

  [
    { titre: 'Nuisibles ciblés',    texte: type.nuisibles },
    { titre: 'Méthodes de lutte',   texte: type.methodes  },
    { titre: 'Fréquence / Protocole', texte: type.frequence },
  ].forEach(({ titre, texte }) => {
    const bloc = document.createElement('div');
    bloc.className = 'nu-info-bloc';
    bloc.innerHTML = `<div class="nu-info-bloc-titre">${titre}</div>
                      <div class="nu-info-bloc-texte">${texte}</div>`;
    elInfoCorps.appendChild(bloc);
  });
}

// ── Chargement personnel (VISA) ───────────────────────────────
async function chargerPersonnel() {
  try {
    const res = await fetch('/api/admin/personnel');
    if (!res.ok) return;
    personnel = (await res.json()).filter(p => p.actif !== false);
    remplirVisaSelect(elVisaSelect);
    remplirVisaSelect(elVisaRapide);
  } catch { /* silencieux */ }
}

function remplirVisaSelect(sel) {
  sel.querySelectorAll('option:not([value=""])').forEach(o => o.remove());
  personnel.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = [p.prenom, p.nom].filter(Boolean).join(' ');
    sel.appendChild(opt);
  });
}

// ── Chargement données ────────────────────────────────────────
async function chargerDonnees() {
  try {
    const res = await fetch(`/api/nuisibles/controles?type_id=${currentTypeId}&annee=${currentAnnee}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    donneesAnnee = await res.json();
    renderInfoCard();
    renderTableau();
  } catch (err) {
    const nbCols = piegesDuType(currentTypeId).length + 2;
    elTbody.innerHTML = `<tr><td colspan="${nbCols}" style="padding:2rem;text-align:center;color:#888;">
      Erreur de chargement : ${err.message}</td></tr>`;
  }
}

// ── Rendu du tableau 52 semaines ──────────────────────────────
function renderTableau() {
  let html = '';
  const nbSem  = nombreSemainesAnnee(currentAnnee);
  const pieges = piegesDuType(currentTypeId);

  for (let sem = 1; sem <= nbSem; sem++) {
    const data = donneesAnnee[String(sem)];
    const isToday = (sem === currentSemaine && currentAnnee === new Date().getFullYear());

    html += `<tr class="${isToday ? 'nu-tr--today' : ''}" data-sem="${sem}">`;
    html += `<td class="nu-td-sem">${sem}</td>`;

    for (const num of pieges) {
      const key = `p${num}`;
      const val = data ? (data.resultats[key] || null) : null;
      const cls = val === 'O' ? 'nu-td-piege--O' : val === 'N' ? 'nu-td-piege--N' : 'nu-td-piege--vide';
      html += `<td class="nu-td-piege ${cls}">${val || '·'}</td>`;
    }

    const visa = data ? (data.visa || '') : '';
    html += `<td class="nu-td-visa">${visa || ''}</td>`;
    html += '</tr>';
  }

  elTbody.innerHTML = html;

  elTbody.querySelectorAll('tr').forEach(tr => {
    tr.addEventListener('click', () => ouvrirModal(parseInt(tr.dataset.sem, 10)));
  });

  if (currentAnnee === new Date().getFullYear()) {
    const trToday = elTbody.querySelector('.nu-tr--today');
    if (trToday) trToday.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }
}

// ── Mettre à jour UNE ligne sans re-rendre tout le tableau ────
function mettreAJourLigne(semaine) {
  const data  = donneesAnnee[String(semaine)];
  const tr    = elTbody.querySelector(`tr[data-sem="${semaine}"]`);
  if (!tr) return;

  const tds = tr.querySelectorAll('.nu-td-piege');
  piegesDuType(currentTypeId).forEach((num, i) => {
    const val = data ? (data.resultats[`p${num}`] || null) : null;
    const td  = tds[i];
    if (!td) return;
    td.className = 'nu-td-piege ' + (val === 'O' ? 'nu-td-piege--O' : val === 'N' ? 'nu-td-piege--N' : 'nu-td-piege--vide');
    td.textContent = val || '·';
  });
  tr.querySelector('.nu-td-visa').textContent = data ? (data.visa || '') : '';
}

// ── FAB saisie rapide ─────────────────────────────────────────
function initFab() {
  majConfigLabel();

  elFab.addEventListener('click', () => {
    const anneeActuelle = new Date().getFullYear();
    if (currentAnnee !== anneeActuelle) {
      currentAnnee = anneeActuelle;
      elAnnee.value = anneeActuelle;
    }
    ouvrirModalRapide(currentSemaine);
  });
}

// ── Modal saisie rapide multi-espèce ──────────────────────────
function initModalRapide() {
  document.getElementById('nu-modal-rapide-fermer').addEventListener('click', fermerModalRapide);
  document.getElementById('nu-btn-rapide-annuler').addEventListener('click', fermerModalRapide);
  elModalRapide.addEventListener('click', e => { if (e.target === elModalRapide) fermerModalRapide(); });
  elBtnRapideSave.addEventListener('click', sauvegarderTout);

  // Navigation semaine
  document.getElementById('nu-sem-prev').addEventListener('click', () => naviguerSemaine(-1));
  document.getElementById('nu-sem-next').addEventListener('click', () => naviguerSemaine(+1));

  // Stepper − / + (porte sur les N premiers pièges de chaque espèce)
  const elMoins = document.getElementById('nu-stepper-moins');
  const elPlus  = document.getElementById('nu-stepper-plus');

  elMoins.addEventListener('click', () => { if (globalNbPieges > 1)                { globalNbPieges--; majStepper(); } });
  elPlus.addEventListener('click',  () => { if (globalNbPieges < maxPiegesActifs()) { globalNbPieges++; majStepper(); } });

  // Boutons d'espèce (uniquement les espèces actives)
  const elEspeces = document.getElementById('nu-ag-especes');
  TYPES_ACTIFS.forEach(type => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'nu-espece-btn';
    btn.dataset.eid = type.id;
    btn.textContent = `${type.emoji} ${type.court}`;
    elEspeces.appendChild(btn);
  });

  // Sélection espèce
  document.getElementById('nu-ag-especes').addEventListener('click', e => {
    const btn = e.target.closest('[data-eid]');
    if (!btn) return;
    document.getElementById('nu-ag-especes').querySelectorAll('[data-eid]').forEach(b => b.classList.remove('actif'));
    btn.classList.add('actif');
    globalEspece = btn.dataset.eid === 'all' ? 'all' : parseInt(btn.dataset.eid, 10);
  });

  // Boutons d'action globale
  document.getElementById('nu-global-n').addEventListener('click',    () => appliquerGlobal('N'));
  document.getElementById('nu-global-o').addEventListener('click',    () => appliquerGlobal('O'));
  document.getElementById('nu-global-vide').addEventListener('click', () => appliquerGlobal(null));
}

// Stepper « N premiers pièges » de l'action globale
function majStepper() {
  const max = maxPiegesActifs();
  globalNbPieges = Math.min(Math.max(globalNbPieges, 1), max);
  document.getElementById('nu-stepper-val').textContent = globalNbPieges;
  document.getElementById('nu-stepper-moins').disabled  = globalNbPieges <= 1;
  document.getElementById('nu-stepper-plus').disabled   = globalNbPieges >= max;
}

function naviguerSemaine(delta) {
  const annee = new Date().getFullYear();
  const nbSem = nombreSemainesAnnee(annee);
  rapideSemaine = Math.min(Math.max(rapideSemaine + delta, 1), nbSem);

  // Recharger les résultats depuis les données déjà en cache
  TYPES_ACTIFS.forEach(type => {
    const semData = (rapideDonnees[type.id]?.[String(rapideSemaine)] || { resultats: {} });
    rapideResultats[type.id] = initResultats(type.id, semData.resultats);
    const grid = document.getElementById(`nu-rapide-grid-${type.id}`);
    if (grid) renderGridRapide(type.id, grid);
  });

  majSemaineNav();
}

function majSemaineNav() {
  const annee   = new Date().getFullYear();
  const nbSem   = nombreSemainesAnnee(annee);
  const label   = `Semaine ${rapideSemaine} / ${annee}${rapideSemaine === currentSemaine ? ' ⚡' : ''}`;
  document.getElementById('nu-sem-label').textContent = label;
  document.getElementById('nu-sem-prev').disabled = rapideSemaine <= 1;
  document.getElementById('nu-sem-next').disabled = rapideSemaine >= nbSem;
}

function appliquerGlobal(val) {
  const types = globalEspece === 'all'
    ? TYPES_ACTIFS
    : TYPES_ACTIFS.filter(t => t.id === globalEspece);
  types.forEach(type => {
    // Les N premiers pièges installés de l'espèce (numéros éventuellement non contigus)
    piegesDuType(type.id).slice(0, globalNbPieges).forEach(num => {
      rapideResultats[type.id][`p${num}`] = val;
    });
    const grid = document.getElementById(`nu-rapide-grid-${type.id}`);
    if (grid) renderGridRapide(type.id, grid);
  });
}

async function ouvrirModalRapide(semaine) {
  rapideSemaine = semaine;
  elModalRapideTitre.textContent = `⚡ Saisie rapide — Semaine ${semaine} / ${new Date().getFullYear()}`;
  elRapideSections.innerHTML = '<div class="nu-rapide-chargement">Chargement…</div>';
  elModalRapide.hidden = false;
  document.body.style.overflow = 'hidden';

  // Rafraîchir les pièges installés sur le plan (ils peuvent avoir changé)
  // puis charger les espèces actives en parallèle.
  await chargerPiegesCarte();
  const annee = new Date().getFullYear();
  const results = await Promise.allSettled(
    TYPES_ACTIFS.map(t =>
      fetch(`/api/nuisibles/controles?type_id=${t.id}&annee=${annee}`).then(r => r.ok ? r.json() : {})
    )
  );

  rapideDonnees  = {};
  rapideResultats = {};
  TYPES_ACTIFS.forEach((type, i) => {
    const data = results[i].status === 'fulfilled' ? results[i].value : {};
    rapideDonnees[type.id] = data;
    const semData = data[String(semaine)] || { resultats: {} };
    rapideResultats[type.id] = initResultats(type.id, semData.resultats);
  });

  // Visa : premier trouvé parmi les types existants, sinon mémorisé
  const pidExistant = TYPES_ACTIFS.map(t => rapideDonnees[t.id]?.[String(semaine)]?.personnel_id).find(v => v);
  elVisaRapide.value = (pidExistant ?? localStorage.getItem('nu-last-personnel-id')) || '';

  // Afficher la semaine dans le navigateur
  majSemaineNav();

  // Réinitialiser la portée globale
  globalNbPieges = maxPiegesActifs();
  globalEspece   = 'all';
  majStepper();
  document.getElementById('nu-ag-especes').querySelectorAll('[data-eid]').forEach(b => {
    b.classList.toggle('actif', b.dataset.eid === 'all');
  });

  renderSectionsRapide();
}

function renderSectionsRapide() {
  elRapideSections.innerHTML = '';
  TYPES_ACTIFS.forEach(type => {
    const nbP = piegesDuType(type.id).length;
    const section = document.createElement('div');
    section.className = 'nu-rapide-section';

    // En-tête de section
    const header = document.createElement('div');
    header.className = 'nu-rapide-section-header';
    header.innerHTML = `
      <span class="nu-rapide-section-nom">${type.emoji} ${type.nom}</span>
      <span class="nu-rapide-nb">${nbP} piège${nbP > 1 ? 's' : ''}</span>
      <div class="nu-rapide-qactions">
        <button class="nu-btn-quick nu-btn-quick--n"    data-tid="${type.id}" data-action="N">✗ N</button>
        <button class="nu-btn-quick nu-btn-quick--o"    data-tid="${type.id}" data-action="O">✓ O</button>
        <button class="nu-btn-quick nu-btn-quick--vide" data-tid="${type.id}" data-action="V">·</button>
      </div>`;

    // Grille pièges
    const grid = document.createElement('div');
    grid.className = 'nu-piege-grid';
    grid.id = `nu-rapide-grid-${type.id}`;

    section.appendChild(header);
    section.appendChild(grid);
    elRapideSections.appendChild(section);

    renderGridRapide(type.id, grid);

    header.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', () => {
        const tid    = parseInt(btn.dataset.tid, 10);
        const action = btn.dataset.action;
        piegesDuType(tid).forEach(num => {
          rapideResultats[tid][`p${num}`] = action === 'V' ? null : action;
        });
        renderGridRapide(tid, document.getElementById(`nu-rapide-grid-${tid}`));
      });
    });
  });
}

function renderGridRapide(typeId, gridEl) {
  gridEl.innerHTML = '';
  piegesDuType(typeId).forEach(num => {
    const key = `p${num}`;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'nu-piege-btn';
    btn.dataset.piege = key;
    appliquerEtatPiege(btn, rapideResultats[typeId][key]);

    btn.addEventListener('click', () => {
      const cur = rapideResultats[typeId][key];
      rapideResultats[typeId][key] = cur === null ? 'O' : cur === 'O' ? 'N' : null;
      appliquerEtatPiege(btn, rapideResultats[typeId][key]);
    });

    gridEl.appendChild(btn);
  });
}

async function sauvegarderTout() {
  const personnelId = elVisaRapide.value ? parseInt(elVisaRapide.value, 10) : null;
  const visaLabel = elVisaRapide.value
    ? elVisaRapide.options[elVisaRapide.selectedIndex].textContent
    : '';
  elBtnRapideSave.disabled = true;
  elBtnRapideSave.textContent = '⏳ Envoi…';

  const typesASauver = TYPES_ACTIFS.filter(t =>
    Object.values(rapideResultats[t.id]).some(v => v !== null)
  );

  if (typesASauver.length === 0) {
    toast('Aucune donnée à enregistrer', true);
    elBtnRapideSave.disabled = false;
    elBtnRapideSave.textContent = '✅ Enregistrer tout';
    return;
  }

  try {
    const annee = new Date().getFullYear();
    await Promise.all(typesASauver.map(type =>
      fetch('/api/nuisibles/controles', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type_id:   type.id,
          annee,
          semaine:   rapideSemaine,
          resultats: rapideResultats[type.id],
          personnel_id: personnelId,
        }),
      }).then(r => { if (!r.ok) throw new Error(`${type.nom}: HTTP ${r.status}`); })
    ));

    // Mettre à jour donneesAnnee si l'onglet actif est dans les types sauvegardés
    typesASauver.forEach(type => {
      if (type.id === currentTypeId && currentAnnee === new Date().getFullYear()) {
        donneesAnnee[String(rapideSemaine)] = {
          resultats:   { ...rapideResultats[type.id] },
          visa:         visaLabel,
          personnel_id: personnelId,
          date_saisie: new Date().toISOString().split('T')[0],
        };
        mettreAJourLigne(rapideSemaine);
      }
    });

    if (personnelId) localStorage.setItem('nu-last-personnel-id', String(personnelId));
    fermerModalRapide();
    const nb = typesASauver.length;
    toast(`✅ Semaine ${rapideSemaine} — ${nb} espèce${nb > 1 ? 's' : ''} enregistrée${nb > 1 ? 's' : ''}`);

  } catch (err) {
    toast(`Erreur : ${err.message}`, true);
  } finally {
    elBtnRapideSave.disabled = false;
    elBtnRapideSave.textContent = '✅ Enregistrer tout';
  }
}

function fermerModalRapide() {
  elModalRapide.hidden = true;
  document.body.style.overflow = '';
  rapideSemaine = null;
}

// ── Modal édition simple (clic sur ligne) ─────────────────────
function initModal() {
  elBtnAnnuler.addEventListener('click',  fermerModal);
  elModalFermer.addEventListener('click', fermerModal);
  elModal.addEventListener('click', e => { if (e.target === elModal) fermerModal(); });
  elBtnSave.addEventListener('click', sauvegarder);

  const appliquerTout = val => {
    piegesDuType(currentTypeId).forEach(num => { editResultats[`p${num}`] = val; });
    renderPiegeGrid();
  };
  document.getElementById('nu-btn-tout-n').addEventListener('click',     () => appliquerTout('N'));
  document.getElementById('nu-btn-tout-o').addEventListener('click',     () => appliquerTout('O'));
  document.getElementById('nu-btn-tout-vider').addEventListener('click', () => appliquerTout(null));
}

function ouvrirModal(semaine) {
  editSemaine = semaine;
  const data  = donneesAnnee[String(semaine)] || { resultats: {}, visa: '' };
  editResultats = initResultats(currentTypeId, data.resultats);

  const type = TYPES.find(t => t.id === currentTypeId);
  const nbP  = piegesDuType(currentTypeId).length;
  const isCurrent = (semaine === currentSemaine && currentAnnee === new Date().getFullYear());
  elModalTitre.textContent =
    `${type.emoji} ${type.nom} — S${semaine} / ${currentAnnee} · ${nbP} piège${nbP > 1 ? 's' : ''}${isCurrent ? ' ⚡' : ''}`;

  renderPiegeGrid();

  elVisaSelect.value = (data.personnel_id ?? localStorage.getItem('nu-last-personnel-id')) || '';

  elBtnSave.disabled = false;
  elModal.hidden = false;
  document.body.style.overflow = 'hidden';
}

function fermerModal() {
  elModal.hidden = true;
  document.body.style.overflow = '';
  editSemaine = null;
}

function renderPiegeGrid() {
  elPiegeGrid.innerHTML = '';
  piegesDuType(currentTypeId).forEach(num => {
    const key = `p${num}`;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'nu-piege-btn';
    btn.dataset.piege = key;
    appliquerEtatPiege(btn, editResultats[key]);

    btn.addEventListener('click', () => {
      const cur = editResultats[key];
      editResultats[key] = cur === null ? 'O' : cur === 'O' ? 'N' : null;
      appliquerEtatPiege(btn, editResultats[key]);
    });

    elPiegeGrid.appendChild(btn);
  });
}

function appliquerEtatPiege(btn, val) {
  const num = btn.dataset.piege.replace('p', 'P');
  btn.classList.remove('nu-piege-btn--O', 'nu-piege-btn--N');

  let etat;
  if (val === 'O') {
    btn.classList.add('nu-piege-btn--O');
    etat = 'O';
  } else if (val === 'N') {
    btn.classList.add('nu-piege-btn--N');
    etat = 'N';
  } else {
    etat = '·';
  }

  btn.innerHTML = `<span class="nu-piege-num">${num}</span>
                   <span class="nu-piege-etat">${etat}</span>`;
}

// ── Sauvegarde simple ─────────────────────────────────────────
async function sauvegarder() {
  elBtnSave.disabled = true;
  elBtnSave.textContent = '⏳ Envoi…';

  const personnelId = elVisaSelect.value ? parseInt(elVisaSelect.value, 10) : null;
  const visaLabel = elVisaSelect.value
    ? elVisaSelect.options[elVisaSelect.selectedIndex].textContent
    : '';

  try {
    const res = await fetch('/api/nuisibles/controles', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type_id:   currentTypeId,
        annee:     currentAnnee,
        semaine:   editSemaine,
        resultats: editResultats,
        personnel_id: personnelId,
      }),
    });

    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail || `HTTP ${res.status}`);
    }

    donneesAnnee[String(editSemaine)] = {
      resultats:   { ...editResultats },
      visa:         visaLabel,
      personnel_id: personnelId,
      date_saisie: new Date().toISOString().split('T')[0],
    };

    if (personnelId) localStorage.setItem('nu-last-personnel-id', String(personnelId));
    mettreAJourLigne(editSemaine);
    fermerModal();
    toast(`✅ Semaine ${editSemaine} enregistrée`);

  } catch (err) {
    toast(`Erreur : ${err.message}`, true);
  } finally {
    elBtnSave.disabled = false;
    elBtnSave.textContent = '✅ Enregistrer';
  }
}

// ══════════════════════════════════════════════════════════════
//  VUE : bascule Registre ↔ Plan des pièges
// ══════════════════════════════════════════════════════════════
function initVueSwitch() {
  elVueTableauBtn.addEventListener('click', () => basculerVue('tableau'));
  elVueCarteBtn.addEventListener('click',   () => basculerVue('carte'));
}

function basculerVue(vue) {
  if (vue === currentVue) return;
  if (currentVue === 'carte' && carteDirty &&
      !confirm('Des modifications du plan ne sont pas enregistrées. Quitter quand même ?')) {
    return;
  }
  currentVue = vue;

  const estTableau = vue === 'tableau';
  elVueTableauBtn.classList.toggle('actif', estTableau);
  elVueCarteBtn.classList.toggle('actif', !estTableau);
  elVueTableauBtn.setAttribute('aria-selected', String(estTableau));
  elVueCarteBtn.setAttribute('aria-selected', String(!estTableau));

  elVueTableauCorps.hidden = !estTableau;
  elVueCarteCorps.hidden   = estTableau;
  // Le FAB de saisie rapide n'a de sens que sur le registre
  elFab.style.display = estTableau ? '' : 'none';

  if (vue === 'carte') chargerCarte();
}

// ══════════════════════════════════════════════════════════════
//  CONFIG : nombre de pièges
// ══════════════════════════════════════════════════════════════
let configValeur = NB_PIEGES;

function initConfig() {
  elConfigBtn.addEventListener('click', ouvrirModalConfig);
  document.getElementById('nu-config-fermer').addEventListener('click', fermerModalConfig);
  document.getElementById('nu-config-annuler').addEventListener('click', fermerModalConfig);
  elModalConfig.addEventListener('click', e => { if (e.target === elModalConfig) fermerModalConfig(); });

  const elVal = document.getElementById('nu-config-val');
  document.getElementById('nu-config-moins').addEventListener('click', () => {
    if (configValeur > 1) { configValeur--; elVal.textContent = configValeur; majAvertConfig(); }
  });
  document.getElementById('nu-config-plus').addEventListener('click', () => {
    if (configValeur < 50) { configValeur++; elVal.textContent = configValeur; majAvertConfig(); }
  });

  document.getElementById('nu-config-save').addEventListener('click', sauvegarderConfig);
}

function majAvertConfig() {
  const avert = document.getElementById('nu-config-avert');
  avert.hidden = configValeur >= NB_PIEGES;
}

function ouvrirModalConfig() {
  configValeur = NB_PIEGES;
  document.getElementById('nu-config-val').textContent = configValeur;
  majAvertConfig();
  elModalConfig.hidden = false;
  document.body.style.overflow = 'hidden';
}

function fermerModalConfig() {
  elModalConfig.hidden = true;
  document.body.style.overflow = '';
}

async function sauvegarderConfig() {
  const btn = document.getElementById('nu-config-save');
  if (configValeur === NB_PIEGES) { fermerModalConfig(); return; }

  btn.disabled = true;
  btn.textContent = '⏳ …';
  try {
    const res = await fetch('/api/nuisibles/config', {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nb_pieges: configValeur }),
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail || `HTTP ${res.status}`);
    }
    NB_PIEGES      = configValeur;
    globalNbPieges = NB_PIEGES;
    majConfigLabel();
    renderTheadPieges();
    renderTableau();
    if (currentVue === 'carte') chargerCarte();
    fermerModalConfig();
    toast(`✅ ${NB_PIEGES} piège${NB_PIEGES > 1 ? 's' : ''} suivi${NB_PIEGES > 1 ? 's' : ''}`);
  } catch (err) {
    toast(`Erreur : ${err.message}`, true);
  } finally {
    btn.disabled = false;
    btn.textContent = '✅ Appliquer';
  }
}

// ══════════════════════════════════════════════════════════════
//  PLAN DES PIÈGES (carte interactive)
// ══════════════════════════════════════════════════════════════
function initCarte() {
  elCarteReset.addEventListener('click', resetCarte);
  elCarteSave.addEventListener('click', sauvegarderCarte);

  // Placer un piège sélectionné en touchant le plan
  elCarteStage.addEventListener('click', e => {
    // Ignorer les clics qui ciblent un ping existant (gérés par le ping lui-même)
    if (e.target.closest('.nu-ping')) return;
    if (cartePiegeActif === null) return;
    const { x, y } = pointEnPourcentage(e.clientX, e.clientY);
    cartePositions[cartePiegeActif] = { pos_x: x, pos_y: y };
    carteDirty = true;
    const placer = cartePiegeActif;
    cartePiegeActif = null;
    renderPalette();
    renderPings();
    elCarteHint.textContent = `P${placer} placé. Glissez-le pour ajuster, ou sélectionnez un autre piège.`;
  });
}

// Charge positions + données de couleur pour le type courant
async function chargerCarte() {
  elCarteHint.textContent = 'Chargement du plan…';
  cartePiegeActif = null;
  carteDirty = false;
  try {
    const res = await fetch(`/api/nuisibles/carte?type_id=${currentTypeId}`);
    const data = res.ok ? await res.json() : { pieges: [] };
    cartePositions = {};
    (data.pieges || []).forEach(p => {
      if (p.piege_num <= NB_PIEGES) {
        cartePositions[p.piege_num] = { pos_x: p.pos_x, pos_y: p.pos_y };
      }
    });
  } catch {
    cartePositions = {};
  }
  // Le plan fait foi pour la liste des pièges à saisir : on resynchronise
  // la mémoire du module (un autre poste a pu modifier le plan).
  memoriserPiegesInstalles();
  const type = TYPES.find(t => t.id === currentTypeId);
  const nbP  = Object.keys(cartePositions).length;
  elCarteHint.textContent = nbP
    ? `${type.emoji} ${type.nom} — ${nbP} piège${nbP > 1 ? 's' : ''} installé${nbP > 1 ? 's' : ''}. Touchez un piège puis le plan pour le placer.`
    : `${type.emoji} ${type.nom} — aucun piège installé. Touchez un piège puis le plan pour le placer.`;
  renderPalette();
  renderPings();
}

/**
 * Enregistre en mémoire les pièges placés sur le plan pour l'espèce courante,
 * et répercute sur le registre (colonnes) et le libellé du FAB.
 */
function memoriserPiegesInstalles() {
  piegesParType[String(currentTypeId)] = Object.keys(cartePositions)
    .map(Number)
    .sort((a, b) => a - b);
  renderTheadPieges();
  renderTableau();
  majConfigLabel();
}

// Palette : un bouton par piège (P1..Pn). Indique placé / à placer / sélectionné.
function renderPalette() {
  elCartePalette.innerHTML = '';
  for (let p = 1; p <= NB_PIEGES; p++) {
    const place = cartePositions[p] !== undefined;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'nu-palette-btn'
      + (place ? ' nu-palette-btn--place' : '')
      + (cartePiegeActif === p ? ' nu-palette-btn--actif' : '');
    btn.textContent = `P${p}`;
    btn.title = place ? `P${p} placé — cliquez pour repositionner` : `P${p} à placer`;
    btn.addEventListener('click', () => {
      cartePiegeActif = (cartePiegeActif === p) ? null : p;
      renderPalette();
      elCarteHint.textContent = cartePiegeActif === null
        ? 'Sélection annulée.'
        : (cartePositions[p] ? `Touchez le plan pour déplacer P${p}.` : `Touchez le plan pour placer P${p}.`);
    });
    elCartePalette.appendChild(btn);
  }
}

// Rendu des pings sur le plan, colorés selon le dernier contrôle connu.
function renderPings() {
  elCartePings.innerHTML = '';
  Object.keys(cartePositions).forEach(numStr => {
    const num = parseInt(numStr, 10);
    if (num > NB_PIEGES) return;
    const pos = cartePositions[num];
    const ping = document.createElement('div');
    ping.className = 'nu-ping ' + classeEtatPing(num);
    ping.style.left = pos.pos_x + '%';
    ping.style.top  = pos.pos_y + '%';
    ping.dataset.num = num;
    ping.innerHTML = `<span class="nu-ping-num">${num}</span>`;
    rendrePingDeplacable(ping, num);
    elCartePings.appendChild(ping);
  });
}

// Met à jour uniquement les couleurs (changement d'année / de données)
function majPingsCouleurs() {
  elCartePings.querySelectorAll('.nu-ping').forEach(ping => {
    const num = parseInt(ping.dataset.num, 10);
    ping.className = 'nu-ping ' + classeEtatPing(num);
  });
}

// Dernier résultat connu du piège sur l'année courante → couleur du ping.
function classeEtatPing(num) {
  const key = `p${num}`;
  let dernier = null;
  // Parcourir les semaines décroissantes pour trouver le dernier état saisi
  for (let sem = nombreSemainesAnnee(currentAnnee); sem >= 1; sem--) {
    const data = donneesAnnee[String(sem)];
    if (data && data.resultats && data.resultats[key]) {
      dernier = data.resultats[key];
      break;
    }
  }
  if (dernier === 'O') return 'nu-ping--O';   // présence/anomalie
  if (dernier === 'N') return 'nu-ping--N';   // RAS
  return 'nu-ping--vide';
}

// Convertit des coordonnées écran en pourcentage relatif à l'image
function pointEnPourcentage(clientX, clientY) {
  const rect = elCarteStage.getBoundingClientRect();
  let x = ((clientX - rect.left) / rect.width)  * 100;
  let y = ((clientY - rect.top)  / rect.height) * 100;
  x = Math.max(0, Math.min(100, x));
  y = Math.max(0, Math.min(100, y));
  return { x: Math.round(x * 100) / 100, y: Math.round(y * 100) / 100 };
}

// Rendre un ping déplaçable (souris + tactile)
function rendrePingDeplacable(ping, num) {
  let deplace = false;

  const onDown = e => {
    e.preventDefault();
    deplace = false;
    cartePiegeActif = null;   // un drag n'est pas une sélection de palette
    ping.classList.add('nu-ping--drag');
    document.addEventListener('pointermove', onMove);
    document.addEventListener('pointerup',   onUp, { once: true });
  };
  const onMove = e => {
    deplace = true;
    const { x, y } = pointEnPourcentage(e.clientX, e.clientY);
    ping.style.left = x + '%';
    ping.style.top  = y + '%';
    cartePositions[num] = { pos_x: x, pos_y: y };
    carteDirty = true;
  };
  const onUp = () => {
    ping.classList.remove('nu-ping--drag');
    document.removeEventListener('pointermove', onMove);
    if (deplace) {
      renderPalette();
      elCarteHint.textContent = `P${num} déplacé.`;
    }
  };

  ping.addEventListener('pointerdown', onDown);
  // Clic simple (sans déplacement) sur un ping = le retirer du plan
  ping.addEventListener('click', e => {
    e.stopPropagation();
    if (deplace) return;       // c'était un drag, pas un clic
    if (confirm(`Retirer le piège P${num} du plan ?`)) {
      delete cartePositions[num];
      carteDirty = true;
      renderPalette();
      renderPings();
      elCarteHint.textContent = `P${num} retiré du plan.`;
    }
  });
}

function resetCarte() {
  if (Object.keys(cartePositions).length === 0) return;
  if (!confirm('Effacer tous les pièges placés sur le plan pour ce type ?')) return;
  cartePositions = {};
  cartePiegeActif = null;
  carteDirty = true;
  renderPalette();
  renderPings();
  elCarteHint.textContent = 'Tous les pièges ont été effacés. Pensez à enregistrer.';
}

async function sauvegarderCarte() {
  elCarteSave.disabled = true;
  elCarteSave.textContent = '⏳ …';
  try {
    const pieges = Object.keys(cartePositions).map(num => ({
      piege_num: parseInt(num, 10),
      pos_x:     cartePositions[num].pos_x,
      pos_y:     cartePositions[num].pos_y,
    }));
    const res = await fetch('/api/nuisibles/carte', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type_id: currentTypeId, pieges }),
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail || `HTTP ${res.status}`);
    }
    carteDirty = false;
    // Le registre et la saisie suivent désormais ces pièges-là
    memoriserPiegesInstalles();
    toast(`✅ Plan enregistré — ${pieges.length} piège${pieges.length > 1 ? 's' : ''} suivi${pieges.length > 1 ? 's' : ''}`);
  } catch (err) {
    toast(`Erreur : ${err.message}`, true);
  } finally {
    elCarteSave.disabled = false;
    elCarteSave.textContent = '💾 Enregistrer';
  }
}

// ── Helpers ───────────────────────────────────────────────────

function getISOWeek(date) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + 3 - (d.getDay() + 6) % 7);
  const week1 = new Date(d.getFullYear(), 0, 4);
  return 1 + Math.round(
    ((d.getTime() - week1.getTime()) / 86400000 - 3 + (week1.getDay() + 6) % 7) / 7
  );
}

function nombreSemainesAnnee(annee) {
  return getISOWeek(new Date(annee, 11, 28));
}

// ── Toast ─────────────────────────────────────────────────────
let toastTimer;
function toast(msg, erreur = false) {
  clearTimeout(toastTimer);
  elToast.textContent = msg;
  elToast.classList.toggle('nu-toast--erreur', erreur);
  elToast.classList.add('nu-toast--visible');
  toastTimer = setTimeout(() => elToast.classList.remove('nu-toast--visible'), 3500);
}

'use strict';
/* ============================================================
   nuisibles.js — Lutte contre Nuisibles (IPM)
   4 onglets × 52 semaines × 15 pièges
   ============================================================ */

// ── Constantes types de nuisibles ────────────────────────────
const TYPES = [
  {
    id: 1,
    nom: 'Rongeurs',
    emoji: '🐀',
    nuisibles: 'Souris, Rats, Mulots…',
    methodes:  '• Plaques de glue avec attractif\n• Rodenticide fluorescent dans boîte sécurisée',
    frequence: '• Inspection hebdomadaire des plaques de glue\n• Changement des pièges à glue et vérification des rodenticides tous les mois',
  },
  {
    id: 2,
    nom: 'Insectes Volants',
    emoji: '🪰',
    nuisibles: 'Mouches, Moucherons, Guêpes…',
    methodes:  '• DEIV à glu pour les zones alimentaires\n• DEIV à électrocution pour les zones non alimentaires',
    frequence: '• Plaque de glu — Période chaude (avril–septembre) : remplacement mensuel\n• Plaque de glu — Période froide (octobre–mars) : remplacement tous les 2 mois\n• Tubes UV : remplacement annuel',
  },
  {
    id: 3,
    nom: 'Insectes Rampants',
    emoji: '🪳',
    nuisibles: 'Cafards, Fourmis…',
    methodes:  '• Piège à phéromones et à glu dans les zones critiques\n• Gel anti-cafard / fourmis dans boîte sécurisée',
    frequence: '• Inspection hebdomadaire des plaques de glue\n• Remplacer les plaques tous les 3 mois\n• Remplacer le gel tous les 3 mois',
  },
  {
    id: 4,
    nom: 'Oiseaux',
    emoji: '🐦',
    nuisibles: 'Pigeons, Moineaux, Étourneaux…',
    methodes:  '• Pics anti-pigeons\n• Filets de protection',
    frequence: '• Inspection hebdomadaire des pics et filets\n• Nettoyage et désinfection immédiats en cas de présence de fientes',
  },
];

const NB_PIEGES = 15;

// ── État ──────────────────────────────────────────────────────
let currentTypeId  = 1;
let currentAnnee   = new Date().getFullYear();
let currentSemaine = getISOWeek(new Date());
let donneesAnnee   = {};   // { "17": {resultats: {p1:"O",...}, visa:"Éric"}, ... }
let personnel      = [];

// Édition en cours
let editSemaine   = null;
let editResultats = {};    // {"p1": "O"/"N"/null, ...}

// ── Références DOM ────────────────────────────────────────────
const elAnnee       = document.getElementById('nu-annee');
const elInfoWrap    = document.getElementById('nu-info-wrap');
const elInfoToggle  = document.getElementById('nu-info-toggle');
const elInfoCorps   = document.getElementById('nu-info-corps');
const elTbody       = document.getElementById('nu-tbody');
const elModal       = document.getElementById('nu-modal');
const elModalTitre  = document.getElementById('nu-modal-titre');
const elPiegeGrid   = document.getElementById('nu-piege-grid');
const elVisaSelect  = document.getElementById('nu-visa-select');
const elBtnAnnuler  = document.getElementById('nu-btn-annuler');
const elBtnSave     = document.getElementById('nu-btn-sauvegarder');
const elModalFermer = document.getElementById('nu-modal-fermer');
const elToast       = document.getElementById('nu-toast');
const elFab         = document.getElementById('nu-fab-rapide');

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initAnnees();
  initTabs();
  initInfoToggle();
  initModal();
  initFab();
  chargerPersonnel();
  chargerDonnees();
});

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
    chargerDonnees();
  });
}

// ── Onglets ───────────────────────────────────────────────────
function initTabs() {
  document.querySelectorAll('.nu-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nu-tab').forEach(b => {
        b.classList.remove('actif');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('actif');
      btn.setAttribute('aria-selected', 'true');
      currentTypeId = parseInt(btn.dataset.type, 10);
      renderInfoCard();
      chargerDonnees();
    });
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
  } catch { /* silencieux */ }
}

function remplirVisaSelect(sel) {
  // Garde l'option vide
  sel.querySelectorAll('option:not([value=""])').forEach(o => o.remove());
  personnel.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.prenom;
    opt.textContent = p.prenom;
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
    elTbody.innerHTML = `<tr><td colspan="17" style="padding:2rem;text-align:center;color:#888;">
      Erreur de chargement : ${err.message}</td></tr>`;
  }
}

// ── Rendu du tableau 52 semaines ──────────────────────────────
function renderTableau() {
  let html = '';
  const nbSem = nombreSemainesAnnee(currentAnnee);

  for (let sem = 1; sem <= nbSem; sem++) {
    const data = donneesAnnee[String(sem)];
    const isToday = (sem === currentSemaine && currentAnnee === new Date().getFullYear());

    html += `<tr class="${isToday ? 'nu-tr--today' : ''}" data-sem="${sem}">`;
    html += `<td class="nu-td-sem">${sem}</td>`;

    for (let p = 1; p <= NB_PIEGES; p++) {
      const key = `p${p}`;
      const val = data ? (data.resultats[key] || null) : null;
      const cls = val === 'O' ? 'nu-td-piege--O' : val === 'N' ? 'nu-td-piege--N' : 'nu-td-piege--vide';
      html += `<td class="nu-td-piege ${cls}">${val || '·'}</td>`;
    }

    // VISA
    const visa = data ? (data.visa || '') : '';
    html += `<td class="nu-td-visa">${visa || ''}</td>`;
    html += '</tr>';
  }

  elTbody.innerHTML = html;

  // Clic sur une ligne → ouvrir modal
  elTbody.querySelectorAll('tr').forEach(tr => {
    tr.addEventListener('click', () => ouvrirModal(parseInt(tr.dataset.sem, 10)));
  });

  // Scroll vers la semaine actuelle si on est dans l'année courante
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
  for (let p = 1; p <= NB_PIEGES; p++) {
    const key = `p${p}`;
    const val = data ? (data.resultats[key] || null) : null;
    const td  = tds[p - 1];
    td.className = 'nu-td-piege ' + (val === 'O' ? 'nu-td-piege--O' : val === 'N' ? 'nu-td-piege--N' : 'nu-td-piege--vide');
    td.textContent = val || '·';
  }
  tr.querySelector('.nu-td-visa').textContent = data ? (data.visa || '') : '';
}

// ── FAB saisie rapide ─────────────────────────────────────────
function initFab() {
  elFab.addEventListener('click', () => {
    // Bascule sur l'année courante si nécessaire
    const anneeActuelle = new Date().getFullYear();
    if (currentAnnee !== anneeActuelle) {
      currentAnnee = anneeActuelle;
      elAnnee.value = anneeActuelle;
      chargerDonnees().then(() => ouvrirModal(currentSemaine));
    } else {
      ouvrirModal(currentSemaine);
    }
  });
}

// ── Modal édition ─────────────────────────────────────────────
function initModal() {
  elBtnAnnuler.addEventListener('click',  fermerModal);
  elModalFermer.addEventListener('click', fermerModal);
  elModal.addEventListener('click', e => { if (e.target === elModal) fermerModal(); });
  elBtnSave.addEventListener('click', sauvegarder);

  document.getElementById('nu-btn-tout-n').addEventListener('click', () => {
    for (let p = 1; p <= NB_PIEGES; p++) editResultats[`p${p}`] = 'N';
    renderPiegeGrid();
  });
  document.getElementById('nu-btn-tout-o').addEventListener('click', () => {
    for (let p = 1; p <= NB_PIEGES; p++) editResultats[`p${p}`] = 'O';
    renderPiegeGrid();
  });
  document.getElementById('nu-btn-tout-vider').addEventListener('click', () => {
    for (let p = 1; p <= NB_PIEGES; p++) editResultats[`p${p}`] = null;
    renderPiegeGrid();
  });
}

function ouvrirModal(semaine) {
  editSemaine = semaine;
  const data  = donneesAnnee[String(semaine)] || { resultats: {}, visa: '' };
  editResultats = {};
  for (let p = 1; p <= NB_PIEGES; p++) {
    editResultats[`p${p}`] = data.resultats[`p${p}`] || null;
  }

  const type = TYPES.find(t => t.id === currentTypeId);
  const isCurrent = (semaine === currentSemaine && currentAnnee === new Date().getFullYear());
  elModalTitre.textContent = `${type.emoji} ${type.nom} — Semaine ${semaine} / ${currentAnnee}${isCurrent ? ' ⚡' : ''}`;

  // Construire les 15 boutons
  renderPiegeGrid();

  // VISA : priorité à la donnée existante, sinon dernier visa mémorisé
  elVisaSelect.value = data.visa || localStorage.getItem('nu-last-visa') || '';

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
  for (let p = 1; p <= NB_PIEGES; p++) {
    const key = `p${p}`;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'nu-piege-btn';
    btn.dataset.piege = key;
    appliquerEtatPiege(btn, editResultats[key]);

    btn.addEventListener('click', () => {
      // Cycle : null → O → N → null
      const cur = editResultats[key];
      editResultats[key] = cur === null ? 'O' : cur === 'O' ? 'N' : null;
      appliquerEtatPiege(btn, editResultats[key]);
    });

    elPiegeGrid.appendChild(btn);
  }
}

function appliquerEtatPiege(btn, val) {
  const num = btn.dataset.piege.replace('p', 'P');
  btn.classList.remove('nu-piege-btn--O', 'nu-piege-btn--N');

  let etat, label;
  if (val === 'O') {
    btn.classList.add('nu-piege-btn--O');
    etat = 'O'; label = '✓';
  } else if (val === 'N') {
    btn.classList.add('nu-piege-btn--N');
    etat = 'N'; label = '✗';
  } else {
    etat = '·'; label = '';
  }

  btn.innerHTML = `<span class="nu-piege-num">${num}</span>
                   <span class="nu-piege-etat">${etat}</span>`;
}

// ── Sauvegarde ────────────────────────────────────────────────
async function sauvegarder() {
  elBtnSave.disabled = true;
  elBtnSave.textContent = '⏳ Envoi…';

  const visa = elVisaSelect.value;

  try {
    const res = await fetch('/api/nuisibles/controles', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type_id:   currentTypeId,
        annee:     currentAnnee,
        semaine:   editSemaine,
        resultats: editResultats,
        visa,
      }),
    });

    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail || `HTTP ${res.status}`);
    }

    // Mettre à jour les données locales
    donneesAnnee[String(editSemaine)] = {
      resultats:   { ...editResultats },
      visa,
      date_saisie: new Date().toISOString().split('T')[0],
    };

    if (visa) localStorage.setItem('nu-last-visa', visa);
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

// ── Helpers ───────────────────────────────────────────────────

/** Numéro de semaine ISO pour une date donnée */
function getISOWeek(date) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + 3 - (d.getDay() + 6) % 7);
  const week1 = new Date(d.getFullYear(), 0, 4);
  return 1 + Math.round(
    ((d.getTime() - week1.getTime()) / 86400000 - 3 + (week1.getDay() + 6) % 7) / 7
  );
}

/** Nombre de semaines ISO dans une année (52 ou 53) — on lit la semaine du 28 décembre */
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

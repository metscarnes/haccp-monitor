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

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initAnnees();
  initTabs();
  initInfoToggle();
  initModal();
  initModalRapide();
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
    remplirVisaSelect(elVisaRapide);
  } catch { /* silencieux */ }
}

function remplirVisaSelect(sel) {
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
  elFabSub.textContent = `S${currentSemaine} · ${TYPES.length} espèces · ${NB_PIEGES} pièges`;

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

  // Stepper − / +
  const elVal   = document.getElementById('nu-stepper-val');
  const elMoins = document.getElementById('nu-stepper-moins');
  const elPlus  = document.getElementById('nu-stepper-plus');

  function majStepper() {
    elVal.textContent    = globalNbPieges;
    elMoins.disabled     = globalNbPieges <= 1;
    elPlus.disabled      = globalNbPieges >= NB_PIEGES;
  }
  elMoins.addEventListener('click', () => { if (globalNbPieges > 1)        { globalNbPieges--; majStepper(); } });
  elPlus.addEventListener('click',  () => { if (globalNbPieges < NB_PIEGES) { globalNbPieges++; majStepper(); } });

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

function appliquerGlobal(val) {
  const types = globalEspece === 'all' ? TYPES : TYPES.filter(t => t.id === globalEspece);
  types.forEach(type => {
    for (let p = 1; p <= globalNbPieges; p++) {
      rapideResultats[type.id][`p${p}`] = val;
    }
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

  // Charger les 4 types en parallèle
  const annee = new Date().getFullYear();
  const results = await Promise.allSettled(
    TYPES.map(t =>
      fetch(`/api/nuisibles/controles?type_id=${t.id}&annee=${annee}`).then(r => r.ok ? r.json() : {})
    )
  );

  rapideDonnees  = {};
  rapideResultats = {};
  TYPES.forEach((type, i) => {
    const data = results[i].status === 'fulfilled' ? results[i].value : {};
    rapideDonnees[type.id] = data;
    const semData = data[String(semaine)] || { resultats: {} };
    rapideResultats[type.id] = {};
    for (let p = 1; p <= NB_PIEGES; p++) {
      rapideResultats[type.id][`p${p}`] = semData.resultats[`p${p}`] || null;
    }
  });

  // Visa : premier trouvé parmi les types existants, sinon mémorisé
  const visaExistant = TYPES.map(t => rapideDonnees[t.id]?.[String(semaine)]?.visa).find(v => v);
  elVisaRapide.value = visaExistant || localStorage.getItem('nu-last-visa') || '';

  // Réinitialiser la portée globale
  globalNbPieges = NB_PIEGES;
  globalEspece   = 'all';
  document.getElementById('nu-stepper-val').textContent = NB_PIEGES;
  document.getElementById('nu-stepper-moins').disabled  = false;
  document.getElementById('nu-stepper-plus').disabled   = true;
  document.getElementById('nu-ag-especes').querySelectorAll('[data-eid]').forEach(b => {
    b.classList.toggle('actif', b.dataset.eid === 'all');
  });

  renderSectionsRapide();
}

function renderSectionsRapide() {
  elRapideSections.innerHTML = '';
  TYPES.forEach(type => {
    const section = document.createElement('div');
    section.className = 'nu-rapide-section';

    // En-tête de section
    const header = document.createElement('div');
    header.className = 'nu-rapide-section-header';
    header.innerHTML = `
      <span class="nu-rapide-section-nom">${type.emoji} ${type.nom}</span>
      <span class="nu-rapide-nb">${NB_PIEGES} pièges</span>
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
        for (let p = 1; p <= NB_PIEGES; p++) {
          rapideResultats[tid][`p${p}`] = action === 'V' ? null : action;
        }
        renderGridRapide(tid, document.getElementById(`nu-rapide-grid-${tid}`));
      });
    });
  });
}

function renderGridRapide(typeId, gridEl) {
  gridEl.innerHTML = '';
  for (let p = 1; p <= NB_PIEGES; p++) {
    const key = `p${p}`;
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
  }
}

async function sauvegarderTout() {
  const visa = elVisaRapide.value;
  elBtnRapideSave.disabled = true;
  elBtnRapideSave.textContent = '⏳ Envoi…';

  const typesASauver = TYPES.filter(t =>
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
          visa,
        }),
      }).then(r => { if (!r.ok) throw new Error(`${type.nom}: HTTP ${r.status}`); })
    ));

    // Mettre à jour donneesAnnee si l'onglet actif est dans les types sauvegardés
    typesASauver.forEach(type => {
      if (type.id === currentTypeId && currentAnnee === new Date().getFullYear()) {
        donneesAnnee[String(rapideSemaine)] = {
          resultats:   { ...rapideResultats[type.id] },
          visa,
          date_saisie: new Date().toISOString().split('T')[0],
        };
        mettreAJourLigne(rapideSemaine);
      }
    });

    if (visa) localStorage.setItem('nu-last-visa', visa);
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

  renderPiegeGrid();

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

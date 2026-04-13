'use strict';
/* ============================================================
   taches.js — Écran Tâches HACCP du jour
   Au Comptoir des Lilas — Mets Carnés Holding

   Tâches affichées :
     - Nettoyage et désinfection  (nettoyage_desinfection)
     - Nettoyage pièges oiseaux   (nettoyage_pieges_oiseaux)
   ============================================================ */

const REFRESH_MS = 60_000;

// Seuls ces deux codes de tâche sont affichés et traités
const CODES_ACTIFS = new Set(['nettoyage_desinfection', 'nettoyage_pieges_oiseaux']);

// ── État ──────────────────────────────────────────────────────
let operateur     = null;   // prénom sélectionné
let tacheCourante = null;   // tâche ouverte dans le modal
let pieges        = [];     // liste des pièges oiseaux

// ── Références DOM ────────────────────────────────────────────
const elDate         = document.getElementById('taches-date');
const elHorloge      = document.getElementById('taches-horloge');
const elOperateurBar = document.getElementById('operateur-bar');
const elOperateurBtns= document.getElementById('operateur-boutons');

const elColRetard    = document.getElementById('liste-retard');
const elColAfaire    = document.getElementById('liste-afaire');
const elColFait      = document.getElementById('liste-fait');
const elNbRetard     = document.getElementById('nb-retard');
const elNbAfaire     = document.getElementById('nb-afaire');
const elNbFait       = document.getElementById('nb-fait');

const elOverlay      = document.getElementById('modal-overlay');
const elModalTitre   = document.getElementById('modal-titre');
const elModalSousTitre = document.getElementById('modal-sous-titre');
const elModalIcone   = document.getElementById('modal-icone');
const elModalChamps  = document.getElementById('modal-champs-specifiques');
const elModalForm    = document.getElementById('modal-form');
const elModalErreur  = document.getElementById('modal-erreur');
const elModalValider = document.getElementById('modal-valider');
const elModalValiderTexte = document.getElementById('modal-valider-texte');

// ── Horloge ───────────────────────────────────────────────────
function majHorloge() {
  const now  = new Date();
  const date = now.toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });
  const heure = now.toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
  elDate.textContent    = date.charAt(0).toUpperCase() + date.slice(1);
  elHorloge.textContent = heure;
}
setInterval(majHorloge, 1000);
majHorloge();

// ── Fetch helper ──────────────────────────────────────────────
async function apiFetch(url, options = {}) {
  const res = await fetch(url, { cache: 'no-store', ...options });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} — ${txt || url}`);
  }
  return res.json();
}

// ── Personnel ─────────────────────────────────────────────────
async function chargerPersonnel() {
  try {
    const data = await apiFetch('/api/admin/personnel');
    afficherPersonnel(data);
  } catch {
    elOperateurBtns.innerHTML = '<span class="operateur-placeholder erreur">Erreur chargement personnel</span>';
  }
}

function afficherPersonnel(personnes) {
  elOperateurBtns.innerHTML = '';
  if (!personnes || personnes.length === 0) {
    elOperateurBtns.innerHTML = '<span class="operateur-placeholder">Aucun personnel configuré</span>';
    return;
  }
  personnes.forEach(p => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'operateur-btn';
    btn.textContent = p.prenom;
    btn.dataset.prenom = p.prenom;
    btn.addEventListener('click', () => selectionnerOperateur(p.prenom));
    elOperateurBtns.appendChild(btn);
  });
}

function selectionnerOperateur(prenom) {
  operateur = prenom;
  elOperateurBar.classList.remove('operateur-bar--vide');
  elOperateurBar.classList.add('operateur-bar--actif');
  document.querySelectorAll('.operateur-btn').forEach(b => {
    b.classList.toggle('operateur-btn--actif', b.dataset.prenom === prenom);
  });
}

// ── Pièges oiseaux ────────────────────────────────────────────
async function chargerPieges() {
  try {
    pieges = await apiFetch('/api/admin/pieges');
  } catch {
    pieges = [];
  }
}

// ── Tâches du jour ────────────────────────────────────────────
async function chargerTaches() {
  try {
    const data = await apiFetch('/api/taches/today');
    afficherColonnes(data);
  } catch {
    [elColRetard, elColAfaire, elColFait].forEach(el => {
      el.innerHTML = '<div class="taches-vide taches-vide--erreur">⚠ Connexion perdue</div>';
    });
  }
}

function afficherColonnes(data) {
  // On n'affiche que les deux tâches nettoyage conservées
  const retard = (data.en_retard ?? []).filter(t => CODES_ACTIFS.has(t.code));
  const afaire = (data.a_faire  ?? []).filter(t => CODES_ACTIFS.has(t.code));
  const fait   = (data.fait     ?? []).filter(t => CODES_ACTIFS.has(t.code));

  elNbRetard.textContent = retard.length || '';
  elNbAfaire.textContent = afaire.length || '';
  elNbFait.textContent   = fait.length   || '';

  elColRetard.innerHTML = retard.length
    ? retard.map(t => carteHtml(t, 'retard')).join('')
    : '<div class="taches-vide">✓ Aucune tâche en retard</div>';

  elColAfaire.innerHTML = afaire.length
    ? afaire.map(t => carteHtml(t, 'afaire')).join('')
    : '<div class="taches-vide">Aucune tâche en attente</div>';

  elColFait.innerHTML = fait.length
    ? fait.map(t => carteHtml(t, 'fait')).join('')
    : '<div class="taches-vide">Aucune validation aujourd\'hui</div>';

  // Bind click sur cartes actives
  document.querySelectorAll('.tache-carte[data-id]').forEach(carte => {
    if (carte.dataset.etat === 'fait') return;
    carte.addEventListener('click', () => {
      const tache = {
        id:          parseInt(carte.dataset.id),
        code:        carte.dataset.code,
        libelle:     carte.dataset.libelle,
        heure_cible: carte.dataset.heure || null,
      };
      ouvrirModal(tache);
    });
  });
}

function carteHtml(tache, etat) {
  const heure = tache.heure_cible
    ? `<span class="tache-heure">${tache.heure_cible.slice(0,5)}</span>`
    : '';
  const icone = iconeParCode(tache.code);
  const cliquable = etat !== 'fait' ? 'tache-carte--cliquable' : '';
  return `<div class="tache-carte tache-carte--${etat} ${cliquable}"
               data-id="${tache.id}"
               data-code="${tache.code}"
               data-libelle="${escHtml(tache.libelle)}"
               data-heure="${tache.heure_cible ?? ''}"
               data-etat="${etat}"
               role="${etat !== 'fait' ? 'button' : 'listitem'}"
               tabindex="${etat !== 'fait' ? '0' : '-1'}">
    <div class="tache-carte-haut">
      <span class="tache-icone" aria-hidden="true">${icone}</span>
      ${heure}
    </div>
    <div class="tache-libelle">${escHtml(tache.libelle)}</div>
  </div>`;
}

function iconeParCode(code) {
  const ICONES = {
    nettoyage_desinfection:   '🧹',
    nettoyage_pieges_oiseaux: '🪤',
  };
  return ICONES[code] ?? '📋';
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Modal ─────────────────────────────────────────────────────
function ouvrirModal(tache) {
  if (!operateur) {
    elOperateurBar.classList.add('operateur-bar--flash');
    setTimeout(() => elOperateurBar.classList.remove('operateur-bar--flash'), 800);
    return;
  }

  tacheCourante = tache;
  elModalTitre.textContent     = tache.libelle;
  elModalSousTitre.textContent = tache.heure_cible
    ? `Heure cible : ${tache.heure_cible.slice(0, 5)}`
    : 'Tâche événementielle';
  elModalIcone.textContent = iconeParCode(tache.code);

  elModalForm.reset();
  elModalErreur.hidden = true;
  elModalValider.disabled = false;
  elModalValiderTexte.textContent = 'Valider ✓';

  elModalChamps.innerHTML = construireChamps(tache.code);

  elOverlay.hidden = false;
  document.body.style.overflow = 'hidden';

  const premierInput = elModalChamps.querySelector('input, select, textarea');
  if (premierInput) premierInput.focus();
}

function fermerModal() {
  elOverlay.hidden = true;
  document.body.style.overflow = '';
  tacheCourante = null;
}

/** Retourne le HTML des champs spécifiques selon le code de la tâche */
function construireChamps(code) {
  switch (code) {

    case 'nettoyage_desinfection':
      return `
        <fieldset class="modal-fieldset">
          <legend class="modal-fieldset-titre">Produits utilisés</legend>
          <div class="modal-grille-2">
            <div class="modal-champ">
              <label class="modal-champ-label" for="ds_produit_nett">Produit détergent-désinfectant</label>
              <input id="ds_produit_nett" name="ds_produit_nett" class="modal-input" type="text"
                     placeholder="Ex : Désoclean, Diversey...">
            </div>
            <div class="modal-champ">
              <label class="modal-champ-label" for="ds_dilution">Dilution / dose</label>
              <input id="ds_dilution" name="ds_dilution" class="modal-input" type="text"
                     placeholder="Ex : 3 %, 50 mL / 5 L...">
            </div>
          </div>
        </fieldset>`;

    case 'nettoyage_pieges_oiseaux': {
      const oiseaux = pieges.filter(p => p.type === 'oiseau');
      if (oiseaux.length === 0) {
        return `<p class="modal-info">Aucun piège oiseau configuré — <a href="/admin.html">configurer</a></p>`;
      }
      return `
        <fieldset class="modal-fieldset">
          <legend class="modal-fieldset-titre">Nettoyage pièges oiseaux</legend>
          ${oiseaux.map(p => `
            <label class="modal-checkbox-ligne">
              <input type="checkbox" name="piege_${p.id}" id="piege_${p.id}">
              <span>
                <strong>${escHtml(p.identifiant)}</strong>
                ${p.localisation ? ` — ${escHtml(p.localisation)}` : ''}
                &ensp;— Nettoyé
              </span>
            </label>`).join('')}
        </fieldset>`;
    }

    default:
      return '';
  }
}

/** Collecte les valeurs des champs spécifiques du formulaire courant */
function collecterDonneesSpecifiques(code) {
  const ds = {};
  const form = elModalForm;

  function val(id) {
    const el = form.querySelector(`[name="${id}"]`);
    return el ? el.value.trim() : undefined;
  }

  switch (code) {
    case 'nettoyage_desinfection':
      ds.produit_nettoyage = val('ds_produit_nett');
      ds.dilution          = val('ds_dilution');
      break;

    case 'nettoyage_pieges_oiseaux': {
      const etat = {};
      pieges.filter(p => p.type === 'oiseau').forEach(p => {
        const cb = form.querySelector(`[name="piege_${p.id}"]`);
        etat[p.identifiant] = cb ? cb.checked : false;
      });
      ds.pieges_oiseaux = etat;
      break;
    }
  }

  return Object.keys(ds).length > 0 ? ds : null;
}

// ── Soumission validation ─────────────────────────────────────
elModalForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!tacheCourante || !operateur) return;

  const conformeRadio = elModalForm.querySelector('[name="conforme"]:checked');
  if (!conformeRadio) {
    afficherErreurModal('Veuillez indiquer si la tâche est conforme ou non.');
    return;
  }

  const commentaire = document.getElementById('modal-commentaire').value.trim();
  const ds          = collecterDonneesSpecifiques(tacheCourante.code);
  const today       = new Date().toISOString().slice(0, 10);

  const payload = {
    tache_type_id:       tacheCourante.id,
    operateur:           operateur,
    date_tache:          today,
    conforme:            conformeRadio.value === 'oui',
    commentaire:         commentaire || null,
    donnees_specifiques: ds,
  };

  elModalValider.disabled          = true;
  elModalValiderTexte.textContent  = 'Envoi…';
  elModalErreur.hidden             = true;

  try {
    await apiFetch('/api/taches/valider', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    fermerModal();
    await chargerTaches();
  } catch (err) {
    afficherErreurModal(`Erreur : ${err.message}`);
    elModalValider.disabled         = false;
    elModalValiderTexte.textContent = 'Valider ✓';
  }
});

function afficherErreurModal(msg) {
  elModalErreur.textContent = msg;
  elModalErreur.hidden      = false;
}

// ── Fermeture modal ───────────────────────────────────────────
document.getElementById('modal-fermer').addEventListener('click', fermerModal);
document.getElementById('modal-annuler').addEventListener('click', fermerModal);

elOverlay.addEventListener('click', (e) => {
  if (e.target === elOverlay) fermerModal();
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !elOverlay.hidden) fermerModal();
});

// ── Accessibilité clavier pour les cartes ─────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    const carte = e.target.closest('.tache-carte--cliquable');
    if (carte) {
      e.preventDefault();
      carte.click();
    }
  }
});

// ── Init ──────────────────────────────────────────────────────
async function init() {
  await Promise.all([chargerPersonnel(), chargerPieges()]);
  await chargerTaches();
  setInterval(chargerTaches, REFRESH_MS);
}

init();

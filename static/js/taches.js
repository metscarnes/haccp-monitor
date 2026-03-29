'use strict';
/* ============================================================
   taches.js — Écran Tâches HACCP du jour
   Au Comptoir des Lilas — Mets Carnés Holding

   Responsabilités :
   - Horloge / date temps réel
   - Sélecteur opérateur (personnel)
   - Chargement et affichage des 3 colonnes (retard / à faire / fait)
   - Modal de validation avec formulaire spécifique par tâche
   - Soumission POST /api/taches/valider
   - Rafraîchissement automatique toutes les 60 s
   ============================================================ */

const REFRESH_MS = 60_000;

// ── État ──────────────────────────────────────────────────────
let operateur    = null;   // prénom sélectionné
let tacheCourante = null;  // tache ouverte dans le modal
let pieges       = [];     // liste des pièges (pour formulaires)

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
    btn.addEventListener('click', () => selectionnerOperateur(p.prenom, btn));
    elOperateurBtns.appendChild(btn);
  });
}

function selectionnerOperateur(prenom, btnEl) {
  operateur = prenom;
  elOperateurBar.classList.remove('operateur-bar--vide');
  elOperateurBar.classList.add('operateur-bar--actif');
  document.querySelectorAll('.operateur-btn').forEach(b => {
    b.classList.toggle('operateur-btn--actif', b.dataset.prenom === prenom);
  });
}

// ── Pièges ────────────────────────────────────────────────────
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
  } catch (err) {
    [elColRetard, elColAfaire, elColFait].forEach(el => {
      el.innerHTML = '<div class="taches-vide taches-vide--erreur">⚠ Connexion perdue</div>';
    });
  }
}

function afficherColonnes(data) {
  const retard = data.en_retard ?? [];
  const afaire = data.a_faire  ?? [];
  const fait   = data.fait     ?? [];

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
    releve_temp_enceintes_matin: '🌡',
    releve_temp_enceintes_soir:  '🌡',
    temp_lave_vaisselle:         '🍽',
    suivi_temp_production:       '🥩',
    nettoyage_desinfection:      '🧹',
    pieges_rongeurs:             '🪤',
    nettoyage_pieges_oiseaux:    '🪤',
    controle_huile_friture:      '🍳',
    suivi_decongélation:         '❄',
    suivi_congelation:           '🧊',
    action_corrective_temp:      '⚠',
    etalonnage_thermometres:     '📐',
    tiac:                        '🚨',
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
    // Flash la barre opérateur
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

  // Réinitialiser
  elModalForm.reset();
  elModalErreur.hidden = true;
  elModalValider.disabled = false;
  elModalValiderTexte.textContent = 'Valider ✓';

  // Champs spécifiques
  elModalChamps.innerHTML = construireChamps(tache.code);

  elOverlay.hidden = false;
  document.body.style.overflow = 'hidden';

  // Focus premier input
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

    case 'releve_temp_enceintes_matin':
    case 'releve_temp_enceintes_soir':
      return `
        <fieldset class="modal-fieldset">
          <legend class="modal-fieldset-titre">Températures relevées (°C)</legend>
          <div class="modal-grille-2">
            ${champTemp('cf1', 'Chambre froide 1', 0, 4)}
            ${champTemp('cf2', 'Chambre froide 2', 0, 4)}
            ${champTemp('vitrine', 'Vitrine', 0, 4)}
            ${champTemp('labo', 'Laboratoire', 10, 15)}
          </div>
        </fieldset>`;

    case 'temp_lave_vaisselle':
      return `
        <fieldset class="modal-fieldset">
          <legend class="modal-fieldset-titre">Températures lave-vaisselle (°C)</legend>
          <div class="modal-grille-2">
            ${champTemp('lavage', 'Cycle lavage', 55, 65, '55–65 °C')}
            ${champTemp('rincage', 'Cycle rinçage', 82, 90, '82–90 °C')}
          </div>
        </fieldset>`;

    case 'suivi_temp_production':
      return `
        <fieldset class="modal-fieldset">
          <legend class="modal-fieldset-titre">Production / service</legend>
          <div class="modal-grille-2">
            ${champTemp('temperature', 'Température mesurée', -5, 10)}
            <div class="modal-champ">
              <label class="modal-champ-label" for="ds_produit">Produit / zone <span class="requis">*</span></label>
              <input id="ds_produit" name="ds_produit" class="modal-input" type="text"
                     placeholder="Ex : viande hachée, vitrine..." required>
            </div>
          </div>
        </fieldset>`;

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

    case 'pieges_rongeurs': {
      const rongeurs = pieges.filter(p => p.type === 'rongeur');
      if (rongeurs.length === 0) {
        return `<p class="modal-info">Aucun piège rongeur configuré — <a href="/admin.html">configurer</a></p>`;
      }
      return `
        <fieldset class="modal-fieldset">
          <legend class="modal-fieldset-titre">État des pièges rongeurs</legend>
          ${rongeurs.map(p => `
            <label class="modal-checkbox-ligne">
              <input type="checkbox" name="piege_${p.id}" id="piege_${p.id}">
              <span>
                <strong>${escHtml(p.identifiant)}</strong>
                ${p.localisation ? ` — ${escHtml(p.localisation)}` : ''}
                &ensp;— Rongeur présent
              </span>
            </label>`).join('')}
        </fieldset>`;
    }

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

    case 'controle_huile_friture':
      return `
        <fieldset class="modal-fieldset">
          <legend class="modal-fieldset-titre">Contrôle huile de friture</legend>
          <div class="modal-grille-2">
            ${champTemp('temperature', 'Température huile (°C)', 150, 180, '≤ 180 °C')}
            <div class="modal-champ">
              <label class="modal-champ-label" for="ds_aspect">Aspect visuel</label>
              <select id="ds_aspect" name="ds_aspect" class="modal-input">
                <option value="">— Sélectionner —</option>
                <option value="bon">Bon — huile claire</option>
                <option value="moyen">Moyen — légèrement foncée</option>
                <option value="mauvais">Mauvais — à changer</option>
              </select>
            </div>
          </div>
        </fieldset>`;

    case 'suivi_decongélation':
      return `
        <fieldset class="modal-fieldset">
          <legend class="modal-fieldset-titre">Suivi décongélation</legend>
          <div class="modal-grille-2">
            <div class="modal-champ">
              <label class="modal-champ-label" for="ds_produit_dec">Produit</label>
              <input id="ds_produit_dec" name="ds_produit_dec" class="modal-input" type="text"
                     placeholder="Ex : rôti de bœuf, pièce entière...">
            </div>
            ${champTemp('temperature', 'Température (°C)', -5, 4)}
          </div>
        </fieldset>`;

    case 'suivi_congelation':
      return `
        <fieldset class="modal-fieldset">
          <legend class="modal-fieldset-titre">Suivi congélation</legend>
          <div class="modal-grille-2">
            <div class="modal-champ">
              <label class="modal-champ-label" for="ds_produit_cong">Produit</label>
              <input id="ds_produit_cong" name="ds_produit_cong" class="modal-input" type="text"
                     placeholder="Ex : bavette, côte d'agneau...">
            </div>
            ${champTemp('temperature', 'Température congélateur (°C)', -25, -18, '≤ −18 °C')}
          </div>
        </fieldset>`;

    default:
      return '';  // Juste conformité + commentaire
  }
}

/** Génère un champ température avec indication du seuil */
function champTemp(name, label, min, max, aide) {
  const aideHtml = aide
    ? `<span class="modal-champ-aide">${aide}</span>`
    : `<span class="modal-champ-aide">Seuil : ${min} à ${max} °C</span>`;
  return `
    <div class="modal-champ">
      <label class="modal-champ-label" for="ds_${name}">${escHtml(label)}</label>
      <input id="ds_${name}" name="ds_${name}" class="modal-input modal-input--temp"
             type="number" step="0.1" inputmode="decimal"
             placeholder="0.0">
      ${aideHtml}
    </div>`;
}

/** Collecte les valeurs des champs spécifiques du formulaire courant */
function collecterDonneesSpecifiques(code) {
  const ds = {};
  const form = elModalForm;

  function val(id) {
    const el = form.querySelector(`[name="${id}"]`);
    return el ? el.value.trim() : undefined;
  }
  function num(id) {
    const v = val(id);
    return v !== '' && v !== undefined ? parseFloat(v) : null;
  }

  switch (code) {
    case 'releve_temp_enceintes_matin':
    case 'releve_temp_enceintes_soir':
      ds.temperatures = {
        cf1:     num('ds_cf1'),
        cf2:     num('ds_cf2'),
        vitrine: num('ds_vitrine'),
        labo:    num('ds_labo'),
      };
      break;

    case 'temp_lave_vaisselle':
      ds.temperatures = {
        lavage:  num('ds_lavage'),
        rincage: num('ds_rincage'),
      };
      break;

    case 'suivi_temp_production':
      ds.temperature = num('ds_temperature');
      ds.produit     = val('ds_produit');
      break;

    case 'nettoyage_desinfection':
      ds.produit_nettoyage = val('ds_produit_nett');
      ds.dilution          = val('ds_dilution');
      break;

    case 'pieges_rongeurs': {
      const etat = {};
      pieges.filter(p => p.type === 'rongeur').forEach(p => {
        const cb = form.querySelector(`[name="piege_${p.id}"]`);
        etat[p.identifiant] = cb ? cb.checked : false;
      });
      ds.pieges_rongeurs = etat;
      break;
    }

    case 'nettoyage_pieges_oiseaux': {
      const etat = {};
      pieges.filter(p => p.type === 'oiseau').forEach(p => {
        const cb = form.querySelector(`[name="piege_${p.id}"]`);
        etat[p.identifiant] = cb ? cb.checked : false;
      });
      ds.pieges_oiseaux = etat;
      break;
    }

    case 'controle_huile_friture':
      ds.temperature = num('ds_temperature');
      ds.aspect      = val('ds_aspect');
      break;

    case 'suivi_decongélation':
      ds.produit     = val('ds_produit_dec');
      ds.temperature = num('ds_temperature');
      break;

    case 'suivi_congelation':
      ds.produit     = val('ds_produit_cong');
      ds.temperature = num('ds_temperature');
      break;
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
    tache_type_id:      tacheCourante.id,
    operateur:          operateur,
    date_tache:         today,
    conforme:           conformeRadio.value === 'oui',
    commentaire:        commentaire || null,
    donnees_specifiques: ds,
  };

  elModalValider.disabled     = true;
  elModalValiderTexte.textContent = 'Envoi…';
  elModalErreur.hidden        = true;

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
    elModalValider.disabled     = false;
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

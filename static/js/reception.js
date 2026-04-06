'use strict';
/* ============================================================
   reception.js — Module Réception marchandises (wizard v2)
   Au Comptoir des Lilas — Mets Carnés Holding

   Flux : Personnel → Camion → Photo BL / Fournisseur
          → Produits (boucle) → Récap & Clôture → Confirmation
   ============================================================ */

// ── Références DOM ─────────────────────────────────────────
const elHorloge        = document.getElementById('rec-horloge');
const elBtnRetour      = document.getElementById('rec-btn-retour');
const elProgress       = document.getElementById('rec-progress');
const elBandeau        = document.getElementById('rec-bandeau');
const DOTS             = [0,1,2,3,4].map(i => document.getElementById(`dot-${i}`));

const elStep0          = document.getElementById('rec-step-0');
const elStep1          = document.getElementById('rec-step-1');
const elStep2          = document.getElementById('rec-step-2');
const elStep3          = document.getElementById('rec-step-3');
const elStep4          = document.getElementById('rec-step-4');
const elStepConfirm    = document.getElementById('rec-step-confirm');
const STEPS            = [elStep0, elStep1, elStep2, elStep3, elStep4, elStepConfirm];

// Étape 0
const elPersonnelGrille   = document.getElementById('rec-personnel-grille');
const elChargementPerso   = document.getElementById('rec-chargement-personnel');

// Étape 1
const elDateReception     = document.getElementById('rec-date-reception');
const elHeure             = document.getElementById('rec-heure');
const elTempCamion        = document.getElementById('rec-temp-camion');
const elPropreteOk        = document.getElementById('rec-proprete-ok');
const elPropreteNc        = document.getElementById('rec-proprete-nc');
const elCamionBadge       = document.getElementById('rec-camion-badge');
const elBtnCamionSuivant  = document.getElementById('rec-btn-camion-suivant');

// Étape 2
const elPhotoZone         = document.getElementById('rec-photo-zone');
const elInputPhoto        = document.getElementById('rec-input-photo');
const elPhotoIcone        = document.getElementById('rec-photo-icone');
const elPhotoTitre        = document.getElementById('rec-photo-titre');
const elPhotoVignette     = document.getElementById('rec-photo-vignette');
const elFournSearch       = document.getElementById('rec-fourn-search');
const elFournResults      = document.getElementById('rec-fourn-results');
const elFournSelWrap      = document.getElementById('rec-fourn-sel-wrap');
const elFournSelNom       = document.getElementById('rec-fourn-sel-nom');
const elFournSearchWrap   = document.getElementById('rec-fourn-search-wrap');
const elFournClear        = document.getElementById('rec-fourn-clear');
const elErreur2           = document.getElementById('rec-erreur-2');
const elBtnCreerFiche     = document.getElementById('rec-btn-creer-fiche');

// Étape 3
const elBandeauCamionChaud = document.getElementById('rec-bandeau-camion-chaud');
const elBandeauCoeur      = document.getElementById('rec-bandeau-coeur');
const elNbProduits        = document.getElementById('rec-nb-produits');
const elLignesListe       = document.getElementById('rec-lignes-liste');
const elProdSel           = document.getElementById('rec-produit-selectionne-wrap');
const elProdSelNom        = document.getElementById('rec-prod-sel-nom');
const elProdSelCode       = document.getElementById('rec-prod-sel-code');
const elBtnChangerProduit = document.getElementById('rec-btn-changer-produit');
const elProdSearchWrap    = document.getElementById('rec-produit-search-wrap');
const elProdSearch        = document.getElementById('rec-prod-search');
const elProdAutoComplete  = document.getElementById('rec-prod-autocomplete');
const elTempProduit       = document.getElementById('rec-temp-produit');
const elTempProduitLabel  = document.getElementById('rec-temp-produit-label');
const elTempVerdict       = document.getElementById('rec-temp-produit-verdict');
const elLot               = document.getElementById('rec-lot');
const elBtnPasLot         = document.getElementById('rec-btn-pas-lot');
const elBtnAnnulerLot     = document.getElementById('rec-btn-annuler-lot');
const elLotGenere         = document.getElementById('rec-lot-genere');
const elDlc               = document.getElementById('rec-dlc');
const elDlcBtn            = document.getElementById('rec-dlc-btn');
const elDluoBtn           = document.getElementById('rec-dluo-btn');
const elDlcLabelText      = document.getElementById('rec-dlc-label-text');
const elPh                = document.getElementById('rec-ph');
const elPhPlage           = document.getElementById('rec-ph-plage');
const elBtnAjouter        = document.getElementById('rec-btn-ajouter');
const elBtnEnregistrer    = document.getElementById('rec-btn-enregistrer');
const elBtnTerminer       = document.getElementById('rec-btn-terminer');

// Critères visuels
const CRITERES = ['couleur', 'consistance', 'exsudat', 'odeur'];

// Étape 4 — Récap
const elRecapCamionInfo   = document.getElementById('rec-recap-camion-info');
const elRecapCamionBadge  = document.getElementById('rec-recap-camion-badge');
const elConformiteGlobale = document.getElementById('rec-conformite-globale');
const elRecapLignes       = document.getElementById('rec-recap-lignes');
const elChkRefuse         = document.getElementById('rec-chk-refuse');
const elChkDdpp           = document.getElementById('rec-chk-ddpp');
const elCommentaireNc     = document.getElementById('rec-commentaire-nc');
const elErreur4           = document.getElementById('rec-erreur-4');
const elBtnCloturer       = document.getElementById('rec-btn-cloturer');

// Étape 4 — Procédure NC
const elNcProcedure       = document.getElementById('rec-nc-procedure');
const elNcStepA           = document.getElementById('rec-nc-step-a');
const elNcStepB           = document.getElementById('rec-nc-step-b');
const elNcProduitsCoeur   = document.getElementById('rec-nc-produits-coeur');
const elNcTousConformes   = document.getElementById('rec-nc-tous-conformes');
const elNcBtnASuivant     = document.getElementById('rec-nc-btn-a-suivant');
const elLivreurOui        = document.getElementById('rec-livreur-oui');
const elLivreurNon        = document.getElementById('rec-livreur-non');
const elSigZone           = document.getElementById('rec-sig-zone');
const elSigCanvas         = document.getElementById('rec-sig-canvas');
const elSigEffacer        = document.getElementById('rec-sig-effacer');
const elEtiqZone          = document.getElementById('rec-etiq-zone');
const elEtiqListe         = document.getElementById('rec-etiq-liste');
const elNcBtnBSuivant     = document.getElementById('rec-nc-btn-b-suivant');
const elPcrDoneBadge      = document.getElementById('rec-pcr-done-badge');

// Confirmation
const elConfirmDetail     = document.getElementById('rec-confirm-detail');
const elConfirmBadge      = document.getElementById('rec-confirm-badge');
const elConfirmCountdown  = document.getElementById('rec-confirm-countdown');
const elBtnHub            = document.getElementById('rec-btn-hub');

// Dialog inactivité
const elDialogInactivite  = document.getElementById('rec-dialog-inactivite');
const elDialogContinuer   = document.getElementById('rec-dialog-continuer');
const elDialogQuitter     = document.getElementById('rec-dialog-quitter');


// ── État ───────────────────────────────────────────────────
let etape              = 0;
let personnelId        = null;
let personnelPrenom    = null;
let propreteCamion     = 'satisfaisant';
let photoBlFile        = null;
let photoBlObjectUrl   = null;
let fournisseurId      = null;
let receptionId        = null;
let lignesAjoutees     = [];      // [{id, produit_nom, conforme, motifs, temp, lot, produit_id, fournisseur_id}]
let produitSelectionne = null;    // objet produit complet
let criteres           = {};      // {couleur:1, consistance:1, exsudat:1, odeur:1}
let timerInactivite    = null;
let timerConfirmation  = null;
let debounceTimer      = null;
let tousProduits       = [];
let tousFournisseurs   = [];
let textesAide         = {};

// NC procedure state
let ncProduits         = [];      // produits NC confirmés (après contrôle à cœur)
let ncProduitsInitiaux = [];      // produits NC initiaux (avant contrôle à cœur)
let ncCoeurResultats   = {};      // {ligne_id: {temp_coeur, conforme_apres_coeur}}
let livreurPresent     = null;    // true | false
let sigDessin          = false;
let sigCtx             = null;
let ncFicheIndex       = 0;       // index dans ncProduits pour PCR01

// État formulaire produit
let dlcMode            = 'dlc';   // 'dlc' ou 'dluo'
let lotInterneGenere   = false;   // true quand lot interne auto-généré
let ligneEnEdition     = null;    // {id, index} — null = mode ajout


// ── Horloge ────────────────────────────────────────────────
function majHorloge() {
  if (!elHorloge) return;
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();


// ── Inactivité ─────────────────────────────────────────────
const DELAI_INACTIVITE = 5 * 60 * 1000;

function resetInactivite() {
  if (elDialogInactivite && !elDialogInactivite.hidden) return;
  clearTimeout(timerInactivite);
  timerInactivite = setTimeout(() => {
    if (lignesAjoutees.length > 0 && etape < 5) {
      elDialogInactivite.hidden = false;
    } else {
      window.location.href = '/hub.html';
    }
  }, DELAI_INACTIVITE);
}

document.addEventListener('click',      resetInactivite, true);
document.addEventListener('touchstart', resetInactivite, { passive: true, capture: true });
document.addEventListener('input',      resetInactivite, true);
resetInactivite();

elDialogContinuer.addEventListener('click', () => {
  elDialogInactivite.hidden = true;
  resetInactivite();
});
elDialogQuitter.addEventListener('click', () => {
  window.location.href = '/hub.html';
});


// ── Fetch helper ───────────────────────────────────────────
async function apiFetch(url, options = {}) {
  const res = await fetch(url, { cache: 'no-store', ...options });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} — ${txt || url}`);
  }
  return res.json();
}


// ── Navigation wizard ──────────────────────────────────────
function allerEtape(cible) {
  etape = cible;

  // STEPS: [step0, step1, step2, step3, step4, confirm] — indices 0..5
  // "confirm" est l'index 5 mais la numérotation logique est aussi 5
  const idx = Math.min(cible, STEPS.length - 1);

  STEPS.forEach((el, i) => {
    el.classList.remove('actif', 'gauche');
    if (i < idx)      el.classList.add('gauche');
    else if (i === idx) el.classList.add('actif');
  });

  // Progress dots : étapes 0-4 (cible 5 = confirm → cacher dots)
  const estConfirm = (cible >= 5);
  elProgress.hidden = estConfirm;
  if (!estConfirm) {
    DOTS.forEach((dot, i) => {
      dot.classList.remove('actif', 'complet');
      if (i < cible)      dot.classList.add('complet');
      else if (i === cible) dot.classList.add('actif');
    });
  }

  // Bandeau personnel
  elBandeau.hidden = (cible === 0 || estConfirm);
  if (cible > 0 && !estConfirm && personnelPrenom) {
    elBandeau.textContent = `👤 ${personnelPrenom}`;
  }

  // Bandeau camion chaud (étape 3 uniquement — en-tête de section)
  if (elBandeauCamionChaud) {
    elBandeauCamionChaud.hidden = !(cible === 3 && camionEstChaud());
  }
  // Bandeau coeur dans form produit — masqué quand pas à l'étape 3 ou pas de produit sélectionné
  if (elBandeauCoeur && cible !== 3) elBandeauCoeur.hidden = true;

  // Bouton retour
  elBtnRetour.hidden = estConfirm;
}


// ── Retour ─────────────────────────────────────────────────
elBtnRetour.addEventListener('click', () => {
  if (etape === 0) {
    window.location.href = '/hub.html';
  } else if (etape === 3) {
    // Retour depuis produits : pas possible si fiche déjà créée → aller à étape 2
    allerEtape(2);
  } else if (etape <= 4) {
    allerEtape(etape - 1);
  }
});


// ── ÉTAPE 0 : Personnel ────────────────────────────────────
async function chargerPersonnel() {
  try {
    const liste = await apiFetch('/api/admin/personnel');
    elChargementPerso.remove();
    liste.forEach(p => {
      const btn = document.createElement('button');
      btn.className    = 'rec-btn-prenom';
      btn.textContent  = p.prenom;
      btn.dataset.id   = p.id;
      btn.dataset.prenom = p.prenom;
      btn.addEventListener('click', () => {
        personnelId     = p.id;
        personnelPrenom = p.prenom;
        // Initialiser date + heure à maintenant
        const now = new Date();
        elHeure.value = now.toTimeString().slice(0, 5);
        if (!elDateReception.value) {
          elDateReception.value = now.toISOString().slice(0, 10);
        }
        allerEtape(1);
      });
      elPersonnelGrille.appendChild(btn);
    });
    if (!liste.length) {
      elPersonnelGrille.innerHTML = '<div class="rec-chargement">Aucun personnel enregistré.</div>';
    }
  } catch {
    elChargementPerso.textContent = 'Impossible de charger le personnel.';
  }
}


// ── ÉTAPE 1 : Camion ───────────────────────────────────────
function camionEstChaud(tempMax) {
  // Si tempMax fourni : hors norme si temp camion > temp cible produit
  // Sinon (contexte global) : hors norme si >= 2°C (approximation)
  const t = parseFloat(elTempCamion.value);
  if (isNaN(t)) return false;
  if (tempMax !== undefined) return t > tempMax;
  return t >= 2;
}

function majBadgeCamion() {
  const temp = parseFloat(elTempCamion.value);

  if (isNaN(temp)) {
    elCamionBadge.className = 'rec-badge neutre';
    elCamionBadge.textContent = '— Non évalué';
  } else if (temp >= 2) {
    // Signal d'alerte uniquement — la temp camion ne crée PAS de NC
    elCamionBadge.className = 'rec-badge attention';
    elCamionBadge.textContent = '⚠️ Contrôle à cœur requis sur chaque produit';
  } else {
    elCamionBadge.className = 'rec-badge conforme';
    elCamionBadge.textContent = '✓ Température OK';
  }

  // Mettre à jour aussi le label temp produit si on est à l'étape 3
  if (produitSelectionne) majLabelTempProduit();
}

elTempCamion.addEventListener('input', majBadgeCamion);

elPropreteOk.addEventListener('click', () => {
  propreteCamion = 'satisfaisant';
  elPropreteOk.classList.add('ok-sel');
  elPropreteNc.classList.remove('nc-sel');
  elPropreteOk.setAttribute('aria-pressed', 'true');
  elPropreteNc.setAttribute('aria-pressed', 'false');
  majBadgeCamion();
});

elPropreteNc.addEventListener('click', () => {
  propreteCamion = 'non_satisfaisant';
  elPropreteNc.classList.add('nc-sel');
  elPropreteOk.classList.remove('ok-sel');
  elPropreteNc.setAttribute('aria-pressed', 'true');
  elPropreteOk.setAttribute('aria-pressed', 'false');
  majBadgeCamion();
});

elBtnCamionSuivant.addEventListener('click', () => {
  if (!elDateReception.value) {
    elDateReception.focus();
    elDateReception.reportValidity();
    return;
  }
  if (elTempCamion.value.trim() === '') {
    elTempCamion.focus();
    elTempCamion.reportValidity();
    return;
  }
  allerEtape(2);
});


// ── ÉTAPE 2 : Photo BL + Fournisseur ──────────────────────
// Photo
elPhotoZone.addEventListener('click', () => elInputPhoto.click());
elPhotoZone.addEventListener('keydown', e => {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); elInputPhoto.click(); }
});

elInputPhoto.addEventListener('change', () => {
  const file = elInputPhoto.files[0];
  if (!file) return;
  photoBlFile = file;
  if (photoBlObjectUrl) URL.revokeObjectURL(photoBlObjectUrl);
  photoBlObjectUrl = URL.createObjectURL(file);
  elPhotoVignette.src = photoBlObjectUrl;
  elPhotoVignette.hidden = false;
  elPhotoIcone.textContent = '✅';
  elPhotoTitre.textContent = 'Photo prise';
});

// Fournisseur
async function chargerFournisseurs() {
  try {
    tousFournisseurs = await apiFetch('/api/fournisseurs');
  } catch {
    tousFournisseurs = [];
  }
}

function afficherFournisseurs(liste) {
  elFournResults.innerHTML = '';
  if (!liste.length) {
    elFournResults.hidden = true;
    return;
  }
  liste.slice(0, 10).forEach(f => {
    const div = document.createElement('div');
    div.className = 'rec-fourn-item';
    div.textContent = f.nom;
    div.addEventListener('click', () => selectionnerFournisseur(f));
    elFournResults.appendChild(div);
  });
  elFournResults.hidden = false;
}

function selectionnerFournisseur(f) {
  fournisseurId = f.id;
  elFournSelNom.textContent = f.nom;
  elFournSelWrap.hidden = false;
  elFournSearchWrap.hidden = true;
  elFournResults.hidden = true;
}

elFournClear.addEventListener('click', () => {
  fournisseurId = null;
  elFournSelWrap.hidden = true;
  elFournSearchWrap.hidden = false;
  elFournSearch.value = '';
  elFournResults.hidden = true;
});

elFournSearch.addEventListener('input', () => {
  const q = elFournSearch.value.trim().toLowerCase();
  if (!q) { elFournResults.hidden = true; return; }
  const filtres = tousFournisseurs.filter(f => f.nom.toLowerCase().includes(q));
  afficherFournisseurs(filtres);
});

// Créer la fiche
elBtnCreerFiche.addEventListener('click', creerFiche);

async function creerFiche() {
  elErreur2.hidden = true;
  elBtnCreerFiche.disabled = true;
  elBtnCreerFiche.textContent = 'Création…';

  try {
    const fd = new FormData();
    fd.append('personnel_id',    personnelId);
    fd.append('heure_reception', elHeure.value || new Date().toTimeString().slice(0, 5));
    if (elDateReception.value) fd.append('date_reception', elDateReception.value);
    if (elTempCamion.value !== '') {
      fd.append('temperature_camion', elTempCamion.value);
    }
    fd.append('proprete_camion', propreteCamion);
    if (fournisseurId) fd.append('fournisseur_principal_id', fournisseurId);
    if (photoBlFile)   fd.append('photo_bl', photoBlFile, photoBlFile.name);

    const rec = await apiFetch('/api/receptions', {
      method: 'POST',
      body: fd,
    });
    receptionId = rec.id;

    // Réinitialiser le formulaire produit et passer à l'étape 3
    reinitFormProduit();
    majListeLignes();
    allerEtape(3);

  } catch (err) {
    elErreur2.textContent = `Erreur : ${err.message}`;
    elErreur2.hidden = false;
  } finally {
    elBtnCreerFiche.disabled = false;
    elBtnCreerFiche.textContent = 'Créer la fiche →';
  }
}


// ── ÉTAPE 3 : Produits ─────────────────────────────────────
async function chargerProduits() {
  try {
    tousProduits = await apiFetch('/api/produits');
  } catch {
    tousProduits = [];
  }
}

async function chargerTextesAide() {
  try {
    textesAide = await apiFetch('/api/receptions/textes-aide-visuel');
  } catch {
    textesAide = {};
  }
}

function filtrerProduits(q) {
  if (!q) return tousProduits.slice(0, 12);
  const ql = q.toLowerCase();
  return tousProduits.filter(p =>
    p.nom.toLowerCase().includes(ql) ||
    (p.code_unique && p.code_unique.toLowerCase().includes(ql))
  ).slice(0, 12);
}

function afficherAutoComplete(liste) {
  elProdAutoComplete.innerHTML = '';
  if (!liste.length) {
    elProdAutoComplete.hidden = true;
    return;
  }
  liste.forEach(p => {
    const div = document.createElement('div');
    div.className = 'rec-autocomplete-item';
    div.setAttribute('role', 'option');
    const nom  = document.createElement('span');
    nom.textContent = p.nom;
    const code = document.createElement('span');
    code.className = 'rec-autocomplete-code';
    code.textContent = p.code_unique || '';
    div.appendChild(nom);
    div.appendChild(code);
    div.addEventListener('click', () => selectionnerProduit(p));
    elProdAutoComplete.appendChild(div);
  });
  elProdAutoComplete.hidden = false;
}

function selectionnerProduit(p) {
  produitSelectionne = p;
  elProdSelNom.textContent  = p.nom;
  elProdSelCode.textContent = p.code_unique || '';
  elProdSel.hidden      = false;
  elProdSearchWrap.hidden = true;
  elProdAutoComplete.hidden = true;
  elProdSearch.value = '';

  // Mise à jour aide visuelle selon l'espèce
  majAideVisuel(p.espece);
  // pH plage
  const aideEspece = textesAide[p.espece];
  elPhPlage.textContent = aideEspece ? `(norme : ${aideEspece.ph.normal})` : '';

  // Label temperature selon statut camion
  majLabelTempProduit();
  majBtnAjouter();
}

function majAideVisuel(espece) {
  const aide = textesAide[espece];
  ['couleur', 'consistance', 'exsudat', 'odeur'].forEach(c => {
    const el = document.getElementById(`rec-aide-${c}`);
    if (el) el.textContent = aide ? `Normal : ${aide[c].normal}` : '';
  });
}

elBtnChangerProduit.addEventListener('click', () => {
  produitSelectionne = null;
  elProdSel.hidden = true;
  elProdSearchWrap.hidden = false;
  elProdSearch.value = '';
  afficherAutoComplete(tousProduits.slice(0, 12));
  elProdSearch.focus();
  majBtnAjouter();
  elTempVerdict.textContent = '';
  elTempVerdict.className = 'rec-temp-verdict';
  if (elBandeauCoeur) elBandeauCoeur.hidden = true;
  if (elTempProduitLabel) {
    elTempProduitLabel.firstChild.textContent = 'Température à réception (°C) ';
    elTempProduitLabel.classList.remove('coeur-label');
  }
});

elProdSearch.addEventListener('input', () => {
  const q = elProdSearch.value.trim();
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    afficherAutoComplete(filtrerProduits(q));
  }, 180);
});
elProdSearch.addEventListener('focus', () => {
  if (!produitSelectionne) {
    afficherAutoComplete(filtrerProduits(elProdSearch.value));
  }
});
document.addEventListener('click', e => {
  if (!elProdAutoComplete.contains(e.target) && e.target !== elProdSearch) {
    elProdAutoComplete.hidden = true;
  }
}, true);

// Température produit → verdict temps réel
function parseIntervalleTemp(str) {
  if (!str) return null;
  const m = str.match(/([-+]?\d+(?:\.\d+)?)\s*°C\s*à\s*([-+]?\d+(?:\.\d+)?)\s*°C/i);
  if (!m) return null;
  return { min: parseFloat(m[1]), max: parseFloat(m[2]) };
}

function majLabelTempProduit() {
  if (!produitSelectionne) return;
  const intervalle = parseIntervalleTemp(produitSelectionne.temperature_conservation);
  const tempMax = intervalle ? intervalle.max : undefined;
  const chaud = camionEstChaud(tempMax);

  if (elBandeauCoeur) elBandeauCoeur.hidden = !chaud;

  if (elTempProduitLabel) {
    const span = elTempProduitLabel.querySelector('.rec-temp-verdict') ||
                 document.createElement('span');
    if (chaud) {
      elTempProduitLabel.firstChild.textContent = 'Température à cœur (°C) ';
      elTempProduitLabel.classList.add('coeur-label');
    } else {
      elTempProduitLabel.firstChild.textContent = 'Température à réception (°C) ';
      elTempProduitLabel.classList.remove('coeur-label');
    }
  }
}

function majVerdictTemp() {
  const val = parseFloat(elTempProduit.value);
  if (isNaN(val) || !produitSelectionne) {
    elTempVerdict.textContent = '';
    elTempVerdict.className = 'rec-temp-verdict';
    return;
  }
  const intervalle = parseIntervalleTemp(produitSelectionne.temperature_conservation);
  if (!intervalle) {
    elTempVerdict.textContent = '';
    elTempVerdict.className = 'rec-temp-verdict';
    return;
  }

  // Règle unifiée : NC si temp > cible_max + 2°C
  const conforme = val <= (intervalle.max + 2.0);
  elTempVerdict.textContent = conforme ? '✓ OK' : '✗ NC';
  elTempVerdict.className   = 'rec-temp-verdict ' + (conforme ? 'ok' : 'nc');
}
elTempProduit.addEventListener('input', majVerdictTemp);

// Critères visuels toggles
function reinitCriteres() {
  criteres = { couleur: 1, consistance: 1, exsudat: 1, odeur: 1 };
  CRITERES.forEach(c => {
    const [btnOk, btnNc] = document.querySelectorAll(`[data-critere="${c}"]`);
    btnOk.classList.add('ok-sel');
    btnOk.setAttribute('aria-pressed', 'true');
    btnNc.classList.remove('nc-sel');
    btnNc.setAttribute('aria-pressed', 'false');
    const obsEl = document.getElementById(`rec-obs-${c}`);
    if (obsEl) { obsEl.value = ''; obsEl.hidden = true; }
  });
}

document.querySelectorAll('[data-critere]').forEach(btn => {
  btn.addEventListener('click', () => {
    const c   = btn.dataset.critere;
    const val = parseInt(btn.dataset.val, 10);
    criteres[c] = val;

    const [btnOk, btnNc] = document.querySelectorAll(`[data-critere="${c}"]`);
    if (val === 1) {
      btnOk.classList.add('ok-sel');
      btnNc.classList.remove('nc-sel');
      btnOk.setAttribute('aria-pressed', 'true');
      btnNc.setAttribute('aria-pressed', 'false');
    } else {
      btnNc.classList.add('nc-sel');
      btnOk.classList.remove('ok-sel');
      btnNc.setAttribute('aria-pressed', 'true');
      btnOk.setAttribute('aria-pressed', 'false');
    }

    const obsEl = document.getElementById(`rec-obs-${c}`);
    if (obsEl) obsEl.hidden = (val === 1);
  });
});

function majBtnAjouter() {
  const lotOk  = lotInterneGenere || elLot.value.trim() !== '';
  const dlcOk  = elDlc.value.trim() !== '';
  const ok = produitSelectionne !== null && lotOk && dlcOk;
  elBtnAjouter.disabled   = !ok;
  if (elBtnEnregistrer) elBtnEnregistrer.disabled = !ok;
}

// ── Lot interne ────────────────────────────────────────────
elBtnPasLot.addEventListener('click', async () => {
  if (!produitSelectionne || !receptionId) return;

  // D'abord créer une ligne temporaire pour avoir un ligne_id ?
  // On génère depuis le endpoint lot-interne en passant par un appel dédié
  // mais sans ligne_id on peut appeler directement l'endpoint avec code_unique
  elBtnPasLot.disabled = true;
  elBtnPasLot.textContent = '⏳…';
  try {
    const code = produitSelectionne.code_unique;
    const today = new Date().toLocaleDateString('fr-FR', {
      day: '2-digit', month: '2-digit', year: '2-digit',
    }).replace(/\//g, '');
    // Appel API générique (sera créé côté backend avec code_unique)
    const data = await apiFetch(
      `/api/receptions/${receptionId}/lot-interne?code_unique=${encodeURIComponent(code)}`
    );
    const lotNum = data.lot_interne;
    elLot.value    = lotNum;
    elLot.readOnly = true;
    elLot.style.background = '#f0faf3';
    elLotGenere.textContent = `Lot interne : ${lotNum}`;
    elLotGenere.hidden = false;
    elBtnPasLot.hidden = true;
    elBtnAnnulerLot.hidden = false;
    lotInterneGenere = true;
    majBtnAjouter();
  } catch (e) {
    alert(`Erreur génération lot : ${e.message}`);
  } finally {
    elBtnPasLot.disabled = false;
    elBtnPasLot.textContent = 'Pas de N° de lot';
  }
});

elBtnAnnulerLot.addEventListener('click', () => {
  elLot.value    = '';
  elLot.readOnly = false;
  elLot.style.background = '';
  elLotGenere.hidden = true;
  elBtnPasLot.hidden = false;
  elBtnAnnulerLot.hidden = true;
  lotInterneGenere = false;
  majBtnAjouter();
});

elLot.addEventListener('input', majBtnAjouter);

// ── DLC / DLUO toggle ──────────────────────────────────────
elDlcBtn.addEventListener('click', () => {
  dlcMode = 'dlc';
  elDlcBtn.classList.add('ok-sel');
  elDluoBtn.classList.remove('ok-sel');
  elDlcBtn.setAttribute('aria-pressed', 'true');
  elDluoBtn.setAttribute('aria-pressed', 'false');
  elDlcLabelText.textContent = 'DLC';
});
elDluoBtn.addEventListener('click', () => {
  dlcMode = 'dluo';
  elDluoBtn.classList.add('ok-sel');
  elDlcBtn.classList.remove('ok-sel');
  elDluoBtn.setAttribute('aria-pressed', 'true');
  elDlcBtn.setAttribute('aria-pressed', 'false');
  elDlcLabelText.textContent = 'DLUO';
});
elDlc.addEventListener('input', majBtnAjouter);

function reinitFormProduit() {
  produitSelectionne = null;
  ligneEnEdition     = null;
  lotInterneGenere   = false;
  dlcMode            = 'dlc';

  elProdSel.hidden       = true;
  elProdSearchWrap.hidden = false;
  elProdSearch.value      = '';
  elProdAutoComplete.hidden = true;
  elTempProduit.value     = '';
  elTempVerdict.textContent = '';
  elTempVerdict.className = 'rec-temp-verdict';

  // Lot
  elLot.value    = '';
  elLot.readOnly = false;
  elLot.style.background = '';
  elLotGenere.hidden = true;
  elBtnPasLot.hidden = false;
  elBtnAnnulerLot.hidden = true;

  // DLC reset to DLC mode
  elDlc.value = '';
  elDlcBtn.classList.add('ok-sel');
  elDluoBtn.classList.remove('ok-sel');
  elDlcBtn.setAttribute('aria-pressed', 'true');
  elDluoBtn.setAttribute('aria-pressed', 'false');
  elDlcLabelText.textContent = 'DLC';

  elPh.value  = '';
  elPhPlage.textContent = '';

  // Reset bandeau coeur
  if (elBandeauCoeur) elBandeauCoeur.hidden = true;
  if (elTempProduitLabel) {
    elTempProduitLabel.firstChild.textContent = 'Température à réception (°C) ';
    elTempProduitLabel.classList.remove('coeur-label');
  }

  CRITERES.forEach(c => {
    document.getElementById(`rec-aide-${c}`).textContent = '';
  });
  reinitCriteres();

  // Boutons footer
  elBtnAjouter.hidden    = false;
  if (elBtnEnregistrer) elBtnEnregistrer.hidden = true;

  majBtnAjouter();
}

function majListeLignes() {
  elNbProduits.textContent = lignesAjoutees.length;
  elLignesListe.innerHTML  = '';
  lignesAjoutees.forEach((l, idx) => {
    const carte = document.createElement('div');
    carte.className = 'rec-ligne-carte';
    if (ligneEnEdition && ligneEnEdition.id === l.id) carte.classList.add('edition');

    const info = document.createElement('div');
    info.className = 'rec-ligne-info';

    const nom = document.createElement('div');
    nom.className = 'rec-ligne-nom';
    nom.textContent = l.produit_nom;

    const detail = document.createElement('div');
    detail.className = 'rec-ligne-detail';
    const parts = [];
    if (l.temperature_reception !== null && l.temperature_reception !== undefined) {
      parts.push(`${l.temperature_reception}°C`);
    }
    if (l.numero_lot) parts.push(l.numero_lot);
    detail.textContent = parts.join(' · ');

    info.appendChild(nom);
    if (parts.length) info.appendChild(detail);

    const btnModif = document.createElement('button');
    btnModif.className   = 'rec-ligne-modifier';
    btnModif.textContent = '✏️';
    btnModif.title       = 'Modifier ce produit';
    btnModif.addEventListener('click', () => chargerLigneEnEdition(l, idx));

    const badge = document.createElement('span');
    badge.className = 'rec-ligne-badge ' + (l.conforme ? 'ok' : 'nc');
    badge.textContent = l.conforme ? '✓ OK' : '✗ NC';

    carte.appendChild(info);
    carte.appendChild(btnModif);
    carte.appendChild(badge);
    elLignesListe.appendChild(carte);
  });

  elBtnTerminer.disabled = (lignesAjoutees.length === 0);
}

function chargerLigneEnEdition(l, idx) {
  ligneEnEdition = { id: l.id, index: idx };

  // Restaurer le produit
  const produit = tousProduits.find(p => p.id === l.produit_id);
  if (produit) selectionnerProduit(produit);

  // Restaurer température
  elTempProduit.value = l.temperature_reception != null ? l.temperature_reception : '';

  // Restaurer lot
  elLot.readOnly = false;
  elLot.style.background = '';
  elLot.value = l.numero_lot || '';
  lotInterneGenere = !!l.lot_interne;
  if (lotInterneGenere) {
    elLot.readOnly = true;
    elLot.style.background = '#f0faf3';
    elLotGenere.textContent = `Lot interne : ${l.numero_lot}`;
    elLotGenere.hidden = false;
    elBtnPasLot.hidden = true;
    elBtnAnnulerLot.hidden = false;
  }

  // Restaurer DLC/DLUO
  if (l.dluo) {
    dlcMode = 'dluo';
    elDluoBtn.classList.add('ok-sel');
    elDlcBtn.classList.remove('ok-sel');
    elDlcLabelText.textContent = 'DLUO';
    elDlc.value = l.dluo;
  } else {
    dlcMode = 'dlc';
    elDlcBtn.classList.add('ok-sel');
    elDluoBtn.classList.remove('ok-sel');
    elDlcLabelText.textContent = 'DLC';
    elDlc.value = l.dlc || '';
  }

  // Boutons footer
  elBtnAjouter.hidden    = true;
  if (elBtnEnregistrer) elBtnEnregistrer.hidden = false;
  majBtnAjouter();
  majListeLignes(); // refresh cartes

  // Scroll vers le formulaire
  document.querySelector('.rec-form-produit').scrollIntoView({ behavior: 'smooth' });
}

elBtnAjouter.addEventListener('click', ajouterLigne);
if (elBtnEnregistrer) elBtnEnregistrer.addEventListener('click', enregistrerModification);

function _buildPayload() {
  const payload = {
    produit_id: produitSelectionne.id,
    couleur_conforme:     criteres.couleur,
    consistance_conforme: criteres.consistance,
    exsudat_conforme:     criteres.exsudat,
    odeur_conforme:       criteres.odeur,
    lot_interne:          lotInterneGenere ? 1 : 0,
  };
  const obsC = document.getElementById('rec-obs-couleur').value.trim();
  const obsT = document.getElementById('rec-obs-consistance').value.trim();
  const obsE = document.getElementById('rec-obs-exsudat').value.trim();
  const obsO = document.getElementById('rec-obs-odeur').value.trim();
  if (obsC) payload.couleur_observation    = obsC;
  if (obsT) payload.consistance_observation = obsT;
  if (obsE) payload.exsudat_observation    = obsE;
  if (obsO) payload.odeur_observation      = obsO;
  const tv = parseFloat(elTempProduit.value);
  if (!isNaN(tv)) payload.temperature_reception = tv;
  const lot = elLot.value.trim();
  if (lot) payload.numero_lot = lot;
  const dateVal = elDlc.value;
  if (dateVal) {
    if (dlcMode === 'dluo') payload.dluo = dateVal;
    else                    payload.dlc  = dateVal;
  }
  const ph = parseFloat(elPh.value);
  if (!isNaN(ph)) payload.ph_valeur = ph;
  return payload;
}

function _ligneToLocal(ligne, produit) {
  const motifsNc = [];
  if (ligne.temperature_conforme === 0) motifsNc.push('température');
  if (ligne.couleur_conforme     === 0) motifsNc.push('couleur');
  if (ligne.consistance_conforme === 0) motifsNc.push('consistance');
  if (ligne.exsudat_conforme     === 0) motifsNc.push('exsudat');
  if (ligne.odeur_conforme       === 0) motifsNc.push('odeur');
  if (ligne.ph_conforme          === 0) motifsNc.push('pH');
  return {
    id:                  ligne.id,
    produit_id:          produit.id,
    produit_nom:         produit.nom,
    fournisseur_id:      fournisseurId || null,
    conforme:            ligne.conforme,
    temperature_reception: ligne.temperature_reception,
    numero_lot:          ligne.numero_lot,
    lot_interne:         ligne.lot_interne,
    dlc:                 ligne.dlc,
    dluo:                ligne.dluo,
    motifs:              motifsNc,
  };
}

async function ajouterLigne() {
  if (!produitSelectionne || !receptionId) return;

  elBtnAjouter.disabled = true;
  elBtnAjouter.textContent = 'Ajout…';

  try {
    const ligne = await apiFetch(`/api/receptions/${receptionId}/lignes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(_buildPayload()),
    });

    lignesAjoutees.push(_ligneToLocal(ligne, produitSelectionne));
    majListeLignes();
    reinitFormProduit();
    document.querySelector('.rec-produits-liste-ajoutee').scrollTop = 9999;

  } catch (err) {
    alert(`Erreur lors de l'ajout : ${err.message}`);
  } finally {
    elBtnAjouter.disabled = !produitSelectionne;
    elBtnAjouter.textContent = '+ Ajouter';
  }
}

async function enregistrerModification() {
  if (!produitSelectionne || !receptionId || !ligneEnEdition) return;

  if (elBtnEnregistrer) { elBtnEnregistrer.disabled = true; elBtnEnregistrer.textContent = 'Enregistrement…'; }

  try {
    const ligne = await apiFetch(
      `/api/receptions/${receptionId}/lignes/${ligneEnEdition.id}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(_buildPayload()),
      }
    );

    lignesAjoutees[ligneEnEdition.index] = _ligneToLocal(ligne, produitSelectionne);
    majListeLignes();
    reinitFormProduit();

  } catch (err) {
    alert(`Erreur lors de la modification : ${err.message}`);
  } finally {
    if (elBtnEnregistrer) { elBtnEnregistrer.disabled = false; elBtnEnregistrer.textContent = '✓ Enregistrer'; }
  }
}

elBtnTerminer.addEventListener('click', () => {
  if (lignesAjoutees.length === 0) return;
  remplirRecap();
  initNcProcedure();
  allerEtape(4);
});


// ── ÉTAPE 4 : Récap + Clôture ──────────────────────────────
function remplirRecap() {
  // Camion
  const tempCamion = parseFloat(elTempCamion.value);
  const infoTexte  = [];
  if (!isNaN(tempCamion)) infoTexte.push(`Température : ${tempCamion}°C`);
  infoTexte.push(`Propreté : ${propreteCamion === 'satisfaisant' ? 'Satisfaisante' : 'Non satisfaisante'}`);
  elRecapCamionInfo.innerHTML = infoTexte.join('<br>');

  // La température camion ne crée PAS de NC — seule la propreté compte
  const camionProprete = propreteCamion === 'satisfaisant';
  const camionChaud    = !isNaN(tempCamion) && tempCamion >= 2;
  if (!camionProprete) {
    elRecapCamionBadge.className = 'rec-badge nc';
    elRecapCamionBadge.textContent = '✗ Propreté NC';
  } else if (camionChaud) {
    elRecapCamionBadge.className = 'rec-badge attention';
    elRecapCamionBadge.textContent = '⚠️ Contrôle à cœur requis';
  } else {
    elRecapCamionBadge.className = 'rec-badge conforme';
    elRecapCamionBadge.textContent = '✓ Conforme';
  }

  // Conformité globale estimée (avant clôture serveur)
  // La temp camion ne génère pas de NC — seule propreté + produits
  const toutesConformes = lignesAjoutees.every(l => l.conforme);
  const globalOk = toutesConformes && camionProprete;
  elConformiteGlobale.className = 'rec-conformite-globale ' + (globalOk ? 'conforme' : 'nc');
  elConformiteGlobale.textContent = globalOk
    ? '✓ Tout conforme'
    : '✗ Présence de non-conformité(s)';

  // Liste produits
  elRecapLignes.innerHTML = '';
  lignesAjoutees.forEach(l => {
    const row = document.createElement('div');
    row.className = 'rec-recap-ligne-item';

    const left = document.createElement('div');
    const nom  = document.createElement('div');
    nom.className = 'rec-recap-ligne-nom';
    nom.textContent = l.produit_nom;
    const det = document.createElement('div');
    det.className = 'rec-recap-ligne-detail';
    const parts = [];
    if (l.temperature_reception !== null && l.temperature_reception !== undefined) {
      parts.push(`${l.temperature_reception}°C`);
    }
    if (l.numero_lot) parts.push(`Lot : ${l.numero_lot}`);
    det.textContent = parts.join(' · ');
    left.appendChild(nom);
    if (parts.length) left.appendChild(det);

    const badge = document.createElement('span');
    badge.className = 'rec-ligne-badge ' + (l.conforme ? 'ok' : 'nc');
    badge.textContent = l.conforme ? '✓ OK' : '✗ NC';

    row.appendChild(left);
    row.appendChild(badge);
    elRecapLignes.appendChild(row);
  });
}

// ── PROCÉDURE NC ───────────────────────────────────────────

function initNcProcedure() {
  ncProduitsInitiaux = lignesAjoutees.filter(l => !l.conforme);
  ncProduits         = [...ncProduitsInitiaux];
  ncCoeurResultats   = {};
  livreurPresent     = null;
  ncFicheIndex       = 0;

  const aNc = ncProduitsInitiaux.length > 0;
  elNcProcedure.hidden = !aNc;
  elBtnCloturer.disabled = aNc;

  if (!aNc) return;

  // Réinitialiser les sous-étapes
  elNcStepA.hidden = false;
  elNcStepB.hidden = true;
  elSigZone.hidden = true;
  elEtiqZone.hidden = true;
  elNcBtnASuivant.disabled = true;
  elNcBtnBSuivant.disabled = true;
  if (elNcTousConformes) elNcTousConformes.hidden = true;
  elLivreurOui.className = 'rec-livreur-btn';
  elLivreurNon.className = 'rec-livreur-btn';

  // Construire la liste des contrôles à cœur
  elNcProduitsCoeur.innerHTML = '';
  ncProduitsInitiaux.forEach(l => {
    const produit = tousProduits.find(p => p.id === l.produit_id);
    const intervalle = produit ? parseIntervalleTemp(produit.temperature_conservation) : null;
    const tempMax = intervalle ? intervalle.max : null;

    const row = document.createElement('div');
    row.className = 'rec-nc-coeur-row';
    row.dataset.ligneId = l.id;

    const nomEl = document.createElement('div');
    nomEl.className = 'rec-nc-produit-nom';
    nomEl.textContent = l.produit_nom;
    row.appendChild(nomEl);

    const motifEl = document.createElement('div');
    motifEl.className = 'rec-nc-motif';
    const tempText = l.temperature_reception != null ? ` — Temp. initiale : ${l.temperature_reception}°C` : '';
    motifEl.textContent = `✗ NC : ${l.motifs.join(', ') || 'non-conformité'}${tempText}`;
    row.appendChild(motifEl);

    const wrap = document.createElement('div');
    wrap.className = 'rec-nc-coeur-wrap';

    const label = document.createElement('label');
    label.style.cssText = 'font-size:.85rem;font-weight:600;color:var(--color-text)';
    label.textContent = 'Temp. à cœur (°C) :';

    const input = document.createElement('input');
    input.type = 'number';
    input.inputMode = 'decimal';
    input.step = '0.1';
    input.className = 'rec-nc-coeur-input';
    input.placeholder = 'ex : 3.5';

    const badge = document.createElement('span');
    badge.className = 'rec-nc-coeur-badge';

    input.addEventListener('input', () => {
      const val = parseFloat(input.value);
      if (isNaN(val) || tempMax === null) {
        badge.textContent = '';
        badge.className = 'rec-nc-coeur-badge';
      } else {
        // Seuil à cœur : conforme si <= cible + 2°C
        const conforme = val <= (tempMax + 2.0);
        badge.textContent = conforme ? '✓ Conforme après contrôle' : '✗ Non conforme confirmé';
        badge.className = 'rec-nc-coeur-badge ' + (conforme ? 'ok' : 'nc');
        ncCoeurResultats[l.id] = { temp_coeur: val, conforme_apres_coeur: conforme };
      }
      majEtatCoeur();
    });

    wrap.appendChild(label);
    wrap.appendChild(input);
    wrap.appendChild(badge);
    row.appendChild(wrap);
    elNcProduitsCoeur.appendChild(row);
  });
}

function majEtatCoeur() {
  // Tous renseignés ?
  const tousRenseignes = ncProduitsInitiaux.every(l => l.id in ncCoeurResultats);
  if (!tousRenseignes) {
    elNcBtnASuivant.disabled = true;
    if (elNcTousConformes) elNcTousConformes.hidden = true;
    return;
  }

  // Recalculer ncProduits = ceux qui restent NC après coeur
  ncProduits = ncProduitsInitiaux.filter(l => {
    const r = ncCoeurResultats[l.id];
    return !r || !r.conforme_apres_coeur;
  });

  const tousConformes = ncProduits.length === 0;
  if (elNcTousConformes) elNcTousConformes.hidden = !tousConformes;

  elNcBtnASuivant.disabled = false;
  // Si tous conformes après coeur → débloquer clôture directement
  if (tousConformes) {
    elNcBtnASuivant.textContent = 'Clôturer →';
  } else {
    elNcBtnASuivant.textContent = 'Suivant →';
  }
}

// Sous-étape A → B (ou clôture directe si tous conformes)
elNcBtnASuivant.addEventListener('click', () => {
  if (ncProduits.length === 0) {
    // Tous conformes après contrôle à cœur → débloquer clôture
    elNcProcedure.hidden = true;
    if (elPcrDoneBadge) {
      elPcrDoneBadge.textContent = '✓ Tous les produits conformes après contrôle à cœur';
      elPcrDoneBadge.hidden = false;
    }
    elBtnCloturer.disabled = false;
    return;
  }
  elNcStepA.hidden = true;
  elNcStepB.hidden = false;
  initSignatureCanvas();
});

// Livreur présent / absent
elLivreurOui.addEventListener('click', () => {
  livreurPresent = true;
  elLivreurOui.className = 'rec-livreur-btn sel-oui';
  elLivreurNon.className = 'rec-livreur-btn';
  elSigZone.hidden  = false;
  elEtiqZone.hidden = true;
  elNcBtnBSuivant.disabled = false;
});

elLivreurNon.addEventListener('click', () => {
  livreurPresent = false;
  elLivreurNon.className = 'rec-livreur-btn sel-non';
  elLivreurOui.className = 'rec-livreur-btn';
  elSigZone.hidden  = true;
  elEtiqZone.hidden = false;
  // Construire les boutons étiquettes
  elEtiqListe.innerHTML = '';
  ncProduits.forEach(l => {
    const btn = document.createElement('button');
    btn.className = 'rec-etiq-reprise-btn';
    btn.innerHTML = `🖨️ &nbsp;<span>Étiquette À REPRENDRE — ${l.produit_nom}</span>`;
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      try {
        const fourn = tousFournisseurs.find(f => f.id === l.fournisseur_id);
        await apiFetch('/api/impression/etiquette-reprise', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            produit_nom:      l.produit_nom,
            fournisseur_nom:  fourn ? fourn.nom : (fournisseurId ? '' : 'Inconnu'),
            motif:            l.motifs.join(', ') || 'non-conformité',
            operateur_prenom: personnelPrenom,
            date_refus:       new Date().toISOString().slice(0, 10),
          }),
        });
        btn.classList.add('imprime');
        btn.innerHTML = `✓ &nbsp;<span>Imprimé — ${l.produit_nom}</span>`;
      } catch (e) {
        btn.disabled = false;
        alert(`Impression échouée : ${e.message}`);
      }
    });
    elEtiqListe.appendChild(btn);
  });
  elNcBtnBSuivant.disabled = false;
});

// Sous-étape B → PCR01 (écran dédié)
elNcBtnBSuivant.addEventListener('click', () => {
  // Sauvegarder l'état complet du wizard pour le restaurer au retour
  const recState = {
    receptionId,
    personnelId,
    personnelPrenom,
    fournisseurId,
    lignesAjoutees,
    tempCamion:    parseFloat(elTempCamion.value) || null,
    propreteCamion,
  };
  sessionStorage.setItem('haccp_rec_state', JSON.stringify(recState));

  // Données spécifiques à la procédure PCR01
  const pcrData = {
    receptionId,
    personnelPrenom,
    fournisseurId,
    livreurPresent,
    ncProduits,          // produits NC confirmés (après contrôle à cœur)
    ncCoeurResultats,    // {ligne_id: {temp_coeur, conforme_apres_coeur}}
    ncFicheIndex: 0,
  };
  sessionStorage.setItem('haccp_pcr01_data', JSON.stringify(pcrData));

  // Sauvegarder la signature si livreur présent
  if (livreurPresent && elSigCanvas && sigCtx) {
    sessionStorage.setItem('haccp_pcr01_signature', elSigCanvas.toDataURL('image/png'));
  } else {
    sessionStorage.removeItem('haccp_pcr01_signature');
  }

  window.location.href = '/pcr01.html';
});

// chargerFichePcr / enregistrerFichePcr → déplacés dans pcr01.js (écran dédié)

// ── Canvas signature ────────────────────────────────────────
function initSignatureCanvas() {
  if (!elSigCanvas) return;
  const W = elSigCanvas.offsetWidth || 600;
  elSigCanvas.width  = W * (window.devicePixelRatio || 1);
  elSigCanvas.height = 180 * (window.devicePixelRatio || 1);
  elSigCanvas.style.height = '180px';
  sigCtx = elSigCanvas.getContext('2d');
  sigCtx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
  sigCtx.strokeStyle = '#000';
  sigCtx.lineWidth   = 2;
  sigCtx.lineCap     = 'round';
  sigCtx.lineJoin    = 'round';

  function pos(e) {
    const r = elSigCanvas.getBoundingClientRect();
    const src = e.touches ? e.touches[0] : e;
    return { x: src.clientX - r.left, y: src.clientY - r.top };
  }

  elSigCanvas.addEventListener('mousedown',  e => { sigDessin = true; const p = pos(e); sigCtx.beginPath(); sigCtx.moveTo(p.x, p.y); });
  elSigCanvas.addEventListener('mousemove',  e => { if (!sigDessin) return; const p = pos(e); sigCtx.lineTo(p.x, p.y); sigCtx.stroke(); });
  elSigCanvas.addEventListener('mouseup',    () => sigDessin = false);
  elSigCanvas.addEventListener('touchstart', e => { e.preventDefault(); sigDessin = true; const p = pos(e); sigCtx.beginPath(); sigCtx.moveTo(p.x, p.y); }, { passive: false });
  elSigCanvas.addEventListener('touchmove',  e => { e.preventDefault(); if (!sigDessin) return; const p = pos(e); sigCtx.lineTo(p.x, p.y); sigCtx.stroke(); }, { passive: false });
  elSigCanvas.addEventListener('touchend',   () => sigDessin = false);
}

elSigEffacer.addEventListener('click', () => {
  if (sigCtx) sigCtx.clearRect(0, 0, elSigCanvas.width, elSigCanvas.height);
});

// ── Clôture ─────────────────────────────────────────────────
elBtnCloturer.addEventListener('click', cloturerFiche);

async function cloturerFiche() {
  elErreur4.hidden = true;
  elBtnCloturer.disabled = true;
  elBtnCloturer.textContent = 'Clôture…';

  const payload = {
    livraison_refusee: elChkRefuse.checked,
    information_ddpp:  elChkDdpp.checked,
    commentaire_nc:    elCommentaireNc.value.trim() || null,
  };

  try {
    const rec = await apiFetch(`/api/receptions/${receptionId}/cloturer`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const conf = rec.conformite_globale === 'conforme';
    elConfirmDetail.textContent = `${lignesAjoutees.length} produit(s) — par ${personnelPrenom}`;
    elConfirmBadge.className   = 'rec-confirm-badge ' + (conf ? 'conforme' : 'nc');
    elConfirmBadge.textContent = conf ? '✓ Conformité globale : OK' : '✗ Non-conformité(s) détectée(s)';

    allerEtape(5);
    demarrerCompteurConfirmation();

  } catch (err) {
    elErreur4.textContent = `Erreur : ${err.message}`;
    elErreur4.hidden = false;
  } finally {
    elBtnCloturer.disabled = false;
    elBtnCloturer.textContent = '✔ Clôturer la fiche';
  }
}


// ── CONFIRMATION ───────────────────────────────────────────
function demarrerCompteurConfirmation() {
  let secondes = 5;
  clearInterval(timerConfirmation);

  function maj() {
    elConfirmCountdown.textContent = `Retour au menu dans ${secondes}s…`;
    if (secondes <= 0) {
      clearInterval(timerConfirmation);
      window.location.href = '/hub.html';
    }
    secondes--;
  }
  maj();
  timerConfirmation = setInterval(maj, 1000);
}

elBtnHub.addEventListener('click', () => {
  clearInterval(timerConfirmation);
  window.location.href = '/hub.html';
});


// ── Restauration état après retour depuis pcr01.html ────────
//
// Si l'opérateur revient de pcr01.html (avec ou sans validation),
// on restaure le wizard à l'étape 4 depuis sessionStorage.
//
function restaurerDepuisPcr01() {
  const recStateRaw = sessionStorage.getItem('haccp_rec_state');
  if (!recStateRaw) return false;

  const pcrDone = sessionStorage.getItem('haccp_pcr01_done') === '1';

  try {
    const state = JSON.parse(recStateRaw);

    // Restaurer l'état mémoire
    receptionId     = state.receptionId;
    personnelId     = state.personnelId;
    personnelPrenom = state.personnelPrenom;
    fournisseurId   = state.fournisseurId;
    lignesAjoutees  = state.lignesAjoutees || [];
    propreteCamion  = state.propreteCamion || 'satisfaisant';

    // Restaurer les inputs DOM nécessaires à remplirRecap()
    if (state.tempCamion !== null && state.tempCamion !== undefined) {
      elTempCamion.value = state.tempCamion;
    }

    // Nettoyage sessionStorage
    sessionStorage.removeItem('haccp_rec_state');
    sessionStorage.removeItem('haccp_pcr01_data');
    sessionStorage.removeItem('haccp_pcr01_done');
    sessionStorage.removeItem('haccp_pcr01_signature');

    // Reconstruire le récap
    remplirRecap();

    if (pcrDone) {
      // PCR01 validé → masquer la procédure NC, afficher le badge, débloquer clôture
      ncProduitsInitiaux = lignesAjoutees.filter(l => !l.conforme);
      ncProduits = [];
      elNcProcedure.hidden = true;
      if (elPcrDoneBadge) elPcrDoneBadge.hidden = false;
      elBtnCloturer.disabled = false;
    } else {
      // Retour sans validation (← Retour sur pcr01) → reprendre depuis étape A
      initNcProcedure();
    }

    allerEtape(4);
    return true;
  } catch (e) {
    console.error('[haccp] Restauration échouée :', e);
    // Nettoyer pour éviter une boucle
    sessionStorage.removeItem('haccp_rec_state');
    sessionStorage.removeItem('haccp_pcr01_data');
    sessionStorage.removeItem('haccp_pcr01_done');
    sessionStorage.removeItem('haccp_pcr01_signature');
    return false;
  }
}


// ── Initialisation ─────────────────────────────────────────
async function init() {
  // Pré-remplir date réception à aujourd'hui
  if (elDateReception && !elDateReception.value) {
    elDateReception.value = new Date().toISOString().slice(0, 10);
  }

  // Vérifier si retour depuis pcr01.html
  if (restaurerDepuisPcr01()) return;

  // Charger les données en parallèle
  await Promise.all([
    chargerPersonnel(),
    chargerFournisseurs(),
    chargerProduits(),
    chargerTextesAide(),
  ]);
  reinitCriteres();
}

init();

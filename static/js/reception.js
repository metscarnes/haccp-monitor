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
const elTempVerdict       = document.getElementById('rec-temp-produit-verdict');
const elLot               = document.getElementById('rec-lot');
const elDlc               = document.getElementById('rec-dlc');
const elPh                = document.getElementById('rec-ph');
const elPhPlage           = document.getElementById('rec-ph-plage');
const elBtnAjouter        = document.getElementById('rec-btn-ajouter');
const elBtnTerminer       = document.getElementById('rec-btn-terminer');

// Critères visuels
const CRITERES = ['couleur', 'consistance', 'exsudat', 'odeur'];

// Étape 4
const elRecapCamionInfo   = document.getElementById('rec-recap-camion-info');
const elRecapCamionBadge  = document.getElementById('rec-recap-camion-badge');
const elConformiteGlobale = document.getElementById('rec-conformite-globale');
const elRecapLignes       = document.getElementById('rec-recap-lignes');
const elChkRefuse         = document.getElementById('rec-chk-refuse');
const elChkDdpp           = document.getElementById('rec-chk-ddpp');
const elCommentaireNc     = document.getElementById('rec-commentaire-nc');
const elErreur4           = document.getElementById('rec-erreur-4');
const elBtnCloturer       = document.getElementById('rec-btn-cloturer');

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
let lignesAjoutees     = [];      // [{id, produit_nom, conforme, temp, lot}]
let produitSelectionne = null;    // objet produit complet
let criteres           = {};      // {couleur:1, consistance:1, exsudat:1, odeur:1}
let timerInactivite    = null;
let timerConfirmation  = null;
let debounceTimer      = null;
let tousProduits       = [];
let tousFournisseurs   = [];
let textesAide         = {};


// ── Horloge ────────────────────────────────────────────────
function majHorloge() {
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
        // Initialiser l'heure à maintenant
        const now = new Date();
        elHeure.value = now.toTimeString().slice(0, 5);
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
function majBadgeCamion() {
  const temp = parseFloat(elTempCamion.value);
  const proprete = propreteCamion;

  if (isNaN(temp)) {
    elCamionBadge.className = 'rec-badge neutre';
    elCamionBadge.textContent = '— Non évalué';
    return;
  }

  const tempOk    = temp < 2;
  const propreteOk = (proprete === 'satisfaisant');
  const conforme  = tempOk && propreteOk;

  if (conforme) {
    elCamionBadge.className = 'rec-badge conforme';
    elCamionBadge.textContent = '✓ Conforme';
  } else {
    elCamionBadge.className = 'rec-badge nc';
    elCamionBadge.textContent = '✗ Non conforme';
  }
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

  // Seuil renforcé si camion NC (temp > max-1)
  const tempCamion = parseFloat(elTempCamion.value);
  const camionNc = !isNaN(tempCamion) && tempCamion >= 2;
  const seuilMax = camionNc ? (intervalle.max - 1) : intervalle.max;

  const conforme = val >= intervalle.min && val <= seuilMax;
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
  elBtnAjouter.disabled = (produitSelectionne === null);
}

function reinitFormProduit() {
  produitSelectionne = null;
  elProdSel.hidden       = true;
  elProdSearchWrap.hidden = false;
  elProdSearch.value      = '';
  elProdAutoComplete.hidden = true;
  elTempProduit.value     = '';
  elTempVerdict.textContent = '';
  elTempVerdict.className = 'rec-temp-verdict';
  elLot.value = '';
  elDlc.value = '';
  elPh.value  = '';
  elPhPlage.textContent = '';
  CRITERES.forEach(c => {
    document.getElementById(`rec-aide-${c}`).textContent = '';
  });
  reinitCriteres();
  majBtnAjouter();
}

function majListeLignes() {
  elNbProduits.textContent = lignesAjoutees.length;
  elLignesListe.innerHTML  = '';
  lignesAjoutees.forEach(l => {
    const carte = document.createElement('div');
    carte.className = 'rec-ligne-carte';

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

    const badge = document.createElement('span');
    badge.className = 'rec-ligne-badge ' + (l.conforme ? 'ok' : 'nc');
    badge.textContent = l.conforme ? '✓ OK' : '✗ NC';

    carte.appendChild(info);
    carte.appendChild(badge);
    elLignesListe.appendChild(carte);
  });

  elBtnTerminer.disabled = (lignesAjoutees.length === 0);
}

elBtnAjouter.addEventListener('click', ajouterLigne);

async function ajouterLigne() {
  if (!produitSelectionne || !receptionId) return;

  elBtnAjouter.disabled = true;
  elBtnAjouter.textContent = 'Ajout…';

  const payload = {
    produit_id: produitSelectionne.id,
    couleur_conforme:     criteres.couleur,
    consistance_conforme: criteres.consistance,
    exsudat_conforme:     criteres.exsudat,
    odeur_conforme:       criteres.odeur,
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

  const dlc = elDlc.value;
  if (dlc) payload.dlc = dlc;

  const ph = parseFloat(elPh.value);
  if (!isNaN(ph)) payload.ph_valeur = ph;

  try {
    const ligne = await apiFetch(`/api/receptions/${receptionId}/lignes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    lignesAjoutees.push({
      id:                  ligne.id,
      produit_nom:         produitSelectionne.nom,
      conforme:            ligne.conforme,
      temperature_reception: ligne.temperature_reception,
      numero_lot:          ligne.numero_lot,
    });

    majListeLignes();
    reinitFormProduit();

    // Scroll vers le haut de la liste
    document.querySelector('.rec-produits-liste-ajoutee').scrollTop = 9999;

  } catch (err) {
    alert(`Erreur lors de l'ajout : ${err.message}`);
  } finally {
    elBtnAjouter.disabled = !produitSelectionne;
    elBtnAjouter.textContent = '+ Ajouter';
  }
}

elBtnTerminer.addEventListener('click', () => {
  if (lignesAjoutees.length === 0) return;
  remplirRecap();
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

  const camionOk = (isNaN(tempCamion) || tempCamion < 2) && (propreteCamion === 'satisfaisant');
  elRecapCamionBadge.className = 'rec-badge ' + (camionOk ? 'conforme' : 'nc');
  elRecapCamionBadge.textContent = camionOk ? '✓ Conforme' : '✗ NC';

  // Conformité globale estimée (avant clôture serveur)
  const toutesConformes = lignesAjoutees.every(l => l.conforme);
  elConformiteGlobale.className = 'rec-conformite-globale ' + (toutesConformes && camionOk ? 'conforme' : 'nc');
  elConformiteGlobale.textContent = toutesConformes && camionOk
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

    // Écran de confirmation
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


// ── Initialisation ─────────────────────────────────────────
async function init() {
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

'use strict';
/* ============================================================
   ouverture.js — Module Ouverture sous-vide
   Au Comptoir des Lilas — Mets Carnés Holding

   Flux wizard : Photo → Produit → Opérateur → Confirmation
   ============================================================ */

// ── Références DOM ─────────────────────────────────────────
const elHorloge          = document.getElementById('ouv-horloge');
const elBtnRetour        = document.getElementById('ouv-btn-retour');
const elProgress         = document.getElementById('ouv-progress');
const elDot1             = document.getElementById('dot-1');
const elDot2             = document.getElementById('dot-2');
const elDot3             = document.getElementById('dot-3');
const elBandeauProduit   = document.getElementById('ouv-bandeau-produit');

// Steps
const elStep1            = document.getElementById('ouv-step-1');
const elStep2            = document.getElementById('ouv-step-2');
const elStep3            = document.getElementById('ouv-step-3');
const elStepConfirm      = document.getElementById('ouv-step-confirm');
const STEPS              = [elStep1, elStep2, elStep3, elStepConfirm];

// Étape 1
const elBtnCamera        = document.getElementById('ouv-btn-camera');
const elInputPhoto       = document.getElementById('ouv-input-photo');
const elApercu           = document.getElementById('ouv-apercu');
const elPhotoVignette    = document.getElementById('ouv-photo-vignette');

// Étape 2
const elSearch           = document.getElementById('ouv-search');
const elSectionLabel     = document.getElementById('ouv-section-label');
const elProduitsList     = document.getElementById('ouv-produits-liste');
const elListeVide        = document.getElementById('ouv-liste-vide');

// Étape 3
const elPersonnelGrille  = document.getElementById('ouv-personnel-grille');
const elErreur3          = document.getElementById('ouv-erreur-3');
const elBtnEnregistrer   = document.getElementById('ouv-btn-enregistrer');

// Confirmation
const elConfirmDetail    = document.getElementById('ouv-confirm-detail');
const elConfirmCountdown = document.getElementById('ouv-confirm-countdown');
const elBtnMemeProduit   = document.getElementById('ouv-btn-meme-produit');
const elBtnNouvelle      = document.getElementById('ouv-btn-nouvelle');

// ── État ───────────────────────────────────────────────────
let etape               = 1;
let photoFile           = null;
let photoObjectUrl      = null;
let produitSelectionne  = null;
let personnelId         = null;
let personnelPrenom     = null;
let suggestions         = [];
let timerInactivite     = null;
let timerConfirmation   = null;
let debounceTimer       = null;

// ── Horloge ────────────────────────────────────────────────
function majHorloge() {
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();

// ── Inactivité (5 min → hub.html) ─────────────────────────
const DELAI_INACTIVITE = 5 * 60 * 1000;

function resetInactivite() {
  clearTimeout(timerInactivite);
  timerInactivite = setTimeout(() => {
    window.location.href = '/hub.html';
  }, DELAI_INACTIVITE);
}
document.addEventListener('click',      resetInactivite, true);
document.addEventListener('touchstart', resetInactivite, { passive: true, capture: true });
document.addEventListener('input',      resetInactivite, true);
resetInactivite();

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
  const index = cible <= 3 ? cible - 1 : 3; // confirmation = index 3

  STEPS.forEach((el, i) => {
    el.classList.remove('actif', 'gauche');
    if (i < index) el.classList.add('gauche');
    else if (i === index) el.classList.add('actif');
    // else : reste translateX(100%) — hors écran à droite
  });

  // Progress bar
  if (cible > 3) {
    elProgress.hidden = true;
  } else {
    elProgress.hidden = false;
    [elDot1, elDot2, elDot3].forEach((dot, i) => {
      dot.classList.remove('actif', 'complet');
      if (i < cible - 1)      dot.classList.add('complet');
      else if (i === cible - 1) dot.classList.add('actif');
    });
  }

  // Bandeau produit (étape 3 seulement)
  const afficherBandeau = (cible === 3 && produitSelectionne !== null);
  elBandeauProduit.hidden = !afficherBandeau;
  if (afficherBandeau) {
    elBandeauProduit.textContent = `📦 ${produitSelectionne.nom}`;
  }

  // Bouton retour masqué sur la confirmation
  elBtnRetour.hidden = (cible > 3);
}

// ── Retour ─────────────────────────────────────────────────
elBtnRetour.addEventListener('click', () => {
  if (etape === 1) {
    window.location.href = '/hub.html';
  } else if (etape <= 3) {
    allerEtape(etape - 1);
  }
});

// ── ÉTAPE 1 : Photo ────────────────────────────────────────
elBtnCamera.addEventListener('click', () => {
  elInputPhoto.click();
});

elInputPhoto.addEventListener('change', () => {
  const file = elInputPhoto.files[0];
  if (!file) return;

  photoFile = file;
  if (photoObjectUrl) URL.revokeObjectURL(photoObjectUrl);
  photoObjectUrl = URL.createObjectURL(file);

  elPhotoVignette.src = photoObjectUrl;
  elApercu.hidden = false;

  // Si produit déjà sélectionné (flux "même produit"), sauter l'étape 2
  setTimeout(() => allerEtape(produitSelectionne ? 3 : 2), 450);
});

// ── ÉTAPE 2 : Suggestions produits ─────────────────────────
async function chargerSuggestions() {
  elListeVide.textContent = 'Chargement…';
  elListeVide.hidden = false;
  try {
    suggestions = await apiFetch('/api/ouvertures/suggestions');
    afficherProduits(suggestions);
  } catch {
    elListeVide.textContent = 'Impossible de charger les produits.';
    elListeVide.hidden = false;
  }
}

function formatDateFR(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
  } catch { return ''; }
}

function afficherProduits(liste) {
  // Vider (conserver elListeVide)
  [...elProduitsList.children].forEach(el => {
    if (el !== elListeVide) el.remove();
  });

  if (!liste.length) {
    elListeVide.textContent = 'Aucun produit trouvé.';
    elListeVide.hidden = false;
    elSectionLabel.textContent = '';
    return;
  }

  elListeVide.hidden = true;

  const recents = liste.filter(p => p.is_recent);
  const autres  = liste.filter(p => !p.is_recent);

  if (recents.length) {
    elSectionLabel.textContent = 'Produits en stock';
    recents.forEach(p => elProduitsList.appendChild(creerCarte(p)));
  }

  if (autres.length) {
    if (recents.length) {
      const sep = document.createElement('div');
      sep.className = 'ouv-sous-label';
      sep.textContent = 'Catalogue';
      elProduitsList.appendChild(sep);
    } else {
      elSectionLabel.textContent = 'Catalogue';
    }
    autres.forEach(p => elProduitsList.appendChild(creerCarte(p)));
  }
}

function creerCarte(produit) {
  const carte = document.createElement('div');
  carte.className = 'ouv-produit-carte' + (produit.is_recent ? ' recent' : '');
  carte.setAttribute('role', 'listitem');

  const info = document.createElement('div');
  info.className = 'ouv-produit-info';

  const nom = document.createElement('div');
  nom.className = 'ouv-produit-nom';
  nom.textContent = produit.nom;
  info.appendChild(nom);

  if (produit.espece) {
    const espece = document.createElement('div');
    espece.className = 'ouv-produit-espece';
    espece.textContent = produit.espece;
    info.appendChild(espece);
  }

  if (produit.is_recent && produit.last_reception) {
    const recu = document.createElement('div');
    recu.className = 'ouv-produit-recu';
    recu.textContent = `Reçu le ${formatDateFR(produit.last_reception)}`;
    info.appendChild(recu);
  }

  carte.appendChild(info);

  if (produit.code_unique) {
    const code = document.createElement('span');
    code.className = 'ouv-produit-code';
    code.textContent = produit.code_unique;
    carte.appendChild(code);
  }

  carte.addEventListener('click', () => selectionnerProduit(produit));
  return carte;
}

function selectionnerProduit(produit) {
  produitSelectionne = produit;
  allerEtape(3);
}

// Filtre : local immédiat + appel API debounced
elSearch.addEventListener('input', () => {
  const q = elSearch.value.trim();

  if (!q) {
    afficherProduits(suggestions);
    clearTimeout(debounceTimer);
    return;
  }

  // Filtre local instantané sur les suggestions déjà chargées
  const ql = q.toLowerCase();
  const locaux = suggestions.filter(p =>
    p.nom.toLowerCase().includes(ql) ||
    (p.code_unique && p.code_unique.toLowerCase().includes(ql))
  );
  afficherProduits(locaux);

  // Appel API debounced pour couvrir tout le catalogue
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    try {
      const res = await apiFetch(
        `/api/ouvertures/suggestions?q=${encodeURIComponent(q)}`
      );
      afficherProduits(res);
    } catch { /* silencieux */ }
  }, 350);
});

// ── ÉTAPE 3 : Personnel ────────────────────────────────────
async function chargerPersonnel() {
  try {
    const liste = await apiFetch('/api/admin/personnel');
    elPersonnelGrille.innerHTML = '';
    liste.forEach(p => {
      const btn = document.createElement('button');
      btn.className = 'ouv-btn-prenom';
      btn.textContent = p.prenom;
      btn.dataset.id     = p.id;
      btn.dataset.prenom = p.prenom;
      btn.addEventListener('click', () => selectionnerPersonnel(p.id, p.prenom, btn));
      elPersonnelGrille.appendChild(btn);
    });
  } catch {
    elPersonnelGrille.innerHTML =
      '<div class="ouv-liste-vide">Impossible de charger le personnel.</div>';
  }
}

function selectionnerPersonnel(id, prenom, btnClique) {
  personnelId     = id;
  personnelPrenom = prenom;
  elPersonnelGrille.querySelectorAll('.ouv-btn-prenom')
    .forEach(b => b.classList.remove('selectionne'));
  btnClique.classList.add('selectionne');
  elBtnEnregistrer.disabled = false;
  elBtnEnregistrer.setAttribute('aria-disabled', 'false');
  elErreur3.hidden = true;
}

// ── Enregistrement ─────────────────────────────────────────
elBtnEnregistrer.addEventListener('click', async () => {
  if (!personnelId) {
    elErreur3.hidden = false;
    return;
  }

  elBtnEnregistrer.disabled = true;
  elBtnEnregistrer.textContent = 'Enregistrement…';

  try {
    const fd = new FormData();
    fd.append('photo',        photoFile);
    fd.append('produit_id',   String(produitSelectionne.produit_id));
    fd.append('personnel_id', String(personnelId));

    const res = await fetch('/api/ouvertures', { method: 'POST', body: fd });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    afficherConfirmation();
  } catch (err) {
    elErreur3.textContent = `Erreur : ${err.message}`;
    elErreur3.hidden = false;
    elBtnEnregistrer.disabled = false;
    elBtnEnregistrer.textContent = '✔\u00A0Enregistrer l\'ouverture';
  }
});

// ── Confirmation ───────────────────────────────────────────
function afficherConfirmation() {
  elConfirmDetail.textContent = `${produitSelectionne.nom} — ${personnelPrenom}`;
  allerEtape(4);
  demarrerCountdown();
}

function demarrerCountdown() {
  clearTimeout(timerConfirmation);
  let restant = 5;

  function tick() {
    elConfirmCountdown.textContent = `Retour à l'accueil dans ${restant}s…`;
    if (restant <= 0) {
      window.location.href = '/hub.html';
      return;
    }
    restant--;
    timerConfirmation = setTimeout(tick, 1000);
  }
  tick();
}

elBtnMemeProduit.addEventListener('click', () => {
  clearTimeout(timerConfirmation);

  // Conserver produit + personnel pour la prochaine ouverture
  const produitGarde  = produitSelectionne;
  const idGarde       = personnelId;
  const prenomGarde   = personnelPrenom;

  resetEtat();

  produitSelectionne = produitGarde;
  personnelId        = idGarde;
  personnelPrenom    = prenomGarde;

  // Pré-sélectionner le personnel dans la grille
  elPersonnelGrille.querySelectorAll('.ouv-btn-prenom').forEach(btn => {
    if (parseInt(btn.dataset.id, 10) === personnelId) {
      btn.classList.add('selectionne');
    }
  });
  elBtnEnregistrer.disabled = false;

  allerEtape(1);
});

elBtnNouvelle.addEventListener('click', () => {
  clearTimeout(timerConfirmation);
  resetEtat();
  allerEtape(1);
});

// ── Reset état complet ─────────────────────────────────────
function resetEtat() {
  photoFile = null;
  if (photoObjectUrl) { URL.revokeObjectURL(photoObjectUrl); photoObjectUrl = null; }
  produitSelectionne = null;
  personnelId        = null;
  personnelPrenom    = null;

  // Étape 1
  elInputPhoto.value = '';
  elApercu.hidden    = true;
  elPhotoVignette.src = '';

  // Étape 2
  elSearch.value = '';
  afficherProduits(suggestions);

  // Étape 3
  elPersonnelGrille.querySelectorAll('.ouv-btn-prenom')
    .forEach(b => b.classList.remove('selectionne'));
  elBtnEnregistrer.disabled = true;
  elBtnEnregistrer.setAttribute('aria-disabled', 'true');
  elBtnEnregistrer.textContent = '✔\u00A0Enregistrer l\'ouverture';
  elErreur3.hidden = true;
}

// ── Init ───────────────────────────────────────────────────
chargerSuggestions();
chargerPersonnel();
allerEtape(1);

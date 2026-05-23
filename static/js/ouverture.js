'use strict';
/* ============================================================
   ouverture.js — Module Ouverture sous-vide
   Au Comptoir des Lilas — Mets Carnés Holding

   Flux wizard : Opérateur → Photo → Produit → Confirmation
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

// Étape 1 — Opérateur
const elPersonnelGrille  = document.getElementById('ouv-personnel-grille');

// Étape 2 — Photo
const elBtnCamera        = document.getElementById('ouv-btn-camera');
const elInputPhoto       = document.getElementById('ouv-input-photo');
const elApercu           = document.getElementById('ouv-apercu');
const elPhotoVignette    = document.getElementById('ouv-photo-vignette');

// Étape 3 — Produit
const elSearch           = document.getElementById('ouv-search');
const elSectionLabel     = document.getElementById('ouv-section-label');
const elProduitsList     = document.getElementById('ouv-produits-liste');
const elListeVide        = document.getElementById('ouv-liste-vide');
const elErreur3          = document.getElementById('ouv-erreur-3');
const elBtnEnregistrer   = document.getElementById('ouv-btn-enregistrer');

// Confirmation
const elConfirmDetail    = document.getElementById('ouv-confirm-detail');
const elConfirmCountdown = document.getElementById('ouv-confirm-countdown');
const elBtnImprimer      = document.getElementById('ouv-btn-imprimer');
const elBtnMemeProduit   = document.getElementById('ouv-btn-meme-produit');
const elBtnNouvelle      = document.getElementById('ouv-btn-nouvelle');

// ── État ───────────────────────────────────────────────────
let etape               = 1;
let photoFile           = null;
let photoObjectUrl      = null;
let produitSelectionne  = null;
let personnelId         = null;
let personnelPrenom     = null;
let dernierSauvegardeData = null;
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

// ── Utilitaire HTML sécurisé ───────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ── Navigation wizard ──────────────────────────────────────
function allerEtape(cible) {
  etape = cible;
  const index = cible <= 3 ? cible - 1 : 3; // confirmation = index 3

  STEPS.forEach((el, i) => {
    el.classList.remove('actif', 'gauche');
    if (i < index) el.classList.add('gauche');
    else if (i === index) el.classList.add('actif');
  });

  // Progress bar
  if (cible > 3) {
    elProgress.hidden = true;
  } else {
    elProgress.hidden = false;
    [elDot1, elDot2, elDot3].forEach((dot, i) => {
      dot.classList.remove('actif', 'complet');
      if (i < cible - 1)        dot.classList.add('complet');
      else if (i === cible - 1) dot.classList.add('actif');
    });
  }

  // Bandeau opérateur (étapes 2 et 3)
  const afficherBandeau = (cible === 2 || cible === 3) && personnelPrenom !== null;
  elBandeauProduit.hidden = !afficherBandeau;
  if (afficherBandeau) {
    elBandeauProduit.textContent = `👤 ${personnelPrenom}`;
  }

  // Bouton retour masqué sur la confirmation
  elBtnRetour.hidden = (cible > 3);

  // Pré-surligner le produit déjà sélectionné quand on arrive à l'étape 3
  if (cible === 3 && produitSelectionne) {
    requestAnimationFrame(highlightProduitSelectionne);
    // Activer le bouton immédiatement — le highlight peut échouer si la carte n'est pas encore dans le DOM
    elBtnEnregistrer.disabled = false;
    elBtnEnregistrer.setAttribute('aria-disabled', 'false');
  }
}

// ── Retour ─────────────────────────────────────────────────
elBtnRetour.addEventListener('click', () => {
  if (etape === 1) {
    window.location.href = '/hub.html';
  } else if (etape <= 3) {
    allerEtape(etape - 1);
  }
});

// ── ÉTAPE 1 : Opérateur ────────────────────────────────────
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
  // Auto-avance vers l'étape 2 (Photo)
  setTimeout(() => allerEtape(2), 200);
}

// ── ÉTAPE 2 : Photo ────────────────────────────────────────
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

  setTimeout(() => allerEtape(3), 450);
});

// ── ÉTAPE 3 : Suggestions produits ─────────────────────────
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
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' });
  } catch { return ''; }
}

function afficherProduits(liste) {
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

  // Restaurer la sélection si un produit est déjà choisi (flux "même produit")
  if (produitSelectionne) highlightProduitSelectionne();
}

function creerCarte(produit) {
  const carte = document.createElement('div');
  carte.className = 'ouv-produit-carte' + (produit.is_recent ? ' recent' : '');
  carte.setAttribute('role', 'listitem');
  carte.dataset.produitId = produit.produit_id;

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

  if (produit.is_recent) {
    if (produit.numero_lot) {
      const lot = document.createElement('div');
      lot.className = 'ouv-produit-lot';
      lot.textContent = `Lot : ${produit.numero_lot}`;
      info.appendChild(lot);
    }
    if (produit.dlc) {
      const dlc = document.createElement('div');
      dlc.className = 'ouv-produit-dlc';
      dlc.textContent = `DLC : ${formatDateFR(produit.dlc)}`;
      info.appendChild(dlc);
    } else if (!produit.numero_lot && produit.last_reception) {
      const recu = document.createElement('div');
      recu.className = 'ouv-produit-recu';
      recu.textContent = `Reçu le ${formatDateFR(produit.last_reception)}`;
      info.appendChild(recu);
    }
  }

  carte.appendChild(info);

  if (produit.code_unique) {
    const code = document.createElement('span');
    code.className = 'ouv-produit-code';
    code.textContent = produit.code_unique;
    carte.appendChild(code);
  }

  carte.addEventListener('click', () => {
    elProduitsList.querySelectorAll('.ouv-produit-carte')
      .forEach(c => c.classList.remove('selectionne'));
    carte.classList.add('selectionne');
    selectionnerProduit(produit);
  });
  return carte;
}

function highlightProduitSelectionne() {
  if (!produitSelectionne) return;
  elProduitsList.querySelectorAll('.ouv-produit-carte').forEach(carte => {
    if (parseInt(carte.dataset.produitId, 10) === produitSelectionne.produit_id) {
      carte.classList.add('selectionne');
      elBtnEnregistrer.disabled = false;
      elBtnEnregistrer.setAttribute('aria-disabled', 'false');
    }
  });
}

function selectionnerProduit(produit) {
  produitSelectionne = produit;
  elBtnEnregistrer.disabled = false;
  elBtnEnregistrer.setAttribute('aria-disabled', 'false');
  elErreur3.hidden = true;
}

// Filtre : local immédiat + appel API debounced
elSearch.addEventListener('input', () => {
  const q = elSearch.value.trim();

  if (!q) {
    afficherProduits(suggestions);
    clearTimeout(debounceTimer);
    return;
  }

  const ql = q.toLowerCase();
  const locaux = suggestions.filter(p =>
    p.nom.toLowerCase().includes(ql) ||
    (p.code_unique && p.code_unique.toLowerCase().includes(ql))
  );
  afficherProduits(locaux);

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

// ── Enregistrement ─────────────────────────────────────────
elBtnEnregistrer.addEventListener('click', async () => {
  if (!produitSelectionne) {
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
    if (produitSelectionne.reception_ligne_id != null) {
      fd.append('reception_ligne_id', String(produitSelectionne.reception_ligne_id));
    }

    const res = await fetch('/api/ouvertures', { method: 'POST', body: fd });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    dernierSauvegardeData = data;
    afficherConfirmation(data);
  } catch (err) {
    elErreur3.textContent = `Erreur : ${err.message}`;
    elErreur3.hidden = false;
    elBtnEnregistrer.disabled = false;
    elBtnEnregistrer.textContent = '✔ Enregistrer l\'ouverture';
  }
});

// ── Confirmation ───────────────────────────────────────────
function afficherConfirmation(data) {
  const lines = [
    `${escHtml(produitSelectionne.nom)} — ${escHtml(personnelPrenom)}`,
  ];
  if (data.numero_lot) lines.push(`Lot : ${escHtml(data.numero_lot)}`);
  if (data.dlc)        lines.push(`DLC : ${escHtml(formatDateFR(data.dlc))}`);
  elConfirmDetail.innerHTML = lines.join('<br>');

  elBtnImprimer.disabled = false;
  elBtnImprimer.textContent = '🖨️ Imprimer l\'étiquette';

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

// ── Impression étiquette ───────────────────────────────────
function remplirGabaritOuverture(data) {
  const fmtDate = iso => {
    if (!iso) return '--/--/--';
    const [y, m, d] = (iso.split('T')[0] || iso).split('-');
    return `${d}/${m}/${(y || '').slice(-2)}`;
  };

  let dateStr = '--/--/--', heureStr = '--h--';
  try {
    const ts = (data.timestamp || '').replace(' ', 'T');
    const dt = new Date(ts);
    dateStr  = `${String(dt.getDate()).padStart(2,'0')}/${String(dt.getMonth()+1).padStart(2,'0')}/${String(dt.getFullYear()).slice(-2)}`;
    heureStr = `${String(dt.getHours()).padStart(2,'0')}h${String(dt.getMinutes()).padStart(2,'0')}`;
  } catch { /* laisse les valeurs par défaut */ }

  document.getElementById('pol-nom').textContent    = (produitSelectionne.nom || '').toUpperCase();
  document.getElementById('pol-dlc').textContent    = fmtDate(data.dlc);
  document.getElementById('pol-lot').textContent    = data.numero_lot ? `Lot : ${data.numero_lot}` : 'Lot : —';
  document.getElementById('pol-action').textContent = `Ouvert le ${dateStr} à ${heureStr}`;
  document.getElementById('pol-meta').textContent   = `Par : ${personnelPrenom || '—'}`;
}

elBtnImprimer.addEventListener('click', () => {
  if (!dernierSauvegardeData) return;
  clearTimeout(timerConfirmation);
  remplirGabaritOuverture(dernierSauvegardeData);
  setTimeout(() => window.print(), 100);
});

// ── Boutons post-confirmation ──────────────────────────────
elBtnMemeProduit.addEventListener('click', () => {
  clearTimeout(timerConfirmation);

  const produitGarde  = produitSelectionne;
  const idGarde       = personnelId;
  const prenomGarde   = personnelPrenom;

  resetEtat();

  produitSelectionne = produitGarde;
  personnelId        = idGarde;
  personnelPrenom    = prenomGarde;

  // Pré-sélectionner l'opérateur dans la grille
  elPersonnelGrille.querySelectorAll('.ouv-btn-prenom').forEach(btn => {
    if (parseInt(btn.dataset.id, 10) === personnelId) {
      btn.classList.add('selectionne');
    }
  });

  // Resélectionner visuellement le produit dans la liste (déjà rechargée par resetEtat)
  highlightProduitSelectionne();

  allerEtape(2); // Reprise directe à la photo
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
  produitSelectionne    = null;
  personnelId           = null;
  personnelPrenom       = null;
  dernierSauvegardeData = null;

  // Étape 1
  elPersonnelGrille.querySelectorAll('.ouv-btn-prenom')
    .forEach(b => b.classList.remove('selectionne'));

  // Étape 2
  elInputPhoto.value  = '';
  elApercu.hidden     = true;
  elPhotoVignette.src = '';

  // Étape 3
  elSearch.value = '';
  afficherProduits(suggestions);
  elBtnEnregistrer.disabled = true;
  elBtnEnregistrer.setAttribute('aria-disabled', 'true');
  elBtnEnregistrer.textContent = '✔ Enregistrer l\'ouverture';
  elErreur3.hidden = true;
}

// ── Init ───────────────────────────────────────────────────
chargerSuggestions();
chargerPersonnel();
allerEtape(1);

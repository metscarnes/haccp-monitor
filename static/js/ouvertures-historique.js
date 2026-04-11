'use strict';
/* ============================================================
   ouvertures-historique.js — Historique des ouvertures
   Au Comptoir des Lilas — Mets Carnés Holding
   ============================================================ */

// ── Références DOM ──────────────────────────────────────────
const elHorloge      = document.getElementById('hist-horloge');
const elBtnRetour    = document.getElementById('hist-btn-retour');
const elInputProduit = document.getElementById('hist-input-produit');
const elAutocomplete = document.getElementById('hist-autocomplete');
const elDateDebut    = document.getElementById('hist-date-debut');
const elDateFin      = document.getElementById('hist-date-fin');
const elBtnFiltrer   = document.getElementById('hist-btn-filtrer');
const elBtnReset     = document.getElementById('hist-btn-reset');
const elCompteur     = document.getElementById('hist-compteur');
const elListe        = document.getElementById('hist-liste');
const elMessage      = document.getElementById('hist-message');
const elMessageIcone = document.getElementById('hist-message-icone');
const elMessageTexte = document.getElementById('hist-message-texte');
const elBtnPlus      = document.getElementById('hist-btn-plus');
const elModal        = document.getElementById('hist-modal');
const elModalImg     = document.getElementById('hist-modal-img');

// ── État ────────────────────────────────────────────────────
const LIMIT           = 50;
let offsetCourant     = 0;
let totalCharges      = 0;
let produitIdFiltre   = null;   // id produit sélectionné via autocomplete
let debounceTimer     = null;
let timerInactivite   = null;

// ── Horloge ─────────────────────────────────────────────────
function majHorloge() {
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();

// ── Inactivité (5 min → hub.html) ───────────────────────────
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

// ── Fetch helper ────────────────────────────────────────────
async function apiFetch(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} — ${txt || url}`);
  }
  return res.json();
}

// ── Formatage dates ─────────────────────────────────────────
function formatDateHeureFR(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    const date = d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    const heure = d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    return `${date} à ${heure}`;
  } catch { return isoStr; }
}

function formatDateFR(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
  } catch { return isoStr; }
}

// ── Init dates par défaut (7 derniers jours) ─────────────────
function initDates() {
  const aujourd = new Date();
  const ilYa7   = new Date();
  ilYa7.setDate(ilYa7.getDate() - 6);

  elDateFin.value   = aujourd.toISOString().slice(0, 10);
  elDateDebut.value = ilYa7.toISOString().slice(0, 10);
}

// ── Construction URL API ─────────────────────────────────────
function buildUrl(offset = 0) {
  const params = new URLSearchParams();
  params.set('limit',  String(LIMIT));
  params.set('offset', String(offset));

  if (produitIdFiltre !== null) {
    params.set('produit_id', String(produitIdFiltre));
  }
  if (elDateDebut.value) params.set('date_debut', elDateDebut.value);
  if (elDateFin.value)   params.set('date_fin',   elDateFin.value);

  return `/api/ouvertures?${params.toString()}`;
}

// ── Chargement initial / rafraîchissement ────────────────────
async function charger() {
  offsetCourant = 0;
  totalCharges  = 0;
  elListe.innerHTML = '';
  elBtnPlus.hidden  = true;
  elCompteur.textContent = '';

  afficherMessage('⏳', 'Chargement…');

  try {
    const rows = await apiFetch(buildUrl(0));
    masquerMessage();
    ajouterResultats(rows);
  } catch (err) {
    afficherMessage('⚠️', `Erreur : ${err.message}`);
  }
}

// ── Pagination — "Voir plus" ─────────────────────────────────
async function chargerSuite() {
  elBtnPlus.disabled = true;
  elBtnPlus.textContent = 'Chargement…';

  try {
    const rows = await apiFetch(buildUrl(offsetCourant));
    ajouterResultats(rows);
  } catch (err) {
    elBtnPlus.disabled = false;
    elBtnPlus.textContent = 'Voir plus…';
    alert(`Erreur de chargement : ${err.message}`);
  }
}

function ajouterResultats(rows) {
  if (rows.length === 0 && totalCharges === 0) {
    afficherMessage('🔍', 'Aucune ouverture trouvée pour ces critères.');
    return;
  }

  rows.forEach(ouv => {
    elListe.appendChild(creerCarte(ouv));
  });

  offsetCourant += rows.length;
  totalCharges  += rows.length;
  majCompteur();

  // Bouton "Voir plus" visible si on a reçu exactement LIMIT résultats
  if (rows.length === LIMIT) {
    elBtnPlus.hidden   = false;
    elBtnPlus.disabled = false;
    elBtnPlus.textContent = 'Voir plus…';
  } else {
    elBtnPlus.hidden = true;
  }
}

function majCompteur() {
  elCompteur.textContent = totalCharges === 1
    ? '1 ouverture'
    : `${totalCharges} ouvertures`;
}

// ── Création d'une carte ─────────────────────────────────────
function creerCarte(ouv) {
  const estTracee = ouv.reception_ligne_id !== null && ouv.fournisseur_nom !== null;

  const carte = document.createElement('div');
  carte.className = 'hist-carte ' + (estTracee ? 'hist-carte--tracee' : 'hist-carte--manuelle');
  carte.setAttribute('role', 'listitem');

  // Photo miniature
  const photoWrap = document.createElement('div');
  photoWrap.className = 'hist-photo-wrap';
  photoWrap.setAttribute('role', 'button');
  photoWrap.setAttribute('aria-label', 'Voir la photo en plein écran');
  photoWrap.tabIndex = 0;

  if (ouv.photo_filename) {
    const img = document.createElement('img');
    img.src = `/api/ouvertures/${ouv.id}/photo`;
    img.alt = `Photo ouverture ${ouv.produit_nom}`;
    img.loading = 'lazy';
    photoWrap.appendChild(img);
  } else {
    const ph = document.createElement('div');
    ph.className = 'hist-photo-placeholder';
    ph.textContent = '📷';
    photoWrap.appendChild(ph);
  }

  photoWrap.addEventListener('click', () => ouvrirModal(ouv.id, ouv.produit_nom));
  photoWrap.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') ouvrirModal(ouv.id, ouv.produit_nom);
  });

  // Corps de la carte
  const corps = document.createElement('div');
  corps.className = 'hist-carte-corps';

  // En-tête : nom + badge
  const entete = document.createElement('div');
  entete.className = 'hist-carte-entete';

  const nom = document.createElement('div');
  nom.className = 'hist-produit-nom';
  nom.textContent = ouv.produit_nom;
  entete.appendChild(nom);

  const badge = document.createElement('span');
  badge.className = 'hist-badge ' + (estTracee ? 'hist-badge--ok' : 'hist-badge--attention');
  badge.textContent = estTracee ? '✓ Traçabilité complète' : '⚠ Saisie manuelle';
  entete.appendChild(badge);

  corps.appendChild(entete);

  // Espèce
  if (ouv.produit_espece) {
    const espece = document.createElement('div');
    espece.className = 'hist-produit-espece';
    espece.textContent = ouv.produit_espece;
    corps.appendChild(espece);
  }

  // Date, heure, opérateur
  const meta = document.createElement('div');
  meta.className = 'hist-meta';
  meta.textContent = `${formatDateHeureFR(ouv.timestamp)} — ${ouv.personnel_prenom}`;
  corps.appendChild(meta);

  // Infos réception si traçabilité complète
  if (estTracee) {
    const infos = document.createElement('div');
    infos.className = 'hist-reception-infos';

    const champs = [
      { label: 'Fournisseur',      valeur: ouv.fournisseur_nom },
      { label: 'N° lot',           valeur: ouv.numero_lot || '—' },
      { label: 'DLC fournisseur',  valeur: formatDateFR(ouv.dlc_fournisseur) },
      { label: 'Origine',          valeur: ouv.origine || '—' },
      { label: 'Date réception',   valeur: formatDateFR(ouv.date_reception) },
    ];

    champs.forEach(({ label, valeur }) => {
      const ligne = document.createElement('div');
      ligne.className = 'hist-info-ligne';

      const lbl = document.createElement('span');
      lbl.className = 'hist-info-label';
      lbl.textContent = label;

      const val = document.createElement('span');
      val.className = 'hist-info-valeur';
      val.textContent = valeur;

      ligne.appendChild(lbl);
      ligne.appendChild(val);
      infos.appendChild(ligne);
    });

    corps.appendChild(infos);
  }

  carte.appendChild(photoWrap);
  carte.appendChild(corps);
  return carte;
}

// ── Modal photo plein écran ──────────────────────────────────
function ouvrirModal(ouvertureId, nom) {
  elModalImg.src = `/api/ouvertures/${ouvertureId}/photo`;
  elModalImg.alt = `Photo ouverture ${nom}`;
  elModal.hidden = false;
  document.body.style.overflow = 'hidden';
}

function fermerModal() {
  elModal.hidden = true;
  elModalImg.src = '';
  document.body.style.overflow = '';
}

elModal.addEventListener('click', fermerModal);
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !elModal.hidden) fermerModal();
});

// ── Messages vide/chargement ─────────────────────────────────
function afficherMessage(icone, texte) {
  elMessageIcone.textContent = icone;
  elMessageTexte.textContent = texte;
  elMessage.hidden = false;
}
function masquerMessage() {
  elMessage.hidden = true;
}

// ── Autocomplete produits ────────────────────────────────────
elInputProduit.addEventListener('input', () => {
  const q = elInputProduit.value.trim();

  // Réinitialiser la sélection si on retape
  produitIdFiltre = null;

  if (!q) {
    elAutocomplete.hidden = true;
    elAutocomplete.innerHTML = '';
    return;
  }

  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    try {
      const res = await apiFetch(
        `/api/ouvertures/suggestions?q=${encodeURIComponent(q)}`
      );
      afficherAutocomplete(res);
    } catch { /* silencieux */ }
  }, 300);
});

function afficherAutocomplete(liste) {
  elAutocomplete.innerHTML = '';

  if (!liste.length) {
    elAutocomplete.hidden = true;
    return;
  }

  liste.slice(0, 12).forEach(p => {
    const item = document.createElement('div');
    item.className = 'hist-ac-item';
    item.setAttribute('role', 'option');

    const nom = document.createElement('div');
    nom.className = 'hist-ac-nom';
    nom.textContent = p.nom;
    item.appendChild(nom);

    if (p.espece) {
      const esp = document.createElement('div');
      esp.className = 'hist-ac-espece';
      esp.textContent = p.espece;
      item.appendChild(esp);
    }

    item.addEventListener('click', () => {
      produitIdFiltre = p.produit_id;
      elInputProduit.value = p.nom;
      elAutocomplete.hidden = true;
      elAutocomplete.innerHTML = '';
    });

    elAutocomplete.appendChild(item);
  });

  elAutocomplete.hidden = false;
}

// Fermer autocomplete si clic ailleurs
document.addEventListener('click', e => {
  if (!elInputProduit.contains(e.target) && !elAutocomplete.contains(e.target)) {
    elAutocomplete.hidden = true;
  }
});

// ── Boutons filtres ──────────────────────────────────────────
elBtnFiltrer.addEventListener('click', charger);

elBtnReset.addEventListener('click', () => {
  produitIdFiltre = null;
  elInputProduit.value = '';
  elAutocomplete.hidden = true;
  initDates();
  charger();
});

elBtnPlus.addEventListener('click', chargerSuite);

// ── Retour hub ───────────────────────────────────────────────
elBtnRetour.addEventListener('click', () => {
  window.location.href = '/hub.html';
});

// ── Init ─────────────────────────────────────────────────────
initDates();
charger();

'use strict';
/* ============================================================
   etiquettes.js — Génération d'étiquettes DLC
   Au Comptoir des Lilas — Mets Carnés Holding

   Responsabilités :
   - Chargement catalogue produits + règles DLC + personnel
   - Autocomplétion produit → pré-remplissage champs
   - Calcul DLC en temps réel (client-side)
   - Soumission POST /api/etiquettes/generer
   - Affichage résultat (lot, DLC, statut impression)
   - Panneau alertes DLC et historique du jour
   ============================================================ */

// ── Références DOM ────────────────────────────────────────────
const elHorloge        = document.getElementById('etiq-horloge');
const elForm           = document.getElementById('etiq-form');
const elSearch         = document.getElementById('etiq-produit-search');
const elDatalist       = document.getElementById('etiq-datalist');
const elSelectionne    = document.getElementById('etiq-produit-selectionne');
const elProduitNom     = document.getElementById('etiq-produit-nom');
const elProduitMeta    = document.getElementById('etiq-produit-meta');
const elEffacer        = document.getElementById('etiq-produit-effacer');
const elManuelZone     = document.getElementById('etiq-produit-manuel-zone');
const elToggleManuel   = document.getElementById('etiq-toggle-manuel');
const elNomManuel      = document.getElementById('etiq-nom-manuel');
const elDlcJours       = document.getElementById('etiq-dlc-jours');
const elTempCons       = document.getElementById('etiq-temp-cons');
const elDateRef        = document.getElementById('etiq-date-ref');
const elDlcPreview     = document.getElementById('etiq-dlc-preview');
const elLotFournZone   = document.getElementById('etiq-lot-fourn-zone');
const elOperateur      = document.getElementById('etiq-operateur');
const elBtnGenerer     = document.getElementById('etiq-btn-generer');
const elResultat       = document.getElementById('etiq-resultat');
const elErreur         = document.getElementById('etiq-erreur');
const elAlertesListe   = document.getElementById('etiq-alertes-liste');
const elHistoListe     = document.getElementById('etiq-histo-liste');

// ── État ──────────────────────────────────────────────────────
let produits           = [];   // catalogue
let reglesDlc          = {};   // {categorie: dlc_jours}
let produitSelectionne = null; // objet produit sélectionné dans catalogue
let modeManuel         = false;

// ── Horloge ───────────────────────────────────────────────────
function majHorloge() {
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();

// ── Date par défaut = aujourd'hui ────────────────────────────
elDateRef.value = new Date().toISOString().slice(0, 10);

// ── Fetch helper ──────────────────────────────────────────────
async function apiFetch(url, options = {}) {
  const res = await fetch(url, { cache: 'no-store', ...options });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} — ${txt || url}`);
  }
  return res.json();
}

// ── Chargement données initiales ─────────────────────────────
async function init() {
  await Promise.all([
    chargerProduits(),
    chargerReglesDlc(),
    chargerPersonnel(),
    chargerAlertes(),
    chargerHistorique(),
  ]);
  majDlcPreview();
}

async function chargerProduits() {
  try {
    produits = await apiFetch('/api/produits');
    // Remplir datalist
    elDatalist.innerHTML = produits.map(p =>
      `<option value="${escAttr(p.nom)}" data-id="${p.id}">`
    ).join('');
  } catch {
    // Pas bloquant
  }
}

async function chargerReglesDlc() {
  try {
    const regles = await apiFetch('/api/regles-dlc');
    regles.forEach(r => { reglesDlc[r.categorie] = r.dlc_jours; });
  } catch {
    // Valeurs par défaut
    Object.assign(reglesDlc, {
      viande_hachee: 1, viande_pieces: 3, preparation_crue: 2,
      charcuterie_tranchee: 5, plat_cuisine: 3,
      produit_deconge: 3, produit_congele: 180,
    });
  }
}

async function chargerPersonnel() {
  try {
    const personnel = await apiFetch('/api/admin/personnel');
    personnel.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.prenom;
      opt.textContent = p.prenom;
      elOperateur.appendChild(opt);
    });
  } catch {
    // Pas bloquant
  }
}

// ── Alertes DLC ───────────────────────────────────────────────
async function chargerAlertes() {
  elAlertesListe.innerHTML = '<div class="etiq-panel-vide">Chargement…</div>';
  try {
    const alertes = await apiFetch('/api/etiquettes/alertes-dlc');
    if (!alertes || alertes.length === 0) {
      elAlertesListe.innerHTML = '<div class="etiq-panel-vide etiq-panel-ok">✓ Aucune DLC critique</div>';
      return;
    }
    elAlertesListe.innerHTML = alertes.map(a => {
      const dlc  = new Date(a.dlc);
      const diff = Math.ceil((dlc - new Date().setHours(0,0,0,0)) / 86400000);
      const cls  = diff <= 0 ? 'etiq-alerte--expire' : diff === 1 ? 'etiq-alerte--urgent' : 'etiq-alerte--proche';
      const label = diff <= 0 ? 'Expiré' : diff === 1 ? 'Demain' : `J+${diff}`;
      return `<div class="etiq-alerte-ligne ${cls}">
        <span class="etiq-alerte-nom">${escHtml(a.produit_nom)}</span>
        <span class="etiq-alerte-dlc">${label} — ${dlc.toLocaleDateString('fr-FR', {day:'2-digit',month:'short'})}</span>
      </div>`;
    }).join('');
  } catch {
    elAlertesListe.innerHTML = '<div class="etiq-panel-vide etiq-panel-erreur">⚠ Erreur chargement</div>';
  }
}

// ── Historique du jour ────────────────────────────────────────
async function chargerHistorique() {
  elHistoListe.innerHTML = '<div class="etiq-panel-vide">Chargement…</div>';
  try {
    const etiquettes = await apiFetch('/api/etiquettes?jours=1');
    if (!etiquettes || etiquettes.length === 0) {
      elHistoListe.innerHTML = '<div class="etiq-panel-vide">Aucune étiquette aujourd\'hui</div>';
      return;
    }
    elHistoListe.innerHTML = etiquettes.slice(0, 20).map(e => {
      const dlc = new Date(e.dlc).toLocaleDateString('fr-FR', {day:'2-digit', month:'short'});
      return `<div class="etiq-histo-ligne">
        <div class="etiq-histo-nom">${escHtml(e.produit_nom)}</div>
        <div class="etiq-histo-meta">
          <span class="etiq-histo-lot">${escHtml(e.numero_lot ?? '—')}</span>
          <span class="etiq-histo-dlc">DLC ${dlc}</span>
          <span class="etiq-histo-op">${escHtml(e.operateur ?? '')}</span>
        </div>
      </div>`;
    }).join('');
  } catch {
    elHistoListe.innerHTML = '<div class="etiq-panel-vide etiq-panel-erreur">⚠ Erreur chargement</div>';
  }
}

// ── Calcul DLC (client-side pour preview) ────────────────────
function calculerDlcPreview() {
  const dateVal  = elDateRef.value;
  if (!dateVal) return null;

  const typeDate = document.querySelector('[name="type_date"]:checked')?.value;
  let jours = null;

  if (typeDate === 'decongélation') {
    jours = 3;
  } else if (produitSelectionne) {
    jours = produitSelectionne.dlc_jours;
  } else if (modeManuel && elDlcJours.value) {
    jours = parseInt(elDlcJours.value);
  }

  if (jours === null) return null;

  const base = new Date(dateVal);
  base.setDate(base.getDate() + jours);
  return base;
}

function majDlcPreview() {
  const dlc = calculerDlcPreview();
  if (!dlc) {
    elDlcPreview.textContent = '—';
    elDlcPreview.className   = 'etiq-dlc-preview';
    return;
  }
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.ceil((dlc - today) / 86400000);

  elDlcPreview.textContent = dlc.toLocaleDateString('fr-FR', {
    weekday: 'short', day: '2-digit', month: 'short',
  });

  if (diff <= 1)      elDlcPreview.className = 'etiq-dlc-preview etiq-dlc-preview--alerte';
  else if (diff <= 2) elDlcPreview.className = 'etiq-dlc-preview etiq-dlc-preview--attention';
  else                elDlcPreview.className = 'etiq-dlc-preview etiq-dlc-preview--ok';
}

// ── Sélection produit via autocomplete ───────────────────────
elSearch.addEventListener('input', () => {
  const val = elSearch.value.trim();
  if (!val) return;

  // Chercher correspondance exacte dans catalogue
  const trouve = produits.find(p => p.nom.toLowerCase() === val.toLowerCase());
  if (trouve) {
    selectionnerProduit(trouve);
    elSearch.value = '';
  }
});

elSearch.addEventListener('change', () => {
  const val = elSearch.value.trim();
  if (!val) return;
  const trouve = produits.find(p => p.nom.toLowerCase() === val.toLowerCase());
  if (trouve) {
    selectionnerProduit(trouve);
    elSearch.value = '';
  }
});

function selectionnerProduit(produit) {
  produitSelectionne = produit;
  modeManuel = false;

  elProduitNom.textContent = produit.nom;
  elProduitMeta.textContent = `${labelCategorie(produit.categorie)} — DLC J+${produit.dlc_jours}`
    + (produit.temperature_conservation ? ` — ${produit.temperature_conservation}` : '');

  elSelectionne.hidden = false;
  elManuelZone.hidden  = true;
  elToggleManuel.hidden = true;

  majDlcPreview();
}

elEffacer.addEventListener('click', () => {
  produitSelectionne = null;
  elSelectionne.hidden  = true;
  elToggleManuel.hidden = false;
  elSearch.value = '';
  majDlcPreview();
});

// ── Mode manuel ───────────────────────────────────────────────
elToggleManuel.addEventListener('click', () => {
  modeManuel = !modeManuel;
  elManuelZone.hidden = !modeManuel;
  elToggleManuel.textContent = modeManuel ? '− Annuler saisie manuelle' : '＋ Produit absent du catalogue';
  if (!modeManuel) majDlcPreview();
});

elDlcJours.addEventListener('input', majDlcPreview);

// ── Réactivité formulaire ─────────────────────────────────────
document.querySelectorAll('[name="type_date"]').forEach(radio => {
  radio.addEventListener('change', majDlcPreview);
});

elDateRef.addEventListener('change', majDlcPreview);

document.querySelectorAll('[name="lot_type"]').forEach(radio => {
  radio.addEventListener('change', () => {
    elLotFournZone.hidden = radio.value !== 'fournisseur' || !radio.checked;
  });
});

// ── Soumission formulaire ─────────────────────────────────────
elForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  elErreur.hidden  = true;
  elResultat.hidden = true;

  const typeDate  = document.querySelector('[name="type_date"]:checked')?.value;
  const lotType   = document.querySelector('[name="lot_type"]:checked')?.value;
  const dateRef   = elDateRef.value;
  const operateur = elOperateur.value;

  // Validation basique
  if (!dateRef) return afficherErreur('Veuillez choisir une date.');
  if (!operateur) return afficherErreur('Veuillez sélectionner un opérateur.');

  let produitNom, dlcJours, tempCons, produitId;

  if (produitSelectionne) {
    produitId  = produitSelectionne.id;
    produitNom = produitSelectionne.nom;
    tempCons   = produitSelectionne.temperature_conservation;
    dlcJours   = typeDate === 'decongélation' ? 3 : undefined;
  } else if (modeManuel) {
    produitNom = elNomManuel.value.trim();
    if (!produitNom) return afficherErreur('Veuillez saisir le nom du produit.');
    if (typeDate !== 'decongélation') {
      dlcJours = parseInt(elDlcJours.value);
      if (!dlcJours || dlcJours < 1) return afficherErreur('Veuillez indiquer la durée DLC en jours.');
    } else {
      dlcJours = 3;
    }
    tempCons = elTempCons.value.trim() || undefined;
  } else {
    return afficherErreur('Veuillez sélectionner ou saisir un produit.');
  }

  const payload = {
    produit_id:              produitId ?? null,
    produit_nom:             produitNom,
    type_date:               typeDate,
    date_etiquette:          dateRef,
    operateur,
    lot_type:                lotType,
    numero_lot_fournisseur:  lotType === 'fournisseur' ? document.getElementById('etiq-lot-fourn').value.trim() : null,
    info_complementaire:     document.getElementById('etiq-info-comp').value.trim() || null,
    temperature_conservation: tempCons ?? null,
    dlc_jours:               produitId ? undefined : dlcJours,
  };

  if (lotType === 'fournisseur' && !payload.numero_lot_fournisseur) {
    return afficherErreur('Veuillez saisir le numéro de lot fournisseur.');
  }

  // Nettoyage champs undefined
  Object.keys(payload).forEach(k => { if (payload[k] === undefined) delete payload[k]; });

  elBtnGenerer.disabled   = true;
  elBtnGenerer.textContent = '⏳ Génération…';

  try {
    const result = await apiFetch('/api/etiquettes/generer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    afficherResultat(result);
    await Promise.all([chargerAlertes(), chargerHistorique()]);
  } catch (err) {
    afficherErreur(`Erreur : ${err.message}`);
  } finally {
    elBtnGenerer.disabled   = false;
    elBtnGenerer.textContent = '🖨 Générer & imprimer';
  }
});

function afficherResultat(r) {
  const dlcDate = new Date(r.dlc).toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long',
  });
  const impHtml = r.impression_ok
    ? '<span class="etiq-imp-ok">✓ Imprimé</span>'
    : `<span class="etiq-imp-non">⚠ Non imprimé${r.impression_erreur ? ` — ${escHtml(r.impression_erreur)}` : ''}</span>`;

  elResultat.innerHTML = `
    <div class="etiq-resultat-contenu">
      <div class="etiq-resultat-ok">✅ Étiquette créée</div>
      <div class="etiq-resultat-ligne">
        <span class="etiq-resultat-label">N° lot</span>
        <strong class="etiq-resultat-val">${escHtml(r.numero_lot)}</strong>
      </div>
      <div class="etiq-resultat-ligne">
        <span class="etiq-resultat-label">DLC</span>
        <strong class="etiq-resultat-val etiq-resultat-dlc">${dlcDate}</strong>
      </div>
      <div class="etiq-resultat-ligne">
        <span class="etiq-resultat-label">Impression</span>
        ${impHtml}
      </div>
    </div>`;
  elResultat.hidden = false;
  elResultat.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function afficherErreur(msg) {
  elErreur.textContent = msg;
  elErreur.hidden = false;
}

// ── Boutons refresh ───────────────────────────────────────────
document.getElementById('etiq-refresh-alertes').addEventListener('click', chargerAlertes);
document.getElementById('etiq-refresh-histo').addEventListener('click', chargerHistorique);

// ── Helpers ───────────────────────────────────────────────────
function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escAttr(str) {
  return String(str ?? '').replace(/"/g, '&quot;');
}

function labelCategorie(code) {
  const LABELS = {
    viande_hachee: 'Viande hachée', viande_pieces: 'Pièces',
    preparation_crue: 'Préparation crue', charcuterie_tranchee: 'Charcuterie',
    plat_cuisine: 'Plat cuisiné', produit_deconge: 'Décongelé',
    produit_congele: 'Congelé',
  };
  return LABELS[code] ?? code;
}

// ── Init ──────────────────────────────────────────────────────
init();

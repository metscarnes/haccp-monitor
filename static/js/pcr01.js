'use strict';
/* ============================================================
   pcr01.js — Fiche Incident PCR01 (écran dédié)
   Au Comptoir des Lilas — Mets Carnés Holding

   Pilote pcr01.html via sessionStorage :
     haccp_pcr01_data      → données NC de la session réception
     haccp_pcr01_signature → dataURL signature livreur (optionnel)
     haccp_rec_state       → état complet du wizard (pour retour)
   ============================================================ */

// ── Références DOM ─────────────────────────────────────────
const elHeaderBadge   = document.getElementById('pcr-header-badge');
const elDate          = document.getElementById('pcr-date');
const elOperateur     = document.getElementById('pcr-operateur');
const elPagination    = document.getElementById('pcr-pagination');
const elPaginLbl      = document.getElementById('pcr-pagination-label');
const elProduitNom    = document.getElementById('pcr-produit-nom');
const elLotRow        = document.getElementById('pcr-lot-row');
const elLot           = document.getElementById('pcr-lot');
const elMotifs        = document.getElementById('pcr-motifs');
const elActionImm     = document.getElementById('pcr-action-imm');
const elEtapesListe   = document.getElementById('pcr-etapes-liste');
const elCorrective    = document.getElementById('pcr-corrective');
const elSuivi         = document.getElementById('pcr-suivi');
const elSigBloc       = document.getElementById('pcr-sig-bloc');
const elSigImg        = document.getElementById('pcr-sig-img');
const elErreur        = document.getElementById('pcr-erreur');
const elBtnEnreg      = document.getElementById('pcr-btn-enreg');
const elBtnRetour     = document.getElementById('pcr-btn-retour');


// ── Charger l'état depuis sessionStorage ────────────────────
const pcrDataRaw = sessionStorage.getItem('haccp_pcr01_data');
const sigDataUrl  = sessionStorage.getItem('haccp_pcr01_signature');

// Si aucune session active → retour réception
if (!pcrDataRaw) {
  window.location.replace('/reception.html');
}

const pcrData = JSON.parse(pcrDataRaw);
let {
  receptionId,
  personnelPrenom,
  fournisseurId,
  livreurPresent,
  ncProduits,
  ncActions,
  ncFicheIndex,
} = pcrData;


// ── Date / opérateur ────────────────────────────────────────
elDate.textContent = new Date().toLocaleDateString('fr-FR', {
  weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
});
elOperateur.textContent = `Opérateur : ${personnelPrenom}`;


// ── Signature livreur ───────────────────────────────────────
if (livreurPresent && sigDataUrl) {
  elSigBloc.hidden = false;
  elSigImg.src = sigDataUrl;
}


// ── Libellé action immédiate ────────────────────────────────
function libelleAction(action) {
  switch (String(action)) {
    case 'refus':              return '🚫 Refus du lot';
    case 'isole':              return '⚠️ Isolement du produit';
    case 'refus_et_isolement': return '🚫 Refus du lot + ⚠️ Isolement';
    default:                   return '⚠️ Isolement du produit';
  }
}


// ── Générer le texte action corrective (auto-fill) ──────────
//
// Décrit chronologiquement ce que l'opérateur a déjà fait :
//   1. NC constatée à la réception (motifs détectés)
//   2. Lot isolé → prise de température à cœur
//   3a. Livreur présent → feuille de reprise signée (retour)
//   3b. Livreur absent  → étiquette À REPRENDRE apposée
//
function genererActionCorrective(produit) {
  const motifs = produit.motifs.length
    ? produit.motifs.join(', ')
    : 'non-conformité';

  let txt = `Non-conformité constatée à la réception : ${motifs} sur ${produit.produit_nom}`;
  if (produit.numero_lot) txt += ` (lot ${produit.numero_lot})`;
  txt += '.\n\nLe lot a été isolé et la température à cœur a été prise.';

  if (livreurPresent) {
    txt += '\n\nLe livreur étant présent, la feuille de reprise avec retour marchandise a été signée par le livreur.';
  } else {
    txt += "\n\nEn l'absence du livreur, le lot a été isolé avec apposition de l'étiquette À REPRENDRE en attente de retour fournisseur.";
  }

  return txt;
}


// ── Construire la timeline des étapes d'identification ──────
function construireEtapes(produit) {
  const motifs = produit.motifs.join(', ') || 'non-conformité';

  const etapes = [
    `Contrôle à la réception (visuel / température) → Non-conformité détectée : ${motifs}.`,
    'Lot isolé immédiatement pour prise de température à cœur.',
  ];

  if (livreurPresent) {
    etapes.push(
      'Livreur présent : feuille de reprise avec retour marchandise signée par le livreur.'
    );
  } else {
    etapes.push(
      "Livreur absent : lot isolé avec apposition de l'étiquette À REPRENDRE en attente de retour fournisseur."
    );
  }

  elEtapesListe.innerHTML = '';
  etapes.forEach(texte => {
    const item = document.createElement('div');
    item.className = 'pcr-etape-item';

    const puce = document.createElement('div');
    puce.className = 'pcr-etape-puce';
    puce.setAttribute('aria-hidden', 'true');

    const txt = document.createElement('div');
    txt.className = 'pcr-etape-texte';
    txt.textContent = texte;

    item.appendChild(puce);
    item.appendChild(txt);
    elEtapesListe.appendChild(item);
  });
}


// ── Charger la fiche courante ───────────────────────────────
function chargerFiche(idx) {
  const l = ncProduits[idx];
  const total = ncProduits.length;

  // Badge header
  elHeaderBadge.textContent = `${idx + 1}/${total}`;

  // Pagination (visible si >1 fiche)
  if (total > 1) {
    elPagination.hidden = false;
    elPaginLbl.textContent = `Fiche incident ${idx + 1} sur ${total}`;
  } else {
    elPagination.hidden = true;
  }

  // Produit
  elProduitNom.textContent = l.produit_nom;

  // Lot
  if (l.numero_lot) {
    elLot.textContent = l.numero_lot;
    elLotRow.hidden   = false;
  } else {
    elLotRow.hidden = true;
  }

  // Motifs NC
  elMotifs.textContent = l.motifs.join(', ') || 'non-conformité';

  // Action immédiate
  const actionKey = ncActions[String(l.id)] ?? ncActions[l.id] ?? 'isole';
  elActionImm.textContent = libelleAction(actionKey);

  // Timeline des étapes
  construireEtapes(l);

  // Auto-fill action corrective
  elCorrective.value = genererActionCorrective(l);

  // Vider le suivi pour chaque nouvelle fiche
  elSuivi.value = '';

  // Masquer l'erreur
  elErreur.hidden = true;
}


// ── Fetch helper ────────────────────────────────────────────
async function apiFetch(url, options = {}) {
  const res = await fetch(url, { cache: 'no-store', ...options });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} — ${txt || url}`);
  }
  return res.json();
}


// ── Convertir dataURL en Blob (pour FormData) ───────────────
function dataUrlToBlob(dataUrl) {
  const [header, data] = dataUrl.split(',');
  const mime   = header.match(/:(.*?);/)[1];
  const binary = atob(data);
  const bytes  = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes], { type: mime });
}


// ── Enregistrer la fiche courante via API ───────────────────
elBtnEnreg.addEventListener('click', enregistrerFiche);

async function enregistrerFiche() {
  const corrective = elCorrective.value.trim();
  if (!corrective) {
    elErreur.textContent = "L'action corrective est obligatoire.";
    elErreur.hidden = false;
    elCorrective.focus();
    return;
  }

  elBtnEnreg.disabled = true;
  elBtnEnreg.textContent = 'Enregistrement…';
  elErreur.hidden = true;

  const l         = ncProduits[ncFicheIndex];
  const actionKey = ncActions[String(l.id)] ?? ncActions[l.id] ?? 'isole';

  const fd = new FormData();
  fd.append('reception_id',      receptionId);
  fd.append('fournisseur_id',    l.fournisseur_id || fournisseurId || 1);
  fd.append('produit_id',        l.produit_id);
  fd.append('nature_probleme',   l.motifs[0] || 'autre');
  fd.append('action_immediate',  actionKey);
  fd.append('livreur_present',   livreurPresent ? 1 : 0);
  if (l.id)          fd.append('reception_ligne_id', l.id);
  if (l.numero_lot)  fd.append('numero_lot',         l.numero_lot);
  if (l.motifs.length > 1) fd.append('description',  l.motifs.join(', '));
  fd.append('action_corrective', corrective);
  if (elSuivi.value.trim()) fd.append('suivi', elSuivi.value.trim());

  // Joindre la signature PNG si livreur présent
  if (livreurPresent && sigDataUrl) {
    fd.append('signature_livreur', dataUrlToBlob(sigDataUrl), 'signature.png');
  }

  try {
    await apiFetch('/api/fiches-incident', { method: 'POST', body: fd });

    if (ncFicheIndex < ncProduits.length - 1) {
      // → Fiche suivante
      ncFicheIndex++;
      pcrData.ncFicheIndex = ncFicheIndex;
      sessionStorage.setItem('haccp_pcr01_data', JSON.stringify(pcrData));
      chargerFiche(ncFicheIndex);
    } else {
      // → Toutes les fiches enregistrées : retour réception
      sessionStorage.setItem('haccp_pcr01_done', '1');
      window.location.href = '/reception.html';
    }
  } catch (err) {
    elErreur.textContent = `Erreur : ${err.message}`;
    elErreur.hidden = false;
  } finally {
    elBtnEnreg.disabled = false;
    elBtnEnreg.textContent = '💾 Enregistrer cette fiche';
  }
}


// ── Bouton retour (sans valider) ────────────────────────────
elBtnRetour.addEventListener('click', () => {
  // On revient à la réception sans marquer pcr01 comme terminé
  // → le wizard reprendra la procédure NC depuis l'étape A
  window.location.href = '/reception.html';
});


// ── Initialisation ──────────────────────────────────────────
chargerFiche(ncFicheIndex);

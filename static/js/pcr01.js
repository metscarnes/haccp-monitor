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
const elProduitNom       = document.getElementById('pcr-produit-nom');
const elFournisseurRow   = document.getElementById('pcr-fournisseur-row');
const elFournisseur      = document.getElementById('pcr-fournisseur');
const elLotRow           = document.getElementById('pcr-lot-row');
const elLot              = document.getElementById('pcr-lot');
const elDlcRow           = document.getElementById('pcr-dlc-row');
const elDlc              = document.getElementById('pcr-dlc');
const elMotifs        = document.getElementById('pcr-motifs');
const elActionImm     = document.getElementById('pcr-action-imm');
const elEtapesListe   = document.getElementById('pcr-etapes-liste');
const elCorrective    = document.getElementById('pcr-corrective');
const elCommentaire   = document.getElementById('pcr-commentaire');
const elSigBloc        = document.getElementById('pcr-sig-bloc');
const elLivreurAccepte = document.getElementById('pcr-livreur-accepte');
const elLivreurRefuse  = document.getElementById('pcr-livreur-refuse');
const elSigCanvas      = document.getElementById('pcr-sig-canvas');
const elSigEffacer     = document.getElementById('pcr-sig-effacer');
const elEtiqRepriseBloc = document.getElementById('pcr-etiq-reprise-bloc');
const elEtiqRepriseBtn = document.getElementById('pcr-etiq-reprise-btn');
const elEtiqBloc       = document.getElementById('pcr-etiq-bloc');
const elEtiqListe      = document.getElementById('pcr-etiq-liste');
const elErreur        = document.getElementById('pcr-erreur');
const elBtnEnreg      = document.getElementById('pcr-btn-enreg');
const elBtnRetour     = document.getElementById('pcr-btn-retour');


// ── Charger l'état depuis sessionStorage ────────────────────
const pcrDataRaw = sessionStorage.getItem('haccp_pcr01_data');

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
  ncCoeurResultats,
  ncFicheIndex,
  tempCamion,
  heureReception,
} = pcrData;
ncCoeurResultats = ncCoeurResultats || {};

// État signature livreur (si présent)
let livreurAccepte = null; // null (pas de choix), true (accepte), false (refuse)


// ── Date / opérateur / heure ────────────────────────────────
elDate.textContent = new Date().toLocaleDateString('fr-FR', {
  weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
});
const heureText = heureReception ? ` à ${heureReception}` : '';
elOperateur.textContent = `Opérateur : ${personnelPrenom}${heureText}`;


// ── Signature livreur (canvas, si présent) ──────────────────
let sigCtx  = null;
let sigDraw = false;

if (livreurPresent) {
  elSigBloc.hidden = false;
  initSigCanvas();
} else {
  // Livreur absent → afficher les boutons impression étiquette
  elEtiqBloc.hidden = false;
  construireEtiquettes();
}

function initSigCanvas() {
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
  elSigCanvas.addEventListener('mousedown',  e => { sigDraw = true; const p = pos(e); sigCtx.beginPath(); sigCtx.moveTo(p.x, p.y); });
  elSigCanvas.addEventListener('mousemove',  e => { if (!sigDraw) return; const p = pos(e); sigCtx.lineTo(p.x, p.y); sigCtx.stroke(); });
  elSigCanvas.addEventListener('mouseup',    () => sigDraw = false);
  elSigCanvas.addEventListener('touchstart', e => { e.preventDefault(); sigDraw = true; const p = pos(e); sigCtx.beginPath(); sigCtx.moveTo(p.x, p.y); }, { passive: false });
  elSigCanvas.addEventListener('touchmove',  e => { e.preventDefault(); if (!sigDraw) return; const p = pos(e); sigCtx.lineTo(p.x, p.y); sigCtx.stroke(); }, { passive: false });
  elSigCanvas.addEventListener('touchend',   () => sigDraw = false);
}

if (elSigEffacer) {
  elSigEffacer.addEventListener('click', () => {
    if (sigCtx) sigCtx.clearRect(0, 0, elSigCanvas.width, elSigCanvas.height);
  });
}

// ── Boutons choix livreur (attestation + retour) ─────────────
function majUILivreur() {
  if (elLivreurAccepte) {
    if (livreurAccepte === true) {
      elLivreurAccepte.classList.add('sel');
      elLivreurRefuse.classList.remove('sel');
    } else if (livreurAccepte === false) {
      elLivreurRefuse.classList.add('sel');
      elLivreurAccepte.classList.remove('sel');
    } else {
      elLivreurAccepte.classList.remove('sel');
      elLivreurRefuse.classList.remove('sel');
    }
  }
  if (elEtiqRepriseBloc) {
    elEtiqRepriseBloc.hidden = livreurAccepte !== false;
  }
  // Régénérer le texte corrective de la fiche courante
  const l = ncProduits[ncFicheIndex];
  if (l && elCorrective) {
    elCorrective.value = genererActionCorrective(l);
  }
}

if (elLivreurAccepte) {
  elLivreurAccepte.addEventListener('click', () => {
    livreurAccepte = true;
    majUILivreur();
  });
}

if (elLivreurRefuse) {
  elLivreurRefuse.addEventListener('click', () => {
    livreurAccepte = false;
    majUILivreur();
  });
}

// Bouton impression étiquette (si refus)
if (elEtiqRepriseBtn) {
  elEtiqRepriseBtn.addEventListener('click', async () => {
    const l = ncProduits[ncFicheIndex];
    elEtiqRepriseBtn.disabled = true;
    try {
      await fetch('/api/impression/etiquette-reprise', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          produit_nom:      l.produit_nom,
          motif:            l.motifs.join(', ') || 'non-conformité',
          operateur_prenom: personnelPrenom,
          date_refus:       new Date().toISOString().slice(0, 10),
        }),
      });
      elEtiqRepriseBtn.classList.add('imprime');
      elEtiqRepriseBtn.innerHTML = `✓ Imprimé — ${l.produit_nom}`;
    } catch (e) {
      elEtiqRepriseBtn.disabled = false;
      alert(`Impression échouée : ${e.message}`);
    }
  });
}

// ── Étiquettes À RETOURNER (livreur absent) ─────────────────
function construireEtiquettes() {
  if (!elEtiqListe) return;
  elEtiqListe.innerHTML = '';
  ncProduits.forEach(l => {
    const btn = document.createElement('button');
    btn.className = 'pcr-etiq-btn';
    btn.innerHTML = `🖨️ &nbsp;Étiquette — ${l.produit_nom}`;
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      try {
        await fetch('/api/impression/etiquette-reprise', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            produit_nom:      l.produit_nom,
            motif:            l.motifs.join(', ') || 'non-conformité',
            operateur_prenom: personnelPrenom,
            date_refus:       new Date().toISOString().slice(0, 10),
          }),
        });
        btn.classList.add('imprime');
        btn.innerHTML = `✓ &nbsp;Imprimé — ${l.produit_nom}`;
      } catch (e) {
        btn.disabled = false;
        btn.innerHTML = `⚠️ Erreur impression — ${l.produit_nom}`;
      }
    });
    elEtiqListe.appendChild(btn);
  });
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

  const coeur = ncCoeurResultats[produit.id] || ncCoeurResultats[String(produit.id)];
  const coeurTxt = coeur
    ? ` La température à cœur mesurée est de ${coeur.temp_coeur}°C.`
    : '';

  let txt = `Non-conformité constatée à la réception : ${motifs} sur ${produit.produit_nom}`;
  if (produit.numero_lot) txt += ` (lot ${produit.numero_lot})`;
  txt += `.\n\nContrôle à cœur effectué : non-conformité confirmée.${coeurTxt}`;

  if (livreurPresent) {
    if (livreurAccepte === true) {
      txt += '\n\nLe livreur étant présent, la non-conformité est attestée et le retour accepté, la feuille de reprise avec retour marchandise a été signée par le livreur.';
    } else if (livreurAccepte === false) {
      txt += '\n\nLe livreur étant présent, la non-conformité n\'est pas attestée par le livreur et le retour n\'est pas accepté, la feuille de reprise a été signée par le livreur. Le produit est isolé et balisé en attente de la résolution du litige.';
    } else {
      txt += '\n\nLe livreur étant présent, la feuille de reprise a été signée.';
    }
  } else {
    txt += "\n\nEn l'absence du livreur, le lot a été isolé avec apposition de l'étiquette À RETOURNER en attente de retour fournisseur.";
  }

  return txt;
}


// ── Construire la timeline des étapes d'identification ──────
function construireEtapes(produit) {
  const motifs = produit.motifs.join(', ') || 'non-conformité';
  const tempCamionTxt = tempCamion !== null && tempCamion !== undefined ? ` (température camion : ${tempCamion}°C)` : '';

  const etapes = [
    `Contrôle à la réception (visuel / température) → Non-conformité détectée : ${motifs}${tempCamionTxt}.`,
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

  // Fournisseur
  if (l.fournisseur_nom) {
    elFournisseur.textContent = l.fournisseur_nom;
    elFournisseurRow.hidden = false;
  } else {
    elFournisseurRow.hidden = true;
  }

  // DLC / DLUO
  const dlcVal = l.dlc || l.dluo;
  const dlcLabel = l.dluo ? 'DLUO' : 'DLC';
  if (dlcVal) {
    elDlc.textContent = dlcVal;
    elDlcRow.querySelector('.pcr-champ-label').textContent = dlcLabel;
    elDlcRow.hidden = false;
  } else {
    elDlcRow.hidden = true;
  }

  // Lot
  if (l.numero_lot) {
    elLot.textContent = l.numero_lot;
    elLotRow.hidden   = false;
  } else {
    elLotRow.hidden = true;
  }

  // Motifs NC
  elMotifs.textContent = l.motifs.join(', ') || 'non-conformité';

  // Action immédiate : contrôle à cœur confirmé NC
  const coeur = ncCoeurResultats[l.id] || ncCoeurResultats[String(l.id)];
  const tempCoeurTxt = coeur ? ` (T° à cœur : ${coeur.temp_coeur}°C)` : '';
  elActionImm.textContent = `🌡️ Contrôle à cœur effectué — NC confirmé${tempCoeurTxt}`;

  // Timeline des étapes
  construireEtapes(l);

  // Auto-fill action corrective
  elCorrective.value = genererActionCorrective(l);

  // Vider le commentaire pour chaque nouvelle fiche
  if (elCommentaire) elCommentaire.value = '';

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

  const l     = ncProduits[ncFicheIndex];
  const coeur = ncCoeurResultats[l.id] || ncCoeurResultats[String(l.id)];

  const fd = new FormData();
  fd.append('reception_id',      receptionId);
  fd.append('fournisseur_id',    l.fournisseur_id || fournisseurId || 1);
  fd.append('produit_id',        l.produit_id);
  fd.append('nature_probleme',   l.motifs[0] || 'temperature');
  fd.append('action_immediate',  'controle_coeur_nc');
  fd.append('livreur_present',   livreurPresent ? 1 : 0);
  if (l.id)          fd.append('reception_ligne_id', l.id);
  if (l.numero_lot)  fd.append('numero_lot',         l.numero_lot);
  if (l.motifs.length > 1) fd.append('description',  l.motifs.join(', '));
  fd.append('action_corrective', corrective);
  if (coeur && coeur.temp_coeur != null) fd.append('temperature_coeur', coeur.temp_coeur);
  if (elCommentaire && elCommentaire.value.trim()) fd.append('commentaire', elCommentaire.value.trim());

  // Joindre la signature PNG si livreur présent (capturée dans ce canvas)
  if (livreurPresent && sigCtx) {
    const dataUrl = elSigCanvas.toDataURL('image/png');
    fd.append('signature_livreur', dataUrlToBlob(dataUrl), 'signature.png');
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

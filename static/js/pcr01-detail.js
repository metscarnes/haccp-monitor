'use strict';
/* ============================================================
   pcr01-detail.js — Affichage fiche PCR01 enregistrée (lecture seule)
   Au Comptoir des Lilas — Mets Carnés Holding
   ============================================================ */

const elBtnRetour = document.getElementById('pcr-btn-retour');
const elMain = document.getElementById('pcr-main');

// ── Inactivité ──────────────────────────────────────────────
let timerInactivite;
function resetInactivite() {
  clearTimeout(timerInactivite);
  timerInactivite = setTimeout(() => {
    window.location.href = '/hub.html';
  }, 5 * 60 * 1000);
}
document.addEventListener('click',      resetInactivite, true);
document.addEventListener('touchstart', resetInactivite, { passive: true, capture: true });
resetInactivite();

// ── Retour ──────────────────────────────────────────────────
elBtnRetour.addEventListener('click', () => {
  window.history.back();
});

// ── Fetch ───────────────────────────────────────────────────
async function apiFetch(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Formatage date complète avec jour semaine + heure ───────
function formatDateHeureFR(isoDate, heureStr) {
  if (!isoDate) return '—';
  try {
    // isoDate = "2026-04-11", heureStr = "15:25"
    const d = new Date(isoDate + 'T12:00:00'); // midi pour éviter décalage TZ
    const dateStr = d.toLocaleDateString('fr-FR', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    });
    return heureStr ? `${dateStr} à ${heureStr}` : dateStr;
  } catch { return isoDate; }
}

// ── Traduction des codes motifs ─────────────────────────────
const MOTIFS_LABELS = {
  'temperature':         'Température non conforme',
  'dlc_depassee':        'DLC / DLUO dépassée',
  'conditionnement':     'Défaut de conditionnement',
  'aspect_visuel':       'Aspect visuel non conforme',
  'odeur':               'Odeur anormale',
  'etiquetage':          'Défaut d\'étiquetage',
  'quantite':            'Quantité non conforme',
  'proprete_camion':     'Propreté camion non satisfaisante',
  'refus_livraison':     'Livraison refusée',
};

function traduireMotif(code) {
  return MOTIFS_LABELS[code] || code;
}

// ── Formatage action immédiate ──────────────────────────────
function formatActionImmediate(fiche) {
  const code = fiche.action_immediate || '';
  if (code === 'controle_coeur_nc') {
    const t = fiche.temperature_coeur != null ? ` (T° à cœur : ${fiche.temperature_coeur}°C)` : '';
    return `🌡️ Contrôle à cœur effectué — NC confirmé${t}`;
  }
  if (code === 'refus_livraison') {
    return '🚚 Livraison refusée — Propreté camion non satisfaisante';
  }
  return traduireMotif(code);
}

// ── Reconstruction timeline étapes ─────────────────────────
function construireEtapes(fiche) {
  const motifs = fiche.description || fiche.nature_probleme || 'non-conformité';
  const estCamion = fiche.action_immediate === 'refus_livraison';

  let etapes;
  if (estCamion) {
    etapes = [
      `Contrôle du camion à la réception → Non-conformité détectée : ${motifs}.`,
    ];
    if (fiche.fournisseur_nom) {
      const noms = fiche.fournisseur_nom.split(/\s*\+\s*/).filter(Boolean);
      const lbl = noms.length > 1
        ? `Fournisseurs concernés (${noms.length}) : ${noms.join(', ')}.`
        : `Fournisseur concerné : ${fiche.fournisseur_nom}.`;
      etapes.push(lbl);
    }
    etapes.push('Livraison refusée pour l\'ensemble du camion.');
    if (fiche.livreur_present) {
      etapes.push('Livreur présent : feuille de reprise avec retour marchandise signée par le livreur.');
    } else {
      etapes.push('Livreur absent : incident enregistré pour suivi fournisseur.');
    }
  } else {
    const tempTxt = fiche.temperature_coeur != null ? ` Température à cœur mesurée : ${fiche.temperature_coeur}°C.` : '';
    etapes = [
      `Contrôle à la réception (visuel / température) → Non-conformité détectée : ${motifs}.`,
      `Lot isolé immédiatement pour prise de température à cœur.${tempTxt}`,
    ];
    if (fiche.livreur_present) {
      etapes.push('Livreur présent : feuille de reprise avec retour marchandise signée par le livreur.');
    } else {
      etapes.push('Livreur absent : lot isolé avec apposition de l\'étiquette À REPRENDRE en attente de retour fournisseur.');
    }
  }
  return etapes;
}

// ── Récupération de l'ID depuis l'URL ────────────────────────
const params = new URLSearchParams(window.location.search);
const ficheId = params.get('id');

if (!ficheId) {
  elMain.innerHTML = '<div style="padding:24px;text-align:center;color:#C93030;"><div style="font-size:48px;margin-bottom:12px;">⚠️</div><div>ID de fiche manquant.</div></div>';
} else {
  charger();
}

// ── Chargement et affichage ──────────────────────────────────
async function charger() {
  try {
    const fiche = await apiFetch(`/api/fiches-incident/${ficheId}`);

    // Récupérer la réception liée pour : opérateur + lot_interne
    let operateurPrenom = '—';
    let lotInterne = false;
    let dlc  = null;
    let dluo = null;
    let proprietePhoto = null;
    if (fiche.reception_id) {
      try {
        const rec = await apiFetch(`/api/receptions/${fiche.reception_id}`);
        operateurPrenom = rec.personnel_prenom || '—';
        if (rec.proprete_photo_filename) {
          proprietePhoto = `/api/receptions/${fiche.reception_id}/photo-proprete`;
        }
        // Trouver la ligne correspondante pour savoir si c'est un lot interne
        if (fiche.reception_ligne_id && rec.lignes) {
          const ligne = rec.lignes.find(l => l.id === fiche.reception_ligne_id);
          if (ligne) {
            lotInterne = !!ligne.lot_interne;
            dlc   = ligne.dlc   || null;
            dluo  = ligne.dluo  || null;
          }
        }
      } catch { /* opérateur inconnu */ }
    }

    afficherFiche(fiche, operateurPrenom, lotInterne, dlc, dluo, proprietePhoto);
  } catch (err) {
    elMain.innerHTML = `<div style="padding:24px;text-align:center;color:#C93030;"><div style="font-size:48px;margin-bottom:12px;">⚠️</div><div>Erreur : ${err.message}</div></div>`;
  }
}

// ── Helper : créer un bloc section ──────────────────────────
function creerBloc(...classes) {
  const el = document.createElement('div');
  el.className = ['pcr-bloc', ...classes].filter(Boolean).join(' ');
  return el;
}

function creerTitre(texte) {
  const el = document.createElement('div');
  el.className = 'pcr-bloc-titre';
  el.textContent = texte;
  return el;
}

function creerCorps(...extraClasses) {
  const el = document.createElement('div');
  el.className = ['pcr-bloc-corps', ...extraClasses].filter(Boolean).join(' ');
  return el;
}

function creerChampLigne(label, valeur, extraClass) {
  const el = document.createElement('div');
  el.className = 'pcr-champ-ligne';
  const span1 = document.createElement('span');
  span1.className = 'pcr-champ-label';
  span1.textContent = label;
  const span2 = document.createElement('span');
  span2.className = ['pcr-champ-val', extraClass].filter(Boolean).join(' ');
  span2.textContent = valeur;
  el.appendChild(span1);
  el.appendChild(span2);
  return el;
}

// ── Impression étiquette À RETOURNER (réimpression) ─────────
function imprimerEtiquetteRetour(fiche, operateurPrenom, dlc, dluo, lotInterne) {
  const now      = new Date();
  const dateStr  = now.toLocaleDateString('fr-FR', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });
  const heureStr = now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });

  const estCamion = fiche.action_immediate === 'refus_livraison';

  // Mode camion : pas de produit / lot / DLC, on utilise un libellé générique
  const produitNom = estCamion
    ? 'Livraison refusée — Propreté camion'
    : (fiche.produit_nom || '—');

  const motifsTxt = estCamion
    ? (fiche.description || 'Propreté du camion non satisfaisante')
    : traduireMotif(fiche.nature_probleme || '')
        + (fiche.description && fiche.description !== fiche.nature_probleme
            ? ` — ${fiche.description}` : '');

  const actionTxt = estCamion
    ? (fiche.action_corrective || 'Livraison refusée pour propreté du camion non satisfaisante')
    : (fiche.temperature_coeur != null
        ? `Contrôle à cœur effectué — NC confirmé (T° cœur : ${fiche.temperature_coeur}°C)`
        : 'Contrôle à cœur effectué — NC confirmé');

  function set(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val || '';
  }
  function setRow(rowId, cellId, labelId, val, label) {
    const row = document.getElementById(rowId);
    if (!row) return;
    if (val) {
      set(cellId, val);
      if (labelId && label) set(labelId, label);
      row.hidden = false;
    } else {
      row.hidden = true;
    }
  }

  const heureOrig = fiche.heure_incident || heureStr;
  const operateurStr = `${operateurPrenom} à ${heureOrig} (réimpression)`;
  set('print-nc-datetime', `${dateStr} — ${operateurStr}`);
  set('print-nc-produit',  produitNom);
  setRow('print-nc-fournisseur-row', 'print-nc-fournisseur', null,
         fiche.fournisseur_nom || null, null);
  setRow('print-nc-lot-row', 'print-nc-lot', 'print-nc-lot-label',
         estCamion ? null : fiche.numero_lot,
         lotInterne ? 'N° lot interne' : 'N° lot');
  setRow('print-nc-dlc-row', 'print-nc-dlc', 'print-nc-dlc-label',
         estCamion ? null : (dlc || dluo), dluo ? 'DLUO' : 'DLC');
  set('print-nc-motifs', motifsTxt || 'non-conformité');
  set('print-nc-action', actionTxt);

  window.print();
}

// ── Affichage ────────────────────────────────────────────────
function afficherFiche(fiche, operateurPrenom, lotInterne, dlc, dluo, proprietePhotoUrl) {
  elMain.innerHTML = '';

  // ── En-tête ──────────────────────────────────────────
  const docHeader = document.createElement('div');
  docHeader.className = 'pcr-doc-header';

  const ref = document.createElement('div');
  ref.className = 'pcr-ref';
  ref.textContent = 'Réf. PCR01 — Non-conformité réception';
  docHeader.appendChild(ref);

  const date = document.createElement('div');
  date.className = 'pcr-date';
  date.textContent = formatDateHeureFR(fiche.date_incident, fiche.heure_incident);
  docHeader.appendChild(date);

  const operateur = document.createElement('div');
  operateur.className = 'pcr-operateur';
  operateur.textContent = `Opérateur : ${operateurPrenom}`;
  docHeader.appendChild(operateur);

  elMain.appendChild(docHeader);

  // ── Produit non conforme ou Fournisseur(s) concerné(s) (mode camion) ──
  const estCamionFiche = fiche.action_immediate === 'refus_livraison';
  const fournNoms = (fiche.fournisseur_nom || '').split(/\s*\+\s*/).filter(Boolean);
  const titreBloc = estCamionFiche
    ? (fournNoms.length > 1 ? 'Fournisseurs concernés' : 'Fournisseur concerné')
    : 'Produit non conforme';
  const blocProduit = creerBloc('pcr-bloc-produit');
  blocProduit.appendChild(creerTitre(titreBloc));
  const corpsProduit = creerCorps();

  // Produit (sauf mode camion)
  if (!estCamionFiche && fiche.produit_nom) {
    corpsProduit.appendChild(creerChampLigne('Produit', fiche.produit_nom));
  }

  // Fournisseur(s) — toujours affiché, y compris en mode camion
  const fournLabel = (estCamionFiche && fournNoms.length > 1) ? 'Fournisseurs' : 'Fournisseur';
  const fournVal = (estCamionFiche && fournNoms.length > 1)
    ? fournNoms.join(', ')
    : (fiche.fournisseur_nom || '—');
  corpsProduit.appendChild(creerChampLigne(fournLabel, fournVal));

  // N° lot (avec label interne si applicable)
  if (fiche.numero_lot) {
    const lotLabel = lotInterne ? 'N° lot interne' : 'N° lot';
    corpsProduit.appendChild(creerChampLigne(lotLabel, fiche.numero_lot));
  }

  // DLC / DLUO
  const dlcVal   = dlc || dluo;
  const dlcLabel = dluo ? 'DLUO' : 'DLC';
  if (dlcVal) {
    corpsProduit.appendChild(creerChampLigne(dlcLabel, dlcVal));
  }

  // Non-conformité (nature_probleme traduite)
  const motifDisplay = traduireMotif(fiche.nature_probleme || '—');
  corpsProduit.appendChild(creerChampLigne('Non-conformité', motifDisplay, 'pcr-nc-badge'));

  // Action immédiate (formatée)
  const actionDisplay = formatActionImmediate(fiche);
  corpsProduit.appendChild(creerChampLigne('Action immédiate', actionDisplay, 'pcr-action-badge'));

  blocProduit.appendChild(corpsProduit);
  elMain.appendChild(blocProduit);

  // ── Étapes d'identification et de traitement ──────────
  const etapes = construireEtapes(fiche);
  if (etapes.length) {
    const blocEtapes = creerBloc('pcr-bloc-etapes');
    blocEtapes.appendChild(creerTitre('Étapes d\'identification et de traitement'));

    const liste = document.createElement('div');
    liste.className = 'pcr-etapes-liste';
    liste.setAttribute('aria-label', 'Étapes chronologiques');

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
      liste.appendChild(item);
    });

    blocEtapes.appendChild(liste);
    elMain.appendChild(blocEtapes);
  }

  // ── Photo NC propreté camion ─────────────────────────
  if (proprietePhotoUrl) {
    const blocPhoto = creerBloc();
    blocPhoto.appendChild(creerTitre('Photo de la non-conformité — propreté camion'));
    const corpsPhoto = creerCorps();
    corpsPhoto.style.textAlign = 'center';
    const img = document.createElement('img');
    img.src = proprietePhotoUrl;
    img.alt = 'Photo NC propreté camion';
    img.style.maxWidth = '100%';
    img.style.maxHeight = '400px';
    img.style.borderRadius = '8px';
    img.style.cursor = 'zoom-in';
    img.addEventListener('click', () => {
      window.open(proprietePhotoUrl, '_blank');
    });
    corpsPhoto.appendChild(img);
    blocPhoto.appendChild(corpsPhoto);
    elMain.appendChild(blocPhoto);
  }

  // ── Livreur ───────────────────────────────────────────
  const blocLivreur = creerBloc();
  blocLivreur.appendChild(creerTitre('Livreur'));
  const corpsLivreur = creerCorps();
  corpsLivreur.textContent = fiche.livreur_present ? '✓ Présent' : '✗ Absent';
  corpsLivreur.style.fontSize = '16px';
  blocLivreur.appendChild(corpsLivreur);
  elMain.appendChild(blocLivreur);

  // ── Réimpression étiquette À RETOURNER ───────────────
  {
    const estCamion = fiche.action_immediate === 'refus_livraison';
    const blocEtiq = creerBloc();
    blocEtiq.appendChild(creerTitre('Étiquette À RETOURNER'));
    const corpsEtiq = creerCorps();
    corpsEtiq.style.textAlign = 'center';

    const labelBtn = estCamion ? 'Camion' : (fiche.produit_nom || 'produit');
    const btnReimp = document.createElement('button');
    btnReimp.type = 'button';
    btnReimp.className = 'pcr-etiq-reprise-btn';
    btnReimp.innerHTML = `🖨️ Réimprimer l'étiquette — ${labelBtn}`;
    btnReimp.addEventListener('click', () => {
      imprimerEtiquetteRetour(fiche, operateurPrenom, dlc, dluo, lotInterne);
    });
    corpsEtiq.appendChild(btnReimp);
    blocEtiq.appendChild(corpsEtiq);
    elMain.appendChild(blocEtiq);
  }

  // ── Action corrective ────────────────────────────────
  const blocCorrec = creerBloc('pcr-bloc-corrective');
  blocCorrec.appendChild(creerTitre('Action corrective'));
  const corpsCorrec = creerCorps();
  corpsCorrec.style.whiteSpace = 'pre-wrap';
  corpsCorrec.style.wordWrap = 'break-word';
  corpsCorrec.textContent = fiche.action_corrective || '(Non remplie)';
  blocCorrec.appendChild(corpsCorrec);
  elMain.appendChild(blocCorrec);

  // ── Signature ────────────────────────────────────────
  if (fiche.signature_livreur_filename) {
    const blocSig = creerBloc();
    blocSig.appendChild(creerTitre('Signature du livreur'));
    const corpsSig = creerCorps();
    corpsSig.style.textAlign = 'center';
    const img = document.createElement('img');
    img.src = `/api/fiches-incident/${ficheId}/signature`;
    img.alt = 'Signature livreur';
    img.style.maxWidth = '300px';
    img.style.maxHeight = '150px';
    corpsSig.appendChild(img);
    blocSig.appendChild(corpsSig);
    elMain.appendChild(blocSig);
  }

  // ── Statut ───────────────────────────────────────────
  const blocStatut = creerBloc();
  blocStatut.appendChild(creerTitre('Statut'));
  const corpsStatut = creerCorps();
  corpsStatut.innerHTML = fiche.statut === 'fermee'
    ? '✓ <strong>Fiche fermée</strong>'
    : '🔄 <strong>Fiche ouverte</strong>';
  blocStatut.appendChild(corpsStatut);
  elMain.appendChild(blocStatut);

  // ── Commentaire ──────────────────────────────────────
  if (fiche.commentaire) {
    const blocCmt = creerBloc();
    blocCmt.appendChild(creerTitre('Commentaire'));
    const corpsCmt = creerCorps();
    corpsCmt.style.whiteSpace = 'pre-wrap';
    corpsCmt.style.wordWrap = 'break-word';
    corpsCmt.textContent = fiche.commentaire;
    blocCmt.appendChild(corpsCmt);
    elMain.appendChild(blocCmt);
  }
}

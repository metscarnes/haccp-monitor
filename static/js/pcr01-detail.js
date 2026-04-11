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
      'Livraison refusée.',
    ];
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
    if (fiche.reception_id) {
      try {
        const rec = await apiFetch(`/api/receptions/${fiche.reception_id}`);
        operateurPrenom = rec.personnel_prenom || '—';
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

    afficherFiche(fiche, operateurPrenom, lotInterne, dlc, dluo);
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

// ── Affichage ────────────────────────────────────────────────
function afficherFiche(fiche, operateurPrenom, lotInterne, dlc, dluo) {
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

  // ── Produit non conforme ──────────────────────────────
  const blocProduit = creerBloc('pcr-bloc-produit');
  blocProduit.appendChild(creerTitre('Produit non conforme'));
  const corpsProduit = creerCorps();

  // Produit
  if (fiche.produit_nom) {
    corpsProduit.appendChild(creerChampLigne('Produit', fiche.produit_nom));
  }

  // Fournisseur
  const fourn = fiche.fournisseur_nom || '—';
  corpsProduit.appendChild(creerChampLigne('Fournisseur', fourn));

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

  // ── Livreur ───────────────────────────────────────────
  const blocLivreur = creerBloc();
  blocLivreur.appendChild(creerTitre('Livreur'));
  const corpsLivreur = creerCorps();
  corpsLivreur.textContent = fiche.livreur_present ? '✓ Présent' : '✗ Absent';
  corpsLivreur.style.fontSize = '16px';
  blocLivreur.appendChild(corpsLivreur);
  elMain.appendChild(blocLivreur);

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

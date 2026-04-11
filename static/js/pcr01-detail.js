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

// ── Formatage ───────────────────────────────────────────────
function formatDateFR(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
  } catch { return isoStr; }
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
    afficherFiche(fiche);
  } catch (err) {
    elMain.innerHTML = `<div style="padding:24px;text-align:center;color:#C93030;"><div style="font-size:48px;margin-bottom:12px;">⚠️</div><div>Erreur : ${err.message}</div></div>`;
  }
}

function afficherFiche(fiche) {
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
  date.textContent = fiche.date_incident ? formatDateFR(fiche.date_incident) : '—';
  docHeader.appendChild(date);

  const operateur = document.createElement('div');
  operateur.className = 'pcr-operateur';
  operateur.innerHTML = `Opérateur : ${fiche.produit_id ? '<em>Voir détail ci-dessous</em>' : '—'}`;
  docHeader.appendChild(operateur);

  elMain.appendChild(docHeader);

  // ── Produit non conforme ──────────────────────────────
  const blocProduit = document.createElement('div');
  blocProduit.className = 'pcr-bloc pcr-bloc-produit';

  const titProduit = document.createElement('div');
  titProduit.className = 'pcr-bloc-titre';
  titProduit.textContent = 'Produit non conforme';
  blocProduit.appendChild(titProduit);

  const corpsProduit = document.createElement('div');
  corpsProduit.className = 'pcr-bloc-corps';

  // Champs produit
  const champProduit = document.createElement('div');
  champProduit.className = 'pcr-champ-ligne';
  champProduit.innerHTML = `
    <span class="pcr-champ-label">Produit</span>
    <span class="pcr-champ-val">${fiche.produit_nom || '—'}</span>
  `;
  corpsProduit.appendChild(champProduit);

  const champFournisseur = document.createElement('div');
  champFournisseur.className = 'pcr-champ-ligne';
  champFournisseur.innerHTML = `
    <span class="pcr-champ-label">Fournisseur</span>
    <span class="pcr-champ-val">${fiche.fournisseur_nom || '—'}</span>
  `;
  corpsProduit.appendChild(champFournisseur);

  const champLot = document.createElement('div');
  champLot.className = 'pcr-champ-ligne';
  champLot.innerHTML = `
    <span class="pcr-champ-label">N° lot</span>
    <span class="pcr-champ-val">${fiche.numero_lot || '—'}</span>
  `;
  corpsProduit.appendChild(champLot);

  const champMotif = document.createElement('div');
  champMotif.className = 'pcr-champ-ligne';
  champMotif.innerHTML = `
    <span class="pcr-champ-label">Non-conformité</span>
    <span class="pcr-champ-val pcr-nc-badge">${fiche.nature_probleme || '—'}</span>
  `;
  corpsProduit.appendChild(champMotif);

  const champAction = document.createElement('div');
  champAction.className = 'pcr-champ-ligne';
  champAction.innerHTML = `
    <span class="pcr-champ-label">Action immédiate</span>
    <span class="pcr-champ-val pcr-action-badge">${fiche.action_immediate || '—'}</span>
  `;
  corpsProduit.appendChild(champAction);

  blocProduit.appendChild(corpsProduit);
  elMain.appendChild(blocProduit);

  // ── Étapes (simple affichage du texte description) ────
  if (fiche.description) {
    const blocEtapes = document.createElement('div');
    blocEtapes.className = 'pcr-bloc pcr-bloc-etapes';

    const titEtapes = document.createElement('div');
    titEtapes.className = 'pcr-bloc-titre';
    titEtapes.textContent = 'Étapes d\'identification et de traitement';
    blocEtapes.appendChild(titEtapes);

    const contenuEtapes = document.createElement('div');
    contenuEtapes.className = 'pcr-bloc-corps';
    contenuEtapes.style.whiteSpace = 'pre-wrap';
    contenuEtapes.style.wordWrap = 'break-word';
    contenuEtapes.textContent = fiche.description;
    blocEtapes.appendChild(contenuEtapes);

    elMain.appendChild(blocEtapes);
  }

  // ── Livreur présent ──────────────────────────────────
  const blocLivreur = document.createElement('div');
  blocLivreur.className = 'pcr-bloc';

  const titLivreur = document.createElement('div');
  titLivreur.className = 'pcr-bloc-titre';
  titLivreur.textContent = 'Livreur';
  blocLivreur.appendChild(titLivreur);

  const corpsLivreur = document.createElement('div');
  corpsLivreur.className = 'pcr-bloc-corps';
  corpsLivreur.textContent = fiche.livreur_present ? '✓ Présent' : '✗ Absent';
  corpsLivreur.style.fontSize = '16px';
  blocLivreur.appendChild(corpsLivreur);

  elMain.appendChild(blocLivreur);

  // ── Action corrective ────────────────────────────────
  const blocCorrec = document.createElement('div');
  blocCorrec.className = 'pcr-bloc pcr-bloc-corrective';

  const titCorrec = document.createElement('div');
  titCorrec.className = 'pcr-bloc-titre';
  titCorrec.textContent = 'Action corrective';
  blocCorrec.appendChild(titCorrec);

  const corpsCorrec = document.createElement('div');
  corpsCorrec.className = 'pcr-bloc-corps';
  corpsCorrec.style.whiteSpace = 'pre-wrap';
  corpsCorrec.style.wordWrap = 'break-word';
  corpsCorrec.textContent = fiche.action_corrective || '(Non remplie)';
  blocCorrec.appendChild(corpsCorrec);

  elMain.appendChild(blocCorrec);

  // ── Signature ────────────────────────────────────────
  if (fiche.signature_livreur_filename) {
    const blocSig = document.createElement('div');
    blocSig.className = 'pcr-bloc';

    const titSig = document.createElement('div');
    titSig.className = 'pcr-bloc-titre';
    titSig.textContent = 'Signature du livreur';
    blocSig.appendChild(titSig);

    const corpsSig = document.createElement('div');
    corpsSig.className = 'pcr-bloc-corps';
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
  const blocStatut = document.createElement('div');
  blocStatut.className = 'pcr-bloc';

  const titStatut = document.createElement('div');
  titStatut.className = 'pcr-bloc-titre';
  titStatut.textContent = 'Statut';
  blocStatut.appendChild(titStatut);

  const corpsStatut = document.createElement('div');
  corpsStatut.className = 'pcr-bloc-corps';
  corpsStatut.innerHTML = fiche.statut === 'fermee'
    ? '✓ <strong>Fiche fermée</strong>'
    : '🔄 <strong>Fiche ouverte</strong>';
  blocStatut.appendChild(corpsStatut);

  elMain.appendChild(blocStatut);

  // ── Commentaire optionnel ────────────────────────────
  if (fiche.commentaire) {
    const blocCmt = document.createElement('div');
    blocCmt.className = 'pcr-bloc';

    const titCmt = document.createElement('div');
    titCmt.className = 'pcr-bloc-titre';
    titCmt.textContent = 'Commentaire';
    blocCmt.appendChild(titCmt);

    const corpsCmt = document.createElement('div');
    corpsCmt.className = 'pcr-bloc-corps';
    corpsCmt.style.whiteSpace = 'pre-wrap';
    corpsCmt.style.wordWrap = 'break-word';
    corpsCmt.textContent = fiche.commentaire;
    blocCmt.appendChild(corpsCmt);

    elMain.appendChild(blocCmt);
  }
}

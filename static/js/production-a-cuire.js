'use strict';
/* ============================================================
   production-a-cuire.js — Lots "suivi cuisson auto" en attente
   (produits reçus déjà préparés : Lasagne, Gratin dauphinois,
   Parmentier de canard…). Un clic sur une carte ouvre le détail
   (produit réceptionné vs produit fini) avec deux actions :
   cuisiner (pousse vers le wizard Cuisson, cf. sessionStorage /
   appliquerPrefill dans cuisson.js) ou exclure (retire le lot de
   la liste sans toucher au catalogue ni au stock — réversible
   depuis la modale "Lots exclus").
   ============================================================ */

const elHorloge  = document.getElementById('pac-horloge');
const elListe    = document.getElementById('pac-liste');
const elMessage  = document.getElementById('pac-message');
const elMsgIcone = document.getElementById('pac-message-icone');
const elMsgTexte = document.getElementById('pac-message-texte');

const elBtnExclusions   = document.getElementById('pac-btn-exclusions');
const elModalExclusions = document.getElementById('pac-modal-exclusions');
const elExclusionsFermer = document.getElementById('pac-exclusions-fermer');
const elExclusionsListe  = document.getElementById('pac-exclusions-liste');

const elModalDetail   = document.getElementById('pac-modal-detail');
const elDetailFermer  = document.getElementById('pac-detail-fermer');
const elDetailTitre   = document.getElementById('pac-detail-titre');
const elDetailArticle = document.getElementById('pac-detail-article');
const elDetailFinal   = document.getElementById('pac-detail-produit-final');
const elDetailLot     = document.getElementById('pac-detail-lot');
const elDetailDlc     = document.getElementById('pac-detail-dlc');
const elDetailReception = document.getElementById('pac-detail-reception');
const elDetailFournisseur = document.getElementById('pac-detail-fournisseur');
const elDetailExclure  = document.getElementById('pac-detail-exclure');
const elDetailCuisiner = document.getElementById('pac-detail-cuisiner');

let lotsCourants = [];
let lotSelectionne = null;

// ── Horloge ────────────────────────────────────────────────
function majHorloge() {
  if (!elHorloge) return;
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();

// ── Inactivité 5 min → retour hub ───────────────────────────
let timerInactivite;
function resetInactivite() {
  clearTimeout(timerInactivite);
  timerInactivite = setTimeout(() => { window.location.href = '/hub.html'; }, 5 * 60 * 1000);
}
document.addEventListener('click',      resetInactivite, true);
document.addEventListener('touchstart', resetInactivite, { passive: true, capture: true });
resetInactivite();

// ── Fetch helper ───────────────────────────────────────────
async function apiFetch(url, options) {
  const res = await fetch(url, { cache: 'no-store', ...options });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* noop */ }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

function escHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function formatDate(iso) {
  if (!iso) return '—';
  const [a, m, j] = iso.slice(0, 10).split('-');
  return `${j}/${m}/${a}`;
}

// ── Rendu liste principale ───────────────────────────────────
function rendre(lots) {
  lotsCourants = lots;
  if (!lots.length) {
    elListe.hidden = true;
    elMessage.hidden = false;
    elMsgIcone.textContent = '✓';
    elMsgTexte.textContent = 'Rien à cuire pour le moment.';
    return;
  }
  elMessage.hidden = true;
  elListe.hidden = false;
  elListe.innerHTML = lots.map((lot, i) => `
    <div class="card pac-carte" role="listitem" data-index="${i}" tabindex="0">
      <div class="pac-carte-titre">${escHtml(lot.produit_nom)}</div>
      <div class="pac-carte-sous">
        Lot <b>${escHtml(lot.numero_lot || '—')}</b> ·
        DLC <b>${formatDate(lot.dlc)}</b> ·
        reçu le ${formatDate(lot.date_reception)}
        ${lot.fournisseur_nom ? ` · ${escHtml(lot.fournisseur_nom)}` : ''}
      </div>
    </div>
  `).join('');

  elListe.querySelectorAll('.pac-carte').forEach((carte) => {
    const ouvrir = () => ouvrirDetail(lotsCourants[Number(carte.dataset.index)]);
    carte.addEventListener('click', ouvrir);
    carte.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ouvrir(); }
    });
  });
}

// ── Modale détail ────────────────────────────────────────────
function ouvrirDetail(lot) {
  lotSelectionne = lot;
  elDetailTitre.textContent = lot.produit_nom || '—';
  elDetailArticle.textContent = lot.article_designation
    ? `${lot.article_designation}${lot.article_code ? ` (${lot.article_code})` : ''}`
    : '—';
  elDetailFinal.textContent = lot.produit_nom || '—';
  elDetailLot.textContent = lot.numero_lot || '—';
  elDetailDlc.textContent = formatDate(lot.dlc);
  elDetailReception.textContent = formatDate(lot.date_reception);
  elDetailFournisseur.textContent = lot.fournisseur_nom || '—';
  elModalDetail.hidden = false;
}

function fermerDetail() {
  elModalDetail.hidden = true;
  lotSelectionne = null;
}

elDetailFermer.addEventListener('click', fermerDetail);
elModalDetail.addEventListener('click', (e) => { if (e.target === elModalDetail) fermerDetail(); });

elDetailCuisiner.addEventListener('click', () => {
  if (lotSelectionne) envoyerEnCuisson(lotSelectionne);
});

elDetailExclure.addEventListener('click', async () => {
  if (!lotSelectionne) return;
  const confirmation = window.confirm(
    `Exclure ce lot de la liste « À cuire » ?\n\n${lotSelectionne.produit_nom}` +
    `${lotSelectionne.numero_lot ? ` · Lot ${lotSelectionne.numero_lot}` : ''}\n\n` +
    `Il restera visible dans « Voir les exclusions » et pourra être réintégré.`
  );
  if (!confirmation) return;
  const motif = window.prompt('Motif de l\'exclusion (optionnel) :', '') || null;
  try {
    await apiFetch(`/api/cuisson/a-traiter/${lotSelectionne.reception_ligne_id}/exclure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ motif }),
    });
    fermerDetail();
    charger();
  } catch (e) {
    window.alert(`Erreur lors de l'exclusion : ${e.message}`);
  }
});

function envoyerEnCuisson(lot) {
  sessionStorage.setItem('cuisson_prefill', JSON.stringify({
    operateur_id:     null,
    operateur_prenom: null,
    // Le lot vient du catalogue ACHATS (réception) — catalogue_fournisseur_id
    // est l'identifiant fiable pour retrouver la tuile (cf. cuisson.js
    // appliquerPrefill). produit_id (legacy) est quasi toujours vide.
    catalogue_fournisseur_id: lot.catalogue_fournisseur_id,
    catalogue_vente_id:       lot.catalogue_vente_id ?? null,
    produit_id:       lot.produit_id ?? null,
    produit_nom:      lot.produit_nom,
  }));
  window.location.href = '/cuisson.html';
}

// ── Modale liste d'exclusion ─────────────────────────────────
function rendreExclusions(lots) {
  if (!lots.length) {
    elExclusionsListe.innerHTML = '<div class="pac-vide-inline">Aucun lot exclu.</div>';
    return;
  }
  elExclusionsListe.innerHTML = lots.map((lot, i) => `
    <div class="card pac-exclusion-carte">
      <div class="pac-carte-titre">${escHtml(lot.produit_nom)}</div>
      <div class="pac-carte-sous">
        Réceptionné : <b>${escHtml(lot.article_designation || '—')}</b> ·
        Lot <b>${escHtml(lot.numero_lot || '—')}</b> ·
        DLC ${formatDate(lot.dlc)}
        ${lot.fournisseur_nom ? ` · ${escHtml(lot.fournisseur_nom)}` : ''}
      </div>
      ${lot.motif ? `<div class="pac-carte-sous">Motif : ${escHtml(lot.motif)}</div>` : ''}
      <button type="button" class="btn btn-outline" data-index="${i}">↩ Réintégrer</button>
    </div>
  `).join('');

  elExclusionsListe.querySelectorAll('button[data-index]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const lot = lots[Number(btn.dataset.index)];
      try {
        await apiFetch(`/api/cuisson/a-traiter/${lot.reception_ligne_id}/reintegrer`, { method: 'POST' });
        chargerExclusions();
        charger();
      } catch (e) {
        window.alert(`Erreur lors de la réintégration : ${e.message}`);
      }
    });
  });
}

async function chargerExclusions() {
  elExclusionsListe.innerHTML = '<div class="pac-vide-inline">Chargement…</div>';
  try {
    const lots = await apiFetch('/api/cuisson/a-traiter/exclusions');
    rendreExclusions(lots);
  } catch (e) {
    elExclusionsListe.innerHTML = `<div class="pac-vide-inline">Erreur : ${escHtml(e.message)}</div>`;
  }
}

elBtnExclusions.addEventListener('click', () => {
  elModalExclusions.hidden = false;
  chargerExclusions();
});
elExclusionsFermer.addEventListener('click', () => { elModalExclusions.hidden = true; });
elModalExclusions.addEventListener('click', (e) => { if (e.target === elModalExclusions) elModalExclusions.hidden = true; });

// ── Chargement ───────────────────────────────────────────────
async function charger() {
  elMessage.hidden = false;
  elMsgIcone.textContent = '⏳';
  elMsgTexte.textContent = 'Chargement…';
  try {
    const lots = await apiFetch('/api/cuisson/a-traiter');
    rendre(lots);
  } catch (e) {
    elListe.hidden = true;
    elMessage.hidden = false;
    elMsgIcone.textContent = '⚠';
    elMsgTexte.textContent = `Erreur : ${e.message}`;
  }
}

charger();

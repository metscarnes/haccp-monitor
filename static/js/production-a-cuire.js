'use strict';
/* ============================================================
   production-a-cuire.js — Lots "suivi cuisson auto" en attente
   (produits reçus déjà préparés : Lasagne, Gratin dauphinois,
   Parmentier de canard…). Chaque carte pousse directement vers
   le wizard Cuisson, pré-rempli, via le même mécanisme
   sessionStorage que le bouton "Remettre en cuisson" du module
   Refroidissement (cf. static/js/cuisson.js → appliquerPrefill).
   ============================================================ */

const elHorloge  = document.getElementById('pac-horloge');
const elListe    = document.getElementById('pac-liste');
const elMessage  = document.getElementById('pac-message');
const elMsgIcone = document.getElementById('pac-message-icone');
const elMsgTexte = document.getElementById('pac-message-texte');

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
async function apiFetch(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* noop */ }
    throw new Error(detail);
  }
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

// ── Rendu ────────────────────────────────────────────────────
function rendre(lots) {
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
    <div class="card pac-carte" role="listitem">
      <div class="pac-carte-titre">${escHtml(lot.produit_nom)}</div>
      <div class="pac-carte-sous">
        Lot <b>${escHtml(lot.numero_lot || '—')}</b> ·
        DLC <b>${formatDate(lot.dlc)}</b> ·
        reçu le ${formatDate(lot.date_reception)}
        ${lot.fournisseur_nom ? ` · ${escHtml(lot.fournisseur_nom)}` : ''}
      </div>
      <button type="button" class="btn btn-primary" data-index="${i}">🔥 Cuisiner ce lot</button>
    </div>
  `).join('');

  elListe.querySelectorAll('button[data-index]').forEach((btn) => {
    btn.addEventListener('click', () => envoyerEnCuisson(lots[Number(btn.dataset.index)]));
  });
}

function envoyerEnCuisson(lot) {
  sessionStorage.setItem('cuisson_prefill', JSON.stringify({
    operateur_id:     null,
    operateur_prenom: null,
    produit_id:       lot.produit_id,
    produit_nom:      lot.produit_nom,
  }));
  window.location.href = '/cuisson.html';
}

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

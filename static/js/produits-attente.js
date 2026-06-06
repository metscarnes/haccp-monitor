'use strict';
/* ============================================================
   produits-attente.js — Complétion des produits en attente
   de traçabilité (lot/DLC manquant à la réception).

   Un produit reste hors stock tant que ses infos ne sont pas
   complétées. Cette page est ouverte depuis la tâche HACCP
   non-masquable du Hub.
   ============================================================ */

// ── Références DOM ─────────────────────────────────────────
const elHorloge   = document.getElementById('pa-horloge');
const elBtnRetour = document.getElementById('pa-btn-retour');
const elCompteur  = document.getElementById('pa-compteur');
const elListe     = document.getElementById('pa-liste');
const elMessage   = document.getElementById('pa-message');
const elMsgIcone  = document.getElementById('pa-message-icone');
const elMsgTexte  = document.getElementById('pa-message-texte');

// ── Horloge ────────────────────────────────────────────────
function majHorloge() {
  if (!elHorloge) return;
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();

// ── Retour & inactivité ────────────────────────────────────
if (elBtnRetour) {
  elBtnRetour.addEventListener('click', () => { window.location.href = '/hub.html'; });
}
let timerInactivite;
function resetInactivite() {
  clearTimeout(timerInactivite);
  timerInactivite = setTimeout(() => { window.location.href = '/hub.html'; }, 5 * 60 * 1000);
}
document.addEventListener('click',      resetInactivite, true);
document.addEventListener('touchstart', resetInactivite, { passive: true, capture: true });
document.addEventListener('input',      resetInactivite, true);
resetInactivite();

// ── Fetch helper ───────────────────────────────────────────
async function apiFetch(url, opts) {
  const res = await fetch(url, { cache: 'no-store', ...(opts || {}) });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} — ${txt || url}`);
  }
  return res.json();
}

// ── Utilitaires ────────────────────────────────────────────
function escHtml(s) {
  if (s === null || s === undefined) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function fmtDateFR(iso) {
  if (!iso) return '—';
  return String(iso).slice(0, 10).split('-').reverse().join('/');
}
function libelleMotif(motif) {
  if (motif === 'lot_dlc') return 'N° de lot + date manquants';
  if (motif === 'lot')     return 'N° de lot manquant';
  if (motif === 'dlc')     return 'Date (DLC) manquante';
  return 'À compléter';
}
// Le produit attend-il une date d'abattage plutôt qu'une DLC ?
function attendDateAbattage(ligne) {
  return ligne.dlc_type === 'date_abattage';
}

function afficherMessage(icone, texte) {
  elMessage.hidden = false;
  elMsgIcone.textContent = icone;
  elMsgTexte.textContent = texte;
}
function masquerMessage() { elMessage.hidden = true; }

// ── Chargement de la liste ─────────────────────────────────
async function charger() {
  afficherMessage('⏳', 'Chargement…');
  elListe.innerHTML = '';
  let data;
  try {
    data = await apiFetch('/api/attente/lignes');
  } catch (e) {
    afficherMessage('⚠️', 'Erreur de chargement. Réessayez.');
    return;
  }

  const lignes = data.lignes || [];
  elCompteur.textContent = lignes.length
    ? `${lignes.length} produit(s) à compléter`
    : '';

  if (!lignes.length) {
    afficherMessage('✅', 'Aucun produit en attente — tout est tracé !');
    return;
  }
  masquerMessage();
  lignes.forEach(rendreCarte);
}

// ── Carte d'un produit en attente ──────────────────────────
function rendreCarte(ligne) {
  const carte = document.createElement('div');
  carte.className = 'pa-carte';
  carte.dataset.ligneId = ligne.ligne_id;

  const dateAbattage = attendDateAbattage(ligne);

  // Bloc identité produit + réception
  const sousParts = [];
  if (ligne.fournisseur_nom) sousParts.push(escHtml(ligne.fournisseur_nom));
  sousParts.push(`Reçu le ${fmtDateFR(ligne.date_reception)}`);
  if (ligne.poids_kg) sousParts.push(`${ligne.poids_kg} kg`);

  carte.innerHTML = `
    <div class="pa-carte-titre">${escHtml(ligne.produit_nom || 'Produit')}</div>
    <div class="pa-carte-sous">${sousParts.join(' · ')}</div>
    <div class="pa-carte-motif">${escHtml(libelleMotif(ligne.attente_motif))}</div>

    <div class="pa-champ">
      <label class="pa-champ-label">N° de lot</label>
      <input type="text" class="pa-input" data-field="numero_lot"
             value="${escHtml(ligne.numero_lot || '')}"
             placeholder="N° de lot du bon de livraison…">
    </div>

    <div class="pa-champ">
      <label class="pa-champ-label">${dateAbattage ? "Date d'abattage" : 'DLC'}</label>
      <input type="date" class="pa-input"
             data-field="${dateAbattage ? 'date_abattage' : 'dlc'}"
             value="${escHtml(dateAbattage ? (ligne.date_abattage || '') : (ligne.dlc || ''))}">
    </div>

    <button class="pa-btn-valider" type="button">✓ Valider et entrer en stock</button>
    <div class="pa-erreur" hidden></div>
  `;

  const btn    = carte.querySelector('.pa-btn-valider');
  const erreur = carte.querySelector('.pa-erreur');
  btn.addEventListener('click', () => valider(carte, ligne, btn, erreur));

  elListe.appendChild(carte);
}

// ── Validation / complétion ────────────────────────────────
async function valider(carte, ligne, btn, erreur) {
  erreur.hidden = true;
  const inputs = carte.querySelectorAll('.pa-input');
  const payload = {};
  inputs.forEach(inp => {
    inp.classList.remove('pa-input--invalide');
    const v = inp.value.trim();
    if (v) payload[inp.dataset.field] = v;
  });

  // Validation côté client : lot + date requis (sauf no_dlc pour la date)
  const manqueLot  = !payload.numero_lot;
  const dateAbattage = attendDateAbattage(ligne);
  const noDlc      = ligne.dlc_type === 'no_dlc';
  const manqueDate = !noDlc && !(dateAbattage ? payload.date_abattage : payload.dlc);

  if (manqueLot || manqueDate) {
    inputs.forEach(inp => {
      if ((inp.dataset.field === 'numero_lot' && manqueLot) ||
          (inp.dataset.field !== 'numero_lot' && manqueDate)) {
        inp.classList.add('pa-input--invalide');
      }
    });
    erreur.textContent = 'Renseignez le N° de lot et la date pour valider.';
    erreur.hidden = false;
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Validation…';
  try {
    const res = await apiFetch(`/api/attente/lignes/${ligne.ligne_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.statut === 'complet') {
      // Produit complété → retirer la carte, le produit entre en stock
      carte.remove();
      const restantes = elListe.querySelectorAll('.pa-carte').length;
      elCompteur.textContent = restantes ? `${restantes} produit(s) à compléter` : '';
      if (!restantes) afficherMessage('✅', 'Aucun produit en attente — tout est tracé !');
    } else {
      erreur.textContent = 'Il manque encore une information pour finaliser.';
      erreur.hidden = false;
      btn.disabled = false;
      btn.textContent = '✓ Valider et entrer en stock';
    }
  } catch (e) {
    erreur.textContent = 'Erreur lors de l’enregistrement. Réessayez.';
    erreur.hidden = false;
    btn.disabled = false;
    btn.textContent = '✓ Valider et entrer en stock';
  }
}

// ── Init ───────────────────────────────────────────────────
charger();

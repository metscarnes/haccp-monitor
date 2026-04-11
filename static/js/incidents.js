'use strict';
/* ============================================================
   incidents.js — Affichage fiches PCR01
   Au Comptoir des Lilas — Mets Carnés Holding
   ============================================================ */

// ── Références DOM ──────────────────────────────────────────
const elBtnRetour = document.getElementById('inc-btn-retour');
const elHorloge = document.getElementById('inc-horloge');
const elCompteur = document.getElementById('inc-compteur');
const elListe = document.getElementById('inc-liste');
const elMessage = document.getElementById('inc-message');

// ── Horloge ─────────────────────────────────────────────────
function majHorloge() {
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();

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
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
  } catch { return isoStr; }
}

// ── Récupération de l'ID depuis l'URL ────────────────────────
const params = new URLSearchParams(window.location.search);
const receptionId = params.get('reception_id');

if (!receptionId) {
  elMessage.innerHTML = '<div style="font-size:48px;margin-bottom:12px;">⚠️</div><div>ID de réception manquant.</div>';
} else {
  charger();
}

// ── Chargement des fiches-incident ──────────────────────────
async function charger() {
  try {
    // Endpoint GET /api/fiches-incident avec filtre reception_id
    const rows = await apiFetch(`/api/fiches-incident?reception_id=${receptionId}`);
    afficherFiches(rows);
  } catch (err) {
    elMessage.innerHTML = `<div style="font-size:48px;margin-bottom:12px;">⚠️</div><div>Erreur : ${err.message}</div>`;
  }
}

function afficherFiches(fiches) {
  elMessage.style.display = 'none';

  if (fiches.length === 0) {
    elCompteur.textContent = 'Aucune fiche PCR01';
    elListe.innerHTML = '<div style="padding:24px;text-align:center;color:#888;">Aucun incident enregistré pour cette réception.</div>';
    return;
  }

  elCompteur.textContent = fiches.length === 1
    ? '1 fiche PCR01'
    : `${fiches.length} fiches PCR01`;

  elListe.innerHTML = '';
  fiches.forEach(fiche => elListe.appendChild(creerCarte(fiche)));
}

// ── Création carte fiche incident ────────────────────────────
function creerCarte(fiche) {
  const carte = document.createElement('div');
  carte.className = 'inc-carte';
  carte.setAttribute('role', 'listitem');
  carte.style.cursor = 'pointer';

  const entete = document.createElement('div');
  entete.className = 'inc-carte-entete';

  const titre = document.createElement('div');
  titre.className = 'inc-carte-titre';
  titre.textContent = `Fiche PCR01 — ${formatDateFR(fiche.date_incident)}`;
  entete.appendChild(titre);

  const badge = document.createElement('span');
  badge.className = 'inc-badge';
  badge.textContent = fiche.statut === 'fermee' ? '✓ Fermée' : '🔄 Ouverte';
  entete.appendChild(badge);

  carte.appendChild(entete);

  // Produit
  const row1 = document.createElement('div');
  row1.className = 'inc-row';

  const chProd = document.createElement('div');
  chProd.className = 'inc-champ';
  const lblProd = document.createElement('span');
  lblProd.className = 'inc-champ-label';
  lblProd.textContent = 'Produit';
  const valProd = document.createElement('span');
  valProd.className = 'inc-champ-val';
  valProd.textContent = '(cliquer pour voir)';
  valProd.style.color = '#0066CC';
  valProd.style.fontWeight = '600';
  chProd.appendChild(lblProd);
  chProd.appendChild(valProd);
  row1.appendChild(chProd);

  // Nature problème
  const chNat = document.createElement('div');
  chNat.className = 'inc-champ';
  const lblNat = document.createElement('span');
  lblNat.className = 'inc-champ-label';
  lblNat.textContent = 'Nature';
  const valNat = document.createElement('span');
  valNat.className = 'inc-champ-val';
  valNat.textContent = fiche.nature_probleme || '—';
  chNat.appendChild(lblNat);
  chNat.appendChild(valNat);
  row1.appendChild(chNat);

  carte.appendChild(row1);

  // Action immédiate
  const row2 = document.createElement('div');
  row2.className = 'inc-row full';

  const chAct = document.createElement('div');
  chAct.className = 'inc-champ';
  const lblAct = document.createElement('span');
  lblAct.className = 'inc-champ-label';
  lblAct.textContent = 'Action immédiate';
  const valAct = document.createElement('span');
  valAct.className = 'inc-champ-val';
  valAct.textContent = fiche.action_immediate || '—';
  chAct.appendChild(lblAct);
  chAct.appendChild(valAct);
  row2.appendChild(chAct);

  carte.appendChild(row2);

  // Clic pour voir le détail
  carte.addEventListener('click', () => {
    window.location.href = `/pcr01-detail.html?id=${fiche.id}`;
  });

  return carte;
}

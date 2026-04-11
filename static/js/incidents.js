'use strict';
/* ============================================================
   incidents.js — Affichage fiches PCR01 (non-conformités)
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

// ── Chargement des incidents ────────────────────────────────
async function charger() {
  try {
    const rows = await apiFetch(`/api/non-conformites?reception_id=${receptionId}`);
    afficherIncidents(rows);
  } catch (err) {
    elMessage.innerHTML = `<div style="font-size:48px;margin-bottom:12px;">⚠️</div><div>Erreur : ${err.message}</div>`;
  }
}

function afficherIncidents(incidents) {
  elMessage.style.display = 'none';

  if (incidents.length === 0) {
    elCompteur.textContent = 'Aucune fiche PCR01';
    elListe.innerHTML = '<div style="padding:24px;text-align:center;color:#888;">Aucun incident enregistré pour cette réception.</div>';
    return;
  }

  elCompteur.textContent = incidents.length === 1
    ? '1 fiche PCR01'
    : `${incidents.length} fiches PCR01`;

  elListe.innerHTML = '';
  incidents.forEach(inc => elListe.appendChild(creerCarte(inc)));
}

// ── Création carte incident ──────────────────────────────────
function creerCarte(inc) {
  const carte = document.createElement('div');
  carte.className = 'inc-carte';
  carte.setAttribute('role', 'listitem');

  const entete = document.createElement('div');
  entete.className = 'inc-carte-entete';

  const titre = document.createElement('div');
  titre.className = 'inc-carte-titre';
  titre.textContent = `Fiche PCR01 — ${formatDateFR(inc.date_livraison || inc.created_at)}`;
  entete.appendChild(titre);

  const badge = document.createElement('span');
  badge.className = 'inc-badge';
  badge.textContent = '⚠️ Non-conformité';
  entete.appendChild(badge);

  carte.appendChild(entete);

  // Opérateur
  const row1 = document.createElement('div');
  row1.className = 'inc-row';

  const chOp = document.createElement('div');
  chOp.className = 'inc-champ';
  const lblOp = document.createElement('span');
  lblOp.className = 'inc-champ-label';
  lblOp.textContent = 'Opérateur';
  const valOp = document.createElement('span');
  valOp.className = 'inc-champ-val';
  valOp.textContent = inc.operateur || '—';
  chOp.appendChild(lblOp);
  chOp.appendChild(valOp);
  row1.appendChild(chOp);

  const chFourn = document.createElement('div');
  chFourn.className = 'inc-champ';
  const lblFourn = document.createElement('span');
  lblFourn.className = 'inc-champ-label';
  lblFourn.textContent = 'Fournisseur';
  const valFourn = document.createElement('span');
  valFourn.className = 'inc-champ-val';
  valFourn.textContent = inc.fournisseur_nom || '—';
  chFourn.appendChild(lblFourn);
  chFourn.appendChild(valFourn);
  row1.appendChild(chFourn);

  carte.appendChild(row1);

  // Produits
  const row2 = document.createElement('div');
  row2.className = 'inc-row';

  const chProd = document.createElement('div');
  chProd.className = 'inc-champ';
  const lblProd = document.createElement('span');
  lblProd.className = 'inc-champ-label';
  lblProd.textContent = 'Produits';
  const valProd = document.createElement('span');
  valProd.className = 'inc-champ-val';
  valProd.textContent = inc.produits || '—';
  chProd.appendChild(lblProd);
  chProd.appendChild(valProd);
  row2.appendChild(chProd);

  carte.appendChild(row2);

  // Nature NC
  if (inc.nature_nc) {
    const row3 = document.createElement('div');
    row3.className = 'inc-row full';

    const chNature = document.createElement('div');
    chNature.className = 'inc-champ';
    const lblNature = document.createElement('span');
    lblNature.className = 'inc-champ-label';
    lblNature.textContent = 'Nature de la non-conformité';
    const valNature = document.createElement('span');
    valNature.className = 'inc-champ-val';
    let natureStr = '—';
    if (typeof inc.nature_nc === 'string') {
      try {
        const arr = JSON.parse(inc.nature_nc);
        natureStr = Array.isArray(arr) ? arr.join(', ') : inc.nature_nc;
      } catch {
        natureStr = inc.nature_nc;
      }
    }
    valNature.textContent = natureStr;
    chNature.appendChild(lblNature);
    chNature.appendChild(valNature);
    row3.appendChild(chNature);

    carte.appendChild(row3);
  }

  // Commentaires
  if (inc.commentaires) {
    const row4 = document.createElement('div');
    row4.className = 'inc-row full';

    const chCmt = document.createElement('div');
    chCmt.className = 'inc-champ';
    const lblCmt = document.createElement('span');
    lblCmt.className = 'inc-champ-label';
    lblCmt.textContent = 'Commentaires';
    const valCmt = document.createElement('span');
    valCmt.className = 'inc-champ-val';
    valCmt.textContent = inc.commentaires;
    chCmt.appendChild(lblCmt);
    chCmt.appendChild(valCmt);
    row4.appendChild(chCmt);

    carte.appendChild(row4);
  }

  // Statut
  const row5 = document.createElement('div');
  row5.className = 'inc-row full';
  row5.style.borderTop = '1px solid #DDD';
  row5.style.marginTop = '8px';
  row5.style.paddingTop = '8px';

  const chStatut = document.createElement('div');
  chStatut.className = 'inc-champ';
  const lblStatut = document.createElement('span');
  lblStatut.className = 'inc-champ-label';
  lblStatut.textContent = 'Infos DDpp';
  const valStatut = document.createElement('span');
  valStatut.className = 'inc-champ-val';
  valStatut.textContent = inc.info_ddpp ? '✓ Signalé' : '—';
  chStatut.appendChild(lblStatut);
  chStatut.appendChild(valStatut);
  row5.appendChild(chStatut);

  carte.appendChild(row5);

  return carte;
}

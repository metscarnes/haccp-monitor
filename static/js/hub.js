'use strict';
/* ============================================================
   hub.js — Accueil Hub Phase 2 HACCP
   Au Comptoir des Lilas — Mets Carnés Holding

   Responsabilités :
   - Horloge temps réel (1 s)
   - Chargement des données depuis 4 endpoints (toutes les 30 s)
   - Mise à jour des 4 tuiles avec statut coloré
   - Bandeau d'alerte si tâches en retard
   - Retour accueil (reload) après 5 min d'inactivité
   ============================================================ */

const REFRESH_MS  = 30_000;          // actualisation des tuiles
const INACT_MS    = 5 * 60 * 1000;   // inactivité → reload

// ── Références DOM ────────────────────────────────────────────
const elHorloge          = document.getElementById('hub-horloge');
const elBandeauConnexion = document.getElementById('hub-bandeau-connexion');

// ── Horloge ───────────────────────────────────────────────────
function majHorloge() {
  const now  = new Date();
  const date = now.toLocaleDateString('fr-FR', {
    weekday: 'short', day: 'numeric', month: 'long',
  });
  const heure = now.toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
  elHorloge.textContent = `${date} — ${heure}`;
}
setInterval(majHorloge, 1000);
majHorloge();

// ── Inactivité ────────────────────────────────────────────────
let timerInact;

function resetInact() {
  clearTimeout(timerInact);
  timerInact = setTimeout(() => location.reload(), INACT_MS);
}

['touchstart', 'click', 'keydown', 'mousemove', 'scroll'].forEach(ev =>
  document.addEventListener(ev, resetInact, { passive: true })
);
resetInact();

// ── Fetch helper ──────────────────────────────────────────────
async function apiFetch(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status} — ${url}`);
  return res.json();
}

// ── Helpers d'affichage ───────────────────────────────────────

/** Dot de statut coloré en HTML */
function dot(etat) {
  return `<span class="hub-dot hub-dot--${etat}" aria-hidden="true"></span>`;
}

/**
 * Applique l'état visuel d'une tuile.
 * @param {string} idTuile  — id de l'élément <a>
 * @param {string} etat     — "ok" | "attention" | "alerte" | "erreur" | "chargement"
 * @param {string} html     — contenu HTML du statut
 */
function setTuile(idTuile, etat, html) {
  const tuile  = document.getElementById(idTuile);
  const statut = document.getElementById('statut-' + idTuile.replace('tuile-', ''));
  tuile.className  = `hub-tuile hub-tuile--${etat}`;
  statut.innerHTML = html;
}

// ── Tuile — Fabrication ───────────────────────────────────────
function afficherEtiquettes(alertes) {
  document.getElementById('tuile-etiquettes').className = 'hub-tuile hub-tuile--ok';
}

// ── Tuile — Réception ─────────────────────────────────────────
function afficherReception(receptions) {
  if (!receptions || receptions.length === 0) {
    setTuile('tuile-reception', 'chargement',
      `${dot('gris')} Aucune réception récente`
    );
    return;
  }

  const d    = receptions[0];
  const date = new Date(d.date_reception).toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'short',
  });
  const nb   = d.nb_lignes ?? '—';
  const nc   = (d.nb_nc > 0) || (d.conforme === 0);

  if (nc) {
    setTuile('tuile-reception', 'attention',
      `${dot('attention')} ${date}&ensp;·&ensp;${nb} produit${nb > 1 ? 's' : ''}&ensp;·&ensp;NC`
    );
  } else {
    setTuile('tuile-reception', 'ok',
      `${dot('ok')} ${date}&ensp;·&ensp;${nb} produit${nb > 1 ? 's' : ''}&ensp;·&ensp;OK`
    );
  }
}

// ── Chargement principal ──────────────────────────────────────
async function charger() {
  const [rDlc, rRecep] = await Promise.allSettled([
    apiFetch('/api/etiquettes/alertes-dlc'),
    apiFetch('/api/receptions?limit=1'),
  ]);

  const toutEchoue = [rDlc, rRecep]
    .every(r => r.status === 'rejected');
  elBandeauConnexion.hidden = !toutEchoue;

  if (rDlc.status === 'fulfilled') {
    afficherEtiquettes(rDlc.value);
  } else {
    document.getElementById('tuile-etiquettes').className = 'hub-tuile hub-tuile--erreur';
  }

  if (rRecep.status === 'fulfilled') {
    afficherReception(rRecep.value);
  } else {
    setTuile('tuile-reception', 'erreur', '⚠ Connexion perdue');
  }
}

// ── Popup tâches HACCP (cloche header) ────────────────────────
const elCloche       = document.getElementById('hub-cloche');
const elClocheBadge  = document.getElementById('hub-cloche-badge');
const elPopupOverlay = document.getElementById('hub-popup-overlay');
const elPopupFermer  = document.getElementById('hub-popup-fermer');
const elListeAuj     = document.getElementById('hub-popup-aujourdhui');
const elListeAVenir  = document.getElementById('hub-popup-avenir');

let popupDejaOuvert = false;   // évite la réouverture auto à chaque refresh

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function ligneTacheHtml(t) {
  const classeEtat = t.etat === 'en_retard' ? 'hub-popup-item--retard' : '';
  return `
    <li class="hub-popup-item ${classeEtat}">
      <a href="${t.url}" class="hub-popup-lien">
        <span class="hub-popup-icone" aria-hidden="true">${t.icone ?? '📋'}</span>
        <span class="hub-popup-texte">
          <span class="hub-popup-libelle">${escHtml(t.libelle)}</span>
          <span class="hub-popup-detail">${escHtml(t.detail ?? '')}</span>
        </span>
        <span class="hub-popup-fleche" aria-hidden="true">›</span>
      </a>
    </li>`;
}

function listeVideHtml(msg) {
  return `<li class="hub-popup-vide">${escHtml(msg)}</li>`;
}

function ouvrirPopup() {
  elPopupOverlay.hidden = false;
  document.body.style.overflow = 'hidden';
}

function fermerPopup() {
  elPopupOverlay.hidden = true;
  document.body.style.overflow = '';
}

elCloche.addEventListener('click', ouvrirPopup);
elPopupFermer.addEventListener('click', fermerPopup);
elPopupOverlay.addEventListener('click', (e) => {
  if (e.target === elPopupOverlay) fermerPopup();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !elPopupOverlay.hidden) fermerPopup();
});

async function chargerResumeTaches() {
  let data;
  try {
    data = await apiFetch('/api/hub/taches-resume');
  } catch {
    elCloche.hidden = true;
    return;
  }

  const auj    = data.aujourd_hui ?? [];
  const avenir = data.a_venir     ?? [];
  const total  = auj.length + avenir.length;

  // Cloche : visible uniquement s'il y a quelque chose à signaler
  elCloche.hidden = (total === 0);
  if (total > 0) {
    elClocheBadge.textContent = String(total);
    elClocheBadge.hidden = false;
    elCloche.classList.toggle('hub-btn-cloche--alerte', auj.length > 0);
  }

  // Remplissage des listes
  elListeAuj.innerHTML = auj.length
    ? auj.map(ligneTacheHtml).join('')
    : listeVideHtml('✓ Tout est à jour aujourd\'hui');

  elListeAVenir.innerHTML = avenir.length
    ? avenir.map(ligneTacheHtml).join('')
    : listeVideHtml('Aucune échéance dans les 14 prochains jours');

  // Ouverture auto au premier chargement (si non vide)
  if (!popupDejaOuvert && total > 0) {
    popupDejaOuvert = true;
    ouvrirPopup();
  }
}

// ── Init ──────────────────────────────────────────────────────
charger();
chargerResumeTaches();
setInterval(charger, REFRESH_MS);
setInterval(chargerResumeTaches, REFRESH_MS);

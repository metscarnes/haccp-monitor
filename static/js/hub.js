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
const elBandeauRetard    = document.getElementById('hub-bandeau-retard');
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

// ── Tuile — Tâches HACCP ──────────────────────────────────────
function afficherTaches(data) {
  const enRetard = data.en_retard?.length ?? 0;
  const aFaire   = data.a_faire?.length   ?? 0;
  const fait     = data.fait?.length      ?? 0;
  const badge    = document.getElementById('badge-taches');

  if (enRetard > 0) {
    badge.textContent = enRetard;
    badge.hidden = false;
    setTuile('tuile-taches', 'alerte',
      `${dot('alerte')} <strong>${enRetard} en retard</strong>&ensp;·&ensp;${aFaire} à faire`
    );
  } else if (aFaire > 0) {
    badge.hidden = true;
    setTuile('tuile-taches', 'attention',
      `${dot('attention')} ${aFaire} à faire&ensp;·&ensp;${fait} fait${fait > 1 ? 'es' : 'e'}`
    );
  } else {
    badge.hidden = true;
    setTuile('tuile-taches', 'ok',
      `${dot('ok')} Journée complète ✓`
    );
  }
}

// ── Tuile — Étiquettes DLC ────────────────────────────────────
function afficherEtiquettes(alertes) {
  if (alertes.length === 0) {
    setTuile('tuile-etiquettes', 'ok',
      `${dot('ok')} Aucune DLC proche`
    );
  } else {
    const nb = alertes.length;
    const premier = alertes[0]?.produit_nom ?? '';
    setTuile('tuile-etiquettes', 'attention',
      `${dot('attention')} <strong>${nb} DLC &lt; 2&nbsp;jours</strong>`
      + (premier ? `<br><small>${premier}${nb > 1 ? ` +${nb - 1}` : ''}</small>` : '')
    );
  }
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

// ── Tuile — Températures ──────────────────────────────────────
function afficherTemperatures(dash) {
  if (!dash?.boutique) {
    setTuile('tuile-temperatures', 'erreur', '⚠ Données indisponibles');
    return;
  }

  const sg   = dash.boutique.statut;
  const etat = sg === 'alerte' ? 'alerte' : sg === 'attention' ? 'attention' : 'ok';
  const label = sg === 'alerte' ? 'ALERTE TEMPÉRATURE'
              : sg === 'attention' ? 'Attention'
              : 'Tout OK';

  const mesures = (dash.enceintes ?? [])
    .filter(e => e.temperature_actuelle !== null)
    .slice(0, 3)
    .map(e => {
      const t   = Number(e.temperature_actuelle).toFixed(1);
      const nom = e.nom
        .replace('Chambre froide', 'CF')
        .replace('chambre froide', 'CF');
      const couleur = e.statut === 'alerte'
        ? 'style="color:var(--alerte);font-weight:700"' : '';
      return `<span ${couleur}>${nom}&nbsp;${t}°</span>`;
    })
    .join('&ensp;·&ensp;');

  setTuile('tuile-temperatures', etat,
    `${dot(etat)} ${label}`
    + (mesures ? `<br><small>${mesures}</small>` : '')
  );
}

// ── Bandeau tâches en retard ──────────────────────────────────
function majBandeauRetard(enRetard) {
  if (!enRetard || enRetard.length === 0) {
    elBandeauRetard.hidden = true;
    return;
  }

  const nb    = enRetard.length;
  const noms  = enRetard.slice(0, 2).map(t => t.libelle).join(' · ');
  const suite = nb > 2 ? ` (+${nb - 2})` : '';

  elBandeauRetard.innerHTML =
    `⚠&nbsp;<strong>${nb} tâche${nb > 1 ? 's' : ''} en retard</strong>`
    + `<span class="hub-bandeau-detail">${noms}${suite}</span>`;
  elBandeauRetard.hidden = false;
}

// Clic bandeau → page tâches
elBandeauRetard.addEventListener('click', () => {
  location.href = '/taches.html';
});

// ── Chargement principal ──────────────────────────────────────
async function charger() {
  const [rTaches, rDash, rDlc, rRecep] = await Promise.allSettled([
    apiFetch('/api/taches/today'),
    apiFetch('/api/boutiques/1/dashboard'),
    apiFetch('/api/etiquettes/alertes-dlc'),
    apiFetch('/api/receptions?limit=1'),
  ]);

  const toutEchoue = [rTaches, rDash, rDlc, rRecep]
    .every(r => r.status === 'rejected');
  elBandeauConnexion.hidden = !toutEchoue;

  if (rTaches.status === 'fulfilled') {
    afficherTaches(rTaches.value);
    majBandeauRetard(rTaches.value.en_retard ?? []);
  } else {
    setTuile('tuile-taches', 'erreur', '⚠ Connexion perdue');
    elBandeauRetard.hidden = true;
  }

  if (rDash.status === 'fulfilled') {
    afficherTemperatures(rDash.value);
  } else {
    setTuile('tuile-temperatures', 'erreur', '⚠ Connexion perdue');
  }

  if (rDlc.status === 'fulfilled') {
    afficherEtiquettes(rDlc.value);
  } else {
    setTuile('tuile-etiquettes', 'erreur', '⚠ Connexion perdue');
  }

  if (rRecep.status === 'fulfilled') {
    afficherReception(rRecep.value);
  } else {
    setTuile('tuile-reception', 'erreur', '⚠ Connexion perdue');
  }
}

// ── Init ──────────────────────────────────────────────────────
charger();
setInterval(charger, REFRESH_MS);

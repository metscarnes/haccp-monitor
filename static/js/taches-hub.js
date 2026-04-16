'use strict';
/* ============================================================
   taches-hub.js — Page intermédiaire Tâches HACCP
   Affiche les sous-modules sous forme de tuiles avec statut.
   ============================================================ */

const REFRESH_MS = 30_000;

const elHorloge = document.getElementById('hub-horloge');

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

// ── Fetch helper ──────────────────────────────────────────────
async function apiFetch(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Helpers tuile ─────────────────────────────────────────────
function dot(etat) {
  return `<span class="hub-dot hub-dot--${etat}" aria-hidden="true"></span>`;
}

function setTuile(idTuile, etat, html) {
  const tuile  = document.getElementById(idTuile);
  const statut = document.getElementById('statut-' + idTuile.replace('tuile-', ''));
  if (!tuile || !statut) return;
  tuile.className  = `hub-tuile hub-tuile--${etat}`;
  statut.innerHTML = html;
}

// ── Tuile — Contrôles journaliers ─────────────────────────────
function afficherControles(data) {
  const enRetard = data.en_retard?.length ?? 0;
  const aFaire   = data.a_faire?.length   ?? 0;
  const fait     = data.fait?.length      ?? 0;
  const badge    = document.getElementById('badge-controles');

  if (enRetard > 0) {
    badge.textContent = enRetard;
    badge.hidden = false;
    setTuile('tuile-controles', 'alerte',
      `${dot('alerte')} <strong>${enRetard} en retard</strong>&ensp;·&ensp;${aFaire} à faire`
    );
  } else if (aFaire > 0) {
    badge.hidden = true;
    setTuile('tuile-controles', 'attention',
      `${dot('attention')} ${aFaire} à faire&ensp;·&ensp;${fait} fait${fait > 1 ? 'es' : 'e'}`
    );
  } else {
    badge.hidden = true;
    setTuile('tuile-controles', 'ok',
      `${dot('ok')} Journée complète ✓`
    );
  }
}

// ── Chargement ────────────────────────────────────────────────
async function charger() {
  try {
    const data = await apiFetch('/api/taches/today');
    afficherControles(data);
  } catch {
    setTuile('tuile-controles', 'erreur', '⚠ Connexion perdue');
  }
}

charger();
setInterval(charger, REFRESH_MS);

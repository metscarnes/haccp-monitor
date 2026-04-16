'use strict';
/* ============================================================
   taches-hub.js — Page intermédiaire Tâches HACCP
   Affiche le statut de validation du nettoyage du jour.
   ============================================================ */

const REFRESH_MS = 60_000;

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

function setTuile(id, etat, html) {
  const tuile  = document.getElementById(id);
  const statut = document.getElementById('statut-' + id.replace('tuile-', ''));
  if (!tuile || !statut) return;
  tuile.className  = `hub-tuile hub-tuile--${etat}`;
  statut.innerHTML = html;
}

// ── Tuile — Nettoyage ─────────────────────────────────────────
async function charger() {
  try {
    const data = await apiFetch('/api/nettoyage/status');
    if (data.valide) {
      const par = data.operateur ? ` — ${data.operateur}` : '';
      setTuile('tuile-nettoyage', 'ok',
        `${dot('ok')} Validé aujourd'hui${par}`
      );
    } else {
      setTuile('tuile-nettoyage', 'alerte',
        `${dot('alerte')} <strong>Non validé aujourd'hui</strong>`
      );
    }
  } catch {
    setTuile('tuile-nettoyage', 'erreur', '⚠ Connexion perdue');
  }
}

charger();
setInterval(charger, REFRESH_MS);

'use strict';
/* ============================================================
   taches-hub.js — Page intermédiaire Tâches HACCP
   Sous-modules : Nettoyage, Étalonnage thermomètres (EET01)
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
async function chargerNettoyage() {
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

// ── Tuile — Étalonnage thermomètres ───────────────────────────
async function chargerEtalonnage() {
  try {
    const data = await apiFetch('/api/etalonnage/status');

    if (data.jamais_fait) {
      setTuile('tuile-etalonnage', 'alerte',
        `${dot('alerte')} <strong>Jamais réalisé</strong><br><small>EET01 requis</small>`
      );
      return;
    }

    if (data.en_retard) {
      const jours = Math.abs(data.jours_restants);
      setTuile('tuile-etalonnage', 'alerte',
        `${dot('alerte')} <strong>En retard de ${jours} j</strong>`
        + `<br><small>Dernier : ${formatDate(data.dernier_date)}</small>`
      );
      return;
    }

    // À jour — afficher le prochain
    const j = data.jours_restants;
    const etat = j <= 14 ? 'attention' : 'ok';
    const dotEtat = j <= 14 ? 'attention' : 'ok';
    setTuile('tuile-etalonnage', etat,
      `${dot(dotEtat)} Prochain dans ${j} j`
      + `<br><small>Dernier : ${formatDate(data.dernier_date)}</small>`
    );
  } catch {
    setTuile('tuile-etalonnage', 'erreur', '⚠ Connexion perdue');
  }
}

function formatDate(iso) {
  if (!iso) return '—';
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

// ── Chargement ────────────────────────────────────────────────
async function charger() {
  await Promise.allSettled([
    chargerNettoyage(),
    chargerEtalonnage(),
  ]);
}

charger();
setInterval(charger, REFRESH_MS);

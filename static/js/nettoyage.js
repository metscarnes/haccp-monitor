'use strict';
/* ============================================================
   nettoyage.js — Checklist Plan de Nettoyage & Désinfection
   Au Comptoir des Lilas — Mets Carnés Holding
   ============================================================ */

// ── État ──────────────────────────────────────────────────────
const tachesFaites = new Set();   // Set<id> des tâches cochées
let totalTaches    = 0;

// ── Références DOM ────────────────────────────────────────────
const elMain        = document.getElementById('nett-main');
const elEtat        = document.getElementById('nett-etat');
const elDate        = document.getElementById('nett-date');
const elCompteurNb  = document.getElementById('nett-compteur-nb');
const elCompteurLbl = document.getElementById('nett-compteur-label');
const elProgressBar = document.getElementById('nett-progress-bar');
const elProgressFill= document.getElementById('nett-progress-fill');
const elOperateur   = document.getElementById('nett-operateur');
const elBtnValider  = document.getElementById('nett-btn-valider');
const elToast       = document.getElementById('nett-toast');

// ── Date dans l'en-tête ───────────────────────────────────────
function afficherDate() {
  const d = new Date();
  elDate.textContent = d.toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });
}

// ── Compteur & progress ───────────────────────────────────────
function majCompteur() {
  const fait  = tachesFaites.size;
  const total = totalTaches;
  const pct   = total > 0 ? Math.round((fait / total) * 100) : 0;

  elCompteurNb.textContent  = fait;
  elCompteurLbl.textContent = `/ ${total} fait`;
  elProgressFill.style.width = `${pct}%`;
  elProgressBar.setAttribute('aria-valuenow', pct);

  if (fait === total && total > 0) {
    elCompteurNb.classList.add('nettoyage-compteur-nb--complet');
  } else {
    elCompteurNb.classList.remove('nettoyage-compteur-nb--complet');
  }

  // Active le bouton seulement si opérateur sélectionné ET ≥1 tâche cochée
  elBtnValider.disabled = !(elOperateur.value && tachesFaites.size > 0);
}

// ── Toggle d'une ligne de tâche ───────────────────────────────
function toggleTache(ligne, id) {
  if (tachesFaites.has(id)) {
    tachesFaites.delete(id);
    ligne.classList.remove('nettoyage-tache--done');
    ligne.querySelector('.nettoyage-tache-check').textContent = '';
    ligne.setAttribute('aria-checked', 'false');
  } else {
    tachesFaites.add(id);
    ligne.classList.add('nettoyage-tache--done');
    ligne.querySelector('.nettoyage-tache-check').textContent = '✓';
    ligne.setAttribute('aria-checked', 'true');
  }
  majCompteur();
}

// ── Construction HTML d'une zone ─────────────────────────────
function construireZone(zone) {
  const section = document.createElement('section');
  section.className = 'nettoyage-zone';

  const titre = document.createElement('div');
  titre.className = 'nettoyage-zone-titre';
  titre.innerHTML = `
    <span>${zone.zone}</span>
    <span class="nettoyage-zone-badge">${zone.taches.length} tâche${zone.taches.length > 1 ? 's' : ''}</span>
  `;
  section.appendChild(titre);

  for (const t of zone.taches) {
    const freq = t.frequence.toLowerCase();
    const badgeClass = freq.includes('hebdo')
      ? 'nettoyage-badge-freq--hebdomadaire'
      : 'nettoyage-badge-freq--quotidien';

    const ligne = document.createElement('div');
    ligne.className = 'nettoyage-tache';
    ligne.setAttribute('role', 'checkbox');
    ligne.setAttribute('aria-checked', 'false');
    ligne.setAttribute('tabindex', '0');
    ligne.dataset.id = t.id;

    ligne.innerHTML = `
      <div class="nettoyage-tache-check" aria-hidden="true"></div>
      <div class="nettoyage-tache-infos">
        <div class="nettoyage-tache-nom">${t.nom_tache}</div>
        <div class="nettoyage-tache-meta">${t.methode_produit}</div>
      </div>
      <span class="nettoyage-badge-freq ${badgeClass}">${t.frequence}</span>
    `;

    ligne.addEventListener('click', () => toggleTache(ligne, t.id));
    ligne.addEventListener('keydown', (e) => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        toggleTache(ligne, t.id);
      }
    });

    section.appendChild(ligne);
  }

  return section;
}

// ── Chargement des tâches ─────────────────────────────────────
async function chargerTaches() {
  try {
    const res = await fetch('/api/nettoyage/taches');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const zones = await res.json();

    elMain.innerHTML = '';

    if (!zones.length) {
      elMain.innerHTML = '<div class="nettoyage-etat">Aucune tâche configurée.<br>Lancez le script seed_taches_nettoyage.py.</div>';
      return;
    }

    totalTaches = zones.reduce((acc, z) => acc + z.taches.length, 0);
    zones.forEach(z => elMain.appendChild(construireZone(z)));
    majCompteur();

  } catch (err) {
    elMain.innerHTML = `<div class="nettoyage-etat">Erreur de chargement : ${err.message}</div>`;
  }
}

// ── Toast ─────────────────────────────────────────────────────
let toastTimer = null;

function afficherToast(msg, erreur = false) {
  clearTimeout(toastTimer);
  elToast.textContent = msg;
  elToast.classList.toggle('nettoyage-toast--erreur', erreur);
  elToast.classList.add('nettoyage-toast--visible');
  toastTimer = setTimeout(() => elToast.classList.remove('nettoyage-toast--visible'), 3500);
}

// ── Validation de fin de journée ──────────────────────────────
async function validerJournee() {
  const operateur = elOperateur.value.trim();
  if (!operateur) {
    afficherToast('Sélectionnez un opérateur avant de valider.', true);
    elOperateur.focus();
    return;
  }
  if (tachesFaites.size === 0) {
    afficherToast('Cochez au moins une tâche avant de valider.', true);
    return;
  }

  elBtnValider.disabled = true;
  elBtnValider.textContent = 'Envoi…';

  try {
    const res = await fetch('/api/nettoyage/validation', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        operateur,
        taches_ids: [...tachesFaites],
        signature: 'OK',
      }),
    });

    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    afficherToast(`✅ ${data.nb_taches} tâche(s) validée(s) par ${data.operateur} !`);

    // Réinitialise la checklist après 2 s
    setTimeout(() => {
      tachesFaites.clear();
      document.querySelectorAll('.nettoyage-tache--done').forEach(el => {
        el.classList.remove('nettoyage-tache--done');
        el.querySelector('.nettoyage-tache-check').textContent = '';
        el.setAttribute('aria-checked', 'false');
      });
      elOperateur.value = '';
      majCompteur();
    }, 2000);

  } catch (err) {
    afficherToast(`Erreur : ${err.message}`, true);
    elBtnValider.disabled = false;
  } finally {
    elBtnValider.textContent = '✅ Valider la journée';
  }
}

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  afficherDate();
  chargerTaches();
  elBtnValider.addEventListener('click', validerJournee);
  elOperateur.addEventListener('change', majCompteur);
});

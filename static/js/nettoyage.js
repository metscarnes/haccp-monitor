'use strict';
/* ============================================================
   nettoyage.js — Planning Hebdomadaire de Nettoyage
   Au Comptoir des Lilas — Mets Carnés Holding

   - Tableau Secteur / Quoi / Quand / Comment / Lun→Dim
   - 1 clic "Valider" = coche la colonne du jour
   - Hebdo = coché uniquement le Samedi (jour 6)
   ============================================================ */

const JOUR_HEBDO = 6; // Samedi = jour de grand nettoyage

const JOURS = ['Dimanche','Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi'];

let zonesData    = [];   // données API
let todayIndex   = 0;    // 0=Dim, 1=Lun … 6=Sam
let allTaskIds   = [];   // [{id, freq}] pour toutes les lignes

// ── DOM ──────────────────────────────────────────────────────
const elDate     = document.getElementById('display-date');
const elSelect   = document.getElementById('operator-select');
const elBtn      = document.getElementById('btn-valider');
const elTbody    = document.getElementById('table-body');
const elToast    = document.getElementById('nett-toast');

// ── Chargement du personnel (même source que le reste de l'app) ──
async function chargerPersonnel() {
  try {
    const res = await fetch('/api/admin/personnel');
    if (!res.ok) throw new Error();
    const personnes = await res.json();
    personnes
      .filter(p => p.actif !== false)
      .forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.prenom;
        opt.textContent = p.prenom;
        elSelect.appendChild(opt);
      });
  } catch {
    // Fallback silencieux : le select reste vide avec le placeholder
  }
}

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  identifierJour();
  chargerPersonnel();
  chargerTaches(); // restaurerEtat() est appelé après la génération du tableau
  elBtn.addEventListener('click', validerJournee);
});

// ── Jour actuel ──────────────────────────────────────────────
function identifierJour() {
  const d = new Date();
  todayIndex = d.getDay(); // 0=Dim … 6=Sam

  const opts = { weekday: 'long', day: 'numeric', month: 'long' };
  const txt  = d.toLocaleDateString('fr-FR', opts);
  elDate.textContent = 'Aujourd\'hui : ' + txt.charAt(0).toUpperCase() + txt.slice(1);

  elBtn.textContent = `✅ VALIDER LE NETTOYAGE DU ${JOURS[todayIndex].toUpperCase()}`;

  // Surligner les en-têtes du jour
  document.querySelectorAll(`th[data-day="${todayIndex}"]`)
    .forEach(th => th.classList.add('nett-today-col'));
}

// ── Charger depuis l'API ─────────────────────────────────────
async function chargerTaches() {
  try {
    const res = await fetch('/api/nettoyage/taches');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    zonesData = await res.json();
    genererTableau();
    await chargerHistoriqueSemaine(); // charge les validations passées de la semaine
    await restaurerEtat(); // restaure l'état "Validé" si déjà fait aujourd'hui
  } catch (err) {
    elTbody.innerHTML = `<tr><td colspan="11" style="padding:2rem;text-align:center;color:#888;">
      Erreur : ${err.message}</td></tr>`;
  }
}

// ── Charger l'historique de la semaine complète ──────────────
async function chargerHistoriqueSemaine() {
  const today = new Date();

  // Calcul de semaine ISO 8601
  const d = new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()));
  const dayNum = d.getUTCDay() || 7; // 1=lun, 7=dim
  d.setUTCDate(d.getUTCDate() + 4 - dayNum); // Aller au jeudi de la semaine
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNum = Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
  const isoYear = d.getUTCFullYear();

  console.log('🔍 Date du jour:', today.toISOString().split('T')[0]);
  console.log('🔍 Semaine ISO:', isoYear, 'Semaine:', weekNum);

  try {
    const url = `/api/nettoyage/historique/semaine?annee_iso=${isoYear}&semaine=${weekNum}`;
    console.log('🌐 Fetching:', url);
    const res = await fetch(url);
    if (!res.ok) {
      console.warn('API error:', res.status);
      return;
    }
    const data = await res.json();
    console.log('📊 Données API reçues:', data);

    // Pour chaque date de la semaine, remplir les cellules validées
    data.zones.forEach(zone => {
      zone.taches.forEach(task => {
        Object.entries(task.validations).forEach(([dateStr, signet]) => {
          if (!signet) return;

          const d = new Date(dateStr + 'T00:00:00');
          const dayOfWeek = d.getDay();

          console.log(`Tâche ${task.id} - ${dateStr} (${dayOfWeek}): ${signet}`);

          const cell = document.querySelector(
            `td.nett-day-cell[data-day="${dayOfWeek}"][data-id="${task.id}"]`
          );
          if (cell) {
            console.log(`✅ Cellule trouvée et remplie`);
            cell.innerHTML = `<span class="nett-check">✅</span><span class="nett-initial">${signet}</span>`;
          } else {
            console.warn(`❌ Cellule introuvable pour jour=${dayOfWeek}, id=${task.id}`);
          }
        });
      });
    });
  } catch (err) {
    console.error('Erreur historique:', err);
  }
}

// ── Restaurer l'état de validation au rechargement ───────────
async function restaurerEtat() {
  const today = new Date().toISOString().split('T')[0];
  try {
    const res = await fetch(`/api/nettoyage/status?date=${today}`);
    if (!res.ok) return;
    const data = await res.json();
    if (!data.valide) return;

    // Remplir les cellules du jour validées
    const initiale = data.operateur ? data.operateur.charAt(0).toUpperCase() : '?';
    data.taches_ids.forEach(id => {
      const cell = document.querySelector(
        `td.nett-day-cell[data-day="${todayIndex}"][data-id="${id}"]`
      );
      if (cell) {
        cell.innerHTML = `<span class="nett-check">✅</span><span class="nett-initial">${initiale}.</span>`;
      }
    });

    // Verrouiller le bouton et le select
    elBtn.disabled = true;
    elBtn.textContent = `✔️ VALIDÉ — ${data.nb_taches} tâche(s)`;
    elBtn.classList.add('nett-btn-valider--done');
    if (data.operateur) elSelect.value = data.operateur;
    elSelect.disabled = true;
  } catch {
    // Silencieux — l'état par défaut (non validé) reste affiché
  }
}

// ── Génération du tableau ────────────────────────────────────
function genererTableau() {
  let html = '';
  allTaskIds = [];

  zonesData.forEach((zone, zoneIdx) => {
    const even = zoneIdx % 2 === 1;

    zone.taches.forEach((task, taskIdx) => {
      const rowClass = even ? 'nett-row-even' : '';
      html += `<tr class="${rowClass}">`;

      // Cellule secteur (fusionnée sur N lignes)
      if (taskIdx === 0) {
        html += `<td class="nett-secteur-cell" rowspan="${zone.taches.length}">${zone.zone}</td>`;
      }

      // Quoi (title = texte complet au survol si tronqué)
      html += `<td class="nett-quoi-cell" title="${task.nom_tache}">${task.nom_tache}</td>`;

      // Quand
      const isHebdo = task.frequence.toLowerCase().includes('hebdo');
      html += `<td class="nett-quand-cell ${isHebdo ? 'nett-quand-cell--hebdo' : ''}">${task.frequence}</td>`;

      // Produit
      html += `<td class="nett-comment-cell">${task.methode_produit}</td>`;

      // 7 colonnes jour (Lun=1, Mar=2 … Sam=6, Dim=0)
      const dayOrder = [1, 2, 3, 4, 5, 6, 0];
      dayOrder.forEach(day => {
        const isToday = day === todayIndex;
        const todayCls = isToday ? ' nett-today-col' : '';
        html += `<td class="nett-day-cell${todayCls}" data-day="${day}" data-id="${task.id}" data-freq="${task.frequence}"></td>`;
      });

      html += '</tr>';

      allTaskIds.push({ id: task.id, freq: task.frequence });
    });
  });

  elTbody.innerHTML = html;
}

// ── Validation ───────────────────────────────────────────────
async function validerJournee() {
  const operateur = elSelect.value;

  if (!operateur) {
    toast('Sélectionnez votre nom avant de valider.', true);
    elSelect.focus();
    return;
  }

  const ok = confirm(
    'En validant, je confirme sur l\'honneur avoir effectué l\'intégralité des tâches ' +
    'de nettoyage et de désinfection listées pour aujourd\'hui, en respectant le Plan de Nettoyage.'
  );
  if (!ok) return;

  const initiale = operateur.charAt(0).toUpperCase();

  // Collecter les IDs à valider + remplir les cellules
  const idsAValider = [];
  const cellsDuJour = document.querySelectorAll(`td.nett-day-cell[data-day="${todayIndex}"]`);

  cellsDuJour.forEach(cell => {
    const freq = cell.getAttribute('data-freq').toLowerCase();
    const id   = parseInt(cell.getAttribute('data-id'), 10);

    const isQuotidien = freq.includes('quotidien');
    const isHebdo     = freq.includes('hebdo');

    if (isQuotidien || (isHebdo && todayIndex === JOUR_HEBDO)) {
      cell.innerHTML = `<span class="nett-check">✅</span><span class="nett-initial">${initiale}.</span>`;
      idsAValider.push(id);
    }
  });

  if (idsAValider.length === 0) {
    toast('Aucune tâche à valider pour aujourd\'hui.', true);
    return;
  }

  // Verrouiller le bouton immédiatement (UI)
  elBtn.disabled = true;
  elBtn.textContent = '⏳ Envoi…';
  elSelect.disabled = true;

  // Envoyer au backend
  try {
    const res = await fetch('/api/nettoyage/validation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        operateur,
        taches_ids: idsAValider,
        signature: 'OK',
      }),
    });

    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    elBtn.textContent = `✔️ VALIDÉ — ${data.nb_taches} tâche(s)`;
    elBtn.classList.add('nett-btn-valider--done');
    toast(`✅ ${data.nb_taches} tâche(s) validée(s) par ${operateur} !`);

  } catch (err) {
    toast(`Erreur : ${err.message}`, true);
    // En cas d'erreur réseau, on re-déverrouille pour retenter
    elBtn.disabled = false;
    elBtn.textContent = `✅ VALIDER LE NETTOYAGE DU ${JOURS[todayIndex].toUpperCase()}`;
    elSelect.disabled = false;
  }
}

// ── Toast ────────────────────────────────────────────────────
let toastTimer;
function toast(msg, erreur = false) {
  clearTimeout(toastTimer);
  elToast.textContent = msg;
  elToast.classList.toggle('nett-toast--erreur', erreur);
  elToast.classList.add('nett-toast--visible');
  toastTimer = setTimeout(() => elToast.classList.remove('nett-toast--visible'), 3500);
}

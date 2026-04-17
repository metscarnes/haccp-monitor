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

// ── Date locale ISO (évite le décalage UTC de toISOString) ───
function toLocalDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

let zonesData    = [];   // données API
let todayIndex   = 0;    // 0=Dim, 1=Lun … 6=Sam
let allTaskIds   = [];   // [{id, freq}] pour toutes les lignes
let weekDates    = {};   // {jsDay: "YYYY-MM-DD"} pour la semaine en cours

// ── DOM ──────────────────────────────────────────────────────
const elDate     = document.getElementById('display-date');
const elSelect   = document.getElementById('operator-select');
const elBtn      = document.getElementById('btn-valider');
const elTbody    = document.getElementById('table-body');
const elToast    = document.getElementById('nett-toast');

// Modale gestion tâches
const elBtnGerer      = document.getElementById('btn-gerer');
const elModal         = document.getElementById('modal-gerer');
const elBtnClose      = document.getElementById('btn-modal-close');
const elModalListe    = document.getElementById('modal-liste');
const elFormTitle     = document.getElementById('form-title');
const elFormId        = document.getElementById('form-id');
const elFormZone      = document.getElementById('form-zone');
const elFormNom       = document.getElementById('form-nom');
const elFormFreq      = document.getElementById('form-freq');
const elFormProduit   = document.getElementById('form-produit');
const elBtnSave       = document.getElementById('btn-form-save');
const elBtnCancel     = document.getElementById('btn-form-cancel');

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
  computeWeekDates();
  identifierJour();
  chargerPersonnel();
  chargerTaches(); // restaurerEtat() est appelé après la génération du tableau
  elBtn.addEventListener('click', validerJournee);

  // Toggle individuel par clic sur une cellule
  elTbody.addEventListener('click', e => {
    const cell = e.target.closest('td.nett-day-cell');
    if (cell) toggleCell(cell);
  });

  // Clic sur en-tête de colonne → cocher toute la colonne (sauf hebdo)
  document.querySelector('#planning-table thead').addEventListener('click', e => {
    const th = e.target.closest('th[data-day]');
    if (th) validerColonne(parseInt(th.dataset.day, 10));
  });

  // Modale gestion
  elBtnGerer.addEventListener('click', ouvrirModalGerer);
  elBtnClose.addEventListener('click', fermerModalGerer);
  elModal.addEventListener('click', e => { if (e.target === elModal) fermerModalGerer(); });
  elBtnSave.addEventListener('click', sauverTache);
  elBtnCancel.addEventListener('click', reinitFormTache);
});

// ── Calcul des dates de la semaine courante ───────────────────
function computeWeekDates() {
  const today = new Date();
  const dow = today.getDay(); // 0=Dim, 1=Lun…
  // Lundi = premier jour de semaine
  const daysFromMonday = dow === 0 ? 6 : dow - 1;
  const monday = new Date(today);
  monday.setDate(today.getDate() - daysFromMonday);
  monday.setHours(0, 0, 0, 0);

  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    weekDates[d.getDay()] = toLocalDate(d); // toISOString() donne UTC → décalage en UTC+x
  }
}

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
  const today = toLocalDate(new Date());
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

    if (data.operateur) elSelect.value = data.operateur;
    mettreAJourBouton();
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
        html += `<td class="nett-day-cell${todayCls}" data-day="${day}" data-id="${task.id}" data-freq="${task.frequence}" data-date="${weekDates[day] || ''}"></td>`;
      });

      html += '</tr>';

      allTaskIds.push({ id: task.id, freq: task.frequence });
    });
  });

  elTbody.innerHTML = html;
}

// ── Validation (tout le jour d'un coup) ──────────────────────
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

  const initiale  = operateur.charAt(0).toUpperCase();
  const today     = weekDates[todayIndex] || toLocalDate(new Date());

  // Collecter TOUS les IDs applicables — le backend gère les doublons (INSERT OR IGNORE)
  // Visuellement : ne cocher que les cases encore vides
  const idsAValider = [];
  const cellules    = [];   // pour rollback visuel en cas d'erreur
  const cellsDuJour = document.querySelectorAll(`td.nett-day-cell[data-day="${todayIndex}"]`);

  cellsDuJour.forEach(cell => {
    const freq = cell.dataset.freq.toLowerCase();
    const id   = parseInt(cell.dataset.id, 10);
    const applicable = freq.includes('quotidien') || (freq.includes('hebdo') && todayIndex === JOUR_HEBDO);
    if (!applicable) return;

    idsAValider.push(id); // toujours inclus → INSERT OR IGNORE côté backend
    if (!cell.querySelector('.nett-check')) {
      cell.innerHTML = `<span class="nett-check">✅</span><span class="nett-initial">${initiale}.</span>`;
      cellules.push(cell); // seulement les nouvelles pour le rollback
    }
  });

  if (idsAValider.length === 0) {
    toast('Aucune tâche applicable aujourd\'hui.', false);
    return;
  }

  const prevText = elBtn.textContent;
  elBtn.textContent = '⏳ Envoi…';

  try {
    const res = await fetch('/api/nettoyage/validation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ operateur, taches_ids: idsAValider, signature: 'OK', date: today }),
    });

    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail || `HTTP ${res.status}`);
    }

    await res.json();
    toast(`✅ ${idsAValider.length} tâche(s) du jour validées par ${operateur} !`);

  } catch (err) {
    toast(`Erreur : ${err.message}`, true);
    // Rollback visuel des cellules qu'on venait de cocher
    cellules.forEach(c => { c.innerHTML = ''; });
    elBtn.textContent = prevText;
  }

  mettreAJourBouton();
}

// ── Cocher toute une colonne jour (sauf hebdo) ───────────────
async function validerColonne(dayIndex) {
  const operateur = elSelect.value;
  if (!operateur) {
    toast('Sélectionnez votre nom avant de cocher.', true);
    elSelect.focus();
    return;
  }

  const date = weekDates[dayIndex] || '';
  if (!date) return;

  const initiale  = operateur.charAt(0).toUpperCase();
  const ids       = [];
  const nouvelles = [];

  document.querySelectorAll(`td.nett-day-cell[data-day="${dayIndex}"]`).forEach(cell => {
    if (cell.dataset.freq.toLowerCase().includes('hebdo')) return; // hebdo → ignoré
    ids.push(parseInt(cell.dataset.id, 10));
    if (!cell.querySelector('.nett-check')) {
      cell.innerHTML = `<span class="nett-check">✅</span><span class="nett-initial">${initiale}.</span>`;
      nouvelles.push(cell);
    }
  });

  if (ids.length === 0) return;

  try {
    const res = await fetch('/api/nettoyage/validation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ operateur, taches_ids: ids, date }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    if (dayIndex === todayIndex) mettreAJourBouton();
    toast(`✅ ${ids.length} tâche(s) cochées.`);
  } catch (err) {
    toast(`Erreur : ${err.message}`, true);
    nouvelles.forEach(c => { c.innerHTML = ''; });
  }
}

// ── Toggle individuel d'une cellule ──────────────────────────
async function toggleCell(cell) {
  const id      = parseInt(cell.dataset.id, 10);
  const date    = cell.dataset.date;
  if (!date) return;

  const isChecked = !!cell.querySelector('.nett-check');

  if (isChecked) {
    // Décocher — pas besoin d'opérateur
    try {
      const res = await fetch(`/api/nettoyage/validation?tache_id=${id}&date=${date}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      cell.innerHTML = '';
      mettreAJourBouton();
      toast('Case décochée et enregistrée.');
    } catch (err) {
      toast(`Erreur : ${err.message}`, true);
    }
  } else {
    // Cocher — opérateur requis
    const operateur = elSelect.value;
    if (!operateur) {
      toast('Sélectionnez votre nom avant de cocher.', true);
      elSelect.focus();
      return;
    }
    const initiale = operateur.charAt(0).toUpperCase();
    try {
      const res = await fetch('/api/nettoyage/validation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operateur, taches_ids: [id], date }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      cell.innerHTML = `<span class="nett-check">✅</span><span class="nett-initial">${initiale}.</span>`;
      mettreAJourBouton();
      toast('Case cochée et enregistrée.');
    } catch (err) {
      toast(`Erreur : ${err.message}`, true);
    }
  }
}

// ── Mise à jour dynamique du bouton VALIDER ───────────────────
function mettreAJourBouton() {
  const cells = document.querySelectorAll(`td.nett-day-cell[data-day="${todayIndex}"]`);
  let total = 0, coches = 0;
  cells.forEach(cell => {
    const freq = cell.dataset.freq.toLowerCase();
    const applicable = freq.includes('quotidien') || (freq.includes('hebdo') && todayIndex === JOUR_HEBDO);
    if (applicable) {
      total++;
      if (cell.querySelector('.nett-check')) coches++;
    }
  });

  if (total === 0) return;

  if (coches === total) {
    elBtn.textContent = `✔ VALIDÉ — ${total} tâche(s)`;
    elBtn.classList.add('nett-btn-valider--done');
  } else if (coches > 0) {
    elBtn.textContent = `✅ VALIDER LE RESTE (${coches}/${total})`;
    elBtn.classList.remove('nett-btn-valider--done');
  } else {
    elBtn.textContent = `✅ VALIDER LE NETTOYAGE DU ${JOURS[todayIndex].toUpperCase()}`;
    elBtn.classList.remove('nett-btn-valider--done');
  }
}

// ── GESTION DES TÂCHES (modale) ──────────────────────────────

async function ouvrirModalGerer() {
  elModal.hidden = false;
  await chargerListeModal();
}

function fermerModalGerer() {
  elModal.hidden = true;
  reinitFormTache();
}

async function chargerListeModal() {
  elModalListe.innerHTML = '<p style="padding:.5rem;color:#888;font-size:.8rem;">Chargement…</p>';
  try {
    const res = await fetch('/api/nettoyage/taches');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const zones = await res.json();

    if (!zones.length) {
      elModalListe.innerHTML = '<p style="padding:.5rem;color:#888;font-size:.8rem;">Aucune tâche définie.</p>';
      return;
    }

    let html = '';
    zones.forEach(({ zone, taches }) => {
      html += `<div class="nett-zone-groupe">
        <div class="nett-zone-titre">${zone}</div>`;
      taches.forEach(t => {
        html += `<div class="nett-tache-row" data-id="${t.id}">
          <span class="nett-tache-nom">${t.nom_tache}</span>
          <span class="nett-tache-freq">${t.frequence}</span>
          <span class="nett-tache-produit">${t.methode_produit}</span>
          <button class="nett-btn-edit" data-action="edit"
            data-id="${t.id}" data-zone="${zone}"
            data-nom="${t.nom_tache}" data-freq="${t.frequence}"
            data-produit="${t.methode_produit}">✏ Modifier</button>
          <button class="nett-btn-del" data-action="del" data-id="${t.id}"
            data-nom="${t.nom_tache}">🗑</button>
        </div>`;
      });
      html += '</div>';
    });
    elModalListe.innerHTML = html;

    elModalListe.addEventListener('click', onListeClick, { once: true });
    // Ré-attacher à chaque rechargement
    elModalListe.onclick = onListeClick;
  } catch (err) {
    elModalListe.innerHTML = `<p style="padding:.5rem;color:red;font-size:.8rem;">Erreur : ${err.message}</p>`;
  }
}

function onListeClick(e) {
  const btn = e.target.closest('button[data-action]');
  if (!btn) return;
  if (btn.dataset.action === 'edit') {
    elFormId.value      = btn.dataset.id;
    elFormZone.value    = btn.dataset.zone;
    elFormNom.value     = btn.dataset.nom;
    elFormFreq.value    = btn.dataset.freq;
    elFormProduit.value = btn.dataset.produit;
    elFormTitle.textContent = '✏ Modifier la tâche';
    elBtnCancel.hidden  = false;
    elBtnSave.textContent = 'Enregistrer les modifications';
    elBtnSave.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } else if (btn.dataset.action === 'del') {
    supprimerTache(parseInt(btn.dataset.id, 10), btn.dataset.nom);
  }
}

async function sauverTache() {
  const id      = elFormId.value;
  const payload = {
    zone:            elFormZone.value.trim().toUpperCase(),
    nom_tache:       elFormNom.value.trim().toUpperCase(),
    frequence:       elFormFreq.value,
    methode_produit: elFormProduit.value.trim().toUpperCase(),
  };

  if (!payload.zone || !payload.nom_tache) {
    toast('Zone et nom de tâche obligatoires.', true);
    return;
  }

  try {
    const url    = id ? `/api/nettoyage/taches/${id}` : '/api/nettoyage/taches';
    const method = id ? 'PUT' : 'POST';
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail || `HTTP ${res.status}`);
    }
    toast(id ? '✅ Tâche modifiée.' : '✅ Tâche ajoutée.');
    reinitFormTache();
    await chargerListeModal();
    // Recharger le tableau principal
    await chargerTaches();
  } catch (err) {
    toast(`Erreur : ${err.message}`, true);
  }
}

async function supprimerTache(id, nom) {
  if (!confirm(`Supprimer la tâche "${nom}" ?\nLes validations passées ne seront pas effacées.`)) return;
  try {
    const res = await fetch(`/api/nettoyage/taches/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail || `HTTP ${res.status}`);
    }
    toast('🗑 Tâche supprimée.');
    await chargerListeModal();
    await chargerTaches();
  } catch (err) {
    toast(`Erreur : ${err.message}`, true);
  }
}

function reinitFormTache() {
  elFormId.value        = '';
  elFormZone.value      = '';
  elFormNom.value       = '';
  elFormFreq.value      = 'Quotidien';
  elFormProduit.value   = '';
  elFormTitle.textContent = '+ Ajouter une tâche';
  elBtnCancel.hidden    = true;
  elBtnSave.textContent = 'Enregistrer';
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

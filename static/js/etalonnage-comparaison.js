'use strict';
/* ============================================================
   etalonnage-comparaison.js — Screen 2 : Comparaison sondes Zigbee
   Au Comptoir des Lilas — Mets Carnés Holding

   Pour chaque enceinte :
   - Température Zigbee   → auto depuis API (actualisée)
   - Température de référence → saisie manuelle par l'opérateur
   - Écart = temp_ref − temp_zigbee
   - Conforme si |écart| ≤ 0,5°C
   ============================================================ */

const ECART_MAX   = 0.5;
const REFRESH_MS  = 30_000;

// ── Récupérer l'ID de l'étalonnage depuis l'URL ───────────────
const etalonnageId = new URLSearchParams(location.search).get('id');
if (!etalonnageId) {
  // Pas d'ID → retour Screen 1
  location.href = '/etalonnage.html';
}

// ── Références DOM ────────────────────────────────────────────
const elHorloge       = document.getElementById('etal-horloge');
const elPhase1Resume  = document.getElementById('etal-phase1-resume');
const elPhase1Detail  = document.getElementById('etal-phase1-detail');
const elPhase1Card    = document.getElementById('etal-phase1-card');
const elGrille        = document.getElementById('etal-enceintes-grille');
const elMsg           = document.getElementById('etal-msg-comp');
const elSubmit        = document.getElementById('etal-submit-comp');
const elSubmitTexte   = document.getElementById('etal-submit-comp-texte');

// État : map enceinte_id → { enceinte, temp_zigbee }
const enceintesState = new Map();

// ── Horloge ───────────────────────────────────────────────────
function majHorloge() {
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();

// ── Fetch helper ──────────────────────────────────────────────
async function apiFetch(url, opts = {}) {
  const res = await fetch(url, { cache: 'no-store', ...opts });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    let detail = txt;
    try { detail = JSON.parse(txt).detail ?? txt; } catch { /* ignore */ }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Charger le contexte Phase 1 ───────────────────────────────
async function chargerPhase1() {
  try {
    const e = await apiFetch(`/api/etalonnage/${etalonnageId}`);
    const date = formatDate(e.date_etalonnage);
    const action = labelAction(e.action_corrective);
    elPhase1Resume.textContent = `EET01 — ${date} — ${e.thermometre_nom}`;
    elPhase1Detail.innerHTML =
      `<strong>${e.thermometre_nom}</strong> &ensp;|&ensp; `
      + `${e.temperature_mesuree.toFixed(1)}°C &ensp;|&ensp; `
      + `${action} &ensp;|&ensp; ${esc(e.operateur)}`;
  } catch {
    elPhase1Card.style.display = 'none';
  }
}

// ── Charger / actualiser les températures Zigbee ─────────────
async function chargerTemperaturesZigbee() {
  try {
    const dash = await apiFetch('/api/boutiques/1/dashboard');
    const enceintes = dash.enceintes ?? [];

    if (enceintesState.size === 0) {
      // Premier chargement → construire les cartes
      construireGrille(enceintes);
    } else {
      // Actualisation → mettre à jour uniquement les températures affichées
      enceintes.forEach(enc => {
        const s = enceintesState.get(enc.id);
        if (!s) return;
        s.temp_zigbee = enc.temperature_actuelle;
        majTempZigbee(enc.id, enc.temperature_actuelle);
        majBadge(enc.id);
      });
    }
  } catch {
    if (enceintesState.size === 0) {
      elGrille.innerHTML = '<div class="etal-vide">⚠ Impossible de charger les enceintes</div>';
    }
  }
}

// ── Construire la grille de cartes (une seule fois) ───────────
function construireGrille(enceintes) {
  if (!enceintes || enceintes.length === 0) {
    elGrille.innerHTML = '<div class="etal-vide">Aucune enceinte configurée</div>';
    return;
  }

  elGrille.innerHTML = '';

  enceintes.forEach(enc => {
    enceintesState.set(enc.id, {
      enceinte: enc,
      temp_zigbee: enc.temperature_actuelle,
    });

    const card = document.createElement('div');
    card.className = 'etal-comp-card';
    card.dataset.id = enc.id;
    card.innerHTML = `
      <div class="etal-comp-nom">${esc(enc.nom)}</div>

      <div class="etal-comp-row">
        <div class="etal-comp-col">
          <div class="etal-comp-label">Sonde Zigbee</div>
          <div class="etal-comp-temp-zigbee" id="zigbee-${enc.id}">
            ${formatTemp(enc.temperature_actuelle)}
          </div>
        </div>
        <div class="etal-comp-col">
          <div class="etal-comp-label">Thermo de référence *</div>
          <input
            class="etal-input etal-comp-input"
            id="ref-${enc.id}"
            type="number"
            step="0.1"
            placeholder="Ex : 2,4"
            aria-label="Température de référence pour ${esc(enc.nom)}"
          >
        </div>
      </div>

      <div id="badge-${enc.id}" class="etal-conformite-badge etal-conformite-badge--vide">
        — Saisir la température de référence
      </div>
    `;

    // Badge en temps réel à la saisie
    card.querySelector(`#ref-${enc.id}`).addEventListener('input', () => {
      majBadge(enc.id);
      majBoutonSubmit();
    });

    elGrille.appendChild(card);
  });

  majBoutonSubmit();
}

// ── Mise à jour d'un affichage temp Zigbee ────────────────────
function majTempZigbee(enteId, temp) {
  const el = document.getElementById(`zigbee-${enteId}`);
  if (el) el.textContent = formatTemp(temp);
}

// ── Badge écart (identique logique Screen 1) ─────────────────
function majBadge(enceId) {
  const s      = enceintesState.get(enceId);
  const elBadge = document.getElementById(`badge-${enceId}`);
  const elRef   = document.getElementById(`ref-${enceId}`);
  if (!s || !elBadge || !elRef) return;

  const tempRef = parseFloat(elRef.value);
  if (isNaN(tempRef) || s.temp_zigbee === null) {
    elBadge.className = 'etal-conformite-badge etal-conformite-badge--vide';
    elBadge.textContent = '— Saisir la température de référence';
    return;
  }

  const ecart   = tempRef - s.temp_zigbee;
  const ok      = Math.abs(ecart) <= ECART_MAX;
  const signe   = ecart >= 0 ? '+' : '';
  const ecartStr = `${signe}${ecart.toFixed(1)}°C`;

  if (ok) {
    elBadge.className = 'etal-conformite-badge etal-conformite-badge--ok';
    elBadge.textContent = `✅ Conforme — écart : ${ecartStr} dans [−0,5 ; +0,5]`;
  } else {
    elBadge.className = 'etal-conformite-badge etal-conformite-badge--nok';
    elBadge.textContent = `❌ Non conforme — écart : ${ecartStr} hors tolérance`;
  }
}

// ── Activer le bouton si toutes les saisies sont remplies ──────
function majBoutonSubmit() {
  const tous = [...enceintesState.keys()].every(id => {
    const el = document.getElementById(`ref-${id}`);
    return el && el.value !== '' && !isNaN(parseFloat(el.value));
  });
  elSubmit.disabled = !tous || enceintesState.size === 0;
}

// ── Soumission ────────────────────────────────────────────────
elSubmit.addEventListener('click', async () => {
  hideMsg();

  const comparaisons = [];
  for (const [id, s] of enceintesState.entries()) {
    const elRef = document.getElementById(`ref-${id}`);
    const tempRef = parseFloat(elRef?.value ?? '');
    if (isNaN(tempRef)) {
      showMsg('Toutes les températures de référence sont obligatoires.', 'erreur');
      return;
    }
    comparaisons.push({
      enceinte_id:    id,
      enceinte_nom:   s.enceinte.nom,
      temp_zigbee:    s.temp_zigbee ?? 0,
      temp_reference: tempRef,
    });
  }

  elSubmit.disabled         = true;
  elSubmitTexte.textContent = 'Envoi…';

  try {
    await apiFetch(`/api/etalonnage/${etalonnageId}/comparaisons`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ comparaisons }),
    });
    // Succès → retour à l'historique (Screen 1)
    location.href = '/etalonnage.html';
  } catch (err) {
    showMsg(`Erreur : ${err.message}`, 'erreur');
    elSubmit.disabled         = false;
    elSubmitTexte.textContent = 'Enregistrer les comparaisons ✓';
  }
});

// ── Messages ──────────────────────────────────────────────────
function showMsg(texte, type) {
  elMsg.textContent = texte;
  elMsg.className   = `etal-msg etal-msg--${type}`;
  elMsg.hidden      = false;
}
function hideMsg() { elMsg.hidden = true; }

// ── Helpers ───────────────────────────────────────────────────
function formatTemp(t) {
  return t !== null && t !== undefined ? `${Number(t).toFixed(1)} °C` : '— °C';
}

function formatDate(iso) {
  if (!iso) return '—';
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

function labelAction(code) {
  return { conforme: '✅ Conforme', calibrage: '🔧 Calibrage', remplace: '🔄 Remplacé' }[code] ?? code;
}

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Init ──────────────────────────────────────────────────────
async function init() {
  await chargerPhase1();
  await chargerTemperaturesZigbee();
  setInterval(chargerTemperaturesZigbee, REFRESH_MS);
}

init();

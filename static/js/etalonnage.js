'use strict';
/* ============================================================
   etalonnage.js — Étalonnage Thermomètres EET01
   Au Comptoir des Lilas — Mets Carnés Holding

   Règle : conforme si température ∈ [-0.5°C ; +0.5°C]
   Fréquence : trimestrielle (tous les ~3 mois)
   ============================================================ */

const TEMP_MIN = -0.5;
const TEMP_MAX =  0.5;

// ── Références DOM ────────────────────────────────────────────
const elHorloge     = document.getElementById('etal-horloge');
const elForm        = document.getElementById('etal-form');
const elDate        = document.getElementById('etal-date');
const elOperateur   = document.getElementById('etal-operateur');
const elThermo      = document.getElementById('etal-thermo');
const elTemp        = document.getElementById('etal-temp');
const elBadge       = document.getElementById('etal-conformite-badge');
const elMsg         = document.getElementById('etal-msg');
const elSubmit      = document.getElementById('etal-submit');
const elSubmitTexte = document.getElementById('etal-submit-texte');
const elHistBody    = document.getElementById('etal-historique-body');

const elLblConforme  = document.getElementById('lbl-conforme');
const elLblCalibrage = document.getElementById('lbl-calibrage');
const elLblRemplace  = document.getElementById('lbl-remplace');

// ── Horloge ───────────────────────────────────────────────────
function majHorloge() {
  const now = new Date();
  elHorloge.textContent = now.toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();

// Date par défaut = aujourd'hui
elDate.value = new Date().toISOString().slice(0, 10);

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

// ── Personnel ─────────────────────────────────────────────────
async function chargerPersonnel() {
  try {
    const data = await apiFetch('/api/admin/personnel');
    (data || []).forEach(p => {
      const opt = document.createElement('option');
      opt.value       = p.prenom;
      opt.textContent = p.prenom;
      elOperateur.appendChild(opt);
    });
  } catch {
    // silencieux — le champ reste vide
  }
}

// ── Badge conformité (temps réel) ────────────────────────────
function majBadgeConformite() {
  const val = parseFloat(elTemp.value);
  if (isNaN(val)) {
    elBadge.className = 'etal-conformite-badge etal-conformite-badge--vide';
    elBadge.textContent = '— Saisir une température';
    updateActionsDisponibles(null);
    return;
  }

  const ok = val >= TEMP_MIN && val <= TEMP_MAX;
  if (ok) {
    elBadge.className = 'etal-conformite-badge etal-conformite-badge--ok';
    elBadge.textContent = `✅ Conforme — ${val.toFixed(1)}°C dans [−0,5 ; +0,5]`;
  } else {
    elBadge.className = 'etal-conformite-badge etal-conformite-badge--nok';
    elBadge.textContent = `❌ Non conforme — ${val.toFixed(1)}°C hors tolérance`;
  }
  updateActionsDisponibles(ok);
}

/**
 * Active / désactive les boutons radio selon la conformité.
 * - Conforme  : disponible uniquement si temp OK
 * - Calibrage : disponible si non conforme
 * - Remplacé  : toujours disponible
 */
function updateActionsDisponibles(conforme) {
  const radios = elForm.querySelectorAll('[name="action_corrective"]');

  if (conforme === null) {
    // Rien saisi — tout désactivé
    elLblConforme .classList.add('etal-action-label--disabled');
    elLblCalibrage.classList.add('etal-action-label--disabled');
    elLblRemplace .classList.add('etal-action-label--disabled');
    radios.forEach(r => { r.checked = false; r.disabled = true; });
    return;
  }

  // Conforme disponible seulement si temp OK
  const rConforme  = elLblConforme.querySelector('input');
  const rCalibrage = elLblCalibrage.querySelector('input');
  const rRemplace  = elLblRemplace.querySelector('input');

  rConforme.disabled  = !conforme;
  rCalibrage.disabled = conforme;   // Calibrage seulement si non conforme
  rRemplace.disabled  = false;

  elLblConforme .classList.toggle('etal-action-label--disabled', !conforme);
  elLblCalibrage.classList.toggle('etal-action-label--disabled',  conforme);
  elLblRemplace .classList.remove('etal-action-label--disabled');

  // Si l'action sélectionnée est devenue invalide, la décocher
  if (rConforme.checked  && !conforme) rConforme.checked  = false;
  if (rCalibrage.checked &&  conforme) rCalibrage.checked = false;
}

elTemp.addEventListener('input', majBadgeConformite);

// Init désactivé
updateActionsDisponibles(null);

// ── Affichage message ─────────────────────────────────────────
function showMsg(texte, type) {
  elMsg.textContent = texte;
  elMsg.className   = `etal-msg etal-msg--${type}`;
  elMsg.hidden      = false;
}

function hideMsg() { elMsg.hidden = true; }

// ── Soumission ────────────────────────────────────────────────
elForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  hideMsg();

  const date     = elDate.value;
  const operateur= elOperateur.value;
  const thermo   = elThermo.value.trim();
  const tempStr  = elTemp.value;
  const actionEl = elForm.querySelector('[name="action_corrective"]:checked');

  // Validation côté client
  if (!date)     { showMsg('La date est obligatoire.',              'erreur'); return; }
  if (!operateur){ showMsg("Sélectionnez un opérateur.",            'erreur'); return; }
  if (!thermo)   { showMsg("L'identification du thermomètre est obligatoire.", 'erreur'); return; }
  if (tempStr === '') { showMsg('La température est obligatoire.',  'erreur'); return; }
  if (!actionEl) { showMsg('Sélectionnez une action corrective.',   'erreur'); return; }

  const payload = {
    date_etalonnage:     date,
    thermometre_id:      thermo,
    temperature_mesuree: parseFloat(tempStr),
    action_corrective:   actionEl.value,
    operateur:           operateur,
    commentaire:         document.getElementById('etal-commentaire').value.trim() || null,
  };

  elSubmit.disabled         = true;
  elSubmitTexte.textContent = 'Envoi…';

  try {
    await apiFetch('/api/etalonnage', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });

    showMsg('Étalonnage enregistré avec succès.', 'succes');
    elForm.reset();
    elDate.value = new Date().toISOString().slice(0, 10);
    elBadge.className = 'etal-conformite-badge etal-conformite-badge--vide';
    elBadge.textContent = '— Saisir une température';
    updateActionsDisponibles(null);
    await chargerHistorique();
  } catch (err) {
    showMsg(`Erreur : ${err.message}`, 'erreur');
  } finally {
    elSubmit.disabled         = false;
    elSubmitTexte.textContent = 'Enregistrer ✓';
  }
});

// ── Historique ────────────────────────────────────────────────
function labelAction(code) {
  switch (code) {
    case 'conforme':  return '✅ Conforme';
    case 'calibrage': return '🔧 Calibrage';
    case 'remplace':  return '🔄 Remplacé';
    default: return code;
  }
}

function formatDate(iso) {
  if (!iso) return '—';
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

async function chargerHistorique() {
  try {
    const data = await apiFetch('/api/etalonnage/historique');
    if (!data || data.length === 0) {
      elHistBody.innerHTML = '<tr><td colspan="6" class="etal-vide">Aucun étalonnage enregistré</td></tr>';
      return;
    }

    elHistBody.innerHTML = data.map(r => {
      const badgeClass = r.conforme ? 'etal-badge--ok' : 'etal-badge--nok';
      const badgeLabel = r.conforme ? '✅ Conforme' : '❌ Non conforme';
      const temp = typeof r.temperature_mesuree === 'number'
        ? r.temperature_mesuree.toFixed(1) + ' °C' : '—';
      return `<tr>
        <td>${formatDate(r.date_etalonnage)}</td>
        <td>${esc(r.thermometre_id)}</td>
        <td>${temp}</td>
        <td><span class="etal-badge ${badgeClass}">${badgeLabel}</span></td>
        <td>${labelAction(r.action_corrective)}</td>
        <td>${esc(r.operateur)}</td>
      </tr>`;
    }).join('');
  } catch {
    elHistBody.innerHTML = '<tr><td colspan="6" class="etal-vide">⚠ Erreur de chargement</td></tr>';
  }
}

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Init ──────────────────────────────────────────────────────
chargerPersonnel();
chargerHistorique();

'use strict';
/* ============================================================
   etalonnage.js — Screen 1 : Étalonnage du thermomètre de référence
   Au Comptoir des Lilas — Mets Carnés Holding

   Règle : conforme si température ∈ [−0,5°C ; +0,5°C]
   - Conforme     → uniquement action "Conforme"
   - Non conforme → uniquement "Calibrage" ou "Remplacé"
   Après soumission → redirect vers Screen 2 (comparaisons)
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
      opt.value = p.prenom;
      opt.textContent = p.prenom;
      elOperateur.appendChild(opt);
    });
  } catch { /* silencieux */ }
}

// ── Thermomètres de référence ─────────────────────────────────
async function chargerThermometres() {
  try {
    const data = await apiFetch('/api/admin/thermometres');
    const actifs = (data || []).filter(t => t.actif);
    if (actifs.length === 0) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = '⚠ Aucun thermomètre configuré';
      opt.disabled = true;
      elThermo.appendChild(opt);
      return;
    }
    actifs.forEach(t => {
      const opt = document.createElement('option');
      opt.value = t.id;
      opt.textContent = t.numero_serie ? `${t.nom} — ${t.numero_serie}` : t.nom;
      elThermo.appendChild(opt);
    });
  } catch { /* silencieux */ }
}

// ── Badge conformité (temps réel) ────────────────────────────
function majBadgeConformite() {
  const val = parseFloat(elTemp.value);
  if (isNaN(val)) {
    elBadge.className = 'etal-conformite-badge etal-conformite-badge--vide';
    elBadge.textContent = '— Saisir une température';
    setActionsDisponibles(null);
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
  setActionsDisponibles(ok);
}

/**
 * Règle stricte :
 *  - Conforme     → uniquement "Conforme" disponible
 *  - Non conforme → uniquement "Calibrage" et "Remplacé" disponibles
 *  - null (rien saisi) → tout désactivé
 */
function setActionsDisponibles(conforme) {
  const rConforme  = elLblConforme.querySelector('input');
  const rCalibrage = elLblCalibrage.querySelector('input');
  const rRemplace  = elLblRemplace.querySelector('input');

  if (conforme === null) {
    [rConforme, rCalibrage, rRemplace].forEach(r => {
      r.checked = false;
      r.disabled = true;
    });
    [elLblConforme, elLblCalibrage, elLblRemplace].forEach(l =>
      l.classList.add('etal-action-label--disabled')
    );
    return;
  }

  if (conforme) {
    // Temp OK → seulement Conforme
    rConforme.disabled  = false;
    rCalibrage.disabled = true;
    rRemplace.disabled  = true;
    elLblConforme .classList.remove('etal-action-label--disabled');
    elLblCalibrage.classList.add('etal-action-label--disabled');
    elLblRemplace .classList.add('etal-action-label--disabled');
    // Décocher les options devenues invalides
    if (rCalibrage.checked) rCalibrage.checked = false;
    if (rRemplace.checked)  rRemplace.checked  = false;
    // Auto-sélectionner Conforme
    rConforme.checked = true;
  } else {
    // Temp hors tolérance → Calibrage + Remplacé, pas Conforme
    rConforme.disabled  = true;
    rCalibrage.disabled = false;
    rRemplace.disabled  = false;
    elLblConforme .classList.add('etal-action-label--disabled');
    elLblCalibrage.classList.remove('etal-action-label--disabled');
    elLblRemplace .classList.remove('etal-action-label--disabled');
    if (rConforme.checked) rConforme.checked = false;
  }
}

elTemp.addEventListener('input', majBadgeConformite);
setActionsDisponibles(null);

// ── Messages ──────────────────────────────────────────────────
function showMsg(texte, type) {
  elMsg.textContent = texte;
  elMsg.className   = `etal-msg etal-msg--${type}`;
  elMsg.hidden      = false;
}
function hideMsg() { elMsg.hidden = true; }

// ── Soumission → redirect Screen 2 ───────────────────────────
elForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  hideMsg();

  const date      = elDate.value;
  const operateur = elOperateur.value;
  const thermoId  = elThermo.value;
  const tempStr   = elTemp.value;
  const actionEl  = elForm.querySelector('[name="action_corrective"]:checked');

  if (!date)     { showMsg('La date est obligatoire.',                        'erreur'); return; }
  if (!operateur){ showMsg('Sélectionnez un opérateur.',                      'erreur'); return; }
  if (!thermoId) { showMsg('Sélectionnez un thermomètre de référence.',       'erreur'); return; }
  if (tempStr === '') { showMsg('La température est obligatoire.',             'erreur'); return; }
  if (!actionEl) { showMsg('Sélectionnez une action corrective.',             'erreur'); return; }

  const payload = {
    date_etalonnage:     date,
    thermometre_ref_id:  parseInt(thermoId),
    temperature_mesuree: parseFloat(tempStr),
    action_corrective:   actionEl.value,
    operateur,
    commentaire: document.getElementById('etal-commentaire').value.trim() || null,
  };

  elSubmit.disabled         = true;
  elSubmitTexte.textContent = 'Envoi…';

  try {
    const result = await apiFetch('/api/etalonnage', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });

    // Si le thermo est validé (conforme ou remplacé) → Screen 2
    if (result.action_corrective === 'calibrage') {
      // Calibrage effectué mais pas encore remplacé → pas de comparaison possible
      showMsg(
        '🔧 Calibrage enregistré. Effectuez le calibrage puis créez un nouvel enregistrement pour passer aux comparaisons.',
        'succes'
      );
      elForm.reset();
      elDate.value = new Date().toISOString().slice(0, 10);
      elBadge.className = 'etal-conformite-badge etal-conformite-badge--vide';
      elBadge.textContent = '— Saisir une température';
      setActionsDisponibles(null);
      await chargerHistorique();
    } else {
      // Conforme ou Remplacé → on peut comparer les sondes
      location.href = `/etalonnage-comparaison.html?id=${result.id}`;
    }
  } catch (err) {
    showMsg(`Erreur : ${err.message}`, 'erreur');
    elSubmit.disabled         = false;
    elSubmitTexte.textContent = 'Enregistrer ✓';
  }
});

// ── Historique ────────────────────────────────────────────────
function labelAction(code) {
  return { conforme: '✅ Conforme', calibrage: '🔧 Calibrage', remplace: '🔄 Remplacé' }[code] ?? code;
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
        <td>${esc(r.thermometre_nom ?? '')}</td>
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
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Init ──────────────────────────────────────────────────────
chargerPersonnel();
chargerThermometres();
chargerHistorique();

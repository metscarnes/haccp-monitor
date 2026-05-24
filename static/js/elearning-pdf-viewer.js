/* ============================================================
   elearning-pdf-viewer.js — Visionneuse PDF + validation lecture
   Récupère module/pdf/titre depuis l'URL (query string),
   liste le personnel, et enregistre la complétion via API.
   ============================================================ */

(() => {
  'use strict';

  // ── Lecture des paramètres d'URL ────────────────────────────
  const params  = new URLSearchParams(location.search);
  const module  = params.get('module') || 'inconnu';
  const pdfUrl  = params.get('pdf')    || '';
  const titre   = params.get('titre')  || 'Formation';
  const retour  = params.get('retour') || `/elearning-${module.split('-')[0]}.html`;

  // ── Références DOM ──────────────────────────────────────────
  const elTitre        = document.getElementById('elearning-titre');
  const elRetour       = document.getElementById('btn-retour');
  const elHorloge      = document.getElementById('hub-horloge');
  const elIframe       = document.getElementById('pdf-iframe');
  const elSelect       = document.getElementById('select-personnel');
  const elBtnValider   = document.getElementById('btn-valider');
  const elDernier      = document.getElementById('dernier-lecteur');
  const elOverlay      = document.getElementById('overlay-success');
  const elOverlayMsg   = document.getElementById('overlay-message');
  const elBtnOverlayOk = document.getElementById('btn-overlay-ok');

  // ── Initialisation ──────────────────────────────────────────
  elTitre.textContent = titre.toUpperCase();
  document.title = `${titre} — Au Comptoir des Lilas`;
  elRetour.href = retour;
  // #toolbar=0 cache la toolbar Chrome dans certaines configs
  elIframe.src = pdfUrl ? `${pdfUrl}#toolbar=1&view=FitH` : 'about:blank';

  // ── Horloge ─────────────────────────────────────────────────
  function tickHorloge() {
    elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
      hour: '2-digit', minute: '2-digit'
    });
  }
  tickHorloge();
  setInterval(tickHorloge, 10000);

  // ── Activation du bouton selon sélection ────────────────────
  elSelect.addEventListener('change', () => {
    elBtnValider.disabled = !elSelect.value;
  });

  // ── Chargement du personnel ─────────────────────────────────
  async function chargerPersonnel() {
    try {
      const res = await fetch('/api/admin/personnel');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const personnes = await res.json();
      personnes
        .filter(p => p.actif !== false)
        .forEach(p => {
          const opt = document.createElement('option');
          opt.value = p.id;
          opt.textContent = [p.prenom, p.nom].filter(Boolean).join(' ');
          elSelect.appendChild(opt);
        });
    } catch (e) {
      console.warn('Personnel non chargé :', e);
    }
  }

  // ── Chargement de la dernière complétion (info) ─────────────
  async function chargerDerniereCompletion() {
    try {
      const res = await fetch(`/api/elearning/completions?module=${encodeURIComponent(module)}&limit=1`);
      if (!res.ok) return;
      const liste = await res.json();
      if (liste.length === 0) {
        elDernier.textContent = 'Aucune lecture enregistrée pour ce module.';
        elDernier.hidden = false;
        return;
      }
      const last = liste[0];
      const d    = new Date(last.date_completion);
      const dateStr = d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
      const heureStr = d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
      elDernier.textContent = `Dernière lecture : ${last.personnel_prenom} — ${dateStr} à ${heureStr}`;
      elDernier.hidden = false;
    } catch (e) {
      console.warn('Historique non chargé :', e);
    }
  }

  // ── Validation ──────────────────────────────────────────────
  async function valider() {
    const personnelId = parseInt(elSelect.value, 10);
    if (!personnelId) return;

    elBtnValider.disabled = true;
    elBtnValider.classList.add('elearning-btn-valider--loading');

    try {
      const res = await fetch('/api/elearning/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ module, personnel_id: personnelId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      afficherSucces(data);
    } catch (e) {
      toast('Erreur : ' + e.message);
      elBtnValider.disabled = false;
      elBtnValider.classList.remove('elearning-btn-valider--loading');
    }
  }

  function afficherSucces(completion) {
    const d = new Date(completion.date_completion);
    const heureStr = d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    elOverlayMsg.textContent =
      `${completion.personnel_prenom}, votre lecture a été enregistrée à ${heureStr}. ` +
      `La validation est désormais traçable.`;
    elOverlay.hidden = false;
  }

  elBtnOverlayOk.addEventListener('click', () => {
    location.href = retour;
  });

  elBtnValider.addEventListener('click', valider);

  // ── Toast d'erreur ──────────────────────────────────────────
  function toast(message) {
    const t = document.createElement('div');
    t.className = 'elearning-toast';
    t.textContent = message;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
  }

  // ── Démarrage ───────────────────────────────────────────────
  chargerPersonnel();
  chargerDerniereCompletion();
})();

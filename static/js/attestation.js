/* ============================================================
   attestation.js — Attestation de réussite d'un quiz
   Paramètres URL : ?quiz=<id>&personnel_id=<id>
   Source des données : /api/elearning/quiz/meilleur (meilleure note
   réelle côté serveur) + quizN.json (titre du module + thèmes abordés).
   ============================================================ */

(() => {
  'use strict';

  const params = new URLSearchParams(location.search);
  const quizId = parseInt(params.get('quiz') || '0', 10);
  const personnelId = parseInt(params.get('personnel_id') || '0', 10);
  // Permet un retour personnalisé (ex: vers l'historique)
  const retour = params.get('retour');

  const $ = (id) => document.getElementById(id);
  const elFeuille = $('att-feuille');

  if (retour) {
    const lien = $('att-retour');
    if (lien) lien.href = retour;
  }

  $('att-imprimer').addEventListener('click', () => window.print());

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function erreur(msg) {
    elFeuille.innerHTML = `<div class="att-erreur">⚠️ ${esc(msg)}</div>`;
  }

  async function getJSON(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  async function init() {
    if (!quizId || !personnelId) {
      erreur('Paramètres manquants pour générer l\'attestation.');
      return;
    }

    let best, quiz;
    try {
      [best, quiz] = await Promise.all([
        getJSON(`/api/elearning/quiz/meilleur?quiz_id=${quizId}&personnel_id=${personnelId}`),
        getJSON(`/static/docs/Quiz/quiz${quizId}.json`),
      ]);
    } catch (e) {
      erreur('Impossible de charger les données de l\'attestation.');
      return;
    }

    if (!best) {
      erreur('Aucun résultat enregistré pour cette personne sur ce quiz.');
      return;
    }
    if (!best.reussi) {
      erreur('Ce quiz n\'a pas encore été validé (score insuffisant).');
      return;
    }

    // Nom du participant
    $('att-nom').textContent = best.personnel_prenom || '—';

    // Module : « Quiz N — THÈME »
    const titreModule = quiz.theme
      ? `Quiz ${quiz.id} — ${quiz.theme}`
      : (quiz.titre || `Quiz ${quiz.id}`);
    $('att-module').textContent = titreModule;
    document.title = `Attestation — ${best.personnel_prenom} — ${titreModule}`;

    // Résultats
    $('att-pct').textContent = `${best.pourcentage} %`;
    $('att-score').textContent = `${best.score} / ${best.total}`;

    // Seuil affiché selon le quiz
    const seuil = quiz.seuil_validation || 80;
    const elSeuil = document.querySelector('.att-resultat-valeur--seuil');
    if (elSeuil) elSeuil.textContent = `≥ ${seuil} %`;

    // Date (de la meilleure tentative)
    const d = new Date(best.date_completion.replace(' ', 'T'));
    const dateStr = d.toLocaleDateString('fr-FR', {
      day: '2-digit', month: 'long', year: 'numeric',
    });
    $('att-date').textContent = dateStr;

    // Thèmes abordés
    const themes = quiz.themes_abordes || [];
    if (themes.length) {
      $('att-themes-liste').innerHTML = themes
        .map((t) => `<li>${esc(t)}</li>`)
        .join('');
      $('att-themes').hidden = false;
    }

    // Référence d'attestation (traçabilité)
    const refDate = d.toISOString().slice(0, 10).replace(/-/g, '');
    $('att-ref').textContent =
      `Référence : ATT-Q${quiz.id}-P${best.personnel_id}-${refDate} · ` +
      `Au Comptoir des Lilas — Plan de Maîtrise Sanitaire`;
  }

  init();
})();

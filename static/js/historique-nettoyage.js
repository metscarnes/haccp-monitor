'use strict';
/* ============================================================
   historique-nettoyage.js
   Affiche l'historique des validations de nettoyage groupées
   par arborescence : Année → Mois → Semaine ISO → Jours
   ============================================================ */

const elMessage  = document.getElementById('hn-message');
const elContenu  = document.getElementById('hn-contenu');

// ── Chargement ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', charger);

async function charger() {
  try {
    const res = await fetch('/api/nettoyage/historique');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    afficher(data);
  } catch (err) {
    elMessage.innerHTML = `
      <div class="hn-message-icone">⚠️</div>
      <div class="hn-message-texte">Erreur : ${err.message}</div>`;
  }
}

// ── Rendu de l'arborescence ──────────────────────────────────
function afficher(data) {
  if (!data.length) {
    elMessage.innerHTML = `
      <div class="hn-message-icone">📋</div>
      <div class="hn-message-texte">Aucune validation enregistrée pour l'instant.</div>`;
    return;
  }

  elMessage.hidden = true;
  elContenu.hidden = false;
  elContenu.innerHTML = '';

  const anneeActuelle = new Date().getFullYear();
  const moisActuel    = new Date().getMonth() + 1; // 1-12

  data.forEach((bloc_annee, idx_annee) => {
    const divAnnee = document.createElement('div');
    divAnnee.className = 'hn-annee';
    const ouvertAnnee = bloc_annee.annee === anneeActuelle;
    if (ouvertAnnee) divAnnee.classList.add('ouvert');

    // Nombre total de jours validés dans l'année
    const nbJoursAnnee = bloc_annee.mois.reduce(
      (s, m) => s + m.semaines.reduce((ss, sem) => ss + sem.jours.length, 0), 0
    );

    divAnnee.innerHTML = `
      <button class="hn-annee-titre" aria-expanded="${ouvertAnnee}">
        📅 ${bloc_annee.annee}
        <span style="font-size:14px;font-weight:400;opacity:.7;">${nbJoursAnnee} jour(s) validé(s)</span>
        <span class="hn-annee-chevron">▼</span>
      </button>
      <div class="hn-annee-corps"></div>`;

    const btnAnnee  = divAnnee.querySelector('.hn-annee-titre');
    const corpsAnnee = divAnnee.querySelector('.hn-annee-corps');

    btnAnnee.addEventListener('click', () => {
      const est_ouvert = divAnnee.classList.toggle('ouvert');
      btnAnnee.setAttribute('aria-expanded', est_ouvert);
    });

    // ── Mois ────────────────────────────────────────────────
    bloc_annee.mois.forEach(bloc_mois => {
      const divMois = document.createElement('div');
      divMois.className = 'hn-mois';
      const ouvertMois = ouvertAnnee && bloc_mois.numero === moisActuel;
      if (ouvertMois) divMois.classList.add('ouvert');

      const nbJoursMois = bloc_mois.semaines.reduce((s, sem) => s + sem.jours.length, 0);

      divMois.innerHTML = `
        <button class="hn-mois-titre" aria-expanded="${ouvertMois}">
          🗓️ ${bloc_mois.nom}
          <span class="hn-mois-badge">${nbJoursMois} jour(s)</span>
          <span class="hn-mois-chevron">▼</span>
        </button>
        <div class="hn-mois-corps"></div>`;

      const btnMois   = divMois.querySelector('.hn-mois-titre');
      const corpsMois = divMois.querySelector('.hn-mois-corps');

      btnMois.addEventListener('click', () => {
        const est_ouvert = divMois.classList.toggle('ouvert');
        btnMois.setAttribute('aria-expanded', est_ouvert);
      });

      // ── Semaines ──────────────────────────────────────────
      bloc_mois.semaines.forEach(bloc_sem => {
        const divSem = document.createElement('div');
        divSem.className = 'hn-semaine';

        // Ouvrir la semaine la plus récente du mois actuel
        const estPremiereSemaine = ouvertMois && bloc_mois.semaines.indexOf(bloc_sem) === 0;
        if (estPremiereSemaine) divSem.classList.add('ouvert');

        const labelSem = `Semaine ${bloc_sem.numero}`;
        const nbJoursSem = bloc_sem.jours.length;

        divSem.innerHTML = `
          <button class="hn-semaine-titre" aria-expanded="${estPremiereSemaine}">
            <span class="hn-semaine-label">${labelSem}</span>
            <span class="hn-semaine-nb">${nbJoursSem} jour(s)</span>
            <span class="hn-semaine-chevron">▼</span>
          </button>
          <div class="hn-semaine-corps"></div>`;

        const btnSem   = divSem.querySelector('.hn-semaine-titre');
        const corpsSem = divSem.querySelector('.hn-semaine-corps');

        btnSem.addEventListener('click', () => {
          const est_ouvert = divSem.classList.toggle('ouvert');
          btnSem.setAttribute('aria-expanded', est_ouvert);
        });

        // ── Jours ────────────────────────────────────────────
        bloc_sem.jours.forEach(jour => {
          const divJour = document.createElement('div');
          divJour.className = 'hn-jour';

          const [annee, mois, day] = jour.date.split('-');
          const dateFormatee = `${jour.jour_nom} ${parseInt(day)}/${parseInt(mois)}/${annee}`;
          const ops = jour.operateurs.join(', ') || '—';

          divJour.innerHTML = `
            <div class="hn-jour-icone">✅</div>
            <div class="hn-jour-info">
              <div class="hn-jour-date">${dateFormatee}</div>
              <div class="hn-jour-ops">Validé par : ${ops}</div>
            </div>
            <div class="hn-jour-badge">${jour.nb_taches} tâche(s)</div>`;

          corpsSem.appendChild(divJour);
        });

        corpsMois.appendChild(divSem);
      });

      corpsAnnee.appendChild(divMois);
    });

    elContenu.appendChild(divAnnee);
  });
}

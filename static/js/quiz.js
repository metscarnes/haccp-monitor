/* ============================================================
   quiz.js — Quiz interactif e-learning hygiène
   Déroulé question par question :
     1. choix du participant
     2. pour chaque question : indice (bouton), réponse,
        verdict, correction détaillée (accordéon), explication (accordéon)
     3. écran final : score, % et envoi du résultat au backend
   ============================================================ */

(() => {
  'use strict';

  const SEUIL = 80; // % de réussite

  // ── Paramètres d'URL ────────────────────────────────────────
  const params = new URLSearchParams(location.search);
  const quizId = parseInt(params.get('quiz') || '1', 10);

  // ── Références DOM ──────────────────────────────────────────
  const $ = (id) => document.getElementById(id);
  const elHorloge   = $('hub-horloge');
  const elTitre     = $('quiz-titre');
  const elProgress  = $('quiz-progress-bar');

  const ecranIntro    = $('ecran-intro');
  const ecranQuestion = $('ecran-question');
  const ecranResultat = $('ecran-resultat');
  const ecranErreur   = $('ecran-erreur');

  // Intro
  const elIntroTitre  = $('intro-titre');
  const elIntroSub    = $('intro-sub');
  const elSelect      = $('select-personnel');
  const elIntroDernier= $('intro-dernier');
  const elBtnDemarrer = $('btn-demarrer');

  // Question
  const elQCompteur   = $('q-compteur');
  const elQScore      = $('q-score');
  const elQEnonce     = $('q-enonce');
  const elQOptions    = $('q-options');
  const elBtnIndice   = $('btn-indice');
  const elQIndice     = $('q-indice');
  const elQFeedback   = $('q-feedback');
  const elQVerdict    = $('q-verdict');
  const elBtnCorrection = $('btn-correction');
  const elQCorrection = $('q-correction');
  const elBtnExplication = $('btn-explication');
  const elQExplication= $('q-explication');
  const elBtnSuivant  = $('btn-suivant');

  // Résultat
  const elResultatEmoji = $('resultat-emoji');
  const elResultatTitre = $('resultat-titre');
  const elScoreCercle   = $('score-cercle');
  const elScorePct      = $('score-pct');
  const elScoreFrac     = $('score-frac');
  const elResultatMsg   = $('resultat-msg');
  const elResultatTrace = $('resultat-trace');
  const elBtnRecommencer= $('btn-recommencer');

  const elErreurMsg = $('erreur-msg');

  // ── État ────────────────────────────────────────────────────
  let quiz = null;
  let qIndex = 0;
  let score = 0;
  let personnelId = null;
  let personnelPrenom = '';
  let repondu = false;

  // ── Horloge ─────────────────────────────────────────────────
  function tickHorloge() {
    if (!elHorloge) return;
    elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
      hour: '2-digit', minute: '2-digit',
    });
  }
  tickHorloge();
  setInterval(tickHorloge, 10000);

  // ── Navigation entre écrans ─────────────────────────────────
  function afficherEcran(el) {
    [ecranIntro, ecranQuestion, ecranResultat, ecranErreur].forEach((e) => {
      e.hidden = e !== el;
    });
  }

  // ── Échappement HTML ────────────────────────────────────────
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  // Texte multi-paragraphes -> <p>…</p>
  function paragraphes(txt) {
    return String(txt || '')
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean)
      .map((l) => `<p>${esc(l)}</p>`)
      .join('');
  }

  // ── Chargement du quiz (JSON) ───────────────────────────────
  async function chargerQuiz() {
    try {
      const res = await fetch(`/static/docs/Quiz/quiz${quizId}.json`);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      quiz = await res.json();
    } catch (e) {
      elErreurMsg.textContent =
        `Le quiz ${quizId} n'est pas encore disponible.`;
      afficherEcran(ecranErreur);
      return;
    }
    initIntro();
  }

  // ── Chargement du personnel ─────────────────────────────────
  async function chargerPersonnel() {
    try {
      const res = await fetch('/api/admin/personnel');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const personnes = await res.json();
      personnes
        .filter((p) => p.actif !== false)
        .forEach((p) => {
          const opt = document.createElement('option');
          opt.value = p.id;
          opt.textContent = p.prenom;
          elSelect.appendChild(opt);
        });
    } catch (e) {
      console.warn('Personnel non chargé :', e);
    }
  }

  // ── Dernier résultat (info intro) ───────────────────────────
  async function chargerDernierResultat() {
    try {
      const res = await fetch(`/api/elearning/quiz/resultats?quiz_id=${quizId}&limit=1`);
      if (!res.ok) return;
      const liste = await res.json();
      if (!liste.length) return;
      const r = liste[0];
      const d = new Date(r.date_completion);
      const dateStr = d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
      const verdict = r.reussi ? 'réussi ✅' : 'échoué ❌';
      elIntroDernier.textContent =
        `Dernier passage : ${r.personnel_prenom} — ${r.pourcentage} % (${verdict}) le ${dateStr}`;
      elIntroDernier.hidden = false;
    } catch (e) {
      console.warn('Historique non chargé :', e);
    }
  }

  // ── Écran intro ─────────────────────────────────────────────
  function initIntro() {
    const titre = `Quiz ${quiz.id} — ${quiz.theme || ''}`.trim();
    elTitre.textContent = `QUIZ ${quiz.id}`;
    document.title = `${titre} — Au Comptoir des Lilas`;
    elIntroTitre.textContent = titre;
    const n = quiz.questions.length;
    const seuil = quiz.seuil_validation || SEUIL;
    elIntroSub.textContent = `${n} questions · réussite à partir de ${seuil} %`;
    afficherEcran(ecranIntro);
  }

  elSelect.addEventListener('change', () => {
    elBtnDemarrer.disabled = !elSelect.value;
  });

  elBtnDemarrer.addEventListener('click', () => {
    if (!elSelect.value) return;
    personnelId = parseInt(elSelect.value, 10);
    personnelPrenom = elSelect.options[elSelect.selectedIndex].textContent;
    qIndex = 0;
    score = 0;
    afficherEcran(ecranQuestion);
    afficherQuestion();
  });

  // ── Affichage d'une question ────────────────────────────────
  function afficherQuestion() {
    repondu = false;
    const q = quiz.questions[qIndex];
    const total = quiz.questions.length;

    elQCompteur.textContent = `Question ${qIndex + 1} / ${total}`;
    elQScore.textContent = `Score : ${score}`;
    elQEnonce.textContent = q.enonce;

    // Progression
    elProgress.style.width = `${(qIndex / total) * 100}%`;

    // Options
    elQOptions.innerHTML = '';
    ['A', 'B', 'C', 'D'].forEach((lettre) => {
      if (!q.options[lettre]) return;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'quiz-option';
      btn.dataset.lettre = lettre;
      btn.innerHTML =
        `<span class="quiz-option-lettre">${lettre}</span>` +
        `<span class="quiz-option-texte">${esc(q.options[lettre])}</span>` +
        `<span class="quiz-option-marque" aria-hidden="true"></span>`;
      btn.addEventListener('click', () => repondre(lettre));
      elQOptions.appendChild(btn);
    });

    // Indice (caché, bouton réarmé)
    elQIndice.textContent = q.indice || '';
    elQIndice.hidden = true;
    elBtnIndice.hidden = !q.indice;
    elBtnIndice.disabled = false;
    elBtnIndice.textContent = '💡 Afficher un indice';

    // Feedback masqué + accordéons repliés
    elQFeedback.hidden = true;
    replierAccordeon(elBtnCorrection, elQCorrection);
    replierAccordeon(elBtnExplication, elQExplication);

    scrollHaut();
  }

  function scrollHaut() {
    const main = document.querySelector('.quiz-main');
    if (main) main.scrollTop = 0;
  }

  // ── Indice ──────────────────────────────────────────────────
  elBtnIndice.addEventListener('click', () => {
    elQIndice.hidden = false;
    elBtnIndice.disabled = true;
    elBtnIndice.textContent = '💡 Indice affiché';
  });

  // ── Réponse ─────────────────────────────────────────────────
  function repondre(lettre) {
    if (repondu) return;
    repondu = true;
    const q = quiz.questions[qIndex];
    const bonne = q.bonne_reponse;
    const correct = lettre === bonne;
    if (correct) score++;

    // Marquer les options
    elQOptions.querySelectorAll('.quiz-option').forEach((btn) => {
      btn.disabled = true;
      const l = btn.dataset.lettre;
      const marque = btn.querySelector('.quiz-option-marque');
      if (l === bonne) {
        btn.classList.add('quiz-option--correct');
        marque.textContent = '✓';
      } else if (l === lettre) {
        btn.classList.add('quiz-option--wrong');
        marque.textContent = '✗';
      } else {
        btn.classList.add('quiz-option--dim');
      }
    });

    elBtnIndice.disabled = true;

    // Verdict
    elQVerdict.className = 'quiz-verdict ' + (correct ? 'quiz-verdict--ok' : 'quiz-verdict--ko');
    elQVerdict.textContent = correct
      ? '✅ Bonne réponse !'
      : `❌ Mauvaise réponse — la bonne réponse était ${bonne}.`;

    // Correction détaillée (par option)
    elQCorrection.innerHTML = ['A', 'B', 'C', 'D']
      .filter((l) => q.corrections[l])
      .map((l) => {
        const cls = l === bonne ? ' quiz-corr-item--bonne' : '';
        return (
          `<div class="quiz-corr-item${cls}">` +
          `<span class="quiz-corr-lettre">${l}.</span>` +
          `<span>${esc(q.corrections[l])}</span>` +
          `</div>`
        );
      })
      .join('');

    // Explication
    elQExplication.innerHTML = paragraphes(q.explication);

    // Texte du dernier bouton
    elBtnSuivant.textContent =
      qIndex + 1 < quiz.questions.length ? 'Question suivante →' : 'Voir mon résultat →';

    elQScore.textContent = `Score : ${score}`;
    elQFeedback.hidden = false;
    // amener le verdict dans le champ de vision
    elQFeedback.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // ── Accordéons ──────────────────────────────────────────────
  function basculerAccordeon(btn, body) {
    const ouvert = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', String(!ouvert));
    body.hidden = ouvert;
  }
  function replierAccordeon(btn, body) {
    btn.setAttribute('aria-expanded', 'false');
    body.hidden = true;
  }
  elBtnCorrection.addEventListener('click', () => basculerAccordeon(elBtnCorrection, elQCorrection));
  elBtnExplication.addEventListener('click', () => basculerAccordeon(elBtnExplication, elQExplication));

  // ── Question suivante / résultat ────────────────────────────
  elBtnSuivant.addEventListener('click', () => {
    if (qIndex + 1 < quiz.questions.length) {
      qIndex++;
      afficherQuestion();
    } else {
      terminer();
    }
  });

  // ── Écran final + envoi du résultat ─────────────────────────
  async function terminer() {
    const total = quiz.questions.length;
    const pct = Math.round((score * 100) / total);
    const seuil = quiz.seuil_validation || SEUIL;
    const reussi = pct >= seuil;

    elProgress.style.width = '100%';

    elScorePct.textContent = `${pct} %`;
    elScoreFrac.textContent = `${score} / ${total}`;
    elScoreCercle.classList.toggle('quiz-score-cercle--echec', !reussi);

    if (reussi) {
      elResultatEmoji.textContent = pct === 100 ? '🏆' : '🎉';
      elResultatTitre.textContent = 'Quiz validé !';
      elResultatMsg.textContent =
        `Bravo ${personnelPrenom}, vous avez obtenu ${pct} % ` +
        `(seuil de réussite : ${seuil} %).`;
    } else {
      elResultatEmoji.textContent = '💪';
      elResultatTitre.textContent = 'Quiz non validé';
      elResultatMsg.textContent =
        `${personnelPrenom}, vous avez obtenu ${pct} %. ` +
        `Il faut au moins ${seuil} % pour valider. Recommencez pour progresser !`;
    }

    afficherEcran(ecranResultat);

    // Score parfait → pluie de confettis sur tout l'écran
    if (score === total) {
      lancerConfettis();
    }

    // Enregistrement backend (traçabilité / future attestation)
    try {
      const res = await fetch('/api/elearning/quiz/resultats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quiz_id: quiz.id,
          personnel_id: personnelId,
          score: score,
          total: total,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const d = new Date(data.date_completion);
        const dateStr = d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
        const heureStr = d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
        elResultatTrace.textContent = `Résultat enregistré le ${dateStr} à ${heureStr}.`;
        elResultatTrace.hidden = false;
      } else {
        throw new Error('HTTP ' + res.status);
      }
    } catch (e) {
      console.warn('Résultat non enregistré :', e);
      toast("Résultat non enregistré (hors ligne ?)");
    }
  }

  // ── Recommencer ─────────────────────────────────────────────
  elBtnRecommencer.addEventListener('click', () => {
    qIndex = 0;
    score = 0;
    afficherEcran(ecranQuestion);
    afficherQuestion();
  });

  // ── Confettis (score parfait 10/10) ─────────────────────────
  function lancerConfettis() {
    const canvas = document.createElement('canvas');
    canvas.className = 'quiz-confettis';
    document.body.appendChild(canvas);
    const ctx = canvas.getContext('2d');

    let W, H;
    function dimensionner() {
      W = canvas.width = window.innerWidth;
      H = canvas.height = window.innerHeight;
    }
    dimensionner();
    window.addEventListener('resize', dimensionner);

    const couleurs = ['#D4A574', '#6B3A1F', '#2D7D46', '#E8913A', '#C93030', '#F5ECD7'];
    const N = 160;
    const pieces = [];
    for (let i = 0; i < N; i++) {
      pieces.push({
        x: Math.random() * W,
        y: Math.random() * -H,          // démarrent au-dessus de l'écran
        w: 6 + Math.random() * 8,
        h: 8 + Math.random() * 10,
        couleur: couleurs[(Math.random() * couleurs.length) | 0],
        vy: 1.8 + Math.random() * 3.2,  // vitesse de chute
        vx: -1.5 + Math.random() * 3,   // dérive latérale
        rot: Math.random() * Math.PI,
        vrot: -0.15 + Math.random() * 0.3,
        oscill: Math.random() * Math.PI * 2,
      });
    }

    const debut = performance.now();
    const DUREE = 5000; // ms

    function frame(now) {
      const ecoule = now - debut;
      ctx.clearRect(0, 0, W, H);
      let vivants = 0;
      for (const p of pieces) {
        p.oscill += 0.05;
        p.x += p.vx + Math.sin(p.oscill) * 0.8;
        p.y += p.vy;
        p.rot += p.vrot;
        if (p.y < H + 20) vivants++;

        // fondu sur la dernière seconde
        ctx.globalAlpha = ecoule > DUREE - 1000
          ? Math.max(0, (DUREE - ecoule) / 1000)
          : 1;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.fillStyle = p.couleur;
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.restore();
      }
      if (ecoule < DUREE && vivants > 0) {
        requestAnimationFrame(frame);
      } else {
        window.removeEventListener('resize', dimensionner);
        canvas.remove();
      }
    }
    requestAnimationFrame(frame);
  }

  // ── Toast ───────────────────────────────────────────────────
  function toast(msg) {
    const t = document.createElement('div');
    t.className = 'quiz-toast';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
  }

  // ── Démarrage ───────────────────────────────────────────────
  chargerQuiz();
  chargerPersonnel();
  chargerDernierResultat();
})();

'use strict';
/* ============================================================
   hub.js — Accueil Hub Phase 2 HACCP
   Au Comptoir des Lilas — Mets Carnés Holding

   Responsabilités :
   - Horloge temps réel (1 s)
   - Chargement des données depuis 4 endpoints (toutes les 30 s)
   - Mise à jour des 4 tuiles avec statut coloré
   - Bandeau d'alerte si tâches en retard
   - Retour accueil (reload) après 5 min d'inactivité
   ============================================================ */

const REFRESH_MS  = 30_000;          // actualisation des tuiles
const INACT_MS    = 5 * 60 * 1000;   // inactivité → reload
const SNOOZE_MS   = 2 * 60 * 60 * 1000;
const SNOOZE_KEY  = 'hub_popup_snooze_until';

// ── Références DOM ────────────────────────────────────────────
const elHorloge          = document.getElementById('hub-horloge');
const elBandeauConnexion = document.getElementById('hub-bandeau-connexion');

// ── Horloge ───────────────────────────────────────────────────
function majHorloge() {
  const now  = new Date();
  const date = now.toLocaleDateString('fr-FR', {
    weekday: 'short', day: 'numeric', month: 'long',
  });
  const heure = now.toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
  elHorloge.textContent = `${date} — ${heure}`;
}
setInterval(majHorloge, 1000);
majHorloge();

// ── Inactivité ────────────────────────────────────────────────
let timerInact;

function resetInact() {
  clearTimeout(timerInact);
  // Pas de rechargement en pleine personnalisation : le rangement serait perdu.
  timerInact = setTimeout(() => { if (!enEdition) location.reload(); }, INACT_MS);
}

['touchstart', 'click', 'keydown', 'mousemove', 'scroll'].forEach(ev =>
  document.addEventListener(ev, resetInact, { passive: true })
);
resetInact();

// ── Fetch helper ──────────────────────────────────────────────
async function apiFetch(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status} — ${url}`);
  return res.json();
}

// ── Helpers d'affichage ───────────────────────────────────────

/** Dot de statut coloré en HTML */
function dot(etat) {
  return `<span class="hub-dot hub-dot--${etat}" aria-hidden="true"></span>`;
}

/**
 * Applique l'état visuel d'une tuile.
 * @param {string} idTuile  — id de l'élément <a>
 * @param {string} etat     — "ok" | "attention" | "alerte" | "erreur" | "chargement"
 * @param {string} html     — contenu HTML du statut
 */
function setTuile(idTuile, etat, html) {
  const tuile  = document.getElementById(idTuile);
  const statut = document.getElementById('statut-' + idTuile.replace('tuile-', ''));
  tuile.className  = `hub-tuile hub-tuile--${etat}`;
  statut.innerHTML = html;
}

// ── Tuile — Fabrication ───────────────────────────────────────
// (tuile absente du Hub actuel : sans garde, l'erreur interrompait charger()
// avant la mise à jour des tuiles suivantes)
function afficherEtiquettes(alertes) {
  const tuile = document.getElementById('tuile-etiquettes');
  if (tuile) tuile.className = 'hub-tuile hub-tuile--ok';
}

// ── Tuile — Étiquettes prix : étiquettes à refaire après un changement de prix ──
function afficherPrixEtiquettes(data) {
  const n = data?.total ?? 0;
  const tuile = document.getElementById('tuile-prix-etiquettes');
  if (n > 0) {
    setTuile('tuile-prix-etiquettes', 'attention',
      `${dot('attention')} ${n} étiquette${n > 1 ? 's' : ''} à refaire`);
    tuile.href = '/prix-etiquettes.html?reimprimer=1';   // ouvre directement la liste
  } else {
    setTuile('tuile-prix-etiquettes', 'ok', `${dot('ok')} Étiquettes à jour`);
    tuile.href = '/prix-etiquettes.html';
  }
}

// ── Tuile — Réception ─────────────────────────────────────────
function afficherReception(receptions) {
  if (!receptions || receptions.length === 0) {
    setTuile('tuile-reception', 'chargement',
      `${dot('gris')} Aucune réception récente`
    );
    return;
  }

  const d    = receptions[0];
  const date = new Date(d.date_reception).toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'short',
  });
  const nb   = d.nb_lignes ?? '—';
  const nc   = (d.nb_nc > 0) || (d.conforme === 0);

  if (nc) {
    setTuile('tuile-reception', 'attention',
      `${dot('attention')} ${date}&ensp;·&ensp;${nb} produit${nb > 1 ? 's' : ''}&ensp;·&ensp;NC`
    );
  } else {
    setTuile('tuile-reception', 'ok',
      `${dot('ok')} ${date}&ensp;·&ensp;${nb} produit${nb > 1 ? 's' : ''}&ensp;·&ensp;OK`
    );
  }
}

// ── Chargement principal ──────────────────────────────────────
async function charger() {
  const [rDlc, rRecep, rPrix] = await Promise.allSettled([
    apiFetch('/api/etiquettes/alertes-dlc'),
    apiFetch('/api/receptions?limit=1'),
    apiFetch('/api/prix-etiquettes/a-reimprimer/compte'),
  ]);

  // Information secondaire : en cas d'échec, la tuile garde son libellé par défaut.
  if (rPrix.status === 'fulfilled') afficherPrixEtiquettes(rPrix.value);

  const toutEchoue = [rDlc, rRecep]
    .every(r => r.status === 'rejected');
  elBandeauConnexion.hidden = !toutEchoue;

  if (rDlc.status === 'fulfilled') {
    afficherEtiquettes(rDlc.value);
  } else {
    const tuile = document.getElementById('tuile-etiquettes');
    if (tuile) tuile.className = 'hub-tuile hub-tuile--erreur';
  }

  if (rRecep.status === 'fulfilled') {
    afficherReception(rRecep.value);
  } else {
    setTuile('tuile-reception', 'erreur', '⚠ Connexion perdue');
  }
}

// ── Popup tâches HACCP (cloche header) ────────────────────────
const elCloche       = document.getElementById('hub-cloche');
const elClocheBadge  = document.getElementById('hub-cloche-badge');
const elPopupOverlay = document.getElementById('hub-popup-overlay');
const elPopupFermer  = document.getElementById('hub-popup-fermer');
const elPopupSnooze  = document.getElementById('hub-popup-snooze');
const elListeAuj     = document.getElementById('hub-popup-aujourdhui');
const elListeAVenir  = document.getElementById('hub-popup-avenir');

let popupDejaOuvert = false;   // évite la réouverture auto à chaque refresh
let aDesNonMasquables = false; // ≥1 tâche prioritaire non-masquable présente

function estEnSnooze() {
  const until = Number(localStorage.getItem(SNOOZE_KEY) ?? 0);
  return Date.now() < until;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function ligneTacheHtml(t) {
  const classes = ['hub-popup-item'];
  if (t.etat === 'en_retard') classes.push('hub-popup-item--retard');
  if (t.non_masquable)        classes.push('hub-popup-item--priorite');
  return `
    <li class="${classes.join(' ')}">
      <a href="${t.url}" class="hub-popup-lien">
        <span class="hub-popup-icone" aria-hidden="true">${t.icone ?? '📋'}</span>
        <span class="hub-popup-texte">
          <span class="hub-popup-libelle">${escHtml(t.libelle)}</span>
          <span class="hub-popup-detail">${escHtml(t.detail ?? '')}</span>
        </span>
        <span class="hub-popup-fleche" aria-hidden="true">›</span>
      </a>
    </li>`;
}

function listeVideHtml(msg) {
  return `<li class="hub-popup-vide">${escHtml(msg)}</li>`;
}

function majBoutonSnooze() {
  // Une tâche prioritaire non-masquable interdit le snooze.
  if (aDesNonMasquables) {
    elPopupSnooze.textContent = '⛔ Alerte prioritaire — non masquable';
    elPopupSnooze.classList.remove('hub-popup-snooze--actif');
    elPopupSnooze.disabled = true;
    return;
  }
  elPopupSnooze.disabled = false;
  if (estEnSnooze()) {
    elPopupSnooze.textContent = '🔔 Réafficher l\'alerte';
    elPopupSnooze.classList.add('hub-popup-snooze--actif');
  } else {
    elPopupSnooze.textContent = '🔕 Ne plus afficher pendant 2h';
    elPopupSnooze.classList.remove('hub-popup-snooze--actif');
  }
}

function ouvrirPopup() {
  majBoutonSnooze();
  elPopupOverlay.hidden = false;
  document.body.style.overflow = 'hidden';
}

function fermerPopup() {
  elPopupOverlay.hidden = true;
  document.body.style.overflow = '';
}

function basculerSnooze() {
  // Impossible de masquer tant qu'une tâche prioritaire non-masquable est présente.
  if (aDesNonMasquables) return;
  if (estEnSnooze()) {
    localStorage.removeItem(SNOOZE_KEY);
    majBoutonSnooze();
  } else {
    localStorage.setItem(SNOOZE_KEY, String(Date.now() + SNOOZE_MS));
    fermerPopup();
  }
}

elCloche.addEventListener('click', ouvrirPopup);
elPopupFermer.addEventListener('click', fermerPopup);
elPopupSnooze.addEventListener('click', basculerSnooze);
elPopupOverlay.addEventListener('click', (e) => {
  if (e.target === elPopupOverlay) fermerPopup();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !elPopupOverlay.hidden) fermerPopup();
});

async function chargerResumeTaches() {
  let data;
  try {
    data = await apiFetch('/api/hub/taches-resume');
  } catch {
    elCloche.hidden = true;
    return;
  }

  const auj    = data.aujourd_hui ?? [];
  const avenir = data.a_venir     ?? [];
  const total  = auj.length + avenir.length;

  // Tâche(s) prioritaire(s) non-masquable(s) : court-circuitent le snooze.
  aDesNonMasquables = auj.some(t => t.non_masquable);

  // Cloche : visible uniquement s'il y a quelque chose à signaler
  elCloche.hidden = (total === 0);
  if (total > 0) {
    elClocheBadge.textContent = String(total);
    elClocheBadge.hidden = false;
    elCloche.classList.toggle('hub-btn-cloche--alerte', auj.length > 0);
  }

  // Remplissage des listes
  elListeAuj.innerHTML = auj.length
    ? auj.map(ligneTacheHtml).join('')
    : listeVideHtml('✓ Tout est à jour aujourd\'hui');

  elListeAVenir.innerHTML = avenir.length
    ? avenir.map(ligneTacheHtml).join('')
    : listeVideHtml('Aucune échéance dans les 14 prochains jours');

  // Si le popup est déjà ouvert, rafraîchir l'état du bouton snooze.
  if (!elPopupOverlay.hidden) majBoutonSnooze();

  // Ouverture automatique :
  // - une tâche non-masquable force l'ouverture, MÊME en snooze, à chaque refresh ;
  // - sinon, ouverture une seule fois au premier chargement si pas en snooze.
  if (aDesNonMasquables) {
    ouvrirPopup();
  } else if (!popupDejaOuvert && total > 0) {
    popupDejaOuvert = true;
    if (!estEnSnooze()) ouvrirPopup();
  }
}

// ── Personnaliser l'accueil (administrateur) ──────────────────
// Les tuiles d'origine sont dans hub.html ; celles-ci peuvent être ajoutées.
// La disposition (ordre + tuiles affichées) est enregistrée sur le serveur :
// une seule pour la boutique, tous les appareils affichent le même Hub.
const TUILES_EN_PLUS = [
  { id: 'pilotage-ca',         href: '/pilotage-ca.html',         icone: '💶', titre: "CHIFFRE D'AFFAIRES",  statut: 'Saisie & comparatif' },
  { id: 'pilotage',            href: '/pilotage.html',            icone: '📊', titre: 'PILOTAGE',            statut: 'CA, inventaire, marge' },
  { id: 'inventaire-valorise', href: '/inventaire-valorise.html', icone: '💰', titre: 'INVENTAIRE VALORISÉ', statut: 'Stock en €' },
  { id: 'marge',               href: '/marge.html',               icone: '📈', titre: 'MARGE',               statut: 'Marge brute' },
  { id: 'fabrication',         href: '/etiquettes.html',          icone: '🔪', titre: 'FABRICATION',         statut: 'Étiquettes fabrication' },
  { id: 'cuisson',             href: '/cuisson.html',             icone: '🔥', titre: 'CUISSON',             statut: 'Contrôle ≥ 75 °C' },
  { id: 'refroidissement',     href: '/refroidissement.html',     icone: '❄️', titre: 'REFROIDISSEMENT',     statut: '≤ 10 °C en ≤ 2 h' },
  { id: 'catalogue-vente',     href: '/catalogue-vente.html',     icone: '🏷️', titre: 'CATALOGUE VENTE',     statut: 'Produits finis' },
  { id: 'catalogue',           href: '/catalogue.html',           icone: '📚', titre: 'CATALOGUE',           statut: 'Produits & matières premières' },
  { id: 'nettoyage',           href: '/nettoyage.html',           icone: '🧹', titre: 'NETTOYAGE',           statut: 'Plan de nettoyage' },
  { id: 'temperatures',        href: '/',                         icone: '🌡️', titre: 'TEMPÉRATURES',        statut: 'Enceintes froides' },
  { id: 'etalonnage',          href: '/etalonnage.html',          icone: '🌡️', titre: 'ÉTALONNAGE',          statut: 'Thermomètres' },
  { id: 'nuisibles',           href: '/nuisibles.html',           icone: '🐛', titre: 'NUISIBLES',           statut: 'Contrôle des pièges' },
  { id: 'elearning',           href: '/elearning.html',           icone: '🎓', titre: 'E-LEARNING',          statut: 'Formation hygiène' },
  { id: 'classeur-pms',        href: '/classeur-pms.html',        icone: '📂', titre: 'CLASSEUR PMS',        statut: 'Procédures & traçabilité' },
];

const elGrille          = document.getElementById('hub-grille');
const elBtnPerso        = document.getElementById('hub-btn-perso');
const elBarre           = document.getElementById('hub-edition-barre');
const elStatutEdition   = document.getElementById('hub-edition-statut');
const elMdpOverlay      = document.getElementById('hub-mdp-overlay');
const elMdpForm         = document.getElementById('hub-mdp-form');
const elMdp             = document.getElementById('hub-mdp');
const elMdpErreur       = document.getElementById('hub-mdp-erreur');
const elAjoutOverlay    = document.getElementById('hub-ajout-overlay');
const elAjoutListe      = document.getElementById('hub-ajout-liste');

const idDe = (tuile) => tuile.id.replace(/^tuile-/, '');
const toutesLesTuiles = () => [...elGrille.querySelectorAll('.hub-tuile')];
const TUILES_ORIGINE = toutesLesTuiles().map(idDe);   // ordre de hub.html

let enEdition = false;
let jetonDispo = null;          // autorisation admin (15 min), en mémoire seulement
let minuteurJeton = null;
let apresDeverrouillage = null; // action à reprendre une fois le mot de passe donné
let dispositionChargee = { personnalisee: false, ordre: [], connues: [] };

// Les tuiles en plus existent toujours dans la page (cachées si non affichées).
for (const t of TUILES_EN_PLUS) {
  const a = document.createElement('a');
  a.className = 'hub-tuile';
  a.id = 'tuile-' + t.id;
  a.href = t.href;
  a.setAttribute('aria-label', t.titre);
  a.hidden = true;
  a.innerHTML = `
    <div class="hub-tuile-icone" aria-hidden="true">${t.icone}</div>
    <div class="hub-tuile-titre">${escHtml(t.titre)}</div>
    <div class="hub-tuile-statut">${escHtml(t.statut)}</div>`;
  elGrille.appendChild(a);
}

// Bouton ✕ (retirer), visible seulement en mode personnalisation.
for (const tuile of toutesLesTuiles()) {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'hub-tuile-retirer';
  b.setAttribute('aria-label', 'Retirer cette tuile de l\'accueil');
  b.textContent = '✕';
  tuile.appendChild(b);
}

function appliquerDisposition(d) {
  const parId = new Map(toutesLesTuiles().map(t => [idDe(t), t]));
  let affichees;
  if (!d.personnalisee) {
    affichees = [...TUILES_ORIGINE];
  } else {
    affichees = d.ordre.filter(id => parId.has(id));
    // Une tuile d'origine créée après l'enregistrement apparaît d'elle-même.
    const connues = new Set(d.connues);
    for (const id of TUILES_ORIGINE) {
      if (!connues.has(id) && !affichees.includes(id)) affichees.push(id);
    }
  }
  for (const id of affichees) {
    const t = parId.get(id);
    t.hidden = false;
    elGrille.appendChild(t);
  }
  for (const [id, t] of parId) {
    if (!affichees.includes(id)) { t.hidden = true; elGrille.appendChild(t); }
  }
}

async function chargerDisposition() {
  try {
    const res = await fetch('/api/hub/disposition', {
      cache: 'no-store', signal: AbortSignal.timeout(4000),
    });
    if (res.ok) dispositionChargee = await res.json();
  } catch { /* serveur injoignable : Hub d'origine */ }
  appliquerDisposition(dispositionChargee);
  elGrille.classList.remove('hub-grille--attente');
}

function statutEdition(msg, erreur = false) {
  elStatutEdition.textContent = msg;
  elStatutEdition.classList.toggle('hub-edition-statut--err', erreur);
  elStatutEdition.hidden = !msg;
}

// ── Mot de passe administrateur ──
function demanderMotDePasse(puis) {
  apresDeverrouillage = puis;
  elMdp.value = '';
  elMdpErreur.hidden = true;
  elMdpOverlay.hidden = false;
  elMdp.focus();
}

elMdpForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const res = await fetch('/api/hub/disposition/deverrouiller', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: elMdp.value }),
      cache: 'no-store',
    });
    if (!res.ok) {
      elMdpErreur.textContent = res.status === 429 ? 'Trop d\'essais : réessayez dans une minute.'
        : res.status === 401 ? 'Mot de passe administrateur incorrect.' : `Erreur ${res.status}`;
      elMdpErreur.hidden = false;
      elMdp.select();
      return;
    }
    const data = await res.json();
    jetonDispo = data.jeton;
    clearTimeout(minuteurJeton);
    minuteurJeton = setTimeout(() => { jetonDispo = null; }, (data.expire_dans || 900) * 1000);
    elMdpOverlay.hidden = true;
    const suite = apresDeverrouillage;
    apresDeverrouillage = null;
    if (suite) suite();
  } catch (err) {
    elMdpErreur.textContent = 'Serveur injoignable : ' + err.message;
    elMdpErreur.hidden = false;
  }
});

// ── Entrer / sortir du mode personnalisation ──
function entrerEdition() {
  enEdition = true;
  document.body.classList.add('hub-edition');
  elBarre.hidden = false;
  statutEdition('');
}

function sortirEdition() {
  enEdition = false;
  document.body.classList.remove('hub-edition');
  elBarre.hidden = true;
  elAjoutOverlay.hidden = true;
}

elBtnPerso.addEventListener('click', () => {
  if (enEdition) return;
  if (jetonDispo) entrerEdition(); else demanderMotDePasse(entrerEdition);
});

/** Envoie au serveur ; redemande le mot de passe si l'autorisation a expiré. */
async function envoyerDisposition(url, methode, corps, quandOk) {
  if (!jetonDispo) { demanderMotDePasse(() => envoyerDisposition(url, methode, corps, quandOk)); return; }
  statutEdition('Enregistrement…');
  try {
    const res = await fetch(url, {
      method: methode,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...corps, jeton: jetonDispo }),
      cache: 'no-store',
    });
    if (res.status === 401) {
      jetonDispo = null;
      statutEdition('Autorisation expirée : redonnez le mot de passe.', true);
      demanderMotDePasse(() => envoyerDisposition(url, methode, corps, quandOk));
      return;
    }
    if (!res.ok) {
      const detail = (await res.json().catch(() => ({}))).detail;
      statutEdition(detail || `Erreur ${res.status}`, true);
      return;
    }
    dispositionChargee = await res.json();
    quandOk();
  } catch (err) {
    statutEdition('Serveur injoignable : rien n\'a été enregistré.', true);
  }
}

document.getElementById('hub-edition-terminer').addEventListener('click', () => {
  const ordre = toutesLesTuiles().filter(t => !t.hidden).map(idDe);
  envoyerDisposition('/api/hub/disposition', 'PUT',
    { ordre, connues: toutesLesTuiles().map(idDe) }, sortirEdition);
});

document.getElementById('hub-edition-annuler').addEventListener('click', () => {
  appliquerDisposition(dispositionChargee);
  sortirEdition();
});

document.getElementById('hub-edition-origine').addEventListener('click', () => {
  if (!confirm('Remettre l\'accueil comme à l\'origine (ordre et tuiles d\'origine) ?')) return;
  envoyerDisposition('/api/hub/disposition/reinitialiser', 'POST', {}, () => {
    appliquerDisposition(dispositionChargee);
    sortirEdition();
  });
});

// ── Ajouter une tuile ──
function ouvrirAjout() {
  const dispo = toutesLesTuiles().filter(t => t.hidden);
  elAjoutListe.innerHTML = dispo.length ? dispo.map(t => `
    <li class="hub-popup-item">
      <button type="button" class="hub-popup-lien hub-ajout-choix" data-tuile="${idDe(t)}">
        <span class="hub-popup-icone" aria-hidden="true">${t.querySelector('.hub-tuile-icone').textContent}</span>
        <span class="hub-popup-texte">
          <span class="hub-popup-libelle">${escHtml(t.querySelector('.hub-tuile-titre').textContent)}</span>
          <span class="hub-popup-detail">${escHtml(t.getAttribute('href'))}</span>
        </span>
        <span class="hub-popup-fleche" aria-hidden="true">＋</span>
      </button>
    </li>`).join('')
    : listeVideHtml('Toutes les tuiles sont déjà sur l\'accueil');
  elAjoutOverlay.hidden = false;
}

document.getElementById('hub-edition-ajouter').addEventListener('click', ouvrirAjout);

elAjoutListe.addEventListener('click', (e) => {
  const choix = e.target.closest('.hub-ajout-choix');
  if (!choix) return;
  const tuile = document.getElementById('tuile-' + choix.dataset.tuile);
  tuile.hidden = false;
  // Placée juste après la dernière tuile affichée (à déplacer ensuite).
  const visibles = toutesLesTuiles().filter(t => !t.hidden && t !== tuile);
  if (visibles.length) visibles[visibles.length - 1].after(tuile); else elGrille.prepend(tuile);
  elAjoutOverlay.hidden = true;
  tuile.scrollIntoView({ block: 'nearest' });
});

for (const overlay of [elMdpOverlay, elAjoutOverlay]) {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay || e.target.closest('[data-fermer]')) overlay.hidden = true;
  });
}

// ── En mode personnalisation : pas de navigation, ✕ retire la tuile ──
elGrille.addEventListener('click', (e) => {
  if (!enEdition) return;
  e.preventDefault();
  const retirer = e.target.closest('.hub-tuile-retirer');
  if (retirer) retirer.closest('.hub-tuile').hidden = true;
}, true);

// ── Glisser-déposer (doigt ou souris) ──
// Pointer Events plutôt que le glisser-déposer HTML5, qui ne marche pas au
// doigt sur les tablettes Android. La tuile tenue change de place en direct
// quand on passe au-dessus d'une autre.
let tuileTenue = null;

elGrille.addEventListener('pointerdown', (e) => {
  if (!enEdition || e.target.closest('.hub-tuile-retirer')) return;
  const tuile = e.target.closest('.hub-tuile');
  if (!tuile) return;
  e.preventDefault();
  tuileTenue = tuile;
  tuile.classList.add('hub-tuile--tenue');
  elGrille.setPointerCapture(e.pointerId);
});

elGrille.addEventListener('pointermove', (e) => {
  if (!tuileTenue) return;
  const sous = document.elementFromPoint(e.clientX, e.clientY)?.closest('.hub-tuile');
  if (!sous || sous === tuileTenue || sous.hidden) return;
  const tuiles = toutesLesTuiles();
  if (tuiles.indexOf(tuileTenue) < tuiles.indexOf(sous)) sous.after(tuileTenue);
  else sous.before(tuileTenue);
});

function lacherTuile() {
  if (!tuileTenue) return;
  tuileTenue.classList.remove('hub-tuile--tenue');
  tuileTenue = null;
}
elGrille.addEventListener('pointerup', lacherTuile);
elGrille.addEventListener('pointercancel', lacherTuile);

// ── Init ──────────────────────────────────────────────────────
chargerDisposition();
charger();
chargerResumeTaches();
setInterval(charger, REFRESH_MS);
setInterval(chargerResumeTaches, REFRESH_MS);

'use strict';
/* ============================================================
   hub.js — Accueil Hub Phase 2 HACCP
   Au Comptoir des Lilas — Mets Carnés Holding

   Responsabilités :
   - Horloge temps réel (1 s)
   - Chargement des données depuis 4 endpoints (toutes les 30 s)
   - Tuiles et dossiers (Tâches HACCP, Production, Achats, Pilotage…) construits
     depuis la disposition enregistrée, rangeables par l'administrateur
   - Mise à jour des tuiles avec statut coloré
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
  // Retour à l'accueil (hors dossier). Pas en pleine personnalisation :
  // le rangement en cours serait perdu.
  timerInact = setTimeout(() => { if (!enEdition) location.replace('/hub.html'); }, INACT_MS);
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
const ETATS_TUILE = ['ok', 'attention', 'alerte', 'erreur', 'chargement'];

function setTuile(idTuile, etat, html) {
  const tuile  = document.getElementById(idTuile);
  const statut = document.getElementById('statut-' + idTuile.replace('tuile-', ''));
  if (!tuile || !statut) return;
  // Seule la classe d'état change (garde « dossier », « tenue »…).
  ETATS_TUILE.forEach(e => tuile.classList.remove('hub-tuile--' + e));
  tuile.classList.add('hub-tuile--' + etat);
  tuile.dataset.etat = etat;
  statut.innerHTML = html;
  majDossiers();   // un dossier prend la couleur de l'alerte qu'il contient
}

/** Texte de statut seul, sans couleur de bordure. */
function setStatut(idTuile, html) {
  const statut = document.getElementById('statut-' + idTuile.replace('tuile-', ''));
  if (statut) statut.innerHTML = html;
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

// ── Tuiles des sous-modules (anciennes pages Tâches HACCP, Achats, Pilotage) ──
function formatDate(iso) {
  if (!iso) return '—';
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

function fmtEur(v) {
  if (v == null) return '—';
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(v);
}

async function chargerNettoyage() {
  try {
    const data = await apiFetch('/api/nettoyage/status');
    if (data.valide) {
      const par = data.operateur ? ` — ${escHtml(data.operateur)}` : '';
      setTuile('tuile-nettoyage', 'ok', `${dot('ok')} Validé aujourd'hui${par}`);
    } else {
      setTuile('tuile-nettoyage', 'alerte', `${dot('alerte')} <strong>Non validé aujourd'hui</strong>`);
    }
  } catch {
    setTuile('tuile-nettoyage', 'erreur', '⚠ Connexion perdue');
  }
}

async function chargerEtalonnage() {
  try {
    const data = await apiFetch('/api/etalonnage/status');
    if (data.jamais_fait) {
      setTuile('tuile-etalonnage', 'alerte',
        `${dot('alerte')} <strong>Jamais réalisé</strong><br><small>EET01 requis</small>`);
      return;
    }
    if (data.en_retard) {
      const jours = Math.abs(data.jours_restants);
      setTuile('tuile-etalonnage', 'alerte',
        `${dot('alerte')} <strong>En retard de ${jours} j</strong>`
        + `<br><small>Dernier : ${formatDate(data.dernier_date)}</small>`);
      return;
    }
    const j = data.jours_restants;
    const etatTuile = j <= 14 ? 'attention' : 'ok';
    setTuile('tuile-etalonnage', etatTuile,
      `${dot(etatTuile)} Prochain dans ${j} j<br><small>Dernier : ${formatDate(data.dernier_date)}</small>`);
  } catch {
    setTuile('tuile-etalonnage', 'erreur', '⚠ Connexion perdue');
  }
}

async function chargerTemperatures() {
  try {
    const dash = await apiFetch('/api/boutiques/1/dashboard');
    if (!dash?.boutique) {
      setTuile('tuile-temperatures', 'erreur', '⚠ Données indisponibles');
      return;
    }
    const sg    = dash.boutique.statut;
    const etatTuile = sg === 'alerte' ? 'alerte' : sg === 'attention' ? 'attention' : 'ok';
    const label = sg === 'alerte' ? 'ALERTE TEMPÉRATURE' : sg === 'attention' ? 'Attention' : 'Tout OK';
    const mesures = (dash.enceintes ?? [])
      .filter(e => e.temperature_actuelle !== null)
      .slice(0, 3)
      .map(e => {
        const t   = Number(e.temperature_actuelle).toFixed(1);
        const nom = escHtml(e.nom.replace('Chambre froide', 'CF').replace('chambre froide', 'CF'));
        const couleur = e.statut === 'alerte' ? 'style="color:var(--alerte);font-weight:700"' : '';
        return `<span ${couleur}>${nom}&nbsp;${t}°</span>`;
      })
      .join('&ensp;·&ensp;');
    setTuile('tuile-temperatures', etatTuile,
      `${dot(etatTuile)} ${label}` + (mesures ? `<br><small>${mesures}</small>` : ''));
  } catch {
    setTuile('tuile-temperatures', 'erreur', '⚠ Connexion perdue');
  }
}

async function chargerAchats() {
  const [rF, rC, rFac] = await Promise.allSettled([
    apiFetch('/api/achats/fournisseurs'),
    apiFetch('/api/achats/commandes?limit=100'),
    apiFetch('/api/achats/factures?limit=100'),
  ]);
  if (rF.status === 'fulfilled') {
    const n = rF.value.length;
    setStatut('tuile-fournisseurs', `${n} fournisseur${n > 1 ? 's' : ''} actif${n > 1 ? 's' : ''}`);
  }
  if (rC.status === 'fulfilled') {
    const n = rC.value.filter(c => c.statut === 'brouillon' || c.statut === 'confirmee').length;
    setStatut('tuile-commandes', n > 0 ? `${n} commande${n > 1 ? 's' : ''} en cours` : 'Aucune commande en cours');
  }
  if (rFac.status === 'fulfilled') {
    const n = rFac.value.filter(f => f.statut === 'litige').length;
    if (n > 0) setTuile('tuile-factures', 'attention', `${dot('attention')} ${n} en litige`);
  }
}

async function chargerPilotage() {
  const [rCa, rInv] = await Promise.allSettled([
    apiFetch('/api/achats/pilotage/ca/stats/resume'),
    apiFetch('/api/inventaire/sessions?limit=1'),
  ]);
  if (rCa.status === 'fulfilled') {
    const mc = rCa.value.mois_courant || {};
    setStatut('tuile-pilotage-ca', mc.nb_jours > 0 ? `Mois en cours : ${fmtEur(mc.total_ttc)}` : 'Aucune saisie ce mois-ci');
  }
  if (rInv.status === 'fulfilled') {
    const ses = (rInv.value.sessions || [])[0];
    if (!ses) {
      setStatut('tuile-inventaire-valorise', 'Aucun inventaire');
    } else {
      const date = new Date(ses.date_inventaire).toLocaleDateString('fr-FR');
      setStatut('tuile-inventaire-valorise', ses.statut === 'cloture'
        ? `${date} : ${fmtEur(ses.valeur_totale_ht)}` : `${date} : en cours…`);
    }
  }
}

async function chargerSousModules() {
  await Promise.allSettled([
    chargerNettoyage(), chargerEtalonnage(), chargerTemperatures(), chargerAchats(), chargerPilotage(),
  ]);
}

// ── Tuiles possibles et disposition d'origine ─────────────────
// Le serveur n'enregistre que des identifiants : titre, icône et lien sont ici.
const TUILES = [
  // Accueil
  { id: 'reception',           href: '/reception.html',            icone: '📦', titre: 'RÉCEPTION',           statut: 'Chargement…' },
  { id: 'ouverture',           href: '/ouverture.html',            icone: '✂️', titre: 'OUVERTURE',           statut: 'Traçabilité ouvertures' },
  { id: 'dlc',                 href: '/dlc.html',                  icone: '📅', titre: 'CALENDRIER DLC',      statut: '4 sources unifiées' },
  { id: 'inventaire',          href: '/inventaire.html',           icone: '📋', titre: 'STOCK',               statut: 'FIFO toutes sources' },
  { id: 'historique',          href: '/historique.html',           icone: '🗂️', titre: 'HISTORIQUE',          statut: 'Tous les enregistrements' },
  { id: 'prix-etiquettes',     href: '/prix-etiquettes.html',      icone: '🏷️', titre: 'ÉTIQUETTES PRIX',     statut: 'Impression Brother QL' },
  // Tâches HACCP
  { id: 'nettoyage',           href: '/nettoyage.html',            icone: '🧹', titre: 'NETTOYAGE',           statut: 'Chargement…' },
  { id: 'etalonnage',          href: '/etalonnage.html',           icone: '🌡️', titre: 'ÉTALONNAGE',          statut: 'Chargement…' },
  { id: 'temperatures',        href: '/',                          icone: '🌡️', titre: 'TEMPÉRATURES',        statut: 'Chargement…' },
  { id: 'nuisibles',           href: '/nuisibles.html',            icone: '🐛', titre: 'NUISIBLES',           statut: 'IPM — Plan de lutte' },
  { id: 'elearning',           href: '/elearning.html',            icone: '🎓', titre: 'E-LEARNING',          statut: 'Formation HACCP' },
  { id: 'classeur-pms',        href: '/classeur-pms.html',         icone: '📂', titre: 'CLASSEUR PMS',        statut: 'Procédures & traçabilité' },
  // Production
  { id: 'fabrication',         href: '/etiquettes.html',           icone: '🔪', titre: 'FABRICATION',         statut: 'Étiquettes & traçabilité' },
  { id: 'cuisson',             href: '/cuisson.html',              icone: '🔥', titre: 'CUISSON',             statut: 'Rôtissoire — T° ≥ 75 °C' },
  { id: 'refroidissement',     href: '/refroidissement.html',      icone: '❄️', titre: 'REFROIDISSEMENT',     statut: '≤ 10 °C en ≤ 2 h' },
  { id: 'catalogue-vente',     href: '/catalogue-vente.html',      icone: '🏷️', titre: 'CATALOGUE VENTE',     statut: 'Produits finis fabriqués' },
  // Achats
  { id: 'fournisseurs',        href: '/fournisseurs.html',         icone: '🏢', titre: 'FOURNISSEURS',        statut: 'Fiches fournisseurs' },
  { id: 'catalogue-achats',    href: '/catalogue-achats.html',     icone: '📋', titre: 'CATALOGUE ACHATS',    statut: 'Articles & prix fournisseurs' },
  { id: 'commandes',           href: '/commandes.html',            icone: '📝', titre: 'COMMANDES',           statut: 'Commandes fournisseurs' },
  { id: 'factures',            href: '/factures-achats.html',      icone: '🧾', titre: 'FACTURES',            statut: 'Rapprocher les écarts' },
  { id: 'comparatif',          href: '/comparatif-achats.html',    icone: '⚖️', titre: 'COMPARATEUR',         statut: 'Prix au kg par fournisseur' },
  // Pilotage
  { id: 'pilotage-ca',         href: '/pilotage-ca.html',          icone: '💶', titre: "CHIFFRE D'AFFAIRES",  statut: 'Chargement…' },
  { id: 'inventaire-valorise', href: '/inventaire-valorise.html',  icone: '💰', titre: 'INVENTAIRE VALORISÉ', statut: 'Chargement…' },
  { id: 'marge',               href: '/marge.html',                icone: '📈', titre: 'MARGE',               statut: 'CA − coût marchandises' },
  // Autres pages (pas sur l'accueil d'origine, à ajouter au besoin)
  { id: 'production-a-cuire',  href: '/production-a-cuire.html',   icone: '🍗', titre: 'À CUIRE',             statut: 'Produits à cuire' },
  { id: 'produits-attente',    href: '/produits-attente.html',     icone: '⏳', titre: 'PRODUITS EN ATTENTE', statut: 'Lot / DLC à compléter' },
  { id: 'receptions-historique', href: '/receptions-historique.html', icone: '📑', titre: 'HISTORIQUE RÉCEPTIONS', statut: 'Réceptions passées' },
  { id: 'historique-nettoyage', href: '/historique-nettoyage.html', icone: '🧽', titre: 'HISTORIQUE NETTOYAGE', statut: 'Nettoyages passés' },
  { id: 'incidents',           href: '/incidents.html',            icone: '⚠️', titre: 'FICHES INCIDENTS',    statut: 'Fiches PCR01' },
  { id: 'catalogue',           href: '/catalogue.html',            icone: '📚', titre: 'CATALOGUE PRODUITS',  statut: 'Produits & matières premières' },
  { id: 'recettes',            href: '/admin-recettes.html',       icone: '📖', titre: 'RECETTES',            statut: 'Gestion des recettes' },
  { id: 'tutoriel',            href: '/tutoriel-slideshow.html',   icone: '📽️', titre: 'TUTORIEL',            statut: 'Tutoriel HACCP' },
  { id: 'admin',               href: '/admin.html',                icone: '⚙️', titre: 'ADMINISTRATION',      statut: 'Configuration' },
];

// Reprend les anciennes pages Tâches HACCP, Production, Achats (et Pilotage dedans).
const DISPOSITION_ORIGINE = {
  accueil: ['dossier-taches', 'dossier-production', 'reception', 'ouverture', 'dlc',
            'inventaire', 'historique', 'dossier-achats', 'prix-etiquettes'],
  dossiers: {
    'dossier-taches':     { titre: 'Tâches HACCP', icone: '✅',
      tuiles: ['nettoyage', 'etalonnage', 'temperatures', 'nuisibles', 'elearning', 'classeur-pms'] },
    'dossier-production': { titre: 'Production', icone: '🏭',
      tuiles: ['fabrication', 'cuisson', 'refroidissement', 'catalogue-vente'] },
    'dossier-achats':     { titre: 'Achats', icone: '🛒',
      tuiles: ['fournisseurs', 'catalogue-achats', 'commandes', 'factures', 'comparatif', 'dossier-pilotage'] },
    'dossier-pilotage':   { titre: 'Pilotage', icone: '📊',
      tuiles: ['pilotage-ca', 'inventaire-valorise', 'marge'] },
  },
};

const ICONES_DOSSIER = ['📁', '✅', '🏭', '🛒', '📊', '🥩', '🔪', '🧾', '📦', '🧹', '🌡️', '💶', '🏷️', '⭐', '🔧', '📚'];

// ── État ──────────────────────────────────────────────────────
const elGrille         = document.getElementById('hub-grille');
const elRetour         = document.getElementById('hub-retour');
const elTitre          = document.getElementById('hub-titre');
const elBtnPerso       = document.getElementById('hub-btn-perso');
const elBarre          = document.getElementById('hub-edition-barre');
const elStatutEdition  = document.getElementById('hub-edition-statut');
const elMdpOverlay     = document.getElementById('hub-mdp-overlay');
const elMdpForm        = document.getElementById('hub-mdp-form');
const elMdp            = document.getElementById('hub-mdp');
const elMdpErreur      = document.getElementById('hub-mdp-erreur');
const elChoixOverlay   = document.getElementById('hub-choix-overlay');
const elChoixTitre     = document.getElementById('hub-choix-titre');
const elChoixListe     = document.getElementById('hub-choix-liste');
const elDossierOverlay = document.getElementById('hub-dossier-overlay');
const elDossierForm    = document.getElementById('hub-dossier-form');
const elDossierTitre   = document.getElementById('hub-dossier-titre');
const elDossierNom     = document.getElementById('hub-dossier-nom');
const elDossierIcones  = document.getElementById('hub-dossier-icones');

const parIdTuile = new Map(TUILES.map(t => [t.id, t]));
const estDossier = (id) => id.startsWith('dossier-');
const cloner = (o) => JSON.parse(JSON.stringify(o));

let disposition = { personnalisee: false };   // telle qu'enregistrée sur le serveur
let etat = cloner(DISPOSITION_ORIGINE);       // affichée (copie de travail en édition)
let vue = null;                               // dossier ouvert, null = accueil
let enEdition = false;
let jetonDispo = null;          // autorisation admin (15 min), en mémoire seulement
let minuteurJeton = null;
let apresDeverrouillage = null; // action à reprendre une fois le mot de passe donné

const listeDe = (v) => (v ? etat.dossiers[v].tuiles : etat.accueil);

/** Dossier qui contient `id` (null = accueil, undefined = nulle part). */
function parentDe(id) {
  if (etat.accueil.includes(id)) return null;
  for (const [k, d] of Object.entries(etat.dossiers)) if (d.tuiles.includes(id)) return k;
  return undefined;
}

function idsPlaces(e) {
  return new Set([...e.accueil, ...Object.values(e.dossiers).flatMap(d => d.tuiles)]);
}

/** Le dossier et tous ses sous-dossiers (on ne range pas un dossier en lui-même). */
function descendants(id) {
  const res = new Set([id]);
  for (const t of etat.dossiers[id]?.tuiles ?? []) {
    if (estDossier(t)) descendants(t).forEach(x => res.add(x));
  }
  return res;
}

function depuisServeur(d) {
  if (!d?.personnalisee) return cloner(DISPOSITION_ORIGINE);
  const e = { accueil: [...d.accueil], dossiers: cloner(d.dossiers) };
  const existe = (id) => (estDossier(id) ? id in e.dossiers : parIdTuile.has(id));
  e.accueil = e.accueil.filter(existe);
  for (const k in e.dossiers) e.dossiers[k].tuiles = e.dossiers[k].tuiles.filter(existe);
  // Tuile ajoutée au code après l'enregistrement : à sa place d'origine.
  const connues = new Set(d.connues);
  const places = idsPlaces(e);
  const origines = [[null, DISPOSITION_ORIGINE.accueil],
    ...Object.entries(DISPOSITION_ORIGINE.dossiers).map(([k, v]) => [k, v.tuiles])];
  for (const [lieu, ids] of origines) {
    for (const id of ids) {
      if (estDossier(id) || connues.has(id) || places.has(id)) continue;
      (lieu && e.dossiers[lieu] ? e.dossiers[lieu].tuiles : e.accueil).push(id);
    }
  }
  return e;
}

// ── Construction des tuiles ───────────────────────────────────
const elements = new Map();   // id → <a> (tuiles et dossiers)

function boutonOutil(action, texte, aide) {
  return `<button type="button" class="hub-tuile-outil hub-tuile-outil--${action}"
            data-action="${action}" aria-label="${aide}" title="${aide}">${texte}</button>`;
}

function creerElement(id) {
  const a = document.createElement('a');
  a.className = 'hub-tuile';
  a.id = 'tuile-' + id;
  a.dataset.id = id;
  a.hidden = true;
  let outils;
  if (estDossier(id)) {
    a.classList.add('hub-tuile--dossier');
    a.href = '#' + id;
    a.innerHTML = `
      <div class="hub-tuile-icone" aria-hidden="true"></div>
      <div class="hub-tuile-titre"></div>
      <div class="hub-tuile-statut" id="statut-${id}"></div>`;
    outils = boutonOutil('renommer', '✏️', 'Renommer le dossier')
           + boutonOutil('ranger', '📁', 'Ranger dans un autre dossier')
           + boutonOutil('supprimer', '✕', 'Supprimer le dossier (son contenu est gardé)');
  } else {
    const t = parIdTuile.get(id);
    a.href = t.href;
    a.setAttribute('aria-label', t.titre);
    a.innerHTML = `
      <div class="hub-tuile-icone" aria-hidden="true">${t.icone}</div>
      <div class="hub-tuile-titre">${escHtml(t.titre)}</div>
      <div class="hub-tuile-statut" id="statut-${id}">${escHtml(t.statut)}</div>`;
    outils = boutonOutil('ranger', '📁', 'Ranger dans un dossier')
           + boutonOutil('retirer', '✕', 'Retirer de l\'accueil');
  }
  a.insertAdjacentHTML('beforeend', `<div class="hub-tuile-outils">${outils}</div>`);
  elGrille.appendChild(a);
  elements.set(id, a);
  return a;
}

// Toutes les tuiles existent dès le départ (cachées) : leurs statuts en direct
// se mettent à jour même quand elles sont rangées dans un dossier fermé.
TUILES.forEach(t => creerElement(t.id));

// « CALENDRIER DLC » → « Calendrier DLC » (sigles gardés en capitales)
const SIGLES = new Set(['DLC', 'PMS']);
const titreCourt = (t) => t.split(' ')
  .map((m, i) => (SIGLES.has(m) ? m : i === 0 ? m.charAt(0) + m.slice(1).toLowerCase() : m.toLowerCase()))
  .join(' ');

function titreDe(id) {
  return estDossier(id) ? etat.dossiers[id]?.titre ?? '' : titreCourt(parIdTuile.get(id).titre);
}

/** Pire état (alerte > attention) parmi les tuiles d'un dossier et de ses sous-dossiers. */
function etatDossier(id, vus = new Set()) {
  if (vus.has(id)) return null;
  vus.add(id);
  let pire = null;
  for (const t of etat.dossiers[id]?.tuiles ?? []) {
    const e = estDossier(t) ? etatDossier(t, vus) : elements.get(t)?.dataset.etat;
    if (e === 'alerte') return 'alerte';
    if (e === 'attention') pire = 'attention';
  }
  return pire;
}

function majDossiers() {
  for (const [id, d] of Object.entries(etat.dossiers)) {
    const el = elements.get(id) ?? creerElement(id);
    el.setAttribute('aria-label', 'Dossier ' + d.titre);
    el.querySelector('.hub-tuile-icone').textContent = d.icone;
    el.querySelector('.hub-tuile-titre').textContent = d.titre;
    const noms = d.tuiles.map(titreDe);
    el.querySelector('.hub-tuile-statut').textContent = noms.length
      ? noms.slice(0, 3).join(' · ') + (noms.length > 3 ? ` +${noms.length - 3}` : '')
      : 'Dossier vide';
    const e = etatDossier(id);
    el.classList.toggle('hub-tuile--alerte', e === 'alerte');
    el.classList.toggle('hub-tuile--attention', e === 'attention');
  }
}

function rendre() {
  if (vue && !etat.dossiers[vue]) vue = null;
  for (const [id, el] of elements) {
    if (estDossier(id) && !etat.dossiers[id]) { el.remove(); elements.delete(id); }
    else el.hidden = true;
  }
  majDossiers();
  for (const id of listeDe(vue)) {
    const el = elements.get(id);
    el.hidden = false;
    elGrille.appendChild(el);
  }
  elRetour.hidden = !vue;
  if (vue) {
    const p = parentDe(vue);
    elRetour.href = p ? '#' + p : '#';
    elRetour.innerHTML = `← <span class="hub-retour-texte">${escHtml(p ? etat.dossiers[p].titre : 'Accueil')}</span>`;
    elTitre.textContent = `${etat.dossiers[vue].icone} ${etat.dossiers[vue].titre}`;
  } else {
    elTitre.textContent = 'Au Comptoir des Lilas';
  }
}

// ── Navigation dans les dossiers (#dossier-xxx dans l'adresse) ──
function vueDepuisAdresse() {
  const h = decodeURIComponent(location.hash.slice(1));
  return etat.dossiers[h] ? h : null;
}

window.addEventListener('hashchange', () => { vue = vueDepuisAdresse(); rendre(); });

async function chargerDisposition() {
  try {
    const res = await fetch('/api/hub/disposition', { cache: 'no-store', signal: AbortSignal.timeout(4000) });
    if (res.ok) disposition = await res.json();
  } catch { /* serveur injoignable : Hub d'origine */ }
  etat = depuisServeur(disposition);
  vue = vueDepuisAdresse();
  rendre();
  elGrille.classList.remove('hub-grille--attente');
}

// ── Personnaliser l'accueil (administrateur) ──────────────────
function statutEdition(msg, erreur = false) {
  elStatutEdition.textContent = msg;
  elStatutEdition.classList.toggle('hub-edition-statut--err', erreur);
  elStatutEdition.hidden = !msg;
}

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
  elChoixOverlay.hidden = true;
  elDossierOverlay.hidden = true;
}

elBtnPerso.addEventListener('click', () => {
  if (enEdition) return;
  if (jetonDispo) entrerEdition(); else demanderMotDePasse(entrerEdition);
});

/** Envoie au serveur ; redemande le mot de passe si l'autorisation a expiré. */
async function envoyerDisposition(url, methode, corps) {
  const relancer = () => envoyerDisposition(url, methode, corps);
  if (!jetonDispo) { demanderMotDePasse(relancer); return; }
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
      demanderMotDePasse(relancer);
      return;
    }
    if (!res.ok) {
      const detail = (await res.json().catch(() => ({}))).detail;
      statutEdition(typeof detail === 'string' ? detail : `Erreur ${res.status}`, true);
      return;
    }
    disposition = await res.json();
    etat = depuisServeur(disposition);
    sortirEdition();
    rendre();
  } catch {
    statutEdition('Serveur injoignable : rien n\'a été enregistré.', true);
  }
}

document.getElementById('hub-edition-terminer').addEventListener('click', () => {
  envoyerDisposition('/api/hub/disposition', 'PUT',
    { accueil: etat.accueil, dossiers: etat.dossiers, connues: TUILES.map(t => t.id) });
});

document.getElementById('hub-edition-annuler').addEventListener('click', () => {
  etat = depuisServeur(disposition);
  sortirEdition();
  vue = vueDepuisAdresse();
  rendre();
});

document.getElementById('hub-edition-origine').addEventListener('click', () => {
  if (!confirm('Remettre tout l\'accueil comme à l\'origine (tuiles et dossiers) ?')) return;
  envoyerDisposition('/api/hub/disposition/reinitialiser', 'POST', {});
});

// ── Popup de choix (ajouter une tuile / ranger dans un dossier) ──
let surChoix = null;

function ouvrirChoix(titre, options, quandChoisi) {
  elChoixTitre.textContent = titre;
  elChoixListe.innerHTML = options.length ? options.map((o, i) => `
    <li class="hub-popup-item">
      <button type="button" class="hub-popup-lien hub-choix" data-i="${i}">
        <span class="hub-popup-icone" aria-hidden="true">${escHtml(o.icone)}</span>
        <span class="hub-popup-texte">
          <span class="hub-popup-libelle">${escHtml(o.libelle)}</span>
          <span class="hub-popup-detail">${escHtml(o.detail ?? '')}</span>
        </span>
        <span class="hub-popup-fleche" aria-hidden="true">›</span>
      </button>
    </li>`).join('')
    : listeVideHtml('Toutes les tuiles sont déjà placées');
  surChoix = (i) => quandChoisi(options[i]);
  elChoixOverlay.hidden = false;
}

elChoixListe.addEventListener('click', (e) => {
  const b = e.target.closest('.hub-choix');
  if (!b) return;
  elChoixOverlay.hidden = true;
  surChoix(Number(b.dataset.i));
});

/** « Achats › Pilotage » : chemin d'un dossier depuis l'accueil. */
function cheminDe(id) {
  const noms = [];
  for (let d = id; d; d = parentDe(d)) noms.unshift(etat.dossiers[d].titre);
  return noms.join(' › ');
}

document.getElementById('hub-edition-ajouter').addEventListener('click', () => {
  const places = idsPlaces(etat);
  const libres = TUILES.filter(t => !places.has(t.id)).map(t => ({
    id: t.id, icone: t.icone, libelle: titreCourt(t.titre),
    detail: t.statut === 'Chargement…' ? t.href : t.statut,
  }));
  ouvrirChoix('＋ Ajouter une tuile ici', libres, (o) => {
    listeDe(vue).push(o.id);
    rendre();
    elements.get(o.id).scrollIntoView({ block: 'nearest' });
  });
});

function deplacer(id, cible) {
  const depuis = parentDe(id);
  if (depuis === undefined) return;
  const liste = depuis ? etat.dossiers[depuis].tuiles : etat.accueil;
  liste.splice(liste.indexOf(id), 1);
  (cible ? etat.dossiers[cible].tuiles : etat.accueil).push(id);
  rendre();
}

function rangerDans(id) {
  const ici = parentDe(id);
  const interdits = estDossier(id) ? descendants(id) : new Set();
  const options = [];
  if (ici !== null) options.push({ cible: null, icone: '🏠', libelle: 'Accueil', detail: 'Écran principal' });
  for (const k of Object.keys(etat.dossiers)) {
    if (k === ici || interdits.has(k) || parentDe(k) === undefined) continue;
    options.push({ cible: k, icone: etat.dossiers[k].icone, libelle: etat.dossiers[k].titre, detail: cheminDe(k) });
  }
  options.push({ nouveau: true, icone: '＋', libelle: 'Nouveau dossier…', detail: 'Créé ici, la tuile va dedans' });
  ouvrirChoix(`📁 Ranger « ${titreDe(id)} » dans…`, options, (o) => {
    if (o.nouveau) ouvrirDossier(null, (nouvelId) => deplacer(id, nouvelId));
    else deplacer(id, o.cible);
  });
}

// ── Nouveau dossier / renommer ──
let iconeChoisie = '📁';
let surDossier = null;

function afficherIcones() {
  elDossierIcones.innerHTML = ICONES_DOSSIER.map(i => `
    <button type="button" class="hub-dossier-icone${i === iconeChoisie ? ' hub-dossier-icone--choisie' : ''}"
            data-icone="${i}" aria-label="Icône ${i}">${i}</button>`).join('');
}

elDossierIcones.addEventListener('click', (e) => {
  const b = e.target.closest('[data-icone]');
  if (!b) return;
  iconeChoisie = b.dataset.icone;
  afficherIcones();
});

function nouvelIdDossier(nom) {
  const base = nom.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 20) || 'perso';
  let id;
  do { id = `dossier-${base}-${Math.random().toString(36).slice(2, 6)}`; } while (etat.dossiers[id]);
  return id;
}

/** idDossier = null → création dans la vue courante, puis quandOk(id). */
function ouvrirDossier(idDossier, quandOk) {
  const d = idDossier ? etat.dossiers[idDossier] : null;
  elDossierTitre.textContent = d ? '✏️ Renommer le dossier' : '📁 Nouveau dossier';
  elDossierNom.value = d ? d.titre : '';
  iconeChoisie = d ? d.icone : '📁';
  afficherIcones();
  surDossier = (nom) => {
    if (d) { d.titre = nom; d.icone = iconeChoisie; rendre(); return; }
    const id = nouvelIdDossier(nom);
    etat.dossiers[id] = { titre: nom, icone: iconeChoisie, tuiles: [] };
    listeDe(vue).push(id);
    rendre();
    if (quandOk) quandOk(id);
  };
  elDossierOverlay.hidden = false;
  elDossierNom.focus();
}

elDossierForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const nom = elDossierNom.value.trim();
  if (!nom) return;
  elDossierOverlay.hidden = true;
  surDossier(nom);
});

document.getElementById('hub-edition-dossier').addEventListener('click', () => ouvrirDossier(null));

function supprimerDossier(id) {
  const d = etat.dossiers[id];
  const ici = parentDe(id);
  const lieu = ici ? `le dossier « ${etat.dossiers[ici].titre} »` : 'l\'accueil';
  const msg = d.tuiles.length
    ? `Supprimer le dossier « ${d.titre} » ? Ses ${d.tuiles.length} tuile(s) reviennent dans ${lieu}.`
    : `Supprimer le dossier vide « ${d.titre} » ?`;
  if (!confirm(msg)) return;
  const liste = ici ? etat.dossiers[ici].tuiles : etat.accueil;
  liste.splice(liste.indexOf(id), 1, ...d.tuiles);
  delete etat.dossiers[id];
  rendre();
}

for (const overlay of [elMdpOverlay, elChoixOverlay, elDossierOverlay]) {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay || e.target.closest('[data-fermer]')) overlay.hidden = true;
  });
}

// ── En mode personnalisation : pas de navigation, outils des tuiles ──
elGrille.addEventListener('click', (e) => {
  if (!enEdition) return;
  e.preventDefault();
  const outil = e.target.closest('[data-action]');
  if (!outil) return;
  const id = outil.closest('.hub-tuile').dataset.id;
  const action = outil.dataset.action;
  if (action === 'retirer') { listeDe(vue).splice(listeDe(vue).indexOf(id), 1); rendre(); }
  else if (action === 'ranger') rangerDans(id);
  else if (action === 'renommer') ouvrirDossier(id);
  else if (action === 'supprimer') supprimerDossier(id);
}, true);

// ── Glisser-déposer (doigt ou souris) ──
// Pointer Events plutôt que le glisser-déposer HTML5, qui ne marche pas au
// doigt sur les tablettes Android. Au-delà de quelques pixels on déplace ;
// une simple touche sur un dossier l'ouvre (pour ranger à l'intérieur).
const SEUIL_GLISSER_PX = 10;
let prise = null;   // { tuile, x, y, glisse }

elGrille.addEventListener('pointerdown', (e) => {
  if (!enEdition || e.target.closest('[data-action]')) return;
  const tuile = e.target.closest('.hub-tuile');
  if (!tuile) return;
  e.preventDefault();
  prise = { tuile, x: e.clientX, y: e.clientY, glisse: false };
  elGrille.setPointerCapture(e.pointerId);
});

elGrille.addEventListener('pointermove', (e) => {
  if (!prise) return;
  if (!prise.glisse) {
    if (Math.hypot(e.clientX - prise.x, e.clientY - prise.y) < SEUIL_GLISSER_PX) return;
    prise.glisse = true;
    prise.tuile.classList.add('hub-tuile--tenue');
  }
  const sous = document.elementFromPoint(e.clientX, e.clientY)?.closest('.hub-tuile');
  if (!sous || sous === prise.tuile || sous.hidden) return;
  const ordre = [...elGrille.children];
  if (ordre.indexOf(prise.tuile) < ordre.indexOf(sous)) sous.after(prise.tuile);
  else sous.before(prise.tuile);
});

function lacher(annule) {
  if (!prise) return;
  const { tuile, glisse } = prise;
  prise = null;
  tuile.classList.remove('hub-tuile--tenue');
  if (glisse) {
    const ordre = [...elGrille.children].filter(el => !el.hidden).map(el => el.dataset.id);
    listeDe(vue).splice(0, Infinity, ...ordre);
  } else if (!annule && estDossier(tuile.dataset.id)) {
    location.hash = tuile.dataset.id;
  }
}
elGrille.addEventListener('pointerup', () => lacher(false));
elGrille.addEventListener('pointercancel', () => lacher(true));

// ── Init ──────────────────────────────────────────────────────
chargerDisposition();
charger();
chargerSousModules();
chargerResumeTaches();
setInterval(charger, REFRESH_MS);
setInterval(chargerSousModules, 2 * REFRESH_MS);
setInterval(chargerResumeTaches, REFRESH_MS);

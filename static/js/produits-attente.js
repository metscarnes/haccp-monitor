'use strict';
/* ============================================================
   produits-attente.js — Complétion des produits en attente
   de traçabilité (lot/DLC manquant à la réception).

   Un produit reste hors stock tant que ses infos ne sont pas
   complétées. Cette page est ouverte depuis la tâche HACCP
   non-masquable du Hub.
   ============================================================ */

// ── Références DOM ─────────────────────────────────────────
const elHorloge   = document.getElementById('pa-horloge');
const elBtnRetour = document.getElementById('pa-btn-retour');
const elCompteur  = document.getElementById('pa-compteur');
const elListe     = document.getElementById('pa-liste');
const elMessage   = document.getElementById('pa-message');
const elMsgIcone  = document.getElementById('pa-message-icone');
const elMsgTexte  = document.getElementById('pa-message-texte');
const elBarre     = document.getElementById('pa-barre');
const elFiltreFourn = document.getElementById('pa-filtre-fourn');
const elTri       = document.getElementById('pa-tri');
// Visionneuse BL
const elViewer     = document.getElementById('pa-viewer');
const elViewerImg  = document.getElementById('pa-viewer-img');
const elViewerTit  = document.getElementById('pa-viewer-titre');
const elViewerPrec = document.getElementById('pa-viewer-prec');
const elViewerSuiv = document.getElementById('pa-viewer-suiv');
const elViewerFerm = document.getElementById('pa-viewer-fermer');

// Toutes les lignes en attente, telles que reçues du serveur (source de vérité).
let toutesLignes = [];

// ── Horloge ────────────────────────────────────────────────
function majHorloge() {
  if (!elHorloge) return;
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();

// ── Retour & inactivité ────────────────────────────────────
if (elBtnRetour) {
  elBtnRetour.addEventListener('click', () => { window.location.href = '/hub.html'; });
}
let timerInactivite;
function resetInactivite() {
  clearTimeout(timerInactivite);
  timerInactivite = setTimeout(() => { window.location.href = '/hub.html'; }, 5 * 60 * 1000);
}
document.addEventListener('click',      resetInactivite, true);
document.addEventListener('touchstart', resetInactivite, { passive: true, capture: true });
document.addEventListener('input',      resetInactivite, true);
resetInactivite();

// ── Fetch helper ───────────────────────────────────────────
async function apiFetch(url, opts) {
  const res = await fetch(url, { cache: 'no-store', ...(opts || {}) });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} — ${txt || url}`);
  }
  return res.json();
}

// ── Utilitaires ────────────────────────────────────────────
function escHtml(s) {
  if (s === null || s === undefined) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function fmtDateFR(iso) {
  if (!iso) return '—';
  return String(iso).slice(0, 10).split('-').reverse().join('/');
}
function libelleMotif(motif) {
  if (motif === 'lot_dlc') return 'N° de lot + date manquants';
  if (motif === 'lot')     return 'N° de lot manquant';
  if (motif === 'dlc')     return 'Date (DLC) manquante';
  return 'À compléter';
}
// Le produit attend-il une date d'abattage plutôt qu'une DLC ?
function attendDateAbattage(ligne) {
  return ligne.dlc_type === 'date_abattage';
}

function afficherMessage(icone, texte) {
  elMessage.hidden = false;
  elMsgIcone.textContent = icone;
  elMsgTexte.textContent = texte;
}
function masquerMessage() { elMessage.hidden = true; }

// ── Chargement de la liste ─────────────────────────────────
async function charger() {
  afficherMessage('⏳', 'Chargement…');
  elListe.innerHTML = '';
  let data;
  try {
    data = await apiFetch('/api/attente/lignes');
  } catch (e) {
    afficherMessage('⚠️', 'Erreur de chargement. Réessayez.');
    return;
  }

  toutesLignes = data.lignes || [];

  if (!toutesLignes.length) {
    elBarre.hidden = true;
    elCompteur.textContent = '';
    afficherMessage('✅', 'Aucun produit en attente — tout est tracé !');
    return;
  }

  masquerMessage();
  remplirFiltreFournisseurs();
  elBarre.hidden = false;
  rendre();
}

// Remplit la liste déroulante des fournisseurs distincts présents dans la file.
function remplirFiltreFournisseurs() {
  const courant = elFiltreFourn.value;
  const noms = [...new Set(
    toutesLignes.map(l => (l.fournisseur_nom || '').trim()).filter(Boolean)
  )].sort((a, b) => a.localeCompare(b, 'fr'));

  elFiltreFourn.innerHTML = '<option value="">Tous les fournisseurs</option>'
    + noms.map(n => `<option value="${escHtml(n)}">${escHtml(n)}</option>`).join('');
  // Conserver la sélection si toujours présente
  if (courant && noms.includes(courant)) elFiltreFourn.value = courant;
}

// ── Rendu groupé par réception, avec filtre + tri ──────────
function rendre() {
  elListe.innerHTML = '';

  const filtreFourn = elFiltreFourn.value;
  const tri = elTri.value;

  let lignes = toutesLignes;
  if (filtreFourn) {
    lignes = lignes.filter(l => (l.fournisseur_nom || '').trim() === filtreFourn);
  }

  // Regrouper par réception
  const groupes = new Map();  // reception_id → {reception_id, fournisseur_nom, date, heure, lignes:[]}
  lignes.forEach(l => {
    let g = groupes.get(l.reception_id);
    if (!g) {
      g = {
        reception_id:    l.reception_id,
        fournisseur_nom: l.fournisseur_nom || '—',
        date_reception:  l.date_reception || '',
        heure_reception: l.heure_reception || '',
        lignes:          [],
      };
      groupes.set(l.reception_id, g);
    }
    g.lignes.push(l);
  });

  let liste = [...groupes.values()];

  // Tri des groupes
  liste.sort((a, b) => {
    if (tri === 'date_asc')  return (a.date_reception || '').localeCompare(b.date_reception || '');
    if (tri === 'fourn')     return a.fournisseur_nom.localeCompare(b.fournisseur_nom, 'fr');
    if (tri === 'nb_desc')   return b.lignes.length - a.lignes.length;
    // date_desc (défaut)
    return (b.date_reception || '').localeCompare(a.date_reception || '');
  });

  const nbProduits = lignes.length;
  const nbReceptions = liste.length;
  elCompteur.textContent =
    `${nbProduits} produit(s) à compléter · ${nbReceptions} réception(s)`;

  if (!nbProduits) {
    afficherMessage('🔍', 'Aucun produit pour ce filtre.');
    return;
  }
  masquerMessage();
  liste.forEach(rendreGroupe);
}

// ── Groupe = une réception ─────────────────────────────────
function rendreGroupe(g) {
  const groupe = document.createElement('div');
  groupe.className = 'pa-groupe';
  groupe.dataset.receptionId = g.reception_id;

  const heure = g.heure_reception ? ` à ${String(g.heure_reception).slice(0, 5)}` : '';
  const nb = g.lignes.length;

  const tete = document.createElement('div');
  tete.className = 'pa-groupe-tete';
  tete.innerHTML = `
    <div class="pa-groupe-info">
      <div class="pa-groupe-fourn">${escHtml(g.fournisseur_nom)}</div>
      <div class="pa-groupe-meta">Livré le ${fmtDateFR(g.date_reception)}${heure} · Réception n°${g.reception_id}</div>
    </div>
    <span class="pa-groupe-badge">${nb} à compléter</span>
    <button class="pa-groupe-reprendre" type="button">🔍 OCR du BL</button>
  `;
  const btnOcr = tete.querySelector('.pa-groupe-reprendre');
  btnOcr.addEventListener('click', () => lancerOcrGroupe(g, btnOcr, statut));

  const statut = document.createElement('div');
  statut.className = 'pa-groupe-statut';
  statut.hidden = true;

  // Aperçu du BL enregistré (vignettes de toutes les pages) — chargé en différé.
  const blZone = document.createElement('div');
  blZone.className = 'pa-bl';
  blZone.innerHTML = '<span class="pa-bl-label">📎 BL…</span>';
  chargerApercuBl(g.reception_id, blZone);

  const corps = document.createElement('div');
  corps.className = 'pa-groupe-corps';
  // Index des cartes par ligne_id pour pré-remplissage OCR.
  g._cartes = {};
  g.lignes.forEach(l => {
    const carte = rendreCarte(l);
    g._cartes[l.ligne_id] = carte;
    corps.appendChild(carte);
  });

  groupe.appendChild(tete);
  groupe.appendChild(statut);
  groupe.appendChild(blZone);
  groupe.appendChild(corps);
  elListe.appendChild(groupe);
}

// ── Aperçu du BL enregistré (toutes les pages) ─────────────
async function chargerApercuBl(receptionId, zone) {
  let data;
  try {
    data = await apiFetch(`/api/receptions/${receptionId}/bl-apercu`);
  } catch {
    zone.innerHTML = '<span class="pa-bl-manquant">⚠️ BL indisponible</span>';
    ajouterBoutonAjoutBl(receptionId, zone);
    return;
  }

  const pages = data.pages || [];
  zone.innerHTML = pages.length
    ? `<span class="pa-bl-label">📎 BL — ${pages.length} page(s)&nbsp;:</span>`
    : '<span class="pa-bl-manquant">⚠️ Aucune photo de BL — ajoutez-la ci-contre</span>';

  const urls = pages.map(p => p.url);
  pages.forEach((p, idx) => {
    const img = document.createElement('img');
    img.className = 'pa-bl-vignette';
    img.src = p.url;
    img.alt = `BL page ${idx + 1}`;
    img.title = `Voir la page ${idx + 1}`;
    img.addEventListener('click', () => ouvrirViewer(urls, idx));
    zone.appendChild(img);
  });

  ajouterBoutonAjoutBl(receptionId, zone);
}

// Bouton « + Ajouter une page de BL » (photo ou fichier image/PDF).
function ajouterBoutonAjoutBl(receptionId, zone) {
  // Input caméra (rear camera, image uniquement)
  const inputCam = document.createElement('input');
  inputCam.type = 'file';
  inputCam.accept = 'image/*';
  inputCam.capture = 'environment';
  inputCam.hidden = true;

  // Input fichier (image ou PDF, multiple)
  const inputFich = document.createElement('input');
  inputFich.type = 'file';
  inputFich.accept = 'image/*,application/pdf';
  inputFich.multiple = true;
  inputFich.hidden = true;

  const btnCam = document.createElement('button');
  btnCam.type = 'button';
  btnCam.className = 'pa-bl-ajout';
  btnCam.textContent = '📷 Photo';
  btnCam.addEventListener('click', () => inputCam.click());

  const btnFich = document.createElement('button');
  btnFich.type = 'button';
  btnFich.className = 'pa-bl-ajout';
  btnFich.textContent = '📁 Fichier';
  btnFich.addEventListener('click', () => inputFich.click());

  async function envoyerFichiers(files, btn) {
    if (!files || !files.length) return;
    const labelInit = btn.textContent;
    btn.disabled = true;
    btnCam.disabled = true;
    btnFich.disabled = true;
    btn.textContent = '⏳ Envoi…';
    const fd = new FormData();
    [...files].forEach(f => fd.append('fichier', f, f.name));
    try {
      await apiFetch(`/api/receptions/${receptionId}/bl-pages`, { method: 'POST', body: fd });
      await chargerApercuBl(receptionId, zone);
    } catch (e) {
      btn.disabled = false;
      btnCam.disabled = false;
      btnFich.disabled = false;
      btn.textContent = labelInit;
      alert('Ajout du BL impossible : ' + e.message);
    }
  }

  inputCam.addEventListener('change',  () => envoyerFichiers(inputCam.files,  btnCam));
  inputFich.addEventListener('change', () => envoyerFichiers(inputFich.files, btnFich));

  zone.appendChild(btnCam);
  zone.appendChild(btnFich);
  zone.appendChild(inputCam);
  zone.appendChild(inputFich);
}

// ── Visionneuse plein écran ────────────────────────────────
let viewerUrls = [];
let viewerIdx  = 0;

function ouvrirViewer(urls, idx) {
  viewerUrls = urls;
  viewerIdx = idx;
  majViewer();
  elViewer.hidden = false;
}
function majViewer() {
  elViewerImg.src = viewerUrls[viewerIdx] || '';
  elViewerTit.textContent = `Page ${viewerIdx + 1} / ${viewerUrls.length}`;
  elViewerPrec.disabled = viewerIdx <= 0;
  elViewerSuiv.disabled = viewerIdx >= viewerUrls.length - 1;
}
function fermerViewer() { elViewer.hidden = true; elViewerImg.src = ''; }

if (elViewerFerm) elViewerFerm.addEventListener('click', fermerViewer);
if (elViewerPrec) elViewerPrec.addEventListener('click', () => { if (viewerIdx > 0) { viewerIdx--; majViewer(); } });
if (elViewerSuiv) elViewerSuiv.addEventListener('click', () => { if (viewerIdx < viewerUrls.length - 1) { viewerIdx++; majViewer(); } });
if (elViewer) elViewer.addEventListener('click', e => { if (e.target === elViewer) fermerViewer(); });
document.addEventListener('keydown', e => {
  if (elViewer.hidden) return;
  if (e.key === 'Escape') fermerViewer();
  else if (e.key === 'ArrowLeft'  && viewerIdx > 0) { viewerIdx--; majViewer(); }
  else if (e.key === 'ArrowRight' && viewerIdx < viewerUrls.length - 1) { viewerIdx++; majViewer(); }
});

// ── OCR du BL pour un groupe-réception ─────────────────────
// Lit la/les photo(s) BL déjà stockées et pré-remplit lot/DLC des cartes en
// attente de cette réception, par correspondance de désignation. Rien n'est
// enregistré : l'utilisateur contrôle puis valide chaque carte normalement.
async function lancerOcrGroupe(g, btn, statut) {
  btn.disabled = true;
  const labelInit = btn.textContent;
  btn.textContent = '⏳ Lecture…';
  statut.hidden = false;
  statut.className = 'pa-groupe-statut';
  statut.textContent = 'Analyse du bon de livraison…';

  let data;
  try {
    data = await apiFetch(`/api/receptions/${g.reception_id}/ocr-bl`, { method: 'POST' });
  } catch (e) {
    btn.disabled = false;
    btn.textContent = labelInit;
    statut.className = 'pa-groupe-statut erreur';
    statut.textContent = `⚠️ ${e.message.includes('Aucune photo')
      ? 'Aucune photo de BL pour cette réception.'
      : 'Lecture du BL impossible. Réessayez ou saisissez à la main.'}`;
    return;
  }

  const articles = data.lignes || [];
  if (!articles.length) {
    btn.disabled = false;
    btn.textContent = labelInit;
    statut.className = 'pa-groupe-statut erreur';
    statut.textContent = '⚠️ Aucun article lu sur le BL. Saisie manuelle nécessaire.';
    return;
  }

  // Correspondance article OCR ↔ carte en attente (par désignation normalisée).
  let nbRemplis = 0;
  let nbSuspects = 0;
  let nbNonRapproches = 0;
  const articlesDispo = [...articles];

  g.lignes.forEach(ligne => {
    const carte = g._cartes[ligne.ligne_id];
    if (!carte) return;
    const idx = articlesDispo.findIndex(a => correspond(a.designation, ligne.produit_nom));
    if (idx === -1) { nbNonRapproches++; return; }
    const art = articlesDispo.splice(idx, 1)[0];  // consommé : pas de réutilisation

    const inpLot  = carte.querySelector('[data-field="numero_lot"]');
    const inpDlc  = carte.querySelector('[data-field="dlc"]');  // null si date_abattage / no_dlc
    let rempli = false;
    if (inpLot && art.numero_lot) { inpLot.value = art.numero_lot; rempli = true; }
    // L'OCR lit une DLC : on ne pré-remplit que les cartes attendant une DLC
    // (les articles 'date_abattage' gardent la saisie manuelle de la date d'abattage).
    if (inpDlc && art.dlc) { inpDlc.value = art.dlc; rempli = true; }
    if (rempli) nbRemplis++;

    if (art.dlc_suspecte) {
      nbSuspects++;
      carte.classList.add('pa-carte--suspect');
      const err = carte.querySelector('.pa-erreur');
      if (err) {
        err.hidden = false;
        err.textContent = `⚠️ ${art.alerte || 'Date à vérifier'} — contrôlez avant de valider.`;
      }
    }
  });

  btn.disabled = false;
  btn.textContent = '🔄 Relancer l\'OCR';
  // S'il reste des produits en attente non rapprochés, c'est souvent qu'une page
  // du BL manque (ou que la désignation diffère) → on le signale clairement.
  const alerteManque = nbNonRapproches
    ? ` — ⚠️ ${nbNonRapproches} produit(s) non trouvé(s) sur le BL : vérifiez qu'aucune page ne manque (📎 ci-dessus) ou saisissez à la main.`
    : '';
  if (nbRemplis) {
    statut.className = nbNonRapproches ? 'pa-groupe-statut' : 'pa-groupe-statut ok';
    statut.textContent = `✓ ${nbRemplis} produit(s) pré-remplis depuis le BL`
      + (nbSuspects ? ` (⚠️ ${nbSuspects} date(s) à vérifier, surlignées)` : '')
      + '.' + alerteManque
      + ' Contrôlez puis validez chaque ligne.';
  } else {
    statut.className = 'pa-groupe-statut erreur';
    statut.textContent = '⚠️ Articles lus mais aucun n\'a pu être rapproché des produits en attente.'
      + alerteManque + ' Saisie manuelle nécessaire.';
  }
}

// Rapprochement souple de deux désignations (insensible casse/accents/ponctuation).
function correspond(a, b) {
  const norm = s => String(s || '')
    .toLowerCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
  const na = norm(a), nb = norm(b);
  if (!na || !nb) return false;
  if (na === nb) return true;
  // Sous-chaîne dans un sens ou l'autre (ex. "PALERON VB" ⊃ "PALERON")
  return na.includes(nb) || nb.includes(na);
}

// ── Carte d'un produit en attente ──────────────────────────
function rendreCarte(ligne) {
  const carte = document.createElement('div');
  carte.className = 'pa-carte';
  carte.dataset.ligneId = ligne.ligne_id;

  const dateAbattage = attendDateAbattage(ligne);

  // Bloc identité produit + réception
  const sousParts = [];
  if (ligne.fournisseur_nom) sousParts.push(escHtml(ligne.fournisseur_nom));
  sousParts.push(`Reçu le ${fmtDateFR(ligne.date_reception)}`);
  if (ligne.poids_kg) sousParts.push(`${ligne.poids_kg} kg`);

  carte.innerHTML = `
    <div class="pa-carte-titre">${escHtml(ligne.produit_nom || 'Produit')}</div>
    <div class="pa-carte-sous">${sousParts.join(' · ')}</div>
    <div class="pa-carte-motif">${escHtml(libelleMotif(ligne.attente_motif))}</div>

    <div class="pa-champ">
      <label class="pa-champ-label">N° de lot</label>
      <input type="text" class="pa-input" data-field="numero_lot"
             value="${escHtml(ligne.numero_lot || '')}"
             placeholder="N° de lot du bon de livraison…">
      <button class="pa-btn-lot-interne" type="button">
        🏷️ Pas de N° de lot → générer un lot interne
      </button>
    </div>

    <div class="pa-champ">
      <label class="pa-champ-label">${dateAbattage ? "Date d'abattage" : 'DLC'}</label>
      <input type="date" class="pa-input"
             data-field="${dateAbattage ? 'date_abattage' : 'dlc'}"
             value="${escHtml(dateAbattage ? (ligne.date_abattage || '') : (ligne.dlc || ''))}">
    </div>

    <button class="pa-btn-valider" type="button">✓ Valider et entrer en stock</button>
    <button class="pa-btn-changer-produit" type="button">🔄 Changer de produit</button>
    <button class="pa-btn-non-recu" type="button">✗ Non reçu</button>
    <div class="pa-erreur" hidden></div>

    <div class="pa-recherche-produit" hidden>
      <div class="pa-recherche-entete">
        <span>Choisir un article du catalogue</span>
        <button class="pa-recherche-fermer" type="button" aria-label="Fermer">✕</button>
      </div>
      <div class="pa-recherche-corps">
        <input class="pa-recherche-input" type="search"
               placeholder="Code article ou désignation…"
               autocomplete="off" autocorrect="off" spellcheck="false">
        <div class="pa-recherche-hint">Tapez au moins 2 caractères</div>
        <div class="pa-recherche-resultats"></div>
      </div>
    </div>
  `;

  const btn    = carte.querySelector('.pa-btn-valider');
  const erreur = carte.querySelector('.pa-erreur');
  btn.addEventListener('click', () => valider(carte, ligne, btn, erreur));

  const btnLot = carte.querySelector('.pa-btn-lot-interne');
  if (btnLot) btnLot.addEventListener('click', () => genererLotInterne(carte, ligne, btnLot, erreur));

  const btnNonRecu = carte.querySelector('.pa-btn-non-recu');
  if (btnNonRecu) btnNonRecu.addEventListener('click', () => marquerNonRecu(carte, ligne, btnNonRecu, erreur));

  const btnChanger  = carte.querySelector('.pa-btn-changer-produit');
  const panneauRech = carte.querySelector('.pa-recherche-produit');
  const inputRech   = carte.querySelector('.pa-recherche-input');
  const btnFermRech = carte.querySelector('.pa-recherche-fermer');
  const divResultats = carte.querySelector('.pa-recherche-resultats');

  if (btnChanger) btnChanger.addEventListener('click', () => {
    panneauRech.hidden = !panneauRech.hidden;
    if (!panneauRech.hidden) { inputRech.value = ''; divResultats.innerHTML = ''; inputRech.focus(); }
  });
  if (btnFermRech) btnFermRech.addEventListener('click', () => { panneauRech.hidden = true; });

  let _rchTimer;
  if (inputRech) inputRech.addEventListener('input', () => {
    clearTimeout(_rchTimer);
    _rchTimer = setTimeout(() => rechercherProduit(inputRech.value, ligne, divResultats, carte, panneauRech, erreur), 280);
  });

  return carte;
}

// ── Génération d'un lot interne {BL}-{code article}-{JJMMAA} ──
// Pour les fournisseurs sans N° de lot. Exige le n° BL de la réception : s'il
// manque, on le demande puis on l'enregistre avant de générer.
async function genererLotInterne(carte, ligne, btnLot, erreur) {
  erreur.hidden = true;
  // Le n° BL est requis comme préfixe. S'il manque sur la réception, le demander.
  let numeroBl = (ligne.numero_bon_livraison || '').trim();
  if (!numeroBl) {
    const saisi = window.prompt(
      'N° du bon de livraison de cette réception (sert de préfixe au lot interne) :',
      ''
    );
    if (saisi === null) return;            // annulé
    numeroBl = saisi.trim();
    if (!numeroBl) {
      erreur.textContent = 'N° de bon de livraison requis pour générer un lot interne.';
      erreur.hidden = false;
      return;
    }
    try {
      await apiFetch(`/api/receptions/${ligne.reception_id}/numero-bl`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ numero_bon_livraison: numeroBl }),
      });
      // Propager à toutes les lignes de la même réception (cache local).
      toutesLignes.forEach(l => {
        if (l.reception_id === ligne.reception_id) l.numero_bon_livraison = numeroBl;
      });
    } catch (e) {
      erreur.textContent = 'Enregistrement du n° BL impossible : ' + e.message;
      erreur.hidden = false;
      return;
    }
  }

  btnLot.disabled = true;
  const labelInit = btnLot.textContent;
  btnLot.textContent = '⏳…';
  try {
    const data = await apiFetch(
      `/api/receptions/${ligne.reception_id}/lignes/${ligne.ligne_id}/lot-interne`
    );
    const inpLot = carte.querySelector('[data-field="numero_lot"]');
    inpLot.value = data.lot_interne;
    inpLot.classList.remove('pa-input--invalide');
    inpLot.readOnly = true;
    inpLot.style.background = '#f0faf3';
    carte.dataset.lotInterne = '1';   // signalé au backend lors de la validation
  } catch (e) {
    erreur.textContent = 'Génération du lot interne impossible : ' + e.message;
    erreur.hidden = false;
  } finally {
    btnLot.disabled = false;
    btnLot.textContent = labelInit;
  }
}

// ── Validation / complétion ────────────────────────────────
async function valider(carte, ligne, btn, erreur) {
  erreur.hidden = true;
  const inputs = carte.querySelectorAll('.pa-input');
  const payload = {};
  inputs.forEach(inp => {
    inp.classList.remove('pa-input--invalide');
    const v = inp.value.trim();
    if (v) payload[inp.dataset.field] = v;
  });
  // Lot auto-généré (interne) : informer le backend pour la traçabilité.
  if (carte.dataset.lotInterne === '1') payload.lot_interne = 1;

  // Validation côté client : lot + date requis (sauf no_dlc pour la date)
  const manqueLot  = !payload.numero_lot;
  const dateAbattage = attendDateAbattage(ligne);
  const noDlc      = ligne.dlc_type === 'no_dlc';
  const manqueDate = !noDlc && !(dateAbattage ? payload.date_abattage : payload.dlc);

  if (manqueLot || manqueDate) {
    inputs.forEach(inp => {
      if ((inp.dataset.field === 'numero_lot' && manqueLot) ||
          (inp.dataset.field !== 'numero_lot' && manqueDate)) {
        inp.classList.add('pa-input--invalide');
      }
    });
    erreur.textContent = 'Renseignez le N° de lot et la date pour valider.';
    erreur.hidden = false;
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Validation…';
  try {
    const res = await apiFetch(`/api/attente/lignes/${ligne.ligne_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.statut === 'complet') {
      // Produit complété → le produit entre en stock. On le retire de la source
      // de vérité puis on re-rend (le groupe disparaît s'il devient vide).
      toutesLignes = toutesLignes.filter(l => l.ligne_id !== ligne.ligne_id);
      if (!toutesLignes.length) {
        elBarre.hidden = true;
        elCompteur.textContent = '';
        afficherMessage('✅', 'Aucun produit en attente — tout est tracé !');
      } else {
        remplirFiltreFournisseurs();
        rendre();
      }
    } else {
      erreur.textContent = 'Il manque encore une information pour finaliser.';
      erreur.hidden = false;
      btn.disabled = false;
      btn.textContent = '✓ Valider et entrer en stock';
    }
  } catch (e) {
    erreur.textContent = 'Erreur lors de l’enregistrement. Réessayez.';
    erreur.hidden = false;
    btn.disabled = false;
    btn.textContent = '✓ Valider et entrer en stock';
  }
}

// ── Recherche catalogue pour changer le produit d'une ligne ────────────────
async function rechercherProduit(q, ligne, divResultats, carte, panneau, erreur) {
  const terme = (q || '').trim();
  if (terme.length < 2) {
    divResultats.innerHTML = '';
    return;
  }
  divResultats.innerHTML = '<div class="pa-recherche-vide">⏳ Recherche…</div>';

  const params = new URLSearchParams({ q: terme, actif_only: 'true' });
  if (ligne.fournisseur_id) params.set('fournisseur_id', ligne.fournisseur_id);

  let articles;
  try {
    articles = await apiFetch(`/api/achats/catalogue?${params}`);
  } catch {
    divResultats.innerHTML = '<div class="pa-recherche-vide">⚠️ Erreur de recherche</div>';
    return;
  }

  if (!articles.length) {
    divResultats.innerHTML = '<div class="pa-recherche-vide">Aucun article trouvé</div>';
    return;
  }

  divResultats.innerHTML = '';
  articles.slice(0, 20).forEach(art => {
    const item = document.createElement('div');
    item.className = 'pa-recherche-item';
    item.innerHTML = `
      <div class="pa-recherche-item-nom">${escHtml(art.designation)}</div>
      <div class="pa-recherche-item-code">${escHtml(art.code_article)} · ${escHtml(art.fournisseur_nom || '')}</div>
    `;
    item.addEventListener('click', () =>
      appliquerChangementProduit(art, ligne, carte, panneau, erreur)
    );
    divResultats.appendChild(item);
  });
}

async function appliquerChangementProduit(art, ligne, carte, panneau, erreur) {
  erreur.hidden = true;
  panneau.hidden = true;

  const titreCarte = carte.querySelector('.pa-carte-titre');
  const sousCarte  = carte.querySelector('.pa-carte-sous');
  const labelOrig  = titreCarte ? titreCarte.textContent : '';

  if (titreCarte) titreCarte.textContent = '⏳ Mise à jour…';

  try {
    const res = await apiFetch(`/api/attente/lignes/${ligne.ligne_id}/produit`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ catalogue_fournisseur_id: art.id }),
    });

    // Mettre à jour l'objet ligne en mémoire
    ligne.produit_nom           = art.designation;
    ligne.code_article          = art.code_article;
    ligne.dlc_type              = res.dlc_type || art.dlc_type || 'dlc';
    ligne.attente_motif         = res.attente_motif;
    ligne.catalogue_fournisseur_id = art.id;

    // Rafraîchir l'en-tête de la carte
    if (titreCarte) titreCarte.textContent = art.designation;
    if (sousCarte) {
      const parts = [];
      if (ligne.fournisseur_nom) parts.push(escHtml(ligne.fournisseur_nom));
      parts.push(`Reçu le ${fmtDateFR(ligne.date_reception)}`);
      if (ligne.poids_kg) parts.push(`${ligne.poids_kg} kg`);
      sousCarte.textContent = parts.join(' · ');
    }

    // Mettre à jour le label DLC si nécessaire
    const dateAbattage = ligne.dlc_type === 'date_abattage';
    const inputDate = carte.querySelector('[data-field="dlc"], [data-field="date_abattage"]');
    const labelDate = inputDate ? inputDate.closest('.pa-champ')?.querySelector('.pa-champ-label') : null;
    if (labelDate) labelDate.textContent = dateAbattage ? "Date d'abattage" : 'DLC';
    if (inputDate) {
      const newField = dateAbattage ? 'date_abattage' : 'dlc';
      inputDate.dataset.field = newField;
      inputDate.value = '';
    }

    // Mettre à jour dans toutesLignes
    const idx = toutesLignes.findIndex(l => l.ligne_id === ligne.ligne_id);
    if (idx !== -1) Object.assign(toutesLignes[idx], ligne);

  } catch (e) {
    if (titreCarte) titreCarte.textContent = labelOrig;
    erreur.textContent = 'Changement de produit impossible : ' + e.message;
    erreur.hidden = false;
  }
}

// ── Marquer "non reçu" (2 taps : premier = demande, second = confirme) ─────
async function marquerNonRecu(carte, ligne, btn, erreur) {
  erreur.hidden = true;

  // Premier tap : demande de confirmation
  if (!btn.classList.contains('confirmer')) {
    btn.classList.add('confirmer');
    btn.textContent = '⚠️ Confirmer : non reçu ?';
    // Reset automatique après 4 s si l'utilisateur ne confirme pas
    const timer = setTimeout(() => {
      btn.classList.remove('confirmer');
      btn.textContent = '✗ Non reçu';
    }, 4000);
    btn.dataset.confirmTimer = timer;
    return;
  }

  // Second tap : confirmation
  clearTimeout(Number(btn.dataset.confirmTimer));
  btn.disabled = true;
  btn.textContent = '⏳…';

  try {
    await apiFetch(`/api/attente/lignes/${ligne.ligne_id}/non-recu`, { method: 'PUT' });
    // Retirer de la source de vérité et re-rendre
    toutesLignes = toutesLignes.filter(l => l.ligne_id !== ligne.ligne_id);
    if (!toutesLignes.length) {
      elBarre.hidden = true;
      elCompteur.textContent = '';
      afficherMessage('✅', 'Aucun produit en attente — tout est tracé !');
    } else {
      remplirFiltreFournisseurs();
      rendre();
    }
  } catch (e) {
    btn.disabled = false;
    btn.classList.remove('confirmer');
    btn.textContent = '✗ Non reçu';
    erreur.textContent = 'Erreur lors de l\'enregistrement. Réessayez.';
    erreur.hidden = false;
  }
}

// ── Contrôles filtre / tri ─────────────────────────────────
if (elFiltreFourn) elFiltreFourn.addEventListener('change', rendre);
if (elTri)         elTri.addEventListener('change', rendre);

// ── Init ───────────────────────────────────────────────────
charger();

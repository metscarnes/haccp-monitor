'use strict';
/* ============================================================
   reception.js — Module Réception marchandises (wizard v2)
   Au Comptoir des Lilas — Mets Carnés Holding

   Flux : Personnel → Camion → Photo BL / Fournisseur
          → Produits (boucle) → Récap & Clôture → Confirmation
   ============================================================ */

// ── Références DOM ─────────────────────────────────────────
const elHorloge        = document.getElementById('rec-horloge');
const elBtnRetour      = document.getElementById('rec-btn-retour');
const elProgress       = document.getElementById('rec-progress');
const elBandeau        = document.getElementById('rec-bandeau');
const DOTS             = [0,1,2,3,4].map(i => document.getElementById(`dot-${i}`));

const elStep0          = document.getElementById('rec-step-0');
const elStep1          = document.getElementById('rec-step-1');
const elStep2          = document.getElementById('rec-step-2');
const elStep3          = document.getElementById('rec-step-3');
const elStep4          = document.getElementById('rec-step-4');
const elStepConfirm    = document.getElementById('rec-step-confirm');
const STEPS            = [elStep0, elStep1, elStep2, elStep3, elStep4, elStepConfirm];

// Si retour depuis pcr01.html, masquer step-0 immédiatement pour éviter le
// flash de l'écran sélection opérateur avant que restaurerDepuisPcr01()
// ne saute à l'étape 4 (init() awaite plusieurs référentiels avant).
if (sessionStorage.getItem('haccp_rec_state') && elStep0) {
  elStep0.classList.remove('actif');
}

// Étape 0
const elPersonnelGrille   = document.getElementById('rec-personnel-grille');
const elChargementPerso   = document.getElementById('rec-chargement-personnel');
// Bandeau « réception non terminée »
const elRepriseBandeau    = document.getElementById('rec-reprise-bandeau');
const elRepriseTxt        = document.getElementById('rec-reprise-txt');
const elRepriseReprendre  = document.getElementById('rec-reprise-reprendre');
const elRepriseAbandonner = document.getElementById('rec-reprise-abandonner');

// Étape 1
const elDateReception     = document.getElementById('rec-date-reception');
const elHeure             = document.getElementById('rec-heure');
const elTempCamion        = document.getElementById('rec-temp-camion');
const elPropreteOk        = document.getElementById('rec-proprete-ok');
const elPropreteNc        = document.getElementById('rec-proprete-nc');
const elCamionBadge       = document.getElementById('rec-camion-badge');
const elBtnCamionSuivant  = document.getElementById('rec-btn-camion-suivant');

// Overlay aperçu photo BL
const elPhotoPreviewOverlay = document.getElementById('rec-photo-preview-overlay');
const elPhotoPreviewImg     = document.getElementById('rec-photo-preview-img');
const elPhotoPreviewClose   = document.getElementById('rec-photo-preview-close');
if (elPhotoPreviewClose) {
  elPhotoPreviewClose.addEventListener('click', () => { elPhotoPreviewOverlay.hidden = true; });
}
if (elPhotoPreviewOverlay) {
  elPhotoPreviewOverlay.addEventListener('click', e => {
    if (e.target === elPhotoPreviewOverlay) elPhotoPreviewOverlay.hidden = true;
  });
}
function ouvrirApercuPhoto(url) {
  elPhotoPreviewImg.src = url;
  elPhotoPreviewOverlay.hidden = false;
}

// ── Fenêtre flottante BL (non-modale, déplaçable / zoomable / redimensionnable) ──
const elBlFlottant       = document.getElementById('rec-bl-flottant');
const elBlBarre          = document.getElementById('rec-bl-flottant-barre');
const elBlImg            = document.getElementById('rec-bl-flottant-img');
const elBlFermer         = document.getElementById('rec-bl-flottant-fermer');
const elBlZoomPlus       = document.getElementById('rec-bl-zoom-plus');
const elBlZoomMoins      = document.getElementById('rec-bl-zoom-moins');
const elBlResize         = document.getElementById('rec-bl-flottant-resize');
let blZoom = 1;
let blPages = [];
let blPageIdx = 0;

function majNavBl() {
  const nav = document.getElementById('rec-bl-nav');
  if (!nav) return;
  if (blPages.length <= 1) { nav.hidden = true; return; }
  nav.hidden = false;
  const label = nav.querySelector('#rec-bl-nav-label');
  const prev  = nav.querySelector('#rec-bl-nav-prev');
  const next  = nav.querySelector('#rec-bl-nav-next');
  if (label) label.textContent = `${blPageIdx + 1} / ${blPages.length}`;
  if (prev)  prev.disabled  = blPageIdx === 0;
  if (next)  next.disabled  = blPageIdx === blPages.length - 1;
}

function ouvrirBlFlottant(url, allUrls) {
  if (!elBlFlottant) return;
  blPages   = allUrls && allUrls.length ? allUrls : [url];
  blPageIdx = 0;
  elBlImg.src = blPages[0];
  blZoom = 1;
  appliquerZoomBl();
  majNavBl();
  elBlFlottant.style.left = Math.max(8, (window.innerWidth - elBlFlottant.offsetWidth) / 2) + 'px';
  elBlFlottant.hidden = false;
}
function appliquerZoomBl() {
  // Zoom = largeur de l'image relative au corps (overflow auto permet de naviguer)
  elBlImg.style.width = (blZoom * 100) + '%';
}
if (elBlFermer)    elBlFermer.addEventListener('click', () => { elBlFlottant.hidden = true; });
if (elBlZoomPlus)  elBlZoomPlus.addEventListener('click', () => { blZoom = Math.min(5, blZoom + 0.25); appliquerZoomBl(); });
if (elBlZoomMoins) elBlZoomMoins.addEventListener('click', () => { blZoom = Math.max(0.5, blZoom - 0.25); appliquerZoomBl(); });
document.getElementById('rec-bl-nav-prev')?.addEventListener('click', () => {
  if (blPageIdx > 0) { blPageIdx--; elBlImg.src = blPages[blPageIdx]; majNavBl(); }
});
document.getElementById('rec-bl-nav-next')?.addEventListener('click', () => {
  if (blPageIdx < blPages.length - 1) { blPageIdx++; elBlImg.src = blPages[blPageIdx]; majNavBl(); }
});

// Déplacement de la fenêtre via la barre de titre (souris + tactile)
function initDragBl() {
  if (!elBlBarre || !elBlFlottant) return;
  let startX, startY, startLeft, startTop, dragging = false;
  const onDown = (e) => {
    // ne pas déclencher le drag depuis les boutons d'action
    if (e.target.closest('.rec-bl-flottant-actions')) return;
    dragging = true;
    const p = e.touches ? e.touches[0] : e;
    startX = p.clientX; startY = p.clientY;
    const r = elBlFlottant.getBoundingClientRect();
    startLeft = r.left; startTop = r.top;
    e.preventDefault();
  };
  const onMove = (e) => {
    if (!dragging) return;
    const p = e.touches ? e.touches[0] : e;
    let nl = startLeft + (p.clientX - startX);
    let nt = startTop  + (p.clientY - startY);
    // garder la fenêtre dans le viewport
    nl = Math.max(0, Math.min(nl, window.innerWidth  - 60));
    nt = Math.max(0, Math.min(nt, window.innerHeight - 40));
    elBlFlottant.style.left = nl + 'px';
    elBlFlottant.style.top  = nt + 'px';
    e.preventDefault();
  };
  const onUp = () => { dragging = false; };
  elBlBarre.addEventListener('mousedown', onDown);
  elBlBarre.addEventListener('touchstart', onDown, { passive: false });
  document.addEventListener('mousemove', onMove);
  document.addEventListener('touchmove', onMove, { passive: false });
  document.addEventListener('mouseup', onUp);
  document.addEventListener('touchend', onUp);
}
// Redimensionnement via la poignée coin bas-droit
function initResizeBl() {
  if (!elBlResize || !elBlFlottant) return;
  let startX, startY, startW, startH, resizing = false;
  const onDown = (e) => {
    resizing = true;
    const p = e.touches ? e.touches[0] : e;
    startX = p.clientX; startY = p.clientY;
    const r = elBlFlottant.getBoundingClientRect();
    startW = r.width; startH = r.height;
    e.preventDefault(); e.stopPropagation();
  };
  const onMove = (e) => {
    if (!resizing) return;
    const p = e.touches ? e.touches[0] : e;
    elBlFlottant.style.width  = Math.max(240, startW + (p.clientX - startX)) + 'px';
    elBlFlottant.style.height = Math.max(220, startH + (p.clientY - startY)) + 'px';
    e.preventDefault();
  };
  const onUp = () => { resizing = false; };
  elBlResize.addEventListener('mousedown', onDown);
  elBlResize.addEventListener('touchstart', onDown, { passive: false });
  document.addEventListener('mousemove', onMove);
  document.addEventListener('touchmove', onMove, { passive: false });
  document.addEventListener('mouseup', onUp);
  document.addEventListener('touchend', onUp);
}
initDragBl();
initResizeBl();

// Étape 2
const elFournUnBtn        = document.getElementById('rec-fourn-un-btn');
const elFournMultiBtn     = document.getElementById('rec-fourn-multi-btn');
const elFournListe        = document.getElementById('rec-fourn-liste');
const elBtnAddFourn       = document.getElementById('rec-btn-add-fourn');
const elErreur2           = document.getElementById('rec-erreur-2');
const elBtnCreerFiche     = document.getElementById('rec-btn-creer-fiche');
// Legacy refs (kept pour compatibilité, pointent vers éléments vides)
const elFournResults      = document.getElementById('rec-fourn-results');
const elFournSelWrap      = document.getElementById('rec-fourn-sel-wrap');
const elFournSearchWrap   = document.getElementById('rec-fourn-search-wrap');

// Étape 3
const elFournProduitGroupe = document.getElementById('rec-fourn-produit-groupe');
const elFournProduitSel = document.getElementById('rec-fourn-produit-sel');
const elNbProduits        = document.getElementById('rec-nb-produits');
const elLignesListe       = document.getElementById('rec-lignes-liste');
const elProdSel           = document.getElementById('rec-produit-selectionne-wrap');
const elProdSelNom        = document.getElementById('rec-prod-sel-nom');
const elProdSelCode       = document.getElementById('rec-prod-sel-code');
const elBtnChangerProduit = document.getElementById('rec-btn-changer-produit');
const elProdSearchWrap    = document.getElementById('rec-produit-search-wrap');
const elProdSearch        = document.getElementById('rec-prod-search');
const elProdAutoComplete  = document.getElementById('rec-prod-autocomplete');
const elLot               = document.getElementById('rec-lot');
const elNumeroBl          = document.getElementById('rec-numero-bl');
const elBtnBlValider      = document.getElementById('rec-btn-bl-valider');
const elNumeroBlHint      = document.getElementById('rec-numero-bl-hint');
const elBtnPasLot         = document.getElementById('rec-btn-pas-lot');
const elBtnAnnulerLot     = document.getElementById('rec-btn-annuler-lot');
const elLotGenere         = document.getElementById('rec-lot-genere');
const elLotsSupp          = document.getElementById('rec-lots-supp');
const elBtnAddLot         = document.getElementById('rec-btn-add-lot');
const elLotsSuppHint      = document.getElementById('rec-lots-supp-hint');
const elBtnLotsCommande   = document.getElementById('rec-btn-lots-commande');
const elLotsCommandeHint  = document.getElementById('rec-lots-commande-hint');
const elOrigine           = document.getElementById('rec-origine');
const elOrigineToggle     = document.getElementById('rec-origine-toggle');
const elOrigineList       = document.getElementById('rec-origine-suggestions-list');
const elDlc               = document.getElementById('rec-dlc');
const elDlcBtn            = document.getElementById('rec-dlc-btn');
const elDluoBtn           = document.getElementById('rec-dluo-btn');
const elDlcLabelText      = document.getElementById('rec-dlc-label-text');
const elPh                = document.getElementById('rec-ph');
const elPhPlage           = document.getElementById('rec-ph-plage');
const elBtnAjouter        = document.getElementById('rec-btn-ajouter');
const elBtnEnregistrer    = document.getElementById('rec-btn-enregistrer');
const elBtnTerminer       = document.getElementById('rec-btn-terminer');

// Critères visuels
const CRITERES = ['couleur', 'consistance', 'exsudat', 'odeur'];

// Étape 4 — Récap
const elRecapCamionInfo   = document.getElementById('rec-recap-camion-info');
const elRecapCamionBadge  = document.getElementById('rec-recap-camion-badge');
const elConformiteGlobale = document.getElementById('rec-conformite-globale');
const elRecapLignes       = document.getElementById('rec-recap-lignes');
const elCommentaireNc     = document.getElementById('rec-commentaire-nc');
const elErreur4           = document.getElementById('rec-erreur-4');
const elBtnCloturer       = document.getElementById('rec-btn-cloturer');
const elBlocCreerCommande = document.getElementById('rec-bloc-creer-commande');
const elBtnCreerCommande  = document.getElementById('rec-btn-creer-commande');
const elCreerCmdStatut    = document.getElementById('rec-creer-cmd-statut');

// Substitution
const elSubstitutionCheck   = document.getElementById('rec-substitution-check');
const elSubstitutionWrap    = document.getElementById('rec-substitution-wrap');
const elSubstitutionSearch  = document.getElementById('rec-substitution-search');
const elSubstitutionResults = document.getElementById('rec-substitution-results');
const elSubstitutionSel     = document.getElementById('rec-substitution-sel');
const elSubstitutionSelNom  = document.getElementById('rec-substitution-sel-nom');
const elSubstitutionClear   = document.getElementById('rec-substitution-clear');

// Étape 4 — Procédure NC
const elNcProcedure       = document.getElementById('rec-nc-procedure');
const elNcStepA           = document.getElementById('rec-nc-step-a');
const elNcStepB           = document.getElementById('rec-nc-step-b');
const elNcProduitsCoeur   = document.getElementById('rec-nc-produits-coeur');
const elNcTousConformes   = document.getElementById('rec-nc-tous-conformes');
const elNcBtnASuivant     = document.getElementById('rec-nc-btn-a-suivant');
const elLivreurOui        = document.getElementById('rec-livreur-oui');
const elLivreurNon        = document.getElementById('rec-livreur-non');
const elNcBtnBSuivant     = document.getElementById('rec-nc-btn-b-suivant');
const elPcrDoneBadge      = document.getElementById('rec-pcr-done-badge');

// Confirmation
const elConfirmDetail     = document.getElementById('rec-confirm-detail');
const elConfirmBadge      = document.getElementById('rec-confirm-badge');
const elConfirmCountdown  = document.getElementById('rec-confirm-countdown');
const elBtnHub            = document.getElementById('rec-btn-hub');

// Dialog inactivité
const elDialogInactivite  = document.getElementById('rec-dialog-inactivite');
const elDialogContinuer   = document.getElementById('rec-dialog-continuer');
const elDialogQuitter     = document.getElementById('rec-dialog-quitter');

// Dialog "Même fournisseur ?"
const elDialogFourn       = document.getElementById('rec-dialog-fourn');
const elDialogFournTexte  = document.getElementById('rec-dlg-fourn-texte');
const elDialogFournOui    = document.getElementById('rec-dialog-fourn-oui');
const elDialogFournNon    = document.getElementById('rec-dialog-fourn-non');

// NC propreté camion — détails + photo
const elPropreteNcDetails    = document.getElementById('rec-proprete-nc-details');
const elPropreteCheckboxes   = document.querySelectorAll('#rec-proprete-nc-details input[type="checkbox"]');
const elPropretePhotoZone    = document.getElementById('rec-proprete-photo-zone');
const elPropretePhotoInput   = document.getElementById('rec-proprete-photo-input');
const elPropretePhotoIcone   = document.getElementById('rec-proprete-photo-icone');
const elPropretePhotoSous    = document.getElementById('rec-proprete-photo-sous');
const elPropretePhotoVignette = document.getElementById('rec-proprete-photo-vignette');

// Dialog "Accepter la livraison ?"
const elDialogLivraison      = document.getElementById('rec-dialog-livraison');
const elDialogLivraisonOui   = document.getElementById('rec-dialog-livraison-oui');
const elDialogLivraisonNon   = document.getElementById('rec-dialog-livraison-non');

// Dialog "Refus BL" (multi-BL : 1 photo + 1 fournisseur par BL)
const elDialogRefusBl        = document.getElementById('rec-dialog-refus-bl');
const elRefusBlListe         = document.getElementById('rec-refus-bl-liste');
const elRefusBlAdd           = document.getElementById('rec-refus-bl-add');
const elErreurRefusBl        = document.getElementById('rec-erreur-refus-bl');
const elDialogRefusAnnuler   = document.getElementById('rec-dialog-refus-annuler');
const elDialogRefusValider   = document.getElementById('rec-dialog-refus-valider');

// Badge verdict température temps réel (étape 3)
const elTempVerdict       = document.getElementById('rec-temp-verdict');


// ── État ───────────────────────────────────────────────────
let etape              = 0;
let personnelId        = null;
let personnelPrenom    = null;
let propreteCamion     = 'satisfaisant';
let photoBlFile        = null;
let photoBlObjectUrl   = null;
let fournisseurId      = null;
let receptionId        = null;
let dernierTempCamionEnvoye = null; // dernière temp camion envoyée au serveur
let lignesAjoutees     = [];      // [{id, produit_nom, conforme, motifs, temp, lot, produit_id, fournisseur_id}]
let produitSelectionne = null;    // objet produit complet
let criteres           = {};      // {couleur:1, consistance:1, exsudat:1, odeur:1}
let timerInactivite    = null;
let timerConfirmation  = null;
let debounceTimer      = null;
let tousProduits       = [];
let tousFournisseurs   = [];
let textesAide         = {};

// NC propreté camion state
let propreteProblemes  = [];      // labels des cases cochées
let propretePhotoFile  = null;    // photo du problème de propreté
// Refus livraison : liste des BL refusés (1 par fournisseur)
// [{photoFile, photoUrl, fournisseurId, fournisseurNom}]
let refusBlList        = [];

// NC procedure state
let ncProduits         = [];      // produits NC confirmés (après contrôle à cœur)
let ncProduitsInitiaux = [];      // produits NC initiaux (avant contrôle à cœur)
let ncCoeurResultats   = {};      // {ligne_id: {temp_coeur, conforme_apres_coeur}}
let livreurPresent     = null;    // true | false
let ncFicheIndex       = 0;       // index dans ncProduits pour PCR01

// Mode liste commande (étape 3 batch) : 1 carte par ligne de commande
let modeBatch          = false;   // true quand l'étape 3 affiche la liste commande
let batchLignes        = [];      // [{produit, dlcType, fournisseur, lotInterne, el, criteres, observations}]

// État formulaire produit
let dlcMode            = 'dlc';   // 'dlc' ou 'dluo'
let lotInterneGenere   = false;   // true quand lot interne auto-généré
let numeroBlValide     = '';      // n° BL enregistré sur la réception (préfixe lot interne)
let ligneEnEdition     = null;    // {id, index} — null = mode ajout
let fournisseurProduitSelected = null; // {id, nom} fournisseur sélectionné pour le produit courant
let dernierFournisseurProduit = null; // {id, nom} dernier fournisseur utilisé pour dialog
let substitutionArticle = null;       // {id, designation} article commandé livré en substitut (ou null)

// Lien commande
let commandeIds        = [];      // IDs des commandes liées (tableau)
let commandeLignes     = [];      // lignes de toutes les commandes liées pour pré-remplissage
let commandeLigneIdx   = 0;       // index de la ligne en cours de réception
let catalogueIdPrefill = null;    // catalogue_fournisseur_id de la ligne de commande pré-remplie
                                  // (propagé vers reception_lignes pour le suivi de stock par référence)
let dlcTypePrefill     = null;    // dlc_type du catalogue ('dlc'|'date_abattage'|'no_dlc')
let toutesCommandes    = [];      // cache de toutes les commandes disponibles
let catalogueBl        = [];      // articles catalogue du fournisseur BL (sans commande)
let catalogueBlFournId = null;    // fournisseur_id pour lequel catalogueBl est chargé


// ── Références DOM — Commande ──────────────────────────────
const elCmdNonBtn       = document.getElementById('rec-cmd-non-btn');
const elCmdOuiBtn       = document.getElementById('rec-cmd-oui-btn');
const elCmdSelZone      = document.getElementById('rec-commande-sel-zone');
const elCmdSelect       = null; // legacy — remplacé par la liste dynamique
const elCmdResume       = null; // legacy — remplacé par les résumés inline
const elCommandesListe  = document.getElementById('rec-commandes-liste');
const elBtnAddCommande  = document.getElementById('rec-btn-add-commande');

// ── Toggle "Lier à une commande" ───────────────────────────
if (elCmdNonBtn && elCmdOuiBtn) {
  elCmdNonBtn.addEventListener('click', () => {
    elCmdNonBtn.classList.add('ok-sel');
    elCmdOuiBtn.classList.remove('ok-sel');
    elCmdNonBtn.setAttribute('aria-pressed', 'true');
    elCmdOuiBtn.setAttribute('aria-pressed', 'false');
    elCmdSelZone.hidden = true;
    commandeIds = [];
    commandeLignes = [];
    if (elCommandesListe) elCommandesListe.innerHTML = '';
  });

  elCmdOuiBtn.addEventListener('click', async () => {
    elCmdOuiBtn.classList.add('ok-sel');
    elCmdNonBtn.classList.remove('ok-sel');
    elCmdOuiBtn.setAttribute('aria-pressed', 'true');
    elCmdNonBtn.setAttribute('aria-pressed', 'false');
    elCmdSelZone.hidden = false;
    await chargerCommandesDisponibles();
    if (elCommandesListe && elCommandesListe.children.length === 0) {
      ajouterLigneCommande();
    }
  });
}

if (elBtnAddCommande) {
  elBtnAddCommande.addEventListener('click', ajouterLigneCommande);
}

async function chargerCommandesDisponibles() {
  if (toutesCommandes.length) return; // déjà chargées
  try {
    const cmds = await apiFetch('/api/achats/commandes?statut=confirmee&limit=50&non_liee=true');
    const brouillons = await apiFetch('/api/achats/commandes?statut=brouillon&limit=50&non_liee=true');
    toutesCommandes = [...cmds, ...brouillons];
  } catch (e) {
    toutesCommandes = [];
  }
}

function ajouterLigneCommande() {
  if (!elCommandesListe) return;
  const rowIdx = elCommandesListe.children.length;
  const row = document.createElement('div');
  row.className = 'rec-commande-row';
  row.dataset.rowIdx = rowIdx;

  const selectEl = document.createElement('select');
  selectEl.className = 'rec-input rec-commande-row-select';
  selectEl.innerHTML = '<option value="">-- Sélectionnez une commande --</option>';
  const dejaChoisis = new Set(commandeIds.filter(Boolean));
  toutesCommandes.forEach(c => {
    if (dejaChoisis.has(c.id)) return;
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = `${c.numero_commande} — ${c.fournisseur_nom} — ${fmtDate(c.date_commande)}`;
    selectEl.appendChild(opt);
  });
  if (!toutesCommandes.length) {
    selectEl.innerHTML = '<option value="">Aucune commande disponible</option>';
  }

  const resumeEl = document.createElement('div');
  resumeEl.className = 'rec-commande-resume';
  resumeEl.hidden = true;

  const removeBtn = document.createElement('button');
  removeBtn.type = 'button';
  removeBtn.className = 'rec-fourn-clear';
  removeBtn.setAttribute('aria-label', 'Supprimer cette commande');
  removeBtn.textContent = '✕';
  removeBtn.style.cssText = 'margin-left:.5rem;flex-shrink:0;';

  const selectWrap = document.createElement('div');
  selectWrap.style.cssText = 'display:flex;align-items:center;gap:.5rem;';
  selectWrap.appendChild(selectEl);
  selectWrap.appendChild(removeBtn);

  row.appendChild(selectWrap);
  row.appendChild(resumeEl);
  elCommandesListe.appendChild(row);

  selectEl.addEventListener('change', async () => {
    const id = parseInt(selectEl.value);
    if (!id) {
      commandeIds[rowIdx] = null;
      commandeLignes = construireLignesCommandes();
      resumeEl.hidden = true;
      resumeEl.innerHTML = '';
      // Vider le fournisseur du bloc BL correspondant
      viderFournisseurBloc(rowIdx);
      return;
    }
    commandeIds[rowIdx] = id;
    await afficherResumeCommande(id, resumeEl, rowIdx);
    commandeLignes = construireLignesCommandes();
  });

  removeBtn.addEventListener('click', () => {
    const idx = parseInt(row.dataset.rowIdx);
    commandeIds.splice(idx, 1);
    row.remove();
    // Renuméroter les rowIdx restants
    Array.from(elCommandesListe.children).forEach((r, i) => {
      r.dataset.rowIdx = i;
    });
    commandeLignes = construireLignesCommandes();
    // Supprimer le bloc BL correspondant (si ce n'est pas le bloc 0)
    if (idx > 0) {
      const bloc = document.getElementById(`rec-fourn-bloc-${idx}`);
      if (bloc) {
        fournisseursListe.splice(idx, 1);
        bloc.remove();
      }
    } else {
      // Pour le bloc 0, juste vider le fournisseur
      viderFournisseurBloc(0);
    }
    syncModeFournisseur();
    majSelectorFournisseur();
  });
}

// Reconstruit commandeLignes depuis toutes les commandes choisies.
// Chaque ligne porte le fournisseur de sa commande (pour rattacher le bon
// fournisseur au produit en mode multi-commandes).
function construireLignesCommandes() {
  const lignes = [];
  commandeIds.forEach(cid => {
    if (!cid) return;
    const cmd = toutesCommandes.find(c => c.id === cid);
    if (cmd && cmd.lignes) {
      cmd.lignes.forEach(l => {
        lignes.push({
          ...l,
          _fournisseur_id:  cmd.fournisseur_id || null,
          _fournisseur_nom: cmd.fournisseur_nom || null,
        });
      });
    }
  });
  return lignes;
}

async function afficherResumeCommande(id, resumeEl, rowIdx) {
  try {
    const cmd = await apiFetch(`/api/achats/commandes/${id}`);
    // Mettre à jour le cache de lignes sur l'objet commande
    const cached = toutesCommandes.find(c => c.id === id);
    if (cached) cached.lignes = cmd.lignes || [];
    commandeLignes = construireLignesCommandes();

    resumeEl.hidden = false;
    resumeEl.innerHTML = `
      <div class="rec-commande-resume-titre">
        📝 ${escHtml(cmd.numero_commande)} — ${escHtml(cmd.fournisseur_nom)}
        <span class="rec-commande-prefill-badge">Auto-remplissage activé</span>
      </div>
      ${(cmd.lignes || []).map(l => `
        <div class="rec-commande-resume-ligne">
          <span><strong>${escHtml(l.code_article)}</strong> — ${escHtml(l.designation)}</span>
          <span>${l.quantite_commandee} ${l.unite}</span>
        </div>
      `).join('')}
    `;

    // Créer le bloc BL si nécessaire (rowIdx > 0 = nouveau bloc à injecter)
    if (rowIdx > 0 && !document.getElementById(`rec-fourn-bloc-${rowIdx}`)) {
      // S'assurer que fournisseursListe a l'entrée pour cet index
      while (fournisseursListe.length <= rowIdx) {
        fournisseursListe.push({ id: null, nom: '', photos: [] });
      }
      creerBlocFourn(rowIdx, false); // pas de bouton ✕ (géré par la liste commandes)
    }

    // Activer le mode multi-fournisseurs si plusieurs commandes
    syncModeFournisseur();

    // Auto-remplir le fournisseur du bloc BL correspondant
    if (cmd.fournisseur_id) {
      preRemplirFournisseurBloc(rowIdx, { id: cmd.fournisseur_id, nom: cmd.fournisseur_nom });
    }
  } catch(e) {
    resumeEl.innerHTML = '<div style="color:#991b1b;">Erreur de chargement de la commande</div>';
    resumeEl.hidden = false;
  }
}

// Pré-remplir le bloc fournisseur d'index idx avec les données {id, nom}
function preRemplirFournisseurBloc(idx, fourn) {
  fournisseursListe[idx] = fournisseursListe[idx] || { id: null, nom: '', photos: [] };
  fournisseursListe[idx].id  = fourn.id;
  fournisseursListe[idx].nom = fourn.nom;
  if (idx === 0) { fournisseurId = fourn.id; if (fourn.id) chargerCatalogueBl(fourn.id); }

  const selWrap    = document.getElementById(`rec-fourn-sel-wrap-${idx}`);
  const selNom     = document.getElementById(`rec-fourn-sel-nom-${idx}`);
  const searchWrap = document.getElementById(`rec-fourn-search-wrap-${idx}`);
  if (selWrap && selNom && searchWrap) {
    selNom.textContent = fourn.nom;
    selWrap.hidden     = false;
    searchWrap.hidden  = true;
  }
  majSelectorFournisseur();
}

// Vider le fournisseur d'un bloc BL
function viderFournisseurBloc(idx) {
  if (!fournisseursListe[idx]) return;
  fournisseursListe[idx].id  = null;
  fournisseursListe[idx].nom = '';
  if (idx === 0) fournisseurId = null;

  const selWrap    = document.getElementById(`rec-fourn-sel-wrap-${idx}`);
  const searchWrap = document.getElementById(`rec-fourn-search-wrap-${idx}`);
  const searchInp  = document.getElementById(`rec-fourn-search-${idx}`);
  if (selWrap) selWrap.hidden = true;
  if (searchWrap) searchWrap.hidden = false;
  if (searchInp) searchInp.value = '';
  majSelectorFournisseur();
}

// Synchronise le mode multi-fournisseurs selon le nombre de commandes liées
function syncModeFournisseur() {
  const nbCommandes = commandeIds.filter(Boolean).length;
  if (nbCommandes > 1 && !modeMultiFourn) {
    // Basculer en mode multi silencieusement
    modeMultiFourn = true;
    elFournMultiBtn.classList.add('ok-sel');
    elFournUnBtn.classList.remove('ok-sel');
    elFournMultiBtn.setAttribute('aria-pressed', 'true');
    elFournUnBtn.setAttribute('aria-pressed', 'false');
    elBtnAddFourn.hidden = false;
    const titre0 = document.getElementById('rec-fourn-bloc-titre-0');
    if (titre0) titre0.hidden = false;
    majSelectorFournisseur();
  } else if (nbCommandes <= 1 && modeMultiFourn) {
    // Repasser en mode simple si on revient à 1 commande
    modeMultiFourn = false;
    elFournUnBtn.classList.add('ok-sel');
    elFournMultiBtn.classList.remove('ok-sel');
    elFournUnBtn.setAttribute('aria-pressed', 'true');
    elFournMultiBtn.setAttribute('aria-pressed', 'false');
    elBtnAddFourn.hidden = true;
    const titre0 = document.getElementById('rec-fourn-bloc-titre-0');
    if (titre0) titre0.hidden = true;
    majSelectorFournisseur();
  }
}

function fmtDate(d) {
  if (!d) return '';
  return d.split('-').reverse().join('/');
}

function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Horloge ────────────────────────────────────────────────
function majHorloge() {
  if (!elHorloge) return;
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();


// ── Inactivité ─────────────────────────────────────────────
const DELAI_INACTIVITE = 5 * 60 * 1000;

function resetInactivite() {
  if (elDialogInactivite && !elDialogInactivite.hidden) return;
  clearTimeout(timerInactivite);
  timerInactivite = setTimeout(() => {
    if (lignesAjoutees.length > 0 && etape < 5) {
      elDialogInactivite.hidden = false;
    }
  }, DELAI_INACTIVITE);
}

document.addEventListener('click',      resetInactivite, true);
document.addEventListener('touchstart', resetInactivite, { passive: true, capture: true });
document.addEventListener('input',      resetInactivite, true);
resetInactivite();

// ── Compression photo navigateur ───────────────────────────
// Redimensionne à PHOTO_MAX_SIDE et ré-encode en JPEG avant l'upload.
// On envoie ~150-300 Ko au lieu de 3 Mo → upload quasi instantané sur la
// connexion distante (BL de réception : 1 à plusieurs photos par livraison).
const PHOTO_MAX_SIDE = 1280;
const PHOTO_QUALITE  = 0.8;

function compresserImage(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      let { width: w, height: h } = img;
      if (Math.max(w, h) > PHOTO_MAX_SIDE) {
        if (w >= h) { h = Math.round(h * PHOTO_MAX_SIDE / w); w = PHOTO_MAX_SIDE; }
        else        { w = Math.round(w * PHOTO_MAX_SIDE / h); h = PHOTO_MAX_SIDE; }
      }
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      canvas.getContext('2d').drawImage(img, 0, 0, w, h);
      canvas.toBlob(
        (blob) => resolve(blob
          ? new File([blob], (file.name || 'photo').replace(/\.[^.]+$/, '') + '.jpg',
                     { type: 'image/jpeg' })
          : file),               // fallback : si toBlob échoue, on garde l'original
        'image/jpeg',
        PHOTO_QUALITE,
      );
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
    img.src = url;
  });
}

elDialogContinuer.addEventListener('click', () => {
  elDialogInactivite.hidden = true;
  resetInactivite();
});
elDialogQuitter.addEventListener('click', () => {
  window.location.href = '/hub.html';
});

// Dialog "Même fournisseur ?"
elDialogFournOui.addEventListener('click', () => {
  elDialogFourn.hidden = true;
  if (dernierFournisseurProduit) {
    fournisseurProduitSelected = { ...dernierFournisseurProduit };
    // Mettre à jour le sélecteur visible (mode multi) : match par id si dispo, sinon par nom
    if (modeMultiFourn && elFournProduitSel) {
      let idx = -1;
      if (dernierFournisseurProduit.id) {
        idx = fournisseursListe.findIndex(f => f.id === dernierFournisseurProduit.id);
      }
      if (idx < 0 && dernierFournisseurProduit.nom) {
        idx = fournisseursListe.findIndex(f => (f.nom || '') === dernierFournisseurProduit.nom);
      }
      if (idx >= 0) elFournProduitSel.value = idx;
    }
  }
});
elDialogFournNon.addEventListener('click', () => {
  elDialogFourn.hidden = true;
  fournisseurProduitSelected = null;
  if (elFournProduitSel) elFournProduitSel.value = '';
});


// ── Fetch helper ───────────────────────────────────────────
async function apiFetch(url, options = {}) {
  const res = await fetch(url, { cache: 'no-store', ...options });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} — ${txt || url}`);
  }
  return res.json();
}


// ── Navigation wizard ──────────────────────────────────────
function allerEtape(cible) {
  etape = cible;

  // STEPS: [step0, step1, step2, step3, step4, confirm] — indices 0..5
  // "confirm" est l'index 5 mais la numérotation logique est aussi 5
  const idx = Math.min(cible, STEPS.length - 1);

  STEPS.forEach((el, i) => {
    el.classList.remove('actif', 'gauche');
    if (i < idx)      el.classList.add('gauche');
    else if (i === idx) el.classList.add('actif');
  });

  // Progress dots : étapes 0-4 (cible 5 = confirm → cacher dots)
  const estConfirm = (cible >= 5);
  elProgress.hidden = estConfirm;
  if (!estConfirm) {
    DOTS.forEach((dot, i) => {
      dot.classList.remove('actif', 'complet');
      if (i < cible)      dot.classList.add('complet');
      else if (i === cible) dot.classList.add('actif');
    });
  }

  // Bandeau personnel
  elBandeau.hidden = (cible === 0 || estConfirm);
  if (cible > 0 && !estConfirm && personnelPrenom) {
    elBandeau.textContent = `👤 ${personnelPrenom}`;
  }

  // Bouton retour
  elBtnRetour.hidden = estConfirm;
}


// ── Retour ─────────────────────────────────────────────────
elBtnRetour.addEventListener('click', () => {
  if (etape === 0) {
    window.location.href = '/hub.html';
  } else if (etape === 3) {
    // Retour depuis produits : pas possible si fiche déjà créée → aller à étape 2
    allerEtape(2);
  } else if (etape <= 4) {
    allerEtape(etape - 1);
  }
});


// ── ÉTAPE 0 : Personnel ────────────────────────────────────
async function chargerPersonnel() {
  try {
    const liste = await apiFetch('/api/admin/personnel');
    elChargementPerso.remove();
    liste.forEach(p => {
      const nomComplet = [p.prenom, p.nom].filter(Boolean).join(' ');
      const btn = document.createElement('button');
      btn.className    = 'rec-btn-prenom';
      btn.textContent  = nomComplet;
      btn.dataset.id   = p.id;
      btn.dataset.prenom = nomComplet;
      btn.addEventListener('click', () => {
        personnelId     = p.id;
        personnelPrenom = nomComplet;
        // Initialiser date à aujourd'hui, heure par défaut 7h30
        const now = new Date();
        if (!elHeure.value) elHeure.value = '07:30';
        if (!elDateReception.value) {
          elDateReception.value = now.toISOString().slice(0, 10);
        }
        allerEtape(1);
      });
      elPersonnelGrille.appendChild(btn);
    });
    if (!liste.length) {
      elPersonnelGrille.innerHTML = '<div class="rec-chargement">Aucun personnel enregistré.</div>';
    }
  } catch {
    elChargementPerso.textContent = 'Impossible de charger le personnel.';
  }
}


// ── Reprise d'une réception non terminée ───────────────────
// Une fiche créée puis quittée sans clôture reste 'en_cours' : elle n'apparaît
// nulle part (ni stock, ni produits en attente) et piège la commande liée.
// Au chargement, on la détecte et on propose de la reprendre ou de l'abandonner.
let receptionEnCours = null;   // {id, nb_lignes, personnel_id, personnel_prenom, ...}

async function detecterReceptionEnCours() {
  try {
    receptionEnCours = await apiFetch('/api/receptions/en-cours');
  } catch {
    receptionEnCours = null;
  }
  if (!receptionEnCours || !receptionEnCours.id || !elRepriseBandeau) return;

  const dateTxt = receptionEnCours.date_reception || '';
  const heureTxt = (receptionEnCours.heure_reception || '').slice(0, 5);
  const qui = receptionEnCours.personnel_prenom ? ` par ${receptionEnCours.personnel_prenom}` : '';
  const nb = receptionEnCours.nb_lignes || 0;

  if (nb === 0) {
    // Fiche créée à l'étape 1 puis quittée sans saisir aucun produit : il n'y a
    // rien à « reprendre ». On ne propose que l'abandon (qui débloque la commande
    // liée), pour éviter de rouvrir un wizard vide qui ressemble à une nouvelle
    // réception.
    elRepriseTxt.textContent =
      `⚠️ Une réception du ${dateTxt}${heureTxt ? ' à ' + heureTxt : ''}${qui} `
      + `a été démarrée mais aucun produit n'y a été saisi, et elle n'a pas été `
      + `clôturée. Tant qu'elle existe, la commande liée reste bloquée. `
      + `Comme elle est vide, abandonnez-la pour débloquer la commande.`;
    if (elRepriseReprendre) elRepriseReprendre.hidden = true;
  } else {
    elRepriseTxt.textContent =
      `⚠️ Une réception du ${dateTxt}${heureTxt ? ' à ' + heureTxt : ''}${qui} `
      + `n'a pas été clôturée (${nb} produit${nb > 1 ? 's' : ''} saisi${nb > 1 ? 's' : ''}). `
      + `Tant qu'elle n'est pas clôturée, ses produits n'apparaissent ni au stock `
      + `ni en attente, et la commande liée reste bloquée.`;
    if (elRepriseReprendre) elRepriseReprendre.hidden = false;
  }
  elRepriseBandeau.hidden = false;
}

async function reprendreReceptionEnCours() {
  if (!receptionEnCours || !receptionEnCours.id) return;
  elRepriseReprendre.disabled = true;
  try {
    const rec = await apiFetch(`/api/receptions/${receptionEnCours.id}`);

    // Restaurer l'état minimal du wizard pour pouvoir compléter + clôturer.
    receptionId     = rec.id;
    // Restaurer le n° BL déjà enregistré (préfixe des lots internes).
    if (rec.numero_bon_livraison && elNumeroBl) {
      elNumeroBl.value = rec.numero_bon_livraison;
      numeroBlValide   = rec.numero_bon_livraison;
      afficherHintBl(`✔ BL enregistré : ${rec.numero_bon_livraison}`, false);
    }
    personnelId     = rec.personnel_id || receptionEnCours.personnel_id;
    personnelPrenom = receptionEnCours.personnel_prenom || null;
    if (rec.temperature_camion !== null && rec.temperature_camion !== undefined) {
      elTempCamion.value = rec.temperature_camion;
      dernierTempCamionEnvoye = rec.temperature_camion;
    }
    propreteCamion = rec.proprete_camion || 'satisfaisant';

    // Restaurer les lignes déjà saisies (telles que majListeLignes les attend).
    lignesAjoutees = (rec.lignes || []).map(l => ({
      id:                    l.id,
      produit_id:            l.produit_id,
      produit_nom:           l.produit_nom,
      conforme:              l.conforme,
      numero_lot:            l.numero_lot,
      origine:               l.origine,
      temperature_reception: l.temperature_reception,
      statut:                l.statut,
      attente_motif:         l.attente_motif,
    }));

    elRepriseBandeau.hidden = true;

    // Vue produits classique (formulaire unitaire) : l'opérateur ajoute les
    // produits restants puis clôture normalement.
    sortirModeBatch();
    reinitFormProduit();
    majListeLignes();
    majSelectorFournisseur();
    majBlocOcr();
    allerEtape(3);
  } catch (e) {
    alert('Impossible de reprendre la réception : ' + e.message);
    elRepriseReprendre.disabled = false;
  }
}

async function abandonnerReceptionEnCours() {
  if (!receptionEnCours || !receptionEnCours.id) return;
  if (!confirm('Abandonner définitivement cette réception non terminée ? '
    + 'Les produits saisis seront supprimés et la commande liée redeviendra '
    + 'sélectionnable.')) return;
  elRepriseAbandonner.disabled = true;
  try {
    await apiFetch(`/api/receptions/${receptionEnCours.id}`, { method: 'DELETE' });
    receptionEnCours = null;
    elRepriseBandeau.hidden = true;
  } catch (e) {
    alert('Abandon impossible : ' + e.message);
    elRepriseAbandonner.disabled = false;
  }
}

if (elRepriseReprendre)  elRepriseReprendre.addEventListener('click', reprendreReceptionEnCours);
if (elRepriseAbandonner) elRepriseAbandonner.addEventListener('click', abandonnerReceptionEnCours);


// ── ÉTAPE 1 : Camion ───────────────────────────────────────
function camionEstChaud(tempMax) {
  // Si tempMax fourni : hors norme si temp camion > temp cible produit
  // Sinon (contexte global) : hors norme si >= 2°C (approximation)
  const t = parseFloat(elTempCamion.value);
  if (isNaN(t)) return false;
  if (tempMax !== undefined) return t > tempMax;
  return t >= 2;
}

function majBadgeCamion() {
  const temp = parseFloat(elTempCamion.value);
  const propreteOk = propreteCamion === 'satisfaisant';

  if (isNaN(temp)) {
    elCamionBadge.className = 'rec-badge neutre';
    elCamionBadge.textContent = '— Non évalué';
  } else if (!propreteOk) {
    elCamionBadge.className = 'rec-badge nc';
    elCamionBadge.textContent = '✗ Propreté non satisfaisante';
  } else {
    // La température camion ne crée PAS de NC à cette étape
    elCamionBadge.className = 'rec-badge conforme';
    elCamionBadge.textContent = '✓ Conforme';
  }
}

elTempCamion.addEventListener('input', majBadgeCamion);

elPropreteOk.addEventListener('click', () => {
  propreteCamion = 'satisfaisant';
  elPropreteOk.classList.add('ok-sel');
  elPropreteNc.classList.remove('nc-sel');
  elPropreteOk.setAttribute('aria-pressed', 'true');
  elPropreteNc.setAttribute('aria-pressed', 'false');
  if (elPropreteNcDetails) elPropreteNcDetails.hidden = true;
  majBadgeCamion();
});

elPropreteNc.addEventListener('click', () => {
  propreteCamion = 'non_satisfaisant';
  elPropreteNc.classList.add('nc-sel');
  elPropreteOk.classList.remove('ok-sel');
  elPropreteNc.setAttribute('aria-pressed', 'true');
  elPropreteOk.setAttribute('aria-pressed', 'false');
  if (elPropreteNcDetails) elPropreteNcDetails.hidden = false;
  majBadgeCamion();
});

elDateReception.addEventListener('input', () => {
  if (elDateReception.value) {
    elDateReception.classList.remove('rec-champ-invalide');
  }
});

elBtnCamionSuivant.addEventListener('click', async () => {
  if (!elDateReception.value) {
    elDateReception.classList.add('rec-champ-invalide');
    elDateReception.focus();
    return;
  }
  if (elTempCamion.value.trim() === '') {
    elTempCamion.focus();
    elTempCamion.reportValidity();
    return;
  }

  // NC propreté → valider le sous-formulaire puis afficher popup livraison
  if (propreteCamion === 'non_satisfaisant') {
    propreteProblemes = [...elPropreteCheckboxes]
      .filter(cb => cb.checked)
      .map(cb => cb.value);

    // Si rien n'est coché, la photo est obligatoire
    if (propreteProblemes.length === 0 && !propretePhotoFile) {
      elPropretePhotoZone.classList.add('photo-requise');
      elPropretePhotoZone.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    elDialogLivraison.hidden = false;
    return;
  }

  // Si la fiche existe déjà et la temp a changé : propager aux lignes (recalcul conformité)
  await propagerTempCamionSiModifiee();

  allerEtape(2);
});

/**
 * Si une fiche est en cours et que la température camion a été modifiée
 * depuis la dernière sauvegarde serveur, propager le changement à toutes
 * les lignes pour recalculer leur conformité.
 */
async function propagerTempCamionSiModifiee() {
  if (!receptionId) return;
  const tempCourante = parseFloat(elTempCamion.value);
  const tempEffective = isNaN(tempCourante) ? null : tempCourante;
  if (tempEffective === dernierTempCamionEnvoye) return;

  try {
    const res = await apiFetch(`/api/receptions/${receptionId}/temperature-camion`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ temperature_camion: tempEffective }),
    });
    dernierTempCamionEnvoye = tempEffective;

    // Rafraîchir lignesAjoutees avec les nouveaux flags de conformité
    // (on patche en place pour préserver fournisseur_nom etc. côté local)
    if (res && Array.isArray(res.lignes)) {
      const parId = new Map(res.lignes.map(l => [l.id, l]));
      lignesAjoutees.forEach(local => {
        const fresh = parId.get(local.id);
        if (!fresh) return;
        local.conforme              = fresh.conforme;
        local.temperature_reception = fresh.temperature_reception;
        const motifs = [];
        if (fresh.temperature_conforme === 0) motifs.push('température');
        if (fresh.couleur_conforme     === 0) motifs.push('couleur');
        if (fresh.consistance_conforme === 0) motifs.push('consistance');
        if (fresh.exsudat_conforme     === 0) motifs.push('exsudat');
        if (fresh.odeur_conforme       === 0) motifs.push('odeur');
        if (fresh.ph_conforme          === 0) motifs.push('pH');
        local.motifs = motifs;
      });
      majListeLignes();
    }
  } catch (err) {
    console.error('[haccp] Propagation temp camion échouée :', err);
  }
}

// ── Checkboxes NC propreté ──────────────────────────────────
elPropreteCheckboxes.forEach(cb => {
  cb.addEventListener('change', () => {
    propreteProblemes = [...elPropreteCheckboxes].filter(c => c.checked).map(c => c.value);
    const photoRequise = propreteProblemes.length === 0;
    if (elPropretePhotoSous) {
      elPropretePhotoSous.textContent = photoRequise
        ? 'Obligatoire si rien n\'est coché'
        : 'Optionnel';
    }
    if (!photoRequise) elPropretePhotoZone.classList.remove('photo-requise');
  });
});

// Photo propreté NC
if (elPropretePhotoZone) {
  elPropretePhotoZone.addEventListener('click', () => ouvrirChoixPhoto(elPropretePhotoInput));
  elPropretePhotoZone.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ouvrirChoixPhoto(elPropretePhotoInput); }
  });
}
if (elPropretePhotoInput) {
  elPropretePhotoInput.addEventListener('change', async () => {
    const file = elPropretePhotoInput.files[0];
    if (!file) return;
    propretePhotoFile = file; // repli avant fin de compression
    const url = URL.createObjectURL(file);
    elPropretePhotoVignette.src = url;
    elPropretePhotoVignette.hidden = false;
    elPropretePhotoIcone.textContent = '✅';
    elPropretePhotoZone.classList.remove('photo-requise');
    propretePhotoFile = await compresserImage(file);
  });
}

// ── Dialog "Accepter la livraison ?" ───────────────────────
elDialogLivraisonOui.addEventListener('click', () => {
  elDialogLivraison.hidden = true;
  allerEtape(2);
});

elDialogLivraisonNon.addEventListener('click', () => {
  elDialogLivraison.hidden = true;
  // Réinitialiser la liste des BL refusés
  refusBlList.forEach(b => { if (b.photoUrl) URL.revokeObjectURL(b.photoUrl); });
  refusBlList = [];
  elRefusBlListe.innerHTML = '';
  ajouterBlocRefusBl();   // toujours au moins 1 bloc
  elDialogRefusValider.disabled = false;   // validation à la soumission
  if (elErreurRefusBl) elErreurRefusBl.hidden = true;
  elDialogRefusBl.hidden = false;
});

// ── Dialog "Refus BL — photo + fournisseur obligatoires" ──
elDialogRefusAnnuler.addEventListener('click', () => {
  elDialogRefusBl.hidden = true;
});

function majBoutonRefusValider() {
  // Bouton toujours actif : la validation se fait au clic, avec retour visuel
  // sur les blocs incomplets.
  elDialogRefusValider.disabled = false;
}

function ajouterBlocRefusBl() {
  const idx = refusBlList.length;
  refusBlList.push({ photoFile: null, photoUrl: null, fournisseurId: null, fournisseurNom: '' });

  const bloc = document.createElement('div');
  bloc.className = 'rec-refus-bl-bloc';
  bloc.dataset.idx = String(idx);
  bloc.innerHTML = `
    <div class="rec-fourn-bloc-titre" id="rec-refus-bl-titre-${idx}">
      Bon de livraison ${idx + 1}
      <button class="rec-fourn-sup-btn" type="button" data-sup="${idx}" aria-label="Supprimer ce BL"
              ${idx === 0 ? 'hidden' : ''}>✕</button>
    </div>
    <div class="rec-photo-zone" id="rec-refus-bl-photo-zone-${idx}" role="button" tabindex="0"
         aria-label="Photo obligatoire du bon de livraison" style="margin:.5rem 0;">
      <span class="rec-photo-icone" id="rec-refus-bl-photo-icone-${idx}">📋</span>
      <div class="rec-photo-texte">
        <div class="rec-photo-texte-titre" id="rec-refus-bl-photo-titre-${idx}">Photo du bon de livraison</div>
        <div class="rec-photo-texte-sous">Obligatoire</div>
      </div>
      <img id="rec-refus-bl-photo-vignette-${idx}" class="rec-photo-vignette" alt="Aperçu BL" hidden>
    </div>
    <input type="file" accept="image/*" capture
           id="rec-refus-bl-photo-input-${idx}" hidden aria-hidden="true">

    <div class="rec-fourn-search-group">
      <div id="rec-refus-bl-fourn-sel-wrap-${idx}" hidden>
        <div class="rec-fourn-sel">
          <span>✓</span>
          <span id="rec-refus-bl-fourn-sel-nom-${idx}"></span>
          <button class="rec-fourn-clear" id="rec-refus-bl-fourn-clear-${idx}" type="button"
                  aria-label="Effacer le fournisseur">✕</button>
        </div>
      </div>
      <div id="rec-refus-bl-fourn-search-wrap-${idx}">
        <input type="search" id="rec-refus-bl-fourn-search-${idx}" class="rec-input"
               placeholder="Nom du fournisseur (obligatoire)…"
               autocomplete="off" aria-label="Fournisseur du BL">
        <div class="rec-fourn-results" id="rec-refus-bl-fourn-results-${idx}" hidden></div>
      </div>
    </div>
  `;
  elRefusBlListe.appendChild(bloc);
  initBlocRefusBl(idx);

  // Bouton suppression
  const supBtn = bloc.querySelector('.rec-fourn-sup-btn');
  if (supBtn) {
    supBtn.addEventListener('click', () => {
      const i = Number(supBtn.dataset.sup);
      const item = refusBlList[i];
      if (item && item.photoUrl) URL.revokeObjectURL(item.photoUrl);
      refusBlList.splice(i, 1);
      // Reconstruire entièrement la liste pour réindexer proprement
      const snapshot = refusBlList.slice();
      refusBlList = [];
      elRefusBlListe.innerHTML = '';
      snapshot.forEach(item => {
        ajouterBlocRefusBl();
        const newIdx = refusBlList.length - 1;
        refusBlList[newIdx] = item;
        // Restaurer la photo
        if (item.photoFile) {
          const z = document.getElementById(`rec-refus-bl-photo-zone-${newIdx}`);
          const v = document.getElementById(`rec-refus-bl-photo-vignette-${newIdx}`);
          const ic = document.getElementById(`rec-refus-bl-photo-icone-${newIdx}`);
          const tt = document.getElementById(`rec-refus-bl-photo-titre-${newIdx}`);
          if (v && item.photoUrl) { v.src = item.photoUrl; v.hidden = false; }
          if (ic) ic.textContent = '✅';
          if (tt) tt.textContent = 'Photo prise';
        }
        // Restaurer le fournisseur
        if (item.fournisseurNom) {
          const selWrap   = document.getElementById(`rec-refus-bl-fourn-sel-wrap-${newIdx}`);
          const selNom    = document.getElementById(`rec-refus-bl-fourn-sel-nom-${newIdx}`);
          const searchWrap = document.getElementById(`rec-refus-bl-fourn-search-wrap-${newIdx}`);
          if (selNom) selNom.textContent = item.fournisseurNom;
          if (selWrap) selWrap.hidden = false;
          if (searchWrap) searchWrap.hidden = true;
        }
      });
      majBoutonRefusValider();
    });
  }

  majBoutonRefusValider();
}

function initBlocRefusBl(idx) {
  const photoZone  = document.getElementById(`rec-refus-bl-photo-zone-${idx}`);
  const photoInput = document.getElementById(`rec-refus-bl-photo-input-${idx}`);
  const photoIcone = document.getElementById(`rec-refus-bl-photo-icone-${idx}`);
  const photoTitre = document.getElementById(`rec-refus-bl-photo-titre-${idx}`);
  const photoVign  = document.getElementById(`rec-refus-bl-photo-vignette-${idx}`);
  const selWrap    = document.getElementById(`rec-refus-bl-fourn-sel-wrap-${idx}`);
  const selNom     = document.getElementById(`rec-refus-bl-fourn-sel-nom-${idx}`);
  const searchWrap = document.getElementById(`rec-refus-bl-fourn-search-wrap-${idx}`);
  const searchInp  = document.getElementById(`rec-refus-bl-fourn-search-${idx}`);
  const results    = document.getElementById(`rec-refus-bl-fourn-results-${idx}`);
  const clearBtn   = document.getElementById(`rec-refus-bl-fourn-clear-${idx}`);

  // Photo
  photoZone.addEventListener('click', () => ouvrirChoixPhoto(photoInput));
  photoZone.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ouvrirChoixPhoto(photoInput); }
  });
  photoInput.addEventListener('change', async () => {
    const file = photoInput.files[0];
    if (!file) return;
    if (refusBlList[idx].photoUrl) URL.revokeObjectURL(refusBlList[idx].photoUrl);
    refusBlList[idx].photoFile = file; // repli avant fin de compression
    refusBlList[idx].photoUrl  = URL.createObjectURL(file);
    photoVign.src = refusBlList[idx].photoUrl;
    photoVign.hidden = false;
    photoIcone.textContent = '✅';
    photoTitre.textContent = 'Photo prise';
    photoZone.classList.remove('photo-requise');
    if (elErreurRefusBl) elErreurRefusBl.hidden = true;
    refusBlList[idx].photoFile = await compresserImage(file);
    majBoutonRefusValider();
  });

  // Fournisseur — recherche
  function afficherResultats(liste) {
    results.innerHTML = '';
    if (!liste.length) { results.hidden = true; return; }
    liste.slice(0, 10).forEach(f => {
      const div = document.createElement('div');
      div.className = 'rec-fourn-item';
      div.textContent = f.nom;
      div.addEventListener('click', () => {
        refusBlList[idx].fournisseurId  = f.id;
        refusBlList[idx].fournisseurNom = f.nom;
        selNom.textContent = f.nom;
        selWrap.hidden     = false;
        searchWrap.hidden  = true;
        results.hidden     = true;
        majBoutonRefusValider();
      });
      results.appendChild(div);
    });
    results.hidden = false;
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      refusBlList[idx].fournisseurId  = null;
      refusBlList[idx].fournisseurNom = '';
      selWrap.hidden     = true;
      searchWrap.hidden  = false;
      searchInp.value    = '';
      results.hidden     = true;
      majBoutonRefusValider();
    });
  }

  searchInp.addEventListener('input', () => {
    const q = searchInp.value.trim().toLowerCase();
    refusBlList[idx].fournisseurNom = searchInp.value.trim();
    refusBlList[idx].fournisseurId  = null; // saisie libre, plus d'ID tant que pas re-sélectionné
    if (q) searchInp.classList.remove('rec-champ-invalide');
    if (elErreurRefusBl) elErreurRefusBl.hidden = true;
    if (!q) { results.hidden = true; majBoutonRefusValider(); return; }
    afficherResultats((tousFournisseurs || []).filter(f => f.nom.toLowerCase().includes(q)));
    majBoutonRefusValider();
  });

  document.addEventListener('click', e => {
    if (!results.contains(e.target) && e.target !== searchInp) results.hidden = true;
  }, true);
}

if (elRefusBlAdd) elRefusBlAdd.addEventListener('click', () => ajouterBlocRefusBl());

elDialogRefusValider.addEventListener('click', allerVersPcr01Camion);

async function allerVersPcr01Camion() {
  // Validation finale avec retour visuel : highlight bloc(s) incomplet(s)
  if (!refusBlList.length) return;

  // Reset des marqueurs avant validation
  refusBlList.forEach((_, idx) => {
    document.getElementById(`rec-refus-bl-photo-zone-${idx}`)?.classList.remove('photo-requise');
    document.getElementById(`rec-refus-bl-fourn-search-${idx}`)?.classList.remove('rec-champ-invalide');
  });

  let firstError = null;
  let manquePhoto = false, manqueFourn = false;
  refusBlList.forEach((b, idx) => {
    if (!b.photoFile && !(b.photos && b.photos.length)) {
      manquePhoto = true;
      const z = document.getElementById(`rec-refus-bl-photo-zone-${idx}`);
      if (z) {
        z.classList.add('photo-requise');
        if (!firstError) firstError = z;
      }
    }
    if (!b.fournisseurId && !(b.fournisseurNom && b.fournisseurNom.trim())) {
      manqueFourn = true;
      const s = document.getElementById(`rec-refus-bl-fourn-search-${idx}`);
      if (s) {
        s.classList.add('rec-champ-invalide');
        if (!firstError) firstError = s;
      }
    }
  });

  if (firstError) {
    if (elErreurRefusBl) {
      const parts = [];
      if (manquePhoto) parts.push('photo du bon de livraison');
      if (manqueFourn) parts.push('nom du fournisseur');
      elErreurRefusBl.textContent =
        `⚠️ Manquant : ${parts.join(' et ')}. Chaque BL doit avoir une photo ET un fournisseur.`;
      elErreurRefusBl.hidden = false;
    }
    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }

  elDialogRefusValider.disabled = true;
  elDialogRefusValider.textContent = 'Création…';
  if (elErreurRefusBl) elErreurRefusBl.hidden = true;

  try {
    // Créer une réception minimale (sans produits — livraison refusée)
    // Le 1er BL renseigne fournisseur principal + photo BL principale.
    const premier = refusBlList[0];

    const fd = new FormData();
    fd.append('personnel_id',    personnelId);
    fd.append('heure_reception', elHeure.value || new Date().toTimeString().slice(0, 5));
    if (elDateReception.value) fd.append('date_reception', elDateReception.value);
    if (elTempCamion.value !== '') fd.append('temperature_camion', elTempCamion.value);
    fd.append('proprete_camion', 'non_satisfaisant');
    if (propretePhotoFile) {
      fd.append('photo_proprete', propretePhotoFile, propretePhotoFile.name);
    }
    if (premier.fournisseurId)  fd.append('fournisseur_principal_id', premier.fournisseurId);
    else if (premier.fournisseurNom) fd.append('fournisseur_nom', premier.fournisseurNom);
    fd.append('photo_bl', premier.photoFile, premier.photoFile.name);

    const rec = await apiFetch('/api/receptions', { method: 'POST', body: fd });
    receptionId = rec.id;
    const tempEnvoyeeRefus = parseFloat(elTempCamion.value);
    dernierTempCamionEnvoye = isNaN(tempEnvoyeeRefus) ? null : tempEnvoyeeRefus;

    // BLs supplémentaires (idx >= 1)
    for (let i = 1; i < refusBlList.length; i++) {
      const b = refusBlList[i];
      const fd2 = new FormData();
      if (b.fournisseurId)  fd2.append('fournisseur_id',  b.fournisseurId);
      if (b.fournisseurNom) fd2.append('fournisseur_nom', b.fournisseurNom);
      fd2.append('photo', b.photoFile, b.photoFile.name);
      try {
        await apiFetch(`/api/receptions/${rec.id}/bls-supplementaires`, { method: 'POST', body: fd2 });
      } catch (e) {
        console.warn('BL supplémentaire échoué :', e);
      }
    }

    // Données PCR01 : 1 fiche par fournisseur concerné
    const fournisseursRefus = refusBlList.map(b => ({
      fournisseurId:  b.fournisseurId  || null,
      fournisseurNom: b.fournisseurNom || null,
    }));

    const pcrData = {
      modeCamion:            true,
      receptionId:           rec.id,
      personnelPrenom,
      livreurPresent:        null,
      problemesPropreteList: propreteProblemes,
      photoBlPrise:          true,
      tempCamion:            parseFloat(elTempCamion.value) || null,
      heureReception:        elHeure.value,
      fournisseursRefus,
      ncFicheIndex:          0,
    };
    sessionStorage.setItem('haccp_pcr01_data', JSON.stringify(pcrData));
    sessionStorage.removeItem('haccp_pcr01_signature');

    window.location.href = '/pcr01.html';
  } catch (err) {
    if (elErreurRefusBl) {
      elErreurRefusBl.textContent = `Erreur : ${err.message}`;
      elErreurRefusBl.hidden = false;
    }
    elDialogRefusValider.disabled = false;
    elDialogRefusValider.textContent = 'Aller à PCR01 →';
  }
}


// ── ÉTAPE 2 : Photo BL + Fournisseur(s) ───────────────────
// État fournisseurs multiples : [{id, nom, photos: [{file, url}]}]
let fournisseursListe = [{ id: null, nom: '', photos: [] }];
let modeMultiFourn    = false;

async function chargerFournisseurs() {
  try {
    tousFournisseurs = await apiFetch('/api/fournisseurs');
  } catch {
    tousFournisseurs = [];
  }
}

function majVignettesBloc(idx) {
  const fourn = fournisseursListe[idx];
  const photoZone  = document.getElementById(`rec-photo-zone-${idx}`);
  const photoIcone = document.getElementById(`rec-photo-icone-${idx}`);
  const photoTitre = document.getElementById(`rec-photo-titre-${idx}`);
  const vignRow    = document.getElementById(`rec-photo-vign-row-${idx}`);
  const btnPage    = document.getElementById(`rec-photo-add-page-${idx}`);

  if (!fourn.photos.length) {
    photoIcone.textContent = '📋';
    photoTitre.textContent = 'Photo du bon de livraison';
    photoZone.classList.remove('photo-ok');
    if (btnPage) btnPage.hidden = true;
  } else {
    photoIcone.textContent = '✅';
    photoTitre.textContent = fourn.photos.length === 1 ? '1 page' : `${fourn.photos.length} pages`;
    photoZone.classList.remove('photo-requise');
    photoZone.classList.add('photo-ok');
    if (btnPage) btnPage.hidden = false;
  }

  if (vignRow) {
    vignRow.innerHTML = '';
    fourn.photos.forEach((p, pi) => {
      const wrap = document.createElement('div');
      wrap.className = 'rec-bl-vign-wrap';
      const img = document.createElement('img');
      img.src = p.url;
      img.className = 'rec-photo-vignette rec-bl-vign';
      img.alt = `Page ${pi + 1}`;
      img.addEventListener('click', e => { e.stopPropagation(); ouvrirApercuPhoto(p.url); });
      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'rec-bl-vign-del';
      del.title = 'Supprimer cette page';
      del.textContent = '✕';
      del.addEventListener('click', e => {
        e.stopPropagation();
        URL.revokeObjectURL(fourn.photos[pi].url);
        fourn.photos.splice(pi, 1);
        majVignettesBloc(idx);
      });
      wrap.appendChild(img);
      wrap.appendChild(del);
      vignRow.appendChild(wrap);
    });
  }
}

function initBlocFourn(idx) {
  const photoZone  = document.getElementById(`rec-photo-zone-${idx}`);
  const inputPhoto = document.getElementById(`rec-input-photo-${idx}`);
  const btnPage    = document.getElementById(`rec-photo-add-page-${idx}`);
  const selWrap    = document.getElementById(`rec-fourn-sel-wrap-${idx}`);
  const selNom     = document.getElementById(`rec-fourn-sel-nom-${idx}`);
  const searchWrap = document.getElementById(`rec-fourn-search-wrap-${idx}`);
  const searchInp  = document.getElementById(`rec-fourn-search-${idx}`);
  const results    = document.getElementById(`rec-fourn-results-${idx}`);
  const clearBtn   = document.getElementById(`rec-fourn-clear-${idx}`);

  photoZone.addEventListener('click', () => ouvrirChoixPhoto(inputPhoto));
  photoZone.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ouvrirChoixPhoto(inputPhoto); }
  });

  if (btnPage) {
    btnPage.addEventListener('click', e => { e.stopPropagation(); ouvrirChoixPhoto(inputPhoto); });
  }

  inputPhoto.addEventListener('change', async () => {
    const file = inputPhoto.files[0];
    if (!file) return;
    inputPhoto.value = '';
    const url = URL.createObjectURL(file);
    fournisseursListe[idx].photos.push({ file, url });
    majVignettesBloc(idx);
    const compressed = await compresserImage(file);
    const last = fournisseursListe[idx].photos.length - 1;
    if (fournisseursListe[idx].photos[last]?.file === file) {
      fournisseursListe[idx].photos[last].file = compressed;
    }
  });

  function afficherResultats(liste) {
    results.innerHTML = '';
    if (!liste.length) { results.hidden = true; return; }
    liste.slice(0, 10).forEach(f => {
      const div = document.createElement('div');
      div.className = 'rec-fourn-item';
      div.textContent = f.nom;
      div.addEventListener('click', () => {
        fournisseursListe[idx].id  = f.id;
        fournisseursListe[idx].nom = f.nom;
        selNom.textContent = f.nom;
        selWrap.hidden     = false;
        searchWrap.hidden  = true;
        results.hidden     = true;
        searchInp.classList.remove('rec-champ-invalide');
        searchInp.title = '';
        if (idx === 0) { fournisseurId = f.id; chargerCatalogueBl(f.id); }
        if (elErreur2 && !elErreur2.hidden && fournisseursListe[0].id) elErreur2.hidden = true;
        majSelectorFournisseur();
      });
      results.appendChild(div);
    });
    results.hidden = false;
  }

  clearBtn.addEventListener('click', () => {
    fournisseursListe[idx].id  = null;
    fournisseursListe[idx].nom = '';
    selWrap.hidden     = true;
    searchWrap.hidden  = false;
    searchInp.value    = '';
    results.hidden     = true;
    if (idx === 0) { fournisseurId = null; catalogueBl = []; catalogueBlFournId = null; }
    majSelectorFournisseur();
  });

  searchInp.addEventListener('input', () => {
    const q = searchInp.value.trim().toLowerCase();
    if (!q) { results.hidden = true; return; }
    afficherResultats(tousFournisseurs.filter(f => f.nom.toLowerCase().includes(q)));
  });

  document.addEventListener('click', e => {
    if (!results.contains(e.target) && e.target !== searchInp) results.hidden = true;
  }, true);
}

// Initialiser le premier bloc
initBlocFourn(0);

// ── Sélecteur fournisseur pour produits (écran 4) ────────────
function majSelectorFournisseur() {
  if (!elFournProduitSel) return;
  const visible = modeMultiFourn && fournisseursListe.length > 1;
  elFournProduitGroupe.hidden = !visible;

  if (visible) {
    elFournProduitSel.innerHTML = '<option value="">-- Sélectionnez --</option>';
    fournisseursListe.forEach((f, idx) => {
      const opt = document.createElement('option');
      opt.value = idx;
      opt.textContent = f.nom || `Fournisseur ${idx + 1}`;
      elFournProduitSel.appendChild(opt);
    });
  }
}

// Quand on sélectionne un fournisseur pour un produit
if (elFournProduitSel) {
  elFournProduitSel.addEventListener('change', () => {
    const idx = parseInt(elFournProduitSel.value, 10);
    if (!isNaN(idx) && fournisseursListe[idx]) {
      const f = fournisseursListe[idx];
      fournisseurProduitSelected = { id: f.id || null, nom: (f.nom || '').trim() || null };
    } else {
      fournisseurProduitSelected = null;
    }
  });
}

// Toggle un/plusieurs fournisseurs
elFournUnBtn.addEventListener('click', () => {
  modeMultiFourn = false;
  elFournUnBtn.classList.add('ok-sel');
  elFournMultiBtn.classList.remove('ok-sel');
  elFournUnBtn.setAttribute('aria-pressed', 'true');
  elFournMultiBtn.setAttribute('aria-pressed', 'false');
  elBtnAddFourn.hidden = true;
  // Supprimer les blocs supplémentaires
  while (fournisseursListe.length > 1) {
    fournisseursListe.pop();
    const bloc = elFournListe.querySelector(`[id^="rec-fourn-bloc-"]:last-child`);
    if (bloc && bloc.id !== 'rec-fourn-bloc-0') bloc.remove();
  }
  document.getElementById('rec-fourn-bloc-titre-0').hidden = true;
});

elFournMultiBtn.addEventListener('click', () => {
  modeMultiFourn = true;
  elFournMultiBtn.classList.add('ok-sel');
  elFournUnBtn.classList.remove('ok-sel');
  elFournMultiBtn.setAttribute('aria-pressed', 'true');
  elFournUnBtn.setAttribute('aria-pressed', 'false');
  elBtnAddFourn.hidden = false;
  document.getElementById('rec-fourn-bloc-titre-0').hidden = false;
  // Afficher le sélecteur fournisseur pour écran 4
  majSelectorFournisseur();
});

// Crée le HTML + init d'un bloc BL/fournisseur à l'index idx
// suppressible : affiche le bouton ✕ (mode manuel multi-fourn)
function creerBlocFourn(idx, suppressible = true) {
  if (!fournisseursListe[idx]) {
    fournisseursListe[idx] = { id: null, nom: '', photos: [] };
  }

  const bloc = document.createElement('div');
  bloc.className = 'rec-fourn-bloc';
  bloc.id = `rec-fourn-bloc-${idx}`;
  const supBtnHtml = suppressible
    ? `<button class="rec-fourn-sup-btn" data-idx="${idx}" type="button" aria-label="Supprimer">✕</button>`
    : '';
  bloc.innerHTML = `
    <div class="rec-fourn-bloc-titre">Fournisseur ${idx + 1}
      ${supBtnHtml}
    </div>
    <div class="rec-photo-zone" id="rec-photo-zone-${idx}" role="button" tabindex="0"
         aria-label="Photo BL obligatoire">
      <span class="rec-photo-icone" id="rec-photo-icone-${idx}">📋</span>
      <div class="rec-photo-texte">
        <div class="rec-photo-texte-titre" id="rec-photo-titre-${idx}">Photo du bon de livraison</div>
        <div class="rec-photo-texte-sous">Obligatoire</div>
      </div>
    </div>
    <div class="rec-bl-vign-row" id="rec-photo-vign-row-${idx}"></div>
    <button class="rec-photo-add-page-btn" id="rec-photo-add-page-${idx}" type="button" hidden>
      + Page
    </button>
    <input type="file" accept="image/*" capture
           id="rec-input-photo-${idx}" hidden aria-hidden="true">
    <div class="rec-fourn-search-group">
      <div id="rec-fourn-sel-wrap-${idx}" hidden>
        <div class="rec-fourn-sel">
          <span>✓</span>
          <span id="rec-fourn-sel-nom-${idx}"></span>
          <button class="rec-fourn-clear" id="rec-fourn-clear-${idx}" type="button">✕</button>
        </div>
      </div>
      <div id="rec-fourn-search-wrap-${idx}">
        <input type="search" id="rec-fourn-search-${idx}" class="rec-input"
               placeholder="Nom du fournisseur…" autocomplete="off">
        <div class="rec-fourn-results" id="rec-fourn-results-${idx}" hidden></div>
      </div>
    </div>`;
  elFournListe.appendChild(bloc);
  initBlocFourn(idx);
  majSelectorFournisseur();

  if (suppressible) {
    const supBtn = bloc.querySelector('.rec-fourn-sup-btn');
    if (supBtn) {
      supBtn.addEventListener('click', () => {
        fournisseursListe.splice(idx, 1);
        bloc.remove();
        majSelectorFournisseur();
        // Renuméroter les titres
        elFournListe.querySelectorAll('.rec-fourn-bloc-titre').forEach((el, i) => {
          if (el.id !== 'rec-fourn-bloc-titre-0') {
            const btnSup = el.querySelector('.rec-fourn-sup-btn');
            el.firstChild.textContent = `Fournisseur ${i + 1} `;
            if (btnSup) el.appendChild(btnSup);
          }
        });
      });
    }
  }

  return bloc;
}

elBtnAddFourn.addEventListener('click', () => {
  const idx = fournisseursListe.length;
  fournisseursListe.push({ id: null, nom: '', photos: [] });
  creerBlocFourn(idx, true);
});

// Créer la fiche
elBtnCreerFiche.addEventListener('click', creerFiche);

async function creerFiche() {
  elErreur2.hidden = true;

  // Fiche déjà créée (retour arrière puis avant) : ne pas re-POSTer.
  // On se contente de propager une éventuelle modif de temp camion puis
  // de revenir à l'écran produits.
  if (receptionId) {
    await propagerTempCamionSiModifiee();
    majBlocOcr();
    allerEtape(3);
    return;
  }

  // Valider : au moins le nom du fournisseur principal
  const fourn0 = fournisseursListe[0];
  const searchInp = document.getElementById('rec-fourn-search-0');
  const nomSaisi = searchInp ? searchInp.value.trim() : '';

  if (!fourn0.id && !nomSaisi) {
    if (searchInp) {
      searchInp.classList.add('rec-champ-invalide');
      searchInp.focus();
      searchInp.title = 'Saisissez le nom d\'un fournisseur';
    }
    elErreur2.textContent = 'Le nom du fournisseur est obligatoire.';
    elErreur2.hidden = false;
    return;
  }

  // Si nom saisi mais pas d'ID (pas sélectionné dans la liste), utiliser le nom
  if (nomSaisi && !fourn0.id) {
    fourn0.nom = nomSaisi;
  }

  // Valider photo du bon de livraison principal
  if (!fourn0.photos.length) {
    const photoZone0 = document.getElementById('rec-photo-zone-0');
    if (photoZone0) {
      photoZone0.classList.add('photo-requise');
      photoZone0.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    elErreur2.textContent = 'La photo du bon de livraison est obligatoire.';
    elErreur2.hidden = false;
    return;
  }

  // Valider et sauvegarder les noms des fournisseurs supplémentaires
  for (let i = 1; i < fournisseursListe.length; i++) {
    const fournI = fournisseursListe[i];
    const searchInpI = document.getElementById(`rec-fourn-search-${i}`);
    const nomSaisiI = searchInpI ? searchInpI.value.trim() : '';

    if (!fournI.id && !nomSaisiI) {
      if (searchInpI) {
        searchInpI.classList.add('rec-champ-invalide');
        searchInpI.focus();
        searchInpI.title = 'Saisissez le nom du fournisseur';
      }
      elErreur2.textContent = `Le nom du fournisseur ${i + 1} est obligatoire.`;
      elErreur2.hidden = false;
      return;
    }

    if (nomSaisiI && !fournI.id) {
      fournI.nom = nomSaisiI;
    }

    // Valider photo du BL supplémentaire
    if (!fournI.photos.length) {
      const photoZoneI = document.getElementById(`rec-photo-zone-${i}`);
      if (photoZoneI) {
        photoZoneI.classList.add('photo-requise');
        photoZoneI.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      elErreur2.textContent = `La photo du bon de livraison ${i + 1} est obligatoire.`;
      elErreur2.hidden = false;
      return;
    }
  }

  elBtnCreerFiche.disabled = true;
  elBtnCreerFiche.textContent = 'Création…';

  try {
    const fd = new FormData();
    fd.append('personnel_id',    personnelId);
    fd.append('heure_reception', elHeure.value || new Date().toTimeString().slice(0, 5));
    if (elDateReception.value) fd.append('date_reception', elDateReception.value);
    if (elTempCamion.value !== '') {
      fd.append('temperature_camion', elTempCamion.value);
    }
    fd.append('proprete_camion', propreteCamion);
    if (propreteCamion === 'non_satisfaisant' && propretePhotoFile) {
      fd.append('photo_proprete', propretePhotoFile, propretePhotoFile.name);
    }
    const fourn0 = fournisseursListe[0];
    if (fourn0.id) fd.append('fournisseur_principal_id', fourn0.id);
    else if (fourn0.nom) fd.append('fournisseur_nom', fourn0.nom);
    fourn0.photos.forEach(p => fd.append('photo_bl', p.file, p.file.name));
    // N° BL saisi à l'étape précédente (avant que la réception n'existe) : on le
    // rattache directement à la création.
    const blSaisi = (elNumeroBl && elNumeroBl.value || '').trim();
    if (blSaisi) fd.append('numero_bon_livraison', blSaisi);

    const rec = await apiFetch('/api/receptions', {
      method: 'POST',
      body: fd,
    });
    receptionId = rec.id;
    if (blSaisi) numeroBlValide = blSaisi;
    const tempEnvoyee = parseFloat(elTempCamion.value);
    dernierTempCamionEnvoye = isNaN(tempEnvoyee) ? null : tempEnvoyee;

    // BLs supplémentaires (idx >= 1) : 1 requête par fournisseur additionnel
    for (let i = 1; i < fournisseursListe.length; i++) {
      const fi = fournisseursListe[i];
      const fd2 = new FormData();
      if (fi.id)  fd2.append('fournisseur_id',  fi.id);
      if (fi.nom) fd2.append('fournisseur_nom', fi.nom);
      fi.photos.forEach(p => fd2.append('photo', p.file, p.file.name));
      try {
        await apiFetch(`/api/receptions/${rec.id}/bls-supplementaires`, { method: 'POST', body: fd2 });
      } catch (e) {
        console.warn('BL supplémentaire échoué :', e);
      }
    }

    // Enregistrer le LIEN commande ↔ réception (le passage en « livrée » se fait
    // seulement à la clôture de la réception, pas ici — cf. cloturer_reception).
    for (const cid of commandeIds.filter(Boolean)) {
      try {
        await apiFetch('/api/achats/commande_receptions_mapping', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ commande_id: cid, reception_id: rec.id }),
        });
      } catch(e) {
        console.warn('[haccp] Mapping commande échoué :', e);
      }
    }

    // Réinitialiser le formulaire produit et passer à l'étape 3
    reinitFormProduit();
    majListeLignes();
    majSelectorFournisseur(); // Mettre à jour le sélecteur si mode multi

    // Rattacher par défaut le fournisseur principal (= celui de la commande si liée,
    // car le bloc 0 a été auto-rempli avec) à chaque produit ajouté.
    if (fourn0 && (fourn0.id || (fourn0.nom && fourn0.nom.trim()))) {
      fournisseurProduitSelected = {
        id: fourn0.id || null,
        nom: (fourn0.nom || '').trim() || null,
      };
      if (modeMultiFourn && elFournProduitSel && fournisseursListe.length > 0) {
        elFournProduitSel.value = '0';
      }
    }

    // Commande liée → vue LISTE (toutes les lignes d'un coup).
    // Sinon → formulaire unitaire classique.
    commandeLigneIdx = 0;
    if (commandeIds.some(Boolean) && commandeLignes.length > 0) {
      entrerModeBatch();
    } else {
      sortirModeBatch();
    }

    majBlocOcr();

    allerEtape(3);

  } catch (err) {
    elErreur2.textContent = `Erreur : ${err.message}`;
    elErreur2.hidden = false;
  } finally {
    elBtnCreerFiche.disabled = false;
    elBtnCreerFiche.textContent = 'Créer la fiche →';
  }
}


// ── ÉTAPE 3 : Produits ─────────────────────────────────────
async function chargerProduits() {
  try {
    tousProduits = await apiFetch('/api/produits?type=brut');
  } catch {
    tousProduits = [];
  }
}

async function chargerCatalogueBl(fournId) {
  if (!fournId || fournId === catalogueBlFournId) return;
  try {
    const articles = await apiFetch(`/api/achats/catalogue?fournisseur_id=${fournId}`);
    catalogueBl = articles;
    catalogueBlFournId = fournId;
  } catch {
    catalogueBl = [];
    catalogueBlFournId = fournId;
  }
}

// Retourne vrai si on est en mode "sans commande avec fournisseur catalogue disponible"
function useCatalogueBl() {
  return !commandeIds.some(Boolean) && catalogueBl.length > 0;
}

function filtrerCatalogueBl(q) {
  if (!q) return catalogueBl.slice(0, 50);
  const mots = q.toLowerCase().split(/[\s\-\/,;]+/).filter(m => m.length > 0 && !STOP_WORDS.has(m));
  if (!mots.length) return catalogueBl.slice(0, 50);
  return catalogueBl.filter(a => {
    const hay = ((a.designation || '') + ' ' + (a.code_article || '')).toLowerCase();
    return mots.every(m => hay.includes(m));
  }).slice(0, 50);
}

// Pré-remplir le formulaire produit depuis la ligne de commande courante
function preRemplirDepuisCommande() {
  if (!commandeLignes.length || commandeLigneIdx >= commandeLignes.length) return;

  const ligne = commandeLignes[commandeLigneIdx];

  // Mémoriser la référence catalogue pour la propager vers la ligne de réception
  // (permet de compter le stock par référence catalogue dans le module commandes).
  catalogueIdPrefill = ligne.catalogue_fournisseur_id || null;
  // Type de DLC du catalogue (dlc / date_abattage / no_dlc) : détermine l'exigence
  // de traçabilité (DLC vs date d'abattage) pour le statut « en attente ».
  dlcTypePrefill = ligne.dlc_type || null;
  // Adapter le champ date (DLC / date d'abattage / aucune) selon le type catalogue.
  appliquerModeDate(dlcTypePrefill);

  // Rattacher le fournisseur de CETTE commande au produit (cas multi-commandes).
  if (ligne._fournisseur_id || ligne._fournisseur_nom) {
    fournisseurProduitSelected = {
      id:  ligne._fournisseur_id  || null,
      nom: (ligne._fournisseur_nom || '').trim() || null,
    };
    // En mode multi, refléter ce fournisseur dans le sélecteur visuel de l'étape 4.
    if (modeMultiFourn && elFournProduitSel) {
      const idx = fournisseursListe.findIndex(f =>
        (ligne._fournisseur_id && f.id === ligne._fournisseur_id) ||
        (ligne._fournisseur_nom && f.nom === ligne._fournisseur_nom));
      if (idx >= 0) elFournProduitSel.value = String(idx);
    }
  }

  // Pré-remplir la recherche produit avec la désignation de la commande
  if (elProdSearch) {
    elProdSearch.value = ligne.designation;
    elProdSearch.dispatchEvent(new Event('input')); // déclenche l'autocomplete
  }

  // Pré-remplir le poids avec la quantité commandée
  const elPoids = document.getElementById('rec-poids');
  if (elPoids) elPoids.value = ligne.quantite_commandee;

  // Badge visuel indiquant la pré-saisie
  const badge = document.createElement('div');
  badge.className = 'rec-commande-prefill-badge';
  badge.style.cssText = 'display:block;background:#166534;color:#fff;padding:.3rem .75rem;border-radius:6px;font-size:.8rem;font-weight:700;margin-bottom:.5rem;';
  badge.textContent = `📋 Commande : ${ligne.code_article} — ${ligne.designation} (${ligne.quantite_commandee} ${ligne.unite})`;

  const formProduit = document.getElementById('rec-form-produit');
  if (formProduit) {
    const existant = formProduit.querySelector('.rec-commande-prefill-badge');
    if (existant) existant.remove();
    formProduit.insertBefore(badge, formProduit.firstChild);
  }
}

async function chargerTextesAide() {
  try {
    textesAide = await apiFetch('/api/receptions/textes-aide-visuel');
  } catch {
    textesAide = {};
  }
}

// Synonymes espèces ↔ codes produits
const SEARCH_SYNONYMS = {
  'boeuf': 'vb', 'bœuf': 'vb', 'bovin': 'vb', 'bovine': 'vb', 'beef': 'vb',
  'agneau': 'agn', 'mouton': 'agn', 'ovin': 'agn',
  'veau': 'vx',
  'porc': 'pc', 'cochon': 'pc', 'porcin': 'pc',
};
const CODE_LABELS = { 'vb': 'boeuf', 'agn': 'agneau', 'vx': 'veau', 'pc': 'porc' };
const STOP_WORDS  = new Set(['de', 'du', 'la', 'le', 'les', 'un', 'une', 'des', 'au', 'et', 'avec', 'sans']);

function filtrerProduits(q) {
  if (!q) return tousProduits.slice(0, 50);
  // Découper en mots, ignorer stop words
  const mots = q.toLowerCase().split(/[\s\-\/,;]+/).filter(m => m.length > 0 && !STOP_WORDS.has(m));
  if (!mots.length) return tousProduits.slice(0, 50);
  // Pour chaque mot, construire ses variantes (mot + synonyme/code)
  const variantes = mots.map(m => {
    const s = new Set([m]);
    if (SEARCH_SYNONYMS[m]) s.add(SEARCH_SYNONYMS[m]);
    if (CODE_LABELS[m])     s.add(CODE_LABELS[m]);
    return [...s];
  });
  return tousProduits.filter(p => {
    const hay = (p.nom + ' ' + (p.code_unique || '')).toLowerCase();
    // Chaque mot doit matcher (directement ou via une de ses variantes)
    return variantes.every(vars => vars.some(v => hay.includes(v)));
  }).slice(0, 50);
}

// Un article catalogue achats n'a pas de `nom` mais `designation` et `code_article`.
// Cette fonction normalise les deux formes pour l'autocomplete et la sélection.
function labelArticle(p) {
  return p.nom || p.designation || '';
}
function codeArticle(p) {
  return p.code_unique || p.code_article || '';
}

function afficherAutoComplete(liste) {
  elProdAutoComplete.innerHTML = '';
  if (!liste.length) {
    elProdAutoComplete.hidden = true;
    return;
  }
  liste.forEach(p => {
    const div = document.createElement('div');
    div.className = 'rec-autocomplete-item';
    div.setAttribute('role', 'option');
    const nom  = document.createElement('span');
    nom.textContent = labelArticle(p);
    const code = document.createElement('span');
    code.className = 'rec-autocomplete-code';
    code.textContent = codeArticle(p);
    div.appendChild(nom);
    div.appendChild(code);
    div.addEventListener('click', () => selectionnerProduit(p));
    elProdAutoComplete.appendChild(div);
  });
  elProdAutoComplete.hidden = false;
}

function selectionnerProduit(p) {
  // p peut être un produit interne (p.nom) ou un article catalogue (p.designation)
  if (!p.nom && p.designation) {
    // Article catalogue : pas de produit interne, on stocke comme article catalogue
    produitSelectionne = p;
    elProdSelNom.textContent  = p.designation;
    elProdSelCode.textContent = p.code_article || '';
    catalogueIdPrefill = p.id;
    dlcTypePrefill     = p.dlc_type || null;
    appliquerModeDate(dlcTypePrefill);
  } else {
    produitSelectionne = p;
    elProdSelNom.textContent  = p.nom;
    elProdSelCode.textContent = p.code_unique || '';
  }
  elProdSel.hidden      = false;
  elProdSearchWrap.hidden = true;
  elProdAutoComplete.hidden = true;
  elProdSearch.value = '';

  // Mise à jour aide visuelle selon l'espèce
  majAideVisuel(p.espece);
  // pH plage
  const aideEspece = textesAide[p.espece];
  elPhPlage.textContent = aideEspece ? `(norme : ${aideEspece.ph.normal})` : '';

  // Verdict température temps réel
  majTempVerdict();
  majBtnAjouter();
}

function majAideVisuel(espece) {
  const aide = textesAide[espece];
  ['couleur', 'consistance', 'exsudat', 'odeur'].forEach(c => {
    const el = document.getElementById(`rec-aide-${c}`);
    if (el) el.textContent = aide ? `Normal : ${aide[c].normal}` : '';
  });
}

elBtnChangerProduit.addEventListener('click', () => {
  produitSelectionne = null;
  elProdSel.hidden = true;
  elProdSearchWrap.hidden = false;
  elProdSearch.value = '';
  afficherAutoComplete(useCatalogueBl() ? catalogueBl.slice(0, 50) : tousProduits.slice(0, 50));
  elProdSearch.focus();
  majBtnAjouter();
});

elProdSearch.addEventListener('input', () => {
  const q = elProdSearch.value.trim();
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    afficherAutoComplete(useCatalogueBl() ? filtrerCatalogueBl(q) : filtrerProduits(q));
  }, 180);
});
elProdSearch.addEventListener('focus', () => {
  if (!produitSelectionne) {
    const q = elProdSearch.value;
    afficherAutoComplete(useCatalogueBl() ? filtrerCatalogueBl(q) : filtrerProduits(q));
  }
});
document.addEventListener('click', e => {
  if (!elProdAutoComplete.contains(e.target) && e.target !== elProdSearch) {
    elProdAutoComplete.hidden = true;
  }
}, true);

// ── Substitution ──────────────────────────────────────────────
elSubstitutionCheck.addEventListener('change', () => {
  elSubstitutionWrap.hidden = !elSubstitutionCheck.checked;
  if (!elSubstitutionCheck.checked) {
    substitutionArticle = null;
    elSubstitutionSearch.value = '';
    elSubstitutionResults.hidden = true;
    elSubstitutionSel.hidden = true;
  } else {
    elSubstitutionSearch.focus();
  }
});

function afficherSubstitutionResultats(articles) {
  elSubstitutionResults.innerHTML = '';
  if (!articles.length) { elSubstitutionResults.hidden = true; return; }
  articles.slice(0, 12).forEach(a => {
    const div = document.createElement('div');
    div.className = 'rec-fourn-item';
    div.textContent = a.designation + (a.code_article ? ` · ${a.code_article}` : '');
    div.addEventListener('click', () => {
      substitutionArticle = { id: a.id, designation: a.designation };
      elSubstitutionSelNom.textContent = a.designation;
      elSubstitutionSel.hidden = false;
      elSubstitutionSearch.value = '';
      elSubstitutionResults.hidden = true;
    });
    elSubstitutionResults.appendChild(div);
  });
  elSubstitutionResults.hidden = false;
}

elSubstitutionSearch.addEventListener('input', () => {
  const q = elSubstitutionSearch.value.trim();
  if (!q) { elSubstitutionResults.hidden = true; return; }
  // Cherche dans le catalogue BL si disponible, sinon texte libre uniquement
  const liste = catalogueBl.length > 0 ? filtrerCatalogueBl(q) : [];
  if (liste.length) {
    afficherSubstitutionResultats(liste);
  } else {
    // Pas de catalogue : stocker le texte libre directement
    substitutionArticle = { id: null, designation: q };
    elSubstitutionSelNom.textContent = q;
    elSubstitutionSel.hidden = false;
    elSubstitutionResults.hidden = true;
  }
});

elSubstitutionSearch.addEventListener('focus', () => {
  const q = elSubstitutionSearch.value.trim();
  if (q && catalogueBl.length > 0) afficherSubstitutionResultats(filtrerCatalogueBl(q));
});

document.addEventListener('click', e => {
  if (!elSubstitutionResults.contains(e.target) && e.target !== elSubstitutionSearch) {
    elSubstitutionResults.hidden = true;
  }
}, true);

elSubstitutionClear.addEventListener('click', () => {
  substitutionArticle = null;
  elSubstitutionSel.hidden = true;
  elSubstitutionSearch.value = '';
});

// Température produit → verdict temps réel
function parseIntervalleTemp(str) {
  if (!str) return null;
  const m = str.match(/([-+]?\d+(?:\.\d+)?)\s*°C\s*à\s*([-+]?\d+(?:\.\d+)?)\s*°C/i);
  if (!m) return null;
  return { min: parseFloat(m[1]), max: parseFloat(m[2]) };
}

/**
 * Évalue la conformité d'une température par rapport à la plage de conservation.
 * Retourne { statut: 'conforme'|'nc'|'attention', texte: string } ou null.
 * Tolérance : borne_min - 1°C à borne_max + 1°C
 */
function evaluerTemperature(tempRecep, tempConservationStr) {
  if (tempRecep === null || tempRecep === undefined || isNaN(tempRecep)) return null;
  const rng = parseIntervalleTemp(tempConservationStr);
  if (!rng) return null;
  const tolMin = rng.min - 1;
  const tolMax = rng.max + 1;
  if (tempRecep >= tolMax) {
    return { statut: 'nc', texte: `NON CONFORME — ${tempRecep}°C ≥ max toléré ${tolMax}°C` };
  }
  if (tempRecep < tolMin) {
    return { statut: 'attention', texte: `Attention — température basse ${tempRecep}°C (min ${tolMin}°C)` };
  }
  return { statut: 'conforme', texte: `Conforme — ${tempRecep}°C (tolérance ${tolMin}°C à ${tolMax}°C)` };
}

function majTempVerdict() {
  if (!elTempVerdict || !produitSelectionne) {
    if (elTempVerdict) elTempVerdict.hidden = true;
    return;
  }
  const tempCamion = parseFloat(elTempCamion.value);
  const verdict = evaluerTemperature(tempCamion, produitSelectionne.temperature_conservation);
  if (!verdict) {
    elTempVerdict.hidden = true;
    return;
  }
  elTempVerdict.hidden = true;
}


// Critères visuels toggles
function reinitCriteres() {
  criteres = { couleur: 1, consistance: 1, exsudat: 1, odeur: 1 };
  CRITERES.forEach(c => {
    const [btnOk, btnNc] = document.querySelectorAll(`[data-critere="${c}"]`);
    btnOk.classList.add('ok-sel');
    btnOk.setAttribute('aria-pressed', 'true');
    btnNc.classList.remove('nc-sel');
    btnNc.setAttribute('aria-pressed', 'false');
    const obsEl = document.getElementById(`rec-obs-${c}`);
    if (obsEl) { obsEl.value = ''; obsEl.hidden = true; }
  });
}

document.querySelectorAll('[data-critere]').forEach(btn => {
  btn.addEventListener('click', () => {
    const c   = btn.dataset.critere;
    const val = parseInt(btn.dataset.val, 10);
    criteres[c] = val;

    const [btnOk, btnNc] = document.querySelectorAll(`[data-critere="${c}"]`);
    if (val === 1) {
      btnOk.classList.add('ok-sel');
      btnNc.classList.remove('nc-sel');
      btnOk.setAttribute('aria-pressed', 'true');
      btnNc.setAttribute('aria-pressed', 'false');
    } else {
      btnNc.classList.add('nc-sel');
      btnOk.classList.remove('ok-sel');
      btnNc.setAttribute('aria-pressed', 'true');
      btnOk.setAttribute('aria-pressed', 'false');
    }

    const obsEl = document.getElementById(`rec-obs-${c}`);
    if (obsEl) obsEl.hidden = (val === 1);
  });
});

function majBtnAjouter() {
  // Lot et DLC ne sont PLUS bloquants : un produit sans lot/DLC est accepté et
  // mis « en attente » (à compléter via la tâche HACCP). Seul le produit est requis.
  // Une date saisie mais invalide (DLC passée) reste bloquante.
  const dateInvalide = elDlc.classList.contains('rec-champ-invalide');
  const ok = produitSelectionne !== null && !dateInvalide;
  elBtnAjouter.disabled   = !ok;
  if (elBtnEnregistrer) elBtnEnregistrer.disabled = !ok;
}

function mettreEnEvidenceChampsManquants() {
  let premier = null;
  if (!produitSelectionne) {
    elProdSearch.classList.add('rec-champ-invalide');
    elProdSearch.title = 'Sélectionnez un produit dans la liste';
    premier = premier || elProdSearch;
  }
  // Seule une date saisie mais invalide (DLC dans le passé) bloque l'ajout.
  // Lot/DLC vides sont autorisés (le produit partira « en attente »).
  if (elDlc.classList.contains('rec-champ-invalide')) {
    elDlc.title = 'La DLC ne peut pas être dans le passé';
    premier = premier || elDlc;
  }
  if (premier) {
    premier.focus();
    // Afficher le tooltip natif temporairement
    const tip = premier.title;
    if (tip) {
      // Force un re-focus pour déclencher l'affichage natif
      premier.blur();
      premier.focus();
    }
  }
  return premier !== null;
}

// Retirer la mise en évidence au focus/input
[elLot, elDlc, elProdSearch].forEach(el => {
  el.addEventListener('input', () => { el.classList.remove('rec-champ-invalide'); el.title = ''; });
  el.addEventListener('focus', () => { el.classList.remove('rec-champ-invalide'); el.title = ''; });
});

// ── Pas de N° de lot : 2 options (lot interne OU en attente) ─
const elLotChoix        = document.getElementById('rec-lot-choix');
const elLotChoixInterne = document.getElementById('rec-lot-choix-interne');
const elLotChoixAttente = document.getElementById('rec-lot-choix-attente');

// ── N° de bon de livraison (1 par réception, préfixe des lots internes) ──
// Enregistre le n° BL sur la réception. Requis pour générer un lot interne au
// format {BL}-{code article}-{JJMMAA}.
async function validerNumeroBl() {
  const numero = (elNumeroBl.value || '').trim();
  if (!numero) {
    afficherHintBl('Saisir un numéro de BL.', true);
    return false;
  }
  // La réception n'existe pas encore (saisie avant le passage à l'étape produits) :
  // on mémorise le n° localement, il sera enregistré à la création de la réception.
  if (!receptionId) {
    numeroBlValide = numero;
    afficherHintBl(`✔ BL enregistré : ${numero} (rattaché au démarrage de la réception)`, false);
    return true;
  }
  try {
    elBtnBlValider.disabled = true;
    await apiFetch(`/api/receptions/${receptionId}/numero-bl`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ numero_bon_livraison: numero }),
    });
    numeroBlValide = numero;
    afficherHintBl(`✔ BL enregistré : ${numero}`, false);
    return true;
  } catch (e) {
    afficherHintBl(`Erreur : ${e.message}`, true);
    return false;
  } finally {
    elBtnBlValider.disabled = false;
  }
}
function afficherHintBl(msg, erreur) {
  if (!elNumeroBlHint) return;
  elNumeroBlHint.textContent = msg;
  elNumeroBlHint.style.color = erreur ? '#991b1b' : '#166534';
  elNumeroBlHint.hidden = false;
}
if (elBtnBlValider) {
  elBtnBlValider.addEventListener('click', validerNumeroBl);
}
// Toute modification après validation invalide l'état enregistré.
if (elNumeroBl) {
  elNumeroBl.addEventListener('input', () => {
    if ((elNumeroBl.value || '').trim() !== numeroBlValide) {
      numeroBlValide = '';
      if (elNumeroBlHint) elNumeroBlHint.hidden = true;
    }
  });
}

// Clic « Pas de N° de lot » → afficher le choix (au lieu de générer directement)
elBtnPasLot.addEventListener('click', () => {
  if (!produitSelectionne || !receptionId) return;
  if (elLotChoix) elLotChoix.hidden = !elLotChoix.hidden;
});

// Option 1 : générer un lot interne (le produit entre en stock normalement)
if (elLotChoixInterne) {
  elLotChoixInterne.addEventListener('click', async () => {
    if (!produitSelectionne || !receptionId) return;
    // Le BL doit être enregistré avant de générer un lot interne (préfixe du lot).
    if (!numeroBlValide) {
      if ((elNumeroBl.value || '').trim()) {
        const ok = await validerNumeroBl();
        if (!ok) return;
      } else {
        afficherHintBl('Saisir et valider le n° de BL avant de générer un lot interne.', true);
        elNumeroBl.focus();
        return;
      }
    }
    elLotChoixInterne.disabled = true;
    elLotChoixInterne.textContent = '⏳…';
    try {
      // code_article du catalogue (article catalogue) ou code_unique (produit interne).
      const code = produitSelectionne.code_article || produitSelectionne.code_unique || '';
      const data = await apiFetch(
        `/api/receptions/${receptionId}/lot-interne?code_article=${encodeURIComponent(code)}`
      );
      const lotNum = data.lot_interne;
      elLot.value    = lotNum;
      elLot.readOnly = true;
      elLot.style.background = '#f0faf3';
      elLotGenere.textContent = `Lot interne : ${lotNum}`;
      elLotGenere.hidden = false;
      elBtnPasLot.hidden = true;
      elBtnAnnulerLot.hidden = false;
      if (elLotChoix) elLotChoix.hidden = true;
      lotInterneGenere = true;
      setLotsSuppVisible(false);
      majBtnAjouter();
    } catch (e) {
      alert(`Erreur génération lot : ${e.message}`);
    } finally {
      elLotChoixInterne.disabled = false;
      elLotChoixInterne.textContent = '🏷️ Générer un lot interne';
    }
  });
}

// Option 2 : laisser en attente (lot vide → produit hors stock à compléter plus tard)
if (elLotChoixAttente) {
  elLotChoixAttente.addEventListener('click', () => {
    elLot.value = '';
    elLot.readOnly = false;
    lotInterneGenere = false;
    elLotGenere.textContent = '⛔ En attente — N° de lot à compléter plus tard';
    elLotGenere.hidden = false;
    if (elLotChoix) elLotChoix.hidden = true;
    setLotsSuppVisible(false);
    majBtnAjouter();
  });
}

elBtnAnnulerLot.addEventListener('click', () => {
  elLot.value    = '';
  elLot.readOnly = false;
  elLot.style.background = '';
  elLotGenere.hidden = true;
  elBtnPasLot.hidden = false;
  elBtnAnnulerLot.hidden = true;
  lotInterneGenere = false;
  setLotsSuppVisible(true);
  majBtnAjouter();
});

elLot.addEventListener('input', majBtnAjouter);

// ── Lot interne sur toute la commande ──────────────────────
// Applique la règle {BL}-{code article}-{JJMMAA} à toutes les lignes déjà
// ajoutées qui n'ont pas de N° de lot (fournisseur sans lot sur son BL).
// Le n° de BL est requis comme préfixe : on le valide d'abord si besoin.
if (elBtnLotsCommande) {
  elBtnLotsCommande.addEventListener('click', async () => {
    if (!receptionId) return;
    // Le BL doit être enregistré avant de générer les lots internes.
    if (!numeroBlValide) {
      if ((elNumeroBl.value || '').trim()) {
        const ok = await validerNumeroBl();
        if (!ok) return;
      } else {
        afficherHintLotsCommande(
          'Saisir et valider le n° de BL (étape précédente) avant de générer les lots internes.',
          true
        );
        return;
      }
    }
    elBtnLotsCommande.disabled = true;
    const label = elBtnLotsCommande.textContent;
    elBtnLotsCommande.textContent = '⏳ Génération…';
    try {
      const res = await apiFetch(`/api/receptions/${receptionId}/lots-internes`, {
        method: 'POST',
      });
      // Recharger les lignes depuis le serveur (lots + statuts à jour).
      await rechargerLignesReception();
      const msgs = [`✔ ${res.generes} lot(s) interne(s) généré(s)`];
      if (res.deja_lot)        msgs.push(`${res.deja_lot} déjà tracé(s)`);
      if (res.restant_attente) msgs.push(`${res.restant_attente} encore en attente (DLC/date à compléter)`);
      afficherHintLotsCommande(msgs.join(' · ') + '.', res.restant_attente > 0);
    } catch (e) {
      afficherHintLotsCommande('Erreur : ' + e.message, true);
    } finally {
      elBtnLotsCommande.disabled = false;
      elBtnLotsCommande.textContent = label;
    }
  });
}

function afficherHintLotsCommande(msg, alerte) {
  if (!elLotsCommandeHint) return;
  elLotsCommandeHint.textContent = msg;
  elLotsCommandeHint.style.color = alerte ? '#991b1b' : '#166534';
  elLotsCommandeHint.hidden = false;
}

// Recharge la liste des lignes de la réception en cours depuis le serveur.
async function rechargerLignesReception() {
  if (!receptionId) return;
  const rec = await apiFetch(`/api/receptions/${receptionId}`);
  lignesAjoutees = (rec.lignes || []).map(l => ({
    id:                    l.id,
    produit_id:            l.produit_id,
    produit_nom:           l.produit_nom,
    catalogue_id:          l.catalogue_fournisseur_id || null,
    fournisseur_id:        l.fournisseur_id || null,
    fournisseur_nom:       l.fournisseur_nom || null,
    conforme:              l.conforme,
    numero_lot:            l.numero_lot,
    lot_interne:           l.lot_interne,
    origine:               l.origine,
    dlc:                   l.dlc,
    dluo:                  l.dluo,
    temperature_reception: l.temperature_reception,
    poids_kg:              l.poids_kg || null,
    statut:                l.statut,
    attente_motif:         l.attente_motif,
    motifs:                [],
    substitution_article:  l.substitution_article || null,
  }));
  majListeLignes();
}

// ── N° de lot supplémentaires ──────────────────────────────
// Permet de saisir plusieurs n° de lot pour un même produit. À l'ajout, une
// ligne de réception distincte est créée par lot (mêmes critères/DLC/origine).
// Désactivé quand le lot est interne ou « en attente » (pas de lot fournisseur).
function ajouterChampLotSupp(valeur = '', dlcVal = '') {
  if (!elLotsSupp) return;
  const row = document.createElement('div');
  row.className = 'rec-lot-supp-row';

  // Ligne lot
  const lotRow = document.createElement('div');
  lotRow.style.cssText = 'display:flex;gap:.5rem;align-items:center;';

  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'rec-input rec-lot-input rec-lot-supp-input';
  input.placeholder = 'ex : LOT-2026-002';
  input.autocomplete = 'off';
  input.setAttribute('aria-label', 'Numéro de lot fournisseur supplémentaire');
  input.value = valeur;
  input.style.flex = '1';
  input.addEventListener('input', majBtnAjouter);

  const rm = document.createElement('button');
  rm.type = 'button';
  rm.className = 'rec-fourn-clear';
  rm.setAttribute('aria-label', 'Retirer ce n° de lot');
  rm.textContent = '✕';
  rm.style.flexShrink = '0';
  rm.addEventListener('click', () => {
    row.remove();
    majLotsSuppHint();
    majBtnAjouter();
  });

  lotRow.appendChild(input);
  lotRow.appendChild(rm);

  // Ligne DLC
  const dlcRow = document.createElement('div');
  dlcRow.style.cssText = 'display:flex;gap:.5rem;align-items:center;margin-top:.3rem;';

  const dlcLabel = document.createElement('span');
  dlcLabel.className = 'rec-lot-supp-dlc-label';
  // Le libellé s'adapte au mode de date courant
  dlcLabel.textContent = dlcMode === 'abattage' ? "Date d'abattage :" : 'DLC :';
  dlcLabel.style.cssText = 'font-size:.8rem;color:var(--color-offline);white-space:nowrap;flex-shrink:0;';

  const dlcInput = document.createElement('input');
  dlcInput.type = 'date';
  dlcInput.className = 'rec-input rec-lot-supp-dlc';
  dlcInput.setAttribute('aria-label', dlcMode === 'abattage' ? "Date d'abattage pour ce lot" : 'DLC pour ce lot');
  dlcInput.value = dlcVal;
  dlcInput.style.flex = '1';

  dlcRow.appendChild(dlcLabel);
  dlcRow.appendChild(dlcInput);

  row.appendChild(lotRow);
  row.appendChild(dlcRow);
  elLotsSupp.appendChild(row);
  majLotsSuppHint();
  input.focus();
}

// Lots supplémentaires saisis : retourne [{lot, dlc}] (valeurs non vides)
function lotsSuppValeurs() {
  if (!elLotsSupp) return [];
  return [...elLotsSupp.querySelectorAll('.rec-lot-supp-row')].map(row => ({
    lot: (row.querySelector('.rec-lot-supp-input')?.value || '').trim(),
    dlc: (row.querySelector('.rec-lot-supp-dlc')?.value   || ''),
  })).filter(p => p.lot);
}

function viderLotsSupp() {
  if (elLotsSupp) elLotsSupp.innerHTML = '';
  majLotsSuppHint();
}

function majLotsSuppHint() {
  if (elLotsSuppHint) {
    elLotsSuppHint.hidden = !(elLotsSupp && elLotsSupp.children.length > 0);
  }
}

// Masque l'ajout de lots multiples quand le lot n'est pas un lot fournisseur saisi
function setLotsSuppVisible(visible) {
  if (elBtnAddLot) elBtnAddLot.hidden = !visible;
  if (!visible) viderLotsSupp();
}

if (elBtnAddLot) {
  elBtnAddLot.addEventListener('click', () => ajouterChampLotSupp());
}

// ── DLC / DLUO toggle ──────────────────────────────────────
elDlcBtn.addEventListener('click', () => {
  dlcMode = 'dlc';
  elDlcBtn.classList.add('ok-sel');
  elDluoBtn.classList.remove('ok-sel');
  elDlcBtn.setAttribute('aria-pressed', 'true');
  elDluoBtn.setAttribute('aria-pressed', 'false');
  elDlcLabelText.textContent = 'DLC';
});
elDluoBtn.addEventListener('click', () => {
  dlcMode = 'dluo';
  elDluoBtn.classList.add('ok-sel');
  elDlcBtn.classList.remove('ok-sel');
  elDluoBtn.setAttribute('aria-pressed', 'true');
  elDlcBtn.setAttribute('aria-pressed', 'false');
  elDlcLabelText.textContent = 'DLUO';
});

// Adapte le champ date selon le type de DLC du catalogue.
//  - 'date_abattage' → libellé « Date d'abattage », toggle DLC/DLUO masqué, date passée (carcasse)
//  - 'no_dlc'        → champ date masqué (aucune date requise)
//  - 'dlc' / null    → comportement standard (toggle DLC/DLUO visible)
function appliquerModeDate(dlcType) {
  const toggle  = document.querySelector('.rec-dlc-toggle');
  const groupe  = elDlc ? elDlc.closest('.rec-form-group') : null;
  if (dlcType === 'date_abattage') {
    dlcMode = 'abattage';
    elDlcLabelText.textContent = "Date d'abattage";
    if (toggle)  toggle.hidden = true;
    if (groupe)  groupe.hidden = false;
    elDlc.removeAttribute('min'); // l'abattage est une date passée
  } else if (dlcType === 'no_dlc') {
    dlcMode = 'no_dlc';
    if (groupe) groupe.hidden = true;
  } else {
    dlcMode = 'dlc';
    elDlcLabelText.textContent = 'DLC';
    if (toggle) toggle.hidden = false;
    if (groupe) groupe.hidden = false;
    elDlcBtn.classList.add('ok-sel');
    elDluoBtn.classList.remove('ok-sel');
    elDlcBtn.setAttribute('aria-pressed', 'true');
    elDluoBtn.setAttribute('aria-pressed', 'false');
  }
}
elDlc.addEventListener('input', () => {
  // Validation « ≥ aujourd'hui » uniquement pour DLC/DLUO.
  // Une date d'abattage est par nature passée → pas de contrôle de futur.
  if (elDlc.value && dlcMode !== 'abattage') {
    const today = new Date().toISOString().slice(0, 10);
    if (elDlc.value < today) {
      elDlc.classList.add('rec-champ-invalide');
    } else {
      elDlc.classList.remove('rec-champ-invalide');
    }
  } else {
    elDlc.classList.remove('rec-champ-invalide');
  }
  majBtnAjouter();
});

function reinitFormProduit() {
  produitSelectionne = null;
  ligneEnEdition     = null;
  lotInterneGenere   = false;
  dlcMode            = 'dlc';
  fournisseurProduitSelected = null;
  catalogueIdPrefill = null;
  dlcTypePrefill     = null;
  substitutionArticle = null;
  if (elSubstitutionCheck) elSubstitutionCheck.checked = false;
  if (elSubstitutionWrap)  elSubstitutionWrap.hidden = true;
  if (elSubstitutionSel)   elSubstitutionSel.hidden = true;
  if (elSubstitutionSearch) elSubstitutionSearch.value = '';

  elProdSel.hidden       = true;
  elProdSearchWrap.hidden = false;
  if (elTempVerdict) elTempVerdict.hidden = true;

  // Réinitialiser le sélecteur fournisseur
  if (elFournProduitSel) {
    elFournProduitSel.value = '';
  }
  elProdSearch.value      = '';
  elProdAutoComplete.hidden = true;

  // Lot
  elLot.value    = '';
  elLot.readOnly = false;
  elLot.style.background = '';
  elLotGenere.hidden = true;
  elBtnPasLot.hidden = false;
  elBtnAnnulerLot.hidden = true;
  if (typeof elLotChoix !== 'undefined' && elLotChoix) elLotChoix.hidden = true;
  // Lots supplémentaires : on repart d'un formulaire propre, ajout réactivé
  if (typeof setLotsSuppVisible === 'function') setLotsSuppVisible(true);

  // Origine : défaut France à chaque nouveau produit
  if (elOrigine) elOrigine.value = 'France';
  if (elOrigineList) elOrigineList.hidden = true;

  // DLC reset to DLC mode (champ + toggle visibles)
  elDlc.value = '';
  appliquerModeDate('dlc');

  elPh.value  = '';
  elPhPlage.textContent = '';
  const elPoidsUnitaire = document.getElementById('rec-poids');
  if (elPoidsUnitaire) elPoidsUnitaire.value = '';

  CRITERES.forEach(c => {
    document.getElementById(`rec-aide-${c}`).textContent = '';
  });
  reinitCriteres();

  // Boutons footer
  elBtnAjouter.hidden    = false;
  if (elBtnEnregistrer) elBtnEnregistrer.hidden = true;

  majBtnAjouter();
}

function majListeLignes() {
  elNbProduits.textContent = lignesAjoutees.length;
  elLignesListe.innerHTML  = '';
  lignesAjoutees.forEach((l, idx) => {
    const carte = document.createElement('div');
    carte.className = 'rec-ligne-carte';
    if (ligneEnEdition && ligneEnEdition.id === l.id) carte.classList.add('edition');

    const info = document.createElement('div');
    info.className = 'rec-ligne-info';

    const nom = document.createElement('div');
    nom.className = 'rec-ligne-nom';
    nom.textContent = l.produit_nom;

    const detail = document.createElement('div');
    detail.className = 'rec-ligne-detail';
    const parts = [];
    if (l.temperature_reception !== null && l.temperature_reception !== undefined) {
      parts.push(`${l.temperature_reception}°C`);
    }
    if (l.numero_lot) parts.push(l.numero_lot);
    if (l.origine) parts.push(`Origine : ${origineCode(l.origine)}`);
    detail.textContent = parts.join(' · ');

    info.appendChild(nom);
    if (parts.length) info.appendChild(detail);

    // Bandeau « en attente » : produit accepté mais hors stock tant que lot/DLC manquant
    if (l.statut === 'en_attente') {
      carte.classList.add('en-attente');
      const att = document.createElement('div');
      att.className = 'rec-ligne-attente';
      att.textContent = `⛔ En attente — ${libelleMotifAttente(l.attente_motif)}`;
      info.appendChild(att);
    }

    const btnModif = document.createElement('button');
    btnModif.className   = 'rec-ligne-modifier';
    btnModif.textContent = '✏️';
    btnModif.title       = 'Modifier ce produit';
    btnModif.addEventListener('click', () => chargerLigneEnEdition(l, idx));

    const badge = document.createElement('span');
    badge.className = 'rec-ligne-badge ' + (l.conforme ? 'ok' : 'nc');
    badge.textContent = l.conforme ? '✓ OK' : '✗ NC';

    carte.appendChild(info);
    carte.appendChild(btnModif);
    carte.appendChild(badge);
    elLignesListe.appendChild(carte);
  });

  elBtnTerminer.disabled = (lignesAjoutees.length === 0);
  majBtnLotsCommande();
}

// Affiche le bouton « lot interne sur toute la commande » dès qu'au moins une
// ligne ajoutée n'a pas de N° de lot (ni fournisseur, ni interne).
function majBtnLotsCommande() {
  if (!elBtnLotsCommande) return;
  const sansLot = lignesAjoutees.filter(
    l => !((l.numero_lot || '').trim()) && !l.lot_interne
  ).length;
  if (sansLot > 0) {
    elBtnLotsCommande.hidden = false;
    elBtnLotsCommande.textContent =
      `🏷️ Lot interne sur toute la commande (${sansLot} sans n° de lot)`;
  } else {
    elBtnLotsCommande.hidden = true;
    if (elLotsCommandeHint) elLotsCommandeHint.hidden = true;
  }
}

function chargerLigneEnEdition(l, idx) {
  ligneEnEdition = { id: l.id, index: idx };

  // Restaurer le produit (produit interne ou article catalogue)
  const produit = l.produit_id ? tousProduits.find(p => p.id === l.produit_id) : null;
  if (produit) {
    selectionnerProduit(produit);
  } else if (l.produit_nom) {
    // Article catalogue : afficher le nom sans objet produit interne
    produitSelectionne = { designation: l.produit_nom };
    elProdSelNom.textContent  = l.produit_nom;
    elProdSelCode.textContent = '';
    elProdSel.hidden       = false;
    elProdSearchWrap.hidden = true;
    majBtnAjouter();
  }

  // Restaurer le fournisseur de la ligne (id et/ou nom) + sélecteur
  if (l.fournisseur_id || l.fournisseur_nom) {
    fournisseurProduitSelected = {
      id: l.fournisseur_id || null,
      nom: (l.fournisseur_nom || '').trim() || null,
    };
    if (modeMultiFourn && elFournProduitSel) {
      let fIdx = -1;
      if (l.fournisseur_id) {
        fIdx = fournisseursListe.findIndex(f => f.id === l.fournisseur_id);
      }
      if (fIdx < 0 && l.fournisseur_nom) {
        fIdx = fournisseursListe.findIndex(f => (f.nom || '') === l.fournisseur_nom);
      }
      elFournProduitSel.value = fIdx >= 0 ? String(fIdx) : '';
    }
  }

  // Restaurer lot — en édition, on modifie une seule ligne : pas de multi-lot
  setLotsSuppVisible(false);
  elLot.readOnly = false;
  elLot.style.background = '';
  elLot.value = l.numero_lot || '';
  lotInterneGenere = !!l.lot_interne;
  if (lotInterneGenere) {
    elLot.readOnly = true;
    elLot.style.background = '#f0faf3';
    elLotGenere.textContent = `Lot interne : ${l.numero_lot}`;
    elLotGenere.hidden = false;
    elBtnPasLot.hidden = true;
    elBtnAnnulerLot.hidden = false;
  }

  // Restaurer Origine
  if (elOrigine) elOrigine.value = l.origine || 'France';

  // Restaurer DLC/DLUO
  if (l.dluo) {
    dlcMode = 'dluo';
    elDluoBtn.classList.add('ok-sel');
    elDlcBtn.classList.remove('ok-sel');
    elDlcLabelText.textContent = 'DLUO';
    elDlc.value = l.dluo;
  } else {
    dlcMode = 'dlc';
    elDlcBtn.classList.add('ok-sel');
    elDluoBtn.classList.remove('ok-sel');
    elDlcLabelText.textContent = 'DLC';
    elDlc.value = l.dlc || '';
  }

  // Boutons footer
  elBtnAjouter.hidden    = true;
  if (elBtnEnregistrer) elBtnEnregistrer.hidden = false;
  majBtnAjouter();
  majListeLignes(); // refresh cartes

  // Scroll vers le formulaire
  document.querySelector('.rec-form-produit').scrollIntoView({ behavior: 'smooth' });
}

elBtnAjouter.addEventListener('click', () => {
  ajouterLigne();
});
// Clic sur zone autour du bouton grisé → mise en évidence des champs manquants
document.querySelector('.rec-step3-footer').addEventListener('click', e => {
  if (e.target === elBtnAjouter || e.target === elBtnEnregistrer) return;
  if (elBtnAjouter.disabled && !elBtnAjouter.hidden) mettreEnEvidenceChampsManquants();
  if (elBtnEnregistrer && elBtnEnregistrer.disabled && !elBtnEnregistrer.hidden) mettreEnEvidenceChampsManquants();
});
if (elBtnEnregistrer) elBtnEnregistrer.addEventListener('click', enregistrerModification);

function _buildPayload() {
  // Article catalogue (pas de produit interne) : designation_libre + catalogue_fournisseur_id
  const estArticleCatalogue = produitSelectionne && !produitSelectionne.nom && produitSelectionne.designation;
  const payload = {
    ...(estArticleCatalogue
      ? { designation_libre: produitSelectionne.designation }
      : { produit_id: produitSelectionne.id }),
    couleur_conforme:     criteres.couleur,
    consistance_conforme: criteres.consistance,
    exsudat_conforme:     criteres.exsudat,
    odeur_conforme:       criteres.odeur,
    lot_interne:          lotInterneGenere ? 1 : 0,
  };
  // Fournisseur du produit : envoyer id (si lié à la table fournisseurs) ET nom (toujours)
  // pour que les fournisseurs en texte libre soient aussi associés à la ligne.
  const fSel = fournisseurProduitSelected
    || (fournisseursListe[0] && (fournisseursListe[0].id || fournisseursListe[0].nom)
        ? { id: fournisseursListe[0].id || null,
            nom: (fournisseursListe[0].nom || '').trim() || null }
        : null);
  if (fSel) {
    if (fSel.id)  payload.fournisseur_id  = fSel.id;
    if (fSel.nom) payload.fournisseur_nom = fSel.nom;
  }
  // La température du camion sert d'évaluation thermique pour chaque produit
  const tempCamion = parseFloat(elTempCamion.value);
  if (!isNaN(tempCamion)) payload.temperature_reception = tempCamion;
  const obsC = document.getElementById('rec-obs-couleur').value.trim();
  const obsT = document.getElementById('rec-obs-consistance').value.trim();
  const obsE = document.getElementById('rec-obs-exsudat').value.trim();
  const obsO = document.getElementById('rec-obs-odeur').value.trim();
  if (obsC) payload.couleur_observation    = obsC;
  if (obsT) payload.consistance_observation = obsT;
  if (obsE) payload.exsudat_observation    = obsE;
  if (obsO) payload.odeur_observation      = obsO;
  const lot = elLot.value.trim();
  if (lot) payload.numero_lot = lot;
  const origineVal = (elOrigine && elOrigine.value || '').trim();
  payload.origine = origineVal || 'France';
  const dateVal = elDlc.value;
  if (dateVal) {
    if (dlcMode === 'dluo')          payload.dluo          = dateVal;
    else if (dlcMode === 'abattage') payload.date_abattage = dateVal;
    else                             payload.dlc           = dateVal;
  }
  const ph = parseFloat(elPh.value);
  if (!isNaN(ph)) payload.ph_valeur = ph;
  const elPoidsUnitaire = document.getElementById('rec-poids');
  if (elPoidsUnitaire) {
    const poids = parseFloat(elPoidsUnitaire.value);
    if (!isNaN(poids) && poids > 0) payload.poids_kg = poids;
  }
  // Référence catalogue issue de la commande (suivi du stock par référence)
  if (catalogueIdPrefill) payload.catalogue_fournisseur_id = catalogueIdPrefill;
  // Type de DLC catalogue → détermine l'exigence de traçabilité (statut en attente)
  if (dlcTypePrefill) payload.dlc_type = dlcTypePrefill;
  // Substitution : article commandé initialement livré à la place de ce produit
  if (substitutionArticle) payload.substitution_article = substitutionArticle.designation;
  return payload;
}

function _ligneToLocal(ligne, produit) {
  const motifsNc = [];
  if (ligne.temperature_conforme === 0) motifsNc.push('température');
  if (ligne.couleur_conforme     === 0) motifsNc.push('couleur');
  if (ligne.consistance_conforme === 0) motifsNc.push('consistance');
  if (ligne.exsudat_conforme     === 0) motifsNc.push('exsudat');
  if (ligne.odeur_conforme       === 0) motifsNc.push('odeur');
  if (ligne.ph_conforme          === 0) motifsNc.push('pH');

  // Résoudre le fournisseur : priorité aux champs renvoyés par le serveur
  // (corrects en mode batch multi-commandes), sinon repli sur la sélection locale.
  let fournId  = ligne.fournisseur_id  ?? null;
  let fournNom = ligne.fournisseur_nom ?? null;
  if (!fournId && !fournNom) {
    const fSel = fournisseurProduitSelected
      || (fournisseursListe[0] && (fournisseursListe[0].id || fournisseursListe[0].nom)
          ? { id: fournisseursListe[0].id || null,
              nom: (fournisseursListe[0].nom || '').trim() || null }
          : null);
    fournId  = fSel ? fSel.id  : null;
    fournNom = fSel ? fSel.nom : null;
  }
  if (!fournNom && fournId) {
    const fObj = tousFournisseurs.find(f => f.id === fournId);
    if (fObj) fournNom = fObj.nom;
  }

  const estCat = produit && !produit.nom && produit.designation;
  return {
    id:                  ligne.id,
    produit_id:          estCat ? null : (produit ? produit.id : null),
    produit_nom:         estCat ? produit.designation : (produit ? produit.nom : null),
    catalogue_id:        ligne.catalogue_fournisseur_id || null,
    fournisseur_id:      fournId,
    fournisseur_nom:     fournNom,
    conforme:            ligne.conforme,
    temperature_reception: ligne.temperature_reception,
    poids_kg:            ligne.poids_kg || null,
    numero_lot:          ligne.numero_lot,
    lot_interne:         ligne.lot_interne,
    origine:             ligne.origine || 'France',
    dlc:                 ligne.dlc,
    dluo:                ligne.dluo,
    statut:              ligne.statut || 'complet',
    attente_motif:       ligne.attente_motif || null,
    motifs:              motifsNc,
    substitution_article: ligne.substitution_article || null,
  };
}

// Libellé court du motif d'attente (lot/DLC manquant)
function libelleMotifAttente(motif) {
  if (motif === 'lot_dlc') return 'lot + DLC à compléter';
  if (motif === 'lot')     return 'lot à compléter';
  if (motif === 'dlc')     return 'DLC à compléter';
  return 'à compléter';
}

async function ajouterLigne() {
  if (!produitSelectionne || !receptionId) return;

  // Plusieurs n° de lot → 1 ligne de réception par lot, chacun avec sa propre DLC.
  const payloadBase = _buildPayload();
  const lotPrincipal = (elLot.value || '').trim();
  const dlcPrincipale = elDlc.value; // déjà intégrée dans payloadBase
  const lotsSupp = lotsSuppValeurs(); // [{lot, dlc}]

  // Construire la liste finale de paires {lot, dlc}, dédupliquées par n° de lot.
  const seenLots = new Set();
  const paires = [];
  if (lotPrincipal) seenLots.add(lotPrincipal);
  paires.push({ lot: lotPrincipal, dlc: dlcPrincipale });
  for (const { lot, dlc } of lotsSupp) {
    if (!lot || seenLots.has(lot)) continue;
    seenLots.add(lot);
    paires.push({ lot, dlc: dlc || dlcPrincipale });
  }
  // Si aucun lot saisi (produit en attente), on garde la paire vide pour 1 ligne.

  elBtnAjouter.disabled = true;
  elBtnAjouter.textContent = paires.length > 1 ? `Ajout (0/${paires.length})…` : 'Ajout…';

  try {
    for (let i = 0; i < paires.length; i++) {
      const { lot, dlc } = paires[i];
      const payload = { ...payloadBase };

      if (lot) payload.numero_lot = lot;
      else     delete payload.numero_lot;

      // DLC spécifique à ce lot (override si différente du lot principal)
      if (dlc && dlc !== dlcPrincipale) {
        delete payload.dlc;
        delete payload.dluo;
        delete payload.date_abattage;
        if (dlcMode === 'dluo')          payload.dluo          = dlc;
        else if (dlcMode === 'abattage') payload.date_abattage = dlc;
        else                             payload.dlc           = dlc;
      }

      const ligne = await apiFetch(`/api/receptions/${receptionId}/lignes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      lignesAjoutees.push(_ligneToLocal(ligne, produitSelectionne));
      if (paires.length > 1) {
        elBtnAjouter.textContent = `Ajout (${i + 1}/${paires.length})…`;
      }
    }

    // Sauvegarder le fournisseur avant le reinit (objet {id, nom})
    if (fournisseurProduitSelected) {
      dernierFournisseurProduit = { ...fournisseurProduitSelected };
    } else if (fournisseursListe[0] && (fournisseursListe[0].id || fournisseursListe[0].nom)) {
      dernierFournisseurProduit = {
        id: fournisseursListe[0].id || null,
        nom: (fournisseursListe[0].nom || '').trim() || null,
      };
    } else {
      dernierFournisseurProduit = null;
    }

    majListeLignes();
    reinitFormProduit();
    document.querySelector('.rec-produits-liste-ajoutee').scrollTop = 9999;

    // Proposer le même fournisseur pour le prochain produit
    afficherModalFournisseur();

  } catch (err) {
    alert(`Erreur lors de l'ajout : ${err.message}`);
    majListeLignes(); // refléter les lignes éventuellement déjà créées
  } finally {
    elBtnAjouter.disabled = !produitSelectionne;
    elBtnAjouter.textContent = '+ Ajouter';
  }
}

/** Affiche le modal "Même fournisseur ?" pour le prochain produit. */
function afficherModalFournisseur() {
  if (!dernierFournisseurProduit) return;
  // En mono-fournisseur, inutile de demander : c'est forcément le même.
  if (!modeMultiFourn || fournisseursListe.length <= 1) return;

  // Nom à afficher : déjà porté par l'objet, sinon résolution par id
  let nomFourn = dernierFournisseurProduit.nom || null;
  if (!nomFourn && dernierFournisseurProduit.id) {
    const fournObj = fournisseursListe.find(f => f.id === dernierFournisseurProduit.id)
      || tousFournisseurs.find(f => f.id === dernierFournisseurProduit.id);
    if (fournObj) nomFourn = fournObj.nom;
  }
  if (!nomFourn) return;

  elDialogFournTexte.textContent =
    `Même fournisseur que le produit précédent ? (${nomFourn})`;
  elDialogFourn.hidden = false;
}

async function enregistrerModification() {
  if (!produitSelectionne || !receptionId || !ligneEnEdition) return;

  if (elBtnEnregistrer) { elBtnEnregistrer.disabled = true; elBtnEnregistrer.textContent = 'Enregistrement…'; }

  try {
    const ligne = await apiFetch(
      `/api/receptions/${receptionId}/lignes/${ligneEnEdition.id}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(_buildPayload()),
      }
    );

    lignesAjoutees[ligneEnEdition.index] = _ligneToLocal(ligne, produitSelectionne);
    majListeLignes();
    reinitFormProduit();

  } catch (err) {
    alert(`Erreur lors de la modification : ${err.message}`);
  } finally {
    if (elBtnEnregistrer) { elBtnEnregistrer.disabled = false; elBtnEnregistrer.textContent = '✓ Enregistrer'; }
  }
}

// ═══════════════════════════════════════════════════════════
//  EXTRACTION OCR DU BON DE LIVRAISON (étape 3)
//  Lit la photo BL déjà stockée et pré-remplit les cartes batch.
//  Garde-fou HACCP : rien n'est enregistré ici — l'utilisateur valide
//  chaque ligne (lot/DLC) avant la suite. Les lignes douteuses sont surlignées.
// ═══════════════════════════════════════════════════════════
const elOcrBloc   = document.getElementById('rec-ocr-bloc');
const elBtnOcrBl  = document.getElementById('rec-btn-ocr-bl');
const elOcrStatut = document.getElementById('rec-ocr-statut');

// Affiche le bloc OCR si une photo de BL a été prise (1er fournisseur).
// Affiché dès qu'il y a une photo de BL et que la fiche est créée (receptionId).
// Fonctionne dans les DEUX cas :
//  • sans commande → l'OCR crée les cartes
//  • avec commande → l'OCR remplit lot/DLC sur les cartes déjà créées (cas le
//    plus utile : on connaît les articles attendus, l'OCR complète la traçabilité)
function majBlocOcr() {
  if (!elOcrBloc) return;
  const aPhotoBl = (fournisseursListe[0]?.photos || []).length > 0;
  elOcrBloc.hidden = !(aPhotoBl && receptionId);
  if (elOcrStatut) elOcrStatut.hidden = true;
}

if (elBtnOcrBl) {
  elBtnOcrBl.addEventListener('click', lancerExtractionOcr);
}

async function lancerExtractionOcr() {
  if (!receptionId) return;
  elBtnOcrBl.disabled = true;
  elBtnOcrBl.textContent = '⏳ Lecture du BL en cours…';
  if (elOcrStatut) { elOcrStatut.hidden = false; elOcrStatut.className = 'rec-ocr-statut'; elOcrStatut.textContent = 'Analyse de la photo…'; }
  const barre = demarrerBarreOcr(elOcrStatut);

  try {
    const data = await apiFetch(`/api/receptions/${receptionId}/ocr-bl`, { method: 'POST' });
    barre.terminer();
    const lignes = data.lignes || [];
    if (!lignes.length) {
      throw new Error("Aucun article lu sur le BL. Saisie manuelle nécessaire.");
    }
    // Pré-remplir le n° BL extrait (à confirmer manuellement via "Valider").
    if (data.numero_bl && elNumeroBl && !numeroBlValide) {
      elNumeroBl.value = data.numero_bl;
      afficherHintBl('N° BL extrait du BL — vérifier puis cliquer « Valider ».', false);
    }
    prefillBatchDepuisOcr(lignes);

    const nbSuspect = lignes.filter(l => l.dlc_suspecte).length;
    elOcrBloc.hidden = true;  // l'extraction est faite, on masque le bouton
    if (elOcrStatut) {
      elOcrStatut.hidden = false;
      elOcrStatut.className = 'rec-ocr-statut ok';
      elOcrStatut.textContent = nbSuspect
        ? `✓ ${lignes.length} article(s) lus — ⚠️ ${nbSuspect} à vérifier (surlignés). Contrôlez chaque DLC.`
        : `✓ ${lignes.length} article(s) lus. Contrôlez chaque ligne avant d'enregistrer.`;
    }
  } catch (err) {
    barre.annuler();
    elBtnOcrBl.disabled = false;
    elBtnOcrBl.textContent = '🔍 Extraire le BL automatiquement';
    if (elOcrStatut) {
      elOcrStatut.hidden = false;
      elOcrStatut.className = 'rec-ocr-statut erreur';
      elOcrStatut.textContent = `⚠️ ${err.message}`;
    }
  }
}

// Barre de progression « estimée » pour l'OCR : l'extraction est un appel unique
// (analyse Claude vision, ~15-30 s) dont on ne connaît pas l'avancement réel. On
// anime donc une barre qui monte progressivement vers 90 % sur une durée typique,
// puis se complète à 100 % à la réception de la réponse. But : donner à l'utilisateur
// un repère « combien de temps attendre » plutôt qu'un simple ⏳ figé.
// `ancre` : élément après lequel la barre est insérée (comme frère). Une barre
// déjà présente est réutilisée (cas « relancer l'OCR »).
function demarrerBarreOcr(ancre) {
  injecterStylesBarreOcr();
  let wrap = ancre && ancre.nextElementSibling && ancre.nextElementSibling.classList.contains('ocr-barre')
    ? ancre.nextElementSibling : null;
  if (!wrap && ancre && ancre.parentNode) {
    wrap = document.createElement('div');
    wrap.className = 'ocr-barre';
    wrap.innerHTML = '<div class="ocr-barre-piste"><div class="ocr-barre-jauge"></div></div>'
                   + '<div class="ocr-barre-txt">0 %</div>';
    ancre.parentNode.insertBefore(wrap, ancre.nextSibling);
  }
  const jauge = wrap ? wrap.querySelector('.ocr-barre-jauge') : null;
  const txt   = wrap ? wrap.querySelector('.ocr-barre-txt')   : null;

  const DUREE_ESTIMEE = 22000;  // ms : durée typique d'un appel OCR
  const PLAFOND = 90;           // on ne dépasse pas 90 % tant que ce n'est pas fini
  const t0 = Date.now();
  let timer = null;

  function rendu(pct) {
    if (jauge) jauge.style.width = pct + '%';
    if (txt)   txt.textContent = Math.round(pct) + ' %';
  }
  function tick() {
    const ecoule = Date.now() - t0;
    // Progression qui ralentit en approchant du plafond (asymptotique).
    const pct = PLAFOND * (1 - Math.exp(-ecoule / (DUREE_ESTIMEE / 2.3)));
    rendu(pct);
    timer = setTimeout(tick, 150);
  }
  if (wrap) { wrap.hidden = false; tick(); }

  return {
    terminer() {
      clearTimeout(timer);
      rendu(100);
      if (wrap) { wrap.classList.add('ocr-barre--ok'); setTimeout(() => wrap.remove(), 600); }
    },
    annuler() {
      clearTimeout(timer);
      if (wrap) wrap.remove();
    },
  };
}

let _stylesBarreOcrInjectes = false;
function injecterStylesBarreOcr() {
  if (_stylesBarreOcrInjectes) return;
  _stylesBarreOcrInjectes = true;
  const st = document.createElement('style');
  st.textContent = `
    .ocr-barre { margin-top:.6rem; }
    .ocr-barre-piste {
      height:8px; border-radius:6px; background:#e5ddd4; overflow:hidden;
    }
    .ocr-barre-jauge {
      height:100%; width:0%; border-radius:6px;
      background:linear-gradient(90deg,#c8852f,#e0a64b);
      transition:width .15s linear;
    }
    .ocr-barre--ok .ocr-barre-jauge { background:#3aa657; }
    .ocr-barre-txt {
      margin-top:.25rem; font-size:.78rem; font-weight:600; color:#5a3e28;
      text-align:right;
    }`;
  document.head.appendChild(st);
}

// Construit les cartes batch à partir des lignes OCR et pré-remplit lot/DLC/poids.
// Réutilise le mode batch existant : chaque ligne OCR devient un « ligneCmd »
// minimal (pas de catalogue, désignation = libellé lu). L'utilisateur corrige.
function prefillBatchDepuisOcr(lignes) {
  // Si une commande est déjà liée, des cartes batch existent déjà : on REMPLIT
  // ces cartes par appariement (sans les recréer). Sinon, on crée une carte par
  // ligne OCR.
  const commandeLiee = modeBatch && batchLignes.length > 0;
  if (commandeLiee) {
    prefillCartesExistantes(lignes);
  } else {
    creerCartesDepuisOcr(lignes);
  }
  majBtnTerminerBatch();
}

// Normalise un libellé pour comparer deux désignations (minuscules, sans accents,
// sans ponctuation). Sert à apparier une ligne OCR à une carte de commande.
function _normLibelle(s) {
  return (s || '')
    .toLowerCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '')   // retire les accents
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

// Score de recouvrement de mots entre deux libellés (0 à 1).
function _scoreLibelle(a, b) {
  const ma = new Set(_normLibelle(a).split(' ').filter(Boolean));
  const mb = new Set(_normLibelle(b).split(' ').filter(Boolean));
  if (!ma.size || !mb.size) return 0;
  let communs = 0;
  ma.forEach(m => { if (mb.has(m)) communs++; });
  return communs / Math.min(ma.size, mb.size);
}

// Applique lot/DLC/poids d'une ligne OCR sur une carte batch (état existant ou neuf).
// Si le lot principal est déjà rempli (ligne OCR précédente pour le MÊME article :
// article livré en plusieurs lots), on AJOUTE un champ lot supplémentaire au lieu
// d'écraser → 1 ligne de réception par couple (lot, DLC) à la validation.
function _appliquerOcrSurCarte(etat, l) {
  const carte = etat.el;
  const inpLot   = carte.querySelector('.rec-batch-lot');
  const inpDate  = carte.querySelector('.rec-batch-date');
  const inpPoids = carte.querySelector('.rec-batch-poids');

  const lotPrincipalRempli = inpLot && inpLot.value.trim() !== '';
  if (l.numero_lot && lotPrincipalRempli && inpLot.value.trim() !== l.numero_lot) {
    // Lot supplémentaire pour cet article (DLC propre au lot).
    ajouterChampLotSuppBatch(etat, l.numero_lot, l.dlc || '');
  } else {
    // On ne remplit que les champs vides : ne jamais écraser une saisie manuelle.
    if (inpLot && l.numero_lot && !inpLot.value.trim())   inpLot.value  = l.numero_lot;
    if (inpDate && l.dlc && !inpDate.value)               inpDate.value = l.dlc;  // ISO
  }
  if (inpPoids && l.poids_kg != null && !inpPoids.value) inpPoids.value = l.poids_kg;

  if (l.dlc_suspecte) {
    carte.classList.add('rec-batch-ocr-suspect');
    if (l.alerte && !carte.querySelector('.rec-batch-ocr-alerte')) {
      const note = document.createElement('div');
      note.className = 'rec-batch-ocr-alerte';
      note.textContent = `⚠️ ${l.alerte} — à vérifier`;
      carte.querySelector('.rec-batch-champs')?.before(note);
    }
  }
  majBadgeCarte(etat);
}

// Cas SANS commande : une carte par article. Les lignes OCR partageant le même
// article (même désignation/référence) sont regroupées sur UNE carte : le 1er lot
// remplit le lot principal, les suivants deviennent des lots supplémentaires.
function creerCartesDepuisOcr(lignes) {
  entrerModeBatch();  // remet batchLignes à zéro et affiche la liste
  const elTitre = document.getElementById('rec-batch-titre');
  if (elTitre) elTitre.textContent = 'Articles lus sur le bon de livraison';

  // Clé d'article : référence si présente, sinon désignation normalisée.
  const cartesParArticle = new Map();
  lignes.forEach(l => {
    const cle = (l.reference && l.reference.trim())
      ? `ref:${l.reference.trim().toLowerCase()}`
      : `des:${_normLibelle(l.designation)}`;

    if (!cartesParArticle.has(cle)) {
      creerCarteBatch({
        designation: l.designation || 'Article',
        code_article: l.reference || null,
        catalogue_fournisseur_id: null,
        quantite_commandee: l.quantite ?? null,
        unite: 'kg',
        dlc_type: null,
        _fournisseur_id:  fournisseursListe[0]?.id  || null,
        _fournisseur_nom: fournisseursListe[0]?.nom || null,
      });
      cartesParArticle.set(cle, batchLignes[batchLignes.length - 1]);
    }
    _appliquerOcrSurCarte(cartesParArticle.get(cle), l);
  });
}

// Cas AVEC commande : remplir les cartes existantes par appariement de libellé.
// Chaque ligne OCR rejoint la carte de commande la plus ressemblante (non déjà prise).
function prefillCartesExistantes(lignes) {
  const dispo = [...batchLignes];   // cartes pas encore appariées
  const orphelines = [];            // lignes OCR sans correspondance

  lignes.forEach(l => {
    // 1) Si une carte DÉJÀ appariée correspond à cet article (même article livré
    //    en plusieurs lots), on l'y rattache : _appliquerOcrSurCarte ajoute un lot.
    let deja = null, dejaScore = 0;
    batchLignes.forEach(etat => {
      if (dispo.includes(etat)) return;  // pas encore appariée → traité en 2)
      const s = _scoreLibelle(l.designation, etat.designation);
      if (s > dejaScore) { dejaScore = s; deja = etat; }
    });
    if (deja && dejaScore >= 0.5) {
      _appliquerOcrSurCarte(deja, l);
      return;
    }

    // 2) Sinon, on apparie à la meilleure carte encore disponible.
    let best = null, bestScore = 0, bestIdx = -1;
    dispo.forEach((etat, i) => {
      const s = _scoreLibelle(l.designation, etat.designation);
      if (s > bestScore) { bestScore = s; best = etat; bestIdx = i; }
    });
    if (best && bestScore >= 0.5) {   // appariement suffisamment sûr
      _appliquerOcrSurCarte(best, l);
      dispo.splice(bestIdx, 1);
    } else {
      orphelines.push(l);
    }
  });

  // Lignes OCR non rattachées à la commande : on les ajoute comme cartes en plus
  // (article livré non commandé, ou libellé trop différent). À vérifier par l'humain.
  orphelines.forEach(l => {
    creerCarteBatch({
      designation: l.designation || 'Article',
      code_article: l.reference || null,
      catalogue_fournisseur_id: null,
      quantite_commandee: l.quantite ?? null,
      unite: 'kg',
      dlc_type: null,
      _fournisseur_id:  fournisseursListe[0]?.id  || null,
      _fournisseur_nom: fournisseursListe[0]?.nom || null,
    });
    const etat = batchLignes[batchLignes.length - 1];
    etat.el.classList.add('rec-batch-ocr-suspect');
    _appliquerOcrSurCarte(etat, l);
  });
}

// ═══════════════════════════════════════════════════════════
//  MODE LISTE COMMANDE (étape 3 batch)
// ═══════════════════════════════════════════════════════════
const elBatchWrap   = document.getElementById('rec-batch-wrap');
const elBatchListe  = document.getElementById('rec-batch-liste');
const elBatchTpl    = document.getElementById('rec-batch-ligne-tpl');
const elFormProduit = document.getElementById('rec-form-produit');
const elListeAjoutee = document.getElementById('rec-produits-liste-ajoutee-wrap');

// Bascule l'étape 3 en mode liste commande (toutes les lignes d'un coup).
function entrerModeBatch() {
  modeBatch = true;
  batchLignes = [];
  if (elBatchListe) elBatchListe.innerHTML = '';
  if (elBatchWrap)  elBatchWrap.hidden = false;
  // Masquer le formulaire unitaire et la liste « produits ajoutés »
  if (elFormProduit)  elFormProduit.hidden = true;
  if (elListeAjoutee) elListeAjoutee.hidden = true;
  if (elBtnAjouter)   elBtnAjouter.hidden = true;

  commandeLignes.forEach(creerCarteBatch);
  majBtnTerminerBatch();
}

// Sort du mode batch (réception sans commande → formulaire unitaire classique).
function sortirModeBatch() {
  modeBatch = false;
  if (elBatchWrap)    elBatchWrap.hidden = true;
  if (elFormProduit)  elFormProduit.hidden = false;
  if (elListeAjoutee) elListeAjoutee.hidden = false;
  if (elBtnAjouter)   elBtnAjouter.hidden = false;
}

// Tente un rattachement souple vers un produit interne (bonus, non bloquant).
// Le catalogue achats est la source : si rien ne matche, on garde la désignation.
function resoudreProduit(designation) {
  const res = filtrerProduits(designation || '');
  return res.length === 1 ? res[0] : null;  // match seulement si non ambigu
}

// Crée une carte éditable pour une ligne de commande (article du catalogue achats).
function creerCarteBatch(ligneCmd) {
  const frag = elBatchTpl.content.cloneNode(true);
  const carte = frag.querySelector('.rec-batch-carte');

  const produit = resoudreProduit(ligneCmd.designation);  // peut rester null
  const dlcType = ligneCmd.dlc_type || null;

  // État local de la carte. L'article du catalogue achats fait foi : produit
  // interne facultatif (rattachement souple), designation = libellé commande.
  const etat = {
    el: carte,
    ligneCmd,
    produit,                       // null = pas de produit interne (OK, non bloquant)
    designation: ligneCmd.designation || ligneCmd.code_article || 'Article',
    dlcType,
    catalogueId: ligneCmd.catalogue_fournisseur_id || null,
    fournisseur: {
      id:  ligneCmd._fournisseur_id  || null,
      nom: (ligneCmd._fournisseur_nom || '').trim() || null,
    },
    lotInterne: false,
    recu: true,                    // true = reçu, false = non reçu (ligne ignorée)
    criteres:     { couleur: 1, consistance: 1, exsudat: 1, odeur: 1 },
    observations: { couleur: '', consistance: '', exsudat: '', odeur: '' },
  };
  batchLignes.push(etat);

  // En-tête : toujours le libellé de la commande (catalogue achats)
  const elNom  = carte.querySelector('.rec-batch-nom');
  const elCode = carte.querySelector('.rec-batch-code');
  elNom.textContent  = etat.designation;
  elCode.textContent = ligneCmd.code_article ? `Réf. ${ligneCmd.code_article}` : '';

  // Fournisseur de la ligne
  const elFourn = carte.querySelector('.rec-batch-fourn');
  if (elFourn) elFourn.textContent = etat.fournisseur.nom ? `🏪 ${etat.fournisseur.nom}` : '';

  // Toggle Reçu / Non reçu
  const btnRecuOui = carte.querySelector('.rec-batch-recu-oui');
  const btnRecuNon = carte.querySelector('.rec-batch-recu-non');
  const elChampsBatch = carte.querySelector('.rec-batch-champs');
  const elDetailToggle = carte.querySelector('.rec-batch-detail-toggle');

  function appliquerEtatRecu(recu) {
    etat.recu = recu;
    if (recu) {
      btnRecuOui.classList.add('ok-sel');
      btnRecuNon.classList.remove('nc-sel');
      btnRecuOui.setAttribute('aria-pressed', 'true');
      btnRecuNon.setAttribute('aria-pressed', 'false');
      if (elChampsBatch) { elChampsBatch.style.opacity = ''; elChampsBatch.style.pointerEvents = ''; }
      if (elDetailToggle) { elDetailToggle.style.opacity = ''; elDetailToggle.style.pointerEvents = ''; }
    } else {
      btnRecuNon.classList.add('nc-sel');
      btnRecuOui.classList.remove('ok-sel');
      btnRecuNon.setAttribute('aria-pressed', 'true');
      btnRecuOui.setAttribute('aria-pressed', 'false');
      if (elChampsBatch) { elChampsBatch.style.opacity = '0.35'; elChampsBatch.style.pointerEvents = 'none'; }
      if (elDetailToggle) { elDetailToggle.style.opacity = '0.35'; elDetailToggle.style.pointerEvents = 'none'; }
    }
    majBadgeCarte(etat);
  }

  btnRecuOui.addEventListener('click', () => appliquerEtatRecu(true));
  btnRecuNon.addEventListener('click', () => appliquerEtatRecu(false));

  // Bouton « Voir le bon de livraison » : retrouve la photo BL du bloc fournisseur
  // correspondant (prise à l'étape 2). Affiché seulement si une photo existe.
  const btnBl = carte.querySelector('.rec-batch-bl-btn');
  if (btnBl) {
    const blocFourn = fournisseursListe.find(f =>
      (etat.fournisseur.id  && f.id  === etat.fournisseur.id) ||
      (etat.fournisseur.nom && f.nom === etat.fournisseur.nom));
    const photos = blocFourn?.photos || [];
    if (photos.length) {
      btnBl.hidden = false;
      btnBl.addEventListener('click', () => ouvrirBlFlottant(photos[0].url, photos.map(p => p.url)));
    }
  }

  // Champ date selon dlc_type
  const dateLabel = carte.querySelector('.rec-batch-date-label');
  const dateChamp = carte.querySelector('.rec-batch-date-champ');
  if (dlcType === 'date_abattage') {
    dateLabel.textContent = "Date d'abattage";
  } else if (dlcType === 'no_dlc') {
    dateChamp.hidden = true;
  } else {
    dateLabel.textContent = 'DLC';
  }

  // Nb de colis reçus : pré-rempli avec la quantité commandée (quelle que soit l'unité).
  const elNbColis      = carte.querySelector('.rec-batch-nb-colis');
  const elNbColisLabel = carte.querySelector('.rec-batch-nb-colis-label');
  const uniteCmd = (ligneCmd.unite || '').trim();
  if (elNbColisLabel) {
    elNbColisLabel.textContent = ligneCmd.quantite_commandee != null && uniteCmd
      ? `Nb de colis reçus — commandé : ${ligneCmd.quantite_commandee} ${uniteCmd}`
      : 'Nb de colis reçus';
  }
  if (elNbColis && ligneCmd.quantite_commandee != null) {
    elNbColis.value = ligneCmd.quantite_commandee;
  }

  // Poids reçu : toujours en kg (poids réel pesé, le stock HACCP est en kg).
  const elPoids      = carte.querySelector('.rec-batch-poids');
  const elPoidsLabel = carte.querySelector('.rec-batch-poids-label');
  const uniteEstKg = /^kg$/i.test(uniteCmd) || uniteCmd === '';
  if (elPoidsLabel) {
    elPoidsLabel.textContent = 'Poids reçu (kg)';
  }
  if (uniteEstKg && ligneCmd.quantite_commandee != null) {
    elPoids.value = ligneCmd.quantite_commandee;
  }
  // Le poids étant obligatoire, on retire le marquage d'erreur dès la saisie.
  elPoids.addEventListener('input', () => elPoids.classList.remove('rec-champ-invalide'));

  // Lot interne
  const btnLotInterne = carte.querySelector('.rec-batch-lot-interne');
  const inpLot        = carte.querySelector('.rec-batch-lot');
  btnLotInterne.addEventListener('click', async () => {
    if (!receptionId) return;
    // Le BL doit être enregistré avant de générer un lot interne (préfixe du lot).
    if (!numeroBlValide) {
      if ((elNumeroBl.value || '').trim()) {
        const ok = await validerNumeroBl();
        if (!ok) return;
      } else {
        afficherHintBl('Saisir et valider le n° de BL avant de générer un lot interne.', true);
        elNumeroBl.focus();
        return;
      }
    }
    // Base du lot interne : réf. catalogue achats (code_article) en priorité.
    const code = etat.ligneCmd.code_article
      || (etat.produit && etat.produit.code_unique)
      || 'ART';
    btnLotInterne.disabled = true; btnLotInterne.textContent = '⏳';
    try {
      const data = await apiFetch(
        `/api/receptions/${receptionId}/lot-interne?code_article=${encodeURIComponent(code)}`);
      inpLot.value = data.lot_interne;
      inpLot.readOnly = true;
      inpLot.style.background = '#f0faf3';
      etat.lotInterne = true;
      // Un lot interne = un seul lot généré : on retire les lots supplémentaires.
      const contSupp = carte.querySelector('.rec-batch-lots-supp');
      if (contSupp) contSupp.innerHTML = '';
      majLotsSuppHintBatch(etat);
      const addBtn = carte.querySelector('.rec-batch-add-lot');
      if (addBtn) addBtn.hidden = true;
      majBadgeCarte(etat);
    } catch (e) {
      alert(`Erreur génération lot : ${e.message}`);
    } finally {
      btnLotInterne.disabled = false; btnLotInterne.textContent = 'Lot interne';
    }
  });
  inpLot.addEventListener('input', () => {
    if (etat.lotInterne) {
      etat.lotInterne = false; inpLot.readOnly = false; inpLot.style.background = '';
      // Le lot redevient un lot fournisseur saisi → on réautorise les lots multiples.
      const addBtn = carte.querySelector('.rec-batch-add-lot');
      if (addBtn) addBtn.hidden = false;
    }
    majBadgeCarte(etat);
  });
  carte.querySelector('.rec-batch-date').addEventListener('input', () => majBadgeCarte(etat));

  // N° de lot supplémentaires : permet plusieurs lots (DLC propre par lot) sur une
  // même carte. À la validation, 1 ligne de réception est créée par lot. Un lot
  // interne occupe le lot principal → on masque l'ajout de lots multiples.
  const elAddLotBatch = carte.querySelector('.rec-batch-add-lot');
  if (elAddLotBatch) {
    elAddLotBatch.addEventListener('click', () => ajouterChampLotSuppBatch(etat));
  }

  // Dépliant contrôle visuel
  const toggle = carte.querySelector('.rec-batch-detail-toggle');
  const detail = carte.querySelector('.rec-batch-detail');
  toggle.addEventListener('click', () => {
    const ouvert = detail.classList.toggle('ouvert');
    toggle.setAttribute('aria-expanded', ouvert ? 'true' : 'false');
  });

  // Critères visuels (réutilise le markup .rec-critere-row)
  const elCriteres = carte.querySelector('.rec-batch-criteres');
  const aide = textesAide[produit ? produit.espece : ''] || null;
  CRITERES.forEach(c => {
    const row = document.createElement('div');
    row.className = 'rec-critere-row';
    const labelAide = aide ? `Normal : ${aide[c].normal}` : '';
    row.innerHTML = `
      <div class="rec-critere-header">
        <span class="rec-critere-label">${c.charAt(0).toUpperCase() + c.slice(1)}</span>
        <span class="rec-critere-aide">${escHtml(labelAide)}</span>
      </div>
      <div class="rec-toggle-pair">
        <button type="button" class="rec-toggle-btn ok-sel" data-val="1" aria-pressed="true">✓ Conforme</button>
        <button type="button" class="rec-toggle-btn" data-val="0" aria-pressed="false">✗ NC</button>
      </div>
      <input type="text" class="rec-obs-input" placeholder="Observation ${c}…" hidden>`;
    const [btnOk, btnNc] = row.querySelectorAll('.rec-toggle-btn');
    const obs = row.querySelector('.rec-obs-input');
    btnOk.addEventListener('click', () => {
      etat.criteres[c] = 1;
      btnOk.classList.add('ok-sel'); btnNc.classList.remove('nc-sel');
      btnOk.setAttribute('aria-pressed', 'true'); btnNc.setAttribute('aria-pressed', 'false');
      obs.hidden = true;
      majBadgeCarte(etat);
    });
    btnNc.addEventListener('click', () => {
      etat.criteres[c] = 0;
      btnNc.classList.add('nc-sel'); btnOk.classList.remove('ok-sel');
      btnNc.setAttribute('aria-pressed', 'true'); btnOk.setAttribute('aria-pressed', 'false');
      obs.hidden = false;
      detail.classList.add('ouvert');
      toggle.setAttribute('aria-expanded', 'true');
      majBadgeCarte(etat);
    });
    obs.addEventListener('input', () => { etat.observations[c] = obs.value.trim(); });
    elCriteres.appendChild(row);
  });

  elBatchListe.appendChild(carte);
  majBadgeCarte(etat);
}

// Ajoute un champ « n° de lot + DLC » supplémentaire sur une carte batch.
// Mêmes critères/origine/poids que le lot principal ; seuls lot et DLC diffèrent.
// `valeur`/`dlcVal` permettent de pré-remplir (utilisé par l'OCR multi-lot).
function ajouterChampLotSuppBatch(etat, valeur = '', dlcVal = '') {
  const cont = etat.el.querySelector('.rec-batch-lots-supp');
  if (!cont) return;
  const row = document.createElement('div');
  row.className = 'rec-lot-supp-row rec-batch-lot-supp-row';
  row.style.cssText = 'margin-top:.5rem;padding-top:.5rem;border-top:1px dashed #e0d6c8;';

  const lotRow = document.createElement('div');
  lotRow.style.cssText = 'display:flex;gap:.5rem;align-items:center;';

  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'rec-input rec-batch-lot-supp-input';
  input.placeholder = 'ex : LOT-2026-002';
  input.autocomplete = 'off';
  input.setAttribute('aria-label', 'Numéro de lot fournisseur supplémentaire');
  input.value = valeur;
  input.style.flex = '1';
  input.addEventListener('input', () => majBadgeCarte(etat));

  const rm = document.createElement('button');
  rm.type = 'button';
  rm.className = 'rec-fourn-clear';
  rm.setAttribute('aria-label', 'Retirer ce n° de lot');
  rm.textContent = '✕';
  rm.style.flexShrink = '0';
  rm.addEventListener('click', () => {
    row.remove();
    majLotsSuppHintBatch(etat);
    majBadgeCarte(etat);
  });

  lotRow.appendChild(input);
  lotRow.appendChild(rm);

  const dlcRow = document.createElement('div');
  dlcRow.style.cssText = 'display:flex;gap:.5rem;align-items:center;margin-top:.3rem;';

  const dlcLabel = document.createElement('span');
  dlcLabel.className = 'rec-batch-lot-supp-dlc-label';
  dlcLabel.textContent = etat.dlcType === 'date_abattage' ? "Date d'abattage :" : 'DLC :';
  dlcLabel.style.cssText = 'font-size:.8rem;color:var(--color-offline);white-space:nowrap;flex-shrink:0;';

  const dlcInput = document.createElement('input');
  dlcInput.type = 'date';
  dlcInput.className = 'rec-input rec-batch-lot-supp-dlc';
  dlcInput.setAttribute('aria-label', etat.dlcType === 'date_abattage' ? "Date d'abattage pour ce lot" : 'DLC pour ce lot');
  dlcInput.value = dlcVal;
  dlcInput.style.flex = '1';
  // Le champ date est masqué pour les articles sans DLC (cohérent avec le lot principal).
  if (etat.dlcType === 'no_dlc') dlcRow.hidden = true;

  dlcRow.appendChild(dlcLabel);
  dlcRow.appendChild(dlcInput);

  row.appendChild(lotRow);
  row.appendChild(dlcRow);
  cont.appendChild(row);
  majLotsSuppHintBatch(etat);
  if (!valeur) input.focus();
}

// Lots supplémentaires saisis sur une carte batch : [{lot, dlc}] (lot non vide).
function lotsSuppValeursBatch(etat) {
  const cont = etat.el.querySelector('.rec-batch-lots-supp');
  if (!cont) return [];
  return [...cont.querySelectorAll('.rec-batch-lot-supp-row')].map(row => ({
    lot: (row.querySelector('.rec-batch-lot-supp-input')?.value || '').trim(),
    dlc: (row.querySelector('.rec-batch-lot-supp-dlc')?.value   || ''),
  })).filter(p => p.lot);
}

function majLotsSuppHintBatch(etat) {
  const cont = etat.el.querySelector('.rec-batch-lots-supp');
  const hint = etat.el.querySelector('.rec-batch-lots-supp-hint');
  if (hint) hint.hidden = !(cont && cont.children.length > 0);
}

// Recherche produit manuelle sur une carte (produit non résolu auto).
function initRechercheProduitCarte(carte, etat) {
  const inp  = carte.querySelector('.rec-batch-prod-search');
  const list = carte.querySelector('.rec-batch-prod-autocomplete');
  const afficher = (liste) => {
    list.innerHTML = '';
    if (!liste.length) { list.hidden = true; return; }
    liste.slice(0, 12).forEach(p => {
      const div = document.createElement('div');
      div.className = 'rec-autocomplete-item';
      div.textContent = `${p.nom}${p.code_unique ? ' · ' + p.code_unique : ''}`;
      div.addEventListener('click', () => {
        etat.produit = p;
        carte.querySelector('.rec-batch-nom').textContent  = p.nom;
        carte.querySelector('.rec-batch-code').textContent = p.code_unique || '';
        carte.querySelector('.rec-batch-resolve').hidden = true;
        majBadgeCarte(etat);
      });
      list.appendChild(div);
    });
    list.hidden = false;
  };
  inp.addEventListener('input', () => {
    const q = inp.value.trim();
    if (!q) { list.hidden = true; return; }
    afficher(filtrerProduits(q));
  });
  document.addEventListener('click', e => {
    if (!list.contains(e.target) && e.target !== inp) list.hidden = true;
  }, true);
}

// Met à jour le badge de statut d'une carte (non reçu / en attente / OK / NC).
function majBadgeCarte(etat) {
  const badge = etat.el.querySelector('.rec-batch-badge');
  etat.el.classList.remove('en-attente', 'nc', 'non-recu');

  if (!etat.recu) {
    etat.el.classList.add('non-recu');
    badge.className = 'rec-batch-badge non-recu';
    badge.textContent = '— Non reçu';
    return;
  }

  const inpLot = etat.el.querySelector('.rec-batch-lot');
  const inpDate = etat.el.querySelector('.rec-batch-date');
  const aLot  = etat.lotInterne || (inpLot.value.trim() !== '');
  const aDate = etat.dlcType === 'no_dlc' ? true : (inpDate.value.trim() !== '');
  const estNc = Object.values(etat.criteres).some(v => v === 0);

  if (estNc) {
    etat.el.classList.add('nc');
    badge.className = 'rec-batch-badge nc';
    badge.textContent = '✗ NC';
  } else if (aLot && aDate) {
    badge.className = 'rec-batch-badge ok';
    badge.textContent = '✓ Complet';
  } else {
    etat.el.classList.add('en-attente');
    badge.className = 'rec-batch-badge attente';
    badge.textContent = '⛔ En attente';
  }
}

function majBtnTerminerBatch() {
  if (!modeBatch) return;
  // En mode batch, « Récap → » est actif s'il y a au moins une ligne.
  elBtnTerminer.disabled = (batchLignes.length === 0);
}

// Liste finale des couples {lot, dlc} d'une carte batch (lot principal + lots
// supplémentaires), dédupliqués par n° de lot. 1 couple = 1 ligne de réception.
// On garde toujours au moins un couple (le principal, éventuellement vide pour
// un produit en attente).
function pairesLotsBatch(etat) {
  const lotPrincipal  = etat.el.querySelector('.rec-batch-lot').value.trim();
  const dlcPrincipale = etat.el.querySelector('.rec-batch-date').value;
  const seen = new Set();
  const paires = [{ lot: lotPrincipal, dlc: dlcPrincipale }];
  if (lotPrincipal) seen.add(lotPrincipal);
  // Un lot interne occupe le lot principal : pas de lots supplémentaires possibles.
  if (!etat.lotInterne) {
    for (const { lot, dlc } of lotsSuppValeursBatch(etat)) {
      if (!lot || seen.has(lot)) continue;
      seen.add(lot);
      paires.push({ lot, dlc: dlc || dlcPrincipale });
    }
  }
  return paires;
}

// Construit le payload d'une carte (même forme que _buildPayload unitaire).
// `paire` (optionnel) {lot, dlc} : si fourni, surcharge le lot et la DLC de base
// (cas multi-lot : 1 payload par couple lot/DLC).
function _buildPayloadBatch(etat, paire = null) {
  const payload = {
    couleur_conforme:     etat.criteres.couleur,
    consistance_conforme: etat.criteres.consistance,
    exsudat_conforme:     etat.criteres.exsudat,
    odeur_conforme:       etat.criteres.odeur,
    lot_interne:          etat.lotInterne ? 1 : 0,
    origine:              'France',
    // Article du catalogue achats : produit interne facultatif, libellé toujours envoyé.
    designation_libre:    etat.designation,
  };
  if (etat.produit)         payload.produit_id = etat.produit.id;
  if (etat.fournisseur.id)  payload.fournisseur_id  = etat.fournisseur.id;
  if (etat.fournisseur.nom) payload.fournisseur_nom = etat.fournisseur.nom;
  if (etat.catalogueId)     payload.catalogue_fournisseur_id = etat.catalogueId;
  if (etat.dlcType)         payload.dlc_type = etat.dlcType;

  const tempCamion = parseFloat(elTempCamion.value);
  if (!isNaN(tempCamion)) payload.temperature_reception = tempCamion;

  const lot = paire ? paire.lot : etat.el.querySelector('.rec-batch-lot').value.trim();
  if (lot) payload.numero_lot = lot;

  const dateVal = paire ? paire.dlc : etat.el.querySelector('.rec-batch-date').value;
  if (dateVal) {
    if (etat.dlcType === 'date_abattage') payload.date_abattage = dateVal;
    else                                  payload.dlc           = dateVal;
  }
  const poids = parseFloat(etat.el.querySelector('.rec-batch-poids').value);
  if (!isNaN(poids)) payload.poids_kg = poids;

  const nbColis = parseInt(etat.el.querySelector('.rec-batch-nb-colis')?.value, 10);
  if (!isNaN(nbColis) && nbColis > 0) payload.nb_colis = nbColis;

  // Observations sur critères NC
  CRITERES.forEach(c => {
    if (etat.criteres[c] === 0 && etat.observations[c]) {
      payload[`${c}_observation`] = etat.observations[c];
    }
  });
  const ph = parseFloat(etat.el.querySelector('.rec-batch-ph').value);
  if (!isNaN(ph)) payload.ph_valeur = ph;
  return payload;
}

// Valide toute la liste : POST chaque carte (sauf "Non reçu") puis passe au récap.
async function validerBatch() {
  // Seule garde : une DLC saisie ne doit pas être dans le passé (pas pour l'abattage).
  // Le produit interne n'est PAS requis (article catalogue achats = source).
  const today = new Date().toISOString().slice(0, 10);
  for (const etat of batchLignes) {
    if (!etat.recu) continue; // lignes "Non reçu" ignorées

    // Poids reçu obligatoire : on ne réceptionne pas une ligne sans poids pesé.
    const inpPoids = etat.el.querySelector('.rec-batch-poids');
    const poids = parseFloat(inpPoids.value);
    if (isNaN(poids) || poids <= 0) {
      inpPoids.classList.add('rec-champ-invalide');
      inpPoids.focus();
      etat.el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      alert('Le poids reçu (kg) est obligatoire et doit être supérieur à 0.');
      return;
    }

    // DLC dans le passé : on contrôle la DLC principale ET celles des lots supp.
    if (etat.dlcType !== 'date_abattage') {
      const dlcs = [
        { el: etat.el.querySelector('.rec-batch-date'), val: etat.el.querySelector('.rec-batch-date').value },
        ...[...etat.el.querySelectorAll('.rec-batch-lot-supp-dlc')].map(el => ({ el, val: el.value })),
      ];
      for (const { el, val } of dlcs) {
        if (val && val < today) {
          el.classList.add('rec-champ-invalide');
          etat.el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          alert('Une DLC est dans le passé.');
          return;
        }
      }
    }
  }

  const lignesRecues = batchLignes.filter(e => e.recu);
  if (lignesRecues.length === 0) {
    alert('Aucun produit marqué comme reçu. Veuillez indiquer au moins un produit reçu.');
    return;
  }

  elBtnTerminer.disabled = true;
  const txt = elBtnTerminer.textContent;
  elBtnTerminer.textContent = 'Enregistrement…';
  try {
    for (const etat of lignesRecues) {
      // Produit d'affichage : produit interne si rattaché, sinon désignation catalogue.
      const prodAffiche = etat.produit || { id: null, nom: etat.designation };
      // Plusieurs n° de lot → 1 ligne de réception par lot, chacune avec sa DLC.
      for (const paire of pairesLotsBatch(etat)) {
        const ligne = await apiFetch(`/api/receptions/${receptionId}/lignes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(_buildPayloadBatch(etat, paire)),
        });
        lignesAjoutees.push(_ligneToLocal(ligne, prodAffiche));
      }
    }
    majListeLignes();
    remplirRecap();
    initNcProcedure();
    allerEtape(4);
  } catch (err) {
    alert(`Erreur lors de l'enregistrement : ${err.message}`);
    elBtnTerminer.disabled = false;
    elBtnTerminer.textContent = txt;
  }
}

elBtnTerminer.addEventListener('click', () => {
  if (modeBatch) { validerBatch(); return; }
  if (lignesAjoutees.length === 0) return;
  remplirRecap();
  initNcProcedure();
  allerEtape(4);
});


// ── ÉTAPE 4 : Récap + Clôture ──────────────────────────────
function remplirRecap() {
  // Camion
  const tempCamion = parseFloat(elTempCamion.value);
  const infoTexte  = [];
  if (!isNaN(tempCamion)) infoTexte.push(`Température : ${tempCamion}°C`);
  infoTexte.push(`Propreté : ${propreteCamion === 'satisfaisant' ? 'Satisfaisante' : 'Non satisfaisante'}`);
  elRecapCamionInfo.innerHTML = infoTexte.join('<br>');

  // La température camion ne crée PAS de NC — seule la propreté compte
  const camionProprete = propreteCamion === 'satisfaisant';
  if (!camionProprete) {
    elRecapCamionBadge.className = 'rec-badge nc';
    elRecapCamionBadge.textContent = '✗ Propreté NC';
  } else {
    elRecapCamionBadge.className = 'rec-badge conforme';
    elRecapCamionBadge.textContent = '✓ Conforme';
  }

  // Conformité globale estimée (avant clôture serveur)
  // Une ligne NC initiale mais conforme après contrôle à cœur est considérée conforme
  const toutesConformes = lignesAjoutees.every(l => {
    if (l.conforme) return true;
    const coeur = ncCoeurResultats[l.id] || ncCoeurResultats[String(l.id)];
    return coeur && coeur.conforme_apres_coeur;
  });
  const globalOk = toutesConformes && camionProprete;
  elConformiteGlobale.className = 'rec-conformite-globale ' + (globalOk ? 'conforme' : 'nc');
  elConformiteGlobale.textContent = globalOk
    ? '✓ Tout conforme'
    : '✗ Présence de non-conformité(s)';

  // Liste produits
  elRecapLignes.innerHTML = '';
  lignesAjoutees.forEach(l => {
    const row = document.createElement('div');
    row.className = 'rec-recap-ligne-item';

    const left = document.createElement('div');
    const nom  = document.createElement('div');
    nom.className = 'rec-recap-ligne-nom';
    nom.textContent = l.produit_nom;
    const det = document.createElement('div');
    det.className = 'rec-recap-ligne-detail';
    const parts = [];
    if (l.fournisseur_nom) parts.push(l.fournisseur_nom);
    if (l.temperature_reception !== null && l.temperature_reception !== undefined) {
      parts.push(`${l.temperature_reception}°C`);
    }
    if (l.numero_lot) parts.push(`Lot${l.lot_interne ? ' interne' : ''} : ${l.numero_lot}`);
    if (l.origine) parts.push(`Origine : ${origineCode(l.origine)}`);
    det.textContent = parts.join(' · ');
    left.appendChild(nom);
    if (parts.length) left.appendChild(det);

    const coeurResult = ncCoeurResultats[l.id] || ncCoeurResultats[String(l.id)];
    const ligneConforme = l.conforme || (coeurResult && coeurResult.conforme_apres_coeur);
    const badge = document.createElement('span');
    badge.className = 'rec-ligne-badge ' + (ligneConforme ? 'ok' : 'nc');
    badge.textContent = ligneConforme ? '✓ OK' : '✗ NC';

    // Badge substitution
    if (l.substitution_article) {
      const sub = document.createElement('div');
      sub.style.cssText = 'font-size:.75rem;color:var(--hors-ligne);margin-top:.2rem;';
      sub.textContent = `↔ Substitution de : ${l.substitution_article}`;
      left.appendChild(sub);
    }

    row.appendChild(left);
    row.appendChild(badge);
    elRecapLignes.appendChild(row);
  });

  // Bloc "Créer commande" : visible seulement si aucune commande liée
  const aCommande = commandeIds.some(Boolean);
  if (elBlocCreerCommande) {
    elBlocCreerCommande.hidden = aCommande;
    if (elCreerCmdStatut) elCreerCmdStatut.hidden = true;
    if (elBtnCreerCommande) {
      elBtnCreerCommande.disabled = false;
      elBtnCreerCommande.textContent = '📋 Créer la commande associée';
    }
  }
}

// ── Création commande rétroactive ──────────────────────────
const elDialogCmdReview   = document.getElementById('rec-dialog-cmd-review');
const elCmdReviewListe    = document.getElementById('rec-cmd-review-liste');
const elCmdReviewErreur   = document.getElementById('rec-cmd-review-erreur');
const elCmdReviewValider  = document.getElementById('rec-cmd-review-valider');
const elCmdReviewAnnuler  = document.getElementById('rec-cmd-review-annuler');

// État interne du modal : une entrée par ligne réceptionnée
let cmdReviewLignes = []; // [{ligneLocal, catalogueArticle, qte, unite}]

function unitesDisponibles(art) {
  if (!art) return ['kg'];
  const csv = art.unites_autorisees;
  if (!csv || !csv.trim()) return ['kg'];
  return csv.split(',').map(s => s.trim()).filter(Boolean);
}

function labelUnite(u) {
  return u === 'piece' ? 'pièce' : u;
}

function construireLigneReview(entry, idx) {
  const { ligneLocal, catalogueArticle, qte, unite } = entry;
  const unites = unitesDisponibles(catalogueArticle);
  const uniqId = `cmd-rev-${idx}`;

  const wrap = document.createElement('div');
  wrap.style.cssText = 'border-bottom:1px solid #e5d9c8;padding:.65rem 0;display:flex;flex-direction:column;gap:.4rem;';

  const nom = document.createElement('div');
  nom.style.cssText = 'font-weight:600;font-size:.95rem;color:var(--noyer);';
  nom.textContent = ligneLocal.produit_nom;
  wrap.appendChild(nom);

  const row = document.createElement('div');
  row.style.cssText = 'display:flex;align-items:center;gap:8px;flex-wrap:wrap;';

  // Stepper − valeur +
  const btnMinus = document.createElement('button');
  btnMinus.type = 'button';
  btnMinus.className = 'ach-step-btn';
  btnMinus.textContent = '−';

  const inp = document.createElement('input');
  inp.type = 'number';
  inp.min = '0';
  inp.step = 'any';
  inp.inputMode = 'decimal';
  inp.value = qte || '';
  inp.placeholder = '0';
  inp.className = 'ach-qte-input';
  inp.style.cssText = 'width:70px;min-height:42px;text-align:center;border:1px solid #d6c3a8;border-radius:6px;font-size:1rem;padding:4px 6px;';

  const btnPlus = document.createElement('button');
  btnPlus.type = 'button';
  btnPlus.className = 'ach-step-btn';
  btnPlus.textContent = '+';

  const step = unite === 'kg' ? 0.5 : 1;
  btnMinus.addEventListener('click', () => {
    const v = parseFloat(inp.value) || 0;
    const s = cmdReviewLignes[idx].unite === 'kg' ? 0.5 : 1;
    inp.value = Math.max(0, +(v - s).toFixed(3));
    cmdReviewLignes[idx].qte = parseFloat(inp.value);
    btnMinus.disabled = parseFloat(inp.value) <= 0;
  });
  btnPlus.addEventListener('click', () => {
    const v = parseFloat(inp.value) || 0;
    const s = cmdReviewLignes[idx].unite === 'kg' ? 0.5 : 1;
    inp.value = +(v + s).toFixed(3);
    cmdReviewLignes[idx].qte = parseFloat(inp.value);
    btnMinus.disabled = false;
  });
  inp.addEventListener('input', () => {
    cmdReviewLignes[idx].qte = parseFloat(inp.value) || 0;
    btnMinus.disabled = (cmdReviewLignes[idx].qte <= 0);
  });
  btnMinus.disabled = (qte <= 0);

  row.appendChild(btnMinus);
  row.appendChild(inp);
  row.appendChild(btnPlus);

  // Boutons unité (seulement si plusieurs disponibles)
  if (unites.length > 1) {
    const grp = document.createElement('div');
    grp.className = 'ach-unite-btns';
    unites.forEach(u => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ach-unite-btn' + (u === unite ? ' is-active' : '');
      btn.textContent = labelUnite(u);
      btn.addEventListener('click', () => {
        cmdReviewLignes[idx].unite = u;
        grp.querySelectorAll('.ach-unite-btn').forEach(b => b.classList.remove('is-active'));
        btn.classList.add('is-active');
        // Adapter le step du stepper à l'unité
        const newStep = u === 'kg' ? 0.5 : 1;
        // Rien de plus à faire, les closures lisent cmdReviewLignes[idx].unite à chaque clic
      });
      grp.appendChild(btn);
    });
    row.appendChild(grp);
  } else {
    const lbl = document.createElement('span');
    lbl.style.cssText = 'font-size:.9rem;color:var(--color-offline);';
    lbl.textContent = labelUnite(unites[0] || 'kg');
    row.appendChild(lbl);
  }

  wrap.appendChild(row);
  return wrap;
}

function ouvrirModalCmdReview() {
  const fourn = fournisseursListe[0];
  if (!fourn || !fourn.id) {
    if (elCreerCmdStatut) {
      elCreerCmdStatut.textContent = '⚠️ Le fournisseur doit être enregistré dans la base pour créer une commande.';
      elCreerCmdStatut.style.color = 'var(--hors-ligne)';
      elCreerCmdStatut.hidden = false;
    }
    return;
  }

  // Construire l'état à partir des lignes réceptionnées + données catalogue
  cmdReviewLignes = lignesAjoutees.map(l => {
    const art = l.catalogue_id ? catalogueBl.find(a => a.id === l.catalogue_id) : null;
    const unites = unitesDisponibles(art);
    // Unité par défaut : format_prix du catalogue si dispo, sinon première unité autorisée
    const uniteDefaut = (art && art.format_prix) ? art.format_prix : (unites[0] || 'kg');
    return {
      ligneLocal: l,
      catalogueArticle: art || null,
      qte: l.poids_kg || 1,
      unite: uniteDefaut,
    };
  });

  // Remplir le modal
  elCmdReviewListe.innerHTML = '';
  cmdReviewLignes.forEach((entry, idx) => {
    elCmdReviewListe.appendChild(construireLigneReview(entry, idx));
  });
  if (elCmdReviewErreur) elCmdReviewErreur.hidden = true;
  elCmdReviewValider.disabled = false;
  elCmdReviewValider.textContent = 'Créer la commande';
  elDialogCmdReview.hidden = false;
}

if (elBtnCreerCommande) {
  elBtnCreerCommande.addEventListener('click', ouvrirModalCmdReview);
}

if (elCmdReviewAnnuler) {
  elCmdReviewAnnuler.addEventListener('click', () => {
    elDialogCmdReview.hidden = true;
  });
}

if (elCmdReviewValider) {
  elCmdReviewValider.addEventListener('click', async () => {
    elCmdReviewValider.disabled = true;
    elCmdReviewValider.textContent = 'Création…';
    if (elCmdReviewErreur) elCmdReviewErreur.hidden = true;

    try {
      const lignes = cmdReviewLignes.map(e => ({
        designation:              e.ligneLocal.produit_nom,
        catalogue_fournisseur_id: e.ligneLocal.catalogue_id || null,
        code_article:             (e.catalogueArticle && e.catalogueArticle.code_article) || '',
        prix_unitaire_ht:         (e.catalogueArticle && e.catalogueArticle.prix_achat_ht) || 0,
        quantite_commandee:       e.qte || 1,
        unite:                    e.unite || 'kg',
        commentaire_ligne:        null,
      }));

      const fourn = fournisseursListe[0];
      const dateRecep = elDateReception.value || new Date().toISOString().slice(0, 10);
      const cmd = await apiFetch('/api/achats/commandes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fournisseur_id:        fourn.id,
          date_commande:         dateRecep,
          date_livraison_prevue: dateRecep,
          commentaire:           `Créée depuis la réception du ${dateRecep} (saisie rétroactive)`,
          personnel_id:          personnelId || null,
          lignes,
        }),
      });

      await apiFetch(`/api/achats/commandes/${cmd.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ statut: 'confirmee' }),
      });

      elDialogCmdReview.hidden = true;
      if (elBtnCreerCommande) elBtnCreerCommande.textContent = '✓ Commande créée';
      if (elCreerCmdStatut) {
        elCreerCmdStatut.textContent = `Commande ${cmd.numero_commande} créée — visible dans le module Commandes.`;
        elCreerCmdStatut.style.color = 'var(--conforme)';
        elCreerCmdStatut.hidden = false;
      }
    } catch (err) {
      elCmdReviewValider.disabled = false;
      elCmdReviewValider.textContent = 'Créer la commande';
      if (elCmdReviewErreur) {
        elCmdReviewErreur.textContent = `Erreur : ${err.message}`;
        elCmdReviewErreur.hidden = false;
      }
    }
  });
}

// ── PROCÉDURE NC ───────────────────────────────────────────

function initNcProcedure() {
  ncProduitsInitiaux = lignesAjoutees.filter(l => !l.conforme);
  ncProduits         = [...ncProduitsInitiaux];
  ncCoeurResultats   = {};
  livreurPresent     = null;
  ncFicheIndex       = 0;

  const aNc = ncProduitsInitiaux.length > 0;
  elNcProcedure.hidden = !aNc;
  elBtnCloturer.disabled = aNc;

  if (!aNc) return;

  // Réinitialiser les sous-étapes
  elNcStepA.hidden = false;
  elNcStepB.hidden = true;
  elNcBtnASuivant.disabled = true;
  elNcBtnBSuivant.disabled = true;
  if (elNcTousConformes) elNcTousConformes.hidden = true;
  elLivreurOui.className = 'rec-livreur-btn';
  elLivreurNon.className = 'rec-livreur-btn';

  // Construire la liste des contrôles à cœur
  elNcProduitsCoeur.innerHTML = '';
  ncProduitsInitiaux.forEach(l => {
    const produit = tousProduits.find(p => p.id === l.produit_id);
    const intervalle = produit ? parseIntervalleTemp(produit.temperature_conservation) : null;
    const tempMax = intervalle ? intervalle.max : null;

    const row = document.createElement('div');
    row.className = 'rec-nc-coeur-row';
    row.dataset.ligneId = l.id;

    const nomEl = document.createElement('div');
    nomEl.className = 'rec-nc-produit-nom';
    nomEl.textContent = l.produit_nom;
    row.appendChild(nomEl);

    const fourn = tousFournisseurs.find(f => f.id === (l.fournisseur_id || fournisseurId));
    if (fourn) {
      const fournEl = document.createElement('div');
      fournEl.className = 'rec-nc-fourn-nom';
      fournEl.textContent = `Fournisseur : ${fourn.nom}`;
      row.appendChild(fournEl);
    }

    const motifEl = document.createElement('div');
    motifEl.className = 'rec-nc-motif';

    const motifTitre = document.createElement('div');
    motifTitre.textContent = `✗ NC : ${l.motifs.join(', ') || 'non-conformité'}`;
    motifEl.appendChild(motifTitre);

    const infoLignes = [];
    if (l.temperature_reception != null) {
      infoLignes.push(`Temp. camion : ${l.temperature_reception}°C`);
    }
    if (produit && produit.temperature_conservation) {
      infoLignes.push(`Cible : ${produit.temperature_conservation}`);
    }
    if (tempMax !== null) {
      infoLignes.push(`Tolérance max : +${tempMax + 1}°C`);
    }
    if (infoLignes.length) {
      const infoEl = document.createElement('div');
      infoEl.className = 'rec-nc-motif-info';
      infoEl.textContent = infoLignes.join(' — ');
      motifEl.appendChild(infoEl);
    }
    row.appendChild(motifEl);

    const wrap = document.createElement('div');
    wrap.className = 'rec-nc-coeur-wrap';

    const label = document.createElement('label');
    label.style.cssText = 'font-size:.85rem;font-weight:600;color:var(--color-text)';
    label.textContent = 'Temp. à cœur (°C) :';

    const input = document.createElement('input');
    input.type = 'number';
    input.inputMode = 'decimal';
    input.step = '0.1';
    input.className = 'rec-nc-coeur-input';
    input.placeholder = 'ex : 3.5';

    const badge = document.createElement('span');
    badge.className = 'rec-nc-coeur-badge';

    input.addEventListener('input', () => {
      const val = parseFloat(input.value);
      if (isNaN(val) || tempMax === null) {
        badge.textContent = '';
        badge.className = 'rec-nc-coeur-badge';
      } else {
        // Seuil à cœur : conforme si T°cœur <= borne_max + 1°C (même tolérance que camion)
        const conforme = val <= (tempMax + 1);
        badge.textContent = conforme ? '✓ Conforme après contrôle' : '✗ Non conforme confirmé';
        badge.className = 'rec-nc-coeur-badge ' + (conforme ? 'ok' : 'nc');
        ncCoeurResultats[l.id] = { temp_coeur: val, conforme_apres_coeur: conforme };
      }
      majEtatCoeur();
    });

    wrap.appendChild(label);
    wrap.appendChild(input);
    wrap.appendChild(badge);
    row.appendChild(wrap);
    elNcProduitsCoeur.appendChild(row);
  });
}

function majEtatCoeur() {
  // Tous renseignés ?
  const tousRenseignes = ncProduitsInitiaux.every(l => l.id in ncCoeurResultats);
  if (!tousRenseignes) {
    elNcBtnASuivant.disabled = true;
    if (elNcTousConformes) elNcTousConformes.hidden = true;
    return;
  }

  // Recalculer ncProduits = ceux qui restent NC après coeur
  ncProduits = ncProduitsInitiaux.filter(l => {
    const r = ncCoeurResultats[l.id];
    return !r || !r.conforme_apres_coeur;
  });

  const tousConformes = ncProduits.length === 0;
  if (elNcTousConformes) elNcTousConformes.hidden = !tousConformes;

  // Mettre à jour le récap pour refléter les résultats du contrôle à cœur
  remplirRecap();

  elNcBtnASuivant.disabled = false;
  // Si tous conformes après coeur → débloquer clôture directement
  if (tousConformes) {
    elNcBtnASuivant.textContent = 'Clôturer →';
  } else {
    elNcBtnASuivant.textContent = 'Suivant →';
  }
}

// Sous-étape A → B (ou clôture directe si tous conformes)
elNcBtnASuivant.addEventListener('click', () => {
  if (ncProduits.length === 0) {
    // Tous conformes après contrôle à cœur → débloquer clôture
    elNcProcedure.hidden = true;
    if (elPcrDoneBadge) {
      elPcrDoneBadge.textContent = '✓ Tous les produits conformes après contrôle à cœur';
      elPcrDoneBadge.hidden = false;
    }
    elBtnCloturer.disabled = false;
    return;
  }
  elNcStepA.hidden = true;
  elNcStepB.hidden = false;
});

// Livreur présent / absent
elLivreurOui.addEventListener('click', () => {
  livreurPresent = true;
  elLivreurOui.className = 'rec-livreur-btn sel-oui';
  elLivreurNon.className = 'rec-livreur-btn';
  elNcBtnBSuivant.disabled = false;
});

elLivreurNon.addEventListener('click', () => {
  livreurPresent = false;
  elLivreurNon.className = 'rec-livreur-btn sel-non';
  elLivreurOui.className = 'rec-livreur-btn';
  elNcBtnBSuivant.disabled = false;
});

// Sous-étape B → PCR01 (écran dédié)
elNcBtnBSuivant.addEventListener('click', () => {
  // Sauvegarder l'état complet du wizard pour le restaurer au retour
  const recState = {
    receptionId,
    personnelId,
    personnelPrenom,
    fournisseurId,
    lignesAjoutees,
    tempCamion:    parseFloat(elTempCamion.value) || null,
    propreteCamion,
  };
  sessionStorage.setItem('haccp_rec_state', JSON.stringify(recState));

  // Données spécifiques à la procédure PCR01
  const pcrData = {
    receptionId,
    personnelPrenom,
    fournisseurId,
    livreurPresent,
    ncProduits,          // produits NC confirmés (après contrôle à cœur)
    ncCoeurResultats,    // {ligne_id: {temp_coeur, conforme_apres_coeur}}
    ncFicheIndex: 0,
    tempCamion: parseFloat(elTempCamion.value) || null,
    heureReception: elHeure.value,
  };
  sessionStorage.setItem('haccp_pcr01_data', JSON.stringify(pcrData));
  sessionStorage.removeItem('haccp_pcr01_signature'); // sera capturée dans pcr01.html

  window.location.href = '/pcr01.html';
});

// chargerFichePcr / enregistrerFichePcr → déplacés dans pcr01.js (écran dédié)

// ── Clôture ─────────────────────────────────────────────────
elBtnCloturer.addEventListener('click', cloturerFiche);

async function cloturerFiche() {
  elErreur4.hidden = true;
  elBtnCloturer.disabled = true;
  elBtnCloturer.textContent = 'Clôture…';

  // Lignes dont le contrôle à cœur a été conforme → remettre conforme = 1 en DB
  const coeurConformes = Object.entries(ncCoeurResultats)
    .filter(([, r]) => r.conforme_apres_coeur)
    .map(([id]) => parseInt(id, 10))
    .filter(id => !isNaN(id));

  const coeurTemperatures = {};
  for (const [id, r] of Object.entries(ncCoeurResultats)) {
    if (r.temp_coeur !== null && r.temp_coeur !== undefined) {
      coeurTemperatures[parseInt(id, 10)] = r.temp_coeur;
    }
  }

  const payload = {
    commentaire_nc: elCommentaireNc.value.trim() || null,
    coeur_conformes: coeurConformes,
    coeur_temperatures: coeurTemperatures,
  };

  try {
    const rec = await apiFetch(`/api/receptions/${receptionId}/cloturer`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const conf = rec.conformite_globale === 'conforme';
    elConfirmDetail.textContent = `${lignesAjoutees.length} produit(s) — par ${personnelPrenom}`;
    elConfirmBadge.className   = 'rec-confirm-badge ' + (conf ? 'conforme' : 'nc');
    elConfirmBadge.textContent = conf ? '✓ Conformité globale : OK' : '✗ Non-conformité(s) détectée(s)';

    allerEtape(5);
    demarrerCompteurConfirmation();

  } catch (err) {
    elErreur4.textContent = `Erreur : ${err.message}`;
    elErreur4.hidden = false;
  } finally {
    elBtnCloturer.disabled = false;
    elBtnCloturer.textContent = '✔ Clôturer la fiche';
  }
}


// ── CONFIRMATION ───────────────────────────────────────────
function demarrerCompteurConfirmation() {
  clearInterval(timerConfirmation);
  elConfirmCountdown.textContent = '';
}

elBtnHub.addEventListener('click', () => {
  clearInterval(timerConfirmation);
  window.location.href = '/hub.html';
});


// ── Restauration état après retour depuis pcr01.html ────────
//
// Si l'opérateur revient de pcr01.html (avec ou sans validation),
// on restaure le wizard à l'étape 4 depuis sessionStorage.
//
function restaurerDepuisPcr01() {
  const recStateRaw = sessionStorage.getItem('haccp_rec_state');
  if (!recStateRaw) return false;

  const pcrDone = sessionStorage.getItem('haccp_pcr01_done') === '1';

  try {
    const state = JSON.parse(recStateRaw);

    // Restaurer l'état mémoire
    receptionId     = state.receptionId;
    personnelId     = state.personnelId;
    personnelPrenom = state.personnelPrenom;
    fournisseurId   = state.fournisseurId;
    lignesAjoutees  = state.lignesAjoutees || [];
    propreteCamion  = state.propreteCamion || 'satisfaisant';

    // Restaurer les inputs DOM nécessaires à remplirRecap()
    if (state.tempCamion !== null && state.tempCamion !== undefined) {
      elTempCamion.value = state.tempCamion;
      dernierTempCamionEnvoye = state.tempCamion;
    }

    // Restaurer ncCoeurResultats depuis les données pcr01 (pour la clôture)
    const pcrDataRaw = sessionStorage.getItem('haccp_pcr01_data');
    if (pcrDataRaw) {
      try {
        const pcrData = JSON.parse(pcrDataRaw);
        if (pcrData.ncCoeurResultats) ncCoeurResultats = pcrData.ncCoeurResultats;
      } catch (_) { /* ignore */ }
    }

    // Nettoyage sessionStorage
    sessionStorage.removeItem('haccp_rec_state');
    sessionStorage.removeItem('haccp_pcr01_data');
    sessionStorage.removeItem('haccp_pcr01_done');
    sessionStorage.removeItem('haccp_pcr01_signature');

    // Reconstruire le récap
    remplirRecap();

    if (pcrDone) {
      // PCR01 validé → masquer la procédure NC, afficher le badge, débloquer clôture
      ncProduitsInitiaux = lignesAjoutees.filter(l => !l.conforme);
      ncProduits = [];
      elNcProcedure.hidden = true;
      if (elPcrDoneBadge) elPcrDoneBadge.hidden = false;
      elBtnCloturer.disabled = false;
    } else {
      // Retour sans validation (← Retour sur pcr01) → reprendre depuis étape A
      initNcProcedure();
    }

    allerEtape(4);
    return true;
  } catch (e) {
    console.error('[haccp] Restauration échouée :', e);
    // Nettoyer pour éviter une boucle
    sessionStorage.removeItem('haccp_rec_state');
    sessionStorage.removeItem('haccp_pcr01_data');
    sessionStorage.removeItem('haccp_pcr01_done');
    sessionStorage.removeItem('haccp_pcr01_signature');
    return false;
  }
}


// ── Dropdown Origine (pays UE) ─────────────────────────────
function _afficherSuggestionsOrigine(filtreTxt) {
  if (!elOrigineList) return;
  const norm = s => String(s || '').trim().toLowerCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '');
  const filtre = norm(filtreTxt);
  const filtreUp = String(filtreTxt || '').trim().toUpperCase();
  const pays = typeof PAYS_UE !== 'undefined' ? PAYS_UE : ['France'];
  const liste = pays.filter(p => {
    if (!filtre) return true;
    if (norm(p).includes(filtre)) return true;
    const code = (typeof origineCode === 'function') ? origineCode(p) : '';
    return filtreUp.length >= 1 && code.startsWith(filtreUp);
  });
  if (!liste.length) {
    elOrigineList.hidden = true;
    return;
  }
  elOrigineList.innerHTML = liste.map(p => {
    const code = (typeof origineCode === 'function') ? origineCode(p) : '';
    return `<div class="rec-autocomplete-item" role="option" data-pays="${p}">
      <span style="font-weight:600;">${p}</span>
      ${code ? `<span style="color:var(--hors-ligne);margin-left:.5rem;">${code}</span>` : ''}
    </div>`;
  }).join('');
  elOrigineList.hidden = false;
}

if (elOrigine) {
  elOrigine.addEventListener('input', () => {
    _afficherSuggestionsOrigine(elOrigine.value);
  });
  elOrigine.addEventListener('blur', () => {
    // Laisser le temps au clic sur l'item de se propager
    setTimeout(() => { if (elOrigineList) elOrigineList.hidden = true; }, 150);
  });
}
if (elOrigineToggle) {
  elOrigineToggle.addEventListener('mousedown', e => e.preventDefault());
  elOrigineToggle.addEventListener('click', (e) => {
    e.preventDefault();
    if (!elOrigineList) return;
    if (elOrigineList.hidden) {
      _afficherSuggestionsOrigine('');
      elOrigine && elOrigine.focus();
    } else {
      elOrigineList.hidden = true;
    }
  });
}
if (elOrigineList) {
  elOrigineList.addEventListener('mousedown', (e) => {
    const item = e.target.closest('[data-pays]');
    if (!item) return;
    e.preventDefault();
    if (elOrigine) elOrigine.value = item.dataset.pays;
    elOrigineList.hidden = true;
  });
}

// ── Initialisation ─────────────────────────────────────────
async function init() {
  // Pré-remplir date réception à aujourd'hui
  if (elDateReception && !elDateReception.value) {
    elDateReception.value = new Date().toISOString().slice(0, 10);
  }

  // Charger les référentiels en parallèle — toujours nécessaires, y compris
  // en cas de restauration depuis pcr01.html (initNcProcedure utilise
  // tousProduits / tousFournisseurs pour calculer les seuils à cœur).
  await Promise.all([
    chargerPersonnel(),
    chargerFournisseurs(),
    chargerProduits(),
    chargerTextesAide(),
  ]);

  // Vérifier si retour depuis pcr01.html
  if (restaurerDepuisPcr01()) return;

  reinitCriteres();

  // Proposer de reprendre/abandonner une réception laissée 'en_cours'
  // (fiche créée puis quittée sans clôture).
  await detecterReceptionEnCours();
}

init();

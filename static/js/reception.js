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
const elBtnPasLot         = document.getElementById('rec-btn-pas-lot');
const elBtnAnnulerLot     = document.getElementById('rec-btn-annuler-lot');
const elLotGenere         = document.getElementById('rec-lot-genere');
const elLotsSupp          = document.getElementById('rec-lots-supp');
const elBtnAddLot         = document.getElementById('rec-btn-add-lot');
const elLotsSuppHint      = document.getElementById('rec-lots-supp-hint');
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
let ligneEnEdition     = null;    // {id, index} — null = mode ajout
let fournisseurProduitSelected = null; // {id, nom} fournisseur sélectionné pour le produit courant
let dernierFournisseurProduit = null; // {id, nom} dernier fournisseur utilisé pour dialog

// Lien commande
let commandeIds        = [];      // IDs des commandes liées (tableau)
let commandeLignes     = [];      // lignes de toutes les commandes liées pour pré-remplissage
let commandeLigneIdx   = 0;       // index de la ligne en cours de réception
let catalogueIdPrefill = null;    // catalogue_fournisseur_id de la ligne de commande pré-remplie
                                  // (propagé vers reception_lignes pour le suivi de stock par référence)
let dlcTypePrefill     = null;    // dlc_type du catalogue ('dlc'|'date_abattage'|'no_dlc')
let toutesCommandes    = [];      // cache de toutes les commandes disponibles


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
    const cmds = await apiFetch('/api/achats/commandes?statut=confirmee&limit=50');
    const brouillons = await apiFetch('/api/achats/commandes?statut=brouillon&limit=50');
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
  if (idx === 0) fournisseurId = fourn.id;

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
    } else {
      window.location.href = '/hub.html';
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
        // Initialiser date + heure à maintenant
        const now = new Date();
        elHeure.value = now.toTimeString().slice(0, 5);
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
        if (idx === 0) fournisseurId = f.id;
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
    if (idx === 0) fournisseurId = null;
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

    const rec = await apiFetch('/api/receptions', {
      method: 'POST',
      body: fd,
    });
    receptionId = rec.id;
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
    nom.textContent = p.nom;
    const code = document.createElement('span');
    code.className = 'rec-autocomplete-code';
    code.textContent = p.code_unique || '';
    div.appendChild(nom);
    div.appendChild(code);
    div.addEventListener('click', () => selectionnerProduit(p));
    elProdAutoComplete.appendChild(div);
  });
  elProdAutoComplete.hidden = false;
}

function selectionnerProduit(p) {
  produitSelectionne = p;
  elProdSelNom.textContent  = p.nom;
  elProdSelCode.textContent = p.code_unique || '';
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
  afficherAutoComplete(tousProduits.slice(0, 50));
  elProdSearch.focus();
  majBtnAjouter();
});

elProdSearch.addEventListener('input', () => {
  const q = elProdSearch.value.trim();
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    afficherAutoComplete(filtrerProduits(q));
  }, 180);
});
elProdSearch.addEventListener('focus', () => {
  if (!produitSelectionne) {
    afficherAutoComplete(filtrerProduits(elProdSearch.value));
  }
});
document.addEventListener('click', e => {
  if (!elProdAutoComplete.contains(e.target) && e.target !== elProdSearch) {
    elProdAutoComplete.hidden = true;
  }
}, true);

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

// Clic « Pas de N° de lot » → afficher le choix (au lieu de générer directement)
elBtnPasLot.addEventListener('click', () => {
  if (!produitSelectionne || !receptionId) return;
  if (elLotChoix) elLotChoix.hidden = !elLotChoix.hidden;
});

// Option 1 : générer un lot interne (le produit entre en stock normalement)
if (elLotChoixInterne) {
  elLotChoixInterne.addEventListener('click', async () => {
    if (!produitSelectionne || !receptionId) return;
    elLotChoixInterne.disabled = true;
    elLotChoixInterne.textContent = '⏳…';
    try {
      const code = produitSelectionne.code_unique;
      const data = await apiFetch(
        `/api/receptions/${receptionId}/lot-interne?code_unique=${encodeURIComponent(code)}`
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

// ── N° de lot supplémentaires ──────────────────────────────
// Permet de saisir plusieurs n° de lot pour un même produit. À l'ajout, une
// ligne de réception distincte est créée par lot (mêmes critères/DLC/origine).
// Désactivé quand le lot est interne ou « en attente » (pas de lot fournisseur).
function ajouterChampLotSupp(valeur = '') {
  if (!elLotsSupp) return;
  const row = document.createElement('div');
  row.className = 'rec-lot-supp-row';
  row.style.cssText = 'display:flex;gap:.5rem;align-items:center;margin-top:.5rem;';

  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'rec-input rec-lot-input rec-lot-supp-input';
  input.placeholder = 'ex : LOT-2026-002';
  input.autocomplete = 'off';
  input.setAttribute('aria-label', 'Numéro de lot fournisseur supplémentaire');
  input.value = valeur;
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

  row.appendChild(input);
  row.appendChild(rm);
  elLotsSupp.appendChild(row);
  majLotsSuppHint();
  input.focus();
}

// Lots supplémentaires saisis (valeurs non vides, dédupliquées avec le lot principal)
function lotsSuppValeurs() {
  if (!elLotsSupp) return [];
  return [...elLotsSupp.querySelectorAll('.rec-lot-supp-input')]
    .map(i => i.value.trim())
    .filter(Boolean);
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
  catalogueIdPrefill = null;   // réf catalogue valable seulement pour la ligne pré-remplie
  dlcTypePrefill     = null;

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
}

function chargerLigneEnEdition(l, idx) {
  ligneEnEdition = { id: l.id, index: idx };

  // Restaurer le produit
  const produit = tousProduits.find(p => p.id === l.produit_id);
  if (produit) selectionnerProduit(produit);

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
  const payload = {
    produit_id: produitSelectionne.id,
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
  // Référence catalogue issue de la commande (suivi du stock par référence)
  if (catalogueIdPrefill) payload.catalogue_fournisseur_id = catalogueIdPrefill;
  // Type de DLC catalogue → détermine l'exigence de traçabilité (statut en attente)
  if (dlcTypePrefill) payload.dlc_type = dlcTypePrefill;
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

  return {
    id:                  ligne.id,
    produit_id:          produit.id,
    produit_nom:         produit.nom,
    fournisseur_id:      fournId,
    fournisseur_nom:     fournNom,
    conforme:            ligne.conforme,
    temperature_reception: ligne.temperature_reception,
    numero_lot:          ligne.numero_lot,
    lot_interne:         ligne.lot_interne,
    origine:             ligne.origine || 'France',
    dlc:                 ligne.dlc,
    dluo:                ligne.dluo,
    statut:              ligne.statut || 'complet',
    attente_motif:       ligne.attente_motif || null,
    motifs:              motifsNc,
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

  // Plusieurs n° de lot → 1 ligne de réception par lot (mêmes critères/DLC/origine).
  // Le payload de base porte le lot principal ; on l'écrase par chaque lot.
  const payloadBase = _buildPayload();
  const lotPrincipal = (elLot.value || '').trim();
  const lotsSupp = lotsSuppValeurs();
  // Liste finale des lots, dédupliquée en préservant l'ordre.
  let lots = [lotPrincipal, ...lotsSupp].filter(Boolean);
  lots = [...new Set(lots)];
  // Si aucun lot saisi (produit en attente), on crée tout de même 1 ligne.
  if (lots.length === 0) lots = [null];

  elBtnAjouter.disabled = true;
  elBtnAjouter.textContent = lots.length > 1 ? `Ajout (0/${lots.length})…` : 'Ajout…';

  try {
    for (let i = 0; i < lots.length; i++) {
      const lot = lots[i];
      const payload = { ...payloadBase };
      if (lot) payload.numero_lot = lot;
      else     delete payload.numero_lot;

      const ligne = await apiFetch(`/api/receptions/${receptionId}/lignes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      lignesAjoutees.push(_ligneToLocal(ligne, produitSelectionne));
      if (lots.length > 1) {
        elBtnAjouter.textContent = `Ajout (${i + 1}/${lots.length})…`;
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

  // Poids reçu : toujours en kg (poids réel pesé, le stock HACCP est en kg).
  // L'unité de commande (colis, pièce…) n'est qu'un repère affiché dans le label.
  // On ne pré-remplit le poids que si la commande est déjà en kg.
  const elPoids      = carte.querySelector('.rec-batch-poids');
  const elPoidsLabel = carte.querySelector('.rec-batch-poids-label');
  const uniteCmd = (ligneCmd.unite || '').trim();
  const uniteEstKg = /^kg$/i.test(uniteCmd) || uniteCmd === '';
  if (elPoidsLabel) {
    if (ligneCmd.quantite_commandee != null && uniteCmd) {
      elPoidsLabel.textContent =
        `Poids reçu (kg) — commandé : ${ligneCmd.quantite_commandee} ${uniteCmd}`;
    } else {
      elPoidsLabel.textContent = 'Poids reçu (kg)';
    }
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
    // Base du lot interne : code produit interne si rattaché, sinon réf. catalogue achats.
    const code = (etat.produit && etat.produit.code_unique)
      || etat.ligneCmd.code_article
      || 'ART';
    btnLotInterne.disabled = true; btnLotInterne.textContent = '⏳';
    try {
      const data = await apiFetch(
        `/api/receptions/${receptionId}/lot-interne?code_unique=${encodeURIComponent(code)}`);
      inpLot.value = data.lot_interne;
      inpLot.readOnly = true;
      inpLot.style.background = '#f0faf3';
      etat.lotInterne = true;
      majBadgeCarte(etat);
    } catch (e) {
      alert(`Erreur génération lot : ${e.message}`);
    } finally {
      btnLotInterne.disabled = false; btnLotInterne.textContent = 'Lot interne';
    }
  });
  inpLot.addEventListener('input', () => {
    if (etat.lotInterne) { etat.lotInterne = false; inpLot.readOnly = false; inpLot.style.background = ''; }
    majBadgeCarte(etat);
  });
  carte.querySelector('.rec-batch-date').addEventListener('input', () => majBadgeCarte(etat));

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

// Met à jour le badge de statut d'une carte (en attente / OK / NC).
function majBadgeCarte(etat) {
  const badge = etat.el.querySelector('.rec-batch-badge');
  const inpLot = etat.el.querySelector('.rec-batch-lot');
  const inpDate = etat.el.querySelector('.rec-batch-date');
  const aLot  = etat.lotInterne || (inpLot.value.trim() !== '');
  const aDate = etat.dlcType === 'no_dlc' ? true : (inpDate.value.trim() !== '');
  const estNc = Object.values(etat.criteres).some(v => v === 0);

  etat.el.classList.remove('en-attente', 'nc');
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

// Construit le payload d'une carte (même forme que _buildPayload unitaire).
function _buildPayloadBatch(etat) {
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

  const lot = etat.el.querySelector('.rec-batch-lot').value.trim();
  if (lot) payload.numero_lot = lot;

  const dateVal = etat.el.querySelector('.rec-batch-date').value;
  if (dateVal) {
    if (etat.dlcType === 'date_abattage') payload.date_abattage = dateVal;
    else                                  payload.dlc           = dateVal;
  }
  const poids = parseFloat(etat.el.querySelector('.rec-batch-poids').value);
  if (!isNaN(poids)) payload.poids_kg = poids;

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

// Valide toute la liste : POST chaque carte puis passe au récap.
async function validerBatch() {
  // Seule garde : une DLC saisie ne doit pas être dans le passé (pas pour l'abattage).
  // Le produit interne n'est PAS requis (article catalogue achats = source).
  const today = new Date().toISOString().slice(0, 10);
  for (const etat of batchLignes) {
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

    const inpDate = etat.el.querySelector('.rec-batch-date');
    if (etat.dlcType !== 'date_abattage' && inpDate.value && inpDate.value < today) {
      inpDate.classList.add('rec-champ-invalide');
      etat.el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      alert('Une DLC est dans le passé.');
      return;
    }
  }

  elBtnTerminer.disabled = true;
  const txt = elBtnTerminer.textContent;
  elBtnTerminer.textContent = 'Enregistrement…';
  try {
    for (const etat of batchLignes) {
      const ligne = await apiFetch(`/api/receptions/${receptionId}/lignes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(_buildPayloadBatch(etat)),
      });
      // Produit d'affichage : produit interne si rattaché, sinon désignation catalogue.
      const prodAffiche = etat.produit || { id: null, nom: etat.designation };
      lignesAjoutees.push(_ligneToLocal(ligne, prodAffiche));
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

    row.appendChild(left);
    row.appendChild(badge);
    elRecapLignes.appendChild(row);
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
  let secondes = 5;
  clearInterval(timerConfirmation);

  function maj() {
    elConfirmCountdown.textContent = `Retour au menu dans ${secondes}s…`;
    if (secondes <= 0) {
      clearInterval(timerConfirmation);
      window.location.href = '/hub.html';
    }
    secondes--;
  }
  maj();
  timerConfirmation = setInterval(maj, 1000);
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
}

init();

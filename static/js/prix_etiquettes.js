'use strict';
/* ============================================================
   prix_etiquettes.js — Éditeur étiquettes prix Brother QL-820NWBc

   Fonctionnalités :
   - Preview live (debounce 500 ms → POST /api/prix-etiquettes/preview)
   - Cadre de prévisualisation aux vraies proportions physiques
   - Import article depuis le catalogue achats
   - Lignes de texte configurables (police, taille, gras, alignement)
   - Upload polices TTF/OTF custom
   - Sauvegarde / chargement de modèles
   - Impression USB via POST /api/prix-etiquettes/imprimer
   ============================================================ */

// ── Helpers ──────────────────────────────────────────────────
function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Jeton valide uniquement s'il n'est pas expiré (durée de session = 8 h côté
// serveur). Évite d'envoyer un jeton périmé qui provoquerait un 401.
function getAdminToken() {
  const exp = Number(localStorage.getItem('admin_token_expires') || 0);
  if (exp && Date.now() > exp) return null;
  return localStorage.getItem('admin_token');
}

// Session expirée/invalide → on nettoie et on renvoie vers la connexion en
// mémorisant la page pour y revenir après reconnexion (même logique que guard.js).
function redirigerVersConnexion() {
  try { sessionStorage.setItem('auth_redirect', window.location.pathname); } catch (e) { /* noop */ }
  localStorage.removeItem('admin_token');
  localStorage.removeItem('admin_token_expires');
  window.location.replace('/login.html');
}

async function apiFetch(url, options = {}) {
  const token = getAdminToken();
  if (!token) { redirigerVersConnexion(); throw new Error('Session expirée'); }
  const headers = { ...(options.headers || {}) };
  headers['Authorization'] = 'Bearer ' + token;
  const res = await fetch(url, { cache: 'no-store', ...options, headers });
  if (res.status === 401) {
    // Jeton refusé par le serveur (expiré entre-temps) → reconnexion.
    redirigerVersConnexion();
    throw new Error('Session expirée');
  }
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} — ${txt || url}`);
  }
  return res.json();
}

function debounce(fn, ms) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

// ── État global ───────────────────────────────────────────────
const state = {
  largeur_cm: 10.0,
  hauteur_cm: 7.5,
  fond_noir: false,
  lignes: [],           // [{texte, taille, gras, police, alignement}]
  fontsDispos: [],      // [{nom, label}]
  modeles: [],          // [{id, nom, config}]
  modeleActifId: null,
  modeleDefautId: null,    // modèle des réimpressions (seul modèle, ou choisi ⭐)
  catalogueArticle: null,  // produit du catalogue de vente importé (variables {Nom}…)
  file: new Map(),         // catalogue_vente_id → élément de la file « À réimprimer »
};

// Polices chargées dans le navigateur via FontFace (pour le rendu Canvas).
// clé = nom de fichier TTF custom ; les valeurs DejaVu sont enregistrées sous
// la famille 'DejaVu Prix' (utilisée comme défaut, identique au backend).
const fontFamillesChargees = new Set();

// Charge une police custom (TTF servi statiquement) pour le Canvas.
async function chargerFontFace(nomFichier) {
  if (!nomFichier || fontFamillesChargees.has(nomFichier)) return;
  try {
    const ff = new FontFace(`pe-font-${nomFichier}`,
      `url('/static/fonts/custom/${encodeURIComponent(nomFichier)}')`);
    await ff.load();
    document.fonts.add(ff);
    fontFamillesChargees.add(nomFichier);
  } catch (e) {
    console.warn('Police non chargée pour aperçu:', nomFichier, e);
  }
}

// Charge la DejaVu embarquée comme police par défaut du Canvas (glyphe €, gras),
// pour que l'aperçu soit identique à l'impression backend.
async function chargerFontDefaut() {
  try {
    const reg  = new FontFace('DejaVu Prix', "url('/static/fonts/system/DejaVuSans.ttf')",        { weight: '400' });
    const bold = new FontFace('DejaVu Prix', "url('/static/fonts/system/DejaVuSans-Bold.ttf')",   { weight: '700' });
    await Promise.all([reg.load(), bold.load()]);
    document.fonts.add(reg);
    document.fonts.add(bold);
  } catch (e) {
    console.warn('DejaVu embarquée non chargée — fallback Arial pour aperçu', e);
  }
}

// ── Constantes ───────────────────────────────────────────────
const PX_PAR_CM = 118;
// Rouleau continu 62mm : hauteur (= largeur du rouleau) bridée à 6,2 cm.
const HAUTEUR_MAX_CM = 6.2;
// Épaisseur du trait d'un prix barré, en fraction de la taille de police (= backend).
const EPAISSEUR_BARRE = 0.07;
// Taille max du cadre de prévisualisation en pixels CSS
const PREVIEW_MAX_W = 520;
const PREVIEW_MAX_H = 460;

// ── Éléments DOM ─────────────────────────────────────────────
const $ = id => document.getElementById(id);

const elLargeur       = $('dim-largeur');
const elHauteur       = $('dim-hauteur');
const elFondBlanc     = $('fond-blanc');
const elFondNoir      = $('fond-noir');
const elLignesListe   = $('lignes-liste');
const elBtnAjoutLigne = $('btn-ajouter-ligne');
const elEtiquetteCadre  = $('etiquette-cadre');
const elCanvas          = $('etiquette-canvas');
const elDimsInfo        = $('preview-dims-info');
const elPrintStatus     = $('print-status');
const elFontsList       = $('fonts-liste');
const elUploadFont      = $('input-upload-font');
const elCatalogueSearch = $('catalogue-search');
const elCatalogueDropdown = $('catalogue-dropdown');
const elCatalogueSelect   = $('catalogue-selectionne');
const elCatalogueNom      = $('catalogue-nom');
const elCatalogueClear    = $('catalogue-clear');
const elListeModeles    = $('liste-modeles');
const elBtnNouveauModele = $('btn-nouveau-modele');
const elBtnSauvegarder  = $('btn-sauvegarder-modele');
const elBtnImprimer     = $('btn-imprimer');
const elBtnImprimerNav  = $('btn-imprimer-navigateur');
const elModalSave       = $('modal-save');
const elModelNom        = $('modele-nom');
const elBtnSaveConfirmer = $('btn-save-confirmer');
const elBtnSaveAnnuler  = $('btn-save-annuler');
const tplLigne          = $('tpl-ligne');

// ── Lecture de l'état courant ────────────────────────────────

function lireEtat() {
  state.largeur_cm = parseFloat(elLargeur.value) || 10;
  state.hauteur_cm = parseFloat(elHauteur.value) || 7.5;

  // Lire toutes les lignes depuis le DOM
  state.lignes = [];
  elLignesListe.querySelectorAll('.pe-ligne').forEach(el => {
    state.lignes.push({
      texte:      el.querySelector('.pe-ligne-texte').value,
      poids:      parseFloat(el.querySelector('.pe-ligne-poids').value) || 1,
      taille_px:  parseInt(el.querySelector('.pe-ligne-taille-px').value, 10) || 0,
      gras:       el.querySelector('.pe-ligne-gras').checked,
      police:     el.querySelector('.pe-ligne-police').value || null,
      alignement: el.querySelector('.pe-ligne-alignement').value,
    });
  });
}

function configVersEtat(config) {
  state.largeur_cm = config.largeur_cm ?? 10;
  state.hauteur_cm = config.hauteur_cm ?? 7.5;
  state.fond_noir  = config.fond_noir  ?? false;
  state.lignes     = config.lignes     ?? [];
}

// ── Prévisualisation — rendu CANVAS 100% LOCAL (zéro réseau) ──────────
// Miroir fidèle de l'algo backend (brother_ql_prix.generer_image_prix) :
// auto-fit max par dichotomie + taille_px fixe, mesure via métriques de police.
// Aucun appel serveur pendant l'édition → aucun lag réseau.

const FONT_FALLBACK = "'DejaVu Prix', Arial, sans-serif";

// Famille CSS à utiliser pour une ligne (police custom chargée ou défaut).
function familleCss(police) {
  if (police && fontFamillesChargees.has(police)) {
    return `'pe-font-${police}', ${FONT_FALLBACK}`;
  }
  return FONT_FALLBACK;
}

// Taille entière en px, tronquée comme le backend (max(6, int(sz))).
function taillePx(sizePx) {
  return Math.max(6, Math.trunc(sizePx));
}

// Le backend ignore « gras » pour une police custom (un seul fichier TTF) :
// l'aperçu ne doit donc pas l'épaissir non plus.
function estPoliceCustom(police) {
  return !!police && fontFamillesChargees.has(police);
}

function specFont(ligne, sizePx) {
  const poids = ligne.gras && !estPoliceCustom(ligne.police) ? '700' : '400';
  return `${poids} ${taillePx(sizePx)}px ${familleCss(ligne.police)}`;
}

// Métriques (ascent/descent en fraction de la taille) fournies par le serveur,
// mesurées par PIL exactement comme à l'impression. Repli DejaVu si absentes.
const METRIQUES_REPLI = { ascent: 0.93, descent: 0.24 };
let metriquesDefaut = { regular: METRIQUES_REPLI, bold: METRIQUES_REPLI };
const metriquesPolices = new Map();   // nom de fichier → {ascent, descent}

function metriquesLigne(ligne) {
  if (estPoliceCustom(ligne.police) && metriquesPolices.has(ligne.police)) {
    return metriquesPolices.get(ligne.police);
  }
  return ligne.gras ? metriquesDefaut.bold : metriquesDefaut.regular;
}

// Mesure identique au backend (brother_ql_prix._mesurer) :
//   - hauteur de ligne = (ascent + descent) de la POLICE, pas des lettres tapées
//     → même auto-fit à l'écran et à l'impression, quel que soit le texte ;
//   - largeur = étendue réelle des glyphes (équivalent textbbox PIL) ;
//   - inkAscent = haut réel des glyphes, pour les poser comme PIL (off_y).
function mesurer(ctx, ligne, sizePx) {
  const taille = taillePx(sizePx);
  ctx.font = specFont(ligne, taille);
  const m = ctx.measureText(ligne.texte);
  const met = metriquesLigne(ligne);
  const encreG = m.actualBoundingBoxLeft  ?? 0;
  const encreD = m.actualBoundingBoxRight ?? m.width;
  return {
    w: encreG + encreD,
    h: Math.ceil(met.ascent * taille) + Math.ceil(met.descent * taille),
    inkAscent: m.actualBoundingBoxAscent ?? met.ascent * taille,
    inkDescent: m.actualBoundingBoxDescent ?? 0,
    encreG,
  };
}

// Aperçu de l'éditeur « Libre ».
function rendrePreview() {
  lireEtat();
  dessinerEtiquette({ canvas: elCanvas, cadre: elEtiquetteCadre, info: elDimsInfo },
                    state, state.catalogueArticle);
}

// Dessine une étiquette sur un canvas, miroir de brother_ql_prix.generer_image_prix.
//   cible   : { canvas, cadre (élément aux proportions réelles), info (texte des dimensions),
//               maxW, maxH (taille max du cadre à l'écran) }
//   config  : { largeur_cm, hauteur_cm, fond_noir, lignes }
//   produit : produit du catalogue de vente (+ promo) qui remplit les variables, ou null
function dessinerEtiquette(cible, config, produit) {
  const { canvas, cadre, info } = cible;
  const maxW = cible.maxW ?? PREVIEW_MAX_W;
  const maxH = cible.maxH ?? PREVIEW_MAX_H;
  const w_cm = parseFloat(config.largeur_cm) || 10;
  const h_cm = Math.min(parseFloat(config.hauteur_cm) || 6, HAUTEUR_MAX_CM); // rouleau 62mm
  const w = Math.max(1, Math.round(w_cm * PX_PAR_CM));
  const h = Math.max(1, Math.round(h_cm * PX_PAR_CM));

  // Taille CSS du cadre (proportions réelles).
  const ratio = w / h;
  let cssW, cssH;
  if (ratio >= 1) {
    cssW = Math.min(maxW, maxH * ratio);
    cssH = cssW / ratio;
  } else {
    cssH = Math.min(maxH, maxW / ratio);
    cssW = cssH * ratio;
  }
  if (cadre) {
    cadre.style.width  = Math.round(cssW) + 'px';
    cadre.style.height = Math.round(cssH) + 'px';
  }

  // Le canvas est rendu à la résolution réelle (netteté), affiché à la taille CSS.
  canvas.width  = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');

  const fond  = config.fond_noir ? '#000' : '#fff';
  const encre = config.fond_noir ? '#fff' : '#000';
  ctx.fillStyle = fond;
  ctx.fillRect(0, 0, w, h);

  if (info) {
    info.textContent =
      `${w_cm.toFixed(1).replace('.', ',')} cm × ${h_cm.toFixed(1).replace('.', ',')} cm — ${w} × ${h} px (300 dpi)`;
  }

  // Le produit remplit les variables du modèle ({Nom}, {prix}…).
  const lignes = (config.lignes || [])
    .map(l => ({ ...l, texte: substituerVariables(l.texte || '', produit) }))
    .filter(l => (l.texte || '').trim())
    .map(l => ({
      texte: l.texte.trim(),
      poids: Math.max(0.1, parseFloat(l.poids) || 1),
      taille_px: (parseInt(l.taille_px, 10) || 0) > 0 ? parseInt(l.taille_px, 10) : 0,
      gras: !!l.gras,
      police: l.police || null,
      alignement: l.alignement || 'center',
      barre: !!l.barre,
    }));

  if (lignes.length === 0) return;

  const margeH = Math.round(w * 0.05);
  const margeV = Math.round(h * 0.06);
  const zoneW  = Math.max(1, w - 2 * margeH);
  const zoneH  = Math.max(1, h - 2 * margeV);
  const inter  = Math.round(h * 0.025);
  const n = lignes.length;

  const taille = (l, f) => l.taille_px ? l.taille_px : f * l.poids;
  const auto = lignes.some(l => !l.taille_px);

  const tient = (f) => {
    let total = inter * (n - 1);
    for (const l of lignes) {
      const mes = mesurer(ctx, l, taille(l, f));
      if (mes.w > zoneW && !l.taille_px) return false;
      total += mes.h;
    }
    return total <= zoneH;
  };

  let facteur = 0;
  if (auto) {
    let lo = 1, hi = Math.max(zoneH, zoneW);
    for (let i = 0; i < 40; i++) {
      const mid = (lo + hi) / 2;
      if (tient(mid)) lo = mid; else hi = mid;
    }
    facteur = lo;
  }

  const rendues = lignes.map(l => {
    const t = taillePx(taille(l, facteur));
    const spec = specFont(l, t);
    const mes = mesurer(ctx, l, t);
    return { ...l, spec, taille: t, w: mes.w, h: mes.h, inkAscent: mes.inkAscent,
             inkDescent: mes.inkDescent, encreG: mes.encreG };
  });

  const blocH = rendues.reduce((s, l) => s + l.h, 0) + inter * (n - 1);
  let y = Math.max(margeV, Math.floor((h - blocH) / 2));

  ctx.fillStyle = encre;
  ctx.textBaseline = 'alphabetic';
  for (const l of rendues) {
    let x;
    if (l.alignement === 'right')      x = w - margeH - l.w;
    else if (l.alignement === 'left')  x = margeH;
    else                               x = Math.floor((w - l.w) / 2);
    ctx.font = l.spec;
    // Comme PIL (y - off_y) : le haut réel des glyphes est posé sur y.
    ctx.fillText(l.texte, x, y + l.inkAscent);
    if (l.barre) {
      // Prix barré : trait au milieu de l'encre (même règle que le backend).
      const epaisseur = Math.max(2, Math.round(l.taille * EPAISSEUR_BARRE));
      const yTrait = y + Math.floor((l.inkAscent + l.inkDescent) / 2);
      ctx.fillRect(x - l.encreG, yTrait - Math.floor(epaisseur / 2), l.w, epaisseur);
    }
    y += l.h + inter;
  }
}

// Rendu instantané à chaque modification (local, pas de debounce nécessaire,
// mais on garde un micro-délai pour ne pas redessiner à chaque keystroke).
const debbouncePreview = debounce(rendrePreview, 30);

// ── Fond ─────────────────────────────────────────────────────

function majFond(noir) {
  state.fond_noir = noir;
  elFondBlanc.classList.toggle('active', !noir);
  elFondNoir.classList.toggle('active',   noir);
  elFondBlanc.setAttribute('aria-pressed', String(!noir));
  elFondNoir.setAttribute('aria-pressed',  String(noir));
  debbouncePreview();
}

elFondBlanc.addEventListener('click', () => majFond(false));
elFondNoir.addEventListener('click',  () => majFond(true));

// ── Dimensions ───────────────────────────────────────────────

elLargeur.addEventListener('input', debbouncePreview);
elHauteur.addEventListener('input', debbouncePreview);

// ── Lignes de texte ──────────────────────────────────────────

function creerLigneDOM(data = {}) {
  // Cloner le template dans un div intermédiaire pour obtenir un vrai Element
  // (DocumentFragment perd ses références après appendChild)
  const tmp = document.createElement('div');
  tmp.appendChild(tplLigne.content.cloneNode(true));
  const el  = tmp.querySelector('.pe-ligne');
  const idx = elLignesListe.children.length + 1;

  el.querySelector('.pe-ligne-num').textContent  = `Ligne ${idx}`;
  el.querySelector('.pe-ligne-texte').value      = data.texte ?? '';
  el.querySelector('.pe-ligne-gras').checked     = data.gras  ?? false;
  el.querySelector('.pe-ligne-alignement').value = data.alignement ?? 'center';
  el.querySelector('.pe-ligne-taille-px').value  = data.taille_px ? data.taille_px : '';

  // Taille relative (= ratio "poids"). On choisit l'option la plus proche de
  // la valeur demandée — robuste aux anciens modèles (ex: poids 0.5).
  const selPoids = el.querySelector('.pe-ligne-poids');
  const poids    = parseFloat(data.poids ?? 1) || 1;
  let meilleur = selPoids.options[0];
  [...selPoids.options].forEach(o => {
    if (Math.abs(parseFloat(o.value) - poids) < Math.abs(parseFloat(meilleur.value) - poids)) {
      meilleur = o;
    }
  });
  selPoids.value = meilleur.value;

  // Polices custom (nouvelle ligne sans police précisée → police par défaut)
  const selPolice = el.querySelector('.pe-ligne-police');
  remplirSelectPolice(selPolice, 'police' in data ? (data.police ?? '') : policeParDefaut());
  majGrasSelonPolice(el);

  // Suppression
  el.querySelector('.pe-ligne-suppr').addEventListener('click', () => {
    el.remove();
    renuméroterLignes();
    debbouncePreview();
  });

  // Tout changement → preview
  el.querySelectorAll('input, select').forEach(inp => {
    inp.addEventListener('input', debbouncePreview);
    inp.addEventListener('change', debbouncePreview);
  });

  // Changement de police : charger la FontFace correspondante avant de redessiner.
  selPolice.addEventListener('change', async (e) => {
    majGrasSelonPolice(el);
    const nom = e.target.value;
    if (nom) { await chargerFontFace(nom); rendrePreview(); }
  });

  return el;   // ← Element réel, pas DocumentFragment
}

// Police utilisée par défaut pour les nouvelles lignes : Moresugar-Thin si elle
// a été importée sur le serveur, sinon DejaVu ('').
const POLICE_DEFAUT_PREFEREE = 'moresugar-thin';
function policeParDefaut() {
  const f = state.fontsDispos.find(p => (p.label || '').toLowerCase() === POLICE_DEFAUT_PREFEREE);
  return f ? f.nom : '';
}

// « Gras » n'a d'effet que sur DejaVu : une police custom est un seul fichier
// TTF, imprimé tel quel. On grise la case pour ne pas laisser croire le contraire.
function majGrasSelonPolice(el) {
  const custom = !!el.querySelector('.pe-ligne-police').value;
  const chk = el.querySelector('.pe-ligne-gras');
  chk.disabled = custom;
  chk.closest('label').title = custom
    ? 'Gras sans effet avec une police importée (imprimée telle quelle)'
    : '';
}

function renuméroterLignes() {
  elLignesListe.querySelectorAll('.pe-ligne').forEach((el, i) => {
    el.querySelector('.pe-ligne-num').textContent = `Ligne ${i + 1}`;
  });
}

function remplirSelectPolice(select, valeurActive) {
  // Garder l'option par défaut
  select.innerHTML = '<option value="">DejaVu (défaut)</option>';
  state.fontsDispos.forEach(f => {
    const opt = document.createElement('option');
    opt.value = f.nom;
    opt.textContent = f.label;
    if (f.nom === valeurActive) opt.selected = true;
    select.appendChild(opt);
  });
}

function majTousSelectsPolice() {
  elLignesListe.querySelectorAll('.pe-ligne-police').forEach(sel => {
    const current = sel.value;
    remplirSelectPolice(sel, current);
    majGrasSelonPolice(sel.closest('.pe-ligne'));
  });
}

elBtnAjoutLigne.addEventListener('click', () => {
  elLignesListe.appendChild(creerLigneDOM());
  debbouncePreview();
});

// ── Polices custom ───────────────────────────────────────────

async function chargerFonts() {
  try {
    const data = await apiFetch('/api/prix-etiquettes/fonts');
    state.fontsDispos = data.fonts ?? [];
    if (data.defaut) metriquesDefaut = data.defaut;
    metriquesPolices.clear();
    state.fontsDispos.forEach(f => {
      if (f.ascent != null && f.descent != null) {
        metriquesPolices.set(f.nom, { ascent: f.ascent, descent: f.descent });
      }
    });
    afficherFonts();
    majTousSelectsPolice();
    // Charger les TTF custom pour le rendu Canvas, puis redessiner.
    await Promise.all(state.fontsDispos.map(f => chargerFontFace(f.nom)));
    rendrePreview();
  } catch (e) {
    console.error('Fonts:', e);
  }
}

function afficherFonts() {
  elFontsList.innerHTML = '';
  if (state.fontsDispos.length === 0) {
    elFontsList.innerHTML = '<span style="font-size:var(--text-xs);color:var(--color-offline)">Aucune police custom</span>';
    return;
  }
  state.fontsDispos.forEach(f => {
    const chip = document.createElement('span');
    chip.className = 'pe-font-chip';
    chip.innerHTML = `${escHtml(f.label)}<button class="pe-font-chip-del" title="Supprimer" data-nom="${escHtml(f.nom)}">✕</button>`;
    chip.querySelector('.pe-font-chip-del').addEventListener('click', async (e) => {
      e.stopPropagation();
      if (!confirm(`Supprimer la police "${f.label}" ?`)) return;
      try {
        await apiFetch(`/api/prix-etiquettes/fonts/${encodeURIComponent(f.nom)}`, { method: 'DELETE' });
        await chargerFonts();
        debbouncePreview();
      } catch (err) {
        alert('Erreur suppression : ' + err.message);
      }
    });
    elFontsList.appendChild(chip);
  });
}

elUploadFont.addEventListener('change', async () => {
  const file = elUploadFont.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append('fichier', file);
  try {
    await apiFetch('/api/prix-etiquettes/upload-font', { method: 'POST', body: fd });
    await chargerFonts();
    elUploadFont.value = '';
    debbouncePreview();
  } catch (e) {
    alert('Erreur upload police : ' + e.message);
  }
});

// ── Catalogue achats ─────────────────────────────────────────

let catalogueTimer;

elCatalogueSearch.addEventListener('input', () => {
  clearTimeout(catalogueTimer);
  const q = elCatalogueSearch.value.trim();
  if (q.length < 1) { fermerDropdownCatalogue(); return; }
  catalogueTimer = setTimeout(() => rechercherCatalogue(q), 300);
});

elCatalogueSearch.addEventListener('keydown', e => {
  if (e.key === 'Escape') fermerDropdownCatalogue();
});

document.addEventListener('click', e => {
  if (!elCatalogueSearch.contains(e.target) && !elCatalogueDropdown.contains(e.target)) {
    fermerDropdownCatalogue();
  }
});

async function rechercherCatalogue(q) {
  try {
    const data = await apiFetch(`/api/prix-etiquettes/catalogue?q=${encodeURIComponent(q)}`);
    afficherDropdownCatalogue(data.articles ?? []);
  } catch (e) {
    console.error('Catalogue search:', e);
  }
}

function afficherDropdownCatalogue(articles) {
  elCatalogueDropdown.innerHTML = '';
  if (articles.length === 0) {
    elCatalogueDropdown.innerHTML = '<div class="pe-catalogue-item" style="color:var(--color-offline)">Aucun résultat</div>';
  } else {
    articles.forEach(a => {
      const div = document.createElement('div');
      div.className = 'pe-catalogue-item';
      const prix = a.prix_vente_ttc
        ? `${parseFloat(a.prix_vente_ttc).toFixed(2)} € TTC`
        : 'Prix non renseigné';
      const famille = a.famille ? ` — ${a.famille}` : '';
      div.innerHTML = `
        <span class="pe-catalogue-item-nom">${escHtml(a.designation)}</span>
        <span class="pe-catalogue-item-prix">${escHtml(prix)}${escHtml(famille)}</span>
      `;
      div.addEventListener('click', () => selectionnerArticle(a));
      elCatalogueDropdown.appendChild(div);
    });
  }
  elCatalogueDropdown.hidden = false;
}

function fermerDropdownCatalogue() {
  elCatalogueDropdown.hidden = true;
  elCatalogueDropdown.innerHTML = '';
}

// Remplace les variables {Nom} {prix}… d'un texte par les valeurs d'un produit du
// catalogue de vente — miroir de brother_ql_prix.appliquer_variables (même rendu
// à l'écran qu'à l'impression, où le serveur relit le prix actuel en base).
function substituerVariables(texte, produit) {
  if (!produit || !texte) return texte;
  const nom = String(produit.nom ?? produit.designation ?? '');
  const v = parseFloat(produit.prix_vente_ttc);
  const prix = isNaN(v) ? '' : v.toFixed(2).replace('.', ',') + ' €';
  const piece = String(produit.unite_vente || 'kg').toLowerCase() === 'piece';
  const unite = piece ? 'pièce' : 'kg';
  const prixUnite = prix ? `${prix} / ${unite}` : '';
  const bas = nom.toLowerCase();
  // Promo (étiquette seulement) : prix barré = plus bas des 30 jours, prix promo, économie.
  const promo = produit.promo || {};
  const fmt = x => (x == null || x === '' || isNaN(parseFloat(x)))
    ? '' : parseFloat(x).toFixed(2).replace('.', ',') + ' €';
  const ref = promo.prix_reference_ttc, prixPromo = promo.prix_promo_ttc;
  const economie = (ref != null && prixPromo != null)
    ? fmt(Math.round((parseFloat(ref) - parseFloat(prixPromo)) * 100) / 100) : '';
  const valeurs = {
    '{nom}': nom,
    '{Nom}': bas.charAt(0).toUpperCase() + bas.slice(1),
    '{NOM}': nom.toUpperCase(),
    '{prix}': prix,
    '{prix_kg}': prixUnite,
    '{prix_unite}': prixUnite,
    '{unite}': unite,
    '{article_unite}': piece ? 'la pièce' : 'le kg',
    '{famille}': produit.famille || '',
    '{sous_famille}': produit.sous_famille || '',
    '{prix_reference}': fmt(ref),
    '{prix_promo}': fmt(prixPromo),
    '{economie_unite}': economie ? `${economie} / ${unite}` : '',
  };
  return Object.entries(valeurs).reduce((t, [cle, val]) => t.split(cle).join(val), texte);
}

const RE_VARIABLE = /\{(nom|Nom|NOM|prix|prix_kg|prix_unite|unite|article_unite|famille|sous_famille|prix_reference|prix_promo|economie_unite)\}/;

function lignesAVariables() {
  return [...elLignesListe.querySelectorAll('.pe-ligne-texte')]
    .some(inp => RE_VARIABLE.test(inp.value || ''));
}

function lignesVides() {
  return [...elLignesListe.querySelectorAll('.pe-ligne-texte')]
    .every(inp => !(inp.value || '').trim());
}

// Id catalogue de VENTE de l'article importé (null si l'article vient d'ailleurs).
function produitVenteId() {
  return state.catalogueArticle?.id ?? null;
}

function selectionnerArticle(article) {
  state.catalogueArticle = article;
  elCatalogueNom.textContent = article.designation ?? article.nom ?? '';
  elCatalogueSelect.hidden = false;
  elCatalogueSearch.value = '';
  fermerDropdownCatalogue();

  // Étiquette vierge → on part du modèle par défaut (modèle des prix de la boutique).
  if (lignesVides()) {
    const defaut = state.modeles.find(m => m.id === state.modeleDefautId);
    if (defaut) chargerModele(defaut);
  }

  // Modèle à variables : on GARDE sa mise en page, l'article remplit {Nom}, {prix}…
  if (lignesAVariables()) {
    rendrePreview();
    return;
  }

  // Sinon (texte libre) : lignes générées à partir de l'article, comme avant.
  elLignesListe.innerHTML = '';
  elLignesListe.appendChild(creerLigneDOM({
    texte: article.designation ?? article.nom, poids: 1, gras: true, alignement: 'center',
  }));
  if (article.prix_vente_ttc) {
    const prix = parseFloat(article.prix_vente_ttc).toFixed(2).replace('.', ',') + ' €';
    const piece = String(article.unite_vente || 'kg').toLowerCase() === 'piece';
    elLignesListe.appendChild(creerLigneDOM({
      texte: prix, poids: 3, gras: true, alignement: 'center',
    }));
    elLignesListe.appendChild(creerLigneDOM({
      texte: piece ? 'la pièce' : 'le kg', poids: 0.6, gras: false, alignement: 'center',
    }));
  }

  debbouncePreview();
}

elCatalogueClear.addEventListener('click', () => {
  state.catalogueArticle = null;
  elCatalogueSelect.hidden = true;
  elCatalogueNom.textContent = '';
  rendrePreview();   // les variables réapparaissent telles quelles
});

// ── Modèles ──────────────────────────────────────────────────

async function chargerModeles() {
  try {
    const [data, defaut] = await Promise.all([
      apiFetch('/api/prix-etiquettes/modeles'),
      apiFetch('/api/prix-etiquettes/modele-defaut'),
    ]);
    state.modeles = data.modeles ?? [];
    state.modeleDefautId = defaut.modele_id ?? null;
    afficherModeles();
  } catch (e) {
    console.error('Modeles:', e);
  }
}

function afficherModeles() {
  elListeModeles.innerHTML = '';
  state.modeles.forEach(m => {
    const chip = document.createElement('div');
    chip.className = 'pe-modele-chip' + (m.id === state.modeleActifId ? ' active' : '');
    chip.dataset.id = m.id;
    chip.innerHTML = `
      <span class="pe-modele-chip-nom">${escHtml(m.nom)}</span>
      <button class="pe-modele-chip-del" title="Supprimer ce modèle" data-id="${m.id}">✕</button>
    `;
    chip.querySelector('.pe-modele-chip-nom').addEventListener('click', () => chargerModele(m));
    chip.querySelector('.pe-modele-chip-del').addEventListener('click', async e => {
      e.stopPropagation();
      if (!confirm(`Supprimer le modèle "${m.nom}" ?`)) return;
      try {
        await apiFetch(`/api/prix-etiquettes/modeles/${m.id}`, { method: 'DELETE' });
        if (state.modeleActifId === m.id) state.modeleActifId = null;
        await chargerModeles();
      } catch (err) {
        alert('Erreur : ' + err.message);
      }
    });
    elListeModeles.appendChild(chip);
  });
}

function chargerModele(modele) {
  state.modeleActifId = modele.id;
  const config = modele.config;
  configVersEtat(config);

  // Appliquer au DOM
  elLargeur.value = state.largeur_cm;
  elHauteur.value = state.hauteur_cm;
  majFond(state.fond_noir);

  elLignesListe.innerHTML = '';
  state.lignes.forEach(l => elLignesListe.appendChild(creerLigneDOM(l)));

  afficherModeles(); // met à jour la chip active
  rendrePreview();
}

elBtnNouveauModele.addEventListener('click', () => {
  state.modeleActifId = null;
  elLignesListe.innerHTML = '';
  state.catalogueArticle = null;
  elCatalogueSelect.hidden = true;
  elCatalogueSearch.value = '';
  majFond(false);
  elLargeur.value = 10;
  elHauteur.value = 7.5;
  afficherModeles();
  rendrePreview();
});

// ── Sauvegarde modèle ────────────────────────────────────────

elBtnSauvegarder.addEventListener('click', () => {
  const modeleActif = state.modeles.find(m => m.id === state.modeleActifId);
  elModelNom.value = modeleActif ? modeleActif.nom : '';
  elModalSave.hidden = false;
  elModelNom.focus();
});

elBtnSaveAnnuler.addEventListener('click', () => { elModalSave.hidden = true; });

elModalSave.addEventListener('click', e => {
  if (e.target === elModalSave) elModalSave.hidden = true;
});

elBtnSaveConfirmer.addEventListener('click', async () => {
  const nom = elModelNom.value.trim();
  if (!nom) { elModelNom.focus(); return; }

  lireEtat();
  const config = {
    largeur_cm: state.largeur_cm,
    hauteur_cm: state.hauteur_cm,
    fond_noir:  state.fond_noir,
    lignes:     state.lignes,
  };

  try {
    if (state.modeleActifId) {
      // Mise à jour du modèle existant
      await apiFetch(`/api/prix-etiquettes/modeles/${state.modeleActifId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nom, config }),
      });
    } else {
      // Nouveau modèle
      const res = await apiFetch('/api/prix-etiquettes/modeles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nom, config }),
      });
      state.modeleActifId = res.id;
    }
    elModalSave.hidden = true;
    await chargerModeles();
  } catch (e) {
    alert('Erreur sauvegarde : ' + e.message);
  }
});

// ── Impression ───────────────────────────────────────────────

function afficherStatut(msg, type) {
  // type : 'ok' | 'err' | 'loading'
  elPrintStatus.textContent = msg;
  elPrintStatus.className = `pe-print-status pe-print-status--${type}`;
  elPrintStatus.hidden = false;
  if (type === 'ok') setTimeout(() => { elPrintStatus.hidden = true; }, 4000);
}

// Contrôles communs aux deux impressions de l'éditeur. Renvoie false si bloquant.
function verifierAvantImpression() {
  lireEtat();
  if (state.lignes.length === 0 || state.lignes.every(l => !l.texte.trim())) {
    afficherStatut('Ajoutez au moins une ligne de texte avant d\'imprimer.', 'err');
    return false;
  }
  if (!state.catalogueArticle && lignesAVariables()) {
    afficherStatut('Ce modèle contient des variables ({Nom}, {prix}…) : choisissez d\'abord '
      + 'un article dans « Import article », sinon elles seraient imprimées telles quelles.', 'err');
    return false;
  }
  return true;
}

elBtnImprimer.addEventListener('click', async () => {
  if (!verifierAvantImpression()) return;

  const payload = {
    largeur_cm: state.largeur_cm,
    hauteur_cm: state.hauteur_cm,
    fond_noir:  state.fond_noir,
    lignes:     state.lignes,
    // Le serveur remplit les variables avec le prix ACTUEL en base et sort le
    // produit de la file « À réimprimer ».
    produit_id: produitVenteId(),
  };

  elBtnImprimer.disabled = true;
  afficherStatut('Envoi à l\'imprimante…', 'loading');

  try {
    await apiFetch('/api/prix-etiquettes/imprimer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    afficherStatut('✓ Étiquette imprimée avec succès.', 'ok');
    chargerFile();
  } catch (e) {
    afficherStatut('Erreur impression : ' + e.message, 'err');
  } finally {
    elBtnImprimer.disabled = false;
  }
});

// Impression navigateur : on ne sait pas si l'étiquette est vraiment sortie, on
// demande avant de retirer les produits de la file « À réimprimer ».
async function proposerSortieFile(ids) {
  const dansFile = ids.filter(id => state.file.has(id));
  if (!dansFile.length) return;
  const n = dansFile.length;
  if (!confirm(`Une fois imprimée${n > 1 ? 's' : ''}, retirer ${n} étiquette${n > 1 ? 's' : ''} `
      + 'de la liste « À réimprimer » ?')) return;
  try {
    await apiFetch('/api/prix-etiquettes/a-reimprimer/sortir', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ produit_ids: dansFile, statut: 'imprimee', mode: 'navigateur' }),
    });
  } catch (e) {
    alert('Erreur : ' + e.message);
  }
  await chargerFile();
}

// ── Impression via le navigateur (Wi-Fi / sans USB serveur) ──
// Imprime le canvas d'aperçu tel quel, dimensionné à la taille physique
// réelle de l'étiquette. Sert au test hors boutique et de secours :
// l'utilisateur choisit l'imprimante dans la boîte de dialogue du navigateur.
elBtnImprimerNav.addEventListener('click', () => {
  if (!verifierAvantImpression()) return;
  rendrePreview();   // canvas à jour (variables remplies) avant de le copier

  // Le canvas est déjà rendu à la résolution réelle par l'aperçu live.
  // On reprend EXACTEMENT ses dimensions, hauteur bridée comme dans
  // rendrePreview() (rouleau 62mm), pour que l'impression colle au canvas.
  const dataUrl = elCanvas.toDataURL('image/png');
  const lCm = state.largeur_cm;
  const hCm = Math.min(state.hauteur_cm, HAUTEUR_MAX_CM);

  const win = window.open('', '_blank');
  if (!win) {
    afficherStatut('Fenêtre d\'impression bloquée par le navigateur (autorisez les pop-ups).', 'err');
    return;
  }

  win.document.write(`<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><title>Étiquette prix</title>
<style>
  @page { size: ${lCm}cm ${hCm}cm; margin: 0; }
  html, body { margin: 0; padding: 0; }
  img { display: block; width: ${lCm}cm; height: ${hCm}cm; }
</style></head>
<body>
  <img src="${dataUrl}" alt="Étiquette prix"
       onload="window.focus(); window.print();">
</body></html>`);
  win.document.close();
  win.addEventListener('afterprint', () => win.close());
  afficherStatut('Aperçu ouvert — choisissez l\'imprimante dans la fenêtre.', 'ok');
  const id = produitVenteId();
  if (id != null) proposerSortieFile([id]);
});

// ── File « À réimprimer » (produits dont le prix a changé) ────
const elBadgeFile = $('badge-a-reimprimer');

async function chargerFile() {
  try {
    const data = await apiFetch('/api/prix-etiquettes/a-reimprimer');
    state.file = new Map((data.elements ?? []).map(e => [e.catalogue_vente_id, e]));
    state.modeleDefautId = data.modele_defaut_id ?? state.modeleDefautId;
  } catch (e) {
    console.error('File à réimprimer :', e);
  }
  const n = state.file.size;
  elBadgeFile.textContent = n;
  elBadgeFile.hidden = n === 0;
}

// ── Série imprimée via le navigateur (secours sans imprimante serveur) ──
// Le serveur génère une image par produit (prix actuel), le navigateur empile
// une page par exemplaire. Renvoie le nombre d'étiquettes, ou lève une erreur.
async function imprimerSerieNavigateur(config, produits) {
  const res = await apiFetch('/api/prix-etiquettes/preview-masse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ config, produits }),
  });
  const etiquettes = res.etiquettes ?? [];
  if (etiquettes.length === 0) throw new Error('Aucune étiquette générée.');
  const lCm = config.largeur_cm ?? 10;
  const hCm = Math.min(config.hauteur_cm ?? 6, HAUTEUR_MAX_CM);
  const pages = [];
  etiquettes.forEach(et => {
    for (let i = 0; i < (et.quantite || 1); i++) {
      pages.push(`<img src="${et.image}" alt="${escHtml(et.nom)}">`);
    }
  });
  const win = window.open('', '_blank');
  if (!win) throw new Error('Pop-ups bloquées — autorisez-les pour imprimer.');
  win.document.write(`<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><title>Étiquettes prix (série)</title>
<style>
  @page { size: ${lCm}cm ${hCm}cm; margin: 0; }
  html, body { margin: 0; padding: 0; }
  img { display: block; width: ${lCm}cm; height: ${hCm}cm; page-break-after: always; }
  img:last-child { page-break-after: auto; }
</style></head>
<body onload="window.focus(); window.print();">
${pages.join('\n')}
</body></html>`);
  win.document.close();
  win.addEventListener('afterprint', () => win.close());
  return pages.length;
}

// ── Onglets : Imprimer | Style | Étiquette libre ─────────────
// Chaque vue s'enregistre dans peVues : { afficher(), quitter() → false pour rester }.
const peVues = {};
window.peVues = peVues;
const ONGLETS = ['imprimer', 'style', 'libre'];

async function afficherOnglet(nom) {
  if (!ONGLETS.includes(nom)) nom = 'imprimer';
  const actuel = document.body.dataset.onglet;
  if (actuel && actuel !== nom && peVues[actuel]?.quitter && !peVues[actuel].quitter()) return;
  document.body.dataset.onglet = nom;
  document.querySelectorAll('.pe-onglet').forEach(o =>
    o.classList.toggle('active', o.dataset.onglet === nom));
  try { localStorage.setItem('pe_onglet', nom); } catch (e) { /* ignore */ }
  if (nom === 'libre') rendrePreview();
  await peVues[nom]?.afficher?.();
}

document.querySelectorAll('.pe-onglet').forEach(o =>
  o.addEventListener('click', () => afficherOnglet(o.dataset.onglet)));

// ── Persistance locale des dimensions ────────────────────────

function sauvegarderDimsLocal() {
  try {
    localStorage.setItem('pe_dims', JSON.stringify({
      largeur_cm: parseFloat(elLargeur.value) || 10,
      hauteur_cm: parseFloat(elHauteur.value) || 7.5,
    }));
  } catch (e) { /* localStorage indisponible */ }
}

function restaurerDimsLocal() {
  try {
    const saved = JSON.parse(localStorage.getItem('pe_dims') || '{}');
    if (saved.largeur_cm) elLargeur.value = saved.largeur_cm;
    if (saved.hauteur_cm) elHauteur.value = saved.hauteur_cm;
  } catch (e) { /* ignore */ }
}

elLargeur.addEventListener('change', sauvegarderDimsLocal);
elHauteur.addEventListener('change', sauvegarderDimsLocal);

// ── Init ──────────────────────────────────────────────────────

async function init() {
  restaurerDimsLocal();
  await chargerFontDefaut();   // DejaVu embarquée pour l'aperçu Canvas
  rendrePreview();             // premier rendu immédiat (avant les appels réseau)
  await chargerFonts();
  await chargerModeles();
  await chargerFile();
  rendrePreview();

  // Import article depuis catalogue achats (bouton 🏷️ du tableau catalogue).
  // Son id est celui du catalogue ACHATS : on l'efface pour ne pas le confondre
  // avec un produit de vente (variables, file « À réimprimer »).
  let ongletDepart = null;
  try {
    const raw = sessionStorage.getItem('pe_article_import');
    if (raw) {
      sessionStorage.removeItem('pe_article_import');
      const article = JSON.parse(raw);
      selectionnerArticle({ ...article, id: null });
      ongletDepart = 'libre';
    }
  } catch (e) { /* ignore */ }

  // Ligne de démarrage vide si aucun article importé
  if (elLignesListe.children.length === 0) {
    elLignesListe.appendChild(creerLigneDOM({ texte: '', gras: true, alignement: 'center' }));
  }

  rendrePreview();

  // Onglet de départ : « Imprimer » (arrivée depuis la tuile du Hub ?reimprimer
  // comprise), sauf import d'article ; sinon le dernier onglet utilisé.
  if (!ongletDepart && !new URLSearchParams(location.search).has('reimprimer')) {
    try { ongletDepart = localStorage.getItem('pe_onglet'); } catch (e) { /* ignore */ }
  }
  await afficherOnglet(ongletDepart || 'imprimer');
}

// Promesse exposée : les autres scripts de la page (vues Imprimer, Style) peuvent
// attendre la fin du chargement initial (polices, modèles, file).
document.addEventListener('DOMContentLoaded', () => { window.peInit = init(); });

// ── Modale configuration imprimante ──────────────────────────

(function () {
  const overlay = document.getElementById('printer-modal-overlay');
  const input   = document.getElementById('printer-ip-input');
  const msgEl   = document.getElementById('printer-status-msg');
  const btnOpen = document.getElementById('btn-config-imprimante');
  const btnClose= document.getElementById('printer-modal-close');
  const btnTest = document.getElementById('printer-btn-test');
  const btnSave = document.getElementById('printer-btn-save');
  if (!overlay) return;

  function showMsg(text, ok) {
    msgEl.textContent = text;
    msgEl.style.background = ok ? '#d1fae5' : '#fee2e2';
    msgEl.style.color       = ok ? '#065f46' : '#991b1b';
    msgEl.style.display     = 'block';
  }

  function ipToIdentifier(raw) {
    raw = (raw || '').trim();
    if (!raw) return '';
    return raw.startsWith('tcp://') ? raw : 'tcp://' + raw;
  }

  async function openModal() {
    msgEl.style.display = 'none';
    try {
      const res  = await apiFetch('/api/impression/config');
      const id   = res.identifier || '';
      input.value = id.replace('tcp://', '');
    } catch (_) {}
    overlay.style.display = 'flex';
    input.focus();
  }

  function closeModal() { overlay.style.display = 'none'; }

  btnOpen  && btnOpen.addEventListener('click', openModal);
  btnClose && btnClose.addEventListener('click', closeModal);
  overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });

  btnTest.addEventListener('click', async () => {
    const id = ipToIdentifier(input.value);
    if (!id) { showMsg('Entrez une adresse IP.', false); return; }
    btnTest.disabled = true;
    btnTest.textContent = '…';
    try {
      await apiFetch('/api/impression/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: id }),
      });
      const data = await apiFetch('/api/impression/status');
      showMsg(data.message || (data.disponible ? 'Joignable ✓' : 'Injoignable ✗'), data.disponible);
    } catch (e) {
      showMsg('Erreur réseau : ' + e.message, false);
    } finally {
      btnTest.disabled = false;
      btnTest.textContent = '🔍 Tester';
    }
  });

  btnSave.addEventListener('click', async () => {
    const id = ipToIdentifier(input.value);
    if (!id) { showMsg('Entrez une adresse IP.', false); return; }
    btnSave.disabled = true;
    try {
      const data = await apiFetch('/api/impression/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: id }),
      });
      if (data.ok) {
        showMsg('Configuration enregistrée ✓', true);
        setTimeout(closeModal, 1200);
      } else {
        showMsg('Erreur lors de l\'enregistrement.', false);
      }
    } catch (_) {
      showMsg('Erreur réseau.', false);
    } finally {
      btnSave.disabled = false;
    }
  });
})();

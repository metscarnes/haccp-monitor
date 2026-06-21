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

async function apiFetch(url, options = {}) {
  const token = localStorage.getItem('admin_token');
  const headers = { ...(options.headers || {}) };
  if (token) headers['Authorization'] = 'Bearer ' + token;
  const res = await fetch(url, { cache: 'no-store', ...options, headers });
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
  catalogueArticle: null,  // article sélectionné depuis le catalogue
};

// ── Constantes ───────────────────────────────────────────────
const PX_PAR_CM = 118;
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
const elEtiquetteImg    = $('etiquette-img');
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
      taille:     parseInt(el.querySelector('.pe-ligne-taille').value, 10) || 36,
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

// ── Prévisualisation ─────────────────────────────────────────

function majCadreProportions() {
  const w_cm = state.largeur_cm;
  const h_cm = state.hauteur_cm;
  const ratio = w_cm / h_cm;

  let cssW, cssH;
  if (ratio >= 1) {
    cssW = Math.min(PREVIEW_MAX_W, PREVIEW_MAX_H * ratio);
    cssH = cssW / ratio;
  } else {
    cssH = Math.min(PREVIEW_MAX_H, PREVIEW_MAX_W / ratio);
    cssW = cssH * ratio;
  }

  elEtiquetteCadre.style.width  = Math.round(cssW) + 'px';
  elEtiquetteCadre.style.height = Math.round(cssH) + 'px';

  const px_w = Math.round(w_cm * PX_PAR_CM);
  const px_h = Math.round(h_cm * PX_PAR_CM);
  elDimsInfo.textContent =
    `${w_cm.toFixed(1).replace('.', ',')} cm × ${h_cm.toFixed(1).replace('.', ',')} cm — ${px_w} × ${px_h} px (300 dpi)`;
}

async function rafraichirPreview() {
  lireEtat();
  majCadreProportions();

  const payload = {
    largeur_cm: state.largeur_cm,
    hauteur_cm: state.hauteur_cm,
    fond_noir:  state.fond_noir,
    lignes:     state.lignes,
  };

  try {
    const data = await apiFetch('/api/prix-etiquettes/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    elEtiquetteImg.src = data.image;
  } catch (e) {
    console.error('Preview:', e);
  }
}

const debbouncePreview = debounce(rafraichirPreview, 500);

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
  const frag = tplLigne.content.cloneNode(true);
  const el   = frag.querySelector('.pe-ligne');
  const idx  = elLignesListe.children.length + 1;

  el.querySelector('.pe-ligne-num').textContent = `Ligne ${idx}`;
  el.querySelector('.pe-ligne-texte').value     = data.texte      ?? '';
  el.querySelector('.pe-ligne-taille').value    = data.taille     ?? 36;
  el.querySelector('.pe-ligne-gras').checked    = data.gras       ?? false;
  el.querySelector('.pe-ligne-alignement').value = data.alignement ?? 'center';

  // Peupler le select police avec les fonts dispo
  const selectPolice = el.querySelector('.pe-ligne-police');
  remplirSelectPolice(selectPolice, data.police ?? '');

  // Suppression
  el.querySelector('.pe-ligne-suppr').addEventListener('click', () => {
    el.remove();
    renuméroterLignes();
    debbouncePreview();
  });

  // Changements → preview
  el.querySelectorAll('input, select').forEach(inp => {
    inp.addEventListener('input', debbouncePreview);
    inp.addEventListener('change', debbouncePreview);
  });

  return frag;
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
    afficherFonts();
    majTousSelectsPolice();
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

function selectionnerArticle(article) {
  state.catalogueArticle = article;
  elCatalogueNom.textContent = article.designation;
  elCatalogueSelect.hidden = false;
  elCatalogueSearch.value = '';
  fermerDropdownCatalogue();

  // Toujours remplacer les lignes existantes par celles de l'article importé
  elLignesListe.innerHTML = '';

  elLignesListe.appendChild(creerLigneDOM({
    texte: article.designation,
    taille: 40,
    gras: true,
    alignement: 'center',
  }));

  if (article.prix_vente_ttc) {
    const prix = parseFloat(article.prix_vente_ttc).toFixed(2).replace('.', ',') + ' €';
    elLignesListe.appendChild(creerLigneDOM({
      texte: prix,
      taille: 80,
      gras: true,
      alignement: 'center',
    }));
    elLignesListe.appendChild(creerLigneDOM({
      texte: 'le kg',
      taille: 28,
      gras: false,
      alignement: 'center',
    }));
  }

  debbouncePreview();
}

elCatalogueClear.addEventListener('click', () => {
  state.catalogueArticle = null;
  elCatalogueSelect.hidden = true;
  elCatalogueNom.textContent = '';
});

// ── Modèles ──────────────────────────────────────────────────

async function chargerModeles() {
  try {
    const data = await apiFetch('/api/prix-etiquettes/modeles');
    state.modeles = data.modeles ?? [];
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
  rafraichirPreview();
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
  rafraichirPreview();
});

// ── Sauvegarde modèle ────────────────────────────────────────

elBtnSauvegarder.addEventListener('click', () => {
  elModelNom.value = '';
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

elBtnImprimer.addEventListener('click', async () => {
  lireEtat();
  if (state.lignes.length === 0 || state.lignes.every(l => !l.texte.trim())) {
    afficherStatut('Ajoutez au moins une ligne de texte avant d\'imprimer.', 'err');
    return;
  }

  const payload = {
    largeur_cm: state.largeur_cm,
    hauteur_cm: state.hauteur_cm,
    fond_noir:  state.fond_noir,
    lignes:     state.lignes,
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
  } catch (e) {
    afficherStatut('Erreur impression : ' + e.message, 'err');
  } finally {
    elBtnImprimer.disabled = false;
  }
});

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
  await chargerFonts();
  await chargerModeles();
  majCadreProportions();

  // Import article depuis catalogue achats (bouton 🏷️ du tableau catalogue)
  try {
    const raw = sessionStorage.getItem('pe_article_import');
    if (raw) {
      sessionStorage.removeItem('pe_article_import');
      const article = JSON.parse(raw);
      selectionnerArticle(article);
    }
  } catch (e) { /* ignore */ }

  // Ligne de démarrage vide si aucun article importé
  if (elLignesListe.children.length === 0) {
    elLignesListe.appendChild(creerLigneDOM({ texte: '', taille: 48, gras: true, alignement: 'center' }));
  }

  rafraichirPreview();
}

document.addEventListener('DOMContentLoaded', init);

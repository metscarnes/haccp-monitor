'use strict';
/* ============================================================
   prix_etiquettes.js — Module Étiquettes prix (Brother QL-820NWB)

   Socle commun de la page (onglets Imprimer / Style / Étiquette libre) :
   - session, appels API, polices (FontFace + métriques serveur) ;
   - dessin d'une étiquette sur canvas, miroir exact de l'impression ;
   - file « À réimprimer », impression navigateur sans pop-up, onglets ;
   - onglet « Étiquette libre » : du TEXTE seulement, au style de la boutique.
   Vues : prix_etiquettes_imprimer.js, prix_etiquettes_style.js.
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
  fontsDispos: [],      // [{nom, label, ascent, descent}]
  styleNormal: null,    // config du style « normal » de la boutique
  file: new Map(),      // catalogue_vente_id → élément de la file « À réimprimer »
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

// ── Dessin d'une étiquette — rendu CANVAS 100% LOCAL (zéro réseau) ──
// Miroir fidèle de brother_ql_prix.generer_image_prix : auto-fit max par
// dichotomie + taille_px fixe, mesure via les métriques de police du serveur.

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

// Police utilisée par défaut pour les nouvelles lignes : Moresugar-Thin si elle
// a été importée sur le serveur, sinon DejaVu ('').
const POLICE_DEFAUT_PREFEREE = 'moresugar-thin';
function policeParDefaut() {
  const f = state.fontsDispos.find(p => (p.label || '').toLowerCase() === POLICE_DEFAUT_PREFEREE);
  return f ? f.nom : '';
}

// Polices custom (importées dans l'onglet Style) : chargées pour l'aperçu, avec leurs
// métriques mesurées par le serveur (mêmes tailles à l'écran qu'à l'impression).
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
    await Promise.all(state.fontsDispos.map(f => chargerFontFace(f.nom)));
  } catch (e) {
    console.error('Polices :', e);
  }
}

// ── Impression : outils communs ──────────────────────────────

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

// Historique : une impression par le navigateur est notée à l'ouverture de la fenêtre
// d'impression (sans attendre : un échec de l'historique ne gêne jamais l'impression).
function noterImpressionNavigateur(corps) {
  apiFetch('/api/prix-etiquettes/impressions/navigateur', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(corps),
  }).catch(e => console.warn('Historique des impressions :', e));
}

// ── File « À réimprimer » (produits dont le prix a changé) ────
const elBadgeFile = $('badge-a-reimprimer');

async function chargerFile() {
  try {
    const data = await apiFetch('/api/prix-etiquettes/a-reimprimer');
    state.file = new Map((data.elements ?? []).map(e => [e.catalogue_vente_id, e]));
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
  const images = [];
  etiquettes.forEach(et => {
    for (let i = 0; i < (et.quantite || 1); i++) images.push({ src: et.image, alt: et.nom });
  });
  await imprimerImagesSansPopup(images, lCm, hCm, 'Étiquettes prix (série)');
  return images.length;
}

// Impression navigateur SANS fenêtre pop-up (souvent bloquée sur tablette) : les
// étiquettes sont posées dans un cadre invisible de la page, une page par étiquette
// à sa taille réelle, puis la boîte d'impression du navigateur s'ouvre.
async function imprimerImagesSansPopup(images, lCm, hCm, titre) {
  document.getElementById('pe-cadre-impression')?.remove();
  const cadre = document.createElement('iframe');
  cadre.id = 'pe-cadre-impression';
  cadre.setAttribute('aria-hidden', 'true');
  cadre.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;';
  document.body.appendChild(cadre);
  const doc = cadre.contentDocument;
  doc.open();
  doc.write(`<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><title>${escHtml(titre)}</title>
<style>
  @page { size: ${lCm}cm ${hCm}cm; margin: 0; }
  html, body { margin: 0; padding: 0; }
  img { display: block; width: ${lCm}cm; height: ${hCm}cm; page-break-after: always; }
  img:last-child { page-break-after: auto; }
</style></head>
<body>${images.map(i => `<img src="${i.src}" alt="${escHtml(i.alt || '')}">`).join('\n')}</body></html>`);
  doc.close();
  // Attendre que toutes les images soient prêtes avant d'imprimer.
  await Promise.all([...doc.images].map(img => (img.complete ? null
    : new Promise(ok => { img.onload = img.onerror = ok; }))));
  cadre.contentWindow.focus();
  cadre.contentWindow.print();
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
  await peVues[nom]?.afficher?.();
}

document.querySelectorAll('.pe-onglet').forEach(o =>
  o.addEventListener('click', () => afficherOnglet(o.dataset.onglet)));

// ── Étiquette libre : texte libre OU étiquette prix, au style de la boutique ──
// Pas de taille, de police, de fond, de format ni de modèle à choisir : une seule
// apparence pour toutes les étiquettes (le style normal). Deux sortes :
//  - « Texte libre » (« Arrivage du jour »…) : le serveur la redessine avec ce style
//    (brother_ql_prix.config_libre), quoi que l'écran envoie ;
//  - « Étiquette prix » d'un article absent du catalogue : seuls le nom, le prix et
//    l'unité se tapent, la mise en page est celle des étiquettes prix. Le serveur note
//    le produit à créer au catalogue de vente (tâche du Hub).
const MAX_LIGNES_LIBRES = 5;
const CLE_TEXTES_LIBRES = 'pe_libre_textes';
const CLE_SORTE_LIBRE   = 'pe_libre_sorte';
const CLE_ARTICLE_LIBRE = 'pe_libre_article';
const elLibreLignes  = $('libre-lignes');
const elLibreAjouter = $('libre-ajouter');
const elLibreNom     = $('libre-nom');
const elLibrePrix    = $('libre-prix');
const elLibreExiste  = $('libre-existe');
const elCanvas       = $('etiquette-canvas');
const elCadre        = $('etiquette-cadre');
const elDimsInfo     = $('preview-dims-info');
const elPrintStatus  = $('print-status');
const elBtnImprimer  = $('btn-imprimer');
const elBtnImprimerNav = $('btn-imprimer-navigateur');
const SANS_STYLE = 'Aucun style d\'étiquette : l\'administrateur doit le créer dans l\'onglet « Style ».';

const libre = { sorte: 'texte', unite: 'kg', catalogue: null };

function afficherStatut(msg, type) {
  // type : 'ok' | 'err' | 'loading'
  elPrintStatus.textContent = msg;
  elPrintStatus.className = `pe-print-status pe-print-status--${type}`;
  elPrintStatus.hidden = false;
  if (type === 'ok') setTimeout(() => { elPrintStatus.hidden = true; }, 6000);
}

function textesLibres() {
  return [...elLibreLignes.querySelectorAll('.pe-libre-texte')].map(i => i.value);
}

// Miroir de brother_ql_prix.config_libre : format, fond et police du style normal,
// lignes de même taille, centrées.
function configLibre(style, textes) {
  const lignes = style.lignes || [];
  const zoneNom = lignes.find(l => l.zone === 'nom') || lignes[0] || {};
  return {
    largeur_cm: style.largeur_cm, hauteur_cm: style.hauteur_cm, fond_noir: !!style.fond_noir,
    lignes: textes.map(t => t.trim()).filter(Boolean).slice(0, MAX_LIGNES_LIBRES).map(texte => ({
      texte, poids: 1, taille_px: 0, gras: false, police: zoneNom.police || null, alignement: 'center',
    })),
  };
}

// « 14,90 » / « 14.9 » / « 14,90 € » → 14.9 ; null si illisible ou ≤ 0.
function lirePrix(texte) {
  const v = parseFloat(String(texte || '').replace(/[€\s]/g, '').replace(',', '.'));
  return Number.isFinite(v) && v > 0 && v < 10000 ? Math.round(v * 100) / 100 : null;
}

// Article tapé à la main, sous la forme d'un produit du catalogue (pour l'aperçu).
function articleSaisi() {
  return { nom: elLibreNom.value.replace(/\s+/g, ' ').trim(),
           prix_vente_ttc: lirePrix(elLibrePrix.value), unite_vente: libre.unite };
}

// Nom sans accents ni majuscules (miroir de produits_a_creer.normaliser_nom).
const normaliser = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '')
  .replace(/\s+/g, ' ').trim().toLowerCase();

// L'article existe peut-être déjà au catalogue : on le signale, avec un lien vers
// sa vraie étiquette (prix du catalogue), pour éviter les doublons.
async function signalerExistants() {
  const cle = normaliser(elLibreNom.value);
  if (cle.length < 3) { elLibreExiste.hidden = true; return; }
  if (!libre.catalogue) {
    try {
      libre.catalogue = (await apiFetch('/api/prix-etiquettes/catalogue?limit=2000')).articles ?? [];
    } catch (e) { libre.catalogue = []; }
  }
  if (normaliser(elLibreNom.value) !== cle) return;     // saisie changée entre-temps
  const proches = libre.catalogue.filter(p => normaliser(p.nom).includes(cle)).slice(0, 3);
  elLibreExiste.hidden = !proches.length;
  elLibreExiste.innerHTML = proches.length ? `Déjà au catalogue : ${proches.map(p => `
    <a href="/prix-etiquettes.html?produit=${p.id}">${escHtml(p.nom)}${p.prix_vente_ttc != null
      ? ` (${p.prix_vente_ttc.toFixed(2).replace('.', ',')} €)` : ''}</a>`).join(', ')}
    — touchez-le pour imprimer sa vraie étiquette.` : '';
}

function sauverSaisie() {
  try {
    localStorage.setItem(CLE_TEXTES_LIBRES, JSON.stringify(textesLibres()));
    localStorage.setItem(CLE_SORTE_LIBRE, libre.sorte);
    localStorage.setItem(CLE_ARTICLE_LIBRE, JSON.stringify(
      { nom: elLibreNom.value, prix: elLibrePrix.value, unite: libre.unite }));
  } catch (e) { /* ignore */ }
}

function rendreLibre() {
  sauverSaisie();
  elLibreAjouter.disabled = elLibreLignes.children.length >= MAX_LIGNES_LIBRES;
  if (!state.styleNormal) {
    elDimsInfo.textContent = SANS_STYLE;
    return;
  }
  const cible = { canvas: elCanvas, cadre: elCadre, info: elDimsInfo };
  if (libre.sorte === 'prix') {
    // Mise en page officielle : le style normal, rempli avec l'article tapé.
    dessinerEtiquette(cible, state.styleNormal, articleSaisi());
  } else {
    dessinerEtiquette(cible, configLibre(state.styleNormal, textesLibres()), null);
  }
}

function choisirSorte(sorte) {
  libre.sorte = sorte === 'prix' ? 'prix' : 'texte';
  document.querySelectorAll('.pe-libre-choix [data-sorte]').forEach(b => {
    const actif = b.dataset.sorte === libre.sorte;
    b.classList.toggle('active', actif);
    b.setAttribute('aria-selected', String(actif));
  });
  $('libre-bloc-texte').hidden = libre.sorte !== 'texte';
  $('libre-bloc-prix').hidden = libre.sorte !== 'prix';
  rendreLibre();
}

function choisirUnite(unite) {
  libre.unite = unite === 'piece' ? 'piece' : 'kg';
  document.querySelectorAll('.pe-libre-unites [data-unite]').forEach(b =>
    b.classList.toggle('active', b.dataset.unite === libre.unite));
  rendreLibre();
}

document.querySelectorAll('.pe-libre-choix [data-sorte]').forEach(b =>
  b.addEventListener('click', () => choisirSorte(b.dataset.sorte)));
document.querySelectorAll('.pe-libre-unites [data-unite]').forEach(b =>
  b.addEventListener('click', () => choisirUnite(b.dataset.unite)));
let minuterieExistants = null;
elLibreNom.addEventListener('input', () => {
  rendreLibre();
  clearTimeout(minuterieExistants);
  minuterieExistants = setTimeout(signalerExistants, 250);
});
elLibrePrix.addEventListener('input', rendreLibre);

function ajouterLigneLibre(texte = '') {
  if (elLibreLignes.children.length >= MAX_LIGNES_LIBRES) return;
  const ligne = document.createElement('div');
  ligne.className = 'pe-libre-ligne';
  ligne.innerHTML = `
    <input type="text" class="pe-input pe-input--grand pe-libre-texte" maxlength="40"
           placeholder="Ex. Arrivage du jour, Fait maison…">
    <button class="pe-icone-btn pe-icone-btn--suppr" title="Retirer cette ligne" aria-label="Retirer">✕</button>`;
  const champ = ligne.querySelector('input');
  champ.value = texte;
  champ.addEventListener('input', rendreLibre);
  ligne.querySelector('button').addEventListener('click', () => {
    if (elLibreLignes.children.length > 1) ligne.remove(); else champ.value = '';
    rendreLibre();
  });
  elLibreLignes.appendChild(ligne);
}

function remplirLignesLibres(textes) {
  elLibreLignes.innerHTML = '';
  (textes.length ? textes : ['']).slice(0, MAX_LIGNES_LIBRES).forEach(t => ajouterLigneLibre(t));
  rendreLibre();
}

elLibreAjouter.addEventListener('click', () => { ajouterLigneLibre(); rendreLibre(); });

// Style normal de la boutique (rechargé à chaque passage sur l'onglet).
async function chargerStyleNormal() {
  try {
    state.styleNormal = (await apiFetch('/api/prix-etiquettes/styles')).normal?.config ?? null;
  } catch (e) {
    console.error('Style :', e);
  }
}

function verifierAvantImpression() {
  if (!state.styleNormal) {
    afficherStatut(SANS_STYLE, 'err');
    return false;
  }
  if (libre.sorte === 'prix') {
    const a = articleSaisi();
    if (!a.nom) { afficherStatut('Tapez le nom de l\'article.', 'err'); elLibreNom.focus(); return false; }
    if (a.prix_vente_ttc == null) {
      afficherStatut('Tapez le prix (ex. 14,90).', 'err'); elLibrePrix.focus(); return false;
    }
    return true;
  }
  if (!textesLibres().some(t => t.trim())) {
    afficherStatut('Tapez au moins une ligne de texte avant d\'imprimer.', 'err');
    return false;
  }
  return true;
}

// Message après une étiquette prix : produit signalé, ou déjà au catalogue.
function messageArticle(rep) {
  if (rep?.existant) return `✓ Étiquette imprimée. « ${rep.existant.nom} » est déjà au catalogue de vente.`;
  if (rep?.demande_id) return '✓ Étiquette imprimée. Le produit est signalé au responsable pour l\'ajouter au catalogue.';
  return '✓ Étiquette imprimée avec succès.';
}

elBtnImprimer.addEventListener('click', async () => {
  if (!verifierAvantImpression()) return;
  elBtnImprimer.disabled = true;
  afficherStatut('Envoi à l\'imprimante…', 'loading');
  try {
    if (libre.sorte === 'prix') {
      const rep = await apiFetch('/api/prix-etiquettes/imprimer-hors-catalogue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(articleSaisi()),
      });
      afficherStatut(messageArticle(rep), 'ok');
    } else {
      // Seul le texte part : le serveur applique le style de la boutique.
      await apiFetch('/api/prix-etiquettes/imprimer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'libre', lignes: textesLibres().map(texte => ({ texte })) }),
      });
      afficherStatut('✓ Étiquette imprimée avec succès.', 'ok');
    }
  } catch (e) {
    afficherStatut('Erreur impression : ' + e.message, 'err');
  } finally {
    elBtnImprimer.disabled = false;
  }
});

// Secours : impression par le navigateur de l'aperçu, à la taille réelle.
elBtnImprimerNav.addEventListener('click', async () => {
  if (!verifierAvantImpression()) return;
  rendreLibre();
  const style = state.styleNormal;
  await imprimerImagesSansPopup([{ src: elCanvas.toDataURL('image/png'), alt: 'Étiquette' }],
    style.largeur_cm, Math.min(style.hauteur_cm, HAUTEUR_MAX_CM), 'Étiquette');
  afficherStatut('Choisissez l\'imprimante dans la fenêtre d\'impression.', 'ok');
  if (libre.sorte === 'prix') {
    noterImpressionNavigateur({ type: 'hors_catalogue', article: articleSaisi() });
  } else {
    noterImpressionNavigateur({ type: 'libre',
      libelle: configLibre(style, textesLibres()).lignes.map(l => l.texte).join('\n') });
  }
});

peVues.libre = {
  async afficher() {
    await chargerStyleNormal();
    libre.catalogue = null;            // relu à la prochaine saisie (produits ajoutés)
    rendreLibre();
  },
};

// Saisie précédente (confort sur la tablette) : sorte, textes, article.
function restaurerLibre(textes, sorteImposee) {
  let article = {}, sorte = sorteImposee;
  try {
    article = JSON.parse(localStorage.getItem(CLE_ARTICLE_LIBRE) || '{}') || {};
    sorte = sorte || localStorage.getItem(CLE_SORTE_LIBRE);
  } catch (e) { /* ignore */ }
  elLibreNom.value = article.nom || '';
  elLibrePrix.value = article.prix || '';
  libre.unite = article.unite === 'piece' ? 'piece' : 'kg';
  document.querySelectorAll('.pe-libre-unites [data-unite]').forEach(b =>
    b.classList.toggle('active', b.dataset.unite === libre.unite));
  remplirLignesLibres(Array.isArray(textes) ? textes : []);
  choisirSorte(sorte || 'texte');
}

// ── Init ──────────────────────────────────────────────────────

async function init() {
  await chargerFontDefaut();   // DejaVu embarquée pour l'aperçu Canvas
  await Promise.all([chargerFonts(), chargerFile(), chargerStyleNormal()]);

  // Textes de la dernière étiquette libre (confort sur la tablette).
  let textes = [];
  try { textes = JSON.parse(localStorage.getItem(CLE_TEXTES_LIBRES) || '[]'); } catch (e) { /* ignore */ }

  // Bouton 🏷️ du catalogue achats : la désignation devient le texte de l'étiquette libre.
  let ongletDepart = null;
  try {
    const raw = sessionStorage.getItem('pe_article_import');
    if (raw) {
      sessionStorage.removeItem('pe_article_import');
      const article = JSON.parse(raw);
      textes = [article.designation || article.nom || ''];
      ongletDepart = 'libre';
    }
  } catch (e) { /* ignore */ }
  restaurerLibre(textes, ongletDepart === 'libre' ? 'texte' : null);

  // Onglet de départ : « Imprimer » quand on arrive pour imprimer (tuile du Hub
  // ?reimprimer, bouton 🏷️ du catalogue de vente ?produit=), sinon le dernier utilisé.
  const params = new URLSearchParams(location.search);
  if (!ongletDepart && !params.has('reimprimer') && !params.has('produit')) {
    try { ongletDepart = localStorage.getItem('pe_onglet'); } catch (e) { /* ignore */ }
  }
  await afficherOnglet(ongletDepart || 'imprimer');
}

// Promesse exposée : les autres scripts de la page (vues Imprimer, Style) peuvent
// attendre la fin du chargement initial (polices, file, style).
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

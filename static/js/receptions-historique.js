'use strict';
/* ============================================================
   receptions-historique.js — Historique des réceptions
   Au Comptoir des Lilas — Mets Carnés Holding
   ============================================================ */

// ── Références DOM ──────────────────────────────────────────
const elHorloge    = document.getElementById('rh-horloge');
const elBtnRetour  = document.getElementById('rh-btn-retour');
const elInputFourn = document.getElementById('rh-input-fourn');
const elAuto       = document.getElementById('rh-autocomplete');
const elDateDebut  = document.getElementById('rh-date-debut');
const elDateFin    = document.getElementById('rh-date-fin');
const elBtnFiltrer = document.getElementById('rh-btn-filtrer');
const elBtnReset   = document.getElementById('rh-btn-reset');
const elCompteur   = document.getElementById('rh-compteur');
const elListe      = document.getElementById('rh-liste');
const elMessage    = document.getElementById('rh-message');
const elMsgIcone   = document.getElementById('rh-message-icone');
const elMsgTexte   = document.getElementById('rh-message-texte');
const elBtnPlus    = document.getElementById('rh-btn-plus');
const elModal      = document.getElementById('rh-modal');
const elModalImg   = document.getElementById('rh-modal-img');

// ── État ────────────────────────────────────────────────────
const LIMIT          = 50;
let offsetCourant    = 0;
let totalCharges     = 0;
let fournisseurIdFiltre = null;
let debounceTimer    = null;
let timerInactivite  = null;

// ── Horloge ─────────────────────────────────────────────────
function majHorloge() {
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();

// ── Inactivité (5 min → hub.html) ───────────────────────────
function resetInactivite() {
  clearTimeout(timerInactivite);
  timerInactivite = setTimeout(() => {
    window.location.href = '/hub.html';
  }, 5 * 60 * 1000);
}
document.addEventListener('click',      resetInactivite, true);
document.addEventListener('touchstart', resetInactivite, { passive: true, capture: true });
document.addEventListener('input',      resetInactivite, true);
resetInactivite();

// ── Fetch helper ────────────────────────────────────────────
async function apiFetch(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} — ${txt || url}`);
  }
  return res.json();
}

// ── Formatage ────────────────────────────────────────────────
function formatDateFR(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
  } catch { return isoStr; }
}

function formatTemp(val) {
  if (val === null || val === undefined) return '—';
  return `${parseFloat(val).toFixed(1)} °C`;
}

// ── Init dates par défaut (7 derniers jours) ─────────────────
function initDates() {
  const auj   = new Date();
  const il7   = new Date();
  il7.setDate(il7.getDate() - 6);
  elDateFin.value   = auj.toISOString().slice(0, 10);
  elDateDebut.value = il7.toISOString().slice(0, 10);
}

// ── Construction URL ─────────────────────────────────────────
function buildUrl(offset = 0) {
  const p = new URLSearchParams();
  p.set('limit',  String(LIMIT));
  p.set('offset', String(offset));
  if (fournisseurIdFiltre !== null) p.set('fournisseur_id', String(fournisseurIdFiltre));
  if (elDateDebut.value) p.set('date_debut', elDateDebut.value);
  if (elDateFin.value)   p.set('date_fin',   elDateFin.value);
  return `/api/receptions?${p.toString()}`;
}

// ── Chargement initial ────────────────────────────────────────
async function charger() {
  offsetCourant = 0;
  totalCharges  = 0;
  elListe.innerHTML = '';
  elBtnPlus.hidden  = true;
  elCompteur.textContent = '';
  afficherMessage('⏳', 'Chargement…');

  try {
    const rows = await apiFetch(buildUrl(0));
    masquerMessage();
    ajouterResultats(rows);
  } catch (err) {
    afficherMessage('⚠️', `Erreur : ${err.message}`);
  }
}

// ── Pagination ────────────────────────────────────────────────
async function chargerSuite() {
  elBtnPlus.disabled = true;
  elBtnPlus.textContent = 'Chargement…';
  try {
    const rows = await apiFetch(buildUrl(offsetCourant));
    ajouterResultats(rows);
  } catch (err) {
    elBtnPlus.disabled = false;
    elBtnPlus.textContent = 'Voir plus…';
    alert(`Erreur de chargement : ${err.message}`);
  }
}

function ajouterResultats(rows) {
  if (rows.length === 0 && totalCharges === 0) {
    afficherMessage('🔍', 'Aucune réception trouvée pour ces critères.');
    return;
  }

  rows.forEach(rec => elListe.appendChild(creerCarte(rec)));

  offsetCourant += rows.length;
  totalCharges  += rows.length;
  majCompteur();

  if (rows.length === LIMIT) {
    elBtnPlus.hidden   = false;
    elBtnPlus.disabled = false;
    elBtnPlus.textContent = 'Voir plus…';
  } else {
    elBtnPlus.hidden = true;
  }
}

function majCompteur() {
  elCompteur.textContent = totalCharges === 1
    ? '1 réception'
    : `${totalCharges} réceptions`;
}

// ── Badge conformité ─────────────────────────────────────────
function badgeConformite(rec) {
  if (rec.livraison_refusee) return { cls: 'rh-badge--refusee', texte: '✗ Refusée' };
  if (rec.nb_nc > 0) return { cls: 'rh-badge--nc', texte: `⚠ ${rec.nb_nc} NC` };
  return { cls: 'rh-badge--ok', texte: '✓ Conforme' };
}

function classeCarte(rec) {
  if (rec.livraison_refusee) return 'rh-carte--refusee';
  if (rec.nb_nc > 0) return 'rh-carte--nc';
  return 'rh-carte--conforme';
}

// ── Création carte (résumé expandable) ───────────────────────
function creerCarte(rec) {
  const carte = document.createElement('div');
  carte.className = `rh-carte ${classeCarte(rec)}`;
  carte.setAttribute('role', 'listitem');

  // --- Bandeau résumé (toujours visible) ---
  const resume = document.createElement('div');
  resume.className = 'rh-carte-resume';

  // Photo BL miniature
  const photoWrap = document.createElement('div');
  photoWrap.className = 'rh-photo-bl';
  if (rec.photo_bl_filename) {
    const img = document.createElement('img');
    img.src    = `/api/receptions/${rec.id}/photo-bl`;
    img.alt    = 'Bon de livraison';
    img.loading = 'lazy';
    photoWrap.appendChild(img);
    photoWrap.addEventListener('click', e => {
      e.stopPropagation();
      ouvrirModal(`/api/receptions/${rec.id}/photo-bl`, 'Bon de livraison');
    });
  } else {
    const ph = document.createElement('div');
    ph.className = 'rh-photo-bl-placeholder';
    ph.textContent = '📋';
    photoWrap.appendChild(ph);
  }
  resume.appendChild(photoWrap);

  // Infos
  const info = document.createElement('div');
  info.className = 'rh-carte-info';

  const entete = document.createElement('div');
  entete.className = 'rh-carte-entete';

  const date = document.createElement('div');
  date.className = 'rh-date';
  date.textContent = formatDateFR(rec.date_reception);
  entete.appendChild(date);

  const b = badgeConformite(rec);
  const badge = document.createElement('span');
  badge.className = `rh-badge ${b.cls}`;
  badge.textContent = b.texte;
  entete.appendChild(badge);
  info.appendChild(entete);

  const meta = document.createElement('div');
  meta.className = 'rh-meta';
  const heure = rec.heure_reception ? ` à ${rec.heure_reception}` : '';
  meta.textContent = `${rec.personnel_prenom || '—'}${heure}`;
  info.appendChild(meta);

  // Chips : fournisseur, nb produits
  const chips = document.createElement('div');
  chips.className = 'rh-chips';

  if (rec.fournisseur_nom) {
    const cf = document.createElement('span');
    cf.className = 'rh-chip';
    cf.textContent = rec.fournisseur_nom;
    chips.appendChild(cf);
  }

  const cp = document.createElement('span');
  cp.className = 'rh-chip';
  cp.textContent = `${rec.nb_lignes || 0} produit${(rec.nb_lignes || 0) > 1 ? 's' : ''}`;
  chips.appendChild(cp);

  if (rec.proprete_camion && rec.proprete_camion !== 'satisfaisant') {
    const cc = document.createElement('span');
    cc.className = 'rh-chip rh-chip--nc';
    cc.textContent = '⚠ Camion NC';
    chips.appendChild(cc);
  }

  if (rec.livraison_refusee) {
    const cr = document.createElement('span');
    cr.className = 'rh-chip rh-chip--refus';
    cr.textContent = '✗ Livraison refusée';
    chips.appendChild(cr);
  }

  info.appendChild(chips);
  resume.appendChild(info);

  // Chevron
  const chev = document.createElement('span');
  chev.className = 'rh-chevron';
  chev.textContent = '▾';
  chev.setAttribute('aria-hidden', 'true');
  resume.appendChild(chev);

  carte.appendChild(resume);

  // --- Détail (caché par défaut, chargé au premier clic) ---
  const detail = document.createElement('div');
  detail.className = 'rh-detail';
  carte.appendChild(detail);

  let detailCharge = false;

  resume.addEventListener('click', async () => {
    carte.classList.toggle('ouvert');
    if (carte.classList.contains('ouvert') && !detailCharge) {
      detailCharge = true;
      detail.innerHTML = '<div style="padding:12px;color:#888;">Chargement…</div>';
      try {
        const rec2 = await apiFetch(`/api/receptions/${rec.id}`);
        remplirDetail(detail, rec2);
      } catch (err) {
        detail.innerHTML = `<div style="padding:12px;color:var(--alerte);">Erreur : ${err.message}</div>`;
      }
    }
  });

  return carte;
}

// ── Remplissage du détail ────────────────────────────────────
function remplirDetail(el, rec) {
  el.innerHTML = '';

  // ── Bouton PCR01 ─────────────────────────────────────────
  const btnPcr = document.createElement('button');
  btnPcr.style.cssText = 'display:block;width:100%;background:var(--alerte,#C93030);color:#FFF;border:none;border-radius:8px;padding:10px;font-size:14px;font-weight:700;cursor:pointer;margin-bottom:12px;';
  btnPcr.textContent = '⚠️ Voir les fiches PCR01';
  btnPcr.addEventListener('click', e => {
    e.stopPropagation();
    window.location.href = `/incidents.html?reception_id=${rec.id}`;
  });
  el.appendChild(btnPcr);

  // Bouton photo BL grande
  if (rec.photo_bl_filename) {
    const btnBl = document.createElement('button');
    btnBl.className = 'rh-detail-bl-btn';
    btnBl.textContent = '📋 Voir le bon de livraison';
    btnBl.addEventListener('click', e => {
      e.stopPropagation();
      ouvrirModal(`/api/receptions/${rec.id}/photo-bl`, 'Bon de livraison');
    });
    el.appendChild(btnBl);
  }

  // Camion
  const titreCamion = document.createElement('div');
  titreCamion.className = 'rh-detail-section-titre';
  titreCamion.textContent = 'Contrôle camion';
  el.appendChild(titreCamion);

  const divCamion = document.createElement('div');
  divCamion.className = 'rh-detail-camion';

  const champsCamion = [
    { label: 'Température',  valeur: formatTemp(rec.temperature_camion) },
    { label: 'Propreté',     valeur: rec.proprete_camion === 'satisfaisant' ? '✓ Satisfaisante' : '✗ Non satisfaisante' },
    { label: 'Heure',        valeur: rec.heure_reception || '—' },
  ];
  champsCamion.forEach(({ label, valeur }) => {
    const div = document.createElement('div');
    div.className = 'rh-camion-info';
    const lbl = document.createElement('span');
    lbl.className = 'rh-camion-label';
    lbl.textContent = label;
    const val = document.createElement('span');
    val.className = 'rh-camion-valeur';
    val.textContent = valeur;
    div.appendChild(lbl);
    div.appendChild(val);
    divCamion.appendChild(div);
  });
  el.appendChild(divCamion);

  // Commentaire NC global
  if (rec.commentaire_nc) {
    const divCmt = document.createElement('div');
    divCmt.className = 'rh-commentaire';
    const lbl = document.createElement('div');
    lbl.className = 'rh-commentaire-label';
    lbl.textContent = 'Commentaire NC';
    const txt = document.createElement('div');
    txt.textContent = rec.commentaire_nc;
    divCmt.appendChild(lbl);
    divCmt.appendChild(txt);
    el.appendChild(divCmt);
  }

  // Lignes produits
  const titreProd = document.createElement('div');
  titreProd.className = 'rh-detail-section-titre';
  titreProd.textContent = `Produits réceptionnés (${(rec.lignes || []).length})`;
  el.appendChild(titreProd);

  const divLignes = document.createElement('div');
  divLignes.className = 'rh-lignes';

  if (!rec.lignes || rec.lignes.length === 0) {
    const vide = document.createElement('div');
    vide.style.cssText = 'padding:8px;color:#888;font-size:15px;';
    vide.textContent = 'Aucun produit enregistré.';
    divLignes.appendChild(vide);
  } else {
    rec.lignes.forEach(lig => divLignes.appendChild(creerLigne(lig)));
  }

  el.appendChild(divLignes);
}

// ── Création ligne produit ────────────────────────────────────
function creerLigne(lig) {
  const estNC = lig.conforme === 0;

  const div = document.createElement('div');
  div.className = `rh-ligne ${estNC ? 'rh-ligne--nc' : ''}`;

  const entete = document.createElement('div');
  entete.className = 'rh-ligne-entete';

  const gauche = document.createElement('div');
  const nom = document.createElement('div');
  nom.className = 'rh-ligne-nom';
  nom.textContent = lig.produit_nom || '—';
  gauche.appendChild(nom);
  if (lig.espece) {
    const esp = document.createElement('div');
    esp.className = 'rh-ligne-espece';
    esp.textContent = lig.espece;
    gauche.appendChild(esp);
  }
  entete.appendChild(gauche);

  const badge = document.createElement('span');
  badge.className = `rh-ligne-badge ${estNC ? 'rh-ligne-badge--nc' : 'rh-ligne-badge--ok'}`;
  badge.textContent = estNC ? '✗ NC' : '✓ OK';
  entete.appendChild(badge);
  div.appendChild(entete);

  // Grille d'infos
  const grille = document.createElement('div');
  grille.className = 'rh-ligne-grille';

  const champs = [
    { label: 'Fournisseur',   valeur: lig.fournisseur_nom || '—' },
    { label: 'N° lot',        valeur: lig.numero_lot || '—' },
    { label: 'DLC',           valeur: formatDateFR(lig.dlc) },
    { label: 'T° réception',  valeur: formatTemp(lig.temperature_reception) },
    { label: 'T° à cœur',     valeur: formatTemp(lig.temperature_coeur) },
  ];
  if (lig.ph_valeur !== null && lig.ph_valeur !== undefined) {
    champs.push({ label: 'pH', valeur: String(lig.ph_valeur) });
  }
  if (lig.poids_kg) {
    champs.push({ label: 'Poids', valeur: `${lig.poids_kg} kg` });
  }

  champs.forEach(({ label, valeur }) => {
    const c = document.createElement('div');
    c.className = 'rh-ligne-champ';
    const lbl = document.createElement('span');
    lbl.className = 'rh-ligne-champ-label';
    lbl.textContent = label;
    const val = document.createElement('span');
    val.className = 'rh-ligne-champ-val';
    val.textContent = valeur;
    c.appendChild(lbl);
    c.appendChild(val);
    grille.appendChild(c);
  });
  div.appendChild(grille);

  // Critères non conformes
  if (estNC) {
    const criteres = [];
    if (lig.couleur_conforme    === 0) criteres.push(`Couleur : ${lig.couleur_observation || 'NC'}`);
    if (lig.consistance_conforme === 0) criteres.push(`Consistance : ${lig.consistance_observation || 'NC'}`);
    if (lig.exsudat_conforme    === 0) criteres.push(`Exsudat : ${lig.exsudat_observation || 'NC'}`);
    if (lig.odeur_conforme      === 0) criteres.push(`Odeur : ${lig.odeur_observation || 'NC'}`);
    if (lig.temperature_conforme === 0) criteres.push('Température hors seuil');
    if (criteres.length) {
      const nc = document.createElement('div');
      nc.className = 'rh-criteres-nc';
      nc.textContent = criteres.join(' — ');
      div.appendChild(nc);
    }
  }

  return div;
}

// ── Modal photo plein écran ──────────────────────────────────
function ouvrirModal(src, alt) {
  elModalImg.src = src;
  elModalImg.alt = alt;
  elModal.hidden = false;
  document.body.style.overflow = 'hidden';
}
function fermerModal() {
  elModal.hidden = true;
  elModalImg.src = '';
  document.body.style.overflow = '';
}
elModal.addEventListener('click', fermerModal);
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !elModal.hidden) fermerModal();
});

// ── Messages ─────────────────────────────────────────────────
function afficherMessage(icone, texte) {
  elMsgIcone.textContent = icone;
  elMsgTexte.textContent = texte;
  elMessage.hidden = false;
}
function masquerMessage() { elMessage.hidden = true; }

// ── Autocomplete fournisseurs ────────────────────────────────
elInputFourn.addEventListener('input', () => {
  fournisseurIdFiltre = null;
  const q = elInputFourn.value.trim();
  if (!q) { elAuto.hidden = true; elAuto.innerHTML = ''; return; }

  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    try {
      const liste = await apiFetch('/api/fournisseurs');
      const ql = q.toLowerCase();
      const filtres = liste.filter(f => f.nom.toLowerCase().includes(ql)).slice(0, 10);
      afficherAuto(filtres);
    } catch { /* silencieux */ }
  }, 300);
});

function afficherAuto(liste) {
  elAuto.innerHTML = '';
  if (!liste.length) { elAuto.hidden = true; return; }
  liste.forEach(f => {
    const item = document.createElement('div');
    item.className = 'rh-ac-item';
    item.setAttribute('role', 'option');
    item.textContent = f.nom;
    item.addEventListener('click', () => {
      fournisseurIdFiltre = f.id;
      elInputFourn.value = f.nom;
      elAuto.hidden = true;
      elAuto.innerHTML = '';
    });
    elAuto.appendChild(item);
  });
  elAuto.hidden = false;
}

document.addEventListener('click', e => {
  if (!elInputFourn.contains(e.target) && !elAuto.contains(e.target)) {
    elAuto.hidden = true;
  }
});

// ── Boutons ──────────────────────────────────────────────────
elBtnFiltrer.addEventListener('click', charger);

elBtnReset.addEventListener('click', () => {
  fournisseurIdFiltre = null;
  elInputFourn.value = '';
  elAuto.hidden = true;
  initDates();
  charger();
});

elBtnPlus.addEventListener('click', chargerSuite);
elBtnRetour.addEventListener('click', () => { window.location.href = '/hub.html'; });

// ── Init ─────────────────────────────────────────────────────
initDates();
charger();

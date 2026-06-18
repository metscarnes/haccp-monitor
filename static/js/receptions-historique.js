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
async function apiFetch(url, opts) {
  const res = await fetch(url, { cache: 'no-store', ...(opts || {}) });
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
function camionNonConforme(rec) {
  return rec.camion_conforme === 0
      || (rec.proprete_camion && rec.proprete_camion !== 'satisfaisant');
}

function badgeConformite(rec) {
  if (rec.livraison_refusee) return { cls: 'rh-badge--refusee', texte: '✗ Refusée' };
  if (rec.nb_nc > 0) return { cls: 'rh-badge--nc', texte: `⚠ ${rec.nb_nc} NC` };
  if (camionNonConforme(rec)) return { cls: 'rh-badge--nc', texte: '⚠ Camion NC' };
  return { cls: 'rh-badge--ok', texte: '✓ Conforme' };
}

function classeCarte(rec) {
  if (rec.livraison_refusee) return 'rh-carte--refusee';
  if (rec.nb_nc > 0 || camionNonConforme(rec)) return 'rh-carte--nc';
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
  // Fournisseurs supplémentaires (BL refus livraison multi)
  (rec.bls_supplementaires_noms || []).forEach(nom => {
    if (!nom) return;
    const cf = document.createElement('span');
    cf.className = 'rh-chip';
    cf.textContent = nom;
    chips.appendChild(cf);
  });

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

  // ── Bouton PCR01 (NC produit ou NC propreté camion) ──
  const nbNc = (rec.lignes || []).filter(l => l.conforme === 0).length;
  if (nbNc > 0 || camionNonConforme(rec)) {
    const btnPcr = document.createElement('button');
    btnPcr.style.cssText = 'display:block;width:100%;background:var(--alerte,#C93030);color:#FFF;border:none;border-radius:8px;padding:10px;font-size:14px;font-weight:700;cursor:pointer;margin-bottom:12px;';
    btnPcr.textContent = '⚠️ Voir les fiches PCR01';
    btnPcr.addEventListener('click', e => {
      e.stopPropagation();
      window.location.href = `/incidents.html?reception_id=${rec.id}`;
    });
    el.appendChild(btnPcr);
  }

  // ── Photos BL multi-pages (nouveau système) ──
  const zoneBlPages = document.createElement('div');
  zoneBlPages.style.cssText = 'margin-bottom:8px;';
  el.appendChild(zoneBlPages);
  chargerBlPagesHistorique(rec.id, zoneBlPages);

  // Boutons photos BL ancienne API (principal + supplémentaires multi-fournisseur)
  const blsSupp = Array.isArray(rec.bls_supplementaires) ? rec.bls_supplementaires : [];
  if (rec.photo_bl_filename) {
    const btnBl = document.createElement('button');
    btnBl.className = 'rh-detail-bl-btn';
    btnBl.textContent = blsSupp.length
      ? `📋 BL — ${rec.fournisseur_nom || 'Fournisseur principal'}`
      : '📋 Voir le bon de livraison';
    btnBl.addEventListener('click', e => {
      e.stopPropagation();
      ouvrirModal(`/api/receptions/${rec.id}/photo-bl`, 'Bon de livraison');
    });
    el.appendChild(btnBl);
  }
  blsSupp.forEach(b => {
    if (!b.photo_bl_filename) return;
    const btn = document.createElement('button');
    btn.className = 'rh-detail-bl-btn';
    btn.textContent = `📋 BL — ${b.fournisseur_nom || 'Fournisseur'}`;
    btn.addEventListener('click', e => {
      e.stopPropagation();
      ouvrirModal(`/api/receptions/${rec.id}/bls-supplementaires/${b.id}/photo`, btn.textContent);
    });
    el.appendChild(btn);
  });

  if (rec.proprete_photo_filename) {
    const btnProp = document.createElement('button');
    btnProp.className = 'rh-detail-bl-btn';
    btnProp.textContent = '📸 Photo NC propreté camion';
    btnProp.addEventListener('click', e => {
      e.stopPropagation();
      ouvrirModal(`/api/receptions/${rec.id}/photo-proprete`, 'Photo NC propreté camion');
    });
    el.appendChild(btnProp);
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

  // ── Annuler la réception ───────────────────────────────────
  const btnAnnuler = document.createElement('button');
  btnAnnuler.style.cssText = 'display:block;width:100%;background:#C93030;color:#FFF;border:none;border-radius:8px;padding:10px;font-size:14px;font-weight:700;cursor:pointer;margin-top:16px;';
  btnAnnuler.textContent = '🗑️ Annuler cette réception';
  btnAnnuler.addEventListener('click', e => {
    e.stopPropagation();
    annulerReception(rec, btnAnnuler);
  });
  el.appendChild(btnAnnuler);
}

// ── Annulation d'une réception ────────────────────────────────
async function annulerReception(rec, btn) {
  const date = formatDateFR(rec.date_reception);
  const fourn = rec.fournisseur_nom ? ` — ${rec.fournisseur_nom}` : '';
  if (!confirm(
    `Annuler la réception du ${date}${fourn} ?\n\n` +
    `Tous les produits réceptionnés seront retirés du stock et la commande liée ` +
    `redeviendra sélectionnable dans le module réception.\n\n` +
    `Cette action est irréversible.`
  )) return;

  btn.disabled = true;
  const ancien = btn.textContent;
  btn.textContent = 'Annulation…';
  try {
    const res = await fetch(`/api/receptions/${rec.id}`, { method: 'DELETE', cache: 'no-store' });
    if (res.status === 409) {
      const txt = await res.text().catch(() => '');
      let detail = txt;
      try { detail = JSON.parse(txt).detail || txt; } catch (_) {}
      alert(`Impossible d'annuler cette réception.\n\n${detail}`);
      btn.disabled = false;
      btn.textContent = ancien;
      return;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    // Succès : recharger l'historique depuis le début
    await charger();
  } catch (err) {
    alert(`Erreur lors de l'annulation : ${err.message}`);
    btn.disabled = false;
    btn.textContent = ancien;
  }
}

// ── Création ligne produit ────────────────────────────────────
function creerLigne(lig) {
  const estNC      = lig.conforme === 0;
  const enAttente  = lig.statut === 'en_attente';
  const nonRecu    = lig.statut === 'non_recu';

  const div = document.createElement('div');
  div.className = `rh-ligne ${estNC ? 'rh-ligne--nc' : ''}`;
  const couleurBord = nonRecu ? '#6B7280' : enAttente ? '#B91C1C' : (estNC ? '#C93030' : '#2D7D46');
  div.style.cssText = `border: 3px solid ${couleurBord}; border-radius: 8px; padding: 12px; ${nonRecu ? 'opacity:.65;' : ''}`;

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
  if (nonRecu) {
    badge.className = 'rh-ligne-badge';
    badge.style.cssText = 'background:#6B7280;color:#FFF;';
    badge.textContent = '✗ Non reçu';
  } else if (enAttente) {
    badge.className = 'rh-ligne-badge rh-ligne-badge--nc';
    badge.textContent = '⛔ En attente';
  } else {
    badge.className = `rh-ligne-badge ${estNC ? 'rh-ligne-badge--nc' : 'rh-ligne-badge--ok'}`;
    badge.textContent = estNC ? '✗ NC' : '✓ OK';
  }
  entete.appendChild(badge);
  div.appendChild(entete);

  // Grille d'infos
  const grille = document.createElement('div');
  grille.className = 'rh-ligne-grille';

  const dateLabel = lig.dlc_type === 'date_abattage' ? "Date abattage"
                  : lig.dlc_type === 'no_dlc'        ? null
                  : 'DLC';
  const dateValeur = lig.dlc_type === 'date_abattage'
    ? formatDateFR(lig.date_abattage)
    : formatDateFR(lig.dlc);

  const champs = [
    { label: 'Fournisseur',   valeur: lig.fournisseur_nom || '—' },
    { label: 'N° lot',        valeur: lig.numero_lot || '—' },
    { label: 'Origine',       valeur: lig.origine || '—' },
    ...(dateLabel ? [{ label: dateLabel, valeur: dateValeur }] : []),
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

  // Produit en attente : mini-formulaire de complétion lot/DLC (ou date d'abattage)
  if (enAttente && !nonRecu) {
    div.appendChild(creerFormCompletion(lig));
  }

  return div;
}

// ── Mini-formulaire de complétion d'un produit en attente ─────
function creerFormCompletion(lig) {
  const dateAbattage = lig.dlc_type === 'date_abattage';
  const noDlc        = lig.dlc_type === 'no_dlc';

  const wrap = document.createElement('div');
  wrap.style.cssText = 'margin-top:10px;padding-top:10px;border-top:1px dashed #B91C1C;display:flex;flex-direction:column;gap:8px;';

  const champLabel = (txt) => {
    const l = document.createElement('div');
    l.style.cssText = 'font-size:12px;font-weight:700;color:#6B3A1F;text-transform:uppercase;letter-spacing:.04em;';
    l.textContent = txt;
    return l;
  };
  const mkInput = (type, field, value, ph) => {
    const i = document.createElement('input');
    i.type = type;
    i.dataset.field = field;
    if (value) i.value = String(value).slice(0, 10);
    if (ph) i.placeholder = ph;
    i.style.cssText = 'border:2px solid #6B3A1F;border-radius:8px;font-size:16px;height:46px;padding:0 10px;width:100%;';
    return i;
  };

  wrap.appendChild(champLabel('N° de lot'));
  const inpLot = mkInput('text', 'numero_lot', lig.numero_lot, 'N° de lot…');
  wrap.appendChild(inpLot);

  let inpDate = null;
  if (!noDlc) {
    wrap.appendChild(champLabel(dateAbattage ? "Date d'abattage" : 'DLC'));
    inpDate = mkInput('date', dateAbattage ? 'date_abattage' : 'dlc',
                      dateAbattage ? lig.date_abattage : lig.dlc, null);
    wrap.appendChild(inpDate);
  }

  const erreur = document.createElement('div');
  erreur.style.cssText = 'color:#C93030;font-size:13px;font-weight:600;';
  erreur.hidden = true;

  const btn = document.createElement('button');
  btn.type = 'button';
  btn.textContent = '✓ Compléter et entrer en stock';
  btn.style.cssText = 'background:#2D7D46;border:none;border-radius:8px;color:#fff;font-size:16px;font-weight:700;height:48px;cursor:pointer;';

  btn.addEventListener('click', async () => {
    erreur.hidden = true;
    const payload = {};
    const lot = inpLot.value.trim();
    if (lot) payload.numero_lot = lot;
    if (inpDate && inpDate.value.trim()) payload[inpDate.dataset.field] = inpDate.value.trim();

    if (!lot || (inpDate && !inpDate.value.trim())) {
      erreur.textContent = 'Renseignez le N° de lot et la date.';
      erreur.hidden = false;
      return;
    }
    btn.disabled = true;
    btn.textContent = 'Validation…';
    try {
      const res = await apiFetch(`/api/attente/lignes/${lig.ligne_id || lig.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.statut === 'complet') {
        // Recharger pour refléter le nouvel état (badge OK, plus de formulaire)
        location.reload();
      } else {
        erreur.textContent = 'Information encore incomplète.';
        erreur.hidden = false;
        btn.disabled = false;
        btn.textContent = '✓ Compléter et entrer en stock';
      }
    } catch (e) {
      erreur.textContent = 'Erreur d’enregistrement. Réessayez.';
      erreur.hidden = false;
      btn.disabled = false;
      btn.textContent = '✓ Compléter et entrer en stock';
    }
  });

  wrap.appendChild(btn);
  wrap.appendChild(erreur);
  return wrap;
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

// ── Pages BL multi-pages (produits-attente + historique) ─────
// Charge et affiche les vignettes de pages BL pour une réception,
// avec bouton d'ajout (caméra ou fichier via camera.js).
async function chargerBlPagesHistorique(receptionId, zone) {
  zone.innerHTML = '<span style="font-size:13px;color:#888;">Chargement BL…</span>';

  let data;
  try {
    data = await apiFetch(`/api/receptions/${receptionId}/bl-apercu`);
  } catch {
    zone.innerHTML = '';
    return;
  }

  const pages = data.pages || [];
  zone.innerHTML = '';

  if (pages.length) {
    const label = document.createElement('div');
    label.style.cssText = 'font-size:12px;font-weight:700;color:#6B3A1F;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px;';
    label.textContent = `📎 BL — ${pages.length} page(s)`;
    zone.appendChild(label);

    const strip = document.createElement('div');
    strip.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;';

    const urls = pages.map(p => p.url);
    pages.forEach((p, idx) => {
      const wrapper = document.createElement('div');
      wrapper.style.cssText = 'position:relative;display:inline-block;';

      const img = document.createElement('img');
      img.src   = p.url;
      img.alt   = `BL page ${idx + 1}`;
      img.title = `Voir la page ${idx + 1}`;
      img.style.cssText = 'width:54px;height:54px;object-fit:cover;border-radius:8px;border:2px solid #6B3A1F;cursor:pointer;background:#f0e6d2;display:block;';
      img.addEventListener('click', e => {
        e.stopPropagation();
        ouvrirViewerPages(urls, idx);
      });
      wrapper.appendChild(img);

      // Bouton supprimer (coin haut-droit)
      if (p.page_id) {
        const btnSup = document.createElement('button');
        btnSup.type = 'button';
        btnSup.textContent = '✕';
        btnSup.style.cssText = 'position:absolute;top:-8px;right:-8px;background:#C93030;color:#FFF;border:none;border-radius:50%;width:24px;height:24px;font-size:14px;font-weight:700;cursor:pointer;padding:0;line-height:1;';
        btnSup.title = 'Supprimer cette page';
        btnSup.addEventListener('click', async e => {
          e.stopPropagation();
          if (!confirm('Supprimer cette page de BL ?')) return;
          btnSup.disabled = true;
          try {
            await apiFetch(`/api/receptions/${receptionId}/bl-pages/${p.page_id}`, { method: 'DELETE' });
            await chargerBlPagesHistorique(receptionId, zone);
          } catch (err) {
            alert('Suppression impossible : ' + err.message);
            btnSup.disabled = false;
          }
        });
        wrapper.appendChild(btnSup);
      }

      strip.appendChild(wrapper);
    });
    zone.appendChild(strip);
  }

  // Bouton d'ajout d'une nouvelle page
  const input = document.createElement('input');
  input.type   = 'file';
  input.accept = 'image/*,application/pdf';
  input.hidden = true;

  const btnAjout = document.createElement('button');
  btnAjout.type      = 'button';
  btnAjout.style.cssText = 'background:#FFF;border:2px dashed #6B3A1F;border-radius:8px;color:#6B3A1F;cursor:pointer;font-size:13px;font-weight:700;height:48px;padding:0 14px;white-space:nowrap;';
  btnAjout.textContent = '＋ Ajouter une page BL';

  btnAjout.addEventListener('click', e => {
    e.stopPropagation();
    input.value = '';
    if (typeof ouvrirChoixPhoto === 'function') {
      ouvrirChoixPhoto(input);
    } else {
      input.click();
    }
  });

  input.addEventListener('change', async () => {
    const file = input.files[0];
    if (!file) return;
    btnAjout.disabled    = true;
    btnAjout.textContent = '⏳ Envoi…';
    const fd = new FormData();
    fd.append('fichier', file, file.name);
    try {
      await apiFetch(`/api/receptions/${receptionId}/bl-pages`, { method: 'POST', body: fd });
      await chargerBlPagesHistorique(receptionId, zone);
    } catch (err) {
      btnAjout.disabled    = false;
      btnAjout.textContent = '＋ Ajouter une page BL';
      alert('Ajout impossible : ' + err.message);
    }
    input.value = '';
  });

  zone.appendChild(btnAjout);
  zone.appendChild(input);
}

// Viewer plein écran pages BL (utilisé dans l'historique — produits-attente a le sien)
function ouvrirViewerPages(urls, startIdx) {
  let idx = startIdx;

  const ov = document.createElement('div');
  ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:200;display:flex;flex-direction:column;';

  const barre = document.createElement('div');
  barre.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:12px 16px;color:#FFF;font-weight:700;gap:12px;';

  const btnFerm = document.createElement('button');
  btnFerm.textContent = '✕ Fermer';
  btnFerm.style.cssText = 'background:rgba(255,255,255,.15);border:2px solid rgba(255,255,255,.5);border-radius:8px;color:#FFF;cursor:pointer;font-size:16px;font-weight:700;height:44px;padding:0 16px;';

  const titre = document.createElement('span');

  const nav = document.createElement('div');
  nav.style.cssText = 'display:flex;gap:8px;';

  const btnPrec = document.createElement('button');
  btnPrec.textContent = '‹';
  btnPrec.style.cssText = 'background:rgba(255,255,255,.15);border:2px solid rgba(255,255,255,.5);border-radius:8px;color:#FFF;cursor:pointer;font-size:18px;font-weight:700;height:44px;width:52px;';

  const btnSuiv = document.createElement('button');
  btnSuiv.textContent = '›';
  btnSuiv.style.cssText = btnPrec.style.cssText;

  nav.appendChild(btnPrec);
  nav.appendChild(btnSuiv);
  barre.appendChild(btnFerm);
  barre.appendChild(titre);
  barre.appendChild(nav);

  const imgWrap = document.createElement('div');
  imgWrap.style.cssText = 'flex:1;display:flex;align-items:center;justify-content:center;overflow:auto;padding:8px;';
  const img = document.createElement('img');
  img.style.cssText = 'max-width:100%;max-height:100%;object-fit:contain;';
  imgWrap.appendChild(img);

  ov.appendChild(barre);
  ov.appendChild(imgWrap);
  document.body.appendChild(ov);

  function majViewer() {
    img.src = urls[idx] || '';
    titre.textContent = `Page ${idx + 1} / ${urls.length}`;
    btnPrec.disabled = idx <= 0;
    btnSuiv.disabled = idx >= urls.length - 1;
  }
  function fermer() { ov.remove(); }

  btnFerm.addEventListener('click', fermer);
  btnPrec.addEventListener('click', () => { if (idx > 0) { idx--; majViewer(); } });
  btnSuiv.addEventListener('click', () => { if (idx < urls.length - 1) { idx++; majViewer(); } });
  ov.addEventListener('click', e => { if (e.target === ov || e.target === imgWrap) fermer(); });
  document.addEventListener('keydown', function handler(e) {
    if (e.key === 'Escape') { fermer(); document.removeEventListener('keydown', handler); }
    else if (e.key === 'ArrowLeft'  && idx > 0) { idx--; majViewer(); }
    else if (e.key === 'ArrowRight' && idx < urls.length - 1) { idx++; majViewer(); }
  });

  majViewer();
}

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

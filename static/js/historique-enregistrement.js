'use strict';
/* ============================================================
   historique-enregistrement.js — Onglets Ouvertures & Réceptions
   Au Comptoir des Lilas — Mets Carnés Holding
   ============================================================ */

// ── Références DOM communes ──────────────────────────────────
const elHorloge = document.getElementById('he-horloge');
const elBtnRetour = document.getElementById('he-btn-retour');
const elTabOuv = document.getElementById('he-tab-ouv');
const elTabRec = document.getElementById('he-tab-rec');
const elTabFab = document.getElementById('he-tab-fab');
const elTabNett = document.getElementById('he-tab-nett');
const elContentOuv = document.getElementById('he-content-ouv');
const elContentRec = document.getElementById('he-content-rec');
const elContentFab = document.getElementById('he-content-fab');
const elContentNett = document.getElementById('he-content-nett');

// ── Onglet Ouvertures ────────────────────────────────────────
const ouvRefs = {
  input: document.getElementById('he-ouv-produit'),
  auto: document.getElementById('he-ouv-auto'),
  debut: document.getElementById('he-ouv-debut'),
  fin: document.getElementById('he-ouv-fin'),
  filtrer: document.getElementById('he-ouv-filtrer'),
  reset: document.getElementById('he-ouv-reset'),
  compteur: document.getElementById('he-ouv-compteur'),
  liste: document.getElementById('he-ouv-liste'),
  message: document.getElementById('he-ouv-message'),
  icone: document.getElementById('he-ouv-icone'),
  texte: document.getElementById('he-ouv-texte'),
  plus: document.getElementById('he-ouv-plus'),
};

// ── Onglet Fabrications ──────────────────────────────────────
const fabRefs = {
  debut:    document.getElementById('he-fab-debut'),
  fin:      document.getElementById('he-fab-fin'),
  filtrer:  document.getElementById('he-fab-filtrer'),
  reset:    document.getElementById('he-fab-reset'),
  compteur: document.getElementById('he-fab-compteur'),
  liste:    document.getElementById('he-fab-liste'),
  message:  document.getElementById('he-fab-message'),
  icone:    document.getElementById('he-fab-icone'),
  texte:    document.getElementById('he-fab-texte'),
  plus:     document.getElementById('he-fab-plus'),
};

// ── Onglet Réceptions ────────────────────────────────────────
const recRefs = {
  input: document.getElementById('he-rec-fourn'),
  auto: document.getElementById('he-rec-auto'),
  debut: document.getElementById('he-rec-debut'),
  fin: document.getElementById('he-rec-fin'),
  filtrer: document.getElementById('he-rec-filtrer'),
  reset: document.getElementById('he-rec-reset'),
  compteur: document.getElementById('he-rec-compteur'),
  liste: document.getElementById('he-rec-liste'),
  message: document.getElementById('he-rec-message'),
  icone: document.getElementById('he-rec-icone'),
  texte: document.getElementById('he-rec-texte'),
  plus: document.getElementById('he-rec-plus'),
};

// Modal
const elModal = document.getElementById('he-modal');
const elModalImg = document.getElementById('he-modal-img');

// ── État ─────────────────────────────────────────────────────
const ouvState = {
  produitId: null,
  offset: 0,
  totalCharges: 0,
  debounce: null,
  inactivite: null,
};

const recState = {
  fournisseurId: null,
  offset: 0,
  totalCharges: 0,
  debounce: null,
  inactivite: null,
};

const fabState = {
  offset: 0,
  totalCharges: 0,
  charge: false,   // true une fois le 1er chargement effectué
};

const LIMIT = 50;

// ── Horloge ──────────────────────────────────────────────────
function majHorloge() {
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();

// ── Inactivité ───────────────────────────────────────────────
function resetInactivite() {
  clearTimeout(ouvState.inactivite);
  clearTimeout(recState.inactivite);
  ouvState.inactivite = setTimeout(() => {
    window.location.href = '/hub.html';
  }, 5 * 60 * 1000);
  recState.inactivite = setTimeout(() => {
    window.location.href = '/hub.html';
  }, 5 * 60 * 1000);
}
document.addEventListener('click',      resetInactivite, true);
document.addEventListener('touchstart', resetInactivite, { passive: true, capture: true });
document.addEventListener('input',      resetInactivite, true);
resetInactivite();

// ── Fetch helper ─────────────────────────────────────────────
async function apiFetch(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
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

function formatDateHeureFR(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    const date = d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    const heure = d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    return `${date} à ${heure}`;
  } catch { return isoStr; }
}

function formatTemp(val) {
  if (val === null || val === undefined) return '—';
  return `${parseFloat(val).toFixed(1)} °C`;
}

// ── Onglets ──────────────────────────────────────────────────
function initDates(refs) {
  const auj = new Date();
  const il7 = new Date();
  il7.setDate(il7.getDate() - 6);
  refs.fin.value   = auj.toISOString().slice(0, 10);
  refs.debut.value = il7.toISOString().slice(0, 10);
}

const TOUS_TABS = [
  { btn: elTabOuv,  content: elContentOuv  },
  { btn: elTabRec,  content: elContentRec  },
  { btn: elTabFab,  content: elContentFab  },
  { btn: elTabNett, content: elContentNett },
];

function basculerTab(tabNouveau, contentNouveau) {
  TOUS_TABS.forEach(({ btn, content }) => {
    const actif = btn === tabNouveau;
    btn.classList.toggle('actif', actif);
    btn.setAttribute('aria-selected', String(actif));
    content.classList.toggle('actif', actif);
  });
}

elTabOuv.addEventListener('click', () => basculerTab(elTabOuv, elContentOuv));
elTabRec.addEventListener('click', () => basculerTab(elTabRec, elContentRec));
elTabFab.addEventListener('click', () => {
  basculerTab(elTabFab, elContentFab);
  if (!fabState.charge) fabCharger();
});

elTabNett.addEventListener('click', () => {
  basculerTab(elTabNett, elContentNett);
  if (!nettState.charge) nettCharger();
});

// ══════════════════════════════════════════════════════════════
// ONGLET OUVERTURES
// ══════════════════════════════════════════════════════════════

function ouvBuildUrl(offset = 0) {
  const p = new URLSearchParams();
  p.set('limit', String(LIMIT));
  p.set('offset', String(offset));
  if (ouvState.produitId !== null) p.set('produit_id', String(ouvState.produitId));
  if (ouvRefs.debut.value) p.set('date_debut', ouvRefs.debut.value);
  if (ouvRefs.fin.value) p.set('date_fin', ouvRefs.fin.value);
  return `/api/ouvertures?${p.toString()}`;
}

async function ouvCharger() {
  ouvState.offset = 0;
  ouvState.totalCharges = 0;
  ouvRefs.liste.innerHTML = '';
  ouvRefs.plus.hidden = true;
  ouvRefs.compteur.textContent = '';
  ouvAfficherMessage('⏳', 'Chargement…');

  try {
    const rows = await apiFetch(ouvBuildUrl(0));
    ouvMasquerMessage();
    ouvAjouterResultats(rows);
  } catch (err) {
    ouvAfficherMessage('⚠️', `Erreur : ${err.message}`);
  }
}

async function ouvChargerSuite() {
  ouvRefs.plus.disabled = true;
  ouvRefs.plus.textContent = 'Chargement…';
  try {
    const rows = await apiFetch(ouvBuildUrl(ouvState.offset));
    ouvAjouterResultats(rows);
  } catch (err) {
    ouvRefs.plus.disabled = false;
    ouvRefs.plus.textContent = 'Voir plus…';
    alert(`Erreur : ${err.message}`);
  }
}

function ouvAjouterResultats(rows) {
  if (rows.length === 0 && ouvState.totalCharges === 0) {
    ouvAfficherMessage('🔍', 'Aucune ouverture trouvée.');
    return;
  }

  rows.forEach(ouv => ouvRefs.liste.appendChild(ouvCreerCarte(ouv)));

  ouvState.offset += rows.length;
  ouvState.totalCharges += rows.length;
  ouvMajCompteur();

  if (rows.length === LIMIT) {
    ouvRefs.plus.hidden = false;
    ouvRefs.plus.disabled = false;
    ouvRefs.plus.textContent = 'Voir plus…';
  } else {
    ouvRefs.plus.hidden = true;
  }
}

function ouvMajCompteur() {
  ouvRefs.compteur.textContent = ouvState.totalCharges === 1
    ? '1 ouverture'
    : `${ouvState.totalCharges} ouvertures`;
}

function ouvAfficherMessage(icone, texte) {
  ouvRefs.icone.textContent = icone;
  ouvRefs.texte.textContent = texte;
  ouvRefs.message.hidden = false;
}
function ouvMasquerMessage() { ouvRefs.message.hidden = true; }

function ouvCreerCarte(ouv) {
  const estTracee = ouv.reception_ligne_id !== null && ouv.fournisseur_nom !== null;

  const carte = document.createElement('div');
  carte.className = 'he-carte-ouv ' + (estTracee ? 'he-carte-ouv--tracee' : 'he-carte-ouv--manuelle');
  carte.setAttribute('role', 'listitem');

  const photoWrap = document.createElement('div');
  photoWrap.className = 'he-photo-ouv';
  photoWrap.setAttribute('role', 'button');
  photoWrap.tabIndex = 0;

  if (ouv.photo_filename) {
    const img = document.createElement('img');
    img.src = `/api/ouvertures/${ouv.id}/photo`;
    img.alt = `Photo ouverture ${ouv.produit_nom}`;
    img.loading = 'lazy';
    photoWrap.appendChild(img);
  } else {
    const ph = document.createElement('div');
    ph.className = 'he-photo-ouv-placeholder';
    ph.textContent = '📷';
    photoWrap.appendChild(ph);
  }

  photoWrap.addEventListener('click', () => ouvrirModal(ouv.id, ouv.produit_nom));
  photoWrap.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') ouvrirModal(ouv.id, ouv.produit_nom);
  });

  const corps = document.createElement('div');
  corps.className = 'he-carte-ouv-corps';

  const entete = document.createElement('div');
  entete.className = 'he-carte-ouv-entete';

  const nom = document.createElement('div');
  nom.className = 'he-produit-nom';
  nom.textContent = ouv.produit_nom;
  entete.appendChild(nom);

  const badge = document.createElement('span');
  badge.className = 'he-badge ' + (estTracee ? 'he-badge--ok' : 'he-badge--attention');
  badge.textContent = estTracee ? '✓ Traçabilité' : '⚠ Manuelle';
  entete.appendChild(badge);

  corps.appendChild(entete);

  if (ouv.produit_espece) {
    const espece = document.createElement('div');
    espece.className = 'he-produit-espece';
    espece.textContent = ouv.produit_espece;
    corps.appendChild(espece);
  }

  const meta = document.createElement('div');
  meta.className = 'he-meta';
  meta.textContent = `${formatDateHeureFR(ouv.timestamp)} — ${ouv.personnel_prenom}`;
  corps.appendChild(meta);

  if (estTracee) {
    const infos = document.createElement('div');
    infos.className = 'he-reception-infos';

    const champs = [
      { label: 'Fournisseur',      valeur: ouv.fournisseur_nom },
      { label: 'N° lot',           valeur: ouv.numero_lot || '—' },
      { label: 'DLC fournisseur',  valeur: formatDateFR(ouv.dlc_fournisseur) },
      { label: 'Origine',          valeur: ouv.origine || '—' },
      { label: 'Date réception',   valeur: formatDateFR(ouv.date_reception) },
    ];

    champs.forEach(({ label, valeur }) => {
      const ligne = document.createElement('div');
      ligne.className = 'he-info-ligne';
      const lbl = document.createElement('span');
      lbl.className = 'he-info-label';
      lbl.textContent = label;
      const val = document.createElement('span');
      val.className = 'he-info-valeur';
      val.textContent = valeur;
      ligne.appendChild(lbl);
      ligne.appendChild(val);
      infos.appendChild(ligne);
    });

    corps.appendChild(infos);
  }

  carte.appendChild(photoWrap);
  carte.appendChild(corps);
  return carte;
}

// ── Autocomplete ouvertures ──────────────────────────────────
ouvRefs.input.addEventListener('input', () => {
  ouvState.produitId = null;
  const q = ouvRefs.input.value.trim();
  if (!q) { ouvRefs.auto.hidden = true; ouvRefs.auto.innerHTML = ''; return; }

  clearTimeout(ouvState.debounce);
  ouvState.debounce = setTimeout(async () => {
    try {
      const res = await apiFetch(`/api/ouvertures/suggestions?q=${encodeURIComponent(q)}`);
      ouvAfficherAuto(res);
    } catch { /* silencieux */ }
  }, 300);
});

function ouvAfficherAuto(liste) {
  ouvRefs.auto.innerHTML = '';
  if (!liste.length) { ouvRefs.auto.hidden = true; return; }
  liste.slice(0, 10).forEach(p => {
    const item = document.createElement('div');
    item.className = 'he-ac-item';
    item.setAttribute('role', 'option');
    const nom = document.createElement('div');
    nom.style.fontWeight = '600';
    nom.textContent = p.nom;
    item.appendChild(nom);
    if (p.espece) {
      const esp = document.createElement('div');
      esp.style.fontSize = '13px';
      esp.style.color = '#666';
      esp.textContent = p.espece;
      item.appendChild(esp);
    }
    item.addEventListener('click', () => {
      ouvState.produitId = p.produit_id;
      ouvRefs.input.value = p.nom;
      ouvRefs.auto.hidden = true;
      ouvRefs.auto.innerHTML = '';
    });
    ouvRefs.auto.appendChild(item);
  });
  ouvRefs.auto.hidden = false;
}

document.addEventListener('click', e => {
  if (!ouvRefs.input.contains(e.target) && !ouvRefs.auto.contains(e.target)) {
    ouvRefs.auto.hidden = true;
  }
});

// ── Boutons ouvertures ───────────────────────────────────────
ouvRefs.filtrer.addEventListener('click', ouvCharger);
ouvRefs.reset.addEventListener('click', () => {
  ouvState.produitId = null;
  ouvRefs.input.value = '';
  ouvRefs.auto.hidden = true;
  initDates(ouvRefs);
  ouvCharger();
});
ouvRefs.plus.addEventListener('click', ouvChargerSuite);

// ══════════════════════════════════════════════════════════════
// ONGLET RÉCEPTIONS
// ══════════════════════════════════════════════════════════════

function recBuildUrl(offset = 0) {
  const p = new URLSearchParams();
  p.set('limit', String(LIMIT));
  p.set('offset', String(offset));
  if (recState.fournisseurId !== null) p.set('fournisseur_id', String(recState.fournisseurId));
  if (recRefs.debut.value) p.set('date_debut', recRefs.debut.value);
  if (recRefs.fin.value) p.set('date_fin', recRefs.fin.value);
  return `/api/receptions?${p.toString()}`;
}

async function recCharger() {
  recState.offset = 0;
  recState.totalCharges = 0;
  recRefs.liste.innerHTML = '';
  recRefs.plus.hidden = true;
  recRefs.compteur.textContent = '';
  recAfficherMessage('⏳', 'Chargement…');

  try {
    const rows = await apiFetch(recBuildUrl(0));
    recMasquerMessage();
    recAjouterResultats(rows);
  } catch (err) {
    recAfficherMessage('⚠️', `Erreur : ${err.message}`);
  }
}

async function recChargerSuite() {
  recRefs.plus.disabled = true;
  recRefs.plus.textContent = 'Chargement…';
  try {
    const rows = await apiFetch(recBuildUrl(recState.offset));
    recAjouterResultats(rows);
  } catch (err) {
    recRefs.plus.disabled = false;
    recRefs.plus.textContent = 'Voir plus…';
    alert(`Erreur : ${err.message}`);
  }
}

function recAjouterResultats(rows) {
  if (rows.length === 0 && recState.totalCharges === 0) {
    recAfficherMessage('🔍', 'Aucune réception trouvée.');
    return;
  }

  rows.forEach(rec => recRefs.liste.appendChild(recCreerCarte(rec)));

  recState.offset += rows.length;
  recState.totalCharges += rows.length;
  recMajCompteur();

  if (rows.length === LIMIT) {
    recRefs.plus.hidden = false;
    recRefs.plus.disabled = false;
    recRefs.plus.textContent = 'Voir plus…';
  } else {
    recRefs.plus.hidden = true;
  }
}

function recMajCompteur() {
  recRefs.compteur.textContent = recState.totalCharges === 1
    ? '1 réception'
    : `${recState.totalCharges} réceptions`;
}

function recAfficherMessage(icone, texte) {
  recRefs.icone.textContent = icone;
  recRefs.texte.textContent = texte;
  recRefs.message.hidden = false;
}
function recMasquerMessage() { recRefs.message.hidden = true; }

function recBadgeConformite(rec) {
  if (rec.livraison_refusee) return { cls: 'he-badge--attention', txt: '✗ Refusée' };
  if (rec.nb_nc > 0) return { cls: 'he-badge--attention', txt: `⚠ ${rec.nb_nc} NC` };
  return { cls: 'he-badge--ok', txt: '✓ OK' };
}

function recClasseCarte(rec) {
  if (rec.livraison_refusee) return 'he-carte-rec--refusee';
  if (rec.nb_nc > 0) return 'he-carte-rec--nc';
  return 'he-carte-rec--conforme';
}

function recCreerCarte(rec) {
  const carte = document.createElement('div');
  carte.className = `he-carte-rec ${recClasseCarte(rec)}`;
  carte.setAttribute('role', 'listitem');

  const resume = document.createElement('div');
  resume.className = 'he-carte-rec-resume';

  const photoWrap = document.createElement('div');
  photoWrap.className = 'he-photo-rec';
  if (rec.photo_bl_filename) {
    const img = document.createElement('img');
    img.src = `/api/receptions/${rec.id}/photo-bl`;
    img.alt = 'BL';
    img.loading = 'lazy';
    photoWrap.appendChild(img);
    photoWrap.addEventListener('click', e => {
      e.stopPropagation();
      ouvrirModalBL(`/api/receptions/${rec.id}/photo-bl`);
    });
  } else {
    const ph = document.createElement('div');
    ph.className = 'he-photo-rec-placeholder';
    ph.textContent = '📋';
    photoWrap.appendChild(ph);
  }
  resume.appendChild(photoWrap);

  const info = document.createElement('div');
  info.className = 'he-carte-rec-info';

  const entete = document.createElement('div');
  entete.className = 'he-carte-rec-entete';

  const date = document.createElement('div');
  date.className = 'he-date';
  date.textContent = formatDateFR(rec.date_reception);
  entete.appendChild(date);

  const b = recBadgeConformite(rec);
  const badge = document.createElement('span');
  badge.className = `he-badge ${b.cls}`;
  badge.textContent = b.txt;
  entete.appendChild(badge);
  info.appendChild(entete);

  const meta = document.createElement('div');
  meta.className = 'he-meta';
  const fournisseurLabel = rec.fournisseur_nom ? ` — ${rec.fournisseur_nom}` : '';
  meta.textContent = `${rec.personnel_prenom || '—'}${fournisseurLabel}`;
  info.appendChild(meta);

  const chips = document.createElement('div');
  chips.className = 'he-chips';

  if (rec.fournisseur_nom) {
    const c1 = document.createElement('span');
    c1.className = 'he-chip';
    c1.textContent = rec.fournisseur_nom;
    chips.appendChild(c1);
  }

  const c2 = document.createElement('span');
  c2.className = 'he-chip';
  c2.textContent = `${rec.nb_lignes || 0} produit${(rec.nb_lignes || 0) > 1 ? 's' : ''}`;
  chips.appendChild(c2);

  if (rec.proprete_camion && rec.proprete_camion !== 'satisfaisant') {
    const c3 = document.createElement('span');
    c3.className = 'he-chip he-chip--nc';
    c3.textContent = '⚠ Camion NC';
    chips.appendChild(c3);
  }

  info.appendChild(chips);
  resume.appendChild(info);

  const chev = document.createElement('span');
  chev.className = 'he-chevron';
  chev.textContent = '▾';
  chev.setAttribute('aria-hidden', 'true');
  resume.appendChild(chev);

  carte.appendChild(resume);

  const detail = document.createElement('div');
  detail.className = 'he-detail';
  carte.appendChild(detail);

  let detailCharge = false;

  resume.addEventListener('click', async () => {
    carte.classList.toggle('ouvert');
    if (carte.classList.contains('ouvert') && !detailCharge) {
      detailCharge = true;
      detail.innerHTML = '<div style="padding:12px;color:#888;">Chargement…</div>';
      try {
        const rec2 = await apiFetch(`/api/receptions/${rec.id}`);
        recRemplirDetail(detail, rec2);
      } catch (err) {
        detail.innerHTML = `<div style="padding:12px;color:var(--alerte);">Erreur : ${err.message}</div>`;
      }
    }
  });

  return carte;
}

function recRemplirDetail(el, rec) {
  el.innerHTML = '';

  // ── Boutons d'action ────────────────────────────────────
  const btnActions = document.createElement('div');
  btnActions.style.cssText = 'display:flex;gap:10px;margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #DDD;';

  const btnFiche = document.createElement('button');
  btnFiche.style.cssText = 'flex:1;background:var(--accent);color:#FFF;border:none;border-radius:8px;padding:10px;font-size:14px;font-weight:700;cursor:pointer;';
  btnFiche.textContent = '📋 Fiche d\'enregistrement';
  btnFiche.addEventListener('click', e => {
    e.stopPropagation();
    window.location.href = `/reception-detail.html?id=${rec.id}`;
  });
  btnActions.appendChild(btnFiche);

  // Afficher le bouton PCR01 seulement s'il y a des NC (calculé depuis les lignes chargées)
  const nbNc = (rec.lignes || []).filter(l => l.conforme === 0).length;
  if (nbNc > 0) {
    const btnPcr = document.createElement('button');
    btnPcr.style.cssText = 'flex:1;background:var(--alerte);color:#FFF;border:none;border-radius:8px;padding:10px;font-size:14px;font-weight:700;cursor:pointer;';
    btnPcr.textContent = '⚠️ Fiches PCR01';
    btnPcr.addEventListener('click', e => {
      e.stopPropagation();
      window.location.href = `/incidents.html?reception_id=${rec.id}`;
    });
    btnActions.appendChild(btnPcr);
  }

  el.appendChild(btnActions);

  if (rec.photo_bl_filename) {
    const btn = document.createElement('button');
    btn.className = 'he-detail-bl-btn';
    btn.textContent = '📋 Voir le bon de livraison';
    btn.addEventListener('click', e => {
      e.stopPropagation();
      ouvrirModalBL(`/api/receptions/${rec.id}/photo-bl`);
    });
    el.appendChild(btn);
  }

  const titreCamion = document.createElement('div');
  titreCamion.className = 'he-detail-section-titre';
  titreCamion.textContent = 'Contrôle camion';
  el.appendChild(titreCamion);

  const divCamion = document.createElement('div');
  divCamion.className = 'he-detail-camion';

  const champsCamion = [
    { label: 'Température', valeur: formatTemp(rec.temperature_camion) },
    { label: 'Propreté', valeur: rec.proprete_camion === 'satisfaisant' ? '✓ OK' : '✗ NC' },
    { label: 'Heure', valeur: rec.heure_reception || '—' },
  ];
  champsCamion.forEach(({ label, valeur }) => {
    const div = document.createElement('div');
    div.className = 'he-camion-info';
    const lbl = document.createElement('span');
    lbl.className = 'he-camion-label';
    lbl.textContent = label;
    const val = document.createElement('span');
    val.className = 'he-camion-valeur';
    val.textContent = valeur;
    div.appendChild(lbl);
    div.appendChild(val);
    divCamion.appendChild(div);
  });
  el.appendChild(divCamion);

  if (rec.commentaire_nc) {
    const divCmt = document.createElement('div');
    divCmt.className = 'he-commentaire';
    const lbl = document.createElement('div');
    lbl.className = 'he-commentaire-label';
    lbl.textContent = 'Commentaire NC';
    const txt = document.createElement('div');
    txt.textContent = rec.commentaire_nc;
    divCmt.appendChild(lbl);
    divCmt.appendChild(txt);
    el.appendChild(divCmt);
  }

  const titreProd = document.createElement('div');
  titreProd.className = 'he-detail-section-titre';
  titreProd.textContent = `Produits réceptionnés (${(rec.lignes || []).length})`;
  el.appendChild(titreProd);

  const divLignes = document.createElement('div');
  divLignes.className = 'he-lignes';

  if (!rec.lignes || rec.lignes.length === 0) {
    const vide = document.createElement('div');
    vide.style.cssText = 'padding:8px;color:#888;font-size:15px;';
    vide.textContent = 'Aucun produit enregistré.';
    divLignes.appendChild(vide);
  } else {
    rec.lignes.forEach(lig => divLignes.appendChild(recCreerLigne(lig, rec.fournisseur_nom)));
  }

  el.appendChild(divLignes);
}

function recCreerLigne(lig, receptionFournisseurNom = null) {
  const estNC = lig.conforme === 0;

  const div = document.createElement('div');
  div.className = `he-ligne ${estNC ? 'he-ligne--nc' : ''}`;
  div.style.cssText = `border: 3px solid ${estNC ? '#C93030' : '#2D7D46'}; border-radius: 8px; padding: 12px;`;

  const entete = document.createElement('div');
  entete.className = 'he-ligne-entete';

  const gauche = document.createElement('div');
  const nom = document.createElement('div');
  nom.className = 'he-ligne-nom';
  nom.textContent = lig.produit_nom || '—';
  gauche.appendChild(nom);
  if (lig.espece) {
    const esp = document.createElement('div');
    esp.className = 'he-ligne-espece';
    esp.textContent = lig.espece;
    gauche.appendChild(esp);
  }
  entete.appendChild(gauche);

  const badge = document.createElement('span');
  badge.className = `he-ligne-badge ${estNC ? 'he-ligne-badge--nc' : 'he-ligne-badge--ok'}`;
  badge.textContent = estNC ? '✗ NC' : '✓ OK';
  entete.appendChild(badge);
  div.appendChild(entete);

  const grille = document.createElement('div');
  grille.className = 'he-ligne-grille';

  const champs = [
    { label: 'Fournisseur', valeur: lig.fournisseur_nom || receptionFournisseurNom || '—' },
    { label: 'N° lot', valeur: lig.numero_lot || '—' },
    { label: 'DLC', valeur: formatDateFR(lig.dlc) },
    { label: 'T° réception', valeur: formatTemp(lig.temperature_reception) },
    { label: 'T° à cœur', valeur: formatTemp(lig.temperature_coeur) },
  ];
  if (lig.ph_valeur !== null && lig.ph_valeur !== undefined) {
    champs.push({ label: 'pH', valeur: String(lig.ph_valeur) });
  }

  champs.forEach(({ label, valeur }) => {
    const c = document.createElement('div');
    c.className = 'he-ligne-champ';
    const lbl = document.createElement('span');
    lbl.className = 'he-ligne-champ-label';
    lbl.textContent = label;
    const val = document.createElement('span');
    val.className = 'he-ligne-champ-val';
    val.textContent = valeur;
    c.appendChild(lbl);
    c.appendChild(val);
    grille.appendChild(c);
  });
  div.appendChild(grille);

  if (estNC) {
    const criteres = [];
    if (lig.couleur_conforme === 0) criteres.push(`Couleur : ${lig.couleur_observation || 'NC'}`);
    if (lig.consistance_conforme === 0) criteres.push(`Consistance : ${lig.consistance_observation || 'NC'}`);
    if (lig.exsudat_conforme === 0) criteres.push(`Exsudat : ${lig.exsudat_observation || 'NC'}`);
    if (lig.odeur_conforme === 0) criteres.push(`Odeur : ${lig.odeur_observation || 'NC'}`);
    if (lig.temperature_conforme === 0) criteres.push('Température hors seuil');
    if (criteres.length) {
      const nc = document.createElement('div');
      nc.className = 'he-criteres-nc';
      nc.textContent = criteres.join(' — ');
      div.appendChild(nc);
    }
  }

  return div;
}

// ── Autocomplete réceptions ──────────────────────────────────
recRefs.input.addEventListener('input', () => {
  recState.fournisseurId = null;
  const q = recRefs.input.value.trim();
  if (!q) { recRefs.auto.hidden = true; recRefs.auto.innerHTML = ''; return; }

  clearTimeout(recState.debounce);
  recState.debounce = setTimeout(async () => {
    try {
      const liste = await apiFetch('/api/fournisseurs');
      const ql = q.toLowerCase();
      const filtres = liste.filter(f => f.nom.toLowerCase().includes(ql)).slice(0, 10);
      recAfficherAuto(filtres);
    } catch { /* silencieux */ }
  }, 300);
});

function recAfficherAuto(liste) {
  recRefs.auto.innerHTML = '';
  if (!liste.length) { recRefs.auto.hidden = true; return; }
  liste.forEach(f => {
    const item = document.createElement('div');
    item.className = 'he-ac-item';
    item.setAttribute('role', 'option');
    item.textContent = f.nom;
    item.addEventListener('click', () => {
      recState.fournisseurId = f.id;
      recRefs.input.value = f.nom;
      recRefs.auto.hidden = true;
      recRefs.auto.innerHTML = '';
    });
    recRefs.auto.appendChild(item);
  });
  recRefs.auto.hidden = false;
}

document.addEventListener('click', e => {
  if (!recRefs.input.contains(e.target) && !recRefs.auto.contains(e.target)) {
    recRefs.auto.hidden = true;
  }
});

// ── Boutons réceptions ───────────────────────────────────────
recRefs.filtrer.addEventListener('click', recCharger);
recRefs.reset.addEventListener('click', () => {
  recState.fournisseurId = null;
  recRefs.input.value = '';
  recRefs.auto.hidden = true;
  initDates(recRefs);
  recCharger();
});
recRefs.plus.addEventListener('click', recChargerSuite);

// ── Modal ────────────────────────────────────────────────────
function ouvrirModal(ouvertureId, nom) {
  elModalImg.src = `/api/ouvertures/${ouvertureId}/photo`;
  elModalImg.alt = `Ouverture ${nom}`;
  elModal.hidden = false;
  document.body.style.overflow = 'hidden';
}

function ouvrirModalBL(src) {
  elModalImg.src = src;
  elModalImg.alt = 'Bon de livraison';
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

// ══════════════════════════════════════════════════════════════
// ONGLET FABRICATIONS
// ══════════════════════════════════════════════════════════════

function fabBuildUrl(offset = 0) {
  const p = new URLSearchParams();
  p.set('limit', String(LIMIT));
  p.set('offset', String(offset));
  if (fabRefs.debut.value) p.set('date_debut', fabRefs.debut.value);
  if (fabRefs.fin.value)   p.set('date_fin',   fabRefs.fin.value);
  return `/api/fabrications?${p.toString()}`;
}

async function fabCharger() {
  fabState.offset = 0;
  fabState.totalCharges = 0;
  fabState.charge = true;
  fabRefs.liste.innerHTML = '';
  fabRefs.plus.hidden = true;
  fabRefs.compteur.textContent = '';
  fabAfficherMessage('⏳', 'Chargement…');

  try {
    const rows = await apiFetch(fabBuildUrl(0));
    fabMasquerMessage();
    fabAjouterResultats(rows);
  } catch (err) {
    fabAfficherMessage('⚠️', `Erreur : ${err.message}`);
  }
}

async function fabChargerSuite() {
  fabRefs.plus.disabled = true;
  fabRefs.plus.textContent = 'Chargement…';
  try {
    const rows = await apiFetch(fabBuildUrl(fabState.offset));
    fabAjouterResultats(rows);
  } catch (err) {
    fabRefs.plus.disabled = false;
    fabRefs.plus.textContent = 'Voir plus…';
    alert(`Erreur : ${err.message}`);
  }
}

function fabAjouterResultats(rows) {
  if (rows.length === 0 && fabState.totalCharges === 0) {
    fabAfficherMessage('🔍', 'Aucune fabrication trouvée.');
    return;
  }

  rows.forEach(fab => fabRefs.liste.appendChild(fabCreerCarte(fab)));

  fabState.offset       += rows.length;
  fabState.totalCharges += rows.length;
  fabMajCompteur();

  if (rows.length === LIMIT) {
    fabRefs.plus.hidden = false;
    fabRefs.plus.disabled = false;
    fabRefs.plus.textContent = 'Voir plus…';
  } else {
    fabRefs.plus.hidden = true;
  }
}

function fabMajCompteur() {
  fabRefs.compteur.textContent = fabState.totalCharges === 1
    ? '1 fabrication'
    : `${fabState.totalCharges} fabrications`;
}

function fabAfficherMessage(icone, texte) {
  fabRefs.icone.textContent = icone;
  fabRefs.texte.textContent = texte;
  fabRefs.message.hidden = false;
}
function fabMasquerMessage() { fabRefs.message.hidden = true; }

function fabCreerCarte(fab) {
  const carte = document.createElement('div');
  carte.className = 'he-carte-fab';
  carte.setAttribute('role', 'listitem');

  // ── Résumé (cliquable) ───────────────────────────────────
  const resume = document.createElement('div');
  resume.className = 'he-carte-fab-resume';

  const icone = document.createElement('div');
  icone.className = 'he-fab-icone';
  icone.setAttribute('aria-hidden', 'true');
  icone.textContent = '🏭';
  resume.appendChild(icone);

  const info = document.createElement('div');
  info.className = 'he-carte-fab-info';

  const entete = document.createElement('div');
  entete.className = 'he-fab-entete';

  const nom = document.createElement('div');
  nom.className = 'he-fab-nom';
  nom.textContent = fab.recette_nom || '—';
  entete.appendChild(nom);

  const lot = document.createElement('span');
  lot.className = 'he-fab-lot';
  lot.textContent = fab.lot_interne || '—';
  entete.appendChild(lot);

  if (fab.dlc_finale) {
    const dlcBadge = document.createElement('span');
    dlcBadge.className = 'ml-4 text-xs font-bold text-red-600 bg-red-100 px-2 py-1 rounded';
    dlcBadge.style.cssText = 'display:inline-block;margin-left:1rem;font-size:.7rem;font-weight:700;color:#dc2626;background:#fee2e2;padding:2px 8px;border-radius:4px;';
    dlcBadge.textContent = `DLC: ${formatDateFR(fab.dlc_finale)}`;
    entete.appendChild(dlcBadge);
  }
  info.appendChild(entete);

  const meta = document.createElement('div');
  meta.className = 'he-fab-meta';
  const { unite: uniteMetaBase } = fabExtraireBase(fab.recette_instructions);
  const poidsLabel = (fab.poids_fabrique != null && fab.poids_fabrique > 0)
    ? ` — ⚖️ ${fab.poids_fabrique} ${uniteMetaBase} fabriqués`
    : '';
  meta.textContent = `${formatDateFR(fab.date)} — ${fab.personnel_prenom || '—'}${poidsLabel}`;
  info.appendChild(meta);

  const chips = document.createElement('div');
  chips.className = 'he-fab-chips';

  const nbIng = (fab.ingredients || []).length;
  const cIng = document.createElement('span');
  cIng.className = 'he-fab-chip';
  cIng.textContent = `${nbIng} ingrédient${nbIng > 1 ? 's' : ''}`;
  chips.appendChild(cIng);

  if (fab.info_complementaire) {
    const cInfo = document.createElement('span');
    cInfo.className = 'he-fab-chip';
    cInfo.textContent = fab.info_complementaire;
    chips.appendChild(cInfo);
  }

  const btnPrint = document.createElement('button');
  btnPrint.className = 'he-btn-reimprimer';
  btnPrint.textContent = '🖨 Imprimer';
  btnPrint.addEventListener('click', e => {
    e.stopPropagation();
    fabReimprimer(fab);
  });
  chips.appendChild(btnPrint);

  info.appendChild(chips);
  resume.appendChild(info);

  const chev = document.createElement('span');
  chev.className = 'he-chevron';
  chev.textContent = '▾';
  chev.setAttribute('aria-hidden', 'true');
  resume.appendChild(chev);

  carte.appendChild(resume);

  // ── Détail ingrédients (accordéon) ──────────────────────
  const detail = document.createElement('div');
  detail.className = 'he-fab-detail';
  carte.appendChild(detail);

  resume.addEventListener('click', () => {
    carte.classList.toggle('ouvert');
    if (carte.classList.contains('ouvert') && !detail.dataset.charge) {
      detail.dataset.charge = '1';
      fabRemplirIngredients(detail, fab.ingredients || [], fab);
    }
  });

  return carte;
}

function fabRemplirIngredients(el, ingredients, fab) {
  // ── Calcul du multiplicateur ─────────────────────────────
  const { base: baseKg, unite: uniteBase } = fabExtraireBase(fab ? fab.recette_instructions : null);
  const poids = (fab && fab.poids_fabrique != null && fab.poids_fabrique > 0) ? fab.poids_fabrique : 0;
  const multiplicateur = (baseKg && baseKg > 0 && poids > 0) ? (poids / baseKg) : null;

  // ── Badge poids fabriqué ─────────────────────────────────
  if (poids > 0) {
    const poidsEl = document.createElement('div');
    poidsEl.className = 'he-fab-det-poids';
    poidsEl.textContent = `⚖️ ${poids} ${uniteBase} fabriqués`;
    el.appendChild(poidsEl);
  }

  if (ingredients.length === 0) {
    const vide = document.createElement('div');
    vide.style.cssText = 'padding:10px 14px;color:#888;font-size:15px;';
    vide.textContent = 'Aucun ingrédient enregistré.';
    el.appendChild(vide);
    return;
  }

  const liste = document.createElement('div');
  liste.className = 'he-fab-ing-liste';

  ingredients.forEach(ing => {
    const div = document.createElement('div');
    div.className = 'he-fab-ing';

    // Colonne gauche : nom de l'ingrédient
    const nomEl = document.createElement('div');
    nomEl.className = 'he-fab-ing-nom';
    nomEl.textContent = ing.produit_nom || '—';
    div.appendChild(nomEl);

    // Colonne milieu : quantité proportionnelle calculée
    const qteEl = document.createElement('div');
    qteEl.className = 'he-fab-ing-qte';
    if (ing.quantite_base != null) {
      const qte = multiplicateur !== null ? ing.quantite_base * multiplicateur : ing.quantite_base;
      const qteStr = parseFloat(qte.toFixed(3)).toString();
      qteEl.textContent = `${qteStr} ${ing.unite || 'kg'}`;
    } else {
      qteEl.textContent = '—';
    }
    div.appendChild(qteEl);

    // Colonne droite : lot + DLC + lien traçabilité
    const lotEl = document.createElement('div');
    lotEl.className = 'he-fab-ing-lot';

    const lotTxt = document.createElement('span');
    lotTxt.textContent = ing.numero_lot ? `Lot ${ing.numero_lot}` : '—';
    lotEl.appendChild(lotTxt);

    if (ing.dlc) {
      const dlcTxt = document.createElement('span');
      dlcTxt.className = 'he-fab-ing-dlc';
      dlcTxt.textContent = ` · DLC ${formatDateFR(ing.dlc)}`;
      lotEl.appendChild(dlcTxt);
    }

    if (ing.reception_id) {
      const lien = document.createElement('a');
      lien.href = `/reception-detail.html?id=${ing.reception_id}`;
      lien.textContent = ' 🔗';
      lien.title = 'Voir la réception';
      lien.style.cssText = 'color:var(--accent);text-decoration:none;font-size:14px;';
      lien.addEventListener('click', e => e.stopPropagation());
      lotEl.appendChild(lien);
    }

    div.appendChild(lotEl);
    liste.appendChild(div);
  });

  el.appendChild(liste);
}

// ── Ré-impression d'un ticket depuis l'historique ────────────

/** Extrait "Base pour X kg/pièces" depuis le champ instructions (même logique que etiquettes.js) */
function fabExtraireBase(instructions) {
  if (!instructions) return { base: null, unite: 'kg' };
  const m = String(instructions).match(/base pour (\d+(?:[.,]\d+)?)\s*(kg|g|pièces?|pc|l)?/i);
  if (!m) return { base: null, unite: 'kg' };
  const base = parseFloat(m[1].replace(',', '.'));
  if (isNaN(base) || base <= 0) return { base: null, unite: 'kg' };
  return { base, unite: m[2] || 'kg' };
}

function fabReimprimer(fab) {
  const dlcFormatee = fab.dlc_finale
    ? fab.dlc_finale.split('-').reverse().join('/')
    : '--/--/----';

  document.getElementById('print-nom').textContent = fab.recette_nom || '—';

  // Afficher le poids réellement fabriqué (stocké en BDD)
  const elPoids = document.getElementById('print-poids');
  if (fab.poids_fabrique != null && fab.poids_fabrique > 0) {
    const { unite } = fabExtraireBase(fab.recette_instructions);
    elPoids.textContent = `${fab.poids_fabrique} ${unite} fabriqués`;
    elPoids.hidden = false;
  } else if (fab.info_complementaire) {
    elPoids.textContent = fab.info_complementaire;
    elPoids.hidden = false;
  } else {
    elPoids.textContent = '';
    elPoids.hidden = true;
  }

  document.getElementById('print-dlc').textContent = dlcFormatee;
  document.getElementById('print-lot').textContent = `Lot : ${fab.lot_interne || '—'}`;
  document.getElementById('print-meta').textContent =
    `Fabriqué le ${formatDateFR(fab.date)} par ${fab.personnel_prenom || '—'}`;

  // Calcul du multiplicateur pour remettre à l'échelle les quantités d'ingrédients
  const { base: baseKg } = fabExtraireBase(fab.recette_instructions);
  const poids = fab.poids_fabrique ?? 0;
  const multiplicateur = (baseKg && baseKg > 0 && poids > 0) ? (poids / baseKg) : 1;

  const ul = document.getElementById('print-ingredients');
  ul.innerHTML = '';
  (fab.ingredients || []).forEach(ing => {
    const li     = document.createElement('li');
    const nom    = ing.produit_nom || '?';
    const lot    = ing.numero_lot || 'N/A';
    const dlcIng = ing.dlc
      ? new Date(ing.dlc).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' })
      : 'N/A';
    let qteTexte = '';
    if (ing.quantite_base != null) {
      const qteScalee = multiplicateur !== 1
        ? Math.round(ing.quantite_base * multiplicateur * 100) / 100
        : ing.quantite_base;
      qteTexte = `${qteScalee}${ing.unite || ''} `;
    }
    li.textContent = `${qteTexte}${nom} (L:${lot} | DLC:${dlcIng})`;
    ul.appendChild(li);
  });

  setTimeout(() => window.print(), 100);
}

// ── Boutons fabrications ─────────────────────────────────────
fabRefs.filtrer.addEventListener('click', fabCharger);
fabRefs.reset.addEventListener('click', () => {
  initDates(fabRefs);
  fabCharger();
});
fabRefs.plus.addEventListener('click', fabChargerSuite);

// ── Bouton retour ────────────────────────────────────────────
elBtnRetour.addEventListener('click', () => { window.location.href = '/hub.html'; });

// ══════════════════════════════════════════════════════════════
// ONGLET NETTOYAGE
// ══════════════════════════════════════════════════════════════

const nettState = { charge: false };
const elHnMessage = document.getElementById('hn-message');
const elHnMessageTexte = document.getElementById('hn-message-texte');
const elHnArbre = document.getElementById('hn-arbre');

async function nettCharger() {
  nettState.charge = true;
  elHnMessage.hidden = false;
  elHnArbre.hidden = true;
  elHnArbre.innerHTML = '';
  elHnMessageTexte.textContent = 'Chargement…';

  try {
    const data = await apiFetch('/api/nettoyage/historique');
    if (!data.length) {
      elHnMessageTexte.textContent = 'Aucune validation enregistrée pour l\'instant.';
      return;
    }
    elHnMessage.hidden = true;
    elHnArbre.hidden = false;
    nettRendreArbre(data);
  } catch (err) {
    elHnMessageTexte.textContent = `Erreur : ${err.message}`;
  }
}

function nettRendreArbre(data) {
  const anneeActuelle = new Date().getFullYear();
  const moisActuel    = new Date().getMonth() + 1;

  data.forEach(blocAnnee => {
    const divAnnee = document.createElement('div');
    divAnnee.className = 'hn-annee';
    const ouvertAnnee = blocAnnee.annee === anneeActuelle;
    if (ouvertAnnee) divAnnee.classList.add('ouvert');

    const nbJours = blocAnnee.mois.reduce(
      (s, m) => s + m.semaines.reduce((ss, sem) => ss + sem.jours.length, 0), 0
    );

    const btnAnnee = document.createElement('button');
    btnAnnee.className = 'hn-annee-btn';
    btnAnnee.innerHTML = `
      📅 ${blocAnnee.annee}
      <span style="font-size:13px;font-weight:400;opacity:.75;">${nbJours} jour(s)</span>
      <span class="hn-annee-chev">▼</span>`;
    btnAnnee.addEventListener('click', () => divAnnee.classList.toggle('ouvert'));

    const corpsAnnee = document.createElement('div');
    corpsAnnee.className = 'hn-annee-corps';

    // ── Mois ────────────────────────────────────────────────
    blocAnnee.mois.forEach(blocMois => {
      const divMois = document.createElement('div');
      divMois.className = 'hn-mois';
      const ouvertMois = ouvertAnnee && blocMois.numero === moisActuel;
      if (ouvertMois) divMois.classList.add('ouvert');

      const nbJoursMois = blocMois.semaines.reduce((s, sem) => s + sem.jours.length, 0);

      const btnMois = document.createElement('button');
      btnMois.className = 'hn-mois-btn';
      btnMois.innerHTML = `
        🗓️ ${blocMois.nom}
        <span class="hn-mois-badge">${nbJoursMois} jour(s)</span>
        <span class="hn-mois-chev">▼</span>`;
      btnMois.addEventListener('click', () => divMois.classList.toggle('ouvert'));

      const corpsMois = document.createElement('div');
      corpsMois.className = 'hn-mois-corps';

      // ── Semaines ──────────────────────────────────────────
      blocMois.semaines.forEach((blocSem, idx) => {
        const divSem = document.createElement('div');
        divSem.className = 'hn-sem';
        const ouvertSem = ouvertMois && idx === 0;
        if (ouvertSem) divSem.classList.add('ouvert');

        const btnSem = document.createElement('button');
        btnSem.className = 'hn-sem-btn';
        btnSem.innerHTML = `
          <span class="hn-sem-label">Semaine ${blocSem.numero}</span>
          <span class="hn-sem-nb">${blocSem.jours.length} jour(s) validé(s)</span>
          <span class="hn-sem-chev">▼</span>`;

        const corpsSem = document.createElement('div');
        corpsSem.className = 'hn-sem-corps';

        let planningCharge = false;

        btnSem.addEventListener('click', async () => {
          const estOuvert = divSem.classList.toggle('ouvert');
          if (estOuvert && !planningCharge) {
            planningCharge = true;
            corpsSem.innerHTML = '<div class="hn-sem-loading">⏳ Chargement du planning…</div>';
            try {
              const semData = await apiFetch(
                `/api/nettoyage/historique/semaine?annee_iso=${blocSem.annee_iso}&semaine=${blocSem.numero}`
              );
              corpsSem.innerHTML = '';
              corpsSem.appendChild(nettRendrePlanning(semData));
            } catch (err) {
              corpsSem.innerHTML = `<div class="hn-sem-loading" style="color:#C93030;">Erreur : ${err.message}</div>`;
            }
          }
        });

        // Si la semaine est déjà ouverte au rendu, charger le planning immédiatement
        if (ouvertSem) {
          planningCharge = true;
          corpsSem.innerHTML = '<div class="hn-sem-loading">⏳ Chargement…</div>';
          apiFetch(`/api/nettoyage/historique/semaine?annee_iso=${blocSem.annee_iso}&semaine=${blocSem.numero}`)
            .then(semData => {
              corpsSem.innerHTML = '';
              corpsSem.appendChild(nettRendrePlanning(semData));
            })
            .catch(err => {
              corpsSem.innerHTML = `<div class="hn-sem-loading" style="color:#C93030;">Erreur : ${err.message}</div>`;
            });
        }

        divSem.appendChild(btnSem);
        divSem.appendChild(corpsSem);
        corpsMois.appendChild(divSem);
      });

      divMois.appendChild(btnMois);
      divMois.appendChild(corpsMois);
      corpsAnnee.appendChild(divMois);
    });

    divAnnee.appendChild(btnAnnee);
    divAnnee.appendChild(corpsAnnee);
    elHnArbre.appendChild(divAnnee);
  });
}

function nettRendrePlanning(semData) {
  const wrap = document.createElement('div');
  wrap.className = 'hn-planning-wrap';

  const table = document.createElement('table');
  table.className = 'hn-planning-table';

  // ── En-tête ───────────────────────────────────────────────
  const thead = document.createElement('thead');
  const trHead = document.createElement('tr');

  [
    { txt: 'Secteur',  cls: 'hn-th-zone' },
    { txt: 'Tâche',    cls: 'hn-th-tache' },
    { txt: 'Fréq.',    cls: 'hn-th-freq' },
    { txt: 'Produit',  cls: 'hn-th-prod' },
  ].forEach(({ txt, cls }) => {
    const th = document.createElement('th');
    th.className = cls;
    th.textContent = txt;
    trHead.appendChild(th);
  });

  semData.jours_noms.forEach((nom, i) => {
    const date = semData.dates[i];
    // Vérifier si au moins une tâche a été validée ce jour
    const jouValide = semData.zones.some(z =>
      z.taches.some(t => t.validations[date])
    );
    const th = document.createElement('th');
    th.className = 'hn-th-day' + (jouValide ? ' hn-th-day--valide' : '');
    th.textContent = nom;
    trHead.appendChild(th);
  });

  thead.appendChild(trHead);
  table.appendChild(thead);

  // ── Corps ─────────────────────────────────────────────────
  const tbody = document.createElement('tbody');

  semData.zones.forEach(zone => {
    zone.taches.forEach((tache, taskIdx) => {
      const tr = document.createElement('tr');

      // Cellule secteur (fusionnée)
      if (taskIdx === 0) {
        const tdZone = document.createElement('td');
        tdZone.className = 'hn-td-zone';
        tdZone.rowSpan = zone.taches.length;
        tdZone.textContent = zone.zone;
        tr.appendChild(tdZone);
      }

      const tdNom = document.createElement('td');
      tdNom.className = 'hn-td-tache';
      tdNom.title = tache.nom_tache;
      tdNom.textContent = tache.nom_tache;
      tr.appendChild(tdNom);

      const tdFreq = document.createElement('td');
      tdFreq.className = 'hn-td-freq';
      tdFreq.textContent = tache.frequence;
      tr.appendChild(tdFreq);

      const tdProd = document.createElement('td');
      tdProd.className = 'hn-td-prod';
      tdProd.title = tache.methode_produit;
      tdProd.textContent = tache.methode_produit;
      tr.appendChild(tdProd);

      // Colonnes jours
      semData.dates.forEach(date => {
        const initial = tache.validations[date];
        const td = document.createElement('td');
        td.className = 'hn-td-day' + (initial ? ' hn-td-day--ok' : ' hn-td-day--vide');
        if (initial) {
          td.innerHTML = `✅<span class="hn-td-initial">${initial}</span>`;
        } else {
          // Afficher — seulement si la fréquence rend la tâche applicable ce jour
          td.textContent = '·';
        }
        tr.appendChild(td);
      });

      tbody.appendChild(tr);
    });
  });

  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}

// ── Init ─────────────────────────────────────────────────────
initDates(ouvRefs);
initDates(recRefs);
initDates(fabRefs);

// Ouvrir l'onglet demandé via ?tab= ou ancre URL legacy (#nettoyage)
// ?fab_date=YYYY-MM-DD pré-filtre l'onglet fabrications sur cette journée
const _urlParams = new URLSearchParams(window.location.search);
const _tabParam  = _urlParams.get('tab');
const _fabDate   = _urlParams.get('fab_date');

if (_tabParam === 'nettoyage' || window.location.hash === '#nettoyage') {
  basculerTab(elTabNett, elContentNett);
  nettCharger();
} else if (_tabParam === 'fabrications' || _fabDate) {
  if (_fabDate) {
    if (fabRefs.debut) fabRefs.debut.value = _fabDate;
    if (fabRefs.fin)   fabRefs.fin.value   = _fabDate;
  }
  basculerTab(elTabFab, elContentFab);
  fabCharger();
} else {
  ouvCharger();
  recCharger();
}

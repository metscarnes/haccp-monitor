'use strict';
/* ============================================================
   reception-detail.js — Affichage détail réception (lecture seule)
   Au Comptoir des Lilas — Mets Carnés Holding
   ============================================================ */

// ── Références DOM ──────────────────────────────────────────
const elBtnRetour = document.getElementById('rd-btn-retour');
const elHorloge = document.getElementById('rd-horloge');
const elMain = document.getElementById('rd-main');
const elMessage = document.getElementById('rd-message');
const elModal = document.getElementById('rd-modal');
const elModalImg = document.getElementById('rd-modal-img');

// ── Horloge ─────────────────────────────────────────────────
function majHorloge() {
  elHorloge.textContent = new Date().toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();

// ── Inactivité ──────────────────────────────────────────────
let timerInactivite;
function resetInactivite() {
  clearTimeout(timerInactivite);
  timerInactivite = setTimeout(() => {
    window.location.href = '/hub.html';
  }, 5 * 60 * 1000);
}
document.addEventListener('click',      resetInactivite, true);
document.addEventListener('touchstart', resetInactivite, { passive: true, capture: true });
resetInactivite();

// ── Retour ──────────────────────────────────────────────────
elBtnRetour.addEventListener('click', () => {
  window.history.back();
});

// ── Fetch ───────────────────────────────────────────────────
async function apiFetch(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Formatage ───────────────────────────────────────────────
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

// ── Récupération de l'ID depuis l'URL ────────────────────────
const params = new URLSearchParams(window.location.search);
const receptionId = params.get('id');

if (!receptionId) {
  elMessage.innerHTML = '<div style="font-size:48px;margin-bottom:12px;">⚠️</div><div>ID de réception manquant.</div>';
} else {
  // Charger et afficher la réception
  apiFetch(`/api/receptions/${receptionId}`)
    .then(rec => afficherReception(rec))
    .catch(err => {
      elMessage.innerHTML = `<div style="font-size:48px;margin-bottom:12px;">⚠️</div><div>Erreur : ${err.message}</div>`;
    });
}

// ── Affichage complet ────────────────────────────────────────
function afficherReception(rec) {
  elMain.innerHTML = '';

  // ── Section Général ────────────────────────────────────
  const secGen = document.createElement('div');
  secGen.className = 'rd-section';

  const titGen = document.createElement('div');
  titGen.className = 'rd-section-titre';
  titGen.textContent = 'Général';
  secGen.appendChild(titGen);

  function creerChamp(labelTxt, id) {
    const ch = document.createElement('div');
    ch.className = 'rd-champ';
    const lbl = document.createElement('span');
    lbl.className = 'rd-champ-label';
    lbl.textContent = labelTxt;
    const val = document.createElement('span');
    val.className = 'rd-champ-val';
    if (id) val.id = id;
    ch.appendChild(lbl);
    ch.appendChild(val);
    return { ch, val };
  }

  // Ligne 1 : Fournisseur (pleine largeur)
  const rowFourn = document.createElement('div');
  rowFourn.className = 'rd-row full';
  const { ch: chFourn, val: valFourn } = creerChamp('Fournisseur', 'detail-fournisseur');
  valFourn.textContent = rec.fournisseur_nom || 'Non renseigné';
  rowFourn.appendChild(chFourn);
  secGen.appendChild(rowFourn);

  // Ligne 2 : N° BL | Date de réception
  const rowBLDate = document.createElement('div');
  rowBLDate.className = 'rd-row';
  const { ch: chBL, val: valBL } = creerChamp('N° Bon de livraison', 'detail-bl');
  valBL.textContent = rec.numero_bon_livraison || '—';
  rowBLDate.appendChild(chBL);
  const { ch: chDate, val: valDate } = creerChamp('Date de réception', 'detail-date');
  valDate.textContent = formatDateFR(rec.date_reception);
  rowBLDate.appendChild(chDate);
  secGen.appendChild(rowBLDate);

  // Ligne 3 : Heure | Opérateur
  const rowHeureOp = document.createElement('div');
  rowHeureOp.className = 'rd-row';
  const { ch: chHeure, val: valHeure } = creerChamp('Heure', 'detail-heure');
  valHeure.textContent = rec.heure_reception || '—';
  rowHeureOp.appendChild(chHeure);
  const { ch: chOp, val: valOp } = creerChamp('Opérateur', 'detail-operateur');
  valOp.textContent = rec.personnel_prenom || '—';
  rowHeureOp.appendChild(chOp);
  secGen.appendChild(rowHeureOp);

  elMain.appendChild(secGen);

  // ── Section Camion ────────────────────────────────────
  const secCamion = document.createElement('div');
  secCamion.className = 'rd-section';

  const titCamion = document.createElement('div');
  titCamion.className = 'rd-section-titre';
  titCamion.textContent = 'Contrôle camion';
  secCamion.appendChild(titCamion);

  const rowCamion = document.createElement('div');
  rowCamion.className = 'rd-row';

  const chTemp = document.createElement('div');
  chTemp.className = 'rd-champ';
  const lblTemp = document.createElement('span');
  lblTemp.className = 'rd-champ-label';
  lblTemp.textContent = 'Température';
  const valTemp = document.createElement('span');
  valTemp.className = 'rd-champ-val';
  valTemp.textContent = formatTemp(rec.temperature_camion);
  chTemp.appendChild(lblTemp);
  chTemp.appendChild(valTemp);
  rowCamion.appendChild(chTemp);

  const chProp = document.createElement('div');
  chProp.className = 'rd-champ';
  const lblProp = document.createElement('span');
  lblProp.className = 'rd-champ-label';
  lblProp.textContent = 'Propreté';
  const valProp = document.createElement('span');
  valProp.className = 'rd-champ-val';
  const propTxt = rec.proprete_camion === 'satisfaisant' ? '✓ Satisfaisante' : '✗ Non satisfaisante';
  valProp.textContent = propTxt;
  if (rec.proprete_camion !== 'satisfaisant') {
    const badge = document.createElement('span');
    badge.className = 'rd-badge nc';
    badge.textContent = '⚠️ NC';
    valProp.appendChild(badge);
  }
  chProp.appendChild(lblProp);
  chProp.appendChild(valProp);
  rowCamion.appendChild(chProp);

  secCamion.appendChild(rowCamion);

  elMain.appendChild(secCamion);

  // Photo BL
  if (rec.photo_bl_filename) {
    const btnBL = document.createElement('div');
    btnBL.style.cssText = 'margin-bottom:16px;';
    const btnBLClick = document.createElement('button');
    btnBLClick.style.cssText = 'background:var(--secondaire);color:var(--texte);border:none;border-radius:8px;padding:10px 14px;font-size:15px;font-weight:700;cursor:pointer;width:100%;';
    btnBLClick.textContent = '📋 Voir le bon de livraison';
    btnBLClick.addEventListener('click', () => {
      elModalImg.src = `/api/receptions/${receptionId}/photo-bl`;
      elModalImg.alt = 'Bon de livraison';
      elModal.hidden = false;
      document.body.style.overflow = 'hidden';
    });
    btnBL.appendChild(btnBLClick);
    elMain.appendChild(btnBL);
  }

  // ── Section Produits ────────────────────────────────────
  const secProd = document.createElement('div');
  secProd.className = 'rd-section';

  const titProd = document.createElement('div');
  titProd.className = 'rd-section-titre';
  titProd.textContent = `Produits réceptionnés (${(rec.lignes || []).length})`;
  secProd.appendChild(titProd);

  const divLignes = document.createElement('div');
  divLignes.className = 'rd-lignes';

  if (!rec.lignes || rec.lignes.length === 0) {
    const vide = document.createElement('div');
    vide.style.cssText = 'padding:8px;color:#888;';
    vide.textContent = 'Aucun produit enregistré.';
    divLignes.appendChild(vide);
  } else {
    rec.lignes.forEach(lig => divLignes.appendChild(creerLigne(lig, rec.fournisseur_nom)));
  }

  secProd.appendChild(divLignes);
  elMain.appendChild(secProd);

  // ── Section Commentaire ────────────────────────────────
  if (rec.commentaire_nc) {
    const secCmt = document.createElement('div');
    secCmt.className = 'rd-section';

    const titCmt = document.createElement('div');
    titCmt.className = 'rd-section-titre';
    titCmt.textContent = 'Commentaire NC';
    secCmt.appendChild(titCmt);

    const txtCmt = document.createElement('div');
    txtCmt.style.cssText = 'font-size:15px;line-height:1.5;';
    txtCmt.textContent = rec.commentaire_nc;
    secCmt.appendChild(txtCmt);

    elMain.appendChild(secCmt);
  }

}

function creerLigne(lig, receptionFournisseurNom = null) {
  const estNC = lig.conforme === 0;

  const div = document.createElement('div');
  div.className = `rd-ligne ${estNC ? 'nc' : ''}`;

  const entete = document.createElement('div');
  entete.className = 'rd-ligne-entete';

  const gauche = document.createElement('div');
  const nom = document.createElement('div');
  nom.className = 'rd-ligne-nom';
  nom.textContent = lig.produit_nom || '—';
  gauche.appendChild(nom);
  if (lig.espece) {
    const esp = document.createElement('div');
    esp.className = 'rd-ligne-espece';
    esp.textContent = lig.espece;
    gauche.appendChild(esp);
  }
  entete.appendChild(gauche);

  const badge = document.createElement('span');
  badge.className = `rd-ligne-badge ${estNC ? 'nc' : ''}`;
  badge.textContent = estNC ? '✗ NC' : '✓ OK';
  entete.appendChild(badge);
  div.appendChild(entete);

  const grille = document.createElement('div');
  grille.className = 'rd-ligne-grille';

  const champs = [
    { label: 'Fournisseur', valeur: lig.fournisseur_nom || receptionFournisseurNom || '—' },
    { label: 'N° lot', valeur: lig.numero_lot || '—' },
    { label: 'DLC', valeur: formatDateFR(lig.dlc) },
    { label: 'Origine', valeur: lig.origine || '—' },
    { label: 'T° réception', valeur: formatTemp(lig.temperature_reception) },
    { label: 'T° à cœur', valeur: formatTemp(lig.temperature_coeur) },
  ];
  if (lig.ph_valeur !== null && lig.ph_valeur !== undefined) {
    champs.push({ label: 'pH', valeur: String(lig.ph_valeur) });
  }

  champs.forEach(({ label, valeur }) => {
    const c = document.createElement('div');
    const lbl = document.createElement('div');
    lbl.className = 'rd-ligne-champ-label';
    lbl.textContent = label;
    const val = document.createElement('div');
    val.className = 'rd-ligne-champ-val';
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
      nc.className = 'rd-criteres';
      nc.textContent = criteres.join(' — ');
      div.appendChild(nc);
    }
  }

  return div;
}

// ── Modal ────────────────────────────────────────────────────
elModal.addEventListener('click', () => {
  elModal.hidden = true;
  elModalImg.src = '';
  document.body.style.overflow = '';
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !elModal.hidden) {
    elModal.hidden = true;
    elModalImg.src = '';
    document.body.style.overflow = '';
  }
});

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

  // Nettoyer les clés localStorage orphelines (lignes validées ou non_recu)
  const ligneIdsActifs = new Set(toutesLignes.map(l => String(l.ligne_id)));
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const key = localStorage.key(i);
    if (key && key.startsWith('pa_carte_')) {
      const id = key.replace('pa_carte_', '');
      if (!ligneIdsActifs.has(id)) localStorage.removeItem(key);
    }
  }

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
    <button class="pa-groupe-lots" type="button" title="Fournisseur sans N° de lot : génère un lot interne pour tous les produits en attente de cette réception">🏷️ Lot interne sur toute la commande</button>
  `;
  const btnOcr = tete.querySelector('.pa-groupe-reprendre');
  btnOcr.addEventListener('click', () => lancerOcrGroupe(g, btnOcr, statut));

  const btnLots = tete.querySelector('.pa-groupe-lots');
  btnLots.addEventListener('click', () => genererLotsCommande(g, btnLots, statut));

  const statut = document.createElement('div');
  statut.className = 'pa-groupe-statut';
  statut.hidden = true;

  // Aperçu du BL enregistré (vignettes de toutes les pages) + N° BL editable — chargé en différé.
  const blZone = document.createElement('div');
  blZone.className = 'pa-bl';
  const blLabel = document.createElement('span');
  blLabel.className = 'pa-bl-label';
  blLabel.textContent = '📎 BL…';
  blZone.appendChild(blLabel);

  const blNumeroZone = document.createElement('div');
  blNumeroZone.style.cssText = 'display:flex;align-items:center;gap:8px;margin-top:4px;';
  blZone.appendChild(blNumeroZone);

  chargerApercuBl(g.reception_id, blZone, blNumeroZone);

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
async function chargerApercuBl(receptionId, zone, blNumeroZone) {
  // Nettoyer les anciens éléments générés (vignettes + bouton d'ajout)
  // Garder : label et blNumeroZone
  const children = Array.from(zone.childNodes);
  children.forEach((child, idx) => {
    if (idx > 1) { // Skip label (0) et blNumeroZone (1)
      child.remove();
    }
  });

  let data;
  try {
    data = await apiFetch(`/api/receptions/${receptionId}/bl-apercu`);
  } catch {
    const span = zone.querySelector('.pa-bl-label');
    if (span) span.textContent = '⚠️ BL indisponible';
    ajouterBoutonAjoutBl(receptionId, zone);
    return;
  }

  const pages = data.pages || [];
  const label = zone.querySelector('.pa-bl-label');
  if (label) {
    label.textContent = pages.length
      ? `📎 BL — ${pages.length} page(s) :`
      : '⚠️ Aucune photo de BL — ajoutez-la ci-contre';
  }

  // Vignettes des pages
  const divVignettes = document.createElement('div');
  divVignettes.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;';
  const urls = pages.map(p => p.url);
  pages.forEach((p, idx) => {
    const wrapper = document.createElement('div');
    wrapper.style.cssText = 'position:relative;display:inline-block;';

    const img = document.createElement('img');
    img.className = 'pa-bl-vignette';
    img.src = p.url;
    img.alt = `BL page ${idx + 1}`;
    img.title = `Voir la page ${idx + 1}`;
    img.style.cssText = 'width:54px;height:54px;object-fit:cover;border-radius:8px;border:2px solid #6B3A1F;cursor:pointer;background:#f0e6d2;display:block;';
    img.addEventListener('click', () => ouvrirViewer(urls, idx));
    wrapper.appendChild(img);

    // Bouton supprimer (coin haut-droit) — uniquement pour les pages multi-pages avec page_id
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
          await chargerApercuBl(receptionId, zone, blNumeroZone);
        } catch (err) {
          alert('Suppression impossible : ' + err.message);
          btnSup.disabled = false;
        }
      });
      wrapper.appendChild(btnSup);
    }

    divVignettes.appendChild(wrapper);
  });
  zone.appendChild(divVignettes);

  // Widget N° de BL editable
  if (blNumeroZone) {
    ajouterWidgetNumeroBl(receptionId, blNumeroZone, data.numero_bon_livraison || '');
  }

  ajouterBoutonAjoutBl(receptionId, zone);
}

// ── Widget N° de BL editable ──────────────────────────────
function ajouterWidgetNumeroBl(receptionId, zone, numeroBl) {
  const wrapper = document.createElement('div');
  wrapper.style.cssText = 'display:flex;align-items:center;gap:6px;font-size:13px;';

  const label = document.createElement('span');
  label.style.cssText = 'color:#8a6d54;font-weight:600;';
  label.textContent = 'N° BL :';
  wrapper.appendChild(label);

  const display = document.createElement('span');
  display.style.cssText = 'color:#3D2008;font-weight:700;min-width:80px;';
  display.textContent = numeroBl || '(non saisi)';

  const btnEdit = document.createElement('button');
  btnEdit.type = 'button';
  btnEdit.style.cssText = 'background:none;border:none;color:#6B3A1F;cursor:pointer;font-size:13px;font-weight:700;padding:2px 4px;';
  btnEdit.textContent = '✏️';

  let editing = false;
  btnEdit.addEventListener('click', async () => {
    if (editing) return;
    editing = true;
    btnEdit.disabled = true;

    const input = document.createElement('input');
    input.type = 'text';
    input.value = numeroBl || '';
    input.style.cssText = 'border:2px solid #6B3A1F;border-radius:6px;font-size:13px;padding:4px 8px;width:100px;';
    input.placeholder = 'N° BL…';

    const btnVal = document.createElement('button');
    btnVal.type = 'button';
    btnVal.textContent = '✓';
    btnVal.style.cssText = 'background:#2D7D46;border:none;border-radius:6px;color:#FFF;cursor:pointer;font-size:12px;font-weight:700;height:32px;width:32px;margin-left:4px;';

    const btnAnn = document.createElement('button');
    btnAnn.type = 'button';
    btnAnn.textContent = '✕';
    btnAnn.style.cssText = 'background:#C93030;border:none;border-radius:6px;color:#FFF;cursor:pointer;font-size:12px;font-weight:700;height:32px;width:32px;';

    wrapper.innerHTML = '';
    wrapper.appendChild(label);
    wrapper.appendChild(input);
    wrapper.appendChild(btnVal);
    wrapper.appendChild(btnAnn);

    input.focus();
    input.select();

    async function valider() {
      const newNum = input.value.trim();
      if (newNum === numeroBl) {
        annuler();
        return;
      }
      btnVal.disabled = true;
      btnAnn.disabled = true;
      try {
        await apiFetch(`/api/receptions/${receptionId}/numero-bl`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ numero_bon_livraison: newNum }),
        });
        numeroBl = newNum;
        display.textContent = newNum || '(non saisi)';
        annuler();
      } catch (err) {
        alert('Erreur : ' + err.message);
        btnVal.disabled = false;
        btnAnn.disabled = false;
      }
    }

    function annuler() {
      editing = false;
      btnEdit.disabled = false;
      wrapper.innerHTML = '';
      wrapper.appendChild(label);
      wrapper.appendChild(display);
      wrapper.appendChild(btnEdit);
    }

    btnVal.addEventListener('click', valider);
    btnAnn.addEventListener('click', annuler);
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') valider();
      else if (e.key === 'Escape') annuler();
    });
  });

  wrapper.appendChild(display);
  wrapper.appendChild(btnEdit);
  zone.appendChild(wrapper);
}

// Zone « + Ajouter une/des page(s) de BL » — utilise ouvrirChoixPhoto (camera.js).
// Après chaque envoi réussi, l'aperçu se recharge et le bouton reste disponible
// pour enchaîner immédiatement une nouvelle page.
function ajouterBoutonAjoutBl(receptionId, zone) {
  // Vérifier si un bouton d'ajout existe déjà
  if (zone.querySelector('.pa-bl-ajout')) {
    return; // Bouton déjà présent, ne pas en ajouter un autre
  }

  const input = document.createElement('input');
  input.type   = 'file';
  input.accept = 'image/*,application/pdf';
  input.hidden = true;

  const btn = document.createElement('button');
  btn.type      = 'button';
  btn.className = 'pa-bl-ajout';
  btn.textContent = '＋ Ajouter une page';

  btn.addEventListener('click', () => {
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
    btn.disabled    = true;
    btn.textContent = '⏳ Envoi…';
    const fd = new FormData();
    fd.append('fichier', file, file.name);
    try {
      await apiFetch(`/api/receptions/${receptionId}/bl-pages`, { method: 'POST', body: fd });
      // Recharger l'aperçu — blNumeroZone est le 2e enfant (après label)
      const blNumeroZone = zone.childNodes[1];
      await chargerApercuBl(receptionId, zone, blNumeroZone);
    } catch (e) {
      btn.disabled    = false;
      btn.textContent = '＋ Ajouter une page';
      alert('Ajout du BL impossible : ' + e.message);
    }
    // Réinitialiser l'input pour permettre une nouvelle sélection du même fichier
    input.value = '';
  });

  zone.appendChild(btn);
  zone.appendChild(input);
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
  const barre = demarrerBarreOcr(statut);

  let data;
  try {
    data = await apiFetch(`/api/receptions/${g.reception_id}/ocr-bl`, { method: 'POST' });
    barre.terminer();
  } catch (e) {
    barre.annuler();
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

    // On ne pré-remplit que la 1re section (l'OCR ne sépare pas encore les lots ici).
    const sect0 = carte.querySelector('.pa-section-lot-dlc:first-child') || carte;
    const inpLot  = sect0.querySelector('[data-field="numero_lot"]');
    // Champ date selon le type paramétré de l'article :
    //  - dlc            → [data-field="dlc"]
    //  - date_abattage  → [data-field="date_abattage"] (la date lue sur le BL fait foi)
    //  - no_dlc         → aucun champ date (le lot seul suffit à lever l'attente)
    const inpDate  = sect0.querySelector('[data-field="dlc"], [data-field="date_abattage"]');
    const inpPoids = sect0.querySelector('[data-field="poids_kg"]');
    let rempli = false;
    if (inpLot && art.numero_lot) { inpLot.value = art.numero_lot; rempli = true; }
    // Date à appliquer : DLC pour un article 'dlc', sinon la date lue (DLC ou DLUO)
    // sert de date d'abattage pour un article 'date_abattage'.
    const dateOcr = ligne.dlc_type === 'date_abattage'
      ? (art.dlc || art.dluo || '')
      : (ligne.dlc_type === 'no_dlc' ? '' : (art.dlc || ''));
    if (inpDate && dateOcr) { inpDate.value = dateOcr; rempli = true; }
    // Poids lu sur le BL : ne remplace pas un poids déjà saisi.
    if (inpPoids && art.poids_kg != null && !inpPoids.value.trim()) { inpPoids.value = art.poids_kg; rempli = true; }
    if (rempli) {
      nbRemplis++;
      // Sauvegarder les données pré-remplies par l'OCR
      sauvegarderSectionsCarte(carte, ligne.ligne_id);
    }

    // Article « date d'abattage » : une date antérieure à la livraison est NORMALE.
    // L'OCR (sans connaissance du type) la signale à tort → on neutralise l'alerte.
    const fauxSuspectAbattage = ligne.dlc_type === 'date_abattage'
      && /antérieure à la livraison/i.test(art.alerte || '');

    if (art.dlc_suspecte && !fauxSuspectAbattage) {
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

// Barre de progression « estimée » pour l'OCR : l'extraction est un appel unique
// (analyse Claude vision, ~15-30 s) dont on ne connaît pas l'avancement réel. On
// anime donc une barre qui monte progressivement vers 90 % sur une durée typique,
// puis se complète à 100 % à la réception de la réponse. But : donner à l'utilisateur
// un repère « combien de temps attendre » plutôt qu'un simple ⏳ figé.
// `ancre` : élément après lequel la barre est insérée (comme frère).
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
    .ocr-barre { margin-top:.5rem; }
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

// ── Lot interne sur toute la réception ─────────────────────
// Fournisseur sans N° de lot : génère un lot interne {BL}-{code}-{JJMMAA} pour
// toutes les lignes en attente de cette réception qui n'ont pas de lot. Exige le
// n° BL (préfixe) ; s'il manque, on le demande et on l'enregistre avant.
async function genererLotsCommande(g, btn, statut) {
  // n° BL de la réception (porté par chaque ligne du groupe).
  let numeroBl = ((g.lignes[0] && g.lignes[0].numero_bon_livraison) || '').trim();
  if (!numeroBl) {
    const saisi = window.prompt(
      'N° du bon de livraison de cette réception (sert de préfixe aux lots internes) :',
      ''
    );
    if (saisi === null) return;             // annulé
    numeroBl = saisi.trim();
    if (!numeroBl) {
      statut.hidden = false;
      statut.className = 'pa-groupe-statut erreur';
      statut.textContent = '⚠️ N° de bon de livraison requis pour générer les lots internes.';
      return;
    }
    try {
      await apiFetch(`/api/receptions/${g.reception_id}/numero-bl`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ numero_bon_livraison: numeroBl }),
      });
      // Propager le BL au cache local (toutes les lignes de la réception).
      toutesLignes.forEach(l => {
        if (l.reception_id === g.reception_id) l.numero_bon_livraison = numeroBl;
      });
    } catch (e) {
      statut.hidden = false;
      statut.className = 'pa-groupe-statut erreur';
      statut.textContent = 'Enregistrement du n° BL impossible : ' + e.message;
      return;
    }
  }

  btn.disabled = true;
  const labelInit = btn.textContent;
  btn.textContent = '⏳ Génération…';
  statut.hidden = false;
  statut.className = 'pa-groupe-statut';
  statut.textContent = 'Génération des lots internes…';

  let res;
  try {
    res = await apiFetch(`/api/receptions/${g.reception_id}/lots-internes`, { method: 'POST' });
  } catch (e) {
    btn.disabled = false;
    btn.textContent = labelInit;
    statut.className = 'pa-groupe-statut erreur';
    statut.textContent = 'Génération impossible : ' + e.message;
    return;
  }

  // Nettoyer le localStorage des lignes de cette réception (lot désormais en base).
  g.lignes.forEach(l => effacerDonneesCarte(l.ligne_id));

  statut.className = res.restant_attente ? 'pa-groupe-statut' : 'pa-groupe-statut ok';
  statut.textContent =
    `✓ ${res.generes} lot(s) interne(s) généré(s)`
    + (res.restant_attente
        ? ` — ⚠️ ${res.restant_attente} produit(s) encore en attente (DLC / date d'abattage à compléter).`
        : ' — réception tracée.');

  // Recharger la file : les lignes complétées (lot + date OK) disparaissent.
  await charger();
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

// ── Sauvegarde sections d'une carte ────────────────────────
function sauvegarderSectionsCarte(carte, ligneId) {
  const sections = [];
  carte.querySelectorAll('.pa-section-lot-dlc').forEach(sect => {
    const donnees = {};
    sect.querySelectorAll('.pa-input').forEach(inp => {
      if (inp.value.trim()) donnees[inp.dataset.field] = inp.value.trim();
    });
    if (Object.keys(donnees).length > 0) sections.push(donnees);
  });
  if (sections.length > 0) sauvegarderDonneesCarte(ligneId, { sections });
}

// ── Ajouter une section lot/DLC supplémentaire ────────────
function ajouterSection(carte, ligne) {
  const conteneur = carte.querySelector('.pa-sections-lot-dlc');
  const dateAbattage = ligne.dlc_type === 'date_abattage';
  const noDlc = ligne.dlc_type === 'no_dlc';
  const nbSections = conteneur.querySelectorAll('.pa-section-lot-dlc').length;

  const section = document.createElement('div');
  section.className = 'pa-section-lot-dlc';
  section.dataset.sectionIdx = nbSections;
  section.innerHTML = `
    <button class="pa-btn-supprimer-section" type="button" title="Supprimer cette entrée">✕</button>
    <div class="pa-champ">
      <label class="pa-champ-label">N° de lot</label>
      <input type="text" class="pa-input" data-field="numero_lot" placeholder="N° de lot…">
    </div>
    <div class="pa-champ"${noDlc ? ' hidden' : ''}>
      <label class="pa-champ-label">${dateAbattage ? "Date d'abattage" : 'DLC'}</label>
      <input type="date" class="pa-input" data-field="${dateAbattage ? 'date_abattage' : 'dlc'}">
    </div>
    <div class="pa-champ">
      <label class="pa-champ-label">Poids (kg)</label>
      <input type="number" step="0.01" min="0" inputmode="decimal"
             class="pa-input" data-field="poids_kg" placeholder="kg">
    </div>
  `;

  section.querySelector('.pa-btn-supprimer-section').addEventListener('click', () => {
    section.remove();
    sauvegarderSectionsCarte(carte, ligne.ligne_id);
  });

  section.querySelectorAll('.pa-input').forEach(inp => {
    inp.addEventListener('input',  () => sauvegarderSectionsCarte(carte, ligne.ligne_id));
    inp.addEventListener('change', () => sauvegarderSectionsCarte(carte, ligne.ligne_id));
  });

  conteneur.appendChild(section);
}

// ── Stockage localStorage des données de cartes ────────────
function sauvegarderDonneesCarte(ligneId, donnees) {
  const key = `pa_carte_${ligneId}`;
  localStorage.setItem(key, JSON.stringify(donnees));
}

function chargerDonneesCarte(ligneId) {
  const key = `pa_carte_${ligneId}`;
  const data = localStorage.getItem(key);
  return data ? JSON.parse(data) : null;
}

function effacerDonneesCarte(ligneId) {
  const key = `pa_carte_${ligneId}`;
  localStorage.removeItem(key);
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

    <div class="pa-sections-lot-dlc" data-ligne-id="${ligne.ligne_id}">
      <div class="pa-section-lot-dlc" data-section-idx="0">
        <div class="pa-champ">
          <label class="pa-champ-label">N° de lot</label>
          <input type="text" class="pa-input" data-field="numero_lot"
                 placeholder="N° de lot du bon de livraison…">
          <button class="pa-btn-lot-interne" type="button">
            🏷️ Pas de N° de lot → générer un lot interne
          </button>
        </div>

        <div class="pa-champ"${ligne.dlc_type === 'no_dlc' ? ' hidden' : ''}>
          <label class="pa-champ-label">${dateAbattage ? "Date d'abattage" : 'DLC'}</label>
          <input type="date" class="pa-input"
                 data-field="${dateAbattage ? 'date_abattage' : 'dlc'}">
        </div>

        <div class="pa-champ">
          <label class="pa-champ-label">Poids (kg)</label>
          <input type="number" step="0.01" min="0" inputmode="decimal"
                 class="pa-input" data-field="poids_kg" placeholder="kg"
                 value="${ligne.poids_kg != null ? ligne.poids_kg : ''}">
        </div>
      </div>
    </div>

    <button class="pa-btn-ajouter-section" type="button">＋ Ajouter un autre lot</button>

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

  // Restaurer les données sauvegardées en localStorage
  const donneesSauvegardees = chargerDonneesCarte(ligne.ligne_id);
  if (donneesSauvegardees) {
    // Normaliser : ancien format {numero_lot, dlc} → nouveau {sections: [...]}
    const sections = donneesSauvegardees.sections
      || [{ numero_lot: donneesSauvegardees.numero_lot, dlc: donneesSauvegardees.dlc,
            date_abattage: donneesSauvegardees.date_abattage }];

    sections.forEach((section, idx) => {
      if (idx > 0) ajouterSection(carte, ligne);
      const sectionDiv = carte.querySelector(`[data-section-idx="${idx}"]`);
      if (sectionDiv) {
        Object.entries(section).forEach(([field, value]) => {
          if (!value) return;
          const inp = sectionDiv.querySelector(`[data-field="${field}"]`);
          if (inp) inp.value = value;
        });
      }
    });
  }

  // Listeners sauvegarde sur les inputs de la première section
  carte.querySelectorAll('.pa-section-lot-dlc:first-child .pa-input').forEach(inp => {
    inp.addEventListener('input',  () => sauvegarderSectionsCarte(carte, ligne.ligne_id));
    inp.addEventListener('change', () => sauvegarderSectionsCarte(carte, ligne.ligne_id));
  });

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

  // Bouton "Ajouter une section" pour plusieurs lots/DLC
  const btnAjouterSection = carte.querySelector('.pa-btn-ajouter-section');
  if (btnAjouterSection) {
    btnAjouterSection.addEventListener('click', () => {
      ajouterSection(carte, ligne);
    });
  }

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
    // Sauvegarder le lot interne généré
    sauvegarderSectionsCarte(carte, ligne.ligne_id);
  } catch (e) {
    erreur.textContent = 'Génération du lot interne impossible : ' + e.message;
    erreur.hidden = false;
  } finally {
    btnLot.disabled = false;
    btnLot.textContent = labelInit;
  }
}

// ── Validation / complétion ────────────────────────────────
// Chaque section = 1 lot (lot + DLC/date + poids propres). La ligne d'origine
// prend la 1re section ; les sections suivantes créent des lignes clonées via
// l'endpoint /multi. Une ligne par lot entre alors séparément en stock.
async function valider(carte, ligne, btn, erreur) {
  erreur.hidden = true;

  const dateAbattage = attendDateAbattage(ligne);
  const noDlc        = ligne.dlc_type === 'no_dlc';
  const premiereSect = carte.querySelector('.pa-section-lot-dlc:first-child');

  // Collecter + valider chaque section.
  const sections = [];
  let invalide = false;
  carte.querySelectorAll('.pa-section-lot-dlc').forEach(sect => {
    const payload = {};
    const inputs = sect.querySelectorAll('.pa-input');
    inputs.forEach(inp => {
      inp.classList.remove('pa-input--invalide');
      const v = inp.value.trim();
      if (v) payload[inp.dataset.field] = v;
    });

    const manqueLot  = !payload.numero_lot;
    const manqueDate = !noDlc && !(dateAbattage ? payload.date_abattage : payload.dlc);
    // Poids obligatoire et > 0 pour chaque lot (chacun a son propre poids pesé).
    const poidsNum   = parseFloat(payload.poids_kg);
    const manquePoids = !(poidsNum > 0);

    if (manqueLot || manqueDate || manquePoids) {
      invalide = true;
      inputs.forEach(inp => {
        if ((inp.dataset.field === 'numero_lot' && manqueLot) ||
            ((inp.dataset.field === 'dlc' || inp.dataset.field === 'date_abattage') && manqueDate) ||
            (inp.dataset.field === 'poids_kg' && manquePoids)) {
          inp.classList.add('pa-input--invalide');
        }
      });
      return;
    }

    // Lot auto-généré (interne) : marqué au niveau de la première section.
    if (sect === premiereSect && carte.dataset.lotInterne === '1') {
      payload.lot_interne = 1;
    }
    // Normaliser le poids en nombre pour le backend.
    payload.poids_kg = poidsNum;
    sections.push(payload);
  });

  if (invalide) {
    erreur.textContent = 'Chaque lot doit avoir son N° de lot, sa date'
      + (noDlc ? '' : ' (DLC / abattage)') + ' et son poids (kg).';
    erreur.hidden = false;
    return;
  }
  if (sections.length === 0) {
    erreur.textContent = 'Renseignez au moins un lot avec sa date et son poids.';
    erreur.hidden = false;
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Validation…';
  try {
    const res = await apiFetch(`/api/attente/lignes/${ligne.ligne_id}/multi`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sections }),
    });
    if (res.en_attente > 0) {
      erreur.textContent = `${res.en_attente} lot(s) encore incomplet(s) — vérifiez lot et date.`;
      erreur.hidden = false;
      btn.disabled = false;
      btn.textContent = '✓ Valider et entrer en stock';
      // Recharger pour refléter l'état réel (certaines lignes ont pu être créées).
      await charger();
      return;
    }

    // Tous les lots sont complets → retirer la ligne de la file.
    effacerDonneesCarte(ligne.ligne_id);
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
    erreur.textContent = 'Erreur lors de l\'enregistrement. Réessayez.';
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
    // Nettoyer le localStorage et retirer de la source de vérité
    effacerDonneesCarte(ligne.ligne_id);
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

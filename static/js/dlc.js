'use strict';
/* ============================================================
   dlc.js — Calendrier mensuel DLC
   Sources : reception_lignes.dlc + fabrications.dlc_finale
   ============================================================ */

const $ = (id) => document.getElementById(id);

function escHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function ymd(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const j = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${j}`;
}

function parseYmd(s) {
  const [y, m, j] = s.split('-').map(Number);
  return new Date(y, m - 1, j);
}

function formatDateFr(s) {
  if (!s) return '—';
  try { return parseYmd(s).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' }); }
  catch { return s; }
}

function joursEntre(d1, d2) {
  // d1 et d2 : Date à minuit local
  const MS = 1000 * 60 * 60 * 24;
  return Math.round((d2 - d1) / MS);
}

// ── État ────────────────────────────────────────────────
const state = {
  moisCourant: new Date(),   // premier jour du mois affiché
  items: [],
  seuils: { rouge_jours: 1, orange_jours: 3, jaune_jours: 7 },
  filtres: { source: '', statut: '' },
  personnel: [],
  devenirCible: null,        // { source_type, source_id, produit_nom, dlc, ... }
  devenirStatut: null,
};

// ── Horloge ─────────────────────────────────────────────
function tickHorloge() {
  const el = $('dlc-horloge');
  if (!el) return;
  el.textContent = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}
setInterval(tickHorloge, 30000);
tickHorloge();

// ── Chargement ──────────────────────────────────────────
async function chargerCalendrier() {
  const loader = $('dlc-loader');
  const err    = $('dlc-error');
  loader.hidden = false;
  err.hidden = true;

  // Grille complète : du lundi de la 1re semaine au dimanche de la dernière
  const premier = new Date(state.moisCourant.getFullYear(), state.moisCourant.getMonth(), 1);
  const dernier = new Date(state.moisCourant.getFullYear(), state.moisCourant.getMonth() + 1, 0);
  const debut = new Date(premier);
  // lundi = 1 ... dimanche = 0 → décaler pour commencer au lundi
  const offset = (premier.getDay() + 6) % 7;
  debut.setDate(debut.getDate() - offset);
  const fin = new Date(dernier);
  const offsetFin = (7 - dernier.getDay()) % 7;
  fin.setDate(fin.getDate() + offsetFin);

  const params = new URLSearchParams({
    date_debut: ymd(debut),
    date_fin: ymd(fin),
  });
  if (state.filtres.source)   params.set('source', state.filtres.source);

  try {
    const res = await fetch(`/api/dlc/calendrier?${params}`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.items = data.items || [];
    state.seuils = data.seuils || state.seuils;
    renderCalendrier(debut, fin);
  } catch (e) {
    err.hidden = false;
    err.textContent = `Erreur chargement : ${e.message}`;
  } finally {
    loader.hidden = true;
  }
}

async function chargerPersonnel() {
  try {
    const res = await fetch('/api/admin/personnel', { cache: 'no-store' });
    if (res.ok) state.personnel = await res.json();
  } catch { state.personnel = []; }
}

// ── Calculs couleur ─────────────────────────────────────
function niveauAlerte(dlcStr, aujourdhui) {
  const dlc = parseYmd(dlcStr);
  const jours = joursEntre(aujourdhui, dlc);
  const s = state.seuils;
  if (jours < 0)               return 'rouge';   // dépassée (critique)
  if (jours <= s.rouge_jours)  return 'rouge';
  if (jours <= s.orange_jours) return 'orange';
  if (jours <= s.jaune_jours)  return 'jaune';
  return 'vert';
}

function passeFiltreStatut(item, aujourdhui) {
  const dlc = parseYmd(item.dlc);
  const expire = dlc < aujourdhui;
  const traite = !!item.devenir_statut;
  switch (state.filtres.statut) {
    case 'a_traiter': return expire && !traite;
    case 'traite':    return traite;
    case 'actif':     return !expire;
    default:          return true;
  }
}

// ── Rendu grille ────────────────────────────────────────
function renderCalendrier(debut, fin) {
  const body = $('dlc-grille-body');
  body.innerHTML = '';
  const label = $('dlc-mois-label');
  label.textContent = state.moisCourant.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });

  const aujourdhui = new Date();
  aujourdhui.setHours(0, 0, 0, 0);

  // Index items par date
  const parDate = {};
  state.items.filter(it => passeFiltreStatut(it, aujourdhui)).forEach(it => {
    if (!parDate[it.dlc]) parDate[it.dlc] = [];
    parDate[it.dlc].push(it);
  });

  const moisCible = state.moisCourant.getMonth();
  const cur = new Date(debut);
  while (cur <= fin) {
    const key = ymd(cur);
    const items = parDate[key] || [];
    const autreMois = cur.getMonth() !== moisCible;
    const estAujourdhui = key === ymd(aujourdhui);

    const case_ = document.createElement('div');
    const cls = ['dlc-jour'];
    if (autreMois) cls.push('dlc-jour--autre-mois');
    if (estAujourdhui) cls.push('dlc-jour--aujourdhui');
    case_.className = cls.join(' ');
    case_.dataset.date = key;

    // Compteurs par niveau
    const compteurs = { rouge: 0, orange: 0, jaune: 0, vert: 0, gris: 0 };
    items.forEach(it => {
      if (it.devenir_statut) { compteurs.gris += 1; return; }
      compteurs[niveauAlerte(it.dlc, aujourdhui)] += 1;
    });

    let badgesHtml = '';
    const aDepassees = items.some(it => !it.devenir_statut && parseYmd(it.dlc) < aujourdhui);
    ['rouge', 'orange', 'jaune', 'vert', 'gris'].forEach(n => {
      if (compteurs[n] > 0) {
        const extra = (n === 'rouge' && aDepassees) ? ' clignotant' : '';
        badgesHtml += `<span class="dlc-badge dlc-badge--${n}${extra}">${compteurs[n]}</span>`;
      }
    });

    case_.innerHTML = `
      <div class="dlc-jour-num">${cur.getDate()}</div>
      <div class="dlc-jour-badges">${badgesHtml}</div>
    `;

    if (items.length > 0) {
      case_.addEventListener('click', () => ouvrirModalJour(key, items));
    } else {
      case_.classList.add('dlc-jour--vide');
    }

    body.appendChild(case_);
    cur.setDate(cur.getDate() + 1);
  }
}

// ── Modal liste du jour ─────────────────────────────────
function ouvrirModalJour(dateStr, items) {
  const aujourdhui = new Date();
  aujourdhui.setHours(0, 0, 0, 0);

  $('dlc-modal-titre').textContent = `DLC du ${formatDateFr(dateStr)}`;
  const body = $('dlc-modal-body');
  body.innerHTML = '';

  items.forEach(it => {
    const niveau = it.devenir_statut ? 'gris' : niveauAlerte(it.dlc, aujourdhui);
    const expire = parseYmd(it.dlc) < aujourdhui;
    const aTraiter = expire && !it.devenir_statut;
    const sourceLabel = it.source_type === 'fabrication' ? 'Fabrication' : 'Réception';
    const sourceCls = it.source_type === 'fabrication' ? 'fabrication' : 'reception';

    const meta = [];
    if (it.numero_lot)       meta.push(`Lot : ${escHtml(it.numero_lot)}`);
    if (it.quantite != null) meta.push(`${it.quantite} ${escHtml(it.unite || '')}`);
    if (it.fournisseur_nom)  meta.push(`Frn : ${escHtml(it.fournisseur_nom)}`);
    if (it.date_origine)     meta.push(`Origine : ${formatDateFr(it.date_origine)}`);

    const devenirHtml = it.devenir_statut
      ? `<div class="dlc-item-devenir">
           ✓ ${escHtml(statutLabel(it.devenir_statut))}
           ${it.devenir_prenom ? `— ${escHtml(it.devenir_prenom)}` : ''}
           ${it.devenir_at ? `le ${new Date(it.devenir_at).toLocaleDateString('fr-FR')}` : ''}
           ${it.devenir_commentaire ? `<br><em>« ${escHtml(it.devenir_commentaire)} »</em>` : ''}
         </div>`
      : '';

    const btnHtml = aTraiter
      ? `<button class="dlc-item-btn-devenir"
                 data-src-type="${escHtml(it.source_type)}"
                 data-src-id="${it.source_id}"
                 data-nom="${escHtml(it.produit_nom)}"
                 data-dlc="${escHtml(it.dlc)}">
           📝 Enregistrer devenir
         </button>`
      : '';

    const el = document.createElement('div');
    el.className = `dlc-item dlc-item--${niveau}`;
    el.innerHTML = `
      <div class="dlc-item-titre">${escHtml(it.produit_nom)}</div>
      <div class="dlc-item-meta">
        <span class="dlc-item-source dlc-item-source--${sourceCls}">${sourceLabel}</span>
        ${meta.map(m => `<span>${m}</span>`).join('')}
      </div>
      ${devenirHtml}
      ${btnHtml}
    `;
    body.appendChild(el);
  });

  body.querySelectorAll('.dlc-item-btn-devenir').forEach(btn => {
    btn.addEventListener('click', () => {
      ouvrirModalDevenir({
        source_type: btn.dataset.srcType,
        source_id: parseInt(btn.dataset.srcId, 10),
        produit_nom: btn.dataset.nom,
        dlc: btn.dataset.dlc,
      });
    });
  });

  $('dlc-modal').hidden = false;
}

function statutLabel(s) {
  return { jete: 'Jeté', vendu: 'Vendu', consomme: 'Consommé', autre: 'Autre' }[s] || s;
}

function fermerModal() { $('dlc-modal').hidden = true; }
document.querySelectorAll('#dlc-modal [data-close]').forEach(e => {
  e.addEventListener('click', fermerModal);
});

// ── Modal Devenir ───────────────────────────────────────
function ouvrirModalDevenir(cible) {
  state.devenirCible = cible;
  state.devenirStatut = null;

  $('devenir-produit-nom').textContent = cible.produit_nom;
  $('devenir-produit-info').textContent = `DLC dépassée le ${formatDateFr(cible.dlc)}`;
  $('devenir-commentaire').value = '';

  // Remplir select personnel
  const sel = $('devenir-personnel');
  sel.innerHTML = '<option value="">— Sélectionner —</option>';
  state.personnel.forEach(p => {
    const label = [p.prenom, p.nom].filter(Boolean).join(' ');
    sel.innerHTML += `<option value="${p.id}">${escHtml(label)}</option>`;
  });
  sel.value = '';

  // Reset boutons statut
  document.querySelectorAll('.btn-statut').forEach(b => b.classList.remove('actif'));
  $('devenir-valider').disabled = true;

  $('devenir-modal').hidden = false;
}

function fermerModalDevenir() {
  $('devenir-modal').hidden = true;
  state.devenirCible = null;
  state.devenirStatut = null;
}
document.querySelectorAll('#devenir-modal [data-close-devenir]').forEach(e => {
  e.addEventListener('click', fermerModalDevenir);
});

document.querySelectorAll('.btn-statut').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.btn-statut').forEach(b => b.classList.remove('actif'));
    btn.classList.add('actif');
    state.devenirStatut = btn.dataset.statut;
    rafraichirBoutonValider();
  });
});

$('devenir-personnel').addEventListener('change', rafraichirBoutonValider);

function rafraichirBoutonValider() {
  const ok = state.devenirStatut && $('devenir-personnel').value;
  $('devenir-valider').disabled = !ok;
}

$('devenir-valider').addEventListener('click', async () => {
  const btn = $('devenir-valider');
  btn.disabled = true;
  btn.textContent = 'Enregistrement...';

  try {
    const res = await fetch('/api/dlc/devenir', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_type:  state.devenirCible.source_type,
        source_id:    state.devenirCible.source_id,
        statut:       state.devenirStatut,
        personnel_id: parseInt($('devenir-personnel').value, 10),
        commentaire:  $('devenir-commentaire').value.trim() || null,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    fermerModalDevenir();
    fermerModal();
    await chargerCalendrier();
  } catch (e) {
    alert(`Erreur : ${e.message}`);
  } finally {
    btn.textContent = 'Enregistrer';
    rafraichirBoutonValider();
  }
});

// ── Navigation ──────────────────────────────────────────
$('dlc-prev').addEventListener('click', () => {
  state.moisCourant = new Date(state.moisCourant.getFullYear(), state.moisCourant.getMonth() - 1, 1);
  chargerCalendrier();
});
$('dlc-next').addEventListener('click', () => {
  state.moisCourant = new Date(state.moisCourant.getFullYear(), state.moisCourant.getMonth() + 1, 1);
  chargerCalendrier();
});
$('dlc-aujourdhui').addEventListener('click', () => {
  state.moisCourant = new Date();
  chargerCalendrier();
});

$('dlc-filtre-source').addEventListener('change', (e) => {
  state.filtres.source = e.target.value;
  chargerCalendrier();
});
$('dlc-filtre-statut').addEventListener('change', (e) => {
  state.filtres.statut = e.target.value;
  chargerCalendrier();
});

// ── Init ────────────────────────────────────────────────
(async () => {
  state.moisCourant = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
  await chargerPersonnel();
  await chargerCalendrier();
})();

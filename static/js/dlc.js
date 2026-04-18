'use strict';
/* ============================================================
   dlc.js — Calendrier DLC multi-vues (semaine / mois / annuel)
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
  if (!s) return null;
  const [y, m, j] = s.split('-').map(Number);
  return new Date(y, m - 1, j);
}

function formatDateFr(s) {
  if (!s) return '—';
  try { return parseYmd(s).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' }); }
  catch { return s; }
}

function joursEntre(d1, d2) {
  return Math.round((d2 - d1) / 86400000);
}

// ── Semaine ISO : lundi au dimanche ─────────────────────
function lundiDeLaSemaine(d) {
  const c = new Date(d);
  c.setHours(0, 0, 0, 0);
  const j = (c.getDay() + 6) % 7; // 0=lun, 6=dim
  c.setDate(c.getDate() - j);
  return c;
}

// ── État ────────────────────────────────────────────────
const state = {
  vue: 'mois',           // 'semaine' | 'mois' | 'annuel'
  dateRef: new Date(),   // ancre : premier jour mois / lundi semaine / 1 jan année
  items: [],
  seuils: { rouge_jours: 1, orange_jours: 3, jaune_jours: 7 },
  filtres: { source: '', statut: '' },
  personnel: [],
  devenirCible: null,
  devenirStatut: null,
};

// ── Horloge ─────────────────────────────────────────────
function tickHorloge() {
  const el = $('dlc-horloge');
  if (el) el.textContent = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}
setInterval(tickHorloge, 30000);
tickHorloge();

// ── Calcul de la plage à charger ─────────────────────────
function computeRange() {
  const ref = state.dateRef;
  switch (state.vue) {
    case 'semaine': {
      const lundi = lundiDeLaSemaine(ref);
      const dim = new Date(lundi); dim.setDate(dim.getDate() + 6);
      return { debut: lundi, fin: dim };
    }
    case 'annuel': {
      const debut = new Date(ref.getFullYear(), 0, 1);
      const fin   = new Date(ref.getFullYear(), 11, 31);
      return { debut, fin };
    }
    default: { // mois
      const premier = new Date(ref.getFullYear(), ref.getMonth(), 1);
      const dernier = new Date(ref.getFullYear(), ref.getMonth() + 1, 0);
      // padder pour grille 7 cols
      const debut = new Date(premier);
      debut.setDate(debut.getDate() - ((premier.getDay() + 6) % 7));
      const fin = new Date(dernier);
      const rest = (7 - dernier.getDay()) % 7;
      fin.setDate(fin.getDate() + rest);
      return { debut, fin };
    }
  }
}

// ── Chargement ──────────────────────────────────────────
async function chargerCalendrier() {
  $('dlc-loader').hidden = false;
  $('dlc-error').hidden = true;

  const { debut, fin } = computeRange();
  const params = new URLSearchParams({ date_debut: ymd(debut), date_fin: ymd(fin) });
  if (state.filtres.source) params.set('source', state.filtres.source);

  try {
    const res = await fetch(`/api/dlc/calendrier?${params}`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.items  = data.items  || [];
    state.seuils = data.seuils || state.seuils;
    renderVue(debut, fin);
  } catch (e) {
    $('dlc-error').hidden = false;
    $('dlc-error').textContent = `Erreur chargement : ${e.message}`;
  } finally {
    $('dlc-loader').hidden = true;
  }
}

async function chargerPersonnel() {
  try {
    const res = await fetch('/api/admin/personnel', { cache: 'no-store' });
    if (res.ok) state.personnel = await res.json();
  } catch { state.personnel = []; }
}

// ── Helpers couleur / filtre ─────────────────────────────
function niveauAlerte(dlcStr) {
  const aujourdhui = new Date(); aujourdhui.setHours(0,0,0,0);
  const dlc = parseYmd(dlcStr);
  const jours = joursEntre(aujourdhui, dlc);
  const s = state.seuils;
  if (jours < 0)               return 'rouge';
  if (jours <= s.rouge_jours)  return 'rouge';
  if (jours <= s.orange_jours) return 'orange';
  if (jours <= s.jaune_jours)  return 'jaune';
  return 'vert';
}

function passeFiltreStatut(item) {
  const aujourdhui = new Date(); aujourdhui.setHours(0,0,0,0);
  const expire = parseYmd(item.dlc) < aujourdhui;
  const traite = !!item.devenir_statut;
  switch (state.filtres.statut) {
    case 'a_traiter': return expire && !traite;
    case 'traite':    return traite;
    case 'actif':     return !expire;
    default:          return true;
  }
}

function indexParDate(items) {
  const map = {};
  items.filter(passeFiltreStatut).forEach(it => {
    if (!map[it.dlc]) map[it.dlc] = [];
    map[it.dlc].push(it);
  });
  return map;
}

function compteursJour(items) {
  const c = { rouge: 0, orange: 0, jaune: 0, vert: 0, gris: 0 };
  const aujourdhui = new Date(); aujourdhui.setHours(0,0,0,0);
  items.forEach(it => {
    if (it.devenir_statut) { c.gris++; return; }
    c[niveauAlerte(it.dlc)]++;
  });
  return c;
}

function badgesHtml(items) {
  const c = compteursJour(items);
  const aujourdhui = new Date(); aujourdhui.setHours(0,0,0,0);
  const aDepassees = items.some(it => !it.devenir_statut && parseYmd(it.dlc) < aujourdhui);
  return ['rouge','orange','jaune','vert','gris'].filter(n => c[n] > 0).map(n => {
    const ext = (n === 'rouge' && aDepassees) ? ' clignotant' : '';
    return `<span class="dlc-badge dlc-badge--${n}${ext}">${c[n]}</span>`;
  }).join('');
}

// ── Mise à jour du label de navigation ──────────────────
function updateLabel() {
  const ref = state.dateRef;
  let txt = '';
  switch (state.vue) {
    case 'semaine': {
      const lundi = lundiDeLaSemaine(ref);
      const dim = new Date(lundi); dim.setDate(dim.getDate() + 6);
      txt = `${lundi.toLocaleDateString('fr-FR',{day:'2-digit',month:'short'})} – ${dim.toLocaleDateString('fr-FR',{day:'2-digit',month:'short',year:'numeric'})}`;
      break;
    }
    case 'annuel':
      txt = String(ref.getFullYear());
      break;
    default:
      txt = ref.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
  }
  $('dlc-mois-label').textContent = txt;
}

// ── Dispatch vue ─────────────────────────────────────────
function renderVue(debut, fin) {
  updateLabel();
  switch (state.vue) {
    case 'semaine': renderSemaine(debut, fin); break;
    case 'annuel':  renderAnnuel();            break;
    default:        renderMois(debut, fin);    break;
  }
}

// ══════════════════════════════════════════════════════════
// VUE SEMAINE — 7 colonnes avec noms produits visibles
// ══════════════════════════════════════════════════════════
function renderSemaine(debut, fin) {
  const parDate = indexParDate(state.items);
  const aujourdhui = new Date(); aujourdhui.setHours(0,0,0,0);
  const container = $('dlc-vue-container');

  const jours = [];
  const cur = new Date(debut);
  while (cur <= fin) { jours.push(ymd(cur)); cur.setDate(cur.getDate() + 1); }

  const JOURS_NOM = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'];

  let html = `<div class="dlc-semaine-grille">`;
  jours.forEach((key, i) => {
    const items = parDate[key] || [];
    const estAuj = key === ymd(aujourdhui);
    const cls = ['dlc-semaine-col', estAuj ? 'dlc-semaine-col--auj' : ''].join(' ').trim();

    let produitsHtml = '';
    if (items.length === 0) {
      produitsHtml = `<div class="dlc-semaine-vide">—</div>`;
    } else {
      items.forEach(it => {
        const niveau = it.devenir_statut ? 'gris' : niveauAlerte(it.dlc);
        const src = it.source_type === 'fabrication' ? '🔪' : '📦';
        produitsHtml += `
          <div class="dlc-semaine-item dlc-semaine-item--${niveau}"
               data-date="${key}" data-index="${items.indexOf(it)}">
            <span class="dlc-semaine-item-src">${src}</span>
            <span class="dlc-semaine-item-nom">${escHtml(it.produit_nom)}</span>
          </div>`;
      });
    }

    html += `
      <div class="${cls}" data-date="${key}">
        <div class="dlc-semaine-entete">
          <span class="dlc-semaine-dow">${JOURS_NOM[i]}</span>
          <span class="dlc-semaine-num">${parseYmd(key).getDate()}</span>
        </div>
        <div class="dlc-semaine-produits">${produitsHtml}</div>
      </div>`;
  });
  html += `</div>`;

  container.innerHTML = html;

  // Ouvrir modal au clic sur une colonne ou un item
  container.querySelectorAll('.dlc-semaine-col[data-date]').forEach(col => {
    const key = col.dataset.date;
    const items = parDate[key] || [];
    if (items.length > 0) {
      col.style.cursor = 'pointer';
      col.addEventListener('click', () => ouvrirModalJour(key, items));
    }
  });
}

// ══════════════════════════════════════════════════════════
// VUE MOIS
// ══════════════════════════════════════════════════════════
function renderMois(debut, fin) {
  const parDate = indexParDate(state.items);
  const aujourdhui = new Date(); aujourdhui.setHours(0,0,0,0);
  const moisCible = state.dateRef.getMonth();

  let html = `<div class="dlc-calendrier">
    <div class="dlc-jour-entete">Lun</div><div class="dlc-jour-entete">Mar</div>
    <div class="dlc-jour-entete">Mer</div><div class="dlc-jour-entete">Jeu</div>
    <div class="dlc-jour-entete">Ven</div><div class="dlc-jour-entete">Sam</div>
    <div class="dlc-jour-entete">Dim</div>
    <div class="dlc-grille-body" id="dlc-grille-body"></div>
  </div>`;

  const container = $('dlc-vue-container');
  container.innerHTML = html;

  const body = container.querySelector('#dlc-grille-body');
  const cur = new Date(debut);
  while (cur <= fin) {
    const key = ymd(cur);
    const items = parDate[key] || [];
    const autreMois = cur.getMonth() !== moisCible;
    const estAuj = key === ymd(aujourdhui);

    const el = document.createElement('div');
    el.className = ['dlc-jour', autreMois ? 'dlc-jour--autre-mois' : '', estAuj ? 'dlc-jour--aujourdhui' : ''].filter(Boolean).join(' ');
    el.dataset.date = key;
    el.innerHTML = `
      <div class="dlc-jour-num">${cur.getDate()}</div>
      <div class="dlc-jour-badges">${badgesHtml(items)}</div>
    `;
    if (items.length > 0) {
      el.addEventListener('click', () => ouvrirModalJour(key, items));
    } else {
      el.classList.add('dlc-jour--vide');
    }
    body.appendChild(el);
    cur.setDate(cur.getDate() + 1);
  }
}

// ══════════════════════════════════════════════════════════
// VUE ANNUELLE — grille 3×4 de mini-mois
// ══════════════════════════════════════════════════════════
function renderAnnuel() {
  const parDate = indexParDate(state.items);
  const annee = state.dateRef.getFullYear();
  const aujourdhui = new Date(); aujourdhui.setHours(0,0,0,0);
  const moisNoms = ['Janv','Févr','Mars','Avr','Mai','Juin','Juil','Août','Sept','Oct','Nov','Déc'];

  let html = `<div class="dlc-annuel-grille">`;

  for (let m = 0; m < 12; m++) {
    const premier = new Date(annee, m, 1);
    const dernier = new Date(annee, m + 1, 0);
    const lundi0 = new Date(premier);
    lundi0.setDate(lundi0.getDate() - ((premier.getDay() + 6) % 7));

    // Compteurs mois
    let rougeM = 0, orangeM = 0, jauneM = 0, vertM = 0, grisM = 0, atTraiter = 0;
    const cur = new Date(lundi0);
    const dateItems = [];
    while (cur <= dernier || cur.getMonth() === m) {
      if (cur.getMonth() === m) {
        const key = ymd(cur);
        (parDate[key] || []).forEach(it => {
          dateItems.push({ key, it });
          if (it.devenir_statut) { grisM++; return; }
          const n = niveauAlerte(it.dlc);
          if (n === 'rouge')  { rougeM++;  if (parseYmd(it.dlc) < aujourdhui) atTraiter++; }
          if (n === 'orange') orangeM++;
          if (n === 'jaune')  jauneM++;
          if (n === 'vert')   vertM++;
        });
      }
      cur.setDate(cur.getDate() + 1);
      if (cur > dernier && cur.getMonth() !== m) break;
    }

    const total = rougeM + orangeM + jauneM + vertM + grisM;
    const estMoisCourant = (new Date().getMonth() === m && new Date().getFullYear() === annee);

    let dotsHtml = '';
    if (rougeM)  dotsHtml += `<span class="dlc-annuel-dot dlc-annuel-dot--rouge${atTraiter ? ' clignotant' : ''}">${rougeM}</span>`;
    if (orangeM) dotsHtml += `<span class="dlc-annuel-dot dlc-annuel-dot--orange">${orangeM}</span>`;
    if (jauneM)  dotsHtml += `<span class="dlc-annuel-dot dlc-annuel-dot--jaune">${jauneM}</span>`;
    if (vertM)   dotsHtml += `<span class="dlc-annuel-dot dlc-annuel-dot--vert">${vertM}</span>`;
    if (grisM)   dotsHtml += `<span class="dlc-annuel-dot dlc-annuel-dot--gris">${grisM}</span>`;

    html += `
      <div class="dlc-annuel-mois${estMoisCourant ? ' dlc-annuel-mois--courant' : ''}"
           data-mois="${m}" ${total > 0 ? 'role="button" tabindex="0"' : ''}>
        <div class="dlc-annuel-mois-nom">${moisNoms[m]}</div>
        ${total > 0
          ? `<div class="dlc-annuel-dots">${dotsHtml}</div>
             <div class="dlc-annuel-total">${total} produit${total > 1 ? 's' : ''}</div>`
          : `<div class="dlc-annuel-vide">—</div>`}
      </div>`;
  }
  html += `</div>`;

  const container = $('dlc-vue-container');
  container.innerHTML = html;

  // Clic sur un mois → passer en vue mois
  container.querySelectorAll('.dlc-annuel-mois[data-mois]').forEach(el => {
    const m = parseInt(el.dataset.mois, 10);
    const total = el.querySelector('.dlc-annuel-total');
    if (!total) return;
    el.style.cursor = 'pointer';
    el.addEventListener('click', () => {
      state.vue = 'mois';
      state.dateRef = new Date(state.dateRef.getFullYear(), m, 1);
      setVueBouton('mois');
      chargerCalendrier();
    });
  });
}

// ── Modal liste du jour ─────────────────────────────────
function ouvrirModalJour(dateStr, items) {
  const aujourdhui = new Date(); aujourdhui.setHours(0,0,0,0);

  $('dlc-modal-titre').textContent = `DLC du ${formatDateFr(dateStr)}`;
  const body = $('dlc-modal-body');
  body.innerHTML = '';

  items.forEach(it => {
    const niveau = it.devenir_statut ? 'gris' : niveauAlerte(it.dlc);
    const expire = parseYmd(it.dlc) < aujourdhui;
    const aTraiter = expire && !it.devenir_statut;
    const sourceLabel = it.source_type === 'fabrication' ? '🔪 Fabrication' : '📦 Réception';
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

    // Bouton : "Actualiser" si déjà traité, "Indiquer devenir" si expiré non traité
    const btnLabel = it.devenir_statut ? '✏️ Actualiser' : '📝 Indiquer devenir';
    const btnHtml = (aTraiter || it.devenir_statut)
      ? `<button class="dlc-item-btn-devenir ${it.devenir_statut ? 'dlc-item-btn-devenir--update' : ''}"
                 data-src-type="${escHtml(it.source_type)}"
                 data-src-id="${it.source_id}"
                 data-nom="${escHtml(it.produit_nom)}"
                 data-dlc="${escHtml(it.dlc)}">
           ${btnLabel}
         </button>`
      : '';

    const el = document.createElement('div');
    el.className = `dlc-item dlc-item--${niveau}`;
    el.innerHTML = `
      <div class="dlc-item-titre">${escHtml(it.produit_nom)}</div>
      <div class="dlc-item-meta">
        <span class="dlc-item-source dlc-item-source--${sourceCls}">${sourceLabel}</span>
        ${meta.map(m => `<span>${escHtml(m)}</span>`).join('')}
      </div>
      ${devenirHtml}
      ${btnHtml}
    `;
    body.appendChild(el);
  });

  body.querySelectorAll('.dlc-item-btn-devenir').forEach(btn => {
    btn.addEventListener('click', () => ouvrirModalDevenir({
      source_type: btn.dataset.srcType,
      source_id:   parseInt(btn.dataset.srcId, 10),
      produit_nom: btn.dataset.nom,
      dlc:         btn.dataset.dlc,
    }));
  });

  $('dlc-modal').hidden = false;
}

function statutLabel(s) {
  return { jete: 'Jeté', vendu: 'Vendu', consomme: 'Consommé', autre: 'Autre' }[s] || s;
}

function fermerModal() { $('dlc-modal').hidden = true; }
document.querySelectorAll('#dlc-modal [data-close]').forEach(e => e.addEventListener('click', fermerModal));

// ── Modal Devenir ───────────────────────────────────────
function ouvrirModalDevenir(cible) {
  state.devenirCible  = cible;
  state.devenirStatut = null;

  $('devenir-produit-nom').textContent  = cible.produit_nom;
  $('devenir-produit-info').textContent = `DLC : ${formatDateFr(cible.dlc)}`;
  $('devenir-commentaire').value = '';

  const sel = $('devenir-personnel');
  sel.innerHTML = '<option value="">— Sélectionner —</option>';
  state.personnel.forEach(p => {
    const label = [p.prenom, p.nom].filter(Boolean).join(' ');
    sel.innerHTML += `<option value="${p.id}">${escHtml(label)}</option>`;
  });
  sel.value = '';

  document.querySelectorAll('.btn-statut').forEach(b => b.classList.remove('actif'));
  $('devenir-valider').disabled = true;
  $('devenir-modal').hidden = false;
}

function fermerModalDevenir() {
  $('devenir-modal').hidden = true;
  state.devenirCible  = null;
  state.devenirStatut = null;
}
document.querySelectorAll('#devenir-modal [data-close-devenir]').forEach(e => e.addEventListener('click', fermerModalDevenir));

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
  $('devenir-valider').disabled = !(state.devenirStatut && $('devenir-personnel').value);
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
    btn.textContent = 'Confirmer';
    rafraichirBoutonValider();
  }
});

// ── Sélecteur de vue ─────────────────────────────────────
function setVueBouton(vue) {
  document.querySelectorAll('.dlc-btn-vue').forEach(b => {
    b.classList.toggle('actif', b.dataset.vue === vue);
  });
}

document.querySelectorAll('.dlc-btn-vue').forEach(btn => {
  btn.addEventListener('click', () => {
    if (state.vue === btn.dataset.vue) return;
    state.vue = btn.dataset.vue;
    // Recaler dateRef selon la vue
    const now = new Date();
    if (state.vue === 'semaine') state.dateRef = lundiDeLaSemaine(state.dateRef);
    if (state.vue === 'mois')    state.dateRef = new Date(state.dateRef.getFullYear(), state.dateRef.getMonth(), 1);
    if (state.vue === 'annuel')  state.dateRef = new Date(state.dateRef.getFullYear(), 0, 1);
    setVueBouton(state.vue);
    chargerCalendrier();
  });
});

// ── Navigation ──────────────────────────────────────────
$('dlc-prev').addEventListener('click', () => {
  const d = state.dateRef;
  if (state.vue === 'semaine') d.setDate(d.getDate() - 7);
  if (state.vue === 'mois')    state.dateRef = new Date(d.getFullYear(), d.getMonth() - 1, 1);
  if (state.vue === 'annuel')  state.dateRef = new Date(d.getFullYear() - 1, 0, 1);
  chargerCalendrier();
});
$('dlc-next').addEventListener('click', () => {
  const d = state.dateRef;
  if (state.vue === 'semaine') d.setDate(d.getDate() + 7);
  if (state.vue === 'mois')    state.dateRef = new Date(d.getFullYear(), d.getMonth() + 1, 1);
  if (state.vue === 'annuel')  state.dateRef = new Date(d.getFullYear() + 1, 0, 1);
  chargerCalendrier();
});
$('dlc-aujourdhui').addEventListener('click', () => {
  const now = new Date();
  state.dateRef = state.vue === 'semaine' ? lundiDeLaSemaine(now)
               : state.vue === 'annuel'  ? new Date(now.getFullYear(), 0, 1)
               :                           new Date(now.getFullYear(), now.getMonth(), 1);
  chargerCalendrier();
});

$('dlc-filtre-source').addEventListener('change', e => { state.filtres.source = e.target.value; chargerCalendrier(); });
$('dlc-filtre-statut').addEventListener('change', e => { state.filtres.statut = e.target.value; chargerCalendrier(); });

// ── Init ────────────────────────────────────────────────
(async () => {
  const now = new Date();
  state.dateRef = new Date(now.getFullYear(), now.getMonth(), 1);
  await chargerPersonnel();
  await chargerCalendrier();
})();

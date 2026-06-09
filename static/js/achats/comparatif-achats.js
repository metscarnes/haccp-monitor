// comparatif-achats.js — Comparateur fournisseurs
//
// Construction de « groupes de comparaison » (paniers d'articles catalogue de
// fournisseurs différents désignant le même produit) et affichage d'un VS au
// prix au kilo normalisé pour arbitrer le meilleur achat. Le €/kg vient du
// backend ; quand il est null, on affiche « indisponible » plutôt qu'un faux chiffre.

const API_CMP = '/api/achats/comparatif';
const API_CAT = '/api/achats/catalogue';

let groupeCourant = null;   // id du groupe affiché
let dernierVS     = null;   // données du VS courant (pour les suggestions)

// ── Utilitaires ───────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

function fmtEuro(v) {
  if (v == null) return '—';
  return v.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
}
function fmtPrixKg(v) {
  if (v == null) return null;
  return v.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €/kg';
}
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"]/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

// ── Chargement des groupes ────────────────────────────────────
async function chargerGroupes(selectionner) {
  const r = await fetch(`${API_CMP}/groupes`);
  if (!r.ok) { console.error('Erreur chargement groupes'); return; }
  const groupes = await r.json();
  const sel = $('select-groupe');
  sel.innerHTML = '<option value="">— Choisir un groupe —</option>' +
    groupes.map((g) =>
      `<option value="${g.id}">${esc(g.nom)} (${g.nb_lignes})</option>`).join('');
  if (selectionner) sel.value = String(selectionner);
  majBoutonsGroupe();
}

function majBoutonsGroupe() {
  const actif = !!$('select-groupe').value;
  $('btn-renommer').style.display        = actif ? '' : 'none';
  $('btn-supprimer-groupe').style.display = actif ? '' : 'none';
  $('btn-ajouter-ligne').style.display    = actif ? '' : 'none';
}

// ── Affichage du VS ───────────────────────────────────────────
async function afficherVS(groupeId) {
  groupeCourant = groupeId;
  if (!groupeId) {
    dernierVS = null;
    $('cmp-vs').innerHTML = '<div class="cmp-empty" id="cmp-empty">Sélectionnez un groupe, ou créez-en un pour commencer la comparaison.</div>';
    return;
  }
  const r = await fetch(`${API_CMP}/groupes/${groupeId}`);
  if (!r.ok) { $('cmp-vs').innerHTML = '<div class="cmp-empty">Erreur de chargement.</div>'; return; }
  dernierVS = await r.json();
  rendreVS(dernierVS);
}

function rendreVS(data) {
  const lignes = data.lignes || [];
  if (!lignes.length) {
    $('cmp-vs').innerHTML =
      `<div class="cmp-empty">Ce groupe est vide. Cliquez sur « + Ajouter un article » pour comparer des produits.</div>`;
    return;
  }

  // Critères en lignes, fournisseurs en colonnes.
  const criteres = [
    ['Code article', (l) => esc(l.code_article) || '—'],
    ['Désignation', (l) => esc(l.designation)],
    ['Format prix', (l) => l.format_prix === 'kg' ? '€/kg' : '€/colis'],
    ['Prix d\'achat', (l) => fmtEuro(l.prix_achat_ht)],
    ['Poids colis', (l) => l.poids_colis_kg != null ? l.poids_colis_kg.toFixed(3) + ' kg' : '—'],
  ];

  let html = '<div class="cmp-grid" style="grid-template-columns: 160px repeat(' + lignes.length + ', minmax(180px, 1fr));">';

  // En-têtes fournisseurs
  html += '<div class="cmp-cell cmp-cell--head cmp-cell--label"></div>';
  lignes.forEach((l) => {
    html += `<div class="cmp-cell cmp-cell--head${l.meilleur ? ' cmp-best' : ''}">
      <div class="cmp-fourn">${esc(l.fournisseur_nom)}</div>
      <button class="cmp-remove" data-cat="${l.id}" title="Retirer du groupe">✕</button>
    </div>`;
  });

  // Lignes de critères
  criteres.forEach(([label, fn]) => {
    html += `<div class="cmp-cell cmp-cell--label">${label}</div>`;
    lignes.forEach((l) => {
      html += `<div class="cmp-cell${l.meilleur ? ' cmp-best' : ''}">${fn(l)}</div>`;
    });
  });

  // Ligne clé : prix au kilo normalisé
  html += '<div class="cmp-cell cmp-cell--label cmp-cell--key">➤ Prix au kilo</div>';
  lignes.forEach((l) => {
    const pk = fmtPrixKg(l.prix_kg);
    if (pk == null) {
      html += `<div class="cmp-cell cmp-cell--key"><span class="cmp-indispo">€/kg indisponible</span></div>`;
    } else {
      html += `<div class="cmp-cell cmp-cell--key${l.meilleur ? ' cmp-best' : ''}">
        <strong>${pk}</strong>${l.meilleur ? ' <span class="cmp-tag">✅ meilleur</span>' : ''}</div>`;
    }
  });

  html += '</div>';

  // Note honnêteté quand des prix manquent
  const indispo = lignes.filter((l) => l.prix_kg == null).length;
  if (indispo) {
    html += `<div class="cmp-note">⚠ ${indispo} article(s) sans prix au kilo : poids du colis non renseigné par le fournisseur. Complétez le poids dans le catalogue achats pour les inclure dans la comparaison.</div>`;
  }

  $('cmp-vs').innerHTML = html;

  // Boutons « retirer »
  $('cmp-vs').querySelectorAll('.cmp-remove').forEach((b) => {
    b.addEventListener('click', () => retirerLigne(b.dataset.cat));
  });
}

// ── Mutations groupe ──────────────────────────────────────────
async function creerGroupe() {
  const nom = prompt('Nom du groupe de comparaison (ex. « Filet de bœuf ») :');
  if (!nom || !nom.trim()) return;
  const r = await fetch(`${API_CMP}/groupes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nom: nom.trim() }),
  });
  if (!r.ok) { alert('Création impossible.'); return; }
  const g = await r.json();
  await chargerGroupes(g.id);
  afficherVS(g.id);
}

async function renommerGroupe() {
  if (!groupeCourant) return;
  const actuel = $('select-groupe').selectedOptions[0]?.text.replace(/\s*\(\d+\)\s*$/, '') || '';
  const nom = prompt('Nouveau nom du groupe :', actuel);
  if (!nom || !nom.trim()) return;
  const r = await fetch(`${API_CMP}/groupes/${groupeCourant}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nom: nom.trim() }),
  });
  if (!r.ok) { alert('Renommage impossible.'); return; }
  await chargerGroupes(groupeCourant);
}

async function supprimerGroupe() {
  if (!groupeCourant) return;
  if (!confirm('Supprimer ce groupe de comparaison ? (les articles du catalogue ne sont pas touchés)')) return;
  const r = await fetch(`${API_CMP}/groupes/${groupeCourant}`, { method: 'DELETE' });
  if (!r.ok) { alert('Suppression impossible.'); return; }
  groupeCourant = null;
  await chargerGroupes();
  afficherVS(null);
}

async function retirerLigne(catId) {
  if (!groupeCourant) return;
  const r = await fetch(`${API_CMP}/groupes/${groupeCourant}/lignes/${catId}`, { method: 'DELETE' });
  if (!r.ok) { alert('Retrait impossible.'); return; }
  await afficherVS(groupeCourant);
  await chargerGroupes(groupeCourant);
}

async function ajouterLigne(catId) {
  if (!groupeCourant) return;
  const r = await fetch(`${API_CMP}/groupes/${groupeCourant}/lignes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ catalogue_fournisseur_id: Number(catId) }),
  });
  if (!r.ok) { alert('Ajout impossible.'); return; }
  await afficherVS(groupeCourant);
  await chargerGroupes(groupeCourant);
  rafraichirPanneau();
}

// ── Panneau d'ajout : suggestions + recherche ─────────────────
function ouvrirPanneau() {
  if (!groupeCourant) return;
  $('cmp-panneau').style.display = '';
  $('cmp-search').value = '';
  rafraichirPanneau();
  $('cmp-search').focus();
}
function fermerPanneau() {
  $('cmp-panneau').style.display = 'none';
}

async function rafraichirPanneau() {
  const q = $('cmp-search').value.trim();
  if (q) {
    await afficherRecherche(q);
  } else {
    await afficherSuggestions();
  }
}

// Suggestions : basées sur le 1er article du groupe (référence sémantique).
async function afficherSuggestions() {
  const lignes = dernierVS?.lignes || [];
  const titre = $('cmp-suggestions-titre');
  if (!lignes.length) {
    titre.style.display = 'none';
    $('cmp-resultats').innerHTML =
      '<div class="cmp-empty cmp-empty--sm">Recherchez un premier article ci-dessus pour démarrer le groupe.</div>';
    return;
  }
  const refId = lignes[0].id;
  const r = await fetch(`${API_CMP}/suggestions?ligne_id=${refId}&groupe_id=${groupeCourant}`);
  const sugg = r.ok ? await r.json() : [];
  titre.style.display = sugg.length ? '' : 'none';
  if (!sugg.length) {
    $('cmp-resultats').innerHTML =
      '<div class="cmp-empty cmp-empty--sm">Aucune suggestion. Utilisez la recherche pour ajouter un article.</div>';
    return;
  }
  rendreResultats(sugg, true);
}

// Recherche libre dans le catalogue.
async function afficherRecherche(q) {
  $('cmp-suggestions-titre').style.display = 'none';
  const r = await fetch(`${API_CAT}?q=${encodeURIComponent(q)}`);
  let articles = r.ok ? await r.json() : [];
  // Exclure ceux déjà dans le groupe.
  const dans = new Set((dernierVS?.lignes || []).map((l) => l.id));
  articles = articles.filter((a) => !dans.has(a.id)).slice(0, 30);
  if (!articles.length) {
    $('cmp-resultats').innerHTML = '<div class="cmp-empty cmp-empty--sm">Aucun article trouvé.</div>';
    return;
  }
  rendreResultats(articles, false);
}

function rendreResultats(items, avecScore) {
  $('cmp-resultats').innerHTML = items.map((a) => {
    const pk = a.prix_kg != null
      ? fmtPrixKg(a.prix_kg)
      : '<span class="cmp-indispo">€/kg indisponible</span>';
    const score = (avecScore && a.score != null)
      ? `<span class="cmp-score">${Math.round(a.score * 100)}%</span>` : '';
    return `<div class="cmp-resultat">
      <div class="cmp-resultat-info">
        <div class="cmp-resultat-nom">${esc(a.designation)} ${score}</div>
        <div class="cmp-resultat-meta">${esc(a.fournisseur_nom)} · ${esc(a.code_article)} · ${pk}</div>
      </div>
      <button class="ach-btn ach-btn--primary cmp-add" data-cat="${a.id}">+ Ajouter</button>
    </div>`;
  }).join('');
  $('cmp-resultats').querySelectorAll('.cmp-add').forEach((b) => {
    b.addEventListener('click', () => ajouterLigne(b.dataset.cat));
  });
}

// ── « Proposer des groupes » : grappes candidates à valider ───
let grappesProposees = [];   // état local des grappes (avec articles décochables)

async function ouvrirProposer() {
  $('cmp-proposer').style.display = '';
  $('cmp-grappes').innerHTML = '<div class="cmp-empty cmp-empty--sm">Analyse du catalogue…</div>';
  $('cmp-proposer-info').textContent = '';
  const r = await fetch(`${API_CMP}/proposer`);
  if (!r.ok) { $('cmp-grappes').innerHTML = '<div class="cmp-empty cmp-empty--sm">Erreur d\'analyse.</div>'; return; }
  const d = await r.json();
  // Chaque grappe : nom éditable + articles avec une case "inclure" (cochée par défaut).
  grappesProposees = d.grappes.map((g, i) => ({
    idx: i,
    nom: g.nom_suggere,
    fiable: g.fiable,
    sous_famille: g.sous_famille,
    lignes: g.lignes.map((l) => ({ ...l, inclus: true })),
  }));
  $('cmp-proposer-info').innerHTML = grappesProposees.length
    ? `${grappesProposees.length} groupe(s) proposé(s). Décochez les intrus, ajustez le nom, puis validez. <span class="cmp-mono">${d.mono_fournisseur} produit(s) mono-fournisseur (rien à comparer).</span>`
    : `Aucun groupe à proposer pour l'instant. <span class="cmp-mono">${d.mono_fournisseur} produit(s) mono-fournisseur.</span>`;
  rendreGrappes();
}
function fermerProposer() { $('cmp-proposer').style.display = 'none'; }

function rendreGrappes() {
  if (!grappesProposees.length) {
    $('cmp-grappes').innerHTML = '<div class="cmp-empty cmp-empty--sm">Rien à proposer.</div>';
    return;
  }
  $('cmp-grappes').innerHTML = grappesProposees.map((g) => {
    if (g.lignes === null) return '';   // grappe déjà créée ou ignorée
    const arts = g.lignes.map((l) => {
      const pk = l.prix_kg != null ? fmtPrixKg(l.prix_kg) : '<span class="cmp-indispo">€/kg indispo</span>';
      return `<label class="cmp-grappe-art">
        <input type="checkbox" data-g="${g.idx}" data-l="${l.id}" ${l.inclus ? 'checked' : ''}>
        <span class="cmp-grappe-art-nom">${esc(l.designation)}</span>
        <span class="cmp-grappe-art-meta">${esc(l.fournisseur_nom)} · ${pk}</span>
      </label>`;
    }).join('');
    const badge = g.fiable ? '' : '<span class="cmp-badge-fiable">moins fiable</span>';
    return `<div class="cmp-grappe" data-g="${g.idx}">
      <div class="cmp-grappe-head">
        <input type="text" class="cmp-grappe-nom" data-g="${g.idx}" value="${esc(g.nom)}">
        ${badge}
        <span class="cmp-grappe-sf">${esc(g.sous_famille) || 'sans sous-famille'}</span>
      </div>
      <div class="cmp-grappe-arts">${arts}</div>
      <div class="cmp-grappe-actions">
        <button class="ach-btn ach-btn--primary cmp-grappe-creer" data-g="${g.idx}">✓ Créer le groupe</button>
        <button class="ach-btn cmp-grappe-ignorer" data-g="${g.idx}">Ignorer</button>
      </div>
    </div>`;
  }).join('');

  // Câblage
  $('cmp-grappes').querySelectorAll('.cmp-grappe-nom').forEach((inp) => {
    inp.addEventListener('input', () => { grappesProposees[+inp.dataset.g].nom = inp.value; });
  });
  $('cmp-grappes').querySelectorAll('.cmp-grappe-art input').forEach((cb) => {
    cb.addEventListener('change', () => {
      const g = grappesProposees[+cb.dataset.g];
      const l = g.lignes.find((x) => x.id === +cb.dataset.l);
      if (l) l.inclus = cb.checked;
    });
  });
  $('cmp-grappes').querySelectorAll('.cmp-grappe-creer').forEach((b) => {
    b.addEventListener('click', () => creerDepuisGrappe(+b.dataset.g));
  });
  $('cmp-grappes').querySelectorAll('.cmp-grappe-ignorer').forEach((b) => {
    b.addEventListener('click', () => { grappesProposees[+b.dataset.g].lignes = null; rendreGrappes(); });
  });
}

async function creerDepuisGrappe(idx) {
  const g = grappesProposees[idx];
  if (!g || g.lignes === null) return;
  const ids = g.lignes.filter((l) => l.inclus).map((l) => l.id);
  if (ids.length < 2) { alert('Sélectionnez au moins 2 articles à comparer.'); return; }
  if (!g.nom.trim()) { alert('Donnez un nom au groupe.'); return; }
  const r = await fetch(`${API_CMP}/groupes/from-cluster`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nom: g.nom.trim(), catalogue_fournisseur_ids: ids }),
  });
  if (!r.ok) { alert('Création impossible.'); return; }
  const groupe = await r.json();
  g.lignes = null;                 // retirer la grappe traitée de la liste
  rendreGrappes();
  await chargerGroupes(groupe.id); // rafraîchir le sélecteur principal
  afficherVS(groupe.id);
}

// ── Badge "articles non groupés" ─────────────────────────────
async function majBadgeNonGroupes() {
  try {
    const r = await fetch(`${API_CMP}/stats`);
    if (!r.ok) return;
    const d = await r.json();
    const n = d.articles_non_groupes ?? 0;
    const badge = $('badge-non-groupes');
    const texte = $('badge-non-groupes-texte');
    if (n > 0) {
      texte.textContent = `${n} article(s) du catalogue non encore comparés`;
      badge.style.display = '';
    } else {
      badge.style.display = 'none';
    }
  } catch { /* silencieux */ }
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  chargerGroupes();
  majBadgeNonGroupes();

  $('select-groupe').addEventListener('change', (e) => {
    majBoutonsGroupe();
    afficherVS(e.target.value ? Number(e.target.value) : null);
    fermerPanneau();
  });
  $('btn-nouveau-groupe').addEventListener('click', creerGroupe);
  $('btn-proposer').addEventListener('click', ouvrirProposer);
  $('btn-fermer-proposer').addEventListener('click', fermerProposer);
  $('btn-renommer').addEventListener('click', renommerGroupe);
  $('btn-supprimer-groupe').addEventListener('click', supprimerGroupe);
  $('btn-ajouter-ligne').addEventListener('click', ouvrirPanneau);
  $('btn-fermer-panneau').addEventListener('click', fermerPanneau);

  let t;
  $('cmp-search').addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(rafraichirPanneau, 250);
  });
});

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
// Nombre monétaire sans unité (l'unité — €/kg ou €/pièce — est ajoutée par l'appelant).
function fmtNb(v) {
  if (v == null) return '—';
  return v.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
  const sel = $('select-groupe');
  const actif = !!sel.value;
  $('btn-renommer').style.display        = actif ? '' : 'none';
  $('btn-supprimer-groupe').style.display = actif ? '' : 'none';
  $('btn-ajouter-ligne').style.display    = actif ? '' : 'none';
  // « Suivant » visible dès qu'il existe au moins 2 groupes (pour enchaîner).
  const nbGroupes = [...sel.options].filter((o) => o.value).length;
  $('btn-groupe-suivant').style.display = nbGroupes > 1 ? '' : 'none';
}

// Passe au groupe suivant dans le sélecteur (boucle au début après le dernier).
function groupeSuivant() {
  const sel = $('select-groupe');
  const valeurs = [...sel.options].map((o) => o.value).filter((v) => v);
  if (valeurs.length < 2) return;
  const i = valeurs.indexOf(sel.value);
  const prochain = valeurs[(i + 1) % valeurs.length];   // i = -1 (aucun) → premier
  sel.value = prochain;
  sel.dispatchEvent(new Event('change'));
}

// ── Affichage du VS ───────────────────────────────────────────
async function afficherVS(groupeId) {
  groupeCourant = groupeId;
  if (!groupeId) {
    dernierVS = null;
    $('cmp-marge').style.display = 'none';
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
    $('cmp-marge').style.display = 'none';
    $('cmp-vs').innerHTML =
      `<div class="cmp-empty">Ce groupe est vide. Cliquez sur « + Ajouter un article » pour comparer des produits.</div>`;
    return;
  }

  const produits = data.produits_vente || [];

  // Le tableau VS « global » en haut ne s'affiche QUE s'il n'y a aucun produit de vente associé
  // (sinon la comparaison vit dans chaque carte dépliée → on évite le doublon).
  if (produits.length) {
    $('cmp-vs').innerHTML = '';
  } else {
    let html = construireGrilleVS(lignes, { retirer: true });
    const indispo = lignes.filter((l) => l.prix_kg == null).length;
    if (indispo) {
      html += `<div class="cmp-note">⚠ ${indispo} article(s) sans prix au kilo : poids du colis non renseigné par le fournisseur. Complétez le poids dans le catalogue achats pour les inclure dans la comparaison.</div>`;
    }
    $('cmp-vs').innerHTML = html;
    $('cmp-vs').querySelectorAll('.cmp-remove').forEach((b) => {
      b.addEventListener('click', () => retirerLigne(b.dataset.cat));
    });
  }

  // Bande marge (cartes produits de vente + comparatif intégré).
  rendreMarge(data);
}

// Construit la grille comparative (fournisseurs en colonnes). Réutilisée pour le VS global
// ET, en mode cliquable, à l'intérieur d'une carte produit pour choisir sa référence.
//   opts.retirer    → bouton ✕ « retirer du groupe » dans l'en-tête.
//   opts.choisirCv  → id du produit de vente : rend les colonnes cliquables (choix de référence).
//   opts.refId      → id de la ligne actuellement choisie (colonne mise en évidence).
function construireGrilleVS(lignes, opts = {}) {
  const { retirer = false, choisirCv = null, refId = null } = opts;
  const cliquable = choisirCv != null;

  const criteres = [
    ['Code article', (l) => esc(l.code_article) || '—'],
    ['Désignation', (l) => esc(l.designation)],
    ['Format prix', (l) => l.format_prix === 'kg' ? '€/kg' : '€/colis'],
    ['Prix d\'achat', (l) => fmtEuro(l.prix_achat_ht)],
    ['Poids colis', (l) => l.poids_colis_kg != null ? l.poids_colis_kg.toFixed(3) + ' kg' : '—'],
  ];

  const colClass = (l) =>
    (l.meilleur ? ' cmp-best' : '') + (cliquable && l.id === refId ? ' cmp-ref' : '');

  let html = '<div class="cmp-grid' + (cliquable ? ' cmp-grid--choix' : '') +
    '" style="grid-template-columns: 160px repeat(' + lignes.length + ', minmax(180px, 1fr));">';

  // En-têtes fournisseurs (cliquables si choix de référence).
  html += '<div class="cmp-cell cmp-cell--head cmp-cell--label"></div>';
  lignes.forEach((l) => {
    const attrs = cliquable
      ? ` data-choix-cv="${choisirCv}" data-choix-ligne="${l.id}" role="button" title="Choisir cet achat comme référence"`
      : '';
    const btn = retirer
      ? `<button class="cmp-remove" data-cat="${l.id}" title="Retirer du groupe">✕</button>`
      : (cliquable && l.id === refId ? '<span class="cmp-ref-check">✓ réf</span>' : '');
    html += `<div class="cmp-cell cmp-cell--head${colClass(l)}"${attrs}>
      <div class="cmp-fourn">${esc(l.fournisseur_nom)}</div>
      ${btn}
    </div>`;
  });

  // Lignes de critères
  criteres.forEach(([label, fn]) => {
    html += `<div class="cmp-cell cmp-cell--label">${label}</div>`;
    lignes.forEach((l) => {
      const attrs = cliquable ? ` data-choix-cv="${choisirCv}" data-choix-ligne="${l.id}"` : '';
      html += `<div class="cmp-cell${colClass(l)}"${attrs}>${fn(l)}</div>`;
    });
  });

  // Ligne clé : prix au kilo normalisé
  html += '<div class="cmp-cell cmp-cell--label cmp-cell--key">➤ Prix au kilo</div>';
  lignes.forEach((l) => {
    const attrs = cliquable ? ` data-choix-cv="${choisirCv}" data-choix-ligne="${l.id}"` : '';
    const pk = fmtPrixKg(l.prix_kg);
    if (pk == null) {
      html += `<div class="cmp-cell cmp-cell--key${cliquable && l.id === refId ? ' cmp-ref' : ''}"${attrs}><span class="cmp-indispo">€/kg indisponible</span></div>`;
    } else {
      html += `<div class="cmp-cell cmp-cell--key${colClass(l)}"${attrs}>
        <strong>${pk}</strong>${l.meilleur ? ' <span class="cmp-tag">✅ meilleur</span>' : ''}</div>`;
    }
  });

  html += '</div>';
  return html;
}

// ── Bande marge : produits de vente associés (1 achat → N ventes) ─────
// Carte repliable : 1 ligne résumée par produit (marge + taux + fournisseur), l'édition
// (réf, prix, unité, poids) ne s'affiche que pour le produit déplié.
let margeOuvert = null;   // id du produit de vente actuellement déplié (un seul à la fois)

function rendreMarge(data) {
  const box = $('cmp-marge');
  const produits = data.produits_vente || [];
  const lignesAchat = data.lignes || [];

  // Sélecteur d'AJOUT : la liste ne s'ouvre que sur clic ▾ (ne masque pas le VS).
  let html = `<div class="cmp-marge-assoc">
    <label class="cmp-marge-lbl">🏷️ Produits de vente associés</label>
    <div class="cmp-marge-vente-pick">
      <input type="search" id="cmp-vente-search" class="cmp-vente-search"
             placeholder="Ajouter un produit de vente…" autocomplete="off">
      <button class="ach-btn cmp-vente-toggle" id="cmp-vente-toggle" title="Voir les produits">▾</button>
      <div id="cmp-vente-resultats" class="cmp-vente-resultats" style="display:none;"></div>
    </div>
  </div>`;

  if (produits.length) {
    html += '<div class="cmp-marge-liste">' +
      produits.map((p) => rendreMargeCarte(p, lignesAchat)).join('') + '</div>';
  } else {
    html += `<div class="cmp-marge-attente">Aucun produit de vente associé. Utilisez « Ajouter » pour relier ce groupe d'achat à un ou plusieurs produits vendus.</div>`;
  }

  box.innerHTML = html;
  box.style.display = '';
  cablerMarge();
}

// Carte d'un produit de vente : barre résumé (toujours visible) + zone d'édition (si déplié).
function rendreMargeCarte(p, lignesAchat) {
  const m = p.marge;
  const ouvert = margeOuvert === p.id;
  const estPiece = p.unite_vente === 'piece';
  const uniteLabel = estPiece ? '€/pièce' : '€/kg';
  const refId = p.ligne_choisie_id;
  const ligneRef = lignesAchat.find((l) => l.id === refId);

  // ── Barre résumé (toujours visible) ─────────────────────────
  // marge + taux à droite si calculée, sinon un libellé « à compléter ».
  let resume;
  if (m) {
    resume = `<span class="cmp-mc-marge">${fmtNb(m.marge)} ${m.base_label}</span>
      <span class="cmp-mc-taux">${m.taux_marge != null ? (m.taux_marge * 100).toFixed(0) + ' %' : '—'}</span>
      <span class="cmp-mc-coef">${m.coef != null ? '×' + m.coef.toFixed(2) : ''}</span>`;
  } else {
    resume = `<span class="cmp-mc-attente">à compléter</span>`;
  }
  // Pastille du fournisseur de référence choisi (ou « réf ? »).
  const pastille = ligneRef
    ? `<span class="cmp-mc-ref" title="${esc(ligneRef.fournisseur_nom)} · ${esc(ligneRef.designation)}">${esc(ligneRef.fournisseur_nom)}</span>`
    : `<span class="cmp-mc-ref cmp-mc-ref--vide">réf ?</span>`;

  const barre = `<div class="cmp-mc-head" data-cv="${p.id}">
    <span class="cmp-mc-chevron">${ouvert ? '▾' : '▸'}</span>
    <span class="cmp-mc-nom">${esc(p.nom)}</span>
    ${pastille}
    <span class="cmp-mc-resume">${resume}</span>
    <button class="cmp-remove cmp-vente-delier" data-cv="${p.id}" title="Délier ce produit">✕</button>
  </div>`;

  if (!ouvert) return `<div class="cmp-marge-carte" data-cv="${p.id}">${barre}</div>`;

  // ── Zone d'édition (déplié) ─────────────────────────────────
  // Le choix de la référence se fait en cliquant une colonne du tableau comparatif complet.
  const grille = construireGrilleVS(lignesAchat, { choisirCv: p.id, refId });

  let detail;
  if (m) {
    detail = `<div class="cmp-marge-detail">coût matière <strong>${fmtNb(m.cout_matiere)} ${m.base_label}</strong> · vente HT <strong>${fmtNb(m.prix_vente_ht)} ${m.base_label}</strong></div>`;
  } else {
    let msg;
    if (refId == null) msg = '🎯 Cliquez une colonne du tableau ci-dessous pour choisir l\'achat de référence.';
    else if (estPiece && !p.poids_piece_kg) msg = '⚖ Renseignez le poids d\'une pièce.';
    else if (p.prix_vente_ttc == null) msg = '💶 Renseignez le prix de vente.';
    else msg = '€/kg de la référence indisponible (poids du colis manquant).';
    detail = `<div class="cmp-marge-attente cmp-marge-attente--sm">${msg}</div>`;
  }

  const edit = `<div class="cmp-mc-body">
    <div class="cmp-marge-ligne-edit">
      <label class="cmp-marge-mini">Prix vente TTC
        <input type="number" step="0.01" min="0" class="cmp-vente-prix" data-cv="${p.id}"
               value="${p.prix_vente_ttc != null ? p.prix_vente_ttc : ''}" placeholder="0.00">
        <span class="cmp-marge-unite">${uniteLabel} · TVA ${p.tva_percent != null ? p.tva_percent : '—'} %</span>
      </label>
      <label class="cmp-marge-mini">Unité
        <select class="cmp-vente-unite" data-cv="${p.id}">
          <option value="kg"${estPiece ? '' : ' selected'}>au kg</option>
          <option value="piece"${estPiece ? ' selected' : ''}>à la pièce</option>
        </select>
      </label>
      <label class="cmp-marge-mini cmp-marge-poids" style="${estPiece ? '' : 'display:none;'}">Poids/pièce (kg)
        <input type="number" step="0.001" min="0" class="cmp-vente-poids" data-cv="${p.id}"
               value="${p.poids_piece_kg != null ? p.poids_piece_kg : ''}" placeholder="0.000">
      </label>
    </div>
    ${detail}
    <div class="cmp-mc-grille-titre">🎯 Achat de référence — cliquez une colonne :</div>
    ${grille}
  </div>`;

  return `<div class="cmp-marge-carte cmp-marge-carte--ouverte" data-cv="${p.id}">${barre}${edit}</div>`;
}

function cablerMarge() {
  const search = $('cmp-vente-search');
  const box = $('cmp-vente-resultats');
  if (search) {
    let tv;
    search.addEventListener('input', () => {
      clearTimeout(tv);
      if (box.style.display === 'none') return;
      tv = setTimeout(() => rechercherProduitsVente(search.value.trim()), 250);
    });
  }
  // Flèche ▾ : ouvre / ferme la liste de suggestions explicitement.
  const toggle = $('cmp-vente-toggle');
  if (toggle) {
    toggle.addEventListener('click', () => {
      if (box.style.display === 'none') {
        rechercherProduitsVente(search.value.trim());
        search.focus();
      } else {
        box.style.display = 'none';
      }
    });
  }

  // Clic sur la barre résumé → déplie/replie cette carte (une seule ouverte à la fois).
  // On ignore les clics sur le bouton « délier » (géré à part).
  $('cmp-marge').querySelectorAll('.cmp-mc-head').forEach((h) => {
    h.addEventListener('click', (e) => {
      if (e.target.closest('.cmp-vente-delier')) return;
      const cv = Number(h.dataset.cv);
      margeOuvert = (margeOuvert === cv) ? null : cv;
      rendreMarge(dernierVS);
    });
  });

  // Boutons « délier » par produit.
  $('cmp-marge').querySelectorAll('.cmp-vente-delier').forEach((b) => {
    b.addEventListener('click', (e) => { e.stopPropagation(); delierVente(Number(b.dataset.cv)); });
  });

  // Prix de vente éditable (blur / Entrée).
  $('cmp-marge').querySelectorAll('.cmp-vente-prix').forEach((inp) => {
    const valider = () => {
      const v = inp.value.trim();
      majVente(Number(inp.dataset.cv), { prix_vente_ttc: v === '' ? null : Number(v) });
    };
    inp.addEventListener('blur', valider);
    inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') inp.blur(); });
  });

  // Unité de vente (change → enregistre).
  $('cmp-marge').querySelectorAll('.cmp-vente-unite').forEach((sel) => {
    sel.addEventListener('change', () => {
      majVente(Number(sel.dataset.cv), { unite_vente: sel.value });
    });
  });

  // Poids d'une pièce (blur / Entrée).
  $('cmp-marge').querySelectorAll('.cmp-vente-poids').forEach((inp) => {
    const valider = () => {
      const v = inp.value.trim();
      majVente(Number(inp.dataset.cv), { poids_piece_kg: v === '' ? null : Number(v) });
    };
    inp.addEventListener('blur', valider);
    inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') inp.blur(); });
  });

  // Choix de la référence : clic sur une colonne du tableau comparatif dans la carte dépliée.
  // Recliquer la colonne déjà choisie la retire.
  $('cmp-marge').querySelectorAll('[data-choix-ligne]').forEach((cell) => {
    cell.addEventListener('click', () => {
      const cv = Number(cell.dataset.choixCv);
      const ligne = Number(cell.dataset.choixLigne);
      const pv = (dernierVS.produits_vente || []).find((x) => x.id === cv);
      const dejaChoisi = pv && pv.ligne_choisie_id === ligne;
      choisirReferenceVente(cv, dejaChoisi ? null : ligne);
    });
  });
}

// Recherche / suggestions de produits de vente.
// q vide → suggestions sémantiques sur le nom du groupe (les plus proches en haut),
// la liste complète reste accessible en dessous (« être sûr de ne rien rater »).
async function rechercherProduitsVente(q) {
  if (!groupeCourant) return;
  const box = $('cmp-vente-resultats');
  const semantique = !q;   // pas de saisie = mode suggestions
  const url = `${API_CMP}/groupes/${groupeCourant}/vente-suggestions` +
    (q ? `?q=${encodeURIComponent(q)}` : '');
  const r = await fetch(url);
  const items = r.ok ? await r.json() : [];
  if (!items.length) {
    box.innerHTML = '<div class="cmp-empty cmp-empty--sm">Aucun produit de vente disponible.</div>';
    box.style.display = '';
    return;
  }
  // En mode sémantique, on titre les vraies suggestions (score > 0) puis le reste.
  const aSugg = semantique && items.some((p) => (p.score || 0) > 0);
  let html = '';
  let titreReste = false;
  items.slice(0, 30).forEach((p) => {
    if (semantique && aSugg && !titreReste && (p.score || 0) === 0) {
      html += '<div class="cmp-vente-titre">Tous les produits de vente</div>';
      titreReste = true;
    }
    const prix = p.prix_vente_ttc != null ? fmtEuro(p.prix_vente_ttc) : '—';
    const sf = p.sous_famille ? esc(p.sous_famille) : 'sans sous-famille';
    const score = (p.score != null && p.score > 0)
      ? `<span class="cmp-score">${Math.round(p.score * 100)}%</span>` : '';
    html += `<div class="cmp-vente-resultat" data-id="${p.id}">
      <span class="cmp-vente-resultat-nom">${esc(p.nom)} ${score}</span>
      <span class="cmp-vente-resultat-meta">${sf} · ${prix}</span>
    </div>`;
  });
  if (aSugg) {
    html = '<div class="cmp-vente-titre">Suggestions (proches du nom du groupe)</div>' + html;
  }
  box.innerHTML = html;
  box.style.display = '';
  box.querySelectorAll('.cmp-vente-resultat').forEach((el) => {
    el.addEventListener('click', () => associerVente(Number(el.dataset.id)));
  });
}

// Ajoute un produit de vente au groupe (1 groupe → N ventes).
async function associerVente(catalogueVenteId) {
  if (!groupeCourant) return;
  const r = await fetch(`${API_CMP}/groupes/${groupeCourant}/ventes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ catalogue_vente_id: catalogueVenteId }),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    alert(d.detail || 'Association impossible.');
    return;
  }
  dernierVS = await r.json();
  rendreVS(dernierVS);
  majBadgeMargeKo();
}

// Délie un produit de vente du groupe.
async function delierVente(cvId) {
  if (!groupeCourant) return;
  const r = await fetch(`${API_CMP}/groupes/${groupeCourant}/ventes/${cvId}`, { method: 'DELETE' });
  if (!r.ok) { alert('Retrait impossible.'); return; }
  dernierVS = await r.json();
  rendreVS(dernierVS);
  majBadgeMargeKo();
}

// Édite un champ d'un produit de vente associé (prix, unité, poids pièce).
async function majVente(cvId, patch) {
  if (!groupeCourant) return;
  const r = await fetch(`${API_CMP}/groupes/${groupeCourant}/ventes/${cvId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    alert(d.detail || 'Mise à jour impossible.');
    return;
  }
  dernierVS = await r.json();
  rendreVS(dernierVS);
  majBadgeMargeKo();
}

// Choisit la ligne d'achat de référence PROPRE à un produit de vente (sa marge se calcule dessus).
async function choisirReferenceVente(cvId, ligneId) {
  if (!groupeCourant) return;
  const r = await fetch(`${API_CMP}/groupes/${groupeCourant}/ventes/${cvId}/reference`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ligne_choisie_id: ligneId }),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    alert(d.detail || 'Choix impossible.');
    return;
  }
  dernierVS = await r.json();
  rendreVS(dernierVS);
  majBadgeMargeKo();
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

// ── Badge + modale "marges en attente d'une information" ─────
// Groupes DÉJÀ associés à un produit de vente mais dont la marge est bloquée par
// une info manquante (référence non choisie, €/kg indispo, ou pas de prix de vente).
let margeKoCache = [];

async function majBadgeMargeKo() {
  try {
    const r = await fetch(`${API_CMP}/marge-incalculable`);
    if (!r.ok) return;
    const d = await r.json();
    margeKoCache = d.groupes || [];
    const n = d.total ?? 0;
    const badge = $('badge-marge-ko');
    if (n > 0) {
      $('badge-marge-ko-texte').textContent =
        `${n} produit(s) de vente sans marge calculable (info manquante)`;
      badge.style.display = '';
    } else {
      badge.style.display = 'none';
    }
  } catch { /* silencieux */ }
}

function ouvrirMargeKo() {
  $('cmp-marge-ko').style.display = '';
  const liste = $('cmp-marge-ko-liste');
  if (!margeKoCache.length) {
    $('cmp-marge-ko-info').textContent =
      'Toutes les marges des produits associés sont calculables. 👍';
    liste.innerHTML = '';
    return;
  }
  $('cmp-marge-ko-info').innerHTML =
    `${margeKoCache.length} produit(s) de vente associé(s) attendent une information pour ` +
    `calculer la marge. Cliquez pour ouvrir le groupe et compléter.`;
  liste.innerHTML = margeKoCache.map((g) => {
    return `<div class="cmp-resultat">
      <div class="cmp-resultat-info">
        <div class="cmp-resultat-nom">${esc(g.vente_nom)}</div>
        <div class="cmp-resultat-meta">groupe « ${esc(g.groupe_nom)} » · <span class="cmp-indispo">${esc(g.detail)}</span></div>
      </div>
      <button class="ach-btn ach-btn--primary cmp-marge-go" data-g="${g.groupe_id}">Compléter →</button>
    </div>`;
  }).join('');
  liste.querySelectorAll('.cmp-marge-go').forEach((b) => {
    b.addEventListener('click', () => {
      // La correction se fait dans le comparateur : on ouvre directement le groupe.
      fermerMargeKo();
      const sel = $('select-groupe');
      sel.value = b.dataset.g;
      sel.dispatchEvent(new Event('change'));
    });
  });
}
function fermerMargeKo() { $('cmp-marge-ko').style.display = 'none'; }

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  chargerGroupes();
  majBadgeNonGroupes();
  majBadgeMargeKo();

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
  $('btn-groupe-suivant').addEventListener('click', groupeSuivant);
  $('btn-ajouter-ligne').addEventListener('click', ouvrirPanneau);
  $('btn-fermer-panneau').addEventListener('click', fermerPanneau);
  $('btn-voir-marge-ko').addEventListener('click', ouvrirMargeKo);
  $('btn-fermer-marge-ko').addEventListener('click', fermerMargeKo);

  // Fermer la liste de suggestions produit-vente au clic en dehors (attaché 1 seule fois).
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.cmp-marge-assoc')) {
      const box = $('cmp-vente-resultats');
      if (box) box.style.display = 'none';
    }
  });

  let t;
  $('cmp-search').addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(rafraichirPanneau, 250);
  });
});

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

// Marge à la volée (miroir front de _calc_marge backend) — pour simuler, dans le tableau de
// choix, la marge que donnerait CHAQUE fournisseur avec le prix/unité/poids du produit de vente.
// Retourne null si incalculable (achat €/kg absent, prix vente ≤ 0, ou pièce sans poids).
function calcMargeFront(prixVenteTtc, tvaPercent, achatRefKg, uniteVente, poidsPieceKg) {
  if (achatRefKg == null || prixVenteTtc == null) return null;
  const ttc = Number(prixVenteTtc), achat = Number(achatRefKg);
  if (!(ttc > 0)) return null;
  const tva = tvaPercent != null ? Number(tvaPercent) : 0;
  const venteHt = ttc / (1 + tva / 100);
  let cout, base;
  if (uniteVente === 'piece') {
    if (!(Number(poidsPieceKg) > 0)) return null;
    cout = achat * Number(poidsPieceKg);
    base = '€/pièce';
  } else {
    cout = achat;
    base = '€/kg';
  }
  const marge = venteHt - cout;
  return {
    base_label: base,
    marge,
    taux_marge: venteHt > 0 ? marge / venteHt : null,
    coef: cout > 0 ? ttc / cout : null,
  };
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

// ── Recherche « partir du produit à vendre » ──────────────────
// On tape un nom de produit du catalogue de vente, on voit les correspondances
// et le groupe de comparaison auquel chacun est relié, puis on clique pour
// ouvrir directement son VS / sa marge.
async function rechercherVenteSauter() {
  const q = $('cmp-recherche-vente').value.trim();
  const pop = $('cmp-recherche-vente-resultats');
  if (q.length < 2) { pop.style.display = 'none'; pop.innerHTML = ''; return; }
  const r = await fetch(`${API_CMP}/recherche-ventes?q=${encodeURIComponent(q)}`);
  if (!r.ok) { pop.style.display = 'none'; return; }
  const items = (await r.json()).produits || [];
  if (!items.length) {
    pop.innerHTML = '<div class="cmp-recherche-vide">Aucun produit de vente trouvé.</div>';
    pop.style.display = '';
    return;
  }
  pop.innerHTML = items.map((p) => {
    const prix = p.prix_vente_ttc != null ? fmtEuro(p.prix_vente_ttc) : '—';
    const groupe = p.groupe_id
      ? `<span class="cmp-recherche-groupe">⚖️ ${esc(p.groupe_nom)}</span>`
      : '<span class="cmp-recherche-sansgroupe">non suivi (cliquer pour démarrer)</span>';
    return `<div class="cmp-recherche-item" data-groupe="${p.groupe_id || ''}" data-cv="${p.id}">
      <div class="cmp-recherche-nom">${esc(p.nom)}</div>
      <div class="cmp-recherche-meta">${prix} · ${groupe}</div>
    </div>`;
  }).join('');
  pop.style.display = '';
  pop.querySelectorAll('.cmp-recherche-item').forEach((el) => {
    el.addEventListener('click', () => ouvrirDepuisVente(el));
  });
}

// Clic sur un résultat : si le produit a un groupe, on l'ouvre ; sinon on en crée un.
async function ouvrirDepuisVente(el) {
  $('cmp-recherche-vente-resultats').style.display = 'none';
  $('cmp-recherche-vente').value = '';
  const groupeId = el.dataset.groupe ? Number(el.dataset.groupe) : null;
  if (groupeId) {
    const sel = $('select-groupe');
    sel.value = String(groupeId);
    sel.dispatchEvent(new Event('change'));
    return;
  }
  // Produit non suivi → on propose de démarrer son suivi de marge.
  const cvId = Number(el.dataset.cv);
  if (!confirm('Ce produit n\'a pas encore de groupe de comparaison. En créer un pour suivre sa marge ?')) return;
  await creerGroupeDepuisVente(cvId);
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
  const produits = data.produits_vente || [];

  if (!lignes.length) {
    // Groupe sans article d'achat. S'il a un produit de vente associé, on propose
    // automatiquement les achats correspondants (matching sur le nom du groupe).
    if (produits.length) {
      rendreMarge(data);                 // affiche la/les carte(s) produit de vente
      proposerAchatsAuto();              // remplit #cmp-vs avec les suggestions d'achat
    } else {
      $('cmp-marge').style.display = 'none';
      $('cmp-vs').innerHTML =
        `<div class="cmp-empty">Ce groupe est vide. Cliquez sur « + Ajouter un article » pour comparer des produits.</div>`;
    }
    return;
  }

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

// Propose automatiquement, dans #cmp-vs, les articles d'achat proches du nom du groupe
// (= produit de vente), à cocher pour les ajouter. Utilisé quand le groupe n'a pas encore
// d'article d'achat à comparer.
async function proposerAchatsAuto() {
  if (!groupeCourant) return;
  const cible = $('cmp-vs');
  cible.innerHTML = '<div class="cmp-empty cmp-empty--sm">Recherche des achats correspondants…</div>';
  const r = await fetch(`${API_CMP}/groupes/${groupeCourant}/achats-suggestions`);
  const items = r.ok ? await r.json() : [];
  if (!items.length) {
    cible.innerHTML = `<div class="cmp-empty">Aucun achat correspondant trouvé automatiquement.
      Utilisez « + Ajouter un article » pour chercher manuellement.</div>`;
    return;
  }
  const lignes = items.map((a) => {
    const pk = a.prix_kg != null ? fmtPrixKg(a.prix_kg) : '<span class="cmp-indispo">€/kg indispo</span>';
    return `<label class="cmp-grappe-art">
      <input type="checkbox" class="cmp-auto-cb" data-id="${a.id}" checked>
      <span class="cmp-grappe-art-nom">${esc(a.designation)} <span class="cmp-score">${Math.round(a.score * 100)}%</span></span>
      <span class="cmp-grappe-art-meta">${esc(a.fournisseur_nom)} · ${esc(a.code_article)} · ${pk}</span>
    </label>`;
  }).join('');
  cible.innerHTML = `<div class="cmp-auto">
    <div class="cmp-auto-titre">🔎 Achats correspondant à « ${esc(dernierVS.groupe.nom)} » — décochez les intrus, puis ajoutez :</div>
    <label class="cmp-grappe-art cmp-auto-tout">
      <input type="checkbox" id="cmp-auto-tout" checked>
      <span class="cmp-grappe-art-nom"><strong>Tout sélectionner / désélectionner</strong></span>
    </label>
    <div class="cmp-grappe-arts">${lignes}</div>
    <div class="cmp-auto-actions">
      <button class="ach-btn ach-btn--primary" id="cmp-auto-ajouter">✓ Ajouter les articles cochés</button>
    </div>
  </div>`;
  $('cmp-auto-ajouter').addEventListener('click', ajouterAchatsCoches);
  // Case maîtresse : bascule toutes les cases d'un coup.
  const tout = $('cmp-auto-tout');
  const cases = [...cible.querySelectorAll('.cmp-auto-cb')];
  tout.addEventListener('change', () => {
    cases.forEach((cb) => { cb.checked = tout.checked; });
  });
  // Reflet inverse : la case maîtresse suit l'état réel (cochée / décochée / indéterminée).
  const majTout = () => {
    const n = cases.filter((cb) => cb.checked).length;
    tout.checked = n === cases.length;
    tout.indeterminate = n > 0 && n < cases.length;
  };
  cases.forEach((cb) => cb.addEventListener('change', majTout));
}

async function ajouterAchatsCoches() {
  const ids = [...document.querySelectorAll('.cmp-auto-cb:checked')].map((cb) => Number(cb.dataset.id));
  if (!ids.length) { alert('Cochez au moins un article.'); return; }
  for (const id of ids) {
    await fetch(`${API_CMP}/groupes/${groupeCourant}/lignes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ catalogue_fournisseur_id: id }),
    });
  }
  await afficherVS(groupeCourant);   // recharge : le VS / les cartes affichent les articles ajoutés
}

// Construit la grille comparative (fournisseurs en colonnes). Réutilisée pour le VS global
// ET, en mode cliquable, à l'intérieur d'une carte produit pour choisir sa référence.
//   opts.retirer    → bouton ✕ « retirer du groupe » dans l'en-tête.
//   opts.choisirCv  → id du produit de vente : rend les colonnes cliquables (choix de référence).
//   opts.refId      → id de la ligne actuellement choisie (colonne mise en évidence).
function construireGrilleVS(lignes, opts = {}) {
  const { retirer = false, choisirCv = null, refId = null, pv = null } = opts;
  const cliquable = choisirCv != null;

  // La colonne choisie comme référence (arbitrage utilisateur) passe tout à gauche, devant
  // le tri par prix. Copie locale pour ne pas muter le tableau partagé (dernierVS.lignes).
  if (cliquable && refId != null) {
    const ref = lignes.find((l) => l.id === refId);
    if (ref) lignes = [ref, ...lignes.filter((l) => l.id !== refId)];
  }

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

  // En-têtes fournisseurs (cliquables si choix de référence). Le ✕ « retirer du groupe »
  // est présent dans les deux modes ; en mode choix s'ajoute le badge « ✓ réf » si choisi.
  html += '<div class="cmp-cell cmp-cell--head cmp-cell--label"></div>';
  lignes.forEach((l) => {
    const attrs = cliquable
      ? ` data-choix-cv="${choisirCv}" data-choix-ligne="${l.id}" role="button" title="Choisir cet achat comme référence"`
      : '';
    const croix = (retirer || cliquable)
      ? `<button class="cmp-remove" data-cat="${l.id}" title="Retirer du groupe">✕</button>` : '';
    const refBadge = (cliquable && l.id === refId) ? '<span class="cmp-ref-check">✓ réf</span>' : '';
    html += `<div class="cmp-cell cmp-cell--head${colClass(l)}"${attrs}>
      <div class="cmp-fourn">${esc(l.fournisseur_nom)}</div>
      ${refBadge}${croix}
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

  // En mode choix : marge simulée par fournisseur (avec le prix/unité/poids du produit de vente).
  // 3 lignes — marge €, taux %, coef — pour arbitrer « lequel rapporte le plus » directement.
  if (cliquable && pv) {
    const marges = lignes.map((l) =>
      calcMargeFront(pv.prix_vente_ttc, pv.tva_percent, l.prix_kg, pv.unite_vente, pv.poids_piece_kg));
    // meilleure marge (la plus haute) pour la mettre en avant
    let maxMarge = null;
    marges.forEach((mm) => { if (mm && (maxMarge == null || mm.marge > maxMarge)) maxMarge = mm.marge; });

    const ligneMarge = (label, fmt, cls) => {
      html += `<div class="cmp-cell cmp-cell--label cmp-cell--marge">${label}</div>`;
      lignes.forEach((l, i) => {
        const mm = marges[i];
        const attrs = ` data-choix-cv="${choisirCv}" data-choix-ligne="${l.id}"`;
        const best = mm && cls === 'marge' && maxMarge != null && mm.marge === maxMarge ? ' cmp-marge-best' : '';
        const refc = (l.id === refId) ? ' cmp-ref' : '';
        html += `<div class="cmp-cell cmp-cell--marge${best}${refc}"${attrs}>${mm ? fmt(mm) : '—'}</div>`;
      });
    };
    ligneMarge('➤ Marge', (mm) => `<strong>${fmtNb(mm.marge)} ${mm.base_label}</strong>`, 'marge');
    ligneMarge('Taux', (mm) => mm.taux_marge != null ? (mm.taux_marge * 100).toFixed(1) + ' %' : '—', 'taux');
    ligneMarge('Coef', (mm) => mm.coef != null ? '×' + mm.coef.toFixed(2) : '—', 'coef');
  }

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

  // Bouton d'AJOUT : ouvre le panneau d'association (recherche + filtres + sélection multiple).
  let html = `<div class="cmp-marge-assoc">
    <label class="cmp-marge-lbl">🏷️ Produits de vente associés</label>
    <button class="ach-btn ach-btn--primary" id="cmp-vente-ajouter">+ Associer des produits de vente</button>
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

  // Classification : utile pour les viandes (« Collier de quoi ? »). Pastille rouge si absente.
  const sfLabel = p.sous_famille
    ? `<span class="cmp-mc-sf" title="${esc(p.famille || '')}">${esc(p.sous_famille)}</span>`
    : `<span class="cmp-mc-sf cmp-mc-sf--vide" title="Classez ce produit (déplier)">famille ?</span>`;

  const barre = `<div class="cmp-mc-head" data-cv="${p.id}">
    <span class="cmp-mc-chevron">${ouvert ? '▾' : '▸'}</span>
    <span class="cmp-mc-nom">${esc(p.nom)}</span>
    ${sfLabel}
    ${pastille}
    <span class="cmp-mc-resume">${resume}</span>
    <button class="cmp-remove cmp-vente-delier" data-cv="${p.id}" title="Délier ce produit">✕</button>
  </div>`;

  if (!ouvert) return `<div class="cmp-marge-carte" data-cv="${p.id}">${barre}</div>`;

  // ── Zone d'édition (déplié) ─────────────────────────────────
  // Le choix de la référence se fait en cliquant une colonne du tableau comparatif complet.
  const grille = construireGrilleVS(lignesAchat, { choisirCv: p.id, refId, pv: p });

  // Encart marge : KPI clairs + détail + équivalent €/kg (utile pour la pièce).
  let encart;
  if (m) {
    const equiv = estPiece
      ? `<div class="cmp-mc-equiv">≈ vendu <strong>${fmtNb(m.vente_ht_kg)} €/kg</strong> HT · acheté <strong>${fmtNb(m.cout_kg)} €/kg</strong></div>`
      : '';
    encart = `<div class="cmp-mc-resultat">
      <div class="cmp-mc-kpis">
        <div class="cmp-mc-kpi"><span class="cmp-mc-kpi-val">${fmtNb(m.marge)} ${m.base_label}</span><span class="cmp-mc-kpi-lbl">marge brute</span></div>
        <div class="cmp-mc-kpi"><span class="cmp-mc-kpi-val">${m.taux_marge != null ? (m.taux_marge * 100).toFixed(1) + ' %' : '—'}</span><span class="cmp-mc-kpi-lbl">taux</span></div>
        <div class="cmp-mc-kpi"><span class="cmp-mc-kpi-val">${m.coef != null ? '×' + m.coef.toFixed(2) : '—'}</span><span class="cmp-mc-kpi-lbl">coefficient</span></div>
      </div>
      <div class="cmp-marge-detail">coût matière <strong>${fmtNb(m.cout_matiere)} ${m.base_label}</strong> · vente HT <strong>${fmtNb(m.prix_vente_ht)} ${m.base_label}</strong></div>
      ${equiv}
    </div>`;
  } else {
    let msg;
    if (refId == null) msg = '🎯 Cliquez une colonne du tableau ci-dessous pour choisir l\'achat de référence.';
    else if (estPiece && !p.poids_piece_kg) msg = '⚖ Renseignez le poids d\'une pièce.';
    else if (p.prix_vente_ttc == null) msg = '💶 Renseignez le prix de vente.';
    else msg = '€/kg de la référence indisponible (poids du colis manquant).';
    encart = `<div class="cmp-marge-attente cmp-marge-attente--sm">${msg}</div>`;
  }

  const edit = `<div class="cmp-mc-body">
    <div class="cmp-mc-params">
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
      <label class="cmp-marge-mini">Famille
        <select class="cmp-vente-famille" id="cmp-fam-${p.id}" data-cv="${p.id}"></select>
      </label>
      <label class="cmp-marge-mini">Sous-famille
        <select class="cmp-vente-sf" id="cmp-sf-${p.id}" data-cv="${p.id}"></select>
      </label>
    </div>
    ${encart}
    <div class="cmp-mc-grille-titre">🎯 Achat de référence — cliquez une colonne :</div>
    ${grille}
  </div>`;

  return `<div class="cmp-marge-carte cmp-marge-carte--ouverte" data-cv="${p.id}">${barre}${edit}</div>`;
}

function cablerMarge() {
  // Bouton « + Associer des produits de vente » → ouvre le panneau dédié.
  const btnAj = $('cmp-vente-ajouter');
  if (btnAj) btnAj.addEventListener('click', ouvrirVentePanneau);

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

  // Famille / sous-famille (listes dépendantes, référentiel partagé familles.js).
  $('cmp-marge').querySelectorAll('.cmp-vente-famille').forEach((selFam) => {
    const cv = Number(selFam.dataset.cv);
    const p = (dernierVS.produits_vente || []).find((x) => x.id === cv) || {};
    const selSf = $(`cmp-sf-${cv}`);
    peuplerSelectFamille(selFam, null, p.famille || '');
    majSousFamille(p.famille || '', selSf, p.sous_famille || '');
    selFam.addEventListener('change', () => {
      majSousFamille(selFam.value, selSf, '');   // reset sous-famille au changement de famille
      majVente(cv, { famille: selFam.value || null, sous_famille: null });
    });
    selSf.addEventListener('change', () => {
      majVente(cv, { sous_famille: selSf.value || null });
    });
  });

  // ✕ « retirer du groupe » dans le tableau d'une carte (sort l'article de TOUT le groupe).
  $('cmp-marge').querySelectorAll('.cmp-remove').forEach((b) => {
    b.addEventListener('click', (e) => { e.stopPropagation(); retirerLigne(b.dataset.cat); });
  });

  // Choix de la référence : clic sur une colonne du tableau comparatif dans la carte dépliée.
  // Recliquer la colonne déjà choisie la retire. Le clic sur le ✕ est ignoré (géré ci-dessus).
  $('cmp-marge').querySelectorAll('[data-choix-ligne]').forEach((cell) => {
    cell.addEventListener('click', (e) => {
      if (e.target.closest('.cmp-remove')) return;
      const cv = Number(cell.dataset.choixCv);
      const ligne = Number(cell.dataset.choixLigne);
      const pv = (dernierVS.produits_vente || []).find((x) => x.id === cv);
      const dejaChoisi = pv && pv.ligne_choisie_id === ligne;
      choisirReferenceVente(cv, dejaChoisi ? null : ligne);
    });
  });
}

// ── Panneau d'association de produits de vente (recherche + filtres + multi) ──
function ouvrirVentePanneau() {
  if (!groupeCourant) return;
  $('cmp-vente-panneau').style.display = '';
  $('cmpv-search').value = '';
  peuplerSelectFamille($('cmpv-filtre-famille'), null, '');
  majSousFamille('', $('cmpv-filtre-sous-famille'), '');
  rafraichirVentePanneau();
  $('cmpv-search').focus();
}
function fermerVentePanneau() { $('cmp-vente-panneau').style.display = 'none'; }

async function rafraichirVentePanneau() {
  const q = $('cmpv-search').value.trim();
  const fam = $('cmpv-filtre-famille').value;
  const sf = $('cmpv-filtre-sous-famille').value;
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (fam) params.set('famille', fam);
  if (sf) params.set('sous_famille', sf);
  const qs = params.toString();
  const r = await fetch(`${API_CMP}/groupes/${groupeCourant}/vente-suggestions${qs ? '?' + qs : ''}`);
  const items = r.ok ? await r.json() : [];
  const box = $('cmpv-resultats');
  const semantique = !(q || fam || sf);
  if (!items.length) {
    majVentePanneauSelection([]);
    box.innerHTML = '<div class="cmp-empty cmp-empty--sm">Aucun produit de vente disponible.</div>';
    return;
  }
  // En mode sémantique : titrer les vraies suggestions (score>0) puis le reste.
  const aSugg = semantique && items.some((p) => (p.score || 0) > 0);
  let html = '';
  let titreReste = false;
  items.forEach((p) => {
    if (semantique && aSugg && !titreReste && (p.score || 0) === 0) {
      html += '<div class="cmp-vente-titre">Tous les produits de vente</div>';
      titreReste = true;
    }
    const prix = p.prix_vente_ttc != null ? fmtEuro(p.prix_vente_ttc) : '—';
    const clf = (p.famille || p.sous_famille)
      ? esc([p.famille, p.sous_famille].filter(Boolean).join(' · ')) : 'non classé';
    const score = (p.score != null && p.score > 0)
      ? `<span class="cmp-score">${Math.round(p.score * 100)}%</span>` : '';
    // Produit déjà dans un autre groupe → mention « déplacer depuis X ».
    const deplace = p.groupe_actuel_id
      ? `<span class="cmp-deplace" title="L'associer ici le déplacera">↪ déjà dans « ${esc(p.groupe_actuel_nom)} »</span>`
      : '';
    html += `<label class="cmp-resultat cmp-resultat--cb">
      <input type="checkbox" class="cmpv-cb" data-id="${p.id}">
      <div class="cmp-resultat-info">
        <div class="cmp-resultat-nom">${esc(p.nom)} ${score} ${deplace}</div>
        <div class="cmp-resultat-meta">${clf} · ${prix}</div>
      </div>
    </label>`;
  });
  if (aSugg) html = '<div class="cmp-vente-titre">Suggestions (proches du nom du groupe)</div>' + html;
  box.innerHTML = html;
  majVentePanneauSelection([...box.querySelectorAll('.cmpv-cb')]);
}

function majVentePanneauSelection(cases) {
  const has = cases.length > 0;
  $('cmpv-tout-label').style.display = has ? '' : 'none';
  $('cmpv-pied').style.display = has ? '' : 'none';
  if (!has) return;
  const tout = $('cmpv-tout');
  tout.checked = false; tout.indeterminate = false;
  tout.onchange = () => cases.forEach((cb) => { cb.checked = tout.checked; });
  const majTout = () => {
    const n = cases.filter((cb) => cb.checked).length;
    tout.checked = n === cases.length;
    tout.indeterminate = n > 0 && n < cases.length;
  };
  cases.forEach((cb) => cb.addEventListener('change', majTout));
}

async function associerSelectionVente() {
  const ids = [...$('cmpv-resultats').querySelectorAll('.cmpv-cb:checked')].map((cb) => Number(cb.dataset.id));
  if (!ids.length) { alert('Cochez au moins un produit.'); return; }
  for (const id of ids) {
    const r = await fetch(`${API_CMP}/groupes/${groupeCourant}/ventes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ catalogue_vente_id: id }),
    });
    if (r.ok) dernierVS = await r.json();   // déplacement géré côté serveur
  }
  rendreVS(dernierVS);
  majBadgeMargeKo();
  majBadgeVentesNonReliees();
  await rafraichirVentePanneau();   // retire les produits désormais dans ce groupe
}

// Délie un produit de vente du groupe.
async function delierVente(cvId) {
  if (!groupeCourant) return;
  const r = await fetch(`${API_CMP}/groupes/${groupeCourant}/ventes/${cvId}`, { method: 'DELETE' });
  if (!r.ok) { alert('Retrait impossible.'); return; }
  dernierVS = await r.json();
  rendreVS(dernierVS);
  majBadgeMargeKo();
  majBadgeVentesNonReliees();   // un produit redevient non relié
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

// ── Panneau d'ajout : recherche + filtres famille/sous-famille, sélection multiple ───
function ouvrirPanneau() {
  if (!groupeCourant) return;
  $('cmp-panneau').style.display = '';
  $('cmp-search').value = '';
  // Peupler les filtres (référentiel partagé familles.js), une fois à l'ouverture.
  const selFam = $('cmp-filtre-famille');
  const selSf = $('cmp-filtre-sous-famille');
  peuplerSelectFamille(selFam, null, '');
  majSousFamille('', selSf, '');
  rafraichirPanneau();
  $('cmp-search').focus();
}
function fermerPanneau() {
  $('cmp-panneau').style.display = 'none';
}

async function rafraichirPanneau() {
  const q = $('cmp-search').value.trim();
  const fam = $('cmp-filtre-famille').value;
  const sf = $('cmp-filtre-sous-famille').value;
  // Recherche dès qu'il y a un texte OU un filtre actif ; sinon, suggestions sémantiques.
  if (q || fam || sf) {
    await afficherRecherche(q, fam, sf);
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
    majPanneauSelection([]);
    $('cmp-resultats').innerHTML =
      '<div class="cmp-empty cmp-empty--sm">Recherchez un article (ou filtrez par famille) pour démarrer le groupe.</div>';
    return;
  }
  const refId = lignes[0].id;
  const r = await fetch(`${API_CMP}/suggestions?ligne_id=${refId}&groupe_id=${groupeCourant}`);
  const sugg = r.ok ? await r.json() : [];
  titre.style.display = sugg.length ? '' : 'none';
  if (!sugg.length) {
    majPanneauSelection([]);
    $('cmp-resultats').innerHTML =
      '<div class="cmp-empty cmp-empty--sm">Aucune suggestion. Utilisez la recherche ou les filtres.</div>';
    return;
  }
  rendreResultats(sugg, true);
}

// Recherche dans le catalogue, combinée aux filtres famille/sous-famille.
async function afficherRecherche(q, fam, sf) {
  $('cmp-suggestions-titre').style.display = 'none';
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (fam) params.set('famille', fam);
  if (sf) params.set('sous_famille', sf);
  const r = await fetch(`${API_CAT}?${params.toString()}`);
  let articles = r.ok ? await r.json() : [];
  // Exclure ceux déjà dans le groupe.
  const dans = new Set((dernierVS?.lignes || []).map((l) => l.id));
  articles = articles.filter((a) => !dans.has(a.id)).slice(0, 100);
  if (!articles.length) {
    majPanneauSelection([]);
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
    return `<label class="cmp-resultat cmp-resultat--cb">
      <input type="checkbox" class="cmp-add-cb" data-cat="${a.id}">
      <div class="cmp-resultat-info">
        <div class="cmp-resultat-nom">${esc(a.designation)} ${score}</div>
        <div class="cmp-resultat-meta">${esc(a.fournisseur_nom)} · ${esc(a.code_article)} · ${pk}</div>
      </div>
    </label>`;
  }).join('');
  majPanneauSelection([...$('cmp-resultats').querySelectorAll('.cmp-add-cb')]);
}

// Gère l'affichage « tout sélectionner » + pied + reflet de la case maîtresse.
function majPanneauSelection(cases) {
  const aDesResultats = cases.length > 0;
  $('cmp-add-tout-label').style.display = aDesResultats ? '' : 'none';
  $('cmp-add-pied').style.display = aDesResultats ? '' : 'none';
  if (!aDesResultats) return;
  const tout = $('cmp-add-tout');
  tout.checked = false;
  tout.indeterminate = false;
  tout.onchange = () => cases.forEach((cb) => { cb.checked = tout.checked; });
  const majTout = () => {
    const n = cases.filter((cb) => cb.checked).length;
    tout.checked = n === cases.length;
    tout.indeterminate = n > 0 && n < cases.length;
  };
  cases.forEach((cb) => cb.addEventListener('change', majTout));
}

// Ajoute tous les articles cochés du panneau.
async function ajouterSelectionPanneau() {
  const ids = [...$('cmp-resultats').querySelectorAll('.cmp-add-cb:checked')].map((cb) => Number(cb.dataset.cat));
  if (!ids.length) { alert('Cochez au moins un article.'); return; }
  for (const id of ids) {
    await fetch(`${API_CMP}/groupes/${groupeCourant}/lignes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ catalogue_fournisseur_id: id }),
    });
  }
  await afficherVS(groupeCourant);
  await chargerGroupes(groupeCourant);
  rafraichirPanneau();
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

// ── Badge + modale "produits de vente non reliés" (couverture catalogue) ─────
let ventesNonReliees = [];

async function majBadgeVentesNonReliees() {
  try {
    const r = await fetch(`${API_CMP}/ventes-non-reliees`);
    if (!r.ok) return;
    const d = await r.json();
    ventesNonReliees = d.produits || [];
    const n = d.total ?? 0;
    const badge = $('badge-ventes-non-reliees');
    if (n > 0) {
      $('badge-ventes-non-reliees-texte').textContent =
        `${n} produit(s) de vente sans suivi de marge`;
      badge.style.display = '';
    } else {
      badge.style.display = 'none';
    }
  } catch { /* silencieux */ }
}

function ouvrirVentesNonReliees() {
  $('cmp-non-reliees').style.display = '';
  const liste = $('cmp-non-reliees-liste');
  if (!ventesNonReliees.length) {
    $('cmp-non-reliees-info').textContent =
      'Tous les produits de vente sont reliés à un groupe de comparaison. 👍';
    liste.innerHTML = '';
    return;
  }
  $('cmp-non-reliees-info').innerHTML =
    `${ventesNonReliees.length} produit(s) de vente ne sont reliés à aucun groupe d'achat ` +
    `(donc aucun suivi de marge). « Créer un groupe » démarre le suivi pour ce produit.`;
  liste.innerHTML = ventesNonReliees.map((p) => {
    const prix = p.prix_vente_ttc != null ? fmtEuro(p.prix_vente_ttc) : '—';
    const clf = (p.famille || p.sous_famille)
      ? esc([p.famille, p.sous_famille].filter(Boolean).join(' · '))
      : '<span class="cmp-indispo">non classé</span>';
    return `<div class="cmp-resultat">
      <div class="cmp-resultat-info">
        <div class="cmp-resultat-nom">${esc(p.nom)}</div>
        <div class="cmp-resultat-meta">${clf} · ${prix}</div>
      </div>
      <button class="ach-btn ach-btn--primary cmp-nr-creer" data-id="${p.id}">+ Créer un groupe</button>
    </div>`;
  }).join('');
  liste.querySelectorAll('.cmp-nr-creer').forEach((b) => {
    b.addEventListener('click', () => creerGroupeDepuisVente(Number(b.dataset.id)));
  });
}
function fermerVentesNonReliees() { $('cmp-non-reliees').style.display = 'none'; }

// Crée un groupe nommé d'après le produit + l'associe, puis ouvre ce groupe.
async function creerGroupeDepuisVente(cvId) {
  const r = await fetch(`${API_CMP}/groupes/from-vente`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ catalogue_vente_id: cvId }),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    alert(d.detail || 'Création impossible.');
    return;
  }
  const groupe = await r.json();
  fermerVentesNonReliees();
  await majBadgeVentesNonReliees();
  await chargerGroupes(groupe.id);
  afficherVS(groupe.id);
}

// Crée d'un coup un groupe par produit de vente non relié.
async function creerTousGroupes() {
  const n = ventesNonReliees.length;
  if (!n) return;
  if (!confirm(`Créer ${n} groupe(s) de comparaison, un par produit de vente sans suivi ?`)) return;
  const r = await fetch(`${API_CMP}/groupes/from-ventes-bulk`, { method: 'POST' });
  if (!r.ok) { alert('Création impossible.'); return; }
  const d = await r.json();
  fermerVentesNonReliees();
  await majBadgeVentesNonReliees();
  await chargerGroupes();
  alert(`${d.crees} groupe(s) créé(s). Ouvrez-en un : les achats correspondants sont proposés automatiquement.`);
}

// Réorganise la viande par sous-famille : supprime les groupes viande vraiment vides
// (sans réf ni achat) et regroupe les produits viande par sous-famille (Bœuf, Veau…).
async function reorganiserViande() {
  if (!confirm(
    'Réorganiser la VIANDE par sous-famille ?\n\n' +
    '• Les groupes viande SANS référence ni article d\'achat seront supprimés (rien d\'utile perdu).\n' +
    '• Les produits viande seront regroupés par sous-famille (Bœuf, Veau, Agneau…).\n' +
    '• Les groupes viande où vous avez déjà mis des achats sont conservés.'
  )) return;
  const r = await fetch(`${API_CMP}/viande/reorganiser`, { method: 'POST' });
  if (!r.ok) { alert('Réorganisation impossible.'); return; }
  const d = await r.json();
  await chargerGroupes();
  await majBadgeVentesNonReliees();
  await majBadgeMargeKo();
  let msg = `${d.groupes_supprimes} groupe(s) supprimé(s), ${d.groupes_crees} groupe(s) créé(s) ` +
    `(${d.sous_familles.join(', ') || 'aucune sous-famille'}).`;
  if (d.produits_sans_sous_famille) {
    msg += `\n\n⚠ ${d.produits_sans_sous_famille} produit(s) viande sans sous-famille n'ont pas pu être ` +
      `regroupés : classez-les (carte produit) puis relancez.`;
  }
  if (d.groupes_epargnes.length) {
    msg += `\n\n${d.groupes_epargnes.length} groupe(s) conservé(s) car ils contiennent déjà des achats : ` +
      d.groupes_epargnes.map((e) => e.vente_nom).join(', ') + '.';
  }
  alert(msg);
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  chargerGroupes();
  majBadgeMargeKo();
  majBadgeVentesNonReliees();

  $('select-groupe').addEventListener('change', (e) => {
    majBoutonsGroupe();
    afficherVS(e.target.value ? Number(e.target.value) : null);
    fermerPanneau();
  });

  // Recherche « partir du produit à vendre » : saute au groupe qui le contient.
  let tr;
  $('cmp-recherche-vente').addEventListener('input', () => {
    clearTimeout(tr);
    tr = setTimeout(rechercherVenteSauter, 250);
  });
  // Fermer la liste de résultats au clic ailleurs.
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.cmp-recherche-vente')) {
      $('cmp-recherche-vente-resultats').style.display = 'none';
    }
  });
  $('btn-nouveau-groupe').addEventListener('click', creerGroupe);
  $('btn-reorg-viande').addEventListener('click', reorganiserViande);
  $('btn-renommer').addEventListener('click', renommerGroupe);
  $('btn-supprimer-groupe').addEventListener('click', supprimerGroupe);
  $('btn-groupe-suivant').addEventListener('click', groupeSuivant);
  $('btn-ajouter-ligne').addEventListener('click', ouvrirPanneau);
  $('btn-fermer-panneau').addEventListener('click', fermerPanneau);
  $('btn-voir-marge-ko').addEventListener('click', ouvrirMargeKo);
  $('btn-fermer-marge-ko').addEventListener('click', fermerMargeKo);
  $('btn-voir-ventes-non-reliees').addEventListener('click', ouvrirVentesNonReliees);
  $('btn-fermer-non-reliees').addEventListener('click', fermerVentesNonReliees);
  $('btn-creer-tous-groupes').addEventListener('click', creerTousGroupes);

  // Panneau d'ajout d'ARTICLES D'ACHAT : recherche + filtres + sélection.
  let t;
  $('cmp-search').addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(rafraichirPanneau, 250);
  });
  $('cmp-filtre-famille').addEventListener('change', () => {
    majSousFamille($('cmp-filtre-famille').value, $('cmp-filtre-sous-famille'), '');
    rafraichirPanneau();
  });
  $('cmp-filtre-sous-famille').addEventListener('change', rafraichirPanneau);
  $('cmp-add-selection').addEventListener('click', ajouterSelectionPanneau);

  // Panneau d'association de PRODUITS DE VENTE : recherche + filtres + sélection.
  $('btn-fermer-vente-panneau').addEventListener('click', fermerVentePanneau);
  let tv;
  $('cmpv-search').addEventListener('input', () => {
    clearTimeout(tv);
    tv = setTimeout(rafraichirVentePanneau, 250);
  });
  $('cmpv-filtre-famille').addEventListener('change', () => {
    majSousFamille($('cmpv-filtre-famille').value, $('cmpv-filtre-sous-famille'), '');
    rafraichirVentePanneau();
  });
  $('cmpv-filtre-sous-famille').addEventListener('change', rafraichirVentePanneau);
  $('cmpv-selection').addEventListener('click', associerSelectionVente);
});

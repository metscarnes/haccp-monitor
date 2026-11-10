/* popup-article-achat.js — Création d'un article du catalogue achats depuis une
   autre page (réception), avec le même formulaire et le même tunnel que le module
   Catalogue achats :
     1. formulaire « Nouvel article » (mêmes champs, mêmes contrôles de saisie) ;
     2. si la famille est vendable (Viande / Charcuterie / Traiteur) : « Suivre la
        marge de cet article ? » → créer un produit de vente et le lier, lier à un
        produit de vente existant, ou ignorer.

   Les règles métier sont celles de static/js/achats/catalogue-achats.js (sauver,
   detecterAnomaliesSaisie, ouvrirModalVentePropose, mvpLierAuProduit,
   mvpValiderCreation, mvpcCalcMarge) : toute évolution de l'une doit être reportée
   dans l'autre.

   Dépendances : /static/js/core/familles.js et /static/css/pages/achats.css.

   Utilisation :
     PopupArticleAchat.ouvrir({
       fournisseurId, fournisseurNom,   // fournisseur imposé (celui de la réception)
       designation, codeArticle,        // pré-remplissage facultatif
       onCree(article),                 // appelé dès la création de l'article
     });
*/
(function () {
  'use strict';

  const API_CAT   = '/api/achats/catalogue';
  const API_FOURN = '/api/achats/fournisseurs';
  const FAMILLES_VENDABLES = new Set(['Viande', 'Charcuterie', 'Traiteur']);
  const UNITES_IDS = { kg: 'paa-unite-kg', piece: 'paa-unite-piece', colis: 'paa-unite-colis' };

  let injecte = false;
  let fournisseurs = null;
  let options = {};
  let article = null;          // article créé (pour le tunnel produit de vente)
  let rechercheTimer = null;

  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtPrix = v => (v ?? 0).toFixed(2);

  async function lireErreur(r, defaut) {
    if (r.status === 401 || r.status === 403) {
      return "Réservé à l'administrateur : connectez-vous avec le compte administrateur "
        + "pour créer un article ou un produit de vente.";
    }
    const data = await r.json().catch(() => ({}));
    return data.detail || `${defaut} (erreur ${r.status})`;
  }

  // ── Markup (copie du module Catalogue achats, identifiants préfixés « paa- ») ──
  function injecter() {
    if (injecte) return;
    injecte = true;
    const optsFamille = ['<option value="">— Aucune —</option>']
      .concat(Object.keys(FAMILLES).map(f => `<option value="${esc(f)}">${esc(f)}</option>`))
      .join('');
    const wrap = document.createElement('div');
    wrap.innerHTML = `
  <div class="ach-modal" id="paa-modal-article" hidden>
    <div class="ach-modal-card">
      <header class="ach-modal-header">
        <h2 class="ach-modal-titre">Nouvel article</h2>
        <button type="button" class="ach-modal-fermer" id="paa-fermer" aria-label="Fermer">✕</button>
      </header>
      <form class="ach-form" id="paa-form" autocomplete="off">
        <div class="ach-champ ach-champ--full">
          <label>Fournisseur <span class="ach-req">*</span></label>
          <select id="paa-fournisseur" required></select>
          <span class="ach-hint" id="paa-fournisseur-hint" hidden>Fournisseur de la réception en cours</span>
        </div>
        <div class="ach-champ">
          <label>Code article <span class="ach-req">*</span></label>
          <input type="text" id="paa-code" required placeholder="Ex: BF-250G">
          <span class="ach-hint">Référence exacte du fournisseur</span>
        </div>
        <div class="ach-champ">
          <label>Désignation <span class="ach-req">*</span></label>
          <input type="text" id="paa-designation" required placeholder="Ex: Filet de boeuf 250g">
        </div>
        <div class="ach-champ">
          <label>Prix achat HT (€) <span class="ach-req">*</span></label>
          <input type="number" id="paa-prix" required min="0" step="0.01" placeholder="0.00" inputmode="decimal">
        </div>
        <div class="ach-champ">
          <label>Prix au <span class="ach-req">*</span></label>
          <select id="paa-format-prix">
            <option value="kg">€ / kg (prix au kilo)</option>
            <option value="colis">€ / colis (prix du colis entier)</option>
            <option value="piece">€ / pièce (prix d'une pièce)</option>
          </select>
        </div>
        <div class="ach-champ">
          <label>Qté par colis <span style="font-weight:400;color:#9ca3af;">(si prix au colis)</span></label>
          <input type="number" id="paa-qte-colis" min="0" step="1" placeholder="Ex : 10" inputmode="numeric">
        </div>
        <div class="ach-champ">
          <label>Poids unitaire (kg) <span style="font-weight:400;color:#9ca3af;">(1 pièce, ex : 0.185)</span></label>
          <input type="number" id="paa-poids-unitaire" min="0" step="0.001" placeholder="Ex : 0.185" inputmode="decimal">
        </div>
        <div class="ach-champ">
          <label>Poids total colis (kg)</label>
          <input type="text" id="paa-poids-colis" readonly placeholder="Calculé automatiquement"
                 style="background:#f3ebdf;color:#5a3e28;font-weight:600;cursor:not-allowed;">
        </div>
        <div class="ach-champ">
          <label>TVA (%)</label>
          <select id="paa-tva">
            <option value="5.5">5.5% (alimentaire)</option>
            <option value="10">10%</option>
            <option value="20">20%</option>
          </select>
        </div>
        <div class="ach-champ">
          <label>Unités de commande autorisées <span style="font-weight:400;color:#9ca3af;">(par le fournisseur)</span></label>
          <div class="ach-unites-check">
            <label><input type="checkbox" id="paa-unite-kg" value="kg"> kg</label>
            <label><input type="checkbox" id="paa-unite-piece" value="piece"> pièce</label>
            <label><input type="checkbox" id="paa-unite-colis" value="colis"> colis</label>
          </div>
        </div>
        <div class="ach-champ">
          <label>Famille</label>
          <select id="paa-famille">${optsFamille}</select>
        </div>
        <div class="ach-champ">
          <label>Sous-famille</label>
          <select id="paa-sous-famille" disabled>
            <option value="">— Choisir une famille d'abord —</option>
          </select>
        </div>
        <div class="ach-champ">
          <label>Type DLC</label>
          <select id="paa-dlc-type">
            <option value="dlc">DLC (date limite)</option>
            <option value="date_abattage">Date d'abattage (carcasses)</option>
            <option value="no_dlc">Sans DLC</option>
          </select>
        </div>
        <!-- Label Rouge, AOP… (plus dans la désignation) : core/mentions-etiquette.js -->
        <div class="ach-champ ach-champ--full" id="paa-mentions"></div>
        <div id="paa-erreur" class="ach-form-erreur" hidden></div>
        <div class="ach-modal-footer">
          <button type="button" class="ach-btn" id="paa-annuler">Annuler</button>
          <button type="submit" class="ach-btn ach-btn--primary" id="paa-sauver">Enregistrer</button>
        </div>
      </form>
    </div>
  </div>

  <div class="ach-modal" id="paa-modal-vente" hidden>
    <div class="ach-modal-card" style="max-width:560px;">
      <header class="ach-modal-header">
        <h2 class="ach-modal-titre">Suivre la marge de cet article ?</h2>
        <button type="button" class="ach-modal-fermer" id="paa-mvp-fermer" aria-label="Fermer">✕</button>
      </header>
      <div style="padding:var(--space-3);">
        <p style="margin:0 0 var(--space-3);color:#5a3e28;">
          ✅ Article créé : <strong id="paa-mvp-designation"></strong><br>
          <span style="color:#6b7280;font-size:var(--text-sm);">
            Le vends-tu au comptoir ? Relie-le à un produit de vente pour connaître ta marge brute.
          </span>
        </p>
        <div id="paa-mvp-choix" style="display:flex;flex-direction:column;gap:var(--space-2);">
          <button type="button" class="ach-btn ach-btn--primary" id="paa-mvp-btn-creer"
                  style="justify-content:flex-start;padding:var(--space-2) var(--space-3);">
            ➕ Créer un produit de vente et le lier
          </button>
          <button type="button" class="ach-btn" id="paa-mvp-btn-lier"
                  style="justify-content:flex-start;padding:var(--space-2) var(--space-3);">
            🔗 Lier à un produit de vente existant
          </button>
          <button type="button" class="ach-btn" id="paa-mvp-btn-ignorer"
                  style="justify-content:flex-start;padding:var(--space-2) var(--space-3);color:#6b7280;">
            Non merci, ignorer
          </button>
        </div>
        <div id="paa-mvp-lier" hidden>
          <label style="font-size:var(--text-sm);font-weight:600;color:#4b5563;">Rechercher le produit de vente</label>
          <input type="search" id="paa-mvp-lier-search" placeholder="Ex : Entrecôte, Saucisse…"
                 style="width:100%;min-height:44px;padding:.5rem .75rem;border:1px solid #d4c5af;border-radius:8px;font-size:1rem;margin:6px 0 10px;">
          <div id="paa-mvp-lier-resultats"
               style="max-height:280px;overflow:auto;display:flex;flex-direction:column;gap:6px;"></div>
          <div style="margin-top:var(--space-3);text-align:left;">
            <button type="button" class="ach-btn" id="paa-mvp-lier-retour">← Retour</button>
          </div>
        </div>
        <div id="paa-mvp-creer" hidden>
          <div class="ach-champ ach-champ--full">
            <label>Nom du produit de vente <span class="ach-req">*</span></label>
            <input type="text" id="paa-mvpc-nom" required>
          </div>
          <div class="ach-champ">
            <label>Prix de vente TTC (€)</label>
            <input type="number" id="paa-mvpc-prix" min="0" step="0.01" placeholder="0.00" inputmode="decimal">
            <div id="paa-mvpc-marge" style="margin-top:6px;font-size:var(--text-sm);font-weight:600;" hidden></div>
          </div>
          <div class="ach-champ">
            <label>Vendu au</label>
            <select id="paa-mvpc-unite">
              <option value="kg">€ / kg</option>
              <option value="piece">€ / pièce</option>
            </select>
          </div>
          <div class="ach-champ" id="paa-mvpc-zone-poids" hidden>
            <label>Poids d'une pièce (kg)</label>
            <input type="number" id="paa-mvpc-poids-piece" min="0" step="0.001" placeholder="Ex : 0.185" inputmode="decimal">
            <div id="paa-mvpc-poids-aide" style="margin-top:4px;font-size:var(--text-xs);color:#6b7280;" hidden></div>
          </div>
          <!-- Fait maison + mentions (AOP, Label Rouge…) : core/mentions-etiquette.js -->
          <div class="ach-champ ach-champ--full" id="paa-mvpc-etiquette"></div>
          <p style="font-size:var(--text-sm);color:#6b7280;margin:6px 0 0;">
            La famille <strong id="paa-mvpc-famille-lbl"></strong> et la sous-famille sont reprises de l'article.
          </p>
          <div style="margin-top:var(--space-3);display:flex;gap:var(--space-2);justify-content:space-between;">
            <button type="button" class="ach-btn" id="paa-mvp-creer-retour">← Retour</button>
            <button type="button" class="ach-btn ach-btn--primary" id="paa-mvp-creer-valider">Créer et lier</button>
          </div>
        </div>
        <div id="paa-mvp-succes" hidden style="text-align:center;">
          <div style="font-size:2rem;">✅</div>
          <p style="margin:8px 0;color:#2f7d3a;font-weight:600;">Article relié au suivi de marge</p>
          <div id="paa-mvp-succes-marge"
               style="background:#f3ebdf;border-radius:10px;padding:14px;margin:12px 0;color:#5a3e28;"></div>
          <button type="button" class="ach-btn ach-btn--primary" id="paa-mvp-succes-ok">Terminé</button>
        </div>
        <div id="paa-mvp-erreur" class="ach-form-erreur" hidden style="margin-top:var(--space-3);"></div>
      </div>
    </div>
  </div>`;
    while (wrap.firstElementChild) document.body.appendChild(wrap.firstElementChild);
    brancher();
  }

  function brancher() {
    $('paa-fermer').addEventListener('click', fermerArticle);
    $('paa-annuler').addEventListener('click', fermerArticle);
    $('paa-form').addEventListener('submit', sauver);
    $('paa-qte-colis').addEventListener('input', recalcPoidsColis);
    $('paa-poids-unitaire').addEventListener('input', recalcPoidsColis);
    $('paa-famille').addEventListener('change', () => majSousFamilleForm(''));

    $('paa-mvp-fermer').addEventListener('click', fermerVente);
    $('paa-mvp-btn-ignorer').addEventListener('click', fermerVente);
    $('paa-mvp-succes-ok').addEventListener('click', fermerVente);
    $('paa-mvp-btn-lier').addEventListener('click', ecranLier);
    $('paa-mvp-btn-creer').addEventListener('click', ecranCreer);
    $('paa-mvp-lier-retour').addEventListener('click', () => montrerEcran('choix'));
    $('paa-mvp-creer-retour').addEventListener('click', () => montrerEcran('choix'));
    $('paa-mvp-lier-search').addEventListener('input', e => {
      clearTimeout(rechercheTimer);
      const q = e.target.value.trim();
      rechercheTimer = setTimeout(() => rechercherVentes(q), 250);
    });
    $('paa-mvp-lier-resultats').addEventListener('click', e => {
      const btn = e.target.closest('button[data-vid]');
      if (btn) lierAuProduit(btn.dataset.vid, btn.dataset.gid || null);
    });
    $('paa-mvp-creer-valider').addEventListener('click', validerCreationVente);
    $('paa-mvpc-unite').addEventListener('change', e => {
      const piece = e.target.value === 'piece';
      $('paa-mvpc-zone-poids').hidden = !piece;
      if (piece) preremplirPoids();
      majMarge();
    });
    $('paa-mvpc-prix').addEventListener('input', majMarge);
    $('paa-mvpc-poids-piece').addEventListener('input', majMarge);
  }

  // ── Formulaire article ───────────────────────────────────────────────────
  async function chargerFournisseurs() {
    if (fournisseurs) return fournisseurs;
    try {
      const r = await fetch(API_FOURN);
      fournisseurs = r.ok ? await r.json() : [];
    } catch (_) {
      fournisseurs = [];
    }
    return fournisseurs;
  }

  function majSousFamilleForm(valeur) {
    majSousFamille($('paa-famille').value, $('paa-sous-famille'), valeur || '');
  }

  function setUnitesForm(csv) {
    const liste = (csv && csv.trim()) ? csv.split(',').map(s => s.trim()) : ['kg', 'piece', 'colis'];
    for (const [u, id] of Object.entries(UNITES_IDS)) $(id).checked = liste.includes(u);
  }

  function getUnitesForm() {
    const sel = Object.entries(UNITES_IDS).filter(([, id]) => $(id).checked).map(([u]) => u);
    return (sel.length ? sel : ['kg', 'piece', 'colis']).join(',');
  }

  function recalcPoidsColis() {
    const qte = parseFloat($('paa-qte-colis').value);
    const poids = parseFloat($('paa-poids-unitaire').value);
    $('paa-poids-colis').value = (qte > 0 && poids > 0) ? (Math.round(qte * poids * 1000) / 1000) + ' kg' : '';
  }

  // Mêmes garde-fous non bloquants que le catalogue achats.
  function detecterAnomaliesSaisie(b) {
    const warns = [];
    const prix = b.prix_achat_ht, pu = b.poids_unitaire_kg, qte = b.qte_par_colis;
    if (pu != null && pu > 5) {
      warns.push(`Poids unitaire de ${pu} kg : est-ce bien le poids d'UNE pièce ? (semble élevé)`);
    }
    if (b.format_prix === 'colis' && !qte) {
      warns.push("Format « colis » sans quantité par colis : le prix à la pièce ne pourra pas être calculé.");
    }
    if (b.format_prix === 'piece' && !pu) {
      warns.push("Format « pièce » sans poids unitaire : le prix au kg ne pourra pas être calculé.");
    }
    let prixKg = null;
    if (prix != null) {
      if (b.format_prix === 'kg') prixKg = prix;
      else if (b.format_prix === 'piece' && pu) prixKg = prix / pu;
      else if (b.format_prix === 'colis' && pu && qte) prixKg = prix / (pu * qte);
    }
    if (prixKg != null && prixKg > 0 && prixKg < 0.5) {
      warns.push(`Prix au kilo dérivé très bas (${prixKg.toFixed(2)} €/kg) : vérifiez le format et le prix.`);
    }
    if (prixKg != null && prixKg > 200) {
      warns.push(`Prix au kilo dérivé très élevé (${prixKg.toFixed(0)} €/kg) : vérifiez le format et le prix.`);
    }
    return warns;
  }

  let mentionsArticle = null;   // mentions de l'article (Label Rouge, AOP…), sans « Fait maison »

  async function ouvrir(opts = {}) {
    options = opts;
    injecter();
    const liste = await chargerFournisseurs();
    const sel = $('paa-fournisseur');
    sel.innerHTML = '<option value="">— Choisir —</option>'
      + liste.map(f => `<option value="${f.id}">${esc(f.nom)}</option>`).join('');
    // Fournisseur de la réception : retrouvé par id, sinon par nom ; imposé s'il est trouvé.
    let fid = opts.fournisseurId || null;
    if (!fid && opts.fournisseurNom) {
      const n = opts.fournisseurNom.trim().toLowerCase();
      fid = (liste.find(f => (f.nom || '').trim().toLowerCase() === n) || {}).id || null;
    }
    sel.value = fid ? String(fid) : '';
    sel.disabled = !!(fid && sel.value);
    $('paa-fournisseur-hint').hidden = !sel.disabled;

    ['paa-code', 'paa-designation', 'paa-prix', 'paa-qte-colis', 'paa-poids-unitaire', 'paa-poids-colis']
      .forEach(id => { $(id).value = ''; });
    $('paa-code').value = opts.codeArticle || '';
    $('paa-designation').value = opts.designation || '';
    $('paa-format-prix').value = 'kg';
    $('paa-tva').value = '5.5';
    setUnitesForm(null);
    $('paa-famille').value = '';
    majSousFamilleForm('');
    $('paa-dlc-type').value = 'dlc';
    mentionsArticle = mentionsArticle || MentionsEtiquette.monter($('paa-mentions'), { faitMaison: false });
    mentionsArticle.ecrire({ mentions: [] });
    $('paa-erreur').hidden = true;
    $('paa-modal-article').hidden = false;
    (opts.codeArticle ? $('paa-designation') : $('paa-code')).focus();
  }

  function fermerArticle() {
    $('paa-modal-article').hidden = true;
  }

  async function sauver(e) {
    e.preventDefault();
    const body = {
      fournisseur_id:    parseInt($('paa-fournisseur').value),
      code_article:      $('paa-code').value.trim(),
      designation:       $('paa-designation').value.trim(),
      prix_achat_ht:     parseFloat($('paa-prix').value),
      format_prix:       $('paa-format-prix').value,
      qte_par_colis:     parseFloat($('paa-qte-colis').value) || null,
      poids_unitaire_kg: parseFloat($('paa-poids-unitaire').value) || null,
      tva_percent:       parseFloat($('paa-tva').value),
      unites_autorisees: getUnitesForm(),
      famille:           $('paa-famille').value || null,
      sous_famille:      $('paa-sous-famille').value || null,
      dlc_type:          $('paa-dlc-type').value,
      mentions:          mentionsArticle ? mentionsArticle.lire().mentions : [],
    };
    const zErr = $('paa-erreur');
    if (!body.fournisseur_id) {
      zErr.textContent = 'Choisissez le fournisseur.'; zErr.hidden = false; return;
    }
    const anomalies = detecterAnomaliesSaisie(body);
    if (anomalies.length && !confirm('⚠ Vérification :\n\n• ' + anomalies.join('\n• ') + '\n\nEnregistrer quand même ?')) {
      return;
    }
    const btn = $('paa-sauver');
    btn.disabled = true; btn.textContent = 'Enregistrement…';
    try {
      const r = await fetch(API_CAT, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(await lireErreur(r, "Création de l'article impossible"));
      const cree = await r.json();
      const f = (fournisseurs || []).find(x => x.id === cree.fournisseur_id);
      if (f && !cree.fournisseur_nom) cree.fournisseur_nom = f.nom;
      fermerArticle();
      if (typeof options.onCree === 'function') {
        try { options.onCree(cree); } catch (err) { console.error('[haccp] onCree :', err); }
      }
      if (FAMILLES_VENDABLES.has(cree.famille)) ouvrirVente(cree);
    } catch (err) {
      zErr.textContent = err.message; zErr.hidden = false;
    } finally {
      btn.disabled = false; btn.textContent = 'Enregistrer';
    }
  }

  // ── « Suivre la marge de cet article ? » ─────────────────────────────────
  function ouvrirVente(a) {
    article = a;
    $('paa-mvp-designation').textContent = a.designation || '(sans nom)';
    montrerEcran('choix');
    $('paa-modal-vente').hidden = false;
  }

  function fermerVente() {
    $('paa-modal-vente').hidden = true;
    article = null;
  }

  function montrerEcran(ecran) {
    $('paa-mvp-choix').hidden  = ecran !== 'choix';
    $('paa-mvp-lier').hidden   = ecran !== 'lier';
    $('paa-mvp-creer').hidden  = ecran !== 'creer';
    $('paa-mvp-succes').hidden = ecran !== 'succes';
    $('paa-mvp-erreur').hidden = true;
  }

  function erreurVente(msg) {
    const z = $('paa-mvp-erreur');
    z.textContent = msg; z.hidden = false;
  }

  function ecranLier() {
    montrerEcran('lier');
    const input = $('paa-mvp-lier-search');
    input.value = '';
    $('paa-mvp-lier-resultats').innerHTML =
      '<p style="color:#9ca3af;font-size:var(--text-sm);">Tapez pour rechercher…</p>';
    const pref = (article?.designation || '').trim();
    if (pref) { input.value = pref; rechercherVentes(pref); }
    input.focus();
  }

  async function rechercherVentes(q) {
    const zone = $('paa-mvp-lier-resultats');
    try {
      const r = await fetch(`/api/achats/comparatif/recherche-ventes?q=${encodeURIComponent(q)}`);
      if (!r.ok) throw new Error(await lireErreur(r, 'Recherche impossible'));
      const produits = (await r.json()).produits || [];
      if (!produits.length) {
        zone.innerHTML = '<p style="color:#9ca3af;font-size:var(--text-sm);">Aucun produit de vente trouvé.</p>';
        return;
      }
      zone.innerHTML = produits.map(p => {
        const relie = p.groupe_id
          ? `<span class="ach-badge ach-badge--dlc" style="margin-left:6px;">groupe : ${esc(p.groupe_nom)}</span>`
          : '<span class="ach-badge ach-badge--no-dlc" style="margin-left:6px;">sans suivi</span>';
        const prix = p.prix_vente_ttc != null
          ? `${fmtPrix(p.prix_vente_ttc)} € TTC/${p.unite_vente === 'piece' ? 'pièce' : 'kg'}`
          : 'prix non renseigné';
        return `
          <button type="button" class="ach-btn" data-vid="${p.id}" data-gid="${p.groupe_id || ''}"
                  style="justify-content:space-between;text-align:left;padding:10px 12px;width:100%;">
            <span>
              <strong>${esc(p.nom)}</strong>${relie}<br>
              <span style="color:#6b7280;font-size:var(--text-xs);">${esc(p.famille || '')}${p.sous_famille ? ' · ' + esc(p.sous_famille) : ''} — ${prix}</span>
            </span>
          </button>`;
      }).join('');
    } catch (e) {
      zone.innerHTML = `<p style="color:#c1452c;font-size:var(--text-sm);">${esc(e.message)}</p>`;
    }
  }

  // Groupe préexistant : on ne touche pas à la ligne de référence choisie par
  // l'utilisateur ; sur un groupe neuf, cet achat devient la référence de marge.
  async function lierAuProduit(venteId, groupeId) {
    const articleId = article?.id;
    if (!articleId) return;
    const groupeNouveau = !groupeId;
    try {
      if (!groupeId) {
        const rg = await fetch('/api/achats/comparatif/groupes/from-vente', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ catalogue_vente_id: Number(venteId) }),
        });
        if (!rg.ok) throw new Error(await lireErreur(rg, 'Création du groupe impossible'));
        groupeId = (await rg.json()).id;
      }
      const rl = await fetch(`/api/achats/comparatif/groupes/${groupeId}/lignes`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ catalogue_fournisseur_id: Number(articleId) }),
      });
      if (!rl.ok) throw new Error(await lireErreur(rl, 'Liaison impossible'));

      let detail = null;
      try {
        if (groupeNouveau) {
          const rr = await fetch(`/api/achats/comparatif/groupes/${groupeId}/ventes/${venteId}/reference`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ligne_choisie_id: Number(articleId) }),
          });
          if (rr.ok) detail = await rr.json();
        } else {
          const rd = await fetch(`/api/achats/comparatif/groupes/${groupeId}`);
          if (rd.ok) detail = await rd.json();
        }
      } catch (_) { /* marge = bonus */ }
      const pv = detail ? (detail.produits_vente || []).find(p => p.id === Number(venteId)) : null;
      afficherSucces(pv?.marge || null);
    } catch (e) {
      erreurVente('Erreur : ' + e.message);
    }
  }

  function afficherSucces(marge) {
    const zone = $('paa-mvp-succes-marge');
    if (marge && marge.marge != null) {
      const taux = marge.taux_marge != null ? ` (${(marge.taux_marge * 100).toFixed(0)} %)` : '';
      const u = marge.unite === 'piece' ? 'pièce' : 'kg';
      zone.innerHTML = `
        Marge brute : <strong style="color:#2f7d3a;">${fmtPrix(marge.marge)} € / ${u}${taux}</strong><br>
        <span style="font-size:var(--text-sm);color:#6b7280;">
          Vente HT ${fmtPrix(marge.prix_vente_ht)} € − coût matière ${fmtPrix(marge.cout_matiere)} €
        </span>`;
    } else {
      zone.innerHTML = `<span style="color:#6b7280;">
        Marge non calculable pour l'instant : complétez le prix de vente et le poids/prix d'achat.
      </span>`;
    }
    montrerEcran('succes');
  }

  // kg→kg, pièce→pièce, colis→pièce (un colis se revend à l'unité).
  function uniteVenteParDefaut(formatAchat) {
    return (formatAchat === 'piece' || formatAchat === 'colis') ? 'piece' : 'kg';
  }

  let etiquette = null;      // bloc « Fait maison + mentions », monté au premier affichage

  function ecranCreer() {
    const a = article;
    if (!a) return;
    montrerEcran('creer');
    etiquette = etiquette || MentionsEtiquette.monter($('paa-mvpc-etiquette'));
    etiquette.ecrire({ fait_maison: false, mentions: a.mentions || [] });   // labels de l'achat
    $('paa-mvpc-nom').value = a.designation || '';
    $('paa-mvpc-prix').value = '';
    const unite = uniteVenteParDefaut(a.format_prix);
    $('paa-mvpc-unite').value = unite;
    $('paa-mvpc-poids-piece').value = '';
    $('paa-mvpc-zone-poids').hidden = unite !== 'piece';
    $('paa-mvpc-marge').hidden = true;
    $('paa-mvpc-poids-aide').hidden = true;
    if (unite === 'piece') preremplirPoids();
    $('paa-mvpc-famille-lbl').textContent = a.famille || '—';
    $('paa-mvpc-nom').focus();
  }

  function preremplirPoids() {
    const a = article;
    const champ = $('paa-mvpc-poids-piece');
    const aide = $('paa-mvpc-poids-aide');
    const defaut = a && a.poids_unitaire_kg != null ? Number(a.poids_unitaire_kg) : null;
    if (defaut != null && defaut > 0 && !champ.value) champ.value = defaut;
    if (a && a.prix_piece != null) {
      aide.innerHTML = `Coût d'achat : <strong>${fmtPrix(a.prix_piece)} € la pièce</strong>. `
        + `Le poids ne sert qu'aux étiquettes.`;
    } else if (defaut != null && defaut > 0) {
      aide.textContent = `Poids repris de l'achat : ${defaut} kg (modifiable) — sert au calcul de la marge.`;
    } else {
      aide.textContent = "Pas de poids sur l'article d'achat — saisissez-le pour calculer la marge.";
    }
    aide.hidden = false;
  }

  // Miroir de _calc_marge (backend) — base HT, TVA de l'article d'achat.
  function calcMarge() {
    const a = article;
    if (!a) return { motif: 'pas_article' };
    const ttc = parseFloat($('paa-mvpc-prix').value);
    if (isNaN(ttc) || !(ttc > 0)) return { motif: 'pas_prix' };
    const tva = a.tva_percent != null ? Number(a.tva_percent) : 5.5;
    const venteHt = ttc / (1 + tva / 100);
    const unite = $('paa-mvpc-unite').value;
    const achatKg = a.prix_kg != null ? Number(a.prix_kg) : null;
    const achatPiece = a.prix_piece != null ? Number(a.prix_piece) : null;
    let cout, u, venteKg = null, achatKgEquiv = null;
    if (unite === 'piece') {
      const poids = parseFloat($('paa-mvpc-poids-piece').value);
      if (achatKg != null && poids > 0) cout = achatKg * poids;
      else if (achatPiece != null) cout = achatPiece;
      else return { motif: 'pas_cout_piece' };
      u = 'pièce';
      if (poids > 0) {
        venteKg = venteHt / poids;
        achatKgEquiv = achatKg != null ? achatKg : (cout / poids);
      }
    } else {
      if (achatKg == null) return { motif: 'pas_kg' };
      cout = achatKg;
      u = 'kg';
    }
    const marge = venteHt - cout;
    return {
      marge, unite: u, cout, venteKg, achatKgEquiv,
      taux: venteHt > 0 ? marge / venteHt : null,
      coef: cout > 0 ? venteHt / cout : null,
    };
  }

  function majMarge() {
    const zone = $('paa-mvpc-marge');
    const m = calcMarge();
    if (m.motif) {
      const ttc = parseFloat($('paa-mvpc-prix').value);
      if (article && ttc > 0 && (m.motif === 'pas_kg' || m.motif === 'pas_cout_piece')) {
        zone.innerHTML = '<span style="color:#9ca3af;">Coût d\'achat indisponible — marge non calculable.</span>';
        zone.hidden = false;
      } else {
        zone.hidden = true;
      }
      return;
    }
    const taux = m.taux != null ? ` · ${(m.taux * 100).toFixed(0)} %` : '';
    const coef = m.coef != null ? ` · coef ${m.coef.toFixed(2)}` : '';
    const col = m.marge >= 0 ? '#2f7d3a' : '#c1452c';
    const equiv = (m.unite === 'pièce' && m.venteKg != null && m.achatKgEquiv != null)
      ? `<div style="color:#6b7280;font-weight:400;font-size:var(--text-xs);margin-top:2px;">
           ≈ vendu ${fmtPrix(m.venteKg)} €/kg HT · acheté ${fmtPrix(m.achatKgEquiv)} €/kg
         </div>`
      : '';
    zone.innerHTML =
        `<span style="color:${col};">Marge : ${fmtPrix(m.marge)} € / ${m.unite}${taux}</span>`
      + `<span style="color:#6b7280;font-weight:400;">${coef} · achat ${fmtPrix(m.cout)} €/${m.unite} HT</span>`
      + equiv;
    zone.hidden = false;
  }

  async function validerCreationVente() {
    const a = article;
    if (!a) return;
    const nom = $('paa-mvpc-nom').value.trim();
    if (!nom) { erreurVente('Le nom du produit de vente est obligatoire.'); return; }
    const unite = $('paa-mvpc-unite').value;
    const prix = parseFloat($('paa-mvpc-prix').value);
    const poids = parseFloat($('paa-mvpc-poids-piece').value);
    const btn = $('paa-mvp-creer-valider');
    btn.disabled = true; btn.textContent = 'Création…';
    try {
      const rv = await fetch('/api/vente/catalogue', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nom,
          prix_vente_ttc: isNaN(prix) ? null : prix,
          unite_vente: unite,
          poids_piece_kg: (unite === 'piece' && !isNaN(poids)) ? poids : null,
          famille: a.famille || null,
          sous_famille: a.sous_famille || null,
          ...(etiquette ? etiquette.lire() : {}),   // fait_maison + mentions
        }),
      });
      if (!rv.ok) throw new Error(await lireErreur(rv, 'Création du produit impossible'));
      const vente = await rv.json();
      await lierAuProduit(vente.id, null);
    } catch (e) {
      erreurVente('Erreur : ' + e.message);
    } finally {
      btn.disabled = false; btn.textContent = 'Créer et lier';
    }
  }

  window.PopupArticleAchat = { ouvrir };
})();

'use strict';
/* ============================================================
   prix_etiquettes_imprimer.js — Vue « Imprimer » (écran de tous les jours)

   En haut : les étiquettes à refaire (prix changés) → « Tout ajouter ».
   À gauche : le catalogue de vente (recherche, familles, bouton +).
   À droite : la liste à imprimer (quantités −/+), l'aperçu réel de
   l'étiquette (style normal + produit), un seul gros bouton Imprimer.

   Dépend de prix_etiquettes.js (chargé avant) : apiFetch, escHtml, state,
   chargerFile, dessinerEtiquette, imprimerSerieNavigateur, proposerSortieFile,
   afficherOnglet, peVues.
   ============================================================ */

(function () {
  const $ = id => document.getElementById(id);
  const CLE_PANIER = 'pe_panier';

  const imp = {
    produits: [],          // catalogue de vente actif (prix ACTUELS)
    familles: [],
    famille: '',
    recherche: '',
    panier: new Map(),     // produit_id → quantité (ordre d'ajout conservé)
    selection: null,       // produit affiché dans l'aperçu
    style: null,           // config du style « normal »
    stylePromo: null,      // config du style « promo » (produits en promo)
  };

  // Un produit en promo s'imprime avec le style promo, sinon avec le style normal.
  const styleDe = p => (p?.promo ? imp.stylePromo : imp.style);
  const dateCourte = iso => (iso ? iso.slice(8, 10) + '/' + iso.slice(5, 7) : '');

  // ── Outils ─────────────────────────────────────────────────
  const prixTexte = v => (v == null ? '—' : parseFloat(v).toFixed(2).replace('.', ',') + ' €');
  const uniteTexte = p => (String(p.unite_vente || 'kg').toLowerCase() === 'piece' ? 'pièce' : 'kg');
  // Recherche insensible aux accents et à la casse (« boeuf » trouve « bœuf »).
  const plat = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/œ/g, 'oe').replace(/æ/g, 'ae').toLowerCase();
  const produit = id => imp.produits.find(p => p.id === id);

  function sauverPanier() {
    try { localStorage.setItem(CLE_PANIER, JSON.stringify([...imp.panier])); } catch (e) { /* ignore */ }
  }
  function lirePanier() {
    try { return new Map(JSON.parse(localStorage.getItem(CLE_PANIER) || '[]')); } catch (e) { return new Map(); }
  }

  function statut(msg, type) {
    const el = $('imp-statut');
    el.textContent = msg;
    el.className = `pe-print-status pe-print-status--${type}`;
    el.hidden = false;
    if (type === 'ok') setTimeout(() => { el.hidden = true; }, 5000);
  }

  // ── Panier ─────────────────────────────────────────────────
  function ajouter(id, n = 1) {
    const p = produit(id);
    if (!p || p.prix_vente_ttc == null) return;
    imp.panier.set(id, Math.min(99, (imp.panier.get(id) || 0) + n));
    imp.selection = id;
    sauverPanier();
    rendre();
  }

  function changerQuantite(id, delta) {
    const q = (imp.panier.get(id) || 0) + delta;
    if (q <= 0) imp.panier.delete(id); else imp.panier.set(id, Math.min(99, q));
    if (!imp.panier.has(imp.selection)) imp.selection = imp.panier.keys().next().value ?? null;
    sauverPanier();
    rendre();
  }

  // ── Rendu ──────────────────────────────────────────────────
  function rendreFile() {
    const bloc = $('imp-file');
    const n = state.file.size;
    bloc.hidden = n === 0;
    if (!n) return;
    $('imp-file-titre').textContent =
      `🏷️ ${n} étiquette${n > 1 ? 's' : ''} à refaire — prix changé${n > 1 ? 's' : ''}`;
    $('imp-file-liste').innerHTML = [...state.file.values()].map(e => {
      const dans = imp.panier.has(e.catalogue_vente_id);
      const avant = e.prix_ancien_ttc != null ? `${prixTexte(e.prix_ancien_ttc)} → ` : 'nouveau · ';
      return `<button class="pe-imp-chip ${dans ? 'pe-imp-chip--ajoute' : ''}" data-id="${e.catalogue_vente_id}">
                <strong>${dans ? '✓ ' : '+ '}${escHtml(e.nom)}</strong>
                <span>${avant}${prixTexte(e.prix_actuel_ttc)}</span></button>`;
    }).join('');
    $('imp-file-liste').querySelectorAll('[data-id]').forEach(b =>
      b.addEventListener('click', () => {
        const id = +b.dataset.id;
        if (!imp.panier.has(id)) ajouter(id); else { imp.selection = id; rendre(); }
      }));
  }

  function rendreFamilles() {
    const el = $('imp-familles');
    el.innerHTML = [''].concat(imp.familles).map(f =>
      `<button class="pe-imp-famille ${f === imp.famille ? 'active' : ''}" data-famille="${escHtml(f)}">`
      + `${f ? escHtml(f) : 'Tous'}</button>`).join('');
    el.querySelectorAll('[data-famille]').forEach(b => b.addEventListener('click', () => {
      imp.famille = b.dataset.famille;
      rendreFamilles();
      rendreProduits();
    }));
  }

  function rendreProduits() {
    const q = plat(imp.recherche.trim());
    const liste = imp.produits
      .filter(p => (!imp.famille || p.famille === imp.famille) && (!q || plat(p.nom).includes(q)))
      .sort((a, b) => String(a.nom).localeCompare(String(b.nom), 'fr'));
    const el = $('imp-produits');
    if (!liste.length) {
      el.innerHTML = '<div class="pe-imp-vide">Aucun produit.</div>';
      return;
    }
    el.innerHTML = liste.map(p => {
      const q = imp.panier.get(p.id);
      const sansPrix = p.prix_vente_ttc == null;
      const aRefaire = state.file.has(p.id) ? '<span class="pe-tag-file">🏷️ à refaire</span>' : '';
      const enPromo = p.promo
        ? `<span class="pe-tag-promo">🔥 ${prixTexte(p.promo.prix_promo_ttc)} jusqu'au ${dateCourte(p.promo.date_fin)}</span>` : '';
      return `<div class="pe-imp-produit">
          <div class="pe-imp-produit-nom">${escHtml(p.nom)}${aRefaire}${enPromo}</div>
          <div class="pe-imp-produit-prix">${sansPrix ? 'pas de prix' : `${prixTexte(p.prix_vente_ttc)} / ${uniteTexte(p)}`}</div>
          <button class="pe-imp-promo-btn ${p.promo ? 'active' : ''}" data-promo="${p.id}"
                  ${sansPrix ? 'disabled' : ''} title="Mettre en promo" aria-label="Promo ${escHtml(p.nom)}">🔥</button>
          <button class="pe-imp-plus ${q ? 'pe-imp-plus--ajoute' : ''}" data-id="${p.id}"
                  ${sansPrix ? 'disabled title="Renseignez d\'abord son prix dans le catalogue de vente"' : ''}
                  aria-label="Ajouter ${escHtml(p.nom)}">${q ? `✓ ${q}` : '+'}</button>
        </div>`;
    }).join('');
    el.querySelectorAll('[data-id]').forEach(b => b.addEventListener('click', () => ajouter(+b.dataset.id)));
    el.querySelectorAll('[data-promo]').forEach(b => b.addEventListener('click', () => ouvrirPromo(+b.dataset.promo)));
  }

  // Bandeau des promos en cours (arrêt possible avant la date de fin).
  function rendrePromos() {
    const enPromo = imp.produits.filter(p => p.promo)
      .sort((a, b) => String(a.promo.date_fin).localeCompare(String(b.promo.date_fin)));
    $('imp-promos').hidden = enPromo.length === 0;
    if (!enPromo.length) return;
    $('imp-promos-titre').textContent =
      `🔥 ${enPromo.length} promo${enPromo.length > 1 ? 's' : ''} en cours`;
    $('imp-promos-liste').innerHTML = enPromo.map(p =>
      `<button class="pe-imp-chip pe-imp-chip--promo" data-promo="${p.id}">
         <strong>${escHtml(p.nom)}</strong>
         <span>${prixTexte(p.promo.prix_promo_ttc)} · jusqu'au ${dateCourte(p.promo.date_fin)}</span></button>`
    ).join('');
    $('imp-promos-liste').querySelectorAll('[data-promo]').forEach(b =>
      b.addEventListener('click', () => ouvrirPromo(+b.dataset.promo)));
  }

  function rendrePanier() {
    const el = $('imp-panier');
    const lignes = [...imp.panier].filter(([id]) => produit(id));
    $('imp-vider').hidden = lignes.length === 0;
    if (!lignes.length) {
      el.innerHTML = '<div class="pe-imp-vide">Touchez <strong>+</strong> sur un produit pour l\'ajouter.</div>';
    } else {
      el.innerHTML = lignes.map(([id, q]) => {
        const p = produit(id);
        return `<div class="pe-imp-ligne ${id === imp.selection ? 'active' : ''}" data-id="${id}">
            <button class="pe-imp-ligne-nom" data-voir="${id}">${escHtml(p.nom)}
              <span>${p.promo
                ? `🔥 promo ${prixTexte(p.promo.prix_promo_ttc)} (au lieu de ${prixTexte(p.promo.prix_reference_ttc)})`
                : `${prixTexte(p.prix_vente_ttc)} / ${uniteTexte(p)}`}</span></button>
            <div class="pe-imp-qte">
              <button class="pe-icone-btn" data-moins="${id}" aria-label="Moins">−</button>
              <span class="pe-imp-qte-val">${q}</span>
              <button class="pe-icone-btn" data-plus="${id}" aria-label="Plus">+</button>
            </div>
          </div>`;
      }).join('');
      el.querySelectorAll('[data-voir]').forEach(b => b.addEventListener('click', () => {
        imp.selection = +b.dataset.voir; rendrePanier(); rendreApercu();
      }));
      el.querySelectorAll('[data-moins]').forEach(b => b.addEventListener('click', () => changerQuantite(+b.dataset.moins, -1)));
      el.querySelectorAll('[data-plus]').forEach(b => b.addEventListener('click', () => changerQuantite(+b.dataset.plus, 1)));
    }
    const total = lignes.reduce((s, [, q]) => s + q, 0);
    const btn = $('imp-imprimer');
    btn.disabled = total === 0 || !imp.style;
    btn.textContent = total ? `🖨️ Imprimer ${total} étiquette${total > 1 ? 's' : ''}` : '🖨️ Imprimer';
    $('imp-navigateur').hidden = total === 0 || !imp.style;
  }

  function rendreApercu() {
    if (!imp.style) return;
    const p = produit(imp.selection) || produit(imp.panier.keys().next().value)
      || produit([...state.file.keys()][0]) || imp.produits.find(x => x.prix_vente_ttc != null);
    dessinerEtiquette({ canvas: $('imp-canvas'), cadre: $('imp-cadre'), maxW: 400, maxH: 160 },
                      styleDe(p) || imp.style, p || null);
  }

  function rendre() {
    rendreFile();
    rendrePromos();
    rendreProduits();
    rendrePanier();
    rendreApercu();
  }

  // ── Chargement (à chaque affichage : prix et file à jour) ──
  async function charger() {
    const [cat, fam, styles] = await Promise.all([
      apiFetch('/api/prix-etiquettes/catalogue?limit=2000'),
      apiFetch('/api/prix-etiquettes/catalogue/familles'),
      apiFetch('/api/prix-etiquettes/styles'),
      chargerFile(),
    ]);
    imp.produits = cat.articles ?? [];
    imp.familles = fam.familles ?? [];
    imp.style = styles.normal?.config ?? null;
    imp.stylePromo = styles.promo?.config ?? null;
    // Produits retirés du catalogue entre-temps : hors de la liste.
    [...imp.panier.keys()].forEach(id => { if (!produit(id)) imp.panier.delete(id); });
    if (!imp.style) {
      statut('Aucun style d\'étiquette : créez-le d\'abord dans l\'onglet « 🎨 Style des étiquettes ».', 'err');
    }
    rendreFamilles();
    rendre();
  }

  // ── Impression ─────────────────────────────────────────────
  function lignesPanier() {
    return [...imp.panier].filter(([id]) => produit(id))
      .map(([produit_id, quantite]) => ({ produit_id, quantite }));
  }

  // Lignes du panier regroupées par style : [{ config, produits }] (normal, puis promo).
  function seriesParStyle() {
    const normal = [], promo = [];
    lignesPanier().forEach(l => (produit(l.produit_id).promo ? promo : normal).push(l));
    return [{ config: imp.style, produits: normal }, { config: imp.stylePromo, produits: promo }]
      .filter(s => s.produits.length && s.config);
  }

  $('imp-imprimer').addEventListener('click', async () => {
    const series = seriesParStyle();
    if (!series.length) return;
    const btn = $('imp-imprimer');
    btn.disabled = true;
    statut('Envoi à l\'imprimante…', 'loading');
    let total = 0;
    const erreurs = [];
    for (const { config, produits } of series) {
      try {
        const res = await apiFetch('/api/prix-etiquettes/imprimer-masse', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ config, produits }),
        });
        // Comme le serveur : un produit est parti si TOUS ses exemplaires sont partis.
        let reste = res.imprimees;
        produits.forEach(l => {
          if (reste >= l.quantite) imp.panier.delete(l.produit_id);
          reste -= l.quantite;
        });
        total += res.imprimees;
        if (res.erreurs?.length) { erreurs.push(res.erreurs[0]); break; }
      } catch (e) {
        erreurs.push(e.message);
        break;                       // imprimante injoignable : inutile d'insister
      }
    }
    imp.selection = null;
    sauverPanier();
    if (erreurs.length) {
      statut(`${total} imprimée(s) — Erreur impression : ${erreurs[0]}`, 'err');
    } else {
      statut(`✓ ${total} étiquette${total > 1 ? 's' : ''} imprimée${total > 1 ? 's' : ''}.`, 'ok');
    }
    await chargerFile();
    rendre();
  });

  $('imp-navigateur').addEventListener('click', async () => {
    const series = seriesParStyle();
    if (!series.length) return;
    statut('Préparation des étiquettes…', 'loading');
    try {
      let n = 0;
      for (const { config, produits } of series) {
        n += await imprimerSerieNavigateur(config, produits);
        noterImpressionNavigateur({ type: config.type || 'normal', produits });
      }
      statut(`Aperçu de ${n} étiquette(s) ouvert — choisissez l'imprimante.`, 'ok');
      await proposerSortieFile(lignesPanier().map(p => p.produit_id));
      rendre();
    } catch (e) {
      statut(e.message, 'err');
    }
  });

  // ── Fenêtre « Mettre en promo » ────────────────────────────
  const promoVue = { produit: null, reference: null, promoId: null, marge: null };

  // Seuil sous lequel la marge d'une promo est signalée comme faible.
  const MARGE_FAIBLE = 0.15;

  // Taux de marque (0..1) d'un prix TTC — même calcul que le serveur (sur HT).
  function tauxMarque(prixTtc, tva, cout) {
    const ht = prixTtc / (1 + (tva || 0) / 100);
    return ht > 0 ? (ht - cout) / ht : null;
  }
  const pct = t => `${Math.round(t * 100)} %`;

  // Indicateur de marge : aujourd'hui → avec la promo, coût d'achat, lien comparateur.
  function promoMarge() {
    const el = $('promo-marge');
    const m = promoVue.marge;
    const p = promoVue.produit;
    if (!m || !p) { el.hidden = true; return; }
    const lien = m.groupe_id
      ? ` · <a href="/comparatif-achats.html?groupe=${m.groupe_id}">Voir dans le comparateur ›</a>` : '';
    el.hidden = false;
    if (m.cout_ht == null) {
      el.className = 'pe-promo-marge';
      el.innerHTML = `📊 Marge inconnue : ce produit n'est relié à aucun prix d'achat de référence.${lien}`;
      return;
    }
    const prix = parseFloat($('promo-prix').value);
    const avec = isNaN(prix) ? null : tauxMarque(prix, m.tva_percent, m.cout_ht);
    let niveau = 'ok', alerte = '';
    if (avec != null && avec < 0) {
      niveau = 'perte';
      alerte = '<br>⚠️ <strong>Vente à perte</strong> : le prix promo est sous le coût d\'achat.';
    } else if (avec != null && avec < MARGE_FAIBLE) {
      niveau = 'faible';
    }
    el.className = `pe-promo-marge pe-promo-marge--${niveau}`;
    el.innerHTML = `📊 Marge : <strong>${m.taux_actuel != null ? pct(m.taux_actuel) : '—'}</strong> aujourd'hui`
      + (avec != null ? ` → <strong>${pct(avec)}</strong> avec la promo` : '')
      + alerte
      + `<div class="pe-promo-marge-achat">Coût d'achat : ${prixTexte(m.cout_ht)} HT / ${uniteTexte(p)}`
      + `${m.article ? ` — ${escHtml(m.article)}` : ''}${m.fournisseur ? ` (${escHtml(m.fournisseur)})` : ''}${lien}</div>`;
  }

  // Prix promo d'une réduction en % — toujours arrondi VERS LE BAS (la réduction
  // réelle est au moins celle demandée) : terminaison ,90 dès 5 €, au centime en
  // dessous (2,99 € −10 % → 2,69 € et non 1,90 €).
  function prixDepuisPourcentage(ref, pct) {
    const exact = ref * (1 - pct / 100);
    if (exact < 5) return Math.max(0.01, Math.floor(exact * 100 + 1e-6) / 100);
    return Math.round((Math.floor(exact - 0.9 + 1e-9) + 0.9) * 100) / 100;
  }

  function promoStatut(msg, type) {
    const el = $('promo-statut');
    el.textContent = msg;
    el.className = `pe-print-status pe-print-status--${type}`;
    el.hidden = !msg;
  }

  function promoApercu() {
    promoMarge();
    const p = promoVue.produit;
    const prix = parseFloat($('promo-prix').value);
    if (!p || !imp.stylePromo) return;
    dessinerEtiquette({ canvas: $('promo-canvas'), cadre: $('promo-cadre'), maxW: 400, maxH: 180 },
      imp.stylePromo, { ...p, promo: { prix_reference_ttc: promoVue.reference,
                                       prix_promo_ttc: isNaN(prix) ? null : prix } });
  }

  async function ouvrirPromo(id) {
    const p = produit(id);
    if (!p) return;
    promoVue.produit = p;
    promoVue.marge = null;
    promoStatut('', 'ok');
    $('promo-marge').hidden = true;
    $('promo-titre').textContent = `🔥 Promo — ${p.nom}`;
    $('promo-ref').textContent = 'Calcul du prix de référence…';
    $('modal-promo').hidden = false;
    try {
      const ref = await apiFetch(`/api/prix-etiquettes/promos/reference/${id}`);
      const enCours = ref.promo_en_cours;
      promoVue.promoId = enCours?.id ?? null;
      promoVue.marge = ref.marge ?? null;
      // Promo en cours : sa référence est figée depuis son début.
      promoVue.reference = enCours ? enCours.prix_reference_ttc : ref.prix_reference_ttc;
      $('promo-ref').innerHTML =
        `Prix actuel : <strong>${prixTexte(ref.prix_actuel_ttc)} / ${uniteTexte(p)}</strong><br>`
        + `Prix barré (plus bas des 30 derniers jours${enCours ? ', figé au début de la promo' : ''}) : `
        + `<strong>${prixTexte(promoVue.reference)}</strong>`;
      const fin = new Date(Date.now() + 7 * 86400e3).toISOString().slice(0, 10);
      $('promo-fin').min = new Date().toISOString().slice(0, 10);
      $('promo-fin').value = enCours?.date_fin ?? fin;
      $('promo-prix').value = enCours ? enCours.prix_promo_ttc.toFixed(2) : '';
      $('promo-pct').value = enCours
        ? Math.round((1 - enCours.prix_promo_ttc / promoVue.reference) * 100) : '';
      $('promo-arreter').hidden = !enCours;
      $('promo-valider').textContent = enCours ? '🔥 Modifier la promo' : '🔥 Valider et ajouter à la liste';
      promoApercu();
    } catch (e) {
      $('promo-ref').textContent = 'Erreur : ' + e.message;
    }
  }

  function fermerPromo() { $('modal-promo').hidden = true; }

  $('promo-prix').addEventListener('input', () => {
    promoStatut('', 'ok');           // la saisie change : l'ancien message ne vaut plus
    const prix = parseFloat($('promo-prix').value);
    $('promo-pct').value = (!isNaN(prix) && promoVue.reference)
      ? Math.round((1 - prix / promoVue.reference) * 100) : '';
    promoApercu();
  });
  $('promo-pct').addEventListener('input', () => {
    promoStatut('', 'ok');
    const pct = parseFloat($('promo-pct').value);
    if (!isNaN(pct) && promoVue.reference) {
      $('promo-prix').value = prixDepuisPourcentage(promoVue.reference, pct).toFixed(2);
    }
    promoApercu();
  });
  document.querySelectorAll('#promo-raccourcis [data-pct]').forEach(b => b.addEventListener('click', () => {
    $('promo-pct').value = b.dataset.pct;
    $('promo-pct').dispatchEvent(new Event('input'));
  }));
  $('promo-annuler').addEventListener('click', fermerPromo);
  $('modal-promo').addEventListener('click', e => { if (e.target === $('modal-promo')) fermerPromo(); });

  $('promo-valider').addEventListener('click', async () => {
    const prix = parseFloat($('promo-prix').value);
    if (isNaN(prix) || prix <= 0) { promoStatut('Indiquez le prix promo.', 'err'); return; }
    if (!$('promo-fin').value) { promoStatut('Indiquez la date de fin.', 'err'); return; }
    try {
      await apiFetch('/api/prix-etiquettes/promos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ produit_id: promoVue.produit.id, prix_promo_ttc: prix,
                               date_fin: $('promo-fin').value }),
      });
    } catch (e) {
      // Erreur métier renvoyée par le serveur (prix ≥ référence, date passée…).
      const m = e.message.match(/"detail"\s*:\s*"([^"]+)"/);
      promoStatut(m ? m[1] : e.message, 'err');
      return;
    }
    const id = promoVue.produit.id;
    fermerPromo();
    await charger();                 // le produit porte maintenant sa promo
    if (!imp.panier.has(id)) ajouter(id); else { imp.selection = id; rendre(); }
    statut('🔥 Promo enregistrée — l\'étiquette promo est dans la liste à imprimer.', 'ok');
  });

  $('promo-arreter').addEventListener('click', async () => {
    if (!promoVue.promoId) return;
    if (!confirm('Arrêter la promo maintenant ? L\'étiquette normale sera ajoutée aux étiquettes à refaire.')) return;
    try {
      await apiFetch(`/api/prix-etiquettes/promos/${promoVue.promoId}/terminer`, { method: 'POST' });
    } catch (e) {
      promoStatut('Erreur : ' + e.message, 'err');
      return;
    }
    fermerPromo();
    await charger();
    statut('Promo arrêtée — l\'étiquette normale est dans les étiquettes à refaire.', 'ok');
  });

  // ── Historique des impressions (date, heure, produits, prix imprimé) ──
  const MODE_IMPRESSION = { serveur: '🖨️ imprimante', navigateur: '🖥️ navigateur' };
  const ICONE_TYPE = { promo: '🔥 ', libre: '✏️ ', normal: '' };

  // « aujourd'hui à 14:32 », « hier à 09:05 », sinon « 12/10 à 17:40 ».
  function quand(s) {
    if (!s) return '';
    const jour = s.slice(0, 10), heure = s.slice(11, 16);
    const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    const auj = new Date(), hier = new Date(Date.now() - 86400e3);
    if (jour === iso(auj)) return `Aujourd'hui à ${heure}`;
    if (jour === iso(hier)) return `Hier à ${heure}`;
    return `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)} à ${heure}`;
  }

  $('imp-historique').addEventListener('click', async () => {
    const el = $('historique-liste');
    el.innerHTML = '<div class="pe-imp-vide">Chargement…</div>';
    $('modal-historique').hidden = false;
    try {
      const { impressions } = await apiFetch('/api/prix-etiquettes/impressions?limit=100');
      el.innerHTML = impressions.length ? impressions.map(i => `
        <div class="pe-histo-lot">
          <div class="pe-histo-tete">
            <span class="pe-histo-quand">${quand(i.imprime_at)}</span>
            <span class="pe-histo-mode">${MODE_IMPRESSION[i.mode] || escHtml(i.mode)}</span>
            <span class="pe-histo-total">${i.total} étiquette${i.total > 1 ? 's' : ''}</span>
          </div>
          <ul class="pe-histo-lignes">${i.lignes.map(l => `
            <li>${ICONE_TYPE[l.type] || ''}${escHtml(l.libelle || '—')}
              ${l.quantite > 1 ? `<strong>×${l.quantite}</strong>` : ''}
              ${l.prix_ttc != null ? `— ${prixTexte(l.prix_ttc)}${l.type === 'promo' ? ' (promo)' : ''}` : ''}</li>`).join('')}
          </ul>
        </div>`).join('') : '<div class="pe-imp-vide">Aucune impression pour l\'instant.</div>';
    } catch (e) {
      el.innerHTML = `<div class="pe-imp-vide">Erreur : ${escHtml(e.message)}</div>`;
    }
  });
  $('historique-fermer').addEventListener('click', () => { $('modal-historique').hidden = true; });
  $('modal-historique').addEventListener('click', e => {
    if (e.target === $('modal-historique')) $('modal-historique').hidden = true;
  });

  $('imp-file-tout').addEventListener('click', () => {
    state.file.forEach((_, id) => { if (!imp.panier.has(id)) ajouter(id); });
  });
  $('imp-vider').addEventListener('click', () => {
    imp.panier.clear();
    imp.selection = null;
    sauverPanier();
    rendre();
  });
  $('imp-recherche').addEventListener('input', e => {
    imp.recherche = e.target.value;
    rendreProduits();
  });

  // ── Onglet ─────────────────────────────────────────────────
  imp.panier = lirePanier();
  let premierAffichage = true;
  window.peVues.imprimer = {
    async afficher() {
      try {
        await charger();
      } catch (e) {
        statut('Erreur de chargement : ' + e.message, 'err');
        return;
      }
      if (premierAffichage) {
        const params = new URLSearchParams(location.search);
        // Tuile du Hub « N étiquettes à refaire » : liste pré-remplie.
        if (params.has('reimprimer') && imp.panier.size === 0) {
          state.file.forEach((_, id) => ajouter(id));
        }
        // Bouton 🏷️ du catalogue de vente : le produit dans la liste, ou sa promo.
        const id = parseInt(params.get('produit'), 10);
        if (id && produit(id)) {
          if (params.get('promo')) {
            ouvrirPromo(id);
          } else if (!imp.panier.has(id)) {
            ajouter(id);
          } else {
            imp.selection = id;
            rendre();
          }
        } else if (id) {
          statut('Ce produit n\'est pas disponible (désactivé ?).', 'err');
        }
        // On retire les paramètres : un rechargement ne refait pas l'action.
        if (params.has('produit') || params.has('reimprimer')) {
          history.replaceState(null, '', location.pathname);
        }
      }
      premierAffichage = false;
    },
  };
})();

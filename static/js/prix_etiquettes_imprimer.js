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
  };

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
      return `<div class="pe-imp-produit">
          <div class="pe-imp-produit-nom">${escHtml(p.nom)}${aRefaire}</div>
          <div class="pe-imp-produit-prix">${sansPrix ? 'pas de prix' : `${prixTexte(p.prix_vente_ttc)} / ${uniteTexte(p)}`}</div>
          <button class="pe-imp-plus ${q ? 'pe-imp-plus--ajoute' : ''}" data-id="${p.id}"
                  ${sansPrix ? 'disabled title="Renseignez d\'abord son prix dans le catalogue de vente"' : ''}
                  aria-label="Ajouter ${escHtml(p.nom)}">${q ? `✓ ${q}` : '+'}</button>
        </div>`;
    }).join('');
    el.querySelectorAll('[data-id]').forEach(b => b.addEventListener('click', () => ajouter(+b.dataset.id)));
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
              <span>${prixTexte(p.prix_vente_ttc)} / ${uniteTexte(p)}</span></button>
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
    dessinerEtiquette({ canvas: $('imp-canvas'), cadre: $('imp-cadre'), maxW: 420, maxH: 190 },
                      imp.style, p || null);
  }

  function rendre() {
    rendreFile();
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

  $('imp-imprimer').addEventListener('click', async () => {
    const produits = lignesPanier();
    if (!produits.length || !imp.style) return;
    const btn = $('imp-imprimer');
    btn.disabled = true;
    statut('Envoi à l\'imprimante…', 'loading');
    try {
      const res = await apiFetch('/api/prix-etiquettes/imprimer-masse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: imp.style, produits }),
      });
      // Comme le serveur : un produit est parti si TOUS ses exemplaires sont partis.
      let reste = res.imprimees;
      produits.forEach(l => {
        if (reste >= l.quantite) imp.panier.delete(l.produit_id);
        reste -= l.quantite;
      });
      imp.selection = null;
      sauverPanier();
      if (res.erreurs?.length) {
        statut(`${res.imprimees} imprimée(s) — ${res.erreurs[0]}`, 'err');
      } else {
        statut(`✓ ${res.imprimees} étiquette${res.imprimees > 1 ? 's' : ''} imprimée${res.imprimees > 1 ? 's' : ''}.`, 'ok');
      }
    } catch (e) {
      statut('Erreur impression : ' + e.message, 'err');
    }
    await chargerFile();
    rendre();
  });

  $('imp-navigateur').addEventListener('click', async () => {
    const produits = lignesPanier();
    if (!produits.length || !imp.style) return;
    statut('Préparation des étiquettes…', 'loading');
    try {
      const n = await imprimerSerieNavigateur(imp.style, produits);
      statut(`Aperçu de ${n} étiquette(s) ouvert — choisissez l'imprimante.`, 'ok');
      await proposerSortieFile(produits.map(p => p.produit_id));
      rendre();
    } catch (e) {
      statut(e.message, 'err');
    }
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
      // Arrivée depuis la tuile du Hub « N étiquettes à refaire » : liste pré-remplie.
      if (premierAffichage && new URLSearchParams(location.search).has('reimprimer')
          && imp.panier.size === 0) {
        state.file.forEach((_, id) => ajouter(id));
      }
      premierAffichage = false;
    },
  };
})();

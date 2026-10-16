'use strict';
/* ============================================================
   prix_etiquettes_style.js — Vue « Style des étiquettes »

   Le style ne contient QUE l'apparence (format, fond, police, taille,
   alignement de chaque zone). Le texte vient toujours du produit :
   zones Nom / Prix / Unité (+ textes fixes), et pour la promo
   Ancien prix barré / Prix promo / Économie. Aucune {variable} visible.

   Dépend de prix_etiquettes.js (chargé avant) : apiFetch, escHtml,
   dessinerEtiquette, state, chargerFonts, chargerFontFace, policeParDefaut.
   ============================================================ */

(function () {
  const $ = id => document.getElementById(id);

  // Zones possibles. `obligatoire` : ne peut pas être retirée (prix ; mentions
  // légales de la promo : ancien prix barré + prix promo).
  const ZONES = {
    nom:            { icone: '🥩', label: 'Nom du produit' },
    prix:           { icone: '💶', label: 'Prix', obligatoire: ['normal'] },
    unite:          { icone: '⚖️', label: 'Unité (le kg / la pièce)' },
    prix_reference: { icone: '❌', label: 'Ancien prix barré', obligatoire: ['promo'],
                      aide: 'Plus bas prix des 30 jours avant la promo (calcul automatique)' },
    prix_promo:     { icone: '🔥', label: 'Prix promo', obligatoire: ['promo'] },
    economie:       { icone: '💰', label: 'Économie (« Économisez … / kg »)' },
    texte:          { icone: '✏️', label: 'Texte fixe' },
  };
  const ZONES_PAR_TYPE = {
    normal: ['nom', 'prix', 'unite'],
    promo:  ['nom', 'prix_reference', 'prix_promo', 'unite', 'economie'],
  };
  const TAILLES = [
    { poids: 0.4, label: 'Très petit' }, { poids: 0.6, label: 'Petit' },
    { poids: 1, label: 'Normal' }, { poids: 2, label: 'Grand' }, { poids: 3, label: 'Très grand' },
  ];
  const ALIGNEMENTS = [
    { val: 'left', label: '⇤', titre: 'À gauche' },
    { val: 'center', label: '↔', titre: 'Centré' },
    { val: 'right', label: '⇥', titre: 'À droite' },
  ];

  const vue = {
    type: 'normal',
    styles: { normal: null, promo: null },   // réponses de GET /styles
    brouillons: {},                          // type → config en cours d'édition
    modifie: false,
    produits: [],
  };

  // ── Valeurs par défaut ─────────────────────────────────────
  function ligne(zone, poids, base = {}) {
    return { zone, texte: '', poids, taille_px: 0, gras: false,
             police: base.police ?? policeParDefaut() ?? null, alignement: 'center' };
  }

  function styleNormalParDefaut() {
    return { largeur_cm: 10, hauteur_cm: 6, fond_noir: false, type: 'normal',
             lignes: [ligne('nom', 1), ligne('prix', 2), ligne('unite', 0.6)] };
  }

  // Style promo dérivé du style normal : même format, même fond, même police.
  function stylePromoDepuis(normal) {
    const n = normal || styleNormalParDefaut();
    const poids = z => n.lignes.find(l => l.zone === z)?.poids;
    const base = { police: n.lignes[0]?.police ?? null };
    return {
      largeur_cm: n.largeur_cm, hauteur_cm: n.hauteur_cm, fond_noir: n.fond_noir, type: 'promo',
      lignes: [
        ligne('nom', poids('nom') ?? 1, base),
        ligne('prix_reference', 0.8, base),
        ligne('prix_promo', poids('prix') ?? 2, base),
        ligne('unite', poids('unite') ?? 0.6, base),
        ligne('economie', 0.6, base),
      ],
    };
  }

  function brouillon() { return vue.brouillons[vue.type]; }

  // ── Produit d'aperçu (+ promo d'exemple : −15 % ramené à ,90) ──
  function produitApercu() {
    const id = parseInt($('style-produit').value, 10);
    const p = vue.produits.find(x => x.id === id) || vue.produits[0]
      || { nom: 'Steak haché', prix_vente_ttc: 19.90, unite_vente: 'kg' };
    if (vue.type !== 'promo') return p;
    const prix = parseFloat(p.prix_vente_ttc) || 10;
    const exemple = Math.max(0.9, Math.floor(prix * 0.85) - 0.1);   // 19,90 → 15,90
    return { ...p, promo: { prix_reference_ttc: prix,
                            prix_promo_ttc: Math.round(exemple * 100) / 100 } };
  }

  // ── Rendu ──────────────────────────────────────────────────
  function apercu() {
    const cfg = brouillon();
    if (!cfg) return;
    // Texte de chaque zone = sa variable (comme le serveur) ; textes fixes tels quels.
    const TEXTES = { nom: '{Nom}', prix: '{prix}', unite: '{article_unite}',
                     prix_reference: '{prix_reference}', prix_promo: '{prix_promo}',
                     economie: 'Économisez {economie_unite}' };
    const config = { ...cfg, lignes: cfg.lignes.map(l => ({
      ...l, texte: l.zone === 'texte' ? l.texte : TEXTES[l.zone], barre: l.zone === 'prix_reference',
    })) };
    dessinerEtiquette({ canvas: $('style-canvas'), cadre: $('style-cadre'), info: $('style-dims'),
                        maxW: 640, maxH: 420 }, config, produitApercu());
  }

  function marquerModifie() {
    vue.modifie = true;
    apercu();
  }

  function optionsPolice(active) {
    const opts = [`<option value="">DejaVu (standard)</option>`].concat(
      state.fontsDispos.map(f => `<option value="${escHtml(f.nom)}" ${f.nom === active ? 'selected' : ''}>`
        + `${escHtml(f.label)}</option>`));
    // Police du style absente du serveur : on la montre telle quelle (pas de faux « DejaVu »).
    if (active && !state.fontsDispos.some(f => f.nom === active)) {
      opts.push(`<option value="${escHtml(active)}" selected>${escHtml(active)} (introuvable)</option>`);
    }
    return opts.join('');
  }

  function rendreZones() {
    const cfg = brouillon();
    const conteneur = $('style-zones');
    conteneur.innerHTML = '';
    cfg.lignes.forEach((l, i) => {
      const info = ZONES[l.zone] || ZONES.texte;
      const obligatoire = (info.obligatoire || []).includes(vue.type);
      const custom = !!l.police;
      const div = document.createElement('div');
      div.className = 'pe-zone';
      div.innerHTML = `
        <div class="pe-zone-tete">
          <span class="pe-zone-nom">${info.icone} ${escHtml(info.label)}</span>
          <span class="pe-zone-actions">
            <button class="pe-icone-btn" data-action="monter" title="Monter" ${i === 0 ? 'disabled' : ''}>▲</button>
            <button class="pe-icone-btn" data-action="descendre" title="Descendre"
                    ${i === cfg.lignes.length - 1 ? 'disabled' : ''}>▼</button>
            ${obligatoire ? '' : '<button class="pe-icone-btn pe-icone-btn--suppr" data-action="retirer" title="Retirer">✕</button>'}
          </span>
        </div>
        ${info.aide ? `<div class="pe-zone-aide">${escHtml(info.aide)}</div>` : ''}
        ${l.zone === 'texte'
          ? `<input type="text" class="pe-input pe-input--grand" data-champ="texte"
                    placeholder="Ex. Fait maison, Origine France…" value="${escHtml(l.texte)}">` : ''}
        <div class="pe-segment pe-segment--tailles" role="group" aria-label="Taille">
          ${TAILLES.map(t => `<button class="pe-segment-btn ${!l.taille_px && Math.abs(l.poids - t.poids) < 0.01 ? 'active' : ''}"
                                      data-poids="${t.poids}">${t.label}</button>`).join('')}
        </div>
        <div class="pe-zone-options">
          <select class="pe-input" data-champ="police" aria-label="Police">${optionsPolice(l.police)}</select>
          <div class="pe-segment" role="group" aria-label="Alignement">
            ${ALIGNEMENTS.map(a => `<button class="pe-segment-btn ${l.alignement === a.val ? 'active' : ''}"
                                            data-align="${a.val}" title="${a.titre}">${a.label}</button>`).join('')}
          </div>
          <button class="pe-segment-btn pe-zone-gras ${l.gras && !custom ? 'active' : ''}" data-action="gras"
                  ${custom ? 'disabled title="Sans effet avec une police importée"' : ''}><b>G</b> Gras</button>
        </div>`;

      div.querySelectorAll('[data-poids]').forEach(b => b.addEventListener('click', () => {
        l.poids = parseFloat(b.dataset.poids); l.taille_px = 0; rendreZones(); marquerModifie();
      }));
      div.querySelectorAll('[data-align]').forEach(b => b.addEventListener('click', () => {
        l.alignement = b.dataset.align; rendreZones(); marquerModifie();
      }));
      div.querySelector('[data-champ="police"]').addEventListener('change', async e => {
        l.police = e.target.value || null;
        if (l.police) await chargerFontFace(l.police);
        rendreZones(); marquerModifie();
      });
      const texte = div.querySelector('[data-champ="texte"]');
      if (texte) texte.addEventListener('input', () => { l.texte = texte.value; marquerModifie(); });
      div.querySelector('[data-action="gras"]').addEventListener('click', () => {
        l.gras = !l.gras; rendreZones(); marquerModifie();
      });
      div.querySelector('[data-action="monter"]').addEventListener('click', () => deplacer(i, -1));
      div.querySelector('[data-action="descendre"]').addEventListener('click', () => deplacer(i, 1));
      div.querySelector('[data-action="retirer"]')?.addEventListener('click', () => {
        cfg.lignes.splice(i, 1); rendreZones(); marquerModifie();
      });
      conteneur.appendChild(div);
    });
    rendreAjouts();
  }

  function deplacer(i, sens) {
    const lignes = brouillon().lignes;
    const j = i + sens;
    if (j < 0 || j >= lignes.length) return;
    [lignes[i], lignes[j]] = [lignes[j], lignes[i]];
    rendreZones(); marquerModifie();
  }

  // Boutons « + » : zones absentes du type courant + texte fixe (toujours).
  function rendreAjouts() {
    const cfg = brouillon();
    const presentes = new Set(cfg.lignes.map(l => l.zone));
    const manquantes = ZONES_PAR_TYPE[vue.type].filter(z => !presentes.has(z));
    const el = $('style-ajouts');
    el.innerHTML = manquantes.concat(['texte']).map(z =>
      `<button class="pe-btn pe-btn--sm pe-btn--ajout" data-ajout="${z}">+ ${ZONES[z].icone} ${escHtml(ZONES[z].label)}</button>`
    ).join('');
    el.querySelectorAll('[data-ajout]').forEach(b => b.addEventListener('click', () => {
      const z = b.dataset.ajout;
      cfg.lignes.push(ligne(z, z === 'texte' ? 0.6 : 1, { police: cfg.lignes[0]?.police }));
      rendreZones(); marquerModifie();
    }));
  }

  function rendreFormat() {
    const cfg = brouillon();
    $('style-largeur').value = cfg.largeur_cm;
    $('style-hauteur').value = cfg.hauteur_cm;
    document.querySelectorAll('[data-fond]').forEach(b =>
      b.classList.toggle('active', (b.dataset.fond === 'noir') === !!cfg.fond_noir));
  }

  function rendreType() {
    document.querySelectorAll('[data-type-style]').forEach(b =>
      b.classList.toggle('active', b.dataset.typeStyle === vue.type));
    $('style-note-promo').hidden = vue.type !== 'promo';
    const s = vue.styles[vue.type];
    const info = $('style-info');
    if (s?.converti) {
      info.textContent = '✨ Votre ancien modèle a été repris automatiquement (nom, prix, unité). '
        + 'Vérifiez l\'aperçu, puis « Enregistrer le style ».';
      info.hidden = false;
    } else if (!s || s.par_defaut) {
      info.textContent = vue.type === 'promo'
        ? '✨ Style promo proposé à partir de votre étiquette normale. Ajustez-le puis enregistrez.'
        : '✨ Style proposé par défaut. Ajustez-le puis enregistrez.';
      info.hidden = false;
    } else {
      info.hidden = true;
    }
    rendreFormat();
    rendreZones();
    apercu();
  }

  function statut(msg, type) {
    const el = $('style-statut');
    el.textContent = msg;
    el.className = `pe-print-status pe-print-status--${type}`;
    el.hidden = false;
    if (type === 'ok') setTimeout(() => { el.hidden = true; }, 4000);
  }

  // ── Chargement ─────────────────────────────────────────────
  function cloner(x) { return JSON.parse(JSON.stringify(x)); }

  async function charger() {
    const [styles, cat] = await Promise.all([
      apiFetch('/api/prix-etiquettes/styles'),
      apiFetch('/api/prix-etiquettes/catalogue?limit=2000'),
    ]);
    vue.styles = styles;
    afficherPolices();
    vue.produits = (cat.articles ?? []).filter(p => p.prix_vente_ttc != null);
    const normal = styles.normal ? cloner(styles.normal.config) : styleNormalParDefaut();
    vue.brouillons = {
      normal,
      promo: styles.promo ? cloner(styles.promo.config) : stylePromoDepuis(normal),
    };
    // Produit d'aperçu : un produit de la file « À réimprimer » sinon le premier.
    const sel = $('style-produit');
    sel.innerHTML = vue.produits.map(p =>
      `<option value="${p.id}">${escHtml(p.nom)} — ${parseFloat(p.prix_vente_ttc).toFixed(2).replace('.', ',')} €</option>`
    ).join('');
    const enFile = vue.produits.find(p => state.file.has(p.id));
    if (enFile) sel.value = enFile.id;
    vue.modifie = false;
    rendreType();
  }

  // ── Événements ─────────────────────────────────────────────
  document.querySelectorAll('[data-type-style]').forEach(b => b.addEventListener('click', () => {
    if (b.dataset.typeStyle === vue.type) return;
    vue.type = b.dataset.typeStyle;
    rendreType();
  }));
  document.querySelectorAll('[data-fond]').forEach(b => b.addEventListener('click', () => {
    brouillon().fond_noir = b.dataset.fond === 'noir';
    rendreFormat(); marquerModifie();
  }));
  $('style-largeur').addEventListener('input', e => {
    brouillon().largeur_cm = parseFloat(e.target.value) || 10; marquerModifie();
  });
  $('style-hauteur').addEventListener('input', e => {
    brouillon().hauteur_cm = Math.min(6.2, parseFloat(e.target.value) || 6); marquerModifie();
  });
  $('style-produit').addEventListener('change', apercu);

  // ── Verrou : modification réservée à l'administrateur ─────
  // Le mot de passe administrateur est vérifié par le serveur au déverrouillage ; il
  // remet une autorisation de 15 min (gardée en mémoire seulement) que chaque
  // « Enregistrer » présente. Quitter l'onglet reverrouille (tablette partagée).
  let jeton = null, minuteurVerrou = null;

  function verrouiller(message) {
    jeton = null;
    clearTimeout(minuteurVerrou);
    document.querySelector('.pe-style').classList.add('verrouille');
    if (message) statut(message, 'err');
  }

  function ouvrirMotDePasse() {
    $('admin-mdp').value = '';
    $('admin-statut').hidden = true;
    $('modal-admin').hidden = false;
    $('admin-mdp').focus();
  }

  async function validerMotDePasse() {
    const el = $('admin-statut');
    try {
      const res = await fetch('/api/prix-etiquettes/styles/deverrouiller', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + (getAdminToken() || '') },
        body: JSON.stringify({ password: $('admin-mdp').value }),
        cache: 'no-store',
      });
      if (!res.ok) {
        el.textContent = res.status === 429 ? 'Trop d\'essais : réessayez dans une minute.'
          : res.status === 401 ? 'Mot de passe administrateur incorrect.' : `Erreur ${res.status}`;
        el.className = 'pe-print-status pe-print-status--err';
        el.hidden = false;
        $('admin-mdp').select();
        return;
      }
      const data = await res.json();
      jeton = data.jeton;
      $('modal-admin').hidden = true;
      document.querySelector('.pe-style').classList.remove('verrouille');
      clearTimeout(minuteurVerrou);
      minuteurVerrou = setTimeout(() => verrouiller('Style reverrouillé (15 min écoulées).'),
                                  (data.expire_dans || 900) * 1000);
      statut('🔓 Style déverrouillé : modifiez puis « Enregistrer le style ».', 'ok');
    } catch (e) {
      el.textContent = 'Erreur : ' + e.message;
      el.className = 'pe-print-status pe-print-status--err';
      el.hidden = false;
    }
  }

  // ── Polices (importer / supprimer) : réservé à l'administrateur ──
  function afficherPolices() {
    const el = $('style-polices');
    el.innerHTML = state.fontsDispos.length
      ? state.fontsDispos.map(f => `<span class="pe-font-chip">${escHtml(f.label)}
          <button class="pe-font-chip-del" data-police="${escHtml(f.nom)}" title="Supprimer">✕</button></span>`).join('')
      : '<span class="pe-dim-aide">Aucune police importée (police standard DejaVu).</span>';
  }

  async function appelPolice(url, options) {
    const res = await fetch(url, { ...options, cache: 'no-store',
      headers: { ...(options.headers || {}), 'X-Jeton-Styles': jeton || '',
                 Authorization: 'Bearer ' + (getAdminToken() || '') } });
    if (res.status === 401) { verrouiller('Autorisation expirée : déverrouillez à nouveau.'); return false; }
    if (!res.ok) {
      const detail = (await res.json().catch(() => ({}))).detail;
      statut(detail || `Erreur ${res.status}`, 'err');
      return false;
    }
    await chargerFonts();
    afficherPolices();
    rendreZones();
    apercu();
    return true;
  }

  $('style-polices').addEventListener('click', async e => {
    const btn = e.target.closest('[data-police]');
    if (!btn || !confirm(`Supprimer la police « ${btn.dataset.police} » ?`)) return;
    if (await appelPolice(`/api/prix-etiquettes/fonts/${encodeURIComponent(btn.dataset.police)}`,
                          { method: 'DELETE' })) statut('Police supprimée.', 'ok');
  });

  $('style-police-fichier').addEventListener('change', async e => {
    const fichier = e.target.files[0];
    if (!fichier) return;
    const fd = new FormData();
    fd.append('fichier', fichier);
    if (await appelPolice('/api/prix-etiquettes/upload-font', { method: 'POST', body: fd })) {
      statut(`✓ Police « ${fichier.name} » importée : choisissez-la dans une zone.`, 'ok');
    }
    e.target.value = '';
  });

  $('style-deverrouiller').addEventListener('click', ouvrirMotDePasse);
  $('admin-valider').addEventListener('click', validerMotDePasse);
  $('admin-mdp').addEventListener('keydown', e => { if (e.key === 'Enter') validerMotDePasse(); });
  $('admin-annuler').addEventListener('click', () => { $('modal-admin').hidden = true; });

  $('style-enregistrer').addEventListener('click', async () => {
    const btn = $('style-enregistrer');
    if (!jeton) { verrouiller(); ouvrirMotDePasse(); return; }
    btn.disabled = true;
    try {
      const cfg = brouillon();
      if (cfg.lignes.some(l => l.zone === 'texte' && !l.texte.trim())) {
        statut('Un texte fixe est vide : remplissez-le ou retirez-le.', 'err');
        return;
      }
      const res = await fetch(`/api/prix-etiquettes/styles/${vue.type}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + (getAdminToken() || '') },
        body: JSON.stringify({ config: cfg, jeton }),
        cache: 'no-store',
      });
      if (res.status === 401) {
        verrouiller('Autorisation expirée : déverrouillez à nouveau (vos réglages sont conservés).');
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const styles = await res.json();
      vue.styles = styles;
      vue.brouillons[vue.type] = cloner(styles[vue.type].config);
      vue.modifie = false;
      state.styleNormal = styles.normal?.config ?? state.styleNormal;   // l'étiquette libre suit
      rendreType();
      statut(`✓ Style ${vue.type === 'promo' ? 'promo' : 'normal'} enregistré.`, 'ok');
    } catch (e) {
      statut('Erreur : ' + e.message, 'err');
    } finally {
      btn.disabled = false;
    }
  });

  // ── Onglet (géré par prix_etiquettes.js → afficherOnglet) ──
  let styleCharge = false;
  window.peVues.style = {
    async afficher() {
      if (!jeton) verrouiller();
      if (styleCharge) { apercu(); return; }
      styleCharge = true;
      try { await charger(); } catch (e) { styleCharge = false; statut('Erreur : ' + e.message, 'err'); }
    },
    quitter() {
      if (vue.modifie && !confirm('Le style a été modifié sans être enregistré. Quitter quand même ?')) {
        return false;
      }
      verrouiller();       // tablette partagée : on referme derrière soi
      return true;
    },
  };

  window.addEventListener('beforeunload', e => {
    if (vue.modifie) { e.preventDefault(); e.returnValue = ''; }
  });
})();

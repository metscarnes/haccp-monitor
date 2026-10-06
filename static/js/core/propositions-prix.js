'use strict';
/* ============================================================
   propositions-prix.js — Popup « Adapter les prix de vente »

   Affiche les propositions de nouveau prix de vente nées d'une variation du
   coût d'achat de référence (moteur : src/prix_vente.py) et envoie les
   décisions. Partagé par la réception (après « Mettre à jour » le prix
   d'achat) et le catalogue vente (badge « Prix à revoir »).

   Règles d'affichage (décisions utilisateur 04-06/10/2026) :
   - hausses qui changent le prix → à décider, cochées d'office (sauf alerte) ;
   - baisses → pour information, section repliée, jamais cochées ;
   - hausses absorbées par l'arrondi → simple mention (gardées en mémoire) ;
   - rien n'est appliqué sans clic ; une hausse non cochée reste en attente.

   API : PropositionsPrix.ouvrir({ receptionId, onFerme })  → Promise<bool>
         PropositionsPrix.compter({ receptionId })            → Promise<{a_decider, baisses}>
   Modale dans la page (jamais de nouvel onglet : tablette en mode kiosque).
   ============================================================ */
(function () {
  const API = '/api/vente/propositions-prix';

  const esc = s => String(s ?? '').replace(/[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const euro = v => (v == null ? '—' : Number(v).toFixed(2).replace('.', ',') + ' €');
  const pct = v => (v == null ? '—' : (Number(v) * 100).toFixed(1).replace('.', ',') + ' %');
  const pctSigne = v => (v == null ? '' : (v > 0 ? '+' : '') + Number(v).toFixed(1).replace('.', ',') + ' %');

  // Miroir de taux_marque (src/prix_vente.py) : (prix HT − coût) ÷ prix HT.
  function tauxMarque(prixTtc, tva, cout) {
    const p = parseFloat(prixTtc);
    if (!(p > 0) || cout == null) return null;
    const ht = p / (1 + (parseFloat(tva) || 0) / 100);
    return (ht - cout) / ht;
  }

  async function lire(receptionId) {
    const url = receptionId ? `${API}?reception_id=${encodeURIComponent(receptionId)}` : API;
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async function compter({ receptionId } = {}) {
    try {
      const data = await lire(receptionId);
      return { a_decider: data.compteurs.a_decider || 0, baisses: data.compteurs.baisses || 0 };
    } catch (_) {
      return { a_decider: 0, baisses: 0 };
    }
  }

  // ── Styles (injectés une fois) ────────────────────────────────
  function injecterStyles() {
    if (document.getElementById('pp-styles')) return;
    const st = document.createElement('style');
    st.id = 'pp-styles';
    st.textContent = `
      .pp-overlay { position: fixed; inset: 0; z-index: 9000; background: rgba(30,20,10,.55);
        display: flex; align-items: center; justify-content: center; padding: 12px; }
      .pp-modal { background: #FFFBF3; color: #3D2008; border-radius: 14px; width: 100%;
        max-width: 760px; max-height: 92vh; display: flex; flex-direction: column;
        box-shadow: 0 10px 40px rgba(0,0,0,.35); font-size: .95rem; }
      .pp-head { padding: 14px 18px 10px; border-bottom: 1px solid #ecdcc0; display: flex; gap: 10px; }
      .pp-titre { font-weight: 800; font-size: 1.15rem; }
      .pp-sous { font-size: .82rem; color: #8a6a45; margin-top: 2px; }
      .pp-fermer { margin-left: auto; background: none; border: none; font-size: 1.4rem;
        cursor: pointer; color: #6B3A1F; min-width: 44px; min-height: 44px; }
      .pp-corps { overflow-y: auto; padding: 10px 18px; flex: 1; }
      .pp-groupe { margin: 8px 0 14px; border: 1px solid #ecdcc0; border-radius: 10px; overflow: hidden; }
      .pp-groupe-tete { display: flex; align-items: center; gap: 10px; background: #F5ECD7;
        padding: 8px 12px; font-weight: 700; }
      .pp-groupe-tete small { font-weight: 500; color: #8a6a45; }
      .pp-groupe-var { margin-left: auto; font-size: .85rem; }
      .pp-hausse { color: #b42318; } .pp-baisse { color: #1f6b32; }
      .pp-ligne { display: grid; grid-template-columns: 34px 1fr auto; gap: 6px 10px;
        align-items: center; padding: 9px 12px; border-top: 1px solid #f1e6d2; }
      .pp-ligne:first-of-type { border-top: none; }
      .pp-ligne input[type=checkbox], .pp-groupe-tete input[type=checkbox] { width: 22px; height: 22px; }
      .pp-nom { font-weight: 600; }
      .pp-detail { font-size: .8rem; color: #7a5a38; }
      .pp-prix { display: flex; align-items: center; gap: 6px; white-space: nowrap; }
      .pp-prix input { width: 82px; min-height: 40px; padding: 4px 6px; border: 1.5px solid #d8c9b2;
        border-radius: 8px; font-size: 1rem; font-weight: 700; text-align: right; }
      .pp-alt { border: 1px dashed #c9a87a; background: #fff; border-radius: 14px; padding: 3px 9px;
        font-size: .8rem; cursor: pointer; min-height: 32px; }
      .pp-marge { grid-column: 2 / 4; font-size: .82rem; color: #5b4128; }
      .pp-marge b { color: #3D2008; }
      .pp-alerte { grid-column: 2 / 4; font-size: .8rem; background: #fff1e6; color: #9a3412;
        border-radius: 6px; padding: 4px 8px; }
      .pp-info { margin: 10px 0; }
      .pp-info summary { cursor: pointer; font-weight: 700; padding: 8px 0; color: #1f6b32; }
      .pp-note { font-size: .82rem; color: #8a6a45; margin: 8px 0; }
      .pp-vide { text-align: center; padding: 28px 10px; color: #7a5a38; }
      .pp-pied { padding: 12px 18px; border-top: 1px solid #ecdcc0; display: flex; gap: 10px;
        flex-wrap: wrap; align-items: center; }
      .pp-msg { flex: 1 1 100%; font-size: .85rem; }
      .pp-msg.err { color: #b42318; } .pp-msg.ok { color: #1f6b32; font-weight: 600; }
      .pp-btn { min-height: 44px; padding: 8px 16px; border-radius: 10px; font-weight: 700;
        font-size: .95rem; cursor: pointer; border: 1.5px solid #6B3A1F; background: #fff; color: #6B3A1F; }
      .pp-btn--primaire { background: #2f7d3a; border-color: #2f7d3a; color: #fff; margin-left: auto; }
      .pp-btn:disabled { opacity: .5; cursor: default; }
    `;
    document.head.appendChild(st);
  }

  // ── Rendu ─────────────────────────────────────────────────────
  function ligneHtml(p) {
    const prop = p.proposition;
    const unite = p.unite_vente === 'piece' ? 'pièce' : 'kg';
    const alerte = prop.alerte_unite
      ? `⚠ Coût ${pctSigne(prop.variation_cout_pct)} : vérifie l'unité (kg / colis / pièce) avant d'appliquer.`
      : prop.alerte_achat_gratuit ? '⚠ Cet achat était à 0 € : prix jamais saisi ? À vérifier.' : '';
    const alt = prop.prix_alternatif_ttc
      ? `<button type="button" class="pp-alt" data-alt="${prop.prix_alternatif_ttc}">ou ${euro(prop.prix_alternatif_ttc)}</button>` : '';
    return `
      <div class="pp-ligne" data-id="${p.id}" data-cout="${prop.cout_nouveau}" data-tva="${p.tva_percent ?? 0}">
        <input type="checkbox" class="pp-cb" ${prop.pre_coche ? 'checked' : ''} aria-label="Appliquer">
        <div>
          <div class="pp-nom">${esc(p.nom)}</div>
          <div class="pp-detail">actuel ${euro(prop.prix_actuel_ttc)} / ${unite}</div>
        </div>
        <div class="pp-prix">
          → <input type="number" class="pp-input" step="0.01" min="0.01" value="${prop.prix_propose_ttc.toFixed(2)}"> €
          ${alt}
        </div>
        <div class="pp-marge">
          Marge <b>${pct(prop.taux_reference)}</b> → <b class="pp-taux">${pct(prop.taux_propose)}</b>
          · sans rien changer : ${pct(prop.taux_sans_changer)}
        </div>
        ${alerte ? `<div class="pp-alerte">${alerte}</div>` : ''}
      </div>`;
  }

  function groupesHtml(liste) {
    const groupes = new Map();
    liste.forEach(p => {
      const cle = p.catalogue_fournisseur_id ?? 0;
      if (!groupes.has(cle)) groupes.set(cle, []);
      groupes.get(cle).push(p);
    });
    return [...groupes.values()].map(lignes => {
      const p0 = lignes[0];
      const v = p0.proposition.variation_cout_pct;
      const sens = v > 0 ? 'pp-hausse' : 'pp-baisse';
      return `
        <div class="pp-groupe">
          <div class="pp-groupe-tete">
            <input type="checkbox" class="pp-cb-groupe" aria-label="Tout cocher">
            <span>${esc(p0.article_designation || 'Achat de référence')}
              <small>${esc(p0.fournisseur_nom || '')} · ${lignes.length} produit${lignes.length > 1 ? 's' : ''}</small></span>
            <span class="pp-groupe-var ${sens}">coût ${pctSigne(v)}</span>
          </div>
          ${lignes.map(ligneHtml).join('')}
        </div>`;
    }).join('');
  }

  function majGroupe(groupe) {
    const cbs = [...groupe.querySelectorAll('.pp-cb')];
    const n = cbs.filter(c => c.checked).length;
    const tete = groupe.querySelector('.pp-cb-groupe');
    tete.checked = n === cbs.length;
    tete.indeterminate = n > 0 && n < cbs.length;
  }

  // ── Ouverture ─────────────────────────────────────────────────
  async function ouvrir({ receptionId, onFerme } = {}) {
    injecterStyles();
    const overlay = document.createElement('div');
    overlay.className = 'pp-overlay';
    overlay.innerHTML = `
      <div class="pp-modal" role="dialog" aria-modal="true" aria-labelledby="pp-titre">
        <div class="pp-head">
          <div>
            <div class="pp-titre" id="pp-titre">💶 Adapter les prix de vente</div>
            <div class="pp-sous">Pour garder ta marge malgré le nouveau prix d'achat — prix arrondis comme tes étiquettes.</div>
          </div>
          <button type="button" class="pp-fermer" aria-label="Fermer">✕</button>
        </div>
        <div class="pp-corps"><div class="pp-vide">Chargement…</div></div>
        <div class="pp-pied">
          <div class="pp-msg" hidden></div>
          <button type="button" class="pp-btn pp-plus-tard">Plus tard</button>
          <button type="button" class="pp-btn pp-btn--primaire pp-appliquer" disabled>Appliquer</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    const corps = overlay.querySelector('.pp-corps');
    const msg = overlay.querySelector('.pp-msg');
    const btnAppliquer = overlay.querySelector('.pp-appliquer');
    let aChange = false;

    return new Promise(resolve => {
      const fermer = () => {
        overlay.remove();
        if (onFerme) onFerme(aChange);
        resolve(aChange);
      };
      overlay.querySelector('.pp-fermer').addEventListener('click', fermer);
      overlay.querySelector('.pp-plus-tard').addEventListener('click', fermer);
      overlay.addEventListener('click', e => { if (e.target === overlay) fermer(); });

      const afficherMsg = (texte, type) => {
        msg.textContent = texte; msg.className = `pp-msg ${type}`; msg.hidden = false;
      };
      const majCompteur = () => {
        const n = corps.querySelectorAll('.pp-cb:checked').length;
        btnAppliquer.disabled = n === 0;
        btnAppliquer.textContent = n ? `Appliquer ${n} prix` : 'Appliquer';
      };

      async function charger() {
        let data;
        try {
          data = await lire(receptionId);
        } catch (e) {
          corps.innerHTML = `<div class="pp-vide">Impossible de charger les propositions (${esc(e.message)}).</div>`;
          return;
        }
        const props = data.propositions || [];
        const aDecider = props.filter(p => p.categorie === 'a_decider');
        const baisses = props.filter(p => p.categorie === 'baisse_info');
        const absorbees = props.filter(p => p.categorie === 'absorbee');
        if (!aDecider.length && !baisses.length) {
          corps.innerHTML = `<div class="pp-vide">Aucun prix de vente à adapter : ta marge reste en place${
            absorbees.length ? ` (${absorbees.length} petite${absorbees.length > 1 ? 's' : ''} hausse${absorbees.length > 1 ? 's' : ''} absorbée${absorbees.length > 1 ? 's' : ''} par l'arrondi, gardée${absorbees.length > 1 ? 's' : ''} en mémoire)` : ''}.</div>`;
          majCompteur();
          return;
        }
        corps.innerHTML = `
          ${aDecider.length ? groupesHtml(aDecider) : '<div class="pp-note">Aucune hausse à répercuter.</div>'}
          ${baisses.length ? `
            <details class="pp-info">
              <summary>📉 Baisses de coût — pour information (${baisses.length})</summary>
              <div class="pp-note">Ta marge augmente si tu gardes ton prix. Coche seulement si tu veux baisser.</div>
              ${groupesHtml(baisses)}
            </details>` : ''}
          ${absorbees.length ? `<div class="pp-note">${absorbees.length} petite(s) hausse(s) absorbée(s) par l'arrondi : prix inchangé, gardée(s) en mémoire pour la suivante.</div>` : ''}`;
        corps.querySelectorAll('.pp-groupe').forEach(majGroupe);
        majCompteur();
      }

      // Interactions (délégation)
      corps.addEventListener('change', e => {
        if (e.target.classList.contains('pp-cb-groupe')) {
          const groupe = e.target.closest('.pp-groupe');
          groupe.querySelectorAll('.pp-cb').forEach(c => { c.checked = e.target.checked; });
        }
        const groupe = e.target.closest('.pp-groupe');
        if (groupe) majGroupe(groupe);
        majCompteur();
      });
      corps.addEventListener('input', e => {
        if (!e.target.classList.contains('pp-input')) return;
        const ligne = e.target.closest('.pp-ligne');
        const t = tauxMarque(e.target.value, ligne.dataset.tva, parseFloat(ligne.dataset.cout));
        ligne.querySelector('.pp-taux').textContent = pct(t);
        ligne.querySelector('.pp-cb').checked = true;
        majGroupe(ligne.closest('.pp-groupe'));
        majCompteur();
      });
      corps.addEventListener('click', e => {
        const alt = e.target.closest('.pp-alt');
        if (!alt) return;
        const ligne = alt.closest('.pp-ligne');
        const input = ligne.querySelector('.pp-input');
        const ancien = input.value;
        input.value = parseFloat(alt.dataset.alt).toFixed(2);
        alt.dataset.alt = ancien;
        alt.textContent = `ou ${euro(ancien)}`;
        input.dispatchEvent(new Event('input', { bubbles: true }));
      });

      btnAppliquer.addEventListener('click', async () => {
        const lignes = [...corps.querySelectorAll('.pp-ligne')];
        const decisions = [];
        for (const l of lignes) {
          const coche = l.querySelector('.pp-cb').checked;
          const estBaisse = !!l.closest('.pp-info');
          if (coche) {
            const prix = parseFloat(l.querySelector('.pp-input').value);
            if (!(prix > 0)) { afficherMsg('Un prix saisi est invalide.', 'err'); return; }
            decisions.push({ proposition_id: +l.dataset.id, action: 'appliquer', prix_ttc: prix });
          } else if (estBaisse) {
            // Baisse vue et non retenue : on garde le prix (elle ne réapparaîtra pas).
            decisions.push({ proposition_id: +l.dataset.id, action: 'garder' });
          }
          // Hausse non cochée : reste en attente (« Prix à revoir »).
        }
        btnAppliquer.disabled = true;
        btnAppliquer.textContent = '⏳';
        try {
          const res = await fetch(`${API}/decider`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ decisions }),
          });
          if (res.status === 403) {
            afficherMsg('Seul le compte responsable peut changer les prix. Les propositions restent dans « Prix à revoir ».', 'err');
            majCompteur();
            return;
          }
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const r = await res.json();
          aChange = aChange || r.appliquees.length > 0;
          const enAttente = lignes.filter(l => !l.querySelector('.pp-cb').checked && !l.closest('.pp-info')).length;
          await charger();
          afficherMsg(`✓ ${r.appliquees.length} prix mis à jour${enAttente ? ` · ${enAttente} laissé(s) en attente` : ''}`
            + (r.erreurs.length ? ` · ${r.erreurs.length} erreur(s) : ${r.erreurs[0].erreur}` : ''),
            r.erreurs.length ? 'err' : 'ok');
        } catch (e) {
          afficherMsg(`Erreur : ${e.message}`, 'err');
          majCompteur();
        }
      });

      charger();
    });
  }

  window.PropositionsPrix = { ouvrir, compter };
})();

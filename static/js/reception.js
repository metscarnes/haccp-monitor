'use strict';
/* ============================================================
   reception.js — Fiche de contrôle réception (3 étapes)
   Au Comptoir des Lilas — Mets Carnés Holding

   Responsabilités :
   - Étape 1 : Entête réception (fournisseur, BL, opérateur, camion)
   - Étape 2 : Lignes produits (ajout unitaire)
   - Étape 3 : Finalisation (conformité globale + NC éventuelles)
   - Historique des réceptions récentes (colonne droite)
   ============================================================ */

// ── Références DOM ────────────────────────────────────────────
const elDate        = document.getElementById('recep-date');
const elHorloge     = document.getElementById('recep-horloge');

// Steps
const elStep1       = document.getElementById('recep-step-1');
const elStep2       = document.getElementById('recep-step-2');
const elStep3       = document.getElementById('recep-step-3');
const elResultat    = document.getElementById('recep-resultat');

// Step indicators
const elStepInd1    = document.getElementById('step-ind-1');
const elStepInd2    = document.getElementById('step-ind-2');
const elStepInd3    = document.getElementById('step-ind-3');

// Step 1
const elFormEntete  = document.getElementById('form-entete');
const elFournisseur = document.getElementById('rcp-fournisseur');
const elFournLibre  = document.getElementById('rcp-fourn-libre');
const elOperateur   = document.getElementById('rcp-operateur');
const elErreur1     = document.getElementById('recep-erreur-1');

// Step 2
const elRecapEntete = document.getElementById('recep-recap-entete');
const elLignesListe = document.getElementById('recep-lignes-liste');
const elLignesVide  = document.getElementById('recep-lignes-vide');
const elBtnAjouter  = document.getElementById('recep-btn-ajouter');
const elFormLigne   = document.getElementById('form-ligne');
const elBtnAnnulerLigne = document.getElementById('recep-btn-annuler-ligne');
const elBtnNextStep3    = document.getElementById('recep-btn-next-3');
const elBtnBack1    = document.getElementById('recep-btn-back-1');
const elErreur2     = document.getElementById('recep-erreur-2');
const elErreurLigne = document.getElementById('recep-erreur-ligne');

// Step 3
const elRecapFinal  = document.getElementById('recep-recap-final');
const elFormFinal   = document.getElementById('form-final');
const elNcZone      = document.getElementById('recep-nc-zone');
const elBtnBack2    = document.getElementById('recep-btn-back-2');
const elBtnFinaliser    = document.getElementById('recep-btn-finaliser');
const elBtnFinalTexte   = document.getElementById('recep-btn-finaliser-texte');
const elErreur3         = document.getElementById('recep-erreur-3');

// Historique
const elHistoListe  = document.getElementById('recep-histo-liste');

// ── État ──────────────────────────────────────────────────────
let receptionId   = null;     // ID créé en step 1
let etapeActuelle = 1;
let lignes        = [];       // lignes saisies en step 2 (cache local)
let enteteData    = {};       // données step 1 (pour affichage recap)

// ── Horloge / date ────────────────────────────────────────────
function majHorloge() {
  const now = new Date();
  elDate.textContent = now.toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long',
  });
  elHorloge.textContent = now.toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
}
setInterval(majHorloge, 1000);
majHorloge();

// Heure de livraison par défaut
document.getElementById('rcp-heure').value = new Date()
  .toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  .replace(':', ':');

// ── Fetch helper ──────────────────────────────────────────────
async function apiFetch(url, options = {}) {
  const res = await fetch(url, { cache: 'no-store', ...options });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} — ${txt || url}`);
  }
  return res.json();
}

// ── Chargement données ────────────────────────────────────────
async function chargerFournisseurs() {
  try {
    const fourn = await apiFetch('/api/fournisseurs');
    fourn.forEach(f => {
      const opt = document.createElement('option');
      opt.value = f.id;
      opt.textContent = f.nom;
      elFournisseur.appendChild(opt);
    });
  } catch { /* pas bloquant */ }
}

async function chargerPersonnel() {
  try {
    const personnel = await apiFetch('/api/admin/personnel');
    personnel.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.prenom;
      opt.textContent = p.prenom;
      elOperateur.appendChild(opt);
    });
  } catch { /* pas bloquant */ }
}

// ── Historique ────────────────────────────────────────────────
async function chargerHistorique() {
  elHistoListe.innerHTML = '<div class="recep-vide">Chargement…</div>';
  try {
    const receptions = await apiFetch('/api/receptions?limit=20');
    if (!receptions || receptions.length === 0) {
      elHistoListe.innerHTML = '<div class="recep-vide">Aucune réception enregistrée</div>';
      return;
    }
    elHistoListe.innerHTML = receptions.map(r => {
      const date = new Date(r.date_reception).toLocaleDateString('fr-FR', {
        day: '2-digit', month: 'short',
      });
      const conformeCls = r.conforme === 1 ? 'recep-histo-ok'
                        : r.conforme === 0 ? 'recep-histo-nc' : '';
      const conformeLabel = r.conforme === 1 ? '✓' : r.conforme === 0 ? '✗ NC' : '…';
      return `<div class="recep-histo-ligne">
        <div class="recep-histo-main">
          <span class="recep-histo-fourn">${escHtml(r.fournisseur_nom ?? '—')}</span>
          <span class="recep-histo-badge ${conformeCls}">${conformeLabel}</span>
        </div>
        <div class="recep-histo-meta">
          ${date}
          ${r.numero_bon_livraison ? ` · BL ${escHtml(r.numero_bon_livraison)}` : ''}
          · ${r.nb_lignes ?? 0} produit${(r.nb_lignes ?? 0) > 1 ? 's' : ''}
        </div>
      </div>`;
    }).join('');
  } catch {
    elHistoListe.innerHTML = '<div class="recep-vide recep-vide--erreur">⚠ Erreur chargement</div>';
  }
}

// ── Navigation étapes ─────────────────────────────────────────
function allerEtape(n) {
  etapeActuelle = n;
  elStep1.hidden = n !== 1;
  elStep2.hidden = n !== 2;
  elStep3.hidden = n !== 3;
  elResultat.hidden = true;

  // Step indicators
  [elStepInd1, elStepInd2, elStepInd3].forEach((el, i) => {
    el.classList.remove('recep-step--actif', 'recep-step--fait');
    if (i + 1 < n)    el.classList.add('recep-step--fait');
    if (i + 1 === n)  el.classList.add('recep-step--actif');
  });

  // Scroll to top
  document.getElementById('recep-wizard').scrollTop = 0;
}

// ── Étape 1 : Soumission entête ───────────────────────────────
elFormEntete.addEventListener('submit', async (e) => {
  e.preventDefault();
  elErreur1.hidden = true;

  const fournId  = elFournisseur.value;
  const fournLib = elFournLibre.value.trim();
  const operateur = elOperateur.value;

  if (!fournId && !fournLib) {
    afficherErreur(elErreur1, 'Veuillez sélectionner ou saisir un fournisseur.');
    return;
  }
  if (!operateur) {
    afficherErreur(elErreur1, 'Veuillez sélectionner un opérateur.');
    return;
  }

  // Récupérer le nom du fournisseur
  const fournNom = fournLib || elFournisseur.options[elFournisseur.selectedIndex]?.text || '';

  const proprete = document.querySelector('[name="proprete_camion"]:checked')?.value;
  const tempCamion = document.getElementById('rcp-temp-camion').value;
  const heureLiv   = document.getElementById('rcp-heure').value;
  const bl         = document.getElementById('rcp-bl').value.trim();
  const commentaire = document.getElementById('rcp-commentaire-entete').value.trim();

  const payload = {
    fournisseur_id:       fournId ? parseInt(fournId) : null,
    fournisseur_nom:      fournNom,
    numero_bon_livraison: bl || null,
    operateur,
    heure_livraison:      heureLiv || null,
    temperature_camion:   tempCamion ? parseFloat(tempCamion) : null,
    proprete_camion:      proprete || null,
    commentaire:          commentaire || null,
  };

  const btn = elFormEntete.querySelector('[type="submit"]');
  btn.disabled = true;
  btn.textContent = 'Création…';

  try {
    const res = await apiFetch('/api/receptions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    receptionId = res.id;
    enteteData  = { ...payload, id: receptionId };
    lignes      = [];

    afficherRecapEntete();
    afficherLignes();
    allerEtape(2);
  } catch (err) {
    afficherErreur(elErreur1, `Erreur : ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Continuer → Produits';
  }
});

function afficherRecapEntete() {
  const t = enteteData;
  elRecapEntete.innerHTML = `
    <div class="recep-recap-info">
      <span class="recep-recap-fourn">${escHtml(t.fournisseur_nom)}</span>
      ${t.numero_bon_livraison ? `<span class="recep-recap-bl">BL ${escHtml(t.numero_bon_livraison)}</span>` : ''}
      <span class="recep-recap-op">par ${escHtml(t.operateur)}</span>
      ${t.temperature_camion != null ? `<span class="recep-recap-temp">Camion ${t.temperature_camion}°C</span>` : ''}
    </div>`;
}

// ── Étape 2 : Lignes produits ─────────────────────────────────
elBtnAjouter.addEventListener('click', () => {
  elFormLigne.hidden = false;
  elBtnAjouter.hidden = true;
  const premierInput = elFormLigne.querySelector('input[type="text"]');
  if (premierInput) premierInput.focus();
});

elBtnAnnulerLigne.addEventListener('click', () => {
  elFormLigne.reset();
  elFormLigne.hidden = true;
  elBtnAjouter.hidden = false;
  elErreurLigne.hidden = true;
});

elFormLigne.addEventListener('submit', async (e) => {
  e.preventDefault();
  elErreurLigne.hidden = true;

  const nom = document.getElementById('lg-nom').value.trim();
  if (!nom) {
    afficherErreur(elErreurLigne, 'Veuillez saisir le nom du produit.');
    return;
  }

  const tempVal     = document.getElementById('lg-temp').value;
  const dlcVal      = document.getElementById('lg-dlc').value;
  const lotVal      = document.getElementById('lg-lot').value.trim();
  const integrite   = document.querySelector('[name="integrite_emballage"]:checked')?.value;
  const conformeVal = document.querySelector('[name="conforme_ligne"]:checked')?.value;

  const payload = {
    produit_nom:         nom,
    temperature_produit: tempVal ? parseFloat(tempVal) : null,
    dlc:                 dlcVal || null,
    numero_lot:          lotVal || null,
    integrite_emballage: integrite || null,
    conforme:            conformeVal ? conformeVal === 'oui' : null,
  };

  const btn = elFormLigne.querySelector('[type="submit"]');
  btn.disabled = true;
  btn.textContent = 'Ajout…';

  try {
    const res = await apiFetch(`/api/receptions/${receptionId}/lignes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    lignes.push({ ...payload, id: res.id });
    afficherLignes();
    elFormLigne.reset();
    elFormLigne.hidden = true;
    elBtnAjouter.hidden = false;
    elBtnNextStep3.disabled = false;
  } catch (err) {
    afficherErreur(elErreurLigne, `Erreur : ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Ajouter ce produit';
  }
});

function afficherLignes() {
  if (!lignes.length) {
    if (elLignesVide) elLignesVide.hidden = false;
    return;
  }
  if (elLignesVide) elLignesVide.hidden = true;

  elLignesListe.innerHTML = '<div class="recep-vide" id="recep-lignes-vide" hidden></div>'
    + lignes.map((l, i) => {
      const confCls = l.conforme === true ? 'recep-ligne-ok' : l.conforme === false ? 'recep-ligne-nc' : '';
      const confLbl = l.conforme === true ? '✓' : l.conforme === false ? '✗ NC' : '—';
      const dlcLbl  = l.dlc ? new Date(l.dlc).toLocaleDateString('fr-FR', {day:'2-digit',month:'short'}) : null;
      return `<div class="recep-ligne-item ${confCls}" data-idx="${i}">
        <span class="recep-ligne-nom">${escHtml(l.produit_nom)}</span>
        <div class="recep-ligne-meta">
          ${l.temperature_produit != null ? `<span>${l.temperature_produit}°C</span>` : ''}
          ${dlcLbl ? `<span>DLC ${dlcLbl}</span>` : ''}
          ${l.numero_lot ? `<span>${escHtml(l.numero_lot)}</span>` : ''}
          ${l.integrite_emballage ? `<span>Emb. ${l.integrite_emballage}</span>` : ''}
          <span class="recep-ligne-conf">${confLbl}</span>
        </div>
      </div>`;
    }).join('');
}

elBtnBack1.addEventListener('click', () => allerEtape(1));

elBtnNextStep3.addEventListener('click', () => {
  if (!lignes.length) {
    afficherErreur(elErreur2, 'Ajoutez au moins un produit avant de continuer.');
    return;
  }
  afficherRecapFinal();
  allerEtape(3);
});

// ── Étape 3 : Finalisation ────────────────────────────────────
function afficherRecapFinal() {
  const ncCount = lignes.filter(l => l.conforme === false).length;
  elRecapFinal.innerHTML = `
    <div class="recep-recap-final-info">
      <span class="recep-recap-final-fourn">${escHtml(enteteData.fournisseur_nom)}</span>
      <span class="recep-recap-final-stat">${lignes.length} produit${lignes.length > 1 ? 's' : ''}
        ${ncCount > 0 ? `— <strong style="color:var(--alerte)">${ncCount} NC</strong>` : '— tous conformes'}
      </span>
    </div>`;
}

// Afficher/masquer zone NC
document.querySelectorAll('[name="conforme_global"]').forEach(r => {
  r.addEventListener('change', () => {
    elNcZone.hidden = r.value !== 'non';
  });
});

elBtnBack2.addEventListener('click', () => allerEtape(2));

elFormFinal.addEventListener('submit', async (e) => {
  e.preventDefault();
  elErreur3.hidden = true;

  const conformeVal = document.querySelector('[name="conforme_global"]:checked')?.value;
  if (!conformeVal) {
    afficherErreur(elErreur3, 'Veuillez indiquer la conformité globale.');
    return;
  }
  const conforme = conformeVal === 'oui';

  elBtnFinaliser.disabled    = true;
  elBtnFinalTexte.textContent = 'Clôture…';

  try {
    await apiFetch(`/api/receptions/${receptionId}/finaliser`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conforme }),
    });

    // Déclarer NC si nécessaire
    if (!conforme) {
      const natures = [];
      if (document.querySelector('[name="nc_temperature"]')?.checked) natures.push('temperature');
      if (document.querySelector('[name="nc_dlc"]')?.checked)         natures.push('dlc');
      if (document.querySelector('[name="nc_emballage"]')?.checked)   natures.push('emballage');
      if (document.querySelector('[name="nc_aspect"]')?.checked)      natures.push('aspect');
      if (document.querySelector('[name="nc_etiquetage"]')?.checked)  natures.push('etiquetage');
      if (document.querySelector('[name="nc_autre"]')?.checked)       natures.push('autre');

      const ncPayload = {
        reception_id:   receptionId,
        operateur:      enteteData.operateur,
        fournisseur_nom: enteteData.fournisseur_nom,
        nature_nc:      natures.length > 0 ? natures : null,
        commentaires:   document.getElementById('rcp-nc-commentaire')?.value.trim() || null,
        refuse_livraison: document.querySelector('[name="nc_refuse"]')?.checked ?? false,
        info_ddpp:      document.querySelector('[name="nc_ddpp"]')?.checked ?? false,
      };

      await apiFetch('/api/non-conformites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ncPayload),
      }).catch(() => {}); // NC non bloquante
    }

    // Afficher résultat
    afficherResultat(conforme);
    allerEtape(99); // cache tous les steps
    elResultat.hidden = false;
    chargerHistorique();
  } catch (err) {
    afficherErreur(elErreur3, `Erreur : ${err.message}`);
    elBtnFinaliser.disabled    = false;
    elBtnFinalTexte.textContent = '✓ Clôturer la fiche';
  }
});

function afficherResultat(conforme) {
  const cls    = conforme ? 'recep-resultat--ok' : 'recep-resultat--nc';
  const titre  = conforme ? '✅ Réception conforme enregistrée' : '⚠ Réception NC enregistrée';
  const detail = `${enteteData.fournisseur_nom} — ${lignes.length} produit${lignes.length > 1 ? 's' : ''}`;

  elResultat.innerHTML = `
    <div class="recep-resultat-boite ${cls}">
      <div class="recep-resultat-titre">${titre}</div>
      <div class="recep-resultat-detail">${escHtml(detail)}</div>
      <div class="recep-resultat-actions">
        <button type="button" onclick="nouvelleReception()" class="btn-valider" style="background:var(--brun)">
          ＋ Nouvelle réception
        </button>
        <a href="/hub.html" class="btn-outline" style="display:inline-flex;align-items:center;text-decoration:none">
          ← Retour Hub
        </a>
      </div>
    </div>`;
}

function nouvelleReception() {
  receptionId   = null;
  lignes        = [];
  enteteData    = {};
  elFormEntete.reset();
  elFormLigne.reset();
  elFormFinal.reset();
  elFormLigne.hidden = true;
  elBtnAjouter.hidden = false;
  elBtnNextStep3.disabled = true;
  elNcZone.hidden = true;
  document.getElementById('rcp-heure').value = new Date()
    .toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  allerEtape(1);
}

// Exposer globalement pour le bouton inline
window.nouvelleReception = nouvelleReception;

// ── Helpers ───────────────────────────────────────────────────
function afficherErreur(el, msg) {
  el.textContent = msg;
  el.hidden = false;
}

function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Refresh historique ────────────────────────────────────────
document.getElementById('recep-refresh-histo').addEventListener('click', chargerHistorique);

// ── Init ──────────────────────────────────────────────────────
async function init() {
  await Promise.all([chargerFournisseurs(), chargerPersonnel(), chargerHistorique()]);
}

init();

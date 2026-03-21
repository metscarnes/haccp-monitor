/**
 * dashboard.js — Logique principale du dashboard HACCP
 *
 * Architecture :
 *   - Polling API toutes les 30s (pas de WebSocket pour rester simple)
 *   - État global minimal, pas de framework
 *   - 4 vues : dashboard | historique | alertes | rapports
 */

const API    = '';          // même origine — vide = relatif
const BOUTIQUE_ID = 1;      // phase 1 : une seule boutique
const POLL_MS     = 30_000; // intervalle de rafraîchissement

// Mini-charts en cours (pour les détruire avant mise à jour)
const miniCharts = {};
let chartHistorique = null;
let pollTimer = null;

// ---------------------------------------------------------------------------
// Utilitaires
// ---------------------------------------------------------------------------

async function apiFetch(path) {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${path}`);
  return res.json();
}

function fmt(val, decimales = 1) {
  return val != null ? Number(val).toFixed(decimales) : '—';
}

function fmtDateHeure(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
}

function fmtDuree(isoDebut) {
  if (!isoDebut) return '';
  const delta = Math.floor((Date.now() - new Date(isoDebut)) / 1000);
  if (delta < 60)   return `${delta}s`;
  if (delta < 3600) return `${Math.floor(delta/60)}min`;
  return `${Math.floor(delta/3600)}h${String(Math.floor((delta%3600)/60)).padStart(2,'0')}`;
}

function statutLabel(statut) {
  return { ok: 'OK', attention: 'Attention', alerte: 'Alerte', hors_ligne: 'Hors ligne', inconnu: '—' }[statut] ?? statut;
}

function typeAlerteLabel(type) {
  return {
    temperature_haute: '🌡️ Température trop haute',
    temperature_basse: '❄️ Température trop basse',
    perte_signal:      '📡 Perte de signal',
    batterie_faible:   '🪫 Batterie faible',
  }[type] ?? type;
}

// ---------------------------------------------------------------------------
// Navigation entre vues
// ---------------------------------------------------------------------------

const VUES = ['dashboard', 'historique', 'alertes', 'rapports', 'configuration'];

function afficherVue(nom) {
  VUES.forEach(v => {
    const el = document.getElementById(`vue-${v}`);
    const flexVues = ['dashboard', 'configuration'];
    el.style.display = v !== nom ? 'none' : (flexVues.includes(v) ? 'flex' : 'block');
  });
  document.querySelectorAll('nav button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.vue === nom);
  });

  // Chargements spécifiques à chaque vue
  if (nom === 'historique')    chargerSelectEnceinteHistorique();
  if (nom === 'alertes')       chargerAlertes();
  if (nom === 'rapports')      chargerRapports();
  if (nom === 'configuration') chargerConfigEnceintes();
}

document.querySelectorAll('nav button').forEach(btn => {
  btn.addEventListener('click', () => afficherVue(btn.dataset.vue));
});

// ---------------------------------------------------------------------------
// VUE DASHBOARD
// ---------------------------------------------------------------------------

async function chargerDashboard() {
  try {
    const data = await apiFetch(`/api/boutiques/${BOUTIQUE_ID}/dashboard`);
    renderDashboard(data);
  } catch (e) {
    console.error('Erreur dashboard :', e);
  }
}

function renderDashboard(data) {
  // Statut global
  const sg = document.getElementById('statut-global');
  sg.textContent  = statutLabel(data.boutique.statut);
  sg.className    = data.boutique.statut;

  // Bandeau alerte
  const ba = document.getElementById('bandeau-alerte');
  const alertesActives = data.enceintes.filter(e => e.statut === 'alerte');
  if (alertesActives.length) {
    ba.textContent = `⚠️  ${alertesActives.length} alerte(s) en cours — ${alertesActives.map(e => e.nom).join(', ')}`;
    ba.classList.add('visible');
  } else {
    ba.classList.remove('visible');
  }

  // Cartes enceintes
  const container = document.getElementById('vue-dashboard');
  container.innerHTML = '';

  data.enceintes.forEach(enc => {
    const card = document.createElement('div');
    card.className = `carte-enceinte ${enc.statut}`;
    card.dataset.id = enc.id;

    const alerteHtml = enc.alerte_en_cours ? `
      <div class="alerte-detail">
        ${typeAlerteLabel(enc.alerte_en_cours.type)} — depuis ${fmtDuree(enc.alerte_en_cours.debut)}
      </div>` : '';

    const batPct  = enc.batterie_sonde ?? 0;
    const batFill = Math.max(0, Math.min(100, batPct));
    const batColor = batPct < 20 ? '#C93030' : batPct < 40 ? '#E8913A' : '#2D7D46';

    card.innerHTML = `
      <div class="carte-en-tete">
        <div>
          <div class="carte-nom">${enc.nom}</div>
          <div class="carte-type">${enc.type.replace(/_/g, ' ')}</div>
        </div>
        <span class="badge-statut ${enc.statut}">${statutLabel(enc.statut)}</span>
      </div>
      ${alerteHtml}
      <div class="temp-principale">
        ${enc.temperature_actuelle != null ? fmt(enc.temperature_actuelle) : '—'}
        <span class="unite">°C</span>
      </div>
      <div class="humidite">Humidité : ${fmt(enc.humidite_actuelle)}%</div>
      <div class="mini-chart-wrap vide" id="wrap-chart-${enc.id}">
        <canvas id="mini-chart-${enc.id}"></canvas>
      </div>
      <div class="carte-meta">
        <span>
          <span class="batterie-icone" style="color:${batColor}">
            <span class="fill" style="width:${batFill}%"></span>
          </span>
          ${enc.batterie_sonde != null ? enc.batterie_sonde + '%' : '—'}
        </span>
        <span>Mis à jour ${fmtDateHeure(enc.derniere_mesure)}</span>
      </div>`;

    card.style.cursor = 'pointer';
    card.addEventListener('click', () => forerVersHistorique(enc.id));

    container.appendChild(card);

    // Mini chart : charger les dernières 24h
    chargerMiniChart(enc);
  });
}

async function forerVersHistorique(encId) {
  afficherVue('historique');
  await chargerSelectEnceinteHistorique();
  document.getElementById('select-enceinte-historique').value = encId;
  document.getElementById('select-periode').value = '24h';
  document.getElementById('dates-custom').style.display = 'none';
  chargerHistorique();
}

async function chargerMiniChart(enc) {
  try {
    const data = await apiFetch(
      `/api/enceintes/${enc.id}/releves?periode=24h`
    );
    const canvas = document.getElementById(`mini-chart-${enc.id}`);
    if (!canvas) return;

    if (miniCharts[enc.id]) miniCharts[enc.id].destroy();

    const temps = data.releves.map(r => r.temperature);
    if (temps.length === 0) return;

    const wrap = document.getElementById(`wrap-chart-${enc.id}`);
    if (wrap) wrap.classList.remove('vide');

    miniCharts[enc.id] = creerMiniChart(canvas, temps, enc.seuil_min, enc.seuil_max);
  } catch (e) {
    // silencieux — le mini chart n'est pas critique
  }
}

// ---------------------------------------------------------------------------
// VUE HISTORIQUE
// ---------------------------------------------------------------------------

let enceintesCachees = [];

async function chargerSelectEnceinteHistorique() {
  if (enceintesCachees.length) return; // déjà chargé
  try {
    enceintesCachees = await apiFetch(`/api/boutiques/${BOUTIQUE_ID}/enceintes`);
    const sel = document.getElementById('select-enceinte-historique');
    sel.innerHTML = enceintesCachees.map(e =>
      `<option value="${e.id}" data-min="${e.seuil_temp_min}" data-max="${e.seuil_temp_max}">${e.nom}</option>`
    ).join('');
  } catch (e) {
    console.error('Erreur chargement enceintes :', e);
  }
}

document.getElementById('select-periode').addEventListener('change', function () {
  document.getElementById('dates-custom').style.display =
    this.value === 'custom' ? 'flex' : 'none';
});

document.getElementById('btn-charger-historique').addEventListener('click', chargerHistorique);

async function chargerHistorique() {
  const sel      = document.getElementById('select-enceinte-historique');
  const opt      = sel.options[sel.selectedIndex];
  const eid      = sel.value;
  const seuilMin = parseFloat(opt.dataset.min);
  const seuilMax = parseFloat(opt.dataset.max);
  const periode  = document.getElementById('select-periode').value;

  let url = `/api/enceintes/${eid}/releves?`;
  if (periode !== 'custom') {
    url += `periode=${periode}`;
  } else {
    const debut = document.getElementById('date-debut').value;
    const fin   = document.getElementById('date-fin').value;
    if (!debut || !fin) { alert('Sélectionne les deux dates.'); return; }
    url += `from=${debut}T00:00:00Z&to=${fin}T23:59:59Z`;
  }

  try {
    const data = await apiFetch(url);
    document.getElementById('titre-chart-historique').textContent =
      `${opt.text} — ${data.nb_releves} relevés`;

    // Stats
    const statsData = await apiFetch(url.replace('/releves?', '/releves/stats?'));
    renderStats(statsData, seuilMin, seuilMax);

    // Chart
    const canvas = document.getElementById('chart-historique');
    detruireChart(chartHistorique);
    chartHistorique = creerChartHistorique(canvas, data.releves, seuilMin, seuilMax);

    // Tableau agrégé
    renderTableauHistorique(data.releves, periode, seuilMin, seuilMax);
  } catch (e) {
    console.error('Erreur historique :', e);
    alert('Erreur lors du chargement des données.');
  }
}

function renderStats(stats, seuilMin, seuilMax) {
  const bande = document.getElementById('stats-bande');
  if (!stats.temp_min) { bande.innerHTML = ''; return; }

  const couleurMin = stats.temp_min < seuilMin ? 'var(--alerte)' : 'var(--noyer)';
  const couleurMax = stats.temp_max > seuilMax ? 'var(--alerte)' : 'var(--noyer)';

  bande.innerHTML = `
    <div class="stat-box">
      <div class="val" style="color:${couleurMin}">${fmt(stats.temp_min)}°C</div>
      <div class="lbl">Température min</div>
    </div>
    <div class="stat-box">
      <div class="val">${fmt(stats.temp_moy)}°C</div>
      <div class="lbl">Température moyenne</div>
    </div>
    <div class="stat-box">
      <div class="val" style="color:${couleurMax}">${fmt(stats.temp_max)}°C</div>
      <div class="lbl">Température max</div>
    </div>
    <div class="stat-box">
      <div class="val">${fmt(stats.hum_moy)}%</div>
      <div class="lbl">Humidité moyenne</div>
    </div>
    <div class="stat-box">
      <div class="val">${stats.nb_releves}</div>
      <div class="lbl">Relevés</div>
    </div>`;
}

function renderTableauHistorique(releves, periode, seuilMin, seuilMax) {
  const wrap  = document.getElementById('tableau-historique-wrap');
  const titre = document.getElementById('tableau-historique-titre');
  const table = document.getElementById('tableau-historique');

  if (!releves.length) { wrap.style.display = 'none'; return; }

  // Clé de regroupement selon la période
  const parHeure = periode === '24h';
  const clef = r => {
    const d = new Date(r.horodatage);
    return parHeure
      ? `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}h`
      : `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  };

  // Agrégation
  const groupes = {};
  releves.forEach(r => {
    const k = clef(r);
    if (!groupes[k]) groupes[k] = { temps: [], humids: [] };
    if (r.temperature != null) groupes[k].temps.push(r.temperature);
    if (r.humidite    != null) groupes[k].humids.push(r.humidite);
  });

  const lignes = Object.entries(groupes).map(([k, g]) => {
    const tMin = Math.min(...g.temps);
    const tMax = Math.max(...g.temps);
    const tMoy = g.temps.reduce((a, b) => a + b, 0) / g.temps.length;
    const hMoy = g.humids.length ? g.humids.reduce((a, b) => a + b, 0) / g.humids.length : null;
    const conforme = tMin >= seuilMin && tMax <= seuilMax;
    return { k, tMin, tMax, tMoy, hMoy, conforme, n: g.temps.length };
  });

  titre.textContent = parHeure ? 'Relevés par heure' : 'Relevés par jour';

  table.innerHTML = `
    <thead><tr>
      <th>${parHeure ? 'Heure' : 'Date'}</th>
      <th>T° min</th>
      <th>T° moy</th>
      <th>T° max</th>
      <th>Humidité moy</th>
      <th>Relevés</th>
      <th>Conformité</th>
    </tr></thead>
    <tbody>
      ${lignes.map(l => `
        <tr>
          <td>${l.k}</td>
          <td class="${l.tMin < seuilMin ? 'val-alerte' : ''}">${fmt(l.tMin)}°C</td>
          <td>${fmt(l.tMoy)}°C</td>
          <td class="${l.tMax > seuilMax ? 'val-alerte' : ''}">${fmt(l.tMax)}°C</td>
          <td>${l.hMoy != null ? fmt(l.hMoy) + '%' : '—'}</td>
          <td>${l.n}</td>
          <td class="${l.conforme ? 'conforme' : 'non-conforme'}">${l.conforme ? '✓ Conforme' : '✗ Hors seuil'}</td>
        </tr>`).join('')}
    </tbody>`;

  wrap.style.display = 'block';
}

document.getElementById('btn-exporter-csv').addEventListener('click', () => {
  const eid    = document.getElementById('select-enceinte-historique').value;
  const periode = document.getElementById('select-periode').value;
  if (!eid) return;
  let url = `/api/enceintes/${eid}/releves/export.csv?`;
  if (periode !== 'custom') {
    url += `periode=${periode}`;
  } else {
    const debut = document.getElementById('date-debut').value;
    const fin   = document.getElementById('date-fin').value;
    url += `from=${debut}T00:00:00Z&to=${fin}T23:59:59Z`;
  }
  window.location.href = url;
});

// ---------------------------------------------------------------------------
// VUE ALERTES
// ---------------------------------------------------------------------------

async function chargerAlertes() {
  const afficherFermees = document.getElementById('toggle-historique-alertes').checked;
  const conteneur = document.getElementById('liste-alertes');
  conteneur.innerHTML = '<div class="spinner"></div>';

  try {
    // Alertes en cours
    let alertes = await apiFetch('/api/alertes/en-cours');

    // Si on veut aussi les fermées, on charge par enceinte
    if (afficherFermees && enceintesCachees.length) {
      const promises = enceintesCachees.map(e =>
        apiFetch(`/api/enceintes/${e.id}/alertes`)
      );
      const resultats = await Promise.all(promises);
      const fermees = resultats.flat().filter(a => a.fin !== null);
      alertes = [...alertes, ...fermees].sort((a, b) =>
        new Date(b.debut) - new Date(a.debut)
      );
    }

    if (!alertes.length) {
      conteneur.innerHTML = '<p style="color:var(--brun); padding:1rem">Aucune alerte.</p>';
      return;
    }

    conteneur.innerHTML = alertes.map(a => {
      const enCours = !a.fin;
      return `
      <div class="alerte-ligne ${enCours ? 'en-cours' : 'fermee'}">
        <span class="alerte-icone">${enCours ? '🔴' : '✅'}</span>
        <div class="alerte-info">
          <strong>${typeAlerteLabel(a.type)}</strong>
          <p>
            ${a.boutique_nom ? a.boutique_nom + ' — ' : ''}${a.enceinte_nom || `Enceinte #${a.enceinte_id}`}
            · Valeur : ${fmt(a.valeur)} · Seuil : ${fmt(a.seuil)}
          </p>
          <p>Début : ${fmtDateHeure(a.debut)}${a.fin ? ' · Fin : ' + fmtDateHeure(a.fin) : ''}</p>
        </div>
        <div class="alerte-duree">
          ${enCours ? fmtDuree(a.debut) : ''}
        </div>
      </div>`;
    }).join('');
  } catch (e) {
    conteneur.innerHTML = '<p style="color:var(--alerte)">Erreur de chargement.</p>';
  }
}

document.getElementById('toggle-historique-alertes').addEventListener('change', chargerAlertes);

// ---------------------------------------------------------------------------
// VUE RAPPORTS
// ---------------------------------------------------------------------------

async function chargerRapports() {
  const conteneur = document.getElementById('liste-rapports');
  conteneur.innerHTML = '<div class="spinner"></div>';
  try {
    const rapports = await apiFetch(`/api/rapports?boutique_id=${BOUTIQUE_ID}`);
    if (!rapports.length) {
      conteneur.innerHTML = '<p style="color:var(--brun); padding:1rem">Aucun rapport généré.</p>';
      return;
    }
    conteneur.innerHTML = rapports.map(r => `
      <div class="rapport-ligne">
        <div>
          <strong>${r.type.charAt(0).toUpperCase() + r.type.slice(1)}</strong>
          — ${r.date_debut} → ${r.date_fin}
          <br><span style="font-size:.75rem; color:#888">Généré le ${fmtDateHeure(r.created_at)}</span>
        </div>
        <span class="${r.conforme ? 'conforme' : 'non-conforme'}">
          ${r.conforme ? '✅ Conforme' : '❌ Non conforme'}
        </span>
        ${r.fichier_path
          ? `<a class="btn btn-secondaire" href="/api/rapports/${r.id}/pdf" target="_blank">📄 PDF</a>`
          : '<span style="color:#aaa; font-size:.8rem">PDF indisponible</span>'}
      </div>`).join('');
  } catch (e) {
    conteneur.innerHTML = '<p style="color:var(--alerte)">Erreur de chargement.</p>';
  }
}

// Préremplir les dates du formulaire rapport
(function() {
  const aujourd_hui = new Date().toISOString().slice(0, 10);
  const hier = new Date(Date.now() - 864e5).toISOString().slice(0, 10);
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
  set('rapport-date-debut', hier);
  set('rapport-date-fin',   hier);
  set('csv-date',           hier);
  set('date-debut',         hier);
  set('date-fin',           aujourd_hui);
})();

// ---------------------------------------------------------------------------
// RAPPORT CSV PAR JOUR
// ---------------------------------------------------------------------------

document.getElementById('btn-charger-csv').addEventListener('click', async () => {
  const btn  = document.getElementById('btn-charger-csv');
  const jour = document.getElementById('csv-date').value;
  const zone = document.getElementById('csv-rapport-resultat');

  if (!jour) { alert('Choisissez une date.'); return; }

  btn.disabled = true;
  btn.textContent = 'Chargement…';
  zone.innerHTML = '<div class="spinner"></div>';

  try {
    const data = await apiFetch(`/api/rapports/csv/rapport/${jour}`);

    if (!data.sondes || !data.sondes.length) {
      zone.innerHTML = `<p style="color:var(--brun); padding:1rem 0">Aucun CSV disponible pour le ${jour}.</p>`;
      return;
    }

    zone.innerHTML = `
      <div class="csv-rapport-grille">
        ${data.sondes.map(s => {
          const conforme = s.temp_max <= 4;  // indicateur visuel simple
          return `
          <div class="csv-rapport-carte">
            <div class="csv-carte-entete">
              <strong>${s.sonde.replace(/_/g, ' ')}</strong>
              <span class="badge ${s.temp_max > 4 ? 'badge-alerte' : 'badge-ok'}">
                ${s.temp_max > 4 ? 'Hors seuil' : 'Conforme'}
              </span>
            </div>
            <div class="csv-carte-stats">
              <div><span class="csv-stat-label">Min</span><span class="csv-stat-val">${s.temp_min} °C</span></div>
              <div><span class="csv-stat-label">Moy</span><span class="csv-stat-val">${s.temp_moy} °C</span></div>
              <div><span class="csv-stat-label">Max</span><span class="csv-stat-val csv-stat-max ${s.temp_max > 4 ? 'csv-hors-seuil' : ''}">${s.temp_max} °C</span></div>
              ${s.hum_min !== null ? `<div><span class="csv-stat-label">Hum.</span><span class="csv-stat-val">${s.hum_min}–${s.hum_max} %</span></div>` : ''}
              <div><span class="csv-stat-label">Relevés</span><span class="csv-stat-val">${s.nb_releves}</span></div>
            </div>
            <a class="btn btn-secondaire csv-dl-btn"
               href="/api/rapports/csv/telecharger/${encodeURIComponent(s.sonde)}/${jour}"
               download="${s.fichier}">
              ⬇ Télécharger CSV
            </a>
          </div>`;
        }).join('')}
      </div>`;
  } catch (e) {
    zone.innerHTML = `<p style="color:#c00; padding:.5rem 0">Erreur : ${e.message}</p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Charger';
  }
});

document.getElementById('btn-generer-rapport').addEventListener('click', async () => {
  const btn = document.getElementById('btn-generer-rapport');
  btn.disabled = true;
  btn.textContent = 'Génération…';
  try {
    const body = {
      boutique_id: BOUTIQUE_ID,
      type:        document.getElementById('select-type-rapport').value,
      date_debut:  document.getElementById('rapport-date-debut').value,
      date_fin:    document.getElementById('rapport-date-fin').value,
    };
    const res = await fetch('/api/rapports/generer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    await chargerRapports();
  } catch (e) {
    alert('Erreur lors de la génération : ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Générer le rapport';
  }
});

// ---------------------------------------------------------------------------
// VUE CONFIGURATION
// ---------------------------------------------------------------------------

let enceinteEnEdition = null; // null = mode création, id = mode édition

async function chargerConfigEnceintes() {
  const conteneur = document.getElementById('liste-config-enceintes');
  conteneur.innerHTML = '<div class="spinner"></div>';
  try {
    const enceintes = await apiFetch(`/api/boutiques/${BOUTIQUE_ID}/enceintes`);
    if (!enceintes.length) {
      conteneur.innerHTML = '<p style="color:var(--brun); padding:.5rem 0">Aucune enceinte configurée.</p>';
      return;
    }
    conteneur.innerHTML = enceintes.map(e => `
      <div class="config-enceinte-ligne" data-id="${e.id}">
        <div class="config-enceinte-info">
          <strong>${e.nom}</strong>
          <span class="config-enceinte-type">${e.type.replace(/_/g, ' ')}</span>
        </div>
        <div class="config-enceinte-seuils">
          T° : ${e.seuil_temp_min ?? '—'}°C → ${e.seuil_temp_max ?? '—'}°C
          · Hum. max : ${e.seuil_hum_max ?? '—'}%
        </div>
        <button class="btn btn-secondaire btn-sm btn-editer-enceinte" data-id="${e.id}">Modifier</button>
      </div>`).join('');

    conteneur.querySelectorAll('.btn-editer-enceinte').forEach(btn => {
      btn.addEventListener('click', () => chargerEditionEnceinte(parseInt(btn.dataset.id)));
    });
  } catch (e) {
    conteneur.innerHTML = '<p style="color:var(--alerte)">Erreur de chargement.</p>';
  }
}

async function chargerEditionEnceinte(id) {
  try {
    const enc = await apiFetch(`/api/enceintes/${id}`);
    enceinteEnEdition = id;

    document.getElementById('enc-nom').value       = enc.nom ?? '';
    document.getElementById('enc-type').value      = enc.type ?? '';
    document.getElementById('enc-sonde').value     = enc.sonde_zigbee_id ?? '';
    document.getElementById('enc-temp-min').value  = enc.seuil_temp_min ?? 0;
    document.getElementById('enc-temp-max').value  = enc.seuil_temp_max ?? 4;
    document.getElementById('enc-hum-max').value   = enc.seuil_hum_max ?? 90;
    document.getElementById('enc-delai').value     = enc.delai_alerte_minutes ?? 5;

    document.querySelector('.config-titre').textContent = `Modifier l'enceinte`;
    document.getElementById('btn-sauver-enceinte').textContent = 'Enregistrer les modifications';
    document.getElementById('btn-annuler-enceinte').style.display = '';

    document.getElementById('form-enceinte').scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    afficherMsgConfig('Erreur lors du chargement de l\'enceinte.', 'erreur');
  }
}

function resetFormEnceinte() {
  enceinteEnEdition = null;
  document.getElementById('form-enceinte').reset();
  document.getElementById('enc-temp-min').value = 0;
  document.getElementById('enc-temp-max').value = 4;
  document.getElementById('enc-hum-max').value  = 90;
  document.getElementById('enc-delai').value    = 5;
  document.querySelector('.config-titre').textContent = 'Ajouter une enceinte';
  document.getElementById('btn-sauver-enceinte').textContent = 'Ajouter l\'enceinte';
  document.getElementById('btn-annuler-enceinte').style.display = 'none';
  afficherMsgConfig('', '');
}

function afficherMsgConfig(texte, type) {
  const el = document.getElementById('config-msg');
  if (!texte) { el.style.display = 'none'; return; }
  el.textContent  = texte;
  el.className    = `config-msg config-msg-${type}`;
  el.style.display = '';
}

document.getElementById('form-enceinte').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('btn-sauver-enceinte');
  btn.disabled = true;

  const payload = {
    nom:                    document.getElementById('enc-nom').value.trim(),
    type:                   document.getElementById('enc-type').value,
    sonde_zigbee_id:        document.getElementById('enc-sonde').value.trim() || null,
    seuil_temp_min:         parseFloat(document.getElementById('enc-temp-min').value),
    seuil_temp_max:         parseFloat(document.getElementById('enc-temp-max').value),
    seuil_hum_max:          parseFloat(document.getElementById('enc-hum-max').value),
    delai_alerte_minutes:   parseInt(document.getElementById('enc-delai').value),
  };

  try {
    if (enceinteEnEdition) {
      // Mise à jour
      const res = await fetch(`/api/enceintes/${enceinteEnEdition}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      afficherMsgConfig('Enceinte mise à jour avec succès.', 'ok');
    } else {
      // Création
      const res = await fetch('/api/enceintes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, boutique_id: BOUTIQUE_ID }),
      });
      if (!res.ok) throw new Error(await res.text());
      afficherMsgConfig('Enceinte ajoutée avec succès.', 'ok');
    }
    resetFormEnceinte();
    // Vider le cache enceintes pour forcer le rechargement
    enceintesCachees = [];
    chargerConfigEnceintes();
  } catch (err) {
    afficherMsgConfig('Erreur : ' + err.message, 'erreur');
  } finally {
    btn.disabled = false;
  }
});

document.getElementById('btn-annuler-enceinte').addEventListener('click', resetFormEnceinte);

// ---------------------------------------------------------------------------
// Démarrage + polling
// ---------------------------------------------------------------------------

function demarrerPolling() {
  chargerDashboard();
  pollTimer = setInterval(() => {
    // Ne rafraîchir le dashboard que si on est sur cet onglet
    const dashboardVisible =
      document.getElementById('vue-dashboard').style.display !== 'none';
    if (dashboardVisible) chargerDashboard();
  }, POLL_MS);
}

// Initialisation
afficherVue('dashboard');
demarrerPolling();

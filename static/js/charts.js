/**
 * charts.js — Helpers Chart.js pour HACCP Monitor
 * Dépendance : Chart.js + adapter date-fns (chargés avant via CDN)
 */

const COULEURS = {
  ok:        '#2D7D46',
  attention: '#E8913A',
  alerte:    '#C93030',
  brun:      '#6B3A1F',
  creme:     '#D4A574',
  noyer:     '#3D2008',
  humidite:  '#4A90C4',
};

Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
Chart.defaults.color = '#6B3A1F';

/**
 * Mini sparkline pour les cartes dashboard (dernières 24h)
 * @param {HTMLCanvasElement} canvas
 * @param {number[]} temperatures  — tableau de valeurs
 * @param {number} seuilMin
 * @param {number} seuilMax
 * @returns {Chart}
 */
function creerMiniChart(canvas, temperatures, seuilMin, seuilMax) {
  // Déterminer la couleur selon si on dépasse
  const horsLimite = temperatures.some(t => t < seuilMin || t > seuilMax);
  const couleur = horsLimite ? COULEURS.alerte : COULEURS.ok;

  return new Chart(canvas, {
    type: 'line',
    data: {
      labels: temperatures.map((_, i) => i),
      datasets: [{
        data: temperatures,
        borderColor: couleur,
        borderWidth: 1.5,
        fill: true,
        backgroundColor: couleur + '22',
        pointRadius: 0,
        tension: 0.3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: {
        x: { display: false },
        y: {
          display: false,
          min: seuilMin - 1,
          max: seuilMax + 2,
        },
      },
    },
  });
}

/**
 * Graphique historique complet (vue historique)
 * @param {HTMLCanvasElement} canvas
 * @param {Array} releves   — [{horodatage, temperature, humidite}]
 * @param {number} seuilMin
 * @param {number} seuilMax
 * @returns {Chart}
 */
function creerChartHistorique(canvas, releves, seuilMin, seuilMax) {
  const labels = releves.map(r => new Date(r.horodatage));
  const temps   = releves.map(r => r.temperature);
  const humids  = releves.map(r => r.humidite);

  // Colorer les points hors seuil
  const pointColors = temps.map(t =>
    (t > seuilMax || t < seuilMin) ? COULEURS.alerte : COULEURS.ok
  );

  return new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Température (°C)',
          data: temps,
          borderColor: COULEURS.brun,
          backgroundColor: COULEURS.brun + '15',
          borderWidth: 2,
          fill: true,
          tension: 0.2,
          pointRadius: releves.length < 100 ? 3 : 0,
          pointBackgroundColor: pointColors,
          yAxisID: 'yTemp',
        },
        {
          label: 'Humidité (%)',
          data: humids,
          borderColor: COULEURS.humidite,
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          borderDash: [4, 3],
          fill: false,
          tension: 0.2,
          pointRadius: 0,
          yAxisID: 'yHum',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top', labels: { boxWidth: 12, font: { size: 12 } } },
        tooltip: {
          callbacks: {
            title: items => {
              const d = new Date(items[0].label);
              return d.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
            },
            label: item => {
              const unite = item.datasetIndex === 0 ? '°C' : '%';
              return ` ${item.dataset.label} : ${item.parsed.y?.toFixed(1)}${unite}`;
            },
          },
        },
        annotation: {}, // réservé pour futurs marqueurs
      },
      scales: {
        x: {
          type: 'time',
          time: { tooltipFormat: 'dd/MM HH:mm', displayFormats: { hour: 'HH:mm', day: 'dd/MM' } },
          ticks: { maxTicksLimit: 10, font: { size: 11 } },
          grid: { color: '#e8ddd0' },
        },
        yTemp: {
          type: 'linear',
          position: 'left',
          title: { display: true, text: 'Température (°C)', font: { size: 11 } },
          grid: { color: '#e8ddd0' },
          ticks: { font: { size: 11 } },
          // Lignes de seuil
          afterDataLimits(scale) {
            scale.min = Math.min(scale.min, seuilMin - 1);
            scale.max = Math.max(scale.max, seuilMax + 1);
          },
        },
        yHum: {
          type: 'linear',
          position: 'right',
          title: { display: true, text: 'Humidité (%)', font: { size: 11 } },
          min: 0, max: 100,
          grid: { drawOnChartArea: false },
          ticks: { font: { size: 11 } },
        },
      },
      // Lignes de seuil superposées
      plugins2: {},
    },
    plugins: [{
      id: 'seuils',
      afterDraw(chart) {
        const { ctx, chartArea: { left, right }, scales: { yTemp } } = chart;
        if (!yTemp) return;
        [[seuilMax, COULEURS.alerte], [seuilMin, COULEURS.attention]].forEach(([val, couleur]) => {
          const y = yTemp.getPixelForValue(val);
          ctx.save();
          ctx.strokeStyle = couleur;
          ctx.lineWidth   = 1.5;
          ctx.setLineDash([6, 4]);
          ctx.beginPath();
          ctx.moveTo(left, y);
          ctx.lineTo(right, y);
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.fillStyle = couleur;
          ctx.font = '11px Segoe UI, sans-serif';
          ctx.fillText(`Seuil ${val > 0 ? 'max' : 'min'} ${val}°C`, left + 4, y - 4);
          ctx.restore();
        });
      },
    }],
  });
}

/**
 * Détruit un chart existant proprement avant d'en créer un nouveau.
 * @param {Chart|null} chart
 */
function detruireChart(chart) {
  if (chart) chart.destroy();
}

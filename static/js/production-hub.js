'use strict';
/* ============================================================
   production-hub.js — Page intermédiaire Production
   Sous-modules : Fabrication, Cuisson, Refroidissement
   ============================================================ */

const elHorloge = document.getElementById('hub-horloge');

function majHorloge() {
  const now  = new Date();
  const date = now.toLocaleDateString('fr-FR', {
    weekday: 'short', day: 'numeric', month: 'long',
  });
  const heure = now.toLocaleTimeString('fr-FR', {
    hour: '2-digit', minute: '2-digit',
  });
  elHorloge.textContent = `${date} — ${heure}`;
}
setInterval(majHorloge, 1000);
majHorloge();

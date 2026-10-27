/**
 * verrou-admin.js — Page réservée au mot de passe ADMINISTRATEUR (CA, marge, stock valorisé).
 *
 * À inclure dans le <head>, AVANT les scripts de la page (pas de defer) :
 *     <script src="/static/js/core/verrou-admin.js"></script>
 *
 * - À l'ouverture, un écran demande le mot de passe administrateur et cache la page.
 * - Le serveur remet une autorisation de 15 min (gardée pour l'onglet seulement) ;
 *   au bout de 15 min l'écran revient : les chiffres ne restent pas affichés
 *   sur la tablette partagée.
 * - Les appels fetch() vers les API verrouillées attendent le déverrouillage puis
 *   présentent l'autorisation (en-tête X-Jeton-Admin) : le code des pages n'a pas
 *   à s'en occuper. Le verrou réel est côté serveur (main.py).
 */
(function () {
  'use strict';

  var VERROU = 'pilotage';
  var PREFIXES = ['/api/achats/pilotage/', '/api/inventaire/'];
  var CLE = 'verrou_admin_' + VERROU;

  var jeton = null;
  var minuteur = null;
  var ouvrir;                       // résout `pret` une fois déverrouillé
  var pret = new Promise(function (res) { ouvrir = res; });

  function lireJeton() {
    try {
      var j = JSON.parse(sessionStorage.getItem(CLE) || 'null');
      if (j && j.exp > Date.now() + 5000) return j;
    } catch (e) { /* stockage indisponible */ }
    return null;
  }

  function memoriser(valeur, exp) {
    jeton = valeur;
    try { sessionStorage.setItem(CLE, JSON.stringify({ jeton: valeur, exp: exp })); } catch (e) {}
    clearTimeout(minuteur);
    minuteur = setTimeout(reverrouiller, Math.max(0, exp - Date.now()));
    ouvrir();
    if (ecran) ecran.hidden = true;
    document.documentElement.classList.remove('verrou-admin-ferme');
  }

  function reverrouiller() {
    jeton = null;
    try { sessionStorage.removeItem(CLE); } catch (e) {}
    pret = new Promise(function (res) { ouvrir = res; });
    afficherEcran('Accès refermé après 15 minutes : redonnez le mot de passe.');
  }

  // ── fetch : attend le déverrouillage, ajoute l'autorisation ──
  var fetchOrigine = window.fetch.bind(window);

  function estVerrouillee(url) {
    var chemin = new URL(typeof url === 'string' ? url : url.url, location.href).pathname;
    return PREFIXES.some(function (p) { return chemin.indexOf(p) === 0; });
  }

  window.fetch = function (url, options) {
    if (!estVerrouillee(url)) return fetchOrigine(url, options);
    var essai = function () {
      return pret.then(function () {
        var o = Object.assign({}, options || {});
        var h = new Headers(o.headers || (typeof url !== 'string' && url.headers) || {});
        h.set('X-Jeton-Admin', jeton || '');
        o.headers = h;
        return fetchOrigine(url, o);
      });
    };
    return essai().then(function (res) {
      if (res.status !== 401) return res;
      reverrouiller();            // autorisation expirée ou refusée : on redemande
      return essai();
    });
  };

  // ── Écran de mot de passe ──
  var ecran = null;

  function afficherEcran(message) {
    document.documentElement.classList.add('verrou-admin-ferme');
    if (!document.body) return;          // construit au chargement de la page
    if (!ecran) construireEcran();
    ecran.querySelector('.va-msg').textContent = message || '';
    ecran.querySelector('.va-msg').hidden = !message;
    ecran.hidden = false;
    var champ = ecran.querySelector('input');
    champ.value = '';
    champ.focus();
  }

  function construireEcran() {
    ecran = document.createElement('div');
    ecran.className = 'verrou-admin';
    ecran.setAttribute('role', 'dialog');
    ecran.setAttribute('aria-modal', 'true');
    ecran.innerHTML =
      '<form class="va-boite">' +
      '  <div class="va-icone" aria-hidden="true">🔒</div>' +
      '  <h1 class="va-titre">Accès administrateur</h1>' +
      '  <p class="va-texte">Chiffre d\'affaires, marge et valeur du stock :<br>mot de passe administrateur.</p>' +
      '  <input type="password" class="va-champ" autocomplete="current-password" aria-label="Mot de passe administrateur">' +
      '  <p class="va-msg" hidden></p>' +
      '  <button type="submit" class="va-ok">Déverrouiller</button>' +
      '  <a href="/hub.html" class="va-hub">🏠 Retour au Hub</a>' +
      '</form>';
    var style = document.createElement('style');
    style.textContent =
      'html.verrou-admin-ferme body > :not(.verrou-admin){visibility:hidden}' +
      '.verrou-admin{position:fixed;inset:0;z-index:10000;display:flex;align-items:center;justify-content:center;' +
      'padding:16px;background:#3D2008;font-family:inherit}' +
      '.verrou-admin[hidden]{display:none}' +
      '.va-boite{background:#FFFDF8;color:#3D2008;border-radius:16px;padding:28px 24px;width:100%;max-width:380px;' +
      'display:flex;flex-direction:column;gap:12px;text-align:center;box-shadow:0 16px 48px rgba(0,0,0,.4)}' +
      '.va-icone{font-size:2.6rem;line-height:1}.va-titre{margin:0;font-size:1.3rem}' +
      '.va-texte{margin:0;opacity:.75;font-size:.95rem}' +
      '.va-champ{min-height:52px;padding:.5rem .75rem;font-size:1.2rem;border:1.5px solid rgba(0,0,0,.25);border-radius:10px;' +
      'user-select:text;-webkit-user-select:text}' +
      '.va-msg{margin:0;color:#C93030;font-weight:600}' +
      '.va-ok{min-height:52px;border:none;border-radius:10px;background:#2E7D32;color:#fff;font-size:1.1rem;font-weight:700;cursor:pointer}' +
      '.va-hub{min-height:44px;display:flex;align-items:center;justify-content:center;color:#3D2008;text-decoration:none;font-weight:600}';
    document.head.appendChild(style);
    document.body.appendChild(ecran);

    ecran.querySelector('form').addEventListener('submit', function (e) {
      e.preventDefault();
      var msg = ecran.querySelector('.va-msg');
      fetchOrigine('/api/auth/deverrouiller', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: ecran.querySelector('input').value, verrou: VERROU }),
        cache: 'no-store',
      }).then(function (res) {
        if (!res.ok) {
          msg.textContent = res.status === 429 ? 'Trop d\'essais : réessayez dans une minute.'
            : res.status === 401 ? 'Mot de passe administrateur incorrect.' : 'Erreur ' + res.status;
          msg.hidden = false;
          ecran.querySelector('input').select();
          return;
        }
        return res.json().then(function (d) {
          memoriser(d.jeton, Date.now() + (d.expire_dans || 900) * 1000);
        });
      }).catch(function () {
        msg.textContent = 'Serveur injoignable.';
        msg.hidden = false;
      });
    });
  }

  // ── Démarrage ──
  var deja = lireJeton();
  if (deja) {
    memoriser(deja.jeton, deja.exp);
  } else {
    document.documentElement.classList.add('verrou-admin-ferme');
    document.addEventListener('DOMContentLoaded', function () { afficherEcran(''); });
  }
})();

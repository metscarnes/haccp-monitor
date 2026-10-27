/**
 * bouton-hub.js — Bouton 🏠 « retour direct à l'accueil du Hub » sur toutes les pages.
 *
 * Les flèches « ← » remontent d'un cran (dossier, sous-module…) : avec des dossiers
 * dans des dossiers, revenir à l'accueil demandait plusieurs touches. Ce script
 * place un 🏠 juste à côté du premier bouton « ← » de la page, avec le même style.
 * Si ce « ← » mène déjà au Hub, rien n'est ajouté. Sans « ← », un 🏠 flottant
 * apparaît en bas à gauche.
 *
 * À inclure dans le <head> :  <script src="/static/js/core/bouton-hub.js" defer></script>
 */
(function () {
  'use strict';

  var ACCUEIL = '/hub.html';

  function versHub(href) {
    if (!href) return false;
    var chemin = new URL(href, location.href).pathname;
    return chemin === ACCUEIL;
  }

  function creerBouton(classe) {
    var a = document.createElement('a');
    a.href = ACCUEIL;
    a.className = (classe ? classe + ' ' : '') + 'bouton-hub';
    a.setAttribute('aria-label', 'Accueil du Hub');
    a.title = 'Accueil du Hub';
    a.textContent = '🏠';
    return a;
  }

  function installer() {
    if (document.querySelector('.bouton-hub')) return;
    var retour = null;
    var candidats = document.querySelectorAll('a, button');
    for (var i = 0; i < candidats.length; i++) {
      if (candidats[i].textContent.trim().charAt(0) === '←') { retour = candidats[i]; break; }
    }

    if (!retour) {
      var flottant = creerBouton('');
      flottant.classList.add('bouton-hub--flottant');
      flottant.style.cssText = 'position:fixed;left:12px;bottom:calc(12px + env(safe-area-inset-bottom));'
        + 'z-index:9000;width:52px;height:52px;border-radius:50%;display:flex;align-items:center;'
        + 'justify-content:center;font-size:1.5rem;text-decoration:none;background:#fff;'
        + 'box-shadow:0 2px 10px rgba(0,0,0,.25);border:1.5px solid rgba(0,0,0,.12);';
      document.body.appendChild(flottant);
      return;
    }
    if (retour.tagName === 'A' && versHub(retour.getAttribute('href'))) return;

    // Le « ← » et le 🏠 sont regroupés : l'en-tête garde le même nombre
    // d'éléments, donc sa mise en page (titre centré…) ne bouge pas.
    var groupe = document.createElement('span');
    groupe.style.cssText = 'display:inline-flex;align-items:center;gap:.4rem;flex-shrink:0;';
    retour.parentNode.insertBefore(groupe, retour);
    groupe.appendChild(retour);
    var maison = creerBouton(retour.className);
    maison.style.justifyContent = 'center';
    maison.style.textDecoration = 'none';
    groupe.appendChild(maison);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', installer);
  else installer();
})();

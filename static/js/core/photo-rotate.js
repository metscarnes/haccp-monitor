/**
 * photo-rotate.js — Bouton de rotation d'affichage pour les visionneuses
 * photo/BL/PDF plein écran de l'application (réception, historique,
 * produits en attente, factures, etc.).
 *
 * Principe : ce script ne connaît rien des différentes visionneuses
 * (rh-modal, pa-viewer, he-modal, ...). Il observe le DOM et, dès qu'une
 * image de visionneuse plein écran devient visible, lui ajoute (une seule
 * fois) un bouton flottant "↻ Tourner" qui fait pivoter l'affichage par
 * pas de 90°. La rotation est remise à zéro à chaque nouvelle image/page
 * affichée (changement de src), pour ne pas polluer la page suivante.
 *
 * Sélecteurs pris en charge (liste ouverte, un de plus suffit à l'ajouter) :
 *   #rh-modal-img, #pa-viewer-img, #he-modal-img
 * ainsi que toute image portant l'attribut [data-rotatable].
 */
(function () {
  'use strict';

  const SELECTORS = [
    '#rh-modal-img',
    '#pa-viewer-img',
    '#he-modal-img',
    '[data-rotatable]',
  ];

  const ROTATIONS = new WeakMap(); // img -> degrés courants (0/90/180/270)

  function appliquerRotation(img) {
    const deg = ROTATIONS.get(img) || 0;
    img.style.transform = deg ? `rotate(${deg}deg)` : '';
    // Sur une rotation à 90°/270°, l'image (souvent portrait) doit pivoter
    // sans déborder de son conteneur : on échange les contraintes de taille.
    if (deg % 180 !== 0) {
      img.style.maxWidth = '96vh';
      img.style.maxHeight = '96vw';
    } else {
      img.style.maxWidth = '';
      img.style.maxHeight = '';
    }
  }

  function tourner(img) {
    const deg = ((ROTATIONS.get(img) || 0) + 90) % 360;
    ROTATIONS.set(img, deg);
    appliquerRotation(img);
  }

  function creerBouton(img) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = '↻ Tourner';
    btn.setAttribute('aria-label', "Faire pivoter l'image");
    btn.className = 'photo-rotate-btn';
    btn.style.cssText = [
      'position:fixed', 'bottom:20px', 'right:20px', 'z-index:2147483647',
      'background:rgba(255,255,255,.15)', 'border:2px solid rgba(255,255,255,.6)',
      'border-radius:8px', 'color:#FFF', 'cursor:pointer',
      'font-size:15px', 'font-weight:700', 'height:44px', 'padding:0 16px',
    ].join(';');
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      tourner(img);
    });
    return btn;
  }

  function trouverConteneurModal(img) {
    // Le plus proche ancêtre positionné en overlay plein écran (id contenant
    // "modal" ou "viewer"), sinon le body pour rattacher le bouton flottant.
    let el = img.parentElement;
    while (el && el !== document.body) {
      if (/modal|viewer/i.test(el.id || '')) return el;
      el = el.parentElement;
    }
    return document.body;
  }

  function equiper(img) {
    if (img.dataset.rotateEquipped) return;
    img.dataset.rotateEquipped = '1';
    img.style.transition = 'transform .15s ease';

    const conteneur = trouverConteneurModal(img);
    const btn = creerBouton(img);
    conteneur.appendChild(btn);

    // Réinitialise la rotation à chaque changement d'image (nouvelle page,
    // nouvelle photo) pour ne pas laisser une rotation appliquée à tort.
    const resetSurChangement = () => {
      ROTATIONS.set(img, 0);
      appliquerRotation(img);
    };
    const observerSrc = new MutationObserver(resetSurChangement);
    observerSrc.observe(img, { attributes: true, attributeFilter: ['src'] });

    // Cache/affiche le bouton en même temps que la visionneuse.
    const conteneurVisible = () => {
      const cache = conteneur.hidden ||
        getComputedStyle(conteneur).display === 'none';
      btn.style.display = cache ? 'none' : '';
      if (cache) resetSurChangement();
    };
    conteneurVisible();
    new MutationObserver(conteneurVisible).observe(conteneur, {
      attributes: true, attributeFilter: ['hidden', 'style', 'class'],
    });
  }

  function scanner() {
    SELECTORS.forEach((sel) => {
      document.querySelectorAll(sel).forEach(equiper);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scanner);
  } else {
    scanner();
  }
  // Certaines visionneuses (ouvrirViewerPages) construisent leur <img> en JS
  // après coup : on observe tout le document pour les rattraper.
  new MutationObserver(scanner).observe(document.documentElement, {
    childList: true, subtree: true,
  });
})();

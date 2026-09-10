/**
 * etiquette-print.js — Impression des étiquettes thermiques Brother 62 mm.
 *
 * Sur un rouleau CONTINU, la 2e dimension de `@page` n'est pas une hauteur de
 * feuille : c'est la longueur de papier déroulée avant la coupe. Les gabarits
 * la déclaraient en dur, avec trois politiques incompatibles :
 *
 *   - `62mm auto`  → le navigateur déroule sa longueur de page par défaut,
 *                    d'où la bande blanche à couper aux ciseaux ;
 *   - `62mm 60mm`  → trop long pour la plupart des étiquettes (papier perdu),
 *                    et `overflow: hidden` rognait silencieusement le pied
 *                    des étiquettes trop chargées ;
 *   - `62mm 40mm`  → même problème, un cran plus court.
 *
 * Aucune constante ne peut convenir : la liste d'ingrédients d'une étiquette de
 * fabrication est de longueur variable (et légalement obligatoire, donc
 * intronquable), et un nom de produit long passe à la ligne. On mesure donc le
 * gabarit une fois rempli, à sa largeur d'impression réelle, et on injecte la
 * longueur exacte le temps de l'impression.
 *
 * Usage — remplace `setTimeout(() => window.print(), 100)` :
 *
 *     imprimerEtiquette(document.getElementById('print-label'));
 *
 * Les règles `@page` des gabarits sont conservées comme filet de sécurité : si
 * ce script n'est pas chargé, l'impression retombe sur l'ancien format fixe.
 */
(function () {
  'use strict';

  const LARGEUR_MM = 62;   // largeur du rouleau
  const PADDING_MM = 2;    // doit rester aligné sur le `padding` des gabarits
  const MARGE_MM   = 2;    // slack : mieux vaut 2 mm de papier qu'un pied rogné
  const MIN_MM     = 20;   // en deçà, l'imprimante n'amorce pas la coupe
  const MAX_MM     = 300;
  const STYLE_ID   = 'etiquette-page-size';

  /**
   * Facteur px/mm réel. Il dépend du zoom navigateur et de la densité de
   * l'écran : on le mesure au lieu de supposer 96 dpi.
   */
  function pxParMm() {
    const sonde = document.createElement('div');
    sonde.style.cssText =
      'position:absolute;left:-10000px;top:0;width:100mm;height:0;visibility:hidden';
    document.body.appendChild(sonde);
    const px = sonde.getBoundingClientRect().width / 100;
    sonde.remove();
    return px > 0 ? px : 96 / 25.4;
  }

  /**
   * Hauteur du gabarit rempli, en mm.
   *
   * La mesure se fait hors écran mais dans le flux, à la largeur exacte du
   * rouleau et avec le `padding`/`font-family` du mode impression : c'est le
   * retour à la ligne des noms longs qui fait la hauteur, pas seulement le
   * nombre d'éléments.
   */
  function mesurerHauteurMm(el) {
    const styleInitial = el.getAttribute('style');
    let hauteurPx;

    try {
      // `display:none` est posé par une règle #id : il faut !important pour la
      // battre sans dépendre de l'ordre des feuilles de style.
      el.style.setProperty('display', 'block', 'important');
      el.style.setProperty('position', 'absolute');
      el.style.setProperty('left', '-10000px');
      el.style.setProperty('top', '0');
      el.style.setProperty('width', LARGEUR_MM + 'mm');
      el.style.setProperty('height', 'auto');
      el.style.setProperty('max-height', 'none');
      el.style.setProperty('overflow', 'visible');
      el.style.setProperty('box-sizing', 'border-box');
      el.style.setProperty('padding', PADDING_MM + 'mm');
      el.style.setProperty('visibility', 'hidden');

      hauteurPx = el.getBoundingClientRect().height;
    } finally {
      // Le gabarit doit retrouver son état d'origine quoi qu'il arrive : c'est
      // lui que l'impression va afficher juste après.
      if (styleInitial === null) el.removeAttribute('style');
      else el.setAttribute('style', styleInitial);
    }

    return hauteurPx / pxParMm();
  }

  /** Injecte (ou met à jour) la règle `@page` du temps de l'impression. */
  function appliquerLongueur(mm) {
    let style = document.getElementById(STYLE_ID);
    if (!style) {
      style = document.createElement('style');
      style.id = STYLE_ID;
      document.head.appendChild(style);
    }
    // Volontairement sans `overflow:hidden` ni hauteur figée sur html/body :
    // un dépassement doit se voir sur une 2e étiquette, jamais disparaître.
    style.textContent =
      '@media print { @page { size: ' + LARGEUR_MM + 'mm ' + mm + 'mm; margin: 0; } }';
  }

  function retirerLongueur() {
    const style = document.getElementById(STYLE_ID);
    if (style) style.remove();
  }

  /**
   * Mesure `el`, cale la longueur de page dessus, imprime, puis nettoie.
   *
   * @param {HTMLElement} el gabarit d'étiquette déjà rempli.
   */
  function imprimerEtiquette(el) {
    if (!el) {
      window.print();
      return;
    }

    try {
      const mm = Math.ceil(mesurerHauteurMm(el) + MARGE_MM);
      appliquerLongueur(Math.min(MAX_MM, Math.max(MIN_MM, mm)));
    } catch (err) {
      // Mesure impossible : on laisse le `@page` du gabarit faire son office.
      console.warn('[etiquette-print] mesure impossible, format par défaut', err);
      retirerLongueur();
    }

    // La règle injectée ne doit pas survivre à l'impression : la page reste
    // ouverte et l'étiquette suivante aura une autre longueur.
    let filet = null;
    const nettoyer = () => {
      retirerLongueur();
      window.removeEventListener('afterprint', nettoyer);
      clearTimeout(filet);
    };
    window.addEventListener('afterprint', nettoyer);
    // Filet si `afterprint` ne se déclenche pas (anciens navigateurs, WebView).
    filet = setTimeout(nettoyer, 10000);

    // Léger délai : laisse le navigateur peindre le gabarit rempli.
    setTimeout(() => window.print(), 100);
  }

  window.imprimerEtiquette = imprimerEtiquette;
})();

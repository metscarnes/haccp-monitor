/**
 * guard.js — Garde d'accès « équipe ou admin » pour les pages du quotidien.
 *
 * À inclure le plus tôt possible dans le <head> ou en tout début de <body> :
 *     <script src="/static/js/core/guard.js"></script>
 *
 * Rôle :
 *   - Si aucune session valide (token absent/expiré) → redirige vers /login.html
 *     en mémorisant la page courante pour y revenir après connexion.
 *   - Accepte aussi bien le rôle « équipe » que « admin » : ces pages sont
 *     accessibles à tout le personnel connecté.
 *   - Les pages réservées à l'admin (admin.html, catalogue.html,
 *     fournisseurs.html, catalogue-achats.html) ont leur propre garde dédié
 *     et n'incluent PAS ce fichier.
 *
 * Note : ce garde est une commodité d'affichage (éviter le comportement
 * aléatoire dû au cache PWA). La vraie sécurité reste assurée côté serveur
 * par le middleware et les dépendances d'authentification.
 */
(function () {
  'use strict';

  var token = localStorage.getItem('admin_token');
  var exp = Number(localStorage.getItem('admin_token_expires') || 0);

  if (!token || Date.now() > exp) {
    // Mémorise la page demandée pour y revenir après connexion.
    try {
      sessionStorage.setItem('auth_redirect', window.location.pathname);
    } catch (e) { /* sessionStorage indisponible : on redirige quand même */ }
    // Nettoyage d'une éventuelle session expirée.
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_token_expires');
    window.location.replace('/login.html');
  }
})();

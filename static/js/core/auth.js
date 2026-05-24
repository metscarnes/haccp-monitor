/**
 * auth.js — Gestion du token admin (localStorage)
 *
 * Utilisation :
 *   import { getToken, requireAuth, authHeaders } from '/static/js/core/auth.js';
 */

const TOKEN_KEY   = 'admin_token';
const EXPIRES_KEY = 'admin_token_expires';

export function getToken() {
  const expires = Number(localStorage.getItem(EXPIRES_KEY) || 0);
  if (Date.now() > expires) {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EXPIRES_KEY);
    return null;
  }
  return localStorage.getItem(TOKEN_KEY);
}

/** Redirige vers /login.html si pas de token valide. */
export function requireAuth(redirectBack = true) {
  const token = getToken();
  if (!token) {
    if (redirectBack) {
      sessionStorage.setItem('auth_redirect', window.location.pathname);
    }
    window.location.href = '/login.html';
    return null;
  }
  return token;
}

/** Retourne les headers Authorization à passer aux fetch() protégés. */
export function authHeaders() {
  const token = getToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

/** Déconnexion manuelle. */
export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(EXPIRES_KEY);
  window.location.href = '/login.html';
}

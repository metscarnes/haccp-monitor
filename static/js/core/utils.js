/* HACCP Monitor — Core utilities */

function formatDate(date, opts = {}) {
  return new Date(date).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    ...opts,
  });
}

function formatTime(date) {
  return new Date(date).toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDateTime(date) {
  return `${formatDate(date)} — ${formatTime(date)}`;
}

function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

function startInactivityTimer(onTimeout, ms = 5 * 60 * 1000) {
  let timer;
  function reset() {
    clearTimeout(timer);
    timer = setTimeout(onTimeout, ms);
  }
  ['touchstart', 'click', 'keydown', 'mousemove', 'scroll']
    .forEach(ev => document.addEventListener(ev, reset, { passive: true }));
  reset();
  return () => {
    ['touchstart', 'click', 'keydown', 'mousemove', 'scroll']
      .forEach(ev => document.removeEventListener(ev, reset));
    clearTimeout(timer);
  };
}

function startClock(el) {
  function tick() {
    const now = new Date();
    el.textContent = now.toLocaleDateString('fr-FR', {
      weekday: 'short', day: 'numeric', month: 'long',
    }) + ' — ' + now.toLocaleTimeString('fr-FR', {
      hour: '2-digit', minute: '2-digit',
    });
  }
  tick();
  const interval = setInterval(tick, 1000);
  return () => clearInterval(interval);
}

function show(el) { el.hidden = false; }
function hide(el) { el.hidden = true; }
function toggle(el, visible) { el.hidden = !visible; }

function statusDot(status) {
  const map = { ok: 'ok', attention: 'warning', alerte: 'alert', error: 'offline' };
  const cls = map[status] || 'offline';
  return `<span class="status-dot status-dot--${cls}" aria-hidden="true"></span>`;
}

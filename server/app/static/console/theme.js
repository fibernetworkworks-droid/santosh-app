/* v0.240 CALM BRAND - her Light / Dark / System choice, text size, reduce motion and the live border glow.
   Loaded in <head> (before the first paint, so the page never flashes the wrong theme) and again used by v2.js
   through window.HoolaTheme. Choices live in this browser only (localStorage); System follows the computer. */
(function () {
  var d = document.documentElement, KEY = { theme: 'hoola.theme', size: 'hoola.size', calm: 'hoola.calm', glow: 'hoola.glow' };
  function get(k, def) { try { return localStorage.getItem(KEY[k]) || def; } catch (e) { return def; } }
  function put(k, v) { try { localStorage.setItem(KEY[k], v); } catch (e) {} }
  function paint() {
    var t = get('theme', 'system');
    if (t === 'light' || t === 'dark') d.setAttribute('data-theme', t); else d.removeAttribute('data-theme');
    d.setAttribute('data-size', get('size', 'md'));
    d.classList.toggle('calm', get('calm', '') === '1');
    d.classList.toggle('noglow', get('glow', '1') === '0');
  }
  paint();
  var listeners = [];
  function changed() { paint(); listeners.forEach(function (f) { try { f(); } catch (e) {} }); }
  window.HoolaTheme = {
    theme: function () { return get('theme', 'system'); },
    size: function () { return get('size', 'md'); },
    calm: function () { return get('calm', '') === '1'; },
    glow: function () { return get('glow', '1') !== '0'; },
    dark: function () { var t = get('theme', 'system'); return t === 'dark' || (t === 'system' && matchMedia('(prefers-color-scheme: dark)').matches); },
    /* ev = the click, so the new theme opens as a soft circle from where she clicked */
    setTheme: function (t, ev) {
      if (['light', 'dark', 'system'].indexOf(t) < 0) return;
      put('theme', t);
      var reduce = get('calm', '') === '1' || matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (ev && document.startViewTransition && !reduce) {
        d.style.setProperty('--vx', (ev.clientX || innerWidth / 2) + 'px'); d.style.setProperty('--vy', (ev.clientY || innerHeight / 2) + 'px');
        document.startViewTransition(changed);
      } else changed();
    },
    setSize: function (z) { if (['sm', 'md', 'lg'].indexOf(z) < 0) return; put('size', z); changed(); },
    setCalm: function (on) { put('calm', on ? '1' : ''); changed(); },
    setGlow: function (on) { put('glow', on ? '1' : '0'); changed(); },
    onChange: function (f) { listeners.push(f); }
  };
  try { matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () { listeners.forEach(function (f) { try { f(); } catch (e) {} }); }); } catch (e) {}
})();

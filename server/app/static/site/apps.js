/* Hoola App Studio page (the App Development page of the Hoola website). Plain file (strict CSP: no inline script).
   GSAP 3.12.5 + ScrollTrigger from /static/site/vendor. Every loop pauses off screen; prefers-reduced-motion shows
   the end states with no movement. All drawn scenes are CSS; nothing here calls an API. The Web Studio page's twin. */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const G = window.gsap;
  if (G && window.ScrollTrigger) G.registerPlugin(window.ScrollTrigger);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

  /* ---------- drawn scenes (same family as the studio's art) ---------- */
  const PAL = {
    dusk: ['linear-gradient(#8b6cf0,#3a2a86 70%,#22184f)', 'rgba(40,26,96,.75)', 'rgba(20,12,52,.9)'],
    gold: ['linear-gradient(#ffcf8a,#e0884a 55%,#7a3b4f)', 'rgba(122,59,79,.7)', 'rgba(60,24,48,.9)'],
    rose: ['linear-gradient(#ffb6c9,#c86b9a 60%,#5b2d63)', 'rgba(110,50,110,.6)', 'rgba(60,24,70,.9)'],
    sea: ['linear-gradient(#9fd8ff,#4b86c9 60%,#203a6e)', 'rgba(30,60,120,.6)', 'rgba(14,30,70,.9)'],
    green: ['linear-gradient(#bff0c6,#4fae8b 55%,#1d4d4a)', 'rgba(25,80,70,.65)', 'rgba(10,40,40,.9)'],
    night: ['linear-gradient(#2c2466,#141033 70%)', 'rgba(60,40,120,.5)', 'rgba(10,8,30,.92)'],
    ember: ['linear-gradient(#ff9a6b,#c0406e 60%,#3e1846)', 'rgba(90,30,70,.7)', 'rgba(40,12,40,.92)'],
  };
  function art(kind, pal, o = {}) {
    const [sky, h1, h2] = PAL[pal] || PAL.dusk;
    const st = `--sky:${sky};--h1:${h1};--h2:${h2};${o.sx ? `--sx:${o.sx};` : ''}${o.sy ? `--sy:${o.sy};` : ''}${o.pc ? `--pc:${o.pc};` : ''}${o.pc2 ? `--pc2:${o.pc2};` : ''}${o.skin ? `--skin:${o.skin};` : ''}`;
    let in_ = '';
    if (kind === 'mount') in_ = '<i class="sun"></i><i class="hill"></i><i class="hill b"></i>';
    else if (kind === 'city') in_ = '<i class="sun"></i><span class="city">' + [62, 40, 78, 52, 90, 46, 70, 34, 58].map(h => `<i style="height:${h}%"></i>`).join('') + '</span>';
    else if (kind === 'product') in_ = '<i class="bottle"></i>';
    else if (kind === 'music') in_ = '<i class="disc"></i>';
    else if (kind === 'portrait') in_ = '<i class="sun" style="--sx:64%;--sy:12%"></i><i class="who"></i>';
    else if (kind === 'diya') in_ = '<i class="hill b"></i>' + [18, 36, 54, 72].map((l, i) => `<i class="diya" style="left:${l}%;animation-delay:${i * .3}s"></i>`).join('');
    return `<span class="art anim" style="${st}" aria-hidden="true">${in_}<i class="grain"></i></span>`;
  }
  /* a drawn phone screen (the three looks of the Home screen) */
  const phone = (sky, on) => `<span class="pn" style="--sky:${sky}" aria-hidden="true"><span class="st"><i></i><i></i></span><span class="hd"></span><span class="bd"><i></i><i></i><i></i></span><span class="tabs"><i></i><i class="${on ? 'on' : ''}"></i><i></i><i></i></span></span>`;

  /* ---------- hero: rotating word, depth on the pointer, the plan typing in ---------- */
  const WORDS = ['app.', 'Android app.', 'iPhone app.', 'store app.'];
  const rot = $('#rot');
  if (rot && G && !RM) {
    let i = 0;
    setInterval(() => {
      if (document.hidden) return;
      i = (i + 1) % WORDS.length;
      const span = rot.firstElementChild;
      G.to(span, {yPercent: -60, opacity: 0, duration: .32, ease: 'power2.in', onComplete: () => {
        span.textContent = WORDS[i];
        G.fromTo(span, {yPercent: 60, opacity: 0}, {yPercent: 0, opacity: 1, duration: .45, ease: 'power3.out'});
      }});
    }, 2300);
  }

  const stage = $('#stage');
  if (stage && G && !RM) {
    const layers = $$('[data-depth]', stage);
    G.from(layers, {y: 40, opacity: 0, duration: 1, ease: 'power3.out', stagger: .12, delay: .15});
    G.from('.as-ai', {y: 10, opacity: 0, duration: .6, delay: 1.4, ease: 'power2.out'});
    if (matchMedia('(pointer:fine)').matches) {
      stage.addEventListener('pointermove', e => {
        const r = stage.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
        layers.forEach(l => { const d = +l.dataset.depth; G.to(l, {x: x * 18 * d, y: y * 14 * d, duration: .6, ease: 'power2.out', overwrite: 'auto'}); });
      });
      stage.addEventListener('pointerleave', () => G.to(layers, {x: 0, y: 0, duration: .8, ease: 'power3.out'}));
    }
  }

  /* pause CSS loops of any block that is off screen */
  const io = new IntersectionObserver(es => es.forEach(e => e.target.classList.toggle('paused', !e.isIntersecting)), {rootMargin: '80px'});
  $$('section').forEach(s => io.observe(s));

  /* ---------- watch it work: brief -> plan -> three looks -> pick -> prototype -> builds -> store ---------- */
  const BRIEF = 'An app for Sharma Kirana in Akola: order groceries, home delivery, pay by UPI, credit reminders';
  const typ = $('#oltype'), steps = $$('#olsteps span'), tl = $('#oltl'), tm = $('#oltime'), send = $('#olsend');
  const board = $('#olboard'), build = $('#olbuild'), rail = $$('#olrail li');
  const gp = $('#olgp'), as = $('#olas'), st = $('#olst');
  if (board && typ) {
    const lookEls = [$('#olka'), $('#olkb'), $('#olkc')].filter(Boolean);
    const stepOn = n => steps.forEach((s, k) => { s.classList.toggle('on', k === n); s.classList.toggle('done', k < n); });
    const railSet = done => rail.forEach((li, k) => { li.classList.toggle('ok', k < done); li.classList.toggle('run', k === done); });
    const endState = () => {
      typ.textContent = BRIEF; stepOn(6); build && build.classList.add('on');
      lookEls.forEach(l => l.classList.add('sel')); lookEls[0] && lookEls[0].classList.add('dim'); lookEls[2] && lookEls[2].classList.add('dim');
      railSet(6); gp && gp.classList.add('ok'); as && as.classList.add('ok'); st && st.classList.add('ok');
      if (tl) tl.style.width = '100%'; if (tm) tm.textContent = 'Ready for the stores · her tap next';
    };
    if (!G || RM) endState();
    else {
      const T = G.timeline({paused: true, repeat: -1, repeatDelay: 1.8});
      const state = {n: 0, p: 0};
      T.call(() => { typ.innerHTML = '<span class="car"></span>'; stepOn(0); tl.style.width = '0%'; tm.textContent = 'step 1 of 7';
        send.classList.remove('hit'); build && build.classList.remove('on');
        lookEls.forEach(l => l.classList.remove('sel', 'dim')); railSet(0);
        gp && gp.classList.remove('ok'); as && as.classList.remove('ok'); st && st.classList.remove('ok'); });
      T.to(state, {n: BRIEF.length, duration: 3, ease: 'none', onUpdate: () => { typ.innerHTML = esc(BRIEF.slice(0, Math.round(state.n))) + '<span class="car"></span>'; }});
      T.call(() => send.classList.add('hit'), null, '+=.2');
      T.call(() => { stepOn(1); tm.textContent = 'Plan · 6 screens · 4 tables · 3 roles'; }, null, '+=.35');
      T.call(() => stepOn(2), null, '+=.9');
      lookEls.forEach((l, i) => T.fromTo(l, {opacity: .35, y: 12}, {opacity: 1, y: 0, duration: .45, ease: 'power2.out'}, i ? '+=.25' : '+=.05'));
      T.call(() => stepOn(3), null, '+=.3');
      T.call(() => { lookEls[1] && lookEls[1].classList.add('sel'); lookEls[0] && lookEls[0].classList.add('dim'); lookEls[2] && lookEls[2].classList.add('dim'); tm.textContent = 'step 4 of 7'; }, null, '+=.4');
      lookEls[1] && T.fromTo(lookEls[1], {scale: .97}, {scale: 1.03, duration: .5, ease: 'back.out(1.6)'}, '<');
      T.call(() => { stepOn(4); tm.textContent = 'step 5 of 7'; }, null, '+=.7');
      T.call(() => railSet(1), null, '+=.5');
      T.call(() => { stepOn(5); tm.textContent = 'step 6 of 7'; }, null, '+=.9');
      T.call(() => railSet(2), null, '+=.2');
      T.call(() => railSet(3), null, '+=.7');
      T.call(() => railSet(4), null, '+=.7');
      T.call(() => railSet(5), null, '+=.7');
      T.call(() => { gp && gp.classList.add('ok'); as && as.classList.add('ok'); }, null, '+=.3');
      T.call(() => { stepOn(6); tm.textContent = 'step 7 of 7'; st && st.classList.add('ok'); }, null, '+=.4');
      T.to(state, {p: 100, duration: 1.2, ease: 'none', onUpdate: () => { tl.style.width = state.p + '%'; }});
      T.call(() => { tm.textContent = 'Ready for the stores · her tap next'; });
      T.set(state, {n: 0, p: 0});
      window.ScrollTrigger.create({trigger: '#olbox', start: 'top 80%', end: 'bottom 10%', onToggle: s => s.isActive ? T.play() : T.pause()});
    }
  }

  /* ---------- the whole road: the step list follows the scroll; the drawn workspace switches with it ---------- */
  const dl = $$('#dsteps li'), dfill = $('#dfill');
  const dvs = [$('#dv1'), $('#dv2'), $('#dv3')];
  let cur = -1;
  function dset(n) {
    if (n === cur || !dl.length) return; cur = n;
    dl.forEach((li, k) => { li.classList.toggle('on', k === n); li.classList.toggle('done', k < n); });
    if (dfill && dl[n]) dfill.style.height = Math.max(0, dl[n].offsetTop) + 'px';
    const state = n <= 3 ? dvs[0] : n === 4 ? dvs[1] : dvs[2];
    dvs.forEach(d => d && d.classList.toggle('on', d === state));
  }
  dset(0);
  dl.forEach((li, k) => li.addEventListener('click', () => { auto = false; dset(k); }));
  let auto = true;
  if (G && !RM && matchMedia('(min-width:981px)').matches) {
    window.ScrollTrigger.create({trigger: '#steps .grid', start: 'top 18%', end: '+=1400', pin: true, pinSpacing: true,
      onUpdate: s => { if (auto) dset(Math.min(7, Math.floor(s.progress * 8))); }});
  } else if (!RM) {
    let on = false; const sec = $('#steps'); if (sec) new IntersectionObserver(es => { on = es[0].isIntersecting; }).observe(sec);
    setInterval(() => { if (on && auto && !document.hidden) dset((cur + 1) % 8); }, 2600);
  }

  /* ---------- price card: Haan, fingerprint, building ---------- */
  const pc = $('#pcard');
  if (pc && G && !RM) {
    const yes = $('#pyes'), fp = $('#pfp'), done = $('#pdone'), ring = $('#pring');
    const T = G.timeline({paused: true, repeat: -1, repeatDelay: 2});
    T.set([fp, done], {opacity: 0}).set(ring, {borderColor: 'rgba(255,177,92,.3)', scale: 1})
      .to(yes, {scale: 1.06, duration: .3, yoyo: true, repeat: 3, ease: 'sine.inOut'}, '+=1.2')
      .to(yes, {scale: .94, duration: .12}).to(yes, {scale: 1, duration: .2})
      .to(fp, {opacity: 1, duration: .35}, '+=.1')
      .to(ring, {borderColor: '#FFB15C', scale: 1.08, duration: .9, ease: 'power2.inOut'})
      .to(done, {opacity: 1, duration: .4}, '+=.2')
      .from($('.tick', done), {scale: .4, duration: .5, ease: 'back.out(2.4)'}, '<')
      .to([fp, done], {opacity: 0, duration: .4}, '+=2.6');
    window.ScrollTrigger.create({trigger: pc, start: 'top 85%', end: 'bottom 10%', onToggle: s => s.isActive ? T.play() : T.pause()});
  }

  /* ---------- made for ---------- */
  const MADE = [
    ['Delivery app', 'Orders, riders on a map, UPI on delivery, ratings after.', 'city', 'night', {}],
    ['Staff & attendance app', 'Who is in, tasks of the day, leaves, a manager\'s eye view.', 'portrait', 'dusk', {pc: '#3b2a74'}],
    ['Gym & membership app', 'Plans, check-ins, dues, a trainer\'s notes per member.', 'product', 'ember', {pc: '#2f7d5b', pc2: '#bff0c6'}],
    ['School parent app', 'Fees, homework, bus on the map, notes from the class teacher.', 'portrait', 'sea', {}],
    ['Salon & booking app', 'Slots, stylists, advance by UPI, a reminder the evening before.', 'product', 'rose', {pc: '#8a1f3a'}],
    ['Society app', 'Notices, maintenance dues, visitor passes, complaints that close.', 'mount', 'green', {}],
    ['Bills & GST app', 'Invoices in Hindi and English, GST sums, old bills in one search.', 'product', 'gold', {pc: '#b4542f', pc2: '#f1c27d'}],
    ['Loyalty & credit app', 'Points on every bill, credit with due dates, gentle reminders.', 'diya', 'night', {}],
  ];
  const mg = $('#mgrid');
  if (mg) mg.innerHTML = MADE.map(m => `<div class="mcard"><div class="pic">${art(m[2], m[3], m[4])}</div><div class="bd"><b>${esc(m[0])}</b><p>${esc(m[1])}</p></div></div>`).join('');

  /* ---------- reveals ---------- */
  if (G && !RM) {
    $$('main section:not(.hero) .eb, main section:not(.hero) .h2, main section:not(.hero) .lead').forEach(el =>
      G.from(el, {y: 28, opacity: 0, duration: .8, ease: 'power3.out', scrollTrigger: {trigger: el, start: 'top 88%'}}));
    G.from('.sys', {y: 40, opacity: 0, duration: .8, ease: 'power3.out', stagger: .1, scrollTrigger: {trigger: '.sgrid', start: 'top 85%'}});
    G.from('.mcard', {y: 34, opacity: 0, duration: .7, ease: 'power3.out', stagger: .06, scrollTrigger: {trigger: '#mgrid', start: 'top 85%'}});
    G.from('.planbox', {y: 40, opacity: 0, duration: .9, ease: 'power3.out', scrollTrigger: {trigger: '.pgrid', start: 'top 85%'}});
    G.from('.dview .frame', {y: 50, rotateX: 8, opacity: 0, duration: 1, ease: 'power3.out', transformPerspective: 1200, scrollTrigger: {trigger: '.dview', start: 'top 85%'}});
  }
})();

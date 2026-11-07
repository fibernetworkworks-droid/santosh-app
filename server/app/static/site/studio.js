/* Hoola Create Studio page. Plain file (strict CSP: no inline script). GSAP 3.12.5 + ScrollTrigger from /static/site/vendor.
   Every loop pauses off screen; prefers-reduced-motion shows the end states with no movement. */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const G = window.gsap;
  if (G && window.ScrollTrigger) G.registerPlugin(window.ScrollTrigger);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

  /* ---------- the studio's drawn scenes (same family as the art in the real studio) ---------- */
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

  /* ---------- hero: rotating word, waveform, the storyboard strip, depth on the pointer ---------- */
  const WORDS = ['film.', 'poster.', 'song.', 'reel.', 'voice-over.', 'dub.'];
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
  const bars = $('#bars');
  if (bars) {
    bars.innerHTML = Array.from({length: 18}, () => '<i></i>').join('');
    $$('i', bars).forEach((b, k) => {
      b.style.height = (30 + ((k * 37) % 60)) + '%';
      if (G && !RM) G.to(b, {height: () => (20 + Math.random() * 80) + '%', duration: .35 + Math.random() * .3, repeat: -1, yoyo: true, repeatRefresh: true, ease: 'sine.inOut', delay: k * .04});
    });
  }
  const strip = $('#strip');
  if (strip) strip.innerHTML = [['mount', 'night'], ['diya', 'night'], ['product', 'gold', {pc: '#b4542f', pc2: '#f1c27d'}], ['portrait', 'rose', {pc: '#7a2f5f'}], ['city', 'gold']]
    .map(([k, p, o]) => `<span class="sh">${art(k, p, o)}</span>`).join('');

  const stage = $('#stage');
  if (stage && G && !RM) {
    const layers = $$('[data-depth]', stage);
    G.from(layers, {y: 40, opacity: 0, duration: 1, ease: 'power3.out', stagger: .12, delay: .15});
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

  /* ---------- one line in, a film out ---------- */
  const BRIEF = 'A 30-second Diwali ad for my chai brand: a family comes home, Dadi makes chai, ends on our logo.';
  const SHOTS = [['Night street lit with diyas, the family walks home', 'diya', 'night'],
    ['Dadi lights the stove, steam rises from the patila', 'portrait', 'gold', {pc: '#8a3b2f', skin: '#c48a62'}],
    ['Chai pours into clay kulhads in slow motion', 'product', 'ember', {pc: '#b4542f', pc2: '#f1c27d'}],
    ['The family laughs together on the doorstep', 'portrait', 'rose', {pc: '#5b2d82'}],
    ['The logo over warm gold light', 'mount', 'gold', {sx: '40%'}]];
  const board = $('#olboard'), typ = $('#oltype'), steps = $$('#olsteps span'), tl = $('#oltl'), tm = $('#oltime'), send = $('#olsend');
  if (board) {
    board.innerHTML = SHOTS.map((s, i) => `<div class="ol-shot"><div class="pic"><span class="blank">Shot ${i + 1}</span><span class="pa" hidden>${art(s[1], s[2], s[3] || {})}</span></div><p><b>${i + 1} · ${[6, 6, 6, 6, 6][i]} s</b>${esc(s[0])}</p></div>`).join('');
    const shotEls = $$('.ol-shot', board);
    const stepOn = n => steps.forEach((s, k) => { s.classList.toggle('on', k === n); s.classList.toggle('done', k < n); });
    const endState = () => {
      typ.textContent = BRIEF; stepOn(4); shotEls.forEach(s => { $('.blank', s).hidden = true; $('.pa', s).hidden = false; });
      tl.style.width = '100%'; tm.textContent = '0:30';
    };
    if (!G || RM) endState();
    else {
      const T = G.timeline({paused: true, repeat: -1, repeatDelay: 1.6});
      const state = {n: 0, t: 0};
      T.call(() => { typ.innerHTML = '<span class="car"></span>'; stepOn(0); tl.style.width = '0%'; tm.textContent = '0:00'; send.classList.remove('hit');
        shotEls.forEach(s => { $('.blank', s).hidden = false; $('.pa', s).hidden = true; G.set(s, {opacity: .45, y: 0, scale: 1}); }); });
      T.to(state, {n: BRIEF.length, duration: 3.2, ease: 'none', onUpdate: () => { typ.innerHTML = esc(BRIEF.slice(0, Math.round(state.n))) + '<span class="car"></span>'; }});
      T.call(() => send.classList.add('hit'), null, '+=.2');
      T.call(() => stepOn(1), null, '+=.35');
      T.to(shotEls, {opacity: 1, y: 0, duration: .4, stagger: .18, ease: 'power2.out'});
      T.call(() => stepOn(2), null, '+=.3');
      T.call(() => stepOn(3), null, '+=.6');
      shotEls.forEach((s, i) => {
        T.call(() => { $('.blank', s).hidden = true; $('.pa', s).hidden = false; }, null, i ? '+=.32' : '+=.1');
        T.fromTo(s, {scale: .94}, {scale: 1, duration: .45, ease: 'back.out(2)'}, '<');
      });
      T.call(() => stepOn(4), null, '+=.4');
      T.to(state, {t: 30, duration: 3, ease: 'none', onUpdate: () => { tl.style.width = (state.t / 30 * 100) + '%'; tm.textContent = '0:' + String(Math.floor(state.t)).padStart(2, '0'); }});
      T.set(state, {n: 0, t: 0});
      window.ScrollTrigger.create({trigger: '#olbox', start: 'top 80%', end: 'bottom 10%', onToggle: s => s.isActive ? T.play() : T.pause()});
    }
  }

  /* ---------- Director: the step list follows the scroll; a glow walks the real screen's step chips ---------- */
  const dl = $$('#dsteps li'), dfill = $('#dfill');
  // the step chips in the 1440 x 900 screenshot (x, width in px; row at y 187, height 38)
  const CHIPS = [[270, 86], [364, 126], [497, 85], [589, 109], [704, 108], [818, 93], [916, 94], [1017, 114]];
  const scr = $('#director .scr');
  let glow = null;
  if (scr) { glow = document.createElement('span'); glow.setAttribute('aria-hidden', 'true');
    glow.style.cssText = 'position:absolute;border-radius:999px;border:2px solid #FFB15C;box-shadow:0 0 0 6px rgba(255,177,92,.22),0 0 30px rgba(255,177,92,.45);pointer-events:none;transition:left .45s cubic-bezier(.2,.8,.2,1),width .45s cubic-bezier(.2,.8,.2,1)';
    scr.appendChild(glow); }
  let cur = -1;
  function dset(n) {
    if (n === cur) return; cur = n;
    dl.forEach((li, k) => { li.classList.toggle('on', k === n); li.classList.toggle('done', k < n); });
    if (dfill && dl[n]) dfill.style.height = Math.max(0, dl[n].offsetTop + 20 - 20) + 'px';
    if (glow) { const [x, w] = CHIPS[n]; glow.style.left = (x / 1440 * 100 - .4) + '%'; glow.style.width = ((w / 1440) * 100 + .8) + '%';
      glow.style.top = ((187 / 900) * 100 - .5) + '%'; glow.style.height = ((38 / 900) * 100 + 1) + '%'; }
  }
  dset(0);
  dl.forEach((li, k) => li.addEventListener('click', () => { auto = false; dset(k); }));
  let auto = true;
  if (G && !RM && matchMedia('(min-width:981px)').matches) {
    window.ScrollTrigger.create({trigger: '#director .grid', start: 'top 18%', end: '+=1400', pin: true, pinSpacing: true,
      onUpdate: s => { if (auto) dset(Math.min(7, Math.floor(s.progress * 8))); }});
  } else if (!RM) {
    let on = false; new IntersectionObserver(es => { on = es[0].isIntersecting; }).observe($('#director'));
    setInterval(() => { if (on && auto && !document.hidden) dset((cur + 1) % 8); }, 2600);
  }

  /* ---------- the six tools on their real screens ---------- */
  const TOOLS = [
    ['video', 'Video', 'Words to video, with the best model for every shot.', ['Hoola Auto picks the best ready model, or choose from 30+', 'Camera moves: dolly in, pan, orbit, drone, handheld, slow motion', '9:16 reels, 16:9 films or square, 4 to 30 seconds', 'A free preview first; the price updates as you change things'], 'Price on the Create button'],
    ['image', 'Image', 'Posters, product shots and characters that read Indian scripts.', ['1 to 4 pictures at a time, in nine looks from Photoreal to Indian folk art', 'Add your own photos as references', 'One switch adds your brand colours', 'Enhance turns a short line into a detailed one'], 'Pictures from about ₹3'],
    ['music', 'Music', 'Whole songs, instrumentals, jingles and film scores.', ['Bollywood romantic, Punjabi pop, Sufi, ghazal, garba, devotional and more', 'Your lyrics word for word, or "Write with Hoola"', 'Language, singers, mood, tempo and length', 'A real waveform of every track'], 'A song for about ₹7'],
    ['voice', 'Voice', 'Voice-overs in 22 voices, or your own Hoola\'s voice.', ['Hindi, Hinglish, Tamil, Telugu, Bengali, Marathi and more', 'Choose by female or male, by mood and pace', 'Up to 5,000 characters of script', 'Every voice-over comes with a download'], 'Price before you press'],
    ['dubbing', 'Dubbing', 'Your video in another language, up to four at a time.', ['Hoola listens once and writes every line with its speaker', 'Each language comes back as its own video', 'Keep the music softly under the new voices', 'Voices are matched to speakers, never cloned'], 'Price before you press'],
    ['editor', 'Editor', 'Your own clips, edited by your words.', ['Drop in videos, photos and music', '"A 30 s reel, fast cuts on the beat, Hindi captions"', 'Made for Instagram Reel, YouTube or WhatsApp status', 'Quick asks: cut the silences, brighter colours, shorter intro'], 'Price before you press'],
  ];
  const tabs = $('#ttabs'), tscr = $('#tscr');
  if (tabs && tscr) {
    tabs.innerHTML = TOOLS.map((t, i) => `<button role="tab" id="tab-${t[0]}" aria-selected="${i ? 'false' : 'true'}" aria-controls="tpane" data-i="${i}">${t[1]}<span class="pg"></span></button>`).join('');
    tscr.innerHTML = TOOLS.map((t, i) => `<img src="/static/site/studio/${t[0]}.webp?v=s1" alt="The real ${t[1]} screen in Hoola Create Studio" width="1440" height="900" loading="lazy" class="${i ? '' : 'on'}">`).join('');
    $('#tpane').setAttribute('role', 'tabpanel');
    let ti = 0, tauto = !RM, pgT = null;
    const show = (i, user) => {
      ti = i; const t = TOOLS[i];
      $$('button', tabs).forEach((b, k) => b.setAttribute('aria-selected', String(k === i)));
      $$('img', tscr).forEach((im, k) => im.classList.toggle('on', k === i));
      $('#tt').textContent = t[1]; $('#tl').textContent = t[2]; $('#tu').innerHTML = t[3].map(x => `<li>${esc(x)}</li>`).join('');
      $('#tp').textContent = t[4]; $('#tlabel').textContent = 'Create · ' + t[1];
      $('#tpane').setAttribute('aria-labelledby', 'tab-' + t[0]);
      if (G && !RM) G.fromTo('#tpane > div:first-child > *', {y: 14, opacity: 0}, {y: 0, opacity: 1, duration: .45, stagger: .05, ease: 'power2.out'});
      if (user) tauto = false;
      $$('.pg', tabs).forEach(p => { p.style.width = '0'; });
      if (pgT) pgT.kill();
      if (tauto && G) pgT = G.fromTo($$('.pg', tabs)[i], {width: '0%'}, {width: '100%', duration: 6, ease: 'none', paused: !toolsOn, onComplete: () => show((ti + 1) % TOOLS.length)});
    };
    let toolsOn = false;
    new IntersectionObserver(es => { toolsOn = es[0].isIntersecting; if (pgT) toolsOn ? pgT.play() : pgT.pause(); }).observe(tabs.parentElement);
    tabs.addEventListener('click', e => { const b = e.target.closest('button'); if (b) show(+b.dataset.i, true); });
    tabs.addEventListener('keydown', e => { if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { const n = (ti + (e.key === 'ArrowRight' ? 1 : TOOLS.length - 1)) % TOOLS.length; show(n, true); $$('button', tabs)[n].focus(); } });
    show(0);
  }

  /* ---------- samples wall: drawn scenes now; Hoola's own pictures and clips replace them as they are made ---------- */
  const SAMPLES = [
    ['film0', 'Ad film', 'A shop owner in Jaipur hands a packed gift across the counter', 'product', 'gold', {pc: '#b4542f', pc2: '#f1c27d'}, 1],
    ['tpl0', 'Diwali reel', 'A sweet shop glowing with diyas for a Diwali sale', 'diya', 'night', {}, 0],
    ['film1', 'Short film', 'A boy flying a kite on an old Delhi rooftop at golden hour', 'city', 'gold', {}, 1],
    ['tpl1', 'Poster', 'A clay kulhad of masala chai, steam rising, warm morning light', 'product', 'ember', {pc: '#9c4a2b', pc2: '#e9b77a'}, 0],
    ['film2', 'Music video', 'A singer with a guitar on a Mumbai rooftop at night', 'music', 'night', {pc: '#C055F5'}, 1],
    ['tpl4', 'Lookbook', 'A deep red Banarasi saree in a haveli courtyard', 'portrait', 'rose', {pc: '#8a1f3a'}, 0],
    ['film3', 'Wedding film', 'Laughter at a haldi ceremony, marigolds and yellow drapes', 'portrait', 'gold', {pc: '#d18b1f'}, 1],
    ['tpl2', 'Travel reel', 'A car on a wet ghat road in the monsoon, mist over green hills', 'mount', 'green', {}, 0],
    ['film4', 'Real estate tour', 'A bright Pune flat with a balcony over green hills', 'city', 'sea', {}, 1],
    ['tpl6', 'Poster', 'A temple gopuram at dawn, golden rim light', 'mount', 'gold', {sx: '30%'}, 0],
  ];
  const SAMPLES2 = [
    ['sty1', 'Photoreal', 'An elderly Rajasthani man in a bright turban', 'portrait', 'ember', {pc: '#c2410c', skin: '#a8714f'}, 0],
    ['film5', 'Product launch', 'New wireless earbuds on a polished stone plinth', 'product', 'night', {pc: '#7C5CFF', pc2: '#c4b5fd'}, 1],
    ['sty5', 'Watercolour', 'A houseboat on the Kerala backwaters', 'mount', 'sea', {sx: '70%'}, 0],
    ['tpl7', 'Street food promo', 'Pav bhaji sizzling on a big tawa at night', 'product', 'ember', {pc: '#d9822b', pc2: '#fbbf24'}, 1],
    ['sty6', 'Anime', 'A girl on a Mumbai local train at sunset', 'city', 'rose', {}, 0],
    ['film7', 'Festival greeting', 'A family lighting diyas on a rangoli doorstep', 'diya', 'night', {}, 1],
    ['sty7', '3D clay', 'A tiny chai stall with a smiling chaiwala', 'portrait', 'green', {pc: '#2f7d5b'}, 0],
    ['tpl3', 'Podcast', 'A founder speaking into a podcast microphone', 'music', 'dusk', {pc: '#FFB15C'}, 1],
    ['sty8', 'Folk art', 'A Madhubani peacock and lotus flowers', 'mount', 'ember', {sx: '20%'}, 0],
    ['film6', 'Micro drama', 'Two friends at a chai stall in the rain, a twist on a phone', 'city', 'night', {}, 1],
  ];
  const tile = s => `<figure class="tile${s[6] ? ' w' : ''}" data-slot="${s[0]}" style="margin:0">${art(s[3], s[4], s[5])}<span class="ai">AI</span><figcaption class="cap"><b>${esc(s[1])}</b><br>${esc(s[2])}</figcaption></figure>`;
  const l1 = $('#lane1'), l2 = $('#lane2');
  if (l1 && l2) {
    l1.innerHTML = SAMPLES.map(tile).join('') + SAMPLES.map(tile).join('');
    l2.innerHTML = SAMPLES2.map(tile).join('') + SAMPLES2.map(tile).join('');
    $$('figure', l1).slice(SAMPLES.length).concat($$('figure', l2).slice(SAMPLES2.length)).forEach(f => f.setAttribute('aria-hidden', 'true'));
    if (G && !RM) {
      const run = (el, dir, dur) => {
        const w = () => el.scrollWidth / 2;
        const tw = G.fromTo(el, {x: dir < 0 ? 0 : () => -w()}, {x: dir < 0 ? () => -w() : 0, duration: dur, ease: 'none', repeat: -1, paused: true});
        el.addEventListener('pointerenter', () => G.to(tw, {timeScale: .15, duration: .5}));
        el.addEventListener('pointerleave', () => G.to(tw, {timeScale: 1, duration: .5}));
        return tw;
      };
      const a = run(l1, -1, 70), b = run(l2, 1, 80);
      window.ScrollTrigger.create({trigger: '#samples', start: 'top bottom', end: 'bottom top', onToggle: s => { s.isActive ? (a.play(), b.play()) : (a.pause(), b.pause()); }});
    } else { l1.style.flexWrap = l2.style.flexWrap = 'wrap'; l1.style.width = l2.style.width = 'auto'; l1.style.padding = l2.style.padding = '0 20px'; }
    // Hoola's own showcase pictures / clips (made by the owner in Create > Engines > Showcase) replace the drawn scenes
    fetch('/api/site/showcase', {credentials: 'omit'}).then(r => r.ok ? r.json() : null).then(d => {
      const m = d && d.slots || {};
      let n = 0;
      $$('.tile[data-slot]').forEach(f => {
        const s = m[f.dataset.slot]; if (!s) return;
        const a = $('.art', f); n++;
        if (s.clip && !RM) {
          const v = document.createElement('video');
          Object.assign(v, {muted: true, loop: true, playsInline: true, autoplay: true, preload: 'metadata'});
          v.setAttribute('muted', ''); v.setAttribute('playsinline', ''); v.setAttribute('aria-hidden', 'true');
          if (s.pic) v.poster = `/api/site/showcase/${f.dataset.slot}/pic`;
          v.src = `/api/site/showcase/${f.dataset.slot}/clip`;
          a.replaceWith(v);
        } else if (s.pic) {
          const im = new Image(); im.loading = 'lazy'; im.alt = ''; im.src = `/api/site/showcase/${f.dataset.slot}/pic`;
          im.onload = () => a.replaceWith(im);
        }
      });
      if (n) $('#snote').textContent = 'Pictures and clips on this wall were made in Hoola Create Studio. Everything Hoola makes carries an AI label.';
    }).catch(() => {});
  }

  /* ---------- price card: Haan, fingerprint, filming ---------- */
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

  /* ---------- languages ---------- */
  const LANGS = [['हिन्दी', 'Hindi'], ['Hinglish', ''], ['मराठी', 'Marathi'], ['தமிழ்', 'Tamil'], ['తెలుగు', 'Telugu'], ['বাংলা', 'Bengali'], ['ગુજરાતી', 'Gujarati'], ['ಕನ್ನಡ', 'Kannada'],
    ['മലയാളം', 'Malayalam'], ['ਪੰਜਾਬੀ', 'Punjabi'], ['ଓଡ଼ିଆ', 'Odia'], ['اردو', 'Urdu'], ['English', ''], ['Español', 'Spanish'], ['العربية', 'Arabic']];
  const mq = $('#marq');
  if (mq) {
    const one = LANGS.map(([a, b]) => `<span lang="">${esc(a)}${b ? `<small>${b}</small>` : ''}</span>`).join('');
    mq.innerHTML = one + one.replace(/<span lang="">/g, '<span aria-hidden="true">');
    if (G && !RM) {
      const tw = G.to(mq, {x: () => -mq.scrollWidth / 2, duration: 45, ease: 'none', repeat: -1, paused: true});
      window.ScrollTrigger.create({trigger: mq, start: 'top bottom', end: 'bottom top', onToggle: s => s.isActive ? tw.play() : tw.pause()});
    } else { mq.style.flexWrap = 'wrap'; mq.style.width = 'auto'; mq.style.padding = '0 20px'; }
  }

  /* ---------- made for ---------- */
  const MADE = [['Ad film', '30 s', 'A hook in two seconds, the product in use, happy customers, your logo.', 'product', 'gold', {pc: '#b4542f', pc2: '#f1c27d'}],
    ['Short film', '3 min', 'A story with a beginning, a turn and an end, scene by scene.', 'mount', 'dusk', {}],
    ['Music video', '2 min', 'Your song, cut to the beat with scenes that follow the words.', 'music', 'ember', {pc: '#FFB15C'}],
    ['Wedding film', '60 s', 'Highlights of the day, warm and candid.', 'portrait', 'rose', {pc: '#8a1f3a'}],
    ['Real estate tour', '60 s', 'A walk through a new flat, room by room, with the view.', 'city', 'sea', {}],
    ['Product launch', '45 s', 'The reveal, the details, the price and where to buy.', 'product', 'night', {pc: '#7C5CFF', pc2: '#c4b5fd'}],
    ['Micro drama', '90 s', 'A short episode with a twist, made for phones.', 'portrait', 'night', {pc: '#3b2a74'}],
    ['Festival greeting', '20 s', 'Diwali, Eid, Pongal or Christmas, from your business.', 'diya', 'night', {}]];
  const mg = $('#mgrid');
  if (mg) mg.innerHTML = MADE.map(m => `<div class="mcard"><div class="pic">${art(m[3], m[4], m[5])}<span class="len">${m[1]}</span></div><div class="bd"><b>${m[0]}</b><p>${esc(m[2])}</p></div></div>`).join('');

  /* ---------- reveals ---------- */
  if (G && !RM) {
    $$('main section:not(.hero) .eb, main section:not(.hero) .h2, main section:not(.hero) .lead').forEach(el =>
      G.from(el, {y: 28, opacity: 0, duration: .8, ease: 'power3.out', scrollTrigger: {trigger: el, start: 'top 88%'}}));
    G.from('.ag', {y: 34, opacity: 0, duration: .7, ease: 'power3.out', stagger: .06, scrollTrigger: {trigger: '.agents', start: 'top 85%'}});
    G.from('.mcard', {y: 34, opacity: 0, duration: .7, ease: 'power3.out', stagger: .06, scrollTrigger: {trigger: '#mgrid', start: 'top 85%'}});
    G.from('.tshot .frame', {y: 50, rotateX: 8, opacity: 0, duration: 1, ease: 'power3.out', transformPerspective: 1200, scrollTrigger: {trigger: '.tshot', start: 'top 85%'}});
    G.from('.kit .frame', {y: 50, opacity: 0, duration: 1, ease: 'power3.out', scrollTrigger: {trigger: '.kit', start: 'top 85%'}});
  }
})();

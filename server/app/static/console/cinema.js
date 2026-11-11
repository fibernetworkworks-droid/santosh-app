/* HOOLA CINEMA (v0.807, owner: "GO BUILD THE WHOLE SET AS HOOLA CINEMA END TO END") - one section inside the Create studio.
   A hub and nine tools over /api/cinema: Cinema still (Hoola's own picture engine), Motion transfer, Character swap,
   Item swap / edit, Restyle, Talking photo, Lip sync, Picture to video, Content factory - plus Characters (a person,
   a made-up character or a product saved once and picked in any tool).
   The studio hands this file its own helpers (S), so the page lives in the studio's shadow root and uses its styles.
   Every Create is HER tap and is asked once more, because it spends the server's video-engine credits. A source video
   needs her rights tick; a face or body that is driven needs her consent tick unless a saved character vouches for it.
   What she typed is kept in CN.f per tool, so a redraw (a poll, a tool switch) never wipes it. */
window.HoolaCinema = S => {
  const {api, esc, I, $, $$, toast, art, when} = S;
  const A = '/api/cinema';
  const CN = {tool: 'hub', ov: null, f: {}, ch: {name: '', kind: 'made', photos: [], consent: false, note: ''}, busy: false};
  const blank = () => ({model: '', prompt: '', images: [], video: null, audio: null, text: '', say: 'type', voice: '', language: 'Hindi',
    character: '', res: '', aspect: '', seconds: 0, look: '', camera: 'auto', extras: {}, consent: false, rights: false, avoid: '', sound: true,
    topic: '', count: 3, platform: 'reels', scenes: [], by: '', note: '', still: {camera: 'digital-ff', lens: 'modern-prime', focal: '35', aperture: 'f2.8', light: 'any'}, n: 1, quality: 'fast'});
  const F = t => (CN.f[t] ||= blank());
  const ov = () => CN.ov || {};
  const tool = id => (ov().tools || []).find(t => t.id === id) || {id, label: 'Hoola Cinema', blurb: ''};
  const modelsOf = id => (ov().models || []).filter(m => m.tools.includes(id));
  const model = (id, f) => modelsOf(id).find(m => m.id === f.model) || modelsOf(id)[0] || {};
  const ready = () => !!ov().key_set;
  const ART = {still: 'portrait', motion: 'film', swap: 'cast', edit: 'product', restyle: 'abstract', talk: 'voice', lipsync: 'portrait', animate: 'world', factory: 'city'};
  const ST = {waiting: 'In the queue', queuing: 'In the queue', generating: 'Making'};
  async function loadOv() { try { CN.ov = await api('GET', A); } catch (e) { CN.ov = {...(CN.ov || {}), error: e.message, tools: ov().tools || [], models: ov().models || [], jobs: ov().jobs || []}; } return CN.ov; }
  const open = t => { CN.tool = t; S.go('cinema'); };

  /* ---------- small parts ---------- */
  const head = (t, extra = '') => `<div class="cn-head"><button class="pillbtn" data-ct="hub">${I('left', 'width:14px;height:14px')}Hoola Cinema</button><b>${esc(t.label)}</b>${extra}</div><p class="note">${esc(t.blurb || '')}${t.needs ? ' ' + esc(t.needs) : ''}</p>`;
  const gate = () => ov().error ? `<div class="box"><h3>Hoola Cinema could not be read</h3><p class="note">${esc(ov().error)}</p></div>`
    : !ready() ? `<div class="box"><h3>The video engine is not connected</h3><p class="note">${esc(ov().setup || 'The owner adds the video engine key in the server settings.')}</p></div>` : '';
  const thumbOf = v => !v ? '' : v.local && /^image\//.test(v.type || '') ? `<img alt="" src="${esc(v.local)}">`
    : v.shelf && v.kind === 'image' ? `<img alt="" data-src="/api/create/items/${encodeURIComponent(v.ref)}">`
    : v.char ? `<img alt="" data-src="${A}/characters/${encodeURIComponent(v.char)}/photo/0">` : I(v.kind === 'video' ? 'video' : v.kind === 'audio' ? 'sound' : 'image', 'width:18px;height:18px');
  function slot(key, kind, label, v, hint) {
    return `<div class="cn-slot"><button class="refs" data-cnadd="${key}" data-kind="${kind}"><span class="cn-th">${v ? thumbOf(v) : I('upload', 'width:18px;height:18px')}</span><div style="min-width:0"><b>${v ? esc(v.name) : esc(label)}</b><small>${esc(v ? 'Tap to change' : hint)}</small></div></button>
      <button class="ib" data-cnshelf="${key}" data-kind="${kind}" aria-label="Pick from My creations" title="Pick from My creations">${I('lib', 'width:16px;height:16px')}</button>${v ? `<button class="ib" data-cnclear="${key}" aria-label="Remove">${I('x', 'width:16px;height:16px')}</button>` : ''}</div>`;
  }
  const photos = (f, m) => { const max = m.image?.max || 1, min = m.image?.min ?? 1;
    const rows = f.images.map((v, i) => slot('images:' + i, 'image', '', v, '')).join('');
    return rows + (f.images.length < max ? slot('images:' + f.images.length, 'image', f.images.length ? 'Add another photo' : min ? 'Add the photo' : 'Add a photo (optional)', null, `JPG, PNG or WebP · up to ${m.image?.mb || 10} MB${max > 1 ? ' · up to ' + max : ''}`) : ''); };
  const modelSel = (id, f) => { const ms = modelsOf(id), m = model(id, f); return ms.length < 2 ? `<p class="note">Model: <b>${esc(m.label || '')}</b>. ${esc(m.note || '')}</p>`
    : `<label class="fld">Model<select id="cnModel">${ms.map(x => `<option value="${esc(x.id)}"${x.id === m.id ? ' selected' : ''}>${esc(x.label)}</option>`).join('')}</select></label><p class="note">${esc(m.note || '')}</p>`; };
  const resRow = (f, m) => (m.res || []).length > 1 ? `<div class="lbl">Quality</div><div class="grid-opts">${m.res.map(r => `<button class="go" aria-pressed="${r === (f.res || m.res_default)}" data-cnres="${esc(r)}">${esc(/^\d+$/.test(r) ? r + 'p' : r)}</button>`).join('')}</div>` : '';
  const aspRow = (f, m) => (m.aspects || []).length ? `<div class="lbl">Shape</div><div class="grid-opts">${m.aspects.slice(0, 6).map(r => `<button class="go" aria-pressed="${r === (f.aspect || m.aspects[0])}" data-cnasp="${esc(r)}">${esc(r)}</button>`).join('')}</div>` : '';
  const durRow = (f, m) => { const d = m.duration; if (!d) return ''; const cur = f.seconds || d.default;
    return d.options ? `<div class="lbl">Length</div><div class="grid-opts">${d.options.map(s => `<button class="go" aria-pressed="${s === cur}" data-cnsec="${s}">${s} s</button>`).join('')}</div>`
      : `<label class="fld">Length in seconds (${d.min}-${d.max})<input id="cnSec" type="number" min="${d.min}" max="${d.max}" value="${cur}"></label>`; };
  const extraRows = (f, m) => (m.extras || []).map(x => `<label class="fld">${esc(x.label)}<select data-cnextra="${esc(x.key)}">${x.options.map(([v, t]) => `<option value="${esc(v)}"${v === (f.extras[x.key] || x.default) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`).join('');
  const tick = (id, on, text) => `<label class="cn-tick"><input type="checkbox" id="${id}"${on ? ' checked' : ''}><span>${text}</span></label>`;
  const charRow = f => { const c = (ov().characters || []).find(x => x.id === f.character);
    return `<button class="prow" data-cnchar aria-haspopup="menu"><span class="pi">${I('cast', 'width:16px;height:16px')}</span><div><small>Character</small><b>${c ? esc(c.name) : 'None - use a photo below'}</b></div>${I('down', 'width:14px;height:14px')}</button>`; };
  const left = () => { const o = ov(), bits = [o.credits_left != null ? Math.round(o.credits_left).toLocaleString('en-IN') + ' engine credits left' : '', o.today ? o.today.left + ' of ' + o.today.cap + ' jobs left today' : ''].filter(Boolean); return bits.length ? `<p class="note">${bits.join(' · ')}</p>` : ''; };
  const foot = (label = 'Create') => `<div class="pfoot"><button class="create" id="cnGo"${ready() ? '' : ' disabled'}>${I('spark', 'width:17px;height:17px')}${label} <small>engine credits</small></button></div>`;
  const stage = (title, id = 'cnres') => `<div class="stage"><div class="sbar"><b>${title}</b><span class="sp"></span><button class="ib" data-cnreload aria-label="Refresh">${I('redo', 'width:16px;height:16px')}</button></div><div class="sgrid" id="${id}"></div></div>`;

  /* ---------- job tiles ---------- */
  function tile(j) {
    const sub = [esc(j.model_label || ''), esc(tool(j.tool).label), when(j.created)].filter(Boolean).join(' · ');
    const t = esc(j.title || tool(j.tool).label);
    if (!j.done) return `<div class="res gening tall"><span class="thumb">${art(ART[j.tool] || 'film', 'cn' + j.id)}<span class="ring"></span><span class="pct">${esc(ST[j.status] || 'Making')}</span></span><b class="rt">${t}</b><small>${sub}</small></div>`;
    if (j.ok && j.item_id) { const it = (S.D.items || []).find(x => x.id === j.item_id);
      if (it) return S.itemTile(it, true).replace(/<\/div>\s*$/, `<small class="cn-send">${j.credits != null ? `<span class="num">${j.credits} credits</span>` : ''}<button class="lnk" data-cnsend="restyle:${esc(it.id)}">Restyle</button><button class="lnk" data-cnsend="lipsync:${esc(it.id)}">Lip sync</button><button class="lnk" data-cnrm="${esc(j.id)}">Hide</button></small></div>`); }
    if (j.ok) return `<div class="res tall"><span class="thumb"><span class="fail">${I('video', 'width:22px;height:22px')}<span>${j.save_error ? 'Made, but the copy for My creations failed: ' + esc(j.save_error) : 'Made - saving to My creations…'}</span></span></span><b class="rt">${t}</b><small>${sub}</small></div>`;
    return `<div class="res failed tall"><span class="thumb"><span class="fail">${I('x', 'width:22px;height:22px')}<span>${esc(j.error || 'The engine could not make it.')}</span></span></span><b class="rt">${t}</b><small>${sub} · <button class="lnk" data-cnrm="${esc(j.id)}">Remove</button></small></div>`;
  }
  function results() {
    const el = $('#cnres'); if (!el) return;
    const js = (ov().jobs || []).filter(j => CN.tool === 'hub' || j.tool === CN.tool);
    el.innerHTML = js.slice(0, CN.tool === 'hub' ? 8 : 60).map(tile).join('') || `<div class="empty" style="grid-column:1/-1"><div><h2>Your Cinema work appears here</h2><p class="mut">${CN.tool === 'hub' ? 'Pick a tool above to start.' : 'Fill the left side and press Create.'}</p></div></div>`;
    S.paintAll(el); S.hydrate(el);
  }
  const stillResults = () => { const el = $('#cnstill'); if (!el) return;
    el.innerHTML = S.running(['image']).map(j => S.jobTile(j, true)).join('') + S.failed(['image']).map(S.failTile).join('')
      + S.items(['image']).slice(0, 40).map(it => S.itemTile(it, true).replace(/<\/div>\s*$/, `<small class="cn-send"><button class="lnk" data-cnsend="animate:${esc(it.id)}">Make it move</button><button class="lnk" data-cnsend="talk:${esc(it.id)}">Make it talk</button></small></div>`)).join('')
      || `<div class="empty" style="grid-column:1/-1"><div><h2>Your stills appear here</h2><p class="mut">Describe the picture, choose the camera and press Create.</p></div></div>`;
    S.paintAll(el); S.hydrate(el); };

  /* ---------- views ---------- */
  function hub() { const o = ov(), nc = o.connected || {};
    const cards = (o.tools || []).map((t, i) => `<button class="tool" data-ct="${t.id}"><span class="thumb">${art(ART[t.id] || 'film', 'ct' + i)}</span><div style="min-width:0"><b>${esc(t.label)}</b><small>${esc(t.blurb)}</small></div></button>`).join('');
    return `<div class="home"><div class="sec-h" style="margin:0"><div><h2 style="font:400 26px/1.2 var(--serif)">Hoola Cinema</h2><p class="mut" style="margin-top:6px">Direct what already exists: move a character with a real performance, swap what is in a shot, make a photo speak, or turn one brief into a batch of clips.</p></div></div>
    ${gate()}
    <div class="cn-stats"><div><small>Video engine</small><b>${ready() ? 'Connected' : 'Not connected'}</b></div><div><small>Credits left</small><b class="num">${o.credits_left != null ? Math.round(o.credits_left).toLocaleString('en-IN') : '-'}</b></div><div><small>Jobs today</small><b class="num">${o.today ? o.today.used + ' of ' + o.today.cap : '-'}</b></div><div><small>Characters</small><b class="num">${(o.characters || []).length}</b></div></div>
    <section><div class="sec-h"><h2>Tools</h2><a data-ct="characters">Characters</a></div><div class="tools">${cards}
      <button class="tool" data-ct="characters"><span class="thumb">${art('cast', 'ctc')}</span><div style="min-width:0"><b>Characters</b><small>Save a person, a made-up character or a product once; pick it in any tool.</small></div></button></div></section>
    <section><div class="sec-h"><h2>Recent Cinema work</h2><button class="ib" data-cnreload aria-label="Refresh">${I('redo', 'width:16px;height:16px')}</button></div><div class="sgrid cn-flat" id="cnres"></div></section>
    <p class="note">${o.refresh_error ? esc(o.refresh_error) + ' ' : ''}Not there yet${nc.rupee_price_before === false ? ': a rupee price before you start (the engine publishes no price list, so you see credits left and what each finished job used)' : ''}, an AI mark on the finished video, a character trained from many photos, asking for Cinema from chat, and the phone app. Request shapes were read from the engine's documents on ${esc(o.spec_date || '')}.</p></div>`; }

  function videoTool(id) { const t = tool(id), f = F(id), m = model(id, f), o = ov();
    const needsFace = ['motion', 'swap', 'talk'].includes(id), src = ['motion', 'swap', 'edit', 'restyle', 'lipsync'].includes(id);
    const c = (o.characters || []).find(x => x.id === f.character);
    let body = modelSel(id, f);
    if (needsFace) body += charRow(f) + (f.character ? '' : photos(f, m));
    else if (m.image && id !== 'restyle') body += `<div class="lbl">${id === 'animate' ? 'The picture' : 'Photos of the new item (optional)'}</div>` + photos(f, m);
    if (src) body += slot('video', 'video', 'Add the source video', f.video, `MP4 or MOV · up to ${Math.min(25, m.video?.mb || 25)} MB${m.video?.seconds ? ' · ' + m.video.seconds[0] + '-' + m.video.seconds[1] + ' s' : ''}`);
    if (id === 'restyle') body += `<div class="lbl">Look</div><div class="chips">${(o.restyles || []).map(r => `<button class="chip" aria-pressed="${r.id === f.look}" data-cnlook="${esc(r.id)}">${esc(r.label)}</button>`).join('')}</div>`;
    if (id === 'animate') body += `<div class="lbl">Camera</div><div class="chips cn-cams">${(o.camera_moves || []).map(r => `<button class="chip" aria-pressed="${r.id === f.camera}" data-cncam="${esc(r.id)}" title="${esc(r.text)}">${esc(r.label)}</button>`).join('')}</div>`;
    if (m.audio) body += `<div class="seg" role="group" aria-label="Voice"><button aria-pressed="${f.say === 'type'}" data-cnsay="type">Type the words</button><button aria-pressed="${f.say === 'file'}" data-cnsay="file">Use an audio file</button></div>`
      + (f.say === 'file' ? slot('audio', 'audio', 'Add the audio', f.audio, `MP3, WAV or M4A · up to ${Math.min(25, m.audio.mb)} MB${m.audio.seconds ? ' · up to ' + m.audio.seconds[1] + ' s' : ''}`)
        : `<div class="box"><h3>Words to speak <span class="dim num" style="font-size:12.5px;font-weight:400" id="cnTextN">${f.text.length}</span></h3><textarea id="cnText" rows="4" maxlength="5000" placeholder="Namaste! Is Diwali par hamari dukaan par har mithai par 10% ki chhoot hai.">${esc(f.text)}</textarea></div>
          <div class="prow2"><label class="fld">Voice<select id="cnVoice"><option value="">My Hoola voice</option>${Object.entries(o.voices || {}).map(([g, vs]) => Object.keys(vs).map(v => `<option value="${esc(v)}"${v === f.voice ? ' selected' : ''}>${esc(v)} · ${g === 'female' ? 'woman' : 'man'}</option>`).join('')).join('')}</select></label>
          <label class="fld">Language<select id="cnLang">${(o.languages || ['Hindi']).map(l => `<option${l === f.language ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select></label></div>${o.voice_ready ? '' : '<p class="note">Hoola’s own voice is not connected on this server, so use an audio file.</p>'}`);
    if (m.prompt_max) body += `<div class="box"><h3>${id === 'edit' ? 'What to change' : id === 'restyle' ? 'Anything else (optional)' : id === 'animate' ? 'What moves' : 'Direction (optional)'}</h3><textarea id="cnPrompt" rows="3" maxlength="${Math.min(m.prompt_max, 5000)}" placeholder="${esc({edit: 'Replace the red bottle on the table with the bottle in my photo. Keep everything else.', animate: 'Steam rises from the cup, the curtain moves in a soft breeze', talk: 'She speaks warmly to the camera, small nods, gentle smile', motion: 'Leave empty to copy the movement exactly'}[id] || '')}">${esc(f.prompt)}</textarea></div>`;
    body += resRow(f, m) + aspRow(f, m) + durRow(f, m) + extraRows(f, m);
    if (m.avoid) body += `<label class="fld">Keep out<input id="cnAvoid" maxlength="300" value="${esc(f.avoid)}" placeholder="text, watermark, blur"></label>`;
    if (m.sound) body += `<div class="btool"><span class="dim" style="font-size:13px">Sound from the model</span><span style="flex:1"></span><button class="sw" role="switch" aria-checked="${f.sound}" data-cnsound aria-label="Sound from the model"><i></i></button></div>`;
    if (src) body += tick('cnRights', f.rights, 'This is my video, or I have the right to use it.');
    if ((needsFace && !(c && id !== 'lipsync')) || id === 'lipsync') body += tick('cnConsent', f.consent, 'The person shown is me, or they agreed to being used in AI videos.');
    return `<div class="gen"><div class="panel"><div class="pbody">${head(t)}${gate()}${body}
      <p class="note">Each Create spends the server’s video-engine credits. The finished video is saved to My creations and is AI-made: say so when you post it.</p>${left()}</div>${foot()}</div>${stage('Your ' + esc(t.label.toLowerCase()) + ' work')}</div>`; }

  function still() { const t = tool('still'), f = F('still'), o = ov(), st = o.still || {};
    const sel = (k, label) => `<label class="fld">${label}<select data-cnstill="${k}">${(st[k] || []).map(r => `<option value="${esc(r.id)}"${r.id === f.still[k] ? ' selected' : ''}>${esc(r.label)}</option>`).join('')}</select></label>`;
    return `<div class="gen"><div class="panel"><div class="pbody">${head(t)}
      <div class="box"><h3>Describe the picture</h3><textarea id="cnPrompt" rows="4" maxlength="3000" placeholder="An old chai seller pouring tea at a railway platform at dawn, steam in cold air">${esc(f.prompt)}</textarea></div>
      <div class="prow2">${sel('camera', 'Camera')}${sel('lens', 'Lens')}</div><div class="prow2">${sel('focal', 'Focal length')}${sel('aperture', 'Aperture')}</div>${sel('light', 'Light')}
      <div class="lbl">Shape</div><div class="grid-opts">${['16:9', '21:9', '9:16', '1:1', '4:5', '3:2'].map(r => `<button class="go" aria-pressed="${r === (f.aspect || '16:9')}" data-cnasp="${r}">${r}</button>`).join('')}</div>
      <div class="lbl">Quality</div><div class="grid-opts">${[['fast', 'Fast'], ['best', 'Best']].map(([k, l]) => `<button class="go" aria-pressed="${k === f.quality}" data-cnq="${k}">${l}</button>`).join('')}</div>
      <p class="note">Made by Hoola’s own picture engine, the same one as the Image page. Finished stills can go straight to Picture to video or Talking photo.</p></div>
      <div class="pfoot"><button class="create" id="cnGo">${I('spark', 'width:17px;height:17px')}Create</button></div></div>${stage('Your pictures', 'cnstill')}</div>`; }

  function factory() { const t = tool('factory'), f = F('factory'), m = model('factory', f), o = ov();
    const scenes = f.scenes.length ? `<div class="lbl">Scenes - edit any of them, then make the clips</div>${f.scenes.map((s, i) => `<div class="box cn-scene"><h3>Clip ${i + 1}<button class="lnk" data-cnscrm="${i}">Remove</button></h3><textarea data-cnscene="${i}" rows="3" maxlength="${Math.min(m.prompt_max || 800, 2000)}">${esc(s)}</textarea></div>`).join('')}${f.note ? `<p class="note">${esc(f.note)}</p>` : ''}` : '';
    return `<div class="gen"><div class="panel"><div class="pbody">${head(t)}${gate()}
      <div class="box"><h3>What are the clips about?</h3><textarea id="cnTopic" rows="3" maxlength="600" placeholder="Our new mango lassi at the shop: fresh Alphonso mangoes, thick and cold, served in a kulhad">${esc(f.topic)}</textarea></div>
      <div class="lbl">Where it will be posted</div><div class="grid-opts">${(o.platforms || []).map(p => `<button class="go" aria-pressed="${p.id === f.platform}" data-cnplat="${esc(p.id)}">${esc(p.label)}</button>`).join('')}</div>
      <div class="lbl">Look</div><div class="chips">${(o.looks || []).map(r => `<button class="chip" aria-pressed="${r.id === (f.look || 'any')}" data-cnlook="${esc(r.id)}">${esc(r.label)}</button>`).join('')}</div>
      <div class="lbl">Camera</div><div class="chips cn-cams">${(o.camera_moves || []).map(r => `<button class="chip" aria-pressed="${r.id === f.camera}" data-cncam="${esc(r.id)}" title="${esc(r.text)}">${esc(r.label)}</button>`).join('')}</div>
      <div class="btool"><span class="dim" style="font-size:13px">How many clips</span><span style="flex:1"></span><button class="ib" data-cncount="-1" aria-label="Fewer">${I('minus', 'width:15px;height:15px')}</button><b class="num" id="cnCount" style="min-width:20px;text-align:center">${f.count}</b><button class="ib" data-cncount="1" aria-label="More">${I('plus', 'width:15px;height:15px')}</button></div>
      <button class="btn sec" id="cnWrite">${I('pen', 'width:16px;height:16px')}${f.scenes.length ? 'Write the scenes again' : 'Write the scenes'} <small class="dim" style="font-weight:400">free</small></button>
      ${scenes}${f.scenes.length ? modelSel('factory', f) + resRow(f, m) + durRow(f, m) + (m.sound ? `<div class="btool"><span class="dim" style="font-size:13px">Sound from the model</span><span style="flex:1"></span><button class="sw" role="switch" aria-checked="${f.sound}" data-cnsound aria-label="Sound from the model"><i></i></button></div>` : '') : ''}
      <p class="note">Writing the scenes costs nothing. Making the clips spends the server’s video-engine credits, one job per clip.</p>${left()}</div>
      ${f.scenes.length ? foot(`Make ${f.scenes.length} clip${f.scenes.length === 1 ? '' : 's'}`) : ''}</div>${stage('Your factory clips')}</div>`; }

  function chars() { const o = ov(), c = CN.ch, kinds = o.character_kinds || [];
    const list = (o.characters || []).map(x => `<div class="res tall"><span class="thumb"><img alt="" data-src="${A}/characters/${encodeURIComponent(x.id)}/photo/0"></span><b class="rt">${esc(x.name)}</b><small>${esc((kinds.find(k => k.id === x.kind) || {}).label || '')} · ${x.photos} photo${x.photos === 1 ? '' : 's'} · <button class="lnk" data-cnchrm="${esc(x.id)}">Remove</button></small></div>`).join('')
      || `<div class="empty" style="grid-column:1/-1"><div><h2>No characters yet</h2><p class="mut">Save one on the left. It then appears under Character in Motion transfer, Character swap and Talking photo.</p></div></div>`;
    return `<div class="gen"><div class="panel"><div class="pbody">${head({label: 'Characters', blurb: 'Save a person, a made-up character or a product once (1 to 5 photos) and pick it in any Cinema tool.'})}
      <label class="fld">Name<input id="cnChName" maxlength="40" value="${esc(c.name)}" placeholder="Meera, our mascot, the brass diya…"></label>
      <label class="fld">This is<select id="cnChKind">${kinds.map(k => `<option value="${esc(k.id)}"${k.id === c.kind ? ' selected' : ''}>${esc(k.label)}</option>`).join('')}</select></label>
      <div class="lbl">Photos</div>${c.photos.map((v, i) => slot('chp:' + i, 'image', '', v, '')).join('')}${c.photos.length < 5 ? slot('chp:' + c.photos.length, 'image', c.photos.length ? 'Add another photo' : 'Add a photo', null, 'Clear, well lit, face and shoulders for a person') : ''}
      <label class="fld">Note (optional)<input id="cnChNote" maxlength="200" value="${esc(c.note)}" placeholder="Always in a blue kurta"></label>
      ${c.kind === 'person' ? tick('cnChConsent', c.consent, 'This is me, or this person agreed to being used in AI videos. Hoola keeps the time of this yes.') : ''}
      <p class="note">A real person is saved only with their yes. Photos are kept on this server only and go to the video engine when you start a job with this character.</p></div>
      <div class="pfoot"><button class="create" id="cnChSave">${I('check', 'width:17px;height:17px')}Save character</button></div></div>
      <div class="stage"><div class="sbar"><b>Your characters</b></div><div class="sgrid" id="cnchars">${list}</div></div></div>`; }

  const view = () => CN.tool === 'hub' ? hub() : CN.tool === 'still' ? still() : CN.tool === 'factory' ? factory() : CN.tool === 'characters' ? chars() : videoTool(CN.tool);

  /* ---------- behaviour ---------- */
  function wire(el) {
    const me = S.token(), id = CN.tool, f = F(id);
    const live = () => S.token() === me && S.view() === 'cinema';
    const keep = () => { const v = i => $('#' + i, el)?.value;
      if (id === 'characters') { CN.ch.name = v('cnChName') ?? CN.ch.name; CN.ch.kind = v('cnChKind') ?? CN.ch.kind; CN.ch.note = v('cnChNote') ?? CN.ch.note; CN.ch.consent = !!$('#cnChConsent', el)?.checked; return; }
      f.prompt = v('cnPrompt') ?? f.prompt; f.text = v('cnText') ?? f.text; f.voice = v('cnVoice') ?? f.voice; f.language = v('cnLang') ?? f.language;
      f.avoid = v('cnAvoid') ?? f.avoid; f.topic = v('cnTopic') ?? f.topic; f.model = v('cnModel') ?? f.model;
      const s = +(v('cnSec') ?? 0); if (s > 0) f.seconds = Math.round(s);
      if ($('#cnRights', el)) f.rights = $('#cnRights', el).checked; if ($('#cnConsent', el)) f.consent = $('#cnConsent', el).checked;
      $$('[data-cnscene]', el).forEach(t => { f.scenes[+t.dataset.cnscene] = t.value; });
      $$('[data-cnextra]', el).forEach(x => { f.extras[x.dataset.cnextra] = x.value; });
      $$('[data-cnstill]', el).forEach(x => { f.still[x.dataset.cnstill] = x.value; }); };
    const redo = () => { keep(); S.go('cinema'); };
    const tickJobs = async () => {
      if (!live()) return;
      await loadOv();
      if ((ov().jobs || []).some(j => j.item_id && !(S.D.items || []).some(x => x.id === j.item_id))) await S.load('items', true);
      if (!live()) return; results();
      if ((ov().jobs || []).some(j => !j.done || (j.ok && !j.item_id && !j.save_error))) S.later(tickJobs, 6000);
    };
    if (!CN.ov) { loadOv().then(() => { if (live()) S.go('cinema'); }); return; }
    if (id === 'still') S.load('items').then(() => { if (live()) stillResults(); });
    else if (id !== 'characters') { S.load('items').then(() => { if (live()) results(); }); S.later(tickJobs, 1500); }
    $('#cnText', el)?.addEventListener('input', e => { $('#cnTextN', el).textContent = e.target.value.length; });
    el.addEventListener('change', e => { const t = e.target;
      if (t.id === 'cnModel') { keep(); f.res = ''; f.aspect = ''; f.seconds = 0; f.extras = {}; S.go('cinema'); }
      if (t.id === 'cnChKind') redo(); });

    const put = (key, v) => { const [k, i] = key.split(':');
      if (k === 'images') f.images[+i] = v; else if (k === 'chp') CN.ch.photos[+i] = v; else f[k] = v; };
    const clear = key => { const [k, i] = key.split(':');
      if (k === 'images') f.images.splice(+i, 1); else if (k === 'chp') CN.ch.photos.splice(+i, 1); else f[k] = null; };
    const ACC = {image: ['image/png,image/jpeg,image/webp', /^image\/(png|jpeg|webp)$/], video: ['video/mp4,video/quicktime,.mov,.mp4', /^video\//], audio: ['audio/*', /^audio\//]};
    async function addFile(key, kind) {
      const [file] = await S.pick(ACC[kind][0]); if (!file) return;
      try { toast('Uploading ' + file.name); const u = await S.upload(file, ACC[kind][1]); keep(); put(key, {ref: u.file_id, name: u.name, type: u.type, local: u.local, kind}); if (live()) S.go('cinema'); }
      catch (er) { toast(er.message, true); }
    }
    async function fromShelf(btn, key, kind) {
      await S.load('items');
      const its = S.items(kind === 'image' ? ['image', 'cast'] : kind === 'video' ? ['video'] : ['voice', 'song', 'dub']).filter(it => it.mime.startsWith(kind + '/')).slice(0, 30);
      if (!its.length) { toast('Nothing of this kind in My creations yet'); return; }
      S.menu(btn, its.map(it => ({v: it.id, label: it.title, sub: when(it.created)})), '', v => { const it = its.find(x => x.id === v); keep(); put(key, {ref: it.id, name: it.title, type: it.mime, shelf: true, kind}); S.go('cinema'); }, 'My creations');
    }
    const refs = L => L.filter(Boolean).map(v => v.ref);

    async function create(b) {
      keep();
      if (id === 'still') {
        if (!f.prompt.trim()) { $('#cnPrompt', el).focus(); toast('Describe the picture first'); return; }
        b.disabled = true;
        try { const r = await api('POST', A + '/still/prompt', {prompt: f.prompt, ...f.still});
          await S.startJob({kind: 'image', prompt: r.prompt, file_ids: [], aspect: f.aspect || '16:9', quality: f.quality, count: 1, style: '', title: f.prompt.slice(0, 48)}, () => { if (live()) stillResults(); }); }
        catch (er) { toast(er.message, true); }
        b.disabled = false; return;
      }
      const m = model(id, f);
      if (id === 'factory') {
        const scenes = f.scenes.map(s => s.trim()).filter(Boolean); if (!scenes.length) { toast('Write the scenes first'); return; }
        if (!confirm(`Make ${scenes.length} clip${scenes.length === 1 ? '' : 's'} with ${m.label}? Each one spends video-engine credits.`)) return;
        b.disabled = true; b.classList.add('busy');
        try { const p = (ov().platforms || []).find(x => x.id === f.platform);
          const r = await api('POST', A + '/factory/start', {model: m.id, scenes, resolution: f.res, aspect: (m.aspects || []).includes(p?.aspect) ? p.aspect : '', seconds: f.seconds || null, sound: m.sound ? f.sound : null, confirm: true});
          toast(r.stopped ? `${r.started.length} of ${r.asked} started. ${r.stopped}` : `${r.started.length} clips started`, !!r.stopped); await loadOv(); if (live()) S.go('cinema'); }
        catch (er) { toast(er.message, true); b.disabled = false; b.classList.remove('busy'); }
        return;
      }
      const body = {tool: id, model: m.id, prompt: f.prompt.trim(), look: f.look, camera: f.camera, images: id === 'restyle' ? [] : refs(f.images), video: f.video?.ref || '',
        audio: f.say === 'file' ? (f.audio?.ref || '') : '', text: f.say === 'type' ? f.text.trim() : '', voice: f.voice, language: f.language, character: f.character,
        resolution: f.res, aspect: f.aspect, seconds: f.seconds || null, avoid: f.avoid.trim(), sound: m.sound ? f.sound : null, extras: f.extras, consent: f.consent, rights: f.rights, confirm: true};
      if (m.video && !body.video) { toast('Add the source video first'); return; }
      if (m.image && (m.image.min ?? 1) > 0 && !body.images.length && !body.character) { toast('Add the photo or pick a character first'); return; }
      if (id === 'animate' && !body.images.length) { toast('Add the picture first'); return; }
      if (id === 'restyle' && !f.look) { toast('Pick a look first'); return; }
      if (m.audio && !body.audio && !body.text) { toast(f.say === 'file' ? 'Add the audio first' : 'Type the words to speak first'); return; }
      if ($('#cnRights', el) && !f.rights) { toast('Tick the box about your right to use the video'); return; }
      if ($('#cnConsent', el) && !f.consent) { toast('Tick the box about the person shown'); return; }
      if (!confirm(`Start this with ${m.label}? It spends video-engine credits.`)) return;
      b.disabled = true; b.classList.add('busy');
      try { await api('POST', A + '/start', body); toast('Started'); await loadOv(); if (live()) S.go('cinema'); }
      catch (er) { toast(er.message, true); b.disabled = false; b.classList.remove('busy'); }
    }

    el.addEventListener('click', async e => {
      const a = e.target.closest('a[data-ct]'); if (a) { e.preventDefault(); keep(); open(a.dataset.ct); return; }
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.cnsend) { const [to, iid] = b.dataset.cnsend.split(':'); send(iid, to); return; }
      if (await S.itemAction(b)) return;
      const d = b.dataset;
      if (d.ct) { keep(); open(d.ct); return; }
      if (d.cnadd) { await addFile(d.cnadd, d.kind); return; }
      if (d.cnshelf) { await fromShelf(b, d.cnshelf, d.kind); return; }
      if (d.cnclear) { keep(); clear(d.cnclear); S.go('cinema'); return; }
      if (d.cnres) { f.res = d.cnres; $$('[data-cnres]', el).forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (d.cnasp) { f.aspect = d.cnasp; $$('[data-cnasp]', el).forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (d.cnsec) { f.seconds = +d.cnsec; $$('[data-cnsec]', el).forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (d.cnq) { f.quality = d.cnq; $$('[data-cnq]', el).forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (d.cnlook) { f.look = d.cnlook; $$('[data-cnlook]', el).forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (d.cncam) { f.camera = d.cncam; $$('[data-cncam]', el).forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (d.cnplat) { f.platform = d.cnplat; $$('[data-cnplat]', el).forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (d.cnsay) { keep(); f.say = d.cnsay; S.go('cinema'); return; }
      if (b.hasAttribute('data-cnsound')) { f.sound = !f.sound; b.setAttribute('aria-checked', String(f.sound)); return; }
      if (d.cncount) { f.count = Math.max(1, Math.min(ov().max_batch || 6, f.count + +d.cncount)); $('#cnCount', el).textContent = f.count; return; }
      if (d.cnscrm) { keep(); f.scenes.splice(+d.cnscrm, 1); S.go('cinema'); return; }
      if (b.hasAttribute('data-cnchar')) { const cs = ov().characters || [];
        S.menu(b, [{v: '', label: 'None - use a photo'}, ...cs.map(c => ({v: c.id, label: c.name, sub: (ov().character_kinds || []).find(k => k.id === c.kind)?.label})), {v: '+', label: 'Save a new character…'}], f.character,
          v => { keep(); if (v === '+') { open('characters'); return; } f.character = v; S.go('cinema'); }, 'Character'); return; }
      if (b.hasAttribute('data-cnreload')) { keep(); S.later(() => {}, 0); await loadOv(); await S.load('items', true); if (live()) S.go('cinema'); return; }
      if (d.cnrm) { try { await api('DELETE', A + '/jobs/' + encodeURIComponent(d.cnrm)); await loadOv(); if (live()) results(); } catch (er) { toast(er.message, true); } return; }
      if (d.cnchrm) { if (!confirm('Remove this character and its photos?')) return;
        try { await api('DELETE', A + '/characters/' + encodeURIComponent(d.cnchrm)); await loadOv(); if (live()) S.go('cinema'); } catch (er) { toast(er.message, true); } return; }
      if (b.id === 'cnWrite') { keep(); if (f.topic.trim().length < 4) { $('#cnTopic', el).focus(); toast('Say what the clips are about'); return; }
        b.disabled = true; b.classList.add('busy');
        try { const r = await api('POST', A + '/factory/scenes', {topic: f.topic.trim(), count: f.count, look: f.look, camera: f.camera, platform: (ov().platforms || []).find(p => p.id === f.platform)?.label || ''});
          f.scenes = r.scenes; f.note = r.note || ''; if (live()) S.go('cinema'); }
        catch (er) { toast(er.message, true); b.disabled = false; b.classList.remove('busy'); } return; }
      if (b.id === 'cnChSave') { keep(); const c = CN.ch;
        if (!c.name.trim()) { $('#cnChName', el).focus(); toast('Give the character a name'); return; }
        if (!c.photos.filter(Boolean).length) { toast('Add at least one photo'); return; }
        if (c.kind === 'person' && !c.consent) { toast('Tick the box: a real person is saved only with their yes'); return; }
        b.disabled = true;
        try { await api('POST', A + '/characters', {name: c.name.trim(), kind: c.kind, photos: refs(c.photos), consent: c.consent, note: c.note});
          CN.ch = {name: '', kind: 'made', photos: [], consent: false, note: ''}; toast('Character saved'); await loadOv(); if (live()) S.go('cinema'); }
        catch (er) { toast(er.message, true); b.disabled = false; } return; }
      if (b.id === 'cnGo') create(b);
    });
  }

  // a creation handed to Cinema from anywhere in the studio: a picture opens Picture to video (or Talking photo),
  // a video is loaded into every tool that takes a source video and the named one opens.
  function send(itemId, to) {
    const it = (S.D.items || []).find(x => x.id === itemId); if (!it) return false;
    const v = {ref: it.id, name: it.title, type: it.mime, shelf: true, kind: it.mime.split('/')[0]};
    if (v.kind === 'image') { const t = to === 'talk' ? 'talk' : 'animate'; F(t).images = [v]; F(t).character = ''; open(t); toast('Picture loaded'); return true; }
    if (v.kind === 'video') { ['motion', 'swap', 'edit', 'restyle', 'lipsync'].forEach(t => { F(t).video = v; }); open(['motion', 'swap', 'edit', 'restyle', 'lipsync'].includes(to) ? to : 'restyle'); toast('Video loaded'); return true; }
    if (v.kind === 'audio') { F('talk').audio = v; F('talk').say = 'file'; F('lipsync').audio = v; open('talk'); toast('Audio loaded'); return true; }
    return false;
  }
  return {view, wire, send, open, reset: () => { CN.ov = null; }};
};

/* Hoola web workspace. A form creates a real agent turn on the existing API.
   The server owns generation, costs, approvals and output persistence. */
'use strict';
window.HoolaWorkspace = ctx => {
  const {api, esc, toast} = ctx;
  const root = document.getElementById('creative');
  const MODES = {
    image: {label:'Image', title:'An idea, ready to take shape.', tool:'Image creation',
      hint:'Describe the subject, setting, style and words to include.',
      starter:'Create a premium product launch image for FNW AI Node. Use violet, indigo and a small orange accent. Keep the product name readable.'},
    video: {label:'Video & motion', title:'Give your idea a story.', tool:'Video studio',
      hint:'Describe the shots, subject and movement. Hoola prepares the storyboard first.',
      starter:'Plan a product launch film for FNW AI Node: a wide product reveal, a close-up of the hardware, then the brand ending. English voiceover. No unverified product claims.'},
    research: {label:'Research', title:'A clearer view of what’s next.', tool:'Research brief',
      hint:'Describe your question, scope and the decision the research should support.',
      starter:'Research the Indian ISP automation market. Compare existing tools using official sources, identify operator workflow gaps, and give a cited launch plan. Separate evidence from assumptions.'},
    document: {label:'Document', title:'Put your thinking into words.', tool:'Document creation',
      hint:'Describe the audience, purpose, structure and the source material to use.',
      starter:'Create a professional FNW AI Node product overview for an ISP owner. Use only the features in my attached source files. Clearly mark any details that still need confirmation.'}
  };
  const ASPECTS = ['16:9','1:1','9:16','4:5','3:4','4:3'];
  let mode='image', files=[], pending=0, sending=false, generation=0, controller=null;
  let drafts={};
  const $ = s => root.querySelector(s);
  const take = () => {
    if (!$('#cw-prompt')) return;
    drafts[mode] = {text:$('#cw-prompt').value, aspect:$('#cw-aspect')?.value,
      quality:$('#cw-quality')?.value, seconds:$('#cw-seconds')?.value,
      language:$('#cw-language')?.value, format:$('#cw-format')?.value, sources:$('#cw-sources')?.value};
  };
  function render() {
    const m=MODES[mode],d=drafts[mode]||{};
    root.innerHTML=`<div class="cw-heading"><div><span class="cw-eyebrow">HOOLA CREATIVE WORKSPACE</span><h2>${m.title}</h2><p>Start here. Keep refining in the conversation.</p></div><button class="btn soft" type="button" data-cw="library">Creations ↗</button></div>
      <div class="cw-tabs" role="group" aria-label="Creation type">${Object.entries(MODES).map(([k,v])=>`<button type="button" data-mode="${k}" aria-pressed="${k===mode}">${v.label}</button>`).join('')}</div>
      <div class="cw-layout"><form class="cw-form gl" id="cw-form">
        <label class="cw-label" for="cw-prompt">${mode==='research'?'What do you want to find out?':'What would you like to create?'}</label>
        <textarea id="cw-prompt" maxlength="12000" required placeholder="${esc(m.hint)}">${esc(d.text||'')}</textarea>
        <div class="cw-options">
          ${['image','video'].includes(mode)?`<label>Format<select id="cw-aspect">${ASPECTS.filter(a=>mode!=='video'||a!=='4:5').map(a=>`<option${a===(d.aspect||'16:9')?' selected':''}>${a}</option>`).join('')}</select></label>`:''}
          ${mode==='image'?`<label>Quality<select id="cw-quality"><option value="fast"${d.quality!=='best'?' selected':''}>Standard</option><option value="best"${d.quality==='best'?' selected':''}>Best · higher cost</option></select></label>`:''}
          ${mode==='video'?`<label>Length<select id="cw-seconds">${[15,30,60].map(n=>`<option value="${n}"${String(n)===(d.seconds||'15')?' selected':''}>${n} seconds</option>`).join('')}</select></label><label>Voiceover<select id="cw-language">${['Hindi','Marathi','English'].map(l=>`<option${l===(d.language||'English')?' selected':''}>${l}</option>`).join('')}</select></label>`:''}
          ${mode==='research'?`<label>Source preference<select id="cw-sources"><option value="web"${d.sources!=='files'?' selected':''}>Public web + attached files</option><option value="files"${d.sources==='files'?' selected':''}>Attached files only</option></select></label>`:''}
          ${mode==='document'?`<label>Output<select id="cw-format">${['Word (.docx)','PDF (.pdf)','Excel (.xlsx)','Presentation (.pptx)'].map(l=>`<option${l===(d.format||'Word (.docx)')?' selected':''}>${l}</option>`).join('')}</select></label>`:''}
        </div>
        <div class="cw-refhead"><span>${mode==='image'?'Reference images':'Source files'}</span><button class="btn soft" type="button" data-cw="attach">+ Add files</button><input id="cw-files" type="file" multiple ${mode==='image'?'accept="image/png,image/jpeg,image/webp"':''} hidden></div>
        <div id="cw-refs" class="cw-refs"></div>
        <div class="cw-send"><span id="cw-sending" role="status" aria-live="polite"></span><button class="btn go" id="cw-submit" type="submit">${mode==='video'?'Prepare storyboard':mode==='research'?'Start research':mode==='document'?'Create document':'Create image'} ↗</button></div>
        <p class="cw-note">${mode==='video'?'Review the storyboard and cost before paid video generation.':mode==='image'?'Generation uses your configured image service and account budget.':'Hoola works with the sources and services available to your account.'}</p>
      </form><aside class="cw-guide"><div class="cw-orbit" aria-hidden="true"><span>h</span><i></i><i></i><i></i></div><span class="cw-eyebrow">${m.tool}</span><h3>Your work.<br>Your direction.</h3><p>${m.hint}</p><button class="cw-example" type="button" data-cw="example">Try a starting brief <span>↗</span></button><div class="cw-path"><span>01 &nbsp; Give Hoola a brief</span><span>02 &nbsp; Follow the real work in chat</span><span>03 &nbsp; Review, refine and export</span></div></aside></div>`;
    $('#cw-prompt').addEventListener('input',take);
    root.querySelectorAll('select').forEach(e=>e.addEventListener('change',take));
    $('#cw-files').addEventListener('change',e=>{upload([...e.target.files]);e.target.value='';});
    $('#cw-form').addEventListener('submit',submit);
    drawFiles();
  }
  function drawFiles() {
    const box=$('#cw-refs');if(!box)return;
    box.innerHTML=files.length?files.map((f,i)=>`<span class="fchip">${esc(f.name)}${f.loading?' · uploading…':''}<button type="button" data-rm="${i}" aria-label="Remove ${esc(f.name)}"${sending?' disabled':''}>×</button></span>`).join(''):'<span class="cw-empty">No files attached. Add references or describe your idea.</span>';
    const button=$('#cw-submit');if(button)button.disabled=!!pending||sending;
    root.querySelectorAll('[data-mode],select,[data-cw="attach"]').forEach(b=>b.disabled=sending||!!pending);
    $('#cw-sending').textContent=sending?'Sending to your conversation…':pending?'Uploading source files…':'';
  }
  async function upload(selected) {
    if(sending||pending)return;
    const conv=ctx.conv(),g=generation,cap=mode==='image'?3:6;
    if(!conv)return toast('Open a conversation first.',true);
    const chosen=selected.slice(0,Math.max(0,cap-files.length));
    if(chosen.length<selected.length)toast(`Up to ${cap} files for this workflow.`);
    pending=chosen.length;controller=new AbortController();drawFiles();
    for(const f of chosen){
      if(g!==generation)break;
      if(f.size>25*1024*1024){toast(`${f.name}: maximum 25 MB.`,true);pending--;continue;}
      if(mode==='image'&&!['image/png','image/jpeg','image/webp'].includes(f.type)){toast('Use PNG, JPEG or WebP reference images.',true);pending--;continue;}
      const item={name:f.name,mime:f.type,loading:true};files.push(item);drawFiles();
      try{const fd=new FormData();fd.append('file',f,f.name);const r=await api('POST',`/api/conversations/${encodeURIComponent(conv)}/files`,undefined,{form:fd,signal:controller.signal});
        if(g!==generation)return;item.file_id=r.file_id;item.loading=false;
      }catch(e){if(g!==generation)return;files=files.filter(x=>x!==item);if(e.name!=='AbortError')toast(`${f.name}: ${e.message}`,true);}
      finally{if(g===generation){pending--;drawFiles();}}
    }
    if(g===generation){controller=null;drawFiles();}
  }
  function request(mode,d,files) {
    const refs=files.map(f=>`${f.name} [file_id: ${f.file_id}]`).join('\n');
    const context=refs?`\nAttached references:\n${refs}`:'';
    if(mode==='image')return `Create ${files.length?'an edited image using my reference images':'a new image'} with photo_banao. Aspect ${d.aspect||'16:9'}, quality ${d.quality||'fast'}.\nBrief: ${d.text}${context}\nReturn the actual image result. Preserve any provided product identity and exact requested wording.`;
    if(mode==='video')return `Use video_studio to prepare a ${d.seconds||15}-second ${d.aspect||'16:9'} video storyboard with ${d.language||'English'} voiceover.\nBrief: ${d.text}${context}\nPrepare the shot plan and estimate. Do not start paid generation until I approve its cost. Return the storyboard and existing project card. Do not claim a completed video before generation and assembly.`;
    if(mode==='research')return `Research this question: ${d.text}${context}\nSource preference: ${d.sources==='files'?'Use ONLY the attached files; do not browse or use external sources. State what these files do not establish.':'Use current public sources and the attached files. Prefer primary sources.'}\nShow a work plan, then research. Cite sources, distinguish facts from inference, and state gaps. Return the report here in chat, and create a downloadable document if supported.`;
    return `Create a real ${d.format||'Word (.docx)'} document.\nBrief: ${d.text}${context}\nUse the provided source material. Do not invent company facts. Show the finished file in chat with a download and preview. If information is missing, mark it clearly.`;
  }
  async function submit(e){
    e.preventDefault();if(pending||sending)return;
    take();const d=drafts[mode];if(!d?.text.trim())return;
    if(mode==='research'&&d.sources==='files'&&!files.length)return toast('Attach a source file for file-only research.',true);
    const origin=ctx.conv(),g=generation;if(!origin)return toast('Open a conversation first.',true);
    sending=true;drawFiles();
    const text=request(mode,d,files),ids=files.map(f=>f.file_id).filter(Boolean);
    try{await ctx.submit(origin,text,ids);if(g===generation){drafts[mode]={...d,text:''};files=[];ctx.openChat(origin);}}
    catch(er){if(g===generation)toast(er.message,true);}
    finally{if(g===generation){sending=false;render();}}
  }
  root.addEventListener('click',e=>{
    const b=e.target.closest('button');if(!b||b.disabled)return;
    if(b.dataset.mode){if(pending||sending)return;take();mode=b.dataset.mode;if(mode==='image')files=files.filter(f=>f.mime?.startsWith('image/')).slice(0,3);render();return;}
    if(b.dataset.rm!==undefined){if(sending)return;files.splice(+b.dataset.rm,1);drawFiles();return;}
    if(b.dataset.cw==='attach')$('#cw-files').click();
    if(b.dataset.cw==='example'){$('#cw-prompt').value=MODES[mode].starter;take();$('#cw-prompt').focus();}
    if(b.dataset.cw==='library')ctx.library();
  });
  function reuse(item){
    if(pending||sending)return toast('Finish the current upload or submission first.',true);
    take();if(item.type==='image'){mode='image';files=files.filter(f=>f.mime?.startsWith('image/')).slice(0,3);}
    if(!files.some(x=>x.file_id===item.ref)&&files.length>=(mode==='image'?3:6))return toast('Remove a reference before adding another.',true);
    if(!files.some(x=>x.file_id===item.ref))files.push({file_id:item.ref,mime:item.type==='image'?'image/png':item.mime,name:item.name||item.title||'Reference'});
    files=files.slice(0,mode==='image'?3:6);render();ctx.show();
  }
  function reset(){generation++;controller?.abort();controller=null;files=[];drafts={};pending=0;sending=false;root.innerHTML='';}
  return {open(next){if(MODES[next]&&!sending&&!pending){take();mode=next;if(mode==='image')files=files.filter(f=>f.mime?.startsWith('image/')).slice(0,3);}render();},reuse,reset,request};
};

// Controls survive the existing studio/panel render cycles.
(() => {
  const app=document.getElementById('app');
  for(const id of ['studio','panel']){
    const box=document.getElementById(id);if(!box)continue;
    const mount=()=>{
      if(!box.children.length||box.querySelector('.workspace-handle'))return;
      const bar=document.createElement('div');bar.className='workspace-handle';
      bar.innerHTML='<label>Workspace width <input type="range" min="360" max="1000" step="20" value="640" aria-label="Workspace width"></label><button type="button" aria-pressed="false">Expand workspace</button>';
      bar.querySelector('input').addEventListener('input',e=>app.style.setProperty('--workspace-width',`min(${e.target.value}px, 80vw)`));
      bar.querySelector('button').addEventListener('click',()=>{
        const full=app.classList.toggle('workspace-full');
        app.querySelectorAll('.workspace-handle button').forEach(b=>{b.setAttribute('aria-pressed',String(full));b.textContent=full?'Restore workspace':'Expand workspace';});
      });box.prepend(bar);
    };
    new MutationObserver(mount).observe(box,{childList:true});mount();
  }
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){
    app.classList.remove('workspace-full');app.querySelectorAll('.workspace-handle button').forEach(b=>{b.setAttribute('aria-pressed','false');b.textContent='Expand workspace';});
  }});
})();

// Sidebar divider: drag, keyboard resize, double-click reset, remembered width.
(() => {
  const app=document.getElementById('app'),side=app.querySelector('.side');
  const divider=document.createElement('div');
  divider.className='sidebar-divider';divider.tabIndex=0;
  divider.setAttribute('role','separator');divider.setAttribute('aria-label','Resize sidebar');
  divider.setAttribute('aria-orientation','vertical');divider.setAttribute('aria-valuemin','220');
  divider.setAttribute('aria-valuemax','420');divider.title='Drag to resize sidebar · double-click to reset';
  side.id='console-sidebar';divider.setAttribute('aria-controls',side.id);side.after(divider);
  const narrow=()=>matchMedia('(max-width:1100px)').matches;
  let width=224,drag=null;
  try{const saved=Number(localStorage.getItem('hoola.web.sidebar.width'));if(saved>=220&&saved<=420)width=saved;}catch{}
  const set=value=>{width=Math.max(220,Math.min(420,Math.round(value)));app.style.setProperty('--sidebar-width',width+'px');divider.setAttribute('aria-valuenow',String(width));};
  const save=()=>{try{localStorage.setItem('hoola.web.sidebar.width',String(width));}catch{}};
  set(width);
  divider.addEventListener('pointerdown',e=>{
    if(narrow()||e.button!==0)return;
    e.preventDefault();app.classList.remove('collapsed');document.getElementById('collapse').setAttribute('aria-expanded','true');
    drag={x:e.clientX,width,id:e.pointerId};divider.setPointerCapture(e.pointerId);app.classList.add('sidebar-resizing');
  });
  divider.addEventListener('pointermove',e=>{if(drag&&e.pointerId===drag.id)set(drag.width+e.clientX-drag.x);});
  function finish(cancel=false){if(!drag)return;const current=drag;drag=null;if(cancel)set(current.width);else save();app.classList.remove('sidebar-resizing');if(divider.hasPointerCapture(current.id))divider.releasePointerCapture(current.id);}
  divider.addEventListener('pointerup',()=>finish());divider.addEventListener('pointercancel',()=>finish(true));
  divider.addEventListener('lostpointercapture',()=>finish(true));
  divider.addEventListener('dblclick',()=>{set(224);save();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&drag){e.preventDefault();e.stopImmediatePropagation();finish(true);}});
  divider.addEventListener('keydown',e=>{
    if(narrow()||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
    e.preventDefault();app.classList.remove('collapsed');document.getElementById('collapse').setAttribute('aria-expanded','true');
    set(e.key==='Home'?220:e.key==='End'?420:width+(e.key==='ArrowRight'?1:-1)*(e.shiftKey?20:10));save();
  });
  addEventListener('resize',()=>{if(narrow())finish(true);});
})();

// Shared presentation policy; backend events remain intact for audit and other clients.
window.HoolaProgressPolicy = {
  quiet(kind,p={}) {
    if (/(^|_)ask($|_)|approval|confirm|draft|quote|_sign/.test(kind)) return false;
    return ['step','think','work','log','say','goal','browser','operator_task','pc_task','pc_step','pc_job','memory_saved','procedure'].includes(kind);
  },
  phase(kind,p={}) {
    if (/(^|_)ask($|_)|approval|confirm/.test(kind)||p.status==='needs_approval')return 'Your approval is required';
    if(['waiting','blocked'].includes(p.status||p.phase))return 'Waiting for the next step…';
    if (['failed','error','partial','stopped'].includes(p.status||p.phase)||p.state==='error')return 'Reviewing an incomplete result…';
    if(kind==='think'||kind==='typing')return 'Thinking…';
    if(kind==='reply_start'||kind==='reply_end')return 'Preparing your response…';
    return 'Working on it…';
  }
};

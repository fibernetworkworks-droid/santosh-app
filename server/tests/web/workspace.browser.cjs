const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const http=require('http'),fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../../app/static');
const shots=process.env.CONSOLE_SHOTS;
if(shots)fs.mkdirSync(shots,{recursive:true});
let posts=[];const streams=new Set();
const emit=(kind,payload,conv="chat-1")=>{for(const r of streams)r.write("data: "+JSON.stringify({kind,payload,conv,live:true})+"\n\n");};
const server=http.createServer((req,res)=>{
 const u=new URL(req.url,'http://localhost'),p=u.pathname;
 const json=o=>{res.setHeader('Content-Type','application/json');res.end(JSON.stringify(o));};
 if(p==='/api/console/stream'||p.endsWith('/events')){res.writeHead(200,{'Content-Type':'text/event-stream'});res.write(': connected\n\n');streams.add(res);res.on('close',()=>streams.delete(res));return;}
 if(p.startsWith('/api/')||p==='/healthz'){
  let raw='';req.on('data',c=>raw+=c);req.on('end',()=>{
   if(req.method==='POST'&&p.endsWith('/messages')){posts.push({path:p,...JSON.parse(raw)});return json({ok:true});}
   if(req.method==='POST'&&p.endsWith('/files'))return json({file_id:'uploaded-reference'});
   if(p.endsWith('/config'))return json({v2:true,sessions:true,panel:true,projects:true,stream:false});
   if(p.endsWith('/me'))return json({owner:'Santosh',handle:'fnw',avatar:{name:'Hoola'}});
   if(p==='/api/console/conversations')return json({conversations:Array.from({length:60},(_,i)=>({id:'chat-'+(i+1),title:i?'Campaign research '+i:'Launch campaign',updated_at:new Date().toISOString()}))});
   if(p==='/api/projects')return json({projects:[]});
   if(p.endsWith('/timeline'))return json({events:posts.length?[{id:1,kind:'message',payload:{role:'user',text:'Create an image'}},...Array.from({length:25},(_,i)=>({id:10+i,kind:'browser',payload:{session_id:'browser-'+i,status:'done',task:'INTERNAL_WORK_MARKER',step:i}})),{id:40,kind:'operator_ask',payload:{id:'approval-1',status:'pending',reason:'Approve this action'}},{id:2,kind:'photo_made',payload:{id:'photo-1',file_id:'result-1',name:'launch.png',title:'Launch image'}},...(posts.length>1?[{id:3,kind:'message',payload:{role:'assistant',text:'This is a long reply that keeps the conversation centered.\n\n'.repeat(50)}}]:[])]:[],last_event_id:3});
   if(p==='/api/panel/files/result-1/info')return json({name:'launch.png',size:68,mime:'image/png',media:'image',inline:true});
   if(p==='/api/panel/files/result-1'){res.setHeader('Content-Type','image/png');return res.end(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==','base64'));}
   if(p.endsWith('/pending'))return json({pending:[]});
   if(p==='/api/usage')return json({});
   if(p==='/api/conversations')return json({id:'chat-1'});
   return json({});
  });return;
 }
 const file=p.startsWith('/static/')?path.join(root,p.slice(8)):path.join(root,'console/v2.html');
 if(!file.startsWith(root)||!fs.existsSync(file)){res.writeHead(404);return res.end();}
 res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':file.endsWith('.html')?'text/html':'image/png');res.end(fs.readFileSync(file));
});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_EXECUTABLE || undefined,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--disable-gpu']});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('hoola.console.token','fixture-only'));
 await page.goto(`http://127.0.0.1:${server.address().port}/console/`);await page.locator('#app').waitFor({state:'visible'});
 const divider=page.getByRole('separator',{name:'Resize sidebar'});
 const edge=await divider.boundingBox();
 await page.mouse.move(edge.x+4,200);await page.mouse.down();await page.mouse.move(edge.x+80,200,{steps:8});await page.mouse.up();
 assert.equal(await page.locator('.side').evaluate(e=>Math.round(e.getBoundingClientRect().width)),300);
 await divider.focus();await page.keyboard.press('ArrowRight');
 await page.reload();await page.locator('#app').waitFor({state:'visible'});
 assert.equal(await page.locator('.side').evaluate(e=>Math.round(e.getBoundingClientRect().width)),310);
 await divider.focus();await page.keyboard.press('End');await page.waitForTimeout(250);
 await page.waitForFunction(n=>Math.round(document.querySelector('.side').getBoundingClientRect().width)===n,420);
 assert.equal(await page.locator('.side').evaluate(e=>Math.round(e.getBoundingClientRect().width)),420);
 await divider.dblclick();await page.waitForTimeout(250);
 await page.waitForFunction(n=>Math.round(document.querySelector('.side').getBoundingClientRect().width)===n,224);
 assert.equal(await page.locator('.side').evaluate(e=>Math.round(e.getBoundingClientRect().width)),224);
 await page.locator('#collapse').click();await page.waitForTimeout(250);
 await page.waitForFunction(n=>Math.round(document.querySelector('.side').getBoundingClientRect().width)===n,72);
 assert.equal(await page.locator('.side').evaluate(e=>Math.round(e.getBoundingClientRect().width)),72);
 await page.locator('#collapse').click();await page.waitForTimeout(250);
 await page.locator('.side').hover();await page.mouse.wheel(0,600);await page.waitForTimeout(150);
 assert.ok(await page.locator('.side').evaluate(e=>e.scrollTop>0),'Sidebar must scroll with wheel');
 assert.ok(await page.locator('.side .sn .txt').first().evaluate(e=>parseFloat(getComputedStyle(e).fontSize)>=15 && Number(getComputedStyle(e).fontWeight)>=700),'Sidebar labels must be larger and bold');
 await page.locator('.side').focus();await page.keyboard.press('End');await page.waitForFunction(()=>{const e=document.querySelector('.side');return e.scrollTop+e.clientHeight>=e.scrollHeight-2});
 assert.ok(await page.locator('.side').evaluate(e=>e.scrollTop+e.clientHeight>=e.scrollHeight-2),'End reaches sidebar footer');
 await page.keyboard.press('Home');
 assert.equal(await page.locator('.main > .top').count(),0);
 assert.equal(await page.locator('.main > .views').evaluate(e=>e.getBoundingClientRect().top),0);
 assert.equal(await page.locator('.side #exportBtn').count(),1);
 await page.locator('[data-v="creative"]').click();await page.locator('#cw-prompt').fill('A crafted image of the FNW AI Node');
 await page.waitForTimeout(500);if(shots)await page.screenshot({path:path.join(shots,'hoola-studio-desktop.png'),fullPage:true});
 await page.locator('#cw-submit').click();await page.waitForFunction(()=>!document.querySelector('#v-chat').hidden);assert.match(posts.at(-1).text,/photo_banao/);assert.match(posts.at(-1).text,/Reply in English/);
 const aligned=async()=>{
  await page.waitForFunction(()=>{const col=document.querySelector('#col'),box=document.querySelector('#composer');return !document.querySelector('#v-chat').hidden && col.getBoundingClientRect().width>0 && box.parentElement.id==='slotDock';});
  const geometry=await page.evaluate(()=>{
   const col=document.querySelector('#col').getBoundingClientRect(),box=document.querySelector('#composer').getBoundingClientRect();
   return {chat:col.left+col.width/2,input:box.left+box.width/2,overflow:document.documentElement.scrollWidth>innerWidth};
  });
  assert.ok(Math.abs(geometry.chat-geometry.input)<2,'Chat and composer share a center: '+JSON.stringify(geometry));assert.equal(geometry.overflow,false);
 };
 await aligned();
 emit('typing',{on:true});await page.getByRole('status').filter({hasText:'Thinking…'}).waitFor();
 for(let i=0;i<30;i++)emit('step',{id:'s'+i,tool:'browser',label:'INTERNAL_LIVE_STEP',state:'running'});
 await page.locator('.simple-progress').filter({hasText:'Working on it…'}).waitFor();
 assert.equal(await page.locator('#col .simple-progress').count(),1);assert.equal(await page.locator('#dock .simple-progress').count(),0);assert.equal(await page.locator('#col .progress-active > .av img').count(),1);assert.equal(await page.locator('.progress-dots i').count(),3);await page.emulateMedia({reducedMotion:'reduce'});assert.equal(await page.locator('.progress-dots i').first().evaluate(e=>getComputedStyle(e).animationName),'none');await page.emulateMedia({reducedMotion:'no-preference'});assert.equal(await page.getByText('INTERNAL_LIVE_STEP',{exact:true}).count(),0);
 emit('message',{role:'assistant',ack:true,source:'agent',text:'Ek second, dekh raha hoon…'});
 await page.waitForTimeout(80);
 assert.equal(await page.getByText('Ek second, dekh raha hoon…',{exact:true}).count(),0);
 assert.equal(await page.locator('#col .simple-progress').count(),1);
 assert.equal(await page.locator('.simple-progress summary svg').count(),1);
 assert.equal(await page.locator('.progress-label').evaluate(e=>getComputedStyle(e).fontWeight),'500');
 emit('think',{turn:'final-fixture',seg:0,text:'PRIVATE_REASONING'});await page.locator('.simple-progress').filter({hasText:'Thinking…'}).waitFor();
 assert.equal(await page.getByText('PRIVATE_REASONING',{exact:true}).count(),0);
 emit('reply_start',{turn:'final-fixture'});await page.locator('.simple-progress').filter({hasText:'Preparing your response…'}).waitFor();
 assert.equal(await page.locator('#col .progress-active > .av').count(),1);
 assert.equal(await page.locator('.simple-progress img').count(),0);
 await page.locator('.simple-progress summary').click();
 assert.equal(await page.locator('.progress-activity').isVisible(),true);
 assert.ok(await page.locator('.progress-activity li').count()<=12);
 assert.equal(await page.locator('.progress-activity').getByText('Checking sources',{exact:true}).count(),1);
 emit('delta',{turn:'final-fixture',seg:0,seq:1,text:'Final verified answer.'});
 emit('reply_end',{turn:'final-fixture'});emit('typing',{on:false});
 await page.locator('.simple-progress').waitFor({state:'hidden'});await page.getByText('Final verified answer.',{exact:true}).waitFor();
 emit('browser',{session_id:'unrelated',status:'working'},'another-chat');await page.waitForTimeout(100);assert.equal(await page.locator('.simple-progress').isVisible(),false);
 assert.equal(await page.locator('#col').getByText('INTERNAL_WORK_MARKER').count(),0);assert.equal(await page.locator('#col').getByText('Approve this action',{exact:true}).count(),1);
 await divider.focus();await page.keyboard.press('End');await page.waitForFunction(()=>Math.round(document.querySelector('.side').getBoundingClientRect().width)===420);await aligned();
 await divider.dblclick();await page.waitForFunction(()=>Math.round(document.querySelector('.side').getBoundingClientRect().width)===224);await aligned();

 for(const mode of ['video','research','document']){
  await page.locator('[data-v="creative"]').click();await page.locator(`[data-mode="${mode}"]`).click();await page.locator('#cw-prompt').fill('Build a clear launch brief from verified information');
  if(mode==='research'){
   await page.locator('#cw-sources').selectOption('files');await page.locator('#cw-submit').click();assert.equal(posts.length,2);
   await page.locator('#cw-files').setInputFiles({name:'source.txt',mimeType:'text/plain',buffer:Buffer.from('Verified product source')});await page.locator('#cw-submit').waitFor({state:'visible'});await page.waitForFunction(()=>!document.querySelector('#cw-submit').disabled);
  }
  await page.locator('#cw-submit').click();await page.waitForFunction(()=>!document.querySelector('#v-chat').hidden);await aligned();
 }
 await page.locator('.result-card').scrollIntoViewIfNeeded();await page.locator('[data-expand]').click();
 await page.locator('#panel .workspace-handle button').click();assert.ok(await page.locator('#app').evaluate(e=>e.classList.contains('workspace-full')));
 await page.keyboard.press('Escape');assert.equal(await page.locator('#app').evaluate(e=>e.classList.contains('workspace-full')),false);
 await page.locator('#pnClose').click();await page.locator('[data-reuse]').click();assert.equal(await page.locator('#cw-refs .fchip').count(),1);
 assert.equal(posts.length,4);assert.match(posts[1].text,/Do not start paid generation until I approve/);assert.deepEqual(posts[2].files,['uploaded-reference']);assert.match(posts[3].text,/real Word/);
 await page.locator('[data-v="creative"]').click();await page.locator('[data-mode="image"]').click();await page.locator('[data-rm]').click();assert.equal(await page.locator('#cw-refs .fchip').count(),0);
 await page.locator('[data-mode="document"]').click();
 await page.locator('#cw-files').setInputFiles({name:'reference.txt',mimeType:'text/plain',buffer:Buffer.from('Reference')});
 await page.waitForFunction(()=>!document.querySelector('#cw-submit').disabled);
 await page.locator('[data-mode="image"]').click();assert.equal(await page.locator('#cw-refs .fchip').count(),0);
 await page.locator('.side [data-v="chat"]').click();await aligned();
 for(const width of [1024,768,390,320]){
  await page.setViewportSize({width,height:900});await page.waitForTimeout(100);
  const sizes=await page.evaluate(()=>({w:innerWidth,scroll:document.documentElement.scrollWidth}));assert.ok(sizes.scroll<=sizes.w,JSON.stringify(sizes));await aligned();
  assert.equal(await divider.isVisible(),false,'Resize handle stays off mobile drawer');
  if(width===390){
   await page.locator('#menu').click();await page.locator('.side').hover();await page.mouse.wheel(0,600);await page.waitForTimeout(150);
   assert.ok(await page.locator('.side').evaluate(e=>e.scrollTop>0),'Mobile drawer must scroll');
   await page.locator('.side').focus();await page.keyboard.press('End');await page.waitForFunction(()=>{const e=document.querySelector('.side');return e.scrollTop+e.clientHeight>=e.scrollHeight-2});
   assert.ok(await page.locator('.side').evaluate(e=>e.scrollTop+e.clientHeight>=e.scrollHeight-2));
   await page.locator('#scrim').click({position:{x:360,y:100}});
  }
  if(width===390 && shots){await page.waitForTimeout(500);await page.screenshot({path:path.join(shots,'hoola-studio-mobile.png'),fullPage:true});}
 }
 assert.deepEqual(errors,[]);console.log('PASS: four workflow submissions, file-only validation/upload, approval wording, image attachment filtering, result reuse, workspace expansion/Escape, 4 responsive widths, no browser exceptions');
 await browser.close();server.closeAllConnections();server.close();
})().catch(e=>{console.error(e);server.closeAllConnections();server.close();process.exit(1)});

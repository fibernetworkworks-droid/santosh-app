const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const http=require('http'),fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../../app/static');
const shots=process.env.CONSOLE_SHOTS;
if(shots)fs.mkdirSync(shots,{recursive:true});
let posts=[];
const server=http.createServer((req,res)=>{
 const u=new URL(req.url,'http://localhost'),p=u.pathname;
 const json=o=>{res.setHeader('Content-Type','application/json');res.end(JSON.stringify(o));};
 if(p==='/api/console/stream'||p.endsWith('/events')){res.writeHead(200,{'Content-Type':'text/event-stream'});res.write(': connected\n\n');return;}
 if(p.startsWith('/api/')||p==='/healthz'){
  let raw='';req.on('data',c=>raw+=c);req.on('end',()=>{
   if(req.method==='POST'&&p.endsWith('/messages')){posts.push({path:p,...JSON.parse(raw)});return json({ok:true});}
   if(req.method==='POST'&&p.endsWith('/files'))return json({file_id:'uploaded-reference'});
   if(p.endsWith('/config'))return json({v2:true,sessions:true,panel:true,projects:true,stream:false});
   if(p.endsWith('/me'))return json({owner:'Santosh',handle:'fnw',avatar:{name:'Hoola'}});
   if(p==='/api/console/conversations')return json({conversations:[{id:'chat-1',title:'Launch campaign',updated_at:new Date().toISOString()}]});
   if(p==='/api/projects')return json({projects:[]});
   if(p.endsWith('/timeline'))return json({events:posts.length?[{id:1,kind:'message',payload:{role:'user',text:'Create an image'}},{id:2,kind:'photo_made',payload:{id:'photo-1',file_id:'result-1',name:'launch.png',title:'Launch image'}}]:[],last_event_id:2});
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
 assert.equal(await page.locator('.main > .top').count(),0);
 assert.equal(await page.locator('.main > .views').evaluate(e=>e.getBoundingClientRect().top),0);
 assert.equal(await page.locator('.side #exportBtn').count(),1);
 await page.locator('[data-v="creative"]').click();await page.locator('#cw-prompt').fill('A crafted image of the FNW AI Node');
 await page.waitForTimeout(500);if(shots)await page.screenshot({path:path.join(shots,'hoola-studio-desktop.png'),fullPage:true});
 await page.locator('#cw-submit').click();await page.waitForFunction(()=>!document.querySelector('#v-chat').hidden);assert.match(posts.at(-1).text,/photo_banao/);
 for(const mode of ['video','research','document']){
  await page.locator('[data-v="creative"]').click();await page.locator(`[data-mode="${mode}"]`).click();await page.locator('#cw-prompt').fill('Build a clear launch brief from verified information');
  if(mode==='research'){
   await page.locator('#cw-sources').selectOption('files');await page.locator('#cw-submit').click();assert.equal(posts.length,2);
   await page.locator('#cw-files').setInputFiles({name:'source.txt',mimeType:'text/plain',buffer:Buffer.from('Verified product source')});await page.locator('#cw-submit').waitFor({state:'visible'});await page.waitForFunction(()=>!document.querySelector('#cw-submit').disabled);
  }
  await page.locator('#cw-submit').click();await page.waitForFunction(()=>!document.querySelector('#v-chat').hidden);
 }
 await page.locator('[data-expand]').click();
 await page.locator('#panel .workspace-handle button').click();assert.ok(await page.locator('#app').evaluate(e=>e.classList.contains('workspace-full')));
 await page.keyboard.press('Escape');assert.equal(await page.locator('#app').evaluate(e=>e.classList.contains('workspace-full')),false);
 await page.locator('#pnClose').click();await page.locator('[data-reuse]').click();assert.equal(await page.locator('#cw-refs .fchip').count(),1);
 assert.equal(posts.length,4);assert.match(posts[1].text,/Do not start paid generation until I approve/);assert.deepEqual(posts[2].files,['uploaded-reference']);assert.match(posts[3].text,/real Word/);
 await page.locator('[data-v="creative"]').click();await page.locator('[data-mode="image"]').click();await page.locator('[data-rm]').click();assert.equal(await page.locator('#cw-refs .fchip').count(),0);
 await page.locator('[data-mode="document"]').click();
 await page.locator('#cw-files').setInputFiles({name:'reference.txt',mimeType:'text/plain',buffer:Buffer.from('Reference')});
 await page.waitForFunction(()=>!document.querySelector('#cw-submit').disabled);
 await page.locator('[data-mode="image"]').click();assert.equal(await page.locator('#cw-refs .fchip').count(),0);
 for(const width of [1024,768,390,320]){
  await page.setViewportSize({width,height:900});await page.waitForTimeout(100);
  const sizes=await page.evaluate(()=>({w:innerWidth,scroll:document.documentElement.scrollWidth}));assert.ok(sizes.scroll<=sizes.w,JSON.stringify(sizes));
  if(width===390 && shots){await page.waitForTimeout(500);await page.screenshot({path:path.join(shots,'hoola-studio-mobile.png'),fullPage:true});}
 }
 assert.deepEqual(errors,[]);console.log('PASS: four workflow submissions, file-only validation/upload, approval wording, image attachment filtering, result reuse, workspace expansion/Escape, 4 responsive widths, no browser exceptions');
 await browser.close();server.closeAllConnections();server.close();
})().catch(e=>{console.error(e);server.closeAllConnections();server.close();process.exit(1)});

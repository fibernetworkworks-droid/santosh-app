const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const http=require('http'),fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../../app/static');
const shots=process.env.CONSOLE_SHOTS;
if(shots)fs.mkdirSync(shots,{recursive:true});
let artifactVersion=1;const revisions=[],shares=[];let posts=[],renames=[];const titles=new Map();const streams=new Set();
const emit=(kind,payload,conv="chat-1")=>{for(const r of streams)r.write("data: "+JSON.stringify({kind,payload,conv,live:true})+"\n\n");};
const server=http.createServer((req,res)=>{
 const u=new URL(req.url,'http://localhost'),p=u.pathname;
 const json=o=>{res.setHeader('Content-Type','application/json');res.end(JSON.stringify(o));};
 if(p==='/api/console/stream'||p.endsWith('/events')){res.writeHead(200,{'Content-Type':'text/event-stream'});res.write(': connected\n\n');streams.add(res);res.on('close',()=>streams.delete(res));return;}
 if(p.startsWith('/api/')||p==='/healthz'){
  let raw='';req.on('data',c=>raw+=c);req.on('end',()=>{
   if(req.method==='PATCH'&&p.startsWith('/api/conversations/')){const body=JSON.parse(raw);renames.push(body);if(body.title)titles.set(p.split('/').at(-1),body.title);return json({ok:true});}
   if(req.method==='POST'&&p.endsWith('/messages')){posts.push({path:p,...JSON.parse(raw)});return json({ok:true});}
   if(req.method==='POST'&&p.endsWith('/files'))return json({file_id:'uploaded-reference'});
   if(req.method==='POST'&&p.endsWith('/revise')){revisions.push(JSON.parse(raw));return json({status:'building'});}
   if(req.method==='POST'&&p==='/api/panel/share'){shares.push(JSON.parse(raw));return json({ok:true});}
   if(p.startsWith('/api/artifacts/'))return json({id:p.split('/').at(-1),title:'ISP Dashboard',version:artifactVersion,versions:Array.from({length:artifactVersion},(_,i)=>({version:i+1,note:'Version '+(i+1)}))});
   if(p.startsWith('/api/panel/pages/')&&p.endsWith('/view'))return json({url:'/a/art-1/'+(u.searchParams.get('version')||artifactVersion)+'?exp=1&sig=fixture'});
   if(p.startsWith('/api/panel/pages/')&&p.endsWith('/source'))return json({html:'<!doctype html><html><body><h1>Dashboard '+u.searchParams.get('version')+'</h1></body></html>',title:'ISP Dashboard',version:+u.searchParams.get('version')});
   if(p==='/api/panel/library'){const q=u.searchParams.get('q')||'',item={type:'page',ref:'art-1',title:q==='old'?'Old result':q==='new'?'Newest result':'ISP Dashboard',version:artifactVersion,at:new Date().toISOString()};return setTimeout(()=>json({items:[item]}),q==='old'?550:5);}
   if(p.endsWith('/config'))return json({v2:true,sessions:true,panel:true,projects:true,stream:false});
   if(p.endsWith('/me'))return json({owner:'Santosh',handle:'fnw',avatar:{name:'Hoola'}});
   if(p==='/api/console/conversations'){const offset=+(u.searchParams.get('offset')||0),history=u.searchParams.has('offset'),n=history?Math.max(0,Math.min(200,205-offset)):60;return json({conversations:Array.from({length:n},(_,j)=>{const i=offset+j,id='chat-'+(i+1);return {id,title:titles.get(id)||(i?'Campaign research '+i:'Launch campaign'),busy:i===2,updated_at:new Date().toISOString()};})});}
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
 if(p.startsWith('/a/')){res.setHeader('Content-Type','text/html');return res.end('<!doctype html><html><body><h1>Interactive dashboard preview</h1></body></html>');}
 const file=p.startsWith('/static/')?path.join(root,p.slice(8)):path.join(root,'console/v2.html');
 if(!file.startsWith(root)||!fs.existsSync(file)){res.writeHead(404);return res.end();}
 if(file.endsWith('.html'))res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'");
 res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':file.endsWith('.html')?'text/html':'image/png');res.end(fs.readFileSync(file));
});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_EXECUTABLE||undefined,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{if(window.top===window)localStorage.setItem('hoola.console.token','fixture-only');});
 await page.goto(`http://127.0.0.1:${server.address().port}/console/`);await page.locator('#app').waitFor({state:'visible'});
 await page.locator('.side [data-v="bana"]').click();await page.getByRole('heading',{name:'Artifacts',exact:true}).waitFor();
 assert.equal(await page.locator('[data-template]').count(),4);await page.locator('[data-template="calculator"]').click();await page.waitForFunction(()=>!document.querySelector('#v-chat').hidden);assert.match(posts.at(-1).text,/artifact_make/);assert.match(posts.at(-1).text,/formula and units/);
 emit('artifact',{id:'art-1',title:'ISP Dashboard',version:1,status:'ready'});
 await page.locator('#panel .pnframe').waitFor();assert.equal(await page.locator('#app').evaluate(e=>e.classList.contains('pn')),true);
 assert.equal(await page.locator('#panel .pnframe').getAttribute('sandbox'),'allow-scripts allow-forms allow-popups');assert.equal(await page.locator('#panel .pnframe').getAttribute('referrerpolicy'),'no-referrer');
 await page.locator('#panel [data-v="code"]').click();await page.locator('#panel .pcode').waitFor();assert.match(await page.locator('#panel .pcode').textContent(),/Dashboard 1/);
 await page.getByRole('textbox',{name:'Refine artifact'}).fill('Add a monthly filter');await page.locator('#panel .pnchg button').click();assert.equal(revisions.length,1);assert.match(revisions[0].request,/monthly filter/);
 artifactVersion=2;emit('artifact',{id:'art-1',title:'ISP Dashboard',version:2,status:'ready'});await page.waitForFunction(()=>document.querySelector('#panel .pnsel')?.value==='2');
 await page.locator('#panel .pnsel').selectOption('1');await page.locator('#panel [data-v="code"]').click();await page.waitForFunction(()=>document.querySelector('#panel .pcode')?.textContent.includes('Dashboard 1'));
 const downloadPromise=page.waitForEvent('download');await page.locator('#panel [data-a="dl"]').click();const download=await downloadPromise;assert.match(download.suggestedFilename(),/v1\.html$/);
 await page.locator('#panel [data-a="share"]').click();assert.equal(shares.length,1);assert.equal(shares[0].kind,'page');assert.equal(shares[0].id,'art-1');assert.equal(shares[0].conversation_id,'chat-1');
 await page.locator('#pnClose').click();emit('artifact',{id:'art-1',title:'ISP Dashboard',version:2,status:'ready'});await page.waitForTimeout(80);assert.equal(await page.locator('#app').evaluate(e=>e.classList.contains('pn')),false);
 await page.locator('.side [data-v="bana"]').click();await page.locator('#libgrid [data-i]').waitFor();await page.getByRole('textbox',{name:'Search artifacts'}).fill('old');await page.waitForTimeout(280);await page.getByRole('textbox',{name:'Search artifacts'}).fill('new');await page.waitForTimeout(700);assert.equal(await page.locator('#libgrid b').textContent(),'Newest result');
 await page.locator('#libgrid [data-i]').click();await page.locator('#panel .pnframe').waitFor();
 for(const width of [1440,768,390,320]){await page.setViewportSize({width,height:900});await page.waitForTimeout(120);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
 if(shots){await page.setViewportSize({width:1440,height:1000});await page.locator('#pnClose').click();await page.waitForTimeout(300);await page.screenshot({path:path.join(shots,'hoola-artifact-library.png')});}
 assert.deepEqual(errors,[]);console.log('PASS: templates, library/search race, live side opening, sandbox, conversational revision, version selection/export, approval-based share request, manual close, responsive layout (simulated services)');
 await browser.close();server.closeAllConnections();server.close();
})().catch(e=>{console.error(e);server.closeAllConnections();server.close();process.exit(1)});

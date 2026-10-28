const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const http=require('http'),fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../../app/static');
const shots=process.env.CONSOLE_SHOTS;
if(shots)fs.mkdirSync(shots,{recursive:true});
let uploadCount=0,uploadDelay=0;let posts=[],renames=[];const titles=new Map();const streams=new Set();
const emit=(kind,payload,conv="chat-1")=>{for(const r of streams)r.write("data: "+JSON.stringify({kind,payload,conv,live:true})+"\n\n");};
const server=http.createServer((req,res)=>{
 const u=new URL(req.url,'http://localhost'),p=u.pathname;
 const json=o=>{res.setHeader('Content-Type','application/json');res.end(JSON.stringify(o));};
 if(p==='/api/console/stream'||p.endsWith('/events')){res.writeHead(200,{'Content-Type':'text/event-stream'});res.write(': connected\n\n');streams.add(res);res.on('close',()=>streams.delete(res));return;}
 if(p.startsWith('/api/')||p==='/healthz'){
  let raw='';req.on('data',c=>raw+=c);req.on('end',()=>{
   if(req.method==='PATCH'&&p.startsWith('/api/conversations/')){const body=JSON.parse(raw);renames.push(body);if(body.title)titles.set(p.split('/').at(-1),body.title);return json({ok:true});}
   if(req.method==='POST'&&p.endsWith('/messages')){posts.push({path:p,...JSON.parse(raw)});return json({ok:true});}
   if(req.method==='POST'&&p.endsWith('/files')){const id='uploaded-'+(++uploadCount);return setTimeout(()=>json({file_id:id}),uploadDelay);}
   if(p.endsWith('/config'))return json({v2:true,sessions:true,panel:true,projects:true,stream:false});
   if(p.endsWith('/me'))return json({owner:'Santosh',handle:'fnw',avatar:{name:'Hoola'}});
   if(p==='/api/console/conversations'){const offset=+(u.searchParams.get('offset')||0),history=u.searchParams.has('offset'),n=history?Math.max(0,Math.min(200,205-offset)):60;return json({conversations:Array.from({length:n},(_,j)=>{const i=offset+j,id='chat-'+(i+1);return {id,title:titles.get(id)||(i?'Campaign research '+i:'Launch campaign'),busy:i===2,updated_at:new Date().toISOString()};})});}
   if(p==='/api/projects')return json({projects:[]});
   if(p.endsWith('/timeline'))return json({events:[{id:100,kind:'message',payload:{role:'user',source:'voice',text:'Please prepare a report.'}},{id:101,kind:'message',payload:{role:'assistant',source:'voice',text:'Your report is ready.'}}],last_event_id:101});
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
 if(file.endsWith('.html'))res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'");
 res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':file.endsWith('.html')?'text/html':'image/png');res.end(fs.readFileSync(file));
});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_EXECUTABLE||undefined,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{
   localStorage.setItem('hoola.console.token','fixture-only');
   window.__tracksStopped=0;window.__audioPlayed=0;
   Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>{if(window.__holdMic)await new Promise(r=>window.__resolveMic=r);return {getTracks:()=>[{stop(){window.__tracksStopped++;}}]};}}});
   class Audio {constructor(){this.sampleRate=48000;this.currentTime=0;this.destination={};}async resume(){}async close(){}createMediaStreamSource(){return {connect(){},disconnect(){}};}createScriptProcessor(){return window.__audioProc={connect(){},disconnect(){}};}createGain(){return {gain:{value:0},connect(){}};}createBuffer(){return {duration:.01,copyToChannel(){}};}createBufferSource(){return {connect(){},start(){window.__audioPlayed++;},stop(){}};}}
   window.AudioContext=Audio;
   const NativeWS=window.WebSocket;
   window.WebSocket=class {constructor(url,protocols){if(!url.includes('/api/voice/ws'))return new NativeWS(url,protocols);this.url=url;this.sent=[];this.readyState=1;window.__voice=this;}send(data){this.sent.push(data);}emit(type,other={}){this.onmessage?.({data:JSON.stringify({type,...other})});}close(){this.readyState=3;setTimeout(()=>this.onclose?.({code:1000}),0);}};
 });
 await page.goto(`http://127.0.0.1:${server.address().port}/console/`);await page.locator('#app').waitFor({state:'visible'});
 // Picker upload shares the existing authenticated endpoint and blocks premature send.
 uploadDelay=160;
 await page.locator('#fileIn').setInputFiles({name:'brief.txt',mimeType:'text/plain',buffer:Buffer.from('Product brief')});
 assert.equal(await page.locator('#files .fchip').count(),1);assert.equal(await page.locator('#sendBtn').isDisabled(),true);
 await page.waitForFunction(()=>document.querySelector('#files').getAttribute('aria-busy')==='false');
 await page.locator('#sendBtn').click();await page.waitForFunction(()=>document.querySelector('#files').children.length===0);
 assert.deepEqual(posts.at(-1).files,['uploaded-1']);assert.match(posts.at(-1).text,/Please review/);
 uploadDelay=500;
 await page.locator('#fileIn').setInputFiles({name:'cancel.txt',mimeType:'text/plain',buffer:Buffer.from('Cancel this upload')});
 await page.locator('#files [data-rm]').click();await page.waitForTimeout(550);assert.equal(await page.locator('#files .fchip').count(),0);
 // Concurrent drop and clipboard operations reserve slots before awaiting the network.
 uploadDelay=120;
 await page.locator('#v-chat').evaluate(e=>{const dt=new DataTransfer();for(let i=0;i<6;i++)dt.items.add(new File(['x'],'drop-'+i+'.txt',{type:'text/plain'}));e.dispatchEvent(new DragEvent('dragenter',{bubbles:true,dataTransfer:dt}));e.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt}));});
 await page.locator('#msg').evaluate(e=>{const dt=new DataTransfer();dt.items.add(new File(['x'],'extra.txt',{type:'text/plain'}));e.dispatchEvent(new ClipboardEvent('paste',{bubbles:true,cancelable:true,clipboardData:dt}));});
 assert.equal(await page.locator('#files .fchip').count(),6);assert.equal(await page.locator('.dropping').count(),0);
 await page.waitForFunction(()=>document.querySelector('#files').getAttribute('aria-busy')==='false');
 for(let i=0;i<6;i++)await page.locator('#files [data-rm]').first().click();
 // Real PNG clipboard data produces a preview, while text+image paste keeps native text insertion.
 const png='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
 const paste=async(mixed=false)=>page.locator('#msg').evaluate((e,{png,mixed})=>{const bytes=Uint8Array.from(atob(png),c=>c.charCodeAt(0)),dt=new DataTransfer();dt.items.add(new File([bytes],'image.png',{type:'image/png'}));if(mixed)dt.setData('text/plain','Keep this text');const event=new ClipboardEvent('paste',{bubbles:true,cancelable:true,clipboardData:dt});e.dispatchEvent(event);return event.defaultPrevented;},{png,mixed});
 assert.equal(await paste(),true);await page.waitForFunction(()=>document.querySelector('#files').getAttribute('aria-busy')==='false');assert.equal(await page.locator('#files img').count(),1);await page.locator('#files [data-rm]').click();
 assert.equal(await paste(true),false);await page.waitForFunction(()=>document.querySelector('#files').getAttribute('aria-busy')==='false');await page.locator('#files [data-rm]').click();
 // Two-way transport, cumulative captions, turn boundaries, mute and persisted-chat access.
 await page.locator('#voiceBtn').click();await page.waitForFunction(()=>!!window.__voice);
 await page.evaluate(()=>{window.__voice.emit('ready');window.__audioProc.onaudioprocess({inputBuffer:{getChannelData:()=>new Float32Array(4096)}});window.__voice.emit('user_text',{text:'Please prepare'});window.__voice.emit('user_text',{text:'Please prepare a report.'});window.__voice.emit('santosh_text',{text:'Your report'});window.__voice.emit('santosh_text',{text:'Your report is ready.'});window.__voice.onmessage({data:new Int16Array([1,2,3]).buffer});});
 assert.equal(await page.locator('.voice-line').count(),2);assert.equal(await page.getByRole('log',{name:'Live voice transcript'}).getByText('Please prepare a report.',{exact:true}).count(),1);
 assert.equal(await page.evaluate(()=>window.__voice.sent.some(s=>s instanceof ArrayBuffer)),true);assert.equal(await page.evaluate(()=>window.__audioPlayed),1);
 await page.getByRole('button',{name:'Mute microphone',exact:true}).click();assert.equal(await page.getByRole('button',{name:'Unmute microphone'}).getAttribute('aria-pressed'),'true');
 await page.evaluate(()=>{window.__voice.emit('turn_done');window.__voice.emit('user_text',{text:'Thank you.'});});assert.equal(await page.locator('.voice-line').count(),3);
 if(shots){await page.waitForTimeout(250);await page.screenshot({path:path.join(shots,'hoola-voice-transcript.png')});}
 await page.getByRole('button',{name:'Hang up'}).click();assert.ok(await page.evaluate(()=>window.__tracksStopped>0));
 await page.getByRole('button',{name:'View saved conversation'}).click();await page.locator('#col').getByText('Your report is ready.',{exact:true}).waitFor();
 await page.evaluate(()=>{window.__voice=null;window.__holdMic=true;});
 await page.locator('#voiceBtn').click();await page.getByRole('button',{name:'Hang up'}).click();
 await page.evaluate(()=>window.__resolveMic());await page.waitForTimeout(100);assert.equal(await page.evaluate(()=>window.__voice),null);
 assert.deepEqual(errors,[]);console.log('PASS: picker/drop/paste, 6-file concurrent limit, upload send guard, image preview, mixed paste, two-way audio transport, cumulative captions, saved transcript navigation, mute and cleanup (simulated services)');
 await browser.close();server.closeAllConnections();server.close();
})().catch(e=>{console.error(e);server.closeAllConnections();server.close();process.exit(1)});

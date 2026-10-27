// Dependency-free behavioral contract checks. This small DOM double is not a layout/browser test.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
class El {
  constructor(tag='div') { this.tagName=tag; this.children=[]; this.attrs={}; this.isConnected=true; this.events={}; this._html=''; }
  set innerHTML(v) {
    this._html=v; this.children=[];
    if (v.includes('result-preview')) { const p=new El(); p.role='preview'; this.children.push(p); }
    for (const k of ['expand','download']) if (v.includes(`data-${k}`)) { const b=new El('button'); b.role=k; this.children.push(b); }
  }
  get innerHTML() { return this._html; }
  querySelector(s) {
    if (s === '.result-preview') return this.children.find(x=>x.role==='preview');
    const m=s.match(/^\[data-(.*?)\]$/); if (m) return this.children.find(x=>x.role===m[1]);
    if (s==='img,video,audio') return this.children.find(x=>['img','video','audio'].includes(x.tagName));
    return null;
  }
  querySelectorAll() { return this.children.flatMap(c=>['video','audio'].includes(c.tagName)?[c]:c.querySelectorAll()); }
  appendChild(e) { this.children.push(e); return e; }
  replaceChildren(...es) { this.children=es; this._html=''; }
  setAttribute(k,v) { this.attrs[k]=v; }
  removeAttribute(k) { delete this.attrs[k]; }
  addEventListener(k,fn) { this.events[k]=fn; }
  pause() { this.paused=true; }
  load() {}
  click() { this.clicked=true; }
}
function setup(api, item) {
  const made=[],revoked=[],opens=[],errors=[];
  class U extends URL {}
  U.createObjectURL=()=>{const u='blob:local-'+made.length;made.push(u);return u;};
  U.revokeObjectURL=u=>revoked.push(u);
  const window={};
  const box={window,location:{origin:'https://hoola.test'},URL:U,AbortController,
    document:{createElement:t=>new El(t)}};
  vm.runInNewContext(fs.readFileSync(path.resolve(__dirname,'../../app/static/console/results.js'),'utf8'),box);
  const R=window.HoolaResults({api,esc:s=>String(s??'').replaceAll('<','&lt;'),
    itemOf:()=>item,open:x=>opens.push(x),toast:m=>errors.push(m)});
  return {R,made,revoked,opens,errors};
}
const info={name:'poster.png',inline:true,media:'image',size:4096};
const image={type:'image',ref:'f_one',title:'Poster'};
const response={blob:async()=>({})};
test('image uses protected bytes, produces a real preview and workspace action',async()=>{
  const calls=[];const x=setup(async(...a)=>{calls.push(a);return a[1].endsWith('/info')?info:response;},image);
  const el=new El();assert.equal(await x.R.card('photo_made',{name:'Poster'},el),true);
  assert.deepEqual(calls.map(c=>c[1]),['/api/panel/files/f_one/info','/api/panel/files/f_one']);
  assert.equal(calls[1][3].raw,true);assert.ok(calls[1][3].signal);
  assert.equal(el.querySelector('.result-preview').children[0].src,'blob:local-0');
  el.children.at(-1).querySelector('[data-expand]').onclick();assert.equal(x.opens[0],image);
  x.R.reset();assert.deepEqual(x.revoked,['blob:local-0']);
});
test('failed file access reports a useful state and retains workspace recovery',async()=>{
  const x=setup(async()=>{throw new Error('File expired');},image);const el=new El();
  await x.R.card('photo_made',{},el);
  assert.match(el.querySelector('.result-preview').innerHTML,/File expired/);
  assert.equal(el.querySelector('.result-preview').attrs['aria-busy'],'false');
  assert.equal(el.children.at(-1).querySelector('[data-download]'),undefined);
});
test('reset aborts outstanding preview and prevents late mutation or blob leak',async()=>{
  let finish,signal;const x=setup((m,p,b,o)=>{signal=o.signal;return new Promise(r=>finish=r);},image);
  const el=new El();const task=x.R.card('pc_file',{},el);x.R.reset();
  assert.equal(signal.aborted,true);finish(info);await task;assert.equal(x.made.length,0);
  assert.equal(el.children.length,1);
});
test('a new result state wins over an earlier metadata request',async()=>{
  let finish,n=0;const x=setup(async(m,p)=>{
    if(p.endsWith('/info') && ++n===1)return new Promise(r=>finish=r);
    return p.endsWith('/info')?info:response;
  },image);const el=new El();const old=x.R.card('photo_made',{},el);
  await x.R.card('photo_made',{},el);const html=el.innerHTML;
  finish({...info,name:'old.png'});await old;
  assert.equal(el.innerHTML,html);assert.equal(x.made.length,1);
});
test('artifacts use the real editing workspace instead of an unbridged iframe',async()=>{
  const x=setup(async()=>{throw Error('should not fetch')},{type:'page',ref:'a_one'});
  const el=new El();await x.R.card('artifact',{status:'ready',version:2,summary:'Calculator'},el);
  assert.match(el.querySelector('.result-preview').innerHTML,/v2/);
  assert.doesNotMatch(el.innerHTML,/<iframe/);
});
test('pending artifacts stay with ordinary status rendering',async()=>{
  const x=setup(async()=>{throw Error('unexpected')},{type:'page',ref:'a_one'});
  assert.equal(await x.R.card('artifact',{status:'building'},new El()),false);
});
test('external video URL is rejected without requesting it',async()=>{
  let n=0;const x=setup(async()=>{n++;},{type:'video',url:'https://attacker.test/api/video/files/x'});
  const el=new El();await x.R.card('video_job',{},el);assert.equal(n,0);
  assert.match(el.querySelector('.result-preview').innerHTML,/link nahi mila/);
});
test('real signed local video plays with controls and no autoplay',async()=>{
  const x=setup(async()=>response,{type:'video',title:'Reel',url:'/api/motion/files/abc?sig=test'});
  const el=new El();await x.R.card('motion',{},el);const v=el.querySelector('.result-preview').children[0];
  assert.equal(v.tagName,'video');assert.equal(v.controls,true);assert.equal(v.autoplay,undefined);
  assert.equal(v.src,'/api/motion/files/abc?sig=test');
});
test('Office and PDF do not trigger conversion during history replay',async()=>{
  const calls=[];const x=setup(async(m,p)=>{calls.push(p);return {...info,media:'pdf'};},{type:'pdf',ref:'pdf_one'});
  await x.R.card('pc_file',{},new El());assert.deepEqual(calls,['/api/panel/files/pdf_one/info']);
});
test('dictation can append multiple final recognition results without const reassignment',()=>{
  const text=fs.readFileSync(path.resolve(__dirname,'../../app/static/console/v2.js'),'utf8');
  const start=text.indexOf('const SR = window.SpeechRecognition');
  const end=text.indexOf('/* ================= landing ideas',start);
  let click,rec;
  class Recognition { constructor(){rec=this;} start(){} }
  const mic={classList:{add(){},remove(){}},addEventListener:(k,f)=>click=f};
  const msg={value:'Initial',dispatchEvent(){}};
  const sandbox={window:{SpeechRecognition:Recognition},$:()=>mic,msg,Event:class{},
    go(){},toast(){},scrollDown(){}};
  vm.runInNewContext(text.slice(start,end),sandbox);click();
  for(const word of ['first','second']){
    const result=[{transcript:word}];result.isFinal=true;
    rec.onresult({resultIndex:0,results:[result]});
  }
  assert.equal(msg.value,'Initial first second');
});

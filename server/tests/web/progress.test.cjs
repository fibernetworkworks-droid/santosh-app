const test=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm'),path=require('path');
const s=fs.readFileSync(path.resolve(__dirname,'../../app/static/console/workspace.js'),'utf8');const context={window:{}};
vm.runInNewContext(s.slice(s.indexOf('window.HoolaProgressPolicy =')).split('// Hoola appearance and composer additions.')[0],context);const p=context.window.HoolaProgressPolicy;
test('routine operations collapse while action and output cards remain available',()=>{
 for(const kind of ['browser','operator_task','step','think','work','say','goal','log'])assert.equal(p.quiet(kind),true);
 for(const kind of ['operator_ask','bazar_approval','ask_form','email_draft','studio_approval','photo_made','pc_file','artifact'])assert.equal(p.quiet(kind),false);
});
test('progress is general English, never tool arguments or reasoning',()=>{
 assert.equal(p.phase('think',{text:'secret'}),'Thinking…');assert.equal(p.phase('step',{tool:'internal',args:'secret'}),'Working on it…');
 assert.equal(p.phase('reply_start'),'Preparing your response…');assert.equal(p.phase('browser',{status:'partial'}),'Reviewing an incomplete result…');
 assert.equal(p.phase('browser',{status:'blocked'}),'Waiting for the next step…');
});

test('dropdown activity uses safe event summaries only',()=>{
 assert.equal(p.activity('step',{tool:'browser',args:'SECRET'}),'Checking sources');
 assert.equal(p.activity('think',{text:'SECRET'}),'Considering the request');
 assert.equal(p.activity('say',{text:'SECRET'}),null);
 assert.equal(p.activity('browser',{status:'failed'}),'Checking an incomplete result');
});

test('search indicators reflect actual tool events and safe completion states',()=>{
 assert.equal(p.phase('step',{tool:'google_search',state:'running'}),'Searching sources…');
 assert.equal(p.phase('work',{tool:'drive_find',phase:'running'}),'Searching connected files…');
 assert.equal(p.phase('step',{tool:'email_check',state:'done'}),'Reviewing sources…');
 assert.equal(p.phase('step',{tool:'google_search',state:'error'}),'Reviewing an incomplete result…');
 assert.equal(p.search('step',{id:'s1',tool:'drive_find'}),true);
 assert.equal(p.search('work',{id:'s1',tool:'drive_find'}),false);
 assert.equal(p.search('step',{tool:'google_search'}),false);
});
test('elapsed time is honest wall-clock duration without percentages',()=>{
 assert.equal(p.elapsed(-1),'0s');assert.equal(p.elapsed(59000),'59s');assert.equal(p.elapsed(61000),'1m 1s');
});

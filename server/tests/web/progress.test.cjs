const test=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm'),path=require('path');
const s=fs.readFileSync(path.resolve(__dirname,'../../app/static/console/workspace.js'),'utf8');const context={window:{}};
vm.runInNewContext(s.slice(s.indexOf('window.HoolaProgressPolicy =')),context);const p=context.window.HoolaProgressPolicy;
test('routine operations collapse while action and output cards remain available',()=>{
 for(const kind of ['browser','operator_task','step','think','work','say','goal','log'])assert.equal(p.quiet(kind),true);
 for(const kind of ['operator_ask','bazar_approval','ask_form','email_draft','studio_approval','photo_made','pc_file','artifact'])assert.equal(p.quiet(kind),false);
});
test('progress is general English, never tool arguments or reasoning',()=>{
 assert.equal(p.phase('think',{text:'secret'}),'Thinking…');assert.equal(p.phase('step',{tool:'internal',args:'secret'}),'Working on it…');
 assert.equal(p.phase('reply_start'),'Preparing your response…');assert.equal(p.phase('browser',{status:'partial'}),'Reviewing an incomplete result…');
 assert.equal(p.phase('browser',{status:'blocked'}),'Waiting for the next step…');
});

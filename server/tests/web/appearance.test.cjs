const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.resolve(__dirname,'../../app/static/console/appearance-init.js'),'utf8');
function boot(value,dark=false,deny=false){const document={documentElement:{dataset:{}}};vm.runInNewContext(source,{document,localStorage:{getItem(){if(deny)throw Error('storage unavailable');return value;}},matchMedia:()=>({matches:dark})});return document.documentElement.dataset;}
test('saved explicit appearance is applied before paint',()=>{assert.deepEqual(boot('{"theme":"dark","font":"readable"}'),{theme:'dark',chatFont:'readable'});});
test('system mode follows the platform in both directions',()=>{assert.equal(boot('{}',true).theme,'dark');assert.equal(boot('{}',false).theme,'light');});
test('invalid preference values cannot alter style attributes',()=>{assert.deepEqual(boot('{"theme":"invalid","font":"invalid"}'),{theme:'light',chatFont:'default'});});
test('blocked or malformed browser storage does not break startup',()=>{assert.equal(boot('bad json').chatFont,'default');assert.equal(boot('{}',true,true).theme,'dark');});

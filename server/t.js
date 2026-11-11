
const H=require('./merged.js');const fx=JSON.parse(require('fs').readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(fx.map(f=>{const p=H.paramsFor(f.kernel,f.params);const K=H.K[f.kernel];
 if(f.calc) return {calc:H.CALCS[f.calc].fn(f.rows,p)};
 const s=K.init(p);K.step(s,p,0.04);return {view:K.view(s,p),measure:K.measure(p),table:K.table(p),tb:H.TEXTBOOK[f.kernel](p)};})));

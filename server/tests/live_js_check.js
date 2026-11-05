const L=require(process.argv[2]);const a=require("assert");
const ch=[{start:1,dur:2,frames:[0,1,2,3,4,5]},{start:3,dur:1,frames:[]}];
a.deepStrictEqual(L.pick(ch,0.5),null);                                  // before the first chunk
let p=L.pick(ch,1.0);a.strictEqual(p.k,0);a.strictEqual(p.idx,0);a.ok(p.have);
p=L.pick(ch,1.2);a.strictEqual(p.idx,5);a.ok(p.have);                    // 0.2 s * 25 = frame 5
p=L.pick(ch,1.5);a.ok(!p.have);a.strictEqual(p.idx,5);                   // frame 12 not here yet: hold the last one
p=L.pick(ch,3.2);a.strictEqual(p.k,1);a.ok(!p.have);                     // chunk 2 has no pictures yet
p=L.pick(ch,4.5);a.ok(p.over);                                           // after the end
a.strictEqual(L.startFor(10,0,0.35,true),10.35);                         // first chunk waits for the jitter buffer
a.strictEqual(L.startFor(10,12,0.35,false),12);                          // next chunk follows the previous exactly
a.ok(Math.abs(L.startFor(10,5,0.35,false)-10.02)<1e-9);                  // a late chunk starts at once (a gap, said so)
console.log("live.js ok");

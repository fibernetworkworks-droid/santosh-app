/* Hoola Motion runtime: everything is a pure function of time t (seconds), so any frame can be rendered exactly. */
(function () {
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const HM = {
    clamp,
    p: (t, s, d) => clamp((t - s) / d),
    lerp: (a, b, x) => a + (b - a) * x,
    e: {
      out: x => 1 - Math.pow(1 - x, 3),
      in: x => x * x * x,
      io: x => (x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
      back: x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); },
      elastic: x => (x <= 0 ? 0 : x >= 1 ? 1 : Math.pow(2, -10 * x) * Math.sin((x * 10 - .75) * (2 * Math.PI) / 3) + 1),
    },
    /** opacity of something on screen from a to b, fading in fi s and out fo s */
    vis(t, a, b, fi = .4, fo = .4) {
      if (t < a || t > b) return 0;
      return Math.min(HM.e.out(HM.p(t, a, fi)), 1 - HM.e.in(HM.p(t, b - fo, fo)));
    },
    rnd(seed) {
      let s = seed >>> 0 || 7;
      return () => { s = (s + 0x6D2B79F5) | 0; let x = Math.imul(s ^ (s >>> 15), 1 | s);
        x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x; return ((x ^ (x >>> 14)) >>> 0) / 4294967296; };
    },
    el(tag, cls, parent, text) {
      const n = document.createElement(tag);
      if (cls) n.className = cls;
      if (text != null) n.textContent = text;
      (parent || document.getElementById("stage")).appendChild(n);
      return n;
    },
    /** transform helper: x/y in vmin, s scale, r degrees */
    put(n, o = 1, x = 0, y = 0, s = 1, r = 0, extra = "") {
      n.style.opacity = o;
      n.style.transform = `translate(${x}vmin, ${y}vmin) scale(${s}) rotate(${r}deg) ${extra}`;
    },
    words(n, text) {
      n.textContent = "";
      return String(text || "").split(/(\s+)/).filter(w => w.length).map(w => HM.el("span", "word", n, w));
    },
    hex(c, d) { return /^#[0-9a-fA-F]{6}$/.test(c || "") ? c : d; },
    mix(a, b, x) {
      const p = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
      const A = p(a), B = p(b);
      return "#" + A.map((v, i) => Math.round(v + (B[i] - v) * x).toString(16).padStart(2, "0")).join("");
    },
    /** "500+" -> {pre:"", n:500, suf:"+"}; "₹1,299" -> {pre:"₹", n:1299, suf:""} */
    num(s) {
      const m = String(s || "").match(/^(\D*?)(\d[\d,]*(?:\.\d+)?)(.*)$/);
      if (!m) return null;
      return { pre: m[1], n: parseFloat(m[2].replace(/,/g, "")), suf: m[3], dec: (m[2].split(".")[1] || "").length, comma: m[2].includes(",") };
    },
    fmt(n, d, comma) {
      const v = n.toFixed(d);
      return comma ? Number(v).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d }) : v;
    },
    stage() { return document.getElementById("stage"); },
    badge(text) { HM.el("div", "ai-badge", null, text || "AI · Hoola"); },
    /** soft moving colour blobs behind everything */
    blobs(colors, seed) {
      const R = HM.rnd(seed || 3), list = colors.map((c, i) => {
        const b = HM.el("div", "blob");
        const size = 45 + R() * 40;
        Object.assign(b.style, { width: size + "vmin", height: size + "vmin", background: c, left: (R() * 70) + "%", top: (R() * 80) + "%" });
        return { b, ax: 8 + R() * 10, ay: 8 + R() * 14, sp: .25 + R() * .3, ph: R() * 6 };
      });
      return t => list.forEach(o => { o.b.style.transform = `translate(${Math.sin(t * o.sp + o.ph) * o.ax}vmin, ${Math.cos(t * o.sp * .8 + o.ph) * o.ay}vmin)`; });
    },
  };
  window.HM = HM;
  window.HOOLA_READY = (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => true);
})();

/* Prayogshala studio RIG: the computational physics WORKSTATION (B.Sc. "Computational physics" practicals).
   One bench serves every method in the comp_ug kernel pack: desk mat, monitor, keyboard with a live Enter key,
   mouse, tower and the printed METHOD CARD. The student reads the card, switches the machine on, chooses the
   method and the step size / sample count, presses Enter - and the MONITOR DRAWS the computation: the exact curve,
   what the method built, and the nodes it actually used, with the run log beside it.
   Every number comes from the lab's kernel (HoolaKernels.K[lab.kernel]) at the student's settings - the same code
   the server checks - so the error printed on the screen is the real error of that method at that step size. */
HoolaStudio.define('comp-workstation', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels;
  var KNAME = S.lab.kernel, K = HK.K[KNAME];
  function labParams() {
    var o = {};
    (S.lab.knobs || []).forEach(function (k) { if (k.param) o[k.param] = k.value * (k.k || 1); });
    var lp = S.lab.params || {};
    Object.keys(lp).forEach(function (key) { o[key] = lp[key]; });
    return HK.paramsFor(KNAME, o);
  }
  var p = labParams();
  var VAR = S.lab.variant || {};
  var CAS = Math.round(p.cas === undefined ? 0 : p.cas);

  // ---------------------------------------------------------------- what each method family is, for the eye
  function fmt(v, d) {                                 // the engine's number format, but usable while the bench is built
    if (!isFinite(v)) return '—';
    var a = Math.abs(v);
    if (d === undefined) d = a >= 100 ? 1 : a >= 10 ? 2 : a >= 1 ? 3 : 4;
    var o = v.toFixed(d);
    return /^-0(\.0*)?$/.test(o) ? o.slice(1) : o;
  }
  function fx(v, d) { return fmt(v, d); }
  function sci(v) {
    if (!isFinite(v)) return '—';
    if (v === 0) return '0';
    var a = Math.abs(v);
    if (a >= 1e-4 && a < 1e5) return v.toFixed(Math.max(0, 6 - Math.max(0, Math.floor(Math.log(a) / Math.LN10))));
    return v.toExponential(2);
  }
  var SPEC = {
    cp_root: {
      quantity: 'root x', unit: '', digits: 6, nlabel: 'iterations', ns: [4, 8, 12, 16, 24], tol: 0.01,
      methods: ['Bisection', 'Newton-Raphson', 'Secant'], xlabel: 'x', ylabel: 'f(x)', zero: true,
      title: ['xᵐ − a = 0', 'd³ − 3R d² + 4sR³ = 0', 'tan α − α = 0'][CAS] || 'f(x) = 0',
      problem: function () {
        if (CAS === 1) return ['A sphere of radius R = ' + fx(p.R * 100, 1) + ' cm and relative density s = ' + fx(p.s, 3),
          'floats in water. The submerged cap of depth d obeys', 'd³ − 3R d² + 4 s R³ = 0  on  0 < d < 2R',
          'Bracket: [' + fx(p.xa, 3) + ', ' + fx(p.xb, 3) + '] m   Start: x₀ = ' + fx(p.x0, 3) + ' m'];
        if (CAS === 2) return ['Solve  tan α = α  for the first root beyond π.',
          'Bracket: [' + fx(p.xa, 2) + ', ' + fx(p.xb, 2) + ']', 'Newton start: x₀ = ' + fx(p.x0, 2) + ', secant x₁ = ' + fx(p.x1, 2),
          'f(α) = tan α − α,  f′(α) = tan²α'];
        return ['Solve  x^' + fx(p.m, 0) + ' = ' + fx(p.a, 4) + ',  that is  f(x) = x^' + fx(p.m, 0) + ' − ' + fx(p.a, 4),
          'f′(x) = ' + fx(p.m, 0) + ' x^' + fx(p.m - 1, 0), 'Bracket: [' + fx(p.xa, 3) + ', ' + fx(p.xb, 3) + ']',
          'Start: x₀ = ' + fx(p.x0, 3) + ',  secant x₁ = ' + fx(p.x1, 3)];
      },
      formula: 'bisect: halve the bracket · Newton: x − f/f′ · secant: chord',
    },
    cp_quad: {
      quantity: 'integral I', unit: '', digits: 8, nlabel: 'strips n', ns: [4, 8, 16, 32, 64], tol: 0.01,
      // a narrow delta sequence has to be sampled far more finely before any rule can see the peak at all
      nsCase: { 3: [50, 100, 200, 400, 800] },
      methods: ['Trapezoidal', 'Simpson 1/3', 'Simpson 3/8', 'Gauss-Legendre'], xlabel: 'x', ylabel: 'f(x)', fill: true,
      title: ['∫ dx / x', '∫ A sin(ωx) dx', '∫ A x^k dx', '∫ delta sequence'][CAS] || '∫ f(x) dx',
      problem: function () {
        var lim = 'from x = ' + fx(p.xa, 4) + ' to x = ' + fx(p.xb, 4);
        if (CAS === 1) return ['Integrate  f(x) = ' + fx(p.A, 3) + ' sin(' + fx(p.w, 3) + ' x)', lim,
          'Exact:  A (cos ωa − cos ωb) / ω = ' + sci(ex0)];
        if (CAS === 2) return ['Integrate  f(x) = ' + fx(p.A, 3) + ' x^' + fx(p.kk, 2), lim,
          'Exact:  A (b^(k+1) − a^(k+1)) / (k+1) = ' + sci(ex0)];
        if (CAS === 3) return ['Integrate the Lorentzian of width ε = ' + fx(p.eps, 3),
          'f(x) = ε / (π (x² + ε²))', lim, 'Exact:  (2/π) arctan(L/ε) = ' + sci(ex0)];
        return ['Integrate  f(x) = 1 / x', lim, 'Exact:  ln(b/a) = ' + sci(ex0)];
      },
      formula: 'trapezoid h/2 · Simpson h/3 (4,2…) · Gauss Σ wᵢ f(xᵢ)',
    },
    cp_ode1: {
      quantity: 'y at t = end', unit: '', digits: 6, nlabel: 'steps n', ns: [10, 25, 50, 100, 250, 500], tol: 0.02,
      methods: ['Euler', 'RK2 (Heun)', 'RK4'], xlabel: 't', ylabel: 'y(t)', showCurve: true,
      title: ['dN/dt = −λN', 'R dq/dt + q/C = E', 'dT/dt = −k(T − Ts)', 'dN/dt = rN(1 − N/K)'][CAS] || 'dy/dt = f(t, y)',
      problem: function () {
        var end = 'Integrate from t = 0 to t = ' + fx(p.tmax, 3) + ',  y(0) = ' + fx(p.y0, 4);
        if (CAS === 1) return ['Charging a capacitor:  R dq/dt + q/C = E',
          'R = ' + fx(p.Rr, 0) + ' Ω,  C = ' + sci(p.Cc) + ' F,  E = ' + fx(p.Em, 3) + ' V', end,
          'Exact:  q = CE(1 − e^(−t/RC))'];
        if (CAS === 2) return ['Newton\'s law of cooling:  dT/dt = −k(T − Ts)',
          'k = ' + fx(p.kk, 4) + ' /s,  Ts = ' + fx(p.Ts, 1) + ' °C', end, 'Exact:  Ts + (T₀ − Ts) e^(−kt)'];
        if (CAS === 3) return ['Logistic growth:  dN/dt = rN(1 − N/K)',
          'r = ' + fx(p.rr, 3) + ',  K = ' + fx(p.Kk, 4), end, 'Exact:  K N₀ e^(rt) / (K + N₀(e^(rt) − 1))'];
        return ['Radioactive decay:  dN/dt = −λN', 'λ = ' + fx(p.lam, 5) + ' per unit time', end,
          'Exact:  N₀ e^(−λt)'];
      },
      formula: 'Euler y+hf · Heun y+h(k₁+k₂)/2 · RK4 (k₁+2k₂+2k₃+k₄)/6',
    },
    cp_diff: {
      quantity: 'derivative f′(x)', unit: '', digits: 6, nlabel: 'step: h = h₀/n', ns: [2, 5, 10, 20, 40, 80],
      tol: 0.03, methods: ['Forward', 'Backward', 'Central', 'Five-point'], xlabel: 'x', ylabel: 'f(x)',
      showCurve: true, title: ['f(x) = A sin(ωx)', 'f(x) = A e^(ωx)', 'f(x) = A x^k'][CAS] || 'f(x)',
      problem: function () {
        var at = 'Differentiate at x = ' + fx(p.x, 4) + ',  h₀ = ' + fx(p.h0, 3);
        if (CAS === 1) return ['f(x) = ' + fx(p.A, 3) + ' e^(' + fx(p.w, 3) + ' x)', at, 'Exact:  A ω e^(ωx) = ' + sci(ex0)];
        if (CAS === 2) return ['f(x) = ' + fx(p.A, 3) + ' x^' + fx(p.kk, 2), at, 'Exact:  A k x^(k−1) = ' + sci(ex0)];
        return ['f(x) = ' + fx(p.A, 4) + ' sin(' + fx(p.w, 4) + ' x)', at, 'Exact:  A ω cos(ωx) = ' + sci(ex0)];
      },
      formula: 'forward Δf/h · central Δf/2h · five-point (−f₂+8f₁−8f₋₁+f₋₂)/12h',
    },
    cp_approx: {
      quantity: 'f(x)', unit: '', digits: 8, nlabel: 'terms / nodes n', ns: [2, 3, 5, 8, 12], tol: 0.01,
      methods: ['Taylor partial sum', 'Lagrange polynomial'], xlabel: 'x', ylabel: 'f(x)', showCurve: true,
      title: ['f(x) = eˣ', 'f(x) = sin x', 'f(x) = cos x', 'f(x) = ln(1 + x)'][CAS] || 'f(x)',
      problem: function () {
        var f = ['eˣ', 'sin x', 'cos x', 'ln(1 + x)'][CAS] || 'f(x)';
        return ['Approximate  f(x) = ' + f + '  at  x = ' + fx(p.x, 4),
          'Taylor: the first n terms about x = 0',
          'Lagrange: n + 1 equally spaced nodes on [' + fx(p.xa, 3) + ', ' + fx(p.xb, 3) + ']',
          'Exact:  f(x) = ' + sci(ex0)];
      },
      formula: 'Taylor Σ f⁽ᵏ⁾(0) xᵏ/k! · Lagrange Σ f(xᵢ) Πⱼ≠ᵢ (x−xⱼ)/(xᵢ−xⱼ)',
    },
    cp_ode2: {
      quantity: 'x at the end', unit: 'm', digits: 6, nlabel: 'steps n', ns: [50, 100, 200, 500, 1000, 2000],
      tol: 0.03, methods: ['Euler', 'RK2 (Heun)', 'RK4'], xlabel: 't (s)', ylabel: 'x (m)', showCurve: true,
      caseOver: { 1: { quantity: 'steady amplitude', unit: 'm' } },
      title: ['m x″ + c x′ + k x = 0', 'm x″ + c x′ + k x = F cos(ωt)'][CAS] || 'second-order IVP',
      problem: function () {
        var g = p.cc / (2 * p.mm), w0 = Math.sqrt(p.kk / p.mm);
        var regime = g <= 1e-12 * Math.max(w0, 1) ? 'undamped (c = 0)'
          : Math.abs(g - w0) <= 1e-8 * w0 ? 'critically damped (γ = ω₀)'
            : g < w0 ? 'underdamped (γ < ω₀)' : 'overdamped (γ > ω₀)';
        var out = ['m = ' + fx(p.mm, 4) + ',  c = ' + fx(p.cc, 4) + ',  k = ' + fx(p.kk, 4),
          'ω₀ = √(k/m) = ' + fx(w0, 4) + ' rad/s,  γ = c/2m = ' + fx(g, 4) + ' /s', 'This set-up is ' + regime];
        if (CAS === 1) out.push('Driven by F = ' + fx(p.FF, 4) + ' N at ω = ' + fx(p.wf, 4) + ' rad/s',
          'Exact steady amplitude = ' + sci(ex0) + ' m', 'Run to t = ' + fx(p.tmax, 2) + ' s; the transient dies first');
        else out.push('x(0) = ' + fx(p.x0, 4) + ' m,  v(0) = 0', 'Integrate to t = ' + fx(p.tmax, 3) + ' s',
          'Exact x at that time = ' + sci(ex0) + ' m');
        return out;
      },
      formula: 'as a pair: x′ = v, v′ = (F cos ωt − c v − k x)/m',
    },
    cp_mc: {
      quantity: 'estimate', unit: '', digits: 6, nlabel: 'samples N', ns: [1000, 4000, 16000, 64000, 256000],
      tol: 0.02, methods: ['Monte Carlo'], xlabel: 'N (samples, log scale)', ylabel: 'running estimate',
      showCurve: true, logx: true, yFrom: 0.3,
      caseOver: { 0: { quantity: 'pi' }, 1: { quantity: 'integral I' }, 2: { quantity: 'sample mean' },
        3: { quantity: 'P(k heads)' }, 4: { quantity: 'spread of the mean' }, 5: { quantity: 'sample mean' },
        6: { quantity: 'spread of f = x y' } },
      title: ['pi by acceptance-rejection', 'a definite integral by the sample mean', 'the mean of uniform numbers',
        'coin-toss macrostates', 'the central limit theorem', 'the mean of an exponential population',
        'error propagation in f = x y'][CAS] || 'Monte Carlo',
      problem: function () {
        if (CAS === 1) return ['Estimate ∫₀¹ eˣ dx as the mean of eᵘ over N uniform numbers u.',
          'Exact:  e − 1 = ' + sci(ex0), 'Seed = ' + fx(p.seed, 0) + ' (the run repeats exactly)'];
        if (CAS === 2) return ['Average N uniform random numbers on (0, 1).', 'Exact population mean = 0.5',
          'The error of the mean falls as 1/√N.', 'Seed = ' + fx(p.seed, 0)];
        if (CAS === 3) return ['Toss ' + fx(p.mtoss, 0) + ' coins, N times, and count how often exactly '
          + fx(p.khead, 0) + ' heads come up.', 'Exact macrostate probability = C(m,k)/2^m = ' + sci(ex0),
          'Seed = ' + fx(p.seed, 0)];
        if (CAS === 4) return ['Each sample is the mean of ' + fx(p.mtoss, 0) + ' uniform numbers.',
          'Measure the standard deviation of those means over N samples.',
          'Exact (central limit theorem):  1/√(12 m) = ' + sci(ex0), 'Seed = ' + fx(p.seed, 0)];
        if (CAS === 5) return ['Draw N waiting times from an exponential population of rate λ = ' + fx(p.rate, 4),
          'by the inverse transform x = −ln(u)/λ, and average them.', 'Exact population mean = 1/λ = ' + sci(ex0),
          'Seed = ' + fx(p.seed, 0)];
        if (CAS === 6) return ['x = ' + fx(p.mx, 3) + ' ± ' + fx(p.sx, 4) + ',  y = ' + fx(p.my, 3) + ' ± '
          + fx(p.sy, 4) + ',  correlation ρ = ' + fx(p.rho, 3),
          'Draw N correlated pairs and measure the spread of f = x y.',
          'Propagation formula:  σf = √(y²σx² + x²σy² + 2xyρσxσy) = ' + sci(ex0), 'Seed = ' + fx(p.seed, 0)];
        return ['Throw N points into the unit square and count those inside the quarter circle.',
          'pi ≈ 4 × (points inside) / N', 'Exact:  pi = ' + sci(ex0), 'Seed = ' + fx(p.seed, 0) + ' (the run repeats exactly)'];
      },
      formula: 'the error of a Monte Carlo estimate falls as 1/√N, whatever the dimension',
    },
    cp_proj: {
      quantity: 'range R', unit: 'm', digits: 5, nlabel: 'steps n', ns: [10, 20, 50, 100, 200, 500], tol: 0.01,
      methods: ['Euler', 'RK2 (Heun)', 'RK4'], xlabel: 'x (m)', ylabel: 'y (m)',
      caseOver: { 1: { quantity: 'greatest height H', unit: 'm' }, 2: { quantity: 'time of flight T', unit: 's' } },
      title: 'projectile:  ẍ = 0,  ÿ = −g',
      problem: function () {
        return ['Launch speed u = ' + fx(p.u, 3) + ' m/s at θ = ' + fx(p.th * 180 / Math.PI, 2) + '°,  g = '
          + fx(p.g, 3) + ' m/s²', 'Integrate the two second-order equations as four first-order ones.',
          'The landing point is found by interpolating the step that crosses the ground.',
          'Exact:  R = u² sin2θ/g,  H = u² sin²θ/2g,  T = 2u sinθ/g', 'Here the exact value is ' + sci(ex0)];
      },
      formula: 'state [x, y, vₓ, v_y];  ẋ = vₓ, ẏ = v_y, v̇ₓ = 0, v̇_y = −g',
    },
  };
  var ex0 = K.measure(p).exact;                        // the exact answer, for the printed card
  var SP = SPEC[KNAME] || SPEC.cp_quad;
  if (SP.caseOver && SP.caseOver[CAS]) Object.keys(SP.caseOver[CAS]).forEach(function (k) { SP[k] = SP.caseOver[CAS][k]; });
  var NS = (SP.nsCase && SP.nsCase[CAS]) || SP.ns, METHODS = SP.methods;
  var M0 = Math.min(METHODS.length - 1, Math.max(0, Math.round(p.method === undefined ? 0 : p.method)));
  var st = { on: false, mi: M0, ni: Math.max(0, NS.length - 3), last: null, busy: false, reveal: 0 };

  function withSet(ni, mi) {
    var q = {};
    Object.keys(p).forEach(function (k) { q[k] = p[k]; });
    q.n = NS[ni]; q.method = mi;
    return q;
  }
  function compute(ni, mi) {
    var q = withSet(ni, mi);
    var s = K.init(q);
    var v = K.view(s, q);
    v.set = q;
    return v;
  }
  var preview = compute(st.ni, st.mi);                 // what the dark screen shows as a "saved" plot

  // ================================================================================= the workstation
  var MX = 0.15, MZ = -0.45;                           // monitor centre
  S.contact(1.0, 0.5, 0.12, -0.14, 0.42);
  var mat = S.rounded(0.92, 0.46, 0.004, 0.01, new T.MeshStandardMaterial({ color: 0x0b0d10, roughness: 0.96 }));
  mat.rotation.x = -Math.PI / 2; mat.position.set(0.12, 0.002, -0.14); S.scene.add(mat);

  // ---- monitor
  var mon = new T.Group(); mon.position.set(MX, 0, MZ); S.scene.add(mon);
  var foot = S.rounded(0.24, 0.15, 0.014, 0.012, M.bakelite); foot.rotation.x = -Math.PI / 2; foot.position.y = 0.007; mon.add(foot);
  var neck = S.mesh(new T.CylinderGeometry(0.014, 0.019, 0.12, 24), M.bakelite); neck.position.set(0, 0.07, -0.005); mon.add(neck);
  var panel = new T.Group(); panel.position.set(0, 0.228, 0.004); panel.rotation.x = -0.06; mon.add(panel);
  var bezel = S.rounded(0.368, 0.238, 0.02, 0.006, M.bakelite); panel.add(bezel);
  var screenTex = S.liveTex(1024, 620);
  var scrMat = new T.MeshBasicMaterial({ map: screenTex, toneMapped: false });
  var screen = new T.Mesh(new T.PlaneGeometry(0.336, 0.2035), scrMat); screen.position.set(0, 0.006, 0.0115); panel.add(screen);
  var glow = new T.PointLight(0x9fc9ff, 0, 0.6); glow.position.set(0, 0.24, -0.3); S.scene.add(glow);
  var pwr = S.mesh(new T.CylinderGeometry(0.004, 0.004, 0.004, 18), M.grey);
  pwr.rotation.x = Math.PI / 2; pwr.position.set(0.15, -0.107, 0.012); panel.add(pwr);
  var led = new T.Mesh(new T.CircleGeometry(0.0022, 14), new T.MeshBasicMaterial({ color: 0x1d4020 }));
  led.position.set(0.128, -0.107, 0.0122); panel.add(led);
  var brand = S.label('HOOLA  LABVIEW 24″', { w: 0.07, ratio: 0.14, color: '#8a8f98' });
  brand.position.set(-0.12, -0.107, 0.0122); panel.add(brand);
  S.contact(0.34, 0.22, MX, MZ, 0.5);

  // ---- keyboard, with an Enter key the hand really presses
  var KBX = 0.15, KBZ = -0.1;
  var kbd = new T.Group(); kbd.position.set(KBX, 0, KBZ); S.scene.add(kbd);
  var kbTex = S.canvasTex(1024, 360, function (x, w, h) {
    x.fillStyle = '#1b1d21'; x.fillRect(0, 0, w, h);
    var rows = [['esc', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12'],
      ['~', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '⌫'],
      ['tab', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']'],
      ['caps', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', "'"],
      ['shift', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/'],
      ['ctrl', 'alt', '', '', '', 'alt', 'ctrl']];
    for (var r = 0; r < rows.length; r++) {
      var y = 14 + r * 56, kx = 14;
      for (var c = 0; c < rows[r].length; c++) {
        var t = rows[r][c], kw = t.length > 1 ? 86 : 58;
        if (t === '') kw = 230;
        x.fillStyle = '#2a2d33'; x.beginPath(); x.rect(kx, y, kw - 6, 48); x.fill();
        x.fillStyle = '#3a3e46'; x.fillRect(kx, y, kw - 6, 4);
        x.fillStyle = '#d7dae0'; x.font = (t.length > 1 ? '500 20px' : '600 24px') + ' "Public Sans", sans-serif';
        x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(t, kx + (kw - 6) / 2, y + 26);
        kx += kw;
      }
    }
  });
  var kbBody = S.rounded(0.34, 0.13, 0.014, 0.004, M.bakelite); kbBody.rotation.x = -Math.PI / 2; kbBody.position.y = 0.007; kbd.add(kbBody);
  var kbFace = new T.Mesh(new T.PlaneGeometry(0.33, 0.116), new T.MeshStandardMaterial({ map: kbTex, roughness: 0.6 }));
  kbFace.rotation.x = -Math.PI / 2; kbFace.position.set(0, 0.0145, 0); kbd.add(kbFace);
  var enter = S.rounded(0.036, 0.022, 0.009, 0.002, new T.MeshStandardMaterial({ color: 0x2f3d55, roughness: 0.45 }));
  enter.rotation.x = -Math.PI / 2; enter.position.set(0.146, 0.018, -0.012); kbd.add(enter);
  var enterLbl = S.label('ENTER', { w: 0.03, ratio: 0.3, color: '#e6ecf5' });
  enterLbl.rotation.x = -Math.PI / 2; enterLbl.position.set(0.146, 0.0232, -0.012); kbd.add(enterLbl);
  S.contact(0.4, 0.2, KBX, KBZ, 0.45);

  // ---- mouse + tower
  var mouse = new T.Group(); mouse.position.set(0.44, 0, -0.1); S.scene.add(mouse);
  var mb = S.mesh(new T.SphereGeometry(0.033, 24, 16), new T.MeshStandardMaterial({ color: 0x17191d, roughness: 0.75 }));
  mb.scale.set(0.74, 0.36, 1.2); mb.position.y = 0.009; mouse.add(mb);
  var wheel = S.mesh(new T.TorusGeometry(0.004, 0.0016, 8, 16), M.grey); wheel.rotation.y = Math.PI / 2; wheel.position.set(0, 0.026, 0.012); mouse.add(wheel);
  S.contact(0.1, 0.12, 0.44, -0.1, 0.4);
  var tower = new T.Group(); tower.position.set(0.66, 0, -0.5); S.scene.add(tower);
  var tbody = S.rounded(0.18, 0.36, 0.38, 0.008, new T.MeshStandardMaterial({ color: 0x23262b, roughness: 0.5 }));
  tbody.position.y = 0.19; tower.add(tbody);
  var vent = S.canvasTex(256, 512, function (x, w, h) {
    x.fillStyle = '#1b1e22'; x.fillRect(0, 0, w, h);
    for (var i = 0; i < 34; i++) { x.fillStyle = 'rgba(0,0,0,.55)'; x.fillRect(30, 90 + i * 11, w - 60, 5); }
  });
  var tfront = new T.Mesh(new T.PlaneGeometry(0.17, 0.34), new T.MeshStandardMaterial({ map: vent, roughness: 0.7 }));
  tfront.position.set(0, 0.19, 0.1905); tower.add(tfront);
  var tled = new T.Mesh(new T.CircleGeometry(0.004, 14), new T.MeshBasicMaterial({ color: 0x14361c }));
  tled.position.set(0.055, 0.345, 0.1912); tower.add(tled);
  var tlbl = S.label('HOOLA WS-4', { w: 0.07, ratio: 0.18, color: '#9aa0a8' }); tlbl.position.set(-0.03, 0.345, 0.1912); tower.add(tlbl);
  S.contact(0.26, 0.46, 0.66, -0.5, 0.5);

  // ---- the printed method card (A5, lying on the bench)
  var cardLines = SP.problem();
  var cardTex = S.canvasTex(840, 1188, function (x, w, h) {
    x.fillStyle = '#fbf8f0'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#e4ddc9'; x.fillRect(0, 0, w, 170);
    x.fillStyle = '#1f3a8a'; x.font = '700 58px "Public Sans", sans-serif'; x.fillText('METHOD CARD', 50, 84);
    x.fillStyle = '#3c4654'; x.font = '600 32px "Public Sans", sans-serif'; x.fillText('Computational Physics Laboratory', 50, 134);
    x.fillStyle = '#121418'; x.font = '700 46px "Public Sans", sans-serif';
    var y = 248; y = wrap(x, SP.title, 50, y, w - 100, 54) + 26;
    x.strokeStyle = '#b9b19a'; x.lineWidth = 3; x.beginPath(); x.moveTo(50, y); x.lineTo(w - 50, y); x.stroke(); y += 62;
    x.font = '500 34px "Public Sans", sans-serif'; x.fillStyle = '#1b1f26';
    cardLines.forEach(function (t) { y = wrap(x, t, 50, y, w - 100, 44) + 44; });
    y += 18; x.fillStyle = '#5a6472'; x.font = '600 30px "Public Sans", sans-serif';
    x.fillText('Methods available', 50, y); y += 46;
    x.fillStyle = '#1b1f26'; x.font = '500 34px "Public Sans", sans-serif';
    METHODS.forEach(function (m2, i) { x.fillText((i + 1) + '.  ' + m2, 68, y); y += 44; });
    y += 14; x.fillStyle = '#5a6472'; x.font = '500 28px "Public Sans", sans-serif';
    y = wrap(x, SP.formula, 50, y, w - 100, 38) + 72;
    x.fillStyle = '#7a1f1f'; x.font = '600 31px "Public Sans", sans-serif';
    wrap(x, 'Record for every run: the method, n, the answer and the error. Report the answer at the largest n.', 50, y, w - 100, 42);
    x.fillStyle = '#8a9099'; x.font = '500 26px "Public Sans", sans-serif';
    x.fillText('Hoola Prayogshala · ' + (VAR.sample || 'standard test problem'), 50, h - 48);
  });
  function wrap(x, text, x0, y0, maxw, lh) {
    var words = String(text).split(' '), line = '', yy = y0, i;
    for (i = 0; i < words.length; i++) {
      var t = line ? line + ' ' + words[i] : words[i];
      if (x.measureText(t).width > maxw && line) { x.fillText(line, x0, yy); yy += lh; line = words[i]; } else line = t;
    }
    if (line) x.fillText(line, x0, yy);
    return yy;      // the baseline of the last line, so the caller can carry on below it
  }
  var card = new T.Group(); card.position.set(-0.13, 0, 0.03); card.rotation.y = 0.05; S.scene.add(card);
  var cardPad = S.mesh(new T.BoxGeometry(0.214, 0.002, 0.301), M.paper, false); cardPad.position.y = 0.001; card.add(cardPad);
  var cardM = new T.Mesh(new T.PlaneGeometry(0.21, 0.297), new T.MeshStandardMaterial({ map: cardTex, roughness: 0.9 }));
  cardM.rotation.x = -Math.PI / 2; cardM.position.y = 0.0032; card.add(cardM);      // clear of the pad: no z-fighting
  S.contact(0.26, 0.35, -0.13, 0.03, 0.4);

  // ================================================================================= the screen
  function fmtRow(r) {
    return 'n=' + String(r.n) + '   ' + SP.quantity.split(' ')[0] + '=' + sci(r.val) + '   err=' + r.err.toExponential(2);
  }
  function drawScreen() {
    var v = st.on ? (st.last || preview) : preview;
    screenTex.draw(function (x, W, H) {
      // ---- shell
      x.fillStyle = st.on ? '#0b1420' : '#05080c'; x.fillRect(0, 0, W, H);
      if (!st.on) {
        x.fillStyle = '#44566a'; x.font = '600 30px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
        x.fillText('HOOLA LABVIEW — press the power button', W / 2, H / 2);
        x.textAlign = 'left'; x.textBaseline = 'alphabetic';
        return;
      }
      x.fillStyle = '#132231'; x.fillRect(0, 0, W, 56);
      x.fillStyle = '#dce7f4'; x.font = '600 28px "Public Sans", sans-serif'; x.textBaseline = 'middle';
      x.fillText(SP.title + '   ·   ' + METHODS[st.mi], 20, 29);
      x.fillStyle = '#7fe3a1'; x.font = '600 22px "JetBrains Mono", monospace'; x.textAlign = 'right';
      x.fillText(SP.nlabel + ' = ' + NS[st.ni], W - 20, 29); x.textAlign = 'left';
      // ---- plot panel
      var P = { l: 86, r: 404, t: 92, b: 100 }, pw = W - P.l - P.r, ph = H - P.t - P.b;
      x.fillStyle = '#081019'; x.fillRect(P.l - 60, P.t - 28, pw + 72, ph + 56);
      var cx = v.cx || [], ce = v.ce || [], cy = v.cy || [], px = v.px || [], py = v.py || [];
      var LOGX = !!SP.logx, tx = function (q) { return LOGX ? Math.log(Math.max(q, 1)) / Math.LN10 : q; };
      var from = Math.floor((cy.length || 0) * (SP.yFrom || 0));
      var xs = cx.map(tx), ys = [];
      [ce, py].forEach(function (a) { a.forEach(function (q) { if (isFinite(q)) ys.push(q); }); });
      var cyx = (cy.length === cx.length) ? cx : px;
      cy.forEach(function (q, i) { if (isFinite(q) && i >= from && i < cyx.length) { ys.push(q); } });
      px.forEach(function (q) { if (isFinite(q)) xs.push(tx(q)); });
      if (!xs.length) { xs = [0, 1]; } if (!ys.length) { ys = [0, 1]; }
      var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
      var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
      if (SP.zero) { y0 = Math.min(y0, 0); y1 = Math.max(y1, 0); }
      if (x1 - x0 < 1e-12) x1 = x0 + 1; if (y1 - y0 < 1e-12) y1 = y0 + 1;
      var pad = (y1 - y0) * 0.12; y0 -= pad; y1 += pad;
      var X = function (q) { return P.l + (q - x0) / (x1 - x0) * pw; };
      var Y = function (q) { return H - P.b - (q - y0) / (y1 - y0) * ph; };
      // grid + axes
      x.strokeStyle = '#17293c'; x.lineWidth = 1; x.fillStyle = '#6f88a3'; x.font = '500 19px "JetBrains Mono", monospace';
      for (var i = 0; i <= 4; i++) {
        var gx = x0 + (x1 - x0) * i / 4, gy = y0 + (y1 - y0) * i / 4;
        x.beginPath(); x.moveTo(X(gx), Y(y0)); x.lineTo(X(gx), Y(y1)); x.stroke();
        x.beginPath(); x.moveTo(X(x0), Y(gy)); x.lineTo(X(x1), Y(gy)); x.stroke();
        x.textAlign = 'center';
        x.fillText(LOGX ? fmt(Math.pow(10, gx), gx < 3 ? 1 : 0) : fmt(gx, 2), X(gx), H - P.b + 26);
        x.textAlign = 'right'; x.fillText(fmt(gy, 2), P.l - 10, Y(gy) + 7);
      }
      x.textAlign = 'left';
      x.strokeStyle = '#2e4760'; x.lineWidth = 2;
      x.beginPath(); x.moveTo(X(x0), Y(Math.max(y0, Math.min(y1, 0)))); x.lineTo(X(x1), Y(Math.max(y0, Math.min(y1, 0)))); x.stroke();
      x.fillStyle = '#9fb6cf'; x.font = '600 21px "Public Sans", sans-serif';
      x.fillText(SP.xlabel, X(x1) - 14, H - P.b + 54);
      x.save(); x.translate(P.l - 62, Y(y1) + 54); x.rotate(-Math.PI / 2); x.fillText(SP.ylabel, 0, 0); x.restore();
      var rev = Math.max(0.02, Math.min(1, st.reveal));
      // exact curve
      if (SP.fill && cx.length > 1) {
        x.fillStyle = 'rgba(80,170,255,.14)'; x.beginPath(); x.moveTo(X(tx(cx[0])), Y(Math.max(y0, Math.min(y1, 0))));
        for (i = 0; i < cx.length; i++) x.lineTo(X(tx(cx[i])), Y(ce[i]));
        x.lineTo(X(tx(cx[cx.length - 1])), Y(Math.max(y0, Math.min(y1, 0)))); x.closePath(); x.fill();
      }
      x.strokeStyle = '#59b6ff'; x.lineWidth = 4; x.beginPath();
      for (i = 0; i < cx.length; i++) { if (i) x.lineTo(X(tx(cx[i])), Y(ce[i])); else x.moveTo(X(tx(cx[i])), Y(ce[i])); }
      x.stroke();
      // what the method built
      if (cy.length > 1 && SP.showCurve) {
        x.strokeStyle = '#ffc247'; x.lineWidth = 3; x.setLineDash([9, 7]); x.beginPath();
        var nseen = Math.max(2, Math.floor(cy.length * rev));
        for (i = 0; i < nseen && i < cyx.length; i++) { if (i) x.lineTo(X(tx(cyx[i])), Y(cy[i])); else x.moveTo(X(tx(cyx[i])), Y(cy[i])); }
        x.stroke(); x.setLineDash([]);
      }
      // the nodes the method used
      var nnodes = Math.max(1, Math.floor(px.length * rev));
      var stride = Math.max(1, Math.ceil(px.length / 80)), rad = px.length > 40 ? 3.5 : 5.5;
      for (i = 0; i < nnodes; i++) {
        if (!isFinite(px[i]) || !isFinite(py[i])) continue;
        if (i % stride !== 0 && i !== nnodes - 1) continue;
        x.fillStyle = '#ff7b5a'; x.beginPath(); x.arc(X(tx(px[i])), Y(py[i]), rad, 0, Math.PI * 2); x.fill();
        if (KNAME === 'cp_root' && i === nnodes - 1) {
          x.strokeStyle = 'rgba(255,123,90,.5)'; x.lineWidth = 2; x.beginPath();
          x.moveTo(X(tx(px[i])), Y(y0)); x.lineTo(X(tx(px[i])), Y(y1)); x.stroke();
        }
      }
      // legend
      x.font = '500 19px "Public Sans", sans-serif';
      x.fillStyle = '#59b6ff'; x.fillText('— exact', P.l + 6, P.t - 38);
      x.fillStyle = '#ffc247'; x.fillText('– – method', P.l + 110, P.t - 38);
      x.fillStyle = '#ff7b5a'; x.fillText('• nodes used', P.l + 250, P.t - 38);
      // ---- run log
      var RX = W - P.r + 24;
      x.fillStyle = '#0d1a28'; x.fillRect(RX - 14, P.t - 28, P.r - 24, H - P.t - P.b + 56);
      x.fillStyle = '#9fb6cf'; x.font = '600 22px "Public Sans", sans-serif'; x.fillText('RUN LOG', RX, P.t - 2);
      x.font = '500 20px "JetBrains Mono", monospace';
      var rows2 = S.rows.slice(-9), yy = P.t + 34;
      if (!rows2.length) { x.fillStyle = '#5d7791'; x.fillText('no runs yet', RX, yy); }
      rows2.forEach(function (r) {
        x.fillStyle = '#d7e4f2'; x.fillText('n=' + String(r.n).padStart(4, ' ') + '  ' + sci(r.val), RX, yy); yy += 26;
        x.fillStyle = '#86a4c2'; x.fillText('        err ' + r.err.toExponential(2), RX, yy); yy += 32;
      });
      var cur = st.last;
      x.fillStyle = '#132231'; x.fillRect(RX - 14, H - P.b + 4, P.r - 24, 76);
      x.font = '600 23px "JetBrains Mono", monospace';
      if (cur) {
        x.fillStyle = '#7fe3a1'; x.fillText(SP.quantity + ' = ' + sci(cur.val), RX, H - P.b + 34);
        x.font = '600 20px "JetBrains Mono", monospace'; x.fillStyle = '#ffd083';
        x.fillText('exact ' + sci(cur.exact) + '   err ' + cur.err.toExponential(2), RX, H - P.b + 64);
      } else {
        x.fillStyle = '#5d7791'; x.fillText('press ENTER to run', RX, H - P.b + 46);
      }
      x.textBaseline = 'alphabetic';
    });
  }

  // ================================================================================= apparatus list
  S.addApparatus('mon', mon, 'Monitor', 'The plot and the run log. Left: the exact curve, what the method built and the nodes it used. Right: every run with its error.');
  S.addApparatus('kbd', kbd, 'Keyboard', 'Enter runs the method at the settings you have chosen. Nothing is computed until you press it.');
  S.addApparatus('mouse', mouse, 'Mouse', 'For the settings on the panel. The method and the step size are the only two choices this practical needs.');
  S.addApparatus('tower', tower, 'Workstation', 'The computer that runs the method. The same code is used for the check, so the error on the screen is the real error.');
  S.addApparatus('card', card, 'Method card', 'The printed card: the problem, the available methods and the formulas. Read it before you touch the machine.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every run you keep is written here: the method, n, the answer, the exact value and the error.');

  var hudV = S.hudCard('Numerical'), hudE = S.hudCard('Exact'), hudErr = S.hudCard('Rel. error'), hudN = S.hudCard('Runs');

  // ================================================================================= actions
  function powerOn() {
    if (st.on || S.hand.busy) return Promise.resolve();
    return S.hand.tap(pwr).then(function () {
      st.on = true; led.material.color.setHex(0x49d36a); tled.material.color.setHex(0x49d36a);
      S.say('Workstation on. Choose the method and the step setting, then press Enter.');
      S.render(); drawScreen();
    });
  }
  function runOnce(quiet) {
    if (!st.on) { S.say('Switch the workstation on first.'); return Promise.resolve(); }
    if (S.hand.busy) return Promise.resolve();
    return S.hand.tap(enter).then(function () {
      var v = compute(st.ni, st.mi);
      st.last = v; st.reveal = S.fast ? 1 : 0;
      var row = { n: NS[st.ni], mi: st.mi, val: v.val, exact: v.exact, err: v.err, nused: v.nused };
      var same = -1;
      S.rows.forEach(function (r, i) { if (r.n === row.n && r.mi === row.mi) same = i; });
      if (same >= 0) S.rows.splice(same, 1);
      S.addRow(row);
      if (!quiet) S.say(METHODS[st.mi] + ' at ' + SP.nlabel + ' = ' + row.n + ':  ' + SP.quantity + ' = ' + sci(row.val)
        + ',  error ' + row.err.toExponential(2) + '.');
      drawScreen(); S.render();
    });
  }
  function setN(i) { st.ni = Math.max(0, Math.min(NS.length - 1, i)); drawScreen(); S.render(); }
  function setMethod(i) {
    st.mi = Math.max(0, Math.min(METHODS.length - 1, i));
    st.last = null; preview = compute(st.ni, st.mi);
    drawScreen(); S.render();
  }
  function distinctN() { var seen = {}, k = 0; S.rows.forEach(function (r) { if (!seen[r.n]) { seen[r.n] = 1; k++; } }); return k; }
  function orderOf() {
    var C = HK.CALCS.cp_order;
    return C ? C.fn(S.rows, p) : 0;
  }
  function best() {
    var b = null;
    S.rows.forEach(function (r) { if (!b || r.n > b.n) b = r; });
    return b;
  }
  drawScreen();

  return {
    camera: { pos: [0.72, 0.68, 1.08], look: [0.12, 0.12, -0.3] },
    views: {
      mon: [[0.16, 0.30, 0.16], [0.15, 0.25, -0.42]],
      screen: [[0.15, 0.28, 0.14], [0.15, 0.25, -0.42]],
      kbd: [[0.17, 0.33, 0.2], [0.16, 0.0, -0.09]],
      mouse: [[0.46, 0.22, 0.1], [0.44, 0.0, -0.1]],
      tower: [[0.78, 0.42, 0.22], [0.66, 0.18, -0.46]],
      card: [[-0.13, 0.54, 0.44], [-0.13, 0.0, 0.03]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]],
      bench: [[0.72, 0.68, 1.08], [0.12, 0.12, -0.3]],
    },
    theory: {
      principle: 'A numerical method answers a question the algebra cannot, but it answers it only to the accuracy '
        + 'of its step size. The practical is therefore a measurement: run the method at several step sizes or '
        + 'sample counts, compare each answer with the exact value, and see how the error falls. That fall is the '
        + 'order of the method, and it is as much a property of the method as a focal length is of a lens.',
      formula: SP.title, formulaNote: SP.formula,
      more: ['The exact answer for this problem is known in closed form, so every run has a real error, not a guess.',
        'Keep the method fixed while you change n, and change only one thing at a time - the same discipline as any '
        + 'other practical.'],
      precautions: 'Read the method card before switching on. Record the method, n, the answer and the error of '
        + 'every run before you change a setting. Never report a digit the error does not support, and remember that '
        + 'below some step size round-off makes the answer worse, not better.',
    },
    book: {
      title: 'Expt. — ' + S.lab.title,
      lines: ['Aim: ' + S.lab.aim, 'Problem: ' + SP.title, 'Exact value = ' + sci(ex0),
        'Method: ' + METHODS[M0] + ' (and the others for comparison)', 'For each run: ' + SP.nlabel + ', answer, error.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'Method', get: function (r) { return METHODS[r.mi].split(' ')[0]; } },
        { label: SP.nlabel.indexOf('h') === 0 ? 'n' : SP.nlabel, get: function (r) { return String(r.n); } },
        { label: 'Answer', get: function (r) { return sci(r.val); } },
        { label: 'Rel. error', get: function (r) { return r.err.toExponential(2); } }],
    },
    graph: {
      x: function (r) { return r.n; }, y: function (r) { return r.val; },
      xlabel: SP.nlabel, ylabel: SP.quantity, x0: 0,
      line: function () { return function () { return ex0; }; },
    },
    result: function (rows) {
      var b = null;
      rows.forEach(function (r) { if (!b || r.n > b.n) b = r; });
      if (!b) return null;
      return { label: SP.quantity, value: b.val, unit: SP.unit, digits: SP.digits, truth: b.exact,
        note: METHODS[b.mi] + ' at ' + SP.nlabel + ' = ' + b.n + '; relative error ' + b.err.toExponential(2)
          + (S.rows.length >= 3 ? '. Order measured from log(error) vs log(n): ' + fmt(orderOf(), 2) : '') };
    },
    tol: SP.tol,
    chips: ['Why does the error fall with n?', 'Which method is best here?', 'Check my runs',
      'Why does a smaller step sometimes make it worse?', 'Explain the order of a method'],
    viva: [['What exactly is being measured in a computational practical?',
      ['The error of a method at a known step size', 'The speed of the computer', 'The value of a constant'], 0,
      'The answer is known in closed form; what the run tells you is the error of the method.'],
      ['The error of a method falls as n^-4. The method is',
        ['fourth order', 'fourth degree', 'exact'], 0, 'Order p means the error goes as h^p, that is n^-p.'],
      ['Why is one run never enough?', ['One run gives no idea of its own error', 'One run is slow',
        'One run uses the wrong method'], 0,
        'Only by changing the step and watching the answer move can you say how accurate it is.']],
    askState: function () {
      var b = best();
      return { problem: SP.title, kernel: KNAME, method: METHODS[st.mi], workstation_on: st.on,
        setting_n: NS[st.ni], exact_value: ex0, runs_recorded: S.rows.length,
        last_numerical_answer: st.last ? st.last.val : null, last_relative_error: st.last ? st.last.err : null,
        best_run: b ? { n: b.n, value: b.val, error: b.err } : null,
        measured_order: S.rows.length >= 3 ? orderOf() : null };
    },

    steps: [
      { id: 'card', title: 'The problem', view: 'card',
        render: function (u) {
          u.h2('Read the method card');
          u.p('Every computational practical starts on paper: what is being solved, which methods are allowed, and '
            + 'what the exact answer is, so that the error of each run can be measured.');
          u.formula(SP.title, SP.formula);
          cardLines.forEach(function (t) { u.p(t); });
          u.h3('Methods on this bench');
          METHODS.forEach(function (m2, i) { u.note((i + 1) + '. ' + m2); });
          u.task('Switch the workstation on', st.on, st.on ? 'The screen is live' : 'Press the power button under the screen')
            .add(u.button(st.on ? 'On' : 'Switch on', function () { powerOn(); }, !st.on, st.on || S.hand.busy));
          u.next('Next: run the method', st.on);
        },
        ok: function () { return st.on; },
        auto: function () { return powerOn(); } },

      { id: 'runs', title: 'Runs', view: 'screen',
        render: function (u) {
          u.h2('Run the method at several settings');
          u.p('Choose the method and the ' + SP.nlabel + ', then press Enter. The screen draws the exact curve, what '
            + 'the method built and the nodes it used; the run log keeps every answer with its error.');
          if (METHODS.length > 1) {
            var r = u.row();
            r.appendChild(document.createTextNode('Method: '));
            METHODS.forEach(function (m2, i) {
              r.appendChild(u.button((st.mi === i ? '✓ ' : '') + m2, function () { setMethod(i); }, false, S.hand.busy));
            });
          }
          u.slider(SP.nlabel, 0, NS.length - 1, 1, function () { return st.ni; },
            function (v) { setN(Math.round(v)); }, '', 0);
          u.note(SP.nlabel + ' = ' + NS[st.ni] + (KNAME === 'cp_diff' ? '  (h = ' + sci(p.h0 / NS[st.ni]) + ')' : ''));
          u.row(u.button('Run — press Enter', function () { runOnce(); }, true, !st.on || S.hand.busy),
            u.button('Run every setting', function () { autoSweep(); }, false, !st.on || S.hand.busy));
          u.live(function () {
            return st.last ? SP.quantity + ' = ' + sci(st.last.val) + '  ·  exact ' + sci(st.last.exact)
              + '  ·  error ' + st.last.err.toExponential(2) : 'No run yet. Press Enter.';
          });
          u.h3('Observation table'); u.table();
          var k = distinctN();
          u.next('Next: how the error falls', S.rows.length >= 4 && k >= 3);
          if (S.rows.length < 4 || k < 3) u.p(S.rows.length + ' run(s) kept at ' + k + ' different settings. '
            + 'Take at least 4 runs at 3 or more settings of ' + SP.nlabel + '.');
        },
        ok: function () { return S.rows.length >= 4 && distinctN() >= 3; },
        auto: function () { return autoSweep(); } },

      { id: 'order', title: 'Error and order', view: 'screen',
        render: function (u) {
          var b = best();
          u.h2('How the error falls');
          u.p('A straight line through the points (log n, log error) has a slope of minus the order of the method. '
            + 'That slope is the result of this practical as much as the answer itself.');
          u.formula('error ≈ C n^(−p)', 'so  log(error) = log C − p log n');
          u.live(function () {
            var o = orderOf();
            return 'Measured order p = ' + fmt(o, 2) + '  (from ' + S.rows.length + ' runs)';
          });
          if (b) u.note('Finest run: ' + METHODS[b.mi] + ' at ' + SP.nlabel + ' = ' + b.n + ' gives '
            + SP.quantity + ' = ' + sci(b.val) + ', error ' + b.err.toExponential(2) + '.');
          u.h3('All runs'); u.table();
          u.p('If the measured order is far below the one the formula promises, the step has gone small enough for '
            + 'round-off to matter, or the run log is mixing two different methods.');
          u.next('Next: the result', S.rows.length >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () { return Promise.resolve(); } },
    ],

    tick: function (dt) {
      if (st.reveal < 1) st.reveal = Math.min(1, st.reveal + dt * 1.6);
      if (st.reveal < 1) drawScreen();
      glow.intensity = st.on ? 0.5 : 0;
      var v = st.last;
      hudV.set(v ? sci(v.val) : '—'); hudE.set(sci(ex0));
      hudErr.set(v ? v.err.toExponential(1) : '—'); hudN.set(String(S.rows.length));
    },
  };

  // the sweep every step's `auto` uses: the same runOnce the Enter key calls, at every setting in turn
  function autoSweep() {
    var pr = powerOn();
    NS.forEach(function (_, i) {
      pr = pr.then(function () { setN(i); return runOnce(true); });
    });
    return pr.then(function () { S.say('Swept every setting of ' + SP.nlabel + '. Look at how the error falls.'); S.render(); });
  }
});

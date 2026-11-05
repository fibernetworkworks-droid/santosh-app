/* Prayogshala studio RIG: the computational physics WORKSTATION for the M.Sc. / Ph.D. practicals (comp3_adv kernel pack).
   Same bench as comp-workstation, with a lattice / phase-space / orbit / band-structure / histogram view in the corner of the screen.
   The bench below was written for the B.Sc. "Computational physics" practicals:
   One bench serves every method in the comp_ug kernel pack: desk mat, monitor, keyboard with a live Enter key,
   mouse, tower and the printed METHOD CARD. The student reads the card, switches the machine on, chooses the
   method and the step size / sample count, presses Enter - and the MONITOR DRAWS the computation: the exact curve,
   what the method built, and the nodes it actually used, with the run log beside it.
   Every number comes from the lab's kernel (HoolaKernels.K[lab.kernel]) at the student's settings - the same code
   the server checks - so the error printed on the screen is the real error of that method at that step size. */
HoolaStudio.define('comp3-workstation', function (S) {
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
  function fmt(v, d) {
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
  var W = Math.round(p.what === undefined ? 0 : p.what);
  var ex0 = (function () {
    try { return HK.TEXTBOOK[S.lab.check.textbook](p); } catch (e) { return K.measure(p).exact; }
  })();
  var STAT = 'A Monte Carlo error falls only as N⁻¹ᐟ²: four times the samples halve the error.';
  var SPECS = {
    cr_interp: function () {
      var fn = ['sin x', '1/(1 + 25x²)  (Runge)'][CAS] || 'f(x)';
      return {
        title: 'Interpolating f(x) = ' + fn, quantity: 'f(' + fx(p.x, 3) + ')', digits: 8, nlabel: 'intervals n',
        ns: CAS === 1 ? [4, 8, 12, 16, 24] : [4, 6, 8, 10, 12], tol: 0.02, showCurve: true,
        methods: ['Lagrange polynomial', 'Cubic spline (clamped)'], xlabel: 'x', ylabel: 'f(x)',
        problem: ['f(x) = ' + fn + ' on [' + fx(p.xa, 3) + ', ' + fx(p.xb, 3) + ']', 'Estimate f at x = ' + fx(p.x, 4),
          'Lagrange: one polynomial of degree n through n + 1 equally spaced nodes',
          'Spline: n cubic pieces with continuous f, f′ and f″; end slopes taken from f′',
          'Exact:  f(x) = ' + sci(ex0)],
        formula: 'Lagrange Σ f(xᵢ) Πⱼ≠ᵢ (x−xⱼ)/(xᵢ−xⱼ) · spline: f″ from a tridiagonal system',
        expect: 'A spline improves as n⁻⁴. One high-degree polynomial through equally spaced nodes can get WORSE as n grows near the ends (Runge).',
        viva: [['Why does the Lagrange polynomial through equally spaced nodes fail for 1/(1+25x²)?',
          ['The high-degree polynomial oscillates near the ends', 'The function is not smooth', 'The nodes are too few'], 0,
          'Equally spaced nodes give a large error factor Π(x−xᵢ) near the ends; the cubic spline never builds a high-degree polynomial.']]
      };
    },
    cr_pde: function () {
      var heat = CAS === 0;
      return {
        title: heat ? 'Heat equation  u_t = c u_xx' : 'Wave equation  u_tt = c² u_xx', quantity: 'u(' + fx(p.xp, 2) + ', ' + fx(p.tend, 2) + ')',
        digits: 6, nlabel: 'grid intervals n', ns: [10, 20, 40, 80, 160], tol: 0.03, showCurve: true,
        methods: heat ? ['Explicit (FTCS)', 'Implicit (Crank-Nicolson)'] : ['Explicit (leapfrog)', 'Implicit (Newmark β = ¼)'],
        xlabel: 'x', ylabel: 'u',
        problem: [heat ? 'Rod on (0, 1), ends held at 0, a triangular start, diffusivity c = ' + fx(p.c, 3) : 'String on (0, 1), fixed ends, plucked at the middle, wave speed c = ' + fx(p.c, 3),
          'Run to t = ' + fx(p.tend, 3) + '; read u at x = ' + fx(p.xp, 2),
          heat ? 'Stability number r = cΔt/Δx² = ' + fx(p.r, 3) + '  (explicit needs r ≤ ½)' : 'Courant number ν = cΔt/Δx = ' + fx(p.r, 3) + '  (explicit needs ν ≤ 1)',
          'Exact: ' + (heat ? 'a Fourier series' : 'd’Alembert’s travelling triangles') + ' = ' + sci(ex0)],
        formula: heat ? 'explicit uⱼ′ = uⱼ + r δ²uⱼ · Crank-Nicolson: tridiagonal solve each step' : 'leapfrog uⁿ⁺¹ = 2uⁿ − uⁿ⁻¹ + ν² δ²uⁿ · implicit average of three levels',
        expect: 'Second order in space: error ∝ n⁻² (the time step is tied to the grid). Make the stability number too large and the explicit method blows up.',
        viva: [['What happens to an explicit scheme when the stability number is too large?',
          ['Rounding errors grow without bound', 'It only becomes less accurate', 'Nothing, it just runs slower'], 0,
          'Each step multiplies the highest mode by a factor above one in size; the implicit scheme has no such limit.']]
      };
    },
    cr_fem: function () {
      return {
        title: ['−u″ = π² sin(πx)', '−u″ = 1'][CAS], quantity: 'u(' + fx(p.xp, 2) + ')', digits: 8, nlabel: 'elements n',
        ns: [2, 4, 8, 16, 32], tol: 0.03, showCurve: true, methods: ['Linear elements (Galerkin)'], xlabel: 'x', ylabel: 'u',
        problem: ['Solve  −u″ = f  on (0, 1)  with  u(0) = u(1) = 0', 'f = ' + (CAS === 1 ? '1' : 'π² sin(πx)') + ';  n equal elements, hat functions',
          'Load vector by 2-point Gauss quadrature; stiffness (2/h, −1/h) solved by the Thomas algorithm',
          'Read u at x = ' + fx(p.xp, 2) + ' by linear interpolation of the mesh solution', 'Exact:  ' + (CAS === 1 ? 'x(1−x)/2' : 'sin(πx)') + ' = ' + sci(ex0)],
        formula: 'K u = b,  Kᵢᵢ = 2/h, Kᵢᵢ₊₁ = −1/h,  bᵢ = ∫ f φᵢ dx',
        expect: 'Linear elements are second order: the error falls as n⁻². For f = 1 the nodal values are exact; only the interpolation between nodes is not.',
        viva: [['How does the error of linear finite elements change when the mesh is halved?',
          ['It falls by about four', 'It falls by two', 'It does not change'], 0, 'The interpolation error of piecewise-linear functions is O(h²).']]
      };
    },
    cr_fit: function () {
      var meth = ['Unweighted least squares', 'Weighted least squares (1/σ²)'];
      return {
        title: ['Straight-line fit, equal errors', 'Straight-line fit, unequal errors', 'Parabola by general linear least squares'][CAS],
        quantity: CAS === 2 ? 'curvature c' : 'slope a', digits: 5, nlabel: 'data points N', ns: [10, 30, 100, 300, 1000, 4000], tol: 0.03,
        showCurve: true, methods: meth, xlabel: 'x', ylabel: 'y', dots: true,
        problem: [['y = a x + b', 'y = a x + b, but σ grows along x', 'y = b + a x + c x²'][CAS] + ',  true a = ' + fx(p.a, 3) + ', b = ' + fx(p.b, 3) + (CAS === 2 ? ', c = ' + fx(p.c, 3) : ''),
          'N points on 0 ≤ x ≤ ' + fx(p.xmax, 2) + ', Gaussian noise σ = ' + fx(p.sig, 3) + (CAS === 1 ? ' × (0.25 … 1.75)' : ''),
          'Seed ' + fx(p.seed, 0) + ': the run repeats exactly', 'Normal equations (AᵀWA) β = AᵀW y solved by elimination',
          'The unknown is the ' + (CAS === 2 ? 'curvature' : 'slope') + ' the data were made with: ' + sci(ex0)],
        formula: 'β = (AᵀWA)⁻¹ AᵀW y,  cov = (AᵀWA)⁻¹,  χ² = Σ ((y − fit)/σ)²',
        expect: 'The error of a fitted parameter falls as N⁻¹ᐟ². With unequal errors the weighted fit does better than the unweighted one.',
        extras: function (v) { return 'χ²/dof = ' + fx(v.chi2r, 3) + '   σ(param) = ' + sci(v.perr); },
        viva: [['Why weight each point by 1/σ²?', ['Precise points should count for more', 'To make the line steeper', 'To remove the noise'], 0,
          'The weights come from the likelihood of Gaussian data: a point known to ±σ contributes (1/σ²) to χ².']]
      };
    },
    cr_mle: function () {
      return {
        title: ['Poisson counts: mean λ', 'Gaussian data: width σ', 'Exponential times: lifetime τ'][CAS],
        quantity: ['λ̂', 'σ̂', 'τ̂'][CAS], digits: 5, nlabel: 'samples N', ns: [100, 300, 1000, 10000, 100000, 400000], tol: 0.03,
        methods: ['Maximise ln L (golden section)'], xlabel: ['counts k', 'x', 'time'][CAS], ylabel: 'events per bin', bars: true, nodes: true,
        problem: [['N counts drawn from a Poisson law of mean λ = ' + fx(p.lam, 3), 'N values from a Gaussian of mean ' + fx(p.mu, 2) + ' and width σ = ' + fx(p.sg, 3), 'N waiting times from an exponential of mean τ = ' + fx(p.tau, 3)][CAS],
          'The estimate is found by maximising ln L numerically, not by quoting a formula',
          'Pearson χ² of the fitted model against the histogram: expect χ²/dof near 1', 'Seed ' + fx(p.seed, 0), 'True value: ' + sci(ex0)],
        formula: 'ln L(θ) = Σ ln f(xᵢ; θ) · golden-section search for the maximum · χ² = Σ (O − E)²/E',
        expect: STAT + ' The maximum-likelihood estimate is consistent and, for large N, its error is the Cramér-Rao bound.',
        extras: function (v) { return 'χ²/dof = ' + fx(v.chi2r, 3) + '  (dof ' + fx(v.dof, 0) + ')'; },
        viva: [['A correct model fitted to enough data should give χ²/dof of about', ['1', '0', '10'], 0, 'Each bin deviates by about its own standard deviation, so χ² ≈ the number of degrees of freedom.']]
      };
    },
    cr_dev: function () {
      return {
        title: ['Exponential deviates', 'Gaussian deviates', 'Binomial (5, 0.3) deviates'][CAS],
        quantity: ['P(x < ' + fx(p.xb, 2) + ')', 'P(|x| < ' + fx(p.xb, 2) + ')', 'P(k = ' + fx(p.kb, 0) + ')'][CAS], digits: 6,
        nlabel: 'samples N', ns: [1000, 4000, 16000, 64000, 200000], tol: 0.03, methods: ['Inverse transform', 'Acceptance-rejection'],
        xlabel: ['x', 'x', 'k'][CAS], ylabel: 'samples per bin', bars: true,
        problem: [['Target density  f(x) = λ e^(−λx),  λ = ' + fx(p.lam, 3), 'Target density  f(x) = e^(−x²/2)/√(2π)', 'Target pmf  C(5,k) 0.3^k 0.7^(5−k)'][CAS],
          'Inverse transform: x = F⁻¹(u)' + (CAS === 1 ? ' from a tabulated normal CDF' : ''),
          'Acceptance-rejection: x uniform in a box, keep it if a second u lies under f(x)', 'Seed ' + fx(p.seed, 0),
          'Exact probability of the interval:  ' + sci(ex0)],
        formula: 'F(x) = u ⇒ x = F⁻¹(u) · accept if u₂ f_max < f(x) · efficiency = area under f / box area',
        expect: STAT,
        extras: function (v) { return 'χ²/dof = ' + fx(v.chi2r, 2) + '   trials per sample = ' + fx(1 / Math.max(v.eff, 1e-9), 2); },
        viva: [['What is the price of acceptance-rejection?', ['Rejected trials, so more random numbers per sample', 'A biased answer', 'Nothing'], 0,
          'It needs 1/efficiency trials per accepted number; the inverse transform needs exactly one.']]
      };
    },
    cr_walk: function () {
      var d = Math.round(p.dim), N = Math.round(p.steps);
      return {
        title: 'Random walk on a ' + d + '-D lattice', quantity: CAS === 1 ? 'P(at origin after ' + N + ' steps)' : '⟨R²⟩ after ' + N + ' steps', digits: 5,
        nlabel: 'walkers W', ns: [500, 2000, 8000, 32000, 128000], tol: 0.04, methods: ['Unit-step lattice walk'],
        xlabel: 'step m', ylabel: '⟨R²⟩', showCurve: true, inset: 'path', nodes: false,
        problem: ['Each walker takes ' + N + ' unit steps, each along ± one of the ' + d + ' axes', 'W walkers, seed ' + fx(p.seed, 0),
          CAS === 1 ? 'Count the walkers back at the origin; exact value is a lattice sum' : 'Average R² over the walkers at every step',
          'Exact: ' + (CAS === 1 ? 'P = ' : '⟨R²⟩ = N = ') + sci(ex0)],
        formula: '⟨R²(N)⟩ = N a² for unit steps, any dimension · P₀(2m) = C(2m, m)²/16ᵐ in 2-D',
        expect: STAT + ' (the walk itself is shown in the corner).',
        viva: [['How does the mean square displacement of a random walk grow?', ['Linearly with the number of steps', 'As the square of the steps', 'It stays constant'], 0, 'Each step is independent, so the squared lengths add: ⟨R²⟩ = N a².']]
      };
    },
    cr_decay: function () {
      return {
        title: ['Monte Carlo decay of one nuclide', 'Parent-daughter decay chain', 'Transient equilibrium'][CAS],
        quantity: ['surviving fraction N/N₀', 'daughter fraction N_B/N₀', 'ratio N_B/N_A'][CAS], digits: 6, nlabel: 'nuclei N₀',
        ns: [1000, 4000, 16000, 64000, 256000], tol: 0.03, methods: ['Sampled decay times'], xlabel: 'time', ylabel: CAS === 2 ? 'N_B / N_A' : 'fraction',
        showCurve: true, nodes: true,
        problem: ['Every nucleus gets a decay time t = −ln(u)/λ' + (CAS > 0 ? ' and its daughter another one' : ''), 'λ₁ = ' + fx(p.l1, 4) + (CAS > 0 ? ',  λ₂ = ' + fx(p.l2, 4) : '') + ' per unit time',
          'Counted at t = ' + fx(p.tend, 3), 'Exact (Bateman): ' + sci(ex0), 'Seed ' + fx(p.seed, 0)],
        formula: 'N_A = N₀ e^(−λ₁t) · N_B = N₀ λ₁/(λ₂ − λ₁) (e^(−λ₁t) − e^(−λ₂t))',
        expect: STAT, viva: [['In transient equilibrium the ratio N_B/N_A tends to', ['λ₁/(λ₂ − λ₁)', '1', 'λ₂/λ₁'], 0, 'When the parent decays more slowly the daughter settles at a fixed fraction of it.']]
      };
    },
    cr_twolevel: function () {
      return {
        title: ['Magnetisation of N two-level spins', 'Specific heat of N two-level spins'][CAS], quantity: ['⟨m⟩', 'c / k per spin'][CAS], digits: 6,
        nlabel: 'sweeps', ns: [200, 1000, 4000, 16000], tol: 0.03, methods: ['Metropolis'], xlabel: 'x = μB/kT', ylabel: ['⟨m⟩', 'c/k'][CAS], inset: 'lattice', nodes: true,
        problem: [fx(p.ns, 0) + ' independent spins, each with energy ∓μB; x = μB/kT = ' + fx(p.x, 3),
          'Metropolis: flip with probability min(1, e^(−ΔE/kT)); every sweep tries each spin once',
          CAS === 1 ? 'c is taken from the energy fluctuation: c = (⟨e²⟩ − ⟨e⟩²)/(kT)²' : 'm is the mean of the spins', 'Exact:  ' + (CAS === 1 ? 'x² sech² x' : 'tanh x') + ' = ' + sci(ex0), 'Seed ' + fx(p.seed, 0)],
        formula: '⟨m⟩ = tanh x · c/k = x² sech² x (Schottky anomaly)',
        expect: STAT, viva: [['The specific heat of a two-level system', ['rises, peaks and falls again with temperature', 'rises for ever', 'is constant'], 0, 'At high T both levels are equally filled; at low T the upper one is frozen out; the peak is between.']]
      };
    },
    cr_mcint: function () {
      return {
        title: CAS === 1 ? '∫₀¹ e^(−x²) dx' : '∫₀^π sin x dx', quantity: 'integral I', digits: 6, nlabel: 'samples N', ns: [1000, 4000, 16000, 64000, 256000], tol: 0.03,
        methods: ['Hit or miss', 'Sample mean', 'Importance sampling'], xlabel: 'N (samples, log scale)', ylabel: 'running estimate', showCurve: true, logx: true, yFrom: 0.3,
        problem: ['Estimate  I = ∫ f(x) dx  with f = ' + (CAS === 1 ? 'e^(−x²) on [0, 1]' : 'sin x on [0, π]'),
          'Hit or miss: points in a box under the curve · Sample mean: (b − a) ⟨f⟩',
          'Importance sampling: draw x from ' + (CAS === 1 ? 'e^(−x)/(1 − e⁻¹)' : 'a triangle peaked at π/2') + ' and average f/p', 'Seed ' + fx(p.seed, 0), 'Exact:  ' + sci(ex0)],
        formula: 'I ≈ (b−a)⟨f⟩ ± (b−a)σ_f/√N · importance: I ≈ ⟨f/p⟩ with x ~ p',
        expect: STAT + ' Importance sampling lowers the constant, not the exponent.',
        extras: function (v) { return 'standard error = ' + sci(v.se); },
        viva: [['Why does importance sampling reduce the error?', ['f/p varies less than f', 'It uses more samples', 'It removes the 1/√N'], 0, 'The error is σ/√N and σ is the spread of what you average, f/p.']]
      };
    },
    cr_scatter: function () {
      var hs = CAS === 0;
      return {
        title: hs ? 'Hard-sphere scattering' : 'Rutherford scattering', quantity: hs ? (W === 0 ? 'total cross-section σ' : 'backward fraction') : 'σ(θ > ' + fx(p.thmin * 180 / Math.PI, 0) + '°)',
        digits: 5, nlabel: 'projectiles N', ns: [2000, 8000, 32000, 128000, 256000], tol: 0.03, methods: ['Random impact parameters'], xlabel: 'cos θ', ylabel: 'projectiles per bin', bars: true,
        problem: [hs ? 'Hard sphere of radius a = ' + fx(p.a, 3) : 'Coulomb field with closest approach d = ' + fx(p.a, 3), 'Beam disc of radius R = ' + fx(p.R, 3) + '; impact parameter b = R√u',
          hs ? 'cos θ = 2b²/a² − 1 if b < a' : 'tan(θ/2) = d/2b', hs ? 'Exact: σ = πa² and dσ/dΩ = a²/4 (isotropic)' : 'Exact: σ(θ > θ₀) = π (d/2)² cot²(θ₀/2)', 'Exact value of the quantity:  ' + sci(ex0), 'Seed ' + fx(p.seed, 0)],
        formula: hs ? 'σ = π a²,  half the scattered projectiles go backward' : 'dσ/dΩ = (d/4)² / sin⁴(θ/2)',
        expect: STAT, viva: [['A hard sphere scatters isotropically in the centre-of-mass frame, so cos θ is', ['uniform from −1 to 1', 'peaked forward', 'peaked backward'], 0, 'Because b² is uniform and cos θ = 2b²/a² − 1 is linear in it.']]
      };
    },
    cr_poly: function () {
      var f = ['x³ − 6x² + 11x − 6 = 0', 'x³ − 2x − 5 = 0', 'x³ − 3x + 2 = 0  (double root)'][CAS];
      return {
        title: f, quantity: 'root x', digits: 10, nlabel: 'iterations', ns: [3, 5, 8, 12, 20, 30], tol: 0.001, zero: true,
        methods: CAS === 2 ? ['Newton-Raphson', 'Modified Newton (multiplicity 2)', 'Secant'] : ['Bisection', 'Newton-Raphson', 'Secant'], xlabel: 'x', ylabel: 'p(x)',
        problem: ['Solve  ' + f, CAS === 0 ? 'The root near 3 (roots 1, 2, 3)' : CAS === 1 ? 'The only real root (Wallis’s classic cubic), by Cardano: ' + sci(ex0) : 'Roots 1 (double) and −2; look for x = 1',
          'Start: x₀ = ' + fx(p.x0, 3) + (CAS === 2 ? ', secant x₁ = ' + fx(p.x1, 3) : ', secant x₁ = ' + fx(p.x1, 3) + ', bracket [' + fx(p.xa, 3) + ', ' + fx(p.xb, 3) + ']'), 'Exact root = ' + sci(ex0)],
        formula: 'bisect: halve the bracket · Newton x − p/p′ · secant: chord · modified Newton x − m p/p′',
        expect: 'Bisection gains one bit per step; Newton squares the error; at a double root plain Newton falls back to a factor of 2 per step.',
        viva: [['Why is Newton-Raphson slow at a double root?', ['p′ also vanishes there, so the convergence is only linear', 'p is not a polynomial', 'The bracket is wrong'], 0, 'With multiplicity m the error shrinks by (m−1)/m per step; multiplying the step by m restores quadratic convergence.']]
      };
    },
    cr_photon: function () {
      return {
        title: 'Photons through a slab', quantity: ['unscattered transmission', 'scattered share of first collisions', 'mean depth of first interaction'][CAS], digits: 5,
        nlabel: 'photons N', ns: [1000, 4000, 16000, 64000, 100000], tol: 0.03, methods: ['Free-flight sampling'], xlabel: 'depth z', ylabel: 'photons per bin', bars: true, line2: true,
        problem: ['Slab thickness d = ' + fx(p.d, 3) + ', μs = ' + fx(p.mus, 3) + ', μa = ' + fx(p.mua, 3) + ' per unit length (illustrative medium)',
          'Free flight s = −ln(u)/μt; at each collision the photon is absorbed with probability μa/μt, else scattered isotropically',
          'Bars: where photons first interact. Line: where they are finally absorbed (multiple scattering)',
          'Exact (Beer-Lambert and first-collision statistics): ' + sci(ex0), 'Seed ' + fx(p.seed, 0)],
        formula: 'unscattered fraction e^(−μt d) · first-collision density μt e^(−μt z) · R + T + A = 1',
        expect: STAT,
        extras: function (v) { return 'T ' + fx(v.Tf, 4) + '  R ' + fx(v.Rf, 4) + '  A ' + fx(v.Af, 4) + '  sum ' + fx(v.Tf + v.Rf + v.Af, 4); },
        viva: [['What does R + T + A = 1 tell you about the code?', ['Every photon was accounted for exactly once', 'The medium is lossless', 'The slab is thin'], 0, 'A photon leaves backward, forward, or is absorbed; a sum that is not 1 means photons were lost or counted twice.']]
      };
    },
    cr_ising: function () {
      var d = Math.round(p.dim);
      return {
        title: d === 1 ? '1-D Ising chain' : '2-D Ising model', quantity: ['⟨|m|⟩', 'energy per spin e', 'specific heat C/N'][W] + ' at T = ' + fx(p.T, 3), digits: 5, nlabel: 'sweeps',
        ns: [100, 200, 500, 1000, 2000], tol: 0.03, methods: ['Metropolis', 'Wolff cluster'], xlabel: 'sweeps (log scale)', ylabel: 'running estimate', showCurve: true, logx: true, yFrom: 0.3, inset: 'lattice',
        problem: [d + '-D lattice, ' + fx(p.L, 0) + (d === 1 ? ' sites' : ' × ' + fx(p.L, 0) + ' sites') + ', periodic, J = kB = 1, T = ' + fx(p.T, 3),
          'Metropolis: random site, flip with probability min(1, e^(−ΔE/T)) · Wolff: grow a cluster with p = 1 − e^(−2/T)',
          d === 1 ? 'Exact (transfer matrix, this L): ' + sci(ex0) : 'Exact (Onsager, infinite lattice): ' + sci(ex0), d === 2 ? 'Onsager: Tc = 2/ln(1+√2) = 2.2692; ⟨|m|⟩ = (1 − sinh⁻⁴(2/T))^(1/8)' : 'No order at any T > 0 in one dimension',
          'Seed ' + fx(p.seed, 0)],
        formula: 'E = −J Σ sᵢsⱼ · accept min(1, e^(−ΔE/T)) · Wolff: add aligned neighbours with p = 1 − e^(−2J/T)',
        expect: STAT + ' The finite lattice differs a little from Onsager’s infinite one.',
        viva: [['Why does the Wolff cluster update help near Tc?', ['It flips whole correlated clusters, so it decorrelates quickly', 'It lowers the temperature', 'It needs no random numbers'], 0, 'Single-spin updates slow down critically near Tc; flipping a cluster moves the system across its correlation length at once.']]
      };
    },
    cr_binder: function () {
      return {
        title: '2-D Ising: critical temperature from the Binder cumulant', quantity: 'crossing temperature Tc', digits: 5, nlabel: 'sweeps per point', ns: [100, 200, 400, 800], tol: 0.04,
        methods: ['Metropolis', 'Wolff cluster'], xlabel: 'T (J/kB)', ylabel: 'U₄ = 1 − ⟨m⁴⟩/3⟨m²⟩²', showCurve: true, line2: true, inset: 'lattice', nodes: true, vline: true,
        problem: ['Lattices L = ' + fx(p.L1, 0) + ' and L = ' + fx(p.L2, 0) + ', periodic, T from ' + fx(p.Tlo, 3) + ' to ' + fx(p.Thi, 3) + ' in ' + fx(p.nT, 0) + ' steps',
          'U₄(L, T) = 1 − ⟨m⁴⟩/(3⟨m²⟩²) for both sizes; the curves cross at Tc', 'Exact (Onsager 1944): Tc = 2/ln(1 + √2) = ' + sci(ex0),
          'A finite-size crossing is a statistical estimate: expect a few per cent, not machine precision', 'Seed ' + fx(p.seed, 0)],
        formula: 'U₄ → 2/3 (ordered), 0 (disordered); the L-independent crossing marks Tc',
        expect: 'The scatter of the crossing falls roughly as N⁻¹ᐟ²; corrections to scaling shift it a little for small L. The vertical line is Onsager’s exact Tc.',
        viva: [['Why do the Binder cumulants of different sizes cross at Tc?', ['At Tc U₄ is independent of the lattice size', 'Because both are 2/3', 'Because the energy is minimal'], 0, 'Near Tc U₄ depends only on L/ξ, and at Tc ξ is infinite, so every size gives the same value.']]
      };
    },
    cr_tb: function () {
      var sam = ['1-D chain (periodic ring)', 'square lattice (periodic cluster)', 'graphene (honeycomb, Bloch Hamiltonian on a k mesh)'][CAS];
      return {
        title: 'Tight-binding bands: ' + sam, quantity: W === 1 ? 'ground-state energy per site' : 'band width', unit: 't', digits: 6, nlabel: CAS === 2 ? 'k points per side' : CAS === 1 ? 'cluster side L' : 'sites N',
        ns: CAS === 0 ? (W === 1 ? [6, 10, 14, 22, 34] : [8, 16, 24, 32]) : CAS === 1 ? (W === 1 ? [4, 6, 8, 10] : [4, 6, 8]) : [6, 12, 18, 24], tol: W === 1 ? 0.03 : 0.001, methods: ['Jacobi diagonalisation'],
        xlabel: 'E / t', ylabel: 'density of states', bars: true, inset: 'bands', nodes: false,
        problem: ['Hopping −t between nearest neighbours, t = ' + fx(p.t, 3) + ' (energy unit)', CAS === 0 ? 'Eigenvalues of the N × N ring matrix by Jacobi rotations' : CAS === 1 ? 'Eigenvalues of the L² × L² torus matrix by Jacobi rotations' : 'Diagonalise the 2 × 2 Bloch Hamiltonian (as a real 4 × 4) at every k',
          W === 1 ? 'Fill the lowest N/2 orbitals twice (half filling with spin)' : 'Band width = largest − smallest eigenvalue',
          'Exact: ' + (CAS === 0 ? 'E = −2t cos ka, width 4t, ground state −4t/π per site' : CAS === 1 ? 'E = −2t (cos kx + cos ky), width 8t, ground state −16t/π² per site' : 'E = ±t|1 + e^(ik·a₁) + e^(ik·a₂)|, width 6t, Dirac point at K'), 'Reference value: ' + sci(ex0)],
        formula: 'H = −t Σ (c†ᵢcⱼ + h.c.) · cyclic Jacobi: rotate away the largest off-diagonal elements',
        expect: W === 1 ? 'The finite ring’s ground-state energy approaches the infinite chain as N⁻² (shown here as the measured order).' : 'For even clusters every band extreme is an allowed k point, so the width is exact; the density of states fills in as the cluster grows.',
        viva: [['Why is the density of states of a 1-D chain peaked at the band edges?', ['E(k) is flat there, so many k share the same energy', 'There are more atoms there', 'The hopping is stronger'], 0, 'g(E) ∝ 1/|dE/dk|, which diverges where the band is flat (van Hove singularity).']]
      };
    },
    cr_schro: function () {
      var lev = Math.round(p.lev), ell = Math.round(p.ell);
      var meths = CAS === 0 ? ['Shooting (Numerov)', 'Split-step Fourier (imaginary time)'] : ['Shooting (Numerov)'];
      var nsB = {};
      nsB[0] = CAS === 0 ? [16, 24, 32, 48, 64] : CAS === 1 ? [8, 16, 32, 64, 128] : [200, 400, 800, 1600, 3200];
      nsB[1] = [10, 20, 40, 80, 160];
      return {
        title: ['Harmonic oscillator', 'Infinite square well', 'Hydrogen radial equation'][CAS] + ', level ' + (CAS === 2 ? 'n = ' + (lev + ell + 1) + ', l = ' + ell : lev), quantity: 'energy E', unit: CAS === 2 ? 'hartree' : '', digits: 7,
        nlabel: 'grid intervals n', ns: nsB[0], nsByMethod: nsB, tol: 0.005, methods: meths, xlabel: CAS === 2 ? 'r (bohr)' : 'x', ylabel: 'V and ψ at height E', showCurve: true, nodes: false, hlines: true,
        problem: [CAS === 0 ? 'ħ = m = ω = 1:  −ψ″/2 + x²ψ/2 = Eψ' : CAS === 1 ? 'ħ = m = 1, width 1:  −ψ″/2 = Eψ, ψ(0) = ψ(1) = 0' : 'Atomic units:  −u″/2 + [l(l+1)/2r² − 1/r] u = E u',
          'Shooting: integrate by the Numerov method; count nodes; bisect on E until the node count changes', CAS === 0 ? 'Split-step: evolve in imaginary time with FFTs, projecting out lower states' : 'Level index (nodes of ψ): ' + lev,
          'Exact:  ' + (CAS === 0 ? 'E = n + ½' : CAS === 1 ? 'E = n² π²/2' : 'E = −1/(2n²) hartree') + ' = ' + sci(ex0)],
        formula: 'Numerov u″ = −k u: (1 + h²k/12) uᵢ₊₁ = 2(1 − 5h²k/12) uᵢ − (1 + h²k/12) uᵢ₋₁',
        expect: 'Numerov is fourth order; the hydrogen u(0) = 0 start is only second order. The split-step energy converges as the evolution time grows, up to an error of order Δτ².',
        viva: [['How does the node count tell you which side of an eigenvalue you are on?', ['It jumps by one as E passes an eigenvalue', 'It never changes', 'It counts the energy levels'], 0, 'The n-th state has n nodes; a trial energy slightly above E_n gives one more.']]
      };
    },
    cr_nbody: function () {
      var kep = CAS === 0;
      return {
        title: kep ? 'Kepler orbit, eccentricity ' + fx(p.ecc, 2) : 'Star cluster: the virial theorem', quantity: kep ? 'orbital period' : 'virial ratio 2K/|W|', digits: 6, nlabel: kep ? 'steps per period' : 'time steps',
        ns: kep ? [50, 100, 200, 400, 800] : [100, 200, 400, 800, 1600], tol: kep ? 0.01 : 0.05, methods: kep ? ['Euler-Cromer', 'Velocity Verlet', 'Runge-Kutta 4'] : ['Euler-Cromer', 'Leapfrog'],
        xlabel: 't', ylabel: kep ? 'relative energy error' : '2K / |W| (running mean)', showCurve: true, line2: !kep, inset: 'orbit', nodes: false,
        problem: [kep ? 'GM = 1, semi-major axis a = 1, started at pericentre' : fx(p.ns, 0) + ' equal stars in a softened gravitational field, started in virial equilibrium',
          kep ? 'The period is the time between two pericentre passages (radial velocity − to +)' : 'Time-average 2K/|W| over ' + fx(p.tend, 1) + ' time units (W is Clausius’ virial Σ r·F)',
          kep ? 'Exact (Kepler’s third law): T = 2π √(a³/GM) = ' + sci(ex0) : 'Exact (virial theorem, long-time average): 2⟨K⟩ = −⟨W⟩, so the ratio is 1', 'Reference value: ' + sci(ex0)],
        formula: kep ? 'Verlet: v½ = v + a Δt/2, x′ = x + v½ Δt, v′ = v½ + a′ Δt/2' : '2⟨K⟩ + ⟨W⟩ = 0 for bounded motion',
        expect: kep ? 'Euler-Cromer is first order, Verlet second, RK4 fourth. The plotted energy error is the reason Verlet is the standard for long runs.' : 'A finite run only approximates the infinite-time average, so a residual of a few per cent is the physics, not a bug.',
        extras: function (v) { return kep ? 'ΔE/E at the end = ' + sci(v.dE) : ''; },
        viva: [['Why is velocity Verlet preferred to RK4 for long orbit runs?', ['It is symplectic: the energy error stays bounded', 'It is more accurate per step', 'It needs no force'], 0, 'Symplectic integrators conserve a nearby Hamiltonian, so the energy oscillates instead of drifting.']]
      };
    },
    cr_spin: function () {
      var xy = CAS === 0;
      return {
        title: xy ? '2-D XY model at low temperature' : '3-D Heisenberg model at low temperature', quantity: W === 1 ? 'helicity modulus Υ' : 'energy per spin e', digits: 5, nlabel: 'sweeps',
        ns: [200, 400, 800, 1600, 3200], tol: 0.03, methods: ['Metropolis'], xlabel: 'sweeps (log scale)', ylabel: 'running estimate', showCurve: true, logx: true, yFrom: 0.3, inset: 'lattice',
        problem: [(xy ? 'Planar rotors on an ' + fx(p.L, 0) + ' × ' + fx(p.L, 0) + ' square lattice' : 'Unit vectors on a ' + fx(p.L, 0) + '³ cubic lattice') + ', H = −J Σ sᵢ·sⱼ, J = kB = 1, T = ' + fx(p.T, 3),
          'Metropolis with a small random rotation of one spin at a time', 'At low T only spin waves matter, and spin-wave theory is exact in that limit',
          xy ? 'Exact (harmonic limit): e = −2 + (T/2)(1 − 1/N);  Υ = 1 − (T/4)(1 − 1/N)' : 'Exact (harmonic limit): e = −3 + T (1 − 1/N)', 'Reference value: ' + sci(ex0),
          'Not an exact result: the BKT temperature (≈ 0.89) or the Heisenberg Tc (≈ 1.44) — those are numerical values and are not checked here'],
        formula: 'each spin wave carries kT/2: e = e₀ + (d.o.f. per spin) T/2',
        expect: STAT + ' At higher T the anharmonic terms (order T²) pull the measured value away from the spin-wave line.',
        viva: [['How much energy does each harmonic spin-wave mode carry in thermal equilibrium?', ['kT/2', 'kT', '0'], 0, 'Equipartition: the Hamiltonian is quadratic in the small angles.']]
      };
    },
    cr_ed: function () {
      var heis = CAS === 1;
      return {
        title: heis ? 'Heisenberg spin-½ ring (Lanczos)' : 'Transverse-field Ising ring (Lanczos)', quantity: heis ? 'E₀/N extrapolated to N → ∞' : 'ground-state energy per site', digits: 8, nlabel: 'chain length N',
        ns: heis ? [6, 8, 10, 12] : [4, 6, 8, 10], tol: 0.003, methods: ['Lanczos'], xlabel: heis ? '1 / N²' : 'N', ylabel: 'E₀ / N', showCurve: true, nodes: true,
        problem: [heis ? 'H = Σ Sᵢ·Sᵢ₊₁ on a ring, in the Sz = 0 sector' : 'H = −Σ σzᵢσzᵢ₊₁ − h Σ σxᵢ with h = ' + fx(p.h, 3) + ', periodic', 'Lowest eigenvalue by the Lanczos recursion on the 2ᴺ-state space, matrix-free',
          heis ? 'Extrapolate E₀/N from N and N − 2 assuming a 1/N² correction' : 'Exact (free fermions, this N): E₀ = −Σ √(1 + h² − 2h cos k), k = (2m+1)π/N',
          heis ? 'Exact (Bethe ansatz, N → ∞): 1/4 − ln 2 = ' + sci(ex0) : 'Exact value: ' + sci(ex0)],
        formula: heis ? 'e(N) = e∞ − π²/(12N²) (conformal field theory) · two sizes give e∞' : 'Jordan-Wigner: the ring is free fermions, E₀ = −Σ ε(k)',
        expect: heis ? 'The extrapolated energy lands within about 0.05 % of the Bethe-ansatz value from sizes of only 8-12 spins.' : 'Lanczos converges in a few dozen iterations to machine precision, so this checks the code, not a method order.',
        viva: [['Why can an N = 12 chain tell you about N → ∞?', ['The leading finite-size correction is a known power of 1/N', 'Twelve spins is already infinite', 'The energy does not depend on N'], 0, 'With a known 1/N² law, two sizes remove the leading error.']]
      };
    },
    cr_mcmc: function () {
      var nm = ['spectral line', 'decay curve', 'transit light curve'][CAS];
      var par = [['amplitude A', 'centre x₀'], ['amplitude A', 'lifetime τ'], ['depth δ']][CAS];
      return {
        title: 'Bayesian fit of a ' + nm, quantity: (W === 1 ? 'posterior width of ' : 'posterior mean of ') + (CAS === 0 ? 'A' : CAS === 1 ? 'τ' : 'δ'), digits: 5, nlabel: 'chain length', ns: [500, 2000, 8000, 20000, 60000], tol: 0.05,
        methods: ['Metropolis random walk'], xlabel: 'chain steps (log scale)', ylabel: 'running estimate', showCurve: true, logx: true, yFrom: 0.3, inset: 'hist',
        problem: ['Noisy ' + nm + ' with σ = ' + fx(p.sig, 4) + ' on each of ' + (CAS === 2 ? 60 : 30) + ' points; unknowns: ' + par.join(' and '),
          'Flat priors; Metropolis steps scaled to the posterior width; first 20 % discarded', CAS === 2 ? 'Linear in δ: the posterior is exactly Gaussian, mean Σmᵢ(1−yᵢ)/Σmᵢ² and width σ/√Σmᵢ²' : 'The exact posterior is integrated on a 120 × 120 grid and marginalised',
          'Reference value (' + (W === 1 ? 'width' : 'mean') + '): ' + sci(ex0), 'Seed ' + fx(p.seed, 0)],
        formula: 'p(θ|y) ∝ exp(−χ²/2) · accept with min(1, p′/p)',
        expect: 'The chain mean converges like 1/√(effective samples); the corner histogram is the chain’s posterior against the exactly integrated one.',
        extras: function (v) { return 'acceptance ' + fx(v.accept, 3); },
        viva: [['A Metropolis acceptance rate of 99 % would mean', ['the steps are too small: the chain barely explores', 'the sampler is perfect', 'the posterior is flat'], 0, 'Tiny steps are almost always accepted but move slowly, giving strongly correlated samples.']]
      };
    },
    cr_fdtd: function () {
      var slab = CAS === 0;
      return {
        title: slab ? '1-D FDTD: transmission through a dielectric slab' : '1-D FDTD: a Bragg mirror (' + fx(p.np, 0) + ' pairs)', quantity: 'transmittance T at ω = ' + fx(p.wr, 2) + ' ω₀', digits: 6, nlabel: 'cells per wavelength n',
        ns: [20, 30, 40, 60, 80], tol: 0.02, methods: ['Yee scheme (Courant number 1)'], xlabel: 'ω / ω₀', ylabel: 'transmittance T', showCurve: true, nodes: true,
        problem: [slab ? 'Slab of index ' + fx(p.n1, 2) + ', a quarter wavelength thick at ω₀, in vacuum' : 'Layers of index ' + fx(p.n1, 2) + ' and ' + fx(p.n2, 2) + ', each a quarter wavelength thick at ω₀',
          'A Gaussian pulse is sent in; T(ω) = |E_out(ω)|² / |E_ref(ω)|² from a second run without the structure', 'Exact: the 2 × 2 characteristic-matrix product at every ω',
          'Reference value at ω = ' + fx(p.wr, 2) + ' ω₀: ' + sci(ex0)],
        formula: 'Hᵢ += Eᵢ₊₁ − Eᵢ ; Eᵢ += (Hᵢ − Hᵢ₋₁)/εᵢ  (Δt = Δz/c)',
        expect: 'The Yee scheme is second order: the error falls as n⁻² (the numerical wave speed differs a little from c, more so in glass).',
        viva: [['Why is Δt = Δz/c exact in vacuum for the 1-D Yee scheme?', ['The numerical dispersion vanishes at Courant number 1', 'Because c = 1', 'It is not exact'], 0, 'At that step a wave moves exactly one cell per step, so it is carried without dispersion.']]
      };
    },
    cr_pic: function () {
      return {
        title: CAS === 0 ? 'Particle-in-cell: cold plasma oscillation' : 'Particle-in-cell: the two-stream instability', quantity: CAS === 0 ? 'oscillation frequency ω / ωp' : 'growth rate γ / ωp', digits: 5, nlabel: 'time steps per plasma period',
        ns: [8, 12, 16, 24, 32, 48], tol: 0.02, methods: ['Cloud-in-cell, leapfrog'], xlabel: 't (1/ωp)', ylabel: CAS === 0 ? 'field amplitude / start' : 'ln |E₁|', showCurve: true, inset: 'phase', nodes: false,
        problem: [CAS === 0 ? 'Electrons displaced by a sine wave over a fixed ion background; ωp = 1' : 'Two cold beams of speed ±' + fx(p.v0, 2) + ', total ωp = 1, mode k = ' + fx(p.kk, 4),
          fx(p.np, 0) + ' particles, 32 cells, periodic; Poisson by a cumulative sum (1-D Gauss’s law)',
          CAS === 0 ? 'ω from the zero crossings of the field amplitude' : 'γ from the slope of ln|E₁| while 10⁻³ < |E₁| < 2·10⁻²',
          CAS === 0 ? 'Exact (cold plasma): ω = ωp = 1' : 'Exact (cold two-stream): (ω² − k²v²)² = ωp²(ω² + k²v²), γ = √(−ω²) = ' + sci(ex0)],
        formula: CAS === 0 ? 'ωp² = n e² / (ε₀ m)' : '(ω² − k²v₀²)² = ωp² (ω² + k²v₀²)',
        expect: 'The leapfrog frequency error is O(Δt²). The field energy in the two-stream case first grows exponentially, then saturates when particles are trapped in the wave.',
        viva: [['In a cold plasma, what restores a displaced electron layer?', ['The electric field of the charge separation', 'Gravity', 'The magnetic field'], 0, 'The displacement leaves net charge on each side; the resulting field pulls the electrons back, and inertia makes them overshoot: ω = ωp.']]
      };
    }
  };
  var SP = (SPECS[KNAME] || SPECS.cr_interp)();
  SP.nsFor = function (mi) { return (SP.nsByMethod && SP.nsByMethod[mi]) || SP.ns; };
  var METHODS = SP.methods;
  var M0 = Math.min(METHODS.length - 1, Math.max(0, Math.round(p.method === undefined ? 0 : p.method)));
  var NS = SP.nsFor(M0);
  var st = { on: false, mi: M0, ni: Math.max(0, NS.length - 3), last: null, busy: false, reveal: 0 };

  function withSet(ni, mi) {
    var q = {};
    Object.keys(p).forEach(function (k) { q[k] = p[k]; });
    q.n = SP.nsFor(mi)[ni]; q.method = mi;
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
    x.fillStyle = '#f2e9d2'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#d8ceb2'; x.fillRect(0, 0, w, 170);
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
  // the sheet itself carries the print: a backing box only fought it for depth at a grazing angle
  var cardM = new T.Mesh(new T.PlaneGeometry(0.21, 0.297), new T.MeshStandardMaterial({ map: cardTex, roughness: 0.9 }));
  cardM.rotation.x = -Math.PI / 2; cardM.position.y = 0.0022; card.add(cardM);
  S.contact(0.26, 0.35, -0.13, 0.03, 0.4);

  // ================================================================================= the screen
  function rowText(r) {
    return 'n=' + String(r.n).padStart(6, ' ') + ' ' + sci(r.val) + ' ' + r.err.toExponential(1);
  }
  function hsl(h, s, l) { return 'hsl(' + Math.round(h) + ',' + s + '%,' + l + '%)'; }
  // ---- the small picture in the corner of the screen: a lattice, phase space, an orbit, a walk, bands or a histogram
  function drawInset(x, v, bx, by, bw, bh) {
    var i, j, cw, ch, cell, ox, oy, xs2, ys2, X, Y, mn, mx, lo, hi, sx, sy, sc, n2;
    x.fillStyle = '#0a1622'; x.fillRect(bx, by, bw, bh);
    x.strokeStyle = '#1d3349'; x.lineWidth = 1; x.strokeRect(bx + 0.5, by + 0.5, bw - 1, bh - 1);
    x.fillStyle = '#6f88a3'; x.font = '500 17px "Public Sans", sans-serif'; x.textAlign = 'left';
    var label = { lattice: 'lattice (final state)', phase: 'phase space  x — v', orbit: v.trail && v.trail.length ? 'orbit' : 'stars (x, y)', path: 'one walker', bands: 'E(k)  — line exact, dots computed', hist: 'posterior: chain vs exact' }[SP.inset] || '';
    x.fillText(label, bx + 10, by + 20);
    var ix = bx + 12, iy = by + 30, iw = bw - 24, ih = bh - 42;
    if (SP.inset === 'lattice' && v.lat && v.lat.length) {
      cw = Math.round(v.lw || Math.sqrt(v.lat.length)); ch = Math.round(v.lh || Math.ceil(v.lat.length / cw));
      if (ch === 1) {                                           // a strip of spins: arrows
        cell = Math.min(iw / cw, 34); ox = ix + (iw - cell * cw) / 2; oy = iy + ih / 2 - cell / 2;
        for (i = 0; i < cw; i++) {
          x.fillStyle = v.lat[i] > 0 ? '#ff9d4d' : '#4f86d6';
          X = ox + i * cell + cell / 2;
          x.beginPath();
          if (v.lat[i] > 0) { x.moveTo(X, oy + 2); x.lineTo(X + cell * 0.32, oy + cell * 0.5); x.lineTo(X - cell * 0.32, oy + cell * 0.5); }
          else { x.moveTo(X, oy + cell - 2); x.lineTo(X + cell * 0.32, oy + cell * 0.5); x.lineTo(X - cell * 0.32, oy + cell * 0.5); }
          x.closePath(); x.fill();
          x.fillRect(X - cell * 0.09, v.lat[i] > 0 ? oy + cell * 0.5 : oy + 2, cell * 0.18, cell * 0.5 - 2);
        }
      } else {
        cell = Math.min(iw / cw, ih / ch); ox = ix + (iw - cell * cw) / 2; oy = iy + (ih - cell * ch) / 2;
        for (j = 0; j < ch; j++) for (i = 0; i < cw; i++) {
          var q = v.lat[j * cw + i];
          if (v.latkind === 0) x.fillStyle = hsl(((q + Math.PI) / (2 * Math.PI)) * 360, 70, 55);
          else if (v.latkind === 1) { var g = Math.round(110 + 110 * q); x.fillStyle = 'rgb(' + g + ',' + Math.round(140 - 40 * Math.abs(q)) + ',' + (230 - g + 40) + ')'; }
          else x.fillStyle = q > 0 ? '#ff9d4d' : '#4f86d6';
          x.fillRect(ox + i * cell, oy + j * cell, Math.ceil(cell), Math.ceil(cell));
        }
      }
    } else if (SP.inset === 'phase' && v.pts && v.pts.length) {
      var vm = v.vmax || 1.5;
      x.strokeStyle = '#1d3349'; x.beginPath(); x.moveTo(ix, iy + ih / 2); x.lineTo(ix + iw, iy + ih / 2); x.stroke();
      x.fillStyle = '#5fd0ff';
      for (i = 0; i + 1 < v.pts.length; i += 2) {
        X = ix + v.pts[i] * iw; Y = iy + ih / 2 - v.pts[i + 1] / vm * ih / 2;
        x.fillRect(X - 1.5, Y - 1.5, 3, 3);
      }
    } else if (SP.inset === 'orbit' && ((v.trail && v.trail.length) || (v.pts && v.pts.length))) {
      var pts2 = (v.trail && v.trail.length) ? v.trail : v.pts;
      lo = [1e9, 1e9]; hi = [-1e9, -1e9];
      for (i = 0; i + 1 < pts2.length; i += 2) { lo[0] = Math.min(lo[0], pts2[i]); hi[0] = Math.max(hi[0], pts2[i]); lo[1] = Math.min(lo[1], pts2[i + 1]); hi[1] = Math.max(hi[1], pts2[i + 1]); }
      if (v.trail && v.trail.length) { lo[0] = Math.min(lo[0], 0); hi[0] = Math.max(hi[0], 0); lo[1] = Math.min(lo[1], 0); hi[1] = Math.max(hi[1], 0); }
      sc = Math.min(iw / Math.max(hi[0] - lo[0], 1e-9), ih / Math.max(hi[1] - lo[1], 1e-9)) * 0.9;
      ox = ix + iw / 2 - (lo[0] + hi[0]) / 2 * sc; oy = iy + ih / 2 + (lo[1] + hi[1]) / 2 * sc;
      if (v.trail && v.trail.length) {
        x.strokeStyle = '#ffc247'; x.lineWidth = 2; x.beginPath();
        for (i = 0; i + 1 < v.trail.length; i += 2) { X = ox + v.trail[i] * sc; Y = oy - v.trail[i + 1] * sc; if (i) x.lineTo(X, Y); else x.moveTo(X, Y); }
        x.stroke();
        x.fillStyle = '#ffe28a'; x.beginPath(); x.arc(ox, oy, 7, 0, Math.PI * 2); x.fill();
        x.fillStyle = '#5fd0ff'; x.beginPath(); x.arc(ox + v.pts[0] * sc, oy - v.pts[1] * sc, 5, 0, Math.PI * 2); x.fill();
      } else {
        x.fillStyle = '#5fd0ff';
        for (i = 0; i + 1 < v.pts.length; i += 2) { x.beginPath(); x.arc(ox + v.pts[i] * sc, oy - v.pts[i + 1] * sc, 4, 0, Math.PI * 2); x.fill(); }
      }
    } else if (SP.inset === 'path' && v.px && v.px.length > 1) {
      lo = [Math.min.apply(null, v.px), Math.min.apply(null, v.py)]; hi = [Math.max.apply(null, v.px), Math.max.apply(null, v.py)];
      sc = Math.min(iw / Math.max(hi[0] - lo[0], 1), ih / Math.max(hi[1] - lo[1], 1)) * 0.9;
      ox = ix + iw / 2 - (lo[0] + hi[0]) / 2 * sc; oy = iy + ih / 2 + (lo[1] + hi[1]) / 2 * sc;
      x.strokeStyle = '#ffc247'; x.lineWidth = 2; x.beginPath();
      for (i = 0; i < v.px.length; i++) { X = ox + v.px[i] * sc; Y = oy - v.py[i] * sc; if (i) x.lineTo(X, Y); else x.moveTo(X, Y); }
      x.stroke();
      x.fillStyle = '#7fe3a1'; x.beginPath(); x.arc(ox + v.px[0] * sc, oy - v.py[0] * sc, 5, 0, Math.PI * 2); x.fill();
      x.fillStyle = '#ff7b5a'; x.beginPath(); x.arc(ox + v.px[v.px.length - 1] * sc, oy - v.py[v.py.length - 1] * sc, 5, 0, Math.PI * 2); x.fill();
    } else if (SP.inset === 'bands' && v.bk && v.be1 && v.be1.length) {
      var all = v.be1.concat(v.be2 || []);
      mn = Math.min.apply(null, all); mx = Math.max.apply(null, all); mn -= 0.1 * (mx - mn); mx += 0.1 * (mx - mn);
      X = function (u2) { return ix + 24 + u2 * (iw - 24); }; Y = function (e2) { return iy + ih - (e2 - mn) / (mx - mn) * ih; };
      x.strokeStyle = '#59b6ff'; x.lineWidth = 3;
      [v.be1, v.be2 || []].forEach(function (arr) {
        if (!arr.length) return; x.beginPath();
        for (i = 0; i < arr.length; i++) { if (i) x.lineTo(X(v.bk[i]), Y(arr[i])); else x.moveTo(X(v.bk[i]), Y(arr[i])); }
        x.stroke();
      });
      x.fillStyle = '#ff7b5a';
      [v.bn1 || [], v.bn2 || []].forEach(function (arr) { for (i = 0; i < arr.length; i += 2) { x.beginPath(); x.arc(X(v.bk[i]), Y(arr[i]), 3.2, 0, Math.PI * 2); x.fill(); } });
      x.fillStyle = '#6f88a3'; x.font = '500 15px "JetBrains Mono", monospace'; x.textAlign = 'right';
      x.fillText(fmt(mx, 1), ix + 20, iy + 12); x.fillText(fmt(mn, 1), ix + 20, iy + ih); x.textAlign = 'left';
    } else if (SP.inset === 'hist' && v.hx && v.hx.length) {
      mx = Math.max.apply(null, v.hy.concat(v.hz)) * 1.1 || 1; sx = iw / v.hx.length;
      x.fillStyle = 'rgba(255,194,71,.55)';
      for (i = 0; i < v.hx.length; i++) { var hh = v.hy[i] / mx * ih; x.fillRect(ix + i * sx + 1, iy + ih - hh, sx - 2, hh); }
      x.strokeStyle = '#59b6ff'; x.lineWidth = 3; x.beginPath();
      for (i = 0; i < v.hx.length; i++) { X = ix + (i + 0.5) * sx; Y = iy + ih - v.hz[i] / mx * ih; if (i) x.lineTo(X, Y); else x.moveTo(X, Y); }
      x.stroke();
    }
    x.textAlign = 'left';
  }
  function drawScreen() {
    var v = st.on ? (st.last || preview) : preview;
    screenTex.draw(function (x, W2, H2) {
      x.fillStyle = st.on ? '#0b1420' : '#05080c'; x.fillRect(0, 0, W2, H2);
      if (!st.on) {
        x.fillStyle = '#44566a'; x.font = '600 30px "Public Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
        x.fillText('HOOLA LABVIEW — press the power button', W2 / 2, H2 / 2);
        x.textAlign = 'left'; x.textBaseline = 'alphabetic';
        return;
      }
      x.fillStyle = '#132231'; x.fillRect(0, 0, W2, 56);
      x.fillStyle = '#dce7f4'; x.font = '600 25px "Public Sans", sans-serif'; x.textBaseline = 'middle';
      var head = SP.title + '  ·  ' + METHODS[st.mi];
      while (x.measureText(head).width > W2 - 330 && head.length > 12) head = head.slice(0, -2);
      x.fillText(head, 20, 29);
      x.fillStyle = '#7fe3a1'; x.font = '600 22px "JetBrains Mono", monospace'; x.textAlign = 'right';
      x.fillText(SP.nlabel + ' = ' + NS[st.ni], W2 - 20, 29); x.textAlign = 'left';
      // ---- plot panel
      var P = { l: 86, r: 404, t: 92, b: 100 }, pw = W2 - P.l - P.r, ph = H2 - P.t - P.b;
      x.fillStyle = '#081019'; x.fillRect(P.l - 60, P.t - 28, pw + 72, ph + 56);
      var cx = v.cx || [], ce = v.ce || [], cy = v.cy || [], cy2 = v.cy2 || [], px = v.px || [], py = v.py || [];
      var LOGX = !!SP.logx, tx = function (q) { return LOGX ? Math.log(Math.max(q, 1)) / Math.LN10 : q; };
      var from = Math.floor((cy.length || 0) * (SP.yFrom || 0));
      var xs = cx.map(tx), ys = [], i;
      ce.forEach(function (q) { if (isFinite(q)) ys.push(q); });
      cy.forEach(function (q, i2) { if (isFinite(q) && i2 >= from) ys.push(q); });
      cy2.forEach(function (q) { if (isFinite(q)) ys.push(q); });
      if (SP.nodes !== false) { py.forEach(function (q) { if (isFinite(q)) ys.push(q); }); px.forEach(function (q) { if (isFinite(q)) xs.push(tx(q)); }); }
      if (SP.hlines) { ys.push(v.hl1); ys.push(v.hl2); }
      if (SP.vline && v.vline) xs.push(tx(v.vline));
      if (SP.bars) ys.push(0);
      if (!xs.length) { xs = [0, 1]; } if (!ys.length) { ys = [0, 1]; }
      var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
      var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
      if (SP.zero) { y0 = Math.min(y0, 0); y1 = Math.max(y1, 0); }
      if (x1 - x0 < 1e-12) x1 = x0 + 1; if (y1 - y0 < 1e-12) y1 = y0 + 1;
      var pad = (y1 - y0) * 0.12; y0 -= pad; if (!SP.bars) y1 += pad; else { y1 += pad; y0 = Math.min(y0, 0); }
      var X = function (q) { return P.l + (q - x0) / (x1 - x0) * pw; };
      var Y = function (q) { return H2 - P.b - (q - y0) / (y1 - y0) * ph; };
      x.strokeStyle = '#17293c'; x.lineWidth = 1; x.fillStyle = '#6f88a3'; x.font = '500 19px "JetBrains Mono", monospace';
      for (i = 0; i <= 4; i++) {
        var gx = x0 + (x1 - x0) * i / 4, gy = y0 + (y1 - y0) * i / 4;
        x.beginPath(); x.moveTo(X(gx), Y(y0)); x.lineTo(X(gx), Y(y1)); x.stroke();
        x.beginPath(); x.moveTo(X(x0), Y(gy)); x.lineTo(X(x1), Y(gy)); x.stroke();
        x.textAlign = 'center';
        x.fillText(LOGX ? fmt(Math.pow(10, gx), gx < 3 ? 1 : 0) : fmt(gx, 2), X(gx), H2 - P.b + 26);
        x.textAlign = 'right'; x.fillText(fmt(gy, Math.abs(gy) >= 100 ? 0 : 2), P.l - 10, Y(gy) + 7);
      }
      x.textAlign = 'left';
      x.strokeStyle = '#2e4760'; x.lineWidth = 2;
      x.beginPath(); x.moveTo(X(x0), Y(Math.max(y0, Math.min(y1, 0)))); x.lineTo(X(x1), Y(Math.max(y0, Math.min(y1, 0)))); x.stroke();
      x.fillStyle = '#9fb6cf'; x.font = '600 21px "Public Sans", sans-serif';
      x.fillText(SP.xlabel, X(x1) - Math.min(14 + SP.xlabel.length * 9, 300), H2 - P.b + 54);
      x.save(); x.translate(P.l - 62, Y(y1) + 54); x.rotate(-Math.PI / 2); x.fillText(SP.ylabel, 0, 0); x.restore();
      var rev = Math.max(0.02, Math.min(1, st.reveal));
      // bars: what the simulation counted
      if (SP.bars && cy.length) {
        var bwid = cx.length > 1 ? Math.abs(X(tx(cx[1])) - X(tx(cx[0]))) * 0.78 : 20;
        x.fillStyle = 'rgba(255,194,71,.62)';
        for (i = 0; i < cy.length; i++) {
          var top = Y(cy[i] * rev), bot = Y(Math.max(y0, 0));
          x.fillRect(X(tx(cx[i])) - bwid / 2, Math.min(top, bot), bwid, Math.abs(bot - top));
        }
      }
      if (SP.fill && cx.length > 1) {
        x.fillStyle = 'rgba(80,170,255,.14)'; x.beginPath(); x.moveTo(X(tx(cx[0])), Y(Math.max(y0, Math.min(y1, 0))));
        for (i = 0; i < cx.length; i++) x.lineTo(X(tx(cx[i])), Y(ce[i]));
        x.lineTo(X(tx(cx[cx.length - 1])), Y(Math.max(y0, Math.min(y1, 0)))); x.closePath(); x.fill();
      }
      // the reference
      if (ce.length > 1 && ce.length === cx.length) {
        x.strokeStyle = '#59b6ff'; x.lineWidth = 4; x.beginPath();
        for (i = 0; i < cx.length; i++) { if (i) x.lineTo(X(tx(cx[i])), Y(ce[i])); else x.moveTo(X(tx(cx[i])), Y(ce[i])); }
        x.stroke();
      }
      // what the method built
      if (!SP.bars && cy.length > 1 && SP.showCurve && cy.length === cx.length) {
        x.strokeStyle = '#ffc247'; x.lineWidth = 3; x.setLineDash([9, 7]); x.beginPath();
        var nseen = Math.max(2, Math.floor(cy.length * rev));
        for (i = 0; i < nseen && i < cx.length; i++) { if (i) x.lineTo(X(tx(cx[i])), Y(cy[i])); else x.moveTo(X(tx(cx[i])), Y(cy[i])); }
        x.stroke(); x.setLineDash([]);
      }
      if (cy2.length > 1 && cy2.length === cx.length) {
        x.strokeStyle = '#7fe3a1'; x.lineWidth = 3; x.setLineDash([3, 5]); x.beginPath();
        for (i = 0; i < cx.length; i++) { if (i) x.lineTo(X(tx(cx[i])), Y(cy2[i])); else x.moveTo(X(tx(cx[i])), Y(cy2[i])); }
        x.stroke(); x.setLineDash([]);
      }
      if (SP.hlines) {
        [[v.hl1, '#ffc247', 'found'], [v.hl2, '#7fe3a1', 'exact']].forEach(function (h) {
          x.strokeStyle = h[1]; x.lineWidth = 2; x.setLineDash([12, 6]); x.beginPath(); x.moveTo(X(x0), Y(h[0])); x.lineTo(X(x1), Y(h[0])); x.stroke(); x.setLineDash([]);
        });
      }
      if (SP.vline && v.vline) {
        x.strokeStyle = '#7fe3a1'; x.lineWidth = 2; x.setLineDash([12, 6]); x.beginPath(); x.moveTo(X(tx(v.vline)), Y(y0)); x.lineTo(X(tx(v.vline)), Y(y1)); x.stroke(); x.setLineDash([]);
      }
      // the nodes (or data points, or fitted model) the method used
      if (SP.nodes !== false) {
        var nnodes = Math.max(1, Math.floor(px.length * rev));
        var stride = Math.max(1, Math.ceil(px.length / 80)), rad = SP.dots ? 3 : (px.length > 40 ? 3.5 : 5.5);
        for (i = 0; i < nnodes; i++) {
          if (!isFinite(px[i]) || !isFinite(py[i])) continue;
          if (i % stride !== 0 && i !== nnodes - 1) continue;
          x.fillStyle = '#ff7b5a'; x.beginPath(); x.arc(X(tx(px[i])), Y(py[i]), rad, 0, Math.PI * 2); x.fill();
        }
        if (KNAME === 'cr_poly' && nnodes) {
          x.strokeStyle = 'rgba(255,123,90,.5)'; x.lineWidth = 2; x.beginPath();
          x.moveTo(X(tx(px[nnodes - 1])), Y(y0)); x.lineTo(X(tx(px[nnodes - 1])), Y(y1)); x.stroke();
        }
      }
      // legend
      x.font = '500 18px "Public Sans", sans-serif';
      var lg = [['#59b6ff', SP.bars ? '— exact' : '— exact'], [SP.bars ? '#ffc247' : '#ffc247', SP.bars ? '▮ simulation' : '– – method']];
      if (SP.nodes !== false) lg.push(['#ff7b5a', SP.dots ? '• data' : '• points used']);
      if (cy2.length) lg.push(['#7fe3a1', SP.line2 && KNAME === 'cr_photon' ? '·· absorbed' : '·· second curve']);
      var lx = P.l + 4;
      lg.forEach(function (it) { x.fillStyle = it[0]; x.fillText(it[1], lx, P.t - 38); lx += x.measureText(it[1]).width + 22; });
      // ---- right column: the picture in the corner, the run log, the answer
      var RX = W2 - P.r + 24, colW = P.r - 24, y = P.t;
      if (SP.inset) {
        drawInset(x, v, RX - 14, P.t - 28, colW, 214);
        y = P.t - 28 + 214 + 34;
      } else {
        x.fillStyle = '#0d1a28'; x.fillRect(RX - 14, P.t - 28, colW, H2 - P.t - P.b + 56);
        y = P.t - 2;
      }
      if (SP.inset) { x.fillStyle = '#0d1a28'; x.fillRect(RX - 14, y - 26, colW, H2 - P.b - (y - 26) - 4); }
      x.fillStyle = '#9fb6cf'; x.font = '600 21px "Public Sans", sans-serif'; x.fillText('RUN LOG', RX, y);
      x.font = SP.inset ? '500 17px "JetBrains Mono", monospace' : '500 20px "JetBrains Mono", monospace';
      var keep = SP.inset ? 7 : 9, rows2 = S.rows.slice(-keep), yy = y + 30;
      if (!rows2.length) { x.fillStyle = '#5d7791'; x.fillText('no runs yet', RX, yy); }
      rows2.forEach(function (r) {
        if (SP.inset) { x.fillStyle = '#d7e4f2'; x.fillText(rowText(r), RX, yy); yy += 25; }
        else {
          x.fillStyle = '#d7e4f2'; x.fillText('n=' + String(r.n).padStart(6, ' ') + '  ' + sci(r.val), RX, yy); yy += 26;
          x.fillStyle = '#86a4c2'; x.fillText('         err ' + r.err.toExponential(2), RX, yy); yy += 32;
        }
      });
      var cur = st.last;
      x.fillStyle = '#132231'; x.fillRect(RX - 14, H2 - P.b + 4, colW, 76);
      x.font = '600 22px "JetBrains Mono", monospace';
      if (cur) {
        x.fillStyle = '#7fe3a1'; x.fillText(SP.quantity.split(' at ')[0].split(' (')[0].slice(0, 20) + ' = ' + sci(cur.val), RX, H2 - P.b + 32);
        x.font = '600 19px "JetBrains Mono", monospace'; x.fillStyle = '#ffd083';
        x.fillText('exact ' + sci(cur.exact) + '  err ' + cur.err.toExponential(1), RX, H2 - P.b + 58);
        if (SP.extras) { x.font = '500 15px "JetBrains Mono", monospace'; x.fillStyle = '#86a4c2'; x.fillText(SP.extras(cur).slice(0, 44), RX, H2 - P.b + 76); }
      } else {
        x.fillStyle = '#5d7791'; x.fillText('press ENTER to run', RX, H2 - P.b + 46);
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
    NS = SP.nsFor(st.mi); st.ni = Math.min(st.ni, NS.length - 1);
    st.last = null; preview = compute(st.ni, st.mi);
    drawScreen(); S.render();
  }
  function distinctN() { var seen = {}, k = 0; S.rows.forEach(function (r) { if (!seen[r.n]) { seen[r.n] = 1; k++; } }); return k; }
  function orderOf() {
    var C = HK.CALCS.cr_order;
    return C ? C.fn(S.rows, p) : 0;
  }
  function best() {                                  // the run with the smallest error (ties: the larger n)
    var b = null;
    S.rows.forEach(function (r) { if (!b || r.err < b.err || (r.err === b.err && r.n > b.n)) b = r; });
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
      principle: 'A simulation answers a question the algebra cannot, but only to the accuracy of its grid, its step or its '
        + 'number of samples. The practical is therefore a measurement: run the method at several settings, compare each '
        + 'answer with the reference value, and see how the error falls. ' + (SP.expect || ''),
      formula: SP.title, formulaNote: SP.formula,
      more: ['The reference value for this problem is known exactly (or, for a statistical result, far better than the simulation), so every run has a real error, not a guess.',
        'Where a result is statistical, the same seed repeats the same run; change the seed and the error changes, which is how the scatter itself is measured.',
        'Keep the method fixed while you change n, and change only one thing at a time - the same discipline as any '
        + 'other practical.'],
      precautions: 'Read the method card before switching on. Record the method, n, the answer and the error of '
        + 'every run before you change a setting. Never report a digit the error does not support, and remember that '
        + 'below some step size round-off makes the answer worse, not better.',
    },
    book: {
      title: 'Expt. — ' + S.lab.title,
      lines: ['Aim: ' + S.lab.aim, 'Problem: ' + SP.title, 'Reference value = ' + sci(ex0),
        'Method: ' + METHODS[M0] + (METHODS.length > 1 ? ' (and the others for comparison)' : ''), 'For each run: ' + SP.nlabel + ', answer, error.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: 'Method', get: function (r) { return METHODS[r.mi].split(' ')[0]; } },
        { label: (SP.ncol || SP.nlabel).slice(0, 14), get: function (r) { return String(r.n); } },
        { label: 'Answer', get: function (r) { return sci(r.val); } },
        { label: 'Rel. error', get: function (r) { return r.err.toExponential(2); } }],
    },
    graph: {
      x: function (r) { return r.n; }, y: function (r) { var a = Math.abs(ex0) || 1; return Math.max(-5 * a, Math.min(5 * a, r.val)); },
      xlabel: SP.nlabel, ylabel: SP.quantity.slice(0, 28), x0: 0,
      line: function () { return function () { return ex0; }; },
    },
    result: function (rows) {
      var b = null;
      rows.forEach(function (r) { if (!b || r.err < b.err || (r.err === b.err && r.n > b.n)) b = r; });
      if (!b) return null;
      return { label: SP.quantity, value: b.val, unit: SP.unit || '', digits: SP.digits, truth: b.exact,
        note: 'Best run: ' + METHODS[b.mi] + ' at ' + SP.nlabel + ' = ' + b.n + '; relative error ' + b.err.toExponential(2)
          + (S.rows.length >= 3 ? '. Order measured from log(error) vs log(n): ' + fmt(orderOf(), 2) : '') };
    },
    tol: SP.tol,
    chips: ['Why does the error fall with n?', 'Which method is best here?', 'Check my runs',
      'Why does a smaller step sometimes make it worse?', 'Explain the order of a method'],
    viva: (SP.viva || []).concat([['What exactly is being measured in a computational practical?',
      ['The error of a method at a known step size', 'The speed of the computer', 'The value of a constant'], 0,
      'The answer is known in closed form; what the run tells you is the error of the method.'],
      ['The error of a method falls as n^-4. The method is',
        ['fourth order', 'fourth degree', 'exact'], 0, 'Order p means the error goes as h^p, that is n^-p.'],
      ['Why is one run never enough?', ['One run gives no idea of its own error', 'One run is slow',
        'One run uses the wrong method'], 0,
        'Only by changing the step and watching the answer move can you say how accurate it is.']]),
    askState: function () {
      var b = best();
      return { problem: SP.title, kernel: KNAME, method: METHODS[st.mi], workstation_on: st.on,
        setting_n: NS[st.ni], reference_value: ex0, runs_recorded: S.rows.length,
        last_numerical_answer: st.last ? st.last.val : null, last_relative_error: st.last ? st.last.err : null,
        best_run: b ? { n: b.n, value: b.val, error: b.err } : null,
        measured_order: S.rows.length >= 3 ? orderOf() : null };
    },

    steps: [
      { id: 'card', title: 'The problem', view: 'card',
        render: function (u) {
          u.h2('Read the method card');
          u.p('Every computational practical starts on paper: what is being solved, which methods are allowed, and '
            + 'what the reference answer is, so that the error of each run can be measured.');
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
          u.note(SP.nlabel + ' = ' + NS[st.ni]);
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
          if (SP.expect) u.note(SP.expect);
          u.formula('error ≈ C n^(−p)', 'so  log(error) = log C − p log n');
          u.live(function () {
            var o = orderOf();
            return 'Slope of log(error) against log(n): p = ' + fmt(o, 2) + '  (from ' + S.rows.length + ' runs)';
          });
          if (b) u.note('Finest run: ' + METHODS[b.mi] + ' at ' + SP.nlabel + ' = ' + b.n + ' gives '
            + SP.quantity + ' = ' + sci(b.val) + ', error ' + b.err.toExponential(2) + '.');
          u.h3('All runs'); u.table();
          u.p('If the measured order is far from what the method promises, the error may have reached round-off or the '
            + 'statistical floor, or the run log may be mixing two different methods. Report the run with the smallest error.');
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

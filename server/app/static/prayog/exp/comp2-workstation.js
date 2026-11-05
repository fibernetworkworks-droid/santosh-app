/* Prayogshala studio RIG: the computational physics WORKSTATION, second set (spectra, quadrature, quantum,
   special functions, linear algebra, dynamics ...). One bench serves every method in the comp2_ug kernel pack (cq_*): desk mat, monitor, keyboard with a live Enter key,
   mouse, tower and the printed METHOD CARD. The student reads the card, switches the machine on, chooses the
   method and the step size / sample count, presses Enter - and the MONITOR DRAWS the computation: the exact curve,
   what the method built, and the nodes it actually used, with the run log beside it.
   Every number comes from the lab's kernel (HoolaKernels.K[lab.kernel]) at the student's settings - the same code
   the server checks - so the error printed on the screen is the real error of that method at that step size. */
HoolaStudio.define('comp2-workstation', function (S) {
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
  var SUBD = '₀₁₂₃₄₅₆₇₈₉';
  function sub(n) { return String(n).split('').map(function (c) { return SUBD.charAt(+c); }).join(''); }
  var FOUR_LIST = [[[1, 1], [1, 3], [1, 5], [1, 7]], [[0, 1], [0, 3], [0, 5], [0, 7]],
    [[0, 0], [1, 1], [0, 2], [0, 4]], [[0, 0], [0, 2], [0, 4], [0, 6]]];
  var LAB_ORD = ['', 'st', 'nd', 'rd'];
  var SPEC = {
    cq_fourier: {
      quantity: (function () {
        var l = (FOUR_LIST[CAS] || [])[Math.round(p.cidx || 0) % 4] || [0, 1];
        return l[1] === 0 ? 'mean value a₀/2' : (l[0] === 0 ? 'a' : 'b') + sub(l[1]);
      })(),
      unit: '', digits: 6, nlabel: 'samples N', ns: [8, 16, 32, 64, 128, 256], tol: 0.01, conv: 'loglog',
      methods: ['Periodic trapezoid rule'], xlabel: 't (rad)', ylabel: 'f(t)', showCurve: true, zero: true,
      legend: ['— exact f(t)', '– – 9 harmonics', '• samples'],
      title: ['Square wave', 'Triangle wave', 'Half-wave rectified sine', 'Full-wave rectified sine'][CAS] || 'Periodic function',
      problem: function () {
        var l = (FOUR_LIST[CAS] || [])[Math.round(p.cidx || 0) % 4] || [0, 1], which = l[1] === 0 ? 'the mean value a₀/2 = (1/2π)∫ f dt'
          : (l[0] === 0 ? 'a' : 'b') + sub(l[1]) + ' = (1/π)∫ f(t) ' + (l[0] === 0 ? 'cos' : 'sin') + '(' + l[1] + 't) dt';
        var shape = ['+A for 0 < t < π, −A for π < t < 2π', 'A(1 − 2|t|/π) for −π ≤ t ≤ π (a triangle, +A at t = 0)',
          'A sin t when positive, 0 otherwise', 'A |sin t|'][CAS];
        var law = ['bₖ = 4A/(kπ) for odd k, all other coefficients 0', 'aₖ = 8A/(k²π²) for odd k, all others 0',
          'a₀/2 = A/π, b₁ = A/2, aₖ = −2A/(π(k²−1)) for even k', 'a₀/2 = 2A/π, aₖ = −4A/(π(k²−1)) for even k'][CAS];
        return ['f(t) = ' + shape + ',  period 2π,  A = ' + fx(p.A, 3), 'Measure ' + which,
          'by the trapezoid rule on N equally spaced samples of one period.', 'Exact:  ' + law, 'Exact value here = ' + sci(ex0)];
      },
      formula: 'aₖ ≈ (2/N) Σ f(tⱼ) cos k tⱼ · bₖ ≈ (2/N) Σ f(tⱼ) sin k tⱼ',
    },
    cq_dft: {
      quantity: '|F(ν)|', unit: '', digits: 6, nlabel: 'samples N', ns: [16, 32, 64, 128, 256, 512], tol: 0.01, conv: 'tab',
      nsCase: { 2: [8, 16, 32, 64, 128, 256], 3: [4, 8, 16, 32, 64, 128] },
      methods: ['Direct DFT', 'FFT (radix-2)'], xlabel: CAS === 3 ? 'ω/π' : 'frequency ν', ylabel: CAS === 3 ? '|X(ω)|' : '|F(ν)|', stems: true,
      caseOver: { 3: { quantity: 'largest side-lobe |X|' } },
      legend: ['— exact transform', '', '• DFT bins'],
      title: ['Fourier transform of a square pulse', 'Fourier transform of a cosine in a window', 'Fourier transform of a Gaussian',
        'DFT of [1, 1, 1, 1] with zero padding'][CAS] || 'Fourier transform',
      problem: function () {
        var fr = 'Read the transform at ν = ' + fx(p.nu, 4) + ' (bin m = νL, sample spacing Δt = L/N).';
        if (CAS === 1) return ['f(t) = cos(2π·' + fx(p.f0, 3) + '·t) seen through a window of length L = ' + fx(p.L, 1),
          'Exact:  |F(ν)| = ½|L sinc(L(ν−f₀)) + L sinc(L(ν+f₀))|', fr, 'Exact value here = ' + sci(ex0),
          'The tone does not sit on a bin, so the spectrum leaks.'];
        if (CAS === 2) return ['f(t) = exp(−t²/2σ²),  σ = ' + fx(p.sg, 3) + ',  window L = ' + fx(p.L, 1),
          'Exact:  F(ν) = σ√(2π) exp(−2π²σ²ν²)', fr, 'Exact value here = ' + sci(ex0),
          'Too few samples fold the Gaussian tails back (aliasing).'];
        if (CAS === 3) return ['x[n] = 1 for n = 0…3, then zeros, padded to N points (N = 4, 8, 16 …).',
          'DTFT:  |X(ω)| = |sin 2ω / sin(ω/2)|, a main lobe and side-lobes.',
          'Read the largest side-lobe the N-point DFT shows (bins between π/2 and π).', 'Exact side-lobe peak of the DTFT = ' + sci(ex0)];
        return ['f(t) = 1 for |t| < ' + fx(p.a, 2) + ', else 0  (a pulse of width ' + fx(2 * p.a, 2) + '),  window L = ' + fx(p.L, 1),
          'Exact:  |F(ν)| = |sin(2πaν) / (πν)|', fr, 'Exact value here = ' + sci(ex0)];
      },
      formula: 'Xₘ = Σ xⱼ e^(−2πi jm/N) · F(νₘ) ≈ Δt Xₘ · direct N² steps, FFT N log₂N',
    },
    cq_gauss: {
      quantity: 'integral I', unit: '', digits: 10, nlabel: 'nodes n', ns: [1, 2, 3, 4, 6, 8, 12], tol: 0.001, conv: 'linlog',
      methods: ['Gauss-Legendre', 'Gauss-Laguerre', 'Gauss-Hermite'], xlabel: 'x', ylabel: 'integrand (with weight)',
      legend: ['— integrand × weight', '', '• nodes'], fill: true,
      title: 'Gauss quadrature: Legendre, Laguerre and Hermite rules',
      problem: function () {
        return ['Legendre:  ∫₀¹ 4/(1+x²) dx = π', 'Laguerre:  ∫₀^∞ e^(−x) sin(' + fx(p.wl, 2) + 'x) dx = ' + sci(p.wl / (1 + p.wl * p.wl)),
          'Hermite:  ∫ e^(−x²) cos(' + fx(p.wh, 2) + 'x) dx = √π e^(−' + fx(p.wh * p.wh / 4, 4) + ') = ' + sci(Math.sqrt(Math.PI) * Math.exp(-p.wh * p.wh / 4)),
          'n nodes xᵢ and weights wᵢ make the rule exact for every polynomial of degree up to 2n−1.'];
      },
      formula: 'I ≈ Σ wᵢ f(xᵢ), nodes = zeros of Pₙ, Lₙ or Hₙ',
    },
    cq_schro: {
      quantity: 'energy E', unit: 'eV', digits: 6, nlabel: 'grid points N', ns: [50, 100, 200, 400, 800, 1600], tol: 0.01, conv: 'loglog',
      nsCase: { 1: [200, 400, 800, 1600, 3200], 2: [200, 400, 800, 1600, 3200] },
      caseOver: { 2: { quantity: 'binding energy below dissociation', unit: 'cm⁻¹', conv: 'tab' } },
      methods: ['Finite differences + Sturm bisection'], xlabel: CAS === 2 ? 'y = a(r − rₑ)' : (CAS === 1 ? 'r / a' : 'r (bohr)'),
      ylabel: 'u(r)', zero: true, legend: ['— exact u(r)', '', '• numerical u(r)'],
      title: ['Radial Schrödinger equation: hydrogen-like atom', 'Radial Schrödinger equation: screened Coulomb (Hulthén) potential',
        'Radial Schrödinger equation: Morse potential'][CAS] || 'Radial Schrödinger equation',
      problem: function () {
        var k = Math.round(p.kst), l = Math.round(p.ll);
        if (CAS === 1) return ['V(r) = −V₀ e^(−r/a) / (1 − e^(−r/a)),  a = ' + fx(p.aa, 2) + ' bohr,  V₀a = e²/4πε₀',
          'In units of a and ħ²/2ma²:  −u″ + [l(l+1)/x² + V]u = εu,  strength g = 2a = ' + fx(p.g, 2),
          'State: ' + (k + 1) + 's (l = 0).  Exact (Hulthén):  Eₙ = −(ħ²/2ma²)[(g − n²)/2n]²',
          'Exact value here = ' + sci(ex0) + ' eV'];
        if (CAS === 2) return ['V(r) = Dₑ(1 − e^(−a(r−rₑ)))² with the H₂ constants ωₑ = 4401.213, ωₑxₑ = 121.336 cm⁻¹ (NIST)',
          'Morse parameter λ = ωₑ/2ωₑxₑ = ' + fx(p.lam, 4) + ',  energy unit ε₀ = ħ²a²/2μ = ωₑxₑ = ' + fx(p.e0, 3) + ' cm⁻¹',
          'Level v = ' + k + ':  exact binding below dissociation = ε₀(λ − v − ½)² = ' + sci(ex0) + ' cm⁻¹',
          'The measured D₀ of H₂ is 36118.3 cm⁻¹: the Morse model is a model, not the molecule.'];
        return ['Hydrogen-like atom, reduced mass μ = ' + fx(p.mu, 5) + ' mₑ, atomic units (Eₕ = 27.211386 eV, bohr).',
          'u″ = 2μ[ l(l+1)/(2μr²) − 1/r − E ] u,  u(0) = u(r_max) = 0,  r_max = ' + fx(p.rmax, 1) + ' bohr',
          'State n = ' + (k + l + 1) + ', l = ' + l + '.  Exact:  Eₙ = −μ Eₕ / 2n²',
          'Exact value here = ' + sci(ex0) + ' eV'];
      },
      formula: 'tridiagonal H: d = 2/h² + V, off-diagonal −1/h²; Sturm count + 100 bisections',
    },
    cq_special: {
      quantity: ['Pₙ(x)', 'integral of Pₙ²', 'Lₙ(x)', 'Hₙ(x)', 'Jₙ(x)'][CAS] || 'value', unit: '', digits: 10, nlabel: 'order n',
      ns: [2, 4, 6, 8, 10, 12], tol: 0.01, conv: 'tab',
      methods: CAS === 4 ? ['Upward recurrence', 'Miller downward recurrence'] : (CAS === 1 ? ['Trapezoid rule', 'Simpson rule', 'Gauss-Legendre'] : ['Three-term recurrence']),
      nsCase: { 1: [8, 16, 32, 64, 128, 256] }, caseOver: { 1: { nlabel: 'strips / nodes n' } },
      convM: CAS === 1 ? ['loglog', 'loglog', 'tab'] : null,
      xlabel: 'x', ylabel: ['Pₙ(x)', 'Pₙ(x)²', 'Lₙ(x)', 'Hₙ(x)', 'Jₙ(x)'][CAS] || 'f(x)', showCurve: true, zero: true, fill: CAS === 1,
      legend: CAS === 1 ? ['— Pₙ(x)²', '', '• nodes used'] : ['— explicit sum', '– – recurrence', '• value at x'],
      title: ['Legendre polynomials from their recurrence', 'Orthogonality of Legendre polynomials', 'Laguerre polynomials from their recurrence',
        'Hermite polynomials from their recurrence', 'Bessel functions of integer order'][CAS] || 'Special functions',
      problem: function () {
        if (CAS === 1) return ['Pₙ built by (k+1)Pₖ₊₁ = (2k+1)x Pₖ − k Pₖ₋₁, degree n = ' + Math.round(p.deg),
          'Check  ∫₋₁¹ Pₙ² dx = 2/(2n+1) = ' + sci(ex0), 'and  ∫₋₁¹ Pₙ Pₙ₊₂ dx = 0 (shown as the cross term).',
          'Compare trapezoid, Simpson and Gauss-Legendre quadrature as the setting n grows.'];
        var nm = ['Legendre Pₙ', '', 'Laguerre Lₙ', 'Hermite Hₙ', 'Bessel Jₙ'][CAS], rec = ['(k+1)Pₖ₊₁ = (2k+1)x Pₖ − k Pₖ₋₁',
          '', '(k+1)Lₖ₊₁ = (2k+1−x)Lₖ − k Lₖ₋₁', 'Hₖ₊₁ = 2x Hₖ − 2k Hₖ₋₁', 'Jₖ₊₁ = (2k/x)Jₖ − Jₖ₋₁ (upward) or the same run downward (Miller)'][CAS],
          ref = ['an explicit finite sum', '', 'the explicit sum Σ(−1)ᵏ C(n,k) xᵏ/k!', 'the explicit sum Σ(−1)ᵐ n!/(m!(n−2m)!) (2x)ⁿ⁻²ᵐ', 'its power series Σ (−1)ᵏ (x/2)^(2k+n) / (k!(k+n)!)'][CAS];
        return [nm + '(x) at x = ' + fx(p.x, 3) + ' for the order n you choose.', 'Recurrence:  ' + rec, 'Reference value: ' + ref,
          CAS === 4 ? 'The upward recurrence is unstable once n exceeds x: watch the error blow up.' : 'The error is round-off only; the recurrence is stable.'];
      },
      formula: 'three-term recurrences · explicit sums as the reference',
    },
    cq_linsys: {
      quantity: CAS === 0 ? ['mesh current I₁ (A)', 'mesh current I₂ (A)', 'mesh current I₃ (A)'][Math.round(p.pick)] : ['displacement x₁ (m)', 'displacement x₂ (m)', 'displacement x₃ (m)'][Math.round(p.pick)],
      unit: '', digits: 8, nlabel: 'sweeps n', ns: [1, 2, 3, 5, 8, 12, 20], tol: 0.001, conv: 'linlog', convM: ['tab', 'linlog'],
      methods: ['Gauss elimination', 'Gauss-Seidel'], xlabel: 'sweep', ylabel: CAS === 0 ? 'I (A)' : 'x (m)', showCurve: true,
      legend: ['— exact (Cramer)', '– – value after each sweep', '• values'],
      title: ['Mesh equations of a three-loop circuit', 'Three masses on four springs'][CAS] || 'Linear system',
      problem: function () {
        if (CAS === 0) return ['Loop currents I₁, I₂, I₃ (all clockwise). R₁ = ' + fx(p.r1, 1) + ', R₂ = ' + fx(p.r2, 1) + ', R₃ = ' + fx(p.r3, 1) + ' Ω',
          'shared: R₁₂ = ' + fx(p.rb, 1) + ', R₂₃ = ' + fx(p.rd, 1) + ', R₁₃ = ' + fx(p.rf, 1) + ' Ω;  EMFs ' + fx(p.e1, 1) + ', ' + fx(p.e2, 1) + ', ' + fx(p.e3, 1) + ' V',
          'Kirchhoff\'s voltage law gives  R I = E  (3 × 3).', 'Exact (Cramer\'s rule) = ' + sci(ex0) + ' A'];
        return ['Masses between two walls on springs k₁…k₄ = ' + fx(p.k1, 0) + ', ' + fx(p.k2, 0) + ', ' + fx(p.k3, 0) + ', ' + fx(p.k4, 0) + ' N/m',
          'Static loads ' + fx(p.f1, 2) + ', ' + fx(p.f2, 2) + ', ' + fx(p.f3, 2) + ' N give  K x = F  (3 × 3).',
          'Exact (Cramer\'s rule) = ' + sci(ex0) + ' m'];
      },
      formula: 'elimination with partial pivoting · Gauss-Seidel xᵢ ← (bᵢ − Σⱼ≠ᵢ aᵢⱼxⱼ)/aᵢᵢ',
    },
    cq_eig: {
      quantity: CAS === 0 ? 'eigenvalue λ' : 'smallest principal moment', unit: '', digits: 8, nlabel: CAS === 0 ? 'iterations n' : 'Jacobi sweeps n',
      ns: CAS === 0 ? [2, 5, 10, 20, 40] : [1, 2, 3, 4, 5], tol: 0.01, conv: CAS === 0 ? 'linlog' : 'tab',
      methods: CAS === 0 ? ['Power method (largest)', 'Inverse power method (smallest)'] : ['Jacobi rotations'],
      xlabel: CAS === 0 ? 'iteration' : 'sweep', ylabel: CAS === 0 ? 'Rayleigh estimate' : 'smallest diagonal entry', showCurve: true,
      legend: ['— exact', '– – estimate', '• estimates'],
      title: ['Eigenvalues of a coupled-oscillator matrix', 'Principal axes of a cube about its corner', 'Principal axes of a tilted cuboid'][CAS] || 'Eigenvalues',
      problem: function () {
        if (CAS === 0) return ['A = tridiag(−1, 2, −1), ' + Math.round(p.mdim) + ' × ' + Math.round(p.mdim) + ' (' + Math.round(p.mdim) + ' equal masses on equal springs between two walls).',
          'Exact:  λₖ = 2 − 2cos(kπ/(M+1)),  k = 1…M', 'Power method finds the largest, the inverse power method the smallest.',
          'Exact value here = ' + sci(ex0)];
        if (CAS === 1) return ['Uniform cube of side a = ' + fx(p.sa, 2) + ' m, mass ' + fx(p.mass, 2) + ' kg, about one corner.',
          'Tensor in units of m a²: diagonal 2/3, off-diagonal −1/4.', 'Exact principal moments: 11/12 (twice) and 1/6 m a².',
          'Exact smallest = ' + sci(ex0) + ' kg m²'];
        return ['Uniform cuboid ' + fx(p.sa, 2) + ' × ' + fx(p.sb, 2) + ' × ' + fx(p.sc, 2) + ' m, mass ' + fx(p.mass, 2) + ' kg, about its centre, axes turned by three Euler angles.',
          'Exact principal moments m(b²+c²)/12 and cyclic; the turned tensor hides them.', 'Exact smallest = ' + sci(ex0) + ' kg m²'];
      },
      formula: 'power: v ← Av/|Av| · inverse: solve A w = v · Jacobi: zero the largest off-diagonal by a plane rotation',
    },
  };
  SPEC.cq_map = {
    quantity: ['first period doubling r₁', 'second period doubling r₂', 'Feigenbaum ratio δ'][CAS] || 'r', unit: '', digits: 6,
    nlabel: CAS === 2 ? 'doublings used n' : 'iterations T per trial', ns: CAS === 2 ? [2, 3, 4, 5, 6, 7] : [250, 500, 1000, 2000, 4000],
    tol: 0.01, conv: ['loglog', 'loglog', 'linlog'][CAS] || 'loglog', scatter: true,
    methods: [CAS === 2 ? 'Superstable cycles (Newton)' : 'Bisection on the orbit period'], xlabel: 'r', ylabel: 'x',
    legend: ['● exact value', '', '● found'],
    title: ['Logistic map: the first period doubling', 'Logistic map: the second period doubling', 'Logistic map: the Feigenbaum ratio'][CAS] || 'Logistic map',
    problem: function () {
      if (CAS === 2) return ['x → r x (1 − x). The cycle of length 2ᵏ that passes through x = ½ is superstable, at r = Rₖ.',
        'R₀ = 2, R₁ = 1 + √5 = 3.2361; each Rₖ is found by Newton\'s method on f^(2ᵏ)(½) − ½.',
        'δₖ = (Rₖ − Rₖ₋₁)/(Rₖ₊₁ − Rₖ) tends to Feigenbaum\'s constant.', 'Exact (literature) value = ' + sci(ex0)];
      return ['x → r x (1 − x). Iterate T times, test whether the orbit has period ' + (CAS === 0 ? '1' : '2') + ', and bisect on r.',
        CAS === 0 ? 'Exact:  r₁ = 3 (the slope of the map at the fixed point is −1).' : 'Exact:  r₂ = 1 + √6 = 3.4495.',
        'Near the bifurcation the orbit settles slowly, so the value found is a little low.', 'Exact value = ' + sci(ex0)];
    },
    formula: 'xₙ₊₁ = r xₙ (1 − xₙ) · bifurcation diagram: the long-time values of x against r',
  };
  SPEC.cq_lorenz = {
    quantity: 'volume factor det Φ(T)', unit: '', digits: 8, nlabel: 'RK4 steps n', ns: [20, 40, 80, 160, 320], tol: 0.01, conv: 'loglog',
    methods: ['Runge-Kutta 4'], xlabel: 'x', ylabel: 'z', trace: true, legend: ['● fixed points', '', '— trajectory (x, z)'],
    title: 'Lorenz equations: phase-volume contraction',
    problem: function () {
      return ['x′ = σ(y − x),  y′ = x(ρ − z) − y,  z′ = xy − βz,  σ = ' + fx(p.sg, 2) + ', ρ = ' + fx(p.rho, 2) + ', β = ' + fx(p.be, 4),
        'The flow has divergence −(σ + 1 + β) = ' + fx(-(p.sg + 1 + p.be), 4) + ', a constant.',
        'Integrate the variational matrix Φ′ = JΦ for time T = ' + fx(p.T, 2) + ' and read det Φ(T).',
        'Exact:  det Φ(T) = exp(−(σ + 1 + β)T) = ' + sci(ex0), p.rho > 24.74 ? 'ρ is above 24.74, so the orbit is a strange attractor.' : 'ρ is below 24.74, so the orbit spirals into a fixed point.'];
    },
    formula: 'RK4 on the 12 variables (x, y, z, Φ) · det Φ = exp(∫ trace J dt)',
  };
  SPEC.cq_bvp = {
    quantity: 'y at x = L/2', unit: '', digits: 8, nlabel: 'intervals n', ns: [4, 8, 16, 32, 64], tol: 0.01, conv: 'loglog',
    methods: ['Finite differences', 'Shooting (RK4 + secant)'], xlabel: 'x', ylabel: 'y(x)', legend: ['— exact y(x)', '', '• numerical y'],
    title: ['y″ + y = 0', 'y″ − y = 0 (reaction-diffusion)'][CAS] || 'boundary value problem',
    problem: function () {
      return [(CAS === 0 ? 'y″ + y = 0' : 'y″ − y = 0') + ',  y(0) = 0,  y(L) = ' + fx(p.B, 2) + ',  L = ' + fx(p.L, 2),
        'Exact:  y = ' + fx(p.B, 2) + (CAS === 0 ? ' sin x / sin L' : ' sinh x / sinh L'), 'Read y at the middle, x = L/2.',
        'Exact value = ' + sci(ex0), 'Finite differences solve a tridiagonal system; shooting guesses y′(0) and corrects it.'];
    },
    formula: '(yⱼ₊₁ − 2yⱼ + yⱼ₋₁)/h² ± yⱼ = 0 · shooting: y′(0) from two trial shots',
  };
  SPEC.cq_pde = {
    quantity: ['u(½, ½)', 'u(½, T)', 'u(½, T)'][CAS] || 'u', unit: '', digits: 8, nlabel: 'grid intervals n',
    ns: [[5, 10, 20, 40], [4, 8, 16, 32], [10, 20, 30, 40, 60]][CAS] || [5, 10, 20, 40], tol: 0.01, conv: 'loglog', convM: CAS === 1 ? ['tab', 'loglog', 'loglog'] : null,
    methods: [['Jacobi relaxation', 'Gauss-Seidel', 'SOR'], ['FTCS (explicit)', 'BTCS (implicit)', 'Crank-Nicolson'], ['Leapfrog']][CAS] || ['SOR'],
    xlabel: 'x', ylabel: ['u(x, ½)', 'u(x, T)', 'u(x, T)'][CAS] || 'u', legend: ['— exact', '', '• numerical'],
    title: ['Laplace equation on a square plate', 'Heat equation in a rod', 'Wave equation on a string'][CAS] || 'PDE',
    problem: function () {
      if (CAS === 1) return ['u_t = α u_xx on 0 < x < 1, u(x,0) = sin πx, ends held at 0, α = ' + fx(p.al, 2) + ', time step ' + fx(p.dt, 4) + ', end time T = ' + fx(p.T, 2),
        'Exact:  u = exp(−π²αt) sin πx', 'Exact value at x = ½ = ' + sci(ex0), 'FTCS is stable only for α dt/h² ≤ ½: watch it blow up on a fine grid.'];
      if (CAS === 2) return ['u_tt = c² u_xx on 0 < x < 1, u(x,0) = sin πx, u_t = 0, ends fixed, c = ' + fx(p.cw, 2) + ', Courant number ν = ' + fx(p.nu, 2),
        'Exact:  u = cos(πct) sin πx', 'Leapfrog is exact at ν = 1 and unstable above it.', 'Exact value at x = ½ at the end time = ' + sci(ex0)];
      return ['∇²u = 0 on the unit square; u = sin πx on the top edge y = 1, u = 0 on the other three.',
        'Exact:  u = sin πx sinh πy / sinh π', 'Read the centre value u(½, ½).', 'Exact value = ' + sci(ex0),
        'Sweep until the largest change is below 1e-11; the work is the number of sweeps.'];
    },
    formula: 'Laplace: u = average of 4 neighbours · heat: r = α dt/h² · wave: ν = c dt/h',
  };
  SPEC.cq_planck = {
    quantity: ['total power M', 'peak wavelength λ_max', 'RJ / Planck at the peak', 'Wien / Planck at the peak'][CAS] || 'value',
    unit: ['W/m²', 'm', '', ''][CAS] || '', digits: 6, nlabel: CAS === 0 ? 'Simpson strips n' : 'golden-section steps n',
    ns: CAS === 0 ? [8, 16, 32, 64, 128] : [4, 8, 12, 16, 24, 32], tol: 0.01, conv: CAS === 0 ? 'loglog' : 'tab',
    methods: [CAS === 0 ? 'Simpson rule' : 'Golden-section search'], xlabel: CAS === 0 ? 'x = hc/λkT' : 'λ (m)', ylabel: CAS === 0 ? 'x³/(eˣ−1)' : 'M(λ) / M(peak)',
    showCurve: CAS !== 0 ? true : false, zero: true,
    legend: CAS === 0 ? ['— integrand', '', '• Simpson nodes'] : ['— Planck', '– – Rayleigh-Jeans', '• peak found'],
    title: ['Stefan-Boltzmann law from Planck\'s law', 'Wien displacement law', 'Rayleigh-Jeans law against Planck', 'Wien law against Planck'][CAS] || 'Planck',
    problem: function () {
      var T = p.T;
      var lines = ['Black body at T = ' + fx(T, 3) + ' K,  M(λ) = 2πhc² / (λ⁵ (e^(hc/λkT) − 1)),  h, k, c exact (SI 2019).'];
      if (CAS === 0) return lines.concat(['Integrate x³/(eˣ−1) from 0 to 50 by Simpson, then M = 2πk⁴T⁴/(h³c²) × integral.', 'Exact:  M = σT⁴ = ' + sci(ex0) + ' W/m²']);
      if (CAS === 1) return lines.concat(['Find the maximum of M(λ) by golden-section search.', 'Exact:  λ_max = hc/(k x*) / T, with x* = 4.9651 the root of (x−5)eˣ+5 = 0.', 'Exact value = ' + sci(ex0) + ' m']);
      if (CAS === 2) return lines.concat(['At the peak found, divide the Rayleigh-Jeans value 2πckT/λ⁴ by Planck\'s value.', 'Exact:  (e^(x*) − 1)/x* = ' + sci(ex0)]);
      return lines.concat(['At the peak found, divide Wien\'s law by Planck\'s value.', 'Exact:  1 − e^(−x*) = ' + sci(ex0)]);
    },
    formula: 'σ = 2π⁵k⁴/(15 h³c²) · λ_max T = hc/(4.9651 k)',
  };
  SPEC.cq_fit = {
    quantity: ['slope b', 'exponent b', 'decay time τ', 'curvature c₂'][CAS] || 'parameter', unit: '', digits: 6, nlabel: 'data points N',
    ns: [20, 50, 100, 500, 1000, 3000], tol: 0.01, conv: 'tab', methods: ['Least squares (normal equations)'], xlabel: 'x', ylabel: 'y',
    showCurve: true, legend: ['— true law', '– – fitted curve', '• data'],
    title: ['Straight-line fit', 'Power-law fit', 'Exponential fit', 'Quadratic fit'][CAS] || 'Least-squares fit',
    problem: function () {
      var law = [fx(p.a0, 2) + ' + ' + fx(p.b0, 2) + ' x', fx(p.a0, 2) + ' x^' + fx(p.b0, 2), fx(p.a0, 2) + ' exp(−x/' + fx(p.b0, 2) + ')',
        fx(p.a0, 2) + ' + ' + fx(p.b0, 2) + ' x + ' + fx(p.c0, 2) + ' x²'][CAS];
      var wt = (CAS === 0 || CAS === 3) ? (Math.round(p.wt) === 1 ? 'Weights wᵢ = 1/σᵢ² from the known error of each point.' : 'Unweighted: every point counts equally.')
        : 'Fitted as a straight line in ' + (CAS === 1 ? 'ln y against ln x.' : 'ln y against x.');
      return ['Data y = ' + law + ' at N points, x from ' + fx(p.x0, 1) + ' to ' + fx(p.x1, 1) + ', each y with ' + fx(p.sig * 100, 1) + ' % random error (seed ' + fx(p.seed, 0) + ').',
        wt, 'Solve the normal equations (AᵀWA)c = AᵀWy by Gauss elimination.', 'True value of the parameter = ' + sci(ex0), 'The uncertainty comes from the inverse of AᵀWA.'];
    },
    formula: 'minimise Σ wᵢ (yᵢ − f(xᵢ))² · σ(c) from (AᵀWA)⁻¹',
  };
  //__SPEC_END__
  var ex0 = K.measure(p).exact;                        // the exact answer, for the printed card
  var SP = SPEC[KNAME];
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
  function convOf(mi) { return (SP.convM && SP.convM[mi]) || SP.conv || 'loglog'; }
  ex0 = preview.exact;

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
      (v.bx || []).forEach(function (q) { xs.push(q); }); (v.by || []).forEach(function (q) { ys.push(q); });
      (v.mx || []).forEach(function (q) { xs.push(q); }); (v.my || []).forEach(function (q) { ys.push(q); });
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
      // the bifurcation diagram (scatter) behind everything
      if (v.bx && v.bx.length) {
        x.fillStyle = 'rgba(120,160,210,.55)';
        for (i = 0; i < v.bx.length; i++) x.fillRect(X(v.bx[i]) - 1, Y(v.by[i]) - 1, 2.4, 2.4);
      }
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
      if (SP.trace && px.length > 1) {
        x.strokeStyle = 'rgba(255,194,71,.85)'; x.lineWidth = 1.6; x.beginPath();
        for (i = 0; i < nnodes; i++) { if (i) x.lineTo(X(px[i]), Y(py[i])); else x.moveTo(X(px[i]), Y(py[i])); }
        x.stroke(); nnodes = 0;
      }
      for (i = 0; i < nnodes; i++) {
        if (!isFinite(px[i]) || !isFinite(py[i])) continue;
        if (i % stride !== 0 && i !== nnodes - 1) continue;
        if (SP.stems) {
          x.strokeStyle = 'rgba(255,123,90,.8)'; x.lineWidth = 3; x.beginPath();
          x.moveTo(X(tx(px[i])), Y(Math.max(y0, Math.min(y1, 0)))); x.lineTo(X(tx(px[i])), Y(py[i])); x.stroke();
        }
        x.fillStyle = '#ff7b5a'; x.beginPath(); x.arc(X(tx(px[i])), Y(py[i]), rad, 0, Math.PI * 2); x.fill();
      }
      if (v.mx) for (i = 0; i < v.mx.length; i++) {
        x.strokeStyle = '#59b6ff'; x.lineWidth = 3; x.beginPath(); x.arc(X(v.mx[i]), Y(v.my[i]), 11, 0, Math.PI * 2); x.stroke();
      }
      // legend
      x.font = '500 19px "Public Sans", sans-serif';
      var LG = SP.legend || ['— exact', '– – method', '• nodes used'];
      x.fillStyle = '#59b6ff'; x.fillText(LG[0], P.l + 6, P.t - 38);
      x.fillStyle = '#ffc247'; x.fillText(LG[1], P.l + 250, P.t - 38);
      x.fillStyle = '#ff7b5a'; x.fillText(LG[2], P.l + 480, P.t - 38);
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
      var row = { n: NS[st.ni], mi: st.mi, val: v.val, exact: v.exact, err: v.err, nused: v.nused, unc: v.unc };
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
    st.last = null; preview = compute(st.ni, st.mi); ex0 = preview.exact;
    drawScreen(); S.render();
  }
  function distinctN() { var seen = {}, k = 0; S.rows.forEach(function (r) { if (!seen[r.n]) { seen[r.n] = 1; k++; } }); return k; }
  function orderOf() {
    var C = HK.CALCS.cq_order, R = HK.CALCS.cq_ratio, mine = S.rows.filter(function (r) { return r.mi === st.mi; });
    return convOf(st.mi) === 'linlog' ? R.fn(mine, p) : C.fn(mine, p);
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
        { label: SP.ncol || SP.nlabel, get: function (r) { return String(r.n); } },
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
          + (S.rows.length >= 3 && convOf(b.mi) === 'loglog' ? '. Order measured from log(error) vs log(n): ' + fmt(orderOf(), 2) : '') };
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
        measured_order: S.rows.length >= 3 && convOf(st.mi) !== 'tab' ? orderOf() : null };
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
          u.note(SP.nlabel + ' = ' + NS[st.ni]);
          u.row(u.button('Run — press Enter', function () { runOnce(); }, true, !st.on || S.hand.busy),
            u.button('Run every setting', function () { autoSweep(); }, false, !st.on || S.hand.busy));
          u.live(function () {
            return st.last ? SP.quantity + ' = ' + sci(st.last.val) + (st.last.unc !== undefined ? ' ± ' + sci(st.last.unc) : '') + '  ·  exact ' + sci(st.last.exact)
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

      { id: 'order', title: 'Error and setting', view: 'screen',
        render: function (u) {
          var b = best(), cv = convOf(st.mi), nm = S.rows.filter(function (r) { return r.mi === st.mi; }).length;
          u.h2('How the error depends on the setting');
          if (cv === 'loglog') {
            u.p('A straight line through the points (log n, log error) has a slope of minus the order of the method. '
              + 'That slope is the result of this practical as much as the answer itself.');
            u.formula('error ≈ C n^(−p)', 'so  log(error) = log C − p log n');
            u.live(function () { return 'Measured order p = ' + fmt(orderOf(), 2) + '  (from ' + nm + ' runs of ' + METHODS[st.mi] + ')'; });
          } else if (cv === 'linlog') {
            u.p('This method improves by a fixed factor every step or node, so log(error) against n is a straight line. '
              + 'Its slope gives the factor by which the error is multiplied each time n grows by one.');
            u.formula('error ≈ C r^n', 'so  ln(error) = ln C + n ln r');
            u.live(function () { return 'Error factor per step r = ' + fmt(orderOf(), 3) + '  (from ' + nm + ' runs of ' + METHODS[st.mi] + ')'; });
          } else {
            u.p('For this method the error does not follow a single power or geometric law: it can jump, saturate at round-off, '
              + 'or be exactly zero once the setting is large enough. Read it directly from the table.');
          }
          if (b) u.note('Finest run: ' + METHODS[b.mi] + ' at ' + SP.nlabel + ' = ' + b.n + ' gives '
            + SP.quantity + ' = ' + sci(b.val) + ', error ' + b.err.toExponential(2) + '.');
          u.h3('All runs'); u.table();
          u.p('Below some size the error stops falling because round-off, not the method, is the limit; and a method that is '
            + 'unstable gets worse, not better, as the setting grows.');
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

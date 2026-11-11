/* Prayogshala studio RIG: the computational physics WORKSTATION for the B.Sc. practicals of wave 8 (ug_comp_w8 kernel pack):
   Stirling's formula, frame transformations, vector-field operators, wave groups, graphics operators, the anharmonic radial
   Schrodinger equation, Lennard-Jones molecular dynamics, few-level partition functions, the Maxwell speeds, the specific heat
   of solids, quantum distributions, fractals, flow lines, games, convolution, difference equations, FIR design, geodesics and
   constrained Lagrangian mechanics.
   The bench is the same real workstation as the other computational rigs: desk mat, monitor, keyboard with a live Enter key,
   mouse, tower and the printed METHOD CARD. The student reads the card, switches the machine on, chooses the method and the
   size n, presses Enter - and the MONITOR DRAWS the computation with a particle box, a fractal, a field of arrows, a pole-zero
   plot or a rough profile in the corner. Every number comes from the lab's kernel (HoolaKernels.K[lab.kernel]) at the
   student's settings - the same code the server checks - so the error on the screen is the real error of that run. */
HoolaStudio.define('comp4-workstation', function (S) {
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
  var KB_EV = 1.380649e-23 / 1.602176634e-19;
  var STAT = 'A statistical error falls only as N⁻¹ᐟ²: four times the samples halve the error.';
  var MAT = Math.round(p.what === undefined ? 0 : p.what);
  var SPECS = {
    cw8_fact: function () {
      var arr = CAS === 1, K4 = Math.round(p.frac * 100);
      return {
        title: arr ? 'Arrangements  ln C(N, K),  K = ' + K4 + ' % of N' : 'ln N!  by Stirling’s formula', quantity: arr ? 'ln C(N, K)' : 'ln N!', digits: 6,
        nlabel: 'N', ns: [5, 10, 20, 50, 100, 200], tol: 0.01, showCurve: true, nodes: true,
        methods: ['N ln N − N', '+ ln √(2πN)', '+ 1/(12N)'], xlabel: 'N', ylabel: arr ? 'ln C(N, K)' : 'ln N!',
        problem: [arr ? 'Count the ways to occupy K of N places: C(N, K) = N! / (K! (N − K)!)' : 'Count the arrangements of N different objects: N!',
          'Exact: sum the logarithms  ln 2 + ln 3 + … + ln N  (no overflow)',
          'Stirling: ln N! ≈ N ln N − N + ln √(2πN) + 1/(12N) − …',
          'N! itself overflows double precision beyond N = 170; ln N! never does'],
        formula: arr ? 'ln C(N, K) = ln N! − ln K! − ln (N−K)!' : 'ln N! = Σ ln k  ≈  N ln N − N + ½ ln(2πN) + 1/(12N)',
        expect: 'Each term of Stirling’s series removes the leading error of the one before, so the error falls faster with N for the longer forms.',
        viva: [['ln 100! is about', ['363.7', '100', '4.6'], 0, 'Stirling: 100 ln 100 − 100 + ½ ln(200π) = 363.74.']]
      };
    },
    cw8_frame: function () {
      var nm = ['Galilean boost', 'Lorentz boost (c = 1)', 'Rotation of the axes'][CAS];
      return {
        title: nm + ' from n small steps', quantity: CAS === 2 ? "x′" : "u′", digits: 8, nlabel: 'small steps n', ns: [1, 2, 4, 16, 64, 256], tol: 0.01,
        showCurve: true, nodes: false, methods: ['Generator steps X → X + d G X'], xlabel: 'fraction of the transformation', ylabel: CAS === 2 ? "x′" : "u′",
        problem: [CAS === 2 ? 'A point at (' + fx(p.x, 2) + ', ' + fx(p.y, 2) + '); the axes turn by θ = ' + fx(p.th, 3) + ' rad' : 'A particle with velocity u = ' + fx(p.u, 3) + ' seen from a frame moving at v = ' + fx(p.v, 3),
          CAS === 0 ? 'Galilean: t′ = t, x′ = x − v t, so u′ = u − v' : CAS === 1 ? 'Lorentz: t′ = γ(t − vx), x′ = γ(x − vt), so u′ = (u − v)/(1 − uv)' : 'Rotation: x′ = x cos θ + y sin θ',
          'Built from n equal steps of the generator: d = ' + (CAS === 1 ? 'atanh(v)' : CAS === 2 ? 'θ' : 'v') + ' / n',
          'Exact finite transformation: ' + sci(ex0)],
        formula: CAS === 1 ? 'u′ = (u − v)/(1 − uv) · rapidities add: atanh u′ = atanh u − atanh v' : CAS === 2 ? 'x′ = x cos θ + y sin θ' : 'u′ = u − v',
        expect: CAS === 0 ? 'The Galilean generator squared is zero: n steps give the finite boost exactly, at every n.' : 'The small steps reach the finite transformation only as n grows (Lorentz ~ n⁻², rotation ~ n⁻¹).',
        extras: function (v) { return CAS === 1 ? 't² − x² = ' + fx(v.inv, 6) : CAS === 2 ? 'x² + y² = ' + fx(v.inv, 6) : 't = ' + fx(v.inv, 3); },
        viva: [['The Lorentz velocity addition keeps every speed', ['below c', 'equal to c', 'unchanged'], 0, '(u − v)/(1 − uv) has magnitude below 1 whenever |u|, |v| < 1.']]
      };
    },
    cw8_vfield: function () {
      var nm = ['|∇φ|,  φ = sin x cos y eᶻ', '∇·F,  F = (sin xy, cos yz, eˣᶻ)', '(∇×G)_z,  G = (−eˣ sin y, y sin x, z²)'][CAS];
      return {
        title: nm, quantity: ['|grad φ|', 'div F', '(curl G)z'][CAS] + ' at the point', digits: 7, nlabel: '1/h', ns: [2, 4, 8, 16, 32, 64], tol: 0.01,
        showCurve: true, methods: ['Central difference', 'Forward difference'], xlabel: 'x  (y, z fixed)', ylabel: ['|grad φ|', 'div F', '(curl G)z'][CAS], inset: 'arrows',
        problem: ['Field: ' + nm, 'Point (' + fx(p.x0, 2) + ', ' + fx(p.y0, 2) + ', ' + fx(p.z0, 2) + ');  step h = 1/n',
          'Central: (f(x+h) − f(x−h)) / 2h  ·  Forward: (f(x+h) − f(x)) / h', 'Exact (analytic derivative): ' + sci(ex0)],
        formula: '∇φ = (∂ₓφ, ∂ᵧφ, ∂_zφ) · ∇·F = ∂ₓFₓ + ∂ᵧFᵧ + ∂_zF_z · (∇×G)_z = ∂ₓGᵧ − ∂ᵧGₓ',
        expect: 'Central differences are second order (error ∝ h²), forward differences first order (error ∝ h).',
        viva: [['The curl of a gradient field is', ['zero', 'the divergence', 'the gradient'], 0, 'Mixed partial derivatives are equal, so ∇×∇φ = 0.']]
      };
    },
    cw8_group: function () {
      var cap = CAS === 1;
      return {
        title: cap ? 'Capillary ripples  ω² = (σ/ρ) k³  (anomalous dispersion)' : 'Deep-water waves  ω² = g k  (normal dispersion)', quantity: 'group velocity v_g', digits: 6,
        nlabel: 'k0 / dk  (× 1/' + fx(p.w, 1) + ')', ns: [1, 2, 3, 4, 8, 16], tol: 0.01, showCurve: true, nodes: true, methods: ['Two-wave beat, envelope peak tracked'],
        xlabel: 'x  at t = ' + fx(p.T, 1), ylabel: 'ψ and its envelope',
        problem: ['ψ = cos(k₁x − ω₁t) + cos(k₂x − ω₂t),  k₁,₂ = k0 ∓ dk/2,  k0 = ' + fx(p.k0, 2), 'dk = ' + fx(p.w, 2) + ' k0 / n;  envelope peak located at t = ' + fx(p.T, 2) + ' on a 2000-point grid + parabola',
          'v_g = (peak position) / t;  phase velocity v_p = ω/k = ' + fx(p.k0 > 0 ? (cap ? Math.sqrt(p.s * p.k0) : Math.sqrt(p.g / p.k0)) : 0, 4),
          'Exact: dω/dk = ' + sci(ex0) + (cap ? '  (= 3/2 v_p)' : '  (= v_p / 2)'), 'Model units: g = σ/ρ = 1'],
        formula: 'v_p = ω/k · v_g = dω/dk ≈ Δω/Δk for two waves',
        expect: 'The envelope speed of two waves is Δω/Δk; it tends to dω/dk as Δk → 0, with an error ∝ Δk² (that is ∝ n⁻²).',
        extras: function (v) { return 'v_p = ' + fx(v.vp, 4) + '   v_g/v_p = ' + fx(v.val / v.vp, 3); },
        viva: [['For deep-water waves the group moves at', ['half the speed of the crests', 'twice the speed of the crests', 'the speed of the crests'], 0, 'ω = √(gk) gives dω/dk = ½ ω/k.']]
      };
    },
    cw8_gfx: function () {
      var nm = ['Translation by (' + fx(p.tx, 2) + ', ' + fx(p.ty, 2) + ')', 'Reflection in the line at ' + fx(p.al, 2) + ' rad', 'Shear x → x + ' + fx(p.sh, 2) + ' y', 'Rotation by ' + fx(p.th, 2) + ' rad'][CAS];
      return {
        title: nm + ' of a drawn circle', quantity: MAT === 1 ? 'centroid x of the moved drawing' : 'signed area of the moved drawing', digits: 8, nlabel: 'polygon sides n',
        ns: [6, 12, 24, 48, 96, 192], tol: 0.01, methods: ['Map every vertex, then shoelace'], xlabel: 'x', ylabel: 'y', showCurve: false, linkNodes: true, equal: true,
        legend: [['#59b6ff', '— original'], ['#ff7b5a', '— moved']],
        problem: ['A circle of radius ' + fx(p.r, 2) + ' centred at (' + fx(p.cx0, 2) + ', ' + fx(p.cy0, 2) + '), drawn as a regular n-gon', 'Operator: ' + nm,
          'Read back: ' + (MAT === 1 ? 'the centroid of the moved polygon' : 'its signed area by the shoelace formula'),
          'Reference: ' + (MAT === 1 ? 'the same operator applied to the centre' : 'det(A) π r²') + ' = ' + sci(ex0)],
        formula: 'A = ½ Σ (xᵢ yᵢ₊₁ − xᵢ₊₁ yᵢ) · area′ = det(A) × area · centre′ = A c + t',
        expect: MAT === 1 ? 'The centroid of a regular polygon is its centre for every n: the error stays at round-off.' : 'An n-gon has area (n/2) r² sin(2π/n): the error falls as n⁻². A reflection makes the signed area negative.',
        extras: function (v) { return 'area = ' + fx(v.area, 5) + '   centroid x = ' + fx(v.cxm, 5); },
        viva: [['The determinant of a rotation matrix is', ['1', '0', '−1'], 0, 'A rotation keeps both area and orientation.']]
      };
    },
    cw8_anharm: function () {
      var U = { hw: p.hbarc * Math.sqrt(p.kk / p.mc2), a: Math.sqrt(Math.sqrt(p.hbarc * p.hbarc / (p.mc2 * p.kk))) };
      U.bm = p.bb * U.a * U.a * U.a / U.hw;
      return {
        title: 'u″ = (2m/ħ²)(V − E) u,   V = kr²/2 + br³/3,   b = ' + fx(p.bb, 1) + ' MeV fm⁻³', quantity: MAT === 1 ? '⟨r²⟩ of the ground state' : 'ground-state energy E₀',
        unit: MAT === 1 ? 'fm²' : 'MeV', digits: 6, nlabel: 'grid steps n', ns: [25, 50, 100, 200, 400], tol: 0.01, showCurve: true, nodes: false,
        methods: ['Numerov shooting + bisection'], xlabel: 'r (fm)', ylabel: 'u(r) (normalised to its peak)',
        problem: ['m c² = ' + fx(p.mc2, 1) + ' MeV,  k = ' + fx(p.kk, 1) + ' MeV fm⁻²,  b = ' + fx(p.bb, 1) + ' MeV fm⁻³,  ħc = ' + fx(p.hbarc, 4) + ' MeV fm',
          'Oscillator units: ħω = ' + fx(U.hw, 3) + ' MeV, a = ' + fx(U.a, 4) + ' fm, b′ = ' + fx(U.bm, 4),
          'Numerov from u(0) = 0 out to r = ' + fx(p.rmax, 1) + ' a; bisect E on the sign of u at the end',
          (Math.abs(p.bb) < 1e-12 ? 'Exact: E₀ = 3/2 ħω, ⟨r²⟩ = 3/2 a²' : 'Reference: Rayleigh-Ritz in 18 oscillator states (an independent method)') + ' = ' + sci(ex0),
          'The syllabus expects E₀ between 90 and 110 MeV'],
        formula: 'Numerov: (1 + h²q/12) uₙ₊₁ = 2(1 − 5h²q/12) uₙ − (1 + h²q/12) uₙ₋₁,  q = 2(E − V)',
        expect: 'Numerov is fourth order: halving the step divides the error by about 16.',
        extras: function (v) { return 'E₀ = ' + fx(v.E * v.hw, 4) + ' MeV  (' + fx(v.E, 5) + ' ħω)'; },
        viva: [['Why must u(0) = 0 for an s-wave?', ['R = u/r must stay finite at the origin', 'The potential is zero there', 'To normalise u'], 0, 'If u(0) were not zero, R(r) = u/r would diverge at r = 0.']]
      };
    },
    cw8_ljmd: function () {
      var q = ['⟨|v|⟩ / v_rms', '⟨v_y²⟩ / ⟨v_x²⟩', 'local density (half box)'][MAT];
      return {
        title: 'Lennard-Jones fluid: ' + fx(p.side * p.side, 0) + ' particles in 2-D (reduced units)', quantity: q, digits: 5, nlabel: 'MD steps averaged', ns: [1000, 2000, 4000, 8000, 16000], tol: 0.05,
        showCurve: true, nodes: false, methods: ['Velocity Verlet, cut-and-shifted 12-6 potential'], xlabel: 't (reduced units)', ylabel: q + ' (running)', inset: 'points',
        problem: ['N = ' + fx(p.side * p.side, 0) + ', density ρ = ' + fx(p.rho, 3) + ', start T = ' + fx(p.T0, 2) + ', dt = ' + fx(p.dt, 4) + ', cut-off ' + fx(p.rc, 1) + ' σ',
          MAT === 1 ? 'Start: every velocity along x (v_y = 0)' : 'Start: a square lattice, random velocities (seed ' + fx(p.seed, 0) + ')',
          'Averages over n steps after ' + fx(p.neq, 0) + ' equilibration steps',
          MAT === 0 ? 'Maxwell (2-D): ⟨|v|⟩ / v_rms = √π/2 = ' + sci(ex0) : MAT === 1 ? 'Equipartition: ⟨v_y²⟩ / ⟨v_x²⟩ = 1' : 'Mean density in a fixed half of the box = N/L² = ' + sci(ex0),
          'Model units: ε = σ = m = kB = 1 (SIMULATED, statistical)'],
        formula: 'U = 4ε[(σ/r)¹² − (σ/r)⁶] · velocity Verlet: v += F dt/2, x += v dt, v += F dt/2',
        expect: STAT + ' Molecular-dynamics averages are correlated in time, so they converge slower than independent samples.',
        extras: function (v) { return 'T = ' + fx(v.Tk, 3) + '  drift ' + v.drift.toExponential(1) + (MAT === 2 ? '  Fano ' + fx(v.fano, 2) : ''); },
        viva: [['Equipartition says that in equilibrium', ['every quadratic degree of freedom has kT/2 on average', 'all particles have the same speed', 'the energy is zero'], 0, 'So ⟨v_x²⟩ = ⟨v_y²⟩ = kT/m.']]
      };
    },
    cw8_levels: function () {
      var st = ['Maxwell-Boltzmann (distinguishable)', 'Fermi-Dirac', 'Bose-Einstein'][CAS];
      return {
        title: 'Two particles on ' + fx(p.L, 0) + ' levels: ' + st, quantity: MAT === 1 ? 'entropy S / kB' : 'heat capacity C / kB', digits: 6, nlabel: 'T / h', ns: [2, 4, 8, 16, 32, 64], tol: 0.01,
        showCurve: true, methods: ['Central difference', 'Forward difference'], xlabel: 'kT / ε', ylabel: MAT === 1 ? 'S / kB' : 'C / kB',
        problem: ['Levels 0, ε, 2ε, … (' + fx(p.L, 0) + ' levels), two particles, ' + st + ' counting', 'Z = Σ e^(−E/kT) over the two-particle states; kT = ' + fx(p.T, 3) + ' ε',
          MAT === 1 ? 'S = −dF/dT with F = −kT ln Z, by a finite difference of step h = T/n' : 'C = dU/dT with U = ⟨E⟩, by a finite difference of step h = T/n',
          'Reference (no derivative): ' + (MAT === 1 ? 'S = (U − F)/T' : 'C = (⟨E²⟩ − ⟨E⟩²)/kT²') + ' = ' + sci(ex0), 'Model units: ε = kB = 1'],
        formula: 'Z = Σ e^(−βE) · U = −∂ln Z/∂β · F = −kT ln Z · S = (U − F)/T · C = (⟨E²⟩−⟨E⟩²)/kT²',
        expect: 'A central difference is second order in h, a forward difference first order.',
        extras: function (v) { return 'Z = ' + fx(v.Z, 5) + '   states ' + fx(v.nstates, 0); },
        viva: [['As T → ∞ the entropy of a system with W states tends to', ['kB ln W', 'zero', 'infinity'], 0, 'All W states become equally likely.']]
      };
    },
    cw8_maxwell: function () {
      var nm = (VAR.sample || 'N₂, M = ' + fx(p.M, 4) + ' g/mol, ' + fx(p.T, 0) + ' K');
      return {
        title: 'Maxwell speed distribution: ' + nm, quantity: ['mean speed ⟨v⟩', 'rms speed', 'most probable speed v_p'][MAT], unit: 'm/s', digits: 5, nlabel: 'intervals n',
        ns: MAT === 2 ? [8, 16, 32, 64, 128] : [4, 8, 16, 32, 64], tol: 0.01, methods: [MAT === 2 ? 'Peak of the table + parabola' : 'Simpson’s rule'], xlabel: 'v (m/s)', ylabel: 'f(v) (s/m)', fill: true, vline: true, nodes: true,
        problem: ['f(v) = 4π (m/2πkT)^(3/2) v² e^(−mv²/2kT),  m = M / N_A', 'M = ' + fx(p.M, 4) + ' g/mol,  T = ' + fx(p.T, 1) + ' K;  kB and N_A exact (SI 2019)',
          'Tabulated on n intervals of [0, 6 v_p]', MAT === 2 ? 'v_p: the largest tabulated value, refined by a parabola through its neighbours' : (MAT === 1 ? 'v_rms = √(∫ v² f dv)' : '⟨v⟩ = ∫ v f dv') + ' by Simpson’s rule',
          'Exact: ' + ['√(8kT/πm)', '√(3kT/m)', '√(2kT/m)'][MAT] + ' = ' + sci(ex0) + ' m/s'],
        formula: '⟨v⟩ = √(8kT/πm) · v_rms = √(3kT/m) · v_p = √(2kT/m)',
        expect: 'Simpson’s rule converges fast for this smooth curve; the peak search improves as the table gets finer.',
        viva: [['Lighter molecules at the same temperature move', ['faster', 'slower', 'at the same speed'], 0, 'All speeds scale as 1/√m.']]
      };
    },
    cw8_heatcap: function () {
      var M0x = Math.round(p.method), nm = VAR.sample || 'copper';
      return {
        title: 'Heat capacity of ' + nm + ' at ' + fx(p.T, 0) + ' K', quantity: 'molar heat capacity C', unit: 'J/(mol K)', digits: 5, nlabel: M0x === 2 ? 'Simpson intervals n' : 'T / h',
        ns: [2, 4, 8, 16, 32, 64], tol: 0.01, showCurve: true, methods: ['Dulong-Petit', 'Einstein', 'Debye'], fixedMethod: true, xlabel: 'T (K)', ylabel: 'C (J/mol K)',
        problem: ['θ_D = ' + fx(p.thD, 1) + ' K,  θ_E = ' + fx(p.thE, 1) + ' K (= √(3/5) θ_D),  T = ' + fx(p.T, 1) + ' K,  R = N_A kB = 8.31446 J/(mol K)',
          'Dulong-Petit: C = 3R, as dU/dT of U = 3RT', 'Einstein: C = dU/dT of U = 3R θ_E/(e^(θ_E/T) − 1)  (finite difference, h = T/n)',
          'Debye: C = 9R (T/θ_D)³ ∫₀^(θ_D/T) t⁴eᵗ/(eᵗ−1)² dt  (Simpson, n intervals)',
          'Reference (' + ['3R', 'Einstein’s formula', 'the Debye integral by its exponential series'][M0x] + '): ' + sci(ex0)],
        formula: 'C_E = 3R x² eˣ/(eˣ−1)², x = θ_E/T · C_D = 9R (T/θ_D)³ ∫ t⁴eᵗ/(eᵗ−1)² dt',
        expect: 'All three meet 3R at high temperature; at low T the Einstein value falls exponentially and the Debye value as T³.',
        viva: [['The Debye model improves on Einstein’s at low temperature because', ['it includes low-frequency sound waves', 'it is classical', 'it ignores quantisation'], 0, 'Long-wavelength phonons stay excited at low T, giving the T³ law.']]
      };
    },
    cw8_qdist: function () {
      var M0x = Math.round(p.method), rel = CAS === 1;
      return {
        title: ['Maxwell-Boltzmann', 'Fermi-Dirac', 'Bose-Einstein'][M0x] + ' gas, ' + (rel ? 'ultra-relativistic (E = pc)' : 'non-relativistic') + ', μ = 0, T = ' + fx(p.T, 0) + ' K',
        quantity: 'mean energy per particle ⟨E⟩', unit: 'eV', digits: 6, nlabel: 'Simpson intervals n', ns: [4, 8, 16, 32, 64, 128], tol: 0.01, showCurve: true, nodes: false,
        methods: ['Maxwell-Boltzmann', 'Fermi-Dirac', 'Bose-Einstein'], fixedMethod: true, xlabel: 'E / kT', ylabel: 'occupation f(E)',
        legend: [['#59b6ff', '— this gas: ' + ['MB', 'FD', 'BE'][M0x]], ['#ffc247', '– – MB'], ['#7fe3a1', '·· FD']],
        problem: ['Density of states g(E) ∝ ' + (rel ? 'E²' : 'E^(1/2)') + ';  occupation ' + ['e^(−E/kT)', '1/(e^(E/kT) + 1)', '1/(e^(E/kT) − 1)'][M0x] + '  (μ = 0)',
          '⟨E⟩ = ∫ E g f dE / ∫ g f dE, both by Simpson’s rule after E = kT t²', 'kT = ' + sci(KB_EV * p.T) + ' eV (kB, e exact SI)',
          'Exact: ⟨E⟩/kT = (a+1) X(a+2)/X(a+1), a = ' + (rel ? '2' : '½') + ', X = ' + ['1', 'η (Dirichlet eta)', 'ζ (Riemann zeta)'][M0x], 'Reference: ' + sci(ex0) + ' eV'],
        formula: 'f_MB = e^(−x) · f_FD = 1/(eˣ + 1) · f_BE = 1/(eˣ − 1),  x = (E − μ)/kT',
        expect: 'Simpson’s rule converges very fast here once the peak of the integrand is resolved.',
        extras: function (v) { return '⟨E⟩/kT = ' + fx(v.ratio, 5); },
        viva: [['At the same E/kT the Bose-Einstein occupation is', ['the largest of the three', 'the smallest', 'equal to the others'], 0, '1/(eˣ − 1) > e^(−x) > 1/(eˣ + 1).']]
      };
    },
    cw8_fractal: function () {
      var nm = ['Sierpinski triangle, built deterministically', 'Sierpinski triangle by the chaos game', 'A rough random-walk profile (fractal in nature)'][CAS];
      return {
        title: nm, quantity: 'fractal dimension D', digits: 5, nlabel: ['subdivision rounds', 'points', 'profile steps'][CAS],
        ns: [[3, 4, 5, 6, 7, 8], [1000, 4000, 16000, 64000], [1024, 4096, 16384, 65536]][CAS], tol: 0.02, showCurve: true, nodes: true, dots: true,
        methods: [['Box counting', 'Box counting', 'Variogram (D = 2 − H)'][CAS]], xlabel: CAS === 2 ? 'ln (lag)' : 'ln (1/ε)', ylabel: CAS === 2 ? 'ln (rms height difference)' : 'ln N(ε)',
        inset: CAS === 2 ? 'profile' : 'points',
        problem: [CAS === 0 ? 'Start at one point; each round replaces every point by its images under the 3 maps (x + corner)/2' : CAS === 1 ? 'Chaos game: jump half way to a random corner, again and again (seed ' + fx(p.seed, 0) + ')' : 'A profile of ±1 steps (seed ' + fx(p.seed, 0) + '): a model coastline / skyline',
          CAS === 2 ? 'Variogram: rms of y(i + t) − y(i) at lags t = 1 … 32;  slope = H' : 'Boxes of side ε = 2⁻ᵏ, k = 1 … ' + fx(p.kmax, 0) + ';  slope of ln N against ln(1/ε)',
          'Reference: ' + (CAS === 2 ? 'D = 2 − ½ = 3/2 (Brownian profile)' : 'D = ln 3 / ln 2 = 1.58496 (three copies at half size)')],
        formula: CAS === 2 ? 'σ(t) ∝ t^H,  D = 2 − H' : 'N(ε) ∝ ε^(−D),  D = log N / log s for N copies scaled by 1/s',
        expect: CAS === 0 ? 'The measured slope is exact once the set is finer than the smallest box (6 rounds for k = 6).' : STAT,
        viva: [['A coastline-like profile of dimension 1.5 is', ['rougher than a smooth curve but not area-filling', 'a straight line', 'a filled region'], 0, 'Its dimension lies between 1 (smooth) and 2 (filling the plane).']]
      };
    },
    cw8_flow: function () {
      var nm = ['Pathline of the particle at (x0, y0), t = 0', 'Streakline of dye released at (x0, y0)', 'Streamline of the frozen field at t = T'][CAS];
      return {
        title: nm, quantity: 'y at the end of the ' + ['pathline', 'streak particle', 'streamline'][CAS], digits: 7, nlabel: 'RK4 steps n', ns: [2, 4, 8, 16, 32, 64], tol: 0.01,
        showCurve: false, nodes: true, linkNodes: true, methods: ['Fourth-order Runge-Kutta'], xlabel: 'x', ylabel: 'y',
        legend: [['#59b6ff', '— exact ' + ['pathline', 'streakline', 'streamline'][CAS]], ['#ff7b5a', '• RK4 ' + ['path', 'particle released at τ', 'streamline'][CAS]]],
        problem: ['u = a x,  v = −a y + b cos(ω t);  a = ' + fx(p.a, 2) + ', b = ' + fx(p.b, 2) + ', ω = ' + fx(p.w, 2), 'Start (' + fx(p.x0, 2) + ', ' + fx(p.y0, 2) + ');  T = ' + fx(p.T, 2) + (CAS === 1 ? ', release time τ = ' + fx(p.tau, 2) : CAS === 2 ? ', streamline parameter S = ' + fx(p.S, 2) : ''),
          CAS === 2 ? 'dx/ds = u(x, T): the time is frozen' : 'dx/dt = u(x, t): the field changes as the particle moves', 'Exact (linear equations, closed form): y = ' + sci(ex0), 'Model units'],
        formula: CAS === 2 ? 'y(s) = c/a + (y0 − c/a) e^(−as),  c = b cos(ωT)' : 'y(t) = y_p(t) + (y0 − y_p(t0)) e^(−a(t − t0)),  y_p = b(a cos ωt + ω sin ωt)/(a² + ω²)',
        expect: 'Runge-Kutta is fourth order: halving the step divides the error by about 16.',
        viva: [['Why do the three lines differ here?', ['The flow is unsteady', 'Runge-Kutta is inaccurate', 'The flow is compressible'], 0, 'Only in a steady flow do streamlines, pathlines and streaklines coincide.']]
      };
    },
    cw8_game: function () {
      var zs = CAS === 1;
      return {
        title: zs ? 'Zero-sum game [[' + fx(p.a, 0) + ', ' + fx(p.b, 0) + '], [' + fx(p.c, 0) + ', ' + fx(p.d, 0) + ']] by fictitious play' : 'Hawk-Dove game: V = ' + fx(p.V, 2) + ', C = ' + fx(p.C, 2),
        quantity: zs ? 'frequency of row 1' : 'long-run hawk fraction', digits: 6, nlabel: zs ? 'rounds played' : 'Euler steps', ns: zs ? [100, 1000, 10000, 100000] : [20, 30, 40, 80, 160], tol: 0.01,
        showCurve: true, nodes: false, methods: [zs ? 'Fictitious play' : 'Replicator equation, Euler steps'], xlabel: zs ? 'round' : 't', ylabel: zs ? 'frequency of row 1' : 'hawk fraction p',
        problem: zs ? ['Payoff to the row player [[a, b], [c, d]] = [[' + fx(p.a, 1) + ', ' + fx(p.b, 1) + '], [' + fx(p.c, 1) + ', ' + fx(p.d, 1) + ']]', 'Each round both best-respond to the other’s past frequencies (ties: the first strategy)', 'Minimax (von Neumann): p = (d − c)/(a + d − b − c) = ' + sci(ex0)]
          : ['Hawk vs hawk (V − C)/2, hawk vs dove V, dove vs hawk 0, dove vs dove V/2', 'dp/dt = p(1 − p)(V − Cp)/2 from p0 = ' + fx(p.p0, 2) + ', run to t = ' + fx(p.tend, 0) + ' in n Euler steps', 'Evolutionarily stable state: p* = V/C = ' + sci(ex0)],
        formula: zs ? 'p* = (d − c)/(a + d − b − c),  value = (ad − bc)/(a + d − b − c)' : 'ṗ = p (1 − p) (f_H − f_D) = p(1 − p)(V − Cp)/2',
        expect: zs ? 'Fictitious play converges slowly (Robinson 1951): the error falls roughly as 1/n.' : 'With steps too large the Euler iteration overshoots or oscillates; with enough steps it settles exactly at V/C.',
        extras: zs ? function (v) { return 'column player plays column 1 with ' + fx(v.colfreq, 4); } : null,
        viva: [['At the evolutionarily stable state', ['hawks and doves earn the same payoff', 'only hawks survive', 'only doves survive'], 0, 'If one did better, its share would grow.']]
      };
    },
    cw8_conv: function () {
      var dir = Math.round(p.method) === 1, gate = Math.abs(p.al - 1) < 1e-9 && Math.abs(p.be - 1) < 1e-9;
      var Ly = Math.round(p.Lx) + Math.round(p.Lh) - 1;
      return {
        title: gate ? 'Gate of length ' + fx(p.Lx, 0) + ' convolved with itself' : 'Convolution of ' + fx(p.al, 2) + 'ᵏ (' + fx(p.Lx, 0) + ' samples) with ' + fx(p.be, 2) + 'ᵏ (' + fx(p.Lh, 0) + ' samples)',
        quantity: 'y[' + fx(p.m, 0) + ']', digits: 8, nlabel: 'DFT length N', ns: gate ? [5, 6, 7, 8, 9, 12] : [8, 12, 16, 20, 21, 24, 32], tol: 0.01, showCurve: true, nodes: true, bars: false,
        methods: ['Circular convolution by the DFT', 'Direct convolution sum'], xlabel: 'k', ylabel: 'y[k]',
        legend: [['#59b6ff', '— linear convolution (exact)'], ['#ffc247', '– – computed'], ['#ff7b5a', '• y[m]']],
        problem: ['x[k] = ' + fx(p.al, 2) + 'ᵏ for k < ' + fx(p.Lx, 0) + ',  h[k] = ' + fx(p.be, 2) + 'ᵏ for k < ' + fx(p.Lh, 0), 'Linear convolution y = x * h has ' + Ly + ' samples',
          'DFT method: y = IDFT(DFT(x) · DFT(h)) of length N (circular)', 'Exact y[' + fx(p.m, 0) + '] (finite geometric sum) = ' + sci(ex0)],
        formula: 'y[m] = Σⱼ x[j] h[m − j] · circular: y_N[m] = Σᵣ y[m + rN]',
        expect: 'Below N = ' + Ly + ' the tail of y wraps round (time aliasing) and y[m] is wrong; from N = ' + Ly + ' on it is exact to round-off.',
        viva: [['Zero-padding before a DFT convolution is needed to', ['stop the circular wrap-round', 'make the DFT faster', 'remove noise'], 0, 'With N ≥ Lx + Lh − 1 the circular and linear convolutions agree.']]
      };
    },
    cw8_lti: function () {
      return {
        title: 'y[k] = a₁y[k−1] + a₂y[k−2] + b₀x[k] + b₁x[k−1],  poles ' + fx(p.r, 2) + ' e^(±' + fx(p.th, 2) + 'i)', quantity: MAT === 1 ? 'step response after n samples' : '|H(e^iω0)| from n samples of h',
        digits: 7, nlabel: 'samples n', ns: [8, 16, 32, 64, 160], tol: 0.01, showCurve: true, nodes: false, methods: ['Run the difference equation'], xlabel: 'k', ylabel: MAT === 1 ? 'step response' : 'impulse response h[k]', inset: 'pz',
        problem: ['a₁ = 2r cos θ = ' + fx(2 * p.r * Math.cos(p.th), 4) + ',  a₂ = −r² = ' + fx(-p.r * p.r, 4) + ',  b₀ = ' + fx(p.b0, 2) + ',  b₁ = ' + fx(p.b1, 2),
          'Zero at z = −b₁/b₀ = ' + fx(-p.b1 / p.b0, 3), MAT === 1 ? 'Input: unit step; output after n samples' : 'Input: unit impulse; |Σ h[k] e^(−iω0 k)| at ω0 = ' + fx(p.w0, 3),
          'Exact: ' + (MAT === 1 ? 'H(1) = (b₀ + b₁)/(1 − a₁ − a₂)' : '|B(e^iω0)/A(e^iω0)|') + ' = ' + sci(ex0)],
        formula: 'H(z) = (b₀ + b₁z⁻¹)/(1 − a₁z⁻¹ − a₂z⁻²)',
        expect: 'The truncation error falls as rⁿ: geometric, faster for poles far inside the unit circle.',
        viva: [['A pole at radius 0.95 compared with 0.8 makes the impulse response', ['ring for longer', 'die faster', 'grow'], 0, 'Each sample is multiplied by r; 0.95ⁿ decays slowly.']]
      };
    },
    cw8_fir: function () {
      return {
        title: 'Low-pass FIR by windowing: ω_c = ' + fx(p.wc, 4) + ' rad/sample', quantity: 'half-amplitude frequency', unit: 'rad/sample', digits: 6, nlabel: 'filter length N', ns: [9, 17, 33, 65, 129], tol: 0.01,
        showCurve: true, nodes: true, methods: ['Rectangular window', 'Hann window', 'Hamming window'], fixedMethod: true, xlabel: 'ω (rad/sample)', ylabel: 'amplitude A(ω)',
        legend: [['#59b6ff', '— ideal'], ['#ffc247', '– – designed'], ['#ff7b5a', '• half point']],
        problem: ['Cut-off 1000 Hz at fs = 5 kHz: ω_c = 2π · 1000/5000 = 0.4π rad/sample', 'h[k] = sin(ω_c (k − M/2))/(π (k − M/2)) × window,  M = N − 1',
          'Window: ' + ['rectangular (truncation)', 'Hann 0.5 − 0.5 cos(2πk/M)', 'Hamming 0.54 − 0.46 cos(2πk/M)'][Math.round(p.method)],
          'Half-amplitude point found by a scan and 60 bisections of A(ω) − ½', 'Reference: the design cut-off ω_c = ' + sci(ex0)],
        formula: 'A(ω) = Σ h[k] cos(ω (k − M/2))',
        expect: 'The transition narrows as N grows, so the half-point closes in on ω_c; the windowed designs have far smaller ripple.',
        viva: [['The ripple of a rectangular-window filter near the edge', ['does not shrink as N grows (Gibbs)', 'vanishes for large N', 'is zero'], 0, 'Its height stays about 9 %; only its width shrinks.']]
      };
    },
    cw8_geod: function () {
      var sph = CAS === 1;
      return {
        title: sph ? 'Geodesic on a sphere: (' + fx(p.la1, 0) + '°, ' + fx(p.lo1, 0) + '°) to (' + fx(p.la2, 0) + '°, ' + fx(p.lo2, 0) + '°)' : 'Geodesic in a plane: (' + fx(p.xa, 1) + ', ' + fx(p.ya, 1) + ') to (' + fx(p.xb, 1) + ', ' + fx(p.yb, 1) + ')',
        quantity: 'length of the relaxed path', digits: 7, nlabel: 'path segments n', ns: [4, 8, 16, 32], tol: 0.01, showCurve: false, nodes: true, linkNodes: true,
        methods: ['Relaxation: each point to the midpoint of its neighbours'], xlabel: sph ? 'longitude (deg)' : 'x', ylabel: sph ? 'latitude (deg)' : 'y', equal: !sph,
        legend: [['#59b6ff', '— starting path'], ['#ff7b5a', '— relaxed path']],
        problem: [sph ? 'Unit sphere; the trial path changes latitude and longitude steadily (not a geodesic)' : 'The trial path bulges by ' + fx(p.bump, 2) + ' (not a geodesic)',
          'n pieces; 6n² + 50 sweeps, every inner point moved to the midpoint of its neighbours' + (sph ? ' and back onto the sphere' : ''),
          'Length = the sum of the n chords', 'Exact: ' + (sph ? 'great-circle distance R × angle' : 'straight-line distance') + ' = ' + sci(ex0)],
        formula: sph ? 'd = R · atan2(|A × B|, A · B)' : 'd = √((x_b − x_a)² + (y_b − y_a)²)',
        expect: sph ? 'The chords of the great circle are shorter than its arc by about (angle/n)²/24: second order in 1/n.' : 'In the plane the relaxed path is the straight line exactly.',
        extras: function (v) { return 'start length ' + fx(v.L0, 5) + '  →  ' + fx(v.val, 6); },
        viva: [['The geodesic between two points on a sphere is part of', ['a great circle', 'a parallel of latitude', 'a spiral'], 0, 'A great circle lies in a plane through the centre.']]
      };
    },
    cw8_constr: function () {
      var nm = ['Pendulum held by a Lagrange multiplier', 'Atwood machine', 'Bead on a rotating hoop'][CAS];
      var q = CAS === 1 ? (MAT === 1 ? 'string tension' : 'acceleration') : 'period';
      return {
        title: nm, quantity: q, unit: CAS === 1 ? (MAT === 1 ? 'N' : 'm/s²') : 's', digits: 6, nlabel: 'RK4 steps per period', ns: CAS === 1 ? [4, 8, 16, 32] : [8, 16, 32, 64, 128], tol: 0.01,
        showCurve: true, nodes: false, methods: ['Fourth-order Runge-Kutta'], xlabel: CAS === 0 ? 'x (m)' : 't (s)', ylabel: CAS === 0 ? 'y (m)' : CAS === 1 ? 'y₁ (m)' : 'θ − θ₀ (rad)', equal: CAS === 0,
        problem: [CAS === 0 ? 'L = ' + fx(p.L, 2) + ' m, released at θ0 = ' + fx(p.th0, 1) + '°, g = 9.80665 m/s²;  x″ = −λx, y″ = −λy − g,  λ = (v² − g y)/r²'
          : CAS === 1 ? 'm₁ = ' + fx(p.m1, 2) + ' kg, m₂ = ' + fx(p.m2, 2) + ' kg; constraint y₁ + y₂ = const, multiplier = tension' : 'R = ' + fx(p.R, 2) + ' m, ω = ' + fx(p.w, 1) + ' rad/s;  θ″ = sin θ (ω² cos θ − g/R)',
          CAS === 0 ? 'Period from the zero crossings of x over ' + fx(p.periods, 0) + ' periods' : CAS === 1 ? 'Run for 1 s; a = 2y/t²' + (MAT === 1 ? ',  tension = m₁(g − a)' : '') : 'Small oscillation (' + fx(p.amp, 4) + ' rad) about cos θ₀ = g/(ω²R); period from zero crossings',
          'Exact: ' + (CAS === 0 ? '4√(L/g) K(sin(θ0/2)), K by the AGM' : CAS === 1 ? (MAT === 1 ? '2m₁m₂g/(m₁ + m₂)' : '(m₁ − m₂)g/(m₁ + m₂)') : '2π/(ω sin θ₀)') + ' = ' + sci(ex0)],
        formula: 'd/dt ∂L/∂q̇ − ∂L/∂q = λ ∂f/∂q,   f(q) = 0',
        expect: CAS === 1 ? 'Constant acceleration is integrated exactly by Runge-Kutta: the error is round-off at every step size.' : 'Runge-Kutta is fourth order; the period timing makes the overall error fall about as n⁻⁴.',
        extras: CAS === 0 ? function (v) { return 'constraint drift |r − L|/L = ' + v.drift.toExponential(1); } : null,
        viva: [['A Lagrange multiplier gives', ['the force that keeps the constraint', 'the energy', 'the period'], 0, 'λ ∂f/∂q is the generalised constraint force.']]
      };
    }
  };
  var SP = (SPECS[KNAME] || SPECS.cw8_fact)();
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
  var tlbl = S.label('HOOLA WS-5', { w: 0.07, ratio: 0.18, color: '#9aa0a8' }); tlbl.position.set(-0.03, 0.345, 0.1912); tower.add(tlbl);
  S.contact(0.26, 0.46, 0.66, -0.5, 0.5);

  // ---- the printed method card (A5, lying on the bench)
  var cardLines = SP.problem;
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
    var label = { arrows: 'the field in the x-y plane', points: KNAME === 'cw8_ljmd' ? 'the particles now (box)' : 'the set (unit square)', profile: 'the rough profile', pz: 'poles × and zero o, unit circle' }[SP.inset] || '';
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
    } else if (SP.inset === 'arrows' && v.arrows && v.arrows.length) {
      lo = [1e9, 1e9]; hi = [-1e9, -1e9]; mx = 1e-9;
      for (i = 0; i + 3 < v.arrows.length; i += 4) {
        lo[0] = Math.min(lo[0], v.arrows[i]); hi[0] = Math.max(hi[0], v.arrows[i]); lo[1] = Math.min(lo[1], v.arrows[i + 1]); hi[1] = Math.max(hi[1], v.arrows[i + 1]);
        mx = Math.max(mx, Math.sqrt(v.arrows[i + 2] * v.arrows[i + 2] + v.arrows[i + 3] * v.arrows[i + 3]));
      }
      sc = Math.min(iw / Math.max(hi[0] - lo[0], 1e-9), ih / Math.max(hi[1] - lo[1], 1e-9)) * 0.82;
      ox = ix + iw / 2 - (lo[0] + hi[0]) / 2 * sc; oy = iy + ih / 2 + (lo[1] + hi[1]) / 2 * sc;
      x.strokeStyle = '#5fd0ff'; x.fillStyle = '#5fd0ff'; x.lineWidth = 1.6;
      for (i = 0; i + 3 < v.arrows.length; i += 4) {
        var ax = ox + v.arrows[i] * sc, ay = oy - v.arrows[i + 1] * sc, L2 = 0.11 * sc / mx;
        var bx2 = ax + v.arrows[i + 2] * L2, by2 = ay - v.arrows[i + 3] * L2, an = Math.atan2(by2 - ay, bx2 - ax);
        x.beginPath(); x.moveTo(ax, ay); x.lineTo(bx2, by2); x.stroke();
        x.beginPath(); x.moveTo(bx2, by2); x.lineTo(bx2 - 5 * Math.cos(an - 0.5), by2 - 5 * Math.sin(an - 0.5)); x.lineTo(bx2 - 5 * Math.cos(an + 0.5), by2 - 5 * Math.sin(an + 0.5)); x.closePath(); x.fill();
      }
      x.fillStyle = '#ff7b5a'; x.beginPath(); x.arc(ox + p.x0 * sc, oy - p.y0 * sc, 4, 0, Math.PI * 2); x.fill();
    } else if (SP.inset === 'points' && v.pts && v.pts.length) {
      sc = Math.min(iw, ih) * 0.94; ox = ix + (iw - sc) / 2; oy = iy + (ih + sc) / 2;
      x.strokeStyle = '#1d3349'; x.strokeRect(ox, oy - sc, sc, sc);
      var big = KNAME === 'cw8_ljmd';
      x.fillStyle = big ? '#5fd0ff' : '#ffc247';
      for (i = 0; i + 1 < v.pts.length; i += 2) {
        X = ox + v.pts[i] * sc; Y = oy - v.pts[i + 1] * sc;
        if (big) { x.beginPath(); x.arc(X, Y, Math.max(2, sc / (2.2 * Math.sqrt(v.pts.length / 2) * 1.6)), 0, Math.PI * 2); x.fill(); }
        else x.fillRect(X - 0.8, Y - 0.8, 1.6, 1.6);
      }
      if (big && MAT === 2) { x.strokeStyle = 'rgba(255,123,90,.7)'; x.setLineDash([6, 5]); x.beginPath(); x.moveTo(ox + sc / 2, oy); x.lineTo(ox + sc / 2, oy - sc); x.stroke(); x.setLineDash([]); }
    } else if (SP.inset === 'profile' && v.path_y && v.path_y.length > 1) {
      mn = Math.min.apply(null, v.path_y); mx = Math.max.apply(null, v.path_y); if (mx - mn < 1e-9) mx = mn + 1;
      x.strokeStyle = '#7fe3a1'; x.lineWidth = 1.5; x.beginPath();
      for (i = 0; i < v.path_y.length; i++) { X = ix + v.path_x[i] * iw; Y = iy + ih - (v.path_y[i] - mn) / (mx - mn) * ih; if (i) x.lineTo(X, Y); else x.moveTo(X, Y); }
      x.stroke();
    } else if (SP.inset === 'pz' && v.poles) {
      var R2 = Math.min(iw, ih) * 0.4, cxp = ix + iw / 2, cyp = iy + ih / 2;
      x.strokeStyle = '#2e4760'; x.lineWidth = 1; x.beginPath(); x.moveTo(cxp - R2 * 1.2, cyp); x.lineTo(cxp + R2 * 1.2, cyp); x.moveTo(cxp, cyp - R2 * 1.2); x.lineTo(cxp, cyp + R2 * 1.2); x.stroke();
      x.strokeStyle = '#59b6ff'; x.lineWidth = 2; x.beginPath(); x.arc(cxp, cyp, R2, 0, Math.PI * 2); x.stroke();
      x.strokeStyle = '#ff7b5a'; x.lineWidth = 2.5;
      for (i = 0; i + 1 < v.poles.length; i += 2) {
        X = cxp + v.poles[i] * R2; Y = cyp - v.poles[i + 1] * R2;
        x.beginPath(); x.moveTo(X - 6, Y - 6); x.lineTo(X + 6, Y + 6); x.moveTo(X + 6, Y - 6); x.lineTo(X - 6, Y + 6); x.stroke();
      }
      x.strokeStyle = '#7fe3a1';
      for (i = 0; i + 1 < v.zeros.length; i += 2) { x.beginPath(); x.arc(cxp + v.zeros[i] * R2, cyp - v.zeros[i + 1] * R2, 6, 0, Math.PI * 2); x.stroke(); }
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
      if (SP.equal) {                                   // the same scale on both axes, so a circle looks round
        var sxp = (x1 - x0) / pw, syp = (y1 - y0) / ph, sm = Math.max(sxp, syp), mxc = (x0 + x1) / 2, myc = (y0 + y1) / 2;
        x0 = mxc - sm * pw / 2 * 1.08; x1 = mxc + sm * pw / 2 * 1.08; y0 = myc - sm * ph / 2 * 1.0; y1 = myc + sm * ph / 2 * 1.0;
      }
      var pad = SP.equal ? 0 : (y1 - y0) * 0.12; y0 -= pad; if (!SP.bars) y1 += pad; else { y1 += pad; y0 = Math.min(y0, 0); }
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
        if (SP.linkNodes && nnodes > 1) {
          x.strokeStyle = '#ff7b5a'; x.lineWidth = 3; x.beginPath();
          for (i = 0; i < nnodes; i++) { if (i) x.lineTo(X(tx(px[i])), Y(py[i])); else x.moveTo(X(tx(px[i])), Y(py[i])); }
          x.stroke();
        }
      }
      // legend
      x.font = '500 18px "Public Sans", sans-serif';
      var lg = [['#59b6ff', SP.bars ? '— exact' : '— exact'], [SP.bars ? '#ffc247' : '#ffc247', SP.bars ? '▮ simulation' : '– – method']];
      if (SP.nodes !== false) lg.push(['#ff7b5a', SP.dots ? '• data' : '• points used']);
      if (cy2.length) lg.push(['#7fe3a1', '·· second curve']);
      if (SP.legend) lg = SP.legend;
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
    var C = HK.CALCS.cw8_order;
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

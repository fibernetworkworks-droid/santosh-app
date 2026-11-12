/* Prayogshala studio RIG: the Ph.D. research-technique WORKSTATION of wave 10 (phd_xfilm_w10 kernel pack): X-ray and
   electron methods (Moseley, Rutherford, rocking curves, SAED), scanning probes (AFM, STM), thin films (profilometry,
   Stoney stress, spin coating, e-beam evaporation with a QCM), impedance spectroscopy and microwave interferometry of a
   plasma. Built on the wave 9 characterisation workstation: a real workstation (desk mat, monitor, keyboard with a live
   Enter key, mouse, tower, printed METHOD CARD) with the INSTRUMENT that recorded the data standing beside it, cabled to
   the tower. The student reads the card, switches on, chooses how much of the record the analysis uses and presses
   Enter. Every number comes from the lab's kernel (HoolaKernels.K[lab.kernel]) - the same code the server checks. The
   data are SIMULATED from a hidden sample value: the screen shows the data, the fit and the answer, never the truth. */
HoolaStudio.define('px10-workstation', function (S) {
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
  var SAMPLE = VAR.sample || ((S.lab.bodies || []).filter(function (b) { return b.id === 'smp'; })[0] || {}).text || '';
  var SIMNOTE = 'SIMULATED DATA: the trace is made by the lab\'s kernel from a hidden sample value, with seeded noise. The analysis is real; the instrument is not.';
  var SPECS = {
    px10_moseley: function () {
      var w = Math.round(p.what), mi = Math.round(p.method), edge = w === 2 || mi === 1, k = Math.max(0, Math.min(4, Math.round(p.k)));
      var EL = ['Cu', 'Zn', 'Zr', 'Mo', 'Ag'];
      return {
        title: w === 2 ? 'K absorption edge of ' + EL[k] : 'Moseley\'s law from the ' + (edge ? 'K absorption edges' : 'K-alpha lines'),
        quantity: ['screening constant σ', 'Rydberg energy R', 'K-edge energy of ' + EL[k]][w], unit: ['', 'eV', 'keV'][w], digits: [4, 4, 4][w],
        nlabel: 'detector channels', ns: [256, 512, 1024, 2048, 4096], tol: 0.01, showCurve: true, nodes: w !== 2, dots: true, hidden: true,
        methods: ['K-alpha fluorescence lines', 'K absorption edges'],
        xlabel: w === 2 ? 'photon energy (keV)' : 'atomic number Z', ylabel: w === 2 ? 'transmission I / I₀' : '√(E / eV)',
        legend: w === 2 ? [['#ffc247', '— transmission spectrum']] : [['#ff7b5a', '• Cu, Zn, Zr, Mo, Ag'], ['#ffc247', '– – straight-line fit']],
        used: 'channels in each spectrum',
        xform: w === 2 ? null : function (v) { return { cx: v.fit[0], cy: v.fit[1], px: v.px, py: v.py }; },
        problem: ['Samples: Cu, Zn, Zr, Mo and Ag ' + (edge ? 'foils in the beam of a tungsten tube (transmission spectra, divided by the open beam)' : 'targets excited by the X-ray tube (fluorescence spectra)'),
          'Energy-dispersive detector, ' + fx(p.fw * 1000, 0) + ' eV resolution, 0 – ' + fx(p.Emax, 0) + ' keV',
          edge ? 'Edge: the steepest rise of μt = −ln(I/I₀) (derivative peak, parabola through three points)' : 'Line: the peak of each spectrum (parabola through log counts)',
          edge ? 'Moseley: E_K = R (Z − σ)²; fit √E against Z' : 'Moseley: E(Kα) = (3/4) R (Z − σ)²; fit √E against Z', SIMNOTE],
        formula: edge ? '√E = √R (Z − σ) · R = slope² · σ = −intercept / slope' : '√E = √(3R/4) (Z − σ) · R = (4/3) slope² · σ = −intercept / slope',
        expect: 'More channels put more points across each line or edge, so its energy is read more exactly.',
        extras: function (v) { return 'σ = ' + fx(v.sigma, 3) + '  R = ' + fx(v.R, 2) + ' eV'; },
        instrument: 'X-ray tube and energy-dispersive detector', lab: 'X-ray Physics Laboratory',
        viva: [['Moseley\'s law says √E of a K line grows', ['linearly with Z', 'as Z²', 'as 1/Z'], 0, 'E = (3/4) R (Z − σ)², so √E is linear in Z.'],
          ['The screening constant of the K-alpha line is close to 1 because', ['the one remaining K electron screens the nucleus', 'all the L electrons screen it', 'the nucleus is a point'], 0, 'An L electron dropping into the K hole sees Z minus about one K electron.']]
      };
    },
    px10_ruth: function () {
      var w = Math.round(p.what), al = Math.round(p.Z) !== 79;
      return {
        title: 'Rutherford scattering off ' + (al ? 'aluminium' : 'gold') + ' foil', quantity: w === 1 ? 'nuclear charge Z of the foil' : 'angular exponent m (N ∝ sin⁻ᵐ(θ/2))', unit: '', digits: 4,
        nlabel: 'hours counted at each angle', ncol: 'hours / angle', ns: [1, 4, 16, 64], tol: 0.01, showCurve: true, nodes: true, dots: true, hidden: true,
        methods: [w === 1 ? 'Counts against a gold foil, same geometry' : 'ln N against ln sin(θ/2)'], xlabel: 'ln sin(θ/2)', ylabel: 'ln N (counts)',
        legend: [['#ff7b5a', '• counts at 20° … 150°'], ['#ffc247', '– – straight-line fit']], used: 'angles',
        problem: ['Alphas of ' + fx(p.E, 3) + ' MeV (Am-241), ' + fx(p.N0 / 1e6, 0) + ' × 10⁶ per second on the foil; detector ' + fx(p.dO * 1000, 0) + ' msr',
          'Foil: ' + (SAMPLE || (al ? 'aluminium' : 'gold')) + ',  ' + sci(p.nt) + ' atoms/m²' + (w === 1 ? ';  gold reference ' + sci(p.ntr) + ' atoms/m²' : ''),
          'dσ/dΩ = (zZe²/(16πε₀E))² / sin⁴(θ/2)  (fixed nucleus, z = 2)',
          w === 1 ? 'Z = 79 √⟨(N/nt) / (N_Au/nt_Au)⟩ over the angles' : 'Fit ln N = c − m ln sin(θ/2); the law says m = 4', SIMNOTE],
        formula: 'N = N₀ nt ΔΩ T (zZe²/(16πε₀E))² / sin⁴(θ/2)',
        expect: 'Longer counting gives more counts at every angle; the Poisson spread falls as 1/√N.',
        extras: function (v) { return 'slope ' + fx(v.slope, 4) + '  Z ' + fx(v.Zfit, 2); },
        instrument: 'Vacuum scattering chamber with a silicon detector', lab: 'Nuclear Physics Laboratory',
        viva: [['Rutherford scattering falls with angle as', ['1/sin⁴(θ/2)', '1/θ', 'cos θ'], 0, 'The Coulomb cross-section has sin⁴(θ/2) in the denominator.'],
          ['At a fixed angle the count rate goes as', ['Z²', 'Z', '√Z'], 0, 'The amplitude is proportional to the nuclear charge, the rate to its square.']]
      };
    },
    px10_mwi: function () {
      return {
        title: 'Microwave interferometer: phase shift of the discharge', quantity: 'line-integrated density ∫n dl', unit: 'm⁻²', digits: 4,
        nlabel: 'samples in the record', ns: [100, 250, 500, 1000, 2000, 4000], tol: 0.01, showCurve: true, nodes: false, hidden: true,
        methods: ['Quadrature (I/Q) phase, unwrapped sample by sample'], xlabel: 'time (s)', ylabel: 'unwrapped phase (rad)',
        legend: [['#ffc247', '— probe phase']], used: 'samples',
        problem: ['Sample: ' + (SAMPLE || 'argon discharge') + ', path L = ' + fx(p.L * 100, 1) + ' cm', 'Probe ' + fx(p.f / 1e9, 0) + ' GHz;  cut-off density n_c = ε₀mₑω²/e²',
          'Phase: φ = (2π/λ) L (1 − √(1 − n/n_c)) for a uniform slab', 'Unwrap atan2(Q, I); Δφ = last tenth − first twentieth;  ∫n dl = n_c L (1 − (1 − Δφλ/2πL)²)', SIMNOTE],
        formula: 'Δφ = (2π/λ) L (1 − √(1 − n/n_c)) ≈ rₑ λ ∫n dl',
        expect: 'The phase must move less than half a turn between samples, or the unwrapping loses whole fringes.',
        extras: function (v) { return fx(v.fringes, 2) + ' fringes  approx ' + sci(v.approx); },
        instrument: '35 GHz interferometer (horns across the discharge)', lab: 'Plasma Physics Laboratory',
        viva: [['Why must the probe frequency be well above the plasma frequency?', ['Below it the wave is cut off and reflected', 'It is cheaper', 'The phase would be zero'], 0, 'A wave cannot travel through plasma denser than its cut-off density.'],
          ['Why record both I and Q?', ['They give the phase and its direction without ambiguity', 'To double the noise', 'For the amplitude only'], 0, 'One mixer gives cos φ only, which cannot tell rising from falling phase.']]
      };
    },
    px10_profilo: function () {
      var w = Math.round(p.what);
      return {
        title: 'Stylus profile across the film edge', quantity: w === 1 ? 'roughness Rq' : 'step height', unit: 'nm', digits: w === 1 ? 4 : 3,
        nlabel: 'points in the scan', ns: [250, 500, 1000, 2000, 4000, 8000], tol: 0.01, showCurve: true, nodes: false, hidden: true,
        methods: ['Two-level fit with one common slope'], xlabel: 'position (µm)', ylabel: 'height, levelled (nm)',
        legend: [['#ffc247', '— levelled profile']], used: 'points in the fit',
        problem: ['Sample: ' + (SAMPLE || 'film step') + ',  scan ' + fx(p.Lscan / 1000, 1) + ' mm, height read to ' + fx(p.lc, 2) + ' nm',
          'Fit z = a + h·s(x) + b x to both sides of the edge (s = 0 on the substrate, 1 on the film); keep 10 % of the scan away from the edge and the ends',
          'Step height = h;  roughness Rq = rms of the residuals', SIMNOTE],
        formula: 'z = a + h s(x) + b x · Rq = √(Σ rᵢ² / N)',
        expect: 'More points across the scan sample the roughness more fully, so Rq and the levels settle.',
        extras: function (v) { return 'h ' + fx(v.step, 3) + '  Rq ' + fx(v.Rq, 3) + ' nm'; },
        instrument: 'Stylus profilometer', lab: 'Thin Film Laboratory',
        viva: [['Why fit the two levels with one common slope?', ['The sample tilt is the same on both sides', 'To make the step bigger', 'It removes the roughness'], 0, 'Levelling with one plane leaves the true step between the two levels.']]
      };
    },
    px10_stoney: function () {
      var w = Math.round(p.what), mi = Math.round(p.method);
      return {
        title: 'Film stress from wafer curvature (Stoney)', quantity: w === 1 ? 'thermal-stress slope dσ/dT' : 'residual film stress σ', unit: w === 1 ? 'MPa/K' : 'MPa', digits: w === 1 ? 4 : 2,
        nlabel: mi === 1 ? 'points in each scan' : 'spot readings each time', ns: [5, 20, 80, 320, 1280], nsByMethod: [[5, 20, 80, 320, 1280], [50, 200, 800, 3200]],
        tol: 0.01, showCurve: true, nodes: true, dots: true, hidden: true,
        methods: ['Laser deflection (two parallel beams)', 'Profilometer curvature scan'], xlabel: 'temperature (°C)', ylabel: 'film stress (MPa)',
        legend: [['#ff7b5a', '• stress'], ['#ffc247', '– – fit']], used: 'readings',
        xform: w === 1 ? null : function (v) { return { cx: [v.px[0] - 20, v.px[0] + 20], cy: [v.py[0], v.py[0]], px: v.px, py: v.py }; },
        problem: ['Sample: ' + (SAMPLE || 'film on silicon') + ',  film ' + fx(p.tf, 2) + ' µm on a ' + fx(p.ts, 0) + ' µm Si(100) wafer, M_s = E/(1 − ν) = ' + fx(p.Ms, 1) + ' GPa',
          mi === 1 ? 'Profilometer: z = κx²/2 over ±40 mm; a least-squares parabola gives κ' : 'Laser: beams ' + fx(p.d * 1000, 0) + ' mm apart, screen ' + fx(p.Ls, 1) + ' m away; spot separation D = d + 2Ldκ',
          'Bare wafer first (κ₀), then with the film: Stoney σ = M_s t_s² (κ − κ₀) / (6 t_f)',
          w === 1 ? 'Measure σ at 25, 75, 125, 175 and 225 °C; the slope of σ against T' : 'Report σ at room temperature (negative = compressive)', SIMNOTE],
        formula: 'σ = M_s t_s² (1/R − 1/R₀) / (6 t_f) · dσ/dT = M_f (α_s − α_f)',
        expect: 'More readings average the spot-reading (or height) noise, so the small curvature change is read more exactly.',
        extras: function (v) { return 'κ₀ ' + fx(v.k0, 5) + ' /m'; },
        instrument: mi === 1 ? 'Stylus profilometer (long scan)' : 'Laser curvature system with a hot stage', lab: 'Thin Film Laboratory',
        viva: [['Stoney\'s equation does not need', ['the film\'s elastic constants', 'the substrate thickness', 'the film thickness'], 0, 'Only the substrate\'s biaxial modulus enters; that is why it is so widely used.'],
          ['A film with a larger expansion than silicon, heated, becomes', ['more compressive', 'more tensile', 'unchanged'], 0, 'It wants to expand more than the wafer lets it.']]
      };
    },
    px10_spin: function () {
      var w = Math.round(p.what);
      return {
        title: w === 2 ? 'Thickness map after spinning (Emslie-Bonner-Peck)' : 'Thickness against spin speed (Meyerhofer)',
        quantity: ['thickness at ' + fx(p.w, 0) + ' rpm', 'speed exponent β (h ∝ ω^−β)', 'uniformity (max − min)/mean'][w], unit: ['nm', '', '%'][w], digits: [2, 4, 4][w],
        nlabel: w === 2 ? 'radii in the map' : 'profilometer points per film', ns: w === 2 ? [5, 9, 17, 33, 65] : [5, 20, 80, 320], tol: 0.01, showCurve: true, nodes: w !== 2, dots: true, hidden: true,
        methods: [w === 2 ? 'Ellipsometer map, centre to 0.9 R' : 'log h against log ω'], xlabel: w === 2 ? 'radius (mm)' : 'ln(ω / 1000 rpm)', ylabel: w === 2 ? 'wet-film thickness (µm)' : 'ln(h / nm)',
        legend: w === 2 ? [['#ffc247', '— thickness profile']] : [['#ff7b5a', '• films at 1000 – 6000 rpm'], ['#ffc247', '– – fit']], used: w === 2 ? 'radii' : 'points per film',
        problem: ['Sample: ' + (SAMPLE || 'polymer solution') + ' on a ' + fx(p.R * 2000, 0) + ' mm wafer',
          w === 2 ? 'Flow stage: ∂h/∂t = −(ρω²/3η)(1/r)∂(r²h³)/∂r; a puddle ' + fx(p.a * 100, 0) + ' % thicker at the centre, ' + fx(p.tf, 1) + ' s at ' + fx(p.w, 0) + ' rpm' : 'One film at each speed: 1000, 1500, 2000, 3000, 4000, 6000 rpm; thickness = profilometer step, averaged',
          w === 2 ? 'Uniformity U = (h_max − h_min) / h_mean over 0 – 0.9 R' : 'Meyerhofer (with evaporation): h = K ω^(−1/2); fit ln h against ln ω', SIMNOTE],
        formula: w === 2 ? 'h = h₀ / √(1 + 4Kh₀²t),  r = r₀ (1 + 4Kh₀²t)^(3/4),  K = ρω²/3η' : 'h = (1 − c)(3ηm / 2ρω²)^(1/3),  m ∝ ω^(1/2)  ⇒  h ∝ ω^(−1/2)',
        expect: w === 2 ? 'More radii sample the thickness profile more finely.' : 'More profilometer points per film average the reading noise.',
        extras: function (v) { return w === 2 ? 'U ' + fx(v.unif, 3) + ' %' : 'β ' + fx(v.beta, 4) + '  h(ω) ' + fx(v.hw, 1) + ' nm'; },
        instrument: 'Spin coater and stylus profilometer', lab: 'Thin Film Laboratory',
        viva: [['Doubling the spin speed makes the film about', ['1/√2 as thick', 'half as thick', 'twice as thick'], 0, 'h ∝ ω^(−1/2).'],
          ['During spinning a thick centre thins faster because', ['the outward flow goes as h³', 'it evaporates first', 'it is colder'], 0, 'The flow rate rises steeply with thickness, so the film levels itself.']]
      };
    },
    px10_imp: function () {
      var w = Math.round(p.what), one = Math.round(p.arcs) === 1;
      return {
        title: w === 3 ? 'Arrhenius plot of the bulk resistance' : 'Impedance spectrum (Nyquist plot) at ' + fx(p.T - 273.15, 0) + ' °C',
        quantity: ['bulk resistance R_b', 'grain-boundary resistance R_gb', 'relaxation time τ', 'activation energy Eₐ', 'grain-boundary relaxation time τ_gb'][w], unit: ['Ω', 'Ω', 's', 'eV', 's'][w], digits: 4,
        nlabel: 'points per decade', ns: [3, 5, 10, 20, 40], tol: 0.01, showCurve: true, nodes: w === 3, dots: true, hidden: true, equal: w !== 3,
        methods: ['Peaks of −Z″ against log f'], xlabel: w === 3 ? '1000 / T (1/K)' : "Z' (Ω)", ylabel: w === 3 ? 'ln (R / Ω)' : "−Z'' (Ω)",
        legend: w === 3 ? [['#ff7b5a', '• five temperatures'], ['#ffc247', '– – fit']] : [['#ffc247', '— Nyquist plot']], used: w === 3 ? 'temperatures' : 'points in the spectrum',
        problem: ['Sample: ' + (SAMPLE || 'ionic conductor pellet') + (one ? ' (one arc: R ∥ C)' : ' (two arcs: grains and grain boundaries)'),
          'Spectrum ' + sci(p.fmin) + ' Hz – ' + sci(p.fmax) + ' Hz;  each arc R ∥ C has −Z″ = R/2 at ω = 1/RC',
          'R = 2 × peak of −Z″;  τ = 1 / (2π f_peak)', 'Eₐ: spectra at 250, 275, 300, 325, 350 °C;  ln R against 1/T, Eₐ = k_B × slope', SIMNOTE],
        formula: 'Z = R / (1 + jωRC) · τ = RC = ε₀εᵣ/σ · R = R₀ exp(Eₐ / k_B T)',
        expect: 'More points per decade place each −Z″ peak, and so R and τ, more exactly.',
        extras: function (v) { return w === 3 ? 'Eₐ ' + fx(v.Ea, 4) + ' eV' : v.npeaks + ' arcs  R ' + sci(v.R) + ' Ω  τ ' + sci(v.tau) + ' s'; },
        instrument: 'Impedance analyser with a sample furnace', lab: 'Solid State Ionics Laboratory',
        viva: [['In a Nyquist plot a parallel RC gives', ['a semicircle of diameter R', 'a straight line', 'a point'], 0, 'Z traces a semicircle from R (low f) to 0 (high f).'],
          ['The grain-boundary arc appears at lower frequency because', ['its RC product is larger', 'it has a smaller R', 'it is noise'], 0, 'The thin boundary layer has a large capacitance.']]
      };
    },
    px10_rock: function () {
      var w = Math.round(p.what), bare = Math.round(p.sub) === 1;
      return {
        title: 'ω rocking curve, Si 004, Cu Kα₁', quantity: ['perpendicular strain ε⊥ of the film', 'mosaic spread of the film', 'rocking-curve width of the crystal'][w], unit: ['', '″', '″'][w], digits: [6, 2, 2][w],
        nlabel: 'steps in the ω scan', ns: [600, 1200, 2400, 4800, 9600], tol: 0.01, showCurve: true, nodes: false, hidden: true,
        methods: ['Gaussian fit of each peak (top half)'], xlabel: 'ω − θ_B (degrees)', ylabel: 'counts (normalised)',
        legend: [['#ffc247', '— rocking curve']], used: bare ? 'peak' : 'peaks',
        problem: ['Sample: ' + (SAMPLE || (bare ? 'silicon single crystal' : 'epitaxial film on Si(001)')) + ';  λ = ' + fx(p.lam, 5) + ' nm, d(004) = ' + fx(p.d, 6) + ' nm',
          'θ_B = arcsin(λ/2d);  scan −0.8° … +0.4° about the substrate peak',
          bare ? 'Width: FWHM of the single peak (intrinsic + instrument)' : 'Strain: ε⊥ = −Δθ cot θ_B (Δθ = film − substrate);  mosaic: √(FWHM² − w_f²), w_f = ' + fx(p.wf * 3600, 0) + '″', SIMNOTE],
        formula: 'λ = 2d sin θ · Δd/d = −Δθ cot θ · mosaic = √(FWHM² − w_f²)',
        expect: 'Finer ω steps put more points across each narrow peak.',
        extras: function (v) { return 'θB ' + fx(v.thB, 3) + '°  FWHM(sub) ' + fx(v.wsub, 1) + '″'; },
        instrument: 'High-resolution diffractometer (4-bounce monochromator)', lab: 'X-ray Diffraction Laboratory',
        viva: [['A film peak at lower ω than the substrate means', ['a larger out-of-plane spacing', 'a smaller spacing', 'no strain'], 0, 'Lower Bragg angle = larger d.'],
          ['Mosaic spread is', ['the spread of tilts of the film\'s blocks', 'the film thickness', 'the wavelength spread'], 0, 'Tilted mosaic blocks reflect at slightly different ω and broaden the peak.']]
      };
    },
    px10_qcm: function () {
      var w = Math.round(p.what), k = Math.max(0, Math.min(4, Math.round(p.k)));
      return {
        title: 'E-beam evaporation with a quartz crystal monitor', quantity: w === 1 ? 'film thickness after the run' : 'deposition rate at ' + [1.0, 1.5, 2.0, 2.5, 3.0][k].toFixed(1) + ' kW', unit: w === 1 ? 'nm' : 'nm/s', digits: 4,
        nlabel: 'frequency readings per step', ns: [10, 30, 60, 120, 240], tol: 0.01, showCurve: true, nodes: false, hidden: true,
        methods: ['Sauerbrey: straight line through f against t in each power step'], xlabel: 'time (s)', ylabel: 'crystal frequency (Hz)',
        legend: [['#ffc247', '— QCM frequency']], used: 'readings per step',
        problem: ['Source: ' + (SAMPLE || 'titanium') + ',  film density ' + fx(p.rho / 1000, 3) + ' g/cm³;  tooling factor ' + fx(p.tool, 3),
          'Beam power 1.0, 1.5, 2.0, 2.5, 3.0 kW, ' + fx(p.Tst, 0) + ' s each;  QCM ' + fx(p.f0 / 1e6, 0) + ' MHz AT-cut',
          'Sauerbrey: Δf = −2f₀² Δm / (A √(ρ_q μ_q));  rate = −(df/dt) √(ρ_q μ_q) / (2f₀² ρ) × tooling', SIMNOTE],
        formula: 'Δf = −2 f₀² Δm / (A √(ρ_q μ_q)) · t = Δm / (A ρ)',
        expect: 'More readings in each step fix the slope of f against t better against the counter noise.',
        extras: function (v) { return 'rates ' + v.rates.map(function (q) { return fx(q, 3); }).join(' '); },
        instrument: 'Electron-beam evaporator with a QCM', lab: 'Thin Film Laboratory',
        viva: [['The Sauerbrey equation assumes', ['a thin, rigid film well bonded to the crystal', 'a liquid on the crystal', 'a film thicker than the crystal'], 0, 'Then the added mass simply moves with the quartz.'],
          ['The tooling factor corrects for', ['the crystal and the substrate sitting at different places in the vapour plume', 'the film density', 'the temperature'], 0, 'The crystal sees a different flux from the substrate.']]
      };
    },
    px10_afm: function () {
      var w = Math.round(p.what);
      return {
        title: ['Thermal tune of the cantilever', 'Force-distance curve: pull-off', 'Tapping-mode image: polymer surface', (Math.round(p.h) >= 5 ? 'Contact-mode image: grating step' : 'Tapping-mode image: flake edge')][w],
        quantity: ['spring constant k', 'adhesion force', 'roughness Rq', 'step height'][w], unit: ['N/m', 'nN', 'nm', 'nm'][w], digits: 4,
        nlabel: w === 0 ? 'thermal samples' : w === 1 ? 'points per curve' : 'points per line',
        ns: w === 0 ? [2048, 8192, 32768, 131072, 262144] : [256, 1024, 4096, 8192], tol: 0.01, showCurve: true, nodes: false, hidden: true,
        methods: [['Equipartition: k = k_B T / ⟨z²⟩', 'Pull-off jump × InvOLS × k', 'Plane-levelled rms', 'Two-level fit'][w]],
        xlabel: w <= 1 ? 'piezo position (nm)' : 'position (nm)', ylabel: w <= 1 ? 'deflection (V)' : 'height (nm)',
        legend: [['#ffc247', w === 0 ? '— contact line (InvOLS)' : w === 1 ? '— retract curve' : '— levelled line']], used: w === 0 ? 'samples' : 'points',
        problem: ['Sample: ' + (SAMPLE || 'cantilever') + ';  optical-lever sensitivity InvOLS from the contact part of a force curve on hard silicon',
          w === 0 ? 'Thermal: free cantilever at ' + fx(p.T - 273.15, 0) + ' °C; z = InvOLS × V; k = k_B T / ⟨z²⟩ (no 0.817 correction)' : w === 1 ? 'Retract: the tip sticks until the cantilever pulls off; F = k × InvOLS × ΔV, k = ' + fx(p.k, 2) + ' N/m from its thermal tune' : 'Fit z = a + h s(x) + b x along the line (s = 1 on the ' + (w === 3 ? 'raised part' : 'film') + ')',
          w === 2 ? 'Rq = rms of the residuals' : w === 3 ? 'Step height = h' : 'Report the value from the most data', SIMNOTE],
        formula: ['k = k_B T / ⟨z²⟩', 'F = k · InvOLS · ΔV', 'Rq = √(Σ rᵢ² / N)', 'z = a + h s(x) + b x'][w],
        expect: w === 0 ? 'The variance of a random signal settles as 1/√N: many samples are needed.' : 'Finer sampling reads the jump (or the surface) more exactly.',
        extras: function (v) { return 'InvOLS ' + fx(v.inv, 2) + ' nm/V'; },
        instrument: 'Atomic force microscope', lab: 'Scanning Probe Laboratory',
        viva: [['The thermal method uses', ['equipartition: ½k⟨z²⟩ = ½k_B T', 'Hooke\'s law with a known weight', 'the resonance frequency only'], 0, 'Each mode of the free cantilever carries k_B T / 2 of energy.'],
          ['Tapping mode is preferred on soft polymers because', ['the tip touches only briefly, with little shear', 'it is faster', 'it needs no laser'], 0, 'Intermittent contact avoids dragging and scratching the soft surface.']]
      };
    },
    px10_saed: function () {
      var w = Math.round(p.what), k = Math.round(p.k);
      var R = ['111', '200', '220', '311', '222', '400'][Math.max(0, Math.min(5, k - 1))];
      return {
        title: ['Camera constant from a gold standard', 'Ring pattern of a polycrystalline film', 'Spot pattern of a single-crystal flake', 'Bright-field image: particle sizes'][w],
        quantity: ['camera constant λL', 'd-spacing of the ' + R + ' ring', 'd-spacing (100)', 'mean particle size'][w], unit: ['nm·mm', 'nm', 'nm', 'nm'][w], digits: [4, 5, 5, 3][w],
        nlabel: w === 3 ? 'image pixels across' : 'detector pixels across', ns: w === 3 ? [256, 512, 1024, 2048, 4096] : [512, 1024, 2048, 4096], tol: 0.01,
        showCurve: w === 3, nodes: w !== 3, dots: true, bars: w === 3, hidden: true, equal: w === 2,
        methods: [['R d averaged over four gold rings', 'd = λL / R', 'Mean spot distance → d = λL / R', 'Every particle measured'][w]],
        xlabel: w === 3 ? 'diameter (nm)' : w === 2 ? 'gₓ (mm)' : 'ring number', ylabel: w === 3 ? 'number of particles' : w === 2 ? 'g_y (mm)' : 'ring radius R (mm)',
        legend: w === 3 ? [['#ffc247', '▮ particles']] : [['#ff7b5a', w === 2 ? '• diffraction spots' : '• ring radii']], used: w === 3 ? 'particles' : 'pixels across',
        problem: ['Sample: ' + (SAMPLE || 'gold standard') + ',  ' + fx(p.V / 1000, 0) + ' kV,  detector ' + fx(p.W, 0) + ' mm wide',
          'λ = h / √(2meV(1 + eV/2mc²)) (relativistic electrons);  camera equation R d = λL',
          w === 0 ? 'Gold (fcc, a = ' + fx(p.aG, 5) + ' nm): rings 111, 200, 220, 311 → λL = mean of R·d' : w === 1 ? 'λL from the gold standard first; then each ring of the film: d = λL / R' : w === 2 ? 'Hexagonal flake, [001] zone: six first-order spots, d(100) = λL / ⟨|g|⟩' : 'Bright field: each particle diameter read to the nearest pixel; mean of all',
          SIMNOTE],
        formula: 'R d = λ L · λ = h / √(2meV(1 + eV/2mc²)) · d = a / √(h² + k² + l²)',
        expect: 'A finer pixel reads each radius or diameter more exactly.',
        extras: function (v) { return 'λ ' + (v.lam * 1000).toFixed(4) + ' pm  λL ' + fx(v.cal || 0, 4); },
        instrument: 'Transmission electron microscope', lab: 'Electron Microscopy Laboratory',
        viva: [['A polycrystalline film gives', ['rings', 'one set of spots', 'nothing'], 0, 'Randomly oriented grains spread each reflection round a ring.'],
          ['Why calibrate λL with a gold standard?', ['The camera length changes with the lens settings', 'Gold is cheap', 'λ is unknown'], 0, 'The effective camera length depends on the projector lens currents.']]
      };
    },
    px10_stm: function () {
      var w = Math.round(p.what);
      return {
        title: ['Constant-current line profile', 'I(z) spectroscopy: apparent barrier', 'I(V) spectroscopy: dI/dV'][w],
        quantity: ['lattice spacing along the row', 'apparent barrier height φ', 'surface-state onset E₀'][w], unit: ['nm', 'eV', 'eV'][w], digits: [4, 3, 4][w],
        nlabel: ['points in the line', 'tip heights', 'bias points'][w], ns: [[150, 300, 600, 1200], [20, 50, 100, 200, 400], [100, 200, 400, 800]][w], tol: 0.01,
        showCurve: true, nodes: w === 1, dots: true, hidden: true,
        methods: [['Atom maxima against their number', 'ln I against z', 'dI/dV by a ±40 mV least-squares slope; half-step crossing'][w]],
        xlabel: ['position (nm)', 'tip retraction z (nm)', 'sample bias (V)'][w], ylabel: ['height (nm)', 'ln I (arb.)', 'dI/dV (arb.)'][w],
        legend: w === 1 ? [['#ff7b5a', '• ln I'], ['#ffc247', '– – fit']] : [['#ffc247', w === 2 ? '— dI/dV' : '— line profile']], used: ['atoms', 'heights', 'bias points'][w],
        problem: ['Sample: ' + (SAMPLE || 'gold (111)') + ', in ultra-high vacuum; Pt-Ir tip',
          w === 0 ? 'Line along a close-packed row; atom maxima by a parabola through three points; slope of position against number = spacing' : w === 1 ? 'I = I₀ exp(−2κz), κ = √(2mₑφ)/ħ;  φ = ħ²κ²/(2mₑ)' : 'dI/dV ∝ LDOS;  onset where dI/dV is half way up its step',
          SIMNOTE],
        formula: ['a = Δx / Δ(atom number)', 'I ∝ exp(−2z√(2mₑφ)/ħ)', 'dI/dV ∝ ρ_sample(E_F + eV)'][w],
        expect: 'More points sample the signal more finely and average the noise.',
        extras: function (v) { return w === 0 ? v.npk + ' atoms' : w === 1 ? 'κ ' + sci(v.kappa) + ' /m' : 'onset ' + fx(v.onset, 4) + ' V'; },
        instrument: 'Ultra-high-vacuum STM', lab: 'Scanning Probe Laboratory',
        viva: [['The tunnel current falls by about a factor 10 for each', ['0.1 nm of tip retraction', '1 nm', '1 µm'], 0, '2κ ≈ 22 /nm for φ ≈ 4.5 eV, i.e. a decade per ~0.1 nm.'],
          ['dI/dV at bias V measures', ['the sample\'s local density of states at E_F + eV', 'the tip height', 'the work function'], 0, 'For a flat tip DOS the differential conductance follows the sample LDOS.']]
      };
    px10_pld: function () {
      var w = Math.round(p.what);
      return {
        title: w === 1 ? 'Rocking curve of the PLD film (substrate 002)' : 'RHEED oscillations during pulsed-laser deposition',
        quantity: w === 1 ? 'mosaic spread of the film' : 'growth rate per pulse', unit: w === 1 ? '″' : 'nm/pulse', digits: w === 1 ? 2 : 5,
        nlabel: w === 1 ? 'scan density (192 ω steps each)' : 'RHEED samples per second', ns: w === 1 ? [5, 10, 20, 50] : [2, 5, 10, 20, 50], tol: 0.01,
        showCurve: true, nodes: false, hidden: true,
        methods: [w === 1 ? 'Gaussian fit of each peak (top half)' : 'Oscillation maxima against their number'],
        xlabel: w === 1 ? 'ω − θ_B (degrees)' : 'time (s)', ylabel: w === 1 ? 'counts (normalised)' : 'specular RHEED intensity',
        legend: [['#ffc247', w === 1 ? '— rocking curve' : '— specular spot intensity']], used: w === 1 ? 'peaks' : 'maxima',
        problem: ['Target: ' + (SAMPLE || 'oxide target') + ';  laser ' + fx(p.f, 0) + ' Hz, ' + fx(p.Np, 0) + ' pulses;  unit-cell height c = ' + fx(p.c, 4) + ' nm',
          w === 1 ? 'Rocking curve of the film beside the substrate 002 peak; mosaic = √(FWHM² − w_f²), w_f = ' + fx(p.wf * 3600, 0) + '″' : 'Layer-by-layer growth: one RHEED oscillation per unit cell',
          w === 1 ? 'Crystallinity: the narrower the film peak, the better aligned the film' : 'Period T from the maxima;  pulses per unit cell = T f;  rate = c / (T f)', SIMNOTE],
        formula: w === 1 ? 'mosaic = √(FWHM² − w_f²)' : 'rate = c / (T f)  (nm per pulse)',
        expect: w === 1 ? 'Finer ω steps put more points across the peak.' : 'More samples per second place each maximum more exactly.',
        extras: function (v) { return w === 1 ? 'FWHM(sub) ' + fx(v.wsub, 1) + '″' : fx(v.ppu, 2) + ' pulses per cell, ' + v.nmax + ' maxima'; },
        instrument: 'PLD chamber with RHEED (KrF laser)', lab: 'Thin Film Laboratory',
        viva: [['One RHEED oscillation corresponds to', ['the growth of one monolayer (unit cell)', 'one laser pulse', 'one second'], 0, 'The surface is smoothest when a layer is complete and roughest when half full.'],
          ['Why do the oscillations die away?', ['The surface slowly roughens as several layers grow at once', 'The laser weakens', 'The target runs out'], 0, 'Growth drifts from layer-by-layer towards rougher modes.']]
      };
    }
  };
  var SP = (SPECS[KNAME] || SPECS.px10_moseley)();
  SP.nsFor = function (mi) { return (SP.nsByMethod && SP.nsByMethod[mi]) || SP.ns; };
  var METHODS = SP.methods;
  var M0 = Math.min(METHODS.length - 1, Math.max(0, Math.round(p.method === undefined ? 0 : p.method)));
  var NS = SP.nsFor(M0);
  var HID = !!SP.hidden;
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
    x.fillStyle = '#3c4654'; x.font = '600 32px "Public Sans", sans-serif'; x.fillText(SP.lab || 'Research Laboratory', 50, 134);
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
    wrap(x, HID ? 'Record for every run: n and the answer. Report the answer from the finest data (the largest n).' : SP.scan ? 'Record for every energy: μ/ρ by the mixture rule and NIST\'s table value. Report the value at the lab\'s energy.' : 'Record for every run: the method, n, the answer and the error. Report the answer at the largest n.', 50, y, w - 100, 42);
    x.fillStyle = '#8a9099'; x.font = '500 26px "Public Sans", sans-serif';
    x.fillText('Hoola Prayogshala · ' + (SAMPLE || 'research technique'), 50, h - 48);
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
  function drawInset() {}
  function drawScreen() {
    var v = st.on ? (st.last || preview) : preview;
    if (SP.xform) v = SP.xform(v);
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
      x.font = '600 22px "JetBrains Mono", monospace';
      var rtxt = SP.nlabel + ' = ' + NS[st.ni], rw = x.measureText(rtxt).width;
      x.font = '600 25px "Public Sans", sans-serif';
      while (x.measureText(head).width > W2 - rw - 60 && head.length > 12) head = head.slice(0, -2);
      x.fillText(head, 20, 29);
      x.fillStyle = '#7fe3a1'; x.font = '600 22px "JetBrains Mono", monospace'; x.textAlign = 'right';
      x.fillText(rtxt, W2 - 20, 29); x.textAlign = 'left';
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
        x.strokeStyle = '#ffc247'; x.lineWidth = 3; x.setLineDash(HID && !SP.dots ? [] : [9, 7]); x.beginPath();
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
        var stride = Math.max(1, Math.ceil(px.length / 80)), rad = px.length <= 12 ? 8 : SP.dots ? 3 : (px.length > 40 ? 3.5 : 5.5);
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
          if (!HID) { x.fillStyle = '#86a4c2'; x.fillText('         err ' + r.err.toExponential(2), RX, yy); yy += 32; } else yy += 8;
        }
      });
      var cur = st.last;
      x.fillStyle = '#132231'; x.fillRect(RX - 14, H2 - P.b + 4, colW, 76);
      x.font = '600 22px "JetBrains Mono", monospace';
      if (cur) {
        x.fillStyle = '#7fe3a1'; x.fillText(SP.quantity.split(' at ')[0].split(' (')[0].slice(0, 20) + ' = ' + sci(cur.val), RX, H2 - P.b + 32);
        x.font = '600 19px "JetBrains Mono", monospace'; x.fillStyle = '#ffd083';
        x.fillText(HID ? 'from ' + cur.nused + ' ' + (SP.used || 'points of the fit') : (SP.scan ? 'NIST ' : 'exact ') + sci(cur.exact) + '  err ' + cur.err.toExponential(1), RX, H2 - P.b + 58);
        if (SP.extras) { x.font = '500 15px "JetBrains Mono", monospace'; x.fillStyle = '#86a4c2'; x.fillText(SP.extras(cur).slice(0, 44), RX, H2 - P.b + 76); }
      } else {
        x.fillStyle = '#5d7791'; x.fillText('press ENTER to run', RX, H2 - P.b + 46);
      }
      x.textBaseline = 'alphabetic';
    });
  }

  // ================================================================================= apparatus list
  // ---- the instrument that recorded the trace (characterisation labs only), cabled to the tower
  var ilamp = null;
  if (SP.instrument) {
    var instG = new T.Group(); instG.position.set(-0.6, 0, -0.47); S.scene.add(instG);
    var ibody = S.rounded(0.36, 0.24, 0.32, 0.012, new T.MeshStandardMaterial({ color: 0xe7e9ec, roughness: 0.55 }));
    ibody.position.y = 0.12; instG.add(ibody);
    var ilid = S.rounded(0.3, 0.02, 0.24, 0.006, new T.MeshStandardMaterial({ color: 0xc9cdd3, roughness: 0.5 }));
    ilid.position.set(0, 0.25, -0.01); instG.add(ilid);
    var iplate = S.canvasTex(512, 160, function (x, w, h) {
      x.fillStyle = '#2b3442'; x.fillRect(0, 0, w, h);
      x.fillStyle = '#e8edf3'; x.font = '700 30px "Public Sans", sans-serif'; x.fillText(SP.instrument, 20, 58);
      x.fillStyle = '#9fb0c4'; x.font = '500 22px "Public Sans", sans-serif'; x.fillText('Hoola Instruments · data to the workstation', 20, 110);
    });
    var ifront = new T.Mesh(new T.PlaneGeometry(0.3, 0.094), new T.MeshStandardMaterial({ map: iplate, roughness: 0.6 }));
    ifront.position.set(0, 0.17, 0.161); instG.add(ifront);
    ilamp = new T.Mesh(new T.CircleGeometry(0.006, 16), new T.MeshBasicMaterial({ color: 0x1d4020 }));
    ilamp.position.set(0.13, 0.07, 0.161); instG.add(ilamp);
    var ibtn = S.mesh(new T.CylinderGeometry(0.01, 0.01, 0.008, 20), M.grey); ibtn.rotation.x = Math.PI / 2; ibtn.position.set(-0.12, 0.07, 0.163); instG.add(ibtn);
    S.contact(0.42, 0.38, -0.6, -0.47, 0.5);
    var cab = new T.CatmullRomCurve3([new T.Vector3(-0.42, 0.06, -0.55), new T.Vector3(-0.1, 0.004, -0.62), new T.Vector3(0.3, 0.004, -0.62), new T.Vector3(0.57, 0.08, -0.56)]);
    var cable = S.mesh(new T.TubeGeometry(cab, 40, 0.004, 8, false), new T.MeshStandardMaterial({ color: 0x1c1d20, roughness: 0.7 }));
    S.scene.add(cable);
    S.addApparatus('inst', instG, SP.instrument, 'The instrument that recorded the trace. Its data file is open on the workstation: the analysis is done on the computer. SIMULATED DATA.');
  }

  S.addApparatus('mon', mon, 'Monitor', 'The plot and the run log. Left: the exact curve, what the method built and the nodes it used. Right: every run with its error.');
  S.addApparatus('kbd', kbd, 'Keyboard', 'Enter runs the method at the settings you have chosen. Nothing is computed until you press it.');
  S.addApparatus('mouse', mouse, 'Mouse', 'For the settings on the panel. The method and the step size are the only two choices this practical needs.');
  S.addApparatus('tower', tower, 'Workstation', 'The computer that runs the method. The same code is used for the check, so the error on the screen is the real error.');
  S.addApparatus('card', card, 'Method card', 'The printed card: the problem, the available methods and the formulas. Read it before you touch the machine.');
  S.addApparatus('book', S.book.group, 'Lab record book', HID ? 'Every run you keep is written here: n and the answer.' : 'Every run you keep is written here: the method, n, the answer, the reference value and the error.');

  var hudV = S.hudCard('Numerical'), hudE = S.hudCard(HID ? 'Fit points' : 'Reference'), hudErr = S.hudCard(HID ? 'n' : 'Rel. error'), hudN = S.hudCard('Runs');

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
        + (HID ? ' ' + (SP.unit || '') + '.' : ',  error ' + row.err.toExponential(2) + '.'));
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
    return 0;
  }
  function best() {                                  // the run with the smallest error (ties: the larger n)
    var b = null;
    S.rows.forEach(function (r) { if (!b || r.err < b.err || (r.err === b.err && r.n > b.n)) b = r; });
    return b;
  }
  drawScreen();

  function scanRow() {                               // the energy scan: the row at the lab's own energy, else the closest
    var b = null, tgt = Math.round(p.n);
    S.rows.forEach(function (r) { if (!b || Math.abs(r.n - tgt) < Math.abs(b.n - tgt)) b = r; });
    return b;
  }
  function finest() {                                // a measurement: the run on the most data points
    var b = null;
    S.rows.forEach(function (r) { if (!b || r.n >= b.n) b = r; });
    return b;
  }
  function pick() { return HID ? finest() : SP.scan ? scanRow() : best(); }
  function maxErr() { var m = 0; S.rows.forEach(function (r) { if (r.err > m) m = r.err; }); return m; }
  var unitS = SP.unit ? ' ' + SP.unit : '';

  var principle = HID
    ? 'A characterisation instrument records a trace; the number in the report comes from analysing it - a fit, a peak, '
      + 'an area, a straight line through part of a plot. This practical is that analysis. ' + SIMNOTE + ' Use more of the '
      + 'recorded points and see how the answer settles. ' + (SP.expect || '')
    : SP.scan
      ? 'A photon cross-section database such as NIST\'s gives the mass attenuation coefficient of every element at a set '
        + 'of energies. A compound or a tissue is built from its elements by the mixture rule - exactly what XCOM does - '
        + 'and values between the tabulated energies are read by log-log interpolation. Scan the energies, build the curve, '
        + 'and compare it with NIST\'s own table for the material. ' + (SP.expect || '')
      : 'A simulation answers a question the algebra cannot, but only to the accuracy of its grid. ' + (SP.expect || '');

  return {
    camera: { pos: [0.72, 0.68, 1.08], look: [0.06, 0.12, -0.3] },
    views: {
      mon: [[0.16, 0.30, 0.16], [0.15, 0.25, -0.42]],
      screen: [[0.15, 0.28, 0.14], [0.15, 0.25, -0.42]],
      kbd: [[0.17, 0.33, 0.2], [0.16, 0.0, -0.09]],
      mouse: [[0.46, 0.22, 0.1], [0.44, 0.0, -0.1]],
      tower: [[0.78, 0.42, 0.22], [0.66, 0.18, -0.46]],
      inst: [[-0.42, 0.42, 0.3], [-0.6, 0.14, -0.47]],
      card: [[-0.13, 0.54, 0.44], [-0.13, 0.0, 0.03]],
      book: [[-0.4, 0.44, 0.52], [-0.5, 0.0, 0.08]],
      bench: [[0.72, 0.68, 1.08], [0.06, 0.12, -0.3]],
    },
    theory: {
      principle: principle,
      formula: SP.title, formulaNote: SP.formula,
      more: HID ? ['The sample value behind the trace is hidden, exactly as a real sample\'s is: the answer is judged only at the end, against the value the trace was made from.',
        'The noise is seeded, so the same settings always give the same trace; a different number of points gives a different draw of the noise.',
        'Change one thing at a time and write down every run before changing anything.']
        : ['The elemental tables and the compound tables are both NIST\'s, fetched for this lab and cited in the sources; nothing is typed in from memory.',
          'Between tabulated energies log μ/ρ is close to a straight line in log E, except across an absorption edge, so interpolation never crosses an edge.',
          'μ = (μ/ρ) ρ gives the linear attenuation coefficient and the half-value layer ln 2 / μ.'],
      precautions: HID ? 'Read the method card before switching on. Record n and the answer of every run. Report the answer from the finest '
        + 'data with no more digits than the runs agree to.' : 'Read the method card before switching on. Record the energy, the mixture-rule value, NIST\'s value and '
        + 'the difference for every energy. Never interpolate across an absorption edge.',
    },
    book: {
      title: 'Expt. — ' + S.lab.title,
      lines: ['Aim: ' + S.lab.aim, 'Problem: ' + SP.title + (SAMPLE ? ' · ' + SAMPLE : ''),
        HID ? 'Data: ' + (SP.instrument || 'instrument') + ' trace (simulated)' : 'Reference: NIST table for the material',
        'Method: ' + METHODS[M0], 'For each run: ' + SP.nlabel + ', the answer' + (HID ? '.' : ', the reference and the error.')],
      columns: HID ? [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: (SP.ncol || SP.nlabel).slice(0, 18), get: function (r) { return String(r.n); } },
        { label: 'Answer' + (SP.unit ? ' (' + SP.unit + ')' : ''), get: function (r) { return sci(r.val); } }]
        : [{ label: 'S.No', get: function (r, i) { return i + 1; } },
          { label: (SP.ncol || SP.nlabel).slice(0, 14), get: function (r) { return String(r.n); } },
          { label: 'Mixture', get: function (r) { return sci(r.val); } },
          { label: 'NIST', get: function (r) { return sci(r.exact); } },
          { label: 'Rel. diff.', get: function (r) { return r.err.toExponential(2); } }],
    },
    graph: SP.scan ? {
      x: function (r) { return Math.log(r.n) / Math.LN10; }, y: function (r) { return Math.log(r.val) / Math.LN10; },
      xlabel: 'log₁₀ E (keV)', ylabel: 'log₁₀ μ/ρ (cm²/g)',
    } : {
      x: function (r) { return r.n; }, y: function (r) { return r.val; },
      xlabel: SP.nlabel, ylabel: (SP.quantity + (SP.unit ? ' (' + SP.unit + ')' : '')).slice(0, 34), x0: 0,
    },
    result: function (rows) {
      var b = null, i;
      if (HID) { for (i = 0; i < rows.length; i++) if (!b || rows[i].n >= b.n) b = rows[i]; }
      else if (SP.scan) { var tgt = Math.round(p.n); for (i = 0; i < rows.length; i++) if (!b || Math.abs(rows[i].n - tgt) < Math.abs(b.n - tgt)) b = rows[i]; }
      else { for (i = 0; i < rows.length; i++) if (!b || rows[i].err < b.err || (rows[i].err === b.err && rows[i].n > b.n)) b = rows[i]; }
      if (!b) return null;
      return { label: SP.quantity, value: b.val, unit: SP.unit || '', digits: SP.digits, truth: b.exact,
        note: HID ? 'From the finest data: ' + SP.nlabel + ' = ' + b.n + (SAMPLE ? ' · ' + SAMPLE : '') + '. SIMULATED DATA.'
          : 'At ' + b.n + ' keV: mixture rule ' + sci(b.val) + ' cm²/g, NIST table ' + sci(b.exact) + ' cm²/g; largest difference over the scan '
            + (maxErr() * 100).toFixed(2) + ' %.' };
    },
    tol: SP.tol,
    chips: HID ? ['What does this trace show?', 'Why use more points?', 'Check my runs', 'Explain the formula on the card', 'Is this real data?']
      : ['Why does μ/ρ fall with energy?', 'What is the mixture rule?', 'Check my runs', 'Why not interpolate across an edge?', 'What is the half-value layer?'],
    viva: (SP.viva || []).concat(HID ? [['Why is the sample\'s true value not shown during the practical?',
      ['It is what the analysis must find', 'The computer does not know it', 'It changes every run'], 0,
      'A characterisation measures an unknown; seeing the answer first would make the analysis pointless.'],
      ['The data in this practical are', ['simulated from a hidden value with seeded noise', 'downloaded from a real instrument', 'typed in by hand'], 0,
        'The lab says SIMULATED DATA plainly: the trace comes from the kernel, the analysis is real.']]
      : [['The mixture rule adds', ['the mass attenuation coefficients weighted by mass fraction', 'the linear coefficients', 'the densities'], 0,
        'μ/ρ is a cross-section per gram, so each element contributes in proportion to its mass fraction.']]),
    askState: function () {
      var b = pick();
      var o = { problem: SP.title, sample: SAMPLE, kernel: KNAME, method: METHODS[st.mi], workstation_on: st.on,
        setting_n: NS[st.ni], runs_recorded: S.rows.length, last_answer: st.last ? st.last.val : null,
        chosen_run: b ? { n: b.n, value: b.val } : null, simulated_data: HID };
      if (!HID) { o.last_reference = st.last ? st.last.exact : null; o.last_relative_difference = st.last ? st.last.err : null; }
      return o;
    },

    steps: [
      { id: 'card', title: 'The problem', view: 'card',
        render: function (u) {
          u.h2('Read the method card');
          u.p(HID ? 'The instrument has recorded its trace (SIMULATED DATA). The card says what the trace is, how it is analysed and which formula turns the fit into the sample\'s value.'
            : 'The card names the material, its composition source and the rule that builds its attenuation curve from the elements.');
          u.formula(SP.title, SP.formula);
          cardLines.forEach(function (t) { u.p(t); });
          u.task('Switch the workstation on', st.on, st.on ? 'The screen is live' : 'Press the power button under the screen')
            .add(u.button(st.on ? 'On' : 'Switch on', function () { powerOn(); }, !st.on, st.on || S.hand.busy));
          u.next('Next: the runs', st.on);
        },
        ok: function () { return st.on; },
        auto: function () { return powerOn(); } },

      { id: 'runs', title: HID ? 'Analyse the trace' : 'Scan the energies', view: 'screen',
        render: function (u) {
          u.h2(HID ? 'Analyse the trace with more and more of its points' : 'Build the attenuation curve energy by energy');
          u.p(HID ? 'Choose how many points of the recorded trace the analysis uses, then press Enter. The screen shows the data, the fit and the answer.'
            : 'Choose a photon energy and press Enter. The screen draws NIST\'s table for the material (blue), the mixture rule (dashed) and this energy (dot).');
          u.slider(SP.nlabel, 0, NS.length - 1, 1, function () { return st.ni; },
            function (v) { setN(Math.round(v)); }, '', 0);
          u.note(SP.nlabel + ' = ' + NS[st.ni]);
          u.row(u.button('Run — press Enter', function () { runOnce(); }, true, !st.on || S.hand.busy),
            u.button(HID ? 'Run every setting' : 'Scan every energy', function () { autoSweep(); }, false, !st.on || S.hand.busy));
          u.live(function () {
            if (!st.last) return 'No run yet. Press Enter.';
            return HID ? SP.quantity + ' = ' + sci(st.last.val) + unitS + '  ·  ' + st.last.nused + ' ' + (SP.used || 'points of the fit')
              : 'μ/ρ = ' + sci(st.last.val) + ' cm²/g  ·  NIST ' + sci(st.last.exact) + '  ·  difference ' + (st.last.err * 100).toFixed(3) + ' %';
          });
          u.h3('Observation table'); u.table();
          var k = distinctN();
          u.next('Next: the answer', S.rows.length >= 4 && k >= 3);
          if (S.rows.length < 4 || k < 3) u.p(S.rows.length + ' run(s) kept at ' + k + ' different settings. Take at least 4 runs at 3 or more settings of ' + SP.nlabel + '.');
        },
        ok: function () { return S.rows.length >= 4 && distinctN() >= 3; },
        auto: function () { return autoSweep(); } },

      { id: 'order', title: HID ? 'Settled answer' : 'Compare with NIST', view: 'screen',
        render: function (u) {
          var b = pick();
          if (HID) {
            u.h2('How the answer settles');
            u.p('Compare the answers as the number of points grows. Report the one from the finest data, with only the digits on which the last runs agree.');
            if (SP.expect) u.note(SP.expect);
            var rs = S.rows.slice().sort(function (a, c) { return a.n - c.n; });
            if (rs.length >= 2) u.note('Change between the two finest runs: ' + sci(Math.abs(rs[rs.length - 1].val - rs[rs.length - 2].val)) + unitS + '.');
            if (b) u.note('Finest run: ' + SP.nlabel + ' = ' + b.n + ' gives ' + SP.quantity + ' = ' + sci(b.val) + unitS + '.');
          } else {
            u.h2('Mixture rule against NIST\'s table');
            u.p('The largest difference over the scan tells how well the mixture rule reproduces the compound table. The value at the lab\'s energy is the result.');
            u.live(function () { return 'Largest difference over ' + S.rows.length + ' energies: ' + (maxErr() * 100).toFixed(3) + ' %'; });
            if (b) u.note('At ' + b.n + ' keV: μ/ρ = ' + sci(b.val) + ' cm²/g; μ = ' + fx(b.val * (st.last ? st.last.rho : 1), 4) + ' /cm.');
          }
          u.h3('All runs'); u.table();
          u.next('Next: the result', S.rows.length >= 4);
        },
        ok: function () { return S.rows.length >= 4; },
        auto: function () { return Promise.resolve(); } },
    ],

    tick: function (dt) {
      if (st.reveal < 1) st.reveal = Math.min(1, st.reveal + dt * 1.6);
      if (st.reveal < 1) drawScreen();
      glow.intensity = st.on ? 0.5 : 0;
      if (ilamp) ilamp.material.color.setHex(st.on ? 0x49d36a : 0x1d4020);
      var v = st.last;
      hudV.set(v ? sci(v.val) + unitS : '—');
      hudE.set(HID ? (v ? String(v.nused) : '—') : (v ? sci(v.exact) : '—'));
      hudErr.set(HID ? String(NS[st.ni]) : (v ? v.err.toExponential(1) : '—')); hudN.set(String(S.rows.length));
    },
  };

  // the sweep every step's `auto` uses: the same runOnce the Enter key calls, at every setting in turn
  function autoSweep() {
    var pr = powerOn();
    NS.forEach(function (_, i) {
      pr = pr.then(function () { setN(i); return runOnce(true); });
    });
    return pr.then(function () { S.say(HID ? 'Analysed the trace at every setting. Look at how the answer settles.' : 'Scanned every energy. Compare the two curves.'); S.render(); });
  }
});

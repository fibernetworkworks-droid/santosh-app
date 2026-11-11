/* Prayogshala studio RIG: the M.Sc. computational and materials-characterisation WORKSTATION of wave 9
   (pg_comp_w9 kernel pack): photon mass attenuation by the mixture rule from NIST's fetched tables, and the analysis
   of SIMULATED instrument data - a quantum-dot absorption edge (Tauc + Brus), a nitrogen isotherm (BET + Gurvich),
   a DSC scan (Tg, Tm, crystallinity), a TGA curve (DTG steps, mass loss) and a powder diffractogram
   (Williamson-Hall, Scherrer, lattice parameter).
   The bench is a real workstation (desk mat, monitor, keyboard with a live Enter key, mouse, tower, printed METHOD
   CARD); for a characterisation lab the INSTRUMENT that recorded the data stands beside it, cabled to the tower. The
   student reads the card, switches on, chooses how many points of the trace to use and presses Enter. Every number
   comes from the lab's kernel (HoolaKernels.K[lab.kernel]) - the same code the server checks. For a measurement the
   sample's true value is hidden: the screen shows the data, the fit and the answer, never the truth. */
HoolaStudio.define('pc9-workstation', function (S) {
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
    pc9_xcom: function () {
      var nm = ['Water, liquid', 'Bone, cortical (ICRU-44)', 'Tissue, soft (ICRU-44)', 'A-150 tissue-equivalent plastic', 'Lead'][Math.round(p.mat)] || 'Water, liquid';
      var lead = Math.round(p.mat) === 4;
      var ns = [15, 30, 60, 100, 200, 500, 1000, 1250, 2000, 5000, 10000];
      if (ns.indexOf(Math.round(p.n)) < 0) { ns.push(Math.round(p.n)); ns.sort(function (a, b) { return a - b; }); }
      return {
        title: 'μ/ρ of ' + nm + ' by the mixture rule', quantity: 'μ/ρ at ' + Math.round(p.n) + ' keV', unit: 'cm²/g', digits: 5,
        nlabel: 'photon energy (keV)', ncol: 'E (keV)', ns: ns, tol: 0.01, showCurve: true, nodes: true, logx: true, scan: true,
        methods: ['Mixture rule Σ wᵢ (μ/ρ)ᵢ, log-log interpolation'], xlabel: 'photon energy (keV)', ylabel: 'log₁₀ μ/ρ (cm²/g)',
        legend: [['#59b6ff', '— NIST compound table'], ['#ffc247', '– – mixture rule'], ['#ff7b5a', '• this energy']],
        problem: ['Material: ' + nm + (lead ? ' (a single element: the mixture has one term)' : ''), 'Data: NIST X-Ray Mass Attenuation Coefficients (Hubbell and Seltzer, NISTIR 5632), elemental tables, fetched for this lab',
          'μ/ρ of a compound = Σ wᵢ (μ/ρ)ᵢ over its elements, wᵢ the fraction by weight',
          'Between tabulated energies, interpolate log μ/ρ linearly in log E', 'Reference: NIST\'s own table for the material'],
        formula: 'μ/ρ = Σ wᵢ (μ/ρ)ᵢ · I = I₀ exp(−(μ/ρ) ρ x) · HVL = ln 2 / μ',
        expect: 'The mixture rule ignores chemical binding, which only matters near absorption edges; above 15 keV it reproduces the compound table to a fraction of a per cent.',
        extras: function (v) { return 'μ = ' + fx(v.mu, 4) + ' /cm   HVL = ' + fx(v.hvl, 3) + ' cm'; },
        lab: 'Radiation Physics Laboratory',
        viva: [['Photons of 1 MeV in water interact mostly by', ['Compton scattering', 'the photoelectric effect', 'pair production'], 0, 'Between about 30 keV and 20 MeV Compton scattering dominates in water.'],
          ['Why does lead have a jump in μ/ρ near 88 keV?', ['The K-shell electrons can be ejected above the K edge', 'Pair production starts', 'Lead melts'], 0, 'Above the K-edge energy a new photoelectric channel opens.']]
      };
    },
    pc9_qd: function () {
      var w = Math.round(p.what);
      return {
        title: 'Tauc plot and the Brus equation', quantity: ['dot radius R', 'blue shift E₁ − Eg', 'optical gap E₁'][w], unit: ['nm', 'eV', 'eV'][w], digits: [3, 4, 4][w],
        nlabel: 'spectrum points', ns: [40, 80, 160, 320, 640], tol: 0.01, showCurve: true, nodes: true, dots: true, hidden: true,
        methods: ['Tauc (direct, allowed): (αE)² against E'], xlabel: 'photon energy E (eV)', ylabel: '(αE)²  (arb.)',
        legend: [['#ff7b5a', '• measured spectrum'], ['#ffc247', '– – straight-line fit']], used: 'points in the Tauc fit',
        problem: ['Sample: ' + (SAMPLE || 'quantum dots'), 'Bulk gap Eg = ' + fx(p.Eg, 2) + ' eV;  mₑ* = ' + fx(p.me, 3) + ' m₀,  mₕ* = ' + fx(p.mh, 3) + ' m₀;  εᵣ = ' + fx(p.eps, 1),
          'Fit a straight line to the middle of the Tauc plot; its intercept on E is the optical gap E₁',
          'Brus: E₁ = Eg + h²/(8R²)(1/mₑ* + 1/mₕ*) − 1.786 e²/(4πε₀εᵣR); solve for R', SIMNOTE],
        formula: 'E₁ = Eg + h²/(8R²)(1/mₑ + 1/mₕ) − 1.786 e²/(4πε₀εᵣR)',
        expect: 'More points on the edge make the straight-line fit, and so E₁ and R, less sensitive to the detector noise.',
        extras: function (v) { return 'E₁ = ' + fx(v.E0, 4) + ' eV  shift ' + fx(v.shift, 4) + '  R = ' + fx(v.Rfit, 3) + ' nm'; },
        instrument: 'UV-Vis spectrophotometer', lab: 'Nanomaterials Characterisation Laboratory',
        viva: [['Smaller dots absorb at', ['higher photon energy (a blue shift)', 'lower photon energy', 'the bulk gap'], 0, 'Confinement raises the first transition as 1/R².'],
          ['The Coulomb term of the Brus equation', ['lowers the gap, as 1/R', 'raises the gap', 'does not depend on R'], 0, 'The electron-hole attraction lowers the energy and falls off as 1/R.']]
      };
    },
    pc9_bet: function () {
      var w = Math.round(p.what);
      return {
        title: 'BET surface area and Gurvich pore size', quantity: ['specific surface area', 'mean pore diameter'][w], unit: ['m²/g', 'nm'][w], digits: [1, 3][w],
        nlabel: 'isotherm points', ns: [12, 24, 48, 96, 192], tol: 0.01, showCurve: true, nodes: true, dots: true, hidden: true,
        methods: ['BET plot over p/p₀ = 0.05 – 0.30'], xlabel: 'relative pressure p/p₀', ylabel: 'N₂ adsorbed (cm³ STP/g)',
        legend: [['#ff7b5a', '• measured isotherm'], ['#ffc247', '– – BET fit']], used: 'points in the BET range',
        problem: ['Sample: ' + (SAMPLE || 'mesoporous powder') + ', 1 g, nitrogen at 77 K', 'BET: x / (v(1 − x)) = 1/(vₘC) + (C − 1) x /(vₘC),  x = p/p₀',
          'S = vₘ Nₐ σ / 22414,  σ(N₂) = 0.162 nm²', 'Total pore volume from the uptake near p/p₀ = 0.99 (as liquid N₂, 0.808 g/cm³); pore size d = 4Vₚ/S', SIMNOTE],
        formula: 'vₘ = 1/(slope + intercept) · S = vₘ Nₐ σ / 22414 · d = 4 Vₚ / S',
        expect: 'More isotherm points put more points into the BET range and average out the noise.',
        extras: function (v) { return 'vm = ' + fx(v.vm, 2) + '  C = ' + fx(v.C, 0) + '  Vp = ' + fx(v.Vp, 3) + ' cm³/g'; },
        instrument: 'Surface area and pore analyser', lab: 'Nanomaterials Characterisation Laboratory',
        viva: [['The BET equation is usually applied over', ['p/p₀ = 0.05 to 0.30', 'p/p₀ = 0.9 to 1', 'any pressure'], 0, 'Below 0.05 the surface is heterogeneous; above 0.3 multilayers and condensation take over.'],
          ['A large C constant means', ['strong adsorption in the first layer', 'a small surface area', 'large pores'], 0, 'C ~ exp((E₁ − E_L)/RT).']]
      };
    },
    pc9_dsc: function () {
      var w = Math.round(p.what);
      return {
        title: 'DSC heating scan at ' + fx(p.beta, 0) + ' K/min', quantity: ['glass transition Tg', 'melting point Tm', 'crystallinity Xc'][w], unit: ['°C', '°C', ''][w], digits: [2, 2, 4][w],
        nlabel: 'data points', ns: [100, 200, 400, 800, 1600], tol: 0.01, showCurve: true, nodes: false, hidden: true,
        methods: ['Half-height Tg, peak Tm, peak areas for Xc'], xlabel: 'temperature (°C)', ylabel: 'heat flow (W/g), endo up',
        legend: [['#ffc247', '— heat flow']], used: 'points in the trace',
        problem: ['Sample: ' + (SAMPLE || 'polymer') + ', heated at ' + fx(p.beta, 0) + ' K/min', 'Tg: half way between the extrapolated baselines (' + fx(p.gl, 0) + ' – ' + fx(p.gh, 0) + ' °C)',
          'Tm: the maximum of the melting endotherm (' + fx(p.ml, 0) + ' – ' + fx(p.mh, 0) + ' °C)',
          'Xc = (ΔHm − ΔHcc) / ΔH100,  ΔH100 = ' + fx(p.H100, 0) + ' J/g for a 100 % crystalline sample' + (p.dHcc > 0 ? ';  cold crystallisation ' + fx(p.cl, 0) + ' – ' + fx(p.ch, 0) + ' °C' : ''), SIMNOTE],
        formula: 'ΔH = ∫ (heat flow − baseline) dT / β · Xc = (ΔHm − ΔHcc) / ΔH100',
        expect: 'Finer sampling locates the half-height crossing and the peak more exactly and integrates the peaks better.',
        extras: function (v) { return 'Tg ' + fx(v.Tg, 1) + '  Tm ' + fx(v.Tm, 1) + '  ΔHm ' + fx(v.dHm, 1) + ' J/g'; },
        instrument: 'Differential scanning calorimeter', lab: 'Materials Characterisation Laboratory',
        viva: [['A glass transition shows on a DSC trace as', ['a step in the baseline', 'a sharp peak', 'nothing'], 0, 'The specific heat changes at Tg, so the baseline steps.'],
          ['Cold crystallisation is', ['an exotherm on heating a quenched polymer', 'an endotherm', 'the melting'], 0, 'Chains that could not crystallise on quenching do so on heating, releasing heat.']]
      };
    },
    pc9_tga: function () {
      var w = Math.round(p.what), k = Math.round(p.k);
      return {
        title: 'TGA mass curve and its derivative', quantity: ['mass loss of step ' + k, 'DTG peak of step ' + k, 'number of steps'][w], unit: ['%', '°C', ''][w], digits: [3, 2, 0][w],
        nlabel: 'data points', ns: [160, 320, 640, 1280], tol: 0.01, showCurve: true, nodes: false, hidden: true,
        methods: ['DTG peaks, plateaux half way between them'], xlabel: 'temperature (°C)', ylabel: 'mass (%)',
        legend: [['#ffc247', '— mass (%)'], ['#7fe3a1', '·· DTG, scaled']], used: 'steps found',
        problem: ['Sample: ' + (SAMPLE || 'sample') + ', in flowing nitrogen', 'DTG = −dm/dT by central differences; each peak is one decomposition step',
          'Peak temperature: a parabola through the top three DTG points', 'Mass loss of a step: the drop between the plateaux half way to its neighbours', SIMNOTE],
        formula: 'mass loss (%) = 100 Δm / m₀ · stoichiometric loss = 100 × M(lost) / M(sample)',
        expect: 'Finer sampling sharpens the DTG peaks; too fine and the differentiated noise starts to show.',
        extras: function (v) { return 'steps ' + v.nsteps + '  peaks ' + v.peaks.map(function (q) { return fx(q, 0); }).join(', ') + ' °C'; },
        instrument: 'Thermogravimetric analyser', lab: 'Materials Characterisation Laboratory',
        viva: [['The DTG curve is', ['the derivative of mass with temperature', 'the heat flow', 'the mass itself'], 0, 'Its peaks mark where each step loses mass fastest.'],
          ['Copper sulphate pentahydrate loses its water in', ['three steps (2, 2 and 1 molecules)', 'one step', 'five equal steps'], 0, 'The waters are bound in three different sites.']]
      };
    },
    pc9_xrd: function () {
      var w = Math.round(p.what), lat = ['fcc', 'bcc', 'wurtzite'][Math.round(p.lat)] || 'cubic';
      return {
        title: 'Powder XRD: line widths and positions (' + lat + ')', quantity: ['crystallite size (Williamson-Hall)', 'microstrain ε', 'lattice parameter a', 'crystallite size (Scherrer)'][w],
        unit: ['nm', '', 'nm', 'nm'][w], digits: [2, 6, 5, 2][w],
        nlabel: 'points in the scan', ns: [1000, 2000, 4000, 8000], tol: 0.01, showCurve: true, nodes: false, hidden: true,
        methods: [w === 3 ? 'Scherrer on the first line' : w === 2 ? 'Bragg positions, indexed as ' + lat : 'Williamson-Hall plot'], xlabel: '2θ (degrees)', ylabel: 'counts (arb.)',
        legend: [['#ffc247', '— diffractogram']], used: 'lines measured',
        problem: ['Sample: ' + (SAMPLE || 'nanopowder') + ',  Cu Kα₁ λ = ' + fx(p.lam, 5) + ' nm,  scan ' + fx(p.tt0, 0) + '° – ' + fx(p.tt1, 0) + '° 2θ',
          'Instrument width ' + fx(p.bi, 2) + '° (from a standard), taken off each FWHM', 'Williamson-Hall: β cos θ = Kλ/L + 4ε sin θ,  K = ' + fx(p.K, 2),
          'Scherrer: L = Kλ / (β cos θ);  Bragg: λ = 2d sin θ,  a = d √(h² + k² + l²)', SIMNOTE],
        formula: 'β cos θ = Kλ/L + 4ε sin θ · L = Kλ/(β cos θ) · a = d √(h² + k² + l²)',
        expect: 'A finer scan puts more points across each line, so its width and centre are read more exactly.',
        extras: function (v) { return v.nfound + ' lines  L(WH) ' + fx(v.Lwh, 1) + ' nm  ε ' + (v.strain * 1000).toFixed(2) + 'e-3'; },
        instrument: 'Powder X-ray diffractometer', lab: 'Materials Characterisation Laboratory',
        viva: [['In a Williamson-Hall plot the slope gives', ['the microstrain', 'the crystallite size', 'the wavelength'], 0, 'Strain broadening goes as 4ε tan θ, i.e. 4ε sin θ after multiplying by cos θ.'],
          ['Why is the instrument width subtracted?', ['A perfect large crystal still gives lines of that width', 'It is the size', 'It is noise'], 0, 'The diffractometer\'s optics broaden every line; only the excess belongs to the sample.']]
      };
    },
    pc9_tem: function () {
      var w = Math.round(p.what), k = Math.round(p.k), sad = w === 1, sem = /sem/.test(S.lab.id || '');
      return {
        title: sad ? 'Selected-area diffraction: the camera equation' : sem ? 'SEM micrograph: particle diameters' : 'Bright-field image: grain diameters',
        quantity: sad ? 'd-spacing of ring ' + k : w === 2 ? 'spread of the sizes (standard deviation)' : sem ? 'mean particle size' : 'mean grain size', unit: 'nm', digits: sad ? 5 : 3,
        nlabel: sad ? 'detector pixels across' : 'image pixels across', ns: [256, 512, 1024, 2048, 4096], tol: 0.01,
        showCurve: !sad, nodes: sad, bars: !sad, hidden: true,
        methods: [sad ? 'Ring radius → d = λL / R' : 'Every grain measured, diameters averaged'],
        xlabel: sad ? 'ring number' : 'grain diameter (nm)', ylabel: sad ? 'ring radius R (mm)' : 'number of grains',
        legend: sad ? [['#ff7b5a', '• ring radii']] : [['#ffc247', '▮ grains measured']], used: sad ? 'pixels across' : sem ? 'particles measured' : 'grains measured',
        problem: sem ? ['Sample: ' + (SAMPLE || 'nanopowder') + ', secondary-electron image, field of view ' + fx(20 * p.D0, 0) + ' nm',
          'Each particle diameter read to the nearest pixel', 'Mean d̄ = Σ dᵢ / N;  spread σ = √(Σ (dᵢ − d̄)² / N)', 'The histogram is the size distribution', SIMNOTE]
          : ['Sample: ' + (SAMPLE || 'nanopowder') + ',  ' + fx(p.V / 1000, 0) + ' kV,  camera length ' + fx(p.Lc * 1000, 0) + ' mm',
          'λ = h / √(2meV(1 + eV/2mc²)) (relativistic electrons)', 'Diffraction: R d = λ L;  fcc rings 111, 200, 220, 311 …',
          'Bright field: each grain diameter read to the nearest pixel; the mean is the grain size', SIMNOTE],
        formula: 'R d = λ L · λ = h / √(2meV(1 + eV/2mc²)) · d = a / √(h² + k² + l²)',
        expect: 'A finer pixel reads each diameter or ring radius more exactly.',
        extras: function (v) { return sad ? 'λ = ' + (v.lam * 1e12).toFixed(4) + ' pm' : 'mean ' + fx(v.mean, 2) + '  σ ' + fx(v.sd, 2) + '  pixel ' + fx(v.pix, 3) + ' nm'; },
        instrument: sem ? 'Scanning electron microscope' : 'Transmission electron microscope', lab: 'Materials Characterisation Laboratory',
        viva: [['A polycrystalline powder gives in SAED', ['rings', 'a single spot pattern', 'nothing'], 0, 'Many randomly oriented grains spread each reflection round a ring.']]
      };
    },
    pc9_gas: function () {
      var w = Math.round(p.what);
      return {
        title: 'Resistance transient of a gas sensor', quantity: ['sensitivity Ra/Rg', 'response time t90', 'recovery time t90'][w], unit: ['', 's', 's'][w], digits: [3, 2, 2][w],
        nlabel: 'samples in the record', ns: [300, 600, 900, 1800, 3600], tol: 0.01, showCurve: true, nodes: false, hidden: true,
        methods: ['Ra, Rg from the plateaux; t90 by interpolation'], xlabel: 'time (s)', ylabel: 'resistance (kΩ)',
        legend: [['#ffc247', '— sensor resistance']], used: 'samples',
        problem: ['Sample: ' + (SAMPLE || 'oxide film sensor') + ';  gas in at ' + fx(p.t1, 0) + ' s, out at ' + fx(p.t2, 0) + ' s',
          'Ra = mean before the gas;  Rg = mean of the last tenth before it is shut off', 'Sensitivity S = Ra / Rg',
          'Response: t from gas in to 90 % of the change;  recovery: t from gas out back to within 10 % of Ra', SIMNOTE],
        formula: 'S = Ra / Rg · t90 = τ ln 10 for an exponential change',
        expect: 'Faster sampling places the 90 % crossing more exactly.',
        extras: function (v) { return 'Ra ' + fx(v.Ra / 1e3, 1) + ' kΩ  Rg ' + fx(v.Rg / 1e3, 2) + ' kΩ'; },
        instrument: 'Gas-sensing test chamber', lab: 'Nanomaterials Characterisation Laboratory',
        viva: [['Why is the sensor heated?', ['The surface reactions need a few hundred degrees to run fast', 'To dry the air', 'To make it glow'], 0, 'Oxygen adsorption and its reaction with the gas are thermally activated.']]
      };
    },
    pc9_film: function () {
      var w = Math.round(p.what), xrr = w !== 1;
      return {
        title: xrr ? 'X-ray reflectivity: Kiessig fringes' : 'Powder XRD of the film: Scherrer',
        quantity: xrr ? 'film thickness' : 'grain size (Scherrer)', unit: 'nm', digits: 3,
        nlabel: 'points in the scan', ns: xrr ? [500, 1000, 2000, 4000, 8000] : [1000, 2000, 4000, 8000], tol: 0.01, showCurve: true, nodes: false, hidden: true,
        methods: [xrr ? 'sin²θ of the minima as a parabola in their number' : 'Scherrer on the first line'],
        xlabel: xrr ? 'θ (degrees)' : '2θ (degrees)', ylabel: xrr ? 'log₁₀ reflectivity' : 'counts (arb.)',
        legend: [['#ffc247', xrr ? '— reflectivity' : '— diffractogram']], used: xrr ? 'fringe minima' : 'lines measured',
        problem: ['Sample: ' + (SAMPLE || 'sputtered film') + ' on silicon,  Cu Kα₁ λ = ' + fx(p.lam, 5) + ' nm',
          xrr ? 'Fringe minima: sin²θⱼ = θc² + (λ/2d)²(m₀ + j)²,  j = 0, 1, 2 …' : 'Scherrer: L = Kλ / (β cos θ),  K = ' + fx(p.K, 2),
          xrr ? 'Fit a parabola in j: the leading coefficient is (λ/2d)²' : 'Instrument width ' + fx(p.bi, 2) + '° taken off the FWHM', SIMNOTE],
        formula: xrr ? 'sin²θⱼ = θc² + (λ/2d)²(m₀ + j)²' : 'L = Kλ / (β cos θ)',
        expect: 'More points in the scan place each fringe minimum (or line width) more exactly.',
        extras: function (v) { return xrr ? (v.mins || []).length + ' minima from ' + fx((v.mins || [0])[0], 3) + '°' : v.nfound + ' lines'; },
        instrument: 'X-ray reflectometer', lab: 'Thin Film Laboratory',
        viva: [['Thicker films give Kiessig fringes that are', ['closer together', 'further apart', 'the same'], 0, 'The spacing is about λ / 2d.']]
      };
    }
  };
  var SP = (SPECS[KNAME] || SPECS.pc9_xcom)();
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
    if (KNAME === 'pc9_tga' && v.py && v.py.length === v.cx.length) {   // the DTG curve, scaled onto the mass axis
      var mx = 0; v.py.forEach(function (d) { if (d > mx) mx = d; });
      v.cy2 = v.py.map(function (d) { return mx > 0 ? 40 * d / mx : 0; });
    }
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
    x.fillStyle = '#3c4654'; x.font = '600 32px "Public Sans", sans-serif'; x.fillText(SP.lab || 'Computational Physics Laboratory', 50, 134);
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
    x.fillText('Hoola Prayogshala · ' + (SAMPLE || 'standard test problem'), 50, h - 48);
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
    var C = HK.CALCS.cw8_order;
    return C ? C.fn(S.rows, p) : 0;
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

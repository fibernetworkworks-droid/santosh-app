/* Prayogshala studio RIG: the PhD ANALYSIS WORKSTATION of wave 10 (phd_astro_w10 kernel pack): cosmic-ray muon time of
   flight and zenith law, relativistic beta electrons, a Cherenkov threshold, SiPM timing, radio drift scans and the
   Y-factor, Hubble's law, a cluster colour-magnitude diagram, variable-star periods and the numerical Schrodinger
   equation. Derived from the wave-9 workstation (pc9-workstation): the same bench, a new set of methods.
   Original header of that rig follows.
   ---- the M.Sc. computational and materials-characterisation WORKSTATION of wave 9
   (pg_comp_w9 kernel pack): photon mass attenuation by the mixture rule from NIST's fetched tables, and the analysis
   of SIMULATED instrument data - a quantum-dot absorption edge (Tauc + Brus), a nitrogen isotherm (BET + Gurvich),
   a DSC scan (Tg, Tm, crystallinity), a TGA curve (DTG steps, mass loss) and a powder diffractogram
   (Williamson-Hall, Scherrer, lattice parameter).
   The bench is a real workstation (desk mat, monitor, keyboard with a live Enter key, mouse, tower, printed METHOD
   CARD); for a characterisation lab the INSTRUMENT that recorded the data stands beside it, cabled to the tower. The
   student reads the card, switches on, chooses how many points of the trace to use and presses Enter. Every number
   comes from the lab's kernel (HoolaKernels.K[lab.kernel]) - the same code the server checks. For a measurement the
   sample's true value is hidden: the screen shows the data, the fit and the answer, never the truth. */
HoolaStudio.define('pa10-workstation', function (S) {
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
  var SIMNOTE = 'SIMULATED DATA: the data are made by the lab\'s kernel from a hidden value, with seeded noise. The analysis is real; the measurement is not.';
  var SPECS = {
    pa10_tof: function () {
      return {
        title: 'Muon speed by time of flight', quantity: 'muon speed β = v/c', unit: '', digits: 4,
        nlabel: 'muons per separation', ncol: 'muons', ns: [50, 200, 800, 3200, 12800], tol: 0.01, showCurve: true, nodes: true, hidden: true,
        methods: ['Mean delay against separation, straight-line fit'], xlabel: 'paddle separation d (m)', ylabel: 'mean start-stop delay (ns)',
        legend: [['#ff7b5a', '• mean delay at each separation'], ['#ffc247', '– – straight-line fit']], used: 'muons in the fit',
        problem: ['Two scintillator paddles, separation d = 0 to ' + fx(p.dmax, 1) + ' m in ' + Math.round(p.nd) + ' steps', 'Each muon: delay t = t₀ + d / v + timing jitter (σ = ' + fx(p.sig, 2) + ' ns)',
          'Fit the mean delay against d: slope 1/v, intercept t₀ (cables and electronics)', 'β = v / c,  c = 0.299792458 m/ns', SIMNOTE],
        formula: 't̄(d) = t₀ + d / v  ·  β = 1 / (c · slope)',
        expect: 'The error of a mean delay falls as σ / √N, so more muons at each separation make the slope, and β, sharper.',
        extras: function (v) { return 'slope ' + fx(v.slope, 4) + ' ns/m  t₀ ' + fx(v.offset, 3) + ' ns'; },
        instrument: 'Scintillator paddles + TDC', lab: 'Cosmic-ray Laboratory',
        viva: [['Cosmic-ray muons at sea level move at', ['very nearly the speed of light', 'about half the speed of light', 'the speed of sound'], 0, 'Their typical energy of a few GeV is many times their rest energy of 106 MeV.']]
      };
    },
    pa10_zenith: function () {
      var w = Math.round(p.what);
      return {
        title: 'Cosmic-ray telescope: I(θ) = I₀ cosⁿθ', quantity: ['zenith exponent n', 'vertical intensity I₀', 'flux J through a horizontal surface'][w],
        unit: ['', 'm⁻² s⁻¹ sr⁻¹', 'm⁻² s⁻¹'][w], digits: [3, 2, 2][w],
        nlabel: 'minutes at each angle', ncol: 'minutes', ns: [60, 240, 960, 3840, 15360], tol: 0.01, showCurve: true, nodes: true, hidden: true,
        methods: ['Weighted straight line of ln(rate) against ln(cos θ)'], xlabel: 'zenith angle θ (degrees)', ylabel: 'coincidences per minute',
        legend: [['#ff7b5a', '• counted rate'], ['#ffc247', '– – fitted cosⁿθ law']], used: 'minutes of counting',
        problem: ['Telescope: two detectors of area ' + fx(p.A, 3) + ' m², ' + fx(p.D, 2) + ' m apart, efficiency ' + fx(p.eff, 2),
          'Angles 0 to ' + fx(p.amax, 0) + '° in ' + Math.round(p.na) + ' steps;  rate R = ε I₀ cosⁿθ A²/D²',
          'ln R = ln(ε I₀ A²/D²) + n ln cos θ: weight each angle by its counts', 'Flux through a horizontal surface J = 2π I₀ / (n + 2)', SIMNOTE],
        formula: 'R(θ) = ε I₀ (A²/D²) cosⁿθ  ·  J = 2π I₀ / (n + 2)',
        expect: 'Longer counting at each angle shrinks the Poisson error of every point as 1/√N.',
        extras: function (v) { return 'n ' + fx(v.nfit, 3) + '  I₀ ' + fx(v.I0fit, 2) + '  J ' + fx(v.J, 2); },
        instrument: 'Coincidence telescope (2 detectors)', lab: 'Cosmic-ray Laboratory',
        viva: [['Why weight each angle by its counts?', ['The error of ln N is 1/√N, so fewer counts are less certain', 'To count faster', 'It makes n = 2'], 0, 'A weighted fit trusts the well-counted angles more.']]
      };
    },
    pa10_reldyn: function () {
      var w = Math.round(p.what);
      return {
        title: 'Relativistic dynamics of beta electrons', quantity: ['electron rest energy mc²', 'e/m of the electron'][w], unit: ['MeV', '×10¹¹ C/kg'][w], digits: [4, 4][w],
        nlabel: 'electrons per field setting', ncol: 'electrons', ns: [10, 40, 160, 640, 2560], tol: 0.01, showCurve: true, nodes: true, hidden: true,
        methods: ['Magnetic momentum selection with energy measurement'],
        xlabel: w ? 'field B (mT)' : 'kinetic energy T (MeV)', ylabel: w ? 'γv/(Br)  (10¹¹ C/kg)' : '(pc)² − T²  (MeV²)',
        legend: w ? [['#ff7b5a', '• each field setting'], ['#ffc247', '– – mean']] : [['#ff7b5a', '• each field setting'], ['#ffc247', '– – straight line, slope 2mc²']], used: 'electrons measured',
        problem: ['Source: ' + (SAMPLE || 'Sr-90') + ';  orbit radius r = ' + fx(p.r, 3) + ' m;  B = ' + fx(p.Bmin * 1000, 1) + ' to ' + fx(p.Bmax * 1000, 1) + ' mT',
          'Momentum: p = eBr, so pc = c B r (in eV)', 'Speed from the crossed-field selector v = E/B; kinetic energy T from the calibrated detector',
          w ? 'e/m = γ v / (B r),  γ = 1/√(1 − v²/c²)' : '(pc)² − T² = 2 mc² T: the slope of the line is 2mc²', SIMNOTE],
        formula: 'E² = (pc)² + (mc²)²  ⇒  (pc)² − T² = 2mc² T  ·  e/m = γv/(Br)',
        expect: 'More electrons per setting average the detector resolution down as 1/√N.',
        extras: function (v) { return 'mc² ' + fx(v.mfit, 4) + ' MeV  e/m ' + fx(v.em, 4) + 'e11'; },
        instrument: 'Magnetic spectrometer + detector', lab: 'Particle Physics Laboratory',
        viva: [['An electron of pc = 1 MeV has a speed of about', ['0.89 c', '0.5 c', '1.95 c'], 0, 'β = pc / E = 1 / √(1 + 0.511²) = 0.89.']]
      };
    },
    pa10_cher: function () {
      var w = Math.round(p.what);
      return {
        title: 'Cherenkov threshold and light yield', quantity: ['threshold velocity β_th', 'light yield at β = 1'][w], unit: ['', 'p.e./cm'][w], digits: [4, 3][w],
        nlabel: 'pions per momentum', ncol: 'pions', ns: [25, 100, 400, 1600, 6400], tol: 0.01, showCurve: true, nodes: true, hidden: true,
        methods: ['Straight line of photoelectrons against 1/β²'], xlabel: '1 / β²', ylabel: 'mean photoelectrons',
        legend: [['#ff7b5a', '• mean photoelectrons'], ['#ffc247', '– – Frank-Tamm straight line']], used: 'pions counted',
        problem: ['Radiator: ' + (SAMPLE || 'water') + ', thickness ' + fx(p.L, 1) + ' cm;  pions, m = ' + fx(p.mass, 2) + ' MeV/c²',
          'Momentum ' + fx(p.pmin, 0) + ' to ' + fx(p.pmax, 0) + ' MeV/c in ' + Math.round(p.np) + ' steps;  β = p / √(p² + m²)',
          'Frank-Tamm: N = ε · 369.81 · ΔE · L · (1 − 1/(β²n²)) = a + b/β²',
          'n² = −a/b,  β_th = 1/n = √(−b/a),  yield at β = 1 = (a + b)/L', SIMNOTE],
        formula: 'cos θ = 1/(βn)  ·  d²N/dxdE = 369.81 sin²θ  eV⁻¹ cm⁻¹',
        expect: 'More pions at each momentum shrink the Poisson spread of every mean.',
        extras: function (v) { return 'β_th ' + fx(v.bth, 4) + '  n ' + fx(v.nfit, 4) + '  yield ' + fx(v.yld, 2); },
        instrument: 'Cherenkov counter + PMT', lab: 'Particle Detector Laboratory',
        viva: [['The Cherenkov angle in water for β = 1 is about', ['41°', '5°', '90°'], 0, 'cos θ = 1/1.333 gives 41.4°.']]
      };
    },
    pa10_sipm: function () {
      var w = Math.round(p.what), le = Math.round(p.method) === 1;
      return {
        title: w ? 'SiPM photoelectron spectrum' : 'Coincidence time resolution', quantity: w ? 'mean photoelectrons μ' : 'CTR (FWHM)', unit: w ? '' : 'ps', digits: w ? 4 : 1,
        nlabel: 'events', ns: [2500, 5000, 10000, 20000, 40000], tol: 0.01, showCurve: false, nodes: false, bars: true, hidden: true,
        methods: [w ? 'Pedestal fraction, μ = −ln(N₀/N)' : (le ? 'Leading-edge discrimination with walk correction' : 'Constant-fraction discrimination')],
        xlabel: w ? 'charge (photoelectrons)' : 'time difference − mean (ps)', ylabel: 'events',
        legend: [['#ffc247', w ? '▮ charge spectrum' : '▮ time-difference spectrum']], used: 'events',
        problem: ['Detectors: ' + (SAMPLE || 'LYSO with SiPM') + ', a pair viewing back-to-back annihilation photons',
          w ? 'Low light: k ~ Poisson(μ) photoelectrons, charge = k × gain + noise' : 'Pulse rise time ' + fx(p.tr, 2) + ' ns; amplitudes spread from 0.3 to 1 of the photopeak',
          w ? 'Pedestal: charge below half a photoelectron; μ = −ln(N₀/N)' : (le ? 'Leading edge fires at a fixed level: walk tr·L/A, removed by fitting Δt against 1/A₁ − 1/A₂' : 'Constant fraction fires at a fixed fraction of each pulse: no walk'),
          w ? 'Gain from the spacing of the peaks' : 'CTR = 2.355 × standard deviation of the corrected Δt', SIMNOTE],
        formula: w ? 'P(k) = μᵏ e^{−μ} / k!  ⇒  N₀/N = e^{−μ}' : 'CTR = 2.355 · σ(Δt)  ·  walk = tr L / A',
        expect: 'More events make the width (or the pedestal fraction) statistically sharper, as 1/√N.',
        extras: function (v) { return w ? 'N₀ = ' + v.n0 : 'σ ' + fx(v.sd, 2) + ' ps  walk slope ' + fx(v.walk, 4); },
        instrument: 'Scintillator + SiPM pair + digitiser', lab: 'Particle Detector Laboratory',
        viva: [['A constant-fraction discriminator removes', ['amplitude walk', 'noise jitter', 'the cable delay'], 0, 'It fires at the same fraction of every pulse, whatever its height.']]
      };
    },
    pa10_radio: function () {
      var w = Math.round(p.what);
      return {
        title: ['Solar drift scan: beam width', 'Y-factor: system temperature', 'Point-source drift scan: flux density'][w],
        quantity: ['beam FWHM', 'system temperature Tsys', 'flux density S'][w], unit: ['°', 'K', 'Jy'][w], digits: [3, 2, 0][w],
        nlabel: w === 1 ? 'seconds of integration' : 'drift scans averaged', ncol: w === 1 ? 'seconds' : 'scans', ns: [1, 4, 16, 64, 256], tol: 0.01,
        showCurve: true, nodes: true, dots: w !== 1, hidden: true,
        methods: [['Parabola in ln(T − baseline) over the top half', 'Hot and cold loads: Y = P_hot / P_cold', 'Known beam shape on a constant baseline'][w]],
        xlabel: w === 1 ? 'load temperature (K)' : 'time from transit (min)', ylabel: w === 1 ? 'receiver output (K scale)' : 'antenna temperature (K)',
        legend: w === 1 ? [['#ff7b5a', '• cold sky and hot absorber'], ['#ffc247', '– – line through them, crossing at −Trx']] : [['#ff7b5a', '• recorded scan'], ['#ffc247', '– – fit']],
        used: w === 1 ? 'seconds' : 'samples used',
        problem: w === 1 ? ['Hot load: absorber at ' + fx(p.Thot, 0) + ' K;  cold load: sky at ' + fx(p.Tcold, 0) + ' K', 'Y = P_hot / P_cold = (Trx + T_hot) / (Trx + T_cold)',
          'Trx = (T_hot − Y T_cold)/(Y − 1);  Tsys = Trx + T_cold', 'Radiometer noise ΔP/P = 1/√(bandwidth × time), bandwidth ' + fx(p.bw / 1e6, 1) + ' MHz', SIMNOTE]
          : w === 2 ? ['Source: ' + (SAMPLE || 'Cas A') + ', declination ' + fx(p.sdec, 1) + '°;  beam FWHM ' + fx(p.fwhm, 2) + '° (from the solar scan)',
            'Dish ' + fx(p.D, 1) + ' m, aperture efficiency ' + fx(p.eta, 2) + ':  Ae = η π D²/4', 'Fit T = baseline + Ta · exp(−4 ln2 t²/w²) with the known width',
            'S = 2 k Ta / Ae,  1 Jy = 10⁻²⁶ W m⁻² Hz⁻¹', SIMNOTE]
            : ['Source: ' + (SAMPLE || 'Sun') + ', declination ' + fx(p.dec, 1) + '°;  the Sun\'s disc ' + fx(p.ssun, 2) + '° wide',
              'Drift rate 0.25068° of sky per minute × cos δ', 'Fit ln(T − baseline) = a + bt + ct² over the top half: FWHM = 2.355 / √(−2c)',
              'Beam² = (sky FWHM)² − (disc)²', SIMNOTE],
        formula: ['θ_FWHM = 0.25068 · Δt_FWHM · cos δ', 'Trx = (T_hot − Y T_cold)/(Y − 1)', 'S = 2 k Ta / Ae'][w],
        expect: 'Averaging more scans (or integrating longer) lowers the radiometer noise as 1/√n.',
        extras: function (v) { return w === 1 ? 'Y ' + fx(v.Y, 4) + '  Trx ' + fx(v.Trx, 2) + ' K' : w === 2 ? 'Ta ' + fx(v.Ta, 3) + ' K  Ae ' + fx(v.Ae, 2) + ' m²' : 'Δt ' + fx(v.wtime, 2) + ' min  sky ' + fx(v.sky, 3) + '°'; },
        instrument: '2.3 m dish + 1.42 GHz receiver', lab: 'Radio Astronomy Laboratory',
        viva: [['The beam width of a dish is about', ['1.2 λ / D radians', 'D / λ radians', 'λ D'], 0, 'Diffraction: a 2.3 m dish at 21 cm gives about 6°.']]
      };
    },
    pa10_hubble: function () {
      return {
        title: 'Hubble\'s law from galaxy spectra', quantity: 'Hubble constant H₀', unit: 'km/s/Mpc', digits: 2,
        nlabel: 'galaxies', ns: [25, 50, 100, 200, 400, 800], tol: 0.01, showCurve: true, nodes: true, dots: true, hidden: true,
        methods: ['Line redshifts, v = cz, fit through the origin'], xlabel: 'distance (Mpc)', ylabel: 'recession velocity cz (km/s)',
        legend: [['#ff7b5a', '• galaxies'], ['#ffc247', '– – v = H₀ d']], used: 'galaxies',
        problem: ['Spectra: ' + (SAMPLE || 'galaxy spectra') + ';  lines Hα 6562.80, Hβ 4861.33, [O III] 5006.84 Å (rest, air)',
          'z = (λ_obs − λ₀) / λ₀ averaged over the lines;  v = c z (z < 0.1)', 'Distances from a calibrated standard candle, ' + fx(p.dmin, 0) + ' – ' + fx(p.dmax, 0) + ' Mpc',
          'H₀ = Σ v d / Σ d²', SIMNOTE],
        formula: 'v = c z = H₀ d  ·  t_H = 1/H₀',
        expect: 'Peculiar velocities of a few hundred km/s scatter the points; more galaxies average them away.',
        extras: function (v) { return 'farthest: d ' + fx(v.dfar, 0) + ' Mpc, z ' + fx(v.zfar, 4) + '  1/H₀ ' + fx(977.8 / v.val, 2) + ' Gyr'; },
        instrument: 'Archive terminal (galaxy spectra)', lab: 'Astrophysics Data Laboratory',
        viva: [['A Hubble constant of 70 km/s/Mpc gives a Hubble time of about', ['14 Gyr', '1.4 Gyr', '140 Gyr'], 0, '977.8 / 70 = 14.0 Gyr.']]
      };
    },
    pa10_cmd: function () {
      var w = Math.round(p.what);
      return {
        title: 'Cluster colour-magnitude diagram', quantity: ['cluster distance', 'turn-off age'][w], unit: ['pc', 'Gyr'][w], digits: [1, 3][w],
        nlabel: 'stars in the member list', ncol: 'stars', ns: [500, 1000, 2000, 4000, 8000, 16000], tol: 0.01, showCurve: true, nodes: true, dots: true, hidden: true,
        methods: [w ? 'Main-sequence turn-off and the lifetime scaling' : 'Inverse of the mean parallax'], xlabel: 'colour BP − RP (mag)', ylabel: '−G (mag): brighter up',
        legend: [['#ff7b5a', '• members'], ['#ffc247', '– – turn-off level']], used: 'members on the main sequence',
        problem: ['Member list: ' + (SAMPLE || 'open cluster') + ' (parallax, G, BP − RP)', 'Distance d = 1000 / mean parallax (pc, parallax in mas)',
          'Turn-off: brightest main-sequence star;  M_G = G − 5 log₁₀ d + 5;  L/L☉ = 10^(−0.4 (M_G − ' + fx(p.MGsun, 2) + '))',
          'M = L^(1/3.5);  age = 10 Gyr × M^(−2.5)  (scaling relations, an estimate)', SIMNOTE],
        formula: 'd = 1/ϖ  ·  L ∝ M^3.5  ·  t_MS = 10 Gyr (M/M☉)^(−2.5)',
        expect: 'More members average the parallax errors and fill the main sequence up to its true turn-off.',
        extras: function (v) { return 'd ' + fx(v.dfit, 1) + ' pc  M_TO ' + fx(v.Mto, 3) + ' M☉  age ' + fx(v.agefit, 3) + ' Gyr'; },
        instrument: 'Archive terminal (Gaia member list)', lab: 'Astrophysics Data Laboratory',
        viva: [['Why the inverse of the mean parallax, not the mean of the inverses?', ['Parallax errors are symmetric; their inverses are not', 'It is faster', 'They are the same'], 0, '1/ϖ is a biased estimator for noisy single parallaxes.']]
      };
    },
    pa10_lsp: function () {
      var w = Math.round(p.what), pdm = Math.round(p.method) === 1;
      return {
        title: 'Variable star: ' + (pdm ? 'phase dispersion minimisation' : 'Lomb-Scargle periodogram'),
        quantity: ['period', 'amplitude (peak to peak)', 'distance (P-L relation)'][w], unit: ['d', 'mag', 'pc'][w], digits: [5, 3, 0][w],
        nlabel: 'epochs', ns: [50, 100, 200, 400], tol: 0.01, showCurve: true, nodes: w !== 0, dots: true, hidden: true,
        methods: [pdm ? 'Phase dispersion minimisation' : 'Lomb-Scargle periodogram'],
        xlabel: w ? 'phase' : 'trial frequency (cycles per day)', ylabel: w ? 'magnitude' : (pdm ? '−θ (PDM)' : 'Lomb-Scargle power'),
        legend: w ? [['#ff7b5a', '• folded epochs'], ['#ffc247', '– – 4-harmonic fit']] : [['#ffc247', pdm ? '— −θ, higher is better' : '— periodogram']], used: 'epochs',
        problem: ['Star: ' + (SAMPLE || 'Cepheid') + ';  ' + Math.round(p.n) + ' epochs at random times over ' + fx(p.span, 0) + ' days, σ = ' + fx(p.sig, 2) + ' mag',
          'Trial frequencies ' + fx(p.fmin, 2) + ' – ' + fx(p.fmax, 2) + ' per day, step 1/(5 × span), refined 20 times finer',
          pdm ? 'PDM: fold on each trial period, ' + Math.round(p.nbin) + ' phase bins; θ = scatter in the bins / total scatter' : 'Lomb-Scargle: power of the best sinusoid at each frequency',
          w === 2 ? 'Cepheid P-L: M_V = ' + fx(p.plA, 2) + ' (log P − 1) ' + fx(p.plB, 2) + ';  d = 10^((m − M + 5)/5) pc' : 'Amplitude: peak to peak of a 4-harmonic Fourier fit at the period', SIMNOTE],
        formula: pdm ? 'θ(P) = s²(bins) / σ²  →  minimum' : 'P_LS(f) = [ (Σ y cos)²/Σ cos² + (Σ y sin)²/Σ sin² ] / 2',
        expect: 'More epochs narrow the periodogram peak against the noise and fill every phase of the fold.',
        extras: function (v) { return 'P ' + fx(v.Pfit, 5) + ' d  amp ' + fx(v.amp, 3) + ' mag' + (Math.round(p.kind) === 0 ? '  d ' + fx(v.dfit, 0) + ' pc' : ''); },
        instrument: 'Archive terminal (survey photometry)', lab: 'Astrophysics Data Laboratory',
        viva: [['Longer observing spans give', ['a sharper periodogram peak (width about 1/span)', 'a broader peak', 'no change'], 0, 'The frequency resolution is about one cycle over the span.']]
      };
    },
    pa10_schro: function () {
      var pot = Math.round(p.pot), split = Math.round(p.method) === 1, hyd = pot === 2, k = Math.round(p.k), l = Math.round(p.l);
      var nm = ['harmonic oscillator V = x²/2', 'double well V = V₀((x/a)² − 1)²', 'hydrogen atom (radial)'][pot];
      if (split) {
        return {
          title: 'Split-step Fourier: tunnelling time', quantity: 'tunnelling time', unit: 'ħ/E units', digits: 4,
          nlabel: 'time steps per unit time', ncol: 'steps/unit', ns: [2, 4, 8, 16, 32], tol: 0.01, showCurve: true, nodes: false, hidden: false,
          methods: ['Split-step Fourier, exp(−iVdt/2) exp(−iTdt) exp(−iVdt/2)'], xlabel: 'time (ħ/E units)', ylabel: 'probability in the right well',
          legend: [['#59b6ff', '— (1 − cos ΔE t)/2 from the reference'], ['#ffc247', '– – split-step']], refname: 'π ħ / ΔE from the finite-difference eigenvalues',
          problem: ['Double well V = ' + fx(p.V0, 1) + ' ((x/' + fx(p.a, 2) + ')² − 1)², units ħ = m = 1, grid 128 points on ±' + fx(p.L, 1),
            'Start: (ψ₀ + ψ₁)/√2, the particle in the left well', 'Each step: half potential, kinetic in momentum space (FFT), half potential',
            'Tunnelling time: the first maximum of the probability on the right (parabola through the top three)', 'Reference: π ħ / (E₁ − E₀), finite differences on 1500 + 3000 points, Richardson'],
          formula: 'ψ(t+dt) = e^{−iVdt/2} F⁻¹ e^{−ik²dt/2} F e^{−iVdt/2} ψ(t)  ·  T = π ħ / ΔE',
          expect: 'The splitting error of the method falls as dt², so halving dt divides the error by about four.',
          extras: function (v) { return 'ΔE ' + fx(v.E, 5) + '  steps ' + v.steps; },
          lab: 'Computational Physics Laboratory',
          viva: [['The probability on the right oscillates as (1 − cos ΔE t)/2 because', ['the state is a superposition of two eigenstates', 'the barrier moves', 'of numerical noise'], 0, 'Only the relative phase ΔE t of ψ₀ and ψ₁ changes.']]
        };
      }
      return {
        title: 'Numerov shooting: ' + nm, quantity: hyd ? 'energy E (n = ' + (k + l + 1) + ', l = ' + l + ')' : 'eigenvalue E' + ['₀', '₁', '₂', '₃', '₄'][Math.min(4, k)],
        unit: hyd ? 'eV' : 'ħω' , digits: 6,
        nlabel: 'grid steps', ncol: 'steps', ns: hyd ? [400, 800, 1600, 3200, 6400] : [100, 200, 400, 800, 1600], tol: 0.01, showCurve: true, nodes: false, hidden: false,
        methods: ['Numerov shooting with node-count bisection'], xlabel: hyd ? 'r (Bohr radii)' : 'x', ylabel: 'ψ (scaled) and V (scaled)',
        legend: [['#59b6ff', '— potential (scaled)'], ['#ffc247', '– – ψ at the energy found']], refname: hyd ? 'E = −13.6057 eV / n²' : pot === 1 ? 'finite differences on 1500 + 3000 points, Richardson-extrapolated' : 'E = (k + ½) ħω',
        problem: ['Potential: ' + nm + (pot === 1 ? ',  V₀ = ' + fx(p.V0, 1) + ', a = ' + fx(p.a, 2) : ''), hyd ? 'u″ = (l(l+1)/r² − 2/r − 2E) u, atomic units, r to ' + fx(p.rmax, 0) : 'ψ″ = 2(V − E) ψ, units ħ = m = ω = 1, x in ±' + fx(p.L, 1),
          'Numerov: ψᵢ₊₁(1 − h²fᵢ₊₁/12) = 2ψᵢ(1 + 5h²fᵢ/12) − ψᵢ₋₁(1 − h²fᵢ₋₁/12)', 'State ' + k + ' (nodes): bisection until the node count jumps from ' + k + ' to ' + (k + 1),
          'Reference: ' + (hyd ? '−13.6057 eV / n²' : pot === 1 ? 'independent finite-difference solution' : 'k + ½')],
        formula: hyd ? 'E_n = −13.6057 eV / n²' : 'ψ″ = 2(V − E)ψ  ·  Numerov error ∝ h⁴',
        expect: 'The Numerov scheme is fourth order: halving the step divides the error by about sixteen until rounding takes over.',
        extras: function (v) { return 'E = ' + fx(v.E, 6) + (hyd ? ' Ha' : ''); },
        lab: 'Computational Physics Laboratory',
        viva: [['The k-th eigenfunction of a 1-D potential has', ['k nodes', 'k + 1 nodes', 'no nodes'], 0, 'The ground state has none; each higher state one more.']]
      };
    }
  };
  var SP = (SPECS[KNAME] || SPECS.pa10_tof)();
  SP.nsFor = function (mi) { return (SP.nsByMethod && SP.nsByMethod[mi]) || SP.ns; };
  var METHODS = SP.methods;
  var M0 = Math.min(METHODS.length - 1, Math.max(0, Math.round(p.method === undefined ? 0 : p.method)));
  var NS = SP.nsFor(M0);
  var HID = !!SP.hidden;
  var st = { on: false, mi: M0, ni: Math.max(0, NS.length - 3), last: null, busy: false, reveal: 0 };

  function withSet(ni, mi) {
    var q = {};
    Object.keys(p).forEach(function (k) { q[k] = p[k]; });
    q.n = SP.nsFor(mi)[ni];                            // the method is the lab's own (p.method), never the panel index
    return q;
  }
  function compute(ni, mi) {
    var q = withSet(ni, mi);
    var s = K.init(q);
    var v = K.view(s, q);
    v.set = q;
    if (false && v.py && v.py.length === v.cx.length) {   // the DTG curve, scaled onto the mass axis
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
    wrap(x, HID ? 'Record for every run: n and the answer. Report the answer from the most data (the largest n).' : 'Record for every run: n, the answer and the error. Report the answer with the smallest error.', 50, y, w - 100, 42);
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
        x.fillText(HID ? 'from ' + cur.nused + ' ' + (SP.used || 'points of the fit') : 'ref ' + sci(cur.exact) + '  err ' + cur.err.toExponential(1), RX, H2 - P.b + 58);
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
    S.addApparatus('inst', instG, SP.instrument, 'The detector or receiver that recorded the data. Its data file is open on the workstation: the analysis is done on the computer. SIMULATED DATA.');
  }

  S.addApparatus('mon', mon, 'Monitor', 'The plot and the run log. Left: the data and the fit (or the reference and the method). Right: every run.');
  S.addApparatus('kbd', kbd, 'Keyboard', 'Enter runs the method at the settings you have chosen. Nothing is computed until you press it.');
  S.addApparatus('mouse', mouse, 'Mouse', 'For the settings on the panel. How much of the data (or how fine a setting) is the only choice this practical needs.');
  S.addApparatus('tower', tower, 'Workstation', 'The computer that runs the analysis. The same code is used for the check, so the answer on the screen is what the check judges.');
  S.addApparatus('card', card, 'Method card', 'The printed card: the problem, the available methods and the formulas. Read it before you touch the machine.');
  S.addApparatus('book', S.book.group, 'Lab record book', HID ? 'Every run you keep is written here: n and the answer.' : 'Every run you keep is written here: the method, n, the answer, the reference value and the error.');

  var hudV = S.hudCard('Numerical'), hudE = S.hudCard(HID ? 'Fit points' : 'Reference'), hudErr = S.hudCard(HID ? 'n' : 'Rel. error'), hudN = S.hudCard('Runs');

  // ================================================================================= actions
  function powerOn() {
    if (st.on || S.hand.busy) return Promise.resolve();
    return S.hand.tap(pwr).then(function () {
      st.on = true; led.material.color.setHex(0x49d36a); tled.material.color.setHex(0x49d36a);
      S.say('Workstation on. Choose how much data (or how fine a setting) to use, then press Enter.');
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
    var C = null;
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
    ? 'A detector, a telescope or a survey records data; the number in a paper comes from analysing it - a fit, a peak, '
      + 'a periodogram, a straight line through part of a plot. This practical is that analysis. ' + SIMNOTE + ' Use more of the '
      + 'recorded points and see how the answer settles. ' + (SP.expect || '')
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
      more: HID ? ['The value behind the data is hidden, exactly as nature keeps it: the answer is judged only at the end, against the value the data were made from.',
        'The noise is seeded, so the same settings always give the same data; a different number of points gives a different draw of the noise.',
        'Change one thing at a time and write down every run before changing anything.']
        : ['The reference is either a closed formula or an independent method, never the same code at a finer setting, so the error on the screen is the method\'s real error.',
          'Refine the setting step by step and watch the error fall: its rate tells the order of the method.',
          'Report the answer with the smallest error and the number of digits on which it agrees with the reference.'],
      precautions: HID ? 'Read the method card before switching on. Record n and the answer of every run. Report the answer from the finest '
        + 'data with no more digits than the runs agree to.' : 'Read the method card before switching on. Record the setting, the answer, the reference and the error of every run.',
    },
    book: {
      title: 'Expt. — ' + S.lab.title,
      lines: ['Aim: ' + S.lab.aim, 'Problem: ' + SP.title + (SAMPLE ? ' · ' + SAMPLE : ''),
        HID ? 'Data: ' + (SP.instrument || 'instrument') + ' data (simulated)' : 'Reference: ' + (SP.refname || 'exact or independent solution'),
        'Method: ' + METHODS[M0], 'For each run: ' + SP.nlabel + ', the answer' + (HID ? '.' : ', the reference and the error.')],
      columns: HID ? [{ label: 'S.No', get: function (r, i) { return i + 1; } },
        { label: (SP.ncol || SP.nlabel).slice(0, 18), get: function (r) { return String(r.n); } },
        { label: 'Answer' + (SP.unit ? ' (' + SP.unit + ')' : ''), get: function (r) { return sci(r.val); } }]
        : [{ label: 'S.No', get: function (r, i) { return i + 1; } },
          { label: (SP.ncol || SP.nlabel).slice(0, 14), get: function (r) { return String(r.n); } },
          { label: 'Method', get: function (r) { return sci(r.val); } },
          { label: 'Reference', get: function (r) { return sci(r.exact); } },
          { label: 'Rel. diff.', get: function (r) { return r.err.toExponential(2); } }],
    },
    graph: {
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
          : 'Best run: ' + SP.nlabel + ' = ' + b.n + ', method ' + sci(b.val) + ', reference ' + sci(b.exact) + ', error '
            + b.err.toExponential(2) + '.' };
    },
    tol: SP.tol,
    chips: HID ? ['What do these data show?', 'Why use more data?', 'Check my runs', 'Explain the formula on the card', 'Is this real data?']
      : ['Why does the error fall?', 'What is the reference?', 'Check my runs', 'Explain the method on the card', 'What is the order of the method?'],
    viva: (SP.viva || []).concat(HID ? [['Why is the sample\'s true value not shown during the practical?',
      ['It is what the analysis must find', 'The computer does not know it', 'It changes every run'], 0,
      'A characterisation measures an unknown; seeing the answer first would make the analysis pointless.'],
      ['The data in this practical are', ['simulated from a hidden value with seeded noise', 'downloaded from a real instrument', 'typed in by hand'], 0,
        'The lab says SIMULATED DATA plainly: the data come from the kernel, the analysis is real.']]
      : [['A numerical answer is judged against', ['an exact formula or an independent method', 'the same code at the same setting', 'nothing'], 0,
        'Only an independent reference shows the real error of the method.']]),
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
          u.p(HID ? 'The detector or survey has recorded its data (SIMULATED DATA). The card says what the data are, how they are analysed and which formula turns the fit into the answer.'
            : 'The card names the problem, the method and the reference the answer is judged against.');
          u.formula(SP.title, SP.formula);
          cardLines.forEach(function (t) { u.p(t); });
          u.task('Switch the workstation on', st.on, st.on ? 'The screen is live' : 'Press the power button under the screen')
            .add(u.button(st.on ? 'On' : 'Switch on', function () { powerOn(); }, !st.on, st.on || S.hand.busy));
          u.next('Next: the runs', st.on);
        },
        ok: function () { return st.on; },
        auto: function () { return powerOn(); } },

      { id: 'runs', title: HID ? 'Analyse the data' : 'Refine the method', view: 'screen',
        render: function (u) {
          u.h2(HID ? 'Analyse the data with more and more of it' : 'Run the method at finer and finer settings');
          u.p(HID ? 'Choose how much of the recorded data the analysis uses, then press Enter. The screen shows the data, the fit and the answer.'
            : 'Choose the setting and press Enter. The screen draws the reference (blue) and what the method built (dashed), with the error.');
          u.slider(SP.nlabel, 0, NS.length - 1, 1, function () { return st.ni; },
            function (v) { setN(Math.round(v)); }, '', 0);
          u.note(SP.nlabel + ' = ' + NS[st.ni]);
          u.row(u.button('Run — press Enter', function () { runOnce(); }, true, !st.on || S.hand.busy),
            u.button('Run every setting', function () { autoSweep(); }, false, !st.on || S.hand.busy));
          u.live(function () {
            if (!st.last) return 'No run yet. Press Enter.';
            return HID ? SP.quantity + ' = ' + sci(st.last.val) + unitS + '  ·  ' + st.last.nused + ' ' + (SP.used || 'points of the fit')
              : SP.quantity + ' = ' + sci(st.last.val) + unitS + '  ·  reference ' + sci(st.last.exact) + '  ·  error ' + st.last.err.toExponential(2);
          });
          u.h3('Observation table'); u.table();
          var k = distinctN();
          u.next('Next: the answer', S.rows.length >= 4 && k >= 3);
          if (S.rows.length < 4 || k < 3) u.p(S.rows.length + ' run(s) kept at ' + k + ' different settings. Take at least 4 runs at 3 or more settings of ' + SP.nlabel + '.');
        },
        ok: function () { return S.rows.length >= 4 && distinctN() >= 3; },
        auto: function () { return autoSweep(); } },

      { id: 'order', title: HID ? 'Settled answer' : 'Compare with the reference', view: 'screen',
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
            u.h2('The method against the reference');
            u.p('Look at how the error falls as the setting is refined. The run with the smallest error is the result.');
            if (SP.expect) u.note(SP.expect);
            if (b) u.note('Best run: ' + SP.nlabel + ' = ' + b.n + ' gives ' + sci(b.val) + unitS + ' against ' + sci(b.exact) + ' (error ' + b.err.toExponential(2) + ').');
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
    return pr.then(function () { S.say(HID ? 'Analysed the data at every setting. Look at how the answer settles.' : 'Ran every setting. Look at how the error falls.'); S.render(); });
  }
});
